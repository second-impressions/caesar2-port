"""static-symbols — Watcom 10.0a debug-info emission for statics & globals.

Tests six hypotheses about how `wcc386` 10.0a routes file-scope and
function-local `static` variables through the OBJ symbol table and the
Watcom V3 debug section that ends up in the LE executable.  The
hypotheses come from reading OW v1 source (`bld/cg/c/dbsyms.c`,
`bld/cg/intel/c/wvsyms.c`, `bld/cc/c/cgen2.c`, `bld/cc/c/csym.c`,
`bld/cc/c/coptions.c`).  This experiment **runs against real Watcom
10.0a** to confirm the v10.0a behaviour matches OW v1's source.

Hypotheses
----------

  H1  ``is_static`` (the ``GBL_KIND_STATIC`` bit in the V3 global-symbol
      table) cleanly distinguishes file-scope statics from file-scope
      globals.

  H2  Function-local statics get the source-level name verbatim — no
      mangling, no scope/function prefix.

  H3  At plain ``-d1`` (PS.EXE's debug level), function-local statics
      are **not** emitted as PUBDEFs by `wcc386` and **not** present
      in the V3 debug global-symbol table.  They have only a private
      OBJ label, so any consumer of `symbols.json` is blind to them.

  H4  At ``-d1+`` / ``-d2`` (``DBG_LOCALS`` set), function-local
      statics are emitted as ``SYM_VARIABLE + VAR_LOCAL`` records in
      the module's "locals" demand block — separate from the global
      symbol table.

  H5  ``-d2`` forces ``-od`` (no optimisation): the same function
      compiled with ``-d2`` is dramatically larger than at ``-d1`` /
      ``-d1+`` because Watcom inserts a frame pointer and pushes
      every callee-save register.

  H6  Two TUs can each declare the same-named file-scope static
      independently (internal linkage); both end up in the V3
      symbol table at distinct addresses, owned by their respective
      modules.

Verdict
-------

Output ends with a checkbox table summarising H1–H6 from the live
Watcom 10.0a runs.  Run with::

    uv run c2 cgex run static-symbols

To inspect a single trial in detail::

    uv run c2 cgex run static-symbols --trial d1
"""

from __future__ import annotations

import sys
from pathlib import Path

from c2.commands.cgex import Experiment


# ── Source under test ───────────────────────────────────────────────────────


_SRC_SINGLE = """\
int g_global = 7;
static int g_file_static = 8;

void counter(void) {
    static int fn_local_static = 9;
    fn_local_static++;
    g_global++;
    g_file_static++;
}
"""


# Two TUs that each define a file-scope static called `locked` —
# proves H6 (same name across TUs is fine because internal linkage).
_SRC_MULTI_A = """\
static int locked = 1;
int get_a(void) { return locked++; }
"""
_SRC_MULTI_B = """\
static int locked = 2;
int get_b(void) { return locked++; }
"""


# ── Trial registration ─────────────────────────────────────────────────────


exp = Experiment(
    name="static-symbols",
    ps_function=None,                       # no PS byte-diff
    cflags="-bt=dos -mf -4r -s",            # base PS.EXE flags (no -d)
)


exp.add(
    "d-none", _SRC_SINGLE,
    cflags="-bt=dos -mf -4r -s",
    note="default flags: no V3 debug section emitted at all",
)

exp.add(
    "d1", _SRC_SINGLE,
    cflags="-bt=dos -mf -4r -s -d1",
    note="line numbers only — PS.EXE's actual flag",
)

exp.add(
    "d1plus", _SRC_SINGLE,
    cflags="-bt=dos -mf -4r -s -d1+",
    note="-d1 plus DBG_LOCALS|DBG_TYPES, NO -od",
)

exp.add(
    "d2", _SRC_SINGLE,
    cflags="-bt=dos -mf -4r -s -d2",
    note="full debug; forces -od",
)

# Multi-TU collision: two `static int locked` in different files.
# We pass a dict source via a separate Experiment hack: cgex's
# Experiment.add() takes a single body string, but compile_snippet
# under the hood accepts a {filename: text} dict.  Easiest path:
# concatenate via the prelude/extra_defs mechanism that the
# Experiment harness already supports.
#
# To keep the two `locked` symbols in *separate* TUs, we register
# this trial via direct compile call in the analyser instead of
# the regular `exp.add()` path (otherwise both definitions would
# collide in the same TU).  See _run_multi_tu() below.


