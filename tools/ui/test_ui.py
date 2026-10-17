#!/usr/bin/env python3
"""Checks for the terminal-units / STATUS and forced-conversation fixes (needs `pip install unicorn pefile`).

    python3 tools/ui/test_ui.py <game dir>/ois.exe
"""
import os
import struct
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "common"))
import emu as tp
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_EBX, UC_X86_REG_ECX, UC_X86_REG_EDX, UC_X86_REG_EIP, UC_X86_REG_ESP

SITE, FIRST_VALID, CONTINUE, STATUS_CALL = 0x431B40, 0x430EB0, 0x431B4A, 0x54B361


def main():
    exe = sys.argv[1]
    emu = tp.Emu(exe)
    emu.dist_hooks = (0, 0)
    bad = 0

    def check(name, ok):
        nonlocal bad
        bad += not ok
        print(("  PASS " if ok else "  FAIL ") + name)

    raw = open(exe, "rb").read()
    check("no 'mw' power format strings are left", b"%.2fmw" not in raw and b"%.2fkw" in raw)
    rel = struct.unpack("<i", bytes(emu.uc.mem_read(STATUS_CALL + 1, 4)))[0]
    check("STATUS 'Current Power Drain' now calls totalPowerDrain", STATUS_CALL + 5 + rel == 0x5246B0)

    # forced conversation start: [this+0x94] must become firstValidConversationOption(), registers kept
    def stub(uc, address, size, user):
        if address == FIRST_VALID:
            this = uc.reg_read(UC_X86_REG_ECX)
            uc.reg_write(UC_X86_REG_EAX, emu.r32(this + 0x88) + 7)     # pretend: option 7 is the first valid one
            esp = uc.reg_read(UC_X86_REG_ESP)
            uc.reg_write(UC_X86_REG_EIP, emu.r32(esp))
            uc.reg_write(UC_X86_REG_ESP, esp + 4)

    emu.uc.hook_add(UC_HOOK_CODE, stub, begin=FIRST_VALID, end=FIRST_VALID)
    this = emu.alloc(0x200)
    emu.w32(this + 0x88, 0)
    emu.w32(this + 0x94, 99)
    emu.stops[CONTINUE] = "continue"
    keep = {UC_X86_REG_ECX: 0xAAAA0001, UC_X86_REG_EDX: 0xBBBB0002, UC_X86_REG_EBX: this}
    emu.call_stdcall(SITE, [], regs=keep)
    check("flow continues at the original next instruction", emu.stopped_at == "continue")
    check("selected option = first valid option", emu.r32(this + 0x94) == 7)
    check("ECX and EDX preserved", emu.uc.reg_read(UC_X86_REG_ECX) == 0xAAAA0001 and emu.uc.reg_read(UC_X86_REG_EDX) == 0xBBBB0002)
    check("stack balanced", emu.uc.reg_read(UC_X86_REG_ESP) == tp.STACK_TOP - 0x1000 - 4)
    # news list: selectedArticle(slot) must ignore a slot outside its table (-1 = nothing selected)
    NEWS_SITE, NEWS_BACK = 0x4B5877, 0x4B587C
    cs = emu.alloc(0x100)
    table = emu.alloc(0x40)
    for i in range(3):
        emu.w32(table + 4 * i, 100 + i)
    emu.w32(cs + 0x34, table)
    emu.w32(cs + 0x38, table + 12)
    for slot, expect in ((1, "continue"), (2, "continue"), (3, "returned"), (0xFFFFFFFF, "returned")):
        emu.stops.clear()
        emu.stops[NEWS_BACK] = "continue"
        emu.w32(cs, 55)
        # the code just before the site: EBP frame with the argument at [EBP+8], saved ECX on the stack
        frame = tp.STACK_TOP - 0x2000
        emu.w32(frame + 8, slot)
        emu.w32(frame - 4, cs)
        emu.w32(frame, 0)
        emu.uc.mem_write(0x7FEFFE40, b"\xf4")
        emu.w32(frame + 4, 0x7FEFFE40)
        emu.stopped_at = None
        from unicorn.x86_const import UC_X86_REG_EBP
        emu.stops[0x7FEFFE40] = "returned"
        emu.uc.reg_write(UC_X86_REG_EBP, frame)
        emu.uc.reg_write(UC_X86_REG_ESP, frame - 4)
        emu.uc.reg_write(UC_X86_REG_ECX, cs)
        emu.uc.reg_write(UC_X86_REG_EDX, slot)
        emu.uc.emu_start(NEWS_SITE, 0, count=200)
        check(f"news slot {slot:#x}: {expect}", emu.stopped_at == expect)
    # PDS panel header: long "manufacturer name" must print the name alone, short ones stay as they were
    PDS_SITE, PDS_FMT_PUSH, PDS_AFTER, FORMAT_FN = 0x4F630B, 0x4F6310, 0x4F631E, 0x593B30
    calls = []

    def fmt_stub(uc, address, size, user):
        if address == FORMAT_FN:
            esp = uc.reg_read(UC_X86_REG_ESP)
            fmt = bytes(uc.mem_read(emu.r32(esp + 8), 12)).split(b"\0")[0]
            arg0 = bytes(uc.mem_read(emu.r32(esp + 12), 16)).split(b"\0")[0]
            calls.append((fmt, arg0))
            uc.reg_write(UC_X86_REG_EAX, emu.r32(esp + 4))
            uc.reg_write(UC_X86_REG_EIP, emu.r32(esp))
            uc.reg_write(UC_X86_REG_ESP, esp + 4)       # cdecl: the caller pops the arguments

    emu.uc.hook_add(UC_HOOK_CODE, fmt_stub, begin=FORMAT_FN, end=FORMAT_FN)
    for mfr, name, want in ((b"Pritchard", b"PSL 10X", "long"), (b"Ceres", b"PDL Mk III", "short"),
                            (b"Pritchard", b"PSL 1", "short"), (b"AAAAAAAA", b"BBBBBBB", "short"), (b"AAAAAAAA", b"BBBBBBBB", "long")):
        m, n = emu.alloc(32), emu.alloc(32)
        emu.uc.mem_write(m, mfr + b"\0")
        emu.uc.mem_write(n, name + b"\0")
        emu.stops.clear()
        emu.stops[PDS_FMT_PUSH] = "short"
        emu.stops[PDS_AFTER] = "long"
        calls.clear()
        from unicorn.x86_const import UC_X86_REG_EBP
        frame = tp.STACK_TOP - 0x4000
        emu.uc.reg_write(UC_X86_REG_EBP, frame)
        emu.uc.reg_write(UC_X86_REG_ESP, frame - 0x80)
        emu.uc.reg_write(UC_X86_REG_EAX, m)
        emu.uc.reg_write(UC_X86_REG_ECX, n)
        esp0 = frame - 0x80
        emu.stopped_at = None
        emu.uc.emu_start(PDS_SITE, 0, count=2000)
        ok = emu.stopped_at == want
        if want == "long":
            ok = ok and calls == [(b"`%%%s\n", name)] and emu.uc.reg_read(UC_X86_REG_ESP) == esp0
        else:
            ok = ok and not calls and emu.uc.reg_read(UC_X86_REG_ESP) == esp0 - 8
        check(f"PDS header {mfr.decode()} {name.decode()}: {want}", ok)
    # nav map "Dist." colour: compares with the real jump range (getCurrentJumpRange), not the class range
    NAV_SITE, NAV_OK, NAV_FAR, GET_RANGE = 0x583012, 0x583023, 0x583021, 0x4AE800
    from unicorn.x86_const import UC_X86_REG_XMM0, UC_X86_REG_XMM3
    rng = {"v": 0.0}

    def range_stub(uc, address, size, user):
        if address == GET_RANGE:
            esp = uc.reg_read(UC_X86_REG_ESP)
            uc.reg_write(UC_X86_REG_XMM0, int.from_bytes(struct.pack("<f", rng["v"]) + b"\0" * 12, "little"))
            uc.reg_write(UC_X86_REG_XMM3, 0)               # the real function clobbers XMM3
            uc.reg_write(UC_X86_REG_EIP, emu.r32(esp))
            uc.reg_write(UC_X86_REG_ESP, esp + 4)

    emu.uc.hook_add(UC_HOOK_CODE, range_stub, begin=GET_RANGE, end=GET_RANGE)
    for dist, real, want in ((373.37, 250.0, "far"), (203.61, 250.0, "ok"), (300.0, 380.0, "ok"), (373.37, 373.37, "ok"), (400.0, 380.0, "far")):
        sm = emu.alloc(0x40)
        emu.w32(sm + 0x14, emu.alloc(0x10))
        rng["v"] = real
        emu.stops.clear()
        emu.stops[NAV_OK], emu.stops[NAV_FAR] = "ok", "far"
        emu.stopped_at = None
        frame = tp.STACK_TOP - 0x5000
        emu.uc.reg_write(UC_X86_REG_ESP, frame)
        emu.uc.reg_write(UC_X86_REG_EAX, sm)
        emu.uc.reg_write(UC_X86_REG_XMM3, int.from_bytes(struct.pack("<f", dist) + b"\0" * 12, "little"))
        emu.uc.emu_start(NAV_SITE, 0, count=200)
        keep = struct.unpack("<f", (emu.uc.reg_read(UC_X86_REG_XMM3) & 0xFFFFFFFF).to_bytes(4, "little"))[0]
        check(f"nav distance {dist} vs real range {real}: {want}", emu.stopped_at == want and abs(keep - dist) < 1e-3
              and emu.uc.reg_read(UC_X86_REG_ESP) == frame)
    print("all UI checks pass" if not bad else f"{bad} FAILED")
    sys.exit(1 if bad else 0)
