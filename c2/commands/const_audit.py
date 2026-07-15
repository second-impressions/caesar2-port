"""``c2 const-audit`` -- surface WRONG CONSTANTS and off-by-one comparison
boundaries in the reconstructed C, independent of register-allocation noise.

Motivation
----------
A non-byte-exact function's diff is usually dominated by regalloc / encoding
cascade.  A genuinely *wrong constant* (a mistyped literal, a wrong struct
stride, an off-by-one comparison boundary) is buried in that noise even
though it is a real semantic bug.  Immediate constants, unlike registers,
are largely allocation-invariant: a ``cmp eax, 0x4e20`` stays ``0x4e20``
no matter which register holds the value.  So comparing the *multiset* of
constants between PS.EXE and the recompile isolates exactly the
constant-level divergences, order-independently.

Three channels, by signal quality
----------------------------------
* **cmp-threshold** (highest signal): every ``cmp reg, K`` is paired with
  its following ``Jcc`` and canonicalised to the *boundary value* at which
  the branch flips -- ``cmp K; jl/jge`` -> K, ``cmp K; jg/jle`` -> K+1.
  This makes ``x < 0x50`` (``cmp 0x50; jl``) and ``x <= 0x4f``
  (``cmp 0x4f; jle``) compare EQUAL -- so a *legitimate* ``>`` vs ``>=``
  source spelling is NOT flagged, and only a real boundary difference
  (e.g. PS boundary 0x50 vs RC 0x51) shows up.  This is the
  "n vs n+/-1" class.
* **eq** (medium): ``cmp reg, K; je/jne`` equality constants.  An eq-vs-
  threshold split (PS tests ``== K`` eight times where RC range-checks)
  surfaces a structural divergence too.
* **plain** (lower, noise-filtered): mov/push/add/sub/imul/or/test
  immediates -- table values, struct strides, message ids.  Filtered as
  non-source noise: zext masks (``and reg, 0xff/0xffff``), shift counts
  (strength-reduction codegen), stack-frame adjustments (``add/sub esp, K``
  -- the immediate is the spill-driven frame SIZE, not a source constant),
  and the literal ``0`` (a zero-store / zero-materialization artifact: PS
  often zeroes via ``xor``/a reused register, emitting no immediate, while
  RC may emit ``mov [m], 0`` -- a genuine wrong-zero is still caught via the
  non-zero side, e.g. PS ``= 5`` vs RC ``= 0`` -> PS-only ``{5}``).

Noise vs signal (per-channel diff granularity)
----------------------------------------------
* **cmp-boundary** uses a *count-aware multiset* diff: the off-by-one
  signal needs it -- a function with two checks at one boundary (one
  matching, one shifted) only reveals the shift as a COUNT delta (PS
  gains a 0x51, RC gains a 0x50); a value-set diff would cancel the
  shared value and lose the ±1 pairing.
* **eq / plain** use a *value-set* diff: a genuine wrong constant is a
  different LITERAL; a value present on BOTH sides with a different COUNT
  is codegen multiplicity (strength reduction, an extra zero-store, an
  elided/duplicated check) -- noise, not a wrong constant.  Set-diff
  drops that without losing any genuinely-different literal.
* ``cmp reg, 0; je`` (== the no-immediate ``test reg, reg``) is dropped
  from eq as a non-canonical codegen idiom.

These cuts took the corpus from 790 -> 278 reported divergent values with
NO loss of specificity (every different literal is still caught).

Validation
----------
The audit is CLEAN on ALL 1368 byte-exact functions (the value-set diff
also absorbs the tail-merge donor-flip edge case, whose borrowed
constants appear on both sides).  See ``tests/test_const_audit.py``.

Relocated addresses (globals, jump-table entries) are masked via the LE
fixup set + capstone's ``imm_offset``; rel jmp/call/jcc targets are
skipped entirely (layout noise).
"""
from __future__ import annotations

import collections
from pathlib import Path
from typing import Annotated, Optional

import typer

_PS_EXE = Path("data/PS.EXE")
_RC_EXE = Path(".c2-cache/build/out.exe")
_RC_MAP = Path(".c2-cache/build/out.map")

