#!/usr/bin/env python3
"""Emulation test of the jump-drive Range rating cut-offs (needs `pip install unicorn pefile`).

    python3 tools/ui/test_jump_range_rating.py <game dir>/ois.exe

Runs the four compares in the shop's jump-drive Range rating (each a `comiss xmm0,[cut-off]` in stock, a `call` to a
cave stub in the patched exe) with the drive's `jumpdistance` in XMM0 and reads the carry/zero flags, then rates the
game's nine real drives (jumpdistance 160-260, from modules_jumpdrive.txt) with the resulting cut-offs.
Patched: cut-offs 180 / 205 / 225 / 245 and a spread of 1/2/3/1/2.  Stock: reports the old cut-offs and exits 1.
"""
import os
import struct
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "common"))
import emu as tp
from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_EBP, UC_X86_REG_EFLAGS, UC_X86_REG_EIP, UC_X86_REG_ESP, UC_X86_REG_XMM0

SITES = (0x49441A, 0x49442B, 0x49443C, 0x49444D)          # 360 / 300 / 280 / 240 in the stock exe, highest first
DRIVES = (("DVJD-400", 160), ("DVJD-450", 190), ("DVJD-500", 200), ("DVJD-600", 220), ("KIJD-10", 260),
          ("KIJD-20", 255), ("KIJD-140", 235), ("KIJD-140R", 220), ("KIJD-140S", 210))
BANDS = ("V. Bad", "Bad", "Medium", "Good", "V. Good")
WANT = {"DVJD-400": "V. Bad", "DVJD-450": "Bad", "DVJD-500": "Bad", "DVJD-600": "Medium", "KIJD-10": "V. Good",
        "KIJD-20": "V. Good", "KIJD-140": "Good", "KIJD-140R": "Medium", "KIJD-140S": "Medium"}


def main():
    exe = sys.argv[1]
    emu = tp.Emu(exe)
    emu.dist_hooks = (0, 0)
    patched = emu.uc.mem_read(SITES[0], 1)[0] == 0xE8

    def below(site, value):
        """True when `value < cut-off at site` (CF set after the compare, which is what the game's JB tests)."""
        frame = tp.STACK_TOP - 0x3000
        emu.uc.reg_write(UC_X86_REG_EBP, frame)
        emu.uc.reg_write(UC_X86_REG_ESP, frame - 0x100)
        emu.uc.reg_write(UC_X86_REG_EAX, 0x1234)
        emu.uc.reg_write(UC_X86_REG_XMM0, int.from_bytes(struct.pack("<f", value) + b"\0" * 12, "little"))
        emu.stops.clear()
        emu.stops[site + 7] = "done"
        emu.stopped_at = None
        emu.uc.emu_start(site, 0, count=40)
        assert emu.stopped_at == "done" and emu.uc.reg_read(UC_X86_REG_EAX) == 0x1234
        return bool(emu.uc.reg_read(UC_X86_REG_EFLAGS) & 1)

    cuts = []
    for site in SITES:                                         # find each cut-off by bisection on the compare itself
        lo, hi = 0.0, 1000.0
        for _ in range(40):
            mid = (lo + hi) / 2
            lo, hi = (lo, mid) if not below(site, mid) else (mid, hi)
        cuts.append(round((lo + hi) / 2))
    cuts.sort()
    print("  cut-offs found by the compares:", cuts)
    ok_cuts = cuts == [180, 205, 225, 245]
    print(("  PASS " if ok_cuts else "  FAIL ") + "cut-offs are 180 / 205 / 225 / 245" + ("" if ok_cuts else " (stock: 240 / 280 / 300 / 360)"))
    bad = not ok_cuts
    spread = [0] * 5
    for name, dist in DRIVES:
        band = sum(1 for c in cuts if dist >= c)
        spread[band] += 1
        ok = BANDS[band] == WANT[name]
        bad += not ok
        print(("  PASS " if ok else "  FAIL ") + f"{name:<10} jumpdistance {dist}: {BANDS[band]}")
    print("  spread V.Bad..V.Good:", spread)
    print("all jump-range checks pass" if patched and not bad else
          ("exe is not patched with this fix" if not patched else f"{bad} FAILED"))
    sys.exit(0 if patched and not bad else 1)


if __name__ == "__main__":
    main()
