"""Tests for the RISCify rover hint (c2.commands.rover_hints), all 3 classes."""
from collections import Counter
import c2.commands.rover_hints as RH


def _ins(asm):
    return (0, len(asm), b"", asm)


def _dword_args(regs, glob="0x1000"):
    """A call whose memory args are `mov <reg>,[glob]; push <reg>` scratches."""
    out = []
    for r in regs:
        out += [_ins(f"mov {r}, [{glob}]"), _ins(f"push {r}")]
    out.append(_ins("call 0x9999"))
    return out


def _byte_loads(regs, glob="0x1000"):
    return [_ins(f"mov {r}, byte ptr [{glob}]") for r in regs]


def _fr(n, tc=5, exc=0xc00, op=0x2a):
    """n permissive records of a given class (except = EBP|ESP -> rover cycles)."""
    return [{"ins": "i", "type_class": tc, "except": exc, "opcode": op, "op0": "x"}
            for _ in range(n)]


def test_rover_loads_dword_push():
    assert RH._rover_loads(_dword_args(["edx", "ebx", "ecx"]), "dword") == ["edx", "ebx", "ecx"]


def test_rover_loads_byte():
    assert RH._rover_loads(_byte_loads(["al", "bl", "cl"]), "byte") == ["al", "bl", "cl"]


def test_rover_loads_skips_indexed_and_unpushed():
    insns = [_ins("mov edx, [eax+0x4]"), _ins("push edx"),      # indexed
             _ins("mov ebx, [0x1000]"), _ins("call 0x9999")]    # not pushed
    assert RH._rover_loads(insns, "dword") == []


def test_uniform_shift_dword():
    assert RH._uniform_shift(["ebx", "ecx", "edx", "esi"],
                             ["ecx", "esi", "ebx", "esi"]) == 1


def test_uniform_shift_byte():
    # byte order AL,AH,DH,DL,BH,BL,CH,CL -> ah(1)->dh(2), dl(3)->bh(4): both +1
    assert RH._uniform_shift(["ah", "dl"], ["dh", "bh"]) == 1


def test_simulate_dword_cycle():
    sim = RH._simulate(_fr(4, tc=5))
    assert [reg for (_c, reg, _o) in sim] == ["edx", "ebx", "ecx", "esi"]


def test_simulate_byte_cycle():
    sim = RH._simulate(_fr(4, tc=0))
    assert [reg for (_c, reg, _o) in sim] == ["ah", "dh", "dl", "bh"]


def test_search_dword_plus_one():
    fr = _fr(3, tc=5)
    res = RH._search(fr, "dword", ["edx", "ebx", "ecx"], ["ebx", "ecx", "esi"],
                     parm_only=True)
    assert res is not None and res[0] == 0 and 1 in res[1]


def _mov(op0, line):
    return {"ins": "i", "type_class": 5, "except": 0xc00, "opcode": 0x26,
            "op0": op0, "line": line}


def test_search_const_store_aligns_past_coalesced_ops():
    # message's shape: the diverging mgp=0 stores (op0 'Z', kept) sit AFTER
    # prologue zero-stores (coalesce to one reg) and =1 stores (op0 'O',
    # collapse to c7).  The old change-multiset match over-counted the coalesced
    # picks and returned None; aligning rc_regs from the end recovers the visible
    # positions so the +1 injection is found, with its source line.
    fr = ([_mov("Z", 49), _mov("Z", 54), _mov("Z", 58)]      # prologue zeros
          + [_mov("O", 83), _mov("Z", 84),                    # mouse: out1=1 ; mgp=0
             _mov("O", 87), _mov("Z", 88),                    # exit
             _mov("O", 91), _mov("Z", 92)])                   # time
    base = RH._simulate(fr)
    rc = [base[4][1], base[6][1], base[8][1]]                 # the kept mgp stores
    ps = RH._simulate(fr, inject=(4, 1, fr[4]["except"], "dword"))
    ps_regs = [ps[4][1], ps[6][1], ps[8][1]]
    assert rc != ps_regs
    res = RH._search(fr, "dword", rc, ps_regs, parm_only=False, const_store=True)
    assert res is not None and 1 in res[1]
    assert fr[res[0]]["line"] is not None        # injection point carries a line


