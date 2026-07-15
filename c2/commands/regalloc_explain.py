"""Register-allocation model explainer for `decomp-verify`.

Given the PS and recomp instruction lists for a diffing function, classify the
register-allocation divergence into one of the proven model layers and emit the
exact source lever.  The model + constants are documented in
``watcom10.0a repo docs/wcc386-re/regalloc-model.md`` and proven by the self-asserting
experiments in ``docs/codegen-experiments/regalloc-*.py``.

The 7 layers (see the model doc):

  (0) TYPE        -> register class (char/short/int/ptr)
  (1) EAX-boundary-> value in EAX iff its range never crosses a call/mul/div
  (2) SAVINGS     -> uses ranked; cost model W=10 loop weight, callee-save costs 2
  (3) USE-ORDER   -> equal savings -> LAST-use order: earliest-last-use
                     value gets the higher reg (proof: regalloc-last-use.py;
                     the Rule 28a lever)
  (4) OVERRIDES   -> hard constraints (shift->ECX, idiv->EAX:EDX) + move-elim
  (5) LOOPS       -> invariant hoist-vs-reload, aliasing-gated
  (6) CAPACITY    -> 7 GP regs; 6 across a call; beyond that, stack spill

This module deliberately focuses on (5) and (6) (not covered by the existing
prologue/rule hints) plus a model-aware *summary*: when the register layout
matches, it tells the agent the diff is **outside** the regalloc model
(instruction-selection / strength-reduction / tail-merge / branch-encoding).

`InsnT = (address:int, size:int, raw:bytes, asm:str)` where ``asm`` is
``"<mnemonic> <op_str>"`` (lower-case).
"""
from __future__ import annotations
from dataclasses import dataclass

_CALLEE_SAVE = ("ebx", "ecx", "edx", "esi", "edi", "ebp")


@dataclass
class RegallocHint:
    layer: int            # model layer number (0-6), -1 = outside model
    summary: str          # one-line classification
    lever: str            # the source property / lever


def _asm(ins) -> str:
    return ins[3]


def _callee_pushes(insns) -> list[str]:
    """Ordered callee-save registers pushed in the prologue (skips __CHK)."""
    start = 0
    if (len(insns) >= 2 and insns[0][3].startswith("push ")
            and insns[1][3].startswith("call ")):
        op = insns[0][3].split(None, 1)[1] if len(insns[0][3].split()) > 1 else ""
        if op[:1].isdigit() or op.startswith("0x"):
            start = 2
    out = []
    for ins in insns[start:]:
        p = ins[3].split(None, 1)
        if not p or p[0] != "push":
            break
        if len(p) > 1 and p[1] in _CALLEE_SAVE:
            out.append(p[1])
        else:
            break
    return out


def _stack_spill_bytes(insns) -> int:
    """Bytes reserved by a `sub esp, N` frame (0 if none) — register spill."""
    for ins in insns:
        a = ins[3]
        if a.startswith("sub esp,"):
            try:
                return int(a.split(",", 1)[1].strip(), 16)
            except ValueError:
                return 0
    return 0


def _loop_region(insns):
    """Index span (lo, hi) of the innermost loop = from the target of the last
    backward branch to that branch.  Returns None if no loop."""
    addr2i = {ins[0]: k for k, ins in enumerate(insns)}
    for k in range(len(insns) - 1, -1, -1):
        a = insns[k][3]
        if a[:1] == "j" and " " in a:
            tgt = a.split(None, 1)[1]
            try:
                t = int(tgt, 16)
            except ValueError:
                continue
            if t <= insns[k][0] and t in addr2i:
                return addr2i[t], k
    return None


def _global_reads_in_loop(insns) -> int:
    """Count instructions inside the innermost loop that read a global via a
    bare `dword ptr [disp32]` operand (no index register) — i.e. a reload."""
    reg = _loop_region(insns)
    if reg is None:
        return 0
    lo, hi = reg
    cnt = 0
    for ins in insns[lo:hi + 1]:
        op = ins[3]
        if "ptr [" not in op:
            continue
        # bracket content with no '*' (scale) and no '+'/'-' (base+disp) -> bare disp32 global
        seg = op[op.index("ptr [") + 5:]
        if "]" not in seg:
            continue
        inside = seg[:seg.index("]")]
        if "*" not in inside and "+" not in inside and "-" not in inside:
            cnt += 1
    return cnt


def _has_call(insns) -> bool:
    return any(ins[3].startswith("call ") for ins in insns)


