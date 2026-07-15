"""Offline allocator replay (c2.regalloc.replay) -- corpus-certified
2026-06-12: sort 1228/1228 routines, selection 19116/19116 allocations."""
import json
from pathlib import Path

import pytest

from c2.regalloc import replay

_CACHE = Path(".c2-cache/build/regtrace.json")


def test_split_rounds():
    seq = [{"node": "a"}, {"node": "b"}, {"node": "a"}, {"node": "c"}]
    r = replay.split_rounds(seq)
    assert [[x["node"] for x in rd] for rd in r] == [["a", "b"], ["a", "c"]]


def test_select_register_rule():
    # argmax wins outright
    assert replay.select_register(
        [{"cand": "EAX", "saves": 0}, {"cand": "EDX", "saves": 4}], 0) == "EDX"
    # tie -> GivenRegisters subset (EDX given, EAX not)
    assert replay.select_register(
        [{"cand": "EAX", "saves": 0}, {"cand": "EDX", "saves": 0}],
        replay.REG_ENC["EDX"]) == "EDX"
    # tie, nothing given -> list order
    assert replay.select_register(
        [{"cand": "EBX", "saves": 0}, {"cand": "ECX", "saves": 0}], 0) == "EBX"


def test_whatif_swap_moves_tie_group():
    pres = [{"node": "a", "savings": 3}, {"node": "b", "savings": 3},
            {"node": "c", "savings": 9}]
    base = [x["node"] for x in replay.replay_sort(pres)]
    what = [x["node"] for x in replay.whatif_swap(pres, 0, 1)]
    assert base[0] == what[0] == "c"          # savings order intact
    assert base[1:] == ["a", "b"] and what[1:] == ["b", "a"]


@pytest.mark.skipif(not _CACHE.exists(), reason="build trace cache absent")
def test_corpus_certification():
    data = json.loads(_CACHE.read_text())
    s_tot = s_ok = p_tot = p_ok = 0
    for r in data.get("by_func", {}).values():
        v = replay.validate_routine(r)
        if v["sort_ok"] is not None:
            s_tot += 1
            s_ok += v["sort_ok"]
        p_tot += v["picks_total"]
        p_ok += v["picks_ok"]
    assert s_tot and s_ok == s_tot, f"sort replay regressed: {s_ok}/{s_tot}"
    assert p_tot and p_ok == p_tot, f"selection rule regressed: {p_ok}/{p_tot}"


def test_crm10a_mov_and_2address():
    row = {"name": "a", "ins_walk": [
        # MOV V -> (reg EAX result): full credit 4
        {"opcode": 0x26, "result": 99, "result_reg": 0x1000003,
         "op0": 0xa, "op0_reg": 0, "op1": 0, "op1_reg": 0},
        # ANY 2-address op (opcode 0xc) op0=V, result bound EAX: half 2
        {"opcode": 0x0c, "result": 98, "result_reg": 0x1000003,
         "op0": 0xa, "op0_reg": 0, "op1": 0, "op1_reg": 0},
    ]}
    assert replay.crm10a(row, replay.REG_ENC["EAX"]) == 6
    assert replay.crm10a(row, replay.REG_ENC["EDX"]) == 0


@pytest.mark.skipif(not _CACHE.exists(), reason="build trace cache absent")
def test_cascade_identity_gates():
    """Corpus gates 2026-06-12: mask reconstruction must stay EXACT;
    identity pick replay and the per-routine trust gate must not regress."""
    data = json.loads(_CACHE.read_text())
    m_tot = m_ok = p_tot = p_ok = f_tot = f_ok = 0
    for r in data.get("by_func", {}).values():
        rows = replay.replay_rows(r.get("alloc") or [])
        if not rows:
            continue
        graph = replay.build_graph(rows)
        for i, b in enumerate(rows):
            mask = graph[i]["baseline"]
            for n in graph[i]["neighbors"]:
                if n < i and n not in graph[i]["excepted"]:
                    mask |= replay.REG_ENC[rows[n]["reg_name"]]
            m_tot += 1
            m_ok += (mask == b["withregs"])
        res = replay.replay_order(rows, list(range(len(rows))), graph)
        good = sum(x["pick"] == x["identity"] for x in res)
        p_tot += len(res)
        p_ok += good
        f_tot += 1
        f_ok += (good == len(res))
    assert m_ok == m_tot, f"mask reconstruction regressed: {m_ok}/{m_tot}"
    assert p_ok / p_tot >= 0.95, f"identity replay regressed: {p_ok}/{p_tot}"
    assert f_ok / f_tot >= 0.70, f"routine gate regressed: {f_ok}/{f_tot}"
