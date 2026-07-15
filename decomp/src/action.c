// D:\C2\CODE\action.c

#include "c2_data.h"
#include "c2_types.h"

/* File-local supplements (not in c2_data.h) */
/* army_list provided as `struct army_rec army_list[]` via c2_types.h */

/* ---------------------------------------------------------------------
 * Implicit-int callees made VISIBLE (NOT the original PS source shape).
 *
 * PS's .c did not declare these helpers: the calls below were K&R
 * implicit-int, so wcc386 assumed `int f()`.  Declaring them `extern
 * int f()` here is BYTE-NEUTRAL -- identical codegen to the implicit
 * declaration the compiler already synthesised -- and exists only to
 * surface the real cross-TU contract.  The real definitions return a
 * narrower type (noted per line); the caller intentionally reads EAX
 * as int, exactly as PS.EXE does.  Do NOT "correct" these to the real
 * return type -- a typed (char / enum) decl CHANGES the bytes.
 * ------------------------------------------------------------------- */
#ifndef _MSC_VER   /* MSVC win-oracle build force-includes c2_funcs.h (typed) */
extern int affected_by_cover1();   /* really char -- map.c */
extern int colour_cycle_delay1();  /* really char -- lib32.c */
#endif



/* Internal callees and shared helpers (forward decls). */
void save_a_game(void);
void clear_landfill(void);
int  pause_db(void);
void helping(int msg_id);
void show_citymap(void);
void show_regionmap(void);
void show_battlemap(void);
void region_map_screen(int do_black_out);
void act_goto_message(void);
void act_goto_city_map(void);
void act_query_do_help(int idx);
void init_help_history(void);
void rewind_help_history(void);
void get_next_viewed_cohort(int dir);


/* Selection-box helpers used by the act_houses/act_water/... wrappers. */
void get_selection_goods_list(int what);
int control_selection(struct selection_rec *list, int count, int x, int y, int width);
void show_fx_box(int what);
void stop_all_sounds(void);
void stop_db(void);

/* Companion act_house1 used by the housing-cheat branch in act_houses. */
void act_house1(void);

/* Cohort/map maintenance helpers used by act_undo_cm. */

/* Slave-requirements helper used by the act_slave_* +/- wrappers. */
int alter_slave_reqs(int kind, int delta);

/* Misc helpers used by the small toggle/wrap actions. */
void rotate_pm_clockwise(void);
void rotate_pm_anticlockwise(void);
void figure_images(void);
void clear_edge_info(void);

/* Battle-screen helpers. */
void general_reform(int kind);
void select_all_figures(void);
void goto_flag_marker_mode(void);

// FUNCTION: C2 0x2EDE2
// WIN: 0x004b0630
// Lines 131–445
//
// Main per-frame action dispatcher.  Snapshots `scrolling`, dispatches
// based on `pointer_mode` and the various mouse-button flags, then
// triggers sounds and the scrolling-stop hook on exit.
//
// RESIDUE (updated 2026-07-07): the dominant byte diff is still the
// Rule 135 mid-function epilogue: PS anchors the 6-byte pops+ret at
// +0x4a (fall-through from the L142 clear_mouse call; every later
// return funnels BACKWARD to it, incl. the closing-brace `jmp 0x4a`),
// while our compile funnels every return FORWARD to an end epilogue.
// This is the ONLY function in all of PS.EXE with this void-fn shape
// (corpus scan 2026-07-05).  The turbo-mode guard is now written as
// the single-return form `if (left != 0 || right != 0) {calls} return;`
// (byte-neutral vs the old two-return form; matches PS's exact L141
// (single je/jne guard) + L142 (calls, fallthrough-ret) line shape).
//
// 2026-07-07: the Rule 135 MECHANISM was found (e27e4717, evolver.c
// evolve_a_building/devolve_a_building) -- a DEPENDENT function
// compiled immediately after, written arms-first with its own
// call+return as the LAST statements, ComTail-shares enough of its
// epilogue tail with the donor's END-of-RetList copy to trigger
// TransformJumps, which physically moves the donor's trailing
// epilogue block up to the earlier return's position.  Does NOT
// apply here: the next function in this TU, flag_mode_action, saves
// only 4 regs (ebx edx esi ebp) vs action's 5 (ebp esi edx ecx ebx) --
// the common epilogue suffix is just `pop ebx; ret` (2b), below
// ComTail's `max.save > OptInsSize(OC_JMP, OC_DEST_NEAR)` threshold.
// No other function in the corpus emits a matching 5-save frameless
// epilogue immediately after action() in file order.  Probed and NOT
// source-reachable at OptSize=50 by any single-function rewrite
// (Rule-137 restructure, goto-into-if labeled return, `int action` +
// Rule 77 uninit-rc returns, `return int_clear_mouse();` -- all still
// funnel forward; see docs/comtail-cascade-analysis.md).
//
// Site-1 `last_icon_over`-guard Rule 132 (copy-then-shl, PS keeps EAX
// live past the `shl edx,2` because -- per the site-2 guard chain a
// few lines later -- the value is read again): tried embedding the
// guard into the existing `idx` local (`if ((idx = last_icon_over) !=
// 0) { ...[idx]... }`).  This DOES close the Rule-132 island locally,
// but `idx` has an unrelated later live range (L366-397, saves
// reg_placing_type around control_selection) and the extended
// lifetime cascades a NEW divergence at site 2 (PS caches map_mode in
// CH across the `||` chain at L337; the idx-reuse edit loses that
// cache) -- net regression, 1179bd -> 1675bd.  Do not retry this
// lever without a dedicated (non-reused) local, or without also
// re-deriving site 2's CH-cache under the same edit.
//
// 2026-07-07 (win-oracle session): the DEDICATED-local retry was run
// (`else if ((icon = last_icon_over) != 0) { ...[icon]... }` + `int
// icon;`) -- BYTE-NEUTRAL: a local that dies at the index read is
// coalesced into the shifted temp, no copy emitted.  So the L200
// copy+shl is NOT a named local; it is the unscaled cross-block CSE
// temp's SEAT (PS EAX / RC EDX -- when the unscaled and scaled temps
// seat apart, the copy materializes) -- same inconclusive whole-fn
// tie family as the rest.  The dedicated-local lever is CLOSED both
// ways.  Win oracle (unblocked this session): win-decompile shows
// literal `pointer_mode = '\0'` in BOTH L337 arms, refuting a
// `pointer_mode = map_mode` reading of the CH-store; win-census
// Delta=+1 (a 2-use eax slot) is Q=0.82 caution and does not map to
// any PS-demanded local.
//
// Remaining islands (const-1-in-bh L183/187 share, zero-in-ecx
// L180/184 share already correct, map_mode-in-ch L337 site-2 cache,
// copy+shl L200 site-1 Rule 132) are seat/materialization collateral
// of the same inconclusive whole-fn reg-swap cascade (regtrace:
// EAX<->EDX, ECX<->ESI ties; Cascade replay INCONCLUSIVE -- big
// routine).
//
// 2026-07-09: the L337 site-2 "CH cache" is NOT a compiler cache --
// it is an EMBEDDED-ASSIGN LOCAL (`(mm = map_mode) == 0`), proven by
// PS's arm-2 asm RE-READING the global with a fresh zext
// (`xor eax,eax; mov al,[map_mode]; cmp eax,1`) where any cache or
// plain local would reuse the register: only embedded-assign in arm 1
// + inline read in arm 2 produces byte-reg load+test THEN a memory
// re-read.  The `pointer_mode = 0;` store then reuses the known-zero
// CH (condition-derived, same mechanism as build_city_item's
// `ok = 0` -> `mov [esp],eax`); source stays the literal 0 (win
// oracle's '\0' confirmed).  This also matches win-census Delta=+1
// (the unmapped 2-use slot = mm).  Fixing L337 re-rolled the cascade:
// the zoom_in_decay_count compiler-cache at L431/L433 broke (RC went
// cmp-mem + re-read), recovered with a second embedded-assign local
// (`zz`); net ir 7 -> 5.  Residue after the two locals: the epilogue
// pair (structurally blocked, see above), the L175 arm-merge (RC's
// two strip-arm `redraw_icons=1;update_map=1` blocks seat the same
// byte reg -> ComCode merges them; PS seats bh/ch -> both inline;
// pure cascade), an RC-only xor-esi zero re-materialization, the
// set_sound eax literal (fixup-masked in the byte oracle; ledger
// artifact), and zz seated AL (PS BL -> and-inplace vs zext_clr_reg,
// 1b; zz sits in a 34-wide anonymous sav=3 ConfBefore tie group with
// no source handle; Byte-seat CASE D).  Raw bd rose (1179 -> 1768,
// cascade seat/encoding noise downstream of the epilogue size flip);
// judged by shape_distance per Hard Rule #3.
// 2026-07-11 (certified-chain session): the "whole-fn INCONCLUSIVE
// reg-swap cascade" is now LOCALIZED.  c2 regtrace --explain: seat
// diff CLEAN over 501 reg-operands except ONE dword value (6c150f7c,
// sav=31, RC EAX / PS ECX, the L160 pointer_mode zero temp's parent);
// GB row shows all-scores-0 list-order pick, so PS's ECX needs
// EAX/EDX/EBX masked at its seat = the MASKED (live-range) family,
// P5 boundary -- NOT reorderable (savings --flip has no order/credit
// lever for an all-zero-scores pick).  Byte-seat CASE D certified
// [trace] on all 12 byte pairs (ch/bh/bl const-temp rotation).  The
// causal chain: byte const-temp seats -> ComCode keeps/merges the
// L161/L175 twin arms (PS bh/ch = both inline; RC same-reg = merged,
// island 2) -> refs-chain/IL stream -> ComTail picks the OPPOSITE
// epilogue canonical (islands 1+6: PS early-inline + L445 jmp back;
// RC forward-funnel) -> 38/105 diff rows are pure alignment cascade
// (near/short Jcc flips).  Fresh probes this session, all inert on
// the post-mm/zz IL: goto-family re-run (labeled return in turbo arm
// + end goto backward; label outside arm; explicit trailing return)
// all 1768bd -- FE canonicalizes to the same gen-order-end RetList;
// c2 sweep full battery exhausted (composed stmt/decl space, no
// improvement, plateau 1768bd/shape5).  Open lever: P5 masked-family
// tooling (the 6c150f7c mask) or a byte-temp-SET parity change that
// does not regress ir (none found; every candidate regresses).
// 2026-07-11b (divide-and-conquer session): remaining probes run to
// ground.  (1) Island-3 MECHANISM pinned: PS's L184
// `mov [flag_for_workhouse_request],ecx` is NOT a CSE'd zero spanning
// L180-L184 -- a `rz` local probe (`had_clear_sound = rz = 0; ...
// flag_for_workhouse_request = rz;`) compiled BYTE-IDENTICAL (1768bd):
// the FE const-propagates the local away and the allocator still
// rematerializes per site.  PS's form is the redundant-def scorer
// deleting z2's `xor ecx,ecx` because z2 SEATED ECX, which provably
// still holds 0 there (PS's L183 1-temp sits in BH; watcall preserves
// ECX across the two calls); RC's z2 seats ESI because RC's L183
// 1-temp took CH (aliases ECX, breaks the known-zero).  So island 3 =
// pure collateral of the L183 byte seat (CASE D); no independent
// source lever.  (2) Island-2 likewise: RC's three
// `redraw_icons=1;update_map=1;goto end` arms all seat CH ->
// byte-identical post-regalloc -> ComCode merges; PS seats them
// BH/AH/CH -> all inline.  Merge direction is deterministic given
// seats (docs/comtail-cascade-analysis.md); no arm-spelling lever
// changes the bytes without breaking the -d1-witnessed store order.
// (3) `c2 spell --suggest` battery (absent from the 07-11a ledger):
// 0 fold + 0 unfold + 3 tail-dup + 1 tail-hoist, all screened LIVE
// and byte-compiled: L485/k1 neutral (1768bd); L536/k1 1540bd but
// ir 4->6, isl 5->7 (shape regress, rejected per Hard Rule #3);
// L536/k2 ir 7; L520-hoist ir 5, isl 7.  The A2-style certification
// condition (suggest battery empty-or-regressing) is now met.  All 5
// islands + the 1 seat are ONE residue family rooted in the anon
// byte-temp exclusion rotation (first divergent pick: L160's zero
// temp, PS CH / RC AH); nothing upstream of it is source-visible.
// Win-oracle caveat kept in mind throughout: CAESAR2.EXE's source
// lineage is unconfirmed, so its literal-0 witnesses were treated as
// hints only; every verdict above rests on the DOS byte oracle.
// 2026-07-11c (frx ground-truth session) -- THE 07-11a/b FRAMING IS
// OVERTURNED.  The "anonymous byte-temp picks" are NOT GiveBestReg
// conflicts at all (none of the 116 chain conflicts seats AH/CH/BH at
// the swap sites): they are BYTE-CLASS ROVER picks (FindRegister,
// post-RegAlloc), so the Byte-seat CASE D "inert byte tie, IRREDUCIBLE"
// certification does not apply to this function -- rover picks are
// advance-count-steerable (Rule 121 / load-fold class), NOT Rule 133.
// Chasing this exposed and fixed a PAIRWISE-SWAPPED byte NAME table
// (bl<->bh, cl<->ch, dl<->dh) in rover_divergence/rover_fit/reglists
// (watcom repo) and rover_hints._NAME (the c2 Rover hint engine) --
// every prior byte-class k/lever on this function was name-inverted;
// audited clean post-fix (frx-emitted-name-audit.py: 46/46 byte-exact
// action.c fns).  New instrumentation (image 2026-07-11, trace v55):
// frx ground-truth picks paired into fr['truth'] + fr result/op0 name
// identity (sym handle, offset) join every advance -- even Score-
// coalesced ones -- to its global.  Measured k trajectory (walk order,
// correct names): k=0 through the whole dispatch prefix (b0-b19: L228
// zero, zoom pair, pm dispatch, both map_mode loads, all four
// control/overmap arms L251/L253 + strip arms L261/L263, mouse tests);
// k=-2 family covering the right-click update_map (fr#115, PS bh/RC
// ch), L248's redraw+update pair (blk156, PS bh/RC ch+al), and the
// L247/L249 city arms (fr#129 PS ch/RC ah, fr#126 PS bl/RC cl); one
// localized +3 at the pm>=1 arm (fr#123, PS cl/RC dh) whose window
// coincides with the binir "+3 unnamed" diverging lines (the pm-arm
// island).  So the residue = TWO rover advance-count deltas: RC has ~2
// extra byte advances somewhere in walk b19..b50 (the left-click/army
// stretch, fr#38..#113), plus the pm-arm disturbance.  Next session:
// anchor rover_fit --cls byte with ONLY visible form-matched anchors
// (fr#0=ah, #23=ah, #34=bl pins; #115=bh, #123=cl, #126=bl, #129=ch
// wants; note #124/#125 pm=5/gen_refresh1 picks are COMPRESSED-INVISIBLE
// -- c6-imm / Score-reuse -- and must NOT be anchored), then census the
// b19..b50 window for the 2-advance IL delta (zz/update_landfill
// region, lines 536-572 + 378-398).
// 2026-07-11d (mm/zz DE-INVENTED, 1768bd -> 1179bd): the 11a locals are
// register-IMPOSSIBLE and are removed with a mechanism proof.  A GB
// byte conflict at sav=2/3 rank can NEVER seat CH/BL: given-subset
// passes ALL byte candidates by then (every parent dword granted), so
// list order forces AL -- `c2 seats --want mm=CH / zz=BL` both verdict
// tie-order over an empty mask, i.e. unreachable.  PS's actual shapes:
// zz-site = ROVER pick BL + Score redundant-load reuse (`mov bl,[zoom];
// test bl,bl; ... mov al,bl` -- the arm-2 re-read is the COALESCE, not
// a local); mm-site = rover pick CH on a KEPT-SPLIT cmp load (`mov ch,
// [map_mode]; test ch,ch` -- compression blocked), NOT a GB local.  The
// 11a embedded-assign forms matched the SHAPE but could never match the
// registers; their islands were fake-closed.  Post-de-invention k-map
// (frx ground truth, corrected names): k=0 through fr#19 (whole
// dispatch prefix + all six arm stores byte-EXACT-registered), then
// k=+2 UNIFORM from fr#35 (mm site) through fr#88 -- verified by
// sim_with: a single +2 byte inject anywhere in fr#20..#35 lands every
// anchor up to #88 (#35=ch, #40=ah, #85=dl, #88=bh all fit).  So PS has
// exactly TWO extra byte-class rover advances in walk window fr#20..#35
// (statements: L299 right-click guard, L350/351 mouse_left+update, L447,
// L461 + the track_army maze blocks) -- likely a GB grant/deny or
// operand-kind difference (a value PS reads from MEMORY where our GB
// grants a register, or vice versa), NOT a missing statement.  The tail
// (fr#117..#131: right-click arms + city arms) does NOT close under the
// +2 alone: the #122 funnel (except 0x48fff8c0, dl/dh masked) re-syncs
// RC to base while PS lands elsewhere -- PS's excepts differ there,
// rooted in GB dword seats; the chain names 6c1b2f4c EBX->ECX masked
// (live-range lever, contributors ins 6c1b322c(result)/6c1b2ef4(live),
// emitted ~offset 337 = the map_mode==1 zext region).  Downstream
// collateral of the cursor parity (NOT independent islands): the
// [const-realize] pair (update_map=1/gen_refresh1=1: PS picks BH ->
// survives the pointer_mode zext (A-family clobber) -> Score reuses at
// gen_refresh1 -> compression BLOCKED -> mov bh,1 + reuse; RC picks
// A-family -> clobbered -> no reuse -> both compress to c6-imm), the
// kept-split mm cmp, and the known-zero pointer_mode=0 reuse (island 6:
// PS stores from the just-tested CH).  Fix the +2 window and the tail
// masks and these collapse together.  Byte-exact needs: (1) the +2
// construct in fr#20..#35, (2) the 6c1b2f4c live-range lever, (3) the
// Rule 135 epilogue pair (unchanged), (4) the L200 Rule 132 copy.
// 2026-07-11e (ComTail ctm probe session): THE ROOT IS NAMED.  New
// instrumentation (watcom ab36d67, trace v56): `ctm` records every
// ComTail max decision (ins -> winner + save).  action's stream: 60
// decisions -- incremental RetList chaining while returns are created,
// then TWO full re-canonicalization sweeps once the end-of-function
// epilogue node (created LAST, gen-order end) appears: every goto-end
// arm re-points to the END copy (all save=5 ties, ping-pong to a
// fixpoint at the end).  PS's fixpoint = the EARLY (L142) copy.  The
// flipped fixpoint owns BOTH remaining structural islands: the
// mid-epilogue (islands 1+7) AND -- because ComTail/TransformJumps
// surgery reorders the block chain, which IS the LdStAlloc walk
// order -- the byte-rover +2/tail rotation (PS walks the zoom-arm /
// finish_route blocks inline where ours cluster at chain tail
// blk136-138; the 'Rover-blocked: BLOCK-ORDER divergence' hint says
// exactly this).  So the +2 'advance window' of 11d is NOT missing
// ops -- it is the same blocks walked at different chain positions.
// Next lever: recover WHY PS's fixpoint is the early copy -- the
// re-sweep is tie-driven (strict >, save=5 everywhere = first-in-
// refs-chain wins), so the refs-chain ORDER at sweep time decides;
// candidates: reclaim cave space and re-add the ct/ctc probes (per-
// candidate saves + list identity), then probe source forms that
// change the RetList insertion order (the turbo-arm return's position
// in the FE gen order).  The 07-07/07-11a goto-family probes were
// byte-judged under the mm/zz IL; re-run them reading the ctm stream
// (1 s trace) instead of bytes -- the fixpoint flip may be reachable
// where byte-neutral probes looked inert.
// 2026-07-12b (bbcb03ec + this commit): THE RULE 135 EPILOGUE PAIR IS
// CLOSED -- the fixpoint was never intra-action.  PS scan: this_region
// +0xc5, act_query+0xf, act_query_do_help+0xfd all jump INTO action+0x4a,
// and act_query's tail jmp targets action+0x45 (= call clear_mouse + the
// pops), proving act_query's source ended `clear_mouse(); }` -- OUR
// act_query WAS MISSING THAT CALL (invisible: tail-merge splicing +
// rel32 masking kept it 'byte-exact').  With it restored, act_query's
// OC_RET ComTail splices save=6 into action's end epilogue, the OptPush
// retry Untangles act_query's end label away (UnTangle2 jump-to-jump
// Redirect), ComTail re-runs and finds the 10-byte [call clear_mouse +
// jmp] common tail with action's TURBO return-jmp, and TransformJumps
// SWAPS action's [label+pops+ret] up to +0x4a (turbo jmp goes to the
// end, Untangle kills it as jmp-to-next): je/jne/jmp 0x4a all match PS.
// LOAD-BEARING SET (each verified by ablation 2026-07-12):
//   1. act_query ends `pointer_mode = saved_pm; clear_mouse();` (PS-
//      witnessed by its own +0x45 jmp target);
//   2. the turbo arm keeps the TWO-RETURN form below (855e92c3, Mac/Win
//      witnessed) -- the single-return `if(l||r){..} return;` form puts
//      the arm-merge LABEL before the return-jmp and FindCommon stops at
//      5 (labels only skip on the CANDIDATE side; optcom.c FindCommon);
//   3. NO zoom-arm duplication of `pointer_mode = 0` (Rule 121 inverse
//      probe): it kills the dance (1178bd, L142/L445 back) AND is
//      counter-witnessed by Mac+Win (assignment shared after if/else).
// Remaining residue after this: L183/187 const-realize, L200 copy+shl,
// L337 kept-split + xor-ah, the byte-rover swaps + 6c1b2f4c EBX->ECX
// masked seat, and a 5b tail length-drift artifact from the above.
// 2026-07-12c (667bd / ir3 / isl4 -- the current floor-of-record):
// * The (unsigned char) base_kind cast (L~424) is RE-VALIDATED post-
//   epilogue-fix: 667bd with it, 1447bd without (the 855e92c3 rejection
//   was measured under the pre-dance IL and is superseded); PS's
//   `and eax,0xff` realization at the 0xd2 compare still reproduces.
// * The zoom block MUST stay the shared form (`do_act_zoom_in(1/0)` in
//   arms, ONE `pointer_mode = 0` after) -- asm-witnessed: PS's single
//   call with the eax bool materialization (cmp/jle/mov 1/jmp/xor) is
//   ComTail's merge of the two arm calls; the plain bool-arg spelling
//   `do_act_zoom_in(zoom>3)` compiles DIFFERENTLY (1442bd, ir6).  The
//   L699-dup sweep/suggest candidates trade this shape for rover bytes
//   (649/645bd but ir2->4, un-witnessed) -- rover crutch, rejected.
// * WIN-oracle witnessed, Watcom-neutral (kept): the prologue stores
//   are SEPARATE statements (`scrolling = 0; stopped_scrolling = 0;`,
//   not chained) and the zoom increment is `zoom_in_decay_count++`.
// * The byte-rover picture (measured via the frx k-map + full-disasm
//   pick lists): RC's byte pick stream in the dispatch is perfectly
//   sequential (no mask skips); PS is +2 ONLY at the city-arm stores
//   (+00dc/+00f2/+0112) while the region twins match -- with a -1
//   window at +029e and +2/+4 windows further down.  rover_hints
//   _search finds NO single-inject fit over the const-store positions;
//   the L382-384 city blocks are 'chained-late' (Rule 125) in RC's
//   chain (walked AFTER the region arms).  The zoom-dup experiments
//   prove chain restructuring MOVES these early picks (a late-walk dup
//   fixed early sites) -- the lever class is BLOCK-CHAIN structure,
//   not advance count.  Blocked pending fr<->em ins-level join tooling
//   (to read which blocks PS walks between the region and city picks);
//   every statement-level respelling probed this session was inert
//   (explicit goto right_click_dispatch in the city block, chain
//   split, ++ form) or shape-regressing (bool-arg, dup family, L683
//   hoist 1827bd).
// 2026-07-12: the initial Rule 121 inverse (duplicating
// `pointer_mode = 0` into both do_act_zoom_in arms) improved the allocator
// but was rejected after both Mac and Win showed the assignment shared
// after the if/else.  Both oracles instead expose the missing turbo-arm
// shape: `if (!left && !right) return;`, then the two calls and a second
// return.  Once the wrong cast candidates are removed this correction is
// byte/shape-neutral (ir 6/196, 1179bd), but it is retained because both
// cross-build witnesses and PS's L141/L142 control flow agree.  `forge`
// also proposed changing the L228 `& 0xff` to a cast; rejected because PS
// explicitly has the mask
// realization and that cast caused a large byte/shape regression.
// 2026-07-13 BYTE-EXACT (Watcom sa/gi/br/bre/bk/frx instrumentation): the
// remaining cascade was MakeFlowGraph DFS/RPO + ReturnsToBottom block order,
// not a missing zoom local or a GiveBestReg tie.  Restoring the source-oracle
// direct map tests, then spelling the two load-bearing pointer tests as
// `!(pointer_mode != 3)` and `!(pointer_mode == 4)`, preserves their emitted
// comparisons but changes the pre-LdStAlloc block walk.  The first change
// collapses 1364bd / four islands to one two-byte rover seat; the second moves
// the hauled exit blocks across that zero store, seating it in PS's CL and
// closing 2bd -> 0.  Raw frx confirms all later byte picks self-heal; all
// 640/640 instructions match register-blind before the final seat correction.
// Packing the L187 pointer_mode/gen_refresh1/goto trio on one physical line
// is byte-neutral but matches PS's single -d1 line (boundary mismatches 58->56).
void action(void)
{
    int icons_helped;       /* index into city/region_icons_to_help */
    int idx;                /* save reg_placing_type around control_selection */

    old_scrolling = scrolling;
    scrolling = 0;
    stopped_scrolling = 0;
    illegal_build = 0;

    if (turbo_mode > 1) {
        if (mouse_left_preclick == 0 && mouse_right_preclick == 0) {
            return;
        }
        act_exit_turbo_mode();
        clear_mouse();
        return;
    }

    action_sound = 0;
    if (zoom_in_decay_count != 0) zoom_in_decay_count++;

    if (tutorial_mode != 0 && exit_screen_at(0x250, 0x1b0) != 0) { out4 = 1; goto end_of_action; }

    get_icon_over();

    if (pointer_mode == 0 || pointer_mode == 2 || pointer_mode == 6) {
        if (map_mode == 0) {
            if (control_menus(main_menu, 4, show_citymap) != 0) { pointer_mode = 0; goto end_of_action; }
            if (perform_city_strip_action() != 0) { redraw_icons = 1; update_map = 1; goto end_of_action; }
            if (use_city_overmap_to_move() != 0) { pointer_mode = 0; show_landfill(com_x, com_y); setup_refresh_area(0x1e0, 0x18, 10, 0xb, 1); goto end_of_action; }
        } else if (map_mode == 1) {
            if (control_menus(main_menu, 4, show_regionmap) != 0) { pointer_mode = 0; unflag_all_rm_xwarehouse(); goto end_of_action; }
            if (perform_region_strip_action() != 0) { redraw_icons = 1; update_map = 1; unflag_all_rm_xwarehouse(); goto end_of_action; }
            if (use_region_overmap_to_move() != 0) { pointer_mode = 0; show_landfill(com_x, com_y); setup_refresh_area(0x1e0, 0x18, 10, 0xb, 1); unflag_all_rm_xwarehouse(); goto end_of_action; }
        }
    } else if (pointer_mode == 5) {
        if (perform_cohort_box_action() != 0) { goto end_of_action; }
    } else if (pointer_mode == 1 && last_icon_over == 0xd) {
        if (map_mode == 0) {
            if (perform_city_strip_action() != 0) { redraw_icons = 1; update_map = 1; goto end_of_action; }
        } else if (map_mode == 1) {
            if (perform_region_strip_action() != 0) { redraw_icons = 1; update_map = 1; goto end_of_action; }
        }
    }

    if (mouse_right_preclick != 0) {
        had_clear_sound = 0;
        unflag_all_rm_xwarehouse();
        setup_whole_screen_refresh();
        update_map = 1;
        flag_for_workhouse_request = 0;

        if (!(pointer_mode == 4)) {
            if (pointer_mode >= 6) {
                pointer_mode = 5; gen_refresh1 = 1; goto end_of_action;
            }
            if (pointer_mode >= 1) {
                pointer_mode = 0;
                goto end_of_action;
            }
        }

        if (over_an_army != 0) {
            tracking_army = over_an_army;
            pointer_mode = 5;
            gen_refresh1 = 1;
            setup_whole_screen_refresh();
        } else if (pm_over != 0) {
            act_query();
        } else if (last_icon_over != 0) {
            if (map_mode == 0) {
                icons_helped = city_icons_to_help[last_icon_over];
            } else {
                icons_helped = region_icons_to_help[last_icon_over];
            }
            if (icons_helped != 0) {
                clear_mouse();
                helping(icons_helped);
            }
        }
        goto end_of_action;
    }

    scroll();
    mouse_follow_cohort();
    show_latest_route();
    mouse_hunt_enemies();
    particles_cleared = 0;
    particles_built = 0;

    if (mouse_left_preclick != 0 && pm_over != 0) {
        update_map = 1;
        total_build_cost = 0;
        industry_build_on = 0;
        industry_build_ok = 0;

        if (over_an_army != 0
         && (reg_placing_type != 0x21
             || ((unsigned char)(*(struct region_cell *)((unsigned char *)region_map + (pm_over_cm_ptr))).base_kind) != 0xd2)) {
            tracking_army = over_an_army;
            pointer_mode = 5;
            gen_refresh1 = 1;
            setup_whole_screen_refresh();
            goto end_of_action;
        }

        if (pointer_mode == 1) {
            zoom_in_decay_count = 1;
            goto end_of_action;
        }
        if (pointer_mode == 2) {
            goto end_of_action;
        }
        if (!(pointer_mode != 3)) {
            pointer_mode = 5;
            gen_refresh1 = 1;
            setup_whole_screen_refresh();
            goto end_of_action;
        }
        if (pointer_mode == 4) {
            act_query();
            goto end_of_action;
        }
        if (pointer_mode == 5) {
            goto end_of_action;
        }
        if (pointer_mode == 6 || pointer_mode == 7 || pointer_mode == 8) {
            setup_map_screen_refresh();
            if (((*(struct region_cell *)((unsigned char *)region_map + (pm_over_cm_ptr))).place_state & 0xff) == 0xff) {
                return;
            }
            get_over_coords();

            if (pointer_mode == 7) {
                if (army_list[tracking_army].state_idx == 1) {
                    army_list[tracking_army].flags |= 1;
                }
                army_list[tracking_army].state_idx = 3;
                army_list[tracking_army].dest_y = 0;
                army_list[tracking_army].dest_x = 0;
                army_list[tracking_army].return_flag = 1;
                army_list[tracking_army].wf_active = 0;
                if (this_route_number >= 9) {
                    this_route_number = 10;
                }
                army_list[tracking_army].target_x = army_routes[army_list[tracking_army].cohort_id].points[0][0].x;
                army_list[tracking_army].target_y = army_routes[army_list[tracking_army].cohort_id].points[0][0].y;
                army_routes[army_list[tracking_army].cohort_id].army_x = army_list[tracking_army].x;
                army_routes[army_list[tracking_army].cohort_id].army_y = army_list[tracking_army].y;
                army_routes[army_list[tracking_army].cohort_id].over_x = over_x;
                army_routes[army_list[tracking_army].cohort_id].over_y = over_y;
                army_routes[army_list[tracking_army].cohort_id].row_count = this_route_number;
                army_routes[army_list[tracking_army].cohort_id].chase_row = 0;
                army_routes[army_list[tracking_army].cohort_id].target_army = 0;
                unflag_all_rm_xwarehouse();
                pointer_mode = 2;
                update_map = 1;
                goto end_of_action;
            } else if (pointer_mode == 8) {
                if (army_list[tracking_army].state_idx == 1) {
                    army_list[tracking_army].flags |= 1;
                }
                army_list[tracking_army].state_idx = 3;
                army_list[tracking_army].dest_y = 0;
                army_list[tracking_army].dest_x = 0;
                army_list[tracking_army].wf_active = 0;
                army_list[tracking_army].return_flag = 1;
                army_list[tracking_army].target_x = army_routes[army_list[tracking_army].cohort_id].points[0][0].x;
                army_list[tracking_army].target_y = army_routes[army_list[tracking_army].cohort_id].points[0][0].y;
                army_routes[army_list[tracking_army].cohort_id].army_x = army_list[tracking_army].x;
                army_routes[army_list[tracking_army].cohort_id].army_y = army_list[tracking_army].y;
                army_routes[army_list[tracking_army].cohort_id].over_x = over_x;
                army_routes[army_list[tracking_army].cohort_id].over_y = over_y;
                army_routes[army_list[tracking_army].cohort_id].row_count = this_route_number + 1;
                army_routes[army_list[tracking_army].cohort_id].chase_row = this_route_number;
                army_routes[army_list[tracking_army].cohort_id].target_army = hunting_army;
                if (this_route_number == 0) {
                    enemy_army = hunting_army;
                    army_list[tracking_army].army_id = enemy_army;
                    army_list[tracking_army].target_marker = army_list[enemy_army].evolve_timer;
                    army_list[tracking_army].state_idx = 4;
                }
                unflag_all_rm_xwarehouse();
                pointer_mode = 2;
                update_map = 1;
                goto end_of_action;
            } else {
                if (this_route_number < 9) {
                    this_route_number = this_route_number + 1;
                    set_route_elastic();
                    save_undo_info();
                }
                goto end_of_action;
            }
        }

        if (map_mode == 0) {
            prebuild_city_item();
            if (placing_type == 0xff) {
                goto end_of_action;
            }
        } else if (map_mode == 1) {
            prebuild_region_item();
            if (reg_placing_type == 0xff) {
                goto end_of_action;
            }
        }
        save_undo_info();
    }

    if (mouse_left_preclick != 0 && pointer_mode == 4) {
        if (map_mode == 0 && last_icon_over == 0x17) {
            pointer_mode = 0;
            redraw_icons = 1;
        } else if (map_mode == 1 && last_icon_over == 0x13) {
            pointer_mode = 0;
            redraw_icons = 1;
        } else if (last_icon_over != 0) {
            if (map_mode == 0) {
                icons_helped = city_icons_to_help[last_icon_over];
            } else {
                icons_helped = region_icons_to_help[last_icon_over];
            }
            if (icons_helped != 0) {
                helping(icons_helped);
            }
            goto end_of_action;
        }
    }

    if (mouse_left_button != 0 && pm_over != 0) {
        action_sound = 2;
        total_build_cost = 0;
        if (pointer_mode >= 1 && pointer_mode <= 9) {
            goto end_of_action;
        }
        if (map_mode == 0) {
            build_city_item();
        } else if (map_mode == 1) {
            build_region_item();
        }
        refresh_big_action_square((mouse_x - 0x50) >> 4,
                                  (mouse_y - 0x78) >> 4);
    }

    if (mouse_left_click != 0) {
        had_clear_sound = 0;
        if (pointer_mode >= 2 && pointer_mode <= 9) {
            action_sound = 2;
            goto end_of_action;
        }

        if (any_army_building_adjusts() != 0) {
            confirm(3, 0xa0, 0xa0);
            if (decision == 1) {
                army_building_adjusts();
            } else {
                restore_region_from_undo_buffer();
            }
        }
        clear_all_cm(2);

        if (reg_placing_type >= 0x25 && reg_placing_type <= 0x29) {
            if (industry_build_on != 0 && industry_build_ok == 0) {
                idx = reg_placing_type;
                if (reg_placing_type == 0x25) {
                    get_selection_goods_list(1);
                    control_selection(farm_selection, 5,
                                      mouse_x - 0x50, mouse_y - 0x50,
                                      0x11);
                    if (selection_is == 0) {
                        industry_build_ok = 1;
                    }
                } else if (reg_placing_type == 0x26) {
                    get_selection_goods_list(2);
                    control_selection(mine_selection, 5,
                                      mouse_x - 0x50, mouse_y - 0x50,
                                      0x12);
                    if (selection_is == 0) {
                        industry_build_ok = 1;
                    }
                } else if (reg_placing_type == 0x27) {
                    get_selection_goods_list(3);
                    control_selection(quarry_selection, 5,
                                      mouse_x - 0x50, mouse_y - 0x50,
                                      0x13);
                    if (selection_is == 0) {
                        industry_build_ok = 1;
                    }
                }
                if (reg_placing_type == 0) {
                    industry_build_ok = 1;
                } else {
                    industry_build_on = 0;
                }
                reg_placing_type = idx;
            }
            if (industry_build_ok != 0) {
                restore_region_from_undo_buffer();
                industry_build_ok = 0;
                industry_build_on = 0;
                total_build_cost = 0;
                denarii = starting_denarii;
                particles_built = 0;
                particles_cleared = 0;
            }
        }

        current_construction_cost = current_construction_cost + total_build_cost;
        if (total_build_cost != 0) {
            set_sound("place.wav", 1);
            if (map_mode == 0) {
                get_landfill(1);
                update_landfill = 1;
            }
            if (reg_placing_type >= 0x25 && reg_placing_type <= 0x29) {
                flag_for_workhouse_request = 0;
                extended_confirm(0xb, 0xa0, 0xa0);
                clear_mouse();
                if (decision == 1) {
                    if (reg_placing_type >= 0x25 && reg_placing_type <= 0x27) {
                        flag_for_workhouse_request = 1;
                    }
                    act_rm_warehouse();
                }
            } else if (reg_placing_type == 0x24
                       && flag_for_workhouse_request != 0) {
                extended_confirm(0xc, 0xa0, 0xa0);
                clear_mouse();
                if (decision == 1) {
                    act_rm_workhouse();
                }
                flag_for_workhouse_request = 0;
            } else {
                flag_for_workhouse_request = 0;
            }
        }
        total_build_cost = 0;
        update_landfill = 1;
        update_map = 1;
        if (pointer_mode == 1 && zoom_in_decay_count != 0) {
            if (zoom_in_decay_count > 3) {
                do_act_zoom_in(1);
            } else {
                do_act_zoom_in(0);
            }
            pointer_mode = 0;
            zoom_in_decay_count = 0;
            goto end_of_action;
        }
    }

    if (action_sound != 1) {
        action_sound = 2;
    }

end_of_action:
    if (action_sound == 1) {
        do_neg();
    } else if (action_sound == 0) {
        do_pos();
    }
    if (old_scrolling != scrolling && old_scrolling == 1) {
        stopped_scrolling = 1;
    }

}