_BYTE_OF = {"ebx": ("bl", "bh"), "ecx": ("cl", "ch"),
           "edx": ("dl", "dh"), "eax": ("al", "ah"),
           "esi": (), "edi": (), "ebp": ()}


def _reg_holds_const_store(insns, reg: str) -> bool:
    """True if ``reg`` (or its byte sub-register) is used only as a
    materialise-a-constant-then-store value: ``xor bl,bl`` / ``mov bl,K``
    followed by ``mov [mem], bl`` — a const-store temp (Rule 110) that landed
    in this (callee-save) register; the store FORM is deterministic, so the
    push is a regalloc (which-register) divergence, NOT a store-form lever."""
    forms = {reg} | set(_BYTE_OF.get(reg, ()))
    materialised = False
    stored = False
    for ins in insns:
        a = ins[3]
        parts = a.replace(",", " ").split()
        if not parts:
            continue
        # materialise a constant into the register
        if parts[0] == "xor" and len(parts) >= 3 and parts[1] in forms and parts[1] == parts[2]:
            materialised = True
        elif (parts[0] == "mov" and len(parts) >= 3 and parts[1] in forms
              and (parts[2][:1].isdigit() or parts[2].startswith("0x"))):
            materialised = True
        # store the register to memory: `mov [..], <reg>`
        elif parts[0] == "mov" and "ptr [" in a and a.rstrip().split()[-1] in forms:
            stored = True
    return materialised and stored


_ALL_GP = ("eax", "edx", "ebx", "ecx", "esi", "edi", "ebp")


def _reg_const_values(insns, reg: str) -> set:
    """Constants loaded into ``reg`` (or its byte sub-reg) via ``mov reg, K``."""
    forms = {reg} | set(_BYTE_OF.get(reg, ()))
    out: set = set()
    for ins in insns:
        p = ins[3].replace(",", " ").split()
        if (len(p) >= 3 and p[0] == "mov" and p[1] in forms
                and (p[2][:1].isdigit() or p[2].startswith(("0x", "-")))):
            out.add(p[2])
    return out


def _stores_const_immediate(insns, consts: set) -> bool:
    """True if any ``mov [mem], K`` stores one of ``consts`` as an immediate."""
    for ins in insns:
        a = ins[3]
        if not a.startswith("mov") or "," not in a:
            continue
        dest, src = a.split(",", 1)
        if "ptr [" in dest and src.strip() in consts:
            return True
    return False


# Rule-hint names that ARE register-allocation divergences (the layer-3
# equal-savings tie-break -- Rule 28a use-order / Rule 115 decl-order) even
# when the prologue push set matches (caller-saved register identity swaps).
_REGALLOC_RULES = {"Reg swap", "Byte-reg swap", "Rule 28", "Rule 28b"}
# Rule-hint names that are NOT regalloc — instruction selection / encoding etc.
_RULE_DESC = {
    "Rule 4": "Rule 4 (cmp operand order)",
    "Rule 16": "Rule 16 (short-vs-near branch encoding)",
    "Rule 62": "Rule 62 (x<<1 vs x+x instruction selection)",
    "Rule 42": "Rule 42 (cross-function tail-merge — fix the donor)",
}


def _rc_reg_savings(rc_alloc) -> dict:
    """Map lower-case register -> [savings ...] (desc) from OUR build's ACTUAL
    allocation (the -trace image), so the model layer can be confirmed/refuted
    against ground truth instead of guessed from the disassembly."""
    m: dict[str, list[int]] = {}
    for a in rc_alloc or ():
        r = (a.get("reg_name") or "").lower()
        if r:
            m.setdefault(r, []).append(a.get("savings", 0))
    for r in m:
        m[r].sort(reverse=True)
    return m


