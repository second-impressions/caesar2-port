# The Watcom 10.0a register-allocation model (for byte-exact decomp)

This is the **operating model** for influencing every register-allocation diff
in the C2 decomp. It is derived from (a) the register-order tables extracted
from `wcc386-10.0a.exe` (`docs/wcc386-re/`), and (b) a battery of behavioural
experiments against the real toolchain, all reproducible and self-asserting:

| experiment | proves |
|---|---|
| `docs/codegen-experiments/regalloc-order.py` | DoubleRegs order (EBX before ECX); callee-save bonus is moot |
| `docs/codegen-experiments/regalloc-eax-boundary.py` | the EAX↔callee-saved boundary = the EAX-clobber crossing |
| `docs/codegen-experiments/regalloc-tiebreak.py` | savings rank + equal-savings tie-break + move-elim/hard-constraint overrides (historical: framed as "first-use"; the validated mechanism is the name-node pointer, of which first-use is a strong proxy) |
| `docs/codegen-experiments/regalloc-last-use.py` | refines the proxy: for multi-use values it tracks last-use (`UpdateLive` walks backward); the name node is created at the value's last backward encounter |
| `docs/codegen-experiments/regalloc-loops.py` | loop hoist-vs-reload (aliasing) |
| `docs/codegen-experiments/regalloc-spill.py` | register-exhaustion spill + char sub-word order |
| `docs/codegen-experiments/regalloc-cost.py` | exact `CalcSavings` cost model (W=10 loop weight) |

You cannot change the compiler — only the C source. So this model is stated as
**inputs you control → register outcome**, i.e. a lever catalogue.

---

## The model in one picture

A scalar value's register is decided in this order:

```
(0) TYPE        -> picks the register CLASS (which table of candidates)
(1) EAX boundary-> may it live in EAX at all? (only if it never crosses an EAX clobber)
(2) SAVINGS     -> values ranked by descending #uses (loop-weighted)
(3) USE ORDER   -> equal-savings values ranked by FIRST-USE position
(4) OVERRIDES   -> hard constraints + move-elimination beat (2)/(3)
(5) LOOPS       -> what stays enregistered across iterations (aliasing-gated)
(6) CAPACITY    -> 7 GP regs; beyond that, spill to the stack
```

## (6) Register exhaustion / spill  (`regalloc-spill.py`)

**7 GP integer registers** are allocatable: EAX, EDX, EBX, ECX, ESI, EDI, EBP.

* A value **crossing a call** can't use EAX, so **6** cross-call values fit
  (EDX,EBX,ECX,ESI,EDI,EBP); the **7th spills to the stack** (`sub esp,4` per
  spilled value, stored/reloaded around uses).
* Values that **don't cross a call** can use EAX too -> **7** fit, **8th** spills.
* **char** packs into byte sub-registers in DoubleRegs parent order: cross-call
  **DL, DH, BL, BH, CL, CH** (no AL/AH across a call; never SI/DI/BP).
* **Index registers have no special class** — an array index uses the value's
  normally-allocated register (any GP reg works as `[reg*4]`).
* **Spill repair = rematerialization, not always a stack slot.**  When the
  evicted conflict is a *constant* or a *never-written global read*, the
  allocator re-creates it at each use (`xor reg,reg` / `mov reg,[global]`)
  instead of `sub esp,N` + store/reload, because the re-read is the cheaper
  repair.  So a spill can appear as **N extra loads of the same global** rather
  than a frame.  This is the model side of **hard sub-case 6** below and
  catalogue **Rule 111** (detector: `spill_hints.detect_spill_class`).
* **Two-address ops** keep the result in operand-1's register (natural x86).
* `long long`/`__int64` do not exist in this C89 toolchain, so the 64-bit
  QuadReg pair table is never exercised by C2 game code.

Candidates are then handed out from the class table **in table order**, to
values **in the rank order** from (2)→(3), subject to (1) and (4).

---

### The slot-assignment pipeline (the ORDER of stack slots once a value spills)

This is a SEPARATE pipeline from the register conflict sort above.  When the
7th/8th value (or any NEEDS_MEMORY/!HAS_MEMORY/!ALIAS temp) spills, the slot
ORDER is decided later in `AssignTemps` @0x55463:

```
nb1  (front-end temp creation = DECLARATION order; +0x24 = reverse-decl-rank)
 -> BuildNameConflicts sort  (comparator AllocBefore @0x5905b; sort engine
    DoSortList @0x665c4 -> ShellSort @0x66689, UNSTABLE; alloc-fail -> MergeList)
 -> nb2 == nt_pre
 -> AssignTemps sort  (comparator SortCmp_flag2_2b @0x55503; same ShellSort)
 -> nt_post = AllocNewLocal @0x558d4 walk order
 -> SetTempLocation @0x4e6bb  (first-allocated -> highest [esp+N])
```

