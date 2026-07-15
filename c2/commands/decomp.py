"""Decomp command: generate the 8 C2 hand-written .asm files.

The `c2 decomp` command regenerates only the assembly modules that the
original C2 source tree contained as hand-written `.asm` files
(library, sprites, dia_ptrs, dialarga, dialargb, dia_medi, dia_smal,
palet).
Everything else (Watcom CRT, Miles, Smacker, the C game code) lives
elsewhere:

  * The Watcom CRT is provided directly by `clib3r.lib` linked from
    the toolchain image — no need to re-extract per-function .asm.
  * Miles (AIL) and RAD Smacker bodies were never assembled by us;
    we link against pre-built objects only when needed.
  * C2 game C code is hand-written in `decomp/src/*.c` (and the build
    is wired by `c2 decomp-verify` directly).

The regenerated .asm files are written to `decomp/src/*.asm` and use:
  * Real WASM mnemonics (capstone-decoded), with byte-level db fallback
    for encodings WASM 10.0a can't reproduce.
  * Per-function relative labels (`<funcname>L<N>`) instead of
    address-derived `L_005AC6`-style names — stable across re-link.
  * No post-link banner (`; offset: 0x..., size: N bytes`) — the
    address is a relocation artefact, not source.

  decomp/
    original/          — extracted LE binaries (le_code.bin, le_data.bin)
    src/*.asm          — the 8 C2 hand-written assembly modules
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Optional

import typer


# ── Main command ─────────────────────────────────────────────────────────────


def decomp(
    symbols_json: Annotated[
        Path,
        typer.Argument(help="Path to symbols.json (from 'c2 export')"),
    ],
    exe_path: Annotated[
        Path,
        typer.Option("--exe", help="Path to PS.EXE"),
    ],
    output_dir: Annotated[
        Optional[Path],
        typer.Option("--output", "-o", help="Output directory (default: decomp/)"),
    ] = None,
    force: Annotated[
        bool,
        typer.Option("--force", "-f", help="Overwrite existing generated files"),
    ] = False,
) -> None:
    """Generate decompilation scaffold from symbols.json + PS.EXE.

    Produces per-module .asm files with db bytes (byte-identical build)
    and Capstone disassembly comments (readable reference).
    """
    if not symbols_json.exists():
        typer.echo(f"Error: {symbols_json} not found", err=True)
        typer.echo("Run 'c2 export data/PS.EXE' first to generate it.", err=True)
        raise typer.Exit(1)
    if not exe_path.exists():
        typer.echo(f"Error: {exe_path} not found", err=True)
        raise typer.Exit(1)

    data = json.loads(symbols_json.read_text())
    out = output_dir or Path("decomp")

    typer.echo(f"Reading {symbols_json}...")
    typer.echo(f"Output directory: {out}")
    typer.echo(
        "Mode: asm-only (regenerating the 8 C2 hand-written "
        ".asm modules; CRT/Miles/Smacker/C come from elsewhere)"
    )

    # ── Parse EXE ────────────────────────────────────────────────────
    from c2.parsers.exe import extract_le_objects, parse_exe

    _mz, _bw, le = parse_exe(exe_path)

    # ── Extract LE objects ───────────────────────────────────────────
    orig_dir = out / "original"
    orig_dir.mkdir(parents=True, exist_ok=True)

    code_bin_path = orig_dir / "le_code.bin"
    data_bin_path = orig_dir / "le_data.bin"

    if not code_bin_path.exists() or force:
        typer.echo(f"Extracting LE objects from {exe_path}...")
        extract_le_objects(exe_path, le, orig_dir)
        typer.echo("  Extracted le_code.bin and le_data.bin")

    # ── Load binary data ─────────────────────────────────────────────
    from c2.commands.genasm import _pad_or_trim

    objects = data["memory_map"]["objects"]
    code_vsize = objects[0]["virtual_size"]
    data_vsize = objects[1]["virtual_size"]

    code_bin = _pad_or_trim(code_bin_path.read_bytes(), code_vsize)
    data_bin = _pad_or_trim(data_bin_path.read_bytes(), data_vsize)
    typer.echo(f"  Code: {len(code_bin)} bytes, Data: {len(data_bin)} bytes")

    # ── Parse LE fixups ──────────────────────────────────────────────
    from c2.commands.fixups import parse_le_fixups

    typer.echo("Parsing LE fixup records...")
    code_fixup_map, data_fixup_map = parse_le_fixups(
        exe_path, le.le_offset, le.page_size, le.num_pages,
        le.objects[0].num_pages, le.objects[1].num_pages,
    )
    typer.echo(f"  {len(code_fixup_map)} code fixups, {len(data_fixup_map)} data fixups")

    # ── Build symbol tables ──────────────────────────────────────────
    from c2.commands.genasm import (
        build_symbol_name_map,
        generate_module_asm,
    )

    code_syms = [s for s in data["symbols"] if s["is_code"]]
    data_syms = [s for s in data["symbols"] if s["is_data"]]
    code_sym_names = build_symbol_name_map(code_syms)
    data_sym_names = build_symbol_name_map(data_syms)

    typer.echo(f"  {len(code_syms)} code symbols, {len(data_syms)} data symbols")

    # ── Group symbols by module, compute function boundaries ─────────
    modules = {m["index"]: m for m in data["modules"]}
    # Deduplicate: keep one symbol per offset (skip aliases)
    all_code_syms = sorted(code_syms, key=lambda s: s["offset"])
    deduped_syms: list[dict] = []
    seen_offsets: set[int] = set()
    for s in all_code_syms:
        if s["offset"] not in seen_offsets:
            seen_offsets.add(s["offset"])
            deduped_syms.append(s)

    for i, s in enumerate(deduped_syms):
        s["_end"] = deduped_syms[i + 1]["offset"] if i + 1 < len(deduped_syms) else code_vsize

    mod_funcs: dict[int, list[dict]] = {}
    for s in deduped_syms:
        mod_funcs.setdefault(s["module_index"], []).append(s)

    # ── Precompute synthetic code labels needed globally ──────────────
    # Any fixup targeting a code offset without a debug symbol needs a
    # synthetic label.  We assign each to the module that owns that range.
    from c2.commands.genasm import _build_fixup_occupied_set

    data_fixup_occupied = _build_fixup_occupied_set(data_fixup_map)
    synthetic_code_labels: dict[int, str] = {}  # offset → name
    force_public_code: set[int] = set()  # code offsets that must be PUBLIC

    for _off, (tgt_obj, tgt_offset) in code_fixup_map.items():
        if tgt_obj == 1 and tgt_offset not in code_sym_names:
            synthetic_code_labels.setdefault(tgt_offset, f"_code_{tgt_offset:06X}")
    # Data fixups targeting code: need PUBLIC (may be cross-module)
    for _off, (tgt_obj, tgt_offset) in data_fixup_map.items():
        if tgt_obj == 1:
            force_public_code.add(tgt_offset)
            if tgt_offset not in code_sym_names:
                synthetic_code_labels.setdefault(tgt_offset, f"_code_{tgt_offset:06X}")
    # Code fixups targeting code in other modules also need PUBLIC
    for _off, (tgt_obj, tgt_offset) in code_fixup_map.items():
        if tgt_obj == 1:
            force_public_code.add(tgt_offset)

    # Merge synthetics into the global code-name map
    code_sym_names.update(synthetic_code_labels)

    # ── Categorize modules ────────────────────────────────────────────
    # We only need to know which modules are the 8 hand-written C2 .asm
    # files; everything else is skipped.  (palet.ASM: the VGA DAC loader
    # `_PaletteSet` — game-side asm, recovered 2026-07 for the PS2 build.)
    c2_asm_names = {'library.asm', 'sprites.asm', 'dia_ptrs.asm',
                    'dialarga.asm', 'dialargb.asm', 'dia_medi.asm',
                    'dia_smal.asm', 'palet.ASM'}
    c2_asm_indices: set[int] = set()
    for m in data["modules"]:
        if m["name"] in c2_asm_names:
            c2_asm_indices.add(m["index"])

    # ── Create directory structure ────────────────────────────────────
    src_dir = out / "src"
    src_dir.mkdir(parents=True, exist_ok=True)

    def _should_write(path: Path) -> bool:
        return force or not path.exists()

    # ── Generate the 8 C2 .asm modules ───────────────────────────────
    typer.echo("\nGenerating modules...")

    c2_asm_count = 0
    for mod_idx in sorted(c2_asm_indices):
        mod = modules[mod_idx]
        funcs = mod_funcs.get(mod_idx, [])
        if not funcs:
            continue
        mod_name = mod["name"].rsplit("\\", 1)[-1]
        base_name = mod_name.rsplit(".", 1)[0]

        # Synthetic labels in this module's address range
        chunk_start = funcs[0]["offset"]
        chunk_end = funcs[-1]["_end"]
        chunk_syn = {off: name for off, name in synthetic_code_labels.items()
                     if chunk_start <= off < chunk_end}

        asm_path = src_dir / f"{base_name}.asm"
        if _should_write(asm_path):
            # The seven C2 modules were written in WASM, whose reg-reg
            # encoding direction matches the binary — skip the db
            # fallback.  palet.ASM's bytes use the OPPOSITE direction
            # bit (8B/33/8A forms): it was assembled with MASM/TASM
            # (RAD SDK support code), so WASM re-encoding diverges and
            # those instructions need the byte-exact db fallback.
            asm_text = generate_module_asm(
                code_bin, funcs, code_fixup_map,
                code_sym_names, data_sym_names,
                data_fixup_map,
                extra_labels=chunk_syn,
                force_public=force_public_code,
                skip_regreg_check=(mod_name != "palet.ASM"),
            )
            asm_path.write_text(asm_text)
            c2_asm_count += 1
            typer.echo(f"  src/{base_name}.asm: {len(funcs)} functions")
        else:
            typer.echo(
                f"  src/{base_name}.asm: skipped (use --force to overwrite)"
            )

    # ── Summary ──────────────────────────────────────────────────────
    typer.echo(f"\n{'=' * 60}")
    typer.echo(f"Generated {c2_asm_count} C2 .asm file(s) in {src_dir}/")
    typer.echo(f"{'=' * 60}")
    typer.echo("")
    typer.echo("Next step:")
    typer.echo("  uv run c2 decomp-verify   # assemble + link + byte-compare")
