#!/usr/bin/env python3
"""Emulation test for the LADAR id alias (needs `pip install unicorn pefile`).

    python3 tools/save/test_module_alias.py <exe>        (ois.exe or ois_server.exe; patched or stock)

Runs the exe's own GameData::getModuleClassWithIdentifier against a hand-built module list that holds the
renamed LADAR modules (ids mkxladr2 / mkxladrt) and a few others.  Patched: the old ids mkxladara2 / mkxladarat
find those modules too, and nothing else changes.  Stock: the old ids find nothing.  Exit 0 only when patched.

Heap-allocated identifiers (capacity > 15) are not exercised: the function frees them through operator_delete, which this
harness does not model.  The cave leaves them alone with its first compare (`cmp [ebp+0x1c],0xf ; ja`).
"""
import os
import struct
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "common"))
import emu as tp

NEW = ["mkxladr2", "mkxladrt", "mkxladra", "mtlc100"]


def main():
    exe = sys.argv[1]
    server = "server" in os.path.basename(exe).lower()
    FUNC, GGD = (0x4A8020, 0x65B5CC) if server else (0x4A8150, 0x65D704)
    emu = tp.Emu(exe)
    emu.dist_hooks = (0, 0)
    patched = emu.uc.mem_read(FUNC + 0xA, 1)[0] == 0xE9
    gd = emu.alloc(0x100)
    emu.w32(GGD, gd)
    classes = [emu.alloc(0x100) for _ in NEW]
    arr = emu.alloc(4 * len(NEW))
    for i, (c, name) in enumerate(zip(classes, NEW)):
        emu.string(c + 0x50, name)
        emu.w32(arr + 4 * i, c)
    emu.w32(gd + 0xC, arr)
    emu.w32(gd + 0x10, arr + 4 * len(NEW))
    by_name = dict(zip(NEW, classes))

    def lookup(text, heap=False):
        s = emu.alloc(0x20)
        b = text.encode()
        if heap or len(b) >= 16:
            p = emu.alloc(len(b) + 1)
            emu.uc.mem_write(p, b + b"\0")
            emu.w32(s, p)
            emu.w32(s + 0x14, max(len(b), 0x1F))
        else:
            emu.uc.mem_write(s, b + b"\0" * (16 - len(b)))
            emu.w32(s + 0x14, 0xF)
        emu.w32(s + 0x10, len(b))
        words = [emu.r32(s + 4 * i) for i in range(6)]
        eax, popped = emu.call_stdcall(FUNC, words)
        return eax, popped

    bad = 0
    cases = [("old LADAR A-2 id", "mkxladara2", by_name["mkxladr2"], by_name["mkxladr2"] if patched else 0),
             ("old LADAR A-T id", "mkxladarat", by_name["mkxladrt"], by_name["mkxladrt"] if patched else 0),
             ("new id still works", "mkxladr2", by_name["mkxladr2"], by_name["mkxladr2"]),
             ("neighbour mkxladra (9 chars)", "mkxladra", by_name["mkxladra"], by_name["mkxladra"]),
             ("unrelated module", "mtlc100", by_name["mtlc100"], by_name["mtlc100"]),
             ("unknown id", "nosuchmod1", 0, 0),
             ("10 chars, similar prefix", "mkxladarxx", 0, 0)]
    for name, text, _, want in cases:
        got, popped = lookup(text)
        ok = got == want and popped == 0x18
        bad += not ok if (patched or not name.startswith("old")) else 0
        print(("  PASS " if ok else ("  FAIL " if patched or not name.startswith("old") else "  (stock) ")) +
              f"{name}: {'found' if got else 'not found'}, stack popped {popped:#x}")
    print("all alias checks pass" if patched and not bad else ("exe is not patched with this fix" if not patched else f"{bad} FAILED"))
    sys.exit(0 if patched and not bad else 1)


if __name__ == "__main__":
    main()