`ShellSort` is **NOT stable**: for distinct-`+0x24` same-size temps the
`SortCmp_flag2_2b` comparator is *sort-equal* (returns FALSE both ways), so a
stable sort would preserve `nt` order but the ShellSort gap-passes reorder
them anyway.  `+0x24` = reverse-decl-rank -> a decl reorder moves BOTH a
temp's `nb1` position AND its `+0x24` rank together, so decl-order is NOT a
slot lever (proven: 24/24 decl perms of `evolve_water_table` miss PS).  The
levers are temp-set changes (local reuse merges / scope hoists).

Offline simulator `c2/regalloc/shellsort_sim_slots.py` (`predict_nb2` +
`predict_nt_post` + `predict_slot_ptrs`) reproduces the binary's sort: 232/232
`nt_post`, 441/456 `nb2`, and predicts PS's slot order on 130/130 byte-exact
functions.  Full canon + per-comparator keys + per-function status:
`docs/slot-swap-survey-2026-06-25.md`.  Rule 107 in
`docs/watcom-codegen-patterns.md` is the catalogue entry.

---

## (0) TYPE → register class  (`regalloc-order.py`, Module-1 tables)

The C type selects the candidate table (extracted from the binary, va in
parentheses):

| C type | class | priority order |
|---|---|---|
| `char` (any sign) | **ByteRegs** | byte-addressable only: **AL, DL, BL, CL** (never SI/DI/BP/EBP — no 8-bit sub-reg) |
| `short` | **WordRegs** (0x81FD0) | AX, DX, BX, CX, SI, DI  (no BP) |
| `int`, `long`, **pointer** | **DoubleRegs** (0x821A8) | **EAX, EDX, EBX, ECX, ESI, EDI, EBP** |
| `long long` (64-bit) | **QuadReg** (0x821CC) pairs | EDX:EAX, ECX:EBX, ECX:EAX, ECX:ESI, EDX:EBX, EDI:EAX, … |
| param-passing variant | **DoubleParmRegs** (0x82194) | EAX, EDX, EBX, ECX |

> **Lever:** changing a local's width/pointer-ness changes the candidate set.
> A `char` value can *never* land in ESI/EDI/EBP; promoting to `int` lets it.
> This is why `char` vs `int` choices cascade into different push sets.

The int allocation list is **DoubleRegs = `EAX, EDX, EBX, ECX, ESI, EDI, EBP`**
(EBX before ECX; va 0x821A8 in the binary).

## (1) The EAX boundary  (`regalloc-eax-boundary.py`)

A value lives in **EAX iff its live range never crosses an EAX-clobbering
instruction** — a `call`, or `mul`/`div`/`idiv`. Proven necessary *and*
sufficient: identical source + identical call, the value flips EAX→callee-saved
iff its range spans the call. **No economics, `register` keyword, or register
pressure can cross this boundary** — only the live-range/crossing structure.

> **Lever:** to push a value out of EAX into a callee-saved register, make its
> live range span a call/`mul`/`div`. To keep it in EAX (no push), use it up
> *before* the first such instruction. There is no other knob.

EDX is the analogous story for the second slot: `idiv`/`mul` and 2-arg calls
clobber EDX too, so a value crossing those skips to EBX.

## (2) SAVINGS rank — #uses wins  (`regalloc-tiebreak.py`, `regalloc-cost.py`)

Among values competing for a class, the one with the higher `CalcSavings`
score gets the earlier/better register, even if used *later* in the source.
**The exact cost model is known** (extracted from `regsave.c`/`i86regsv.c`/
`savings.h` and confirmed against the 10.0a binary to the constant):

```
savings = Σ_blocks ( uses·use_save + defs·def_save + idx·index_save ) · W^depth
        − Σ_blocks ( spill_loads·load_cost + spill_stores·store_cost ) · W^depth
```

Exact constants for PS (`-4r` = 486, default opt):

| weight | value | meaning |
|---|---|---|
| `W` (loop_weight) | **10** | savings multiplier **per loop nesting level** (depth1 ×10, depth2 ×100, … cap depth 5). `(LOOP_FACTOR·time)/256 = (20·128)/256`. |
| `use_save` | 1 | each use of the value |
| `def_save` | 1 | each def of the value |
| `load_cost` / `store_cost` | 2 / 2 | each spill reload / store |
| `push_cost` + `pop_cost` | 1 + 1 = 2 | a callee-saved register's prologue cost (`WorthProlog`) |
| `index_save` | 2 | a value used as an array index |

Confirmed behaviourally: a value used once per loop iteration outranks a
straight-line value for a register up to ~`W` uses — crossover at **10**
(depth 1) and **100** (depth 2), i.e. `W^depth = 10^depth`
(`regalloc-cost.py`).  Flag corollary: `-ot` → W=20, `-os` → W=1 (no loop
weighting); PS uses default → **W=10**.

> **Lever:** add/remove a use to move a value up/down the ranking (Rule 1);
> **one use inside a loop counts as ~10** (×100 at depth 2), so loop-carried
> values almost always win registers.  A callee-saved register is "worth it"
> once savings exceed 2 (≈ 3 straight-line uses, or any single loop use).

