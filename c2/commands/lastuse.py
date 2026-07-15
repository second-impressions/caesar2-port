"""Layer-3 use-order analyzer (``c2 lastuse <fn>``) -- the Rule 28a half of the
layer-3 tie-break.

For a diffing function whose Regalloc diff is a *layer-3 register-identity
swap* (``Reg swap`` hint), this tool computes the concrete source-level
reorder that Rule 28a (commute / move a use) prescribes for the swap.

The mechanism (validated 7-layer model, ``docs/wcc386-re/regalloc-model.md`` §3):
equal-savings ties are resolved by ``regalloc.c::ConfBefore`` on the
**name-node pointer** (`a->name < b->name`), and the 1st-allocated takes the
higher-priority register (DoubleRegs = EAX > EDX > EBX > ECX > ESI > EDI > EBP).
Use position is a strong proxy for that key, since ``liveinfo.c::UpdateLive``
walks instructions backward and creates name nodes as it goes -- a value whose
**last use is earliest** (dies first) usually gets the earlier-allocated name
node and the higher register.  When PS puts a value in a higher register than
our build, that value usually dies earlier on PS's instruction stream, so the
Rule 28a lever is to make that value's last use come *earlier* in the statement
stream (or move the rival's trailing use later).

This analyzer:
  1. runs ``decomp-verify --json -f <fn>`` to get the aligned PS/RC rows
     (each with the original source line number ``ln``);
  2. finds the ``Reg swap`` rows and the swapped register pair (X↔Y);
  3. on the PS asm column, traces the *def* and *last use* of the value in
     each swapped register (a local register-liveness walk);
  4. maps those to source lines and prints which value PS gives the higher
     register, and the exact reorder to reproduce it.

Advisory: tells the agent *which two source statements* compete and *which*
way to reorder.  Doesn't edit source.  When the use is genuinely pinned (the
classifier returns ``pinned`` / ``correlated-home`` / ``callee-home``), the
Rule 28a lever is dead -- fall through to Rule 115 (swap the two tied locals'
declaration order; ``regtrace --explain`` will name the pair).
"""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
from io import StringIO
from contextlib import redirect_stdout

# DoubleRegs priority order (lower index == higher priority).
_DOUBLE_REGS = ["eax", "edx", "ebx", "ecx", "esi", "edi", "ebp"]
_PRIO = {r: i for i, r in enumerate(_DOUBLE_REGS)}

# sub-register -> enclosing 32-bit register
_SUB = {
    "al": "eax", "ah": "eax", "ax": "eax",
    "bl": "ebx", "bh": "ebx", "bx": "ebx",
    "cl": "ecx", "ch": "ecx", "cx": "ecx",
    "dl": "edx", "dh": "edx", "dx": "edx",
    "si": "esi", "di": "edi", "bp": "ebp", "sp": "esp",
}
_FULL = set(_DOUBLE_REGS) | {"esp"}
_REG_RE = re.compile(r"\b(e?[abcd]x|[abcd][lh]|e?(si|di|bp|sp))\b")


def _norm(reg: str) -> str:
    return _SUB.get(reg, reg)


def _regs_in(operand: str) -> list[str]:
    return [_norm(m.group(1)) for m in _REG_RE.finditer(operand)]


# Mnemonics whose destination operand is read-modify-write (reads dst too).
_RMW = {
    "add", "sub", "or", "and", "xor", "adc", "sbb", "inc", "dec", "neg",
    "not", "shl", "shr", "sar", "rol", "ror", "imul", "lea",
}
# Mnemonics that only read both operands.
_CMP = {"cmp", "test"}
# Mnemonics whose dest is written-only (no read of dest).
_WRITE_ONLY = {"mov", "movzx", "movsx", "pop", "lea"}
_CALL_CLOBBER = {"eax", "edx", "ebx", "ecx"}


@dataclass
class _Insn:
    idx: int
    off: int
    ln: int | None
    mn: str
    ops: str
    ps_asm: str = ""
    rc_asm: str = ""


