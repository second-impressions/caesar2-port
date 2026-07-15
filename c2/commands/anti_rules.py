"""Anti-rule oracle — the rule catalogue as a pattern library.

``docs/watcom-codegen-patterns.md`` is a library of **positive** rules:
``{asm-pattern PS emits  →  the C source shape that reproduces it}``.  The
``rule_hints`` detectors are the runtime arm of the same library, mapping a
diff row to ``RuleHint(rule, summary, fix)``.

This module uses that library as an **oracle for anti-rules**.  An *anti-rule*
is the inverse direction: ``{un-PS-like C construct  →  the rule that tells you
what to write instead}``.

Two consumers:

* ``negative_corpus`` flags source constructs that correlate with residue.
  Each flag is joined here to the positive rule(s) that prescribe the rewrite
  — so a smell like a ternary becomes "Rule 82 is the only PS-shaped ternary;
  anything else → if/else".  When a high-lift construct has **no** mapped
  rule, that is a **novel anti-rule discovery candidate** (the catalogue does
  not yet explain it).

* ``residue_cluster`` labels each residue family by the positive rule-hints
  its members carry.  A family dominated by a known rule is a "known
  anti-rule family"; a family whose only hints are the generic register-swap
  classifiers (or none) is a **novel anti-rule candidate family**.

The single source of truth for rule titles is the catalogue file, parsed once;
the FEATURE→RULE map is curated (the join cannot be inferred mechanically).
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

CATALOGUE = Path("docs/watcom-codegen-patterns.md")

_RULE_HEAD = re.compile(
    r"^#{2,3}\s*Rule\s+(\d+[a-z]?)\s*[—\-–:]\s*(.+?)\s*$", re.MULTILINE)


@lru_cache(maxsize=1)
def rule_titles() -> dict[str, str]:
    """``{'82': 'if (x == 0) x = N; pins indexed-load scratch ...', ...}``.

    First heading wins (a few rule numbers appear twice with sub-notes)."""
    out: dict[str, str] = {}
    try:
        text = CATALOGUE.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return out
    for m in _RULE_HEAD.finditer(text):
        num, title = m.group(1), m.group(2).strip()
        out.setdefault(num, title)
    return out


def rule_label(num: str) -> str:
    """``'Rule 82 — if (x == 0) x = N; …'`` (truncated)."""
    title = rule_titles().get(num.lstrip("Rule ").strip(), "")
    if not title:
        return f"Rule {num}"
    short = title if len(title) <= 64 else title[:61] + "…"
    return f"Rule {num} — {short}"


# ── FEATURE → anti-rule oracle ────────────────────────────────────────────────
#
# Each negative-corpus feature maps to (rule_numbers, anti_rule_phrasing).
# rule_numbers == [] means "no positive rule in the catalogue addresses this
# construct yet" → discovery candidate.  Curated, grounded in the real rules
# above (verified against the catalogue index).

FEATURE_RULES: dict[str, tuple[list[str], str]] = {
    # ternary: the ONLY PS-shaped ternary is the Rule 82 `x = c ? N : x`
    # split-live-range idiom (and Rule 26 forbids it in call args).
    "ternary": (["82"],
                "Rule 82: the only byte-exact ternary is `x = c ? N : x`; any "
                "other ternary was almost certainly if/else in PS."),
    "nested-ternary": ([],
                       "no rule reproduces a nested ternary — unfold to "
                       "if/else (style: never in the corpus)."),
    "switch": (["95"],
               "Rule 95: a switch is a distinct jump-table dispatch. If the "
               "PS asm shows no jump table, the original was an if/else-if "
               "chain, not a switch."),
    "goto": (["92"],
             "Rule 92: goto is PS-shaped as an epilogue funnel (`goto fail`); "
             "a dense goto web is suspect."),
    "ptr-cache": (["63"],
                  "Rule 63: PS recomputes the index and folds `global+field` "
                  "into a disp32 operand. Inline the cached pointer at its "
                  "(few) use sites."),
    "many-locals>=10": (["116"],
                        "Rule 116: extra readable temporaries that cache a "
                        "memory value spill and add callee-saves. Inline the "
                        "memory-rooted temps; reuse one local for double-duty."),
    "shl1": (["62"],
             "Rule 62: `x << 1` → `mov;add`; `x + x` → `lea [x+x]` (1 byte "
             "shorter, cascades through short jumps). Match the PS form."),
    "compound-assign": (["91"],
                        "Rule 91: compound `op=` on a computed-address lvalue "
                        "is an in-place RMW and is NOT equivalent to the "
                        "expanded `lhs = lhs op rhs`. Usually correct — low "
                        "lift."),
    "do-while": (["93"],
                 "Rule 93: do/while = test-at-bottom (no entry jump). Neutral "
                 "on its own; match PS's loop-test placement."),
    "cast": (["49"],
             "Rule 49: width/sign casts pick the zext idiom and the addressing "
             "mode. Keep only the casts PS's loads imply."),
    "comma-for-incr": (["79"],
                       "Rule 79: comma `for`-increment is house style and "
                       "governs increment ordering. Neutral."),
    "assign-in-if": ([],
                     "no rule — assignment inside `if` is not observed in the "
                     "corpus (assign-in-`while` IS house style). Split it out."),
    "register": ([],
                 "`register` is a Watcom 10.0a no-op and never appears in the "
                 "corpus. Remove it (style, not codegen)."),
    "while1": ([],
               "`while (1)` ≡ `for (;;)` — codegen-neutral noise."),
    "multi-return": ([],
                     "multiple returns are common and usually fine — low lift."),
    "deep-nest>=4": ([],
                     "deep nesting is mostly a size proxy (low size-controlled "
                     "lift); not an anti-rule by itself."),
}


def feature_rules(feature: str) -> tuple[list[str], str]:
    return FEATURE_RULES.get(feature, ([], ""))


# ── residue-cluster side: classify a family's rule-hint coverage ──────────────

# Hints that are generic register-allocation *classifiers*, not numbered rules
# with a prescribed source fix — a family whose ONLY coverage is these has no
# catalogue explanation yet.
GENERIC_HINTS = frozenset({"Reg swap", "Byte-reg swap", "Add/LEA copy"})


def classify_family_coverage(hint_names: set[str]) -> tuple[str, list[str]]:
    """Return ``(verdict, known_rules)``.

    verdict ∈ {'known', 'partial', 'novel'}:
      * known   — a numbered rule covers the family (a prescribed source fix
                  exists; this is a *known anti-rule family*).
      * partial — numbered rule(s) present alongside generic classifiers.
      * novel   — only generic register-swap classifiers (or nothing) →
                  no catalogue explanation → **novel anti-rule candidate**.
    """
    numbered = sorted(
        {h.replace("Rule ", "") for h in hint_names
         if h.startswith("Rule ")},
        key=lambda s: (len(s), s),
    )
    generic = {h for h in hint_names if h in GENERIC_HINTS}
    if numbered and not generic:
        return "known", numbered
    if numbered and generic:
        return "partial", numbered
    return "novel", []