def explain(ps_insns, rc_insns, rule_hist: dict | None = None,
            has_body_diff: bool = False,
            rc_alloc: list | None = None,
            rc_spilled: int | None = None) -> RegallocHint | None:
    """Return the dominant register-allocation diagnosis, or None when the
    register layout already matches and the diff is fully a regalloc no-op.

    ``rule_hist`` is the ``decomp-verify`` rule histogram ({rule_name: count});
    it lets us catch caller-saved register-identity swaps (layer 3) that don't
    change the prologue push set.

    ``rc_alloc`` is OUR build's actual per-value allocation from the -trace
    image ([{savings, reg_name, ...}], reg_name None = spilled); ``rc_spilled``
    its spill count.  When present they turn the disasm guesses into GROUND
    TRUTH: confirm/refute the equal-savings tie (layer 3 vs 2), give the exact
    spill count + savings (layer 6) and name the divergent register's savings.
    Degrades to the disasm-only heuristics when absent."""
    rule_hist = rule_hist or {}
    rcsav = _rc_reg_savings(rc_alloc)
    ps_push = _callee_pushes(ps_insns)
    rc_push = _callee_pushes(rc_insns)
    ps_spill = _stack_spill_bytes(ps_insns)
    rc_spill = _stack_spill_bytes(rc_insns)
    ps_loop = _global_reads_in_loop(ps_insns)
    rc_loop = _global_reads_in_loop(rc_insns)

    # (6) CAPACITY — one side spills to the stack, the other doesn't.
    if ps_spill != rc_spill:
        more, less = ("RC", "PS") if rc_spill > ps_spill else ("PS", "RC")
        n = abs(rc_spill - ps_spill) // 4
        rc_sp = (sorted((a.get("savings", 0) for a in rc_alloc
                         if not a.get("reg_name")), reverse=True)
                 if rc_alloc is not None else None)
        # GROUND TRUTH: a bigger RC frame with ZERO register spills (trace) is
        # NOT a capacity spill -- the extra bytes are addressable/struct/array
        # locals.  The `sub esp` heuristic conflates the two; the trace
        # disambiguates.  Reclassify (unless a push divergence below is the
        # real story, in which case fall through to it).
        if rc_sp is not None and more == "RC" and not rc_sp:
            if ps_push == rc_push:
                return RegallocHint(
                    layer=6,
                    summary=("frame-size diff is STACK-RESIDENT LOCALS, not a "
                             "register spill (trace: RC spilled 0 values)"),
                    lever=("an addressable local (its address is taken, or a "
                           "struct/array) forces stack storage; PS had fewer or "
                           "packed them tighter.  Look for a local we take &of, "
                           "or a struct/array/extra named local -- this is NOT a "
                           "capacity/live-value problem, so do not chase register "
                           "pressure."),
                )
            # push set also diverges -> the push divergence is the diagnosis
        else:
            held_low = (min((s for sl in rcsav.values() for s in sl), default=None)
                        if rcsav else None)
            if rc_sp is None:
                note = ""
            elif more == "RC":
                note = (f"  [trace: RC actually spilled {len(rc_sp)} value(s) "
                        f"(savings {rc_sp}) -- drop the lowest, or cut the "
                        f"live-value count]")
            else:
                note = (f"  [trace: RC spilled {len(rc_sp)}; lowest HELD value "
                        f"savings={held_low} = the spill margin over PS]")
            return RegallocHint(
                layer=6,
                summary=(f"capacity/spill: {more} spills ~{n} value(s) to the stack "
                         f"that {less} keeps in registers{note}"),
                lever=("too many simultaneously-live values (6 max across a call, "
                       "7 otherwise).  The lowest-savings value spills first; reduce "
                       "the number of values live at once, or raise the wanted "
                       "value's use count (1 loop use = savings 10)."),
            )

    # (5) LOOPS — invariant hoisted on one side, reloaded each iteration on the
    # other (aliasing-gated: a call / pointer store in the loop forces reloads).
    if _loop_region(ps_insns) is not None and _loop_region(rc_insns) is not None:
        if abs(ps_loop - rc_loop) >= 1:
            more, less = ("RC", "PS") if rc_loop > ps_loop else ("PS", "RC")
            return RegallocHint(
                layer=5,
                summary=(f"loop hoist/reload: {more} reloads a global inside the "
                         f"loop that {less} hoisted (loaded once before it)"),
                lever=("an invariant global is reloaded when a call or a pointer "
                       "store in the loop could alias it.  Match the loop's "
                       "call / aliasing-store structure to PS.  NEVER add `-oa`."),
            )

    # (1)/(2)/(3) — prologue push-set divergence.  (The 'Prologue hint' line
    # already gives the per-register detail; here we tag the model layer.)
    if ps_push != rc_push:
        ps_set, rc_set = set(ps_push), set(rc_push)
        if len(ps_push) == len(rc_push) and len(ps_set ^ rc_set) == 2:
            a = (ps_set - rc_set).pop()
            b = (rc_set - ps_set).pop()
            # Only `b` is callee-save-HELD in RC (RC pushed b, not a; a is
            # scratch here), so the reliable fact is the savings of the value
            # RC put in b -- and how many enregistered values SHARE that
            # savings (an equal-savings cohort >=2 is the genuine layer-3 tie
            # that the use/decl-order lever resolves).
            sb = rcsav.get(b, [None])[0]
            confirm = ""
            if sb is not None:
                cohort = sum(1 for x in (rc_alloc or [])
                             if x.get("reg_name") and x.get("savings") == sb)
                if cohort >= 2:
                    confirm = (f"  [trace: RC's {b}-value savings={sb}, shared by "
                               f"{cohort} enregistered values -> genuine "
                               f"equal-savings tie; use/decl-order lever]")
                else:
                    confirm = (f"  [trace: RC's {b}-value savings={sb} (unique) -> "
                               f"the {a}/{b} choice is RegLists priority order, "
                               f"not a savings tie]")
            return RegallocHint(
                layer=3,
                summary=f"callee-save swap (PS {a} / RC {b}) — equal savings{confirm}",
                lever=("LAST-use order (regalloc-last-use.py): the value with "
                       "the EARLIER last use gets the higher-priority reg "
                       "(DoubleRegs EAX,EDX,EBX,ECX,...).  To move a value to "
                       "the higher reg, make its last use earlier (move the "
                       "rival's trailing use later); within `A op B` the LATER "
                       "operand B takes the higher reg.  Worked: "
                       "change_citizen_targs."),
            )
        # asymmetric count: extra callee-save on one side
        more, less = ("RC", "PS") if len(rc_push) > len(ps_push) else ("PS", "RC")
        extra_set = (set(ps_push) - set(rc_push)) if more == "PS" else (set(rc_push) - set(ps_push))
        more_insns = ps_insns if more == "PS" else rc_insns
        # Ground truth: when RC is the side with the extra callee-save, the
        # -trace image tells us the savings of the value that landed there.
        # A callee-save only pays off above savings 2 (~3 uses); naming the
        # savings tells the agent exactly how far to cut its use count.
        xnote = ""
        if more == "RC" and extra_set:
            picks = [(r, rcsav[r][0]) for r in sorted(extra_set) if r in rcsav]
            if picks:
                xnote = ("  [trace: RC "
                         + ", ".join(f"{r} holds savings {s}" for r, s in picks)
                         + " -- a callee-save needs savings>2 (~3 uses); cut this "
                         "value's uses below that to drop the push]")
        # Sub-case: the extra register holds a materialised constant that is
        # stored to memory.  Per Rule 110 the const-store FORM is deterministic
        # (0 always register; nonzero register iff >=2 refs) -- so this is NOT a
        # store-form lever.  The extra callee-save means the const-temp landed
        # in a callee-save register HERE: a regalloc (which-register) divergence.
        if any(_reg_holds_const_store(more_insns, r) for r in extra_set):
            less_insns = rc_insns if more == "PS" else ps_insns
            consts: set = set()
            for r in extra_set:
                consts |= _reg_const_values(more_insns, r)
            less_caches = any(_reg_const_values(less_insns, r) & consts
                              for r in _ALL_GP)
            less_imm = bool(consts) and _stores_const_immediate(less_insns, consts)
            xr = "/".join(sorted(extra_set))
            if less_imm and not less_caches:
                # PURGE the old "form already matches; WHICH register" claim:
                # the OTHER side does NOT cache -- it stores the immediate and
                # leaves this register UNUSED.  It is a cache-vs-immediate
                # (loop-invariant hoist) divergence, not a which-register tie.
                cs = "{" + ",".join(sorted(consts)) + "}"
                return RegallocHint(
                    layer=3,
                    summary=(f"{more} CACHES const {cs} in an extra callee-save "
                             f"({xr}); {less} stores it INLINE and leaves {xr} "
                             f"UNUSED (NOT a which-register tie)"),
                    lever=(f"const-cache vs immediate (Rule 110 / loop-invariant "
                           f"hoist), NOT a which-register tie: {more} enregistered "
                           f"the constant (>=2 refs or a loop store) in a "
                           f"callee-save -- that IS the extra push -- while {less} "
                           f"emits `mov [m], imm` each time and uses {xr} 0x.  "
                           f"{less} leaves {xr} FREE too, so availability is NOT "
                           f"the discriminator -- it is a codegen/hoist decision on "
                           f"~identical IL.  No isolated source lever is confirmed; "
                           f"the direction is to match {less}'s live-set / IL "
                           f"(c2 win-census flags any extra local as a candidate), "
                           f"but it may be sub-source.  `c2 reg-delta <fn>` shows "
                           f"the full PS-vs-RC register census + the held "
                           f"constant."),
                )
            # else: BOTH sides cache the const (in different registers) -- a
            # genuine which-register tie.
            return RegallocHint(
                layer=3,
                summary=f"{more}'s extra {xr} holds a "
                        f"const-store temp placed in a callee-save (Rule 110)",
                lever=("Rule 110: the const-store FORM is deterministic -- in "
                       "global/indexed addressing (form A) a 0-store is always "
                       "register (`xor reg,reg; mov [m],reg`) and a nonzero is "
                       "register-cached iff referenced >=2x.  Both sides cache it "
                       "(verified: the other side holds the same constant in a "
                       "register) -- the diff is WHICH register the const-temp got. "
                       "Plain regalloc -- match PS's allocation (Rule 108 "
                       "inline-vs-cache, use-order, savings), do NOT chase the "
                       "store.  `c2 reg-delta <fn>` shows both sides' census.  (If "
                       "instead PS folds a global address while recomp caches a "
                       "pointer, that is Rule 73 -- inline the pointer.)"),
            )
        if _has_call(ps_insns) or _has_call(rc_insns):
            return RegallocHint(
                layer=1,
                summary=f"{more} enregisters one more value across a call than {less}",
                lever=("EAX-boundary or savings: check whether the extra value's "
                       "live range crosses a call/idiv on this side (move its use "
                       "before the call to free it to EAX), or has fewer uses on "
                       "the other (a callee-save needs savings > 2 ≈ 3 uses, or 1 "
                       "loop use ×10).  See the Prologue hint for the register." + xnote),
            )
        return RegallocHint(
            layer=2,
            summary=f"{more} enregisters one more value than {less}",
            lever=("savings: a callee-save register needs savings > 2 (≈3 "
                   "straight-line uses, or 1 loop use ×10) to be worth its "
                   "push/pop.  See the Prologue hint for the register." + xnote),
        )

    # Prologue matches: a scaled-index load fused into the result register
    # (Rule 109) is a layer-4 single-use COALESCE, not a layer-3 last-use
    # swap, and it has a concrete source lever (split the index with a dead
    # store).  Surface that instead of the generic last-use message.
    if "Rule 109" in rule_hist:
        return RegallocHint(
            layer=4,
            summary="scaled-index load fused into the result register (Rule 109)",
            lever=("layer 4 (CountRegMoves coalesce): a single-use `arr[i].field` "
                   "index merges into the result register; PS keeps it in a "
                   "scratch reg because its source gave the index a SECOND use. "
                   "Lever: a dead store through the same index "
                   "(`arr[i].field = arr[i].field;`) splits the live range and "
                   "is DCE'd -> byte-exact.  Worked: barbarians_drop_by_city. "
                   "See Rule 109."),
        )

    # Prologue matches, no spill/loop divergence.  A caller-saved register
    # identity swap (Reg swap / Byte-reg swap / Rule 28) is still layer 3.
    if rule_hist.keys() & _REGALLOC_RULES:
        return RegallocHint(
            layer=3,
            summary="register-identity swap (caller-saved; no prologue change)",
            lever=("layer 3 equal-savings tie-break (ConfBefore name-pointer). "
                   "Two source levers: (a) Rule 28a -- reorder which of the two "
                   "tied values is USED FIRST (commute a deciding expression / "
                   "move a statement; worked: change_citizen_targs); or, when "
                   "the use is pinned by semantics, (b) Rule 115 -- swap the "
                   "two tied locals' DECLARATION order (worked: show_help_page; "
                   "direction non-monotonic, verify both).  Genuine residue "
                   "only when both values are compiler temps / CSE-hoisted "
                   "globals with no named-local handle.  For ground truth + "
                   "the exact competing pair, run `c2 regtrace <fn> --explain`; "
                   "screen order/credit levers OFFLINE with `c2 savings <fn> "
                   "--flip VAR=REG [--depth 2]` (grounded edits through the "
                   "full sort+pick replay, side effects listed)."),
        )

    # Register layout matches.  Any remaining diff is NOT a regalloc issue.
    if has_body_diff:
        outside = [d for r, d in _RULE_DESC.items() if r in rule_hist]
        named = ("; likely " + ", ".join(outside)) if outside else ""
        return RegallocHint(
            layer=-1,
            summary="register layout matches PS",
            lever=("the NAMED-value layout matches PS; the diff is in a layer "
                   "BELOW it — push-scratch rover picks (call-arg/const stores), "
                   "spill-SLOT order (same-size co-spilled temps -> creation/"
                   "Names order; try a local at function vs block scope, Rule "
                   "107), or instruction selection / strength reduction / "
                   f"tail-merge / branch encoding{named}."),
        )
    return None


def render(hint: RegallocHint) -> str:
    if hint.layer == -1:
        return f"{hint.summary} \u2014 {hint.lever}"
    return f"layer {hint.layer} {hint.summary}. {hint.lever}"
