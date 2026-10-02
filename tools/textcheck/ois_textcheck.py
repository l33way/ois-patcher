#!/usr/bin/env python3
"""
ois_textcheck.py -- find spelling / grammar problems in the player-visible text of
Objects in Space's assets/*.txt files, and turn reviewed corrections into patch data.

The assets mix prose (news articles, dialogue, emails, descriptions, UI labels) with a
lot of data (ids, coordinates, flags, file names). This tool only looks at prose:

  * article files   news_*.txt / info_*.txt         every line except metadata headers
  * key=value lines  keys listed in PROSE_KEYS      (text=, body=, description=, ...)
  * free-text lines  chatter_*.txt, tgs_*email, continuation lines of multi-line values

Colour codes (`0 `! ...), %-format specifiers, UPPER_CASE_IDENTIFIERS and $variable
tokens are stripped before checking.

Commands
--------
  scan   --assets DIR [--out DIR] [--grammar]
         Writes candidates for HUMAN REVIEW (nothing is changed):
           spelling_unknown.csv   words unknown to both en_GB and en_US dictionaries
           name_variants.csv      capitalised words one letter away from a much more common one
           variable_typos.csv     rare $variable tokens that look like typos of common ones
           grammar.csv            (--grammar) LanguageTool findings, noisy rule classes removed
  fixes  --assets DIR [--out FILE] [--name-variants]
         Applies corrections.py (a curated word -> replacement table) to the prose lines and
         writes FIXES in the same shape apply_data_fixes.py uses:
             "file.txt": [(count, "old snippet", "new snippet"), ...]
         Snippets are short (the word plus a little context, unique in that file) so no game
         text is bundled. The result is validated by simulating the patcher.

Requirements: Python 3.8+, `aspell` with the en dictionaries on PATH (scan), and for
--grammar:  pip install language-tool-python  (needs Java; downloads LanguageTool once).

Important limits (see README.md next to this file): a dictionary cannot find a correctly
spelled wrong word, many "errors" are deliberate (dialect, rushed emails, a ciphered line),
and invented names are everywhere. Treat scan output as candidates, not verdicts.
"""
import argparse
import collections
import csv
import os
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

# ----------------------------------------------------------------------------- extraction
PROSE_KEYS = {
    "text", "body", "description", "subject", "summary", "boot", "customfield",
    "name", "email", "docking", "dockdesc", "tooltip", "hostilemessage",
    "successtext", "failuretext", "attackmessage", "from", "button",
    "greyedbutton", "checkbox", "message", "title", "label", "reply",
    "dialog", "dialogue", "shortname", "tabname", "string", "msg", "greeting",
    "success", "failure", "complytext", "refusetext", "intro", "outro",
    "undocking", "playermessage", "shortdesc", "piratemessage", "cancelattackmessage",
}
COLOUR = re.compile(r"`.")
FMT = re.compile(r"%[-+ #0]*\d*(?:\.\d+)?[a-zA-Z%]")
IDENT = re.compile(r"\b[A-Za-z0-9]*_[A-Za-z0-9_]*\b|\b[A-Z0-9]{2,}(?:_[A-Z0-9]+)+\b")
VARIABLE = re.compile(r"\$[A-Za-z_]+")
NUMERIC_LEAD = re.compile(r"^\s*(?:-?\d+(?:\.\d+)?\s*,\s*)+")
WORD = re.compile(r"[A-Za-z]+(?:['’][A-Za-z]+)*")
KV = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)\s*$")
ARTICLE_PREFIXES = ("news_", "info_")
ARTICLE_SKIP = re.compile(r"^\s*(Importance|Date|Req|Delay|Tags|Flags?|Order|Type|Category)\s*:", re.I)
ARTICLE_HDR = re.compile(r"^\s*(Author|Publication|Short|Subject|Summary|Title)\s*:\s*(.*)$", re.I)


def clean(text):
    text = text.replace("%%", "%").replace("^", " ").replace("\\n", " ")
    text = COLOUR.sub("", text)
    text = FMT.sub(" ", text)
    text = IDENT.sub(" ", text)
    return VARIABLE.sub(" ", text)


