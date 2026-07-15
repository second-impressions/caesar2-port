"""Verification registry for the codegen RULES in docs/watcom-codegen-patterns.md.

Each rule asserts (a) an OBSERVATION — a source form maps to a PS codegen shape —
and (b) a MECHANISM — why, usually with an OW-v1 source citation.  The
observations are largely covered by ``tests/oracle/test_rule_NN_*.py`` (they
recompile both forms on the real 10.0a wcc386 and assert the shape).  The
MECHANISMS were never systematically checked against OW v1 / the RE'd 10.0a
binary — and several are wrong (e.g. Rule 1 invoked ``Reg64Order``, which the
allocator never uses; that doc text has been CORRECTED in place).

This registry records, per rule: a one-line ACTIONABLE hint (what to DO when the
pattern shows up in a diff), the verification verdict, the confirmed/corrected
mechanism, and citations.  Status values:

  * "verified"  — observation holds AND the cited mechanism matches OW v1 / RE.
  * "corrected" — observation holds, but the doc MECHANISM was wrong and has been
                  CORRECTED in docs/watcom-codegen-patterns.md; ``mechanism``
                  gives the real cause.
  * "debunked"  — the observation itself does not hold on 10.0a (rare).
  * "unreviewed"— not yet checked here.

The ``hint`` is the deliverable the decompiler reads; everything else is
provenance.
"""
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class RuleVerdict:
    rule: str            # "1", "5b", "28b", ...
    title: str
    status: str          # verified | corrected | debunked | unreviewed
    hint: str            # ACTIONABLE: "if you see X in the diff -> do Y"
    mechanism: str = ""  # the confirmed/corrected cause
    ow_v1: str = ""      # OW v1 source citation
    re_10_0a: str = ""   # 10.0a binary / native-trace evidence
    oracle: str | None = None  # tests/oracle/... that checks the observation
    # Instrumentation feed: some hints can only give the SPECIFIC fix for THIS
    # function by reading what the instrumented 10.0a compiler actually did.
    # ``instrumentation`` names the trace signal + the patch_trace hook (and
    # whether that hook exists yet); ``static`` rules are fully determined by
    # the diff alone.
    instrumentation: str = ""   # "" => static (diff-only); else trace signal needed
    # Universality tier.  ``universal`` rules are DETERMINISTIC: a front-end /
    # optab / addressing decision maps source->bytes with no allocator
    # involvement, so the lever ALWAYS reproduces PS's shape.  Non-universal
    # rules depend on register pressure, conflict-allocation ties, CSE/value-pool
    # decisions, or the per-TU optimizer queue -- none fully controlled by the
    # local source shape; ``caveat`` says exactly when/why the rule fails to hold.
    universal: bool = True
    caveat: str = ""


