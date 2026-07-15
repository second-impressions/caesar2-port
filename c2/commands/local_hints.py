"""local-hints — which memory-rooted values were REAL named locals in PS source?

The session-validated insight: most temporaries in PS.EXE are Watcom's own
(promotion temps, CSE temps), NOT source variables — but *some* loads really
were `int step = s->step_pixels;` statements (slider_control L404-407), and
naming/de-naming them is one of the highest-leverage source-shape levers
(get_morale_and_readiness 162→0, slider_control 156→3, handle_collision 84→0
all hinged on it).

This module reads ONLY what is available for an unsolved function — the
PS.EXE disassembly + its original -d1 line records — and classifies each
memory load as:

  REAL    the source had a named local assigned from this read
  INLINE  the source read the expression in place (no local)

Three signals, each with an independent rationale:

  A  standalone-assign run   A -d1 line run consisting ONLY of loads /
                             register arithmetic (no compare, no jump, no
                             call, no store) is an assignment statement —
                             its load(s) feed a named local.
  B  hold across a call      A loaded value that survives a `call` in a
                             callee-save register and is used afterwards
                             cannot be compiler CSE (calls invalidate global
                             CSE; watcall clobbers eax/edx/ebx/ecx) — only a
                             source-level local produces that.
  C  reload, same value      The same address re-loaded while the previous
                             value was still valid (no store to the symbol
                             between) means the source re-read the
                             expression: a named local NEVER re-touches its
                             memory home.

`--validate` scores the detector against the byte-exact corpus: for every
byte-exact function the true source is OURS, the recompiled -d1 line table
(dumped by decomp-verify into .c2-cache/exact-line-map.json) maps each code
offset to OUR source line, and pycparser labels each line as a local-assign
or an inline read.  Per-signal precision is reported so the hint's accuracy
is a measured number, not a guess.

Measured against the byte-exact corpus with a PER-SYMBOL ground truth
(`--validate`).  The earlier line-granularity ground truth was WRONG: it
marked an entire source line REAL whenever any scalar local was assigned
on it, so every operand (`x = a + global`), call-arg (`x = f(global)`) and
array-index (`a[global]`) read on that line was mislabelled REAL.  That
reported a fictitious 94% REAL / 95% INLINE; the per-symbol truth is:

    INLINE (signal C)   ~99%    (the de-invent workhorse; trustworthy)
    REAL   (signal A)   ~94%    (gate 5 lifts it from a true 40% by
                                 abstaining loads consumed within their
                                 own -d1 run -- an inline sub-expression)

Signal B (hold-across-call) measured at 73% — demoted to the advisory
lowercase 'b' tag, NOT counted in the verdict (subregister aliasing and
held screen-globals pollute it).  The abstain class is the honest third
answer: split multi-line statements (`if (arr[i]\n & 0xe7)`), argument
computations, return expressions and pointer-base fetches are
*byte-identical* to local assignments and cannot be decided from the
binary alone.

The DE-INVENT / ADD-LOCAL cross-check (`_disagreements`) has a second,
cleaner ground truth: on the byte-exact corpus the source IS PS-faithful,
so it must recommend NOTHING -- every firing is a false positive.  Three
guards drive that FP count from 12 -> 1 (1301 fns) with ZERO per-load
recall loss, while keeping every genuine diffing lever:

  * DE-INVENT requires sv == {REAL} EXCLUSIVELY -- a source that mixes a
    cache with inline reads of the same global is the deliberate Rule-116
    reload pattern PS uses, not an over-cache (this_region_box, smk).
  * DE-INVENT is suppressed when the global is HELD across a call (signal
    'b') -- that is real callee-save-local evidence the verdict demotes
    (battle_stats_nof_units: deleting it regressed 350->441b).
  * ADD-LOCAL REQUIRES signal 'b' -- a bare signal-A REAL (94%) produces
    the add-local FP class (player_rank, current_palette); a value PS
    genuinely named is one it holds across a call.

The lone residual FP (new_province/c2inf+0x34) is a struct FIELD the AST
cannot disambiguate from its siblings (it keys on the base symbol name,
not the field offset); it is byte-exact so it never reaches the diffing
frontier `--vs-source --corpus` shows.  REACH: the cross-check keys on
resolved global symbols, scalar AND indexed (`arr[i]`); pure local-pointer
field derefs (`p->field`, ~5% of loads) have no AST-nameable base and are
out of scope.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table
from typing_extensions import Annotated

console = Console()

SIDECAR_PATH = Path(".c2-cache/exact-line-map.json")

_REG_FAMILY = {
    "eax": "eax", "ax": "eax", "al": "eax", "ah": "eax",
    "edx": "edx", "dx": "edx", "dl": "edx", "dh": "edx",
    "ebx": "ebx", "bx": "ebx", "bl": "ebx", "bh": "ebx",
    "ecx": "ecx", "cx": "ecx", "cl": "ecx", "ch": "ecx",
    "esi": "esi", "si": "esi",
    "edi": "edi", "di": "edi",
    "ebp": "ebp", "bp": "ebp",
    "esp": "esp", "sp": "esp",
}
# __watcall: the callee saves every register it uses except EAX (the
# return).  From the caller's view only EAX is clobbered by a call.
_CALL_CLOBBERS = {"eax"}

_JCC = re.compile(r"^j[a-z]+$")
_MEM = re.compile(r"\[([^\]]+)\]")
_ARITH_RMW = {
    "add", "sub", "and", "or", "xor", "adc", "sbb", "inc", "dec",
    "neg", "not", "shl", "shr", "sar", "rol", "ror", "imul",
}


def _fam(reg: str) -> str | None:
    return _REG_FAMILY.get(reg.strip())


def _split_ops(op_str: str) -> list[str]:
    return [o.strip() for o in op_str.split(",")] if op_str else []


def _mem_operand(op: str) -> str | None:
    m = _MEM.search(op)
    return m.group(1) if m else None


def _is_stack_mem(mem: str) -> bool:
    return "esp" in mem or "ebp" in mem


def _mem_regs(mem: str) -> list[str]:
    regs = []
    for tok in re.split(r"[+*\s]", mem):
        f = _fam(tok)
        if f and f not in regs:
            regs.append(f)
    return regs


def _key_for(ln, mem: str) -> str | None:
    """Stable identity for a memory operand, or None if untrackable.

    Indexed operands include their registers in the key: two loads of
    `[eax*4 + lson]` with a re-written EAX between them are NOT the same
    address, so a reload there says nothing (DeleteNode false-INLINE)."""
    if _is_stack_mem(mem):
        return None                      # stack slot = a local's own home
    regs = _mem_regs(mem)
    if ln.data_ref:
        base = f"@{ln.data_ref}"
        return base + ("|" + "+".join(regs) if regs else "")
    parts = [p.strip() for p in mem.split("+")]
    return "+".join(parts)


def _key_symbol(key: str) -> str | None:
    """Base symbol of a data_ref key ('@army_list+0x25|eax' -> 'army_list')."""
    if key.startswith("@"):
        return key[1:].split("|")[0].split("+")[0].split("-")[0]
    return None


def _key_regs(key: str) -> set[str]:
    """Registers whose redefinition invalidates address identity."""
    if key.startswith("@"):
        if "|" in key:
            return {f for f in (_fam(r) for r in key.split("|")[1].split("+")) if f}
        return set()
    return {f for f in (_fam(tok) for tok in key.split("+")) if f}


# Zero-extend masks: `and reg, 0xff/0xffff` is a (unsigned char/short) CAST,
# not a value transform - `int x = (unsigned char)global` is still REAL.
_ZEXT_MASKS = frozenset({0xFF, 0xFFFF})


def _imm_val(op: str):
    try:
        return int(op.strip(), 0)
    except ValueError:
        return None


def _consumed_in_run(insns: list, idx: int, reg0: str) -> bool:
    """Signal-A gate: True (=> INLINE) iff the value loaded at ``insns[idx]``
    is consumed WITHIN its own ``-d1`` line run -- transformed by an arithmetic
    op, used as a memory INDEX, fed to a compare/division, or stored to a
    GLOBAL.  A value that SURVIVES its run untouched (or is only spilled to a
    STACK home / copied) lived past the statement, which is the named-local
    (`x = global;` on its own line) REAL signature.

    Scoping to the run is the principled discriminator: PS emits a separate
    ``-d1`` line per source statement, so ``step = sliders->step_pixels;``
    loads on its own line (survives the run -> REAL), whereas
    ``pick = rand128 & 7;`` loads AND masks on one line (the mask is in-run ->
    INLINE).  Cross-run consumption (a split statement) is already handled by
    gate 1 (``consumed_next``).  Zext-mask ``and reg, 0xff/0xffff`` is a cast,
    not a transform.  Plain reg->reg copies are followed.
    """
    run = insns[idx].run
    regs = {reg0}
    for insn in insns[idx + 1:]:
        if insn.run != run:
            return False                    # survived the statement -> REAL
        m, ops = insn.mnemonic, insn.ops
        # used as an address/index register -> the value is a subscript
        for op in ops:
            mem = _mem_operand(op)
            if mem and (regs & set(_mem_regs(mem))):
                return True
        # zext-mask cast on a tracked reg -> NOT a transform; keep tracking
        if (m == "and" and len(ops) == 2 and _fam(ops[0]) in regs
                and _imm_val(ops[1]) in _ZEXT_MASKS):
            continue
        # copy / store with a tracked reg as the source
        if m in ("mov", "movsx", "movzx") and len(ops) == 2 and _fam(ops[1]) in regs:
            dmem = _mem_operand(ops[0])
            if dmem is None:
                df = _fam(ops[0])
                if df:
                    regs.add(df)            # reg->reg copy: keep tracking
                continue
            if _is_stack_mem(dmem):
                return False                # spilled to a stack local home
            return True                     # stored to a global -> inline
        # any other read OR write of a tracked reg consumes/transforms it
        if (regs & insn.reads) or (regs & insn.writes):
            return True
    return False


@dataclass
class LoadSite:
    idx: int                  # instruction index
    off: int                  # offset within function
    line: int                 # PS -d1 line (inherited)
    run: int                  # line-run ordinal
    reg: str                  # destination register family
    key: str                  # memory identity
    verdicts: list[str] = field(default_factory=list)   # signal letters
    c_call_free: bool = False  # an INLINE (signal C) reload with NO call
                               # between the two loads -- the only PROOF PS
                               # reads the global inline rather than caching it
                               # in a register per region (de-invent needs this)

    @property
    def verdict(self) -> str | None:
        # 'b' (hold-across-call) is advisory only — 73% precision measured,
        # polluted by subregister aliasing and screen-global holds.
        real = any(v == "A" for v in self.verdicts)
        inline = "C" in self.verdicts
        if real and inline:
            return None                  # conflict -> abstain
        if real:
            return "REAL"
        if inline:
            return "INLINE"
        return None


@dataclass
class Insn:
    off: int
    line: int          # inherited -d1 line
    run: int
    mnemonic: str
    ops: list[str]
    data_ref: str | None
    is_call: bool
    is_jump: bool
    is_cmp: bool
    load: tuple[str, str] | None    # (dest reg family, key)
    store_key: str | None           # key stored to (None if no mem store)
    store_unknown: bool             # store through untrackable pointer
    writes: set[str]                # register families written
    reads: set[str]                 # register families read


def _decode(lines) -> list[Insn]:
    out: list[Insn] = []
    cur_line = 0
    run = -1
    for i, ln in enumerate(lines):
        if ln.line:
            cur_line = ln.line
            run += 1
        mnem = ln.mnemonic
        ops = _split_ops(ln.op_str)
        is_call = mnem == "call"
        is_jump = mnem == "jmp" or bool(_JCC.match(mnem))
        is_cmp = mnem in ("cmp", "test")
        load = None
        store_key = None
        store_unknown = False
        writes: set[str] = set()
        reads: set[str] = set()

        # register reads/writes (coarse)
        for j, op in enumerate(ops):
            mem = _mem_operand(op)
            if mem:
                for tok in re.split(r"[+*\s]", mem):
                    f = _fam(tok)
                    if f:
                        reads.add(f)
            else:
                f = _fam(op)
                if f:
                    if j == 0 and mnem not in ("cmp", "test", "push"):
                        writes.add(f)
                        if mnem in _ARITH_RMW:
                            reads.add(f)
                    else:
                        reads.add(f)

        if is_call:
            writes |= _CALL_CLOBBERS
        # implicit register writes
        if mnem in ("cdq", "cwd", "cwde", "cbw"):
            writes |= {"eax", "edx"}
        elif mnem in ("mul", "imul", "div", "idiv") and len(ops) == 1:
            writes |= {"eax", "edx"}
        elif mnem.startswith(("movs", "stos", "lods", "scas", "cmps")) and not ops:
            writes |= {"esi", "edi", "ecx", "eax"}
        elif mnem == "pop" and ops and _fam(ops[0]):
            writes.add(_fam(ops[0]))
        elif mnem == "xchg":
            for op in ops:
                f = _fam(op)
                if f:
                    writes.add(f)

        if ops:
            mem0 = _mem_operand(ops[0])
            if mem0 is not None and mnem not in ("cmp", "test", "push", "lea"):
                # destination is memory -> store
                k = _key_for(ln, mem0)
                if k is None and not _is_stack_mem(mem0):
                    store_unknown = True
                store_key = k
            elif (mnem in ("mov", "movsx", "movzx") and len(ops) == 2
                  and _mem_operand(ops[1]) is not None):
                mem1 = _mem_operand(ops[1])
                k = _key_for(ln, mem1)
                f = _fam(ops[0])
                if k is not None and f is not None:
                    load = (f, k)

        out.append(Insn(
            off=ln.address, line=cur_line, run=run, mnemonic=mnem, ops=ops,
            data_ref=ln.data_ref, is_call=is_call, is_jump=is_jump,
            is_cmp=is_cmp, load=load, store_key=store_key,
            store_unknown=store_unknown, writes=writes, reads=reads,
        ))
    # rebase offsets to fn-relative
    if out:
        base = out[0].off
        for insn in out:
            insn.off -= base
    return out


def analyze(fn: str) -> list[LoadSite]:
    """Run the detector over one PS.EXE function."""
    from c2.commands.disasm import disasm_function

    _addr, _size, lines = disasm_function(fn)
    insns = _decode(lines)
    sites: list[LoadSite] = []
    for i, insn in enumerate(insns):
        if insn.load:
            reg, key = insn.load
            sites.append(LoadSite(idx=i, off=insn.off, line=insn.line,
                                  run=insn.run, reg=reg, key=key))

    # ── Signal A: standalone-assign line runs ────────────────────────────
    runs: dict[int, list[Insn]] = {}
    for insn in insns:
        runs.setdefault(insn.run, []).append(insn)
    good_runs: set[int] = set()
    for rid, body in runs.items():
        if rid == 0:
            continue                      # prologue / first statement
        has_load = any(x.load for x in body)
        bad = any(
            x.is_call or x.is_jump or x.is_cmp or x.store_key is not None
            or x.store_unknown or x.mnemonic in ("push", "pop", "ret", "leave")
            for x in body
        )
        if has_load and not bad:
            good_runs.add(rid)
    # Gate 1: a load-only run whose value is consumed in the IMMEDIATELY
    # following run is indistinguishable from a multi-line statement —
    # `if (arr[idx]\n    & 0xe7)`, `f(arr[idx]);` across two lines, and
    # `randseed = randseed * k\n    + 1;` all produce a load-only run whose
    # reg the next run reads.  `x = arr[idx]; <use x>` compiles identically,
    # so abstain; A only fires when the value's first use is FARTHER away
    # (a split statement's parts are always adjacent).
    run_first: dict[int, int] = {}
    for i, insn in enumerate(insns):
        run_first.setdefault(insn.run, i)
    for s in sites:
        if s.run not in good_runs:
            continue
        nxt = run_first.get(s.run + 1)
        consumed_next = False
        if nxt is not None:
            for insn in insns[nxt:]:
                if insn.run > s.run + 1:
                    break
                if s.reg in insn.reads or insn.is_call:
                    consumed_next = True
                    break
                if s.reg in insn.writes:
                    break
        if consumed_next:
            continue
        # Gate 2: keys without a resolved symbol that involve scaling or
        # two registers are pointer+index array walks (lson[i] stores,
        # unrolled blit loops) — not local assignments.
        if not s.key.startswith("@") and (
                "*" in s.key or len(_key_regs(s.key)) >= 2):
            continue
        # Gate 3: a load-only run right before the epilogue is a
        # `return global <op> ...;` statement, not a local assignment.
        nxt_body = []
        if nxt is not None:
            for insn in insns[nxt:]:
                if insn.run > s.run + 1:
                    break
                nxt_body.append(insn)
        if any(x.mnemonic == "ret" for x in nxt_body):
            continue
        # Gate 4: if the value's FIRST use is as an ADDRESS register (inside
        # a [mem] operand), this was a pointer-base fetch for a multi-line
        # access expression (`son[i] = ...` loads the `son` pointer global
        # on its own line) — ambiguous, abstain.
        addr_use = False
        for insn in insns[s.idx + 1:]:
            used_in_mem = False
            for op in insn.ops:
                mem = _mem_operand(op)
                if mem and s.reg in _mem_regs(mem):
                    used_in_mem = True
            if used_in_mem:
                addr_use = True
                break
            if s.reg in insn.reads:
                break
            if s.reg in insn.writes:
                break
        if addr_use:
            continue
        # Gate 5: the loaded value must SURVIVE its own -d1 run to be a
        # named local (`x = global;` on its own line).  If it is
        # transformed by an arithmetic op, used as a [mem] INDEX, fed to a
        # compare/division, or stored to a global WITHIN the run
        # (`x = global & 7;`, `x = a + g`, `a[g]`), the load is an INLINE
        # sub-expression.  Dominant signal-A false-positive class
        # (40%->75% precision; see test_local_hints).
        if _consumed_in_run(insns, s.idx, s.reg):
            continue
        s.verdicts.append("A")

    # ── Signal B: value held across a call, used after ───────────────────
    # A global-derived value reused after a call cannot be compiler CSE
    # (the call may store to the global, killing the equivalence); only a
    # source-level local keeps the value live.  Any register but EAX
    # survives a __watcall call.
    for s in sites:
        if s.reg == "eax":
            continue
        # byte/word loads (mov ch, [m]) make family-level liveness tracking
        # unsound (the full reg may carry an unrelated value) — 32-bit only.
        dest = insns[s.idx].ops[0] if insns[s.idx].ops else ""
        if not dest.startswith("e"):
            continue
        seen_call = False
        for insn in insns[s.idx + 1:]:
            if s.reg in insn.writes:
                break
            if insn.is_call:
                seen_call = True
                continue
            if seen_call and s.reg in insn.reads:
                s.verdicts.append("b")
                break

    # ── Signal C: reload while previous value still valid ────────────────
    by_key: dict[str, list[LoadSite]] = {}
    for s in sites:
        by_key.setdefault(s.key, []).append(s)
    for key, ks in by_key.items():
        if len(ks) < 2:
            continue
        sym = _key_symbol(key)
        kregs = _key_regs(key)
        for a, b in zip(ks, ks[1:]):
            if a.run == b.run:
                continue                  # same statement (e.g. cmp chain)
            # a reload whose site sits in a load-only run may be a SECOND
            # assignment statement (`n = global;` twice) — only claim
            # INLINE for reads embedded in compute/compare/store runs.
            if a.run in good_runs or b.run in good_runs:
                continue
            ok = True
            call_between = False
            for insn in insns[a.idx + 1: b.idx]:
                if insn.is_call:
                    call_between = True
                if insn.store_unknown:
                    ok = False
                    break
                if insn.store_key is not None and sym is not None and \
                        _key_symbol(insn.store_key) == sym:
                    ok = False
                    break
                if insn.store_key == key:
                    ok = False
                    break
                if kregs & insn.writes:
                    ok = False
                    break
            if ok:
                if "C" not in a.verdicts:
                    a.verdicts.append("C")
                if "C" not in b.verdicts:
                    b.verdicts.append("C")
                if not call_between:      # genuine inline (not a forced reload)
                    a.c_call_free = True
                    b.c_call_free = True
    return sites


# ── Register-rooted named locals (the class the load signals can't see) ──────

def _statement_locals_from_insns(insns) -> list[dict]:
    """Per -d1 STATEMENT run, flag the ones that produce a register-rooted
    named local: a PURE-computation run (no compare/branch/call/store) whose
    result SURVIVES the statement as a VALUE (read in a later run, not merely
    as a memory-address base).  A CSE temp's value is consumed inside its own
    statement; a named local's value outlives it."""
    from collections import defaultdict
    by: dict[int, list] = defaultdict(list)
    for ins in insns:
        by[ins.run].append(ins)
    clean: set[int] = set()
    for r, body in by.items():
        if r == 0:
            continue                       # prologue / first statement
        bad = any(
            x.is_call or x.is_jump or x.is_cmp or x.store_key is not None
            or x.store_unknown
            or x.mnemonic in ("push", "pop", "ret", "leave")
            for x in body
        )
        if not bad:
            clean.add(r)
    # runs that contain the epilogue (ret/leave): a value whose only later
    # use lands here is a RETURN value funnelled through the exit, not a
    # named local (`return 0/1/-1`, often staged in a callee-save).
    ret_runs = {r for r, body in by.items()
                if any(x.mnemonic in ("ret", "leave") for x in body)}
    n = len(insns)
    rows: list[dict] = []
    seen: set[int] = set()
    for i, ins in enumerate(insns):
        if ins.run not in clean or ins.run in seen:
            continue
        for f in ins.writes:
            j = i + 1
            value_liveout = False
            use_run = None
            while j < n:
                nxt = insns[j]
                if f in nxt.reads:
                    # used ONLY as a memory-address base => pointer/index temp
                    addr_only = True
                    for op in nxt.ops:
                        m = _mem_operand(op)
                        if not (m and f in _mem_regs(m)) and _fam(op) == f:
                            addr_only = False
                    if nxt.run > ins.run:
                        value_liveout = not addr_only
                        use_run = nxt.run
                    break
                if f in nxt.writes:
                    break
                j += 1
            if value_liveout and use_run in ret_runs:
                continue                   # return value, not a named local
            if value_liveout:
                rows.append({"run": ins.run, "off": ins.off,
                             "line": ins.line, "reg": f})
                seen.add(ins.run)
                break
    return rows