// FUNCTION: C2 0x2F902
// WIN: 0x004b1951
// Lines 448–485
//
// Per-frame dispatcher used while the player is in flag-marker
// (banner) placement mode.  Mostly delegates to the city/region
// strip-action helpers and lets the user toggle a flag at the cell
// under the cursor on left click.
void flag_mode_action(void)
{
    old_scrolling = scrolling;
    scrolling = 0; stopped_scrolling = 0; illegal_build = 0;

    get_icon_over();

    if (map_mode == 0) {
        if (control_menus(main_menu, 4, show_citymap) != 0) {
            flag_mode = 0;
            update_map = 1;
            setup_map_screen_refresh();
            goto flag_done;
        }
        if (perform_city_strip_action() != 0) {
            redraw_icons = 1;
            update_map = 1;
            setup_map_screen_refresh();
            goto flag_done;
        }
        if (use_city_overmap_to_move() != 0) {
            show_landfill(com_x, com_y);
            update_map = 1;
            setup_map_screen_refresh();
            goto flag_done;
        }
    } else if (map_mode == 1) {
        if (control_menus(main_menu, 4, show_regionmap) != 0) {
            flag_mode = 0;
            update_map = 1;
            setup_map_screen_refresh();
            goto flag_done;
        }
        if (perform_region_strip_action() != 0) {
            redraw_icons = 1;
            update_map = 1;
            setup_map_screen_refresh();
            goto flag_done;
        }
        if (use_region_overmap_to_move() != 0) {
            show_landfill(com_x, com_y);
            update_map = 1;
            setup_map_screen_refresh();
            goto flag_done;
        }
    }

    scroll();

    if (mouse_left_preclick != 0 && pm_over != 0) {
        if (map_mode == 0) {
            if (toggle_city_flag(pm_over_cm_ptr) == 0) {
                put_message(0x66, 0, 0);
            }
        } else if (map_mode == 1) {
            if (toggle_prov_flag(pm_over_cm_ptr) == 0) {
                put_message(0x66, 0, 0);
            }
        }
        update_map = 1;
        setup_map_screen_refresh();
    }

    if (mouse_right_preclick != 0) {
        flag_mode_decay_count = 0; flag_mode = 0;
        do_pos();
        setup_map_screen_refresh();
    }

flag_done:
    if (old_scrolling != scrolling && old_scrolling == 1) {
        stopped_scrolling = 1;
    }
}

// FUNCTION: C2 0x2FA7D
// WIN: 0x004b1b8f
// Lines 487–556
//
// Per-frame dispatcher used during a tactical battle.  Updates the
// hover / drag highlights, kicks off select/move/aim actions on left
// click, and exits to the city map on right click.
void battle_action(void)
{
    old_scrolling = scrolling;
    scrolling = 0; stopped_scrolling = 0; illegal_build = 0;

    if (zoom_in_decay_count != 0) zoom_in_decay_count = zoom_in_decay_count + 1;

    if (control_menus(main_menu, 4, show_battlemap) != 0) goto end_battle_action;
    if (perform_battle_strip_action() != 0) { redraw_icons = 1; update_map = 1; goto end_battle_action; }

    scroll();

    if (pm_over != 0) {

        act_start_pm_ptr = pm_over_cm_ptr;
        act_start_ptr = pm_over_cm_ptr / map_actual_atom;
        act_start_x = act_start_ptr % map_actual_width;
        act_start_y = act_start_ptr / map_actual_width;
        if (pointer_mode == 1) show_move_highlight();
        else if (pointer_mode == 2) show_aim_highlight();
    }
    else {

        battle_drag_on = 0;
    }

    if (mouse_left_preclick != 0 && pm_over != 0) {

        if (pointer_mode == 0 && zoom_level == 1) {

            if ((*(struct battle_cell *)((unsigned char *)battle_map + (pm_over_cm_ptr))).figure != 0) select_a_unit((*(struct battle_cell *)((unsigned char *)battle_map + (pm_over_cm_ptr))).figure, 0);
            else {

                deselect_all_figures();
                battle_drag_on = 1;
                battle_drag_start_x = act_start_x;
                battle_drag_start_y = act_start_y;
            }
        }
        if (pointer_mode == 1) start_move();
        else if (pointer_mode == 2) start_aim();
    }

    if (mouse_left_button != 0 && pm_over != 0) {

        if (battle_drag_on != 0) {

            deselect_all_figures();
            select_drag_figures();
        }
    }

    if (mouse_left_click != 0) {

        battle_drag_on = 0;
    }

    if (mouse_left_preclick != 0) {

        if (battle_setup_count != 0) battle_setup_count = 2;
    }

    if (mouse_right_preclick != 0) {

        pointer_mode = 0;
        redraw_icons = 1;
        if (battle_setup_count != 0) battle_setup_count = 2;
    }
end_battle_action:
    if (old_scrolling != scrolling && old_scrolling == 1) stopped_scrolling = 1;
}

// FUNCTION: C2 0x2FC9B
// WIN: 0x004b1df5
// Lines 560–590
//
// Edge-of-screen panning.  When the mouse is at one of the screen
// edges, advances `pm_x`/`pm_y` by `scroll_amount` (or twice that for
// the top/bottom rows).  After moving, asks `scroll_speed()` whether
// scrolling is allowed this frame; if not, restores the saved
// coordinates and clears the `scrolling` flag.
void scroll(void)
{
    int saved_pm_x = pm_x;
    int saved_pm_y = pm_y;

    /* Province (large) map at zoom 2 doesn't scroll on edges. */
    if (map_mode == 2 && zoom_level == 2) {
        return;
    }
    /* Pointer mode 5 (cohort tracking) suppresses scrolling. */
    if (pointer_mode == 5) {
        return;
    }

    /* Top edge — scroll up. */
    if (mouse_y <= 0 && pm_y > 0) { pm_y = pm_y - scroll_amount * 2; scrolling = 1; update_map = 1; setup_map_screen_refresh(); }
    /* Bottom edge — scroll down. */
    if (mouse_y >= screen_height && (0xa0 - pm_screen_height) > pm_y) { pm_y = pm_y + scroll_amount * 2; scrolling = 1; update_map = 1; setup_map_screen_refresh(); }
    /* Left edge — scroll left. */
    if (mouse_x <= 0 && pm_x > 0) { pm_x = pm_x - scroll_amount; scrolling = 1; update_map = 1; setup_map_screen_refresh(); }
    /* Right edge — scroll right. */
    if (mouse_x >= screen_width && (0x50 - pm_screen_width) > pm_x)
    { pm_x = pm_x + scroll_amount; scrolling = 1; update_map = 1; setup_map_screen_refresh(); }

    if (scrolling != 0) {
        if (scroll_speed() == 0) {
            pm_x = saved_pm_x;
            pm_y = saved_pm_y;
            scrolling = 0;
        }
    }
}

// FUNCTION: C2 0x2FDF5
// WIN: 0x004b1f7d
// Lines 592–619
//
// On the region map (map_mode == 1) and only while the player is in
// pointer_mode 2 or 3 (over-army or tracking-army), keep the mouse
// pulled toward the army's screen coordinates.  Drops back to
// pointer_mode 2 if the cursor wanders too far.
//
// cohort_tick_gate is a small "tick gate" so the mouse only nudges every
// other frame.
void mouse_follow_cohort(void)
{
    /* PS: unnamed function-local static (data 0x87c60, no -d1 symbol) --
       the every-other-frame nudge gate. */
    static int cohort_tick_gate;
    int dist;
    int ax;
    int ay;

    if (map_mode != 1) { tracking_army = 0; return; }
    if (pointer_mode <= 1) { tracking_army = 0; return; }
    if (pointer_mode >= 4) return;
    if (pm_over == 0) { tracking_army = 0; pointer_mode = 2; return; }

    if (pointer_mode == 2) dist = get_nearest_army_to_track(mouse_x, mouse_y);
    else if (pointer_mode == 3) dist = get_tracking_army_distance(tracking_army, mouse_x, mouse_y);

    if (dist >= 0x18) { tracking_army = 0; pointer_mode = 2; return; }


    pointer_mode = 3;
    if (cohort_tick_gate >= 2) { cohort_tick_gate = 0; return; }
    cohort_tick_gate = cohort_tick_gate + 1;
    ax = army_list[tracking_army].map_x; if (ax < mouse_x) { mse_x = (short)(mouse_x - 1); }
    else if (ax > mouse_x) { mse_x = (short)(mouse_x + 1); }
    else { mse_x = mouse_x; }
    ay = army_list[tracking_army].map_y; if (ay < mouse_y) { mse_y = (short)(mouse_y - 1); }
    else if (ay > mouse_y) { mse_y = (short)(mouse_y + 1); }
    else { mse_y = mouse_y; }
    set_mouse();
}

// FUNCTION: C2 0x2FF3C
// WIN: 0x004b2194
// Lines 621–646
//
// Twin of `mouse_follow_cohort` for hostile armies.  Active when the
// player is in pointer_mode 6..8 (the attack-target modes); pulls the
// mouse toward the hovered enemy army's screen coordinates so the
// cursor "snaps" onto the unit it last selected.
void mouse_hunt_enemies(void)
{
    /* PS: unnamed function-local static (data 0x87c64, no -d1 symbol) --
       the every-other-frame nudge gate (twin of mouse_follow_cohort's). */
    static int enemy_tick_gate;
    int dist;
    int ax;
    int ay;

    if (map_mode != 1) {
        hunting_army = 0;
        return;
    }
    if (pointer_mode <= 5) {
        hunting_army = 0;
        return;
    }
    if (pointer_mode >= 9) {
        hunting_army = 0;
        return;
    }
    if (pm_over == 0) {
        hunting_army = 0;
        return;
    }

    dist = get_nearest_enemy_to_track(mouse_x, mouse_y);
    if (dist >= 0x18) {
        hunting_army = 0;
        return;
    }

    pointer_mode = 8;

    if (enemy_tick_gate >= 2) {
        enemy_tick_gate = 0;
        return;
    }
    enemy_tick_gate = enemy_tick_gate + 1;

    ax = army_list[hunting_army].map_x;
    if (ax < mouse_x) {
        mse_x = (short)(mouse_x - 1);
    } else if (ax > mouse_x) {
        mse_x = (short)(mouse_x + 1);
    } else {
        mse_x = mouse_x;
    }
    ay = army_list[hunting_army].map_y;
    if (ay < mouse_y) {
        mse_y = (short)(mouse_y - 1);
    } else if (ay > mouse_y) {
        mse_y = (short)(mouse_y + 1);
    } else {
        mse_y = mouse_y;
    }

    set_mouse();
}

// FUNCTION: C2 0x30071
// WIN: 0x004b2362
// Lines 648–676
//
// While drawing an attack/move route across the region map (pointer
// modes 6..8), trace and highlight the elastic path from the source
// to the cell under the cursor.  Switches to pointer_mode 7 when a
// route segment lands on a destination tile, or 6 otherwise.
void show_latest_route(void)
{
    unsigned char terrain;

    if (pointer_mode < 6 || pointer_mode > 8) {
        return;
    }
    if (pm_over == 0) {
        return;
    }

    pointer_mode = 6;
    get_over_coords();

    terrain = (*(struct region_cell *)((unsigned char *)region_map + (pm_over_cm_ptr))).place_state;
    if (terrain > 0x20 || terrain < 1) {
        return;
    }

    restore_region_from_undo_buffer();
    trace_back_route_elastic();

    if (this_route_number >= 9) {
        pointer_mode = 7;
        (*(struct region_cell *)((unsigned char *)region_map + (pm_over_cm_ptr))).edge_bits |= 0x80;
    } else if (army_list[tracking_army].x == over_x
            && army_list[tracking_army].y == over_y) {
        if (this_route_number > 0) {
            pointer_mode = 7;
        } else {
            pointer_mode = 6;
        }
    } else {
        unsigned int flags =
            (unsigned char)((*(struct region_cell *)((unsigned char *)region_map + (pm_over_cm_ptr))).edge_bits & 0x80);
        if (flags != 0) {
            pointer_mode = 7;
        } else {
            pointer_mode = 6;
            (*(struct region_cell *)((unsigned char *)region_map + (pm_over_cm_ptr))).edge_bits |= 0x80;
        }
    }

    setup_refresh_area(mouse_x - 0x40, mouse_y - 0x40, 9, 9, 2);
}

