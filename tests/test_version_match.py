"""Smoke tests for c2 version-match."""

from __future__ import annotations

from pathlib import Path

import pytest

from c2.commands.version_match import build_reference, match_variant


ROOT = Path(__file__).resolve().parents[1]
SYMBOLS = ROOT / "data/out/symbols.json"
REF_EXE = ROOT / "data/PS.EXE"
VARIANTS = ROOT / "data/variants"


@pytest.fixture(scope="module")
def ref():
    if not (SYMBOLS.exists() and REF_EXE.exists()):
        pytest.skip("reference symbols.json or PS.EXE missing")
    return build_reference(SYMBOLS, REF_EXE)


def test_self_match_is_all_exact(ref):
    """Matching the reference against itself must produce 100% exact matches
    on every anchored function and anchor ≥99% of named ref fns.  The
    residual <1% are CRT helpers with byte-identical duplicates that can't
    be uniquely placed by content alone (e.g. two `mov eax, N; ret` stubs)."""
    result = match_variant(ref, REF_EXE)
    assert result.cand_code_size == len(ref.code)
    statuses = {m.status for m in result.matches}
    assert statuses == {"exact"}, f"unexpected statuses: {statuses}"
    assert len(result.matches) / len(ref.fns) > 0.99, (
        f"only anchored {len(result.matches)}/{len(ref.fns)}"
    )


@pytest.mark.parametrize("variant", [
    "ps_c95790fa.exe",  # 5-CD common older release
    "ps_e18875e9.exe",  # eu-only oldest release
])
def test_older_variant_mostly_matches(ref, variant):
    """Older PS.EXE variants should anchor ≥85% of named ref fns,
    of which ≥95% are byte-exact (modulo fixups + rel disps).
    Catches regressions in masking, prefix-search, or module
    interpolation logic."""
    p = VARIANTS / variant
    if not p.exists():
        pytest.skip(f"{variant} not extracted")
    result = match_variant(ref, p)
    n = len(result.matches)
    assert n >= 0.85 * len(ref.fns), \
        f"only anchored {n}/{len(ref.fns)} ({n/len(ref.fns)*100:.1f}%)"
    exact = sum(1 for m in result.matches if m.status == "exact")
    assert exact / n >= 0.95, \
        f"only {exact}/{n} ({exact/n*100:.1f}%) anchored fns are exact"


def test_module_interp_methods_engage(ref):
    """Verify Phase A3/A4 actually contribute to self-match anchoring
    (i.e. the module-locality leverage is wired up correctly)."""
    result = match_variant(ref, REF_EXE)
    methods = {m.method for m in result.matches}
    assert "module-interp" in methods, \
        "Phase A3 (module interpolation) didn't anchor any fns"
    assert "tiny-body" in methods, \
        "Phase A0 (tiny-body) didn't anchor any fns"
    assert "unique-prefix" in methods, \
        "Phase A1 (unique-prefix) didn't anchor any fns"
