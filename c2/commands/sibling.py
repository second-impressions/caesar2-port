r"""sibling command: find decompiled siblings of a PS.EXE function via
fuzzy ASM shingle matching, and STRUCTURAL twins by prologue signature.

Two similarity lenses over one cached corpus:

  * **Shingle lens** (default) -- "what byte-exact function does this
    whole body resemble".  Rolling 5-insn shingle containment.  Finds
    sibling templates (``barbarian_in_region`` ~ ``raider_in_region``).
  * **Structural lens** (``--structure`` / ``--survey``) -- the three
    asm-visible features that DIAGNOSE a diffing function: how much
    stack it reserves (``sub esp, N``), how many args it takes (declared
    param count), and its opening-instruction SHAPE.  Here the goal is
    not a template but a verdict: a (pushes, frame, argc) signature no
    byte-exact function shares -- especially one made unique by its
    FRAME -- is a structural smoking gun; an UNRELATED byte-exact
    function that reproduces the same prologue+opening proves the shape
    is right and the residue is downstream register allocation.
    Corpus findings: ``docs/structure-twin-survey-2026-06-17.md``.

The idea: PS.EXE has a corpus of ~1000 byte-exact decompiled functions.
A new diffing or undecompiled function often shares structural pattern
with one of them (e.g. ``barbarian_in_region`` is 90% structurally
identical to ``raider_in_region``).  Finding the byte-exact sibling
gives the agent a verified C-source template to study.

Approach (lifted from ethteck/coddog, used in N64/PSX decomp projects):

  1. Disassemble every code function in PS.EXE.
  2. Normalize each instruction to ``MNEMONIC OP_CLASS`` tokens
     (registers → ``R``, immediates → ``IMM``, fixups → ``[DATA]``,
     branches → ``TGT``).
  3. Compute rolling 5-instruction shingles and hash them.
  4. For a query function, find candidate siblings via inverted
     index (sublinear lookup) and rank by *containment* — what
     fraction of the query's shingles appear in each donor.
  5. ``submatch`` mode: find contiguous shingle runs so the agent
     knows *which instruction range* in the donor to study.

Default metric is **containment of query in donor** (``common / |Q|``)
rather than Jaccard, because:

  * Source-hint usefulness is asymmetric: a 20-insn helper fully
    contained in a 200-insn function is a great hint, even though
    Jaccard would score them low (20/200 = 10%).
  * Watcom emits common idioms (struct field copy, loop tails)
    that appear in many functions; containment biases the score
    toward "how much of THIS function I recognize" rather than
    "how similar are these two", which is the right question.

Usage::

    uv run c2 sibling get_aquaduct_elastic
    uv run c2 sibling action --status any --top 10
    uv run c2 sibling barbarian_in_region --submatch raider_in_region
    uv run c2 sibling --all --min-score 0.30   # corpus-wide report
    uv run c2 sibling some_fn --json
    uv run c2 sibling build_city_item --structure        # structural twins
    uv run c2 sibling build_city_item --structure --cross-family
    uv run c2 sibling --survey                           # diff-corpus diagnosis

Library use::

    from c2.commands.sibling import (find_siblings, find_submatches,
                                     find_structure_twins, structure_survey)
    hits = find_siblings("show_ov_legend_panel", filter_status={"exact"})
    runs = find_submatches("show_ov_legend_panel", "show_recruitment")
    twins = find_structure_twins("build_city_item", cross_family_only=True)
    survey = structure_survey()   # corpus-wide diagnostic partition
"""

from __future__ import annotations

import json
import pickle
import re
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Annotated, Iterable, Optional

import typer

from c2.commands.disasm import disasm_function, DisasmLine


# ── Token normalization ─────────────────────────────────────────────────────

_R32 = {"eax", "ecx", "edx", "ebx", "esp", "ebp", "esi", "edi"}
_R16 = {"ax", "cx", "dx", "bx", "sp", "bp", "si", "di"}
_R8  = {"al", "cl", "dl", "bl", "ah", "ch", "dh", "bh"}
_SEG = {"cs", "ds", "es", "fs", "gs", "ss"}

# Match a numeric literal (decimal or hex) that's not embedded in an
# identifier.  Negative sign included so e.g. ``mov eax, -1`` collapses
# correctly.
_IMM_RE = re.compile(r"(?<![\w.])(0x[0-9a-fA-F]+|-?\d+)(?![\w.])")
_DWORD_RE = re.compile(r"\bdword ptr\s+")
_WORD_RE = re.compile(r"[A-Za-z_][\w.]*|\?+")


def _norm_reg(tok: str) -> str:
    r = tok.lower()
    if r in _R32 or r in _R16 or r in _R8:
        return "R"
    if r in _SEG:
        return "SR"
    if r.startswith("st") and ("(" in r or r == "st"):
        return "FR"
    return tok  # leave non-register tokens alone


def _normalize_op_str(op_str: str) -> str:
    s = _DWORD_RE.sub("", op_str)
    s = _IMM_RE.sub("IMM", s)
    s = _WORD_RE.sub(lambda m: _norm_reg(m.group(0)), s)
    return s.strip()


def normalize_insn(ln: DisasmLine) -> str:
    """Stable canonical token for one instruction.

    Collapses register identities, immediates, and data/branch
    operands so e.g. ``mov eax, [0x72734]`` and ``mov ebx, [0x80100]``
    both become ``mov R, [DATA]``.  Branch instructions collapse
    their operand to ``TGT`` (we keep the mnemonic, which still
    distinguishes jcc directions: ``je`` ≠ ``jne``).
    """
    op = _normalize_op_str(ln.op_str)
    if ln.target is not None:
        op = "TGT"
    elif ln.data_ref is not None:
        # First IMM/MEM operand is the data ref
        op = op.replace("IMM", "DATA", 1)
    return f"{ln.mnemonic} {op}" if op else ln.mnemonic


# ── Structural-twin lens (frame / args / opening shape) ─────────────────────
#
# A second similarity axis over the SAME corpus.  Where the shingle lens
# asks "what byte-exact function does this whole body resemble", the
# structural lens asks the three asm-visible questions that diagnose a
# diffing function: how much stack it reserves, how many args it takes,
# and its opening-instruction SHAPE (first OPENING_WINDOW normalized
# tokens after the prologue -- the SAME normalization the shingle lens
# uses, so registers/immediates/globals are already abstracted).

OPENING_WINDOW = 10            # post-prologue instructions of shape compared
_CALLEE_SAVE = ("ebx", "ecx", "edx", "esi", "edi", "ebp", "eax")
_DEF_KEYWORDS = {"if", "for", "while", "switch", "return", "sizeof",
                 "do", "else", "catch"}


def _is_push_imm_line(ln: DisasmLine) -> bool:
    if ln.mnemonic != "push":
        return False
    op = ln.op_str.strip()
    return bool(op) and (op[0].isdigit() or op.startswith("0x")
                         or op.startswith("-"))


