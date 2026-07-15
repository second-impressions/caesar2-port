"""Tests for the regtrace x diff correlator (hard-case lever explainer)."""
from c2.commands import regtrace_explain as rx


def _text(conflicts, rows):
    return "\n".join(rx.explain(conflicts, rows))


def test_word_class_truncation():
    """A word-class conflict + masking divergence -> truncation-form lever."""
    conflicts = [{"var": "c", "savings": 55,
                  "cand": ["AX", "DX", "BX", "CX"], "chosen": "AX", "withregs": 0}]
    rows = [{"kind": "replace",
             "ps": {"asm": "and edx, 0xffff"}, "rc": {"asm": "xor eax, eax"}}]
    t = _text(conflicts, rows)
    assert "type-width conflicts" in t
    assert "word-class" in t and "c" in t
    assert "TRUNCATION" in t
    # must NOT misclassify it as a register swap
    assert "register-identity swaps" not in t


def test_register_swap_dominant_value_inversion():
    """No source-line pin -> the dominant rc_r value is inverted toward ps_r.
    EDX(rc) value should be in ECX(ps); ECX is later in DoubleRegs + equal CRM
    => order_loss use-order lever."""
    from c2.commands.regtrace import _REG_ENC
    conflicts = [
        {"var": "a", "savings": 40, "cand": ["EAX", "EDX", "EBX", "ECX"],
         "chosen": "EDX", "withregs": _REG_ENC["EAX"], "def_line_num": 0},
        {"var": "b", "savings": 40, "cand": ["EAX", "EDX", "EBX", "ECX"],
         "chosen": "ECX", "withregs": _REG_ENC["EAX"] | _REG_ENC["EDX"], "def_line_num": 0},
    ]
    rows = [{"kind": "replace", "ln": None, "ps": {"asm": "mov edi, ecx"},
             "rc": {"asm": "mov edi, edx"}},
            {"kind": "replace", "ln": None, "ps": {"asm": "inc edx"},
             "rc": {"asm": "inc ecx"}}]
    t = _text(conflicts, rows)
    assert "ECX <-> EDX" in t and "(2 row(s))" in t
    assert "best-guess" in t and "order_loss" in t


def test_register_swap_taken_inversion():
    """Dominant rc_r value: ps_r is held by a higher-savings rival => taken."""
    from c2.commands.regtrace import _REG_ENC
    conflicts = [
        {"var": "want", "savings": 40, "cand": ["EAX", "EDX", "EBX", "ECX"],
         "chosen": "EBX", "withregs": _REG_ENC["EAX"] | _REG_ENC["EDX"], "def_line_num": 0},
        {"var": "rival", "savings": 99, "cand": ["EAX", "EDX"],
         "chosen": "EDX", "withregs": _REG_ENC["EAX"], "def_line_num": 0},
    ]
    rows = [{"kind": "replace", "ln": None, "ps": {"asm": "add edx, 1"},
             "rc": {"asm": "add ebx, 1"}}]
    t = _text(conflicts, rows)
    assert "EDX <-> EBX" in t
    assert "best-guess" in t and "taken" in t


def test_no_regalloc_divergence():
    """Identical register usage -> outside the regalloc model."""
    conflicts = [{"var": "x", "savings": 10, "cand": ["EAX", "EDX"], "chosen": "EAX",
                  "withregs": 0}]
    rows = [{"kind": "replace", "ps": {"asm": "shl eax, 1"}, "rc": {"asm": "add eax, eax"}}]
    t = _text(conflicts, rows)
    assert "outside regalloc" in t


def test_extension_row_not_counted_as_swap():
    """movzx/movsx form difference is truncation, never a register swap."""
    conflicts = []
    rows = [{"kind": "replace", "ps": {"asm": "movzx eax, byte ptr [edx]"},
             "rc": {"asm": "mov al, byte ptr [edx]"}}]
    t = _text(conflicts, rows)
    assert "truncation/extension" in t
    assert "register-identity swaps" not in t


# ---- differential trace (_diff_tables) -------------------------------------
from c2.commands.regtrace import _diff_tables, _conflict_key  # noqa: E402


def _c(order, var, sav, chosen, cand, rng=2, line=0):
    return {"order": order, "var": var, "def_line": line, "savings": sav,
            "range_len": rng, "cand": cand, "chosen": chosen, "crm_scores": {},
            "withregs": 0}


def test_diff_named_savings_and_chosen_change():
    base = [_c(0, "c", 55, "AX", ["AX", "DX"], rng=64, line=581)]
    cur = [_c(0, "c", 40, "DX", ["DX", "AX"], rng=64, line=581)]
    t = "\n".join(_diff_tables(base, cur))
    assert "~ c" in t
    assert "savings 55->40" in t and "chosen AX->DX" in t
    assert "1 changed" in t


