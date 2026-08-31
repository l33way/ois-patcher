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

- `ois_patcher.py` — patches your `ois.exe` and `ois_server.exe`, and
  installs the bugfix mod
- `apply_data_fixes.py` — generates the data-only fixes from your own
  `assets/` folder (see the file's own header for why they're not
  shipped as ready-made files)
- `mod/oisbugfix/modinfo.txt` — this mod's metadata; ship all three
  files together — the patcher looks for them right next to itself

## Requirements

- Python 3.8+
- `pip install pefile`

## Usage

```
python ois_patcher.py "C:\Path\To\Objects in Space\ois.exe"
```

Point it at the `ois.exe` inside your game's install folder (right next
to the `ObjectsInSpace` subfolder — that's how the patcher finds where
to install the mod). It will:

1. Back up your original `ois.exe` as `ois.exe.original-backup`
   (created once — running the patcher again reuses the existing
   backup rather than overwriting it)
2. Apply the binary fixes listed below, in place
3. Back up and patch `ois_server.exe` the same way — it ships alongside
   `ois.exe` in every Windows Steam install and is needed for
   hosting/joining co-op games (singleplayer never runs it, but it's
   still there). Its own separate backup, checked and skipped just as
   safely if anything doesn't match. If it's genuinely missing (e.g. a
   modified install), this step is skipped quietly rather than erroring.
4. Install the `oisbugfix` mod into `ObjectsInSpace/mods/oisbugfix/`

Every patch checks the exact bytes it's about to change first, and
skips itself with a warning (rather than guessing) if anything doesn't
match — a different game version, or a file already modified some other
way. It's safe to re-run against an *unpatched* backup at any time.

Running it against an `ois.exe` (or `ois_server.exe`) that's already been
patched won't touch anything — each binary independently detects its own
previous work and tells you exactly what's going on: if it's the same
version, there's nothing to do for that binary; if it's an older version,
it'll tell you to restore that binary's own `.original-backup` and re-run
to pick up the newer fixes.

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