def statement_locals(fn: str) -> list[dict]:
    """ADVISORY (~92% precision, ~19% recall vs the byte-exact corpus): which
    -d1 STATEMENTS produce a REGISTER-ROOTED named local -- the class the
    load-based REAL/INLINE verdicts structurally cannot see (`t = a + b`,
    `x = f()`, `p = q`: no global memory load, ~82% of all scalar locals).

    Complements `analyze` (memory loads): together they widen the detector
    from the ~18% memory-rooted locals toward the register-computed ones.  It
    is ADVISORY ONLY -- ~92% precision (measured vs the byte-exact corpus,
    GT including parameters), still below the 94/99% of the load signals
    (watcall callee-saves every reg but EAX, so liveness is noisy, and -d1
    line attribution blurs multi-statement regions; the residue is struct-field
    RMW + if-condition address bases) -- so it is kept OUT of the authoritative
    REAL/INLINE verdict and the de-invent/add-local cross-check.  Recall is
    ~19% of register-rooted local-assign lines: deliberately one-sided
    (allowing call-result locals would crater precision 92->70%).  Returns one
    row {run, off, line, reg} per producing run.
    """
    from c2.commands.disasm import disasm_function
    _addr, _size, lines = disasm_function(fn)
    return _statement_locals_from_insns(_decode(lines))


