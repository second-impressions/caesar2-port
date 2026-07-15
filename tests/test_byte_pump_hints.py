"""Tests for ``c2.commands.byte_pump_hints`` (Rule 119)."""
from __future__ import annotations

from unittest.mock import patch

import pycparser

from c2.commands.byte_pump_hints import (
    BytePumpHint,
    detect,
    render,
    to_json,
)


def _parse_to_fundef(src: str) -> pycparser.c_ast.FuncDef:
    """Parse a single-function C source into its FuncDef node."""
    # Wrap in declarations the parser might need.
    full = "extern char text_buffer[];\n" + src
    ast = pycparser.CParser().parse(full)
    for ext in ast.ext:
        if isinstance(ext, pycparser.c_ast.FuncDef):
            return ext
    raise ValueError("no FuncDef found")


def _patch_source_index(fn_name: str, src: str):
    """Return a patched ``_source_index`` that resolves ``fn_name`` to the
    parsed FuncDef of ``src``."""
    node = _parse_to_fundef(src)
    return patch(
        "c2.commands.byte_pump_hints._source_index",
        lambda: {fn_name: ("test.c", node, 1)},
    )


# ── Detection: positive cases ───────────────────────────────────────────────


def test_detects_24bit_accumulator_pattern():
    """The canonical 24-bit byte-pump composite -- get_buffer_ofset's
    pre-fix shape -- fires Rule 119 with accumulator='r'."""
    src = """
    int get_buffer_ofset(int idx) {
        int off = idx * 4;
        int r;
        r  = (unsigned char)text_buffer[off + 0xa];
        r <<= 16;
        r += (unsigned char)text_buffer[off + 9] << 8;
        r += (unsigned char)text_buffer[off + 8];
        return r;
    }
    """
    with _patch_source_index("get_buffer_ofset", src):
        hint = detect("get_buffer_ofset")
    assert hint is not None
    assert hint.accumulator == "r"
    assert hint.compound_op_count == 3   # <<= + 2x +=
    assert hint.byte_zext_assign_count == 1  # r = (uchar)... (the first stmt)
    assert hint.returned is True
    assert hint.existing_byte_scratch is None


def test_detects_or_assignment_form():
    """``|=`` is treated as a compound op (it routes through the same OR-RMW
    optab as ``+=`` does ADD-RMW)."""
    src = """
    int build_le24(int idx) {
        int r;
        r  = (unsigned char)text_buffer[idx];
        r |= (unsigned char)text_buffer[idx + 1] << 8;
        r |= (unsigned char)text_buffer[idx + 2] << 16;
        return r;
    }
    """
    with _patch_source_index("build_le24", src):
        hint = detect("build_le24")
    assert hint is not None
    assert hint.accumulator == "r"
    assert hint.compound_op_count == 2
    assert hint.byte_zext_assign_count >= 1


# ── Detection: negative cases ───────────────────────────────────────────────


def test_does_not_fire_when_scratch_pattern_present():
    """Post-fix get_buffer_ofset shape: byte loads route through `t`
    (>=2 byte-zext direct assigns -- the SCRATCH role, not the
    accumulator role).  The detector must NOT misfire on this shape;
    the lever is already applied."""
    src = """
    int get_buffer_ofset(int idx) {
        int off = idx * 4;
        int r, t;
        t  = (unsigned char)text_buffer[off + 0xa];
        t <<= 16;
        r  = t;
        t  = (unsigned char)text_buffer[off + 9];
        t <<= 8;
        r += t;
        t  = (unsigned char)text_buffer[off + 8];
        r += t;
        return r;
    }
    """
    with _patch_source_index("get_buffer_ofset", src):
        hint = detect("get_buffer_ofset")
    # t has 3 byte-zext direct assigns -- it's the scratch role,
    # not the accumulator-with-byte-loads candidate.  r has compound ops
    # but NO direct byte-zext assigns.  Neither matches: no candidates.
    assert hint is None


def test_does_not_fire_on_simple_function():
    """A function with no byte-pump pattern -- just simple arithmetic --
    must not fire Rule 119."""
    src = """
    int simple_sum(int a, int b, int c) {
        return a + b + c;
    }
    """
    with _patch_source_index("simple_sum", src):
        hint = detect("simple_sum")
    assert hint is None


def test_does_not_fire_on_single_compound_op():
    """One compound op is insufficient -- need >=2 (the threshold the
    detector uses)."""
    src = """
    int half_pattern(int x) {
        int r;
        r = (unsigned char)text_buffer[x];
        r <<= 8;
        return r;
    }
    """
    with _patch_source_index("half_pattern", src):
        hint = detect("half_pattern")
    # Only 1 compound op (<<=) -- below threshold.
    assert hint is None


def test_does_not_fire_when_unknown_function():
    """An unknown name returns None gracefully (no exception)."""
    with patch(
        "c2.commands.byte_pump_hints._source_index",
        lambda: {},
    ):
        assert detect("nope") is None


# ── Render / JSON ───────────────────────────────────────────────────────────


def test_render_full_message_for_unfixed_pattern():
    """The render() text for an unfixed pattern points at the candidate AND
    suggests the workhorse-rotation rewrite."""
    hint = BytePumpHint(
        function="foo",
        accumulator="r",
        compound_op_count=3,
        byte_zext_assign_count=1,
        returned=True,
        existing_byte_scratch=None,
    )
    msg = render(hint)
    assert "'r'" in msg
    assert "3 compound" in msg
    assert "1 byte-zext" in msg
    assert "returned" in msg
    assert "int t" in msg.replace("``", "")  # the suggestion text


def test_render_acknowledges_existing_scratch():
    """When a byte scratch already exists, the suggestion text differs:
    move shifts onto the existing scratch rather than introduce a new one."""
    hint = BytePumpHint(
        function="foo",
        accumulator="r",
        compound_op_count=2,
        byte_zext_assign_count=1,
        returned=True,
        existing_byte_scratch="t",
    )
    msg = render(hint)
    assert "'t'" in msg
    assert "move shifts onto" in msg


def test_to_json_schema():
    """JSON output has the documented fields and Rule 119 marker."""
    hint = BytePumpHint(
        function="get_buffer_ofset",
        accumulator="r",
        compound_op_count=3,
        byte_zext_assign_count=1,
        returned=True,
        existing_byte_scratch=None,
    )
    js = to_json(hint)
    assert js["rule"] == "119"
    assert js["name"] == "byte_pump_workhorse"
    assert js["function"] == "get_buffer_ofset"
    assert js["accumulator"] == "r"
    assert js["compound_op_count"] == 3
    assert js["byte_zext_assign_count"] == 1
    assert js["returned"] is True
    assert js["existing_byte_scratch"] is None
