#!/usr/bin/env python3
"""Rule 132 oracle: copy-then-op vs op-in-place = left-operand liveness.

wcc386 reduces every two-address binary op through a result temp
(OW v1 bld/cg/c/split.c rMOVOP1RES prefixes ``mov result, op0``;
rUSEREGISTER's CanUseOp1 checks ``HW_Ovlap(op0.reg, next->live.regs)``).
The register allocator coalesces the result with op0 -- deleting the
copy -- exactly when op0's value DIES at the op.

Expected codegen (watcall: a=EAX, b=EDX):

  f1 (a dead):        sub eax, edx               ; in-place
  f2 (a read later):  mov ebx, eax               ; value-preserving copy
                      sub ebx, edx               ;   (+ EBX goes callee-save:
                      ...                        ;    push/pop ride along)
  f3 (return a):      same copy form as f2 -- even a bare return keeps it.

Decomp-verify levers fed by this oracle:
  * binir kind ``copy_then_op``  (c2/binir.py) -- decodes the pair to ONE
    ASSIGN so stmt-IR doesn't flag restructuring.
  * Rule 132 detector (c2/commands/rule_hints.py) -- PS-side copy means
    PS's source READS the left value again later (find/add that use);
    recomp-side copy means OUR source keeps an extra later use.

Run:  python3 docs/codegen-experiments/copy_then_op_liveness.py
"""

import subprocess
import sys
import tempfile
from pathlib import Path

SRC = """\
int g, h;
void f1(int a, int b){ g = a - b; }
void f2(int a, int b){ g = a - b; h = a + 3; }
int f3(int a, int b){ g = a - b; return a; }
"""

IMAGE = "localhost/watcom-10.0a-dosemu2"


def main() -> int:
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        (d / "cuo.c").write_text(SRC)
        r = subprocess.run(
            ["podman", "run", "--rm", "-v", f"{td}:/src", IMAGE,
             "wcc386 -bt=dos -mf -4r -s -d1 cuo.c"],
            capture_output=True, text=True, timeout=300)
        if not (d / "cuo.obj").exists():
            print(r.stdout[-500:], r.stderr[-200:])
            return 1
        sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
        import capstone
        from c2.parsers.omf import parse_obj_functions
        cs = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
        asm = {}
        for f in parse_obj_functions(str(d / "cuo.obj")):
            name = f.name if hasattr(f, "name") else f[0]
            code = f.code if hasattr(f, "code") else f[1]
            asm[name.rstrip("_")] = [
                f"{i.mnemonic} {i.op_str}".strip()
                for i in cs.disasm(bytes(code), 0)]
        ok = True
        # f1: in-place, no reg,reg mov before the sub
        ok &= asm["f1"][0] == "sub eax, edx"
        # f2/f3: copy-then-op
        for fn in ("f2", "f3"):
            body = asm[fn]
            i = next(k for k, t in enumerate(body) if t.startswith("sub"))
            ok &= body[i - 1].startswith("mov ") and body[i].endswith(", edx")
            ok &= ", eax" in body[i - 1]          # copy FROM the live value
        for fn, body in asm.items():
            print(f"-- {fn}")
            for t in body:
                print(f"   {t}")
        print("PASS" if ok else "FAIL: codegen no longer matches Rule 132")
        return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
