#!/usr/bin/env python3
"""Oracle probe: `for(init; cond; cnt++)` triggers PS-style loop rotation
that `while(cond) {...; cnt++;}` does NOT.

Mechanism (rooted in OW v1 source):
  bld/cc/c/cstmt2.c:850 ForStmt():
      init_expr;  NewLoop();  JumpFalse(cond,break);  body;  EndForStmt()
  bld/cc/c/cstmt2.c:875 EndForStmt():
      DropContinueLabel();  AddStmt(inc_var);  Jump(top_label);
  bld/cc/c/cstmt2.c:416 case T_WHILE end:
      DropContinueLabel();  Jump(top_label);   (no separate inc_var)

The structural difference -- the `for` clause's inc_var being emitted via
AddStmt() as a separate statement between body and back-jump -- triggers
the optimizer's block-layout pass to place the cond block at the BOTTOM
(rotated layout: init; jmp test; body; inc; test+jcc-back) at *default*
optimization, even WITHOUT -ol+ loop-opts gating TwistLoop (which is the
classical induction-variable rotation -- a separate path).

Compile-time probe:                                  expected output:
  for ( ; gy < 0x3c; gy++) { gz += gy; }             jmp L_test
                                                     L_body: gz += gy; gy++
                                                     L_test: cmp gy, 0x3c; jl L_body
  while (gy < 0x3c) { gz += gy; gy++; }              L_top: cmp gy, 0x3c; jge L_exit
                                                     gz += gy; gy++
                                                     jmp L_top

The for-clause rotation is what PS uses for:
  - get_nearest_reg_building (int_c2.c)  +0x1b jmp 0xca to cmp+jl at +0xca
  - convert_lbm_file (lib32.c)           +0x148 jmp 0x194 to cmp+jle at +0x194
  - clear_an_area (map.c)                +0xd8 jmp 0x1e8 to cmp+jle at +0x1e8

CAVEAT: just swapping `while(...; cnt++;)` -> `for(;...;cnt++)` ALSO
flips the increment form from in-place `inc [global]` (PS's 6-byte RMW)
to cached `mov r, [global]; inc r; mov [global], r` (RC's 13-byte cached
form -- a Rule 72 violation).  Get the rotation lever AND the inc form
right or the source change regresses.

Run with:
  cd <caesar2>; python docs/codegen-experiments/loop_rotation_for_vs_while.py
"""

from __future__ import annotations
import re, subprocess, sys, tempfile
from pathlib import Path

PROBES = {
    "for_external_init": """
        extern int gx, gy, gz;
        void f1(void) {
            gy = 0; gz = 0;
            for ( ; gy < 0x3c; gy++) {
                gz += gy;
            }
        }
    """,
    "for_inside_init": """
        extern int gx, gy, gz;
        void f2(void) {
            gz = 0;
            for (gy = 0; gy < 0x3c; gy++) {
                gz += gy;
            }
        }
    """,
    "while_with_inc_in_body": """
        extern int gx, gy, gz;
        void f3(void) {
            gy = 0; gz = 0;
            while (gy < 0x3c) {
                gz += gy;
                gy++;
            }
        }
    """,
}

_CFLAGS = "-bt=dos -mf -4r -s -d1"
_IMG = "localhost/watcom-10.0a-dosemu2"


def _compile_and_disasm(src: str) -> str:
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        (d / "probe.c").write_text(src)
        run = subprocess.run(
            ["podman", "run", "--rm", "-v", f"{d}:/src", _IMG,
             f"wcc386 {_CFLAGS} probe.c"],
            capture_output=True, text=True, timeout=60)
        if run.returncode != 0:
            return f"COMPILE FAIL:\n{run.stdout}\n{run.stderr}"
        run = subprocess.run(
            ["podman", "run", "--rm", "-v", f"{d}:/src", _IMG,
             "wdisasm probe.obj > probe.lst"],
            capture_output=True, text=True, timeout=60)
        return (d / "probe.lst").read_text()


_OFF_RE = re.compile(r"^\s*([0-9a-f]+)\s")


def _row_off(line: str) -> int | None:
    m = _OFF_RE.match(line)
    return int(m.group(1), 16) if m else None


def _has_rotation(lst: str) -> bool:
    """A rotated loop has a FORWARD `jmp Lx` where Lx's offset is LATER
    than the jmp's offset, and Lx (or a few rows after) is a `cmp` whose
    next row is a `jcc Ly` where Ly is BEFORE Lx (back-jump to body)."""
    fn_lines = [l for l in lst.splitlines() if l.strip()]
    label_offs: dict[str, int] = {}
    for line in fn_lines:
        m = re.search(r"\bL(\d+)\b", line[:30])
        off = _row_off(line)
        if m and off is not None:
            label_offs[f"L{m.group(1)}"] = off

    for line in fn_lines:
        m_jmp = re.search(r"\bjmp\s+(L\d+)\b", line)
        if not m_jmp:
            continue
        src_off = _row_off(line)
        tgt = m_jmp.group(1)
        tgt_off = label_offs.get(tgt)
        if src_off is None or tgt_off is None:
            continue
        if tgt_off <= src_off:
            continue   # backward jmp -> head-tested loop tail
        # forward jmp.  Find the row at tgt_off; the rotated form has
        # a `cmp` within the next ~4 rows and then a jcc that points
        # backward to a body label between src_off and tgt_off.
        for i, line2 in enumerate(fn_lines):
            if _row_off(line2) != tgt_off:
                continue
            for k in range(0, 4):
                if i + k >= len(fn_lines):
                    break
                if "cmp" in fn_lines[i + k] or "test" in fn_lines[i + k]:
                    # confirm a backward jcc nearby
                    for j in range(k + 1, k + 4):
                        if i + j >= len(fn_lines):
                            break
                        m_back = re.search(
                            r"\bj(g|l|a|b|e|n|z|c)e?\s+(L\d+)\b",
                            fn_lines[i + j])
                        if m_back:
                            back_off = label_offs.get(m_back.group(2))
                            if (back_off is not None
                                    and src_off < back_off < tgt_off):
                                return True
                    break
            break
    return False


def main() -> int:
    fails = 0
    for nm, src in PROBES.items():
        out = _compile_and_disasm(src)
        rot = _has_rotation(out)
        want_rot = nm.startswith("for_")
        # Only the `for (;cond;inc)` form (empty init, inc clause set) gets
        # the rotated layout at default optimization.  `for(init;cond;inc)`
        # with explicit constant init triggers the do-while form (no
        # initial jmp).  `while` stays head-tested.
        want_rot = (nm == "for_external_init")
        ok = (rot == want_rot)
        status = "PASS" if ok else "FAIL"
        print(f"  [{status}] {nm}: rotation={rot} (expected {want_rot})")
        if not ok:
            fails += 1
            print("--- disasm excerpt ---")
            print("\n".join(out.splitlines()[6:30]))
            print("--- end ---")
    return 0 if fails == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