// FUNCTION: C2 0x30173
// WIN: 0x004b24d7
// Lines 679–693
//
// Snapshot the current cursor position and current denarii at the
// instant the player presses LMB to start a build, then dispatch to
// the per-tool "elastic preview" helper for road/wall/aqueduct.  The
// landscape clears the c0..0xDF flag bits used by the pseudo cursor
// trail so the next preview starts from a clean slate.
void prebuild_city_item(void)
{
    act_start_pm_ptr = pm_over_cm_ptr;
    act_start_ptr = pm_over_cm_ptr / map_actual_atom;
    act_start_x = act_start_ptr % map_actual_width;
    act_start_y = act_start_ptr / map_actual_width;

    unflag_all_cm(3, 0xdf);
    starting_denarii = denarii;
    hot_key_out_off_build = 0;

    if (placing_type == 2) {
        get_road_elastic();
    } else if (placing_type == 3) {
        get_wall_elastic();
    } else if (placing_type == 4) {
        get_aquaduct_elastic();
    }
}

// FUNCTION: C2 0x3020C
// WIN: 0x004b2585
// Lines 695–1007
//
// Per-frame "build the placing_type item" handler.  Called from
// `action()` when LMB is held and the cursor is over the city map.
// One huge dispatch on `placing_type`; each branch first restores
// the city-map snapshot taken by `prebuild_city_item`, then drops
// the appropriate building footprint via put_xN_area / build_*_from
// helpers.  Costs are settled at the bottom against `placing_cost`
// and the per-tile clear cost.
//
// Source-shape evidence retained after the byte-exact cleanup:
//   * PS -d1 marks and both the raw Mac PPC and Windows /Od builds show the
//     warning guard reading the global directly and passing literal zero.
//   * The Bath call result and its test are distinct PS statements; the Mac
//     and Windows builds agree, hence the semantic `has_cover` local.
//   * PS gives each `building_type` load its own line mark and keeps the value
//     live through the guarded call; scoped per-arm declarations produce a
//     different front-end value set, so this is source state rather than a
//     rover-only carrier.
// The declaration order is Watcom-load-bearing.  No dead stores, chained
// assignments, comma identities, or one-use rover compensators remain.
void build_city_item(void)
{
    int gfx_b_idx;
    unsigned int house_gfx;
    int gfx_a_idx;
    int dy;
    unsigned int tgfx_b;
    unsigned int fountain_gfx;
    int gfx_a;
    int gfx_b;
    int ok;
    unsigned int building_gfx;
    unsigned int shape;
    unsigned int building_type;
    int has_cover;
    int dx;

    illegal_build = 2;
    CM_CELL(pm_over_cm_ptr).edge_bits |= 1;

    if (slave_requirements[0].current < slave_requirements[0].max) {
        if (warned_of_not_build != 0) return;
        warned_of_not_build = 1;
        put_message(0x65, 0, 0);
        return;
    }

    if (placing_type != 0) denarii = starting_denarii;
    particles_cleared = particles_built = 0;

    if (placing_type == 0x2) {  /* Road */
        restore_city_from_undo_buffer();
        if (hot_key_out_off_build == 0) build_road_from_elastic();
        if (pm_over != 0 && pm_over != old_pm_over) setup_map_screen_refresh();
    }
    if (placing_type == 0x3) {  /* Wall */
        restore_city_from_undo_buffer();
        if (hot_key_out_off_build == 0) build_wall_from_elastic();
        if (pm_over != 0 && pm_over != old_pm_over) setup_map_screen_refresh();
    }
    if (placing_type == 0x4) {  /* Aqueduct */
        restore_city_from_undo_buffer();
        if (hot_key_out_off_build == 0) build_aquaduct_from_elastic();
        if (pm_over != 0 && pm_over != old_pm_over) setup_map_screen_refresh();
        evolve_row = 0; evolve_water_supply_baths_industry(0x50);
    }

    if (placing_type == 0x1) {  /* Clear / bulldoze (with aqueduct-removal confirm) */
        restore_city_from_undo_buffer();
        /* Aqueduct-removal confirmation: only if cursor stayed put,
         * the cell has the +1 (terrain & 0x20) and (terrain & 0x40)
         * markers, and the player confirms. */
        if (act_start_x == over_x
         && act_start_y == over_y) {
            if ((CM_CELL(pm_over_cm_ptr).terrain & 0x20) != 0) {
                if ((CM_CELL(pm_over_cm_ptr).terrain & 0x40) != 0) {
                    confirm(10, 0xa0, 0xa0);
                    if (decision == 0) {
                        CM_CELL(pm_over_cm_ptr).terrain &= 0xdf;
                        building_type = CM_CELL(pm_over_cm_ptr).base_kind;
                        if (building_type == 0xd5) { CM_CELL(pm_over_cm_ptr).base_kind = 0xcf; CM_CELL(pm_over_cm_ptr).extra_edge = 0x79; }
                        else { CM_CELL(pm_over_cm_ptr).base_kind = 0xd0; CM_CELL(pm_over_cm_ptr).extra_edge = 0x76; }
                        aquaduct_ramifications(over_x, over_y);
                        setup_map_screen_refresh();
                        goto after_clear;
                    }
                }
            }
        }
        if (hot_key_out_off_build == 0) clear_an_area(act_start_x, act_start_y, over_x, over_y);
        if (pm_over != 0 && pm_over != old_pm_over) setup_map_screen_refresh();
        if ((cycle_count & 7) == 0) setup_map_screen_refresh();
    }
    if (placing_type == 0x6) {  /* Gardens */
        restore_city_from_undo_buffer();
        if (hot_key_out_off_build == 0) garden_an_area(act_start_x, act_start_y, over_x, over_y);
        if (pm_over != 0 && pm_over != old_pm_over) setup_map_screen_refresh();
    }
    if (placing_type == 0x7) {  /* Plaza */
        restore_city_from_undo_buffer();
        if (hot_key_out_off_build == 0) plaza_an_area(act_start_x, act_start_y, over_x, over_y);
        if (pm_over != 0 && pm_over != old_pm_over) setup_map_screen_refresh();
    }

    /* Houses (house1..house5): shape+sprite from the placing_type*4 table at +0x4D3B. */
    if (placing_type >= 0x82 && placing_type <= 0xa1) {
        restore_city_from_undo_buffer();
        building_type = placing_type;
        house_gfx = house_gfxdat[building_type * 4 - 0x208];
        shape = house_gfxdat[building_type * 4 - 0x207];
        tgfx_b = house_gfxdat[building_type * 4 - 0x206];
        if (hot_key_out_off_build == 0) {
            if (shape == 3) put_x3_area(over_x, over_y, building_type, tgfx_b, house_gfx);
            else if (shape == 2) put_x2_area(over_x, over_y, building_type, tgfx_b, house_gfx);
            else build_an_area(act_start_x, act_start_y, over_x, over_y, building_type, tgfx_b, house_gfx);
        }
    }

    /* Forums (small/medium/large): shape+sprite from the placing_type*4 table at +0x4D0B. */
    if (placing_type >= 0xae && placing_type <= 0xb9) {
        restore_city_from_undo_buffer();
        building_type = placing_type;
        building_gfx = forum_gfxdat[building_type * 4 - 0x2b8];
        shape = forum_gfxdat[building_type * 4 - 0x2b7];
        tgfx_b = forum_gfxdat[building_type * 4 - 0x2b6];
        if (hot_key_out_off_build == 0) {
            if (shape == 2) put_x2_area(over_x, over_y, building_type, tgfx_b, building_gfx);
            else if (shape == 3) put_x3_area(over_x, over_y, building_type, tgfx_b, building_gfx);
            else if (shape == 4) put_x4_area(over_x, over_y, building_type, tgfx_b, building_gfx);
        }
    }

    if (placing_type == 0xa) {  /* Baths */
        restore_city_from_undo_buffer();
        has_cover = affected_by_cover1(CM_CELL(pm_over_cm_ptr).b, 2, 4);
        if (has_cover != 0) building_gfx = 0x20;
        else building_gfx = 99;
        if (hot_key_out_off_build == 0) {
            put_x2_area(over_x, over_y, 0xdf, 8, building_gfx);
            CM_CELL(start_sptr).building = 0x0f;
        }
    }
    if (placing_type == 0xb) {  /* Hospital */
        restore_city_from_undo_buffer();
        if (hot_key_out_off_build == 0) put_x3_area(over_x, over_y, 0xfb, 8, 0x56);
    }
    if (placing_type == 0xe) {  /* Prefecture */
        restore_city_from_undo_buffer();
        if (hot_key_out_off_build == 0) {
            put_x1_area(over_x, over_y, 0xe3, 0, 0x50);
            CM_CELL(start_sptr).edge_bits |= 0x80;
        }
    }
    if (placing_type == 0xd) {  /* Barracks */
        restore_city_from_undo_buffer();
        if (hot_key_out_off_build == 0) put_x3_area(over_x, over_y, 0xe4, 0, 0x51);
    }
    if (placing_type == 0x10) {
        restore_city_from_undo_buffer();
        if (hot_key_out_off_build == 0) {
            if (put_x3_area(over_x, over_y, 0xfa, 0xc, 0x3e) != 0) {
                CM_CELL(start_sptr).edge_bits  |= 0x80;
                CM_CELL(start_sptr).business &= 0xf0;
                CM_CELL(start_sptr).business |= (unsigned char)business_build_type;
                CM_CELL(start_sptr + CITY_CELL_BYTES).edge_bits |= 0x80;
            }
        }
    }
    if (placing_type == 0xf) {  /* Market */
        restore_city_from_undo_buffer();
        if (hot_key_out_off_build == 0) put_x2_area(over_x, over_y, 0xfc, 8, 0x30);
    }
    if (placing_type == 0x11) {  /* Grammaticus (school) */
        restore_city_from_undo_buffer();
        if (hot_key_out_off_build == 0) put_x2_area(over_x, over_y, 0xf3, 8, 0x40);
    }
    if (placing_type == 0x12) {  /* Rhetor (academy) */
        restore_city_from_undo_buffer();
        if (hot_key_out_off_build == 0) put_x3_area(over_x, over_y, 0xf4, 8, 0x44);
    }
    if (placing_type == 0x13) {  /* Library */
        restore_city_from_undo_buffer();
        if (hot_key_out_off_build == 0) put_x3_area(over_x, over_y, 0xf5, 8, 0x4d);
    }
    if (placing_type == 0x14) {  /* Small temple */
        restore_city_from_undo_buffer();
        if (hot_key_out_off_build == 0) put_x1_area(over_x, over_y, 0xa2, 0, 0x3c);
    }
    if (placing_type == 0x15) {  /* Medium temple */
        restore_city_from_undo_buffer();
        if (hot_key_out_off_build == 0) put_x2_area(over_x, over_y, 0xa6, 0, 0x40);
    }
    if (placing_type == 0x16) {  /* Large temple */
        restore_city_from_undo_buffer();
        if (hot_key_out_off_build == 0) put_x3_area(over_x, over_y, 0xaa, 0xc, 0);
    }
    if (placing_type == 0x17) {  /* Theatre */
        restore_city_from_undo_buffer();
        if (hot_key_out_off_build == 0) put_x2_area(over_x, over_y, 0xe5, 0xc, 0x24);
    }
    if (placing_type == 0x18) {  /* Odeum */
        restore_city_from_undo_buffer();
        if (hot_key_out_off_build == 0) put_x2_area(over_x, over_y, 0xe6, 0xc, 0x28);
    }
    if (placing_type == 0x19) {  /* Arena */
        restore_city_from_undo_buffer();
        if (hot_key_out_off_build == 0) {
            put_x3_area(over_x, over_y, 0xe7, 0xc, 0x2c);
            CM_CELL(start_sptr).edge_bits |= 0x80;
        }
    }
    if (placing_type == 0x1a) {  /* Colosseum */
        restore_city_from_undo_buffer();
        if (hot_key_out_off_build == 0) {
            put_x3_area(over_x, over_y, 0xe8, 0xc, 0x35);
            CM_CELL(start_sptr).edge_bits |= 0x80;
        }
    }

    if (placing_type == 0x1b) {
        /* Circus: two 3x3 tiles, orientation chosen from map_direction. */
        restore_city_from_undo_buffer();
        if (map_direction == 0) { gfx_a = 0xe9; gfx_b = 0xea; gfx_a_idx = 0; gfx_b_idx = 9; dx = 0; dy = 3; }
        else if (map_direction == 4) { gfx_a = 0xe9; gfx_b = 0xea; gfx_a_idx = 9; gfx_b_idx = 0; dx = 0; dy = -3; }
        else if (map_direction == 2) { gfx_a = 0xeb; gfx_b = 0xec; gfx_a_idx = 0x3b; gfx_b_idx = 0x32; dx = -3; dy = 0; }
        else if (map_direction == 6) { gfx_a = 0xeb; gfx_b = 0xec; gfx_a_idx = 0x32; gfx_b_idx = 0x3b; dx = 3; dy = 0; }
        if (hot_key_out_off_build == 0) {
            ok = 1;
            if (put_x3_area(over_x, over_y, gfx_a, 0x14, gfx_a_idx) == 0) ok = 0;
            if (put_x3_area(over_x + dx, over_y + dy, gfx_b, 0x14, gfx_b_idx) == 0) ok = 0;
            if (ok == 0) { restore_city_from_undo_buffer(); particles_built = 0; }
            else particles_built = 1;
            set_map_ref(over_x, over_y, 3);
            set_map_ref(over_x + dx, over_y + dy, 3);
        }
    }

    if (placing_type == 0x1c) {
        /* Circus Maximus: two 4x4 tiles, orientation from map_direction. */
        restore_city_from_undo_buffer();
        if (map_direction == 0) { gfx_a = 0xed; gfx_b = 0xee; gfx_a_idx = 0x12; gfx_b_idx = 0x22; dx = 0; dy = 4; }
        else if (map_direction == 4) { gfx_a = 0xed; gfx_b = 0xee; gfx_a_idx = 0x22; gfx_b_idx = 0x12; dx = 0; dy = -4; }
        else if (map_direction == 2) { gfx_a = 0xef; gfx_b = 0xf0; gfx_a_idx = 0x54; gfx_b_idx = 0x44; dx = -4; dy = 0; }
        else if (map_direction == 6) { gfx_a = 0xef; gfx_b = 0xf0; gfx_a_idx = 0x44; gfx_b_idx = 0x54; dx = 4; dy = 0; }
        if (hot_key_out_off_build == 0) {
            ok = 1;
            if (put_x4_area(over_x, over_y, gfx_a, 0x14, gfx_a_idx) == 0) ok = 0;
            if (put_x4_area(over_x + dx, over_y + dy, gfx_b, 0x14, gfx_b_idx) == 0) ok = 0;
            if (ok == 0) { restore_city_from_undo_buffer(); particles_built = 0; }
            else particles_built = 1;
            set_map_ref(over_x, over_y, 4);
            set_map_ref(over_x + dx, over_y + dy, 4);
        }
    }

    if (placing_type == 0xbf) {  /* Tower */
        restore_city_from_undo_buffer();
        building_type = placing_type;
        if (hot_key_out_off_build == 0) {
            CM_CELL(pm_over_cm_ptr).terrain &= 0xfd;
            if (put_x1_area(over_x, over_y, building_type, 8, 0x94) == 0) {
                restore_city_from_undo_buffer();
            }
            if (wall_ramifications(over_x, over_y) == 0) {
                restore_city_from_undo_buffer();
            }
        }
    }

    if (placing_type == 0xbe) {  /* Reservoir */
        restore_city_from_undo_buffer();
        building_type = placing_type;
        if (hot_key_out_off_build == 0) {
            CM_CELL(pm_over_cm_ptr).terrain &= 0xbf;
            if (put_x1_area(over_x, over_y, building_type, 0, 0x5a) == 0) {
                restore_city_from_undo_buffer();
            }
            if (aquaduct_ramifications(over_x, over_y) == 0) {
                restore_city_from_undo_buffer();
            }
        }
        evolve_row = 0; evolve_water_supply_baths_industry(0x50);
    }

    if (placing_type == 0x8) {  /* Well */
        restore_city_from_undo_buffer();
        if (hot_key_out_off_build == 0) {
            if (put_x1_area(over_x, over_y, 0xd7, 8, 0x10) == 0) {
                restore_city_from_undo_buffer();
            }
        }
    }

    if (placing_type == 0xc) {  /* Fountain */
        restore_city_from_undo_buffer();
        building_type = 0xdb;
        fountain_gfx = fountain_gfxdat[building_type - 0xdb];
        if ((CM_CELL(pm_over_cm_ptr).education & 4) != 0) fountain_gfx++;
        if (hot_key_out_off_build == 0) {
            if (put_x1_area(over_x, over_y, building_type, 8, fountain_gfx) == 0) {
                restore_city_from_undo_buffer();
            } else { CM_CELL(pm_over_cm_ptr).building = 0x0f; }
        }
    }

after_clear:
    total_build_cost = particles_cleared * city_costs[1];
    total_build_cost = total_build_cost + particles_built * placing_cost;
    denarii = denarii - total_build_cost;
    update_map = 2;
    return;
}

// FUNCTION: C2 0x30EBF
// WIN: 0x004b3568
// Lines 1010–1022
//
// Region-map twin of `prebuild_city_item`.  Snapshots cursor and
// denarii, then dispatches to the appropriate elastic-preview helper
// for the active reg_placing_type.
void prebuild_region_item(void)
{
    act_start_pm_ptr = pm_over_cm_ptr;
    act_start_ptr = pm_over_cm_ptr / map_actual_atom;
    act_start_x = act_start_ptr % map_actual_width;
    act_start_y = act_start_ptr / map_actual_width;

    hot_key_out_off_build = 0;
    starting_denarii = denarii;

    if (reg_placing_type == 0x1e) {
        get_reg_road_elastic();
    } else if (reg_placing_type == 0x1f) {
        get_reg_wall_elastic();
    }
}

// FUNCTION: C2 0x30F3A
// WIN: 0x004b35f0
// Lines 1024–1233
//
// Region-map twin of `build_city_item`.  Long if-chain on
// `reg_placing_type` for road/wall/clear and the various industry
// (farm, mine, quarry, port, …) and fortress placements.  After a
// successful fortress placement (type 0x22) it calls `create_army`
// to spawn a 2-cohort fortress garrison.  Costs are accumulated
// into `total_build_cost` from `region_costs[+0x4]` per particle
// cleared and `placing_cost` per particle built.
void build_region_item(void)
{


    (*(struct region_cell *)((unsigned char *)region_map + (pm_over_cm_ptr))).edge_bits |= 1;
    illegal_build = 2;

    if (slave_requirements[0].current < slave_requirements[0].max) {
        if (warned_of_not_build != 0) {
            return;
        }
        warned_of_not_build = 1;
        put_message(0x65, 0, 0);
        return;
    }

    denarii = starting_denarii;
    particles_built = 0;
    particles_cleared = 0;
    industry_build_on = 0;

    if (reg_placing_type == 0x1e) {
        /* Region road. */
        restore_region_from_undo_buffer();
        if (hot_key_out_off_build == 0) {
            build_reg_road_from_elastic();
        }
        if (pm_over != 0 && old_pm_over != pm_over) {
            setup_map_screen_refresh();
        }
    }

    if (reg_placing_type == 0x1f) {
        /* Region wall. */
        restore_region_from_undo_buffer();
        if (at_edge_of_map(over_x, over_y) != 0) {
            illegal_build = 1;
        } else if (at_edge_of_map(act_start_x, act_start_y) != 0) {
            illegal_build = 1;
        } else if (hot_key_out_off_build == 0) {
            build_reg_wall_from_elastic();
        }
        if (pm_over != 0 && old_pm_over != pm_over) {
            setup_map_screen_refresh();
        }
    }

    if (reg_placing_type == 0x21) {
        /* Clear region area. */
        restore_region_from_undo_buffer();
        if (hot_key_out_off_build == 0) {
            clear_a_reg_area(act_start_x, act_start_y,
                             over_x, over_y, 0);
        }
        if (pm_over != 0 && old_pm_over != pm_over) {
            setup_map_screen_refresh();
        }
    }

    if (reg_placing_type == 0x23) {
        /* Workhouse */
        restore_region_from_undo_buffer();
        if (at_edge_of_map(over_x, over_y) != 0) {
            illegal_build = 1;
        } else if (hot_key_out_off_build == 0) {
            if (get_reg_industries_in_radius(over_x, over_y) == 0) {
                restore_region_from_undo_buffer();
                illegal_build = 1;
            } else if (put_reg_x1_area(over_x, over_y, 0xd3, 0,
                                        0x3c, 0) == 0) {
                restore_region_from_undo_buffer();
                illegal_build = 1;
            }
        }
    }

    if (reg_placing_type == 0x24) {
        /* Warehouse */
        restore_region_from_undo_buffer();
        if (at_edge_of_map(over_x, over_y) != 0) {
            illegal_build = 1;
        } else if (hot_key_out_off_build == 0) {
            if (get_reg_industries_in_radius(over_x, over_y) == 0) {
                restore_region_from_undo_buffer();
                illegal_build = 1;
            } else if (put_reg_x1_area(over_x, over_y, 0xd4, 0,
                                        0x0b, 0) == 0) {
                restore_region_from_undo_buffer();
                illegal_build = 1;
            }
        }
    }

    if (reg_placing_type == 0x2a) {
        /* Bridge */
        restore_region_from_undo_buffer();
        if (at_edge_of_map(over_x, over_y) != 0) {
            illegal_build = 1;
        } else if (hot_key_out_off_build == 0
                && put_reg_x2_area(over_x, over_y, 0xd5, 0,
                                    0x46, 0) == 0) {
            restore_region_from_undo_buffer();
            illegal_build = 1;
        }
    }

    if (reg_placing_type == 0x25) {
        /* Farm */
        industry_build_on = 1;
        restore_region_from_undo_buffer();
        check_region_map_for_farm_square(over_x, over_y, 0x80);
        if (at_edge_of_map(over_x, over_y) != 0) {
            illegal_build = 1;
        } else if (hot_key_out_off_build == 0) {
            if (put_reg_x2_area(over_x, over_y, 0xdc, 8,
                                0x30, 1) == 0) {
                illegal_build = 1;
                restore_region_from_undo_buffer();
                industry_build_ok = 0;
                industry_build_on = 0;
            }
        }
    }

    if (reg_placing_type == 0x26) {
        /* Mine */
        industry_build_on = 1;
        restore_region_from_undo_buffer();
        check_region_map_for_farm_square(over_x, over_y, 0x40);
        if (at_edge_of_map(over_x, over_y) != 0) {
            illegal_build = 1;
        } else if (hot_key_out_off_build == 0) {
            if (put_reg_x2_area(over_x, over_y, 0xe0, 8,
                                0x40, 1) == 0) {
                illegal_build = 1;
                restore_region_from_undo_buffer();
                industry_build_ok = 0;
                industry_build_on = 0;
            }
        }
    }

    if (reg_placing_type == 0x27) {
        /* Quarry */
        industry_build_on = 1;
        restore_region_from_undo_buffer();
        check_region_map_for_farm_square(over_x, over_y, 0x40);
        if (at_edge_of_map(over_x, over_y) != 0) {
            illegal_build = 1;
        } else if (hot_key_out_off_build == 0) {
            if (put_reg_x2_area(over_x, over_y, 0xe4, 8,
                                0x20, 1) == 0) {
                illegal_build = 1;
                restore_region_from_undo_buffer();
                industry_build_ok = 0;
                industry_build_on = 0;
            }
        }
    }

    if (reg_placing_type == 0x29) {
        /* Logging camp */
        industry_build_on = 1;
        restore_region_from_undo_buffer();
        if (at_edge_of_map(over_x, over_y) != 0) {
            illegal_build = 1;
        } else if (hot_key_out_off_build == 0) {
            if (put_reg_x2_area(over_x, over_y, 0xe8, 8,
                                0x60, 1) == 0) {
                illegal_build = 1;
                restore_region_from_undo_buffer();
                industry_build_ok = 0;
                industry_build_on = 0;
            }
        }
    }

    if (reg_placing_type == 0x28) {
        /* Port */
        industry_build_on = 1;
        restore_region_from_undo_buffer();
        check_region_map_for_port_square(over_x, over_y);
        if (at_edge_of_map(over_x, over_y) != 0) {
            illegal_build = 1;
        } else if (hot_key_out_off_build == 0) {
            if (put_reg_x2_area(over_x, over_y, 0xec, 8,
                                0x50, 2) == 0) {
                illegal_build = 1;
                restore_region_from_undo_buffer();
                industry_build_ok = 0;
                industry_build_on = 0;
            } else if (industry_build_ok == 0) {
                flag_rm_area(over_x, over_y, 2, 8);
                adjust_regions_coastline(start_x_pos - 1,
                                         start_y_pos - 1, 4, 4);
            }
        }
    }

    if (reg_placing_type == 0x22) {
        /* Fortress */
        restore_region_from_undo_buffer();
        if (at_edge_of_map(over_x, over_y) != 0) {
            illegal_build = 1;
        } else if (hot_key_out_off_build == 0) {
            get_cohorts_in_action();
            (*(struct region_cell *)((unsigned char *)region_map + (pm_over_cm_ptr))).terrain &= 0xfd;
            if (put_reg_x1_area(over_x, over_y, 0xd2, 0, 0x46, 1) == 0) {
                restore_region_from_undo_buffer();
                illegal_build = 1;
            } else if (reg_wall_ramifications(over_x, over_y) == 0) {
                restore_region_from_undo_buffer();
                illegal_build = 1;
            } else if (no_of_cohorts_in_action >= 0xa) {
                restore_region_from_undo_buffer();
                if (warned_of_not_build == 0) {
                    warned_of_not_build = 1;
                    put_message(0x5a, 0, 0);
                }
            } else if (create_army(1, over_x, over_y, 0) != 0) {
                int new_no = created_army_no;
                army_list[new_no].state_idx = 1;
                army_list[new_no].saved_state_idx = 1;
                army_list[new_no].exists = 2;
                army_list[new_no].cohort_id = next_cohort_free;
                army_list[new_no].departure_year = year;
                army_list[new_no].morale_timer = 2;
            }
        } else {
            restore_region_from_undo_buffer();
        }
    }

    total_build_cost = particles_cleared * region_costs[1];
    total_build_cost = total_build_cost + particles_built * placing_cost;
    denarii -= total_build_cost;
}

