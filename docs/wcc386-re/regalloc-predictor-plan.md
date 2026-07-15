# Regalloc predictor (Path B) — build plan & honest sizing

> Tooling paths below (`qemu-harness/`, `tools/*`) are in the sibling
> `~/git/ReverseEngineering/watcom10.0a` repo — see `README.md` “Where the
> tooling lives”.

Goal: a simulator that reproduces Watcom 10.0a's register assignment for a
function, so every reg-swap diff becomes a mechanical search ("which source
ordering makes the predicted assignment match PS?").

## BREAKTHROUGH (2026-06-07): decoder bug fixed + forward replay validated 17/18

Two findings turned the predictor from "self-consistent but wrong" into faithful:

1. **The hw_reg_set decoder for EBX/ECX/EDX** (a 3-cycle on masks
   `0x200000c`/`0x4000030`/`0x80000c0`). The corpus-certified mapping
   (`c2/regalloc/trace.py::REG_NAME` + `replay.py::REG_ENC`, validated against
   the real disassembly) is **`EBX=0x200000c`, `ECX=0x4000030`,
   `EDX=0x80000c0`** — the byte sub-register bits pack in `AX,BX,CX,DX` order
   (AX=bits 0-1, BX=2-3, CX=4-5, DX=6-7), NOT ModRM order. Any diff
   correlation touching EBX/ECX/EDX must use this mapping; it is what
   `select_register` validates 19,116/19,116 against. (A short-lived
   2026-06-07 relabel to `ECX=0x200000c/EDX=0x4000030/EBX=0x80000c0` was itself
   wrong and was reverted — ignore any earlier text asserting it.)

2. **A from-scratch forward replay reproduces 17/18** of start_smacking's
   register assignments with the corrected decoder. Algorithm (validated against
   the `-trace` ground-truth `rg` regs, joined to the qemu CRM/withregs table by
   allocation-order index — both compile the same TU deterministically):

   ```
   for conf in allocation_order:                 # = ShellSort(reverse NameList); reproduce_order()==True
       blocked = decode(conf.with_regs)           # interference set
       free    = [r for r in CAND15 if r not in blocked]   # CAND15 = EAX,EBX,ECX,EDX,ESI,EDI,EBP,ESP
       crm     = {r: CountRegMoves(conf, r) for r in free}
       best    = max(crm.values(), default=0)
       cands   = [r for r in free if crm[r]==best]
       pick    = name_reg[conf.name] if (coalesce hit) else cands[0]   # name-coalesce, else RegLists order
       assign(conf, pick); given.add(pick); name_reg[conf.name]=pick
   ```

   Result: **17/18**, including BOTH contested move-elim push-temps (#13->EDX,
   #14->ECX) that the diff is about. The 1 miss (#4, dln161) is a known
   truncated-range (loop-spanning, range_len>=INS_CAP) coalesce — the pinning
   MOV is outside the captured ins window.

   The `GivenRegisters`-"prefer any already-given reg" tiebreak is NOT how the
   real allocator breaks ties (it regressed #5 EBX->EBP); only **name-coalesce**
   (reuse THIS conflict-name's prior reg) + RegLists order are needed.

### qemu RETIRED (2026-06-07): the -trace image carries everything

The `-trace` image now emits the GiveBestReg SELECTION inputs directly
(watcom10.0a commit a82c119), so the ~1-min ephemeral qemu/mkhook harness is no
longer needed for the predictor:

* `wr <conf> <withregs>` -- conf->with.regs read at the reg-selection fn 0x5F8BC
  entry (EAX=conf); FIRST sighting within the routine's fb/fn block sticks.
* `gi <conf> <opcode> <result>+reg <op0>+reg <op1>+reg` -- one per instruction in
  the conflict's range (the CountRegMoves substrate), chained from the al cave.
* al keeps name as the value handle (== tree->temp/alt, validated).

Consumer side: `trace.parse()` attaches `withregs` +
`ins_walk` per alloc entry; `c2/regalloc/replay.py` (`replay_sort_rounds` +
`select_register` / `replay_order`) runs the validated GiveBestReg replay.
**End-to-end through the parser on start_smacking: 17/17 effective** (excludes the spill and the one known truncated-range coalesce) --
the fast 0.27s `-trace` compile reproduces the register assignment as well as the
retired harness. Replay rule: candidate set = class order minus with.regs; max
CountRegMoves among free; tie-break NAME-coalesce then RegLists order; accumulate
per-name. (NO "prefer any given reg" GivenRegisters tiebreak -- it over-binds.)

### What's needed to SEARCH — DONE (certified 2026-06-12)

Both original blockers are built and corpus-certified in
`c2/regalloc/replay.py`:

* **qemu retired** — the `-trace` image emits the GiveBestReg inputs
  (`with.regs`, the ins-range walk for CountRegMoves) directly (see the next
  subsection); the fast (~0.27 s) `-trace` compile alone feeds the replay.
* **Interference reconstruction under a PERTURBED order** — `build_graph`
  rebuilds the symmetric interference graph from each earlier node's
  `with.out` snapshot (edge A–B iff an earlier pick lands in a later node's
  mask), and `replay_order` replays the full pick cascade under any
  hypothesised allocation order (masks evolve as `baseline | earlier-neighbor
  picks`; GivenRegisters accumulates; scores are recorded-or-recomputed via
  `crm10a`). Certified **1,228/1,228** sorts + **19,116/19,116** picks over
  the full build trace; `inverse_search` / `batched_inverse_search` enumerate
  the birth-reorder lever space offline (no recompile).

The original driving case, **`start_smacking`, is byte-exact** — but the lever
turned out to be the RISCify push-scratch *rover*, not a GiveBestReg-seat
reorder (see "SOLVED (2026-06): the RISCify push-scratch rover" below).


## Status — SOLVED via the live oracle (2026-06-01)

The original offline plan below (port `GiveBestReg`/`BuildRegTree` from the
8-years-newer OW source and compute the interference set from disasm) is
**superseded**.  Instead we instrument the **real 10.0a compiler** (`c2 regtrace`,
the hooked `GiveBestReg` dumper) and read the allocator's true inputs, so the
only thing to model is the per-conflict SELECTION — which is now done and
validated:

| piece | state | file |
|---|---|---|
| conflict ORDERING (savings desc, last-use asc, operand-idx) | **proven** | `regalloc-last-use.py` |
| savings cost model (W=10/loop, use/def=1, spill=2) | **proven** | `regalloc-cost.py` |
| live `with.regs` / savings / candidates per conflict | **captured** (full 8-cand DoubleRegs) | `c2 regtrace` (mkhook) |
| instruction struct offsets (opcode/result/operands) | **pinned + validated 448/448** | regalloc-symbols.md |
| full `ins_range` walk (CountRegMoves inputs) | **captured + validated** | mkhook `ins_walk` |
| `CountRegMoves` + full `GiveBestReg` SELECTION | **modelled + corpus-certified 19,116/19,116** | `c2/regalloc/replay.py` (`crm10a` / `select_register`) |
| actual chosen register (live) | **UNBLOCKED** via the `-trace` compiler image | `c2 regtrace-native` / `c2.regalloc` (`rg` records) — see `regalloc-trace-image.md` |

**Validation (evidence, not claim):** on the pm_map0.c TU the model's chosen
registers are *fully self-consistent* with the live allocator — every register
appearing in any conflict's `with.regs` is reproduced by the model (93/93
conflicts, all 7 GP regs incl EBP).  The greedy (CountRegMoves==0) model alone
leaves ECX unexplained; the full CountRegMoves model picks ECX for `front_offset`
(score 4), closing that gap — direct evidence CountRegMoves is the missing piece
and is now captured correctly.  CountRegMoves overrides greedy on ~9/93 conflicts
(the move-elimination tie-breaks).  Automated end-to-end disasm check
(`regalloc-predict-live.py`): the full model predicts the register each named
variable actually gets in our compiler's output — `get_pm_from_actual`
col=EDX/pm_val=EAX/row=ECX = **3/3 match**.  That check also corrected two
assumptions (CountRegMoves is untrusted when the ins-range is truncated past
INS_CAP; the FIRST GiveBestReg sighting sticks across RegAlloc passes, not the
last).

The historical offline path and its sizing are kept below for context.

## Historical offline path (superseded)

### Why the offline v0 was only 3% on real code

v0 greedily gives each conflict the highest-priority free register.  Watcom
does NOT.  Per-conflict selection is `regalloc.c::GiveBestReg`:

```
for reg in tree->regs (candidate set from BuildRegTree):     # NOT plain DoubleRegs order
    if reg not in conf->with.regs and not in except:
        if not TooGreedy(conf, reg):
            saves = CountRegMoves(conf, reg, ...)            # primary
            pick reg with max saves; tie-break: prefer reg already in GivenRegisters
```

Worked failure `act_house1`: a zero-value (`xor ecx,ecx; mov [g],ecx`) goes
to **ECX**, not the free EAX (v0's pick) nor the higher EDX.  CountRegMoves
is 0 for every register (no MOV Rn=>Rn to save), so the choice falls to the
**BuildRegTree candidate order** + the GivenRegisters tiebreak — neither of
which v0 has.

## The port (in dependency order)

1. **`BuildRegTree` / `BuildPossible`** (`regtree.c`) — the candidate set
   `tree->regs` and its ORDER for a conflict, from the RE'd `386rgtbl.c`
   tables (`docs/wcc386-re/`).  This alone fixes the "ECX not EDX" class.
2. **`CountRegMoves`** (`regalloc.c`, body already read) — count
   `MOV Rn=>Rn` (full move) and commutative `OP Rn,x=>Rn` (half) the
   assignment would create over the conflict's live range.  Needs the IR
   move/op structure, which the extractor must expose (currently it has
   reg-rw but not the move/op operand identities — extend it).
3. **`NeighboursUse` → `conf->with.regs`** — interference set (the extractor
   already approximates this via overlapping lifetimes; tighten it).
4. **`TooGreedy`** (`regalloc.c`) — reject a reg that steals the last
   index/segment/required register from another instruction.
5. **`GivenRegisters` tiebreak** — running set of already-assigned regs;
   prefer reuse on CountRegMoves ties.
6. **`WorthProlog` + save-set** — when EDX/ECX is pushed (callee-saved by
   force) vs spilled to memory; folds into savings.
7. **Move coalescing / 2-address** — the leftmost-operand-of-a-chain rule
   (`regalloc-predict.py` already models the simple case; generalise).

Each step is validated by re-running `regalloc-extract.py`'s match-rate
against the straight-line byte-exact corpus and watching it climb.  Then
extend the extractor to branches/loops (per-block live ranges).

## Sizing

This is, honestly, porting the core of `regalloc.c` + `regtree.c` +
`386rgtbl.c` (the latter already RE'd in `docs/wcc386-re/`).  Multi-session.
But it is **fully specified** (deterministic source in `~/git/open-watcom/owp4v1copy/bld/cg/c/`)
and incrementally validatable (match-rate climbs with each ported piece).
The payoff: the ~360 reg-swap diffing functions become a mechanical
predict-and-search instead of one-off battles.

## The oracle: instrument the REAL 10.0a binary (decided)

The open-source `regalloc.c` is OW 1.x (8 yrs newer); the byte-match reference
is the 10.0a `wcc386` itself.  10.0a ships **only** the DOS-hosted compiler —
a Phar Lap TNT bound, **uncompressed flat 32-bit image** (MZ stub + LX
bootstrap + headerless payload; `va = file + 0x6758`).  No NT/OS2/Linux host,
no symbols, no object/lib form, in any 10.0.x variant (la/ga/a/b are the same
format).  So the oracle must observe *this* binary.

Three instrumentation approaches were compared:

* **A. code-cave binary patching** — REJECTED.  Must extend the TNT-mapped
  image, relocate cave space, and do DOS int-21h I/O from injected asm to get
  data out.  Fragile (one wrong byte = silent miscompile).
* **B. dosemu2 + ptrace + HW breakpoints** — RECOMMENDED FIRST.  dosemu2 runs
  the 32-bit DPMI client natively, so no free per-insn hook; but DR0–3 give 4
  hardware breakpoints, exactly enough for `GiveBestReg` / `CountRegMoves` /
  `AssignConflicts` / `BuildRegTree`.  Reuses the already-working compiler;
  read regs + `conflict_node` memory at each trap, dump to host.  One-time
  costs: va→host translation (find dosemu2's client mapping) and the 4-BP
  ceiling.  Use HW (not int3) BPs to avoid colliding with dosemu2's own
  signal/exception path.
* **C. Unicorn/QEMU CPU-emulation harness** — GRADUATE TO LATER.  Own the CPU,
  unlimited hooks + full observability, pure-Python integration; cost is
  implementing the bounded DOS/TNT syscall surface (open/read/write/seek/close,
  mem alloc, env, exit, FPU) to run a compile end-to-end.

**Self-bootstrapping function location (B's first move):** the register tables
are reached INDIRECTLY (0 direct VA refs to `DoubleRegs` at `0x821A8`; no
frame-pointer prologues), so don't locate `GiveBestReg` by static call-graph
RE.  Instead set a **hardware watchpoint on the `DoubleRegs` table memory**,
run one compile, and the faulting instruction is inside `BuildRegTree`/
`GiveBestReg` — the harness finds its own hook points.

Status of the RE foundation (works today): `wcc_image.py` cracks the TNT flat
image, pins `va = file + 0x6758` (verified: `FAR_DATA` va `0x7900E` has 4
direct code refs), and `find_regtables` locates the register lists
(`DoubleRegs = EAX,EDX,EBX,ECX,ESI,EDI,EBP` at va `0x821A8`).

## Diff-application end state (P5)

Once match-rate is high on the byte-exact corpus: for a diffing function,
run the predictor on PS's value-flow and on ours; where the predicted
assignment diverges, report the minimal last-use/operand reorder that makes
ours match PS, surfaced in `decomp-verify -v`.

### P5 — BUILT (engine): `c2/regalloc/replay.py` (offline) + `cascade_hints.py`

The forward model + inverse-search engine live in `c2/regalloc/replay.py`,
unit-tested by `tests/test_alloc_replay.py` / `tests/test_cascade_hints.py`
(no live compile needed):

* **forward model** `select_register(cand_scores, given_before)` — the
  corpus-certified GiveBestReg SELECTION rule (argmax CountRegMoves; tie → the
  first candidate that is a hw-subset of GivenRegisters; else list order). The
  2-address operand-order asymmetry (`result = op0; result op= op1`, so the
  result reuses the LEFT operand's reg) is carried in the recorded/`crm10a`
  scores, so the model *represents* the accumulator choice a symmetric model
  could not. `replay_order` runs the full cascade under a hypothesised order.
* **inverse query** `inverse_search(rows, want)` / `batched_inverse_search`
  — enumerate single-row moves + pair swaps of the allocation order and
  return the orders whose full cascade reproduces PS's seats, each tagged
  `tie` (reachable by a pure birth reorder, Rule 28a/115) vs a savings-change,
  with per-row `side_effects` to check against PS's diff rows.

The old `c2/commands/regsolve.py` engine, its `c2 regtrace --solve` wiring,
and the blind `c2 permute` sweep were **removed** (2026-06 — the auto-solvers
did not close diffs in practice). The offline engine now feeds the
**`Cascade:`** hint (`c2/commands/cascade_hints.py`, surfaced in
`decomp-verify -v`) and **`c2 regalloc-verdict`**; the source-edit ACTUATOR is
**`c2 forge`** (its `commute_all` / `decl_swap_all` / `stmt_reorder_deep`
levers realise the commutes/reorders the inverse search names).

**Validated live** end-to-end on `show_tribunes_report`: the inverse search
correctly emits **zero** birth-reorder candidates — a true negative, because
that function's accumulator residue is in *implicit* array-index addressing
(`a[i].centuries[j]`) with no source `+` to commute.

**Remaining work** (to close more of the ~360 reg-swap corpus):
1. *(done)* the `GivenRegisters` tiebreak is implemented in
   `select_register` and certified (it decides 7,233 of the 19,116 picks).
2. an **implicit-index transform generator**: rewrite `a[i].f[j]` ->
   explicit `*(T*)((char*)a + j*sz + i*stride + off)` with the operand order
   the predictor says PS wants (the implicit accumulator has no source `+`,
   so `commute_all` can't reach it — the pointer-arith form exposes it).
3. a **move-elim transform generator** for the `crm_loss` class (introduce/
   relocate the `MOV Rn=>Rn` the model says lands the value in PS's reg).

## SOLVED (2026-06): the RISCify push-scratch rover — start_smacking byte-exact

The contested call-argument push registers are picks of the **RISCify rover
`FindRegister`** (10.0a va 0x62a29; owp4v1 `bld/cg/intel/c/i86ldstr.c`).  In code
generation, before register allocation, `LdStAlloc` (va 0x62d95) lowers each
`push <global>` to `mov reg,[global]; push reg`, with `reg` = the next entry in
`DoubleRegs` (va 0x79850 = EAX,EDX,EBX,ECX,ESI,EDI,EBP,ESP) not in `except`
(= live | zap | result), over a **persistent cursor** advanced once per RISCified
dword op.  GiveBestReg later only coalesces the pushed value into that scratch.

So the register depends on the COUNT of RISCified dword loads before the call.
PS's cursor is +1 ahead at those three pushes.  The fix is byte-neutral: writing
`smk_ref_wi = 0x28` in BOTH arms of the dead inner `if (smk_height==0xc8)`
(instead of once after it) is store-identical but splits the basic blocks, so the
compiler emits one extra COALESCED (byte-invisible) dword load before the calls
— advancing the cursor +1, turning EDX/EBX/ECX into PS's EBX/ECX/ESI, healing at
the next push.  **start_smacking is byte-exact to PS.EXE.**

This is now a generic decomp-verify feature: the **`Rover:`** hint
(`c2.commands.rover_hints`) detects a call-arg push-scratch swap, shows PS-vs-RC
picks, and runs the rover search over the function's `fr` trace to report the
exact byte-neutral advance + the steering recipe (dead/duplicated branch to add a
coalesced load; merge/CSE/array-arg to remove one).  Model + simulator:
watcom10.0a `docs/rover-model.md`, `tools/rover_sim.py`, `tools/rover_search.py`.

(Background corrections that enabled this: the Ghidra DB was re-based to the true
flat base `va = fo - 0x2200`; the EBX/ECX/EDX mask labels were corrected to
EBX=0x200000c, ECX=0x4000030, EDX=0x80000c0; and the rover order is the dword
`DoubleRegs` list, not FirstReg's `FindRegisterOrder` — FirstReg was a dead end.)