# ── Ground truth from the byte-exact corpus ─────────────────────────────────

def _read_base_symbol(node, local_names: set, call_names: set):
    """The base global symbol of a memory-read expression (the leftmost ID
    after stripping casts / [] / . / *), or None if it bottoms out at a local
    or a call name."""
    import pycparser.c_ast as c
    n = node
    while True:
        if isinstance(n, c.Cast):
            n = n.expr
        elif isinstance(n, c.ArrayRef):
            n = n.name
        elif isinstance(n, c.StructRef):
            n = n.name
        elif isinstance(n, c.UnaryOp) and n.op == "*":
            n = n.expr
        else:
            break
    if isinstance(n, c.ID) and n.name not in local_names and n.name not in call_names:
        return n.name
    return None


def _strip_cast(n):
    import pycparser.c_ast as c
    while isinstance(n, c.Cast):
        n = n.expr
    return n


def _is_mem_read_node(n) -> bool:
    import pycparser.c_ast as c
    return (isinstance(n, (c.ArrayRef, c.StructRef))
            or (isinstance(n, c.UnaryOp) and n.op == "*")
            or isinstance(n, c.ID))


def _collect_addr_indices(name, local_names, call_names, out):
    """Walk a memory-access *address* chain emitting only its SUBSCRIPT reads
    (e.g. the `i` in `a[i][j]`), not the address base itself."""
    import pycparser.c_ast as c
    n = name
    while True:
        if isinstance(n, c.Cast):
            n = n.expr
        elif isinstance(n, c.StructRef):
            n = n.name
        elif isinstance(n, c.ArrayRef):
            _collect_reads(n.subscript, local_names, call_names, out)
            n = n.name
        elif isinstance(n, c.UnaryOp) and n.op == "*":
            _collect_reads(n.expr, local_names, call_names, out)
            break
        else:
            break


