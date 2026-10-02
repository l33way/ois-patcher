# textcheck: spelling and grammar tooling for the game's text files

`ois_textcheck.py` finds spelling and grammar problems in the player-visible text of
*Objects in Space*'s `assets/*.txt` files, and turns **reviewed** corrections into patch
data in the same shape `apply_data_fixes.py` already uses.

The generator itself is optional and never edits the game. Its output, `text_fixes.py` at the
repo root, **is** used: `apply_data_fixes.py` loads it automatically when the patcher installs
the bugfix mod. See [REPORT.md](REPORT.md) for what was found and what needs a human decision.

## What it looks at

The assets mix prose with a lot of data (ids, coordinates, flags, file names), so the tool
only checks prose: news/info articles, `text=` / `body=` / `description=` / `subject=` / ...
values, UI labels, docking messages, chatter templates and continuation lines. Colour codes
(`` `0 ``), `%`-format specifiers, `UPPER_CASE` ids and `$variable` tokens are stripped first.
The `sector_*` files and the `*_names.txt` lists are invented names, so those are not
treated as prose.

## Usage

```
# 1. find candidates (needs aspell + en dictionaries on PATH; --grammar also needs Java)
python ois_textcheck.py scan  --assets "C:\...\Objects in Space\assets" --out textcheck_out [--grammar]

# 2. after reviewing, generate patch data from corrections.py (validated before writing)
python ois_textcheck.py fixes --assets "C:\...\Objects in Space\assets" --out ../../text_fixes.py [--name-variants]
```

`scan` writes CSVs for human review: `spelling_unknown.csv` (words unknown to both the
en_GB and en_US dictionaries, lowercase first), `name_variants.csv` (a rare capitalised word
one letter away from a much commoner one), `variable_typos.csv` (rare `$tokens` that look
like typos of common ones) and, with `--grammar`, `grammar.csv` (LanguageTool findings with
the noisy style/punctuation classes removed).

`fixes` applies the curated tables in `corrections.py` and writes `text_fixes.py`:

```python
TEXT_FIXES = {"news_foo.txt": [(1, "that way beacuse the words", "that way because the words")], ...}
```

Every entry is a short snippet (the word plus a little context, unique in its file), so no
game text is bundled. Each snippet's expected occurrence count is checked against the
player's own file at install time, exactly like the existing data fixes. The generator also
validates its own output by simulating the patcher before writing anything.

### How `text_fixes.py` is used by the patcher

`apply_data_fixes.py` loads `text_fixes.py` automatically and merges its entries into the existing
`FIXES` table per file (a file such as `modules_arms.txt` can have entries in both), so no manual
step is needed. If the file is missing, the patcher prints a warning and installs without the text
corrections. The release workflow packages it alongside `apply_data_fixes.py`.

The corrections add 321 files to the generated mod. In testing, the patcher's own `apply_all`
applied all 321 with 0 skipped, and the result matched an independently built copy.

## Honest limits

* A dictionary cannot find a correctly spelled wrong word ("form" for "from"). The grammar
  pass catches some of those, but nowhere near all.
* A lot of "errors" are deliberate: dialect (`gonna`, `lookin'`, `you was`), rushed or panicked
  emails, a ciphered line, a character unsure how to spell "progenitors". Those files are listed
  in `corrections.DELIBERATE` and never touched.
* Invented names are everywhere. Place names on the in-game nav map are treated as correct;
  person-name spelling variants are opt-in only (`--name-variants`).
* So this is "every error I could find and was confident about", not a guarantee of "every error".
