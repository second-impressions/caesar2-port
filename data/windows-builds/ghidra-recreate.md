# Recreating the Windows CAESAR2.EXE ghidra database

The ghidra project is **disposable** — every durable result is committed to
files in this directory + the decomp headers.  **Recreate it with one command**
(`c2win.py`, the pyghidra recovery script, modelled on `mac.py`):

```python
import c2win
c2win.open()        # imports build A, analyzes, re-bakes ALL knowledge (~60s)
print(c2win.decompile('city_pop_limit_10_to_1'))   # named, typed, near-source
```

`c2win.open()` imports `caesar2_A_1044480.exe` (sha256 caca2babb57d9450…, the
closest build to the -d1 PS.EXE; PE32 x86, base 0x400000, .text @ 0x401000),
autoanalyzes, then `apply_knowledge()` bakes in everything below.  The
`C2WinProject/` dir is gitignored (rebuildable).  (A non-fatal
`WindowsResourceReferenceAnalyzer` NPE prints during headless analysis — it
does not affect code analysis.)

**`apply_knowledge()` applies, from committed files (verified, 0 failures):**
* **1187 function names** ← `func-map.json`
* **1079 global labels, 901 typed** ← `globals-map.json` (names+addrs) +
  `decomp/include/c2_data.h` (types; the 178 untyped are `[]` arrays with no
  declared element count)
* **1168 function signatures** (param names + types) ← `decomp/include/c2_funcs.h`

Validation: `city_pop_limit_10_to_1(int value,int factor)` decompiles with the
global `population` correctly named; `water_trouble()` shows `water_cover` /
`water_trouble_rate`.

## globals-map.json — how global→address was recovered

From the **compile-exact** matched functions, each obj DIR32 relocation names a
global; the matched Windows function's bytes at that offset hold `symbol_VA +
addend`, and the obj's pre-link bytes hold the addend → `symbol_VA`.  Voted
across all sites (**372 globals, tier `exact`**).  Extended by **instruction-
level alignment** over all 1187 matched functions (align mnemonic sequences,
subtract the obj operand displacement from the win one) → **+707** (`instr-
multi` ≥2 agreeing votes / `instr-single`).  Exact↔instr agreement 97%.
Total **1079 / ~1338** referenced PS-named globals.  ~265 remain (referenced
only by platform-divergent or unmatched functions — hand-map as needed; the
rows list which mapped callers reference them).

## Legacy ghidra-cli path (equivalent, no signatures/globals)

```bash
ghidra-cli import  caesar2_A_1044480.exe --project c2win95 --program CAESAR2.EXE
ghidra-cli analyze --project c2win95 --program CAESAR2.EXE
# then replay func-map.csv via `ghidra-cli function rename <win_va> <ps_name>`
```

Durable artifacts (do not depend on the ghidra DB):
* `func-map.json` / `func-map.csv` — PS.EXE function name → Windows VA mapping.
* `win_funcs.json` — address-ordered Windows function list (FUN_ + sizes).
* `ps_game_funcs.json` — address-ordered PS.EXE game-code functions (names+TU).

Re-applying names to a fresh DB: replay `func-map.csv` through
`ghidra-cli function rename <win_va> <ps_name>` (address-based; works
regardless of the current FUN_ names).

## How the 1,187-function map was built (3 levers, by confidence tier)

1. **compile-exact (315)** — compile each game TU with the MSVC 4.0
   container (`localhost/msvc-4.00-wibo`, `cl /Od /Zp1 /I _msvc_shim
   /I include /FIc2_funcs.h /D__pascal= /D__far=`), parse the COFF
   object, mask relocations (DIR32/REL32), byte-search CAESAR2.EXE.
   Self-contained `/Od` code matches exactly. DOS-only TUs need the
   `decomp/_msvc_shim/i86.h` shim (REGS/SREGS/find_t/MK_FP/int386…).
2. **ordinal (555+176+94+1)** — within a TU the function order is
   preserved across Watcom↔MSVC, so functions between two exact anchors
   (count-consistent) map 1:1 by position; pre/post extends to TU edges;
   `ordinal-bracket` fills single gaps between mapped PS neighbors.
3. **fuzzy (33+13)** — for packing-shifted code (large struct-heavy
   funcs) where exact match fails, normalize to capstone mnemonic
   sequences (operands wildcarded) and align by similarity. This located
   the whole `pm_map1.c` (22 fns) and `pm_map3.c` (11 fns) blocks whose
   absolute layout is permuted vs PS.

Scripts: `scripts/compile_match_all.sh` (batch compile),
`scripts/fingerprint_pe.py`, `scripts/verify_msvc_crt.py`.
The Python matching pipeline lives in the session notebook; key inputs
are `data/out/symbols.json` (PS link order) + the ghidra function list.

**Coverage:** 1,187/1,451 game functions (~82%); **124/131 still-diffing
decomp functions have a Windows `/Od` oracle (95%)**; all 16 TUs holding
diffing functions are mapped.  The 7 unmapped diffing functions are
either platform-divergent (`install_mouse`, `start_samples`,
`convert_lbm_file` — DOS I/O, no Windows counterpart) or sit in gaps
with a build-structure count mismatch (different inlining: e.g.
`sf14_opertunist_fire`, `set_route_elastic_range`).
