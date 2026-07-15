"""Tests for c2.commands.local_hints — the REAL-vs-INLINE locals oracle."""

from __future__ import annotations

import pytest

from c2.commands.local_hints import (
    _fam,
    _key_for,
    _key_regs,
    _key_symbol,
    _mem_operand,
    _split_ops,
    analyze,
)


def test_reg_families():
    assert _fam("dl") == "edx"
    assert _fam("bh") == "ebx"
    assert _fam("esi") == "esi"
    assert _fam("0x14") is None


def test_mem_operand_parsing():
    assert _mem_operand("byte ptr [eax + 0x8095e]") == "eax + 0x8095e"
    assert _mem_operand("eax") is None
    assert _split_ops("eax, dword ptr [ebx + 8]") == [
        "eax", "dword ptr [ebx + 8]"]


def test_key_symbol_and_regs():
    assert _key_symbol("@army_list+0x25") == "army_list"
    assert _key_symbol("@lson|eax") == "lson"
    assert _key_symbol("ebx+8") is None
    assert _key_regs("@lson|eax") == {"eax"}
    assert _key_regs("ebx+8") == {"ebx"}
    assert _key_regs("@mouse_x") == set()


class _FakeLn:
    def __init__(self, data_ref):
        self.data_ref = data_ref


def test_key_for_stack_is_none():
    assert _key_for(_FakeLn(None), "esp + 0x18") is None
    assert _key_for(_FakeLn(None), "ebp + 8") is None


def test_key_for_indexed_includes_regs():
    assert _key_for(_FakeLn("lson"), "eax*2 + 0x87e00") == "@lson|eax"
    assert _key_for(_FakeLn("mouse_x"), "0x34e94") == "@mouse_x"


# ── End-to-end on known-good functions (need the PS.EXE project data) ──────

@pytest.fixture(scope="module")
def slider_sites():
    try:
        return analyze("slider_control")
    except Exception as e:                      # pragma: no cover
        pytest.skip(f"PS.EXE project data unavailable: {e}")


def test_slider_control_real_locals(slider_sites):
    """Three of the four knob-computation locals are REAL (validated session
    lever).  The fourth (maxp, ebx+0x11) abstains: its first use is in the
    immediately-following run, which is byte-identical to a wrapped
    expression — the designed honest abstention."""
    real_keys = {s.key for s in slider_sites if s.verdict == "REAL"}
    assert {"ebx+8", "ebx+9", "ebx+0xf"} <= real_keys
    maxp = [s for s in slider_sites if s.key == "ebx+0x11"]
    assert maxp and maxp[0].verdict is None


def test_slider_control_inline_reads(slider_sites):
    """sliders->x and mouse_x re-reads are INLINE (de-invented x local)."""
    inline_keys = {s.key for s in slider_sites if s.verdict == "INLINE"}
    assert "@mouse_x" in inline_keys
    assert "ebx" in inline_keys


def test_slider_control_no_real_x(slider_sites):
    """sliders->x (key 'ebx') must NOT be classified REAL — naming it was
    the 156-byte mistake this tool exists to prevent."""
    for s in slider_sites:
        if s.key == "ebx":
            assert s.verdict != "REAL"


# ── Gate-5 (signal-A run-scoping) + per-symbol-validation regression ────────

def test_consumed_in_run_inline_vs_real():
    """`_consumed_in_run` abstains a value transformed within its own -d1 run
    (`x = g & 7`) but keeps one that survives the run (`x = g;`)."""
    from c2.commands.local_hints import _decode, _consumed_in_run

    class _Ln:
        def __init__(self, line, mnem, ops, data_ref=None):
            self.line = line
            self.address = 0
            self.mnemonic = mnem
            self.op_str = ", ".join(ops)
            self.data_ref = data_ref

    # run 1: `x = g` (load only, survives), run 2: a transform on a DIFFERENT
    # value, plus a same-run masked load `y = h & 7`.
    lines = [
        _Ln(10, "mov", ["edx", "dword ptr [0x9000]"], "g"),   # idx0  load g
        _Ln(11, "mov", ["esi", "dword ptr [0x9004]"], "h"),   # idx1  load h
        _Ln(0, "and", ["esi", "7"]),                           # idx2  mask h (same run)
    ]
    insns = _decode(lines)
    # g (idx0) survives its run -> NOT consumed -> REAL-eligible
    assert _consumed_in_run(insns, 0, "edx") is False
    # h (idx1) is masked in its own run -> consumed -> INLINE
    assert _consumed_in_run(insns, 1, "esi") is True