// FUNCTION: C2 0x31645
// WIN: 0x004b3fd6
// Lines 1235–1242
//
// Used by the farm-type-selection box: stamp `para1<<4` into the
// upper nibble of the cell's `(*(struct region_cell *)((unsigned char *)region_map + (+7))).base_kind` byte at the start of
// the selected 2x2 farm.
void act_select_farm(void)
{
    int off = get_region_2x2_start(pm_over_cm_ptr);
    (*(struct region_cell *)((unsigned char *)region_map + (off))).occupant &= 0x0f;
    para1 <<= 4;
    (*(struct region_cell *)((unsigned char *)region_map + (off))).occupant |= (unsigned char)para1;
}

// FUNCTION: C2 0x3166C
// WIN: 0x004b402d
// Lines 1244–1251
//
// Given a cm-byte pointer somewhere inside a 2x2 farm/mine/etc., walk
// back to the byte pointer of its top-left cell.  The 2x2 origin
// index is stored in the low 2 bits of (*(struct region_cell *)((unsigned char *)region_map + (+7))).base_kind of the cell.
//
// Special case: if the cell is region terrain 0xd4 ("port quay"),
// the offsets are zero so the call is a no-op.
//
// Returns the new cm-byte pointer (offset from region_map base).
int get_region_2x2_start(int cm_ptr)
{
    int row;
    int col;
    int divisor;

    if ((*(struct region_cell *)((unsigned char *)region_map + (cm_ptr))).base_kind == 0xd4) {
        row = 0;
        col = 0;
    } else {
        row = (*(struct region_cell *)((unsigned char *)region_map + (cm_ptr))).occupant & 3;
        col = row;
    }

    divisor = 2;
    col = col % divisor;
    row = row / divisor;
    cm_ptr = cm_ptr - col * 8;
    cm_ptr = cm_ptr - row * 480;
    return cm_ptr;
}

// FUNCTION: C2 0x316CD
// WIN: 0x004b40c5
// Lines 1256–1298
//
// Determine which icon (if any) is under the mouse pointer.  Sets
// `last_icon_over` to:
//   0      — none
//   1      — mouse is in the top status bar
//   2      — mouse is over the command/menu strip
//   4..27  — index into city or region icon header
//
// City icons are int_city_header[i*16 .. i*16 + 5] (4 shorts):
//   +8  x, +0xA y, +0x10 width, +0x12 height
// Region icons use int_region_header with the same layout.
void get_icon_over(void)
{
    int bot;
    int i;
    short x;
    short y;
    short w;
    short h;

    last_icon_over = 0;

    if (mouse_y < 0x18) {
        last_icon_over = 1;
        return;
    }

    if (mouse_x >= com_x && (com_x + com_w) > mouse_x) {
        bot = com_y + com_h;
        if (map_mode == 0) {
            if (com_y - 0x18 <= mouse_y && bot > mouse_y) {
                last_icon_over = 2;
                return;
            }
        } else {
            if (mouse_y >= com_y && mouse_y < bot) {
                last_icon_over = 2;
                return;
            }
        }
    }

    if (mouse_x < 0x1e0) {
        return;
    }

    if (map_mode == 0) {
        for (i = 4; i < 0x1c; i++) {
            if (tutorial_mode == 0 || city_icon_allowed(i - 4) != 0) {
                w = int_city_header[i * 8 + 4];
                h = int_city_header[i * 8 + 5];
                x = int_city_header[i * 8 + 8] + 0xee;
                y = int_city_header[i * 8 + 9];
                if (mouse_in_area((unsigned short)x, (unsigned short)y,
                                  (unsigned short)w, (unsigned short)h) != 0) {
                    last_icon_over = i;
                    return;
                }
            }
        }
    } else {
        for (i = 4; i < 0x17; i++) {
            if (tutorial_mode == 0 || region_icon_allowed(i - 4) != 0) {
                w = int_region_header[i * 8 + 4];
                h = int_region_header[i * 8 + 5];
                x = int_region_header[i * 8 + 8] + 0xee;
                y = int_region_header[i * 8 + 9];
                if (mouse_in_area((unsigned short)x, (unsigned short)y,
                                  (unsigned short)w, (unsigned short)h) != 0) {
                    last_icon_over = i;
                    return;
                }
            }
        }
    }
}

// FUNCTION: C2 0x31850
// WIN: 0x004b437f
// Lines 1300–1323
//
// "Is the cursor over icon `idx`?".  Returns 1 if the mouse is in
// the icon's box (or if `idx==2`, which always returns 1 — the
// command-strip area is special-cased by the caller).  Otherwise 0.
int is_icon_over(int idx)
{
    short x;
    short y;
    short w;
    short h;

    if (mouse_x < 0x1e0) {
        return 0;
    }

    if (map_mode == 0) {
        w = int_city_header[idx * 8 + 4];
        h = int_city_header[idx * 8 + 5];
        x = int_city_header[idx * 8 + 8] + 0xee;
        y = int_city_header[idx * 8 + 9];
    } else {
        w = int_region_header[idx * 8 + 4];
        h = int_region_header[idx * 8 + 5];
        x = int_region_header[idx * 8 + 8] + 0xee;
        y = int_region_header[idx * 8 + 9];
    }

    if (mouse_in_area((unsigned short)x, (unsigned short)y,
                      (unsigned short)w, (unsigned short)h) != 0) {
        return 1;
    }
    if (idx == 2) {
        return 1;
    }
    return 0;
}

// FUNCTION: C2 0x318ED
// WIN: 0x004b44b1
// Lines 1325–1342
//
// On a left-click while the cursor is on the overview-map strip,
// either pop the legend / select-map dialogue or — if the click is
// on the map proper — re-centre the city view on that point.
// Returns 1 if the click was consumed (and the view jumped), 0
// otherwise.
int use_city_overmap_to_move(void)
{
    int dx;
    int dy;
    int ptr;

    if (mouse_left_preclick == 0) {
        return 0;
    }
    if (last_icon_over != 2) {
        return 0;
    }

    if (mouse_y < com_y && (com_y - 0x18) <= mouse_y) {
        if (mouse_x >= 0x25c) {
            act_show_ov_legend();
        } else {
            act_select_ov_map();
        }
        return 0;
    }

    dx = (mouse_x - com_x) / 2;
    dy = (mouse_y - com_y) / 4 * 2;
    ptr = (dy * map_actual_width + dx) * map_actual_atom;
    if (jump_to_citymap_ptr(ptr) != 0) {
        return 1;
    }
    return 0;
}

// FUNCTION: C2 0x31997
// WIN: 0x004b459d
// Lines 1344–1355
//
// Region-map twin of `use_city_overmap_to_move`: convert mouse
// coordinates over the command strip into a region cell pointer
// and call `jump_to_regionmap_ptr`.  Returns 1 on consumed click.
int use_region_overmap_to_move(void)
{
    int dx;
    int dy;
    int ptr;

    if (mouse_left_preclick == 0) {
        return 0;
    }
    if (last_icon_over != 2) {
        return 0;
    }

    dx = (mouse_x - com_x) / 2;
    dy = (mouse_y - com_y) / 4 * 2;
    ptr = (dy * map_actual_width + dx) * map_actual_atom;
    if (jump_to_regionmap_ptr(ptr) != 0) {
        return 1;
    }
    return 0;
}

// FUNCTION: C2 0x31A0A
// WIN: 0x004b463e
// Lines 1357–1384
//
// Re-centre the city view on the cell whose pseudo_map[] entry
// matches `target_ptr`.  If we're currently on the region map
// (map_mode==1), first restore the saved city rotation/zoom and
// switch back to the city map (map_mode=0).  Sets pm_x/pm_y to the
// 161x81 grid square that contains the target cell, kicks off a
// rescroll, and returns 1 if a switch happened, 2 on a normal jump,
// or 0 if no matching cell was found.
int jump_to_citymap_ptr(int target_ptr)
{
    int y;
    int x;
    int switched = 0;

    if (map_mode != 0) {
        prov_rotation = map_direction;
        prov_zoom_level = zoom_level;
        map_direction = city_rotation;
        zoom_level = city_zoom_level;
        map_mode = 0;
        act_correct_map();
        switched = 1;
    }

    /* Linear search of pseudo_map for the target cell pointer. */
    for (y = 0; y < 0xa1; y++) {
        for (x = 0; x < 0x51; x++) {
            if (pseudo_map[y][x] == target_ptr) {
                goto found;
            }
        }
    }
    return 0;
found:
    pm_x = x;
    pm_y = y & 0xfffe;
    if (zoom_level == 0) {
        pm_x += -4;
        pm_y += -0xc;
    } else if (zoom_level == 1) {
        pm_x += -8;
        pm_y += -0x1e;
    } else if (zoom_level == 2) {
        pm_x += -0x14;
        pm_y += -0x46;
    }
    pm_limits();
    scrolling = 1;
    update_map = 1;
    if (switched) {
        return 1;
    }
    return 2;
}

// FUNCTION: C2 0x31B1B
// WIN: 0x004b47ba
// Lines 1386–1406
//
// Region-map twin of `jump_to_citymap_ptr`.  If we're on the city
// map, save city rotation/zoom and switch to the region view; then
// linear-search pseudo_map for `target_ptr` and jump to it.
// Returns 1 on switch, 2 on plain jump, 0 if not found.
int jump_to_regionmap_ptr(int target_ptr)
{
    int x;
    int y;
    int switched = 0;

    if (map_mode != 1) {
        city_rotation = map_direction;
        city_zoom_level = zoom_level;
        map_direction = prov_rotation;
        zoom_level = prov_zoom_level;
        map_mode = 1;
        act_correct_map();
        switched = 1;
    }

    for (y = 0; y < 0xa1; y++) {
        for (x = 0; x < 0x51; x++) {
            if (pseudo_map[y][x] == target_ptr) {
                goto found;
            }
        }
    }
    return 0;
found:
    pm_x = x;
    pm_y = y & 0xfffe;
    if (zoom_level == 0) {
        pm_x += -4;
        pm_y += -0xc;
    } else if (zoom_level == 1) {
        pm_x += -8;
        pm_y += -0x1e;
    } else if (zoom_level == 2) {
        pm_x += -0x14;
        pm_y += -0x46;
    }
    pm_limits();
    scrolling = 1;
    update_map = 1;
    if (switched) {
        return 1;
    }
    return 2;
}

// FUNCTION: C2 0x31BD9
// WIN: 0x004b4937
// Lines 1415–1428
//
// Dispatch a click on icon `last_icon_over` (in city mode).  Each
// non-trivial icon (>=4) calls into `rome2_buttons[icon_idx]`, a
// table of function pointers (offset 0x3A in rome2_buttons array,
// i.e. starts at icon 4).  Resets the strip toggle to 0x1f and
// remembers the icon used (except for icons 0xe..0x11).
int perform_city_strip_action(void)
{
    int zero;

    if (mouse_left_preclick == 0) {
        return 0;
    }
    if (last_icon_over < 4) {
        return 0;
    }

    zero = 0;
    selected_icon_no   = zero;
    selected_icon_text = zero;
    icon_strip_toggle  = 0x1f;

    ((void (**)(void))((char *)rome2_buttons + 0x3a))[last_icon_over]();

    if (last_icon_over >= 0xe && last_icon_over != 0x12) {
        last_icon_used = last_icon_over;
        update_icon    = last_icon_over;
    }
    return 1;
}

// FUNCTION: C2 0x31C3C
// WIN: 0x004b49d3
// Lines 1430–1443
//
// Region-mode dispatch for icon-strip clicks.  Mirrors
// `perform_city_strip_action` but indexes into `city_actions+0x50`
// instead.  (The dispatch table is shared between city and region
// modes; the +0x50 offset selects the region-mode entry.)
int perform_region_strip_action(void)
{
    int zero;

    if (mouse_left_preclick == 0) {
        return 0;
    }
    if (last_icon_over < 4) {
        return 0;
    }

    zero = 0;
    selected_icon_no   = zero;
    selected_icon_text = zero;
    icon_strip_toggle  = 0x1f;

    ((void (**)(void))((char *)city_actions + 0x50))[last_icon_over]();

    if (last_icon_over >= 0xe && last_icon_over != 0x12) {
        last_icon_used = last_icon_over;
        update_icon    = last_icon_over;
    }
    return 1;
}

// FUNCTION: C2 0x31C9E
//
// No-op slot used as a placeholder in the icon-action dispatch tables.
void act_null(void)
{
}

// FUNCTION: C2 0x31C9F
// WIN: 0x004b4a6f
// Lines 1445–1470
//
// Find which battle-screen icon (4..0x14) the cursor is in and, on
// a left-click, dispatch via `region_actions+0x3C`.  Sets
// `last_icon_over` to the matched icon and `last_icon_used` if
// idx>=9.  Returns 1 on consumed click, 0 otherwise.
int perform_battle_strip_action(void)
{
    int i;
    short x;
    short y;
    short w;
    short h;

    last_icon_over = 0;
    if (mouse_y < 0x168) {
        return 0;
    }

    for (i = 4; i < 0x15; i++) {
        w = int_battle_header[i * 8 + 4];
        h = int_battle_header[i * 8 + 5];
        x = int_battle_header[i * 8 + 8];
        y = int_battle_header[i * 8 + 9] + 0xc8;
        if (mouse_in_area((unsigned short)x, (unsigned short)y,
                          (unsigned short)w, (unsigned short)h) != 0) {
            last_icon_over = i;
            if (mouse_left_preclick == 0) {
                return 0;
            }
            region_actions[0xf + i]();
            update_icon = i;
            if (i >= 9) {
                last_icon_used = i;
            }
            return 1;
        }
    }
    return 0;
}

// FUNCTION: C2 0x31D46
// WIN: 0x004b4b98
// Lines 1472–1480
//
// Dispatch a click on the floating cohort-control box (patrol /
// return-home / patrol-stop buttons) shown when an army is being
// tracked.  Returns 1 if the click was consumed (and the box was
// dismissed), 0 otherwise.
int perform_cohort_box_action(void)
{
    int idx;
    int h;

    if (exit_screen() != 0) {
        pointer_mode = 0;
        update_map = 1;
        setup_map_screen_refresh();
        return 1;
    }
    idx = tracking_army * 0xaf;
    if (army_list[tracking_army].type != 1) {
        return 0;
    }

    control_buttons(0x190, 0x82, cohort_buttons, 1);
    if (mouse_left_preclick == 0) {
        return 0;
    }

    /* Three 34x34 buttons at the bottom of the cohort box. */
    h = 0x22;
    if (mouse_in_area(0x28, 0x126, h, h) != 0) {
        act_set_patrol_markers();
        return 1;
    }
    if (mouse_in_area(0xb8, 0x126, h, h) != 0) {
        act_set_return_home();
        return 1;
    }
    if (mouse_in_area(0x148, 0x126, h, h) != 0) {
        act_set_patrol_stop();
        return 1;
    }
    return 0;
}

// FUNCTION: C2 0x31E1A
// WIN: 0x004b4cb6
// Lines 1488–1494
//
// Enter turbo mode (fast-forward).  Disabled on the battle screen.
void act_init_turbo_mode(void)
{
    if (map_mode != 2) {
        turbo_mode   = 1;
        pointer_mode = 0;
        setup_whole_screen_refresh();
        update_map = 1;
    }
}

// FUNCTION: C2 0x31E45
// WIN: 0x004b4cee
// Lines 1496–1501
//
// Leave turbo mode and request a full-screen repaint.
void act_exit_turbo_mode(void)
{
    turbo_mode = 0;
    setup_whole_screen_refresh();
    update_map = 1;
}

// FUNCTION: C2 0x31E5C
// WIN: 0x004b4d0a
// Lines 1503–1513
//
// "New Game" menu action.  In tutorial / demo mode just shows a
// warning; otherwise asks the user to confirm and, if accepted,
// sets `restart_flag` so the main loop tears the game down.
// In battle mode (map_mode==2) it also sets `battle_state = 10`.
void act_new_game(void)
{
    if (tutorial_mode != 0) {
        click_warning(2, 0x50, 0xa0);
        return;
    }
    if (demo_mode != 0) {
        click_warning(6, 0x50, 0xa0);
        return;
    }
    confirm(1, 0xa0, 0xa0);
    if (decision == 1) {
        restart_flag = 1;
        pre_loaded_status = 0;
        if (map_mode == 2) {
            battle_state = 0xa;
        }
    }
}

// FUNCTION: C2 0x31EDD
// WIN: 0x004b4da7
// Lines 1514–1522
//
// "Load Game" menu action.  In tutorial / demo mode shows a
// warning; otherwise calls `load_a_game()`.  Afterwards, if we
// were in battle mode (the captured `map_mode == 2`), advance the
// battle state machine to 10.
void act_load_game(void)
{
    int saved_map_mode = map_mode;
    if (tutorial_mode != 0) {
        click_warning(2, 0x50, 0xa0);
        return;
    }
    if (demo_mode != 0) {
        click_warning(6, 0x50, 0xa0);
        return;
    }
    load_a_game();
    if (saved_map_mode == 2) {
        battle_state = 0xa;
    }
}

// FUNCTION: C2 0x31F38
// WIN: 0x004b4e1e
// Lines 1523–1529
//
// "Save Game" menu action.  Tutorial/demo: warning only.  Otherwise
// invoke `save_a_game()` and, if we're in battle mode, refresh the
// battle screen on return (since the save UI overlapped it).
void act_save_game(void)
{
    if (tutorial_mode != 0) {
        click_warning(2, 0x50, 0xa0);
        return;
    }
    if (demo_mode != 0) {
        click_warning(6, 0x50, 0xa0);
        return;
    }
    save_a_game();
    if (map_mode == 2) {
        battle_screen(0);
    }
}

// FUNCTION: C2 0x31F8F
// WIN: 0x004b4e8e
// Lines 1530–1542
//
// "Exit Game" menu action.  Tutorial mode: warning.  Otherwise pop
// the exit-confirmation modal and, if accepted, set `exit_flag` so
// the main loop unwinds.  Loops on `out1==0` because
// `show_exit_box` returns 0 while the modal is still active —
// each iteration calls `exit_game_loop` to pump messages.
void act_exit_game(void)
{
    if (tutorial_mode != 0) {
        click_warning(2, 0x50, 0xa0);
        return;
    }
    pointer_mode = 0;
    show_exit_box();
    out1 = 0;
    while (out1 == 0) {
        exit_game_loop();
    }

    if (decision == 1) {
        exit_flag = 1;
        if (map_mode == 2) {
            battle_state = 0xa;
        }
    }
    setup_map_screen_refresh();
    update_map = 1;
}

// FUNCTION: C2 0x3200D
// WIN: 0x004b4f21
// Lines 1544–1544
//
// Exit-confirmation modal: "yes" — commit the exit.
void act_do_exit(void)
{
    decision = 1;
    out1     = 1;
}

// FUNCTION: C2 0x3201F
// WIN: 0x004b4f3d
// Lines 1545–1545
//
// Exit-confirmation modal: save the game and dismiss.
void act_exit_and_save(void)
{
    save_a_game();
    out1 = 1;
}

// FUNCTION: C2 0x32026
// WIN: 0x004b4f57
// Lines 1546–1546
//
// Exit-confirmation modal: "no" — cancel the exit.
void act_dont_exit(void)
{
    decision = 0;
    out1     = 1;
}

// FUNCTION: C2 0x32030
// WIN: 0x004b4f73
// Lines 1548–1556
//
// Open the FX-options dialog (mode 0 = tunes), pumping
// `tune_game_loop` until the modal closes.  On exit refresh the
// whole screen and re-apply tune volume.
void act_toggle_tunes(void)
{
    int t = tutorial_mode;
    if (t != 0) {
        click_warning(2, 0x50, 0xa0);
        return;
    }
    show_fx_box(0);
    out1 = t;
    while (out1 == 0) {
        tune_game_loop();
    }
    setup_whole_screen_refresh();
    set_sequences_volume();
}

// FUNCTION: C2 0x3207D
// WIN: 0x004b4fd1
// Lines 1557–1567
//
// Toggle the "tunes enabled" bit (c2inf[+0xD] xor 1) and either
// stop the current tune (if now disabled) or start one of the
// two scene tunes (battle vs. peaceful), based on map_mode.
void act_tog_tunes(void)
{
    c2inf.tunes_on ^= 1;
    show_fx_box(0);
    if (c2inf.tunes_on == 0) {
        stop_tune();
        return;
    }
    if (map_mode == 2) {
        play_tune("batest2.xmi", 1);
    } else {
        play_tune("cityprov.xmi", 0);
    }
}

// FUNCTION: C2 0x320C2
// WIN: 0x004b5040
// Lines 1568–1572
//
// Adjust the music-volume slider in the FX dialog.  Hands the
// dialog back to `adjust()` (kind=3, target=&c2inf.tunes_level, step 1,
// max 0x64, min 0, x=0x70, y=0x90, no callback).  Refreshes
// volume and falls through to the screen-refresh tail-call shared
// with `act_sound_fx_level`.
void act_tunes_level(void)
{
    adjust(3, &c2inf.tunes_level, 1, 0x64, 0, 0x70, 0x90, 0);
    set_sequences_volume();
    out1 = 0;
    show_fx_box(0);
}

// FUNCTION: C2 0x320FD
// WIN: 0x004b5086
// Lines 1575–1583
//
// FX-options dialog (mode 1 = sound effects), looping until
// modal closes.  Refresh + reapply sample volume on exit.
void act_toggle_sound_fx(void)
{
    int t = tutorial_mode;
    if (t != 0) {
        click_warning(2, 0x50, 0xa0);
        return;
    }
    show_fx_box(1);
    out1 = t;
    while (out1 == 0) {
        samples_game_loop();
    }
    setup_whole_screen_refresh();
    set_samples_volume();
}

// FUNCTION: C2 0x3214D
// WIN: 0x004b50e4
// Lines 1584–1587
//
// Toggle the SFX-enabled flag and re-render the FX dialog.
void act_tog_samples(void)
{
    c2inf.samples_on ^= 1;
    show_fx_box(1);
    if (c2inf.samples_on == 0) stop_samples();
}

// FUNCTION: C2 0x3216C
// WIN: 0x004b511b
// Lines 1589–1592
//
// Toggle the ambient-sound flag and re-render the FX dialog.
void act_tog_ambients(void)
{
    c2inf.ambients_on ^= 1;
    show_fx_box(1);
    if (c2inf.ambients_on == 0) stop_all_sounds();
}

// FUNCTION: C2 0x3218B
// WIN: 0x004b5152
// Lines 1594–1597
//
// Toggle the speech-enabled flag and re-render the FX dialog.
void act_tog_speech(void)
{
    c2inf.speech_on ^= 1;
    show_fx_box(1);
    if (c2inf.speech_on == 0) stop_db();
}

// FUNCTION: C2 0x321AA
// WIN: 0x004b5189
// Lines 1599–1603
//
// Adjust the SFX volume slider; same template as
// `act_tunes_level`, refreshes sample volume and re-shows the FX
// box (mode 1) so the new value is rendered.
void act_samples_level(void)
{
    adjust(4, &c2inf.samples_level, 1, 0x64, 0, 0x70, 0x90, 0);
    set_samples_volume();
    out1 = 0;
    show_fx_box(1);
}

// FUNCTION: C2 0x321EC
// WIN: 0x004b51cf
// Lines 1606–1608
//
// Adjust the "number of simultaneous samples" slider in the FX
// dialog (entry 5: c2inf[+0x3C], step 1, 1..4, x=0x70, y=0x90, flag 2).
void act_nof_samples(void)
{
    adjust(5, &c2inf.max_samples, 1, 4, 1, 0x70, 0x90, 2);
    out1 = 0;
    show_fx_box(1);
}

// FUNCTION: C2 0x32215
// WIN: 0x004b5210
// Lines 1612–1620
//
// Toggle-animations dialog (mode 2 = anims).  Tutorial / demo
// blocked.  Loops until modal closes (out1 != 0), pumping
// `tog_anims_game_loop`.  Refresh whole screen on exit.
void act_toggle_anims(void)
{
    int t = tutorial_mode;
    if (t != 0) {
        click_warning(2, 0x50, 0xa0);
        return;
    }
    if (demo_mode != 0) {
        click_warning(6, 0x50, 0xa0);
        return;
    }
    show_fx_box(2);
    out1 = t;
    while (out1 == 0) {
        tog_anims_game_loop();
    }
    setup_whole_screen_refresh();
}

// FUNCTION: C2 0x3227A
// WIN: 0x004b528c
// Lines 1621–1621
//
// Toggle the animations flag and re-render the FX dialog (anims tab).
void act_tog_anims(void)
{
    c2inf.anims_on ^= 1;
    show_fx_box(2);
}

// FUNCTION: C2 0x3228B
// WIN: 0x004b52af
// Lines 1623–1630
//
// FX-options dialog (mode 3 = end-of-year summary toggle).
// Tutorial blocked, no demo branch.  Loops on out1, pumping
// `tog_yearend_game_loop`, and refreshes on exit.
void act_toggle_year_end(void)
{
    int t = tutorial_mode;
    if (t != 0) {
        click_warning(2, 0x50, 0xa0);
        return;
    }
    show_fx_box(3);
    out1 = t;
    while (out1 == 0) {
        tog_yearend_game_loop();
    }
    setup_whole_screen_refresh();
}

