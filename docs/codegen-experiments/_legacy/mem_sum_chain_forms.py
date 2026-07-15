#!/usr/bin/env python3
"""Rule 130 oracle: surface forms of an n-term memory sum under -4r.

LdStAlloc RISCifies every memory operand post-alloc (486 scheduling);
LdStCompress/CompressIns merges adjacent pairs back with two
DETERMINISTIC declines (10.0a CompressIns @0x62e16, decompile-confirmed
identical to owp4v1 i86ldstr.c):

  * LAST-ADDEND SPLIT: for the final addend, `next` is the result store
    (`mov [g],acc`, a register-source MOV) -> CompressIns' presult path
    engages and `*popnd != *presult` aborts BOTH merges.
  * ACC-SWAP SPLIT: when SWAPOPS handed the accumulator to the freshly
    loaded register (`add r2, old_acc`), r2 is live after -> the popnd
    live-guard declines.

So `g = a+b+c+d+e;` emits  mov/add[mem]/add[mem]/mov+add(swap)/mov+add
while a `+=` CHAIN emits RMW `add dword [g], reg` stores -- a completely
different shape.  binir `mem_sum_chain` decodes all three sum forms as
ONE statement (ASSIGN + O_PLUS chain); the trace `lc` records are the
RC-side ground truth (fr = split, lc = merge-back commit).

Run:
    python3 docs/codegen-experiments/mem_sum_chain_forms.py
"""
import subprocess
import sys
sys.path.insert(0, "/home/simon/git/caesar2")

SRC = """int g,a,b,c,d,e;
void f2(void){ g = a+b; }
void f5(void){ g = a+b+c+d+e; }
void h(void){ g = a+b; g += c; }
"""


def main():
    open("/tmp/sum.c", "w").write(SRC)
    subprocess.run(
        ["podman", "run", "--rm", "-v", "/tmp:/src",
         "localhost/watcom-10.0a-dosemu2",
         "wcc386 -bt=dos -mf -4r -s -d1 sum.c"],
        check=True, capture_output=True, timeout=300)
    from c2.parsers.omf import parse_obj_functions
    import capstone
    cs = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    got = {n: [f"{i.mnemonic} {i.op_str}".strip() for i in cs.disasm(b, 0)]
           for n, b, *_ in parse_obj_functions("/tmp/sum.obj")}
    f2 = got["f2_"]
    # last-addend split: two loads, one reg-reg add, store
    assert f2[1].startswith("mov eax, dword ptr") and \
           f2[2].startswith("mov edx, dword ptr") and \
           f2[3] == "add eax, edx", f2
    f5 = got["f5_"]
    # merged cascade for middle terms
    assert any(x.startswith("add eax, dword ptr") for x in f5), f5
    # acc swap present (add r2, old_acc)
    assert "add edx, eax" in f5, f5
    h = got["h_"]
    assert any(x.startswith("add dword ptr") for x in h), h  # RMW += form
    # binir decodes the sums as single statements
    from c2 import binir
    insns = []
    off = 0
    for n, b, *_ in parse_obj_functions("/tmp/sum.obj"):
        if n != "f2_":
            continue
        insns = [(i.address, i.size, bytes(i.bytes),
                  f"{i.mnemonic} {i.op_str}".strip()) for i in cs.disasm(b, 0)]
    kinds = [o.kind for o in binir.recover(insns)]
    assert "mem_sum_chain" in kinds, kinds
    print("OK: last-addend split + acc-swap + merged cascade + RMW += form; "
          "mem_sum_chain decodes f2 as one statement")


if __name__ == "__main__":
    main()