# signed/unsigned conditional jumps -> boundary normalisation.
#   jl/jb   : x <  K   -> boundary K
#   jge/jae : x >= K   -> boundary K
#   jg/ja   : x >  K   -> x >= K+1 -> boundary K+1
#   jle/jbe : x <= K   -> x <  K+1 -> boundary K+1
_JCC_BOUNDARY_K = {"jl", "jb", "jge", "jae"}
_JCC_BOUNDARY_K1 = {"jg", "ja", "jle", "jbe"}
_JCC_EQ = {"je", "jz", "jne", "jnz"}

_ZEXT_MASKS = frozenset({0xFF, 0xFFFF, 0xFFFFFF00, 0xFFFF0000})
_SHIFT_MNEMONICS = frozenset({"shl", "shr", "sar", "sal", "rol", "ror"})


def _md():
    from capstone import CS_ARCH_X86, CS_MODE_32, Cs
    m = Cs(CS_ARCH_X86, CS_MODE_32)
    m.detail = True
    return m


def _is_frame_adjust(ins, x86) -> bool:
    """``add esp, K`` / ``sub esp, K`` -- stack-frame setup/teardown.  The
    immediate is the FRAME SIZE (a spill/regalloc artifact that moves with
    the number of locals the allocator chose to spill), never a source-level
    constant -- so it must not enter the ``plain`` channel, where a PS-vs-RC
    frame-size delta would masquerade as a wrong constant."""
    if ins.mnemonic not in ("add", "sub"):
        return False
    ops = ins.operands
    return (len(ops) == 2 and ops[0].type == x86.X86_OP_REG
            and ins.reg_name(ops[0].reg) == "esp")


def _extract(code: bytes, abs_base: int, fix: set[int]) -> tuple[
        collections.Counter, collections.Counter, collections.Counter]:
    """Return (plain, cmp_boundaries, eq_consts) constant multisets for a
    function's code bytes.  ``abs_base`` is the function's absolute offset
    in the code section (so immediate byte positions can be tested against
    the absolute ``fix`` fixup set)."""
    from capstone import x86
    plain: collections.Counter = collections.Counter()
    boundary: collections.Counter = collections.Counter()
    eq: collections.Counter = collections.Counter()
    insns = list(_md().disasm(code, 0))
    for idx, ins in enumerate(insns):
        mn = ins.mnemonic
        # control transfers: rel targets are layout noise.
        if mn == "jmp" or mn == "call" or (mn.startswith("j") and mn != "jmp"):
            continue
        imm_ops = [o for o in ins.operands if o.type == x86.X86_OP_IMM]
        if not imm_ops:
            continue
        # mask relocated-address immediates (globals / table entries).
        if (abs_base + ins.address + ins.imm_offset) in fix:
            continue
        sval = imm_ops[-1].imm           # signed value
        val = sval & 0xFFFFFFFF
        if mn == "and" and val in _ZEXT_MASKS:
            continue                      # (unsigned char/short) zext mask
        if mn in _SHIFT_MNEMONICS:
            continue                      # strength-reduction shift count
        if _is_frame_adjust(ins, x86):
            continue                      # `add/sub esp, K` = frame size, noise
        if mn == "cmp":
            nj = insns[idx + 1].mnemonic if idx + 1 < len(insns) else ""
            if nj in _JCC_BOUNDARY_K:
                boundary[sval] += 1
            elif nj in _JCC_BOUNDARY_K1:
                boundary[sval + 1] += 1
            elif nj in _JCC_EQ:
                # `cmp reg, 0; je/jne` is the same as `test reg, reg` (which
                # has no immediate) -- PS prefers `test`, so a `cmp 0` here is
                # a non-canonical codegen idiom, not a wrong constant.
                if sval != 0:
                    eq[sval] += 1
            elif sval != 0:
                plain[sval] += 1
        elif val != 0:
            # plain literal 0 is a zero-store / zero-materialization artifact
            # (PS often zeroes via `xor`/a reused register -> no immediate;
            # RC may emit `mov [m], 0`).  A genuine wrong-zero divergence is
            # still caught by the NON-zero side (PS 5 vs RC 0 -> PS-only={5}).
            plain[val] += 1
    return plain, boundary, eq


