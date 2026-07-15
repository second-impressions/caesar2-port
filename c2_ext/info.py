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

from c2_ext.project import ProjectConfig


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
    name: str
    score: float


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
    tail_merge_donor: str | None
    fallthrough_callee: str | None

    def to_dict(self) -> dict:
        d = asdict(self)
        d["source_line_range"] = list(self.source_line_range) if self.source_line_range else None
        d["prologue_pushes"] = list(self.prologue_pushes)
        d["calls"] = [asdict(c) for c in self.calls]
        d["types"] = [asdict(t) for t in self.types]
        d["siblings"] = [asdict(s) for s in self.siblings]
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

    if fi.siblings:
        lines.append("## Byte-exact siblings (5-insn shingle containment)")
        lines.append(
            "Score = fraction of this function's asm shingles that also appear "
            "in the sibling's body.  High score = structural twin (same shape, "
            "likely same source family).  Use `fetch(<name>)` for the C source, "
            "`disasm(<name>)` for the target asm."
        )
        lines.append("")
        for s in fi.siblings:
            lines.append(f"- `{s.name}`  (score: {s.score:.3f})")

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


def _siblings(project: ProjectConfig, function_name: str,
              top: int) -> list[SiblingInfo]:
    """Top-N byte-exact siblings via shingle-containment matching.

    Uses the project's ``c2 sibling`` machinery (5-insn shingle hashes
    over the normalized asm) which is structurally more precise than
    embedding NN \u2014 family members (e.g. ``down_slider_var``,
    ``up_slider_var`` for ``mid_slider_var``) cluster top of the list.
    """
    try:
        from c2.commands.sibling import find_siblings
        hits = find_siblings(
            function_name, filter_status={"exact"},
            top_n=top, min_score=0.05,
        )
    except Exception:
        return []
    return [SiblingInfo(name=h.name, score=float(h.score)) for h in hits]
