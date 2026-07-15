"""Parsing tests for the gb / tg trace records and given_before derivation."""
from c2.regalloc.trace import parse


def _trace():
    return (
        "~WV1 fb\n"
        "~WV1 fn\n"
        # conflict 10 (name 100): al, bt, tg sweep, gb sweep, rg pick
        "~WV1 al 10 100 5 f 0 0 2 1\n"
        "~WV1 tg 10 1000003 0\n"        # EAX passes TooGreedy
        "~WV1 gb 10 1000003 0\n"
        "~WV1 tg 10 80000c0 1\n"        # EDX vetoed by TooGreedy
        "~WV1 gb 10 200000c 4\n"        # EBX scored 4 (no tg line forged)
        "~WV1 rg 10 200000c\n"          # pick EBX
        # conflict 20: second sweep -- given_before must contain EBX
        "~WV1 al 20 200 3 f 0 0 2 2\n"
        "~WV1 gb 20 4000030 0\n"
        "~WV1 rg 20 4000030\n"          # pick ECX
        "~WV1 fc 99 0 0\n"
    )


def test_gb_tg_and_given_before():
    td = parse(_trace())
    r = td["routines"][0]
    a1, a2 = r["alloc"][0], r["alloc"][1]
    assert a1["cand_scores"] == [{"cand": "EAX", "saves": 0},
                                 {"cand": "EBX", "saves": 4}]
    assert a1["tg_veto"] == ["EDX"]
    assert a1["given_before"] == 0          # first pick: nothing given yet
    assert a2["given_before"] == 0x200000c  # EBX from conflict 10
    # raw stream preserved for multi-pass analysis
    assert {g["conf"] for g in r["gb"]} == {"10", "20"}


def test_gb_signed_saves():
    td = parse("~WV1 fb\n~WV1 fn\n"
               "~WV1 al 10 100 5 f 0 0 2 1\n"
               "~WV1 gb 10 1000003 ffffffff\n"
               "~WV1 fc 99 0 0\n")
    a = td["routines"][0]["alloc"][0]
    assert a["cand_scores"][0]["saves"] == -1


def test_wr_ins_range_extension():
    td = parse("~WV1 fb\n~WV1 fn\n"
               "~WV1 al 10 100 5 f 0 0 2 1\n"
               "~WV1 wr 10 4000f800 99430 99240\n"
               "~WV1 rg 10 1000003\n"
               "~WV1 al 20 200 3 f 0 0 2 2\n"
               "~WV1 wr 20 4000f802\n"          # old 2-field form: no range
               "~WV1 rg 20 80000c0\n"
               "~WV1 fc 99 0 0\n")
    r = td["routines"][0]
    assert r["alloc"][0]["withregs"] == 0x4000f800
    assert r["alloc"][0]["ins_range"] == ("99430", "99240")
    assert r["alloc"][1]["ins_range"] is None


def test_bt_state_idbits_extension():
    td = parse("~WV1 fb\n~WV1 fn\n"
               "~WV1 al 10 100 5 f 0 0 2 1\n"
               "~WV1 bt 10 99 88 1000003 0 0 0 0 0 0 0 f000c 0 0\n"
               "~WV1 rg 10 1000003\n"
               "~WV1 al 20 200 3 f 0 0 2 2\n"
               "~WV1 bt 20 99 88 1000003 0 0 0 0 0 0 0 f0008 4 0\n"
               "~WV1 rg 20 80000c0\n"
               "~WV1 fc 99 0 0\n")
    a1, a2 = td["routines"][0]["alloc"]
    assert a1["on_hold"] is True and a1["no_id_bits"] is True
    assert a2["on_hold"] is False and a2["no_id_bits"] is False
    assert a2["id_bits"] == (4, 0)


def test_ob_oh_prefb_buffering():
    # ob/oh fire in AssignGlobalBits (MakeConflicts) BEFORE the routine's
    # fb -- they must buffer and attach to the NEXT routine, like cn.
    txt = "\n".join([
        "~WV1 ob aa111 bb111 2 1 0 0 0",
        "~WV1 ob aa222 bb222 2 2 0 0 0",
        "~WV1 oh aa333 bb333",
        "~WV1 fb",
        "~WV1 ob aa444 bb444 1 4 0 0 0",   # in-routine (MoreConflicts round)
        "~WV1 fn",
    ])
    from c2.regalloc.trace import parse
    rts = parse(txt)["routines"]
    r = rts[0]
    assert [o["conf"] for o in r["ob"]] == ["aa111", "aa222", "aa444"]
    assert r["ob"][0]["bits"] == (1, 0, 0, 0)
    assert r["ob"][2]["class"] == 1
    assert r["oh"] == [{"conf": "aa333", "name": "bb333"}]