def detect_prologue(lines: list[DisasmLine]) -> tuple[tuple[str, ...], int, int]:
    """Parse a Watcom prologue.  Returns ``(pushes, frame, body_start)``:
    the ordered callee-save / arg-spill push registers, the ``sub esp, N``
    frame size (0 if none), and the index of the first body instruction.
    Skips the optional ``push <imm>; call __STK`` stack-probe prefix.
    """
    i = 0
    if (len(lines) >= 2 and _is_push_imm_line(lines[0])
            and lines[1].mnemonic == "call"):
        i = 2
    pushes: list[str] = []
    while i < len(lines) and lines[i].mnemonic == "push":
        op = lines[i].op_str.strip()
        if op in _CALLEE_SAVE:
            pushes.append(op)
            i += 1
        else:
            break
    frame = 0
    if i < len(lines) and lines[i].mnemonic in ("sub", "add"):
        f = [o.strip() for o in lines[i].op_str.split(",")]
        if len(f) == 2 and f[0] == "esp":
            try:
                imm = int(f[1], 0)
            except ValueError:
                imm = 0
            frame = imm if lines[i].mnemonic == "sub" else -imm
            i += 1
    return tuple(pushes), frame, i


def _build_argc_map(src_dir: Path) -> dict[str, int]:
    """Declared parameter count per function name, one pass per .c file.

    Over-captures (any ``ident(...) {``) but is keyed by name, so only
    real function names are ever looked up.  C keywords are excluded.
    """
    amap: dict[str, int] = {}
    if not src_dir.exists():
        return amap
    ident = re.compile(r"([A-Za-z_]\w*)\s*\(")
    for fp in sorted(src_dir.glob("*.c")):
        try:
            text = fp.read_text(errors="replace")
        except OSError:
            continue
        for m in ident.finditer(text):
            nm = m.group(1)
            if nm in _DEF_KEYWORDS:
                continue
            i = m.end() - 1
            depth = 0
            params = ""
            j = i
            while j < len(text):
                c = text[j]
                if c == "(":
                    depth += 1
                elif c == ")":
                    depth -= 1
                    if depth == 0:
                        params = text[i + 1:j]
                        break
                j += 1
            k = j + 1
            while k < len(text) and text[k] in " \t\r\n":
                k += 1
            if k >= len(text) or text[k] != "{":
                continue
            p = params.strip()
            if p in ("", "void"):
                amap[nm] = 0
                continue
            depth = 0
            cnt = 1
            for c in p:
                if c in "([{":
                    depth += 1
                elif c in ")]}":
                    depth -= 1
                elif c == "," and depth == 0:
                    cnt += 1
            amap[nm] = cnt
    return amap


def _shared_prefix(a: Iterable, b: Iterable) -> int:
    n = 0
    for x, y in zip(a, b):
        if x != y:
            break
        n += 1
    return n


# ── Corpus build & cache ────────────────────────────────────────────────────

CACHE_DIR = Path(".c2-cache")
CORPUS_CACHE = CACHE_DIR / "sibling-corpus.pkl"
STATUS_CACHE = CACHE_DIR / "sibling-status.json"
CORPUS_SCHEMA = 3  # bump when normalization or shingle format changes


@dataclass
class FnEntry:
    name: str
    address: int
    size: int                  # body size in bytes
    n_insns: int               # instruction count
    tokens: tuple[str, ...]    # normalized instruction stream
    shingles: tuple[int, ...]  # rolling-window hashes
    src_file: Optional[str]    # decomp/src/<file>.c if annotated
    status: str                # 'exact' | 'diff' | 'written' | 'undone'
    diff_byte_count: int = 0
    # Structural-twin lens (PS-asm only):
    pushes: tuple[str, ...] = ()    # callee-save / arg-spill push regs
    frame: int = 0                  # prologue `sub esp, N`
    argc: Optional[int] = None      # declared param count (from src)
    body_start: int = 0             # index of first post-prologue insn


@dataclass
class Corpus:
    window: int
    entries: dict[str, FnEntry] = field(default_factory=dict)
    # Inverted index: shingle hash -> list of function names
    inv: dict[int, list[str]] = field(default_factory=lambda: defaultdict(list))

    def build_index(self) -> None:
        self.inv = defaultdict(list)
        for e in self.entries.values():
            for h in set(e.shingles):
                self.inv[h].append(e.name)


_corpus_singleton: Optional[Corpus] = None

# Re-entry guard: when sibling is being consulted from *inside*
# ``decomp-verify -v`` for the per-function ``Sibling:`` hint, we must
# NOT recursively call decomp-verify again to refresh status — that
# would either infinite-loop or rebuild the whole project at every
# per-function hint call.  The hint path sets this to True before
# calling find_siblings(); the status refresher checks it and stays
# on the disk cache / annotation-only fallback path.
_in_verify_hint: bool = False


def _shingle(tokens: list[str], w: int) -> list[int]:
    if len(tokens) < w:
        tokens = tokens + ["_PAD_"] * (w - len(tokens))
    return [hash(tuple(tokens[i : i + w])) for i in range(len(tokens) - w + 1)]


def _scan_src_mtime(src_dir: Path) -> float:
    """Newest mtime across decomp/src/*.c and decomp/include/*.h.

    Drives baseline-staleness detection: if any source file has been
    touched since the baseline was taken, the exact/diff classification
    in that baseline is suspect.
    """
    newest = 0.0
    for pat in (src_dir.glob("*.c"), src_dir.parent.joinpath("include").glob("*.h")):
        for f in pat:
            try:
                m = f.stat().st_mtime
            except OSError:
                continue
            if m > newest:
                newest = m
    return newest


def _baseline_is_fresh(baseline_path: Path, src_dir: Path) -> bool:
    """True if the baseline is newer than every decomp source/header."""
    try:
        b_mt = baseline_path.stat().st_mtime
    except OSError:
        return False
    return b_mt >= _scan_src_mtime(src_dir)


def _diffs_from_verify_json(v: dict) -> dict[str, int]:
    """Shape the ``decomp-verify --json`` output into ``{name: byte_diff}``.

    The verifier emits diffing functions only under ``functions[]``;
    exact ones are implied by the per-file summary.  Both kinds get
    folded into one dict where ``byte_diff == 0`` means exact — the
    same shape baseline JSON uses under ``diffs``.
    """
    diffs: dict[str, int] = {}
    for fn in v.get("functions", []):
        diffs[fn["name"]] = fn.get("diff_byte_count", 0)
    # The verifier doesn't emit per-function records for exact functions,
    # but we want them in the dict so the caller can distinguish
    # ``exact`` (in dict, byte_diff == 0) from ``written`` (not in dict).
    # Use the per-file ``exact`` count + the file's ``names`` list when
    # available; the JSON schema as of 2026 doesn't include exact
    # function names, so we leave them out and let the caller treat
    # missing-from-dict as ``written``.  The fresh-status path below
    # overrides this by running its own in-process verify and writing
    # a richer cache.
    return diffs


