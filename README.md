# Objects in Space — Unofficial Bugfix Patch

**Credit:** Leeway ([steamcommunity.com/id/l33way](https://steamcommunity.com/id/l33way/))

An unofficial bugfix patch for *Objects in Space*, an incredible (but
sadly abandoned) space-stealth game by Flat Earth Games. Fixes several
crashes and one long-standing spam bug, and adds a small mail-terminal
feature.

This is a community patch, not an official release. Use at your own
discretion — a backup of your original `ois.exe` and `ois_server.exe`
(the co-op server binary, which ships alongside `ois.exe` in every
Windows Steam install) is made automatically before anything is touched
(see below).

## Why I built this

*Objects in Space* is a genuine work of art. It just never got finished.
This patch is my attempt to change that — fixing what's broken, so it
can be closer to what it was meant to be.

## Goal: restoring original intent, not adding new features

Every fix in this patch exists because something the developers clearly
intended to work is instead broken, unreachable, or crashes. The scope
is deliberately narrow: **restore the game to the state it evidently was
meant to ship in — not redesign it, rebalance it, or extend it.**

In practice, that means:

- **A typo, a missing bounds-check, a leaked resource handle,
  an identifier one character too long for a fixed-size
  buffer** — these are unambiguous bugs. Restoring the evidently
  intended behavior is squarely in scope.
- **Deliberate design choices are left alone, even ones that feel
  restrictive or arbitrary.** If something is disabled by a hardcoded
  developer list rather than broken by accident, that's a design
  decision, not a bug — no matter how tempting a "fix" might be. (One
  investigated example: LADAR modules turned out to be intentionally
  excluded from the in-game shop's purchase list, confirmed via
  disassembly of the actual filter the developers wrote — not a data
  bug, not touched by this patch.)
- **When a fix can't be pinned to a specific, proven original
  behavior, this README says so plainly instead of presenting a guess
  as a restoration.** One fix below (the mail-terminal `DEL` command)
  was already broken — it only crashed, and never actually did
  anything — before this patch, so there was no working original
  behavior to restore. That entry is marked as a best-effort
  interpretation of what the surrounding code seemed to be reaching
  for, not a confirmed restoration, so you can judge it accordingly.
- **Nothing here touches economy, difficulty, or content balance.**
  Every fix corrects something that was never supposed to happen in the
  first place, not something the developers shipped on purpose but that
  plays out unfavorably.

None of this is a judgment against going further — it's just not what
*this* patch is for. If someone wants to build a rebalance, a difficulty
overhaul, new content, or anything else on top of what's fixed here, I
fully support that effort. This code is here to be built on for exactly
that kind of work, within the terms of the license below.

## Why a Python script instead of a pre-patched `ois.exe`?

This patch is distributed as source — a script you run against your own
copy of the game — rather than as an already-patched `ois.exe` you'd
just drop in. That's a deliberate choice, not a convenience shortcut:

- **Visibility.** You can read exactly what the patcher does before you
  run it: every patch site, every byte it checks and changes, every
  file it copies. A pre-built exe hides all of that behind an opaque
  binary diff.
- **External verification.** Anyone can independently check the
  patcher's claims against the real game binary — disassemble the
  patch sites, confirm the before/after bytes, verify nothing beyond
  what's documented here actually changes. That's not practical against
  a binary you're just told is safe.
- **Lower security risk.** A modified game executable from an
  unofficial source is exactly the kind of thing that's easy to hide
  something unwanted inside. A plain, readable script that only ever
  touches the specific bytes it prints and explains is a much smaller,
  much more inspectable trust surface — you (or anyone else) can verify
  it does only what it says, instead of taking a stranger's binary on
  faith.

The same reasoning is why the data-only fixes (see `apply_data_fixes.py`
below) aren't shipped as ready-made files either — they're generated
from your own game install at run time, so this repo never bundles a
copy of Flat Earth Games' own content.

## What's in this folder

Only one file here is ever run directly — the other two are support
files it needs sitting alongside it. **All three must stay together in
this same folder structure** (don't move or rename them individually):

- **`ois_patcher.py`** — **this is the one you actually run.** A single
  invocation locates your game, patches `ois.exe` and `ois_server.exe`,
  and generates and installs the bugfix mod, all in one pass (see
  "Installation" below).
- `apply_data_fixes.py` — not something you run yourself. `ois_patcher.py`
  imports and calls it automatically to build the data-only fixes
  (typo/data corrections, generated fresh from *your own* `assets/`
  folder rather than shipped as ready-made files — see the file's own
  header for why).
- `mod/oisbugfix/` — a folder, not a single file. Contains `modinfo.txt`
  (this mod's own metadata, original content). `apply_data_fixes.py`
  fills in the rest of this folder's contents at install time; keep the
  folder itself intact and in place.

## Requirements

- **Python 3.8 or newer.**
  - **Check if you already have it:** open a terminal (see step 2 under
    "Installation" below for how) and run `python --version`. If that
    prints something like `Python 3.11.4`, you're set — skip ahead to
    Installation.
  - **If it's not found, install it:** go to
    [python.org/downloads](https://www.python.org/downloads/), download
    the Windows installer, and run it. **On the installer's very first
    screen, check the box "Add python.exe to PATH"** before clicking
    Install — this is the single most commonly-missed step, and without
    it none of the commands below will work. (Don't install Python from
    the Microsoft Store instead — it uses a different mechanism that
    can behave inconsistently for a script like this one.)
  - **After installing,** close any terminal window you already had
    open and open a new one (a terminal opened before installing Python
    won't see the update), then confirm it worked with `python --version`
    again.
- **The `pefile` package.** Once Python itself is installed, open a
  terminal and run:

  ```
  pip install pefile
  ```

  `pip` comes bundled with Python when installed from python.org, so
  this should just work right after the step above. If `pip` also isn't
  recognized, try `py -m pip install pefile` instead (see the `py`
  launcher note under Troubleshooting below).
- **`git` (optional).** Only needed if you want the patcher to check for
  and pull its own updates from a `git clone` of this repo (see
  "Checking for updates" below). Not required for anything else — a
  plain downloaded-and-unzipped copy works fine for patching, checking
  status, and uninstalling; the patcher just won't be able to update
  itself and will say so.

## Installation

**1. Download and unzip the patcher.** Get the latest release from the
[GitHub repo](https://github.com/l33way/ois-patcher) — either the
Releases page, or the green "Code → Download ZIP" button — then extract
it: right-click the downloaded `.zip` file in File Explorer and choose
"Extract All...". Don't try to run anything straight out of the zip;
extract it to a real folder first. `ois_patcher.py`, `apply_data_fixes.py`,
and the `mod/oisbugfix/` folder (see "What's in this folder" above) all
need to end up together in that one extracted folder.

(If you'd rather clone the repo with `git` instead of downloading a
zip, that works too — and it's what lets the patcher check for and pull
its own updates later. See "Checking for updates" below.)

**2. Open a terminal in that folder.** In File Explorer, open the
folder you just extracted (the one containing `ois_patcher.py`), then
either type `cmd` into the address bar and press Enter, or
Shift+right-click empty space in the folder and choose "Open PowerShell
window here" / "Open in Terminal."

**3. Run this one command:**

```py
python ois_patcher.py
```

That's it — no path required. The patcher looks for your game the same
way Steam and GOG themselves would: Steam's own registry entries and
default install folders, every Steam library (including ones on other
drives), and GOG's registry records, in that order. If it finds exactly
one install, it uses it and tells you which one. If it finds more than
one, it lists all of them and asks which to patch — nothing is ever
silently picked for you between two installs. If it can't find one at
all, it asks you to paste the path.

If you'd rather point it at a specific copy yourself — say, you have
more than one install and want to skip the prompt, or auto-detection
doesn't find yours for some reason — you can still give it the path
explicitly, same as before:

```py
python ois_patcher.py "C:\Path\To\Objects in Space\ois.exe"
```

or, equivalently:

```py
python ois_patcher.py --game-dir "C:\Path\To\Objects in Space"
```

- Either the folder itself or the `ois.exe` inside it works — the
  patcher figures out which you gave it.
- **Keep the quotes around the path.** The default Steam install path
  contains a space (`Objects in Space`), and an unquoted path with a
  space in it will fail or silently target the wrong thing.
- A typical default path looks like:
  `C:\Program Files (x86)\Steam\steamapps\common\Objects in Space\ois.exe`
- Running it repeatedly with an environment variable instead — say,
  from your own script — is also supported: set `OIS_TARGET_DIR` to
  your install folder and just run `python ois_patcher.py` with no
  argument. An explicit path or `--game-dir` always overrides it.

**That's it — one command, one run.** You do not need to run
`apply_data_fixes.py` yourself, and there is no separate mod-install
step: the single command above does everything described below
automatically, in order:

1. Finds your game install (auto-detected, or the path you gave it).
2. Backs up your original `ois.exe` as `ois.exe.original-backup`
   (created once — running the patcher again reuses the existing
   backup rather than overwriting it).
3. Applies the binary fixes listed below, in place.
4. Backs up and patches `ois_server.exe` the same way — it ships
   alongside `ois.exe` in every Windows Steam install and is needed for
   hosting/joining co-op games (singleplayer never runs it, but it's
   still there). Its own separate backup, checked and skipped just as
   safely if anything doesn't match. If it's genuinely missing (e.g. a
   modified install), this step is skipped quietly rather than erroring.
5. Generates and installs the `oisbugfix` mod into
   `ObjectsInSpace/mods/oisbugfix/`, reading the affected files fresh
   out of your own `assets/` folder.

**4. Check the summary printed at the end.** A successful run ends with
a block like:

```
Applied 9 exe fix(es), skipped 0.
ois_server.exe: applied 2 fix(es), skipped 0.
Bugfix mod: installed
```

If anything shows as skipped, scroll up — the patcher explains exactly
why (usually a different game version, or something already patched).
Skipped items don't stop the rest of the run; every other fix still
applies normally.

Every patch checks the exact bytes it's about to change first, and
skips itself with a warning (rather than guessing) if anything doesn't
match — a different game version, or a file already modified some other
way. It's safe to re-run against an *unpatched* backup at any time.

### Checking what's installed

```py
python ois_patcher.py --status
```

Reports, for your detected (or given) install: whether each exe is
patched and by which version, whether its backup is present and usable,
and whether the bugfix mod is installed. Doesn't check for updates and
doesn't change anything — safe to run any time out of curiosity.

### Updating

Running `python ois_patcher.py` again picks this up on its own — no
separate command needed:

- **Already at the current version:** the exe(s) are left alone, and
  only the data-only mod is refreshed (handy if you ever deleted the
  `oisbugfix` folder by hand and want it back without touching the exe).
- **Patched by an older version of this tool:** you'll be asked to
  confirm, then the patcher restores the original from
  `<name>.original-backup` and re-applies the current fixes on top of
  that clean original — never on top of an already-patched file. Your
  existing backup is kept and reused; nothing is re-downloaded or
  re-copied for this.
- **Patched by a newer version than the copy of the script you're
  running:** the patcher refuses, rather than downgrading you. Get the
  current release and run that instead (see "Checking for updates for
  the patcher itself" below), or pass `--force` if you genuinely want
  to go backward.

You can also force a from-scratch re-patch even when already current
with `--force`, and skip all the "are you sure?" prompts (for scripted
or unattended runs) with `--yes`.

### Checking for updates for the patcher itself

If you got this patcher via `git clone` (rather than a downloaded zip),
a plain `python ois_patcher.py` run also checks whether a newer version
of the *script itself* is available upstream, before it does anything
to your game:

- If your checkout is current, it says so and moves straight on to
  patching.
- If an update is available, it shows what's changed and asks before
  doing anything — this never pulls new code without your say-so, even
  if you passed `--yes` (that only answers the game-patching prompts).
  Say yes with `--update` on the command line to skip that ask (e.g.
  for a scripted update-and-patch run), or decline and it just patches
  with the version you already have.
- If you pulled a newer version, the patcher restarts itself
  automatically to make sure the new code is actually the code that
  runs — you don't need to re-run anything yourself.
- If you downloaded a zip instead of cloning with git, or if `git`
  itself isn't installed, this check is skipped automatically and
  patching proceeds normally with your local copy. Check the
  [GitHub repo](https://github.com/l33way/ois-patcher) yourself now and
  then if you want to know about new releases.

Skip this check entirely (e.g. if you're offline and don't want the
delay) with `--no-update-check`.

### Troubleshooting

- **Double-clicking `ois_patcher.py` makes a window flash and
  disappear instantly.** This usually means Windows closed the console
  before you could read what happened — auto-detection may have needed
  to ask you a question (which one of several installs, or a path to
  paste) that a double-click can't answer. Run it from a terminal
  instead, as shown above, so you can see and respond to any prompts.
- **`'python' is not recognized...`, or a Microsoft Store page opens
  when you try to run it.** Python isn't installed, or isn't on your
  system's PATH. Install it from
  [python.org/downloads](https://www.python.org/downloads/) (not the
  Microsoft Store version, which can behave differently on Windows) —
  and make sure to check **"Add python.exe to PATH"** on the installer's
  first screen. If Python is already installed this way and `python`
  still doesn't work, try `py` in its place (Windows' own Python
  launcher, installed alongside python.org's Python) — e.g.
  `py ois_patcher.py`.
- **`ModuleNotFoundError: No module named 'pefile'`.** You're missing
  the one required package — run `pip install pefile` (or
  `py -m pip install pefile`) in a terminal, then try again.
- **"Could not automatically find the game folder."** Auto-detection
  covers standard Steam and GOG installs; an unusual setup (a
  non-default GOG install path, a Steam library it couldn't see, a
  storefront other than Steam/GOG) can miss yours. Paste the path when
  asked, or run it with the path directly:
  `python ois_patcher.py "C:\Path\To\Objects in Space"`.
- **It found more than one install and I don't recognize one of
  them.** Old installs (a previous drive, an old Steam library you
  haven't cleaned up, a leftover GOG copy) can still show up here even
  if you don't play from them anymore. Pick the one you actually use;
  the others are just left alone.
- **It says some fixes were "skipped."** Scroll up in the output — the
  patcher always explains why (usually a different game version than
  this patch targets, 1.0.8, or that file already having been patched
  by an earlier run). This is expected, safe behavior, not a failure —
  every other fix still applies normally.

Still stuck? Open an issue on the
[GitHub repo](https://github.com/l33way/ois-patcher/issues) with what
you tried and exactly what you saw.

### Reverting

```py
python ois_patcher.py --uninstall
```

Run against your detected (or given) install, this puts the game folder
back the way it was: restores `ois.exe` and `ois_server.exe` from their
`.original-backup` files (each one verified to be a genuine pristine
original before it's used, and the restore itself verified byte-for-byte
after writing), and removes the `oisbugfix` folder from
`ObjectsInSpace/mods/`. Asks for confirmation first, showing exactly
what it's about to do; add `--yes` to skip that if you're scripting it.
Your save games and every other game file are left untouched.

By default the `.original-backup` files are deleted once they've been
successfully restored from (their job is done). Pass `--keep-backups`
if you'd rather they stick around.

If you'd prefer to do it by hand instead, that still works exactly as
before:

- **Client exe:** copy `ois.exe.original-backup` back over `ois.exe`.
- **Server exe:** if `ois_server.exe.original-backup` exists, copy it back
  over `ois_server.exe` the same way.
- **Mod:** delete the `oisbugfix` folder from `ObjectsInSpace/mods/`.

## Fixes included

- **Pirate Hunt scenario crash** — two independent causes, both fixed on
  both `ois.exe` and `ois_server.exe`: a missing bounds-check in the
  ship spawn-selection loop, and a separate log
  call with too few arguments for its own format string a little
  further down the same code path. Either one alone can crash the
  game/server during ship spawning; the server binary has the
  identical bugs and crashes the same way for anyone hosting or
  joining a co-op game.
- **Music player permanent failure loop** — the music player leaked a
  sound-engine handle on every track change; eventually the pool was
  exhausted and music stopped for the rest of the session.
- **Ship steering recompute spam** (three separate causes) — ships were
  recomputing and re-logging their course correction up to ~125
  times/second in bursts, instead of only when their course actually
  changed. Real wasted CPU work, not just log noise.
- **Mail/PC terminal `DEL` command crash** — typing `DEL <name>` crashed
  the game for almost any input. Also adds the feature this crash was
  found while chasing: `DEL` can now genuinely delete an unprotected
  command ("Deleted.") but refuses a protected one ("cannot delete
  system file"). Confirmed to never touch your save data — a deleted
  command comes back automatically the next time you leave and
  re-enter the Communications room, load a save, or restart the game.
  This one's a bit different from the others: the functionality was
  already broken (it just crashed instead of doing anything), so there
  was no working original behavior to restore. I wasn't sure what the
  developers actually intended here — the fix is my best attempt at
  following what the surrounding code seemed to be reaching for, not a
  restoration of something proven.
- **Co-op scenario "Escort: Make a Break" fails to load** — a one-character
  typo in a scenario file made it silently unloadable. (Mod-only fix, no
  exe patch needed.)
- **"CLASH between additions" log spam** — background NPCs' data files
  listed a hairstyle after a helmet in the same character-cosmetics
  list, so the (already-correctly-rejected) hairstyle logged a noisy
  error every boot. Purely a log fix — those items were never actually
  shown. (Mod-only fix, no exe patch needed.)
- **"unknown mesh" error for a specific beard style** — a one-field typo
  in a character-cosmetics data file shifted every value after it,
  breaking the mesh lookup for background NPCs wearing a particular
  beard. (Mod-only fix, no exe patch needed.)
- **"Unknown room" log spam cycling past a ship's last room** — the
  room-lookup function logged an error on every miss, even though the
  room-cycling code already correctly handles reaching the end of the
  list; mashing "next room" there just re-triggered the log every
  press.
- **Rare crash opening the PDA while a character's portrait is
  mid-render** — a race between two rendering operations in the
  game's engine could crash the game if the PDA/tablet was opened at
  the exact wrong instant. Fixed by ignoring the "open PDA" key press
  for that instant instead — press it again a moment later and it
  opens normally.
- **GRA 5 grappling arm installs broken and unsellable** — its data was
  missing 8 of 10 components whenever a shop rolled it in Stealth or
  Low Power Use condition. (Mod-only fix, no exe patch needed.)
- **6 LADAR modules show every component in the wrong repair-screen
  slot** (`MKX-LADAR-A-2`, `MKX-LADAR-A-T`, `MTL-C100`, `MTL-C150`,
  `MTL-CC`, `TBL-B42`) — a stray extra value in their configuration
  data shifted every real component one slot off from where it's
  actually declared. (Mod-only fix, no exe patch needed.)
- **`MKX-LADAR-A-2`/`MKX-LADAR-A-T` crash the game on equip** — their
  identifiers were exactly one character too long for a fixed-size
  network packet field; the resulting mangled identifier failed to
  resolve with no fallback. Fixed by shortening both ids. (Mod-only
  fix, no exe patch needed.)

## Limitations

Only tested against the **Windows Steam** build of `ois.exe` and
`ois_server.exe` (game version 1.0.8, the last Steam release before the
developers stopped supporting it). Every patch site checks its exact
bytes before changing anything and skips itself with a warning rather
than guessing, so running this against a different build should fail
safely rather than corrupt anything — but it hasn't been verified
against GOG, other storefronts, other game versions, or non-Windows
builds, if any exist. Auto-detection can *locate* a GOG install, but the
binary fixes themselves are only confirmed against the Steam 1.0.8
build either way — the same "check first, skip safely if it doesn't
match" behavior applies regardless of where the exe came from.

## Limitation of liability

This patch is provided "as is," with no warranty of any kind, express
or implied — including, without limitation, any warranty of fitness for
a particular purpose or merchantability. You run it entirely at your
own risk. The author is not liable for any damages or losses arising
from its use, including but not limited to save-file corruption, lost
progress, an unstable or unlaunchable game install, or any other issue
with your game or system. Modifying game files may also violate the
terms of service of the platform you purchased the game through —
checking that is on you. A backup of your original `ois.exe` and
`ois_server.exe` is made automatically, but you're responsible for
keeping it, and for your own save backups, before running this.

## License

[CC BY-NC 4.0](LICENSE) — free to use, share, and adapt for
non-commercial purposes, as long as you credit the original author
(Leeway). See [LICENSE](LICENSE) for the full terms.

## Version history

### 0.3.4 - 2026-09-02

- **No more typing a path.** Running `python ois_patcher.py` with no
  arguments now finds your Steam or GOG install automatically —
  checking Steam's registry entries and default folders, every Steam
  library including ones on other drives, and GOG's registry records.
  Asks which install to use if it finds more than one, and asks you to
  paste a path if it can't find any. Pointing it at a specific
  `ois.exe` or install folder still works exactly as before, and a new
  `--game-dir` flag and `OIS_TARGET_DIR` environment variable are
  available for scripted setups.
- **Added `--uninstall`**, which restores `ois.exe` and `ois_server.exe`
  from their backups and removes the `oisbugfix` mod folder in one
  step, after confirming what it's about to do. No more manual
  copy-the-backup-back-yourself. Each backup is checked to make sure
  it's a genuine unpatched original before being used, and the restore
  is verified byte-for-byte after writing. `--yes` skips the
  confirmation for scripted use; `--keep-backups` keeps the backup
  files afterward instead of deleting them.
- **Added `--status`**, which reports what's currently installed (which
  exes are patched, by which version, whether their backups are usable,
  whether the mod is installed) without changing anything.
- **Updating is now automatic.** Running the patcher again against an
  install patched by an older version of this tool now asks to update
  it for you: restores the original from its backup, then re-applies
  the current fixes to that clean original — never on top of an
  already-patched file. An install already on the current version is
  left alone (with the mod refreshed in case you'd deleted it). Trying
  to run an *older* copy of the patcher against an install patched by a
  *newer* one is now refused instead of silently downgrading it, unless
  you pass `--force`.
- **Added a self-update check.** If this patcher was set up via
  `git clone`, a normal run now checks whether a newer version of the
  script itself is available and offers to pull and use it, before
  touching your game. Skipped automatically for a plain downloaded zip,
  or if `git` isn't installed. `--update` accepts the update without
  asking (for scripted runs); `--no-update-check` skips the check
  entirely.
- **More reliable failure handling throughout.** A truncated or
  corrupted exe is now reported clearly and safely instead of crashing
  with a raw error — and no longer leaves a stray backup file behind
  when that happens. A corrupted `ois_server.exe` no longer prevents
  `ois.exe` from being patched successfully. The data-only mod install
  now degrades to a clear warning (matching what this README already
  promised) instead of failing outright if its companion file is
  missing. The patcher also checks that the target files are actually
  writable (e.g. the game isn't currently running) before making any
  changes, rather than partway through.

### 0.3.3 - 2026-09-01

- Fixed the GRA 5 grappling arm installing non-functional and unsellable when bought in Stealth or Low Power Use condition — its data was missing 8 of 10 components in those two states (issue #7).
- Fixed 6 LADAR modules (`MKX-LADAR-A-2`, `MKX-LADAR-A-T`, `MTL-C100`, `MTL-C150`, `MTL-CC`, `TBL-B42`) installing with every component shown in the wrong slot in the repair screen, due to a stray extra value in their data.
- Fixed `MKX-LADAR-A-2` and `MKX-LADAR-A-T` crashing the game outright when equipped — their identifiers were exactly one character too long for a fixed network-packet field, and the game didn't handle the resulting failed lookup gracefully.

(credit to Voidless7125 for bringing these issues to my attention)

### 0.3.2 - 2026-08-31

- Quick fix for versioning on the mod.

(credit to Voidless7125 for creating the fix for this)

### 0.3.1 — 2026-08-30

- Fixed a second Pirate Hunt crash cause on **both** `ois.exe` and `ois_server.exe`: a log call formatting a "duplicate ship-sets" message was missing an argument for its own format string, crashing with the same signature as the spawn-selection bug above. Found while live-testing 0.3.0's server fix — it correctly stopped the first crash, but a Pirate Hunt session could still hit this second, independent one a few lines later in the same code path.

### 0.3.0 — 2026-08-30

- Also patches `ois_server.exe`, the co-op server binary that ships
  alongside `ois.exe`: the same Pirate Hunt spawn-selection crash fixed
  on the client also exists in the server binary. Singleplayer never
  runs `ois_server.exe`, so this only matters for hosting or joining a
  co-op game — but it's a hard crash there every time, reported and
  confirmed by a co-op host after 0.2.0 shipped.

(credit to Voidless7125 for bringing this to my attention)

### 0.2.0 — 2026-08-30

- "unknown mesh" error for a specific beard style (mod)
- "Unknown room" log spam cycling past a ship's last room
- Rare crash opening the PDA while a character's portrait is mid-render

### 0.1.0 — 2026-08-28

First packaged release.

- Pirate Hunt scenario crash (client-side)
- Music player permanent failure loop
- Ship steering recompute spam (three independent causes)
- Mail/PC terminal `DEL` command crash + delete-a-command feature
- Co-op scenario "Escort: Make a Break" load failure (mod)
- "CLASH between additions" log spam (mod)