def test_consumed_in_run_index_use():
    """A value used as a [mem] INDEX within its run is consumed (INLINE)."""
    from c2.commands.local_hints import _decode, _consumed_in_run

    class _Ln:
        def __init__(self, line, mnem, ops, data_ref=None):
            self.line = line
            self.address = 0
            self.mnemonic = mnem
            self.op_str = ", ".join(ops)
            self.data_ref = data_ref

    lines = [
        _Ln(20, "mov", ["eax", "dword ptr [0x9000]"], "idx"),       # load idx
        _Ln(0, "mov", ["ecx", "dword ptr [eax*4 + 0x9100]"], "t"),  # use as index (same run)
    ]
    insns = _decode(lines)
    assert _consumed_in_run(insns, 0, "eax") is True


def test_ast_symbol_labels_per_symbol():
    """Per-symbol GT: a global as the complete scalar rvalue is REAL; the
    same kind of global as an operand / index / call-arg is INLINE."""
    from pycparser import CParser
    from c2.commands.local_hints import _ast_symbol_labels

    code = (
        "int ga; int gb; int gc[4]; int gi; int f(void){\n"
        "  int x; int y; int z;\n"
        "  x = ga;\n"            # REAL: ga is the whole rvalue
        "  y = gb + 1;\n"        # INLINE: gb is an operand
        "  z = gc[gi];\n"        # REAL: gc[..]; INLINE: gi (index)
        "  return 0;\n"
        "}\n"
    )
    ast = CParser().parse(code, "t.c")
    fdef = ast.ext[-1]
    labels = _ast_symbol_labels("f", "t.c", fdef)
    by_sym = {sym: lab for (_ln, sym), lab in labels.items()}
    assert by_sym.get("ga") == "REAL"
    assert by_sym.get("gb") == "INLINE"
    assert by_sym.get("gc") == "REAL"
    assert by_sym.get("gi") == "INLINE"


def test_corpus_precision_regression():
    """Per-symbol corpus validation must hold: INLINE (the de-invent
    workhorse) >= 97%; REAL (asm-ambiguous, gate-5-gated) >= 65%.  Skips when
    the byte-exact line-map sidecar / project data is unavailable."""
    import contextlib
    import io
    import json as _json
    from c2.commands.local_hints import validate, SIDECAR_PATH

    if not SIDECAR_PATH.exists():
        pytest.skip("no .c2-cache/exact-line-map.json sidecar")
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            validate(json_out=True)
    except SystemExit:
        pytest.skip("validation prerequisites unavailable")
    lines = [l for l in buf.getvalue().splitlines() if l.strip()]
    if not lines:
        pytest.skip("validation produced no output")
    st = _json.loads(lines[-1])["stats"]

    def prec(k):
        tp, fp = st[k]["tp"], st[k]["fp"]
        return tp / (tp + fp) if (tp + fp) else 1.0

    assert st["INLINE"]["tp"] >= 500, st
    assert prec("INLINE") >= 0.97, ("INLINE", st["INLINE"])
    assert prec("REAL") >= 0.80, ("REAL", st["REAL"])