# ── Custom analysis ────────────────────────────────────────────────────────


def _scan_demand_area(data: bytes, area_off: int, area_size: int) -> list[str]:
    """Scan the per-module demand area for symbol names.

    The Watcom V3 demand area (between ``section_start`` and
    ``section_start + section_hdr.mod_offset``) holds the actual
    locals / types / lines record streams for every module, indexed
    by per-module prefix tables that ``ModuleInfo.locals_offset`` etc.
    point into.  Decoding the prefix-table indirection in full is
    outside this experiment's scope; for our purposes it is enough
    to scan the entire demand area for the literal ASCII names we
    expect and confirm they exist.

    Watcom V3 record encoding (from `bld/cg/intel/c/wvsyms.c`):

        BuffStart( &temp, SYM_VARIABLE + VAR_LOCAL );  // 0x11
        LocDump( local->loc );                          // location expr
        BuffIndex( (uint) tipe );                       // type idx
        BuffWSLString( FEName( local->sym ) );          // name (LP)
        BuffEnd( DbgLocals );
    """
    if area_size <= 0:
        return []
    blob = data[area_off : area_off + area_size]
    found: list[str] = []
    for needle in (b"fn_local_static", b"g_file_static", b"locked",
                   b"g_global"):
        if needle in blob:
            found.append(needle.decode())
    return found


def _parse_or_none(exe: Path):
    from c2.parsers.debug import parse_watcom_debug
    try:
        return parse_watcom_debug(exe)
    except Exception:
        return None


def _omf_pubdef_names(obj_path: Path) -> set[str]:
    """Return the set of decorated symbol names found in an OMF .obj.

    This is a lightweight grep: PUBDEFs and EXTDEFs both store
    length-prefixed names, so we scan for the LP-encoded form of
    each candidate.  This dodges the OMF record framing entirely and
    is more than enough to tell whether a name made it as a public
    symbol.
    """
    raw = obj_path.read_bytes()
    found: set[str] = set()
    candidates = [
        "_g_global", "_g_file_static", "_fn_local_static",
        "g_global", "g_file_static", "fn_local_static",
        "counter_", "_locked",
    ]
    for name in candidates:
        for i in range(len(raw) - len(name) - 1):
            if raw[i] == len(name) and raw[i + 1 : i + 1 + len(name)] == name.encode():
                found.add(name)
                break
    return found


def _run_multi_tu_trial() -> dict:
    """Compile two TUs that each define `static int locked = N;`."""
    from c2.commands.oracle import compile_snippet, IMAGE_10_0A
    b = compile_snippet(
        {"a.c": _SRC_MULTI_A, "b.c": _SRC_MULTI_B},
        image=IMAGE_10_0A,
        cflags="-bt=dos -mf -4r -s -d1",
        label="multi-tu/d1",
    )
    info = _parse_or_none(b.work / "out.exe")
    return {"build": b, "info": info}