def test_diff_savecalc_block_delta():
    """A savings change with cv data pins to the changed block term."""
    base = [_c(0, "c", 40, "EBX", ["EBX"], line=581)]
    cur = [_c(0, "c", 50, "EBX", ["EBX"], line=581)]
    base[0]["savecalc"] = [{"blk": "a", "save": 3, "cost": 0, "depth": 1},
                           {"blk": "b", "save": 4, "cost": 0, "depth": 3}]
    cur[0]["savecalc"] = [{"blk": "a", "save": 3, "cost": 0, "depth": 1},
                          {"blk": "b", "save": 5, "cost": 0, "depth": 3}]
    t = "\n".join(_diff_tables(base, cur))
    assert "savings 40->50" in t
    assert "savecalc [3@d1 + 4@d3] -> [3@d1 + 5@d3]" in t


def test_diff_savecalc_silent_when_equal():
    """No savecalc line when breakdowns match or are absent."""
    base = [_c(0, "c", 55, "AX", ["AX"], line=581)]
    cur = [_c(0, "c", 40, "DX", ["DX"], line=581)]
    t = "\n".join(_diff_tables(base, cur))
    assert "savecalc" not in t


def test_diff_added_named_conflict():
    base = [_c(0, "c", 55, "AX", ["AX"], line=581)]
    cur = [_c(0, "c", 55, "AX", ["AX"], line=581),
           _c(1, "new", 25, "EBX", ["EBX"], line=590)]
    t = "\n".join(_diff_tables(base, cur))
    assert "+ new" in t and "1 added" in t


def test_diff_temp_useorder_shift_suppressed():
    """A temp's absolute order shifting (from a named insertion) is NOT noise."""
    base = [_c(2, None, 20, "EAX", ["EAX"])]
    cur = [_c(0, "new", 25, "EBX", ["EBX"], line=5), _c(3, None, 20, "EAX", ["EAX"])]
    t = "\n".join(_diff_tables(base, cur))
    assert "use-order" not in t          # temp order shift suppressed
    assert "+ new" in t


def test_diff_neutral_edit():
    base = [_c(0, "c", 55, "AX", ["AX"], line=581)]
    t = "\n".join(_diff_tables(base, list(base)))
    assert "regalloc-neutral" in t


def test_diff_histogram_delta():
    base = [_c(0, "a", 10, "EAX", ["EAX"]), _c(1, "b", 10, "EDX", ["EDX"])]
    cur = [_c(0, "a", 10, "EBX", ["EBX"]), _c(1, "b", 10, "EDX", ["EDX"])]
    t = "\n".join(_diff_tables(base, cur))
    assert "histogram delta" in t and "EAX 1->0" in t and "EBX 0->1" in t


def test_line_pinning_in_swap():
    """def_line_num pins a swap row to the specific conflict at that line."""
    conflicts = [
        {"var": "p", "savings": 40, "cand": ["EAX", "EDX", "EBX", "ECX", "ESI", "EDI"],
         "chosen": "ESI", "withregs": 0, "def_line_num": 88},
        {"var": "q", "savings": 40, "cand": ["EAX", "EDX", "EBX", "ECX", "ESI", "EDI"],
         "chosen": "EDI", "withregs": 0, "def_line_num": 88},
    ]
    rows = [{"kind": "replace", "ln": 88, "ps": {"asm": "mov eax, esi"},
             "rc": {"asm": "mov eax, edi"}}]
    t = "\n".join(rx.explain(conflicts, rows))
    assert "line 88" in t and "p[ESI" in t and "q[EDI" in t


# ---- model inversion (invert_to_target) ------------------------------------
from c2.commands.regtrace_explain import invert_to_target  # noqa: E402


def _conf(chosen, cand, withregs=0, ins_walk=None, var="v", line=10, sav=20):
    return {"var": var, "chosen": chosen, "cand": cand, "withregs": withregs,
            "ins_walk": ins_walk or [], "def_line_num": line, "savings": sav}


def test_invert_already_matches():
    c = _conf("EAX", ["EAX", "EDX"])
    assert invert_to_target(c, "EAX", [c]) is None


def test_invert_not_candidate_type_lever():
    # PS wants EAX (int) but the value is word-class (candidates AX,DX)
    c = _conf("AX", ["AX", "DX"])
    inv = invert_to_target(c, "EAX", [c])
    assert inv["case"] == "not_candidate"
    assert "TYPE/class" in inv["lever"]