### (2a) Compiler-created temps compete in the SAME ranking as your locals

The `conflict_node` list that `SortConflicts` ranks contains **both** the
names the source declared **and** every `N_TEMP` the back end invents on
its own.  Knowing the temp-creation passes matters — they take registers
your source never named.  Passes verified by reading the v1 source:

| pass / file | when a temp is born (code-verified) |
|---|---|
| **IndexToTemp** (`fixindex.c::IndexToTemp`, gated by `IndexOkay`/`NoMemIndex`) | an `arr[i]` index isn't directly addressable (e.g. a memory-class index, or the element is reused so the load can't stay a scale-index memory operand) → `i*scale` is split into a temp via `MakeMove` |
| **CSE** (`cse.c`, `AllocTemp` at 711/737/813) | the *same* subexpression is computed ≥2× and survives the cost gate (`CanCrossBlocks`/`HoistLooksGood`) → one temp holds the value, both sites read it |
| **ConstToTemp** (`cachecon.c`, **Rule 110**) | a non-zero constant referenced ≥2× → cached in a register temp |
| **address-fold** (`addrfold.c`), **loop IV** (`loopopts.c`) | folded address arithmetic / induction-variable strength reduction → `lea`-materialised running pointers |

**Savings accounting (verified, `h/savcode.h` cost mode + `regsave.c`):**
per block, `_ReplaceOpnd` adds `use_save` (1) for each operand use **plus a
second `use_save`** when it is operand-0 of a non-condition op whose result
is a register (a move-elimination bonus); `_ReplaceResult` adds `def_save`
(1) for a def (but charges `load_cost` instead for a same-location
temp→temp copy); `_ReplaceIdx*` adds `index_save` (**2**) for an index use;
the block total is then `Weight()`-ed by `loop_weight[depth]` (=10^depth).
**`ConfBefore` is strict `savings >`** (`regalloc.c:1122`); equal-savings
ties resolve via `SortList` → `DoSortList` → `ShellSort` @0x66689, which is
**NOT stable** (alloc-success arm; see the slot-assignment pipeline canon in
§"The slot-assignment pipeline" + `docs/slot-swap-survey-2026-06-25.md`).  So
an equal-savings run is NOT necessarily preserved in pre-sort (conflict-
creation) order; the ShellSort gap-passes can reorder equal-rank conflicts.
But ties are the exception; use count (savings) dominates.

**Named local vs inline read — a structural rank change, not a tie-break.**
The `named-local-tiebreak.py` cgex experiment (2026-06-25) isolates the
exact mechanism behind the corpus's 5x diffing-vs-exact mirror bias
(observed-source-style.md §13).  Under PS_CFLAGS (BlockByBlock=TRUE,
no -ot), 4 inline reads of the same global emit **4 separate sav=2
anonymous-temp conflicts** — Watcom does NOT auto-CSE them within a block.
The equivalent `int x = G; x×4` source produces **ONE FE temp at sav=5**.
The consolidation isn't a tie-break perturbation: the named-local conflict
lands at the TOP of the ConfBefore queue and out-prioritises ANY rival at
sav ≤ N+1, while the inline form's leaves sort at the BOTTOM.  This is
why introducing `local = G;` where PS source had no such local cascades
into a downstream seat divergence — a new top-of-queue conflict claims a
callee-save (EBX/EDX) that PS never asked for, the prologue grows a `push
ebx`, frame offsets shift, byte cascade follows.  Re-run
`uv run python docs/codegen-experiments/named-local-tiebreak.py` to
regression-check the mechanism after any Watcom-source change.

**Corpus survey (measured, do not re-guess from one example).**  Across the
1186 byte-exact functions, the loop-counter idiom (`inc R; cmp R,imm;
j<cc>` back) puts the counter in: **EAX 59, EDX 51**, ECX 25, EBX 24,
ESI 21, EDI 13, EBP 7.  I tested the hypothesis "a heavily-reused
`arr[i].field` row temp displaces the counter off EAX": it is **NOT**
supported — EAX-counters and EDX-counters carry a reused row temp
(≥3 `[R+disp]` refs) at nearly the same rate (20/43 vs 18/46).  So the
counter's register is **not** predictable from a simple source heuristic;
it is the full per-value savings ranking outcome (every competing temp
included), for which the ground truth is **`c2 regtrace <fn>`**.  Two
endpoints are clear and verified by disasm: when the counter is the only
long-lived value it wins EAX (`count_city_flags`, byte-exact, counter in
EAX, element only *compared* via scale-index so **no** index temp is
born); and a per-row stride temp can win EAX while the counter sits in
EDX (`drop_all_units_morale`: the param is *moved out* of EAX to a callee
reg, freeing EAX for `i*0x4e` reused across every `unit_list[i].*`).
What decides between them in the middle is the savings arithmetic, not a
slogan.  `goto_flag_marker_mode` (3 distinct arrays, indexed once each,
void) is the open residual: `regtrace` shows `i` as the top-savings
conflict → EAX, while PS placed it in EDX — a whole-function choice the
per-value model flags but the named-local source levers (28a/115) cannot
reach, because the competitors are all single-use compiler index temps.

