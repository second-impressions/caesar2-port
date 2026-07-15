# Far-pointer return EDX must-save divergence (pcsound.c) — RESOLVED

**Status:** **RESOLVED (2026-06-20).**  The `#pragma aux <fn> modify exact
[eax gs]` on the far-ptr pcsound functions is **confirmed faithful** — it
is the documented Miles-AIL / Watcom register-contract idiom, NOT a decomp
hack.  This file was originally an OPEN RE handoff; §6's "toolchain gap"
hypothesis is **disproven** by binary RE of the actual 10.0a `wcc386`.  The
sections below are kept as the investigation record; §2-§5 stand, §6 is
struck and replaced by §6-prime (the resolution).

The companion experiment is `docs/codegen-experiments/farptr-edx-save.py`
(run `uv run c2 cgex run farptr-edx-save`).  Source under study:
`decomp/src/pcsound.c`.  OW v1 (2002) source: `vendor/open-watcom/`.
10.0a binary RE tree: `~/git/ReverseEngineering/watcom10.0a/`.

---

## 1. The phenomenon

pcsound.c has a cluster of functions the debug build declares as
returning a **far pointer** (`char __far *`):
`start_sequences`, `start_samples`, `start_sound`, `start_tune`,
`pos_sound`, `neg_sound`, `pause_db`, `set_db_sound`.  Their "error"
returns are far-pointer constants — e.g. `return (char __far *)1`,
`return (char __far *)MK_FP(1,2)` — which lower to a two-register
`EDX:EAX` set (EDX = segment, EAX = offset).  The caller(s) discard the
return value entirely.

**Canonical case — `start_sequences` (PS.EXE @ 0x118A2):**

PS pushes **6** callee-saves including EDX:

```
push ebx ; push ecx ; push edx ; push esi ; push edi ; push ebp
```