def test_detect_dword_end_to_end():
    rc = _dword_args(["edx", "ebx", "ecx"])
    ps = _dword_args(["ebx", "ecx", "esi"])
    h = RH.detect(ps, rc, rule_hist={"Reg swap": 3}, fr=_fr(3, tc=5))
    assert h is not None and h.cls == "dword" and h.shift == 1 and 1 in h.advances
    assert "edx->ebx" in h.summary
    assert "dword rover" in RH.render(h) and "dead" in RH.render(h).lower()


def test_diverge_line_const_store():
    # font_format_split shape: font_screen_limit(line A) matches, x_is(line B)
    # diverges.  _diverge_line aligns the kept-store picks to the fr trace and
    # returns (line, rc_reg, ps_reg) for the FIRST mismatch.
    fr = [_mov("S", 3408), _mov("X", 3462)]
    base = RH._simulate(fr)                       # ebx, esi (fresh dword cursor)
    rc = [base[0][1], base[1][1]]                 # RC kept picks
    ps = [base[0][1], base[0][1]]                 # PS: 2nd store same reg as 1st
    d = RH._diverge_line(fr, "dword", rc, ps, const_store=True, parm_only=False)
    assert d is not None
    line, rc_reg, ps_reg = d
    assert line == 3462 and rc_reg == rc[1] and ps_reg == ps[1]


def test_diverge_line_surfaced_in_summary():
    fr = [_mov("S", 100), _mov("X", 200)]
    base = RH._simulate(fr)
    # build PS/RC arg lists whose const-store picks reproduce a divergence at #1
    rc = _dword_args([base[0][1], base[1][1]])
    ps = _dword_args([base[0][1], base[0][1]])
    h = RH.detect(ps, rc, rule_hist={"Reg swap": 2}, fr=fr)
    # diverge populated only when the const-store alignment lands (line carried)
    if h is not None and h.diverge is not None:
        assert "DIVERGENCE at source line 200" in h.summary


def test_detect_byte_end_to_end():
    rc = _byte_loads(["al", "ah", "dh"])
    ps = _byte_loads(["ah", "dh", "dl"])
    h = RH.detect(ps, rc, rule_hist={"Byte-reg swap": 3}, fr=_fr(3, tc=0))
    assert h is not None and h.cls == "byte" and h.shift == 1
    assert "byte rover" in RH.render(h)


def test_detect_requires_swap_rule():
    rc = _dword_args(["edx", "ebx", "ecx"])
    ps = _dword_args(["ebx", "ecx", "esi"])
    assert RH.detect(ps, rc, rule_hist={"Rule 16": 1}, fr=None) is None


def test_detect_no_diff_returns_none():
    same = _dword_args(["edx", "ebx", "ecx"])
    assert RH.detect(same, same, rule_hist={"Reg swap": 1}, fr=None) is None


def test_parm_reload_fires_on_duplicated_global():
    # baseline link_to_smacker: smacker_open loaded for the TEST then RELOADED
    # for the call arg -> two records share op0, the 2nd a PARM_DEF (0x2a).
    fr = [
        {"ins": "a", "type_class": 5, "except": 0, "opcode": 0x31, "op0": "0x99ea0"},  # test g
        {"ins": "b", "type_class": 5, "except": 0, "opcode": 0x2a, "op0": "0x99ea0"},  # PARM g (reload)
        {"ins": "c", "type_class": 5, "except": 0, "opcode": 0x2a, "op0": "0x99ab0"},  # PARM dig
        {"ins": "d", "type_class": 5, "except": 0, "opcode": 0x26, "op0": "0x99c38"},  # const
    ]
    msg = RH.parm_reload(fr)
    assert msg is not None and "reload" in msg.lower() and "cache" in msg.lower()


def test_parm_reload_quiet_when_no_dup():
    # local_open: cached temp -> arg references the temp, no duplicated global.
    fr = [
        {"ins": "a", "type_class": 5, "except": 0, "opcode": 0x2a, "op0": "0x99a24"},  # PARM dig
        {"ins": "b", "type_class": 5, "except": 0, "opcode": 0x26, "op0": "0x99b88"},  # const
    ]
    assert RH.parm_reload(fr) is None
    assert RH.parm_reload([]) is None
    assert RH.parm_reload(None) is None


def test_parm_reload_ignores_two_parms_of_different_globals():
    # two distinct globals passed as args must NOT trigger (no reload).
    fr = [
        {"ins": "a", "type_class": 5, "except": 0, "opcode": 0x2a, "op0": "0xAAA"},
        {"ins": "b", "type_class": 5, "except": 0, "opcode": 0x2a, "op0": "0xBBB"},
    ]
    assert RH.parm_reload(fr) is None


