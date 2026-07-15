"""Lint command for Rule 63 (row-cache) source-shape regressions.

Codifies the heuristic findings from the entity-row-cache sweep (commits
84aee2c..873a618) so future decomp/source changes can't silently reintroduce
the anti-pattern.

Classification (heuristic, fast):

  ENTITY_CACHE      `<var> = &<entity_array>[<index>]` — Rule 63 REVERSE.
                    PS uses inline SIB+disp32 access; the cache forces an
                    extra callee-save register.  Removing the cache and
                    rewriting `<var>->field` to `<array>[<index>].field`
                    typically closes 10-200 bytes.  WARNS.

                    Entity arrays: figure_list, unit_list, army_list,
                    arrow_list, citizen_list.

  WHOLE_MAP_CACHE   `<var> = <map_array>` (no index) — Rule 63 REVERSE.
                    PS uses inline absolute access to map_array[K] every
                    site; the cache pins the base in a callee-save reg.
                    Removing typically closes 50-200 bytes.  WARNS.

  MAP_ROW_CACHE     `<var> = &<map_array>[<row_offset>]` — Rule 63 FORWARD.
                    PS DOES cache row pointers in tight neighbour loops
                    (city_map/region_map/battle_map cells are small/dense).
                    Leaving the cache is correct.  OK.

  TABLE_CACHE       `<var> = &<other_table>[<index>]` (e.g. mice, frame).
                    Direction depends on table size and access density.
                    WARNS (probable reverse) for known-bad tables; OK
                    otherwise.

`--verify` actually removes each warned cache (via the same scratch-tree
mechanism the sweep scripts used) and reports the byte-diff delta from
`decomp-verify`.  Empirical confirmation of the heuristic.
"""

from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import typer

from c2.commands.row_caches import (
    INTERESTING_ARRAYS,
    Hit,
    _scan_file,
)


ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = ROOT / "decomp" / "src"

ENTITY_ARRAYS = {
    "figure_list",
    "unit_list",
    "army_list",
    "arrow_list",
    "citizen_list",
}

MAP_ARRAYS = {
    "city_map",
    "region_map",
    "battle_map",
    "pseudo_map",
}

# Other tables empirically confirmed Rule 63 REVERSE (cache hurts).
KNOWN_BAD_TABLE_CACHES = {
    "mice",
}


@dataclass
class Finding:
    hit: Hit
    classification: str          # ENTITY_CACHE | WHOLE_MAP_CACHE | MAP_ROW_CACHE | TABLE_CACHE
    severity: str                # warn | ok
    note: str
    verify_delta: int | None = None   # bytes reduced when cache removed (if --verify)


def _classify(h: Hit) -> tuple[str, str, str]:
    """Return (classification, severity, note)."""
    arr = h.array
    # Whole-map cache: pattern is `var = <map_array>` (no index).
    # Our scanner records these as offset-add when index is `0` / expr is empty;
    # if uses are very low and there's no index expression, treat as whole-map.
    # The scanner only emits hits with a non-trivial expression, so whole-map
    # caches with no index are NOT picked up by the AST scanner — those need a
    # separate regex pass.  Here we only see indexed caches.
    if arr in ENTITY_ARRAYS:
        return (
            "ENTITY_CACHE",
            "warn",
            f"Rule 63 reverse: drop cache, rewrite `{h.var}->field` to "
            f"`{arr}[{h.expr}].field`",
        )
    if arr in MAP_ARRAYS:
        # Map row cache — Rule 63 FORWARD, leave it.
        return (
            "MAP_ROW_CACHE",
            "ok",
            "Rule 63 forward (map row cache) — PS source likely has this cache",
        )
    if arr in KNOWN_BAD_TABLE_CACHES:
        return (
            "TABLE_CACHE",
            "warn",
            f"Rule 63 reverse: empirically confirmed for {arr}; "
            f"rewrite `{h.var}[K]` to `{arr}[{h.expr} + K]`",
        )
    return (
        "TABLE_CACHE",
        "ok",
        "unknown table — direction not classified",
    )


# ---------------------------------------------------------------------------
# Whole-map cache scanner (regex; AST scanner skips these because the RHS
# has no index).
# ---------------------------------------------------------------------------

_WHOLE_MAP_RE = re.compile(
    rf"^(?P<indent>[ \t]*)"
    rf"(?:unsigned\s+char|char|void)\s*\*+\s*"
    rf"(?P<var>\w+)\s*=\s*"
    rf"(?P<arr>{'|'.join(MAP_ARRAYS)})\s*;",
    re.M,
)