def _refresh_status_via_verify(verbose: bool) -> Optional[dict[str, int]]:
    """Run ``decomp-verify --json`` in-process and return ``{name: byte_diff}``
    for every compared function (exact rows have byte_diff == 0).

    Returns None if the verifier fails to run (e.g. no Watcom container
    available).  In that case the caller falls back to ``written`` status
    for every annotated function.
    """
    if verbose:
        typer.echo(
            "sibling: regenerating status via decomp-verify --json "
            "(~10–30 s; cached afterwards)…",
            err=True,
        )
    try:
        # Lazy import to avoid a hard cycle with decomp_verify, which
        # itself imports sibling.render_sibling_hint lazily.
        import contextlib
        import io as _io
        from c2.commands.decomp_verify import decomp_verify

        buf = _io.StringIO()
        # Redirect BOTH stdout and stderr: ``decomp_verify`` with
        # ``json_out=True`` routes the JSON document to stdout (caught
        # by ``buf``) AND all progress chatter (``Loading PS.EXE...`` /
        # ``Building 37 source files...`` / per-function ``~`` lines /
        # ``line-corpus: indexed ...``) to stderr.  Without the stderr
        # redirect, that chatter leaks into the orchestrator's UI when
        # ``c2 decompile``'s per-agent ``compose_workspace`` chain
        # eventually reaches ``info -> _siblings -> find_siblings ->
        # _load_fn_status -> _refresh_status_via_verify``.
        with (contextlib.redirect_stdout(buf),
              contextlib.redirect_stderr(_io.StringIO())):
            try:
                decomp_verify(
                    c_files=None,
                    symbols_json=Path("data/out/symbols.json"),
                    exe_path=Path("data/PS.EXE"),
                    decomp_dir=Path("decomp"),
                    json_out=True,
                    strict=False,
                    strict_warnings=False,
                )
            except typer.Exit as exc:
                if exc.exit_code not in (0, None):
                    raise
        v = json.loads(buf.getvalue())
    except Exception as e:
        if verbose:
            typer.echo(
                f"sibling: status refresh failed ({type(e).__name__}: {e}); "
                f"falling back to 'written' for all annotated functions",
                err=True,
            )
        return None

    # Build {name: byte_diff} for ALL compared functions.  Diffing
    # rows come straight from functions[]; exact ones are derived
    # from the per-file totals minus diffing.  We can't recover
    # exact-function names from the JSON alone, so we synthesise
    # the set from decomp/src/*.c FUNCTION annotations and subtract
    # the diffing names.
    diffing = {fn["name"]: fn.get("diff_byte_count", 0)
               for fn in v.get("functions", [])}

    # Cache to disk so the next session doesn't re-run the verifier.
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    try:
        STATUS_CACHE.write_text(json.dumps({
            "schema": 1,
            "generated_at": _now_iso(),
            "summary": v.get("summary", {}),
            "diffing": diffing,
        }, indent=2))
    except OSError:
        pass

    return diffing


def _now_iso() -> str:
    import datetime as _dt
    return _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")


def _load_status_cache(src_dir: Path) -> Optional[dict[str, int]]:
    """Return cached ``{name: byte_diff}`` if the on-disk status cache
    is newer than every decomp/src/*.c and decomp/include/*.h."""
    if not STATUS_CACHE.exists():
        return None
    try:
        if STATUS_CACHE.stat().st_mtime < _scan_src_mtime(src_dir):
            return None
        data = json.loads(STATUS_CACHE.read_text())
        return data.get("diffing")
    except (OSError, ValueError):
        return None


def _load_fn_status(
    *,
    src_dir: Path = Path("decomp/src"),
    baseline_path: Optional[Path] = None,
    refresh: bool = False,
    verbose: bool = False,
) -> tuple[dict[str, tuple[str, int]], dict[str, str]]:
    """Determine each function's decomp/verify status.

    Returns ``(status_by_name, src_file_by_name)``.

    Status:
      * ``exact``   — annotated FUNCTION + byte_diff == 0
      * ``diff``    — annotated FUNCTION + byte_diff > 0
      * ``written`` — annotated FUNCTION but no verification data available
      * ``undone``  — no FUNCTION annotation

    The exact/diff distinction comes from one of three sources, in
    priority order:

      1. **Explicit baseline path** (``baseline_path`` argument).
         Honoured verbatim even if stale — user opted in.
      2. **On-disk status cache** (``.c2-cache/sibling-status.json``)
         if newer than every decomp source/header file.
      3. **Auto-discovered baseline** in ``baselines/`` if newer than
         every decomp source/header file (else considered stale).
      4. **In-process ``decomp-verify --json`` regeneration**, with
         the result written back to the status cache.

    Pass ``refresh=True`` to force an in-process verify regardless of
    cache freshness.

    If the verifier itself fails (no Watcom container, broken source,
    etc.), every annotated function falls back to ``written`` status
    so sibling search degrades gracefully.
    """
    fn_re = re.compile(
        r"^//\s*FUNCTION:\s*\w+\s+0x([0-9A-Fa-f]+)", re.MULTILINE,
    )
    addr_to_file: dict[int, str] = {}
    if src_dir.exists():
        for f in sorted(src_dir.glob("*.c")):
            try:
                txt = f.read_text(errors="replace")
            except Exception:
                continue
            for m in fn_re.finditer(txt):
                addr_to_file.setdefault(int(m.group(1), 16), f.name)

    # Need addr->name to translate annotation → function status
    sym = json.loads(Path("data/out/symbols.json").read_text())
    addr_to_name = {s["address"]: s["name"] for s in sym["symbols"]}
    written_names: set[str] = set()
    src_file_by_name: dict[str, str] = {}
    for addr, fname in addr_to_file.items():
        n = addr_to_name.get(addr)
        if n is not None:
            written_names.add(n)
            src_file_by_name[n] = fname

    # Resolve baseline diffs by walking the priority chain above.
    baseline_diffs: Optional[dict[str, int]] = None

    # (1) explicit baseline path: trust it verbatim.
    if baseline_path is not None and baseline_path.exists() and not refresh:
        try:
            base = json.loads(baseline_path.read_text())
            baseline_diffs = {
                n: info.get("byte_diff", 0)
                for n, info in base.get("diffs", {}).items()
            }
        except Exception:
            baseline_diffs = None

    # (2) status cache, if fresh.
    if baseline_diffs is None and not refresh:
        baseline_diffs = _load_status_cache(src_dir)
        if baseline_diffs is not None and verbose:
            typer.echo(
                f"sibling: status loaded from {STATUS_CACHE} "
                f"({sum(1 for v in baseline_diffs.values() if v == 0)} exact, "
                f"{sum(1 for v in baseline_diffs.values() if v > 0)} diff)",
                err=True,
            )

    # (3) auto-discovered baseline if not stale.
    stale_baseline_fallback: Optional[dict[str, int]] = None
    if baseline_diffs is None and not refresh:
        bdir = Path("baselines")
        if bdir.is_dir():
            cands = sorted(bdir.glob("*.json"),
                           key=lambda p: p.stat().st_mtime, reverse=True)
            for cand in cands:
                if _baseline_is_fresh(cand, src_dir):
                    try:
                        base = json.loads(cand.read_text())
                        baseline_diffs = {
                            n: info.get("byte_diff", 0)
                            for n, info in base.get("diffs", {}).items()
                        }
                        if verbose:
                            typer.echo(
                                f"sibling: using fresh baseline {cand}",
                                err=True,
                            )
                        break
                    except Exception:
                        continue
            else:
                # Every baseline is stale.  Keep the newest one
                # around as a fallback for the verify-hint path
                # (where we can't recursively refresh) so that the
                # Sibling: header keeps firing across source edits
                # — the score is still meaningful even if a handful
                # of "exact" labels are slightly out of date.
                if cands:
                    try:
                        stale_baseline_fallback = {
                            n: info.get("byte_diff", 0)
                            for n, info in json.loads(
                                cands[0].read_text()
                            ).get("diffs", {}).items()
                        }
                    except Exception:
                        stale_baseline_fallback = None
                    if verbose:
                        newest = cands[0]
                        age_h = (_scan_src_mtime(src_dir) - newest.stat().st_mtime) / 3600
                        if _in_verify_hint:
                            typer.echo(
                                f"sibling: baseline {newest} is stale "
                                f"(~{age_h:.1f}h behind source); using "
                                f"it anyway (in verify-hint context, "
                                f"cannot recurse to refresh)",
                                err=True,
                            )
                        else:
                            typer.echo(
                                f"sibling: baseline {newest} is stale "
                                f"(~{age_h:.1f}h behind source); refreshing…",
                                err=True,
                            )

    # (4) regenerate via in-process verify.  Skipped when we're being
    # called from inside decomp-verify's hint path (would recurse) —
    # in that case we fall back to the stale baseline, if any.
    if baseline_diffs is None and not _in_verify_hint:
        baseline_diffs = _refresh_status_via_verify(verbose=verbose)
    if baseline_diffs is None and stale_baseline_fallback is not None:
        baseline_diffs = stale_baseline_fallback

    status: dict[str, tuple[str, int]] = {}
    for n in written_names:
        if baseline_diffs is None:
            status[n] = ("written", 0)
        elif n not in baseline_diffs:
            # Annotated but not in baseline: probably added since
            # the baseline was taken.  Mark as 'written'.
            status[n] = ("written", 0)
        elif baseline_diffs[n] == 0:
            status[n] = ("exact", 0)
        else:
            status[n] = ("diff", baseline_diffs[n])
    return status, src_file_by_name


