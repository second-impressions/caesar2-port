#!/usr/bin/env python3
"""Rule 128 oracle: pointer-local hoist vs direct array indexing.

Watcom 10.0a lowers `arr[gi].a = 0` (direct) with the array base folded
into each access displacement: the result is N_INDEXED **with a symbol
base**, so i86ldstr.c `Enregister` fires for `OP_MOV const -> mem` and the
constant is RISCified into a register shared by every store in the run:

    f:  movsx edx,[gi]; <idx*sizeof math in eax>
        xor edx, edx
        mov [eax+0x76], edx        ; 6b per store, one fixup each
        mov [eax+0x7a], edx
        mov [eax+0x7e], edx

A pointer local `struct A *p = &arr[gi]` materializes the base into the
register (`add eax, ARR`), so each access is N_INDEXED with base==NULL --
Enregister explicitly breaks on that case (owp4v1 bld/cg/intel/c/
i86ldstr.c, `case N_INDEXED: if (ins->result->i.base == NULL) break;`)
and the stores stay immediate-form:

    g:  movsx edx,[gi]; <same idx math>
        add eax, ARR               ; the materialize (+5b)
        mov dword [eax+0x76], 0    ; 10b per store, no shared zero reg
        ...

Consequences of the pointer form beyond the stores: the index derivation
is CACHED in the pointer (direct form re-derives movsx+imul per statement
group -> PS-only signext_load_* excess), and the pointer occupies a
callee-save register across statements (prologue pressure).

Run:
    python3 docs/codegen-experiments/ptr_local_vs_direct_indexing.py
"""
import subprocess
import sys
sys.path.insert(0, "/home/simon/git/caesar2")

SRC = """struct A { char pad[0x76]; int a,b,c; char d; };
struct A arr[40];
short gi;
void f(void){ arr[gi].a = 0; arr[gi].b = 0; arr[gi].c = 0; }
void g(void){ struct A *p = &arr[gi]; p->a = 0; p->b = 0; p->c = 0; }
"""


def main():
    open("/tmp/ptr1.c", "w").write(SRC)
    subprocess.run(
        ["podman", "run", "--rm", "-v", "/tmp:/src",
         "localhost/watcom-10.0a-dosemu2",
         "wcc386 -bt=dos -mf -4r -s -d1 ptr1.c"],
        check=True, capture_output=True, timeout=300)
    from c2.parsers.omf import parse_obj_functions
    import capstone
    cs = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    got = {}
    for n, b, *_ in parse_obj_functions("/tmp/ptr1.obj"):
        got[n] = [f"{i.mnemonic} {i.op_str}".strip() for i in cs.disasm(b, 0)]
    f, g = got["f_"], got["g_"]
    assert "xor edx, edx" in f, f                      # shared zero register
    assert any(x.startswith("mov dword ptr [eax + 0x76], edx") for x in f), f
    assert any(x.startswith("add eax, 0") for x in g), g   # base materialize
    assert any(x.startswith("mov dword ptr [eax + 0x76], 0") for x in g), g
    assert not any(x.startswith("xor") for x in g), g       # no zero reg
    print("OK: direct=reg-form zero stores (Enregister), "
          "pointer-local=imm stores + base materialize")


if __name__ == "__main__":
    main()