def _collect_reads(expr, local_names, call_names, out):
    """Append ``(line, base_symbol, node_id)`` for every GLOBAL memory read in
    ``expr``.  An array/struct/deref access is ONE read (its base symbol); its
    subscript/index globals are separate reads; the address base ID itself is
    not double-counted."""
    import pycparser.c_ast as c
    if expr is None:
        return
    if (isinstance(expr, (c.ArrayRef, c.StructRef))
            or (isinstance(expr, c.UnaryOp) and expr.op == "*")):
        base = _read_base_symbol(expr, local_names, call_names)
        if base is not None and expr.coord:
            out.append((expr.coord.line, base, id(expr)))
        if isinstance(expr, c.ArrayRef):
            _collect_reads(expr.subscript, local_names, call_names, out)
            _collect_addr_indices(expr.name, local_names, call_names, out)
        elif isinstance(expr, c.StructRef):
            _collect_addr_indices(expr.name, local_names, call_names, out)
        else:
            _collect_reads(expr.expr, local_names, call_names, out)
        return
    if isinstance(expr, c.ID):
        if (expr.name not in local_names and expr.name not in call_names
                and expr.coord):
            out.append((expr.coord.line, expr.name, id(expr)))
        return
    for _name, ch in expr.children():
        _collect_reads(ch, local_names, call_names, out)


