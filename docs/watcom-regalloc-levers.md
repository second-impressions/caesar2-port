# Watcom 10.0a Regalloc Levers — A Practical Guide

> **Audience**: agents and humans working on byte-exact decompilation
> who hit a register-allocation diff and need to know *which lever
> to pull*.

> **Scope**: practical source-level and pragma levers that actually
> move codegen under Watcom C/C++ 10.0a with our default cflags
> (`-bt=dos -mf -4r -s`).  Empirically verified — anything that
> doesn't change bytes is in § [Anti-Levers](#anti-levers) so you
> don't waste time on it.

> **Companion docs**:
>
> * `docs/watcom-regalloc-research.md` — the theory: how `CalcSavings`,
>   `GiveBestReg`, `CountRegMoves`, `TooGreedy`, `WorthProlog` actually
>   work in `bld/cg/c/regalloc.c`.  Read this when you want to
>   understand *why* a lever works.
> * `docs/watcom-codegen-patterns.md` — the catalogue: 71 numbered
>   rules with discovery commit, asm shape, and source fix.  This guide
>   is an index *into* that catalogue.
> * `AGENTS.md` § "Pragma / Prologue Hints" — the `c2 pragma-hints`
>   detector: scans PS-vs-RC prologue divergence and points you at the
>   relevant lever.

---

## 1. Decision Tree — "I see this diff, what do I try?"

Start with `c2 decomp-verify <file> -f <fn> -v --no-strict` and look
at the header.

```
PS callee-saves: ebx ecx edx esi
RC callee-saves: ebx ecx edx        (divergent)
Prologue hint: ...                  ← read this; it picks the lever
Rule hints: 2x Rule 28b; 19 unexplained
Tail-merge: Tail-merge donor: ...
Sig mismatch: declared takes N arg(s), inferred M
```

The `Prologue hint:` and `Rule hints:` lines tell you which category
of fix applies.  This guide maps each category to the concrete lever.

### 1.1 Prologue push-set differs (`c2 pragma-hints`)