# Ordered by rule number.  Append verdicts as each rule is reviewed.
VERDICTS: list[RuleVerdict] = [
    RuleVerdict(
        rule="1",
        title="Use a global twice inline rather than caching it in a local",
        status="verified",
        hint="PS prologue `push ebx` (not `push edx`) for a global held across "
        "uses -> READ THE GLOBAL INLINE at every use site, no local. PS `push "
        "edx` -> use an explicit `int t = g;` local. All-or-nothing: one local "
        "read collapses the whole value back to the temp pool.",
        mechanism="Inline/CSE reads are RISCified: the load's register is the "
        "FindRegister rover pick (the value is never a GiveBestReg conflict) and "
        "with EAX held by the parm the rover lands on EBX. A NAMED local routes "
        "through GiveBestReg over DoubleRegs and lands on EDX (EAX taken). "
        "Reg64Order is NOT the integer order (it's debug-only via Low64Reg).",
        ow_v1="FindRegister i86ldstr.c (rover); GiveBestReg/RegSets regalloc.c; "
        "MustSaveRegs i86reg.c:272 (HW_FULL & ~modify & ~(parm|ret) & ~stack).",
        re_10_0a="wcc386 FindRegister@0x62a29 (RoverDouble@0x80710 over "
        "DoubleRegs@0x79850), GiveBestReg@0x57b78 -- both decompiled+confirmed. "
        "trace: named-local alloc=[EAX:6,EDX:3]; inline=[EAX:6]+3 fr rover recs.",
        oracle="tests/oracle/test_rule_01_inline_reads.py",
        instrumentation="INSTRUMENTED: which path the global took is read from "
        "the live trace -- `fr` rover hook (0x62a29) vs `al` GiveBestReg hook "
        "(0x57ed8). decomp-verify's `regalloc (actual 10.0a)` line shows the real "
        "picks for THIS function; if the global appears in `al` (a conflict) it "
        "went the named-local path, if only in `fr` it was RISCified."),
    RuleVerdict(
        rule="2", title="Pre-load a global into a named local before dividing",
        status="verified",
        hint="`dst = g/k` whose result feeds a downstream call shows EAX-first "
        "(`a1` mov eax,[g]); PS wanted EDX-first -> materialise `int t = g; dst = "
        "t/k;` (the named temp lands on EDX, locking PS's idiv setup).",
        mechanism="Named `int t=g;` -> GiveBestReg over DoubleRegs -> EDX (EAX is "
        "the divide result). Bare `g/k` consumed by a call scores EAX-first via "
        "the 5-byte `a1` mov eax,[imm32] savings. Consistent with DoubleRegs RE.",
        ow_v1="RG_DBL_DIV rg.h:62 (RL_EDX_EAX pair); R_MOVOP2TEMP->RG_DBL_DIV "
        "386table.c:685; named temp -> AssignConflicts->GiveBestReg (NOT the "
        "x87-only AssignARegister regalloc.c:896).",
        re_10_0a="DoubleRegs GiveBestReg order EAX,EDX,EBX,ECX,.. (native trace).",
        oracle="tests/oracle/test_rule_02_preload_dividend.py",
        instrumentation="INSTRUMENTED: the dividend temp's register comes from the "
        "`al` GiveBestReg hook -- read the `regalloc (actual 10.0a)` line to see "
        "whether the dividend is on EDX (PS idiom) or EAX."),
    RuleVerdict(
        rule="3", title="Two assignment statements to a global emit two stores",
        status="verified",
        hint="Two `mov [g],reg` to the same global spanning a compute -> write "
        "TWO assignment statements (`g = a; g /= k;`), NOT one fused `g = a/k;` "
        "(which stores once).",
        mechanism="CheckUseful marks any instruction whose RESULT is N_MEMORY/"
        "N_REGISTER as unconditionally useful, so dead-store elimination never "
        "drops a global store (no alias analysis). Each source `=` to the global "
        "-> one `mov [g],reg`.",
        ow_v1="CheckUseful insdead.c:283 (`res class N_MEMORY(1)||N_REGISTER(3) "
        "=> MarkOpsUseful; return`), gated by SideEffect.",
        re_10_0a="wcc386 CheckUseful@0x5873d decompiled+confirmed: result@+0x30, "
        "class@+4, the 1||3 keep is verbatim; SideEffect@0x58676, MarkUseful@"
        "0x586a9, MarkOpsUseful@0x5870f (INS_VISITED=ins[0x40]|1). Annotated.",
        oracle="tests/oracle/test_rule_03_pre_divide_store.py"),
    RuleVerdict(
        rule="4", title="Watcom preserves </<=/>/>= literally (+ cmp,0->test)",
        status="verified",
        hint="Match PS's cmp-immediate + Jcc to the SOURCE operator exactly: "
        "`x<26` (cmp 0x1a;jge) != `x<=25` (cmp 0x19;jg). For a register vs literal "
        "`0`, write `0` to get the 2-byte `test reg,reg` (memory stays `cmp [g],0`)",
        mechanism="Six distinct OP_CMP_* opcodes, no relational normalisation; "
        "each maps to a fixed Jcc. Operand swap (`a<b` vs `b>a`) is RevBranch[]. "
        "`cmp reg,0`->`test` is the V_OP2ZERO optab shortcut (R,C row only).",
        ow_v1="RevBranch[] revcond.c:50-58 (verbatim); OP_CMP_* opcodes.h:136-142; "
        "V_OP2ZERO 386table.c Cmp4 (R,0->G_TEST).",
        re_10_0a="wcc386 RevCond@0x68007 (`ins->opcode=RevBranch[opcode]`, table "
        "@0x7bd98) decompiled+confirmed: EQ/NE identity, GT(0x32)<->LT(0x34), "
        "LE(0x33)<->GE(0x35). 10.0a OP_CMP opcodes pinned EQ=0x30..GE=0x35. "
        "Annotated. 22 oracle assertions.",
        oracle="tests/oracle/test_rule_04_operator_preservation.py"),
    RuleVerdict(
        rule="5", title="Signed division by power-of-2 uses sar;shl;sbb idiom",
        status="verified",
        hint="When PS shows the `sar 31; shl N; sbb; sar N` idiom, write the plain "
        "`x / 2^N` — do NOT use the portable ternary-bias `(x<0?x+k:x)>>N` (it "
        "compiles to a longer BRANCHED sequence).",
        mechanism="Unsigned pow2 divides tree-fold to `>>N` early. Signed pow2 "
        "route through the Div optab: V_OP2TWO(==2)->G_DIV2 (By2Div) beats "
        "V_OP2POW2(any pow2)->G_POW2DIV (sar;shl;sbb;sar).",
        ow_v1="Div4 dword rows 386table.c:682-683 (V_OP2TWO->G_DIV2 BEFORE "
        "V_OP2POW2->G_POW2DIV; verified verbatim). FoldDiv treefold.c:670 "
        "(unsigned pow2 fold at :724 -> O_RSHIFT); GetLog2 :195. Emitters "
        "Pow2Div/By2Div in i86enc32.c:848/:886.",
        re_10_0a="wcc386 Pow2Div@0x4f205, By2Div@0x4f2b9, GetLog2@0x51ac4 "
        "decompiled+confirmed (opwords 0xe2c1/0xc21b/0xf8c1 and 0xc22b/0xf8d1 "
        "match OW v1 byte/word/dword paths verbatim). Helpers LayOpword@0x50756, "
        "AddByte@0x50086, AdvanceCode@0x4f402, OpndSizeIf@0x4e6fd annotated. "
        "13 oracle assertions.",
        oracle="tests/oracle/test_rule_05_signed_pow2_divide.py"),
    RuleVerdict(
        rule="5b", title="PS bare arithmetic shift where source has /2^N",
        status="verified",
        hint="PS shows a bare `sar/shr reg,N` with NO sign-bias -> the source "
        "wrote `x >> N`, not `x / 2^N`. Use `>>` (faithful for non-negative "
        "coords/counters). EXCEPT when the value shares its load with a `& "
        "(2^N-1)` parity sibling — leave `/2` there.",
        mechanism="The source OPERATOR selects: signed `/2^N` rounds toward zero "
        "so the back-end inserts the bias idiom; signed `x>>N` is a single bare "
        "`sar` (no bias).",
        ow_v1="Same Div optab as Rule 5; `>>` is O_RSHIFT.",
        re_10_0a="adjust/de_toggle_all_icons closed via `>>4`.",
        oracle=None),
    RuleVerdict(
        rule="5c", title="adjacent %2^N and /2^N share divisor -> both idiv",
        status="verified",
        hint="PS does a real `idiv` for a `/2^N` sitting next to a `%2^N` of the "
        "SAME value -> keep `/2^N` (do NOT switch to `>>`); the shared divisor "
        "temp defeats strength reduction. Context-dependent (CSE/pressure).",
        mechanism="MOD optab has NO pow2 rule (always idiv); when `%2^N` "
        "materialises the divisor into a temp and CSE shares it with the `/2^N`, "
        "the divide's op2 is no longer a literal so V_OP2TWO/V_OP2POW2 fail and "
        "the divide also goes to idiv.",
        ow_v1="Div4 dword V_OP2TWO/V_OP2POW2 rows at 386table.c:682-683; Mod4 "
        "dword has NEITHER -- only `V_NO R_MOVOP2TEMP` (verified verbatim). "
        "V_OP2TWO/V_OP2POW2 verifiers at verify.c:232,236 REQUIRE op2->c."
        "const_type == CONS_ABSOLUTE -- a CSE-shared divisor temp is N_TEMP and "
        "both verifiers fall through to the idiv path.",
        re_10_0a="get_region_2x2_start: PS shares `mov edi,2`+two idiv.",
        oracle=None),
    RuleVerdict(
        rule="6", title="Split compound division into two assignment statements",
        status="verified",
        hint="Two `idiv` with an intermediate `mov [g],eax` between -> write two "
        "statements (`g = a/12; g /= 100;`), NOT the chained `(a/12)/100` (one "
        "store).",
        mechanism="Rule 3 applied to divides: each source `=` to the global "
        "survives via CheckUseful's N_MEMORY keep.",
        ow_v1="CheckUseful insdead.c:283 / wcc386 0x5873d (see Rule 3).",
        re_10_0a="four *_tax_estimate funcs; +6b per extra store.",
        oracle="tests/oracle/test_rule_06_split_compound_division.py"),
    RuleVerdict(
        rule="7", title="Source order of global stores is preserved verbatim",
        status="verified",
        hint="The order of `mov [g],reg` vs `mov ebx,reg` (value into global vs "
        "callee-save) follows SOURCE statement order — write the two assignments "
        "in PS's order. A swapped `xor reg,reg` init pair -> swap the local decls.",
        mechanism="CGAssign runs once per `=` statement in source order; no "
        "reordering of side-effecting results, both survive (CheckUseful). "
        "`xor reg,reg` order follows DECL order (CDecl1Init, same path).",
        ow_v1="CGAssign intrface.c:911 / wcc386 0x2ef2c (-> TGAssign 0x410d4 -> "
        "DoTGAssign 0x41098 builds TN_ASSIGN tree node); CDecl1Init cstmt2.c; "
        "CheckUseful insdead.c:283 / wcc386 0x5873d.",
        re_10_0a="adjust_peace_criteria; get_new_sslot xor order.",
        oracle="tests/oracle/test_rule_07_global_store_order.py"),
    RuleVerdict(
        rule="7b", title="Split +=1 from the add -> inc + load/add/store",
        status="verified",
        hint="PS `add reg,[g]; inc reg; mov [g],reg` (compact) -> write ONE "
        "expression `g = g + x + 1`. PS `inc reg; mov r2,[g]; add r2,reg; mov "
        "[g],r2` -> two statements `x++; g += x;` (the inverse of Rule 7).",
        mechanism="Two statements cannot merge across the boundary (separate "
        "CGAssign IR). The fused expression is one tree -> Add4 `(R,M,EQ_R1)->"
        "G_RM2` compact `add reg,[m]`.",
        ow_v1="CGAssign intrface.c:911 / wcc386 0x2ef2c; Add4 386table.c (R,M,EQ_R1->G_RM2).",
        re_10_0a="slave_welfare; fused 4b shorter, avoids push ebx.",
        oracle="tests/oracle/test_rule_07b_inc_separate_from_add.py"),
    RuleVerdict(
        rule="8", title="`char` defaults to unsigned on Watcom 10.0a",
        status="verified",
        hint="PS `movsx` reading a byte field -> declare it `signed char`. PS "
        "`xor+mov` / `mov+and 0xff` -> plain `char` (= unsigned). PS `mov "
        "[esp+N],edx` for a 1-byte parm spill -> the parm was `int`, promote it. "
        "Per-field/per-parm — never a blanket `-j`.",
        mechanism="Plain `char` is unsigned by default; reads zero-extend, "
        "`signed char` sign-extends (movsx). 1-byte parms pass in AL/DL/BL/CL.",
        ow_v1="SetPlainCharType(TYPE_UCHAR) default ctype.c:200; SetSignedChar->"
        "TYPE_CHAR :288. Doc cites :131 — actual :200.",
        re_10_0a="9 oracle assertions.",
        oracle="tests/oracle/test_rule_08_char_unsigned_default.py"),
    RuleVerdict(
        rule="9", title="if-body is fall-through; equivalent forms swap the Jcc",
        status="verified",
        hint="The if-body is ALWAYS the fall-through; PS's Jcc is FlipBranch of "
        "the source test. Choose the if/else form + `!cond` inversion that matches "
        "PS's Jcc: PS `jne`->`if(x==0){A}else{B}`; `je`->`if(x!=0){B}else{A}`; "
        "`jge`->`if(a<b)`; `jl`->`if(a>=b){B}else{A}`; etc.",
        mechanism="if-body laid out as the conditional jump's fall-through; "
        "DoCondJump flips the condition when dest_true==dest_next, so PS's Jcc == "
        "FlipBranch[source operator].",
        ow_v1="FlipBranch[] revcond.c:38-48 (verbatim: EQ<->NE, LESS<->GE, "
        "GREATER<->LE); DoCondJump/FlipCond encode.c:131,153. Distinct from Rule "
        "4's RevBranch[]. Bit-identical v1<->v2.",
        re_10_0a="wcc386 FlipCond@0x68017 (`ins->opcode=FlipBranch[opcode]`, table "
        "@0x7bd90) decompiled+confirmed: EQ(0x30)<->NE(0x31), GT(0x32)<->LE(0x33), "
        "LT(0x34)<->GE(0x35). Annotated. 24 oracle assertions; control_buttons/"
        "strip_spaces landed.",
        oracle="tests/oracle/test_rule_09_if_else_layout.py"),
    RuleVerdict(
        rule="10", title="Staged global RMW instead of a single fused sum",
        status="verified",
        hint="Chain of `mov [g],r; add [g],r; add [g],r` to one global -> write "
        "staged statements (`g = a; g += b; g += c;`). A single final store -> "
        "fuse to `g = a+b+c;`.",
        mechanism="Rules 3/7b composed: each `+=` to the global is a separate "
        "`add [m],reg` (Add4 (M,R,M,EQ_R1)->G_MR2, CheckUseful keep).",
        ow_v1="Add4 G_MR2 386table.c:147; CGAssign intrface.c:911 / wcc386 0x2ef2c; "
        "CheckUseful insdead.c:283 / wcc386 0x5873d.",
        re_10_0a="adjust_proserity_criteria; -5b for 3->1.",
        oracle="tests/oracle/test_rule_10_staged_global_rmw.py"),
    RuleVerdict(
        rule="11", title="Pre-increment + cache pattern for loop sentinels",
        status="verified",
        hint="PS uses 8-bit `cmp dl,ah` on a pre-incremented sentinel -> write "
        "`cur++; best=cur; ...; if(best==cur)`, NOT `best=cur+1; ...; "
        "if(best==cur+1)` (which recomputes `cur+1` at int width with zero-"
        "extends + a 32-bit cmp).",
        mechanism="`cur++` materialises cur (incremented) in a register reused by "
        "`best=cur`/`best==cur`; the fused `cur+1` recomputes a temp at the "
        "compare and C int-promotion forces 32-bit width.",
        ow_v1="CGAssign per-statement intrface.c:911 / wcc386 0x2ef2c.",
        re_10_0a="trace_back_ferret; pre-inc >=4b shorter.",
        oracle="tests/oracle/test_rule_11_preinc_cache_loop_sentinel.py"),
    RuleVerdict(
        rule="12", title="Data-pointer literals look like immediate dwords",
        status="verified",
        hint="PS shows `mov reg, ?? ?? ?? ??` (all 4 immediate bytes are fixups) "
        "-> the argument is the ADDRESS of a labelled data symbol: pass "
        "`(int)&sym` (or a typed global name), NOT an int constant (which emits "
        "`b8 40 a3 01 00` with no fixup and won't match).",
        mechanism="A labelled symbol reference emits placeholder bytes + an "
        "F_OFFSET fixup; the linker patches the address. The verifier tags fixup "
        "bytes as `??`.",
        ow_v1="Fixup emission in the x86 escape layer (OutCodeDisp; file renamed "
        "from the cited x86esc.c).",
        re_10_0a="lead_in_logos; integer literal has 0 fixup bytes vs 4.",
        oracle="tests/oracle/test_rule_12_data_pointer_literals.py"),
    RuleVerdict(
        rule="13", title="Per-branch vs hoisted shared call",
        status="verified",
        hint="If each PS branch loads ALL N args (incl. constants repeated in "
        "every branch) before the merged `call;ret` -> write a per-branch call in "
        "each arm (`if(z==0) f(&a,dst,sz,0);`). If branches load only the VARYING "
        "args -> hoist the call past the if-tree. Both tail-merge; the diff is "
        "WHERE the constant-arg loads live.",
        mechanism="ComTail merges the common `call;ret` suffix of both forms "
        "equally; the per-branch form just materialises the shared args inside "
        "each arm. (The doc's earlier 'extra spills' note was already corrected.)",
        ow_v1="ComTail optcom.c:185 (OptForSize<25 guard :214); args pushed in "
        "the AST walk OPR_PARM (cgen.c).",
        re_10_0a="swap_circus_gfx 6 readfile branches each load edx,ecx const.",
        oracle="tests/oracle/test_rule_13_call_hoist_vs_per_branch.py"),
    RuleVerdict(
        rule="27", title="Instruction-pair reorder via parm-alias toggle",
        status="verified",
        hint="Two adjacent entry parm-copy `mov`s in OPPOSITE order vs PS -> "
        "toggle the alias decision: either introduce a named local aliasing the "
        "parm (`int cap = value;` then use cap) OR mutate the parm directly "
        "(`if(value<0) value=0;`). Pick the form whose mov order matches PS.",
        mechanism="A named local aliasing a parm becomes its own virtual name "
        "with its own savings, shifting GiveBestReg's processing order, hence the "
        "order of the entry parm-copy movs. Same family as Rules 24/28.",
        ow_v1="GiveBestReg/AssignARegister regalloc.c (conflict-order driven).",
        re_10_0a="city_pop_limit_10_to_1 byte-exact via removing `int cap=value`.",
        oracle="tests/oracle/test_rule_27_instruction_pair_reorder.py",
        instrumentation="INSTRUMENTED: the parm-copy order follows the conflict "
        "allocation order from the `al` hook; `regalloc (actual 10.0a)` shows "
        "whether the alias local got its own conflict."),
    RuleVerdict(
        rule="14", title="Bare ret (no EAX preload) means the function returns void",
        status="verified",
        hint="PS shows a bare `ret` (or `pop..;ret`) with NO `mov eax`/`xor "
        "eax,eax` before it -> declare the function `void`, even if call sites "
        "look like they read the return (they read leftover register state).",
        mechanism="CGReturn(NULL,...) skips the TGReturn that would emit the "
        "EAX-load IR; BGReturn(NULL) emits the bare ret. `return 0;`->`xor "
        "eax,eax`, `return 1;`->`mov eax,1`.",
        ow_v1="cgen.c:287-296 (SYM_NULL -> CGReturn(NULL)); CGReturn intrface.c:674.",
        re_10_0a="show_pl8file family; int->void drops the eax-set bytes.",
        oracle="tests/oracle/test_rule_14_void_return.py"),
    RuleVerdict(
        rule="15", title="Cross-function tail-merge within a TU",
        status="verified",
        hint="PS small wrappers that set globals then `jmp` into a shared "
        "epilogue -> decompile the MERGE TARGET (the FIRST function in source "
        "order carrying that epilogue) BEFORE its siblings, so Watcom can "
        "back-jump into the stub. A non-reproducing FAR merge means the family "
        "is NOT fully decompiled in PS's source order (donor or an intervening "
        "function is still a stub, or the order differs) -- decompile the whole "
        "family in order; it WILL reproduce.",
        mechanism="ComTail merges the longest common ret-suffix. On x86 "
        "FlushQueue is gated to NEW_P5_PROFILING so RetList accumulates across the "
        "WHOLE TU and is never evicted (its only eviction path, FlushSomeOpt->"
        "ShrinkQueue, runs only on memory starvation, which never occurs here). "
        "So every within-TU far-merge is reproducible given the decompiled family "
        "in source order; distance is irrelevant.",
        ow_v1="ComTail optcom.c:185 (gate OptForSize<25 :214); RetList optdata.c; "
        "FlushQueue gate generate.c:331-336; ShrinkQueue<-FlushSomeOpt "
        "memlimit.c:75. Matches watcom10.0a docs/tail-merge.md RE.  "
        "FindCommon compares raw OBJECT CODE, so ComTail merges ANY identical "
        "suffix -- epilogues AND whole call sequences (the 58 corpus "
        "`mov edx,K; mov eax,M; jmp <shared call tail>` arg-pair sites: "
        "get_census/get_new_tribute/show_* UI panels).",
        re_10_0a="map.c: of PS's 453 function-final far-merges the build "
        "reproduces every family that is decompiled+ordered; misses track "
        "un-decompiled members, not a memory ceiling.",
        oracle=None),
    RuleVerdict(
        rule="16", title="Short-vs-near jmp encoding cascade",
        status="verified",
        hint="A 1/3-byte diff at a tail-merge jmp where PS has `e9 ....` (5b near) "
        "and recomp has `eb ..` (2b short) -> DECOMPILE THE INTERMEDIATE STUBS so "
        "the jmp distance crosses ~127 and both pick the near form. Not a source-"
        "shape choice in the wrapper itself; +3b per flip.",
        mechanism="optrel.c walks from the jmp to its target summing _ObjLen; <= "
        "MAX_SHORT_FWD(127)/BWD(126) -> short eb, else near e9.",
        ow_v1="MAX_SHORT_FWD 127 / MAX_SHORT_BWD 126 ocentry.h:198-199; optrel.c.",
        re_10_0a="act_tower family 1-byte diffs.",
        oracle="tests/oracle/test_rule_16_jmp_short_vs_near.py"),
    RuleVerdict(
        rule="17", title="Flag-mask split-RMW emits an extra register copy",
        status="verified",
        hint="PS shows `mov rl2,rl1` between the AND and the OR at a flag-update "
        "(`...&MASK ...|BITS`) -> write TWO statements `x &= MASK; x |= BITS;`. A "
        "tight 4-instruction AND/OR with one register -> write the COMBINED `x = "
        "(x & MASK) | BITS;`.  **CRUCIAL CAVEAT**: when the source has an "
        "intermediate temp `unsigned char s = X & MASK; X = s; ... X = s | BIT;` "
        "you MUST remove `s` and use direct `X &= MASK; ... X |= BIT;` -- the "
        "temp prevents the (M,C,M,EQ_R1) optab row from matching because op1 is "
        "an N_TEMP at codegen time, not the memory location.  See Rule 17b.",
        mechanism="Each `&=`/`|=` is its own TN_PRE_GETS statement; the back-end "
        "keeps the post-AND value observable in a 2nd register across the "
        "statement boundary. The combined single expression folds AND/OR into one "
        "register (no boundary).",
        ow_v1="cgen.c:1357-1369 (OPR_AND_EQUAL/OR_EQUAL -> CGPreGets); "
        "DoTGPreGets tree.c:1102; CheckUseful keeps plain-global stores (Rule 3).",
        re_10_0a="sa01_wait; struct-field SPLIT 5 insns vs COMBINED 4.",
        oracle="tests/oracle/test_rule_17_flag_mask_split_rmw.py"),
    RuleVerdict(
        rule="17b",
        title="Intermediate temp blocks the AND/OR direct-memory-RMW optab row",
        status="verified",
        hint="When the source has `s = X & MASK; X = s; ... X = s | BIT;` (a "
        "named temp re-used across multiple `X = s | ...` statements), the AND "
        "doesn't fold into an `and [m], imm` -- it goes through a register temp "
        "and emits `mov reg,[m]; and reg, imm; mov [m], reg` PLUS one `mov reg,"
        "[m]` per subsequent `X = s | BIT`.  **REMOVE the temp `s`** and use "
        "`X &= MASK;` plus direct `X |= BIT;` in each branch -- each statement "
        "then matches the `(M, C, M, EQ_R1) -> G_MC` optab row and emits direct "
        "`and [m], imm` / `or [m], imm`.  Saves the temp load + the temp store "
        "per branch.",
        mechanism="The OW v1 optab tables (386table.c:519 And4, 414 Or4) have a "
        "row `_BinSC(M, C, M, EQ_R1), V_NO, G_MC, RG_, FU_ALUX` that matches IFF "
        "the OP_AND / OP_OR ins has op1 == result == same N_MEMORY name AND op2 "
        "== N_CONSTANT.  The source `X &= MASK;` produces exactly this IR shape "
        "(the front end builds TN_PRE_GETS with the memory location reused as "
        "both op1 and result).  But `s = X & MASK; X = s;` builds the AND as "
        "OP_AND(t1=LOAD(X), op2=MASK, result=t2) -- op1 and result are TEMPS, "
        "not MEMORY -- the M,C,M,EQ_R1 row doesn't match, so the matcher falls "
        "through to (R, C, R, EQ_R1) -> G_RC, requiring the value in a register.",
        ow_v1="And4 row 5 (M, C, M, EQ_R1) -> G_MC at 386table.c:519; Or4 row 5 "
        "at 386table.c:414.  G_MC emitter at i86enc.c:871 "
        "(LayModRM(left) + AddSWCons(opcode, right, type_class)).",
        re_10_0a="wcc386 GenObjCode @ 0x4f894 (1787b); switch jump table "
        "@ 0x4f704 indexed by gen_class-1; G_MC handler @ 0x4f965 "
        "(`mov eax,ebx ; call LayModRM@0x4ec0a ; jmp common-tail @ 0x4f934 -> "
        "call AddSWCons@0x50369`).  evolver.c market_image: SPLIT-via-`s` "
        "produced 113b diff; removing `s` -> 0b (byte-exact).  **Corpus-wide "
        "AST scan** (c2.commands.rule_pattern_scan): 0 instances of the source "
        "pattern remain across 1444 indexed functions; guard test "
        "test_rule_17b_pattern_stays_gone_corpus_wide ensures the pattern can't "
        "regress without a CI failure.",
        oracle=None),
    RuleVerdict(
        rule="18", title="Lazy per-branch computation, not pre-computed temps",
        status="verified",
        hint="Under HIGH register pressure, PS materialises `arg+offset` "
        "per-branch as `mov reg,arg; add reg,K` (5b), not `lea reg,[arg+K]` (3b) "
        "-> write the offset INLINE in each branch (`field=(short)(arg+0x1B);`), "
        "NOT as a pre-computed temp. (Low pressure: both emit LEA, no diff.)",
        mechanism="The LEA-vs-(mov+add) choice is the V_LEA verifier in the Add4 "
        "optab, gated by whether the operands land in LEA-foldable registers — "
        "register-pressure-dependent. A pre-computed temp at the arg-save level "
        "lets the back-end fold to LEA; per-branch scoping forces the 2-step form.",
        ow_v1="Add4 V_LEA->G_LEA row 386table.c (vs G_RM2/mov+add).",
        re_10_0a="get_rioter_image (EBX+ECX+EDX saved -> mov+add per branch).",
        oracle="tests/oracle/test_rule_18_lazy_per_branch.py"),
    RuleVerdict(
        rule="19", title="char vs int parameter spill width (sub-case of 8)",
        status="verified",
        hint="Read the parm SPILL width: `mov byte ptr [esp+N],al` -> `char`; "
        "`push eax` (1st parm) or `mov [esp+N],edx` (multi) -> `int`; byte spill "
        "+ `movsx` reload -> `signed char`. 19a: a 5th+ STACK-passed byte parm "
        "should be `char` (frees the upper 3 bytes of its register for reuse) and "
        "be used only as a byte.",
        mechanism="Same as Rule 8 (char unsigned default; 1-byte parms in AL/DL/"
        "BL/CL). `mov bl,[m]` leaves ebx[31:8] free for scratch; `mov ebx,[m]` "
        "locks ebx and cascades the allocation.",
        ow_v1="SetPlainCharType ctype.c:200 (see Rule 8).",
        re_10_0a="set_rm_range 184b->0b via `char field_offset`+`char kind_byte`.",
        oracle="tests/oracle/test_rule_08_char_unsigned_default.py"),
    RuleVerdict(
        rule="20", title="Loop-counter terminal value as the final index",
        status="verified",
        hint="A post-loop array access at the TERMINAL index -> use the LOOP "
        "VARIABLE (`arr[i].f = v;` after `for(i=0;i<7;i++)`), NOT the literal "
        "`arr[7].f` (which emits an absolute displacement `[disp]` instead of the "
        "loop's `[eax*8+off]` and is a few bytes shorter).",
        mechanism="IV analysis tracks the counter; a post-loop reference keeps it "
        "register-resident at the terminal value, and address folding reuses the "
        "loop's `[reg*scale+disp]` mode. A literal index loses the IV link and "
        "computes the absolute displacement at compile time.",
        ow_v1="IndVarList loopopts.c:91; address folding in the x86 escape layer.",
        re_10_0a="slave_requirements post-loop store keeps [eax*8].",
        oracle="tests/oracle/test_rule_20_loop_terminal_index.py"),
    RuleVerdict(
        rule="21", title="Indexed-array folding only at the deref site",
        status="verified",
        hint="A non-power-of-2-stride array store -> write the FULL address in the "
        "deref: `*(short*)((char*)base + idx*70 + 4) = v;`. Do NOT pin it through "
        "a local pointer first (`short *row = ...; *row = v;`) -- that materialises "
        "base and the +offset as two separate `add`s (+4 bytes).",
        mechanism="The addressing-mode synthesiser folds base+index*scale+disp "
        "into one `[reg+disp]` mode only when all three are visible at the deref. "
        "A local pointer holds the fully-computed address, leaving nothing to fold.",
        ow_v1="OutMem* addressing synthesis in the x86 escape layer.",
        re_10_0a="set_ambient_minimum; via-local 4b longer (2 extra add).",
        oracle="tests/oracle/test_rule_21_indexed_array_folding.py"),
    RuleVerdict(
        rule="22", title="Stub signatures must match real arg widths",
        status="verified",
        hint="PS caller shows `mov eax,K; call X` (10b) -> declare the stub `void "
        "X(int)` (with the arg), NOT `void X(void)` (which makes a 5b call site "
        "and under-shoots). The body can be empty; the prototype drives the call "
        "bytes.",
        mechanism="The front-end emits OPR_PARM IR per actual arg only if the "
        "prototype declares params; the back-end trusts the prototype for the "
        "call-site, blind to the (possibly empty) body.",
        ow_v1="OPR_PARM cgen.c:1530-1532; CGAddParm.",
        re_10_0a="int_c2 state-handler family.",
        oracle="tests/oracle/test_rule_22_stub_signatures.py"),
    RuleVerdict(
        rule="23", title="signed char field, no (char) cast (sub-case of 8)",
        status="verified",
        hint="PS reads a struct field with `movsx` but recomp emits `mov al; and "
        "eax,0xff` -> declare that field `signed char` (in the header) and DROP "
        "any `(char)` cast at the read site (the cast forces zero-extend). "
        "Per-field, not a global sweep.",
        mechanism="Plain char is unsigned (zero-extend); signed char sign-extends "
        "(movsx). A `(char)` cast forces the default unsigned promotion.",
        ow_v1="SetPlainCharType ctype.c:200 (see Rule 8).",
        re_10_0a="state_idx etc.; oracle test_signed_char_global_uses_movsx.",
        oracle="tests/oracle/test_rule_08_char_unsigned_default.py"),
    RuleVerdict(
        rule="24", title="Spill-via-local: force a stack slot for an argument",
        status="verified",
        hint="PS spills a DIFFERENT arg to a named `[esp+N]` slot than recomp (no "
        "Rule fires; same byte budget, wrong register at the use site) -> "
        "introduce a named local aliasing the arg PS spills (`int hi_x = xmax;`) "
        "and read it at the matching use site, forcing that arg onto its own slot.",
        mechanism="The allocator's spill-victim (InMemory) choice depends on arg "
        "decl order, first-use order, and whether the value is an initializer RHS. "
        "A named local gets its own conflict/savings, flipping the victim. Same "
        "GiveBestReg/AssignConflicts family as Rules 27/28.",
        ow_v1="GiveBestReg/AssignConflicts InMemory selection regalloc.c.",
        re_10_0a="mouserange xmax spill via `int hi_x=xmax`.",
        oracle=None,
        instrumentation="INSTRUMENTED: which arg is the spill victim (InMemory) "
        "and the savings come from the `al`/`gb` hooks. `c2 regtrace <fn> --native` "
        "lists each conflict's reg/savings/InMemory; the victim that differs from "
        "PS is the one to pin with a named local."),
    RuleVerdict(
        rule="25", title="byte-offset access vs cell-index access for typed arrays",
        status="verified",
        hint="PS uses `mov dl,[reg+base+N]` for a typed-array field where the BYTE "
        "offset is already in a register -> write the byte-offset cast "
        "`((struct cell*)((char*)arr + ref))->field`, NOT `arr[cell].field` (which "
        "emits the SIB shift+add strength-reduction form, +16b). Unroll loops in "
        "SOURCE -- PS was NOT compiled with -ol+ (it regresses ~28 funcs).",
        mechanism="Same addressing-mode synthesis as Rule 21: O_PTR(O_PLUS(base,"
        "ref)) folds base(fixup disp)+ref(reg)+field(disp) into one mode. "
        "`arr[cell].f` is O_PTR(O_PLUS(O_TIMES(cell,20),base),1) and without -ol+ "
        "emits the mul as shift+add+SIB.",
        ow_v1="OutMem* addressing synthesis (see Rule 21); -ol+ togglable only "
        "globally (CGUIDE: only unreferenced/check_stack are pragma-switchable).",
        re_10_0a="check_citizen_list/clear_all_cm; -ol+ regresses ~28 funcs.",
        oracle="tests/oracle/test_rule_25_byte_offset_vs_cell_index.py"),
    RuleVerdict(
        rule="26", title="Two call statements vs one call with a ternary arg",
        status="verified",
        hint="PS shows two `mov edx,imm` (per branch) feeding a register call-arg, "
        "tail-merged at the `call`, where recomp emits `sete dl; and edx,0xff` -> "
        "write TWO distinct call statements in if/else (`if(c) f(i,1); else "
        "f(i,0);`), NOT a ternary arg `f(i, c?1:0)`.",
        mechanism="A `?:` sub-expression materialises the bool first (cheap sete "
        "under -4r), collapsing the branch. Two separate calls keep the branch and "
        "ComTail-merge the shared `call`. PS has only 52 setcc in the whole binary.",
        ow_v1="ComTail optcom.c:185 (tail-merge); sete from the bool materialise.",
        re_10_0a="explain_forum; detect_rule_26 auto-flags recomp setcc.",
        oracle="tests/oracle/test_rule_26_two_calls_vs_ternary.py"),
    RuleVerdict(
        rule="28", title="Whole-function callee-save register swap",
        status="verified",
        hint="PS pushes one callee-save where recomp pushes another (same count; "
        "e.g. ESI<->EDI everywhere a long-lived value lives) = a GiveBestReg "
        "equal-savings tie on the 4th/5th simultaneously-live int value. LEVER 1: "
        "commute a use so PS's value is referenced FIRST (`dest_x + dest_y*80` "
        "instead of `dest_y*80 + dest_x`). LEVER 2 (Rule 115): swap the two tied "
        "locals' DECLARATIONS (try both orders). Use-count/savings outranks both. "
        "CSE-hoisted-global swaps are genuine residue (no source handle).  "
        "MEASURED (set_current_cohort_totals, 2026-06-10): cn creation slots "
        "follow DECLARATION order; reordering the ASSIGNMENT statements has NO "
        "effect on cn slots or seats -- decl order is the only slot lever for "
        "locals.  Multi-way rotations decompose into pairwise decl swaps walked "
        "one at a time against the PS-alloc replay (12b -> 6b -> exact).",
        mechanism="GiveBestReg walks DoubleRegs (EAX,EDX,EBX,ECX,ESI,EDI,EBP) "
        "picking max CountRegMoves; on a tie it prefers an already-pushed "
        "(GivenRegisters) register. The conflict-allocation ORDER (ConfBefore: "
        "savings then name-pointer/creation order) decides which value allocates "
        "first; commuting a use or swapping decls reorders it.",
        ow_v1="GiveBestReg tie-break regalloc.c:854-858 (saves==best && HW_Subset"
        "(GivenRegisters,reg)) -- VERIFIED verbatim; DoubleRegs NOT Reg64Order.",
        re_10_0a="change_citizen_targs 0b via `dest_x+dest_y*80`; show_help_page "
        "0b via swapping text_lines/text_x decls (Rule 115).",
        oracle="tests/oracle/test_rule_28_callee_save_swap.py",
        instrumentation="INSTRUMENTED: the tied pair, their equal savings and the "
        "allocation order are read from the `al` (GiveBestReg) + `gb` (savings) "
        "hooks. decomp-verify's `regalloc (actual 10.0a)` + `Regalloc:` lines name "
        "the two tied conflicts so you know WHICH use to commute / decls to swap "
        "-- the hint is incomplete without this per-function data."),
    RuleVerdict(
        rule="28b", title="Asymmetric callee-save push count",
        status="verified",
        hint="PS pushes MORE callee-saves than recomp (or vice versa), same body "
        "role -> if PS has the extra, add a named local capturing the long-lived "
        "value (Rule 24a); if recomp has the extra, remove a named local / split "
        "an expression to cut live-range pressure. Many small math helpers "
        "(totalXpercent) have no fix -- known regalloc residue.",
        mechanism="Same GiveBestReg/DoubleRegs mechanism as Rule 28; the push set "
        "is `MustSaveRegs() & state.used` so a value landing in an extra "
        "callee-save adds its push.",
        ow_v1="DoubleRegs is the int type-class list; GiveBestReg tie-break "
        "regalloc.c:854-858. (Reg64Order is debug-only, not the allocator's.)",
        re_10_0a="totalXpercent ECX divisor push; check_for_promotion.",
        oracle="tests/oracle/test_rule_28_callee_save_swap.py",
        instrumentation="INSTRUMENTED: which value landed in the extra callee-save "
        "(and its savings) is read from the `al` hook; the `Rule 28b`/`Regalloc:` "
        "lines surface the extra-push register for THIS function."),
    RuleVerdict(
        rule="85", title="Far-pointer return type: `return N` lowers to edx:eax (seg:off)",
        status="verified",
        hint="`xor edx,edx; mov eax,N` (or `mov edx,S; mov eax,N`, S!=0) at "
        "an exit = a far-pointer constant return.  binir decodes the EXACT "
        "source: kind farptr_ret_const (followed by local pops+ret -- "
        "certain) or regpair_const_exit (exit jmp -- decomp-verify resolves "
        "the jmp through symbols: RETURN -> the printed `return (char __far "
        "*)MK_FP(S,N);` is the literal source line (S==0 -> plain cast); "
        "ARGS -> it is (eax,edx) watcall args into a ComTail-merged shared "
        "call tail, NOT a return).  Constraints: E1096 forbids mixing bare "
        "`return;` with valued returns (guard-wrapper + fall-off-end "
        "instead); the far* definition needs a prototype before any caller "
        "(E1062 implicit-int); the seg write can be value-pool ELIDED after "
        "a `test reg,reg` proved the reg zero (needs the `int s = ...` "
        "local form); PS pushes/pops EDX in far*-returning functions "
        "anyway (10.0a quirk -- never use the push set to rule far* out).",
        mechanism="BGReturn converts the int constant to the 48-bit far "
        "pair: offset->EAX, segment->EDX.  Corpus census 2026-06-10: 5 "
        "certain returns (pcsound family), 58 arg-pair call-tail merges.",
        ow_v1="ComTail optcom.c:185 / FindCommon (raw object-code suffix "
        "compare) for the stub chains; conversion lowering in the type "
        "convert tables.",
        re_10_0a="start_sequences +0x36 (0,1) / +0x89 MK_FP(1,2) resolved "
        "RETURN; start_samples' return-2 shows the test-elision (no seg "
        "write after `test edx,edx`).  Open IL-level question: the W107 "
        "join-read funnel (retval pair exiled to callee-saves in RC, "
        "per-site EDX:EAX in PS) -- frame_hints.detect_retval_funnel "
        "flags it.",
        oracle="docs/codegen-experiments/farptr_return_mkfp.py (runnable): "
        "MK_FP(1,2) -> mov edx,1; mov eax,2; plain casts -> xor edx,edx; "
        "no 64-bit type in 10.0a; E1096 forbids mixed bare/valued returns.",
        instrumentation="binir farptr_ret_const/regpair_const_exit + "
        "tail_merge.classify_regpair_exit + frame_hints retval funnel."),
    RuleVerdict(
        rule="121", title="Duplicated-tail rover advance (ComTail merges, rover walks twice)",
        status="verified",
        hint="A pure register-identity swap on a RISCified scratch (compare "
        "load `mov reg,[g]; cmp reg,imm` or push scratch) in the SECOND-walked "
        "arm of an if/else-if whose arms share a common tail (call + cleanup) "
        "-> write the shared tail INSIDE EACH ARM.  ComTail merges the "
        "identical tails back to one block of bytes, but LdStAlloc has "
        "already walked the duplicated ops once per arm, advancing the rover "
        "cursor between the arms' scratch picks.",
        mechanism="LdStAlloc walks the BLOCK LIST (creation order, not layout) "
        "forward per block; every Enregister-able op advances the shared "
        "type-class rover via FindRegister EVEN IF LdStCompress CISCifies it "
        "back to zero extra bytes (e.g. `sub reg,[mem]`).  With the tail "
        "duplicated, its rover-advancing ops sit between the two arms in the "
        "block list, so the second arm's scratch lands one register later "
        "(EBX->ECX).  Tail-merge then erases the duplication from the bytes.",
        ow_v1="i86ldstr.c LdStAlloc (HeadBlock->next_block walk, rover reset "
        "per routine), FindRegister rover ++-first; CompressIns keeps the "
        "advance; ComTail (optimize.c) merges the duplicate tails.",
        re_10_0a="print3_test_info + print_test_info byte-exact via duplicated "
        "font_no tail (3b/98b closed); fr-trace simulation: picks EDX,[EBX "
        "coalesced sub],ECX reproduce PS.  LdStAlloc@0x5A43D, "
        "FindRegister@0x62a29, RoverDouble@0x77DB8.",
        oracle=None,
        instrumentation="INSTRUMENTED: the `fr` trace records every rover "
        "advance (with source line); watcom10.0a tools/rover_sim.py replays "
        "the cursor; a +1 injection between the two picks predicts the fix "
        "before editing source."),
    RuleVerdict(
        rule="122", title="if/else ARM ORDER steers the rover walk (block-creation order)",
        status="verified",
        hint="A rover-class register swap (no conflict binding) on an op inside "
        "ONE ARM of an if/else, where the fr walk shows the OTHER arm's ops "
        "advancing the cursor first -> INVERT the condition and swap the arms "
        "(`if (A) X else Y` -> `if (!A) Y else X`).  Emitted bytes are "
        "identical for both arm orders (branch layout + tail-merge are "
        "CFG-driven); only the LdStAlloc walk order moves.",
        mechanism="LdStAlloc walks the BLOCK LIST in front-end creation order, "
        "not layout order.  The burner creates the arms' blocks in source arm "
        "order, so swapping then/else reorders the arms' rover advances "
        "relative to each other while the byte layout (fall-through + "
        "cross-jump/tail-merge) stays fixed.  Sibling of Rule 121 (duplicated "
        "tail): both are block-LIST-order levers over the same FindRegister "
        "cursor.",
        ow_v1="i86ldstr.c LdStAlloc HeadBlock->next_block walk; block creation "
        "in the tree burner follows source arm order.",
        re_10_0a="update_time arena block: `if (pop>=500){++..} else {=0}` walks "
        "the else-store BEFORE the RMW (fr: L229 then L226) -> RMW scratch EBP; "
        "inverted `if (pop<500) =0; else if (++.. > 12) =0;` walks RMW first -> "
        "EDI = PS.  26b -> 22b (rest is donor-blocked epilogue).  Found by "
        "remove/reorder simulation over the fr stream.",
        oracle=None,
        instrumentation="INSTRUMENTED: the fr stream + rover_sim reorder test "
        "(simulate the arms' events swapped) proves the lever before editing; "
        "the generalized Rover hint surfaces the swap and cursor delta."),
    RuleVerdict(
        rule="123", title="in-place compound op MERGES temps -- combined savings reorder the allocation walk",
        status="verified",
        hint="A register-identity swap where PS's pick implies a conflict "
        "allocated EARLIER than its savings suggest (e.g. a byte temp taking "
        "BL before the dword that owns EBX is placed): look for a temp our "
        "source SPLITS into load + result (`char hi = step << 4` or an "
        "rvalue `step << 4`).  Write the IN-PLACE compound form "
        "(`step <<= 4; use step`): the front end keeps load and result in "
        "the SAME temp, the merged conflict's savings are the SUM of the "
        "split temps', and the allocation order flips to PS's.",
        mechanism="CalcSavings totals per-conflict memory-ref savings; "
        "SortConflicts allocates in savings-desc order.  Two split temps "
        "(sav 30 + 20) each rank below a dword local (41); merged via the "
        "in-place op they rank 50 > 41, allocate first, and take the byte "
        "reg whose parent dword reg the loser then cannot use.",
        ow_v1="regalloc.c CalcSavings/SortConflicts; the temp merge is a "
        "front-end IL property (compound assignment reuses the operand "
        "temp).",
        re_10_0a="copy_ferret_run_to_army/_citizen: `step <<= 4` -> step "
        "merges to sav~50, outranks j(41), takes BL, pushes j to ECX = PS.  "
        "Both twins code-exact (161b/154b, ~pad only).  Split forms keep "
        "byte temps 30/20 and j gets EBX first (CL residue).",
        oracle=None,
        instrumentation="al rows carry savings per conflict; the signature "
        "is two same-class temps whose savings SUM exceeds the "
        "diverging-pick owner's savings."),
    RuleVerdict(
        rule="124", title="GiveBestReg pick = argmax CountRegMoves, GivenRegisters tie-break, list order (gb read)",
        status="verified",
        hint="For ANY register-identity/home question, read the al rows' "
        "cand_scores (gb trace): pick = argmax saves; tie -> first candidate "
        "already subset of GivenRegisters; else candidate-list order.  Three "
        "source knobs: (1) SAVINGS ORDER -- loop-bound refs inflate a parm's "
        "savings; accumulate onto the dying parm and COPY (`h = p + r*2; "
        "w = h;`) to kill its loop refs and demote it; (2) HOMING-MOV CREDIT "
        "-- a `MOV <parm-reg> -> <other-conf>` inside this conflict's range "
        "gives +half for that reg even though the MOV is not this "
        "conflict's; (3) GIVEN TIE-BREAK -- zero-score temps stick to "
        "already-Given regs; reorder which temp allocates first by "
        "splitting/merging the statement that creates it.",
        mechanism="GiveBestReg@0x57b78 candidate loop; CountRegMoves@0x57728 "
        "(MOV temp<->reg +size; MOV reading an overlapping N_REGISTER +half; "
        "commutative-op result credit +half; opcode set {1,2,5,9,a,b}); "
        "GivenRegisters accumulates every given reg across the routine.",
        ow_v1="regalloc.c GiveBestReg/CountRegMoves (v1 adds SUPER_OPTIMAL "
        "paths 10.0a lacks; the overlap half-credit checks res in v1 vs op0 "
        "in 10.0a).",
        re_10_0a="change_lv 250b EXACT: delta->ECX (homing credit), "
        "extra->EBP (savings demotion), scratch EAX-vs-EDX (Given tie-break "
        "via nv load/+= statement split).  gb record = CountRegMoves return "
        "hook 0x57c9c.",
        oracle=None,
        instrumentation="INSTRUMENTED: gb record (per-candidate scores) in "
        "alloc rows' cand_scores; bt-minus-gb = masked/TooGreedy-skipped."),
    RuleVerdict(
        rule="126", title="byte-value register seat: zext-overlap / address-temp masks (AL-squat mechanism)",
        status="verified",
        hint="A byte value seated in AL by our build but DL/DH in PS: the "
        "seat is decided by NeighboursUse interference, NOT tie-breaks "
        "(CountRegMoves gives no CONVERT credit).  Two PROVEN mask "
        "vehicles: (1) ZEXT-OVERLAP -- a byte value live ACROSS a separate "
        "`xor eax,eax; mov al,b` extension temp gets EAX masked once that "
        "temp allocates first (a DYING convert use does NOT mask -- the "
        "value needs a second extension use or later last-use); (2) "
        "ADDRESS-TEMP -- the [base] address temp (EAX) masks whichever "
        "byte field is loaded FIRST when a later field load keeps the "
        "address alive.  Levers: test grouping that forces re-extension "
        "(|| groups extend separately; pooled dword compares extend once "
        "in place), field load order, and the conflict's savings rank vs "
        "the EAX temps (allocate AFTER them to be masked).",
        mechanism="NeighboursUse@0x580c0 channel C (live-overlap gate) runs "
        "at GiveBestReg time, so with.regs sees earlier-allocated conflicts "
        "as N_REGISTERs; allocation order = savings order (Rule 124).  "
        "Z1to4 lowering then picks `and reg,0xff` in place when the byte "
        "value sits in the extension's register family, else "
        "`xor;mov al,b`.",
        ow_v1="regalloc.c NeighboursUse (~:1157) -- ALGORITHM GUIDE: "
        "zap+N_REGISTER-dst+live accumulation gated by usage&0x88 / empty id "
        "bits / live-bit overlap; NowAlive/NowDead copy-relation exemption.",
        re_10_0a="PROVED in wcc386 10.0a: NeighboursUse@0x580c0 inits conf->with.regs "
        "(+0x20) at 0x580fc, OP_MOV=0x26 exemption @0x580dc; GiveBestReg EXCLUDES a "
        "with.regs-overlapping candidate at 0x57c50 (GiveBestReg_withregs_gate, "
        "`test [conf+0x20],reg`).  get_industry_ov_image: with the proven ||-form, "
        "kind's withregs gains the A-bits (0x..03) and kind lands asm-DL = PS; "
        "load-order swap flips industry<->kind symmetrically (address-temp "
        "vehicle).  are_overlays_on: same family; line cues recovered the "
        "exact layout.  Helpers grounded: FindConflictNode 0x51716 (builds "
        "ins_range), NowDead 0x5a415, NowAlive 0x5a3c6, AssignBit 0x5a48c.",
        oracle=None,
        instrumentation="INSTRUMENTED: wr (withregs + ins_range), bt "
        "(cand list + state/id bits), gb/tg (scores/vetoes).  The AL-squat "
        "hint reads wr A-bits and names the lever class."),
    RuleVerdict(
        rule="127", title="named byte local vs repeated expression: allocator conflict vs rover-seated CSE temp",
        status="verified",
        hint="A byte value PS loads ONCE into a non-A byte register, tests, "
        "then RE-EXTENDS via `mov al,<reg>; and eax,0xff` for a call arg "
        "(binir kind zext_copy_and) while RC seats it directly in AL: PS's "
        "source wrote the EXPRESSION TWICE -- e.g. `if (bm[i+1] != 0) "
        "f(bm[i+1], 0);` -- and the optimizer commons the loads into a temp "
        "that is ROVER-seated (FindRegister, next byte-cursor slot), NOT an "
        "allocator conflict.  RC's named local (`if ((u = bm[i+1]) != 0) "
        "f(u,0);`) creates a 2-ref conflict that GiveBestReg seats in AL.  "
        "The rover advance also shifts EVERY later byte rover pick by +1 "
        "(downstream const-store seats, callee-save set, tail-merge "
        "eligibility, jcc widths) -- one source edit can close hundreds of "
        "bytes (battle_action 316b -> exact).",
        mechanism="CSE creates the temp AFTER conflict construction, so it "
        "never reaches MakeConflicts/GiveBestReg; LdStAlloc's Enregister/"
        "FindRegister rover (i86ldstr.c) seats it from the persistent byte "
        "cursor.  rg+rq trace census = total allocator commit coverage, so "
        "absence there + an fr record IS the rover proof.",
        ow_v1="i86ldstr.c Enregister (OP_MOV const->mem and load/store "
        "operands) + FindRegister rover; csemain.c commons the repeated "
        "expression.",
        re_10_0a="DWORD variant PROVEN (show_debug_screen 5171b -> exact, "
        "debug.c 2/2): seven signed-value sections as repeated expressions "
        "-> dword CSE temps walk to PS's seats (ECX/ESI/EDI/EBP/EAX), the "
        "prologue gains the callee-saves, the dword rover shifts so the "
        "first const-zero lands in callee-save ESI, and the cross-call "
        "scoreboard (esi==0 survives calls) feeds 16 subsequent stores.  "
        "battle_action L645: probe pA (named local) = 3 allocator "
        "confs, byte->AL, no fr; probe pB (repeated expr) = 2 dword confs + "
        "one byte fr -> `mov dl,[eax+1]; test dl,dl; mov al,dl; and eax,"
        "0xff` exactly PS's shape.  FindRegister 0x62a29 (fr hook at entry "
        "= all callers).",
        oracle=None,
        instrumentation="INSTRUMENTED: fr records (rover walk + line map), "
        "rg/rq (allocator commits); binir zext_copy_and = the PS-side "
        "machine signature.",
        universal=False),
    RuleVerdict(
        rule="128", title="pointer-local hoist vs direct array indexing (Enregister gate)",
        status="verified",
        hint="PS stores a run of one constant through a SHARED REGISTER "
        "(`xor edx,edx; mov [eax+BASE+f1],edx; ...` -- binir "
        "const_store_run_reg, one fixup per access) where RC emits "
        "IMMEDIATE stores (`mov dword [p+f1],0; ...` -- "
        "const_store_run_imm) plus a base materialize (`add r,ARR` / "
        "`mov r,ARR; add r,idx` -- ptr_base_materialize): RC's source "
        "hoisted `struct X *p = &arr[i];` where PS indexed DIRECTLY "
        "(`arr[i].f = K;` per statement).  Replace the pointer local with "
        "direct indexing (or vice versa for the mirrored split).  "
        "Knock-on effects of the pointer form: the index derivation is "
        "cached (direct form re-derives movsx+imul per statement group -> "
        "PS-only signext_load_* excess), each store is 10b vs 6b, and the "
        "pointer holds a callee-save register across statements "
        "(prologue pressure).",
        mechanism="i86ldstr.c Enregister RISCifies `OP_MOV const -> mem` "
        "ONLY for N_MEMORY or N_INDEXED with a symbol base: "
        "`case N_INDEXED: if (result->i.base == NULL) break;`.  A pointer "
        "local makes every access base==NULL (register-only addressing) "
        "so the constant is never enregistered; direct indexing folds the "
        "array base into the displacement (symbol base survives) and the "
        "shared const register comes from the dword rover.",
        ow_v1="i86ldstr.c Enregister (OP_MOV arm) + FindRegister; the "
        "addressing fold is the front-end's N_INDEXED(base=arr+off, "
        "index=i*scale) form.",
        re_10_0a="probe ptr1.c: direct form -> xor edx,edx + 6b reg "
        "stores; pointer form -> `add eax,ARR` + 10b imm stores, no zero "
        "reg.  Corpus: get_battle_centuries_left PS reg-run(n=5) vs RC "
        "imm-run(n=10) + 3 materializes; signext census 140 PS-only "
        "word / 91 byte sites across ~40 fns largely downstream.",
        oracle="docs/codegen-experiments/ptr_local_vs_direct_indexing.py",
        instrumentation="binir const_store_run_reg/const_store_run_imm + "
        "ptr_base_materialize; the kind split surfaces per line in "
        "binir-shape automatically.",
        universal=False),
    RuleVerdict(
        rule="129", title="caching local vs direct global use (call = reload boundary)",
        status="verified",
        hint="PS reloads the same fixed global N times (one load after "
        "each intervening CALL) while RC loads it once and pushes an "
        "extra callee-save: the decomp invented a caching local (`int i "
        "= g;`).  DELETE the local and write the global at each use -- "
        "the reloads reappear AND the callee-save push disappears.  "
        "Inverse direction (RC reloads, PS single load + callee-save): "
        "ADD the local.  The `Global re-read` hint prints totals + the "
        "top re-read addresses.",
        mechanism="The value pool keeps a loaded global's register across "
        "plain stores to OTHER symbols, but a CALL kills the copy (caller "
        "-clobber + pool flush) -> next use reloads.  A named local is a "
        "TEMP: it allocates a callee-save register and survives calls.  "
        "Knock-ons: prologue push set, register pressure, and the "
        "Rule 128 family (a pointer local is the same invention for "
        "&arr[i]).  WITHIN-BLOCK variant (named-local-tiebreak.py, "
        "2026-06-25): even without a call boundary, naming the cache "
        "consolidates N inline sav=2 anon-temp leaves into ONE FE "
        "conflict at sav=N+1, jumping to the TOP of the ConfBefore "
        "queue.  Structural rank change, not a tie-break -- the named "
        "local out-prioritises any sav-≤N+1 rival downstream of it.  "
        "observed-source-style.md §13.",
        ow_v1="value-pool / scoreboard global tracking (scmain.c family); "
        "call kill is the caller-save flush.",
        re_10_0a="probe rld.c: f1 one load across 3 stores; f2 reload "
        "after call; h1 cached local -> push edx + one load; f3 const "
        "propagation g=5 -> [0x18].  Corpus: 53 fns with PS >= RC+4 "
        "fixed-load excess (place_sprite 70v19, evolve_region 26x one "
        "global, check_*_ferret_move 20x).",
        oracle="docs/codegen-experiments/global_reload_boundary.py",
        instrumentation="decomp-verify `De-invent`/`Add an intermediate` "
        "hint (c2/commands/deinvent_hints.py): AST-named local + PS-side "
        "per-address reload census, both directions.",
        universal=False),
    RuleVerdict(
        rule="130", title="memory-sum surface forms (LdStAlloc split / LdStCompress merge-back)",
        status="verified",
        hint="An n-term memory sum stored to memory (`g = a+b+...+z;`) "
        "shows THREE surface forms for the same IR: merged `add acc,[m]` "
        "terms, an acc-swap split (`mov r2,[m]; add r2,acc`), and the "
        "LAST addend ALWAYS split (`mov r2,[m]; add acc,r2`).  binir "
        "mem_sum_chain decodes all of it as ONE statement -- do NOT "
        "write a `+=` chain to imitate the splits (that emits RMW "
        "`add [g],reg` stores, a different shape entirely).  Same-side "
        "term-count mismatch = different expression grouping.",
        mechanism="Post-alloc LdStAlloc RISCifies every memory operand "
        "(486 scheduling); LdStCompress/CompressIns merges back only "
        "ADJACENT pairs passing the guards: when `next` is the result "
        "store, the presult path engages and `*popnd != *presult` aborts "
        "both merges (last-addend split); when SWAPOPS made the riscify "
        "register the accumulator, the popnd live-guard declines "
        "(acc-swap split).",
        ow_v1="i86ldstr.c LdStAlloc/LoadStoreIns/Enregister + "
        "LdStCompress/CompressIns (incl. the BBB Dec-4-1993 operand "
        "guard).",
        re_10_0a="CompressIns 0x62e16 decompile-confirmed 1:1; "
        "LdStCompress 0x62ff0, CompressMem16Moves 0x62d5a, ChangeIns "
        "0x6974e named.  Probe sum.c: f2 (2-term) keeps last addend "
        "split, f5 (5-term) merges b,c + acc-swaps d + splits e; `+=` "
        "chain h emits RMW add-[g] forms.  lc trace record @0x62fb4 = "
        "merge-back commits (fr+lc = the full story); PS exemplar: "
        "get_battle_centuries_left totals L+26/L+27.",
        oracle="docs/codegen-experiments/mem_sum_chain_forms.py",
        instrumentation="binir mem_sum_chain (reverse IR: ASSIGN + O_PLUS "
        "chain); trace lc records (rf['lc'], cache v15) for RC-side "
        "ground truth.",
        universal=False),
    RuleVerdict(
        rule="131", title="|| chain vs else-if chain: per-term line entries discriminate",
        status="verified",
        hint="A short-circuit OR over n comparisons (je/je/../jne to one "
        "shared body) can come from TWO sources with IDENTICAL bytes: a "
        "multi-line `||` chain, or an else-if chain with the SAME body "
        "duplicated per arm (ComTail merges the bodies back).  The LINE "
        "TABLE discriminates: `||` emits ONE entry (every term carries "
        "the if-line); else-if emits an entry PER TERM (PS L+13/14/15/16 "
        "ascending).  When PS shows ascending per-term entries, write the "
        "else-if + duplicated-body form -- the duplicated assignments also "
        "raise the flag variable's savings (extra defs), which can flip "
        "downstream seats (cd_path: matched allocates before p -> p=ECX).",
        mechanism="cfe attributes each statement's tree to its line; a "
        "parenthesized || condition is ONE statement (one tree, one line "
        "span), an else-if chain is n statements.  ComTail (Rule 15) "
        "merges the duplicated single-ins bodies so control flow and "
        "bytes converge; only the LINNUMs and the conflict savings "
        "differ.",
        ow_v1="ComTail/FindCommon (tail merge); cfe line attribution.",
        re_10_0a="probe lin.c: f (multi-line ||) -> LINNUM one entry for "
        "the whole condition; g (else-if dup-body) -> per-term entries + "
        "merged shared body, byte-identical flow.  cd_path 6b -> exact.",
        oracle="docs/codegen-experiments/linnum_or_vs_elseif.py",
        instrumentation="read PS line labels in the sxs view: ascending "
        "L+n at each term's first ins = else-if; single label = ||.",
        universal=False),
    RuleVerdict(
        rule="132", title="copy-then-op vs op-in-place: left-operand liveness",
        status="verified",
        hint="`mov rT,rS; <alu> rT,X [; mov [dst],rT]` and the in-place "
        "`<alu> rS,X` are the SAME statement `d = s <op> x`.  The copy "
        "survives iff the value in rS is still LIVE past the statement "
        "(a later read, a `return s`, a cached variable).  PS-side copy "
        "= PS's source reads that value again later and OURS consumed "
        "it; recomp-side copy = our source keeps an extra later use "
        "that PS didn't have.  Fix the LATER USE, never restructure the "
        "op statement itself.  Side effect: the copy target prefers a "
        "callee-save reg, so prologue push deltas often ride along.",
        mechanism="wcc reduces every two-address binary op through a "
        "result temp (OW v1 split.c rMOVOP1RES prefixes `mov result,op0`; "
        "rUSEREGISTER's CanUseOp1 tests HW_Ovlap(op0.reg, next->live.regs)). "
        "The allocator coalesces result with op0 -- killing the mov -- "
        "exactly when op0's conflict does not overlap the result's, i.e. "
        "op0 dies at the op.",
        ow_v1="bld/cg/c/split.c rMOVOP1RES / rUSEREGISTER (CanUseOp1).",
        re_10_0a="oracle probe cuo.c: `g=a-b;` alone -> `sub eax,edx` "
        "in-place; adding `h=a+3;` or `return a;` -> `mov ebx,eax; "
        "sub ebx,edx` + EBX push.  Tooling: binir kind `copy_then_op` "
        "(57 clean corpus sightings) + rule_hints Rule 132 detector "
        "(both directions, suppressed when both sides copy) -- "
        "deterministic from the diff alone, no live trace needed.",
        oracle="docs/codegen-experiments/copy_then_op_liveness.py",
        universal=True),
    RuleVerdict(
        rule="133", title="sub-dword (byte/word) inert tie-break: list-order seats the seat",
        status="verified",
        hint="A byte/word value is SEATED differently than PS with no MOV-credit "
        "reason (the `Byte-seat:` CASE D verdict, or a cwde-vs-`movsx eax,rX` "
        "disagreement for shorts -- 1b vs 3b).  ROOT: GiveBestReg's equal-savings "
        "tie-break is INERT for sub-dword regs.  Byte/word registers sub-register "
        "already-given dwords, so `HW_Subset(Given,reg)` AND `HW_Subset(Given,best)` "
        "both hold for every candidate => the discriminator never fires => the "
        "candidate-LIST order alone decides (ByteRegs AL,AH,DL,DH,BL,BH,CL,CH; "
        "WordRegs AX,DX,BX,CX,SI,DI).  CONSEQUENCE: this is SOURCE-IRREDUCIBLE -- "
        "declaration/use-order levers (permute, decl-swap, Rule 28a/115) PROVABLY "
        "cannot move a pure sub-dword seat; park it.  Only a SAVINGS-rank change "
        "(split counters as in fade_to_palette i/j) or moving it off the byte/word "
        "class (Rule 126 int-widen) reseats it.  Markers: `Byte-seat:` (bytes), "
        "cwde/movsx (shorts -- get_linked_page, convert_lbm_file park).",
        mechanism="GiveBestReg tie-break requires HW_Subset(Given,reg) && "
        "!HW_Subset(Given,best); both true for sub-dword candidates once the "
        "higher-savings dword conflicts have committed EAX/EDX/EBX/ECX to "
        "GivenRegisters, so the test is dead and list-order wins.  (optab also "
        "picks the AX accumulator short form, so the seat drives the cwde/movsx "
        "size for shorts.)",
        ow_v1="regalloc.c GiveBestReg tie-break (HW_Subset); cgi86reg.h byte/word "
        "register order -- ALGORITHM GUIDE ONLY.",
        re_10_0a="PROVED in wcc386 10.0a: tie-break VA 0x57ca1-0x57cc8 "
        "(GiveBestReg_byte_tiebreak; cmp saves,best then HW_Subset(Given,reg) "
        "&& !HW_Subset(Given,best)), GivenRegisters@0x7f884, ByteRegs@0x79620 = "
        "AL,AH,DL,DH,BL,BH,CL,CH.  Byte-class theorem grounded on live bt.given_regs "
        "(watcom10.0a knowledge/wcc386_regalloc.py).  fade_to_palette (word): short "
        "counters seat BX after changed takes DL; get_linked_page +0x6b movsx vs cwde.",
        oracle="fade_to_palette worked example (lib32.c, exact).",
        instrumentation="`al` trace records with regclass=word give the "
        "short locals' savings/walk order -- needed to pick WHICH lever "
        "(decl order, split counters, extra defs) moves the seat.  The "
        "rule_hints Rule 133 detector (cwde vs movsx r32,r16) only marks "
        "the family.",
        universal=False,
        caveat="the winning seat depends on allocator state (masking by "
        "earlier-allocated overlapping conflicts, byte siblings like "
        "changed->DL masking DX); same source shape can seat differently "
        "in a different function."),
    RuleVerdict(
        rule="134", title="for-clause loop rotation vs while+manual-inc",
        status="verified",
        hint="PS shows `jmp <forward>` from the loop entry to a bottom-tested "
        "`cmp/test + jcc <back>` (rotated layout: init; jmp test; body; "
        "inc; test+jcc-back).  Equivalent RC has head-tested layout "
        "(`cmp; jcc exit; body; jmp top`).  The trigger is the SOURCE form: "
        "`for ( ; cond; cnt++) { body }` -- a for-clause with EMPTY init "
        "clause but populated cond and inc -- gets the rotation at default "
        "optimization.  The equivalent `while (cond) { ...; cnt++; }` (manual "
        "inc at body tail) stays head-tested.  Rewrite the while to `for(;;)` "
        "to match PS.  CAVEAT: the rewrite also flips the inc form from "
        "in-place `inc [global]` (PS's 6-byte RMW) to cached `mov r,[g]; "
        "inc r; mov [g],r` (RC's 13-byte form, a Rule 72 violation).  Pair "
        "with a Rule 72 check on the same function before committing.",
        mechanism="GROUNDED 2026-06-12 (watcom10.0a 6820229): the rotation is "
        "the 10.0a FE's for-statement lowering ITSELF (block-creation/gen_id "
        "order).  Final layout == gen_id order: 10.0a SortBlocks@0x5c4e3 is a "
        "plain stable bubble sort (no branch-prediction pass), the only gen_id "
        "mutator is MoveDownLoop@0x60535, and its only caller TwistLoop@0x61586 "
        "is gated on the -ol model bit (0x7f8a0 & 0x400000) which is CLEAR at "
        "PS flags -- no optimizer pass reorders blocks.  The ge trace shows the "
        "rotated emission order already at GenObjCode time.  CAVEAT vs OW v1 "
        "source: owp4v1 cc cstmt2.c emits TOP-TESTED IL for both forms -- a "
        "real FE divergence; do not cite cstmt2.c as the mechanism.",
        ow_v1="bld/cc/c/cstmt2.c::EndForStmt vs case T_WHILE end of statement.",
        re_10_0a="get_nearest_reg_building (int_c2.c) +0x1b jmp 0xca to cmp+jl "
        "at +0xca; convert_lbm_file (lib32.c) +0x148 jmp 0x194 to cmp+jle; "
        "clear_an_area (map.c) +0xd8 jmp 0x1e8 to cmp+jle.  Triple-confirmed "
        "by oracle probe.",
        oracle="docs/codegen-experiments/loop_rotation_for_vs_while.py",
        instrumentation="binir kinds `loop_rotation_entry` (the forward jmp) "
        "and `loop_rotation_test_back` (the bottom cmp+jcc-back compound).  "
        "An asymmetric PS-only sighting of `loop_rotation_entry` means the "
        "source uses `while(...; cnt++)` and a for-clause rewrite is the "
        "lever.",
        universal=False,
        caveat="the for clause's INIT must be EMPTY and the actual init has "
        "to be a SEPARATE statement immediately before -- e.g. "
        "`cnt = 0; for ( ; cond; cnt++) { body }`.  Placing the init INSIDE "
        "the for clause (`for (cnt = 0; cond; cnt++)`) does NOT trigger "
        "the rotation -- it produces the do-while form (no initial jmp).  "
        "Worked example get_nearest_reg_building 132 -> 5b (int_c2.c "
        "L4391, commit 91f2590); the FIRST attempt with init inside the "
        "for regressed 132 -> 165b.  Residual 5b is a Rule 133 byte-reg "
        "seat tie unrelated to the lever."),
    RuleVerdict(
        rule="29", title="DEC vs LEA for in-place global decrement",
        status="verified",
        hint="PS shows `dec reg; mov [g],reg` for a global decrement -> write the "
        "load-local-dec-store form `if((ref=g)!=0){ref--; g=ref;}`, NOT the direct "
        "`g--` (which emits `lea reg2,[reg1-1]` into a FRESH register to preserve "
        "the old value, +4b).",
        mechanism="Naming a local lets the value-pool prove the pre-decrement "
        "value is dead -> in-place `dec`. A direct global `--` keeps the old value "
        "potentially live (the test register) -> `lea` into a new register. Same "
        "named-local-changes-liveness family as Rule 24.",
        ow_v1="value-pool liveness in the back-end (CGGets path).",
        re_10_0a="check_for_promotion refused_promotion-- uses dec form.",
        oracle="tests/oracle/test_rule_29_dec_vs_lea.py"),
    # ------------------------------------------------------------------
    # 2026-06-11 backfill: the workhorse rules cited daily by live hint
    # lines (Reg-swap levers, zext idioms, tail-merge, code motion) that
    # were documented in docs/watcom-codegen-patterns.md but never got a
    # registry verdict.  Each is long-verified in practice; the verdict
    # text condenses the doc section.
    # ------------------------------------------------------------------
    RuleVerdict(
        rule="28a", title="Equal-savings tie-break lever 1: commute / reorder the deciding USE",
        status="verified",
        hint="Layer-3 register-identity swap on two values with EQUAL savings "
        "(same tie group in the regtrace --explain SortConflicts panel): "
        "reorder which value is REFERENCED FIRST -- commute the deciding "
        "expression (`dest_y*80 + dest_x` -> `dest_x + dest_y*80`) or move "
        "a statement.  Most predictable of the two tie levers; try before "
        "Rule 115.  ONLY acts inside a tie group -- check the panel first.",
        mechanism="SortConflicts' ShellSort is UNSTABLE and ConfBefore has no "
        "secondary key; the tied pair's relative order comes from conflict "
        "CREATION order (cn records), which follows the IL operand/use order. "
        "Reordering the first use swaps the creation slots and hence the "
        "allocation walk -> the pair takes opposite registers.",
        ow_v1="regalloc.c::ConfBefore (strict savings compare, no secondary "
        "key); sortlist.c ShellSort (unstable).",
        re_10_0a="sa/cn trace records; ps_alloc.detect replays the ShellSort "
        "with swapped creation slots.  Worked: change_citizen_targs.",
        instrumentation="INSTRUMENTED: `c2 regtrace <fn> --explain` prints the "
        "sa tie-group panel (ground-truth allocation queue) and PS-alloc "
        "REACHABLE/NOT-TRANSPORTED verdicts.  CAUTION: pairs the RISCify "
        "rover claims are DEFERred (rover scratch, not an allocator tie).",
        universal=False,
        caveat="acts only inside an equal-savings tie group; NOT-TRANSPORTED "
        "verdicts (pair order pinned by the rest of the list) and rover-"
        "seated values are unreachable.  given_regs DRIFT (retry rounds) "
        "invalidates the order reasoning entirely."),
    RuleVerdict(
        rule="35", title="Byte-by-byte LE word load: low-byte-first source order",
        status="verified",
        hint="PS reads a packed LE u16 byte-by-byte as `xor edx,edx; mov dl,"
        "[m+1]; shl edx,8; movzx edi,[m]; add edi,edx` -> write the HIGH byte "
        "term first in C (`(p[1] << 8) + p[0]`).  Low-first source produces "
        "the mirrored (different-byte) sequence.",
        mechanism="The FE emits the addition operands in source order; the "
        "high term's shl lands on the first-loaded register.  Pure "
        "source-shape -> deterministic byte sequence.",
        ow_v1="front-end expression order (cexpr); no optimizer involvement.",
        re_10_0a="restore_picture_part sprite_width/sprite_x high-first forms "
        "(display.c) byte-match PS.",
        oracle=None),
    RuleVerdict(
        rule="42", title="Cross-function tail-merge donor selection (ComTail)",
        status="verified",
        hint="A function tail replaced by `jmp` into another function's "
        "epilogue: the donor is ComTail's argmax over the TU-wide RetList "
        "(LIFO of every ret emitted so far; >=6 common bytes required, "
        "first-encountered wins ties).  Donor wrong -> fix the DONOR "
        "function (or the TU function order) before grinding the hostee; "
        "the donor-flip filter classifies body-irrelevant cases.",
        mechanism="optins.c::OptPush walks backward from LastIns; on OC_RET "
        "calls ComTail(RetList, ins); FindCommon counts matching PrevIns "
        "pairs; max.save > 5 gates; TransformJumps rewires.  OptForSize>=25 "
        "(default 50) -> always on.",
        ow_v1="bld/cg/c/optcom.c::ComTail; optutil.c::AddRef (RetList).",
        re_10_0a="ComTail@0x679CE, OptPush callsite 0x4C866 (rl hook), "
        "decision site 0x67A28 (cm hook).",
        oracle="tests/oracle/test_rule_42_tail_merge_donor_selection.py",
        instrumentation="INSTRUMENTED (image >= 2026-06-11 parse): "
        "routine['retlists'] (rl, RetList length per OptPush ComTail call) + "
        "routine['comtail'] (cm, per-invocation {save,line} merge decision) "
        "make the donor choice observable per routine.",
        universal=False,
        caveat="the donor is a TU-WIDE property (RetList contents = every "
        "ret emitted so far): any size/order change in OTHER functions can "
        "flip it (the common.c cross-function cascade lesson).  Run the "
        "whole file before committing."),
    RuleVerdict(
        rule="44", title="Split a temp for `(byte & MASK) == 0` to drop a "
        "spurious zext",
        status="verified",
        hint="Diff shows PS `and al,MASK; jcc` (ZF set straight off the 8-bit "
        "AND) where RC inserts a `and eax,0xff` (5b) before the test: the inline "
        "`if ((x & MASK) != 0)` promoted the AND result to int for the compare. "
        "Split the masked byte into an `unsigned char` temp "
        "(`unsigned char t = x & MASK; if (t != 0)`) so the back-end keeps the "
        "test byte-only and elides the widening.",
        mechanism="C integer-promotion of `byte & MASK` to int for `== 0`; held "
        "in an int intermediate the back-end inserts `and eax,0xff` to clean the "
        "upper bits before the int compare.  Assigning to an unsigned char temp "
        "first marks the result byte-only and suppresses the widening cast "
        "(opposite of Rule 1: cache-good here, inline-bad).",
        ow_v1="docs/watcom-codegen-patterns.md Rule 44; integer-promotion in the "
        "expression evaluator.",
        re_10_0a="evolve_amenity_cover 552b->28b via `unsigned char act = "
        "CM_CELL(cm_sptr).activity_a & 0xf` at loop-top.",
        universal=False,
        caveat="REGIME-DEPENDENT: the byte-temp split only wins when the test is "
        "at low register pressure (loop-top guard).  In a register-pressured "
        "branch the extra named local adds spill/slot churn that outweighs the "
        "5b zext -- business_output's deep water-source guard went +42b when "
        "split, so the inline form (with the spurious zext) was kept there. "
        "Read the surrounding pressure before splitting; if the function has "
        "many live values across the guard, leave it inline."),
    RuleVerdict(
        rule="49", title="`& 0xff` vs `(unsigned char)` selects different zext idioms",
        status="verified",
        hint="PS `mov rl,[m]; and reg,0xff` (load-then-mask, 12b) vs RC "
        "`xor reg,reg; mov rl,[m]` (xor-then-load, 8b) for the same byte "
        "zext: flip the C spelling -- `x & 0xff` gives PS's mask form, "
        "`(unsigned char)x` gives the xor form.  The 4b delta cascades "
        "through all later offsets.  SECOND LEVER (variable-reuse, cgex "
        "`putting_out_fire`): for a byte FIELD read into a condition, a single "
        "REUSED `unsigned char` local with NESTED ifs emits the MASK form "
        "(`mov;and`); INLINE reads in an `&&` emit the XOR form (`xor;mov`).  "
        "Worked: test_zone_for_closest_fire `b=base_kind; if(b<8){b=edge_bits; "
        "if(b&0x80){...}}` recovered PS's mask form (binir 16->18, 318->298b).  "
        "CAVEAT: the xor-form-producing form (cast/inline) can RELOCATE a "
        "separate UNCONDITIONAL read into a conditional block when the value is "
        "read before an `if` -- verify the -d1 line shape, don't trade it for a "
        "few bytes (worked counter-example: dock_the_ship cohort inline gave "
        "`xor;mov` -2b but moved the read inside the if = wrong shape).",
        mechanism="The FE lowers the explicit AND mask as a real O_AND on the "
        "widened value; the cast form goes through the CONVERT path which "
        "the back-end RISCifies as clear+partial-load.  Spelling-determined, "
        "deterministic.  Variable-reuse acts on the same fork: a reused named "
        "byte local keeps the value in a byte reg the mask path widens "
        "in-place; inline reads go through CONVERT (clear+partial-load).",
        ow_v1="cexpr/ctypes widening vs O_AND lowering; i86enc32 zext forms.",
        re_10_0a="binir kinds zext_and_inplace / zext_clr_reg / zext_byte_load "
        "mark each form; Rule 49 sweep list in priority-targets.",
        oracle=None),
    RuleVerdict(
        rule="49b", title="Asymmetric xor+mov.lo zext pair insertion (cast-form marker)",
        status="verified",
        hint="Diff shows an INSERTED `xor reg,reg; mov reg.lo,[...]` pair on "
        "one side only (the aligner can't pair it with the other side's "
        "load+and): that side used the cast-form zext.  RC has the pair -> "
        "rewrite `(unsigned char)x` as `x & 0xff`; PS has it -> reverse.",
        mechanism="Same mechanism as Rule 49; this is the diff-shape detector "
        "for the unaligned case (SequenceMatcher shows insert+delete instead "
        "of a replace).",
        ow_v1="see Rule 49.",
        re_10_0a="rule_hints.detect_rule_49b (adjacent-pair scan); binir "
        "zext_copy_and is the related Rule 127 rover marker -- check the "
        "AL-squat OVERRIDE line before applying 49b mechanically.",
        oracle=None),
    RuleVerdict(
        rule="89", title="Register allocation = interference + CountRegMoves + list order (no economics knob)",
        status="verified",
        hint="A value's register is decided by (1) live-range interference "
        "incl. call/mul/div clobber crossings, (2) CountRegMoves move-"
        "elimination credits, (3) first free candidate in DoubleRegs "
        "(EAX,EDX,EBX,ECX,ESI,EDI,EBP -- EBX BEFORE ECX in 10.0a).  "
        "EAX<->callee-saved swaps mean a clobber crossing changed: cut RC "
        "value uses across calls (the RC-extra-callee-save bucket lever).",
        mechanism="GiveBestReg argmax over CountRegMoves with GivenRegisters "
        "subset tie-break, then candidate list order.  No caller/callee-save "
        "cost model exists; MustSaveRegs is a set-algebra fact, not a "
        "heuristic.",
        ow_v1="regalloc.c::GiveBestReg/CountRegMoves; i86reg.c::MustSaveRegs.",
        re_10_0a="GiveBestReg@0x57b78, DoubleRegs@0x79850 (va 0x821A8 table); "
        "gb/tg trace records give the full per-candidate score table.",
        oracle="docs/codegen-experiments/regalloc-eax-boundary.py",
        instrumentation="INSTRUMENTED: gb/tg records -> the GB: hint line "
        "([credit]/[given-tie-break]/[list-order]/[forced] pick reasons).",
        universal=False,
        caveat="this is the MODEL, not a single lever: the per-function "
        "outcome depends on the whole conflict set (interference + queue "
        "state); any clobber-crossing edit re-ranks neighbours.  Read gb/tg "
        "before editing."),
    RuleVerdict(
        rule="103", title="(R,R) compare operand order welded to register priority (compiler-delta class)",
        status="verified",
        hint="A 2b residue: `cmp A,B; jcc` vs `cmp B,A; jcc-mirror` with "
        "IDENTICAL register contents on both sides.  decomp-verify filters "
        "pure cases as ~r4 soft-exact.  Do NOT grind source operand "
        "reorders: the emitted order is welded to which value sits in the "
        "higher-priority register, not to source order.",
        mechanism="G_RR2 encoding picks operand order from register priority; "
        "flipping the source compare also flips the conflict-creation slots, "
        "so the register assignment flips WITH it and the cmp re-mirrors.  "
        "Preimage exists but no independent source lever found.",
        ow_v1="i86enc32 G_RR2 row; RevCond/FlipCond machinery.",
        re_10_0a="entering_new_square (int_c2.c, 2b) -- PROVEN residue via "
        "cn+ShellSort replay (NOT-TRANSPORTED).",
        universal=False,
        caveat="this is a stop-grinding classification, not a lever: "
        "NOT-TRANSPORTED PS-alloc verdicts land here."),
    RuleVerdict(
        rule="108", title="Named local caching a global out-ranks an incoming param for EAX",
        status="verified",
        hint="PS keeps the PARAM in its arrival register (EAX) and the "
        "global elsewhere; RC emits `mov edx,eax` evacuating the param and "
        "loads the global into EAX -> DELETE the caching local and read the "
        "global inline at every use (Watcom CSEs the loads anyway).",
        mechanism="A named local caching a global becomes a first-class "
        "conflict with savings=defs+uses, out-ranking the param's conflict "
        "in the allocation queue; it takes EAX first.  Inline reads are "
        "RISCified (rover scratch) and never compete for the param's seat.",
        ow_v1="regalloc.c conflict savings (CalcSavings); i86ldstr.c rover.",
        re_10_0a="do_act_zoom_out worked example (zoom_level local vs "
        "decayed param); cascades to end-of-function const stores and "
        "ComTail eligibility.",
        universal=False,
        caveat="the inverse of Rule 1's all-or-nothing: one remaining named "
        "read keeps the conflict alive.  EAX-funnel functions (retval in "
        "EAX) can mask the effect."),
    RuleVerdict(
        rule="109", title="Single-use scaled-index load fuses its index into the result register",
        status="verified",
        hint="Diagnostic tell on the load row: same dst reg both sides, but "
        "PS base != dst (index in a scratch) while RC base == dst (index "
        "merged).  Lever: a dead self-store through the same index "
        "(`arr[i].f = arr[i].f;` -- DCE'd) gives the index its own conflict "
        "and a scratch seat.",
        mechanism="CountRegMoves credits the fixed destination (call-arg / "
        "return seat) for the index temp when the load is single-use -> "
        "coalesce.  A second (dead) use breaks single-use and the credit.",
        ow_v1="regalloc.c::CountRegMoves coalesce credit.",
        re_10_0a="barbarians_drop_by_city 3b->0 (worked).  HARD members where "
        "the lever regresses: find_enemy (4->21: the extra use re-allocates "
        "the surrounding section).",
        universal=False,
        caveat="the dead-store lever adds a use that can re-rank NEIGHBOURING "
        "conflicts; verify the whole function, expect regressions on "
        "high-pressure members (find_enemy parked)."),
    RuleVerdict(
        rule="115", title="Equal-savings tie-break lever 2: swap the tied locals' DECLARATION order",
        status="verified",
        hint="When Rule 28a's use is pinned by semantics, swap the two tied "
        "locals' declaration lines.  Direction is NON-MONOTONIC -- verify "
        "both orders.  Only meaningful inside a sa-panel tie group.",
        mechanism="Decl order moves the name nodes' creation slots, which "
        "moves the conflicts' cn order through MakeConflicts -> same "
        "unstable-ShellSort transport as Rule 28a.",
        ow_v1="regalloc.c::ConfBefore + sortlist.c ShellSort instability "
        "(H1 hidden name-pointer key vs H2 instability -- same levers).",
        re_10_0a="show_help_page (mmedia.c) canonical 11b ESI<->EDI worked "
        "example; sa/cn records ground the replay.",
        instrumentation="INSTRUMENTED: same panel/verdict machinery as "
        "Rule 28a (sa tie groups, PS-alloc transport replay).",
        universal=False,
        caveat="same limits as Rule 28a (tie group only, rover pairs "
        "DEFERred, drift invalidates).  Anonymous-temp ties have no decl "
        "handle at all -- skip mechanical swaps (font_format_split note)."),
    RuleVerdict(
        rule="135", title="goto-to-shared-call idiom + the framed mid-epilogue class",
        status="verified",
        hint="PS shows a shared [args+call(+epilogue+ret)] cluster INSIDE the "
        "first arm with LATER arms back-jumping into it: the source is the "
        "goto idiom -- a label on the call statement in arm 1 (+ `return;`), "
        "`goto <label>` from every other arm.  Worked: devolve_a_building "
        "127b -> body exact.  The arm's early return also decouples the "
        "call from the cond-chain's linear span (fixes the whole seat "
        "cascade: CSE'd zext -> EAX, byte temp -> DL, slot reload).",
        mechanism="FE block-creation order = final layout (no reorder pass "
        "at PS flags); the goto arms produce the back-jumps directly.  The "
        "one non-source residue: PS places the FRAMED epilogue (add esp,N + "
        "pops + ret N, >5 bytes) mid-function right after the call; our "
        "builds funnel it to the function end with a jmp.  CloneCode's "
        "budget (ObjLen(jmp)=5 at OptForSize=50) only inlines epilogues "
        "<= 5 bytes -- which proves the corpus split below.",
        ow_v1="optpull.c CloneCode (MAX_CLONE_SIZE + OptForSize scaling); "
        "optins.c OptPush/OptPull dispatch.",
        re_10_0a="StraightenCode@0x6732e, FindShort@0x67181 (ATTR_SHORT=0x20 "
        "veto), branch-shortener 0x67da1/0x67f74 (sets ATTR_SHORT at front "
        "time), flusher chain 0x3a3a9/0x3a491/0x3a5e8/0x3a455, "
        "Insert/DeleteQueue 0x670a4/0x67122 (count @0x8034c).  CORPUS "
        "THEOREM (2026-06-12): all 19 byte-exact mid-ret functions are "
        "FRAMELESS (pops-only epilogue <= 5b, CloneCode-able); EVERY framed "
        "mid-epilogue function diffs identically.",
        oracle=None,
        instrumentation="the donor-flip detector classifies the epilogue-"
        "position residue ~exact (body exact).  cm/rl records show ComTail "
        "declining (save<=5).",
        universal=False,
        caveat="the framed mid-epilogue POSITION reproduces ONLY when TWO "
        "per-return epilogue copies exist for ComTail to merge keep-first "
        "(common > 5 bytes): colour_cycle_delay1 is the byte-exact proof "
        "(`if (...) { ...; return 1; } return 0;` -> mid epilogue + "
        "back-jump, cm save=7).  When the compiler FUNNELS the returns "
        "instead (single epilogue + jmp, e.g. devolve's goto form), the "
        "position stays end-anchored -> ~donor residue *within that one "
        "function*.  UPDATE (2026-07-07, e27e4717, evolver.c): the "
        "funnel-vs-per-return question above only asks whether ONE "
        "function alone can move its own epilogue.  It cannot -- but a "
        "SECOND, cross-function mechanism can move it for you: ComTail's "
        "TransformJumps (optcom.c) fires when a DEPENDENT function is "
        "compiled immediately after the donor (this file's emission "
        "order) and is itself written arms-first with its own shared "
        "call+`return;` as the function's LAST statements -- the FE's "
        "last-statement special case then emits ITS epilogue inline "
        "right after ITS call, and ComTail's ComTail/JustMoveLabel/"
        "AddNewJump/Untangle chain (see docs/comtail-cascade-analysis.md "
        "and the evolve_a_building commit message for the 4-step replay) "
        "physically hauls the DONOR's trailing epilogue block up to sit "
        "right after the donor's own early return -- the exact 'framed "
        "mid-epilogue' shape PS shows.  Reproduced byte-exact on "
        "evolve_a_building (23b, `jmp devolve+0x11`) + devolve_a_building "
        "(154b, mid-epilogue at +0x5b) together.  The donor CANNOT fix "
        "itself (Hard Rule: the lever lives in the DEPENDENT's shape, not "
        "the donor's) -- do not grind the donor alone.  GATING corpus "
        "check (2026-07-07): re-verified all 12 previously 'affected "
        "framed' members below -- 11/12 are ALREADY byte-exact (resolved "
        "in prior sessions via the goto idiom above, independent of this "
        "cross-function lever); the lone holdout, figure_go_to_target, "
        "is NOT a mid-epilogue-position residue any more -- its 12-byte "
        "diff reclassifies as a plain byte-seat CASE A tie (regalloc_pure, "
        "ir 0/75), unrelated to Rule 135.  action.c's own Rule 135 "
        "residue was checked against this new lever and is CONFIRMED "
        "STRUCTURALLY BLOCKED: its file-order neighbour flag_mode_action "
        "only shares a 2-byte common epilogue suffix (`pop ebx; ret`) with "
        "action's 5-save epilogue, below ComTail's `max.save > "
        "OptInsSize(OC_JMP,near)` (5b) admission threshold, so "
        "TransformJumps never fires -- no other corpus function supplies "
        "a matching donor tail immediately after it.  NET: as of "
        "2026-07-07 there are ZERO live Rule-135 targets with a reachable "
        "dependent; the census above is closed pending a NEW framed-"
        "mid-epilogue function surfacing elsewhere in the corpus (re-run "
        "the affected-members list first before assuming one exists).  "
        "Affected framed members: get_tb_value, "
        "get_ferret2, sail_to_target, region_go_to_target, "
        "try_this_regionmap_square, figure_go_to_target, get_wf_dirc, "
        "get_start_points, one_aquaduct_ramification, "
        "reg_road_ramifications, put_reg_x1_area, "
        "get_random_start_points_from_dirc (frameless members like "
        "get_region_invasion_points reproduce fully).  binir kinds: "
        "mid_func_epilogue (detail: framed/shared/arms) + "
        "backjump_shared_call; corpus census 104 sightings, "
        "framed+exact = 1 (the colour_cycle proof)."),
    RuleVerdict(
        rule="136", title="Memory retval funnel: W107 join-read exile to the frame slot",
        status="verified",
        hint="PS shows `sub esp,4` + `mov dword [esp],IMM` + epilogue "
        "funnel `mov eax,[esp]` while RC returns through a register: the "
        "return temp is exiled to MEMORY by an uninitialized-but-live join "
        "read.  Source recipe: `ret = IMM; goto done;` after the main "
        "body, the exit(100)/abort fail blocks AFTER it at function "
        "bottom, and a SINGLE `done: return ret;` as the last statement "
        "that the fail paths fall into.  Writing `return ret;` twice "
        "(early + final) creates separate exits, kills the join read and "
        "seats the temp in EAX -- that is the usual RC divergence.",
        mechanism="the fail paths reach the shared `return ret` without a "
        "reaching def, so the temp is live-but-uninitialized across their "
        "calls (stop_system/printf/exit) -> every register masked -> "
        "memory home (W107, same mechanism as the far-ptr homing pair in "
        "frame_hints.detect_retval_funnel, opposite direction).",
        re_10_0a="load_map_graphics: PS mov [esp],1 @+0x115, funnel "
        "mov eax,[esp] @+0x15d; RC had mov eax,1 / ECX homing until the "
        "goto-done shape landed (c2.c, byte-exact 2026-06-13).",
        oracle="load_map_graphics worked example (c2.c, exact).",
        instrumentation="static detector: frame_hints.detect_memory_"
        "retval_funnel.  Trace side (cache >= v29 + wp hook, watcom10.0a "
        "b81dfce): the exiled variable is the alloc row with "
        "memory_exiled = 'masked' (bt fired, every candidate with.regs/"
        "except-masked) or 'worthprolog' (wp budget < cost); regtrace "
        "renders it as MEMORY(<class>) instead of stale gb scores.",
        universal=False,
        caveat="fires only when RC has NO [esp] funnel load; functions "
        "with real stack locals that funnel both sides never match."),
    RuleVerdict(
        rule="137", title="Suffix-merge direction: per-arm self-contained statements, first instance kept",
        status="verified",
        hint="PS has >=2 unconditional jmps converging BACKWARD on one "
        "block while RC's converge FORWARD: both compilers tail-merged "
        "identical per-arm suffixes but kept OPPOSITE instances.  The "
        "shared block is NOT a source label/goto -- write EVERY arm "
        "self-contained (own check/call statements); Watcom then keeps "
        "the FIRST arm's copy inline and later arms back-jump into it.  "
        "The arm whose copy FALLS THROUGH (last else-if) always keeps it "
        "inline.  The rover renders each arm's freshly-stored global read "
        "as the same eax byte pattern -- that identity is what makes the "
        "suffixes mergeable.  Sibling of Rule 135 (use the goto idiom "
        "only when PS's shared block includes call+epilogue).",
        mechanism="per-arm duplicate suffixes (test/je/jmp-join) merge "
        "keep-first; a single source-level shared check (goto label or "
        "hoisted statement) gives the value a join web instead -> "
        "callee-save seat + forward merge -> different bytes.",
        re_10_0a="load_map_graphics: 8 malloc arms, per-arm "
        "`X = malloc(size); if (X == NULL) goto alloc_fail; if "
        "(!readfile(fname, X, size, 0)) goto file_fail;` -> arms 1-6 "
        "jmp 0x68 backward into arm 0's check; buf join local de-invented "
        "(c2.c, byte-exact 2026-06-13).",
        oracle="load_map_graphics worked example (c2.c, exact).",
        universal=False,
        caveat="symmetric loop back-edges (continue) appear on both sides "
        "and cancel; the detector fires only on direction ASYMMETRY.  "
        "Corpus fires 2026-06-13: one_wall_ramification, "
        "setup_enemy_units, setup_roman_units, try_this_regionmap_square "
        "(all unreviewed -- treat as leads, not verdicts)."),
    RuleVerdict(
        rule="138", title="Incoming __watcall arg registers are scratch: unused params kill saves",
        status="verified",
        hint="PS writes EDX/EBX/ECX without saving it while RC pushes it: "
        "the original signature declares parameters (possibly unused) -- "
        "incoming __watcall arg regs (EAX,EDX,EBX,ECX order) are caller-"
        "scratch.  EDX scratch => >=2 params, EBX => >=3, ECX => 4.  Add "
        "the params to decl+def; check callers/runtime for natural arity "
        "(argc/argv for main).",
        mechanism="wcc386 only preserves registers not occupied by the "
        "function's own parameter list; an unused param still marks its "
        "register caller-owned.",
        re_10_0a="main: PS saves ebx/ecx/ebp yet writes edx freely -> "
        "`void main(int argc, char *argv[])` removed RC's push edx "
        "(c2.c, byte-exact 2026-06-13).",
        oracle="main worked example (c2.c, exact).",
        universal=True,
        caveat="corpus fire 2026-06-13: try_this_citymap_square (PS "
        "writes ebx unsaved => >=3 params; unreviewed)."),
    RuleVerdict(
        rule="139", title="Dead-argument staging: callee prototype takes an int it ignores",
        status="verified",
        hint="A LONE PS-only `mov <argreg>, imm` immediately before a "
        "call both sides share (previous row equal): PS passes an "
        "argument the callee never reads.  Add the int param to the "
        "callee's decl+def (its bytes do not change) and pass the literal "
        "at the call site.  Often symmetric with an init_ sibling that "
        "uses the value.",
        mechanism="1995 API evolution: the free/teardown half of an "
        "init/free pair kept the count parameter after the body stopped "
        "using it.",
        re_10_0a="main: PS `mov eax,0xa` before call free_sample_buffer_ "
        "-> free_sample_buffer(10), prototype int n (c2.c, byte-exact "
        "2026-06-13; callee stayed exact).",
        oracle="main worked example (c2.c, exact).",
        universal=True,
        caveat="suppressed when the previous row is also PS-only (whole "
        "staging block differs = different call signature, not a dead "
        "arg).  0 corpus fires on the 232 open diffs 2026-06-13 -- rare "
        "but exact when it appears."),
    RuleVerdict(
        rule="140", title="Loop-prologue hoist: back-edge re-enters AFTER the leading stores",
        status="verified",
        hint="Both sides jump BACKWARD with the same mnemonic but PS's "
        "target sits N bytes after RC's and the skipped PS window is "
        "plain stores (mov/xor): those statements run ONCE -- write them "
        "BEFORE the loop, not at the top of its body.  Typical: a flag "
        "clear (`turbo_mode = 0;`) above `while (1)`.",
        mechanism="the back edge targets the loop's first BODY statement; "
        "statements lexically before the `while` are outside the back "
        "edge even when the byte layout is identical otherwise.",
        re_10_0a="main: je/jmp -> 0x34e (PS) vs 0x346 (RC); window "
        "[0x346,0x34e) = xor ebp,ebp + mov [turbo_mode],ebp (c2.c, "
        "byte-exact 2026-06-13).",
        oracle="main worked example (c2.c, exact).",
        universal=True,
        caveat="window capped at 32 bytes and must decode to mov/xor "
        "only; offset-cascade jcc deltas (size drift elsewhere) do not "
        "match the store-window check.  Corpus fires 2026-06-13: "
        "check_goods_in_region_warehouses, set_new_province "
        "(unreviewed leads)."),
    RuleVerdict(
        rule="92", title="Per-return inline epilogue: every `return;` emits its own ret block at its source position",
        status="verified",
        hint="PS shows an epilogue+ret MID-FUNCTION (later code below it, "
        "possibly back-jumping): the source has an explicit `return;` at "
        "that position -- 10.0a emits a REAL inline epilogue+ret per return "
        "statement (even nested), placed at the return's gen_id (creation) "
        "position.  Early-exit guards written as `if (cond) return 0;` give "
        "the early-epilogue layout; the `goto fail` funnel gives ONE tail "
        "epilogue with forward jumps.  Choose the form that matches PS's "
        "epilogue position.",
        mechanism="The 10.0a FE/cg creates a RETURN-class block per return "
        "statement which BlockToCode emits inline (epilogue + ret) at its "
        "creation position; final layout = gen_id order (no reordering pass "
        "at PS flags).  Duplicate ret tails then merge at the obj level "
        "(ComTail when common > 5 bytes; ComCode keeps the fall-through "
        "copy).  DIVERGENT from owp4v1 cc, which lowers `return` as "
        "Jump(end_of_func_label) -> one shared epilogue.",
        ow_v1="owp4v1 cstmt2.c lowers return as Jump(end label) -- 10.0a "
        "differs (FE divergence, like the for-rotation).",
        re_10_0a="ret2 probe 2026-06-12: nested early return emits two "
        "inline rets.  devolve_a_building: PS's +0x5b mid-function epilogue "
        "= arm1's `return;` block.  cm trace records expose ComTail's "
        "per-invocation max-save for the merge analysis.",
        oracle=None,
        instrumentation="cm/rl records (routine['comtail']/['retlists']) "
        "show ComTail's decisions; save <= 5 means no ret-tail merge.",
        universal=False,
        caveat="the final layout of duplicated tails depends on the merge "
        "direction (ComTail keep-candidate vs ComCode keep-fall-through); "
        "PS keep-first vs RC keep-last on devolve_a_building is the open "
        "case -- check the cm saves before assuming a merge fired."),
    RuleVerdict(
        rule="125", title="Optimizer code MOTION across functions (CallRet + StraightenCode)",
        status="verified",
        hint="A function whose PS body carries ZERO -d1 line records (the "
        "moved-code marker, `c2 moved-code`): the peephole queue hauled its "
        "head/body to a caller's jmp site.  Fix the function's FILE POSITION "
        "first (the blob's L+n labels give the original TU position), then "
        "fix the body per sxs.  Do not chase the extent diff as if it were "
        "codegen.",
        mechanism="The peephole instruction queue spans function boundaries: "
        "CallRet rewrites `call X; ret` -> `jmp X`; StraightenCode moves "
        "[X's label .. first jmp/ret] up to an unconditional jmp site and "
        "deletes the jmp; symbols travel with the label while OC_LINENUM "
        "records are orphaned (NextIns/PrevIns skip OC_INFO).",
        ow_v1="bld/cg/c/optpull.c::CallRet/StraightenCode/CloneCode; "
        "optutil.c NextIns/PrevIns OC_INFO skip.",
        re_10_0a="`helping` (52b body at 0x32409, zero line records, "
        "continuation at 0x324C9).  Donor-extent recipe in priority-targets.",
        oracle=None,
        instrumentation="`c2 moved-code` lists the zero-line-record functions; "
        "tail_merge.foreign_branches maps block ownership."),
    RuleVerdict(
        rule="141", title="One-sided xor argreg before a shared call: live value vs literal 0",
        status="verified",
        hint="A one-sided `xor edx/ebx/ecx, <same>` followed by EQUAL "
        "arg-staging rows up to an EQUAL call: the side WITHOUT the xor "
        "passes a VARIABLE already live in the register (often the value "
        "computed just above), the side WITH it passes literal 0.  "
        "RC-only xor -> trace PS's register at the callsite and pass that "
        "expression; PS-only xor -> pass literal 0.",
        mechanism="the variable's CSE/home already occupies the __watcall "
        "arg register, so no setup instruction is needed; a literal 0 "
        "must be materialised.",
        re_10_0a="war/raider/horde_trouble: chance_of_attack's 2nd arg is "
        "months_since_last_X (live in EDX from the ++); all byte-exact "
        "2026-06-12.  citizen_maraude_to_target's 3rd arg (xor ebx).",
        oracle="tests/test_rule_hints.py::TestRule141LiveArgVsZero",
        universal=True,
        caveat="EAX excluded (one-sided xor eax,eax is usually "
        "return-value setup, not arg staging)."),
    RuleVerdict(
        rule="142", title="Return constants staged via EDX: merged-return-suffix (&&-guard) shape",
        status="verified",
        hint="PS `mov edx, K` vs RC `mov eax, K` (same K) with PS's next "
        "insn `mov eax, edx` feeding the epilogue (return-0 block = "
        "`xor edx,edx; jmp <mov eax,edx>`): funnel the returns so they "
        "share the staged suffix -- `if (g1 && g2) { body; return 1; } "
        "return 0;`.  Plain per-site `return K;` goes straight to EAX.",
        mechanism="the &&-guard merges the failure edges into one block; "
        "the return-value temp materialises per path in a common staging "
        "register and ComTail merges the `mov eax,edx`+epilogue suffix.",
        re_10_0a="revolt_trouble byte-exact 2026-06-12; corpus witness "
        "known_world (empire.c, byte-exact).",
        oracle="tests/test_rule_hints.py::TestRule142ReturnStagingViaEdx",
        universal=False,
        caveat="the *_trouble family showed the donor geometry is coupled "
        "across the TU: which function physically owns the merged tail "
        "depends on the sibling shapes; converge the family together."),
    RuleVerdict(
        rule="143", title="Consecutive compound RMWs on one memory lvalue: store-forward copy chain",
        status="verified",
        hint="PS byte-reg copy chain (mov b2,b1 between byte ALU steps, "
        "one load, one final store) vs RC fused in-place ALU: write "
        "CONSECUTIVE compound RMWs on the memory lvalue itself "
        "(`m &= A; m |= b; m &= C;`).  NOT the Rule 17 register split -- "
        "on memory it emits two RMWs and regresses.",
        mechanism="store-forwarding + dead-store elimination: each "
        "statement's load forwards from the previous pending value into "
        "a FRESH byte register (the copies); intermediate stores die.  "
        "Side effect: later arms reading the field get per-arm fresh "
        "regs, keeping their stores byte-distinct (not ComTail-merged).",
        re_10_0a="do_land_trade 171b -> 0 (2026-06-12); Mac oracle showed "
        "the three verbatim RMW statements.",
        oracle="tests/test_rule_hints.py::TestRule143MemoryRmwChain",
        universal=False,
        caveat="fusion is pressure-sensitive: road_ramifications' wall "
        "arm REGRESSED on the split and kept the combined "
        "single-expression form -- verify per function."),
    RuleVerdict(
        rule="144", title="while (i++ < N): post-increment tested at the top",
        status="verified",
        hint="PS loop head `mov rA,rB; inc rB; cmp rA,imm` with a backward "
        "jump targeting the mov: the compare tests the OLD value while "
        "the counter already advanced.  Write `i = 0; while (i++ < N)`; "
        "a for-loop bottom inc cannot produce the triple.",
        mechanism="the post-increment's value-of-expression is the old "
        "value: front end emits copy-then-inc, the compare consumes the "
        "copy.",
        re_10_0a="get_region_invasion_points 93b -> 0 (2026-06-12).",
        oracle="tests/test_rule_hints.py::TestRule144WhileIPlusPlus",
        universal=True),
    RuleVerdict(
        rule="145", title="Signed % (1<<k) vs & (2^k-1)",
        status="verified",
        hint="One side `mov rD, 2^k ... idiv rD` (signed remainder), the "
        "other `and r, 2^k-1`: write whichever PS shows.  They are NOT "
        "interchangeable -- % has signed semantics for negative operands, "
        "so this is usually a SEMANTIC bug, not a codegen nuance.",
        mechanism="C semantics: a%b may be negative; Watcom cannot lower "
        "signed % by a power of two to a plain mask.",
        re_10_0a="barbarian_invades_city `(world_dir + 4) % 8` (the & 7 "
        "spelling was wrong); byte-exact 2026-06-12.",
        oracle="tests/test_rule_hints.py::TestRule145SignedRemVsMask",
        universal=True),
    RuleVerdict(
        rule="146", title="De-invent the local: repeated field reads CSE into the callee-save",
        status="verified",
        hint="Compare chain with RC testing EAX (short 3D encodings) and "
        "PS a callee-save (81 /7), same immediates, def row = memory "
        "load: delete the named local and spell the global/field read in "
        "EACH compare -- Watcom's CSE homes the repeated reads in the "
        "callee-save exactly as PS.  Compare-chain instance of Rule 116.",
        mechanism="a named local fuses with its defining load's result "
        "(EAX); the CSE temp of repeated reads allocates separately and "
        "prefers a callee-save when its range spans the chain's arms.",
        re_10_0a="barbarian_invades_city total_troops->EBX (264b -> 0); "
        "continue_battle battle_state->EBP; get_morale_and_readiness "
        "(all 2026-06-12).",
        oracle="tests/test_rule_hints.py::TestRule146DeinventCseCalleeSave",
        universal=False,
        caveat="the CSE only spans arms whose path has no aliasing store "
        "or call to the chain; if RC then RELOADS per test instead, the "
        "local was real (continue_battle needed the de-invent, but its "
        "residue moved elsewhere)."),
    RuleVerdict(
        rule="147", title="Array element width/stride mismatch: scaled dword vs unscaled byte loads",
        status="verified",
        hint="One side reads a 4-byte field through a SCALED index "
        "(`mov r32, [rI*4 + disp]`), the other a 1-byte field unscaled "
        "through the SAME index value (`mov r8, byte [rI + disp]`): the "
        "array's element/field type is wrong in entities.h / "
        "_TYPE_OVERRIDES.  Width and stride diverge TOGETHER => it is "
        "the declaration, not regalloc.  One header edit moves every "
        "user of the array.",
        mechanism="the front end derives both the operand width and the "
        "index scale from the declared element type.",
        re_10_0a="struct troop_numbers_rec char->int flipped all four "
        "*_trouble functions (2026-06-12).",
        oracle="tests/test_rule_hints.py::TestRule147ElementWidthStride",
        universal=True),
    RuleVerdict(
        rule="148", title="Mid-function epilogue funnel: jmp-to-end vs inlined per-exit epilogue copies",
        status="verified",
        hint="PS funnels >=2 early exits via `jmp <end>` while RC inlines "
        "the full epilogue (multi-pop + ret) at each early-exit site.  "
        "Triggered when the final epilogue is > 5 bytes (5+ callee-save "
        "pushes, frameless function): CloneCode declines to inline, PS "
        "keeps each early exit as a 2-byte jmp.  Source recipe: rewrite "
        "every early `return ...;` as `goto end;` and add a single "
        "`end:;` immediately before the natural body epilogue.",
        mechanism="ObjLen(jmp)=5 at OptForSize=50 with CloneCode's "
        "MAX_CLONE_SIZE=5: epilogues <=5b inline at every exit on BOTH "
        "sides (no diff), epilogues >5b inline on RC but stay as jmp on "
        "PS when the source uses goto-end.  Sibling of Rule 135 (the "
        "FRAMED mid-epilogue class; this rule is the frameless dual: "
        "goto-end works for frameless functions whose epilogue crosses "
        "the 5b threshold).  OPPOSITE of Rule 92 (PS-inlines per-return "
        "vs RC-funnels): Rule 148 is RC-inlines vs PS-funnels.",
        re_10_0a="initreg_game_loop 228b -> 17b (gloops.c, 2026-06-13): "
        "5 callee-save pushes -> 6b epilogue, 4 early-exit sites -> "
        "added `goto end;` everywhere + `end:;` sentinel.  PS jmps "
        "@+0x102,+0x10b,+0x115,+0x125,+0x136 -> 0x16b.",
        oracle="tests/test_frame_hints.py::TestEpilogueFunnel",
        instrumentation="",
        universal=False,
        caveat="frameless functions only -- framed functions (`sub esp,N` "
        "in prologue) follow Rule 135 instead; no current corpus fires "
        "2026-06-13 (worked example initreg_game_loop is the only known "
        "candidate, already fixed)."),
    RuleVerdict(
        rule="149", title="Global cached in extra callee-save: de-invent the pessimizing local",
        status="verified",
        hint="PS uses an EXTRA callee-save register (vs RC) holding a "
        "global across one or more calls: `mov X, [global]` followed by "
        "uses of X after `call`.  In OUR source, a local copies this "
        "global (`<type> v = <global>;`) and the local's range terminates "
        "BEFORE the call, forcing post-call reloads.  Source recipe: "
        "DELETE the local, read the global directly at each use site -- "
        "the compiler enregisters the global in a callee-save across the "
        "calls.  Hint surfaces the SPECIFIC global address and call "
        "count so the agent can locate the local on the RC side.",
        mechanism="a local copy creates a named-value web with its "
        "defining load result; that web fights for caller-save (EAX) "
        "and dies on the first call.  Reading the global directly leaves "
        "the CSE temp of repeated reads, which the allocator prefers in "
        "a callee-save when its range spans the calls.  Specializes "
        "Rule 146 (which catches the compare-chain instance) and "
        "pragma_hints `ps_extra_callee_save` (which is the general "
        "diagnostic line).",
        re_10_0a="initreg_game_loop's `region` (gloops.c, 2026-06-13): "
        "removing the `region = region_over;` local + reading region_over "
        "directly across this_region() forced PS's seat (EBP); 228b->17b.",
        oracle="tests/test_frame_hints.py::TestGlobalInExtraCalleeSave",
        instrumentation="the `al` alloc trace surfaces the value PS holds "
        "in the extra callee-save (named local or CSE temp); pair with "
        "this static hint when the named local needs identifying.",
        universal=False,
        caveat="OPPOSITE direction of pragma_hints case (a): "
        "ps_extra_callee_save's (a) suggestion is to ADD a local "
        "covering the call, but the right move is sometimes the inverse "
        "-- when our build ALREADY has a local that pessimizes, REMOVE "
        "it.  Corpus fire 2026-06-13: place2_a_building_top (EBP holds "
        "[0x3480c] across 3 calls; unreviewed lead)."),
    RuleVerdict(
        rule="150", title="`goto label` (mid-function) vs `return` (epilogue) -- INVERSE of Rule 148",
        status="verified",
        hint="Multiple jcc/jmp sites where PS jumps to the function "
        "epilogue (pop…pop;ret) but RC jumps to a mid-function LABEL "
        "whose body is `if (...) return;` plus cleanup code.  PS's "
        "source uses `return;` at these sites; ours uses `goto "
        "<label>;` to a label that has additional cleanup the early-"
        "exit paths should SKIP.  Replace each `goto X;` with `return;` "
        "-- Watcom emits a jmp directly to the epilogue (matching PS) "
        "and the cleanup remains reachable via natural fall-through.",
        mechanism="the goto/label sites compile to `jmp <label_offset>`; "
        "plain `return;` compiles to `jmp <epilogue_offset>` (or inline "
        "pop+ret).  When the goto target is mid-function but the early-"
        "exit paths shouldn't execute the cleanup at/after the label, "
        "the goto is semantically dead code -- replace with return.",
        re_10_0a="main_game_loop (gloops.c, 2026-06-13): three `if "
        "(game_state == 1/2/3) goto restart_check;` sites -> three `if "
        "... return;` sites; the restart_check label's cleanup (decay "
        "counters, message refresh, ambient FX) is irrelevant on game-"
        "end states 1/2/3.  Diff 454b -> 0.",
        oracle="tests/test_rule_hints.py::TestRule150GotoLabelVsReturn",
        universal=True,
        caveat="INVERSE direction of Rule 148: Rule 148 says "
        "convert return->goto-end when the epilogue is big and RC "
        "inlines per-exit; Rule 150 says convert goto-label->return "
        "when PS already funnels to epilogue.  Detector requires >=2 "
        "jumps converging on the same PS epilogue target (lone matches "
        "are likely Rule 92 or similar single-site patterns)."),
    RuleVerdict(
        rule="151",
        title="Byte-pack via array+offset+cast triggers different zext idiom "
              "than via pointer-alias",
        status="verified",
        hint="3-byte little-endian load `result = buf[ptr+4] + (buf[ptr+5]"
             "<<8) + (buf[ptr+6]<<16);` with EXPLICIT `(unsigned char)` casts "
             "on a `buf[ptr+N]` indexed access selects WCC's xor+mov-low "
             "zext idiom for the low/mid bytes but the and-mask idiom for "
             "the high (<<16) byte, with the register routing of the high-"
             "byte temp cascading through 15-20 bytes.  FIX: use a pointer "
             "alias `unsigned char *p = buf + ptr;` then `p[4] + (p[5]<<8) "
             "+ (p[6]<<16);` with NO casts (buf is already unsigned char*).  "
             "Byte-exact.",
        mechanism="the `(unsigned char)buf[ptr+N]` form forces the cast IL "
                  "node (OP_CONVERT_U8_U32) into the tree at a different "
                  "position than the bare `p[N]` form, which changes the "
                  "tree-build order of the byte-load conflicts and thus "
                  "their register allocation; the high-byte temp lands in "
                  "a different reg than PS picks, and the zext idiom (xor+"
                  "mov-low vs mov-low+and-mask) cascades through every "
                  "subsequent encoding.",
        re_10_0a="write_clipped_image (lib32.c, 2026-06-13): explicit-cast "
                 "form had 19b residue, pointer-alias form went to 2b.  "
                 "general_sprite + write_image (display.c, lib32.c) use the "
                 "pointer-alias form and are byte-exact.",
        oracle=None,
        universal=True,
        caveat="Specifically for the THREE-byte pack with `<<16` on the "
               "high byte.  The two-byte pack `p[0] + (p[1]<<8)` works "
               "either way (already byte-exact in many functions with the "
               "explicit-cast form).  Discovered via cluster #0 "
               "representative -- the cluster has 15 members but only "
               "functions with this specific 3-byte-pack expression benefit; "
               "the rest of cluster #0 has different reg-swap causes."),
    RuleVerdict(
        rule="152",
        title="Multi-byte-value temps held as `char` spill where `int` stay "
              "in registers",
        status="verified",
        hint="When swapping or shuffling several byte-sized fields between "
             "two struct elements via `char temp_x, temp_y;` locals, PS "
             "sign-extends the loads to int and keeps the temps in dword "
             "registers (movsx ecx,byte[]; mov ecx -> store).  Our `char` "
             "temps push WCC to use byte registers under pressure, which "
             "often spill: `mov bl,[]; mov [esp],bl` (load+spill).  FIX: "
             "declare the temps as `int` not `char` -- WCC then sign-"
             "extends at the load and keeps them in dword regs without "
             "spilling.",
        mechanism="`char` temps are class N_TEMP with byte-width regclass; "
                  "on a routine with high register pressure they compete "
                  "for the same 4 byte-aliasing slots (AL/AH/BL/BH/CL/CH/"
                  "DL/DH) but the byte-spill cost is favourable vs dword. "
                  "PS's int-typed temps land in the dword regclass with 6 "
                  "candidates (EAX/EDX/EBX/ECX/ESI/EDI) and the allocator "
                  "finds a non-spilling home.",
        re_10_0a="swap_2_figures (battle.c, 2026-06-13): char->int on "
                 "temp_x/temp_y closed 78b -> 26b (-52b).  PS emits "
                 "movsx ecx,byte[figure_list+0x8] for temp_x; we emit "
                 "mov bl,[m]+spill to [esp+8] with the char form.",
        oracle=None,
        universal=False,
        caveat="Conditional on the function having register pressure that "
               "makes the char form spill.  In low-pressure routines the "
               "char form may compile identically.  Cluster #15 (4 "
               "functions, signature 'Byte-reg swap'): swap_2_figures "
               "benefits; the other 3 members (get_region_revolt_points, "
               "get_fig_missile_image, figure_update) have different "
               "causes -- get_fig_missile_image specifically requires "
               "`char` per its Mac-oracle PROBE.  Run the dossier first "
               "to confirm the spill signature before applying.  "
               "DIRECTION DISCRIMINATOR (do not blanket-apply `->int`): "
               "this rule is for STRUCT-FIELD-SWAP temps that PS keeps in "
               "dword registers.  The OPPOSITE regime exists for per-cell "
               "SCRATCH locals (kind/level/cooldown/staged in the evolver "
               "sweep): PS byte-STORES them (`mov [esp+N],al` + `add "
               "byte[esp+N],K` in-place + `xor r,r; mov r.lo,[esp+N]; cmp` "
               "reloads), so they must be `unsigned char`, NOT int -- "
               "byte-typing them packs PS's byte slots, kills Rule "
               "49b/73/19 truncations, and can resolve a frame-shift ROOT "
               "(evolve_water_table 587->363, business_output 572->144). "
               "The discriminator is Rule 19's spill-width READ of the PS "
               "asm: dword register => int (this rule); byte stack slot "
               "=> unsigned char (the scratch regime).  Read PS first; "
               "never pick the width from the C alone."),
    RuleVerdict(
        rule="156",
        title="Tail store of a known-zero register is the byte-signature of "
              "a `= 0` source (not `= <that var>`)",
        status="verified",
        hint="PS stores a REGISTER at a tail/early-exit (`mov [mem], r8`) "
             "where that r8 was just `test`ed (or `and`+tested) and the "
             "branch FELL THROUGH -> r8 is provably 0 there.  PS reused the "
             "known-zero register for a `= 0` store instead of `mov [mem],0` "
             "/ `xor r,r`.  Transcribe the statement as `= 0` (or the "
             "provably-zero var collapsed to its constant), NOT as the "
             "variable occupying the register.  This is LOAD-BEARING: the "
             "store is also an IL *use*, so `= <var>` inflates that var's "
             "CalcSavings and flips its register seat -- removing the use "
             "(`= 0`) frequently unblocks a Rule 115 / 28a decl/use-order "
             "byte-seat tie.",
        mechanism="The store counts as a `use_save` reference in "
                  "regsave.c/savcode.h CalcSavings.  `= <var>` gives the "
                  "variable an extra use -> higher savings -> SortConflicts "
                  "allocates it earlier and GiveBestReg greedily takes the "
                  "first byte reg (AL).  `= 0` drops the use; the compiler "
                  "satisfies the constant by recycling the dead, "
                  "flow-proven-zero register (no fresh xor / immediate).",
        re_10_0a="get_education_ov_image (landfill.c, 2026-06-18): `= 0` (not "
                 "`= school`) was 1 of 3 coupled levers (with all-uchar + "
                 "Rule 115 kind-declared-last) that closed 44b -> 0b.  PS "
                 "tail `mov [eax+landfill_pool], dh` with dh=school proven 0 "
                 "after `if(school!=0)return;`.",
        oracle="docs/codegen-experiments/education-ov-seats.py",
        universal=False,
        caveat="The `= 0` spelling is only faithful when the path is "
               "provably reached with the variable == 0 (PS stores the "
               "register precisely because the flow proved it zero).  The "
               "downstream seat flip is then a Rule 115/28a tie, so it only "
               "changes bytes on functions where that tie is live."),
    RuleVerdict(
        rule="157",
        title="Byte temp 1 savings-unit SHORT of AL vs a dword rival -- the "
              "+1 use IS the widen (irreducible faithfully)",
        status="verified",
        hint="A byte temp (an `unsigned char` field read into a local) loses "
             "AL to a competing DWORD value (a loop direction/index var) that "
             "out-ranks it by a SMALL savings margin (1-2 units), so the byte "
             "seats in DL and the dword takes EAX -- the INVERSE of Rule 156.  "
             "This is a SAVINGS GAP, not an equal-savings tie: the `Cascade:` "
             "line says `needs a SAVINGS change`, NOT `REACHABLE`, so reorders "
             "(decl-swap / Rule 28a/115) PROVABLY cannot move it (verified: 0 "
             "improvements at depth 2; `c2 savings <fn> --var X` prints the "
             "per-ref ledger behind both values).  The ONLY lever is to raise the byte "
             "temp's CalcSavings by +1 use -- but every emitted `v` op IS the "
             "byte divergence: an explicit `v & 0xff` adds the use AND a 2nd "
             "widen (PS shares ONE in-place `and reg,0xff` across compare+"
             "store; the extra mask forces `movzx <rival>,al` + a separate "
             "`and`), a duplicate `v!=0` emits a 2nd `test`, a named int temp "
             "`vi=v` COALESCES back, and folded refs (`v-v`,`v&0`,`v*0`) drop "
             "before CalcSavings.  PROOF the seat is the whole diff: adding "
             "the +1 (e.g. `best = v & 0xff`) flips the ENTIRE layout to PS "
             "(push ebp, dir->EDX, i->ECX, v->AL) -- but leaves the 2nd-widen "
             "residue.  CORRECT LEVER is a SAVINGS change on the RIVAL, not "
             "the byte: Rule 156 (`= 0` instead of `= <provably-0 var>` drops "
             "a rival store-use -- the closeable inverse, e.g. "
             "get_education_ov_image), Rule 123 (merge a split rival temp), or "
             "de-invent a rival local (`c2 triage <fn>`).  IRREDUCIBLE only "
             "when the rival's refs are ALL load-bearing (no `=0`/merge/"
             "de-invent applies) -- THEN park.  Sibling of Rule 156 (same "
             "CalcSavings store-use lever, opposite sign) and the "
             "font_format_split (lib32.c) `and reg,0xff` vs `movzx` byte-squat "
             "pressure tie.",
        mechanism="CalcSavings (regsave.c) counts each `v` reference as a "
                  "use_save; the byte temp's references (load, test, one "
                  "shared widen feeding compare+store) sum to exactly ONE "
                  "unit below the dword rival, so SortConflicts allocates the "
                  "rival first and GiveBestReg gives it EAX, masking AL out of "
                  "the byte temp's candidate set (NeighboursUse).  Raising the "
                  "byte temp's savings requires an extra reference, which the "
                  "back end must MATERIALISE as an instruction -- and that "
                  "instruction is exactly the widen/test that diverges from "
                  "PS's shared in-place `and`.  Non-monotonic: +2 uses "
                  "OVERSHOOTS and re-breaks the layout (regalloc-model warns).",
        re_10_0a="get_best_elastic_value (map.c, 2026-06-19): `unsigned char "
                 "v` widen matches PS but v->DL/dir->EAX (139b); `best = v & "
                 "0xff` (+1 use) flips to PS's full layout 139b->98b but adds "
                 "the 2nd widen; both-mask (+2) overshoots back to 139b.  "
                 "Committed source stays `int v` (107b, eager widen).  Twin: "
                 "get_best_rm_elastic_value (same residue).",
        oracle="docs/codegen-experiments/get_best_elastic_value.py "
               "(store-mask-FLIP trial = the 98b layout witness).",
        universal=False,
        caveat="Detector (byte-seat CASE E) is keyed off the VALIDATED "
               "cascade replay search ('needs a SAVINGS change' for the "
               "byte's parent dword pair), NOT a savings-delta proxy: a raw "
               "delta between two alloc rows does NOT prove they are the "
               "competing OVERLAPPING pair -- NeighboursUse (regalloc.c:1157) "
               "excludes a register only when an *overlapping* value holds "
               "it, independent of savings magnitude.  cascade returns None "
               "when undecidable (>250 rows / suppressed / H2-unreliable) -- "
               "then it is NOT claimed (falls back to CASE A/D).  The savings-"
               "gap (vs equal-savings tie) is the universal part -- permute "
               "provably can't move it; whether it CLOSES depends on the "
               "rival being reducible (Rule 156/123/de-invent), so HARD, not "
               "auto-PARK.  Confirm with `c2 regtrace <fn> --explain`."),
    RuleVerdict(
        rule="158",
        title="A folded-away always-true guard (`uchar >= 0 &&`) still roots "
              "a CSE partition",
        status="verified",
        hint="An else-if chain over an unsigned char selector where, vs PS: "
             "(a) RC hoists a very-busy expression ABOVE the chain-head "
             "compare while PS's def sits one level lower (inside the first "
             "arm, with an explicit `test eax,eax` where RC branches on AND "
             "flags); (b) PS re-zexts the selector at the next else-if level "
             "(binir PS-only zext_byte_load); (c) PS's call sites recompute "
             "the hoisted expression inline and tail-merge DEEPER.  The "
             "source had an always-true guard (`x >= 0 &&`) that Watcom "
             "FOLDS to zero bytes -- but only after the flow graph exists, "
             "so the dead edge gives the chain-head TWO fail edges and the "
             "next level becomes a PARTITION_ROOT (cse.c:344), blocking "
             "CommonSex pairing across it.  ADD the guard; W111 is expected.",
        mechanism="FindPartition roots every block with inputs != 1; "
                  "ProcessExpr very-busy hoisting + zext CSE cannot pair "
                  "across partition roots.  WhichIsAncestor places a hoisted "
                  "def before the ancestor block's trailing condition insns "
                  "(hence the explicit test).  The guard's compare folds "
                  "AFTER flow-graph construction, so it shapes partitions "
                  "while emitting nothing.",
        re_10_0a="evolve_land_value (evolver.c, 2026-07-03): single token "
                 "`kind >= 0 &&` closed the whole 247-byte diff (commit "
                 "e6ea8769; commit message says Rule 157 -- renumbered 158 "
                 "for the registry collision).  Minimal wcc386 repro flips "
                 "all three observables at once.",
        oracle="c2 win-verify --guards (corpus sweep) / c2 diagnose "
               "(win-guard line): the guard is INVISIBLE in PS.EXE but "
               "LITERAL in the MSVC /Od CAESAR2.EXE build -- a one-sided "
               "zero-compare run (xor/mov-al/test/jl) in the aligned win "
               "diff.  PS-side co-occurrence fingerprint in the binir-shape "
               "hint (PS-only zext_byte_load + zero_test_jcc-vs-"
               "branch_flag_jcc).",
        universal=True),
]


