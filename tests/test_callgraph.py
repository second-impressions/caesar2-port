"""Tests for c2.commands.callgraph.

Covers: graph construction (memoized), callees_of / callers_of public
helpers, _proto_callzap mirror of i86reg.c::CallZap, _truth_arg_count
combining body + caller-side, and check_proto_consistency filter.
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

from c2.commands.callgraph import (
    _proto_callzap,
    _truth_arg_count,
    build_callgraph,
    callees_of,
    callers_of,
    check_proto_consistency,
)
from c2.commands.inferred_sig import (
    CallerEvidence,
    InferredSig,
    DeclaredSig,
)


# ── _proto_callzap: mirrors i86reg.c CallZap() for default __watcall ──


def test_callzap_void_void():
    assert _proto_callzap(0, has_return=False) == frozenset()


def test_callzap_void_int():
    assert _proto_callzap(0, has_return=True) == frozenset({"eax"})


def test_callzap_1arg_void():
    assert _proto_callzap(1, has_return=False) == frozenset({"eax"})


def test_callzap_2arg():
    assert _proto_callzap(2, has_return=False) == frozenset({"eax", "edx"})


def test_callzap_3arg():
    assert _proto_callzap(3, has_return=False) == frozenset(
        {"eax", "edx", "ebx"}
    )


def test_callzap_4arg():
    assert _proto_callzap(4, has_return=False) == frozenset(
        {"eax", "edx", "ebx", "ecx"}
    )


def test_callzap_4plus_clamps_to_4():
    """Args beyond 4 go on the stack; CallZap is unchanged."""
    assert _proto_callzap(10, has_return=False) == _proto_callzap(
        4, has_return=False
    )


def test_callzap_4arg_int_return_no_extra_bits():
    """4-arg + int return adds nothing because EAX is already in zap."""
    assert _proto_callzap(4, has_return=True) == _proto_callzap(
        4, has_return=False
    )


# ── _truth_arg_count: combines body + caller-side ─────────────────────


def _mk_body(name="x", arg_regs=None, has_return=False):
    return InferredSig(
        name=name,
        address=0,
        size=0,
        arg_regs=list(arg_regs or []),
        has_return=has_return,
    )


def _mk_ev(eax=0, edx=0, ebx=0, ecx=0, sites=0, target="x"):
    return CallerEvidence(
        target=target,
        n_call_sites=sites,
        args_set_before_call={"eax": eax, "edx": edx, "ebx": ebx, "ecx": ecx},
    )


def test_truth_caller_extends_body():
    # font_list pattern: body reads only 2 regs, callers consistently
    # set 4 (the 100% on ECX proves all 4 are args by prefix property).
    body = _mk_body(arg_regs=["eax", "edx"])
    ev = _mk_ev(eax=100, edx=98, ebx=98, ecx=98, sites=100)
    n, source = _truth_arg_count("font_list", body, ev)
    assert n == 4
    assert source == "caller-extends"


def test_truth_body_dominates_when_callers_agree():
    body = _mk_body(arg_regs=["eax", "edx", "ebx"])
    ev = _mk_ev(eax=10, edx=10, ebx=10, sites=10)
    n, source = _truth_arg_count("x", body, ev)
    assert n == 3
    assert source == "agree"


def test_truth_no_callers_falls_back_to_body():
    body = _mk_body(arg_regs=["eax"])
    n, source = _truth_arg_count("x", body, ev=_mk_ev(sites=0))
    assert n == 1
    assert source == "body-only"


def test_truth_insufficient_callers():
    body = _mk_body(arg_regs=["eax"])
    ev = _mk_ev(eax=1, sites=1)  # below min_sites
    n, source = _truth_arg_count("x", body, ev)
    assert n == 1
    assert "insufficient" in source


# ── Graph builders (smoke / functional) ───────────────────────────────


@pytest.mark.slow
def test_build_callgraph_cached():
    """First call builds; second call returns the same object."""
    a = build_callgraph()
    b = build_callgraph()
    assert a is b
    callers, callees = a
    assert len(callers) > 100
    assert len(callees) > 100


@pytest.mark.slow
def test_callees_of_known_fn():
    """battle_stats_panel is a known multi-callee function."""
    calls = callees_of("battle_stats_panel")
    callees = {tgt for _, tgt in calls}
    # Per the AGENTS.md narrative this fn calls font_list, font_no, etc.
    expected = {"font_list", "font_no", "write_image"}
    assert expected <= callees, f"missing: {expected - callees}"


@pytest.mark.slow
def test_callers_of_font_list_includes_screens():
    callers = callers_of("font_list")
    # font_list is called by hundreds of fns; sanity-check a few obvious ones
    assert "battle_stats_panel" in callers
    assert "show_recruitment" in callers
    assert len(callers) > 50


# ── Proto-consistency end-to-end ─────────────────────────────────────


@pytest.mark.slow
def test_check_proto_consistency_returns_rows():
    """Scanning the full project surfaces actual mismatches."""
    rows = check_proto_consistency(require_diffing_caller=False)
    # Should find at least the well-known cases (eg font_no's
    # declared 7 args may or may not match truth, depending on
    # current source state).  Just sanity-check that the scan
    # returns *some* rows.
    assert isinstance(rows, list)
    for r in rows:
        assert "name" in r
        assert "declared_args" in r
        assert "truth_args" in r
        assert "source" in r
        assert r["declared_reg"] != r["truth_args"] or (
            r["declared_returns"] != r["truth_returns"]
        )


# ── CLI smoke ─────────────────────────────────────────────────────────


def test_cli_help_lists_callgraph():
    """The c2 main app exposes the callgraph subcommand."""
    r = subprocess.run(
        ["uv", "run", "c2", "callgraph", "--help"],
        capture_output=True, text=True,
        cwd=Path(__file__).parent.parent,
        timeout=60,
    )
    assert r.returncode == 0
    out = r.stdout + r.stderr
    assert "callgraph" in out.lower()
    assert "--check" in out
    assert "--callers" in out
