# Mac PPC Ghidra decompilation (`mac.py` + `c2 mac-decompile`)

When reading raw PS x86 asm gets too noisy, the 1996 Mac PPC build of
Caesar II is a much cleaner source-shape oracle.  Ghidra's PEF loader,
CodeWarrior traceback tables, our TOC-name knowledge AND function
signatures from `c2_funcs.h` combine to give a near-source-quality
decompile of every function.

## Quickstart

```bash
c2 mac-decompile water_trouble          # AST-cleaned decompile (default)
c2 mac-decompile water_trouble --raw    # raw Ghidra output (with PEF indirection)

# Inside decomp-verify:
c2 decomp-verify -f some_function --mac-decompile
```

Or programmatically:

```python
import mac
mac.open()                              # ~25s first run
print(mac.decompile_clean("water_trouble"))
```

## First-run setup

The first call to `mac.open()` (or `c2 mac-decompile`) takes ~25 s and:

1. Imports `MAC/extracted/French retail/Caesar_II_1.0_fr.pef` with the
   `PowerPC:BE:32:default + macosx` language/cspec.
2. Runs Ghidra autoanalysis (finds 1770 functions, names 1291 from CW
   traceback tables).
3. Calls `apply_knowledge()`:
   * strips the CodeWarrior `.` prefix from function names
   * labels all 246 TOC slots in our `.c2-cache/mac/toc_names.fr.json`
     as `_NAME`
   * labels the actual globals (pointed to by each slot) as `NAME`
   * types TOC slots as `int *` and globals as `int`
   * applies ~960 function signatures (return type + typed params) from
     `decomp/include/c2_funcs.h`
4. Saves the resulting project to `MacProject/` (gitignored, ~12 MB).

Subsequent calls reuse the saved project (<3 s for any decompile).

## AST-based PEF indirection cleanup

PEF stores every global in the TOC and the compiler emits an extra
dereference at every read/write.  Ghidra renders this faithfully::

    int *piVar1;
    int *piVar2;
    piVar2 = _water_trouble_rate;     // load TOC slot
    piVar1 = _water_cover;
    get_water_cover();
    if (*piVar1 < 0xb) { *piVar2 = 0; }
    ...

That indirection is NOT in the original C source.  `c2.mac.clean`
postprocesses the decompile with pycparser:

1. Parses Ghidra's output as C (adds a synthetic prolog of typedefs +
   stub decls so the parse succeeds).
2. Collects pointer-alias decls (`T *alias; ... alias = _GLOBAL;`).
3. Rewrites every `*alias` -> `ID(global)` and bare `alias` ->
   `&global`, plus the same for direct `*_GLOBAL` references.
4. Drops the alias decls and alias-init assignments.
5. Regenerates clean C via pycparser's `CGenerator`.

Result::

    void water_trouble(void) {
      get_water_cover();
      if (water_cover < 0xb)    { water_trouble_rate = 0; }
      else if (water_cover < 0x17) { water_trouble_rate = 2; }
      ...
    }

If parsing fails (unrecognised Ghidra construct, anonymous globals, etc.)
the raw output is returned with a leading comment, never silently lost.

## Three Mac oracles

* **`c2 mac-fn <name>`** -- raw PPC disasm with TOC-name annotations.
  Use when you want to see the actual register flow / ABI details.
* **`c2 mac-decompile <name>`** -- Ghidra C with PEF indirection collapsed.
  Use when you want to read the original C source shape.
* **`c2 decomp-verify -f <name> --mac-decompile`** -- show the Mac
  decompile inline next to the byte diff so you don't have to context-switch.

## Reproducibility

Everything is rebuildable from sources in the repo:

* PEF binary: `MAC/extracted/French retail/Caesar_II_1.0_fr.pef`
* TOC name map: `.c2-cache/mac/toc_names.fr.json` (committed)
* Function signatures: `decomp/include/c2_funcs.h` (committed)
* The Ghidra project: `MacProject/` is gitignored.  Delete it any time
  and the next `mac.open()` rebuilds in ~25 s with everything re-applied.

To extend the TOC map, see `c2.macref.build_toc_map` (cross-build PS
data-symbol correlation, ~1 min).

## When to use which

| Need | Oracle |
|------|--------|
| Match bytes (the actual goal) | PS x86 disasm (`c2 disasm`) |
| ABI / register / signedness signals | `c2 mac-fn` (raw PPC disasm) |
| Source structure, control flow, parameter intent | `c2 mac-decompile` (AST-cleaned C) |
| Side-by-side while reviewing a diff | `c2 decomp-verify --mac-decompile` |

The Mac source is a 1996 snapshot vs PS's 1995 vintage -- small drifts
exist (`screen_mode` is `int` in Mac, `char` in PS).  Compare structure,
not gospel.