// FUNCTION: C2 0x322D6
// WIN: 0x004b5308
// Lines 1631–1631
//
// Toggle the end-of-year-summary flag and re-render the FX dialog.
void act_tog_yearend(void)
{
    c2inf.yearend_on ^= 1;
    show_fx_box(3);
}

// FUNCTION: C2 0x322E7
// WIN: 0x004b532b
// Lines 1632–1637
//
// Toggle the "auto-save on year-end" bit (c2inf[+0x3B]) and
// re-render the year-end FX dialog (mode 3).  Tutorial / demo
// blocked.
void act_tog_autosave(void)
{
    if (tutorial_mode != 0) {
        click_warning(2, 0x50, 0xa0);
        return;
    }
    if (demo_mode != 0) {
        click_warning(6, 0x50, 0xa0);
        return;
    }
    c2inf.autosave_on ^= 1;
    show_fx_box(3);
}

// FUNCTION: C2 0x32337
// WIN: 0x004b5394
// Lines 1639–1643
//
// Adjust the game-speed slider in the FX dialog: kind 1,
// target=&c2inf[+4], step 0xa, max 0x64, min 0, (x,y)=(0xa0,0xa0),
// flag 1.
void act_game_speed(void)
{
    if (tutorial_mode != 0) {
        click_warning(2, 0x50, 0xa0);
        return;
    }
    adjust(1, &c2inf.game_speed, 0xa, 0x64, 0, 0xa0, 0xa0, 1);
}

// FUNCTION: C2 0x32386
// WIN: 0x004b53e7
// Lines 1644–1648
//
// Adjust the scroll-speed slider: kind 2, target=&c2inf[+8],
// step 0xa, max 0x64, min 0, (x,y)=(0xa0,0xa0), flag 1.
void act_scroll_speed(void)
{
    if (tutorial_mode != 0) {
        click_warning(2, 0x50, 0xa0);
        return;
    }
    adjust(2, &c2inf.scroll_speed, 0xa, 0x64, 0, 0xa0, 0xa0, 1);
}

// FUNCTION: C2 0x323D5
// WIN: 0x004b543a
// Lines 1650–1654
//
// Launch help topic 2 (tips).  Blocked in tutorial mode.
void act_help_tips(void)
{
    if (tutorial_mode) click_warning(2, 0x50, 0xA0);
    else               helping(2);
}

// FUNCTION: C2 0x32404
// WIN: 0x004b5472  (unverified)
// Lines 1655–1655
//
// In-game F1/help-button: pop the main help index modal.
void act_help_game(void)
{
    helping(1);
}

// FUNCTION: C2 0x3243D
// WIN: 0x004b5487
// Lines 1659–1663
//
// Launch help topic 3 (history).  Blocked in tutorial mode.
void act_help_history(void)
{
    if (tutorial_mode) click_warning(2, 0x50, 0xA0);
    else               helping(3);
}

// FUNCTION: C2 0x3246C
// WIN: 0x004b54bf
// Lines 1665–1665
//
// Launch help topic 0x5C (icon legend).
void act_help_icons(void)
{
    helping(0x5c);
}

// FUNCTION: C2 0x32473
// WIN: 0x004b54d4
// Lines 1670–1697
//
// Show the "About" / credits modal.  Loops `just_idle_game_loop`
// while the user is reading; right-click or any `exit_screen`
// hit closes the modal.  Cleans up mouse + refreshes screen.
void act_about(void)
{
    show_about_box();
    out1 = 0;
    while (out1 == 0) {
        just_idle_game_loop();
        if (mouse_right_click != 0) {
            out1 = 1;
        }
        if (exit_screen() != 0) {
            out1 = 1;
        }
    }
    clear_mouse();
    setup_whole_screen_refresh();
}

// FUNCTION: C2 0x32409
//
// Pop the in-game help/topics modal for `msg_id`, then refresh
// whichever main screen we came from (city / region / battle) so
// the help overlay is wiped.  Saves and restores `pointer_mode`
// across the call.
void helping(int msg_id)
{
    int saved_mode = pointer_mode;
    pointer_mode = 0;
    launch_help(msg_id);
    if (map_mode == 0) {
        city_map_screen(1);
    } else if (map_mode == 1) {
        region_map_screen(1);
    } else {
        battle_screen(1);
    }
    flush_sb_buffer();
    pointer_mode = saved_mode;
}

// FUNCTION: C2 0x324F1
// WIN: 0x004b55f2
// Lines 1699–1699
//
// Help modal: rewind history and signal the modal to redisplay (out2 = 10).
void act_rewind_help(void)
{
    rewind_help_history();
    out2 = 10;
}

// FUNCTION: C2 0x32501
// Lines 1700–1703
//
// Help modal: pause speech playback; ignored while the message queue is busy.
void act_pause_help(void)
{
    if (pause_db() != 0) return;
    help_buttons[1].state = 0;   /* un-toggle the help play/pause button */
}

// FUNCTION: C2 0x32513
// WIN: 0x004b562b
// Lines 1704–1704
//
// Help modal: restart from the beginning of the help history (out2 = 10).
void act_start_help(void)
{
    init_help_history();
    out2 = 10;
}

// FUNCTION: C2 0x3251A
// WIN: 0x004b5645
// Lines 1705–1705
//
// Help modal: exit (set out3 = 1, out2 = 10).
void act_exit_help(void)
{
    out3 = 1;
    out2 = 10;
}

// FUNCTION: C2 0x32526
// WIN: 0x004b5664
// Lines 1707–1711
//
// Generic "yes" button: decision = 1, out1 = 100 — dismiss the modal.
void act_yes(void)
{
    decision = 1;
    out1     = 100;
}

// FUNCTION: C2 0x32538
// WIN: 0x004b5680
// Lines 1713–1713
//
// Generic "no" button: decision = 0, out1 = 100 — dismiss the modal.
void act_no(void)
{
    decision = 0;
    out1     = 100;
}

// FUNCTION: C2 0x32542
// WIN: 0x004b569c
// Lines 1719–1722
//
// Toggle the global pause flag.
void act_pause(void)
{
    c2inf.paused ^= 1;
}

// FUNCTION: C2 0x3254A
// WIN: 0x004b56b5
// Lines 1724–1727
//
// Generic "out" button: set out1 = 10 to break a modal loop.
void act_out(void)
{
    out1 = 0xA;
}

// FUNCTION: C2 0x32555
// WIN: 0x004b56ca
// Lines 1729–1729
//
// Shared adjust-slider button: bump *adjust_var up by adjust_step (clamped at adjust_max).
void act_adjust_up(void)
{
    if (*adjust_var < adjust_max) *adjust_var += adjust_step;
}

// FUNCTION: C2 0x3256F
// WIN: 0x004b56f5
// Lines 1730–1730
//
// Shared adjust-slider button: drop *adjust_var down by adjust_step (clamped at adjust_min).
void act_adjust_down(void)
{
    if (*adjust_var > adjust_min) *adjust_var -= adjust_step;
}

// FUNCTION: C2 0x32589
// WIN: 0x004b5725
// Lines 1734–1734
//
// Debug/test placement (placing_type 5) — cheat-only.
void act_test(void)
{
    placing_type  = 5;
    placing_flags = 0;
}

// FUNCTION: C2 0x3259E
// WIN: 0x004b5744  (unverified)
// Lines 1736–1736
//
// Play the "exclaim" beep.
void act_exclaim(void)
{
    high_beep();
}

// FUNCTION: C2 0x325A3
// WIN: 0x004b5754
// Lines 1741–1747
//
// Undo the last city-map placement and clear the placing context.
void act_undo_cm(void)
{
    if (!sb_cm_undo_flushed) {
        restore_city_from_undo_buffer();
        setup_map_screen_refresh();
        placing_type   = 0xFF;
        placing_flags  = 0;
        pm_build_shape = 0;
    }
}

// FUNCTION: C2 0x325D2
// WIN: 0x004b5796
// Lines 1751–1760
//
// Pop the houses selection list (or open act_house1 directly when the housing cheat is off).
void act_houses(void)
{
    flag_mode = 0;
    if (housing_cheat) {
        get_selection_goods_list(0);
        control_selection(houses_selection, 6, mouse_x - 0x70, mouse_y - 0x30, 0x18);
    } else {
        act_house1();
    }
}

// FUNCTION: C2 0x3261D
// WIN: 0x004b57f3
// Lines 1761–1767
//
// Pop the "water structures" selection list (wells / fountains / etc.).
void act_water(void)
{
    flag_mode = 0;
    get_selection_goods_list(0);
    control_selection(water_selection, 5, mouse_x - 0x80, mouse_y - 0x30, 0xD);
    selected_icon_text = 0xD;
    selected_icon_no = selection_is;
}

// FUNCTION: C2 0x3266F
// WIN: 0x004b5848
// Lines 1768–1773
//
// Pop the security-buildings selection list (prefecture etc.).
void act_security(void)
{
    flag_mode = 0;
    get_selection_goods_list(0);
    control_selection(security_selection, 5, mouse_x - 0x90, mouse_y - 0x30, 0xE);
    selected_icon_text = 0xE;
    selected_icon_no = selection_is;
}

// FUNCTION: C2 0x326B3
// WIN: 0x004b589d
// Lines 1775–1780
//
// Pop the health-buildings selection list (hospital / baths).
void act_health(void)
{
    flag_mode = 0;
    get_selection_goods_list(0);
    control_selection(health_selection, 3, mouse_x - 0x90, mouse_y - 0x30, 0xF);
    selected_icon_text = 0xF;
    selected_icon_no = selection_is;
}

// FUNCTION: C2 0x326FA
// WIN: 0x004b58f2
// Lines 1782–1787
//
// Pop the gardens/plaza selection list.
void act_gardens_plaza(void)
{
    flag_mode = 0;
    get_selection_goods_list(0);
    control_selection(gardens_plaza_selection, 3, mouse_x - 0x70, mouse_y - 0x30, 0x3A);
    selected_icon_text = 0x3A;
    selected_icon_no = selection_is;
}

// FUNCTION: C2 0x3273E
// WIN: 0x004b5947
// Lines 1790–1790
//
// Enter city-clear placement mode (cost from city_costs[1]).
void act_clear(void) { placing_type = 1; placing_flags = 0; placing_cost = city_costs[1]; pm_build_shape = 0; flag_mode = 0; }

// FUNCTION: C2 0x32769
// WIN: 0x004b5984
// Lines 1791–1791
//
// Enter city-road placement mode.
void act_road(void)  { placing_type = 2; placing_flags = 0x20; placing_cost = city_costs[2]; pm_build_shape = 0; flag_mode = 0; }

// FUNCTION: C2 0x32798
// WIN: 0x004b59c1
// Lines 1792–1792
//
// Enter plaza placement mode.
void act_plaza(void)   { placing_type = 7; placing_flags = 0;    placing_cost = city_costs[8];  pm_build_shape = 0; }

// FUNCTION: C2 0x327BD
// WIN: 0x004b59f4
// Lines 1793–1793
//
// Enter gardens placement mode.
void act_gardens(void) { placing_type = 6; placing_flags = 0;    placing_cost = city_costs[7];  pm_build_shape = 0; }

// FUNCTION: C2 0x327D7
// WIN: 0x004b5a27
// Lines 1794–1794
//
// Enter tier-1 house placement mode.
void act_house1(void) { placing_type = 0x82; placing_flags = 1; placing_cost = city_costs[30]; pm_build_shape = 0; }

// FUNCTION: C2 0x32800
// WIN: 0x004b5a5a
// Lines 1795–1795
//
// Enter tier-2 house placement mode.
void act_house2(void) { placing_type = 0x88; placing_flags = 1; placing_cost = city_costs[36]; pm_build_shape = 0; }

// FUNCTION: C2 0x3281C
// WIN: 0x004b5a8d
// Lines 1796–1796
//
// Enter tier-3 house placement mode.
void act_house3(void) { placing_type = 0x8C; placing_flags = 1; placing_cost = city_costs[40]; pm_build_shape = 0; }

// FUNCTION: C2 0x32838
// WIN: 0x004b5ac0
// Lines 1797–1797
//
// Enter tier-4 house placement mode.
void act_house4(void) { placing_type = 0x96; placing_flags = 1; placing_cost = city_costs[50]; pm_build_shape = 0; }

// FUNCTION: C2 0x32854
// WIN: 0x004b5af3
// Lines 1798–1798
//
// Enter tier-5 house placement mode.
void act_house5(void) { placing_type = 0xA1; placing_flags = 1; placing_cost = city_costs[56]; pm_build_shape = 2; }

// FUNCTION: C2 0x3287D
// WIN: 0x004b5b26
// Lines 1800–1805
//
// Pop the forum-tier selection list (small/medium/large).
void act_forums(void)
{
    flag_mode = 0;
    get_selection_goods_list(0);
    control_selection(forum_selection, 4, mouse_x - 0x80, mouse_y - 0x30, 0x14);
    selected_icon_text = 0x14;
    selected_icon_no = selection_is;
}

// FUNCTION: C2 0x328C4
// WIN: 0x004b5b7b
// Lines 1808–1808
//
// Forum-selection: pick the small forum (pm_build_shape 1).
void act_select_small_forum(void)  { placing_type = 0xAE; placing_flags = 1; placing_cost = city_costs[70 + para1]; pm_build_shape = 1; }

// FUNCTION: C2 0x328EB
// WIN: 0x004b5bb5
// Lines 1809–1809
//
// Forum-selection: pick the medium forum (pm_build_shape 2).
void act_select_medium_forum(void) { placing_type = 0xB2; placing_flags = 1; placing_cost = city_costs[70 + para1]; pm_build_shape = 2; }

// FUNCTION: C2 0x32910
// WIN: 0x004b5bef
// Lines 1810–1810
//
// Forum-selection: pick the large forum (pm_build_shape 3).
void act_select_large_forum(void)  { placing_type = 0xB6; placing_flags = 1; placing_cost = city_costs[70 + para1]; pm_build_shape = 3; }

// FUNCTION: C2 0x32940
// WIN: 0x004b5c29
// Lines 1812–1812
//
// Enter watch-tower placement mode.
void act_tower(void)      { placing_type = 0xBF; placing_flags = 4;    placing_cost = city_costs[5];  pm_build_shape = 0; }

// FUNCTION: C2 0x3295F
// WIN: 0x004b5c5c
// Lines 1813–1813
//
// Enter city-wall placement mode.
void act_wall(void)       { placing_type = 3;    placing_flags = 2;    placing_cost = city_costs[3];  pm_build_shape = 0; }

// FUNCTION: C2 0x3297E
// WIN: 0x004b5c8f
// Lines 1814–1814
//
// Enter barracks placement mode.
void act_barracks(void) { placing_type = 0xD; placing_flags = 1; placing_cost = city_costs[13]; pm_build_shape = 2; }

// FUNCTION: C2 0x3299C
// WIN: 0x004b5cc2
// Lines 1815–1815
//
// Enter prefecture placement mode.
void act_prefecture(void) { placing_type = 0xE;  placing_flags = 1;    placing_cost = city_costs[14]; pm_build_shape = 0; }

// FUNCTION: C2 0x329BB
// WIN: 0x004b5cf5
// Lines 1816–1816
//
// Enter reservoir placement mode.
void act_resevoir(void)   { placing_type = 0xBE; placing_flags = 0x80; placing_cost = city_costs[6];  pm_build_shape = 0; }

// FUNCTION: C2 0x329DA
// WIN: 0x004b5d28
// Lines 1817–1817
//
// Enter aqueduct placement mode.
void act_aquaduct(void)   { placing_type = 4;    placing_flags = 0x40; placing_cost = city_costs[4];  pm_build_shape = 0; }

// FUNCTION: C2 0x329F9
// WIN: 0x004b5d5b
// Lines 1818–1818
//
// Enter fountain placement mode.
void act_fountain(void)   { placing_type = 0xC;  placing_flags = 1;    placing_cost = city_costs[12]; pm_build_shape = 0; }

// FUNCTION: C2 0x32A18
// WIN: 0x004b5d8e
// Lines 1819–1819
//
// Enter well placement mode.
void act_well(void)       { placing_type = 8;    placing_flags = 1;    placing_cost = city_costs[9];  pm_build_shape = 0; }

// FUNCTION: C2 0x32A37
// WIN: 0x004b5dc1
// Lines 1821–1827
//
// Pop the industry selection list.
void act_industries(void)
{
    flag_mode = 0;
    get_selection_goods_list(0);
    control_selection(industry_selection, 0x12, mouse_x - 0x80, mouse_y - 0x30, 0x10);
    if (selection_is == 1) {
        selected_icon_text = 0x10;
        selected_icon_no = selection_is;
    }
}

// FUNCTION: C2 0x32A8E
// WIN: 0x004b5e23
// Lines 1828–1828
//
// Enter business placement mode using business_build_type from para1.
void act_business(void)
{
    business_build_type = para1;
    placing_type = 0x10;
    placing_flags = 1;
    placing_cost = city_costs[16];
    pm_build_shape = 2;
}

// FUNCTION: C2 0x32AB6
// WIN: 0x004b5e60
// Lines 1829–1829
//
// Enter market placement mode.
void act_market(void)   { placing_type = 0xF; placing_flags = 1; placing_cost = city_costs[15]; pm_build_shape = 1; }

// FUNCTION: C2 0x32AD6
// WIN: 0x004b5e93
// Lines 1830–1830
//
// Enter hospital placement mode.
void act_hospital(void) { placing_type = 0xB; placing_flags = 1; placing_cost = city_costs[11]; pm_build_shape = 2; }

// FUNCTION: C2 0x32AF4
// WIN: 0x004b5ec6
// Lines 1831–1831
//
// Enter baths placement mode.
void act_baths(void)    { placing_type = 0xA; placing_flags = 1; placing_cost = city_costs[10]; pm_build_shape = 1; }

// FUNCTION: C2 0x32B14
// WIN: 0x004b5ef9
// Lines 1833–1838
//
// Pop the temple-tier selection list.
void act_temple(void)
{
    flag_mode = 0;
    get_selection_goods_list(0);
    control_selection(temple_selection, 4, mouse_x - 0x70, mouse_y - 0x30, 0x16);
    selected_icon_text = 0x16;
    selected_icon_no = selection_is;
}

// FUNCTION: C2 0x32B58
// WIN: 0x004b5f4e
// Lines 1840–1840
//
// Temple-selection: pick the small temple.
void act_select_small_temple(void)  { placing_type = 0x14; placing_flags = 1; placing_cost = city_costs[20]; pm_build_shape = 0; }

// FUNCTION: C2 0x32B77
// WIN: 0x004b5f81
// Lines 1841–1841
//
// Temple-selection: pick the medium temple.
void act_select_medium_temple(void) { placing_type = 0x15; placing_flags = 1; placing_cost = city_costs[21]; pm_build_shape = 1; }

// FUNCTION: C2 0x32B97
// WIN: 0x004b5fb4
// Lines 1842–1842
//
// Temple-selection: pick the large temple.
void act_select_large_temple(void)  { placing_type = 0x16; placing_flags = 1; placing_cost = city_costs[22]; pm_build_shape = 2; }

// FUNCTION: C2 0x32BB5
// WIN: 0x004b5fe7
// Lines 1844–1849
//
// Pop the education-buildings selection list.
void act_education(void)
{
    flag_mode = 0;
    get_selection_goods_list(0);
    control_selection(education_selection, 4, mouse_x - 0xA0, mouse_y - 0x30, 0x15);
    selected_icon_text = 0x15;
    selected_icon_no = selection_is;
}

// FUNCTION: C2 0x32BFC
// WIN: 0x004b603c
// Lines 1851–1851
//
// Education-selection: pick the grammaticus.
void act_select_grammaticus(void) { placing_type = 0x11; placing_flags = 1; placing_cost = city_costs[17]; pm_build_shape = 1; }

// FUNCTION: C2 0x32C1C
// WIN: 0x004b606f
// Lines 1852–1852
//
// Education-selection: pick the rhetor school.
void act_select_rhetor(void)      { placing_type = 0x12; placing_flags = 1; placing_cost = city_costs[18]; pm_build_shape = 2; }

// FUNCTION: C2 0x32C3A
// WIN: 0x004b60a2
// Lines 1853–1853
//
// Education-selection: pick the library.
void act_select_library(void)     { placing_type = 0x13; placing_flags = 1; placing_cost = city_costs[19]; pm_build_shape = 2; }

// FUNCTION: C2 0x32C58
// WIN: 0x004b60d5
// Lines 1855–1860
//
// Pop the entertainment-buildings selection list.
void act_entertainment(void)
{
    flag_mode = 0;
    get_selection_goods_list(0);
    control_selection(entertainment_selection, 7, mouse_x - 0x90, mouse_y - 0x30, 0x17);
    selected_icon_text = 0x17;
    selected_icon_no = selection_is;
}

// FUNCTION: C2 0x32C9F
// WIN: 0x004b612a
// Lines 1862–1862
//
// Entertainment-selection: pick the theatre.
void act_select_theatre(void)   { placing_type = 0x17; placing_flags = 1; placing_cost = city_costs[23]; pm_build_shape = 1; }

// FUNCTION: C2 0x32CBF
// WIN: 0x004b615d
// Lines 1863–1863
//
// Entertainment-selection: pick the odium.
void act_select_odium(void)     { placing_type = 0x18; placing_flags = 1; placing_cost = city_costs[24]; pm_build_shape = 1; }

// FUNCTION: C2 0x32CDF
// WIN: 0x004b6190
// Lines 1864–1864
//
// Entertainment-selection: pick the arena.
void act_select_arena(void)     { placing_type = 0x19; placing_flags = 1; placing_cost = city_costs[25]; pm_build_shape = 2; }

// FUNCTION: C2 0x32CFD
// WIN: 0x004b61c3
// Lines 1865–1865
//
// Entertainment-selection: pick the colosseum.
void act_select_colosseum(void) { placing_type = 0x1A; placing_flags = 1; placing_cost = city_costs[26]; pm_build_shape = 2; }

// FUNCTION: C2 0x32D1B
// WIN: 0x004b61f6
// Lines 1866–1866
//
// Entertainment-selection: pick the circus.
void act_select_circus(void)     { placing_type = 0x1B; placing_flags = 1; placing_cost = city_costs[27]; pm_build_shape = 4; }

// FUNCTION: C2 0x32D44
// WIN: 0x004b6229
// Lines 1867–1867
//
// Entertainment-selection: pick the circus maximus.
void act_select_circus_max(void) { placing_type = 0x1C; placing_flags = 1; placing_cost = city_costs[28]; pm_build_shape = 5; }

// FUNCTION: C2 0x32D6D
// WIN: 0x004b625c
// Lines 1870–1870
//
// Selection modal: cancel — clear the placing context.
void act_select_cancel(void)
{
    reg_placing_type = 0;
    placing_type     = 0;
    placing_flags    = 0;
    placing_cost     = 0;
}

// FUNCTION: C2 0x32D8A
// WIN: 0x004b628f
// Lines 1872–1886
//
// Pop the overview-map legend panel.  Loads the legend overlay,
// shows it, then idles in `read_mouse + colour_cycle_delay1` until
// the user releases the mouse button.  On dismissal restores the
// landfill/main overlay and refreshes the icon strip area.
void act_show_ov_legend(void)
{
    get_landfill(1);
    load_overlay_graphics(1);
    show_ov_legend_panel();
    do {
        read_mouse();
        if (mse_button == 0) {
            break;
        }
        if (colour_cycle_delay1(0x3c) != 0) {
            pulse_red(0x48, 6);
        }
    } while (1);
    load_overlay_graphics(0);
    show_landfill(com_x, com_y);
    setup_refresh_area(0x1e0, 0x30, 0xa, 0xb, 1);
    setup_whole_screen_refresh();
}

// FUNCTION: C2 0x32E0E
// WIN: 0x004b62d1
// Lines 1888–1894
//
// Pop the overview-map "select map type" selection.
// `get_selection_goods_list(0)` builds the option list, then
// `control_selection` runs the modal at fixed coordinates.
// Marks several update flags and reloads the landfill view.
void act_select_ov_map(void)
{
    get_selection_goods_list(0);
    control_selection(ovmap_selection, 0xb, 0x1f4, 0x36, 0x35);
    update_ov_bar = 1;
    redraw_icons = 1;
    update_map = 1;
    get_landfill(1);
    update_landfill = 1;
}

// FUNCTION: C2 0x32E60
//
// Undo last region-map placement (empty placeholder in PS).
void act_undo_rm(void)
{
}

// FUNCTION: C2 0x32E61
// WIN: 0x004b632e
// Lines 1896–1896
//
// Switch the overview map to mode 0 (geography) and trigger a landfill rebuild.
void act_ov_geography(void)
{
    ov_map_mode = 0;
    need_glf    = 1;
    clear_landfill();
}

// FUNCTION: C2 0x32E75
// WIN: 0x004b634c
// Lines 1897–1897
//
// Switch the overview map to mode 1 (land value) and trigger a landfill rebuild.
void act_ov_landval(void)
{
    ov_map_mode = 1;
    need_glf    = 1;
    clear_landfill();
}

// FUNCTION: C2 0x32E88
// WIN: 0x004b636a
// Lines 1898–1898
//
// Switch the overview map to mode 2 (water coverage).
void act_ov_water(void)    { ov_map_mode = 2; need_glf = 1; clear_landfill(); }