def _scan_whole_map_caches(path: Path) -> list[Hit]:
    """Find `unsigned char *X = <map_array>;` (no index) declarations."""
    out: list[Hit] = []
    text = path.read_text(errors="replace")
    # Find enclosing function for each match
    fn_defs = list(re.finditer(
        r"^(?:int|void|char|unsigned\s+char|short|unsigned\s+short)\s+(\w+)\s*\([^)]*\)\s*\{",
        text, re.M,
    ))
    for m in _WHOLE_MAP_RE.finditer(text):
        line = text[: m.start()].count("\n") + 1
        # Find enclosing function
        fn_name = "?"
        for fd in fn_defs:
            if fd.start() < m.start():
                fn_name = fd.group(1)
            else:
                break
        out.append(Hit(
            file=path,
            line=line,
            function=fn_name,
            var=m.group("var"),
            array=m.group("arr"),
            expr="",  # no index → whole-map cache
            uses=0,
            kind="decl:whole-map",
        ))
    return out


def _classify_whole_map(h: Hit) -> tuple[str, str, str]:
    return (
        "WHOLE_MAP_CACHE",
        "warn",
        f"Rule 63 reverse: drop `unsigned char *{h.var} = {h.array};` and "
        f"inline `{h.array}[K]` at every use site",
    )


# ---------------------------------------------------------------------------
# Optional --verify: empirically test each warning by removing the cache and
# running c2 decomp-verify on the affected function.
# ---------------------------------------------------------------------------

def _baseline_diff(file: Path, fn: str) -> int | None:
    r = subprocess.run(
        ["uv", "run", "c2", "decomp-verify", str(file), "-f", fn, "--no-strict"],
        capture_output=True, text=True, timeout=240,
    )
    if "✓" in r.stdout:
        return 0
    m = re.search(r"(\d+) byte diff", r.stdout)
    return int(m.group(1)) if m else None


def _try_remove_entity_cache(file: Path, fn: str, var: str, arr: str, idx: str) -> int | None:
    src = file.read_text()
    # Locate function body
    fn_m = re.search(rf"^(?:int|void|char|unsigned\s+char)\s+{re.escape(fn)}\b[^{{]*{{", src, re.M)
    if not fn_m:
        return None
    start = fn_m.start()
    depth = 0; end = start; started = False
    for i in range(fn_m.end()-1, len(src)):
        if src[i] == "{": depth += 1; started = True
        elif src[i] == "}":
            depth -= 1
            if started and depth == 0: end = i+1; break
    body = src[start:end]
    idx_esc = re.escape(idx)
    # Match decl + assign forms
    decl_pat = re.compile(
        rf"^([ \t]*)(?:struct\s+\w+|unsigned\s+char|char|int|void)\s*\*+\s*{re.escape(var)}\s*="
        rf"\s*&?{re.escape(arr)}\s*\[\s*{idx_esc}\s*\]\s*;\s*\n", re.M,
    )
    new_body, n1 = decl_pat.subn("", body)
    assign_pat = re.compile(
        rf"^([ \t]*){re.escape(var)}\s*=\s*&?{re.escape(arr)}\s*\[\s*{idx_esc}\s*\]\s*;\s*\n", re.M,
    )
    new_body, n2 = assign_pat.subn("", new_body)
    if n1 + n2 == 0:
        return None
    new_body = re.sub(rf"\b{re.escape(var)}->", f"{arr}[{idx}].", new_body)
    # Drop unused decl if any
    if not re.search(rf"\b{re.escape(var)}\b", new_body):
        new_body = re.sub(
            rf"^[ \t]*(?:struct\s+\w+|unsigned\s+char|char|int|void)\s*\*+\s*{re.escape(var)}\s*;\s*\n",
            "", new_body, flags=re.M,
        )
    file.write_text(src[:start] + new_body + src[end:])
    return _baseline_diff(file, fn)


def _try_remove_whole_map(file: Path, fn: str, var: str, arr: str) -> int | None:
    src = file.read_text()
    fn_m = re.search(rf"^(?:int|void|char|unsigned\s+char)\s+{re.escape(fn)}\b[^{{]*{{", src, re.M)
    if not fn_m:
        return None
    start = fn_m.start()
    depth = 0; end = start; started = False
    for i in range(fn_m.end()-1, len(src)):
        if src[i] == "{": depth += 1; started = True
        elif src[i] == "}":
            depth -= 1
            if started and depth == 0: end = i+1; break
    body = src[start:end]
    pat = re.compile(
        rf"^[ \t]*(?:unsigned\s+char|char|void)\s*\*+\s*{re.escape(var)}\s*=\s*"
        rf"{re.escape(arr)}\s*;\s*\n", re.M,
    )
    new_body, n = pat.subn("", body)
    if n == 0: return None
    # Replace `var[X]` with `arr[X]`
    new_body = re.sub(rf"\b{re.escape(var)}\[", f"{arr}[", new_body)
    # `var + X` → `&arr[X]` (less common; skip)
    file.write_text(src[:start] + new_body + src[end:])
    return _baseline_diff(file, fn)