def test_rq_parses_as_alloc_row():
    txt = "\n".join([
        "~WV1 fb",
        "~WV1 rq cc111 1000003",
        "~WV1 fn",
    ])
    from c2.regalloc.trace import parse
    r = parse(txt)["routines"][0]
    rows = [a for a in r["alloc"] if a.get("source") == "rq"]
    assert len(rows) == 1
    assert rows[0]["conf"] == "cc111" and rows[0]["reg_name"] == "EAX"


def test_lc_merge_back_records():
    txt = "\n".join([
        "~WV1 fb",
        "~WV1 fr aa111 5 41fff803 1 bb111 0",
        "~WV1 lc aa111 0 cc222",
        "~WV1 lc dd333 ee444 ff555",
        "~WV1 fn",
    ])
    from c2.regalloc.trace import parse
    r = parse(txt)["routines"][0]
    assert r["lc"] == [
        {"ins": "aa111", "presult": False, "popnd": True},
        {"ins": "dd333", "presult": True, "popnd": True},
    ]


def test_opt_rl_cm_records():
    txt = "\n".join([
        "~WV1 opt 50 40100000 8b0 a4",
        "~WV1 fb",
        "~WV1 cm 0 517",
        "~WV1 cm 10 517",
        "~WV1 rl 2",
        "~WV1 cm 1 1536",
        "~WV1 fc 99 0 0",
    ])
    from c2.regalloc.trace import parse
    td = parse(txt)
    assert td["opt"] == {"opt_for_size": 50, "flags1": "40100000",
                         "flags2": "8b0", "target": "a4"}
    r = td["routines"][0]
    assert r["retlists"] == [2]
    assert r["comtail"] == [{"save": 0, "raw20": 517},
                            {"save": 10, "raw20": 517},
                            {"save": 1, "raw20": 1536}]


def test_opt_absent_is_none():
    from c2.regalloc.trace import parse
    assert parse("~WV1 fb\n~WV1 fn\n")["opt"] is None


def test_oc_events_stream():
    """The unit-global OC-queue tail-merge stream: trace order preserved,
    header word decoded (incl. b2 = comparator raw-compare length), w10/w14
    captured, seq joins, cross-function merge keep-first commit captured
    (the devolve/evolve goto-form JustMoveLabel), emit ledger + splice
    births (em/nl/nj)."""
    txt = "\n".join([
        "~WV1 fb",
        "~WV1 op a45ac 83060203 99c8c 19",   # add esp,4 (cls 2, objlen 3)
        "~WV1 op a45c4 c0600 9a22c 19",      # label (cls 6, objlen 0)
        "~WV1 op a4564 c4e03 0 4",           # ret 4 (cls 0xe, attr 0x40)
        "~WV1 fc 1 0 0",
        "~WV1 fb",
        "~WV1 op a2b64 c4e03 0 4",           # evolve's ret
        "~WV1 fw a4564 a2b64 a45ac a2bac 8",  # FindCommon: save=8 (epilogue)
        "~WV1 jm a2bc4 a45ac a2bac 8 a2b64",  # JustMoveLabel commit
        "~WV1 ct a4d7c a55b8 a5220 a4dac 10",  # a splice commit...
        "~WV1 nl a5160 a55a0",                 # ...births its merge label
        "~WV1 nj a4dc4 a5160",                 # ...and its back-jump
        "~WV1 fc 2 0 0",
        "~WV1 fq",                            # drain boundary
        "~WV1 sc 9967c 99e78",                # front-side StraightenCode
        "~WV1 em a45c4 60600",                # emit ledger: final order/len
    ])
    from c2.regalloc.trace import parse
    ev = parse(txt)["oc_events"]
    tags = [e["tag"] for e in ev]
    assert tags == ["op", "op", "op", "op", "fw", "jm", "ct", "nl", "nj",
                    "fq", "sc", "em"]
    # header decode + w10/w14
    add_esp = next(e for e in ev if e["tag"] == "op" and e["entry"] == "a45ac")
    assert add_esp["cls"] == 0x2 and add_esp["objlen"] == 3
    assert add_esp["b2"] == 0x06 and add_esp["hdr"] == "83060203"
    assert add_esp["w10"] == "99c8c" and add_esp["w14"] == "19"
    lbl = next(e for e in ev if e["tag"] == "op" and e["entry"] == "a45c4")
    assert lbl["cls"] == 0x6
    ret = next(e for e in ev if e["tag"] == "op" and e["entry"] == "a4564")
    assert ret["cls"] == 0xe and ret["attr"] == 0x40
    # seq: monotonic, in trace order (fb consumed seq 0)
    seqs = [e["seq"] for e in ev]
    assert seqs == sorted(seqs) and seqs[0] == 1
    # the cross-function FindCommon result + commit
    fw = next(e for e in ev if e["tag"] == "fw")
    assert (fw["cand"], fw["ins"], fw["old"], fw["new"], fw["save"]) == \
        ("a4564", "a2b64", "a45ac", "a2bac", 8)
    jm = next(e for e in ev if e["tag"] == "jm")
    assert jm["save"] == 8 and jm["label"] == "a2bc4" and jm["ins"] == "a2b64"
    # splice trio: ct -> nl (label birth) -> nj (back-jump, 1:1 with ct)
    ct = next(e for e in ev if e["tag"] == "ct")
    nl = next(e for e in ev if e["tag"] == "nl")
    nj = next(e for e in ev if e["tag"] == "nj")
    assert ct["save"] == 10 and nl["label"] == "a5160" == nj["label"]
    # emit ledger decodes like op
    em = next(e for e in ev if e["tag"] == "em")
    assert em["entry"] == "a45c4" and em["cls"] == 6 and em["objlen"] == 0
    # op records carry their routine index (rtn)
    assert ret["rtn"] == 0
    assert next(e for e in ev if e.get("entry") == "a2b64")["rtn"] == 1


