#!/usr/bin/env python3
"""Emulation test of the solar-wing Range rating cut-offs (needs `pip install unicorn pefile`).

    python3 tools/ui/test_solar_range_rating.py <game dir>/ois.exe

Runs the four compares of the shop's solar-wing Range rating with the wing's `range` in XMM0 (the last one is
`comiss xmm0,xmm1 ; jb` in stock, a call to a cave stub in the patched exe), finds each cut-off by bisection, and rates the
four real wings (range 1.05-1.35, from modules_solar.txt).  Patched: cut-offs 1.1 / 1.15 / 1.28 / 1.4.  Stock: exits 1.
"""
import os
import struct
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "common"))
import emu as tp
from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_EBP, UC_X86_REG_EFLAGS, UC_X86_REG_ESP, UC_X86_REG_XMM0, UC_X86_REG_XMM1

SITES = (0x494548, 0x494559, 0x49456A)                      # 1.8 / 1.6 / 1.4 in stock
LAST = 0x49457B                                             # comiss xmm0,xmm1 (0.0) ; jb 0x494588
BANDS = ("V. Bad", "Bad", "Medium", "Good", "V. Good")
WINGS = (("SLSP", 1.2, "Medium"), ("SLSP AE", 1.05, "V. Bad"), ("E SOLAR", 1.35, "Good"), ("E SOLAR MK 2", 1.35, "Good"))
f = lambda v: int.from_bytes(struct.pack("<f", v) + b"\0" * 12, "little")


def main():
    exe = sys.argv[1]
    emu = tp.Emu(exe)
    emu.dist_hooks = (0, 0)
    patched = emu.uc.mem_read(SITES[0], 1)[0] == 0xE8

    def setup(value):
        frame = tp.STACK_TOP - 0x3000
        emu.uc.reg_write(UC_X86_REG_EBP, frame)
        emu.uc.reg_write(UC_X86_REG_ESP, frame - 0x100)
        emu.uc.reg_write(UC_X86_REG_EAX, 0x1234)
        emu.uc.reg_write(UC_X86_REG_XMM0, f(value))
        emu.uc.reg_write(UC_X86_REG_XMM1, f(0.0))
        emu.stops.clear()
        emu.stopped_at = None

    def below(site, value):
        setup(value)
        if site == LAST:
            emu.stops[0x494580], emu.stops[0x494588] = "fall", "below"
            emu.uc.emu_start(site, 0, count=40)
            assert emu.uc.reg_read(UC_X86_REG_EAX) == 0x1234 and emu.stopped_at in ("fall", "below")
            return emu.stopped_at == "below"
        emu.stops[site + 7] = "done"
        emu.uc.emu_start(site, 0, count=40)
        assert emu.stopped_at == "done" and emu.uc.reg_read(UC_X86_REG_EAX) == 0x1234
        return bool(emu.uc.reg_read(UC_X86_REG_EFLAGS) & 1)

    cuts = []
    for site in SITES + (LAST,):
        lo, hi = -1.0, 10.0
        for _ in range(50):
            mid = (lo + hi) / 2
            lo, hi = (lo, mid) if not below(site, mid) else (mid, hi)
        cuts.append(round((lo + hi) / 2, 3))
    cuts.sort()
    print("  cut-offs found by the compares:", cuts)
    ok = cuts == [1.1, 1.15, 1.28, 1.4]
    bad = not ok
    print(("  PASS " if ok else "  FAIL ") + "cut-offs are 1.1 / 1.15 / 1.28 / 1.4" + ("" if ok else " (stock: 0 / 1.4 / 1.6 / 1.8)"))
    for name, rng, want in WINGS:
        band = BANDS[sum(1 for c in cuts if struct.unpack("<f", struct.pack("<f", rng))[0] >= c)]
        ok = band == want
        bad += not ok
        print(("  PASS " if ok else "  FAIL ") + f"{name:<13} range {rng}: {band}")
    print("all solar-range checks pass" if patched and not bad else
          ("exe is not patched with this fix" if not patched else f"{bad} FAILED"))
    sys.exit(0 if patched and not bad else 1)


if __name__ == "__main__":
    main()