def _corpus_cache_key(
    exe_path: Path, symbols_json: Path, window: int,
) -> tuple:
    return (
        CORPUS_SCHEMA,
        window,
        exe_path.stat().st_mtime_ns,
        symbols_json.stat().st_mtime_ns,
    )


def build_corpus(
    *,
    window: int = 5,
    max_fn_size: int = 8000,
    min_insns: int = 4,
    exe_path: Path = Path("data/PS.EXE"),
    symbols_json: Path = Path("data/out/symbols.json"),
    src_dir: Path = Path("decomp/src"),
    baseline_path: Optional[Path] = None,
    refresh_status: bool = False,
    use_cache: bool = True,
    verbose: bool = False,
) -> Corpus:
    """Build (or load from cache) the full sibling corpus.

    Caches normalized tokens + shingles + status to
    ``.c2-cache/sibling-corpus.pkl``.  Invalidated when ``PS.EXE``,
    ``symbols.json``, or the window size change.
    """
    global _corpus_singleton
    if _corpus_singleton is not None and _corpus_singleton.window == window:
        return _corpus_singleton

    cache_key = _corpus_cache_key(exe_path, symbols_json, window)

    if use_cache and CORPUS_CACHE.exists():
        try:
            blob = pickle.loads(CORPUS_CACHE.read_bytes())
            if blob.get("key") == cache_key:
                corpus = blob["corpus"]
                # Refresh status (cheap, depends on src + baselines)
                status_map, src_map = _load_fn_status(
                    src_dir=src_dir, baseline_path=baseline_path,
                    refresh=refresh_status, verbose=verbose,
                )
                for e in corpus.entries.values():
                    if e.name in status_map:
                        e.status, e.diff_byte_count = status_map[e.name]
                    else:
                        e.status, e.diff_byte_count = "undone", 0
                    if e.name in src_map:
                        e.src_file = src_map[e.name]
                corpus.build_index()
                _corpus_singleton = corpus
                if verbose:
                    typer.echo(f"sibling: corpus loaded from {CORPUS_CACHE} ({len(corpus.entries)} fns)", err=True)
                return corpus
        except Exception:
            pass  # fall through to rebuild

    if verbose:
        typer.echo("sibling: building corpus (~5–20s cold)…", err=True)
    t0 = time.time()

    sym = json.loads(symbols_json.read_text())
    code_syms = sorted(
        [s for s in sym["symbols"] if s.get("is_code")],
        key=lambda s: s["address"],
    )
    # Sizes: distance to next code symbol
    name_to_size: dict[str, int] = {}
    for i, s in enumerate(code_syms[:-1]):
        name_to_size[s["name"]] = code_syms[i + 1]["address"] - s["address"]

    status_map, src_map = _load_fn_status(
        src_dir=src_dir, baseline_path=baseline_path,
        refresh=refresh_status, verbose=verbose,
    )
    argc_map = _build_argc_map(src_dir)

    corpus = Corpus(window=window)
    skipped = 0
    for s in code_syms:
        name = s["name"]
        sz = name_to_size.get(name, 0)
        if sz <= 0 or sz > max_fn_size:
            skipped += 1
            continue
        try:
            _, _, lines = disasm_function(name)
        except Exception:
            skipped += 1
            continue
        tokens = tuple(normalize_insn(ln) for ln in lines)
        if len(tokens) < min_insns:
            skipped += 1
            continue
        sh = tuple(_shingle(list(tokens), window))
        st, dbc = status_map.get(name, ("undone", 0))
        pushes, frame, body_start = detect_prologue(lines)
        corpus.entries[name] = FnEntry(
            name=name,
            address=s["address"],
            size=sz,
            n_insns=len(tokens),
            tokens=tokens,
            shingles=sh,
            src_file=src_map.get(name),
            status=st,
            diff_byte_count=dbc,
            pushes=pushes,
            frame=frame,
            argc=argc_map.get(name),
            body_start=body_start,
        )

    corpus.build_index()

    if use_cache:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        # Drop the inv index from the pickle — it's rebuilt cheaply.
        blob = {
            "key": cache_key,
            "corpus": Corpus(window=window, entries=corpus.entries),
        }
        CORPUS_CACHE.write_bytes(pickle.dumps(blob, protocol=4))

    if verbose:
        typer.echo(
            f"sibling: corpus built ({len(corpus.entries)} fns, "
            f"{skipped} skipped) in {time.time()-t0:.1f}s",
            err=True,
        )

    _corpus_singleton = corpus
    return corpus