# ── localization: map each divergent constant back to its asm site(s) ─────
#
# The multiset diff says WHICH constant is wrong; localization says WHERE.
# We re-walk the same disassembly (identical fixup-masking / channel logic
# as ``_extract`` so the keys match the divergence dicts exactly) and
# record, per ``(channel, value)``, the function-relative offset(s) and the
# instruction text.  The PS side is further annotated with its ``-d1``
# source line so the divergent literal lands on the original statement.

def _constant_sites(code: bytes, abs_base: int,
                    fix: set[int]) -> dict[tuple[str, int], list[tuple[int, str]]]:
    """``{(channel, value): [(func_rel_off, asm_text), ...]}``.

    Mirrors ``_extract`` exactly (same skip/mask rules and the same
    ``sval``/``sval+1`` boundary keys) so a lookup by a divergence-dict key
    always hits.  The recorded asm for a boundary is the ``cmp`` itself
    (showing the raw immediate, which makes an off-by-one visible)."""
    from capstone import x86
    sites: dict[tuple[str, int], list[tuple[int, str]]] = {}

    def _add(ch: str, val: int, off: int, asm: str) -> None:
        sites.setdefault((ch, val), []).append((off, asm))

    insns = list(_md().disasm(code, 0))
    for idx, ins in enumerate(insns):
        mn = ins.mnemonic
        if mn == "jmp" or mn == "call" or (mn.startswith("j") and mn != "jmp"):
            continue
        imm_ops = [o for o in ins.operands if o.type == x86.X86_OP_IMM]
        if not imm_ops:
            continue
        if (abs_base + ins.address + ins.imm_offset) in fix:
            continue
        sval = imm_ops[-1].imm
        val = sval & 0xFFFFFFFF
        if mn == "and" and val in _ZEXT_MASKS:
            continue
        if mn in _SHIFT_MNEMONICS:
            continue
        if _is_frame_adjust(ins, x86):
            continue
        asm = f"{mn} {ins.op_str}".strip()
        if mn == "cmp":
            nj = insns[idx + 1].mnemonic if idx + 1 < len(insns) else ""
            if nj in _JCC_BOUNDARY_K:
                _add("cmp_threshold", sval, ins.address, f"{asm} ; {nj}")
            elif nj in _JCC_BOUNDARY_K1:
                _add("cmp_threshold", sval + 1, ins.address, f"{asm} ; {nj}")
            elif nj in _JCC_EQ:
                if sval != 0:
                    _add("eq", sval, ins.address, f"{asm} ; {nj}")
            elif sval != 0:
                _add("plain", sval, ins.address, asm)
        elif val != 0:
            _add("plain", val, ins.address, asm)
    return sites


def _ps_line_map(name: str) -> dict[int, int]:
    """``{func_rel_off: ps_d1_source_line}`` for a PS function (carry-forward
    from the last line mark).  Empty on any failure."""
    try:
        from c2.commands.disasm import disasm_function
        start, _size, lines = disasm_function(name)
    except Exception:
        return {}
    out: dict[int, int] = {}
    cur = 0
    for dl in lines:
        if dl.line:
            cur = dl.line
        out[dl.address - start] = cur
    return out


# ── out-of-order parameter (swapped constant arg) detector ────────────────
# __watcall passes the first 4 int/ptr args in eax,edx,ebx,ecx.  At each call
# we track which arg-register holds a known immediate; a constant that lands
# in a DIFFERENT arg slot in PS vs RC (same callee, matched by order) is a
# swapped-argument candidate -- and it fires even when the OTHER swapped arg
# is a variable (the constant's slot still moves).  Same value-multiset, so
# `constant_audit` sees it as CLEAN: this is the additive signal.
_ARGREG = {"eax": 0, "edx": 1, "ebx": 2, "ecx": 3}
_ARGNAME = {0: "eax/arg0", 1: "edx/arg1", 2: "ebx/arg2", 3: "ecx/arg3"}