def test_invert_taken_by_competitor():
    from c2.commands.regtrace import _REG_ENC
    # EDX taken in with.regs; a rival conflict chose EDX
    c = _conf("EBX", ["EAX", "EDX", "EBX", "ECX"], withregs=_REG_ENC["EDX"] | _REG_ENC["EAX"])
    rival = _conf("EDX", ["EAX", "EDX"], var="rival", line=8, sav=99)
    inv = invert_to_target(c, "EDX", [c, rival])
    assert inv["case"] == "taken"
    assert inv["competitor"] is rival
    assert "rival" in inv["detail"]


def test_invert_order_loss_use_order():
    from c2.commands.regtrace import _REG_ENC
    # target ECX free + candidate, equal CRM (no ins_walk), but later than chosen EAX
    c = _conf("EAX", ["EAX", "EDX", "EBX", "ECX"], withregs=0)
    inv = invert_to_target(c, "ECX", [c])
    assert inv["case"] == "order_loss"
    # the equal-savings tie-break is reverse-last-use (conflicts created at the
    # operand's LAST use, backward scan + prepend + unstable ShellSort)
    assert "LAST USE" in inv["lever"] or "LAST-USE" in inv["lever"]


# ---- inversion-guided solve targets + safe reorder ------------------------


# ---- given_regs ground-truth cross-check (retry-round detector) -------------
from c2.commands.regtrace import given_regs_drift  # noqa: E402


def _g(order, var, chosen, given):
    return {"order": order, "var": var, "chosen": chosen, "given_regs": given}


def test_given_regs_clean_single_round():
    # seed EAX (parm), pick EDX, then EBX: ground truth tracks the picks
    table = [_g(0, "a", "EDX", 0x1000003),
             _g(1, "b", "EBX", 0x1000003 | 0x80000c0),
             _g(2, "c", "ECX", 0x1000003 | 0x80000c0 | 0x200000c)]
    assert given_regs_drift(table) == []


def test_given_regs_drift_unexplained_bit():
    # conflict 1 sees ESI given, but nobody picked ESI -> retry-round signature
    table = [_g(0, "a", "EDX", 0),
             _g(1, "b", "EBX", 0x80000c0 | 0x10000100)]
    lines = given_regs_drift(table)
    assert lines and "DRIFT at alloc #1" in lines[0]
    assert "unexplained ESI" in lines[0]
    assert "retry rounds" in lines[-1]


def test_given_regs_drift_missing_bit():
    # conflict 1's ground truth LOST the EDX pick (kept only the EAX seed)
    # -> GivenRegisters reset between rounds
    table = [_g(0, "a", "EDX", 0x1000003),
             _g(1, "b", "EBX", 0x1000003)]
    lines = given_regs_drift(table)
    assert lines and "missing EDX" in lines[0]


def test_given_regs_no_ground_truth_is_silent():
    # all-zero gt => old trace (or rq-only rows): no check possible
    table = [_g(0, "a", "EDX", 0), _g(1, "b", "EBX", 0)]
    assert given_regs_drift([]) == []
    assert given_regs_drift(table) == []


def test_do_this_clean_swap_is_confident():
    """A clean swap-only diff -> confident DO THIS naming the exact decl pair."""
    from c2.commands.regtrace_explain import _do_this
    rc = {"var": "best_x", "def_line_num": 4556, "savings": 102}
    ps = [{"var": "best_y", "def_line_num": 4557, "savings": 102}]
    out = _do_this("order_loss", rc, ps, has_typewidth=False)
    assert out.startswith("DO THIS:")
    assert "best_x (ln4556)" in out and "best_y (ln4557)" in out


def test_do_this_demotes_to_candidate_when_noisy():
    """type-width / semantic noise -> CANDIDATE, never a confident DO THIS."""
    from c2.commands.regtrace_explain import _do_this
    rc = {"var": "best_x", "def_line_num": 4556, "savings": 102}
    ps = [{"var": "best_y", "def_line_num": 4557, "savings": 102}]
    out = _do_this("order_loss", rc, ps, has_typewidth=True)
    assert out.startswith("CANDIDATE")
    assert "may regress" in out


def test_do_this_none_for_temps_and_nontie():
    from c2.commands.regtrace_explain import _do_this
    rc = {"var": "(temp)", "def_line_num": 10, "savings": 5}
    ps = [{"var": "x", "def_line_num": 11, "savings": 5}]
    assert _do_this("order_loss", rc, ps) is None          # temp -> no handle
    assert _do_this("interference", {"var": "a", "def_line_num": 1, "savings": 9},
                    [{"var": "b", "def_line_num": 2, "savings": 9}]) is None
