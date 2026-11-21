# Security notes

This is a hobby project by players, for players. It is not a security product and nothing here is audited. This page
says what the patcher touches, what it never touches, and one thing worth knowing about the game itself.

## What the patcher does to your computer

- **Edits files in your game folder only:** `ois.exe`, `ois_server.exe`, text files under `assets/` and the `oisbugfix` mod
  folder. Before it changes the exes it saves `.original-backup` copies, and `--uninstall` puts everything back.
- **Needs no admin rights** unless your game sits somewhere Windows protects (for example Program Files), in which case it
  tells you the write failed.
- **Stays off the network by default.** The only things that can touch the internet are the update check (if you cloned this with
  git, it asks GitHub whether there is a newer patcher and asks before pulling it) and the optional DLL update below, which asks
  first.
- **Does not install firewall rules, scheduled tasks or shortcuts**, and does not phone home.
- **Is plain Python you can read.** It is a script rather than a pre-patched `ois.exe` so you can see every byte it changes,
  and so no copy of the game (which belongs to Flat Earth Games) is ever shared. Each fix is checked against the exact bytes
  it expects, and is skipped, not forced, on a game version it does not recognise.

## Why the optional DLL update exists

Objects in Space 1.0.8 was built in 2018 with the libraries of the day, for example cURL 7.52.1, zlib 1.2.5, SQLite 3.7.15,
libtiff 4.0.3 and OpenAL 1.16. Libraries that old have had many security fixes since. The game cannot be recompiled, but most of
these are separate DLLs that can be swapped for newer builds, which is what the
[OIS-Update](https://github.com/Voidless7125/OIS-Update) package does (it has the full version table and the reasoning). The
patcher can apply that package for you: if it finds an `OIS-Update` folder it offers to use it, and if not it offers to download
it (about 25 MB). It is always your choice, and nothing is downloaded without a yes.

What the patcher does when you say yes, the same as `Patch_OIS.bat` does minus the extras:

1. Checks every file against the package's `manifest.txt` (SHA256) and refuses anything that does not match.
2. Backs up each DLL it replaces to `oisbugfix_original_dlls/` (the first backup is kept as the true original).
3. Copies the new DLLs, re-checks them, and removes a few leftovers of older package releases.
4. `--status` shows the installed DLL version, and `--uninstall` puts the originals back.

What it leaves out: the optional Windows Firewall rules, the repair shortcut and the install ping from `Patch_OIS.bat`. If you want
those, run `Patch_OIS.bat` from the OIS-Update package yourself.

Things to be honest about:

- The newer DLLs are a bigger change than a typo fix. FMOD 2.0 in particular is a major version jump over the 1.x the game
  shipped with, so if audio misbehaves afterwards, run `--uninstall` (or Steam's "Verify integrity of game files") to get the
  stock libraries back.
- Steam's "Verify integrity of game files" puts the old DLLs back. Run the patcher again to reapply.
- One library, `libwebsockets` (used for multiplayer), cannot be brought fully up to date without the game's source. The
  OIS-Update package explains this and suggests firewall rules for it.
- The download step trusts the OIS-Update repository on GitHub, as far as a SHA256 manifest served from the same place can
  protect you. If you would rather not, download the package yourself, read it, and put the folder next to the patcher.

## What the patcher does not cover

This project is an unofficial community patch. It does not fix, and makes no promises about, security problems in the base game or
its network protocol. Playing someone else's co-op server is as risky as it was before.

## Reporting a problem

If you find a problem in the patcher itself (for example it writes somewhere it should not), please use GitHub's private
vulnerability reporting on this repository or contact the maintainers directly rather than opening a public issue. Anything
else is a normal [issue](https://github.com/l33way/ois-patcher/issues).