def iter_prose(path):
    """yield (file, line_no, kind, cleaned_text, raw_line) for the prose lines of one file"""
    name = path.name
    raw = path.read_bytes().decode("utf-8", errors="replace")
    article = name.startswith(ARTICLE_PREFIXES)
    for no, line in enumerate(raw.splitlines(), 1):
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if article:
            if ARTICLE_SKIP.match(line):
                continue
            m = ARTICLE_HDR.match(line)
            yield name, no, "article", clean(m.group(2) if m else line), line
            continue
        m = KV.match(line)
        if not m:
            if (not name.endswith("_names.txt") and not s.startswith(("begin", "end", "include"))
                    and len(re.findall(r"[A-Za-z]{2,}", s)) >= 3 and " " in s):
                yield name, no, "freetext", clean(s), line
            continue
        key, val = m.group(1).lower(), m.group(2)
        if key in PROSE_KEYS:
            yield name, no, key, clean(NUMERIC_LEAD.sub("", val)), line


def iter_all(assets):
    for p in sorted(Path(assets).glob("*.txt")):
        yield from iter_prose(p)


# ----------------------------------------------------------------------------- scan
def aspell_unknown(words, lang):
    if not words:
        return set()
    try:
        out = subprocess.run(["aspell", "list", "-l", lang, "--encoding=utf-8"],
                             input="\n".join(words), capture_output=True, text=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError) as e:
        sys.exit(f"aspell ({lang}) failed: {e}. Install aspell and its English dictionaries.")
    return {w for w in out.split("\n") if w}


def aspell_suggest(word, lang="en_GB"):
    try:
        out = subprocess.run(["aspell", "-a", "-l", lang], input=word + "\n", capture_output=True,
                             text=True).stdout
    except OSError:
        return []
    for ln in out.splitlines():
        if ln.startswith("&"):
            return [s.strip() for s in ln.split(":", 1)[1].split(",")][:3]
    return []


def one_edit(a, b):
    if a == b or abs(len(a) - len(b)) > 1:
        return False
    if len(a) == len(b):
        d = [i for i in range(len(a)) if a[i] != b[i]]
        return len(d) == 1 or (len(d) == 2 and d[1] == d[0] + 1 and a[d[0]] == b[d[1]] and a[d[1]] == b[d[0]])
    if len(a) > len(b):
        a, b = b, a
    return any(b[:i] + b[i + 1:] == a for i in range(len(b)))


