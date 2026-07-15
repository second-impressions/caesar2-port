# Watcom 10.0 Code-Generation Patterns

A growing catalogue of code-generation rules discovered by matching
`PS.EXE` byte-for-byte against the output of Watcom C/C++ 10.0a with
`wcc386 -bt=dos -mf -4r -s`.

> **Looking for a starting point?**  This file is a *reference
> catalogue*, not a tutorial.  For a decision tree that maps
> observable symptoms (prologue divergence, rule-hint category) to
> specific levers, start at **`docs/watcom-regalloc-levers.md`**.
> For the underlying allocator theory, see
> **`docs/watcom-regalloc-research.md`**.

Each rule documents:

1. **What you see in PS.EXE** (the asm pattern Watcom emits)
2. **What you must write in C** to make the compiler emit it
3. **What the compiler emits if you write it the obvious way instead**
4. **Why** (where understood — Watcom's register allocator is a
   priority-based heap, and most rules are about steering it into the
   right pool)

## Auto-detected rules

`decomp-verify -v` runs `c2/commands/rule_hints.py` over each diff and
flags rows that match a known rule, printing a per-function histogram
below the diff table:

```
  Rule hints: 1× Rule 16, 2× Rule 8/23; 3 diff row(s) unexplained
```

Current auto-detected numbered rules include: **4, 5, 8/23, 9, 10,
12, 14, 16, 17, 19, 20, 24a, 24b, 26, 28, 28b, 29, 35, 35a, 37,
40, 43, 44, 49, 49b, 51, 53, 62, 72, 73, 78, 106, 110, 111** (the
byte-pattern-detectable set; 111 is a PS-vs-RC *differential* spill
classifier surfaced as the `Spill-class:` header — negative triage, not a
fix recipe). The remaining rules are semantic and need human/LLM
judgement to apply.  (Rule 107 — stack-slot size order — is deliberately
NOT auto-detected: stack-offset rows shift en masse on any frame/cascade
change, so a detector would be too noisy to be reliable.)

`decomp-verify -v` also has low-priority **regalloc-noise classifiers**
that are deliberately not numbered source rules because they usually
explain a residue rather than suggest a reliable fix:

* **Byte-reg swap** — same mnemonic/operand structure but different
  byte register identity (`bh` vs `dh`, `cl` vs `al`, etc.), including
  fixup-masked absolute-address rows.  This is the byte-register
  analogue of Rule 28a (first-use tie-break) — reorder which competing
  value is used first where the source allows.
* **Reg swap** — same idea for full/sub-word general registers
  (`eax` vs `edx`, indexed `edx + ebx*4` vs `ebx + edx*4`, etc.).
  This is intentionally lower-priority than actionable numbered rules.
* **Add/LEA copy** — one side mutates an adjusted pointer/index in place
  (`add esi, 0x374`) while the other computes a copy
  (`lea eax, [esi + 0x374]`) and uses that copy.  Usually a live-range
  / adjusted-pointer-temp choice, not a semantic mismatch.

When a diff row has no rule hint, the explanation is novel — worth
careful inspection. If you discover a new pure-byte-pattern rule or
noise classifier, add a detector to `rule_hints.py` and a regression
test to `tests/test_rule_hints.py`.

### Prologue-hint-detected rules (`c2/commands/pragma_hints.py`)

Some rules are about the prologue/epilogue **push set** rather than a
single diff row, so they are surfaced by the separate `Prologue hint:`
line in `decomp-verify -v` (and `functions[].pragma_hint` in `--json`):

* **edi↔ebp callee-save swap** — a `Callee-save SWAP: PS uses edi
  where RC uses ebp` hint has two known C-source levers, both about
  reducing pressure on the long-lived value so the allocator prefers
  edi over ebp: **Rule 1/63** (remove a cached local read multiple
  times — inline the reads; the cache's live range is what bumps the
  held value into ebp) and **Rule 87** (drop a spurious `else return;`
  on an unreachable dispatch case).  The hint text spells out both.
  Regression test: `tests/test_pragma_hints.py`
  `test_edi_ebp_swap_points_at_rule_87`.
* Other prologue categories (`ps_loadds`, `ps_stack_spill`,
  `ps_extra_callee_save`, generic `callee_save_swap` → Rule 28a, …) are
  documented in AGENTS.md § "Pragma / Prologue Hints".

---

## Rule 1 — Use a global twice inline rather than caching it in a local

### Symptom

PS.EXE saves and restores **EBX** as the register holding a global's
value across two uses; reasonable-looking C produces a save/restore
of **EDX** in the same role.

### Original (PS.EXE) — `do_promotion` at 0x55B1E

```asm
push ebx                       ; preserve EBX (caller-saved by watcall but
                               ;   used here as a stable value-holder)
mov  [game_state], 3
mov  ebx, [player_rank]        ; load global → EBX
cmp  ebx, 10
jge  .out
add  eax, ebx                  ; reuse EBX
cmp  eax, 10
jg   .out
mov  [player_rank], eax
.out:
pop  ebx
ret
```

### Wrong C (produces `push edx … pop edx`)

```c
void do_promotion(int level) {
    int rank;
    game_state = 3;
    rank = player_rank;            /* explicit local copy */
    if (rank < 10) {
        level += rank;
        if (level <= 10)
            player_rank = level;
    }
}
```

Watcom emits `mov edx, [player_rank]` and saves/restores **EDX**.

### Right C (produces `push ebx … pop ebx`, byte-identical to PS.EXE)

```c
void do_promotion(int level) {
    game_state = 3;
    if (player_rank < 10) {                 /* read global inline */
        level += player_rank;               /* read it again inline */
        if (level <= 10)
            player_rank = level;
    }
}
```

No local. The global appears textually twice. Watcom hoists the load
into a register itself, and chooses **EBX** for it.

### Mechanism

Under register `__watcall`, every general-purpose register is callee-saved,
so the function preserves whichever register its body writes to.  The
prologue saves `MustSaveRegs() & state.used`:

  * `MustSaveRegs()` (OW v1 `bld/cg/intel/c/i86reg.c:272`) returns
    `HW_FULL` minus `state.modify`, `HW_UNUSED`,
    `parm.used | return_reg` (unless `ROUTINE_MODIFY_EXACT`), and the
    stack register.  For a small leaf function this is
    `{EBX, ECX, EDX, ESI, EDI, EBP}`.
  * `state.used` accumulates every register the body actually writes,
    via `CalcUsedRegs()` (OW v1 `bld/cg/intel/c/i86proc.c`).

The two C formulations differ only in **which register holds the global**,
because they take two different allocation paths:

  * **Inline / CSE reads** are RISCified: the memory read is lowered to a
    register load whose register is chosen by `FindRegister`, the stateful
    rover over the type-class list (OW v1 `bld/cg/intel/c/i86ldstr.c`;
    10.0a wcc386 `0x62a29`, rover cursor `RoverDouble@0x80710` over
    `DoubleRegs@0x79850 = EAX,EDX,EBX,ECX,ESI,EDI,EBP,ESP`).  The value
    never becomes a `GiveBestReg` conflict — on 10.0a the inline form
    yields only the parm's `EAX` conflict, with the global read carried in
    the `fr` rover trace; the rover's pick (EAX excepted by the parm) lands
    on **EBX**.
  * **Named locals** route through the per-temp pipeline to `GiveBestReg`
    (OW v1 `bld/cg/c/regalloc.c`; 10.0a wcc386 `0x57b78`) over the same
    `DoubleRegs` list.  On 10.0a the named-local form yields a `GiveBestReg`
    allocation `EAX(savings 6) + EDX(savings 3)` — EAX taken by the parm,
    so the local lands on **EDX**.

`Reg64Order` (`386rgtbl.c:51`) is **not** the integer allocation order —
it is read only by `Low64Reg` (debug/64-bit-split support), never the
allocator.  The integer type class uses `DoubleRegs` for both paths.

Both formulations emit a `push reg / pop reg` pair of identical size;
only the chosen register differs.

### Verification

`tests/oracle/test_rule_01_inline_reads.py` (`uv run pytest`):

  * both forms compile to 36 bytes;
  * right form pushes EBX, caches in EBX, byte-shape matches
    PS.EXE’s `do_promotion`;
  * wrong form pushes EDX, caches in EDX.

### Implication for decompilation

When a single global appears in two or more expressions inside a small
function and PS.EXE shows `push ebx` (not `push edx`) in its prologue,
**do not introduce a local variable** for that global in the C source.
Read it inline at every use site. Watcom's CSE pass will hoist the
load and the resulting register selection will match.

Conversely, when PS.EXE shows `push edx` in the prologue with no
matching push of EBX, the original source almost certainly *did* use
an explicit local; reproduce it.

### Stronger form: *every* read must be inline

If the global is read more than twice and any one of the reads goes
through a local, the value-pool allocation collapses back to the temp
pool. The rule is all-or-nothing.

In `check_game_over` (0x55326), the original updates
`months_to_game_over` and reads it three times. The naive C version

```c
int x = months_to_game_over;
if (x == 0) ...
x--;
months_to_game_over = x;
if (x == 12) ...
if (months_to_game_over <= 0) ...     /* one inline read out of three */
```

produces `push ebx, edx, edi`, `dec eax`, `mov eax, [m32]` — the
temp-pool allocation. Removing the `x` local entirely

```c
if (months_to_game_over == 0) ...
months_to_game_over--;
if (months_to_game_over == 12) ...
if (months_to_game_over <= 0) ...
```

produces `push ebx, ecx, edx`, `lea ecx, [ebx-1]`, `mov ebx, [m32]`
— the value-pool allocation, byte-identical to PS.EXE.

The `lea ecx, [ebx-1]` form is particularly diagnostic: it appears
when the compiler considers the *pre-decrement* value still live in
EBX (a value-pool register) and so cannot use a destructive `dec`. It
materialises the new value in a separate temp register (ECX) via LEA.
This is wasteful in this function (the pre-decrement value is never
actually used again) but the allocator's liveness analysis is
conservative.

### Verified on

- `do_promotion` (0x55B1E) — exact byte match after rewrite
- `check_game_over` (0x55326) — 58 byte diffs → 0 codegen diffs
  (4 remaining bytes are call-displacement noise to `put_message`)
- `adjust_peace_criteria` (0x554FE) — indirectly applied via `+=`
- `xclip` / `yclip` (lib32.c, 0x27E54 / 0x27F20) — both byte-exact
  after replacing the obvious `int sx = sprite_x; int w = sprite_width;`
  preamble with inline reads at every reference.  Caching the params'
  globals into named locals caused Watcom to additionally callee-save
  the *parameter* (clip_left → ebx) which knock-on reshuffled every
  remaining register: a textbook Rule 28 swap (esi↔ecx) cascade
  triggered solely by the local cache.  Reading sprite_x / sprite_width
  inline at all four use sites lets CSE hoist them itself, and the
  parameter regs (eax/edx) stay live without callee-save spilling.
- Watcom version: 10.0 GA, 10.0a, 10.0b (codegen identical across
  these three; rule is unaffected by 10.5/10.6a as well)
- Compiler flags: `-bt=dos -mf -4r -s`

---

## Rule 3 — Two assignment statements to a global emit two stores

### Trigger

When PS.EXE shows *two* `mov [global], reg` instructions to the
same global spanning a compute (a divide, a clamp, a call), the
original C had two separate assignment statements:

```c
current_gdp = sum;          /* pre-compute store */
current_gdp /= 4;           /* post-compute store */
```

The single-statement form `current_gdp = sum / 4;` emits only the
final store — there’s only one assignment in the source.

The operator on the second statement doesn’t matter:

  * `current_gdp = sum; current_gdp /= 4;`
  * `current_gdp = sum; current_gdp = sum / 4;`
  * `current_gdp = sum; current_gdp = current_gdp / 4;`

all produce byte-identical output (same two stores, same intervening
divide).  What matters is two distinct assignment *statements* to
the same global.

### Right C — typical clamp shape

```c
current_gdp = sum;          /* store 1 */
current_gdp = sum / 4;      /* store 2 */
if (current_gdp > 60)
    current_gdp = 60;       /* store 3 (the clamp) */
```

Matches PS.EXE’s `adjust_proserity_criteria` at 0x557AF: three
`mov [current_gdp], …` instructions, exactly the shape above.

### Mechanism

`CheckUseful` (OW v1 `bld/cg/c/insdead.c:254`, the keep at `:283`; 10.0a wcc386
`0x5873d`) short-circuits whenever an instruction’s result is `N_MEMORY` or
`N_REGISTER`:

```c
if( res != NULL ) {
    if( res->n.class == N_MEMORY || res->n.class == N_REGISTER ) {
        change |= MarkOpsUseful( ins );
        return( change );
    }
    ...
}
```

The instruction is unconditionally marked useful; its operands
become `VISITED`; nothing in the dead-store-elimination pass will
remove it, even if a later instruction overwrites the same memory
before any read.  Compare to `N_TEMP` (named locals) which are only
kept when something downstream actually reads them.

This is conservative dead-store elimination: Watcom doesn’t try to
prove that no aliased pointer reads the global between the two
stores, so it preserves both.  Each C statement that writes to the
global becomes a `mov [global], reg` in the output; merging happens
only when the C source itself merges them into one statement.

### Cost

Each extra store is 6 bytes for a 32-bit global at a fixed address
(`a3 ?? ?? ?? ??` for `mov [imm32], eax`, or `89 0d ?? ?? ?? ??`
for `mov [imm32], ecx`, etc.).

### Verified on

  * `adjust_proserity_criteria` (0x557AF) — three-store clamp
     pattern reproduced exactly.
  * `tests/oracle/test_rule_03_pre_divide_store.py` — 5 passing
     assertions covering single/two-statement variants, plain vs
     compound second statement, and the +6-byte cost delta.
  * Watcom 10.0a, `-bt=dos -mf -4r -s`.

### Verified on

- `adjust_proserity_criteria` (0x557AF) — 93 byte diffs → all 30 bytes
  of the initial GDP computation exact-match; rest of function
  byte-identical modulo 1-byte shift from an unreproduced EBP
  allocation (see § Unexplained quirks).

### Unexplained quirk — "reserved EBP" in `adjust_proserity_criteria`

PS.EXE pushes `EBP` at the prologue, uses it *only* as
`xor ebp, ebp; mov [prosperity_rating_pop_limit], ebp` at the final
zero-store, then pops it. Recomp picks `EAX` for that store (legal,
1 byte shorter) and never touches `EBP`. The allocator decision is
not reproducible from the obvious C shape; it may require matching
register pressure in the original source that we have not yet
inferred. Shifts all post-call bytes by 1.

---

## Rule 2 — Pre-load a global into a named local before dividing

### Trigger

For `dst = g / k` where `g` is a global and `k` is a small constant,
Watcom 10.0a emits one of two divide setups:

  * **EDX-first** (PS.EXE’s shape): `mov edx, [g]; mov ebx, k; mov eax,
     edx; sar edx, 31; idiv ebx`.
  * **EAX-first**: `mov ebx, k; mov eax, [g]; mov edx, eax; sar edx,
     31; idiv ebx`.

The choice depends on what the divide-result temp is consumed by:

| C source                                                | Setup       |
|---------------------------------------------------------|-------------|
| `dst = g / k;`                                          | EDX-first   |
| `int r = g / k; dst = r; helper(r, 1);`                 | **EAX-first** |
| `int t = g; int r = t / k; dst = r; helper(r, 1);`      | EDX-first   |

When the result is consumed by a downstream call, Watcom’s
savings-sorted register allocator scores the EAX-first form better:
`mov eax, [imm32]` has the special 5-byte opcode `a1` (vs the
6-byte `mov edx, [imm32]` = `8b 15 …`).  The 1-byte saving wins,
and the dividend goes via EAX directly.

When the dividend is materialised into a named local first, that
local lands on EDX through `temps.c`’s per-temp pipeline regardless
of downstream pressure, and the divide reverts to EDX-first.  PS.EXE
always used this form, costing 1 byte but keeping the EDX-first
shape.

### Right C

```c
int t;
t = g;
result = t / k;
```

Matches PS.EXE’s `mov edx, [g]; mov ebx, k; mov eax, edx; sar edx,
31; idiv ebx`.

### Mechanism

`RG_DBL_DIV` (`bld/cg/intel/386/h/rg.h:62`,
`RG( RL_EDX_EAX, RL_DOUBLE, RL_EAX, RL_EDX, RL_, RG_DBL_DIV )`)
constrains the dividend to the `EDX:EAX` pair and the divisor to any
32-bit reg.  The divide optab routes a `(ANY, C)` dividend/constant-divisor
through `R_MOVOP2TEMP` (`bld/cg/intel/386/c/386table.c:685`) to load the
dividend into the pair.

Writing `int t = g;` as a separate statement materialises `t` as a named
temp, which becomes a conflict processed by the normal allocator —
`AssignConflicts` → `SortConflicts` → `GiveBestReg` (10.0a wcc386
`AssignConflicts@0x57f9c`, `GiveBestReg@0x57b78`), NOT the x87-only
`AssignARegister` (`regalloc.c:896`).  `GiveBestReg` walks `DoubleRegs`
(`EAX, EDX, EBX, ECX, ESI, EDI, EBP`); EAX is held by the divide result,
so the dividend temp takes **EDX**, locking the EDX-first shape.  The bare
`g / k` consumed by a downstream call instead scores the EAX-first form
because `mov eax, [imm32]` is the 5-byte `a1` opcode (vs 6-byte
`mov edx, [imm32]` = `8b 15`), a 1-byte saving that `GiveBestReg`'s
`CountRegMoves` rewards.

### Verified on

  * `adjust_peace_criteria` (0x554F3) — reduced from 61 byte-diffs
    to call-displacement noise.
  * `tests/oracle/test_rule_02_preload_dividend.py` — 5 passing
    assertions covering bare/inline/preloaded variants and the
    1-byte cost delta.
  * Watcom 10.0a, `-bt=dos -mf -4r -s`.

---

## Rule 4 — Watcom preserves `<` / `<=` / `>` / `>=` literally

### Trigger

Watcom 10.0a does not normalise relational operators.  The C source
operator picks both the comparison immediate and the Jcc opcode
byte-for-byte:

| C source     | Compare immediate | Branch (skip-body) |
|--------------|-------------------|--------------------|
| `x < 26`     | `cmp r, 0x1a`     | `jge skip`         |
| `x <= 25`    | `cmp r, 0x19`     | `jg  skip`         |
| `x > 25`     | `cmp r, 0x19`     | `jle skip`         |
| `x >= 26`    | `cmp r, 0x1a`     | `jl  skip`         |
| `x == 25`    | `cmp r, 0x19`     | `jne skip`         |
| `x != 25`    | `cmp r, 0x19`     | `je  skip`         |

`x <= 25` and `x < 26` are semantically equal but produce different
bytes; pick whichever form PS.EXE shows.

### Tooling: `Rule 4b` auto-detector (boundary inclusive/exclusive form)

`detect_rule_4b` (`c2/commands/rule_hints.py`) auto-flags the boundary
case that the plain Rule 4 detector misses.  It fires on an **aligned**
diff row that is `cmp R, imm` on both sides with the SAME first operand
but immediates differing by **exactly one**, AND whose following Jcc is
the inclusive/exclusive complement (`jle`↔`jl`, `jge`↔`jg`, plus the
unsigned `jbe`↔`jb` / `jae`↔`ja`).  That is the literal signature of
source written `x > N` where PS used `x >= N+1` (or `< N` vs `<= N-1`).
The Jcc-complement requirement rejects the desync artefact where the
verifier's aligner pairs two unrelated `cmp`s (those have mismatched
surrounding context and no complementary Jcc).  Found live in
`build_city_item` (`placing_type > 0x81 && < 0xa2` → PS's `>= 0x82 &&
<= 0xa1`, confirmed by the sibling `q_type` range checks).  NOTE:
Watcom canonicalises *some* signed `>`/`>=` pairs to identical bytes
(e.g. `pointer_mode > 5` ≡ `>= 6`), so the rewrite is only byte-moving
when the diff actually shows the off-by-one immediate — which is exactly
when the hint fires.  The fix is byte-neutral if masked by an earlier
regalloc cascade, but it is still the correct PS form and necessary for
eventual byte-exactness.  Tests: `tests/test_rule_hints.py`.

### Sub-pattern: `cmp reg, 0` → `test reg, reg`

For a *register-resident* operand compared against literal `0`,
Watcom emits `test reg, reg` (2 bytes) instead of `cmp reg, 0`
(3 bytes for `83 f8 00`).  Transform fires whenever the literal
numeric `0` appears in the source position — including `x < 0`
and `x >= 0`:

| C source  | Asm                      | Bytes |
|-----------|--------------------------|-------|
| `x > 0`   | `test eax, eax; jle`     | 4     |
| `x >= 1`  | `cmp eax, 1; jl`         | 5     |
| `x <= 0`  | `test eax, eax; jg`      | 4     |
| `x < 1`   | `cmp eax, 1; jge`        | 5     |
| `x == 0`  | `test eax, eax; jne`     | 4     |
| `x != 0`  | `test eax, eax; je`      | 4     |
| `x < 0`   | `test eax, eax; jge`     | 4     |
| `x >= 0`  | `test eax, eax; jl`      | 4     |
| `x > -1`  | `cmp eax, -1; jle`       | 5     |
| `x <= -1` | `cmp eax, -1; jg`        | 5     |

`x >= 1` (semantically `x > 0`) is encoded as `cmp eax, 1` because
the source literal is `1`, not `0`.  `x <= -1` (semantically
`x < 0`) is encoded as `cmp eax, -1` because the source literal is
`-1`.

The transform does **not** fire when op1 is a memory operand:
`cmp dword ptr [g], 0` stays as a memory compare.  Converting to
`test mem, mem` would require two memory reads and be longer.

### Mechanism

The front-end emits six distinct compare opcodes —
`OP_CMP_EQUAL`, `OP_CMP_NOT_EQUAL`, `OP_CMP_LESS`,
`OP_CMP_LESS_EQUAL`, `OP_CMP_GREATER`, `OP_CMP_GREATER_EQUAL`
(visible in `bld/cg/c/foldins.c:148`).  Each maps to a specific
Jcc encoding without any operator normalisation.

**Operand-swap interaction with Rule 9**: writing `if (b > a)`
produces semantically the same code as `if (a < b)` but with the
operands swapped in the cmp.  The mapping for this transformation
is **`RevBranch[]`** in `bld/cg/c/revcond.c:51-58` (“what to do to
a conditional if we reverse its operands”):

  * EQUAL↔EQUAL, NOT_EQUAL↔NOT_EQUAL (symmetric).
  * LESS↔GREATER, LESS_EQUAL↔GREATER_EQUAL.

So `cmp eax, edx; jl` (from `a < b`) and `cmp edx, eax; jg` (from
`b > a`) are the two `RevBranch[]` siblings of the same
relational test.  Bit-identical between OW v1.0.0 and OW v2
master.  Rule 9’s `FlipBranch[]` is the **negation** mapping;
this `RevBranch[]` is the **operand-swap** mapping.  The two are
distinct and both are observable in PS.EXE.

The cmp-vs-test selection is in the 32-bit compare optab `Cmp4` at
`bld/cg/intel/386/c/386table.c:1051`:

```c
_OE( _SidCC( R, C ), V_OP2ZERO, RG_DBL, G_TEST, FU_ALUX ),  // R, 0  → test
_OE( _SidCC( R, R ), V_NO,      RG_DBL, G_RR2,  FU_ALUX ),
_OE( _SidCC( R, M ), V_NO,      RG_DBL, G_RM2,  FU_ALUX ),
_OE( _SidCC( R, C ), V_AC_BETTER, RG_DBL_ACC, G_AC, FU_ALUX ),
_OE( _SidCC( R, C ), V_NO,      RG_DBL, G_RC,   FU_ALUX ),  // R, non-0
_OE( _SidCC( M, C ), V_NO,      RG_,    G_MC,   FU_ALUX ),  // M, C — no V_OP2ZERO
```

The `V_OP2ZERO` verifier (in `bld/cg/c/optab.c`) requires op2 to
be the integer constant 0.  It guards only the `R, C` row, so
memory operands always go through `G_MC`.  The `R, R` and `R, M`
rows have no zero-shortcut because there’s no shorter encoding
to switch to.

### Caveat

The `< 1 → <= 0` rewrite isn’t always a net win.  In
`get_new_tribute` (formulae.c), flipping two
`imperial_request < 1` and `imperial_review < 1` tests to `<= 0`
regressed 42 bytes because adjacent-instruction layout changed.
Apply only when the diff visibly shows `cmp reg, 1` and is
otherwise locally aligned.

### Verified on

  * `clear_army_from_fort_ref` (`0x2B3B3`) — 2 byte diffs → 0 by
     switching `army_no <= 25` → `army_no < 26`.
  * `put_message` (`0x5914C`) — 2 byte diffs → 0 by switching
     `free_message_ptr > 15` → `free_message_ptr >= 16`.
  * `random_event` (formulae.c): `stolen_denarii < 1` → `<= 0`
     yields the 4-byte `test eax,eax; jg` matching PS.EXE.
  * `tests/oracle/test_rule_04_operator_preservation.py` — 22
     parametrised assertions covering every operator + memory/reg
     operand + zero/non-zero immediate + the `cmp→test` cost
     delta (−1 byte).
  * Watcom 10.0a, `-bt=dos -mf -4r -s`.

## Rule 5 — Signed division by power-of-2 uses the `sar; shl; sbb` idiom

### Trigger

For signed `int x / 2^N` (N ≥ 2), Watcom 10.0a emits a branch-free
6-instruction sequence:

    mov  edx, eax        ; copy dividend
    sar  edx, 31         ; edx = 0 or -1 (sign bit broadcast)
    shl  edx, N          ; edx = 0 or -2^N; CF = sign bit of x
    sbb  eax, edx        ; eax += (2^N - 1) when x < 0; eax += CF
    sar  eax, N          ; arithmetic right-shift to divide

For signed `x / 2`, a special case (`By2Div`) saves one instruction:

    mov  edx, eax
    sar  edx, 31
    sub  eax, edx        ; eax += 0 or 1
    sar  eax, 1

For non-power-of-2 signed divides, the full `idiv` is emitted.

For unsigned `unsigned u / 2^N`, the front-end’s tree-fold rewrites
the divide to `u >> N` early, so the asm is just `shr reg, N`.

### Right C

Write the natural form when PS.EXE shows the idiom:

```c
factor = x / 8;
```

**Do not** rewrite as the portable if-bias form:

```c
factor = (x < 0 ? x + 7 : x) >> 3;     /* wrong */
```

The ternary-bias form compiles to a 5-instruction *branched* sequence
(`test edx, edx; jge; lea eax, [edx+7]; jmp; mov eax, edx; sar eax,
3`) — 1 byte longer than the idiom and structurally different.

### Mechanism

`FoldDiv` (OW v1 `bld/cg/c/treefold.c:670`, the unsigned-pow2 branch at `:724`)
handles the **unsigned** case early, before the optab:

```c
} else if( !_HasBigConst( tipe )
       && ( left->tipe->attr & TYPE_SIGNED ) == 0 ) {
    if( CFIsU32( rv ) ) {
        log = GetLog2( rite->u.name->c.int_value );
        if( log != -1 ) {
            fold = TGBinary( O_RSHIFT, left,
                          IntToType( log, TypeInteger ), tipe );
            BurnTree( rite );
        }
    }
}
```

Unsigned dividend + power-of-2 constant divisor → the divide tree is rewritten
as a right shift before reaching the back-end.  Signed dividends bypass this
fold.  `GetLog2` (10.0a wcc386 `0x51ac4`) returns `log2(value)` or `-1`.

For signed types, the optab `Div4` at `bld/cg/intel/386/c/386table.c:682-683`
selects between the two power-of-2 generators:

```c
_Bin( R, C, R, NONE ), V_OP2TWO,  G_DIV2,    RG_DBL_DIV, FU_IDIV,
_Bin( R, C, R, NONE ), V_OP2POW2, G_POW2DIV, RG_DBL_DIV, FU_IDIV,
```

`V_OP2TWO` matches divisor exactly == 2; `V_OP2POW2` matches any power-of-2.
The first row beats the second so `/2` gets the specialised `By2Div` sequence;
`/4`, `/8`, `/16`, … go through `Pow2Div`’s `sar/shl/sbb/sar` chain.

Byte-emitting code (OW v1 `bld/cg/intel/386/c/i86enc32.c`; 10.0a wcc386):

  * `Pow2Div` (`:848`; wcc386 `0x4f205`) — emits
     `shl edx,N; sbb eax,edx; sar eax,N` (opwords `0xe2c1`, `0xc21b`, `0xf8c1`),
     with a byte path (`0xe4c0 shl ah,n; 0xc41a sbb al,ah; 0xf8c0 sar al,n`)
     and a word path (dword opwords + `OpndSizeIf` 0x66 prefix).
  * `By2Div` (`:886`; wcc386 `0x4f2b9`) — emits
     `sub eax,edx; sar eax,1` (opwords `0xc22b`, `0xf8d1`).

Both assume the leading `mov edx, eax; sar edx, 31` setup is already in place
(emitted by the `RG_DBL_DIV` register-pair load).

### Context-sensitivity caveat

The idiom reliably fires for plain assignments `dst = src / N`.
When the divide appears as a function-call argument, Watcom may
pick a different layout: in `random_event` at the
`totalXpercent(…, pct)` call site (formulae.c line 1207), `x / 4`
regressed 188 bytes while the portable ternary form
`(x < 0 ? x + 3 : x) >> 2` matched via peephole.  When a divide is
inside a call argument and already produces sar-shl-sbb in the
diff, leave it as the ternary form.

### Verified on

  * `get_industry_growth_factor`, `pop_growth_factor`, two of the
     three division sites in `random_event`.
  * `tests/oracle/test_rule_05_signed_pow2_divide.py` — 13 tests:
     parametrised over `/4 /8 /16 /32` (sar-shl-sbb), `/2`
     (By2Div), `/3` (idiv fallback), unsigned `/2 /4 /8 /16` (shr),
     ternary-bias produces a branch, idiom is 1 byte shorter
     than ternary-bias for `/8`, `/2` is 4 bytes shorter than `/4`.
  * Watcom 10.0a, `-bt=dos -mf -4r -s`.

## Rule 5b — PS uses a bare arithmetic shift where source has `/ 2^N`

### Trigger (the *inverse* of Rule 5)

Rule 5 covers the case where PS.EXE emits the `sar; shl; sbb` idiom and
the source should be a plain `x / 2^N` divide.  **Rule 5b is the opposite**:
PS emits a *single bare* `sar reg, N` (or `shr reg, N`) with **no
sign-correction**, but the recompile emits the full idiom.

```
PS :  sar  edx, 4                          ; floor-divide by 16
RC :  mov eax,edx; sar edx,0x1f; sar eax,4; ...   ; truncating /16 idiom
```

A bare `sar reg, N` only comes from a **source-level shift** (`x >> N`),
never from a `/ 2^N` divide: signed `/` must round toward zero, so Watcom
always inserts the sign-bias correction for a divide.  If PS has the bare
shift, the original source wrote `x >> N`, and our decompile wrote
`x / 2^N`.

### Right C — use the shift

```c
ref_x = p->x >> 4;          /* PS form: bare `sar` / `shr` */
/* NOT:  ref_x = p->x / 16;  — emits the truncating idiom */
```

This is the floor-division semantics PS intended; the original C source
used `>>` because the values are non-negative coordinates / counters and
the author wrote the cheap shift directly.

### Mechanism

For signed `int`, `/ 2^N` must satisfy C's round-toward-zero rule, so the
back-end emits the `sar 31; shl N; sbb; sar N` bias sequence (or the
`By2Div` 4-insn special case for `/2`).  `x >> N` on a signed `int` lowers
to a single arithmetic `sar reg, N` (Watcom does not add bias — shift is
defined as arithmetic).  So the *operator in the source* (`/` vs `>>`)
selects the idiom directly; this is purely a source-shape lever, not a
type or flag issue.

### When it applies (and when NOT)

* **Applies** when the divide is *isolated* and the value is non-negative
  by construction (screen coords, counts, indices).  The shift is the
  faithful PS form.
* **Does NOT apply** when the divided value shares its load with a sibling
  `& (2^N - 1)` parity test — e.g. `wf_steps[wf_step / 2]` next to
  `if (wf_step & 1)`.  PS computes `wf_step/2` and `wf_step&1` from one
  loaded byte; rewriting only the `/2` to `>>1` reshapes the shared
  live range and *regresses* the function.  Leave those as `/ 2`.

### Verified on

  * `adjust` (controls.c): `(x+0x64)/16, (y+0x22)/16` → `>> 4` closed
    73 b → 2 b (residual is an esi↔edi tie-break).
  * `de_toggle_all_icons` (controls.c): `p->x/16, p->y/16` → `>> 4`
    collapsed 98 b → 2 b, then dropping the pointer alias closed it to 0.
  * Counter-example (regressed, reverted): `get_dirc_from_army_wf_run` /
    `get_dirc_from_citizen_wf_run` — `wf_step/2` shares its load with
    `wf_step & 1`; `>>1` took them 68 b → 91 b and 70 b → 88 b.

### Tooling

`c2 decomp-verify -v` flags this as **`Rule 5b`** ("recomp uses
sar/shl/sbb signed-div idiom; PS uses a bare shift OR a shared-divisor
idiv") with both fixes and the parity-sibling caveat.  Same detector as
Rule 5 (`detect_rule_5` in `c2/commands/rule_hints.py`), inverse branch.

**False-positive guard (2026):** `sar reg, 31` starts the shift idiom but
is ALSO the cdq-equivalent sign-extension before a hardware `idiv`
(`mov edx,src; sar edx,31; idiv divisor`).  `detect_rule_5` now suppresses
the hint when the `sar 31` is immediately followed by `idiv`/`div` (it is
just sign-extension, not the idiom).  Without this, any function using a
real `idiv` (every `x % 2^N` — MOD has *no* power-of-2 reduction, see
below) produced spurious Rule 5/5b hints once a size shift misaligned the
two instruction streams (e.g. `get_region_2x2_start` reported `2x Rule 5,
2x Rule 5b` that were pure misalignment noise — PS uses `idiv` for both
its `%2` and `/2`, not a bare shift).

## Rule 5c — adjacent `% 2^N` and `/ 2^N` share the divisor → both `idiv`

### Trigger

PS emits a hardware `idiv` for a `/ 2^N` that would *normally*
strength-reduce to a shift (Rule 5/G_DIV2), because an **adjacent
`% 2^N`** on the same value forces the divisor into a shared temp:

```
PS :  mov edi, 2                      ; divisor 2 materialised in a TEMP
      mov eax,esi; mov edx,esi; sar edx,31; idiv edi   ; col = code % 2
      mov eax,ecx; mov edx,ecx; sar edx,31; idiv edi   ; row = code / 2  ← idiv, not shift
RC :  mov esi,2; ...; idiv esi        ; col = code % 2  (idiv — MOD has no pow2 rule)
      mov edx,ebx; sar edx,31; sub eax,edx; sar eax,1  ; row = code / 2  ← G_DIV2 shift
```

### Mechanism (source-proven, `bld/cg/intel/i86/c/i86table.c`)

The integer `DIV` rule table has, in order, `V_OP2TWO → G_DIV2`
(divide-by-2 special), `V_OP2POW2 → G_POW2DIV` (general power of 2), then
the fall-through `R_MOVOP2TEMP → idiv`.  The **`MOD` table has *no* pow2
rule at all** — `% 2^N` always falls through to `R_MOVOP2TEMP` (move the
divisor to a register) + `idiv`.

`V_OP2TWO` / `V_OP2POW2` (`bld/cg/c/verify.c`) only pass when **op2 is a
literal `CONS_ABSOLUTE` constant**.  When the `% 2^N` materialises the
divisor `2^N` into a temp register and CSE shares that temp with the
adjacent `/ 2^N`, the divide's op2 is no longer a constant → `V_OP2TWO`
**fails** → the divide also falls through to `idiv`.  So both operations
share one `idiv divisor` register.

Whether the CSE actually shares the divisor temp is **context-dependent**
(register pressure / CSE sharing): the *same source* can emit
the shift form (`G_DIV2`) in one build and the shared-idiv form in
another.  This is a CSE/register-pressure divergence, not always
reproducible by a local source edit.  Confirmed on
`get_region_2x2_start`: PS shares the divisor (`mov edi,2` + two `idiv
edi`); our build strength-reduces the `/2` to `G_DIV2`.  A bare `x >> 1`
is **wrong** here (PS does a real signed `idiv`); forcing the divisor into
a variable (`int two = 2; col = code % two; row = code / two;`) makes both
`idiv` but did not close the function (the dominant residue is a separate
`cm_ptr` callee-save register cascade, not the divide).

### When it applies

Only when a `% 2^N` and `/ 2^N` of the **same value** sit adjacent.  Read
the PS disasm: if PS shows `idiv` for the `/`, match it (do **not** apply
Rule 5b's `>> N`).  If PS shows the shift idiom, the divisor was *not*
shared — leave the divide as `/ 2^N`.

## Rule 6 — Split compound division into two assignment statements

### Trigger

This is **Rule 3 applied to chained divides**.  When PS.EXE shows
two `idiv` instructions with an intermediate store between them:

    idiv ebx              ; first divide
    mov  [estimate], eax  ; <- intermediate store
    mov  ebx, 100
    ...
    idiv ebx              ; second divide
    mov  [estimate], eax  ; final store

the source was written as two assignment statements:

```c
estimate = projected / 12;       /* store 1 */
estimate /= 100;                 /* store 2 */
```

The operator on the second statement doesn’t matter —
`estimate = estimate / 100;` produces byte-identical output to
`estimate /= 100;`.  What matters is two distinct C statements
storing to the global.

The single-expression form `(projected / 12) / 100` chains the
divides in registers and emits only **one** final store.

### Mechanism

See Rule 3.  `CheckUseful` (`bld/cg/c/insdead.c:283`; wcc386 `0x5873d`) marks any
instruction with `N_MEMORY` result as unconditionally useful, so
each assignment statement to the global survives as a `mov [imm32],
reg` regardless of whether a later store overwrites it.  Each extra
store costs +6 bytes (`a3` or `89 0d` opcode + 4-byte fixup).

### Verified on

  * The four `*_tax_estimate` / `collect_*_tax` functions in
     formulae.c.
  * `tests/oracle/test_rule_06_split_compound_division.py` — 5
     tests: single expression → 1 store; two statements with `/=`
     → 2 stores; two statements with plain divide → 2 stores;
     byte-equivalence between the two two-statement forms; +6
     byte cost delta.
  * Watcom 10.0a, `-bt=dos -mf -4r -s`.

## Rule 7 — Source order of global stores is preserved verbatim

### Trigger

When a value flows into both a global and a callee-saved register
(for use after a downstream call), the order of those two writes
in the asm follows the C source order:

```c
peace_rating = t / 10;          /* statement 1 */
orig         = peace_rating;    /* statement 2 */
adj = helper(orig, 1);
flag = (orig > adj);            /* orig live across call → EBX */
```

emits

    mov  [peace_rating], eax    ; statement 1
    mov  ebx, eax                ; statement 2 (orig in EBX)
    ...
    call helper

while

```c
orig         = t / 10;
peace_rating = orig;
adj = helper(orig, 1);
flag = (orig > adj);
```

emits

    mov  ebx, eax                ; now first
    mov  [peace_rating], eax    ; now second
    ...
    call helper

The two pairs are equivalent in semantics; PS.EXE picked one
specific order, and matching it is just writing the C statements
in the same order.

### Mechanism

This is a direct consequence of Rule 3.  The C front-end’s
`CGAssign` (OW v1 `bld/cg/c/intrface.c:911`; 10.0a wcc386 `0x2ef2c`) is called for each `=`
statement in source order; each call appends one IR instruction
whose result is the destination.  No general reordering pass
exists for instructions with side effects, so the two stores
remain in source order through the back-end.

The reason both stores survive (rather than the first being
dead-store-eliminated) is the same as Rule 3:
`bld/cg/c/insdead.c:283` (wcc386 `0x5873d`) unconditionally marks any instruction
with `N_MEMORY` or `N_REGISTER` result as useful.  Both the global
store and the EBX-cache stay alive.

### Verified on

  * `adjust_peace_criteria` (0x554F3) — PS.EXE’s order is
     `mov [peace_rating], eax; mov ebx, eax`, matching the
     global-first source form.
  * `tests/oracle/test_rule_07_global_store_order.py` — 4 tests:
     global-first emits store-then-save; local-first emits
     save-then-store; both forms have the same store/save count;
     size delta is ≤ 1 byte (Rule 2’s EAX-vs-EDX cost-model swap).
  * Watcom 10.0a, `-bt=dos -mf -4r -s`.

### Sub-pattern: local zero-init `xor reg, reg` order

The same source-order rule applies to **register-resident
locals** initialised to 0.  When a function declares two
locals that both end up in callee-save registers, the order
of the emitted ``xor reg, reg`` pair follows source declaration
order — *not* register-name order or alphabetic name order.

Example (`get_new_sslot` 94 b @ 0x12953)::

    /* Source A — best first */
    int best  = 0;     /* → esi (callee-save) */
    int max_c = 0;     /* → ecx (callee-save) */
    /* RC emits:  xor esi, esi  ;  xor ecx, ecx  */

    /* Source B — max_c first */
    int max_c = 0;
    int best  = 0;
    /* RC emits:  xor ecx, ecx  ;  xor esi, esi  */

PS at this offset emits ``xor ecx, ecx; xor esi, esi``, so
**source B is the byte-exact form**.  The mechanism is
`bld/cc/c/cstmt2.c::CDecl1Init` issuing one `CGAssign` per
local in source order; same code path as Rule 7's stores.

Detection hint: when comparing recomp vs PS, look at the
register-init prologue — a swapped pair of adjacent
``xor reg, reg`` instructions is almost always a declaration
re-order in the C source.

## Rule 7b — Split `+=1` from the add to get `inc reg` + load/add/store

### Trigger

The four-instruction read-modify-write

    inc   reg                   ; +1 of a local
    mov   r2, [global]          ; load destination
    add   r2, reg               ; fold in the increment
    mov   [global], r2          ; store

is emitted by **two** assignment statements:

```c
growth_amt++;
slaves += growth_amt;
```

The single-expression form

```c
slaves = slaves + growth_amt + 1;
```

emits the more compact three-instruction sequence

    add   reg, [global]         ; absorbs the load
    inc   reg
    mov   [global], reg

saving 4 bytes total: the explicit `mov reg, [m]` + register-to-
register `add reg, reg` becomes a single `add reg, [m]`
(`G_RM2`, 6 bytes), and the split form’s use of a callee-saved
register for the load destination triggers a `push ebx; pop ebx`
pair which the fused form avoids.

The rule is the inverse of Rule 7: there, two statements match
PS.EXE; here, **one** expression matches PS.EXE’s compact form.
Read the diff to decide:

  * `inc reg; mov r2,[m]; add r2,reg; mov [m],r2`  → two C statements.
  * `add reg,[m]; inc reg; mov [m],reg`            → one C expression.

### Mechanism

Watcom emits each `=` statement as its own IR sequence via
`CGAssign` (`bld/cg/c/intrface.c:911`).  The optimizer doesn’t
merge IR across statement boundaries, so the second statement’s
load+add can’t pick up the just-incremented value as a free side
input.

The fused single-expression form reaches the back-end as one IR
tree.  The optab `Add4` at `bld/cg/intel/386/c/386table.c:141`
matches `(R, M, R, EQ_R1)` with `G_RM2`, emitting the compact
`add reg, [m]` form.

### Verified on

  * `slave_welfare` (formulae.c).
  * `tests/oracle/test_rule_07b_inc_separate_from_add.py` — 4
     tests: split form has separate load + register-only add;
     fused form has memory-operand add; fused is exactly 4 bytes
     shorter; split pushes EBX while fused doesn’t.
  * Watcom 10.0a, `-bt=dos -mf -4r -s`.

## Rule 10 — Staged global RMW instead of a single fused sum

### Trigger

When PS.EXE emits a chain of memory-touching writes to the same
global:

    mov   [global], reg              ; first partial
    add   [global], otherreg         ; subsequent partials hit memory
    add   [global], otherreg         ; ...

the source used staged read-modify-write on the destination:

```c
prosperity_rating  = pop_cap / 60;
prosperity_rating += current_gdp;
prosperity_rating += rolling_profit / 200;
```

The single-expression form

```c
prosperity_rating = pop_cap / 60 + current_gdp + rolling_profit / 200;
```

accumulates in a callee-saved register and emits only **one**
final `mov [global], reg`.

This is Rule 7b generalised to N partials: each `+=` statement
that survives statement boundaries becomes a separate `add [m], reg`
in the asm.

### Mechanism

Same chain as Rules 3 / 7 / 7b composed:

  * `CGAssign` (`bld/cg/c/intrface.c:911`) emits one IR sequence
     per `=` statement; no merging across statement boundaries.
  * Each `+=` statement matches `Add4` row
     `(M, R, M, EQ_R1) → G_MR2`
     (`bld/cg/intel/386/c/386table.c:142`), emitting
     `add [m], reg`.
  * `CheckUseful` (`bld/cg/c/insdead.c:283`) keeps every
     `N_MEMORY` write alive.

The fused form reaches the back-end as one IR tree; the back-end
allocates an accumulator register and emits register-to-register
adds with one final store, sparing N−1 of the memory RMW ops.

### Cost

For 3 statements collapsing to 1 expression: −5 bytes net.
Each replaced `add [m], reg` (6 bytes) becomes `add reg, reg`
(2 bytes) saving 4 bytes per RMW; the fused form needs one extra
final `mov [m], reg` (6 bytes) and may push an extra callee-saved
register (+2 bytes); plus a 1-byte Rule 2 EAX-vs-EDX shift.

### Verified on

  * `adjust_proserity_criteria` (formulae.c).
  * `tests/oracle/test_rule_10_staged_global_rmw.py` — 5 tests:
     staged form emits 3 memory writes (1 mov + 2 RMW adds);
     fused form emits 1 memory write; staged uses
     `add [m], reg` form; fused uses register-to-register adds;
     fused is smaller.
  * Watcom 10.0a, `-bt=dos -mf -4r -s`.

## Rule 11 — Pre-increment + cache pattern for loop sentinels

### Trigger

When a loop body initialises ``best_val`` from ``cur_val`` and the
post-search check is “did the inner search find anything better?”,
PS.EXE uses the pre-incremented primary as both the sentinel and
the tie-detection comparand:

```c
cur_val++;                  /* pre-increment */
best_val = cur_val;
inner_search(&best_val);    /* may shrink best_val */
if (best_val == cur_val) return 0;
cur_val = best_val;
```

The fused alternative

```c
best_val = cur_val + 1;
inner_search(&best_val);
if (best_val == cur_val + 1) return 0;
cur_val = best_val;
```

is semantically equivalent (when ``cur_val`` isn’t read elsewhere)
but produces longer asm because the comparison
``best_val == cur_val + 1`` recomputes ``cur_val + 1`` at compare
time.  C’s integer promotion rules force the comparison to int
width (one operand is `int`), so the fused form gains 32-bit
zero-extends + a 32-bit cmp instead of the pre-increment form’s
plain 8-bit `cmp dl, ah`.

### Mechanism

Same chain as Rules 7 / 7b / 10: each `=` statement is its own
IR sequence (`CGAssign` at `bld/cg/c/intrface.c:911`); no merging
across statement boundaries.  ``cur_val++`` materialises
``cur_val`` in a register at its incremented value; the next
statement’s ``best_val = cur_val`` and the later
``best_val == cur_val`` reuse that already-resident value.

The fused ``cur_val + 1`` produces a temp expression each time
it appears.  At the comparison site the temp must be recomputed
because the original ``cur_val`` wasn’t modified.  The C
standard’s integer-promotion rule forces the recomputation to
be at int width, dragging in zero-extends.

### Verified on

  * `trace_back_ferret` (common.c).
  * `tests/oracle/test_rule_11_preinc_cache_loop_sentinel.py` —
     4 tests: pre-increment form uses 8-bit `cmp`; fused form
     uses 32-bit `cmp` after zero-extending both sides;
     pre-increment saves ≥ 4 bytes; pre-increment emits exactly
     one `inc` (the fused form has an inc too, but for the
     temp `+1`, not the cur_val update).
  * Watcom 10.0a, `-bt=dos -mf -4r -s`.

## Rule 8 — `char` defaults to **unsigned** on Watcom 10.0a

### Trigger

Plain `char` (no explicit `signed`/`unsigned` qualifier) behaves
as `unsigned char`:

  * Reading a `char` global/field widens via zero-extend
    (`xor reg, reg; mov rl, [m]`, or `mov rl, [m]; and reg, 0xff`).
  * Reading a `signed char` global/field widens via sign-extend
    (`movsx reg, byte ptr [m]`).
  * Reading an `unsigned char` is byte-identical to plain `char`.

If the diff shows `movsx` where the recomp emits `xor + mov`, the
original field was declared `signed char` (explicit).

### Parameter spilling

Watcom’s `__watcall` passes 1-byte parms in the 8-bit halves of
the parm-pass registers (AL, DL, BL, CL).  When the parm’s address
is taken, or it must survive a downstream call, it spills:

| Parm declaration  | Spill                                  | Reload                                |
|-------------------|----------------------------------------|---------------------------------------|
| `char`            | `mov byte ptr [esp+N], al`             | `xor eax, eax; mov al, byte ptr ...`  |
| `unsigned char`   | identical to `char`                    | identical                             |
| `signed char`     | `mov byte ptr [esp+N], al`             | `movsx eax, byte ptr [esp+N]`         |
| `int` (1 parm)    | `push eax`                             | `mov eax, dword ptr [esp]`            |
| `int` (2nd parm)  | `mov dword ptr [esp+N], edx`           | `mov edx, dword ptr [esp+N]`          |

When PS.EXE shows `mov dword ptr [esp+N], edx` for a parm spill,
the parm was declared `int`, not `char`.  Promote `char X` parms
to `int X` when the diff shows that shape.

### Casting caveat

`(char)x` in source forces the default unsigned promotion, even if
the underlying field is `signed char`.  Drop the cast and rely on
natural integer promotion if a `movsx` is wanted.

### Mechanism

`SetPlainCharType(TYP_UCHAR)` in `bld/cc/c/ctype.c:131` is the
default.  The `-j` flag flips it via `SetSignedChar()`
(`bld/cc/c/ctype.c:218`), which calls
`SetPlainCharType(TYP_CHAR)`.  Character constants are typed by
`bld/cc/c/cscan.c:1439-1450`: without `-j` they’re `TYP_UCHAR`;
with `-j` they’re `TYP_CHAR` (narrowed from 0…255 to -128…127).

PS.EXE was compiled **without** `-j`: applying `-j` globally
regresses the byte-match score.  Express signed-char fields
explicitly per-field.

### Caveat

The rule is **per-field / per-parameter**.  A blanket
`char -> signed char` sweep regresses the score in functions that
use `char` fields the natural unsigned way.  Apply only where the
diff visibly shows `movsx` mismatch.

### Verified on

  * `get_nearest_enemy_to_track` (dropped `(char)` casts on
     `.type`).
  * `get_army_name_from_fort_ref` (struct `army_rec.name` →
     `signed char`, dropped `(int)(char)` cast).
  * `create_arrow` (struct `arrow_rec.grid_x` / `.grid_y` →
     `signed char`; dropped `(char)` casts; param `char arrow_type`
     → `int`).
  * `create_unit` (3 char params → int).
  * `tests/oracle/test_rule_08_char_unsigned_default.py` — 9
     tests: plain/unsigned/signed char globals; plain/signed/int
     parm spills (single + multi-parm); reload patterns; byte-
     identity between plain `char` and `unsigned char`.
  * Watcom 10.0a, `-bt=dos -mf -4r -s` (no `-j`).

## Rule 9 — if-body fall-through layout; equivalent forms swap the Jcc

### Trigger

Watcom 10.0a always emits the if-body **immediately after the
conditional jump** (so the if-body is the fall-through path) and
the else-body at the forward target.  This holds regardless of
the relational operator and regardless of relative branch sizes.
The Jcc opcode is the *negation* of the C test (because the Jcc
skips the if-body to reach the else):

| C test       | Jcc (skip if-body)  |
|--------------|---------------------|
| `x == 0`     | `jne forward`       |
| `x != 0`     | `je forward`        |
| `x == N`     | `jne forward`       |
| `x != N`     | `je forward`        |
| `x < N`      | `jge forward`       |
| `x <= N`     | `jg forward`        |
| `x > N`      | `jle forward`       |
| `x >= N`     | `jl forward`        |

The negation table is **`FlipBranch[]`** in
`bld/cg/c/revcond.c:42-49`.  Two distinct transformations live in
that file:

  * **`FlipBranch[]`** — “what to do to a conditional if we
     **complement (!) it**.”  EQUAL↔NOT_EQUAL, LESS↔GREATER_EQUAL,
     LESS_EQUAL↔GREATER.  This is **Rule 9**.
  * **`RevBranch[]`** — “what to do to a conditional if we
     **reverse its operands**.”  EQUAL↔EQUAL (symmetric),
     LESS↔GREATER, LESS_EQUAL↔GREATER_EQUAL.  This is **Rule 4**
     (operand-swap with operator preservation).

The two tables are bit-identical in OW v1.0.0 (the very first
open-source release, 2003) and OW v2 master.

### Matching PS.EXE

The semantically-equivalent forms

```c
if (cond)  { A; } else { B; }
if (!cond) { B; } else { A; }
```

produce different bytes: the Jcc is `FlipBranch[cond]` in the first
form and `FlipBranch[!cond]` in the second, and the bodies appear
in opposite order in memory (if-body is always first).  For
inequality this means:

  * `if (a < b) X(); else Y();`   →   `cmp; jge ELSE; X(); jmp end; ELSE: Y(); end:`
  * `if (a >= b) Y(); else X();`  →   `cmp; jl ELSE;  Y(); jmp end; ELSE: X(); end:`

Pick the form whose Jcc matches PS.EXE:

  * PS shows `jne` → source had `if (x == 0) { A } else { B }`.
  * PS shows `je`  → source had `if (x != 0) { B } else { A }`.
  * PS shows `jge` → source had `if (a < b)  { A } else { B }`.
  * PS shows `jl`  → source had `if (a >= b) { B } else { A }`.
  * PS shows `jg`  → source had `if (a <= b) { A } else { B }`.
  * PS shows `jle` → source had `if (a > b)  { B } else { A }`.

### Mechanism

1. The C front-end emits one `OP_CMP_*` IR per source-level test
   (`bld/cg/c/foldins.c:148` enumerates the six relational ops:
   `OP_CMP_EQUAL`, `OP_CMP_NOT_EQUAL`, `OP_CMP_LESS`,
   `OP_CMP_LESS_EQUAL`, `OP_CMP_GREATER`, `OP_CMP_GREATER_EQUAL`).
2. The block-layout pass keeps the if-body contiguous with the
   conditional jump’s fall-through; the else-body becomes a
   forward block ending in a join label.
3. **`DoCondJump`** at `bld/cg/c/encode.c:131-180` (v1.0) /
   `:144-198` (v2) reads `dest_true` and `dest_false` from the
   IR.  When `dest_true == dest_next` (i.e. the if-body is the
   next basic block in layout), it calls `FlipCond(cond)` and
   emits a Jcc to the now-`dest_true` (originally the else):

   ```c
   if( dest_true == dest_next && dest_false != NULL ) {
       FlipCond( cond );          /* opcode -> FlipBranch[opcode] */
       dest_true = dest_false;
       dest_false = dest_next;
   }
   /* emit Jcc to dest_true */
   ```

4. The 386 emit layer (`bld/cg/intel/386/c/386table.c:Cmp4`)
   selects the byte encoding for the (possibly-flipped) opcode.

No source-level operator normalisation happens.  The Jcc you
observe in PS.EXE is `FlipBranch[<source operator>]`, period.

### Verified on

  * `create_citizen` (common.c) at sites L67 and elsewhere —
     PS.EXE shows `je forward` for what semantically is “is_barb
     is zero”, confirming the source used the inverted form
     `if (is_barb != 0) { B } else { A }`.
  * `cd_path` (lib32.c, 0x2426E) — four `strcmp(ext, …) == 0`
     terms feeding a single `matched = 0` body.  PS emits
     `je <shared_label>` at every term (jump-on-match into a
     forward `xor ebx, ebx`); the natural per-strcmp form
     `if (strcmp(...)==0) matched = 0;` emits `jne next; xor ebx,
     ebx; next:` — same semantics, **opposite Jcc** at each test
     and an inserted xor between every pair.  Folding the four
     terms into one `||` chain
     (`if (s1==0 || s2==0 || s3==0 || s4==0) matched = 0;`) lets
     Watcom layout the body as a single fall-through after the
     last term and route the earlier matches to it via forward
     `je`s — matching PS's bytes (modulo a residual Rule 28 swap
     on the matched-flag/buffer-pointer regalloc).
  * `tests/oracle/test_rule_09_if_else_layout.py` — 24 tests:
     each of 8 operator forms picks a specific inverted Jcc; the
     if-body is the fall-through in each case; equivalent
     `==`/`!=` forms swap the Jcc; layout is independent of branch
     sizes; **all three FlipBranch pairs** (`==/!=`, `</>=`,
     `<=/>`) produce complementary Jccs of equal byte size when
     bodies are swapped.
  * **OW source cross-check**: `bld/cg/c/revcond.c` and
     `bld/cg/c/encode.c` are bit-identical between OW v1.0.0
     (2003) and OW v2 master — the Rule 9 mechanism is stable
     across the whole open-source history of the toolchain.
  * Watcom 10.0a, `-bt=dos -mf -4r -s`.

## Rule 4 expansion — cmp-imm encoding details


Check the Jcc mnemonic in the disassembly and the immediate in the
preceding `cmp`:

| PS.EXE asm            | Original C |
|-----------------------|------------|
| `cmp r, N;  jl  L`    | `x < N`    |
| `cmp r, N-1; jle L`   | `x <= N-1` |
| `cmp r, N;  jg  L`    | `x > N`    |
| `cmp r, N+1; jge L`   | `x >= N+1` |

The two columns collapse to the same integer semantics; only the
byte pattern differs.

---

## Rule 27 — Instruction-pair reorder via parm-alias toggle

*(Closely related to Rule 24 — same regalloc-priority mechanism;
spans different observable shapes.)*

### Trigger

Two adjacent function-entry `mov reg, reg` instructions (typically
parm-spill copies) appear in OPPOSITE order between PS.EXE and the
recomp:

```
  PS:                       Recomp:
    push esi                  push esi
    mov esi, eax              mov ecx, edx       <- reversed
    mov ecx, edx              mov esi, eax       <- reversed
```

Same instructions, same registers, just swapped.  Produces a
2-byte diff per pair.  See *Mechanism* below.

### Mechanism

The order in which Watcom’s register allocator processes virtual
names determines the order of parm-spill `mov` instructions at
function entry.

When the C source declares a NAMED LOCAL that aliases a parm
(e.g. `int cap = value;`), the local becomes a separate virtual
name.  The allocator processes the local before the parm (or vice
versa, depending on declaration order), changing which `mov reg,
src` gets emitted first.

This is the same regalloc-priority mechanism that powers Rule 24
and Rule 28:

  * **Rule 24a** — named local forces a stack spill.
  * **Rule 24b** — named local forces shift-in-place.
  * **Rule 27** — named local flips parm-copy ORDER at entry.
  * **Rule 28** — whole-function callee-save register swap (no
    general lever; documented as a known artefact).

All four reduce to: a freshly named virtual gets its own
def-use chain and savings calculation, which shifts the
allocator’s greedy decisions in `bld/cg/c/regalloc.c:
GiveBestReg` / `AssignARegister`.

### Right C: invert the alias decision

Two reciprocal forms produce the SAME total instructions but
opposite parm-copy order at entry.  Pick whichever matches PS.EXE.

**Form A** — named local aliases the parm:

```c
int city_pop_limit_10_to_1(int value, int factor) {
    int cap, counter;
    cap = value;                /* introduces named alias `cap` */
    if (cap < 0) cap = 0;
    if (cap > 100) cap = 100;
    /* ... uses cap throughout ... */
}
```

**Form B** — no named local, mutate the parm directly:

```c
int city_pop_limit_10_to_1(int value, int factor) {
    int counter;
    if (value < 0) value = 0;
    if (value > 100) value = 100;
    /* ... uses value throughout ... */
}
```

Earlier this looked like an “irreducible” 2-byte diff because we
hadn’t identified the lever.  In `city_pop_limit_10_to_1`, Form B
matches PS.EXE byte-for-byte; the original C source had no `cap`
local.

### Detector

`detect_hints` calls `_find_rule_27_pairs` to scan diff rows for
two shapes:

  * **delete + insert** — PS row has `mov X, A` paired with
     RC=None, plus another row within ±3 with PS=None and
     RC=`mov X, A`.
  * **replace + replace** — PS=`mov X, A`, RC=`mov Y, B` at
     row i, plus a mirrored row at j: PS=`mov Y, B`, RC=`mov X, A`.

Limited to `mov` instructions to keep the false-positive rate low.
Fires last in the priority chain — only annotates rows that
other rules didn’t already explain.

### Verified on

  * `city_pop_limit_10_to_1` (formulae.c) — 2-byte diff at +0x4
     fixed by removing the `int cap = value;` alias and using
     `value` directly throughout.
  * `adjust_peace_criteria` (formulae.c) — previously listed
     as “irreducible” at +0x47; now byte-exact in the current
     source (already uses the right alias shape).
  * `tests/oracle/test_rule_27_instruction_pair_reorder.py` —
     5 tests: Form A and Form B emit equal-size functions with
     the parm-copy `mov`s in opposite order; detector fires on
     real Watcom output for both shapes; detector ignores rows
     that aren’t `mov` swaps; no false positives on identical
     code.
  * Watcom 10.0a, `-bt=dos -mf -4r -s`.

---

## Rule 12 — Data-pointer literals look like immediate dwords

### Trigger

A `mov reg, IMM32` instruction with all four immediate bytes
masked as `??` in the verifier diff is a **pointer to a labelled
data symbol**, not an integer constant.  Both forms encode as the
same 5-byte opcode (`b8` for `mov eax, imm32`); the difference is
whether the linker emitted a fixup record for the immediate.

| Asm bytes              | Source                              |
|------------------------|-------------------------------------|
| `b8 40 a3 01 00`       | integer literal `0x1A340`           |
| `b8 ?? ?? ?? ??`       | address of a labelled data symbol   |

### Right C

```c
readfile((int)&data_5A340, buf, size);
```

or, if the symbol has a meaningful name and a typed declaration in
`caesar2.h`:

```c
readfile((int)filename_buf, buf, size);
```

Not:

```c
readfile(filename_table_offset, buf, size);   /* int constant arg — wrong */
```

which emits `b8 40 a3 01 00` (no fixup) and won’t match.

### Mechanism

Whenever the IR references a labelled symbol (data or code), the
back-end emits the placeholder bytes inline and queues an
`F_OFFSET` fixup record carrying the symbol’s label handle.  The
emission code is in `bld/cg/intel/c/x86esc.c:268+` (`OutCodeDisp`
and siblings).  At link time, the linker walks the fixup queue
and patches the real address into each placeholder.

The LE writer carries the fixup records into the executable’s
fixup table; the verifier’s fixup parser reads that table and
tags each byte offset.  The diff renderer in
`c2/commands/decomp_verify.py` shows tagged bytes as `??` instead
of their literal value (which is just placeholder zeroes).

### Verified on

  * `lead_in_logos` and friends in `titles.c` (commit `abe35bd`).
  * `tests/oracle/test_rule_12_data_pointer_literals.py` — 4
     tests: integer literal has 0 fixup bytes; pointer literal
     has all 4 immediate bytes as fixups; both share the same
     opcode byte `b8`; fixup-bytes-in-immediate is the cleanest
     discriminator.
  * Watcom 10.0a, `-bt=dos -mf -4r -s`.

---

## Rule 13 — Per-branch vs hoisted shared call: source structure matters

### Trigger

When multiple if/else branches each end with the same call
(different args per branch), the C source can be written two ways
and both compile to a single tail-merged ``call; ret`` epilogue
(via Rule 15’s `ComTail`).  The two forms differ in **which args
appear in which block**:

  * **Per-branch** — each branch has its own ``call``.  Watcom
     materialises **all N args** inside each branch (including
     args that are identical across all branches), then jumps to
     a shared ``call; ret`` block.
  * **Hoisted** — the call is lifted past the if-tree, with each
     branch storing into shared locals first.  Each branch only
     materialises the *varying* args; the constant args are loaded
     once at the join, just before the call.

### Wrong (mismatched form)

If PS.EXE’s asm has each branch loading constants like
``mov edx, building_data4; xor ecx, ecx;`` (i.e. args that are
identical across all branches), the original C was per-branch.
Writing the recomp as the hoisted form drops those per-branch
loads and merges them into the join — making the recomp
**smaller** than PS.EXE.  Bytes don’t match.

```c
/* WRONG when PS.EXE has per-branch constant loads */
int sz, *fname;
if      (zoom_level == 0) { sz = 0x1000; fname = &a; }
else if (zoom_level == 1) { sz = 0x2000; fname = &b; }
else                      { sz = 0x4000; fname = &c; }
readfile(fname, dst, sz, 0);   /* dst, 0 set ONCE here */
```

### Right (match PS.EXE’s structure)

```c
if      (zoom_level == 0) readfile(&a, dst, 0x1000, 0);
else if (zoom_level == 1) readfile(&b, dst, 0x2000, 0);
else                      readfile(&c, dst, 0x4000, 0);
```

Each branch materialises ``dst`` and ``0`` redundantly — matching
the PS.EXE shape.

### Discriminator

Look at the per-branch suffixes in PS.EXE just before the
``jmp tail`` to the merged call:

  * If each branch loads **only the varying args** → source was
     hoisted.
  * If each branch loads **all N args** (including constants
     repeated in every branch) → source was per-branch.

### Mechanism

`ComTail` in `bld/cg/c/optcom.c:212` is invoked from
`bld/cg/c/optins.c:309` whenever an `OC_RET` is added to the
per-function `RetList`.  It walks the list looking for the
longest common suffix between the new ret-block and any earlier
ret-block; if savings exceed `OptInsSize(OC_JMP, OC_DEST_NEAR)`
(5 bytes) and `OptForSize >= 25` (default 50), it emits a join
label and rewrites the duplicated suffix as a `jmp_near` to that
label.  This works equally well for per-branch and hoisted forms
(both produce the same ``call; ret`` suffix and merge into one
copy).

Args are pushed during the AST walk (`bld/cc/c/cgen.c:1530`,
`OPR_PARM` case).  The order in which arg-load `mov` instructions
appear in the per-branch form follows the call’s arg evaluation
order (right-to-left under `__watcall`); the hoisted form’s
order follows the source’s local-variable assignment order.

The doc’s previous mechanism note ("the hoisted form forces extra
spills, ... pay for an unconditional join block") was incorrect.
Both forms tail-merge cleanly.  The byte difference comes from
*where the constant-arg loads live*, not from extra spills or
epilogue overhead.

### Verified on

  * `swap_circus_gfx` (c2.c) commit `767c8ba`: 6 readfile()
     branches, each loading ``mov edx, building_data4; xor ecx,
     ecx;`` even though those args are identical for all six —
     diagnostic of per-branch source.
  * `tests/oracle/test_rule_13_call_hoist_vs_per_branch.py` — 5
     tests: hoisted is smaller when args share constants; both
     forms equal in size when all args differ; both tail-merge to
     exactly one ``call``; per-branch loads constant args inside
     every branch (3 × ``xor ecx, ecx``, 3 × ``mov edx, &dst``);
     hoisted loads constant args once at the join.
  * Watcom 10.0a, `-bt=dos -mf -4r -s`.

---

## Rule 14 — Bare `ret` (no EAX preload) means the function returns `void`

### Trigger

In `__watcall`, an integer return value is left in EAX.  Watcom
materialises that value with an explicit instruction immediately
before the `ret`:

  * `return 0;`     -> `xor eax, eax; ret`  (3 bytes; `mov eax, 0`
     is 5 bytes, the back-end peephole picks `xor`)
  * `return 1;`     -> `mov eax, 1; ret`    (6 bytes, no peephole
     for non-zero immediates)
  * `return EXPR;`  -> `<eval EXPR into eax>; ret`

A `void` return emits **no EAX-setting instruction**:

  * `return;` (in a void function)  -> bare `ret`
  * implicit fallthrough             -> bare `ret`

If PS.EXE shows a bare `ret` (or `pop ...; ret`) with no preceding
`mov eax`/`xor eax, eax`, the function was declared `void`.  Even
when call sites appear to consume the return (`if (foo()) ...`),
the value being read is whatever incidental register state was
left over (often a flag read inside the function); the C source
still declared `void`.

### Right C

```c
void show_pl8file(char *name) {
    if (!readfile(name, ...)) { beep(); return; }
    flush();
}
```

### Wrong C

```c
int show_pl8file(char *name) {           /* WRONG: PS shows bare `ret` */
    if (!readfile(name, ...)) { beep(); return 0; }
    flush();
    return 1;
}
```

The `int` form emits `xor eax, eax` / `mov eax, 1` before each
`ret` — won’t match PS.

### Mechanism

`bld/cc/c/cgen.c:287-296` selects between two `CGReturn`
invocations based on whether the OPR_RETURN node has a value:

```c
if (node->u2.sym_handle == SYM_NULL) {
    dtype = CGenType(CurFunc->sym_type->object);
    CGReturn(NULL, dtype);                 /* void return */
} else {
    SymGet(&sym, node->u2.sym_handle);
    dtype = CGenType(sym.sym_type);
    name = CGTempName(sym.u1.return_var, dtype);
    name = CGUnary(O_POINTS, name, dtype);
    CGReturn(name, ReturnType(dtype));     /* value return */
}
```

`CGReturn(NULL, ...)` in `bld/cg/c/intrface.c:674` skips the
`TGReturn(name, ...)` call that would otherwise generate the
EAX-load IR.  `BGReturn(NULL, ...)` then emits the bare `ret`.

### Verified on

  * `show_pl8file`, `display_pl8file`, `show_picfile`,
     `display_picfile` in `display.c` (commit `a36a942`).
  * `tests/oracle/test_rule_14_void_return.py` — 5 tests:
     `return 0;` emits `xor eax, eax`; `return 1;` emits
     `mov eax, 1`; `return;` (void fn) emits no EAX-set;
     fallthrough on a void fn emits no EAX-set; an int->void
     conversion drops the EAX-set bytes (and shrinks the
     function).
  * Watcom 10.0a, `-bt=dos -mf -4r -s`.

---

## Rule 15 — Watcom 10.0a does cross-function tail-merge within a TU

This is the single most-impactful rule for action.c-style files (lots
of small wrappers that share an epilogue).

### Mechanism

`ComTail` lives in `bld/cg/c/optcom.c:212+`.  It’s invoked from
`bld/cg/c/optins.c:304` whenever an `OC_RET` is added to the
per-CG-pass `RetList`:

```c
case OC_RET:
    ...
    ComTail(RetList, ins);
```

`RetList` is a global in `bld/cg/c/optdata.c:41`, initialised by
`InitQueue()` in `bld/cg/c/optmain.c:210` (called once per TU from
`InitCG()` in `bld/cg/c/generate.c:105`).  This is why merging
spans function boundaries within a TU but **not** across TUs.

`FindCommon` accumulates `c->save += _ObjLen(p1)` for each common
instruction (working backwards from the ret).  `ComTail` then
gates: `if (max.save <= OptInsSize(OC_JMP, OC_DEST_NEAR))
optreturn(false);` (must save more than a near-jmp’s worth, i.e.
> 5 bytes), and `if (OptForSize < 25) optreturn(false);` (default
`OptForSize = 50`, satisfied by `-bt=dos -mf -4r -s`).

### Far merges accumulate across the whole TU — a miss is incomplete decompilation, not a build artifact

On the x86 target `FlushQueue()` is gated to `NEW_P5_PROFILING`
(`generate.c:331-336`), so it is **not** called per routine: the
optimization queue (`FirstIns…LastIns`) and `RetList` accumulate across
the **whole translation unit**.  `RetList` is only ever shortened by
`ShrinkQueue → PullQueue → DelRef(&RetList, …)`, and `ShrinkQueue`'s only
caller is `FlushSomeOpt` (`memlimit.c:75`), invoked from the memory-limit /
allocation-failure paths and which itself emits the user-visible
`MSG_PEEPHOLE_FLUSHED` warning.  That fires only when the compiler is
memory-starved, which never happens in this toolchain (the W32RUN extender
reports a fixed pool the build never exhausts, and the flush warning is
never emitted; see § memory).  So `RetList` is never evicted and persists
for the entire TU.

⇒ **Every within-TU far-merge is reproducible.**  `ComTail` can merge a
dependent's `ret` into any earlier-generated donor's `ret` anywhere in the
same TU, regardless of distance.  A non-reproducing far-merge therefore
means the merge family is **not fully decompiled in PS's source order** —
the donor or an intervening function is still a stub, or the source order
differs — both of which are source-fixable.  Decompile the whole family
(donor first, in PS's order); do not treat the miss as a build artifact.

Empirically this is just decompilation progress: of PS.EXE's 453
function-final far-merges, the build reproduces the ones whose families
are decompiled and in order; the misses cluster on large spans only
because those families have more not-yet-decompiled members.

### Symptom

A series of small functions in PS.EXE that all set up a few globals,
then jump to a shared epilogue. Only the **first function in source
order** containing the shared epilogue has the full body inlined;
subsequent functions emit a `jmp` (short or near) into the middle of
that first function.

```
act_house1:                      ; full body
    push edx
    mov  [placing_type],  10
    mov  [placing_flags], 1
    ...
act_house1_eplog:
    mov  [placing_cost],  eax
    mov  [pm_build_shape], 0
    pop  edx
    ret

act_house2:                      ; tail-merges into act_house1
    push edx
    mov  [placing_type],  11
    mov  [placing_flags], 1
    mov  eax, [city_costs+0x10]
    jmp  act_house1_eplog        ; <-- jumps mid-act_house1
```

### Source-order requirement

For byte-exact reproduction, decompile the **merge target** (first
function in source order with the shared epilogue) before its
siblings. If you decompile a sibling first, Watcom can’t back-jump
into a stub and emits the full epilogue inline — different bytes.

### Forward AND backward tail-merge

Cross-function tail-merge is bidirectional. An *earlier* function in
source order can jmp into a *later* function’s body, as long as both
are in the same TU. Example: `act_pop_tax_up/_down` (line ~1700) jmp
into `act_slave_welfare_up + 0x19` (line ~1900). Demonstrated in
commit `a29e1a9`.

### Stack fall-through (degenerate case)

When the next function in source order starts with the same
instruction the current function would have emitted at its
epilogue, Watcom drops the trailing instruction and lets execution
fall through. Most often seen with bare `ret`:

```
a08_raider_ship:    mov  [threat_mood], 2     ; no ret — falls through
s00_null:           ret                       ; provides the ret for a08
```

Source: `void a08_raider_ship(void) { threat_mood = 2; }`

Documented on commit `fe80333`.

### Merge-target selection: longest shared tail wins

When N functions share an M-byte tail, Watcom doesn't simply pick
the earliest or latest one as the canonical body. The merge target
is the function whose tail prefix matches the **longest** shared
sub-sequence with at least one other function.

Discovered on `skill1_game_loop` / `skill2_game_loop` /
`battle_intro_game_loop` / `exit_game_loop` / `promotion_game_loop`
(commit `1466175`):

* `battle_intro`, `exit`, `promotion` all end in `<args>; call
  control_buttons; pop edx; pop ecx; pop ebx; ret` (10-byte
  shared tail).
* `skill1` ends in `mov edx,0x50; mov eax,edx; call control_buttons;
  pop edx; pop ecx; pop ebx; ret` (12-byte tail).
* `skill2` ends in the **same** 12-byte tail as `skill1`.

With only the 10-byte cluster, Watcom picks the EARLIEST in source
order (`battle_intro`) as canonical, others jmp BACKWARD to its
tail. Adding `skill2` — which shares the LONGER 12-byte tail with
`skill1` — re-anchors the merge target to `skill1`. Now
`battle_intro/exit/promotion` jmp FORWARD into `skill1+0x34` (the
`call control_buttons`) and `skill2` jmps into `skill1+0x2D` (the
`mov edx,0x50`).

**Practical consequence**: When decompiling tail-merge clusters,
decompile **all** members at once. A cluster with the wrong subset
decompiled may pick a different merge target than PS, producing
1–5 byte diffs at the tail-jump sites that resolve when the
remaining members are added.

Also documented in commit `1466175`.

### Direction-flipping: cannot be coerced via source restructuring

For the `floop_end` / `gloop_end` / `just_idle_game_loop` cluster in
gloops.c the merge runs in the **wrong direction**:

* **PS picks `gloop_end` as canonical** (43-byte body), with
  `floop_end` (28 bytes) emitting `call+if+je+mov+jmp` that jumps
  *forward* into `gloop_end`'s body at +5 and +12.
* **Our build picks `floop_end` as canonical** (full inline body,
  ~60 bytes), with `gloop_end` (10 bytes) emitting `call
  get_mouse_droppings; jmp` *backward* into floop_end's tail.

Both versions are semantically equivalent and use the same fall-through
from `just_idle_game_loop`.

**Source-derived mechanism (corrected — supersedes the earlier
"larger emitted body" guess, which was circular: the donor is larger
*because* it keeps the tail, not chosen *for* its size).**  Reading
`bld/cg/c/optcom.c` + `optins.c` shows there are **two** tail-merge
passes that race to claim the shared `show_mouse(pointer_mode); …; ret`
sequence, and whichever fires first fixes the donor:

* **`ComTail(RetList, ret)`** — fired from `OptPush` (`optins.c`
  `case OC_RET:`).  `OptPush` walks the instruction list from
  `LastIns` **backward**, so the *later* function's `ret` is processed
  first.  The processed `ret` (`ins`) is the one **deleted** and turned
  into a back-jump; the donor (`first`) is the RetList ref with the
  largest `FindCommon` tail.  On its own this makes the **later**
  function (`gloop_end`) the dependent — exactly our build's direction.
* **`ComCode(jmp)`** — fired from `OptPush`/`OptPull` on `OC_JMP`.
  `floop_end` has an `if/else` (`if (forum_dept_over) show_mouse(0x15)
  else show_mouse(pointer_mode)`), so it carries an internal `jmp` whose
  predecessors `ComCode` can fold into a sibling's body.  When this
  fires first it merges **floop_end's** two paths *forward* into
  `gloop_end` (the linear sibling whose whole body already *is* the
  shared tail), eliminating floop_end's own `ret` before `ComTail` ever
  reaches it — so `gloop_end` stays canonical.  This is PS's direction.

So the donor is decided by **which pass claims the shared tail first**
(`ComCode` folding `floop_end`'s branch paths *forward* into `gloop_end`,
vs `ComTail` turning `gloop_end`'s `ret` into a *backward* jump into
`floop_end`) — **not** by body size.  The compiler and flags are
identical between PS and our build, so the *pass order itself* is the
same; the divergence therefore traces to a difference in `floop_end`'s
**pre-merge instruction sequence** (its own 7-byte diff: how the
`if/else` lowers and where its internal `jmp`/`je` land), which changes
which `FindCommon` window the two passes see and hence which one wins.
That difference is entangled with the merge outcome (chicken-and-egg),
and no C-source spelling of the `if/else` tried below de-tangles it —
consistent with the "longest shared tail wins" donor rule (the donor is
always the ref with the largest `FindCommon` tail; here both candidates
tie at the same shared tail, so the tie falls to internal queue order).

Experiments that **do not** flip the direction:

| Attempt | Result |
|---|---|
| Ternary inside `show_mouse(...)` arg | Same bytes, same direction |
| Early-return on the IF branch + tail-call `gloop_end()` on else | Different layout entirely (get_mouse_droppings moved inside the if, breaks line 85) |
| Optimization flags `-ot`, `-os`, `-or`, `-oc`, `-oe`, `-oh`, `-ol+`, `-of+` | Same direction (or no merge at all with `-ot`) |
| `#pragma alloc_text("EARLY_TEXT", gloop_end, just_idle)` | Linker still places EARLY_TEXT after _TEXT; tail-merge stays per-segment, direction unchanged |
| 100 filler functions between floop_end and gloop_end (mimic PS's ~1500-byte gap) | Same direction |

**The only thing that flips it**: putting `gloop_end` *before*
`floop_end` in source order. That's prohibited by the
"don't reorder functions" rule.

**Verdict**: 7+9 = 16 byte diffs at the floop_end / gloop_end tail-jump
sites are an unfixable Watcom canonical-selection artefact, given the
constraints. The behaviour is correct; only the byte layout differs.

Documented after exhausting source-restructuring options.

### Second instance: show_about_box cluster (screens.c)

**Cluster** (commit `ef228b4`): 7 functions in screens.c share the
same 11-byte tail (`mov [hold_mouse_replace], 1; pop edx; pop ecx;
pop ebx; ret`):

| Function | Line | Tail kind | PS canonical? |
|---|---|---|---|
| `battle_screen` | 185 | 11 b (call set_palette + epilogue) | no — jmp src |
| `show_no_provinces_box` | 633 | 11 b (call setup_whole_screen_refresh + epilogue) | no — jmp src |
| `show_skill1_box` | 707 | 11 b (call font_list + epilogue) | no — jmp src |
| `show_skill2_box` | 722 | 11 b (call show_name_choice + epilogue) | no — jmp src |
| `show_about_box` | **797** | 16 b (call refresh_svga_screen + epilogue) | **YES — body intact** |
| `forum_constant_screen` | 908 | 11 b | no — jmp src |
| `show_census_panel` | 2331 | 16 b (call refresh_svga_screen + epilogue) | no — jmp src to +0x9D |

In PS.EXE, the canonical body lives at show_about_box+0xA2.  6 of
the 7 cluster members tail-jmp into show_about_box (5 to +0xA2,
1 to +0x9D).

Under the OW v1/v2 ComTail "first-RET-with-matching-tail wins"
rule, the canonical *should* be `battle_screen` (line 185, earliest
in source).  In our recompiled build it falls on the earliest
11-byte-tail member that's been decompiled (currently
`show_no_provinces_box`, line 633).  Neither matches PS.

**The 16-byte tail observation** (show_about_box ↔ show_census_panel)
is the most likely tie-breaker, but no source-level lever (re-
ordering forbidden) has yet been found that makes Watcom 10.0a
pick show_about_box as canonical.  Hypotheses tried:

* `hold_mouse_replace = 1` on same source line as
  `refresh_svga_screen()` (force one line entry) — no effect.
* Removing `hold_mouse_replace = 1` from sister tails (so they
  don't form the 11-byte cluster) — changes diff but doesn't fix.
* Adding more cluster members (forum_constant_screen,
  show_first_region_box, etc.) — progresses other functions to
  byte-exact but doesn't re-anchor the canonical.

**Residue accepted**: 7 b on show_about_box, 1 b on
show_no_provinces_box, 1 b on reshow_initreg_box.  Functional
behaviour is correct; only the layout differs.

### Hypothesis for future investigation

The pattern suggests Watcom's tail-merge has a **two-level**
selection rule:

1. Identify cluster (functions sharing the canonical 11-byte tail).
2. Among cluster members, the canonical is the one with the
   **longest unique tail extension** (here: show_about_box and
   show_census_panel both have 16-byte tails, breaking the tie
   with an earliest-in-source rule → show_about_box at line 797
   wins over show_census_panel at line 2331).

This would imply Watcom 10.0a does either (a) a multi-pass
tail-merge that retroactively re-anchors when a longer-tailed
sibling appears, or (b) a deferred merge-decision pass that runs
at TU end with full visibility of all RETs.

Neither is visible in OW v1/v2's `optcom.c`.  Possibly a Watcom
10.0a-specific algorithm not preserved in the OW lineage.

When the underlying mechanism is reduced to a reproducible
source pattern, document as a new rule and reference both
instances (act_idle/floop_end and show_about_box cluster).

### Verified on

  * `act_house1`/`2`/`3` cluster (action.c) and dozens of
     similar wrapper clusters across action.c, c2.c, gloops.c.
  * `tests/oracle/test_rule_15_cross_function_tail_merge.py` —
     6 tests: same-TU merges 3 functions into 1 canonical;
     cross-TU prevents merging; same-TU total bytes < cross-TU
     total bytes; source order determines which function is
     canonical (reversing source order swaps the canonical
     function); merged `jmp` targets a label inside the canonical
     function’s tail (not its start); a tail of ≤ 5 bytes is
     below the near-jmp threshold and does NOT merge.
  * Cross-version tail-merge bisect (`docs/codegen-experiments/
    tail-merge-bisect.c`): tail-merge enabled in Watcom 9.01d
    through 11.0; disabled by default in 11.0b/11.0c; re-enabled
    in OW v2 master.
  * Watcom 10.0a, `-bt=dos -mf -4r -s`.

### See also

  * Rule 42 documents the *donor selection algorithm* in
    detail (with OW source references): which function in
    a tail-merge family ends up keeping the inline tail
    vs. emitting the jmp.  Critical for predicting which
    stub decompositions will retroactively unblock
    byte-exact wins for their named-PS-donor dependents.

---

## Rule 16 — Short-vs-near jmp encoding cascade

### Trigger

The target of an unconditional jmp (including tail-merge jmps from
Rule 15) is encoded in one of two ways depending on byte distance:

  * **Short** (`eb disp8`, 2 bytes) when the signed 8-bit
     displacement fits, i.e. forward up to +127, backward down to
     -127 in practice (`MAX_SHORT_BWD` = 126).
  * **Near** (`e9 disp32`, 5 bytes) otherwise.

Adding or removing intermediate stubs can shift the byte distance
across 127 and flip the encoding.  The function size cascades by
exactly **3 bytes** (5 - 2) per flip.

### Symptom

A 1-byte (or 3-byte) diff at the end of an otherwise byte-exact
tail-merge wrapper, where PS shows `e9 XX XX XX XX` (5 bytes) and
the recomp shows `eb XX` (2 bytes), or vice versa.

### Cause

PS.EXE has decompiled neighbours between the wrapper and its
merge target; the recomp still has stubs there, so the byte
distance is shorter and Watcom picks the smaller encoding.

### Fix

Decompile the intermediate stubs.  Once the byte distance crosses
~127, both PS and the recomp emit the 5-byte form and the diff
collapses.

### Mechanism

`bld/cg/h/ocentry.h:68-69` defines the x86 short-jmp range:

```c
#define MAX_SHORT_FWD  127
#define MAX_SHORT_BWD  (128 - 2)   /* 126 */
```

`bld/cg/c/optrel.c:74-99` walks instructions forward from the jmp
to its target accumulating `_ObjLen(instr)`; if the cumulative
size stays under `MAX_SHORT_FWD`, the jmp is shrunk to short.
For backward jmps the test is `(AskLocation() - lbl->lbl.address)
<= MAX_SHORT_BWD`.

The encoder in `bld/cg/intel/c/x86esc.c:288` checks
`objlen == OptInsSize(OC_JMP, OC_DEST_SHORT)` and emits the short
form via `_OutJShort + OutShortDisp(...)`; otherwise it emits the
near form via `_OutJNear + OutCodeDisp(...)`.

### Verified on

  * `act_tower` (commit `19a77c7`, resolved `b57121f`),
     `act_barracks`, four `act_help_*` / `act_query_*` 1-byte
     diffs in action.c.
  * `tests/oracle/test_rule_16_jmp_short_vs_near.py` — 5 tests:
     close neighbour uses `eb` (2 bytes); far neighbour uses `e9`
     (5 bytes); threshold sits at exactly the 10-vs-11-filler
     boundary in our snippet (corresponds to backward
     displacement crossing -127); function size cascades by
     exactly 3 bytes at the threshold; opcode bytes match (`eb`
     vs `e9`).
  * Watcom 10.0a, `-bt=dos -mf -4r -s`.

---

## Rule 17 — Flag-mask split-RMW emits an extra register copy

### Trigger

When a flag byte is updated by clearing some bits and setting
others, the C source can be written two ways:

  * **Combined**: a single statement
     ``x = (x & MASK) | BITS;``
  * **Split**: two statements
     ``x &= MASK; x |= BITS;``

PS.EXE’s pattern for the SPLIT form has an **extra register-copy**
between the AND and the OR:

```
mov  rl1, [x]
and  rl1, MASK
mov  rl2, rl1   ; <-- extra copy to a SECOND register
or   rl2, BITS
mov  [x], rl2
```

versus the COMBINED form’s tighter 4-instruction sequence:

```
mov  rl, [x]
and  rl, MASK
or   rl, BITS
mov  [x], rl
```

The extra `mov rl2, rl1` is the rule’s diagnostic: if PS.EXE shows
that copy at a flag-update site, the source had two separate
statements, not the combined expression.

### Two sub-shapes

  * **Struct field / array element** (the case from PS.EXE’s
     `army_list[army_no].flags`): SPLIT emits exactly the doc’s
     5-instruction sequence with one memory write at the end.
  * **Plain global byte**: SPLIT also emits **two memory writes**
     (one per source statement, by Rule 3), so the full sequence
     is 6 instructions.  The "copy to second register" is still
     present.

In both shapes COMBINED folds to 4 instructions with one register
and one memory write.

### Right C: write what PS.EXE shows

If the diff shows the 5-instruction pattern with the
`mov rl2, rl1` copy, write two statements:

```c
army_list[army_no].flags &= 0xFC;
army_list[army_no].flags |= 1;
```

If the diff shows the 4-instruction tight form, write the
combined expression:

```c
army_list[army_no].flags = (army_list[army_no].flags & 0xFC) | 1;
```

### Mechanism

`bld/cc/c/cgen.c:1357-1369` handles `OPR_AND_EQUAL` and
`OPR_OR_EQUAL` by calling `CGPreGets(CGOperator[opr], lvalue,
rvalue, ...)`.  `CGPreGets` -> `TGPreGets` -> `DoTGPreGets`
(`bld/cg/c/tree.c:1102`) builds a `TN_PRE_GETS` tree node per
source statement.

Two consecutive `TN_PRE_GETS` nodes feed two distinct IR
statements.  Rule 3’s `CheckUseful` keeps the per-statement
`N_MEMORY` writes alive on plain globals (struct/array writes get
folded into one).  Inside each statement, the back-end allocates
a destination register that’s distinct from the source register
so the source remains observable post-statement (the compiler
treats the post-AND value as potentially live for the next
reference); on a single combined expression no such boundary
exists, so the back-end folds AND/OR into one register.

### Verified on

  * `sa01_wait` in `int_c2.c` (commit `c73dee1`).
  * `tests/oracle/test_rule_17_flag_mask_split_rmw.py` — 4
     tests: struct-field SPLIT shows the 5-insn pattern with the
     extra register copy; struct-field COMBINED has no copy;
     plain-global SPLIT has the extra copy plus two memory writes
     (Rule 3 cooperating); COMBINED is strictly shorter than SPLIT
     in both shapes.
  * Watcom 10.0a, `-bt=dos -mf -4r -s`.

---

## Rule 18 — Lazy per-branch computation, not pre-computed temps

### Trigger

When a function takes an arg and uses ``arg + offset`` inside an
if/else cascade, the C source structure determines whether Watcom
emits the eager LEA or the per-branch ``mov + add``:

  * **Pre-computed temp**
     `int v = arg + 0x1B; if (...) ... v ...;`
     -> `lea reg, [arg_reg + 0x1B]` (3 bytes)
  * **Inline per-branch**
     `if (...) f = arg + 0x1B;`
     -> `mov reg, arg_reg; add reg, 0x1B` (5 bytes)

The 2-byte difference repeats per pre-computed temp.  PS.EXE
consistently shows the 5-byte ``mov + add`` shape at sites like
`get_rioter_image`; matching it requires writing the offsets
inline at each branch.

### Caveat — depends on register pressure

The trigger isn’t *just* the source structure; it depends on how
many callee-saved registers the function uses.  With pressure low
(only EDX needs saving), Watcom picks LEA in both forms and the
bytes are identical.  With pressure high (EBX + ECX + EDX all
saved, e.g. in `get_rioter_image`), the per-branch form yields
``mov + add`` while the pre-computed form yields LEA.

### Symptom

PS.EXE’s prologue keeps the function arg in a callee-saved
register (`mov ebx, eax`), then materialises `arg + offset` into
another register **only inside the branch that uses it**:

```
push ebx
push ecx
push edx
mov  ebx, eax       ; save arg
...
mov  ecx, ebx       ; first branch: ecx = arg + 0x1B
add  ecx, 0x1B
cmp  ...
jge  branch2
mov  [field], cx
ret

branch2:
add  ebx, 0x1C      ; second branch: ebx becomes arg + 0x1C
...
```

### Right C

```c
if      (cond1) field = (short)(arg + 0x1B);
else if (cond2) field = (short)(arg + 0x1C);
else if (cond3) field = (short)(arg + 0x1B);
...
```

Not:

```c
int a = arg + 0x1B;     /* WRONG: emits LEA in high-pressure context */
int b = arg + 0x1C;
if (cond1) ... a ...
else       ... b ...
```

### Mechanism

Watcom’s IR builder creates an `O_PLUS` tree node for ``arg +
0x1B``.  The lowering to x86 is choice-based: `bld/cg/intel/386/c/
386table.c`’s `Add4` rows map `O_PLUS` to either `LEA` or
`mov + add` depending on operand register classes.

The pre-computed temp form lives at the same source level as the
arg-saving `mov`, giving the back-end visibility into both
materialisations at once; the compiler picks LEA because it can
fold the precompute and the offset into one instruction.

The inline-per-branch form scopes each materialisation to its
basic block; the compiler treats each as an independent two-step
operation (`mov dest, src; add dest, K`).  Under high register
pressure, the cost-based selector in `AssignARegister`
(`bld/cg/c/regalloc.c:1034`) prefers the `mov + add` form because
LEA would overlap conflicts with already-allocated callee-saves.

### Verified on

  * `get_rioter_image` (commit `f7aa75d`).
  * `tests/oracle/test_rule_18_lazy_per_branch.py` — 4 tests:
     low-pressure case both forms produce identical bytes;
     high-pressure pre-computed -> LEA; high-pressure per-branch
     -> `mov + add`; per-branch is at least 2 bytes longer per
     eager precompute (the trade-off PS.EXE consistently makes).
  * Watcom 10.0a, `-bt=dos -mf -4r -s`.

---

## Rule 19 — `char` vs `int` parameter spill width

**Sub-case of Rule 8** — see Rule 8 for the verified mechanism
and tests (`tests/oracle/test_rule_08_char_unsigned_default.py`).

### Trigger

A parameter is spilled to the stack at function entry.  The spill
width tells you the parm’s declared type:

| PS.EXE shows                              | Original parm type       |
|-------------------------------------------|--------------------------|
| `mov byte ptr [esp+N], al`                | `char` (or `unsigned`)   |
| `mov byte ptr [esp+N], al` + `movsx` reload | `signed char`          |
| `push eax` (single parm)                  | `int`                    |
| `mov dword ptr [esp+N], edx` (multi-parm) | `int`                    |

### Right C

```c
void create_unit(int x, int y, int type);
/* not: void create_unit(char x, char y, char type); */
```

Applies even when the parameter is semantically a small value;
the original authors used `int` for ABI consistency.

### Verified on

  * `create_unit` / `create_arrow` (commit `8724ab8`).
  * `tests/oracle/test_rule_08_char_unsigned_default.py` — the
     `test_char_int_two_param_spill_distinguishes_widths` and
     surrounding tests cover both single-parm and multi-parm
     spills.
  * Watcom 10.0a, `-bt=dos -mf -4r -s`.

### Sub-rule 19a — Stack-passed parms: type determines callee load width

When a function takes more than 4 register-passed parms, the
5th+ parms are passed on the stack.  __watcall callers always
`push imm32 0` (4 bytes, dword-aligned), but the callee's load
width is determined by the **declared parm type**, NOT the
caller's push width:

| Callee-side parm decl  | Callee emits                  | Bytes |
|------------------------|-------------------------------|-------|
| `char p`               | `mov bl, byte ptr [esp+N]`    | 4     |
| `int p`                | `mov ebx, dword ptr [esp+N]`  | 4     |

Both are 4-byte instructions, so the load itself doesn't
differ in size.  But the **register allocation cascade** does:

* `mov bl, [m]` only writes the low byte of `ebx`, leaving
  the upper 3 bytes available.  Watcom can then reuse `ebx`
  for ANOTHER value (e.g. a register-passed parm that needs
  to live alongside the byte parm), or zext via
  `xor ebx, ebx; mov bl, [m]` if the parm is used as an int.
* `mov ebx, [m]` overwrites all of `ebx`, locking it to the
  parm value.  Other live values must go to different
  registers.

For `set_rm_range(int x, int y, int half_width, char field_offset, char kind_byte)`,
the 5th arg `kind_byte` is loaded as `mov bl, [esp+18]`.  The
upper 24 bits of `ebx` are then reused as a scratch register
throughout the function (Watcom uses `ebx` for `half_width`
briefly via `mov eax, ebx`, then for various intermediate
computations).

If `kind_byte` is declared `int`, Watcom emits
`mov ebx, [esp+18]` and locks `ebx` to the parm.  This forces
the original `mov eax, ebx` (copying half_width to eax) to use
a different register, which cascades through the entire
function.

**Lever**: declare stack-passed byte parms as `char` (or
`unsigned char`), not `int`.  This frees up the upper 3 bytes
of the parm-pass register for downstream use.

### Verified on

* `set_rm_range` (commit `076e41b`) — 184 b diff with
  `int field_offset, int kind_byte`; 50 b after `char
  field_offset`; 0 b after `char kind_byte`.  The cascade was
  function-wide: prologue, x-clamp, y-clamp, and inner-loop
  all changed register assignments based on whether `ebx` was
  locked to the parm or available.

### Caveat

This sub-rule **only applies to stack-passed parms** (5th arg
and beyond in __watcall).  Register-passed parms (1st-4th args
in eax/edx/ebx/ecx) are covered by Rule 19's main table — they
use `mov [esp+N], al` (byte spill) vs `push eax` (int spill).

The `char` declaration alone is NOT enough — you also need to
make sure the parm is USED only as a byte in the callee body.
If you cast it to `int` for arithmetic, Watcom may zext early
and lose the cascade benefit.

---

## Rule 20 — Loop-counter terminal value as the final index

### Trigger

After a counted ``for`` loop, the loop counter holds the terminal
value (the value that failed the loop condition).  When the C
source uses that variable as an array index right after the loop,
Watcom keeps the counter live and re-uses the indexed addressing
mode it built inside the loop:

```c
int i;
for (i = 0; i < 7; i++) {
    slave_requirements[i].current = 0;     // [eax*8]
}
slave_requirements[i].current = pool;      // STILL [eax*8] (i = 7)
```

emits `mov [eax*8], reg` for the post-loop store — same
addressing mode as inside the loop.

If the C source uses a literal index instead:

```c
slave_requirements[7].current = pool;
```

Watcom emits `mov [0x38], reg` (absolute displacement 7*8 = 0x38),
**different bytes** even though semantically identical.  The
literal form is also a few bytes shorter (no extra register save
needed), so writing it that way under-shoots PS.EXE’s size.

### Right C

```c
for (i = 0; i < 7; i++) { ... }
slave_requirements[i].current = pool;   // matches PS.EXE
```

Not:

```c
slave_requirements[7].current = pool;   // emits absolute disp
```

### Mechanism

Watcom’s induction-variable analysis (`bld/cg/c/loopopts.c`,
`IndVarList` from line 91) tracks the loop counter as an
induction variable.  When the post-loop code references the same
variable, the back-end keeps the register-resident counter live;
its register holds the terminal value.

The address-folding pass in `bld/cg/intel/c/x86esc.c` then sees
the post-loop expression `array_base + i * elem_size + field_off`
where `i` is in EAX, and folds it into the same `[eax*8 + disp]`
shape that the loop body used.  Using a literal `7` instead loses
the IV link; the constant `7 * 8 + field_off` is computed at
compile time and emitted as an absolute displacement.

### Verified on

  * `adjust_slave_usage` (commit `ff2cf77`).
  * `tests/oracle/test_rule_20_loop_counter_terminal_index.py` —
     4 tests: loop-counter form emits indexed addressing for the
     final store; literal form emits absolute displacement;
     differ at the byte level; loop-counter form is larger by a
     few bytes (extra register live-out forces an additional
     save/restore).
  * Watcom 10.0a, `-bt=dos -mf -4r -s`.

---

## Rule 21 — Indexed-array folding only at the deref site

### Trigger

A byte-array offset expression
`(char *)base + idx * STRIDE + FIELD_OFFSET` collapses into a
single `[reg + disp]` addressing mode **only if the entire
expression is the operand of a single deref** — not if it’s
pinned to a pointer local first.

  * **Direct deref** (folded, fewer bytes):
    ```c
    *(short *)((char *)ambient_list + idx * 70 + 4) = value;
    ```
    -> `imul eax, eax, 0x46; mov [eax + base+4], dx` (11 bytes;
    the `base + 4` displacement lives in one 4-byte fixup).
  * **Pinned through a local pointer** (un-folded):
    ```c
    short *row = (short *)((char *)ambient_list + idx * 70 + 4);
    *row = value;
    ```
    -> `imul eax, eax, 0x46; add eax, base; add eax, 4;
    mov [eax], dx` (15 bytes; base and +4 are materialised
    separately).

The **4-byte difference** comes from the two extra `add`
instructions in the un-folded form.  Watcom’s addressing-mode
synthesis runs at the deref; splitting the address through a
local type-laundering pointer breaks the fold.

Applies to any struct stride that isn’t a power of 2 (8, 16, 32
are folded as `eax*N`; 70, 175, 58, etc. need the explicit
displacement and benefit from the deref-site fold).

### Right C

```c
*(short *)((char *)ambient_list + idx * 70 + 4) = some_value;
```

Not:

```c
short *row = (short *)((char *)ambient_list + idx * 70 + 4);
*row = some_value;       /* WRONG: emits two extra adds */
```

### Mechanism

The back-end’s addressing-mode synthesiser
(`bld/cg/intel/c/x86esc.c`’s `OutMem*` routines) walks the
operand tree of an `O_PTR` (deref) node, identifying the base
register, an index*scale term, and a constant displacement.  When
the deref is on a complete expression, all three components are
visible at once and the synthesiser folds them into one
addressing mode.

When a local pointer is assigned the partial address first, the
local pointer’s register holds the *fully-computed* address;
the deref on the local sees only `*reg` with no displacement, so
the synthesiser has nothing to fold.  The address-computation
side now lives at the assignment site, where each `add` becomes
a separate instruction.

### Verified on

  * `set_ambient_minimum` (commit `a29fed1`).
  * `tests/oracle/test_rule_21_indexed_array_folding.py` — 4
     tests: direct-deref emits a single store with no extra
     `add`; via-local emits exactly two extra `add reg, imm`;
     via-local is at least 4 bytes longer; both share the
     `imul eax, eax, 0x46`.
  * Watcom 10.0a, `-bt=dos -mf -4r -s`.

---

## Rule 22 — Stub signatures must match real arg widths

Operational rather than pure codegen.  When a callee is still a
stub, its signature must match the real ABI even when the body
is empty - otherwise the **caller’s call-site bytes differ**
from PS.EXE’s.

### Trigger

  * Callee declared `void X(int p);` and caller passes `0x36`:
     caller emits `mov eax, 0x36; call X` (call site = 10 bytes).
  * Callee declared `void X(void);` and caller passes no args:
     caller emits `call X` only (5 bytes).

If PS.EXE’s caller shows `mov eax, 0x36; call X`, the original
declaration was `void X(int)` (or compatible).  An auto-generated
`void X(void)` stub will produce a 5-byte call site - 5 bytes
shorter than PS.EXE.

### Right C

```c
void get_movement_image(int img_id) { (void)img_id; }
```

Not:

```c
void get_movement_image(void) {}                /* WRONG */
```

### Mechanism

The C front-end checks the callee’s prototype during expression
analysis (`bld/cc/c/cgen.c:1530-1532`, `OPR_PARM` case).  If the
prototype declares `(void)`, no `OPR_PARM` IR nodes are emitted
for any actual arguments (and the source itself can’t
syntactically pass any).  If the prototype declares `(int)`, each
argument generates a `CGAddParm(call, arg, TY_INTEGER)` call
which materialises the arg in the right `__watcall` register
before the call.

The back-end has no visibility into the callee’s actual body
when generating the call-site - it trusts the prototype.  An
empty function body with the right prototype generates the same
call bytes as a full implementation with that prototype.

### Verified on

  * Repeatedly while decompiling the int_c2 state-handler family
     (commit `fe80333`); also bit `confirm` in controls.c,
     `alter_slave_reqs` in formulae.c, `region_go_to_target`,
     `sail_to_target`, `citizen_maraude_to_target`, etc.
  * `tests/oracle/test_rule_22_stub_signatures.py` — 3 tests:
     `void(int)` stub + `X(0x36)` -> caller emits
     `mov eax, 0x36`; `void(void)` stub + `X()` -> no arg-load
     instruction; the int-proto call site is strictly larger
     than the void-proto call site.
  * Watcom 10.0a, `-bt=dos -mf -4r -s`.

### See also

  * Rule 41 — Dead parameter as ABI-compat slot.  The mirror
    case: when the *real* (decompiled) function has a stack-arg
    slot the body never reads but every caller pushes a uniform
    constant for, declare it as a `(void)` arg so the function's
    ``ret X`` cleanup matches PS.

---

## Rule 23 — `signed char` field, no `(char)` cast

**Sub-case of Rule 8** — see Rule 8 for the verified mechanism
and tests (`tests/oracle/test_rule_08_char_unsigned_default.py`).

### Trigger

PS.EXE reads a struct field with `movsx`:

```
movsx  eax, byte ptr [reg + struct_base + 0x10]
```

but our recomp emits zero-extension:

```
mov    al, byte ptr [reg + struct_base + 0x10]
and    eax, 0xff
```

The field is declared plain `char` (defaults to unsigned on
Watcom 10.0a; see Rule 8) or we wrote `(char)x` at the read site,
which forces zero-extend.

### Right C: two halves

1. Declare the field `signed char` in `entities.h`:

   ```c
   signed char state_idx;        /* +0x10  movsx-read */
   ```

2. Drop any `(char)` casts at read sites; let the natural
   integer promotion from `signed char` to `int` emit `movsx`.

Do NOT do a global sweep — leave plain `char` for fields PS reads
with plain byte ops.  Only promote those fields PS uses with
`movsx`.

### Verified on

  * Reinforced repeatedly in commits `7c62a80`, `8724ab8`,
     `c73dee1`, `fe80333`.
  * `tests/oracle/test_rule_08_char_unsigned_default.py` —
     `test_signed_char_global_uses_movsx` covers the read side;
     `test_plain_char_global_uses_zero_extend` confirms the
     wrong-shape diagnostic.
  * Watcom 10.0a, `-bt=dos -mf -4r -s`.

---

## Rule 24 — Spill-via-local: force a stack slot for an argument

### Symptom

PS.EXE saves an argument to a *named* stack slot at function entry
and reloads it later through `mov ax, [esp+N]`:

```
+0011  mov edi, edx                ; PS keeps ymin in a callee-save reg
+0013  mov [esp+0x1c], ebx         ; PS spills xmax to a stack slot
...
+0030  mov eax, [esp+0x1c]         ; reload xmax
+0034  mov [esp+0xc], ax           ; r.w.dx = xmax
```

Our recomp picks the *opposite* spill victim and uses the wrong
register at the use site:

```
+0011  mov [esp+0x1c], edx         ; recomp spills ymin
+0013  mov edi, ebx                ; recomp keeps xmax in edi
...
+0030  mov [esp+0xc], di           ; r.w.dx via di, no reload
```

No `Rule N` hint will fire — byte counts and total instruction
budget match, only the regalloc choice differs.

### Cause

Watcom's register allocator picks the spill victim by an interaction
of:

* declaration order of args
* first-use order in the function body
* whether the value also appears on the right-hand side of a local
  initializer

When the chosen victim differs from PS, the bytes diverge for the
entire span between save and reload (typically 5–40b).

### Fix

Introduce an explicit *named* local that aliases the argument and
use the local at the matching read site:

```c
void mouserange(int xmin, int ymin, int xmax, int ymax)
{
    union REGS r;
    int hi_x = xmax;            /* force xmax onto its own stack slot */
    memset(&r, 0, 0x1c);
    r.w.ax = 7;
    r.w.cx = xmin;
    r.w.dx = hi_x;              /* read from local → reload from stack */
    int386(0x33, &r, &r);
    ...
}
```

Watcom assigns the new local its own stack slot, eagerly stores the
argument into that slot at function entry, and reloads from it at
the use site — reproducing PS's spill pattern exactly.

A companion form for shift-in-place codegen:

```c
int lock_region(unsigned int addr, unsigned int size)
{
    union REGS r;
    unsigned int hi;
    r.w.ax = 0x600;
    hi = addr >> 16;            /* force shift via temp */
    r.w.bx = hi;
    r.w.cx = addr;              /* low half from saved register */
    hi = size >> 16;
    r.w.si = hi;
    r.w.di = size;
    int386(0x31, &r, &r);
    return r.w.cflag == 0;
}
```

Without `unsigned int hi`, Watcom shifts a *copy* of `addr` (`mov
ebx, eax; shr ebx, 0x10`); with the explicit temp, it shifts the
original (`mov ebx, eax; shr eax, 0x10`) and reads the low half
from `bx` — matching PS.

### When to apply

Only when the diff is purely regalloc (same instruction count, same
total bytes ± a few, just different registers / stack slots) and
the replaced register choice keeps showing up across multiple
sites in the function. Don't add named temps prophylactically —
they can pessimize unrelated functions in the same TU.

### Auto-detection

Both halves of Rule 24 are detected by `c2/commands/rule_hints.py`
and surface as `Hint` column entries in the verifier diff:

* **`Rule 24a`** — spill swap. Keys on a pair of *adjacent* diff
  rows where one row has `mov reg, X` on PS and `mov [esp+N], X`
  on recomp (or vice versa), and the other row has the matching
  swap with a *different* source register. Hint text reads
  `spill swap: PS spills <reg> to stack, recomp keeps it in <reg>`.

* **`Rule 24b`** — shift-in-place vs shift-copy. Keys on a diff
  row where exactly ONE side has `shr <reg>, IMM` and any of the
  surrounding [-1, 0, +1] rows on the *other* side has
  `shr <different_reg>, IMM` with the same shift count. Hint text
  reads `shift-in-place vs shift-copy (PS shr <regA>, recomp shr <regB>)`.

When either hint fires, apply the named-local fix above before
looking elsewhere — the byte diff usually collapses to zero in one
iteration.

### Mechanism

The register allocator in `bld/cg/c/regalloc.c:1034`
(`AssignARegister`) sorts candidate values by a savings metric
and assigns registers greedily.  An arg used in many basic
blocks gets prioritised for a callee-save register; an arg used
at one site competes with locals for a stack slot.

Adding `int hi_x = xmax;` introduces a *new* virtual name with
its own def-use chain and savings calculation.  The new name
inherits the use sites that previously belonged to `xmax`,
leaving `xmax` itself with only the `hi_x = xmax` def site.
The allocator now sees `xmax` as a tiny live range (good
candidate for stack-slot residency) and `hi_x` as the wider one.
The net effect is that `xmax`’s value gets stored to `hi_x`’s
stack slot at function entry and reloaded from there at each
use.

For 24b, the same mechanism applies to the *result* of the shift:
binding it to a named local makes the back-end allocate a
separate virtual name for the post-shift value, freeing the
allocator to mutate the *source* register in place rather than
emitting a copy.

### Sub-rule 24c — Neutral live-range anchor for a local alias

Sometimes a named local alias is useful even when you do **not** want a
stack slot.  You want to keep a value live just long enough that Watcom
allocates the pointer-walk / call-argument block like PS, but you still
want later calls to reload the original global or argument.

The source shape is:

```c
{
    int s = smk;

    if (*(int *)(s + 0x68) != 0) {
        int palptr;
        if (*(int *)(s + 0x6c) == 1)
            palptr = s + 0x70;
        else
            palptr = s + 0x374;
        _PaletteSet(palptr);
    }

    SMACKDOFRAME(smk);
    SMACKNEXTFRAME(smk + (s - s));  /* neutral use keeps `s` live */
}
```

The algebraic expression `smk + (s - s)` is semantically just `smk`,
but it keeps the alias `s` in the live range through the following call.
That can make Watcom choose PS's callee-save register for the earlier
pointer walk while still emitting the global reloads for the real call
arguments.

In `start_smacking`, the natural source held the palette pointer in EAX:

```asm
mov eax, [smk]
cmp [eax+0x68], 0
...
add eax, 0x374      ; 5-byte accumulator encoding
push eax
```

PS instead used ESI:

```asm
mov esi, [smk]
cmp [esi+0x68], 0
...
add esi, 0x374      ; 6-byte non-accumulator encoding
push esi
```

The alias plus neutral anchor collapses the large cascade by forcing the
ESI-shaped palette walk while leaving `SMACKDOFRAME(smk)` and the final
`SMACKNEXTFRAME(...)` call in the same broad shape as PS.

Use this sparingly.  The neutral expression is deliberately non-obvious;
add a source comment at the call site explaining which diff it pins.
Do **not** treat it as a generic optimisation.  It is for cases where:

* a local alias already improves the register class / live range, but
  dies too early unless it is referenced later;
* the later reference must not change program semantics;
* verifier output shows a large register-allocation cascade collapsing
  to a small residual after the anchor is added.

### Verified on

  * `mouserange` and `lock_region` (commit `997715d`);
     auto-detection added in the commit that follows.
  * `start_smacking` (decomp/src/smacker.c, commit `220b770`):
     local `s = smk` plus `SMACKNEXTFRAME(smk + (s - s))`
     reduced the function from 112 to 11 byte diffs by forcing
     PS's ESI palette-walk shape.
  * `tests/oracle/test_rule_24_spill_via_local.py` — 4 tests:
     named local flips which arg is spilled to the stack; same
     function size in both forms (regalloc swap, not byte
     budget); named local for the shift result forces
     `shr eax, 0x10` (in-place) instead of `shr ebx, 0x10`
     (copy); the two shift forms produce different bytes.
  * `show_general_query_panel` (decomp/src/screens.c): a neutral term
     `+ (font1[0] - font1[0])` on a `font_list` register argument forces
     that y-value into its own temp so it lands in ECX (arg4) like PS
     instead of EAX+LEA — closed the function 358→0 b.  See **Rule 98**
     for the full mechanism and the rule that the neutral operand must be
     local to the same call's args.
  * Watcom 10.0a, `-bt=dos -mf -4r -s`.

---

## Rule 25 — byte-offset access vs cell-index access for typed arrays

When `city_map` is declared as `struct city_cell city_map[6400]` and a
caller already has the cell's BYTE offset in a register (e.g. `ref =
(y * 80 + x) * 20`), Watcom 10.0a generates *different* code
depending on how the field is expressed in C:

| C expression | x86 codegen |
|---|---|
| `((struct city_cell *)((char *)city_map + ref))->terrain` | `mov dl, [eax + city_map + 1]`  *(6 B)* |
| `city_map.bytes[ref + 1]` (union) | same as above (6 B) |
| `city_map[cell].terrain`  *where `cell = ref / 20`* | `mov dl, [eax*4 + city_map + 1]`  *(7 B, SIB form)* |
| `(&city_map[cell])->terrain`  *(via local pointer)* | `add eax, &city_map; mov dl, [eax + 1]` *(longer prologue, shorter access)* |

PS.EXE consistently uses the FIRST form: byte offset in a register,
`city_map_base + field_offset` folded into the displacement. To match
the PS bytes, decompiled C code MUST use one of the two forms that
generate `[reg + city_map_disp + N]`:

1. **Byte-offset cast pattern** — the common case:

   ```c
   /* `ref` is a BYTE offset (cell_idx * 20).  Field name lookup
    * via the cast preserves PS's [reg + base + N] codegen. */
   terrain = ((struct city_cell *)((char *)city_map + ref))->terrain;
   ((struct city_cell *)((char *)city_map + ref))->citizen_a = 0;
   ```

2. **Co-existing cell + ref (CSE)** — when both cell index and byte
   offset are needed in the function (e.g. one for struct access,
   the other for storing in `entity.map_ref`):

   ```c
   int cell = y * 0x50 + x;
   int ref  = cell * 0x14;          /* byte offset, stored in entity */
   terrain  = city_map[cell].terrain;          /* uses ref via CSE */
   citizen_list[n].map_ref = ref;
   ```
   Watcom recognises `cell * 20` and `ref` as the same value, keeps
   it in one register, and emits the [reg + base + N] form.

Why not switch the array's declared type to `unsigned char[]`?
Because hand-written struct field access (`.terrain`, `.citizen_a`,
etc.) is far more readable than `+ 1`, `+ 7` magic numbers, and we
need both readability and byte-exactness.

Unrolled 4x clearing loops (PS line numbers confirm 8 separate source
statements per iteration):

```c
int i = 0;
do {
    ((struct city_cell *)((char *)city_map + i))->citizen_a    = 0;
    ((struct city_cell *)((char *)city_map + i))->citizen_b    = 0;
    ((struct city_cell *)((char *)city_map + i))[1].citizen_a  = 0;
    ((struct city_cell *)((char *)city_map + i))[1].citizen_b  = 0;
    ((struct city_cell *)((char *)city_map + i))[2].citizen_a  = 0;
    ((struct city_cell *)((char *)city_map + i))[2].citizen_b  = 0;
    ((struct city_cell *)((char *)city_map + i))[3].citizen_a  = 0;
    ((struct city_cell *)((char *)city_map + i))[3].citizen_b  = 0;
    i += 80;
} while (i < 128000);
```

The extra `[k]` index after the cast bumps the byte offset by
`k * sizeof(struct city_cell)` while still keeping the
`mov [reg + city_map + (k*20+N)], 0` form (PS line numbers 293–302
in `check_citizen_list`).

Watcom 10.0a does NOT auto-unroll a simple `for(i=0;i<6400;i++)`
body under default flags, so the unrolling MUST be expressed in
source. Test with isolated TU: cell-index simple loop emits a
rolled inner body using SIB scaling.

### Why not `-ol+` (loop unrolling)?

In isolation `-ol+` produces *byte-identical* output to PS for a
cell-index 4x-unrolled `clear` loop — it does induction-variable
strength reduction (turning `c * 20 + N` into a stride-of-80 byte
pointer). Tempting!

But `-ol+` REGRESSES many other byte-exact functions (measured by
compiling the whole project with `-bt=dos -mf -4r -s -ol+`):

| File | default flags | with `-ol+` |
|---|---|---|
| common.c | 31 exact / 23 diff | 19 exact / 35 diff |
| gloops.c | 29 / 7 | 26 / 10 |
| lib32.c | 79 / 14 | 67 / 26 |
| web.c | 5 / 0 | 4 / 1 |

Net regression of ~28 byte-exact functions. PS.EXE was NOT compiled
with `-ol+`; the city_map clear loop was manually unrolled in
source using the cast pattern.

### Can we enable `-ol+` per function via pragma?

No. From the Watcom 10.0a C User's Guide (CGUIDE.IHP, *Using
Pragmas to Specify Options*):

> *Currently, the following options can be specified with pragmas:*
> 1. `unreferenced`
> 2. `check_stack`

Only those two switches are togglable with `#pragma on(...)` /
`#pragma off(...)` in Watcom 10.0a. There is no per-function
`#pragma aux ... unroll`, no per-function optimization level, no
`-ol+` equivalent at the pragma level. The `unroll` string in
`wcc386.exe` is error-message vocabulary, not a pragma toggle.

`#pragma aux` modifiers (`aborts`, `parm`, `modify`, `exact`,
`frame`, ...) all describe calling convention or callee behaviour
— none affect loop optimization or strength reduction.

**Conclusion**: the cast pattern is the only way to get PS-equivalent
bytes for cell access without changing global optimization flags.

### Mechanism

Same machinery as Rule 21: the addressing-mode synthesiser in
`bld/cg/intel/c/x86esc.c` folds a constant displacement into a
`[reg + disp]` mode when the byte offset is already register-
resident.

The cast `((struct city_cell *)((char *)city_map + ref))->
terrain` gives the back-end an `O_PTR(O_PLUS(BASE, REF))` tree
at the deref node.  `BASE` is a labelled symbol (folded into the
fixup displacement); `REF` is in EAX.  The constant field offset
(`+ 1` for `.terrain`) folds in too, giving one
`mov [eax + base+1]`.

`city_map[cell].terrain` gives `O_PTR(O_PLUS(O_TIMES(cell, 20),
BASE), 1)`.  Without `-ol+` (loop strength reduction), the
back-end emits the multiplication as ``mov edx, eax; shl eax, 2;
add eax, edx; mov al, [eax*4 + base + 1]`` (distributes 20 = 4 *
5 across the SIB scale and a shift+add) - 16 bytes more.

### Verified on

  * `check_citizen_list`, `clear_all_cm` and other
     `city_map`-heavy functions.
  * `tests/oracle/test_rule_25_byte_offset_vs_cell_index.py` —
     4 tests: byte-offset cast emits a single 6-byte plain
     `[eax + disp]` indexed load with no SIB; cell-index emits
     the load wrapped in shift+add stride multiplication and
     uses SIB `[eax*4 + disp]`; byte-offset is at least 8 bytes
     shorter; cell-index has ≥ 1 `shl` for the strength reduction.
  * Watcom 10.0a, `-bt=dos -mf -4r -s`.

---

## Rule 26 — Two call statements vs one call with a ternary arg

### Symptom

PS.EXE emits an explicit if/else branch around a flag arg — *with
both paths reaching the same `call`* via a tail-merged shared
epilogue. The obvious C using a ternary inside the call argument
folds to `sete` instead.

### Original (PS.EXE) — `explain_forum` at 0x3E1F6

```asm
L489:
    cmp  [out1], 1
    je   end
    xor  ebx, ebx              ; i = 0
loop:
    xor  eax, eax              ; load forum_dept_over (Rule 24-style)
    mov  al, [forum_dept_over]
    cmp  ebx, eax
    jne  else                  ; explicit branch — not sete
    mov  edx, 1                ; if i == forum_dept_over: hilite = 1
    jmp  call                  ; (eax already == ebx, skip the mov)
else:
    xor  edx, edx              ; else: hilite = 0
    mov  eax, ebx              ;       and reload eax with i
call:
    call forum_explanations
    inc  ebx
    cmp  ebx, 0xc
    jl   loop
end:
    pop edx
    pop ebx
    ret
```

Note the asymmetry: the equal-path falls through to the merged
`call` site without re-loading `eax`, because `eax` already equals
`ebx` in that case (it was loaded with `forum_dept_over`, which
the `cmp` just verified equals `ebx`). This is only achievable
through explicit-branch codegen — a sete fold loses the
opportunity.

### Wrong C (sete fold)

```c
for (i = 0; i < 12; i++) {
    forum_explanations(i, i == forum_dept_over ? 1 : 0);
}
```

Watcom emits:

```asm
mov  dl, [forum_dept_over]
cmp  ebx, edx
sete dl
and  edx, 0xff
mov  eax, ebx
call forum_explanations
```

28-byte diff vs PS, completely different shape.

### Right C (explicit branch with two calls)

```c
for (i = 0; i < 12; i++) {
    if (i == forum_dept_over)
        forum_explanations(i, 1);
    else
        forum_explanations(i, 0);
}
```

With **two physically distinct call statements**, Watcom keeps the
branch and tail-merges the calls. Byte-exact match.

### Why

When the compiler sees `(condition ? a : b)` as a sub-expression,
the boolean is materialised into a register *first* and then
passed. With register-calling `-4r`/`-3r`, materialising a 0/1 in
`edx` is cheap with `sete`/`movzx`, so the optimiser collapses the
branch.

When the compiler sees two separate `call` statements with
different constant arguments, it has no incentive to merge them
into a sete. Watcom's tail-merge pass instead notices the calls
are to the same function with the same `eax` value (`i`) and
different `edx` (1 vs 0), so it shares the call instruction itself,
emitting:

* equal branch: `mov edx, 1; jmp call_site`
* else branch: `xor edx, edx; mov eax, ebx; call_site:`

This is *also* what allows the equal branch to skip `mov eax, ebx`
— since `eax` was loaded with `forum_dept_over` for the compare
and the equal branch "knows" `eax == ebx`.

### Detector

Auto-detected (`detect_rule_26` in `rule_hints.py`). Triggers on any
diff row where the recomp instruction is `setcc reg8` (and PS at
that row is not the same `setcc`). PS.EXE contains only **52 `setcc`
instructions across all 2261 functions / 518 KB** (48 functions, mostly 1
each — re-counted 2026-06 by disassembling every code function) — so a
recomp `setcc` paired with a non-`setcc` PS row is a near-certain Rule 26
hit. Regression
test in `tests/test_rule_hints.py::test_detect_rule_26_*`.

### When to apply

When PS shows two `mov` instructions (one per branch) with
different immediates feeding the second register-call argument,
followed by tail-merged convergence at the `call`. Rewrite the
call in C as two separate statements inside `if/else` instead of
one statement with a `?:` flag arg.

Introduced when decompiling `explain_forum` in gloops.c.

### Verified on

  * `explain_forum` in gloops.c (commit `c27f398`).
  * Auto-detector `detect_rule_26` in `rule_hints.py` flags any
     diff row where the recomp instruction is `setcc reg8` and PS
     is not.
  * `tests/oracle/test_rule_26_two_calls_vs_ternary.py` — 4
     tests: ternary form emits `sete`; if/else form has no
     `setcc`; if/else still folds to exactly one `call`
     instruction via Rule 15’s tail-merge; the two forms produce
     different byte shapes.
  * Watcom 10.0a, `-bt=dos -mf -4r -s`.

---

## Rule 28 — Whole-function callee-save register swap

### What we observed

A void(void)-shaped function with a long-lived 32-bit local
produces a function-wide diff that looks like a single-pair
register rename, e.g. PS uses EDI everywhere a value lives,
recomp uses ESI.  The function-level marker is the prologue:
PS pushes one register where the recomp pushes another, with
the same total push count.

```
PS:                           Recomp:
  push ebx                      push ebx
  push ecx                      push ecx
  push edx                      push edx
  push edi   <-- swap           push esi   <-- swap
  …
  bf e0 00 00 00  mov edi, …    be e0 00 00 00  mov esi, …
  89 3d ?? ?? ?? ??  mov [m], edi  89 35 ?? ?? ?? ??  mov [m], esi
  …
  pop edi    <-- swap           pop esi    <-- swap
  pop edx                       pop edx
  pop ecx                       pop ecx
  pop ebx                       pop ebx
  ret                           ret
```

Bytes 0x57 (push edi) vs 0x56 (push esi) differ in the LSB.
Across the whole function body, every encoding that names ESI
(reg/RM field 110b) shows up as EDI (reg/RM field 111b) on PS.

### Mechanism — `GiveBestReg` greedy savings allocator

`bld/cg/c/regalloc.c:GiveBestReg` lines 836-840 (OW v1.0.0,
verbatim in OW v2 master):

```c
if( ( saves > best_saves )
 || ( saves == best_saves
   && HW_Subset( GivenRegisters, reg )
   && !HW_Subset( GivenRegisters, best ) ) ) {
    best = reg;
    best_saves = saves;
}
```

Walks `tree->regs` (the priority list for the type class), picks
the register with maximum `CountRegMoves` savings.  Ties go to
registers already in `GivenRegisters` (i.e. already pushed in
the prologue) — once a callee-save register has been chosen for
ANY long-lived value, every subsequent variable prefers the
same register at zero additional prologue cost (`WorthProlog`
in `bld/cg/intel/c/i86regsv.c:109` returns 0 for already-pushed
registers).

The 32-bit integer priority list is **`DoubleRegs[]`** (the
`RL_DOUBLE` class per `rl.h`; `Reg64Order` is a *different* table
used by other passes, NOT the int type-class list):
`DoubleRegs = EAX, EDX, EBX, ECX, ESI, EDI, EBP` (va 0x821A8;
ESI-before-EDI).  Verified behaviourally:
`docs/codegen-experiments/regalloc-order.py`.

So the first long-lived int value gets EDX, the next EBX, then
ECX, **then ESI, then EDI**.  The ESI↔EDI swap (Rule 28a) is the
tie between the 4th and 5th simultaneously-live values.

### Right C: source-level levers (PROVEN — two co-equal handles)

The equal-savings tie-break is **deterministic** in 10.0a and
responds to two source-level handles.  The exact micro-mechanism
is under investigation — upstream OW v1/v2 `ConfBefore` is strict
savings (no secondary key), so the tie-break must come from either
a hidden secondary key in 10.0a's `ConfBefore` (the project's
`REVCG_CONFFLIP` hook models this as the name-pointer order) or
from ShellSort instability + the conflict-list's pre-sort order
(see `watcom10.0a repo docs/wcc386-re/regalloc-model.md` §3 for the full
discussion).  Both hypotheses predict the same levers below.

**Lever 1 — reorder a use (commute / move a statement).**  This is
the most predictable handle: `liveinfo.c::UpdateLive` walks
instructions backward and creates name nodes as it goes, so a
value referenced earlier on a path usually gets the earlier-allocated
name node and the higher-priority register.

* **Worked, byte-exact** — `change_citizen_targs` (int_c2.c) carried
  a 3-byte EDX↔EBX swap in `cell_idx = dest_y*80 + dest_x`.  PS
  keeps the product (referenced first) in EDX; our recomp put it
  in EBX.  Rewriting commutatively as `dest_x + dest_y*80` makes
  `dest_x` the first-referenced value, flips the pair, and closes
  the diff to **0 bytes**.
* Other handles in the same family: add a use to bump savings
  rank (Rule 1 inline-twice), split/merge a temp to change use
  position, or let a value be consumed into its destination
  register (move-elim, Rule 28b territory).

**Lever 2 — swap the two tied locals' declarations (Rule 115).**
The handle for residue Lever 1 can't reach.  When the use is
pinned by semantics, reorder the declarations themselves — the IL
allocates their name nodes in the new order and the tie flips.
Direction is **not monotonic** in source line (reassignment / IL
structure perturb the name-pointer order), so the procedure is
"try both decl orders and keep the one that verifies."

* **Worked, byte-exact** — `show_help_page` (mmedia.c) carried an
  11-byte ESI↔EDI swap on the tied pair `text_x`/`text_lines`.
  `text_lines` is read early on both sides (a `cap > text_lines`
  compare), so Lever 1 is dead.  Swapping `int text_lines;` and
  `int text_x;` (uses untouched) moved ESI from `text_lines` to
  `text_x` and closed the diff to **0 bytes**.  See Rule 115.

*Savings/use-count outranks both levers* (a value used more
times jumps ahead — Rule 1).  Full model:
`docs/codegen-experiments/regalloc-tiebreak.py`,
`watcom10.0a repo docs/wcc386-re/regalloc-model.md` §3.

**Genuine residue:** when the competing values are CSE-hoisted
globals in a fixed algorithmic sequence (e.g. `update_time`,
`print3_test_info`), Lever 1 is dead (use position pinned) AND
Lever 2 is dead (no named local to reorder — the conflicts are
on temp nodes).  These specific swaps remain residue — the
source has no handle, not because the mechanism is unknown.

### Detector

`_find_rule_28_swap` in `rule_hints.py` is a function-level
pre-scan: it inspects the leading consecutive `push <callee-
save-reg>` instructions and returns `(ps_reg, rc_reg)` if
exactly ONE register differs between the two prologue push
lists.

`detect_rule_28` is a per-row check: a diff row fires Rule 28
when the PS and recomp asm are identical under the
`(ps_reg, rc_reg)` substitution and at least one swap-pair
register name appears on either side.  Numeric-token
mismatches are tolerated only when the bytes are fixup-affected
on both sides (relocated addresses); branch-displacement
differences are explicitly rejected (those are Rule 16
territory).

The "at least one swap-reg token" guard prevents false positives
on rows like `je 0x69` (branch distance differs after a
prologue size change but the row itself doesn't reference ESI
or EDI).

### Rule 28b — Asymmetric callee-save push count

A separate sub-shape: PS pushes more (or fewer) callee-save
registers than the recomp.  Common shapes:

* **PS extra**: PS pushes ebx+ecx, recomp pushes ebx only.
  Examples in lib32.c: `totalXpercent`, `totalXpercentX100`,
  `valueDIVtotal` — PS uses ECX as the IDIV divisor and pushes
  it; recomp uses EBX for the divisor and skips the second push.
  Also `copy_to_physical_screen` — PS uses callee-save EBX for
  a byte read where recomp uses caller-save EAX.
* **Recomp extra**: recomp's regalloc decided to spill into a
  callee-save register that PS didn't need.  Often a
  consequence of a named local that doesn't actually fit into
  a caller-save slot under recomp's regalloc decisions.

The body shape between the two builds diverges enough that we
can't fold body diffs into the rule.  The detector restricts
itself to the prologue/epilogue rows where the **extra**
push/pop instruction lives.  This is intentionally an
informational hint: it identifies the root cause without
trying to explain every cascading body diff.

The push-set scanner skips an optional `push <imm>; call <abs>`
preamble (Watcom's `__CHK` invocation, present on functions
with stack frames ≥ 0x100 bytes) before counting register
pushes.  This lets Rule 28a/28b apply to small math helpers
like `totalXpercent` that begin with a stack-check.

`_find_rule_28b_extras` returns `(ps_only, rc_only)` if the
prologue push sets differ AND each side has at most ONE extra
register beyond the common set.  The single-extra-per-side
restriction keeps the detector focused: more elaborate
divergences are too noisy to flag as a single rule.

`detect_rule_28b` per-row check: a `push reg` or `pop reg` row
on the side that has the extra register fires Rule 28b.  Body
rows are NOT tagged.

#### Source-level lever (Rule 24a-style)

When PS uses an extra callee-save, try adding a named local that
captures the long-lived value.  When recomp uses an extra
callee-save that PS doesn't, try removing a named local or
splitting an expression to reduce live-range pressure.  Most
small `totalXpercent`-style cases have no fix and are documented
as known regalloc artefacts in source comments.

### Verified on

* `new_name_game_loop` in gloops.c — 6 Rule 28 hits (4 unexplained
  rows are Rule 15 cross-function tail-merge artefacts).
* `battle_game_loop` in gloops.c — 3 Rule 28 hits.
* `check_for_promotion` in formulae.c — 2 Rule 28 hits (prologue +
  epilogue; remaining 30 unexplained rows have other causes).
* `tests/oracle/test_rule_28_callee_save_swap.py` — 24 unit tests
  covering prologue scanner, pair-swap detector, per-row
  equivalence check, end-to-end via `detect_hints`, and a
  parametric sweep over all 6 callee-save register pairs.
* OW v1.0.0 source citations: the int type-class priority list is
  **`DoubleRegs[]`** (`RL_DOUBLE`: `EAX,EDX,EBX,ECX,ESI,EDI,EBP`),
  NOT `Reg64Order` — `Reg64Order` (`386rgtbl.c:51`) is only read by
  `Low64Reg`/debug support, never the allocator.  The tie-breaker is
  `bld/cg/c/regalloc.c:854-858` (`GiveBestReg`: `saves==best_saves &&
  HW_Subset(GivenRegisters,reg)` prefers an already-pushed register).
  Bit-identical in OW v2 master.

---

## Rule 29 — DEC vs LEA for in-place global decrement

### What we observed

The two C forms below produce different byte sequences for the same
"decrement-and-store" semantics:

```c
/* Form A: direct global decrement */
if (refused_promotion != 0) {
    refused_promotion--;
}

/* Form B: load into a named local, decrement, store back */
int ref = refused_promotion;
if (ref != 0) {
    ref--;
    refused_promotion = ref;
}
```

* **Form A** emits `mov reg1, [m]; test reg1, reg1; je …; lea reg2,
  [reg1 - 1]; mov [m], reg2` — Watcom uses LEA into a *different*
  register to compute the decremented value, then stores it.  Total
  ~14 bytes.
* **Form B** emits `mov reg, [m]; test reg, reg; je …; dec reg;
  mov [m], reg` — DEC in place on the loaded register, then store.
  Total ~10 bytes.

Bytes saved: ~4 per call site.  PS's
`check_for_promotion::refused_promotion--` (line 89-90) uses
Form B's shape (`dec ecx; mov [m], ecx`); decompilations that
write the obvious `refused_promotion--` get Form A.

### Mechanism

Watcom decides between LEA and DEC based on whether the
just-decremented value is still needed.  When the global is
modified directly via `--`, the value-pool tracker assumes the
*old* value (in the register that was used for the test) might
still be live downstream, so it uses LEA into a fresh register
to preserve the old value.  When the value lives in a *local*,
the tracker can prove the old value is dead after the decrement
and emits the in-place `dec`.

(This is the same general principle as Rule 24a/24b — naming a
local changes the value-pool's analysis of liveness.)

### Right C: write the local-and-store form

```c
int ref;
if ((ref = refused_promotion) != 0) {
    ref--;
    refused_promotion = ref;
}
```

### Caveat

Applying this fix in isolation can cascade through the function
because the saved 4 bytes shift every relative jmp/jcc displacement
downstream, often including a `jmp 0xN` to a shared epilogue
(Rule 15 cross-function tail-merge).  When PS's epilogue is
*tail-merged* with the next function, the recomp must end with
the same `jmp <abs>` byte sequence; an inline `pop … pop … ret`
epilogue ruins the match even though it is locally correct.

For check_for_promotion specifically, applying Rule 29 raises the
function's diff count from 108 → 235 because of this cascade.
Document the rule but leave it un-applied until we can also fix
Rule 15 for that function.

### Verified on

* `tests/oracle/test_rule_29_dec_vs_lea.py` — 7 pytest cases:
  Form A (direct `--`, `--g`, `g -= 1`) produces LEA;
  Form B (named-local with `int x = g; x--; g = x`) produces DEC,
  including the inline-assignment-in-test variant
  (`if ((rp = g) != 0) …`) and the unsigned-local variant.
* PS.EXE: `check_for_promotion::refused_promotion--`
  emits `dec ecx` (1 byte) at +0x05d, matching Form B's shape.
* No detector implemented yet — the cascading-Rule-15 problem
  in `check_for_promotion` makes mass-application unsafe.  Apply
  manually when the surrounding function has no tail-merge.

---

## Rule 30 — Sibling `if` was actually nested in the original source

This is a **decompilation-shape rule**, not a Watcom codegen quirk:
Watcom 10.0a does no value-range propagation, so the only way two
`if`s can be tail-merged at compile time is if the original C
source nested the second inside the first.

### Symptom

The function has two consecutive `if` blocks at sibling level (same
indentation in the decomp output).  In PS.EXE, the failure-path
of the first `if`'s condition jumps **past** the second `if`
straight to the function epilogue (or to a tail-merge target).

```c
/* What the decomp first emitted */
void request_outcome(void) {
    ...
    if (imperial_request < -1 || pct >= 75) {
        ...
        if (imperial_req_amount <= 0) {
            ...
            return;
        }
    }
    if (imperial_request <= -2) {       /* sibling */
        ...
    }
}
```

```
PS at +0x3b:
    cmp eax, 0x4b                  ; cmp pct, 75
    jl  0xd8                        ; rel32 → +0x11c (function epilogue)
    test eax, eax                  ; first-if body starts
    ...
    +0xe7  cmp [imperial_request], -2  ; second-if body
```

Note `jl rel32` lands on the **epilogue**, not on the second-if
test.  The flat sibling form produces a different rel32 because
the compiler emits the second-if at +0xe7 in the !outer path.

### Why it works (the dead-code argument)

Look at the conditions: `!outer ⇒ (imperial_request >= -1 AND pct < 75)`,
which already implies `imperial_request <= -2` is false.  So the
second `if`'s body is dead code in the !outer path.

The original C author wrote it nested:

```c
void request_outcome(void) {
    ...
    if (imperial_request < -1 || pct >= 75) {
        ...
        if (imperial_req_amount <= 0) { ...; return; }
        if (imperial_request <= -2) {   /* nested — only reached
                                            when outer is true */
            ...
        }
    }
}
```

Because the C-level dead-code argument is sound (every path that
runs the inner `if` already ran the outer), the two forms are
behaviourally equivalent — but only the nested form makes the
compiler emit the single-jump shape PS.EXE has.

### How to spot it during decomp

1. The fail-path target of an early condition is the function
   epilogue (or a tail-merge target), **not** the start of the
   next visible block.
2. The visible "second if" lives at a higher offset than that
   target.
3. The two conditions are related such that one implies the
   negation of the other (often: same variable, overlapping
   ranges, or a strict-subset shape).

Run `c2 disasm <fn>` and look at where the jcc lands.  If it's
past a sibling block, that block was nested.

### Why no detector

Detection requires solving the implication on the C side
(`!outer ⇒ !inner`), which is a small SMT problem.  Cheaper to
catch on a case-by-case basis: when a `<<<` row shows a
1-byte rel32-displacement diff and the surrounding diff hunk
points at a sibling-if shape, try nesting.

### Verified on

* `request_outcome` (message.c) — 1 byte-diff at +0x40 fixed by
  nesting `if (imperial_request <= -2)` inside the outer
  `if (imperial_request < -1 || pct >= 75)`.  Discovered while
  triaging Stage 2 candidates.

---

## Rule 31 — `else if (¬outer)` keeps a dead conditional jump

This is another **decompilation-shape rule**: Watcom 10.0a does
not fold away `else if (negation_of_outer)`, even though the
inner test is provably always true after the outer `if` failed.
The compiler emits the redundant `cmp` and an *unreachable*
`jcc` past the body, which then shows up in PS as a "dead"
branch instruction the recomp omits.

### Symptom

PS asm has a conditional jump at the start of an `else` block
whose condition is the **opposite** of the outer `if`.  After
the outer test was false, the new `cmp` is redundant and the
`jcc` always falls through.  The recomp emits a plain `else`
(no inner cmp) so it's 2 bytes shorter.

```text
PS                       recomp (else without inner test)
cmp dl, dh
jle else                 cmp dl, dh
(>): branch1; jmp store  jle else
else:                    (>): branch1; jmp store
  jg end       ←dead     else:
  branch2; fall to store    branch2; fall to store
end:                     end:
```

### Right C

When the dead jcc shows up, write the source as `else if (X)`
where X is the negation of the outer condition:

```c
if (dest > home) dest = home + rand - 3;
else if (dest <= home) dest = home + rand - 5;   /* always true */
```

**Do not** simplify to a plain `else`:

```c
if (dest > home) dest = home + rand - 3;
else dest = home + rand - 5;     /* drops the dead jcc */
```

### Why no detector

The diff signature is a single 2-byte `+RC delete` row right
at the start of the else block, with the deleted bytes a
2-byte short jcc whose target is past the else body.  This
overlaps with Rule 16 (short-vs-near jcc cascade) so a
mechanical detector would false-positive constantly.  Easier
to spot by reading the diff: if the missing jcc is a `jg`
(after `jle`) or a `jl` (after `jge`) etc., it's the
negation-of-outer pattern.

### Why does Watcom keep the redundant test?

The C-front-end lowers `if/else if/else` chains into a
sequence of `BLOCK { TEST → JMP-out }` IL nodes
**before** flow analysis.  Watcom 10.0a's flow optimiser
(`bld/cg/c/fixfind.c`) does merge identical jcc tails (Rule
15) but it does **not** propagate "outer condition was false"
into the inner block to recognise the inner test as
constant-true.  No `IsConstantTrue()`-style fold runs at this
stage; the inner `cmp+jcc` survives intact.

Plain `else` short-circuits this entirely because there's no
`TEST` IL node — just a `JMP-out` of the outer-if body and a
fall-through label.

### Verified on

* `random_target` (int_c2.c) — 4 byte diffs at +0x29, +0x63 and
  the corresponding Y-axis offsets fixed by changing both
  `else if (dest_x < x)` / `else if (dest_y < y)` to
  `else if (dest_x <= x)` / `else if (dest_y <= y)`.  This is
  *semantically* the same since the outer `>` test already
  excluded the `>` case.  Confirmed byte-exact.

## Rule 32 — `goto` triggers `O_IF_TRUE`, preserves the original jcc opcode

PS occasionally emits a conditional jump using the **literal**
operator from the source — `ja` (0x77) for `> 0` unsigned, `jl`
(0x7c) for signed `< X`, etc. — without Watcom's usual
`FlipCond` rewrite.  The pattern is:

```
test  bl, bl
ja    forward_label          ; original opcode preserved!
... fall-through block ...
jmp   end
forward_label:
... body ...
end:
```

Whereas the equivalent `if (x > 0) { body } else { fall-through }`
emits `jbe end_label` (the operator was flipped because Watcom
swaps THEN/ELSE block layout to put THEN as the immediate fall-
through, and `DoCondJump` calls `FlipCond` whenever
`dest_true == dest_next`).

### What you must write in C

Use **`goto`** to force the original jcc opcode to survive:

```c
if (home_x > 0) goto check_max;
target_x++;
goto skip;
check_max:
if (home_x >= 0x3b)
    target_x--;
skip: ;
```

This corresponds to the Watcom AST emitting `OPR_JUMPTRUE` (→
`O_IF_TRUE` in the back-end) instead of the if-statement's
default `OPR_JUMPFALSE` (→ `O_IF_FALSE`).  In `O_IF_TRUE`, the
TRUE-edge points at the **goto label** (a different block from
the immediate fall-through), so `dest_true != dest_next` and
`FlipCond` is skipped.

### What Watcom emits if you write the obvious if/else

```c
if (home_x > 0) {
    if (home_x >= 0x3b) target_x--;
} else {
    target_x++;
}
```

Watcom evaluates `home_x > 0` (`OP_CMP_GREATER`), but
`OPR_JUMPFALSE` makes `dest_true = THEN-block = next block`.
`FlipCond` then rewrites the opcode to `OP_CMP_LESS_EQUAL` and
emits **`jbe`** (0x76) skipping past the THEN block to the ELSE
block.  Functionally equivalent, byte-different.

### Discovery

Tested with Watcom 10.0a directly:

```c
unsigned char x = arr[idx];
if (x > 0) goto check_max;
gv++;
return;
check_max:
if (x >= 0x3b) gv--;
```

→ emits `test al, al ; ja 0x16` (0x77 0x07) — the literal
`ja`.

The equivalent `if (x > 0) { if (x >= 0x3b) gv--; } else gv++;`
→ emits `test dl, dl ; jbe 0x24` (0x76 0x14) — flipped to
`jbe`.

Compiler source confirms (`bld/cg/c/encode.c::DoCondJump`):

```c
if (dest_next != NULL) {
    if (dest_true == dest_next && dest_false != NULL) {
        FlipCond(cond);                     // <- the flip
        dest_true  = dest_false;
        dest_false = dest_next;
    }
}
```

`O_IF_TRUE` (set by `goto` at AST level via `OPR_JUMPTRUE`)
makes `dest_true = goto_label != next_block`, so the flip is
skipped.

### Why does PS.EXE use this?

PS.EXE was compiled without `-ob` (branch prediction; `-ob`
isn't available in 10.0a anyway, only in OW v2; the closest
v10 equivalent is `-ox` which Set_OX expands to include
`BRANCH_PREDICTION` but PS.EXE wasn't built with `-ox`).  So
`SortBlocks` returns early and block layout = source order.
The original C source must have used explicit `goto` to force
the unflipped jcc — likely because the developer wanted the
`> 0` predicate to remain visible at the asm level (hot path
hint).

### Verified on

* `sa12_army_sail_home` (int_c2.c) — both axis nudge blocks.
  Without `goto`, recomp emits `jne` (after FlipCond) where PS
  emits `ja`; with `goto`, byte-aligned (modulo 9-byte regalloc
  residual).

### Detection

Diff row:
```
-PS  77 [N]    ja  forward
+RC  75 [N]    jne forward
```
or other un-flipped vs flipped jcc opcode pair (`jbe`↔`ja`,
`jle`↔`jg`, `jb`↔`jae`, etc.) accompanied by *no* surrounding
layout differences — i.e. the function's block order matches.
If the rest of the function is byte-exact, the cause is almost
always Rule 32: the original C used `goto`.

### Why no detector

The pair `jne` vs `ja` after `test r, r` (or `cmp [..], 0`) is
near-impossible to distinguish from a Rule 8/9 polarity issue
without manually inspecting the surrounding control flow.  Add
a hint manually if a single 1-byte jcc-opcode diff is the only
remaining residual.

## Rule 33 — Three-lever combo for 2D-region scans (IV-substitution + LICM + int return)

### Trigger

A small 2D loop scanning a rectangular region of `city_map`
(or any large flat array) with a per-cell test, often with an
early-exit `return 1` and a final `return 0`.  PS emits the
loop with **all three** of:

1. **Induction-variable substitution**: the cell address is held
   in a single register that is advanced linearly:
   `add eax, 0x14` inside the inner loop, `add eax, edi` between
   rows (where `edi` holds the row-end stride `1600 - n*20`).
   No `i*1600 + j*20` recomputation per iteration.

2. **LICM hoist of the row stride**: `mov edi, 0x640; sub edi, edx`
   (where `edx = n*20`) executed **once before** the outer loop,
   stashed in a callee-saved register (`edi`).  The row
   transition is then a 2-byte `add eax, edi`.

3. **32-bit return-value writes**: `mov eax, 1` (5 b) for the
   early-exit and `xor eax, eax` (2 b) for the final return,
   *not* the 8-bit `mov al, 1` / `xor al, al` forms — even when
   the function logically returns a boolean.

Default flag set (`-bt=dos -mf -4r -s`) emits ALL THREE
"obvious" forms unless the source is written carefully:

* No IV substitution — `i*1600 + j*20` recomputed every iter
  (~30 b extra in a 4-deep loop).
* No LICM — `n*20` and `1600 - n*20` recomputed each outer iter
  (~12 b extra, plus an extra register save).
* `mov al, 1` / `xor al, al` — saves 3 b vs PS but breaks the
  exact match.

### What you must write in C

Three coordinated source-level levers, *all required*:

```c
int test_for_any_admin(int cm_ptr, int n)
//  ^^^                                          (lever 3 — int return)
{
    int i, j;
    int eax = cm_ptr;                          /* lever 1 — running pointer */
    int stride = 1600 - n * 20;                /* lever 2 — hoisted stride  */
    for (i = 0; i < n; i++, eax += stride) {   /* per-iter advance in for-clause */
        for (j = 0; j < n; j++, eax += 20) {   /* same — Rule 4 order:
                                                  inc edx; add eax, 0x14   */
            char b = ((char *)city_map)[eax + 0xA] & 0x0C;
            if (b) {
                return 1;
            }
        }
    }
    return 0;
}
```

The four moving parts:

* **`int eax = cm_ptr`** — naming a local `int` that holds the
  byte offset from the array base teaches Watcom that the loop
  has a single linear induction variable, which it then
  collapses with the implicit `i*1600 + j*20` index expression.
  Without this, Watcom emits the multiplication chain inline.

* **`int stride = 1600 - n*20`** — naming the row-end stride
  *outside* both loops makes Watcom hoist the shift-add chain
  computing `n*20` plus the `0x640 - …` subtraction into the
  prologue, parking the result in a callee-saved register.
  Without this, the chain is recomputed inside the outer loop
  every iteration.

* **`int` return type** (not `char`) — even though the function
  is logically boolean, declaring it `int` makes Watcom emit
  `mov eax, 1` (full 5-byte form) and `xor eax, eax` (full 2-byte
  zero) at the return paths.  With `char` return, Watcom would
  emit `mov al, 1` / `xor al, al` — 3 bytes shorter overall but
  byte-different from PS.  The caller-side cost is zero: callers
  treat the result as `0` or non-zero, both fit in `al`.

* **Per-loop advance in the `for` increment clause**
  (`for (j = 0; j < n; j++, eax += 20)`) — Rule 4 source-order
  means Watcom emits `inc edx; add eax, 0x14` (counter first,
  pointer-advance second) to match the C comma expression's
  left-to-right order.  Putting `eax += 20;` at the end of the
  loop body would emit `add eax, 0x14; inc edx` (pointer first)
  instead, producing a 2-byte instruction-pair reorder (Rule 27
  family).

### What Watcom emits if you write the obvious form

```c
char test_for_any_admin(int cm_ptr, int n) {        /* char return */
    int i, j;
    char *cm = (char *)city_map;
    for (i = 0; i < n; i++) {
        for (j = 0; j < n; j++) {
            if (cm[cm_ptr + i*1600 + j*20 + 0xA] & 0x0C)
                return 1;
        }
    }
    return 0;
}
```

PS:        74 bytes, IV-substituted, LICM-hoisted, 32-bit ret.
Recomp:    99 bytes (+25), every iter recomputes both
           `i*1600` and `j*20`, no hoist, 8-bit ret.

### Discovery

Test bed: `/tmp/iv-test/test{1..12}.c` against
`uv run c2 oracle compile -f test_for_any_admin -c "-bt=dos -mf
-4r -s"` (default flag set, no `-ol`).  Iteratively narrowed:

* `test1.c` — natural 2D index → 99 b (worst).
* `test2.c` — running pointer (`char *cm = … + cm_ptr; cm += 20`)
  → 76 b; gained IV substitution but no LICM.
* `test4.c` — `int eax = cm_ptr` (named-local int variant of the
  running pointer) + index `[eax + 0xA]` → 74 b but **not byte-
  exact**: still missing LICM and using `mov al, 1`.
* `test8.c` — added `int stride = 1600 - n*20` LICM-hoist → 71 b,
  closer but still 8-bit ret.
* `test10.c` — promoted return type to `int` → 74 b structural
  match, only 2 instruction-pair reorders left at the loop tails.
* `test12.c` — moved the per-iter advance into the `for`
  increment clauses (`for (j = …; …; j++, eax += 20)`) → **74 b
  byte-exact** to PS.

`-ol` (loop optimizations on) does NOT help: it triggers an
extra `ebp` push for a "j-seed register" that PS doesn't have
(71 b vs PS 74 b but byte-different).  PS is compiled *without*
`-ol`; the IV substitution there falls out of the default
opt level when the source is written with a named running-
pointer int.

### Open Watcom mechanism

`bld/cg/c/loopopts.c::LoopRegInvariant()` walks each loop and
hoists computations whose operands don't change inside the loop
body.  `int stride = 1600 - n*20` *outside* the outer loop is
recognized as loop-invariant and hoisted; the same expression
inline at the row-transition site is *not* hoisted because the
analysis is local to the loop body.

`bld/cg/c/optcom.c::IndVarFold()` recognizes a single integer
variable updated by a constant (`eax += 20`) inside a loop and
elides the loop-counter-times-stride recomputation that the
high-level translator would emit for `arr[i*N + j*M]`.  The
compiler's heuristic: it must see an existing scalar increment
in the source — if you write `arr[i*1600 + j*20]`, the multiplies
are visible expressions and the optimizer doesn't replace them
with an induction variable unless `-ol` is set (and even then,
only with a less-aggressive form).

### Verified on

* `test_for_any_admin` (census.c) — 74 b byte-exact (commit
  TBD; was the original probe function).

### When this rule does NOT apply

`affected_by_cover1` / `affected_by_cover2` (map.c) have the same
2D-region-scan shape but *PS does not IV-substitute them*.
Differences that block the rule:

1. They take a `struct city_cell *p` (typed pointer) plus an
   early-out for `range == 1` — the early-exit branch suppresses
   IV substitution.
2. They spill a `char mask` parameter to a stack slot
   (`mov [esp], bl`) — register pressure is too high for the
   running-pointer trick.

For functions matching the "1-arg cm_ptr int + 1-arg int
range, no early-out, no spilled mask" silhouette, Rule 33
applies as written.  For the harder shape (early-out, mask
spill, struct typed pointer) the IV-substitution path in PS
is disabled, and Rule 39 (byte-pointer cast for separate-
offset 2D fold) covers the byte-exact form for that shape.

### No detector

The diff signature is "30+ bytes of multiplication-chain
recompute differences" which overlaps with general "we picked
the wrong source form" failures.  Hand-detect by spotting:

* PS uses `add eax, 0x14` inside the inner loop (the linear
  pointer advance).
* PS hoists a stride into a callee-saved register before the
  outer loop.
* PS emits `mov eax, 1` / `xor eax, eax` (5 b + 2 b) at the
  return paths.

If all three are present in PS and missing in recomp, apply
Rule 33.

---

## Rule 34 — Loop counter init: `xor reg,reg; .top: inc reg; cmp reg, N` is a literally-emitted source pattern

### Trigger

PS shows a counted loop whose prologue is

```asm
    xor  esi, esi             ; counter = 0
.top:
    inc  esi                  ; counter += 1
    cmp  esi, 0x7d0
    jge  .end
    ...                       ; body uses counter values 1..0x7cf
    jmp  .top
.end:
```

— i.e. the **counter starts at 0**, is **incremented at the
top of the loop body**, and the **comparison is the second
operation** of every iteration.  The body sees values 1, 2,
…, 0x7cf (never 0).

The natural-looking C form

```c
for (i = 1; i < 0x7d0; i++) {
    /* body uses i = 1..0x7cf */
}
```

emits a *different* prologue:

```asm
    mov  esi, 1               ; 5 bytes (vs 2 for xor)
    jmp  .test                ; or no jmp + reordered layout
.top:
    ...
    inc  esi
.test:
    cmp  esi, 0x7d0
    jl   .top
```

Two byte-level differences:

1. **`mov esi, 1`** (5 b) vs **`xor esi, esi`** (2 b) at the
   init.  Watcom does *not* rewrite `mov reg, 1` into
   `xor reg, reg; inc reg`.
2. The `inc esi` lands at the **bottom** of the body, not the
   top, so the byte layout of the loop body differs (and any
   inner `jmp .top` / `je .top` short-jumps shift by 1–2 bytes).

### What you must write in C

Spell out the increment-at-top form literally:

```c
i = 0;
while (1) {
    i++;
    if (i >= 0x7d0) break;
    /* body, here i is 1..0x7cf */
}
```

Or equivalently with a `do { … } while (1)` and a labelled
break; both lower to the same IR.  The defining feature is
that **the increment statement comes before the test**, in
source order, inside the loop body.

### What Watcom emits if you write the obvious form

`for (i = 1; i < N; i++)` produces the `mov reg, 1` /
increment-at-bottom pair shown above.  Functionally equivalent,
byte-different.

The “rotate `for(i=1)` into `xor+inc-at-top`” transform is **not**
in Watcom 10.0a's loop-opt pass: `bld/cg/c/loopopts.c` has IV
substitution and LICM but no init-form rewriter.  The IR you
emit is the IR you get.

### Mechanism

The C front-end (`bld/cc/c/cstmt2.c` `CForStmt`) lays out a
`for ( init ; test ; step ) body` as

```
init;
test_label:
if !test goto end;
body;
step;
goto test_label;
end:
```

— init is *outside* the loop, step is at the *bottom*.  When the
init expression is the integer literal `1`, the back-end emits
`mov reg, 1` (no special case for "init = 1, body uses inc"
fusion).

The hand-rolled `i = 0; while (1) { i++; if (...) break; ... }`
form lays out as

```
i = 0;
loop_label:
i = i + 1;
if (i >= N) goto end;
body;
goto loop_label;
end:
```

— init is the literal `0`, which `bld/cg/c/foldins.c` recognises
and emits as `xor reg, reg` (2 b vs 5 b for `mov reg, 0`); the
increment is the first statement of the body, so it lands at the
top of the emitted loop.

Both forms execute the body the same number of times with the
same counter values; only the byte layout differs.

### Sub-pattern: pre-inc snapshot — `while (i++ < N)`

A close cousin of the increment-at-top pattern.  Some loops
have a slightly different shape — the cmp tests the **pre-
increment** value:

```asm
    xor  edx, edx              ; counter = 0
.top:
    mov  eax, edx              ; eax = i (pre-inc snapshot)
    inc  edx                   ; i++
    cmp  eax, 0xa
    jge  .end
    ...                        ; body
    jmp  .top
.end:
```

`eax` holds the pre-inc value (`i`), `edx` ends each iteration
holding the post-inc value (`i+1`, the next iteration's `i`).
The body sees `eax = 0, 1, …, 9` (never 10).  The 1-byte
`mov eax, edx` + 1-byte `inc edx` pair is the giveaway, vs the
plain Rule 34 form's 1-byte `inc reg` alone.

The matching C source is the post-increment-in-test idiom:

```c
i = 0;
while (i++ < 10) {
    /* body, here i is already incremented (1, 2, …, 10),
       but the comparison saw the pre-inc value (0..9). */
}
```

`for (i = 0; i < 10; i++)` lowers to test-at-bottom (no
snapshot mov, plain `cmp edx, 10; jl .top` after the body's
`inc edx`).  Same iteration count, byte-different.

Verified on `get_rand_max` (lib32.c, 0x2817B) — byte-exact
after switching the `for (i = 0; i < 10; i++)` retry loop to
`i = 0; while (i++ < 10) { … }`.  26 byte diffs collapsed to
zero.

### Verified on

- `get_next_word_length` (lib32.c, 0x2729B) — byte-exact after
  switching from `for (i = 1; i < 0x7d0; i++)` to
  `i = 0; while (1) { i++; if (i >= 0x7d0) break; ... }`.
  The natural for-loop form produced 69 byte diffs, all
  cascading from the prologue's `mov esi, 1` vs PS's
  `xor esi, esi`.
- `get_rand_max` (lib32.c, 0x2817B) — byte-exact after
  switching from `for (i = 0; i < 10; i++)` to
  `i = 0; while (i++ < 10) { … }` (the post-inc-snapshot
  sub-pattern above).
- Watcom 10.0a, `-bt=dos -mf -4r -s`.

### Detection hint

The diff signature is **`mov reg, 1` (5 b) replaced by
`xor reg, reg` (2 b)** at the loop init, with the loop body's
internal jumps all shifted by ≈3 bytes downstream.  Whenever
PS's loop prologue is a 2-byte `xor reg, reg` and the body
references the counter starting from 1, the source is the
increment-at-top while-loop form, not `for (i = 1; …; i++)`.

For the post-inc-snapshot sub-pattern, the giveaway is the
**`mov eax, edx; inc edx; cmp eax, N`** triple at the loop
top (where edx is the running counter and eax is the per-
iteration snapshot).  The natural `for (i = 0; i < N; i++)`
emits no snapshot — `cmp edx, N` directly against the post-
inc value.

---

## Rule 35 — Byte-by-byte LE word load: low-byte-first source order

### Trigger

PS reads a packed little-endian 16-bit (or 24-bit) integer
**byte by byte** out of a `char *` buffer (typical for fixed-
layout binary file formats), and emits this exact shape:

```asm
    xor  edx, edx                   ; clear high half once
    mov  dl, [esi + eax + 1]        ; load HIGH byte into dl
    shl  edx, 8                     ; shift in place — edx = high << 8
    movzx edi, byte ptr [esi + eax] ; load LOW byte zero-extended
    add  edi, edx                   ; combine
    mov  [target_global], edi
```

— a 16-byte sequence per `u16` slot.  Notable features:

1. The high byte is loaded into `dl` (8-bit reg part of the
   just-cleared `edx`), then the **whole 32-bit `edx`** is
   shifted left 8 (3-byte `shl edx, 8`).  This is shorter than
   `movzx edx, byte ptr […+1]; shl edx, 8` (5 + 3 = 8 b vs
   PS's 4 + 3 = 7 b).
2. The low byte uses `movzx edi, byte ptr […+0]` — a separate
   register, allowing the next `add` to be a 2-byte two-reg
   form rather than another `mov + xor + add`.

### What you must write in C

Spell out the addition with the **low byte FIRST**, the
shifted high byte SECOND:

```c
sprite_width  = buf[k]     + (buf[k + 1] << 8);
sprite_height = buf[k + 2] + (buf[k + 3] << 8);
sprite_start  = buf[k + 4] + (buf[k + 5] << 8) + (buf[k + 6] << 16);
```

(`buf` typed as `unsigned char *`.)  The `<< 8` operand has
to be the right-hand operand of `+` so Watcom evaluates it
into the holding register `edx` and lets the low byte be
loaded straight into a fresh `edi` via `movzx`.

### What Watcom emits if you write the obvious form

The natural high-first form

```c
sprite_width = (buf[k + 1] << 8) + buf[k];
```

emits a different shape — the high byte ends up in `edi` (the
LHS operand reg) and the low byte has to be re-routed
through `edx`:

```asm
    xor  edx, edx
    mov  dl, [esi + eax + 1]
    mov  edi, edx                 ; copy edx → edi (extra)
    shl  edi, 8                   ; shift the COPY (not edx)
    xor  edx, edx                 ; clear edx for the next byte (extra)
    mov  dl, [esi + eax]
    add  edi, edx
    mov  [target_global], edi
```

That's `mov edi, edx` (2 b) + `xor edx, edx` (2 b) = **4
extra bytes per word load**, and it cascades through every
subsequent packed-int field of the same record.

### Mechanism

Watcom's expression evaluator (in `bld/cg/c/foldins.c` and
the back-end's temp-allocation pass) walks `+` expressions
left-to-right, allocating a destination register for the
LHS and a temp register for the RHS.  When the LHS is a
simple byte load, the dest reg picks up the load; when the
LHS is a shifted byte (`(byte) << 8`), the dest reg picks
up the **shifted** value, forcing the RHS byte into a
secondary register.

Putting the unshifted byte on the LHS means the dest reg
becomes `edi` via the `movzx` of the low byte, and the
already-prepared `edx` (holding the shifted high) is added
to it directly.  This is the only source-level lever that
selects between the two equivalent emit shapes — Watcom
does not commute `+` operands during code emission.

### Verified on

- `write_image` (lib32.c, 0x27CB3) — byte-exact after
  reordering all three packed-word loads from
  `(buf[k+1] << 8) + buf[k]` (high-first) to
  `buf[k] + (buf[k+1] << 8)` (low-first).  127 byte diffs
  collapsed to zero.  Same pattern verified on the 24-bit
  `sprite_start` load (`buf[k+4] + (buf[k+5] << 8) +
  (buf[k+6] << 16)`).
- Watcom 10.0a, `-bt=dos -mf -4r -s`.

### Detection hint

The diff signature is the **insert** of `mov edi, edx; …;
xor edx, edx; mov dl, …` between PS's `shl edx, 8` and
`movzx edi, …`.  Look for repeated `xor edx, edx; mov dl,
[…]; shl edx, 8; movzx edi, […]; add edi, edx` blocks in
PS's disassembly — those are the byte-by-byte LE word
loads, and any source that gets them wrong fails the same
way 4 bytes per slot.

### Sub-pattern 35a — Combine operator: `+` not `|`

PS emits `add eax, edx` (opcode `01 D0`) for the final
combine of low + (high << 8).  Watcom does **not**
canonicalize `|` (bitwise OR) into `+` (add) even when the
operands are provably non-overlapping (one is a byte 0x00–
0xFF, the other is `byte << 8` with low byte zero).  So
writing

```c
val = buf[k] | (buf[k + 1] << 8);
```

emits `or eax, edx` (`09 D0`) instead of `add eax, edx`,
producing a 1-byte diff at the combine site (and may
cascade through downstream regalloc).

**Rule**: when reading packed little-endian words byte-by-
byte to combine into an integer, **always use `+`**, never
`|`, even though both are semantically equivalent for non-
overlapping byte fields.

Verified on `place_legend_block` (screens.c, 0x627B6) —
changing `|` to `+` collapsed a 1-byte combine diff at
+0x20.

### Sub-pattern 35b — Operand order biases regalloc beyond byte loads

Rule 35's left-to-right `+` walk also picks register
allocation for **non-byte** sub-expressions.  Specifically,
when an additive expression mixes a multiplicative term and
an additive term, the C source order picks which sub-
expression evaluates into which register:

```c
/* Form A — multiplication on RHS: */
place_2x2_block(addr, (x + xo) + (y + yo) * screen_width);
```

emits

```asm
    lea  edx, [esi + ecx]            ; edx = y + yo  (RHS sub-expr)
    imul edx, [screen_width]          ; edx = (y+yo)*sw
    lea  eax, [edi + ebx]            ; eax = x + xo  (LHS)
    add  edx, eax                     ; edx += eax
```

```c
/* Form B — multiplication on LHS: */
place_2x2_block(addr, (y + yo) * screen_width + (x + xo));
```

emits the *register-swapped* shape:

```asm
    lea  eax, [esi + ecx]            ; eax = y + yo
    imul eax, [screen_width]          ; eax = (y+yo)*sw
    lea  edx, [edi + ebx]            ; edx = x + xo
    add  edx, eax                     ; edx += eax
```

Same arithmetic, swapped registers (`edx` vs `eax` for the
multiplied value).  PS picks one specific shape;  matching
it requires writing the source operands in PS's order, not
the "natural" multiplied-first form.

**Mechanism**: Same as Rule 35's main pattern.  Watcom
allocates a register for the LHS first; subsequent RHS sub-
expressions get a secondary register.  The `imul` lands in
whichever register holds the multiplicand at evaluation
time, which is the FIRST sub-expression encountered.

**Rule**: when an `add`-of-two-subexpressions assigns to a
register at a call-site, examine PS's `lea/imul/add` chain
and write the C operands in PS's left-to-right register
order.

Verified on `place_legend_block` (screens.c, 0x627B6) —
swapping `(y+yo)*sw + (x+xo)` to `(x+xo) + (y+yo)*sw`
collapsed 3 byte diffs at +0x2C/+0x30/+0x36 to zero.

## Rule 36 — Shared-constant register cache: name a local for `1` to defeat per-store immediate folding

### Trigger

PS materialises a small constant (typically `1`) into a
register **once** and re-uses it across multiple statements
within the same basic block:

```asm
    mov  ebp, 1                          ; materialise the 1
    mov  [mouse_movement],   ebp         ; store via reg
    mov  [mouse_was_pressed], ebp         ; store via reg
    ...
    cmp  eax, ebp                         ; compare via reg
    ...
```

This shape is hot in event-decoder routines that flag several
status globals together and then test a value against the
same constant.  PS pays 5 bytes once for the `mov ebp, 1` and
then 6 bytes per `mov [mem], reg` store and 2 bytes for `cmp
eax, reg`, vs the natural form's 10-byte `mov [mem], imm`
and 3-byte `cmp eax, imm`.  When three or more uses cluster
in one block, the shared-register form is **shorter overall**
and so Watcom prefers it — but only when the source
explicitly names the constant.

### What you must write in C

Declare a local int initialised to the shared constant and
use that name everywhere the constant appears in the cluster:

```c
int one;
...
if (button_changed) {
    one = 1;
    movement     = one;          /* mov [movement],     <reg> */
    was_pressed  = one;          /* mov [was_pressed],  <reg> */
    if (button == one) {         /* cmp <reg>, <reg> */
        preclick = 1;
    } else if (button == 0) {
        click = 1;
    }
}
```

The `one` local is a no-op semantically (it's just `1`) but
it gives Watcom a single SSA value to keep alive in a
register across the three uses.

### What Watcom emits if you write the obvious form

The natural

```c
movement     = 1;
was_pressed  = 1;
if (button == 1) { ... }
```

constant-folds each `1` into its own immediate at code-gen
time:

```asm
    mov  [movement],    1                 ; 10 bytes (C7 05 ?? ?? ?? ?? imm32)
    mov  [was_pressed], 1                 ; 10 bytes
    cmp  byte ptr [button], 1              ; 7 bytes (or load+cmp)
```

Three independent 10/7-byte sequences, no register cache.
Diff vs PS: ~10 bytes per cluster.

### Mechanism

Watcom's expression-tree builder treats each `= 1` and
`== 1` as an independent `IConst(1)` node.  The constant-
folding pass in `bld/cg/c/foldins.c` does NOT
common-subexpression-eliminate identical immediates across
statement boundaries — CSE only sees them as equal trees
when they share an SSA name.  Naming the constant via a
local int gives the front-end a `OPR_PUSHADDR + OPR_POINTS`
load tree that the back-end's IV-substitution pass turns
into a single register live-range covering all three uses.

### Verified on

- `get_mouse` (lib32.c, 0x25CCC) — byte-exact after
  switching from three independent `= 1` / `== 1` lines to
  a per-side `int one = 1; mouse_movement = one;
  mouse_was_pressed = one; if (button == one) ...`.  PS
  uses `ebp` for the left-button cluster and `edx` for
  the right-button cluster (they're separate basic blocks,
  so the cache doesn't cross between them).  All other
  diffs in the function were already explained by Rule 35
  (LE byte loads) plus the implicit-int rule for
  `sim_mouse` (Rule 37).
- Watcom 10.0a, `-bt=dos -mf -4r -s`.

### Detection hint

In a single basic block, look for **two or more** stores of
the same small immediate (most often `1`) followed by a
`cmp reg, imm` against the same value.  If PS uses
`mov [mem], reg` (6 b each) and `cmp reg, reg` (2 b) where
RC produces `mov [mem], imm` (10 b each) and `cmp reg, imm`
(3 b), the lever is missing — name the shared value as a
local int.

The rule applies to **any** small constant, not just `1`,
but the saving (10−6 = 4 bytes per store) is largest when
the immediate is non-zero (`mov [mem], imm` is uniformly
10 bytes regardless of value, while `mov [mem], reg` is
always 6 bytes).  For `0` the natural form's
`mov [mem], 0` is also 10 bytes, but Watcom additionally
peepholes `xor reg, reg; mov [mem], reg` for clusters,
which is 8 bytes — still 2 bytes worse than PS's
`xor reg, reg + mov [mem], reg + mov [mem], reg` (2 + 6 +
6 = 14 vs 10 + 10 = 20 for two stores).  Any time you see
`mov reg, imm` followed by multiple `mov [mem], reg` in
PS, suspect Rule 36.

---

## Rule 37 — Forward-declare callee return type before first use, or implicit-int wins

### Trigger

PS's call site uses an **8-bit** read of the return value
(`test al, al` / `mov [byte_global], al` after a call), but
RC emits a **32-bit** read (`test eax, eax` / `mov [int_global],
eax`) — a 1-byte miss at the test instruction plus possible
cascade through subsequent compare/store widths.

This happens when the callee is **defined later in the same
TU** (or in a different TU entirely) with a `char` return
type, but the **first call site doesn't see a prototype**, so
C89's "implicit int" rule kicks in and the front-end records
the return type as `int` for that call.

### What you must write in C

Forward-declare the callee with its real return type **before
the first call**, in the same TU:

```c
extern char sim_mouse(void);          /* must precede first use */

void get_mouse(void)
{
    if (sim_mouse() == 0) {           /* test al, al — 2 bytes */
        read_mouse();
    }
    ...
}

char sim_mouse(void)                  /* definition (anywhere) */
{
    return 0;
}
```

Putting the `extern` declaration **after** the first call
is too late — the call's IR already committed to `int`.

### What Watcom emits if you write the obvious form

Without the forward declaration:

```c
void get_mouse(void)
{
    if (sim_mouse() == 0) {           /* test eax, eax — 2 bytes BUT WRONG WIDTH */
        ...
    }
}

extern char sim_mouse(void);          /* TOO LATE — first call already lowered */
char sim_mouse(void) { return 0; }
```

… emits `test eax, eax` (`85 c0`) where PS has `test al, al`
(`84 c0`).  Same byte count but the **opcode** differs.
Diff = 1 byte at the test, plus any cascade if the truncated
value is then stored to a `char` global (PS's `mov
[byte_global], al` is 5 bytes; RC's `movzx eax, al; mov
[byte_global], al` would be 8).

### Mechanism

When the C front-end (`bld/cc/c/cexpr.c`, `MakeFunctionCall`)
encounters a call to an undeclared identifier, it synthesises
a default prototype `int X(...)` per C89 §6.3.2.2.  The
return-type information flows into the call-expression's
`OP_NODE` as `T_INT`, and the back-end's `O_RETURN` handler
emits the wider register read accordingly.

A subsequent `extern char X(void);` declaration **doesn't
retroactively patch the earlier call's IR** — Watcom records
each call site's expected return type at parse time and the
back-end runs per-function.  The compiler does, however,
emit `E1062: Inconsistent return type for function 'X'`
when it later sees the actual definition with a different
type — that's how this rule is usually noticed.

### Verified on

- `sim_mouse` (declared `void` in hotkeys.c, called from
  `get_mouse` in lib32.c with `if (sim_mouse() == 0)`).
  Initial decomp had no forward declaration in lib32.c;
  diff was 1 byte at the test (`85 c0` vs PS's `84 c0`).
  Adding `extern char sim_mouse(void);` immediately above
  `get_mouse` collapsed the diff to zero.  Bumping the
  `hotkeys.c` stub from `void sim_mouse(void)` to
  `char sim_mouse(void) { return 0; }` is independently
  required to satisfy the compiler — but the lib32.c
  forward declaration is what fixes the codegen.
- Watcom 10.0a, `-bt=dos -mf -4r -s`.

### Detection hint

Diff signature: a single byte mismatch at a `test`
instruction following a `call` (`85 c0` -> `84 c0`),
optionally followed by similar mismatches at any byte
store of the call's result (`a3` -> `a2`, etc.).  Search
the same TU and AGENTS.md's globals header for an
`extern <type> <fn>(...)` matching the called name; if
absent, the implicit-int rule is in play.

This rule is operational rather than pure codegen — it
fires even when the callee is just a stub — and it's a
sibling of Rule 22 (stub signatures): both insist that
the **prototype as visible to the caller** must match
the real ABI before the first call site is parsed.

---

(Future rules append below.)

## Rule 38 — Whole-program tail-call fall-through reordering

### What PS.EXE does

PS.EXE compiles a wrapper like

```c
int act_battle_help(void) { return helping(0x33); }
```

(in action.c, source line ~1727) into a 10-byte sequence:

```
mov eax, 0x33
e9 NN NN NN NN     jmp helping
```

with `helping` placed at its *own* source-order position
(line ~1655), wherever in the .obj that puts it.  The
explicit `e9` near-jmp covers the long backward distance
to `helping`.

### What our Watcom 10.0a build does instead

Our `wcc386` (also Watcom 10.0a, in the dosemu2 container)
**reorders** function emission: it sees that
`act_battle_help` ends in a tail-call to `helping` and
moves `helping` to immediately follow act_battle_help's
body in the .obj, then drops the `jmp` — falling through
to `helping`'s entry instead.  Result:

```
act_battle_help_:  mov eax, 0x33     ;; 5 bytes total
helping_:          push ebx          ;; helping starts at +5
                   ...
```

This 5-byte saving from one wrapper pulls `helping` to a
position 9000+ bytes away from *other* wrappers
(`act_help_icons`, `act_detailed_query`, ...) that ALSO
tail-call helping but don't get the fall-through perk.
Those wrappers must now use a 5-byte `e9` near-jmp where
PS used a 2-byte `eb` short-jmp (their helping is close by
in source order, far away in our compiled order).

### Symptoms

* A 1-byte diff at a tail-jmp site, hint = Rule 16:
  PS emits `eb XX`, our build emits `e9 XX XX XX XX`.
* The function offset of the tail-jmp's target (`helping`,
  `set_palette`, `display_event`, etc.) is far from PS's
  position in `out.map`.
* The tail-call target appears immediately after a *5-byte*
  function in our build's wdis dump, with no intervening
  bytes (= fall-through).

Affected wrappers in action.c: `act_help_icons`,
`act_battle_help` (the fall-through donor),
`act_detailed_query`, `act_query_help`, `act_query_tips`
(latter two = stubs).

### Why we can't fix it source-side

We can't disable the optimisation through `-bt=dos -mf -4r -s`
flags (verified — neither `-ou` "unique addresses" nor any
other flag in the 10.0a set suppresses the reorder).

Manually moving `helping`'s definition in the .c file just
shifts which wrapper "wins" the fall-through donation — one
wrapper always gets it, and the others always pay the
encoding-size cost.  PS got lucky (or had different source
ordering) and avoided the merge entirely.

### Workaround

Mark these as **structural diffs**: byte-exact is not
achievable until we replicate the PS source ordering of
*all* tail-callers and the callee in one TU.  A search for
`act_help_icons`-style 1-byte diffs across the project
should isolate the cluster, and stripping its members from
the decomp-verify exact-target is acceptable as long as we
flag the reason in the source comment block.

### Open question

Is the reorder controlled by some `OPTIM` flag we don't
yet pass, or is it a side-effect of `-os`/`-ot` that PS
also had?  Worth a future sweep with the wcc386
disassembler against tiny test cases (`fall_thru.c`:
two functions, one tail-calls the other) to find the
flag (or absence of flag) that turns fall-through merging
on/off.

* **Discovered**: 2026-04-27 while decompiling
  `affected_by_cover1`/`affected_by_cover2` — those landed
  byte-exact, but the residual Rule 16 diffs in callers
  (`act_help_icons`, `clear_all_cm`) refused to clear,
  prompting investigation of the action.obj layout via
  `wdis -p`.


## Rule 39 — Byte-pointer cast forces separate-offset 2D address fold

### Context — when Rule 33 doesn't apply

For 2D-region scans where IV substitution is suppressed
(struct typed pointer + early-out + spilled mask param —
see Rule 33 "When this rule does NOT apply"), PS still
picks a *specific* address-fold register layout that
differs from the natural C form.

### What PS.EXE does

For `affected_by_cover1`/`affected_by_cover2` (map.c, 103 b
and 95 b — both confirmed byte-exact 2026-04-27):

```
0006E3D7  L3897  mov eax, edx       ; eax = xi
                shl eax, 2
                add eax, edx        ; eax = 5*xi
                shl eax, 2          ; eax = 20*xi
                lea ecx, [eax + ebp] ; ecx = p + xi*20
                mov ebx, esi
                mov eax, esi        ; eax = yi
                shl eax, 2
                sub eax, esi        ; eax = 3*yi
                shl eax, 3          ; eax = 24*yi
                add eax, esi        ; eax = 25*yi
                shl eax, 6          ; eax = 1600*yi
                xor ebx, esi        ; ebx = 0 (just zeroing)
                mov bl, [ecx + eax + 0xd]  ; ← THE FOLD
```

PS computes `xi*20` and `yi*1600` as **two separate scaled
chains** in two different registers (`ecx` for `p + xi*20`,
`eax` for `yi*1600`), then folds them at the load via
`[ecx + eax + 0xd]`.  Each iteration recomputes both
chains.

### What you must write in C

```c
char affected_by_cover1(struct city_cell *p, int range, char mask)
{
    int xi, yi;

    if (range == 1)
        return p->education & mask;       /* 0xD */
    for (yi = 0; yi < range; yi++) {
        for (xi = 0; xi < range; xi++) {
            if (((char *)(p + xi))[yi * 1600 + 0xd] & mask)
                return 1;
        }
    }
    return 0;
}
```

The crucial part is the address expression
`((char *)(p + xi))[yi * 1600 + 0xd]`:

* `p + xi` produces a typed pointer with stride 20 (Watcom
  emits `xi * 20` as the standard `*5*4` shift+add chain).
* The cast to `char *` lets the constant `1600` and `0xd`
  be byte-precise without re-deriving the cell index.
* `[... + 0xd]` keeps the field offset as an immediate in
  the `mov bl, [reg + reg + 0xd]` encoding, instead of
  folding into a precomputed combined offset.

### What the compiler emits if you write it the obvious way

The natural form `p[yi * 80 + xi].education` produces a
single fused linear index:

```
mov eax, ecx        ; eax = yi
shl eax, 2
add eax, ecx        ; eax = 5*yi
shl eax, 4          ; eax = 80*yi
lea ebx, [eax + edx]  ; ebx = 80*yi + xi
mov eax, ebx
shl eax, 2
add eax, ebx        ; eax = 5*(80*yi + xi)
mov al, [edi + eax*4 + 0xd]  ; ← single fold via *4 scale
```

Watcom collapses `(80*yi + xi)*20` into `((80*yi + xi)*5) * 4`
and emits a single `[reg + reg*4 + 0xd]` fold.  Same address
math, completely different instruction encoding — 30+ byte
positions differ.

### Rationale

When the source expresses the index as `(p + xi)` first
(typed pointer arithmetic), Watcom commits to the
`xi*20` chain in `eax` and stashes the partial address
(`p + xi*20`) in a separate register *before* computing
the row offset.  The byte-pointer cast and the literal
`1600` then preserve the second-chain register usage —
no opportunity for the unified `*4`-scaled fold.

### Examples

* `affected_by_cover1` — 103 b byte-exact, commit `3988655`.
* `affected_by_cover2` — 95 b byte-exact (sibling, also
  shares cover1's epilogue via Rule 15 cross-function
  tail-merge — both must be in the same TU and adjacent in
  source order).

### Detection hint

Diff signature: ~30 byte positions of "scaled-fold vs
two-chain" differences clustered around the inner-loop
load.  PS shows `lea ecx, [eax + ebp]; mov bl, [ecx + eax + 0xd]`
(two regs, no scale).  Recomp shows `add eax, ebx; mov al,
[reg + reg*4 + 0xd]` (one reg, *4 scale).  Try the byte-
pointer cast form before deeper restructuring.

### Watcom version + flags

Watcom 10.0a, `-bt=dos -mf -4r -s`.  Discovered 2026-04-27.

---

## Rule 40 — Sentinel return value forces signed-char return type

### What PS.EXE does

For `check_clock_ferret_move` / `check_anti_ferret_move`
(common.c) PS returns the byte value `0xFF` from one path
and the AND-result of cell field bits from others, all
through a single 1-byte `al` return:

```
0002C6E2  L1103  mov al, 0xff
0002C6E4         (epilogue: pop callee-saves; ret)
```

Callers in PS interpret the `0xFF` as `-1` (signed) for
the "out-of-bounds" sentinel — `if (result == -1)` paths
in `run_clock_ferret`/`run_anti_ferret`.

### What you must write in C

```c
signed char check_clock_ferret_move(int dir, int count)
{
    ...
    if (dir > 7) return -1;
    ...
}
```

`signed char` is the only return type that:

1. Compiles `return -1;` cleanly (no W106 truncation
   warning — `-1` is in range `[-128, 127]`).
2. Matches PS's 1-byte return convention (`mov al, ...; ret`).
3. Sign-extends correctly at caller-side `result == -1`
   comparisons (`movsx eax, al` -> `cmp eax, -1`).

### What the compiler emits if you write it the obvious way

* `char` (Watcom default = unsigned): triggers W106 on
  every `return -1;` and `return -2;` site (W106:
  "Constant out of range — truncated").  The body still
  compiles to identical bytes, but the noise drowns out
  real warnings, and `--strict-warnings` rejects the
  build (post commit `c0dcd6b`).
* `int`: silences W106 but switches the return convention
  from 1-byte `al` to 4-byte `eax`.  Callers expecting
  `signed char` sign-extension see a wider type and may
  emit a `movsx` they didn't have before.

### Distinction from Rule 8

Rule 8 covers default-unsigned **reads** of `char` fields
(use `signed char` only at fields PS reads via `movsx`,
never globally).  Rule 40 covers default-unsigned **return
types** for functions that use `-1`/`-2` as sentinel
values — flipping to `signed char` is the only correct
fix when the function is otherwise byte-exact.

### Detection hint

* W106 ("Constant out of range - truncated") at a `return
  -N` line in a `char`-returning function.
* PS disasm shows `mov al, 0xff` (or `0xfe`) at one of
  the return paths.
* Caller does `if (result == -1) ...` or similar
  signed-comparison.

When all three line up, change the return type to `signed
char` and update any local `char result;` declarations to
`signed char result;` in the same TU.

### Examples

* `check_clock_ferret_move` (common.c, 1008 b) —
  signature changed in commit `c0dcd6b`.
* `check_anti_ferret_move` (common.c, 1135 b) — same.

Both are still byte-diff (independent codegen issues), but
the signature change cleared 42 W106 warnings without
introducing regressions.

### Watcom version + flags

Watcom 10.0a, `-bt=dos -mf -4r -s`.  Discovered 2026-04-27.


## Rule 41 — Dead parameter as ABI-compat slot

### Trigger

A function declared with N parameters where the compiled
body provably reads only N-1 of them, **yet every caller
faithfully pushes/loads the dead slot**.  PS.EXE's
``ret X`` cleanup sums the full N-slot stack-arg count,
not the live-slot count.

The function looks like this in disasm:

```
flag_range3: ; 8 args (4 reg + 4 stack), but stack arg #1 (esp+0x1C) is dead
push esi, edi, ebp
sub esp, 0xc
mov ebp, eax     ; arg1
mov esi, edx     ; arg2
mov edi, ebx     ; arg3
mov eax, ecx     ; arg4
mov dh, [esp+0x20]   ; arg6 (skips arg5 at +0x1C!)
mov ch, [esp+0x24]   ; arg7
mov cl, [esp+0x28]   ; arg8
...
ret 0x10         ; pops 4 stack dwords (16 bytes)
```

The body never reads `[esp+0x1C]`, yet the function
``ret 0x10`` pops 4 stack dwords (= 4 stack slots).
Diagnose by counting:

  * The number of distinct ``[esp + N]`` reads in the body
    that target arg-region offsets (above the saved
    return-addr slot).
  * The number of dwords popped by the closing ``ret X``
    (X / 4).
  * If the second is larger, some slots are dead.

### Caller pattern (the give-away)

Every caller pushes the **same constant** for the dead
slot, suggesting an old hard-coded value.  In
`flag_range3`'s case, every caller pushes `0xC` for the
unused 5th arg — the same value the body hard-codes as
the city_cell field offset (the entertainment byte +0xC).
The most likely history: an earlier revision took
`field_offset` as a runtime parameter, a later refactor
inlined the constant into the body, **but the parameter
slot was kept** so the dispatch ABI stayed compatible
across already-compiled callers (or because removing it
from a function-pointer table would have required
synchronised changes to multiple .obj files).

### Right C

Declare the dead arg explicitly and mark it consumed:

```c
void flag_range3(int extra, int x, int y, int range,
                 int unused_field_off,           /* ALWAYS 0xC */
                 char threshold, char query_mask, char clear_mask)
{
    (void)unused_field_off;
    /* body uses only 7 of 8 args; +0xC is hard-coded */
    ...
}
```

Not:

```c
/* WRONG: 7-arg signature */
void flag_range3(int extra, int x, int y, int range,
                 char threshold, char query_mask, char clear_mask)
```

The 7-arg version produces ``ret 0xC`` (3 dwords) — every
caller diff'd against PS.EXE will be 4 bytes off because
it pushes 4 dwords expecting the 8-arg ABI.

### Why this rule matters operationally

Without naming the dead slot, you'll waste hours
searching for a use-site that doesn't exist.  When you've
walked the entire function body and every register state
is accounted for *except* one stack slot, **stop looking
— it's dead**.  Verify by counting the ``ret X`` pop
size against the number of body-reachable arg reads.

### Mechanism

The C front-end emits the function's stack-cleanup
``ret X`` from the prototype's parameter list, not from
the body's actual reads (`bld/cc/c/cgen.c` — function
epilogue pass).  An unread parameter is allocated a stack
slot during prologue lowering but never marked as a
required IV in the dataflow graph; the back-end skips
emitting any read instruction for it but the prologue's
arg-region size already covers it.

### Detection hint

  * ``ret X`` where X / 4 > number of distinct
    ``[esp + N]`` arg reads in the body.
  * All callers pushing a uniform constant for a slot
    you can't tie to any body instruction.
  * Common rationale clues:
       * That constant matches a hard-coded literal
         elsewhere in the body (e.g. `+0xC` field
         offset that was once a parameter).
       * A sister function with one fewer arg exists
         and shares the body structure.

### Examples

  * `flag_range3` (map.c, 267 b) — 8 args declared, 7
    used; arg5 (`unused_field_off`) is always 0xC and
    the body hard-codes the entertainment offset (+0xC)
    that was likely once parametric.  Commit `af83fa1`.

### See also

  * Rule 22 — Stub signatures must match real arg widths
    (the inverse of this rule: when *callees* are stubs,
    you must declare their args correctly so the
    *call-site* bytes match).  Rule 41 is the
    same problem from the *callee's* side — a real,
    decompiled function with a dead arg slot.

### Watcom version + flags

Watcom 10.0a, `-bt=dos -mf -4r -s`.  Discovered 2026-04-27.

## Rule 42 — Cross-function tail-merge donor selection (`ComTail` in optcom.c)

### What PS.EXE does

When two or more functions in the same TU share a common
backward sequence ending in ``ret``, Watcom 10.0a's
**`ComTail`** optimisation in `bld/cg/c/optcom.c` replaces the
duplicate sequences with a near-jmp to a single shared copy.
The mechanism is:

  1. Every emitted ``OC_RET`` instruction is added to a
     TU-wide global list ``RetList`` (LIFO — newest at head).
     See `bld/cg/c/optutil.c::AddRef`.
  2. `OptPush` (in `optins.c`) walks the instruction stream
     **backward from `LastIns`**.  When it hits an `OC_RET`,
     it calls ``ComTail( RetList, ins )``.
  3. ``ComTail`` walks the entire `RetList`.  For each
     candidate ``try`` (``try != ins``), it calls
     ``FindCommon(common, try, ins)`` which walks
     ``PrevIns(p1)``, ``PrevIns(p2)`` simultaneously,
     counting matching instructions per ``CommonInstr``.
  4. The candidate with the highest ``common.save`` wins.
     ``common.save > max.save`` is strictly greater, so
     **first-encountered** at any given size wins.
  5. Gating: ``OptForSize >= 25`` (default 50, so always
     fires) and ``max.save > OptInsSize(OC_JMP, OC_DEST_NEAR)
     == 5``.  At least 6 bytes of common tail are required.
  6. If a winner exists, ``TransformJumps`` rearranges
     predecessors, ``AddNewLabel`` inserts a new internal
     label *just before* ``max.start_com`` (the candidate's
     first matching instruction), ``AddNewJump`` emits a
     near-jmp at ``max.start_del`` (the *current* RET's
     first matching instruction), and **the duplicate
     instructions in the current RET's path are deleted**
     (including the current RET itself, via
     ``DelInstr(next); if(next == ins) break;``).
  7. ``DelInstr`` removes the deleted RET from
     ``RetList`` (`bld/cg/c/optutil.c::DelInstr_Helper`).

### Important asymmetry

The function being processed is **always the loser** — its
RET is deleted and replaced with a jmp.  The candidate
**keeps its tail intact**.  Combined with the
walk-backward order in `OptPush`, this means:

  * *Later in source* = emitted later = at HEAD of `RetList`
    = processed *earlier* by `OptPush`.
  * The *earliest in source* function with a matching tail
    will be processed *last*, by which time most candidates
    have been deleted; it always keeps its inline tail.

So in a TU with three matching-tail functions A < B < C
(< means earlier in source / .obj order):

  * C processes first, finds A or B in `RetList`, merges into
    whichever appears first in `RetList` iteration (LIFO ⇒
    B-most-recent-emitted ⇒ B wins by tie-break).
  * B processes next; its RET still in `RetList`.  Finds A
    (only remaining candidate with matching tail).  Merges
    into A.
  * A processes last.  No candidate left with matching tail.
    A keeps inline tail.

PS.EXE's `clear_all_rm` (line 3261) and `clear_all_cm`
(line 4096) both `jmp 0x678b4` (= label inside
`build_wall_from_elastic` at line 890); `build_wall_from_
elastic` keeps the inline ``add esp, 0xc; pop ebp/edi/esi/
edx/ecx/ebx; ret`` tail.

### Stub bodies break the donor chain

Our stub bodies are ``__stub_log = ADDR; (void)args;`` →
compile to ``mov [stub_log], ADDR; ret <pop_count>`` — the
``ret`` is preceded by **a single 10-byte mov**, so the
backward walk in `FindCommon` matches only ``ret`` itself
(if RetPop equals) or nothing (if RetPop differs).
``save`` is at most 1 byte; the ``> 5`` gate fails; no
merge fires.

This is *the* mechanism behind a large class of currently-
unactionable 1-byte diffs in the project: a function with
inline ``5d 5f 5e 5a 59 5b c3`` tail in our build, where
PS shows ``e9 NN NN NN NN`` jumping into a real donor
function that's still a stub on our side.

### Right C / how to fix the diff

Decompile **the donor function** with a body whose tail
naturally produces the same 6-pop+ret epilogue (or
whatever shared tail the family uses).  Empirical fix
for `clear_all_rm` (commit `<unmerged>` experiment):

  * `build_wall_from_elastic` was a `(void)` stub →
    inline `mov + ret 0`, save=1, no merge.
  * Replaced its body with a synthetic copy of
    `clear_all_rm`'s loop (same callee-save set, same
    ``ret 0`` epilogue).  Body content irrelevant — only
    the prologue/epilogue shape matters.
  * `clear_all_rm` immediately flipped from
    1-byte diff to byte-exact ✓.
  * `clear_all_cm` continued as byte-exact ✓ (it had
    been opportunistically merging into `clear_all_rm`'s
    inline tail; now both jmp to `build_wall_from_elastic`).

### Detection hint

Run `c2 disasm <fn>`.  If the last instruction is an
``e9 NN NN NN NN`` jmp whose target falls **inside another
function** of the same source file, you have a Rule-42
candidate.  Look up the named donor in `symbols.json`:

  * Is the donor a stub in our build?  Decompile it (or
    write a synthetic body with matching prologue/
    epilogue) — your function will become byte-exact.
  * Is the donor decompiled but with a *different*
    epilogue?  Then PS's tail-merge directed your function
    elsewhere; trace the donor's pop sequence and adjust
    the candidate's source to match.

### Ordering caveat (cross-TU only)

The optimisation is **strictly intra-TU**.  `RetList` is
reset per compilation unit (`OptPush` runs once per
function, but the `RetList` accumulates across all
functions in the same `.c` file).  Cross-TU tail-merge
does not exist — it's the linker's job, and Watcom's
linker doesn't do code-level dedup.

### Verified by

Empirical experiment 2026-04-27:

  * Baseline: `clear_all_rm` (153 b) had a 1-byte diff at
    +0x94 — PS used ``e9 fd a7 ff ff`` jmp to
    `build_wall_from_elastic+0x261`; our build emitted
    ``5d 5f 5e 5a 59 5b c3`` inline.
  * Replaced `build_wall_from_elastic`'s stub body with a
    synthetic 6-callee-save body.
  * Result: `clear_all_rm` flipped to byte-exact;
    `clear_all_cm` stayed byte-exact (it had been
    secondarily merging into `clear_all_rm`'s inline tail);
    `build_wall_from_elastic` itself still diff (synthetic
    body ≠ PS body, expected).
  * Reverted experiment after confirmation; the proper
    fix is to decompile `build_wall_from_elastic` with its
    real PS body.

### Source references

  * `bld/cg/c/optcom.c::ComTail` — the algorithm.
  * `bld/cg/c/optcom.c::FindCommon` — backward walk,
    label-skip on candidate side only.
  * `bld/cg/c/optcom.c::CommonInstr` — single-instruction
    equality including `_RetPop` for OC_RET.
  * `bld/cg/c/optins.c::OptPush` — driver, calls
    `ComTail(RetList, ins)` for every OC_RET.
  * `bld/cg/c/optutil.c::AddRef`, `DelInstr_Helper` —
    `RetList` LIFO maintenance.
  * Strategy: `docs/open-corpus-levers-2026-06-14.md` —
    *donor-first / tail-merge cascade* remains one of the current leverage
    filters.

### Tooling

The verifier (`uv run c2 decomp-verify ... -v`) prints a
**Tail-merge** hint line for every diffing function whose last
instruction is a near `jmp` into a different known function.  The
hint shows the donor symbol, the merge offset inside it, the byte
count of the shared tail, and a disasm preview, e.g.::

    Tail-merge: Tail-merge donor: build_wall_from_elastic+0x261
        (7 b): pop ebp; pop edi; pop esi; pop edx; pop ecx; pop ebx; ret

In `--json` mode the same data appears under
`functions[].tail_merge` so external tooling (progress dashboards,
stub-priority rankers) can observe donor relationships directly.

The scanner is implemented in `c2/commands/tail_merge.py`
(`scan_tail_merge_donor`) and tested by
`tests/test_tail_merge.py` (10 tests: 8 synthetic, 2 PS.EXE
smoke).  See also Rule 15's `Practical consequence` paragraph
which originally identified the same problem from the *user* side.

### Watcom version + flags

Watcom 10.0a, `-bt=dos -mf -4r -s`.  Discovered 2026-04-27
via OW v1 source reading + controlled experiment.

----

## Rule 43 — `#pragma on(check_stack)` selectively enables `__CHK` prologue

Watcom 10.0a emits a `push <frame_size>; call __CHK` prologue when
the function's `SYM_CHECK_STACK` flag is set.  The flag is recorded
in `cdecl1.c:145` at function-definition time:

    if( Toggles & TOGGLE_CHECK_STACK )
        sym->flags |= SYM_CHECK_STACK;

`TOGGLE_CHECK_STACK` is **on by default** (`cmodel.c:321`).  It is
toggled by:

  * **`-s`** flag (`Set_S` in `coptions.c:1025`) → clears it.
  * **`-ox`** master flag (`Set_OX` in `coptions.c:1234`) → clears it.
  * **`#pragma on(check_stack)` / `#pragma off(check_stack)`** in
    source (`togdef.h:33`, runtime toggle).

At codegen, `DoStackCheck` in `i86proc.c:451` checks the flag via
`FEStackChk` and emits the `__CHK` call when set:

    if( NeedStackCheck() ) {
        GenUnkPush( &CurrProc->targ.stack_check );
        RTCall( RT_CHK, ATTR_POP );
    }

The push immediate is the function's full stack-frame depth at the
deepest point — see the patch site at `i86proc.c:1133`:

    AbsPatch( CurrProc->targ.stack_check,
              CurrProc->locals.size +
              CurrProc->parms.base  +
              WORD_SIZE*CurrProc->lex_level +
              CurrProc->targ.push_local_size +
              MaxStack );

There is **no size threshold** — even a zero-frame function gets
`push 4; call __CHK` if the flag is set.  The only suppressors are
`GENERATE_THUNK_PROLOG` (Windows API thunks — irrelevant for DOS) and
`GENERATE_GROW_STACK` (`-sg`, which substitutes `__GRO`).

### Caesar2 incidence

107 / 2261 (~5%) of PS functions emit a `push <imm>; call __CHK`
prologue.  The remaining 95% have a plain register-save prologue.
This means PS source was predominantly compiled with `-s` (or
`#pragma off(check_stack)` at file scope), with **specific functions
wrapped** in `#pragma on(check_stack)`.

The 5% that DO emit `__CHK` cluster around:

  * The lib32.c drawing primitives (`draw_a_2point`, `draw_a_line`,
    `draw_a_rect`, `xor_a_diamond_top`, `xor_a_diamond_lhs_top`,
    `xor_a_diamond_rhs_top`, `put_a_font_string`, …).
  * Other large utility/leaf routines.

### What you write in C

Wrap the function with the pragma toggle (the `off` after the function
restores the file-default so the next function isn't affected):

    #pragma on(check_stack)
    void affected_function(int x, int y, int width, int height, int color)
    {
        ...
    }
    #pragma off(check_stack)

With our default `-s` flag, this is the only way to make the
recompiled body match a PS function that has `__CHK` in its prologue.

### Sub-pattern 43a — Dead `mov reg, parm_reg` at function entry

A common PS prologue idiom in __CHK functions::

    push 0x18; call __CHK
    push esi; push edi; push ebp; push eax; push edx
    mov esi, ebx          ; ← DEAD: ESI is overwritten 11 insns later
    mov edx, ecx
    mov ebp, [esp + 0x18]
    xor ecx, ecx
    mov eax, edx; sar edx, 0x1f; sub eax, edx; sar eax, 1
    lea esi, [ebx + 2]    ; ← OVERWRITES the earlier mov esi, ebx

The `mov esi, ebx` is the parameter-init copy emitted by
`DoParmDecl` in `bldcall.c:316`:

    ins = MakeConvert( parm_name, temp, TypeClass( tipe ), class );
    LinkParmIns( parm_def, ins );
    AddIns( ins );          ;← unconditional emission of the param copy

#### Trigger — *parameter mutation*

**The trigger is the C source mutating its own parameter.** When
the source contains `width += 2;` (or `width = ...;`), Watcom
allocates `width`'s temp to a *callee-save* register (esi) so the
written-to value survives across calls within the function.
`DoParmDecl` then emits the parm-init copy `mov esi, ebx`, and the
later `width += 2` folds to `lea esi, [ebx + 2]` reading directly
from the still-live parm reg — leaving the original copy as dead
code that the IR-level DCE pass cannot eliminate (the temp is
conceptually still *read* by the lea, even after register-folding).

**Reproduction** (oracle harness, `param-mutation-yo-last` trial in
`docs/codegen-experiments/rule43a.py`)::

    void xor_a_diamond_lhs_top(
        int x, int y, int width, int height, int color)
    {
        int x_offset = 0;
        int y_offset;
        width += 2;                       /* ← THE TRIGGER */
        y_offset = height / 2 - 1;

        for ( ; x_offset < width / 2;
              x_offset += 2, y_offset--) {
            xor_internal_2point(
                x + x_offset, y + y_offset, color);
        }
    }

Produces 88 bytes; **byte-identical to PS** (modulo rel32 fixups
to `__CHK` and `xor_internal_2point`).  Verified 2026-04-27 via
``uv run c2 cgex run rule43a --trial param-mutation-yo-last``.

#### Why every other oracle attempt failed

The earlier hypothesis ("regalloc decides whether to allocate to
esi vs ebx") was **half right** — regalloc *does* make that
choice, but the *cause* is the C source.  Without param mutation,
Watcom keeps `width` in its arrival reg `ebx` (no copy emitted).
With param mutation, the writeable home must be a stable temp →
callee-save reg → `mov esi, ebx` parm-init.

Source patterns we tried that did **not** trigger it:

  * `int loop_max = width + 2;` — fresh local, no mutation
  * `int local_width = width;` — read-only alias
  * `register int t = width + 2;` — register hint on temp, not param
  * `int *pw = &width;` — address-taken (forces stack home, not callee-save)
  * `for (...; x < (width + 2) / 2; ...)` — width inline in test, no mutation
  * `dummy_sink = width;` after loop — single read, no mutation

The pattern affects at least these PS functions (callee-save reg
in parens — that's the param-init target)::

  * `xor_a_diamond_lhs_top` (esi = width, dead) — 88 b
  * `xor_a_diamond_top`     (esi = width, dead) — 142 b
  * `xor_a_diamond_rhs_top` (edi = width, dead) — 75 b

In all three, ``<callee_save_reg> = ebx`` is followed by
``lea <callee_save_reg>, [ebx + 2]`` 5–11 instructions later — the
exact `width += 2` body Watcom emits when the source mutates the
param.

#### What you must write in C

Match PS by **mutating the parameter directly**, not introducing a
fresh local:

    /* RIGHT — produces PS shape */
    width += 2;
    for ( ; x < width / 2; ...) ...

    /* WRONG — eliminates the mov esi, ebx */
    int loop_max = width + 2;
    for ( ; x < loop_max / 2; ...) ...

The two are semantically identical from the function's outside
view (parameters are pass-by-value), but they produce different
codegen because Watcom's regalloc treats writeable params and
fresh locals differently.

#### Statement ordering matters

`width += 2` must appear *before* the `y_offset` initialisation
for the leas to come out in PS order (`lea esi, [ebx+2]` before
`lea edi, [eax-1]`).  Source-statement order biases regalloc's
emit order — Rule 35b territory.

#### Detection hint

Look for `mov <callee-save-reg>, <parm-reg>` immediately after the
push-callee-saves prologue (and before any computation), where
that callee-save reg is *also* later reassigned via lea/load.
Such a copy is dead and means the original C source mutated that
param.

#### Source references (OW v1)

  * `bld/cg/c/bldcall.c:316::DoParmDecl` — emits the parm-init
    copy unconditionally per parm.
  * `bld/cg/c/regalloc.c::AssignTemps` — allocates a callee-save
    register to a writeable temp that survives across calls.
  * `bld/cg/c/optimize.c:367::IsDeadIns` — IR-level DCE that
    keeps the parm-init alive because the temp's read got
    register-folded but the IR still records the temp as read.

#### Tooling

`uv run c2 cgex run rule43a` runs the full reproduction matrix
(24 trials).  Add a new trial via the `Experiment.add()` API in
`docs/codegen-experiments/rule43a.py`.

### Tooling

`uv run c2 disasm <name>` shows the `push <imm>; call __CHK` prologue
when present.  A future `c2 chk-functions` lister would scan PS and
report all 107 functions for batch pragma application — currently
do it ad-hoc with the python snippet documented in the Caesar2 incidence
section.

### Source references

  * `bld/cc/c/cdecl1.c:145` — `SYM_CHECK_STACK` flag set on function
    decl.
  * `bld/cc/c/cinfo.c:975`  — `FEStackChk` reads the flag.
  * `bld/cc/c/coptions.c:1025` — `Set_S` clears `TOGGLE_CHECK_STACK`.
  * `bld/cc/c/cmodel.c:321` — default `Toggles = TOGGLE_CHECK_STACK`.
  * `bld/cg/intel/c/i86proc.c:444` — `NeedStackCheck` /
    `DoStackCheck` emission.
  * `bld/cg/intel/c/i86proc.c:1133` — `__CHK` immediate patch site.
  * **Sub-pattern 43a**: `bld/cg/c/bldcall.c:316` (`DoParmDecl`),
    `bld/cg/c/optimize.c:367` (`IsDeadIns`).

### Watcom version + flags

Watcom 10.0a, `-bt=dos -mf -4r -s`.  Discovered 2026-04-27
via OW v1 source archeology while pursuing tail-merge donor
`xor_a_diamond_lhs_top`.

---

## Rule 44 — Split a temp for `(byte & MASK) == 0` to avoid spurious zero-extend

### Trigger

When testing a masked byte against zero, Watcom 10.0a emits an
extra `and eax, 0xFF` zero-extend if the AND-and-test is written
inline as a single expression:

```c
if (((unsigned char)arr[i] & 0xe7) == 0) return 0;
```

emits

```asm
    mov  al, byte ptr [...]
    and  al, 0xe7
    and  eax, 0xff           ; ← spurious zero-extend
    je   return0
```

The extra `25 ff 00 00 00` (5 bytes) shifts everything below by
5 bytes and cascades through downstream branch encodings.

### Right C — split the masked byte into a `char` temp

```c
unsigned char x = ((unsigned char)arr[i]) & 0xe7;
if (x == 0) return 0;
```

emits the clean PS shape:

```asm
    mov  al, byte ptr [...]
    and  al, 0xe7
    je   return0
```

The `and al, MASK` instruction sets ZF directly from the 8-bit
result; `je` reads ZF correctly without needing the 32-bit zero-
extend.  Splitting into a named `unsigned char` temp tells
Watcom that the result type is byte-only, suppressing the
widening cast.

### Mechanism

Watcom's expression evaluator promotes the result of `byte &
MASK` to `int` for the `== 0` comparison (C standard integer
promotion).  When the result is held in an `int`-typed
intermediate, the back-end inserts `and eax, 0xff` to ensure
upper bits are clean before the int compare.  When the result
is assigned to an `unsigned char` temp first, the back-end
treats the comparison as a byte-only test and elides the zero-
extend.

This is the **opposite** of Rule 1 (which says inline globals
twice rather than caching).  The distinction:

* **Rule 1**: globals' regalloc benefits from inline reuse —
  cache **bad**, inline **good**.
* **Rule 44**: byte-mask zero tests benefit from byte-typed
  cache — cache **good**, inline **bad**.

The rule of thumb: cache when the type system needs the hint
(byte-only compares); inline when register allocation needs
the value-flow visibility (long-lived globals).

### What Watcom emits if you write the obvious form

The natural form

```c
if ((arr[i] & 0xe7) == 0) ...
```

emits 4 extra bytes per masked-byte test.  In a function with
multiple such tests, this cascades through the entire layout.

### Verified on

  * `are_overlays_on` (pm_map1.c, 0x39377) — splitting
    `((cm[ptr+1] & 0xe7) == 0)` into `x = cm[ptr+1] & 0xe7;
    if (x == 0)` collapsed the 5-byte spurious zero-extend
    (and the 60+ cascading byte diffs) to a 2-byte regalloc
    cosmetic remainder.  Verified via oracle: 22 b inline → 17 b
    split (5-byte savings exactly matches PS shape).
  * Watcom version: 10.0a, `-bt=dos -mf -4r -s`.

### Detection hint

Look for `and reg8, MASK; and reg32, 0xff` pairs in PS
disassembly (PS doesn't have these, but **your RC will**).  If
your RC emits `and al, MASK; and eax, 0xff` and PS emits just
`and al, MASK; je`, this rule applies.

### Source refs (OW v1)

  * `bld/cc/c/cgen.c::PromoteByte` — integer-promotion of
    byte expressions to int before relational ops.
  * `bld/cg/c/foldins.c::OptimizeFoldedSeq` — fails to fold
    away the redundant zero-extend when the intermediate is
    int-typed.


────────────────────────────────────────────────────────────────────────────

## Rule 45 — Aggregate-init `SYM_TEMP` statics live in `_TEXT` under `-mf`

### Pattern

Bytes from a `char buf[N] = "literal";`-style local aggregate
initializer appear in PS's **code segment**, not the data
segment, **even though `-zc` was not used**.  They cluster at
the start of each .obj's `_TEXT` contribution and look like
ASCII string fragments interleaved between function bodies::

    ; smacker.c.obj end:
    +13a06   c3                   ret      ; show_smksum_screen
    ; smackw32.obj _TEXT start:
    +13a07   20 20 00 00          db "  ",0,0    ; SYM_TEMP for char[?] = "  "
    +13a0b   20 20 00 00          db "  ",0,0    ; another SYM_TEMP
    +13a0f   56 57 55 …           push esi/edi/ebp ; _DLL_read body

The bytes are NOT linker padding (OW v1 `PadLoad` writes only
zeros), and there are no fixups pointing at them.

### Source mechanism (OW v1)

`bld/cc/c/cinfo.c::SetSegment` for `_CPU == 386`::

    if( !CompFlags.rent ){
        if( ((sym->attrib & FLAG_FAR) || (TargetSwitches & FLAT_MODEL)) ) {
           if( CONSTANT(sym->attrib) && CompFlags.zc_switch_used ){
                sym->u.var.segment = SEG_CODE;
                return;
           }
           if( (sym->stg_class == SC_STATIC) && (sym->flags & SYM_TEMP) ) {
                sym->u.var.segment = SEG_CODE;     /* ← THIS BRANCH */
                return;
           }
        }
    }

Under flat model (`-mf`), any `SC_STATIC` symbol with the
`SYM_TEMP` flag is routed to `SEG_CODE` — independent of `-zc`.
`SYM_TEMP` is set by `MakeNewSym` (`csym.c:456`) on every
compiler-generated temporary static.  These are created at::

  * `bld/cc/c/cdinit.c:944, 1070, 1083` — backing storage for
    aggregate string-literal initializers (`char x[N] = "..."`)
  * `bld/cc/c/cexpr2.c:2157, 2204` — compound-literal temps
  * `bld/cc/c/cstmt2.c:392` — function return slots

### Per-.obj layout

Within each `.obj`, `_TEXT` is laid out as::

    [ all SYM_TEMP statics, source order ]
    [ all function bodies, source order  ]

Combined image: `[obj1.statics][obj1.code][obj2.statics][obj2.code]...`

So a function that sits at the **end** of one .obj's `_TEXT`
will have the next .obj's static-initializer bytes immediately
after it in the linked image.  These bytes belong to a
*different* compilation unit and **cannot be reproduced** from
the original source's .c file alone — you'd need to rebuild the
adjacent .obj from its source too.

### Empirical verification

Single-TU test (`compile_snippet` w/ `-bt=dos -mf -4r -s`)::

    void f1(void) { char a[6] = "AA"; }
    void f2(void) { char b[6] = "BB"; }

Code section: `41 41 00 00 00 00 42 42 00 00 00 00 c3 c3`

Both temps cluster at the start; both function bodies follow.

Multi-TU test (3 .objs, each with a temp)::

    obj1: char buf1[6] = "AA";  void f1(void) { ... }
    obj2: char buf2[6] = "BB";  void f2(void) { ... }
    obj3: void _entry_(void) { }

Code section: `41 41 00 00 00 00 c3 42 42 00 00 00 00 c3 c3 c3 c3`

Each .obj's `[statics][code]` contributes a contiguous chunk;
.objs are concatenated in link order.

### Implications for byte-exact decomp

* **Trailing-bytes diffs** at .obj boundaries (where a
  decompiled function ends and the next bytes look like
  `20 ...` ASCII fragments) belong to the *next* TU's
  SYM_TEMPs.
* **Detection**: bytes are printable ASCII or 0-padded
  4/8-byte aligned blobs sitting between two named functions
  *from different source files*, with no fixups pointing at
  them.
* **Fix — emulate the layout in the adjacent .c file**.  Add
  matching `char[N] = "...";` aggregate-init locals to the
  first .c that contributes _TEXT after the boundary.  E.g.
  to reproduce `20 20 00 00 20 20 00 00`:

      void __pad1(void) { char x[4] = "  "; (void)x; }
      void __pad2(void) { char y[4] = "  "; (void)y; }

  Watcom emits both SYM_TEMPs at offset 0 of the .obj's
  _TEXT, then merges the two empty bodies into a single 1-b
  `c3` (9 bytes total).  See `decomp/src/smackinp.c` for the
  canonical example — it closed the
  `show_smksum_screen` diff in 2026-05.
* **Caveat**: the adjacent .c file must currently contribute
  no code (or at least its first emitted function must come
  *after* the pad).  Alphabetical link order determines which
  .obj follows; insert the pad in that .c.

### Source refs (OW v1)

  * `bld/cc/c/cinfo.c:240–260` — `SetSegment()`, the routing
    rule that puts SYM_TEMP statics in `SEG_CODE` under flat
    model.
  * `bld/cc/c/csym.c:456` — `MakeNewSym()` setting the
    `SYM_TEMP` flag on compiler-generated statics.
  * `bld/cc/c/cdinit.c:944, 1070, 1083` — the call sites that
    create temps for aggregate string-literal initializers.
  * `bld/cc/h/ctypes.h:109` — `SYM_TEMP = 0x20` definition.


────────────────────────────────────────────────────────────────────────────

## Rule 46 — `arr + i + k` vs `&arr[i + k]` differ in SIB-scale reuse

### Pattern

When two array element accesses share an index expression `i`
that the compiler has already kept in a register (e.g.
`arr[i] = X` followed by `&arr[i + 1]` or similar), the
**syntactic form** of the second access decides whether the
SIB *4 scaling factor is reused.

  * **Pointer-arithmetic form** ``arr + i + k`` — preserves
    the unscaled index in the register, lets the second
    access use ``[reg*4 + base+disp]`` SIB *4 with a tiny
    extra ``+disp`` constant.
  * **Address-of-element form** ``&arr[i + k]`` — the compiler
    treats `i + k` as a fresh addressing expression, often
    ends up *re-deriving* the byte offset from scratch via a
    chain of `mov`/`shl`/`add` instructions.

Same C semantics, very different bytes::

    /* PS / "good" form: */
    ss_entries[slot * 5] = 1000;
    strcpy((char *)(ss_entries + slot * 5 + 1), "unused.wav");

    ; PS bytes (free_up_sslot, 42 b @ 0x129B1):
    mov [eax*4 + 0xd2a8], 0x3e8        ; first store, eax = slot*5
    lea edi, [eax*4 + 0xd2ac]          ; same eax reused, +4 disp

    /* "Bad" form — index re-derivation: */
    ss_entries[slot * 5] = 1000;
    strcpy((char *)&ss_entries[slot * 5 + 1], "unused.wav");

    ; recomp bytes:
    mov [eax*4 + 0xd2a8], 0x3e8        ; first store
    mov esi, edx                        ; ← re-fetch slot
    shl esi, 2; add esi, edx; shl esi, 2  ; ← recompute slot*5*4
    lea edi, [esi + 0xd2ac]              ; ← uses byte offset

The "bad" form costs **+9 bytes** per offending pair.

### Discovery

Found via byte-diffing `free_up_sslot` (42 b @ 0x129B1).
The original C used `strcpy(&ss_entries[slot*5+1], ...)`, with
the address-of-element form on the destination.  Even with
`#pragma intrinsic(strcpy)` and `-oi` to inline the copy as
`movsd; movsd; movsw; movsb`, the address calculation diverged
30 bytes from PS.

Switching to `strcpy((char *)(ss_entries + slot * 5 + 1), ...)`
brought the function to **byte-identical**, with no other
changes.  The intrinsic expansion `movsd; movsd; movsw; movsb`
also activated *without* `-oi` once the addressing was right —
suggesting the strcpy intrinsic fires whenever the destination
expression resolves to a pointer-arithmetic form the compiler
can fold into the `rep movsX` parm slot.

### Why?

OW v1 lowers the two forms to different IR:

  * ``arr + i + k`` is a **pointer addition** (`OP_ADD` on
    pointer operands) which the codegen leaves as a SIB-scale
    candidate via `bld/cg/c/optindex.c`.
  * ``&arr[i + k]`` is an **address-of** (`OP_ADDR`) on an
    indexed lvalue, which the codegen lowers via the
    array-indexing path — usually fine, but here it loses
    track of the existing SIB-scaled register from the
    previous access.

Effectively, the register allocator's value-numbering/CSE
hashes the two forms differently and fails to merge them.

### Detection hint

Look for sequences in the recomp where the same scalar
(`slot`, `i`, etc.) is multiplied by a constant **twice**, the
second time spilled to a different register:

    mov edx, eax           ; save slot
    shl eax, 2; add eax, edx
    ...
    mov esi, edx           ; ← re-derived slot copy
    shl esi, 2; add esi, edx
    shl esi, 2

If PS at the same offset has only one such chain followed by
two `[reg*4 + …]` accesses, you've hit Rule 46.

### Fix

Replace ``&arr[i + k]`` with ``arr + i + k`` (cast to the
desired pointer type if necessary).  The transform is
semantically identical but bytewise large.

### Source refs (OW v1)

  * `bld/cc/c/cexpr.c::IndirectOp` — lowers `arr[i+k]` to
    indirection of an addition; the result is an `OP_ADDR`
    when address-of is taken.
  * `bld/cg/c/optindex.c::SearchIndex` — looks for SIB-scale
    candidates among already-allocated index registers; only
    triggers on `OP_ADD` operands.

### Empirical reproduction

`docs/codegen-experiments/strcpy-intrinsic.py` trial
``ptr-add-1`` reaches 0-byte diff vs PS for `free_up_sslot`
under `-bt=dos -mf -4r -s -oi`.  All other variants (struct
view, char-cast pointer, intermediate index local) leave 22+
byte residuals.  Verified again *without* `-oi` in the full
pcsound.c TU build: still byte-exact, because the strcpy
intrinsic activates as a side effect of the ptr-arithmetic
form regardless of the global `-oi` switch in this context.


## Rule 47 — `int slot = 0;` upfront forces edx/spilled-register, vs reusing arg

For if/else dispatchers that map an input to a small set of
slot constants and then index a global array:

```c
void f(int event) {
    int slot = 0;                       /* ← matters */
    if      (event <= 3)    slot = 6;
    else if (event <= 9)    slot = 0xb;
    /* … */
    ambient_list[slot * 70] = 1;
    *(short *)&ambient_list[slot * 70 + 4] += 0x19;
}
```

Watcom emits:

```asm
push  edx               ; spill of incoming caller's edx
xor   edx, edx          ; slot = 0
cmp   eax, 3
jg    .check9
mov   edx, 6
jmp   .end
.check9:
cmp   eax, 9
jle   .set_b
…
.end:
imul  eax, edx, 0x46    ; slot * 70 → eax for indexing
mov   byte ptr [eax + ambient_list], 1
add   word ptr [eax + ambient_list+4], 0x19
pop   edx
ret
```

If you instead omit the `= 0` initialiser and add an explicit
`else slot = 0;` at the bottom:

```c
int slot;
if      (event <= 3)    slot = 6;
…
else                    slot = 0;
```

Watcom collapses the local into eax (overwriting the arg in
place), no edx spill, no callee-save, and the `imul` becomes
`imul eax, eax, 0x46`.  The byte sequence diverges at every
`mov ?, N` constant store *and* at the imul source register —
60+ b residual on a 67 b function.

### Mirror case — overwrite-arg-in-place (no save/restore)

The opposite pattern works when the dispatcher has no
"default" arm at all and an early-return precedes the chain:

```c
void f(int event) {
    if (event < 0x??) return;          /* early-out */
    if      (event < ??) event = ??;   /* overwrite arg */
    else if …
    ambient_list[event * 70] = 1;
}
```

PS emits no callee-save prologue — slot lives in eax,
overwriting the arg, and `imul eax, eax, 0x46` reuses it.

### Why

Watcom's regalloc treats `int slot = 0;` as "live from
function entry" (the initialiser is at the top of the IR) so
the var can't share eax with the arg without an explicit
store.  It picks the next-available register (edx) and emits
`xor edx, edx`.  Without the initialiser, slot's first
definition is downstream and Watcom can fold it into the same
register that holds `event` once event is dead.

### Discovery

Commits in pcsound batch — `set_missile_fight_fx` (67 b),
`set_battle_fight_fx` (94 b), `set_prov_ambient` (139 b) all
went from 60–112 b diff → 0 b once the right form was chosen.

## Rule 48 — Struct-cast macro vs local pointer for byte-offset access

When source code receives a *byte offset* into a typed array (rather
than a typed pointer), how you spell the field-access expression
controls whether Watcom emits an **absolute-displacement** addressing
mode or a **register+small-displacement** mode.

### Pattern

PS source apparently used a `#define` macro that re-derives the
struct lvalue at every field touch:

```c
#define CC (*(struct city_cell *)((char *)city_map + sptr))

CC.terrain = ...;       /* per-touch struct re-cast */
CC.base_kind = CC.building;
```

Watcom emits, for each field touch:

```
mov bl, [eax + city_map+0x53174]   ; 6 bytes — abs disp + reg
```

— a single 32-bit absolute displacement that adds `city_map_base + field_offset`
together at compile time, with `eax` carrying just the byte-offset
(`sptr`).  Six bytes per access, no preceding `lea`.

If you instead **cache the struct pointer** in a local:

```c
struct city_cell *c = (struct city_cell *)((char *)city_map + sptr);
c->terrain = ...;
c->base_kind = c->building;
```

Watcom emits:

```
lea eax, [eax + city_map]          ; once at top
mov bl, [eax + 0x1]                 ; 3 bytes — small disp
```

— a register-relative form with a small displacement.  3 bytes per
access, but **all field offsets are encoded as the small disp** because
`city_map_base` is folded into the register at the top.

### Why the byte counts go up so fast

For a function with 13 field touches (`clear_basic`):

| Form               | Per-touch bytes | Total       |
|--------------------|------------------|-------------|
| Macro (PS)         | 6 (abs disp)    | 78          |
| Local ptr          | 3 (reg+small)   | 39 + 1 lea  |

The "smaller" form mismatches PS by 100+ bytes because every access
is encoded differently *and* the first instruction (`lea` vs nothing)
differs.

### When PS used the macro

Two heuristics help identify when the original source must have used
the macro form rather than a cached pointer:

1. **No `lea reg, [base+sym]` at the function top** — if the first
   instruction touching the cell is already a 5-or-6 byte
   `mov al, [reg + abs_disp]`, the source did not cache a pointer.
2. **Multiple field touches with full 32-bit displacements** — every
   `mov [reg + city_map+0x53174]` instead of `[reg + 0x14]` after a
   `lea` is the macro idiom.

### Source-level rule

When decompiling a function whose param/local is a *byte offset*
into `city_map`, `region_map`, etc., **always start with the macro
form**:

```c
#define CM (*(struct city_cell *)((char *)city_map + sptr))
```

Only switch to a cached pointer if PS's disasm shows a `lea` at the
top of the function and small-displacement field touches afterwards.

### Discovery

Commits decomp(map): `clear_basic` (122 b, 4 callers) — 101 b diff
collapsed to 0 b ⟶ byte-exact when the local pointer was replaced
with the `CC` macro.  `garden_an_area` (393 b donor) uses the same
macro on the global `cm_sptr` and matches PS's per-touch absolute-
displacement encoding.


## Rule 49 — `& 0xff` vs `(unsigned char)` selects different zext idioms

### Trigger

The diff shows two different zero-extension patterns for the same
byte load:

```
PS:  8a 90 ?? ?? ?? ??   mov dl, byte ptr [m]
     81 e2 ff 00 00 00   and edx, 0xff           ; 12 b total

RC:  31 d2               xor edx, edx            ; 8 b total
     8a 90 ?? ?? ?? ??   mov dl, byte ptr [m]
```

Both forms produce the same numeric result (zext byte → int), but
PS uses the longer "load + and" form whereas the recomp emits the
shorter "xor + load" form.  In a small function the 4-byte
difference cascades through subsequent instruction offsets,
producing 30-60 b of total residue.

### Source-level lever

The choice is driven by **how the byte is widened in C**:

| Source form                                | Watcom emits                             |
|--------------------------------------------|------------------------------------------|
| `((char *)x)[i] & 0xff`                    | `mov rl, [m]; and reg, 0xff`  (PS-style) |
| `(unsigned char)((char *)x)[i]`            | `xor reg, reg; mov rl, [m]`              |
| `((unsigned char *)x)[i]`                  | `xor reg, reg; mov rl, [m]`              |

The `& 0xff` mask is treated as a regular bitwise-AND: Watcom
loads first, then ANDs the upper bits clear.  The `(unsigned char)`
cast (or pointer cast) is treated as a *type-conversion to a
narrower unsigned type*, which Watcom optimises by pre-zeroing the
destination register before the byte load.

PS source apparently used the explicit AND form here:

```c
int kind = ((char *)city_map)[sptr + 0] & 0xff;
```

NOT the cast form:

```c
int kind = (unsigned char)((char *)city_map)[sptr + 0];   /* recomp-style */
```

### Why this is asymmetric to Rule 8

Rule 8 says "plain `char` defaults to unsigned" and lists both zext
idioms in the table.  It doesn't pin down WHICH source form picks
which idiom.  This rule fills that gap: the idiom selection is
driven by *how the type widens*, not by the underlying char's
signedness.

### Detector

`detect_hints` doesn't currently flag this as a named pattern; it
shows up as an "unexplained" diff in the prologue.  Visual cue:
PS disasm has `mov rl, [m]` followed by `and reg, 0xff`, recomp
has `xor reg, reg` followed by `mov rl, [m]`.  Look for an early
`xor edx, edx` (or any reg) immediately before a byte load.

### Verified on

* `plague_an_atom` (map.c) — 56 b residue with `(unsigned char)`,
  collapsed to 0 b with `& 0xff`.
* `clear_to_empty` (map.c) — partially related; uses
  `(unsigned int)(unsigned char)` to bypass the 4-step signed-div
  idiom (Rule 5 caveat), but still leaves a 1 b `sar` vs `shr`
  diff.
* `select_a_unit` (battle.c) — 80+ b residue with explicit
  `& 0xff` masking on a unit_ref byte field; collapsed to 0 b
  by declaring `int unit_ref = figure_list[fig].unit_ref;` (no
  cast, no mask) and dropping the explicit `(figure_list[i].
  unit_ref & 0xff)` masks at the cmp site.  Implicit char→int
  promotion goes through PS's `xor reg, reg; mov reg.lo, [byte]`
  zext idiom; the explicit `& 0xff` mask forces the longer
  `mov; and` form.  Demonstrates the rule's table direction
  swap: depending on the function, EITHER form might match PS —
  match the disasm, don't assume.

### Caveat

This rule applies *to the zext idiom only* — not to the load width
or the addressing mode.  Both forms still load a byte; both still
use the same memory operand.  Only the surrounding `xor` vs `and`
opcode changes.

### When NOT to apply

If the surrounding code already references the value as `unsigned
char` (e.g. for a `mod size_t` divisor or array index), the cast
form may be needed for type safety even at the cost of byte-match.
The recomp's `xor + mov` form is functionally equivalent and only
breaks byte-exactness, not behaviour.


## Rule 50 — `for` vs `while` for global-counter loops: jump-to-bottom-test layout

### Trigger

A loop iterates a *memory-resident global counter* (e.g. `gmn_x`,
`gmn_y`, `cm_sptr`).  PS emits the loop with the test at the
bottom and a `jmp` from init to the test, so the body falls
through naturally:

```
PS:                                    Recomp (while-form):
mov [gmn_x], 0                         mov [gmn_x], 0
jmp .test                              .test:
.body:                                 cmp ebx, [gmn_x]
  call helper                          jl .exit
  inc [gmn_x]                          .body:
.test:                                   call helper
cmp ebx, [gmn_x]                         mov reg, [gmn_x]
jge .body                                inc reg
                                         mov [gmn_x], reg     ; cached!
                                         cmp ebx, reg
                                         jmp .test
                                       .exit:
```

The recomp form caches the global in a register (Watcom thinks it
can reuse the post-incremented value across the cmp), forcing an
extra callee-save register.  Net diff is 100+ b in a loop with
2-3 nested levels.

### Source-level lever

`for (gmn = lo; gmn <= hi; gmn++)` produces PS's layout.
`while (gmn <= hi) { ...; gmn++; }` produces the cached form.

Functionally identical, but Watcom's loop-shape analysis is
*syntactic*: the `for` form is recognised as a counted loop and
the body is moved above the test (jump-to-bottom-test), with the
counter manipulated *only via memory* (`inc [m]`, `cmp reg, [m]`).
The `while` form is recognised as a general predicate-loop and
Watcom hoists the post-incremented counter to a register to
"save" the redundant memory cmp.

```c
/* GOOD — matches PS */
for (gmn_x = x_min; gmn_x <= x_max; gmn_x++) {
    if (one_aquaduct_ramification() == 0)
        return 0;
}

/* BAD — caches gmn_x, costs an extra callee-save */
gmn_x = x_min;
while (gmn_x <= x_max) {
    if (one_aquaduct_ramification() == 0)
        return 0;
    gmn_x++;
}
```

### Why for-loop wins

The body contains a function call (`one_aquaduct_ramification`)
which Watcom assumes may modify any global.  This means the
post-incremented value of `gmn_x` MUST be re-read from memory
on the next iteration's test — Watcom can't reliably cache it
across the call.

In the `for` form, Watcom spots that the entire iteration —
init, test, advance — is expressible as a memory-resident
counter, and emits the in-place RMW pattern.  In the `while`
form, the counter is conceptually a "loop variable" that
Watcom tries to optimise via register caching, but the call
forces a memory write-back that defeats the optimisation.

### Why this is distinct from Rule 11 / Rule 33

Rule 11 covers *pre-increment cache for sentinel-driven loops*
(local counters compared against a constant).  Rule 33 covers
*2D-region scans with IV substitution* (induction variable in
a register, advanced by a constant per iter).  This rule covers
the simpler case where the counter IS the global itself —
Watcom can either keep it purely in memory (for-loop) or cache
it in a register (while-loop), and the source form chooses.

### Detector

Visual cue: PS shows `inc [m]; cmp reg, [m]; jge .body` at the
bottom of the loop, recomp shows `inc reg; mov [m], reg; cmp
reg, reg2` (or similar) with an extra callee-save in the
prologue.  Heuristic: if PS has fewer pushes than recomp by
exactly 1, and the body contains a function call, suspect this.

### Verified on

* `aquaduct_ramifications` (map.c) — 100 b residue with
  `while`-form, collapsed to 0 b with `for`-form.  Extra
  `push ebp` for the cached counter disappeared.
* `wall_ramifications` + `reg_wall_ramifications` (map.c) —
  same pattern, byte-exact first try with `for`.

### Caveat

Only applies to loops whose counter is a *memory-resident
global* and whose body contains a *function call* (or other
operation Watcom assumes can modify the global).  For loops
over local counters, see Rule 11 / Rule 34.


## Rule 51 — Hoisting `(byte_load) & MASK` into `int` for the EAX-shortcut absolute load

### Trigger

A loop reads a 32-bit global and AND-masks low bits.  PS uses
the eax-specific 5-byte absolute-load encoding, the recomp uses
a generic 6-byte byte-load:

```
PS:  a1 ?? ?? ?? ??         mov eax, [m]              ; 5 b
     83 e0 0f               and eax, 0xf              ; 3 b
     88 c3                  mov bl, al                ; 2 b — total 10 b

RC:  8a 1d ?? ?? ?? ??      mov bl, byte ptr [m]      ; 6 b
     80 e3 0f               and bl, 0xf               ; 3 b — total 9 b
```

Recomp is 1 b shorter per access, but the cascading offset shift
breaks downstream byte-match (typically 30-40 b of diff in a
loop).

### Source-level lever

| Source form                                          | Watcom emits   |
|------------------------------------------------------|----------------|
| `((char *)dest)[i] = (char)((global & 0xf) + N);`    | byte-load form |
| `int v = global & 0xf; ((char *)dest)[i] = (char)(v + N);` | int-load form  |

Hoisting the AND result into an `int` local forces Watcom to
materialise the value as a full 32-bit register, which then uses
the short 5-byte `mov eax, [m]` encoding (opcode `a1`, eax-only).
Inlining the AND into a cast expression lets Watcom narrow the
load to a byte access (no eax shortcut available — `mov bl, [m]`
needs the 6-byte modrm form `8a 1d ?? ?? ?? ??`).

```c
/* GOOD — matches PS */
for (xi = 0; xi < 80; xi++, cm_sptr += 20) {
    int v;
    random();
    v = rand128 & 0xf;
    ((char *)city_map)[cm_sptr + 0] = (char)(v + 8);
}

/* BAD — byte-load form, 36 b residue */
for (xi = 0; xi < 80; xi++, cm_sptr += 20) {
    random();
    ((char *)city_map)[cm_sptr + 0] = (char)((rand128 & 0xf) + 8);
}
```

### Mechanism

The eax-specific absolute-mov encodings (`a0` for byte, `a1` for
dword) are 5 bytes vs the 6-byte modrm form (`8a` / `8b` / `c6`
etc. + `[disp32]`).  Watcom's encoder picks the shortest form
when the destination is `eax` / `al` and the operand is an
absolute address.

When the source has `(char)(global & 0xf + N)`, Watcom's tree
optimiser narrows the operation to byte width (the result is
ultimately stored as a byte).  The byte load destination is the
TARGET register for the assignment — typically a non-eax
register chosen for callee-save / lifetime reasons.  Without
the `mov al, …` opportunity, Watcom emits the 6-byte modrm
load directly into the target.

When the source has an explicit `int v = global & 0xf`, the
hoist forces a separate full-int read.  Watcom puts the load
in eax (the natural arithmetic register), uses the 5-byte
shortcut, and emits a separate `mov target, al` truncation
afterwards.

### Why this differs from Rule 36

Rule 36 (shared-constant register cache) is about *naming a
local for a constant `1`* to defeat per-store immediate folding.
This rule is about *naming a local for a masked-load result*
to force the eax-shortcut absolute-load encoding.  Both are
"name a local to change codegen", but the mechanism and target
encoding differ.

### Detector

Visual cue: PS has `a1` / `a0` at the start of an absolute load,
recomp has `8a 1d` / `8b 1d` / similar.  The lengths differ by
1 byte and the cascade shifts subsequent offsets.

### Verified on

* `generate_cm_scrub` (map.c) — 36 b residue with inlined AND,
  collapsed to 0 b with hoisted `int v`.

### Caveat

Only applies when the destination register is NOT eax/al.  If
Watcom would naturally pick `al` for the byte target (e.g. a
single byte-write expression with no other live registers
needing eax), the byte-load eax shortcut already kicks in and
hoisting has no effect.


## Rule 52 — Variable double-duty for stack-slot sharing

### Trigger

PS uses ONE stack slot to hold two semantically-distinct
values across non-overlapping lifetimes:

```
PS:  mov [esp+4], eax        ; phase 1: save value A
     ...
     mov [esp+4], eax        ; phase 2: overwrite with value B (different meaning)
     ...
     sub [esp+4], ecx        ; phase 2 continues: mutate value B
```

The recomp emits two separate stack slots — one for each
semantic value — bumping the stack frame from 8 b to 12 b
(or 4 b to 8 b) and producing 100+ b of cascading diffs in
the prologue, mid-function reads, and epilogue.

### Source-level lever

Use ONE C variable that mutates from value A to value B
mid-function, rather than declaring two separately:

```c
/* GOOD — matches PS */
int height;            /* one variable, two roles */

height = 2 * half_width + 1;   /* phase 1: stores diameter */
width = height;
... x-clamp uses height as diameter ...
if (y < 0) {
    height = y + height;       /* phase 2: rewrite as effective_height */
    y = 0;
} else if (y + height > 60) {
    height -= (y + height - 60);
}
... loop test uses height as effective_height ...
```

Compare the wrong form:

```c
/* BAD — two slots */
int diameter = 2 * half_width + 1;
int height;
... x-clamp uses diameter ...
if (y < 0) {
    height = y + diameter;
    y = 0;
} else if (y + diameter > 60) {
    height = diameter - (y + diameter - 60);
} else {
    height = diameter;
}
... loop test uses height ...
```

### Mechanism

Watcom's regalloc/spill module (`bld/cg/c/regalloc.c`) computes
liveness intervals per *named variable*.  When you declare two
variables, even if their lifetimes don't overlap, the compiler
allocates them separate slots — it doesn't (in 10.0a) coalesce
slots based on liveness, the way modern compilers' register
allocators do.

Reusing the same C variable name forces Watcom to use one slot
because it sees one live range that mutates over time.  This
is the "variable name = lifetime" identity assumption.

### Why this differs from Rule 24 (spill-via-local)

Rule 24 is about *forcing* a stack slot (or register) for an
argument by introducing a named local.  This rule is the
inverse: *avoiding* an extra stack slot by reusing one variable
across two semantic phases.

Both rules exploit the same underlying mechanism (Watcom's
"variable name = lifetime" model), but in opposite directions:
* Rule 24: introduce a local to gain a slot.
* Rule 52: collapse two locals into one to free a slot.

### Detector

Visual cue: PS's `sub esp, N` is smaller than recomp's by
exactly 4 (one slot's worth).  If you also see a `mov
[esp+M], eax` happening twice in PS at different points (with
the second write logically "starting a new variable"), this
rule applies.

### Verified on

* `set_rm_range` (map.c) — 12 b stack frame collapsed to 8 b
  by reusing `height` for both diameter and effective_height.
  Net diff impact ~50 b (the slot reuse cascaded into other
  register choices).

### Caveat

Only valid when the two semantic values' lifetimes truly don't
overlap.  If both need to be live simultaneously, they need
separate slots regardless.  Reading the disasm carefully
(when does each value's last use happen?) is the only way to
know if the lifetimes can be merged in source.

### When NOT to apply

For values that DO need to coexist (e.g. diameter still needed
AFTER the y-clamp, perhaps for a third clamp dimension), keep
them as separate variables.  Forcing reuse will compute wrong
results.

---

## Rule 53 — `(expr) != 0` materialises a boolean via `setne; movzx`; bare `expr` does not

### Trigger

A diff at a tiny bit-test → 0/1 conversion site shows two
fundamentally different idioms:

```
PS:  f6 c2 01            test  dl, 1                 ; 3 b
     0f 95 c0            setne al                    ; 3 b
     89 c6               mov   esi, eax              ; 2 b
     81 e6 ff 00 00 00   and   esi, 0xff             ; 6 b   ← Rule 49 zext
                                                     ; total 14 b
RC:  89 d6               mov   esi, edx              ; 2 b
     83 e6 01            and   esi, 1                ; 3 b
                                                     ; total  5 b
```

PS uses 9 more bytes for what looks like the same parity-bit test.
This isn't an optimization regression — it's because the two source
forms compute *different things*:

  * `(y & 1)` is a value that happens to be 0 or 1.
  * `(y & 1) != 0` is a *boolean test result* that's then converted
    to an int (0 or 1).

Watcom 10.0a treats them differently in the front-end: a bare AND
emits the AND and uses the result; an `!= 0` (or any explicit
boolean conversion) materialises the test through `setne` and then
zero-extends.

### Source-level lever

| Source form              | Watcom emits                              | Bytes |
|--------------------------|-------------------------------------------|-------|
| `int p = y & 1;`         | `mov reg, edx; and reg, 1`                |   5   |
| `int p = (y & 1) != 0;`  | `test dl, 1; setne al; mov reg, eax; and reg, 0xff` |  14   |
| `int p = !!(y & 1);`     | (longer; emits 2 setcc)                   |  ≥ 14 |
| `int p = (y & 1) ? 1 : 0;` | same as `!= 0`                          |  14   |

The three "explicit boolean" forms (`!= 0`, `!!`, ternary) all
funnel through the same `setne; movzx` code path.

### Why this is asymmetric to Rule 49

Rule 49 is about how the **load width** widens: byte → int via
`xor; mov rl` vs `mov rl; and reg, 0xff`.

Rule 53 is about how the **test result** materialises into an int.
The `and reg, 0xff` at the tail of the `setne` path is in fact a
**Rule 49 instance** — Watcom is widening the 8-bit `setne al`
result to int via the post-load AND form (because it's still
"wide an existing byte register" semantically, not "load and
zero-extend").

You can have a function that triggers Rule 53 but NOT Rule 49 if
the value is consumed as a byte register (e.g. stored straight
back to a byte field).  And vice versa: a function reading a byte
into an int local without any boolean test triggers Rule 49 only.

### When PS picks the boolean form

PS source had a `bool`-like idiom:

```c
int parity = (y & 1) != 0;
int xl     = x - parity;
```

If the source had been `int parity = y & 1;`, PS would have
emitted the 5-byte `mov; and` form — and our recomp matches *that*
form when written that way.  The three_by_three function in
pm_map0.c is the canonical example:

  * Source `(y & 1) != 0`  →  byte-exact match (PS-style, 14 b).
  * Source `y & 1`         →  43-byte function vs PS's 54 (9 b
                             diff cluster around the parity test).

### Detector

`detect_hints` doesn't currently flag this as a named pattern,
but visual cue: PS disasm has `setne reg8` immediately followed
by a zero-extension (`movzx`, or `mov reg, eax; and reg, 0xff`).
A `setne` in PS that the recomp lacks is a near-certain Rule 53
hit — PS.EXE only contains **52 `setcc` instructions across all 2261
functions** (re-counted 2026-06), so they're rare and pattern-laden.
The inverse is the more common error: a recomp `setcc` where PS has none
means the source wrote `x = (cond);` but PS wrote `if (cond) x = 1;` with
a pre-zeroed slot and branches — 13 diffing functions currently do this.

### Verified on

* `three_by_three` (pm_map0.c) — `int parity = (y & 1) != 0;`
  is byte-exact; bare `int parity = y & 1;` would leave 9 b of
  unexplained diff at the prologue.
* `docs/codegen-experiments/parity-bool.py` — 4 trials covering
  bare AND / `!= 0` / `!!` / ternary forms, demonstrating the
  setne path is selected by all three explicit-boolean forms.

### When NOT to apply

If the value is consumed only as a 0/1 multiplier or array index,
the bare AND form is **shorter and faster** — there's no semantic
need for the boolean conversion.  Use the `!= 0` form only when
PS source clearly distinguished "the bit is set" (boolean) from
"the bit's value" (numeric).  Look at how the value is *used* —
if it's added to a counter or compared to zero again, the bool
form is right; if it's used as an offset or shift amount, bare
AND is right.

### Caveat

Rule 53 is *partly* a Rule 49 instance (the `and reg, 0xff` zext
of the setne result is Rule 49's "explicit AND" form).  But the
first three bytes (`test`/`setne`) are uniquely Rule 53; you
cannot get them from any source idiom that doesn't go through a
boolean conversion.  When both rules apply to the same site,
fix the boolean form first (Rule 53), then check if the residual
zext idiom needs Rule 49 attention.


## Rule 54 — Statement-form `x--;` keeps original load + decremented value in separate registers

### Trigger

A "decrement field if non-zero" snippet shows different register
allocation between PS.EXE and the recomp.  PS allocates TWO
sub-registers (typically `dh` for the load and `bl` for the
decremented store), the recomp collapses to ONE (`dl` used for
both load and decrement-in-place):

```
PS:                             Recomp:
  mov  dh, [eax + 0x4E]           mov  dl, [eax + 0x4E]
  test dh, dh                     test dl, dl
  je   skip                       je   skip
  mov  bl, dh    ; copy           dec  dl       ; in-place
  dec  bl        ; decrement      mov  [eax + 0x4E], dl
  mov  [eax + 0x4E], bl
skip:                           skip:
```

PS uses a CALLEE-SAVE register (ebx) for `bl`; the recomp's
collapse means ebx is unused and the prologue lacks `push ebx`.
Cascades through the rest of the function as ebx becomes
available for OTHER byte values, while the recomp must use
caller-save registers (often forcing a 2nd, separate byte
allocation later in the body).

### Mechanism

C `field--;` (post-decrement, void context) is parsed by Watcom
as a read-modify-write whose *value* is the original.  Even
though the statement-level expression's result is discarded,
Watcom's CG keeps the original load alive until after the
modified store, allocating it a separate register.  The
canonical IR shape is:

```
  T  = load(field)         ; original, alive until post-store
  T' = T - 1
  store(field, T')
  ; T's lifetime ends here — but the allocator already gave it
  ; its own virtual name and register
```

Versus the explicit-temp form:

```c
char tc = field;
if (tc != 0) {
    field = tc - 1;
}
```

Watcom's CG sees `tc` as a single virtual name; CSEs the load
and the decrement source together; allocates one register.

### Source-level lever

| Source form                                  | Watcom emits                                   |
|----------------------------------------------|------------------------------------------------|
| `if (field != 0) field--;`                    | TWO regs: `mov A, [m]; test A, A; je _; mov B, A; dec B; mov [m], B` |
| `if (field != 0) field = field - 1;`         | TWO regs (same as `field--;`)                  |
| `tc = field; if (tc != 0) field = tc - 1;`   | ONE reg: `mov A, [m]; test A, A; je _; dec A; mov [m], A` |

The `field = field - 1;` form (re-reading the field for the RHS)
also works because Watcom CSEs the two memory reads to one
register but keeps the test value and the decremented value as
SEPARATE virtuals.

### Why it matters

The two-register pattern is what enables byte-half packing
(Rule 24-style): once Watcom commits to using `ebx` for one byte
value (`bl`), it can pack a *second* byte value into `bh` later
in the function (e.g. a sprite_type read).  The collapsed-to-
one-reg form has fewer simultaneously-live byte virtuals, so
Watcom prefers caller-save (`al`, `dl`) and never picks up `ebx`.

### Detector

`detect_hints` doesn't currently flag this directly.  Visual
cues:

  * PS prologue has `push ebx` that the recomp lacks.
  * In the diff, PS row sequence: `mov rh, [m]; test rh, rh;
    je …; mov sl, rh; dec sl; mov [m], sl` (two distinct byte
    registers `rh` and `sl`).
  * Recomp row sequence: `mov rl, [m]; test rl, rl; je …; dec
    rl; mov [m], rl` (single byte register reused).

### Verified on

  * `figure_intelligence` (battle.c) — 87 b residue collapsed to
    3 b by switching from
    `tcount = field; if (tcount != 0) field = tcount - 1;` to
    `if (field != 0) field--;`.  The remaining 3 b were closed
    by Rule 55 (inline byte-field access).
  * Watcom 10.0a, `-bt=dos -mf -4r -s`.

### Companion: Rule 55 (inline byte-field access)

Rules 54 and 55 often need to be applied *together* on the same
function.  Rule 54 unlocks `ebx` as a callee-save byte register;
Rule 55 then ensures Watcom uses the OTHER half of `ebx` for a
later byte value rather than allocating a fresh register.


## Rule 55 — Inline byte-field access lets Watcom pack into the running byte-half

### Trigger

A byte field is read once, tested, and used as an array index in
a function-pointer dispatch.  PS allocates the byte to a callee-
save register-half (`bh`) that's already in flight from an
earlier byte op; the recomp allocates a fresh caller-save
register (`al`):

```
PS:                                   Recomp:
  mov bh, [eax + 0x5]                   mov al, [eax + 0x5]
  test bh, bh                           test al, al
  jle remove_path                       jle remove_path
  movsx eax, bh                         movsx eax, al
  cmp eax, 0x12                         cmp eax, 0x12
  jl dispatch                           jl dispatch
```

3-byte residue per pattern occurrence (one byte per `mov`/`test`/
`movsx` register-encoding difference).

### Mechanism

When the C source declares an explicit local for the byte:

```c
signed char st = (signed char)figure_list[fig].sprite_type;
if (st <= 0 || st >= 0x12)  remove_figure(fig);
else                         ((void(*)(void))intelligences[st])();
```

`st` becomes a virtual name with its own def-use chain.  The
allocator processes it independently of the surrounding byte
values' lifetimes and tends to pick the next FREE register
(typically caller-save eax/edx since those aren't carrying
existing data).

When the source inlines the read at every use site:

```c
if ((signed char)figure_list[fig].sprite_type <= 0 ||
    (signed char)figure_list[fig].sprite_type >= 0x12) {
    remove_figure(fig);
} else {
    ((void(*)(void))intelligences[
        (signed char)figure_list[fig].sprite_type])();
}
```

Watcom's CSE folds the three reads into a SINGLE `mov` + reuse,
but the resulting virtual name is created LATER in the IR
(after the surrounding statements have already pinned ebx for
their own byte ops via Rule 54).  The allocator finds `bh` free
because `bl` was just consumed by the dec-store from the
preceding `field--;` block, and packs the new value into `bh`.

### Source-level lever

| Source form                                   | Watcom emits        |
|-----------------------------------------------|---------------------|
| `T t = field; if (t == X) …`                  | Fresh reg (`al`)    |
| `if (field == X) …`  (inlined at use sites)   | Reuses byte-half (`bh`) |

The CSE of multiple inline reads produces a single load with
the SAME effect as the explicit local, but the regalloc decision
happens LATER in the IR, allowing byte-half packing.

### When NOT to apply

  * If the byte field is actually MUTATED between reads, you
    can't inline (each read sees a different value).
  * If the function has no surrounding byte op that could share
    the same callee-save register, there's nothing to pack
    INTO — both forms produce equivalent code.
  * If the field is read only ONCE in the function, the local
    form may already pack correctly via Rule 24 — try both.

### Verified on

  * `figure_intelligence` (battle.c) — final 3 b residue
    collapsed to 0 b by inlining `(signed char)figure_list[fig]
    .sprite_type` at all three use sites.  The post-Rule-54
    diff showed `mov bh, [+0x5]` (PS) vs `mov al, [+0x5]`
    (recomp); switching to inline access flipped the recomp
    to `bh` to match.
  * Watcom 10.0a, `-bt=dos -mf -4r -s`.


## Rule 56 — `for`-update clause emits expressions in declaration order, after the body

### Trigger

A loop body has TWO independent updates (e.g. a counter
increment + a pointer advance).  Their relative emission order
between PS.EXE and the recomp is opposite, producing 2-byte
residue per pair:

```
PS:                          Recomp:
  or  [eax + 2], 2             or  [eax + 2], 2
  inc edx        ; col++       add eax, 4     ; off += 4
  add eax, 4     ; off += 4    inc edx        ; col++
  cmp edx, ebx                 cmp edx, ebx
```

Same instructions, swapped order.  Cascades through the offset
of the back-jmp and any subsequent code by 2 bytes per swap.

### Mechanism

Watcom emits statements in source order.  A `for` loop's three
clauses are ordered: init → cond-test → body → update.  Within
the **update** clause, comma-separated expressions emit in
declaration order, AFTER the body's last statement.

Source A (body-last update):

```c
for (col = x0; col <= x1; ++col) {
    arr[off + 2] |= 2;
    off += 4;          /* body statement */
}
```

Emits: `or; add off; inc col; cmp; jle`.

Source B (update-clause-only):

```c
for (col = x0; col <= x1; ++col, off += 4) {
    arr[off + 2] |= 2;
}
```

Emits: `or; inc col; add off; cmp; jle`.

Both forms produce the same instructions; the order of the two
increments is the only difference.

### Source-level lever

If PS's loop tail shows a specific increment-pair order that
doesn't match the natural body-then-update flow, move the
"misordered" increment into the for-update clause and place
its declaration in the position you want it emitted.

### Generalization

The same lever works for `do…while` and `while` loops by moving
update statements out of the body into a comma operator:

```c
while (cond) {
    body;
    a++;
    b += k;       /* recomp emits a++; b+=k */
}

while ((body, a++, b += k, 1)) ... /* DON'T do this — illegible */
```

In practice the comma-operator hack is too ugly; for non-`for`
loops, the lever is "reorder the body statements" instead.
For `for` loops specifically, the update clause is the natural
home for both increments.

### When NOT to apply

  * If the two updates have a data dependency (one reads the
    other), they must stay in dependency order regardless of
    where they appear in the source.
  * If PS source clearly separates them (e.g. one is after a
    conditional store), the body-statement form may be correct.
    Look at PS's pattern carefully before applying.

### Detector

`detect_hints` doesn't currently flag this — it surfaces as
"unexplained" diff rows in the loop tail.  Visual cue: two
adjacent rows with same-instruction, swapped-order between
PS and recomp, both arithmetic operations on different
registers.

### Verified on

  * `set_figure_map_refresh` (battle.c) — 7 b residue collapsed
    to 0 b by moving `byte_off += 4` and `byte_off += row_stride`
    out of the inner / outer loop bodies into the for-update
    clauses (`for (col = x0; col <= x1; ++col, byte_off += 4)`).
  * Watcom 10.0a, `-bt=dos -mf -4r -s`.

## Rule 57 — Multiplication accumulator goes into the first operand of the surrounding `+`

**TL;DR.**  When a compound expression `a + b * c` (or any
additive form with a multiplication factor) needs both `a` and
`b * c` to be live at the same time, Watcom 10.0a places the
multiplication accumulator in whichever register it computes
FIRST.  The C source ORDER of the addition determines which
register gets reused for the result.  Specifically:

  * `b * c + a`  — multiplication runs in EDX, then `add eax,
     edx` produces the result in EAX (which the next statement
     can use immediately).
  * `a + b * c`  — `a` is loaded into EAX, the multiplication
     runs in EDX, then `add eax, edx` produces the result in
     EAX (matching the source order: load `a` first, accumulate
     into it).

When the result of `a + b*c` is **also stored to a global** at
the end of the statement (e.g. `pm_screen_x_end = a + b * c`),
placing `a` first triggers Watcom to keep the running
accumulator in EAX/EDX in the order PS uses for the trailing
recomp tail, eliminating the extra `mov edx, eax` shuffles.

### What you must write

```c
pm_screen_x_end = pm_screen_x_start + pm_screen_width * pm_diamond_width;
pm_screen_y_end = pm_screen_y_start + (pm_screen_height + 1) * pm_diamond_half_height;
```

Note `pm_screen_x_start` (the simple load) comes FIRST.

### What goes wrong if you flip the operands

```c
pm_screen_x_end = pm_screen_width * pm_diamond_width + pm_screen_x_start;
```

Produces the multiplication accumulator in EDX and the simple
load in EAX, then `add edx, eax` flowing into a different reg
for the next statement.  Cascades through ~26–32 byte diffs
in trailing recomp code that reads the just-written global.

### Discovery

* Commits `bd410d0` (refresh_zoom_mode / refresh_battle_zoom_mode
  via cgex `start-first` trial) and `e855861` (initial faithful
  attempt with operand-flipped form, ~30 b residue).
* CGex experiment `docs/codegen-experiments/refresh-battle-zoom-mode.py`
  (8 trials, only `start-first` matches).

### Verified on

* `refresh_zoom_mode` (refresh.c) — 32 b residue → 0 b.
* `refresh_battle_zoom_mode` (refresh.c) — 26 b residue → 0 b.
* Watcom 10.0a, `-bt=dos -mf -4r -s`.

### Related rule

Rule 4 (operator preservation) is the more general principle:
Watcom preserves operand order for `cmp`/`sub`/`add` literally.
Rule 57 is the specific cascading case where the choice flows
through into surrounding statements via register-reuse choice.


## Rule 58 — Mutate the first parameter to keep multiply/divide temporaries in EBX/ECX

**TL;DR.**  For tiny integer helpers of the form `(a * b) / C` or
`(value * C) / total`, Watcom 10.0a emits a different register-allocation
shape depending on whether the product is a fresh expression/local or a
mutation of the **first parameter**.

When PS.EXE wants the product in `EBX` and the divisor in `ECX`:

```asm
push ebx
push ecx
mov  ebx, eax        ; first parameter becomes product accumulator
imul ebx, edx        ; or imul ebx, eax, C
mov  ecx, C/total    ; divisor in ECX
mov  eax, ebx
mov  edx, ebx
sar  edx, 0x1f
idiv ecx
pop  ecx
pop  ebx
ret
```

write the C as a **first-parameter mutation**:

```c
int totalXpercent(int a, int b)
{
    a *= b;
    return a / 100;
}

int valueDIVtotal(int value, int total)
{
    value *= 100;
    if (total != 0)
        value = value / total;
    else
        value = 0;
    return value;
}
```

### What goes wrong if you write the obvious expression

```c
int totalXpercent(int a, int b)
{
    return (a * b) / 100;
}
```

or even:

```c
int p = a * b;
return p / 100;
```

Watcom treats the product as a temporary and produces the smaller but
non-PS register allocation:

```asm
push ebx
imul edx, eax        ; product stays in EDX
mov  ebx, 100        ; divisor in EBX
mov  eax, edx
sar  edx, 0x1f
idiv ebx
pop  ebx
ret
```

That misses PS.EXE's extra `ECX` callee-save and blocks the
cross-function tail merge between sibling percent helpers.

### Why this happens

This matches Open Watcom v1's `regalloc.c::GiveBestReg` /
`CountRegMoves` heuristic: assigning the mutated first-parameter
conflict to `EBX` creates high-value register-register move savings
(`mov ebx,eax` followed by `imul ebx,edx`).  With a fresh expression,
the multiply result is just a short-lived temp, so the allocator leaves
it in `EDX` and uses `EBX` for the divisor constant.  Once `EBX` is
claimed by the product, the divisor is forced into `ECX`, producing
PS's `push ebx; push ecx` shape.

### Discovery

* CGex experiment `docs/codegen-experiments/totalXpercent.py`: after
  enabling `chk=True` (to match lib32.c's `#pragma on(check_stack)`),
  the `a-times-equals-b` trial reduced `totalXpercent` from 24 b diff
  to 1 b (the only residual was cgex's local `__CHK` stub byte).
* Applying the same pattern to the real source made all three helpers
  byte-exact.

### Verified on

* `totalXpercent` (lib32.c) — 24 b residue → 0 b.
* `totalXpercentX100` (lib32.c) — 12 b residue → 0 b.
* `valueDIVtotal` (lib32.c) — 34 b residue → 0 b.
* Watcom 10.0a, `-bt=dos -mf -4r -s`, with lib32.c's local
  `#pragma on(check_stack)` in effect.

## Rule 59 — Pass-through parameters reserve EAX/EDX, biasing the byte-temp allocator into EBX

**TL;DR.**  When PS.EXE emits `push ebx; xor ebx, ebx; mov bl, [byte_global]; cmp ebx, IMM`
at the top of a function whose body otherwise has no use for EBX, the
function's PS source signature **takes parameters that get forwarded
verbatim to inner callees** — even if the function never reads those
parameters itself.  Reserving `EAX`/`EDX` for the params is what
pushes the byte temp past the front of the `ABCDRegs` priority list
and lands it in the callee-save `EBX`.

### Symptom

A tiny dispatcher with one byte-global test ends up using `EBX` for
the zero-extended byte read, with matching `push ebx`/`pop ebx` in
the prologue/epilogue:

```asm
push ebx
xor  ebx, ebx              ; would normally be `xor eax, eax`
mov  bl,  byte ptr [m]     ; would normally be `mov al, [m]`
cmp  ebx, 1                ; would normally be `cmp eax, 1`
jne  .else
call blitter_a
pop  ebx
ret
.else:
call blitter_b
pop  ebx
ret
```

The naive C source

```c
void copy_to_physical_screen(void)
{
    if (screen_mode == 1) {
        convert_and_copy_to_256xscreen();
        return;
    }
    copy_to_640_480_screen();
}
```

compiles to a 13 b-diff version that uses `EAX` instead.  No amount
of body-level rewriting (char vs unsigned char locals, register
hints, switch vs if-else, volatile, ternary, struct/union/array/
pointer-cast access to the global, fake live ghost locals, two-test
show_landfill-style patterns, debug flags, calling conventions) can
shift the allocator off `EAX` — we tried 100+ permutations in
`docs/codegen-experiments/copy-to-physical-screen.py`.

### Right C: declare and forward two pass-through params

```c
void copy_to_physical_screen(int p1, int p2)
{
    if (screen_mode == 1) {
        convert_and_copy_to_256xscreen(p1, p2);
        return;
    }
    copy_to_640_480_screen(p1);
}
```

with matching `extern` declarations on the inner callees:

```c
extern void convert_and_copy_to_256xscreen(int p1, int p2);
extern void copy_to_640_480_screen(int p1);
```

The callees can be stubs (their bodies don't have to actually USE
the params) — what matters is that the **caller's parm list claims
EAX and EDX** and forwards them through, so Watcom can't optimize
them away.

### Mechanism

In Open Watcom v1's `regalloc.c::GiveBestReg`, the byte-temp's
`tree->regs` list is `ABCDRegs = [EAX, EDX, EBX, ECX]`.  The
allocator iterates this list in order; for each candidate register
it calls `CountRegMoves` to score savings, and picks the highest
score.  With no register-move opportunities (a single-use byte
temp, no other conflicts), all four candidates tie at zero savings
and the **first** one wins — normally `EAX`.

When `EAX` and `EDX` are already claimed by parameter conflicts
(`HW_Ovlap( reg, conf->with.regs )` is true), they're **skipped**:

```c
if( !HW_Ovlap( reg, conf->with.regs )
 && !HW_Ovlap( reg, except ) ) {
    saves = CountRegMoves( conf, reg, conf->tree, 3 );
    ...
}
```

so the byte temp's allocator scans past `EAX` and `EDX` and lands
on `EBX`.  Watcom then emits the `push ebx; pop ebx` callee-save
pair because EBX is callee-save in `__watcall`.

Unused `int a, int b` declarations alone DON'T trigger this —
Watcom optimizes truly unused params away before regalloc.  The
pass-through to a callee that *also* takes args in EAX/EDX is what
keeps the params live across the byte-temp allocation.

### Discovery

1. Searched all decompiled functions for the prologue `push ebx;
   xor ebx, ebx; mov bl, [m]`; only `copy_to_physical_screen`
   matched.  Broadened to **anywhere** in the body and found 68
   matches.  The smallest with the SAME 2-test dispatcher shape
   was `show_landfill` (37 b).
2. `show_landfill` had the comment "Faithful (~23 byte diffs).
   Watcom is inlining our 1-line stub bodies…" — a wrong diagnosis.
3. `c2 inferred-sig show_landfill` revealed: **all 7 callers set
   EAX and EDX before the call** (e.g.
   `flag_mode_action: mov edx, [com_y]; mov eax, [com_x]; call
   show_landfill`).  PS source signature was `void show_landfill
   (int x, int y)` even though the body ignores `x` and `y`.
4. `convert_and_copy_to_256xscreen` (callee) had inferred-sig
   `(eax, edx)` and `copy_to_640_480_screen` had `(eax)` — they
   take pass-through args.
5. Cgex `parm-eax-edx-passed` trial (params declared, params
   forwarded to typed callees) closed `copy_to_physical_screen`
   from 13 b → 0 b in one shot.
6. Same pattern applied to `show_landfill` closed it from 23 b
   → 0 b.

### When to apply

Whenever you see a small dispatcher / wrapper function with the
EBX-byte-zero-extend prologue and your decomp is stuck at a
10–30 b regalloc-shape diff, run:

```bash
uv run c2 inferred-sig <fn_name>
```

If the report shows `! ARG COUNT: declared=N, inferred=M` (M > N)
or lists callers consistently setting EAX/EDX, the function had
pass-through parameters in PS source.  Update:

* The function's signature — add `int p1`, `int p2`, ... in
  declared order.
* Per-file `extern` declarations of the inner callees — give them
  matching parameter lists so the forwarding compiles cleanly.
* The function body — forward each param to the callee that
  consumes it (`callee(p1, p2)`).
* Stub bodies — widen the stubs to `void X(int p1, int p2) { (void)p1; (void)p2; }`
  if needed to compile.

Then `c2 gen-header` + `c2 decomp-verify` to confirm.

### Caveats

* The fix relies on the inner callees ALSO taking matching args.
  If the callees are `void(void)` in PS but the wrapper has
  pass-through params, the wrapper still triggers the EBX shape —
  but you need a `(void)p` sink in the body to keep Watcom from
  optimizing the param storage out.
* This rule applies only to functions whose signature actually
  has params in the PS source.  Don't add fake params
  prophylactically: it changes ABI for any caller that exists.
* Functions with **0 callers** (orphan code, like
  `copy_to_physical_screen` itself) can be given any pass-through
  signature without breaking calling code, since nothing calls
  them.  Use the inferred-sig of the inner callees as the
  authoritative source.

### Verified on

* `copy_to_physical_screen` (lib32.c) — 13 b → 0 b.  0 callers in PS.EXE
  (orphan); pattern derived from inner-callee inferred sigs.
* `show_landfill` (landfill.c) — 23 b → 0 b.  7 callers all set
  EAX+EDX; both inner callees take `(eax, edx)`.
* Watcom 10.0a, `-bt=dos -mf -4r -s`.


## Rule 60 — Array indexing: `arr[a + b*N]` fuses before scaling; explicit byte-offset keeps operands separate

### Pattern

When you index a 4-byte array with two terms that need to be
combined and scaled, e.g. `pseudo_map[cell_x + cell_y * 81]`,
Watcom 10.0a emits two materially different addressing forms
depending on whether the source expresses the address as a
**typed array subscript** or as an **explicit byte offset**.

  * **Typed array subscript** ``arr[a + b * N]`` — Watcom
    fuses `a + b*N` into a single integer register *before*
    the implicit `* sizeof(elem)` scale, then loads via
    `[reg*4 + base]` (single SIB-scaled register).
  * **Explicit byte offset** ``*(int *)((char *)arr + b*N*4 + a*4)``
    — Watcom keeps the two scaled byte-offsets in *separate*
    registers and loads via `[reg + reg*4 + base]` (full
    base+index*scale SIB form).

Same C semantics, different bytes::

    /* Recomp form (operands fused before scale): */
    pm_val = pseudo_map[cell_x + cell_y * 81];

    ; recomp bytes:
    mov  eax, ecx          ; eax = cell_y
    shl  eax, 2; add eax, ecx; shl eax, 4; add eax, ecx  ; eax = cell_y*81
    add  eax, esi          ; eax = cell_y*81 + cell_x  ← FUSED
    mov  eax, [eax*4 + 0x73d84]                        ; one-reg SIB

    /* PS form (byte-offset keeps operands separate): */
    pm_val = *(int *)((char *)pseudo_map
                      + cell_y * (81 * 4)
                      + cell_x * 4);

    ; PS bytes:
    mov  eax, ecx          ; eax = cell_y
    shl  eax, 2; add eax, ecx; shl eax, 4; add eax, ecx  ; eax = cell_y*81
    shl  esi, 2            ; esi = cell_x * 4           ← SCALED EARLY
    mov  eax, [esi + eax*4 + 0x73d84]                  ; two-reg SIB

The byte-count diff is small per-site (~1 b: a `shl reg, 2`
that doesn't appear in the fused form) but **cascades** because
the function body is now 1 byte shorter and every downstream
short-jump (`jl`, `jge`, `je`, etc.) computes a 1-off rel8
displacement.  In `show_one_ptr` (598 b, pm_map0.c) one
single-site fix closed all 7 residual diff rows in one shot
(4 jump rel-byte off-by-ones + the addressing-mode swap +
trailing-byte alignment shift).

### Why?

Both forms are mathematically equivalent (`(a + b*N) * 4 + base
== a*4 + b*N*4 + base`), but Watcom's address-mode lowering
(`bld/cg/c/optindex.c`) treats them differently:

  * `arr[expr]` with elem-size-4 array: the scale factor is
    inserted at the END as a SIB scale.  Watcom may fuse
    multi-term `expr` BEFORE the implicit scale to keep one
    free SIB-scale slot.
  * `*(int *)((char *)base + raw_byte_offset)` lowers the
    byte-offset as a regular integer expression that Watcom
    then has to fit into available addressing-mode slots.
    Two pre-scaled terms in registers stay there; the load
    uses base+index*scale instead of one indexed register.

Effectively, with the typed-array form, Watcom prefers a
"smaller register pressure" load (one SIB-scaled reg, +disp32
base); with the byte-offset form, it picks the more flexible
two-register SIB form when both operands are already in regs.

### When it matters

For 4-byte arrays where the index expression naturally
decomposes as `col + row*stride`:

  * **`pseudo_map[x + y*81]`** (panorama display) — show_one_ptr.
  * **`city_map[ix + iy*80]`** (Rule 25) — careful here: city_map
    is a struct array where the cell stride is 20 bytes, NOT 4;
    the byte-offset form for that uses different multipliers.
  * **Any 2-D `int[]` traversal** where PS keeps the column index
    in one reg and the row offset in another.

The signature of "this function is hitting Rule 60" is a diff
where PS has `shl esi, 2; mov eax, [esi + eax*4 + base]` and
recomp has `add eax, esi; mov eax, [eax*4 + base]` — i.e.
identical mnemonics modulo the final addressing mode and one
extra `shl` instruction in PS.

### Fix

Replace::

    val = arr[col + row * stride];

with::

    val = *(int *)((char *)arr + row * (stride * 4) + col * 4);

The cast to `(char *)` keeps the offsets in raw bytes; the
explicit `* 4` on each term matches the element size.  Watcom
then keeps `col*4` and `row*stride*4` in separate registers
and loads via the two-reg SIB form.

### Caveats

* This is a **per-site** fix.  Rewriting every array access
  in a function this way is overkill; only sites where the
  diff specifically calls for the two-reg SIB form need the
  byte-offset form.
* The byte-offset form is **harder to read** than `arr[...]`.
  Add a comment naming the original index expression so future
  readers can decode it.
* Don't conflate with **Rule 46** (`arr + i + k` vs
  `&arr[i + k]`): Rule 46 is about preserving an
  ALREADY-SCALED register across two consecutive accesses.
  Rule 60 is about controlling the scale-vs-fuse choice within
  a SINGLE access.

### Discovery

Found while decompiling `show_one_ptr` (598 b @ 0x35F0F,
pm_map0.c).  After getting the body structurally correct
(7 residual diff rows / 344 b), the asm pattern showed PS
emitting `shl esi, 2` + two-reg SIB, while the recomp emitted
fused-add + one-reg SIB.  Switching the single
`pseudo_map[cell_x + cell_y * 81]` access to the byte-offset
form closed the function byte-exact.

### Verified on

* `show_one_ptr` (pm_map0.c) — 344 b → 0 b. 29 callers, top
  panorama-render dispatcher.
* Watcom 10.0a, `-bt=dos -mf -4r -s`.

## Rule 61 — Sibling functions PS shipped as separate bodies must NOT be factored into a shared static helper

Meta-rule about source structure, not a per-instruction
codegen pattern.  Three or more PS-source functions with
near-identical structure but differing by a small constant
(size, kind, table pointer) must be decompiled as separate
standalone bodies — NOT as thin wrappers over a shared
`static` helper.  Even though Watcom 10.0a's aggressive
inliner makes the wrapper-version compile to the right
SIZE, the wrapper-version diverges from PS by hundreds of
bytes per function because the inlined-helper body makes
different regalloc / IV-substitution / loop-shape choices
than PS's hand-spelled body.

### Pattern

Given three sibling functions like the city-map area
stampers:

    /* PS source (per debug line-numbers): three separate */
    /* ~50-line functions, body spelled out in each.       */
    int put_x2_area(int x, int y, char bk, int eb, int color);   /* lines 2309-2357 */
    int put_x3_area(int x, int y, char bk, int eb, int color);   /* lines 2359-2408 */
    int put_x4_area(int x, int y, char bk, int eb, int color);   /* lines 2410-2458 */

**Wrong** (compiles to the right size, diverges by 440-452
b each):

    static int put_city_sized_area(int x, int y, char bk,
                                   int eb, int color,
                                   int size, char *diamond)
    {
        /* ~50 lines of stamping loop */
    }

    int put_x2_area(int x, int y, char bk, int eb, int c) {
        return put_city_sized_area(x, y, bk, eb, c, 2, diamond_ofsets_2x);
    }
    /* idem put_x3_area / put_x4_area */

**Right** (19-21 b residue per function):

    int put_x2_area(int x, int y, char bk, int eb, int color)
    {
        int row_skip = (80 - 2) * 20;     /* literal, not param */
        ...
        for (yi = y0; yi < y0 + 2; ) {    /* literal 2 in cond */
            for (xi = x0; xi < x0 + 2; ) {
                ...
            }
        }
    }
    /* idem put_x3_area (literal 3) / put_x4_area (literal 4) */

### Why?

Watcom 10.0a inlines `static` functions when:

  * The callee has no other external references.
  * The callee body fits the inliner's size budget (small
    `-oe` threshold by default at `-4r`; aggressive at any
    higher opt level).
  * The callee is called from at least one site that doesn't
    pass the call to another inline-eligible site.

When Watcom inlines, it processes the callee's IR with the
actual call-site argument types/values substituted.  But:

  * **Constant arguments don't fully fold inside the inlined
    IR.**  The inliner copies the IR body and then runs a
    limited pass to substitute constants.  Loop-induction
    variables that depend on a parameter—`xi < x0 + size`—
    are NOT re-derived with `size = 2`; the IR keeps `size`
    as a virtual register and emits the conditional `cmp xi,
    eax` form rather than `cmp xi, x0+2` (an `lea`‐fused
    immediate).
  * **The inlined body's local-variable stack slots
    interleave with the caller's locals.**  In the wrapper-
    version, the inliner allocates the helper's locals AND
    the wrapper's own (none) into one stack frame.  In the
    standalone version, locals are allocated cleanly by their
    declaration order, giving Watcom a predictable spill
    layout that matches PS (see Rule 24 / Rule 27 for the
    spill-slot mechanics).
  * **Inliner regalloc differs from non-inline regalloc.**
    Watcom's `bld/cg/c/inline.c` clones the IR but resets
    some allocator state; the resulting register choices
    (especially for tight-budget functions that already use
    all four `__watcall` reg args) don't match what the
    standalone-function path produces.  Cascades through the
    body via Rule 28 (push-set) and Rule 27 (spill order).

The net effect: three wrappers × ~150 b of cascaded
divergence each = ~450 b/function × 3 = ~1300 b of
byte-diff that disappears the moment you spell the bodies
out separately.

### How to detect

Look for all three:

  1. **Sibling function naming.**  `foo_x2`, `foo_x3`,
     `foo_x4`; or `test_a_X`, `test_b_X`, `test_c_X`; or
     `*_citymap_*` paired with `*_regionmap_*`.
  2. **Body ≥ 300 bytes** with 60-80% byte-diff against PS.
  3. **Debug line-number ranges** in the function-header
     comment (`// Lines NNNN-MMMM`) indicate ~50 lines per
     PS body.  A 5-line wrapper over a shared helper would
     show a 5-line range here.  PS's debug info preserves
     these ranges because Watcom's `-d1` emits SYM_FUNCTION
     records with start/end-line attributes per function.

### Fix

Inline the helper into each wrapper.  Replace the parameter
with a literal at every site within the inlined body:

  * `size` → `2` / `3` / `4`
  * `size - 1` → `1` / `2` / `3`
  * `(80 - size) * 20` → `(80 - 2) * 20` (Watcom will fold
    to the literal `0x618` / `0x604` / `0x5f0` at compile)
  * The size-specific data-pointer parameter (e.g.
    `diamond`) → the actual symbol
    (`diamond_ofsets_2x` / `_3x` / `_4x`)

Drop the now-unused helper entirely.  Don't leave it as dead
`static` code: Watcom's `-W3` warns on unused statics, and a
later editor may accidentally re-add a call to it.

The `put_x[234]_area` decomp also needed every supporting
fix that the helper-version had been masking:

  * `char base_kind` (not `int`) — PS uses only BL; declaring
    as `int` forces an extra push of EBX, cascading through
    the body.  See Rule 22 (stub signatures) and Rule 8/23
    (char signedness).
  * `int row_skip = (80 - 2) * 20;` declared FIRST so it gets
    the `[esp+0]` stack slot.  Rule 24 / Rule 27 territory.
  * `goto illegal` with the label nested **inside** the first
    bounds-check (`if (x0 < 0) { illegal: ... }`).  Subsequent
    `goto illegal` from later checks then branch backwards
    into this block.  Plain `goto illegal` after a tail
    label balloons by 250+ bytes (separate `mov; jmp` blocks
    per check, no shared illegal block).
  * `for (xi = x0; xi < x0+N; ) { ...; xi++; cm_sptr += 20; }`
    with empty for-update and increment in the body, so
    `inc edx` lands BEFORE `add eax, 0x14`.  See Rule 56
    (for-update emits after the body) for the converse case.
  * `(x0 + y0 * 80) * 20` instead of the `CM_OFF(x0, y0)`
    macro: CM_OFF expands `y * 80 + x` (y first), giving
    `lea edx, [eax + esi]`; PS wants `lea edx, [esi + eax]`
    which the `x + y*80` form produces.

### When NOT to apply

* The "helper" is genuinely shared by 5+ call sites with
  varied parameter values.  Watcom inlines small statics
  aggressively, but very-different-value callers produce
  per-site inlined bodies that don't suffer from the
  divergence (each site sees its own constants folded
  cleanly).
* The wrapper functions are tiny (< 50 bytes each) — those
  really were thin wrappers in PS source too.  Telltale:
  PS line-number range of 5–10 lines per wrapper.
* The shared logic genuinely uses runtime-variable
  parameters (not just `2`/`3`/`4` literals).  Inlining
  here would be wrong both for codegen and readability.

### Caveats

* The 19–21 b residue per function after inlining is the
  prologue spill-ordering divergence: PS does
  `mov esi, eax; mov ebp, edx` BEFORE the stack spills
  (`mov [esp+8], bl; mov [esp+4], ecx`); Watcom in our build
  emits the spills first.  No known source-level lever yet
  (Rule 27 toggle doesn't apply; the spill stores have no
  aliasing local name).  Document as a known Rule 61
  residue.
* Same-shape sibling families that ALL diff by 60-80% are
  the strong signal.  If only one of three siblings diffs
  heavily, Rule 61 is probably not the cause — look at
  the divergent function alone (likely Rule 27 / Rule 28
  regalloc-bias).

### Discovery

Discovery commit: `81727f1` — decomp(map): inline
put_x[234]_area as standalone, drop helper.

Found while triaging the largest-diff functions in `map.c`
(`uv run c2 progress --by-file` showed map.c holding 16% of
all remaining diff bytes).  The `put_x[234]_area` siblings
stood out as a 3-function cluster all with 80%+ diff, the
tell-tale signal that the source-structure choice (not a
per-instruction codegen pattern) was the root cause.

### Verified on

* `put_x2_area` (map.c) — 452 b → 19 b.  (size=2)
* `put_x3_area` (map.c) — 448 b → 21 b.  (size=3; one
  extra `int dir = map_direction;` line needed to trigger
  Watcom's CSE of the dir-2 comparison with the
  `x0 -= dir` subtraction value, both = 2.)
* `put_x4_area` (map.c) — 447 b → 19 b.  (size=4)

Total: ~1288 byte-diffs eliminated in one refactor.

### Candidates still to apply this rule to

In `map.c` (largest expected payoff first):

* `test_citymap_neighbours_posedge` /
  `test_citymap_neighbours_negedge` /
  `test_regionmap_neighbours_posedge` /
  `test_regionmap_neighbours_negedge` /
  `test_type_citymap_neighbours_posedge` /
  `test_type_regionmap_neighbours_posedge` /
  `test_type_citymap_neighbours_negedge` /
  `test_type_regionmap_neighbours_negedge`
  — 8 siblings, 700-948 b each, 78-82% diff. Likely
  factored over a shared `test_neighbours(grid, edge_dir,
  type_filter)` helper.
* `*_elastic_*` family
  (`build_road_from_elastic` / `build_reg_road_from_elastic`
  / `test_elastic_range` / `test_rm_elastic_range` /
  `set_route_elastic_range` / `transform_wall_elastic` /
  `transform_aquaduct_elastic` / `transform_reg_wall_elastic`
  / `trace_back_route_elastic`).
* `clear_an_area` / `clear_a_reg_area` /
  `clear_sized_to_rubble`.
* `one_aquaduct_ramification` / `one_wall_ramification` /
  `road_ramifications`.
* `put_reg_x2_area` (region-map sibling of `put_x[234]_area`).

Rough payoff estimate by family: ~5-8 kB of diff per family,
~15-25 kB total across map.c if all four families clean up
like the put_x* family did.

## Rule 62 — `x + x` lowers to `lea [x+x]`; `x * 2` / `2 * x` / `x << 1` lower to `mov; add`

### Pattern

PS source `return dir << 1` emits (3 b reg-reg `mov` + 2 b
`add reg, reg`):

```asm
89 d8           mov  eax, ebx
01 c0           add  eax, eax
```

PS source `return dir + dir` emits the LEA form (3 b):

```asm
8d 04 1b        lea  eax, [ebx + ebx]
```

The two forms differ by **1 byte**, which then cascades
through every short `jmp`/`jcc` target that hops over the
emitting block — easily producing 5–20 b of byte diffs from
a single 1-byte instruction-size shift (see Rule 16).

### Why

The split is by **AST node type**, not arithmetic value.  Only the
literal *addition* `x + x` is parsed as an add-expression that the
address-mode peephole can rewrite into `lea reg, [src + src]`.  Every
*multiply/shift* spelling of doubling — `x << 1`, `x * 2`, `2 * x` —
reaches codegen as a multiply/shift node, which Watcom lowers to
`mov reg, src; add reg, reg` (it knows `add reg, reg` is cheaper than
`shl reg, 1` on 486/Pentium, and does not fold it back into LEA).

Mnemonic: **`+` folds into `lea`; `*` and `<<` do not.**

### Measured (PS `get_attackers`, `mov eax,ebx; add eax,eax`, `--no-cache`)

| spelling | lowers to | matches PS `mov;add`? |
|---|---|---|
| `dir << 1` | `mov; add` | ✅ exact |
| `dir * 2`  | `mov; add` | ✅ exact |
| `2 * dir`  | `mov; add` | ✅ exact |
| `dir + dir`| `lea [x+x]` | ✗ 1 b diff |

The two forms differ by 1 byte (`mov;add` = 4 b vs `lea` = 3 b), which
cascades through every short `jmp`/`jcc` that hops the emitting block
(see Rule 16).

### How to detect

Diff row showing one side `lea reg, [src + src]` and the other side
`mov reg, src; add reg, reg` for a doubling.  Often paired with a
1-byte short-jump cascade (Rule 16 hints).

### Fix

* PS emits `lea [x+x]`  → write **`x + x`** (literal addition only).
* PS emits `mov; add`   → write **`x << 1`**, **`x * 2`**, or **`2 * x`**
  (any multiply/shift doubling).

Larger powers of two are symmetric — both spellings route through `shl`:

| C expression | Watcom emits |
|---|---|
| `x * 4`, `x << 2` | `shl x, 2` (verified `==` on `get_dos_memory`) |
| `x * 8`, `x << 3` | `shl x, 3` |

The `× 2` doubling is the only power-of-two with the `lea`-vs-`mov;add`
asymmetry.  (Odd multipliers `× 3`/`× 5`/`× 9` may use `lea` scale forms
but have not been measured here — verify against PS before assuming.)

The asymmetry only exists for the `× 2` doubling; larger powers of
two route through `shl` in both cases.

### Caveats

* If PS emits `lea` *and* the value's source register isn't
  about to be overwritten, the `mov reg, src` may be elided
  (the LEA form reads `src` directly).  Don't expect the
  exact 5-byte pair on every call site — sometimes `add eax,
  eax` alone is the diff.
* `x + 0` and `x + 1` don't follow this rule (the latter
  uses `inc`).
* The discovery case (`get_attackers`) was a `dir + dir`
  doubling pattern; the `<< 1` rewrite landed the function
  byte-exact (17 → 0 b).  No regression risk: `<< 1` and
  `+ x` are semantically identical for signed `int`, and
  callers see the same value either way.

### Discovery

`get_attackers` (bbarian.c, 0x534FD).  17 b diff dominated
by a `je 0xN` cascade — root cause was a single 1-byte size
mismatch from PS `mov eax, ebx; add eax, eax` vs RC
`lea eax, [ebx + ebx]` at the function tail.  Rewriting
`return dir + dir` as `return dir << 1` flipped the
function to byte-exact.  Committed in 012116d.

### Verified on

* `get_attackers` (decomp/src/bbarian.c) — `<< 1`, `* 2`, `2 * dir` all
  byte-exact (`mov;add`); `dir + dir` diffs (`lea`).  Source normalized to
  `dir * 2` (house multiply style; see `docs/observed-source-style.md`).
* `get_dos_memory` (decomp/src/lib32.c) — `<< 2` == `* 4` (both `shl`).

### Candidates still to apply this rule to

Any function with a 1-byte size shift at a `* 2` / `+ x`
site that the rule-hint detector currently flags as Rule 16
(short-vs-near jmp cascade).  When the cascade traces back
to a single LEA-vs-add divergence, swap the source for
`<< 1` and re-verify.

Note: this rule is the inverse of the more common
"prefer LEA for cheap arithmetic" advice — Watcom's codegen
makes both forms reachable depending on how the C source
spells the expression, so the recompiler has to match the
original author's spelling rather than picking the shorter
form.

## Rule 63 — Cached row pointer vs repeated indexed global field access

### Symptom

PS repeatedly computes `index * stride` and folds the global base plus
field offset into each memory operand:

```asm
movsx eax, word ptr [figure_no]
imul  eax, eax, 0x58
mov   byte ptr [eax + figure_list+0x3], dl
...
movsx eax, word ptr [figure_no]
imul  eax, eax, 0x58
movsx edx, byte ptr [eax + figure_list+0x6]
```

The obvious C source caches a row pointer:

```c
struct figure_rec *f = &figure_list[figure_no];
f->sprite_dir = 0;
dir = f->direction;
```

Watcom 10.0a then materializes the row base in a callee-save register
(or an added pointer local) and emits `[reg + field]` accesses.  That
changes the prologue push set and cascades through the whole function.

### Cause

A named pointer local gives the register allocator a long-lived value
that is profitable to keep in a callee-save register.  PS source in many
entity-list hot paths appears to have spelled field accesses as repeated
indexed expressions (or macro-expanded byte offsets), so Watcom keeps the
index multiply near each access instead of preserving a row pointer.

This is especially common for fixed-stride global arrays:

* `figure_list[figure_no]` / `figure_no * 0x58`
* `arrow_list[arrow_no]` / `arrow_no * 0x26` or raw 45-byte accessors
* `unit_list[unit_idx]` / `unit_idx * 0x4e`
* `army_list[...]`
* map cell arrays when a cell pointer is cached only for convenience

### Fix

Replace the cached row pointer with explicit offset macros or direct
indexed field accesses.  For byte-oriented decompiled code, local macros
are the least invasive form:

```c
#define FIG_B(n)  (((unsigned char *)figure_list)[figure_no * 0x58 + (n)])
#define FIG_SB(n) ((signed char)FIG_B(n))
#define FIG_I(n)  (*(int *)((unsigned char *)figure_list + figure_no * 0x58 + (n)))

FIG_B(0x3) = 0;
dir = FIG_SB(0x6);
FIG_B(0x2) = (char)frame;

#undef FIG_B
#undef FIG_SB
#undef FIG_I
```

Do **not** apply blindly.  If PS caches the row base in a register, keep
the pointer local.  This rule applies when disassembly shows repeated
`imul index, stride` plus `[index + global+field]` memory operands and
RC shows a cached row pointer (`add reg, global_base`, `[reg+field]`) or
extra callee-save pressure.

### Tooling

Use the AST-backed candidate scanner:

```bash
uv run c2 row-caches --limit 50
uv run c2 row-caches decomp/src/battle.c --array figure_list
```

It walks pycparser `FuncDef` / `Decl` / `Assignment` nodes and ranks
cached row-pointer expressions such as `&figure_list[i]` and
`(char *)figure_list + i * 0x58` by use count and assignment-site count.
Treat the output as a triage list; confirm each candidate against
`c2 disasm` / `decomp-verify -v` before rewriting.

### Discovery

First isolated in `fly_to_target`, where removing a cached
`arrow_list[arrow_no]` row pointer reduced the function by 46 diff bytes.
The same pattern then improved a cluster of battle figure functions:

* `get_fig_tortoise_image`: 198 → 50 diff bytes (-148)
* `test_for_same_fig_to`: 174 → 55 (-119)
* `get_fig_walk_image`: 284 → 199 (-85)
* `get_fig_still_image`: 182 → 115 (-67)
* `move_figure`: 225 → 192 (-33)
* `get_fig_missile_image`: 256 → 241 (-15)
* `get_fig_fight_image`: 352 → 340 (-12)

### Verified on

* `fly_to_target` (decomp/src/battle.c)
* `move_figure` / `backtrack_figure` (decomp/src/battle.c)
* `get_fig_walk_image`, `get_fig_still_image`,
  `get_fig_tortoise_image`, `get_fig_missile_image`,
  `get_fig_fight_image` (decomp/src/battle.c)
* `test_for_same_fig_to` (decomp/src/battle.c)

### Caveats

* Long functions with many assignments to the same row pointer may need a
  partial refactor; wholesale macro expansion can change unrelated
  register allocation.
* `struct` field syntax and byte-offset macros are not interchangeable
  for signedness.  Preserve PS's `movsx` vs zero-extension behaviour by
  using `signed char` (`FIG_SB`) only where PS sign-extends.
* The rule often exposes remaining Rule 28/28b push-set differences.
  Once the row-pointer cache is gone, remaining diffs may be pure
  regalloc/tail-merge noise rather than another source-level pointer bug.

## Rule 64 — Mutate an index parameter to keep the original value in EBX

### Symptom

A table-entry loader computes `n * stride`, reads several adjacent fields,
and later still needs the original unscaled `n` for a threshold adjustment.
PS keeps the original parameter in `ebx`, mutates `eax` into the scaled table
index, and uses `edx` for the repeated zero-extended word loads:

```asm
push ebx
push ecx
push edx
mov  ebx, eax          ; keep original n
shl  eax, 4            ; mutate n into byte/word table offset
xor  ecx, ecx
mov  cx, [eax+table+0xc]
xor  edx, edx
mov  dx, [eax+table+0xe]
shl  edx, 16
add  ecx, edx
...
cmp  ebx, 4            ; original n still live
jl   done
lea  ebx, [eax+0xc8]
mov  [sprite_y], ebx
```

The obvious C source repeats `n * stride` in every subscript and/or copies
`n` to a neutral `saved_n` local:

```c
int saved_n = n;
offset = header[n * 8 + 6];
offset += header[n * 8 + 7] << 16;
...
sprite_y = header[n * 8 + 9];
if (saved_n >= 4) sprite_y += 0xc8;
```

Watcom then tends to keep the original `n` in `edx`, use `ebx` for the
zero-extended field temporaries, and (depending on source shape) may spill an
extra callee-save register for the post-load adjustment.

### Cause

The C front end preserves the source expression shape into `CGBinary`:
`treewalk.c` / `cgen2.c` linearize the expression tree, `bldins.c` passes
operand order through to `MakeBinary`, and `makeins.c` records it unchanged.
The register allocator (`regalloc.c` `GiveBestReg`) then scores conflicts via
`CountRegMoves` and breaks remaining choices through the target register lists
in `386rgtbl.c`.

Writing every access as `n * 8 + field` creates a long-lived original-`n`
conflict plus repeated short-lived multiply/index temporaries.  Mutating the
parameter itself (`n *= 8`) gives Watcom exactly the PS-shaped live ranges:
original `n` is copied once for the later compare, while `eax` becomes the
scaled table index reused by all field loads.

### Fix

When PS shows `mov ebx, eax; shl eax, K` at the top of a table-entry loader,
spell the source as a parameter mutation plus a saved original:

```c
void draw_battle_part(int n)
{
    int saved_n = n;
    int offset;

    n *= 8;
    offset = (unsigned short)int_battle_header[n + 6];
    offset += ((unsigned short)int_battle_header[n + 7]) << 16;
    sprite_start  = 0;
    sprite_width  = (unsigned short)int_battle_header[n + 4];
    sprite_height = (unsigned short)int_battle_header[n + 5];
    sprite_x      = (unsigned short)int_battle_header[n + 8];
    sprite_y      = (unsigned short)int_battle_header[n + 9];
    if (saved_n >= 4) sprite_y += 0xc8;
    ...
}
```

Do not apply just because a function has `n * stride` subscripts.  This rule is
for the specific PS shape where the parameter is copied before scaling and the
scaled value is then reused for a compact run of adjacent table fields.

### Discovery

`draw_battle_part` (display.c, 0x5AD8D).  A dedicated cgex experiment
(`docs/codegen-experiments/display-draw-battle-part.py`) compared repeated
`n * 8`, a named base-index local, staged `sprite_y` variants, and parameter
mutation.  Only the `n *= 8` form reproduced PS byte-for-byte:

```text
current                    68 diff bytes in isolated cgex
ps-order-y-store-before-if 108
base-index-local           108
param-mutate                 0
```

In the full TU this flipped `draw_battle_part` from 108 diff bytes to exact.

### Verified on

* `draw_battle_part` (decomp/src/display.c)

---

## Rule 65 — `GiveBestReg` sort-instability residuals (known irreducible)

### Pattern

A function compiles to the **right size**, with the **right callee-save
push set**, the **right instruction list** — but **one or two adjacent
register choices** differ between PS and recomp.  Typical shapes:

```
;; show_lbm @ +0x16, +0x46
PS: 89 c1   mov ecx, eax   …   85 c9   test ecx, ecx
RC: 89 c2   mov edx, eax   …   85 d2   test edx, edx   ← 2 bytes diff
```

```
;; restore_picture_part @ width/x compute
PS: 03 d1   add edx, ecx   …   89 15 [m]   mov [m], edx
RC: 03 ca   add ecx, edx   …   89 0d [m]   mov [m], ecx   ← 4 bytes diff
```

The diff is **a single register pair flip** (ECX↔EDX, or one ADD direction
flip with a matching store source).  Function size, push set, branch
layout, fixup count — everything else matches.

### What it is

Pure register-allocation tie-break in `GiveBestReg`
(`bld/cg/c/regalloc.c:784`).  When two candidate registers tie on
`CountRegMoves` savings, the winner depends on:

1. Iteration order through `tree->regs` (= `DoubleRegs[]` =
   **EAX, EDX, EBX, ECX, ESI, EDI, EBP** for 32-bit ints, EBX before
   ECX, va 0x821A8).  Earliest non-excluded reg wins by default →
   for a clean tie EDX beats EBX beats ECX.
2. The `conf->with.regs` exclusion set built by `NeighboursUse()`.
3. Which conflict gets first pick: descending `CountRegMoves`/savings,
   and **equal savings break by first-use order** (the value first used
   in the instruction stream gets the higher-priority reg).  This is
   the actionable Rule 28a lever — see Rule 28a and
   `watcom10.0a repo docs/wcc386-re/regalloc-model.md`.

Conflicts are processed in descending-savings order; **equal-savings
conflicts are ordered by FIRST-USE position** — the value whose first
use comes earlier in the instruction stream gets the higher-priority
register (proven in `regalloc-tiebreak.py`, corpus-validated by
`change_citizen_targs`).

### The lever: first-use order (and why flags don't help)

Reorder which of the two competing values is used first — commute an
operand, move a statement — and the registers follow.  When the
competing values are CSE-hoisted globals accessed in a fixed
algorithmic order, the first use can't be moved, so the row stays as
residue.  Compiler flags and versions never fix a tie-break (only
source order does), verified by exhaustive negative testing:

| Lever class            | Variants tested | Effect on the tied bytes |
|------------------------|-----------------|--------------------------|
| Compiler version       | 9 (10.0LA → 11.0c) | none — same diff in all |
| Optimization flags     | 25+ combos (`-ol`, `-or`, `-oe`, `-oi`, `-ot`, `-os`, `-od`, `-of`, `-on`, `-op`, `-ou`, `-ox`, `-oxat`, `-oh`, `-ob`, `-ok`, `-oc`, …) | flips the residual *up* (worse), never to 0 |
| Calling-conv flags     | `-3r`, `-4r`, `-5r`, `-ri` | none |
| Memory model           | `-mf`, `-ms` | none |
| Segment / output       | `-zc`, `-zg`, `-zm`, `-zdl`, `-zff`, `-zk0`, `-zp1/2/4` | none |
| FP flags               | `-fpc`, `-fpi`, `-fpi87`, `-fp2/3/5`, `-7` | none |
| Source restructure     | compound-`if`, `else if`, `goto`, two-tests-nested, flush-then-test, nonzero-first, oversized-branch-tail, block-scope, named locals before/after `rc`, second-int alias, `volatile`, `static` global, register-hint, `(int)`/`(long)`/`NULL` zero spellings, `+` vs `\|` order | none (only WORSE) |
| `#pragma aux` on subject | `parm [eax]`, `modify exact [eax]`, `modify exact []`, `modify [eax]`, custom save set | none |
| `#pragma aux` on callees | readfile / printf / no_high_beeps / stop_system / convert_lbm_file with various `modify exact [...]` lists, `aborts`, etc. | none |

The 4-byte diff on `restore_picture_part` is the same class:
two values computed via `(p[hi]<<8) + p[lo]`; the ADD-result
register flip determines which side becomes the store source.  No
source-level form — `p[lo] + (p[hi]<<8)`, `|` instead of `+`, `+=`,
`(unsigned short)` casts, named hi/lo locals, two-step shifts —
flips the chosen register.

### What to do

* **Stop chasing** these once you've confirmed via cgex that the
  size matches and only register identity differs.  No source you
  can write will close them.
* **Document** them in the file's progress notes as "Rule 65
  residual: N bytes" so the next session doesn't burn time on them.
* **Don't regress** them — keep an eye on the diff count in
  `c2 progress --verify` for the function; if it grows past the
  known residual you've introduced a real bug.
* **Watch for** the same shape elsewhere: a sub-10-byte diff
  that's all register-identity flips (ECX↔EDX, ESI↔EDI swaps that
  AREN'T full Rule 28 sweeps) on an otherwise size-matched
  function is almost certainly Rule 65.

### Why "irreducible"

The register assignment follows **first-use order** (Rule 28a): the
value whose first use comes earlier gets the higher-priority
register.  Recovering the exact bytes means making the source's
first-use order match PS — reorder which competing value is used
first (commute an operand, move a statement).  Where the competing
values are CSE-hoisted globals accessed in a fixed algorithmic order,
the first use can't be moved, so the row stays as residue.

### Currently known residuals

| Function (file)                    | bytes | shape |
|------------------------------------|------:|-------|
| `restore_picture_part` (display.c) |   4   | width/x ADD direction (EDX vs ECX as result) |
| ~~`show_lbm` (display.c)~~         |  0    | **byte-exact via prior fix** |
| ~~`clear_city_flag` (map.c)~~      |  0    | **fixed by Rule 66** — see below |
| ~~`clear_prov_flag` (map.c)~~      |  0    | **fixed by Rule 66** — see below |
| ~~`put_new_node` (web.c)~~         |  0    | **fixed by Rule 67** — see below |
| ~~`set_ai_unit_move` (battle.c)~~  |  0    | **fixed by Rule 67** — see below (parm variant) |
| ~~`entering_new_square` (int_c2.c)~~ |  -1 | partial close via Rule 4 (3b → 2b, trade-off) |
| `start_smacking` (smacker.c)       |  11   | `mov reg, [global]; push reg` scratch-reg choice for 3 args to SMACKTOBUFFER / SMACKTOSCREEN + palette `add esi` vs `lea eax` |
| `control_icons` (controls.c)       |   2   | ESI↔EBX pure swap (Rule 28a-style) |
| `do_the_fight` (battle.c)          |   3   | AL vs BH scratch byte-reg choice |
| `barbarian_in_region` (bbarian.c)  |   3   | EAX vs EDX scaled-index choice for `army_list[created_army_no].field` |
| `empire_in_region` (bbarian.c)     |   3   | same shape as `barbarian_in_region` |
| `barbarians_drop_by_city` (bbarian.c) | 3  | same shape as `barbarian_in_region` |
| `check_for_Trident` (lib32.c)      |   2   | EBX vs ECX scratch-reg choice for `mov reg, 0x7bf` constant load |
| `cd_path` (lib32.c)                |   6   | EBX vs ECX scratch choice cascades through whole function |

### Cases that LOOK like Rule 65 but are actually layout cascades

These have small byte diffs but root-cause is **Rule 16 (short-vs-near jmp encoding)** or **Rule 42 (cross-function tail-merge)**, NOT pure regalloc tie-break.  Listed here so they don't get re-triaged as Rule 65:

| Function | shape |
|----------|-------|
| `act_help_icons` (action.c) | Rule 16 — `eb 96` (short) vs `e9 70 ...` (near) |
| `act_detailed_query` (action.c) | Rule 42 — tail-merge to `act_people_query+0x2A` |
| `get_aquaduct_elastic` (map.c) | Rule 42 — tail-merge to `get_wall_elastic+0x4D` |
| `put_danger_flag` (map.c) | Rule 15 — `return 1` tail-merged with sibling helper |
| `show_ov_legend_panel` (screens.c) | Rule 42 — tail-merge to `show_final_bribe_box+0x17F` |
| `show_this_tribune` (screens.c) | Rule 42 — tail-merge to `basic_temple_screen+0x648` |
| `show_year_end_screen` (screens.c) | Rule 42 — tail-merge to `basic_temple_screen+0x647` |
| `xor_a_diamond_lhs_top` (lib32.c) | Rule 15/42 — epilogue shared with siblings |
| `xor_a_diamond_rhs_top` (lib32.c) | Rule 42 — tail-merge into `xor_a_diamond_lhs_top+0x4F` |
| `set_rm_range` (map.c) | Rule 42 — epilogue shared with adjacent range setters |
| `fight_barbarian` (int_c2.c) | Rule 15 — tail-merge shares `xp += 1` epilogue with `fight_centurian` |
| `change_citizen_targs` (int_c2.c) | Rule 42 — tail-merge to `test_zone_for_closest_fire+0x191` |
| `sa16_army_lurk_round_coast` (int_c2.c) | Dead-byte interpretation; function ends earlier in RC |
| `try_this_battlemap_square` (battle.c) | Dead-byte interpretation; function ends earlier in RC |

This is now a **confirmed pattern** with > 3 examples.  The common
thread: the diff is **purely register-identity flips** on a
size-matched function with the same instruction list and the same
callee-save push set.

The **root cause** is the LIFO + sort-stability interaction in
`AddConflictNode` + `SortConflicts`:

```c
// bld/cg/c/conflict.c:67 (1.1 src; identical in OWv1 initial commit)
new->next_conflict = ConfList;   // PREPEND to list
ConfList = new;

// bld/cg/c/regalloc.c:1122
static bool ConfBefore(void *c1, void *c2) {
    return ((conflict_node *)c1)->savings > ((conflict_node *)c2)->savings;
}
```

Among equal-savings conflicts (parm vs short-lived local with
similar use counts), the LAST one created during `BuildConflicts`
ends up at the **HEAD** of `ConfList` and gets the first pick from
the candidate register list.

For parms, the conflict is created at the implicit parm-move at
function entry (`mov temp_parm, eax`) which is the FIRST
instruction.  For locals like `cur` or `pal_ptr`, the conflict is
created at first use in the body.  Conclusion: **parms always lose
the equal-savings tie-break** unless the savings calculation tilts
in their favour.

There is no source-level lever to defer the parm-move past the
body's first-use instruction — Watcom emits the parm-move at IR
generation before any optimisation pass that could move it.

### Discovery

`show_lbm` (2 b) and `restore_picture_part` (4 b) in
`decomp/src/display.c`.  Investigation chain:
`docs/codegen-experiments/display-show-lbm.py` and
`docs/codegen-experiments/display-restore-picture-part.py` —
combined ~50 source trials — followed by:

* `/tmp/show_lbm_versions.py` — all 9 Watcom versions give the
  identical 2-byte diff (codegen is deterministic across patches).
* `/tmp/show_lbm_flags.py`, `/tmp/show_lbm_flags2.py`,
  `/tmp/rpp_flags.py` — 50+ flag combinations, none flip the
  residual to 0.
* `/tmp/show_lbm_aux.py`, `/tmp/show_lbm_callee_pragma.py` —
  `#pragma aux` modifications on both `show_lbm` and its callees,
  none reach 0.

Source walk through Watcom `regalloc.c` (`GiveBestReg`,
`CountRegMoves`), `regsave.c` (`_ReplaceOpnd` / `_ReplaceResult`
savings model), and `sortlist.c` (`ShellSort`, `DoSortList`)
identified `SortList` instability over conflict-priority ties as
the only remaining degree of freedom — and one we cannot observe
or control from outside the compiler.

### Subclass that DOES have a lever: see Rule 66

Before filing a residual under Rule 65, check whether one of the
conflicting variables is used as an **array index inside a branch
where it equals a parm**.  If so, you can transfer the
`_ReplaceIdxOpnd` `index_save` bonus from the local to the parm
by rewriting the indexed access to use the parm directly — see
Rule 66.  This closes `clear_city_flag` / `clear_prov_flag` and
any sibling whose source has the same `if (local == parm)` /
`array[local + N]` shape.


## Rule 66 — Transfer `index_save` to flip parm-vs-local register tie-break

### Pattern

A function with a parm and a loop-local where:

* The parm and the local hold **the same value inside a branch** (e.g. a `if (local == parm)` gate).
* The local is used as an **array index** inside that branch (`array[local + N]`).
* The compare itself uses the loaded value as the LHS (`if (city_flag_list[i] == val)`).
* The diff is a Rule 28-style **EBX↔ECX swap** — PS keeps the parm in EBX (first `DoubleParmRegs` candidate after EAX/EDX), our build does the opposite.

### Reason

Inside `bld/cg/h/savcode.h`, the macro `_ReplaceIdxOpnd` adds `Save.index_save` to whichever variable is used as the index of an `N_INDEXED` operand. That bonus is on top of the regular `use_save` you get from a plain register read.

For a function like

```c
void clear_city_flag(int val) {
    int cur, i;
    for (i = 0; i < 0x14; i++) {
        cur = city_flag_list[i];
        if (cur == val) {
            city_flag_list[i] = -1;
            city_map[cur + 2] = 0;   /* ← cur is the INDEX */
        }
    }
    count_city_flags();
}
```

`cur`'s savings include `def_save + use_save (cmp) + index_save (city_map[cur+2])`.  `val`'s savings include only `def_save (parm-move) + use_save (cmp)`.  Result: `cur > val`, so cur lands at the head of `ConfList` after `SortConflicts`, picks first from `DoubleRegs` (= EBX after EAX/EDX/ECX exclusions), and val falls to ECX.

PS shipped the binary with the OPPOSITE choice (val in EBX, cur in ECX) — meaning PS's savings calculation had val > cur.  The way to get there is to **move the index role onto the parm**: inside the branch `cur == val` is true, so `city_map[cur + 2]` and `city_map[val + 2]` are semantically identical.  Rewriting the branch as

```c
city_map[val + 2] = 0;
```

transfers `index_save` from `cur` to `val`.  At that point `val` no longer has any other use that requires it to live in a register; cur drops out entirely and you can simplify away the local:

```c
void clear_city_flag(int val) {
    int i;
    for (i = 0; i < 0x14; i++) {
        if (city_flag_list[i] == val) {       /* compare loaded value first (Rule 4) */
            city_flag_list[i] = -1;
            city_map[val + 2] = 0;             /* index by val to give it index_save */
        }
    }
    count_city_flags();
}
```

This is byte-exact against PS.  Same recipe worked on `clear_prov_flag` (mirror function with `RM_PLACE_STATE(val)` instead).

### When to apply

This pattern resolves Rule 65 residuals where:

1. The two conflicting variables are **provably equal inside the branch** that uses one of them as an index.
2. The local being eliminated has **no other use** outside the branch (or its other uses can also be rewritten via the parm).
3. The diff is exactly the EBX↔ECX swap that Rule 65 documents.

### When NOT to apply

* If the local has **uses outside the gating branch** — replacing them with the parm changes semantics.
* If the compare gates on something weaker than strict equality (`>=`, `!=`, etc.) — the values aren't necessarily equal in the branch.
* If the index expression is **structurally different** from the parm's value (e.g. `cur + offset_depending_on_something`) — splitting that requires more thought.

### Discovery

`clear_city_flag` and `clear_prov_flag` in `decomp/src/map.c` (2 b each, originally listed in Rule 65's table).  Found by reading the `_ReplaceIdxOpnd` macro in `bld/cg/h/savcode.h` (from the open-watcom-v1 initial-commit source tree) after exhausting the Rule 65 catalogue of "no known lever".

The `index_save` constant lives in `Save.index_save` (loaded per-target in `bld/cg/intel/c/i86proc.c`) and on the 386 target is roughly equivalent to a load_cost — substantial enough to dominate the parm's modest def_save advantage.

### Cross-reference

* Rule 4 — compare operand order (write `loaded_value == parm`, not the reverse, so `cmp [global], val_reg` is emitted as one instruction).
* Rule 65 — sort-instability residual catalogue; entries that match this recipe should be moved out of Rule 65 once fixed.
* `decomp/src/map.c::clear_city_flag` and `::clear_prov_flag` — the canonical fixed examples.

## Rule 68 — 2D-array cast triggers SIB-form `[base+index+disp32]` store

> **IMPORTANT — UPDATED 2026-05-24**: the original draft of this rule
> documented a `row-pointer` lever (`char *row = arr + STRIDE*idx`).
> That lever DOES produce SIB form but with **CL_POINTER + offset** (no
> disp32), forcing the array base into a register and adding an extra
> callee-save push.  The correct lever — verified byte-identical to PS —
> is **declaring or casting the array as 2D** (`char (*)[N][M]`), which
> drives `addrfold.c` into the CL_GLOBAL_INDEX path and keeps the
> array base as the displacement.  See the cgex receipts below.

### Pattern

When PS emits a `[reg + reg + disp32]` SIB-form store but our recompile
emits the flat `[reg + disp32]` form (after an explicit `add reg, reg`),
the source-level lever is to declare/cast the array as **2D**:

```asm
; PS:
89 c2       mov edx, eax       ; t = ref_y
c1 e0 02    shl eax, 2         ; eax = 4y
01 c2       add edx, eax       ; ← edx = 5y (RESULT IN EDX)
c1 e2 03    shl edx, 3         ; edx = 40y
a1 ?? ?? ?? ??  mov eax, [ref_x]
b3 02       mov bl, 2
88 9c 02 ?? ?? ?? ??   mov [edx+eax+disp], bl    ; ← SIB store

; Plain `tab[STRIDE*idx + col]` source produces:
89 c2       mov edx, eax       ; same start
c1 e0 02    shl eax, 2
01 d0       add eax, edx       ; ← eax = 5y (RESULT IN EAX) — backwards
c1 e0 03    shl eax, 3
8b 3d ?? ?? ?? ??  mov edi, [ref_x]   ; needs callee-save cache
01 f8       add eax, edi       ; explicit fold
b2 02       mov dl, 2
88 90 ?? ?? ?? ??   mov [eax+disp], dl       ; ← flat store
```

### Source-level lever

Two equivalent forms work:

**(a)** Declare locally as 2D:
```c
extern char tab[ROWS][COLS];     // local extern, MUST be 2D
tab[ry][rx] = val;
tab[ry][rx + 1] = val;
```

**(b)** Cast at each access (when conflicting with a file-scope `char[]`
declaration in a shared header — the most common case for us):
```c
#define TAB2D (*(char (*)[ROWS][COLS])tab)   // global header has `char tab[]`
TAB2D[ry][rx] = val;
TAB2D[ry][rx + 1] = val;
```

**Caveat — DO NOT store the cast in a local pointer**:
```c
char (*t)[COLS] = (char (*)[COLS])tab;   // BAD — produces flat
t[ry][rx] = val;                          // CL_POINTER, not CL_GLOBAL_INDEX
```
This stores the array as a pointer (`CL_POINTER`) and the address-fold
falls back to flat-form `[eax+disp]` with the array base in a register —
same as the natural 1D form, plus an extra callee-save push for the
pointer cache.

### Why this works — `addrfold.c` AddTable

Watcom's `bld/cg/c/addrfold.c` `CypAddrPlus` walks an `AddTable[r][l]`
state machine to decide whether an `expr + expr` can be folded into a
`base + index + offset` address triple (which lowers to SIB form), or
whether it must spill to an explicit ADD instruction (flat form).

For the **1D-array form** `tab[STRIDE*idx + col]`:
- `tab` builds as `&g+C` (CL_ADDR_GLOBAL, class index 0).
- `STRIDE*idx + col` reduces to two I4 temps.
- AddTable[I4][&g+C] = `TEMP_R` → `LoadTempInt` converts `&g+C` to
  `TI4+C` (class 5).
- AddTable[TI4+C][&g+C] = `UNEXPECTED` → returns NULL → emit explicit
  ADD instruction → **flat addressing** `[reg + disp32]`.

For the **row-pointer form** `(tab + STRIDE*idx)[col]`:
- `tab + STRIDE*idx` resolves to CL_POINTER (class 4, the row pointer).
- AddTable[I4][CL_POINTER] hits `ADD_RI` → SIB form, BUT the array base
  is folded INTO the pointer register, not the disp.  Result:
  `[reg+reg]` (no disp32) — requires the row-pointer cache in a
  callee-save register and adds an extra prologue push.  Different
  shape from PS.

For the **2D-array form** `tab[ry][rx]` (or 2D-cast `(*(char(*)[R][C])
tab)[ry][rx]`):
- `tab` builds as `&g+C[I]` (CL_GLOBAL_INDEX with computed row-scale
  index, class index 1).
- Inner index `ry` reduces to I4.
- AddTable[I4][&g+C[I]] = `ADD_RI` → folds `ry` as the SIB index with
  scale=COLS implicit in the row-stride math.
- Outer `[rx]` adds rx as the base, keeping the array address as
  disp32.  Result: `[base + index + disp32]` SIB — **exactly the PS
  form**.

The cascade:
- SIB form keeps the multiplication-result and the index in **distinct
  registers** → strength-reduction accumulator picks EDX (matching
  PS's `add edx, eax`).
- The base-disp32 stays in the addressing displacement, so no
  callee-save register is needed for the array base.
- The freed register budget lets a second-half access (e.g. `if (ry <
  29) ...`) re-use the value via the EBP callee-save instead of EDI
  (matches PS's `push ebp`).

### Receipts — cgex `sib-vs-flat-probe.py`

Three source forms compiled with `-bt=dos -mf -4r -s`, all writing to
the same `svga_refresh_table` cells:

| Form | size | `add edx,eax` | SIB | push ebp | push edi |
|------|-----:|:-:|:-:|:-:|:-:|
| Natural 1D `tab[40*ry + rx]`                   | 261 | ✗ | ✗ | ✗ | ✓ extra |
| Row pointer `char *row = tab + 40*ry; row[rx]` | 237 | ✓ | partial (no disp32) | ✓ | ✓ extra |
| 2D cast `(*(char(*)[30][40])tab)[ry][rx]`      | 262 | ✓ | ✓ (with disp32) | ✓ | ✗ |
| PS.EXE reference                               | 259 | ✓ | ✓ | ✓ | ✗ |

The 2D cast matches PS prologue (`push ebx; push ecx; push edx; push
ebp`) and SIB store form (`88 9c 02 ?? ?? ?? ??  mov [edx+eax+disp32],
bl`) byte-identically.

### Applying — coexisting with a flat header declaration

c2_data.h declares `extern char svga_refresh_table[];` for the 109
sites across refresh.c + controls.c that index it flat (`tab[i]`,
`tab[rx + ry * 40]`).  Adding a 2D declaration there would break
those.

Instead, use a **function-local cast macro**:

```c
#define SVGA_REFRESH_2D (*(char (*)[30][40])svga_refresh_table)

void set_mouse_refresh(void) {
    ...
    SVGA_REFRESH_2D[ref_y][ref_x] = 2;
    ...
}
```

The macro expansion at each call site rebinds the cast type fresh,
keeping the addrfold path through CL_GLOBAL_INDEX.  A local
`char(*)[40]` pointer alias would NOT work (collapses to CL_POINTER).

### Tooling

The `c2 permute --only row_pointer` mutator was the original
discovery vehicle but its output produces the *wrong* form (CL_POINTER,
not CL_GLOBAL_INDEX).  Use the 2D-cast macro pattern by hand for now.
A future mutator `2d_array_cast` could enumerate candidates by finding
flat `arr[ROWS_CONST * idx + col]` patterns and rewriting to
`(*(char(*)[ROWS][COLS])arr)[idx][col]`.

### Discovery and receipts

`set_mouse_refresh` in `decomp/src/refresh.c` (now **byte-exact**):
- Cross-version Watcom bisection (9.01d through 11.0c) ruled out
  compiler-version drift as the cause of the original SIB-vs-flat
  divergence.
- The row-pointer mutator regressed in-TU (44 → 191 b); deep-asm
  comparison proved this was NOT TU-state-dependent: isolated cgex
  and real-TU produce byte-identical asm.  The row-pointer form just
  doesn't match PS's shape.
- 2D-cast macro applied: **44 b → 21 b** (−23 b).  The final 21 b — the
  2×2 corner store — was then closed with the Rule 66 SIB-scale-8 form
  `(&svga_refresh_table[ref_x])[(ref_y+1)*40+1] = 2;` (see the Rule 66
  "Won `set_mouse_refresh`" note), reaching byte-exact.

## Rule 69 — inline byte-field compare chains to keep direct byte-register tests

### Pattern

When PS compares the same byte-sized struct/global field against several
constants, it may keep the containing address/base live and reload/test the
field directly for the first comparison:

```asm
mov dl, byte ptr [eax + field]
test dl, dl
jne ...
mov al, dl
and eax, 0xff
cmp eax, 1
...
```

The tempting C shape caches the byte field in a local:

```c
unsigned char order;
order = army_list[idx].cohort_size_class;
if (order == 0) ...
else if (order == 1) ...
else if (order == 2) ...
```

Watcom then commonly chooses AL for the local cache:

```asm
mov al, byte ptr [eax + field]
test al, al
...
and eax, 0xff
```

That is semantically identical but can leave 50–120 bytes of register/layout
cascade in functions with shared call tails.

### Source shape that matches PS

Do not introduce the byte local.  Compare the field expression directly at each
branch:

```c
if (army_list[idx].cohort_size_class == 0) ...
else if (army_list[idx].cohort_size_class == 1) ...
else if (army_list[idx].cohort_size_class == 2) ...
```

Despite the repeated source expression, Watcom keeps the scaled base/address
available and emits the PS-shaped direct byte-register tests.

### Discovery

`show_cohort_box` and `show_recruitment` in `decomp/src/screens.c`:
removing a cached `unsigned char order` local and inlining
`army_list[...].cohort_size_class` into the compare chain made both functions
byte-exact.

### Tooling

`c2 permute --only inline_byte_cmp <function>` now probes this pattern by
removing a cached `char`/`unsigned char` local assigned from a field/array
expression and inlining that expression into the following compare chain.

## Rule 70 — Prologue divergence: pragma directives + source-level levers

### What we observed

`push_node_value` (web.c, 442 b) verified with a residual that wouldn't
shrink below ~190 b of regalloc cascade no matter what C source we
threw at it.  PS pushed **EBX, ECX, EDX, ESI** in the prologue;
recomp's __watcall pushed only EBX/ECX/EDX (ESI missing).  Pressure
landed in DH instead of CL, building stayed as a CL byte-temp rather
than being routed CH → ESI via movzx, and the cascade through the
`(cm & 2)` check + the `web_directions` XOR added the rest of the 190
byte residue.

### The actual cause (web.c case)

For `push_node_value` specifically, **no pragma was needed** — the fix
was purely source-shape:

  1. **`int building`, not `unsigned char building`** — building's
     int promotion (zero-extend after the byte AND) creates a separate
     int-typed conflict that Watcom enregisters in ESI via the
     `mov ch, [..]; and ch, 0x80; movzx esi, ch` pattern.  With
     `unsigned char building`, the value stays in CL as a byte temp,
     ESI is never claimed, and the rest of the regalloc shifts to
     compensate.
  2. **`else if (mask >= 1)`, not `if (mask >= 1)`** — the `cm[+4]`
     mutation in the `(cm[+1] & 2) == 0` block: PS emits a `jmp` after
     the `mask==3 ? cm+=2` branch, skipping the `mask>=1 ? cm++` check.
     The without-`else` form (`if; if`) would incorrectly add `+3`
     for mask==3 instead of PS's `+2`, *and* compile to a different
     branch shape.

Both together close the diff to byte-exact.

### When a pragma IS the answer

Under `-4r`, Watcom's default __watcall preserves every GP register
the callee modifies — confirmed empirically with `c2 oracle compile`
of minimal test functions (a 4-line `void foo(int x) { int a=g; g=a+x; }`
pushes EDX even with no pragma).  So in most cases, a missing pragma
is *not* what's causing prologue divergence.

The few cases where a pragma is actually needed are flagged by the
`c2 pragma-hints` detector as `severity=high`:

  * **`ps_eax_preserved`** — PS pushes EAX in the prologue.  Default
    __watcall removes EAX from `MustSaveRegs` (it's the param/return
    register).  When PS pushes EAX, the source carried `#pragma aux
    NAME modify [edx ebx ecx];` (or similar list **omitting** EAX from
    the modify set), forcing the callee to preserve the caller's EAX
    value.  Typical reason: the caller relies on EAX surviving across
    the call (e.g. a loop-invariant value used after every iteration
    body).
  * **`ps_loadds`** — PS pushes DS.  Source carried `#pragma aux NAME
    __loadds;` (LOAD_DS_ON_ENTRY aux class), typically because the
    function is registered as a callback with a non-flat library (in
    C2 the only known case is `click_handler` registered with the mouse
    DOS service).
  * **`ps_seg_preserved`** — PS pushes other segment regs (FS/GS/ES).
    Even rarer; would need a custom save set in the aux clause.

For `ps_extra_callee_save` / `rc_extra_callee_save` / `callee_save_swap`
the fix is **source-shape, not pragma** — widen/narrow a local, add or
remove a named cache, change a type to bias enregistration.  See the
detector's per-category suggestions.

### Mechanism (OW v1.0 source)

**Pragma parsing** — `bld/cc/c/cprag86.c::GetSaveInfo`:

```c
HW_CTurnOn( CurrInfo->save, HW_FULL );  // start with HW_FULL
if( !have.f_exact && !CompFlags.save_restore_segregs ) {
    // subtract floating seg regs (DS/ES/FS/GS in flat models)
    HW_TurnOff( CurrInfo->save, flt_n_seg );
}
HW_TurnOff( CurrInfo->save, modlist );  // subtract `modify [...]` list
```

With `modify [eax]`, `CurrInfo->save = HW_FULL - flt_seg - {eax}`.  The
`exact` keyword keeps the segregs in the save set; omit `exact` under
flat models or you'll get spurious `push gs/pop gs` etc.

**Per-function state setup** — `bld/cg/intel/c/i86reg.c::CallState`:

```c
pregs = FEAuxInfo( aux, SAVE_REGS );
HW_CAsgn( state->modify, HW_FULL );
HW_TurnOff( state->modify, *pregs );
```

`state->modify = HW_FULL - save_regs`.  Then `MustSaveRegs()` (in
`i86reg.c:275`) subtracts `state.modify`, parm.used, return_reg, and
stack/unalterable regs from `HW_FULL`, leaving the set of registers
the function must preserve.  `SaveRegs()` finally intersects that with
`state.used` (the regs actually touched) to get the prologue push set.

### Detector

`c2/commands/pragma_hints.py` implements the cross-binary detector.
It compares PS-vs-RC prologue push sets and categorises divergences:

* `ps_eax_preserved` (high) — EAX in PS-only set → suggest `modify
  [...]` pragma omitting EAX.
* `ps_loadds` (high) — DS in PS-only set → suggest `__loadds`.
* `ps_seg_preserved` (high) — other segregs in PS-only set.
* `ps_extra_callee_save` (medium) — exactly one extra GP reg on PS side
  → suggest widening a local / adding a named cache.
* `rc_extra_callee_save` (medium) — exactly one extra GP reg on RC side
  → suggest narrowing a local / removing a cache.
* `callee_save_swap` (medium) — one-for-one swap (Rule 28a territory).
* `structural_divergence` (low) — ≥ 2 regs differ on at least one side.
* `prologue_order` (low) — same set, different push order.

Used by:

* `decomp-verify -v` — per-function `Prologue hint:` header line.
* `decomp-verify --json` — `functions[].pragma_hint` field.
* `c2 pragma-hints` — project-wide triage view.  See AGENTS.md
  § "Pragma / Prologue Hints" for the CLI.

Current landscape (1521 functions):

* 7 `severity=high` hits — actual pragma cases.  Worth ~1 000 diff
  bytes total.
* 104 `severity=medium` hits — source-shape levers.  Worth ~30 000
  diff bytes.
* 31 `severity=low` hits — informational only.

### Discovery

`push_node_value` in `decomp/src/web.c`.  The function spent multiple
sessions at 192-238 b residue across every type/scope/order
permutation, until I traced through the OW v1.0 `MustSaveRegs()` /
`SetStackConventions()` / `GetSaveInfo()` path to understand what the
pragma actually does and what default __watcall actually preserves.
The initial hypothesis ("we need `#pragma aux ... modify [eax]`") was
wrong; the actual fix was `int building` + `else if`, both of which
are source-shape, not pragma.  Documenting both is the whole point of
this rule — high-severity prologue divergences map to real pragma
fixes (the EAX/DS-preserved cases), but most prologue divergences are
source-shape problems wearing a prologue-shape disguise.

Verified-on commit (this session): `web.c` 15/15 byte-exact; full
detector wired into `decomp-verify -v`, `decomp-verify --json`, and
`c2 pragma-hints` (with 27-test suite at `tests/test_pragma_hints.py`).


## Rule 71 — Explicit `goto outer_test` for nested do-while-in-while grid walks

### Trigger

A nested loop walks a grid via a memory-resident outer counter
(e.g. `cm_y`) and an inner do-while:

```c
cm_y = 0;
cm_dptr = 0;
while (cm_y < 80) {           /* outer test-at-top */
    cm_x = 0;
    do {                       /* inner do-while */
        landfill_pool[cm_dptr] = 0;
        cm_x++;
        cm_dptr++;
    } while (cm_x < 80);
    cm_y++;
}
```

PS emits the outer loop as **test-at-bottom with jmp-from-init**:

```
mov [cm_y], 0
mov [cm_dptr], 0
jmp .outer_test
.outer_loop:
  ; inner do-while body
  inc [cm_y]
.outer_test:
  cmp [cm_y], 80
  jl .outer_loop
```

The straight `while (cm_y < 80) { ... }` shape produces a different
top-test layout (PS's `jmp .outer_test` is missing, an extra register
caches the post-incremented value, etc.).  Rule 50 covers the
single-loop `for` → bottom-test rewrite, but for **nested loops
where the inner body is a `do-while`** that rewrite alone is not
enough — Watcom still picks the test-at-top form for the outer
`for` / `while`.

### Source-level lever

Spell out the jmp-from-init explicitly with `goto`:

```c
cm_y = 0;
cm_dptr = 0;
goto outer_test;
outer_loop:
    cm_x = 0;
    do {
        landfill_pool[cm_dptr] = 0;
        cm_x++;
        cm_dptr++;
    } while (cm_x < 80);
    cm_y++;
outer_test:
    if (cm_y < 80) goto outer_loop;
```

This is the literal C-source pattern PS used for every grid-walk
sweep in the landfill / battle / region modules.  Verified on
sibling `clear_all_highlights_from_battlemap` (byte-exact) which
uses this exact `goto outer_test;` shape.

### Caveats

* The bottom-test expression must be **cheap** — preferably a single
  global compared to a constant (`cm_y < 80`).  Non-constant bounds
  like `row < start_row + row_count` regress because Watcom
  re-evaluates the sum at the bottom (where it could be hoisted at
  the top).  Tested on `show_battle_landfill` — `goto outer_test`
  *added* 5 bytes vs the plain `while` form because of the
  recomputed addition.
* Inner loop must use a non-counter-shape (do-while or call-laden
  while).  A clean nested `for` already triggers Rule 50.
* Inner loop body should NOT make a function call that aliases the
  outer counter via a global pointer — otherwise Watcom can't keep
  the inner loop independent of the outer test.

### Wins this discovery

| function (file)              |  before |  after | Δ |
|------------------------------|--------:|-------:|--:|
| `clear_landfill` (landfill.c) |   43    |   0    | -43 |
| `get_landfill` (landfill.c)   |   43    |   0    | -43 |
| `take_from_warehouses` (map.c) |  132    | 121    | -11 |
| `show_city_landfill` (landfill.c) | 370 | 347 | -23 (partial; other diffs remain) |
| `show_cohort_landfill` (landfill.c) | 322 | 299 | -23 (partial) |
| `show_region_landfill` (landfill.c) | 399 | 389 | -10 (partial) |

### Mechanism

Watcom 10.0a's loop-shape selector (`bld/cg/c/loops.c`) recognises
`for` and `while` patterns syntactically.  The recogniser walks the
IL forward looking for the test-block-of-the-loop, and emits one
of two layouts based on a heuristic that examines:

1. Whether the body contains function calls that may invalidate
   the loop test (call-laden body → may need top-test).
2. Whether the counter is enregisterable (memory globals with calls
   in body → can't enregister).

For the nested case, the inner loop's calls / global writes mark
the outer counter as "may be modified", which biases Watcom toward
test-at-top.  The explicit `goto outer_test;` bypasses the
recogniser and produces the literal IL the source asks for.

### Discovery

`clear_landfill` in `decomp/src/landfill.c` paired with sibling
`clear_all_highlights_from_battlemap` (byte-exact donor) at 60%
containment via `c2 sibling`.  The donor's source uses the
`goto outer_test;` pattern verbatim; transferring the shape closed
clear_landfill to 0 b in one edit.  Same technique then propagated
across 5 sibling functions in the same TU.

Verified-on commit: `5cca25e fix(landfill): goto-test loop shape + industry test reorder`.


## Rule 72 — Prefix-increment / -decrement on field eliminates the `int cN = field ± 1` cache

### Trigger

A counter pattern that reads, increments/decrements, stores, and
tests, written via a named local:

```c
/* counter wrap-around (do_32_count) */
int c4;
c4 = cnt4 + 1;
cnt4 = c4;
if (c4 >= 4) cnt4 = 0;

/* per-tick decrement-and-test (sf01_wait) */
int sub;
sub = figure_list[figure_no].wait_counter - 1;
figure_list[figure_no].wait_counter = sub;
if (sub > 0) return;

/* timer-increment-then-test (sf02_death) */
signed char cnt;
cnt = (signed char)(figure_list[figure_no].death_timer + 1);
figure_list[figure_no].death_timer = cnt;
if (cnt > 0x40) ...;
```

Watcom materialises the `int cN` / `int sub` / `signed char cnt`
local in a register (typically callee-save EBX or DH, depending on
context), emits `mov reg, [field]; inc/dec reg; mov [field], reg;
test reg, reg`.  PS instead emits **direct byte-RMW on the field
plus a single byte test**:

```
inc byte [field]                  ; (or dec byte [field])
cmp byte [field], N
jge ...
```

### Source-level lever

Replace the named-temp cache with the **prefix** form on the field:

```c
/* counter wrap-around: ++ */
++cnt4;
if (cnt4 >= 4) cnt4 = 0;

/* per-tick decrement: -- */
if (--figure_list[figure_no].wait_counter > 0) return;

/* timer increment: ++ */
++figure_list[figure_no].death_timer;
if (figure_list[figure_no].death_timer > 0x40) ...
```

Watcom now lowers the prefix `++` / `--` to a direct memory-RMW
instruction (no register temp), and the immediately-following
re-read of the field is folded into the compare (`cmp byte [field], N`).

### Why prefix, not postfix

Postfix `cntN++` returns the OLD value, requiring Watcom to
materialise the pre-increment value in a register *before* doing
the store — same effect as the explicit `int cN = field + 1`
cache.  When the post-value is not used (statement form), Watcom
*sometimes* recognises this and folds, but inconsistently.  Prefix
`++cntN` returns the NEW value and reliably folds.

### Difference from Rule 54

Rule 54 documents the *opposite* direction:
`x--;` keeps the original load *and* the decremented value in
separate registers when both are referenced — useful when PS
emits two reads.  Rule 72 is for the case where PS emits a
**single in-memory** RMW with no register temp; the lever is to
match by not introducing the temp at all.

### Wins this discovery

| function (file)               | before | after |   Δ |
|-------------------------------|-------:|------:|----:|
| `sf01_wait` (battle.c)        |   64   |   0   | -64 |
| `sf02_death` (battle.c)       |   32   |   0   | -32 |
| `do_32_count` (lib32.c)       |  135   |   0   | -135 |

### Mechanism

`bld/cc/c/cmac1.c::PreIncDec()` lowers `++expr` / `--expr` to an
IL-tree `OPADD/OPSUB` node with a single LHS that is the lvalue
itself (no temp creation).  The IL optimisation pass spots this
shape and generates `inc/dec [m]` directly.

`PostIncDec()` lowers `expr++` to an IL sequence that loads the
pre-value into a temp, performs the add, stores back, and yields
the temp — three IL nodes, harder to optimise back into a single
RMW.

The same applies to the explicit cache:
`int sub = field - 1; field = sub; ...` emits three IL nodes plus
a SYM_VARIABLE binding for `sub`.  The optimiser doesn't recognise
this as equivalent to `--field`.

### Discovery

`sa01_wait` (byte-exact donor) vs `sf01_wait` (64 b residue at
sibling 33%) via `c2 sibling`.  `sa01_wait` source already uses
`if (--army_list[army_no].wait_count <= 0)`; transferring the
prefix form to `sf01_wait` (which had an `int sub` cache) closed
the function in one edit.  Then propagated to `sf02_death`
(applied to two `death_timer + 1` cache sites) and `do_32_count`
(applied to all seven cnt2..cnt256 wrap-arounds).

Verified-on commits:
* `58e8405 fix(battle): sf01_wait byte-exact via prefix-decrement field pattern`
* `f5011bb fix(battle): sf02_death byte-exact via prefix-inc field pattern`
* `cdf0f55 fix(lib32): do_32_count byte-exact via prefix-inc on globals`

### Extension to switch-driven INT globals (sibling-witnessed, 2026-06-13)

The canonical Rule 72 trigger is BYTE globals where prefix folds to
`inc/dec byte [m]`.  But the prefix-vs-postfix choice ALSO matters for
**int globals incremented inside a switch's case bodies**, even though
the operand width never becomes a single byte-RMW.  The prefix form
steers Watcom's CSE walk over the case bodies into the same per-arm
order PS picks, where the postfix form computes the old value into an
intermediate register and that intermediate's register home cascades
through every case's register layout (a Rule 28-style swap).

Worked: `move_clock_ferret`, `move_anti_ferret` (common.c, 2026-06-13):
both had 93-byte residues with postfix `clock_ferret_y--; clock_ferret_x++;`
in every case.  The byte-exact sibling `move_to_tb_value` used prefix
`--tb_y; ++tb_x;` everywhere.  Mirroring the prefix form on both
functions (8 cases each, all `--`/`++` on int globals) closed both in
the same commit: 93 → 0 per function.  No source change other than
the `x--; → --x;` swap and `y++; → ++y;` swap at every site.

Use the byte-exact-sibling oracle (`Sibling:` header in
`decomp-verify -v`) to spot this: when a sibling at ≥ 40 % similarity
uses prefix where you use postfix, try the swap.

## Rule 73 — Remove pointer cache to fold `array+field` into disp32

### Trigger

PS emits `cmp [reg + huge_disp32]` (where the disp32 is
`array_address + field_offset` folded together), but recomp emits
`cmp [reg + small_offset]` (where reg is a base pointer cached
into a local).  Example from `goto_army_attack`:

```
PS:   83 ba a4 2f 07 00 00     cmp [edx + 0x72fa4], 0
                                       ; edx = cohort_id * 0x15a
                                       ; 0x72fa4 = army_routes + 8 (target_army field)
RC:   83 7a 08 00               cmp [edx + 8], 0
                                       ; edx = &army_routes[cohort_id] (base ptr cached)
                                       ;   then +8 is the field offset within the row
```

Both compute the same effective address.  The difference is what's
in EDX: PS keeps just the **row-stride product** (`cohort_id * 0x15a`)
and folds the array base into each access's disp32; recomp caches
the **full row pointer** (`array_base + cohort_id * 0x15a`) and
adds small field offsets at use sites.

### Source-level lever

Remove the pointer cache and inline the indexed access at every
use site:

```c
/* BAD — caches base pointer */
struct army_route_rec *route;
route = &army_routes[army_list[army_no].cohort_id];
if (route->target_army == 0) return 0;
if (army_list[army_no].dest_y < route->chase_row) return 0;
enemy_army = route->target_army;

/* GOOD — matches PS */
if (army_routes[army_list[army_no].cohort_id].target_army == 0) return 0;
if (army_list[army_no].dest_y <
        army_routes[army_list[army_no].cohort_id].chase_row) return 0;
enemy_army = army_routes[army_list[army_no].cohort_id].target_army;
```

Watcom will recompute `cohort_id * sizeof(struct)` at each use, but
keep the product in EDX (or any free reg) and fold the `array_base
+ field_offset` constants into the displacement field of each
mem-op.  Result: one CSE-shared scaled index times K accesses, each
with its own folded disp32.

### Caveats

* This is the **opposite** of Rule 63 (cached row pointer).  Both
  rules exist because Watcom's choice depends on use count and
  address-mode encoding cost:
  * **≤ 3 uses** of the row → no cache, fold base+field into disp32
    (Rule 73).  Each access uses `mov/cmp [scaled_index + array_offset]`
    which is the same byte count as `[ptr + field]`.
  * **≥ 4 uses** of the row → cache helps.  PS itself caches in those
    cases (Rule 63).
* The function must use the index from a memory-resident global
  (e.g. `army_list[army_no].cohort_id`) so that re-reading at each
  callsite is free.  If the index requires re-computation (e.g.
  `compute_idx(x)`), caching is mandatory.
* Watcom needs to keep the scaled-index product in **one** register
  across all uses.  If register pressure forces it to spill the
  product, the optimiser falls back to a cached pointer anyway and
  the win evaporates.
* **LOCAL index vs GLOBAL index (verified 2026-06, `media_text_place`
  vs `get_units_status`/`get_battle_centuries_left`)**: the disp32-fold
  only fires reliably when the array index is a **local** loop variable.
  When the index is a **global** (`temp_unit`, `our_battle_army`, …),
  inlining `array[g].field` forces Watcom to re-load the global from
  memory at each field access (it cannot prove the global is unchanged
  across the stores), so the fold *regresses* — it trades one cached
  pointer for N global re-loads.
  * `media_text_place`: `for (i=0;i<20;i++) help_page_hot_spots[i].f=0;`
    — local `i` → fold fires, **−32 b**.
  * `get_units_status`: `for (temp_unit=…) unit_list[temp_unit].f=0;`
    — global `temp_unit` → inlining **regressed 641→720 b**; reverted.
  * `get_battle_centuries_left`: fixed global indices
    `army_list[our_battle_army]` → no improvement; reverted.
  Rule of thumb: only apply Rule 73 inlining when the index lives in a
  register-promotable **local**; for global/loop-counter indices keep
  the cached pointer (Rule 63).

### Wins this discovery

| function (file)              | before | after |  Δ |
|------------------------------|-------:|------:|---:|
| `goto_army_attack` (int_c2.c) |   79  |   0   | -79 |
| `new_army_route_point` (int_c2.c) |  167 | 136 | -31 (partial; outer-block residue remains) |

### Mechanism

`bld/cg/c/treefold.c::FoldAddress()` collapses
`(scaled_index) + (constant_base + constant_field)` into a single
disp32 when both constants are link-time-known.  This happens at
IL-level *before* register allocation, and the result is a
single SIB-form mem-op (`[reg*scale + disp32]`).

When the source caches `&array[idx]` to a local pointer, the cache
is a SYM_VARIABLE with type `struct ptr` — not a folded address.
The IL stores the pointer in a register and later accesses are
`[ptr_reg + field_const]`.  `FoldAddress()` doesn't merge across
the SYM_VARIABLE boundary.

### Discovery

`goto_army_attack` (79 b residue) via verbose-diff inspection: the
first byte diff at `+0x1c` showed PS `cmp [edx + 0x72fa4]` (huge
disp32) vs RC `cmp [edx + 8]` (cached ptr + small offset).
Removing `route` cache produced byte-exact.  Same lever then
shaved 31 b from `new_army_route_point` (one of the bigger
`army_routes`-using functions).

Verified-on commits:
* `84c0d7f fix(int_c2): goto_army_attack byte-exact (remove route ptr cache)`
* `2919a87 fix(int_c2): inline army_routes index in new_army_route_point (-31b)`

### Refinement A — byte arrays vs struct arrays (which form to use)

The replacement depends on the array's element stride:

* **Byte arrays (`city_map`, `region_map`, `battle_map`,
  `pseudo_map`, all `unsigned char[]`, stride 1):** inline the
  index directly — `map[idx + field]`.  The index *is* the byte
  offset, so PS keeps it in a register (scale 1) and folds
  `map_base + field` into disp32.  This works for an arbitrary
  number of field reads (8+ neighbours), not just ≤3 — the
  "≤3 uses" guideline is conservative; the real criterion is
  whether PS folds base+field as disp32.
  Won `test_for_next_to_region_wall` (184 b → 0, 8 neighbour reads).

* **Struct arrays (stride > 1, e.g. `svga_refresh_data`):** do
  NOT inline `arr[idx].field`.  The element index must be scaled
  by the struct size, and Watcom either re-multiplies per field
  access or uses SIB `[idx*k + base]`, which is *worse* than the
  cached pointer.  Keep the `p = &arr[idx]` cache for struct
  arrays.  Counter-example: inlining `svga_refresh_data[idx].field`
  regressed `setup_svga_refresh_data` 169 b → 181 b (reverted).

### Refinement B — loop pointers: use a running INT index, not a pointer

When the cached cell is *advanced in a loop* (`cell += stride`),
the same disp32-fold lever applies, but the fix is to make the
running cursor an **`int` index**, not a pointer:

```c
/* WRONG — pointer cursor forces `add reg, map_base` + [cell+field] */
unsigned char *cell = &city_map[start];
for (i = 0; i < n; i++, cell += 20)
    if (cell[1] & 0x20) ...

/* RIGHT — int index, PS folds map+field as disp32, advances the index */
int p = start;
for (i = 0; i < n; i++, p += 20)
    if (city_map[p + 1] & 0x20) ...
```

PS keeps the byte index in a register and reads
`[idx_reg + (map_base + field)]`; the pointer form emits an
`add reg, map_base` to materialise the cursor and then small
`[cell + field]` displacements that don't match PS's fixup disps.
Won `test_perimeter_for_road_and_forum` (293 b → 0, four perimeter
loops) — combined with the Rule 30/31 nested-if rewrite of the
`a && (b || c)` body so the shared `return 1` lands where PS puts it.

### Power-of-2 strides: the lever is NOT here — it's the zext idiom (L0)

When the index stride is `1/2/4/8`, the Rule 63/73 cache-vs-inline lever
does NOT move it: Watcom's addrfold re-encodes `idx*{2,4,8}` as an x86
SIB scale `[idx*N+disp32]`, and every plain form (`idx*=4`,
`int j=idx*4`, `j=idx<<2`, `a=idx*2;j=a*2`, `text_buffer+idx*4`) folds
back to the scale.  So Rules 63/73/101 (non-power-of-2 strides like
0x15a, 20, 1600 — where SIB can't scale) don't transfer here.

**But the materialised form IS reproducible** (Determinism Principle — it
exists in PS.EXE).  In `get_buffer_ofset` (×4) PS emits `mov edx,eax;
shl edx,2; [edx+disp32]`.  The materialisation is a *consequence* of the
**Rule 49 clear-first zext idiom** (`xor eax,eax; mov al,[edx+disp]`)
claiming EAX as the byte-scratch — forcing the index OFF EAX into EDX
(scale-1 base, text_buffer folded to disp32).  RC instead keeps the
index in EAX as the SIB index and uses an and-form zext on another byte
reg.  So the lever lives at **L0 (the zext idiom + accumulator register
choice)**, not addrfold.  Triggering it means getting RC to put the
byte-load accumulator in EAX with the clear-first idiom; the
`(unsigned char)` cast alone hasn't flipped the joint register decision
(lever not yet found, NOT impossible).  When fighting a power-of-2-scale
addressing diff, look at the byte-load / accumulator register choice,
not the index expression.


## Rule 74 — Inline LEA-able expressions over cached intermediate locals

### Trigger

A function makes K successive calls with arguments that differ by
small integer offsets from a base:

```c
void four_by_four(int x, int y) {
    int parity = (y & 1) != 0;
    int x0;          /* cached x - parity */
    int x2;          /* cached x + 1     */
    int y1;          /* cached y + 1     */
    int y2;          /* cached y + 2     */

    show_one_ptr(x, y);
    y1 = y + 1;
    x0 = x - parity;
    show_one_ptr(x0, y1);
    show_one_ptr(x0 + 1, y1);
    y2 = y + 2;
    show_one_ptr(x - 1, y2);
    ...
}
```

The cached locals (`x0`, `y1`, `y2`) get spilled to stack:

```
mov [esp + 4], y1                 ; spill y1
...
mov edx, [esp + 4]                ; reload y1 for next call
```

PS instead emits the offset directly as an LEA at each callsite:

```
lea edi, [ecx + 4]                ; compute y + 4
mov edx, edi
mov eax, ebp                      ; reload base
call show_one_ptr
mov edx, edi                      ; reuse y+4 across two calls
...
```

### Source-level lever

Inline the small-offset expressions verbatim at each callsite — no
intermediate locals:

```c
void four_by_four(int x, int y) {
    int parity = (y & 1) != 0;

    show_one_ptr(x, y);
    show_one_ptr(x - parity, y + 1);
    show_one_ptr(x - parity + 1, y + 1);
    show_one_ptr(x - 1, y + 2);
    show_one_ptr(x, y + 2);
    show_one_ptr(x + 1, y + 2);
    ...
}
```

Watcom evaluates each `base + N` expression with an LEA into a
free reg per call, reuses the LEA result across consecutive calls
with the same offset, and never spills.

### When the cache helps vs hurts

The cache wins when:
* The offset expression involves a multi-cycle op (`mul`, `div`,
  function call), so caching genuinely amortises the cost.
* The number of uses is high (≥ 6 sites referencing the same
  precomputed value).

The cache hurts when:
* The offset is a single ADD or SUB by a small constant — LEA
  computes it in 1 cycle, no win from caching.
* The function makes many consecutive calls and the cache forces
  Watcom to keep the value alive across all of them, eating a
  callee-save register or a stack slot.

For `four_by_four`-style cell-painting routines, every offset is
a `base ± k` expression that LEAs in one cycle.  The cache offers
no compute saving, only spill cost.

### Sibling-pattern observation

`three_by_three` (byte-exact) and `four_by_four` (88 b diff)
target the same 2×2 / 3×3 / 4×4 cell-stamping role with similar
shape.  `three_by_three` uses inline expressions verbatim:

```c
show_one_ptr(x - parity, y + 1);
show_one_ptr(x - parity + 1, y + 1);
```

`four_by_four`'s author cached `x0 = x - parity`, `y1 = y + 1`,
etc.  Transferring `three_by_three`'s shape produced byte-exact
in one edit.

### Wins this discovery

| function (file)        | before | after | Δ |
|------------------------|-------:|------:|--:|
| `four_by_four` (pm_map0.c) | 88 | 0 | -88 |

### Discovery

`c2 sibling four_by_four --status exact` returned `three_by_three`
at 37.5 % containment with shape diff in the cached locals.
Inlining all four cached locals produced byte-exact.

Verified-on commit: `eaee8bb fix(pm_map0): inline four_by_four to match three_by_three pattern`.


## Rule 75 — Mirror sister-function signatures even when the body ignores the args

### Trigger

A function appears in a family of sister implementations
(`raider_in_region(dirc, from_sea)`, `barbarian_in_region(dirc, from_sea)`,
`empire_in_region(dirc, from_sea)`), but one variant is declared with
fewer parameters:

```c
int revolt_in_region(void)                  /* old: no args */
{
    /* body doesn't use dirc or from_sea */
    revolt_size = get_region_revolt_points();
    ...
}
```

Even though the body ignores the args, declaring `void` produces a
different prologue than declaring `(int dirc, int from_sea)`.  In
the `(void)` form, Watcom adds an extra `push edx` to the
prologue, treating EDX as a "potentially-live inbound register
needing preservation".  PS pushes only `ebx, ecx`.

### Source-level lever

Declare the function with the same parameter list as its sisters,
discard the unused args with `(void)cast`:

```c
int revolt_in_region(int dirc, int from_sea)
{
    (void)dirc;
    (void)from_sea;
    revolt_size = get_region_revolt_points();
    ...
}
```

Update the caller(s) to pass values.  `c2 inferred-sig` tells you
what callers actually pass — read its `caller list` line.  For
`revolt_in_region`, the caller `revolt_trouble` was setting
EAX=1 and EDX=1 before the call (leftover from prior operations);
passing `(0, 0)` produced the same registers-live-on-call state
modulo dead-value identity.

### Why the prologue changes

Under `-4r`, Watcom's calling-convention setup looks at the function's
formal parm list to decide which registers are "args" (caller-provided,
free to use as scratch in the callee without saving) vs "inbound
state" (preserved register that the caller had filled, must save).

* `int f(int a, int b)` — EAX, EDX are args.  Callee may clobber
  them without saving.
* `void f(void)` — no args.  EAX is still scratch (return-value
  register), but EDX is treated as inbound and gets a defensive
  `push edx` if the function references EDX at all.

PS's sister functions declare `(int dirc, int from_sea)`, so they
get the args-not-saved prologue.  Declaring `revolt_in_region(void)`
forces the saved-prologue path even though the body never reads
EDX.

### Wins this discovery

| function (file)              | before | after |   Δ |
|------------------------------|-------:|------:|----:|
| `revolt_in_region` (bbarian.c) |  61   |   0   | -61 |
| `revolt_trouble` (bbarian.c)   | 248   | 225   | -23 (caller cascade improvement) |

### Diagnostic

Run `c2 inferred-sig <func>` and look for:

```
! ARG COUNT: declared=0, inferred=2  (caller-confirmed=2)
callers (1): args set before call: eax=1, edx=1; ...
```

When `caller-confirmed` is non-zero but `declared=0`, the function is
under-declared.  If sister functions exist, mirror their signature.

### Discovery

`c2 inferred-sig revolt_in_region` reported `! ARG COUNT: declared=0,
inferred=2 (caller-confirmed=2)` with EAX and EDX set before the
caller's call site.  Sister `raider_in_region` takes `(int dirc,
int from_sea)`.  Adding the args to `revolt_in_region` and updating
the caller closed both functions in one edit.

Verified-on commit: `4ffeaa4 fix(bbarian): revolt_in_region takes (dirc, from_sea) like sisters`.


## Rule 76 — Split OR-chain shared-write into separate if/else with back-jumps

### Trigger

A first-if test is a 3+ term OR-chain that branches to a shared
single-byte write:

```c
if ((terrain & 6) != 0 ||
    (kind >= 0x1e && kind <= 0x51) ||
    kind == 0xe3 ||
    kind == 0xe4)
{
    landfill_pool[cm_dptr] = 0x96;
} else if (level != 0) {
    ...
}
```

Watcom emits the OR-chain with short-circuit branches that all
eventually land on a single `mov byte [m], 0x96; ret` block.  PS
instead emits each term as its **own conditional with an
independent back-jump to a single shared write**:

```
cmp ..; je shared_write
... next term ...
cmp ..; je shared_write
shared_write:
  mov byte [m], 0x96
  ret
```

The difference is the **per-term test layout**: PS uses
`xor edx,edx; mov dl, al; cmp edx, 0xN` (10 b per equality test)
because it keeps the comparand in a byte register; Watcom's
short-circuit form fuses the tests through a chain of
`cmp eax, N; jcc next` (5 b per test) using EAX as a working
register.  When the back-jump distance varies, recomp's
short-circuit form can use 2-byte short `jcc` for some terms while
PS used 6-byte near `jcc`, cascading byte deltas.

### Source-level lever

Split each OR term into its own `else if` block.  Each block
writes the shared value:

```c
if ((terrain & 6) != 0) {
    landfill_pool[cm_dptr] = 0x96;
} else if (kind == 0xe3) {
    landfill_pool[cm_dptr] = 0x96;
} else if (kind == 0xe4) {
    landfill_pool[cm_dptr] = 0x96;
} else if (kind >= 0x1e && kind <= 0x51) {
    landfill_pool[cm_dptr] = 0x96;
} else if (level != 0) {
    ...
}
```

ComTail merges the four identical assignments back into a single
write at the end of the function, and emits per-term back-jumps to
that shared write — matching PS's layout.

### Ordering matters

The order of the split terms drives the back-jump distances and
thus the final byte count.  The right order is **the order PS's
asm emits the tests**, which you read off the `c2 disasm` output:

```
PS asm for get_security_ov_image:
  +0x44: test (terrain & 6) → je SKIP_0x96
  +0x48: load kind into DL
  +0x68: cmp DL, 0xe3       → je SHARED_0x96
  +0x76: cmp DL, 0xe4       → je SHARED_0x96
  +0x83: cmp DL, [0x1e, 0x51] range → jl SKIP / jg SKIP
```

So the source order is: `terrain & 6`, then `kind == 0xe3`, then
`kind == 0xe4`, then `kind >= 0x1e && kind <= 0x51`.  Putting the
range test before the equality tests regresses.

### Variation: equality first when there's a single "weird" value

For `get_industry_ov_image`, the OR is
`(kind >= 0xfc && kind <= 0xff) || kind == 0xfa`.  PS-order would
be range-first, equality-second.  But splitting in **equality-first
order** (`kind == 0xfa; else if range`) actually wins more bytes:

```c
if (kind == 0xfa) {
    landfill_pool[cm_dptr] = 0x96;
} else if (kind >= 0xfc && kind <= 0xff) {
    landfill_pool[cm_dptr] = 0x96;
} else if (industry != 0) { ... }
```

This is the right order for `get_industry_ov_image` because the
equality test produces a short back-jump (`je` is 2 b), the range
test that follows produces a slightly-longer back-jump (`jl`/`jge`
to the same target), and the back-jump distances chain
favourably with the rest of the function.  Always disassemble both
candidate orderings if the PS asm isn't an obvious match.

### Wins this discovery

| function (file)                       | before | after | Δ |
|---------------------------------------|-------:|------:|--:|
| `get_security_ov_image` (landfill.c)   |   95  |   88  | -7 |
| `get_industry_ov_image` (landfill.c)   |  104  |   87  | -17 (partial; regalloc residue remains) |

### Discovery

`get_industry_ov_image` diffing at 104 b with sibling
`get_admin_ov_image` (byte-exact) at 42 % containment.  Both share
the same `kind` range-test → shared write structure, but admin's
single-range test gave a different IL pattern than industry's
range || equality.  Splitting industry's OR into two if/elses
shaved 17 b.  Same lever applied to `get_security_ov_image`'s
4-term OR shaved 7 b.

Verified-on commits:
* `5cca25e fix(landfill): goto-test loop shape + industry test reorder`
* `4f7aabb fix(landfill): split get_security_ov_image OR chain into 4 if/else`


## Rule 77 — Uninitialised local on fall-through (UB-compatible) for callee-save return path

### Trigger

A search function returns a value whose only assignment is inside
the matched branch:

```
PS asm:
  push ebx
  push ecx
  push edx
  mov edx, eax            ; save ref param to edx
  xor ecx, ecx            ; loop counter = 0
  mov [global], cx        ; persist counter
  jmp .test
.loop:
  ...
  cmp [match]
  jne .advance
  movsx ebx, byte [field]   ; result = field, ONLY assignment of ebx
  jmp .done
.advance:
  inc [global]
.test:
  movsx eax, [global]
  cmp eax, 0x1a
  jl .loop
.done:
  mov eax, ebx              ; return result (ebx)
  pop edx
  pop ecx
  pop ebx                   ; restore CALLER's ebx
  ret
```

EBX on the fall-through (no-match) path is **whatever the caller
had** — the function's prologue pushed/popped EBX, so the saved
value is restored across the body but the **return register EAX**
is set from the **current** EBX, not the caller's.  Effectively
the no-match path returns garbage.

This is undefined behaviour by the C standard, but compiles
cleanly and is fine when callers guarantee a match.

### Source-level lever

Declare `int result;` **uninitialised**, assign inside the matched
branch only, and `return result;` at both exit points:

```c
int get_army_name_from_fort_ref(int ref)
{
    int result;       /* UB-on-no-match: callers guarantee a match */
    for (army_no = 0; army_no < 26; army_no++) {
        if (army_list[army_no].exists != 0 &&
            ref == army_list[army_no].fort_ref) {
            result = army_list[army_no].cohort_id;
            return result;
        }
    }
    return result;     /* returns garbage from EBX-on-entry; callers don't hit this */
}
```

Watcom maps `result` onto a callee-save register (typically EBX)
which is preserved across the loop via the prologue's `push ebx;
... pop ebx`.  The function's RETURN register (EAX) is loaded from
EBX at the single `mov eax, ebx; ret` exit — but EBX is never
*written* on the no-match path, so the post-prologue body sees
whatever value was sitting in EBX after the matched-only
assignment.  In practice this is the value last placed there by a
preceding call site's setup register (e.g. EAX was passed as the
parm, then `mov edx, eax` saved ref to EDX, and EBX still holds
the caller's saved value).

The cleaner alternatives — `int result = ref;` (init to ref) or
`int result; ...; result = ref; done:` (single-exit with fallthrough
set) — both insert a `mov ebx, eax` (or equivalent) somewhere in
the prologue or epilogue, adding 2-3 bytes that diff against PS.

### Caveats

* **Verify caller invariant first.**  Read every caller of the
  function and confirm none uses the return value on the no-match
  path.  For `get_army_name_from_fort_ref`, callers always test
  for a matching fort_ref before invoking, so the UB is invisible.
* Add a source comment explaining the deliberate UB (otherwise a
  future reader will "fix" it and regress the function).
* This is **only worth doing for searches whose body is otherwise
  byte-exact** — adding UB to fix a regalloc divergence is a bad
  trade.  Use this when the search structure already matches PS
  but the result-init is the only remaining diff.

### Wins this discovery

| function (file)                           | before | after |   Δ |
|-------------------------------------------|-------:|------:|----:|
| `get_army_name_from_fort_ref` (common.c)  |   53  |   0   | -53 |

### Diagnostic

The "Prologue hint: Recomp uses an extra callee-save register"
line in `c2 decomp-verify -v` is a typical fingerprint, **combined
with** a body that's byte-equal except for a single `mov reg,
eax` (or equivalent init) in the prologue.  If you also see
"early return inside loop" topology and the post-loop return
matches the in-loop return's register, this rule is a candidate.

### Discovery

`c2 sibling get_army_name_from_fort_ref` → `clear_army_from_fort_ref`
at 37 % containment.  Both walk the 26-army list with the same
filter pattern.  Inspection of PS asm revealed the `mov eax, ebx`
single-exit with EBX uninitialised on the no-match fall-through.
Three variants tested (`int result = ref;`, single-exit
`done:`/goto, and the uninit form) — only the uninit form was
byte-exact.

Verified-on commit: `4a0bb12 fix(common): get_army_name_from_fort_ref byte-exact`.


## Rule 78 — Pointer-save before dereference forces the `mov edx, eax; inc eax; lea ebp, [edi+ebx]; mov dl, [edx]; mov [ebp], dl` 5-insn store pattern

When PS source copies bytes through a pointer with both an
explicit pointer-save AND a separate destination-address
computation, Watcom emits a stylized 5-instruction sequence:

```
mov edx, eax            ; save source pointer
inc eax                 ; advance original
lea ebp, [edi + ebx]    ; compute destination address
mov dl, [edx]           ; load from saved pointer
mov [ebp], dl           ; store to destination
```

The pattern arises only when the source has BOTH:

  1. A local pointer-save before the dereference
     (`char *p = suffix++;`)
  2. A local destination-address computation
     (`char *q = &buf[i];`)

Writing the same logic compactly:

```c
buf[i] = *suffix++;          /* doesn't trigger */
*dst   = *suffix++;          /* with dst pre-computed once */
```

produces a 2-insn `mov ch, [eax]; mov [edi+ebx], ch` direct
indexed copy.  Identical semantics, but the byte sequence
diverges by ~140 b through a heavily-iterated copy loop in
font_no (suffix copy + later loop bodies).

### Source form

```c
while (*suffix != 0) {
    char *p = suffix++;       /* save BEFORE deref */
    char *q = &buf[i];        /* dst pointer */
    *q = *p;                  /* indirect via saved ptr */
    i++;
    if (i >= 16) break;
}
```

### Why Watcom emits this

The two named pointers create explicit live ranges Watcom can't
fold:

  * `p` keeps the pre-increment value live in a scratch reg (EDX)
    while `suffix++` advances the original (EAX).
  * `q` forces the destination to be computed via LEA into a
    scratch reg (EBP) instead of a direct indexed `[base+index]`
    operand on the store.
  * The store becomes `mov [ebp], dl` (1-byte displacement)
    instead of `mov [base+index], reg` (longer).

Without the named locals, Watcom CSE-folds the pointer save and
the LEA, generating the shorter direct form.

### Detection

`c2 disasm <fn>` showing a `mov reg2, reg1; inc reg1; lea reg3,
[...]; mov dl, [reg2]; mov [reg3], dl` quintet on a byte-copy
loop is the fingerprint.  The double-save (one in saved reg,
one in incremented reg) is the giveaway.

### Detector

Auto-detected (`detect_rule_78` + `_find_rule_78_copies` in
`rule_hints.py`).  Function-level pre-scan over the diff row
list locates 5 consecutive PS-side instructions matching the
exact pattern `mov regA, regB / inc regB / lea regC, [r1+r2]
/ mov regA_byte, [regA] / mov [regC], regA_byte`, where
`regA ∈ {EAX, EBX, ECX, EDX}` (must have a low-byte form).
Suppresses when the same 5-insn shape is present on the
recomp side too (no actionable lever).  Each diff row inside
a matched window is annotated with a Rule 78 hint.  Regression
tests in `tests/test_rule_hints.py` cover positive matches,
the equal-row suppression, the symmetric-shape suppression,
the broken-pattern rejection, and the regA-must-have-low-byte
constraint.

### Discovery

font_no (220 b @ 0x2704e) had remained ~150 b diff for months
under various source rewrites.  Coordinated cgex exploration
with `/tmp/ow110/bld/cg/intel/386/c/386rgtbl.c` confirmed:

  * DoubleRegs[] picks `EAX, EDX, EBX, ECX, ESI, EDI, EBP` (see
    Rule 89), with EDI before EBP for callee-save allocation, which determined
    the divisor register choice in the digit loop.
  * Forcing `bufp = buf` (cache buf into a local pointer) pushed
    EDI = buf, freeing EBP for the divisor — exactly PS's
    pattern.
  * The named pointer-save in the suffix-copy loop was the final
    lever that flipped the 5-insn pattern.

Combined with Rule 64-style `int div10 = 10` reload (non-volatile
with two explicit writes — see Rule 64 § Divisor) and dropping
the `saved_pad` indirection so pad_char spills to `[esp+4]`
naturally, the 152 b diff collapsed to 0.

Verified-on commit: `9fd1ab3 fix(lib32): font_no byte-exact`.

## Rule 79 — Parallel-counter loops: init order outside `for(...)` and comma-step inside govern register binding and increment ordering

PS source for tight blit/copy loops that step two parallel counters
(typically a destination index `i` and a source index `s`) controls
two distinct codegen decisions through C-source syntax:

### Lever A — Init order outside `for(;...;...)`

The order in which the counter locals get their first `= 0`
(or initial value) determines which physical register Watcom binds
to each local.  PS source pattern:

```c
i = 0;
s = 0;
for (; i < N; i += 2, s += 8) { ... }
```

emits

```asm
xor ebx, ebx      ; i=0 -> EBX  (first init -> first DoubleRegs choice)
xor esi, esi      ; s=0 -> ESI  (second init -> second DoubleRegs choice)
jmp loop_test
```

If the source instead writes

```c
s = 0;
for (i = 0; i < N; ...) { ... }
```

the `for`-header `i = 0` is hoisted by the parser to the prologue
*after* the bare `s = 0`, so Watcom's allocator sees the locals in
the reverse order.  EBX/ESI roles flip, producing a whole-function
register swap (Rule 28 territory).  Every indexed access inside the
loop body then differs in its SIB encoding.

This is **not** Rule 28 proper because there's no allocator
tie-break to break — it's an ordering-driven binding.  But the
visible diff *looks* like Rule 28 (esi vs ebx throughout the body)
until you check the init-sequence.

### Lever B — Comma-step inside `for(...;...;step)`

Where the increment of `s` lives in the C source controls **the
order of the two `add` instructions** at the bottom of the loop:

```c
for (; i < N; i += 2, s += 8) {     // both in step: PS shape
    body...
}
```

emits

```asm
add ebx, 2          ; i += 2  (step in source order: i first)
add esi, 8          ; s += 8
cmp ebx, N
jl  loop_body
```

If `s += 8` is moved into the body:

```c
for (; i < N; i += 2) {
    body...
    s += 8;            // RC shape
}
```

Watcom emits `add esi, 8` at the *end of the body* (before the
`add ebx, 2` in the step clause), reversing the increment pair
order and shifting all subsequent bytes by 4 (the size of one
`add reg, imm8` plus its encoding overhead in cascade).

### Combined

Both levers compound: Lever A fixes which register is `i` and
which is `s`; Lever B fixes the order of the two `add` instructions
at the bottom.  Without both, even a perfectly aligned body diffs
because each indexed access (`mov al, [edi + esi + 1]`,
`mov [ebx + ebp + 0x3e80], al`, etc.) differs by 1-3 bytes of SIB
encoding per row.

### Discovery

`convert256_to_256xscreen` (114 b @ 0x25686) closed 96 b → 0 b
in one commit (`036ecda`) by changing

```c
s = 0;
for (i = 0; i < 0x3e80; i += 2) {
    dst[i]            = src[s];
    dst[i + 0x3e80]   = src[s + 1];
    /* ... 6 more parallel writes ... */
    s += 8;
}
```

to

```c
i = 0;
s = 0;
for (; i < 0x3e80; i += 2, s += 8) {
    dst[i]            = src[s];
    /* ... unchanged body ... */
}
```

Verified-on commit: `036ecda fix(lib32): convert256_to_256xscreen byte-exact`.

### Lever A corollary — stable binding, emission-order-only residue

Lever A above flips the *register binding* (a whole-function Rule-28
look).  But there is a milder, very common sub-case: when each loop
variable's register is already pinned by **use-order** in the body
(e.g. `py` is read first in the body so it lands in ESI, `idx` second
so it lands in EDI, regardless of init order), the binding does NOT
flip.  What still tracks source assignment order is the **emission
order of the prologue `xor reg,reg` zero-inits**.

So a function can be byte-exact *except* for two adjacent prologue
instructions being swapped:

```asm
PS:   xor esi, esi   ; py = 0
      xor edi, edi   ; idx = 0
RC:   xor edi, edi   ; idx = 0   <-- emitted first
      xor esi, esi   ; py = 0
```

This is a standalone ≤2-byte residue (the two `xor` opcodes are
identical, only their order differs).  Fix it by writing the plain
`= 0` assignments in the SAME order PS zeroes the registers — here
`py = 0;` BEFORE `idx = 0;`.  No body change, no register flip.

Diagnostic: the *entire* function matches except a swapped pair of
adjacent `xor rA,rA` / `xor rB,rB` in the prologue, and `decomp-verify
-v` prints `Regalloc: register layout matches PS — the diff is OUTSIDE
the regalloc model`.  When you see that line together with a swapped
prologue-xor pair, reorder the zero-inits before reaching for anything
harder.

Won `setup_svga_refresh_data` (refresh.c) — last 2 b → 0 b by moving
`py = 0;` ahead of `idx = 0;` (the body had already pinned ESI=py /
EDI=idx by use-order, so only the xor pair was out of order).

### When to apply

  * Two or more parallel counters initialized to zero (or to a
    matching initial value) and stepped together in a tight loop.
  * Whole-function `Reg swap` shows up in `decomp-verify -v` between
    the two counter registers, especially when paired with a
    `replace PS: add R1, K1   RC: add R2, K1` row a few bytes
    apart (often delete/insert in the diff).
  * The body has no early-exit branches between the two
    counter updates — pure parallel stride.

### When NOT to apply

  * Single counter — Lever A has nothing to disambiguate.
  * The step values differ by something other than a constant
    (e.g. `i += stride` where stride is a variable); Watcom
    materializes the variable, breaking the simple `add reg, imm8`
    pattern this rule targets.
  * The body conditionally skips one of the parallel updates —
    moving such an update into the for-step changes semantics.


## Rule 80 — `FP_SEG((void __far *)p)` is the canonical way to read DS in C

For DPMI/segmented-mode helpers that need the current DS register
value (typically to populate `struct SREGS` for `int386x`), the only
1995-era C idiom that produces a single `mov edx, ds` is:

```c
sr.es = FP_SEG((void __far *)&some_global);
```

i86.h declares `FP_SEG` as a pragma-aux intrinsic in flat-386 mode:

```c
unsigned short FP_SEG( void __far * );
#pragma aux FP_SEG = parm caller [eax dx] value [dx];
```

Casting a near pointer to `__far` materializes a 48-bit far pointer
whose segment portion comes from the runtime DS register.  Watcom
expands this inline as:

```asm
mov edx, ds          ; segment portion of __far ptr
mov eax, 0xdeadbeef  ; offset (the original ptr value)
                     ; FP_SEG returns the seg portion (in dx)
```

The `mov eax, ...` is dead code if you only consume `FP_SEG`'s
return value, but it's emitted regardless because the pragma's
`parm caller [eax dx]` signature forces both halves of the far ptr
to be set up.  This costs one extra `mov eax, imm32` (5 bytes) per
call site.

**Alternatives that do NOT work:**

  * `segread(&sr)` is an `extern` function call in Watcom 10.0a's
    i86.h (NOT a pragma), so it emits a `call segread_` not the
    inline `mov edx, ds`.  PS source visibly avoids `segread` when
    only `sr.es` (or any single field) is needed.
  * Reading from `extern int _ds` (declared with `#pragma aux _ds "*"`)
    is a MEMORY load from the C2 `_ds` global, not a register read.
    `_ds` happens to be a real BSS slot at 0x14144 in PS.EXE; reading
    it gets a stale value, not the live DS register.
  * Inline assembly via `__asm` blocks isn't 1995-era for Watcom 10.0a's
    32-bit C and gets stripped by the compiler in our build.
  * Custom `#pragma aux readDS = "mov ax, ds" value [ax]` declarations
    are pragma-aux machinery that PS source clearly didn't use (no
    such pragma appears in symbols.json's module-local pragma table).

### Discovery

`get_dos_memory` (117 b @ 0x28579) needed `sr.es = (DS register)` to
set up DPMI int 0x31 fn 0x500.  Three alternatives were tried:

  1. `segread(&sr); sr.es = sr.ds;` — emits a `call segread` (six-reg
     fill, 26 bytes) instead of inline `mov edx, ds`.  Diff: 58 b.
  2. `sr.es = (unsigned short)_ds;` (with `extern int _ds; #pragma
     aux _ds "*"`) — loads from data segment, doesn't read DS.
     Diff: 43 b (improved but wrong addressing).
  3. `sr.es = FP_SEG((void __far *)&memory);` — emits exactly
     `mov edx, ds; mov word ptr [sr.es], dx` matching PS.  Diff: 0 b.

Verified-on commit: `c0f9a62 fix(lib32): get_dos_memory byte-exact`.

### When to apply

  * DPMI / int386x setup code where one field of `struct SREGS` needs
    the current segment register value.
  * Watcom-10.0a-era flat-mode code that has a `mov edx, ds` (or
    `mov ax, ds`) followed by a memory store of `dx`/`ax`.

### When NOT to apply

  * If the source needs ALL six segment registers, `segread(&sr)`
    is appropriate — emits the right sequence of `mov word [sr.X], es`
    style loads.  PS uses `segread` in those cases.
  * If the code only needs to compare segments (`sr.es == sr.cs`)
    without populating from a register, no FP_SEG needed.


## Rule 81 — Named byte-temp `c` pins regalloc; double-load to free it

A widespread pattern in copy/scan loops:

```c
while ((c = src[i]) != 0) {
    *out++ = c;
    i++;
}
*out = c;
```

The named `char c;` temp keeps BL alive across the entire loop AND the
post-loop `*out = c;` store.  Watcom's regalloc treats `c` as a
strong-live local pinned to EBX (the only callee-save byte-capable
register under __watcall).  That pressure cascades: `i` (the int
counter) gets pushed onto EDX, leaving `out` in EAX.

PS source for the same idiom uses a **double-load** form:

```c
while (src[i] != 0) {
    *out = src[i];
    i++;
    out++;
}
*out = 0;
```

There's no named `c`.  Watcom's value-numbering recognizes the two
`src[i]` reads as the same load and emits BL exactly once per
iteration.  Critically, **the post-loop `*out = 0` is encoded as
`mov [reg], bl`** because Watcom knows BL is still 0 from the
loop-exit `test bl, bl; je end` path.  No additional immediate-0
store needed.

The freed BL pressure lets the allocator choose differently for the
int counter: `i` lands in EAX (`xor eax, eax` at entry, free, since
EAX held the parm `out` originally), and `out` moves to EDX
(`mov edx, eax` at entry).

### Asm contrast

Named-`c` shape (RC, 23 b diff against PS):

```asm
push ebx
push edx              ; reserve stack slot
xor edx, edx          ; i = 0 in EDX
mov bl, [edx+src]     ; load src[i]
test bl, bl
je end
mov [eax], bl         ; *out = c (out in EAX)
inc edx               ; i++
inc eax               ; out++
jmp loop
end:
mov [eax], bl         ; *out = c (final NUL via BL=0)
```

Double-load shape (PS, byte-exact):

```asm
push ebx
push edx              ; reserve stack slot
mov edx, eax          ; out -> EDX
xor eax, eax          ; i = 0 in EAX
mov bl, [eax+src]     ; load src[i]
test bl, bl
je end
mov [edx], bl         ; *out = src[i] (Watcom CSE'd the load)
inc eax               ; i++
inc edx               ; out++
jmp loop
end:
mov [edx], bl         ; *out = 0 (BL still 0 from loop exit)
```

Same byte count, same prologue, different register assignment.  The
2-byte `mov edx, eax` at entry is "paid back" by saving on later
re-encoding.

### Discovery

`out_format_buffer` (37 b @ 0x26AF5) — 60+ cgex trials over pragmas,
calling conventions (`__cdecl`, `__stdcall`, `__pascal`, `__fastcall`,
`__saveregs`, `__loadds`, `__far`), compile flags (`-3r`, `-5r`,
`-ol`, `-os`, `-ot`, `-oa`, `-oh`, `-oi`, `-or`, `-ox`, `-d1`, `-d2`,
`-zc`, `-zm`, `-zp[1-4]`, `-fp[c3]`, `-zw`, `-zu`, `-bm`, `-bt=nt`,
`-od`, `-j`), memory models (`-ms`/`-mm`/`-mc`/`-ml`), header
inclusion (`<i86.h>`, `<conio.h>`, `<string.h>`, `<stdio.h>`),
`register` keyword on parm/local, `_Packed`, `volatile`, `const`,
type widening (`long i`, `short i`, `unsigned char i`), return-type
changes (`int`, `char *`), and structural variants (for-loop,
do-while, K&R-style, alias to local pointer, addr-of, extra unused
uses, scope-blocking) all FAILED to flip the swap.

What worked: **remove the named byte-temp entirely**, use the
expression `src[i]` directly in both the loop test and the store.
Won out_format_buffer (-23 b → 0 b in one commit).

Verified-on commit: `b9b8028 fix(lib32): out_format_buffer byte-exact`.

### When to apply

  * Source has `char c;` (or `unsigned char c;`) plus a `(c = src[i])`
    assignment in a loop test.
  * The loop body uses `c` directly (as a value, not just a check).
  * A post-loop store `*out = c;` exists that depends on the final
    loop value of `c`.
  * Diff shows whole-function EAX↔EDX swap for the int counter and
    pointer parm, with no other functional differences.

### When NOT to apply

  * `c` is referenced AFTER the post-loop store (in which case
    Watcom needs a stable temp).
  * The loop body has more than one different use of `c` that
    couldn't all CSE to a single load (e.g. an arithmetic compute
    that modifies the byte).
  * The body has side-effecting calls between the load and the
    store — `format_buffer[i]` could change between the test and the
    body, breaking the CSE assumption.

### Why it works (Watcom internals)

Watcom 10.0a's CSE pass (in `bld/cg/c/cse.c`) recognizes identical
indexed loads with no intervening writes to the base and folds them
into one load with the result kept in a register.  A named local
`c` short-circuits this: the explicit assignment `c = ...` creates
a name-bound temp, and Watcom treats `c`'s definition as a separate
live-range that competes with `i` and `out` for callee-save slots.

The byte-typed nature of `c` means it MUST be in a low-byte-capable
register (EAX, EBX, ECX, EDX).  Combined with EBX being the only
callee-save with low-byte form (under __watcall after EAX/EDX/ECX),
EBX gets pinned for `c`.  Then `i` and `out` compete for the
remaining usable callee-saves (EDX from parm.used minus modify).

Removing `c` lets Watcom treat the two `src[i]` loads as a single
CSE'd computation whose result lives transiently in BL.  BL is no
longer pinned across the entire loop — it's recomputed each iter
naturally, freeing the allocator to make different choices for the
two int-typed roles (`i` counter and `out` pointer).


## Byte-copy loop form catalog (Rule 81 family)

Empirical mapping of C source loop forms to Watcom 10.0a `-bt=dos
-mf -4r -s` asm output, all for the canonical "copy bytes from
indexed source to pointer dest until NUL" idiom.  Derived from
60+ cgex trials on `out_format_buffer` (see
`docs/codegen-experiments/out_format_buffer.py`).

Common context: function `void f(char *out)` with the prologue
`push ebx; push edx` and a parm `out` arriving in EAX.

### Form A — named byte-temp, while-test-assign

```c
void f(char *out) {
    int i = 0;
    char c;
    while ((c = src[i]) != 0) {
        *out++ = c;
        i++;
    }
    *out = c;
}
```

Asm shape (this is what RC emits "naturally"):

```asm
xor edx, edx                 ; i=0 in EDX (Watcom keeps out in EAX, free)
mov bl, [edx + src]          ; c = src[i]
test bl, bl
je end
mov [eax], bl                ; *out = c
inc edx                      ; i++
inc eax                      ; out++
jmp loop
end:
mov [eax], bl                ; *out = c (BL=0 from exit test)
```

Key regalloc: `out → EAX, i → EDX, c → EBX (BL)`.

### Form B — no named temp, double-indexed-load

```c
void f(char *out) {
    int i = 0;
    while (src[i] != 0) {
        *out = src[i];
        i++;
        out++;
    }
    *out = 0;
}
```

Asm shape (this is the PS shape):

```asm
mov edx, eax                 ; out → EDX (2-byte cost)
xor eax, eax                 ; i=0 in EAX (free)
mov bl, [eax + src]          ; CSE'd: single load of src[i]
test bl, bl
je end
mov [edx], bl                ; *out = src[i] (same BL)
inc eax                      ; i++
inc edx                      ; out++
jmp loop
end:
mov [edx], bl                ; *out = 0 (BL=0 from exit test)
```

Key regalloc: `out → EDX, i → EAX, c-transient → BL`.

The 2-byte cost of `mov edx, eax` at entry is exactly offset by
identical-length encoding in the body; **same total size, different
register choices**.

### Form C — pure pointer iter (strcpy-like)

```c
void f(char *out) {
    char *p = src;
    char c;
    while ((c = *p) != 0) {
        *out++ = c;
        p++;
    }
    *out = c;
}
```

Asm shape: similar to Form A but with EBX or ECX holding `p` (a
real pointer, not an index).  No `[reg + disp32]` form — direct
`[reg]` indirection.

### Form D — K&R strcpy idiom

```c
void f(char *out) {
    char *p = src;
    while ((*out++ = *p++) != 0)
        ;
}
```

Asm shape: 31 bytes total (vs 37 for Form A/B).  Compact but
DIFFERENT regalloc — neither matches PS's `out_format_buffer` shape.

### Form E — for-loop with step

```c
void f(char *out) {
    int i;
    char c;
    for (i = 0; (c = src[i]) != 0; i++)
        *out++ = c;
    *out = c;
}
```

Asm shape: similar to Form A but with `inc i` in the for-step
position (after the body, before the test).  Regalloc same as A.

### Form F — do-while

```c
void f(char *out) {
    int i = 0;
    char c;
    do {
        c = src[i];
        *out++ = c;
        i++;
    } while (c != 0);
}
```

Asm shape: 32 bytes (vs 37 baseline) — drops the entry-test branch.
Regalloc still RC-style (Form A).

### Levers that do NOT change Form A's regalloc

All of these were tested and produced byte-equal output to Form A:

  * `register` keyword on parm or local (Watcom 10.0a ignores)
  * `volatile` on i or out
  * `const` on temp or parm
  * Storage class: `static` on inner var
  * Type-width on counter: `short i`, `long i`, `unsigned int i`,
    `unsigned char i`
  * Return-type change: `int f(...)` returning 0, `char *f(...)`
    returning out
  * Statement reorder of body: `i++; out++` vs `out++; i++`
  * Block-scoping the temp inside an inner `{ }`
  * Extra unused locals/dummies
  * `#pragma aux` modify variations: `modify`, `modify exact []`,
    `modify exact [eax]`, `modify exact [eax esi edi]`
  * `#pragma aux default` modify variations
  * `#pragma aux` parm convention: `parm caller [eax]`,
    `parm caller [edx]` (semantically changes calling convention)
  * `#pragma intrinsic(strcpy)` with/without dead-code use
  * Compile flags: `-3r`, `-5r`, `-ol`, `-os`, `-ot`, `-oa`, `-oh`,
    `-oi`, `-or`, `-ox`, `-d1`, `-d2`, `-zc`, `-zm`, `-zp1/4`,
    `-fpc`, `-fpi87`, `-zw`, `-zu`, `-bm`, `-bt=nt`, `-od`, `-j`,
    `-ec=__cdecl`, `-ow`
  * Memory model: `-ms`, `-mm`, `-mc`, `-ml`, `-mh` (these change
    far/near convention but don't flip the local regalloc)
  * Header inclusion: `<string.h>`, `<stdio.h>`, `<i86.h>`,
    `<conio.h>`
  * Preprocessor defines (-D)
  * Calling convention keywords: `__cdecl`, `__pascal`, `__stdcall`,
    `__fastcall`, `__saveregs`, `__loadds`, `__far`

The ONLY lever that flips A → B is the double-load source rewrite.

### Diagnostic for picking the form

When you see a function with the asm-shape pattern:

```asm
mov edx, eax
xor eax, eax
mov bl, [eax + disp32]
...
mov [edx], bl
inc eax
inc edx
```

The source MUST be Form B (double-load, no named temp).  This is
the cd_path-class Rule 28 signature for byte-copy loops.

When you see:

```asm
xor edx, edx              ; or xor reg, reg where reg != EAX/EDX
mov bl, [edx + disp32]
...
mov [eax], bl
inc edx
inc eax
```

The source is Form A (named temp).  These two shapes are NOT
interchangeable via flags, pragmas, or qualifiers — only via the
source-level rewrite.

## Rule 82 — `if (x == 0) x = N;` pins indexed-load scratch to result register

When the source contains a struct/array indexed-field load followed
immediately by an "if-zero, replace with default" idiom whose
result is consumed as a call argument (typically `put_message`
arg 2 in EDX), Watcom merges the indexed-load scratch with the
result register and emits the in-place RMW form
`mov edx, [edx + disp32]`.  PS source for the same pattern
keeps the scratch in EAX and emits `mov edx, [eax + disp32]`.

### When you see this

`barbarian_in_region` and `empire_in_region` both presented this
exact 3-byte regalloc swap at L+19:

```asm
PS:                                  RC:
  movsx eax, word [created_army_no]    movsx edx, word [created_army_no]
  imul  eax, eax, 0xaf                 imul  edx, edx, 0xaf
  mov   edx, [eax + map_ref_field]     mov   edx, [edx + map_ref_field]
  test  edx, edx                       test  edx, edx
  jne   $+5                            jne   $+5
  mov   edx, 8                         mov   edx, 8
  mov   ebx, 0x11                      mov   ebx, 0x11
  mov   eax, 0x5d                      mov   eax, 0x5d
  call  put_message                    call  put_message
```

The sibling `raider_in_region` was already byte-exact because
its source had extra `target_x = 0; target_y = 0;` stores
between the if/else merge and the map_ref read — those stores
forced the scratch (the army base offset) into multiple uses,
making it a distinct live range from the map_ref result.

### The lever

Rewrite

```c
int map_ref;
map_ref = army_list[idx].map_ref;
if (map_ref == 0) map_ref = 8;
put_message(msg, map_ref, arg3);
```

as

```c
int map_ref;
map_ref = army_list[idx].map_ref;
map_ref = map_ref == 0 ? 8 : map_ref;
put_message(msg, map_ref, arg3);
```

### The lever is broader than "use a ternary" (measured 2026-06)

Normalization sweep on `barbarian_in_region` mapped the full
equivalence class.  What matters is **assigning the result in every
branch from a fresh (re-)evaluation** — not the `?:` token.  An
`if/else` with a double-load reaches the PS bytes just as well:

| source form | result |
|---|---|
| `x = x == 0 ? 8 : x;` (ternary reassign) | ✅ exact |
| `x = field == 0 ? 8 : field;` (ternary, field double-loaded) | ✅ exact |
| `if (field == 0) x = 8; else x = field;` (**if/else double-load**) | ✅ exact |
| `x = field; if (x == 0) x = 8;` (load-then-patch) | ✗ 3 b diff |
| `int m = field; x = m; if (m == 0) x = 8;` (temp + patch) | ✗ 3 b diff |
| `x = 8; if (field != 0) x = field;` (init-then-overwrite) | ✗ 3 b diff |

Rule of thumb: the result temp must get a **fresh SSA value on every
path** (ternary, or if/else where each arm assigns from a re-load of
the field).  The diff appears only when the field is loaded **once**
into the result and then conditionally patched — that single load lets
the indexed-load scratch reuse the result register.  So when reaching
for this lever you may use a ternary **or** an if/else-double-load;
avoid load-then-patch.

### Why it works

The two forms are semantically equivalent (and produce identical
asm except for the scratch register choice) but Watcom builds
DIFFERENT expression trees for them:

* `if (x == 0) x = N;` builds ONE statement tree where `x` is
  read, compared, and conditionally re-assigned — all sharing
  the same SSA value.  The conflict-graph merges the load
  destination with the post-test value, so when
  `CountRegMoves` (regalloc.c:457) scores the load instruction,
  it sees the in-place form `mov RES, [RES + disp]` as a save
  (res = reg_name AND op1 is an indexed memory reference whose
  base IS the temp) — count += tree->size.  Watcom assigns
  scratch=EDX (= the call-arg constraint reg) to capture that
  save, producing the RMW form.

* `x = x == 0 ? N : x;` builds a TERNARY expression tree that
  produces a fresh SSA result.  The load destination is one
  temp, the ternary result is a different temp, and the call
  argument is the ternary result.  The indexed-load scratch
  no longer benefits from sharing a register with the
  call-arg constraint, so Watcom picks EAX (DoubleRegs first)
  for the scratch and emits the PS-matching three-instruction
  sequence.

### When NOT to apply

* The C source MUST genuinely have an "if-zero, replace with N"
  shape.  The fresh-evaluation rewrite (ternary or if/else
  double-load) is only a valid lever for that specific idiom;
  it doesn't apply to generic field-load-then-consume patterns
  (e.g. `barbarians_drop_by_city` has the same EAX/EDX swap but
  no zero-check — a different lever is needed there).

* When the function's STRUCTURE already keeps the scratch alive
  across multiple uses (as in `raider_in_region` with its
  redundant target_x/y=0 stores), the merge doesn't happen
  and no fix is needed.

### Detector

`c2/commands/rule_hints.py` → `_find_rule_82_pattern` +
`detect_rule_82`.  Signature:

  * PS row N    : `movsx <scratch_reg>, word ptr [disp32]`
  * PS row N+1  : `imul <scratch>, <scratch>, imm`
  * PS row N+2  : `mov <result_reg>, [<scratch> + disp32]`
                 where scratch != result
  * PS row N+k  : `test <result>, <result>` + `jne` +
                 `mov <result>, imm`

  * RC row M    : same `movsx` but with scratch == result
  * RC row M+2  : `mov <result>, [<result> + disp32]` (RMW)

PS/RC `result_reg` must match (it's the call-arg constraint).

Won: `barbarian_in_region` (3→0 b), `empire_in_region` (3→0 b).

Discovered via `docs/codegen-experiments/barbarian_in_region.py`
trial `S_test_after_call` (the 21st variant) after 20 other
source-shape mutations all failed to flip the swap.

## Rule 83 — Compound `&=` over `=&` for byte-load + mask: stable evaluation order

Watcom 10.0a's regalloc tie-break can pick the "wrong" register for the
byte half of `val = byte_load(c) & mask;`, causing a whole-row cascade
where PS loads the byte into EAX and the mask into EBX, but RC swaps
them.

### Pattern

PS asm (`get_range1` inner loop body):
```
mov  al, [esi + eax + 0xa]   ; load byte → AL  (then widen)
and  eax, 0xff               ; Z1to4 widen
xor  ebx, edi                ; clear EBX (high part)
mov  bl, [esp + 4]           ; load mask → BL
and  eax, ebx                ; val = byte & mask
```

RC emits the equivalent operations but with EAX↔EBX swapped — `mov al,
mask` first, then `mov bl, byte_load`, then `and eax, ebx`. Same
result, opposite register identity, 46-byte cascade through the loop
(short jumps shift by 3 bytes).

### Source-level lever

Rewrite the AND expression from binary form `val = (byte_load) & mask;`
to compound-assignment form:

```c
val = byte_load;
val &= mask;
```

The compound `&=` forces the IR to evaluate the byte load INTO `val`
first (Watcom's destination-of-assignment is the first conflict to be
allocated), and only afterwards perform the AND in place. That pins
the byte to EAX (since `val` lives in EAX) and lets the mask flow to
EBX naturally.

Won: `get_range1` (46→0 b), `get_range3` (46→0 b, plus the
CC_FPU_FLAG → CC_ENTERTAIN macro-name fix detailed below).

### When to apply

* The diff hint is **`Reg swap` + `Rule 49b` near a single-line
  expression `result = mask_load(...) & mask;`** and the swap is
  whole-statement (loads, AND, store all flipped).
* The result variable is used in a subsequent comparison (e.g.
  `if (val > best) best = val;`), so it needs a stable register
  identity across multiple uses.
* PS asm shows the byte load resolving to EAX first, mask second.
* Easy to spot: the binary form `=...&...` reads almost identically
  to the compound `=; &=` form in C, but only the latter pins the
  evaluation order in Watcom 10.0a.

### Bonus: macro-name mismatch in get_range3

While verifying the lever on `get_range3`, the residual 2 byte diff
(after applying compound `&=`) revealed the underlying source was
using the **wrong cell field macro**: `CC_FPU_FLAG(c)` is `c[11]` but
PS reads `c[12]` which is `CC_ENTERTAIN`.  The callers
(`q_theatre/colosseum/circus` with 2-bit masks 0x3/0xc/0x30 — packed
entertainment fields) confirm the field is entertainment, not
fpu_flag. **Macro-name typos in field accessors are a separate class
of "type mismatch" that surface as 1-byte disp diffs in PS asm; if
you see a `[base + N]` vs `[base + N±1]` row with matching mnemonic,
the source's field-accessor macro is wrong.**

### Detector

Not currently auto-detected.  Look for: a Reg-swap-heavy diff in a
function whose body has `var = COMPLEX_LOAD(...) & SIMPLE_OPERAND;`
where COMPLEX is a struct/array/macro load and SIMPLE is a parm or
local of byte type.  Try the compound `&=` rewrite first; if the
swap closes but a 1-2 byte residue remains at a `[reg + N]` operand,
audit the field macro against the PS disp.

## Rule 84 — Named byte-temp reused across sequential byte reads triggers `mov+and` (in-place) Z1to4 over `xor+mov` (clear-first)

Watcom's `rCLRHI_R` in `bld/cg/c/split.c` (the lowering used after
regalloc for Z1to4 conversions on i486 / OptForSize<=50) has **two
forms**:

* **Form 1 (and-form)**: `mov dl, [m]; ...; and edx, 0xff` — 6+6 bytes
  for the conversion, but enables follow-up byte reloads via `mov dl,
  [m]` to share the same EDX (upper bytes stay 0 from the AND).
* **Form 2 (clear-first)**: `xor edx, edx; mov dl, [m]` — 2+6 bytes,
  shorter but each independent reload needs its own xor.

The choice depends on rCLRHI_R's operand-overlap analysis at split
time, which itself depends on regalloc decisions earlier.

### Pattern

Source with three sequential byte reads from different fields,
each into a fresh block-scope local:

```c
if (CM_KIND(ref) < 8
 && (CM_EDGE_BITS(ref) & 0x80) != 0) {
    unsigned char f = CM_FIRE(ref);
    if (--f != 0) ...
}
```

emits the clear-first form everywhere — every byte load gets its
own `xor edx, edx`.  PS uses the and-form throughout, with a single
named local reused across reloads.  64 bytes of cascade diff.

### Source-level lever

Declare a single `unsigned char` local at the top of the body and
**reuse it** across sequential byte reads:

```c
unsigned char x;
x = CM_KIND(ref);
if (x < 8) {
    x = CM_EDGE_BITS(ref);
    if ((x & 0x80) != 0) {
        x = CM_FIRE(ref);
        if (--x != 0) ...
    }
}
```

The reused local pins the value to a stable register (e.g. DL within
EDX), and rCLRHI_R's "register-overlap with high part" branch fires,
emitting the and-form.  Subsequent reloads via `mov dl, [m]` keep the
upper bytes from the first `and edx, 0xff`, so no extra zero-extension
instructions are emitted.

Won: `putting_out_fire` (64→0 b — entire cascade).

### When to apply

* Source has 3+ sequential `unsigned char`-typed byte reads from
  related fields, each into its own ad-hoc local or used inline.
* Diff shows alternating `mov dl, [m]` vs `xor edx, edx; mov dl, [m]`
  patterns between PS and RC, with PS consistently the shorter form
  after the first widening.
* The sibling/adjacent function (often verified byte-exact) uses
  different scratch registers per byte (e.g. confirm_fire_target
  spreads kind→EDX, edge→EAX), and doesn't need this lever.

### Reference

* `bld/cg/c/split.c` `rCLRHI_R()` — the split-time decision.
* `bld/cg/intel/c/i86ver.c` `V_GOOD_CLR` — the verifier predicate
  that gates `R_CLRHIGH_R` on i486+ / OptForSize<=50.
* `bld/cg/intel/386/c/386conv.c` `Z1to4[]` — the conversion table.

## Rule 85 — Far-pointer return type lowers `return 3` to `xor edx,edx; mov eax,3` (edx:eax = seg:off)

> ### ⚠️ CORRECTION (2026-06-22): `xor edx,edx; mov eax,N` is NOT always a return — it can be a DEAD STORE.  `pos_sound`/`neg_sound` are `void`.
>
> The Ghidra decompile of PS.EXE (`ghidra-cli decompile pos_sound` /
> `neg_sound`) renders **`void f(void)`** for both — they return
> NOTHING.  Their `xor edx,edx; mov eax,3` at L314 is a **dead store**
> (`if (set_sample_file(...) == 0) r = (char __far *)3;` — an error code
> set then discarded; start_sample is called UNCONDITIONALLY and the
> function returns nothing), which PS's 10.0a kept but our build's DSE
> removes.  A prior session (commit ea1ad6f5) read this dead store as a
> far-ptr return and mis-declared both `char __far *`.  That was
> actively HARMFUL: the forced `return r;` of an uninitialised `r`
> made r live-from-entry, RegAlloc exiled it to a callee-save that sat
> in the RISCify rover's except mask, and every `S_dig[ds]` parm-push
> shifted one register late — an 18-byte "rover rotation" that was
> PURELY an artifact of the wrong return type.  Declaring `void` fixed
> it: **neg_sound -> byte-exact, pos_sound 27b -> 19b** (the 19b is the
> irreducible dead store).
>
> **The discriminator** (do this before declaring a far-ptr return on
> the strength of an `xor edx,edx; mov eax,N`):
> 1. **Ghidra return type** — does it render a USED return value
>    (`undefined4`/`int`, e.g. `return uVar2`) or `void`?  Ghidra void
>    = the value is never consumed.  `start_sound`/`start_sequences`
>    are `undefined4`/`int` (real returns -> far-ptr is right, both
>    byte-exact); `pos_sound`/`neg_sound` are `void`.
> 2. **The byte test** — declare `void` and rebuild.  If the bytes
>    IMPROVE (the rover shift disappears), the value was a dead store
>    and the function is void.  If they REGRESS, it was a real return.
>    This is the only fully-reliable test: `inferred-sig` says
>    `has_return=False` for BOTH classes (it can't see the AIL-leak
>    return), and Ghidra "void" only means "return unused" — neither
>    alone is conclusive, the rebuild is.
>
> Bottom line: a 2-register `xor edx,edx; mov eax,N` followed by MORE
> code on the same path (not a tail `jmp epilogue`) is a DEAD STORE,
> not a return.  Only the tail-position form is a real far-ptr return.

### Pattern (PS.EXE)

A function returning a constant via `xor edx,edx; mov eax,N` — the
canonical-looking "8-byte (I8) constant load" — when the function has
no 64-bit type in sight (Watcom 10.0a has none).  Seen in the
`start_sound` / `start_samples` / `start_sequences` family that share
the far-pointer-return epilogue at `0x118df` (but NOT pos_sound/
neg_sound — see the correction above):

```
00011F1F  31d2          xor  edx, edx       ; far-ptr segment = 0
00011F21  b803000000    mov  eax, 3         ; far-ptr offset   = 3
```

### What it actually is

**A far pointer return value.**  Under `-mf` (flat) a `char __far *`
/ `void __far *` is a 48-bit `edx:eax` pair (edx = segment, eax =
offset).  `return 3;` from a far-ptr-returning function converts the
`int 3` to the far pointer `0000:00000003`, emitting exactly
`xor edx,edx (seg) ; mov eax,3 (off)`.  This is NOT a `long long` /
`__int64` (those don't exist until Watcom 11.0) and NOT a compiler-
version artifact: building the 10.5 and 10.6a containers and
recompiling gives a **byte-identical .obj** to 10.0a (md5 `aa1356db`
for the plain `int` return, `f0943768` for the far-ptr return).  The
shared epilogue (`pop ebp; jmp <chain>`) is the far-ptr-return
epilogue class — sibling functions ending in `xor edx,edx; mov eax,1`
etc. are returning far pointers too.

### How to confirm

```c
extern int g(int);
char __far *f(int a) { if (g(a) == 0) return 3; g(a+1); return 0; }
/* -> xor edx,edx; mov eax,3   on the ==0 path */
```

### Source-shape constraint (2026-06-10): E1096 forbids mixed returns

10.0a rejects `return;` mixed with `return N;` in the same function
(E1096, hard error — verified for explicit `int`, implicit-int, and
type-less K&R definitions alike).  Therefore every Rule 85 family
member whose PS bytes show bare early exits (je/jne straight to the
epilogue, no EAX setup) PLUS valued `return N;` sites MUST have been
written as a guard wrapper with fall-off-end, not early returns:

```c
char __far *start_samples(void)
{
    if (samples_running == 0 && c2inf.samples_on != 0) {
        if (readfile(...) == 0) return (char __far *)4;
        ...
    }
}   /* fall off the end — W107 warning only, matches PS's missing
       success-path EAX setup */
```

(start_samples' first two exits: `jne` on samples_running then `je` on
samples_on — exactly the `&&` operand order above.)  Confirmed the
fall-off also explains start_sound's missing `xor eax,eax` (RC-only
row): PS's success path is NOT `return 0;`, it falls off the end.

### MK_FP error constants + the implicit-int blocker (2026-06-10)

Two additions from the start_sequences root-cause session:

* **`mov edx,1; mov eax,2` (nonzero segment!) = `(char __far *)MK_FP(1, 2)`**
  — oracle-proven: a plain `(char __far *)2` always gives `xor edx,edx`.
  When a Rule 85 site shows a NONZERO edx immediate, the original wrote
  `MK_FP(seg, off)` (include `<i86.h>`).  Also: the seg-zero write is
  VALUE-POOL ELIDED when a preceding `test reg,reg` proved the register
  zero (start_samples' `return 2` after `int s = S_dig[ds]; if (s == 0)`
  emits only `mov eax,2` — the `int s` local is required for the
  `test edx,edx` form AND the elision).
* **E1062 implicit-int blocker**: if any caller precedes the definition
  in the file and there is no prototype, the call creates an implicit
  `int` declaration and the far* definition then HARD-FAILS E1062.  The
  original must have had file-top prototypes.  This — not codegen — is
  why far* "couldn't be restored" in pcsound.c.
* **PS pushes/pops EDX in far*-returning functions** (10.0a quirk): the
  popped seg half is garbage at ret; callers discard it.  Do NOT use
  push-set differences to rule far* in or out.
* **The remaining far* funnel residue is IL-level**: our guard-wrapper
  fall-off compiles to an uninitialized-but-live join read (retval temp
  live across every call → exiled to callee-saves + homing MOVs); PS has
  per-site EDX:EAX with no join read.  The suppressing source shape is
  an open question — do NOT permute registers, find the IL lever.

### Machine levers (2026-06-10)

The whole family is now machine-detected:

* binir `farptr_ret_const` (pops+ret follows: certain) /
  `regpair_const_exit` (exit jmp: ambiguous) decode the pair into the
  LITERAL source expression, including nonzero segments
  (`MK_FP(seg, off)`).
* decomp-verify resolves the ambiguous form through symbols.json
  (`tail_merge.classify_regpair_exit`): `resolved: RETURN` vs
  `resolved: ARGS`.  Corpus census: **5 returns** (this pcsound family)
  vs **58 arg-pair merges** — `mov edx,K; mov eax,M; jmp <shared call
  tail>` where ComTail (FindCommon compares raw object code, so it
  merges call sequences as readily as epilogues) factored out identical
  call sites: get_census, get_new_tribute, show_* UI panels.  Those 58
  sites are a separate lever: the RC source must produce IDENTICAL call
  shapes at every merged site for the factoring to reproduce.
* `frame_hints.detect_retval_funnel` flags the RC-side join-read exile
  (homing pair from callee-saves at one exit).

### Caveat — not always worth restoring

Identifying the far-ptr return type explains the bytes, but
restoring it is only a *byte-exactness* win when the function's
callers and tail-merge tolerate it.  For `pos_sound`/`neg_sound` it
is a net regression: `neg_sound` tail-merges into `pos_sound` and is
byte-exact as `void`, so switching the return type breaks the merge
(0→63 b); and even `pos_sound` alone only reaches 16 b (vs 13 b void)
because Watcom keeps the far-ptr return value alive across the
trailing call in callee-saves (`esi:edi`) while PS allocates it to
the caller-saved return pair `edx:eax` and lets the call clobber it
(genuinely dead — returns garbage).  That edx:eax-and-discard
allocation is a regalloc tie-break we could not force from C source.
See the long comment over `pos_sound` in `decomp/src/pcsound.c` and
`docs/codegen-experiments/possound.py`.

### Discovery

Found while disproving the "binary was built with Watcom 10.5/10.6"
hypothesis: the cross-version sweep (10.0a/10.5/10.6a byte-identical)
ruled out a compiler-version cause for the `xor edx,edx` and
relocated it to the far-pointer return type.  See
`docs/compiler-version-confirmation.md` and
`docs/compiler-identification.md` §13.

## Rule 86 — Iterate over the parameter itself; keep a named copy for the saved value

When a function receives a pointer parameter, then both (a) walks it
through a loop *and* (b) passes the **original** pointer to a callee,
Watcom binds the **incoming parameter register** to whichever C
variable is the moving pointer in the loop — and spills the other to
a second callee-save register via a copy at entry.  The order of the
two entry `mov`s (and hence which physical register ends up holding
the loop pointer vs the saved copy) is decided by which variable is
the *parameter* and which is the *derived copy*.

### The asm

`control_icons(struct icon_rec *icons, int count)` walks `icons` and
calls `de_toggle_all_icons(icons_original, count)`:

```asm
; PS:
89 c3   mov ebx, eax     ; ebx = icons (the parameter)  ← loop pointer
...
89 de   mov esi, ebx     ; esi = saved copy             ← arg for the call
```

```asm
; recomp (before fix):
89 c6   mov esi, eax     ; esi = icons                  ← saved copy
...
89 f3   mov ebx, esi     ; ebx = loop pointer
```

Both are semantically identical (ebx = moving pointer, esi = saved),
but the entry copy chain runs in opposite directions: PS routes the
parameter into EBX (the mutated pointer) and copies EBX→ESI; recomp
routes the parameter into ESI and copies ESI→EBX.  Two `mov` modrm
bytes differ (`c3`/`de` vs `c6`/`f3`).

### The C lever

Make the **parameter variable itself** the moving pointer, and
introduce a separate named local for the saved copy used by the
callee:

```c
/* PS-matching: parameter is the moving pointer */
struct icon_rec *base = icons;          /* saved copy → esi */
for (i = 0; i < count; i++) {
    if (icons->x <= mouse_x && ...) {   /* icons walks → ebx */
        de_toggle_all_icons(base, count);
        ...
        icons->callback();
        return i + 1;
    }
    icons++;
}
```

vs the non-matching shape that keeps the parameter as the *saved*
value and walks a derived copy:

```c
/* non-matching: derived copy walks, parameter stays put */
struct icon_rec *p = icons;
for (...) { ... de_toggle_all_icons(icons, count); ... p++; }
```

Watcom keeps the parameter in the register it is mutated in, so the
variable you advance with `++` is the one that inherits the incoming
parameter register.  Flip which variable is advanced to flip the
entry copy direction.

### Discovery

`control_icons` (controls.c), 2 b → 0 b.  The diff was flagged as
`2x Reg swap` (ebx↔esi) and was source-shapeable (Rule 28a first-use
order) by choosing which variable carries the `++`.

## Rule 87 — A spurious `else return;` on an unreachable branch flips callee-save register selection

When a dispatch has already constrained a variable to a small set of
values (e.g. two earlier guards prove `pointer_mode` is 2 or 3), a
trailing `else { return; }` on the *unreachable* remaining case is not
free: it adds a control-flow edge that changes Watcom's register
pressure analysis and can flip which physical register the allocator
picks as a callee-save — typically `edi` ↔ `ebp`.

### The asm

`mouse_follow_cohort` after the guards `if (pointer_mode <= 1) return;`
`if (pointer_mode >= 4) return;` dispatches on `== 2` / `== 3`:

```c
/* non-matching: explicit else-return on the dead branch */
if (pointer_mode == 2)      dist = get_nearest_army_to_track(...);
else if (pointer_mode == 3) dist = get_tracking_army_distance(...);
else                        return;          /* unreachable */
if (dist >= 0x18) { ... }
```

Watcom pushed `ebp` (RC) where PS pushes `edi`:

```
PS:   push ebx; push ecx; push edx; push esi; push edi
RC:   push ebx; push ecx; push edx; push esi; push ebp   ← Rule 28a swap
```

The PS disasm shows the dead path simply falls through into the
`dist >= 0x18` check with `dist` (EDX) uninitialised — i.e. PS source
had **no** `else return;`.  Dropping it:

```c
/* PS-matching: dead branch falls through, dist left undefined */
if (pointer_mode == 2)      dist = get_nearest_army_to_track(...);
else if (pointer_mode == 3) dist = get_tracking_army_distance(...);
if (dist >= 0x18) { ... }
```

flips the allocator back to `edi`, matching PS's prologue/epilogue
push set exactly.

### Why it matters beyond the prologue

The callee-save set is the gate for cross-function tail-merge
(Rule 42).  PS's many early-return `jmp`s tail-merge **backward** into
the preceding function's `pop edi;pop esi;pop edx;pop ecx;pop ebx;ret`
epilogue (2-byte `eb` short jumps).  If the allocator picks `ebp`
instead of `edi`, the epilogue is `pop ebp;…` and the function can no
longer share that tail — so getting the callee-save set right is a
prerequisite for the tail-merge to even be reachable.

### Discovery

`mouse_follow_cohort` (action.c): 205 b → 196 b, callee-saves aligned
(`ebx ecx edx esi edi`), Prologue-hint `Callee-save SWAP edi↔ebp`
cleared.  The residual 196 b is a separate ComTail **anchor-direction**
problem (RC merges the shared epilogue forward; PS keeps it inline in
`scroll` and jumps back) — not fixable via this rule.  Detected via the
`Prologue hint: Callee-save SWAP` line in `decomp-verify -v`.

### Related: same swap, different cause (Rule 1)

Not every edi↔ebp swap is a dead branch.  `select_filename`
(loadsave.c) showed the identical `PS uses edi where RC uses ebp`
prologue hint with **no** dispatch/dead-branch at all (12 b → 0 b).
The cause there was a cached `int mx = mouse_x;` read three times: the
cache's live range bumped the long-lived `old_pointer_mode` into ebp.
Inlining the three `mouse_x` reads (Rule 1) freed the pressure and the
allocator picked edi, matching PS byte-for-byte.  So when the hint
fires, check for a multiply-read cached local **first** (cheap, often
the cause), then the dead-branch pattern.

## Rule 88 — Array / struct-array addressing-mode map (stride factoring + zext idiom)

The single most common diff source in indexed-data code is getting
the **addressing mode** and **byte-widening idiom** wrong.  Both are
mechanical functions of three inputs: the element **stride**, the
element **type** (width + signedness), and whether the index lands
in a **free** register or must reuse the destination.  This rule maps
the complete decision tree so you can predict the asm from the C
source (or recover the C source from the asm) without guessing.

All of the following were derived by isolating single accesses with
`c2 cgex` (see `docs/codegen-experiments/array-access-map.py`) and
confirmed against byte-exact PS functions (`get_new_sslot`,
`select_a_unit`, `plague_an_atom`).

### 88a — Scalar array read `arr[i]` → int (variable index in EAX)

When the index arrives in EAX and the result returns in EAX (so the
register is **busy**):

| Element type      | Watcom emits                                            |
|-------------------|---------------------------------------------------------|
| `int`             | `mov eax, [eax*4 + base]`                               |
| `short`           | `movsx eax, word ptr [eax*2 + base]`                    |
| `unsigned short`  | `mov ax, [eax*2 + base]; and eax, 0xffff`               |
| `char` / `unsigned char` | `mov al, [eax + base]; and eax, 0xff`            |
| `signed char`     | `movsx eax, byte ptr [eax + base]`                      |

### 88b — Same read, but the destination register is FREE

With a **constant** index, or when the result goes to a register that
isn't holding the index, the unsigned-byte/short widen flips to the
**clear-first** idiom:

| Element type      | Busy dest (88a)                  | Free dest                        |
|-------------------|----------------------------------|----------------------------------|
| `char`/`uchar`    | `mov al,[m]; and eax,0xff`       | `xor eax,eax; mov al,[m]`        |
| `unsigned short`  | `mov ax,[m]; and eax,0xffff`     | `xor eax,eax; mov ax,[m]`        |
| `signed char`     | `movsx eax, byte ptr [m]`        | (same — movsx needs no clear)    |
| `short`           | `movsx eax, word ptr [m]`        | (same)                           |

This is the mechanism behind **Rule 49**: the `& 0xff` source mask
**always** forces the busy-dest `mov; and` form (even when the
register is free), whereas a bare read or `(unsigned char)` cast uses
`xor`-first **whenever the destination is free** and falls back to
`mov; and` only when the index occupies the destination.  Practical
consequence: in variable-index context you **cannot** tell `arr[i]`,
`arr[i] & 0xff`, and `(unsigned char)arr[i]` apart — all three emit
`mov al; and eax,0xff`.  The `& 0xff` vs cast distinction is only
observable when the register is free.

### 88c — Struct-array element address: stride factoring

For `tbl[i].field` where `sizeof(tbl[0]) == stride`, Watcom strength-
reduces the `index * stride` multiply into `index * odd × SIB_scale`:

  * **SIB_scale** = the largest power of two that divides `stride` and
    is `≤ 8` (the x86 SIB scale cap), **unless** `stride` is itself a
    pure power of two:
      * pure pow2 `≤ 8` → SIB scale = stride, **no multiply** at all
        (e.g. stride 8 → `[eax*8]`).
      * pure pow2 `> 8` → single `shl eax, log2(stride)`, SIB scale 1
        (e.g. stride 16 → `shl eax,4; [eax]`).
  * **odd cofactor** `m = stride / SIB_scale` is materialised with a
    shift+add/sub chain (multiply strength reduction at OptSize=50):
      * `i*3` → `mov edx,eax; shl eax,2; sub eax,edx`
      * `i*5` → `mov edx,eax; shl eax,2; add eax,edx`
      * `i*7` → `mov edx,eax; shl eax,3; sub eax,edx`
  * the field offset is folded into the SIB **disp8/disp32**.

Worked strides:

| stride | factoring | index calc           | load                       |
|-------:|-----------|----------------------|----------------------------|
|   8    | 1 × 8     | (none)               | `[eax*8 + foff]`           |
|   6    | 3 × 2     | `i*3`                | `[eax*2 + foff]`           |
|  12    | 3 × 4     | `i*3`                | `[eax*4 + foff]`           |
|  20    | 5 × 4     | `i*5`                | `[eax*4 + foff]`           |
|  24    | 3 × 8     | `i*3`                | `[eax*8 + foff]`           |
|  40    | 5 × 8     | `i*5`                | `[eax*8 + foff]`           |
|  16    | pure 2⁴   | `shl eax,4`          | `[eax + foff]`             |
|   7    | 7 × 1     | `i*7` (`shl3;sub`)   | `[eax + foff]`             |

The same factored index register is **reused** across multiple field
reads of the same element (`tbl[i].a + tbl[i].b` keeps `i*odd` in EAX
and emits two `[eax*scale + foff]` loads — it does NOT recompute).

### 88d — Address-taken / multi-purpose offset → full byte offset + disp32

When you take the **address** of an element or field (`&tbl[i].f`,
`use(tbl[i].name)`, or `strcpy(...)` into the element), the SIB fold
is impossible — Watcom must produce a real pointer value.  It
materialises the **full byte offset** and adds the array base as a
disp32 fixup:

```
mov edx, eax
shl eax, 2
add eax, edx        ; eax = i*5
shl eax, 2          ; eax = i*20  (full byte offset)
add eax, <base>     ; disp32 fixup  → absolute element address
add eax, <foff>     ; field offset
```

This is exactly the `get_new_sslot` shape (`shl;add;shl` → `i*20`,
then `[eax + 0xd2a8]` reused for the count read/write **and** the
`strcpy` destination).  The trigger is **offset reuse for an
address**, not merely multiple reads: pure multi-read still uses the
SIB-fold form (88c).  See `docs/codegen-experiments/sslot-struct.py`.

### 88e — Writes

| Write                 | Watcom emits                                   |
|-----------------------|------------------------------------------------|
| `carr[i] = v;` (char) | `mov byte ptr [eax], dl`  (low byte, no mask)  |
| `iarr[i] = v;` (int)  | `mov [eax*4 + base], <reg>`                    |
| `tbl[i].f = v;`       | stride-factor index (88c), `mov [eax*s+foff],r`|

Char stores never mask — they just write the low 8 bits of the source
register.

### Why — verified against the OW1 (≈11.0) cg sources

The AGENTS.md caveat applies: the open-source tree is closer to a
11.0 branch than 10.0a, so the **mechanism** aligns but one **idiom**
diverges.  Where they differ, the empirical 10.0a compiler output
(via `cgex`) is ground truth.

**Stride factoring (88c) — aligns exactly.**  Two cg passes combine:

* `MulToShiftAdd()` / `Factor()` in `bld/cg/c/multiply.c` reduces the
  `index * stride` multiply to a shift+add/sub chain.  `Factor()`
  first tries the `pow2±1` trick, then a trailing-bit decomposition,
  and is **cost-gated** by `MulCost(rhs) <= cost` — i.e. only reduces
  when shift+add is cheaper than `imul` (this is the OptSize=50
  balance; `-os`/`OptForSize` shifts the cutoff, which is why the
  rule is flag-sensitive).  Produces `i*3 = (i<<2)-i`, `i*5 =
  (i<<2)+i`, `i*7 = (i<<3)-i`, etc.
* `FoldIntoIndex()` in `bld/cg/intel/386/c/386sib.c` then folds a
  trailing `shl` into the SIB scale, **capped at `sib.scale > 3`**
  (i.e. ×8 max — exactly the x86 SIB scale limit).  When the value is
  consumed as an **address** (added to a base, 88d) the fold can't
  apply, so the full byte offset stays materialised — the
  `get_new_sslot` shape.

**Zext idiom (88b) — mechanism aligns, fallback diverges.**  The
byte→dword zero-extend table `Z1to4[]` in
`bld/cg/intel/386/c/386conv.c` lists the clear-high path *first*:

```
_Un( R|M, R, NONE ), V_GOOD_CLR, R_CLRHIGH_R, RG_BYTE_DBL, ...   ; xor-first
_Un( R|M, R, NONE ), V_NO,       G_MOVZX,     RG_BYTE_DBL, ...   ; movzx
```

`R_CLRHIGH_R` is the `xor reg,reg; mov rl,[m]` idiom, gated by the
`V_GOOD_CLR` verify (`bld/cg/intel/c/i86ver.c`):

```c
case V_GOOD_CLR:
    if( op1 == result ) return TRUE;      /* reg==reg: always clearable   */
    if( !_CPULevel(CPU_486) ) break;      /* needs 486  → -4r satisfies   */
    if( OptForSize > 50 ) break;          /* default 50 OK; -os disables! */
    if( result reg overlaps BP ) break;
    return TRUE;
```

So the clear-first idiom is a **486 + OptSize≤50** feature — which
exactly matches the proven PS flag set, and predicts that `-os` would
flip every unsigned byte read away from `xor`-first.  Where OW1
diverges: when `V_GOOD_CLR` fails, **11.0 emits `movzx`** (second
table row), whereas **10.0a / PS.EXE emits `mov rl,[m]; and reg,0xff`**
(no `movzx` for these widenings — only the signed `movsx` path,
`G_MOVSX`, is shared).  The busy-vs-free split I measured (index in
the destination reg ⇒ can't clear ⇒ `and` fallback) is the practical
10.0a manifestation of the `V_GOOD_CLR` failing in a way the OW1
verify doesn't model (it doesn't reject when `result` overlaps the
index reg used inside `op1`'s addressing).  **Trust the cgex output,
not OW1, for the unsigned-zext fallback.**

### Verified on

  * `get_new_sslot` (88c+88d, stride-20 struct, address reuse).
  * `select_a_unit`, `plague_an_atom` (88a/88b zext idiom — see Rule 49).
  * `docs/codegen-experiments/array-access-map.py` — the full probe
    matrix (scalar reads, const vs var index, `& 0xff` vs cast,
    stride factoring 6/7/8/10/12/16/20/24/40, signed-char field,
    address-taken, writes).

## Rule 89 — Register allocation is list-order + interference (EAX↔callee-saved = the clobber-crossing)

> This is the canonical register-allocation model.  Supporting theory:
> `docs/watcom-regalloc-research.md`.  Proofs:
> `docs/codegen-experiments/regalloc-eax-boundary.py` /
> `regalloc-order.py` (both self-verifying, `ALL PROOFS PASS`), and the
> binary RE in `watcom10.0a repo docs/wcc386-re/`.

### The proven model (Watcom 10.0a, reverse-engineered from `wcc386-10.0a.exe`)

A value's register is decided by exactly three things — **there is no
caller/callee-save "economics" knob, and no keyword lever**:

1. **Interference / live-range structure** — which values are live
   simultaneously, and whether a value's range crosses a register
   **clobber** (a `call`, or `mul`/`div`/`idiv`, which clobber
   EAX[/EDX]).
2. **`CountRegMoves` savings** — move-elimination (does the assignment
   turn a `mov` into a no-op or let an operand/result already sit in
   the chosen register).
3. **The candidate list order** — first non-interfering register in the
   type's list wins ties.  For 32-bit ints that list is **`DoubleRegs`**,
   which in **10.0a is `EAX, EDX, EBX, ECX, ESI, EDI, EBP`**
   (`va 0x821A8` in the binary; **EBX before ECX**).  The
   *equal-savings* ordering among tied conflicts is **deterministic in 10.0a**
   with two source-level levers (micro-mechanism between hidden-secondary-key
   and ShellSort-instability is under investigation — see
   `watcom10.0a repo docs/wcc386-re/regalloc-model.md` §3; both predict the same levers):
   (a) reorder which value is used first (Rule 28a; commute the deciding
   expression — `change_citizen_targs`), and (b) when the use is pinned,
   swap the two tied locals' declaration order (Rule 115 — `show_help_page`,
   direction non-monotonic, verify both).  Proven behaviourally in
   `docs/codegen-experiments/regalloc-tiebreak.py` and corpus-validated.
   So pure ESI↔EDI ties between named locals are *actionable* (Rule 28a
   or 115), not residue —
   except where the competing values are CSE-hoisted globals in a
   fixed algorithmic order (then the first use can't be moved).  Full
   model: `watcom10.0a repo docs/wcc386-re/regalloc-model.md`.

### The EAX↔callee-saved boundary (the proven, actionable lever)

**A value moves between EAX and a callee-saved register *only* when you
change whether its live range crosses an EAX-clobber.**  Not the
`register` keyword, not register pressure, not "shortening" the range
without changing the crossing.  Clean proof (identical source, same
call, same use count — only the crossing differs):

```c
/* v used BEFORE the call → never crosses → stays in EAX, no push */
int t(void){ int v=ga; gb=v+1; sink(); return gc; }
        mov eax,[ga]; inc eax; mov [gb],eax; call sink; mov eax,[gc]; ret

/* v used AFTER the call → crosses → forced to a callee-saved reg + push */
int t(void){ int v=ga; sink(); gb=v+1; return gc; }
        push edx; mov edx,[ga]; call sink; inc edx; mov [gb],edx; ...; pop edx; ret
```

`idiv`/`mul` clobbers count the same as a call.  Negative controls
(all proven to NOT move the value across the boundary):
`register int v`, 4 extra live locals (max pressure), 5 uses of `v`.

**Levers, derived from the boundary:**

* **PS holds it in a callee-saved reg, we keep it in memory / EAX**
  (`ps_extra_callee_save`): PS's source kept the value live **across a
  call/`idiv`**.  Reshape the C so the value's range spans the clobber
  — e.g. read a global into a named local *before* a call and use it
  *after* (Rule 1 is the inverse: removing such a cache); widen a
  `char` flag to `int` if PS held an int-typed conflict.
* **We hold it in a callee-saved reg, PS doesn't**
  (`rc_extra_callee_save`): our source extends a range across a clobber
  that PS didn't.  Inline the value at its use sites so its range stops
  crossing the call (Rule 1/63/73 family), or move the use before the
  call.

### Diagnostic — `extra_callee_save` is heterogeneous; classify before fixing

A divergent prologue push set (the `ps_extra_callee_save` /
`rc_extra_callee_save` pragma hint) has **several distinct causes**.
Read the PS vs RC body and bucket it:

| symptom in the diff body | sub-cause | lever |
|---|---|---|
| the extra reg holds a value **live across a `call`/`idiv`** on one side only | **EAX-boundary** (this rule) | reshape the crossing (above) |
| the extra reg holds a value that **crosses nothing**, where the two sides picked different registers | **FIRST-USE order** (Rule 28a) | reorder which competing value is used first (commute an operand, move a statement); not always reorderable |
| the extra reg is a **byte reg used to materialise a const for a store** (`xor bl,bl; mov [m],bl`) | **const-temp in a callee-save (Rule 110)** | the store FORM is deterministic (0 always register; nonzero register iff ≥2 refs) — this is a regalloc *which-register* divergence, NOT a store-form lever; match PS's allocation (Rule 108 / use-order), don't chase the store |

Worked corpus examples (all `extra_callee_save`, all *different* causes):
* `link_to_smacker` (rc_extra `esi`) — **first-use order**: RC put the
  constant `1` (stored to `smacker_open`, then returned) in `esi` where
  PS used `ecx`.  The value crosses nothing → not the EAX-boundary →
  reorder the competing values' first uses to flip it (Rule 28a).
* `army_restoring_adjusts` (ps_extra `ebx`) — **const-temp register swap
  (Rule 110)**: BOTH sides use the register form for `exists = 0` — PS
  `xor bl,bl; mov [army_list+eax],bl`, RC `xor dh,dh; mov [army_list+eax],dh`
  (verified against PS.EXE).  It is **not** a form mismatch (RC does *not*
  emit `mov byte[…],0`; storing 0 is always register-materialised).  The
  diff is purely WHICH register the zero-temp got (BL vs DH) — ordinary
  regalloc, fix the allocation (Rule 108 / use-order), not the store.

So: when you see an extra-callee-save hint, **do not assume the
EAX-boundary** — confirm the extra register actually spans a clobber
first.  Only then is the crossing-reshape lever applicable.

### Provenance

* Allocation order `EAX,EDX,EBX,ECX,ESI,EDI,EBP`: static (binary table
  `va 0x821A8`) + behavioural (`regalloc-order.py` consumption ladder).
  RE method: `watcom10.0a repo docs/wcc386-re/`.
* EAX-boundary necessity/sufficiency + the failed economics/keyword
  levers: `regalloc-eax-boundary.py` (clinching pair +
  negative controls, `ALL PROOFS PASS`).
* Why the callee-save "bonus" is moot: the no-push registers (EAX + used
  param regs) are exactly the prefix of `DoubleRegs`, so list order
  already prefers them — a bonus can't reorder a prefix.
* Equal-savings tie-break = **first-use order** (`regalloc-tiebreak.py`),
  corpus-validated (`change_citizen_targs`).
* The exact `CalcSavings` weights are known: loop multiplier **W=10** per
  nesting level (×10 depth 1, ×100 depth 2), `use_save=1`, `def_save=1`,
  `load/store_cost=2`, callee-save prolog cost 2 — confirmed against the
  10.0a binary in `regalloc-cost.py` (`watcom10.0a repo docs/wcc386-re/regalloc-model.md §2`).

## Rule 90 — `enum` vs `char` vs `int`: four distinct codegens; signed/unsigned promotion is the discriminator

Watcom 10.0a (default flags, **no `-ei`**) packs an `enum` to the
smallest integer type that holds all its enumerators.  An `enum` whose
values fit in 0..255 is therefore **1 byte wide** — same storage as
`char` — but it is NOT interchangeable with `char` or `int` in codegen.
The same logic `if (x == 3)` / `if (x > 1)` produces four different
instruction sequences depending on `x`'s declared type:

| type of `x` | load | `x == 3` | `x > 1` |
|---|---|---|---|
| `int` | `mov eax,[x]` (dword) | `cmp eax,3` | `cmp eax,1; jg` (signed) |
| `unsigned char` (project default) | `mov al,[x]` | `and eax,0xff; cmp eax,3` | `xor eax,eax; mov al,[x]; cmp eax,1; jg` (signed) |
| `signed char` | `mov al,[x]` | `movsx eax,al; cmp eax,3` | `movsx eax,al; cmp eax,1; jg` (signed) |
| `enum` (byte-packed, all-nonneg) | `mov al,[x]` | **`cmp al,3`** (byte) | **`cmp byte [x],1; ja`** (UNSIGNED) |

Two independent axes:

1. **Comparison width** — an `enum` compares the byte directly
   (`cmp al,K` / `cmp byte [x],K`); a `char` zero-extends first
   (`and eax,0xff` / `movsx`) and compares as `int`.  Proven in
   `/tmp/enumtest` (enum dispatch 32 b vs `unsigned char` 40 b: the
   char version carries an extra `and eax,0xff`).
2. **Promotion signedness** — this is the decisive faithfulness test.
   `char`/`signed char`/`int` promote to **signed `int`** ⇒ ordered
   comparisons emit `jg`/`jl`/`jle`/`jge`.  A byte-packed `enum` with
   all-non-negative enumerators promotes to its **unsigned** underlying
   type ⇒ ordered comparisons emit `ja`/`jb`/`jbe`/`jae`.

**Worked counter-example (why you must check the jcc, not just the diff
count): `map_mode`.**  146 of the ~409 diffing functions show a
byte-compare-vs-zext signature, which *looked* like a missing enum.
Retyping the `map_mode` global to `enum map_mode_t {CITY,REGION,BATTLE}`
removed the zext in 11 functions but **regressed 37** previously-exact
ones (e.g. `act_query` 0→272 b): PS emits `xor eax,eax; mov al,[map_mode];
cmp eax,1; **jg**` (signed) but the enum forces `cmp byte [map_mode],1;
**ja**` (unsigned).  The `jg` proves PS declared `map_mode` as **`char`**,
not an enum.  Net −26 exact ⇒ reverted.

**Rule:** before retyping any byte value to `enum`, confirm PS uses an
**unsigned** ordered comparison (`ja`/`jb`) on it, or only ever
equality-tests it (`je`/`jne`, sign-agnostic).  If PS uses `jg`/`jl`,
it is a `char`/`int` and an enum will regress it.  The byte-compare vs
zext difference alone is NOT sufficient evidence — for `char` it is a
per-function regalloc/context decision (PS emits `cmp bh,1` directly when
the value already lives in a byte register), so it is not fixable by a
global type change.

## Rule 91 — Compound `op=` on a computed-address memory lvalue is an in-place RMW; expanding to `lhs = lhs op rhs` is NOT equivalent

Discovered 2026-06 during the byte-exact normalization sweep
(`docs/observed-source-style.md`). Generalises Rule 72 (`++field`)
from the increment special-case to all compound operators.

### Compiler-source proof (OpenWatcom V1)

`bld/cc/c/cgen2.c` (`OPR_*_EQUAL` cases) lowers every compound assignment
through **`CGPreGets(op, lvalue, rhs, type)`**, evaluating the lvalue
exactly once.  `bld/cg/c/cg.c::DoCGPreGets` builds
`Unary(O_PRE_GETS, Binary(op, l, r))` — a dedicated read-modify-write IR
node the back-end emits as a single in-place memory op.  A plain
`x = x op y` instead builds a `CGBinary` plus a separate assignment, so
the lvalue address is materialised twice and there is no `O_PRE_GETS`
node to fold — hence the load-op-store.  This is the mechanism, not a
guess.

### Pattern

For a memory lvalue whose **address must be computed** (indexed array
element `arr[i].field`, or any lvalue behind an index/scale calc):

```c
figure_list[figure_no].selected ^= 1;          /* compound  */
```
emits a single in-place read-modify-write, computing the address once:
```asm
xor byte ptr [eax + 0x4380d], 1     ; 7 bytes, one address calc
```

The "expanded" spelling:
```c
figure_list[figure_no].selected = figure_list[figure_no].selected ^ 1;
```
emits a load-modify-store (and may re-evaluate the index), diverging:
```asm
mov dl, byte ptr [eax + 0x2f057]    ; load
xor dl, 1                           ; modify
mov byte ptr [eax + 0x2f057], dl    ; store      (15 b total)
```

On `select_a_unit` that single source change cascaded to a **28-byte**
diff (every short jump after the statement shifts by the 8-byte size
delta). Confirmed regressions on the same lever: `select_a_unit`
(`^=`), `alter_slave_reqs` (`-=`), `set_defense_shield` (`+=`).

### The boundary: fixed-address globals are exempt

When the lvalue is a **constant disp32** (a plain global or a field of a
fixed global, e.g. `c2inf.speech_on ^= 1;`), the compound and expanded
forms are **byte-identical** — Watcom folds `mov;op;mov [disp32]` into
the in-place `op byte [disp32], imm` because the address is a link-time
constant with no index to recompute. So the divergence only appears
when the lvalue carries an index/scale computation.

#### Exception — a CACHED fixed-address global is NOT exempt (`= +` forces the re-read)

The "fixed-address globals are exempt" rule holds only when the global is
**read exactly once** (at the `op=`).  If the same global is **also read
nearby** (a comparison, a `tmp = g;` capture), Watcom keeps it in a
register and the compound `g op= expr` then **reuses that cached value**
via an `lea`/reg-ALU + store, which seats the result in a *callee-save*
register.  The expanded `g = g op a op b` instead forces a fresh
**re-read** of the global and an in-place RMW (`add [g], reg`), exactly
like PS.  So for a cached fixed-global the two spellings are **NOT**
byte-identical, and the cascade is severe: the extra callee-save flips
the prologue push set and **funnels an otherwise-frameless mid-epilogue**
(Rule 92/129) to a tail-merged exit, so the 1-instruction form delta
mushrooms across every later branch displacement.

**Lever:** when `decomp-verify -v` shows `Recomp uses an extra
callee-save` + an `lea <callee-save>,[reg+reg]; mov [global],<cs>` where
PS has a plain `add/sub [global], reg` RMW, rewrite the global update from
`g += a + b` / `g -= a + b` to the explicit chain `g = g + a + b` /
`g = g - a - b` (left-associative; the subtraction form emits PS's two
`sub`s).  Worked: `get_start_points` (battle.c) — the three main-dispatch
`xright_* += bat_width + bat_spacing` / `xleft_* -= bat_width +
bat_spacing` updates were caching the xleft/xright globals into ebx/edi
and funneling PS's frameless mid-epilogues; the `= +` / `= - -` rewrite
dropped both callee-saves: **424 → 230 b, concordance 1.00** (`5da282af`).
Residue is then a separate Rule 110 const-store-0 register tie.

*Caveat — direction is context-dependent:* this is the inverse of the
main Rule 91 guidance (indexed lvalues prefer the **compound** form).
For a cached fixed-global, prefer the **expanded** form; for an indexed
lvalue, prefer **compound**.  Read the asm (Hard Rule #3) to pick.

### Lever

* PS shows an in-place RMW (`xor`/`and`/`or`/`add`/`sub byte|dword
  [base+index+disp], imm`) on an array element → write the **compound**
  `arr[i].field op= rhs;`.
* PS shows a separate load, op, and store of an indexed element →
  write the **expanded** `arr[i].field = arr[i].field op rhs;` (rare;
  usually PS prefers the compound RMW).
* For fixed-global fields either spelling is fine — they're identical.

This is why the byte-exact corpus uses compound assignment on indexed
lvalues essentially everywhere (`&=`/`|=`/`+=`/`-=`/`^=` on
`figure_list[i]`, `slave_requirements[k]`, etc.) and almost never the
expanded form: the compound spelling *is* the PS shape.

### Verified on

* `select_a_unit` (battle.c) — compound exact, expanded +28 b.
* `alter_slave_reqs` (action.c), `set_defense_shield` — expanded diffs.
* `c2inf.*_on ^= 1` toggles (action.c) — both forms identical (control).

## Rule 92 — Early-exit guards need one shared failure tail; `goto fail` is optional, inline `return CONST` is wrong

Discovered 2026-06 during the byte-exact control-flow normalization sweep
(`docs/observed-source-style.md`). Complements Rule 32 (which explains the
jcc-opcode preservation) and Rule 71 (goto for loop reentry) with the
**epilogue-placement** consequence of guard style.

### Pattern

A function with several early-exit guards that all return the same constant:

```c
int mouse_in_area(int x, int y, int w, int h)
{
    if (x > mouse_x)      goto fail;
    if (x + w <= mouse_x) goto fail;
    if (y > mouse_y)      goto fail;
    if (y + h <= mouse_y) goto fail;
    return 1;
fail:
    return 0;
}
```

PS emits **one** `return 0` epilogue at the **function tail**, and every guard
jumps **forward** to it:

```asm
cmp eax, esi
jg  <tail>          ; forward
...
jle <tail>          ; forward
...
mov eax, 1          ; success path
ret
<tail>: xor eax, eax ; the single shared return-0 block, at the very end
        pop ...; ret
```

### What breaks it: inline `return CONST` at each guard

Writing the guards as `if (cond) return 0;` makes Watcom place the `return 0`
epilogue **early** (right after the first guard) and have the *later* guards
jump **backward** to it:

```asm
cmp eax, esi
jle <early>         ; skip the early return-0
xor eax, eax        ; return-0 block emitted EARLY, after guard 1
pop ...; ret
<early>: ...
jle <early>         ; backward jump
```

On `mouse_in_area` that one source change cascaded to a **34-byte** diff
(every guard's jcc flips direction and the whole tail layout moves). Rule 9
(`jg↔jle` flip) fires on every guard row, but the *cause* is the guard style.

### The lever

* PS funnels all same-value early exits to a single tail epilogue (forward
  jumps).  The source does **not** have to use a label when the same CFG can be
  expressed structurally:
  * `goto fail; … fail: return CONST;` is the literal/portable form.
  * A single positive combined condition can be byte-identical:
    `if (a && b && c && d) return 1; return 0;`.
  * Nested positive `if`s can also be byte-identical.
* Do **not** write `if (cond) return 0;` at each guard — that emits the early
  epilogue + backward jumps and diverges.
* When a success-only side effect sits between the guards and `return 1`
  (e.g. `scroll_speed` resetting `cmu_count[2]`), a combined/nested positive
  success block can still be exact; use it if it reads cleanly.  If the logic
  cannot be expressed without duplicating side effects, keep the `goto fail`.
* This rule is **only** for failure funnels.  Loop-placement labels
  (`outer_test`, Rule 71/93), loop-tail `next:` labels, and real shared-tail
  labels (`tail:`) are different classes and are often load-bearing.

### Related: `goto next` (continue-with-trailing-increment) also resists structuring

A forward `goto` to a label that sits at the loop-body tail (so a per-iteration
increment still runs) is **also load-bearing**. On `get_next_word_length`,
rewriting `if (started == 0) goto next; break;` as the structured
`if (started != 0) break;` (fall through to the `next:` increment) still leaves
a 3-byte diff; a `continue` form is much worse.  Watcom does not always
reproduce the goto-based block layout from the structured form.

General principle after the label audit: labels are rare in the exact corpus
(~3%), and many failure funnels can be de-labelled safely, but loop-placement,
loop-tail, and shared-tail labels usually encode a real CFG/layout choice.  Do
not use broad `end_function:` labels as a speculative tail-merge lever unless
the verifier proves that exact CFG shape.

### Verified on

* `mouse_in_area` (lib32.c) — `goto fail` exact; combined/nested positive exact;
  inline `return 0` +34 b.
* `game_speed` / `scroll_speed` (gloops.c) — `goto fail` exact; nested
  positive exact; inline `return 0` on `scroll_speed` +31 b.
* `clear_landfill` (landfill.c) — loop label exact; `while` +43 b,
  `do/while`/`for` +52 b.
* `colour_cycle_delay1` (lib32.c) — `goto ret_zero` exact; positive success
  `if (delta >= delay) { ...; return 1; } return 0;` exact.
* `get_next_word_length` (lib32.c) — `goto next` exact; simple structured
  fall-through +3 b, `continue` +61 b.
* `sf10_hunt_for_fight` (battle.c) — `tail:` exact; structured `else if` +37 b.
* `put_new_node` (web.c) — label loop exact; `for`+`break` also exact, while
  `while`+`break` +63 b.

## Rule 93 — Loop test placement: `do/while` = test-at-bottom (no entry jump); `while`/`for` = test-at-top

Discovered 2026-06 (control-flow normalization sweep,
`docs/observed-source-style.md`).

### Pattern

A `do { body } while (cond);` compiles with the **test at the bottom** and no
entry jump — the body falls through from the prologue and a single conditional
jump at the end loops back:

```asm
; PS wait_key  (do { get_key(); } while (key_ready == 0);)
L1570: call get_key
       cmp  byte ptr [key_ready], 0
       je   L1570            ; bottom test, jumps back
       ret
```

A `while (cond) { body }` (or `for`) compiles with the **test at the top** —
either an entry `jmp` to the condition, or a guard test before the first
iteration, then `body; jmp test`.  Rewriting the `do/while` as a top-test
`while` diverges (measured on `wait_key`: `do/while` exact, top-test `while`
+diff).

### Lever

* PS shows the body executing immediately with the only conditional jump at the
  loop tail (no entry `jmp`/guard) → source is **`do { } while (cond);`**.
* PS shows an entry `jmp` to the condition (or a pre-guard) → source is
  **`while (cond) { }`** / **`for`**.

This is a semantic choice too (do/while always runs once), but the byte-level
consequence is the loop-entry shape — match PS's entry.  Related: Rule 71
(`goto outer_test` when Watcom won't pick test-at-bottom for a `while` whose
body is itself a `do/while`).

### Verified on

* `wait_key` (lib32.c) — `do/while` exact; top-test `while` diffs.
* Corpus uses `do/while` in 19 byte-exact functions (scan-until / run-once
  loops).

## Rule 94 — Boolean structure: `a && b` ≡ nested `if`, but `a || b` ≢ split `if/else-if`

Discovered 2026-06. Clarifies the boundary of Rules 30/31 and 76.

### `if (a && b)` is byte-identical to nested `if (a) { if (b) … }`

Short-circuit AND lowers to two forward skip-jumps to the same fall-through
target, exactly like the nested form.  Measured byte-exact **both ways** on
`get_road_cover` (independent vars) and `find_nearest_target` (shared var
`dist`).  ⇒ **NOISE** — write whichever reads better when there is no `else`.

Caveat: this is *only* the plain AND-vs-nest equivalence.  When an `else` /
`else if` chain hangs off the structure, the nesting **does** matter (Watcom
does no value-range propagation) — that is the separate, load-bearing Rules
30/31.  Flattening `if (a) { if (b) X; else if (c) Y; else Z; }` into combined
`&&` siblings with duplicated guards diverges (measured on `sf02_death`).

### `if (a || b) X` is NOT equal to split `if (a) X; else if (b) X;`

Short-circuit OR funnels to **one shared body block** reached via
test-true-jumps; splitting the OR into an if/else-if chain duplicates the body
into separate blocks and changes the layout.  Measured +diff on `click_warning`
(`if (left || right) out1 = 1;` → split form diffs).  ⇒ **LOAD-BEARING**.

* PS funnels several conditions to one shared body (OR test-true-jumps) →
  write the combined **`if (a || b || …) { body }`**.
* PS shows each condition with its own compare landing on a *separate* body →
  split into per-term branches (this is the Rule 76 case — OR-chain shared-write
  split, won on `get_security_ov_image` / `get_industry_ov_image`).

Match PS's block structure; do not assume `||` and split-if are interchangeable.

### Verified on

* `get_road_cover`, `find_nearest_target` — `&&` ≡ nested (exact).
* `sf02_death` — nested-with-else ≠ flattened (Rules 30/31).
* `click_warning` — `||` ≠ split (diff); Rule 76 is the inverse.

## Rule 95 — `switch` is a distinct dispatch; an if/else-if chain (or arithmetic equivalent) does NOT reproduce it

Discovered 2026-06.  PS uses `switch` in only 5 byte-exact functions
(`backtrack_figure`, `move_army`, `get_movement_image`, `move_citizen`);
everywhere else multi-way dispatch is an if/else-if chain (§2 of the style
guide).  These are **not interchangeable**.

On `get_movement_image`, the `switch (d) { case 0..7: img_base += 3*case; }`
converted to an if/else-if chain diffs — and even the arithmetically-equivalent
`img_base += d * 3` diffs.  Watcom compiles a `switch` via its own dispatch
construction (jump table / balanced compare tree depending on case density),
which neither an if-chain nor a closed-form expression matches.

Lever: write `switch` **only** where PS shows the switch dispatch shape; write
if/else-if everywhere else.  Do not "simplify" a PS `switch` into arithmetic or
an if-chain even when the cases are arithmetically regular.

**The inverse is just as common** (and a real source of large diffs): the
decompiler often wrote a `switch` where PS used an *if/else-if chain*, which
Watcom lowers to a jump table — diverging the whole body.  Decide per function
from the disasm:

* `jmp cs:[reg*4 + table]` (or `jmp [reg*4+...]`) ⇒ PS used a genuine
  jump-table `switch` — keep `switch` (e.g. `try_a_battlemap_square`,
  `get_fig_walk_image`).
* `cmp reg, K; jne …; cmp reg, K2; jne …` chain ⇒ PS used **if/else-if** —
  convert the `switch` to an explicit `if/else if` chain in PS's *exact branch
  order* (read the `cmp` sequence top-to-bottom).  Watcom prefers if/else-if
  over a jump table when the cases all assign the **same field** (so they
  ComTail-merge through one shared store) or when some cases carry compound
  bodies.

### Verified on

* `get_movement_image` (int_c2.c) — switch exact; if/else-if +diff;
  `img_base += d*3` +diff.
* `rebuild_figures_image_data` (battle.c, 2026-06) — **if-else direction**:
  both sprite-table loops were written as `switch (type)` but PS used
  if/else-if chains (cases all assign `arrow_data_ptr = figureN_data`, funneled
  through one ComTail store).  Converting both — figure loop in PS's order
  `7,1,2,3,4,5,6` (case 7 first, its compound `sprite_data_ptr` body kept),
  arrow loop in natural `1..8` — made it byte-exact (260 b → 0).  Same file's
  `try_a_battlemap_square` is the opposite (jump table) — left as `switch`.
  Caveat: the conversion only closes the diff when the prologue already matches
  PS; in prologue-divergent functions (`get_battle_odds`, `get_fig_fight_image`)
  the switch is a minor part and converting it barely moves the byte count.

### Empirical evidence (the equivalence is exact)

Cross-tabulated over the whole byte-exact corpus (2026-06,
`c2/commands/dispatch_hints.py`):

| source construct (byte-exact fns) | PS dispatch shape | count |
|---|---|---|
| `switch` (≥3 cases) | jump table (`jmp [reg*4+t]`) | **5 / 5** |
| if/else-if chain (≥3) | NO jump table | **71 / 71** |
| (any) | jump table **without** a source `switch` | **0** |

So `switch` ⇔ jump-table is a clean **bidirectional** equivalence in this
codebase: every byte-exact `switch` is a jump table, every if-chain is not, and
nothing is a jump table without being a `switch`.  A *diffing* function that
violates it is mis-shaped.  Project-wide there are **18 diffing functions whose
source uses `switch` but PS has no jump table** (the if-else direction above) —
e.g. `get_battle_centuries_left`, `nearest_formation_enemy`, `load_map_graphics`,
`build_road_from_elastic`, `setup_enemy_units` — and **0** of the inverse.
(NB: a genuinely *sparse* switch would compile to a compare tree, not a jump
table; none exist in the byte-exact corpus, so "source switch + no jump table"
is always the mis-shape here.)

**Pre-scaled jump tables** matter for the detector: Watcom often emits the
table index as a separate `shl reg,2` and then `jmp cs:[reg + table]` — the
`jmp` operand has only a *displacement*, no `*4` scale (e.g. `move_to_tb_value`,
`get_tb_value`, `get_ferret2`, all 8-way directional switches).  `ps_has_jump_table`
matches BOTH the inline-scaled (`jmp [eax*4+t]`) and the pre-scaled
(`jmp [reg+disp]`) forms, so those are correctly recognised as genuine switches
and the hint stays silent on them.

**Conversion is a gamble in prologue-divergent functions.**  When the switch
*body* is a large fraction of the function it pays off big (`rebuild_figures`
260→0, `setup_enemy_units` 1238→1121, a 4-field shared-write switch); when it is
a small dispatch buried in a larger diverging body the conversion just shifts
the regalloc cascade and can REGRESS (`build_aquaduct_from_elastic` 341→355,
`build_units_figures` 957→986).  Verify each, keep the wins, revert the rest —
the if/else shape is still more faithful, but byte-down is not guaranteed.

### Auto-detection

`decomp-verify -v` prints a `Dispatch:` header when the source dispatch
disagrees with PS's, and `--json` carries `functions[].dispatch_hint`:

* source `switch` + PS has no jump table ⇒ *"rewrite the switch as if/else-if in
  PS's branch order"* (with the case + fall-through count).
* PS jump table + source has no `switch` ⇒ *"use a `switch`"*.

The detector is `ps_has_jump_table()` (PS disasm) × `_switch_index()` (pycparser
AST over `decomp/src/*.c`).  It stays silent on the byte-exact corpus (no false
positives) and on genuine jump-table switches (`try_a_battlemap_square`,
`move_army`).  Tests: `tests/test_dispatch_hints.py`.

## Rule 96 — Indexed `arr[X].field[D]` under register pressure: give X a temp and D a local so Watcom folds `X*scale` into the SIB byte

### Pattern

A two-subscript indexed read `arr[X].field[D]` (outer array stride = a
power of two, e.g. `struct { unsigned char dir[4]; } rotated2_map[]`)
lowers to a single addressing-mode SIB access when X stays unscaled in a
register:

    mov al, byte ptr [edx + eax*4 + rotated2_map]   ; X=eax (×4 scale), D=edx base

PS.EXE emits exactly that, keeping the array-index value X in EAX (anchored
by an immediately-preceding store) and the inner subscript D in EDX.

Under extra register pressure (e.g. a `print2_test_info()` call inside the
same loop), the obvious source

    sprite_image_no = region_map[pm_shown_ptr];           /* X to a global */
    sprite_image_no = rotated2_map[sprite_image_no]
                          .dir[map_direction >> 1];        /* X reused, D inline */

makes Watcom *pre-scale* X with `shl` and drop the SIB scale, and swap the
X/D registers:

    mov edx, eax ; and edx, 0xff ; shl edx, 2              ; X pre-scaled into EDX
    mov eax, [map_direction] ; sar eax, 1                  ; D in EAX
    mov al, byte ptr [edx + eax + rotated2_map]            ; no ×4 scale

The pre-scale also lengthens the live range of X so the allocator reserves
EAX for it and spills the *loop-index strength-reduction scratch* from EAX
to EBX — a whole-function cascade (12 b local diff balloons to 26–63 b).

### Fix

Give the array-index value its own **temp** and the inner subscript its own
**local**:

    int t   = region_map[pm_shown_ptr];
    sprite_image_no = t;                 /* PS's intermediate (dead) store */
    dir = map_direction >> 1;
    sprite_image_no = rotated2_map[t].dir[dir];
    sprite_image_no += 0x10;

The temp `t` keeps X in a plain register (EAX) so the SIB `*4` scale is
used, and the `dir` local parks D in EDX.  **Both** levers are required:

| form                                  | result |
|---------------------------------------|--------|
| inline X, inline D                    | 12 b (no dead store, swapped regs) |
| separate X (global), inline D         | 63 b (swap + cascade) |
| separate X (global), `dir` local      | 26 b (index correct, scratch cascade) |
| **temp X + `dir` local**              | **0 b** |
| temp X, inline D                      | 76 b (D local is essential) |

`int`, `unsigned int`, and `unsigned char` all work for the temp; a plain
`int t` is cleanest.  Re-reading `region_map[pm_shown_ptr]` at the index
site instead of a temp also reaches 0 but is redundant.

### Discovery

`mid2_line_no_sides_base` (pm_map2.c), 12 b → 0 b.  Full bisection in
`docs/codegen-experiments/mid2_line_no_sides_base.py` (16 trials).  The
exact sibling `mid_line_no_sides_base` (pm_map1.c) needs *no* temp because
it has no in-loop call and hence no pressure — the temp is specifically a
pressure-relief lever, only apply it when `decomp-verify -v` shows the
SIB-scale-vs-`shl` divergence below.

### Auto-detection

`decomp-verify -v` flags the SIB signature: PS memory operand carries a
`reg*2/4/8` scale where the recomp's corresponding row has the same
base+index with **no** scale (recomp pre-scaled via a nearby `shl`).

## Rule 96b — explicit pointer form `*(base + idx + N)` forces a global-index reload (vs the subscript form's register-copy)

### Pattern

PS reads a few adjacent bytes from a `unsigned char *` global at an offset
held in **another global** that was just computed and stored:

    data_ptr = sprite_image_no * 16 + 8;      /* global store    */
    sprite_start = fixt_data[data_ptr+4]
                 | (fixt_data[data_ptr+5] << 8)
                 | (fixt_data[data_ptr+6] << 16);

PS keeps `fixt_data` in EAX and **reloads** `data_ptr` from its global into
EDX, then uses indexed `[edx+eax+N]`:

    mov [data_ptr], eax        ; store the just-computed index
    mov eax, [fixt_data]       ; base -> EAX
    mov edx, [data_ptr]        ; RELOAD index -> EDX
    mov bl, [edx+eax+5]         ; indexed addressing

The array-subscript form `fixt_data[data_ptr+N]` lets Watcom notice the
index value is still live in the register it just stored from, so it emits
a 2-byte register copy instead of the reload:

    mov [data_ptr], eax
    mov edx, eax               ; COPY (index still in EAX) — diverges from PS
    mov eax, [fixt_data]

The two are semantically identical but the copy is 4 bytes shorter and
shifts the whole tail, producing a ~100 b cascade.

### Fix

Write the read in **explicit pointer arithmetic** so the index is reloaded
from the global:

    sprite_start = *(fixt_data + data_ptr + 4)
                 + (*(fixt_data + data_ptr + 5) << 8)
                 + (*(fixt_data + data_ptr + 6) << 16);

`*(base + idx + N)` defeats the register-copy CSE and emits the PS reload.
Do **not** pre-cache the base in a local (`unsigned char *p = fixt_data;`):
that reorders the base load *before* the index computation and regresses.

### Discovery

The `place_diamond` / `place_lefthalf_diamond` / `place_righthalf_diamond`
family and their `*_overlay` siblings in `pm_map0.c` (6 functions, ~100 b
each → 0 b).  Bisected in `docs/codegen-experiments/place-lefthalf.py`.
Likely transfers to the same idiom in the other `pm_mapX.c` clones.

## Rule 97 — an intermediate local for a value immediately stored to a global adds a callee-save register (and can break tail-merge)

> **See also Rule 100** for the inverse lever: when PS *re-materializes a
> literal or re-reads a global* at a downstream use, dropping the local
> (substituting the literal/global) *shortens* the range and flips a swap
> the other way.  Read `c2 disasm` to tell which direction applies.


### Pattern

A scanline loop reads a cell and stashes it to a global before testing it:

    ptr = pseudo_map[pm_shown_y][pm_shown_x];   /* local temp     */
    pm_shown_x++;
    pm_shown_ptr = ptr;                          /* store to global */
    if (!PM_IS_SPRITE(ptr))                       /* tests via local */
        place_sprite(0);

The intermediate local `ptr` keeps the value live in its own register
across the `place_sprite` call, so Watcom commits an **extra callee-save
register** (e.g. a 4th push) and a register-identity swap (Rule 28a)
versus PS, which reads/uses the global `pm_shown_ptr` directly.

### Fix — mirror the byte-exact sibling's source shape exactly

Drop the local; write the global directly and fold the post-increment
into the subscript (matches `sprites_with_sides` / `mid_line_no_sides_top`):

    pm_shown_ptr = pseudo_map[pm_shown_y][pm_shown_x++];
    if (!PM_IS_SPRITE(pm_shown_ptr))
        place_sprite(0);

Also order the loop-counter init **before** the running-index store so the
`xor`-init precedes the index store (PS statement order):

    i = 0;
    pm_shown_x = pm_x;
    for (; i < pm_screen_width; i++) { ... }

### Why it matters beyond the one function (tail-merge)

The extra callee-save changes the function's **epilogue** (`pop esi` vs
`pop edi`, or a different push count).  When the function is a tail-merge
**donor** (Rule 42), a wrong epilogue either (a) blocks its dependents from
merging, or (b) makes its tail *spuriously* match a different sibling's
tail, so ComTail merges the wrong pair and silently regresses a
previously-exact dependent.  Fixing the donor's body to PS-exact restores
the whole merge cluster.

### Discovery

`sprites_no_sides` (pm_map1.c) 173 b → 0 b; the fix also flipped
`mid_line_with_sides_top`, `mid_line_no_sides_base`,
`mid_line_no_sides_top` exact (tail-merge cluster).  When in doubt, read
the byte-exact sibling reported by `c2 sibling` / `decomp-verify -v` and
match its source shape token-for-token — the intermediate-local vs
direct-global choice is the usual divergence.

## Rule 98 — register-arg computed value lands in `ecx` (PS) vs `eax`+`lea` (RC): force its own temp with a Rule 24c neutral term

### Pattern

A value computed inline as the **register argument** of a call — e.g. a
y-coordinate `(query_panel_reduction + K) * 0x10 + 0x20` passed as
`font_list` arg4 (ECX) — can be emitted two ways:

    ; PS form: value born in the arg register
    mov  ecx, [global]        ; 8b 0d ... (6 b)
    add  ecx, K
    shl  ecx, 4
    add  ecx, 0x20            ; result already in ECX (arg4)

    ; RC form: computed in EAX, moved to the arg register
    mov  eax, [global]        ; a1 ... (5 b, eax-only short encoding)
    add  eax, K
    shl  eax, 4
    lea  ecx, [eax + 0x20]    ; +0x20 fused with the move to ECX

The two differ by 1 byte (the load encoding), which cascades into every
downstream short-jump displacement (tens of bytes of diff).

### Mechanism (`bld/cg/c/regalloc.c`)

`GiveBestReg()` keeps the candidate with the highest `CountRegMoves()`
"saves" (candidates tried in `DoubleRegs` order, EAX first), tie-broken
by `HW_Subset(GivenRegisters, reg)` — prefer a register already assigned
to an earlier conflict.  `CountRegMoves()` credits `MOV Rn=>Rn`
eliminations (`+size`) and `OP Rn,x=>Rn` fusions (`+half`) over the
conflict's instruction range.

Whether ECX wins hinges on **whether the value is its own temp**:

* If the expression is bound *directly* as the parm operand (no separate
  `MOV T=>ECX` in the value's conflict range), ECX and EAX **tie** at
  `size` (only the two `add`s fuse).  The tie falls to `GivenRegisters`,
  and EAX is typically already given (e.g. a preceding stack-arg yrow
  pinned it), so **EAX wins** → `lea ecx,[eax+0x20]`.
* If the value is its **own temp** with a `MOV T=>ECX` parm-move in
  range, ECX scores `~2·size` (the eliminated `MOV ECX=>ECX` **plus** the
  two `OP ECX,x=>ECX` fusions) and **wins outright** → `add ecx,0x20`.

Plain expression rewrites (`*0x10` vs `<<4`, operand order, `*16+32`) are
inert — they don't change whether the value is its own temp.

### Fix (Rule 24c neutral term)

Add a neutral term that folds to zero but forces the value into its own
temp:

```c
font_list(0x3d, 0x5b, x_is + 0x38,
          (query_panel_reduction + 0xa) * 0x10 + 0x20
              + (font1[0] - font1[0]),   /* folds to 0; forces own temp */
          font1, 0x10);
```

**Pick the neutral operand from a value LOCAL to THIS call's args**
(here `font1[0]`, the array being passed).  A term built from a global
that an *earlier* call also uses (`query_panel_reduction -
query_panel_reduction`, or `x_is - x_is` when `x_is` feeds arg3) shifts
the whole-function conflict graph and flips an earlier call's value off
its correct register — net regression.  A block-local
`int z = q_type; … + (z - z)` also works (z is defined after the earlier
call, so its range can't overlap it).

### Finding it: use cgex on the FULL function

The register choice is whole-function conflict-graph state, so a minimal
`oracle.compile_snippet` probe gives the *opposite* answer and is
misleading.  Reproduce the whole function in cgex
(`docs/codegen-experiments/sgqp_fontlist.py`,
`ps_function="show_general_query_panel"`) and disassemble each trial to
check the per-call register for **every** affected call (the fixed call
must flip to ECX *and* the other calls must stay on their PS register).
Closed `show_general_query_panel` 358→0 b.  The same mechanism appears in
the other direction (`show_people_query_panel`: PS=EAX+LEA / RC=ECX) —
there the neutral term goes on the call that should be EAX.

## Rule 99 — A byte/short value feeding a `(short)`-cast expression must be a `short` local, not `int` (narrow vs 32-bit arithmetic)

### Pattern

LHARC bit-buffer code reads a byte and shifts it into a `short`
accumulator:

```c
int i;                                  /* WRONG */
i = p[idx];                             /* byte 0..255 */
getbuf |= (short)(i << (8 - getlen));   /* getbuf is `short` */
```

With `int i`, Watcom does the whole `i << k` in 32-bit and zero-extends
the byte with `and eax, 0xff` (5 b).  PS keeps the value 16-bit:

```
mov al, [p+idx] ; xor ah, ah            ; i -> AX (16-bit zero-extend)
... shl ax, cl ; or [getbuf], ax
```

Declaring the local `short` reproduces the narrow form:

```c
short i;                                /* RIGHT */
i = p[idx];
getbuf |= (short)(i << (8 - getlen));
```

`short i` matches PS's intent (the value is a 16-bit shift register) and
flips the byte zero-extend from `and eax,0xff` to `xor ah,ah`, plus the
shift/OR from 32-bit to 16-bit.

### Impact

* `GetBit` (pump.c): 63 b → 8 b.
* `GetByte` (pump.c): 67 b → 2 b.

`unsigned short` works identically; `unsigned char` is worse (25 b in
cgex — too narrow, forces extra reloads).  Bisection:
`docs/codegen-experiments/get_bit.py`.

### Residual (not closed by the type fix)

Two partial-register zero-extend forms survive and have **no** known
source lever (same class as Rule-49b / the `decode_char` truncation
tie-break):

* `xor ch, ch` (PS, char→16-bit zext of `getlen` for `8 - getlen`) vs
  `xor ecx, ecx` (our build, char→32-bit).  Same size (2 b), no cascade.
  Casting the subtraction operands (`(short)getlen`, `(short)(8-getlen)`,
  `((short)8 - getlen)`) does not move it.
* `xor ah, ah` (PS) vs `and eax, 0xff` (ours) for the `return (t < 0)`
  boolean zero-extend in `GetBit`.

These are Watcom partial-register-width tie-breaks decided by dataflow
(whether the high bits are provably zero), not by the C source.

### Rule 99c — a byte *parameter* feeding a compare-chain: type it `unsigned char`, not `int`

The `and eax,0xff` vs al-zext (`xor edx,edx; mov dl,al`) divergence DOES
have a source lever in one common shape: a byte-valued **parameter**
tested against several constants in a row.

`get_circus_bodge(int kind)` is a chain of independent
`if ((unsigned char)kind == 0xE9..0xF0) sprite_image_no = K;`.  PS
re-zero-extends the byte into a fresh scratch on **every** compare
(`xor edx,edx; mov dl,al; cmp edx,K`).  With the param typed `int`,
Watcom matches all but the **last** compare: because `kind`/EAX is dead
after the final test it masks in place (`and eax,0xff; cmp eax,K`) — a
6-byte last-use divergence.  (Note the in-place form is *larger*, 5 b
vs the 4 b al-zext form; it is chosen only because EAX is free to
clobber, not for size.)

Fix: declare the parameter **`unsigned char kind`** and drop the
per-compare casts.  `kind` then lives as a byte in AL, so every compare
— including the dead-value final one — uses the al-zext form, matching
PS byte-for-byte.  This is the parameter-typing analogue of Rule 99 /
Rule 49 (the declared width drives the zext idiom).  Faithful when the
arg genuinely is a byte and no caller has a prototype visible (so the
signature change cannot perturb call-site codegen — `get_circus_bodge`
is called implicit-int from the same TU).  Won get_circus_bodge
(6 b → 0).


## Rule 100 — shorten a local's live range by substituting an equal literal / global-reload at a downstream use to flip a callee-save (Rule 28a) swap

### Pattern (the inverse of Rule 97)

Rule 97 says an *intermediate local* keeps a value live in a register
and **adds** a callee-save.  The complement is just as useful: when PS
**re-materializes a constant** or **re-reads a global** at a downstream
use instead of re-using a value that is still sitting in a register, the
local's live range is *shorter on the PS side*.  Spelling that downstream
use as the literal / global (rather than the live local) shortens our
range to match — which moves the local's *last register-use earlier* and
flips a whole-function Rule 28a callee-save swap (`esi`↔`edi`).

### Symptom in `decomp-verify -v`

* `Prologue hint: Callee-save SWAP: PS uses edi where RC uses esi`
  (whole-function `esi/edi` swap), and
* one localized `mov eax, <reg>` (RC) vs `mov eax, <literal>` (PS), or
  `mov [g], <cached-reg>` (RC) vs `mov [g], eax` where PS already
  reloaded the global into `eax` for an adjacent statement.

The `Regalloc:` line classifies it as a **layer-3 last-use tie**: "the
value with the EARLIER last use gets the higher-priority reg
(DoubleRegs EAX,EDX,EBX,ECX,ESI,EDI,…)".  Removing the local's trailing
use is the lever that makes its last use earlier.

### Fix — write the literal / global at the downstream use, not the local

**`new_name_game_loop` (gloops.c), −60 b → 0 b (byte-exact):**

    int y = 0xe0;
    cursor_y = y;
    ...
    show_a_system_blank(y, 0xd8, 0xc, 2);
    put_a_font_string(..., y, ...);
    setup_refresh_area(y, 0xd0, 0xc, 3, 1);   /* BAD: y still live here  */

PS re-emits the constant (`mov eax, 0xe0`) at the `setup_refresh_area`
call rather than re-using the register holding `y`.  Pass the literal:

    setup_refresh_area(0xe0, 0xd0, 0xc, 3, 1); /* GOOD: y's last reg-use
                                                  is now put_a_font_string */

`y`'s last register-use moves earlier, the layer-3 tie flips so `y`
lands in `edi` (higher DoubleRegs priority) instead of `esi`, and the
entire whole-function Rule 28a swap + its 60-byte cascade dissolves.

**`initreg_game_loop` (gloops.c), −6 b (faithful):**

    region = region_over;
    ... checks via region ...
    province_is = region_over - 1;                       /* eax = region_over */
    province_difficulty = (&empire_region_order[10])[region_over];
    region_warned_status[region]    = 6;   /* BAD: uses cached `region`  */
    region_warned_status[region_over] = 6; /* GOOD: PS reuses the eax it
                                              already reloaded for the two
                                              lines above (mov byte [eax+disp],6) */

`region == region_over` here (region_over is not modified in between), so
the substitution is semantically identical and matches PS's instruction
stream exactly.

### When it does NOT apply (Rule 97 direction wins)

If PS *keeps* the value in a register across the downstream use (no
re-load / no re-materialized constant in the PS disasm), do the opposite —
keep the local (Rule 97).  Read `c2 disasm <fn>` first: a `mov reg,
<literal>` or a fresh `mov reg, [global]` at the use site is the tell for
Rule 100; re-use of the already-live register is the tell for Rule 97.

### Caveat — this is a layer-3 *last-use* lever, not a global-pressure fix

Rule 100 only flips swaps that are decided by last-use order at *equal
savings*.  It does **not** add a missing callee-save when PS enregisters
a 3-use value that our build leaves in a volatile because a volatile was
free (that is the layer-1 global-pressure residue — e.g. `main_game_loop`
`new_turbo`→edi, `initreg_game_loop` `loops_left`→edi / `region`→ebp,
`battle_game_loop` `new_count`→esi).  Those need PS's full live-value set
reconstructed, which has no per-statement lever.  Do not try Rule 100
(or a named intermediate local — that regresses, see Rule 97) on those.

### Discovery

`new_name_game_loop` (gloops.c, this session) −60 b → 0 b;
`initreg_game_loop` (gloops.c) −6 b faithful.  Tested negatives the same
session: a named `int tc = battle_turbo_count + 1` intermediate local in
`battle_game_loop` *regressed* 41 → 134 b (Rule 97 — PS uses in-place
`inc`), and a separate result variable in `main_game_loop` was a no-op
(the temp dies immediately so Watcom still emits in-place `inc`).

## Rule 101 — Base-pointer reassociation: `(&arr[col])[row*stride + k]` to fold the row stride into a SIB scale

### Pattern

A 2-D store `tbl[row][col]` (or `(*(T(*)[H][W])tbl)[row][col]`) where
`col` is **already live in a register** lowers two ways:

* **Full-multiply (the obvious form):** Watcom materializes
  `row*W + col` end-to-end —
  `mov edx, row; shl …; add …; shl edx, k; mov [edx+col_reg+base], v` —
  i.e. it builds the whole linear index in one register.
* **SIB-scale (what PS often emits):** when `W` factors as `m * 2^s`
  (e.g. `W = 40 = 5*8`), PS keeps `col` as the **base register**,
  computes only `row*m` in an index register, and lets the addressing
  mode apply the `*2^s` scale:

      lea/compute eax = row*5         ; m = 5
      mov [col_reg + eax*8 + base+k], v   ; *8 scale, +k disp

PS picks the SIB form when `col` is sitting in a register (so it can be
the SIB base) and `W` has a power-of-two factor ≤ 8.  The obvious C
spelling makes Watcom build the full multiply instead.

### Fix — make the column the base pointer in source

Reassociate so the **column** is the pointer base and the **row offset**
is the subscript:

```c
/* BAD: Watcom builds row*40 in full */
(*(char (*)[30][40])tbl)[row + 1][col + 1] = 2;

/* GOOD: col is the base ptr; (row+1)*40 + 1 is the scaled index    */
(&tbl[col])[(row + 1) * 40 + 1] = 2;
```

Watcom then strength-reduces `(row+1)*40` to `(row+1)*5` and folds the
`*8` into the SIB scale, with `col` (already in a register) as the base
and `+1` in the displacement — byte-identical to PS.

### When it applies

* The column index is already enregistered (PS reloaded/kept it for an
  adjacent compare or a previous store).
* The outer stride `W` has a power-of-two factor ≤ 8 (`40=5*8`,
  `20=5*4`, `48=6*8`, `24=3*8`, `80=5*16`→scale capped at 8 so `*2`
  residual, etc.).
* PS disasm shows `[col_reg + idx*scale + disp]`, not a full multiply.

Won `set_mouse_refresh` (refresh.c): the 2×2 corner store
`[ref_y+1][ref_x+1]` was the last diff; `(&svga_refresh_table[ref_x])
[(ref_y+1)*40+1] = 2;` closed it (ref_x was already in EBX for the
`ref_x < 39` check, so it became the SIB base with `(ref_y+1)*5 * 8`).

## Rule 102 — A narrowing cast INSIDE a sub-expression (`(unsigned short)(E) % N`) defeats CSE with a wider sibling and enables pre-truncation

### Pattern

Two struct fields are written from the *same* arithmetic value at two
widths — a full-`int` field and a narrower `unsigned short` field that is
the value modulo a power of two:

```c
rec.screen_off = py * 5 * 128 + px;                 /* int, == py*640+px */
rec.bank_off   = (py * 0x280 + px) % 0x10000;       /* ushort, 0x280==640 */
```

Because `py*5*128 == py*0x280 == py*640`, Watcom **CSEs** the two
dividends: it computes the value once (into the reg holding `screen_off`)
and reuses it for the modulo — `mov edx, screen_off_reg; … idiv`.  PS
instead re-emits the multiply (`imul eax, py, 0x280`) AND, crucially,
**pre-truncates the dividend to 16 bits** before the divide
(`xor edx,edx; mov dx, ax; … idiv`), because the result is stored to a
`unsigned short` and the dividend is then provably < 0x10000.

The CSE blocks that pre-truncation: a value shared with the wide
`screen_off` use can't be narrowed.

### Fix — move the narrowing cast INSIDE, before the `%`

```c
rec.bank_off = (unsigned short)(py * 0x280 + px) % 0x10000;
```

The `(unsigned short)` truncates the dividend first, producing a value
that is *not* equal to the wide `screen_off` (it's the low 16 bits), so
Watcom no longer CSEs it — it re-emits the `imul` and the ushort
pre-truncation exactly as PS does.  Note the cast is **inside** the `%`,
not wrapping it: `(unsigned short)(E) % N`, not `(unsigned short)(E % N)`.

### Companion lever — written-once local hoists a constant divisor

In the same loop, a literal `% 0x10000` divisor gets **rematerialized**
(`mov ebp, 0x10000`) inside the loop body each iteration. Assigning it to
a written-once local before the loop keeps it hoisted in a callee-save
register across the loop (matching PS):

```c
int modbase;                 /* not a literal, not const-folded away */
…
modbase = 0x10000;           /* written once, before the loop */
…
rec.bank_off = (unsigned short)(py * 0x280 + px) % modbase;   /* uses EBP */
```

A literal, a `const int`, or an initialized-at-declaration form all get
constant-propagated and rematerialized; the bare written-once assignment
statement is what keeps it in a register.

Won `setup_svga_refresh_data` (refresh.c): 169 b → exact, combining this
with the Rule 79 init-order corollary, `idx++` in the for-increment, and
the `goto outer_test` loop entry.

## Hint — Watcom stack-temp coalescing / spill selection is NOT a steerable source lever

When a diff is a **stack-frame size** difference (`sub esp, 0xc` vs
`sub esp, 8`) that cascades every `[esp+N]` offset and trailing short
jump, and `c2 regtrace --explain` reports **no register-identity
divergence** (the register *choices* match PS), the residue is Watcom's
*stack-temp allocation*: whether two non-overlapping spill temporaries
get distinct slots (PS) or are coalesced into one (recomp), and which of
two equal-savings values is spilled vs kept in a callee-save.

This is decided by `GiveBestReg` spill selection (a savings tie broken by
live-range, which is itself a function of the spill decision) plus the
local/temp stack-offset assignment — **not** by anything the C source can
express.  Confirmed on `refresh_svga_screen` (refresh.c): inlining the
field accesses gives the correct indexed `[idx*8+disp32]` addressing AND
correct register choices, but Watcom coalesces the two split-pass spill
temps into one slot where PS keeps two, shrinking the frame and netting
*more* diff bytes (130-187 b) than the cached-pointer form (120 b).
Levers tried and rejected: inline one/both passes, `screen_off`/`bank_off`
temps (incl. `unsigned short`), `volatile` forced spill, both-temp load
order, early loads, explicit byte-offset pointer `*(int*)((char*)arr +
idx*8)`, named locals, guard-side extra reference, inline part_rows
ternary, cached bank-row pointer (22+ variants total: all 130-218 b).
Do not chase frame-size cascades of this class; keep the faithful form
that minimizes the cascade and move on.

### The exact mechanism (traced through OpenWatcom v1 cg)

For `refresh_svga_screen` the split-row pass calls
`partblock(screen_off, bank_off, part_rows)`.  Both `screen_off` (arg1,
EAX) and `bank_off` (arg2, EDX) are int conflicts that prefer the last
callee-save **EBP**, and `c2 regtrace` shows them with **identical
savings (300)** — a genuine tie.  PS keeps `bank_off` in EBP and transits
`screen_off` through the free EDX → spilling it; recomp does the reverse.
The tie is resolved purely by conflict-allocation order:

* `liveinfo.c` builds conflicts by scanning instructions **backward**;
  `AddConflictNode` (`conflict.c`) **prepends** to `ConfList`.
* `regalloc.c::ConfBefore` sorts by `savings` **only**; `SortList`
  (`sortlist.c`) is a **ShellSort** (not stable), so equal-savings order
  is fixed by initial `ConfList` position (i.e. the IL instruction
  stream), not by any C-source keyword.
* `GiveBestReg` then assigns EBP to whichever of the tied conflicts sorts
  first; the loser spills.
* Stack slots: `temps.c::AssignOtherLocals` sorts temps by
  `TempAllocBefore` (smallest size first, then id) and `ReUsableStack`
  coalesces a later spill into an earlier slot when sizes fit and
  instruction-ID ranges don't overlap.

Because PS's source IS the idx-indexed (inline) form and the toolchain is
identical, the only thing that could differ is the IL instruction order
of the three argument evaluations — and that is emitted by the FE with no
C-source handle (a temp to reorder the reference changes the `unsigned
short` field load from a 1-op `movzx` to a 2-op `mov;movzx`/`mov;and` and
still does not flip the tie).  This is the canonical example of a residue
that is *fully understood* yet has *no lever found yet* (a source preimage
exists — Determinism Principle — but likely requires whole-TU IL/temp-
ordering control we can't yet express from one function's source).  Do not
read this as "impossible"; read it as "unsolved, deprioritised."

## Rule 103 — A register-vs-register compare's operand order is welded to register priority; a simple operand reorder swaps the seats too.  RESOLVED for the exemplar: a branchy constant if/else def re-creates the IL with the tie flipped (byte-exact 2026-07-07)

### Pattern

A 2-byte residue that the `Reg swap` classifier *mislabels* as a
register-identity swap, but `c2 regtrace --explain` reports **no
register-class divergence** (registers match PS).  The diff is a single
compare + branch where the operands are swapped and the condition is the
mirror:

```
PS:   cmp ebx, edx ; jl   (target_count < threshold -> skip)
RC:   cmp edx, ebx ; jg   (threshold > target_count -> skip)
```

Both encode the same thing; they are exactly one `RevCond` (operand swap
+ mirrored condition) apart.  Crucially the *register contents are
identical on both sides* — e.g. `threshold` in EDX, `target_count` in
EBX.  Worked example: `entering_new_square` (int_c2.c, 2 b; since
closed to byte-exact — see the RESOLVED disposition below).

```c
threshold = 1 + (army_list[army_no].target_flag == 0);   /* lea edx,[eax+1] */
if (threshold <= army_list[army_no].target_count          /* movsx ebx,byte field */
 && army_list[army_no].target_kind >= 15)
    return 1;
return 0;
```

### Why it is NOT closable by source operand reorder

The compare-selection rules live in
`~/git/open-watcom/owp4v1copy/bld/cg/intel/386/c/386table.c` (`TestOrCmp1` for bytes,
`Test2`/`Test4` for word/dword).  The **only** simplifying reductions
that reverse operands are:

```
_Side(  C,    ANY ),  R_SWAPCMP   /* constant first  -> swap so const is 2nd */
_Side(  M,    R   ),  R_SWAPCMP   /* memory  first   -> swap so it's cmp R,M */
_Side(  C,    C   ),  R_MOVOP1REG
_Side(  M,    M   ),  R_MOVOP1REG
_SidCC( R,    R   ),  G_RR2       /* reg vs reg: emitted in IL order, NEVER swapped */
```

`R_SWAPCMP` (`split.c::rSWAPCMP`) is the *only* straight-line operand
reversal (`RevCond` itself fires only in loopopts/unroll/split).  It
triggers **exclusively** for `(C,ANY)` and `(M,R)` operand shapes.  A
register-vs-register compare matches `_SidCC(R,R) -> G_RR2` and is emitted
in **IL order, never reversed**.

In `entering_new_square`, `target_count` is a **signed byte** field, so it
*must* be `movsx`-extended into a register before being compared with the
`int` `threshold` — the compare is unavoidably `(R,R)`.  Therefore the
asm operand order equals the IL/source operand order.  But the source
operand order *also* fixes register priority (the left source operand is
used first → wins the higher DoubleReg, EDX — see Rule 89 / layer 3).  So
the two facts you would need to match PS are welded together **for a
fixed def-IL** (see the RESOLVED disposition above — changing the DEF's
IL un-welds them):

* PS has `target_count` **first** in the asm (`cmp ebx,edx`) **and**
  `threshold` in the higher reg (EDX).
* Putting `target_count` first in the source (`target_count >= threshold`)
  flips the asm operand order correctly **but** also moves `target_count`
  into EDX (3-byte diff — verified).
* Keeping `threshold` first (`threshold <= target_count`) keeps the PS
  register assignment **but** emits `cmp edx,ebx` (the 2-byte residue).

No *simple operand reorder* yields "target_count first in asm" while
leaving "threshold in EDX": within the `(R,R)`/`G_RR2` path the operand
order and the register priority move together, and SWAPCMP engages only
for `C`/`M` operands.  A source preimage that reproduces PS's exact
combination still **exists** (Determinism Principle) — e.g. some idiom
that fixes the register assignment independently of the compare's source
operand order, or that keeps the field as a memory operand — but it has
not been found.

### Disposition — RESOLVED (2026-07-07): the branchy-def preimage

The "welded" claim below holds for *operand reorders alone*, but a
source preimage DOES exist and closed `entering_new_square` to
byte-exact on BOTH oracles (PS.EXE via Watcom AND CAESAR2.EXE via
MSVC `/Od`):

```c
if (army_list[army_no].target_flag) threshold = 1;
else threshold = 2;
if (army_list[army_no].target_count >= threshold      /* cmp ebx,edx ; jl */
 && army_list[army_no].target_kind >= 15)
    return 1;
return 0;
```

Two ingredients, both required:

1. **Compare written `field >= threshold`** (target_count first) — the
   `(R,R)`/`G_RR2` path emits IL order, giving PS's `cmp ebx,edx; jl`.
2. **`threshold` defined by a constant if/else, not arithmetic.**
   Watcom 10.0a if-converts `if (c) t=1; else t=2;` (and the ternary
   `c ? 2 : 1` / the arithmetic `1 + (c==0)`) to the SAME
   `cmp byte,0; sete al; and eax,0xff; lea rDST,[eax+1]` bytes — but
   the branchy IL creates a *different conflict-node creation order*
   (the boolean/merge temps of the if/else occupy different `cn`
   slots), and the unstable ShellSort then seats `threshold` → EDX
   even with the cmp IL order `(tc, threshold)`.  The two "welded"
   facts decouple.

The arithmetic def (`1 + (flag==0)`) and the ternary both leave the
3-byte seat swap; only the if/else def flips it.  The **Windows
witness pointed at the fix**: `c2 win-decompile` showed a branchy def
(MSVC `/Od` preserves it as real branches), and `c2 win-verify -v`
even pinned the polarity — `if (flag) t=1; else t=2;` (je), not
`if (flag==0) t=2; else t=1;` (jne) — after which both oracles went
byte-exact.  This is another instance of the Hard Rule #7 lesson: on
a ✓IR seat residue, read the win oracle BEFORE grinding regalloc.

For any future member of this class: try the if/else constant-def
form of the tied value's definition before classifying the weld as
unreachable.

**Tooling**: `decomp-verify` auto-detects the fingerprint (a swapped
`(R,R)` cmp whose operand is defined by the `sete/setne … lea
rDST,[rX+K]` chain) via `_rule103_branchy_def_note` — it appends a
`Rule 103 lever:` line to the `~r4` classification, prints a header
line in `-v` on diffing functions, and exports `rule103_lever` in
`--json`.  As of 2026-07-07 the corpus has ZERO remaining members
(entering_new_square was the last `~r4` function; no diffing function
carries the fingerprint) — the hint guards future decompilation work.

The **byte-exact corpus was swept too** (the PS oracle cannot see the
def-form choice — `K + (cond)`, ternary, and constant if/else all
compile to the same sete/lea bytes — so a byte-exact function could
silently carry the wrong form; only the Windows `/Od` oracle
distinguishes them).  Scanning all 1,486 byte-exact functions' PS
bytes: the full sete→lea→(R,R)-cmp chain appears ONLY in
`entering_new_square`; the loose sete/setne→lea boolean-constant def
appears in exactly one more — `four_by_four` (pm_map0.c,
`int parity = (y & 1) != 0;`) — and that one is **win-exact**
(`struct_diff 0`), i.e. MSVC `/Od` reproduces CAESAR2.EXE from our
setne-arithmetic form, certifying the recovered shape.  The ambiguity
class has exactly two members in PS.EXE and both are dual-oracle
certified; no silent wrong-form members remain.

### Tooling note — the `Reg swap` classifier mislabels this

The `Reg swap` rule-hint fires on `cmp ebx,edx` vs `cmp edx,ebx` because
the *register tokens* differ position-wise, but the underlying register
*assignment* is identical.  When `c2 regtrace --explain` says "no
register-class divergence" / "outside the regalloc model" on a 2-byte
`cmp`+`jcc` diff, this Rule 103 `(R,R)` operand-order lock is the cause —
not a register swap.  (Only 3 functions in the current corpus carry the
true `cmp`-operand-swap signature; the other 282 `Reg swap` hits are
whole-function divergence noise, not this case.)

### The IR-lever hunt (why "make the swap swap again" fails here)

PS's reversed form is *not* a SWAPCMP — it is a genuine `(R,R)` compare
whose IL node order is `CMP(target_count, threshold)` (target_count first
in the asm) **while** `threshold` still holds the higher reg EDX.  To
reproduce it you would need both:

1. IL order `CMP(tc, thr)` — reachable: write `target_count >= threshold`.
2. `threshold` allocated to EDX anyway (the op2 value winning the higher
   reg).

These two are mutually exclusive in 10.0a, and the mechanism is now
**directly measured** via the trace image's `cn` (AddConflictNode-birth)
record (watcom10.0a `tools/patch_trace.py`; parsed into
`routine["confs"]`, rendered as the `conflicts(creation order)` hint
line):

* Both temps die at the compare, so both conflicts are **created at the
  cmp**, in operand order: **cmp-op0 (the left source operand) gets the
  earlier creation slot, op1 the next one**.  In `entering_new_square`
  they are creation slots 8/9 of a 13-node pre-sort list; the names are
  visible in the `cn` stream (`threshold`'s name ptr binds slot 8 in the
  `threshold <= tc` form, slot 9 in the `tc >= threshold` form — ins
  ranges identical, only the binding swaps).
* `conflict.c::AddConflictNode` **prepends** (`ConfList = new`), so the
  head is the last-created conflict.
* `SortConflicts` sorts by **savings only** with an **unstable ShellSort**
  (`sortlist.c`); on this list it deterministically maps creation slot 8
  → allocation walk position 4 (first free after EAX ⇒ **EDX**) and slot
  9 → walk position 9 (⇒ **EBX**).  An exact offline ShellSort replay
  (H2) reproduces the `al` walk 14/14.
* `386table.c`'s `(R,R)` compare matches `G_RR2` and is **never**
  operand-swapped, so the asm order == IL order with no compiler escape.

PS's combination (op0 = `target_count` in the asm AND `threshold` → EDX)
requires `threshold`'s conflict to be created **before** the cmp
sighting, or the equal-savings pair to permute differently.  An
exhaustive single-perturbation search over the replayed ShellSort
(insert/remove/savings-change at every creation position) shows the pair
flips only via (a) `threshold` savings ≥ 3 — needs an extra use, i.e. an
instruction PS does not have; (b) an extra conflict at creation slots
0–3/10–13 — all IL-pinned by the byte-identical remainder; or (c)
removing IL-pinned conflicts.  Coalesced-copy injections (`t2 =
threshold`) are eliminated before MakeConflicts (verified: `cn` count
stays 14), and `register` is inert in 10.0a.  Conclusion of that search: **no source
preimage for THIS IL** — which was correct but incomplete: the search
held the def-IL fixed.  The if/else constant def (RESOLVED disposition
above) produces a *different* IL with the same bytes, and there the
equal-savings pair permutes the other way.  The function is byte-exact;
the "compiler-delta class" hypothesis is refuted for this exemplar.

## Rule 104 — Area-stamp prologue/loop lever family: in-place params + deferred row_skip + increment-clause pointer-advance

A large class of `map.c` "stamp a `size×size` (or clamped) rectangle of
cells" functions (`put_x2_area`, `put_x4_area`,
`check_region_map_for_farm_square`, `check_region_map_for_port_square`,
`set_map_ref`, …) shares one PS source shape.  Recovering it closes the
whole function to byte-exact; getting any part wrong leaves a 10–200 b
register/stack cascade.  Four independent levers, all required:

**1. Modify the `x`/`y` parameters in place — do NOT copy to `x0`/`y0`.**

PS source mutates the incoming params directly:

```c
if (map_direction == 2) x -= 1;          /* not: x0 = x; ... x0 -= 1; */
```

A param that is *modified* must be homed to its callee-save register
(esi/ebp) as part of parameter processing, so Watcom emits those moves
**first**, before the stack-param spills (`mov [esp+N], bl/ecx`).  The
`x0 = x` copy is instead a free-floating statement Watcom schedules
*after* the stack spills, producing a 4-mov prologue reorder:

```
PS  : mov esi,eax ; mov ebp,edx ; mov [esp+8],bl ; mov [esp+4],ecx   (params first)
copy: mov [esp+8],bl ; mov [esp+4],ecx ; mov esi,eax ; mov ebp,edx   (stack first)
```

**2. Defer the `row_skip` init and order the early inits exactly as PS.**

```c
int row_skip;                  /* declare, don't init at decl */
... 
industry_build_ok = 1;         /* globals/locals in PS's statement order */
count = 0;
row_skip = (80 - size) * 20;   /* assigned here, not at the declaration */
```

`int row_skip = K;` at the declaration makes Watcom emit the constant
store at the very top; PS emits it *after* the param spills and the
`xor`-zero of the first counter.  Deferring the assignment lets Watcom
schedule the `mov [esp], K` where PS does.  Init order also lets Watcom
**CSE a shared constant into a register**: `industry_build_ok = 1`
materialises `1` in EDX (`mov edx,1; mov [g],edx`), which is then reused
for the `x -= 1` decrement as `sub esi,edx` instead of an immediate store
+ `lea`.

**3. Put the pointer advance in the `for`-increment clause.**

```c
for (yi = y; yi < y + size; yi++, cm_sptr += row_skip) {
    for (xi = x; xi < x + size; xi++, cm_sptr += 8) {
        ...                    /* no `cm_sptr += 8;` as the last body stmt */
    }
}
```

A `cm_sptr += stride;` as the **last statement of the loop body** emits
the pointer-`add` *before* the counter-`inc`; PS emits the counter-`inc`
first (it lives in the `for`-increment clause).  Moving the advance into
the increment clause flips the pair to PS order (compare Rule 27 / 79).

**4. Inline the cell offset as `(x + y*W)*B`, not the `CM_OFF`/`RM_OFF`
macro, when the final `lea` operand order matters.**

`CM_OFF(x,y)` expands to `((y)*W + (x))*B` — the inner sum is `y*W + x`,
so the final `lea` is `[<y-term> + x]`.  PS computes `x + y*W` (x first),
emitting `lea edx,[ecx+eax]` (ecx=x) where the macro emits `[eax+ecx]`
(1-byte SIB difference that then shifts the whole tail).  Write the
offset inline `(x + y*80)*20` at that one call site (don't change the
shared macro — every other caller relies on its order).

**Expression sub-lever (same family): cache `size - 1` once for paired
bounds checks.**  `if (x + size - 1 >= W) ...; if (y + size - 1 >= W)
...;` — PS computes `size - 1` once (`lea eax,[ebx-1]`) and reuses it in
EAX across both the x and y checks.  Recomp recomputes `x + size - 1`
folded into each `lea`.  Introduce `int sm1 = size - 1;` right before the
checks and use `x + sm1` / `y + sm1`.

**When it does NOT apply / is insufficient:** functions that additionally
do min/max clamping of a rectangle (`build_an_area`, `set_range`,
`clear_an_area`) or `idiv`-based sub-tile back-up (`packed % size` /
`packed / size` — `clear_sized_to_reg_basic`, `plague_sized`,
`get_ptr_to_corner`) have a register-pressure / EAX-boundary problem that
dominates and is not fixed by these four levers alone.  Discovery commits:
put_x2_area / put_x4_area, check_region_map_for_farm_square /
_port_square, set_map_ref.

## Rule 105 — WorthProlog `savings >= cost` is a DIAGNOSTIC, not a push-set lever

### Mechanism (verified from `intel/c/i86regsv.c::WorthProlog`)

Once `GiveBestReg` has *chosen* a callee-save register for a conflict,
WorthProlog decides whether to keep it there or spill to memory:

```c
cost    = HW_Ovlap(reg, MustSaveRegs()) ? push_cost+pop_cost (~2) : 0;
savings = conf->savings - MaxConstSave;     /* /LOOP_FACTOR for const temps */
return savings >= cost;                      /* callee-save vs SPILL */
```

So a callee-save is kept (and pushed) iff `savings >= ~2` (≈3 straight-line
uses, or 1 loop use at W=10).  This only gates **callee-save vs spill** —
the same fact as regalloc-model.md layer 2.

### Why this is NOT the lever for Rule 28b push-set diffs (validated)

An earlier version of this rule claimed the push-set diff is one value on
the wrong side of this threshold, nudgeable by a use.  **That was wrong**,
confirmed against real functions:

* `forum_update_census` — PS pushes `ebp` (6 saves), RC pushes 5.  PS puts
  `ec` (a value read AFTER all calls, crossing nothing) in **EBP**; RC puts
  it in **EAX** (caller-save, free, *optimal*).  Both have `savings=3 > 2`,
  both enregister `ec` — they just pick a different register.  This is a
  `GiveBestReg` **candidate-choice** divergence (caller-save vs callee-save
  for a non-call-crossing value), which WorthProlog does not control.
* `perform_region_strip_action` — PS pushes ebx+edx+edi, RC pushes only edx:
  a spill **cascade** from an earlier structural divergence, not a single
  threshold crossing.

### Disposition

The threshold is real and useful for **diagnosis** (a value with
`savings < ~2` cannot hold a callee-save), but observed push-set diffs are
GiveBestReg register-choice / spill-cascade, which are **not** reliably
source-steerable.  Treat L8 push-set diffs as regalloc residue: read the PS
disasm, identify what the extra callee-save holds, and only act if it maps
to a real layer-1/3 lever (EAX-boundary call-crossing, or first-use order).
There is **no push-economics / savings-nudge lever** — i.e. nudging a value's
use count does NOT flip the push-set the way the threshold suggested.  A
source preimage for PS's push-set still exists (Determinism Principle); it
lies in the GiveBestReg register-CHOICE (which competing value wins which
register), an L5 problem whose source lever has not been found here.  "Not
found," not "impossible."

---

## Rule 106 — A callee's declared parameter width truncates the caller's argument; `unsigned short` emits `and eax,0xffff`, signed `short`/`int` do not

### Symptom

PS.EXE masks an argument to 16 bits at the *call site* before a call:

```
mov ax, word ptr [match_length]   ; load 16-bit
add eax, 0xfd                      ; + 253  (high bits now stale)
and eax, 0xffff                    ; ← truncate the int result to 16-bit unsigned
call EncodeChar
```

Our recomp computes the same value but emits **no** `and eax,0xffff`,
so the call site is shorter (and any later short jumps cascade).  The
mask is the tell: PS is converting an `int`-valued expression down to a
**16-bit unsigned** parameter.

### Cause

This is a *caller-side* consequence of the **callee's prototype** (it is
not the callee spilling its own arg — that is Rule 19; and it is not arg
*presence* — that is Rule 22).  The C front-end's `OPR_PARM` handling
converts each actual argument to the callee's declared parameter type
before materialising it in the `__watcall` register.  An `int`-valued
expression passed to a 16-bit **unsigned** parameter is narrowed with
`and eax,0xffff`; a `char`-valued expression (e.g. `unsigned char buf[r]`)
is narrowed with `and eax,0xff` regardless of the param width (the source
value is already 0–255).

The signed/unsigned distinction matters and is the discriminator:

| callee param | int-valued arg (`253 + ml`) | char-valued arg (`buf[r]`) |
|--------------|------------------------------|----------------------------|
| `int`            | *(no mask)*            | `and eax,0xff`             |
| `short` (signed) | *(no mask)*            | `and eax,0xff`             |
| `unsigned short` | **`and eax,0xffff`**  | `and eax,0xff`             |

Only **`unsigned short`** produces the `and eax,0xffff` truncation of an
`int`-valued argument.  (Verified in isolation, not just on pump — a
3-line caller calling `void Sink(<T>)` reproduces the table exactly.)

### Right C

If PS masks an int-valued arg to `0xffff`, the callee's parameter is
`unsigned short` (not `int`, not signed `short`):

```c
void EncodeChar(unsigned short c);          /* not int */
...
EncodeChar(text_buf[r]);                     /* char  -> and eax,0xff   */
EncodeChar((255 - THRESHOLD) + match_length);/* int   -> and eax,0xffff */
```

This was the final lever that closed LZHUF `pump`: `EncodeChar` had been
declared `int c` (its sibling `EncodePosition` was already `unsigned
short`).  Changing the parameter to `unsigned short` added the missing
`and eax,0xffff`, fixed a 10-byte call-site size gap, and — because the
narrower param also changed how `text_buf[r]` was materialised — flipped
the `text_buf[r]` base/index register choice back to PS's, taking the
function from 188 byte-diffs to 0.

### When to apply

Read the call-site mask in `c2 disasm`: `and eax,0xffff` on an
`int`-valued argument ⇒ the callee's parameter is `unsigned short`.  No
mask ⇒ `int` (or signed `short`).  Set the prototype the caller's TU sees
accordingly (for a callee defined in the same TU, fix the definition; the
masking follows the parameter type the front end sees at the call).

Mind the CallZap interaction (Rule 22 / `c2 callgraph --check`): changing
a parameter's *width* does not change arg count, so CallZap is unaffected;
but always confirm the callee's own body still compiles byte-exact with
the narrower parameter (in `EncodeChar` the body already cast `c` to
`(unsigned short)`, so the change was a no-op there).

### Auto-detection

Detected by `c2/commands/rule_hints.py` (`detect_rule_106` +
`_find_rule_106_excess`) and surfaced in `decomp-verify -v`.  It uses the
same asymmetry strategy as Rule 44: count `and reg, 0xffff` rows that
precede a `call` per side, and flag only the genuine excess (a balanced
PS==RC pair, or an `and reg, 0xffff` not followed by a call, is
suppressed).  Hint text: ``PS masks a call arg with `and <reg>, 0xffff`;
recomp omits it (callee param should be `unsigned short`)`` (or the mirror
for a recomp-excess).  Tests: `tests/test_rule_hints.py`.

### Verified on

  * `EncodeChar` / `pump` (decomp/src/pump.c) — `int c` → `unsigned short c`
    added `and eax,0xffff` and closed pump (188 → 0 b).
  * Isolated `compile_snippet` matrix (`int` / `short` / `unsigned short`
    callee param vs char- and int-valued args) reproduces the table above.
  * Watcom 10.0a, `-bt=dos -mf -4r -s`.

### See also

  * Rule 19 — `char` vs `int` *parameter spill width* (callee-side: how the
    callee stores its own incoming parameter).
  * Rule 22 — stub signatures must match real arg *presence/count* (CallZap).
  * Rule 49 / Rule 99 — `& 0xff` vs `(unsigned char)` and narrow-vs-32-bit
    zero-extension idioms (the value-narrowing forms inside a single TU).

---

## Rule 107 — Two co-spilled locals get stack slots ordered by SIZE: the larger temp lands at the lower `[esp+N]` (TempAllocBefore)

### Symptom

PS.EXE and recomp spill the *same* two locals to the stack but to
**swapped** slots, so every access cascades `[esp+A]` ↔ `[esp+B]`:

```
PS :  mov [esp+8],  eax      ; last_match_length (int)  at the LOW slot
      mov [esp+0xc], ax       ; c (short byte temp)     at the HIGH slot
RC :  mov [esp+8],  ax        ; c                       at the LOW slot
      mov [esp+0xc], eax       ; last_match_length       at the HIGH slot
```

No `Rule N` hint fires; only the slot offsets differ, but the swap
repeats at every read/write of both locals (10–40 b of cascade).

### Cause (verified in the 10.0a binary)

`AssignTemps` (va `0x55463`) assigns memory to every NEEDS_MEMORY/!HAS_MEMORY/!ALIAS temp.  It first sorts `Names[N_TEMP]` with comparator `SortCmp_flag2_2b` @`0x55503` (OW v1 names this `TempAllocBefore`, but 10.0a's is flag/offset-keyed — NOT size-only) via `SortList` → `DoSortList` @`0x665c4` → `ShellSort` @`0x66689`, then walks the result calling `AllocNewLocal` (`0x558d4`) → `SetTempLocation` (`0x4e6bb`):

```c
/* SortCmp_flag2_2b @0x55503: t1 before t2 iff ... */
if( byte[t1+0x2b] & 0x2  && !(byte[t2+0x2b] & 0x2) ) return TRUE;  /* ALIAS bit -> alias-first */
if( byte[t2+0x2b] & 0x2  && !(byte[t1+0x2b] & 0x2) ) return FALSE;
if( t1->n.size < t2->n.size ) return TRUE;   /* SMALLER size first */
if( t1->n.size != t2->n.size ) return FALSE; /* larger goes after  */
if( t1->[+0x24] != t2->[+0x24] ) return FALSE; /* DIFFERENT +0x24 -> sort-equal BOTH ways! */
return t1->[+0x10] > t2->[+0x10];          /* +0x10 (v.offset) DESC, only if +0x24 equal */
```

```c
/* SetTempLocation: each call grows the frame, so FIRST-allocated gets the
   LEAST-negative location => the HIGHEST [esp+N] offset. */
CurrProc->locals.size += size;
temp->t.location = -CurrProc->locals.size - CurrProc->locals.base;
```

Putting the two together for two **different-size** co-spilled locals:
* **smaller temp → allocated first → HIGHER `[esp+N]`**
* **larger temp → allocated last → LOWER `[esp+N]`**

For two **same-size** locals the comparator returns FALSE both ways for the
usual case (distinct `[+0x24]`, `+0x10`==0 → sort-equal).  A STABLE sort
would then keep the input order; **10.0a's `ShellSort` is NOT stable** (its
alloc-SUCCESS arm — explicitly annotated "the UNSTABLE ShellSort path";
only alloc-FAILURE falls back to the stable `MergeList` @`0x66566`), so the
gap-passes can REORDER equal-rank same-size temps regardless of size mixing.
The `[+0x24]` field is a **reverse-declaration-rank** id assigned at decl
time, so two user-named same-size locals almost always have distinct `+0x24`
→ sort-equal → their final slot order is purely the non-stable ShellSort
permutation of the whole temp list, independent of their declaration order.

When the diff is a same-size slot swap (the `Slot-swap:` hint flags it),
the **trace gives ground truth** on what each candidate slot is and what
order it commits in — 195/195 functions on the corpus.  Run
`c2 regtrace <fn>` and read the **`an` stream** (AllocNewLocal entry hook
at va `0x558d4`): one record per spill candidate in commit order.  Each
`an` either fires a matching `st` (fresh slot via `SetTempLocation`) or
is ReUsableStack-coalesced into an existing slot.

The candidate order is the NEEDS_MEMORY/!HAS_MEMORY/!ALIAS subsequence of
Names[N_TEMP] at the moment AssignTemps runs its size sort
(`SortList(...,TempAllocBefore)` at va `0x55498`), captured by the
`nt`/`na` walk records emitted by `listwalk_around` on the same call.

**Mechanism for same-size slot swaps:** 10.0a's `ShellSort` @va `0x66689`
is provably **NOT stable** — full stop, not "only when size=1 and size=4 are
interleaved" (that older read is disproven; see
`docs/slot-swap-survey-2026-06-25.md` for the trace proof).  `SortCmp_flag2_2b`
returns sort-equal for every pair of distinct-`[+0x24]` same-size temps
(the usual case), so a stable sort would leave them in `nt` order; the
ShellSort gap-passes reorder them anyway.  An offline simulator
(`c2.regalloc.shellsort_sim_slots.py`, decompiled from the binary) reproduces
the real `nt_post` on 232/232 routines and predicts PS's slot order on
130/130 byte-exact functions.  **`[+0x24]` is a reverse-decl-rank id**,
so a decl reorder moves both the temp's `nb1` position and its `[+0x24]`
rank together — which is why decl-order is NOT a slot lever (proven: 24/24
decl perms of `evolve_water_table` miss PS's target).  The real levers are
temp-set changes (local reuse merges / scope hoists / statement reorder).
of four mechanism classes — surfaced inline by the `Slot-swap:` hint in
`decomp-verify -v`, the `## Rule 107 slot-swap residue` section in
`c2 dossier <fn>`, and the `slot-swap` tool string in `c2 worklist`:

into one of four residue classes — surfaced inline by the `Slot-swap:` hint
in `decomp-verify -v`, the `## Rule 107 slot-swap residue` section in
`c2 dossier <fn>`, and the `slot-swap` tool string in `c2 worklist`:

* **`non-stable-shell-sort`** — the slot order differs purely because the
  non-stable ShellSort permuted equal-rank same-size temps differently.
  The simulator (`c2.regalloc.shellsort_sim_slots.py`) names the temps and,
  given PS's asm-observed slot order, the relative `nt_pre` order that would
  yield it.  Source lever: a *temp-set* change (local reuse merge / scope
  hoist / statement reorder) that renames `[+0x24]` ranks — NOT decl-order
  (decl reorder moves position + rank together; proven insufficient).
* **`savings-keyed`** — the swap is causally UPSTREAM: `AllocBefore` @`0x5905b`
  (BuildNameConflicts) keys on `conflict->savings` for both-have-conflict
  pairs, and the sort-time savings can differ from the later `al`-record
  savings (CalcSavings refines later).  Read `sort_sav` on the `nb1`/`nb2`
  records.  Source lever: change a use-count to move a temp's sort-time savings.
  Cleanest probe target: `show_menu_items` (4 user-named locals, fully
  observable, no size confounder).
* **`sub-source`** — dominated by anonymous CG temps (CSE / spill
  intermediates) with no source attribution.  No source-faithful lever
  available; classify as residue.
* **`misbucketed`** — `c2 diagnose <fn>` reports `fix-next: ir` (or
  similar); the slot-swap symptom is cascade noise from an upstream
  shape divergence.  Re-triage via `c2 diagnose <fn>`.

With that ground truth in hand, the source-side lever is **a temp-set
change** — local reuse merge / scope hoist / statement reorder — that
renames the survivors' `[+0x24]` ranks, which the non-stable sorts then
resolve differently.  Proven cases:

* **Hoist an inner-block local to function scope.**  Changes when its
  temp is AllocName'd, hence its list position.  `refresh_svga_screen`
  went byte-exact by moving the block-scoped `off` (and `saved_idx`) to
  function scope; the affirmed shape matches PS (0 b).
* **Reach for the simulator, not a decl sweep.**  Earlier guidance said
  this case was "unfixable without a SetTempLocation trace"; that trace
  exists now (`nt`/`na`/`an` records) AND a trace-validated offline
  simulator (`c2.regalloc.shellsort_sim_slots`) reproduces the binary's
  sort on 232/232 routines and PS's slot order on 130/130 byte-exact
  functions.  See `docs/slot-swap-survey-2026-06-25.md`.

For **same-line parameters** the simple "swap decl order in signature"
perturbation is a SEMANTIC REGRESSION (each param has a definite
semantic role tied to the asm assignments) — do NOT use it as a lever
even if the byte count happens to drop.  Verify any candidate fix
against the Mac PPC AND the Windows MSVC `/Od` decompiles (`c2
mac-fn <fn>` / `c2 win-decompile <fn>`) to confirm the param-to-field
map still matches; both compiles are independent oracles for the
semantic role of each parameter.  The trace-driven lever for register
params is still being characterised — see
`docs/slot-swap-survey-2026-06-25.md` for the running notes.

**Isolated mechanism proof:** `c2 cgex run shellsort-instability`
demonstrates the ShellSort destabilisation in a controlled 2-trial probe
— two functions identical except for the presence of a size=1 byte temp
in the spill set, with the same-size dword pair landing in OPPOSITE
registers (EDI↔ESI) between trials.  Reproducible mechanism proof; use it
as the reference test when investigating slot-swap residue in a new
function.

### Right C

To match PS's slot order, make the types match PS's **store widths** (read
them off `c2 disasm`: `mov [esp+N], eax` ⇒ a 4-byte/`int` slot; `mov
[esp+N], ax` ⇒ a 2-byte/`short` slot).  In `pump`, PS stores
`last_match_length` with `mov [esp+8], eax` (4 bytes) and the byte temp
`c` with `mov [esp+0xc], ax` (2 bytes), so:

```c
int   last_match_length;   /* 4-byte temp -> LOW slot  [esp+8]  */
short c;                    /* 2-byte temp -> HIGH slot [esp+0xc] */
```

Declaring `last_match_length` as `short` makes both temps 2 bytes; the
slot order then falls to the stable `Names[]` order and lands them
swapped vs PS.  The `int` width is independently correct anyway (PS's
32-bit store + 32-bit refill-bound compare), and it is what gives the
PS slot order for free.

### When to apply

Only when the diff is a pure slot swap of two co-spilled locals (same
instruction count, `[esp+A]` ↔ `[esp+B]` repeated).  Fix the **types**
from PS's observed store widths; do not try to reorder declarations for a
same-size pair (the order is the internal `Names[]` order, not source
order).  Note the size lever can interact with register pressure
elsewhere — verify the whole function, not just the slot rows.

### Verified on

  * `pump` (decomp/src/pump.c) — `int last_match_length` (vs `short`) puts
    it at `[esp+8]` and the byte temp `c` at `[esp+0xc]`, matching PS and
    making the whole refill loop byte-exact.
  * Isolated `compile_snippet` (two address-taken locals; flipping the
    first from `short` to `int` moves it from the high slot to the low
    slot, the short taking the high slot) reproduces the size ordering.
  * Watcom 10.0a, `-bt=dos -mf -4r -s`.

### Detection: total-frame delta YES, same-size swap NO

"Stack-size difference" is really two signals with opposite reliability,
and only one is auto-surfaced:

* **Total-frame delta (surfaced).** `decomp-verify -v` prints a `Frame:`
  header (`_render_frame_alloc` / `_detect_frame_alloc` in
  `c2/commands/decomp_verify.py`) when PS and recomp allocate different
  prologue frame sizes, e.g. `Frame: PS sub esp,0xc  RC sub esp,0x4
  (-8 b) — recomp is missing a stack local/arg slot PS has`.  This is
  reliable because it compares a single SCALAR (the prologue `sub esp, N`)
  that reflects the FINAL frame layout — it is not renumbered by cascade
  the way per-row `[esp+N]` offsets are.  A delta means an extra/missing
  local, a wrong-width local, or a different outgoing stack-arg slot.
  (Caught `show_city_landfill`, -8 b, on first run.)

* **Same-size slot swap (NOT surfaced).** The case in this rule — two
  co-spilled locals exchanging slots at *equal* frame size (e.g. pump's
  `c`/`last_match_length`) — is **not** auto-detected.  It shows up as
  `[esp+A]` vs `[esp+B]` rows, but any upstream cascade renumbers many
  `[esp+N]` offsets at once, so a byte-pattern detector would fire on
  cascade noise as often as on a genuine size-order swap — too
  low-precision to be a reliable hint.  The `Frame:` header will NOT fire
  on it either (the frame size is identical).  Apply it by reading the
  spill store widths in `c2 disasm` (`mov [esp+N], eax` = 4-byte slot,
  `mov [esp+N], ax` = 2-byte slot) and matching the local types.

### See also

  * Rule 24 — spill-via-local (*which* value is chosen as the spill
    victim); this rule is about *where* two already-spilled values land.
  * Rule 47 / Rule 52 — upfront-`int` stack-slot and variable double-duty
    slot-sharing.

## Rule 108 — A named local caching a global out-ranks an incoming param for EAX; inline the global (Watcom CSEs the loads) to keep the param in its arrival register

### Symptom

A function takes a register parameter (arrives in EAX) and also reads a
global a few times.  PS keeps the **param in EAX** and puts the cached
global in EDX; recomp does the opposite — it emits `mov edx, eax` to
evacuate the param, then loads the global into EAX:

```
PS  :  push edx                 RC :  push edx
       xor edx, edx                   mov edx, eax        ; param -> EDX (extra move!)
       mov dl, [zoom_level]           xor eax, eax
       cmp edx, 2                     mov al, [zoom_level] ; global -> EAX
       ...                            cmp eax, 2
       test eax, eax (param in EAX)   ...
                                      test edx, edx (param in EDX)
```

Worked example: **`do_act_zoom_out`** (`decayed` param vs `int zl =
zoom_level`).  The swap also cascades to the end-of-function const stores
(the byte register that materialises `1`/`0` follows whichever DoubleReg
the cached global lived in) and can spuriously enable/disable a ComTail
tail-merge with a sibling (here it pinned `do_act_zoom_in`'s epilogue).

### Cause

A **named local** (`int zl = zoom_level;`) becomes a first-class conflict
with savings = `defs + uses`.  With 3 uses it scores savings 4 and
out-ranks the incoming param (savings 3), so `SortConflicts` allocates
the cached global FIRST and it greedily takes EAX (first in DoubleRegs);
the param, allocated later, is displaced to EDX with a `mov edx, eax`.

PS's source did **not** cache the global in a named local — it read it
inline at each comparison.  Watcom's CSE folds the repeated `zoom_level`
loads into a single load, but the value is now an anonymous **CSE temp**,
not a named local, and the CSE temp is allocated at lower priority than
the param.  So the param keeps EAX and the CSE temp takes EDX — matching
PS exactly (and the const stores + tail-merge fall into place for free).

### Fix

Drop the `int x = global;` local and reference the global inline at each
use site.  Watcom still emits one load (CSE), but the register-allocation
priority flips so the param keeps its arrival register:

```c
/* before: named local out-ranks the param */
int zl = zoom_level;
if (zl == 2) return;
if (zl == 1 || decayed != 0) { ...; refresh_zoom_mode(2); }
else if (zl == 0)           { ...; refresh_zoom_mode(1); }

/* after: inline the global -> CSE temp keeps lower priority than the param */
if (zoom_level == 2) return;
if (zoom_level == 1 || decayed != 0) { ...; refresh_zoom_mode(2); }
else if (zoom_level == 0)            { ...; refresh_zoom_mode(1); }
```

### When it does NOT apply

* If PS itself loads the global into a register **once and that load is
  visibly the canonical body** AND the param is moved out (e.g.
  `do_act_zoom_in`, where the cached zoom-level value is used twice and
  legitimately outranks the param), then the named-local form is correct —
  do not inline.  Decide from the PS disasm: if PS keeps the **param** in
  its arrival reg, inline the global; if PS moves the param out, keep the
  cache.
* Only inline when the global is genuinely re-read cheaply (Watcom CSE
  collapses the loads).  A non-CSE-able expression would reload N times
  and regress.

Discovery: `do_act_zoom_out` (commit on action.c), cgex experiment
`docs/codegen-experiments/zoom_out_conststore.py` (trial `inline_zl` = 0 b).

## Rule 109 — A single-use indexed/scaled load consumed into a fixed register fuses its index into that register; a dead store through the same index splits it

### Symptom

An `arr[i].field` (or any scaled-index load) whose result is consumed into
a **fixed register** — a call/return argument register, or anywhere the
value must land — comes out with the scaled index FUSED into the result
register.  PS keeps the index in a separate **scratch** register:

```
PS  :  movsx eax, word [created_citizen_no]   RC :  movsx edx, word [created_citizen_no]
       imul  eax, eax, 0x3a                          imul  edx, edx, 0x3a
       mov   edx, [eax + citizen_list+6]             mov   edx, [edx + citizen_list+6]   ; index merged!
       mov   ebx, 0x17  ; put_message arg3            mov   ebx, 0x17
       mov   eax, 0x53  ; put_message arg1 (EAX reuse) mov  eax, 0x53
       call  put_message                             call  put_message
```

The diff is a whole register-identity swap (`eax↔edx`) across the
`movsx`/`imul`/`mov` chain.  The **diagnostic tell is the load row**: same
destination register on both sides (`edx`, the arg2 register here), but PS's
base register `!=` dst (index in a scratch) while recomp's base register
`==` dst (index merged into the result).

Worked example: **`barbarians_drop_by_city`** (3 b → 0 b).  Other current
members of the class: `find_enemy`, `barbarian_invades_city`,
`get_fig_walk_image`, `sf14_opertunist_fire` (each carries this as one
component of a larger diff).

### Cause (reverse-engineered from the allocator)

`citizen_list[i].map_ref` lowers to two CG values: the scaled index
(`t_idx = movsx i; imul t_idx, 0x3a`) and the load result
(`t_res = [t_idx + base+field]`).  The result is consumed as `put_message`
arg2, so move-elimination forces it to **EDX** (`bld/cg/c/regalloc.c`
`CountRegMoves` / `GiveBestReg`: the candidate that turns the arg-setup
`MOV EDX <- t_res` into `MOV EDX => EDX` wins).

When the index is **single-use** (its only reader is that one load),
Watcom coalesces `t_idx` into `t_res`'s register — the load becomes
`mov edx, [edx+disp]`, one register.  `GiveBestReg` picks the register with
the highest `CountRegMoves`, and merging the dying single-use index into
the result scores higher than giving it a fresh scratch.

PS does **not** coalesce: its `t_idx` is a **separate value** that greedily
takes EAX (first in `DoubleRegs`), and `t_res` takes EDX.  The reason is
that PS's source gave the index a **second use** — almost always an
*otherwise-dead store* through the same index (set a field on the same
element after the loop) that Watcom's dead-store elimination removes from
the code section but which already forced `t_idx` to be materialised as its
own multi-use value during IL building.  (The loop body in the same
function proves this: there the index feeds five field STORES, is multi-use,
and is correctly kept in its own register — EAX — on both sides.)

### Fix

Give the index a second use so it cannot coalesce into the result register.
The minimal, byte-exact trigger is an **otherwise-dead store through the
same index**, which Watcom DCEs (emits zero extra bytes) while still
splitting the live range:

```c
/* before: single-use index fuses into EDX (put_message arg2) */
put_message(0x53, citizen_list[created_citizen_no].map_ref, 0x17);

/* after: the dead self-store materialises the index as its own value
 * (EAX scratch); the store itself is DCE'd, so the bytes match PS. */
citizen_list[created_citizen_no].map_ref = citizen_list[created_citizen_no].map_ref;
put_message(0x53, citizen_list[created_citizen_no].map_ref, 0x17);
```

This reconstructs a dead store PS's source had at that spot (a field write
to the just-handled element that is never re-read, hence invisible in
PS.EXE).

### What does NOT work

* A plain extra **read** (`(void)arr[i].field;`) — it is DCE'd *whole*
  (load and all), so the index is never materialised. Verified +3 b.
* A **named index/result local** (`int n = i; ... arr[n].field` or
  `int mr = arr[i].field;`) — still single-use, still coalesces. Verified +3 b.
* A **row pointer** (`struct T *p = &arr[i]; p->field`) — materialises a
  full pointer (`base + i*stride`) instead of PS's scaled-offset-in-scratch
  form; regresses hard (+42 b).
* The store must be a **STORE through the index** (its address computation
  is what materialises the index); the data move is what gets DCE'd.

### When it does NOT apply

* If the indexed value is already **multi-use** (several fields of the same
  element read/written), the index is its own value and is split correctly —
  do nothing.
* If PS itself **merges** the index into the result (recomp matches), there
  is no dead store to reconstruct — leave it inline.

Discovery: `barbarians_drop_by_city` (bbarian.c).  Detector:
`rule_hints.detect_rule_109` (fires on the load row: same dst, PS base != dst,
recomp base == dst).  This supersedes the earlier mis-classification of this
shape as an unfixable layer-3 last-use swap — it is a layer-4 single-use
coalesce with a concrete source lever.

## Rule 110 — Const-store form is deterministic (set by addressing mode + ref-count); only the *register* is regalloc

### The "const-store idiom" mystery, resolved

For a long time the layer-4 backlog listed a const-store "idiom" as an
*open* trigger: PS sometimes materialises a constant in a register and
stores it (`xor bl,bl; mov [m],bl` / `mov dl,1; mov [m],dl`), and sometimes
emits an immediate store (`mov [m],imm`).  It is **not a single mystery** —
the *form* is deterministic (set by the destination **addressing mode** and,
for nonzero in form A, the constant's **ref-count**), and the *register* is
ordinary regalloc.  Verified by oracle bisection (Watcom 10.0a, PS flags;
`docs/codegen-experiments/const-store.py`).

The form is decided by the destination addressing mode:

**Form A — direct global `[disp32]` or indexed-global `[reg*scale +
global_disp]`** (this is PS's folded `global[idx].field`):

| store | recomp emits | form |
|---|---|---|
| `g = 0;` (any size, even single) | `xor r,r; mov [g],r` (push r if no scratch) | **register** |
| `g = 5;` (nonzero, **single**) | `mov [g], 5` (`c6`/`c7` immediate) | **immediate** |
| `ga = 5; gb = 5;` (nonzero, **≥2 refs**) | `mov r,5; mov [ga],r; mov [gb],r` | **register** |
| `g = 5; if (h == 5) …` (store + **reg-compare**) | `mov r,5; mov [g],r; cmp r,[h]` | **register** |
| `if (g==5) …; if (h==5) …` (two **mem-immediate** compares) | `cmp [g],5; cmp [h],5` | **immediate** |

**Form B — pointer / base+offset `[reg + disp]`** (a cached `p->field`):

| store | recomp emits | form |
|---|---|---|
| `p->b = 0;` (even 3 fields) | `mov [reg+disp], 0` (`c6`/`c7` immediate) | **immediate** |
| `p->a = 5; p->b = 5;` (even ≥2) | `mov [reg+disp], 5` ×2 (immediate, **not** cached) | **immediate** |

So two mechanisms (both **form A only**) decide register-vs-immediate:

1. **Zero in form A is always register-materialised** (`xor reg,reg;
   mov [m],reg`), even single-use — a gen-level choice independent of
   `cachecon` (a single `g = 0` has ref-count 1 and would be skipped by
   `ConstToTemp`).  The register is a genuine CG value that goes through
   regalloc, so it can land in a callee-save and force an extra `push`
   (e.g. PS `do_act_zoom_out`: `push ebx; … xor bl,bl;
   mov [pointer_mode],bl`).  **Zero in form B is NOT** — a pointer-deref
   `p->x = 0` is `mov [reg+disp], 0` (immediate).

2. **Nonzero in form A is `cachecon.c::ConstToTemp`.**  In the function
   body (`head == HeadBlock`) a nonzero constant becomes a register-held
   `CONST_TEMP` **iff referenced ≥ 2 times** (`num_refs < 2 → continue`).
   References are counted by `CountOps` over the IL operand slots, with the
   exceptions: **call args never count** (constants in a call are always
   immediate/stack), shifts count 1, `ADD/SUB` by `1` or into a stack reg
   count 0.  A **store** is a ref; a **register-operand compare** is a ref
   (and reuses the cached reg — `cmp r,[h]`); a pure **memory-immediate
   compare** (`cmp [m],imm`) does *not* trigger caching.  Inside an inner
   loop the threshold drops to 1 (loop-invariant hoist).  **Form B never
   caches** — a const stored through a pointer is always immediate,
   regardless of count.

#### Rule 110-L — the loop-level single-ref bypass (`head != HeadBlock`)

The "inside a loop the threshold drops to 1" clause above is **load-bearing
and frequently mis-diagnosed**, so spell it out.  `ConstToTemp` is called
once per region.  Its only ref-count gate is:

```c
/* cg/c/cachecon.c — ConstToTemp() */
class = FindMaxClass( cons, &num_refs );
if( class == XX ) continue;
if( head == HeadBlock && num_refs < 2 ) continue;   /* <-- the gate */
temp = AllocTemp( class );
temp->t.temp_flags |= CONST_TEMP;
... ReplaceConst(...); SuffixIns( pre..., MakeMove( cons, temp ) );  /* hoist to preheader */
```

`head == HeadBlock` is **only** true for the whole-function pass.  For
every LOOP call (`head` = a loop head, reached via `LoopRegInvariant` →
`ConstToTemp`, gated by `-ol` / the default OptSize loop opts) the
`&&` short-circuits, so **a nonzero constant used even ONCE inside a loop
becomes a `CONST_TEMP`** and gets a `mov reg,const` hoisted to the loop
preheader.  Both PS *and* our build create this temp — it is **not** a
store-form (Rule 110) difference and the ref-count lever does **not**
apply (the constant is already single-use).

**What actually diverges is the regalloc cost gate**: a `CONST_TEMP`
lives across the whole loop, so giving it a register that is a callee-save
costs an extra `push`/`pop`.  Watcom keeps it only if its savings beat
that overhead.  When a callee-save happens to be free (e.g. EBP, unpushed)
one build seats the temp there (`push ebp; mov ebp,const; … mov [m],ebp`
— statically *larger* than the immediate) and the other lets the temp
spill back to the **immediate** store (`mov [m],imm`, via the
`temp->v.symbol = cons` back-link).  Net: **PS immediate ↔ recomp
register with the constant single-use in a loop is a which-register /
whether-to-push regalloc tie, NOT a const-store-form lever.**  The 1-byte
store-size delta (`a3`/`c7` 10 b immediate vs `89` 6 b register, + the
5 b preheader load + 2 b push/pop) then **cascades every later branch
displacement** — that alignment cascade is the bulk of the byte diff, not
distinct problems.

**Diagnosis / levers (in order):**
* `decomp-verify -v` → `Prologue hint: extra callee-save`/`Rule 28b` +
  the `mov <callee-save>, <const>` row in the loop preheader; the
  `Regalloc:` line tags it `layer 5 loop hoist/reload` and names the reg.
* It is **not** reachable by `permute` (decl / first-assign order) nor by
  `rover-solve` (`not a RISCify-rover swap`) — both confirm "no source
  lever" for the single-store case.
* The **one** known faithful lever is the *multi-exit* variant (the
  `message` case below): if the loop materialises the same constant at
  **several** exits, writing the loop-pinned value as a literal makes
  Watcom emit an independent immediate store at each exit instead of one
  hoisted temp.  With a **single** store there is nothing to de-merge, so
  the residue is a classified regalloc tie-break (record it; do not grind
  decl/use order).

Worked example — `mid3_line_no_sides_base` (pm_map3.c): the 3-way edge
sprite assign `else sprite_image_no = 0xe;` is one store inside the
scan-line loop.  PS keeps it immediate (`c7 05 … 0e`); our build's
`ConstToTemp` loop call seats the single-use `0xe` const-temp in EBP
(`push ebp; bd 0e…; 89 2d …`), the extra `push ebp` flips the callee-save
set (Rule 28b), and the 4-byte-per-store / branch-displacement cascade is
the whole residual diff.  Shape is byte-faithful (shape-recon concordance
1.00, binir all-but-the-hoist identical); `permute --depth 2` and
`rover-solve` both find no lever → **classified loop-const regalloc tie.**
Same root in `mid3_line_with_sides_base` (0xd/0xe) and
`show_battlemap_base` (0xf, alongside PS's own `sprite_default`=0xe local
hoist that we DO match).

### Consequence — there is no separate "const-store lever"

A const-store byte-diff is **always one of three known classes**, never a
mysterious idiom:

* **Addressing-driven form mismatch (the COMMON one) ⇒ Rule 73.**  PS folds
  a global into the address (form A → register-0 / cached nonzero) but recomp
  caches a pointer (form B → immediate).  The store form differs *because the
  addressing differs* — the fix is **Rule 73** (inline the `T *p = &arr[i]`
  cache so the global folds into disp32), which fixes both the addressing and
  the form at once.  `decomp-verify -v` flags these rows as **Rule 73**, not
  Rule 110.
* **Pure form mismatch (same addressing, register ↔ immediate) ⇒ ref-count
  (Rule 110).**  Both sides use form A but one caches the literal and the
  other doesn't ⇒ a ref-count difference (only possible for **nonzero**;
  zero in form A is always register).  Lever: align how many times the
  literal is *used* — PS register / recomp immediate ⇒ make the source share
  the literal ≥ 2× (a second store / register-compare); PS immediate / recomp
  register ⇒ make it single-use (distinct literals, or move a use into a call
  arg, which never counts).  Rare in practice.
* **Register mismatch (both register-form, different reg) ⇒ plain regalloc.**
  The `CONST_TEMP` / zero-temp got a different register — a layer-1/2/3
  problem, *not* a const-store problem.  Use the normal levers (Rule 108
  inline-vs-cache, use-order, savings).  This is the common *form-A* case:
  `do_act_zoom_out`'s `pointer_mode = 0` emitted the register form on both
  sides; only the *register* differed (PS BL / recomp DH) and it closed via
  a regalloc change (Rule 108), never by touching the store.

### Diagnosing

Read the two sides of the diff row:

* dest **addressing differs** (PS `[idx + global_disp32]` vs recomp
  `[ptr + small_disp]`) ⇒ **Rule 73** (cached-pointer); inline the pointer.
* same addressing, `c6/c7 … imm` on one side vs `xor`/`mov reg,imm` + `mov
  [m],reg` on the other ⇒ **Rule 110 form** mismatch ⇒ ref-count lever
  (nonzero only).
* same addressing, `mov [m], <regA>` vs `mov [m], <regB>` (both register) ⇒
  **regalloc** ⇒ do not chase the store; fix the allocation (Rule 108 etc.).

Detector: `rule_hints.detect_rule_110` (fires only on a same-width
register↔immediate store mismatch where the register side is a confirmed
const-temp; it runs *after* `detect_rule_73`, so addressing-driven mismatches
are attributed to Rule 73).  Runtime classifier: the `Regalloc:` line
(`regalloc_explain.py`) tags an extra-callee-save const-temp as a
which-register regalloc divergence, not a store-form lever.

Discovery: oracle bisection of const-store forms (`cachecon.c::ConstToTemp`
+ the gen-level zero-store rule + the addressing-mode split).  Supersedes the
"Const-store idiom (layer 4) — open" entry in
`watcom10.0a repo docs/wcc386-re/regalloc-model.md` §"hard
sub-cases": the form is deterministic, the register is ordinary regalloc.

## Rule 111 — Register-pressure spill / rematerialization: PS re-reads a CSE-able global (or re-materializes a constant) where the recompile holds it in a register

**Asm pattern (PS):** the same never-written global is loaded several times in
one call-free region — e.g. `bribe_emperor` loads `imperial_gift_level` 5× into
EAX/EDI with no intervening `call` and no write to it:

```
mov eax, [imperial_gift_level]   ; gift < avg
...
mov eax, [imperial_gift_level]   ; gift < trib      (re-read)
...
mov edi, [imperial_gift_level]   ; trib*N chain     (re-read, cached in EDI)
...
mov eax, [imperial_gift_level]   ; players_denarii -= gift   (re-read)
```

**Asm pattern (recompile):** our build performs full cross-block CSE and
**holds** the value in one register (here EAX), then has to put every dependent
computation somewhere else — in `bribe_emperor` the `trib*N` chain cascades into
ECX instead of EAX, producing a 283-byte diff across the whole body.

**What this means:** *this is not a source-shape bug.* PS's allocator **spilled**
the lowest-priority conflict under register pressure and re-materialized it
(re-reading a global is cheaper than a stack spill); our build had a free
register and kept it.  Same compiler, same flags, same source — the divergence
is purely which conflict the allocator chose to evict.

**Why there is no faithful source lever:**

* Removing the cache local (`gift = imperial_gift_level` → read the global
  directly) does **not** force a re-read — Watcom just CSEs the global loads into
  a *different* held register (`bribe` no-local → 290 b, worse).
* A split (cache only for the dense sub-region) lands the cache in the wrong
  register class and doesn't reproduce PS's EAX-rescan + EDI-cache split (283 b).
* `volatile` *would* force the re-reads, but it is **non-faithful**: other
  readers of the same global (e.g. `act_gift_down` caches `imperial_gift_level`
  in EDX and reuses it for the `test`), so the global is provably not volatile.
* Reversing a comparison's operand order (`gift >= trib*N` → `trib*N <= gift`)
  does not flip it: PS's `cmp trib*N, gift` is a *consequence* of the register
  split (trib*N in EAX, gift in EDI), not a source operand order (Rule 4 is not
  preserved through the spill — verified, −1 b only).

**Mechanism.** Normally Watcom holds a CSE-able value across basic blocks.
Under register pressure the allocator evicts the lowest-priority conflict and,
for a constant or a global read, re-materializes it (re-reading a global is
cheaper than a stack spill) rather than holding it.  Which conflict gets evicted
is an ordinary `GiveBestReg`/savings decision; when PS's pressure forces an
eviction the recompile doesn't hit, PS re-reads the global while the recompile
holds it — a pure allocator divergence with no faithful source lever (the
levers above were all tried and rejected).

**These re-read diffs are ordinary register-pressure spill tie-breaks, NOT a
memory-mode artifact.**  An earlier hypothesis attributed the whole "PS re-reads
a global that we hold" class to `BlockByBlock` mode (set by the compiler's
low-memory `_MemLow` path), supposedly hit by PS's memory-constrained 1995 build.
That was never confirmed and does not hold: `BlockByBlock` is unreachable in this
toolchain (the W32RUN extender masks every host/guest memory knob — `WCGMEMORY`,
dosemu `$_dpmi`, qemu `-m` — so `_MemLow` never trips; a cross-block-CSE probe
compiles byte-identical at `WCGMEMORY=1` and `4096`), and small TUs like
`message.c` (~3.6 KB) could never have exhausted 1995 memory anyway.  The
divergence is purely which conflict `GiveBestReg` evicted under ordinary
pressure; there is no confirmed source lever.

The compiler's low-memory path is masked by the W32RUN extender (which reports
a fixed 4 MB pool regardless of `WCGMEMORY`, dosemu `$_dpmi`, or qemu `-m`, tested
to 2 MB guest RAM under QEMU), so it cannot be triggered at all in this
toolchain.  The `C2_WCGMEMORY` hook is a harmless no-op placeholder; do not
re-investigate the host-memory path — it is closed and was never the cause of
these diffs anyway.  The "PS re-reads a global far more than RC" class
(`check_clock_ferret_move`, `setup_roman_units`, …) is an ordinary regalloc
eviction divergence with no faithful source lever, not a memory-mode artifact.

**Caution — a 3-slot frame is ordinary regalloc, not a special mode.**
Keeping two non-overlapping spill temps in separate slots happens in ordinary
mode whenever the IL gives the temps **overlapping** instruction-ID ranges (or a
third temp sits in the slot) — there is no need to invoke any memory mode.
Worked example: **`refresh_svga_screen`** — its inline (PS-faithful) form
coalesces two split-pass spills into one slot (`sub esp,8`) while PS keeps two
(`sub esp,0xc`).  PS achieves this in an *ordinary* build, and the function's own
cached-pointer variant ALSO gets 3 slots in an ordinary build (via a pass-2
double-spill).  So the residue is a **source/IL-ordering** shape we haven't
reproduced — a plain allocation difference.

**Detector:** `spill_hints.detect_spill_class` (PS-vs-RC differential: counts
CSE-able redundant reads per side, fires only when PS re-reads materially more
than the recompile — so a function where both re-read, e.g. the byte-exact
`raider_in_region`, is *not* flagged). Surfaced by `decomp-verify -v` as the
`Spill-class:` header. Use it as **negative triage**: when it fires, the diff is
a regalloc spill tie-break — do *not* spend time hunting a source lever, and do
*not* try to reproduce it with a memory-constrained toolchain build (that path
is proven dead under both dosemu2 and QEMU — see above). It is an ordinary
`GiveBestReg` eviction difference; there is no confirmed source lever. Tests:
`tests/test_spill_hints.py`.

**Loop-const variant (the `message` case).** The same keep-vs-rematerialize
split happens for a **loop-invariant constant**, not just a global read.  PS
re-materializes `message_goto_ptr = 0` as independent transients in EAX (5-byte
`a3` store) at each of the loop's three exit blocks; our build runs
`LoopRegInvariant` -> `ConstToTemp` (`cg/c/loopopts.c`), which hoists the 0 into a loop-spanning
const-temp held in EBP (the 6-byte `89 2d` store).  The 1-byte store growth
cascades every later branch displacement (= the bulk of `message`'s 249 b).
PS materialized the constant per exit block while the recompile hoisted it; the
faithful lever is the LOOP-INVARIANT-CONST rover rewrite — write the loop-pinned
value as a literal so it emits an independent const store at each exit like PS.
That closed `message` byte-exact (`game_state = out1` -> `game_state = 1`, since
`out1 == 1` after `while(out1 != 1)`); see the rover loop-invariant-const lever.  Distinguish from an
ordinary register-identity swap (the `Regalloc:` line) only when **neither**
side hoists — here our side demonstrably hoists (EBP held across the loop) and
PS does not.

Discovery: live-allocator + OW-source investigation of `bribe_emperor` /
`message` (`docs/codegen-experiments/bribe_grind.py`). The model side is
written up as hard sub-case 6 ("spill via rematerialization") in
`watcom10.0a repo docs/wcc386-re/regalloc-model.md`; this rule is the byte-pattern detector for
the global-re-read flavour.

## Rule 112 — Reuse a dead variable as a scratch pointer, and assign it INSIDE the narrowest block: pins a freed callee-save register AND keeps an equal-savings tie unflipped

**Asm pattern (PS):** after a parameter/variable's first role is dead,
PS reuses its freed callee-save home (e.g. ESI) for a later short-lived
pointer walk — the byte-exact form, because the callee-save is already
pushed so reusing it is free, and ESI has the long `add esi, imm32`
(6 b) encoding PS emits:

```
mov esi, [smk]            ; smk re-loaded into the dead filename's ESI home
cmp [esi+0x68], 0
cmp [esi+0x6c], 1
add esi, 0x374            ; 81 c6 .. — 6 bytes
push esi
```

**What you must write in C:** reuse the now-dead variable (here the
filename pointer `p`) as the scratch pointer, and **place the reuse
assignment inside the narrowest conditional block where the scratch is
actually used** — not before it:

```c
if (smk->NewPalette != 0) {
    p = (char *)smk;                 /* reuse INSIDE the if */
    if (smk->PalType == 1) p += 0x70; else p += 0x374;
    PaletteSet((unsigned char *)p);
}
```

**What the compiler emits if you write it the obvious way instead:**

* A *fresh* local (`unsigned char *pal = …`) is a short caller-save temp
  → greedily lands in **EAX**, whose `add eax, imm32` is the 1-byte-shorter
  `05` encoding (5 b).  That single byte cascades the epilogue by 2 b
  through every `je <epilogue>` after it — turning a clean diff into a
  100-b mess.  Reuse pins the value to the already-saved callee-save
  (ESI) instead, so the `add` is 6 b and the cascade vanishes.
* Hoisting the reuse assignment **before** the block (`p = (char *)smk;`
  outside the `if`) keeps ESI pinned, but it *lengthens* `p`'s live range
  enough to raise its `CalcSavings` (15 → ~25), and that perturbs the
  *equal-savings* callee-save home tie of two **other** values (the
  `left`/`top` coordinate parameters here): OW's non-stable conflict
  merge-sort (`sortlist.c::MergeList`, equal savings → second-half wins)
  then flips `top→EDI,left→EBP` to `left→EDI,top→EBP`, cascading a 4-b
  prologue swap into every coordinate use.  Assigning **inside** the
  block keeps `p`'s range short (savings ~18, below the flip threshold)
  so the tie stays resolved PS's way.

**Why:** reusing a variable maps to *one* CG conflict whose live range is
the union first-def→last-use (OW does not split ranges); the *scope* of
the reuse assignment is therefore the only source-level control over that
range.  Shortening it (a) lets the allocator keep the value in the freed
callee-save where it began, and (b) lowers its savings so it sorts after
the equal-savings rivals whose order you must not disturb.  This is the
live-range-control complement of Rule 100 (substitute a literal/reload to
shorten a range) and Rule 24a/24c (name a temp to steer regalloc): here
the lever is *where* you spell the reuse, not whether.

**Scope of this rule:** the inside-the-`if` placement pins ONE freed
callee-save (ESI) for the reused palette pointer and unflips the
`left`/`top` home tie — it takes `start_smacking` from 112 b to 6 b.  The
last 6 b (the `SmackToBuffer`/`SmackToScreen` push-temps landing on
ecx/esi/ebx in PS but ebx/ecx/edx in our build) is **not** part of this
rule and is **not** an irreducible tie-break — it is a push-scratch
ROVER cursor position, fixed by a different lever (below).

Discovery: `start_smacking` (`smacker.c`), 112 b → **0 b (byte-exact)**.
Two levers compose:
1. This rule (inside-the-`if` `p` reuse): 112 → 6 b — pins the palette ESI
   and unflips the `left`/`top` home tie.
2. The **push-scratch rover** lever: 6 → 0 b — writing `smk_ref_wi = 0x28`
   into BOTH arms of the dead inner `if (smk_height == 0xc8)` (instead of
   hoisting it after) splits a basic block, which advances the dword
   `FindRegister` rover by one and lands the three push-temps on PS's
   ecx/esi/ebx.  See the decomp-verify `Rover:` hint and watcom10.0a
   `docs/rover-model.md` — the residue was a rover position, not a floor.

Related: Rule 100 (range shortening to flip a tie), Rule 97 (the inverse:
a local that *lengthens* a range adds a callee-save), Rule 24a/24c,
Rule 28a, and the Rover lever (decomp-verify SKILL).

## Rule 113 — A 2-D offset's source operand order (`x + y*W` vs `y*W + x`) picks the `lea` base register; PS wrote `x` first, so the `CM_OFF`/`RM_OFF` macros (`y*W + x`) emit the swapped `lea [idx + base]`

**Discovered:** closing `transform_road_elastic` / `transform_reg_road_elastic` to
byte-exact (the last 1-byte residue after the whole body matched).

### The asm

Computing a cell byte offset `(x + y*W) * C` (e.g. `CM_OFF` = `(y*80 + x)*20`,
`RM_OFF` = `(y*60 + x)*8`) ends in an add of the running `y*W` term and the `x`
term.  When Watcom lowers that add to a `lea`, the **operand order in the C
source decides which value becomes the `lea` base** (the first sub-expression)
and which becomes the index:

```
PS  (source `x_min + y_min*80`):   lea edx, [ebx + eax]   ; ebx = x_min (base), eax = y*80
RC  (macro  `y_min*80 + x_min`):   lea edx, [eax + ebx]   ; eax = y*80  (base), ebx = x_min
```

Both compute the same value; the bytes differ by one (the ModRM SIB picks a
different base/index pairing).  That single byte then cascades through every
short jump after it.

### What to write

* **In `map.c` (and any TU you are matching), do NOT use the `CM_OFF` / `RM_OFF`
  / `BM_OFF` macros for the offset of a cell you then index.**  They are defined
  `((y)*W + (x)) * C` — y-first — which is the *wrong* operand order for PS.
  Write the offset explicitly with **`x` first**:

  ```c
  gmn_sptr = (x_min + y_min * 80) * 20;   /* city map  — NOT CM_OFF(x_min, y_min) */
  gmn_sptr = (x_min + y_min * 60) * 8;    /* region map — NOT RM_OFF(x_min, y_min) */
  ```

* This only flips a byte when the add lowers to a `lea` (both addends live in
  registers at that point).  When PS computes the offset with a plain
  `add eax, ebx` (e.g. the region-map path where `y*60` is built by a shift
  chain into `eax` and `x` is *added* to it), the operand order is invisible and
  either spelling is byte-identical — but the explicit x-first form is never
  *worse*, so prefer it uniformly and stop reasoning about which case you are in.

### Why not just fix the macro

The macros live in the shared `entities.h` and are consumed by every TU.  Some
already-byte-exact functions in other TUs may depend on the current (y-first)
lowering, so flipping the macro globally is a blind risk.  Ban the macro **per
TU** (replace with the explicit x-first expression) and guard with
`c2 baseline check`.  Mnemonic: **offset = `(x + y*W)*C`, x always first.**

## Rule 114 — Loop-bound min/max sort: PS uses an **in-place swap** (`if (a>b){t=a;a=b;b=t;}`) for the axis whose min seeds the loop counter, reusing the arg registers — NOT separate `min`/`max` locals

**Discovered:** `plaza_an_area` 208 b → 28 b (the single edit that collapsed the
whole-function register cascade); also used in `build_an_area`.

### The shape

Clipped-rectangle area/range functions sort their args into a min/max bounding
box, then walk it.  Two spellings of the sort produce *different whole-function
register allocations*:

```c
/* ✗ separate min/max locals — Watcom assigns fresh registers and the
   permutation rarely matches PS, cascading a reg-swap through the whole body */
ymin = y1; ymax = y2;
if (y1 > y2) { ymax = y1; ymin = y2; }
... for (y = ymin; y <= ymax; ...) ...

/* ✅ in-place swap, then use the (now sorted) ARGS directly — PS keeps the
   smaller value in y1's arrival register (it becomes the loop seed) and the
   larger in y2's, exactly matching PS's `cmp; jle; xchg`-style swap */
if (y1 > y2) { int t = y1; y1 = y2; y2 = t; }
... cm_sptr = (xmin + y1 * 80) * 20;
... for (y = y1; y <= y2; ...) ...   /* y1 = ymin, y2 = ymax */
```

* Apply the **in-place swap to the Y axis** (the one whose min initialises the
  outer loop counter and feeds the offset).  The **X axis keeps separate
  `xmin`/`xmax` locals** with an `if (x1 > x2) { xmax = x1; xmin = x2; }` —
  PS allocates xmin/xmax to two callee-save registers (they both survive the
  loop: xmin is re-loaded each outer iteration, xmax is the inner bound), so the
  separate-local form is correct there.  The asymmetry (Y in-place, X separate)
  is what PS actually emits.
* **Swap-body order matters** (Rule 4): write `xmax = x1; xmin = x2;` (max
  first) to match PS's `mov esi,eax; mov edi,ebx` order.
* **`row_skip` / stride**: write `(W - (xmax - xmin) - 1) * C`, NOT
  `(W - (xmax - xmin + 1)) * C` — PS computes `xmax-xmin`, then `W - that`
  (`mov R,W; sub R,..`), then `dec` (the `-1`), then `*C`.  The `+1`-inside
  form lowers to a `lea` and diverges.
* Combine with **Rule 71** loop-inversion gotos when the loop body has a call,
  and **Rule 113** (explicit `(x + y*W)*C` offset, no `CM_OFF`/`RM_OFF`).

### Residue

Even with the correct sort, functions with **5+ args** (`build_an_area`,
`put_*_area`) spill the extra args and the *spill-slot ordering* (Rule 107) or a
short-lived **offset-temp register** (edi vs ebx) can leave a tie — the
statement-reorder lever (compute the offset / `start_sptr` *before* the
`start_x_pos`/`start_y_pos` stores) closes part of it (`put_x1_area`
197 → 135).  These are the residual hard cases; the sort shape above is the
durable, high-leverage part.

## Rule 115 — Declaration order is the regalloc lever for equal-savings ties when the use is pinned

The second source-level handle on the layer-3 equal-savings tie-break (the
first is Rule 28a, commute the use).  When two named locals have *equal
savings* and the register-identity swap can't be flipped by commuting /
reordering a use, **swap the two locals' declaration lines** at the top of
the function.  The IL allocates their name nodes in the new order, and the
tied pair takes the opposite registers.

*Micro-mechanism uncertainty:* upstream OW v1/v2 `regalloc.c::ConfBefore` is
strict savings comparison with **no secondary key** — the tie-break comes from
either (H1) a hidden name-pointer secondary key in 10.0a, or (H2)
ShellSort instability + `AddConflictNode`'s pre-sort order (the project's
`owp4v1copy` carries a `REVCG_CONFFLIP` research hook that models H1).  Both
hypotheses predict the same source levers; see
`watcom10.0a repo docs/wcc386-re/regalloc-model.md` §3 for the full discussion.

### When this lever applies (vs Rule 28a)

`regtrace --explain` reports the diverging swap and the competing values.
If it names two named locals with `case: taken` or `order_loss`:

1. **Rule 28a first** — commute the deciding expression / move the use.  Most
   predictable; works whenever the use is reorderable
   (`change_citizen_targs`: `dest_y*80 + dest_x` → `dest_x + dest_y*80`).
2. **Rule 115** — when the use is pinned by semantics, swap the two locals'
   declaration lines.

`show_help_page` (mmedia.c) is the canonical Rule-115 case: 11-byte ESI↔EDI
swap on tied locals `text_x` / `text_lines`.  `text_lines` is read early in
both builds (`cap > text_lines`), so Rule 28a is dead.  The decl swap:

```c
int text_lines;   /* was: int text_x;     */
int text_x;       /* was: int text_lines; */
int text_w;
... text_x = 0x28; text_w = 0x190; text_lines = 1;   /* inits unchanged */
```

flips the name-pointer order, moves ESI from `text_lines` to `text_x`, and
closes the diff to **0 bytes**.

### Direction is NOT monotonic in source line — verify

"Declared earlier" does **not** mean "higher register."  In the same function,
`text_w` is declared **last** yet takes the **lowest** register (EBP); declaring
`text_x` later made it take the **highest** (ESI).  Reassignment and IL
restructuring perturb the name-pointer order, so the procedure is **try both
decl orders and keep the one that verifies byte-exact**.

The `register` / `auto` *keywords* remain inert (Watcom routes both through
`CGAutoDecl`); only the *order* moves bytes.

### Where the lever is dead

When the competing values aren't named locals (compiler-generated temps,
CSE-hoisted globals), there is no source name to reorder — Rule 115 has no
handle.  Combined with Rule 28a being dead on the same case, those swaps are
genuine residue.

## Rule 116 — Named intermediates: inline memory-rooted reads, don't hold them (reload-vs-hold marker)

The general principle behind Rules 1 / 63 / 73 / 74 (all "remove a cache"):
**PS.EXE almost never names an intermediate that holds a memory-rooted value**
— a global read, an array-element / struct-field read.  It inlines the
expression and lets the compiler reload (or CSE) the home.  A human reading the
asm is tempted to introduce `int t = <global-or-element>;` — and that one named
local changes the instruction stream.

### Why a named temp is load-bearing (mechanism)

A named local `int t = G;` is **one coalesced CG value severed from its memory
home** — the allocator must HOLD it (callee-save register + `push`/`pop`, or a
private stack slot under register pressure); it can never re-read `[G]`.  An
inline memory read stays an `N_MEMORY` reference tied to its home, so the
compiler is free to:

* **reload** `[G]` at each use when a `__watcall` call kills the aliasable
  global between uses (`cse.c::ReDefinedBy`), or
* **CSE to one load** when nothing kills it between uses (e.g. a `char` global
  byte-compared in place across an `if/else-if` chain — the byte-width sub-case
  below).

Whether a held value is *worth* a register is `regsave.c::CalcSavings`
= Σ(uses)·W^depth − spill/prolog cost (W=10 per loop level), so the
reload↔hold crossover is purely **use-count × loop-weight**.

### The marker (read this off the PS disassembly)

Per memory-rooted value:

* **Re-reads its original home** (`mov reg,[disp32]` global, `mov reg,[idx+disp]`
  row field) at each use, *especially across a `call`* → the source **inlined**
  it; **no named temp**.  (A `void` function tail-`jmp` on the last reload
  corroborates.)
* **Materialised once, reused from a register or a private `[esp+N]`/`[ebp-N]`
  slot**, never re-reading the home → the source had a **named intermediate**
  (callee-save reg+push = low pressure; stack slot = high pressure).
* **Single use, or register-only arithmetic of params/locals** → **byte-neutral,
  no marker** — the compiler builds the same temp whether or not you name it.

### Byte-width sub-case (was the old Rule 116)

A `char` global cached in a `char` local and tested several times in an
`if/else-if` chain makes Watcom promote the *second* comparison to `int` — a
spurious `and eax,0xff` zero-extend plus an `al`↔`bh` byte-reg swap. Inlining
the global at each compare lets Watcom byte-compare in place
(`mov bh,[g]; test bh,bh; cmp bh,1`). Won `helping` (action.c) 10→5 b (residual
5 b is Rule 16 cross-fn tail-merge).

### Loop exception (do not over-read the hold)

Inside a loop an invariant global/array read is **hoisted-and-held by LICM even
when written inline** (including when the body stores to a *different,
provably-non-aliasing* global).  Only a **call** (or an aliasing pointer store)
in the loop body forces a per-iteration reload.  So "loaded once before the
loop, held" does **not** imply a named temp — match PS's loop call/store
structure (Rule 50), don't add a temp to force a hoist.

### The C lever

When PS reloads `[home]` but our build holds it (extra callee-save `push`, single
load reused), **delete the `int t = <expr>;` local and inline the expression at
each use**.  Only for memory-rooted values; register-only arithmetic temps are
inert.

### The inverse is NOT a reliable lever

"PS held a value our source inlined → add a temp" is **not** auto-flagged. A
single PS load of a global is dominated by confounds a scalar temp does not fix:
a compare-chain CSEs to one load in *both* builds (`helping`); a global in
subscript position is a held *scaled index* (Rule 63/64, not a scalar); reads in
mutually-exclusive branches load once per path with no reload. In causal tests
the "add a temp" rewrite was a no-op or regressed (`f15_barb_elephant` 7→7 b,
`flag_mode_action` 150→198 b). Adding a temp to match a PS hold is a
case-by-case manual judgement, not a mechanical rule.

### Tooling

* `c2 decomp-verify -v` prints a `Rule 116:` header (and `--json`
  `functions[].reload_hint`) when our source declares a named local caching a
  **bare global** that PS fully inlines. Implementation:
  `c2/commands/reload_hints.py`; tests: `tests/test_reload_hints.py`.
* **Every hint is PS-confirmed and tightly gated** — the detector only fires when
  ALL of:
  1. the local is used ≥2× (single-use temps are byte-neutral);
  2. PS loads the global home **more** than the source's own max load count
     (`distinct caches + inline reads of the same global`) — so a source that
     also inlines the global elsewhere (`act_correct_map`: `mm` + 5 inline
     `map_mode`) already matches PS and is NOT flagged; sibling holds of one
     global (`perform_region_strip_action`: `icon`+`after` in edx/edi) are NOT
     flagged;
  3. PS reloads at **every** use (`ps_loads >= uses`) — a value PS merely
     *holds and reloads a few times across calls* (`get_query_info`: `ptr` used
     18×, PS loads 3×) is a hold, not an inline, and is NOT flagged.
* **Element/field caches are NOT flagged here.** They have no single confirmable
  home address (the read is a computed `arr[i].field`), so a reload cannot be
  distinguished from a CSE'd sequential double-read (`strip_spaces` `c`,
  `goto_flag_marker_mode` `p` — both CSE, inlining regressed them). That family
  is the Rule 63/73/74 pointer/row cache, covered by `c2 row-caches` /
  `global_cache_hints`.
* Distinct from **Rule 111** (`spill_hints`): that is the *negative*-triage case
  (PS re-reads more than us with no removable source local — a pressure spill we
  cannot reproduce). Rule 116 fires only when our source has an explicit named
  local to delete.
* **Caveat — a hint identifies the inline *shape*, not a guaranteed close.** When
  the function's diff is dominated by an unrelated regalloc cascade, deleting the
  cache won't close it and may regress (`show_battle_outtro_screen`: genuine
  per-use index reload, but its 1215 b diff is the `font_no`/`font_list` call
  sequence — inlining moved it 1215→1224). Verify each apply.

### Proven

* `docs/codegen-experiments/reload-vs-hold.py` (self-asserting cgex: named ≠
  inline iff memory-rooted & used ≥2×; the reload vs hold disasm shapes; `ALL
  PROOFS PASS`).
* Live allocator (`c2 regtrace`): byte-exact all-inline `running_pop_tax` → 5
  anonymous `(temp)` conflicts, ins-range 2-5, savings 2-4 (reloaded);
  byte-exact named-temp `test_for_any_admin` → named conflicts, ins-range 64
  (loop-spanning), savings 421/310/…/11, held in callee-save ESI/EDI.
* Causal: adding `int pass = pop_income_pass_count;` to the byte-exact inline
  `running_pop_tax` breaks it (0 → 22 b diff); reverting to inline is exact.
* Corpus: named computed-init intermediates are 8× rarer per function in the
  byte-exact corpus (0.06/fn) than the diffing corpus (0.48/fn); size-controlled
  (Mantel–Haenszel) lift 1.34 (≥1 temp) → 1.54 (≥3).

## Rule 117 — Prologue frame-size delta is the root of the largest cascades; the slot delta + sign localizes the fix

Corpus mining of the 335 diffing functions (full `decomp-verify --json` +
disassembly of all 2261 PS.EXE functions) established two facts that reframe the
remaining grind:

1. **Cascades are seeded in the prologue.** The median first-divergent
   instruction sits at **1.8 % into the function**. 45 % of diffing functions
   have their *first* diff in the prologue (callee-save `push`/`pop` set or the
   `sub esp, N` frame), and those prologue-rooted cascades account for **63 % of
   all residual diff bytes**. Most body register-swaps are *downstream symptoms*
   of one prologue seed, not independent diffs — stop treating big diffing
   functions as body-regalloc problems and treat them as prologue-seed problems.

2. **The `sub esp, N` delta is a reliable, currently-under-diagnosed signal.**
   It is a single scalar reflecting the FINAL stack-frame layout, so a PS-vs-RC
   difference is a clean measure of how many stack slots (named locals + register
   spills + outgoing stack-arg space) the two builds disagree on. Unlike per-row
   `[esp+N]` offsets it does **not** renumber on a cascade. 66 diffing functions
   have a frame-size delta; **all 66 are root-of-cascade**, covering 35 % of
   residual diff bytes on their own (the frame-size subset of the 63 %).

### The marker (read off the prologue)

`Frame: PS sub esp,0xA  RC sub esp,0xB  (±N b = ±K slots)` — `K = (RC−PS)/4`
whole 4-byte slots. The **sign is the fix direction**:

* **RC bigger (we allocate more slots, 28/66).** We hold a value PS didn't.
  The diagnostic auto-splits this into three by comparing prologue **push
  counts**:
  * **WorthProlog spill-vs-callee-save (RC has FEWER pushes, ~4/28).** RC
    dropped a callee-save register and spilled that long-lived value to a stack
    slot instead, where PS enregistered it in one more callee-save reg
    (`put_x1_area`: PS+edi; `up_slider_var`: PS+ebp). This is a Rule 89 /
    WorthProlog savings tie — **NOT** a removable local. Raise the value's
    use-count savings or reshape its range; often a hard tie. The diagnostic
    prints `WorthProlog spill-vs-callee-save` and routes you to the Prologue
    hint, away from Rule 116.
  * **Structural / RC over-enregisters (RC has MORE pushes AND a bigger
    frame).** RC enregisters more values overall, so the function's live-value
    count / control-flow shape differs from PS — the frame delta is a downstream
    *symptom*, not the cause. Fix the **structure**, not the frame: a `switch`
    compiled to a jump table where PS used if/else-if (Rule 95), a ternary or
    `if(c)x=A;else x=B;` folded to `sete`/`add` where PS branched (Rule 26 —
    use the `x=A; if(!c)x=B;` init-then-override form), a throwaway
    boolean-expression call arg `(c!=K)+N` whose temp spills (Rule 155 —
    reassign `c` to the constant), or cached global array
    elements (Rule 63). The diagnostic prints `structural (RC over-enregisters)`.
    Worked: `figure_update` 326→320 by inlining `figure_list[]`/`unit_list[]`,
    switch→if/else-if, and the init-then-override `size` form (residual is a
    Rule 111 spill tie on the global loop counter `figure_no`).
  * **Equal push count (~24/28).** The Rule 116 / pressure-spill class —
    disambiguate with the disasm:
    * **(a) superfluous named local** PS held in a register → inline it
      (generalised Rule 116). The clean, source-fixable case.
    * **(b) a loop-invariant PS reloaded, or a genuine pressure spill** →
      Watcom hoisted a global-pointer load out of a loop (occupying a register
      across all iterations) where PS reloaded it each iteration, **or** the
      function is simply over-pressured. This is a Rule 111 / Spill-class tie and
      is frequently NOT cleanly source-fixable — the invariant local is
      re-hoisted even when you assign it inside the loop body (verified on
      `get_region_over`: `unsigned char *sb = scratch_buffer;` inside the `for`
      did not stop the hoist).
* **PS bigger (PS spills more, 38/66).** PS's allocator was memory-constrained
  (an ordinary regalloc eviction / rematerialization, Rule 111) or PS named temps
  we inlined. Less reliably source-fixable; do not blindly add locals.

### Validation (two independent code paths agree to the slot)

The frame-delta (`sub esp` immediate, parsed directly) and the live-range
capacity model (`regalloc_explain`'s `RC spills ~N value(s)` line, computed by a
completely separate walk) **agree to the exact slot count**:
`evolve_a_cm_row` +7 slots ↔ "RC spills ~7"; `get_region_over` +1 ↔ "RC spills
~1". And the existing `reload_hint` (Rule 116) fires on **0 of the 66** — the
frame diagnostic fills a real gap, it is not a restatement of an existing hint.

### Tooling

* `decomp-verify -v` prints a `Frame:` root-cause line (slot delta, prologue
  push counts `PS n/RC m`, ROOT-of-cascade flag, the `WorthProlog
  spill-vs-callee-save` tag when applicable, sign-based fix direction). `--json`
  carries `functions[].frame_hint` (`ps_frame`, `rc_frame`, `delta`,
  `slot_delta`, `is_root`, `direction`, `ps_pushes`, `rc_pushes`,
  `worthprolog_swap`, `fix`).
* Implementation: `c2/commands/frame_hints.py`; tests
  `tests/test_frame_hints.py`. Companion to Rule 107 (which is the same-size
  slot *swap*; Rule 117 is the total-size *delta*).

### Discovered

Corpus analysis 2026-06 (this session). Disasm count: PS.EXE contains only **52
`setcc` instructions across all 2261 functions / 518 KB** (48 functions, mostly
1 each) — see Rule 26/53. Any recompile `setcc` paired with a non-`setcc` PS row
is therefore a near-certain source-shape error (PS wrote `if (cond) x = 1;` with
a pre-zeroed slot and branches, not `x = (cond);`).

## Rule 118 — A global that is tested then passed as a call argument is RELOADED for the push; cache it through a temp AFTER the guard

### Symptom

A function checks a global and then passes that same global as a call
argument, e.g.

```c
if (smacker_open) return 1;
SetSmackAILDigDriver(dig, smacker_open);   /* arg 2 = the just-tested global */
```

PS loads the global once and reuses it (`mov edx,[g]; test edx,edx; …;
push edx`); our build emits an extra reload for the push, which advances
the push-scratch rover one position and bumps every later call-arg /
const-store up a register — and when the caller-saved ring runs out, into
an extra callee-save `push esi`/`pop esi`.  Looks like a register swap or a
gratuitous extra spill.

### Cause (Ghidra-verified: `Enregister`, wcc386 va 0x62939 = owv1 i86ldstr.c)

`Enregister` RISCifies a `PARM_DEF`'s memory operand **unconditionally** —
there is no "is this value already in a register" check.  So the second
read of the global (as the call arg) is always turned into a fresh load =
one extra `FindRegister` rover advance.  `Score` later coalesces the load
back to `push <reg>`, but only AFTER the rover already cascaded.  (See the
decomp-verify `Parm-reload:` hint and watcom10.0a `docs/parm-reload-rover.md`.)

### Right C

Copy the global into a temp **after the guard** and pass the temp:

```c
int o;
if (smacker_open) return 1;
o = smacker_open;                     /* 0 past the guard; faithful */
SetSmackAILDigDriver(dig, o);         /* arg is a TEMP, not N_MEMORY -> no reload */
```

The guard test stays a DIRECT read (so it keeps PS's register, usually the
rover's EDX); the arg references the temp, so `Enregister` skips it — no
extra rover advance; `Score` coalesces the temp into the guard's live reg,
emitting the same `push edx` PS has.

**Placement is the whole trick.**  Caching *before* the guard
(`int o = g; if (o) …`) puts the TEST on a named temp, which `GiveBestReg`
allocates from `DoubleRegs[0] = EAX` (not the rover's EDX), shifting
everything.  Cache only the arg, after the guard.

### Discovery

`link_to_smacker` (`pcsound.c`), byte-exact.  Related: the Rover lever
(decomp-verify SKILL), Rule 89 / Rule 117 (the extra esi looks like a
capacity spill but is this reload cascade).

---

## Rule 119 — A function that builds a multi-byte composite into a NAMED accumulator with compound assigns and byte-zext loads regalloc-OVER-allocates the accumulator to EAX

### Symptom

The function has a body like

```c
int r;
r  = (unsigned char)mem[i + N0];
r <<= 16;
r += (unsigned char)mem[i + N1] << 8;
r += (unsigned char)mem[i + N2];
return r;
```

(or any equivalent: multiple compound assigns / byte-zext loads piped
into a single accumulator that's also returned).  Diff vs PS is a
register-identity swap WITHIN the DoubleRegs class — your `r` lives in
EAX, PS's `r` lives in EBX, with byte temps mirrored (EBX↔EAX).
`regalloc-explain` says "no register-class divergence" / layer-3 or
layer-4 Reg-swap.

### Cause (OW source-verified)

OW v1 ``regalloc.c::CountRegMoves`` scores each (conflict, candidate
reg) pair by walking the IR.  Two kinds of bonus accrue:

* **MOV bonus** ``count += tree->size`` (≈ +4 for 32-bit): a MOV between
  the conflict's value and the candidate register saves an instruction.
* **Commutative-RMW bonus** ``count += half`` (≈ +2): for
  ``OP_ADD``, ``OP_EXT_ADD``, ``OP_MUL``, ``OP_AND``, ``OP_OR``,
  ``OP_XOR`` only — *not* ``OP_LSHIFT``, *not* ``OP_SUB``.

In the accumulator-workhorse form above, every byte load goes through
``r`` (because the first one is ``r = byte`` — an explicit MOV +4 to
``r``'s CRM(EAX)), every shift is on ``r`` (LSHIFT contributes nothing,
but consumes one IR instruction-slot in ``r``'s walk), and the
``return r`` adds another +4 via the return MOV.  ``r`` claims EAX by
having the highest CRM total.  Byte temps from the inline byte-zext
loads scatter to whatever caller-save remains (BL/DL).

### Right C — route byte loads through a SCRATCH local

Add ``int t;`` and rewrite so that **every byte load lands in t**,
**every shift acts on t in-place**, and ``r`` does nothing except
``r = t`` / ``r += t`` / ``return r``:

```c
int r, t;
t  = (unsigned char)mem[i + N0];
t <<= 16;
r  = t;
t  = (unsigned char)mem[i + N1];
t <<= 8;
r += t;
t  = (unsigned char)mem[i + N2];
r += t;
return r;
```

Now ``t`` has THREE byte-load MOV bonuses (+12 to CRM(EAX), since AL is
the natural byte-load destination), winning EAX as the highest-savings
conflict.  ``r`` keeps only the return-MOV bonus (+4) and falls to
EBX (next callee-save).  Matches PS bit-for-bit on the canonical case.

### Discovery

``get_buffer_ofset`` (``lib32.c``), 28b → 0 byte diff via
``c2.commands.cgex`` decomp-bound CRM-table sweep.  After ~30
expression-shape variants showed no movement on the EAX-claim, the
**op-count-among-named-values** axis was varied: shifting the byte
loads + shifts onto a fresh ``t`` local flipped the allocation.

### Hint

``c2.commands.byte_pump_hints.detect(fn_name)`` returns a ``BytePumpHint``
when this pattern fires.  Wired into ``decomp-verify``'s `-v` output as
`Rule 119`.  Cross-reference: the worked-example experiment lives at
``docs/codegen-experiments/get_buffer_ofset.py``; the regalloc model
is in ``watcom10.0a repo docs/wcc386-re/regalloc-model.md`` §4.

## Rule 121 — Duplicated-tail rover advance: shared arm-tails written inside each arm shift the RISCify scratch picks (ComTail erases the bytes, LdStAlloc keeps the advance)

### Pattern

A pure register-identity swap (e.g. `mov ebx,[g]` vs PS's `mov ecx,[g]`)
on a **RISCified scratch** — a compare load (`mov reg,[g]; cmp reg,imm`)
or call-arg push scratch — in the **second-walked arm** of an
if/else-if whose arms share a common tail (a call + cleanup stores).
`c2 regtrace` shows **no conflict** bound to the diverging register: the
pick comes from the FindRegister rover, not GiveBestReg (the `fr` trace
records it; the alloc table doesn't).

Worked examples: `print3_test_info` (pm_map3.c, 3 b → exact),
`print_test_info` (pm_map1.c, 98 b → exact).

### Mechanism

* `LdStAlloc` (i86ldstr.c; 10.0a @0x5A43D) walks the **block list in
  creation order — not layout order** — forward within each block, and
  every `Enregister`-able op (non-move with a memory operand) advances
  the shared per-type-class rover via `FindRegister` (10.0a @0x62a29,
  `RoverDouble` @0x77DB8, ++-first).
* The advance survives even when `LdStCompress`/`CompressIns` CISCifies
  the op back to its memory form (`sub reg,[mem]` → zero extra bytes):
  **byte-invisible cursor advances**.
* When the source hoists the shared tail AFTER the if/else, the tail's
  block sits after both arms in the block list: both arms' compare
  scratches are picked back-to-back (EDX, EBX).
* When the source **duplicates the tail into each arm**, the first arm's
  tail ops (e.g. the `sub ecx, pm_diamond_width` arg compute) are walked
  **between** the two compare picks → +1 advance → the second pick lands
  one register later (EBX → ECX).  `ComTail` then merges the two
  identical tails back into one block of bytes — the duplication is
  invisible in the output, except through the rover.

### Lever

Write the shared tail **inside each arm** (PS's debug-print style).
Diagnose with the `fr` trace + `tools/rover_sim.py` (watcom10.0a): if a
`+1` injection between the two dword picks reproduces PS's registers and
self-heals downstream, this is the rule.  Block-list walk order in the
trace is readable off the `fr` records' source lines (here:
B1, B3, B4(+tail), B2(+tail), i.e. conditions first, then true-arms in
reverse, tails inline).

### 2026-07-10 refinement — the tail must include a CALL to survive the pre-walk re-merge

A **statement-only** duplicated tail (e.g. `sprite_x += w; continue;` in
each arm) is re-merged by a post-emission pass BEFORE LdStAlloc walks it
(`c2 spell` screens it INERT@BURN: births diverge, walk identical) — the
advance never materialises.  Duplicating the tail **including the arm's
call** (`place_diamond(0); sprite_x += w;`) blocks that pre-walk merge:
the dup survives to the walk (`spell` = LIVE with the exact advance
delta) and ComTail still erases the duplicate bytes afterwards.

Byte-safety is decided by PS's witnessed layout, so byte-compile after
screening:

* **PS's layout IS the merged-dup form** (ComTail jmp-to-first-copy,
  the merged jmp carrying the duplicated statement's own `-d1` mark) →
  the lever closes.  Worked: `mid3_line_no_sides_base` — per-arm
  `place_diamond(0); sprite_x += pm_diamond_width;` in the terrain
  sub-arms + a `tile == 0` arm with its own add (WIN-/Od-witnessed)
  added the +2 dword advances, killed the `mov ebp,0xf`
  CompressIns-non-fusion knot, isl 4→3, win struct-diff 33→24
  (15cd1284).
* **PS's layout shows a cross-arm `goto`/shared-tail jmp** (a jump INTO
  another arm's call site) → the dup makes ComTail build a NEW
  intra-arm merge point instead, and bytes regress even though the
  advance count is right.  Counter-example: `show_battlemap_base`'s
  top-terrain `goto top_draw` (296→313bd, isl 3→5; b5d891d9).

Read PS's form off `c2 disasm`: a merged duplicate leaves the jmp
carrying its own line mark; a shared tail leaves the jmp unmarked.

### Relation to other rover levers

Same cursor mechanism as the call-arg rover (+k coalesced-load /
LOOP-INVARIANT-CONST / Parm-reload levers in `watcom10.0a repo docs/wcc386-re/rover-model`
notes), but the trigger op is a **compare scratch** and the +1 comes from
**block-list reordering via tail duplication** rather than an extra load.

## Rule 122 — if/else ARM ORDER steers the LdStAlloc rover walk (block-creation order; bytes identical either way)

### Pattern

A rover-class register swap (the diverging register has NO row in the
alloc table — pure FindRegister pick) on an op inside ONE arm of an
if/else, where the `fr` trace shows the OTHER arm's ops advancing the
cursor BEFORE it.  Worked example: `update_time`'s arena block — our
`if (population >= 500) { arena_top_count++; … } else { arena_top_count = 0; }`
walks the else-store before the RMW (fr: L229 → L226), so the RMW
scratch lands EBP; PS has EDI.

### Mechanism

`LdStAlloc` walks the **block list in front-end creation order** (Rule
121's substrate).  The tree burner creates arm blocks in **source arm
order**, so `if (A) X else Y` vs `if (!A) Y else X` produce the same
emitted bytes (layout is CFG/fall-through/tail-merge driven) but
opposite rover-walk order for X's and Y's RISCified ops.

### Lever

Invert the condition and swap the arms.  For update_time the PS form
(also matching the line cues) is:

```c
if (population < 500) arena_top_count = 0;
else if (++arena_top_count > 12) arena_top_count = 0;
```

26 b → 22 b (register-exact; the rest is a donor-blocked epilogue merge).

### Diagnosis recipe (the fr reorder test)

When a single `+k` injection does NOT reproduce PS (`rover_search`
fails), try **removing or reordering** whole events in the fr stream and
re-simulate: a LOCAL SWAP of two adjacent-arm event groups that
reproduces ALL of PS's kept picks (later picks unchanged) is this rule;
a pure removal that reproduces them is Rule 121 / a one-store form.

## Rule 123 — in-place compound op MERGES temps; combined savings reorder the allocation walk

**Signature.** A whole-function register-identity swap where PS's pick implies a
conflict allocated *earlier* than its apparent savings allow — e.g. a byte temp
in BL while the dword local that would own EBX sits in ECX, when our build
allocates the dword first (EBX) and the byte temp gets CL.

**Mechanism.** `CalcSavings` totals memory-ref savings per conflict and
`SortConflicts` allocates in savings-descending order.  A split source form —
`char hi = step << 4;` or even the rvalue `step << 4` — creates TWO byte temps
(load temp + shift-result temp, e.g. sav 30 + 20), each ranking below a
competing dword local (sav 41).  The in-place compound form `step <<= 4` keeps
the result in the SAME temp: one conflict with the SUMMED savings (≈50) that
now outranks the dword, allocates first, takes BL, and forces the dword to ECX.

**Lever.** Write the compound assignment in place and use the variable
afterwards: `step <<= 4; wf_steps[j] += step;` — NOT `wf_steps[j] += step << 4;`
and NOT a named intermediate.

**Proven.** `copy_ferret_run_to_army` (161b) and `copy_ferret_run_to_citizen`
(154b) both code-exact (cluster-#32 trailing pad only).  The al-row savings
show the merge directly: split forms keep `byte 30 + byte 20 < dword 41`;
the in-place form's single byte conflict outranks `j`.

**Detection.** al rows: two same-class temps whose savings SUM exceeds the
diverging pick's owner — surface as a "merge candidates" hint.

## Rule 124 — GiveBestReg mechanics: per-candidate score (gb), homing-MOV credit, GivenRegisters tie-break

The `gb` trace record (one per candidate surviving with.regs/except/
TooGreedy, with its CountRegMoves score) makes register-home questions a
direct read.  The pick is: **argmax saves; tie → first candidate already ⊆
GivenRegisters; else candidate-list order** (GiveBestReg@0x57b78).

Three proven sub-mechanisms (change_lv, 250b → EXACT):

1. **Savings order = allocation order; loop-bound references inflate
   savings.**  `for (..; gmn_x < x + extra; ..)` charges extra with
   deep-loop refs (sav 111) so it allocates before delta (98) and takes
   ECX with its homing credit.  The original's `height = extra + radius*2;
   width = height;` (accumulate onto the dying parm, then COPY) kills
   extra's loop refs → extra allocates LAST (→EBP).

2. **Parm-homing MOV credit** (CountRegMoves@0x57728): a `MOV
   <parm-reg> → <other-conf>` inside this conflict's range gives +half
   credit for that register even though the MOV doesn't involve this
   conflict.  delta's range contains the `MOV ECX→extra` homing →
   CountRegMoves(delta, ECX) > 0 → ECX beats EBX despite list order.

3. **GivenRegisters tie-break cascade**: when all scores are 0, a
   candidate already inside GivenRegisters beats an earlier-listed one
   that isn't.  After a byte conflict (nv→AL) forces the store-addr temp
   off EAX onto EDX, every later zero-score temp tie-breaks onto EDX.
   Lever: reorder which temp allocates first by SPLITTING a statement —
   `nv = map[..] + (char)d` (one temp, sav 400 store-side first) vs
   `nv = map[..]; nv += (char)d;` (load-side temp outranks) — the latter
   lets the load temp take EAX before EDX enters GivenRegisters.

Workflow: read the al rows' `cand_scores` (gb), find the diverging pick,
and ask which of the three knobs moves it: savings order (statement
shape), a homing/MOV credit (live-range boundaries), or the Given
tie-break (allocation order of zero-score temps).

## Rule 125 — Optimizer code MOTION across functions: CallRet + StraightenCode haul a tail-callee's head to the caller; source position ≠ symbol address (zero -d1 line records is the marker)

**Discovery (2026-06-10)**: the long-standing `helping` mystery — its
52-byte body sits at 0x32409 with **zero -d1 line records** while a
40-byte continuation carrying lines L1693–1697 sits at 0x324C9, past
`act_about`'s `ret`.  Suspected LX/debug parser bug; the parser was
correct.

### Mechanism (owp4v1copy/bld/cg, behavior-confirmed on 10.0a)

The peephole optimizer's instruction queue (`optins.c`/`optpull.c`/
`optcom.c`) spans FUNCTION BOUNDARIES (the same machinery as Rule 42
ComTail).  Three transforms physically relocate code:

1. `CallRet` (optpull.c): `call X; ret` → `jmp X` (tail call).
2. `StraightenCode` (optpull.c) — "hauling code up to jump": when the
   queue front reaches an unconditional `jmp X` and X's body is still
   in the queue (defined LATER in the TU), it MOVES the block
   `[X's label .. first unconditional jmp/ret]` — which can span
   conditional branches and calls — up to the jump site and deletes
   the jmp (fall-through).  The function's SYMBOL travels with the
   moved label.
3. `CloneCode` (optpull.c): duplicates blocks ≤ 40 b at the jump site;
   the clone loop explicitly skips `OC_INFO`.

`NextIns()`/`PrevIns()` (optutil.c) **skip `OC_INFO` entries**, so the
moved head's `OC_LINENUM` records are ORPHANED at the original
emission position; `MultiLineNums` collapses consecutive orphans to
the LAST one.  Observable signature in the binary: the moved body has
**zero line records**, and the first surviving record after the
un-moved remainder is the function's first not-hauled line.

### Worked example — helping (action.c): 5 b + 1 b → 0 in one move

PS source order was: act_help_game (L1655, body `helping(1);`),
act_help_history, act_help_icons, act_about (L1670–82), **helping
(L1684–97)**, act_rewind_help (L1699).  CallRet turned act_help_game's
tail call into `jmp helping`; StraightenCode hauled helping's head
(through its first unconditional `jmp`, exactly 52 b) up to 0x32409;
the remainder stayed at 0x324C9 (the phantom "act_about+0x70 donor"
the tail-merge scanner reported).  Moving `helping`'s DEFINITION after
`act_about` in our source made helping, act_help_icons, act_help_game,
act_about (7 functions compared) all byte-exact — the optimizer
reproduces the haul deterministically.

### Tooling

* `c2 moved-code [<fn>] [--json]` — scans for the zero-line-record
  signature and classifies: **hauled** (trailing jmp into a LATER-line
  region; hint names the define-after/define-before functions),
  **tail-consumed** (trailing jmp BACKWARD into an earlier-line donor:
  ordinary Rule 42, position fine), **relocated** (ret-ender; no
  pointer back).  Corpus: 5 functions (helping ✅ hauled+fixed;
  fade_to_palette/vhigh_beep/clear_all_cm tail-consumed;
  set_palette relocated-but-exact).
* `decomp-verify -v` prints a `Moved-code:` header; `--json` carries
  `functions[].moved_code`.
* `c2 func-order` exempts moved-code functions from the source-order ==
  address-order invariant (their symbol address is an optimizer
  artifact).

### Corollary — trailing jump-table filler (cluster #32) is lc-parity, not a version delta

The same investigation disproved the "wcc386 version delta" theory for
the trailing-table NOP filler: PS itself emits NOP pads
(fight_barbarian: PS `8d 40 00` vs RC `8b c0`), neither build 4-aligns
tables, and the pad length tracks the section location counter at the
pad point — i.e. cumulative upstream TU layout.  Expected to self-heal
when the TU is fully byte- and size-exact.  Full analysis:
docs/jump-table-alignment.md (2026-06-10 revision).

## Rule 126 — byte-value register seat: zext-overlap / address-temp masks (the AL-squat mechanism)

**Signature.** A byte value our build seats in AL (with in-place
`and eax,0xff` extension) where PS seats it in DL/DH (with separate
`xor eax,eax; mov al,<b>` extensions).  ~14 functions, the BYTE-reg
bucket.

**Mechanism (grounded, watcom10.0a docs/regalloc-mechanics.md).**  The
seat is interference, not preference: `NeighboursUse` runs at
GiveBestReg time, so a byte conflict allocating AFTER an EAX-holding
temp that overlaps its live range gets AL/AH masked (channel C) and
falls to the D family.  Two proven mask vehicles:

1. **Zext-overlap**: a byte value live ACROSS a separate extension temp
   (because a second `||` group re-extends it) is masked by that temp's
   EAX.  A *dying* convert use creates no interference — single-use
   values keep AL and the extension folds in place.
2. **Address-temp**: `mov eax,[base]; mov dl,[eax+a]; mov dh,[eax+b]` —
   the address stays live to the SECOND field load, masking the FIRST
   byte value loaded.

**Levers.**  Test grouping (separate `||` groups → separate extensions;
pooled dword compares → one in-place extension), field load order, and
the byte conflict's savings rank vs the EAX temps (Rule 124: allocation
order = savings order; the masked value must allocate after the
masker).

**Lever — widen the byte locals to `int` (proven, 2026-06-13).**  When
the diverging locals are byte-mask values (`unsigned char x = field &
MASK;`) the AL-squat byte-seat coloring is what diverges from PS on
*every* row.  Re-declaring them as `int` removes the byte-register
seating problem entirely — the values become D/A *dword* conflicts that
follow PS's control-flow + compare structure — and can halve the diff.
Semantically identical (the loads are still byte loads; the masks and
compares are int-promoted exactly as C already specifies).

* Worked: `get_education_ov_image` (landfill.c) 92 b → 44 b by widening
  all four of `kind`/`flags`/`school`/`academy` from `unsigned char` to
  `int`.  The full byte/int type matrix (16 combos) + 24 decl perms were
  swept; `(int,int,int,int)` is the floor (residual 44 b is the
  remaining `school→EAX`/`academy→EDX` vs PS `DH`/`DL` seat split + the
  `kind` zext-compare form, with no further source lever).
* **Shape caveat — only the bare-AND idiom benefits.**  The lever is
  specific to `field & MASK` (no shift).  It *regresses* the shifted
  siblings that compute `(field & MASK) >> n`: measured
  `get_entertainment_ov_image` 99→105, `get_industry_ov_image` 104→109,
  `get_water_ov_image` 84→110 (the latter also has a `terrain` D-family
  seat swap).  So apply per-function, verify, and keep `unsigned char`
  where the byte arithmetic involves a shift.

**Status (RESOLVED 2026-06-18).**  Both byte-exact.
* `get_education_ov_image`: closed 44 b → 0 b with **all-`unsigned char`**
  (NOT the int-widen lever above — that was a local 44 b minimum, not the
  floor) + `kind` declared LAST (Rule 115) + `= 0` store (Rule 156).
* `get_industry_ov_image`: closed 99 b → 0 b — the byte-seat IS flippable
  here, the "savings rank" was a Rule 115 **declaration-order** tie.
  Declaring `industry` BEFORE `kind` moves industry off AL into DH (and
  frees EAX for the eax-scratch kind widen); the `|| kind==0xfa` must also
  be spelled as a tail-merged two-if (block order [range][store][fa]) and
  the else store as `= 0` (Rule 156).  So the int-widen lever in this
  section is a *local* improvement, not the global floor — sweep the full
  type × decl-order × structure × store space (and try the all-uchar
  byte-seat form) before declaring an int-widen floor.

## Rule 141 — One-sided `xor <argreg>, <argreg>` before a shared call: the other side passes a LIVE value

### Symptom

A diff row where ONE side emits `xor edx, edx` (or ebx/ecx) just before
a `call` both sides share, with only equal arg-staging rows in between.

### Cause

The side WITHOUT the xor passes a **variable** that is already live in
that argument register — typically the value computed or incremented
immediately above (CSE keeps it in the arg register, no setup needed).
The side WITH the xor passes literal `0`.

### Fix

* RC-only xor → the argument is a variable, not `0`.  Trace what PS's
  register holds at the callsite (`c2 disasm`) and pass that
  expression.  Worked: `chance_of_attack(3, months_since_last_war, 0, 1)`
  in war_trouble (PS's EDX still held `months_since_last_war` from the
  `++` above; our literal `0` emitted the extra xor);
  `try_a_citymap_square`'s 3rd arg in citizen_maraude_to_target.
* PS-only xor → our source passes a variable that happens to sit in the
  register; PS passes literal `0` — replace the argument with `0`.

### Detection

`decomp-verify -v` auto-fires (`_find_rule_141_rows`): one-sided
self-xor of edx/ebx/ecx, all following rows EQUAL register staging up
to an EQUAL call within 6 rows.  EAX is excluded (a one-sided
`xor eax, eax` is usually return-value setup).  Structured-operand
based (`c2/commands/insn_ast.py`), no text matching.

Discovery: bbarian.c *_trouble family (2026-06-12, all byte-exact).

## Rule 142 — Return constants staged via EDX: the merged-return-suffix (&&-guard) shape

### Symptom

PS `mov edx, K` vs RC `mov eax, K` (same constant), with PS's next
instruction `mov eax, edx` feeding the epilogue; the PS return-0 block
is `xor edx, edx; jmp <the mov eax,edx>` (a backward jmp into the
shared suffix).

### Cause

PS's source funnels its return paths so each materialises the return
value in a common staging register (EDX), then shares one
`mov eax, edx` + epilogue via ComTail.  Plain per-site `return K;`
emits the constant directly into EAX and the suffixes don't merge.

### Fix

The &&-guard shape:

```c
if (guard1() && guard2()) {
    ...body...
    return 1;
}
return 0;
```

Worked: revolt_trouble (15 b → 0 once the whole *_trouble family
adopted compatible shapes — the donor geometry is coupled across the
TU).  Byte-exact corpus witness: known_world (empire.c).

### Detection

`decomp-verify -v` auto-fires (`detect_rule_142`): replace row
`mov edx, K` / `mov eax, K` (same K, from decoded immediates) whose
next PS row is `mov eax, edx` and next RC row (if any) is pop/ret/jmp.

## Rule 143 — Consecutive compound RMWs on ONE memory lvalue: store-forwarding emits a byte-reg copy chain

### Symptom

PS shows a byte-register **copy chain** — `mov b2, b1` between byte ALU
steps, ONE load, ONE final byte store:

```
mov  dh, [m]        ; single load
and  dh, 0xe3
mov  bl, dh         ; <-- copy
or   bl, dl
mov  bh, bl         ; <-- copy
and  bh, 0x9f
mov  [m], bh        ; single store
```

while RC fuses the ALU steps in place on one register and stores.

### Cause

The source is consecutive compound RMWs on the SAME memory location:

```c
cell->occupant &= 0xe3;
cell->occupant |= cur_lvl;
cell->occupant &= 0x9f;
```

Watcom store-forwards each statement's load from the previous
statement's pending value and dead-store-eliminates the intermediate
stores: one load, a **fresh byte register per statement** (the copies),
one final store.  Later reads of the field (e.g. `cell->occupant |= 0x20;`
in following arms) forward from the last register, giving per-arm fresh
regs — which also keeps the arms' stores byte-distinct and therefore
NOT ComTail-mergeable (matching PS's inline per-arm returns).

### Fix

Write the consecutive compound RMWs on the lvalue itself.  Do NOT use
the Rule 17 register split — on a memory lvalue a temp-based split
emits two separate RMWs and regresses.  Worked: do_land_trade
(171 b → 0).  Caveat: fusion is pressure-sensitive — in one site
(road_ramifications' wall arm) the split regressed and the combined
single-expression form stayed closer; verify per function.

### Detection

`decomp-verify -v` auto-fires (`_find_rule_143_rows`): PS-side byte
`mov reg, reg` copy whose forward window holds ≥1 byte ALU then a byte
store, with fused-RC evidence (in-place byte ALU or byte store) in the
same window.  Claims its rows BEFORE Rule 17 (whose register-lvalue fix
would mislead here).

## Rule 144 — `while (i++ < N)`: post-increment tested at the top

### Symptom

PS's loop head is

```
mov  eax, ecx        ; copy the OLD value
inc  ecx             ; counter advances
cmp  eax, 0x14       ; compare the OLD value
jge  exit
```

with a backward jump targeting the `mov`.  RC (from a for-loop) puts
the `inc` at the bottom and compares the counter directly.

### Fix

```c
i = 0;
while (i++ < 20) { ... }
```

Only the top-tested post-increment produces the copy-old / inc /
compare-old triple.  Worked: get_region_invasion_points (93 b → 0).

### Detection

`decomp-verify -v` auto-fires (`_find_rule_144_rows`): PS triple
`mov rA, rB` / `inc rB` / `cmp rA, imm` where the `mov` is a
backward-jump target and at least one of the three rows diffs.

## Rule 145 — Signed `% (1<<k)` vs `& (2^k - 1)`

### Symptom

One side computes a signed remainder —

```
mov  ebx, 8
mov  eax, edx
sar  edx, 0x1f
idiv ebx            ; remainder in edx
```

— where the other side masks (`and reg, 7`).

### Fix

They are NOT interchangeable: `%` has signed semantics (negative
operands).  Write whichever the PS side shows — `x % 8` when PS has the
idiv sequence, `x & 7` when PS masks.  Worked: barbarian_invades_city's
`dir = (world_dir + 4) % 8` (the `& 7` spelling was a semantic bug).

### Detection

`decomp-verify -v` auto-fires (`_find_rule_145_rows`): an `idiv rD` on
either side with `mov rD, 2^k` within 4 same-side rows, and an
`and r, 2^k-1` on the OTHER side within ±4 rows, near a diff.

## Rule 146 — De-invent the local: repeated field reads CSE into the callee-save

### Symptom

A compare chain where RC tests EAX (`3D imm32`, 5-byte encodings) and
PS tests a callee-save (`81 /7 imm32`, 6-byte) with the SAME
immediates — the 1-byte deltas cascade through every later jump.  The
defining row is a memory load into the respective registers.

### Cause

Our source declared a named local (`strength = army_list[i].total_troops;`)
which Watcom fused into EAX.  PS's source had **no local** — it re-read
the global/field in each `else if`, and Watcom's CSE unified the
repeated reads into ONE load homed in a callee-save (the CSE temp
allocates differently from a named local).

### Fix

Delete the local and spell the memory read in each compare:

```c
if      (army_list[i].total_troops >= 0x320) count = 9;
else if (army_list[i].total_troops >= 0x258) count = 7;
...
```

Worked: barbarian_invades_city (total_troops → EBX, 264 b → 0),
continue_battle (battle_state → EBP), get_morale_and_readiness.  This
is the compare-chain instance of Rule 116 (inline memory-rooted reads,
don't hold them).

### Detection

`decomp-verify -v` auto-fires (`_find_rule_146_rows`): ≥2 replace rows
`cmp <callee-save>, K` vs `cmp eax, K` (equal K, single PS register
across the chain), anchored on the `mov <reg>, [mem]` def row when
present.

## Rule 147 — Array element width/stride mismatch: scaled dword vs unscaled byte loads

### Symptom

PS reads a 4-byte field through a scaled index —
`mov edx, [edx*4 + tribe_to_troop_numbers]` — where RC (within a few
rows, usually on misaligned insert/delete rows) reads a 1-byte field
unscaled through the SAME index value —
`mov bl, byte [edx + tribe_to_troop_numbers]`.

### Cause

The array's element/field type is declared with the wrong width in
`entities.h` / `_TYPE_OVERRIDES`.  Width and stride diverge TOGETHER
(operand size AND addressing scale), which separates this from any
regalloc effect.

### Fix

Fix the declaration; one header edit moves every user.  Worked:
`struct troop_numbers_rec` fields are `int`, not `unsigned char` —
flipping it moved all four *_trouble functions at once.

### Detection

`decomp-verify -v` auto-fires (`_find_rule_147_rows`): a scaled (×2/×4)
dword load on one side and an unscaled byte load on the other within
±5 rows, paired through base == index register (the same index value).
Function-level scan because the aligner rarely puts the two loads on
one row.

## Rule 150 — `goto label;` (mid-function) vs `return;` (epilogue) — INVERSE of Rule 148

### Symptom

Multiple jcc/jmp sites where PS jumps to the function epilogue
(`pop…pop;ret`) but RC jumps to a mid-function LABEL whose body is
`if (...) return;` plus cleanup code:

```
PS  +0x050  je 0x445   ; -> epilogue (pop ebp; pop edi; … ret)
PS  +0x059  je 0x445   ;    "
PS  +0x062  je 0x445   ;    "
RC  +0x050  je 0x3fb   ; -> mid-function label (`if (restart_flag) return;`)
RC  +0x059  je 0x3fb   ;    "
RC  +0x062  je 0x3fb   ;    "
```

Targets differ by tens to hundreds of bytes (the size of the mid-function
cleanup block).  Multiple sites converge on the same target.

### Cause

Our source has

```c
if (state == X) goto cleanup_check;       // RC: je 0x3fb (label)
...
cleanup_check:
    if (restart_flag != 0) return;
    /* … cleanup code that the early-exit paths should SKIP … */
}
```

PS's source skips the cleanup entirely on these early-exit paths:

```c
if (state == X) return;                   // PS: je 0x445 (epilogue)
```

The cleanup is reachable only via the natural fall-through from the
preceding block.

### Fix

Replace each `goto <label>;` with `return;`.  Watcom emits a `jmp` to
the epilogue exactly as PS, and the cleanup remains reachable via
fall-through.  Semantically equivalent when the early-exit paths
represent terminal-state cases (game-over, abort, etc.) where the
cleanup is irrelevant.

Worked: `main_game_loop` (gloops.c, 454 b → 0); three `if (game_state
== 1/2/3) goto restart_check;` sites all rewritten to `return;`.

### Detection

`decomp-verify -v` auto-fires (`_find_rule_150_rows`): finds ≥ 2
jcc/jmp rows where both sides have the same mnemonic at the same
offset, PS's target lands at a `pop…pop;ret` epilogue, RC's target is
mid-function (not an epilogue), and the gap is ≥ 20 bytes.  Requires
multi-site convergence to distinguish from Rule 92 (single-site
goto-funnel).

INVERSE of Rule 148:
- Rule 148: PS funnels via `jmp <end>`, RC inlines per-exit
  epilogues (multi-pop+ret blocks).  Fix: rewrite returns as
  `goto end;` + `end:;` sentinel.  Triggered by big epilogues
  (> 5 bytes, CloneCode threshold).
- Rule 150: PS funnels via `return;` (jmp to epilogue), RC funnels via
  `goto <mid_label>;`.  Fix: rewrite goto sites as `return;`.
  Triggered by goto-label sites where the label has cleanup the
  early-exit paths should skip.

### Rule 151 — `int` vs `short` local: the `movsx`/`cwde` sign-extension diagnostic

When a function return value or struct-field load is stored into a `short`
local and then compared against an `int` (or used as an `int` argument),
Watcom emits the narrowing store (`mov ax, …`) then widens it back
(`cwde` / `movsx eax, dx`) before the comparison.  If PS compares the
register directly (`cmp edx, 0x18`) with no preceding sign-extension,
the local was declared `int` — the value was never narrowed.

Two telltale diff-row patterns:

**Pattern A — register-to-register widening before a compare:**
```
PS:  cmp edx, 0x18                        (3 bytes)
RC:  movsx eax, edx; cmp eax, 0x18        (3+3 = 6 bytes)
```
Fix: change `short dist` → `int dist`.

**Pattern B — field-load width (`movsx` vs `mov word + cwde`):**
```
PS:  movsx eax, word ptr [eax + field]     (7 bytes, 0F BF)
RC:  mov   ax,  word ptr [eax + field]     (6 bytes, 66 8B) + cwde (1 byte, 98)
```
Fix: change `short ay` → `int ay` (the variable receiving the field).

Both patterns cascade through jmp-encoding (Rule 16) because they change
the function's byte size.  Won `mouse_follow_cohort` (198 b → 0).

Discovery: 2026-06-15, by reading the PS asm bytes at the diff rows.

### Rule 152 — explicit `else if (var == K)` vs bare `else`

When PS emits `cmp reg, K; jne target` (an explicit equality check) that
RC lacks entirely (a delete row pair in the diff), the source had
`else if (var == K)` where our code has a bare `else`.  The two are
*semantically identical* when `var` can only be K at that point, but
they produce *different IL block structures*:

- Bare `else`: one basic block, the branch falls through unconditionally.
- `else if (var == K)`: two basic blocks (the check + the body), and a
  "neither" path where `var ≠ K`.

The block-structure difference cascades into:
1. Different pre-SortBlocks `next_block` chain order (what `LdStAlloc`
   walks) → different RISCify rover cursor → different scratch registers.
2. Different function size → jmp-encoding cascade (Rule 16).
3. If the function is a tail-merge dependent, the changed push set can
   break the tail-merge entirely (different prologue → near-jmp cascade).

**Signal:** PS-only (delete) row pair of `cmp reg, <small literal>` +
`jne`/`je` at a position where RC has no corresponding instruction.

Fix: change `else {` → `else if (var == K) {` with the literal from PS's
`cmp` instruction.

**Uninit-variable caveat:** adding the explicit check introduces a
"neither" path where the variable assigned in the `if`/`else if` arms
is *undefined*.  If Watcom's dataflow sees this, it may allocate the
variable to a callee-save register (extending its live range), adding
an extra push to the prologue.  PS avoids this because the neither-path
is unreachable at runtime — Watcom 10.0a does not eliminate the check
but also does not pessimize the register choice for the unreachable path
(the exact mechanism is not yet understood, but empirically both `int`
width + the explicit check together produce the PS register assignment).

Won `mouse_follow_cohort` (198 b → 0).  Discovery: 2026-06-15, by reading
PS's `-d1` line numbers to reconstruct the source structure, then
confirming via the Mac PPC Ghidra decompile (same source, different
compiler) which showed the explicit `pointer_mode == 3` test.

## Rule 153 — Cross-block CSE-defeat via disjoint product form

### Symptom

Diff row pair where PS emits a 3-insn strength-reduction sequence
(`mov R1, R2; shl R1, K; sub R1, R2`  for `R2 * (2^K - 1)`, or
`add R1, R2` for `R2 * (2^K + 1)`) at the START of an `else if` arm,
and our recompile is **MISSING the `mov R1, R2; shl R1, K`** —
emitting only the final `sub R1, R2` (or `add`).  Five bytes shorter
on our side, cascades through every downstream short-jump via Rule 16.

```
PS  +0x0bf  89 d8        mov eax, ebx       ; recompute R2*4
PS  +0x0c1  c1 e0 02     shl eax, 2
PS  +0x0c4  29 d8        sub eax, ebx       ; -> R2*3
RC  +0x0be                                  ; (nothing -- EAX still holds R2*4 from prev arm)
RC  +0x0be  29 d8        sub eax, ebx       ; -> reuses CSE'd R2*4
```

Same compiler, same flags — both PS and our build are Watcom 10.0a.
The divergence is entirely a **source-shape** difference.

### Cause

The CSE pass (`cse.c::FindRedunds`) matches IR sub-expressions by their
`OP_MUL` node identity.  In an `else if` chain where both arms multiply
the same variable by the same constant, the second arm's
`OP_MUL(x, K)` matches the first arm's, and CSE elides the recomputation
when the register is still live across the jcc.

**The byte-exact corpus is 100% disjoint product form in this context.**
Audit: 50 byte-exact strength-reduction comparison-arm sites — 9 use
disjoint `x * 3 / x * 5 / x * 7 / x * 9`, **0 use** `x * 4 ± x` /
`x * 8 ± x`.  The remaining 40 are struct-index multiplies (`arr[N]`
where the struct happens to be size 3/7 — no source spelling choice).

PS source spells the value as a **disjoint product** that has a different
IR node identity from the previous arm's multiply:

```c
/* PS source -- disjoint product, no CSE-share */
if      (x * 4 < y) ...
else if (x * 3 < y) ...    /* OP_MUL(x, 3) -- distinct from OP_MUL(x, 4) */

/* Our (broken) source -- CSE-share */
if      (x * 4 < y) ...
else if (x * 4 - x < y) ...    /* OP_SUB(OP_MUL(x, 4), x) -- shares OP_MUL(x, 4) */
```

Watcom's multiply-strength-reduction (`StrReduceMul` in `bld/cg/c/loopopts.c`)
runs **after** CSE detection, so `x * 3` lowers to the same `mov; shl 2; sub`
sequence PS emits — bytes-identical to the additive form, IR-distinct from
the previous arm.

### Fix

Rewrite additive forms to disjoint products:

| our spelling | PS spelling | lowers to (same bytes) |
|---|---|---|
| `x * 4 - x` | `x * 3` | `mov R, X; shl R, 2; sub R, X` |
| `x * 4 + x` | `x * 5` | `lea R, [X + X*4]` |
| `x * 8 - x` | `x * 7` | `mov R, X; shl R, 3; sub R, X` |
| `x * 8 + x` | `x * 9` | `lea R, [X + X*8]` |
| `x * 16 - x` | `x * 15` | `mov R, X; shl R, 4; sub R, X` |
| `x * 16 + x` | `x * 17` | `lea R, [X + X*16]` (no, scale max 8 — `mov;shl;add`) |

Shift forms (`x << K - x`) collapse the same way.

Discovery: 2026-06-15.  `get_battle_odds` 325 b → byte-exact via the
single rewrite `our_battle_men * 4 - our_battle_men` → `our_battle_men * 3`
(commit 3d184b2).  The 5-byte arm-prefix delta cascaded through every
downstream short-jmp via Rule 16, producing the full 325 b residue from
a single divergent binir line (1/17).

### Audit

The byte-exact corpus is **drained** of this pattern (the corpus survey
above found 0 byte-exact functions with the additive form).  The diffing
corpus contained exactly one occurrence (`get_battle_odds`); after the
fix, **0 candidates remain**.  The rule is documented to prevent
regressions when new code is added.

### Detection

Visible in PS asm: a `mov R1, R2; shl R1, K; <add|sub> R1, R2` sequence
at the start of a basic block reached by a `jcc` from a sibling block
that also computed `R2 * 2^K`.  Could be added as a `rule_hints` detector
fired on the asm pattern alone (no AST needed) — left as a TODO since
the corpus is currently clean.

## Rule 154 — `if (X) { body; goto L; } rest; L:` vs `if (!X) { rest; } else { body; } L:`

### Symptom

A diffing function with an `if (cond) { body_A (>=1 stmt); goto tail; } body_B; tail:`
pattern where PS asm places `body_B` (not `body_A`) immediately after the
gating jcc, with `body_A` at a far address reached via the jcc target.

The cascade hits Rule 16 (encoding) and a fall-through-size delta of 5–50+
bytes per site, producing 100–500 byte residue from a single mis-shape.

### Cause

`bld/cg/c/encode.c::DoCondJump` controls the jcc emission:

```c
if (dest_true == dest_next && dest_false != NULL) {
    FlipCond(cond);                /* flip so fall-through is the FALSE branch */
    dest_true = dest_false;
    dest_false = dest_next;
}
```

`dest_next` is the next basic block in linear IR layout — and the IL builder
keeps the iftrue body's basic blocks IMMEDIATELY after the if-test (then
iffalse, then the post-block).  So source form decides which block lands at
fall-through:

* `if (X) { body_A; goto L; } body_B; L:` ⇒ iftrue contains body_A + goto.
  IR layout: [if-test, body_A+gotoL, body_B, L].  After FlipCond:
  **fall-through = body_A** (jcc skips body_A, lands at body_B).

* `if (!X) { body_B; } else { body_A; } L:` ⇒ iftrue contains body_B.
  IR layout: [if-test, body_B, body_A, L].  After FlipCond:
  **fall-through = body_B** (jcc skips body_B, lands at body_A).

Both forms produce IDENTICAL bytes when `body_A` is empty (the IR `goto`
instruction collapses to nothing — same block layout).  When body_A has
>= 1 statement, the byte layout differs.

### Synthetic verification

`docs/codegen-experiments/goto-vs-ifelse.py` synthesizes both forms at
body_A ∈ {0, 1, 2 statements}.  Result (Watcom 10.0a, PS_CFLAGS):

| body_A | goto form size | ifelse form size | bytes identical? |
|---|---|---|---|
| 0 stmts | 44 b | 44 b | **yes** (un-distinguishable from bytes) |
| 1 stmt  | 56 b | 56 b | **no** (different fall-through layout) |
| 2 stmts | 86 b | 86 b | **no** (different fall-through layout) |

Fall-through size after the gating jcc IS the source-form signature for
body_A >= 1.

### Detection

PS asm signal (visible without source-PS line mapping):

1. Find the jcc that gates the if-test (a `je`/`jne` whose target is FAR
   and whose fall-through ends in an unconditional `jmp` to a shared tail).
2. Measure fall-through size in bytes (or instruction count) from the jcc
   to that `jmp`.
3. Compare with source body_A vs body_B sizes:
   * fall-through ≈ body_A size ⇒ PS source is `if (X) { body_A; goto L; }` (goto form)
   * fall-through ≈ body_B size ⇒ PS source is `if (!X) { body_B; } else { body_A; }` (if/else form)
4. If our source uses the OPPOSITE form, rewrite.

### Audit

* **Byte-exact corpus**: 2 candidates (`main`, `region_census`), both
  `body_A=0` — equivalence class, either form correct.  Zero byte-exact
  functions use `body_A >= 1` goto form (PS source style avoids it).
* **Diffing corpus**: 6 candidates.  Only those with `body_A >= 1` AND PS
  asm fall-through ≈ body_B are rewrite candidates.  Examples:
  - `sf13_autofire_missile` (body_A=1, PS fall-through=long): rewrite
    closed 220 b → 0 (commit 678e996).
  - `do_a_tutorial_page` (body_A=2, PS fall-through=16 b / 2 insns ≈
    body_A): PS uses goto form, no rewrite — confirmed by the failed
    trial that regressed 219 → 386 b.

The asm signal is the necessary disambiguator.  AST detection alone
flags candidates; the asm signal classifies them as goto-form (keep)
or ifelse-form (rewrite).


## Rule 155 — Reassign-to-constant relieves cross-call register pressure (a throwaway boolean-expression call arg)

### Symptom

A diffing function sits at the register-pressure spill threshold: its
recomp build emits a `sub esp, 4` (one spill slot) PS does not, and the
`Frame:` header reports `+1 slot; pushes PS n/RC n` (equal push count —
the slot is a genuine pressure spill, not a `WorthProlog` callee-save
swap).  The root is a **throwaway boolean-expression call argument** of
the form `(c != K) + N` (or `c ? N1 : N2` folded to `setcc`) where `c`
is a local whose *original* value is live across one or more preceding
calls.

Crucially, **both PS and RC fold the arg to the identical `setcc`
sequence** (`setne dl; add edx, 0x4b`), so Rule 26's `setcc`-vs-branch
detector stays silent — this is a *different* lever.  The bytes differ
purely because the throwaway form keeps a **7th cross-call value** alive
(the boolean temp materialised before the call), which spills; the
reassign form never materialises that temp.

### Original (PS.EXE) — `forum_industry_screen` else-arm (0x611A0 region)

PS source (confirmed by the Mac PPC witness) reassigns the `trader`
local in the else-arm:

```c
if (trader == 0) {
    ...font_no(pipe2, ...);
} else {
    if (trader == 1) trader = 0x4b;
    else             trader = 0x4c;
    write_image(game_panels, trader, 0x7c, ...);
}
```

Both builds emit, at the trader compare:

```asm
cmp  esi, 1
setne dl
add  edx, 0x4b        ; trader := (trader!=1) + 0x4b
```

— but the throwaway-expression source `write_image(..., (trader != 1) + 0x4b, ...)`
kept `trader`'s *original* live across the preceding `font_list`/`font_no`
calls (the boolean temp is computed and held), pushing the loop to 7
cross-call values → 1 spill → `sub esp, 0x1c`.  The reassign form lets
`trader`'s original die at the `cmp`; the constant result is short-lived
and consumed immediately.  6 cross-call values → no spill → `sub esp, 0x18`.
`forum_industry_screen` 619 b → 483 b (commit `d83a329`); the follow-on
`x_is = 0` literal (Rule 129) then closed 483 → 145 b (`2132646`).

### Wrong C (throwaway — spills)

```c
write_image(game_panels, (trader != 1) + 0x4b, 0x7c, i * 0x13 + 0x37);
```

### Right C (reassign — no spill)

```c
if (trader == 1) trader = 0x4b;
else             trader = 0x4c;
write_image(game_panels, trader, 0x7c, i * 0x13 + 0x37);
```

### Why

The throwaway expression `(c != K) + N` is evaluated as a
sub-expression: the compiler materialises the boolean into a register
(`setcc r8; movzx r32, r8; add r32, N`) **and that register is a new
live value** crossing any calls between the materialisation and the
consuming call.  At the 7-register pressure threshold it spills.

The reassign form `if (c == K) c = N1; else c = N2;` reuses `c`'s
**own** register/slot for the constant result.  `c`'s original live
range ends at the `cmp`; the constant result is born in the same
register and consumed immediately by the call — no extra cross-call
value, no spill.  (Both forms still lower to the same `setcc` when the
branch is simple — the spill delta is the only observable difference,
which is why this is easy to miss.)

### Proof / boundary

`docs/codegen-experiments/reassign-to-constant.py` isolates the lever
and asserts:

1. **Both forms emit `setcc`** (Rule 26 stays silent — proven distinct).
2. **Throwaway spills `sub esp, 4`; reassign spills `sub esp, 0`** at
   the threshold.
3. **Robust across pressure** (n = 2..9 cross-call values all fire
   `+4 / 0`): the throwaway's boolean temp is *always* the
   spill-triggering extra cross-call value; the reassign form never
   adds it.  (An earlier "narrow pressure window" hypothesis was an
   artefact of a buggy probe.)

Run: `uv run python docs/codegen-experiments/reassign-to-constant.py`
(prints `ALL PROOFS PASS`).

### When to apply

* The `Frame:` header shows `+1 slot` (or more) at **equal push count**
  (the `Rule 116 / pressure-spill` class — see the frame-delta
  disambiguation in Rule 116's "Tooling" section).
* A call argument is a **throwaway boolean expression** on a local
  whose original is live across preceding calls: `(c != K) + N`,
  `c ? N1 : N2`, `(c == K) + base`, etc.
* Both PS and RC emit the same `setcc` at that site (so Rule 26 does
  not fire) — the spill delta is the only symptom.

Rewrite the throwaway as a reassign: `if (c == K) c = N1; else c = N2;`
then pass `c`.  This is source-shape faithful **iff** the Mac witness
(or PS `-d1` line structure) shows PS reusing `c` for the constant —
which it does whenever PS's arg is a bare local at that call site
rather than an expression.

### Detector

Not yet auto-detected by `rule_hints.py` (Rule 26's `setcc` detector
correctly does *not* fire here, since both sides `setcc`).  The
planned detector is the AST + spill-delta gate described in
`c2/commands/reassign_hints.py` (TODO): fire when a call argument is a
`setcc`-foldable boolean expression on a local `c` that is live across
a preceding call, AND the function's `Frame:` shows a pressure spill.
The forum_industry_screen pre-fix state (RC spills 7 vs PS 6) is the
ground-truth positive; the byte-exact corpus is the negative set.

## Rule 156 — A tail store of a *known-zero register* is the byte-signature of a `= 0` source (NOT `= <that var>`); the choice is regalloc-load-bearing

### Symptom / tell-tale sign in the PS bytes

A function's final (or an early-exit) store writes a **register** to its
destination — `mov [mem], r8` — where dataflow proves that `r8 == 0` on
that path: the same `r8` was the operand of a `test r8, r8; je <fwd>`
(or `cmp`/`and`+`je`) earlier on the path and **fell through** to here
with no redefinition.  PS did **not** emit the obvious `mov byte [mem],
0` (opcode `C6 /0 00`) nor `xor r,r; mov [mem], r` — it *reused* a
register that the flow analysis already knows is zero.

That reuse is the tell-tale: it means the **source statement is `= 0`**
(or `= v` where `v` is provably 0 there), and the compiler satisfied it
by recycling the known-zero register instead of materialising a fresh
constant.  A naïve decompile reads `mov [mem], dh` as `dst = school;`
(the variable that lives in `dh`).  Byte-faithfully it is `dst = 0;`.

### Why the spelling is load-bearing (not cosmetic)

`= 0` and `= school` are **runtime-equivalent** when the path is only
reached with `school == 0` — but they are **NOT codegen-equivalent**,
because the store is also a *use* of the variable in the IL:

* `dst = school;` gives `school` an extra reference → its `CalcSavings`
  total rises by one block's worth (`regsave.c` / `savcode.h`
  `use_save`).  In `get_education_ov_image` that pushed `school` to
  `sav=4` vs the sibling byte locals at `sav=3`, so `SortConflicts`
  allocated it **first** and `GiveBestReg` greedily handed it `AL`
  (verified in the raw `-trace` `savecalc`/conflict dump).
* `dst = 0;` removes that use → `school` drops to `sav=3`, tying the
  others, and the byte-seat tie is then settled by **declaration order**
  (Rule 115).

So the known-zero store is not a peephole curiosity — it is the
upstream cause of a whole register-seat layout.

### Worked example — `get_education_ov_image` (0x3ED2A, 137 b)

PS tail:

```asm
0003EDA5  mov  eax, [cm_dptr]
0003EDAA  mov  byte ptr [eax + landfill_pool], dh   ; dh = school, proven 0 here
```

`dh` holds `school = education & 0x10`; the path to `0x3EDA5` is reached
only after `if (school != 0) return;` fell through, so `dh == 0`.  The
faithful source stores the constant, reusing the dead register:

```c
landfill_pool[cm_dptr] = 0;     /* NOT `= school` */
```

This was the third of three coupled levers that took the function from a
44 b "parked register-tie floor" to **byte-exact** (commit landing this
rule).  The full recipe — discovered by sweeping every
type × declaration-order × store-target combination in one TU against
PS — was:

1. all four locals `unsigned char` → the `kind` range-compare widens via
   the eax-scratch `xor eax,eax; mov al,bl` form, **reserving eax** so
   the live byte locals avoid it (Rule 126 / rCLRHI_R);
2. `kind` declared **last** → Rule 115 conflict-creation-order tie-break
   lands `school→DH`, `academy→DL` (packed into `EDX`), `kind→BL`
   instead of the default eax-squat fixpoint;
3. **this rule** — final store `= 0`, not `= school`, so `school` loses
   its third use and no longer outranks the others for `eax`.

Experiment: `docs/codegen-experiments/education-ov-seats.py`.

### Wrong C (reads as the variable — perturbs savings)

```c
if (academy != 0) { landfill_pool[cm_dptr] = 0x84; return; }
landfill_pool[cm_dptr] = school;   /* school gains a 3rd use → grabs eax */
```

### Right C (the constant — known-zero reuse)

```c
if (academy != 0) { landfill_pool[cm_dptr] = 0x84; return; }
landfill_pool[cm_dptr] = 0;        /* compiler reuses school's dead, 0 reg */
```

### How to recognise it in a diff

* PS stores a **register** at a tail/early-exit; the recompile stores an
  **immediate** (`C6 /0 00`) or zeroes a register first (`xor r,r`),
  OR the byte counts simply won't close on an otherwise shape-aligned
  function whose last statement you transcribed as `= <var>`.
* The register PS stores was just `test`ed (or `and`+`test`ed) and the
  branch **fell through** to the store — i.e. it is provably 0.
* Inverse of Rule 110/129 (deterministic const-store *form*): here the
  question is whether the source even *is* a const store; the byte clue
  is "store of a register the flow proved zero."

When you see it, transcribe the statement as `= 0` (or `= <provably-zero
var>` collapsed to its constant), NOT as the variable that happens to
occupy the register.  Then re-evaluate the byte-local seats — removing
the use frequently unblocks a Rule 115 / Rule 28a decl/use-order tie.

### Detector

`c2 decomp-verify` flags this statically: see
`_known_zero_store_hint` (the `known-zero store` advisory line).  It
scans the PS disasm for a tail `mov [mem], r8` whose register is proven
zero by a preceding `test r8,r8`/`and …,r8`-then-fall-through, and (on a
diffing function) checks the recompile is NOT already storing a constant
there.  Ground-truth positive: `get_education_ov_image` pre-fix; the
byte-exact corpus is the negative set.

## Rule 158 — A folded-away always-true guard (`uchar >= 0 &&`) still roots a CSE partition

### Trigger

A still-diffing else-if chain over an `unsigned char` selector where,
versus PS, ALL of the following co-occur around one chain level:

  * RC hoists a very-busy expression (e.g. `row + evolve_row`) HIGHER
    than PS — RC's def sits before the chain-head compare
    (`cmp eax, K; jge`), PS's def sits one level lower, inside the
    first arm (after that arm's condition computation, with an
    explicit `test eax, eax` where RC branches on the AND's flags);
  * PS re-zexts the selector (`xor eax,eax; mov al,[home]`) at the
    next else-if level where RC reuses the register copy
    (binir: PS-only `zext_byte_load`);
  * PS's arm/join call sites recompute the hoisted expression inline
    and consequently tail-merge DEEPER (whole `push/…/call` suffix
    shared via `jmp`) where RC's sites read the hoisted register and
    merge only a stub.

### Right C

```c
if (kind >= 0 && kind < 8) {        /* kind is unsigned char */
    ...
} else if (kind >= 0x7c && kind <= 0x7e) {
    ...
```

`kind >= 0` is always true (unsigned), emits ZERO bytes in PS.EXE —
Watcom folds the compare — but the fold happens AFTER the flow graph
is built.  The dead conditional contributes a second fail edge to the
`kind < 8` level, so the next else-if level has `inputs != 1` and
becomes a PARTITION_ROOT (`cse.c:344 FindPartition`).  CommonSex
(`ProcessExpr` very-busy hoisting + zext CSE) cannot pair expressions
across partition roots, which reproduces all three observables above
at once.  Emits W111 (“Meaningless use of an expression”) — the
original team evidently ignored it.

### Mechanism

`FindPartition` roots every block with `inputs != 1`; `TreeBits` +
`WhichIsAncestor` place a very-busy pair's def at the common-ancestor
block's end, *before its trailing condition instructions* (hence the
explicit `test` when the def lands between an AND-chain and its jcc).
Calibration inside the same function (`evolve_land_value`'s
byte-matching bkind chain): every `&&`-range level (2 fail edges)
starts a new partition → re-zext + re-hoist at that level; every
`== K`/`jne` level (1 fail edge) continues the partition → zext and
hoisted-add reuse.  An if/else JOIN block (e.g. the 0xfa idx case, or
a call after an if/else) is likewise its own partition → its copy of
the expression recomputes inline.

### Detection (automated)

The guard is INVISIBLE in PS.EXE bytes.  The MSVC 4.0 `/Od`
CAESAR2.EXE oracle shows it literally:
`xor eax,eax; mov al,[kind]; test eax,eax; jl <skip>` immediately
before the `cmp eax, K` — four extra instructions with no Watcom
counterpart.  When a Watcom-side CSE-grouping divergence resists every
statement-level rewrite, DIFF THE WIN BUILD (`c2 win-verify -v`): a
constant-foldable guard, or any other zero-byte source construct, can
be the load-bearing difference.

Harness integration (2026-07-03):

  * **`c2 win-verify --guards`** — corpus sweep: scans every win-diff
    function's aligned diff for one-sided zero-compare runs
    (`wb.guard_hits`); still-PS-diffing hits sort first.
  * **`c2 diagnose <fn>`** — the `win-guard:` line fires per function
    (same probe, `wb.guard_probe`).
  * **binir-shape hint** — PS-side co-occurrence fingerprint (PS-only
    `zext_byte_load` + PS `zero_test_jcc` vs RC `branch_flag_jcc`)
    appends a Rule 158 pointer even without a win mapping.

The probe also fires on the wider class “CAESAR2 has a zero-compare
our source lacks at that slot” — e.g. a mutated-parameter shape where
our source clips a copy instead of the param (see
`get_closest_trading_post`).  Either way the hit names a real
shape divergence.

### Verified on

  * `evolve_land_value` (evolver.c, 0x40AC5) — 247bd → body
    byte-exact with the single-token guard; commit `e6ea8769`
    (commit message says Rule 157; renumbered 158 — the registry
    already had a 157).
  * `get_closest_trading_post` (map.c, 0x6DD8C) — 275bd → byte-exact;
    the sweep's zero-compare hit exposed the param-mutation shape;
    commit `f0490082`.
  * Minimal wcc386 10.0a repro (warm-container compile): guard flips
    the fingerprint {hoist-above-cmp, no re-zext, register-reuse
    sites} → {hoist-in-arm + test, re-zext, inline recompute + deep
    tail-merge} with zero byte cost.
  * Watcom 10.0a, `-bt=dos -mf -4r -s -d1`.

## Rule 159 — Explicit `(unsigned char)` narrowing casts on char-param call args tip the loop-counter HOMING fixed point

### Symptom

PS memory-homes the loop counters (dword init `xor r,r` + `mov
[esp+K], r`, `inc dword [esp]` in-memory increments, frame N slots
bigger) and computes char-typed call args **byte-wise from the
slots**:

```
mov  bl, [evolve_row]        ; byte read of an int global
add  bl, byte ptr [esp]      ; byte read of the int counter's SLOT
and  ebx, 0xff               ; in-place zext into the arg register
...
mov  dl, byte ptr [esp+0x14] ; byte read of col's slot for arg edx
```

while RC keeps the counters in callee-saves (row→EBP, col→ESI, one or
two EXTRA pushes) and computes the same args dword-wide
(`mov ebx, [evolve_row]; add ebx, ebp`).  Every downstream island is
this flip's slot-shift or prologue delta.

### Cause — two self-consistent regalloc fixed points

The arg width follows the homing, and the homing follows the arg
width (chicken-egg):

  * {counter in dword reg → dword add + late truncate → no byte-width
    use → callee-save legal} — RC's equilibrium.
  * {counter memory-homed → Watcom narrows the arg add to BYTE (both
    operands byte-readable from memory) → the counter now has a
    byte-width USE → its register candidates restrict to the
    byte-addressable a–d set, all call-clobbered at the 7-arg
    `__watcall` call → memory-homed} — PS's equilibrium.

The implicit char-param conversion (`put_out_a(..., col,
evolve_row + row, ...)` with a `char x, char y` prototype) is NOT
enough to tip Watcom 10.0a into the byte fixed point: the FE keeps
the arg expression int-typed and truncates late.

### Fix

Write the casts explicitly in the call:

```c
result = put_out_a(1, (unsigned char)col,
                   (unsigned char)(evolve_row + row), flags, ...);
```

The cast forces the byte-width use into the FE tree, restricting the
counters' register class up front → memory-homing → PS's exact frame
and byte-wise arg codegen.  Zero semantic change (the params are
char anyway).

### Verified on

  * `evolve_fort_activity` (evolver.c, 0x4176E) — 234bd → BYTE-EXACT
    from the casts alone (both `col` and the y-sum).
  * `evolve_forum_activity` (0x415BB) — 344bd → 91bd from the casts;
    byte-exact after Rule 143 store-backs + decl-order slot seating.
  * `evolve_security_activity` (0x418D9) — 530bd → 479bd from the
    casts (ir 24→11, spill →0); byte-exact after the same follow-ups.
  * Win /Od caveat: CAESAR2.EXE shows a plain dword add+push here
    (no truncation) — the newer Windows build likely widened these
    prototypes; the win witness is NOT authoritative for this rule
    (PS byte-adds win the conflict).
  * Watcom 10.0a, `-bt=dos -mf -4r -s -d1`.

### Detection

Fires when PS does `add <byte-reg>, byte ptr [esp+K]` (or byte reads
of counter slots feeding arg registers) at a call whose prototype has
char params, while RC computes the same value dword-wide from a
callee-save — plus the Rule 28b asymmetric push set and PS-only
dword spill stores of the counters at the loop heads.

## Rule 160 — `-d1` marks attribute for-increment/condition insns to the loop's CLOSING-BRACE line (a braceless outer loop is line-mark-visible)

### Symptom

Byte-exact function, but `c2 line-compare` reports an RC-only mark on
the OUTER loop's back-edge (`inc <reg>` / `cmp` / `jl`) while PS has
no transition there.  Code bytes are identical either way — this is a
**pure `-d1` line-stream divergence** (Hard Rule #8 class).

### Mechanism

Watcom 10.0a does NOT mark a rotated `for`-loop's increment+condition
instructions with the `for`-header line: they get the line of the
loop body's **closing brace** (verified directly on the .obj LINNUM
records: `evolve_region`'s inner `inc edi; add [cm_sptr],8; cmp; jl`
carried line 2573 = the inner `}` line, NOT the header line).  A new
mark is emitted only when the line *changes* between consecutive
instructions, so:

* nested loops with each `}` on its own line → the outer back-edge
  gets a NEW mark (its own `}` line);
* a **braceless outer loop** (`for (...)` whose body is just the
  inner `for (...) { ... }`) → both loops' back-edge insns share the
  inner `}`'s line → NO mark on the outer back-edge.

### What to write in C

If PS shows no mark on the outer back-edge, drop the outer loop's
braces (single-statement body):

```c
for (row = 0; row < rows; row++)
    for (col = 0; col < 60; col++, cm_sptr += 8) {
        ...
    }
```

### Verified on

  * `evolve_region` (evolver.c, 0x436AB) — commit ad1de9e7: PS-only
    witness at +0x8e2 resolved; `line-compare` 141/141 paired, clean.
  * Watcom 10.0a, `-bt=dos -mf -4r -s -d1` (`-d1` does not change
    code bytes; this rule is about the line stream only).

### Detection

`c2 line-compare <fn>` RC-only mark whose offset lands on a loop
back-edge (`inc`/`cmp`/`jcc` immediately before an epilogue or next
loop level).  Compare the mark's line value against the loop `}`
lines in the recovered source.

## Rule 161 — Byte-seat picks are OCCUPANCY-pinned: first non-excluded byte reg in list order; anonymous-conflict swaps have NO reorder handle

### Symptom

Small residual diff (~5-30 b) of pure byte-register identity swaps on
CONSTANT byte stores / byte RMW chains (`xor dh,dh; mov [m],dh` vs
`xor dl,dl; …`, `mov bh,1` vs `mov ch,1`, `dec ch` vs `dec dl`), with
binir "all IDENTICAL IR" and run-ledger `regalloc_pure`.  Every
decl-order / statement-reorder / permute probe is neutral.

### Mechanism (gb-record study, 2026-07-09, figure_go_to_target)

GiveBestReg's byte pick decomposes as (all read directly off the `bt`/
`gb`/`tg` trace records):

1. candidates = the 8 byte regs MINUS byte regs whose OWNING ranges
   overlap this conflict (`with.regs`/`except` — **byte-granular**:
   DL can be excluded while DH survives) MINUS TooGreedy vetoes.
   The exclusion set determines where the scored sweep STARTS
   (observed sweeps starting at AL, DL, BL, CL in one function);
2. argmax CountRegMoves credit (a MOV touching that byte reg inside
   the range — observed `DL saves=1` picks);
3. tie → GivenRegisters subset — **saturated late-function**
   (`given=0x1f0001ff` on every byte conflict observed), so a no-op;
4. tie → list order `AL,AH,DL,DH,BL,BH,CL,CH`.

So the seat is a pure function of BYTE-RANGE OCCUPANCY + MOV credits,
both determined by the allocation order and live ranges of (usually
ANONYMOUS) byte temps.

### The reorder-futility corollary (corpus-proven)

* Swapping the declaration lines of NAMED byte locals in byte-exact
  functions perturbs their **spill-slot order** (Rule 107 class), NOT
  any byte seat — two perturbation experiments
  (clear_region_ferret_map cell0/cell7, try_this_regionmap_square
  terr_bit_1/terr_bit_2: both flip `[esp+K]` slots only).
* figure_go_to_target: all 15 swap-participating byte conflicts are
  anonymous; 320 single-lever + 86 composed-pair byte-form variants
  ALL tie.  The one `credit` pick sits on an anon temp's range.

**Verdict class `Byte-seat = CASE A2` (occupancy-pinned):** fires when
every swap byte conflict is anonymous.  Levers: byte-temp-SET changes
only (name/inline a byte value — Rule 129/§10 — or a byte-RMW form
change, which alters WHICH byte ranges exist and overlap).  When
`c2 spell --suggest` hazard-rejects all set changes, the residue is
certified.  Do NOT grind decl/use reorders.

### Detection

`c2 decomp-verify -v` Byte-seat line (CASE A2), or by hand: regtrace's
byte conflicts with `var=None`, `given_regs` saturated, gb scores 0 /
anon-range credits.

### Verified on

  * figure_go_to_target (11 b, battle.c) — classifies A2; matches the
    406-variant empirical exhaustion.
  * show_battlemap_base / start_samples / show_move_highlight — no
    Byte-seat hint fires (no over-claim regression).
  * Watcom 10.0a, `-bt=dos -mf -4r -s -d1`.

## Rule 162 — The empty-body `#pragma aux` far-pointer helper (parm-liveout + branch-implied-zero elision)

### The asm pattern

A far-pointer-returning error exit whose fail block, on the
fall-through of `test REG,REG; jne`, materializes ONLY the offset
half — no `xor edx,edx` — while sibling fail sites in the SAME
function DO carry the xor, and a memory-compare that stays SPLIT
(`mov edx,[mem]; test edx,edx`) where the plain source form fuses to
`cmp [mem],0`:

```
mov  eax,[idx]              ; idx cache
mov  edx,[eax*4+ARRAY]      ; the SPLIT load survives
test edx,edx
jne  skip
mov  eax,2                  ; off half ONLY -- seg "0" elided
jmp  epilogue               ; (pair DX:EAX, EDX = the tested 0)
skip:
lea  ebx,[eax+1]            ; rover-picked THIRD register
```

### What to write

The TU's own helper, inlined away by an EMPTY aux body:

```c
char __far *MK_FP(int off, int seg);
#pragma aux MK_FP = parm [eax] [edx] value [dx eax];
...
if (ARRAY[i] == 0) return MK_FP(2, 0);   /* anonymous test, seg = literal 0 */
```

Three compiler mechanisms compose (all measured, watcom 9.5–11.0):

1. **parm [edx] = a live-out**: the (invisible) call ins USES EDX, so
   the tested value is live out of the cond block and LdStCompress
   keeps the split (the lcx3 `[sentinel+8]` live-out gate).
2. **branch-implied-zero elision**: the encoder's constant tracker
   knows EDX==0 on the `test/jne` fall-through and SKIPS materializing
   the const-0 seg arg.  It elides ARG MATERIALIZATIONS only — an IL
   `xor edx,edx` from `(char __far *)2` / `MK_FP(0,2)` is NOT deleted.
3. **the rover advance**: the anonymous test keeps the fr'd split, so
   the RISCify cursor advances and a following memory-RMW increment
   picks the NEXT rotation register (`lea ebx,[eax+1]`).

### What the obvious forms emit instead

* `return (char __far *)2` → `xor edx,edx` present (36bd on
  start_samples) — the seg const is a real IL def.
* naming the tested value (`s = ARRAY[i]; ... MK_FP(s, 2)`) → the
  split load stops being a rover event → the increment wraps to EAX
  (`inc eax`).
* re-mentioning `ARRAY[i]` in the fail → the FE binds the ADDRESS →
  `shl eax,2` + decomposed addressing (all versions 9.5–11.0; every
  pointer-arith respelling canonicalizes to the same tree).

### Verified on

* start_samples (pcsound.c) — 234b, byte-exact from this form after
  ~950 variants of everything else (caesar2 3d1f33b1).
* Witnesses: C2DEMO 1995-08 (the same helper WITH a real
  `test edx,edx` dispatcher body, shared fail tail); the Windows port
  (MSVC can't `#pragma aux` → MK_FP became the literal dead stub at
  0x409344, same `(off, seg)` arg order).
* Discovery trail: watcom10.0a `notes/start-samples-p5p6.md`.

## Rule 163 — Byte-reg swaps at RISCified const-store / split-load sites are ROVER cursor parity, not GiveBestReg ties (the false-CASE-D class)

* **Asm pattern**: PS↔RC byte-register identity swaps on `xor r8,r8` /
  `mov r8,imm` + `mov [global],r8` const stores, or on `mov r8,[global];
  test r8,r8` split compare loads.  Often MANY per function, no single
  consistent k in layout order.
* **The trap**: `byte_seat_hints` matched ANY GB byte conflict in the
  routine whose seat was in the swapped set, so unrelated AL-conflicts
  pushed these sites into the Rule 133/161 ladder and certified an
  "inert GB tie — IRREDUCIBLE, park it".  These sites are NOT GB
  conflicts: they are **FindRegister byte-rover picks** (post-RegAlloc,
  i86ldstr.c) — the picked register is the byte-rover CURSOR state, and
  the swap class is **advance-count / except-mask parity**, fully
  steerable by the rover levers (load-fold, Rule 121 tail-dup,
  temp-SET; watcom10.0a docs/rover-model.md).
* **The discriminator** (exact since trace v55): pair `routine['frx']`
  ground-truth picks 1:1 with byte-class `fr` records → `fr['truth']`.
  If a swapped RC byte reg is a rover truth pick and not a GB byte-conf
  seat, the verdict is CASE **R** (byte_seat_hints), never D/A2.
* **The method**: k-map = idx(PS_pick) − idx(RC_truth) mod 8 over the
  corrected ByteRegs order **AL,AH,DL,DH,BL,BH,CL,CH** per WALK-ordered
  site (anchor ONLY visible form-matched sites; c6-compressed and
  Score-coalesced picks are invisible and must not be anchored).  The
  trajectory is piecewise-constant; each transition = one advance-count
  delta window; masked advances create funnels/pins that absorb deltas
  (rover_fit computes the windows exactly).
* **Corollary fixes bundled with the discovery** (2026-07-11): the
  byte NAME table was pairwise-swapped for B/C/D in rover_hints._NAME +
  the watcom repo's reglists/rover_divergence (H = the LOW bit:
  AH=0x1 AL=0x2 BH=0x4 BL=0x8 CH=0x10 CL=0x20 DH=0x40 DL=0x80); every
  byte-class rover k/lever computed before the fix was name-inverted.
  Standing gate: docs/codegen-experiments/frx-emitted-name-audit.py.
* **Worked example**: action.c `action` — 12 byte pairs certified
  "CASE D [trace] irreducible" on 2026-07-11a; the frx k-map showed
  k=0 across the whole dispatch prefix and a single +2 window
  (fr#20..#35) + tail funnel divergence instead.  Also exposed that the
  `mm`/`zz` embedded-assign locals were register-impossible (a GB byte
  conflict at sav=2/3 rank can never seat CH/BL: given-subset is
  saturated → list order → AL always) — PS's shapes there are rover
  picks + Score redundant-load reuse (`mov bl,[g]; … mov al,bl`).
* Discovery commits: 62f77b5c, 8601ea09 (caesar2); 3ae8e52 (watcom10.0a).

## Rule 164 — A chained assignment can be the load-bearing SEAT lever: its value/index temp is a savings-weighted conflict that masks a register for a later pick (the EBX-eater)

* **Asm pattern**: a dword named local seats in the "wrong" register on
  a GiveBestReg list-order tie (e.g. RC `xor ebx,ebx` where PS has
  `xor ecx,ecx` for a loop-carried index), with the ENTIRE remaining
  diff (byte pairs, rover picks, copy-loop rotations) downstream of
  that one seat.  `c2 seats` shows the value alone in its savings band
  with `scores[EBX:0 ECX:0]` — nothing masks the earlier list register.
* **What to write**: the multi-store init as a CHAINED assignment,
  e.g. `temp_route[i].x = temp_route[i].y = 0;` (not two split
  statements).  The chain births an extra index/value temp whose
  savings (index refs weigh 2u; ×10 per loop depth) lift it ABOVE the
  later value in ConfBefore, so it allocates first, takes the list-
  order register, and the later pick lands on PS's seat.  MSVC /Od is
  the witness: it realizes the chain literally (store y, RE-READ y,
  store x), so `c2 win-verify -v` shows the form directly.
* **The trap (Hard Rule #3 worked example)**: judged by island count
  the chain looks like a big regression (ir 1→12) because the new
  conflict reshuffles the equal-savings ShellSort group (list size
  N+1 = new permutation of the byte seats and slots).  Judge by
  `first-diff` / seat layer instead: the header goes byte-exact and
  the reshuffle is then steerable by DECL ORDER (Rule 115 name queue)
  — `c2 sweep` finds the recovering permutation mechanically.
* **Corollary — statement GROUPING of a zero chain is load-bearing at
  the Score-coalesce level**: `a = b = c = 0; d = e = 0;` (6+2) vs one
  8-var chain vs 8 splits all canonicalize to the same stores, but the
  xor/store INTERLEAVE differs (`c2 spell --fusion` fr rows: lcx0
  "pair separated (Score coalesce)").  Only the grouping that matches
  PS's `-d1`-witnessed interleave is byte-exact.
* **Discovery**: trace_back_route_elastic (map.c) 57bd→0,
  commits 16cbd37e / 879254a3 / 9743ab3a, 2026-07-12.  Four prior
  sessions had certified the seat "no reachable source lever" from
  savings/credit/order families alone — the lever was a NEW conflict
  (liveness/temp-set family), reachable only through the source form.

## Rule 165 — `add rX,rY` vs `add rY,rX` before a memory store is IL OPERAND ORDER (source associativity), not a register seat — and seat_recon will misattribute it

* **Asm pattern**: a 2-row diff `add rX, rY; mov [global], rX` vs PS
  `add rY, rX; mov [global], rY` where BOTH operand values sit in the
  SAME registers in PS and RC.  The `decomp-verify -v` hint already
  tags it "op-direction / accumulator choice".
* **Mechanism**: a commutative ADD whose IL result is N_MEMORY
  realizes as `add op0reg, op1reg; mov mem, op0reg` — the accumulator
  is ALWAYS op0.  op0/op1 order comes from the SOURCE expression tree
  (left operand = op0), surviving evaluation-order canonicalization
  (Watcom may compute the right subtree first yet keep the slots).
  Register-blind IR matches (dest/src blind), every GiveBestReg seat
  matches, no allocator layer is involved.
* **The trap**: seat_recon aligns the swapped rows to the NEAREST
  chain conflict — in place_sprite it picked a round-1 split carrier
  (sprite_width's word->shift MOV-CONVERT-MOV pass-through, seat
  byte-invisible) and certified a plausible-looking "given-subset-tie
  ECX:4/ESI:4".  Two sessions ground seat levers against a
  non-existent tie.  The [LOCALIZED divergence -- row attribution
  approximate] caveat is the tell: READ THE ROUND-0 IL WALK
  (c2.regalloc.file_trace -> alloc[].own_walk; res_meta 0x1201 =
  N_MEMORY result on the ADD) before believing a localized seat
  verdict.
* **What to write**: put the operand PS accumulates into FIRST
  (left).  If the naive reorder breaks a sibling load idiom (the
  place_sprite left-assoc 174bd cascade: m6's convert fuses to a
  movzx and loses the Rule 49 xor-idiom), pin the load with an
  embedded named-int def:
  `(m4 + (m5 << 8)) + ((word = m6) << 16)` — left-assoc pins
  op0=inner-sum; `word =` pins the named-int load.
* **Discovery**: place_sprite (pm_map1.c) 2bd→0, commit 1bff2694,
  2026-07-13; overturned the 2026-07-11/13 "credit-level sub-source"
  certifications (Hard Rule #6 worked example).