# ── Universality classification ────────────────────────────────────────────────
# Rules NOT in this map are deterministic source-shape rules (universal=True):
# the C form selects the codegen via a front-end/optab/addressing path with no
# allocator involvement, so the lever always reproduces PS's shape.  The rules
# below are CONDITIONAL -- the caveat states exactly when/why they don't hold.
# (This is the instrumentation flag generalised: every allocator/pressure/queue
# rule is here; every front-end/optab rule is not.)
_CONDITIONAL: dict[str, str] = {
    "1":  "small-leaf only; the inline->EBX side rides the FindRegister rover "
          "cursor, so it shifts with the count of prior RISCified loads. Read "
          "the actual prologue push (ebx vs edx) -- don't assume.",
    "2":  "EDX-first vs EAX-first FLIPS on whether a downstream call consumes the "
          "divide result (the doc's 3-row table). Read the consumer.",
    "5":  "holds for plain `dst = g/k;`; a divide used as a CALL ARGUMENT may pick "
          "a different layout -- if PS already shows sar/shl/sbb there, leave the "
          "ternary-bias form.",
    "5b": "the bare-shift observation holds, but the FIX regresses when the value "
          "shares its load with a `& (2^N-1)` parity sibling -- leave those as /2.",
    "5c": "NON-DETERMINISTIC from source: whether the `%2^N` divisor temp is "
          "CSE-shared with the adjacent `/2^N` depends on register pressure, so "
          "the SAME source can emit the shift form in one build and shared-idiv "
          "in another. Match PS's disasm; don't force it.",
    "7b": "the split form's extra callee-save push (and thus the byte delta) "
          "depends on register pressure.",
    "11": "the register-keeping that yields the 8-bit cmp is pressure-dependent.",
    "13": "the two forms only differ once they TAIL-MERGE (ComTail/Rule 15); the "
          "merge needs the call-sharing family decompiled in source order.",
    "15": "reproducible at ANY distance within a TU (RetList persists the whole "
          "TU; never evicted here). A miss means the merge family isn't fully "
          "decompiled in PS's source order -- SOURCE-FIXABLE: decompile the donor "
          "+ intervening functions in order.",
    "16": "a jmp short<->near distance CASCADE, not a local source choice -- "
          "fixable only by decompiling the intervening stubs so the distance "
          "crosses +/-127.",
    "17": "the extra register copy appears for the SPLIT form, but plain globals "
          "emit two memory writes (Rule 3) while struct/array writes fold to one "
          "-- the shape depends on the lvalue kind.",
    "18": "only manifests under HIGH register pressure; at low pressure both forms "
          "emit LEA and there is NO diff.",
    "20": "only when the terminal index is actually reused after the loop; the "
          "loop-counter form also adds a register live-out (save/restore).",
    "24": "a pure regalloc spill-victim TIE -- no Rule fires, byte budget matches. "
          "Needs the live `al` trace to know which arg PS spills.",
    "27": "the parm-copy order follows the conflict-allocation order, not the "
          "source order directly -- a regalloc tie.",
    "28": "an equal-savings GiveBestReg TIE. Levers (commute use / swap decls) "
          "work for NAMED locals; CSE-hoisted-global swaps have no source handle "
          "and are irreducible residue.",
    "28b":"a regalloc-pressure outcome; many small math helpers (totalXpercent) "
          "have no source fix -- known residue.",
    "29": "depends on value-pool liveness analysis; applying it cascades the "
          "downstream jmp displacements (often into a Rule 15 epilogue).",
    "121": "a rover-cursor outcome: fires only when the diverging register is a "
           "RISCified scratch with NO conflict binding (no row in the alloc "
           "table -- check the `fr` trace, and simulate the +1 with "
           "tools/rover_sim.py before editing source).",
    "122": "a rover-cursor outcome (same gate as Rule 121); prove it with the "
           "fr reorder test (swap the arms' events in simulation) before "
           "editing -- a conflict-bound register swap is NOT this rule.",
    "124": "a direct READ, not a guess: only act on what cand_scores shows; "
           "the three knobs interact (changing savings order changes Given "
           "content downstream) -- re-read after every edit.",
    "85": "the regpair form is AMBIGUOUS in-function: 58 of 65 corpus sites "
          "are merged-call-site ARGS, not returns -- always use the resolved "
          "verdict, never the raw pattern.",
    "126": "interference is ALLOCATION-ORDER dependent: the same source can "
           "mask or not depending on which conflict allocates first -- read "
           "the walk (sav + wr + cand_scores) per variant; never conclude "
           "from one build.",
    "127": "the rover-cursor shift is WALK-ORDER dependent (the CSE temp "
           "advances the persistent byte cursor at ITS walk position, which "
           "can be a tail-moved block far from the source line); read the "
           "fr stream + rover sim per variant, and confirm the PS-side "
           "zext_copy_and marker before applying -- a plain reloaded "
           "expression (two loads in asm) is NOT this rule.",
    "125": "donor-extent diffs are usually the functions INSIDE the extent, "
           "not the named function: read the PS line labels of the hosted "
           "blob -- L+n relative to the extent owner reveals the ORIGINAL "
           "file position of the blob's source function.  Reorder the .c "
           "to match and the optimizer motion (body-in-place + head moved "
           "to serve a fallthrough) reproduces by itself "
           "(go_16m_palette/fade_to_palette: 5/7 cluster exact on reorder "
           "alone).",
    "131": "only meaningful when the shared body is byte-identical across "
           "arms (ComTail must merge it); a body with arm-specific values "
           "stays duplicated and the byte diff is structural, not a line "
           "question.",
    "130": "the chain detector requires the final store to memory; "
           "register-accumulated sums (local result) or chains broken by "
           "interleaved scheduling are not claimed -- check fr+lc records "
           "on the RC side when in doubt.  Term ORDER inside the chain is "
           "the source operand order (left-assoc).",
    "129": "totals-based and fixup-blind on the RC side (relocatable objs "
           "print pre-fixup addends): per-address pairing is only valid on "
           "the PS side, and structural differences (loops, dup'd tails) "
           "also change load counts -- confirm the call-boundary pattern "
           "in the sxs view before deleting a local.",
    "128": "the form split is only meaningful on CONST-store runs (>=2 same "
           "value): single stores stay imm-form in both shapes, and a "
           "reg-run can also come from value-pool reuse of a register that "
           "happens to hold K -- confirm the materialize/displacement "
           "signature (fixup per access vs base register) before editing.",
    "123": "an allocation-ORDER outcome: only fires when the merged temp's "
           "summed savings actually exceed the competitor's (check the al "
           "rows / Merge hint); with no savings crossover the in-place form "
           "is byte-identical to the split form.",
}
from dataclasses import replace as _replace
VERDICTS = [
    (_replace(v, universal=False, caveat=_CONDITIONAL[v.rule])
     if v.rule in _CONDITIONAL else v)
    for v in VERDICTS
]

