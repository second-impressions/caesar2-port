"""`c2 line-skeleton` -- reconstruct a function's ORIGINAL source-line layout
from PS.EXE's -d1 debug line table.

The Watcom debug info maps every statement to its ORIGINAL source line
(symbols.json line_numbers).  For a function this yields the original
file's statement-per-line skeleton: which lines hold code, how many
lines sit between statements (blanks / comments / wrapped expressions
in the ORIGINAL), where multi-statement lines pack several marks, and
what each line's code DOES (calls by name, global stores/loads by name,
compares, branch arcs).

This systematizes the line-map workflow for hard recoveries: write one
source statement per PS line mark, keep multi-line calls spanning the
same number of lines, and the seats follow.  ("The line numbers are
your friends.")

Usage:
    c2 line-skeleton show_people_query_panel
    c2 line-skeleton show_history_graph --bytes
"""
from __future__ import annotations

import bisect
import json
from pathlib import Path

import typer

_SYMS = Path("data/out/symbols.json")
_CODE = Path("data/out/le_code.bin")


def line_skeleton(
    name: str = typer.Argument(..., help="function name"),
    with_bytes: bool = typer.Option(False, "--bytes", help="show opcodes"),
    symbols_json: Path = typer.Option(_SYMS, "--symbols"),
) -> None:
    """Print the function's original-source line skeleton from PS's
    debug line records."""
    from capstone import CS_ARCH_X86, CS_MODE_32, Cs

    d = json.loads(symbols_json.read_text())
    code_syms = sorted((s for s in d["symbols"]
                        if s["kind"].endswith("code") and s["segment"] == 1),
                       key=lambda s: s["offset"])
    by_name = {s["name"]: i for i, s in enumerate(code_syms)}
    if name not in by_name:
        typer.secho(f"[!] {name!r} not in PS code symbols", fg="red")
        raise typer.Exit(1)
    i = by_name[name]
    start = code_syms[i]["offset"]
    end = (code_syms[i + 1]["offset"] if i + 1 < len(code_syms)
           else start + 0x4000)
    mod = code_syms[i]["module_index"]

    data_syms = sorted((s for s in d["symbols"]
                        if s["is_data"] and s["segment"] == 2),
                       key=lambda s: s["offset"])
    data_offs = [s["offset"] for s in data_syms]
    code_offs = [s["offset"] for s in code_syms]

    def dsym(off):
        j = bisect.bisect_right(data_offs, off) - 1
        if j < 0:
            return hex(off)
        s = data_syms[j]
        delta = off - s["offset"]
        return s["name"] + (f"+{delta:#x}" if delta else "")

    def csym(off):
        j = bisect.bisect_right(code_offs, off) - 1
        if j >= 0 and code_offs[j] == off:
            return code_syms[j]["name"]
        return None

    recs = sorted((r for r in d["line_numbers"]
                   if r["module_index"] == mod and start <= r["offset"] < end),
                  key=lambda r: r["offset"])
    if not recs:
        typer.secho("[!] no line records (asm module?)", fg="red")
        raise typer.Exit(1)

    le_code = _CODE.read_bytes()
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    md.detail = True
    ins_by_off = {}
    for ins in md.disasm(le_code[start:end], start):
        ins_by_off[ins.address] = ins
        if ins.mnemonic == "ret" and ins.address >= recs[-1]["offset"]:
            end = ins.address + ins.size
            break

    fname = recs[0]["file"]
    first_line = recs[0]["line"]
    typer.secho(f"# {name}  {fname}:{first_line}..{recs[-1]['line']}  "
                f"PS +0x0..+{end - start:#x}  ({len(recs)} line marks)",
                fg="cyan", bold=True)
    typer.echo("#  gap = original-source lines between marks "
               "(blanks/comments/wrapped args); same line twice = "
               "multi-statement line")

    prev_line = None
    bounds = [r["offset"] for r in recs] + [end]
    for k, r in enumerate(recs):
        line, off = r["line"], r["offset"]
        gap = ""
        if prev_line is not None:
            dl = line - prev_line
            if dl > 1:
                gap = f"  (+{dl - 1} src line{'s' if dl > 2 else ''} between)"
            elif dl == 0:
                gap = "  (SAME LINE: multi-stmt)"
            elif dl < 0:
                gap = f"  (BACKWARD {dl}: shared/loop line)"
        prev_line = line
        # summarize this span's instructions
        parts = []
        o = off
        while o < bounds[k + 1]:
            ins = ins_by_off.get(o)
            if ins is None:
                o += 1
                continue
            if ins.mnemonic == "call":
                t = int(ins.op_str, 16) if ins.op_str.startswith("0x") else None
                parts.append(f"call {csym(t) or ins.op_str}")
            elif ins.mnemonic.startswith("j"):
                t = int(ins.op_str, 16) if ins.op_str.startswith("0x") else None
                if t is not None:
                    arc = ("self" if t == off else
                           "back" if t < off else "fwd")
                    parts.append(f"{ins.mnemonic}->{t - start:+#x}({arc})")
                else:
                    parts.append(ins.mnemonic)
            elif ins.mnemonic in ("cmp", "test"):
                ops = ins.op_str
                for op in ins.operands:
                    if op.type == 3 and op.value.mem.disp > 0x1000 \
                            and op.value.mem.base == 0 and op.value.mem.index == 0:
                        ops = ops.replace(hex(op.value.mem.disp),
                                          dsym(op.value.mem.disp))
                parts.append(f"{ins.mnemonic} {ops}")
            elif ins.mnemonic == "mov":
                for op in ins.operands:
                    if op.type == 3 and op.value.mem.disp > 0x1000 \
                            and op.value.mem.base == 0 and op.value.mem.index == 0:
                        nm = dsym(op.value.mem.disp)
                        st = "->" if op is ins.operands[0] else "<-"
                        parts.append(f"{st}{nm}")
            elif ins.mnemonic == "ret":
                parts.append("ret")
            if with_bytes:
                pass
            o += ins.size
        nbytes = bounds[k + 1] - off
        summ = "  ".join(parts[:6]) + (" …" if len(parts) > 6 else "")
        typer.echo(f"  {fname}:{line:<5} +{off - start:<#7x} "
                   f"{nbytes:>3}b  {summ}{gap}")