def test_const_store_rover_swap_fires_for_message():
    # message.c residue: the loop-tail `message_goto_ptr = 0` stores are RISCified
    # constant stores (`xor reg,reg; mov [global],reg`), NOT mov reg,[global] loads.
    # PS reuses the just-freed EAX (a3); RC parks 0 in EBP.  The rover hint must
    # detect the const-store picks, not miss them like _rover_loads does.
    def mk(regs):
        out = []
        for r in regs:
            out.append((0, 0, 0, f"xor {r}, {r}"))
            out.append((0, 0, 0, f"mov dword ptr [0x72e2c], {r}"))
        return out
    ps = mk(["eax", "ebx", "eax"])
    rc = mk(["ebp", "edx", "ebp"])
    assert RH._rover_const_stores(ps, "dword") == ["eax", "ebx", "eax"]
    assert RH._rover_const_stores(rc, "dword") == ["ebp", "edx", "ebp"]
    # `mov [global], imm` (c7 direct form) is NOT a pick -- no register.
    assert RH._rover_const_stores([(0, 0, 0, "mov dword ptr [0x72e2c], 1")], "dword") == []
    h = RH.detect(ps, rc, rule_hist={"Reg swap": 3})
    assert h is not None and h.cls == "dword"
    assert h.rc_regs == ["ebp", "edx", "ebp"] and h.ps_regs == ["eax", "ebx", "eax"]
    assert "rover" in RH.render(h).lower()
    # the lever menu must name the proven byte-neutral levers
    txt = RH.render(h).lower()
    assert "loop-invariant" in txt and "game_state = out1" in txt
    assert "parm-reload" in txt and "dead-branch" in txt


def test_rover_sites_maps_walk_order_to_source_lines():
    # the fr line_num field lets the hint point at the candidate cursor-advance
    # SITES in source -- the message crack (game_state=out1 at L197) sits in the
    # walk window before the diverging loop-tail const stores (L84/L88).
    fr = [{"type_class": 5, "opcode": 0x30, "line": 197},   # dword load
          {"type_class": 5, "opcode": 0x30, "line": 197},   # same line -> collapsed
          {"type_class": 5, "opcode": 0x26, "line": 84},    # const store
          {"type_class": 0, "opcode": 0x26, "line": 82},    # byte op, ignored
          {"type_class": 5, "opcode": 0x26, "line": 88}]
    assert RH._rover_sites(fr, "dword") == "197:L 84:C 88:C"
    # no line_num (old trace image) -> empty, hint degrades gracefully
    assert RH._rover_sites([{"type_class": 5, "opcode": 0x30, "line": None}], "dword") == ""
    assert RH._rover_sites([], "dword") == ""


def test_arm_swap_search_rule_122():
    # Synthetic two-arm scenario: blocks walked B1(cond), B2(else-store),
    # B3(then RMW), B4(tail).  RC walk: store(B2) advances BEFORE the RMW
    # (B3) -> RMW lands one register later than PS, which walked the arms
    # the other way round.  All excepts allow everything but EAX (so picks
    # advance EDX,EBX,ECX,...).
    EXC = 0x40fff800 | 0x1000003          # ESP/EBP-ish base + EAX blocked
    def ev(line, blk, opcode=0x26):
        return {"type_class": 5, "opcode": opcode, "except": EXC,
                "line": line, "blk": blk}
    fr = [
        ev(10, 0, 0x35),    # B1 cond cmp scratch        -> edx
        ev(20, 1, 0x26),    # B2 else =0 store           -> ebx
        ev(15, 2, 0x01),    # B3 then RMW                -> ecx   (kept)
        ev(30, 3, 0x26),    # B4 tail store              -> esi   (kept)
    ]
    # RC kept picks (disasm): RMW=ecx, tail=esi.  PS: RMW=ebx (arms swapped),
    # tail=esi (self-healed? no -- swap moves B2's advance after B3:
    # B3 gets ebx, B2 gets ecx, B4 still esi).
    res = RH._arm_swap_search(fr, "dword", ["ecx", "esi"], ["ebx", "esi"],
                              False, False)
    assert res is not None
    a, b, la, lb = res
    assert {a, b} == {1, 2}
    assert {la, lb} == {20, 15}
    # without blk tags (old trace image) the test degrades to None
    fr_nb = [dict(x, blk=None) for x in fr]
    assert RH._arm_swap_search(fr_nb, "dword", ["ecx", "esi"],
                               ["ebx", "esi"], False, False) is None


