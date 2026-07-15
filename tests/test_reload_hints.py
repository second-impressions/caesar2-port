"""Tests for the reload-vs-hold named-intermediate marker (Rule 116) wired into
`decomp-verify`.  See ``c2/commands/reload_hints.py`` and the self-asserting
proof ``docs/codegen-experiments/reload-vs-hold.py``."""
import pytest
from pycparser import c_ast

import c2.commands.reload_hints as rh
from c2.commands.c_source import parse_c


def _i(asm):
    """A PS-stream instruction tuple (addr, size, raw, asm)."""
    return (0, 1, b"", asm)


def _funcdef(src):
    ast = parse_c(src, "<test>")
    for node in ast.ext:
        if isinstance(node, c_ast.FuncDef):
            return node
    raise AssertionError("no funcdef")


# ── _ps_global_reloads ───────────────────────────────────────────────────────
def test_ps_global_reloads_counts_source_reads():
    insns = [_i("mov eax, [0x72aa4]"),
             _i("imul eax, [0x72b90]"),
             _i("mov eax, [0x72aa4]")]
    assert rh._ps_global_loads(0x72aa4, insns) == 2


def test_ps_global_reloads_ignores_writes():
    # `[addr]` as destination is a write, not a reload.
    insns = [_i("mov eax, [0x72aa4]"),
             _i("mov [0x72aa4], edx"),
             _i("inc [0x72aa4]")]
    # only the first is a source read
    assert rh._ps_global_loads(0x72aa4, insns) == 1


# ── source candidate extraction ──────────────────────────────────────────────
def test_global_init_temp_used_twice_is_a_candidate():
    fd = _funcdef("void f(void){ int t = some_global; use(t); use2(t); }")
    v = rh._Temps(set())
    v.visit(fd.body)
    assert "t" in v.temps
    assert v.temps["t"].kind == "global"
    assert v.temps["t"].gname == "some_global"
    # the decl name emits no ID visit, so reads counts the 2 genuine uses
    assert v.uses["t"] == 2


def test_element_init_temp_is_NOT_a_candidate():
    # Element/field caches have no single confirmable home address; that family
    # is Rule 63/73/74 (c2 row-caches), not the PS-confirmed global reload rule.
    fd = _funcdef("void f(int i){ int t = rows[i].hp; use(t); use2(t); }")
    v = rh._Temps(set())
    v.visit(fd.body)
    assert "t" not in v.temps


def test_arithmetic_init_is_not_a_candidate():
    # No memory home -> byte-neutral -> never flagged.
    fd = _funcdef("void f(int a, int b){ int t = a * 7 + b; use(t); use2(t); }")
    v = rh._Temps(set())
    v.visit(fd.body)
    assert "t" not in v.temps


def test_pointer_cache_is_not_a_candidate():
    # `p = &rows[i]` is Rule 63/73 row-cache territory, not a scalar reload temp.
    fd = _funcdef("void f(int i){ row *p = &rows[i]; use(p->hp); }")
    v = rh._Temps(set())
    v.visit(fd.body)
    assert "p" not in v.temps


# ── detect_reload_hints gating ───────────────────────────────────────────────
@pytest.fixture
def patched(monkeypatch):
    """Inject a synthetic source function + global address table."""
    def _install(src, gaddrs):
        fd = _funcdef(src)
        name = fd.decl.name
        monkeypatch.setattr(rh, "_func_map", lambda: {name: fd})
        monkeypatch.setattr(rh, "_global_addrs", lambda: gaddrs)
        return name
    return _install


def test_fires_when_ps_reloads_global(patched):
    name = patched("void running(void){ int t = g; use(t); use2(t); }",
                   {"g": 0x72aa4})
    ps = [_i("mov eax, [0x72aa4]"), _i("call 0x10"), _i("mov eax, [0x72aa4]")]
    hints = rh.detect_reload_hints(name, ps, has_body_diff=True)
    assert len(hints) == 1
    h = hints[0]
    assert h.local == "t" and h.source == "g" and h.kind == "global"
    assert h.ps_loads == 2 and h.confidence == "high"
    assert "delete the local" in rh.render(hints).lower()


