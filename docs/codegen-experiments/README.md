# Codegen experiments

This directory holds experiment files for the `c2 forge` brute-force
harness (and a few standalone cross-version codegen probes like
`tail-merge-bisect.c`).

## Forge experiments

Each `<slug>.py` defines a module-level `forge = Forge(...)` and the
levers (built-in + custom) to fire.  Run with

```bash
uv run c2 forge run <slug> --jobs $(nproc)
```

See [`docs/forge.md`](../forge.md) for the user guide and `c2 forge
ls-levers` for the built-in lever catalogue.

## Legacy cgex experiments (`_legacy/`)

119 `cgex`-based experiment files live in `_legacy/`.  Their
conclusions are still useful historical record (each top-level
docstring captures what was *learned* about a Watcom codegen quirk),
but they no longer run -- `c2.commands.cgex` was removed when forge
landed.  When porting a finding back to a runnable test, recreate it
as a forge experiment in this directory.

## Standalone codegen probes

Standalone .c test cases used to probe Watcom codegen behaviour across
versions.  Compile in a `watcom-X.Y-dosemu2` container, dump with
`wdis`, compare.

## tail-merge-bisect.c

Five-test-cases-in-one for cross-function tail-merge.  Compile with:

```bash
podman run --rm -v "$PWD/docs/codegen-experiments:/src" \
  localhost/watcom-10.0a-dosemu2 \
  wcc386 -bt=dos -mf -3r -s -d1 -oi tail-merge-bisect.c
```

(rename to an 8.3 filename inside `/tmp` first — Watcom 10.0a's
DOS host can't open long names; we use `tmrg.c` in scratch
directories).

### Cross-version code-size results (2026-04-27)

| Version          | Code size | Tail-merge? |
|------------------|-----------|-------------|
| 9.01d            | 127       | **yes**     |
| 9.01e            | 127       | **yes**     |
| 9.5              | 127       | **yes**     |
| 9.5a             | 127       | **yes**     |
| 9.5b             | 127       | **yes**     |
| 9.5c             | 127       | **yes**     |
| 10.0a            | 127       | **yes**     |
| 10.0b            | 127       | **yes**     |
| 10.5             | 127       | **yes**     |
| 10.6a            | 127       | **yes**     |
| 11.0             | 127       | **yes**     |
| **11.0b**        | 158       | **NO** (default off) |
| **11.0c**        | 158       | **NO** (default off) |
| **OW v1.0 binary**  | 158    | **NO** (inherits 11.0c) |
| **OW v2 master** | 124       | **yes** (re-enabled) |

The optimisation was present in every Watcom from 9.01d through
11.0, **default-disabled** in 11.0b/11.0c (per the 11.0b changelog
entry below), and **re-enabled by default** in the Open Watcom v2
community fork.  Open Watcom 1.0 (the *first* open-source release,
2003-02) was based on 11.0c source and inherits its disabled
default — verified by downloading `c_doswin.zip` from
`openwatcom.org/ftp/archive/zips-1.0/` and running its `wcc386.exe`
through the dosemu2 host of the 11.0c container; same 158-byte
output, no `-o<letter>` flag combination restores tail-merge.

### Source of truth: `bld/cg/c/optcom.c` in OW source

The 11.0c changelog says (in its accumulated 11.0b/c notes):

> **B**  added a compiler switch to disable the "common epilogue"
> optimization.

"Common epilogue" is Sybase's name for what we've been calling
cross-function tail-merge.  The algorithm lives in
`bld/cg/c/optcom.c` of every Open Watcom source release.

**Reference checkout**: `~/git/open-watcom/open-watcom-v2`
(local, current master).  Verified algorithmically identical to
the OW 1.0 source release `open_watcom_1.0.0-src.zip`: only
whitespace + `bool` cleanup + `OC_NORET` case added.

The OW v1.0 *binary* does **not** behave like the source suggests
it should — same as 11.0c, no tail-merge.  Something in the
11.0c-era build pipeline disabled the path; that something is not
in the open-source files we have access to.  The OW v2 binary
behaves like the source again, so somewhere between 1.0 and v2
the community removed whatever build-time gate Sybase had in
place (or the Sybase open-source dump deliberately published the
un-gated source while the Sybase commercial binary kept the gate).

Key functions:

  * `ComTail(list, ins)`     — find a common tail to share between
     two instruction streams that converge on `ins`.
  * `ComCode(jmp)`           — try common-code merge for a `JMP`.
  * `TraceCommon(lbl_ins)`   — driver: walk every reference to a
     label and call `ComCode` on each.
  * `FindCommon` / `CommonInstr` — walk back through both
     streams comparing instructions for mergeability.
  * `JustMoveLabel` / `TransformJumps` — the actual rewriting.

Key gating conditions in `ComTail` (line 245–247 of OW v2):

```c
if( OptForSize < 25 )
    optreturn( false );
if( max.save <= OptInsSize( OC_JMP, OC_DEST_NEAR ) )
    optreturn( false );
```

  * `OptSize` defaults to **50** in the C front-end (`cdata.c`,
     overridden to 50 in the option-spec default — see
     `bld/cc/c/coptions.c:462` `OPT_ENUM_opt_size_time_default`).
     `-os` pushes it to 100, `-ot` to 0.  Our flags don't include
     either, so the size weight is 50, which clears the `>= 25`
     bar.
  * The second condition refuses to merge if the savings don't
     exceed the cost of the new near-jmp.

