# Delinking third-party blobs out of PS.EXE (`c2 delink`)

PS.EXE statically links three bodies of code we never rebuild from source:
Miles **AIL** (sound), RAD **Smacker** (video), and the Watcom CRT.  For a
*functional* rebuild we need those objects back.  The CRT ships as
`clib3r.lib` in the toolchain image, but AIL and Smacker exist only as
already-linked bytes inside PS.EXE.

`c2 delink` recovers a **relocatable OMF `.obj`** for a chosen module set,
byte-for-byte, so WLINK 10.0a can link it into our `out.exe` exactly like a
freshly-compiled object.

## What "proper delinking" means here

PS.EXE is a fully-linked LE image — there are no object files inside it.
Delinking reconstructs the **relocation table** the linker consumed, turning
the absolute addresses baked into the code back into symbolic references.
The output is *byte-preserving by construction*: code/data bytes are copied
verbatim and relocations are attached at the offsets we recover.  We never
disassemble to re-emit — disassembly is used only as an oracle to *locate*
PC-relative branch sites.

This is deliberately **not** the mnemonic-`.asm` route the repo uses for its
seven hand-written C2 asm modules (`library.asm`, …).  That route
disassembles to WASM mnemonics and reassembles; it is the right tool for
C2's own asm (we want it readable and byte-verified) but the wrong tool for a
proprietary blob we will never read — its `db`-fallback is an admission that
the mnemonic layer is a leaky abstraction over "bytes + relocations", and
hand-written asm like `unsmack.ASM` (jump tables, data-in-code) is exactly
where reassembly silently diverges.

## Where the relocations come from

Two sources, because the LE fixup table is only half the story:

1. **LE fixup table** — every *absolute* address reference: `code -> data`
   (global reads), `code -> code` (jump-table `dd` entries), and any
   `data -> code/data` pointers.  Complete and exact.
2. **A control-flow scan (capstone)** — the *PC-relative* `call`/`jmp`
   (`rel32`) edges that leave a function.  These carry **no** LE fixup (the
   linker resolved them by displacement), so they must be recovered.

### Clusters preserve short branches

Functions are grouped into **clusters** of originally-contiguous bodies
(`end == next.start`).  Each cluster is copied as one verbatim byte run, so
every *intra-cluster* relative branch — including 1-byte `rel8` — is
preserved with no fixup.  Only cross-cluster and external references become
relocations, and those are always `rel32`/absolute (relocatable).  A
cross-cluster `rel8` would be unrelocatable; the tool asserts none exist
(Smacker: 4 clusters, zero cross-cluster `rel8`).

## OMF encoding

`c2/omf.py` is a small 32-bit flat OMF writer (validated against a
wasm-produced reference).  Conventions, mirroring Watcom's own output:

* every fixup is `OFFSET32` (loc = 9); absolute = segment-relative (M=1),
  `call`/`jmp` = self-relative (M=0);
* frame = "determined by target" (method 5) — correct for flat model;
* the additive displacement is folded into the **location content** (the
  bytes already in the LEDATA) and the FIXUPP uses a no-displacement target
  method (4 = segment, 6 = external);
* LEDATA chunked to ≤1024 bytes; FIXUPP data-offset never straddles a chunk.

## Usage

```
c2 delink --group smacker -o decomp/lib/smacker.obj --verify
c2 delink unsmack.ASM -o /tmp/unsmack.obj      # a single TU by name
c2 delink --list                                # predefined groups
```

Output `.obj`s are gitignored (reproducible from PS.EXE, and proprietary).

## Validation (Smacker)

The Smacker delink (57 funcs, 4 clusters, 26 KB `_TEXT`, 584 B `_DATA`,
4 B `_BSS`) is proven correct by:

* **verbatim** — 22 583 non-fixup bytes identical to PS.EXE (0 diff);
* **link** — WLINK 10.0a links it with no OMF/undefined errors;
* **`SMACKOPEN`** — 429/429 instructions match PS.EXE, 76/76 branch targets
  land exactly per layout;
