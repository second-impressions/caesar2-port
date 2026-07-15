"""Compiler version identification via cross-version comparison.

Two approaches:

  c2 compiler-id codegen
    Compile decompiled .c files with every available Watcom container image,
    parse the resulting .obj (bypassing wlink), and diff per-function bytes
    against the original PS.EXE.  Works even when wlink is broken.

  c2 compiler-id crt
    Extract CRT functions from each version's clib3r.lib, compare byte-for-
    byte against the CRT code embedded in PS.EXE.  Uses the union of LE
    fixup offsets (loader-patched) and OMF fixup offsets (linker-patched)
    to mask relocated bytes.

Both commands produce a matrix: Watcom version × function → match/diff,
making it trivial to identify which compiler built the binary.

See docs/compiler-version-confirmation.md for the results.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Annotated, Optional

import typer

from c2.parsers.omf import extract_omf_lib, parse_obj_functions
from c2.commands.decomp_verify import (
    _load_le_code_and_fixups,
    _strip_stub_bodies,
    _parse_annotations,
    _run_in_container,
    PS_CFLAGS,
)
from c2.commands.c_source import generate_stubs as _generate_stubs_ast

app = typer.Typer(
    help="Identify the Watcom compiler version used to build PS.EXE.",
    no_args_is_help=True,
)

# ── Default container images ─────────────────────────────────────────────────

_DEFAULT_IMAGES: list[tuple[str, str]] = [
    ("9.5", "localhost/watcom-9.5-dosemu2"),
    ("9.5a", "localhost/watcom-9.5a-dosemu2"),
    ("9.5b", "localhost/watcom-9.5b-dosemu2"),
    ("9.5c", "localhost/watcom-9.5c-dosemu2"),
    ("10.0LA", "localhost/watcom-10.0-la-dosemu2"),
    ("10.0GA", "localhost/watcom-10.0-ga-dosemu2"),
    ("10.0a", "localhost/watcom-10.0a-dosemu2"),
    ("10.0b", "localhost/watcom-10.0b-dosemu2"),
    ("10.5", "localhost/watcom-10.5-dosemu2"),
    ("10.6a", "localhost/watcom-10.6a-dosemu2"),
    ("11.0", "localhost/watcom-11.0-dosemu2"),
    ("11.0b", "localhost/watcom-11.0b-dosemu2"),
    ("11.0c", "localhost/watcom-11.0c-dosemu2"),
]


# ── Shared helpers ───────────────────────────────────────────────────────────

def _load_exe_functions(
    exe_path: Path,
    symbols_json: Path,
) -> tuple[bytes, set[int], list[dict], dict[str, int]]:
    """Load PS.EXE code + fixups + symbol table.

    Returns (code_bytes, fixup_set, sorted_code_syms, name_to_addr).
    """
    code, fixups = _load_le_code_and_fixups(exe_path)
    sym_data = json.loads(symbols_json.read_text())
    code_syms = sorted(
        [s for s in sym_data["symbols"] if s["is_code"]],
        key=lambda s: s["offset"],
    )
    # Deduplicate by offset
    seen: set[int] = set()
    deduped: list[dict] = []
    for s in code_syms:
        if s["offset"] not in seen:
            seen.add(s["offset"])
            deduped.append(s)
    vsize = sym_data["memory_map"]["objects"][0]["virtual_size"]
    for i, s in enumerate(deduped):
        s["_end"] = deduped[i + 1]["offset"] if i + 1 < len(deduped) else vsize

    name_to_addr = {s["raw_name"]: s["address"] for s in deduped}
    return code, fixups, deduped, name_to_addr


def _exe_func_bytes(
    addr: int,
    code: bytes,
    fixups: set[int],
    code_syms: list[dict],
    code_base: int = 0x10000,
) -> tuple[bytes | None, set[int] | None]:
    """Extract function bytes + local fixup offsets from PS.EXE."""
    for i, s in enumerate(code_syms):
        if s["address"] == addr:
            end_off = s["_end"]
            off = s["offset"]
            n = end_off - off
            local_fix = {b - off for b in fixups if off <= b < off + n}
            return code[off : off + n], local_fix
    return None, None


def _diff_bytes(
    a: bytes,
    a_fix: set[int],
    b: bytes,
    b_fix: set[int],
) -> tuple[int, int]:
    """Count non-fixup byte differences. Returns (n_diff, n_compared)."""
    n = min(len(a), len(b))
    extra = abs(len(a) - len(b))
    diffs = 0
    for i in range(n):
        if i in a_fix or i in b_fix:
            continue
        if a[i] != b[i]:
            diffs += 1
    return diffs + extra, max(len(a), len(b))


# ── c2 compiler-id codegen ───────────────────────────────────────────────────

@app.command()
def codegen(
    c_file: Annotated[
        Path,
        typer.Argument(help="C source file to compile (default: decomp/src/formulae.c)"),
    ] = Path("decomp/src/formulae.c"),
    symbols_json: Annotated[
        Path,
        typer.Option("--symbols", "-s"),
    ] = Path("data/out/symbols.json"),
    exe_path: Annotated[
        Path,
        typer.Option("--exe"),
    ] = Path("data/PS.EXE"),
    include_dir: Annotated[
        Path,
        typer.Option("--include", help="Include directory for headers"),
    ] = Path("decomp/include"),
    cflags: Annotated[
        str,
        typer.Option("--cflags"),
    ] = PS_CFLAGS,  # proven PS.EXE flags (single source of truth)
    images: Annotated[
        Optional[list[str]],
        typer.Option(
            "--image", "-i",
            help="label:image pairs (e.g. '10.0a:localhost/watcom-10.0a-dosemu2'). "
                 "Repeatable. Default: all dosemu2 images.",
        ),
    ] = None,
) -> None:
    """Compare codegen across Watcom versions by compiling to .obj (no linking).

    Compiles the given C file with every Watcom container image, parses the
    resulting .obj to extract per-function bytes, and diffs against PS.EXE.
    This bypasses wlink entirely — useful when the linker is broken under
    Wine/HX-DOS.

    \\b
    Output: a matrix of version × function showing byte diffs (✓ = exact match).
    The version with all ✓ and lowest total diff is the best candidate.
    """
    if not c_file.exists():
        typer.echo(f"Error: {c_file} not found", err=True)
        raise typer.Exit(1)

    # Parse image list
    image_list: list[tuple[str, str]]
    if images:
        image_list = []
        for spec in images:
            if ":" in spec:
                label, img = spec.split(":", 1)
            else:
                label = spec.rsplit("/", 1)[-1]
                img = spec
            image_list.append((label, img))
    else:
        image_list = list(_DEFAULT_IMAGES)

    typer.echo("Loading PS.EXE …")
    code, fixups, code_syms, name_to_addr = _load_exe_functions(
        exe_path, symbols_json
    )

    # Find FUNCTION-annotated addresses in the source file
    func_addrs, _ = _parse_annotations(c_file)
    func_names_in_exe = {
        s["raw_name"]: s["address"]
        for s in code_syms
        if s["address"] in func_addrs
    }
    typer.echo(
        f"FUNCTION-annotated: {len(func_addrs)}, "
        f"resolved in symbols: {len(func_names_in_exe)}"
    )

    if not func_names_in_exe:
        typer.echo("No functions to compare.")
        raise typer.Exit(1)

    # Header
    func_names = list(func_names_in_exe.keys())
    typer.echo()
    hdr = f"{'Image':<22}"
    for fname in func_names:
        short = fname.rstrip("_")[:7]
        hdr += f" {short:>7}"
    hdr += f" {'TOTAL':>7}"
    typer.echo(hdr)
    typer.echo("-" * len(hdr))

    for label, image in image_list:
        funcs = _compile_obj(c_file, image, cflags, include_dir)
        if funcs is None:
            typer.echo(f"{label:<22} BUILD-FAILED")
            continue
        by_name = {n: (c, f) for n, c, f in funcs}
        row_parts: list[str] = []
        total = 0
        for fname, addr in func_names_in_exe.items():
            if fname not in by_name:
                row_parts.append("   --- ")
                continue
            recomp_code, recomp_fix = by_name[fname]
            exe_code, exe_fix = _exe_func_bytes(
                addr, code, fixups, code_syms
            )
            if exe_code is None:
                row_parts.append("   ??? ")
                continue
            ndiff, _ = _diff_bytes(exe_code, exe_fix, recomp_code, recomp_fix)
            total += ndiff
            if ndiff == 0:
                row_parts.append("     ✓ ")
            else:
                row_parts.append(f"  {ndiff:>4} ")

        typer.echo(f"{label:<22}" + "".join(row_parts) + f"  {total:>5}")

    typer.echo()
    typer.echo('Lower TOTAL = closer codegen match to PS.EXE.')
    typer.echo('"✓" = byte-identical for that function (after fixup masking).')


def _compile_obj(
    c_file: Path,
    image: str,
    cflags: str,
    include_dir: Path | None = None,
) -> list[tuple[str, bytes, set[int]]] | None:
    """Compile a single C file in a container, return parsed .obj functions."""
    work = Path(tempfile.mkdtemp(prefix="c2_cid_"))
    try:
        src = c_file.read_text()
        stripped = _strip_stub_bodies(src)
        (work / c_file.name).write_text(stripped)

        # Copy headers so #includes resolve
        if include_dir and include_dir.is_dir():
            for h in include_dir.glob("*.h"):
                (work / h.name).write_text(h.read_text())

        ok, _ = _run_in_container(
            work, image,
            f"wcc386 {cflags} -fo={c_file.stem}.obj {c_file.name}",
        )
        if not ok:
            return None
        obj = work / f"{c_file.stem}.obj"
        if not obj.exists():
            # HX-DOS writes 8.3 uppercase
            obj = work / f"{c_file.stem.upper()}.OBJ"
        if not obj.exists():
            return None
        return parse_obj_functions(obj)
    finally:
        shutil.rmtree(work, ignore_errors=True)


# ── c2 compiler-id crt ──────────────────────────────────────────────────────


@app.command()
def crt(
    symbols_json: Annotated[
        Path,
        typer.Option("--symbols", "-s"),
    ] = Path("data/out/symbols.json"),
    exe_path: Annotated[
        Path,
        typer.Option("--exe"),
    ] = Path("data/PS.EXE"),
    lib_dir: Annotated[
        Optional[Path],
        typer.Option(
            "--lib-dir",
            help="Directory containing clib3r.lib files named "
                 "'watcom-VERSION_clib3r.lib' or 'cVERSION.lib'.",
        ),
    ] = None,
    libs: Annotated[
        Optional[list[str]],
        typer.Option(
            "--lib",
            help="label:path pairs (e.g. '10.0a:path/to/clib3r.lib'). Repeatable.",
        ),
    ] = None,
) -> None:
    """Compare CRT library functions across Watcom versions against PS.EXE.

    Extracts .obj modules from each clib3r.lib, parses OMF fixup records,
    and compares function bytes against PS.EXE using the union of LE fixups
    (loader-patched) and OMF fixups (linker-patched) as the relocation mask.

    \\b
    Supply libraries via --lib-dir (auto-discovers files) or --lib (explicit).
    Output: a matrix of version × CRT function showing ✓ for exact match.
    """
    typer.echo("Loading PS.EXE …")
    code, fixups, code_syms, name_to_addr = _load_exe_functions(
        exe_path, symbols_json
    )
    # Build raw_name → sym lookup
    sym_by_raw = {s["raw_name"]: s for s in code_syms}

    # Build library catalogue
    lib_catalogue: list[tuple[str, Path]] = []
    if libs:
        for spec in libs:
            if ":" in spec:
                label, path = spec.split(":", 1)
            else:
                label = Path(spec).stem
                path = spec
            lib_catalogue.append((label, Path(path)))
    elif lib_dir and lib_dir.is_dir():
        for f in sorted(lib_dir.iterdir()):
            if f.suffix.lower() == ".lib":
                lib_catalogue.append((f.stem, f))
    else:
        typer.echo(
            "Error: provide --lib-dir or --lib. "
            "Example: c2 compiler-id crt --lib-dir ./libs/",
            err=True,
        )
        raise typer.Exit(1)

    if not lib_catalogue:
        typer.echo("No libraries found.", err=True)
        raise typer.Exit(1)

    # Index each library
    typer.echo("Building lib indices …")
    lib_indices: dict[str, dict[str, tuple[bytes, set[int]]]] = {}
    for label, lib_path in lib_catalogue:
        typer.echo(f"  {label} … ", nl=False)
        idx = _index_lib(lib_path)
        lib_indices[label] = idx
        typer.echo(f"{len(idx)} funcs")

    versions = [label for label, _ in lib_catalogue]

    # Auto-discover all CRT functions: any function name that appears
    # in BOTH PS.EXE symbols AND at least one library index.
    all_lib_names: set[str] = set()
    for idx in lib_indices.values():
        all_lib_names.update(idx.keys())

    targets: list[tuple[str, str]] = []  # (display_name, raw_name)
    for raw_name, sym in sorted(sym_by_raw.items(), key=lambda kv: kv[1]["offset"]):
        if raw_name in all_lib_names:
            display = raw_name.rstrip("_")
            targets.append((display, raw_name))

    typer.echo(f"\nFound {len(targets)} CRT functions in PS.EXE matching library exports.")
    if not targets:
        typer.echo("No matching functions found.")
        raise typer.Exit(1)

    # Comparison
    scores: dict[str, list[int]] = {v: [0, 0] for v in versions}
    exact_rows: list[tuple[str, int, dict[str, bool | None]]] = []
    diff_rows: list[tuple[str, int, str]] = []

    for display, raw_name in targets:
        sym = sym_by_raw[raw_name]
        exe_code, exe_fix = _exe_func_bytes(
            sym["address"], code, fixups, code_syms
        )
        if exe_code is None:
            continue

        row_exact: dict[str, bool | None] = {}
        any_match = False
        for v in versions:
            idx = lib_indices[v]
            hit = idx.get(raw_name)
            if hit is None:
                row_exact[v] = None
                continue
            lib_code, lib_fix = hit
            ndiff, _ = _diff_bytes(exe_code, exe_fix, lib_code, lib_fix)
            scores[v][1] += 1
            if ndiff == 0:
                scores[v][0] += 1
                row_exact[v] = True
            else:
                row_exact[v] = False
            any_match = True

        if any_match:
            exact_rows.append((display, len(exe_code), row_exact))

    # Print results — show all functions, with ✓/✗/? per version
    # Determine column width
    name_w = max(len(d) for d, _, _ in exact_rows) + 1 if exact_rows else 12
    name_w = max(name_w, 12)

    hdr = f"{'Function':<{name_w}} {'bytes':>5}"
    for v in versions:
        hdr += f" {v:>7}"
    typer.echo(hdr)
    typer.echo("-" * len(hdr))

    for display, size, row_exact in exact_rows:
        row = f"{display:<{name_w}} {size:>5}"
        for v in versions:
            val = row_exact.get(v)
            if val is None:
                row += f"  {'·':>5}"
            elif val:
                row += f"    {'✓':>3}"
            else:
                row += f"    {'✗':>3}"
        typer.echo(row)

    # Summary
    typer.echo("-" * len(hdr))
    summary = f"{'EXACT':<{name_w + 6}}"
    for v in versions:
        e, t = scores[v]
        summary += f" {e:>3}/{t:<3}"
    typer.echo(summary)
    typer.echo()
    typer.echo("✓ = byte-identical after masking LE + OMF fixups.")
    typer.echo("✗ = bytes differ.  · = function not in that library.")
    typer.echo("Highest EXACT count = best CRT version match.")


def _index_lib(
    lib_path: Path,
) -> dict[str, tuple[bytes, set[int]]]:
    """Extract and parse all .obj modules from a library."""
    index: dict[str, tuple[bytes, set[int]]] = {}
    with tempfile.TemporaryDirectory() as td:
        extract_omf_lib(lib_path, td)
        for obj_file in Path(td).glob("*.obj"):
            try:
                funcs = parse_obj_functions(obj_file)
                for name, code_bytes, fset in funcs:
                    index[name] = (code_bytes, fset)
            except Exception:
                pass
    return index
