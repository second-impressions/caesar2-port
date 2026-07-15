# MSVC 4.0 `/Od` + Watcom 10.0a goto signal — empirical findings (2026-07-03)

Question: does the MSVC 4.0 `/Od` compiler that built CAESAR2.EXE
preserve a binary signal for `goto` labels, usable to *prove* where the
original source used gotos instead of guessing?

Answer: **YES, with precisely characterized limits.**  Every `goto`
survives as its own unconditional near `jmp` (`E9 rel32`) — `/Od` does
no jump fusion, no jump threading, no dead-jump elimination — and a
goto is *positively identifiable* whenever its target is not exactly
the target a `break` / `continue` / `return` / loop template would
produce at that spot.  Gotos that exactly mimic those statements are
genuinely byte-identical to them (proven below), so for byte-exactness
either source form works there.

All experiments: MSVC 4.0 in `localhost/msvc-4.00-wibo`, flags
`/nologo /c /Od /Zp1` (the project's win-verify flags), COFF `.text`
extracted and disassembled with capstone.  Every result below is a
byte-level comparison of compiled test functions.

## Core codegen facts (all verified byte-level)

1. **No jcc fusion for goto.**  `if (c) goto L;` NEVER emits a single
   conditional jump to L.  It always emits the generic if-template:
   inverted `jcc` over the guarded body, and the body is the goto's
   `jmp`:

   ```
   0F 8x 05 00 00 00    jcc  +5      ; skip exactly the jmp
   E9 xx xx xx xx       jmp  L
   ```

   A do-while `} while (i < 10);` by contrast emits a single fused
   `jl top`.  So a *conditional-jump-statement* is always this
   11-byte "pair" — trivially scannable (`0F 8x 05 00 00 00 E9`).

2. **All jumps are near-form at /Od** (`E9` / `0F 8x rel32`), even for
   5-byte skips.  No short `EB`/`7x` forms appear.

3. **No jump threading.**  A goto to a label that sits on another jmp
   produces a jmp-to-jmp chain (kept verbatim).

4. **`goto` to the immediately-following statement keeps a
   `jmp $+0`** (`E9 00 00 00 00` to the next instruction).

## Proven byte-identical equivalences (goto NOT detectable)

| goto form | structured twin | result |
|---|---|---|
| `if (a) goto end;` … `end:` at function end | `if (a) return;` | **identical** |
| `if (c) goto out;` with `out:` right after the loop | `if (c) break;` | **identical** |
| bare backward `goto top;` | `while (1) { }` / `for (;;) { }` | **identical** (no test emitted for the constant) |

In these positions the two sources are indistinguishable by bytes;
prefer the structured form per observed-source-style unless another
oracle says otherwise.

## Proven distinguishable cases (goto IS detectable)

* **continue vs goto-label-at-end-of-body: DIFFERENT.**  `continue`
  jumps directly to the for-increment (an address no source label can
  name); a goto to a label at the end of the body jumps to the label
  position and *chains through* the backedge jmp.  Also the loop-test
  jcc target shifts.  A `jmp` landing on a for-loop's increment block
  = `continue`, definitively; a jmp-to-the-backedge-jmp = goto.
* **`if (a) return 5;` vs `goto`-to-shared-`return 5;` label:
  DIFFERENT.**  The return-value load happens inside the guarded block
  for the former (jcc skips `mov eax,5; jmp epi` = 10 bytes, not the
  pure 5-byte pair); the goto version emits the pure pair plus the
  label's `mov eax,5; jmp epi` placed at the label's source position.
  Shared-return-label ladders are therefore visible in code layout.
* **Cleanup-ladder gotos**: a jmp from inside a loop to a target
  strictly *past* the loop exit and *before* the epilogue cannot be
  break (wrong target), return (not the epilogue), or continue.
  Undeniable goto.
* **Convergence**: N jmps from different nesting contexts onto one
  shared non-epilogue, non-loop-boundary target = a shared source
  label.

## Classification recipe for a jmp (E9) at /Od

Every unconditional `E9` in a function is exactly one of:

| template position | meaning |
|---|---|
| target = epilogue start | `return` (or goto-to-end; identical) |
| target = enclosing loop's exit (its test's jcc-false target) | `break` (or goto-there; identical) |
| target = enclosing for's increment / while's test | `continue` |
| backward, at end of loop body, target = loop test/increment | loop backedge |
| forward over the increment block, right after for-init | for-loop entry jump |
| at end of a then-body, target = end of else-body | if/else join |
| switch: body-to-end jmps + entry jmp to the compare chain at the END of the switch (cases laid out first, dispatch last) | switch template |
| target = next instruction, guarded-empty-else or pre-epilogue | empty else / last return |
| **anything else** | **goto — undeniable** |