def _ast_symbol_labels(fn: str, path: str, node) -> dict:
    """Per-(source-line, symbol) ground truth for one FuncDef.

    Returns ``{(line, symbol): "REAL"|"INLINE"}``.  A global memory read is
    REAL **only** when it is the complete (cast-stripped) right-hand side of a
    SCALAR-local assignment / decl-init (`x = global[...]`); every other global
    read -- an operand (`x = a + global`), a call argument (`x = f(global)`),
    an array INDEX (`a[global]`), a condition / return / compound-assign, or a
    store to a non-scalar lvalue -- is INLINE.  This is PER-SYMBOL, not
    per-line: the old line-granularity labelling marked an entire line REAL
    whenever *any* local was assigned on it, which mislabels operand /
    call-arg / index reads and made the validation untrustworthy (it reported
    a fictitious 94% REAL / 95% INLINE; the truth is ~75% / ~99%)."""
    import pycparser.c_ast as c

    local_names: set = set()
    decl = node.decl
    try:
        for p in (decl.type.args.params if decl.type.args else []):
            if getattr(p, "name", None):
                local_names.add(p.name)
    except AttributeError:
        pass

    class _DeclV(c.NodeVisitor):
        def visit_Decl(self, d):
            if d.name:
                local_names.add(d.name)
            self.generic_visit(d)
    _DeclV().visit(node.body)

    call_names: set = set()

    class _CallV(c.NodeVisitor):
        def visit_FuncCall(self, fc):
            if isinstance(fc.name, c.ID):
                call_names.add(fc.name.name)
            self.generic_visit(fc)
    _CallV().visit(node.body)

    real_ids: set = set()

    def _maybe_real(lval, rval):
        if isinstance(lval, c.ID) and lval.name in local_names:
            r = _strip_cast(rval)
            if _is_mem_read_node(r) and _read_base_symbol(r, local_names, call_names):
                real_ids.add(id(r))

    class _RealV(c.NodeVisitor):
        def visit_Assignment(self, a):
            if a.op == "=":
                _maybe_real(a.lvalue, a.rvalue)
            self.generic_visit(a)

        def visit_Decl(self, d):
            if d.name and d.name in local_names and d.init is not None:
                r = _strip_cast(d.init)
                if _is_mem_read_node(r) and _read_base_symbol(r, local_names, call_names):
                    real_ids.add(id(r))
            self.generic_visit(d)
    _RealV().visit(node.body)

    reads: list = []
    _collect_reads(node.body, local_names, call_names, reads)
    real_pairs: set = set()
    inline_pairs: set = set()
    for line, base, nid in reads:
        (real_pairs if nid in real_ids else inline_pairs).add((line, base))
    mixed = real_pairs & inline_pairs
    labels: dict = {}
    for pr in real_pairs - mixed:
        labels[pr] = "REAL"
    for pr in inline_pairs - mixed:
        labels[pr] = "INLINE"
    return labels


def _source_index():
    from c2.commands.style_check import _source_index as si
    return si()