## (3) TIE-BREAK on equal savings — deterministic but micro-mechanism uncertain

> **Provenance.**  10.0a's compiler source is not public.  What we have is
> (a) the **Watcom 10.0a binary** (`wcc386-10.0a.exe`, partially RE'd under
> `docs/wcc386-re/`) and (b) the **Open Watcom v1.0 / v2 reference checkouts**
> (`~/git/open-watcom/owp4v1copy/`, `~/git/open-watcom/open-watcom-v2/`) —
> roughly **5–10 years younger** (≈2001–2025) descendants of the same code
> generator.  v1/v2 source is an algorithm reference, NOT 10.0a's source;
> specific behaviour must be confirmed against the 10.0a binary by experiment.
>
> The `owp4v1copy` tree in this repo carries a `REVCG_CONFFLIP`-gated **research
> hook** in `ConfBefore` (a name-pointer secondary key) added by this project's
> RE work to model the believed 10.0a tie-break.  **Upstream OW v1.0 and v2
> both have a *strict* `ConfBefore` (`return a->savings > b->savings;`) — no
> secondary key.**  Do not cite the modified `owp4v1copy` `ConfBefore` as
> "OW source"; it's the *project's model*.

After sorting conflicts by descending savings (`regalloc.c::SortConflicts`),
equal-savings ties resolve via the SAME `SortList`/`DoSortList` non-stable
`ShellSort` (the `H2` mechanism below) — 10.0a's behaviour on equal-savings
ties is **deterministic** and **moves with source changes**.  Two
micro-mechanism hypotheses are consistent with the behaviour we see in the
binary:

* **(H1) Hidden `ConfBefore` secondary key.**  10.0a's `ConfBefore` resolves
  ties on the conflict's `name`-node pointer address (symbol allocation
  order).  This is what the project's `REVCG_CONFFLIP` hook in `owp4v1copy`
  models.
* **(H2) ShellSort instability + `AddConflictNode` order.**  With a strict
  `ConfBefore`, equal-savings *runs* preserve their pre-sort order;
  `liveinfo.c::UpdateLive` walks instructions backwards and
  `AddConflictNode` *prepends*, so the conflict whose value is last-encountered
  going backwards (≈ earliest-last-use) ends up at the head of the run and is
  allocated first.

Both hypotheses give the same **observable order** — 1st-allocated takes EDX,
2nd EBX, 3rd ECX, 4th ESI, 5th EDI, 6th EBP — because both keys (name-pointer
allocation order; backward-walk creation order) move together when source
changes in the ways our levers cover.  We document the lever recommendations
below; the choice between H1 and H2 doesn't change them.

### Two source-level levers

Whatever the underlying key, source changes that shift it have two reliable
shapes when at least one tied value is a **named local**:

* **Lever 1: commute / move a use** (Rule 28a) — reorder which of the two tied
  values is referenced first in the deciding expression.  Most predictable;
  works when the use is reorderable.  Under either H1 or H2 this shifts the
  conflict node's effective position (allocation order under H1; pre-sort
  position under H2) so the head of the equal-savings run changes.
* **Lever 2: swap the declarations** (Rule 115) — the handle for residue
  Lever 1 can't reach.  When the use is fixed by semantics, reorder the two
  tied locals' declaration lines.  Under either hypothesis this shifts the
  name node's allocation order *and* `UpdateLive`'s backward-walk encounter
  order.  Direction is **not monotonic in source line** (reassignment / IL
  structure perturb both keys) — try both orders and verify.

Neither lever is exact ("try and verify," not "compute and apply"), but
together they cover essentially every equal-savings residue with a *named*
local on at least one side.  Equal-savings residue between *compiler temps*
falls outside both levers (no source name to reorder, no source use to commute)
and lives in layer 4 / move-elimination territory.

### Worked Lever 1 example (Rule 28a)

`change_citizen_targs` (int_c2.c) carried a 3-byte EDX↔EBX swap on
`cell_idx = dest_y*80 + dest_x`.  Rewriting commutatively `dest_x +
dest_y*80` (so `dest_x` is referenced first) flipped the pair to match PS
and closed the diff to **0 bytes**.

### Worked Lever 2 example (Rule 115)

`show_help_page` (mmedia.c) carried an 11-byte ESI↔EDI swap on the tied pair
`text_x` / `text_lines`.  `text_lines` is read early on both sides (`cap >
text_lines`), so Lever 1 is dead.  Swapping the declarations

```c
int text_lines;   /* was: int text_x;     */
int text_x;       /* was: int text_lines; */
```

(uses untouched) moved ESI from `text_lines` to `text_x` and closed the
diff to **0 bytes**.

