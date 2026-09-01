#!/usr/bin/env python3
"""
Applies the project's data-only bugfix mod without ever distributing a
copy of Objects in Space's own copyrighted asset files.

Every fix below is expressed as an exact single-line replacement, not a
bundled full file. At install time, this script reads the line straight
out of the user's own installed copy of the affected file, verifies it
matches byte-for-byte what's expected (same discipline as the exe
patches in ois_patcher.py -- wrong game version or an already-modified
file causes that file's fix to be skipped with a warning, never
guessed at), and writes only the corrected result into the game's own
mod-loader folder. The copyrighted game content itself never leaves
the user's machine or appears in this repository.

FIXES maps each affected asset filename to a list of
(expected_occurrence_count, old_line, new_line) tuples. A count other
than 1 means the same line legitimately repeats verbatim elsewhere in
the file (e.g. several near-identical character entries) -- every
occurrence gets the same fix, and the count itself is part of the
verification (wrong count means the file doesn't match what this was
built against).
"""
import shutil
from pathlib import Path

FIXES = {
    # BUG-001: a literal typo in an include directive orphaned an entire
    # co-op scenario.
    "scenarios.txt": [
        (1,
         "include coop_escort_3.txtX",
         "include coop_escort_3.txt"),
    ],

    # BUG-002: several background-NPC data files listed a hairstyle after
    # a helmet/fez/headscarf in the same body slot -- the game's own
    # clash-check already correctly rejects the second item, so these
    # tokens were already dead (never rendered), just noisy in the log.
    "cha_akihasagawa.txt": [
        (1,
         "additions=HighLifeShirt:0,HighLife2Pants:0,ReadingGlasses:0,Fez:0,HairFullSwish:0",
         "additions=HighLifeShirt:0,HighLife2Pants:0,ReadingGlasses:0,Fez:0"),
    ],
    "cha_bud.txt": [
        (1,
         "additions=MilitaryFlightJacket:0,MilitaryArmouredPants:0,RoundGlasses:0,Fez:0,HairFullSwish:0,BikerMoustache:0",
         "additions=MilitaryFlightJacket:0,MilitaryArmouredPants:0,RoundGlasses:0,Fez:0,BikerMoustache:0"),
    ],
    "cha_grandpa.txt": [
        (1,
         "additions=FezShirt:0,HighLifePants:0,RoundGlasses:0,Fez:0,HairCostanza:0,ChineseMoustache:0",
         "additions=FezShirt:0,HighLifePants:0,RoundGlasses:0,Fez:0,ChineseMoustache:0"),
    ],
    "cha_hillarytemkin.txt": [
        (1,
         "\tadditions=RockSuitJacket:0,HighLifePants:0,RoundGlasses:0,Fez:0,HairCostanza:0,LongMoustache:0",
         "\tadditions=RockSuitJacket:0,HighLifePants:0,RoundGlasses:0,Fez:0,LongMoustache:0"),
    ],
    "cha_kylevavos.txt": [
        (1,
         "additions=RoyaltyShirt:0,JockPants:0,TracerGoggles:0,Fez:0,HairLongFlowy2:0",
         "additions=RoyaltyShirt:0,JockPants:0,TracerGoggles:0,Fez:0"),
    ],
    "cha_leonmilitaryofficial.txt": [
        (1,
         "additions=MilitaryFlightJacket:2,MilitaryArmouredPants:2,MilitaryHelmet_A:2,HairCostanza:0,ChineseMoustache:0",
         "additions=MilitaryFlightJacket:2,MilitaryArmouredPants:2,MilitaryHelmet_A:2,ChineseMoustache:0"),
    ],
    "cha_merchant.txt": [
        (1,
         "\tadditions=DesertShirt:0,GrifterPants:1,TracerGoggles:0,Fez:0,HairSideSwishL:0,ChineseMoustache:0",
         "\tadditions=DesertShirt:0,GrifterPants:1,TracerGoggles:0,Fez:0,ChineseMoustache:0"),
    ],
    "cha_parssusauthority.txt": [
        (1,
         "\tadditions=MilitaryArmouredTop:1,MilitaryArmouredPants:1,MilitaryHelmet_A:1,HairSpikeyLong:0",
         "\tadditions=MilitaryArmouredTop:1,MilitaryArmouredPants:1,MilitaryHelmet_A:1"),
        (18,
         "\tadditions=MilitaryArmouredTop:1,MilitaryArmouredPants:1,MilitaryHelmet_A:1,HairFullSwish:0",
         "\tadditions=MilitaryArmouredTop:1,MilitaryArmouredPants:1,MilitaryHelmet_A:1"),
    ],
    "cha_pilot.txt": [
        (1,
         "\tadditions=HighLife2Shirt:0,GrifterPants:1,TracerGoggles:0,MilitaryHelmet_A:4,HairSideSwishL:0,LongBushyBeard:0",
         "\tadditions=HighLife2Shirt:0,GrifterPants:1,TracerGoggles:0,MilitaryHelmet_A:4,LongBushyBeard:0"),
        (1,
         "\tadditions=WanderersCoat:0,GrifterPants:1,TracerGoggles:0,MilitaryHelmet_B:4,HairSideSwishL:0,LongChinstrapBeard:0",
         "\tadditions=WanderersCoat:0,GrifterPants:1,TracerGoggles:0,MilitaryHelmet_B:4,LongChinstrapBeard:0"),
        (1,
         "\tadditions=ScientistCoat:0,GrifterPants:1,TracerGoggles:0,DesertHeadscarf:0,HairPonytail:0,SoupMoustache:0",
         "\tadditions=ScientistCoat:0,GrifterPants:1,TracerGoggles:0,DesertHeadscarf:0,SoupMoustache:0"),
    ],
    "cha_poorcitizen.txt": [
        (1,
         "\tadditions=HighLife2Shirt:2,DesertPants:0,DesertHeadscarf:0,HairLongFlowy4:0",
         "\tadditions=HighLife2Shirt:2,DesertPants:0,DesertHeadscarf:0"),
    ],
    "cha_shengxu.txt": [
        (1,
         "additions=HighLife2Shirt:0,HighLife2Pants:0,Neckbrace:0,Fez:0,HairCostanza:0,ChineseMoustache:0",
         "additions=HighLife2Shirt:0,HighLife2Pants:0,Neckbrace:0,Fez:0,ChineseMoustache:0"),
    ],
    "cha_sylviagarcia.txt": [
        (1,
         "additions=RoyaltyShirt:0,ScientistPants:0,Fez:0,HairLongFlowy:0",
         "additions=RoyaltyShirt:0,ScientistPants:0,Fez:0"),
    ],
    "cha_uniformedguard.txt": [
        (1,
         "additions=MilitaryArmouredTop:1,MilitaryArmouredPants:1,MilitaryHelmet_A:1,HairCostanza:0",
         "additions=MilitaryArmouredTop:1,MilitaryArmouredPants:1,MilitaryHelmet_A:1"),
    ],

    # BUG-010: a one-field typo in this addition's own definition shifted
    # every value after it, breaking its mesh lookup.
    "characterclasses.txt": [
        (1,
         "    addition=LongChinstrapBeard,head,face,face,,true",
         "    addition=LongChinstrapBeard,true,head,face,,true"),
    ],

    # BUG-016: GRA 5's stealth/lowpoweruse configuration arrays had all 8
    # of the module's original component slots wiped to -1 (only the 2
    # slots unique to GRA 5, added when it was extended from the simpler
    # 8-slot GRA design, kept real values) -- an authoring gap from that
    # extension. A GRA 5 that rolls Stealth or Low Power Use condition in
    # a shop installs with only 2 of 10 components: non-functioning and
    # unsellable. Corrected values verified against real component stats
    # (powermodifier/emissionsmodifier) and manufacturer lore, not just
    # copied from GRA's own working lines -- GRA's own picks checked out,
    # but GRA 5's *already-populated* trailing stealth value (53, a
    # Ventarii/"durability" part matching its own defence tier) was a
    # second, independent mistake, corrected here to 54 (Elander, the
    # genuine lowest-emissions part in that family).
    "modules_arms.txt": [
        (1,
         "configuration=stealth,-1,-1,-1,-1,-1,-1,-1,-1,35,53\n",
         "configuration=stealth,24,35,-1,-1,-1,54,-1,-1,35,54\n"),
        (1,
         "configuration=lowpoweruse,-1,-1,-1,-1,-1,-1,-1,-1,33,52\n",
         "configuration=lowpoweruse,22,33,-1,-1,-1,52,-1,-1,33,52\n"),
    ],

    # BUG-017: 6 of 9 LADAR modules have a configuration= array one
    # element longer than the module's own compinterfaces.txt slot count
    # -- every quality tier carries an extra id from the "burner"
    # component family (100-103) with no matching UI slot anywhere in
    # that module's interface definition. The client places components
    # by array index directly into its slot list with no adjustment for
    # the extra element, so every real component from the second slot
    # onward renders one position off from its actual declared classtype,
    # and the final real component has no valid slot at all and never
    # appears. Fix: drop the stray leading value from every tier so the
    # array length matches the module's real slot count again.
    # tblb40 has a messier version of the same defect -- it's not just
    # one extra value, it's also short a real shp1 slot's worth of data
    # (3 shp1 values in the array where the UI declares 4) -- so its fix
    # both drops the leading value and restores the missing 4th value,
    # matching the pattern the other 3 known shp1 values in each tier
    # already establish (stealth's partial reduction -- 2 active, 1 empty
    # -- extended to a clean 2-of-4 rather than left ambiguous).
    "modules_ladar.txt": [
        (1,
         "configuration=new,100,80,80,20,40,40,70,50,70\n",
         "configuration=new,80,80,20,40,40,70,50,70\n"),
        (1,
         "configuration=stealth,103,-1,80,24,44,44,-1,-1,71\n",
         "configuration=stealth,-1,80,24,44,44,-1,-1,71\n"),
        (1,
         "configuration=lowpoweruse,103,-1,81,22,43,43,-1,-1,72\n",
         "configuration=lowpoweruse,-1,81,22,43,43,-1,-1,72\n"),
        (1,
         "configuration=boost,102,-1,80,22,43,43,-1,-1,70\n",
         "configuration=boost,-1,80,22,43,43,-1,-1,70\n"),
        (1,
         "configuration=defence,101,83,83,23,43,43,73,53,73\n",
         "configuration=defence,83,83,23,43,43,73,53,73\n"),

        (1,
         "configuration=new,100,80,80,20,50,70,50,30,30\n",
         "configuration=new,80,80,20,50,70,50,30,30\n"),
        (1,
         "configuration=stealth,103,-1,80,-1,-1,71,54,35,35\n",
         "configuration=stealth,-1,80,-1,-1,71,54,35,35\n"),
        (1,
         "configuration=lowpoweruse,103,-1,81,-1,-1,72,52,33,33\n",
         "configuration=lowpoweruse,-1,81,-1,-1,72,52,33,33\n"),
        (1,
         "configuration=boost,102,-1,80,-1,-1,70,52,33,33\n",
         "configuration=boost,-1,80,-1,-1,70,52,33,33\n"),
        (1,
         "configuration=defence,101,83,83,23,53,73,53,34,34\n",
         "configuration=defence,83,83,23,53,73,53,34,34\n"),

        (1,
         "configuration=new,100,80,80,20,50,70,50,30,30,20\n",
         "configuration=new,80,80,20,50,70,50,30,30,20\n"),
        (1,
         "configuration=stealth,103,-1,-1,-1,-1,71,54,35,35,24\n",
         "configuration=stealth,-1,-1,-1,-1,71,54,35,35,24\n"),
        (1,
         "configuration=lowpoweruse,103,-1,-1,-1,-1,72,52,33,33,22\n",
         "configuration=lowpoweruse,-1,-1,-1,-1,72,52,33,33,22\n"),
        (1,
         "configuration=boost,102,-1,-1,-1,-1,70,52,33,33,22\n",
         "configuration=boost,-1,-1,-1,-1,70,52,33,33,22\n"),
        (1,
         "configuration=defence,101,83,83,23,53,73,53,34,34,23\n",
         "configuration=defence,83,83,23,53,73,53,34,34,23\n"),

        (1,
         "configuration=new,100,80,80,20,50,70,50,30,20,40\n",
         "configuration=new,80,80,20,50,70,50,30,20,40\n"),
        (1,
         "configuration=stealth,103,-1,-1,-1,-1,71,54,35,24,44\n",
         "configuration=stealth,-1,-1,-1,-1,71,54,35,24,44\n"),
        (1,
         "configuration=lowpoweruse,103,-1,-1,-1,-1,72,52,33,22,43\n",
         "configuration=lowpoweruse,-1,-1,-1,-1,72,52,33,22,43\n"),
        (1,
         "configuration=boost,102,-1,-1,-1,-1,70,52,33,22,43\n",
         "configuration=boost,-1,-1,-1,-1,70,52,33,22,43\n"),
        (1,
         "configuration=defence,101,83,83,23,53,73,53,34,23,43\n",
         "configuration=defence,83,83,23,53,73,53,34,23,43\n"),

        (1,
         "configuration=new,100,80,80,20,50,70,50,20,40,40\n",
         "configuration=new,80,80,20,50,70,50,20,40,40\n"),
        (1,
         "configuration=stealth,103,-1,-1,-1,-1,71,54,24,44,44\n",
         "configuration=stealth,-1,-1,-1,-1,71,54,24,44,44\n"),
        (1,
         "configuration=lowpoweruse,103,-1,-1,-1,-1,72,52,22,43,43\n",
         "configuration=lowpoweruse,-1,-1,-1,-1,72,52,22,43,43\n"),
        (1,
         "configuration=boost,102,-1,-1,-1,-1,70,52,22,43,43\n",
         "configuration=boost,-1,-1,-1,-1,70,52,22,43,43\n"),
        (1,
         "configuration=defence,101,83,83,23,53,73,53,23,43,43\n",
         "configuration=defence,83,83,23,53,73,53,23,43,43\n"),

        (1,
         "configuration=new,100,80,80,70,40,40,40,40,30,30,30,30\n",
         "configuration=new,80,80,70,40,40,40,40,30,30,30,30\n"),
        (1,
         "configuration=stealth,103,-1,-1,71,44,44,44,-1,-1,35,35,-1\n",
         "configuration=stealth,-1,-1,71,44,44,44,-1,-1,35,35,-1\n"),
        (1,
         "configuration=lowpoweruse,103,-1,-1,72,43,43,43,-1,-1,33,33,-1\n",
         "configuration=lowpoweruse,-1,-1,72,43,43,43,-1,-1,33,33,-1\n"),
        (1,
         "configuration=boost,102,-1,-1,70,43,43,43,-1,-1,33,33,-1\n",
         "configuration=boost,-1,-1,70,43,43,43,-1,-1,33,33,-1\n"),
        (1,
         "configuration=defence,101,83,83,73,43,43,43,43,34,34,34,34\n",
         "configuration=defence,83,83,73,43,43,43,43,34,34,34,34\n"),

        (1,
         "configuration=new,100,80,80,20,50,70,50,20,40,40,40\n",
         "configuration=new,80,80,20,50,70,50,20,40,40,40,40\n"),
        (1,
         "configuration=stealth,103,-1,-1,-1,-1,71,54,24,44,44,-1\n",
         "configuration=stealth,-1,-1,-1,-1,71,54,24,44,44,-1,-1\n"),
        (1,
         "configuration=lowpoweruse,103,-1,-1,-1,-1,72,52,22,43,43,43\n",
         "configuration=lowpoweruse,-1,-1,-1,-1,72,52,22,43,43,43,43\n"),
        (1,
         "configuration=boost,102,-1,-1,-1,-1,70,52,22,43,43,43\n",
         "configuration=boost,-1,-1,-1,-1,70,52,22,43,43,43,43\n"),
        (1,
         "configuration=defence,101,83,83,23,53,73,53,23,43,43,43\n",
         "configuration=defence,83,83,23,53,73,53,23,43,43,43,43\n"),

        # BUG-018: mkxladara2 and mkxladarat are the only 2 module ids in
        # the entire game at exactly 10 characters. The network protocol
        # that syncs an equipped module to a connecting client copies the
        # identifier into a fixed 10-byte packet field via a safe-copy
        # helper that truncates to fit rather than overflow -- correct
        # behaviour for that helper, but the resulting mangled identifier
        # ("mkxlad...") then fails to resolve to any real module on the
        # receiving end, and nothing checks for that failure before
        # dereferencing the (null) result: a hard, 100%-reproducible
        # client crash on connect. Renaming both ids to 9 characters or
        # fewer (matched below in compinterfaces.txt) avoids the overflow
        # entirely -- neither id is referenced anywhere else in the
        # game's data.
        (1, "id=mkxladara2", "id=mkxladr2"),
        (1, "id=mkxladarat", "id=mkxladrt"),
    ],

    # BUG-018 (see modules_ladar.txt above): compinterfaces.txt's own
    # copy of each id must match the rename exactly, or the renamed
    # module loses its wiring-diagram/repair-screen definition.
    "compinterfaces.txt": [
        (1, "\tid=mkxladara2", "\tid=mkxladr2"),
        (1, "\tid=mkxladarat", "\tid=mkxladrt"),
    ],
}