def _call_arg_consts(code: bytes, abs_base: int, fix: set[int],
                     off_to_name: dict) -> list[tuple[str, dict[int, int]]]:
    """``[(callee_name, {argslot: const}), ...]`` in call order.

    Tracks ``mov <argreg>, imm`` constants live into each call.  A pending
    arg-const is invalidated as soon as its register is READ (its value flows
    elsewhere -- e.g. ``mov edx, ebx`` stages it into arg1, so ebx is a source
    register, not a dedicated arg2) or written by anything other than a fresh
    ``mov-imm``.  This drops the regalloc-leftover false positive where a
    variable that happens to hold a constant lives in an arg register across a
    call to a function that doesn't take that many args."""
    from capstone import x86
    calls: list[tuple[str, dict[int, int]]] = []
    pending: dict[int, int] = {}              # argslot -> const since last call
    for ins in _md().disasm(code, abs_base):
        mn = ins.mnemonic
        if mn == "call":
            tgt = (int(ins.op_str, 16) if ins.op_str.startswith("0x") else None)
            nm = off_to_name.get(tgt) if tgt is not None else None
            if nm:
                calls.append((nm, dict(pending)))
            pending = {}                       # arg regs are caller-clobbered
            continue
        ops = ins.operands
        set_slot = None
        if (mn == "mov" and len(ops) == 2 and ops[0].type == x86.X86_OP_REG
                and ops[1].type == x86.X86_OP_IMM
                and (abs_base + ins.address + ins.imm_offset) not in fix):
            set_slot = _ARGREG.get(ins.reg_name(ops[0].reg))
        # invalidate any arg reg this instruction READS or WRITES (the value
        # is consumed/recomputed -> not a fresh dedicated arg), except the one
        # we are setting via mov-imm this instruction.
        regs_read, regs_written = ins.regs_access()
        for r in set(regs_read) | set(regs_written):
            s = _ARGREG.get(ins.reg_name(r))
            if s is not None and s != set_slot:
                pending.pop(s, None)
        if set_slot is not None:
            pending[set_slot] = ops[1].imm & 0xFFFFFFFF
    return calls


def argswap_audit(ps_bytes: bytes, rc_bytes: bytes,
                  ps_off: int, rc_off: int,
                  ps_fix: set[int], rc_fix: set[int],
                  ps_o2n: dict, rc_o2n: dict) -> list[dict]:
    """Swapped-constant-arg candidates for one function.  Each entry:
    ``{callee, const, ps_slot, rc_slot}``."""
    import collections
    ps_calls = _call_arg_consts(ps_bytes, ps_off, ps_fix, ps_o2n)
    rc_calls = _call_arg_consts(rc_bytes, rc_off, rc_fix, rc_o2n)
    # Reliability guard: only compare when the CALL SEQUENCE matches.  If the
    # two callee sequences differ (a shape divergence added / removed / moved
    # a call), per-position pairing can compare two DIFFERENT logical calls
    # and invent a false swap.  Requiring an identical sequence guarantees the
    # k-th call is the same logical call on both sides.  (Byte-exact functions
    # always match; this only suppresses unreliable shape-divergent ones.)
    if [n for n, _ in ps_calls] != [n for n, _ in rc_calls]:
        return []
    by_callee_rc: dict[str, list] = collections.defaultdict(list)
    for nm, args in rc_calls:
        by_callee_rc[nm].append(args)
    out: list[dict] = []
    seen: collections.Counter = collections.Counter()
    for nm, ps_args in ps_calls:
        k = seen[nm]
        seen[nm] += 1
        if k >= len(by_callee_rc[nm]):
            continue                            # call sequences diverge; skip
        rc_args = by_callee_rc[nm][k]
        # A value at EXACTLY ONE slot on each side is unambiguous; a value in
        # multiple arg slots (e.g. a dimension passed to two params) inverts
        # lossily -- skip it.
        pc = collections.Counter(ps_args.values())
        rc_c = collections.Counter(rc_args.values())
        ps_pos = {v: s for s, v in ps_args.items()}
        rc_pos = {v: s for s, v in rc_args.items()}
        for val in set(ps_pos) & set(rc_pos):
            if pc[val] == 1 and rc_c[val] == 1 and ps_pos[val] != rc_pos[val]:
                out.append({"callee": nm, "const": val,
                            "ps_slot": ps_pos[val], "rc_slot": rc_pos[val]})
    return out


_PS_O2N_CACHE: Optional[dict] = None


def _ps_off_to_name() -> dict:
    global _PS_O2N_CACHE
    if _PS_O2N_CACHE is None:
        from c2.commands.shape_recon import _get_syms
        S = _get_syms()
        _PS_O2N_CACHE = {s["offset"]: s["name"] for s in S.code_syms}
    return _PS_O2N_CACHE