def _reads_writes(ins: _Insn) -> tuple[set[str], set[str]]:
    """(regs read, regs written) for one instruction, conservative."""
    mn, ops = ins.mn, ins.ops
    parts = [p.strip() for p in ops.split(",")] if ops else []
    reads: set[str] = set()
    writes: set[str] = set()
    if mn == "call":
        return set(_regs_in(ops)), set(_CALL_CLOBBER)
    if mn in ("mul", "imul") and len(parts) == 1:
        return {"eax", *_regs_in(ops)}, {"eax", "edx"}
    if mn in ("div", "idiv"):
        return {"eax", "edx", *_regs_in(ops)}, {"eax", "edx"}
    if mn in ("push",) or mn.startswith("j") or mn in ("ret", "nop"):
        return set(_regs_in(ops)), set()
    if not parts:
        return set(_regs_in(ops)), set()
    dst, src = parts[0], (parts[1] if len(parts) > 1 else "")
    src_regs = set(_regs_in(src))
    dst_regs = set(_regs_in(dst))
    dst_is_mem = "[" in dst
    # memory operands: their address registers are always READ
    mem_addr = set(_regs_in(dst)) if dst_is_mem else set()
    mem_addr |= set(_regs_in(src)) if "[" in src else set()
    if mn in _CMP:
        return dst_regs | src_regs, set()
    if dst_is_mem:                       # store: dst regs are address (read)
        return mem_addr | src_regs, set()
    # dst is a register
    base_dst_reg = {_norm(dst)} if _norm(dst) in _FULL else set(_regs_in(dst))
    reads |= src_regs | mem_addr
    if mn in _RMW:
        reads |= base_dst_reg
    writes |= base_dst_reg
    return reads, writes


def _trace(insns: list[_Insn], at: int, reg: str) -> tuple[int | None, int | None]:
    """For the value living in `reg` at instruction index `at`, return
    (def_idx, last_use_idx): the instruction that defined it (last write at
    or before `at`) and its last use (last read at or after `at` before reg
    is rewritten).  Indices are into `insns`."""
    # def: nearest write to reg at or before `at`
    def_idx = None
    for i in range(at, -1, -1):
        r, w = _reads_writes(insns[i])
        if reg in w:
            def_idx = i
            break
    # last use: scan forward from def (or `at`), last read before a pure rewrite
    start = def_idx if def_idx is not None else at
    last_use = None
    for i in range(start + 1, len(insns)):
        r, w = _reads_writes(insns[i])
        if reg in r:
            last_use = i
        if reg in w and reg not in r:    # pure rewrite ends this value's life
            break
    return def_idx, last_use


def _verify_json(file: str, fn: str) -> dict | None:
    """Run decomp-verify --json for one function, return its record."""
    out = subprocess.run(
        ["uv", "run", "c2", "decomp-verify", file, "-f", fn,
         "--json", "--no-strict"],
        capture_output=True, text=True,
    ).stdout
    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        return None
    for f in data.get("functions", []):
        if f["name"] == fn:
            return f
    return None


def _describe(insns: list[_Insn], idx: int | None) -> str:
    if idx is None:
        return "?"
    ins = insns[idx]
    loc = f"line {ins.ln}" if ins.ln else f"+0x{ins.off:x}"
    return f"{loc}: {ins.mn} {ins.ops}".rstrip()


@dataclass
class SwapFinding:
    off: int
    ln: int | None
    higher_reg: str
    lower_reg: str
    hi_val_def: str
    hi_val_last: str
    lo_val_def: str
    lo_val_last: str
    hi_last_idx: int | None
    lo_last_idx: int | None
    kind: str = "two-value"   # two-value | single-home | pinned | untraceable


def _same_src(ps_asm: str, rc_asm: str) -> bool:
    """True if both rows are a register-dest move/load with the SAME source —
    i.e. one logical value being homed in a different register (NOT a
    two-value last-use competition)."""
    pm, _, po = ps_asm.partition(" ")
    rm, _, ro = rc_asm.partition(" ")
    if pm != rm or pm not in ("mov", "movzx", "movsx", "lea"):
        return False
    pp = [x.strip() for x in po.split(",", 1)]
    rp = [x.strip() for x in ro.split(",", 1)]
    if len(pp) != 2 or len(rp) != 2:
        return False
    # normalise fixup-masked hex disps (PS vs RC data segments differ)
    norm = lambda s: re.sub(r"0x[0-9a-f]+", "0x?", s)
    return norm(pp[1]) == norm(rp[1]) and pp[0] != rp[0] and "[" not in pp[0]


