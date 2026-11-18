#!/usr/bin/env python3
"""Emulation test for the Options > resolution fix (Fix 34; needs `pip install unicorn pefile`).

    python3 tools/ui/test_resolution_list.py <game dir>/ois.exe

Runs the mode-enumeration loop of OISConfiguration::configure() (from the first EnumDisplaySettingsW call to the end
of the loop) with a stand-in EnumDisplaySettingsW that returns what Windows returns for a monitor with several
refresh rates, and prints the resulting validResolutions list.  Stock exe: every mode is kept (1920x1080 five times
-> five clicks for one visible change).  Patched exe: one entry per distinct width x height, first occurrence kept.
"""
import struct
import sys

import pefile
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
from unicorn.x86_const import (UC_X86_REG_EAX, UC_X86_REG_EBP, UC_X86_REG_EDI, UC_X86_REG_EIP, UC_X86_REG_ESI,
                               UC_X86_REG_ESP)

LOOP_START, LOOP_END = 0x4B0B0E, 0x4B0B7B
VEC_FIRST, VEC_LAST, VEC_END = 0x65D760, 0x65D764, 0x65D768
STUB = 0x20000000
# what EnumDisplaySettingsW returns, in order: (width, height) once per refresh rate / colour depth
MODES = ([(640, 480)] * 2 + [(1280, 720)] * 3 + [(1600, 900)] * 2 + [(1920, 1080)] * 5 + [(2560, 1440)] * 3
         + [(1920, 1080)] * 2 + [(1280, 720)])


def run(exe):
    pe = pefile.PE(exe, fast_load=True)
    raw = open(exe, "rb").read()
    uc = Uc(UC_ARCH_X86, UC_MODE_32)
    base = pe.OPTIONAL_HEADER.ImageBase
    for sec in pe.sections:
        size = (max(sec.Misc_VirtualSize, sec.SizeOfRawData) + 0xFFF) & ~0xFFF
        uc.mem_map(base + sec.VirtualAddress, size)
        uc.mem_write(base + sec.VirtualAddress, raw[sec.PointerToRawData:sec.PointerToRawData + sec.SizeOfRawData])
    uc.mem_map(0x10000000, 0x20000)             # stack + vector storage
    uc.mem_map(STUB, 0x1000)
    uc.mem_write(STUB, b"\xC3")
    ebp = 0x10010000
    vec = 0x10001000
    uc.mem_write(VEC_FIRST, struct.pack("<III", vec, vec, vec + 0x4000))    # first, last, end (room for everything)

    def hook(u, address, size, _):
        esp = u.reg_read(UC_X86_REG_ESP)
        mode, devmode = struct.unpack("<II", bytes(u.mem_read(esp + 8, 8)))
        if mode < len(MODES):
            u.mem_write(devmode + 0xAC, struct.pack("<II", *MODES[mode]))
            u.reg_write(UC_X86_REG_EAX, 1)
        else:
            u.reg_write(UC_X86_REG_EAX, 0)
        ret = struct.unpack("<I", bytes(u.mem_read(esp, 4)))[0]
        u.reg_write(UC_X86_REG_ESP, esp + 16)
        u.reg_write(UC_X86_REG_EIP, ret)

    uc.hook_add(UC_HOOK_CODE, hook, begin=STUB, end=STUB)
    # the devmode lives at EBP-0xE0, so its width/height fields (+0xAC/+0xB0) are EBP-0x34/-0x30, as the code reads them
    uc.reg_write(UC_X86_REG_EBP, ebp)
    uc.reg_write(UC_X86_REG_ESP, ebp - 0x1000)
    uc.reg_write(UC_X86_REG_EDI, STUB)
    uc.reg_write(UC_X86_REG_ESI, 0)
    uc.emu_start(LOOP_START, LOOP_END, count=100000)
    first, last = struct.unpack("<II", bytes(uc.mem_read(VEC_FIRST, 8)))
    return [struct.unpack("<II", bytes(uc.mem_read(a, 8))) for a in range(first, last, 8)]


def main():
    got = run(sys.argv[1])
    want = []
    for m in MODES:
        if m not in want:
            want.append(m)
    print(f"  Windows lists {len(MODES)} modes; the game's list has {len(got)} entries:")
    print("   ", ", ".join(f"{w}x{h}" for w, h in got))
    patched = got == want
    stock = got == MODES
    if patched:
        print("\npatched exe: one entry per distinct resolution, first occurrence kept -- OK")
        sys.exit(0)
    print("\nstock exe: every mode kept, duplicates included" if stock else "\nunexpected list")
    sys.exit(1)


if __name__ == "__main__":
    main()