def constant_audit(orig_bytes: bytes, recomp_bytes: bytes,
                   orig_off: int, recomp_off: int,
                   orig_fix: set[int], recomp_fix: set[int]) -> dict:
    """Pure audit: compare PS vs RC constant multisets for one function.

    Returns ``{channel: {"ps_only": {k: n}, "rc_only": {k: n}}}`` for each
    channel that diverges, plus ``"clean": bool`` and ``"n_div": int``."""
    po, pb, pe = _extract(orig_bytes, orig_off, orig_fix)
    ro, rb, re = _extract(recomp_bytes, recomp_off, recomp_fix)
    out: dict = {}
    n_div = 0
    # Per-channel diff granularity (noise vs signal):
    #   cmp_threshold -> MULTISET (count-aware).  The off-by-one signal needs
    #     it: a function with two checks at one boundary (one matching, one
    #     shifted) only reveals the shift as a COUNT delta (PS gains a 0x51,
    #     RC gains a 0x50).  Value-set would cancel the shared value and lose
    #     the ±1 pairing.  Boundary values are high-signal, so the residual
    #     count noise here is small.
    #   eq / plain    -> VALUE-set.  A genuine wrong constant is a different
    #     LITERAL; a value on BOTH sides with a different COUNT is codegen
    #     multiplicity (strength reduction, extra zero-store, elided check) --
    #     noise.  Set-diff drops it without losing any different literal.
    for ch, ps_c, rc_c, multiset in (("cmp_threshold", pb, rb, True),
                                     ("eq", pe, re, False),
                                     ("plain", po, ro, False)):
        if multiset:
            ps_only = dict(ps_c - rc_c)
            rc_only = dict(rc_c - ps_c)
        else:
            ps_v, rc_v = set(ps_c), set(rc_c)
            ps_only = {k: ps_c[k] for k in ps_v - rc_v}
            rc_only = {k: rc_c[k] for k in rc_v - ps_v}
        if ps_only or rc_only:
            out[ch] = {"ps_only": ps_only, "rc_only": rc_only}
            n_div += len(ps_only) + len(rc_only)   # distinct divergent values
    out["clean"] = not any(k in out for k in ("cmp_threshold", "eq", "plain"))
    out["n_div"] = n_div
    return out


# ── data loading (cached recompile) ───────────────────────────────────────

def _load_all():
    from c2.commands.decomp_verify import _load_le_code_and_fixups, _parse_map
    from c2.commands.shape_recon import _get_syms
    S = _get_syms()
    ps_code, ps_fix = _load_le_code_and_fixups(_PS_EXE)
    if not _RC_EXE.exists() or not _RC_MAP.exists():
        raise FileNotFoundError(
            f"no cached recompile at {_RC_EXE}; run `c2 decomp-verify` once")
    rc_code, rc_fix = _load_le_code_and_fixups(_RC_EXE)
    rc_map = _parse_map(_RC_MAP)
    ps_o2n = {s["offset"]: s["name"] for s in S.code_syms}
    rc_o2n = {off: nm.rstrip("_") for nm, off in rc_map.items()}
    # Sorted unique offset list of every named code symbol in the recompile;
    # used to compute the *RC* function end (= offset of the next named
    # symbol).  Without this, an audit re-uses the PS function size for both
    # sides, and when the RC function is SMALLER than its PS counterpart
    # the slice overruns into the NEXT RC function and reports phantom
    # divergences from neighbour code (e.g. `build_city_item` (PS 0xCB3b /
    # RC 0xC39b) used to surface `cmp edi, 0x1e/0x1f ; jne` that physically
    # lives in `prebuild_region_item`).
    rc_sorted_offs = sorted(set(rc_map.values()))
    return (S, ps_code, ps_fix, rc_code, rc_fix, rc_map, ps_o2n, rc_o2n,
            rc_sorted_offs)


def _rc_func_end(ro: int, rc_sorted_offs: list[int], rc_code_len: int) -> int:
    """Offset of the next named RC code symbol after ``ro`` (or the end of
    the code section).  This is the upper bound for slicing RC bytes of the
    function starting at ``ro``; using PS size as a fallback overruns into
    the next function and reports neighbour-code constants as divergent."""
    import bisect
    j = bisect.bisect_right(rc_sorted_offs, ro)
    return rc_sorted_offs[j] if j < len(rc_sorted_offs) else rc_code_len