def analyze(file: str, fn: str) -> tuple[list[SwapFinding], str]:
    rec = _verify_json(file, fn)
    if rec is None:
        return [], f"could not verify {fn}"
    if rec.get("diff_byte_count", 0) == 0:
        return [], f"{fn} is already byte-exact"
    rows = rec.get("rows") or []
    # build the PS instruction stream (only rows with a ps side)
    insns: list[_Insn] = []
    row_to_insn: dict[int, int] = {}
    for ri, r in enumerate(rows):
        ps = r.get("ps") or {}
        asm = ps.get("asm")
        if not asm:
            continue
        mn, _, ops = asm.partition(" ")
        row_to_insn[ri] = len(insns)
        insns.append(_Insn(len(insns), r.get("off", 0), r.get("ln"),
                           mn.strip(), ops.strip(),
                           ps_asm=asm, rc_asm=(r.get("rc") or {}).get("asm", "")))
    findings: list[SwapFinding] = []
    for ri, r in enumerate(rows):
        if r.get("kind") != "replace":
            continue
        ps = (r.get("ps") or {}).get("asm", "")
        rc = (r.get("rc") or {}).get("asm", "")
        if not ps or not rc:
            continue
        # swapped register pair: same mnemonic, operands differ only by regs
        pm, _, po = ps.partition(" ")
        rm, _, ro = rc.partition(" ")
        if pm != rm:
            continue
        preg, rreg = _regs_in(po), _regs_in(ro)
        if len(preg) != len(rreg):
            continue
        swap_pair = None
        ok = True
        for a, b in zip(preg, rreg):
            if a == b:
                continue
            if a in _PRIO and b in _PRIO:
                if swap_pair and swap_pair != (a, b):
                    ok = False
                    break
                swap_pair = (a, b)
            else:
                ok = False
                break
        if not ok or not swap_pair:
            continue
        ps_reg, rc_reg = swap_pair        # PS uses ps_reg, recomp uses rc_reg
        at = row_to_insn.get(ri)
        if at is None:
            continue
        # single-value register-home: same source moved to a different reg.
        if _same_src(ps, rc):
            findings.append(SwapFinding(
                off=r.get("off", 0), ln=r.get("ln"),
                higher_reg=(ps_reg if _PRIO[ps_reg] < _PRIO[rc_reg] else rc_reg),
                lower_reg=(rc_reg if _PRIO[ps_reg] < _PRIO[rc_reg] else ps_reg),
                hi_val_def="", hi_val_last="", lo_val_def="", lo_val_last="",
                hi_last_idx=None, lo_last_idx=None, kind="single-home"))
            continue
        # the value at this row goes to ps_reg (PS) vs rc_reg (recomp).
        # rival = whatever PS keeps in rc_reg around here.
        v_def, v_last = _trace(insns, at, ps_reg)
        w_def, w_last = _trace(insns, at, rc_reg)
        # which register is higher priority?
        if _PRIO[ps_reg] < _PRIO[rc_reg]:
            hi, lo = ps_reg, rc_reg
            hi_def, hi_last = v_def, v_last
            lo_def, lo_last = w_def, w_last
        else:
            hi, lo = rc_reg, ps_reg
            hi_def, hi_last = w_def, w_last
            lo_def, lo_last = v_def, v_last
        # Correlated-home: if BOTH values are defined by single-home moves
        # (their home register is swapped at the def site, e.g. two entry
        # params homed to esi/edi vs edi/esi), the use-site swap is downstream
        # of a whole-function home choice — reordering uses does NOT help
        # (validated on start_sound: the lever precondition was already met
        # yet the swap persisted).
        def _def_is_single_home(di):
            return (di is not None
                    and _same_src(insns[di].ps_asm, insns[di].rc_asm))
        _CALLEE = {"esi", "edi", "ebp"}
        if hi_last is None or lo_last is None or hi_def == lo_def:
            kind = "untraceable"
        elif _def_is_single_home(hi_def) and _def_is_single_home(lo_def):
            kind = "correlated-home"
        elif hi in _CALLEE and lo in _CALLEE:
            # both callee-save: a long-lived-value HOME (savings/capacity)
            # decision across calls, not a short-lived caller-saved last-use
            # tie-break.  Validated not-reorderable on start_sound /
            # get_linked_page (esi/edi/ebp pairs).
            kind = "callee-home"
        elif hi_last <= lo_last:
            kind = "two-value"      # actionable: caller-saved last-use swap
        else:
            kind = "pinned"
        findings.append(SwapFinding(
            off=r.get("off", 0), ln=r.get("ln"),
            higher_reg=hi, lower_reg=lo,
            hi_val_def=_describe(insns, hi_def),
            hi_val_last=_describe(insns, hi_last),
            lo_val_def=_describe(insns, lo_def),
            lo_val_last=_describe(insns, lo_last),
            hi_last_idx=hi_last, lo_last_idx=lo_last, kind=kind,
        ))
    return findings, ""


