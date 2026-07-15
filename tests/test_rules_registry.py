"""Tests for the codegen-rules verification registry."""
from __future__ import annotations

from c2.commands import rules_registry as rr


def test_lookup_and_status_values():
    assert rr.verdict_for("1") is not None
    assert rr.verdict_for("9").status == "verified"
    assert rr.verdict_for("99999") is None
    for v in rr.VERDICTS:
        assert v.status in ("verified", "corrected", "debunked", "unreviewed")
        # corrected/debunked must carry the real mechanism
        if v.status in ("corrected", "debunked"):
            assert v.mechanism, f"Rule {v.rule} {v.status} needs a mechanism"


def test_corrected_docs_become_verified():
    # wrong mechanisms are CORRECTED in the doc itself, not left as a lingering
    # "corrected" annotation -> no rule should stay in the corrected state.
    assert not [v for v in rr.VERDICTS if v.status == "corrected"]


def test_render_includes_instrumentation_note():
    line = rr.render_verdict_lines([rr.verdict_for("28")])[0]
    assert "INSTRUMENTED" in line and "regalloc (actual 10.0a)" in line
    # static rules carry no instrumentation note
    assert "INSTRUMENTED" not in rr.render_verdict_lines([rr.verdict_for("9")])[0]


def test_universality_classification():
    # deterministic front-end/optab rules are universal; allocator/pressure/
    # queue rules are conditional and MUST carry a caveat.
    assert rr.verdict_for("9").universal      # FlipBranch deterministic
    assert rr.verdict_for("4").universal      # operator preservation
    assert not rr.verdict_for("15").universal  # tail-merge build artifact
    assert not rr.verdict_for("18").universal  # pressure-gated
    assert not rr.verdict_for("28").universal  # regalloc tie
    for v in rr.VERDICTS:
        if not v.universal:
            assert v.caveat, f"Rule {v.rule} conditional but has no caveat"
    # every instrumentation-backed rule is also conditional (the structural fact)
    for r in rr.instrumented_rules():
        assert not rr.verdict_for(r).universal


def test_render_tags_tier_and_caveat():
    cond = rr.render_verdict_lines([rr.verdict_for("15")])[0]
    assert "CONDITIONAL" in cond and "does NOT always hold" in cond
    det = rr.render_verdict_lines([rr.verdict_for("9")])[0]
    assert "deterministic" in det and "does NOT always hold" not in det


def test_verdicts_for_hist_parses_labels_and_dedups():
    vs = rr.verdicts_for_hist(["Rule 9", "Rule 9", "Rule 4", "Reg swap", "Rule 99999"])
    ids = [v.rule for v in vs]
    assert ids == ["9", "4"]   # deduped, order preserved, unknown dropped


def test_render_leads_with_actionable_hint():
    # every line leads with the actionable hint
    verified = rr.render_verdict_lines([rr.verdict_for("9")])[0]
    assert "if-body" in verified.lower() or "Jcc" in verified
    assert "Rule 9" in verified

    # the render machinery still handles a corrected/debunked verdict if one
    # ever exists (synthetic), appending the real mechanism
    synth = rr.RuleVerdict(rule="X", title="t", status="corrected",
                           hint="do Y", mechanism="real cause Z")
    line = rr.render_verdict_lines([synth])[0]
    assert "do Y" in line and "[why: real cause Z]" in line


def test_every_verdict_has_actionable_hint():
    for v in rr.VERDICTS:
        assert v.hint and len(v.hint) > 20, f"Rule {v.rule} needs an actionable hint"


def test_no_duplicate_rule_ids():
    ids = [v.rule for v in rr.VERDICTS]
    assert len(ids) == len(set(ids))
