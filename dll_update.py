"""
dll_update.py -- optional refresh of the game's bundled 32-bit libraries.

A Python port of the core of Patch_OIS.bat from https://github.com/Voidless7125/OIS-Update
(branch `dev`): the same package layout, the same SHA256 manifest, the same marker files in
the game folder, so Patch_OIS.bat / OIS_Health_Check.bat still understand a game folder this
module has updated.  Used by ois_patcher.py, which asks the user before anything here runs.

What it does
  1. Finds the update package: a local copy (an extracted OIS-Update[-dev] folder next to this
     script, or the folder named by %OIS_UPDATE_DIR%), otherwise downloads it from GitHub into
     ./OIS-Update.  Every file is checked against the package's own manifest.txt.
  2. Refuses to touch anything while ois.exe / ois_server.exe is running.
  3. Backs up each DLL it is about to replace (once -- the first backup is the true original)
     into <game>/oisbugfix_original_dlls/, copies the new ones, and re-verifies every file.
  4. Writes OIS_Update.version.txt / OIS_Update.manifest.txt (same format as the batch script)
     plus oisbugfix_dll_update.json, which remembers what to put back on --uninstall.

What it deliberately does not do: the optional Windows Firewall rules, the repair shortcut /
scheduled task, the install "ping", or self-updating Patch_OIS.bat.  Those need admin rights or
phone home, and are not part of replacing the libraries.

Steam's "Verify integrity of game files" puts the stock DLLs back; re-run the patcher to redo it.
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO_OWNER, REPO_NAME, REPO_BRANCH = "Voidless7125", "OIS-Update", "dev"
RAW_BASE = f"https://raw.githubusercontent.com/{REPO_OWNER}/{REPO_NAME}/{REPO_BRANCH}"
# OIS-Update keeps OpenAL32.dll in Git LFS (.gitattributes). raw.githubusercontent.com serves LFS files as a
# ~130 byte pointer, not the DLL, so each file is tried from the raw host first, then from the two hosts that
# do resolve LFS. Every attempt is checked against the manifest's SHA256, so a wrong answer is just rejected.
WEB_RAW_BASE = f"https://github.com/{REPO_OWNER}/{REPO_NAME}/raw/{REPO_BRANCH}"
MEDIA_BASE = f"https://media.githubusercontent.com/media/{REPO_OWNER}/{REPO_NAME}/{REPO_BRANCH}"
DOWNLOAD_SOURCES = (RAW_BASE, WEB_RAW_BASE, MEDIA_BASE)
ENV_PACKAGE_DIR = "OIS_UPDATE_DIR"
PACKAGE_DIRNAMES = ("OIS-Update", "OIS-Update-dev")      # where a local package is looked for
CACHE_DIRNAME = PACKAGE_DIRNAMES[0]                      # where a download is kept
BACKUP_DIRNAME = "oisbugfix_original_dlls"
VERSION_MARKER_NAME = "OIS_Update.version.txt"
GAME_MANIFEST_NAME = "OIS_Update.manifest.txt"
STATE_NAME = "oisbugfix_dll_update.json"
MAX_DOWNLOAD_BYTES = 64 * 1024 * 1024
HERE = Path(__file__).resolve().parent

# Files earlier releases of the package put in the game folder that the current release no
# longer needs (OIS-Update SECURITY.md, "Removed outright").  Patch_OIS.bat only deletes what an
# obsolete.txt lists, and the repository has none, so on its own it leaves these behind.  Here they
# are removed only when the file still matches what the package itself installed earlier.
OBSOLETE = ("libcrypto-3.dll", "libgcc_s_dw2-1.dll", "libiconv-2.dll", "libintl-8.dll", "libnghttp2-14.dll",
            "libpsl-5.dll", "libssl-3.dll", "libunistring-5.dll", "libwinpthread-1.dll", "libzstd.dll")

_SHA = re.compile(r"^[0-9a-f]{64}$")

# Network entry point, replaceable in tests.
_open_url = urllib.request.urlopen


# ---------------------------------------------------------------- small helpers

def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _safe_leaf(name):
    return bool(name) and name not in (".", "..") and not any(c in name for c in '/\\:*?"<>|')


def _safe_package_path(name):
    """`name` or `Original/name` -- nothing that could climb out of the package folder."""
    parts = name.split("/")
    return 1 <= len(parts) <= 2 and all(_safe_leaf(p) for p in parts)


def parse_manifest(text):
    """[(scope, sha256, name)] from a manifest.txt; malformed or unsafe lines are dropped."""
    out = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split(None, 2)
        if len(parts) != 3:
            continue
        scope, sha, name = parts[0].lower(), parts[1].lower(), parts[2].strip().replace("\\", "/")
        if scope not in ("game", "tool") or not _SHA.match(sha) or not _safe_package_path(name):
            continue
        if scope == "game" and "/" in name:           # game files are copied into the game root
            continue
        out.append((scope, sha, name))
    return out


def _manifest_version(text):
    m = re.search(r"^#\s*Version=(\S+)", text, re.M)
    return m.group(1) if m else "unknown"


class Package:
    def __init__(self, root, version, entries):
        self.root = Path(root)
        self.version = version
        self.game = [(n, s) for sc, s, n in entries if sc == "game"]
        self.tools = {n: s for sc, s, n in entries if sc == "tool"}

    def path(self, name):
        return self.root / name

    def original(self, name):
        """Verified path of the stock copy of `name` kept in the package's Original/ folder, or None."""
        rel = f"Original/{name}"
        p = self.path(rel)
        if rel in self.tools and p.is_file() and sha256_file(p) == self.tools[rel]:
            return p
        return None

    def has_original_folder(self):
        return (self.root / "Original").is_dir()


