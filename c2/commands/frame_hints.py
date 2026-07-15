"""Frame-size root-cause diagnostic.

Corpus analysis of the 335 diffing functions established that **45 % of
them have their first divergent instruction in the prologue** (the
callee-save push set or the ``sub esp, N`` frame allocation), and that
those prologue-seeded cascades account for **63 % of all residual diff
bytes** in the project.  The single most actionable sub-signal is the
``sub esp, N`` delta: it is a scalar reflecting the FINAL stack-frame
layout, so a PS-vs-RC difference is a reliable measure of how many stack
slots (named locals + register spills + outgoing stack-arg space) the two
builds disagree on -- and, unlike per-row ``[esp+N]`` offsets, it does not
renumber on a cascade.

This module turns the bare ``Frame:`` line (Rule 107 companion) into a
root-cause diagnostic:

  * reports the delta in whole 4-byte **slots**, not just bytes;
  * states whether the frame divergence is the **root** of the cascade
    (the first divergence is in the prologue) vs a downstream symptom;
  * gives a **sign-based fix direction**:
      - RC frame BIGGER  -> we allocate more slots than PS -> we likely
        named/spilled locals PS held in registers.  Inline the
        superfluous named locals (generalised Rule 116); this is the
        class the narrow ``reload_hints`` gate misses.
      - PS frame BIGGER  -> PS spilled more than we do -> an ordinary
        regalloc eviction divergence (Rule 111) or PS named temporaries
        we inlined.  Less reliably source-fixable.

Empirically (frame-rooted set, n=53): RC-bigger 15, PS-bigger 25 -- and
the existing ``reload_hint`` (Rule 116) fired on NONE of them, which is
exactly the gap this diagnostic fills.

The detector takes the two already-decoded instruction streams (``InsnT``
tuples: ``(off, size, raw_bytes, asm_text)``) plus the diff ``rows`` so it
can decide root-vs-symptom.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Annotated, Optional

import typer

# Registers that may appear in the prologue push run.  Mirrors
# decomp_verify._CALLEE_SAVE_REGS exactly: under __watcall the true
# callee-saves are ebx/esi/edi/ebp, but PS routinely pushes the
# caller-saved ecx/edx/eax as preserved values or stack slots (Rule 24a),
# and those pushes precede the `sub esp, N` just the same.
_CALLEE_SAVE = {"ebx", "ecx", "edx", "esi", "edi", "ebp", "eax"}

# Slot granularity: Watcom 10.0a allocates stack locals in 4-byte units on
# the 32-bit flat target.
_SLOT = 4


@dataclass
class FrameHint:
    ps_frame: int            # PS `sub esp, N` (bytes)
    rc_frame: int            # recomp `sub esp, N` (bytes)
    delta: int               # rc_frame - ps_frame (bytes; +ve = RC bigger)
    slot_delta: int          # delta // 4 (signed; whole slots)
    is_root: bool            # True when the prologue is the first divergence
    direction: str           # "rc_bigger" | "ps_bigger"
    ps_pushes: int           # # prologue register pushes, PS side
    rc_pushes: int           # # prologue register pushes, recomp side

    @property
    def worthprolog_swap(self) -> bool:
        """True for a distinct RC-bigger sub-case: RC dropped a callee-save
        register and spilled the value to a stack slot instead (a
        ``WorthProlog`` tie), so RC has FEWER prologue pushes but a BIGGER
        frame (put_x1_area: PS+edi, up_slider_var: PS+ebp).  A minority of
        the RC-bigger set (~4/28) but worth flagging because it must be
        routed AWAY from the Rule 116 'inline a local' advice -- there is no
        removable local; it is a Rule 89 / WorthProlog savings tie.  The
        remaining RC-bigger cases (equal push count) are the Rule 116 /
        pressure-spill class.
        """
        return (self.direction == "rc_bigger"
                and self.rc_pushes < self.ps_pushes
                and self.slot_delta >= 1)

    @property
    def over_enregister(self) -> bool:
        """RC has MORE prologue pushes AND a bigger frame: RC enregisters and
        spills more values overall than PS, i.e. the function's live-value
        count / control-flow shape differs from PS (extra `else`/`continue`
        paths, a ternary folded to `sete`, a `switch` compiled as a jump
        table where PS used if/else-if).  The frame delta is a *downstream
        symptom* of a structural divergence -- fix the structure (Rule
        82/26/95), not the frame.  Example: figure_update (PS 4 / RC 6).
        """
        return (self.direction == "rc_bigger"
                and self.rc_pushes > self.ps_pushes)

    @property
    def fix(self) -> str:
        if self.direction == "rc_bigger":
            if self.worthprolog_swap:
                return (
                    f"RC dropped a callee-save register ({self.ps_pushes - self.rc_pushes} "
                    "fewer prologue push(es)) and spilled that long-lived "
                    "value to a stack slot instead -- a WorthProlog tie, NOT a "
                    "removable local.  See the Prologue hint / Rule 89: raise "
                    "the value's use-count savings (1 loop use = 10) or reshape "
                    "the range so the enregistered choice wins; often a hard tie"
                )
            if self.over_enregister:
                return (
                    f"RC has MORE prologue pushes ({self.rc_pushes} vs PS "
                    f"{self.ps_pushes}) AND a bigger frame -- RC enregisters more "
                    "values overall, so the live-value count / control-flow shape "
                    "differs.  The frame delta is a downstream SYMPTOM: fix the "
                    "structure (ternary->sete = Rule 82/26, switch->jumptable = "
                    "Rule 95, extra else/continue paths), NOT the frame"
                )
            return (
                "we allocate more stack slots than PS at EQUAL push count "
                "(cross-check Regalloc: 'RC spills ~N').  Likely a superfluous "
                "named local PS held in a register -- inline it (Rule 116); or "
                "a loop-invariant PS reloaded / a genuine pressure spill "
                "(Spill-class/Rule 111)"
            )
        return (
            "PS spilled more than we do -- an ordinary regalloc eviction "
            "(Rule 111) or named temps we inlined; less reliably "
            "source-fixable"
        )


def _is_push_imm(asm: str) -> bool:
    parts = asm.split(None, 1)
    if not parts or parts[0] != "push":
        return False
    op = parts[1] if len(parts) > 1 else ""
    return bool(op) and (op[0].isdigit() or op.startswith("0x")
                         or op.startswith("-"))


def detect_frame_alloc(insns: list) -> Optional[int]:
    """Return the prologue stack-frame allocation in bytes (the ``sub esp,
    N`` after the callee-save pushes), 0 if there is none, or None if the
    prologue can't be parsed.  Kept in sync with
    ``decomp_verify._detect_frame_alloc``.
    """
    if not insns:
        return None
    start = 0
    if (len(insns) >= 2
            and _is_push_imm(insns[0][3])
            and insns[1][3].startswith("call ")):
        start = 2
    j = start
    while j < len(insns):
        parts = insns[j][3].split(None, 1)
        if not parts or parts[0] != "push":
            break
        op = parts[1] if len(parts) > 1 else ""
        if op in _CALLEE_SAVE:
            j += 1
        else:
            break
    if j >= len(insns):
        return None
    parts = insns[j][3].split(None, 1)
    if not parts:
        return None
    ops = parts[1] if len(parts) > 1 else ""
    fields = [o.strip() for o in ops.split(",")]
    if parts[0] not in ("sub", "add") or len(fields) != 2 or fields[0] != "esp":
        return 0
    try:
        imm = int(fields[1], 0)
    except ValueError:
        return None
    return imm if parts[0] == "sub" else -imm


def count_prologue_pushes(insns: list) -> int:
    """Number of bare-register pushes in the prologue push run (after an
    optional `push N; call __CHK` pair).  Reflects how many values the
    allocator chose to preserve via the callee-save mechanism.
    """
    if not insns:
        return 0
    i = 0
    if (len(insns) >= 2
            and _is_push_imm(insns[0][3])
            and insns[1][3].startswith("call ")):
        i = 2
    n = 0
    while i < len(insns):
        parts = insns[i][3].split(None, 1)
        if not parts or parts[0] != "push":
            break
        op = parts[1] if len(parts) > 1 else ""
        if op in _CALLEE_SAVE:
            n += 1
            i += 1
        else:
            break
    return n


def _first_divergence_off(rows: list[dict]) -> Optional[int]:
    """Function-relative byte offset of the first non-equal diff row."""
    for r in rows:
        if r.get("kind") != "equal":
            return r.get("off")
    return None


def detect(orig_insns: list, recomp_insns: list,
           rows: Optional[list[dict]] = None,
           prologue_window: int = 24) -> Optional[FrameHint]:
    """Return a ``FrameHint`` when PS and recomp allocate different prologue
    frame sizes, else None.

    ``rows`` (the aligned diff stream) is optional; when supplied it sets
    ``is_root`` = True iff the first divergence falls within
    ``prologue_window`` bytes of the entry (i.e. the frame mismatch is the
    seed of the cascade rather than a downstream renumber).
    """
    ps_frame = detect_frame_alloc(orig_insns)
    rc_frame = detect_frame_alloc(recomp_insns)
    if ps_frame is None or rc_frame is None or ps_frame == rc_frame:
        return None
    delta = rc_frame - ps_frame
    is_root = False
    if rows is not None:
        off = _first_divergence_off(rows)
        is_root = off is not None and off <= prologue_window
    return FrameHint(
        ps_frame=ps_frame,
        rc_frame=rc_frame,
        delta=delta,
        slot_delta=delta // _SLOT if delta % _SLOT == 0 else delta // _SLOT,
        is_root=is_root,
        direction="rc_bigger" if delta > 0 else "ps_bigger",
        ps_pushes=count_prologue_pushes(orig_insns),
        rc_pushes=count_prologue_pushes(recomp_insns),
    )


def render_line(h: FrameHint) -> str:
    """One Rich-markup line for ``decomp-verify -v``."""
    sign = "+" if h.delta > 0 else ""
    slots = abs(h.slot_delta)
    slot_word = "slot" if slots == 1 else "slots"
    root = ("[bold]ROOT of cascade[/] -- "
            if h.is_root else "(downstream of an earlier diff) ")
    if h.worthprolog_swap:
        cls = "[magenta]WorthProlog spill-vs-callee-save[/] -- "
    elif h.over_enregister:
        cls = "[magenta]structural (RC over-enregisters)[/] -- "
    else:
        cls = ""
    return (
        f"  [yellow]Frame[/]: PS sub esp,{h.ps_frame:#x}  "
        f"RC sub esp,{h.rc_frame:#x}  ({sign}{h.delta} b = "
        f"{sign}{h.slot_delta} {slot_word}; pushes PS {h.ps_pushes}/RC "
        f"{h.rc_pushes})  {root}{cls}{h.fix}"
    )


def to_json(h: Optional[FrameHint]) -> Optional[dict]:
    if h is None:
        return None
    return {
        "ps_frame": h.ps_frame,
        "rc_frame": h.rc_frame,
        "delta": h.delta,
        "slot_delta": h.slot_delta,
        "is_root": h.is_root,
        "direction": h.direction,
        "ps_pushes": h.ps_pushes,
        "rc_pushes": h.rc_pushes,
        "worthprolog_swap": h.worthprolog_swap,
        "over_enregister": h.over_enregister,
        "fix": h.fix,
    }


# ── Frame-level levers (2026-06-10): foreign-frame blocks + retval funnel ──
#
# Two cheap, fully mechanical signals discovered during the
# start_sequences / sf14_opertunist_fire root-cause sessions, both of
# which previously required hand-reading PS bytes.
#
# FOREIGN-FRAME BLOCKS (Rule 125 signal).  Under __watcall every
# register except EAX is callee-save: a self-contained function never
# writes ESI/EDI/EBP without pushing them.  A write to an UNSAVED one
# of those inside a PS symbol range is proof that the surrounding bytes
# execute under ANOTHER function's frame (queue-resident code motion:
# ComTail/Untangle/CallRet hosting -- Rule 125 / Rule 42).  Example: PS
# sf14_opertunist_fire saves only ebx/ecx/edx yet contains
# `xor esi,esi` (+0x301) and `mov edi,[...]` (+0x6e3).  When this
# fires, function-local source work CANNOT reach byte parity -- the
# lever is block-ownership mapping, not source permutation.  We
# restrict to ESI/EDI/EBP because EDX/EBX/ECX may legally carry
# __watcall parameters.
#
# RETVAL FUNNEL (W107 join-read exile).  An RC-side tail
# `mov edx,<csave>; mov eax,<csave>; pop ...; ret` is the far-pointer
# return pair homed from callee-saves at a single exit.  Mechanism
# (grounded in 10.0a NeighboursUse + OW v1 dataflo.c): a value-
# returning function whose success path falls off the end gets an
# uninitialized-but-live join read of the return temp -> live across
# every call -> EAX/EDX masked -> exiled + homing MOVs.  PS shows
# per-site `xor edx,edx; mov eax,N` with NO homing.  Lever is the
# SOURCE SHAPE feeding the IL (Rule 85), never register permutation.

_PUSH_REG = {"ebx", "ecx", "edx", "esi", "edi", "ebp"}
_STRICT_CSAVE = {"esi", "edi", "ebp"}
_WRITES_OP0 = {
    "mov", "lea", "movsx", "movzx", "xor", "add", "sub", "inc", "dec",
    "imul", "or", "and", "shl", "sar", "shr", "neg", "not", "pop",
    "xchg",
}


def _fh_mnem(i) -> str:
    return i[3].split(None, 1)[0]


def _fh_ops(i) -> list:
    parts = i[3].split(None, 1)
    if len(parts) < 2:
        return []
    return [t.strip() for t in parts[1].split(",")]


def prologue_pushes(insns: list) -> list:
    """The leading `push <reg>` run (wcc386 saves everything up front)."""
    out = []
    for ins in insns:
        if _fh_mnem(ins) != "push":
            break
        ops = _fh_ops(ins)
        if len(ops) != 1 or ops[0] not in _PUSH_REG:
            break
        out.append(ops[0])
    return out


@dataclass
class ForeignFrameHint:
    func: str
    saved: list
    writes: list                       # (offset, reg, asm-text)
    custom: bool = False               # whole function is non-watcall


def detect_foreign_frame(func: str, insns: list) -> Optional[ForeignFrameHint]:
    """Writes to UNSAVED strict callee-saves inside the PS range.

    Two verdicts (corpus census, docs/frame-lever-census.md):
    ``custom=False`` -- a wcc-style head with LATE foreign writes =
    hosted blocks (Rule 125, 4 corpus cases); ``custom=True`` -- unsaved
    writes from offset ~0 with an empty push set = the whole function
    uses a non-watcall convention (sprite blitters / Smacker / AIL asm /
    CRT internals, 249 corpus cases) and is NOT a C reconstruction
    target in the normal sense."""
    if not insns:
        return None
    saved = prologue_pushes(insns)
    unsaved = _STRICT_CSAVE - set(saved)
    if not unsaved:
        return None
    writes = []
    for ins in insns[len(saved):]:
        mn = _fh_mnem(ins)
        if mn not in _WRITES_OP0:
            continue
        ops = _fh_ops(ins)
        if not ops:
            continue
        if ops[0] in unsaved:
            writes.append((ins[0], ops[0], ins[3]))
        elif mn == "xchg" and len(ops) == 2 and ops[1] in unsaved:
            writes.append((ins[0], ops[1], ins[3]))
    if not writes:
        return None
    custom = (not saved) and writes[0][0] < 0x20
    return ForeignFrameHint(func, saved, writes, custom)


def render_foreign_frame(h: ForeignFrameHint, *, max_sites: int = 4) -> list:
    sites = ", ".join(f"+{o:#x} `{txt}`" for o, _r, txt in h.writes[:max_sites])
    more = f" (+{len(h.writes) - max_sites} more)" if len(h.writes) > max_sites else ""
    regs = ",".join(sorted({r for _o, r, _t in h.writes}))
    if h.custom:
        return [
            f"Custom-convention function: PS pushes nothing yet writes "
            f"{regs} from +{h.writes[0][0]:#x} -- hand-written/generated "
            f"asm or pragma aux (blitter/Smacker/AIL/CRT class), NOT a "
            f"normal __watcall C function.",
            "  -> do not reconstruct as plain C; match the original asm "
            "or pragma instead.  See docs/frame-lever-census.md.",
        ]
    return [
        f"Foreign-frame blocks (Rule 125): PS saves only "
        f"[{','.join(h.saved) or 'nothing'}] but its range WRITES {regs} at "
        f"{sites}{more}.",
        "  -> those bytes execute under ANOTHER function's frame (queue "
        "code motion / hosted blocks).  Function-local source work cannot "
        "reach parity; map block ownership first (which jump sources feed "
        "those offsets) and fix the owning function / queue order.  Do NOT "
        "chase register swaps or prologue pragmas here.",
    ]


@dataclass
class RetvalFunnelHint:
    func: str
    offset: int
    seg_src: str
    off_src: str


def detect_retval_funnel(func: str, rc_insns: list) -> Optional[RetvalFunnelHint]:
    """RC-side far-ptr pair homed from callee-saves right before the
    epilogue: `mov edx,R1; mov eax,R2` followed only by pops/ret/jmp."""
    n = len(rc_insns)
    for i in range(n - 1):
        a, b = rc_insns[i], rc_insns[i + 1]
        if _fh_mnem(a) != "mov" or _fh_mnem(b) != "mov":
            continue
        oa, ob = _fh_ops(a), _fh_ops(b)
        if len(oa) != 2 or len(ob) != 2:
            continue
        if {oa[0], ob[0]} != {"edx", "eax"}:
            continue
        if oa[1] not in _PUSH_REG or ob[1] not in _PUSH_REG:
            continue
        tail = rc_insns[i + 2:]
        if not tail or not all(_fh_mnem(t) in {"pop", "ret", "jmp", "leave"}
                               for t in tail):
            continue
        seg_src = oa[1] if oa[0] == "edx" else ob[1]
        off_src = oa[1] if oa[0] == "eax" else ob[1]
        return RetvalFunnelHint(func, a[0], seg_src, off_src)
    return None


def render_retval_funnel(h: RetvalFunnelHint) -> list:
    return [
        f"Retval funnel (W107 join-read exile): RC homes the far-ptr "
        f"return pair from callee-saves at +{h.offset:#x} "
        f"(edx<-{h.seg_src}, eax<-{h.off_src}).",
        "  -> the fall-off success path never assigns the return temp, "
        "so its uninitialized-but-live join read keeps the pair live "
        "across every call -> EAX/EDX masked -> exiled to callee-saves. "
        "PS has per-site `xor edx,edx; mov eax,N` and NO homing (no join "
        "read in its IL).  The lever is the SOURCE SHAPE feeding the IL, "
        "not registers -- see Rule 85 (watcom-codegen-patterns.md) and "
        "the pcsound.c start_sequences note for the open question.",
    ]


# ── c2.c burn-down detectors (2026-06-13): Rules 136/137/138 ────────────
#
# Three whole-function shapes proven on the c2.c sweep (new_province /
# load_map_graphics / load_battle_graphics / main, all byte-exact after
# applying the rendered recipe).  Each detector is STATIC (PS+RC insn
# lists only); corpus-grounded fire counts live in the rules registry.


def _jmp_target(ins) -> Optional[int]:
    """Absolute (function-local) target of a `jmp 0x...` insn, else None."""
    asm = ins[3]
    if not asm.startswith("jmp 0x"):
        return None
    try:
        return int(asm.split()[1], 16)
    except ValueError:
        return None


@dataclass
class MemRetvalFunnelHint:
    func: str
    store_off: int
    load_off: int
    imm: str


def detect_memory_retval_funnel(func: str, ps_insns: list,
                                rc_insns: list) -> Optional[MemRetvalFunnelHint]:
    """Rule 136: PS exiles the return temp to the frame slot.

    PS shows `mov dword ptr [esp], IMM` and a later epilogue funnel
    `mov eax, dword ptr [esp]` (followed only by add esp/pops/ret),
    while RC keeps the value in a register (no funnel load).  The slot
    usually rides on a `sub esp,4` that RC lacks."""
    store = None
    load_i = None
    for i, ins in enumerate(ps_insns):
        asm = ins[3]
        if asm.startswith("mov dword ptr [esp],"):
            val = asm.split(",", 1)[1].strip()
            if not val.startswith(("e", "[")):       # immediate only
                store = ins
        elif asm == "mov eax, dword ptr [esp]" and store is not None:
            load_i = i
    if store is None or load_i is None:
        return None
    if ps_insns[load_i][0] <= store[0]:
        return None
    tail = ps_insns[load_i + 1:]
    if not tail or not all(
            _fh_mnem(t) in {"pop", "ret", "jmp", "add", "leave"} for t in tail):
        return None
    for ins in rc_insns:
        if ins[3] == "mov eax, dword ptr [esp]":
            return None                              # RC funnels too
    return MemRetvalFunnelHint(func, store[0], ps_insns[load_i][0],
                               store[3].split(",", 1)[1].strip())


def render_memory_retval_funnel(h: MemRetvalFunnelHint) -> list:
    return [
        f"Rule 136 (memory retval funnel, W107 exile): PS stores "
        f"{h.imm} to the frame slot at +{h.store_off:#x} and loads the "
        f"return value back at +{h.load_off:#x}; RC returns through a "
        f"register.",
        "  -> the return temp is exiled to [esp] by an uninitialized-but-"
        "live JOIN read: the noreturn-looking fail blocks (exit()/abort "
        "paths) fall into ONE shared `return ret;` at the very end.  "
        "Source recipe (load_map_graphics, exact): `ret = " + h.imm +
        "; goto done;` after the main body, fail blocks AFTER it at "
        "function bottom, and a single `done: return ret;` last line that "
        "the fail paths fall into.  TWO separate `return ret;` statements "
        "kill the exile (separate exits, no join) -- that is the usual RC "
        "bug.  The `sub esp,4` delta rides along.",
    ]


@dataclass
class MergeDirectionHint:
    func: str
    ps_target: int
    ps_jumpers: int
    rc_target: int
    rc_jumpers: int


def detect_merge_direction(func: str, ps_insns: list,
                           rc_insns: list) -> Optional[MergeDirectionHint]:
    """Rule 137: shared-suffix merge DIRECTION mismatch.

    PS has >=2 unconditional jmps to one BACKWARD target (kept instance
    = first arm) while RC's multi-jumper target is FORWARD (kept
    instance = last arm), or vice versa.  Symmetric loop back-edges
    (continue statements) appear on BOTH sides and cancel out."""
    def multi_targets(insns, backward: bool):
        from collections import Counter
        c: Counter = Counter()
        for ins in insns:
            t = _jmp_target(ins)
            if t is None:
                continue
            if (t < ins[0]) == backward:
                c[t] += 1
        return {t: n for t, n in c.items() if n >= 2}

    ps_back, rc_back = multi_targets(ps_insns, True), multi_targets(rc_insns, True)
    ps_fwd, rc_fwd = multi_targets(ps_insns, False), multi_targets(rc_insns, False)
    # PS merges backward where RC merges forward.
    if len(ps_back) > len(rc_back) and len(rc_fwd) > len(ps_fwd):
        pt, pn = max(ps_back.items(), key=lambda kv: kv[1])
        rt, rn = max(rc_fwd.items(), key=lambda kv: kv[1])
        return MergeDirectionHint(func, pt, pn, rt, rn)
    return None


def render_merge_direction(h: MergeDirectionHint) -> list:
    return [
        f"Rule 137 (suffix-merge direction): {h.ps_jumpers} PS jmps "
        f"converge BACKWARD on +{h.ps_target:#x} (kept instance = FIRST "
        f"arm) while {h.rc_jumpers} RC jmps converge FORWARD on "
        f"+{h.rc_target:#x} (kept instance = LAST arm).",
        "  -> the \"shared\" block is not a source label/goto: write "
        "EVERY arm self-contained (its own check/call statements) and let "
        "Watcom tail-merge the identical suffixes -- the FIRST arm's copy "
        "then stays inline and later arms back-jump into it "
        "(load_map_graphics: per-arm `X = malloc(size); if (X == NULL) "
        "goto alloc_fail; if (!readfile(fname, X, size, 0)) goto "
        "file_fail;`, exact).  An arm whose check FALLS THROUGH (last "
        "else-if) keeps its copy inline.  The rover renders each arm's "
        "global read as the same byte pattern, which is what makes the "
        "suffixes identical.  Sibling: Rule 135 (explicit goto idiom -- "
        "use that when PS's shared block includes the call+epilogue).",
    ]


@dataclass
class ParamScratchHint:
    func: str
    writes: list           # [(reg, off), ...]
    ps_saves: list
    rc_saves: list


_WATCALL_ORDER = ["eax", "edx", "ebx", "ecx"]


def detect_param_reg_scratch(func: str, ps_insns: list,
                             rc_insns: list) -> Optional[ParamScratchHint]:
    """Rule 138: PS treats EDX/EBX/ECX as scratch (writes without saving)
    while RC saves it -> the original function declares (unused)
    parameters; incoming __watcall arg regs are caller-scratch."""
    ps_saves = set(prologue_pushes(ps_insns))
    rc_saves = set(prologue_pushes(rc_insns))
    extra = [r for r in ("edx", "ebx", "ecx")
             if r in rc_saves and r not in ps_saves]
    if not extra:
        return None
    writes = []
    for r in extra:
        for ins in ps_insns[len(ps_saves):]:
            m = _fh_mnem(ins)
            ops = _fh_ops(ins)
            if ops and ops[0] == r and m in _WRITES_OP0:
                writes.append((r, ins[0]))
                break
    if not writes:
        return None
    return ParamScratchHint(func, writes,
                            sorted(ps_saves), sorted(rc_saves))


def render_param_scratch(h: ParamScratchHint) -> list:
    regs = ", ".join(f"{r} (written at +{o:#x})" for r, o in h.writes)
    # How many params make the last written reg scratch?
    deepest = max(_WATCALL_ORDER.index(r) for r, _ in h.writes) + 1
    return [
        f"Rule 138 (param regs are scratch): PS saves "
        f"[{','.join(h.ps_saves)}] but freely writes {regs}; RC saves it.",
        f"  -> the original signature very likely declares >= {deepest} "
        f"parameters (even if unused): incoming __watcall arg registers "
        f"need no save.  Worked example: `void main(int argc, char "
        f"*argv[])` killed main's extra `push edx` (c2.c, exact).  Check "
        f"callers/runtime for the natural arity before inventing one.",
    ]


# ── Session 2026-06-13 (initreg_game_loop close-out): Rules 148/149 ─────
#
# Two whole-function shapes proven on the gloops.c initreg_game_loop
# 228b -> 17b close-out, both Mac-confirmed and source-truthful.


@dataclass
class EpilogueFunnelHint:
    func: str
    ps_jmps: list          # [(offset, target), ...]
    rc_rets: list          # [(offset, pop_count), ...]
    epilogue_size: int     # pop_count*1 + 1 for ret


def _is_pop_or_ret(ins):
    return _fh_mnem(ins) in ("pop", "ret")


def _epilogue_blocks(insns: list) -> list:
    """Find sequences of (pop reg)+ followed by ret; return
    [(start_offset, pop_count), ...].  A bare ret with no pops counts
    too -- needed for frameless funnels."""
    out = []
    i, n = 0, len(insns)
    while i < n:
        if _fh_mnem(insns[i]) == "pop":
            start = insns[i][0]
            pops = 0
            while i < n and _fh_mnem(insns[i]) == "pop":
                pops += 1
                i += 1
            if i < n and _fh_mnem(insns[i]) == "ret":
                out.append((start, pops))
                i += 1
                continue
        elif _fh_mnem(insns[i]) == "ret":
            out.append((insns[i][0], 0))
            i += 1
            continue
        i += 1
    return out


def detect_epilogue_funnel(func: str, ps_insns: list,
                            rc_insns: list) -> Optional[EpilogueFunnelHint]:
    """Rule 148: PS funnels early returns via `jmp <end>`; RC inlines
    multi-pop epilogues per early-exit site.

    Signal: RC has >= 2 epilogue blocks (pop+...+ret) at non-final
    offsets AND PS has corresponding jcc/jmp instructions targeting
    the function-end region (last 16 bytes).  When CloneCode declines
    to inline epilogues (callee-save count s.t. epilogue > 5b), PS
    keeps each early exit as a 1-2 byte jmp; RC inlines a full
    epilogue block (5+ bytes per site) -- the goto-end source recipe
    closes this.  Frameless functions only (sub esp,N would hide
    behind the framed mid-epilogue class, Rule 135)."""
    if not ps_insns or not rc_insns:
        return None
    # Frameless: no `sub esp, N` in the prologue.  CloneCode's threshold
    # only matters when the function is frameless (otherwise the framed
    # mid-epilogue class dominates -- Rule 135).
    for ins in ps_insns[:8]:
        if _fh_mnem(ins) == "sub" and "esp" in ins[3]:
            return None
    rc_blocks = _epilogue_blocks(rc_insns)
    if len(rc_blocks) < 2:
        return None
    # Find PS's final epilogue (last block ends at function end).
    ps_blocks = _epilogue_blocks(ps_insns)
    if not ps_blocks:
        return None
    ps_final_off, ps_final_pops = ps_blocks[-1]
    # Epilogue size = pops + 1 (for ret).  When < 6b CloneCode inlines
    # both sides and there is no diff to surface.
    epilogue_size = ps_final_pops + 1
    if epilogue_size < 6:
        return None
    # PS funnel jmps target the final-epilogue region (last 16 bytes).
    ps_end_off = ps_insns[-1][0] + ps_insns[-1][1]
    funnel_lo = ps_final_off
    ps_jmps = []
    for ins in ps_insns:
        m = _fh_mnem(ins)
        if m not in ("jmp",) and not m.startswith("j"):
            continue
        t = _jmp_target(ins)
        if t is None:
            try:
                t = int(ins[3].split()[-1], 16)
            except ValueError:
                continue
        if funnel_lo <= t < ps_end_off and ins[0] < funnel_lo:
            ps_jmps.append((ins[0], t))
    # RC's NON-final epilogue blocks are the inlined per-exit copies.
    rc_non_final = [b for b in rc_blocks if b != rc_blocks[-1]]
    if len(ps_jmps) < 2 or len(rc_non_final) < 1:
        return None
    return EpilogueFunnelHint(
        func, ps_jmps, rc_non_final, epilogue_size)


def render_epilogue_funnel(h: EpilogueFunnelHint) -> list:
    sites = ", ".join(f"+{o:#x}->{t:#x}" for o, t in h.ps_jmps[:4])
    if len(h.ps_jmps) > 4:
        sites += f" (+{len(h.ps_jmps) - 4} more)"
    rc_sites = ", ".join(f"+{o:#x}({p}p)" for o, p in h.rc_rets[:4])
    return [
        f"Rule 148 (mid-function epilogue funnel): PS funnels "
        f"{len(h.ps_jmps)} early exit(s) via jmp-to-end "
        f"({sites}); RC inlines {len(h.rc_rets)} epilogue copies "
        f"({rc_sites}).  Final epilogue is {h.epilogue_size}b, "
        f"above CloneCode's <=5b inline threshold.",
        "  -> rewrite each early `return ...;` as `goto end;` and add "
        "a single `end:;` immediately before the natural body epilogue.  "
        "The frameless function still benefits because the funnel keeps "
        "each early exit as a 2-byte jmp instead of a 5+ byte inlined "
        "epilogue copy (initreg_game_loop: 228b -> 17b worked example, "
        "gloops.c, 2026-06-13).  Sibling: Rule 92 (per-return epilogue, "
        "the OPPOSITE direction -- when PS inlines and RC funnels).",
    ]


@dataclass
class GlobalEnregHint:
    func: str
    extra_save: str
    global_addr: int
    load_off: int          # PS-side offset
    spans_calls: int       # # of `call` insns between the load and last use


def detect_global_in_extra_callee_save(
    func: str, ps_insns: list, rc_insns: list,
) -> Optional[GlobalEnregHint]:
    """Rule 149: PS holds a global in the extra callee-save register
    across one or more calls; OUR build has a local that copies the
    global and terminates before the call, forcing RC to re-load after.

    Signal:
      - PS has exactly one extra callee-save register X (over RC's set)
      - PS body contains `mov X, [<imm_addr>]` -- a global load into X
      - At least one `call` instruction occurs after the load and
        before X's last body-use (so PS keeps the global alive across
        the call via X)

    Source recipe: locate the RC local that copies this global and
    DELETE it; read the global directly so the compiler enregisters
    it in a callee-save across the calls (initreg_game_loop's `region`
    de-invention, gloops.c, 2026-06-13)."""
    ps_saves = set(prologue_pushes(ps_insns))
    rc_saves = set(prologue_pushes(rc_insns))
    extra = ps_saves - rc_saves
    if len(extra) != 1:
        return None
    X = next(iter(extra))
    # Find the FIRST `mov X, [imm32]` (global load into X).
    load = None
    for ins in ps_insns:
        if _fh_mnem(ins) != "mov":
            continue
        ops = _fh_ops(ins)
        if len(ops) != 2 or ops[0] != X:
            continue
        # Source must be `[<imm32>]` form (a global memory read).
        src = ops[1]
        # Strict match: dword/byte/word ptr [<imm32>] or [<imm32>]
        m = re.match(r"(?:(?:dword|word|byte)\s+ptr\s+)?\[(0x[0-9a-fA-F]+)\]$",
                     src)
        if not m:
            continue
        load = (ins[0], int(m.group(1), 16))
        break
    if load is None:
        return None
    load_off, global_addr = load
    # Walk forward: find LAST body use of X.  Count `call` insns between
    # load_off and that last use.
    last_use_off = load_off
    calls_spanned = 0
    seen_call_since_load = False
    for ins in ps_insns:
        if ins[0] <= load_off:
            continue
        m = _fh_mnem(ins)
        if m == "call":
            seen_call_since_load = True
        elif X in ins[3]:
            last_use_off = ins[0]
            if seen_call_since_load:
                calls_spanned += 1
                seen_call_since_load = False
    if calls_spanned == 0:
        return None
    return GlobalEnregHint(func, X, global_addr, load_off, calls_spanned)


def render_global_in_extra_callee_save(h: GlobalEnregHint) -> list:
    return [
        f"Rule 149 (global cached in extra callee-save): PS holds the "
        f"global at [{h.global_addr:#x}] in {h.extra_save} across "
        f"{h.spans_calls} call(s) (loaded at +{h.load_off:#x}).",
        "  -> locate the RC source local that copies this global "
        "(typical shape: `<type> v = <global>; if (v == 0) return;` etc.)  "
        "and DELETE the local; read the global directly at each use site.  "
        "The local makes its own range terminate BEFORE the calls, forcing "
        "post-call re-loads; the global-direct form lets the compiler "
        "enregister the global in a callee-save across the calls.  Worked "
        "example: initreg_game_loop's `region` local (gloops.c, 228b->17b, "
        "2026-06-13).  Sibling: pragma_hints `ps_extra_callee_save` "
        "(general diagnostic line) + Rule 129 `Global re-read` (totals-"
        "based, fires when PS reloads >= RC+4 globally).",
        f"  -> CONFIRM in the alloc trace: `c2 regtrace {h.func}` -- if "
        f"the row at {h.extra_save} is an UNNAMED `(temp)` (CSE temp of "
        f"repeated global reads), the de-invent fix is correct; if it is "
        f"a NAMED local, the local exists in PS source too and the lever "
        f"is INVERSE (Rule 129 `add a local`).  The named-vs-CSE check "
        f"disambiguates which direction this row falls in.",
    ]


# ── CLI command (`c2 frame-hints`) ─────────────────────────────────────
#
# Single-purpose triager for the Rule 107 / Rule 117 frame-size lever.
# Reads the persisted ``frame_hint`` field from ``.c2-cache/verify.json``
# (computed by ``decomp_verify._frame_hint_for_json`` -> ``to_json``), so
# it never re-disassembles and is the same scalar that surfaces as the
# ``Frame:`` header in ``decomp-verify -v`` and as the ``[frame]`` bucket
# in ``c2 worklist``.


def _print_frame_block(name: str, fn: dict, fh: dict) -> None:
    delta = fh.get("delta", 0)
    sign = "+" if delta > 0 else ""
    slots = abs(fh.get("slot_delta", 0))
    slot_word = "slot" if slots == 1 else "slots"
    root = ("ROOT of cascade" if fh.get("is_root")
            else "downstream of an earlier diff")
    cls = ("WorthProlog spill-vs-callee-save" if fh.get("worthprolog_swap")
           else "structural (RC over-enregisters)" if fh.get("over_enregister")
           else "pressure-spill / Rule 116")
    from c2.regalloc.seat_recon import fmt_shape_cell as _sc
    typer.secho(f"  ✗  {name}  [{_sc(fn.get('shape_distance'))}]",
                fg="yellow")
    typer.echo(f"      Frame: PS sub esp,{fh.get('ps_frame', 0):#x}  "
               f"RC sub esp,{fh.get('rc_frame', 0):#x}  "
               f"({sign}{delta} b = {sign}{fh.get('slot_delta', 0)} "
               f"{slot_word}; pushes PS {fh.get('ps_pushes', 0)}/RC "
               f"{fh.get('rc_pushes', 0)})")
    typer.echo(f"      class: {cls}  [{root}]")
    typer.echo(f"      fix  : {fh.get('fix', '')}")


def frame_hints(
    name: Annotated[Optional[str], typer.Argument(
        help="function name (omit with --corpus)")] = None,
    corpus: Annotated[bool, typer.Option(
        "--corpus", help="rank every diffing function with a frame "
        "divergence by |slot delta| then diff bytes")] = False,
    limit: Annotated[int, typer.Option(
        "-n", "--limit", help="corpus: max rows (0 = all)")] = 0,
    as_json: Annotated[bool, typer.Option(
        "--json", help="emit the raw frame_hint record(s) as JSON")] = False,
) -> None:
    """Frame-size root-cause diagnostic (Rule 107 / Rule 117 companion).

    Turns the bare ``Frame:`` line into a root-cause verdict: the delta in
    whole 4-byte slots, whether the prologue is the cascade ROOT, and a
    sign-based fix direction (RC-bigger -> inline a superfluous named
    local; PS-bigger -> ordinary regalloc eviction).  Surfaces the same
    ``functions[].frame_hint`` the verifier persists, so it never rebuilds.
    """
    from c2.commands.verify_json import get_verify_json
    try:
        doc = get_verify_json()
    except FileNotFoundError:
        typer.secho("no .c2-cache/verify.json -- run `c2 decomp-verify "
                    "--json` once", fg="red", err=True)
        raise typer.Exit(1)
    funcs = doc.get("functions", [])

    if not corpus:
        if not name:
            typer.secho("[!] provide a function name or --corpus", fg="red",
                        err=True)
            raise typer.Exit(2)
        fn = next((f for f in funcs if f["name"] == name), None)
        if fn is None:
            typer.secho(f"[!] {name}: not in the verify set (byte-exact, "
                        "unknown, or cache stale)", fg="yellow")
            raise typer.Exit(1)
        fh = fn.get("frame_hint")
        if not fh:
            if as_json:
                typer.echo("null")
            else:
                typer.secho(f"  ✓  {name}: no frame divergence (PS and RC "
                            "allocate the same prologue frame)", fg="green")
            return
        if as_json:
            typer.echo(json.dumps({"name": name, **fh}, indent=2))
            return
        _print_frame_block(name, fn, fh)
        return

    # corpus mode
    rows = [f for f in funcs
            if f.get("diff_byte_count", 0) > 0 and f.get("frame_hint")]
    rows.sort(key=lambda f: (abs(f["frame_hint"].get("slot_delta", 0)),
                             f.get("diff_byte_count", 0)), reverse=True)
    if limit:
        rows = rows[:limit]
    if as_json:
        typer.echo(json.dumps(
            [{"name": f["name"], "diff_byte_count": f.get("diff_byte_count"),
              **f["frame_hint"]} for f in rows], indent=2))
        return
    typer.secho(f"\n# frame-hints: {len(rows)} diffing function(s) with a "
                "prologue frame divergence (Rule 107/117)\n", fg="cyan",
                bold=True)
    for f in rows:
        _print_frame_block(f["name"], f, f["frame_hint"])