* **all relocations** — 708 `code->data` fixups imply a single consistent
  `_DATA` base, 3 `->BSS` a single `_BSS` base, 42 jump-table `code->code` a
  single `_TEXT` base (a wrong relocation would imply a divergent base), and
  51/51 cross-cluster internal calls retarget exactly.

The `unsmack.ASM` functions show spurious mnemonic diffs under a naive
side-by-side disassembly — a capstone re-sync artifact where relocated
jump-table bytes differ — disproven as real errors by those 42 jump-table
fixups all resolving correctly.

## Shared data: delink co-dependent modules together

PS.EXE reuses memory aggressively.  `unsmack.ASM`'s decoder scratch region
(`simspeed`, ~530 B) is **memory-overlaid** with `qread`'s file read buffer —
one physical buffer, two module owners.  Delinking those modules into
*separate* objects gives each a private copy of the region, silently breaking
whatever relies on the sharing (the Smacker decoder produced a degenerate
2-colour frame until the two were delinked together).

**Rule: modules that share a data region must be delinked into ONE object**
(`c2 delink --group smacker rfile.ASM qread`), or the region must be exported
once and imported.  The `--verify` verbatim check does *not* catch this — it
only checks each object's own bytes, not cross-object aliasing.

## Data-in-code jump tables mis-attributed to a trailing CRT symbol

`ailssa.asm` builds its DIG-copy / mixer dispatch as **jump tables that live
in the code image** (`call cs:[eax*4 + TABLE]`, 256 `_DC_*`/`_M_*` pointers at
`0x7606c`).  These tables carry no `-d1` symbol, so the symbol map attributes
their bytes to the *preceding* symbol — here a 5-byte CRT `remove` `jmp`
thunk.  Because `remove` is CRT (externed, not emitted), a naïve delink drops
the whole table **and** externs the reference to `remove+N` (clib3r) → at
runtime the dispatch does `call cs:[garbage]` and jumps to a wild address
(seen as a DOS/4GW `GRP5:Illegal call` / `DYNX86: can't run code in this
page`).  This is exactly what broke the Miles **AIL digital-audio driver**:
the SB16.DIG driver loaded fine, but the first timer-serviced DMA copy
dispatched through the dropped table and crashed.

**Fix** (`_delink`, "data-in-code jump tables"): an absolute `code->code`
fixup sited in included code whose target is *not* in any function cluster
but lives in the code image owned by a **non-module symbol at a mid-symbol
offset** is a data-in-code table.  Pull in `[target, owner_end)` as a
verbatim `_TEXT` region (skipped by the relative-branch scan since it isn't
code); the normal fixup passes then relocate both the reference and the
table's own entries.  Surfaced as `N code jump-table(s)` in the delink
summary.  This is the code-segment analogue of the data-side "inline unnamed
module data trailing a CRT symbol" fix.

**Debugging note:** the crash was localised with a `--enable-debug=heavy`
DOSBox-X build patched to (a) enable the per-instruction ring log from
startup and (b) on the `GRP5:Illegal call`, dump CS:EIP + a memory window and
flush the 20 000-instruction ring — which pinned the faulting
`call cs:[eax*4 + 0x1D3101]` and its garbage table slot.  The nixpkgs
DOSBox-X ships **no** debugger and **no** gdb stub, so a local override build
is required for this.

## Validated end-to-end: the Smacker player

`tools/smk-player/` links the delinked Smacker (+ its RAD file I/O) into a
DOS/4GW program that **decodes real `.SMK` videos** — the ultimate proof the
object is correct, since the 13 KB self-modifying `unsmack.ASM` decompressor
would produce garbage from any wrong relocation.  It decodes to full-colour
frames (see `docs/smk-delink-frame.png`).  `tools/smk-player/build.sh` builds
it; `tools/smk-player/README.md` documents the run and the shared-`simspeed`
finding.

## Reconstructed vendor archives (`--split --libs`)

`c2 delink --group av --split --libs -o decomp/lib/av` additionally packs
the per-module objects into the RECONSTRUCTED 1995 link inputs via wlib:

