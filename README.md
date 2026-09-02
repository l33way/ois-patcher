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
  invocation patches `ois.exe` and `ois_server.exe`, and generates and
  installs the bugfix mod, all in one pass (see "Installation" below).
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

## Installation

**1. Download and unzip the patcher.** Get the latest release from the
[GitHub repo](https://github.com/l33way/ois-patcher) — either the
Releases page, or the green "Code → Download ZIP" button — then extract
it: right-click the downloaded `.zip` file in File Explorer and choose
"Extract All...". Don't try to run anything straight out of the zip;
extract it to a real folder first. `ois_patcher.py`, `apply_data_fixes.py`,
and the `mod/oisbugfix/` folder (see "What's in this folder" above) all
need to end up together in that one extracted folder.

**2. Open a terminal in that folder.** In File Explorer, open the
folder you just extracted (the one containing `ois_patcher.py`), then
either type `cmd` into the address bar and press Enter, or
Shift+right-click empty space in the folder and choose "Open PowerShell
window here" / "Open in Terminal."

**3. Run this one command**, replacing the path with wherever *your*
copy of the game is actually installed:

```py
python ois_patcher.py "C:\Path\To\Objects in Space\ois.exe"
```

- Point it at `ois.exe` itself (not the folder) — the file directly
  inside your game's install folder, sitting right next to an
  `ObjectsInSpace` subfolder and an `assets` subfolder. That's how the
  patcher locates everything else it needs. (In Steam: right-click
  *Objects in Space* → Properties → Installed Files → Browse, if you're
  not sure where yours is.)
- **Keep the quotes around the path.** The default Steam install path
  contains a space (`Objects in Space`), and an unquoted path with a
  space in it will fail or silently target the wrong thing.
- A typical default path looks like:
  `C:\Program Files (x86)\Steam\steamapps\common\Objects in Space\ois.exe`

**That's it — one command, one run.** You do not need to run
`apply_data_fixes.py` yourself, and there is no separate mod-install
step: the single command above does everything described below
automatically, in order:

1. Backs up your original `ois.exe` as `ois.exe.original-backup`
   (created once — running the patcher again reuses the existing
   backup rather than overwriting it).
2. Applies the binary fixes listed below, in place.
3. Backs up and patches `ois_server.exe` the same way — it ships
   alongside `ois.exe` in every Windows Steam install and is needed for
   hosting/joining co-op games (singleplayer never runs it, but it's
   still there). Its own separate backup, checked and skipped just as
   safely if anything doesn't match. If it's genuinely missing (e.g. a
   modified install), this step is skipped quietly rather than erroring.
4. Generates and installs the `oisbugfix` mod into
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

Running it again against an `ois.exe` (or `ois_server.exe`) that's
already been patched won't touch anything — each binary independently
detects its own previous work and tells you exactly what's going on: if
it's the same version, there's nothing to do for that binary; if it's
an older version, it'll tell you to restore that binary's own
`.original-backup` and re-run to pick up the newer fixes.

### Troubleshooting

- **Double-clicking `ois_patcher.py` by itself makes a window flash and
  disappear instantly.** This is expected, not a crash — the script has
  nothing telling it which `ois.exe` to patch, so it immediately prints
  a "missing argument" error and exits, and Windows closes the console
  window before you can read that error. Run it from a terminal with
  the `ois.exe` path as shown above instead of double-clicking it plain.
- **`'python' is not recognized...`, or a Microsoft Store page opens
  when you try to run it.** Python isn't installed, or isn't on your
  system's PATH. Install it from
  [python.org/downloads](https://www.python.org/downloads/) (not the
  Microsoft Store version, which can behave differently on Windows) —
  and make sure to check **"Add python.exe to PATH"** on the installer's
  first screen. If Python is already installed this way and `python`
  still doesn't work, try `py` in its place (Windows' own Python
  launcher, installed alongside python.org's Python) — e.g.
  `py ois_patcher.py "C:\Path\To\Objects in Space\ois.exe"`.
- **`ModuleNotFoundError: No module named 'pefile'`.** You're missing
  the one required package — run `pip install pefile` (or
  `py -m pip install pefile`) in a terminal, then try again.
- **It says some fixes were "skipped."** Scroll up in the output — the
  patcher always explains why (usually a different game version than
  this patch targets, 1.0.8, or that file already having been patched
  by an earlier run). This is expected, safe behavior, not a failure —
  every other fix still applies normally.

Still stuck? Open an issue on the
[GitHub repo](https://github.com/l33way/ois-patcher/issues) with what
you tried and exactly what you saw.

### Reverting

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
builds, if any exist.

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

- Added automatic Steam and GOG install discovery, including Steam libraries
  on other drives, with an interactive choice when multiple installs are
  found.
- Added `--list-installs`, `--status`, `--uninstall`, `--force`, and
  `--update` modes, plus `OIS_TARGET_DIR` for scripted or headless installs.
- Added embedded patch-version markers so older patcher releases can be
  upgraded safely from their original backups instead of patching on top.
- Improved executable validation, backup verification, and failure handling;
  the data-only mod now degrades to a warning when its companion files are
  unavailable.

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