def test_oc_events_op_old_format_back_compat():
    """v19-era traces (op with only entry+hdr8) still parse; w10/w14 None."""
    from c2.regalloc.trace import parse
    ev = parse("~WV1 fb\n~WV1 op a45ac 83060203\n")["oc_events"]
    assert ev[0]["cls"] == 2 and ev[0]["w10"] is None and ev[0]["w14"] is None


def test_oc_events_empty_when_absent():
    from c2.regalloc.trace import parse
    assert parse("~WV1 fb\n~WV1 fn\n")["oc_events"] == []


# ── wp records + memory-exile classification (2026-06-13, v29) ───────────

def test_wp_attaches_to_open_presentation():
    td = parse("~WV1 fb\n~WV1 fn\n"
               "~WV1 al 10 100 5 f 0 0 2 1\n"
               "~WV1 bt 10 0 0 1000003 200000c 0 0 0 0 0 0 0 0 1 0\n"
               "~WV1 gb 10 200000c 4\n"
               "~WV1 wp 6 2\n"
               "~WV1 rg 10 200000c\n"
               "~WV1 fc 99 0 0\n")
    a = td["routines"][0]["alloc"][0]
    assert a["wp"] == [{"budget": 6, "cost": 2, "ok": True}]
    assert "memory_exiled" not in a          # committed -> not exiled


def test_wp_decline_marks_memory_exile():
    td = parse("~WV1 fb\n~WV1 fn\n"
               "~WV1 al 10 100 5 f 0 0 2 1\n"
               "~WV1 bt 10 0 0 1000003 200000c 0 0 0 0 0 0 0 0 1 0\n"
               "~WV1 gb 10 200000c 4\n"
               "~WV1 wp 1 2\n"               # budget 1 < cost 2: declined
               "~WV1 fc 99 0 0\n")
    a = td["routines"][0]["alloc"][0]
    assert a["wp"] == [{"budget": 1, "cost": 2, "ok": False}]
    assert a["memory_exiled"] == "worthprolog"


def test_masked_exile_bt_without_gb():
    # load_map_graphics `ret` class: bt fires, every candidate is
    # with.regs/except-masked (no tg/gb at all), no commit -> memory.
    td = parse("~WV1 fb\n~WV1 fn\n"
               "~WV1 al 10 100 5 f 0 0 2 1\n"
               "~WV1 bt 10 0 0 1000003 200000c 0 0 0 0 0 0 0 0 1 0\n"
               "~WV1 al 20 200 9 f 0 0 2 1\n"
               "~WV1 fc 99 0 0\n")
    a = td["routines"][0]["alloc"][0]
    assert a["memory_exiled"] == "masked"


def test_wp_windowed_to_own_birth():
    # the wp of conflict 20's presentation must NOT leak onto conflict 10
    td = parse("~WV1 fb\n~WV1 fn\n"
               "~WV1 al 10 100 5 f 0 0 2 1\n"
               "~WV1 bt 10 0 0 1000003 0 0 0 0 0 0 0 0 0 1 0\n"
               "~WV1 gb 10 1000003 4\n"
               "~WV1 rg 10 1000003\n"
               "~WV1 al 20 200 9 f 0 0 2 1\n"
               "~WV1 bt 20 0 0 1000003 200000c 0 0 0 0 0 0 0 0 1 0\n"
               "~WV1 gb 20 200000c 4\n"
               "~WV1 wp 1 9\n"
               "~WV1 fc 99 0 0\n")
    r = td["routines"][0]
    a10, a20 = r["alloc"][0], r["alloc"][1]
    assert "wp" not in a10 or not a10.get("wp")
    assert a20["wp"] == [{"budget": 1, "cost": 9, "ok": False}]
    assert a20["memory_exiled"] == "worthprolog"
    assert "memory_exiled" not in a10
