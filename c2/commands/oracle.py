"""Codegen oracle — compile C snippets across Watcom versions and compare.

The point is to verify our codegen rules against actual compiler output
instead of guessing.  Most rules in ``docs/watcom-codegen-patterns.md``
say "PS.EXE shows X; rewrite the C to Y".  The oracle lets us check
that a given C *snippet* really does produce X (under the wrong
formulation) and Y (under the right one) on the 10.0a binary that
built PS.EXE — and across the historical container set, and across
flag variants, when we want cross-cutting evidence.

## Design

* Each compile produces a tiny **LE** binary, not a bare ``.obj``.
* We reuse the verifier's ``_load_le_code_and_fixups`` + capstone
  disassembler and ``_parse_map`` symbol-table reader, so insn
  objects carry fixup info and are byte-identical to what
  ``decomp-verify`` sees.
* Compile-cache key is ``(source, image, cflags)``.  Cache lives at
  ``/tmp/c2-oracle/<sha1[:12]>/`` next to the artefacts.

## Quick API

```python
from c2.commands.oracle import compile_snippet, IMAGE_10_0A

src = '''
extern int player_rank;
extern int game_state;
void do_promotion(int level) {
    game_state = 3;
    if (player_rank < 10) {
        level += player_rank;
        if (level <= 10)
            player_rank = level;
    }
}
'''
b = compile_snippet(src)               # 10.0a + default flags
fn = b.function("do_promotion")        # mangled lookup auto-handles trailing _
print(fn.disasm_text())
assert fn.has_insn("push", "ebx")      # Rule 1 prediction
```

## Matrix / comparison API

```python
from c2.commands.oracle import compile_matrix, IMAGE_10_0A, BISECT_IMAGES

builds = compile_matrix(
    sources={"right": right_src, "wrong": wrong_src},
    images=[IMAGE_10_0A],
    flag_sets={
        "default":  "-bt=dos -mf -4r -s -d1",   # proven PS.EXE flags
        "ot":       "-bt=dos -mf -4r -s -d1 -ot",
        "os":       "-bt=dos -mf -4r -s -d1 -os",
    },
)

# Pick any two and diff a function side-by-side
r = builds[("right", IMAGE_10_0A, "default")].function("do_promotion")
w = builds[("wrong", IMAGE_10_0A, "default")].function("do_promotion")
print(diff_functions(r, w))
```

## CLI

```sh
uv run c2 oracle compile snippet.c                  # 10.0a / default flags
uv run c2 oracle compile snippet.c -f do_promotion  # one function
uv run c2 oracle compile snippet.c --bisect         # all 13 versions
uv run c2 oracle compile snippet.c \\
       --image localhost/watcom-9.5c-dosemu2 \\
       --cflags '-bt=dos -mf -4r -s -d1'

uv run c2 oracle diff right.c wrong.c -f do_promotion
uv run c2 oracle diff right.c wrong.c -f do_promotion \\
       --image localhost/watcom-10.0a-wibo \\
       --image localhost/watcom-9.5c-dosemu2

uv run c2 oracle pack            # list discovered rule packs
uv run c2 oracle pack 42         # run rule 42's pack
uv run c2 oracle pack 42 -v -k stub  # verbose, only "stub" tests
uv run c2 oracle pack all        # run every pack
```

## Pack model

Each ``tests/oracle/test_rule_NN_*.py`` is one *pack* — a set of
oracle-driven mutations that prove a numbered rule from
``docs/watcom-codegen-patterns.md``.  ``c2 oracle pack`` is a thin
``pytest`` shell that auto-discovers them by filename pattern; the
header docstring of each test file is the rule's evidence record
(why we believe the rule, where it was confirmed, source refs to OW
internals).
"""

from __future__ import annotations

import hashlib
import re
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Optional

import typer

# We borrow the verifier's machinery so the oracle's view of bytes +
# fixups + insns is exactly what decomp-verify sees.
from c2.commands.decomp_verify import (
    _CS,
    _load_le_code_and_fixups,
    _parse_map,
    _run_in_container,
    PS_CFLAGS,
)


# ── Image / flag defaults ────────────────────────────────────────────────────

IMAGE_10_0A = "localhost/watcom-10.0a-wibo"
"""The PS.EXE compiler.  Default oracle target."""