def _resolve_file(fn: str) -> str | None:
    """Find the decomp/src/*.c file that defines `fn`."""
    import glob
    pat = re.compile(
        r"^[A-Za-z_][\w ]*\b" + re.escape(fn) + r"\s*\(", re.M)
    for path in sorted(glob.glob("decomp/src/*.c")):
        try:
            with open(path) as fh:
                txt = fh.read()
        except OSError:
            continue
        # require a definition (a `{` after the signature, not just a decl)
        for m in pat.finditer(txt):
            tail = txt[m.start():m.start() + 400]
            if ");" not in tail.split("{", 1)[0] and "{" in tail:
                return path
    return None


def lastuse(name: str) -> None:
    """Compute the layer-3 last-use reorder for a Reg-swap diff.

    NAME is a function with a `Reg swap` regalloc diff.  Prints which value
    PS gives the higher-priority register and the exact source reorder
    (per docs/codegen-experiments/regalloc-last-use.py) to reproduce it.
    """
    import typer
    from rich.console import Console

    c = Console(color_system=None)
    file = _resolve_file(name)
    if file is None:
        c.print(f"[red]could not find a definition of {name} in decomp/src[/]")
        raise typer.Exit(1)
    findings, err = analyze(file, name)
    if err:
        c.print(f"[yellow]{err}[/]")
        raise typer.Exit(0 if "byte-exact" in err else 1)
    if not findings:
        c.print(f"[yellow]{name}: no layer-3 register-identity swap found "
                f"(diff may be layer-4 accumulator, tail-merge, or "
                f"instruction-selection — not a last-use case).[/]")
        raise typer.Exit(0)
    c.print(f"[bold]{name}[/]  ({file})")
    c.print(f"  Model: dies-first → higher reg "
            f"(EAX>EDX>EBX>ECX>ESI>EDI>EBP); proof regalloc-last-use.py")
    counts = {}
    for f in findings:
        counts[f.kind] = counts.get(f.kind, 0) + 1
    c.print(f"  {len(findings)} swap row(s): " +
            ", ".join(f"{v}× {k}" for k, v in counts.items()) + "\n")
    for i, f in enumerate(findings, 1):
        loc = f"line {f.ln}" if f.ln else f"+0x{f.off:x}"
        head = (f"[bold cyan]swap #{i}[/] at {loc}: "
                f"PS gives [green]{f.higher_reg}[/] (higher) vs our "
                f"[red]{f.lower_reg}[/]")
        if f.kind == "single-home":
            c.print(head + "  — [magenta]SINGLE-VALUE HOME[/]")
            c.print(f"  one value moved to a different home register "
                    f"(same source).  This is a whole-function register-home "
                    f"choice, NOT a last-use tie-break — reordering uses will "
                    f"NOT move it.  (capacity/CountRegMoves class)\n")
            continue
        if f.kind == "callee-home":
            c.print(head + "  — [magenta]CALLEE-SAVE HOME[/]")
            c.print(f"  both registers are callee-save (esi/edi/ebp): this is "
                    f"a long-lived-value home (savings/capacity) decision "
                    f"across calls, not a short-lived last-use tie-break — "
                    f"reordering uses is unlikely to move it.\n")
            continue
        if f.kind == "correlated-home":
            c.print(head + "  — [magenta]CORRELATED HOME[/]")
            c.print(f"  both values are homed via single-home moves (their "
                    f"home regs are swapped at the def site).  The use-site "
                    f"swap is downstream of a whole-function home choice — "
                    f"reordering uses will NOT move it.\n")
            continue
        c.print(head)
        c.print(f"  value PS puts in {f.higher_reg} (dies first):")
        c.print(f"    def : {f.hi_val_def}")
        c.print(f"    last: {f.hi_val_last}")
        c.print(f"  rival PS puts in {f.lower_reg} (dies later):")
        c.print(f"    def : {f.lo_val_def}")
        c.print(f"    last: {f.lo_val_last}")
        if f.kind == "two-value":
            c.print(f"  [bold green]Lever (actionable)[/]: PS's {f.higher_reg}-"
                    f"value last use ({f.hi_val_last.split(':')[0]}) precedes "
                    f"the rival's ({f.lo_val_last.split(':')[0]}).  Reorder our "
                    f"source so that value's last use comes [bold]earlier[/] "
                    f"than the rival's — move the rival's trailing use later, or "
                    f"hoist the target's final read up.\n")
        elif f.kind == "pinned":
            c.print(f"  [yellow]Pinned[/]: target's last use is NOT earlier in "
                    f"the PS stream — both last uses fixed by the algorithm; "
                    f"reordering won't help.\n")
        else:
            c.print("  [yellow]Untraceable[/]: a value's def/last-use couldn't "
                    "be isolated (call-clobbered or index-only) — likely an "
                    "index-scratch case (Rule 96 family), not last-use.\n")
