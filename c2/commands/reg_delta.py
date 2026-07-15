"""``c2 reg-delta <fn>`` -- PS-vs-RC register census from asm (direction-B:
the liveness/realization inverse's first lens).

Most of the remaining diffing corpus is NOT wrong source SHAPE -- it is
register/instruction REALISATION: RC enregisters a value PS materialised
inline (extra callee-save push, Rule 110 const-hoist), or seats a value in a
different register than PS (an equal-savings tie, Rule 28a/115).  Diagnosing
those means reading BOTH sides' *actual register usage* -- RC's from the
recompile, PS's from PS.EXE's bytes -- and diffing it.  That read used to be a
hand grep of the disassembly; this command automates it.

For each general register it reports, per side, how many instructions touch it
and the **constant-operand fingerprint** of the values it holds (``mov reg,
0x28`` etc.).  The fingerprint is the discriminator: the SAME constants showing
up in register R on PS and register R' on RC is a **seat swap** R<->R' that a
bare use-count would hide.

Two headline signals:

  * **push-set delta** -- a callee-save register one side pushes and the other
    doesn't.  RC-extra = RC enregisters one more long-lived value than PS
    (Rule 89/110); the register's held value (esp. a const) names it.
  * **seat swap** -- a constant fingerprint that lands in different registers
    on the two sides (Rule 28a/115 last-use/creation-order tie).

Validated: a byte-exact function shows ZERO delta (the bytes are identical);
``mid3_line_with_sides_base`` shows RC's extra EBP holding const ``0xf`` while
PS leaves EBP unused (the LICM const-hoist); ``place2_a_building_top`` shows an
``esi<->edi`` swap via the ``0x28/0x2c`` fingerprint.

Usage::

    uv run c2 reg-delta mid3_line_with_sides_base
    uv run c2 reg-delta place2_a_building_top --json
"""
from __future__ import annotations

import bisect
import json
import re
from pathlib import Path
from typing import Annotated, Optional

import typer

_REGTOK = re.compile(r"\b(e?[a-d]x|[a-d][lh]|e?[sd]i|e?bp|e?sp)\b")
_MOVIMM = re.compile(r"mov (e[a-z]{2}), (0x[0-9a-f]+|-?\d+)$")
# 32-bit family -> all its sub-register tokens
_FAM = {
    "eax": ["eax", "ax", "al", "ah"], "ebx": ["ebx", "bx", "bl", "bh"],
    "ecx": ["ecx", "cx", "cl", "ch"], "edx": ["edx", "dx", "dl", "dh"],
    "esi": ["esi", "si"], "edi": ["edi", "di"], "ebp": ["ebp", "bp"],
    "esp": ["esp", "sp"],
}
_TOK2FAM = {t: f for f, ts in _FAM.items() for t in ts}
_CALLEE = ("ebx", "esi", "edi", "ebp")          # esp/ebp frame aside; ebx/esi/edi/ebp are the pushed callees
_GP = ("eax", "edx", "ebx", "ecx", "esi", "edi", "ebp")


def _sides(function: str):
    """Return ``(ps_insns, rc_insns)`` -- disasm of PS.EXE's bytes and the
    cached recompile's bytes for ``function`` (same slicing as c2 ledger)."""
    from c2.commands.decomp_verify import (
        _disasm_for_diff, _load_le_code_and_fixups, _build_all, _parse_map,
        _DEFAULT_IMAGE, PS_CFLAGS,
    )
    d = json.loads(Path("data/out/symbols.json").read_text())
    code_syms = sorted(
        (s for s in d["symbols"] if s.get("is_code") and s["segment"] == 1),
        key=lambda s: s["offset"])
    m = [s for s in code_syms
         if s.get("name") == function or s.get("raw_name") == function]
    if not m:
        raise ValueError(f"{function!r} not found in PS code symbols")
    ps = m[0]
    offs = [s["offset"] for s in code_syms]
    i = bisect.bisect_right(offs, ps["offset"])
    ps_size = (offs[i] if i < len(offs) else ps["offset"] + 0x4000) - ps["offset"]
    ps_code, _ = _load_le_code_and_fixups(Path("data/PS.EXE"))
    ps_bytes = ps_code[ps["offset"]:ps["offset"] + ps_size]

    ok, out, _work, out_exe, out_map = _build_all(
        Path("decomp/src"), Path("decomp/include"), _DEFAULT_IMAGE,
        PS_CFLAGS, use_cache=True)
    if not ok:
        raise ValueError("build failed:\n" + out)
    rc_code, _ = _load_le_code_and_fixups(out_exe)
    rc_map = _parse_map(out_map)
    raw = function if function.endswith("_") else function + "_"
    rc_off = rc_map.get(raw, rc_map.get(function))
    if rc_off is None:
        raise ValueError(f"{function!r} not in the recompile map")
    rc_offs = sorted(set(rc_map.values()))
    j = bisect.bisect_right(rc_offs, rc_off)
    rc_size = (rc_offs[j] if j < len(rc_offs) else rc_off + 0x4000) - rc_off
    rc_bytes = rc_code[rc_off:rc_off + rc_size]
    return _disasm_for_diff(ps_bytes), _disasm_for_diff(rc_bytes)


