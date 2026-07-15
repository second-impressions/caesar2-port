"""Smoke tests for ``c2 stubs --donors`` mode.

The donor scanner is a thin orchestration layer over
``scan_tail_merge_donor`` (already covered in detail by
``tests/test_tail_merge.py``).  These tests verify the
end-to-end CLI behaviour against the real PS.EXE — mainly to
catch regressions where the orchestration breaks even though
the underlying scanner is fine.

Skipped when ``data/PS.EXE`` or ``data/out/symbols.json`` are
missing (e.g. fresh checkout without binary).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from typer.testing import CliRunner

sys.path.insert(0, ".")

from c2.app import app


_NEEDS_DATA = pytest.mark.skipif(
    not (
        Path("data/PS.EXE").exists()
        and Path("data/out/symbols.json").exists()
    ),
    reason="needs PS.EXE + symbols.json",
)


@_NEEDS_DATA
def test_donors_mode_returns_json_with_required_fields() -> None:
    """``--donors --json`` returns a list of donor records, each with
    ``name``, ``size``, ``deps``, ``dep_count``, ``blocked_bytes``,
    ``is_stub``, and ``file``.

    Uses ``--include-decompiled`` (audit mode) so the test exercises
    a non-empty result set even when the stub-only donor corpus is
    drained (the current target state).  ``test_donors_stub_only_empty_state``
    pins the empty stub-only case separately.
    """
    runner = CliRunner()
    result = runner.invoke(
        app, ["stubs", "--donors", "--include-decompiled",
              "--json", "--limit", "5"],
    )
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert "donors" in data
    assert len(data["donors"]) >= 1
    for d in data["donors"]:
        assert {"name", "size", "deps", "dep_count",
                "blocked_bytes", "is_stub", "file"} <= set(d)
        assert d["dep_count"] == len(d["deps"])
        assert d["blocked_bytes"] == sum(dep["size"] for dep in d["deps"])
        for dep in d["deps"]:
            assert {"name", "size", "merge_offset",
                    "tail_bytes", "address"} <= set(dep)


@_NEEDS_DATA
def test_donors_stub_only_empty_state() -> None:
    """Stub-only mode (default, no ``--include-decompiled``) returns a
    well-formed empty list when the stub-donor corpus is drained — the
    target state of the project, not a bug.  Exit 0, valid JSON, empty
    ``donors`` array.  When stub donors return, this test will continue
    to pass (the assertion is the WELL-FORMED contract, not emptiness).
    """
    runner = CliRunner()
    result = runner.invoke(
        app, ["stubs", "--donors", "--json", "--limit", "20"],
    )
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert "donors" in data
    assert isinstance(data["donors"], list)
    # Whatever's in the stub-only set must be a stub.
    assert all(d["is_stub"] for d in data["donors"])


@_NEEDS_DATA
def test_donors_mode_default_filters_to_stubs() -> None:
    """Without ``--include-decompiled``, all donor rows are stubs.

    Vacuously true when the stub-donor corpus is drained (the current
    target state); ``test_donors_stub_only_empty_state`` pins that.
    """
    runner = CliRunner()
    result = runner.invoke(
        app, ["stubs", "--donors", "--json", "--limit", "20"],
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert all(d["is_stub"] for d in data["donors"])


@_NEEDS_DATA
def test_donors_mode_include_decompiled_audit() -> None:
    """``--include-decompiled`` returns more donors than the
    stub-only default (audit mode listing already-decompiled
    donors that should already be triggering tail-merge).
    """
    runner = CliRunner()
    only_stubs = json.loads(runner.invoke(
        app, ["stubs", "--donors", "--json", "--limit", "0"],
    ).output)
    with_all = json.loads(runner.invoke(
        app, ["stubs", "--donors", "--include-decompiled",
              "--json", "--limit", "0"],
    ).output)
    assert len(with_all["donors"]) > len(only_stubs["donors"])
    # Every stub-only donor must also appear in audit mode.
    stub_names = {d["name"] for d in only_stubs["donors"]}
    audit_names = {d["name"] for d in with_all["donors"]}
    assert stub_names <= audit_names


@_NEEDS_DATA
def test_donors_mode_max_size_filter() -> None:
    """``--max-size`` filters donor body size; rows obey the cap.

    Uses audit mode (``--include-decompiled``) so the filter has data
    to act on regardless of the stub-only corpus state.
    """
    runner = CliRunner()
    result = runner.invoke(
        app, ["stubs", "--donors", "--include-decompiled",
              "--max-size", "300", "--json", "--limit", "0"],
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert len(data["donors"]) >= 1
    for d in data["donors"]:
        assert d["size"] <= 300


@_NEEDS_DATA
def test_donors_mode_sort_order() -> None:
    """Rows are sorted by ``dep_count desc, size asc``.

    Uses audit mode to ensure a non-trivial multi-row sort regardless
    of stub-only corpus state.
    """
    runner = CliRunner()
    result = runner.invoke(
        app, ["stubs", "--donors", "--include-decompiled",
              "--json", "--limit", "20"],
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    rows = data["donors"]
    for prev, curr in zip(rows, rows[1:]):
        assert (prev["dep_count"], -prev["size"]) >= (
            curr["dep_count"], -curr["size"],
        )


@_NEEDS_DATA
def test_donors_text_output_smoke() -> None:
    """Default text output contains expected header columns + footer
    when there's data to render.

    Uses audit mode so the renderer exercises non-empty output
    regardless of stub-only corpus state.
    """
    runner = CliRunner()
    result = runner.invoke(
        app, ["stubs", "--donors", "--include-decompiled", "--limit", "3"],
    )
    assert result.exit_code == 0
    assert "deps" in result.output
    assert "size" in result.output
    assert "stub" in result.output
    # Footer.
    assert "donor candidates" in result.output


@_NEEDS_DATA
def test_donors_text_output_empty_message() -> None:
    """When stub-only mode is empty, text output is the explicit
    'no donor candidates match the given filters' message (exit 0).
    Pins the empty-state UX.
    """
    runner = CliRunner()
    json_result = runner.invoke(
        app, ["stubs", "--donors", "--json", "--limit", "0"],
    )
    if json.loads(json_result.output)["donors"]:
        pytest.skip("stub-only donors present — empty-state UX not exercised")
    text_result = runner.invoke(app, ["stubs", "--donors", "--limit", "3"])
    assert text_result.exit_code == 0
    assert "no donor candidates match the given filters" in text_result.output


@_NEEDS_DATA
def test_donors_show_deps_lists_dependents() -> None:
    """``--show-deps`` prints an indented list of dependents.

    Uses audit mode so the renderer has a donor to expand dependents
    under regardless of stub-only corpus state.
    """
    runner = CliRunner()
    result = runner.invoke(
        app, ["stubs", "--donors", "--include-decompiled",
              "--show-deps", "--limit", "1"],
    )
    assert result.exit_code == 0
    # The arrow marker indicates a dependent line.
    assert "↳" in result.output
    # Format: "↳ NAME ... (NN b, merge +0xXX)"
    assert " b, merge +0x" in result.output
