#!/usr/bin/env python3
"""Rule 85 oracle probes (2026-06-10): far-pointer constant returns.

Findings (Watcom 10.0a, PS flags `-bt=dos -mf -4r -s -d1`):

1. `return (char __far *)N;`        -> xor edx,edx; mov eax,N
2. `return (char __far *)MK_FP(S,N);` (<i86.h>)
                                    -> mov edx,S;   mov eax,N
   ONLY MK_FP produces a nonzero EDX immediate -- this decoded PS
   start_sequences' return-2 `mov edx,1; mov eax,2` = MK_FP(1, 2).
3. No 64-bit type exists in 10.0a (`long long` E1060, `__int64` E1022),
   so an EDX:EAX immediate pair at an exit is NEVER a 64-bit constant.
4. Mixing bare `return;` with valued returns is E1096 (hard error):
   bare-exit paths in PS far*-functions are guard-wrapper fall-offs.
5. A guard-wrapper far* function with calls in the body funnels the
   retval pair through callee-saves + homing MOVs at one exit (the
   W107 join-read keeps the uninitialized temp live across calls) --
   PS instead shows per-site EDX:EAX with no homing; the suppressing
   source shape is the OPEN question (see pcsound.c start_sequences).

Machine levers built from these: binir `farptr_ret_const` /
`regpair_const_exit` + `tail_merge.classify_regpair_exit` +
`frame_hints.detect_retval_funnel`.

Run: `python docs/codegen-experiments/farptr_return_mkfp.py`
(needs podman image localhost/watcom-10.0a-dosemu2).
"""

import subprocess
import tempfile
from pathlib import Path

PROBE = r"""
#include <i86.h>
extern int ga, gb;
char __far *f(void) {
    if (ga) return (char __far *)MK_FP(1, 2);
    if (gb) return (char __far *)1;
    return 0;
}
"""

EXPect = """
expected f_ code (10.0a):
  cmp [ga],0; je L1; mov edx,1;   mov eax,2; ret    ; MK_FP(1,2)
L1: cmp [gb],0; je L2; xor edx,edx; mov eax,1; ret  ; plain cast
L2: xor edx,edx; xor eax,eax; ret
"""


def main() -> None:
    with tempfile.TemporaryDirectory() as td:
        src = Path(td) / "mkfp.c"
        src.write_text(PROBE)
        subprocess.run(
            ["podman", "run", "--rm", "-v", f"{td}:/src",
             "localhost/watcom-10.0a-dosemu2",
             "wcc386 -bt=dos -mf -4r -s -d1 mkfp.c"],
            check=True)
        from c2.parsers import omf
        import capstone
        cs = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
        fns = omf.parse_obj_functions(str(Path(td) / "mkfp.obj"))
        body = fns[0][1]
        text = "\n".join(f"{i.mnemonic} {i.op_str}".strip()
                         for i in cs.disasm(body, 0))
        print(text)
        assert "mov edx, 1" in text and "mov eax, 2" in text, \
            "MK_FP(1,2) must emit a nonzero EDX immediate"
        assert "xor edx, edx" in text, \
            "plain cast must zero the segment"
        print("\nOK -- Rule 85 MK_FP lowering reproduced")


if __name__ == "__main__":
    main()
