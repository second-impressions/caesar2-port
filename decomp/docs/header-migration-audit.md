# Header migration audit

Audit date: 2026-05-18

This records the post-migration checks for the Caesar II header split.

## Source include policy

Checked with:

```bash
grep -R '#include "caesar2.h"\|#include "c2_funcs.h"\|#include "entities.h"' -n decomp/src
```

Result: no checked-in `decomp/src/*.c` file includes any of those headers.

Current source include counts:

| Header | Source files |
|---|---:|
| `c2_data.h` | 33 |
| `c2_types.h` | 11 |
| `ail.h` | 1 |
| `smacker.h` | 2 |

Policy:

* Normal source files include `c2_data.h` for generated data externs.
* Files needing shared structs/map helpers include `c2_types.h`.
* `c2_funcs.h` is generated for tooling/experiments only; do not include it broadly.
* `caesar2.h` is a generated compatibility umbrella and is data-only.

## Runtime helper declarations

`c2rt.h` (curated `__STOSB`/`__STOSD` pragmas) was **deleted**: no source
file calls the CRT helpers directly any more.  Watcom 10.0a's fill-loop
recognition lowers constant-bound `for (i...) arr[i] = val;` loops to
`call __STOSB` / `call __STOSD` by itself (replicating the element value
into edx), so the authentic source form is the plain loop — confirmed
verbatim by the Mac PPC build at every former call site.  For reference,
the helper register protocol is: eax = dst, edx = replicated value,
ecx = count (bytes for `__STOSB`, dwords for `__STOSD`), modifies nothing.

## Synthetic static strings

Checked with:

```bash
grep -R '\bs_[A-Za-z0-9_]*\b' -n decomp/src/*.c
```

Result: no `s_*` decompiler string shims remain in source.  The former
`debug.c` shims are now ordinary string literals, matching the likely PS source;
PS.EXE stores their bytes in `_nullarea` and loads offsets to those literals.

## Generated-header idempotence

Checked by running:

```bash
uv run c2 gen-header
```

Result: generated headers are stable after regeneration.

## Verifier result

Checked with:

```bash
uv run c2 decomp-verify --json --no-strict
```

Result:

```text
982 exact / 539 diff / 1521 compared
```