def cmd_scan(args):
    assets = Path(args.assets)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    occ = collections.defaultdict(list)
    contexts = {}
    rows = list(iter_all(assets))
    for f, no, kind, text, raw in rows:
        for m in WORD.finditer(text):
            w = m.group(0)
            occ[w].append((f, no))
            contexts.setdefault((w, f, no), text[max(0, m.start() - 40):m.end() + 40].strip())
    words = sorted(occ)
    unknown = sorted(aspell_unknown(words, "en_GB") & aspell_unknown(words, "en_US"))
    # spelling_unknown.csv: lowercase first (almost always typos / slang), then capitalised
    unknown.sort(key=lambda w: (w[0].isupper(), w.lower()))
    with open(out / "spelling_unknown.csv", "w", newline="", encoding="utf-8") as fh:
        wr = csv.writer(fh)
        wr.writerow(["word", "count", "first_file", "first_line", "context", "suggestions"])
        for w in unknown:
            f, no = occ[w][0]
            wr.writerow([w, len(occ[w]), f, no, contexts[(w, f, no)], " | ".join(aspell_suggest(w))])
    # name_variants.csv: rare capitalised word one edit away from a much commoner one
    cnt = collections.Counter({w: len(v) for w, v in occ.items() if w[0].isupper() and len(w) >= 5 and not w.isupper()})
    ws = sorted(cnt)
    byfirst = collections.defaultdict(list)
    for w in ws:
        byfirst[w[0]].append(w)
    pairs = []
    for lo in ws:
        if cnt[lo] > 3:
            continue
        for hi in byfirst[lo[0]] + [w for w in ws if w[0] != lo[0] and one_edit(lo.lower(), w.lower())]:
            if cnt[hi] >= 2 and cnt[lo] * 2 <= cnt[hi] and one_edit(lo, hi):
                pairs.append((lo, cnt[lo], hi, cnt[hi]))
    with open(out / "name_variants.csv", "w", newline="", encoding="utf-8") as fh:
        wr = csv.writer(fh)
        wr.writerow(["rare", "rare_count", "common", "common_count", "first_file", "first_line"])
        for lo, cl, hi, ch in sorted(set(pairs)):
            wr.writerow([lo, cl, hi, ch, *occ[lo][0]])
    # variable_typos.csv
    var = collections.Counter()
    where = {}
    for p in sorted(assets.glob("*.txt")):
        for no, ln in enumerate(p.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            if ln.lstrip().startswith("#"):
                continue
            for t in VARIABLE.findall(ln):
                var[t] += 1
                where.setdefault(t, (p.name, no))
    with open(out / "variable_typos.csv", "w", newline="", encoding="utf-8") as fh:
        wr = csv.writer(fh)
        wr.writerow(["token", "count", "looks_like", "like_count", "file", "line"])
        for t, n in var.items():
            if n <= 2:
                for u, m in var.most_common(60):
                    if u != t and m >= 5 and one_edit(t.lower(), u.lower()) and t.lower() != u.lower():
                        wr.writerow([t, n, u, m, *where[t]])
                        break
    print(f"{len(rows)} prose lines; {len(unknown)} unknown words -> {out}")
    if args.grammar:
        scan_grammar(rows, out)


GRAMMAR_SKIP_CATEGORIES = {"PUNCTUATION", "STYLE", "TYPOGRAPHY", "REDUNDANCY", "AMERICAN_ENGLISH",
                           "BRE_STYLE_OXFORD_SPELLING", "COMPOUNDING", "COLLOCATIONS"}
GRAMMAR_SKIP_RULES = {"ENGLISH_WORD_REPEAT_BEGINNING_RULE", "EN_QUOTES", "UPPERCASE_SENTENCE_START",
                      "WHITESPACE_RULE", "MORFOLOGIK_RULE_EN_GB", "MORFOLOGIK_RULE_EN_US",
                      "COMMA_PARENTHESIS_WHITESPACE", "SENTENCE_WHITESPACE", "DOUBLE_PUNCTUATION",
                      "PUNCTUATION_PARAGRAPH_END", "EN_UNPAIRED_BRACKETS", "UNLIKELY_OPENING_PUNCTUATION",
                      "COMMA_COMPOUND_SENTENCE", "ELLIPSIS", "TWO_HYPHENS"}


def scan_grammar(rows, out):
    try:
        import language_tool_python as lt
    except ImportError:
        sys.exit("--grammar needs:  pip install language-tool-python   (and Java)")
    tool = lt.LanguageTool("en-GB")
    tool.disabled_rules = GRAMMAR_SKIP_RULES
    with open(out / "grammar.csv", "w", newline="", encoding="utf-8") as fh:
        wr = csv.writer(fh)
        wr.writerow(["file", "line", "rule", "category", "message", "context", "suggestions"])
        for f, no, kind, text, raw in rows:
            if len(text.split()) < 3:
                continue
            for m in tool.check(re.sub(r"\s+", " ", text).strip()):
                if m.category in GRAMMAR_SKIP_CATEGORIES:
                    continue
                wr.writerow([f, no, m.rule_id, m.category, m.message, m.context, " | ".join(m.replacements[:3])])
    print(f"grammar -> {out / 'grammar.csv'}")


# ----------------------------------------------------------------------------- fixes
def load_corrections():
    sys.path.insert(0, str(HERE))
    import corrections as C
    return C


def case_like(src, new):
    if src.isupper() and len(src) > 1:
        return new.upper()
    if src[0].isupper():
        return new[0].upper() + new[1:]
    return new


WORD_BOUND = re.compile(r"(?<![A-Za-z'’_])[A-Za-z]+(?:['’][A-Za-z]+)*(?![A-Za-z_])")


def line_spans(line, C, table, fname=None):
    """non-overlapping (start, end, replacement) fixes for one raw line"""
    out = []
    for old, new in C.PHRASES.items():
        for m in re.finditer(re.escape(old), line):
            out.append((m.start(), m.end(), new))
    for gfile, old, new in C.GRAMMAR:
        if gfile is None or gfile == fname:
            for m in re.finditer(re.escape(old), line):
                out.append((m.start(), m.end(), new))
    for m in WORD_BOUND.finditer(line):
        if any(s <= m.start() < e for s, e, _ in out):
            continue
        r = table.get(m.group(0).lower())
        if r:
            out.append((m.start(), m.end(), case_like(m.group(0), r)))
    return sorted(out)


def apply_spans(line, spans):
    for s, e, r in reversed(spans):
        line = line[:s] + r + line[e:]
    return line


def build_fixes(assets, C, with_names):
    table = {**C.SPELLING, **C.PLACES}
    if with_names:
        table.update(C.NAME_VARIANTS)
    skip = set(C.DELIBERATE) | set(C.SKIP_FILES)
    per_file = collections.defaultdict(list)
    for f, no, kind, text, raw in iter_all(assets):
        if f in skip:
            continue
        sp = line_spans(raw, C, table, f)
        if sp:
            per_file[f].append((no, raw, sp))
    fixes, expected = {}, {}
    for f, lines in per_file.items():
        content = (Path(assets) / f).read_bytes().decode("utf-8").replace("\r\n", "\n")
        toks = []
        for no, raw, sp in lines:
            for i, (s, e, r) in enumerate(sp):
                lo = sp[i - 1][1] if i else 0
                hi = sp[i + 1][0] if i + 1 < len(sp) else len(raw)
                toks.append((raw, s, e, r, lo, hi))

        def snip(t, k):
            raw, s, e, r, lo, hi = t
            S, E = max(lo, s - k), min(hi, e + k)
            while S < s and S > lo and not raw[S - 1].isspace():
                S += 1
            while S < s and raw[S].isspace():
                S += 1
            while E < hi and E > e and not raw[E].isspace():
                E += 1
            while E > e and raw[E - 1].isspace():
                E -= 1
            return raw[S:E], raw[S:s] + r + raw[e:E]

        entries, seen = [], set()
        for t in toks:
            chosen = None
            for k in range(12, 120, 3):
                o, n = snip(t, k)
                same = sum(1 for u in toks if snip(u, k) == (o, n))
                if content.count(o) == same:
                    chosen = (o, n)
                    break
            if chosen is None:           # fall back to the whole line (rare)
                line_sp = next(sp for no, raw, sp in lines if raw == t[0])
                chosen = (t[0], apply_spans(t[0], line_sp))
            if chosen not in seen:
                seen.add(chosen)
                entries.append(chosen)
        fixes[f] = [(content.count(o), o, n) for o, n in entries]
        # what the file should look like after the fix
        out_lines = content.split("\n")
        for no, raw, sp in lines:
            out_lines[no - 1] = apply_spans(raw, sp)
        expected[f] = "\n".join(out_lines)
    return fixes, expected


def simulate(assets, fixes, expected):
    bad = []
    for f, entries in fixes.items():
        content = (Path(assets) / f).read_bytes().decode("utf-8").replace("\r\n", "\n")
        for cnt, o, n in entries:
            if content.count(o) != cnt:
                bad.append((f, "count", o))
                break
            content = content.replace(o, n)
        if content != expected[f]:
            bad.append((f, "mismatch", ""))
    return bad


def cmd_fixes(args):
    C = load_corrections()
    fixes, expected = build_fixes(args.assets, C, args.name_variants)
    bad = simulate(args.assets, fixes, expected)
    if bad:
        for b in bad[:20]:
            print("PROBLEM", b)
        sys.exit(f"{len(bad)} validation problems; not writing {args.out}")
    n = sum(len(v) for v in fixes.values())
    lines = ['"""Generated by ois_textcheck.py -- spelling/grammar fixes for apply_data_fixes.py.',
             '',
             'Same shape as apply_data_fixes.FIXES: file -> [(expected_count, old, new)].',
             'Each snippet is verified against your own game files before it is applied."""',
             '', 'TEXT_FIXES = {']
    for f in sorted(fixes):
        lines.append(f"    {f!r}: [")
        for cnt, o, nn in fixes[f]:
            lines.append(f"        ({cnt}, {o!r}, {nn!r}),")
        lines.append("    ],")
    lines.append("}")
    Path(args.out).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"{n} fixes in {len(fixes)} files -> {args.out} (validated by simulation)")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("scan", help="list candidate errors for human review")
    s.add_argument("--assets", required=True, help="the game's assets folder")
    s.add_argument("--out", default="textcheck_out")
    s.add_argument("--grammar", action="store_true", help="also run LanguageTool (slow, needs Java)")
    s.set_defaults(fn=cmd_scan)
    f = sub.add_parser("fixes", help="apply corrections.py and write patch data")
    f.add_argument("--assets", required=True)
    f.add_argument("--out", default="text_fixes.py")
    f.add_argument("--name-variants", action="store_true", help="also apply the opt-in person-name variants")
    f.set_defaults(fn=cmd_fixes)
    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
