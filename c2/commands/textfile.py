"""textfile command group: inspect, export, and assemble Caesar II Textfile binaries.

Sub-commands
------------
show      Parse and display a binary Textfile (C2.ENG / C2.GER / …).
export    Transpile a binary Textfile to an editable TOML representation.
assemble  Reassemble a TOML representation back to a binary Textfile.

Round-trip guarantee
--------------------
``assemble(export(file))`` produces a byte-for-byte identical binary when the
TOML has not been modified.  Aliased groups (multiple offset-table entries that
share the same string data) are preserved via the ``alias_of`` key.
"""

from __future__ import annotations

import sys
import tomllib
from pathlib import Path
from typing import Annotated

import tomli_w
import typer

from c2.parsers.textfile import ENCODING, GAME_BUFFER_LIMIT, TextFile, parse, serialise

# ── Typer sub-application ─────────────────────────────────────────────────────

app = typer.Typer(
    name="textfile",
    help="Inspect, export, and assemble Caesar II Textfile binaries (.ENG/.GER/…).",
    no_args_is_help=True,
)

# ── TOML schema helpers ───────────────────────────────────────────────────────

_TOML_COMMENT_HEADER = """\
# Caesar II Textfile — TOML representation
#
# Encoding: all strings are stored as Unicode (decoded from CP437).
#           On assemble they are re-encoded to CP437.
#
# Aliasing: when multiple group indices share the same string data in the
#           binary file, only the first index carries the "strings" key.
#           Subsequent indices use "alias_of = <first_index>" instead.
#           This is required for a byte-identical round-trip.

"""


def _textfile_to_toml_doc(tf: TextFile, source_name: str) -> dict:
    """Convert a ``TextFile`` to a plain dict suitable for ``tomli_w.dumps``."""

    # Map id(group_list) → first group index that owns it (for alias detection)
    id_to_first_index: dict[int, int] = {}

    groups_list: list[dict] = []

    for i, group in enumerate(tf.groups):
        if i == 0:
            # Null sentinel — always omitted from the TOML groups array;
            # the assembler always inserts it automatically.
            continue

        gid = id(group)
        if gid in id_to_first_index:
            # Aliased entry
            groups_list.append({"index": i, "alias_of": id_to_first_index[gid]})
        else:
            id_to_first_index[gid] = i
            strings = [s.decode(ENCODING) for s in group]
            groups_list.append({"index": i, "strings": strings})

    return {
        "meta": {
            "source": source_name,
            "num_groups": tf.num_groups,
            "encoding": ENCODING,
        },
        "groups": groups_list,
    }