_BY_RULE = {v.rule: v for v in VERDICTS}
_RULE_ID = re.compile(r"Rule\s+([0-9]+[a-z]?)")


def verdict_for(rule: str) -> RuleVerdict | None:
    """Lookup by bare rule id, e.g. ``verdict_for("28b")``."""
    return _BY_RULE.get(str(rule).strip())


def reviewed_rules() -> list[str]:
    return [v.rule for v in VERDICTS]


def verdicts_for_hist(rule_names) -> list[RuleVerdict]:
    """Given cited rule labels (e.g. ``"Rule 9"``) from the decomp-verify
    histogram, return the registry verdicts that exist, de-duped in order."""
    seen: set[str] = set()
    out: list[RuleVerdict] = []
    for label in rule_names:
        m = _RULE_ID.search(str(label))
        if not m:
            continue
        rid = m.group(1)
        if rid in seen:
            continue
        v = verdict_for(rid)
        if v is not None:
            seen.add(rid)
            out.append(v)
    return out


_MARK = {"verified": "[green]\u2713[/]", "corrected": "[yellow]\u26a0 corrected[/]",
         "debunked": "[red]\u2717 debunked[/]", "unreviewed": "[dim]?[/]"}


def render_verdict_lines(verdicts: list[RuleVerdict]) -> list[str]:
    """One ACTIONABLE line per cited+reviewed rule: a universality tag, the
    verdict mark, the hint, then (for conditional rules) the caveat that says
    when it fails to hold, and (for allocator-backed rules) the live trace data
    needed to apply it.  Corrected/debunked rules append the real mechanism."""
    lines: list[str] = []
    for v in verdicts:
        mark = _MARK.get(v.status, v.status)
        tier = ("[green]deterministic[/]" if v.universal
                else "[yellow]CONDITIONAL[/]")
        line = f"Rule {v.rule} {mark} {tier}: {v.hint}"
        if not v.universal and v.caveat:
            line += f"  [does NOT always hold: {v.caveat}]"
        if v.status in ("corrected", "debunked"):
            line += f"  [why: {v.mechanism}]"
        if v.instrumentation:
            line += f"  [{v.instrumentation}]"
        lines.append(line)
    return lines


def instrumented_rules() -> list[str]:
    """Rules whose hint needs live instrumented-compiler data to give the
    specific per-function fix (not determinable from the diff alone)."""
    return [v.rule for v in VERDICTS if v.instrumentation]


def conditional_rules() -> list[str]:
    """Non-universal rules (allocator/pressure/layout/queue-dependent)."""
    return [v.rule for v in VERDICTS if not v.universal]