Its body uses EDX as a 32-bit scratch (the loop counter `ms`,
`mov edx,[0x14150]`), and its returns set EDX:EAX per-site
(`xor edx,edx; mov eax,1`  and  `mov edx,1; mov eax,2`).  The epilogue at
+0x3d is `pop ebp ; jmp 0x13181` — a **cross-function tail-merge** into
`init_city_ambients`'s epilogue (`pop edi; pop esi; pop edx; pop ecx;
pop ebx; ret` @0x13181).  Note `init_city_ambients` is **void** and
naturally pushes EDX (a void function keeps EDX in must_save and pushes
it because the body uses it).  So PS's far-ptr `start_sequences` ends up
with the **same 6-register save set as a void function**.

The recompile (RC, the verifier's 10.0a) with the plain far-ptr source
pushes only **5** (no EDX): `push ebx ; push ecx ; push esi ; push edi ;
push ebp`.  Because RC doesn't push EDX, its epilogue doesn't suffix-match
`init_city_ambients`, the cross-merge doesn't fire, the epilogue lands at
the function end, and the no-op/success guards need 6-byte forward Jcc
instead of PS's 2-byte backward Jcc → the whole layout cascades to a
**113-byte diff**.

So the entire 113b reduces to one fact: **PS keeps EDX in `must_save`
for this far-ptr-returning function; the verifier's 10.0a strips it.**

---

## 2. What OW v1 (2002, ~5y AFTER 10.0a) says — the MODEL, not ground truth

`bld/cg/intel/c/i86reg.c:272 MustSaveRegs()`:

```c
HW_CAsgn( save, HW_FULL );
HW_TurnOff( save, CurrProc->state.modify );
HW_CTurnOff( save, HW_UNUSED );
if( CurrProc->state.attr & ROUTINE_MODIFY_EXACT ) {
    HW_TurnOff( save, CurrProc->state.return_reg );        // line 282: NO FullReg
} else {
    tmp = CurrProc->state.parm.used;
    HW_TurnOn( tmp, CurrProc->state.return_reg );
    tmp = FullReg( tmp );                                  // line 286: FullReg the union
    HW_TurnOff( save, tmp );
}
HW_TurnOff( save, StackReg() );
if( HW_CEqual( CurrProc->state.return_reg, HW_EMPTY ) ) {  // void: clears EAX only
    tmp = ReturnReg( WD, _NPX( CurrProc->state.attr ) );
    HW_TurnOff( save, tmp );
}
tmp = CurrProc->state.unalterable;                         // FixedRegs()
HW_TurnOff( tmp, DisplayReg() );
HW_TurnOff( tmp, StackReg() );
HW_TurnOff( save, tmp );
```

And `SaveRegs() = MustSaveRegs() & state.used` (so a register is pushed
iff it is a must-save candidate AND the body uses it).

Relevant tables in `bld/cg/intel/386/c/386rgtbl.c`:

* `ReturnSets[]`: **CP (far data/code pointer) → `RL_DX_EAX` = `{DX, EAX}`**
  (16-bit DX seg + 32-bit EAX off; line 442).  `U8/I8` (long long) →
  `RL_EDX_EAX` (full EDX).  `U4/I4`/near pointer → `RL_EAX`.
  struct → `StructReg()` = **`HW_ESI`** (line 678; small structs return
  via a hidden pointer/ESI, NOT in EDX:EAX).
* `FullReg()` (line 872): if the set overlaps EDX, turn on the **full
  EDX** — i.e. `FullReg(DX) == EDX`.
* `FixedRegs()` (line 1062): `{SP, BP, SS, CS}` + `DS/ES/FS/GS` unless
  the model marks them FLOATING + `EBX` if `INDEXED_GLOBALS`.

**OW v1 model prediction:** for a far-ptr return, the non-`MODIFY_EXACT`
branch does `save &= ~FullReg(parm.used | return_reg)`, and
`FullReg(DX) = EDX`, so the **full EDX is stripped from `save`** → EDX
can never be pushed, even when the body uses it.  The only branch that
spares EDX is `MODIFY_EXACT`, which clears just the named `return_reg`
(16-bit DX), leaving EDX in `save`.

> ⚠ This is the 2002 snapshot.  10.0a is 1995.  The `tmp = FullReg(tmp)`
> on line 286 (applied to the union including `return_reg`) is the prime
> suspect: **it may not exist, or may apply only to `parm.used`, in the
> 1995 build.**  That is the single fact the RE must establish.

---

## 3. What the VERIFIER's 10.0a actually does (measured)

The verifier image is `localhost/watcom-10.0a-wibo[-trace]` — claimed to
be the actual 1995 binary, byte-identical `.obj`
(see `docs/wcc386-re/regalloc-trace-image.md`).  cgex experiment
`farptr-edx-save` (run it; reads the prologue via `print_trial`):

| trial | return type | EDX pushed? | how the far seg is produced |
|---|---|---|---|
| A-far | `char __far *` | **NO** (push ebx only) | `mov edx, ds` at epilogue (cast) / `mov edx,N` at return site (MK_FP) |
| B-near | `char *` | **YES** (push ebx; push edx) | n/a |
| C-void | `void` | **YES** | n/a |
| D-int | `int` | **YES** | n/a |

Additional measurements:
* MK_FP (constant seg) vs cast (DS seg): **both** far-ptr forms → no EDX
  push.  So it is the *return type*, not the seg value.
* long long (`RL_EDX_EAX`) also strips EDX (FullReg of the full pair).
* struct-by-value: `StructReg()=ESI`, memory return, not a 2-reg EDX:EAX.
* **Sibling test:** a void EDX-pushing function and a far-ptr function in
  the SAME TU — the far-ptr function STILL does not push EDX.  So the
  cross-function epilogue share does NOT drive the push (the push set is
  decided per-function before ComTail).

**Conclusion:** the verifier's 10.0a behaves EXACTLY like the OW v1 model
— it FullReg-strips EDX for a far-ptr return.  The real `start_sequences`
in the verifier confirms it (5-push, no EDX).

---

## 4. The contradiction (this is the crux)

* All **three** PS.EXE builds push EDX in `start_sequences`
  (cross-build: `c2 decomp-verify -v -f start_sequences` reports
  "stable across all builds (exact in rel-1995-10, rel-1995-09)" — i.e.
  the 1995 release builds' bytes == the 1996 debug build's bytes, all
  6-push-with-EDX).
* The verifier reproduces the 1995 release builds for *other* functions,
  yet for this far-ptr case it strips EDX (5-push).
* Same compiler + same source ⇒ same bytes (deterministic).  So either
  **(a)** the source we have differs from PS's (a natural construct we
  haven't found that keeps EDX), or **(b)** the verifier's binary differs
  from the binary that built PS.EXE *specifically in the far-ptr
  `return_reg` FullReg*.

The control that pins it down is **`start_sound`**: it is far-ptr too but
takes `loop_count` in EDX as a **parameter**.  PS does NOT push EDX there
— because `parm.used` contains EDX and `FullReg(parm.used)` strips it
regardless of the return_reg question.  So `start_sound` is consistent
across every hypothesis; the divergence is **only** about whether the
far-ptr *return_reg* gets FullReg'd.  → The RE only needs to inspect the
`return_reg` handling, using a **void-param far-ptr fn that uses EDX**
(start_sequences/start_samples) as the discriminator and `start_sound`
(EDX param) as the negative control.

---

## 5. The two source levers we found

### 5a. Value-less return — FAITHFUL (keep this)

PS's no-op/success paths return **value-less**: they jump to the shared
epilogue WITHOUT materialising EDX:EAX (the caller discards the return,
so it is garbage).  Reproductions:
* `return (char __far *)0;` → emits `xor edx,edx; xor eax,eax` PS never
  has (splits the epilogue).  WRONG.
* fall off the end → **funnels** the error returns through ESI:EDI.  WRONG.
* **`return rc;` of an UNINITIALISED `char __far *rc`** (Rule 77 /
  style-guide §9) → no materialisation, no funnel.  **CORRECT.**  This is
  the idiom prior agents never tried (the old `pos_sound` comment lists
  "init, ternary, void/far spelling" but not *uninitialised local*).

This is a genuine 1995 idiom and is not in question.

### 5b. EDX push — the `modify exact` PRAGMA (SUSPECT — likely NOT original)

`#pragma aux start_sequences modify exact [eax gs];` forces the
`ROUTINE_MODIFY_EXACT` branch of `MustSaveRegs` (the one that does NOT
FullReg the return_reg), so EDX stays in `must_save` and — being used —
gets pushed.  Combined with 5a this makes `start_sequences` **byte-exact**
and cascades `neg_sound` + `pause_db` to exact.