* **`ail.lib`** — Miles AIL (ail, ailss, ailsfile, ailxmidi, ailxdig,
  aildebug, dllload, aila, ailssa — 9 modules);
* **`smack.lib`** — RAD Smacker SDK (smackinp, sndail, sndnull, unsmack,
  rfile, qread — 6 modules).

They behave as real libraries: the smk-player links `LIBRARY ail.lib,
smack.lib` exactly like a 1995 licensee program and decodes cinematics
identically.

**The 1995 link, reconstructed (2026-07-10):** PS's `-d1` module list
IS the link input record — modules 0–45 are the explicit FILE objects
(the game TUs, the eight asm modules, **plus `dllload.obj` and
`sndail.obj` as loose SDK glue**), and modules 46+ are the library
pulls in wlink's resolution order.  `c2 rebuild` now emits exactly that
shape — 44 FILE entries + `LIBRARY ail.lib, smack.lib, clib3r.lib` —
and wlink 10.0a's own resolution regenerates PS's entire CRT/AV
interleaving: **0 cross-module order breaks** (1 within-module: a
1-byte empty-function fold).  No CRT extraction, no synthetic ordering.

Two delink details were load-bearing for that result:

* the RAD assembly modules (`qread`/`unsmack`/`rfile`) occupy their OWN
  code segments at PS's image tail, in the order (qread, unsmack,
  rfile) — NOT their pull order — so the original objects must each
  have declared all three segments in one canonical order (a shared
  assembler include).  The delinker reproduces both the segment split
  (`_SEGMENT_NAME_OVERRIDES`) and the canonical declaration
  (`_SEGMENT_CANON`: each RAD object declares all three, own filled,
  others empty SEGDEFs).
* `palet.obj` (module 64) was a Smacker SDK library member — consistent
  with its MASM reg-reg direction bits — and is packed into the
  reconstructed `smack.lib`.

(An earlier note here claimed library linking "defers placement" — that
was an artifact of a mixed test that FILE'd the CRT objects while
lib-resolving only the AV modules.)

## Split mode: one object per original module (`--split`)

`c2 delink --group av --split -o <dir>` emits **one `.obj` per original
module** (av: 15 objects) instead of one merged blob, mirroring the
1995 link's separate library objects.  The analysis stays set-wide;
every unnamed shared region is emitted ONCE in its owning module's
object and referenced cross-module through exported anchors — the
region's named symbol where the set has one, else a synthetic
`__dlk_[CDX]<offset>` label — so the shared-`simspeed`-class guarantees
hold across split objects by construction.  Split objects are what let
the rebuild interleave modules in PS.EXE's original link order (merged
blobs place contiguously and can never reproduce PS's game/CRT/AV
interleaving).  In the resulting exe the two modes are byte-equivalent
per function; only layout differs.

## Integration: `c2 rebuild` (DONE, 2026-07-10)

`c2 rebuild` links the delinked AV modules (split, in PS module order)
with every recovered game TU, the eight hand-written asm modules, and
`clib3r.lib` into a runnable, DOS/4GW-Professional-bound
**`build/PS.EXE`** — verified to boot to the title screen, and
auto-compared per code symbol against `data/PS.EXE` on every build
(av-delink: 517/517 byte-exact).  Wiring notes:

* `RADMALLOC` / `RADFREE` — defined in `decomp/src/smacker.c` (game
  wrapper); the delinked object's externs resolve against them.
* The data-only scaffold TUs of delinked modules (`smackinp.c`,
  `sndail.c`, `sndnull.c`) are EXCLUDED from the rebuild link — the
  real code AND data come from `av.obj`, which now also emits **data
  PUBDEFs** (non-static data symbols + the `_sndinit` allowlist the
  dia_*.asm renderers reach into).
* There is **no auto-stubbing** in the rebuild: an unresolved extern is
  a hard wlink error (the verifier's `stubs.c` machinery remains for
  `decomp-verify` only).
