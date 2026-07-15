"""show_battlemap_base — index-expression form sweep  [RESULT CORRECTED 2026-06-30]

CORRECTION
----------
The original conclusion below ("forms canonicalise to identical IL,
negative result") was WRONG — it was reached by reading `c2 disasm`
output (which disassembles PS.EXE, immutable) as if it were the
recompile.  The actual verify data showed the flat form applied to the
TOP edge REMOVED the L64 binir divergence (ir 6/36 -> 5/36).  Combined
with hoisting the nested `unsigned char tile;` decls to top-of-function
(fixes L135), the function reached ir 4/36 — committed in 1242c402.
The flat form is codegen-load-bearing for the multiply decomposition
direction (acc-dest vs y-dest); what IS true is that arithmetic operand
order cannot encode the direction (the front end folds y+y*80 to y*81).

ORIGINAL (WRONG) TEXT KEPT FOR THE RECORD:


HYPOTHESIS (disproved)
----------------------
PS's `show_battlemap_base` emits byte-ASYMMETRIC code for the identical
expression `pm_shown_ptr = pseudo_map[pm_shown_y][pm_shown_x++];` on its
two loop edges (top L64: EBX accumulator; bottom L112: EAX->EDX).  A
deterministic compiler only does that if the SOURCE differs, so this
experiment tried the three known array-index *forms* (2D, cached row
pointer, flat pointer) at both edge sites, combined with the full
tie/reorder lever set at depth 3 (4890 plans).

RESULT
------
The cached-row-pointer (split_expr) and flat-pointer (replace_expr)
forms produce byte-IDENTICAL codegen to the 2D form: Watcom's front end
canonicalises `((int*)pseudo_map)[y*PM_W + x]` and `pseudo_map[y][x]`
to the SAME address-calculation IL (the y*324 stride becomes the same
shl/add strength-reduction chain either way; PM_W never survives as a
multiply).  So the "3 forms" are 1 form at the codegen level, and the
entities.h note claiming the 2D-vs-flat distinction is codegen-load-
bearing is WRONG for this construct (or applied to a different case).

4890 plans, 0 shape improvement; the only byte winner (-7b
swap_stmts(L109,L110)) is the same non-PS-faithful collateral tie the
bare tie-group search already found (it diverges PS's actual bottom-
edge statement order, PS does `i=0` first at L121).

CONCLUSION
----------
The top/bottom accumulator asymmetry is NOT caused by PS writing the
edges in different index forms.  It is driven by the surrounding
register context live at each loop's entry (what GiveBestReg's
`HW_Subset(GivenRegisters, reg)` tie-break and CountRegMoves collapse
off) -- i.e. a pure allocator-context effect, not an index-expression
lever.  Per vendor/open-watcom/bld/cg/c/regalloc.c GiveBestReg: the
winner is max CountRegMoves, tie-broken by "prefer a reg already in
GivenRegisters", then by DoubleRegs iteration order (EAX first).

The genuine remaining question is therefore not "which form" but
"which earlier statement's live-range / seat sets the GivenRegisters
context that flips the bottom-edge accumulator off ebx".  That is a
context-dependence investigation, not a form-swap.
"""
