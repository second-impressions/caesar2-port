# Watcom 10.0a Register Allocator: Annotated Research

> The canonical, proven register-allocation model is **Rule 89** in
> `docs/watcom-codegen-patterns.md`, reverse-engineered from the actual
> `wcc386-10.0a.exe` (`docs/wcc386-re/`) and proven by
> `docs/codegen-experiments/regalloc-order.py` +
> `regalloc-eax-boundary.py`.  Read it first; this document is the
> supporting theory.

> **Scope**: This document covers the internal workings of the Watcom C/C++ 10.0a
> (mid-1990s) graph-coloring register allocator as it relates to a decompilation /
> binary-matching effort against a PS.EXE binary compiled with `-d1` and standard
> optimisation flags. All findings are annotated with their source.

> **Companion docs (read in this order)**:
>
> 1. **`docs/watcom-regalloc-levers.md`** — practical decision tree:
>    symptom → lever.  Start here when fixing a function.
> 2. **`docs/watcom-codegen-patterns.md`** — numbered rule catalogue
>    (89 rules).  Each rule has discovery commit + worked example.
>    **Rule 89 is the canonical, proven register-allocation model** —
>    read it before this document.
> 3. **This document** — the theory behind the levers.  Read when a
>    lever surprises you and you want to understand *why*.

---

## 1. Provenance and Architecture

### 1.1 The Code Generator is Wholly Proprietary

The Watcom code generator (`bld/cg/`) is shared across all Watcom languages (C,
C++, FORTRAN) and was written entirely in-house.