def validate(json_out: bool = False, limit: int = 0) -> None:
    """Score the detector against the byte-exact corpus."""
    if not SIDECAR_PATH.exists():
        console.print("[red]no sidecar — run a full `c2 decomp-verify` first "
                      "(writes .c2-cache/exact-line-map.json)[/red]")
        raise SystemExit(1)
    sidecar = json.loads(SIDECAR_PATH.read_text())
    index = _source_index()

    stats = {
        "A": {"tp": 0, "fp": 0}, "B": {"tp": 0, "fp": 0},
        "C": {"tp": 0, "fp": 0},
        "REAL": {"tp": 0, "fp": 0}, "INLINE": {"tp": 0, "fp": 0},
    }
    n_fn = n_sites = n_scored = 0
    fp_examples: list[tuple[str, str, str, int, str]] = []

    names = sorted(sidecar)
    if limit:
        names = names[:limit]
    for fn in names:
        if fn not in index:
            continue
        _path, node, _start = index[fn]
        try:
            sym_labels = _ast_symbol_labels(fn, _path, node)
        except Exception:
            continue
        try:
            sites = analyze(fn)
        except Exception:
            continue
        starts = {int(k): v for k, v in sidecar[fn]["starts"].items()}
        if not starts:
            continue
        n_fn += 1
        # build off -> OUR line (inheritance over statement starts)
        offs = sorted(starts)

        def our_line(off: int) -> int | None:
            lo = None
            for o in offs:
                if o <= off:
                    lo = o
                else:
                    break
            return starts.get(lo) if lo is not None else None

        for s in sites:
            n_sites += 1
            v = s.verdict
            if v is None:
                continue
            ln = our_line(s.off)
            sym = _key_symbol(s.key)
            if ln is None or sym is None:
                continue
            # PER-SYMBOL ground truth: match the specific global this load
            # touches, not merely the source line (a single line mixes a
            # local-assign with operand/call-arg/index reads).
            truth = sym_labels.get((ln, sym))
            if truth is None:
                continue
            n_scored += 1
            ok = (v == truth)
            for sig in s.verdicts:
                if (sig in ("A", "B") and v == "REAL") or (sig == "C" and v == "INLINE"):
                    stats[sig]["tp" if ok else "fp"] += 1
            stats[v]["tp" if ok else "fp"] += 1
            if not ok and len(fp_examples) < 25:
                fp_examples.append((fn, v, "+".join(s.verdicts), s.off, s.key))

    if json_out:
        print(json.dumps({"functions": n_fn, "sites": n_sites,
                          "scored": n_scored, "stats": stats}))
        return

    t = Table(title=f"local-hints validation — {n_fn} byte-exact fns, "
                    f"{n_scored} scored predictions ({n_sites} load sites)")
    t.add_column("signal")
    t.add_column("predicts")
    t.add_column("correct", justify="right")
    t.add_column("wrong", justify="right")
    t.add_column("precision", justify="right")
    for sig, what in (("A", "REAL"), ("B", "REAL"), ("C", "INLINE"),
                      ("REAL", "—"), ("INLINE", "—")):
        st = stats[sig]
        tot = st["tp"] + st["fp"]
        prec = f"{100.0 * st['tp'] / tot:.1f}%" if tot else "n/a"
        t.add_row(sig, what, str(st["tp"]), str(st["fp"]), prec)
    console.print(t)
    if fp_examples:
        console.print("\n[dim]sample mispredictions:[/dim]")
        for fn, v, sigs, off, key in fp_examples[:12]:
            console.print(f"  {fn} +0x{off:X} {key}  predicted {v} ({sigs})")


def _assigned_globals(node, local_names: set, call_names: set) -> set:
    """Global symbols WRITTEN in the function body (lvalue base is a global).

    A genuine invented cache caches a READ-ONLY global; a global the source
    also assigns is a mutable cursor / state variable, and a local copied from
    it is almost always a load-bearing SAVE/RESTORE across a call
    (`saved = g; clobber(); g = saved;`), not a redundant cache.  Excluding
    these from the DE-INVENT direction removes that false-positive class
    (e.g. take_census's `cm_sptr`)."""
    import pycparser.c_ast as c
    out: set = set()

    class _V(c.NodeVisitor):
        def _mark(self, lval):
            base = _read_base_symbol(lval, local_names, call_names)
            if base is not None:
                out.add(base)

        def visit_Assignment(self, a):
            self._mark(a.lvalue)
            self.generic_visit(a)

        def visit_UnaryOp(self, u):
            if u.op in ("p++", "p--", "++", "--"):
                self._mark(u.expr)
            self.generic_visit(u)
    _V().visit(node.body)
    return out


def _inline_cmp_read_syms(fn: str) -> set:
    """Globals read INLINE via a direct memory operand in a compare/test
    (`cmp [placing_type], K`) -- the in-place dispatch form the LOAD-only
    `analyze` scanner is BLIND to (it tracks only `mov reg,[mem]`).  A global
    read this way is genuinely read in place; naming a local for it would force
    `mov reg,[g]; cmp reg,K` and DIVERGE.  Used to guard the ADD-LOCAL
    direction against the cmp-inline-read FP class (build_city_item/
    placing_type: 40+ `cmp [mem]` dispatch reads, only 2 stray `mov`-for-
    arithmetic loads the scanner mislabels REAL)."""
    from c2.commands.disasm import disasm_function
    try:
        _a, _s, lines = disasm_function(fn)
    except Exception:
        return set()
    out: set = set()
    for ln in lines:
        if not ln.data_ref:
            continue
        if ln.mnemonic in ("cmp", "test") and \
                any(_mem_operand(op) for op in _split_ops(ln.op_str)):
            sym = ln.data_ref.split("+")[0].split("-")[0].strip()
            if sym:
                out.add(sym)
    return out