def _prologue_pushes(insns) -> list[str]:
    out = []
    for off, sz, raw, txt in insns:
        m = re.match(r"push (e[a-z]{2})$", txt)
        if m and off < 16:
            out.append(m.group(1))
        elif not txt.startswith("push"):
            break
    return out


def _census(insns) -> tuple[dict[str, int], dict[str, list[str]]]:
    """``(uses_per_family, const_loads_per_family)``."""
    use = {f: 0 for f in _FAM}
    const: dict[str, list[str]] = {}
    for off, sz, raw, txt in insns:
        for tok in set(_REGTOK.findall(txt)):
            f = _TOK2FAM.get(tok)
            if f:
                use[f] += 1
        m = _MOVIMM.match(txt)
        if m and m.group(1) in _FAM:
            const.setdefault(m.group(1), []).append(m.group(2))
    return use, const


def analyze(function: str) -> dict:
    ps_ins, rc_ins = _sides(function)
    psp, rcp = _prologue_pushes(ps_ins), _prologue_pushes(rc_ins)
    psu, psc = _census(ps_ins)
    rcu, rcc = _census(rc_ins)
    rc_extra = [r for r in rcp if r not in psp]
    ps_extra = [r for r in psp if r not in rcp]
    # seat swaps: a const fingerprint present in reg R (PS) and reg R' (RC).
    swaps = []
    for a in _GP:
        for b in _GP:
            if a >= b:
                continue
            shared_ab = set(psc.get(a, [])) & set(rcc.get(b, []))
            shared_ba = set(psc.get(b, [])) & set(rcc.get(a, []))
            # require a DISTINCTIVE fingerprint: >=2 shared constants (a single
            # small common literal like `2`/`6` coincides across many regs).
            if shared_ab and shared_ba and len(shared_ab | shared_ba) >= 2:
                swaps.append((a, b, sorted(shared_ab | shared_ba)))
    return {
        "function": function, "ps_push": psp, "rc_push": rcp,
        "rc_extra": rc_extra, "ps_extra": ps_extra,
        "ps_use": psu, "rc_use": rcu, "ps_const": psc, "rc_const": rcc,
        "swaps": swaps,
    }


def _classify(a: dict) -> str:
    if a.get("err"):
        return "ERR"
    if a["rc_extra"]:
        return "RC-extra-push"
    if a["ps_extra"]:
        return "PS-extra-push"
    if a["swaps"]:
        return "seat-swap"
    if any(a["ps_use"][f] != a["rc_use"][f]
           or a["ps_const"].get(f) != a["rc_const"].get(f) for f in _GP):
        return "reg-count-delta"
    return "zero-delta"


def _corpus():
    """Landscape of the reg-delta classes over the whole diffing set."""
    import collections
    from c2.commands.verify_json import get_verify_json
    v = get_verify_json(verbose=False, no_build=False)
    fns = [f["name"] for f in v.get("functions", [])
           if f.get("diff_byte_count", 0) > 0]
    rows = []
    for fn in fns:
        try:
            rows.append(analyze(fn))
        except Exception as e:                     # noqa: BLE001
            rows.append({"function": fn, "err": str(e)[:60]})
    bucket = collections.Counter(_classify(a) for a in rows)
    typer.secho(f"\nreg-delta landscape -- {len(rows)} diffing fns",
                fg="green", bold=True)
    typer.secho("  " + "  ".join(f"{k}:{c}" for k, c in bucket.most_common()),
                fg="cyan")
    typer.echo("  RC/PS-extra-push = Rule 89/110 (const-hoist names the value) · "
               "seat-swap = Rule 28a/115 tie · zero-delta = pure byte-seat "
               "(c2 regtrace) · reg-count-delta = mixed realisation")
    for cls in ("RC-extra-push", "PS-extra-push", "seat-swap",
                "reg-count-delta", "zero-delta", "ERR"):
        group = [a for a in rows if _classify(a) == cls]
        if not group:
            continue
        typer.secho(f"\n  [{cls}] ({len(group)})", bold=True)
        for a in group:
            extra = ""
            if a.get("rc_extra"):
                held = a["rc_const"].get(a["rc_extra"][0], [])
                extra = f"  RC+{','.join(a['rc_extra'])}" + (
                    f"={{{','.join(sorted(set(held)))}}}" if held else "")
            elif a.get("ps_extra"):
                extra = f"  PS+{','.join(a['ps_extra'])}"
            elif a.get("swaps"):
                extra = "  " + " ".join(f"{x}<->{y}" for x, y, _ in a["swaps"])
            elif a.get("err"):
                extra = f"  ({a['err']})"
            typer.echo(f"    {a['function']:34}{extra}")