def test_disagreement_cross_check_no_fp_on_byte_exact():
    """The de-invent / add-local cross-check has a clean ground truth on the
    byte-exact corpus: the recovered source IS PS-faithful, so it should
    recommend NEITHER de-invent NOR add-local.  Every firing is a false
    positive by construction.  The sv-exclusive + 'b' guards drove this from
    12 -> 1 (the lone remainder is the new_province/c2inf struct-field
    reload-across-call case the AST can't field-disambiguate); assert it does
    not regress.  Skips when project data is unavailable."""
    try:
        from c2.commands.verify_json import get_verify_json
        from c2.commands import local_hints as m
        doc = get_verify_json(no_build=True)
    except Exception:
        pytest.skip("no verify.json / project data")
    exact = [f["name"] for f in doc.get("functions", [])
             if f.get("diff_byte_count", 0) == 0 and not f.get("size_differs")]
    if len(exact) < 200:
        pytest.skip("byte-exact corpus too small / uncached")
    fps = []
    for fn in exact:
        try:
            d = m._disagreements(fn)
        except Exception:
            continue
        if d and (d["deinvent"] or d["addlocal"]):
            fps.append((fn, d["deinvent"], d["addlocal"]))
    # baseline before the guards was 12; allow a tiny residue (struct-field
    # collapse) but fail loudly if a guard is weakened.
    assert len(fps) <= 2, f"cross-check FP regression: {fps}"


def test_statement_locals_precision_on_byte_exact():
    """The register-rooted statement-local detector (the advisory signal that
    sees `t=a+b` / `x=f()` / `p=q` locals the load signals can't) must hold
    >=80% precision vs the byte-exact corpus: a flagged statement run should
    land on a source line that assigns a local.  Skips without project data."""
    try:
        import json as _json
        from c2.commands.verify_json import get_verify_json
        from c2.commands.local_hints import (
            statement_locals, _source_index, SIDECAR_PATH)
        from c2.commands.disasm import disasm_function
        import pycparser.c_ast as cc
    except Exception:
        pytest.skip("deps unavailable")
    if not SIDECAR_PATH.exists():
        pytest.skip("no exact-line-map sidecar")
    sidecar = _json.loads(SIDECAR_PATH.read_text())
    index = _source_index()
    doc = get_verify_json(no_build=True)
    exact = [f["name"] for f in doc.get("functions", [])
             if f.get("diff_byte_count", 0) == 0 and not f.get("size_differs")]
    if len(exact) < 200:
        pytest.skip("byte-exact corpus too small / uncached")

    def assign_lines(node):
        loc = set()
        # parameters are locals too (modified params: `x -= flag`, `base += off`)
        try:
            for p in (node.decl.type.args.params if node.decl.type.args else []):
                if getattr(p, "name", None):
                    loc.add(p.name)
        except AttributeError:
            pass
        class DV(cc.NodeVisitor):
            def visit_Decl(self, d):
                if d.name and not isinstance(d.type, cc.FuncDecl):
                    loc.add(d.name)
                self.generic_visit(d)
        DV().visit(node.body)
        lines = set()
        class AV(cc.NodeVisitor):
            def visit_Decl(self, d):
                if d.name in loc and d.init is not None and d.coord:
                    lines.add(d.coord.line)
                self.generic_visit(d)
            def visit_Assignment(self, a):
                if isinstance(a.lvalue, cc.ID) and a.lvalue.name in loc and a.coord:
                    lines.add(a.coord.line)
                self.generic_visit(a)
            def visit_UnaryOp(self, u):
                if (u.op in ("p++", "p--", "++", "--")
                        and isinstance(u.expr, cc.ID) and u.expr.name in loc
                        and u.coord):
                    lines.add(u.coord.line)
                self.generic_visit(u)
        AV().visit(node.body)
        return lines

    tp = fp = 0
    for fn in exact:
        if fn not in index or fn not in sidecar:
            continue
        _p, node, _ = index[fn]
        try:
            al = assign_lines(node)
            rows = statement_locals(fn)
        except Exception:
            continue
        starts = {int(k): v for k, v in sidecar[fn]["starts"].items()}
        if not starts:
            continue
        offs = sorted(starts)

        def our_line(off):
            lo = None
            for o in offs:
                if o <= off:
                    lo = o
                else:
                    break
            return starts.get(lo) if lo is not None else None
        for r in rows:
            ln = our_line(r["off"])
            if ln is None:
                continue
            if ln in al:
                tp += 1
            else:
                fp += 1
    prec = tp / (tp + fp) if (tp + fp) else 1.0
    assert tp + fp >= 200, f"too few predictions ({tp + fp})"
    # measured ~92% (GT includes params + the ret-value exclusion); guard 88%.
    assert prec >= 0.88, f"statement-local precision regressed: {prec:.2f} ({tp}/{tp + fp})"
