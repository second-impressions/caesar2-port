"""Tests for c2.commands.sig_drift.

CallZapSig equality, TUDecl extraction, drift detection rules.
"""
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

from c2.commands.sig_drift import (
    CallZapSig,
    Drift,
    TUDecl,
    scan_all_tu_declarations,
)


# ── CallZapSig equality ignores n_total_args ──────────────────────────


def test_callzap_equality_ignores_total_args():
    """4 reg args is 4 reg args, whether total is 4 or 6 (stack extras)."""
    a = CallZapSig.from_counts(4, returns_void=True)
    b = CallZapSig.from_counts(6, returns_void=True)
    assert a == b
    assert hash(a) == hash(b)


def test_callzap_distinct_on_reg_arg_count():
    a = CallZapSig.from_counts(3, returns_void=True)
    b = CallZapSig.from_counts(4, returns_void=True)
    assert a != b


def test_callzap_distinct_on_return_type():
    a = CallZapSig.from_counts(2, returns_void=True)
    b = CallZapSig.from_counts(2, returns_void=False)
    assert a != b


def test_callzap_clamps_to_4_reg_args():
    a = CallZapSig.from_counts(4, returns_void=False)
    b = CallZapSig.from_counts(10, returns_void=False)
    assert a == b


def test_callzap_render_short():
    sig = CallZapSig.from_counts(2, returns_void=True)
    assert sig.render() == "void f(int, int)"


def test_callzap_render_void_void():
    sig = CallZapSig.from_counts(0, returns_void=True)
    assert sig.render() == "void f(void)"


def test_callzap_render_5_args_uses_ellipsis():
    sig = CallZapSig.from_counts(5, returns_void=False)
    # First 4 are int (reg), 5th is "..." to denote stack
    assert "..." in sig.render()


# ── Drift bucketization ───────────────────────────────────────────────


def _decl(name, file, n_args, returns_void, kind="extern", line=1):
    return TUDecl(
        name=name, file=file, line=line, kind=kind,
        return_type="void" if returns_void else "int",
        arg_types=["int"] * n_args,
        raw="",
    )


def test_drift_no_drift_when_all_agree_with_truth():
    decls = [
        _decl("f", "a.c", 4, True),
        _decl("f", "b.c", 4, True),
    ]
    truth = CallZapSig.from_counts(4, returns_void=True)
    d = Drift(name="f", decls=decls, truth_sig=truth)
    assert not d.has_inter_tu_drift()
    assert not d.has_truth_drift()
    assert not d.has_any_drift()


def test_drift_4_vs_6_args_not_inter_tu():
    """4-arg and 6-arg decls have IDENTICAL CallZap (both clamp to 4).
    So they're NOT inter-TU drift, even though the C sigs differ."""
    decls = [
        _decl("f", "a.c", 4, True),
        _decl("f", "b.c", 6, True),
    ]
    truth = CallZapSig.from_counts(4, returns_void=True)
    d = Drift(name="f", decls=decls, truth_sig=truth)
    assert not d.has_inter_tu_drift()


def test_drift_inter_tu_real():
    decls = [
        _decl("f", "a.c", 2, True),
        _decl("f", "b.c", 4, True),
    ]
    truth = CallZapSig.from_counts(4, returns_void=True)
    d = Drift(name="f", decls=decls, truth_sig=truth)
    assert d.has_inter_tu_drift()
    assert d.has_truth_drift()  # a.c disagrees with truth
    buckets = d.buckets()
    assert len(buckets) == 2


def test_drift_truth_only_no_inter_tu():
    """All TUs agree with each other but all disagree with truth."""
    decls = [
        _decl("f", "a.c", 2, True),
        _decl("f", "b.c", 2, True),
    ]
    truth = CallZapSig.from_counts(4, returns_void=True)
    d = Drift(name="f", decls=decls, truth_sig=truth)
    assert not d.has_inter_tu_drift()
    assert d.has_truth_drift()
    assert d.has_any_drift()


def test_drift_4_vs_6_args_same_callzap():
    """4-arg and 6-arg declarations are CallZap-equivalent (both clamp to 4)."""
    decls = [
        _decl("f", "a.c", 4, True),
        _decl("f", "b.c", 6, True),
    ]
    truth = CallZapSig.from_counts(6, returns_void=True)  # both = 4 reg args
    d = Drift(name="f", decls=decls, truth_sig=truth)
    assert not d.has_inter_tu_drift()
    assert not d.has_truth_drift()