`OptPush()` in `bld/cg/c/optins.c` (lines 283/294/304/309 of OW
v2) calls `TraceCommon` / `ComCode` / `ComTail` unconditionally
for each `OC_LABEL` / `OC_JMP` / `OC_RET` / `OC_NORET` it
encounters during instruction-queue processing.  **No global flag
gates the call site** in the open-source code — 11.0b/c must
have gated it via a Sybase-internal `#ifdef` or runtime switch
whose default was flipped to off, and that change did not survive
into the open-source release.

### `-o` flag sweep on 11.0c — nothing re-enables it

Tested every documented `-o<letter>` flag in isolation against
11.0c (default flags `-bt=dos -mf -3r -s -d1` plus the one
being tested):

| Flag | Code size | Notes |
|------|-----------|-------|
| (none) | 158 | baseline, no merge |
| `-oa`/`-ob`/`-oe`/`-of`/`-oh`/`-oi`/`-ok`/`-ol`/`-ol+`/`-om`/`-on`/`-oo`/`-op`/`-or`/`-os`/`-ou`/`-ox`/`-oz` | 158 | unchanged |
| `-oc` | 163 | `NO_CALL_RET_TRANSFORM` adds bytes |
| `-of+` | 211 | forces stack frames |
| `-ot` | 176 | `OptSize=0` adds 18 bytes |

**No combination resurrects the 127-byte tail-merged output.**
Whatever switch Sybase added in 11.0b is either undocumented in
the `-o<letter>` family or default-disabled-only-in-11.0b/c’s
shipped binary.

### How OW v2 compares to 10.0a on the same source

OW v2 master `wcc386` (`open-watcom-v2` Nix package, 2025-11-15
build) emits 124 bytes — 3 bytes *less* than 10.0a:

| Function   | 10.0a | OW v2 | Tail-merged in both? |
|------------|-------|-------|----------------------|
| wrap_alpha |   10  |   10  | n/a                  |
| wrap_beta  |   10  |   10  | n/a                  |
| wrap_gamma |   10  |   10  | n/a                  |
| op_one     |   25  |   25  | yes (canonical)      |
| op_two     |   12  |   12  | **yes** (jmp -> L$1) |
| op_three   |   12  |   12  | **yes** (jmp -> L$1) |
| floppy_op  |   41  |   33  | yes (canonical)      |
| glop_op    |    7  |   12  | **10.0a yes / OW v2 NO** |

The op_one/op_two/op_three trio merges identically.  But for the
floppy_op/glop_op pair, 10.0a fall-throughs glop_op into
floppy_op's tail (7b vs 12b), while OW v2 keeps glop_op
self-contained.  The algorithm is the same; the *cost model* (or
a heuristic threshold) drifted between 1994 and 2026.

### Implication

* **Reading the algorithm**: `~/git/open-watcom/open-watcom-v2/
   bld/cg/c/optcom.c` (≈ 350 lines) is the canonical reference.
   The OW 1.0 source matches it module on whitespace; the
   algorithm has not been materially changed between 1992 and
   today.
* **A second runnable testbed**: OW v2 master `wcc386` does
   most of the merges 10.0a does, with documented divergence on
   the cost-model edge case above.  We can probe it under a
   debugger or with listing files to see *which candidates it
   considers* and *what savings it computes* — then port that
   reasoning back to predict 10.0a's choices.
* **Still need** the cross-version 9.01d … 11.0 container set as
   the *behaviour* oracle.  When source-reading isn't enough
   (cost-model edge cases), we run 10.0a directly.
* **OW v2 is now an option for `c2 oracle`**.  Steps 3 and M5
   of the roadmap can be sped up by adding OW v2 to the
   automated codegen-mutation harness.

The 31-byte difference is exactly the cost of three operations
no longer being fall-through:

```
op_two   : 12 b → 25 b   (+13)
op_three : 12 b → 25 b   (+13)
glop_op  :  7 b → 12 b   (+5)
                        +31 ✓
```

### Where to read the algorithm instead

Since OW source post-dates the removal, options are:

* **Compile-test-only modelling.** Bisect source-level mutations
   against compile-time output across the still-merging 9.01d–11.0
   container set.  This repository is set up for it; the experiment
   in this directory is the seed.
* **Reverse-engineer `wcc386.exe`.**  Sybase shipped the binaries
   stripped — `wdump -d` on every wcc386.exe (DOS LX *and* Win32
   PE32, 9.5c / 10.0a / 11.0c checked) reports `No debugging
   information found`.  The `.debug_pubnames` etc. strings in
   `strings(1)` output are from the compiler's *own* DWARF reader
   (it consumes debug info from input `.obj` files), not symbols
   *for* the compiler.  RE work would be from scratch on a 530 KB
   binary.

Recommended path: keep refining the source-level oracle (Step 3 in
the roadmap) and treat OW 1.0 source only as a reference for
algorithms that didn't change (Rule 16 jmp-encoding, regalloc
heuristics).