# Verifier-canonical flags.  Single source of truth is PS_CFLAGS in
# decomp_verify.py (proven, fingerprint-backed).  Keeping this identical to
# the verifier means oracle bytes == verifier bytes == decomp-verify recompile
# bytes.  Do NOT drift it; any change invalidates oracle predictions.
DEFAULT_CFLAGS = PS_CFLAGS
"""Proven Watcom 10.0a flags PS.EXE was built with (= decomp_verify.PS_CFLAGS)."""

BISECT_IMAGES = [
    "localhost/watcom-9.01d-dosemu2",
    "localhost/watcom-9.01e-dosemu2",
    "localhost/watcom-9.5-dosemu2",
    "localhost/watcom-9.5a-dosemu2",
    "localhost/watcom-9.5b-dosemu2",
    "localhost/watcom-9.5c-dosemu2",
    "localhost/watcom-10.0a-wibo",
    "localhost/watcom-10.0b-dosemu2",
    "localhost/watcom-10.5-dosemu2",
    "localhost/watcom-10.6a-dosemu2",
    "localhost/watcom-11.0-dosemu2",
    "localhost/watcom-11.0b-dosemu2",
    "localhost/watcom-11.0c-dosemu2",
]

_CACHE_ROOT = Path("/tmp/c2-oracle")


# ── Result model ─────────────────────────────────────────────────────────────


@dataclass
class Insn:
    """One disassembled instruction within a function."""

    rel_off: int           # offset from start of function (in its own bytes)
    size: int
    raw: bytes
    mnemonic: str
    op_str: str
    fixup_mask: list[bool]  # True for bytes that are fixup targets
    src_line: int | None = None   # source line number (Watcom -d1 cue), if known

    @property
    def line(self) -> str:
        return f"{self.mnemonic} {self.op_str}".strip()

    @property
    def hex(self) -> str:
        return " ".join(
            "??" if m else f"{b:02x}" for m, b in zip(self.fixup_mask, self.raw)
        )


@dataclass
class Function:
    """Disassembled bytes + insns for a single named function."""

    name: str              # mangled (with trailing _, as it appears in MAP)
    base: int              # absolute LE virtual address (code section)
    bytes_: bytes
    fixups: set[int]       # absolute byte offsets that are fixups
    insns: list[Insn] = field(default_factory=list)

    def size(self) -> int:
        return len(self.bytes_)

    def has_insn(self, mnem: str, ops_substr: str = "") -> bool:
        """``True`` if any instruction has matching mnemonic and op substring."""
        for i in self.insns:
            if i.mnemonic == mnem and ops_substr in i.op_str:
                return True
        return False

    def find(self, mnem: str, ops_substr: str = "") -> Optional[Insn]:
        for i in self.insns:
            if i.mnemonic == mnem and ops_substr in i.op_str:
                return i
        return None

    def disasm_text(self) -> str:
        out = []
        for i in self.insns:
            out.append(f"  {i.rel_off:04x}  {i.hex:<23s}  {i.mnemonic:<7s} {i.op_str}")
        return "\n".join(out)

    def hex_masked(self) -> str:
        """Hex of all bytes, with fixup bytes shown as ``??`` (link noise)."""
        out = []
        for i, b in enumerate(self.bytes_):
            out.append("??" if (self.base + i) in self.fixups else f"{b:02x}")
        return "".join(out)


@dataclass
class Build:
    """Result of one (source, image, cflags) compile."""

    label: str             # human label, e.g. "right" or "10.0a / default"
    source: str
    image: str
    cflags: str
    work: Path
    ok: bool
    output: str
    code_size: Optional[int]
    functions: dict[str, Function] = field(default_factory=dict)

    def function(self, name: str) -> Function:
        """Look up by mangled (trailing ``_``) or unmangled name."""
        if name in self.functions:
            return self.functions[name]
        if (m := name + "_") in self.functions:
            return self.functions[m]
        raise KeyError(
            f"function {name!r} not in build {self.label!r}; "
            f"available: {sorted(self.functions.keys())}"
        )


# ── Compile pipeline ─────────────────────────────────────────────────────────


# Minimal entry stub so wlink doesn't complain about a missing entry
# point.  We need *something* exported from _TEXT for the LE to be
# valid.  ``_entry_`` matches what ``decomp-verify`` uses.
_ENTRY_C = "void _entry_(void) {}\n"