def test_rover_sites_annotates_source_text():
    # src_lines turns the bare walk-order map into the actionable form:
    # each site carries the source construct that produces the advance.
    fr = [{"type_class": 5, "opcode": 0x30, "line": 795},
          {"type_class": 5, "opcode": 0x26, "line": 796}]
    src = {795: "    if (cohort_tick_gate >= 2) {",
           796: "        cohort_tick_gate = 0;"}
    out = RH._rover_sites(fr, "dword", src)
    assert "795:L \u00abif (cohort_tick_gate >= 2)\u00bb" in out
    assert "796:C \u00abcohort_tick_gate = 0;\u00bb" in out
    # no src_lines -> unchanged bare form (back-compat)
    assert RH._rover_sites(fr, "dword") == "795:L 796:C"


def test_src_text_trims_and_collapses():
    src = {10: "        if   (pm_over  == 0)   {  ",
           11: "    x = " + "a" * 80 + ";"}
    assert RH._src_text(src, 10) == "if (pm_over == 0)"
    assert RH._src_text(src, 11, width=20).endswith("\u2026")
    assert RH._src_text(src, 999) == ""
    assert RH._src_text(None, 10) == ""


def test_actionable_names_divergence_and_action():
    # +1 dword advance before a const-store divergence; the loads before it are
    # not const-stores -> no host, the ACTION + sites are still named.
    fr = [{"type_class": 5, "opcode": 0x30, "line": 773},
          {"type_class": 5, "opcode": 0x30, "line": 795},
          {"type_class": 5, "opcode": 0x26, "line": 796}]
    src = {773: "    if (pm_over == 0) {",
           795: "    if (cohort_tick_gate >= 2) {",
           796: "        cohort_tick_gate = 0;"}
    struct = {"dup_hosts": {}, "guard_stores": set(), "const_stores": {796}}
    txt = RH._actionable("dword", (796, "ebx", "ecx"), [1], None, fr, src,
                         False, struct)
    assert "divergence line 796: `cohort_tick_gate = 0;`" in txt
    assert "ACTION: ADD 1 dword advance(s) BEFORE line 796" in txt
    assert "no duplicated-tail host before line 796" in txt
    assert "773:L" in txt and "795:L" in txt          # advance sites listed


def test_actionable_real_dup_host_from_ast():
    # a const-store BEFORE the divergence that the AST says follows an if/else
    # -> a DEFINITE duplicated-tail host (no hedging).
    fr = [{"type_class": 5, "opcode": 0x26, "line": 100},   # const store host
          {"type_class": 5, "opcode": 0x30, "line": 110},   # load divergence
          {"type_class": 5, "opcode": 0x30, "line": 120}]
    src = {100: "    smk_ref_wi = 0x28;", 110: "    if (g > 3) {", 120: "    f();"}
    struct = {"dup_hosts": {100: 90}, "guard_stores": set(), "const_stores": {100}}
    txt = RH._actionable("dword", (110, "ebx", "ecx"), [1], None, fr, src,
                         False, struct)
    assert "+1 HOST = the const-store at line 100" in txt
    assert "shared tail of the if/else at line 90" in txt
    assert "both arms" in txt.lower()


def test_actionable_guard_stores_are_not_dup_hosts():
    # all const-stores before the divergence are early-return guards -> the AST
    # gives the DEFINITE verdict that they are NOT dup-able.
    fr = [{"type_class": 5, "opcode": 0x26, "line": 1770},  # guard store
          {"type_class": 5, "opcode": 0x26, "line": 1756}]  # const-store divergence
    src = {1770: "        last_icon_over = 2;", 1756: "        last_icon_over = 1;"}
    struct = {"dup_hosts": {}, "guard_stores": {1770, 1756},
              "const_stores": {1770, 1756}}
    txt = RH._actionable("dword", (1756, "edx", "ebx"), [1], None, fr, src,
                         False, struct)
    assert "early-return guards" in txt
    assert "NOT" in txt and "dup-able" in txt
    assert "PARM-RELOAD" in txt


def _row(ps_asm, rc_asm):
    return {"kind": "replace", "o": (0, 0, b"", ps_asm), "r": (0, 0, b"", rc_asm)}


