#!/usr/bin/env python3
"""Emulation test for the uninitialised "stealthy" flag fix (needs `pip install unicorn pefile`).

    python3 tools/behaviour/test_behaviour.py <game dir>/ois.exe        (or ois_server.exe)

Runs the patched last store of the ShipBehaviour constructor on an object whose memory is filled
with 0x20 (leftover heap), and checks that +0x158..+0x163 are zeroed (+0x160 is the flag that
makes general_runLogic run a ship dark), that the neighbours are untouched, and that execution
continues at the instruction after the original store.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "common"))
import emu as tp
from unicorn.x86_const import UC_X86_REG_EDI, UC_X86_REG_EIP


def main():
    exe = sys.argv[1]
    server = "server" in os.path.basename(exe).lower()
    site = 0x502144 if server else 0x502864
    emu = tp.Emu(exe)
    emu.dist_hooks = (0, 0)
    obj = emu.alloc(0x200)
    emu.uc.mem_write(obj, b"\x20" * 0x200)
    emu.uc.reg_write(UC_X86_REG_EDI, obj)
    emu.uc.emu_start(site, site + 10)
    mem = bytes(emu.uc.mem_read(obj, 0x200))
    fails = []

    def check(name, cond):
        print(("  PASS " if cond else "  FAIL ") + name)
        if not cond:
            fails.append(name)

    check("+0x158..+0x15F zeroed", mem[0x158:0x160] == b"\0" * 8)
    check("+0x160 (stealthy flag) .. +0x163 zeroed", mem[0x160:0x164] == b"\0" * 4)
    check("+0x154 and +0x164 untouched", mem[0x154:0x158] == b"\x20" * 4 and mem[0x164:0x168] == b"\x20" * 4)
    check("execution continues after the original store", emu.uc.reg_read(UC_X86_REG_EIP) == site + 10)
    print("all behaviour checks pass" if not fails else f"{len(fails)} FAILED")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