In the same function, `text_w` is declared *last* yet takes the *lowest*
register (EBP); declaring `text_x` later made it take the *highest* (ESI).
Reassignment and IL structure perturb the order, so the procedure is "try
both decl orders and keep the one that verifies."  The `register` / `auto`
*keywords* remain inert (same `CGAutoDecl` path); only the *order* moves
bytes.

## (3b) Byte-register seating — the AL-squat / Rule 126/127/133 family

Byte values (`char`/`unsigned char`) seat **differently** from the
tie-break in (3), and the difference is the source of the prominent
"Byte-reg swap" residue family.  The `Byte-seat:` verdict in
`decomp-verify -v` (`c2/commands/byte_seat_hints.py`) classifies every
byte swap into one of four cases.  **Every claim below is proven against
the disassembled wcc386 10.0a binary** (VAs in the watcom10.0a repo's
`knowledge/wcc386_regalloc.py`); OW v1 (`~/git/open-watcom/owp4v1copy/
bld/cg/`) is only the algorithm guide.

**The byte candidate list** — `ByteRegs@0x79620` (`RegSets[RL_BYTE]`),
decoded from the binary (`REG_LISTS[0x04]`):

```
ByteRegs = AL, AH, DL, DH, BL, BH, CL, CH      (8 entries, 0-terminated)
```

(The §0 table lists the low-byte subset `AL,DL,BL,CL`; the high bytes
`AH,DH,BH,CH` **do** appear in PS residues, e.g. `bh`/`dh`/`ch`.)  This is
both the candidate-list order for `GiveBestReg` byte conflicts AND the walk
order for the rover (below).

**Two allocation paths** — this is *why* the family looks "unknown":

* **Named-local conflicts → `GiveBestReg@0x57b78`** over `ByteRegs`.
* **RISCified CSE / inline reads → the rover `FindRegister@0x62a29`** —
  three persistent, static cursors (`RoverByte@0x80714` /`RoverWord`/
  `RoverDouble`), advanced `++regs` per RISCified op, gated by
  `except = live | zap->reg | result.reg`.

**CASE D — Rule 133 inert byte tie (IRREDUCIBLE).**  The layer-3 tie-break
lives at `GiveBestReg+0x129..0x150` (VA **0x57ca1–0x57cc8**, label
`GiveBestReg_byte_tiebreak`):

```
0x57ca1  cmp eax, ecx          ; saves vs best_saves
0x57ca3  jg  …                 ; saves > best -> take
0x57ca5  jne …                 ; saves < best -> skip; else (tie):
0x57ca7  mov edx,[0x7f884]; and edx,esi; cmp edx,esi; jne …   ; require HW_Subset(Given,reg)
0x57cb3  mov edx,[0x7f884]; and edx,ebp; cmp edx,ebp; setne…  ; require !HW_Subset(Given,best)
0x57cc8  best = reg
```

(`0x7f884` = `GivenRegisters`, zeroed per-routine by `RegAlloc@0x58404`.)
Byte registers are sub-registers of dwords (`AL ⊂ EAX`, …), and byte
conflicts allocate *after* the higher-savings dword ones, so by then
`GivenRegisters` already covers EAX/EDX/EBX/ECX → `HW_Subset(Given, reg)`
is **true for every byte candidate**, and so is `HW_Subset(Given, best)` →
the `!HW_Subset(Given,best)` test at 0x57cbd is **false** → `best` is never
replaced on a byte tie → **`ByteRegs` list-order alone decides the seat.**
Proved from the disasm + the live `bt.given_regs` trace.  ⇒
`permute`/`decl-swap`/Rule 28a/115 **provably cannot move a pure byte
seat** — park it, don't grind.  (Trace tell: the `GB:` line reads
`[list-order] all scores 0`.)

**CASE B — Rule 126 AL-squat masking.**  A byte value is forced off AL when
an EAX zero-extension temp or `[base]` address temp overlaps its live
range: `NeighboursUse@0x580c0` builds `conf->with.regs` (offset `+0x20`,
initialised at VA 0x580fc; the `OP_MOV=0x26` copy-exemption is gated at
0x580dc) from the zap/dst/live registers over the range; `GiveBestReg`'s
eligibility loop then excludes any candidate overlapping it at VA
**0x57c50** (`test [conf+0x20], reg`, label `GiveBestReg_withregs_gate`),
so AL (⊂ EAX) drops out.  **Lever:** widen the bare-AND `unsigned char`
locals to `int` — that changes `ins->type_class` from `I1/U1` to `I4/U4`,
moving the value off `ByteRegs` onto `DoubleRegs@0x79850` entirely
(`get_education_ov_image` 92b→44b; `swap_2_figures` `char`→`int` temps
78b→26b).