# Linker script template — single-translation-unit, DOS LE, no CRT.
# We deliberately avoid pulling in clib3r.lib so the user's snippet
# doesn't accidentally inherit library byte sequences.  If a snippet
# *needs* the CRT (e.g. uses memcpy intrinsics that fall back to a
# call), the user can opt in via ``need_clib3r=True``.
_LNK_HEADER = (
    "DEBUG ALL\n"
    "FORMAT os2 le\n"
    "OPTION MAP=out.map\n"
    "OPTION QUIET\n"
    "NAME out.exe\n"
)


def _content_hash(*parts: str) -> str:
    h = hashlib.sha1()
    for p in parts:
        h.update(p.encode("utf-8"))
        h.update(b"\0")
    return h.hexdigest()[:12]


def _cache_dir(source: str, image: str, cflags: str, *, need_clib3r: bool) -> Path:
    return _CACHE_ROOT / _content_hash(
        source, image, cflags, "clib3r" if need_clib3r else "noclib3r"
    )


def compile_snippet(
    source: str | dict[str, str],
    *,
    image: str = IMAGE_10_0A,
    cflags: str = DEFAULT_CFLAGS,
    label: Optional[str] = None,
    need_clib3r: bool = False,
    extern_defs: Optional[str] = None,
    cache: bool = True,
) -> Build:
    """Compile ``source`` to an LE binary and return a ``Build``.

    Args:
        source: either the full text of a self-contained ``.c`` file,
            or a dict ``{filename: text}`` for multi-file builds.  When a
            dict, all files are compiled and linked together; the
            *first* dict entry's filename (the insertion-order first)
            is treated as the primary translation unit but all
            functions from all files are exposed in the result.
        image: podman image to compile under.  Defaults to 10.0a.
        cflags: compiler flags.  Defaults to PS.EXE flags.
        label: human label used in diff output.  Defaults to
            ``image / cflags``.
        need_clib3r: pull in ``clib3r.lib`` and the WATCOM lib path
            (so memcpy/strcpy/printf etc. resolve).
        extern_defs: optional C source compiled to a separate ``.obj``
            and linked.  Convenience knob for tests that need to
            *define* symbols their primary TU declares ``extern``
            (where defining them in the primary TU would change
            codegen — e.g. tentative definitions get a known address
            in DGROUP, so Watcom may emit ``cmp [imm],...`` instead
            of ``mov reg,[imm]; cmp reg,...``).  Equivalent to
            ``source={"snip.c": ..., "defs.c": extern_defs}``.
        cache: if True (default), reuse cached artefacts when the
            full input tuple matches.
    """
    if isinstance(source, str):
        files = {"snip.c": source}
    else:
        files = dict(source)
    if extern_defs is not None:
        files.setdefault("defs.c", extern_defs)

    cache_key = "\0\0".join(
        f"{n}\0{t}" for n, t in sorted(files.items())
    )
    work = _cache_dir(cache_key, image, cflags, need_clib3r=need_clib3r)
    out_exe = work / "out.exe"
    out_map = work / "out.map"
    log = work / "build.log"

    label = label or f"{_image_short(image)}/{cflags}"

    inputs_match = all(
        (work / fn).exists() and (work / fn).read_text() == text
        for fn, text in files.items()
    )
    cached = (
        cache and inputs_match and out_exe.exists() and out_map.exists()
        and log.exists()
    )

    if not cached:
        work.mkdir(parents=True, exist_ok=True)
        for fn, text in files.items():
            (work / fn).write_text(text)
        (work / "entry.c").write_text(_ENTRY_C)

        # Linker script
        lnk = [_LNK_HEADER]
        if need_clib3r:
            lnk.append("LIBPATH Z:\\opt\\watcom\\lib386;Z:\\opt\\watcom\\lib386\\dos\n")
            lnk.append("LIBRARY clib3r.lib\n")
        for fn in files:
            lnk.append(f"FILE {Path(fn).stem}.obj\n")
        lnk.append("FILE entry.obj\n")
        (work / "out.lnk").write_text("".join(lnk))

        # Build steps -- one container invocation per tool (the wibo shim
        # takes a single argv command; bat execution retired with the DOS
        # images.  wibo start is ~100 ms, so per-step containers are fine
        # for probe-sized builds).
        steps = [f"wcc386 {cflags} -fo={Path(fn).stem}.obj {fn}"
                 for fn in files]
        steps.append(f"wcc386 {cflags} -fo=entry.obj entry.c")
        steps.append("wlink @out.lnk")
        ok, outputs = True, []
        for st in steps:
            st_ok, st_out = _run_in_container(work, image, st)
            outputs.append(st_out)
            ok = ok and st_ok
        output = "\n".join(outputs)
        if "Error!" in output or "undefined symbol" in output \
                or not out_exe.exists():
            ok = False
        log.write_text(output)
        out_text = output
    else:
        out_text = log.read_text()
        ok = True

    code_size = None
    for ln in out_text.splitlines():
        m = re.match(r"\s*Code size:\s*(\d+)", ln)
        if m:
            code_size = int(m.group(1))
            break

    functions: dict[str, Function] = {}
    if ok:
        # Read code bytes + fixup byte-offset set, then carve into functions
        # by walking the .map symbol table.
        code, fixups = _load_le_code_and_fixups(out_exe)
        syms = _parse_map(out_map)

        # Sort symbols by offset; treat each named symbol as a function
        # and use the next symbol's offset (or end-of-code) as the close.
        # Skip helpers from clib3r and the entry stub.
        keep = sorted(
            (off, name) for name, off in syms.items()
            if name.endswith("_") and name != "_entry_"
        )
        keep_offs = [o for o, _ in keep]
        ends = keep_offs[1:] + [len(code)]

        # Try to load Watcom -d1 line-number debug info from the LE binary.
        # When the build wasn't compiled with -d1 (or debug parser fails)
        # we silently fall back to no line annotations.
        line_lookup: dict[int, int] = _load_oracle_line_lookup(out_exe)

        for (off, name), end in zip(keep, ends):
            fn_bytes = code[off:end]
            fn_fixups = {f for f in fixups if off <= f < end}
            insns = list(_disasm_func(fn_bytes, off, fn_fixups))
            if line_lookup:
                for ins in insns:
                    ln = line_lookup.get(off + ins.rel_off)
                    if ln is not None:
                        ins.src_line = ln
            functions[name] = Function(
                name=name, base=off, bytes_=fn_bytes,
                fixups=fn_fixups, insns=insns,
            )

    return Build(
        label=label, source=source, image=image, cflags=cflags,
        work=work, ok=ok, output=out_text, code_size=code_size,
        functions=functions,
    )


