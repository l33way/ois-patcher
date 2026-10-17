# Changelog & Fix Reference

All notable changes to the **Objects in Space — Unofficial Bugfix Patch** are documented in this file, along with links to the corresponding GitHub issues, pull requests, and community contributors.

**Credits:**
- **Project Author:** [Leeway (`l33way`)](https://github.com/l33way) ([Steam Profile](https://steamcommunity.com/id/l33way/))
- **Major Contributor, Code, QA & Issue Reporting:** [Voidless7125](https://github.com/Voidless7125)
- **Additional Issue Reporting:** [ABadChoice](https://github.com/ABadChoice) ([#58](https://github.com/l33way/ois-patcher/issues/58))

---

## Version History

### [Unreleased]

- **New fix (exe, client and server):** Some NPC ships no longer turn up with their IFF off ("Unknown" in red on the nav map) and their reactors switched off, as Leslie Garbut's *SS Jolly Rancher* did in the intro on some machines. `ShipBehaviour`'s "stealthy" byte (+0x160) was set to 1 for pirates and `stealthy=true` ships but never cleared otherwise, and the constructor leaves it as whatever the heap held, so any non-zero leftover made the ship run dark. The constructor now zeroes it (and +0x15C). Found with a debug-log diagnostic that showed the IFF flag changing 1 → 0 inside the AI update (reported by [@Voidless7125](https://github.com/Voidless7125)).

---

### [0.4.1] - 2026-10-15

- **New fix (exe, client):** Fixed a crash to desktop when returning from a station to the player ship on saves played for some time ([Issue #58](https://github.com/l33way/ois-patcher/issues/58) — reported by [@ABadChoice](https://github.com/ABadChoice)). `PresentationInterface::update` previously ran `Room::runLogic` (queueing deferred Cocos2d-x `RenderTexture` draw commands for station monitors) *before* `runFullFadeLogic` destroyed the outgoing room's screens on the same frame, and `Room::runLogic` updated screens before `RoomObject::render` state/visibility rebuilds. Both ordering bugs are now fixed so destroyed `ScreenInterface` objects are never drawn after free.
- **Usability:** `ois_patcher.py` can now be launched directly by double-clicking it in Windows File Explorer and waits for a keypress before closing the console window, and automatically detects the active fork's `origin` remote URL for update notices.

---

### [0.4.0] - 2026-10-03 ([PR #33](https://github.com/l33way/ois-patcher/pull/33) by [@Voidless7125](https://github.com/Voidless7125))

- **New fix (exe, client and server):** The point-defence laser (`PDS`) can now destroy incoming torpedoes as stated in the Infopedia, prioritizes weapons (excluding the owner's own or already-destroyed ordnance), and still targets ships only when their IFF is off ([Issue #51](https://github.com/l33way/ois-patcher/issues/51) — reported & fixed by [@Voidless7125](https://github.com/Voidless7125) in [PR #33](https://github.com/l33way/ois-patcher/pull/33)).
- **New fix (mod):** NPC-only modules (`AP-RCS1` Remora RCS and `Probe Sensor` in `modules_npc.txt`) now have `basevalue=0` so they are no longer stocked in station shops ([Issue #50](https://github.com/l33way/ois-patcher/issues/50) — reported & fixed by [@Voidless7125](https://github.com/Voidless7125) in [PR #33](https://github.com/l33way/ois-patcher/pull/33)).
- **New fix (exe, client):** Pressing Enter on the News list with nothing selected (`slot -1`) no longer reads out-of-bounds heap memory to print `"Invalid article number: 747614849"` ([Issue #47](https://github.com/l33way/ois-patcher/issues/47) — reported & fixed by [@Voidless7125](https://github.com/Voidless7125) in [PR #33](https://github.com/l33way/ois-patcher/pull/33)). *(Note: The missing first-article selection marker on initial open is not changed.)*
- **New fix (exe, client):** Long point-defence manufacturer + model names (e.g., `"Pritchard PSL 10X"`) no longer wrap onto a second line and overlap the `ENABLE` button on the 16-column PDS panel; when combined length exceeds 15 characters, only the model name is printed ([Issue #46](https://github.com/l33way/ois-patcher/issues/46) — reported & fixed by [@Voidless7125](https://github.com/Voidless7125) in [PR #33](https://github.com/l33way/ois-patcher/pull/33)).
- **New fix (mod):** Console `Weapons` and `Cargo` tabs on the Enceladus, Ceres/Proxima, and Remora now carry `linkto=helm` so they properly show helm damage static and offline states alongside the other console tabs ([Issue #45](https://github.com/l33way/ois-patcher/issues/45) — reported & fixed by [@Voidless7125](https://github.com/Voidless7125) in [PR #33](https://github.com/l33way/ois-patcher/pull/33)).
- **New fix (mod):** The Infopedia article list and adjacent text pane (4:3 and 16:9 layouts) are trimmed to a whole number of rows (`235` / `259` units) so the bottom row is no longer sliced in half ([Issue #40](https://github.com/l33way/ois-patcher/issues/40) — reported & fixed by [@Voidless7125](https://github.com/Voidless7125) in [PR #33](https://github.com/l33way/ois-patcher/pull/33)).
- **New fix (exe, client):** Ship terminal `STATUS`, `POWER`, and ship-text lines now display units as `kw` instead of `mw` to match the power screen and power bar, and `STATUS` "Current Power Drain" now prints actual power drain instead of power generation ([Issue #38](https://github.com/l33way/ois-patcher/issues/38) — reported & fixed by [@Voidless7125](https://github.com/Voidless7125) in [PR #33](https://github.com/l33way/ois-patcher/pull/33)).
- **New fix (exe, client and server):** Power drain shown on the Power Management screen/power bar and the power actually drawn from the batteries now agree: component `powermodifier` percentages are applied to both, and active modules no longer add their idle drain on top of their active drain ([Issue #37](https://github.com/l33way/ois-patcher/issues/37) — reported & fixed by [@Voidless7125](https://github.com/Voidless7125) in [PR #33](https://github.com/l33way/ois-patcher/pull/33)). *Note: Batteries will drain faster on ships whose components carry a positive power modifier, matching the "Actual" figure already shown on module screens.*
- **Fixed a regression (exe, client):** Reverted the 0.3.0–0.3.8 behavior where the mail-terminal `DEL` command could delete `.COM` commands, restoring original game behavior (`"cannot delete system file"`) while keeping the crash fix for extensionless arguments like `DEL DEL`, `DEL DIR`, or `DEL VIEW` ([Issue #32](https://github.com/l33way/ois-patcher/issues/32) — reported by [@Voidless7125](https://github.com/Voidless7125), fixed in [PR #33](https://github.com/l33way/ois-patcher/pull/33)).
- **New fix (mod):** Cleared `hasmenu=true` on the square (192×192) Comms Download / Sync terminal on the Enceladus and Proxima (matching the Ceres III) so dead `?` (help) and log buttons are no longer shown ([Issue #31](https://github.com/l33way/ois-patcher/issues/31) — reported & fixed by [@Voidless7125](https://github.com/Voidless7125) in [PR #33](https://github.com/l33way/ois-patcher/pull/33)).
- **New fix (exe, client):** Nav map sector distance color (`Dist.`) now compares against `ShipModule::getCurrentJumpRange` (base range × efficiency) rather than base range alone, so jump drives above 100% efficiency no longer show reachable sectors in red *(no issue opened; found & fixed directly by [@Voidless7125](https://github.com/Voidless7125) in [PR #33](https://github.com/l33way/ois-patcher/pull/33))*.
- **New fix (exe, client and server):** Autopilot no longer burns *away* from its destination after overshooting it with a fast engine (e.g., GX Delta at 100%); it now checks the dot product of velocity and waypoint vector to orient a proper retro burn *(no issue opened; found & fixed directly by [@Voidless7125](https://github.com/Voidless7125) in [PR #33](https://github.com/l33way/ois-patcher/pull/33))*.
- **New fix (exe, client and server):** Autopilot in the "accelerate to final waypoint" state now uses a `1e-5` float tolerance (matching intermediate waypoints) when comparing current speed to top speed, preventing the main drive from continuously burning at top speed and draining the batteries *(no issue opened; found & fixed directly by [@Voidless7125](https://github.com/Voidless7125) in [PR #33](https://github.com/l33way/ois-patcher/pull/33))*.
- **New fix (exe, client):** Forced/intercom conversations (such as Asterin Allas) now initialize selection using `firstValidConversationOption()` instead of hardcoded option `0`, so pressing Enter immediately works even when option `0` is hidden by story flags *(no issue opened; found & fixed directly by [@Voidless7125](https://github.com/Voidless7125) in [PR #33](https://github.com/l33way/ois-patcher/pull/33))*.
- **New fix (exe, client):** Docking or jumping in stand-alone scenarios (Convoy Attack, Survival, Stealth, Escape, Defend, quickstart, etc.) no longer auto-saves over campaign Save Slot 1; auto-save now checks for `scenariocat=story` *(no issue opened; found & fixed directly by [@Voidless7125](https://github.com/Voidless7125) in [PR #33](https://github.com/l33way/ois-patcher/pull/33))*.
- **New fix (exe + mod):** Buying a module at Mechanixx now queues its unused `email=` welcome message (present in 71 module files) for your next comms sync, and the 56 shared category emails now include the specific manufacturer and model name in their opening line *(no issue opened; found & fixed directly by [@Voidless7125](https://github.com/Voidless7125) in [PR #33](https://github.com/l33way/ois-patcher/pull/33))*.
- **New fix (mod + in-place assets):** Applied ~450 spelling and grammar corrections across ~320 text files (dialogue, emails, news, and info pages), including fixing the broken `$amonut` reward token in `passengers.txt`. Because the game engine ignores mod folders for `news_*` and `info_*` files, those 179 files are patched in place in `assets/` with untouched backups saved in `oisbugfix_original_assets/` and restored by `--uninstall` *(no issue opened; found & fixed directly by [@Voidless7125](https://github.com/Voidless7125) in [PR #33](https://github.com/l33way/ois-patcher/pull/33))*.

---

### [0.3.9] - 2026-10-03 ([PR #43](https://github.com/l33way/ois-patcher/pull/43) by [@l33way](https://github.com/l33way))

- **Fixed a sound regression from 0.3.8:** Station terminal beeps (docking computer, wire/commodities, contracts, and other terminals) stopped playing in 0.3.8 because nearly all terminal button beeps attach to the player's own ship while typing clicks attach to the station ([Issue #35](https://github.com/l33way/ois-patcher/issues/35), [Issue #21](https://github.com/l33way/ois-patcher/issues/21) — reported by [@Voidless7125](https://github.com/Voidless7125)). `SoundEngine::playSound(Ship*)` now plays sounds belonging to the active listener ship, `currentlyBoardedShip`, *or* the player's own ship (`*(g_gameData+0xd0)`), so all station clicks and beeps play reliably.

---

### [0.3.8] - 2026-10-01 ([PR #34](https://github.com/l33way/ois-patcher/pull/34) by [@l33way](https://github.com/l33way))

- **New fix (exe, client):** Fixed a crash when clicking or backing out of a monitor in the moments after the player ship's Primary Hull is destroyed ([Issue #22](https://github.com/l33way/ois-patcher/issues/22) — reported by [@Voidless7125](https://github.com/Voidless7125)).
- **New fix (exe, client):** Fixed `"docking"` and `"stationary"` drawing on top of each other on the ship status screen during the docking phase ([Issue #23](https://github.com/l33way/ois-patcher/issues/23) — reported by [@Voidless7125](https://github.com/Voidless7125)).
- **New fix (exe, client):** Fixed station Admin Terminal typing clicks and `[change details]` beep swapping depending on whether you loaded at the station or walked over from your ship ([Issue #21](https://github.com/l33way/ois-patcher/issues/21) — reported by [@Voidless7125](https://github.com/Voidless7125)). *(Refined in 0.3.9 via [#35](https://github.com/l33way/ois-patcher/issues/35)).*
- **New fix (mod):** Moved the Enceladus Inner and Outer airlock door button click-colliders up by 1–2 units to align with the drawn button plates ([Issue #25](https://github.com/l33way/ois-patcher/issues/25) — reported by [@Voidless7125](https://github.com/Voidless7125)).
- **New fix (mod):** Fixed the Enceladus Dock Con screen `"Undock"` button sitting 30px left of alignment (`x=128` -> `x=158`) with the `JUMP` button above it ([Issue #26](https://github.com/l33way/ois-patcher/issues/26) — reported by [@Voidless7125](https://github.com/Voidless7125)).

---

### [0.3.7] - 2026-09-26 ([PR #28](https://github.com/l33way/ois-patcher/pull/28) by [@l33way](https://github.com/l33way))

- **New fix (exe, client):** Fixed the last keybinding row (`"Decrease Main Drive Power"`) being impossible to scroll into view in the PDA and main-menu Input Configuration lists, and removed a stray leading space in its label ([Issue #27](https://github.com/l33way/ois-patcher/issues/27) — reported by [@Voidless7125](https://github.com/Voidless7125)).
- **New fix (exe, client):** Enabled scrolling up with the mouse wheel to zoom back out of non-screen cabin close-ups—the Ceres Mk III cabin posters, Enceladus cabin desk PC, and Proxima equivalent ([Issue #24](https://github.com/l33way/ois-patcher/issues/24) — reported by [@Voidless7125](https://github.com/Voidless7125)).
- **New fix (exe, client):** Quitting the PC terminal's `MAIL` app right after deleting an email no longer leaves a frozen pre-delete copy of the email list on screen.

---

### [0.3.6] - 2026-09-24 ([PR #19](https://github.com/l33way/ois-patcher/pull/19) by [@l33way](https://github.com/l33way))

- **New fix (exe, client):** Fixed a garbled error message on the Commodities Trading Terminal when buying radiation-shielded or temperature-controlled goods without enough free specialized pod space ([Issue #17](https://github.com/l33way/ois-patcher/issues/17) — reported by [@Voidless7125](https://github.com/Voidless7125)).
- **New fix (exe, client):** Fixed an out-of-bounds read crash when dragging an installed addon component between slots on the engineering repair screen ([Issue #16](https://github.com/l33way/ois-patcher/issues/16) — reported by [@Voidless7125](https://github.com/Voidless7125)). *(Cleanly rejects the unimplemented move without re-enabling disabled shield/adapter content.)*
- **New fix (exe, client):** Fixed `"Quit to OS"` and `"Quit to Menu"` failing to disconnect and close the game when clicked as a connected LAN client.

---

### [0.3.5] - 2026-09-12 ([PR #15](https://github.com/l33way/ois-patcher/pull/15) by [@l33way](https://github.com/l33way), [PR #12](https://github.com/l33way/ois-patcher/pull/12) by [@Voidless7125](https://github.com/Voidless7125))

- **New fix (exe, client):** Triggering Full Stop while docked no longer clears the ship's docking-process state field, preventing the exploit where ships could start their reactor and fly away without paying undocking fees or closing the airlock ([Issue #11](https://github.com/l33way/ois-patcher/issues/11) — reported by [@Voidless7125](https://github.com/Voidless7125)).
- **New fix (exe, client):** Loading a save (or ship file) that references a retired/unresolvable module ID—including saves made prior to v0.3.3's LADAR ID shortening—no longer crashes with a null-pointer dereference or hangs from a 339-byte stream desync; the ship now loads cleanly with that module slot empty ([Issue #13](https://github.com/l33way/ois-patcher/issues/13) — reported by [@Voidless7125](https://github.com/Voidless7125)).
- **Internal:** Refactored code structure for readability and maintainability ([PR #12](https://github.com/l33way/ois-patcher/pull/12) by [@Voidless7125](https://github.com/Voidless7125)).

---

### [0.3.4] - 2026-09-02 ([PR #10](https://github.com/l33way/ois-patcher/pull/10) by [@l33way](https://github.com/l33way))

- **Usability overhaul** (credit to [@Voidless7125](https://github.com/Voidless7125)):
  - **Auto-detection:** Running `python ois_patcher.py` with no arguments now locates Steam (and best-effort GOG) installs automatically.
  - **Added `--uninstall` and `--status`** flags.
  - **Automatic updates:** Re-running the patcher against an older patched install automatically restores from `.original-backup` and applies the new version.
  - **Self-update check:** `git clone` checkouts now check upstream for newer commits before patching.
  - **Hardened error handling:** Validates PE headers and file writability before touching disk, and isolates `ois_server.exe` and mod-install warnings.

---

### [0.3.3] - 2026-09-01 ([PR #9](https://github.com/l33way/ois-patcher/pull/9) by [@l33way](https://github.com/l33way))

- **New fix (mod):** Fixed the `GRA 5` grappling arm missing 8 of 10 components (installing broken and unsellable) when rolled in Stealth or Low Power Use condition ([Issue #7](https://github.com/l33way/ois-patcher/issues/7) — reported by [@Voidless7125](https://github.com/Voidless7125)).
- **New fix (mod):** Fixed 6 LADAR modules (`MKX-LADAR-A-2`, `MKX-LADAR-A-T`, `MTL-C100`, `MTL-C150`, `MTL-CC`, `TBL-B42`) displaying every component shifted one slot off on the repair screen due to a stray leading burner value in their `configuration=` arrays ([Issue #7](https://github.com/l33way/ois-patcher/issues/7) — reported by [@Voidless7125](https://github.com/Voidless7125)).
- **New fix (mod):** Fixed `MKX-LADAR-A-2` (`mkxladara2`) and `MKX-LADAR-A-T` (`mkxladarat`) crashing the game on equip due to their 10-character identifiers truncating inside a fixed 10-byte network packet field (reported by [@Voidless7125](https://github.com/Voidless7125)).

---

### [0.3.2] - 2026-08-31 ([PR #8](https://github.com/l33way/ois-patcher/pull/8) by [@Voidless7125](https://github.com/Voidless7125))

- Fixed mod versioning and updated the GitHub Actions release workflow (authored by [@Voidless7125](https://github.com/Voidless7125)).

---

### [0.3.1] - 2026-08-30 ([PR #3](https://github.com/l33way/ois-patcher/pull/3) by [@l33way](https://github.com/l33way))

- **New fix (exe, client and server):** Fixed a second, independent Pirate Hunt crash cause on both `ois.exe` and `ois_server.exe` where a `"duplicate ship-sets"` log call passed only 2 arguments to a 3-specifier format string ([Issue #2](https://github.com/l33way/ois-patcher/issues/2) — reported by [@Voidless7125](https://github.com/Voidless7125)).

---

### [0.3.0] - 2026-08-30 ([PR #1](https://github.com/l33way/ois-patcher/pull/1) by [@l33way](https://github.com/l33way))

- **New fix (exe, server):** Extended patching to `ois_server.exe` (the co-op server binary) to fix the Pirate Hunt spawn-selection bounds-check crash for co-op hosts and clients ([Issue #2](https://github.com/l33way/ois-patcher/issues/2) — reported by [@Voidless7125](https://github.com/Voidless7125)).

---

### [0.2.0] - 2026-08-30

- **New fix (mod):** Fixed an `"unknown mesh"` error for background NPCs wearing a specific beard style caused by a one-field typo in character-cosmetics data.
- **New fix (exe, client):** Silenced `"Unknown room"` `[ERROR]` log spam when cycling past a ship's last room.
- **New fix (exe, client):** Fixed a rare crash when opening the PDA at the exact instant a character's portrait is mid-render inside `libcocos2d.dll`.

---

### [0.1.0] - 2026-08-28

First packaged release.

- **New fix (exe, client):** Fixed the Pirate Hunt scenario ship spawn-selection bounds-check crash.
- **New fix (exe, client):** Fixed the music player permanent failure loop caused by leaked FMOD sound handles on track changes.
- **New fix (exe, client):** Fixed ship steering/burn-vector recompute and log spam (~125 times/sec) across three separate causes.
- **New fix (exe, client):** Fixed the Mail/PC terminal `DEL` command crash when invoked without a file extension.
- **New fix (mod):** Fixed a one-character include typo that prevented the co-op scenario *"Escort: Make a Break"* from loading.
- **New fix (mod):** Removed dead hairstyle tokens listed after helmets/headgear in 13 NPC files that caused `"CLASH between additions"` log spam on boot.

---

## Investigated & Left Unchanged (`wontfix` / Original Design)

In keeping with the project's scope of only fixing unambiguous bugs rather than altering original design or layout choices without proof of unintended behavior, the following reported issues were investigated and intentionally left unchanged:

- **LADAR modules excluded from station shops:** Confirmed via disassembly to be an intentional hardcoded developer filter in the shop generator rather than a data bug.
- **Text overflowing in module/ship view** ([Issue #14](https://github.com/l33way/ois-patcher/issues/14) — reported by [@Voidless7125](https://github.com/Voidless7125)): Closed as `wontfix` because this is how the original game UI was written and there is no evidence the developers intended different behavior.
- **PDA "Switch tabs for current screen" text/unbound label going off screen** ([Issue #30](https://github.com/l33way/ois-patcher/issues/30) — reported by [@Voidless7125](https://github.com/Voidless7125)): Closed as `wontfix`.
- **Deleting `.COM` commands with `DEL` in the mail terminal** ([Issue #32](https://github.com/l33way/ois-patcher/issues/32) — reported by [@Voidless7125](https://github.com/Voidless7125)): Closed as `wontfix` (and reverted in v0.4.0); the original game only ever responds `"cannot delete system file"`.