def load_package(root):
    root = Path(root)
    mf = root / "manifest.txt"
    if not mf.is_file():
        return None
    text = mf.read_text(encoding="utf-8", errors="replace")
    entries = parse_manifest(text)
    if not any(sc == "game" for sc, _, _ in entries):
        return None
    return Package(root, _manifest_version(text), entries)


def check_package(pkg):
    """(missing, wrong_hash) game file names."""
    missing, bad = [], []
    for name, sha in pkg.game:
        p = pkg.path(name)
        if not p.is_file():
            missing.append(name)
        elif sha256_file(p) != sha:
            bad.append(name)
    return missing, bad


_extra_search_dirs = []


def add_search_dir(path):
    """Also look for a local package inside `path` and next to it (the patcher adds the game folder, so an
    OIS-Update folder dropped into, or beside, the game folder is found even if the patcher lives elsewhere)."""
    p = Path(path).resolve()
    if p not in _extra_search_dirs:
        _extra_search_dirs.append(p)


def find_local_package():
    cands = []
    env = os.environ.get(ENV_PACKAGE_DIR)
    if env:
        cands.append(Path(env.strip().strip('"')))
    bases = [HERE, HERE.parent]
    for d in _extra_search_dirs:
        bases += [d, d.parent]
    for base in bases:
        cands.extend(base / n for n in PACKAGE_DIRNAMES)
    for c in cands:
        pkg = load_package(c) if c.is_dir() else None
        if pkg is not None:
            return pkg
    return None


# ---------------------------------------------------------------- download

def _download_bytes(url, limit=1 << 20):
    req = urllib.request.Request(url, headers={"User-Agent": "ois-patcher-dll-update"})
    with _open_url(req, timeout=30) as r:
        data = r.read(limit + 1)
    if len(data) > limit:
        raise ValueError(f"{url} is unexpectedly large")
    return data


def _download_file(url, dest, expected_sha):
    """Downloads to dest, but only keeps it if its SHA256 is `expected_sha`."""
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_name(dest.name + ".part")
    req = urllib.request.Request(url, headers={"User-Agent": "ois-patcher-dll-update"})
    h = hashlib.sha256()
    total = 0
    try:
        with _open_url(req, timeout=60) as r, open(part, "wb") as f:
            while True:
                chunk = r.read(1 << 18)
                if not chunk:
                    break
                total += len(chunk)
                if total > MAX_DOWNLOAD_BYTES:
                    raise ValueError("download is larger than any file in this package should be")
                h.update(chunk)
                f.write(chunk)
        if h.hexdigest() != expected_sha:
            raise ValueError("SHA256 does not match the manifest")
        os.replace(part, dest)
    finally:
        if part.exists():
            part.unlink()


