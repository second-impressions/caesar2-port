"""off-seat-reuse -- NEGATIVE: get_query_info's off ESI<-EAX is NOT a
flippable byte fixpoint (unlike education-ov-seats); it is a FORCED
highest-savings seat.

Why (from OW v1 cg/c + cg/h, verified against the real-10.0a tracer):
  * `off` is marched: `off += 0x14` and `off += (0x50-x)*0x14` are
    in-place ops, and CalcSavings/savcode.h `_ReplaceOpnd` DOUBLES
    `use_save` for the first operand of a register-result op.  At inner
    loop depth 2 (Weight ~x100) that makes off the unique savings max
    (621; ground truth `SortConflicts #0`).
  * `GiveBestReg` walks EAX-first, CountRegMoves(off,EAX)==(off,ESI),
    and when the #0 conflict allocates `GivenRegisters` is EMPTY -- so
    the GivenRegisters tie-break that would pick ESI CANNOT fire.
    => off -> EAX, deterministically.

Sweep below (decl-order x break-form x store-form, 12 variants) keeps
off in EAX in EVERY case -- no equal-savings symmetry to re-select.
Flipping off would require LOWERING its savings below another value =
NOT marching off in place = a different byte stream from PS.  The
education-ov fixpoint technique does not apply to a strict-max dword
seat.
"""

from c2.commands.cgex import Experiment

exp = Experiment(
    name="off-seat-reuse", chk=False,
    externs={"sink": "extern void sink(void);"},
)

GLOBALS = (
    "unsigned char cmap[120000];\nunsigned char people[64];\n"
    "int gcount, gmn_x, gmn_y, axg, ayg;\nint gx, gy;\n"
    "#pragma aux sink modify [eax ecx edx ebx];\n"
)

HEAD = """
int f(int dx, int dy)
{
    int ptr; int off; int ax; int ay; int x; int y;
    %DECLS%
    ptr = dy * 80 + dx;
    gx = cmap[ptr]; sink(); gy = cmap[ptr]; sink();
    ax = dx - 1; ay = dy - 1; x = 3; y = 3;
    if (ax < 0) { x = 2; ax = 0; } else if (ax + x > 80) x = 2;
    if (ay < 0) { y = 2; ay = 0; } else if (ay + y > 60) y = 2;
    off = (ay * 80 + ax) * 20;
    gmn_y = ay;
    for ( ; gmn_y < ay + y; gmn_y++, off += (80 - x) * 20) {
        gmn_x = ax;
        for ( ; gmn_x < ax + x; gmn_x++, off += 20) {
            %BREAK%
            if (gmn_x != axg || gmn_y != ayg) {
                a = cmap[off + 7]; b = cmap[off + 8];
                %STORE%
            }
        }
    }
    return gcount;
}
"""

decl_variants = {
    "ab": "unsigned char a; unsigned char b;",
    "ba": "unsigned char b; unsigned char a;",
}
break_variants = {
    "nobreak": "",
    "break6": "if (gcount >= 6) break;",
    "break6u": "if ((unsigned char)gcount >= 6) break;",
}
store_variants = {
    "inc": "if (a) { people[gcount] = a; gcount++; }\n                if (b) { people[gcount] = b; gcount++; }",
    "nlocal": "if (a) { int n = gcount; people[n] = a; gcount = n + 1; }\n                if (b) { int n = gcount; people[n] = b; gcount = n + 1; }",
}

for dn, dv in decl_variants.items():
    for bn, bv in break_variants.items():
        for sn, sv in store_variants.items():
            name = f"{dn}_{bn}_{sn}"
            body = HEAD.replace("%DECLS%", dv).replace("%BREAK%", bv).replace("%STORE%", sv)
            exp.add(name, GLOBALS + body, note=name)

if __name__ == "__main__":
    exp.run()
    for dn in decl_variants:
        for bn in break_variants:
            for sn in store_variants:
                t = f"{dn}_{bn}_{sn}"
                print(f"@@@ {t}")
                exp.print_trial(t)