def _load_oracle_line_lookup(exe: Path) -> dict[int, int]:
    """Parse Watcom -d1 debug info from a freshly-built LE binary.

    Returns ``{flat_code_offset: source_line}``.  Returns an empty
    dict (silently) when the binary has no debug section or parsing
    fails — cgex / oracle output then just lacks line annotations.

    The flat code offset matches ``Function.base + Insn.rel_off`` so
    the caller can look up the source line for each instruction.
    """
    try:
        from c2.parsers.debug import (
            parse_watcom_debug, build_addr_info_base_map,
        )
        info = parse_watcom_debug(exe)
    except Exception:
        return {}

    addr_info_base_map = build_addr_info_base_map(info.addr_info)
    out: dict[int, int] = {}
    for _mod_idx, segments in info.line_numbers.items():
        for seg in segments:
            module_base = addr_info_base_map.get(seg.addr_info_offset, 0)
            for lentry in seg.entries:
                flat_off = module_base + lentry.code_offset
                # Multiple cues at the same offset shouldn't happen,
                # but if they do prefer the first (matches PS behavior).
                out.setdefault(flat_off, lentry.line)
    return out


def _disasm_func(code: bytes, base: int, fixups: set[int]) -> Iterable[Insn]:
    decoded = 0
    for insn in _CS.disasm(code, 0):
        raw = bytes(insn.bytes)
        mask = [(base + insn.address + i) in fixups for i in range(len(raw))]
        yield Insn(
            rel_off=insn.address, size=insn.size, raw=raw,
            mnemonic=insn.mnemonic, op_str=insn.op_str, fixup_mask=mask,
        )
        decoded = insn.address + insn.size
    if decoded < len(code):
        tail = code[decoded:]
        mask = [(base + decoded + i) in fixups for i in range(len(tail))]
        yield Insn(
            rel_off=decoded, size=len(tail), raw=tail,
            mnemonic="<raw>", op_str=f"{len(tail)}b", fixup_mask=mask,
        )


