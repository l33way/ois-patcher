#!/usr/bin/env python3
"""
Objects in Space (Flat Earth Games) -- unofficial bugfix patcher for
ois.exe (client) and ois_server.exe, which ships alongside it in every
Windows Steam install (needed for hosting or joining co-op games --
singleplayer never touches it).

A collection of verified fixes for the game, consolidated into one
script anyone can point at their own copy of the game. Also installs a
data-only bugfix mod (a scenario-file typo, 33 dead/unreachable data
tokens across 13 character files, and a one-field typo in a character
cosmetics file) via the game's own mod-loader, since it fixes bugs the
exe patch doesn't touch.

None of Flat Earth Games' own asset files are bundled with this
script -- that content is theirs, not this project's. Instead,
apply_data_fixes.py reads each affected file straight out of your own
game install, verifies the exact line it's about to change matches
byte-for-byte what's expected (same discipline as the exe patches
below), and writes only the corrected result into the mod folder. The
game's own content never leaves your machine.

Usage:
    python ois_patcher.py
    python ois_patcher.py "C:\\path\\to\\Objects in Space"
    python ois_patcher.py "C:\\path\\to\\Objects in Space\\ois.exe"
    python ois_patcher.py --list-installs
    python ois_patcher.py --status
    python ois_patcher.py --uninstall
    python ois_patcher.py --update

With no path given, the install is located the same way Patch_OIS.bat
locates it -- Steam's registry keys and default folders, then every
library in libraryfolders.vdf -- extended to cover GOG installs and to
read the folder name out of Steam's own app manifest rather than
assuming it. An explicit path always wins; OIS_TARGET_DIR is consulted
before falling back to a prompt. A folder is only accepted if ois.exe
is actually in it, and if two installs are found the choice is put to
the user rather than guessed at.

Expects apply_data_fixes.py and a "mod" folder containing "oisbugfix"
(just modinfo.txt) next to this script -- ship all three together when
distributing this patcher. Skips mod installation with a warning,
rather than failing, if either is missing.

Updating and uninstalling are both driven by the version marker
embedded in the patched exe itself, so the installed state is read off
the file rather than a receipt that can go stale. Run against an
install patched by an older release, the script restores the original
from its backup and re-applies the current fixes, after asking; an
install already at this version is left alone and only its data-only
mod is refreshed. --uninstall reverses everything: stock exes back from
their backups (each verified stock before use, and byte-verified after
writing), mod folder deleted, saves and settings untouched.

Backs up the original alongside itself as "<name>.original-backup"
(created once, on first run -- never overwritten by later runs) and
writes the patched result back to the same path, in place. The mod
install is a separate, additive step (copies files into the game's own
mods/ folder via its supported mod-loader system) that needs no backup
of its own -- it never touches an existing game file in place.

Applies (all client-only, ois.exe):
  - Pirate Hunt scenario crash: missing bounds-check in the ship
    spawn-selection loop, plus a 3-argument format string with only 2
    args passed to it, both causing the same access-violation crash.
  - Music player permanent failure loop: FMOD Sound handle leak in
    SoundEngine::playNewTrack (never releases the previous track).
  - Ship burn-vector spam (three independent contributors): an
    over-strict bit-exact position comparison, a per-frame recompute
    with no "already handled" gate, and a numerical instability in the
    burn-angle calculation itself near a singularity.
  - Mail/PC terminal DEL/DIR crash + feature: DEL can delete an
    unprotected (COM) command ("Deleted.", green) but refuses a
    protected (EXE) one ("cannot delete system file", yellow, reusing
    the original developers' own unused string for it); a deleted
    command stops matching in the terminal and disappears from DIR.
    All of this is confirmed transient -- never touches save data,
    rebuilt fresh by Screen_PC's constructor on every undock/redock,
    save load, or game restart.
  - "Unknown room" log spam: cycling past a ship's last room repeatedly
    logs an [ERROR], because the existence check itself always logs on
    a miss even when the caller is only asking "does this room exist"
    and already handles a no answer correctly.
  - Rare PDA-open crash: opening the PDA at the exact moment a
    character's portrait is mid-render can collide inside the game's
    (third-party) rendering engine and crash. Rather than patch that
    engine DLL, this ignores the "open PDA" input for that instant
    instead -- pressing it again immediately after works normally.

Applies to ois_server.exe (ships alongside ois.exe in every Windows
Steam install):
  - Both halves of the same Pirate Hunt crash as above -- ois.exe and
    ois_server.exe both compile the same vulnerable function, at
    different addresses. Patched separately (own backup, own .ptch
    section); skipped quietly in the rare case it's genuinely missing
    (e.g. a modified install).

Every patch site's original bytes are verified before being touched; if
they don't match (wrong game version, already patched, modded some
other way), the affected patch is skipped with a warning rather than
guessing -- this script never overwrites bytes it hasn't confirmed it
understands. All absolute addresses used by injected code are computed
at runtime via a CALL $+5 / POP-register trick rather than hardcoded,
since this binary does not reliably load at its preferred base address;
every patch site is also checked against the PE's base-relocation table
and any conflicting entry is neutralized, since a hardcoded relocation
entry pointing into overwritten bytes corrupts them at load time
regardless of what replaced them.
"""
import argparse
import os
import re
import shutil
import struct
import subprocess
import sys
from pathlib import Path

try:
    import pefile
except ImportError:
    print("This script needs 'pefile': pip install pefile", file=sys.stderr)
    sys.exit(1)

# The docstring promises the mod install degrades to a warning if this is
# missing, so a hard ImportError here would break that promise on the very
# setup it was written for: someone who copied out just ois_patcher.py.
try:
    import apply_data_fixes
except ImportError:
    apply_data_fixes = None

IMAGE_BASE = 0x400000
FIXES_APPLIED = []
FIXES_SKIPPED = []
SERVER_FIXES_APPLIED = []
SERVER_FIXES_SKIPPED = []

# Bumped on every release that changes what gets patched -- embedded into
# the patched exe itself (see VERSION_MARKER_* below) so a later run of
# this script (possibly a newer version) can tell whether a "this exe is
# already patched" refusal means "you already ran this exact version" or
# "an older version patched this -- restore the backup and re-run to
# upgrade", instead of one generic message either way.
PATCHER_VERSION = "0.3.4"
VERSION_MARKER_PREFIX = b"OISPATCH:"
VERSION_MARKER_SIZE = 32  # reserved bytes at the start of .ptch's raw data


def load_pe(data):
    return pefile.PE(data=bytes(data), fast_load=True)


def validate_pe(data, label):
    """Confirms a blob really is the 32-bit PE this tool knows how to
    patch, before anything is written anywhere. Returns (ok, reason).

    pefile raises a whole family of things on malformed input, not just
    PEFormatError -- a truncated file can surface as struct.error or an
    AttributeError from a header that never got parsed -- so this catches
    broadly and turns all of it into one readable sentence."""
    try:
        pe = load_pe(data)
    except Exception as e:
        return False, (f"{label} is not a Windows executable this tool can read ({e}). "
                       f"If this file is truncated or corrupt, use Steam's \"Verify integrity "
                       f"of game files\" (or reinstall from GOG) to get a good copy.")
    try:
        image_base = pe.OPTIONAL_HEADER.ImageBase  # read it before close()
    except Exception as e:
        pe.close()
        return False, f"{label}: could not read the PE optional header ({e})."
    pe.close()
    if image_base != IMAGE_BASE:
        return False, (f"{label}: unexpected ImageBase {hex(image_base)} -- this doesn't look "
                       f"like the expected build.")
    return True, None


def va_to_offset(pe, va):
    rva = va - IMAGE_BASE
    for section in pe.sections:
        start = section.VirtualAddress
        end = start + max(section.Misc_VirtualSize, section.SizeOfRawData)
        if start <= rva < end:
            return rva - start + section.PointerToRawData
    return None


def verify_site(data, pe, va, expected, label):
    """Returns the file offset if the bytes at `va` match `expected`, else
    None (printing a warning) -- callers must skip the patch on None."""
    off = va_to_offset(pe, va)
    if off is None:
        print(f"  [SKIP] {label}: VA {hex(va)} not mapped in this file")
        return None
    actual = bytes(data[off:off + len(expected)])
    if actual != expected:
        print(f"  [SKIP] {label}: byte mismatch at VA {hex(va)}")
        print(f"         got:      {actual.hex(' ').upper()}")
        print(f"         expected: {expected.hex(' ').upper()}")
        return None
    return off


def neutralize_relocations(data, pe, va, length, label):
    """Find and neutralize any base-relocation entries pointing into
    [va, va+length) -- overwriting bytes doesn't remove the loader's own
    fixup for them, which corrupts our patch at load time if the module
    doesn't load at its preferred base (confirmed it usually doesn't)."""
    IMAGE_REL_BASED_ABSOLUTE = 0
    rva = va - IMAGE_BASE
    conflicts = []
    if hasattr(pe, "DIRECTORY_ENTRY_BASERELOC"):
        for reloc in pe.DIRECTORY_ENTRY_BASERELOC:
            for entry in reloc.entries:
                if entry.type == 0:
                    continue
                if rva <= entry.rva < rva + length:
                    conflicts.append(entry)
    for entry in conflicts:
        file_off = entry.struct.get_file_offset()
        struct.pack_into("<H", data, file_off, IMAGE_REL_BASED_ABSOLUTE)
    if conflicts:
        print(f"    neutralized {len(conflicts)} relocation entr{'y' if len(conflicts)==1 else 'ies'} in {label}'s patch range")


# ============================================================
# .ptch section setup -- adds a new PE section for the cave code below,
# then gives it real file-backed bytes to write into
# ============================================================

def read_version_marker(data, pe, ptch_section):
    """Returns the embedded patcher version string from an existing .ptch
    section's raw data, or None if it's missing/unparseable (e.g. a build
    from before this versioning existed, or an unrelated .ptch section)."""
    off = ptch_section.PointerToRawData
    if not off:
        return None
    marker = bytes(data[off:off + VERSION_MARKER_SIZE])
    if not marker.startswith(VERSION_MARKER_PREFIX):
        return None
    rest = marker[len(VERSION_MARKER_PREFIX):]
    nul = rest.find(b"\x00")
    if nul == -1:
        return None
    version = rest[:nul].decode("ascii", errors="replace")
    return version or None


