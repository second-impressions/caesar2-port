# Watcom C/C++ 10.0a documentation (Markdown)

The original IBM IPF help files (`.inf`) shipped with the Watcom 10.0a
toolchain — the **exact compiler that built PS.EXE** — converted to
Markdown. These are the authoritative docs for compiler options,
pragmas, calling conventions, the C library, and the linker, straight
from the toolchain image (NOT the later OpenWatcom v1/v2 fork).

## Source & regeneration
Extracted from `localhost/watcom-10.0a-wibo:/opt/watcom/binp/help/*.inf`
and converted by `tools/inf2md.py` (a faithful decoder of the OS/2 IPF
compiled-help format — magic `HS` — per Marcus Groeber / Carl Hauser's
`inf02b.doc` spec). To regenerate:

```sh
cid=$(podman create localhost/watcom-10.0a-wibo)
for f in cguide clib cmix cpplib pguide lguide tools ide wd \
         wbrw wprof wccerrs wpperrs som ipfc20; do
  podman cp $cid:/opt/watcom/binp/help/$f.inf /tmp/$f.inf
  python3 tools/inf2md.py /tmp/$f.inf docs/watcom-10.0a/$f.md
done
podman rm $cid
```

## Files
| file | manual | most relevant to us |
|---|---|---|
| `cguide.md` | **C/C++ User's Guide** | **compiler options, all `#pragma`s (pack/aux/intrinsic/...), calling conventions, memory layout** |
| `pguide.md` | C/C++ Programmer's Guide | language, code generation, data representation |
| `clib.md` | C Library Reference | CRT function semantics |
| `cmix.md` | C/C++ combined reference | large combined index |
| `cpplib.md` | C++ Library Reference | (C++ only) |
| `lguide.md` | Linker Guide | wlink directives, segment/order, layout |
| `tools.md` | Tools | wmake, wlib, disassembler, etc. |
| `wccerrs.md` / `wpperrs.md` | C / C++ diagnostic messages | warning/error numbers |
| `wd.md` / `wprof.md` / `wbrw.md` | debugger / profiler / browser | — |
| `ide.md` | IDE | — |
| `som.md` / `ipfc20.md` | SOM / IPF compiler | — |

## Key facts confirmed from these docs (not OW-fork)
* **`#pragma pack` defaults to 1** — "By default, WATCOM C/C++ aligns all
  structures and its fields on a byte boundary... a default value of 1 is
  used" (`cguide.md`, 32-bit Pack Pragmas). Matches the survey finding
  that `-zp1` is byte-inert (== baseline).
* The full 10.0a pragma set (C, not C++-only): `pack`, `alloc_text`,
  `code_seg`, `data_seg`, `intrinsic`, `function`, **`aux`** (auxiliary —
  calling convention / `parm` / `value` / `modify` register clauses),
  options/library. `inline_depth`, `inline_recursion`, `warning`,
  `initialize`, `dump_object_model` are C++-only.
