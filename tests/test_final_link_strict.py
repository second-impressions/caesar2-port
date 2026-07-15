"""Strict final-link gate used by ``c2 decomp-verify``."""

from copy import deepcopy

from c2.commands.decomp_verify import (
    _final_link_failure_reasons,
    _final_link_relocations_by_address,
)


def _clean_report() -> dict:
    return {
        "code": {
            "game": {
                "exact": 1435, "diff": 0, "missing": 0,
                "anchored": 0, "diff_bytes": 0, "tail": 0,
            },
            # Post-RET span noise remains explicitly non-failing.
            "crt": {
                "exact": 194, "diff": 0, "missing": 0,
                "anchored": 0, "diff_bytes": 0, "tail": 1,
            },
        },
        "data": {"exact": 341, "diff": 0, "missing": 0, "anchored": 0},
        "strict_code_bytes": 0,
        "pre_debug_byte_diff": 0,
        "whole_file_byte_diff": 0,
        "debug_grafted": True,
        "strict_sites": [],
        "fixups": {
            "code": {
                "only_ps": [], "only_rc": [], "target_mismatches": [],
            },
            "data": {
                "only_ps": [], "only_rc": [], "target_mismatches": [],
            },
        },
        "placement": {
            # A byte-identical public/debug label alias is also non-failing.
            "starts_breaks": ["~sound_error(alias RC→0x1234)"],
            "data_misplaced": [],
        },
        "sizes": {
            "o_code": 508368, "r_code": 508368,
            "o_dfile": 53231, "r_dfile": 53231,
            "o_dvsize": 562208, "r_dvsize": 562208,
        },
    }


def test_clean_final_link_accepts_documented_nonsemantic_noise():
    assert _final_link_failure_reasons(_clean_report()) == []


def test_final_link_rejects_wrong_fixup_target():
    report = _clean_report()
    report["fixups"]["code"]["target_mismatches"] = [
        {"site": 0x123, "ps_target": (2, 0x10), "rc_target": (2, 0x20)},
    ]
    assert _final_link_failure_reasons(report) == [
        "code fixups: 1 target mismatch(es)",
    ]


def test_final_link_rejects_whole_file_difference():
    report = _clean_report()
    report["whole_file_byte_diff"] = 1
    assert _final_link_failure_reasons(report) == [
        "1 whole-file byte(s) differ",
    ]


def test_final_link_rejects_every_loaded_image_divergence_class():
    report = deepcopy(_clean_report())
    report["code"]["game"]["diff"] = 2
    report["code"]["game"]["missing"] = 1
    report["data"]["diff"] = 3
    report["strict_code_bytes"] = 4
    report["pre_debug_byte_diff"] = 5
    report["fixups"]["data"]["only_ps"] = [1]
    report["fixups"]["data"]["only_rc"] = [2, 3]
    report["placement"]["starts_breaks"].append("move_figure")
    report["placement"]["data_misplaced"] = ["target_x"]
    report["sizes"]["r_dvsize"] += 4

    assert _final_link_failure_reasons(report) == [
        "game code: 2 diff, 1 unmatched",
        "initialized data: 3 diff",
        "4 strict code byte(s) differ",
        "5 pre-debug container byte(s) differ",
        "data fixups: 1 PS-only site(s), 2 RC-only site(s)",
        "1 code symbol start(s) misplaced",
        "1 data symbol(s) misplaced",
        "data vsize: PS 562208 != RC 562212",
    ]


def test_missing_comparison_report_fails_closed():
    assert _final_link_failure_reasons(None) == [
        "final-link comparison produced no report",
    ]


def test_code_relocation_defects_are_attributed_to_containing_function():
    report = _clean_report()
    report["fixups"]["code"]["target_mismatches"] = [
        {
            "site": 0x112,
            "ps_target": (2, 0x10),
            "rc_target": (2, 0x20),
            "ps_target_name": "target_x",
            "rc_target_name": "target_y",
        },
    ]
    symbols = [
        {"offset": 0x100, "_end": 0x120, "address": 0x10100},
        {"offset": 0x120, "_end": 0x140, "address": 0x10120},
    ]

    assert _final_link_relocations_by_address(report, symbols) == {
        0x10100: [{
            "site": 0x112,
            "ps_target": (2, 0x10),
            "rc_target": (2, 0x20),
            "ps_target_name": "target_x",
            "rc_target_name": "target_y",
            "function_offset": 0x12,
        }],
    }
