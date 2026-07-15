"""entering_new_square — 2-byte Rule 4 (R,R) cmp-direction residue.

PS `entering_new_square` (98 b @ 0x4944A) emits, at the threshold test:

    movsx ebx, byte ptr [eax + 0x846dc]   ; ebx = target_count
    cmp   ebx, edx                        ; edx = threshold
    jl    <return 0>

Our faithful body `if (threshold <= army_list[army_no].target_count ...)`
emits the same registers (target_count=EBX, threshold=EDX) but the
*opposite* operand order + reversed condition:

    cmp   edx, ebx
    jg    <return 0>

Same semantics, 2 bytes apart (Rule 4).  PS places target_count as cmp
op0; the natural codegen of `threshold <= cnt` places threshold as op0.
Writing `cnt >= threshold` flips the cmp order the right way but ALSO
swaps the register identity (creation-order H2 tie) → regresses.

Goal: find a source form that yields `cmp ebx,edx; jl` with
target_count=EBX, threshold=EDX.

Run::

    uv run c2 cgex run entering_new_square
"""

from c2.commands.cgex import Experiment

_PRELUDE = """
struct army_rec {
    char         pad0[0x23];
    signed char  target_kind;    /* +0x23 */
    signed char  target_count;   /* +0x24 */
    signed char  flags;          /* +0x25 */
    char         pad1;           /* +0x26 */
    char         target_flag;    /* +0x27 */
    char         pad2[0xaf - 0x28];
};
extern struct army_rec army_list[];
extern short army_no;
"""

_DEFS = _PRELUDE + """
struct army_rec army_list[300];
short army_no;
"""

exp = Experiment(
    name="entering_new_square",
    ps_function="entering_new_square",
    prelude=_PRELUDE,
    extra_defs=_DEFS,
)

exp.add(
    "baseline",
    """
int entering_new_square(void)
{
    int threshold;
    if ((army_list[army_no].flags & 1) != 0) return 1;
    threshold = 1 + (army_list[army_no].target_flag == 0);
    if (threshold <= army_list[army_no].target_count
     && army_list[army_no].target_kind >= 15)
        return 1;
    return 0;
}
""",
    note="current faithful body — cmp edx,ebx; jg (2b off)",
)

exp.add(
    "cnt-ge-threshold",
    """
int entering_new_square(void)
{
    int threshold;
    if ((army_list[army_no].flags & 1) != 0) return 1;
    threshold = 1 + (army_list[army_no].target_flag == 0);
    if (army_list[army_no].target_count >= threshold
     && army_list[army_no].target_kind >= 15)
        return 1;
    return 0;
}
""",
    note="cnt first — flips cmp order, may swap regs",
)

exp.add(
    "cnt-temp",
    """
int entering_new_square(void)
{
    int threshold;
    int cnt;
    if ((army_list[army_no].flags & 1) != 0) return 1;
    threshold = 1 + (army_list[army_no].target_flag == 0);
    cnt = army_list[army_no].target_count;
    if (cnt >= threshold
     && army_list[army_no].target_kind >= 15)
        return 1;
    return 0;
}
""",
    note="cnt materialised into its own temp before the test",
)

exp.add(
    "cnt-temp-decl-first",
    """
int entering_new_square(void)
{
    int cnt;
    int threshold;
    if ((army_list[army_no].flags & 1) != 0) return 1;
    threshold = 1 + (army_list[army_no].target_flag == 0);
    cnt = army_list[army_no].target_count;
    if (cnt >= threshold
     && army_list[army_no].target_kind >= 15)
        return 1;
    return 0;
}
""",
    note="cnt declared first (creation-order perturb)",
)

exp.add(
    "not-cnt-lt",
    """
int entering_new_square(void)
{
    int threshold;
    if ((army_list[army_no].flags & 1) != 0) return 1;
    threshold = 1 + (army_list[army_no].target_flag == 0);
    if (!(army_list[army_no].target_count < threshold)
     && army_list[army_no].target_kind >= 15)
        return 1;
    return 0;
}
""",
    note="explicit !(cnt < threshold)",
)


# ── creation-order perturbations: keep cnt as cmp op0, try to flip
#    the register priority so cnt→EBX, threshold→EDX (PS layout) ──

exp.add(
    "threshold-split-incr",
    """
int entering_new_square(void)
{
    int threshold;
    if ((army_list[army_no].flags & 1) != 0) return 1;
    threshold = (army_list[army_no].target_flag == 0);
    threshold += 1;
    if (army_list[army_no].target_count >= threshold
     && army_list[army_no].target_kind >= 15)
        return 1;
    return 0;
}
""",
    note="threshold built in two statements",
)