def _disagreements(fn: str, sites: list | None = None):
    """Cross-check the PS-scanner verdict (ground truth) against our RECOVERED
    source's local structure, per global symbol.  Returns
    ``{"deinvent": [...], "addlocal": [...], "ps_inline_count": {...}}`` or
    None when the source isn't indexed.  ``sites`` may be a pre-computed
    ``analyze(fn)`` result (avoids a second disasm pass when the caller
    already has it).

    * DE-INVENT: PS reads the global INLINE everywhere it commits, but our
      source caches it in a scalar local -> delete the invented local and read
      the global directly (Rule 129 / §10).  The highest-leverage direction.
    * ADD-LOCAL: PS names a scalar local from the global, but our source reads
      it inline everywhere -> introduce ``T v = global;`` (the de-invent
      inverse).
    """
    index = _source_index()
    if fn not in index:
        return None
    path, node, _start = index[fn]
    try:
        sym_labels = _ast_symbol_labels(fn, path, node)
    except Exception:
        return None
    srcv: dict = {}
    for (_ln, sym), lab in sym_labels.items():
        srcv.setdefault(sym, set()).add(lab)
    # globals the source ASSIGNS are mutable cursors -> a local copied
    # from them is a save/restore, not an invented cache (see
    # _assigned_globals).
    _local_names: set = set()
    _decl = node.decl
    try:
        for _p in (_decl.type.args.params if _decl.type.args else []):
            if getattr(_p, 'name', None):
                _local_names.add(_p.name)
    except AttributeError:
        pass
    import pycparser.c_ast as _ca
    class _LN(_ca.NodeVisitor):
        def visit_Decl(self, d):
            if d.name:
                _local_names.add(d.name)
            self.generic_visit(d)
    _LN().visit(node.body)
    _call_names: set = set()
    class _CN(_ca.NodeVisitor):
        def visit_FuncCall(self, fc):
            if isinstance(fc.name, _ca.ID):
                _call_names.add(fc.name.name)
            self.generic_visit(fc)
    _CN().visit(node.body)
    assigned = _assigned_globals(node, _local_names, _call_names)
    cmp_inline_reads = _inline_cmp_read_syms(fn)
    psv: dict = {}
    ps_inline: dict = {}
    held_across_call: set = set()   # symbols with the 'b' (hold-across-call)
                                    # signal -- REAL-local evidence the verdict
                                    # logic demotes to advisory
    genuine_inline: set = set()     # symbols with a CALL-FREE reload -- the
                                    # only proof PS reads them inline rather
                                    # than caching per region (best_elastic_dirc:
                                    # PS holds it in ECX across the whole
                                    # if/else chain -> a real `dirc` local, the
                                    # 2 "inline reads" are the 2 loop phases)
    if sites is None:
        try:
            sites = analyze(fn)
        except Exception:
            return None
    for s in sites:
        sym = _key_symbol(s.key)
        if not sym:
            continue
        if "b" in s.verdicts:
            held_across_call.add(sym)
        if s.c_call_free:
            genuine_inline.add(sym)
        if not s.verdict:
            continue
        psv.setdefault(sym, set()).add(s.verdict)
        if s.verdict == "INLINE":
            ps_inline[sym] = ps_inline.get(sym, 0) + 1
    deinvent: list = []
    addlocal: list = []
    for sym, pv in psv.items():
        sv = srcv.get(sym, set())
        # DE-INVENT guards (each kills a measured byte-exact-corpus FP class):
        #  * sv == {"REAL"} EXCLUSIVELY -- the source must cache the global
        #    and NEVER also read it inline.  A source that MIXES cache+inline
        #    (sv == {REAL, INLINE}) is the deliberate Rule-116 reload pattern
        #    PS itself uses (`r = region_over; f(); ... empire_won[region_over]`)
        #    -- deleting the cache there is wrong (this_region_box,
        #    continue_smacking, battle_stats_nof_units were all REAL+INLINE).
        #  * sym not in held_across_call -- a global PS holds across a call
        #    (signal 'b') is backed by a real callee-save local (the verdict
        #    demotes 'b' to advisory); deleting it REGRESSED 350->441b.
        #  * sym not in assigned -- a mutable cursor; a copy is a save/restore.
        #  * sym in genuine_inline -- a CALL-FREE reload proves PS actually
        #    re-reads the global rather than caching it in a register per
        #    region.  Without it the "INLINE" verdict is only forced post-call
        #    reloads of a value the source legitimately cached (best_elastic_dirc
        #    held in ECX across the if/else chain; new_province/c2inf field).
        if (pv == {"INLINE"} and sv == {"REAL"} and sym not in assigned
                and sym not in held_across_call and sym in genuine_inline):
            deinvent.append(sym)
        # ADD-LOCAL: REQUIRE signal 'b' (held across a call) -- the symmetric
        # partner of the de-invent guard.  Signal A alone (a load-only -d1
        # run) is the weaker 94% REAL signal and produces the add-local FP
        # class (player_rank, army_a, current_palette: byte-exact functions
        # whose source reads the global inline, signal A misfiring on an
        # array-element store or an indexed read).  A value PS genuinely made
        # a named local is the one it HOLDS across a call in a callee-save.
        # ALSO exclude globals read via `cmp/test [mem]` somewhere -- PS reads
        # those in place (build_city_item/placing_type: the LOAD scanner only
        # saw 2 arithmetic loads, was blind to the 40+ cmp-dispatch reads).
        elif (pv == {"REAL"} and sv == {"INLINE"}
                and sym in held_across_call
                and sym not in cmp_inline_reads):
            addlocal.append(sym)
    return {"deinvent": sorted(deinvent), "addlocal": sorted(addlocal),
            "ps_inline_count": ps_inline}


def tool_summary(fn: str) -> dict:
    """Compact summary for the `c2 diagnose` / `c2 dossier`
    integration.  NEVER raises.

    Combines the per-load REAL/INLINE classification counts with the
    actionable PS-vs-recovered-source cross-check (DE-INVENT = delete an
    invented caching local, ADD-LOCAL = introduce ``T v = global;``) -- the
    highest-leverage source-shape lever from the Fable-5 corpus runs
    (get_morale_and_readiness 162->0, slider_control 156->3 all hinged on
    de-inventing).  ``available`` is False when the PS function can't be
    disassembled; ``in_source`` is False when it isn't in the recovered
    source index (then deinvent/addlocal are empty).
    """
    out = {
        "available": False, "in_source": False,
        "n_real": 0, "n_inline": 0, "n_abstain": 0,
        "deinvent": [], "addlocal": [], "ps_inline_count": {},
        "real_sites": [], "n_reg_locals": 0,
    }
    try:
        sites = analyze(fn)
    except Exception:
        return out
    out["available"] = True
    try:
        out["n_reg_locals"] = len(statement_locals(fn))
    except Exception:
        out["n_reg_locals"] = 0
    for s in sites:
        v = s.verdict
        if v == "REAL":
            out["n_real"] += 1
            out["real_sites"].append(
                {"off": s.off, "line": s.line, "reg": s.reg, "key": s.key})
        elif v == "INLINE":
            out["n_inline"] += 1
        else:
            out["n_abstain"] += 1
    try:
        dis = _disagreements(fn, sites=sites)
    except Exception:
        dis = None
    if dis is not None:
        out["in_source"] = True
        out["deinvent"] = dis.get("deinvent", [])
        out["addlocal"] = dis.get("addlocal", [])
        out["ps_inline_count"] = dis.get("ps_inline_count", {})
    return out