// FUNCTION: C2 0x32E91
// WIN: 0x004b6388
// Lines 1899–1899
//
// Switch the overview map to mode 3 (security).
void act_ov_security(void) { ov_map_mode = 3; need_glf = 1; clear_landfill(); }

// FUNCTION: C2 0x32E9A
// WIN: 0x004b63a6
// Lines 1900–1900
//
// Switch the overview map to mode 4 (unrest).
void act_ov_unrest(void)
{
    ov_map_mode = 4;
    need_glf    = 1;
    clear_landfill();
}

// FUNCTION: C2 0x32EA3
// WIN: 0x004b63c4
// Lines 1901–1901
//
// Switch the overview map to mode 5 (administration).
void act_ov_admin(void)
{
    ov_map_mode = 5;
    need_glf    = 1;
    clear_landfill();
}

// FUNCTION: C2 0x32EAC
// WIN: 0x004b63e2
// Lines 1902–1902
//
// Switch the overview map to mode 6 (entertainment).
void act_ov_entertainment(void)
{
    ov_map_mode = 6;
    need_glf    = 1;
    clear_landfill();
}

// FUNCTION: C2 0x32EB5
// WIN: 0x004b6400
// Lines 1903–1903
//
// Switch the overview map to mode 7 (education).
void act_ov_education(void)
{
    ov_map_mode = 7;
    need_glf    = 1;
    clear_landfill();
}

// FUNCTION: C2 0x32EBE
// WIN: 0x004b641e
// Lines 1904–1904
//
// Switch the overview map to mode 8 (health).
void act_ov_health(void)
{
    ov_map_mode = 8;
    need_glf    = 1;
    clear_landfill();
}

// FUNCTION: C2 0x32EC7
// WIN: 0x004b643c
// Lines 1905–1905
//
// Switch the overview map to mode 9 (industry).
void act_ov_industry(void) { ov_map_mode = 9; need_glf = 1; clear_landfill(); }

// FUNCTION: C2 0x32ED0
// WIN: 0x004b645a
// Lines 1909–1915
//
// Pop the region-map "security" selection list (rm_security_selection,
// 3 entries, width 0x36).  Falls through to the shared
// `selected_icon_no = selection_is` epilogue.
void act_rm_security(void)
{
    flag_mode = 0;
    pointer_mode = 0;
    get_selection_goods_list(0);
    control_selection(rm_security_selection, 3,
                      mouse_x - 0x90, mouse_y - 0x20, 0x36);
    selected_icon_text = 0x36;
    selected_icon_no = selection_is;
}

// FUNCTION: C2 0x32F1F
// WIN: 0x004b64b6
// Lines 1918–1924
//
// Pop the region-map "industry" selection list
// (rm_industry_selection, 7 entries, width 0x37).  Falls through
// to the shared selection-finalise epilogue.
void act_rm_industry(void)
{
    flag_mode = 0;
    pointer_mode = 0;
    get_selection_goods_list(0);
    control_selection(rm_industry_selection, 7,
                      mouse_x - 0x90, mouse_y - 0x30, 0x37);
    selected_icon_text = 0x37;
    selected_icon_no = selection_is;
}

// FUNCTION: C2 0x32F6E
// WIN: 0x004b651d
// Lines 1928–1928
//
// Enter region-map clear placement mode.
void act_clear_rm(void) { reg_placing_type = 0x21; reg_placing_flags = 0;    placing_cost = region_costs[1]; pm_build_shape = 0; flag_mode = 0; pointer_mode = 0; }

// FUNCTION: C2 0x32F9C
// WIN: 0x004b6561
// Lines 1929–1929
//
// Enter region-map road placement mode.
void act_road_rm(void)  { reg_placing_type = 0x1E; reg_placing_flags = 0x20; placing_cost = region_costs[2]; pm_build_shape = 0; flag_mode = 0; pointer_mode = 0; }

// FUNCTION: C2 0x32FCB
// WIN: 0x004b65a5
// Lines 1930–1930
//
// Enter region-map wall placement mode.
void act_wall_rm(void)       { reg_placing_type = 0x1F; reg_placing_flags = 2; placing_cost = region_costs[3]; pm_build_shape = 0; pointer_mode = 0; }

// FUNCTION: C2 0x32FFC
// WIN: 0x004b65df
// Lines 1931–1931
//
// Enter region-map warehouse placement mode.
void act_rm_warehouse(void)  { reg_placing_type = 0x24; reg_placing_flags = 1; placing_cost = region_costs[8]; pm_build_shape = 0; pointer_mode = 0; }

// FUNCTION: C2 0x33018
// WIN: 0x004b6619
// Lines 1932–1932
//
// Enter region-map workhouse placement mode.
void act_rm_workhouse(void)  { reg_placing_type = 0x23; reg_placing_flags = 1; placing_cost = region_costs[5]; pm_build_shape = 0; pointer_mode = 0; }

// FUNCTION: C2 0x33034
// WIN: 0x004b6653
// Lines 1933–1933
//
// Enter region-map port placement mode.
void act_rm_port(void)
{
    reg_placing_type  = 0x28;
    reg_placing_flags = 1;
    placing_cost      = region_costs[7];
    pm_build_shape    = 1;
    flag_mode         = 0;
    pointer_mode      = 0;
}

// FUNCTION: C2 0x3306E
// WIN: 0x004b6697
// Lines 1934–1939
//
// Enter region-map shipyard placement mode.
void act_rm_shipyard(void)
{
    pointer_mode      = 0;
    reg_placing_type  = 0x2A;
    reg_placing_flags = 1;
    placing_cost      = region_costs[9];
    pm_build_shape    = 1;
}

// FUNCTION: C2 0x33096
// WIN: 0x004b66d1
// Lines 1942–1942
//
// Enter region-map farm placement mode.
void act_rm_farm(void)   { reg_placing_type = 0x25; reg_placing_flags = 1; placing_cost = region_costs[6]; pm_build_shape = 1; pointer_mode = 0; }

// FUNCTION: C2 0x330C6
// WIN: 0x004b670b
// Lines 1943–1943
//
// Enter region-map mine placement mode.
void act_rm_mine(void)   { reg_placing_type = 0x26; reg_placing_flags = 1; placing_cost = region_costs[6]; pm_build_shape = 1; pointer_mode = 0; }

// FUNCTION: C2 0x330D3
// WIN: 0x004b6745
// Lines 1944–1944
//
// Enter region-map quarry placement mode.
void act_rm_quarry(void) { reg_placing_type = 0x27; reg_placing_flags = 1; placing_cost = region_costs[6]; pm_build_shape = 1; pointer_mode = 0; }

// FUNCTION: C2 0x330E0
// WIN: 0x004b677f
// Lines 1945–1945
//
// Enter region-map trading-post placement mode.
void act_rm_trading_post(void)
{
    reg_placing_type  = 0x29;
    reg_placing_flags = 1;
    placing_cost      = region_costs[10];
    pm_build_shape    = 1;
    flag_mode         = 0;
    pointer_mode      = 0;
}

// FUNCTION: C2 0x33101
// WIN: 0x004b67c3
// Lines 1946–1946
//
// Enter region-map fortress placement mode.
void act_rm_fort(void)   { reg_placing_type = 0x22; reg_placing_flags = 4; placing_cost = region_costs[4]; pm_build_shape = 0; pointer_mode = 0; }

// FUNCTION: C2 0x33120
// WIN: 0x004b67fd
// Lines 1948–1954
//
// "Order cohort" entry — clears the placing context, switches the
// pointer to selection-mode (2), and snapshots `denarii` so any
// subsequent build can be priced.
void act_order_cohort(void)
{
    flag_mode = 0;
    reg_placing_type = 0;
    reg_placing_flags = 0;
    pointer_mode = 2;
    starting_denarii = denarii;
}

// FUNCTION: C2 0x33148
// WIN: 0x004b6837
// Lines 1956–1990
//
// "Set patrol markers" — initiates the patrol-route placement UI
// for the currently tracked cohort.  If the army is exhausted
// (total_troops==0 && morale_timer==0) or already in state 10, it
// instead pops a "cannot patrol" warning.  Otherwise switches to
// pointer_mode 6, clears the route slot, copies the cohort's home
// position into over_x/over_y, sets order_progress based on
// state, and primes the elastic route preview.
void act_set_patrol_markers(void)
{
    int seg;
    int j;

    if ((army_list[tracking_army].total_troops == 0
            && army_list[tracking_army].morale_timer != 0)
            || army_list[tracking_army].state_idx == 0xa) {
        put_message(0x61, 0, 0);
        pointer_mode = 0;
        setup_map_screen_refresh();
        update_map = 1;
        clear_mouse();
        return;
    }

    pointer_mode = 6;
    army_list[tracking_army].dest_y = 0;
    army_list[tracking_army].dest_x = 0;
    unflag_all_rm_xwarehouse();

    /* Clear all 10 patrol-route slots' 15 entries. */
    for (seg = 0; seg < 10; seg++) {
        for (j = 0; j < 15; j++) {
            army_routes[(signed char)
                army_list[tracking_army].cohort_id]
                .points[seg][j].x = 0;
            army_routes[(signed char)
                army_list[tracking_army].cohort_id]
                .points[seg][j].y = 0;
        }
    }
    for (seg = 0; seg < 10; seg++) army_routes[(signed char)army_list[tracking_army].cohort_id].row_len[seg] = 0;

    this_route_number = 0;
    over_x = army_list[tracking_army].x;
    over_y = army_list[tracking_army].y;
    if ((signed char)army_list[tracking_army].state_idx == 4
            || (signed char)army_list[tracking_army].state_idx == 8) {
        army_list[tracking_army].order_progress = 1;
    } else {
        army_list[tracking_army].order_progress = 0;
    }
    set_route_elastic();
    save_undo_info();
    setup_map_screen_refresh();
    clear_mouse();
}

// FUNCTION: C2 0x3329B
// Lines 1992–2012
//
// "Return home" cohort order — resets the patrol-route slot,
// restores the cohort's home tile (army_list[+0x2C] is the
// home_ref), sets state_idx=5 (returning), clears the patrolling
// flag bit and sets order_progress=1.
void act_set_return_home(void)
{
    int q;
    int r;
    int i;

    pointer_mode = 0;
    army_list[tracking_army].dest_y = 0;
    army_list[tracking_army].dest_x = 0;
    unflag_all_rm_xwarehouse();

    for (i = 0; i < 10; i++) {
        army_routes[(signed char)
            army_list[tracking_army].cohort_id].row_len[i] = 0;
    }
    army_routes[(signed char)
        army_list[tracking_army].cohort_id].row_count = 0;
    army_routes[(signed char)
        army_list[tracking_army].cohort_id].chase_row = 0;
    army_routes[(signed char)
        army_list[tracking_army].cohort_id].target_army = 0;

    q = army_list[tracking_army].fort_ref / 8;
    r = q % 60;       /* 0x3c */
    army_list[tracking_army].target_x = r;
    army_list[tracking_army].target_y = (q / 60);
    army_list[tracking_army].state_idx = 5;
    army_list[tracking_army].flags &= ~2;
    army_list[tracking_army].order_progress = 1;
    setup_map_screen_refresh();
    clear_mouse();
}

// FUNCTION: C2 0x33360
// WIN: 0x004b6ce8
// Lines 2014–2031
//
// "Stop patrol" cohort order — clears the patrol slot, snaps the
// cohort's target position back onto its grid square, sets state
// 3 (idle), clears the patrolling flag bit and falls through to
// the shared map-refresh / clear-mouse epilogue at 0x3328d.
void act_set_patrol_stop(void)
{
    int i;
    int st;

    pointer_mode = 0;
    army_list[tracking_army].dest_y = 0;
    army_list[tracking_army].dest_x = 0;
    unflag_all_rm_xwarehouse();

    for (i = 0; i < 10; i++) {
        army_routes[(signed char)
            army_list[tracking_army].cohort_id].row_len[i] = 0;
    }
    army_routes[(signed char)
        army_list[tracking_army].cohort_id].row_count = 0;
    army_routes[(signed char)
        army_list[tracking_army].cohort_id].chase_row = 0;
    army_routes[(signed char)
        army_list[tracking_army].cohort_id].target_army = 0;

    army_list[tracking_army].target_x =
        army_list[tracking_army].x;
    army_list[tracking_army].target_y =
        army_list[tracking_army].y;
    st = (signed char)army_list[tracking_army].state_idx;
    if (st == 4 || st == 8) {
        army_list[tracking_army].order_progress = 1;
    } else {
        army_list[tracking_army].order_progress = 0;
    }
    army_list[tracking_army].state_idx = 3;
    army_list[tracking_army].flags &= ~2;

    setup_map_screen_refresh();
    clear_mouse();
}

// FUNCTION: C2 0x3342F
// WIN: 0x004b6f46
// Lines 2040–2048
//
// Rotate the map view clockwise by 90 degrees and refresh.
void act_rotate_clockwise(void)
{
    rotate_pm_anticlockwise();
    if (map_mode == 2) {
        if (c2inf.paused) figure_images();
        setup_battle_screen_refresh();
    } else {
        setup_map_screen_refresh();
    }
    clear_edge_info();
    update_landfill = 1;
    update_map      = 1;
    pointer_mode    = 0;
}

// FUNCTION: C2 0x3347A
// WIN: 0x004b6f99
// Lines 2055–2060
//
// Rotate the map view counter-clockwise by 90 degrees and refresh.
void act_rotate_anticlockwise(void)
{
    rotate_pm_clockwise();
    if (map_mode == 2) {
        if (c2inf.paused) figure_images();
        setup_battle_screen_refresh();
    } else {
        setup_map_screen_refresh();
    }
    clear_edge_info();
    update_landfill = 1;
    update_map      = 1;
    pointer_mode    = 0;
}

// FUNCTION: C2 0x33483
// WIN: 0x004b6fec  (unverified)
// Lines 2069–2069
//
// Zoom-out click handler — tail-calls do_act_zoom_out(0).
void act_zoom_out(void)
{
    do_act_zoom_out(0);
}

// FUNCTION: C2 0x33485
// WIN: 0x004b7001
// Lines 2074–2087
//
// Zoom out one step.  At zoom 2 nothing happens.  At zoom 1 we
// always shift the pm_x/pm_y centre.  At zoom 0 we shift only if
// `decayed` is non-zero.  Re-loads the map graphics for the new
// zoom level on success.
void do_act_zoom_out(int decayed)
{
    if (zoom_level == 2) {
        return;
    }
    if (zoom_level == 1 || decayed != 0) {
        pm_x -= 0xc;
        pm_y -= 0x28;
        refresh_zoom_mode(2);
    } else if (zoom_level == 0) {
        pm_x -= 4;
        pm_y -= 0x10;
        refresh_zoom_mode(1);
    }
    pm_limits();
    setup_map_screen_refresh();
    clip_zoom_level1();
    clear_edge_info();
    update_landfill = 1;
    update_map = 1;
    load_map_graphics(map_mode, zoom_level);
    pointer_mode = 0;
}

// FUNCTION: C2 0x33513
// WIN: 0x004b7196
// Lines 2089–2099
//
// Zoom-in click handler.  At zoom 0 it just sets `action_sound`
// (the click is filtered later).  At zoom 1/2 it pre-positions
// pm_x_coord/pm_y_coord and tail-calls `do_act_zoom_in(0)`.
// At pointer_mode 0 the call enters drag-zoom mode (sets
// pointer_mode 1) instead.
void act_zoom_in(void)
{
    if (zoom_level == 0) {
        action_sound = 1;
        return;
    }
    if (pointer_mode == 1) {
        if (zoom_level == 1) {
            pm_x_coord = 8;
            pm_y_coord = 0x1c;
        } else if (zoom_level == 2) {
            pm_x_coord = 0x10;
            pm_y_coord = 0x3c;
        }
        do_act_zoom_in(0);
        return;
    }
    if (zoom_level > 0) {
        pointer_mode = 1;
    }
}

// FUNCTION: C2 0x33583
// WIN: 0x004b72fc
// Lines 2100–2122
//
// Zoom in one step.  At zoom 1 we always shift; at zoom 0 we
// shift only if `decayed==1`.  Re-loads map graphics, refreshes,
// and clears pointer_mode.
void do_act_zoom_in(int decayed)
{
    if (zoom_level == 1 || decayed == 1) {
        pm_x = pm_x_coord + pm_x - 4;
        pm_y = ((pm_y_coord + pm_y) & 0xfffe) - 0xe;
        refresh_zoom_mode(0);
    } else if (zoom_level == 2) {
        pm_x = pm_x_coord + pm_x - 8;
        pm_y = ((pm_y_coord + pm_y) & 0xfffe) - 0x1e;
        refresh_zoom_mode(1);
    }
    pm_limits();
    setup_map_screen_refresh();
    clip_zoom_level1();
    clear_edge_info();
    update_landfill = 1;
    update_map = 1;
    load_map_graphics(map_mode, zoom_level);
    pointer_mode = 0;
}

// FUNCTION: C2 0x33640
// WIN: 0x004b74bd
// Lines 2124–2124
//
// Jump to the city map and dismiss the current modal.
void act_goto_city(void)
{
    act_goto_city_map();
    out3 = 1;
}

// FUNCTION: C2 0x33650
// WIN: 0x004b74e9
// Lines 2126–2144
//
// Toggle between city and region maps.  Saves the current view's
// rotation/zoom into its slot (city_rotation/zoom or
// prov_rotation/zoom), restores the other side's, flips
// `map_mode`, then calls `act_correct_map` to adjust pm_x/pm_y.
// Blocked in tutorial / demo (c2inf[+0x35] is the
// "tutorial-restrict-maps" flag).
void act_swap_maps(void)
{
    if (c2inf.peace_mode != 0) {
        click_warning(4, 0x50, 0xa0);
        return;
    }
    pointer_mode = 0;
    pm_build_shape = 0;
    placing_type = 0;
    placing_flags = 0;

    if (map_mode == 0) {
        map_mode = 1;
        city_rotation = map_direction;
        city_zoom_level = zoom_level;
        map_direction = prov_rotation;
        zoom_level = prov_zoom_level;
    } else {
        map_mode = 0;
        prov_rotation = map_direction;
        prov_zoom_level = zoom_level;
        map_direction = city_rotation;
        zoom_level = city_zoom_level;
    }
    act_correct_map();
}

// FUNCTION: C2 0x336FC
// WIN: 0x004b75b9
// Lines 2146–2155
//
// Switch to the city map (no-op if already there).  Saves the
// region pm_x/pm_y into region_pm_x/_y so they survive the swap.
void act_goto_city_map(void)
{
    if (map_mode == 0) {
        return;
    }
    pointer_mode = 0;
    pm_build_shape = 0;
    placing_type = 0;
    placing_flags = 0;

    prov_rotation = map_direction;
    prov_zoom_level = zoom_level;
    map_direction = city_rotation;
    zoom_level = city_zoom_level;
    map_mode = 0;

    region_pm_x = pm_x;
    region_pm_y = pm_y;
    pm_x = city_pm_x;
    pm_y = city_pm_y;
    act_correct_map();
}

// FUNCTION: C2 0x33783
// WIN: 0x004b7722
// Lines 2156–2177
//
// Switch to the region map.  Tutorial-restricted via c2inf[+0x35].
// First time around, region_pm_x is -1 and we initialise the
// region view (rebuild pseudo_map, jump to the city's
// reg_city_ptr cell).  Otherwise restore the saved pm_x/pm_y.
void act_goto_prov_map(void)
{
    if (c2inf.peace_mode != 0) {
        click_warning(4, 0x50, 0xa0);
        return;
    }
    if (map_mode == 1) {
        return;
    }
    pointer_mode = 0;
    pm_build_shape = 0;
    placing_type = 0;
    placing_flags = 0;

    city_rotation = map_direction;
    city_zoom_level = zoom_level;
    map_direction = prov_rotation;
    zoom_level = prov_zoom_level;
    map_mode = 1;

    city_pm_x = pm_x;
    city_pm_y = pm_y;

    if (region_pm_x == -1) {
        map_actual_width = 0x3c;
        map_actual_height = 0x3c;
        map_actual_atom = 8;
        map_width_reduction = 0xa;
        map_height_reduction = 0xa;
        get_pseudo_map(map_direction);
        jump_to_regionmap_ptr(reg_city_ptr);
        region_pm_x = pm_x;
        region_pm_y = pm_y;
    }
    map_mode = 1;
    pm_x = region_pm_x;
    pm_y = region_pm_y;
    act_correct_map();
}

// FUNCTION: C2 0x33899
// WIN: 0x004b78ff
// Lines 2180–2261
//
// After a map-mode change (city/region/battle), set the
// map_actual_* dimensions, command-strip rectangle, reset placing
// state, rebuild the pseudo_map, refresh the zoom, reload the
// graphic tiles, and finally show the destination screen.  Also
// kicks off the appropriate ambient/tune for the new mode.
void act_correct_map(void)
{
    if (map_mode == 1) {
        /* Region */
        map_actual_width  = 0x3c;
        map_actual_height = 0x3c;
        map_actual_atom   = 8;
        map_width_reduction  = 0xa;
        map_height_reduction = 0xa;
        com_x = 0x1f4; com_y = 0x44;
        com_w = 0x78;  com_h = 0x78;
    } else if (map_mode == 0) {
        /* City */
        map_actual_width  = 0x50;
        map_actual_height = 0x50;
        map_actual_atom   = 0x14;
        map_width_reduction = map_height_reduction = 0;
        com_x = 0x1e0; com_y = 0x30;
        com_w = 0xa0;  com_h = 0xa0;
    } else if (map_mode == 2) {
        /* Battle */
        map_actual_width  = 0x34;
        map_actual_height = 0x34;
        map_actual_atom   = 4;
        map_width_reduction  = 0xe;
        map_height_reduction = 0xe;
        com_x = 0x1e0; com_y = 0x30;
        com_w = 0xa0;  com_h = 0xa0;
    }

    update_icon = 0;
    overlays_on = 0;
    reg_placing_type = 0;
    reg_placing_flags = 0;
    placing_type = 0;
    placing_flags = 0;
    pm_build_shape = 0;

    get_pseudo_map(map_direction);

    if (map_mode == 2) {
        refresh_battle_zoom_mode(zoom_level);
    } else {
        refresh_zoom_mode(zoom_level);
    }
    pm_limits();
    setup_whole_screen_refresh();
    clear_edge_info();
    update_landfill = 1;

    if (map_mode == 2) {
        load_battle_graphics(zoom_level);
    } else {
        load_map_graphics(map_mode, zoom_level);
    }

    if (pre_loaded_status != 0 && map_mode == 2) {
        rebuild_figures_image_data();
    }

    if (map_mode == 0) {
        init_city_ambients();
        tune_mood = last_city_mood;
        if (city_tune_playing == 0) {
            play_tune("cityprov.xmi", 0);
        }
        city_tune_playing = 1;
    } else if (map_mode == 1) {
        init_prov_ambients();
        tune_mood = last_city_mood;
        if (city_tune_playing == 0) {
            play_tune("cityprov.xmi", 0);
        }
        city_tune_playing = 1;
    } else if (map_mode == 2) {
        init_battle_ambients();
        play_tune("batest2.xmi", 1);
        city_tune_playing = 0;
    }

    if (map_mode == 0) {
        city_map_screen(1);
    } else if (map_mode == 1) {
        region_map_screen(1);
    } else if (map_mode == 2) {
        battle_screen(1);
    }
    flush_sb_buffer();
    pointer_mode = 0;
}

// FUNCTION: C2 0x33B1C
// WIN: 0x004b7c74
// Lines 2264–2269
//
// Enter flag-marker pointer mode and clear the placing context.
void act_goto_flags(void)
{
    pointer_mode   = 0;
    goto_flag_marker_mode();
    placing_type   = 0;
    placing_flags  = 0;
    pm_build_shape = 0;
}

// FUNCTION: C2 0x33B40
// WIN: 0x004b7ca9
// Lines 2271–2279
//
// Cycle to the next "city flag" marker.  If `next_city_flag`
// returns 0 the city has none and a "no markers" message (id 0x67)
// pops up; otherwise enter flag-marker pointer mode (with a 10-tick
// decay) and pan the city map to that flag.
void act_set_marker1(void)
{
    pointer_mode = 0;
    placing_type = 0;
    placing_flags = 0;
    pm_build_shape = 0;
    if (next_city_flag() == 0) {
        put_message(0x67, 0, 0);
        return;
    }
    if (flag_mode == 0) {
        goto_flag_marker_mode();
        flag_mode_decay_count = 0xa;
    }
    jump_to_citymap_ptr(city_flag_list[last_city_flag]);
}

// FUNCTION: C2 0x33BA2
// WIN: 0x004b7d38
// Lines 2280–2288
//
// Province-flag twin of `act_set_marker1`: cycle next_prov_flag
// and pan the region map to it.
void act_set_marker2(void)
{
    pointer_mode = 0;
    placing_type = 0;
    placing_flags = 0;
    pm_build_shape = 0;
    if (next_prov_flag() == 0) {
        put_message(0x67, 0, 0);
        return;
    }
    if (flag_mode == 0) {
        goto_flag_marker_mode();
        flag_mode_decay_count = 0xa;
    }
    jump_to_regionmap_ptr(prov_flag_list[last_prov_flag]);
}

// FUNCTION: C2 0x33C04
// WIN: 0x004b7dc7
// Lines 2289–2298
//
// Danger-flag cycle.  `danger_flag_map_mode` selects whether the
// flag is on the city map (0) or region map (non-zero).
void act_set_marker3(void)
{
    int target;

    pointer_mode = 0;
    placing_type = 0;
    placing_flags = 0;
    pm_build_shape = 0;
    if (next_danger_flag() == 0) {
        put_message(0x67, 0, 0);
        return;
    }
    if (flag_mode == 0) {
        goto_flag_marker_mode();
        flag_mode_decay_count = 0xa;
    }
    target = danger_flag_list[last_danger_flag];
    if (danger_flag_map_mode == 0) {
        jump_to_citymap_ptr(target);
    } else {
        jump_to_regionmap_ptr(target);
    }
}