def _audit_named(name: str, ctx) -> Optional[dict]:
    (S, ps_code, ps_fix, rc_code, rc_fix, rc_map, ps_o2n, rc_o2n,
     rc_sorted_offs) = ctx
    if name not in S.by_name:
        return None
    i = S.by_name[name]
    o = S.code_syms[i]["offset"]
    end = (S.code_syms[i + 1]["offset"] if i + 1 < len(S.code_syms)
           else o + 0x4000)
    size = end - o
    ro = rc_map.get(name) or rc_map.get(name + "_")
    if ro is None:
        return None
    # Slice each side by its OWN function bounds -- PS size != RC size in
    # general, and re-using PS size for RC overruns into the next RC
    # function (false-positive constants from neighbour code).
    rc_end = _rc_func_end(ro, rc_sorted_offs, len(rc_code))
    rc_size = rc_end - ro
    ps_slice = ps_code[o:o + size]
    rc_slice = rc_code[ro:ro + rc_size]
    res = constant_audit(ps_slice, rc_slice, o, ro, ps_fix, rc_fix)
    swaps = argswap_audit(ps_slice, rc_slice, o, ro,
                          ps_fix, rc_fix, ps_o2n, rc_o2n)
    res["arg_swap"] = swaps
    if swaps:
        res["clean"] = False          # an out-of-order parameter is not clean
    res["name"] = name
    # Localization: attach asm sites for the divergent constants so the
    # verdict is actionable (offset + instruction + PS -d1 line).  Only when
    # there is a real constant divergence (cheap; skipped for clean fns).
    if any(k in res for k in ("cmp_threshold", "eq", "plain")):
        res["_ps_sites"] = _constant_sites(ps_slice, o, ps_fix)
        res["_rc_sites"] = _constant_sites(rc_slice, ro, rc_fix)
        res["_ps_lines"] = _ps_line_map(name)
    return res


def _fmt_counter(d: dict) -> str:
    return "{" + ", ".join(f"{k:#x}:{v}" for k, v in
                           sorted(d.items())) + "}"


def _print_one(res: dict) -> None:
    nm = res.get("name", "?")
    swaps = res.get("arg_swap") or []
    has_const = any(k in res for k in ("cmp_threshold", "eq", "plain"))
    if not has_const and not swaps:
        typer.secho(f"  ✓  {nm}: CLEAN (no constant divergence)", fg="green")
        return
    if swaps:
        typer.secho(f"  ✗  {nm}: {len(swaps)} out-of-order parameter(s)",
                    fg="red")
        for s in swaps:
            typer.echo(f"      {s['callee']}() const {s['const']:#x} -> "
                       f"PS {_ARGNAME[s['ps_slot']]} but RC "
                       f"{_ARGNAME[s['rc_slot']]}")
    if not has_const:
        return
    typer.secho(f"  ✗  {nm}: {res['n_div']} divergent constant(s)", fg="yellow")
    for ch, label in (("cmp_threshold", "cmp-boundary (n vs n±1)"),
                      ("eq", "equality"), ("plain", "plain")):
        if ch in res:
            ps = res[ch]["ps_only"]
            rc = res[ch]["rc_only"]
            # flag exact off-by-one pairs in the boundary channel.
            extra = ""
            if ch == "cmp_threshold":
                pset, rset = set(ps), set(rc)
                offby1 = sorted(k for k in pset if (k + 1 in rset or k - 1 in rset))
                if offby1:
                    extra = ("   ⟵ off-by-one boundary: "
                             + ", ".join(f"PS {k:#x}" for k in offby1))
            typer.echo(f"      {label:24s} PS-only={_fmt_counter(ps)}  "
                       f"RC-only={_fmt_counter(rc)}{extra}")
            _print_sites(ch, ps, rc, res)


