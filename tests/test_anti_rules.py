"""Tests for the anti-rule oracle (c2/commands/anti_rules.py)."""

from c2.commands.anti_rules import (
    rule_titles, rule_label, feature_rules, classify_family_coverage,
    GENERIC_HINTS,
)


def test_rule_titles_parsed_from_catalogue():
    titles = rule_titles()
    # A handful of well-known rules must be present and non-empty.
    for num in ("82", "62", "16", "95", "28b"):
        assert num in titles, f"Rule {num} missing from catalogue parse"
        assert titles[num]
    # First-heading-wins: Rule 82 is the ternary-pin rule.
    assert "x == 0" in titles["82"]


def test_rule_label_truncates_and_prefixes():
    lbl = rule_label("62")
    assert lbl.startswith("Rule 62 — ")
    assert len(lbl) <= len("Rule 62 — ") + 64


def test_rule_label_unknown():
    assert rule_label("9999") == "Rule 9999"


def test_feature_rules_known():
    # Each construct cites exactly ONE canonical rule (no multi-rule shotgun).
    rules, anti = feature_rules("ternary")
    assert rules == ["82"]
    assert "82" in anti


def test_feature_rules_single_canonical():
    from c2.commands.anti_rules import FEATURE_RULES
    for feat, (rules, _) in FEATURE_RULES.items():
        assert len(rules) <= 1, f"{feat} cites {rules} (must be <=1 canonical rule)"


def test_feature_rules_novel():
    rules, anti = feature_rules("nested-ternary")
    assert rules == []
    assert anti  # still has prose


def test_feature_rules_unknown_feature():
    assert feature_rules("does-not-exist") == ([], "")


# ── family coverage classification ──────────────────────────────────────────

def test_coverage_known():
    verdict, rules = classify_family_coverage({"Rule 16", "Rule 73"})
    assert verdict == "known"
    assert rules == ["16", "73"]


def test_coverage_partial():
    verdict, rules = classify_family_coverage({"Rule 16", "Reg swap"})
    assert verdict == "partial"
    assert rules == ["16"]


def test_coverage_novel_generic_only():
    verdict, rules = classify_family_coverage({"Reg swap", "Byte-reg swap"})
    assert verdict == "novel"
    assert rules == []


def test_coverage_novel_empty():
    verdict, rules = classify_family_coverage(set())
    assert verdict == "novel"
    assert rules == []


def test_generic_hints_are_classifiers():
    assert "Reg swap" in GENERIC_HINTS
    assert "Byte-reg swap" in GENERIC_HINTS
    assert "Rule 16" not in GENERIC_HINTS