def sync_from_github(root, log=print):
    """Makes `root` hold a complete, verified copy of the package's game files. Returns a Package or None."""
    root = Path(root)
    log(f"      Fetching manifest from github.com/{REPO_OWNER}/{REPO_NAME} (branch {REPO_BRANCH})...")
    try:
        mtext_raw = _download_bytes(f"{RAW_BASE}/manifest.txt")
    except (urllib.error.URLError, OSError, ValueError) as e:
        log(f"      [ERROR] Could not download the manifest: {e}")
        return None
    mtext = mtext_raw.decode("utf-8", errors="replace")
    entries = parse_manifest(mtext)
    game = [(n, s) for sc, s, n in entries if sc == "game"]
    if not game:
        log("      [ERROR] The downloaded manifest lists no game files.")
        return None
    root.mkdir(parents=True, exist_ok=True)
    fetched = 0
    for name, sha in game:
        dest = root / name
        if dest.is_file() and sha256_file(dest) == sha:
            continue
        log(f"      downloading {name} ...")
        err = None
        for base in DOWNLOAD_SOURCES:
            try:
                _download_file(f"{base}/{name}", dest, sha)
                err = None
                break
            except (urllib.error.URLError, OSError, ValueError) as e:
                err = e
        if err is not None:
            log(f"      [ERROR] {name}: {err}. Nothing was installed.")
            return None
        fetched += 1
    # kept so the folder is a normal local package afterwards (works offline, Original/ can be added)
    try:
        (root / "manifest.txt").write_bytes(mtext_raw)
        vt = _download_bytes(f"{RAW_BASE}/VERSION.txt")
        (root / "VERSION.txt").write_bytes(vt)
    except (urllib.error.URLError, OSError, ValueError):
        pass
    log(f"      Downloaded {fetched} file(s), {len(game) - fetched} already present.")
    return load_package(root)


def obtain_package(log=print, allow_download=True):
    pkg = find_local_package()
    if pkg is not None:
        missing, bad = check_package(pkg)
        if not missing and not bad:
            log(f"      Using local package {pkg.version} at {pkg.root}")
            return pkg
        log(f"      Local package at {pkg.root} is incomplete ({len(missing)} missing, {len(bad)} wrong hash).")
        if not allow_download:
            return None
        got = sync_from_github(pkg.root, log)
        return got if got and not any(check_package(got)) else None
    if not allow_download:
        return None
    return sync_from_github(HERE / CACHE_DIRNAME, log)


def describe_source():
    """One line for the prompt: where the files will come from. Never touches the network."""
    pkg = find_local_package()
    if pkg is not None:
        return f"local package {pkg.version} at {pkg.root} ({len(pkg.game)} files)"
    return (f"downloaded from github.com/{REPO_OWNER}/{REPO_NAME} (branch {REPO_BRANCH}), "
            f"about 25 MB, each file checked against the package's SHA256 manifest")


# ---------------------------------------------------------------- game folder state

def running_game_processes():
    if os.name != "nt":
        return []
    try:
        out = subprocess.run(["tasklist", "/FO", "CSV", "/NH"], capture_output=True, text=True, timeout=30).stdout.lower()
    except (OSError, subprocess.SubprocessError):
        return []
    return [n for n in ("ois.exe", "ois_server.exe") if f'"{n}"' in out]


def read_installed_manifest(game_dir):
    """{name: sha256} from OIS_Update.manifest.txt (written by Patch_OIS.bat or by this module)."""
    p = Path(game_dir) / GAME_MANIFEST_NAME
    out = {}
    if p.is_file():
        for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                parts = line.split(None, 1)
                if len(parts) == 2 and _SHA.match(parts[0].lower()) and _safe_leaf(parts[1].strip()):
                    out[parts[1].strip()] = parts[0].lower()
    return out


def load_state(game_dir):
    p = Path(game_dir) / STATE_NAME
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_state(game_dir, state):
    (Path(game_dir) / STATE_NAME).write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")


