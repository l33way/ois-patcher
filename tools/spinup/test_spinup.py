#!/usr/bin/env python3
"""Emulation test for --weapon-spinup-fix (needs `pip install unicorn pefile`).

    python3 tools/spinup/test_spinup.py <game dir>/ois.exe        (or ois_server.exe)

All seven places that compute a weapon tube's spin-up figure are run from their `call getEfficiencyPercent`
to the instruction that truncates the result to an integer (the timer start in ShipModule::runLogic is
read back from the weapon's timer instead).  getEfficiencyPercent itself is stubbed to return a chosen
efficiency; every other instruction is the exe's own.

  patched exe : every site must give  int(spinuptime * 0.5 * (2 - efficiency/100))   -> exit 0
  stock exe   : every site gives      int(spinuptime * 0.5 * efficiency/100)         -> reported, exit 1
"""
import ctypes
import os
import struct
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "common"))
import emu as tp
from unicorn.x86_const import UC_X86_REG_EBP, UC_X86_REG_EBX, UC_X86_REG_EDI, UC_X86_REG_ESI, UC_X86_REG_ESP

f32 = lambda v: ctypes.c_float(v).value

# (call getEfficiencyPercent, offset of the instruction after the truncation, register holding the int)
SITES_CLIENT = {"ShipModule::runLogic": (0x4AF43D, 0x56), "Ship::fireWeapon": (0x510400, 0x40),
                "doSetWeaponTarget": (0x4E3D40, 0x37), "getTubeSpinUpPercent": (0x4ECC13, 0x31),
                "getTubeSummary": (0x4F0F8C, 0x36), "getTubeAdvancedSummary": (0x4F1553, 0x33),
                "UI_WeaponTubes::render": (0x590360, 0x34)}
SITES_SERVER = {"ShipModule::runLogic": (0x4AF2ED, 0x56), "Ship::fireWeapon": (0x50FCA0, 0x40),
                "doSetWeaponTarget": (0x4E3830, 0x37), "getTubeSpinUpPercent": (0x4EC673, 0x31),
                "getTubeSummary": (0x4F09FC, 0x36), "getTubeAdvancedSummary": (0x4F0FC3, 0x33),
                "UI_WeaponTubes::render": (0x58E630, 0x34)}
CASES = [(24.0, 100), (21.5, 124), (17.0, 150), (26.5, 164), (24.0, 182), (19.0, 138)]


def stock(spin, eff):
    return int(f32(f32(f32(eff) / f32(100)) * f32(0.5)) * f32(spin))


def fixed(spin, eff):
    return int(f32(f32(f32(200 - eff) / f32(100)) * f32(0.5)) * f32(spin))


def main():
    exe = sys.argv[1]
    server = "server" in os.path.basename(exe).lower()
    sites = SITES_SERVER if server else SITES_CLIENT
    get_eff = tp.Emu(exe)                       # only to read where the call goes
    bad = 0
    modes = {"fixed": 0, "stock": 0, "other": 0}
    for name, (call, end_off) in sites.items():
        for spin, eff in CASES:
            emu = tp.Emu(exe)
            emu.dist_hooks = (0, 0)
            rel = struct.unpack("<i", emu.uc.mem_read(call + 1, 4))[0]
            target = call + 5 + rel
            # a patched site calls the stub, which calls getEfficiencyPercent: find the real one from the stub
            stub = bytes(emu.uc.mem_read(target, 13))
            if stub[0] == 0xE8 and stub[5:] == bytes.fromhex("F7D805C8000000C3"):
                emu.eff_addr = target + 5 + struct.unpack("<i", stub[1:5])[0]
            else:
                emu.eff_addr = target
            emu.efficiency = eff
            cls, p2, p1, weapon, x = emu.alloc(0x200), emu.alloc(0x100), emu.alloc(0x100), emu.alloc(0x500), emu.alloc(0x500)
            emu.wf(cls + 0x108, spin)
            emu.w32(p2 + 8, cls)
            emu.w32(p2 + 0x30, 0)
            emu.w32(p2 + 0x3C, weapon)
            emu.w32(p1 + 0x20, p2)
            emu.w32(p1 + 8, cls)
            emu.w32(x + 4, p1)
            emu.w32(x + 0x40, p1)
            scratch = emu.alloc(0x800)
            for reg in (UC_X86_REG_EBX, UC_X86_REG_ESI, UC_X86_REG_EDI):
                emu.uc.reg_write(reg, x)
            emu.uc.reg_write(UC_X86_REG_EBP, scratch + 0x400)
            emu.uc.reg_write(UC_X86_REG_ESP, tp.STACK_TOP - 0x2000)
            emu.stops = {call + end_off: "end"}
            emu.uc.emu_start(call, call + 0x200, count=4000)
            if name == "ShipModule::runLogic":
                got = int(emu.rf(weapon + 0x3C0))
            elif name == "Ship::fireWeapon":
                got = emu.uc.reg_read(__import__("unicorn").x86_const.UC_X86_REG_EDX)
            else:
                got = emu.uc.reg_read(__import__("unicorn").x86_const.UC_X86_REG_EAX)
            got = ctypes.c_int32(got).value
            mode = "fixed" if got == fixed(spin, eff) else "stock" if got == stock(spin, eff) else "other"
            if fixed(spin, eff) == stock(spin, eff):
                mode = "fixed"
            modes[mode] += 1
            ok = mode == "fixed"
            bad += not ok
            print(("  PASS " if ok else "  FAIL ") + f"{name:<24} spinup {spin:>5} at {eff}%: {got:>3}  "
                  f"(fixed {fixed(spin, eff)}, stock formula {stock(spin, eff)})")
    print(f"\n{sum(modes.values()) - bad} of {sum(modes.values())} match the fixed formula"
          + ("" if modes["stock"] == 0 else f"; {modes['stock']} match the stock formula (exe is not patched)"))
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