> _"The Open Watcom code generators, the heart of the compilers. These are shared
> by all languages (C, C++, FORTRAN). Currently supported targets are 16-bit and
> 32-bit x86 as well as Alpha AXP."_
>
> — **Open Watcom V2 Developer Guide**, `docs/doc/devguide/tour.gml`,
> [open-watcom/open-watcom-v2 on GitHub](https://github.com/open-watcom/open-watcom-v2/blob/master/docs/doc/devguide/tour.gml)

> _"The reasons why this was possible at all was the fact that Watcom had very
> little reliance on third-party tools and source code and had developed
> practically everything in-house, from YACC to IDE."_
>
> — **Ibid.**

The allocator in `bld/cg/c/regalloc.c` is therefore a proprietary design, not
derived from GCC, LLVM, or any published academic reference implementation. It
predates the Briggs PhD thesis (1992) and the Chaitin-Briggs improvements, though
it shares their interference-graph lineage conceptually.

### 1.2 Historical Context: Watcom's Reputation in the Mid-1990s

> _"In the mid-1990s some of the most technically ambitious DOS computer games
> such as Doom, Descent, Duke Nukem 3D, Rise of the Triad, and Tomb Raider were
> built using Watcom C/C++."_
>
> — **Wikipedia**, "Watcom C/C++",
> <https://en.wikipedia.org/wiki/Watcom_C/C++>

> _"In a February 1989 overview of optimizing C compilers, BYTE praised Watcom C
> 6.5's 'unmatched execution speed' and noted that it was the most ANSI
> C-compliant."_
>
> — **Ibid.**

> _"Version 10.0 included the Win32 SDK for Win32s & Windows NT 3.1, the Windows
> 3.1 SDK, and the OS/2 1.3 & 2.0 SDK's for OS/2 development."_
>
> — **Computer History Wiki**, "Watcom C",
> <https://gunkies.org/wiki/Watcom_C>

---

## 2. The Full Compilation Pipeline

The allocator does not operate on raw C source. It receives IR that has already
been through several optimisation passes.

> _"The overall optimisation pipeline (in `bld/cg/c/generate.c`, line 681) runs
> these major passes in order:_
>
> 1. _CFG (Control Flow Graph) normalization and tail recursion_
> 2. _Common subexpression elimination (CSE) with copy/constant propagation_
> 3. _Loop optimisations: invariant code motion, induction variable strength
>    reduction, loop enregistration_
> 4. _Multiplication strength reduction (multiply → shift+add)_
> 5. **Register allocation (graph-coloring based with scoring)\***
> 6. _Peephole optimisation (merge adjacent operations)_
> 7. _Scoreboarding (redundant load/store elimination)_
> 8. _Condition code optimisation (eliminate redundant comparisons)_
> 9. _Instruction scheduling_
> 10. _Encoding and object emission"_
>
> — **AI analysis of Open Watcom source (`bld/cg/c/generate.c`, line 681)**,
> `public/open watcom/8086_optimisations_report.md`,
> [ggeorgovassilis/public on GitHub](https://github.com/ggeorgovassilis/public/blob/master/open%20watcom/8086_optimisations_report.md)

**Implication for binary matching**: By the time the allocator runs (step 5), CSE
has already collapsed duplicate loads, and the loop enregistration pass may have
already promoted loop-invariant globals into pseudo-registers. The allocator sees
a richer set of pre-coalesced live ranges than a naive reading of the C source
would suggest.

---

## 3. Internal Terminology: "Conflicts" = Live Ranges

Watcom calls live ranges **"conflicts"** internally, not "live ranges" or
"intervals." This is visible in the public crash trace from issue #784 of the
Open Watcom V2 repository:

> ```
> #0  NeighboursUse (conf=0x56fc80) at regalloc.c:827
>        no_conflict = {regs = {_0 = 0, _1 = 0},
>                       out_of_block = {_0 = 0, _1 = 0, _2 = 0, _3 = 0},
>                       within_block = {_0 = 0}}
> #1  GiveBestReg (conf=0x56fc80, tree=0x5ad480, ...) at regalloc.c:950
> #2  GiveRegister (conf=0x56fc80, ...) at regalloc.c:1169
> #3  AssignConflicts () at regalloc.c:1271
> #4  RegAlloc (keep_on_truckin=true) at regalloc.c:1358
> ```
>
> — **Open Watcom V2 Issue #784**, "Segmentation fault when building debug
> compiler",
> <https://github.com/open-watcom/open-watcom-v2/issues/784>

The `no_conflict` structure contains two critical sub-fields:

- **`out_of_block`** — a bit-set of registers already claimed by conflicts whose
  live ranges cross basic block boundaries (i.e., survive at least one branch or
  call).
- **`within_block`** — a bit-set of registers claimed by conflicts that live
  entirely within a single basic block.

This distinction is the mechanical explanation for the EAX-vs-ECX register
choice observed in the PS.EXE vs. recomp diff: block-scoped variables generate
only `within_block` interference, while function-scoped variables that span calls
generate `out_of_block` interference and are forced into callee-saved registers.

---

## 4. The Scoring Algorithm: `CalcSavings` → `GiveBestReg` → `CountRegMoves`

This is the heart of register selection. The scoring algorithm is documented in
the AI source-code analysis:

> _"The allocator in `bld/cg/c/regalloc.c` uses an interference-graph approach:_
>
> - _`CalcSavings()` computes the benefit of allocating each conflict (live range)
>   to a register. Conflicts are sorted by descending savings — highest-value live
>   ranges get first pick._
> - _`GiveBestReg()` (line 1009) iterates through possible registers and scores
>   each with `CountRegMoves()` (line 456):_
>   - _Full score for `MOV temp→reg` or `MOV reg→temp` (eliminates a move)_
>   - _Half score for operations using the temp as an operand in the chosen
>     register_
>   - _Tie-breaking: prefers registers already in `GivenRegisters` (reuse
>     minimizes interference)_
> - _`TooGreedy()` (line 708) prevents stealing the last index register, last
>   segment register, or the last register needed by any instruction in the
>   conflict's live range. This is a critical safety net against unsolvable
>   register allocation failures."_
>
> — **AI analysis of Open Watcom source**, `8086_optimisations_report.md`
> (section 5b), [ggeorgovassilis/public on GitHub](https://github.com/ggeorgovassilis/public/blob/master/open%20watcom/8086_optimisations_report.md)

### 4.1 What decides EAX vs a callee-saved register

> Canonical statement of this is **Rule 89** in
> `docs/watcom-codegen-patterns.md`, proven by
> `docs/codegen-experiments/regalloc-eax-boundary.py` against the actual
> `wcc386-10.0a.exe`.

A value sits in EAX vs a callee-saved register **purely by whether its
live range crosses an EAX-clobber** (a `call`, or `mul`/`div`/`idiv`).
Cross it → the value is forced out of EAX; don't → it stays in EAX.  This
is necessary and sufficient: a clinching pair (identical source, same
call, same use count — only the crossing differs) flips EAX↔EDX, while the
`register` keyword, maximum register pressure, and use count all fail to
move the value across the boundary.

Register choice is decided by three things and nothing else:

1. **Interference / live-range structure** — which values are live at once,
   and which ranges cross a clobber.
2. **`CountRegMoves` move-elimination** — does the assignment turn a `mov`
   into a no-op or let an operand/result already sit in the chosen reg.
3. **Candidate list order** — first non-interfering register in
   `DoubleRegs = EAX,EDX,EBX,ECX,ESI,EDI,EBP` (10.0a) wins ties.

There is no push/pop "economics" term and no caller/callee-save bonus: the
no-push registers (EAX + the used parameter registers) are exactly the
prefix `EAX,EDX,EBX,ECX` of `DoubleRegs`, so list order already prefers
them.  Practical consequence: when a diff is "PS holds it in a callee-saved
reg where we use EAX" (or vice-versa), the cause is a live-range/crossing
difference in the C source — there is no flag or keyword to chase.

### 4.2 `TooGreedy()` — the safety net

> _"`TooGreedy()` (line 708) prevents stealing the last index register, last
> segment register, or the last register needed by any instruction in the
> conflict's live range."_
>
> — **Ibid.**

This explains occasional unexpected spills: if ECX is required by a shift-count
operation within the conflict's live range, `TooGreedy()` will refuse to assign
ECX to a different conflict even if the savings score would otherwise suggest it.

---

## 5. Register Priority Order and the `i386rgtbl` Table

For 32-bit compilation (wcc386), the candidate register priority for integer
temporaries is established in `bld/cg/intel/i386/c/i386rgtbl.c` (analogous to
the 16-bit `bld/cg/intel/i86/c/i86rgtbl.c`).

> _"AX, DX, BX, CX (in that order) are the preferred general-purpose registers —
> they are the first choices for the WordRegs allocator set."_
>
> — **AI analysis of Open Watcom source**, `8086_optimisations_report.md`
> (section on `#pragma aux` guidelines), [ggeorgovassilis/public on GitHub](https://github.com/ggeorgovassilis/public/blob/master/open%20watcom/8086_optimisations_report.md)

For 32-bit, this maps to: **EAX → EDX → EBX → ECX → ESI → EDI → EBP**.

The key constraint shaping this order is Watcom's calling convention:

> _"The Watcom compiler doesn't conform to the register usage conventions in
> [standard x86 ABI]. The only scratch register is EAX. All other general purpose
> registers are callee-save, except for EBX, ECX, EDX when used for parameter
> transfer, and ESI when used for return pointer."_
>
> — **Agner Fog**, _Calling Conventions for Different C++ Compilers and Operating
> Systems_, Table 4 (Watcom 32-bit v. 1.2 entry),
> <https://www.agner.org/optimize/calling_conventions.pdf>

And from the Watcom documentation itself:

> _"All used 80x86 registers must be saved on entry and restored on exit except
> those used to pass arguments and return values."_
>
> — **Watcom documentation**, quoted in "Using Watcom's Register-based Calling
> Convention With TASM",
> <http://blarg.ca/2018/04/16/using-watcoms-register-calling-convention-with-tasm>

**Implication**: EBX, ECX, EDX are callee-saved in Watcom's convention _whenever
they are not argument/return registers_. If a function takes no parameters in
ECX, and uses ECX as a local variable, it must `push ecx` in the prologue and
`pop ecx` in the epilogue. The allocator knows this and prices it into the
savings calculation.

---

## 6. The `AssignConflicts` Algorithm: Step by Step

Reconstructed from the crash-trace call stack and the analysis document:

| Step | Function            | What it does                                                                                                                         |
| ---- | ------------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| 1    | `Renumber()`        | Numbers all conflicts (live ranges) across the function's CFG                                                                        |
| 2    | `CalcSavings()`     | Computes net benefit of enregistering each conflict                                                                                  |
| 3    | `SortConflicts()`   | Sorts by descending savings; highest-value conflicts get first pick                                                                  |
| 4    | `AssignConflicts()` | Iterates the sorted list; calls `GiveRegister()` per conflict                                                                        |
| 5    | `GiveRegister()`    | Calls `NeighboursUse()` to build the interference bit-set, then `GiveBestReg()`                                                      |
| 6    | `GiveBestReg()`     | Scores non-interfering registers by `CountRegMoves()` move-elimination; applies the `TooGreedy()` guard; first in `DoubleRegs` order wins ties (§4.1 / Rule 89) |
| 7    | Spill               | If no register fits: evict to memory; insert reload/store around each use                                                            |

> _"The call stack at crash time reveals: `AssignConflicts()` → `GiveRegister(conf)`
> → `GiveBestReg(conf, tree, except, needs_one)` → `NeighboursUse(conf)`."_
>
> — **Open Watcom V2 Issue #784**, [GitHub](https://github.com/open-watcom/open-watcom-v2/issues/784)

The `state = ALLOC_BITS` visible in `AssignConflicts()`'s local variables
indicates the allocator is in a bit-set driven phase (as opposed to a fallback
stack-slot phase), confirming the graph-coloring approach is active.

---

## 7. Live Range Analysis: `out_of_block` vs `within_block` — The Core of the EAX vs ECX Divergence

### 7.1 The Chaitin-style interference graph foundation

> _"In register allocation, nodes in the graph represent live ranges (variables,
> temporaries, virtual/symbolic registers) that are candidates for register
> allocation. Edges connect live ranges that interfere, i.e., live ranges that are
> simultaneously live at at least one program point."_
>
> — **Wikipedia**, "Register allocation",
> <https://en.wikipedia.org/wiki/Register_allocation>

> _"A variable that is not spilled is kept in the same register throughout its
> whole lifetime."_
>
> — **Ibid.** (describing Chaitin-style graph-coloring's third major drawback)

Watcom's allocator follows this model. A conflict assigned to ECX stays in ECX
for its entire live range — there is no live-range splitting in Watcom 10.0a.

### 7.2 The call-site interference boundary

When a live range crosses a `CALL` instruction:

- EAX is "pre-colored" to the return value of the call — it interferes with any
  live range crossing that call.
- EBX, ECX, EDX are "pre-colored" to the argument registers consumed by the
  call — they interfere for the duration of the call instruction itself, but only
  at that point.
- ESI, EDI, EBP are truly callee-saved — they do _not_ interfere with conflicts
  that span the call, because any callee that uses them must restore them before
  returning.

> _"Now if a temp t is live after a function call, we have to add an interference
> edge connecting t with any of the fixed registers noted above, since the value
> of those registers are not preserved across a function call."_
>
> — **Frank Pfenning et al.**, _Lecture Notes on Calling Conventions_, 15-411:
> Compiler Design, Carnegie Mellon University,
> <https://www.cs.cmu.edu/~janh/courses/411/23/lec/11-calling.pdf>

Watcom implements the same constraint. Conflicts with `out_of_block` interference
(i.e., live ranges spanning calls) cannot be assigned EAX — it is always killed
by the call's return value — and must be assigned from the callee-saved pool:
EBX, ECX, ESI, EDI, EBP.

### 7.3 Why block-scoped variables collapse to EAX

For block-scoped variables:

```c
{
    int cache = global->val;   // defined here
    if (cache) font_no(cache, ...);
}  // cache dies here — its live range ends before the next block
```

The conflict for `cache` has **zero** `out_of_block` interference entries: its
live range **does not cross the `font_no` call** (it is used in the `if` test
_before_ the call, or not at all).  EAX is therefore not in its interference
set, and EAX is first in `DoubleRegs`, so it wins.

For function-scoped variables:

```c
int cache0, cache1, ..., cache7;
cache0 = global->val0;
if (cache0) font_no(cache0, ...);  // cache0 must survive this call
// cache1..cache7 also live here
cache1 = global->val1;
// ...
```

Each `cacheN` has a live range spanning multiple `font_no` calls. EAX is
impossible (killed by each call). The allocator fills the callee-saved pool
in order: **EBX → ECX → ESI → EDI → EBP**, saving/restoring each in the
prologue/epilogue.

---

## 8. The Loop Enregistration Pre-Pass

This pass, which runs _before_ the main register allocator (step 3 in the
pipeline), can independently create long-lived conflicts that force callee-saved
register allocation:

> _"Loop enregistration: moves loop-invariant memory references into registers
> (processes from innermost loops outward)."_
>
> — **AI analysis of Open Watcom source**, `8086_optimisations_report.md`,
> [ggeorgovassilis/public on GitHub](https://github.com/ggeorgovassilis/public/blob/master/open%20watcom/8086_optimisations_report.md)

> _"The compiler will keep local variables (especially those without their address
> taken) in registers through the register allocator. This is always safe and
> often necessary because the aliasing model is conservative. The `-oa` flag helps
> but cannot eliminate all false aliasing."_
>
> — **Ibid.**

If any of the 8 global accesses in a PS.EXE-style function are inside a loop,
the enregistration pass creates a conflict tagged with `out_of_block` interference
spanning the entire loop body — achieving the same callee-saved allocation
outcome as function-scope variable declarations, without any change to the C source.

---

## 9. The `mov eax, ecx` / `mov eax, esi` Pattern Explained

The 2-byte `mov eax, reg` instructions observed in PS.EXE before each `font_no`
call are a direct consequence of the callee-saved register allocation:

1. The allocator assigns `cache0` to ECX (survives calls).
2. `font_no`'s first argument must arrive in EAX (Watcom's watcall convention:
   args passed in EAX, EDX, EBX, ECX order).
3. The allocator emits `mov eax, ecx` at the call site to shuffle the cached
   value into the argument register.

> _"Up to 4 registers are assigned to arguments in the order EAX, EDX, EBX, ECX.
> Arguments are assigned to registers from left to right."_
>
> — **Wikipedia**, "x86 calling conventions" (Watcom section),
> <https://en.wikipedia.org/wiki/X86_calling_conventions>

In the recomp, `cache` is already in EAX, because its live range does **not
cross** the `font_no` call (an EAX-clobber), so EAX is not in its interference
set and EAX is first in `DoubleRegs`.  No shuffle is needed, producing code
**2 bytes shorter per block** (16 bytes across 8 blocks).  When the value's range
*does* cross the call, EAX is excluded from its interference set and the value
goes to a callee-saved register (see § 4.1 / Rule 89).

---

## 10. `TooGreedy()` and Hard Register Constraints

Specific x86 instructions impose hard constraints that the allocator must
respect:

> _"Specific instructions impose hard register constraints (from
> `bld/cg/intel/i86/h/rg.h`)"_
>
> — **AI analysis of Open Watcom source**, `8086_optimisations_report.md`,
> [ggeorgovassilis/public on GitHub](https://github.com/ggeorgovassilis/public/blob/master/open%20watcom/8086_optimisations_report.md)

> _"CX/CL is required for variable-count shifts and LOOP/REP prefixed
> instructions. If your inline code uses these, CX will be contended with code
> that needs variable shifts or string operations in the same function."_
>
> — **Ibid.**

`TooGreedy()` enforces these constraints by refusing to assign a register that is
the "last" register of its class needed by some instruction within the conflict's
live range. This can produce unexpected spills even when the savings calculation
would otherwise justify an assignment.

---

## 11. The Graph-Coloring Academic Context (1990s)

Watcom's allocator was contemporary with the peak of graph-coloring allocator
research. The two dominant algorithms of the era:

> _"Both the Chaitin-Briggs allocator and the Callahan-Koblenz allocator were
> published in the 1990s."_
>
> — **Cooper, Dasgupta, Eckhardt**, "Revisiting Graph Coloring Register
> Allocation: A Study of the Chaitin-Briggs and Callahan-Koblenz Algorithms",
> LCPC 2005,
> <https://llvm.org/pubs/2005-10-20-LCPC-RegAlloc.pdf>

The Chaitin-Briggs phases (Renumber → Build → Coalesce → Spill Cost → Simplify →
Spill Code → Select) map closely to what is visible in Watcom's `regalloc.c`:

> _"Coalesce: merge the live ranges of non-interfering variables related by copy
> instructions. Spill cost: compute the spill cost of each variable. This assesses
> the impact of mapping a variable to memory on the speed of the final program.
> Simplify: construct an ordering of the nodes in the interference graph."_
>
> — **Wikipedia**, "Register allocation",
> <https://en.wikipedia.org/wiki/Register_allocation>

Watcom's `CalcSavings()` corresponds to the Spill Cost phase. The `SortConflicts()`
→ `AssignConflicts()` sequence corresponds to Simplify → Select. Crucially,
Watcom appears **not** to implement conservative coalescing (the Briggs
improvement) — it uses a simpler savings-first greedy assignment. This is
consistent with the observed behavior where independently-scoped variables that
could theoretically share a register do not coalesce into a single conflict.

---

## 12. Summary Table: What Determines Register Choice

| Factor                                           | Effect on register selection                                                          | Source                                                                     |
| ------------------------------------------------ | ------------------------------------------------------------------------------------- | -------------------------------------------------------------------------- |
| Live range crosses `CALL`                        | EAX impossible; forces callee-saved pool                                              | Watcom convention: EAX = return value; `out_of_block` interference bit set |
| Live range does NOT cross an EAX-clobber          | EAX chosen — first in `DoubleRegs`, not in the interference set                       | `within_block` interference only; § 4.1 / Rule 89                          |
| Move elimination opportunity                      | Higher `CountRegMoves` score if assignment avoids a `MOV` / matches an operand        | `CountRegMoves()` in `regalloc.c`                                          |
| Number of simultaneously-live values              | More live-at-once → more callee-saved regs consumed, in `DoubleRegs` order            | interference graph; `DoubleRegs = EAX,EDX,EBX,ECX,ESI,EDI,EBP`             |
| Hard instruction constraint (shift count in ECX)  | `TooGreedy()` refuses that register                                                   | `TooGreedy()` in `regalloc.c`, constraint tables in `rg.h`                 |
| Loop enregistration pre-pass                      | Promotes loop-invariant globals to long-lived conflicts before main allocator runs    | `loopopts.c` loop enregistration pass                                      |
| Live-range shape (where uses sit vs calls)        | A range spanning a call/`mul`/`div` is forced to a callee-saved register              | the EAX-clobber crossing — § 4.1 / Rule 89                                 |

---

## 13. Practical Implications for Binary Matching

Given the above, to reproduce the original PS.EXE register allocation pattern
from C source:

1. **Shape the live range across the call.** To put a value in a callee-saved
   register (as PS does), make its live range **cross a call** (or `mul`/`div`):
   read it into a named local *before* the call and use it *after*.  To keep a
   value in EAX, use it *before* the call so its range never crosses.  This is
   the only lever for the EAX↔callee-saved choice (Rule 89).

2. **Accept the `mov eax, reg` shuffle.** A value held in a callee-saved
   register across a call emits a 2-byte move into the argument register at the
   call site.  PS.EXE has it too.

3. **`-ol` (loop enregistration)** affects loops only, not sequential-block
   patterns.

4. **`#pragma aux` cannot force local-variable register assignment.** It only
   sets calling conventions for named functions, not the allocator's internal
   assignment of locals.

---

## 14. Key Source Files (Open Watcom codebase)

| File                              | Role                                                       |
| --------------------------------- | ---------------------------------------------------------- |
| `bld/cg/c/generate.c` (line 681)  | Main optimisation pipeline driver                          |
| `bld/cg/c/regalloc.c`             | Graph-coloring register allocator (1366 lines)             |
| `bld/cg/c/loopopts.c`             | Loop optimisations including loop enregistration           |
| `bld/cg/c/cse.c`                  | Common subexpression elimination                           |
| `bld/cg/intel/i386/c/i386rgtbl.c` | 32-bit register sets and allocation order                  |
| `bld/cg/intel/i86/h/rg.h`         | Hard register constraint definitions per instruction class |
| `bld/fe_misc/h/callinfo.c`        | Watcall/cdecl/pascal calling convention definitions        |

Source: AI analysis of Open Watcom codebase,
[`8086_optimisations_report.md`](https://github.com/ggeorgovassilis/public/blob/master/open%20watcom/8086_optimisations_report.md);
cross-validated against Open Watcom V2 issue #784 crash trace,
<https://github.com/open-watcom/open-watcom-v2/issues/784>.

---

## 15. Cross-Reference with Open Watcom V2 Source (`~/git/open-watcom/open-watcom-v2`)

The following findings were verified directly against the Open Watcom V2 source
tree.

### 15.1 `DoubleRegs` Allocation Order

The 32-bit integer allocation list, reverse-engineered from
`wcc386-10.0a.exe` (table at `va 0x821A8`) and confirmed behaviourally
(`docs/codegen-experiments/regalloc-order.py`):

```
DoubleRegs = EAX, EDX, EBX, ECX, ESI, EDI, EBP        (EBX before ECX)
```

This is the `RL_DOUBLE` list (`rl.h`); `GiveBestReg()` iterates it via
`tree->regs`.  `DoubleRegs` and `DoubleParmRegs` share the same first four
(`EAX,EDX,EBX,ECX`).  Behavioural proof: piling up N simultaneous cross-call
int values consumes registers in the order `EDX, EBX, ECX, ESI, EDI, EBP`
(EAX is the return/clobbered reg) — EBX strictly before ECX.  See Rule 89
and `docs/wcc386-re/`.

### 15.2 No caller/callee-save bonus

The allocator applies **no** penalty or bonus for callee-saved vs
caller-saved registers.  A register is chosen by `CountRegMoves`
move-elimination plus `DoubleRegs` list order: the first non-interfering
register with the highest move-elimination score wins.

This holds structurally: under `__watcall` the no-push registers (EAX + the
used parameter registers) are exactly the prefix `EAX,EDX,EBX,ECX` of
`DoubleRegs`, so list order already prefers them — no separate bias is
possible or needed.  Proven in `regalloc-eax-boundary.py` (`nc_pressure`:
even four extra live values cannot evict the value that holds EAX).  The
equal-savings tie-break is **first-use order** (`regalloc-tiebreak.py`,
corpus-validated).  The exact `CalcSavings` weights are known too — loop
multiplier **W=10** per nesting level, `use_save=1`, `load/store_cost=2`,
callee-save prolog cost 2 — confirmed against the binary in
`regalloc-cost.py` (see `docs/wcc386-re/regalloc-model.md §2`).

### 15.3 `CallZap` — How EAX Gets Excluded

When a conflict's live range spans a CALL instruction, `NeighboursUse()`
(regalloc.c:854) adds the instruction's `zap->reg` to `conf->with.regs`.

`CallZap()` (`bld/cg/intel/c/x86reg.c:259`) returns:
```c
zap = state->modify;                    // callee's declared modify set
HW_TurnOn( zap, state->parm.used );     // argument registers consumed
HW_TurnOn( zap, state->return_reg );    // return register (EAX)
zap = FullReg( zap );
tmp = ReturnReg( WD, _NPX(...) );
HW_TurnOn( zap, tmp );                  // EAX again for safety
```

For watcall calls: at minimum **EAX** is zapped (return value). Argument
registers (EAX/EDX/EBX/ECX as used) are also zapped. So a conflict that must
survive across a `font_no(val, ...)` call — where `val` goes in EAX — has EAX
in its interference set and must use a different register.

### 15.4 Why PS.EXE Uses ECX for `rolling_profit`

The assembly pattern:
```nasm
mov ecx, [rolling_profit]    ; define
test ecx, ecx                ; use #1 (condition)
jge .positive
; negative path:
mov eax, ecx                 ; use #2 (shuffle to arg1)
neg eax
... call font_no
jmp .end
.positive:
mov eax, ecx                 ; use #2 (shuffle to arg1)
... call font_no
.end:
```

The conflict for the cached value spans from `mov ecx, [global]` through both
branches of the if/else. Since the `test`/`jge` creates a branch, the live range
crosses basic block boundaries → `out_of_block` bit is set → the conflict
interferes with EAX (zapped by `font_no` call in both paths, even though the
value is consumed before the call, the allocator conservatively includes zap
registers at all instructions within the live range).

With EAX excluded, the allocator picks the next available register from
`DoubleRegs`, which in **10.0a is `EAX, EDX, EBX, ECX, ESI, EDI, EBP`**
(EBX *before* ECX — va 0x821A8 in the binary).  So: EDX (unless used as arg2), then EBX,
ECX, ESI, EDI, EBP.  For N signed-value blocks with overlapping live
ranges they spread across EDX, EBX, ECX, ESI, EDI in **first-use order**
(see Rule 28a in `watcom-codegen-patterns.md`).

### 15.5 Why Our Recomp Still Uses EAX — And How to Force Callee-Saved Regs

Our recomp's variable (whether block-scoped or function-scoped) has a live
range that **does not cross basic block boundaries in the same way**. The
compiler sees:
1. Load global into temp
2. Test temp
3. In each branch: temp is the last use before the call (consumed as arg1)

Since the value goes directly into EAX for `font_no`'s first argument, the
allocator can assign the temp to EAX itself — no call crossing required.
The temp is dead after `mov eax, temp` (or it IS eax already), so the zap
set of the call doesn't interfere.

**Empirical test results** (Watcom 10.0a, `-d1 -os -3r -mf`):

| Variable placement | Load position | Register used | push esi/edi? |
|---|---|---|---|
| Block-scoped `{ int v = g; ... }` | After call | EAX | No |
| Function-scoped, load after call | After call | EAX | No |
| Function-scoped, load BEFORE call | Before call | ESI/EDI | Yes |
| Multiple loads before first call | Before calls | EDI + ESI | Yes |

The **only way to force callee-saved register allocation** is to make the
variable's live range cross a CALL instruction. Loading the value BEFORE a
`put_a_font_string` call and using it AFTER forces the allocator to pick
ESI/EDI/EBP.

The mechanism is the EAX-clobber crossing (Rule 89), and it **does** reproduce
in small test functions — see `regalloc-eax-boundary.py`, where the same value
flips EAX↔callee-saved purely on whether its range crosses the call.  Where PS
holds a value in a callee-saved register that our recomp keeps in EAX, PS's
source shaped the live range to span a call (directly, or via a CSE temp that
spans one); reshape the C the same way to match.

### 15.6 `MustSaveRegs` for Watcall Void Functions

`MustSaveRegs()` (`bld/cg/intel/c/x86reg.c:278`) computes which registers
must be saved if used. For a `void __watcall` function with no parameters:
- Starts with HW_FULL (all registers)
- Turns off `modify` set (empty for default watcall)
- Turns off parameter regs (none used)
- Turns off return reg (EAX)
- Turns off ESP

Result: **EBX, ECX, EDX, ESI, EDI, EBP** must all be saved if used.
This means ANY register other than EAX incurs a push/pop cost.

### 15.7 Flags and Switches That Affect Register Allocation

Searched exhaustively through the Open Watcom source for compiler flags,
pragmas, or switches that influence register selection beyond the core
allocator:

| Flag/Switch | Code path | Effect on regalloc | In 10.0a? |
|---|---|---|---|
| `-oh` | `CGSW_GEN_SUPER_OPTIMAL` | +2 bonus for non-callee-saved regs in `CountRegMoves`; enables expensive cross-temp analysis | **No** (E1074) |
| `-ok` | `CGSW_GEN_FLOW_REG_SAVES` | Affects `flowsave.c` (flow-based reg save/restore) | Untested |
| `-d2` | `CGSW_GEN_NO_OPTIMIZATION` | Skips `DeadInstructions`, `PropagateMoves`, `PropRegsOne`, `ReConstFold` inside `RegAlloc` after `SplitConflicts`; also skips entire `PreOptimize` (CSE, loop opts, etc.) | Yes |
| `-d1+`/`-d2` | `CGSW_GEN_DBG_LOCALS` | Calls `DBAllocReg()` — **a no-op stub** in the actual source | Yes |
| `-oa` | `CGSW_GEN_RELAX_ALIAS` | Sets `CST_OK_ACROSS_CALLS` for non-global, non-visible symbols — reduces reload costs in `CalcSavings` | Yes |
| `-ol` | `CGSW_GEN_LOOP_OPTIMIZATION` | Enables `LoopEnregister()` → `ConstToTemp()` — hoists constants into temps with `USE_IN_ANOTHER_BLOCK`, forcing callee-saved regs | Yes |
| `register` keyword | `SC_REGISTER` in front-end | Treated identically to `SC_AUTO` in codegen; no effect on allocator scoring | N/A |
| `#pragma aux` | Calling convention | Only affects callee's modify/parm/return sets, not internal variable allocation | Yes |

**Key finding**: No compiler flag or pragma exists in Watcom 10.0a that can
force a specific local variable into a particular register. The allocator's
choice is determined entirely by live range length, interference graph, and
`CountRegMoves` scoring. The only way to influence it is to change the C
source structure to extend live ranges across call sites.

### 15.8 File Locations Verified in Source Tree

| File | Verified | Notes |
|------|----------|-------|
| `bld/cg/c/regalloc.c` | ✅ 1365 lines | All functions confirmed at documented line numbers |
| `bld/cg/c/regsave.c` | ✅ | `CalcSavings()` at line 121 |
| `bld/cg/h/savcode.h` | ✅ 290 lines | Included by CalcSavings for cost/save computation |
| `bld/cg/intel/386/c/386rgtbl.c` | ✅ | `DoubleRegs` at line 288 |
| `bld/cg/intel/c/x86reg.c` | ✅ | `CallZap()` at line 259, `MustSaveRegs()` at line 278 |
| `bld/cc/c/coptions.c` | ✅ | `-oh` → `CGSW_GEN_SUPER_OPTIMAL` at line 683 |

---

## 16. Multiply Strength Reduction: IMUL vs Shift+Add

PS.EXE uses `shl`/`add`/`sub` chains for constant multiplies (e.g. ×10 =
`shl 2; add; add`). Our recomp uses `imul`. This is controlled by
`MulToShiftAdd()` in `bld/cg/c/multiply.c`, gated by `MulCost()` in
`bld/cg/intel/c/x86mul.c`.

### The `OptForSize` Gate

```c
// x86mul.c line 45
if( OptForSize > 50 )
    return( 1 );   // IMUL always preferred
```

`OptForSize` is set from the front-end:

| Flag | `OptSize` value | `OptForSize > 50`? | Strength reduction? |
|------|----------------|-------------------|--------------------|
| `-ot` | 0 | No | **Yes** — shift+add chains |
| (none) | 50 | No (50 > 50 is false) | **Yes** — shift+add chains |
| `-os` | 100 | **Yes** | **No** — IMUL always |

**PS.EXE uses shift+add chains, therefore it was NOT compiled with `-os`.**

However, `-ot` and default both generate `lea` instructions for some
multiplies (e.g. `lea ecx, [edx+edx*4]` for ×5), while PS.EXE uses
pure `shl`/`add`/`sub` without `lea`. This suggests either:
1. Watcom 10.0a's `lea` generation differs from the V2 source
2. The original used a specific combination that avoids `lea`
3. CPU target flags affect `lea` usage

### MulCost by CPU Target

| CPU | MulCost(10) | Typical shift+add cost for ×10 |
|-----|------------|-------------------------------|
| 8086 | 120 | ~20 → always reduce |
| 186 | 28 | ~15 → always reduce |
| 286 | 18 | ~15 → usually reduce |
| 386 | ~8 | ~11 → keep IMUL (cheaper!) |
| 486 | ~8 | ~7 → borderline |
| 586 | 6 | ~4 → reduce |
| 686 | 3 | ~4 → keep IMUL |

On 386 (`-3r`), IMUL is actually *cheaper* than shift+add for ×10
according to the V2 cost model. But PS.EXE still uses shift+add,
suggesting either the 10.0a cost tables differed or `OptForSize` was
different.

### 16.2 Optimization Sub-Flag Analysis

Each sub-flag was tested against PS.EXE byte diffs (formulae.c +
message.c, ~53 functions):

| Flag | Total byte diffs | vs baseline (9728) | Notes |
|------|----------------:|-------------------:|-------|
| `-d1` (baseline) | 9728 | — | |
| `-d1 -oa` | 9958 | +230 | Alias relaxation causes wrong register caching |
| `-d1 -ol` | 9719 | −9 | Loop enregistration helps `fill_cohort_centuries` (−59) |
| `-d1 -oi` | 9728 | 0 | No impact on tested functions (no memcpy in them) |
| `-d1 -oe=20` | 9767 | +39 | Inline expansion hurts |
| `-d1 -or` | 9938 | +210 | Instruction scheduling hurts |
| `-d1 -oz` | 9728 | 0 | No impact |
| `-d1 -ol -oi` | 9719 | −9 | Best combination |
| `-d1 -oa -ol -oi` | 9967 | +239 | `-oa` dominates negatively |

**Binary evidence for `-oi`**: PS.EXE contains 114 `rep movsd`/`rep movsb`
instructions (inlined memcpy) and 2 `rep stosd`/`rep stosb` (inlined
memset). Without `-oi`, these would be `call _memcpy`/`call _memset`.

**Binary evidence against `-or`**: Instruction scheduling reorders
instructions for pipeline efficiency, causing +210 byte diffs. PS.EXE
instruction ordering is consistent with no scheduling.

**Binary evidence against `-oa`**: Relaxed aliasing causes the compiler
to cache globals in registers across pointer stores. In
`set_current_cohort_totals`, this inflates diffs from 902 to 1050.

**Reconstructed flags**: `wcc386 -bt=dos -mf -3r -s -d1 -oi`
(possibly with `-ol` for loop-heavy modules).

---

## References

1. **Open Watcom V2 Developer Guide** (`docs/doc/devguide/tour.gml`) — pipeline
   architecture, in-house development history.
   <https://github.com/open-watcom/open-watcom-v2/blob/master/docs/doc/devguide/tour.gml>

2. **Open Watcom V2 Issue #784** — crash trace exposing `regalloc.c` call graph
   and internal structure of `AssignConflicts`, `GiveBestReg`, `NeighboursUse`.
   <https://github.com/open-watcom/open-watcom-v2/issues/784>

3. **AI analysis of Open Watcom codebase** (`8086_optimisations_report.md`) —
   source-level analysis of `regalloc.c` scoring functions, pipeline order,
   loop enregistration, `TooGreedy()`.
   <https://github.com/ggeorgovassilis/public/blob/master/open%20watcom/8086_optimisations_report.md>

4. **Agner Fog**, _Calling Conventions for Different C++ Compilers and Operating
   Systems_ — Watcom 32-bit callee-save register table (Table 4).
   <https://www.agner.org/optimize/calling_conventions.pdf>

5. **Wikipedia**, "Register allocation" — Chaitin-style graph-coloring phases,
   `out_of_block` vs `within_block` interference concepts.
   <https://en.wikipedia.org/wiki/Register_allocation>

6. **Wikipedia**, "x86 calling conventions" (Watcom section) — argument passing
   order (EAX, EDX, EBX, ECX); `#pragma aux` directive.
   <https://en.wikipedia.org/wiki/X86_calling_conventions>

7. **Wikipedia**, "Watcom C/C++" — historical context, BYTE review, game titles.
   <https://en.wikipedia.org/wiki/Watcom_C/C++>

8. **Computer History Wiki**, "Watcom C" — version 10.0 feature list.
   <https://gunkies.org/wiki/Watcom_C>

9. **Gered's Ramblings**, "Using Watcom's Register-based Calling Convention With
   TASM" — "save all used registers" rule, `#pragma aux` modify list.
   <http://blarg.ca/2018/04/16/using-watcoms-register-calling-convention-with-tasm>

10. **Frank Pfenning et al.**, _Lecture Notes on Calling Conventions_, 15-411:
    Compiler Design, Carnegie Mellon University — call-site interference edges,
    precolored register live ranges.
    <https://www.cs.cmu.edu/~janh/courses/411/23/lec/11-calling.pdf>

11. **Cooper, Dasgupta, Eckhardt**, "Revisiting Graph Coloring Register
    Allocation: A Study of the Chaitin-Briggs and Callahan-Koblenz Algorithms",
    LCPC 2005 / LLVM publications — 1990s graph-coloring allocator context.
    <https://llvm.org/pubs/2005-10-20-LCPC-RegAlloc.pdf>

12. **Open Watcom 1.9 C/C++ User's Guide** — `-d2` forces `-od`; `-d1` does not
    affect code quality; `-of`/`-of+` frame pointer options.
    <https://open-watcom.github.io/open-watcom-1.9/cguide.html>

13. **Open Watcom C/C++ Tools User's Guide V2.0** — WCL environment variable
    examples, `-d1` for line numbers only.
    <https://open-watcom.github.io/open-watcom-v2-wikidocs/ctools.pdf>

14. **Paul Hsieh's WATCOM C/C++ Programmer's FAQ** — `-d1` vs `-d2` code quality
    difference; `/otexan` recommendation.
    <https://www.azillionmonkeys.com/qed/watfaq.txt>