def reg_delta(
    function: Annotated[Optional[str], typer.Argument(help="function name")] = None,
    corpus: Annotated[bool, typer.Option("--corpus", help="landscape over all diffing fns")] = False,
    json_out: Annotated[bool, typer.Option("--json", help="JSON output")] = False,
):
    """Diff PS's vs RC's actual register usage (from asm) -- the extra-push /
    const-hoist / seat-swap lens for direction-B realisation residues."""
    if corpus:
        _corpus()
        return
    if not function:
        typer.secho("provide a function name or --corpus", fg="red", err=True)
        raise typer.Exit(2)
    try:
        a = analyze(function)
    except Exception as exc:                       # noqa: BLE001
        typer.secho(f"reg-delta {function}: {exc}", fg="red", err=True)
        raise typer.Exit(2)
    if json_out:
        typer.echo(json.dumps(a, indent=2))
        return

    typer.secho(f"\nreg-delta {function}  (PS vs RC register census from asm)",
                fg="green", bold=True)
    typer.echo(f"  push set:  PS [{' '.join(a['ps_push'])}]"
               f"   RC [{' '.join(a['rc_push'])}]")
    if a["rc_extra"]:
        typer.secho(f"    ⚠ RC pushes EXTRA callee-save: {' '.join(a['rc_extra'])}"
                    "  (RC enregisters one more long-lived value than PS -- "
                    "Rule 89/110)", fg="yellow")
    if a["ps_extra"]:
        typer.secho(f"    ⚠ PS pushes EXTRA callee-save: {' '.join(a['ps_extra'])}"
                    "  (PS enregisters one more than RC -- add a named local / "
                    "cache a value)", fg="yellow")
    if not a["rc_extra"] and not a["ps_extra"] and not any(
            a["ps_use"][f] != a["rc_use"][f] or a["ps_const"].get(f) != a["rc_const"].get(f)
            for f in _GP) and not a["swaps"]:
        typer.secho("  register census IDENTICAL (byte-exact or pure "
                    "byte-seat) -- no register-level delta.", fg="cyan")
        return

    typer.echo("  register census (uses  const-fingerprint):")
    for f in _GP:
        pu, ru = a["ps_use"][f], a["rc_use"][f]
        pc, rc = a["ps_const"].get(f, []), a["rc_const"].get(f, [])
        if pu == ru and pc == rc:
            continue
        mark = ""
        if f in a["rc_extra"]:
            mark = "  ← RC-only (const-hoist / Rule 110)" if rc else "  ← RC-only push"
        pcs = "{" + ",".join(sorted(set(pc))) + "}" if pc else ""
        rcs = "{" + ",".join(sorted(set(rc))) + "}" if rc else ""
        typer.echo(f"    {f}: PS {pu:>3}x {pcs:22}  RC {ru:>3}x {rcs}{mark}")

    if a["swaps"]:
        typer.echo("  seat swaps (same const fingerprint, different register):")
        for x, y, consts in a["swaps"]:
            typer.echo(f"    {x} <-> {y}   fingerprint {{{','.join(consts)}}}")

    typer.echo("\n  levers:")
    for r in a["rc_extra"]:
        held = a["rc_const"].get(r)
        if held:
            typer.echo(f"    * RC's extra {r} caches const {{{','.join(sorted(set(held)))}}} "
                       f"that PS stores INLINE (`mov [m], imm`); PS uses {r} "
                       f"{a['ps_use'][r]}x -> const-cache vs immediate (Rule 110 / "
                       f"loop-invariant hoist), NOT a which-register tie.  PS "
                       f"leaves {r} free too, so availability is not the "
                       f"discriminator -- a codegen/hoist decision on ~identical "
                       f"IL.  Direction: match PS's live-set (c2 win-census flags "
                       f"any extra local as a candidate); may be sub-source.")
        else:
            typer.echo(f"    * RC's extra {r} holds a long-lived value PS didn't "
                       f"enregister -> Rule 89: inline the value / shorten its "
                       f"range so it no longer spans the call.")
    for x, y, consts in a["swaps"]:
        typer.echo(f"    * {x}<->{y} seat swap -> equal-savings tie (Rule 28a "
                   f"use-order / Rule 115 decl-order); c2 regtrace names the value, "
                   f"reorder its last use to flip the seat.")
    typer.echo("  (byte-exact fns show ZERO delta; a pure byte-register swap is "
               "invisible here -- use c2 regtrace for CL/DL ties.)")