def apply_all(assets_dir, mod_dst_dir):
    """Reads each affected file from `assets_dir` (the user's own game
    install), applies the verified line fixes, and writes the result into
    `mod_dst_dir`. Returns (applied_count, skipped_count)."""
    assets_dir = Path(assets_dir)
    mod_dst_dir = Path(mod_dst_dir)
    mod_dst_dir.mkdir(parents=True, exist_ok=True)

    applied, skipped = 0, 0
    for filename, line_fixes in FIXES.items():
        src = assets_dir / filename
        if not src.is_file():
            print(f"  [SKIP] {filename}: not found in {assets_dir}")
            skipped += 1
            continue

        content = src.read_text(encoding="utf-8")
        ok = True
        for expected_count, old_line, new_line in line_fixes:
            actual_count = content.count(old_line)
            if actual_count != expected_count:
                print(f"  [SKIP] {filename}: expected {expected_count} occurrence(s) of a known line, "
                      f"found {actual_count} -- different game version or already modified")
                ok = False
                break
            content = content.replace(old_line, new_line)

        if not ok:
            skipped += 1
            continue

        (mod_dst_dir / filename).write_text(content, encoding="utf-8")
        applied += 1
        print(f"  [OK] {filename}")

    return applied, skipped


def install(game_root, bundled_mod_dir):
    """Full mod install: copies this project's own modinfo.txt as-is
    (it's original content, not derived from the game), then generates
    every data fix from the user's own assets/ folder. `game_root` is the
    folder containing ois.exe; `bundled_mod_dir` is this script's own
    mod/oisbugfix folder (just modinfo.txt)."""
    game_root = Path(game_root)
    assets_dir = game_root / "assets"
    mods_dir = game_root / "ObjectsInSpace" / "mods"
    mod_dst = mods_dir / "oisbugfix"

    if not assets_dir.is_dir():
        print(f"[SKIP] Bugfix mod: expected assets folder not found at {assets_dir} -- "
              f"is this really the game's install folder? Skipping mod install.")
        return False

    if mod_dst.exists():
        shutil.rmtree(mod_dst)
    mods_dir.mkdir(parents=True, exist_ok=True)

    modinfo_src = Path(bundled_mod_dir) / "modinfo.txt"
    if not modinfo_src.is_file():
        print(f"[SKIP] Bugfix mod: modinfo.txt not found at {modinfo_src}")
        return False
    mod_dst.mkdir(parents=True)
    shutil.copy2(modinfo_src, mod_dst / "modinfo.txt")

    applied, skipped = apply_all(assets_dir, mod_dst)

    print(f"\n[OK] Bugfix mod: {applied} fix(es) applied, {skipped} skipped -- installed to {mod_dst}")
    return True
