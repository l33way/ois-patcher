# tools/spinup — weapon spin-up fix

Developer tooling for `fix_weapon_spinup` in `ois_patcher.py`.

| File | Purpose |
|------|---------|
| `test_spinup.py` | Runs all seven spin-up sites of a patched exe in a CPU emulator (`pip install unicorn pefile`) with `getEfficiencyPercent` stubbed to a chosen efficiency, and checks each gives `int(spinuptime * 0.5 * (2 - e))`. On a stock exe it reports that the stock formula (`... * e`) is in use and exits 1. |

```
python tools/spinup/test_spinup.py <game dir>/ois.exe
python tools/spinup/test_spinup.py <game dir>/ois_server.exe
```

The test proves the arithmetic at every site. It does not run the game; the object layout it builds comes
from the decompile.