def _toml_doc_to_textfile(doc: dict, toml_path: Path) -> TextFile:
    """Reconstruct a ``TextFile`` from a parsed TOML document.

    Raises ``ValueError`` with a descriptive message on any schema violation.
    """
    meta = doc.get("meta", {})
    num_groups: int = meta.get("num_groups", 0)
    if not isinstance(num_groups, int) or num_groups < 1:
        raise ValueError(
            f"{toml_path}: meta.num_groups must be a positive integer, "
            f"got {num_groups!r}"
        )

    raw_groups = doc.get("groups", [])
    if not isinstance(raw_groups, list):
        raise ValueError(f"{toml_path}: 'groups' must be a TOML array of tables")

    # Build a lookup: group_index → entry dict
    by_index: dict[int, dict] = {}
    for entry in raw_groups:
        if not isinstance(entry, dict):
            raise ValueError(f"{toml_path}: each [[groups]] entry must be a table")
        idx = entry.get("index")
        if not isinstance(idx, int):
            raise ValueError(
                f"{toml_path}: [[groups]] entry missing integer 'index' key"
            )
        if idx in by_index:
            raise ValueError(
                f"{toml_path}: duplicate group index {idx} in [[groups]]"
            )
        by_index[idx] = entry

    # Reconstruct the groups list (index 0 = null sentinel)
    groups: list[list[bytes]] = [[]]  # index 0 always empty

    # We need to resolve aliases, so process in index order.
    # First pass: build canonical groups (those with "strings").
    canonical: dict[int, list[bytes]] = {}  # index → list[bytes]

    for idx in sorted(by_index):
        entry = by_index[idx]
        if "strings" in entry and "alias_of" in entry:
            raise ValueError(
                f"{toml_path}: group {idx} has both 'strings' and 'alias_of' — "
                "use one or the other"
            )
        if "strings" in entry:
            raw_strings = entry["strings"]
            if not isinstance(raw_strings, list):
                raise ValueError(
                    f"{toml_path}: group {idx} 'strings' must be an array"
                )
            encoded: list[bytes] = []
            for j, s in enumerate(raw_strings):
                if not isinstance(s, str):
                    raise ValueError(
                        f"{toml_path}: group {idx} string[{j}] must be a string"
                    )
                try:
                    encoded.append(s.encode(ENCODING))
                except UnicodeEncodeError as exc:
                    raise ValueError(
                        f"{toml_path}: group {idx} string[{j}] cannot be encoded "
                        f"as {ENCODING}: {exc}"
                    ) from exc
            canonical[idx] = encoded
        elif "alias_of" not in entry:
            raise ValueError(
                f"{toml_path}: group {idx} must have either 'strings' or 'alias_of'"
            )

    # Second pass: fill groups list in order, resolving aliases.
    for i in range(1, num_groups):
        if i not in by_index:
            # Missing group index — treat as empty (matches sentinel behaviour)
            groups.append([])
            continue
        entry = by_index[i]
        if "strings" in entry:
            groups.append(canonical[i])
        else:
            alias_target = entry["alias_of"]
            if not isinstance(alias_target, int):
                raise ValueError(
                    f"{toml_path}: group {i} alias_of must be an integer"
                )
            if alias_target not in canonical:
                raise ValueError(
                    f"{toml_path}: group {i} alias_of={alias_target} but group "
                    f"{alias_target} has no 'strings' (cannot alias an alias)"
                )
            # Share the *same list object* so the serialiser detects aliasing
            groups.append(canonical[alias_target])

    return TextFile(groups=groups)


# ── Sub-commands ──────────────────────────────────────────────────────────────


@app.command("show")
def show(
    file: Annotated[
        Path, typer.Argument(help="Path to a Caesar II Textfile (C2.ENG, C2.GER, …)")
    ],
    group: Annotated[
        int | None,
        typer.Option("--group", "-g", help="Show only this group index"),
    ] = None,
    raw: Annotated[
        bool,
        typer.Option("--raw", help="Show raw CP437 bytes instead of decoded Unicode"),
    ] = False,
) -> None:
    """Parse and display a Caesar II Textfile (C2.ENG, C2.GER, C2.FRE, C2.SPA, …).

    Prints every string group and its strings.  Use --group to inspect a single
    group, and --raw to see the raw CP437 byte values.
    """
    if not file.exists():
        typer.echo(f"Error: file not found: {file}", err=True)
        raise typer.Exit(1)

    file_size = file.stat().st_size
    try:
        tf: TextFile = parse(file)
    except ValueError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(1)

    typer.echo(f"File:        {file}")
    typer.echo(f"Size:        {file_size:,} bytes  (limit: {GAME_BUFFER_LIMIT:,})")
    typer.echo(f"Groups:      {tf.num_groups}  (index 0 is null sentinel)")
    typer.echo(f"Encoding:    {ENCODING.upper()}")
    typer.echo("")

    groups_to_show = (
        range(tf.num_groups) if group is None else range(group, group + 1)
    )

    for i in list(groups_to_show):
        if i >= tf.num_groups:
            typer.echo(
                f"Error: group {i} out of range (0–{tf.num_groups - 1})", err=True
            )
            raise typer.Exit(1)

        strings = tf.groups[i]
        typer.echo(f"[{i:3d}]  {len(strings)} string(s)")
        for j, s in enumerate(strings):
            if raw:
                typer.echo(f"       [{j}] {s!r}")
            else:
                decoded = s.decode(ENCODING)
                typer.echo(f"       [{j}] {decoded!r}")