**CASE C — Rule 127 rover-seated CSE.**  When PS wrote a byte expression
twice (`if (bm[i+1] != 0) f(bm[i+1], 0);`), the optimizer CSE'd it into a
temp seated by `FindRegister@0x62a29` (the rover path; reached via
`LdStAlloc@0x62d95 → LoadStoreIns → Enregister@0x62939`), re-extended via
`mov al,<reg>; and eax,0xff`; a *named* local instead makes a `GiveBestReg`
conflict that squats AL.  **Lever:** de-name — write the expression twice so
the value rejoins the rover path (`battle_action` 316b→exact,
`show_debug_screen` 5171b→exact).

**CASE A — collateral.**  The byte register is just the low/high byte of a
wider `Reg swap`; the real divergence is a dword/word equal-savings tie
(handled by (3)).  Reorderable via Rule 28a/115/123 (`permute` if the
`Cascade:` line says REACHABLE).  `control_buttons` (`dl/al` is the low byte
of an `edx/eax` tie) is the canonical example.

## (4) OVERRIDES (beat 2 & 3)  (`regalloc-tiebreak.py::moveelim,hard_shift`)

* **Hard register constraints** (highest priority):
  * variable shift/rotate count → **ECX** (`shl reg, cl`).
  * `idiv`/`div` consume **EAX (quotient/dividend) + EDX (sign-ext/remainder)**;
    other live values avoid them.
  * `mul`/`imul reg` (one-operand) consume EAX/EDX similarly.
* **Move-elimination (`CountRegMoves`)**: a value **consumed as argument *N*** is
  placed in argument *N*'s register when its live range allows, eliminating the
  shuffle `mov` — overriding the equal-savings tie-break. In `f2(a,b)`, `b` is
  put in EDX (arg2) and `a` in EBX, flipping the pure-tie order `a→EDX`.

> **Lever:** restructure so the value you want in register R is *consumed into R*
> (passed as the arg that uses R, or stored from R). Conversely, an idiv/shift in
> the live range will claim EAX/EDX/ECX and reshape everything else.

## (5) LOOP register behaviour — hoist vs reload  (`regalloc-loops.py`)

Loops add one layer on top of the scalar model: **what stays in a register
across iterations**. At the PS flags (no `-ol`, no `-oa`):

* **Locals** (counter, accumulator, params) live in registers across the whole
  loop **including calls** (callee-saved if they span a call); loaded/initialised
  once, never reloaded — they can't be aliased.
* **Loop-invariant global reads are HOISTED** (loaded once before the loop) when
  the loop has **no aliasing risk** *and* register pressure permits.
* **Loop-invariant globals are RELOADED every iteration** when the loop body
  contains **a call** (the callee might modify the global — no `-oa`) **or a
  store through a pointer** that could alias.  Intra-iteration CSE still holds:
  used N times in one iteration → loaded once per iteration, reloaded next.
* **Worth-it threshold:** a *single* invariant hoists; *multiple* invariants in
  a loop that already spends registers on accumulator+counter may not all hoist.
* **Register order** is the scalar model with **test-at-bottom** accounting:
  Watcom emits `jmp <test>; body; test: cmp; jcc body`, so the loop is entered
  at the `cmp` — the **bound is the first-used value** (gets the high register),
  then the body values.
* **Index sub-rule:** a counter used purely as a shared `[i*4]` index across two
  arrays tends to land in EDX (leaving EAX unused); a counter with a sibling
  accumulator/return value lands in EAX.

> **Lever / diagnosis:** a "PS reloads this global in the loop, we hoist it"
> (or vice-versa) diff is **not** a register choice — it's an *aliasing* mismatch.
> Match PS by matching the loop's call / aliasing-store structure.  **Never reach
> for `-oa`** to force hoisting: PS was built without it, so its globals reload
> across calls; `-oa` would diverge (and regresses the corpus by +230 bytes).

---

## Influence playbook — diff symptom → lever

| symptom (PS vs recomp) | layer | what to change in C |
|---|---|---|
| EAX vs callee-saved (push appears/disappears) | (1) | move the value's range across / before a call/mul/div |
| EDX vs EBX, or EBX vs ECX, on tied values | (3) | Lever 1: commute / reorder a use (Rule 28a). Lever 2: swap the two locals' declaration order (Rule 115, verify both directions) |
| **ESI vs EDI (Rule 28a/115)** | (3) | Lever 1: swap which slot-4/5 value is used first (worked: `change_citizen_targs`). Lever 2 (use pinned): swap the two locals' decl order (worked: `show_help_page`) |
| **register swap on RISCified memory picks** (`mov reg,[global]`, incl. `mov reg,[g]; push reg` call args), regs are a rover-order shift of PS's | (RISCify rover) | picks of the **FindRegister rover** — a persistent cursor PER WIDTH (byte AL,AH,DH,DL,BH,BL,CH,CL / word AX,DX,BX,CX,SI,DI / dword EAX,EDX,EBX,ECX,ESI,EDI), advanced once per RISCified op of that width. NOT a savings/decl tie. Shift the cursor ±k byte-neutrally: **+k = split a basic block before the op** so an extra COALESCED load is emitted (a dead/duplicated branch — push an if/else's shared store INTO BOTH ARMS, or a never-taken `if(x==K)`); −k = merge blocks / CSE a load / pass an array-or-immediate. Self-heals at the next op. decomp-verify's **`Rover:`** line shows PS-vs-RC, classifies the width, and runs the search for the exact advance. Worked: `start_smacking` (dword +1 via the dead inner-if). See `docs/wcc386-re/rover-model.md` (watcom10.0a repo) + `c2.commands.rover_hints` |
| value ranked too high/low | (2) | add/remove a use (inline-twice vs cache — Rule 1) |
| value lands in its arg register on one side only | (4) move-elim | match how the value is consumed (arg position) |
| `char`-vs-`int` register divergence / different push set | (0) | fix the local's width to PS's (movsx/movzx evidence) |
| ECX appears unexpectedly | (4) hard | a variable shift in that range claims ECX |
| EDX claimed around a divide | (4) hard | the idiv owns EAX:EDX — restructure the divide |
| PS reloads a global in a loop, we hoist (or vice-versa) | (5) | match the loop's call / aliasing-store structure; never `-oa` |
| loop counter in EDX vs EAX | (5) | shared 2-array index → EDX; counter with accumulator/return → EAX |

