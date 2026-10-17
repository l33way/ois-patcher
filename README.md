# Objects in Space — Unofficial Bugfix Patch

**Author:** Leeway ([steamcommunity.com/id/l33way](https://steamcommunity.com/id/l33way/))  
**Major Contributor & QA:** [Voidless7125](https://github.com/Voidless7125)

An unofficial community patch for *Objects in Space*, the space-stealth game by Flat Earth Games. It fixes numerous crashes (including the Pirate Hunt crash and the station-to-ship transition crash), broken modules, autopilot bugs, power-drain math, UI glitches, and over 450 text/dialogue typos—while staying strictly faithful to the developers' original vision.

> **Safe by default:** Before anything is modified, the patcher automatically backs up your original `ois.exe` and `ois_server.exe` as `.original-backup` files, and you can uninstall with a single command at any time.

---

## Quick Start (Step-by-Step for Beginners)

### Step 1: Install Python (via Python Install Manager)

Python on Windows is installed using the official **Python Install Manager (`.msix`)** from [python.org/downloads](https://www.python.org/downloads/) ([official Python Windows docs](https://docs.python.org/3/using/windows.html)):

1. **Download and Run the Installer:**
   - Go to [python.org/downloads](https://www.python.org/downloads/) and click the yellow **Download Python Install Manager** button to download the `.msix` file.
   - Double-click the downloaded `.msix` file and click **Install**.
2. **Finish the Automatic Terminal Setup & Enable `PATH`:**
   - As soon as the `.msix` installation finishes, a terminal window will **launch automatically** to install the default Python runtime.
   - When prompted in that terminal window to **add the global commands directory (`%LocalAppData%\Pythonin`) to your `PATH`**, press **`y`** (Yes) so `python`, `py`, and `pip` work everywhere.
   - *(Note: If you didn't get the prompt or closed the window early, open PowerShell or Command Prompt and run `py install default --configure`. If you need to add the directory to `PATH` manually later, click Start, search for **"Edit environment variables for your account"**, and add `%LocalAppData%\Pythonin` to your user `Path`.)*
3. **The `pefile` Package:**
   - The patcher needs the `pefile` package to read and patch the game files. If it isn't installed yet, **`ois_patcher.py` will automatically ask if you want to install it** right when you run it and will handle it for you (or you can install it manually anytime via `py -m pip install pefile`).

### Step 2: Download and Extract the Patcher

**Choose your preferred installation method below:**

#### Method A: Download the ZIP (Recommended for most players)
1. Download the latest release `.zip` from the [Releases page](https://github.com/l33way/ois-patcher/releases) (or click the green **Code → Download ZIP** button on GitHub).
2. **Right-click** the downloaded `.zip` file in File Explorer and click **Extract All...**.
   - **Important:** Do not double-click `ois_patcher.py` from *inside* the unextracted `.zip` preview! Extract the entire folder first and keep all files (`ois_patcher.py`, `apply_data_fixes.py`, `text_fixes.py`, and the `mod/` folder) together inside the same folder.

#### Method B: Use Git Clone (Advanced — best for seamless auto-updates)
If you are comfortable using Git, cloning the repository directly enables the patcher's built-in self-update feature so you can pull new fixes instantly:
1. Open a terminal where you want to keep your patcher files and clone the repo:
   ```powershell
   git clone https://github.com/l33way/ois-patcher.git
   cd ois-patcher
   ```
   *(Note: If you are using a personal fork such as Voidless7125's repository, clone your fork's URL instead so auto-update fetches from your fork).*
2. The patcher will automatically verify your remote URL and check for updates on future runs.

### Step 3: Run `ois_patcher.py`

- **Easiest way (ZIP install):** Open your extracted folder in File Explorer and **double-click `ois_patcher.py`**.
  - A window will open, automatically find your Steam (or GOG) *Objects in Space* installation, back up your original files, apply all binary and mod fixes, and wait for you to **press any key to close** when finished.
- **From a Terminal:** You can also open a terminal in the patcher folder and run:
  ```powershell
  py ois_patcher.py
  ```

### Step 4: Verify the Output

At the end of the run, you should see a summary right above `Press any key to close this window...`:

```text
Applied 27 exe fix(es), skipped 0.
ois_server.exe: applied 5 fix(es), skipped 0.
Bugfix mod: installed
```

That's it! Launch *Objects in Space* through Steam as normal.

---

## Updating, Checking Status, & Uninstalling

### Updating to a Newer Release
- **If you used the ZIP:** Download and extract the new release over your existing folder (or re-run `ois_patcher.py`). It detects the older patch version, restores your clean `.original-backup` files automatically, and applies the newest fixes cleanly on top.
- **If you used `git clone`:** Simply run `py ois_patcher.py`. The script will automatically check GitHub for upstream updates, show you the commit changelog, and ask if you'd like to pull and re-run automatically.

### Command-Line Options
If you run `ois_patcher.py` from Command Prompt or PowerShell, you can pass these options:

| Command | What it does |
| :--- | :--- |
| `py ois_patcher.py` | Auto-detects your game install and applies/updates the patch. |
| `py ois_patcher.py "C:\Path\To\Objects in Space"` | Patches a specific game folder (use quotes if the path has spaces). |
| `py ois_patcher.py --status` | Shows whether your game is patched, which version is installed, and backup status without changing anything. |
| `py ois_patcher.py --uninstall` | Restores your original `ois.exe`, `ois_server.exe`, and `assets/` files from backups and removes the `oisbugfix` mod. Leaves save games untouched. |
| `py ois_patcher.py --force` | Forces a fresh re-patch from backup even if already on the current version. |
| `py ois_patcher.py --yes` | Skips confirmation prompts and exits immediately without waiting for a keypress (for scripts). |

### Manual Uninstall (If Needed)
If you ever want to revert everything by hand without running the script:
1. Copy `ois.exe.original-backup` back over `ois.exe` (and `ois_server.exe.original-backup` over `ois_server.exe`).
2. Delete the `ObjectsInSpace/mods/oisbugfix` folder.
3. Copy the files from `oisbugfix_original_assets/` back into `assets/`, then delete `oisbugfix_original_assets/` (or run Steam's **"Verify integrity of game files"**).

---

## Troubleshooting

- **Double-clicking `ois_patcher.py` asks "How do you want to open this file?"**  
  Python isn't associated with `.py` files yet, or the first-time setup didn't finish. Open PowerShell or Command Prompt and run `py install default --configure` (or `py install --refresh`), or run the patcher from a terminal in the extracted folder with `py ois_patcher.py`.
- **`'py'` or `'python'` is not recognized:**  
  1. Make sure you opened a **new** terminal window after installing Python.
  2. If you had an older version of Python installed previously, uninstall the old **"Python Launcher"** from Windows **Installed Apps** and check **Settings → Apps → Advanced app settings → App execution aliases** to make sure the **`python.exe`** and **`py.exe`** aliases are toggled **On** ([Python Windows Troubleshooting docs](https://docs.python.org/3/using/windows.html#troubleshooting)).
  3. To check your `PATH` manually, click Start, search for **"Edit environment variables for your account"**, and ensure `%LocalAppData%\Pythonin` is listed under your user `Path`.
- **`This script needs 'pefile'`:**  
  Open PowerShell or Command Prompt and run `py -m pip install pefile`.
- **"Could not automatically find the game folder":**  
  When prompted in the window, copy and paste the path to your `Objects in Space` folder (e.g., `C:\Program Files (x86)\Steam\steamapps\common\Objects in Space`) and press Enter.

Still stuck? [Open an issue on GitHub](https://github.com/l33way/ois-patcher/issues) with what you tried and what message appeared.

---

## What Does This Patch Fix?

See **[CHANGELOG.md](CHANGELOG.md)** for the full release history, issue links, and detailed technical breakdown of all 33+ binary and data fixes. Highlights include:

- **Crash Fixes:** Fixes the **station-to-ship transition crash** ([#58](https://github.com/l33way/ois-patcher/issues/58)), **Pirate Hunt** scenario crashes on both client and co-op server ([#2](https://github.com/l33way/ois-patcher/issues/2)), **LADAR equip & save-load crashes** ([#13](https://github.com/l33way/ois-patcher/issues/13)), **PDA portrait-render crashes**, **post-hull-destruction monitor crashes** ([#22](https://github.com/l33way/ois-patcher/issues/22)), **engineering addon drag crashes** ([#16](https://github.com/l33way/ois-patcher/issues/16)), and **terminal `DEL` command crashes** ([#32](https://github.com/l33way/ois-patcher/issues/32)).
- **Gameplay & Ship Systems:** Point-defence lasers now actually shoot down incoming torpedoes ([#51](https://github.com/l33way/ois-patcher/issues/51)), autopilot no longer burns away after overshooting or drains batteries at max cruise speed, power drain UI and actual battery draw now respect component power modifiers ([#37](https://github.com/l33way/ois-patcher/issues/37)), standalone scenarios no longer overwrite campaign Save Slot 1, and Full Stop while docked no longer bypasses undocking fees/airlocks ([#11](https://github.com/l33way/ois-patcher/issues/11)).
- **Modules & Co-op:** Fixes broken GRA 5 and LADAR component slots ([#7](https://github.com/l33way/ois-patcher/issues/7)), prevents NPC-only modules from appearing in shops ([#50](https://github.com/l33way/ois-patcher/issues/50)), restores the 71 unused module-purchase welcome emails, fixes the unloadable *"Escort: Make a Break"* co-op scenario, and fixes *"Quit to Menu / Quit to OS"* freezing LAN clients.
- **Audio, UI & Text:** Fixes the music player handle-leak failure loop, missing station terminal beeps/clicks ([#21](https://github.com/l33way/ois-patcher/issues/21), [#35](https://github.com/l33way/ois-patcher/issues/35)), hidden *"Decrease Main Drive Power"* keybind ([#27](https://github.com/l33way/ois-patcher/issues/27)), cabin scroll-wheel zoom-out ([#24](https://github.com/l33way/ois-patcher/issues/24)), Enceladus button alignments ([#25](https://github.com/l33way/ois-patcher/issues/25), [#26](https://github.com/l33way/ois-patcher/issues/26)), console damage displays ([#45](https://github.com/l33way/ois-patcher/issues/45)), and ~450 spelling/grammar mistakes across ~320 game text files (including the broken `$amonut` reward token).

---

## Project Philosophy & Design Scope

### Goal: Restoring Original Intent, Not Adding New Features
*Objects in Space* is a genuine work of art that was sadly abandoned before completion. Every fix in this patch exists because something the developers clearly intended to work is broken, unreachable, or crashes. The scope is deliberately narrow: **restore the game to the state it evidently was meant to ship in—not redesign it, rebalance it, or extend it.**

- **Unambiguous bugs are in scope:** Typos, missing bounds-checks, leaked resource handles, use-after-free bugs, and identifiers one character too long for fixed-size network buffers.
- **Deliberate design choices are left alone:** Even if a mechanic feels restrictive, if it is enforced by an intentional developer filter (such as LADAR modules being deliberately excluded from shop purchase lists), this patch does not alter it.
- **No guesswork disguised as restoration:** Nothing here touches economy, difficulty, or content balance.

### Why a Python Script Instead of a Pre-Patched `ois.exe`?
Distributing a source script that patches your own installation rather than a pre-modified `.exe` is a deliberate security and copyright choice:
1. **Visibility & Security:** Anyone can read `ois_patcher.py` and `apply_data_fixes.py` to inspect every exact byte and file modified, rather than trusting an opaque binary from the internet.
2. **No Redistributed Game Assets:** Both the binary patches and data fixes are generated on the fly from your own local `Objects in Space` installation, so Flat Earth Games' copyrighted files are never bundled in this repository.

### What's in This Folder
Keep all of these files together in the same folder:
- **`ois_patcher.py`** — The main script you run (or double-click).
- **`apply_data_fixes.py`** — Imported automatically by `ois_patcher.py` to generate the `oisbugfix` mod from your local `assets/` files.
- **`text_fixes.py`** — Spelling and grammar correction snippets loaded automatically by `apply_data_fixes.py`.
- **`mod/oisbugfix/`** — Contains `modinfo.txt`; populated at install time by `apply_data_fixes.py`.

---

## Limitations, Liability, & License

- **Tested Build:** Tested against the **Windows Steam** build of *Objects in Space* (**v1.0.8**). Every patch site verifies its exact original bytes before modifying anything and safely skips itself with a warning if a byte doesn't match.
- **Limitation of Liability:** This patch is provided "as is," without warranty of any kind. Use at your own risk. While `.original-backup` files are created automatically, you are responsible for keeping backups of your game and save files.
- **License:** [CC BY-NC 4.0](LICENSE) — Free to use, share, and adapt for non-commercial purposes with credit to the original author (**Leeway**). See [LICENSE](LICENSE) for full terms.