def _image_short(image: str) -> str:
    """``localhost/watcom-10.0a-wibo`` → ``10.0a``."""
    m = re.search(r"watcom-([^-]+)-", image)
    return m.group(1) if m else image


# ── Matrix / comparison ──────────────────────────────────────────────────────


def compile_matrix(
    sources: dict[str, str],
    *,
    images: Iterable[str] = (IMAGE_10_0A,),
    flag_sets: dict[str, str] | None = None,
    need_clib3r: bool = False,
) -> dict[tuple[str, str, str], Build]:
    """Compile a set of source variants under a matrix of (image, flags).

    Returns a dict keyed by ``(source_label, image, flag_label)``.
    """
    flag_sets = flag_sets or {"default": DEFAULT_CFLAGS}
    out: dict[tuple[str, str, str], Build] = {}
    for src_label, source in sources.items():
        for img in images:
            for flag_label, cflags in flag_sets.items():
                key = (src_label, img, flag_label)
                lab = f"{src_label} / {_image_short(img)} / {flag_label}"
                out[key] = compile_snippet(
                    source, image=img, cflags=cflags,
                    label=lab, need_clib3r=need_clib3r,
                )
    return out


def diff_functions(a: Function, b: Function) -> str:
    """Return a side-by-side text diff of two Function disassemblies.

    Aligned by instruction index (no SequenceMatcher) — both sides
    print every insn; mismatches are flagged with ``!``.
    """
    n = max(len(a.insns), len(b.insns))
    rows = []
    rows.append(f"{'A: '+a.name:<55s} | {'B: '+b.name}")
    rows.append("-" * 55 + "-+-" + "-" * 55)
    for i in range(n):
        ai = a.insns[i] if i < len(a.insns) else None
        bi = b.insns[i] if i < len(b.insns) else None
        a_text = (
            f"{ai.rel_off:04x}  {ai.hex:<19s}  {ai.line}"
            if ai is not None else ""
        )
        b_text = (
            f"{bi.rel_off:04x}  {bi.hex:<19s}  {bi.line}"
            if bi is not None else ""
        )
        sep = "|"
        if ai is None or bi is None or ai.line != bi.line:
            sep = "!"
        rows.append(f"{a_text:<55s} {sep} {b_text}")
    rows.append(f"\nA size={a.size()}  B size={b.size()}  delta={b.size()-a.size():+d}")
    return "\n".join(rows)


# ── CLI ──────────────────────────────────────────────────────────────────────


app = typer.Typer(
    help="Codegen oracle — compile C snippets across Watcom versions.",
    no_args_is_help=True,
)


@app.command("compile")
def cli_compile(
    snippet: Path = typer.Argument(..., help="Path to .c snippet"),
    image: list[str] = typer.Option(
        [IMAGE_10_0A], "--image", "-i",
        help="Compiler image (repeat to add)"),
    cflags: list[str] = typer.Option(
        [DEFAULT_CFLAGS], "--cflags", "-c",
        help="Flag set (repeat to add multiple)"),
    function: Optional[str] = typer.Option(
        None, "--function", "-f", help="Print only this function"),
    bisect: bool = typer.Option(
        False, "--bisect", "-b", help="Use the historical 9.01d…11.0c set"),
    need_clib3r: bool = typer.Option(
        False, "--clib3r", help="Link against clib3r.lib"),
    only_size: bool = typer.Option(
        False, "--only-size", help="Print only the per-function sizes"),
) -> None:
    """Compile a snippet under one or more (image, flags) combos."""
    src = snippet.read_text()
    images = BISECT_IMAGES if bisect else image
    flag_set = {f"flags{i}": c for i, c in enumerate(cflags)}

    builds = compile_matrix(
        {"snip": src},
        images=images, flag_sets=flag_set, need_clib3r=need_clib3r,
    )
    for (_, img, flab), build in builds.items():
        head = f"== {_image_short(img)}  cflags={build.cflags!r} =="
        if not build.ok:
            typer.echo(head)
            typer.echo(build.output)
            typer.echo("[FAILED]")
            continue
        sz = build.code_size if build.code_size is not None else "?"
        typer.echo(f"{head}  Code size: {sz}  fns: {len(build.functions)}")
        names = (
            [function + "_"] if function and function + "_" in build.functions
            else [function] if function and function in build.functions
            else list(build.functions.keys())
        )
        for n in names:
            fn = build.functions[n]
            typer.echo(f"\n  {fn.name}  ({fn.size()} bytes  @{fn.base:#x})")
            if not only_size:
                for line in fn.disasm_text().splitlines():
                    typer.echo(line)


