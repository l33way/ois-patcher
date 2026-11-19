#!/usr/bin/env python3
"""Check of the shop stat-label fix (needs `pip install pefile`).

    python3 tools/ui/test_shop_labels.py <game dir>/ois.exe

Reads the exe and checks the two shop format strings (sensor rating and grappling-arm figure) and that the shop code
still pushes exactly those addresses.  Patched: the new labels, same length, same terminator.  Stock: reports it.
"""
import struct
import sys

import pefile

CASES = (("sensor rating", 0x60E264, b"`7Strength  : %s\n", b"`7Detection : %s\n", 0x494011),
         ("grappling arm", 0x60E134, b"`7Speed     : `!%.0f\n", b"`7Use Time  : `!%.0f\n", 0x493978))


def main():
    exe = sys.argv[1]
    pe = pefile.PE(exe, fast_load=True)
    raw = open(exe, "rb").read()

    def read(va, n):
        for s in pe.sections:
            a = 0x400000 + s.VirtualAddress
            if a <= va < a + s.SizeOfRawData:
                o = s.PointerToRawData + va - a
                return raw[o:o + n]

    patched, bad = None, 0
    for name, va, old, new, push in CASES:
        cur = read(va, len(old) + 3)
        is_new, is_old = cur.startswith(new), cur.startswith(old)
        patched = is_new if patched is None else patched
        ok = (is_new or is_old) and cur[len(old):] == b"\x00\x00\x00" and read(push, 5) == b"\x68" + struct.pack("<I", va)
        bad += not ok or is_new != patched
        print(("  PASS " if ok else "  FAIL ") + f"{name}: {'new' if is_new else 'stock'} label {cur[:len(old)]!r}, "
              f"push at {push:#x} references it")
    print("all shop-label checks pass" if patched and not bad else
          ("exe is not patched with this fix" if not patched else f"{bad} FAILED"))
    sys.exit(0 if patched and not bad else 1)


if __name__ == "__main__":
    main()
