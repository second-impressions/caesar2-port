"""Regression tests for symbol-only OMF PUBDEF repairs."""

import pytest

from c2.omf import OmfObject
from c2.parsers.omf import parse_obj_functions, rewrite_pubdef_offsets


def _object_with_two_functions(tmp_path):
    obj = OmfObject("sample")
    text = obj.segment("_TEXT", "CODE")
    text.data.extend(bytes(range(32)))
    obj.public(text, "first_", 0)
    obj.public(text, "alias_", 4)
    path = tmp_path / "sample.obj"
    path.write_bytes(obj.build())
    return path


def test_rewrite_pubdef_offsets_moves_symbol_without_changing_segment(tmp_path):
    path = _object_with_two_functions(tmp_path)
    before = path.read_bytes()

    after = rewrite_pubdef_offsets(before, {"alias_": 12})
    path.write_bytes(after)
    functions = {name: code for name, code, _fixups in parse_obj_functions(path)}

    assert functions["first_"] == bytes(range(12))
    assert functions["alias_"] == bytes(range(12, 32))
    assert len(after) == len(before)


def test_rewrite_pubdef_offsets_requires_exactly_one_symbol(tmp_path):
    path = _object_with_two_functions(tmp_path)

    with pytest.raises(ValueError, match="missing_=0"):
        rewrite_pubdef_offsets(path.read_bytes(), {"missing_": 12})