@app.command("export")
def export_toml(
    file: Annotated[
        Path, typer.Argument(help="Path to a Caesar II Textfile (C2.ENG, C2.GER, …)")
    ],
    output: Annotated[
        Path | None,
        typer.Option(
            "--output",
            "-o",
            help=(
                "Destination .toml file.  Defaults to <input>.toml "
                "(e.g. C2.ENG → C2.ENG.toml) in the same directory."
            ),
        ),
    ] = None,
    force: Annotated[
        bool,
        typer.Option("--force", "-f", help="Overwrite the output file if it exists."),
    ] = False,
) -> None:
    """Transpile a binary Textfile to an editable TOML representation.

    The resulting .toml file can be opened in any text editor.  All strings are
    stored as Unicode (CP437 is decoded on export and re-encoded on assemble).
    Aliased groups are represented with ``alias_of = <index>`` so that a
    subsequent ``assemble`` produces a byte-identical binary.

    Example:

        c2 textfile export C2.ENG
        c2 textfile export C2.ENG --output my_translation.toml
    """
    if not file.exists():
        typer.echo(f"Error: file not found: {file}", err=True)
        raise typer.Exit(1)

    out_path = output if output is not None else file.with_suffix(file.suffix + ".toml")

    if out_path.exists() and not force:
        typer.echo(
            f"Error: output file already exists: {out_path}\n"
            "Use --force / -f to overwrite.",
            err=True,
        )
        raise typer.Exit(1)

    try:
        tf = parse(file)
    except ValueError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(1)

    doc = _textfile_to_toml_doc(tf, file.name)
    toml_bytes = tomli_w.dumps(doc).encode()

    header = _TOML_COMMENT_HEADER.format(limit=GAME_BUFFER_LIMIT).encode()
    out_path.write_bytes(header + toml_bytes)

    typer.echo(f"Exported {tf.num_groups} groups → {out_path}")


@app.command("assemble")
def assemble(
    toml_file: Annotated[
        Path,
        typer.Argument(
            help="Path to a .toml file previously produced by 'textfile export'."
        ),
    ],
    output: Annotated[
        Path | None,
        typer.Option(
            "--output",
            "-o",
            help=(
                "Destination binary file.  Defaults to the value of "
                "meta.source inside the TOML (e.g. C2.ENG), written next to "
                "the TOML file."
            ),
        ),
    ] = None,
    force: Annotated[
        bool,
        typer.Option("--force", "-f", help="Overwrite the output file if it exists."),
    ] = False,
) -> None:
    """Reassemble a TOML representation back into a binary Textfile.

    When the TOML has not been modified since export, the output is
    byte-for-byte identical to the original binary.

    Example:

        c2 textfile assemble C2.ENG.toml
        c2 textfile assemble C2.ENG.toml --output C2_modified.ENG
    """
    if not toml_file.exists():
        typer.echo(f"Error: file not found: {toml_file}", err=True)
        raise typer.Exit(1)

    try:
        doc = tomllib.loads(toml_file.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        typer.echo(f"Error: TOML parse error in {toml_file}: {exc}", err=True)
        raise typer.Exit(1)

    try:
        tf = _toml_doc_to_textfile(doc, toml_file)
    except ValueError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(1)

    # Determine output path
    if output is not None:
        out_path = output
    else:
        source_name: str = doc.get("meta", {}).get("source", "")
        if source_name:
            out_path = toml_file.parent / source_name
        else:
            typer.echo(
                "Error: cannot determine output filename — "
                "meta.source is missing from the TOML.  "
                "Use --output to specify the destination.",
                err=True,
            )
            raise typer.Exit(1)

    if out_path.exists() and not force:
        typer.echo(
            f"Error: output file already exists: {out_path}\n"
            "Use --force / -f to overwrite.",
            err=True,
        )
        raise typer.Exit(1)

    try:
        binary = serialise(tf)
    except ValueError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(1)

    out_path.write_bytes(binary)
    typer.echo(
        f"Assembled {tf.num_groups} groups → {out_path}  ({len(binary):,} bytes)"
    )