# ── Sibling search ──────────────────────────────────────────────────────────

@dataclass
class SiblingHit:
    score: float       # containment / jaccard / dice depending on metric
    common: int        # shared shingle count
    name: str
    status: str
    src_file: Optional[str]
    n_insns: int
    diff_byte_count: int


def find_siblings(
    query: str,
    *,
    top_n: int = 10,
    min_score: float = 0.10,
    metric: str = "containment",        # 'containment' | 'jaccard' | 'dice'
    filter_status: Optional[set[str]] = None,
    exclude_self: bool = True,
    corpus: Optional[Corpus] = None,
) -> list[SiblingHit]:
    """Find sibling functions ranked by shingle overlap.

    ``filter_status`` defaults to ``{'exact'}`` if None — we want to
    return *only* siblings whose C source is proven byte-exact, since
    those are the actionable templates.  Pass ``{'exact','diff','written'}``
    (or ``{'any'}`` via CLI) to widen the search.
    """
    if filter_status is None:
        filter_status = {"exact"}

    corpus = corpus or build_corpus()
    q = corpus.entries.get(query)
    if q is None:
        return []
    q_set = set(q.shingles)
    if not q_set:
        return []

    cand: Counter[str] = Counter()
    for h in q_set:
        for n in corpus.inv.get(h, ()):
            if exclude_self and n == query:
                continue
            cand[n] += 1

    out: list[SiblingHit] = []
    for n, common in cand.items():
        e = corpus.entries[n]
        if filter_status and e.status not in filter_status:
            continue
        e_set_len = len(set(e.shingles))
        if metric == "containment":
            score = common / len(q_set)
        elif metric == "jaccard":
            score = common / (len(q_set) + e_set_len - common)
        elif metric == "dice":
            score = 2 * common / (len(q_set) + e_set_len)
        else:
            raise ValueError(f"unknown metric {metric!r}")
        if score < min_score:
            continue
        out.append(SiblingHit(
            score=score, common=common, name=n,
            status=e.status, src_file=e.src_file,
            n_insns=e.n_insns, diff_byte_count=e.diff_byte_count,
        ))
    out.sort(key=lambda h: (-h.score, -h.common, h.n_insns))
    return out[:top_n]


# ── Submatch (contiguous shingle runs) ──────────────────────────────────────

@dataclass
class SubmatchRun:
    query_insn_start: int
    donor_insn_start: int
    length: int          # in *instructions*, not shingles


def find_submatches(
    query: str,
    donor: str,
    *,
    min_run: int = 6,    # in instructions
    corpus: Optional[Corpus] = None,
) -> list[SubmatchRun]:
    """Find contiguous shingle runs shared by ``query`` and ``donor``.

    Returns instruction-range pairs, sorted by query start.  Greedy
    longest-match advance: at each position in ``query``, take the
    longest run extension found in ``donor``, then skip past it.
    """
    corpus = corpus or build_corpus()
    q = corpus.entries.get(query)
    d = corpus.entries.get(donor)
    if q is None or d is None:
        return []
    qh, dh = list(q.shingles), list(d.shingles)
    w = corpus.window
    min_run_shingles = max(1, min_run - w + 1)

    # Build position map in donor
    dpos: dict[int, list[int]] = defaultdict(list)
    for i, h in enumerate(dh):
        dpos[h].append(i)

    runs: list[SubmatchRun] = []
    i = 0
    while i < len(qh):
        best: Optional[tuple[int, int]] = None  # (donor_start, length_shingles)
        for dj in dpos.get(qh[i], ()):
            ln = 1
            while i + ln < len(qh) and dj + ln < len(dh) and qh[i + ln] == dh[dj + ln]:
                ln += 1
            if best is None or ln > best[1]:
                best = (dj, ln)
        if best is not None and best[1] >= min_run_shingles:
            runs.append(SubmatchRun(
                query_insn_start=i,
                donor_insn_start=best[0],
                length=best[1] + w - 1,
            ))
            i += best[1]
        else:
            i += 1
    return runs


# ── Structural-twin search & survey ─────────────────────────────────────

@dataclass
class StructureTwin:
    name: str
    status: str
    src_file: Optional[str]
    frame: int
    argc: Optional[int]
    n_insns: int
    opening_prefix: int   # leading post-prologue tokens identical to query
    cross_family: bool    # in a DIFFERENT source file than the query


def structure_signature(e: FnEntry) -> tuple:
    """The (pushes, frame, argc) triple that defines a structural twin."""
    return (e.pushes, e.frame, e.argc)


def _opening(e: FnEntry) -> tuple[str, ...]:
    return e.tokens[e.body_start:e.body_start + OPENING_WINDOW]


def find_structure_twins(
    query: str,
    *,
    top_n: int = 10,
    filter_status: Optional[set[str]] = None,
    cross_family_only: bool = False,
    corpus: Optional[Corpus] = None,
) -> list[StructureTwin]:
    """Functions sharing the query's (pushes, frame, argc) signature,
    ranked by how deep their opening instruction SHAPE agrees.

    ``filter_status`` defaults to ``{'exact'}`` -- a byte-exact twin is
    the actionable one (it proves the prologue+opening is achievable).
    Set ``cross_family_only`` to drop same-file siblings, surfacing the
    UNRELATED structural twins (the diagnostic the survey is about).
    """
    if filter_status is None:
        filter_status = {"exact"}
    corpus = corpus or build_corpus()
    q = corpus.entries.get(query)
    if q is None:
        return []
    qsig = structure_signature(q)
    qopen = _opening(q)
    out: list[StructureTwin] = []
    for e in corpus.entries.values():
        if e.name == query:
            continue
        if filter_status and e.status not in filter_status:
            continue
        if structure_signature(e) != qsig:
            continue
        cross = e.src_file != q.src_file
        if cross_family_only and not cross:
            continue
        out.append(StructureTwin(
            name=e.name, status=e.status, src_file=e.src_file,
            frame=e.frame, argc=e.argc, n_insns=e.n_insns,
            opening_prefix=_shared_prefix(qopen, _opening(e)),
            cross_family=cross,
        ))
    # deepest opening agreement first; cross-family before same-file.
    out.sort(key=lambda t: (-t.opening_prefix, not t.cross_family, t.n_insns))
    return out[:top_n]


def _classify_diff(in_prolog: bool, depth: Optional[int],
                   has_frame_delta: bool) -> str:
    if has_frame_delta:
        return "A:frame-wrong-stack"
    if in_prolog:
        return "B:prologue-push-set"
    if depth is None:
        return "?:no-divergence-data"
    if depth <= 0:
        return "C:instr-select-stmt1"
    if depth <= 9:
        return "D:early-body"
    return "E:deep-body"