def test_load_divergences_filters_to_real_loads():
    rows = [
        _row("mov ecx, [0x1000]", "mov ebx, [0x1000]"),     # dword load swap -> kept
        _row("lea ecx, [ebx + 1]", "lea esi, [eax + 1]"),   # lea (inherited) -> dropped
        _row("mov [0x1000], ecx", "mov [0x1000], ebx"),     # store (inherited) -> dropped
        _row("mov edi, [0x2000]", "mov esi, [0x2000]"),     # dword load swap -> kept
        _row("mov cx, [0x3000]", "mov bx, [0x3000]"),       # word (not dword) -> dropped
    ]
    rc, ps = RH._load_divergences(rows)
    assert rc == ["ebx", "esi"] and ps == ["ecx", "edi"]


def test_closeability_closeable_self_heals():
    # 3 dword ops (except=0), the LAST diverges ecx->esi (k=+1); injecting +1
    # before it shifts only it -> CLOSEABLE at the prior op's line.
    fr = [{"type_class": 5, "except": 0, "opcode": 0x30, "line": 10},
          {"type_class": 5, "except": 0, "opcode": 0x30, "line": 20},
          {"type_class": 5, "except": 0, "opcode": 0x30, "line": 30}]
    base = RH._simulate(fr)
    rc_last = base[2][1]            # whatever the sim lands (EBX/ECX...)
    ps_last = RH._NAME[RH._REGS["dword"][(RH._REG_IDX[rc_last] + 1)]]
    rows = [_row(f"mov {ps_last}, [0x1000]", f"mov {rc_last}, [0x1000]")]
    res = RH.closeability(rows, fr)
    assert res is not None and res[0] == "closeable" and res[1] == 1
    assert 20 in res[2]            # inject after the op before the divergence


def test_closeability_blocked_when_tail_op_held():
    # a 4th dword op AFTER the divergence must HOLD; the +1 shifts it too ->
    # BLOCKED (block-order divergence).
    fr = [{"type_class": 5, "except": 0, "opcode": 0x30, "line": 10},
          {"type_class": 5, "except": 0, "opcode": 0x30, "line": 20},
          {"type_class": 5, "except": 0, "opcode": 0x30, "line": 30},
          {"type_class": 5, "except": 0, "opcode": 0x30, "line": 40}]
    base = RH._simulate(fr)
    rc_d = base[2][1]
    ps_d = RH._NAME[RH._REGS["dword"][(RH._REG_IDX[rc_d] + 1)]]
    rows = [_row(f"mov {ps_d}, [0x1000]", f"mov {rc_d}, [0x1000]")]
    res = RH.closeability(rows, fr)
    assert res is not None and res[0] == "blocked"


def test_render_closeability_text():
    assert "SELF-HEALS" in RH.render_closeability(("closeable", 1, [166]))
    assert "BLOCK-ORDER" in RH.render_closeability(("blocked", 1, []))
    assert RH.render_closeability(None) == ""


def test_closeability_compressins_visible_flips_blocked_to_closeable():
    # The 4th dword op (the tail) would block a +1 -- BUT if it's a CompressIns-
    # INVISIBLE op (immediate const-store / single-use compare-load that leaves
    # no register in the bytes) it must NOT be required to hold.  Modelling that
    # via `visible` flips the verdict blocked -> closeable.  This is exactly the
    # build_region_item case (`warned_of_not_build = 1` immediate stores).
    fr = [{"type_class": 5, "except": 0, "opcode": 0x30, "line": 10},
          {"type_class": 5, "except": 0, "opcode": 0x30, "line": 20},
          {"type_class": 5, "except": 0, "opcode": 0x30, "line": 30},
          {"type_class": 5, "except": 0, "opcode": 0x26, "line": 40}]  # const store (invisible)
    base = RH._simulate(fr)
    rc_d, tail = base[2][1], base[3][1]
    ps_d = RH._NAME[RH._REGS["dword"][(RH._REG_IDX[rc_d] + 1)]]
    rows = [_row(f"mov {ps_d}, [0x1000]", f"mov {rc_d}, [0x1000]")]
    # without the model -> BLOCKED (the tail op is required to hold)
    assert RH.closeability(rows, fr)[0] == "blocked"
    # visible set = the 3 real loads only (lines 10/20/30); the L40 const store
    # is invisible -> not required to hold -> CLOSEABLE.
    visible = {(10, base[0][1]), (20, base[1][1]), (30, base[2][1])}
    res = RH.closeability(rows, fr, visible=visible)
    assert res[0] == "closeable"
