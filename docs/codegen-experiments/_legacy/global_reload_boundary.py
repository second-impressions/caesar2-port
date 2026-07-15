#!/usr/bin/env python3
"""Rule 129 oracle: the CALL is the reload boundary for direct global reads.

wcc386 -4r value-pools a global's loaded register across plain stores to
OTHER symbols (f1: one load for three uses), but a CALL kills the copy --
the next use RELOADS from memory (f2).  A named local caching the global
(h1) instead survives the call in a CALLEE-SAVE register, costing a
push/pop pair and one fewer load.

Therefore: PS showing N repeated loads of the same global (one after each
call) while RC loads it once and pushes an extra callee-save = the decomp
invented a caching local -- write the global directly at each use.
Bonus (f3): the value pool also propagates a KNOWN CONSTANT assigned to a
global into subsequent address arithmetic (`g=5; arr[g+1]` folds to
[0x18]).

Run:
    python3 docs/codegen-experiments/global_reload_boundary.py
"""
import subprocess
import sys
sys.path.insert(0, "/home/simon/git/caesar2")

SRC = """int g; int arr[100]; int brr[100];
extern void ext(void);
void f1(void){ arr[g]=1; arr[g+1]=2; arr[g+2]=3; }
void f2(void){ arr[g]=1; ext(); arr[g+1]=2; }
void f3(void){ arr[g]=1; brr[g]=2; g=5; arr[g+1]=7; }
void h1(void){ int i=g; arr[i]=1; ext(); arr[i+1]=2; }
"""


def main():
    open("/tmp/rld.c", "w").write(SRC)
    subprocess.run(
        ["podman", "run", "--rm", "-v", "/tmp:/src",
         "localhost/watcom-10.0a-dosemu2",
         "wcc386 -bt=dos -mf -4r -s -d1 rld.c"],
        check=True, capture_output=True, timeout=300)
    from c2.parsers.omf import parse_obj_functions
    import capstone
    cs = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    got = {n: [f"{i.mnemonic} {i.op_str}".strip() for i in cs.disasm(b, 0)]
           for n, b, *_ in parse_obj_functions("/tmp/rld.obj")}
    n_load = lambda f: sum(1 for x in got[f]
                           if x.startswith("mov") and "ptr [0]" in x)
    assert n_load("f1_") == 1, got["f1_"]      # value-pool across stores
    assert n_load("f2_") == 2, got["f2_"]      # CALL kills -> reload
    assert n_load("h1_") == 1, got["h1_"]      # local survives the call
    assert got["h1_"][0] == "push edx", got["h1_"]   # ...in a callee-save
    assert any("[0x18], 7" in x for x in got["f3_"])  # const propagation
    print("OK: call = reload boundary; caching local = callee-save + 1 load")


if __name__ == "__main__":
    main()