def structure_survey(
    *,
    corpus: Optional[Corpus] = None,
    verify_json: Path = Path(".c2-cache/verify.json"),
) -> dict:
    """Corpus-wide structural diagnosis of the diff corpus.

    Matches every diffing function against the byte-exact corpus by
    (pushes, frame, argc) + opening shape, then enriches with the
    decomp-verify cache (``frame_hint`` -> wrong-stack detection;
    first-divergence row -> divergence depth) when present.  Returns a
    JSON-able dict; ``_render_survey`` prints it.
    """
    corpus = corpus or build_corpus()
    exact = [e for e in corpus.entries.values() if e.status == "exact"]
    diff = [e for e in corpus.entries.values() if e.status == "diff"]

    by_sig: dict = defaultdict(list)
    by_push: dict = defaultdict(list)
    by_push_frame: dict = defaultdict(list)
    for e in exact:
        by_sig[structure_signature(e)].append(e)
        by_push[e.pushes].append(e)
        by_push_frame[(e.pushes, e.frame)].append(e)

    # Optional decomp-verify enrichment (frame delta + first-divergence).
    fh: dict = {}
    first_diff: dict = {}
    rule_hints: dict = {}
    if verify_json.exists():
        try:
            v = json.loads(verify_json.read_text())
            for f in v.get("functions", []):
                fh[f["name"]] = f.get("frame_hint")
                rule_hints[f["name"]] = f.get("rule_hints") or {}
                vr = f.get("rows") or []
                first_diff[f["name"]] = next(
                    (i for i, r in enumerate(vr)
                     if r.get("kind") != "equal"), None)
        except (OSError, ValueError):
            pass

    rows = []
    for e in diff:
        sig = structure_signature(e)
        twins = by_sig.get(sig, [])
        xtwins = [t for t in twins if t.src_file != e.src_file]
        qopen = _opening(e)
        best_pref, best = -1, None
        for t in xtwins:
            p = _shared_prefix(qopen, _opening(t))
            if p > best_pref:
                best_pref, best = p, t
        frame_hint = fh.get(e.name)
        fdr = first_diff.get(e.name)
        in_prolog = (fdr is not None and fdr < e.body_start)
        depth = (fdr - e.body_start) if fdr is not None else None
        cls = _classify_diff(in_prolog, depth, bool(frame_hint))
        if twins:
            uniq = "has-twin"
        elif by_push.get(e.pushes) and not by_push_frame.get((e.pushes, e.frame)):
            uniq = "unique-frame"
        elif by_push.get(e.pushes):
            uniq = "unique-argc"
        else:
            uniq = "unique-pushset"
        rows.append({
            "name": e.name, "file": e.src_file,
            "diff_bytes": e.diff_byte_count,
            "pushes": "".join(p[1:] for p in e.pushes) or "-",
            "frame": e.frame, "argc": e.argc, "n_insns": e.n_insns,
            "class": cls, "uniqueness": uniq,
            "twin_count": len(twins),
            "xtwin": best.name if best else None,
            "xtwin_file": best.src_file if best else None,
            "xtwin_opening": best_pref if best else -1,
            "frame_delta": (frame_hint or {}).get("delta"),
            "ps_frame": (frame_hint or {}).get("ps_frame"),
            "rc_frame": (frame_hint or {}).get("rc_frame"),
            "regswap": bool({"Reg swap", "Byte-reg swap"}
                            & set(rule_hints.get(e.name, {}))),
        })

    return {
        "n_diff": len(diff), "n_exact": len(exact),
        "enriched": bool(fh),
        "partition": dict(Counter(r["class"] for r in rows)),
        "uniqueness": dict(Counter(r["uniqueness"] for r in rows)),
        "regswap": sum(1 for r in rows if r["regswap"]),
        "cross_family_twin": sum(1 for r in rows if r["xtwin"]),
        "rows": rows,
    }


# ── decomp-verify hint integration ──────────────────────────────────────────

def render_sibling_hint(
    name: str,
    *,
    top_n: int = 3,
    min_score: float = 0.20,
    corpus: Optional[Corpus] = None,
) -> Optional[str]:
    """Render a one-line ``Sibling:`` hint string for decomp-verify -v.

    Returns None when no sibling clears the threshold.  Filtered to
    byte-exact siblings only — those are the actionable templates.

    Sets ``_in_verify_hint`` for the duration of the call so the
    status refresher doesn't recursively invoke ``decomp-verify``
    (we're already inside one).
    """
    global _in_verify_hint
    prev = _in_verify_hint
    _in_verify_hint = True
    try:
        hits = find_siblings(
            name,
            top_n=top_n,
            min_score=min_score,
            filter_status={"exact"},
            corpus=corpus,
        )
    except Exception:
        return None
    finally:
        _in_verify_hint = prev
    if not hits:
        return None
    parts = []
    for h in hits:
        loc = f" ({h.src_file})" if h.src_file else ""
        parts.append(f"{h.name}{loc} {h.score*100:.0f}%")
    return "; ".join(parts)


# ── CLI ─────────────────────────────────────────────────────────────────────

_STATUS_COLORS = {
    "exact":   "green",
    "diff":    "yellow",
    "written": "cyan",
    "undone":  "dim",
}


def _render_table(query: str, hits: list[SiblingHit], q_entry: FnEntry) -> None:
    typer.echo(
        f"\n  query: {query}  ({q_entry.n_insns} insns, "
        f"status={q_entry.status}"
        + ")"
    )
    if not hits:
        typer.echo("  no siblings above threshold")
        return
    name_w = max(4, max(len(h.name) for h in hits))
    file_w = max(4, max(len(h.src_file or "") for h in hits))
    header = (
        f"  {'score':>6}  {'common':>6}  {'insn':>5}  "
        f"{'status':<7}  {'name':<{name_w}}  {'file':<{file_w}}"
    )
    typer.echo(header)
    typer.echo("  " + "-" * (len(header) - 2))
    for h in hits:
        typer.echo(
            f"  {h.score*100:5.1f}%  {h.common:>6}  {h.n_insns:>5}  "
            f"{h.status:<7}  {h.name:<{name_w}}  {(h.src_file or ''):<{file_w}}"
        )


def _render_structure_twins(query: str, twins: list[StructureTwin],
                            q: FnEntry) -> None:
    typer.echo(
        f"\n  structural twins of {query}  "
        f"(pushes=[{','.join(q.pushes) or '-'}] frame={q.frame} "
        f"argc={q.argc} insns={q.n_insns} status={q.status})"
    )
    if not twins:
        typer.echo(
            "  no byte-exact function shares this (pushes, frame, argc) "
            "signature\n  -- candidate STRUCTURAL defect (wrong frame / "
            "arg count); cross-check the Frame hint."
        )
        return
    name_w = max(4, max(len(t.name) for t in twins))
    file_w = max(4, max(len(t.src_file or "") for t in twins))
    typer.echo(
        f"  {'open':>4}  {'xfam':>4}  {'insn':>5}  {'status':<7}  "
        f"{'name':<{name_w}}  {'file':<{file_w}}"
    )
    for t in twins:
        typer.echo(
            f"  {t.opening_prefix:>4}  {('yes' if t.cross_family else '-'):>4}  "
            f"{t.n_insns:>5}  {t.status:<7}  {t.name:<{name_w}}  "
            f"{(t.src_file or ''):<{file_w}}"
        )
    typer.echo(
        "\n  open = leading post-prologue instructions whose SHAPE matches; "
        "xfam = different\n  source file (the non-sibling structural twin)."
    )