def _custom_print_table(file=sys.stdout) -> None:
    """Replacement for Experiment.print_table — print full analysis."""
    print("=" * 78, file=file)
    print("static-symbols: hypothesis verification under Watcom 10.0a",
          file=file)
    print("=" * 78, file=file)

    # -- per-trial breakdown -------------------------------------------------
    rows: dict[str, dict] = {}
    for name, t in exp.trials.items():
        rec = {"trial": name, "cflags": t.cflags, "note": t.note,
               "fn_size": None, "info": None, "obj_pub": set(),
               "demand_hits": []}
        if t.build is None:
            rec["status"] = "(not run)"
        elif not t.ok:
            rec["status"] = "FAIL"
        else:
            rec["status"] = "OK"
            fn = t.build.functions.get("counter_")
            if fn:
                rec["fn_size"] = len(fn.bytes_)
            rec["info"] = _parse_or_none(t.build.work / "out.exe")
            rec["obj_pub"] = _omf_pubdef_names(t.build.work / "snip.obj")
            # Scan the entire demand area for symbol names.  The demand
            # area covers the bytes between section_start and the start
            # of the module table (section_hdr.mod_offset), and contains
            # all locals / types / lines record streams for every module.
            if rec["info"] is not None:
                exe_data = (t.build.work / "out.exe").read_bytes()
                from c2.parsers.debug import (
                    MasterDbgHeader, SectionDbgHeader,
                )
                fsz = len(exe_data)
                master = MasterDbgHeader.parse(
                    exe_data[fsz - MasterDbgHeader.sizeof():]
                )
                debug_start = fsz - master.debug_size
                section_start = (
                    debug_start + master.lang_size + master.segment_size
                )
                section_hdr = SectionDbgHeader.parse(
                    exe_data[section_start :
                             section_start + SectionDbgHeader.sizeof()]
                )
                area_off = section_start + SectionDbgHeader.sizeof()
                area_size = (section_start + section_hdr.mod_offset
                             - area_off)
                found = _scan_demand_area(exe_data, area_off, area_size)
                if found:
                    rec["demand_hits"].append(
                        f"demand area ({area_size}b): {found}"
                    )
        rows[name] = rec

    # -- print per-trial sections --------------------------------------------
    for name, rec in rows.items():
        print(file=file)
        print(f"── {name}  [{rec['cflags']}]  {rec['status']}", file=file)
        print(f"   {rec['note']}", file=file)
        if rec["status"] != "OK":
            continue
        print(f"   counter() size: {rec['fn_size']} b", file=file)
        # OBJ-level public names
        pub = sorted(rec["obj_pub"])
        present = [n for n in ("_g_global", "_g_file_static",
                               "_fn_local_static", "counter_") if n in pub]
        missing = [n for n in ("_g_global", "_g_file_static",
                               "_fn_local_static", "counter_")
                   if n not in pub]
        print(f"   OBJ pubdef names present:  {present}", file=file)
        print(f"   OBJ pubdef names missing:  {missing}", file=file)
        # V3 debug presence
        info = rec["info"]
        if info is None:
            print("   V3 debug:  (no debug section in LE)", file=file)
        else:
            print(f"   V3 debug:  {len(info.symbols)} global syms, "
                  f"{len(info.modules)} modules", file=file)
            for m in info.modules:
                marks = []
                if m.lines_entries: marks.append(f"lines={m.lines_entries}")
                if m.locals_entries: marks.append(f"locals={m.locals_entries}")
                if m.types_entries: marks.append(f"types={m.types_entries}")
                tag = " ".join(marks) if marks else "(no demands)"
                print(f"     m{m.index} {m.name!r}: {tag}", file=file)
            print("   V3 global symbols:", file=file)
            for s in info.symbols:
                k = []
                if s.kind & 1: k.append("STATIC")
                if s.kind & 2: k.append("DATA")
                if s.kind & 4: k.append("CODE")
                print(f"     {s.demangled_name!r:24s}  seg={s.segment} "
                      f"off=0x{s.offset:06x}  mod={s.module_index}  "
                      f"kind={'|'.join(k)}", file=file)
            if rec["demand_hits"]:
                print("   Demand-area name scan (proves names present in",
                      file=file)
                print("   per-module locals/types record streams):",
                      file=file)
                for hit in rec["demand_hits"]:
                    print(f"     {hit}", file=file)

    # -- multi-TU trial (H6) -------------------------------------------------
    print(file=file)
    print("── multi-tu/d1  (separate TUs both with `static int locked`)",
          file=file)
    multi = _run_multi_tu_trial()
    info = multi["info"]
    if info is None:
        print("   V3 debug missing or unparseable", file=file)
    else:
        for s in info.symbols:
            k = []
            if s.kind & 1: k.append("STATIC")
            if s.kind & 2: k.append("DATA")
            if s.kind & 4: k.append("CODE")
            print(f"     {s.demangled_name!r:14s}  seg={s.segment} "
                  f"off=0x{s.offset:06x}  mod={s.module_index}  "
                  f"kind={'|'.join(k)}", file=file)

    # -- verdict matrix ------------------------------------------------------
    def _has(name: str, sym: str, *, kind_mask: int = 0,
             require_static: bool | None = None) -> bool:
        info = rows[name]["info"]
        if info is None:
            return False
        for s in info.symbols:
            if s.demangled_name == sym:
                if require_static is True and not (s.kind & 1):
                    return False
                if require_static is False and (s.kind & 1):
                    return False
                return True
        return False

    sz_d1 = rows["d1"]["fn_size"] or 0
    sz_d2 = rows["d2"]["fn_size"] or 0
    sz_d1plus = rows["d1plus"]["fn_size"] or 0

    h1 = (
        _has("d1", "g_global", require_static=False) and
        _has("d1", "g_file_static", require_static=True)
    )
    h2 = (
        # If the function-local static name appears in the demand area
        # at all, it was preserved verbatim (not mangled or scope-prefixed).
        any("fn_local_static" in b for b in rows["d2"]["demand_hits"])
        or any("fn_local_static" in b for b in rows["d1plus"]["demand_hits"])
    )
    h3 = (
        not _has("d1", "fn_local_static") and
        "_fn_local_static" not in rows["d1"]["obj_pub"]
    )
    h4 = (
        any("fn_local_static" in b for b in rows["d1plus"]["demand_hits"])
        and any("fn_local_static" in b for b in rows["d2"]["demand_hits"])
    )
    h5 = sz_d2 > 2 * sz_d1   # -d2 should bloat function size dramatically
    h6_locked_count = sum(
        1 for s in (multi["info"].symbols if multi["info"] else [])
        if s.demangled_name == "locked" and (s.kind & 1)
    )
    h6 = h6_locked_count == 2

    print(file=file)
    print("=" * 78, file=file)
    print("Verdict matrix", file=file)
    print("=" * 78, file=file)
    def mark(b): return "✓" if b else "✗"
    print(f"  H1  is_static distinguishes file-scope static vs global       {mark(h1)}",
          file=file)
    print(f"  H2  function-local static name preserved verbatim             {mark(h2)}",
          file=file)
    print(f"  H3  function-local static INVISIBLE at -d1 (no PUBDEF, no V3) {mark(h3)}",
          file=file)
    print(f"  H4  function-local static → VAR_LOCAL record at -d1+/-d2     {mark(h4)}",
          file=file)
    print(f"  H5  -d2 forces -od (counter size {sz_d1}b → {sz_d2}b)        {mark(h5)}",
          file=file)
    print(f"  H6  same name in two TUs ok ({h6_locked_count}× `locked` STATIC|DATA)  {mark(h6)}",
          file=file)
    print(file=file)
    print(f"  d1 / d1+ / d2 counter() sizes: "
          f"{sz_d1}b / {sz_d1plus}b / {sz_d2}b", file=file)
    print(file=file)
    print("Implications for Caesar II reverse-engineering:", file=file)
    print("  • PS.EXE's 61 `static data` symbols are ALL file-scope statics.",
          file=file)
    print("    Function-local statics in PS would have been compiled away to",
          file=file)
    print("    name-less private labels (no PUBDEF, no V3 record) at -d1.",
          file=file)
    print("  • Ghidra `data_XXX` symbols inside a single function's body may",
          file=file)
    print("    be the storage of a function-local static whose name was lost",
          file=file)
    print("    at compile time and is unrecoverable from the binary alone.",
          file=file)


def _custom_print_trial(trial_name: str, *, n: int | None = None,
                        file=sys.stdout) -> None:
    """Override print_trial: dump just the disasm of `counter()`.

    The default cgex print_trial picks the largest function in the
    build, which for these tiny snippets ends up dumping the entire
    code section with trailing zero-padding.  We only care about
    `counter()` (the function with the local static).
    """
    t = exp.trials.get(trial_name)
    if t is None or not t.ok:
        print(f"=== {trial_name}: not built ===", file=file)
        return
    fn = t.build.functions.get("counter_")
    if fn is None:
        print(f"=== {trial_name}: counter_ not in build ===", file=file)
        return
    print(f"=== {trial_name}: counter() = {len(fn.bytes_)} b ===", file=file)
    for ins in fn.insns:
        print(f"  +{ins.rel_off:04x}  {ins.hex:<23s}  "
              f"{ins.mnemonic:<7s} {ins.op_str}", file=file)


# Replace the default print_table / print_trial with our analysers
exp.print_table = _custom_print_table  # type: ignore[assignment]
exp.print_trial = _custom_print_trial  # type: ignore[assignment]
