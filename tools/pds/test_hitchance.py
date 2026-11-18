#!/usr/bin/env python3
"""Emulation test for the shop "Hit Chce" fix (needs `pip install unicorn pefile`).

    python3 tools/pds/test_hitchance.py <game dir>/ois.exe

Runs the percentage calculation in Screen_UpgradeTerminal (0x5511E6 up to the `push eax` at 0x55121A) with
a fake module class whose `hitchance` dice are set to each case, and compares EAX with the real chance of the
PDS's roll (ShipModule::runLogic hits on a roll of 1): 100/N % for 1dN, 0 if 1 can never come up.
Stock exe prints ((N+1)/2)*100-100 (200 for 1d6) and fails; the patched exe passes.
"""
import os
import struct
import sys

import pefile
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32
from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_ECX, UC_X86_REG_ESP

START, END = 0x5511E6, 0x55121A
# (count, sides, constant) -> shown percentage
CASES = [((1, 6, 0), 17), ((1, 5, 0), 20), ((1, 4, 0), 25), ((1, 3, 0), 33), ((1, 2, 0), 50), ((1, 1, 0), 100),
         ((1, 7, 0), 14), ((1, 9, 0), 11), ((2, 6, 0), 0), ((1, 6, 1), 0), ((3, 4, 2), 0), ((1, 0, 0), 0)]


def run(exe, dice):
    pe = pefile.PE(exe, fast_load=True)
    raw = open(exe, "rb").read()
    uc = Uc(UC_ARCH_X86, UC_MODE_32)
    base = pe.OPTIONAL_HEADER.ImageBase
    for sec in pe.sections:
        size = (max(sec.Misc_VirtualSize, sec.SizeOfRawData) + 0xFFF) & ~0xFFF
        uc.mem_map(base + sec.VirtualAddress, size)
        uc.mem_write(base + sec.VirtualAddress, raw[sec.PointerToRawData:sec.PointerToRawData + sec.SizeOfRawData])
    uc.mem_map(0x10000000, 0x10000)
    uc.mem_write(0x10000000 + 0xE8, struct.pack("<III", *dice))
    uc.reg_write(UC_X86_REG_ECX, 0x10000000)
    uc.reg_write(UC_X86_REG_ESP, 0x10008000)
    uc.emu_start(START, END, count=200)
    v = uc.reg_read(UC_X86_REG_EAX)
    return v - (1 << 32) if v >= 1 << 31 else v


def main():
    exe = sys.argv[1]
    bad = 0
    for dice, want in CASES:
        got = run(exe, dice)
        ok = got == want
        bad += not ok
        print(f"  {'PASS' if ok else 'FAIL'} {dice[0]}d{dice[1]}{'+%d' % dice[2] if dice[2] else ''}: shows {got}%  (real chance {want}%)")
    print("\nall checks passed" if not bad else f"\n{bad} check(s) failed")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
