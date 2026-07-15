"""Tests for confirmed_arg_count_prefix_property — __watcall-aware
caller-side arg-count inference.
"""
from c2.commands.inferred_sig import CallerEvidence


def _ev(eax=0, edx=0, ebx=0, ecx=0, sites=0, target="x"):
    return CallerEvidence(
        target=target,
        n_call_sites=sites,
        args_set_before_call={"eax": eax, "edx": edx, "ebx": ebx, "ecx": ecx},
    )


def test_all_zero_below_min_sites():
    ev = _ev(sites=2)
    n, conf = ev.confirmed_arg_count_prefix_property()
    assert n is None and conf == "insufficient"


def test_clean_4_args():
    # All four regs set by every caller (sites=100, count=100 each).
    ev = _ev(eax=100, edx=100, ebx=100, ecx=100, sites=100)
    assert ev.confirmed_arg_count_prefix_property() == (4, "confident")


def test_clean_2_args():
    # First two regs set by all 50 callers, latter two never.
    ev = _ev(eax=50, edx=50, ebx=0, ecx=0, sites=50)
    assert ev.confirmed_arg_count_prefix_property() == (2, "confident")


def test_prefix_property_rescues_pass_through():
    # font_list pattern: EAX 84%, EDX/EBX/ECX 99-100% (real 4-arg).
    # Pass-through escapes look-back window → EAX appears low,
    # but ECX 99% proves all 4 must be args by prefix property.
    ev = _ev(eax=84, edx=99, ebx=99, ecx=99, sites=100)
    n, conf = ev.confirmed_arg_count_prefix_property()
    assert n == 4, f"expected 4 (prefix-property rescue), got {n} ({conf})"


def test_above_threshold_alone_is_enough():
    # font_no pattern: EAX 94, EDX/EBX 100, ECX 90 (just below 95%
    # legacy threshold but above 85% hi_threshold).
    ev = _ev(eax=94, edx=100, ebx=100, ecx=90, sites=100)
    assert ev.confirmed_arg_count_prefix_property() == (4, "confident")


def test_below_high_threshold_no_args():
    # show_pl8file pattern: EAX 100% (16/16), EDX 62% (10/16),
    # EBX/ECX 0%.  Only EAX crosses the 85% high threshold.
    ev = _ev(eax=16, edx=10, ebx=0, ecx=0, sites=16)
    assert ev.confirmed_arg_count_prefix_property() == (1, "confident")


def test_small_sample_returns_none():
    # Only 2 callers → too few for caller-side analysis.
    ev = _ev(eax=2, edx=2, ebx=2, ecx=2, sites=2)
    n, conf = ev.confirmed_arg_count_prefix_property()
    assert n is None and conf == "insufficient"


def test_zero_callsites():
    ev = _ev(sites=0)
    n, conf = ev.confirmed_arg_count_prefix_property()
    assert n is None and conf == "insufficient"


def test_sanity_threshold_catches_holes():
    # ECX 100%, but EDX is only 10% → prefix property violated.
    # Fall back to longest well-formed prefix.
    ev = _ev(eax=100, edx=10, ebx=100, ecx=100, sites=100)
    n, conf = ev.confirmed_arg_count_prefix_property()
    assert conf in ("prefix-fallback", "sanity-fail")
    assert n in (0, 1), f"expected 0 or 1 from fallback, got {n}"


def test_threshold_customization():
    # 80% on EAX: should return 0 with default 85% threshold,
    # but accept as 1 with 75% threshold.
    ev = _ev(eax=80, edx=0, ebx=0, ecx=0, sites=100)
    assert ev.confirmed_arg_count_prefix_property() == (0, "no-args")
    n, conf = ev.confirmed_arg_count_prefix_property(hi_threshold=0.75)
    assert n == 1 and conf == "confident"


def test_legacy_method_unchanged():
    """Legacy confirmed_arg_count uses strict 80% prefix from low end."""
    # 4-arg with one slightly noisy reg: legacy returns up to noisy one
    ev = _ev(eax=100, edx=100, ebx=85, ecx=85, sites=100)
    # Legacy with 0.8 threshold should accept all 4.
    assert ev.confirmed_arg_count(threshold=0.8) == 4
    # With 0.9 threshold should stop at EDX (since EBX 85% < 90%).
    assert ev.confirmed_arg_count(threshold=0.9) == 2