**Why we do NOT believe a 1995 programmer wrote it:**
* `modify exact [eax gs]` is not something a human writes for an internal
  C MIDI-init helper; `modify` pragmas are for assembly/library entry
  points whose clobbers the compiler can't see.
* The `gs` is a tell: the function never touches GS.  `modify exact [eax]`
  alone makes the compiler *preserve* GS (an artifact of the exact path);
  `gs` is only in the list to cancel that artifact.  A clobber list you
  reverse-engineer to suppress an artifact is a hack.
* `modify exact [ebx ecx esi edi ebp]` (declare EDX preserved) is rejected
  **E1122** — the far-ptr return makes EDX the seg return reg, which can't
  also be a preserved callee-save.  So the pragma can only express the
  push as a side effect of MODIFY_EXACT, not as intent.

~~So 5b is a verifier-parity shim, not recovered source.~~  **REVERSED
by the binary RE (see §6-prime):** 5b is the *only* C-level lever that
reproduces PS's EDX push and it is the documented AIL/Watcom idiom — it
stays.  The `gs` in the list is required (not an artifact): `modify exact`
pushes any unlisted register, so an unlisted `gs` emits a spurious
`push gs` (`[eax]`-alone regresses to 134 b).  `gs` is legitimately
clobbered because the function operates in the AIL driver's segment
context (separate selector; ail32.asm uses `push gs`/`pop gs` at ISR
time).  Upstream evidence: `decomp/refs/miles-ail-sdk/AIL.H`.

---

## 6. ~~Hypothesis to test against the 10.0a binary~~ (DISPROVEN — see §6-prime)

~~The 1995 10.0a `MustSaveRegs` does NOT `FullReg` the far-ptr `return_reg`
— leaving EDX in `must_save` emergently.~~  **Disproven** by RE of the
actual 10.0a binary (§6-prime): 10.0a's `MustSaveRegs` matches the 2002 OW
source exactly — it DOES `FullReg` the return_reg, stripping EDX for a
plain far-ptr return.  There is no toolchain gap; the verifier image IS the
binary that built PS.EXE.

---

## 6-prime. RESOLUTION (binary RE, 2026-06-20)

RE of the actual 10.0a `wcc386.exe` (sister repo
`~/git/ReverseEngineering/watcom10.0a/`, pyghidra) settles every open
question:

1. **`MustSaveRegs` located at `0x4b67b`** — raw capstone disasm confirms
   the OW v1 structure 1:1:
   ```
   mov eax,[CurrProc=0x7f8b0]   ebx=~modify        ; save = FULL & ~modify
   test byte[eax+0x55],4        ; ROUTINE_MODIFY_EXACT? (i86proc.h ROUTINE_MODIFY_EXACT=0x400 -> attr bit 0xA)
   je  nonexact
     eax=[eax+0x50]              ; EXACT branch: eax=return_reg, NO FullReg
     jmp join
   nonexact:
     edx=[eax+0x34]; or edx,[eax+0x50]  ; parm.used | return_reg
     eax=call 0x3e113(edx)       ; FullReg(parm.used|return_reg)
   join: save &= ~eax
   ... void branch: if [eax+0x50]==0 eax=ReturnReg(0x3df7e)(WD,~float); save&=~eax ...
   ... FixedRegs (0x3e2ec/0x3e2e6) ...
   ```
   - `0x3e113` = **`FullReg`** (decompile confirms the six family masks;
     `FullReg(DX)` turns on the full EDX bit `0x04000000`).
   - `0x3df7e` = **`ReturnReg`** (RegLists table at `0x79b37`).
   So the **EXACT branch** turns off only the 16-bit `DX` subreg
   (`0x30`), leaving the full `EDX` in `save` -> EDX pushed if
   `state.used`; the **non-exact branch** FullRegs `(parm.used|return_reg)`
   -> `FullReg(DX)` promotes to EDX -> EDX stripped -> never pushed
   (matches the verifier's 113 b diff and cgex `farptr-edx-save`).
2. **`ROUTINE_MODIFY_EXACT` is set ONLY by the `modify exact` pragma.**
   The sole setter is `i86reg.c:~119` `if(cclass & MODIFY_EXACT)
   state->attr |= ROUTINE_MODIFY_EXACT;`, and `MODIFY_EXACT` comes only
   from parsing `#pragma aux <sym> modify exact`.  No C keyword
   (`__saveregs`, calling convention, attribute) sets it.  -> PS pushing
   EDX for a far-ptr fn *requires* `#pragma aux ... modify exact` in the
   source; it is provably the only lever.
3. **The verifier image IS the binary that built PS.EXE** — provenance is
   byte-identical end to end:
   - RE repo `binaries/wcc386.exe` = `c3666de9...` (dated **1994-09-01**)
   - verifier `localhost/watcom-10.0a-wibo` `/opt/watcom/binb/wcc386.exe` =
     `c3666de9...` (identical)
   - the binary's `MustSaveRegs` FullReg-strips EDX for plain far-ptr =
     exactly the verifier's observed behaviour == PS's compiler behaviour
     for every other function.
   So §6's toolchain-gap hypothesis is FALSE; PS's EDX push is a SOURCE
   pragma, not a compiler behaviour.
4. **The pragma is the documented Miles-AIL / Watcom idiom** (web/SDK
   evidence `decomp/refs/miles-ail-sdk/AIL.H`, from `gondur/mig_src`
   commit `7adf5e68c56f1bfbc79430064df39e36a4e665b6`): every `AIL_*`
   helper declares its exact clobber set via `#pragma aux _AIL_* "*" ...
   modify [eax ebx ecx edx]`; callbacks are `AILCALLBACK __pascal`;
   drivers are separate selectors (`AIL_DRIVER.sel`) using `gs` at ISR
   time (ail32.asm `push gs`/`pop gs`); AIL is interrupt-driven
   (`AIL_register_timer`, `INT 66H` dispatcher `this_ISR`/`prev_ISR`,
   `PM_ISR`, `AIL_disable/restore_interrupts`).  `#pragma aux <fn> modify
   exact [...]` is the standard Watcom spelling of "this function clobbers
   exactly these registers, preserves the rest."  `modify exact [eax gs]`
   on a sound-init wrapper reads: *clobber eax (far-ptr return) + gs (AIL
   driver segment), preserve ebx/ecx/edx/esi/edi/ebp exactly*.  EDX being
   pushed is the necessary consequence of EDX being preserved under a
   far-ptr return.  NOT a hack.
5. **Corroboration in PS push sets:**
   - the far-ptr cluster (`start_sequences`, `pos_sound`) all save
     `[ebx ecx edx esi edi ebp]` (EDX via the pragma; `pos_sound` even
     tail-merges into start_sequences' identical epilogue).
   - the **void** AIL functions (`choose_odd_tune`, `set_db_sound`,
     `fade_sequence_in`) push EDX *naturally* — void's `return_reg` is
     EMPTY, so `MustSaveRegs` strips only EAX, leaving EDX savable with NO
     pragma (cgex C-void confirms).  PS used the pragma ONLY where a
     far-ptr return would otherwise strip EDX.
   - the actual AIL trigger callback `_mood_modfication` saves *only
     `[esi]`* and clobbers edx freely -> callbacks follow the
     `AIL_* modify [eax ebx ecx edx]` scratch contract; the pragma on the
     init wrappers is the wrappers' OWN caller contract, NOT callback
     interrupt-safety.

**Conclusion: keep `modify exact [eax gs]` on the far-ptr pcsound
functions — it is faithful recovered source, the Miles AIL
register-contract idiom, and the only lever that reproduces PS's EDX
callee-save push.  Do not revert.**

---

## 7. RE plan (concrete) — DONE

All five steps executed in §6-prime: `MustSaveRegs`@0x4b67b,
`FullReg`@0x3e113, `ReturnReg`@0x3df7e located; EXACT-vs-non-EXACT
branch confirmed; far-ptr `return_reg`=DX:EAX (16-bit DX, the EXACT
branch turns off only `0x30`); verifier image proven byte-identical to
PS's compiler.  Remaining work is only the *source-shape* residues (§9),
not this mechanism.

1. Locate `MustSaveRegs` (and `SaveRegs`, `CallState`, `FullReg`,
   `ReturnReg`/`ReturnSets`) in the actual 10.0a `wcc386` binary.
   Start from the verifier image's compiler and from
   `~/git/ReverseEngineering/watcom10.0a/` (knowledge/notes/probes).
   Cross-reference the OW v1 names/structure in §2 as the map.
2. Determine whether 10.0a's `MustSaveRegs` non-exact branch applies
   `FullReg` to `(parm.used | return_reg)` (2002 form, strips EDX) or to
   `parm.used` only / not at all over the return_reg (hypothesised 1995
   form, keeps EDX).  This single instruction sequence is the answer.
3. Confirm the far-ptr `return_reg` is `DX:EAX` (16-bit DX) in 10.0a's
   tables, and check how DX↔EDX promotion is done in must_save.
4. Validate with the discriminator pair: compile a void-param far-ptr fn
   that uses EDX (expect 6-push incl EDX if 1995 keeps it) and
   `start_sound`-shape (EDX param, expect no EDX push in both eras).
5. Decide: is the verifier image the same binary that built PS.EXE?  If
   the image strips EDX but PS keeps it, the image is not bit-faithful
   for this path — quantify the gap (which build/patch).

---

## 8. Current commit state

Byte-exact via 5a (faithful) + 5b (now-confirmed-faithful pragma):
* `1c90c5c9` start_sequences byte-exact (`modify exact [eax gs]` + value-less rc) → cascaded neg_sound, pause_db exact.
* `9f0d57b7` start_samples 91b→36b (same idiom + inline-s).
* `d49986c7` start_sound 30b→4b (cascade + value-less rc).
* `6cd23d3e` get_new_sslot byte-exact (Rule 116/123 — UNRELATED to this issue).

~~If the RE confirms §6, revert the `modify exact` pragmas.~~  The RE
(§6-prime) **confirms the pragma is faithful** — keep it.

---

## 9. Other pcsound residues (for completeness; mostly independent)

* **start_samples 36b** — loop-2 seg-elision.  PS materialises
  `S_dig[ds]` into EDX (`mov edx,[..]; test edx`) and return-2 reuses
  that `edx==0` as the far seg.  Named `int s` forces EDX in PS but
  funnels the error returns through ESI:EDI in RC (89b); inline
  `if (S_dig[ds]==0)` avoids the funnel but compiles to a memory `cmp`
  (no materialise) because the dword rover seats the load in EAX, not
  EDX.  Rover/scratch-seat, not source-reorderable.
* **start_sound 4b** — `buf`/`loop_count` ESI↔EDI seat swap; the
  uninitialised `rc`'s live range perturbs the param-save order (Rule 28a
  tie; `c2 permute` finds no inter-statement variant → intra-statement).
* **start_tune 1b** — value-less final return; the uninitialised-`rc`
  local competes with the seq_arg spill (param function) and blows the
  prologue to 122b.  Needs the value-less return without an extra local.
* **pos_sound 13b** — far-ptr (mistyped `void`): PS has a DEAD
  `xor edx,edx; mov eax,3` (set-3 then *fall through* to an unconditional
  `_AIL_start_sample`, which clobbers it — returned garbage) on the
  set_sample_file==0 path, i.e. `rc = (char __far *)3;` not an early
  return.  ENTANGLED: `neg_sound` tail-merges its tail into `pos_sound`,
  so typing pos_sound far-ptr breaks neg_sound (which is byte-exact as
  void).  Both-far-ptr was worse (neg_sound 59b).
* **get_city_mood 463b** — SEPARATE, not far-ptr.  `old_mood` in EDX
  (PS) vs EAX (RC): GiveBestReg savings-major routing; savings 19 (old_mood)
  vs 15 (r=rand128&7) are invariant for any byte-exact source, and there
  is no CountRegMoves lever (no calls/idiv/variable-shift), so the
  highest-savings value deterministically takes EAX while PS routes it to
  EDX.  Likely its own rover-vs-GiveBestReg routing question; see the
  in-source comment.
