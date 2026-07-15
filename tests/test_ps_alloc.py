"""PS-alloc verdict tests: rover-pair deferral + tie transport basics."""
from types import SimpleNamespace

from c2.commands import ps_alloc


def _hint(summary):
    return SimpleNamespace(rule="Reg swap", summary=summary, fix="")


def _routine():
    """Synthetic routine: two tied s4010 conflicts (EBX/ECX) + filler.

    presort is the REVERSED creation order (ConfList is a LIFO of cn)."""
    alloc = [
        {"conf": "a1", "var": "p", "savings": 4070, "reg_name": "EAX",
         "regclass_name": "dword", "defline": 10, "last": "i1", "ins_walk": []},
        {"conf": "b1", "var": "buf_idx", "savings": 4010, "reg_name": "EBX",
         "regclass_name": "dword", "defline": 20, "last": "i9", "ins_walk": []},
        {"conf": "c1", "var": "x_count", "savings": 4010, "reg_name": "ECX",
         "regclass_name": "dword", "defline": 21, "last": "i9", "ins_walk": []},
    ]
    confs = [{"conf": "a1"}, {"conf": "c1"}, {"conf": "b1"}]
    presort = [{"node": "b1", "savings": 4010},
               {"node": "c1", "savings": 4010},
               {"node": "a1", "savings": 4070}]
    return {"alloc": alloc, "confs": confs, "presort": presort,
            "src_file": None}


def _patch_lookup(monkeypatch, routine):
    from c2.commands import regalloc_hints
    monkeypatch.setattr(regalloc_hints, "_lookup",
                        lambda func, file: (routine, {}, 10))


def test_rover_pair_defers(monkeypatch):
    _patch_lookup(monkeypatch, _routine())
    hints = [_hint("register identity swap (ebx\u2194ecx)")]
    v = ps_alloc.detect("f", hints, rows=None,
                        rover_pairs={frozenset(("EBX", "ECX"))})
    assert v is not None
    txt = "\n".join(v.lines)
    assert "DEFER to the Rover lever" in txt
    assert "REACHABLE" not in txt


def test_no_rover_pair_still_analyses(monkeypatch):
    _patch_lookup(monkeypatch, _routine())
    hints = [_hint("register identity swap (ebx\u2194ecx)")]
    v = ps_alloc.detect("f", hints, rows=None, rover_pairs=set())
    assert v is not None
    txt = "\n".join(v.lines)
    assert "DEFER" not in txt
    # the synthetic tie is analysed (verdict wording may vary)
    assert "tie s4010" in txt or "MODEL-MISMATCH" in txt