def test_drift_no_truth_only_inter_tu():
    """When truth_sig is None, only inter-TU drift can be detected."""
    decls = [
        _decl("f", "a.c", 2, True),
        _decl("f", "b.c", 3, True),
    ]
    d = Drift(name="f", decls=decls, truth_sig=None)
    assert d.has_inter_tu_drift()
    assert not d.has_truth_drift()  # no truth to compare against
    assert d.has_any_drift()


# ── TU scanning over a temp .c file ───────────────────────────────────


def test_scan_extracts_extern_forward_def(tmp_path):
    """Verify scan_all_tu_declarations finds all three decl kinds."""
    (tmp_path / "src").mkdir()
    src = tmp_path / "src" / "test.c"
    src.write_text(textwrap.dedent("""
        extern void foo(int a, int b);

        void bar(int x);

        int baz(int x, int y, int z, int w) {
            return x + y + z + w;
        }
    """))

    out = scan_all_tu_declarations([tmp_path / "src"])
    assert "foo" in out
    assert "bar" in out
    assert "baz" in out
    assert out["foo"][0].kind == "extern"
    assert out["foo"][0].n_args == 2
    assert out["foo"][0].returns_void is True
    assert out["bar"][0].kind == "forward"
    assert out["bar"][0].n_args == 1
    assert out["baz"][0].kind == "def"
    assert out["baz"][0].n_args == 4
    assert out["baz"][0].returns_void is False


def test_scan_multiple_files_same_name(tmp_path):
    """Same function declared in two TUs → both decls collected."""
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "a.c").write_text(
        "extern void f(int a, int b);\n"
    )
    (tmp_path / "src" / "b.c").write_text(
        "extern void f(int a, int b, int c, int d);\n"
    )
    out = scan_all_tu_declarations([tmp_path / "src"])
    assert "f" in out
    assert len(out["f"]) == 2
    files = {d.file for d in out["f"]}
    assert any("a.c" in f for f in files)
    assert any("b.c" in f for f in files)
    # Different arg counts → would be inter-TU drift.
    arg_counts = {d.n_args for d in out["f"]}
    assert arg_counts == {2, 4}


# ── CLI smoke ─────────────────────────────────────────────────────────


def test_cli_help_lists_sig_drift():
    r = subprocess.run(
        ["uv", "run", "c2", "sig-drift", "--help"],
        capture_output=True, text=True,
        cwd=Path(__file__).parent.parent,
        timeout=60,
    )
    assert r.returncode == 0
    out = r.stdout + r.stderr
    assert "sig-drift" in out.lower() or "drift" in out.lower()
    assert "--by-tu" in out
    assert "--callzap" in out or "--all-drift" in out
    assert "--actionable" in out


# ── ActionableDrift / actionable_drift ───────────────────────────────


def test_actionable_drift_filters_correctly():
    """actionable_drift only surfaces cases where a diffing caller's TU
    declares the callee with a non-truth sig."""
    from c2.commands.sig_drift import actionable_drift, ActionableDrift
    # Run with an empty diffing_fns set: should produce no actionable rows
    # regardless of how much drift exists in the project.
    rows = actionable_drift(diffing_fns=set())
    assert all(isinstance(r, ActionableDrift) for r in rows)
    assert all(r.n_actionable > 0 for r in rows)
    # With no diffing fns, every actionable count should be 0 -> filtered
    assert len(rows) == 0


def test_actionable_drift_returns_sorted():
    """Results are sorted by n_actionable desc, then n_diffing desc, then name."""
    from c2.commands.sig_drift import actionable_drift
    rows = actionable_drift()  # uses real diffing-status cache
    # Verify ordering invariant
    for i in range(len(rows) - 1):
        a, b = rows[i], rows[i + 1]
        # a should sort before b
        ka = (-a.n_actionable, -a.n_diffing_callers, a.callee)
        kb = (-b.n_actionable, -b.n_diffing_callers, b.callee)
        assert ka <= kb, f"sort violation: {ka} > {kb}"
