"""progress command: print Caesar II decompilation project progress.

Counts every code function in PS.EXE (from symbols.json) and classifies
each as one of:

  ✅ asm-extracted  — has a matching ``PUBLIC name`` in some
                       ``decomp/src/*.asm`` file
  ✅ C-decompiled   — has a ``// FUNCTION: C2 0xADDR`` annotation in
                       some ``decomp/src/*.c`` file
  🚧 C-stubbed      — has a ``// STUB: C2 0xADDR`` annotation
  ⛔ 3rd-party       — declared by Miles AIL / Smacker / sound-driver /
                       Watcom CRT / DOS extender helper, which the
                       project does not aim to recreate
  ❓ untracked       — none of the above (further classified by name
                       prefix in the breakdown)

Optionally cross-references results with the verifier to count
byte-exact matches, the PS-byte footprint of still-diffing bodies,
and the normalized byte-diff total (the same relocation/fixup-aware
comparison used by ``c2 decomp-verify``).

Run from the repo root::

    uv run c2 progress           # quick summary
    uv run c2 progress --verify  # also run decomp-verify byte metrics
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Annotated

import typer


# ── Classifier ───────────────────────────────────────────────────────────────


# Files in the binary's debug-info that belong to 3rd-party libraries.
# Anything attributed to one of these source paths is out-of-scope.
_THIRD_PARTY_FILE_KEYWORDS = (
    "NET\\LIBS",      # Caesar II's NET\LIBS subtree (AIL, Smacker, etc.)
    "AILXMIDI",
    "AILA",
    "AILSSA",
    "SMACKER",
)

# Symbol-name patterns for unattributed (no line-numbers) functions
# that we still want to mark out-of-scope.
_THIRD_PARTY_NAME_PATTERNS = (
    "_Smack",
    "SMACK",
    "_AIL",
    "_SS_",
    "_DIG",
    "_MDI",
    "_XMI",
    "_XDIG",
    "_DLL_",
    "AILXMIDI",
    "LOWSOUND",
    "soundopen",
    "soundnext",
    "soundclose",
    "setuptheframe",
    "gotoframe",
    "blockread",
    "dovoltable",
    "_DoINTR",
    "_API_timer",
    "IO_PARMS",
    "DRIVERS",
    "DETECT_",
    "ENABLE_DEBUG",
)
_THIRD_PARTY_NAME_EXACT = frozenset({
    # CRT / runtime
    "_cstart", "_DLL_load", "_DLL_size", "formstring",
    "remove", "open", "close", "read", "write", "lseek", "sopen",
    "fopen", "fclose", "fread", "fwrite", "fseek", "fprintf",
    "sprintf", "sscanf", "printf", "scanf",
    "malloc", "calloc", "realloc", "free",
    "strcpy", "strcat", "strcmp", "strlen", "strncpy", "strncmp",
    "memcpy", "memset", "memmove", "memcmp",
    "qsort", "rand", "srand", "exit", "atexit",
    "mktime", "asctime", "localtime", "gmtime", "time", "clock",
    "_asctime", "calc_yday",
    "getenv", "setenv",
    "sbrk", "_SplitParms", "RationalAlloc", "FixedPoint_Format",
    "getprintspecs", "parse_offset", "parse_rule", "timeframe",
})


def _looks_third_party(name: str) -> bool:
    if name in _THIRD_PARTY_NAME_EXACT:
        return True
    return any(p in name for p in _THIRD_PARTY_NAME_PATTERNS)


def _looks_crt_helper(name: str) -> bool:
    """Tiny utility helpers Watcom emits (\\__\\* / \\_\\*)."""
    return name.startswith("__") or name in {
        "_dl_term", "_dl_init", "_dl_dput", "_dl_putc",
    }


# ── Data collection ─────────────────────────────────────────────────────────


def _build_function_table(symbols_json: Path) -> tuple[
    list[dict],
    dict[int, int],
    dict[int, set[str]],
]:
    """Return (code_syms, addr_to_size, addr_to_attributed_files).

    Sizes and file-attribution are keyed by the symbol's *address*,
    not its name: PS.EXE has two pairs of distinct functions that
    happen to share a name (``_XMI_write_log`` at 0x80520/0x83670 and
    ``_Alphabet`` at 0x88341/0x883DD), and a name-keyed table would
    silently lose one occurrence of each (a 501-byte under-count of
    ``total_bytes`` and a 474-byte over-count of the third-party /
    untracked buckets that double-count the surviving entry).
    """
    sym = json.loads(symbols_json.read_text())
    code_syms = sorted(
        [s for s in sym["symbols"] if s.get("is_code")],
        key=lambda s: s["address"],
    )
    addr_to_size: dict[int, int] = {}
    for i, s in enumerate(code_syms[:-1]):
        addr_to_size[s["address"]] = code_syms[i + 1]["address"] - s["address"]

    # Attribute each function to source files via line_numbers.
    code_base = sym["memory_map"]["objects"][0]["base_address_int"]
    addr_to_files: dict[int, set[str]] = defaultdict(set)
    for ln in sym.get("line_numbers", []):
        f = ln.get("file") or ""
        if not f:
            continue
        addr = ln["offset"] + code_base
        for i, s in enumerate(code_syms[:-1]):
            if s["address"] <= addr < code_syms[i + 1]["address"]:
                addr_to_files[s["address"]].add(f)
                break

    return code_syms, addr_to_size, addr_to_files


def _collect_asm_publics(src_dir: Path) -> set[str]:
    """Return the set of code-symbol names already extracted as asm."""
    out: set[str] = set()
    pattern = re.compile(r"^PUBLIC\s+(\w+?)_?\s*$", re.MULTILINE)
    for f in sorted(src_dir.glob("*.asm")):
        for m in pattern.finditer(f.read_text(errors="replace")):
            n = m.group(1)
            out.add(n)
            out.add(n + "_")           # try both mangling forms
    return out


def _collect_c_annotations(
    src_dir: Path,
) -> tuple[set[int], set[int], dict[int, str]]:
    """Return (function-marked addresses, stub-marked addresses, addr → filename).

    ``addr_to_file`` maps each annotated address (FUNCTION or STUB) to
    the basename of the ``.c`` file declaring it.  The .c source is
    the authoritative attribution: line_numbers debug info in
    symbols.json is incomplete (a few dozen helper / linker-folded
    aliases have no debug entry), so this lookup lets the progress
    report avoid an `<unknown>` bucket for functions we already
    annotated by hand.
    """
    fn_addrs: set[int] = set()
    stub_addrs: set[int] = set()
    addr_to_file: dict[int, str] = {}
    fn_re = re.compile(r"^// FUNCTION: C2 0x([0-9A-Fa-f]+)", re.MULTILINE)
    stub_re = re.compile(r"^// STUB: C2 0x([0-9A-Fa-f]+)", re.MULTILINE)
    for f in sorted(src_dir.glob("*.c")):
        txt = f.read_text(errors="replace")
        for m in fn_re.finditer(txt):
            addr = int(m.group(1), 16)
            fn_addrs.add(addr)
            addr_to_file.setdefault(addr, f.name)
        for m in stub_re.finditer(txt):
            addr = int(m.group(1), 16)
            stub_addrs.add(addr)
            addr_to_file.setdefault(addr, f.name)
    return fn_addrs, stub_addrs, addr_to_file


# ── Verifier integration (optional) ─────────────────────────────────────────


def _run_verifier(src_dir: Path) -> dict:
    """Run ``c2 decomp-verify --json-summary`` once and aggregate byte metrics.

    Returns a small dict with per-file and total verifier stats.  The
    verifier builds the recompiled exe a single time, walks every
    FUNCTION annotation (plus hand-written asm PUBLICs), and compares
    PS vs RC with the same relocation/fixup-aware byte matcher used by
    ``c2 decomp-verify``.  We keep two separate "remaining" views:

    * ``diff_func_bytes``: PS byte size of functions that are still not
      byte-exact (answers "how many function bytes are still in play?").
    * ``byte_diff``: normalized byte-diff count inside those functions
      (answers "how many individual bytes differ?").
    """
    import json as _json
    import subprocess

    try:
        proc = subprocess.run(
            [
                "uv", "run", "c2", "decomp-verify",
                "--json-summary", "--no-strict",
            ],
            capture_output=True, text=True, timeout=600,
        )
    except Exception:
        return {}

    try:
        doc = _json.loads(proc.stdout)
    except _json.JSONDecodeError:
        return {}

    results: dict[str, dict[str, int]] = {}
    for path, stats in doc.get("files", {}).items():
        # ``files`` always includes a bucket per source file (even ones
        # with only stubs and zero FUNCTION markers).  Skip those so
        # the output matches the legacy per-file loop.
        if stats.get("exact", 0) == 0 and stats.get("diff", 0) == 0:
            continue
        fname = Path(path).name
        results[fname] = {
            "exact": stats.get("exact", 0),
            "diff": stats.get("diff", 0),
            "byte_diff": stats.get("byte_diff", 0),
            "verifier_byte_diff": stats.get("byte_diff", 0),
            "diff_func_bytes": stats.get("diff_func_bytes", 0),
            "exact_func_bytes": stats.get("exact_func_bytes", 0),
            "compared_func_bytes": stats.get("compared_func_bytes", 0),
        }

    summary = doc.get("summary", {})
    totals = {
        "exact": int(summary.get("exact", 0) or 0),
        "diff": int(summary.get("diff", 0) or 0),
        "byte_diff": int(summary.get("byte_diff", 0) or 0),
        "diff_func_bytes": int(summary.get("diff_func_bytes", 0) or 0),
        "exact_func_bytes": int(summary.get("exact_func_bytes", 0) or 0),
        "compared_func_bytes": int(summary.get("compared_func_bytes", 0) or 0),
        "compared_funcs": int(summary.get("compared", 0) or 0),
        "not_found": int(summary.get("not_found", 0) or 0),
    }

    for fn in doc.get("functions", []):
        fname = Path(fn.get("file", "<unknown>")).name
        entry = results.setdefault(fname, {
            "exact": 0,
            "diff": 0,
            "byte_diff": 0,
            "verifier_byte_diff": 0,
            "diff_func_bytes": 0,
            "exact_func_bytes": 0,
            "compared_func_bytes": 0,
        })
        size = int(fn.get("size", 0) or 0)
        diff_bytes = int(fn.get("diff_byte_count", 0) or 0)
        exact = bool(fn.get("exact", False))

        entry["compared_func_bytes"] += size
        totals["compared_func_bytes"] += size
        totals["compared_funcs"] += 1
        if exact:
            entry["exact_func_bytes"] += size
            totals["exact_func_bytes"] += size
        else:
            entry["diff_func_bytes"] += size
            entry["byte_diff"] += diff_bytes
            totals["diff_func_bytes"] += size
            totals["byte_diff"] += diff_bytes

    # Prefer the verifier's function counts (it also accounts for exact-with-
    # note cases); the per-function list is used only to add byte footprints.
    summary = doc.get("summary", {})
    totals["exact"] = int(summary.get("exact", 0) or 0)
    totals["diff"] = int(summary.get("diff", 0) or 0)
    # If the per-function JSON shape ever changes and omits diff rows, fall
    # back to the file-level byte-diff total already supplied by the verifier.
    if totals["byte_diff"] == 0:
        for entry in results.values():
            entry["byte_diff"] = entry.get("verifier_byte_diff", 0)
        totals["byte_diff"] = sum(e["byte_diff"] for e in results.values())

    return {"files": results, "totals": totals}


# ── Output formatting ───────────────────────────────────────────────────────


def _fmt_pct(num: int, denom: int) -> str:
    if denom <= 0:
        return "  -  "
    return f"{100.0 * num / denom:>5.1f}%"


def _fmt_bar(pct: float, width: int = 24) -> str:
    full = int(round(pct / 100.0 * width))
    full = max(0, min(width, full))
    return "█" * full + "░" * (width - full)


# ── Main command ────────────────────────────────────────────────────────────


def progress(
    symbols_json: Annotated[
        Path,
        typer.Option("--symbols", help="Path to symbols.json"),
    ] = Path("data/out/symbols.json"),
    src_dir: Annotated[
        Path,
        typer.Option("--src", help="Decomp source directory"),
    ] = Path("decomp/src"),
    verify: Annotated[
        bool,
        typer.Option(
            "--verify",
            help=(
                "Run decomp-verify and show normalized byte-diff / "
                "diffing-body byte metrics"
            ),
        ),
    ] = False,
    by_file: Annotated[
        bool,
        typer.Option("--by-file", help="Show per-source-file stub breakdown"),
    ] = False,
) -> None:
    """Show project decompilation progress versus PS.EXE."""

    if not symbols_json.exists():
        typer.echo(f"error: {symbols_json} not found", err=True)
        typer.echo("Run 'c2 export data/PS.EXE' first.", err=True)
        raise typer.Exit(1)
    if not src_dir.exists():
        typer.echo(f"error: {src_dir} not found", err=True)
        raise typer.Exit(1)

    code_syms, addr_to_size, addr_to_files = _build_function_table(symbols_json)
    asm_pubs = _collect_asm_publics(src_dir)
    fn_addrs, stub_addrs, src_addr_to_file = _collect_c_annotations(src_dir)

    # Group all aliases by address: PS.EXE has 19 addresses where the
    # linker has folded multiple PUBLICs onto one code body (ICF /
    # tail-merged source functions), plus a handful of CRT/AIL
    # underscore-pair aliases like ``malloc``/``_nmalloc``.  Counting
    # by ``code_syms[:-1]`` would inflate per-bucket bytes by 27
    # alias entries (~935 bytes total).
    addr_to_names: dict[int, list[str]] = defaultdict(list)
    for s in code_syms[:-1]:
        addr_to_names[s["address"]].append(s["name"])

    total_funcs = len(addr_to_size)
    total_bytes = sum(addr_to_size.values())

    # Classify every unique address into exactly one bucket.  When
    # several aliases live at one address we OR-merge their
    # classifications: any alias triggering a stronger bucket promotes
    # the address (e.g. ``malloc``/``_nmalloc`` → third_party because
    # ``malloc`` is in ``_THIRD_PARTY_NAME_EXACT``).
    bucket_funcs: dict[str, list[int]] = defaultdict(list)

    def file_says_third_party(addr: int) -> bool:
        files = addr_to_files.get(addr, set())
        return any(
            kw in f.upper()
            for f in files
            for kw in _THIRD_PARTY_FILE_KEYWORDS
        )

    # Priority order matters: prefer C-decompiled (FUNCTION marker)
    # over asm-extracted (PUBLIC in some src/*.asm), so that if a
    # future fallback `<module>_asm.asm` ever overlaps a function
    # already moved to C, the C decomp wins.  STUB markers are weaker
    # than FUNCTION ones for the same address (shouldn't normally
    # happen, but be safe).
    for addr, names in sorted(addr_to_names.items()):
        if addr in fn_addrs:
            bucket_funcs["c_done"].append(addr)
        elif any(n in asm_pubs for n in names):
            bucket_funcs["asm"].append(addr)
        elif addr in stub_addrs:
            bucket_funcs["c_stub"].append(addr)
        elif file_says_third_party(addr) or any(_looks_third_party(n) for n in names):
            bucket_funcs["third_party"].append(addr)
        elif any(_looks_crt_helper(n) for n in names):
            bucket_funcs["crt_helper"].append(addr)
        else:
            bucket_funcs["untracked"].append(addr)

    def bytes_of(bucket: str) -> int:
        return sum(addr_to_size.get(a, 0) for a in bucket_funcs[bucket])

    asm_b = bytes_of("asm")
    c_done_b = bytes_of("c_done")
    c_stub_b = bytes_of("c_stub")
    third_b = bytes_of("third_party")
    crt_b = bytes_of("crt_helper")
    untracked_b = bytes_of("untracked")

    out_of_scope_b = third_b + crt_b
    in_scope_b = total_bytes - out_of_scope_b - untracked_b
    in_scope_funcs = (
        len(bucket_funcs["asm"])
        + len(bucket_funcs["c_done"])
        + len(bucket_funcs["c_stub"])
    )
    decompiled_b = asm_b + c_done_b
    decompiled_funcs = len(bucket_funcs["asm"]) + len(bucket_funcs["c_done"])

    typer.echo("=" * 78)
    typer.echo(f"Caesar II / PS.EXE — decompilation progress")
    typer.echo("=" * 78)
    typer.echo(f"  Total: {total_funcs} functions, {total_bytes:,} code bytes\n")

    rows: list[tuple[str, str, int, int]] = [
        ("✅ asm-extracted", "asm",         len(bucket_funcs["asm"]),         asm_b),
        ("✅ C-decompiled",  "c_done",      len(bucket_funcs["c_done"]),      c_done_b),
        ("🚧 C-stubbed",     "c_stub",      len(bucket_funcs["c_stub"]),      c_stub_b),
        ("⛔ 3rd-party",     "third_party", len(bucket_funcs["third_party"]), third_b),
        ("⛔ CRT helpers",   "crt_helper",  len(bucket_funcs["crt_helper"]),  crt_b),
        ("❓ untracked",     "untracked",   len(bucket_funcs["untracked"]),   untracked_b),
    ]
    typer.echo(
        f"  {'category':<22} {'funcs':>6} {'bytes':>10} {'pct':>6}"
    )
    typer.echo("  " + "-" * 50)
    for label, _key, n, b in rows:
        typer.echo(
            f"  {label:<22} {n:>6} {b:>10,} {_fmt_pct(b, total_bytes)}"
        )

    typer.echo()
    typer.echo("  In-scope progress (C source, excludes 3rd-party + untracked CRT):")
    typer.echo(
        f"    {decompiled_b:>9,} / {in_scope_b:,} bytes  "
        f"{_fmt_pct(decompiled_b, in_scope_b)} of in-scope  "
        f"{_fmt_bar(100.0 * decompiled_b / max(1, in_scope_b))}"
    )
    typer.echo(
        f"    {decompiled_funcs:>9} / {in_scope_funcs} funcs  "
        f"{_fmt_pct(decompiled_funcs, in_scope_funcs)} of in-scope"
    )
    if not verify:
        typer.echo(
            "    (run with --verify for normalized byte-diff and "
            "diffing-body byte counts)"
        )

    # ── Optional: per-file breakdown of what's still stubbed ────────────────
    if by_file:
        typer.echo()
        typer.echo("=" * 78)
        typer.echo("  Remaining C stubs by source file (largest first)")
        typer.echo("=" * 78)
        per_file: dict[str, dict[str, int]] = defaultdict(
            lambda: {"funcs": 0, "bytes": 0}
        )
        for addr in bucket_funcs["c_stub"]:
            files = addr_to_files.get(addr, set())
            if not files:
                # Fall back to the .c file that declared the STUB
                # (line_numbers debug info is incomplete for some
                # helpers / linker-folded aliases).
                src_file = src_addr_to_file.get(addr)
                files = {src_file} if src_file else {"<unknown>"}
            for f in files:
                per_file[f]["funcs"] += 1
                per_file[f]["bytes"] += addr_to_size.get(addr, 0)
        typer.echo(f"  {'file':<35} {'stubs':>6} {'bytes':>10}")
        typer.echo("  " + "-" * 55)
        for f in sorted(per_file, key=lambda k: -per_file[k]["bytes"]):
            entry = per_file[f]
            display = f.split("\\")[-1] if "\\" in f else f
            typer.echo(
                f"  {display:<35} {entry['funcs']:>6} {entry['bytes']:>10,}"
            )

    # ── Optional: byte-exact verification stats ─────────────────────────────
    if verify:
        typer.echo()
        typer.echo("=" * 78)
        typer.echo("  Byte-exact verification (running decomp-verify) …")
        typer.echo("=" * 78)
        verify_stats = _run_verifier(src_dir)
        results = verify_stats.get("files", {}) if verify_stats else {}
        totals = verify_stats.get("totals", {}) if verify_stats else {}
        if not results:
            typer.echo("  no .c/.asm files with comparison targets found.")
            return

        typer.echo(
            "  (body-bytes = PS size of non-exact functions; "
            "byte-diff = normalized differing bytes)"
        )
        typer.echo(
            f"  {'file':<23} {'exact':>6} {'diff':>5} "
            f"{'body-bytes':>10} {'byte-diff':>10}"
        )
        typer.echo("  " + "-" * 61)
        for fname, stats in sorted(results.items()):
            exact = stats.get("exact", 0)
            diff = stats.get("diff", 0)
            diff_func_bytes = stats.get("diff_func_bytes", 0)
            byte_diff = stats.get("byte_diff", 0)
            typer.echo(
                f"  {fname:<23} {exact:>6} {diff:>5} "
                f"{diff_func_bytes:>10,} {byte_diff:>10,}"
            )
        typer.echo("  " + "-" * 61)
        total_exact = totals.get("exact", 0)
        total_diff = totals.get("diff", 0)
        total_diff_func_bytes = totals.get("diff_func_bytes", 0)
        total_byte_diff = totals.get("byte_diff", 0)
        typer.echo(
            f"  {'TOTAL':<23} {total_exact:>6} {total_diff:>5} "
            f"{total_diff_func_bytes:>10,} {total_byte_diff:>10,}"
        )

        verified = total_exact + total_diff
        if verified > 0:
            pct = 100.0 * total_exact / verified
            typer.echo(
                f"\n  Byte-exact: {total_exact}/{verified} verified "
                f"functions ({pct:.1f}%)  {_fmt_bar(pct)}"
            )

        compared_func_bytes = totals.get("compared_func_bytes", 0)
        exact_func_bytes = totals.get("exact_func_bytes", 0)
        if compared_func_bytes > 0:
            pct_b = 100.0 * exact_func_bytes / compared_func_bytes
            typer.echo(
                f"  Verified body bytes exact: {exact_func_bytes:,}/"
                f"{compared_func_bytes:,} ({pct_b:.1f}%)  {_fmt_bar(pct_b)}"
            )

        remaining_funcs = len(bucket_funcs["c_stub"]) + total_diff
        remaining_func_bytes = c_stub_b + total_diff_func_bytes
        typer.echo("\n  Remaining in-scope work (stubs + verified non-exact bodies):")
        typer.echo(
            f"    functions: {remaining_funcs:,} "
            f"({len(bucket_funcs['c_stub']):,} stubs + {total_diff:,} diffing)"
        )
        typer.echo(
            f"    function bytes: {remaining_func_bytes:,} "
            f"({c_stub_b:,} stub bytes + {total_diff_func_bytes:,} "
            "diffing-body bytes)"
        )
        typer.echo(
            f"    normalized byte diffs inside verified bodies: "
            f"{total_byte_diff:,}"
        )
        if totals.get("not_found", 0):
            typer.echo(
                f"    warning: {totals['not_found']} comparison target(s) "
                "were not found in the recompiled map"
            )


if __name__ == "__main__":
    typer.run(progress)