**Dead levers (proven inert):** the `register` / `auto` *keywords*
(`CGAutoDecl` ignores them), push/callee-save "economics", raw register
pressure (none cross the EAX boundary or change the class order). Don't add
permuter mutators for these.  **Note:** declaration *order* is NOT inert — it
is Lever 2 above (Rule 115).  Only the storage-class keywords are.

---

## Residual nuances

The model is complete: type classes, the EAX boundary, the exact savings cost
model (§2), the `ConfBefore` name-pointer tie-break (§3), overrides, loop
hoist/reload, and spill capacity are all mapped and proven, and the
`CalcSavings` weight constants are extracted and confirmed (§2).  Two small
behavioural notes remain:

* **Multiple loop-invariant globals under pressure** — a single invariant
  always hoists; whether 2+ all hoist depends on how the per-value savings
  (§2) compare against the spill costs given the other live values.  It is
  predicted by the cost model but tedious to compute by hand — compile and
  look.
* **Mutually-exclusive if/else branches** — neither value has a clear
  execution-order "first use," so the §3 tie reduces to pure declaration order
  (Lever 2 dominant, Lever 1 inert).

The one thing *not* obtained is a byte-level read of `CalcSavings` in the
`wcc386-10.0a.exe` image itself (the register/const tables are reached via
load-time-relocated pointers with no findable absolute reference, so static
Ghidra navigation into the allocator is blocked — `README.md §5b`).  It is not
needed: the cost model was taken from the code-generator source and confirmed
against the 10.0a binary's behaviour to the exact constant (§2,
`regalloc-cost.py`).

---

## Remaining hard problems (continue here)

The model is complete and the `Regalloc:` line in `decomp-verify -v` classifies
every register diff into a layer.  What's left is **reachability**: for most
sub-cases a source lever exists (codegen is deterministic) but finding the shape
that produces it is per-function work — "lever exists, not yet reduced to a
one-liner."  The **one genuine exception is sub-case 6 (spill via
rematerialization, Rule 111)**: when PS spilled a value our build can hold,
*there is no faithful source lever* — it is an ordinary `GiveBestReg` eviction
divergence, not a special compiler mode.  `decomp-verify -v`'s `Spill-class:`
line flags exactly these so you don't burn time on them.

### Corpus state

73% byte-exact (1111/1521); ~410 diffing, all decompiled (the work is
byte-tuning, not decompilation).  Triage every diffing function by its
`Regalloc:` line first: it either names the layer+lever or says **"register
layout matches PS — outside the regalloc model"** (then it's
instruction-selection / strength-reduction / tail-merge / branch-encoding — a
rule-catalogue problem, not this model).

### Easy wins (do these first)

* **Layer 3 tie-break** (Rule 28a / 115) — the equal-savings ESI↔EDI / EDX↔EBX /
  EBX↔ECX class.  Try Lever 1 first (commute an operand or move a statement so
  the right value is used first — `change_citizen_targs` pattern); if the use
  is pinned, try Lever 2 (swap the two locals' decl order — `show_help_page`
  pattern, verify both directions).  Often one line.
* **Layer 2 savings** — a value with too few/many uses: inline a global read N
  times vs cache it once (Rule 1).  Threshold: callee-save worth it at
  savings > 2 (≈3 uses, or 1 loop use ×10).
* **Layer 5 loop reload/hoist** — match PS's loop call/aliasing-store
  structure; never `-oa`.

### The hard sub-cases (the actual backlog)