// FUNCTION: C2 0x33C77
// Lines 2305–2352
//
// Open the forum (advisor) screen.  Picks an entry tune based on
// `rand8`, resets `tracking_army`, primes the chosen department
// (slave_warning forces dept 8), then loops on
// `forum_game_loop` while the modal is up.  Mouse clicks change
// dept; on exit re-show the previous map.
void act_forum(void)
{
    pointer_mode = 0;
    stop_all_sounds();

    /* Entry tune choice based on rand8 buckets. */
    if (rand8 <= 1) play_tune("forum1.xmi", 1);
    else if (rand8 <= 4) play_tune("forum2.xmi", 1);
    else play_tune("forum3.xmi", 1);
    city_tune_playing = 0;
    tracking_army = 0;
    last_forum_dept = FORUM_DEPT_OVERVIEW;

    if (slave_warning != 0) { forum_dept = FORUM_DEPT_SLAVES; last_forum_dept = FORUM_DEPT_SLAVES; }
    evolve_to_current_fabric();
    forum_update_census(); current_temple_tip = 0;
    forum_constant_screen();

    show_forum_screen();
    out1 = 0;
    while (out1 == 0) {
        in_the_forum = 1;
        forum_game_loop();
        in_the_forum = 0;
        if (out1 == 2) { out1 = 0; stop_db(); show_forum_screen(); }
        forum_dept_over = FORUM_DEPT_OVERVIEW;

        if (c2inf.peace_mode == 0 || forum_dept != 0xb) {
            if (mouse_y < forum_repapering[forum_dept]) {
                continue;
            }
        }

        if (mouse_x >= 0x280) mouse_x = 0x27f;
        if (mouse_y >= 0x198) forum_dept_over = (char)over_forum_menu();
        else if (mouse_y >= 0xb0) {
            /* Pixel-pick from the dept-strip lookup table. */
            unsigned char *strip;
            strip = scratch_buffer; strip += mouse_x / 8;
            forum_dept_over = strip[(mouse_y - 0xb0) / 8 * 0x50 + 0x1d4c0];
        } else forum_dept_over = FORUM_DEPT_OVERVIEW;

        if (mouse_left_preclick == 0) continue;
        last_forum_dept = forum_dept;
        forum_dept = forum_dept_over;
        if (forum_dept == FORUM_DEPT_ADVISOR) launch_help(4);
        show_forum_screen();
    }

    forum_update_census();
    forum_dept = FORUM_DEPT_OVERVIEW;
    forum_dept_over = FORUM_DEPT_OVERVIEW;
    if (map_mode == 0) city_map_screen(1);
    else if (map_mode == 1) region_map_screen(1);
    play_tune("cityprov.xmi", 0);
    city_tune_playing = 1;
    flush_sb_buffer();
    in_the_forum = 0;
}

// FUNCTION: C2 0x33EA7
// WIN: 0x004b7e89
// Lines 2355–2364
//
// Tail-dispatch the per-department forum idle loop.  Each
// `forum_*_game_loop` runs the modal until either it sets `out1`
// or another department is chosen.  Falls through to the idle
// loop for unknown values.
void forum_game_loop(void)
{
    int d = forum_dept;
    if (d == FORUM_DEPT_ADMIN) { forum_admin_game_loop();    return; }
    if (d == FORUM_DEPT_CAREER) { forum_career_game_loop();   return; }
    if (d == FORUM_DEPT_ROME) { forum_rome_game_loop();     return; }
    if (d == FORUM_DEPT_CLERKS) { forum_clerks_game_loop();   return; }
    if (d == FORUM_DEPT_ARMY) { forum_army_game_loop();     return; }
    if (d == FORUM_DEPT_INDUSTRY) { forum_industry_game_loop(); return; }
    if (d == FORUM_DEPT_SLAVES) { forum_slaves_game_loop();   return; }
    if (d == FORUM_DEPT_EXIT) { out1 = 1; return; }
    if (d == FORUM_DEPT_TEMPLE) { forum_temple_game_loop();  return; }
    if (d == FORUM_DEPT_EMPIRE) { forum_empire_game_loop();  return; }
    forum_idle_game_loop();
}

// FUNCTION: C2 0x33EF2
// Lines 2365–2366
//
// Forum-internal "go to message" hook — sets out1 to 1 so the
// outer modal cycles around and re-displays the message screen.
void act_goto_message(void)
{
    out1 = 1;
}

// FUNCTION: C2 0x33F14
// WIN: 0x004b7fa2
// Lines 2369–2383
//
// Render the active forum department's full-screen layout.  When
// transitioning out of the temple (0xa) or empire (0xb) views
// (the latter only outside tutorial mode) we first fade to black
// to mask the screen-tearing the new department's repaint would
// cause.  Each dept screen is a tail-call.
void show_forum_screen(void)
{
    int d;

    if (last_forum_dept == FORUM_DEPT_TEMPLE) {
        black_out();
    }
    if (c2inf.peace_mode == 0 && last_forum_dept == FORUM_DEPT_EMPIRE) {
        black_out();
    }

    d = forum_dept;
    if (d == FORUM_DEPT_ADMIN) { forum_admin_screen();    return; }
    if (d == FORUM_DEPT_CAREER) { forum_career_screen();   return; }
    if (d == FORUM_DEPT_ROME) { forum_rome_screen();     return; }
    if (d == FORUM_DEPT_CLERKS) { forum_clerks_screen();   return; }
    if (d == FORUM_DEPT_ADVISOR) { forum_advisor_screen();  return; }
    if (d == FORUM_DEPT_ARMY) { forum_army_screen();     return; }
    if (d == FORUM_DEPT_INDUSTRY) { forum_industry_screen(); return; }
    if (d == FORUM_DEPT_SLAVES) { forum_slaves_screen();   return; }
    if (d == FORUM_DEPT_TEMPLE) { forum_temple_screen();  return; }
    if (d == FORUM_DEPT_EMPIRE) { forum_empire_screen();  return; }
    forum_empty_screen();
}

// FUNCTION: C2 0x33FA5
// WIN: 0x004b80ef
// Lines 2387–2399
//
// Hit-test the bottom-of-screen forum menu strip (FORUM_DEPT_END
// entries, 0..FORUM_DEPT_EMPIRE). Each is 0x18 wide x 0xa0 tall —
// coordinates from forum_menu[i*2] for x and forum_menu[i*2+1] for y.
// The natural one-past-last value is FORUM_DEPT_END; PS falls through
// with the final mouse_in_area() return value (0) when no entry matches.
int over_forum_menu(void)
{
    int i;
    for (i = 0; i < FORUM_DEPT_END; i++) {
        int x = forum_menu[i].x;
        int y = forum_menu[i].y;
        if (mouse_in_area(x, y, 0xa0, 0x18) != 0) {
            return i;
        }
    }
    return 0;
}

// FUNCTION: C2 0x33FDE
// WIN: 0x004b8163
// Lines 2402–2428
//
// Hit-test the empire-map regions.  The empire screen has 0x2c
// region records, each 16 bytes packed in scratch_buffer at
// `i * 16 + 8`:
//     short width        (LE @ +0)
//     short height       (LE @ +2)
//     int24 bitmap_off   (LE @ +4..+6)
// Region screen position is empire_positions[i*2 .. i*2+1] (shorts).
// If the cursor is inside the box and the bitmap byte at the
// (mx-x, my-y) offset is non-zero, region_over = i+1.
void get_region_over(void)
{
    int rx;
    int i;
    int h;
    int w;
    int bmp_off;
    int ry;
    unsigned char c;

    region_over = 0;
    for (i = 0; i < 0x2c; i++) {
        data_ptr = i * 16 + 8;

        w = ((scratch_buffer)[data_ptr + 1] << 8) + (scratch_buffer)[data_ptr];
        h = (scratch_buffer)[data_ptr + 2] + ((scratch_buffer)[data_ptr + 3] << 8);
        rx = empire_positions[i].x;
        ry = empire_positions[i].y;
        bmp_off = (scratch_buffer)[data_ptr + 4] + ((scratch_buffer)[data_ptr + 5] << 8)
                + (scratch_buffer)[data_ptr + 6] * 0x10000;

        if (mouse_x < rx) continue;
        if (ry > mouse_y) continue;
        if (((rx) + (w)) <= mouse_x) continue;
        if ((h + ry) <= mouse_y) continue;

        rx = mouse_x - rx; ry = mouse_y - ry;
        c = *(scratch_buffer + bmp_off + rx + ry * w);
        if (c != 0) {
            region_over = i + 1; return;
        }
    }
}

// FUNCTION: C2 0x340C2
// WIN: 0x004b82fa
// Lines 2430–2441
//
// "Final bribe to Caesar" modal.  Loops gift_game_loop(0x10) until
// the player commits or aborts; if accepted (decision==1) calls
// `bribe_emperor`, otherwise sets `game_state = 1` (resignation).
// Always sets out1=1 on exit so the surrounding loop terminates.
void act_final_bribe(void)
{
    final_bribe = 1;
    show_final_bribe_box();
    out1 = 0;
    decision = 0;
    if (players_denarii <= 0) {
        imperial_gift_level = 0;
    }
    while (out1 == 0) {
        gift_game_loop(0x10);
    }
    if (decision == 1) {
        bribe_emperor();
    } else {
        game_state = 1;
    }
    clear_mouse();
    out1 = 1;
}

// FUNCTION: C2 0x34134
// WIN: 0x004b838b
// Lines 2442–2442
//
// Drop Caesar's requested-tribute slider by 1 (floored at 0).
void act_request_down(void) { if (imperial_send_amount > 0) imperial_send_amount--; gen_refresh1 = 1; }

// FUNCTION: C2 0x34152
// WIN: 0x004b83b0
// Lines 2443–2443
//
// Raise Caesar's requested-tribute slider (clamped at the goods supply).
void act_request_up(void)
{
    if (imperial_send_amount < industry[imperial_req_goods].supply)
        imperial_send_amount++;
    gen_refresh1 = 1;
}

// FUNCTION: C2 0x34185
// WIN: 0x004b83f8
// Lines 2446–2446
//
// Raise the population-tax rate one step (clamped at 0x19).
void act_pop_tax_up(void)   { if (pop_tax_rate < 0x19) pop_tax_rate++;   gen_refresh1 = 1; }

// FUNCTION: C2 0x341A4
// WIN: 0x004b841d
// Lines 2447–2447
//
// Drop the population-tax rate one step (floored at 0).
void act_pop_tax_down(void) { if (pop_tax_rate > 0)    pop_tax_rate--;   gen_refresh1 = 1; }

// FUNCTION: C2 0x341B9
// WIN: 0x004b8442
// Lines 2448–2448
//
// Raise the industry-tax rate one step (clamped at 0x19).
void act_ind_tax_up(void)   { if (ind_tax_rate < 0x19) ind_tax_rate++;   gen_refresh1 = 1; }

// FUNCTION: C2 0x341D8
// WIN: 0x004b8467
// Lines 2449–2449
//
// Drop the industry-tax rate one step (floored at 0).
void act_ind_tax_down(void) { if (ind_tax_rate > 0)    ind_tax_rate--;   gen_refresh1 = 1; }

// FUNCTION: C2 0x341ED
// WIN: 0x004b848c
// Lines 2451–2451
//
// Raise the player salary slider by 1 (clamped at 0x3E8).
void act_salary_up(void)    { if (players_salary < 0x3E8) players_salary++; gen_refresh1 = 1; }

// FUNCTION: C2 0x3420F
// WIN: 0x004b84b4
// Lines 2452–2452
//
// Drop the player salary slider by 1 (floored at 0).
void act_salary_down(void)  { if (players_salary > 0)     players_salary--; gen_refresh1 = 1; }

// FUNCTION: C2 0x34224
// WIN: 0x004b84d9
// Lines 2453–2460
//
// Open the "make a donation to Rome" modal.  Clamps the donation
// to the player's available denarii first.  Idles
// `donation_game_loop` until the user accepts/cancels (out1!=0),
// then re-renders the career advisor screen.
void act_donation(void)
{
    if (donation_level > players_denarii) {
        donation_level = players_denarii;
    }
    show_donation_box();
    out1 = 0;
    while (out1 == 0) {
        donation_game_loop();
    }
    forum_career_screen();
    out1 = 0;
    clear_mouse();
}

// FUNCTION: C2 0x3426F
// WIN: 0x004b8539
// Lines 2462–2467
//
// "Donation +" button: bump the slider by 0xa if there's enough
// headroom (>= 10 below players_denarii), otherwise step by 1.
void act_donation_up(void)
{
    if ((players_denarii - 0xa) > donation_level) {
        donation_level += 0xa;
    } else if (donation_level < players_denarii) {
        donation_level += 1;
    }
    gen_refresh1 = 1;
}

// FUNCTION: C2 0x342AB
// WIN: 0x004b8582
// Lines 2468–2471
//
// "Donation –" button: drop by 0xa if >=10, by 1 otherwise.
// Floors at 0 — clicks are ignored once we've hit it.
void act_donation_down(void)
{
    if (donation_level > 0xa) {
        donation_level -= 0xa;
    } else if (donation_level > 0) {
        donation_level -= 1;
    }
    gen_refresh1 = 1;
}

// FUNCTION: C2 0x342CD
// WIN: 0x004b85c0
// Lines 2474–2477
//
// Commit the chosen donation amount: transfer denarii from the player to Rome.
void act_send_donation(void)
{
    denarii        += donation_level;
    players_denarii -= donation_level;
    act_goto_message();
}

// FUNCTION: C2 0x342E3
// WIN: 0x004b85f0
// Lines 2481–2481
//
// Extend the income-history graph window by one bucket (up to 4).
void act_history_graph_longer(void)  { if (history_graph_length < 4) history_graph_length++; gen_refresh1 = 1; }

// FUNCTION: C2 0x34302
// WIN: 0x004b8615
// Lines 2482–2482
//
// Shrink the income-history graph window by one bucket (floored at 0).
void act_history_graph_shorter(void) { if (history_graph_length > 0) history_graph_length--; gen_refresh1 = 1; }

// FUNCTION: C2 0x34317
// WIN: 0x004b863a
// Lines 2484–2492
//
// "Help" inside the army-box: launch help topic 0xb, then return
// to the army (forum dept 6) advisor view.
void act_army_box_help(void)
{
    launch_help(0xb);
    forum_dept = 6;
    last_forum_dept = FORUM_DEPT_ARMY;
    forum_constant_screen();
    show_forum_screen();
    hold_mouse_replace = 0;
    clear_mouse();
}

// FUNCTION: C2 0x34349
// WIN: 0x004b8676
// Lines 2493–2493
//
// Raise the army-wage slider by 5 denarii (clamped at 0x3E8).
void act_army_wage_up(void)    { if (army_wage_level < 0x3E8) army_wage_level += 5; gen_refresh1 = 1; gen_refresh2 = 1; }

// FUNCTION: C2 0x34364
// WIN: 0x004b86a6
// Lines 2494–2494
//
// Drop the army-wage slider by 5 denarii (floored at 0).
void act_army_wage_down(void)  { if (army_wage_level > 0)     army_wage_level -= 5; gen_refresh1 = 1; gen_refresh2 = 1; }

// FUNCTION: C2 0x34375
// WIN: 0x004b86d3
// Lines 2495–2495
//
// Raise the conscription rate by 1 (clamped at 0x32).
void act_conscription_up(void)   { if (conscription_rate < 0x32) conscription_rate++; gen_refresh1 = 1; gen_refresh2 = 1; }

// FUNCTION: C2 0x3439C
// WIN: 0x004b86ff
// Lines 2496–2496
//
// Drop the conscription rate by 1 (floored at 0).
void act_conscription_down(void) { if (conscription_rate > 0)    conscription_rate--; gen_refresh1 = 1; gen_refresh2 = 1; }

// FUNCTION: C2 0x343AD
// WIN: 0x004b872b
// Lines 2497–2497
//
// Cycle the army-box view forward to the next cohort and request a refresh.
void act_next_cohort(void)
{
    get_next_viewed_cohort(0);
    gen_refresh2 = 1;
    gen_refresh1 = 1;
}

// FUNCTION: C2 0x343C3
// WIN: 0x004b874e
// Lines 2498–2498
//
// Cycle the army-box view back to the previous cohort and request a refresh.
void act_prev_cohort(void)
{
    get_next_viewed_cohort(1);
    gen_refresh2 = 1;
    gen_refresh1 = 1;
}

// FUNCTION: C2 0x343CA
// WIN: 0x004b8771
// Lines 2499–2508
//
// 4-state demobilise toggle for the currently viewed army.
// army_list[+0xA0] cycles 0→1→2→3→0:
//   0   no demob queued
//   1   demob next turn
//   2   demob immediately (saves state_idx into +0x10, sets idle 0xa)
//   3   reverts (restores +0x10 into state_idx)
void act_demob_cohort(void)
{
    short idx = (short)get_actual_viewed_army();
    temp_army = idx;

    if (army_list[idx].cohort_size_class == 0) {
        army_list[idx].cohort_size_class = 1;
    } else {
        unsigned int s = army_list[idx].cohort_size_class;
        if (s == 1) {
            army_list[idx].cohort_size_class = 2;
        } else if (s == 2) {
            army_list[idx].cohort_size_class = 3;
            army_list[idx].saved_state_idx = army_list[idx].state_idx;
            army_list[idx].state_idx = 0xa;
        } else {
            army_list[idx].cohort_size_class = 0;
            army_list[idx].state_idx = army_list[idx].saved_state_idx;
        }
    }
    gen_refresh1 = 1;
    gen_refresh2 = 1;
}

// FUNCTION: C2 0x34448
// WIN: 0x004b88e9
// Lines 2510–2517
//
// "Hire +50 mercs" button: bumps mercs_in_army by 0x32, clamped
// at max_mercs_allowed.
void act_more_mercs(void)
{
    if (mercs_in_army < max_mercs_allowed) {
        mercs_in_army += 0x32;
        if (mercs_in_army >= max_mercs_allowed) {
            mercs_in_army = max_mercs_allowed;
        }
        gen_refresh3 = 1;
        gen_refresh1 = 1;
        gen_refresh2 = 1;
    }
}

// FUNCTION: C2 0x34483
// WIN: 0x004b8941
// Lines 2518–2528
//
// "Hire -50 mercs" button: rounds mercs_in_army down to the
// nearest multiple of 50, then subtracts 50 if already aligned.
// Floors at 0.
void act_less_mercs(void)
{
    if (mercs_in_army > 0) {
        int rem = mercs_in_army % 0x32;
        if (rem != 0) {
            mercs_in_army -= rem;
        } else {
            mercs_in_army -= 0x32;
        }
        if (mercs_in_army < 0) {
            mercs_in_army = 0;
        }
        gen_refresh3 = 1;
        gen_refresh1 = 1;
        gen_refresh2 = 1;
    }
}

// FUNCTION: C2 0x344D8
// WIN: 0x004b89c0
// Lines 2530–2531
//
// Raise the slave welfare bill by 1 (clamped at 0x61A8).
void act_slave_welfare_up(void)   { if (slave_welfare_bill < 0x61A8) slave_welfare_bill++; gen_refresh1 = 1; }

// FUNCTION: C2 0x344FB
// WIN: 0x004b89e8
// Lines 2532–2533
//
// Drop the slave welfare bill by 1 (floored at 0).
void act_slave_welfare_down(void) { if (slave_welfare_bill > 0)     slave_welfare_bill--; gen_refresh1 = 1; }

// FUNCTION: C2 0x3450C
// WIN: 0x004b8a0d
// Lines 2535–2535
//
// Allocate one more slave to the fire-brigade category.
void act_slave_fire_up(void)        { alter_slave_reqs(1,  1); gen_refresh2 = 1; }

// FUNCTION: C2 0x34516
// WIN: 0x004b8a2b
// Lines 2536–2536
//
// Take one slave away from the fire-brigade category.
void act_slave_fire_down(void)      { alter_slave_reqs(1, -1); gen_refresh2 = 1; }

// FUNCTION: C2 0x34523
// WIN: 0x004b8a49
// Lines 2537–2537
//
// Add one slave to the city-road upkeep category.
void act_slave_city_road_up(void)   { alter_slave_reqs(2,  1); gen_refresh2 = 1; }

// FUNCTION: C2 0x34530
// WIN: 0x004b8a67
// Lines 2538–2538
//
// Take one slave away from the city-road upkeep category.
void act_slave_city_road_down(void) { alter_slave_reqs(2, -1); gen_refresh2 = 1; }

// FUNCTION: C2 0x34538
// WIN: 0x004b8a85
// Lines 2539–2539
//
// Add one slave to the city-water upkeep category.
void act_slave_city_water_up(void)  { alter_slave_reqs(3,  1); gen_refresh2 = 1; }

// FUNCTION: C2 0x34545
// WIN: 0x004b8aa3
// Lines 2540–2540
//
// Take one slave away from the city-water upkeep category.
void act_slave_city_water_down(void){ alter_slave_reqs(3, -1); gen_refresh2 = 1; }

// FUNCTION: C2 0x3454D
// WIN: 0x004b8ac1
// Lines 2541–2541
//
// Add one slave to the city-wall upkeep category.
void act_slave_city_wall_up(void)   { alter_slave_reqs(4,  1); gen_refresh2 = 1; }

// FUNCTION: C2 0x34566
// WIN: 0x004b8adf
// Lines 2542–2542
//
// Take one slave away from the city-wall upkeep category.
void act_slave_city_wall_down(void) { alter_slave_reqs(4, -1); gen_refresh2 = 1; }

// FUNCTION: C2 0x3456E
// WIN: 0x004b8afd
// Lines 2543–2547
//
// Add one slave to the regional-work category.  Gated on !c2inf.peace_mode.
void act_slave_reg_work_up(void)    { if (!c2inf.peace_mode) { alter_slave_reqs(5,  1); gen_refresh2 = 1; } }

// FUNCTION: C2 0x34590
// WIN: 0x004b8b2f
// Lines 2548–2552
//
// Take one slave away from the regional-work category.  Gated on !c2inf.peace_mode.
void act_slave_reg_work_down(void)  { if (!c2inf.peace_mode) { alter_slave_reqs(5, -1); gen_refresh2 = 1; } }

// FUNCTION: C2 0x345B2
// WIN: 0x004b8b61
// Lines 2553–2557
//
// Add one slave to the regional-upkeep category.  Gated on !c2inf.peace_mode.
void act_slave_reg_upkeep_up(void)  { if (!c2inf.peace_mode) { alter_slave_reqs(6,  1); gen_refresh2 = 1; } }

// FUNCTION: C2 0x345D4
// WIN: 0x004b8b93
// Lines 2558–2562
//
// Take one slave away from the regional-upkeep category.  Gated on !c2inf.peace_mode.
void act_slave_reg_upkeep_down(void){ if (!c2inf.peace_mode) { alter_slave_reqs(6, -1); gen_refresh2 = 1; } }

// FUNCTION: C2 0x345F6
// WIN: 0x004b8bc5
// Lines 2564–2574
//
// Bring `slave_requirements[kind][0]` into agreement with the
// "needed" target at slot `+0x4`, by repeatedly nudging via
// `alter_slave_reqs` (which returns 0 once it can't move further).
void act_set_slaves_to_need_level(int kind)
{
    int delta;

    while (slave_requirements[kind].current
            != slave_requirements[kind].max) {
        if (slave_requirements[kind].current
                < slave_requirements[kind].max) {
            delta = 1;
        } else if (slave_requirements[kind].current
                > slave_requirements[kind].max) {
            delta = -1;
        }
        if (alter_slave_reqs(kind, delta) == 0) {
            break;
        }
    }
    gen_refresh2 = 1;
}

// FUNCTION: C2 0x3463A
// WIN: 0x004b8c5d
// Lines 2576–2608
//
// Adjust slave_requirements[kind][0] by delta (-1 or +1).  The
// pool is conserved through `slave_requirements[+0x38]` (free
// slaves remaining).  When `delta == +1` and the pool is empty we
// scan kinds 6→0 to take a slave from any other allotment.
// Returns 1 if a change was made, 0 if no slack was available.
int alter_slave_reqs(int kind, int delta)
{
    int k;

    if (delta == -1) {
        if (slave_requirements[kind].current <= 0) {
            return 0;
        }
        slave_requirements[kind].current -= 1;
        slave_requirements[7].current += 1;          /* +0x38 / 4 */
        return 1;
    }

    if (delta == 1) {
        if (slave_requirements[7].current != 0) {
            slave_requirements[kind].current += 1;
            slave_requirements[7].current -= 1;
            return 1;
        }
        /* Take from another category, kinds 6 → 1. */
        for (k = 6; k > 0; k--) {
            if (k == kind) continue;
            if (slave_requirements[k].current == 0) continue;
            slave_requirements[kind].current += 1;
            slave_requirements[k].current -= 1;
            return 1;
        }
        return 0;
    }

    return 0;
}

// FUNCTION: C2 0x346C7
// WIN: 0x004b8d3b
// Lines 2610–2620
//
// Open the "send a gift to Caesar" modal.  Loops gift_game_loop(4)
// until the user accepts or cancels; if accepted commits the gift
// via `bribe_emperor`.  Then re-renders the Rome advisor screen.
void act_send_gift(void)
{
    show_gift_box();
    out1 = 0;
    decision = 0;
    if (players_denarii <= 0) {
        imperial_gift_level = 0;
    }
    while (out1 == 0) {
        gift_game_loop(4);
    }
    if (decision == 1) {
        bribe_emperor();
    }
    forum_rome_screen();
    clear_mouse();
    out1 = 0;
}

