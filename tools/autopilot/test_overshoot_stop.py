#!/usr/bin/env python3
"""Emulation test for the autopilot last-second-overshoot fix (needs `pip install unicorn pefile`).

    python3 tools/autopilot/test_overshoot_stop.py <exe>          (ois.exe or ois_server.exe; patched or stock)

1. Overshoot branch of the final-waypoint "decelerate" state.  Stock: empties the waypoint list and re-enters
   state 4 (a no-op), after which the autopilot ends with the drive still on.  Patched: calls Ship::allStop with
   `this` in ECX, leaves the list alone, and returns to the original epilogue.
2. performAllStopLogic's halt test: stock halts at speed <= 0.1, patched at speed <= 0.3.
Exit 0 only for a patched exe; a stock exe prints what it does and exits 1.
"""
import os
import struct
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "common"))
import emu as tp
from unicorn.x86_const import UC_X86_REG_EBP, UC_X86_REG_EBX, UC_X86_REG_ECX, UC_X86_REG_EDI, UC_X86_REG_EIP, UC_X86_REG_ESP


def main():
    exe = sys.argv[1]
    server = "server" in os.path.basename(exe).lower()
    OVER, HALT, ALLSTOP = (0x516F94, 0x517175, 0x518AF0) if server else (0x517A84, 0x517C65, 0x5195E0)
    emu = tp.Emu(exe)
    emu.dist_hooks = (0, 0)
    patched = emu.uc.mem_read(OVER + 3, 1)[0] == 0x90
    bad = 0

    # ---- 1. overshoot branch -------------------------------------------------------------------------------
    sh, lst, wps = emu.alloc(0x400), emu.alloc(0x20), emu.alloc(0x40)
    emu.w32(lst, wps)
    emu.w32(lst + 4, wps + 0x20)                        # one waypoint in the list
    frame = tp.STACK_TOP - 0x3000
    stack = frame - 0x100
    emu.w32(stack, 0xDEAD0001)
    emu.w32(stack + 4, 0xDEAD0002)                      # the two debugPrint args the branch pops
    for r, v in ((UC_X86_REG_EBP, frame), (UC_X86_REG_ESP, stack), (UC_X86_REG_EBX, lst), (UC_X86_REG_EDI, sh)):
        emu.uc.reg_write(r, v)
    seen = {}

    def hook(uc, address, size, _):
        if address == ALLSTOP:
            seen["allStop"] = (uc.reg_read(UC_X86_REG_ECX), emu.r32(uc.reg_read(UC_X86_REG_ESP)))
            uc.emu_stop()
        elif address > OVER + 17 and "tail" not in seen and address < OVER + 0x40:
            seen["tail"] = address
            uc.emu_stop()
    from unicorn import UC_HOOK_CODE
    h = emu.uc.hook_add(UC_HOOK_CODE, hook)
    emu.stops.clear()
    try:
        emu.uc.emu_start(OVER, 0, count=40)
    except Exception as e:                              # the stock branch walks into switchTravelState / epilogue
        seen["err"] = type(e).__name__
    emu.uc.hook_del(h)
    list_end = emu.r32(lst + 4)
    if patched:
        checks = (("calls Ship::allStop with this in ECX", seen.get("allStop", (None,))[0] == sh),
                  ("returns to the original epilogue", seen.get("allStop", (0, 0))[1] == OVER + 17),
                  ("leaves the waypoint list alone", list_end == wps + 0x20))
    else:
        checks = (("STOCK: empties the waypoint list (the latch)", list_end == wps),
                  ("STOCK: does not call Ship::allStop", "allStop" not in seen))
    for name, ok in checks:
        bad += (not ok) if patched else 0
        print(("  PASS " if ok else "  FAIL ") + name)

    # ---- 2. halt threshold ---------------------------------------------------------------------------------
    want_patched = {0.05: "halt", 0.25: "halt", 0.299: "halt", 0.35: "burn", 1.3: "burn"}
    want_stock = {0.05: "halt", 0.25: "burn", 0.299: "burn", 0.35: "burn", 1.3: "burn"}
    for speed, want in sorted((want_patched if patched else want_stock).items()):
        frame = tp.STACK_TOP - 0x3400
        emu.uc.reg_write(UC_X86_REG_EBP, frame)
        emu.uc.reg_write(UC_X86_REG_ESP, frame - 0x100)
        emu.uc.emu_start(HALT, 0, count=1)              # movss xmm0,[threshold]
        emu.wf(frame - 0x10, speed)
        emu.uc.reg_write(UC_X86_REG_EIP, HALT + 0xB)    # skip the fstp, whose FPU input is not modelled
        emu.uc.emu_start(HALT + 0xB, 0, count=2)        # comiss ; jb (short)
        got = "burn" if emu.uc.reg_read(UC_X86_REG_EIP) != HALT + 0xB + 4 + 2 else "halt"
        ok = got == want
        bad += (not ok) if patched else 0
        print(("  PASS " if ok else "  FAIL ") + f"speed {speed}: {got}")
    print("all overshoot-stop checks pass" if patched and not bad else
          ("exe is not patched with this fix" if not patched else f"{bad} FAILED"))
    sys.exit(0 if patched and not bad else 1)


if __name__ == "__main__":
    main()