def _unblock(path):
    """Drops the Mark-of-the-Web stream (no-op anywhere but NTFS)."""
    try:
        os.remove(str(path) + ":Zone.Identifier")
    except OSError:
        pass


# ---------------------------------------------------------------- install

def install(game_dir, log=print, package=None):
    """Applies the update to `game_dir`. Returns True when every file verified."""
    game_dir = Path(game_dir)
    log("      Locating the update package...")
    pkg = package or obtain_package(log)
    if pkg is None:
        log("      [ERROR] No usable update package; DLLs were not changed.")
        return False
    missing, bad = check_package(pkg)
    if missing or bad:
        log(f"      [ERROR] The package is damaged (missing: {missing or 'none'}, wrong hash: {bad or 'none'}).")
        return False
    running = running_game_processes()
    if running:
        log(f"      [ERROR] {', '.join(running)} is running. Close it and run the patcher again; DLLs were not changed.")
        return False

    prior = read_installed_manifest(game_dir)
    state = load_state(game_dir)
    backup_dir = game_dir / BACKUP_DIRNAME
    new_hash = dict(pkg.game)
    backed_up = set(state.get("backed_up", []))
    created = set(state.get("created", []))
    replaced = set(state.get("replaced", []))

    def backup_once(name):
        src = game_dir / name
        dst = backup_dir / name
        if dst.exists() or not src.is_file():
            return
        known = {prior.get(name), new_hash.get(name)} - {None}
        if sha256_file(src) in known:                    # already an updated copy, not an original
            return
        backup_dir.mkdir(exist_ok=True)
        shutil.copy2(src, dst)
        backed_up.add(name)

    def put(src, name):
        dst = game_dir / name
        tmp = game_dir / (name + ".oistmp")
        try:
            shutil.copyfile(src, tmp)
            os.replace(tmp, dst)
        finally:
            if tmp.exists():
                tmp.unlink()
        _unblock(dst)

    try:
        # 1. files an earlier release installed that this one no longer ships
        obsolete = list(OBSOLETE)
        ot = pkg.path("obsolete.txt")
        if ot.is_file():
            obsolete += [l.strip() for l in ot.read_text(encoding="utf-8", errors="replace").splitlines()
                         if l.strip() and not l.startswith("#")]
        for name in dict.fromkeys(obsolete):
            p = game_dir / name
            if _safe_leaf(name) and p.is_file() and name in prior and sha256_file(p) == prior[name]:
                log(f"      Removing obsolete {name} (installed by an earlier package release)...")
                backup_dir.mkdir(exist_ok=True)
                if not (backup_dir / name).exists():
                    shutil.copy2(p, backup_dir / name)
                    backed_up.add(name)
                p.unlink()
        for name in sorted(set(prior) - set(new_hash) - set(obsolete)):
            if not (game_dir / name).is_file():
                continue
            orig = pkg.original(name)
            if orig is not None:
                log(f"      Restoring stock {name} (no longer patched)...")
                backup_once(name)
                put(orig, name)
                replaced.add(name)
            else:
                log(f"      Note: {name} is no longer patched; leaving the existing copy alone.")

        # 2. copy the new files
        copied = 0
        for name, sha in pkg.game:
            dst = game_dir / name
            if dst.is_file() and sha256_file(dst) == sha:
                continue
            if not dst.is_file() and name not in prior:
                created.add(name)
            backup_once(name)
            put(pkg.path(name), name)
            replaced.add(name)
            copied += 1
        log(f"      Copied {copied} file(s), {len(pkg.game) - copied} already current.")
    except OSError as e:
        log(f"      [ERROR] {e}. Make sure the game is closed and you have write access to the game folder.")
        state.update(backed_up=sorted(backed_up), created=sorted(created), replaced=sorted(replaced))
        save_state(game_dir, state)
        return False

    # 3. verify what is actually in the game folder
    wrong = [n for n, s in pkg.game if not (game_dir / n).is_file() or sha256_file(game_dir / n) != s]
    if wrong:
        log(f"      [ERROR] These files in the game folder do not match the package: {', '.join(wrong)}")
        return False
    log(f"      Verified {len(pkg.game)} file(s) by SHA256.")

    # 4. markers (same format as Patch_OIS.bat) and our own record
    stamp = time.strftime("%a %m/%d/%Y %H:%M:%S")
    (game_dir / VERSION_MARKER_NAME).write_text(
        "\n".join(["OIS Community Patch", f"Version={pkg.version}", f"Files={len(pkg.game)}",
                   f"Installed={stamp}", f"Source={pkg.root}", "Script=ois_patcher.py (dll_update.py)"]) + "\n",
        encoding="utf-8")
    (game_dir / GAME_MANIFEST_NAME).write_text(
        "\n".join(["# OIS Community Patch installed manifest", f"# Version={pkg.version}", f"# Installed={stamp}",
                   f"# Package={pkg.root}", "# Format: <sha256> <filename>"] + [f"{s} {n}" for n, s in pkg.game]) + "\n",
        encoding="utf-8")
    save_state(game_dir, {"version": pkg.version, "installed": dict(pkg.game),
                          "backed_up": sorted(backed_up), "created": sorted(created),
                          "replaced": sorted(replaced)})
    log(f"      Pre-update originals kept in {backup_dir}")
    log("      Steam's \"Verify integrity of game files\" reverts these DLLs; re-run the patcher to reapply.")
    return True


