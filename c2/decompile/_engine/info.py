"""``info`` builder \u2014 unified structural + neighbor data for one function.

The agent's most common upfront need is "tell me everything you know
about this function so I don't have to grep around".  ``info`` returns:

* **identity** \u2014 name, address, size, source TU, signature line
* **shape** \u2014 prologue saved registers, stack frame size, argc, source
  line range
* **calls** \u2014 names of functions this one calls (cross-references)
* **types** \u2014 struct/typedef definitions referenced by the function's
  signature, lifted verbatim from the project headers (so the agent
  doesn't have to grep through 100KB of entities.h to find ``slider_rec``)
* **siblings** \u2014 top-N byte-exact functions whose asm clusters near
  this one in the embedding index
* **tail-merge / fall-through** \u2014 cross-function elision relationships

For the run's own function, ``compose`` pre-renders this as ``info.md``
in the run dir.  For OTHER functions, the agent calls ``info(name)``
on demand.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, asdict
from pathlib import Path

import capstone

from c2.decompile._engine.project import ProjectConfig


@dataclass(frozen=True)
class CallInfo:
    name: str
    times: int


@dataclass(frozen=True)
class TypeInfo:
    name: str
    header: str
    definition: str


@dataclass(frozen=True)
class SiblingInfo:
    """A structurally-similar sibling function (5-insn shingle containment).

    Siblings are useful as templates regardless of their byte-exact status:

    * **byte-exact** siblings are ready-to-copy source patterns.
    * **diffing** siblings show what NOT to do (or share a residue you may
      already understand) -- they often instantiate the same source family
      and Watcom codegen quirk.
    * **annotated** (written, no verify data) siblings at least have
      readable C source.

    ``status`` is one of ``"byte_exact"`` / ``"diffing"`` / ``"annotated"``.
    ``byte_diff`` is the raw bytes of divergence (0 for byte-exact / annotated).
    ``shape_summary`` is the compact layered shape distance for diffing
    siblings, e.g. ``"ir 2/14 -> ir"`` (the dominant fix-next layer); None
    for byte-exact and annotated.
    """
    name: str
    score: float
    status: str = "byte_exact"           # 'byte_exact' | 'diffing' | 'annotated'
    byte_diff: int = 0                    # 0 for byte-exact / annotated
    shape_summary: str | None = None      # compact 'ir N/T -> layer' for diffing


@dataclass(frozen=True)
class NameRelative:
    """A function that shares a template-instantiation pattern in its name.

    These are the OBVIOUS sister patterns the Caesar II source is full
    of — zoom-level variants (``place_*`` / ``place2_*`` / ``place3_*``),
    render layers (``*_top`` / ``*_base`` / ``*_roof``), directions
    (``up_`` / ``down_``), sides (``with_sides`` / ``no_sides``), …  When
    one of these is byte-exact, its source is the single best
    PS-faithful template to copy structure from.
    """
    name: str
    pattern: str           # short description of how it relates ("zoom 2→3")
    status: str            # 'byte-exact' | 'diffing' | 'unknown'
    byte_diff: int = 0     # 0 for byte-exact / unknown; raw diff bytes for diffing
    source_file: str | None = None


@dataclass(frozen=True)
class FunctionInfo:
    name: str
    address_hex: str
    size: int
    source_file: str | None
    signature: str | None
    source_line_range: tuple[int, int] | None
    prologue_pushes: tuple[str, ...]
    frame_size: int
    argc: int | None
    calls: tuple[CallInfo, ...]
    types: tuple[TypeInfo, ...]
    siblings: tuple[SiblingInfo, ...]
    name_relatives: tuple[NameRelative, ...]
    tail_merge_donor: str | None
    fallthrough_callee: str | None

    def to_dict(self) -> dict:
        d = asdict(self)
        d["source_line_range"] = list(self.source_line_range) if self.source_line_range else None
        d["prologue_pushes"] = list(self.prologue_pushes)
        d["calls"] = [asdict(c) for c in self.calls]
        d["types"] = [asdict(t) for t in self.types]
        d["siblings"] = [asdict(s) for s in self.siblings]
        d["name_relatives"] = [asdict(r) for r in self.name_relatives]
        return d


def info(project: ProjectConfig, function_name: str,
         *, siblings_top: int = 8) -> FunctionInfo:
    """Compute :class:`FunctionInfo` for one function."""
    tc = project.toolchain()
    finfo = tc.function_info(function_name)
    fb = tc.function_bytes(function_name)
    fix = tc.function_fixups(function_name)

    #  shape (prologue / frame / argc)
    insns = tc.disassemble(fb, finfo.address, fix)
    pushes, frame = _prologue(insns)
    argc = _argc_from_signature(finfo.signature)

    #  source line range
    line_marks = tc.line_numbers(function_name)
    line_range = (
        (min(l for _, l in line_marks), max(l for _, l in line_marks))
        if line_marks else None
    )

    #  calls (cross-fn)
    calls = _collect_calls(insns)

    #  types referenced by signature
    types = _resolve_types(project, finfo.signature)

    #  siblings via embedding NN
    siblings = _siblings(project, function_name, siblings_top)

    #  name-pattern relatives (template-instantiation variants)
    name_relatives = _name_relatives(function_name)

    #  cross-function elision (toolchain-specific: Watcom detects
    #  tail-merge donors + fall-through callees; MSVC returns (None, None)).
    try:
        tm_donor, ft_callee = tc.detect_cross_function_elision(function_name)
    except Exception:
        tm_donor, ft_callee = None, None

    return FunctionInfo(
        name=function_name,
        address_hex=f"0x{finfo.address:x}",
        size=finfo.size,
        source_file=finfo.source_file,
        signature=finfo.signature,
        source_line_range=line_range,
        prologue_pushes=tuple(pushes),
        frame_size=frame,
        argc=argc,
        calls=tuple(calls),
        types=tuple(types),
        siblings=tuple(siblings),
        name_relatives=tuple(name_relatives),
        tail_merge_donor=tm_donor,
        fallthrough_callee=ft_callee,
    )


def render_info_md(fi: FunctionInfo) -> str:
    """Render :class:`FunctionInfo` as a compact Markdown brief for the agent.

    Focuses on what the agent CAN'T see from scratch.c + target/asm.txt
    alone: types referenced by the signature, nearest sibling functions,
    cross-function elision relationships (tail-merge donor, fall-through
    callee), and the resolved cross-function call list.  Things visible
    in the asm or scratch source (address, signature, prologue saves,
    frame size) are omitted as noise.
    """
    lines: list[str] = []
    lines.append(f"# {fi.name}")
    lines.append("")

    if fi.tail_merge_donor or fi.fallthrough_callee:
        lines.append("## Cross-function elision")
        if fi.tail_merge_donor:
            lines.append(
                f"- **tail-merge donor**: `{fi.tail_merge_donor}` \u2014 the target's "
                f"trailing `jmp` lands inside this sibling; verify accounts for it."
            )
        if fi.fallthrough_callee:
            lines.append(
                f"- **falls through into**: `{fi.fallthrough_callee}` \u2014 PS emits "
                f"no explicit call here; verify ignores the trailing standalone emission."
            )
        lines.append("")

    if fi.calls:
        lines.append("## Cross-function calls")
        for c in fi.calls:
            tag = f" \u00d7{c.times}" if c.times > 1 else ""
            lines.append(f"- `{c.name}`{tag}")
        lines.append("")

    if fi.types:
        lines.append("## Types referenced by signature")
        for t in fi.types:
            lines.append(f"### `struct {t.name}`  ({t.header})")
            lines.append("```c")
            lines.append(t.definition.strip())
            lines.append("```")
            lines.append("")

    if fi.name_relatives:
        lines.append("## Name-pattern relatives (template-instantiated variants)")
        lines.append(
            "Caesar II's render/UI code is heavily template-instantiated by "
            "zoom level (`_` / `2` / `3`), render layer (`_top` / `_base` / "
            "`_roof`), direction (`up_` / `down_`), with/no sides, etc.  Each "
            "row below is a function whose name differs from this one by "
            "exactly one such token.  A **byte-exact** relative is the single "
            "strongest PS-faithful structural template available — its source "
            "shows exactly the shape PS expects for this family.  Use "
            "`fetch(<name>)` for the C source."
        )
        lines.append("")
        for r in fi.name_relatives:
            status_tag = {
                "byte-exact": "✓ byte-exact",
                "diffing":    f"✗ diffing ({r.byte_diff}b)",
                "unknown":    "· unknown",
            }.get(r.status, r.status)
            src = f"  ({r.source_file})" if r.source_file else ""
            lines.append(f"- `{r.name}`  — {r.pattern}  — {status_tag}{src}")
        lines.append("")

    if fi.siblings:
        lines.append("## Structural siblings (5-insn shingle containment)")
        lines.append(
            "Score = fraction of this function's asm shingles that also appear "
            "in the sibling's body.  High score = structural twin (same shape, "
            "likely same source family).  Use `fetch(<name>)` for the C source, "
            "`disasm(<name>)` for the target asm."
        )
        lines.append("")
        lines.append(
            "Per-sibling status:  **byte-exact** = ready-to-copy source template; "
            "**diffing** = same family but not byte-exact yet (residue may be the "
            "same lever you're chasing -- bytes + fix-next layer shown); "
            "**annotated** = source written but verify status unknown."
        )
        lines.append("")
        for s in fi.siblings:
            if s.status == "byte_exact":
                tag = "**byte-exact**"
            elif s.status == "diffing":
                if s.shape_summary:
                    tag = f"diffing  {s.byte_diff}b  {s.shape_summary}"
                else:
                    tag = f"diffing  {s.byte_diff}b"
            else:  # 'annotated'
                tag = "annotated (verify status unknown)"
            lines.append(f"- `{s.name}`  (score: {s.score:.3f})  -- {tag}")

    return "\n".join(lines) + "\n"


#  helpers


_PUSH_REG_RE = re.compile(r"^push\s+(e[abcd]x|esi|edi|ebp|esp)$", re.IGNORECASE)
_SUB_ESP_RE = re.compile(r"^sub\s+esp,\s*(?:0x([0-9a-fA-F]+)|(\d+))$", re.IGNORECASE)


def _prologue(insns) -> tuple[list[str], int]:
    """Extract prologue: leading pushes + ``sub esp, N`` (if present)."""
    pushes: list[str] = []
    frame = 0
    for ins in insns:
        text = f"{ins.mnemonic} {ins.op_str}".strip()
        m = _PUSH_REG_RE.match(text)
        if m:
            pushes.append(m.group(1).upper())
            continue
        m = _SUB_ESP_RE.match(text)
        if m:
            frame = int(m.group(1), 16) if m.group(1) else int(m.group(2))
        break
    return pushes, frame


def _argc_from_signature(sig: str | None) -> int | None:
    """Count parameters in a C signature line."""
    if not sig:
        return None
    m = re.search(r"\(([^)]*)\)", sig)
    if not m:
        return None
    params = m.group(1).strip()
    if params == "" or params.lower() == "void":
        return 0
    # Crude: count top-level commas + 1; this is good enough for typical
    # Caesar II signatures which don't nest parentheses in parameter types.
    depth = 0
    n = 1
    for c in params:
        if c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
        elif c == "," and depth == 0:
            n += 1
    return n


def _collect_calls(insns) -> list[CallInfo]:
    """Extract distinct call/jmp targets that resolved to function names."""
    counts: dict[str, int] = {}
    order: list[str] = []
    for ins in insns:
        if ins.mnemonic not in ("call", "jmp"):
            continue
        op = ins.op_str
        # symbol-resolved render is just `<name>` or `<name>+0x<delta>`
        if "ptr" in op or "[" in op or op.startswith(".L_"):
            continue
        # Anything that looks like a hex literal (unresolved) we skip.
        if op.startswith("0x"):
            continue
        # Strip +0xN displacement for grouping
        base = op.split("+")[0]
        if not re.match(r"^[A-Za-z_][\w$]*$", base):
            continue
        if base not in counts:
            order.append(base)
        counts[base] = counts.get(base, 0) + 1
    return [CallInfo(name=n, times=counts[n]) for n in order]


_TYPE_REF_RE = re.compile(r"\bstruct\s+(\w+)")


def _resolve_types(project: ProjectConfig, signature: str | None) -> list[TypeInfo]:
    """Find every ``struct NAME`` mentioned in the signature, lift its
    definition from project headers.
    """
    if not signature:
        return []
    type_names = list({m.group(1) for m in _TYPE_REF_RE.finditer(signature)})
    if not type_names:
        return []
    out: list[TypeInfo] = []
    seen: set[str] = set()
    for header in sorted(project.headers_dir.glob("*.h")):
        text = header.read_text()
        for name in type_names:
            if name in seen:
                continue
            span = _find_struct_span(text, name)
            if span is None:
                continue
            out.append(TypeInfo(
                name=name,
                header=header.name,
                definition=text[span[0]:span[1]],
            ))
            seen.add(name)
    return out


def _find_struct_span(text: str, name: str) -> tuple[int, int] | None:
    """Locate ``struct NAME { ... };`` in ``text`` via brace matching."""
    pat = re.compile(rf"\bstruct\s+{re.escape(name)}\s*\{{")
    m = pat.search(text)
    if not m:
        return None
    open_brace = m.end() - 1
    depth = 1
    i = open_brace + 1
    n = len(text)
    while i < n and depth > 0:
        c = text[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
        i += 1
    if depth != 0:
        return None
    # Consume optional trailing identifier + `;` for typedef-style defs
    while i < n and text[i] not in ";\n":
        i += 1
    if i < n and text[i] == ";":
        i += 1
    return m.start(), i


#  ---------------------------------------------------------------
#  Name-pattern relatives
#  ---------------------------------------------------------------

#  (needle, [replacements], short pattern label)
_NAME_SWAPS: tuple[tuple[str, tuple[str, ...], str], ...] = (
    # render layer
    ("_top",       ("_base", "_roof", "_mid", "_bottom"), "layer"),
    ("_base",      ("_top", "_roof", "_mid", "_bottom"), "layer"),
    ("_roof",      ("_top", "_base", "_mid"),             "layer"),
    ("_bottom",    ("_top", "_base"),                     "layer"),
    # has-sides
    ("with_sides", ("no_sides",),  "sides"),
    ("no_sides",   ("with_sides",), "sides"),
    # direction
    ("up_",        ("down_",),      "direction"),
    ("down_",      ("up_",),        "direction"),
    ("left_",      ("right_",),     "direction"),
    ("right_",     ("left_",),      "direction"),
    # vertical position
    ("mid_",       ("top_", "bottom_"), "position"),
    ("top_",       ("mid_", "bottom_"), "position"),
    ("bottom_",    ("top_", "mid_"),    "position"),
    # actions / verbs
    ("show_",      ("hide_", "draw_", "render_"), "action"),
    ("hide_",      ("show_",),                    "action"),
    ("draw_",      ("show_", "render_"),          "action"),
    ("render_",    ("show_", "draw_"),            "action"),
    ("start_",     ("stop_", "end_"),             "action"),
    ("stop_",      ("start_",),                   "action"),
    ("end_",       ("start_",),                   "action"),
    ("open_",      ("close_",),                   "action"),
    ("close_",     ("open_",),                    "action"),
    # init / cleanup
    ("init_",      ("shutdown_", "cleanup_"),     "lifecycle"),
    ("shutdown_",  ("init_", "cleanup_"),         "lifecycle"),
)


def _zoom_variants(name: str) -> list[tuple[str, str]]:
    """Yield (variant_name, pattern_label) for digit-suffix swaps.

    Caesar II uses `<verb>_<noun>` (no digit), `<verb>2_<noun>` and
    `<verb>3_<noun>` for zoom-level template instantiations.  We swap
    the leading verb's trailing digit (or the absence of one) across
    {none, 2, 3}.
    """
    out: list[tuple[str, str]] = []
    # Match a leading identifier optionally suffixed with a digit, then '_'.
    m = re.match(r"^([A-Za-z][A-Za-z]*?)(\d)?_", name)
    if not m:
        return out
    base, cur = m.group(1), m.group(2)
    rest = name[m.end() - 1 :]   # the '_<rest>'
    digits = ("", "2", "3")
    for d in digits:
        if d == (cur or ""):
            continue
        out.append((f"{base}{d}{rest}", f"zoom {cur or '-'}→{d or '-'}"))
    return out


def _candidate_relatives(name: str) -> list[tuple[str, str]]:
    """Generate (candidate_name, pattern_label) pairs."""
    out: list[tuple[str, str]] = []
    seen: set[str] = set()

    def _add(cand: str, label: str) -> None:
        if cand and cand != name and cand not in seen:
            seen.add(cand)
            out.append((cand, label))

    # zoom levels (leading verb digit)
    for cand, label in _zoom_variants(name):
        _add(cand, label)

    # known suffix / prefix segment swaps
    for needle, repls, label in _NAME_SWAPS:
        if needle not in name:
            continue
        for repl in repls:
            _add(name.replace(needle, repl, 1), label)

    return out


def _verify_cache() -> dict | None:
    """Read the in-process verify cache (None on miss/error).

    Wraps ``get_verify_json`` with stdout+stderr redirection: if the
    cache is stale, the helper triggers a full ``decomp-verify`` pass
    whose ``Loading PS.EXE …`` / per-function ``~ swap_2_figures …``
    chatter would otherwise leak into the agent CLI's progress
    stream, drowning the per-agent transitions.  The chatter is
    informational only; the cache document is what we need.
    """
    try:
        import contextlib, io
        from c2.commands.verify_json import get_verify_json
        with (contextlib.redirect_stdout(io.StringIO()),
              contextlib.redirect_stderr(io.StringIO())):
            return get_verify_json(rebuild=False)
    except Exception:
        return None


def _name_relatives(function_name: str, *, top: int = 12) -> list[NameRelative]:
    """Resolve name-pattern variants and look up their corpus status.

    Returns at most ``top`` rows, ordered: byte-exact relatives first
    (most useful PS-faithful templates), then diffing, then unknown.
    """
    cands = _candidate_relatives(function_name)
    if not cands:
        return []

    cache = _verify_cache()
    if cache is None:
        # Without the cache we can't tell status; return unknown rows
        # rather than nothing — the agent can still `fetch` them.
        return [
            NameRelative(name=c, pattern=p, status="unknown")
            for c, p in cands[:top]
        ]

    by_name = {f["name"]: f for f in cache.get("functions", [])}
    rows: list[NameRelative] = []
    for cand, pat in cands:
        f = by_name.get(cand)
        if f is None:
            continue   # function doesn't exist; skip silently
        diff = int(f.get("diff_byte_count", 0) or 0)
        status = "byte-exact" if diff == 0 else "diffing"
        rows.append(NameRelative(
            name=cand, pattern=pat, status=status,
            byte_diff=diff, source_file=f.get("file"),
        ))

    # Sort: byte-exact first (best templates), then by ascending diff
    rows.sort(key=lambda r: (0 if r.status == "byte-exact" else 1, r.byte_diff))
    return rows[:top]


def _siblings(project: ProjectConfig, function_name: str,
              top: int) -> list[SiblingInfo]:
    """Top-N structural siblings via shingle-containment matching.

    Uses the project's ``c2 sibling`` machinery (5-insn shingle hashes
    over the normalized asm) which is structurally more precise than
    embedding NN \u2014 family members (e.g. ``down_slider_var``,
    ``up_slider_var`` for ``mid_slider_var``) cluster top of the list.

    **Returns siblings of every byte status** (``exact`` / ``diff`` /
    ``written``).  Byte-exact siblings make the strongest templates,
    but diffing siblings often instantiate the same source family and
    Watcom codegen quirk -- their residue is informative even when
    their bytes aren't.  Each :class:`SiblingInfo` carries the sibling's
    verify status (``status`` / ``byte_diff`` / ``shape_summary``) so
    the agent can pick wisely.
    """
    try:
        from c2.commands.sibling import find_siblings
        hits = find_siblings(
            function_name,
            filter_status={"exact", "diff", "written"},
            top_n=top, min_score=0.05,
        )
    except Exception:
        return []

    # Build name -> shape_distance map from the in-process verify
    # cache (single lookup, reused across every diffing sibling).
    # ``_verify_cache`` is the same helper used by ``_name_relatives``;
    # it suppresses chatter via redirect_stdout/stderr.
    cache = _verify_cache() or {}
    shape_by_name: dict[str, dict] = {}
    for fn in cache.get("functions", []):
        sd = fn.get("shape_distance")
        if sd:
            shape_by_name[fn["name"]] = sd

    out: list[SiblingInfo] = []
    for h in hits:
        if h.status == "exact":
            out.append(SiblingInfo(
                name=h.name, score=float(h.score),
                status="byte_exact",
            ))
        elif h.status == "diff":
            sd = shape_by_name.get(h.name)
            shape_summary = _format_shape_summary(sd) if sd else None
            out.append(SiblingInfo(
                name=h.name, score=float(h.score),
                status="diffing",
                byte_diff=int(h.diff_byte_count or 0),
                shape_summary=shape_summary,
            ))
        else:  # 'written' (annotated but no verify status)
            out.append(SiblingInfo(
                name=h.name, score=float(h.score),
                status="annotated",
            ))
    return out


def _format_shape_summary(sd: dict) -> str | None:
    """Compact one-line layered shape distance for a sibling row.

    Surfaces the FIX-NEXT layer's N/T (the actionable signal) -- not
    the mixed-unit ``shape`` sum.  Examples:

    * ``"shape ir 2/14 -> fix-next ir"`` reads "2 of 14 IR lines
      diverge; this is the layer to fix first".
    * ``"shape-exact (regalloc residue)"`` means the C source matches
      PS in every layer -- the remaining byte diff is a pure regalloc
      tie-break, so this sibling's source IS the PS-faithful template
      even though its bytes aren't.
    """
    fix_next = sd.get("fix_next")
    if not fix_next or fix_next == "none":
        return None
    if fix_next == "regalloc":
        return "shape-exact (regalloc residue)"
    n = sd.get(fix_next)
    t = sd.get(f"{fix_next}_total")
    if n is None or t is None:
        return None
    return f"shape {fix_next} {n}/{t} -> fix-next {fix_next}"
