"""Tests for the residue-cluster tool (c2/commands/residue_cluster.py).

build_model takes a verify-JSON doc directly, so these are pure unit tests
(no Watcom container, no source dependency).
"""

from c2.commands.residue_cluster import (
    signature, _shape, _mag, build_model,
)


def _fn(name, *, diff=10, size=300, rules=None, rows=None,
        tail=False, pragma=None, size_differs=False):
    return {
        "name": name, "diff_byte_count": diff, "size": size,
        "rule_hints": rules or {}, "rows": rows or [],
        "tail_merge": ({"donor_name": "d"} if tail else None),
        "pragma_hint": ({"category": pragma} if pragma else None),
        "size_differs": size_differs,
    }


def _rows(ins=0, de=0, rep=0):
    return ([{"kind": "insert"}] * ins + [{"kind": "delete"}] * de
            + [{"kind": "replace"}] * rep)


# ── helpers ──────────────────────────────────────────────────────────────────

def test_shape_aligned():
    assert _shape(_rows(rep=10)) == "aligned"


def test_shape_cascade():
    assert _shape(_rows(ins=8, de=8, rep=1)) == "cascade"


def test_shape_mixed():
    assert _shape(_rows(ins=2, de=1, rep=7)) == "mixed"


def test_mag_buckets():
    assert _mag(2) == "tiny"
    assert _mag(10) == "small"
    assert _mag(40) == "med"
    assert _mag(200) == "large"


def test_signature_includes_rule_hints_and_flags():
    fn = _fn("x", rules={"Rule 16": 3}, tail=True, rows=_rows(rep=4))
    sig = signature(fn)
    assert sig["hint:Rule 16"] == 1
    assert sig["tailmerge"] == 1
    assert "shape:aligned" in sig


# ── clustering ────────────────────────────────────────────────────────────────

def test_only_diffing_functions_clustered():
    doc = {"functions": [
        _fn("a", diff=5, rules={"Reg swap": 1}, rows=_rows(rep=3)),
        _fn("exact", diff=0),
    ]}
    m = build_model(doc)
    assert "exact" not in m.sig
    assert "a" in m.sig


def test_similar_functions_cluster_together():
    # Three functions with the same Rule-16 cascade signature should land in
    # one family; a distinct tiny-aligned reg-swap function should not.
    doc = {"functions": [
        _fn("c1", diff=80, size=600, rules={"Rule 16": 4, "Reg swap": 1},
            rows=_rows(ins=10, de=10, rep=2), size_differs=True),
        _fn("c2", diff=90, size=620, rules={"Rule 16": 5, "Reg swap": 1},
            rows=_rows(ins=12, de=11, rep=2), size_differs=True),
        _fn("c3", diff=70, size=580, rules={"Rule 16": 3, "Reg swap": 1},
            rows=_rows(ins=9, de=9, rep=1), size_differs=True),
        _fn("odd", diff=2, size=100, rules={"Reg swap": 1},
            rows=_rows(rep=2)),
    ]}
    m = build_model(doc, threshold=0.6)
    c_rule16 = m.cluster_of("c1")
    assert {"c1", "c2", "c3"} <= set(c_rule16.members)
    assert "odd" not in c_rule16.members


def test_known_vs_novel_coverage():
    doc = {"functions": [
        # A rule-16 family → KNOWN coverage.
        _fn("k1", rules={"Rule 16": 3}, rows=_rows(ins=5, de=5, rep=1)),
        _fn("k2", rules={"Rule 16": 2}, rows=_rows(ins=5, de=5, rep=1)),
        # A reg-swap-only family → NOVEL coverage.
        _fn("n1", diff=3, rules={"Reg swap": 1}, rows=_rows(rep=2)),
        _fn("n2", diff=4, rules={"Reg swap": 1}, rows=_rows(rep=2)),
    ]}
    m = build_model(doc, threshold=0.6)
    ck = m.cluster_of("k1")
    cn = m.cluster_of("n1")
    assert ck.coverage in ("known", "partial")
    assert "16" in ck.known_rules
    assert cn.coverage == "novel"
    assert cn.known_rules == []


def test_representative_is_smallest_diff():
    doc = {"functions": [
        _fn("big", diff=50, rules={"Reg swap": 1}, rows=_rows(rep=20)),
        _fn("small", diff=3, rules={"Reg swap": 1}, rows=_rows(rep=2)),
    ]}
    m = build_model(doc, threshold=0.5)
    c = m.cluster_of("small")
    assert c.rep == "small"


def test_cluster_json_shape():
    doc = {"functions": [_fn("a", rules={"Rule 16": 1},
                             rows=_rows(ins=4, de=4, rep=1))]}
    m = build_model(doc)
    from c2.commands.residue_cluster import _cluster_json
    j = _cluster_json(m.clusters[0], m)
    assert set(j) >= {"cid", "size", "coverage", "known_rules",
                      "representative", "members"}
    assert j["members"][0]["name"] == "a"