def _print_sites(ch: str, ps: dict, rc: dict, res: dict) -> None:
    """Render the asm site(s) for each divergent constant in one channel.

    PS-only values come from PS's bytes (annotated with the ``-d1`` source
    line -- the original statement to fix); RC-only values come from OUR
    recompile (offset + instruction -- the wrong literal we emitted)."""
    ps_sites = res.get("_ps_sites")
    rc_sites = res.get("_rc_sites")
    if ps_sites is None and rc_sites is None:
        return
    ps_lines = res.get("_ps_lines") or {}
    cap = 10
    for val in sorted(ps):
        hits = (ps_sites or {}).get((ch, val), [])
        for off, asm in hits[:cap]:
            ln = ps_lines.get(off)
            tag = f"L{ln}" if ln else "L?"
            typer.echo(f"          PS {val:#x}  @ +{off:#06x} {tag:>7}  {asm}")
        if len(hits) > cap:
            typer.echo(f"          PS {val:#x}  … +{len(hits) - cap} more site(s)")
    for val in sorted(rc):
        hits = (rc_sites or {}).get((ch, val), [])
        for off, asm in hits[:cap]:
            typer.echo(f"          RC {val:#x}  @ +{off:#06x}          {asm}")
        if len(hits) > cap:
            typer.echo(f"          RC {val:#x}  … +{len(hits) - cap} more site(s)")


def const_audit(
    name: Annotated[Optional[str], typer.Argument(
        help="function name (omit with --corpus)")] = None,
    corpus: Annotated[bool, typer.Option(
        "--corpus", help="audit every diffing function, ranked by "
        "divergence; surfaces wrong-constant candidates corpus-wide")] = False,
    boundary_only: Annotated[bool, typer.Option(
        "--boundary-only", help="only the high-signal cmp-boundary channel "
        "(the n vs n±1 / >/>= class)")] = False,
    argswap_only: Annotated[bool, typer.Option(
        "--argswap", help="only out-of-order parameter (swapped const arg) "
        "candidates")] = False,
    limit: Annotated[int, typer.Option(
        "-n", "--limit", help="corpus: max rows (0 = all)")] = 0,
) -> None:
    """Audit reconstructed-C constants against PS.EXE, regalloc-independent.

    Compares the *multiset* of immediate constants (with comparison
    boundaries canonicalised so ``>`` vs ``>=`` spellings don't false-
    positive) between PS.EXE and the cached recompile.  Surfaces wrong
    literals, struct strides, and off-by-one comparison boundaries that
    are otherwise buried in regalloc cascade.
    """
    try:
        ctx = _load_all()
    except FileNotFoundError as e:
        typer.secho(f"[!] {e}", fg="red")
        raise typer.Exit(1)

    if not corpus:
        if not name:
            typer.secho("[!] provide a function name or --corpus", fg="red")
            raise typer.Exit(1)
        res = _audit_named(name, ctx)
        if res is None:
            typer.secho(f"[!] {name}: not found in symbols or recompile map",
                        fg="red")
            raise typer.Exit(1)
        if boundary_only and not res.get("clean"):
            res = {k: v for k, v in res.items() if k != "eq" and k != "plain"}
            res["clean"] = "cmp_threshold" not in res
            res.setdefault("name", name)
        _print_one(res)
        return

    # corpus mode
    import json as _json
    from c2.commands.verify_json import get_verify_json
    doc = get_verify_json(no_build=True)
    diffing = [f["name"] for f in doc.get("functions", [])
               if f.get("diff_byte_count", 0) > 0]
    rows = []
    for nm in diffing:
        res = _audit_named(nm, ctx)
        if res is None or res.get("clean"):
            continue
        if argswap_only and not res.get("arg_swap"):
            continue
        if boundary_only and "cmp_threshold" not in res:
            continue
        rows.append(res)
    # arg-swaps first (a real out-of-order parameter), then cmp-boundary.
    rows.sort(key=lambda r: (bool(r.get("arg_swap")),
                             ("cmp_threshold" in r), r["n_div"]), reverse=True)
    if limit:
        rows = rows[:limit]
    n_swap = sum(1 for r in rows if r.get("arg_swap"))
    typer.secho(f"\n# const-audit: {len(rows)} diffing function(s) flagged  "
                f"(of {len(diffing)})", fg="cyan", bold=True)
    typer.secho(f"#   {n_swap} with an OUT-OF-ORDER PARAMETER (swapped const "
                "arg) -- highest signal -- then cmp-boundary (n vs n±1)\n",
                fg="cyan")
    for res in rows:
        _print_one(res)
