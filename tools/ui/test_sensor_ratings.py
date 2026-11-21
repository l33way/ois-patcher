#!/usr/bin/env python3
"""Emulation test of the sensor-page changes (needs `pip install unicorn pefile`).

    python3 tools/ui/test_sensor_ratings.py <game dir>/ois.exe

Finds the cut-offs of the shop's "Detect Rng" (sensorquality) and "Sns. Ghsts" (ghosttimer) ratings by bisecting the
exe's own compares, rates every sensor in modules_sensors.txt / modules_npc.txt with them, and checks that the sensor's
"Range : 0Gm" line is now "Soft. Ver.: <softwareversion>" (the argument set-up is run up to the formatter call).  Patched: detection cut-offs 0.55 / 0.75 / 0.95 / 1.15, ghost
cut-offs 180 / 220 / 250 / 300.  Stock: exits 1.
"""
import os
import struct
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "common"))
import emu as tp
from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_EBP, UC_X86_REG_EFLAGS, UC_X86_REG_ESP, UC_X86_REG_XMM0

GHOST = (0x493D34, 0x493D45, 0x493D56, 0x493D67)
DETECT = (0x493FA2, 0x493FB3, 0x493FC4, 0x493FD5)
# id, sensorquality, ghosttimer (count, sides, const)   -- from the game's modules_sensors.txt / modules_npc.txt
SENSORS = (("C1-SNS", 0.8, (12, 32, 43)), ("C5-SNS", 1.2, (12, 32, 43)), ("D2-SNS", 0.4, (10, 32, 32)),
           ("D4-SNS", 0.6, (10, 32, 32)), ("M1-SNS", 0.9, (22, 32, 32)), ("M2-SNS", 1.0, (22, 32, 32)),
           ("SL-SNS", 1.0, (14, 32, 32)), ("SM-SNS", 1.1, (14, 32, 32)), ("SQ-SNS", 1.3, (14, 32, 32)),
           ("T9-SNS", 0.6, (22, 32, 32)), ("T0-SNS", 0.8, (22, 32, 14)), ("RM-SNS", 5.0, (14, 32, 32)),
           ("Probe", 1.2, (8, 12, 24)))
DET_BANDS = ("V. Bad", "Bad", "Medium", "Good", "V. Good")
GHOST_BANDS = ("V. High", "High", "Moderate", "Low", "V. Low")      # more ghosts .. fewer ghosts
WANT_DET = {"C1-SNS": "Medium", "C5-SNS": "V. Good", "D2-SNS": "V. Bad", "D4-SNS": "Bad", "M1-SNS": "Medium",
            "M2-SNS": "Good", "SL-SNS": "Good", "SM-SNS": "Good", "SQ-SNS": "V. Good", "T9-SNS": "Bad",
            "T0-SNS": "Medium", "RM-SNS": "V. Good", "Probe": "V. Good"}
WANT_GHOST = {"C1-SNS": "Moderate", "C5-SNS": "Moderate", "D2-SNS": "High", "D4-SNS": "High", "M1-SNS": "V. Low",
              "M2-SNS": "V. Low", "SL-SNS": "Low", "SM-SNS": "Low", "SQ-SNS": "Low", "T9-SNS": "V. Low",
              "T0-SNS": "V. Low", "RM-SNS": "Low", "Probe": "V. High"}


def main():
    exe = sys.argv[1]
    emu = tp.Emu(exe)
    emu.dist_hooks = (0, 0)
    patched = emu.uc.mem_read(GHOST[0], 1)[0] == 0xE8

    def below(site, value):
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

    def cutoffs(sites, hi):
        out = []
        for site in sites:
            lo, h = 0.0, hi
            for _ in range(50):
                mid = (lo + h) / 2
                lo, h = (lo, mid) if not below(site, mid) else (mid, h)
            out.append(round((lo + h) / 2, 3))
        return sorted(out)

    det, gh = cutoffs(DETECT, 20.0), cutoffs(GHOST, 2000.0)
    print("  detection cut-offs:", det, " ghost cut-offs:", gh)
    bad = 0
    for name, ok in (("detection cut-offs 0.55 / 0.75 / 0.95 / 1.15", det == [0.55, 0.75, 0.95, 1.15]),
                     ("ghost cut-offs 180 / 220 / 250 / 300", gh == [180, 220, 250, 300])):
        bad += not ok
        print(("  PASS " if ok else "  FAIL ") + name)
    f32 = lambda v: struct.unpack("<f", struct.pack("<f", v))[0]
    spread_d, spread_g = [0] * 5, [0] * 5
    for name, q, (n, sides, k) in SENSORS:
        d = DET_BANDS[sum(1 for c in det if f32(q) >= f32(c))]
        g = GHOST_BANDS[sum(1 for c in gh if ((sides + 1) // 2) * n + k >= c)]
        spread_d[DET_BANDS.index(d)] += 1
        spread_g[GHOST_BANDS.index(g)] += 1
        ok = d == WANT_DET[name] and g == WANT_GHOST[name]
        bad += not ok
        print(("  PASS " if ok else "  FAIL ") + f"{name:<8} quality {q:<4} -> {d:<8} ghosts {((sides + 1) // 2) * n + k:>3} -> {g}")
    print("  detection spread:", spread_d, " ghost spread:", spread_g)
    # the line that used to be "Range : <float>Gm": run its argument set-up up to the formatter call
    from unicorn.x86_const import UC_X86_REG_ECX, UC_X86_REG_EDX
    cls = 0x2000000
    emu.uc.mem_map(cls, 0x1000)
    emu.uc.mem_write(cls + 0x108, struct.pack("<f", 123.0))
    for ver in (0, 1, 2, 3):
        emu.uc.mem_write(cls + 0xB0, struct.pack("<i", ver))
        frame = tp.STACK_TOP - 0x3000
        emu.uc.reg_write(UC_X86_REG_EBP, frame)
        emu.uc.reg_write(UC_X86_REG_ESP, frame - 0x100)
        emu.uc.reg_write(UC_X86_REG_ECX, cls)
        emu.stops.clear()
        emu.stops[0x493CC2] = "call"
        emu.stopped_at = None
        emu.uc.emu_start(0x493CA6, 0, count=40)
        assert emu.stopped_at == "call"
        esp = emu.uc.reg_read(UC_X86_REG_ESP)
        out, fmt, arg = struct.unpack("<III", bytes(emu.uc.mem_read(esp, 12)))
        text = bytes(emu.uc.mem_read(fmt, 40)).split(b"\0")[0].decode("latin1")
        if patched:
            ok = text == "`7Soft. Ver.: `!%d\n" and arg == ver and out == frame - 0x28
        else:
            ok = "Range" in text
        bad += not ok
        print(("  PASS " if ok else "  FAIL ") + f"sensor line: softwareversion {ver} -> format {text!r}, argument {arg}")
    print("all sensor-rating checks pass" if patched and not bad else
          ("exe is not patched with this fix" if not patched else f"{bad} FAILED"))
    sys.exit(0 if patched and not bad else 1)


if __name__ == "__main__":
    main()