# station-to-ship crash fix:
    # (1) PresentationInterface::update runs runFullFadeLogic before Room::runLogic, and skips
    #     Room::runLogic while fading out ([esi+0x29c]==1) or when a transition ([esi+0x2a4]) fires
    UPD_SITE, UPD_SKIP, FADE_FN, RL_FN = 0x52EF66, 0x52EF7A, 0x52E1F0, 0x536B60
    events = []

    def fade_and_rl_stub(uc, address, size, user):
        esp = uc.reg_read(UC_X86_REG_ESP)
        if address == FADE_FN:
            events.append("fade")
            this_ptr = uc.reg_read(UC_X86_REG_ECX)
            if fade_and_rl_stub.consume_action:
                emu.w32(this_ptr + 0x2A4, 0)  # simulate leaveDockedVessel firing & clearing +0x2a4
            uc.reg_write(UC_X86_REG_EIP, emu.r32(esp))
            uc.reg_write(UC_X86_REG_ESP, esp + 4)
        elif address == RL_FN:
            events.append("runLogic")
            uc.reg_write(UC_X86_REG_EIP, emu.r32(esp))
            uc.reg_write(UC_X86_REG_ESP, esp + 4)

    emu.uc.hook_add(UC_HOOK_CODE, fade_and_rl_stub, begin=FADE_FN, end=RL_FN)
    from unicorn.x86_const import UC_X86_REG_ESI, UC_X86_REG_EBP
    pi = emu.alloc(0x420)
    room = emu.alloc(0x100)
    emu.w32(pi + 0x2D4, room)

    for name, fade_state, action, consume, want in (
        ("normal tick (no fade): fade then runLogic", 0, 0, False, ["fade", "runLogic"]),
        ("fading out (state=1): fade only, runLogic skipped", 1, 3, False, ["fade"]),
        ("transition fired (action 3->0): fade only, runLogic skipped", 2, 3, True, ["fade"]),
    ):
        events.clear()
        fade_and_rl_stub.consume_action = consume
        emu.w32(pi + 0x29C, fade_state)
        emu.w32(pi + 0x2A4, action)
        emu.stops.clear()
        emu.stops[UPD_SKIP] = "done"
        emu.stopped_at = None
        frame = tp.STACK_TOP - 0x6000
        emu.wf(frame + 8, 0.016)
        emu.uc.reg_write(UC_X86_REG_EBP, frame)
        emu.uc.reg_write(UC_X86_REG_ESP, frame - 0x40)
        emu.uc.reg_write(UC_X86_REG_ESI, pi)
        emu.uc.emu_start(UPD_SITE, 0, count=200)
        check(name, emu.stopped_at == "done" and events == want and emu.uc.reg_read(UC_X86_REG_ESP) == frame - 0x40)

if __name__ == "__main__":
    main()