1. **Const-store idiom (layer 4) — RESOLVED, see Rule 110.**  Not a single
   mystery: the *form* is deterministic (set by the destination addressing
   mode + ref-count) and the *register* is ordinary regalloc.
   **Form A** (direct global `[disp32]` / indexed-global `[reg*scale +
   global_disp]`): a `0`-store is always register-materialised
   (`xor reg,reg; mov [m],reg`, even single-use — gen-level zero rule); a
   nonzero is register-cached **iff referenced ≥ 2 times**
   (`cachecon.c::ConstToTemp`, `num_refs < 2 → skip`; call args never count,
   mem-immediate compares don't trigger it), else immediate (`c6/c7`).
   **Form B** (pointer / base+offset `[reg + disp]`): always immediate,
   both 0 and nonzero, regardless of count.  So a const-store diff is one of:
   (i) an **addressing** mismatch (PS folds the global, recomp caches a
   pointer) — that's **Rule 73**, inline the pointer; (ii) a **ref-count**
   form mismatch at equal addressing (nonzero only) — align literal uses;
   (iii) a **regalloc** register mismatch (both register-form, different reg).
   Worked example: **`do_act_zoom_out`** emitted the register form on both
   sides for `pointer_mode = 0`; only the register differed (BL vs DH) and it
   closed via a regalloc change (Rule 108), never by touching the store.
   Verified by oracle bisection (`docs/codegen-experiments/const-store.py`).

2. **Divisor / structural materialisation.**  PS does **two `idiv`s sharing a
   divisor in a callee-saved register** where we do one `idiv` and derive the
   remainder (or vice-versa).  Worked example: **`get_region_2x2_start`**
   (`code%2` and `code/2`, PS keeps divisor 2 in EDI for both; we use ESI +
   one idiv).  *Attack:* match PS's division structure in C — compute `%`
   and `/` as two explicit divisions vs one divmod.  Open: which C form makes
   Watcom emit two idivs sharing the divisor.

3. **CSE-hoisted globals in fixed algorithmic order (layer 3, Lever 1
   dead).**  When the competing values are global reads in a fixed sequence
   (e.g. `update_time`, `print3_test_info`) you can't move the use (Lever 1)
   without changing semantics, and the values aren't named locals so Lever 2
   has no source handle either — this is **genuine residue**.  *Attack:* look
   for an equivalent restructuring that changes use order without changing
   behaviour (rare); otherwise live with it.

4. **Tail-merge canonical selection (cross-function, Rule 42).**  Which
   function's tail becomes the shared canonical depends on intra-TU function
   *order*, not the dependent's body.  *Attack:* the donor cascade
   (`c2 stubs --donors`) — fix the donor byte-exact first; the dependent's
   `jmp` into it then matches.  Not fixable from the dependent's source.

5. **Multiple loop-invariant globals under register pressure (layer 2/5).**
   One invariant always hoists; whether 2+ all hoist is a savings-vs-spill
   decision given the other live values — predicted by the cost model (§2)
   but tedious by hand.  *Attack:* compile and look; reduce simultaneous
   live values or raise the wanted one's use count.

6. **Spill via rematerialization — PS re-reads a global we hold (Rule 111).**
   PS evicts the lowest-priority conflict and re-materializes it (re-reads a
   never-written global, or re-creates a constant) at each use, where our build
   has a free register and holds the value once; the dependent computations then
   cascade into different registers.  Worked example: **`bribe_emperor`** — PS
   re-reads `imperial_gift_level` 5× (EAX singles + EDI for the `trib*N` chain);
   we hold it in EAX, pushing `trib*N` into ECX, 283 b across the body.
   *This sub-case has no faithful single-source lever* (proven, Rule 111):
   removing the cache local just CSEs into a different held reg; `volatile` is
   non-faithful; the comparison-operand reversal is a consequence, not a cause.
   *Mechanism:* ordinary register pressure — which conflict `GiveBestReg`
   evicts.  *Attack:* it is **negative triage** — when `decomp-verify -v` prints
   `Spill-class:`, stop hunting a source lever; there is no confirmed one.  This
   is NOT a memory-mode artifact: the compiler's low-memory path is unreachable
   in this toolchain (the W32RUN extender masks every memory knob — `WCGMEMORY`,
   dosemu `$_dpmi`, qemu `-m` — see `docs/watcom-codegen-patterns.md` § memory),
   and it was never the cause of these diffs anyway.  Detector:
   `spill_hints.detect_spill_class`; tests `tests/test_spill_hints.py`.

### The one open reverse-engineering task

**Byte-level navigation into `GiveBestReg`/`CalcSavings` in the image.**  Not
needed for the model (the cost model is obtained + confirmed, §2), but it would
let us read the allocator bytes directly and settle sub-cases 1–2 by
disassembly instead of behavioural bisection.  Blocked on the Phar Lap TNT
data-segment relocation table (`README.md §5b`); the register/const tables
have no findable absolute reference because they're reached via
load-time-relocated pointers.  This is the single bounded RE task left.

## How to use this when a function diffs

1. Identify the diverging register(s) from `decomp-verify -v`.
2. Classify the layer with the playbook table above.
3. Apply the corresponding source lever; re-verify.
4. If it's a (3) tie-break or (4) move-elim case, the
   `regalloc-tiebreak.py` experiment is the worked template.
