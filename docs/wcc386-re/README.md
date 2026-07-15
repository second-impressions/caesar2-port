# Reverse-engineering the Watcom 10.0a `wcc386` binary

> **Goal**: *reason about register-allocation tie-breaks* in PS.EXE from the
> **actual compiler that built it** — Watcom 10.0a, reverse-engineered
> directly from `wcc386-10.0a.exe` (the open-source code generator is a
> later version, so the binary is the reference for codegen specifics).

This directory is the reproducible toolkit + findings.  TL;DR of the first
real result:

* **The 10.0a integer register order is `DoubleRegs = EAX, EDX, EBX, ECX,
  ESI, EDI, EBP`** (EBX before ECX).  Established three independent ways
  below (binary table + byte-pattern search + behaviour).

> **Where the tooling lives.**  This directory holds the *static* binary
> cracker (`wcc_image.py`), the dev shell (`flake.nix`), and the findings
> (`README.md` + the sibling `.md` notes).  The *dynamic* instrumentation —
> the `-trace` instrumented `wcc386` image, the QEMU hook harness, and the
> reference-model scripts — lives in a **separate sibling repo**,
> `~/git/ReverseEngineering/watcom10.0a`.  Any path in these docs of the
> form `qemu-harness/…`, `tools/{patch_trace,rover_divergence,reglists,
> regalloc_*,trace_parse}.py`, or `scripts/{build-trace-image,dump_analyze}.*`
> is relative to **that** repo, not this one.

---

## 1. The binary format (why standard loaders fail)

`wcc386-10.0a.exe` (528 KB) is a **Phar Lap TNT bound executable**:

```
file 0x000000  MZ real-mode stub
file 0x000C08  LX (OS/2) bootstrap loader  ~4 KB code + bss   <- rizin/Ghidra stop here
file 0x001000  ── flat 32-bit compiler image (uncompressed) ──
   ...code...   file 0x1000 .. ~0x6F000      (va 0x7758 .. ~0x75758)
   ...rodata/strings/globals... file ~0x6F000 .. EOF (0x842B4)
```

rizin's LX loader and Ghidra's OS/2 loader only map the **4 KB bootstrap**
and miss the entire compiler.  The real payload is a *headerless* flat image
that the TNT extender memory-maps.  `"TNT"` is literally embedded at file
`0x1F109`.

### The coordinate system

The whole flat image is one contiguous, **uncompressed** blob (entropy ~6.0).
The single fact you need:

```
virtual_address = file_offset + 0x6758            (DELTA = 0x6758)
```

How `DELTA` was pinned (see `wcc_image.py`):

1. All 494 absolute `[disp32]` data operands in the code cluster tightly in
   one va range → there is a single flat data segment.
2. Code immediates that are data pointers, minus the file offset of the
   string they point at, vote overwhelmingly for `0x6758`.  The resulting
   `imm → string` mappings are perfect semantic hits ("Out of memory",
   "$$TYPES", source paths like `g:\bld\dwarf\dw\c\dwrefer.c`).

> **Bonus property**: for `call rel32`, the *file offset* of the target is
> `next_file_off + rel32` **independent of `DELTA`** (the base cancels).  So
> the file itself is a valid coordinate system for the call graph — you can
> recover ~2200 functions with a recursive capstone sweep before ever loading
> Ghidra.

```bash
python wcc_image.py wcc386-10.0a.exe          # self-test + register tables
python wcc_image.py wcc386-10.0a.exe --regtables
python wcc_image.py wcc386-10.0a.exe --ghidra-base
```

## 2. Getting a decompiler on it (Ghidra)

Load the **whole exe** as a *raw binary* at base `0x6758` so every baked-in
address resolves (`file 0 → addr 0x6758`; the MZ/LX stub bytes land at
`0x6758..0x7758` and are simply ignored — real code is `va ≥ 0x7758`):

```bash
analyzeHeadless <projdir> wcc386_10_0a \
  -import wcc386-10.0a.exe \
  -loader BinaryLoader -loader-baseAddr 0x6758 \
  -processor x86:LE:32:default
```

This yields **1916 functions** + the decompiler.  The project's `ghidra-cli`
can then drive it:

```bash
ghidra-cli function list --count --project wcc386_10_0a --program wcc386-10.0a.bin
ghidra-cli decompile <addr>   --project wcc386_10_0a --program wcc386-10.0a.bin
```

(The Ghidra project `wcc386_10_0a` already exists in the ghidra-cli project
dir from this session.)

## 3. Anchoring: how to find a specific cg function with no symbols

The compiler ships **stripped of cg/ assertions** (only the DWARF library
kept its `__FILE__` strings), so you can't grep for `regalloc.c`.  Working
anchors, best first:

1. **Register-set tables in `.data`** (the anchor that cracked this).  They
   are `EMPTY(0)`-terminated arrays of `hw_reg_set` words.  The 386
   `hw_reg_set` is a **single 32-bit word**: `_0 = part0 | (part1<<16)`
   (`EAX=0x01000003`, `EDX=0x080000C0`, `EBX=0x0200000C`, `ECX=0x04000030`,
   …).  **Caveat:** the 2003 OW V2 source added MMX/XMM register bits which
   shift this layout — that is why a naïve port of the 2003 byte values
   *fails* to match, and why you must rediscover the encoding empirically
   (`find_regtables` does the structural search: small recurring "register
   vocabulary" dwords in `EMPTY`-terminated runs).
2. **Behavioral differential** (§4) — compile a probe with the real toolchain
   (podman `localhost/watcom-10.0a-dosemu2`) and read the codegen.  This is
   the *ground truth* and needs no symbol recovery at all.
3. **`call reg` sites** — the whole compiler has only **11** register-indirect
   call sites, so callback-driven code (sorts/dispatchers) is easy to
   enumerate.
4. **Structural / numeric fingerprints** stable across 1995→2003 (e.g. a
   sort's gap sequence, a magic cost constant) for functions with no data
   anchor.

## 4. The first result: 10.0a integer register order is `EAX,EDX,EBX,ECX,…`

### Static evidence (the binary's own tables)

`python wcc_image.py … --regtables` extracts, among others:

| va | table | contents |
|----|-------|----------|
| `0x821A8` | **DoubleRegs** (alloc order) | `EAX, EDX, EBX, ECX, ESI, EDI, EBP, ESP` |
| `0x82194` | DoubleParmRegs | `EAX, EDX, EBX, ECX` |
| `0x81FD0` | WordRegs | `AX, DX, BX, CX, SI, DI` |
| `0x81F78` | ByteParmRegs | `AL, AH, DL, DH, BL, BH, CL, CH` |

A byte-pattern search across the **entire** binary finds the
`EAX,EDX,EBX,ECX` order at `0x82194` and `0x821A8` (and no other GP-int
ordering), confirming `DoubleRegs`/`DoubleParmRegs`.

### Behavioral confirmation (the compiler itself)

A value forced to survive calls that zap `EAX`+`EDX` must land in the first
*callee-saved* candidate; 10.0a's table predicts `EBX`:

```c
extern int g2(int, int);
int test(int a) {
    int x = g2(a, 1);   /* EAX; 2-arg call also zaps EDX            */
    g2(0, 0);           /* zaps EAX+EDX -> x needs a callee-saved reg */
    return x + g2(1, 1);
}
```
```
wcc386 -bt=dos -mf -4r -s -d1  →
  push ebx
  ...
  mov  ebx, eax        ;  x -> EBX   (NOT ecx)
  ...
  add  eax, ebx
```

Two tied cross-call values occupy **EBX then ECX**, confirming the full pool
order `EAX, EDX, EBX, ECX, ESI, EDI, EBP`.

### Why it matters for the decomp — and the precise scope (don't overstate it)

The int-allocation list is **DoubleRegs** (`rl.h`: 4-byte ints → `RL_DOUBLE`
→ DoubleRegs).  In 10.0a that list is `EAX,EDX,EBX,ECX,…` — **EBX ranked
above ECX** — so:

* **Rule 28b (EBX↔ECX push count)** *is* governed by this order.  Worked,
  proven example: `totalXpercent` (`a*b/100`) puts the product in **EBX** and
  the IDIV divisor in **ECX**, byte-identical to PS.EXE — which only matches
  because EBX outranks ECX.  (It is byte-exact today.)
* **Rule 28a (ESI↔EDI swap)** is **NOT** an EBX/ECX question — it is governed
  by ESI-before-EDI; the EBX/ECX detail does not touch Rule 28a.
* A second, distinct table **`Reg64Order = EAX,EBX,ESI,EDI,EDX,ECX,EBP`**
  (va `0x81EE8`) is also in the binary but is **not** the int type-class list
  (`rl.h` never maps a 4-byte type to it); it governs other passes.

Reason EBX/ECX ties from `DoubleRegs = EAX,EDX,EBX,ECX,…`.  Full behavioural
proof: `docs/codegen-experiments/regalloc-order.py` (consumption ladder +
Rule-28b + leaf-global cases, all asserted).

## 5. The tie-break mechanism itself (`SortList`/`ShellSort`)

`SortConflicts` sorts the conflict (live-range) list by **descending
`savings`** before `GiveRegister` assigns each in turn.  In the 2003 source
(`bld/cg/c/sortlist.c`) the sort is:

* `SortList → DoSortList`: tries to `_Alloc` a scratch pointer array.
  * **success** (always, for the small conflict lists) → **`ShellSort`**
    (gap sequence `gap = gap/2 + adjust`, `adjust` toggling 0/1) — **not a
    stable sort**.
  * allocation **failure** → recursive **merge sort** (stable) fallback.
* The comparator `ConfBefore` returns **strict** `savings_a > savings_b`, so
  equal-savings conflicts never trigger a swap — but ShellSort's gap>1 passes
  still reorder *equal-savings runs* deterministically as a function of the
  whole pre-sort list (NOT a stable preserve-order; the gap-passes drag
  elements across equal-rank peers).  This is REPRODUCIBLE offline: the slot
  + conflict sort simulators in `c2/regalloc/shellsort_sim_slots.py` match
  the binary on 232/232 routines (see `docs/slot-swap-survey-2026-06-25.md`).

So a register tie decomposes into two deterministic layers:
1. **Savings sort** decides *who picks first* — equal savings ⇒ **first-use
   order** (the value first used in the instruction stream picks first;
   proven in `regalloc-tiebreak.py`, corpus-validated by `change_citizen_targs`).
2. **Candidate iteration** decides *which register* the winner takes —
   first non-interfering register in `DoubleRegs` = **EAX,EDX,EBX,ECX,…**
   scored by `CountRegMoves`.

**Version caveat:** whether 10.0a's `SortConflicts` calls the generic
`SortList` (vs an inlined sort) still needs to be confirmed against the
binary — the compiler has only 11 `call reg` sites, none an obvious generic
sort, so 10.0a may inline the comparator.  This is the next thing to read in
the Ghidra decompiler (use the `DoubleRegs` xref neighbourhood as the entry
into the allocator).  Verify `sortlist.c` behaviour against the binary rather
than assuming the source matches byte-for-byte.

## 5b. The callee-save "bonus" is moot; static trace of `GiveBestReg` is blocked

**Callee-save bonus — settled behaviourally.**  There is no caller/callee-save
bias in `CountRegMoves` that matters: under `__watcall` the no-push registers
(EAX + the used parameter registers) are *exactly* the prefix `EAX,EDX,EBX,ECX`
of DoubleRegs,
so the list order already prefers them — a bonus can never reorder a prefix
preference.  Probe (`regalloc-order.py::void_xcall`): a `void(void)` cross-call
value has **no** free register (EAX is call-clobbered) and the allocator takes
**EDX paying a push** rather than dodging it.  So for tie-break reasoning the
callee-save bonus can be ignored; the determinants are (a) DoubleRegs list
order [proven] and (b) `CountRegMoves` savings + the equal-savings sort.

**The `CalcSavings` cost model is obtained** — the exact savings weights
(`W=10` loop multiplier, `use_save=1`, `load/store_cost=2`,
`push+pop=2`, …) come from the code-generator source
(`regsave.c`/`i86regsv.c`/`savings.h`) and are **confirmed against the 10.0a
binary's behaviour to the exact constant**: a value used once per loop iteration
outranks a straight-line value up to exactly 10 uses (depth 1) / 100 (depth 2)
— `regalloc-cost.py`, `ALL PROOFS PASS`.  See `regalloc-model.md §2`.

**Byte-level navigation into `GiveBestReg` in the image is still blocked** (not
needed for the model).  The register/const tables at `0x808E0–0x825C4` have
**no findable absolute reference** in code or data (every apparent hit is a
misaligned-read coincidence — e.g. the "WordRegs+0x18" hit is the displacement
bytes of a `call rel32`); they're reached via load-time-relocated pointers.
Reading the allocator bytes directly would need the Phar Lap TNT data-segment
relocation table parsed first — a separate task, but the cost model and the full
behavioural model are already complete without it.

## 6. Files

| file | what |
|------|------|
| `wcc_image.py` | format crack, base solver, register-table locator (run it) |
| `flake.nix`    | `nix develop` shell: rizin, radare2, python+capstone, ghidra, podman |
| `README.md`    | this document |
| *(external)*   | the `-trace` image, `qemu-harness/`, and `tools/*.py` reference model live in the sibling `~/git/ReverseEngineering/watcom10.0a` repo |

## 7. Reproduce from zero

```bash
cd docs/wcc386-re
nix develop                      # or: nix shell nixpkgs#{rizin,ghidra}
python wcc_image.py /path/to/wcc386-10.0a.exe          # see §1/§4
# Ghidra decompiler:
analyzeHeadless /tmp/proj wcc386_10_0a -import /path/to/wcc386-10.0a.exe \
  -loader BinaryLoader -loader-baseAddr 0x6758 -processor x86:LE:32:default
# Behavioral ground truth:
printf '%s\n' 'extern int g2(int,int);' \
  'int t(int a){int x=g2(a,1);g2(0,0);return x+g2(1,1);}' > t.c
podman run --rm -v "$PWD:/src" localhost/watcom-10.0a-dosemu2 \
  "wcc386 -bt=dos -mf -4r -s -d1 t.c"        # x -> EBX
```