The 11-byte pair `0F 8x 05 00 00 00 E9` additionally pins "bare
conditional jump-statement" (`if (c) goto/break/continue/return;`),
narrowing the candidates before target classification.

## Validation against CAESAR2.EXE

* 1,027 pair-signature hits in `.text`; 475 distinct named functions;
  42 overlap with the 81 decomp/src functions currently containing
  `goto` (the rest are `if(c) return/break/continue;`, CRT, or
  not-yet-decompiled functions).
* `action()` (`0x4b0630`): **23 internal E9s converge on offset
  +0x12c5** — mid-function, real code follows, not the epilogue and
  not a loop boundary.  The recovered source has 28
  `goto end_of_action`.  The convergent-label signal reproduces on
  the shipping binary.

## Deterministic-fragility caveat (do not over-read)

A *dead* (never-jumped-to) label can still perturb codegen: e.g. it
can flip the operand choice of a `g == i` compare
(`mov eax,g; cmp [i],eax` ⇄ `mov eax,[i]; cmp g,eax`, ±1 byte).  But
the same flip is also triggered by ordinary code after the loop with
no label at all — it is a usage/tracking artifact ("fragile but
deterministic", cf. AGENTS.md), NOT a reliable label detector.  Label
placement *inside* the loop head produced no flip.  Treat any such
flip as codegen noise attached to nearby source, not as goto evidence.

## Watcom 10.0a (PS flags `-bt=dos -mf -4r -s -d1`) — the same matrix

Run with the `watcom-10.0a-wibo` image, OMF carve + LINNUM extraction.
The optimizer erases nearly everything MSVC preserves:

* **Full fusion**: `if (c) goto L;` compiles to a single conditional
  jump (no pair).  `goto`-loop == do-while, `goto`-past-loop == break,
  goto-to-end == return, and (unlike MSVC) goto-label-at-body-end ==
  `continue` — all **byte-identical**.
* **goto-to-next eliminated**; **dead labels have zero codegen
  effect** (only a W118 warning at compile time).
* **`-d1` LINNUM carries no label witness**: a label line emits no
  line mark; the byte-identical goto/do-while pair has an identical
  mark stream.  (Beware in experiments: identical function bodies in
  one TU get cross-function-aliased to zero-length PUBDEFs — looks
  like a diff but isn't.)
* What SURVIVES: **non-structured topology** — a *detached* block
  (preceded by `ret`/`jmp`, no fall-through entry, not a pure shared
  epilogue) with >= 2 predecessors.  Structured statements cannot
  produce that shape; cleanup funnels like `action`'s
  `end_of_action` remain visible in PS.EXE.

## The tool: goto-topology census (on by default)

Engine: `c2/goto_topology.py`.  Differential design: compare the
internal-jmp funnel profile of CAESAR2.EXE's copy of a function
against our own MSVC /Od compile of the recovered source — structured
false positives (switch-break funnels, if/else joins) appear on both
sides and cancel; a WIN-only non-epilogue funnel means the original
had a shared label / `continue` we lack (`missing-goto`), the reverse
means we invented one (`extra-goto`).  Funnel kinds: `loop-inc` = a
`continue` (only backedge+continue can converge on a for-increment;
no source label can name it), `return` = plain multi-return (no
information), `label` = a shared source label.  The PS side reports
detached multi-pred blocks as corroboration.

Surfaces (no flags):

* `c2 diagnose <fn>` — a `win-goto:` line whenever the verdict is not
  `consistent`, plus `ps-goto:` corroboration.
* `c2 win-census <fn>` / `c2 win-census --corpus` — the goto-topology
  block / `goto` + `funnels w/o` columns ride along with the
  named-local census (same compiled TU, negligible cost).

Gate on mapping quality like the local census (`usable` >= 0.85).
Byte-exact functions are located via masked search (map-independent),
so a stale func-map VA can't fake a verdict.

Worked example: `get_icon_over` — **PS-byte-exact**, yet the census
says `missing-goto` (WIN funnels `[2,2]` on the two loop increments,
ours `[]`; src gotos 0).  The recovered source wraps the loop body in
`if (allowed) { ... }` where the original used `if (!allowed)
continue;` — Watcom compiles both to identical bytes (proven above),
MSVC /Od does not.  The win witness recovers source shape the PS
oracle is provably blind to.

## Practical use

When a win-target function diffs and the E9 topology of CAESAR2.EXE
shows a non-template jmp target (especially multi-jmp convergence on a
mid-function address), the original source had a label there — write
the `goto`, don't synthesize nested structure.  Conversely, when a
goto in recovered source targets the exact break/return position, the
byte oracle cannot care — pick the structured form.  For the corpus:
`c2 win-census --corpus` ranks the still-diffing block; `missing-goto`
rows with `usable` gate and src gotos 0 are the strongest targets.
