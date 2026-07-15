"""Tests for the precise global-array-element cache detector
(c2/commands/global_cache_hints.py).

The detector is AST-based and resolves array-vs-pointer-vs-scalar from the
real project headers, so these tests use real global names:
  * ``svga_refresh_data`` / ``text_buffer`` — arrays
  * ``text_pointer`` / ``city_qptr``        — pointers
  * ``data_ptr``                            — scalar (declared int)
"""

from c2.commands.global_cache_hints import detect_in_body, _global_types


def _globals(body):
    return {h.global_ for h in detect_in_body(body)}


# ── the anti-pattern fires ───────────────────────────────────────────────────

def test_address_of_array_element_flagged():
    body = ("void f(int idx){ struct svga_cell *cell = &svga_refresh_data[idx];"
            " g(cell->screen_off); }")
    assert "svga_refresh_data" in _globals(body)


def test_array_plus_index_flagged():
    body = ("void f(int idx){ char *p = svga_refresh_data + idx;"
            " g(*p); }")
    assert "svga_refresh_data" in _globals(body)


def test_assignment_form_flagged():
    body = ("void f(int idx){ struct svga_cell *cell;"
            " cell = &svga_refresh_data[idx]; g(cell->screen_off); }")
    assert "svga_refresh_data" in _globals(body)


# ── legitimate forms are NOT flagged ─────────────────────────────────────────

def test_pointer_global_copy_not_flagged():
    # copying a global that is itself a pointer is a base-cursor copy.
    body = "void f(void){ char *p = text_pointer; while(*p) p++; }"
    assert _globals(body) == set()


def test_moving_cursor_into_array_not_flagged():
    # &array[off] but advanced with p++ -> genuine cursor, like load_to_text_buffer.
    body = ("void f(int off){ char *dst = &text_buffer[off];"
            " while(*dst) dst++; *dst = 0; }")
    assert _globals(body) == set()


def test_compound_advance_not_flagged():
    body = ("void f(int off){ char *dst = &text_buffer[off];"
            " dst += 4; g(*dst); }")
    assert _globals(body) == set()


def test_bare_array_base_not_flagged():
    # p = whole_array (no index) -> base cursor, not an element alias.
    body = "void f(void){ char *p = text_buffer; g(*p); }"
    assert _globals(body) == set()


def test_scalar_global_not_flagged():
    # data_ptr is declared int (scalar), even if cast to a pointer.
    body = "void f(void){ char *p = (char *)data_ptr; g(*p); }"
    assert _globals(body) == set()


def test_local_array_not_flagged():
    body = ("void f(int i){ char buf[40]; char *p = &buf[i]; g(*p); }")
    assert _globals(body) == set()


def test_unknown_name_not_flagged():
    body = ("void f(int i){ char *p = &not_a_real_global[i]; g(p->x); }")
    assert _globals(body) == set()


# ── header type classification sanity ────────────────────────────────────────

def test_global_type_classification():
    gt = _global_types()
    assert gt.get("svga_refresh_data") == "array"
    assert gt.get("text_buffer") == "array"
    assert gt.get("text_pointer") == "pointer"
    assert gt.get("city_qptr") == "pointer"