def _render_survey(s: dict) -> None:
    typer.echo(
        f"\n  STRUCTURE SURVEY — {s['n_diff']} diffing vs {s['n_exact']} "
        f"byte-exact"
        + ("" if s["enriched"]
           else "  (no .c2-cache/verify.json: classes A/B/C/D/E degraded)")
    )
    labels = {
        "A:frame-wrong-stack": "wrong stack frame (ps!=rc) — STRUCTURAL",
        "B:prologue-push-set": "wrong callee-save set — WorthProlog/Rule 89",
        "C:instr-select-stmt1": "instr-select at 1st statement",
        "D:early-body": "early-body regalloc residue",
        "E:deep-body": "deep-body regalloc residue",
        "?:no-divergence-data": "no divergence data",
    }
    typer.echo("\n  diagnostic partition:")
    for k in ("A:frame-wrong-stack", "B:prologue-push-set",
              "C:instr-select-stmt1", "D:early-body", "E:deep-body",
              "?:no-divergence-data"):
        if k in s["partition"]:
            typer.echo(f"    {k:22} {s['partition'][k]:3}  {labels[k]}")
    typer.echo("\n  structural-twin coverage:")
    typer.echo(
        f"    {s['cross_family_twin']:3}/{s['n_diff']}  have a CROSS-FAMILY "
        "byte-exact twin (shape proven right; residue is regalloc)"
    )
    typer.echo(
        f"    {s['regswap']:3}/{s['n_diff']}  carry a Reg/Byte-reg swap hint"
    )
    typer.echo("\n  prolog-signature uniqueness:")
    for k in ("has-twin", "unique-frame", "unique-argc", "unique-pushset"):
        if k in s["uniqueness"]:
            typer.echo(f"    {k:14} {s['uniqueness'][k]:3}")
    wrong = [r for r in s["rows"] if r["class"] == "A:frame-wrong-stack"]
    if wrong:
        wrong.sort(key=lambda r: -abs(r["frame_delta"] or 0))
        typer.echo(
            f"\n  wrong-stack-size cohort ({len(wrong)}) — highest structural "
            "leverage:"
        )
        for r in wrong[:20]:
            ps = r["ps_frame"] if r["ps_frame"] is not None else "?"
            rc = r["rc_frame"] if r["rc_frame"] is not None else "?"
            d = r["frame_delta"] or 0
            typer.echo(
                f"    {r['name']:30} ps={ps:>4} rc={rc:>4} delta={d:+4}  "
                f"db={r['diff_bytes']}"
            )
    deep = [r for r in s["rows"] if r["xtwin"] and r["xtwin_opening"] >= 4]
    if deep:
        deep.sort(key=lambda r: -r["xtwin_opening"])
        typer.echo(
            f"\n  deep cross-family twins ({len(deep)}) — shape proven "
            "correct, residue is regalloc:"
        )
        for r in deep[:15]:
            typer.echo(
                f"    {r['name']:28} ~~ {r['xtwin']:26} open={r['xtwin_opening']} "
                f"({r['class'][:1]}) db={r['diff_bytes']}"
            )
    typer.echo(
        "\n  drill in:  c2 sibling <fn> --structure --cross-family   "
        "|   --json for the full table"
    )