@app.command("diff")
def cli_diff(
    a: Path = typer.Argument(..., help="First snippet"),
    b: Path = typer.Argument(..., help="Second snippet"),
    function: str = typer.Option(..., "--function", "-f"),
    image: list[str] = typer.Option([IMAGE_10_0A], "--image", "-i"),
    cflags: str = typer.Option(DEFAULT_CFLAGS, "--cflags"),
    need_clib3r: bool = typer.Option(False, "--clib3r"),
) -> None:
    """Side-by-side diff of one function across two snippets."""
    src_a = a.read_text()
    src_b = b.read_text()
    for img in image:
        ba = compile_snippet(src_a, image=img, cflags=cflags,
                             label=f"A:{a.name}", need_clib3r=need_clib3r)
        bb = compile_snippet(src_b, image=img, cflags=cflags,
                             label=f"B:{b.name}", need_clib3r=need_clib3r)
        typer.echo(f"\n== {_image_short(img)} ==")
        if not ba.ok:
            typer.echo(f"A failed:\n{ba.output}\n"); continue
        if not bb.ok:
            typer.echo(f"B failed:\n{bb.output}\n"); continue
        try:
            fa = ba.function(function)
            fb = bb.function(function)
        except KeyError as e:
            typer.echo(str(e)); continue
        typer.echo(diff_functions(fa, fb))


@app.command("clear-cache")
def cli_clear_cache() -> None:
    """Remove the oracle compile cache at /tmp/c2-oracle."""
    import shutil
    shutil.rmtree(_CACHE_ROOT, ignore_errors=True)
    typer.echo(f"Removed {_CACHE_ROOT}")


# ── Pack discovery ─────────────────────────────────────────────────


_PACKS_DIR = Path(__file__).resolve().parent.parent.parent / "tests" / "oracle"


def _discover_packs() -> dict[str, Path]:
    """Map pack id (e.g. ``"42"``, ``"7b"``) to its test file path."""
    packs: dict[str, Path] = {}
    for p in sorted(_PACKS_DIR.glob("test_rule_*.py")):
        # filename: test_rule_NN[suffix]_<descr>.py
        m = re.match(r"test_rule_(\d+[a-z]*)_(.+)\.py", p.name)
        if m:
            packs[m.group(1)] = p
    return packs


@app.command("pack")
def cli_pack(
    rule: Optional[str] = typer.Argument(
        None,
        help='Rule id (e.g. "42", "7b") or "all".  Omit to list available packs.',
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Forward -v to pytest"),
    keyword: Optional[str] = typer.Option(
        None, "--keyword", "-k", help="Pytest -k filter"),
) -> None:
    """Run an oracle pack (= the test_rule_NN_*.py for one rule).

    Examples:

      c2 oracle pack             # list all packs
      c2 oracle pack 42          # run rule 42's pack
      c2 oracle pack 42 -v       # verbose
      c2 oracle pack 42 -k stub  # only tests with "stub" in name
      c2 oracle pack all         # run every pack
    """
    packs = _discover_packs()
    if rule is None:
        # List mode
        typer.echo(f"Discovered {len(packs)} oracle packs:\n")
        # Group by leading numeric, preserving suffix order (7, 7b)
        for pid, path in sorted(packs.items(), key=lambda kv: (
            int(re.match(r"(\d+)", kv[0]).group(1)),
            kv[0],
        )):
            descr = path.stem.split("_", 3)[-1].replace("_", " ")
            typer.echo(f"  rule {pid:>4}  {descr}")
        typer.echo("\nUse `c2 oracle pack <id>` to run one,"
                   " or `c2 oracle pack all` for every pack.")
        return

    if rule == "all":
        targets = [str(p) for p in packs.values()]
    else:
        if rule not in packs:
            typer.echo(f"unknown pack {rule!r}; "
                       f"see `c2 oracle pack` for list", err=True)
            raise typer.Exit(2)
        targets = [str(packs[rule])]

    cmd = ["pytest"] + targets
    if verbose:
        cmd.append("-v")
    if keyword:
        cmd.extend(["-k", keyword])

    rc = subprocess.call(cmd)
    raise typer.Exit(rc)