exp.add(
    "and-order-swap",
    """
int entering_new_square(void)
{
    int threshold;
    if ((army_list[army_no].flags & 1) != 0) return 1;
    threshold = 1 + (army_list[army_no].target_flag == 0);
    if (army_list[army_no].target_kind >= 15
     && army_list[army_no].target_count >= threshold)
        return 1;
    return 0;
}
""",
    note="kind test first in the &&",
)

exp.add(
    "threshold-after-flag-temp",
    """
int entering_new_square(void)
{
    int threshold;
    int flag0;
    if ((army_list[army_no].flags & 1) != 0) return 1;
    flag0 = (army_list[army_no].target_flag == 0);
    threshold = 1 + flag0;
    if (army_list[army_no].target_count >= threshold
     && army_list[army_no].target_kind >= 15)
        return 1;
    return 0;
}
""",
    note="extra flag0 temp before threshold",
)

exp.add(
    "cnt-not-lt",
    """
int entering_new_square(void)
{
    int threshold;
    if ((army_list[army_no].flags & 1) != 0) return 1;
    threshold = 1 + (army_list[army_no].target_flag == 0);
    if (army_list[army_no].target_count >= threshold)
        if (army_list[army_no].target_kind >= 15)
            return 1;
    return 0;
}
""",
    note="nested ifs instead of &&",
)


exp.add(
    "cnt-before-threshold",
    """
int entering_new_square(void)
{
    int cnt;
    int threshold;
    if ((army_list[army_no].flags & 1) != 0) return 1;
    cnt = army_list[army_no].target_count;
    threshold = 1 + (army_list[army_no].target_flag == 0);
    if (cnt >= threshold
     && army_list[army_no].target_kind >= 15)
        return 1;
    return 0;
}
""",
    note="cnt loaded before threshold computed",
)

exp.add(
    "cnt-before-thr-le",
    """
int entering_new_square(void)
{
    int cnt;
    int threshold;
    if ((army_list[army_no].flags & 1) != 0) return 1;
    cnt = army_list[army_no].target_count;
    threshold = 1 + (army_list[army_no].target_flag == 0);
    if (threshold <= cnt
     && army_list[army_no].target_kind >= 15)
        return 1;
    return 0;
}
""",
    note="cnt before threshold, le form",
)


exp.add(
    "thr-eq-rev-cnt-first",
    """
int entering_new_square(void)
{
    int threshold;
    if ((army_list[army_no].flags & 1) != 0) return 1;
    threshold = (army_list[army_no].target_flag == 0) + 1;
    if (army_list[army_no].target_count >= threshold
     && army_list[army_no].target_kind >= 15)
        return 1;
    return 0;
}
""",
    note="(flag==0)+1, cnt first",
)

exp.add(
    "thr-eq-rev-le",
    """
int entering_new_square(void)
{
    int threshold;
    if ((army_list[army_no].flags & 1) != 0) return 1;
    threshold = (army_list[army_no].target_flag == 0) + 1;
    if (threshold <= army_list[army_no].target_count
     && army_list[army_no].target_kind >= 15)
        return 1;
    return 0;
}
""",
    note="(flag==0)+1, le form",
)

exp.add(
    "flag0-flip",
    """
int entering_new_square(void)
{
    int threshold;
    if ((army_list[army_no].flags & 1) != 0) return 1;
    threshold = 1 + (0 == army_list[army_no].target_flag);
    if (army_list[army_no].target_count >= threshold
     && army_list[army_no].target_kind >= 15)
        return 1;
    return 0;
}
""",
    note="0==flag, cnt first",
)


exp.add(
    "sub-ge-zero",
    """
int entering_new_square(void)
{
    int threshold;
    if ((army_list[army_no].flags & 1) != 0) return 1;
    threshold = 1 + (army_list[army_no].target_flag == 0);
    if (army_list[army_no].target_count - threshold >= 0
     && army_list[army_no].target_kind >= 15)
        return 1;
    return 0;
}
""",
    note="cnt - threshold >= 0",
)

exp.add(
    "gt-minus-one",
    """
int entering_new_square(void)
{
    int threshold;
    if ((army_list[army_no].flags & 1) != 0) return 1;
    threshold = (army_list[army_no].target_flag == 0);
    if (army_list[army_no].target_count > threshold
     && army_list[army_no].target_kind >= 15)
        return 1;
    return 0;
}
""",
    note="cnt > (flag==0)  [== cnt >= threshold, threshold folded]",
)