def _print_vs_source(fn: str, dis: dict) -> None:
    n = len(dis["deinvent"]) + len(dis["addlocal"])
    if n == 0:
        console.print(f"[green]{fn}: PS-scanner agrees with the recovered "
                      "source (no de-invent / add-local lever).[/green]")
        return
    console.print(f"[bold]{fn}[/bold]: {n} PS-vs-source local mismatch(es)")
    if dis["deinvent"]:
        console.print("  [yellow]DE-INVENT[/yellow] (PS reads INLINE, source "
                      "caches a local -> delete the local, read the global "
                      "directly; Rule 129 / §10):")
        for sym in dis["deinvent"]:
            n_in = dis["ps_inline_count"].get(sym, 0)
            console.print(f"      {sym}  (PS reads inline {n_in}x)")
    if dis["addlocal"]:
        console.print("  [cyan]ADD-LOCAL[/cyan] (PS names a local, source "
                      "reads inline -> introduce `T v = global;`):")
        for sym in dis["addlocal"]:
            console.print(f"      {sym}")


def local_hints(
    function: Annotated[str, typer.Argument(help="Function name (omit with --validate / --corpus)")] = "",
    validate_corpus: Annotated[bool, typer.Option("--validate", help="Score the detector against the byte-exact corpus (needs a prior full decomp-verify run for the .c2-cache/exact-line-map.json sidecar)")] = False,
    vs_source: Annotated[bool, typer.Option("--vs-source", help="Cross-check the PS-scanner verdict against the RECOVERED source: surface DE-INVENT (delete an invented caching local) and ADD-LOCAL opportunities")] = False,
    corpus: Annotated[bool, typer.Option("--corpus", help="With --vs-source: rank every diffing function by its PS-vs-source local mismatches (the de-invent / add-local frontier)")] = False,
    statements: Annotated[bool, typer.Option("--statements", help="ADVISORY (~92%): also list -d1 STATEMENTS that produce a REGISTER-rooted named local (t=a+b, x=f(), p=q) -- the class the load REAL/INLINE verdicts can't see")] = False,
    json_out: Annotated[bool, typer.Option("--json", help="Machine-readable output")] = False,
    limit: Annotated[int, typer.Option("--limit", help="Validate/corpus: at most N functions (0 = all)")] = 0,
) -> None:
    """Classify a PS function's memory loads as REAL locals vs INLINE reads."""
    if validate_corpus:
        validate(json_out=json_out, limit=limit)
        return
    if vs_source and corpus:
        _vs_source_corpus(json_out=json_out, limit=limit)
        return
    if not function:
        console.print("[red]give a function name, or --validate / --corpus --vs-source[/red]")
        raise SystemExit(2)
    if vs_source:
        dis = _disagreements(function)
        if dis is None:
            console.print(f"[red]{function}: not found in the recovered source index[/red]")
            raise SystemExit(1)
        if json_out:
            print(json.dumps({"function": function, **dis}))
            return
        _print_vs_source(function, dis)
        return
    sites = analyze(function)
    if statements:
        rows = statement_locals(function)
        if json_out:
            print(json.dumps(rows))
            return
        rt = Table(title=f"register-rooted named locals (ADVISORY ~92%): {function}")
        rt.add_column("off")
        rt.add_column("PS line", justify="right")
        rt.add_column("reg")
        for r in rows:
            rt.add_row(f"+0x{r['off']:X}", str(r["line"]), r["reg"])
        console.print(rt)
        console.print(f"[dim]{len(rows)} statement(s) produce a register-rooted "
                      "named local the load signals cannot see (t=a+b / x=f() / "
                      "p=q).  Advisory: ~92% precision, ~19% recall.[/dim]")
        return
    if json_out:
        print(json.dumps([{
            "off": s.off, "line": s.line, "reg": s.reg, "key": s.key,
            "signals": s.verdicts, "verdict": s.verdict,
        } for s in sites]))
        return
    t = Table(title=f"local-hints: {function}")
    t.add_column("off")
    t.add_column("PS line", justify="right")
    t.add_column("reg")
    t.add_column("key")
    t.add_column("signals")
    t.add_column("verdict")
    for s in sites:
        v = s.verdict or "—"
        style = {"REAL": "green", "INLINE": "yellow"}.get(v, "dim")
        t.add_row(f"+0x{s.off:X}", str(s.line), s.reg, s.key,
                  "+".join(s.verdicts) or "—", f"[{style}]{v}[/{style}]")
    console.print(t)
    n_real = sum(1 for s in sites if s.verdict == "REAL")
    n_inl = sum(1 for s in sites if s.verdict == "INLINE")
    console.print(f"[dim]{len(sites)} load sites: {n_real} REAL, "
                  f"{n_inl} INLINE, {len(sites) - n_real - n_inl} abstain[/dim]")


def _vs_source_corpus(json_out: bool = False, limit: int = 0) -> None:
    """Rank every diffing function by its PS-vs-source local mismatches -- the
    de-invent / add-local frontier (the now-accurate scanner driving the
    source-shape effort)."""
    from c2.commands.verify_json import get_verify_json
    try:
        doc = get_verify_json(no_build=True)
    except FileNotFoundError:
        console.print("[red]no .c2-cache/verify.json -- run `c2 decomp-verify "
                      "--json` once[/red]")
        raise SystemExit(1)
    diffing = [f["name"] for f in doc.get("functions", [])
               if f.get("diff_byte_count", 0) > 0]
    rows = []
    for fn in diffing:
        dis = _disagreements(fn)
        if not dis:
            continue
        nd, na = len(dis["deinvent"]), len(dis["addlocal"])
        if nd + na == 0:
            continue
        rows.append((fn, nd, na, dis))
    rows.sort(key=lambda r: (r[1] + r[2], r[1]), reverse=True)
    if limit:
        rows = rows[:limit]
    if json_out:
        print(json.dumps([{"function": fn, "deinvent": d["deinvent"],
                           "addlocal": d["addlocal"]} for fn, _, _, d in rows]))
        return
    console.print(f"\n[bold]local-hints frontier[/bold]: {len(rows)} diffing "
                  "function(s) where the PS scanner disagrees with the "
                  "recovered source's local structure")
    console.print("  (de-invent = delete an invented caching local; add-local "
                  "= introduce `T v = global;`)\n")
    for fn, nd, na, dis in rows:
        tags = []
        if nd:
            tags.append(f"deinvent={nd}")
        if na:
            tags.append(f"add={na}")
        syms = ", ".join(dis["deinvent"] + ["+" + s for s in dis["addlocal"]])
        console.print(f"  {fn:34} {'  '.join(tags):20} {syms[:50]}")
    console.print("\n  drill in: c2 local-hints <fn> --vs-source")