def add_ptch_section(data):
    pe = load_pe(data)

    existing_ptch = next((s for s in pe.sections if s.Name.rstrip(b"\x00") == b".ptch"), None)
    if existing_ptch is not None:
        found_version = read_version_marker(data, pe, existing_ptch)
        pe.close()
        if found_version == PATCHER_VERSION:
            raise RuntimeError(
                f"This exe was already patched by this exact version (v{PATCHER_VERSION}) -- nothing to do."
            )
        elif found_version is not None:
            raise RuntimeError(
                f"This exe was patched by an older/different version of this tool (v{found_version}); "
                f"you're running v{PATCHER_VERSION}. Restore from <name>.original-backup and re-run "
                f"this script to upgrade to the current fixes."
            )
        else:
            raise RuntimeError(
                "This exe already has a .ptch section -- it looks like it's already "
                "been patched by this tool (an older release that predates version tracking) "
                "or something else using the same section name. Refusing to patch an "
                "already-patched file; restore from <name>.original-backup first if you "
                "want to re-patch from scratch."
            )

    file_header_off = pe.FILE_HEADER.get_file_offset()
    num_sections_off = file_header_off + pe.FILE_HEADER.__field_offsets__["NumberOfSections"]
    opt_header_off = pe.OPTIONAL_HEADER.get_file_offset()
    size_of_image_off = opt_header_off + pe.OPTIONAL_HEADER.__field_offsets__["SizeOfImage"]

    last_section = pe.sections[-1]
    last_header_off = last_section.get_file_offset()
    new_header_off = last_header_off + 40
    first_raw_data_off = min(s.PointerToRawData for s in pe.sections if s.PointerToRawData > 0)
    if new_header_off + 40 > first_raw_data_off:
        pe.close()
        raise RuntimeError("Not enough spare room in the section header table to add .ptch")

    sa = pe.OPTIONAL_HEADER.SectionAlignment
    new_va = ((last_section.VirtualAddress + last_section.Misc_VirtualSize + sa - 1) // sa) * sa
    new_virtual_size = 0x1000
    new_size_of_image = ((new_va + new_virtual_size + sa - 1) // sa) * sa

    IMAGE_SCN_CNT_CODE = 0x00000020
    IMAGE_SCN_MEM_EXECUTE = 0x20000000
    IMAGE_SCN_MEM_READ = 0x40000000
    IMAGE_SCN_MEM_WRITE = 0x80000000
    characteristics = IMAGE_SCN_CNT_CODE | IMAGE_SCN_MEM_EXECUTE | IMAGE_SCN_MEM_READ | IMAGE_SCN_MEM_WRITE

    name_padded = b".ptch".ljust(8, b"\x00")
    new_section_header = struct.pack(
        "<8sIIIIIIHHI", name_padded, new_virtual_size, new_va,
        0, 0, 0, 0, 0, 0, characteristics,
    )
    existing = bytes(data[new_header_off:new_header_off + 40])
    if any(b != 0 for b in existing):
        pe.close()
        raise RuntimeError("Section header slot for .ptch isn't empty -- unexpected file layout")
    data[new_header_off:new_header_off + 40] = new_section_header

    old_num_sections = struct.unpack_from("<H", data, num_sections_off)[0]
    struct.pack_into("<H", data, num_sections_off, old_num_sections + 1)
    struct.pack_into("<I", data, size_of_image_off, new_size_of_image)
    pe.close()

    # Give it real file-backed bytes (it starts pure-virtual, zero-filled at
    # load, which the loader is fine with but we need actual file space to
    # write cave code into).
    pe2 = load_pe(data)
    ptch_section = [s for s in pe2.sections if s.Name.rstrip(b"\x00") == b".ptch"][0]
    file_align = pe2.OPTIONAL_HEADER.FileAlignment
    sec_hdr_off = ptch_section.get_file_offset()
    pe2.close()

    CAVE_FILE_SIZE = 0x400
    new_raw_data_offset = len(data)
    if new_raw_data_offset % file_align != 0:
        data.extend(b"\x00" * (file_align - (new_raw_data_offset % file_align)))
        new_raw_data_offset = len(data)
    data.extend(b"\x00" * CAVE_FILE_SIZE)

    size_of_raw_off = sec_hdr_off + 8 + 4 + 4
    pointer_to_raw_off = size_of_raw_off + 4
    struct.pack_into("<I", data, size_of_raw_off, CAVE_FILE_SIZE)
    struct.pack_into("<I", data, pointer_to_raw_off, new_raw_data_offset)

    version_marker = VERSION_MARKER_PREFIX + PATCHER_VERSION.encode("ascii") + b"\x00"
    assert len(version_marker) <= VERSION_MARKER_SIZE, "PATCHER_VERSION too long for the reserved marker space"
    data[new_raw_data_offset:new_raw_data_offset + len(version_marker)] = version_marker

    print(f"Added .ptch section: VA {hex(new_va + IMAGE_BASE)}, {CAVE_FILE_SIZE} bytes file-backed at offset {hex(new_raw_data_offset)}")
    print(f"Embedded version marker: v{PATCHER_VERSION}")
    return new_va + IMAGE_BASE, new_raw_data_offset, CAVE_FILE_SIZE


# ============================================================
# Fix 1: Pirate Hunt spawn-selection bounds-check guard
# ============================================================

def fix_pirate_hunt(data, pe, ptch_va, ptch_off, cave_cursor):
    label = "Pirate Hunt crash guard"
    PATCH_SITE_VA, RESUME_VA, LOOP_EXIT_VA = 0x00408c17, 0x00408c1d, 0x00408ca3
    ERROR_STR_VA, CATEGORY_VA, LOG_FUNC_VA = 0x5e45f0, 0x5cfcfc, 0x00592da0

    expected = bytes([0x8D, 0x04, 0x76, 0x8B, 0x55, 0xA4])
    off = verify_site(data, pe, PATCH_SITE_VA, expected, label)
    if off is None:
        FIXES_SKIPPED.append(label)
        return cave_cursor

    cave = bytearray()
    def emit(b): cave.extend(b)

    emit(bytes([0x83, 0xFE, 0xFF]))
    jnz_pos = len(cave)
    emit(bytes([0x0F, 0x85, 0, 0, 0, 0]))
    call_pos = len(cave)
    emit(bytes([0xE8, 0, 0, 0, 0]))
    next_offset = len(cave)
    emit(bytes([0x5B]))
    lea1_pos = len(cave)
    emit(bytes([0x8D, 0x83, 0, 0, 0, 0]))
    emit(bytes([0x50]))
    lea2_pos = len(cave)
    emit(bytes([0x8D, 0x83, 0, 0, 0, 0]))
    emit(bytes([0x50]))
    call2_pos = len(cave)
    emit(bytes([0xE8, 0, 0, 0, 0]))
    emit(bytes([0x83, 0xC4, 0x08]))
    jmp1_pos = len(cave)
    emit(bytes([0xE9, 0, 0, 0, 0]))
    resume_pos = len(cave)
    emit(bytes([0x8D, 0x04, 0x76]))
    emit(bytes([0x8B, 0x55, 0xA4]))
    jmp2_pos = len(cave)
    emit(bytes([0xE9, 0, 0, 0, 0]))

    cave_va = ptch_va + cave_cursor
    next_va = cave_va + next_offset

    struct.pack_into("<i", cave, jnz_pos + 2, (cave_va + resume_pos) - (cave_va + jnz_pos + 6))
    struct.pack_into("<i", cave, lea1_pos + 2, ERROR_STR_VA - next_va)
    struct.pack_into("<i", cave, lea2_pos + 2, CATEGORY_VA - next_va)
    struct.pack_into("<i", cave, call2_pos + 1, LOG_FUNC_VA - (cave_va + call2_pos + 5))
    struct.pack_into("<i", cave, jmp1_pos + 1, LOOP_EXIT_VA - (cave_va + jmp1_pos + 5))
    struct.pack_into("<i", cave, jmp2_pos + 1, RESUME_VA - (cave_va + jmp2_pos + 5))
    struct.pack_into("<i", cave, call_pos + 1, 0)

    data[ptch_off + cave_cursor: ptch_off + cave_cursor + len(cave)] = cave

    redirect = bytearray([0xE9, 0, 0, 0, 0, 0x90])
    struct.pack_into("<i", redirect, 1, cave_va - (PATCH_SITE_VA + 5))
    data[off:off + 6] = redirect

    print(f"  [OK] {label}")
    FIXES_APPLIED.append(label)
    return cave_cursor + len(cave)


def fix_pirate_hunt_format_string(data, pe):
    label = "Pirate Hunt crash guard #2 (\"duplicate ship-sets\" log call missing an argument)"
    STRING_VA = 0x5e4620
    ORIGINAL = b"%s duplicate ship-sets that need spawning."
    REPLACEMENT = b"Duplicate ship-sets need spawning."

    off = verify_site(data, pe, STRING_VA, ORIGINAL, label)
    if off is None:
        FIXES_SKIPPED.append(label)
        return

    padded = REPLACEMENT + b"\x00" * (len(ORIGINAL) - len(REPLACEMENT))
    data[off:off + len(ORIGINAL)] = padded

    print(f"  [OK] {label}")
    FIXES_APPLIED.append(label)


# ============================================================
# Fix 2: Music-track FMOD Sound leak
# ============================================================

def fix_music_leak(data, pe, ptch_va, ptch_off, cave_cursor):
    label = "Music player failure loop (FMOD Sound leak)"
    PATCH_SITE_VA, RESUME_VA, SOUND_RELEASE_VA = 0x00559fb0, 0x00559fb6, 0x005cf2dc

    expected = bytes([0x8B, 0x47, 0x50, 0x8D, 0x5F, 0x4C])
    off = verify_site(data, pe, PATCH_SITE_VA, expected, label)
    if off is None:
        FIXES_SKIPPED.append(label)
        return cave_cursor

    cave = bytearray()
    def emit(b): cave.extend(b)

    emit(bytes([0x83, 0x7F, 0x68, 0x00]))
    jz_pos = len(cave)
    emit(bytes([0x0F, 0x84, 0, 0, 0, 0]))
    emit(bytes([0xFF, 0x77, 0x68]))
    call_pos = len(cave)
    emit(bytes([0xE8, 0, 0, 0, 0]))
    next_offset = len(cave)
    emit(bytes([0x58]))
    add_pos = len(cave)
    emit(bytes([0x05, 0, 0, 0, 0]))
    emit(bytes([0xFF, 0x10]))
    skip_pos = len(cave)
    emit(bytes([0x8B, 0x47, 0x50]))
    emit(bytes([0x8D, 0x5F, 0x4C]))
    jmp_pos = len(cave)
    emit(bytes([0xE9, 0, 0, 0, 0]))

    cave_va = ptch_va + cave_cursor
    next_va = cave_va + next_offset

    struct.pack_into("<i", cave, jz_pos + 2, (cave_va + skip_pos) - (cave_va + jz_pos + 6))
    struct.pack_into("<i", cave, add_pos + 1, SOUND_RELEASE_VA - next_va)
    struct.pack_into("<i", cave, call_pos + 1, 0)
    struct.pack_into("<i", cave, jmp_pos + 1, RESUME_VA - (cave_va + jmp_pos + 5))

    data[ptch_off + cave_cursor: ptch_off + cave_cursor + len(cave)] = cave

    redirect = bytearray([0xE9, 0, 0, 0, 0, 0x90])
    struct.pack_into("<i", redirect, 1, cave_va - (PATCH_SITE_VA + 5))
    data[off:off + 6] = redirect

    print(f"  [OK] {label}")
    FIXES_APPLIED.append(label)
    return cave_cursor + len(cave)


# ============================================================
# Fix 3: correctWaypointsToFlyWith over-strict comparison
# ============================================================

def fix_burnvector_strict_compare(data, pe, ptch_va, ptch_off, cave_cursor):
    label = "Burn-vector spam #1 (over-strict waypoint comparison)"
    PATCH_SITE_VA, RESUME_VA, SKIP_VA = 0x00506d2a, 0x00506d44, 0x00506d67
    TARGET_X_OFF, TARGET_Y_OFF = 0xc8, 0xcc
    DIST_SQ_THRESHOLD = 0.25
    RELOC_TARGET_VA = 0x00506d35

    expected = bytes([0x8D, 0x8F, 0xC8, 0x00, 0x00, 0x00, 0x51, 0x8B, 0xC8,
                       0xFF, 0x15, 0xA4, 0xF4, 0x5C, 0x00,
                       0xC7, 0x45, 0xFC, 0xFF, 0xFF, 0xFF, 0xFF,
                       0x84, 0xC0, 0x75, 0x23])
    off = verify_site(data, pe, PATCH_SITE_VA, expected, label)
    if off is None:
        FIXES_SKIPPED.append(label)
        return cave_cursor

    cave = bytearray()
    def emit(b): cave.extend(b)

    emit(bytes([0xF3, 0x0F, 0x10, 0x45, (-0x1c) & 0xFF]))
    emit(bytes([0xF3, 0x0F, 0x5C, 0x87]) + struct.pack("<i", TARGET_X_OFF))
    emit(bytes([0xF3, 0x0F, 0x59, 0xC0]))
    emit(bytes([0xF3, 0x0F, 0x10, 0x4D, (-0x18) & 0xFF]))
    emit(bytes([0xF3, 0x0F, 0x5C, 0x8F]) + struct.pack("<i", TARGET_Y_OFF))
    emit(bytes([0xF3, 0x0F, 0x59, 0xC9]))
    emit(bytes([0xF3, 0x0F, 0x58, 0xC1]))
    call_pos = len(cave)
    emit(bytes([0xE8, 0, 0, 0, 0]))
    next_offset = len(cave)
    emit(bytes([0x5B]))
    comiss_pos = len(cave)
    emit(bytes([0x0F, 0x2F, 0x83, 0, 0, 0, 0]))
    jb_pos = len(cave)
    emit(bytes([0x0F, 0x82, 0, 0, 0, 0]))
    jmp_pos = len(cave)
    emit(bytes([0xE9, 0, 0, 0, 0]))
    const_pos = len(cave)
    emit(struct.pack("<f", DIST_SQ_THRESHOLD))

    cave_va = ptch_va + cave_cursor
    next_va = cave_va + next_offset
    const_va = cave_va + const_pos

    struct.pack_into("<i", cave, call_pos + 1, 0)
    struct.pack_into("<i", cave, comiss_pos + 3, const_va - next_va)
    struct.pack_into("<i", cave, jb_pos + 2, SKIP_VA - (cave_va + jb_pos + 6))
    struct.pack_into("<i", cave, jmp_pos + 1, RESUME_VA - (cave_va + jmp_pos + 5))

    data[ptch_off + cave_cursor: ptch_off + cave_cursor + len(cave)] = cave

    redirect = bytearray([0xE9, 0, 0, 0, 0])
    struct.pack_into("<i", redirect, 1, cave_va - (PATCH_SITE_VA + 5))
    redirect += b"\x90" * (len(expected) - len(redirect))
    data[off:off + len(expected)] = redirect

    neutralize_relocations(data, pe, RELOC_TARGET_VA, 4, label)

    print(f"  [OK] {label}")
    FIXES_APPLIED.append(label)
    return cave_cursor + len(cave)


# ============================================================
# Fix 4: switchTravelState per-frame recompute (pure control flow, no cave)
# ============================================================

def fix_burnvector_travelstate(data, pe):
    label = "Burn-vector spam #2 (switchTravelState per-frame recompute)"
    PATCH_SITE_VA, EXIT_VA = 0x00517195, 0x00517286

    expected = bytes([0x83, 0xF8, 0x02, 0x0F, 0x85, 0xE8, 0x00, 0x00, 0x00])
    off = verify_site(data, pe, PATCH_SITE_VA, expected, label)
    if off is None:
        FIXES_SKIPPED.append(label)
        return

    redirect = bytearray([0xE9, 0, 0, 0, 0])
    struct.pack_into("<i", redirect, 1, EXIT_VA - (PATCH_SITE_VA + 5))
    redirect += b"\x90" * (len(expected) - len(redirect))
    data[off:off + len(expected)] = redirect

    print(f"  [OK] {label}")
    FIXES_APPLIED.append(label)


# ============================================================
# Fix 5: resetBurnVector numerical instability near singularity
# ============================================================

def fix_burnvector_singularity(data, pe, ptch_va, ptch_off, cave_cursor):
    label = "Burn-vector spam #3 (numerical instability / singularity)"
    PATCH_SITE_VA, RESUME_VA = 0x005170b7, 0x005170bf
    DIFF_X_EBP_OFF, DIFF_Y_EBP_OFF = -0x20, -0x1c
    MAG_SQ_THRESHOLD = 0.0001

    expected = bytes([0xF3, 0x0F, 0x11, 0x86, 0xCC, 0x02, 0x00, 0x00])
    off = verify_site(data, pe, PATCH_SITE_VA, expected, label)
    if off is None:
        FIXES_SKIPPED.append(label)
        return cave_cursor

    neutralize_relocations(data, pe, PATCH_SITE_VA, len(expected), label)

    cave = bytearray()
    def emit(b): cave.extend(b)

    emit(bytes([0x53]))
    emit(bytes([0xF3, 0x0F, 0x10, 0x4D]) + struct.pack("<b", DIFF_X_EBP_OFF))
    emit(bytes([0xF3, 0x0F, 0x59, 0xC9]))
    emit(bytes([0xF3, 0x0F, 0x10, 0x55]) + struct.pack("<b", DIFF_Y_EBP_OFF))
    emit(bytes([0xF3, 0x0F, 0x59, 0xD2]))
    emit(bytes([0xF3, 0x0F, 0x58, 0xCA]))
    call_pos = len(cave)
    emit(bytes([0xE8, 0, 0, 0, 0]))
    next_offset = len(cave)
    emit(bytes([0x5B]))
    comiss_pos = len(cave)
    emit(bytes([0x0F, 0x2F, 0x8B, 0, 0, 0, 0]))
    emit(bytes([0x5B]))
    jb_pos = len(cave)
    emit(bytes([0x72, 0]))
    emit(expected)
    skip_store_pos = len(cave)
    jmp_pos = len(cave)
    emit(bytes([0xE9, 0, 0, 0, 0]))
    const_thresh_pos = len(cave)
    emit(struct.pack("<f", MAG_SQ_THRESHOLD))

    cave_va = ptch_va + cave_cursor
    next_va = cave_va + next_offset

    struct.pack_into("<i", cave, call_pos + 1, 0)
    struct.pack_into("<i", cave, comiss_pos + 3, (cave_va + const_thresh_pos) - next_va)
    jb_rel8 = skip_store_pos - (jb_pos + 2)
    assert -128 <= jb_rel8 <= 127
    cave[jb_pos + 1] = jb_rel8 & 0xFF
    struct.pack_into("<i", cave, jmp_pos + 1, RESUME_VA - (cave_va + jmp_pos + 5))

    data[ptch_off + cave_cursor: ptch_off + cave_cursor + len(cave)] = cave

    redirect = bytearray([0xE9, 0, 0, 0, 0])
    struct.pack_into("<i", redirect, 1, cave_va - (PATCH_SITE_VA + 5))
    redirect += b"\x90" * (len(expected) - len(redirect))
    data[off:off + len(expected)] = redirect

    print(f"  [OK] {label}")
    FIXES_APPLIED.append(label)
    return cave_cursor + len(cave)


# ============================================================
# Fix 6: Structure::getRoom logs an ERROR for a nonexistent room id even
# when a caller is only probing whether one exists (pure control flow,
# no cave)
# ============================================================

def fix_unknown_room_spam(data, pe):
    label = "\"Unknown room\" log spam cycling past a ship's last room"
    PATCH_SITE_VA, EXIT_VA = 0x0055a79d, 0x0055a7b9

    expected = bytes([
        0x83, 0x7E, 0x14, 0x10,
        0x72, 0x02,
        0x8B, 0x36,
        0x56,
        0x57,
        0x68, 0xC8, 0x5F, 0x62, 0x00,
        0x68, 0xFC, 0xFC, 0x5C, 0x00,
        0xE8, 0xEA, 0x85, 0x03, 0x00,
        0x83, 0xC4, 0x10,
    ])
    off = verify_site(data, pe, PATCH_SITE_VA, expected, label)
    if off is None:
        FIXES_SKIPPED.append(label)
        return

    neutralize_relocations(data, pe, PATCH_SITE_VA, len(expected), label)

    redirect = bytearray([0xE9, 0, 0, 0, 0])
    struct.pack_into("<i", redirect, 1, EXIT_VA - (PATCH_SITE_VA + 5))
    redirect += b"\x90" * (len(expected) - len(redirect))
    data[off:off + len(expected)] = redirect

    print(f"  [OK] {label}")
    FIXES_APPLIED.append(label)


# ============================================================
# Fix 7: PDA-open crash guard -- ignore the "open tablet" command while a
# character's head-overlay portrait is mid-render (see BUG-009: the actual
# crash is a missing null-check inside libcocos2d.dll's batch renderer when
# two render-to-texture passes collide in the same frame; rather than patch
# the third-party engine DLL, this closes the only known trigger from the
# ois.exe side -- a one-byte reentrancy flag set for the duration of each
# character's portrait refresh, checked at the top of showTablet)
# ============================================================

def fix_pda_render_guard(data, pe, ptch_va, ptch_off, cave_cursor):
    label = "PDA-open crash guard (ignore Tab while a character portrait is mid-render)"
    SET_SITE_VA, SET_RESUME_VA = 0x00537cb0, 0x00537cb5
    CLEAR_SITE_VA, CLEAR_RESUME_VA = 0x00538658, 0x00538662
    CHECK_SITE_VA, CHECK_RESUME_VA = 0x00530b90, 0x00530b97

    expected_set = bytes([0x55, 0x8B, 0xEC, 0x6A, 0xFF])
    off_set = verify_site(data, pe, SET_SITE_VA, expected_set, label + " (set site)")
    if off_set is None:
        FIXES_SKIPPED.append(label)
        return cave_cursor

    expected_clear = bytes([0x8B, 0x4D, 0xF4, 0x64, 0x89, 0x0D, 0x00, 0x00, 0x00, 0x00])
    off_clear = verify_site(data, pe, CLEAR_SITE_VA, expected_clear, label + " (clear site)")
    if off_clear is None:
        FIXES_SKIPPED.append(label)
        return cave_cursor

    expected_check = bytes([0x55, 0x8B, 0xEC, 0x83, 0xE4, 0xF8, 0x51])
    off_check = verify_site(data, pe, CHECK_SITE_VA, expected_check, label + " (check site)")
    if off_check is None:
        FIXES_SKIPPED.append(label)
        return cave_cursor

    cave = bytearray()
    def emit(b): cave.extend(b)

    # shared reentrancy flag byte (zero-initialized -- the whole cave starts zeroed)
    flag_pos = len(cave)
    emit(bytes([0x00]))

    # --- block A: set flag=1, replay original 5 bytes, resume ---
    call_posA = len(cave)
    emit(bytes([0xE8, 0, 0, 0, 0]))            # CALL $+5
    next_offA = len(cave)
    emit(bytes([0x58]))                         # POP EAX -> PIC anchor
    movA_pos = len(cave)
    emit(bytes([0xC6, 0x80, 0, 0, 0, 0, 0x01]))  # MOV byte ptr [EAX+disp32],1
    emit(expected_set)
    jmpA_pos = len(cave)
    emit(bytes([0xE9, 0, 0, 0, 0]))

    # --- block B: clear flag=0, replay original 10 bytes, resume ---
    call_posB = len(cave)
    emit(bytes([0xE8, 0, 0, 0, 0]))
    next_offB = len(cave)
    emit(bytes([0x58]))
    movB_pos = len(cave)
    emit(bytes([0xC6, 0x80, 0, 0, 0, 0, 0x00]))  # MOV byte ptr [EAX+disp32],0
    emit(expected_clear)
    jmpB_pos = len(cave)
    emit(bytes([0xE9, 0, 0, 0, 0]))

    # --- block C: if flag set, bail out (RET 4) ignoring the open-tablet
    # command entirely; else replay original 7 bytes and resume normally ---
    call_posC = len(cave)
    emit(bytes([0xE8, 0, 0, 0, 0]))
    next_offC = len(cave)
    emit(bytes([0x58]))
    cmp_pos = len(cave)
    emit(bytes([0x80, 0xB8, 0, 0, 0, 0, 0x00]))  # CMP byte ptr [EAX+disp32],0
    jz_pos = len(cave)
    emit(bytes([0x74, 0]))                       # JZ do_normal
    emit(bytes([0xC2, 0x04, 0x00]))              # RET 0x4 (ignore the command)
    do_normal_pos = len(cave)
    emit(expected_check)
    jmpC_pos = len(cave)
    emit(bytes([0xE9, 0, 0, 0, 0]))

    cave_va = ptch_va + cave_cursor
    flag_va = cave_va + flag_pos

    struct.pack_into("<i", cave, call_posA + 1, 0)
    struct.pack_into("<i", cave, movA_pos + 2, flag_va - (cave_va + next_offA))
    struct.pack_into("<i", cave, jmpA_pos + 1, SET_RESUME_VA - (cave_va + jmpA_pos + 5))

    struct.pack_into("<i", cave, call_posB + 1, 0)
    struct.pack_into("<i", cave, movB_pos + 2, flag_va - (cave_va + next_offB))
    struct.pack_into("<i", cave, jmpB_pos + 1, CLEAR_RESUME_VA - (cave_va + jmpB_pos + 5))

    struct.pack_into("<i", cave, call_posC + 1, 0)
    struct.pack_into("<i", cave, cmp_pos + 2, flag_va - (cave_va + next_offC))
    jz_rel8 = do_normal_pos - (jz_pos + 2)
    assert -128 <= jz_rel8 <= 127
    cave[jz_pos + 1] = jz_rel8 & 0xFF
    struct.pack_into("<i", cave, jmpC_pos + 1, CHECK_RESUME_VA - (cave_va + jmpC_pos + 5))

    data[ptch_off + cave_cursor: ptch_off + cave_cursor + len(cave)] = cave

    redirectA = bytearray([0xE9, 0, 0, 0, 0])
    struct.pack_into("<i", redirectA, 1, (cave_va + call_posA) - (SET_SITE_VA + 5))
    data[off_set:off_set + len(expected_set)] = redirectA

    redirectB = bytearray([0xE9, 0, 0, 0, 0])
    struct.pack_into("<i", redirectB, 1, (cave_va + call_posB) - (CLEAR_SITE_VA + 5))
    redirectB += b"\x90" * (len(expected_clear) - len(redirectB))
    data[off_clear:off_clear + len(expected_clear)] = redirectB

    redirectC = bytearray([0xE9, 0, 0, 0, 0])
    struct.pack_into("<i", redirectC, 1, (cave_va + call_posC) - (CHECK_SITE_VA + 5))
    redirectC += b"\x90" * (len(expected_check) - len(redirectC))
    data[off_check:off_check + len(expected_check)] = redirectC

    print(f"  [OK] {label}")
    FIXES_APPLIED.append(label)
    return cave_cursor + len(cave)


# ============================================================
# Fix 8 (fix8-fix11): DEL command match-branch crash + extension OOB +
# DIR listing skip + distinct Deleted/protected messages
# ============================================================

def fix_del_command(data, pe, ptch_va, ptch_off, cave_cursor):
    label = "Mail terminal DEL crash + delete-a-COM-command feature"

    # --- fix8: matched-command branch, corrected flag-address formula ---
    PATCH_SITE_VA, PATCH_SITE_END = 0x00548f34, 0x00549029
    PATCH_SITE_LEN = PATCH_SITE_END - PATCH_SITE_VA
    PROTECTED_MSG_VA = 0x00548ff5
    RESUME_VA = PATCH_SITE_END

    expected_start = bytes([0x8B, 0x4F, 0x2C, 0x8D, 0x5F, 0x18])
    off = verify_site(data, pe, PATCH_SITE_VA, expected_start, label + " (fix8 site)")
    if off is None:
        FIXES_SKIPPED.append(label)
        return cave_cursor
    tail_expected = bytes([0xE8, 0x5A, 0x4F, 0xEE, 0xFF, 0x8B, 0x7D, 0xD4])
    tail_off = va_to_offset(pe, PATCH_SITE_END - len(tail_expected))
    if tail_off is None or bytes(data[tail_off:tail_off + len(tail_expected)]) != tail_expected:
        print(f"  [SKIP] {label}: fix8 patch-site tail mismatch")
        FIXES_SKIPPED.append(label)
        return cave_cursor

    neutralize_relocations(data, pe, PATCH_SITE_VA, PATCH_SITE_LEN, label + " (fix8)")

    cave = bytearray()
    def emit(b): cave.extend(b)

    emit(bytes([0x89, 0xCB]))
    emit(bytes([0x8B, 0x45, 0xF0]))
    emit(bytes([0x8B, 0x40, 0x44]))
    emit(bytes([0x89, 0xDA]))
    emit(bytes([0x29, 0xC2]))
    emit(bytes([0x89, 0xC3]))
    emit(bytes([0x89, 0xD0]))
    emit(bytes([0x31, 0xD2]))
    emit(bytes([0xB9, 0x78, 0x00, 0x00, 0x00]))
    emit(bytes([0xF7, 0xF1]))
    emit(bytes([0x69, 0xC8, 0x78, 0x00, 0x00, 0x00]))
    emit(bytes([0x01, 0xD9]))
    # flag byte lives inside each entry's own struct at entry+0x48 -- NOT a
    # separately packed array; ECX already holds the entry address here.
    emit(bytes([0x8D, 0x51, 0x48]))
    emit(bytes([0x0F, 0xB6, 0x12]))
    emit(bytes([0x85, 0xD2]))
    jnz_pos = len(cave)
    emit(bytes([0x75, 0]))
    emit(bytes([0xC6, 0x01, 0x00]))
    emit(bytes([0xC7, 0x41, 0x10, 0x00, 0x00, 0x00, 0x00]))
    emit(bytes([0x8B, 0x7D, 0xD4]))
    jmp_resume_pos = len(cave)
    emit(bytes([0xE9, 0, 0, 0, 0]))
    protected_pos = len(cave)
    emit(bytes([0xE9, 0, 0, 0, 0]))

    cave_va = ptch_va + cave_cursor
    jnz_rel8 = protected_pos - (jnz_pos + 2)
    assert -128 <= jnz_rel8 <= 127
    cave[jnz_pos + 1] = jnz_rel8 & 0xFF
    struct.pack_into("<i", cave, jmp_resume_pos + 1, RESUME_VA - (cave_va + jmp_resume_pos + 5))
    struct.pack_into("<i", cave, protected_pos + 1, PROTECTED_MSG_VA - (cave_va + protected_pos + 5))

    fix8_cave_va = cave_va
    data[ptch_off + cave_cursor: ptch_off + cave_cursor + len(cave)] = cave

    redirect = bytearray([0xE9, 0, 0, 0, 0])
    struct.pack_into("<i", redirect, 1, cave_va - (PATCH_SITE_VA + 5))
    redirect += b"\x90" * (PATCH_SITE_LEN - len(redirect))
    data[off:off + PATCH_SITE_LEN] = redirect

    cave_cursor += len(cave)

    # --- fix9: extension token read past the end of a single-element vector ---
    PATCH_SITE_VA2, RESUME_VA2, SKIP_VA2 = 0x005490ae, 0x005490b4, 0x0054910c
    expected2 = bytes([0x8B, 0x4F, 0x2C, 0x8D, 0x5F, 0x18])
    off2 = verify_site(data, pe, PATCH_SITE_VA2, expected2, label + " (fix9 site)")
    if off2 is None:
        FIXES_SKIPPED.append(label)
        return cave_cursor

    cave2 = bytearray()
    def emit2(b): cave2.extend(b)

    emit2(bytes([0x8B, 0x4D, 0xD8]))
    emit2(bytes([0x2B, 0x4D, 0xD4]))
    emit2(bytes([0xB8, 0xAB, 0xAA, 0xAA, 0x2A]))
    emit2(bytes([0xF7, 0xE9]))
    emit2(bytes([0xC1, 0xFA, 0x02]))
    emit2(bytes([0x8B, 0xC2]))
    emit2(bytes([0xC1, 0xE8, 0x1F]))
    emit2(bytes([0x03, 0xC2]))
    emit2(bytes([0x83, 0xF8, 0x01]))
    jbe_pos = len(cave2)
    emit2(bytes([0x76, 0]))
    emit2(bytes([0x8B, 0x4F, 0x2C]))
    emit2(bytes([0x8D, 0x5F, 0x18]))
    jmp_resume_pos2 = len(cave2)
    emit2(bytes([0xE9, 0, 0, 0, 0]))
    skip_pos2 = len(cave2)
    emit2(bytes([0x8B, 0x7D, 0xD4]))
    jmp_skip_pos2 = len(cave2)
    emit2(bytes([0xE9, 0, 0, 0, 0]))

    cave_va2 = ptch_va + cave_cursor
    jbe_rel8 = skip_pos2 - (jbe_pos + 2)
    assert -128 <= jbe_rel8 <= 127
    cave2[jbe_pos + 1] = jbe_rel8 & 0xFF
    struct.pack_into("<i", cave2, jmp_resume_pos2 + 1, RESUME_VA2 - (cave_va2 + jmp_resume_pos2 + 5))
    struct.pack_into("<i", cave2, jmp_skip_pos2 + 1, SKIP_VA2 - (cave_va2 + jmp_skip_pos2 + 5))

    data[ptch_off + cave_cursor: ptch_off + cave_cursor + len(cave2)] = cave2

    redirect2 = bytearray([0xE9, 0, 0, 0, 0])
    struct.pack_into("<i", redirect2, 1, cave_va2 - (PATCH_SITE_VA2 + 5))
    redirect2 += b"\x90" * (6 - len(redirect2))
    data[off2:off2 + 6] = redirect2

    cave_cursor += len(cave2)

    # --- fix10: cmd_DIR listing loop skips zero-length (deleted) entries ---
    PATCH_SITE_VA3, RESUME_VA3, EXIT_VA3 = 0x00548530, 0x00548535, 0x0054859a
    expected3 = bytes([0x83, 0x7C, 0x33, 0x14, 0x10])
    off3 = verify_site(data, pe, PATCH_SITE_VA3, expected3, label + " (fix10 site)")
    if off3 is None:
        FIXES_SKIPPED.append(label)
        return cave_cursor

    cave3 = bytearray()
    def emit3(b): cave3.extend(b)

    emit3(bytes([0x83, 0x7C, 0x33, 0x10, 0x00]))
    jnz_pos3 = len(cave3)
    emit3(bytes([0x0F, 0x85, 0, 0, 0, 0]))
    emit3(bytes([0x8B, 0x4D, 0xEC]))
    emit3(bytes([0xFF, 0x45, 0xF0]))
    emit3(bytes([0x83, 0xC3, 0x78]))
    emit3(bytes([0x8B, 0x79, 0x48]))
    emit3(bytes([0x8B, 0x71, 0x44]))
    emit3(bytes([0xB8, 0x89, 0x88, 0x88, 0x88]))
    emit3(bytes([0x8B, 0xCF]))
    emit3(bytes([0x2B, 0xCE]))
    emit3(bytes([0xF7, 0xE9]))
    emit3(bytes([0x03, 0xD1]))
    emit3(bytes([0xC1, 0xFA, 0x06]))
    emit3(bytes([0x8B, 0xC2]))
    emit3(bytes([0xC1, 0xE8, 0x1F]))
    emit3(bytes([0x03, 0xC2]))
    emit3(bytes([0x39, 0x45, 0xF0]))
    jc_pos3 = len(cave3)
    emit3(bytes([0x0F, 0x82, 0, 0, 0, 0]))
    jmp_exit_pos3 = len(cave3)
    emit3(bytes([0xE9, 0, 0, 0, 0]))
    replay_pos3 = len(cave3)
    emit3(bytes([0x83, 0x7C, 0x33, 0x14, 0x10]))
    jmp_resume_pos3 = len(cave3)
    emit3(bytes([0xE9, 0, 0, 0, 0]))

    cave_va3 = ptch_va + cave_cursor
    struct.pack_into("<i", cave3, jnz_pos3 + 2, replay_pos3 - (jnz_pos3 + 6))
    struct.pack_into("<i", cave3, jc_pos3 + 2, PATCH_SITE_VA3 - (cave_va3 + jc_pos3 + 6))
    struct.pack_into("<i", cave3, jmp_exit_pos3 + 1, EXIT_VA3 - (cave_va3 + jmp_exit_pos3 + 5))
    struct.pack_into("<i", cave3, jmp_resume_pos3 + 1, RESUME_VA3 - (cave_va3 + jmp_resume_pos3 + 5))

    data[ptch_off + cave_cursor: ptch_off + cave_cursor + len(cave3)] = cave3

    redirect3 = bytearray([0xE9, 0, 0, 0, 0])
    struct.pack_into("<i", redirect3, 1, cave_va3 - (PATCH_SITE_VA3 + 5))
    data[off3:off3 + 5] = redirect3

    cave_cursor += len(cave3)

    # --- fix11: distinct "Deleted." / "cannot delete system file" messages ---
    ASSIGN_FN_VA, ADDLINE_FN_VA = 0x004028d0, 0x0042df80
    PROTECTED_EXISTING_STR_VA = 0x62376c
    RESUME_VA4 = 0x00549029

    fix8_redirect = bytes(data[off:off + 5])
    fix8_cave_va_check = PATCH_SITE_VA + 5 + struct.unpack("<i", fix8_redirect[1:5])[0]
    resume_jmp_off = va_to_offset(pe, fix8_cave_va_check + 0x38)
    protected_jmp_off = va_to_offset(pe, fix8_cave_va_check + 0x3D)
    resume_jmp = bytes(data[resume_jmp_off:resume_jmp_off + 5]) if resume_jmp_off else b""
    protected_jmp = bytes(data[protected_jmp_off:protected_jmp_off + 5]) if protected_jmp_off else b""
    if (resume_jmp_off is None or protected_jmp_off is None
            or resume_jmp[:1] != b"\xE9" or protected_jmp[:1] != b"\xE9"):
        print(f"  [SKIP] {label}: fix11 couldn't locate fix8's exit jumps")
        FIXES_SKIPPED.append(label)
        return cave_cursor

    def emit_message_block(cave, length, pic_targets, fixed_calls, resume_jmps):
        block_pos = len(cave)
        cave.extend(bytes([0x83, 0xEC, 0x18]))
        cave.extend(bytes([0xC6, 0x45, 0x0B, 0x01]))
        cave.extend(bytes([0x8B, 0xCC]))
        cave.extend(bytes([0x6A, length]))
        cave.extend(bytes([0xC7, 0x41, 0x10, 0x00, 0x00, 0x00, 0x00]))
        cave.extend(bytes([0xC7, 0x41, 0x14, 0x0F, 0x00, 0x00, 0x00]))
        call_pos = len(cave)
        cave.extend(bytes([0xE8, 0x00, 0x00, 0x00, 0x00]))
        cave.extend(bytes([0x58]))
        add_pos = len(cave)
        cave.extend(bytes([0x05, 0, 0, 0, 0]))
        pic_targets.append((call_pos, add_pos))
        cave.extend(bytes([0x50]))
        cave.extend(bytes([0xC6, 0x01, 0x00]))
        assign_call_pos = len(cave)
        cave.extend(bytes([0xE8, 0, 0, 0, 0]))
        fixed_calls.append((assign_call_pos, ASSIGN_FN_VA))
        cave.extend(bytes([0x8B, 0x45, 0xF0]))
        cave.extend(bytes([0x8B, 0x48, 0x2C]))
        addline_call_pos = len(cave)
        cave.extend(bytes([0xE8, 0, 0, 0, 0]))
        fixed_calls.append((addline_call_pos, ADDLINE_FN_VA))
        cave.extend(bytes([0x8B, 0x7D, 0xD4]))
        jmp_pos = len(cave)
        cave.extend(bytes([0xE9, 0, 0, 0, 0]))
        resume_jmps.append(jmp_pos)
        return block_pos

    cave4 = bytearray()
    pic_targets, fixed_calls, resume_jmps = [], [], []
    deleted_block_pos = emit_message_block(cave4, 0x08, pic_targets, fixed_calls, resume_jmps)
    deleted_pic = pic_targets[-1]
    protected_block_pos = emit_message_block(cave4, 0x1B, pic_targets, fixed_calls, resume_jmps)
    protected_pic = pic_targets[-1]
    deleted_str_pos = len(cave4)
    cave4.extend(b"Deleted.\x00")

    cave_va4 = ptch_va + cave_cursor
    deleted_call_pos, deleted_add_pos = deleted_pic
    struct.pack_into("<i", cave4, deleted_add_pos + 1,
                      (cave_va4 + deleted_str_pos) - (cave_va4 + deleted_call_pos + 5))
    protected_call_pos, protected_add_pos = protected_pic
    struct.pack_into("<i", cave4, protected_add_pos + 1,
                      PROTECTED_EXISTING_STR_VA - (cave_va4 + protected_call_pos + 5))
    for pos, target_va in fixed_calls:
        struct.pack_into("<i", cave4, pos + 1, target_va - (cave_va4 + pos + 5))
    for pos in resume_jmps:
        struct.pack_into("<i", cave4, pos + 1, RESUME_VA4 - (cave_va4 + pos + 5))

    data[ptch_off + cave_cursor: ptch_off + cave_cursor + len(cave4)] = cave4

    deleted_block_va = cave_va4 + deleted_block_pos
    protected_block_va = cave_va4 + protected_block_pos
    new_resume_jmp = bytearray([0xE9, 0, 0, 0, 0])
    struct.pack_into("<i", new_resume_jmp, 1, deleted_block_va - (fix8_cave_va_check + 0x38 + 5))
    data[resume_jmp_off:resume_jmp_off + 5] = new_resume_jmp
    new_protected_jmp = bytearray([0xE9, 0, 0, 0, 0])
    struct.pack_into("<i", new_protected_jmp, 1, protected_block_va - (fix8_cave_va_check + 0x3D + 5))
    data[protected_jmp_off:protected_jmp_off + 5] = new_protected_jmp

    cave_cursor += len(cave4)

    print(f"  [OK] {label}")
    FIXES_APPLIED.append(label)
    return cave_cursor


# ============================================================
# Fix 9: Pirate Hunt spawn-selection bounds-check guard -- ois_server.exe
# copy of the same bug as fix_pirate_hunt above. ois.exe and ois_server.exe
# both compile GameLogic::resetShipsInScenario; the missing bounds-check
# exists in both binaries at different absolute addresses. Singleplayer
# never touches ois_server.exe (confirmed live -- only ois.exe runs), so
# this only matters for anyone hosting or joining a co-op game, where
# ois_server.exe runs as its own real process. Patched separately from
# ois.exe's fixes above -- own backup, own .ptch section, own version
# marker -- since it's a completely different binary.
# ============================================================

def fix_pirate_hunt_server(data, pe, ptch_va, ptch_off, cave_cursor):
    label = "Pirate Hunt crash guard (server)"
    PATCH_SITE_VA, RESUME_VA, LOOP_EXIT_VA = 0x00408947, 0x0040894d, 0x004089d3
    ERROR_STR_VA, CATEGORY_VA, LOG_FUNC_VA = 0x5e2478, 0x5cdc34, 0x00591070

    expected = bytes([0x8D, 0x04, 0x76, 0x8B, 0x55, 0xA4])
    off = verify_site(data, pe, PATCH_SITE_VA, expected, label)
    if off is None:
        SERVER_FIXES_SKIPPED.append(label)
        return cave_cursor

    cave = bytearray()
    def emit(b): cave.extend(b)

    emit(bytes([0x83, 0xFE, 0xFF]))
    jnz_pos = len(cave)
    emit(bytes([0x0F, 0x85, 0, 0, 0, 0]))
    call_pos = len(cave)
    emit(bytes([0xE8, 0, 0, 0, 0]))
    next_offset = len(cave)
    emit(bytes([0x5B]))
    lea1_pos = len(cave)
    emit(bytes([0x8D, 0x83, 0, 0, 0, 0]))
    emit(bytes([0x50]))
    lea2_pos = len(cave)
    emit(bytes([0x8D, 0x83, 0, 0, 0, 0]))
    emit(bytes([0x50]))
    call2_pos = len(cave)
    emit(bytes([0xE8, 0, 0, 0, 0]))
    emit(bytes([0x83, 0xC4, 0x08]))
    jmp1_pos = len(cave)
    emit(bytes([0xE9, 0, 0, 0, 0]))
    resume_pos = len(cave)
    emit(bytes([0x8D, 0x04, 0x76]))
    emit(bytes([0x8B, 0x55, 0xA4]))
    jmp2_pos = len(cave)
    emit(bytes([0xE9, 0, 0, 0, 0]))

    cave_va = ptch_va + cave_cursor
    next_va = cave_va + next_offset

    struct.pack_into("<i", cave, jnz_pos + 2, (cave_va + resume_pos) - (cave_va + jnz_pos + 6))
    struct.pack_into("<i", cave, lea1_pos + 2, ERROR_STR_VA - next_va)
    struct.pack_into("<i", cave, lea2_pos + 2, CATEGORY_VA - next_va)
    struct.pack_into("<i", cave, call2_pos + 1, LOG_FUNC_VA - (cave_va + call2_pos + 5))
    struct.pack_into("<i", cave, jmp1_pos + 1, LOOP_EXIT_VA - (cave_va + jmp1_pos + 5))
    struct.pack_into("<i", cave, jmp2_pos + 1, RESUME_VA - (cave_va + jmp2_pos + 5))
    struct.pack_into("<i", cave, call_pos + 1, 0)

    data[ptch_off + cave_cursor: ptch_off + cave_cursor + len(cave)] = cave

    redirect = bytearray([0xE9, 0, 0, 0, 0, 0x90])
    struct.pack_into("<i", redirect, 1, cave_va - (PATCH_SITE_VA + 5))
    data[off:off + 6] = redirect

    print(f"  [OK] {label}")
    SERVER_FIXES_APPLIED.append(label)
    return cave_cursor + len(cave)


def fix_pirate_hunt_format_string_server(data, pe):
    label = "Pirate Hunt crash guard #2, server (\"duplicate ship-sets\" log call missing an argument)"
    STRING_VA = 0x5e24a8
    ORIGINAL = b"%s duplicate ship-sets that need spawning."
    REPLACEMENT = b"Duplicate ship-sets need spawning."

    off = verify_site(data, pe, STRING_VA, ORIGINAL, label)
    if off is None:
        SERVER_FIXES_SKIPPED.append(label)
        return

    padded = REPLACEMENT + b"\x00" * (len(ORIGINAL) - len(REPLACEMENT))
    data[off:off + len(ORIGINAL)] = padded

    print(f"  [OK] {label}")
    SERVER_FIXES_APPLIED.append(label)


def patch_server_exe(exe_path):
    """Patches ois_server.exe, which ships alongside ois.exe in every
    Windows Steam install -- separate file, separate backup, separate
    .ptch section. Skips quietly (not an error) in the rare case it's
    genuinely missing (e.g. a modified install)."""
    server_path = exe_path.parent / "ois_server.exe"
    if not server_path.is_file():
        print(f"\n[SKIP] ois_server.exe not found next to {exe_path.name} -- skipping server-side fixes "
              f"(only matters for hosting/joining co-op games).")
        return False

    try:
        data = bytearray(server_path.read_bytes())
    except OSError as e:
        print(f"\n[SKIP] Could not read {server_path}: {e}")
        return False

    ok, reason = validate_pe(data, server_path.name)
    if not ok:
        print(f"\n[SKIP] {reason}", file=sys.stderr)
        return False

    backup_path = server_path.with_name(server_path.name + BACKUP_SUFFIX)
    if backup_path.exists():
        print(f"\nServer backup already exists at {backup_path} -- not overwriting it.")
    else:
        try:
            backup_path.write_bytes(data)
        except OSError as e:
            print(f"\n[SKIP] Could not write the server backup to {backup_path}: {e}")
            return False
        print(f"\nBacked up original server exe to {backup_path}")

    print("Adding patch section to ois_server.exe...")
    try:
        ptch_va, ptch_off, ptch_size = add_ptch_section(data)
    except RuntimeError as e:
        print(f"ois_server.exe: {e}")
        return False

    pe = load_pe(data)
    pe.parse_data_directories()

    print("Applying server-side fixes:")
    cave_cursor = VERSION_MARKER_SIZE
    cave_cursor = fix_pirate_hunt_server(data, pe, ptch_va, ptch_off, cave_cursor)
    fix_pirate_hunt_format_string_server(data, pe)
    pe.close()

    if cave_cursor > ptch_size:
        print(f"ERROR: server cave usage ({cave_cursor} bytes) exceeded reserved space ({ptch_size} bytes) -- "
              f"aborting without writing ois_server.exe.", file=sys.stderr)
        return False

    server_path.write_bytes(data)
    print(f"Applied {len(SERVER_FIXES_APPLIED)} server fix(es), skipped {len(SERVER_FIXES_SKIPPED)}.")
    print(f"Patched: {server_path}")
    return True


# ============================================================
# Data-only mod install (scenario typo, dead hair tokens, mesh typo --
# see apply_data_fixes.py; generated from the user's own game files
# rather than shipped as full copies, since those are Flat Earth
# Games' own copyrighted content, not this project's)
# ============================================================

def find_bundled_mod_dir():
    """Look for mod/oisbugfix next to this script first (how it's meant to
    ship); also check two levels up, in case this script is nested a
    couple of directories deep inside a larger checkout."""
    here = Path(__file__).resolve().parent
    candidates = [
        here / "mod" / "oisbugfix",
        here.parent.parent / "mod" / "oisbugfix",
    ]
    for c in candidates:
        if c.is_dir() and any(c.iterdir()):
            return c
    return None


def install_mod(exe_path):
    if apply_data_fixes is None:
        print("\n[SKIP] Bugfix mod: apply_data_fixes.py isn't next to this script -- skipping "
              "the data-only fixes. The exe patch is unaffected; ship both files together.")
        return False
    mod_src = find_bundled_mod_dir()
    if mod_src is None:
        print("\n[SKIP] Bugfix mod: couldn't find a bundled 'mod/oisbugfix' folder next to this script -- "
              "skipping mod install. The exe patch above is unaffected; ship this script together with "
              "its 'mod' folder (containing modinfo.txt) to include the data-only fixes too.")
        return False

    # ois.exe's own directory is the game root; mods live at
    # <root>/ObjectsInSpace/mods/<modname>/ per the game's own loader.
    if not (exe_path.parent / "ObjectsInSpace").is_dir():
        print(f"\n[SKIP] Bugfix mod: expected game data folder not found at {exe_path.parent / 'ObjectsInSpace'} -- "
              f"is {exe_path} really ois.exe from the game's install folder? Skipping mod install.")
        return False

    print()
    return apply_data_fixes.install(exe_path.parent, mod_src)


# ============================================================
# Game install discovery
#
# Ported from Patch_OIS.bat's :DetectTarget / :ScanSteamRoot /
# :TryLibrary, with the same search order, plus the things batch made
# awkward and Python doesn't:
#   - libraryfolders.vdf is parsed as key/value pairs rather than
#     whitespace-split, so library paths containing spaces survive, and
#     both the pre-2021 ("1" "D:\\Lib") and current (nested block with
#     a "path" key) formats are understood.
#   - the install folder name is read from Steam's own
#     appmanifest_<appid>.acf when present, instead of assuming the
#     literal string "Objects in Space".
#   - GOG installs are searched too. The game has a DRM-free GOG
#     release, which the Steam-only batch search cannot find at all.
#   - every candidate is collected rather than stopping at the first
#     hit, so two installs produce a question instead of a silent
#     coin-flip about which one gets patched.
# ============================================================

GAME_EXE_NAME = "ois.exe"
STEAM_APP_ID = "824070"
STEAM_DEFAULT_DIR_NAME = "Objects in Space"
TARGET_DIR_ENV = "OIS_TARGET_DIR"

# Matches a "key" "value" pair in Valve's KeyValues text format, keeping
# backslash escapes intact so they can be unescaped deliberately below.
_VDF_PAIR = re.compile(r'"((?:[^"\\]|\\.)*)"[ \t]*"((?:[^"\\]|\\.)*)"')


def _vdf_unescape(value):
    return value.replace("\\\\", "\\").replace('\\"', '"')


def _vdf_pairs(path):
    """Yields (key, value) from a Valve KeyValues file. Missing or
    unreadable files yield nothing -- a library entry that has been
    deleted or is on a disconnected drive is normal, not an error."""
    try:
        text = Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return
    for key, value in _VDF_PAIR.findall(text):
        yield key, _vdf_unescape(value)


def is_game_dir(path):
    """A folder counts as an install only if ois.exe is in it.

    Deliberately stricter than the batch file's :IsValidGameDir, which
    also accepts an ois_server.exe-only folder. This script's whole
    entry point is patching ois.exe; a folder without it would be
    detected here only to fail two lines into main()."""
    try:
        return (Path(path) / GAME_EXE_NAME).is_file()
    except OSError:
        return False


def normalize_user_path(raw):
    """Accepts what people actually paste: surrounding quotes, stray
    whitespace, a trailing separator, ~, or the path to ois.exe itself
    rather than the folder holding it. Returns a Path or None."""
    if raw is None:
        return None
    text = str(raw).strip().strip('"').strip("'").strip()
    if not text:
        return None
    path = Path(text).expanduser()
    if path.name.lower() == GAME_EXE_NAME:
        path = path.parent
    return path


def _env_path(var):
    value = os.environ.get(var)
    if not value:
        return None
    value = value.strip().rstrip("\\/") or value.strip()
    # SystemDrive is bare "C:", and Path("C:") / "Steam" means "Steam,
    # relative to the current directory on C:" on Windows, not "C:\Steam".
    if len(value) == 2 and value.endswith(":"):
        value += "\\"
    return Path(value)


def _windows_registry_values(hive, subkey, value_names):
    try:
        import winreg
    except ImportError:
        return
    try:
        with winreg.OpenKey(hive, subkey) as key:
            for name in value_names:
                try:
                    value, _ = winreg.QueryValueEx(key, name)
                except OSError:
                    continue
                if isinstance(value, str) and value.strip():
                    yield value.strip()
    except OSError:
        return


def _steam_roots():
    """Steam client install folders, most likely first."""
    if sys.platform == "win32":
        for var in ("ProgramFiles(x86)", "ProgramFiles", "USERPROFILE", "SystemDrive"):
            base = _env_path(var)
            if base is not None:
                yield base / "Steam"
        try:
            import winreg
        except ImportError:
            return
        for hive, subkey, names in (
            (winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam", ("SteamPath", "InstallPath")),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam", ("InstallPath",)),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Valve\Steam", ("InstallPath",)),
        ):
            for value in _windows_registry_values(hive, subkey, names):
                yield Path(value)
    else:
        # Not the intended platform, but the patcher itself is
        # platform-agnostic (it edits a PE file on disk), so a Proton or
        # Crossover install is patchable from the host side.
        home = Path.home()
        for rel in (
            ".steam/steam",
            ".steam/root",
            ".local/share/Steam",
            "Library/Application Support/Steam",
            "snap/steam/common/.local/share/Steam",
            ".var/app/com.valvesoftware.Steam/data/Steam",
        ):
            yield home / rel


def _steam_libraries(steam_root):
    """The root's own steamapps, plus every library listed in
    libraryfolders.vdf (games are frequently on a different drive)."""
    yield steam_root
    for key, value in _vdf_pairs(steam_root / "steamapps" / "libraryfolders.vdf"):
        # Current format keys the path as "path"; the old format keys it
        # by library index ("1", "2", ...). The nested "apps" block is
        # also index-keyed, but its values are byte counts, so anything
        # purely numeric is not a library path.
        if value.isdigit():
            continue
        if key.lower() == "path" or key.isdigit():
            yield Path(value)


def _steam_game_dirs(library):
    """Candidate install folders inside one Steam library."""
    steamapps = Path(library) / "steamapps"
    names = []
    for key, value in _vdf_pairs(steamapps / f"appmanifest_{STEAM_APP_ID}.acf"):
        if key.lower() == "installdir" and value:
            names.append(value)
    names.append(STEAM_DEFAULT_DIR_NAME)  # fallback if the manifest is gone
    for name in names:
        yield steamapps / "common" / name


def _gog_game_dirs():
    """GOG Galaxy records each installed game's folder in the registry.
    Every entry is enumerated and tested for ois.exe rather than looking
    up a hardcoded product ID, so this keeps working if the ID is wrong
    or the game was installed by the standalone offline installer."""
    if sys.platform != "win32":
        return
    try:
        import winreg
    except ImportError:
        return
    for subkey in (r"SOFTWARE\GOG.com\Games", r"SOFTWARE\WOW6432Node\GOG.com\Games"):
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, subkey) as games:
                index = 0
                while True:
                    try:
                        child = winreg.EnumKey(games, index)
                    except OSError:
                        break
                    index += 1
                    for value in _windows_registry_values(
                        winreg.HKEY_LOCAL_MACHINE, subkey + "\\" + child, ("path", "PATH", "exe")
                    ):
                        yield normalize_user_path(value)
        except OSError:
            continue
    for base_var in ("SystemDrive", "ProgramFiles(x86)", "ProgramFiles"):
        base = _env_path(base_var)
        if base is None:
            continue
        yield base / "GOG Games" / STEAM_DEFAULT_DIR_NAME
        yield base / "GOG Galaxy" / "Games" / STEAM_DEFAULT_DIR_NAME


def _candidate_dirs():
    """Yields (candidate_dir, source_label), unvalidated, in priority
    order. Nothing here touches the disk except to read config files."""
    for root in _steam_roots():
        for library in _steam_libraries(root):
            for game_dir in _steam_game_dirs(library):
                yield game_dir, "Steam"
    for game_dir in _gog_game_dirs():
        if game_dir is not None:
            yield game_dir, "GOG"


def find_game_dirs():
    """Every distinct install that actually contains ois.exe, in
    priority order. Returns a list of (Path, source_label)."""
    found = []
    seen = set()
    for candidate, source in _candidate_dirs():
        try:
            resolved = candidate.resolve()
        except OSError:
            continue
        key = str(resolved).lower()
        if key in seen:
            continue
        seen.add(key)
        if is_game_dir(resolved):
            found.append((resolved, source))
    return found


def _prompt_for_dir():
    """Last resort, and only when someone is actually there to answer."""
    if not sys.stdin.isatty():
        return None
    print("\nPlease paste your Objects in Space install folder.")
    print(r"Example: D:\SteamLibrary\steamapps\common\Objects in Space")
    for _ in range(3):
        try:
            raw = input("Game folder path (blank to give up): ")
        except (EOFError, KeyboardInterrupt):
            print()
            return None
        path = normalize_user_path(raw)
        if path is None:
            return None
        if is_game_dir(path):
            return path
        print(f"[ERROR] No {GAME_EXE_NAME} in: {path}")
    return None


def _choose_dir(found):
    """More than one install is not a coin-flip: patching writes to
    disk, so the choice gets made by whoever can actually see the
    machine, not by search order."""
    print(f"\nFound {len(found)} Objects in Space installs:")
    for i, (path, source) in enumerate(found, 1):
        print(f"  [{i}] {path}   ({source})")
    if not sys.stdin.isatty():
        print(
            "\n[ERROR] Multiple installs found and nothing to prompt (not an interactive\n"
            "        session). Re-run with the one you want:\n"
            f"          python ois_patcher.py --game-dir \"{found[0][0]}\"",
            file=sys.stderr,
        )
        return None
    for _ in range(3):
        try:
            raw = input(f"Which one? [1-{len(found)}, or blank to cancel]: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return None
        if not raw:
            return None
        if raw.isdigit() and 1 <= int(raw) <= len(found):
            return found[int(raw) - 1][0]
        print("[ERROR] Not one of the listed numbers.")
    return None


def resolve_game_dir(explicit=None):
    """Search order, mirroring Patch_OIS.bat:
    explicit path (CLI) -> OIS_TARGET_DIR -> auto-detect -> ask.

    An explicit path that turns out to be wrong is a hard error, not a
    reason to start guessing: someone who names a folder means that
    folder. A wrong OIS_TARGET_DIR only warns, since a stale environment
    variable shouldn't block a detectable install. Returns a Path or
    None."""
    path = normalize_user_path(explicit)
    if path is not None:
        if is_game_dir(path):
            return path
        print(f"[ERROR] No {GAME_EXE_NAME} in the folder you gave: {path}", file=sys.stderr)
        return None

    path = normalize_user_path(os.environ.get(TARGET_DIR_ENV))
    if path is not None:
        if is_game_dir(path):
            print(f"Using {TARGET_DIR_ENV}: {path}")
            return path
        print(f"[WARN] {TARGET_DIR_ENV} is set to {path}, which has no {GAME_EXE_NAME} -- ignoring it.")

    print("Looking for your Objects in Space install...")
    found = find_game_dirs()
    if len(found) == 1:
        print(f"Found install ({found[0][1]}): {found[0][0]}")
        return found[0][0]
    if len(found) > 1:
        return _choose_dir(found)

    print("[NOTICE] Could not find the game automatically.")
    return _prompt_for_dir()


# ============================================================
# Install state: inspect, restore, uninstall
#
# The exe already carries an embedded version marker (see
# VERSION_MARKER_* and read_version_marker), so "what is installed
# right now" is a question the file itself can answer -- nothing here
# relies on a sidecar receipt that can drift out of sync with reality.
# ============================================================

PATCHABLE_EXES = ("ois.exe", "ois_server.exe")
MOD_DIR_RELATIVE = ("ObjectsInSpace", "mods", "oisbugfix")
BACKUP_SUFFIX = ".original-backup"

# state values from inspect_exe()
STATE_MISSING = "missing"        # file isn't there
STATE_UNREADABLE = "unreadable"  # there, but not a PE this tool understands
STATE_STOCK = "stock"            # no .ptch section -- never patched by us
STATE_PATCHED = "patched"        # .ptch present, version marker readable
STATE_PATCHED_UNKNOWN = "patched-unknown"  # .ptch present, no readable marker


class ExeStatus:
    __slots__ = ("path", "state", "version")

    def __init__(self, path, state, version=None):
        self.path = path
        self.state = state
        self.version = version

    @property
    def is_patched(self):
        return self.state in (STATE_PATCHED, STATE_PATCHED_UNKNOWN)

    def describe(self):
        return {
            STATE_MISSING: "not present",
            STATE_UNREADABLE: "unreadable (not a PE this tool understands)",
            STATE_STOCK: "stock (unpatched)",
            STATE_PATCHED: f"patched by v{self.version}",
            STATE_PATCHED_UNKNOWN: "patched (by a build with no version marker)",
        }[self.state]


def backup_path_for(exe_path):
    return Path(exe_path).with_name(Path(exe_path).name + BACKUP_SUFFIX)


def inspect_exe(exe_path):
    """Reads a file's patch state without modifying anything."""
    exe_path = Path(exe_path)
    if not exe_path.is_file():
        return ExeStatus(exe_path, STATE_MISSING)
    try:
        data = bytearray(exe_path.read_bytes())
        pe = load_pe(data)
    except Exception:
        # Anything unreadable is reported as such rather than raised: this
        # runs from --status and from uninstall, where a bad file is a
        # thing to report, not a crash.
        return ExeStatus(exe_path, STATE_UNREADABLE)
    try:
        section = next((s for s in pe.sections if s.Name.rstrip(b"\x00") == b".ptch"), None)
        if section is None:
            return ExeStatus(exe_path, STATE_STOCK)
        version = read_version_marker(data, pe, section)
    finally:
        pe.close()
    if version is None:
        return ExeStatus(exe_path, STATE_PATCHED_UNKNOWN)
    return ExeStatus(exe_path, STATE_PATCHED, version)


def parse_version(text):
    """'0.3.2' -> (0, 3, 2). None when it isn't dotted integers, so a
    hand-edited or future marker format degrades to 'different', never
    to a false ordering."""
    if not text:
        return None
    parts = text.strip().split(".")
    if not all(p.isdigit() for p in parts):
        return None
    return tuple(int(p) for p in parts)


def ensure_writable(paths):
    """A running game holds its own exe against writes on Windows, and
    the same is true of a folder owned by another account. Both fail
    much more clearly here than halfway through a rewrite."""
    blocked = []
    for path in paths:
        path = Path(path)
        if not path.is_file():
            continue
        try:
            with open(path, "r+b"):
                pass
        except OSError:
            blocked.append(path)
    if not blocked:
        return True
    print("\n[ERROR] These files cannot be written to right now:", file=sys.stderr)
    for path in blocked:
        print(f"  {path}", file=sys.stderr)
    print("Close Objects in Space (and its server) if it's running, and make sure this\n"
          "account can write to the game folder, then try again. Nothing has been changed.",
          file=sys.stderr)
    return False


def check_backup_usable(backup):
    """A backup is only worth restoring if it's a stock exe. Someone who
    once copied a patched build over their backup would otherwise
    'restore' to a patched file and then get patched again on top --
    exactly the double-patch this tool refuses to do elsewhere."""
    status = inspect_exe(backup)
    if status.state == STATE_MISSING:
        return False, "no backup file"
    if status.state == STATE_UNREADABLE:
        return False, "backup is not a readable PE file"
    if status.is_patched:
        return False, f"backup is itself {status.describe()} -- it is not a pristine original"
    return True, None


def restore_exe(exe_path, keep_backup=True):
    """Copies <exe>.original-backup back over <exe>, verifies the result
    byte-for-byte, and only then optionally removes the backup."""
    exe_path = Path(exe_path)
    backup = backup_path_for(exe_path)
    usable, reason = check_backup_usable(backup)
    if not usable:
        print(f"  [SKIP] {exe_path.name}: {reason}")
        return False

    original = backup.read_bytes()
    exe_path.write_bytes(original)
    if exe_path.read_bytes() != original:
        print(f"  [ERROR] {exe_path.name}: restored file does not match the backup -- "
              f"leaving the backup in place.", file=sys.stderr)
        return False
    print(f"  [OK] restored {exe_path.name}")

    if not keep_backup:
        try:
            backup.unlink()
            print(f"       removed {backup.name}")
        except OSError as e:
            print(f"       [WARN] could not remove {backup.name}: {e}")
    return True


def remove_mod(game_dir):
    """Deletes the mod folder this tool installs. Refuses if what's there
    doesn't look like it (no modinfo.txt), since this deletes a tree."""
    mod_dir = Path(game_dir).joinpath(*MOD_DIR_RELATIVE)
    if not mod_dir.exists():
        print("  [SKIP] bugfix mod: not installed")
        return False
    if not (mod_dir / "modinfo.txt").is_file():
        print(f"  [SKIP] bugfix mod: {mod_dir} has no modinfo.txt -- this doesn't look like "
              f"the mod this tool installs, so it is being left alone. Delete it by hand "
              f"if you're sure.")
        return False
    try:
        shutil.rmtree(mod_dir)
    except OSError as e:
        print(f"  [ERROR] could not remove {mod_dir}: {e}", file=sys.stderr)
        return False
    print(f"  [OK] removed bugfix mod from {mod_dir}")
    return True


def print_status(game_dir):
    game_dir = Path(game_dir)
    print(f"Install: {game_dir}")
    print(f"This patcher: v{PATCHER_VERSION}")
    for name in PATCHABLE_EXES:
        status = inspect_exe(game_dir / name)
        backup = backup_path_for(game_dir / name)
        backup_note = ""
        if backup.is_file():
            usable, reason = check_backup_usable(backup)
            backup_note = "  [backup: available]" if usable else f"  [backup: unusable -- {reason}]"
        else:
            backup_note = "  [backup: none]"
        print(f"  {name:<16} {status.describe()}{backup_note}")
        if status.state == STATE_PATCHED and status.version != PATCHER_VERSION:
            print(f"  {'':<16} -> run this script with no arguments to update it to v{PATCHER_VERSION}")
    mod_dir = game_dir.joinpath(*MOD_DIR_RELATIVE)
    print(f"  {'bugfix mod':<16} {'installed at ' + str(mod_dir) if mod_dir.is_dir() else 'not installed'}")


def confirm(question, assume_yes):
    if assume_yes:
        return True
    if not sys.stdin.isatty():
        print("\n[ERROR] This needs a yes/no answer but there's nobody to ask (not an "
              "interactive session). Re-run with --yes to confirm up front.", file=sys.stderr)
        return False
    try:
        return input(f"{question} [y/N]: ").strip().lower() in ("y", "yes")
    except (EOFError, KeyboardInterrupt):
        print()
        return False


def uninstall(game_dir, assume_yes=False, keep_backups=False, extra_exes=()):
    """Puts the folder back the way it was: stock exes from the backups
    this tool made, and the mod folder gone. `extra_exes` covers a
    non-standard exe name the user named explicitly."""
    game_dir = Path(game_dir)
    targets = [game_dir / name for name in PATCHABLE_EXES]
    for extra in extra_exes:
        if Path(extra) not in targets:
            targets.append(Path(extra))
    mod_dir = game_dir.joinpath(*MOD_DIR_RELATIVE)

    print(f"\nCurrent state of {game_dir}:")
    restorable = []
    for exe_path in targets:
        status = inspect_exe(exe_path)
        if status.state == STATE_MISSING:
            continue
        usable, reason = check_backup_usable(backup_path_for(exe_path))
        print(f"  {exe_path.name:<16} {status.describe()}"
              f"{'  [backup available]' if usable else '  [backup: ' + reason + ']'}")
        if usable:
            restorable.append(exe_path)
        elif status.is_patched:
            print(f"  {'':<16} -> cannot be reverted by this script. Use Steam's "
                  f"\"Verify integrity of game files\" (or reinstall from GOG) to get a stock copy.")

    mod_present = mod_dir.is_dir()
    print(f"  {'bugfix mod':<16} {'installed' if mod_present else 'not installed'}")

    if not restorable and not mod_present:
        print("\nNothing installed by this script was found -- nothing to undo.")
        return True

    print("\nThis will:")
    for exe_path in restorable:
        print(f"  - restore {exe_path.name} from {backup_path_for(exe_path).name}"
              f"{'' if keep_backups else ', then delete that backup'}")
    if mod_present:
        print(f"  - delete {mod_dir}")
    print("  - leave save games, settings and every other game file untouched")

    if not confirm("\nProceed?", assume_yes):
        print("Uninstall canceled. Nothing was changed.")
        return False

    if not ensure_writable(restorable):
        return False

    print("\nUninstalling:")
    ok = True
    for exe_path in restorable:
        ok = restore_exe(exe_path, keep_backup=keep_backups) and ok
    if mod_present:
        remove_mod(game_dir)

    print("\n" + "=" * 60)
    if ok:
        print("Uninstall complete -- the game folder should match its pre-patch state.")
    else:
        print("Uninstall finished with problems (see above). The folder may now be a mix of\n"
              "patched and stock files; verifying the game files through Steam or GOG is the\n"
              "safest way back to a clean state.")
    return ok


def prepare_for_patch(client_exe, force=False, assume_yes=False):
    """Decides what a patch run should actually do, given what's already
    installed. Returns one of:
        "patch"     -- go ahead and patch the exes
        "mod-only"  -- exes are already current; refresh the mod only
        None        -- stop, reason already printed

    Upgrading is a restore-then-patch, never a patch-on-top: the fixes
    are byte-verified against stock code, so the only safe base for a
    new version is the original file."""
    client_exe = Path(client_exe)
    client = inspect_exe(client_exe)
    server = inspect_exe(client_exe.parent / "ois_server.exe")

    if client.state == STATE_UNREADABLE:
        print(f"\n[ERROR] {client_exe.name} is not a Windows executable this tool can read.\n"
              f"        {client_exe}\n"
              f'        Use Steam\'s "Verify integrity of game files" (or reinstall from GOG)\n'
              f"        to get a good copy, then run this again.", file=sys.stderr)
        return None

    def is_current(status):
        return status.state == STATE_PATCHED and status.version == PATCHER_VERSION

    any_backup = any(backup_path_for(st.path).is_file()
                     for st in (client, server) if st.state != STATE_MISSING)

    # Ordinary first install: nothing here has been touched yet.
    if not client.is_patched and not server.is_patched and not (force and any_backup):
        return "patch"

    # Everything that exists is already at this version. Note the server is
    # checked too: a stale ois_server.exe beside a current ois.exe used to
    # fall through to "already current", quietly leaving co-op unpatched.
    server_ok = server.state == STATE_MISSING or is_current(server)
    if is_current(client) and server_ok and not force:
        print(f"\n{client_exe.name} is already patched by this exact version (v{PATCHER_VERSION}).")
        print("Leaving it alone and refreshing the data-only mod instead "
              "(pass --force to re-patch from the backup anyway).")
        return "mod-only"

    for status in (client, server):
        if status.state == STATE_PATCHED and not is_current(status):
            print(f"\n{status.path.name}: patched by v{status.version}")
        elif status.state == STATE_PATCHED_UNKNOWN:
            print(f"\n{status.path.name}: patched by a build with no version marker")

    if client.state == STATE_PATCHED:
        installed = parse_version(client.version)
        current = parse_version(PATCHER_VERSION)
        if installed and current and installed > current:
            print(f"\n[ERROR] {client_exe.name} is patched by v{client.version}, which is NEWER than this "
                  f"script (v{PATCHER_VERSION}).\n"
                  f"        Continuing would downgrade it. Get the newer patcher, or pass "
                  f"--force if you really mean to go back.", file=sys.stderr)
            if not force:
                return None
        label = f"v{client.version}"
    else:
        label = "an unversioned build"

    # Every exe that is patched (or that --force is about to re-patch)
    # needs a usable backup before anything is touched.
    to_restore = []
    for status in (client, server):
        if status.state == STATE_MISSING:
            continue
        if not status.is_patched and not force:
            continue
        if status.state == STATE_UNREADABLE:
            print(f"\n[ERROR] {status.path.name} is not readable as a PE file; "
                  f"not touching this install.", file=sys.stderr)
            return None
        usable, reason = check_backup_usable(backup_path_for(status.path))
        if not usable:
            print(f"\n[ERROR] {status.path.name} is {status.describe()}, but its backup can't be "
                  f"used ({reason}).\n"
                  f"        Updating means restoring the original first, so this can't proceed.\n"
                  f"        Use Steam's \"Verify integrity of game files\" (or reinstall from GOG)\n"
                  f"        to get a stock copy, then run this script again.", file=sys.stderr)
            return None
        to_restore.append(status.path)

    if force and not client.is_patched:
        print(f"\n--force: restoring from backup and re-patching from scratch.")
    else:
        print(f"\nThis install was patched by {label}; this script is v{PATCHER_VERSION}.")
        print("Updating means restoring the original exe(s) from their backups and applying")
        print("the current fixes to them. Save games and settings are not involved.")

    if not confirm("\nUpdate now?", assume_yes):
        print("Update canceled. Nothing was changed.")
        return None

    if not ensure_writable(to_restore):
        return None

    print("\nRestoring originals before re-patching:")
    for exe_path in to_restore:
        # The backups are kept: patching immediately follows, and main()
        # reuses each one as the pristine original rather than re-making it.
        if not restore_exe(exe_path, keep_backup=True):
            print("[ERROR] Restore failed -- not patching on top of an unknown file.", file=sys.stderr)
            return None
    return "patch"


# ============================================================
# Self-update
#
# Two hard constraints shape this:
#
#   1. A pull replaces the very code that is running, including
#      apply_data_fixes.py, which was imported at startup. Python does
#      not reload either from disk mid-run, so pulling and then
#      continuing would apply the OLD fixes while reporting the NEW
#      version. Every successful pull therefore re-runs the script as a
#      fresh process and exits; nothing continues in-process.
#   2. Pulling is running someone else's new code on the user's
#      machine. That gets asked about, not assumed. --yes deliberately
#      does NOT imply consent here; --update does.
# ============================================================

REPO_URL = ""  # e.g. "https://github.com/you/ois-patcher" -- shown when git isn't usable
UPDATED_ENV = "OIS_PATCHER_SELF_UPDATED"  # re-exec guard: one update per invocation


def _git(args, cwd, timeout=30):
    """Runs git, returning the CompletedProcess or None if git isn't
    installed / didn't answer in time."""
    try:
        return subprocess.run(["git", *args], cwd=str(cwd), capture_output=True,
                              text=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError):
        return None


def _manual_update_hint(reason):
    """Silent when REPO_URL is unset: most people run this from a
    downloaded zip, and telling them every single run that updates can't
    be checked -- without being able to say where to look -- is noise,
    not help."""
    if not REPO_URL:
        return
    print(f"\n[NOTICE] Can't check for updates automatically ({reason}).")
    print(f"         Check for a newer release at: {REPO_URL}")


def check_for_updates(assume_update=False):
    """Returns True if the script updated itself and re-ran (caller should
    stop). Any failure here is a notice, never a reason to abort a patch
    run -- being one commit behind is not a safety problem."""
    if os.environ.get(UPDATED_ENV):
        return False  # already re-ran once this invocation

    here = Path(__file__).resolve().parent
    top = _git(["rev-parse", "--show-toplevel"], here)
    if top is None:
        _manual_update_hint("git isn't installed or isn't on PATH")
        return False
    if top.returncode != 0:
        _manual_update_hint("this copy isn't a git checkout -- probably a downloaded zip")
        return False
    repo = Path(top.stdout.strip())

    # -uno: untracked files are ignored on purpose. Running this script
    # writes __pycache__/ into its own directory, so counting untracked
    # files as "local changes" would switch the update check off
    # permanently after the very first run. Tracked edits still block it,
    # and if an untracked file ever does collide with an incoming one,
    # git's own ff-only pull refuses and that failure is handled below.
    dirty = _git(["status", "--porcelain", "-uno"], repo)
    if dirty is not None and dirty.returncode == 0 and dirty.stdout.strip():
        print("\n[NOTICE] Skipping the update check: you have uncommitted local changes.")
        print("         Updating would risk your edits, so this leaves the checkout alone.")
        return False

    upstream = _git(["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"], repo)
    if upstream is None or upstream.returncode != 0:
        _manual_update_hint("this branch has no upstream to compare against")
        return False

    print("Checking for patcher updates...")
    fetch = _git(["fetch", "--quiet"], repo, timeout=60)
    if fetch is None or fetch.returncode != 0:
        detail = (fetch.stderr.strip().splitlines() or ["no network, or the remote refused"])[-1] if fetch else "git fetch timed out"
        print(f"[NOTICE] Update check failed ({detail}) -- continuing with the local version.")
        return False

    counts = _git(["rev-list", "--left-right", "--count", "HEAD...@{u}"], repo)
    if counts is None or counts.returncode != 0:
        print("[NOTICE] Could not compare against the remote -- continuing with the local version.")
        return False
    try:
        ahead, behind = (int(n) for n in counts.stdout.split())
    except ValueError:
        print("[NOTICE] Could not read the remote comparison -- continuing with the local version.")
        return False

    if behind == 0:
        print(f"Patcher is up to date (v{PATCHER_VERSION}).")
        return False
    if ahead:
        print(f"\n[NOTICE] {behind} update(s) available, but this checkout also has {ahead} local "
              f"commit(s).\n         A fast-forward isn't possible; merge or rebase by hand.")
        return False

    print(f"\n{behind} patcher update(s) available:")
    log = _git(["log", "--oneline", "--no-decorate", "-10", "HEAD..@{u}"], repo)
    if log is not None and log.returncode == 0:
        for line in log.stdout.strip().splitlines():
            print(f"  {line}")
        if behind > 10:
            print(f"  ... and {behind - 10} more")

    if not confirm("\nUpdate the patcher now (git pull, then re-run)?", assume_update):
        print("Continuing with the local version.")
        return False

    pull = _git(["pull", "--ff-only", "--quiet"], repo, timeout=120)
    if pull is None or pull.returncode != 0:
        detail = (pull.stderr.strip() if pull else "git pull timed out") or "unknown error"
        print(f"\n[NOTICE] Update failed: {detail}\n         Continuing with the local version.")
        return False

    print("Updated. Re-running the patcher with the new version...\n")
    env = dict(os.environ)
    env[UPDATED_ENV] = "1"
    # A fresh process, not os.execv: this keeps console behaviour sane on
    # Windows and guarantees the new apply_data_fixes.py is the one imported.
    result = subprocess.run([sys.executable, str(Path(__file__).resolve()), *sys.argv[1:]], env=env)
    sys.exit(result.returncode)


# ============================================================
# main
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="Unofficial Objects in Space (ois.exe) bugfix patcher",
        epilog="With no arguments, the game folder is detected automatically "
               f"(Steam and GOG), falling back to the {TARGET_DIR_ENV} environment "
               "variable and then to asking.",
    )
    parser.add_argument("exe_path", nargs="?",
                        help=f"Path to {GAME_EXE_NAME}, or the folder containing it. "
                             "Optional -- omit it to auto-detect.")
    parser.add_argument("--game-dir", dest="game_dir", metavar="DIR",
                        help="Same as passing the path positionally; provided because "
                             "it reads better in scripts and shortcuts.")
    parser.add_argument("--list-installs", action="store_true",
                        help="List every install found and exit without patching anything.")
    parser.add_argument("--uninstall", action="store_true",
                        help="Restore the original exe(s) from their .original-backup files "
                             "and remove the bugfix mod, then exit.")
    parser.add_argument("--status", action="store_true",
                        help="Report what is currently installed and exit without changing anything.")
    parser.add_argument("--force", action="store_true",
                        help="Re-patch from the backup even when the install is already current.")
    parser.add_argument("--yes", "-y", action="store_true",
                        help="Answer yes to confirmation prompts (for unattended runs).")
    parser.add_argument("--update", action="store_true",
                        help="Check the git checkout for a newer patcher and apply it without "
                             "asking, then re-run.")
    parser.add_argument("--no-update-check", action="store_true",
                        help="Skip the update check entirely.")
    parser.add_argument("--keep-backups", action="store_true",
                        help="With --uninstall, leave the .original-backup files in place "
                             "instead of deleting them after a verified restore.")
    args = parser.parse_args()

    if args.list_installs:
        found = find_game_dirs()
        if not found:
            print("No Objects in Space install found.")
            sys.exit(1)
        for path, source in found:
            print(f"{path}   ({source})")
        sys.exit(0)

    if args.exe_path and args.game_dir:
        print("[ERROR] Give the path once, either positionally or as --game-dir, not both.",
              file=sys.stderr)
        sys.exit(1)

    explicit = args.exe_path or args.game_dir
    exe_path = None

    # An explicitly named file that isn't ois.exe is taken at face value:
    # before auto-detection existed, pointing this script at a renamed or
    # copied-aside exe worked, and folder-based detection shouldn't
    # quietly redirect such a run to the real ois.exe instead.
    if explicit:
        named = Path(str(explicit).strip().strip('"').strip("'")).expanduser()
        if named.is_file() and named.name.lower() != GAME_EXE_NAME:
            exe_path = named

    if exe_path is None:
        game_dir = resolve_game_dir(explicit)
        if game_dir is None:
            print('\nNo game folder found. Re-run with the path, e.g.:\n'
                  '  python ois_patcher.py "D:\\SteamLibrary\\steamapps\\common\\Objects in Space"',
                  file=sys.stderr)
            sys.exit(1)
        exe_path = game_dir / GAME_EXE_NAME
    else:
        game_dir = exe_path.parent

    # Before anything is written. Skipped for read-only modes below unless
    # asked for, so --status stays instant and offline.
    if args.update or not (args.no_update_check or args.status):
        check_for_updates(assume_update=args.update)

    if args.status:
        print_status(game_dir)
        sys.exit(0)

    if args.uninstall:
        extra = [exe_path] if exe_path.name.lower() != GAME_EXE_NAME else []
        sys.exit(0 if uninstall(game_dir, assume_yes=args.yes,
                                keep_backups=args.keep_backups, extra_exes=extra) else 1)

    action = prepare_for_patch(exe_path, force=args.force, assume_yes=args.yes)
    if action is None:
        sys.exit(1)

    if action == "mod-only":
        print("\nRefreshing data-only bugfix mod...")
        mod_installed = install_mod(exe_path)
        print(f"\nBugfix mod: {'installed' if mod_installed else 'skipped, see above'}")
        print("Exe fixes: already up to date, nothing changed.")
        sys.exit(0)

    print(f"\nPatching: {exe_path}")

    if not ensure_writable([exe_path, game_dir / "ois_server.exe"]):
        sys.exit(1)

    # Read and validate first. Writing a backup of a file that turns out
    # not to be patchable leaves confusing litter in the game folder and
    # tells the user nothing useful.
    try:
        data = bytearray(exe_path.read_bytes())
    except OSError as e:
        print(f"\nCould not read {exe_path}: {e}", file=sys.stderr)
        sys.exit(1)

    ok, reason = validate_pe(data, exe_path.name)
    if not ok:
        print(f"\n[ERROR] {reason}", file=sys.stderr)
        sys.exit(1)

    backup_path = exe_path.with_name(exe_path.name + BACKUP_SUFFIX)
    if backup_path.exists():
        print(f"Backup already exists at {backup_path} -- not overwriting it (reusing it as the pristine original).")
    else:
        try:
            backup_path.write_bytes(data)
        except OSError as e:
            print(f"\nCould not write the backup to {backup_path}: {e}\n"
                  f"Refusing to patch without one.", file=sys.stderr)
            sys.exit(1)
        print(f"Backed up original to {backup_path}")

    print("\nAdding patch section...")
    try:
        ptch_va, ptch_off, ptch_size = add_ptch_section(data)
    except RuntimeError as e:
        print(f"\nError: {e}", file=sys.stderr)
        sys.exit(1)

    pe = load_pe(data)
    pe.parse_data_directories()

    print("\nApplying fixes:")
    cave_cursor = VERSION_MARKER_SIZE  # first bytes of the cave are reserved for the version marker
    cave_cursor = fix_pirate_hunt(data, pe, ptch_va, ptch_off, cave_cursor)
    fix_pirate_hunt_format_string(data, pe)
    cave_cursor = fix_music_leak(data, pe, ptch_va, ptch_off, cave_cursor)
    cave_cursor = fix_burnvector_strict_compare(data, pe, ptch_va, ptch_off, cave_cursor)
    fix_burnvector_travelstate(data, pe)
    cave_cursor = fix_burnvector_singularity(data, pe, ptch_va, ptch_off, cave_cursor)
    fix_unknown_room_spam(data, pe)
    cave_cursor = fix_pda_render_guard(data, pe, ptch_va, ptch_off, cave_cursor)
    cave_cursor = fix_del_command(data, pe, ptch_va, ptch_off, cave_cursor)
    pe.close()

    if cave_cursor > ptch_size:
        print(f"\nERROR: cave usage ({cave_cursor} bytes) exceeded reserved space ({ptch_size} bytes) -- aborting without writing.", file=sys.stderr)
        sys.exit(1)

    exe_path.write_bytes(data)

    print("\nChecking for ois_server.exe (needed for hosting/joining co-op games)...")
    server_patched = patch_server_exe(exe_path)

    print("\nInstalling data-only bugfix mod...")
    mod_installed = install_mod(exe_path)

    print(f"\n{'='*60}")
    print(f"Applied {len(FIXES_APPLIED)} exe fix(es), skipped {len(FIXES_SKIPPED)}.")
    if FIXES_SKIPPED:
        print("Skipped (likely a different game version, or already patched some other way):")
        for f in FIXES_SKIPPED:
            print(f"  - {f}")
    if server_patched:
        print(f"ois_server.exe: applied {len(SERVER_FIXES_APPLIED)} fix(es), skipped {len(SERVER_FIXES_SKIPPED)}.")
    else:
        print("ois_server.exe: not patched, see above (only matters for hosting/joining co-op games).")
    print(f"Bugfix mod: {'installed' if mod_installed else 'skipped, see above'}")
    print(f"\nPatched: {exe_path}")
    print(f"Original backed up at: {backup_path}")
    print("To undo everything (exe(s) restored, mod removed):")
    print("  python ois_patcher.py --uninstall")
    print("To see what's installed at any time: python ois_patcher.py --status")


if __name__ == "__main__":
    main()