def sibling(
    query: Annotated[
        Optional[str],
        typer.Argument(help="Function name to search siblings for.  "
                            "Omit with --all for a corpus-wide report."),
    ] = None,
    top_n: Annotated[
        int,
        typer.Option("--top", "-n", help="Show top N siblings per query."),
    ] = 10,
    min_score: Annotated[
        float,
        typer.Option("--min-score",
                     help="Minimum containment/Jaccard/Dice score (0.0–1.0)."),
    ] = 0.10,
    metric: Annotated[
        str,
        typer.Option("--metric",
                     help="containment | jaccard | dice"),
    ] = "containment",
    status_filter: Annotated[
        str,
        typer.Option("--status",
                     help="Filter siblings: exact | any | written | diff. "
                          "Comma-separated for multiple."),
    ] = "exact",
    window: Annotated[
        int,
        typer.Option("--window", "-w",
                     help="Shingle window size in instructions."),
    ] = 5,
    submatch_with: Annotated[
        Optional[str],
        typer.Option("--submatch",
                     help="Print contiguous shingle runs between "
                          "<query> and this donor function."),
    ] = None,
    min_run: Annotated[
        int,
        typer.Option("--min-run",
                     help="Submatch: minimum run length in instructions."),
    ] = 6,
    all_diffs: Annotated[
        bool,
        typer.Option("--all", "-a",
                     help="Report top sibling per diffing function "
                          "(corpus-wide ranking)."),
    ] = False,
    baseline: Annotated[
        Optional[Path],
        typer.Option("--baseline",
                     help="Path to baseline JSON.  When omitted: prefer "
                          ".c2-cache/sibling-status.json if fresh, then "
                          "the newest baselines/*.json if fresh, then "
                          "auto-regenerate via decomp-verify."),
    ] = None,
    refresh_status: Annotated[
        bool,
        typer.Option("--refresh-status",
                     help="Force a fresh decomp-verify run to derive "
                          "exact/diff status, ignoring all cached "
                          "baselines."),
    ] = False,
    as_json: Annotated[
        bool,
        typer.Option("--json", help="Emit JSON."),
    ] = False,
    rebuild: Annotated[
        bool,
        typer.Option("--rebuild",
                     help="Force corpus rebuild (ignore cache)."),
    ] = False,
    structure: Annotated[
        bool,
        typer.Option("--structure", "-S",
                     help="Structural-twin lens: match by stack frame, arg "
                          "count and opening-instruction shape instead of "
                          "fuzzy shingles."),
    ] = False,
    survey: Annotated[
        bool,
        typer.Option("--survey",
                     help="Corpus-wide structural diagnosis of the diff "
                          "corpus (the structure lens, all functions)."),
    ] = False,
    cross_family: Annotated[
        bool,
        typer.Option("--cross-family",
                     help="Structural mode: show only twins in a DIFFERENT "
                          "source file (the non-sibling structural matches)."),
    ] = False,
) -> None:
    """Find decompiled siblings of a PS.EXE function via fuzzy ASM match,
    or STRUCTURAL twins by prologue signature (--structure / --survey).

    Examples::

        # Top 10 byte-exact siblings of a diffing function
        uv run c2 sibling barbarian_in_region

        # Widen to any decompiled function, top 5
        uv run c2 sibling action --status any --top 5

        # Show contiguous instruction ranges that match
        uv run c2 sibling barbarian_in_region --submatch raider_in_region

        # Corpus-wide: best sibling for every diffing function
        uv run c2 sibling --all --min-score 0.30

        # Structural twins (frame/args/opening) of one diffing function
        uv run c2 sibling build_city_item --structure
        uv run c2 sibling build_city_item --structure --cross-family

        # Corpus-wide structural diagnosis of the whole diff corpus
        uv run c2 sibling --survey
    """
    corpus = build_corpus(
        window=window,
        baseline_path=baseline,
        refresh_status=refresh_status,
        use_cache=not rebuild,
        verbose=not as_json,
    )

    # Parse status filter
    if status_filter.lower() == "any":
        fs: Optional[set[str]] = {"exact", "diff", "written"}
    else:
        fs = {x.strip() for x in status_filter.split(",") if x.strip()}

    # --survey: corpus-wide structural diagnosis
    if survey:
        s = structure_survey(corpus=corpus)
        if as_json:
            typer.echo(json.dumps(s, indent=2))
        else:
            _render_survey(s)
        return

    # --structure: the structural-twin lens (single fn or --all)
    if structure:
        if all_diffs:
            pool = [e for e in corpus.entries.values() if e.status == "diff"]
            pool.sort(key=lambda e: -e.diff_byte_count)
            rows = []
            for e in pool:
                tw = find_structure_twins(
                    e.name, top_n=1, filter_status=fs,
                    cross_family_only=cross_family, corpus=corpus)
                t = tw[0] if tw else None
                rows.append({
                    "query": e.name, "diff_bytes": e.diff_byte_count,
                    "frame": e.frame, "argc": e.argc,
                    "twin": t.name if t else None,
                    "twin_file": t.src_file if t else None,
                    "opening_prefix": t.opening_prefix if t else -1,
                    "cross_family": t.cross_family if t else None,
                })
            if as_json:
                typer.echo(json.dumps({"rows": rows}, indent=2))
                return
            typer.echo(
                "\n  best structural twin per diffing function (status "
                f"{sorted(fs) if fs else 'any'}"
                + (", cross-family only" if cross_family else "") + "):"
            )
            typer.echo(
                f"  {'open':>4}  {'diff_b':>6}  {'query':<30}  →  "
                f"{'twin':<28}  {'file':<14}"
            )
            for r in rows:
                tw = r["twin"] or "(none — unique signature)"
                typer.echo(
                    f"  {r['opening_prefix']:>4}  {r['diff_bytes']:>6}  "
                    f"{r['query']:<30}  →  {tw:<28}  {r['twin_file'] or '':<14}"
                )
            return
        if query is None:
            typer.echo("--structure needs a query function "
                       "(or --all / --survey)", err=True)
            raise typer.Exit(2)
        q_entry = corpus.entries.get(query)
        if q_entry is None:
            typer.echo(f"unknown function: {query}", err=True)
            raise typer.Exit(1)
        twins = find_structure_twins(
            query, top_n=top_n, filter_status=fs,
            cross_family_only=cross_family, corpus=corpus)
        if as_json:
            typer.echo(json.dumps({
                "query": query, "pushes": list(q_entry.pushes),
                "frame": q_entry.frame, "argc": q_entry.argc,
                "twins": [t.__dict__ for t in twins],
            }, indent=2))
            return
        _render_structure_twins(query, twins, q_entry)
        return

    # --submatch mode
    if submatch_with is not None:
        if query is None:
            typer.echo("--submatch requires a query argument", err=True)
            raise typer.Exit(2)
        runs = find_submatches(
            query, submatch_with, min_run=min_run, corpus=corpus,
        )
        if as_json:
            typer.echo(json.dumps({
                "query": query, "donor": submatch_with,
                "runs": [r.__dict__ for r in runs],
            }, indent=2))
            return
        q_e = corpus.entries.get(query)
        d_e = corpus.entries.get(submatch_with)
        if q_e is None or d_e is None:
            typer.echo(f"unknown function: {query if q_e is None else submatch_with}", err=True)
            raise typer.Exit(1)
        typer.echo(
            f"\n  {query} ({q_e.n_insns} insns) ~~ {submatch_with} "
            f"({d_e.n_insns} insns)"
        )
        if not runs:
            typer.echo(f"  no contiguous runs of ≥ {min_run} insns")
            return
        for r in runs:
            typer.echo(
                f"  query[{r.query_insn_start:4d}..{r.query_insn_start+r.length-1:4d}]  "
                f"== donor[{r.donor_insn_start:4d}..{r.donor_insn_start+r.length-1:4d}]  "
                f"({r.length} insns)"
            )
        return

    # --all mode: corpus-wide report
    if all_diffs:
        pool = [
            e for e in corpus.entries.values()
            if e.status == "diff"
        ]
        pool.sort(key=lambda e: -e.diff_byte_count)
        rows = []
        for e in pool:
            hits = find_siblings(
                e.name, top_n=1, min_score=min_score,
                filter_status=fs, corpus=corpus, metric=metric,
            )
            if not hits:
                continue
            h = hits[0]
            rows.append({
                "query": e.name,
                "query_insns": e.n_insns,
                "query_diff_bytes": e.diff_byte_count,
                "sibling": h.name,
                "sibling_status": h.status,
                "sibling_src_file": h.src_file,
                "sibling_insns": h.n_insns,
                "score": h.score,
                "common": h.common,
            })
        if as_json:
            typer.echo(json.dumps({"rows": rows}, indent=2))
            return
        if not rows:
            typer.echo("no sibling pairs above threshold")
            return
        rows.sort(key=lambda r: -r["score"])
        if top_n > 0:
            rows = rows[:top_n] if top_n < len(rows) else rows
        typer.echo(
            f"\n  best {metric} sibling per diffing function "
            f"(≥ {min_score*100:.0f}%, status filter: {sorted(fs) if fs else 'any'}):"
        )
        typer.echo(
            f"  {'score':>6}  {'diff_b':>6}  {'query':<32}  →  "
            f"{'sibling':<32}  {'file':<14}"
        )
        for r in rows:
            typer.echo(
                f"  {r['score']*100:5.1f}%  {r['query_diff_bytes']:>6}  "
                f"{r['query']:<32}  →  {r['sibling']:<32}  "
                f"{r['sibling_src_file'] or '':<14}"
            )
        return

    # Single-query mode
    if query is None:
        typer.echo("specify a query function or pass --all", err=True)
        raise typer.Exit(2)
    q_entry = corpus.entries.get(query)
    if q_entry is None:
        typer.echo(f"unknown function: {query}", err=True)
        raise typer.Exit(1)

    hits = find_siblings(
        query, top_n=top_n, min_score=min_score,
        filter_status=fs, corpus=corpus, metric=metric,
    )

    if as_json:
        typer.echo(json.dumps({
            "query": query,
            "query_insns": q_entry.n_insns,
            "query_status": q_entry.status,
            "metric": metric,
            "min_score": min_score,
            "filter_status": sorted(fs) if fs else None,
            "hits": [h.__dict__ for h in hits],
        }, indent=2))
        return

    _render_table(query, hits, q_entry)