def test_suppressed_when_ps_holds_global(patched):
    # PS loads g only once (it ALSO holds it) -> our temp is faithful, no flag.
    name = patched("void running(void){ int t = g; use(t); use2(t); }",
                   {"g": 0x72aa4})
    ps = [_i("mov eax, [0x72aa4]"), _i("mov edx, eax"), _i("add edx, eax")]
    assert rh.detect_reload_hints(name, ps, has_body_diff=True) == []


def test_suppressed_when_sibling_local_holds_same_global(patched):
    # `icon = g` (assignment) + `int after = g` (decl) are TWO holds of g; PS
    # loading g twice gives each its own register (hold), it is NOT a reload
    # of one value.  Regression for perform_region_strip_action.
    name = patched(
        "void f(void){ int icon; icon = g; use(icon);"
        " { int after = g; use(after); use2(after); } }", {"g": 0x72aa4})
    ps = [_i("mov edx, [0x72aa4]"), _i("call 0x10"), _i("mov edi, [0x72aa4]")]
    # 2 loads, 2 sibling holds (icon assignment + after decl) -> suppressed.
    assert rh.detect_reload_hints(name, ps, has_body_diff=True) == []
    # but 3 loads with 2 holds (a genuine reload of one of them) -> fires.
    ps3 = ps + [_i("mov ecx, [0x72aa4]")]
    assert len(rh.detect_reload_hints(name, ps3, has_body_diff=True)) == 1


def test_suppressed_when_not_diffing(patched):
    name = patched("void running(void){ int t = g; use(t); use2(t); }",
                   {"g": 0x72aa4})
    ps = [_i("mov eax, [0x72aa4]"), _i("call 0x10"), _i("mov eax, [0x72aa4]")]
    assert rh.detect_reload_hints(name, ps, has_body_diff=False) == []


def test_suppressed_when_single_use(patched):
    # used once -> byte-neutral -> not a candidate even if PS reloads elsewhere.
    name = patched("void running(void){ int t = g; use(t); }", {"g": 0x72aa4})
    ps = [_i("mov eax, [0x72aa4]"), _i("call 0x10"), _i("mov eax, [0x72aa4]")]
    assert rh.detect_reload_hints(name, ps, has_body_diff=True) == []


def test_element_temp_is_not_flagged(patched):
    # Element/field caches are not flagged (no confirmable home; Rule 63/73/74).
    name = patched("void f(int i){ int t = rows[i].hp; use(t); use2(t); }", {})
    assert rh.detect_reload_hints(name, [], has_body_diff=True) == []


def test_to_json_roundtrip(patched):
    name = patched("void running(void){ int t = g; use(t); use2(t); }",
                   {"g": 0x72aa4})
    ps = [_i("mov eax, [0x72aa4]"), _i("call 0x10"), _i("mov eax, [0x72aa4]")]
    hints = rh.detect_reload_hints(name, ps, has_body_diff=True)
    js = rh.to_json(hints)
    assert js == [{"local": "t", "source": "g", "kind": "global",
                   "uses": 2, "ps_loads": 2, "confidence": "high"}]


def test_inline_only_global_is_not_flagged(patched):
    # No caching temp -> only the inverse (ADD) could apply, which is
    # deliberately not emitted (unreliable: compare-chain CSE / index reuse /
    # mutually-exclusive branches).  So nothing fires.
    name = patched("void f(void){ use(g); use2(g); }", {"g": 0x72aa4})
    ps = [_i("mov eax, [0x72aa4]"), _i("call 0x10"), _i("mov eax, [0x72aa4]")]
    assert rh.detect_reload_hints(name, ps, has_body_diff=True) == []


def test_render_empty_is_blank():
    assert rh.render([]) == ""
    assert rh.to_json([]) is None
