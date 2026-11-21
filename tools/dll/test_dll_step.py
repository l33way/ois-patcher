"""ois_patcher's optional DLL step, offline, on a scratch game folder with a fake OIS-Update package.

    python3 tools/dll/test_dll_step.py

Cases: no package + decline / non-interactive / --no-dll-update / a download with wrong bytes is refused /
download accepted and applied last / already current / uninstall restores the original bytes / package on disk
(asks to update, not to download) / damaged local package repaired from the download.
"""
import builtins, hashlib, io, os, shutil, sys, tempfile
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import dll_update, ois_patcher as op


def sha(b): return hashlib.sha256(b).hexdigest()
def fsha(p): return sha(Path(p).read_bytes())


def run(fn, *a, answer=None, tty=False, **k):
    asked, buf = [], io.StringIO()
    class In(io.StringIO):
        def isatty(self): return tty
    old_in, old_input = sys.stdin, builtins.input
    sys.stdin = In()
    builtins.input = lambda prompt="": (asked.append(prompt), answer)[1]
    try:
        with redirect_stdout(buf):
            r = fn(*a, **k)
    finally:
        sys.stdin, builtins.input = old_in, old_input
    return r, buf.getvalue(), asked


class FakeResp(io.BytesIO):
    def __enter__(self): return self
    def __exit__(self, *a): return False


def main():
    tmp = Path(tempfile.mkdtemp())
    try:
        game = tmp / "game"; game.mkdir()
        names = ["OpenAL32.dll", "fmod.dll", "zlib1.dll"]
        old = {n: (n.encode() + b"-2018") * 40 for n in names}
        new = {n: (n.encode() + b"-2026") * 40 for n in names}
        for n in names: (game / n).write_bytes(old[n])
        orig = {n: fsha(game / n) for n in names}
        manifest = "# Version=2099.01.01.1\n" + "".join(f"game {sha(new[n])} {n}\n" for n in names)
        served = {f"{base}/{n}": new[n] for base in dll_update.DOWNLOAD_SOURCES for n in names}
        served[f"{dll_update.RAW_BASE}/manifest.txt"] = manifest.encode()
        tamper = {"on": False}
        def fake_open(req, timeout=0):
            url = req.full_url
            if url not in served:
                raise OSError("404 " + url)
            return FakeResp(b"tampered" if tamper["on"] and not url.endswith("manifest.txt") else served[url])
        dll_update._open_url = fake_open
        dll_update.running_game_processes = lambda: []
        dll_update.HERE = tmp / "patcher"; dll_update.HERE.mkdir()
        os.environ.pop(dll_update.ENV_PACKAGE_DIR, None)
        dll_update._extra_search_dirs.clear()
        cache = dll_update.HERE / dll_update.CACHE_DIRNAME
        cur = lambda: {n: fsha(game / n) for n in names}
        newh = {n: sha(new[n]) for n in names}

        _, out, asked = run(op.dll_begin, game, None, answer="n", tty=True)
        assert len(asked) == 1 and "Download" in asked[0] and not op._DLL["go"]
        assert not cache.exists() and cur() == orig

        _, out, asked = run(op.dll_begin, game, None, tty=False)
        assert not asked and not op._DLL["go"] and "--dll-update" in out

        _, out, asked = run(op.dll_begin, game, False, tty=True)
        assert not asked and not out.strip()

        tamper["on"] = True
        _, out, asked = run(op.dll_begin, game, None, answer="y", tty=True)
        assert len(asked) == 1 and not op._DLL["go"], out
        run(op.dll_apply, game)
        assert cur() == orig, "installed unverified bytes"
        shutil.rmtree(cache, ignore_errors=True)
        tamper["on"] = False

        _, out, asked = run(op.dll_begin, game, None, answer="y", tty=True)
        assert op._DLL["go"] and cache.is_dir(), out
        assert cur() == orig, "changed before the apply step"
        run(op.dll_apply, game)
        assert cur() == newh
        assert (game / dll_update.BACKUP_DIRNAME / "fmod.dll").read_bytes() == old["fmod.dll"]
        assert "applied" in run(op.dll_summary_lines)[0][0]
        st = "\n".join(run(op.dll_status_lines, game)[0]); assert "2099.01.01.1" in st and "3/3" in st, st
        assert run(op.dll_uninstall_plan, game)[0]

        _, out, asked = run(op.dll_begin, game, None, answer="y", tty=True)
        assert not asked and "nothing to do" in out and not op._DLL["go"]

        ok, out, _ = run(op.dll_uninstall, game)
        assert ok and cur() == orig, out
        assert not (game / dll_update.STATE_NAME).exists()

        shutil.rmtree(game / dll_update.BACKUP_DIRNAME, ignore_errors=True)
        _, out, asked = run(op.dll_begin, game, None, answer="n", tty=True)
        assert len(asked) == 1 and "Download" not in asked[0] and "2099.01.01.1" in out
        _, out, asked = run(op.dll_begin, game, True, tty=False)
        assert not asked and op._DLL["go"]
        run(op.dll_apply, game)
        assert cur() == newh
        run(op.dll_uninstall, game)

        (cache / "fmod.dll").write_bytes(b"corrupt")
        _, out, asked = run(op.dll_begin, game, True, tty=False)
        assert "incomplete or altered" in out and op._DLL["go"], out
        run(op.dll_apply, game)
        assert cur() == newh
        print("DLL step: all checks passed")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


main()