// FUNCTION: C2 0x34728
// WIN: 0x004b8db8
// Lines 2622–2628
//
// Raise the imperial-gift slider by 1, clamped at the player's denarii.
void act_gift_up(void)
{
    if (players_denarii > 0) {
        imperial_gift_level++;
        if (imperial_gift_level > players_denarii) imperial_gift_level = players_denarii;
        gen_refresh1 = 1;
    }
}

// FUNCTION: C2 0x34755
// WIN: 0x004b8dfd
// Lines 2629–2632
//
// Drop the imperial-gift slider by 1 (floored at 0).
void act_gift_down(void)
{
    imperial_gift_level--;
    if (imperial_gift_level < 0) imperial_gift_level = 0;
    gen_refresh1 = 1;
}

// FUNCTION: C2 0x34779
// WIN: 0x004b8e25
// Lines 2636–2641
//
// Commit the imperial gift (decision = (level != 0); dismiss modal).
void act_gift_send(void)
{
    decision = (imperial_gift_level != 0);
    out1     = 1;
}

// FUNCTION: C2 0x34796
// WIN: 0x004b8e5a
// Lines 2643–2647
//
// Refresh the temple-tips strip with the new tip_kind selection.
void act_set_temple_tips(int tip_kind)
{
    get_temple_tip(tip_kind);
    gen_refresh1 = 1;
}

// FUNCTION: C2 0x347A3
// WIN: 0x004b8e78
// Lines 2651–2660
//
// Battle-screen zoom-level 1.  No-op when already at level 1;
// otherwise re-centre on (0x1c, 0x38) and reload battle graphics.
// Tail-calls clip_battle_zoom_level2 to validate pm_x/pm_y.
void act_zoom_level1(void)
{
    if (zoom_level == 1) {
        return;
    }
    pm_x = 0x1c;
    pm_y = 0x38;
    refresh_battle_zoom_mode(1);
    setup_battle_screen_refresh();
    clear_edge_info();
    update_landfill = 1;
    update_map = 1;
    load_battle_graphics(zoom_level);
    rebuild_figures_image_data();
    clip_battle_zoom_level2();
}

// FUNCTION: C2 0x347FB
// WIN: 0x004b8ee3
// Lines 2662–2666
//
// Battle zoom-level 2.  No-op at level 2; otherwise centre on
// (0xd, 0x18) and run the same refresh as act_zoom_level1
// (refresh_battle_zoom_mode + load_battle_graphics + clip).
void act_zoom_level2(void)
{
    if (zoom_level == 2) {
        return;
    }
    pm_x = 0xd;
    pm_y = 0x18;
    refresh_battle_zoom_mode(2);
    setup_battle_screen_refresh();
    clear_edge_info();
    update_landfill = 1;
    update_map = 1;
    load_battle_graphics(zoom_level);
    rebuild_figures_image_data();
    clip_battle_zoom_level2();
}

// FUNCTION: C2 0x34822
// WIN: 0x004b8f4e
// Lines 2673–2681
//
// Click the "begin / pause battle" toggle.  Marks icon-strip
// repaint, advances battle_state from 0→1 if applicable, flips
// the c2inf[+0x18] bit, and resets the battle_setup_count and
// battle_turbo flags.  Always points nomansland_ptr at the
// fixed 0x65900 buffer.
void act_stop_go(void)
{
    last_icon_used = 8;
    redraw_icons = 1;
    if (battle_state == 0) {
        battle_state = 1;
    }
    c2inf.paused ^= 1;
    nomansland_ptr = 0x65900;
    battle_turbo = 0;
    battle_setup_count = 0;
}

// FUNCTION: C2 0x34868
// WIN: 0x004b8fad
// Lines 2682–2686
//
// Toggle battle-screen turbo mode (no-op while battle_state == 0).
void act_turbo(void)
{
    if (battle_state) {
        battle_turbo ^= 1;
        battle_turbo_count = 0;
    }
}

// FUNCTION: C2 0x34883
// WIN: 0x004b8fdb
// Lines 2687–2692
//
// Battle: enter "move" pointer mode (1) when stats-control is on; otherwise deselect.
void act_move_unit(void)
{
    if (zoom_level == 2) return;
    if (!battle_stats_control) deselect_all_figures();
    else pointer_mode = 1;
}

// FUNCTION: C2 0x348A4
// WIN: 0x004b9019
// Lines 2693–2698
//
// Battle: enter "target" pointer mode (2) when stats-control is on; otherwise deselect.
void act_target_unit(void)
{
    if (zoom_level == 2) return;
    if (!battle_stats_control) deselect_all_figures();
    else pointer_mode = 2;
}

// FUNCTION: C2 0x348C5
// WIN: 0x004b9057
// Lines 2699–2704
//
// Battle "retreat" button: confirm and, on yes, advance battle_state to 6.
void act_battle_retreat(void)    { confirm(5, 0xA0, 0xA0); if (decision == 1) battle_state = 6; pointer_mode = 0; }

// FUNCTION: C2 0x348F9
// WIN: 0x004b9097
// Lines 2705–2708
//
// Battle "surrender" button: confirm and, on yes, advance battle_state to 7.
void act_battle_surrender(void)  { confirm(6, 0xA0, 0xA0); if (decision == 1) battle_state = 7; pointer_mode = 0; }

// FUNCTION: C2 0x34924
// WIN: 0x004b90d7
// Lines 2711–2714
//
// Battle "auto-calculate" button: confirm and, on yes, advance battle_state to 5.
void act_battle_autocalc(void)   { confirm(7, 0xA0, 0xA0); if (decision == 1) battle_state = 5; pointer_mode = 0; }

// FUNCTION: C2 0x3494F
// WIN: 0x004b9117
// Lines 2718–2724
//
// Battle: select every figure on the field (no-op at zoom 2).
void act_battle_select_all(void)
{
    if (zoom_level != 2) {
        select_all_figures();
        setup_whole_screen_refresh();
        update_map = 1;
    }
}

// FUNCTION: C2 0x3496D
// WIN: 0x004b9143
// Lines 2726–2726
//
// Battle: launch help topic 0x33.
void act_battle_help(void)
{
    helping(0x33);
}

// FUNCTION: C2 0x34977
// WIN: 0x004b9162
// Lines 2728–2735
//
// Battle: order selected units into a line formation (general_reform(0)).
void act_unit_line_formation(void)
{
    if (zoom_level == 2) return;
    general_reform(0);
    if (!battle_state) return;
    if (!battle_stats_control) deselect_all_figures();
    else pointer_mode = 1;
}

// FUNCTION: C2 0x349A8
// WIN: 0x004b91bc
// Lines 2736–2743
//
// Battle: order selected units into a column formation (general_reform(1)).
void act_unit_column_formation(void)
{
    if (zoom_level == 2) return;
    general_reform(1);
    if (!battle_state) return;
    if (!battle_stats_control) deselect_all_figures();
    else pointer_mode = 1;
}

// FUNCTION: C2 0x349DC
// WIN: 0x004b9216
// Lines 2744–2751
//
// Battle: order selected units into a testudo / tortoise formation (general_reform(2)).
void act_unit_tortoise_formation(void)
{
    if (zoom_level == 2) return;
    general_reform(2);
    if (!battle_state) return;
    if (!battle_stats_control) deselect_all_figures();
    else pointer_mode = 1;
}

// FUNCTION: C2 0x34A10
// WIN: 0x004b9270
// Lines 2752–2756
//
// mop_up tail-calls general_reform(3) — no battle_state guard,
// just clears pointer_mode and lets reform run.
void act_unit_mop_up_formation(void)
{
    if (zoom_level == 2) return;
    pointer_mode = 0;
    general_reform(3);
}

// FUNCTION: C2 0x34A2E
// WIN: 0x004b92a1
// Lines 2768–2786
//
// "Choose skill levels" startup dialog.  Loops show_skill1_box +
// skill1_game_loop until accepted, then show_skill2_box (unless
// the user already exited / preloaded a save / continues a
// tutorial).  If skill2 returns 0x42a we go back to skill1.
void act_set_skill_levels(void)
{
    pre_loaded_status = 0;
    tutorial_mode = 0;
    continue_tutorial_status = 0;

    do {
        show_skill1_box();
        out1 = 0;
        while (out1 == 0) {
            skill1_game_loop();
        }
        if (continue_tutorial_status != 0
                || exit_flag != 0
                || pre_loaded_status != 0) {
            break;
        }
        show_skill2_box();
        out1 = 0;
        while (out1 == 0) {
            skill2_game_loop();
        }
    } while (out1 == 0x42a);
    flush_sb_buffer();
}

// FUNCTION: C2 0x34AB0
// WIN: 0x004b9357
// Lines 2788–2824
//
// Province-selection on first promotion.  In tutorial mode this is
// pre-canned: province_is = 0, province_difficulty derived from
// c2inf[+0x34].  Otherwise pop the initial-region modals; on player
// rank 0 the first run shows show_first_region_box; on no
// provinces left the player must restart.
void act_choose_init_region(void)
{
    if (tutorial_mode != 0) {
        return;
    }
    if (c2inf.peace_mode != 0) {
        province_is = 0;
        province_difficulty = c2inf.skill_level * 2 + 1;
        return;
    }
    clear_mouse();
    get_new_province_options();
    if (provinces_on_offer == 0) {
        do_vga_smacked_anim("wingame.smk");
    }
    if (player_rank == 0) {
        show_initreg_box();
        show_first_region_box();
        out2 = 0;
        while (out2 != 1) {
            just_idle_game_loop();
            if (mouse_right_preclick != 0) {
                out2 = 1;
            }
        }
        reshow_initreg_box();
    } else {
        show_initreg_box();
    }
    if (provinces_on_offer == 0) {
        show_no_provinces_box();
    }
    out2 = 0;
    if (provinces_on_offer == 0) {
        while (out2 != 1) {
            just_idle_game_loop();
            if (mouse_right_click != 0) {
                out2 = 1;
            }
        }
        restart_flag = 1;
    } else {
        while (out2 != 1) {
            initreg_game_loop();
        }
    }
    flush_sb_buffer();
}

// FUNCTION: C2 0x34BB1
// WIN: 0x004b94a6
// Lines 2826–2843
//
// Pop the "this region: <name>" confirmation modal during the
// new-province flow.  Loops show_buttons + control_buttons (the
// Yes / No pair `confirming_buttons`) until out1 == 1.  Translates
// out1 down by 1 (the buttons array is 1-indexed) and stamps the
// resulting decision into out2.
void this_region(void)
{
    this_region_box(0);
    out1 = 0; decision = 0;
    while (out1 != 1) {
        gloop_start();
        show_buttons(0x170, 0x110, confirming_buttons, 2);
        gloop_end();
        control_buttons(0x170, 0x110, confirming_buttons, 2);
        if (out1 > 0xa) { out1 = 0xa; }
        if (out1 > 1) out1 -= 1;
    }
    if (decision == 0) { out2 = 0; }
    else if (decision == 1) { out2 = 1; }
    clear_mouse(); out1 = 0;
    stop_db();
    setup_whole_screen_refresh();
}

// FUNCTION: C2 0x34C7B
// WIN: 0x004b9590
// Lines 2846–2851
//
// Run a tutorial-mode game once (`do_tutorial`).  After it returns,
// either go to the skill1 dialog (regular flow) or just set
// out1=1 (`continue_tutorial_status` was set, meaning the player
// chose "continue" and we should not reset).
void act_tutorial(void)
{
    do_tutorial();
    if (continue_tutorial_status == 0) {
        show_skill1_box();
        out1 = 0;
    } else {
        out1 = 1;
    }
}

// FUNCTION: C2 0x34CA5
// WIN: 0x004b9647
// Lines 2852–2852
//
// New-game flow: "quit to DOS" — set exit_flag and dismiss the modal.
void act_dos(void)
{
    exit_flag = 1;
    act_goto_message();
}

// FUNCTION: C2 0x34CB1
// WIN: 0x004b9663
// Lines 2854–2854
//
// Raise the difficulty slider by 1 (clamped at 4).
void act_skill_up(void)
{
    if (c2inf.skill_level < 4) {
        gen_refresh1 = 1;
        c2inf.skill_level++;
    }
}

// FUNCTION: C2 0x34CCC
// WIN: 0x004b968b
// Lines 2855–2855
//
// Drop the difficulty slider by 1 (floored at 0).
void act_skill_down(void)
{
    if (c2inf.skill_level > 0) {
        gen_refresh1 = 1;
        c2inf.skill_level--;
    }
}

// FUNCTION: C2 0x34CEB
// WIN: 0x004b96b2
// Lines 2856–2856
//
// Toggle the peaceful-mode (no-region) flag.
void act_tog_peace(void)
{
    c2inf.peace_mode ^= 1;
    gen_refresh2   = 1;
}

// FUNCTION: C2 0x34CFA
// WIN: 0x004b96d2
// Lines 2858–2864
//
// "Edit player name" modal during the new-game flow.  Idles
// new_name_game_loop while the user types, then re-shows skill2
// box.
void act_choose_name(void)
{
    insert_cursor = 0;
    this_letter = 0;
    in_format_buffer(c2inf.player_name, 0x18, 0xa0, 2);
    show_new_name_box();
    out2 = 0;
    while (out2 == 0) {
        new_name_game_loop();
    }
    show_skill2_box();
    setup_whole_screen_refresh();
}

// FUNCTION: C2 0x34D4D
// WIN: 0x004b9735
// Lines 2868–2868
//
// Close the current modal back to the new-game front panel (out1 = 1066).
void act_back_to_front_panel(void)
{
    out1 = 1066;
}

// FUNCTION: C2 0x34D58
// WIN: 0x004b974a
// Lines 2870–2877
//
// "Load saved game" entry from the new-game flow.  On success
// (file_loaded_status set), close the new-game flow with
// pre_loaded_status and out1=1; otherwise reopen the skill1 box.
void act_preload(void)
{
    load_a_game();
    if (file_loaded_status != 0) {
        out1 = 1;
        pre_loaded_status = 1;
    } else {
        out1 = 0;
        show_skill1_box();
    }
    setup_whole_screen_refresh();
    hold_mouse_replace = 1;
}

// FUNCTION: C2 0x34D95
// WIN: 0x004b9795
// Lines 2879–2894
//
// Pop the census panel and idle until the user dismisses it.
// Battle mode is silently ignored.
void act_census(void)
{
    if (map_mode == 2) {
        return;
    }
    in_census_mode = 1;
    clear_mouse();
    show_census_panel();
    out1 = 0;
    while (out1 != 1) {
        just_idle_game_loop();
        if (exit_screen() != 0) {
            out1 = 1;
        }
        if (mouse_right_click != 0) {
            out1 = 1;
        }
    }
    cover_mouse_droppings();
    setup_map_screen_refresh();
    in_census_mode = 0;
}

// FUNCTION: C2 0x34E10
// WIN: 0x004b97d7
// Lines 2896–2937
//
// Show the query panel for the cell under the cursor.  Resolves
// pm_over_cm_ptr → act_start_x/y, fetches city or region info,
// pre-selects the proper view button (queery_buttons+0x54 / +0x6C
// / +0x84) based on q_type/q_flag, then idles queery_game_loop
// while the user clicks through it.  Restores pointer_mode on
// exit.
void act_query(void)
{
    int saved_pm;
    if (map_mode > 1) {
        return;
    }
    get_pm_over_diamond(1);
    saved_pm = pointer_mode;
    pointer_mode = 0;
    act_start_pm_ptr = pm_over_cm_ptr;
    act_start_ptr = pm_over_cm_ptr / map_actual_atom;
    act_start_x = act_start_ptr % map_actual_width;
    act_start_y = act_start_ptr / map_actual_width;

    evolve_to_current_fabric();
    if (map_mode == 0) {
        get_query_info();
    } else {
        get_region_query_info();
    }

    /* Reset the three "active dot" markers in the query button bar. */
    queery_buttons[3].state = 0;
    queery_buttons[4].state = 0;
    queery_buttons[5].state = 0;

    if (q_type >= 0x82
            && q_type <= 0xa1) {
        query_mode = last_house_query_mode;
        queery_buttons[last_house_query_mode + 3].state = 1;
    } else {
        unsigned int flag20 = q_flag & 0x20;
        if (flag20 != 0) {
            query_mode = 1;
            queery_buttons[4].state = 1;
        } else {
            query_mode = 0;
            queery_buttons[3].state = 1;
        }
    }

    if (map_mode == 0) {
        nof_query_buttons = 6;
    } else {
        nof_query_buttons = 3;
    }
    show_query_panel();
    clear_mouse();
    out3 = 0;
    while (out3 != 1) {
        queery_game_loop();
        if (exit_screen() != 0) {
            out2 = 1;
            out3 = 1;
        }
        if (mouse_right_click != 0) {
            out3 = 1;
        }
    }
    if (q_type >= 0x82
            && q_type <= 0xa1) {
        last_house_query_mode = query_mode;
    }
    setup_map_screen_refresh();
    update_map = 1;
    pointer_mode = saved_pm;
    clear_mouse();
}

// FUNCTION: C2 0x34FB3
// WIN: 0x004b99d4
// Lines 2941–2947
//
// Query-panel "General" tab.  Only acts when query_mode != 0:
// resets the other two button dots, clears query_mode, and
// re-renders the panel (city map first when in city view).
void act_general_query(void)
{
    if (query_mode == 0) {
        queery_buttons[3].state = 1;
    } else {
        queery_buttons[4].state = 0;
        queery_buttons[5].state = 0;
        query_mode = 0;
    }
    if (map_mode == 0) {
        show_citymap();
    }
    show_query_panel();
}

// FUNCTION: C2 0x34FF1
// WIN: 0x004b9a29
// Lines 2948–2953
//
// Query-panel "People" tab.  Same shape as `act_general_query`
// but selects mode 1.  Tail-jumps into act_general_query's
// repaint helper.
void act_people_query(void)
{
    if (query_mode == 1) {
        queery_buttons[4].state = 1;
    } else {
        queery_buttons[3].state = 0;
        queery_buttons[5].state = 0;
        query_mode = 1;
    }
    if (map_mode == 0) {
        show_citymap();
    }
    show_query_panel();
}

// FUNCTION: C2 0x35032
// WIN: 0x004b9a7e
// Lines 2955–2958
//
// Query-panel "Detailed" tab.  Selects mode 2 then runs the shared
// repaint epilogue.
void act_detailed_query(void)
{
    if (query_mode == 2) {
        queery_buttons[5].state = 1;
    } else {
        queery_buttons[3].state = 0;
        queery_buttons[4].state = 0;
        query_mode = 2;
    }
    if (map_mode == 0) {
        show_citymap();
    }
    show_query_panel();
}

// FUNCTION: C2 0x3505E
// WIN: 0x004b9ad3  (unverified)
// Lines 2962–2962
//
// Query panel: navigate to the help page (delta 0).
void act_query_help(void)
{
    act_query_do_help(0);
}

// FUNCTION: C2 0x35062
// WIN: 0x004b9ae8  (unverified)
// Lines 2963–2963
//
// Query panel: navigate to the tips page (delta +1).
void act_query_tips(void)
{
    act_query_do_help(1);
}

// FUNCTION: C2 0x35069
// WIN: 0x004b9afd
// Lines 2964–2964
//
// Query panel: navigate to the history page (delta +2).
void act_query_history(void)
{
    act_query_do_help(2);
}

// FUNCTION: C2 0x3506E
// WIN: 0x004b9b12
// Lines 2977–3005
//
// Pop a help-page modal for the current query.  Adds `delta` to
// `this_help_page` (so help-cursor arrows page through topics),
// then routes through three redirect tables (temple-tips,
// temple-history, ent-history) before checking the debar list.
// If allowed, calls `launch_help` and re-renders the underlying
// map screen and query panel.  Always clears mouse and resets
// pointer_mode on exit.  Returns 0.
void act_query_do_help(int delta)
{
    int debarred;
    int i;

    this_help_page += delta;
    debarred = 0;

    /* Temple-tips redirect: 2 entries, page 0xec is the canonical. */
    for (i = 0; i < 2; i++) {
        if (this_help_page == help_redir_temple_tips[i]) {
            this_help_page = 0xec;
        }
    }

    /* Temple-history redirect: 2 entries, page 0xed canonical. */
    for (i = 0; i < 2; i++) {
        if (this_help_page == help_redir_temple_history[i]) {
            this_help_page = 0xed;
        }
    }

    /* Entertainment-history redirect: 5 pairs (page → replacement). */
    for (i = 0; i < 5; i++) {
        if (this_help_page == help_redir_ent_history[i].page) {
            this_help_page = help_redir_ent_history[i].replacement;
        }
    }

    /* Debar list — empty by default. */
    for (i = 0; i < 0; i++) {
        if (this_help_page == help_debar[i]) {
            debarred = 1;
            this_help_page -= delta;
        }
    }

    if (!debarred) {
        launch_help(this_help_page);
        if (map_mode == 0) {
            city_map_screen(1);
        } else if (map_mode == 1) {
            region_map_screen(1);
        } else {
            battle_screen(1);
        }
        show_query_panel();
    }
    flush_sb_buffer();
    pointer_mode = 0;
    out2 = 0;
    out3 = 0;
}

// FUNCTION: C2 0x35170
// WIN: 0x004b9c74
// Lines 3008–3012
//
// Toggle query pointer mode (between 4 and 0).
void act_query_mode(void)
{
    if (pointer_mode == 4) pointer_mode = 0;
    else                   pointer_mode = 4;
}

// FUNCTION: C2 0x35190
// WIN: 0x004b9ca2
// Lines 3017–3055
//
// Final stub for the source file: end-of-year sequence.  Tutorial
// games skip the modal entirely.  When the year-end summary is
// disabled (c2inf[+0x39] == 0) we just do an autosave (if enabled)
// and return.  Otherwise show the year-end review screen, idle on
// just_idle_game_loop, then re-show the underlying map.  The
// `turbo_mode` flag re-enters turbo on exit.
void act_do_year_end(void)
{
    int saved_pm;

    if (tutorial_mode != 0) {
        return;
    }
    swap_circus_gfx();

    if (c2inf.yearend_on == 0) {
        if (c2inf.autosave_on != 0) {
            savegame("lastyear.sav");
        }
        return;
    }

    if (game_state == 3 || game_state == 1 || game_state == 2) {
        return;
    }

    saved_pm = pointer_mode;
    turbo_mode = 0;
    local_time = time_is;
    pointer_mode = 0;
    show_top_line();
    show_year_end_screen();
    out1 = 0;

    if (c2inf.autosave_on != 0) {
        savegame("lastyear.sav");
    }

    while (out1 == 0) {
        just_idle_game_loop();
        if (mouse_right_click != 0) {
            out1 = 1;
        }
        if (exit_screen() != 0) {
            out1 = 1;
        }
    }

    if (map_mode == 0) {
        city_map_screen(1);
    } else if (map_mode == 1) {
        region_map_screen(1);
    }
    flush_sb_buffer();
    pointer_mode = saved_pm;
    if (turbo_mode != 0) {
        act_init_turbo_mode();
    }
}

void (*city_actions[24])(void) = {
    act_rotate_clockwise,
    act_rotate_anticlockwise,
    act_goto_flags,
    act_set_marker1,
    act_set_marker2,
    act_set_marker3,
    act_goto_city_map,
    act_forum,
    act_goto_prov_map,
    act_zoom_in,
    act_clear,
    act_houses,
    act_road,
    act_forums,
    act_zoom_out,
    act_water,
    act_security,
    act_industries,
    act_health,
    act_query_mode,
    act_entertainment,
    act_temple,
    act_education,
    act_gardens_plaza
};

void (*region_actions[19])(void) = {
    act_rotate_clockwise,
    act_rotate_anticlockwise,
    act_goto_flags,
    act_set_marker1,
    act_set_marker2,
    act_set_marker3,
    act_goto_city_map,
    act_forum,
    act_goto_prov_map,
    act_zoom_in,
    act_clear_rm,
    act_road_rm,
    act_rm_security,
    act_rm_trading_post,
    act_zoom_out,
    act_query_mode,
    act_rm_industry,
    act_order_cohort,
    act_rm_port
};

void (*battle_actions[17])(void) = {
    act_rotate_clockwise,
    act_rotate_anticlockwise,
    act_zoom_level1,
    act_zoom_level2,
    act_stop_go,
    act_turbo,
    act_move_unit,
    act_target_unit,
    act_unit_line_formation,
    act_unit_column_formation,
    act_unit_tortoise_formation,
    act_unit_mop_up_formation,
    act_battle_retreat,
    act_battle_surrender,
    act_battle_autocalc,
    act_battle_select_all,
    act_battle_help
};

int help_redir_house_tips[5] = { 161, 176, 191, 206, 221 };

int help_redir_house_history[5] = { 162, 177, 192, 207, 222 };

int help_redir_temple_tips[2] = { 251, 266 };

int help_redir_temple_history[2] = { 252, 267 };

struct help_redirect_rec help_redir_ent_history[5] = {
    { 507, 492 },
    { 537, 522 },
    { 567, 552 },
    { 597, 582 },
    { 612, 582 }
};

int help_debar[31] = { 372, 477, 627, 671, 672, 686, 687, 701, 702, 716, 717, 731, 732, 746, 747, 762, 776, 777, 792, 806, 807, 821, 822, 897, 912, 926, 927, 942, 957, 972, 987 };