# ---------------------------------------------------------------- status / uninstall

def status_lines(game_dir):
    game_dir = Path(game_dir)
    state = load_state(game_dir)
    marker = game_dir / VERSION_MARKER_NAME
    if not state:
        if marker.is_file():
            ver = next((l.split("=", 1)[1] for l in marker.read_text(errors="replace").splitlines()
                        if l.startswith("Version=")), "?")
            return [f"  {'DLL update':<16} installed by Patch_OIS.bat (version {ver}); not tracked by this script"]
        return [f"  {'DLL update':<16} not installed"]
    files = state.get("installed", {})
    ok = sum(1 for n, s in files.items() if (game_dir / n).is_file() and sha256_file(game_dir / n) == s)
    line = f"  {'DLL update':<16} version {state.get('version', '?')}, {ok}/{len(files)} file(s) match"
    if ok != len(files):
        line += "  (Steam may have reverted some; re-run the patcher)"
    return [line]


def uninstall_plan(game_dir):
    state = load_state(game_dir)
    if not state:
        return []
    return [f"restore the original DLLs ({len(state.get('installed', {}))} updated file(s)) from "
            f"{BACKUP_DIRNAME}/ and remove DLLs the update added"]


def uninstall(game_dir, keep_backups=False, log=print):
    game_dir = Path(game_dir)
    state = load_state(game_dir)
    if not state:
        return True
    backup_dir = game_dir / BACKUP_DIRNAME
    local = find_local_package()
    ok, unresolved = True, []
    backed_up, created = set(state.get("backed_up", [])), set(state.get("created", []))
    names = sorted(set(state.get("replaced", [])) | backed_up | created)
    for name in names:
        dst = game_dir / name
        bak = backup_dir / name
        try:
            if bak.is_file():
                shutil.copy2(bak, dst)
                log(f"  [OK] restored {name} from backup")
            elif local is not None and local.original(name) is not None:
                shutil.copy2(local.original(name), dst)
                log(f"  [OK] restored stock {name} from the package's Original/ folder")
            elif name in created or (local is not None and local.has_original_folder()
                                     and f"Original/{name}" not in local.tools):
                if dst.is_file():
                    dst.unlink()
                log(f"  [OK] removed {name} (not part of the stock game)")
            else:
                unresolved.append(name)
        except OSError as e:
            log(f"  [ERROR] {name}: {e}")
            ok = False
    if unresolved:
        log(f"  [WARN] no original copy of {', '.join(unresolved)}; use Steam's \"Verify integrity of game files\".")
        ok = False
    for marker in (VERSION_MARKER_NAME, GAME_MANIFEST_NAME, STATE_NAME):
        try:
            (game_dir / marker).unlink()
        except OSError:
            pass
    if not keep_backups and ok and backup_dir.is_dir():
        shutil.rmtree(backup_dir, ignore_errors=True)
    return ok