# ---------------------------------------------------------------------------
# Main CLI
# ---------------------------------------------------------------------------

def lint_row_caches(
    path: Path = typer.Argument(SRC_DIR, help="Source file or directory"),
    verify: bool = typer.Option(False, "--verify", help="Empirically test each warning by removing the cache (slow)"),
    only_warn: bool = typer.Option(False, "--warn-only", help="Suppress OK rows"),
    json_out: bool = typer.Option(False, "--json", help="Emit JSON instead of table"),
    fail_on_warn: bool = typer.Option(False, "--fail", help="Exit 1 if any warnings"),
) -> None:
    """Lint Rule 63 (row-cache) source-shape regressions.

    Classifies every entity / map / table row-cache in the C source as
    likely Rule 63 REVERSE (warn) or Rule 63 FORWARD (ok), based on the
    empirical findings catalogued in docs/watcom-codegen-patterns.md.
    """
    path = path.resolve()
    files = [path] if path.is_file() else sorted(path.glob("*.c"))

    findings: list[Finding] = []
    arrays = set(INTERESTING_ARRAYS) | KNOWN_BAD_TABLE_CACHES

    # Indexed caches (AST scanner)
    for f in files:
        for h in _scan_file(f, arrays, min_uses=1):
            cls, sev, note = _classify(h)
            findings.append(Finding(h, cls, sev, note))
        # Whole-map caches (regex scanner)
        for h in _scan_whole_map_caches(f):
            cls, sev, note = _classify_whole_map(h)
            findings.append(Finding(h, cls, sev, note))

    # Verify (slow): for each warning, actually remove the cache and measure.
    if verify:
        warns = [fd for fd in findings if fd.severity == "warn"]
        typer.echo(f"# Verifying {len(warns)} warnings (this may take {len(warns)*20}s+)…", err=True)
        for fd in warns:
            h = fd.hit
            orig = h.file.read_text()
            baseline = _baseline_diff(h.file, h.function)
            if baseline is None:
                fd.verify_delta = None
                continue
            if fd.classification == "WHOLE_MAP_CACHE":
                new = _try_remove_whole_map(h.file, h.function, h.var, h.array)
            else:
                new = _try_remove_entity_cache(h.file, h.function, h.var, h.array, h.expr)
            h.file.write_text(orig)
            if new is None:
                fd.verify_delta = None
            else:
                fd.verify_delta = baseline - new   # positive = improvement
                if fd.verify_delta <= 0:
                    fd.note += f" (verify: Δ={fd.verify_delta:+d} — heuristic false positive)"
                    fd.severity = "ok-verified"

    # Filter / sort
    if only_warn:
        findings = [fd for fd in findings if fd.severity == "warn"]
    findings.sort(key=lambda fd: (
        0 if fd.severity == "warn" else 1,
        -(fd.verify_delta or 0),
        str(fd.hit.file),
        fd.hit.line,
    ))

    # Output
    if json_out:
        import json as _json
        out = []
        for fd in findings:
            h = fd.hit
            out.append({
                "file": str(h.file.relative_to(ROOT)),
                "line": h.line,
                "function": h.function,
                "var": h.var,
                "array": h.array,
                "expr": h.expr,
                "kind": h.kind,
                "uses": h.uses,
                "classification": fd.classification,
                "severity": fd.severity,
                "note": fd.note,
                "verify_delta": fd.verify_delta,
            })
        typer.echo(_json.dumps({"findings": out, "summary": {
            "total": len(out),
            "warnings": sum(1 for fd in findings if fd.severity == "warn"),
        }}, indent=2))
    else:
        n_warn = sum(1 for fd in findings if fd.severity == "warn")
        cols = "sev   classification    uses  delta  file:line                          function                         var      array"
        if verify:
            pass
        typer.echo(cols)
        typer.echo("-" * 140)
        for fd in findings:
            h = fd.hit
            sev_disp = {
                "warn": typer.style("warn", fg=typer.colors.YELLOW),
                "ok":   typer.style("ok  ", fg=typer.colors.GREEN),
                "ok-verified": typer.style("okV ", fg=typer.colors.CYAN),
            }.get(fd.severity, fd.severity)
            loc = f"{h.file.relative_to(ROOT)}:{h.line}"
            delta = f"{fd.verify_delta:+5d}" if fd.verify_delta is not None else "   - "
            typer.echo(
                f"{sev_disp:>4}  {fd.classification:18} {h.uses:4d}  {delta:>5}  "
                f"{loc:34} {h.function:32} {h.var:8} {h.array}"
            )
            if fd.severity == "warn":
                typer.echo(f"      → {fd.note}")
        typer.echo()
        typer.echo(f"summary: {n_warn} warning(s), {len(findings) - n_warn} ok")

    if fail_on_warn and any(fd.severity == "warn" for fd in findings):
        sys.exit(1)
