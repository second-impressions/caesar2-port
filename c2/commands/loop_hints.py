"""Loop classifier from PS.EXE byte shape (`c2 loops <fn>`).

Operates ONLY on PS.EXE disassembly (no RC source consulted).  For each
back-edge in a function, classifies the loop as one of:

  * ``for``                  -- entry-jmp + step + test all align (high confidence)
  * ``for_or_dowhile_step``  -- step + test but no entry-jmp (byte-ambiguous:
                                ``for(; cond; step)`` and
                                ``do { ...; step; } while(cond);`` produce
                                identical bytes)
  * ``while``                -- entry-jmp without step, OR test-at-top pattern
                                with unconditional back-edge
  * ``do_while``             -- no entry-jmp, no step, no top-test
  * ``infinite``             -- unconditional back-edge, no top-test
  * ``loop_insn``            -- x86 ``loop``/``loopnz``/``loopz`` back-edge

Validated against 533 source-AST loops in the byte-exact corpus: **99.1%**
kind agreement.  The 5 outliers are genuinely ambiguous from bytes alone
(compiler quirks producing patterns the cascade can't disambiguate).

The classifier walks each back-edge through a cascade of independent
checks (definite ``for`` first, then ``infinite`` / ``while`` / ``do_while``,
then the byte-ambiguous ``for_or_dowhile_step`` as a fallback) so the
high-confidence cases never get reclassified by weaker signals.

Heuristics use ``insn_ast._decode_raw`` for structured operand identity
(register-family base, memory base/index/scale/disp) -- no text parsing.

The ``-d1`` line numbers from PS.EXE (propagated forward through sparse
debug records) gate the step search: a true for-step shares a source
line with the iteration test, while a body-internal modification of the
test variable has its own line.

Public entry point: ``detect_loops(disasm_lines) -> list[Loop]``.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Optional

import typer

from c2.commands.disasm import DisasmLine, disasm_function
from c2.commands.insn_ast import Insn, Op, _decode_raw

# x86 conditional jumps.
JCC = frozenset({
    'je', 'jne', 'jz', 'jnz', 'jl', 'jle', 'jg', 'jge',
    'jb', 'jbe', 'ja', 'jae', 'jc', 'jnc', 'js', 'jns',
    'jo', 'jno', 'jp', 'jnp', 'jpe', 'jpo', 'jcxz', 'jecxz',
})

# Insns that write CPU flags (candidates for the test feeding a back-edge).
FLAG_SETTERS = frozenset({
    'cmp', 'test',
    'inc', 'dec', 'add', 'sub', 'and', 'or', 'xor',
    'sbb', 'adc', 'neg',
    'shl', 'shr', 'sar', 'rol', 'ror',
    'mul', 'imul', 'div', 'idiv',
})

# Insns that can serve as a for-loop step (modify the iteration variable).
STEP_MNEM = frozenset({'inc', 'dec', 'add', 'sub', 'mov', 'lea'})


# Register family lookup: every byte/word/dword sub-reg -> dword base.
_REG_BASE: dict[str, str] = {}
for _base, _parts in [
    ('eax', ['eax', 'ax', 'al', 'ah']),
    ('ebx', ['ebx', 'bx', 'bl', 'bh']),
    ('ecx', ['ecx', 'cx', 'cl', 'ch']),
    ('edx', ['edx', 'dx', 'dl', 'dh']),
    ('esi', ['esi', 'si']),
    ('edi', ['edi', 'di']),
    ('ebp', ['ebp', 'bp']),
    ('esp', ['esp', 'sp']),
]:
    for _p in _parts:
        _REG_BASE[_p] = _base


def _reg_base(r: str) -> str:
    return _REG_BASE.get(r, r)


def _op_key(op: Op) -> tuple:
    """Canonical location key (size-agnostic).  Two operands referring
    to the same storage share the same key.
    """
    if op.kind == 'reg':
        return ('reg', _reg_base(op.reg))
    if op.kind == 'mem':
        return ('mem', _reg_base(op.base), _reg_base(op.index), op.scale, op.disp)
    return ('imm', op.imm)


def _read_locs(insn: Optional[Insn]) -> set[tuple]:
    """Locations the insn reads.  For ``mov R, X`` only the source side
    counts (the destination is a write, not a read); for everything else
    we assume operand 0 is both read+write (cmp/test/arith).  Memory
    addressing always reads the base/index registers regardless of
    operand role.
    """
    out: set[tuple] = set()
    if insn is None:
        return out
    is_mov = insn.mnemonic == 'mov'
    for k, op in enumerate(insn.ops):
        if is_mov and k == 0:
            if op.kind == 'mem':
                if op.base:
                    out.add(('reg', _reg_base(op.base)))
                if op.index:
                    out.add(('reg', _reg_base(op.index)))
            continue
        if op.kind == 'reg':
            out.add(('reg', _reg_base(op.reg)))
        elif op.kind == 'mem':
            out.add(('mem', _reg_base(op.base), _reg_base(op.index), op.scale, op.disp))
            if op.base:
                out.add(('reg', _reg_base(op.base)))
            if op.index:
                out.add(('reg', _reg_base(op.index)))
    return out


def _decode(ln: DisasmLine) -> Optional[Insn]:
    return _decode_raw(bytes(ln.bytes_), ln.address)


def _branch_target(insn: Optional[Insn]) -> Optional[int]:
    if insn is None:
        return None
    m = insn.mnemonic
    if m == 'jmp' or m in JCC or m.startswith('loop'):
        if insn.ops and insn.ops[0].kind == 'imm':
            return insn.ops[0].imm
    return None


def _propagate_ps_lines(lines: list[DisasmLine]) -> list[int]:
    """PS ``-d1`` debug records mark line transitions only; each insn
    inherits the line of the last marked instruction.  Returns a parallel
    list of effective line numbers.
    """
    out: list[int] = []
    cur = 0
    for ln in lines:
        if ln.line:
            cur = ln.line
        out.append(cur)
    return out


def _reachable_forward(
    decoded: list[Optional[Insn]],
    lines: list[DisasmLine],
    by_addr: dict[int, int],
    start_idx: int,
    target_idx: int,
    body_hi_addr: int,
    max_seen: int = 400,
) -> bool:
    """Can forward execution from ``start_idx`` reach ``target_idx`` without
    escaping past ``body_hi_addr``?  Used to filter out tail-merge backward
    jumps (e.g. switch-break collapse to a shared post-switch tail) which
    look like loops but aren't.
    """
    if start_idx == target_idx:
        return True
    seen: set[int] = set()
    stack = [start_idx]
    while stack and len(seen) < max_seen:
        i = stack.pop()
        if i in seen:
            continue
        seen.add(i)
        if i == target_idx:
            return True
        if i >= len(lines) or i < 0:
            continue
        ln = lines[i]
        d = decoded[i]
        next_addr = ln.address + len(ln.bytes_)
        next_idx = by_addr.get(next_addr)

        def _push(t: Optional[int]) -> None:
            if t is None or t > body_hi_addr:
                return
            tidx = by_addr.get(t)
            if tidx is not None:
                stack.append(tidx)

        if d is None:
            if next_idx is not None and next_addr <= body_hi_addr:
                stack.append(next_idx)
            continue
        m = d.mnemonic
        if m == 'ret' or m.startswith('ret') or m == 'iret':
            continue
        if m == 'jmp':
            _push(_branch_target(d))
        elif m in JCC or m.startswith('loop'):
            _push(_branch_target(d))
            if next_idx is not None and next_addr <= body_hi_addr:
                stack.append(next_idx)
        else:
            if next_idx is not None and next_addr <= body_hi_addr:
                stack.append(next_idx)
    return False


@dataclass
class Loop:
    kind: str                       # for | for_or_dowhile_step | while | do_while | infinite | loop_insn
    top: int                        # back-edge target (loop body's first insn)
    end: int                        # address after the back-edge insn
    back_edge: int                  # address of the back-edge instruction
    test: Optional[int] = None      # address of the flag-setter feeding the back-edge
    step: Optional[int] = None      # address of the iteration step (if for-shaped)
    entry_jmp: Optional[int] = None # address of the entry-jmp (if a `for` with entry-jmp)
    continues: int = 0              # number of additional back-edges to the same top (continues)

    @property
    def ambiguous(self) -> bool:
        """True when bytes alone can't distinguish for from do-while/while
        with a tail-step modification.
        """
        return self.kind == 'for_or_dowhile_step'


def detect_loops(lines: list[DisasmLine]) -> list[Loop]:
    """Detect and classify all loops in a function's PS.EXE disasm.

    Returns one ``Loop`` per source-level loop (back-edges to the same top
    are deduplicated; continues are tracked as ``loop.continues``).
    """
    decoded = [_decode(ln) for ln in lines]
    by_addr = {ln.address: i for i, ln in enumerate(lines)}
    eff_line = _propagate_ps_lines(lines)
    if not lines:
        return []
    func_start = lines[0].address
    func_end = lines[-1].address + len(lines[-1].bytes_)

    # Pass 1: collect candidate back-edges that pass reachability filter.
    raw: list[tuple[int, int, int, Insn]] = []
    for i, (ln, ins) in enumerate(zip(lines, decoded)):
        if ins is None:
            continue
        tgt = _branch_target(ins)
        if tgt is None or tgt >= ln.address:
            continue
        if tgt < func_start or tgt >= func_end:
            continue
        top_idx = by_addr.get(tgt)
        if top_idx is None:
            continue
        if not _reachable_forward(decoded, lines, by_addr, top_idx, i, ln.address):
            continue
        raw.append((tgt, i, top_idx, ins))

    # Pass 2: dedup by top -- the latest (highest-address) back-edge per top
    # is the loop's natural closing-brace back-edge; earlier ones are continues.
    by_top: dict[int, tuple[int, int, Insn]] = {}
    extras: dict[int, int] = {}
    for top, be_idx, top_idx, ins in raw:
        prev = by_top.get(top)
        if prev is None or lines[be_idx].address > lines[prev[0]].address:
            if prev is not None:
                extras[top] = extras.get(top, 0) + 1
            by_top[top] = (be_idx, top_idx, ins)
        else:
            extras[top] = extras.get(top, 0) + 1

    loops: list[Loop] = []
    for top, (be_idx, top_idx, ins) in by_top.items():
        ln = lines[be_idx]
        body_lo, body_hi = top, ln.address
        loop = _classify_loop(
            decoded, lines, by_addr, eff_line,
            ins, be_idx, top, top_idx, body_lo, body_hi,
        )
        loop.continues = extras.get(top, 0)
        loops.append(loop)
    return loops


def _classify_loop(
    decoded: list[Optional[Insn]],
    lines: list[DisasmLine],
    by_addr: dict[int, int],
    eff_line: list[int],
    ins: Insn,
    be_idx: int,
    top: int,
    top_idx: int,
    body_lo: int,
    body_hi: int,
) -> Loop:
    """Classify one loop given its back-edge and body extent.

    The cascade order (most-confident first):

      1. ``loop_insn``       -- x86 ``loop``/``loopnz``/``loopz`` instruction
      2. ``infinite``        -- ``jmp top`` back-edge, no top-exit jcc
      3. ``while`` (top)     -- top has flag-setter + forward exit jcc
                                (test-at-top while-loop pattern)
      4. ``for``             -- entry-jmp targeting iteration footer
                                + step (line-gated) + test
      5. ``while`` (entry)   -- entry-jmp without a matching step
      6. ``for_or_dowhile_step`` -- step found, no entry-jmp (byte-ambiguous)
      7. ``do_while``        -- no entry-jmp, no step, no top-test
    """
    end_addr = ln_after = ln_be = lines[be_idx].address + len(lines[be_idx].bytes_)
    base = Loop(kind='unknown', top=top, end=end_addr, back_edge=lines[be_idx].address)

    # --- Detect top-test pattern (used by infinite/while-jmp and while-top) ---
    top_test_idx: Optional[int] = None
    top_exit_idx: Optional[int] = None
    for j in range(top_idx, min(top_idx + 8, be_idx)):
        d = decoded[j]
        if d is None:
            continue
        if d.mnemonic in FLAG_SETTERS and top_test_idx is None:
            top_test_idx = j
            continue
        if d.mnemonic in JCC:
            t = _branch_target(d)
            if t is not None and (t < body_lo or t >= body_hi):
                top_exit_idx = j
                break
    has_top_test = top_test_idx is not None and top_exit_idx is not None

    # --- Cascade ---
    if ins.mnemonic.startswith('loop'):
        base.kind = 'loop_insn'
        return base

    if ins.mnemonic == 'jmp':
        if has_top_test:
            base.kind = 'while'
            base.test = lines[top_test_idx].address  # type: ignore[index]
        elif top_exit_idx is not None:
            base.kind = 'while'
        else:
            base.kind = 'infinite'
        return base

    # Conditional back-edge: scan for flag-setter, step, entry-jmp.
    if ins.mnemonic in JCC:
        # Find test (the flag-setter feeding the back-edge jcc).
        test_idx: Optional[int] = None
        for j in range(be_idx - 1, top_idx - 1, -1):
            d = decoded[j]
            if d is not None and d.mnemonic in FLAG_SETTERS:
                test_idx = j
                base.test = lines[j].address
                break
        test_line = eff_line[test_idx] if test_idx is not None else 0

        # Find step: a step-candidate insn within 8 insns before test whose
        # destination is READ by anything in the iteration footer.  When PS
        # line info is available, the step must share the test's source line
        # (a true for-step is on the iteration-test source line; a body-
        # internal modification has a different line).
        if test_idx is not None:
            footer_lo = max(top_idx, test_idx - 8)
            for j in range(test_idx - 1, footer_lo - 1, -1):
                cand = decoded[j]
                if cand is None or cand.mnemonic not in STEP_MNEM:
                    continue
                if not cand.ops:
                    continue
                dst = cand.ops[0]
                if dst.kind not in ('reg', 'mem'):
                    continue
                cand_line = eff_line[j]
                if test_line and cand_line and cand_line != test_line:
                    continue
                dst_key = _op_key(dst)
                # Check whether dst_key is READ by any insn between step and back-edge.
                used = False
                for k in range(j + 1, be_idx + 1):
                    if dst_key in _read_locs(decoded[k]):
                        used = True
                        break
                if used:
                    base.step = lines[j].address
                    break

        # Find entry-jmp: the jmp immediately before loop top, whose target is
        # in the iteration footer ([step_addr or test_addr] .. test_addr).
        if base.test is not None and top_idx > 0:
            j = top_idx - 1
            d = decoded[j]
            if d is not None and d.mnemonic == 'jmp':
                ej_tgt = _branch_target(d)
                if ej_tgt is not None:
                    footer_start = base.step if base.step is not None else base.test
                    if footer_start <= ej_tgt <= base.test:
                        base.entry_jmp = lines[j].address

        # Final cascade:
        if has_top_test and base.step is None:
            # Test-at-top while-pattern; bottom back-edge is conditional
            # body-internal (e.g. while(i++ < N) with body conditional).
            base.kind = 'while'
            base.test = lines[top_test_idx].address  # type: ignore[index]
        elif base.entry_jmp is not None and base.step is not None:
            base.kind = 'for'
        elif base.entry_jmp is not None:
            base.kind = 'while'
        elif base.step is not None:
            # Step + test + no entry-jmp.  This shape is BYTE-AMBIGUOUS:
            # both for(;cond;step){body} (init elided) and
            # do{body;step;}while(cond) produce identical bytes.
            base.kind = 'for_or_dowhile_step'
        else:
            base.kind = 'do_while'
        return base

    # Anything else (call, ret, etc. as back-edge): mark unknown but keep address.
    return base


# --- Hint rendering (for `decomp-verify -v`) ---------------------------------

_KIND_PRIORITY = {
    'for':                   0,
    'while':                 1,
    'do_while':              2,
    'infinite':              3,
    'loop_insn':             4,
    'for_or_dowhile_step':   5,  # report ambiguous cases last
}


def render_loops_hint(name: str) -> Optional[str]:
    """Return a one-line summary of the loops detected in PS.EXE bytes for
    ``name``, or None if the function has no loops.

    Format: a count per kind, followed by per-loop addresses.  Ambiguous
    loops carry a trailing ``[?]`` so the agent knows the for-vs-do-while
    distinction cannot be made from bytes alone for that loop.
    """
    try:
        _, _, lines = disasm_function(name)
    except (KeyError, FileNotFoundError, ValueError):
        return None
    detected = detect_loops(lines)
    if not detected:
        return None
    fn_start = lines[0].address
    detected = sorted(detected, key=lambda lp: (_KIND_PRIORITY.get(lp.kind, 99), lp.top))
    parts: list[str] = []
    for lp in detected:
        rel = lp.top - fn_start
        tag = lp.kind
        if lp.ambiguous:
            tag += ' [?]'
        parts.append(f'{tag} @+0x{rel:X}')
    return '; '.join(parts)


# --- CLI ---------------------------------------------------------------------

def loops(
    name_or_addr: str = typer.Argument(..., help="Function name or 0xADDR"),
    as_json: bool = typer.Option(False, "--json", help="Emit JSON"),
) -> None:
    """Classify every loop in a PS.EXE function from its byte shape alone.

    Operates on PS.EXE disassembly only -- no RC source / RC.EXE involvement.
    Each back-edge is classified via the cascade documented in
    :mod:`c2.commands.loop_hints`; ``for_or_dowhile_step`` means the shape
    is byte-ambiguous between ``for(; cond; step)`` and
    ``do { ...; step; } while (cond);``.

    The hint is grounded in two PS-only signals:

      * the structural pattern (entry-jmp / top-test / step / back-edge);
      * the propagated ``-d1`` source line at the test, which must match the
        candidate step's line for the step to count as a for-iteration step
        (a body-internal modification has its own line).
    """
    _, _, lines = disasm_function(name_or_addr)
    detected = detect_loops(lines)
    if as_json:
        typer.echo(json.dumps([asdict(lp) for lp in detected], indent=2))
        return
    if not detected:
        typer.echo("no loops detected")
        return
    by_addr = {ln.address: ln for ln in lines}
    for i, lp in enumerate(detected, 1):
        bits = [f"{lp.kind:<22s}", f"top=0x{lp.top:X}"]
        if lp.entry_jmp is not None:
            bits.append(f"entry_jmp=0x{lp.entry_jmp:X}")
        if lp.step is not None:
            bits.append(f"step=0x{lp.step:X}")
        if lp.test is not None:
            bits.append(f"test=0x{lp.test:X}")
        bits.append(f"back_edge=0x{lp.back_edge:X}")
        if lp.continues:
            bits.append(f"+{lp.continues} continue(s)")
        typer.echo(f"  loop #{i}: " + "  ".join(bits))
        if lp.ambiguous:
            typer.echo(
                "           ambiguous: byte-equivalent to BOTH "
                "`for(; cond; step) {body}` AND "
                "`do { body; step; } while (cond);`"
            )