| Symptom (`category` from `c2 pragma-hints`) | Lever |
|---------------------------------------------|-------|
| `ps_loadds` — PS pushes DS | § 2.1 `#pragma aux NAME __loadds;` |
| `ps_seg_preserved` — PS pushes FS/GS/ES | § 2.2 segment-reg pragma |
| `ps_eax_preserved` — PS pushes EAX (and body **doesn't** read `[esp]`) | § 2.3 `modify exact [...]` omitting eax |
| `ps_stack_spill` — PS pushes EAX (and body **does** read `[esp]`) | § 3.1 Rule 24a spill-via-local |
| `ps_extra_callee_save` — PS uses one more callee-save | § 3.2 widen a local / cache an expression |
| `rc_extra_callee_save` — RC uses one more callee-save | § 3.3 simplify / inline / narrow |
| `callee_save_swap` — one-for-one swap | § 4.1 Rule 28a — first-use order (reorder which value is used first) |
| `structural_divergence` — ≥ 2 regs differ on a side | § 5 read PS asm carefully; not a single-lever fix |
| `prologue_order` — same set, different push order | § 4.3 IL emission order |

### 1.2 Body diff with rule hints

| Rule hint emitted | Lever |
|-------------------|-------|
| Rule 4 — `<` vs `>` operand order | rewrite cmp to match PS's operand order |
| Rule 8 / 23 — `char` signedness | use `signed char` only at fields PS reads via `movsx` |
| Rule 12 — looks like an int literal | it's a data-pointer fixup; use the right symbol |
| Rule 14 — bare `ret`, no EAX preload | return type is `void` |
| Rule 16 — short-vs-near jmp | rearrange so the branch fits in 8 bits |
| Rule 17 — flag-mask split-RMW | split or fuse the RMW per PS |
| Rule 19 — `char` vs `int` parameter spill | match the param width PS uses |
| Rule 22 — stub signature mismatch | fix the callee's declared signature |
| Rule 28a — callee-save swap (esi↔edi, edx↔ebx, …) | **reorder which value is used first** (equal-savings tie-break = first-use order). Reorderable expr → fixable (e.g. `change_citizen_targs`); CSE-hoisted globals in fixed order → residue. See Rule 28a + `docs/wcc386-re/regalloc-model.md` |
| Rule 28b — asymmetric callee-save count | § 3.2 / § 3.3 |
| Rule 42 — tail-merge donor | decompile the donor first; § 4.4 |
| Rule 44 — spurious `and ecx, 0xff` | int-promotion of byte AND; match the type |
| Rule 49b — `& 0xff` vs `(unsigned char)` zext idiom | choose the spelling PS uses |
| Rule 50 — `for` vs `while` for global-counter loops | match the source loop style |
| Rule 59 — pass-through params reserve EAX/EDX | widen the function to take the pass-through params |
| Rule 65 — equal-savings tie | first-use order (reorder which value is used first) |
| Rule 78 — 5-insn ptr-save-deref byte-copy idiom | name BOTH the pre-increment ptr save and the dest address as locals |

The rule hints are emitted automatically by `c2/commands/rule_hints.py`.

---

## 2. Pragma Levers — `#pragma aux`

Watcom's `#pragma aux NAME` lets you override the default
calling-convention `aux_info` for a single function.  The
relevant clauses for regalloc:

### 2.1 `__loadds` — `push ds; mov ds, DGROUP; ...; pop ds`

**When**: PS pushes `ds` in the prologue.  Usually a DOS/DPMI
callback registered with a non-flat library (e.g. mouse driver
via int 0x33).  See worked example in
`decomp/src/lib32.c::click_handler`.

```c
#pragma aux NAME __loadds;
void __far NAME(...);
```

**Not** `__interrupt`: that adds the full `pushal; ...; iret`
envelope, which is wrong for far-call callbacks that use `retf`.

Mechanism: `bld/cc/c/cprag86.c` sets `LOAD_DS_ON_ENTRY` in
`aux_info.class`; `bld/cg/intel/c/i86reg.c::CallState` triggers
the `push ds; call __GETDS; ...; pop ds` envelope at prolog/epilog
emission.

### 2.2 Segment-register preservation — `modify exact [...]`

**When**: PS pushes a segreg other than DS (rare).  Need to
exclude the seg from the modify set so it ends up in `save`.

```c
#pragma aux NAME modify exact [eax edx ebx ecx];
```

The `exact` keyword keeps segregs in `save` even under flat memory
model (where `FLOATING_DS` etc. would normally evict them).

### 2.3 `modify [...]` and `modify exact [...]` — register save set

**When (true `modify [eax]`)**: PS pushes everything *including*
EAX.  The function preserves EAX across the call (caller relies on
it).  Body must **not** read `[esp]` (otherwise it's stack-spill,
not preservation).  Rare to non-existent in C2.

```c
#pragma aux NAME modify exact [edx ebx ecx];
/* save = HW_FULL - {edx, ebx, ecx} → EAX, ESI, EDI, EBP all preserved */
```

`exact` is required when the omitted register (EAX) is also a
parameter or return reg — otherwise `MustSaveRegs` strips it
automatically and you don't get the `push eax`.

**When NOT to use**: when PS preserves the standard __watcall set
(EBX/ECX/EDX/ESI) but RC doesn't — that's *not* a pragma issue.
Default `-4r` __watcall already preserves all GP regs the function
modifies (verified empirically via `c2 oracle compile`).  The
mismatch is a regalloc-shape problem; see § 3.

**`modify` vs `modify exact`**: `modify exact` additionally
preserves segment registers (DS/ES/FS/GS); plain `modify` lets
Watcom freely scribble them under flat models.  Use plain `modify`
unless you genuinely need segreg preservation.

Mechanism: `bld/cc/c/cprag86.c::GetSaveInfo` sets `aux_info.save =
HW_FULL - {floating segs} - modlist`.  Then
`bld/cg/intel/c/i86reg.c::CallState` does `state.modify = HW_FULL
- aux.save` and `MustSaveRegs` returns `HW_FULL - state.modify -
parm.used - return_reg`.  See `docs/watcom-regalloc-research.md`
§ 7 for the live-range math.

### 2.4 `parm [...]` — custom parameter register set

**When**: a callback whose caller hands parameters via a non-
default register order (e.g. real-mode DOS handlers).

```c
#pragma aux NAME parm [eax] [ebx] [ecx] [edx] [esi] [edi];
```

The 16-bit register names (`ax`, `bx`, ...) for 16-bit parameters
**don't** behave as expected in 32-bit mode under our cflags;
they're documented in OW but practice diverges.  Reach for this
only with disassembly evidence.

### 2.5 Other pragma clauses we've used or considered

| Clause | Effect | Used in C2? |
|--------|--------|-------------|
| `aborts` | function never returns; tail-call optimisation | only via ImportCaesar2.java noreturn fixups |
| `nomemory` | function doesn't read/write memory (CSE hint) | no — high false-positive risk |
| `__cdecl` / `__stdcall` / `__pascal` | non-watcall conv | no; everything in C2 is __watcall |
| `__far16` / `__based` / `__segment` | non-flat pointers | no; flat 32-bit DOS/4GW only |
| `__saveregs` | save *all* regs (interrupt-like) | no (use `modify exact []`) |

The reason `aborts` isn't sprinkled in source is that
ImportCaesar2.java applies it via Ghidra noreturn flags during
import, so the generated `symbols.json` and downstream tooling
already know which functions don't return.  See AGENTS.md
§ "Project Setup".

---

## 3. Source-Shape Levers (non-pragma)

These are the levers that actually fire on the majority of medium-
severity prologue divergences.

### 3.1 Rule 24a — Spill-via-local (stack slot allocation)

**When**: PS does `push eax; mov reg, [esp]; ...; add esp, 4` —
allocates a 4-byte stack slot for a local.  Detector category
`ps_stack_spill`.

**Lever**: add a named local in the C source for a value Watcom
will decide to spill rather than enregister.  Typical candidates:

* A pointer that survives across many sub-expressions or a call.
* A value live across a function call (forcing Watcom to either
  spill or enregister in a callee-save).

```c
void foo(int x) {
    int saved_x = x;          /* named local — Watcom may spill */
    some_call();              /* x clobbered if not preserved */
    use(saved_x);
}
```

See Rule 24a in `docs/watcom-codegen-patterns.md` for the auto-
detector that recognises the spill pattern in `decomp-verify -v`.

### 3.2 Type widening — `unsigned char` → `int`

**When**: detector category `ps_extra_callee_save`.  PS uses one
more callee-save (typically ESI) than recomp.

> **DIAGNOSE FIRST (Rule 89).** `ps_extra_callee_save` is
> heterogeneous — read the PS body and confirm the extra register's
> actual cause before reaching for type-widening: (a) value live
> **across a call/idiv** → EAX-boundary, reshape the crossing;
> (b) byte reg materialising a literal (`xor bl,bl; mov [m],bl`) →
> store-zero idiom (Rule 8/23/49), *not* this lever; (c) the value
> crosses nothing and the two sides picked different regs → FIRST-USE
> order (Rule 28a): reorder which competing value is used first.  Type
> widening below only applies to the int-typed-conflict flavour.

**Mechanism**: an `int` local creates an int-typed conflict in
the allocator's interference graph.  Int conflicts prefer to live
in `DoubleRegs` (`EAX, EDX, EBX, ECX, ESI, EDI, EBP` — see Rule 89),
where ESI/EDI are
callee-save.  A `unsigned char` local stays as a byte temp in
`ByteRegs` (AL, AH, DL, DH, BL, BH, CL, CH) where AL/AH/DL/DH/BL/BH
have caller-save homes and CL/CH share ECX (also caller-save in
function calls under -4r).

**Worked example** — `push_node_value` (web.c) hit ~190 b residue
until `unsigned char building` was widened to `int building`.
With int, Watcom emitted `mov ch, [..]; and ch, 0x80; movzx esi,
ch` (the canonical "byte AND, then zext into ESI" pattern).  See
Rule 70.

### 3.3 Simplification — drop a cached local

**When**: detector category `rc_extra_callee_save`.  RC uses one
more callee-save than PS.

> **DIAGNOSE FIRST (Rule 89).** If the extra register holds a value
> WE keep live **across a call/idiv** that PS didn't, this is the
> EAX-boundary: the fix is to stop crossing the clobber (inline the
> value at its use sites, or move the use *before* the call) — which
> the lever below does.  If instead the value crosses nothing and the
> two sides just picked different regs, it's a FIRST-USE-order case
> (Rule 28a): reorder which competing value is used first, not this lever.

**Lever**: PS source kept the value as a repeated memory
expression; recomp source cached it into a local.  Remove the
local:

```c
/* Before — recomp wins ESI, PS doesn't */
int row_base = (char *)map + y * stride;
for (...) use(*(int *)row_base);
for (...) use(((short *)row_base)[k]);

/* After — match PS */
for (...) use(*(int *)((char *)map + y * stride));
for (...) use(((short *)((char *)map + y * stride))[k]);
```

The repeated long expression looks ugly but it's what PS source
actually wrote (or its CSE pass produced).  Cross-reference Rule
63 (cached row pointer) for a worked discussion.

### 3.4 Named local for spill / shift / live-range pinning

* **Rule 24a** (spill swap): name a temp to force Watcom to give
  it a stack slot.
* **Rule 24b** (shift-in-place vs shift-copy): name a temp to
  pick between `shl r, k` (in-place) and `mov r2, r1; shl r2, k`
  (copy then shift).
* **Rule 24c** (live-range pinning): keep a value alive across a
  region via `var + (s - s)` style neutral expressions.

All three share the same "name a local to change the conflict
graph" mechanism.  See Rule 24 in the catalogue for examples.

### 3.5 Parameter-list mutation (Rules 27, 28b, 43a, 58, 59, 64)

When PS source treats a parameter as a *modifiable local* (mutates
it in-place: `n *= stride; n--;`), Watcom's regalloc keeps the
original and modified values in different registers, biasing the
push-set and downstream codegen.

* **Rule 27** — parm-alias toggle for instruction-pair reorder.
* **Rule 43a** — `width += 2;`-style param mutation triggers dead
  `mov esi, ebx` insertion.
* **Rule 58** — mutate 1st param to keep multiply/divide temps in
  EBX/ECX.
* **Rule 59** — pass-through params reserve EAX/EDX, biasing byte-
  temp into EBX.
* **Rule 64** — mutate an index param to keep the original in EBX
  while the scaled version lives in EAX.

Source-level signature: where C "best practice" would name a new
local (`int scaled = n * stride;`), PS source mutates the param
(`n *= stride;`).  Decomp should match PS's style.

### 3.6 Expression form (Rules 2, 3, 5, 6, 7, 10, 11, …)

Smaller-scale levers that bias single-instruction shapes:

* **Rule 1** — Inline a global twice rather than cache once
  (avoids load-into-callee-save).
* **Rule 7** — Source order of global stores is preserved.
* **Rule 10** — Staged global RMW instead of fused sum.
* **Rule 11** — Pre-increment + cache for loop sentinels.
* **Rule 62** — `x + x` lowers to `lea [x+x]` (3 b); `x << 1`
  lowers to `mov; add` (5 b).  Pick the form PS used.

These don't change *which* register is used; they change the
instruction shape for an already-fixed register choice.  Use when
the prologue and callee-save set match but body bytes still differ.

### 3.7 Control-flow shape (Rules 9, 30, 31, 50, 56)

* **Rule 9** — if-body fall-through layout; equivalent `if (a) X
  else Y` forms swap the Jcc.
* **Rule 30** — sibling-if was actually nested in original source.
* **Rule 31** — `else if (¬outer)` keeps a dead conditional jump.
* **Rule 50** — `for` vs `while` for global-counter loops emits a
  jump-to-bottom-test layout.
* **Rule 56** — `for`-update clause emits expressions in
  declaration order, *after* the body.

When `Rule hints:` flags many of these, the body's control-flow
shape diverges from PS — re-read the disasm and match the source
structure exactly.

---

## 4. Layout / Order Levers

### 4.1 Rule 28 — Whole-function callee-save register swap

PS uses EDI where recomp uses ESI (or vice versa), throughout the
function.  Same allocator savings; the tie is broken by **first-use
order** — the value whose first use comes earlier gets the
higher-priority register.

**Lever:** reorder which of the two competing values is used first
(commute an operand, move a statement) — worked example
`change_citizen_targs`.  See `docs/watcom-codegen-patterns.md`
Rule 28a and `docs/wcc386-re/regalloc-model.md`.  Not reorderable
when the values are CSE-hoisted globals in fixed algorithmic order.

### 4.2 Rule 28b — Asymmetric callee-save count

PS pushes one more (or fewer) callee-save register than recomp — one side
enregisters an extra value.  This is **not one thing**: the `Regalloc:` line
in `decomp-verify -v` classifies it into the model layer and gives the lever.
The sub-cases (each has a lever — codegen is deterministic, so a source shape
that produces PS's bytes always exists; only the *reachability* varies):

1. **Savings (layer 2)** — the extra register holds a value with savings > 2
   (≥3 uses, or 1 loop use ×10) on one side.  Match the use count: inline a
   global read N times vs cache it once (Rule 1).  Usually a one-liner.
2. **EAX-boundary (layer 1)** — the extra value crosses a call/idiv on one
   side only.  Move its use before the clobber (§ above).
3. **Const-store temp in a callee-save (Rule 110)** — the extra register
   holds a materialised constant that is stored to memory (`xor bl,bl;
   mov [m],bl`).  The store *form* is deterministic, NOT a lever: storing `0`
   is always register-materialised, and a nonzero constant is register-cached
   iff referenced ≥2× (`cachecon.c::ConstToTemp`).  The push means that
   const-temp was allocated to a callee-save *here* — a **regalloc**
   (which-register) divergence, not a store-form one.  Match PS's allocation
   (Rule 108 inline-vs-cache, use-order); do **not** chase the store.
4. **Loop hoist/reload (layer 5)** / **capacity spill (layer 6)** — see those
   layers.
5. **Divisor / structural materialisation** — e.g. PS does two `idiv`s sharing
   a divisor in a callee-saved reg where we do one and derive the remainder.
   The lever exists but is per-function source-shape (match PS's division
   structure); the hardest sub-case.

### 4.3 IL emission order (Rule 65)

Watcom's `SortConflicts` sorts by descending `savings`; equal-
equal-savings conflicts are ordered by **first-use position** —
the value first used in the instruction stream picks its register
first.

**Lever:** reorder which of the competing values is used first
(commute an operand, move a statement).  Worked:
`change_citizen_targs`.  Not reorderable when the values are
CSE-hoisted globals in fixed algorithmic order.

### 4.4 Tail-merge donor (Rule 42)

When the function ends with `jmp <imm32>` into another known
function, that target is the **tail-merge donor**: PS factored
out a shared epilogue.  Recomp won't byte-match until the donor's
prologue/epilogue **also** matches.

`c2 decomp-verify -v` prints a `Tail-merge:` hint line; the donor
must be decompiled with the matching push-set first.

### 4.5 Static helper sibling functions (Rule 61)

If PS shipped two near-identical small bodies as separate
functions (e.g. `clear_all_rm` + `clear_all_pm`), recomp source
**must** keep them as separate functions.  Factoring into a
`static inline` helper breaks the byte-match because Watcom emits
different prolog/epilog for the wrapper.

---

## 5. Tooling

The c2 toolchain has detectors and probes for every category
above; reach for the right one before hand-fixing.

| Tool | Use case | Output |
|------|----------|--------|
| `c2 decomp-verify -v -f <fn>` | per-function diff with all hints | compact diff + headers (regalloc, rule hints, tail-merge, sig mismatch, **prologue hint**) |
| `c2 pragma-hints` | project-wide prologue-divergence triage | table sorted by severity + diff bytes |
| `c2 disasm <fn>` | annotated PS disassembly (lines + fixups + branch targets) | text |
| `c2 inferred-sig <fn>` | declared-vs-actual signature mismatch | "takes N args, inferred M" |
| `c2 stubs --donors` | tail-merge donor candidates | leaderboard |
| `c2 row-caches` | row-cache anti-pattern detector | linter output |
| `c2 permute <fn>` | enumerate small mutations + recompile | improvement table |
| `c2 cgex run <slug>` | reusable codegen-experiment harness | per-trial byte-diff |
| `c2 oracle compile` | minimal Watcom 10.0a compile of a snippet | disasm |
| `c2 baseline save` / `check` | project-wide regression guard | summary diff |

### 5.1 Reach-for-it order

When a function diffs:

1. `c2 decomp-verify -v -f <fn> --no-strict` — read the header.
2. If `Prologue hint:` fires → consult § 1.1 table → apply lever.
3. If `Rule hints:` fires → consult § 1.2 table → apply lever.
4. If `Tail-merge:` fires → decompile the donor first.
5. If `Sig mismatch:` fires → fix the stub or the caller's decl.
6. If nothing fires but bytes still differ → `c2 disasm <fn>` and
   compare side-by-side with the recomp asm via `decomp-verify -v
   --full`.
7. Last resort: `c2 permute <fn>` (only on already-faithful bodies;
   see AGENTS.md § Source Permuter for the safety checklist).

---

## 6. Anti-Levers

Things people try that **don't** influence Watcom 10.0a regalloc
under our cflags.  Documented to save time.

| Anti-lever | Why it doesn't work |
|------------|---------------------|
| `register int x` | Watcom 10.0a treats `SC_REGISTER` and `SC_AUTO` identically for codegen (verified via `bld/cc/c/cgen2.c::DoAutoDecl`).  Only effect is rejecting `&x` (`ERR_CANT_TAKE_ADDR_OF_REGISTER`). |
| `auto int x` | Same as plain `int x` — explicit storage class spelling has no codegen impact. |
| `typedef int my_int` | Type aliases don't allocate; same codegen as the underlying type. |
| `extern` spelling on a decl | Storage-class keyword has no codegen impact; *visibility* of the prototype does (Rule 37 implicit-int). |
| `const int x` | Block-scope `const` is just a type qualifier; doesn't bias regalloc. |
| Reordering unrelated locals | Watcom IL emission is based on first-use order, not declaration order, in most cases. |
| Adding `__cdecl` to a void/no-arg helper | The default __watcall already produces correct prolog/epilog; `__cdecl` switches conventions and breaks byte-match. |
| `#pragma intrinsic(memcpy)` globally | Per-function intrinsic recognition fires context-dependently even without the global flag; flipping it globally regresses 7 lib32 functions (verified). |
| `-oi` global flag | Same as above — global intrinsic enabling regresses more than it helps. |
| `-d2` (full debug) | Forces `-od` (no optimisation), produces frame pointers everywhere — wrong for matching `-d1`-built PS.EXE. |

When in doubt, write the lever as a `c2 cgex` experiment and
prove it moves bytes before adopting it.  See
`docs/codegen-experiments/regalloc-levers.py` for the existing
empirical probe.

---

## 7. References

* `docs/watcom-regalloc-research.md` — 800-line theoretical
  treatment with OW v1.0 source citations
* `docs/watcom-codegen-patterns.md` — 71 numbered rules with
  discovery commits, asm shapes, and source fixes
* `docs/permute.md` — source permuter usage + safety checklist
* `decomp/docs/watcom-10.0a-flags.md` — canonical cflag reference
* `c2/commands/pragma_hints.py` — prologue-divergence detector
  module
* `AGENTS.md` § "Pragma / Prologue Hints" — CLI workflow
* OW v1.0 source files most relevant:
  * `bld/cg/c/regalloc.c` — `RegAlloc`, `AssignConflicts`,
    `SortConflicts`, `GiveBestReg`, `CountRegMoves`, `TooGreedy`
  * `bld/cg/c/regsave.c` — `CalcSavings`
  * `bld/cg/h/savcode.h` — shared cost-mode / fix-mode macro
  * `bld/cg/intel/c/i86reg.c` — `CallState`, `MustSaveRegs`,
    `SaveRegs`
  * `bld/cg/intel/c/i86regsv.c` — `WorthProlog`, `ConstSavings`
  * `bld/cg/intel/386/c/386rgtbl.c` — `ByteRegs`, `DoubleRegs`,
    `WordRegs`, `DoubleParmRegs` priority tables
  * `bld/cc/c/cprag86.c` — `#pragma aux ... parm/modify/save`
    parser, especially `GetSaveInfo`
  * `bld/cc/c/coptions.c` — `SetStackConventions`,
    `SetCPU_xR`/`xS`, default `aux_info` setup
  * `bld/cc/c/cfeinfo.c` — `LangInfo`, `FEAuxInfo`, `SAVE_REGS`
    pragma lookup
