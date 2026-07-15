"""putting_out_fire — Z1to4 byte-load idiom: mov+and vs xor+mov.

PS uses `mov dl, [m]; and edx, 0xff` form (rCLRHI_R "and-form") for
the kind read.  RC uses `xor edx, edx; mov dl, [m]` (rCLRHI_R
"clear-first" form), shorter by 4 b which cascades 64 b of diff
through the rest of the body.

The split routine is /tmp/ow110/bld/cg/c/split.c rCLRHI_R; the
choice between the two forms depends on operand-overlap conditions
at split time which themselves depend on regalloc scheduling.
Sibling confirm_fire_target (right below) uses the same C-source
shape `if (CM_KIND(ref) < 8) ... if ((CM_EDGE_BITS(ref) & 0x80) ...)`
and emits the clear-first form (xor;mov), and it is byte-exact.

The difference between the two functions: putting_out_fire reuses
the **same register (EDX)** for kind, edge, fire — three byte
reloads.  confirm_fire_target spreads them across EDX and EAX.
Test whether forcing a separate int variable and explicit reuse
pushes Watcom into the and-form.
"""
from c2.commands.cgex import Experiment

_PRELUDE = r"""
extern unsigned char city_map[];
struct citizen_rec {
    char pad00[6];
    int  map_ref;     /* +0x6 */
    char pad0A[44];   /* total 0x3A */
};
extern struct citizen_rec citizen_list[];
extern short citizen_no;

#define CM_KIND(p)       city_map[(p)]
#define CM_EDGE_BITS(p)  city_map[(p) + 3]
#define CM_FIRE(p)       city_map[(p) + 0x10]
"""
_DEFS = _PRELUDE + r"""
unsigned char city_map[80*80*20];
struct citizen_rec citizen_list[201];
short citizen_no;
"""

exp = Experiment(
    name="putting_out_fire",
    ps_function="putting_out_fire",
    chk=False,
    prelude=_PRELUDE,
    extra_defs=_DEFS,
)

exp.add("baseline", r"""
int putting_out_fire(void)
{
    int ref;

    ref = citizen_list[citizen_no].map_ref;
    if (CM_KIND(ref) < 8
     && (CM_EDGE_BITS(ref) & 0x80) != 0) {
        unsigned char f = CM_FIRE(ref);
        if (--f != 0)
            CM_FIRE(ref)--;
        else
            CM_EDGE_BITS(ref) &= 0x7f;
        return 1;
    }
    return 0;
}
""", note="current source — xor;mov form (64 b diff)")

exp.add("reused_int", r"""
int putting_out_fire(void)
{
    int ref;
    int x;

    ref = citizen_list[citizen_no].map_ref;
    x = CM_KIND(ref);
    if (x < 8) {
        x = CM_EDGE_BITS(ref) & 0x80;
        if (x != 0) {
            x = CM_FIRE(ref);
            if (--x != 0) CM_FIRE(ref)--;
            else CM_EDGE_BITS(ref) &= 0x7f;
            return 1;
        }
    }
    return 0;
}
""", note="reuse one int variable across all byte reads")

exp.add("reused_uchar", r"""
int putting_out_fire(void)
{
    int ref;
    unsigned char x;

    ref = citizen_list[citizen_no].map_ref;
    x = CM_KIND(ref);
    if (x < 8) {
        x = CM_EDGE_BITS(ref);
        if ((x & 0x80) != 0) {
            x = CM_FIRE(ref);
            if (--x != 0) CM_FIRE(ref)--;
            else CM_EDGE_BITS(ref) &= 0x7f;
            return 1;
        }
    }
    return 0;
}
""", note="reuse one unsigned char variable")

exp.add("nested_if_no_short_circuit", r"""
int putting_out_fire(void)
{
    int ref;

    ref = citizen_list[citizen_no].map_ref;
    if (CM_KIND(ref) < 8) {
        if ((CM_EDGE_BITS(ref) & 0x80) != 0) {
            unsigned char f = CM_FIRE(ref);
            if (--f != 0) CM_FIRE(ref)--;
            else CM_EDGE_BITS(ref) &= 0x7f;
            return 1;
        }
    }
    return 0;
}
""", note="nested if instead of &&")

exp.add("early_return", r"""
int putting_out_fire(void)
{
    int ref;
    unsigned char f;

    ref = citizen_list[citizen_no].map_ref;
    if (CM_KIND(ref) >= 8) return 0;
    if ((CM_EDGE_BITS(ref) & 0x80) == 0) return 0;
    f = CM_FIRE(ref);
    if (--f != 0) CM_FIRE(ref)--;
    else CM_EDGE_BITS(ref) &= 0x7f;
    return 1;
}
""", note="early returns (matches confirm_fire_target shape)")

exp.add("reused_uchar_early_return", r"""
int putting_out_fire(void)
{
    int ref;
    unsigned char x;

    ref = citizen_list[citizen_no].map_ref;
    x = CM_KIND(ref);
    if (x >= 8) return 0;
    x = CM_EDGE_BITS(ref);
    if ((x & 0x80) == 0) return 0;
    x = CM_FIRE(ref);
    if (--x != 0) CM_FIRE(ref)--;
    else CM_EDGE_BITS(ref) &= 0x7f;
    return 1;
}
""", note="reused uchar + early returns")

exp.add("reused_int_early_return", r"""
int putting_out_fire(void)
{
    int ref;
    int x;

    ref = citizen_list[citizen_no].map_ref;
    x = CM_KIND(ref);
    if (x >= 8) return 0;
    x = CM_EDGE_BITS(ref);
    if ((x & 0x80) == 0) return 0;
    x = CM_FIRE(ref);
    if (--x != 0) CM_FIRE(ref)--;
    else CM_EDGE_BITS(ref) &= 0x7f;
    return 1;
}
""", note="reused int + early returns")
