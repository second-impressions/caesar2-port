"""Map PS.EXE instruction ranges to original/debug source line groups.

The Watcom -d1 line table marks only statement starts.  Instructions with
line 0 inherit the previous source line.  This command groups a function's PS
assembly by those inherited line numbers and prints an LLM-friendly map from
binary code passages to original line-relative source locations.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from typing import Annotated

import typer

from c2.commands.c_source import classify_source
from c2.commands.disasm import disasm_function, format_disasm_line
from c2.commands import line_corpus as _lc


@dataclass
class SourceLoc:
    file: str
    annotation_line: int
    signature_line: int
    orig_start: int | None
    orig_end: int | None


@dataclass
class LineGroup:
    orig_line: int | None
    rel_line: int | None
    current_line: int | None
    source: str | None
    insn_count: int
    start_off: int
    end_off: int
    asm: list[str]
    diff_rows: int = 0
    diff_bytes: int = 0
    hints: dict[str, int] | None = None
    examples: list[str] | None = None
    # Cross-corpus line-code match: verified source that produced the same
    # normalized bytes elsewhere.  Carries ALL suggestions for JSON; the text
    # renderer shows only the top useful ones.
    match: dict | None = None


def _find_source_loc(fn: str) -> SourceLoc | None:
    """Find the checked-in function with the AST classifier.

    Regex is used only for the non-C ``// Lines A–B`` metadata comment; the
    function identity and definition line come from pycparser/classify_source.
    """
    pat_lines = re.compile(r"//\s*Lines\s+(\d+)\s*[–-]\s*(\d+)")
    for path in sorted(Path("decomp/src").glob("*.c")):
        src = path.read_text(errors="ignore")
        try:
            decls = classify_source(src, str(path))
        except Exception:
            continue
        lines = src.splitlines()
        for func in decls.func_defs:
            if func.decl.name != fn or func.decl.coord is None:
                continue
            sig_line = func.decl.coord.line
            ann = decls.annotations.get(sig_line)
            ann_line = ann.line if ann else sig_line
            orig_start = orig_end = None
            for j in range(max(0, ann_line - 1), max(0, sig_line - 1)):
                m = pat_lines.match(lines[j])
                if m:
                    orig_start, orig_end = int(m.group(1)), int(m.group(2))
            return SourceLoc(str(path), ann_line, sig_line, orig_start, orig_end)
    return None


def _source_line(loc: SourceLoc | None, orig_line: int | None) -> tuple[int | None, str | None, int | None]:
    if loc is None or orig_line is None or loc.orig_start is None:
        return None, None, None
    rel = orig_line - loc.orig_start
    cur = loc.signature_line + rel
    try:
        lines = Path(loc.file).read_text(errors="ignore").splitlines()
        text = lines[cur - 1] if 1 <= cur <= len(lines) else None
    except OSError:
        text = None
    return cur, text, rel


def _load_diff_by_line(fn: str, loc: SourceLoc | None) -> dict[int, dict]:
    """Run decomp-verify JSON for fn and bucket diff rows by inherited PS line."""
    if loc is None:
        return {}
    try:
        from c2.commands.decomp_verify import decomp_verify
        buf = StringIO()
        with redirect_stdout(buf):
            decomp_verify(
                c_files=[Path(loc.file)],
                function=[fn],
                verbose=True,
                json_out=True,
                strict=False,
                strict_warnings=False,
            )
        doc = json.loads(buf.getvalue())
    except BaseException:
        return {}
    funcs = doc.get("functions") or []
    if not funcs:
        return {}
    cur_ln: int | None = None
    out: dict[int, dict] = {}
    for row in funcs[0].get("rows", []):
        if row.get("ln") is not None:
            cur_ln = row["ln"]
        if cur_ln is None or row.get("kind") == "equal":
            continue
        b = out.setdefault(cur_ln, {"rows": 0, "bytes": 0, "hints": {}, "examples": []})
        b["rows"] += 1
        ps_n = len(row.get("ps", {}).get("diff_pos") or [])
        rc_n = len(row.get("rc", {}).get("diff_pos") or [])
        b["bytes"] += max(ps_n, rc_n)
        hint = row.get("hint") or {}
        rule = hint.get("rule") or "unexplained"
        b["hints"][rule] = b["hints"].get(rule, 0) + 1
        if len(b["examples"]) < 4:
            ps = row.get("ps", {}).get("asm", "")
            rc = row.get("rc", {}).get("asm", "")
            b["examples"].append(f"{row.get('kind')}: PS `{ps}` | RC `{rc}` ({rule})")
    return out


_PS_CACHE: tuple | None = None


def _ps_fix_and_base() -> tuple[set[int], int]:
    """Cached (code-section fixup byte set, code_base vaddr) for PS.EXE."""
    global _PS_CACHE
    if _PS_CACHE is None:
        from c2.commands.decomp_verify import _load_le_code_and_fixups
        _, fix = _load_le_code_and_fixups(Path("data/PS.EXE"))
        sym = json.loads(Path("data/out/symbols.json").read_text())
        base = sym["memory_map"]["objects"][0]["base_address_int"]
        _PS_CACHE = (fix, base)
    return _PS_CACHE


def build_line_groups(fn: str, *, max_asm_per_line: int = 30, with_diff: bool = True, with_match: bool = True) -> tuple[SourceLoc | None, list[LineGroup]]:
    addr, _size, lines = disasm_function(fn)
    loc = _find_source_loc(fn)
    groups: list[LineGroup] = []
    diff_by_line = _load_diff_by_line(fn, loc) if with_diff else {}

    corpus = _lc.load_corpus() if with_match else None
    ps_fix: set[int] = set()
    fbase = 0
    if corpus is not None:
        ps_fix, code_base = _ps_fix_and_base()
        fbase = addr - code_base       # function start as a code-section offset

    cur_line: int | None = None
    cur: dict | None = None

    def _match_for(norm: bytearray) -> dict | None:
        if corpus is None or len(norm) < _lc.MIN_RUN_BYTES:
            return None
        m = _lc.match_run(bytes(norm).hex(), len(norm), corpus, self_func=fn)
        if m is None:
            return None
        return {
            "nbytes": m.nbytes,
            "n_functions": m.n_functions,
            "suggestions": m.suggestions,          # ALL (JSON)
            "useful": _lc.useful_suggestions(m),    # filtered (text)
        }

    def flush() -> None:
        nonlocal cur
        if cur is None:
            return
        current_line, source, rel = _source_line(loc, cur["orig_line"])
        d = diff_by_line.get(cur["orig_line"] or -1, {})
        groups.append(LineGroup(
            orig_line=cur["orig_line"],
            rel_line=rel,
            current_line=current_line,
            source=source,
            insn_count=cur["count"],
            start_off=cur["start"],
            end_off=cur["end"],
            asm=cur["asm"],
            diff_rows=d.get("rows", 0),
            diff_bytes=d.get("bytes", 0),
            hints=d.get("hints") or None,
            examples=d.get("examples") or None,
            match=_match_for(cur["norm"]),
        ))
        cur = None

    def _new(ins) -> dict:
        return {"orig_line": cur_line, "start": ins.address - addr,
                "end": ins.address - addr, "count": 0, "asm": [],
                "norm": bytearray()}

    for ins in lines:
        if ins.line not in (None, 0):
            if cur is not None and ins.line != cur_line:
                flush()
            cur_line = ins.line
        if cur is None:
            cur = _new(ins)
        elif cur["orig_line"] != cur_line:
            flush()
            cur = _new(ins)
        cur["count"] += 1
        cur["end"] = ins.address - addr + len(ins.bytes_)
        if corpus is not None:
            cur["norm"] += _lc.normalize_insn(
                ins.bytes_, fbase + (ins.address - addr), ps_fix)
        if len(cur["asm"]) < max_asm_per_line:
            text = format_disasm_line(ins, show_lines=False)
            # Drop absolute address; this command already prints function-relative ranges.
            parts = text.split(None, 1)
            cur["asm"].append(parts[1] if len(parts) == 2 else text)
    flush()
    return loc, groups


def line_shape(
    function: Annotated[str, typer.Argument(help="Function name to map")],
    json_out: Annotated[bool, typer.Option("--json", help="Emit machine-readable JSON")] = False,
    max_asm: Annotated[int, typer.Option("--max-asm", help="Max instructions printed per source line")] = 18,
    dense: Annotated[int, typer.Option("--dense", help="Mark source lines with at least this many instructions")] = 8,
    show_source: Annotated[bool, typer.Option("--source", help="Show approximate current-source line by applying original line offset to the checked-in function. This is approximate because decomp files contain extra comments.")] = False,
    with_diff: Annotated[bool, typer.Option("--with-diff/--no-diff", help="Run decomp-verify JSON and annotate each original source-line group with diff rows. Default: on.")] = True,
    with_match: Annotated[bool, typer.Option("--match/--no-match", help="Annotate each line with verified C source that produced the same normalized code elsewhere in the byte-exact corpus (.c2-cache/line-corpus.json, rebuilt automatically by any full `decomp-verify` pass). Default: on.")] = True,
) -> None:
    """Group PS.EXE disassembly by inherited Watcom debug source line."""
    loc, groups = build_line_groups(function, max_asm_per_line=max_asm, with_diff=with_diff, with_match=with_match)
    if with_match and _lc.load_corpus() is None:
        print("note: no line-corpus cache yet; run a full `uv run c2 decomp-verify` "
              "(any whole-project pass) once to build it.\n")
    if json_out:
        print(json.dumps({"function": function, "source": asdict(loc) if loc else None, "groups": [asdict(g) for g in groups]}, indent=2))
        return

    print(f"{function}: PS instruction groups by Watcom -d1 line" + (" + verifier diff" if with_diff else ""))
    if loc:
        rng = f"orig Lines {loc.orig_start}–{loc.orig_end}" if loc.orig_start is not None else "orig Lines ?"
        print(f"source: {loc.file}:{loc.signature_line}  ({rng})")
        print("note: L+N is the original-source-relative line from Watcom debug info; instructions with line=0 inherit the previous L+N.")
    print()
    for g in groups:
        rel = f"L+{g.rel_line}" if g.rel_line is not None else "L?"
        orig = f"orig {g.orig_line}" if g.orig_line is not None else "orig ?"
        cur = f"src~{g.current_line}" if (show_source and g.current_line is not None) else ""
        flags = []
        if g.insn_count >= dense:
            flags.append("DENSE")
        if g.diff_rows:
            hint_s = ", ".join(f"{k}×{v}" for k, v in sorted((g.hints or {}).items()))
            flags.append(f"DIFF {g.diff_bytes}b/{g.diff_rows}r" + (f" [{hint_s}]" if hint_s else ""))
        flag = "  " + "  ".join(flags) if flags else ""
        print(f"{rel:>5}  {orig:<9} {cur:<8}  +0x{g.start_off:04X}..+0x{g.end_off:04X}  {g.insn_count:2} insn{flag}")
        if show_source and g.source:
            print(f"       C~: {g.source.strip()}")
        for a in g.asm:
            print(f"       {a}")
        if g.insn_count > len(g.asm):
            print(f"       ... {g.insn_count - len(g.asm)} more insn")
        if g.examples:
            print("       diff examples:")
            for ex in g.examples:
                print(f"         - {ex}")
        # Text shows only DISTINCTIVE matches (<=3 distinct source forms);
        # generic many-variant runs stay in JSON only.
        if g.match and g.match.get("useful") and len(g.match["useful"]) <= 3:
            useful = g.match["useful"]
            nf = g.match["n_functions"]
            tag = "unique" if len(g.match["suggestions"]) == 1 else f"{nf} fns"
            print(f"       corpus match ({g.match['nbytes']}b, {tag}):")
            for s in useful[:2]:
                loc_s = f"{s['func']} {s['file'].split('/')[-1]}:{s['line']}"
                print(f"         => {s['text']}   [{loc_s}]")
        print()
