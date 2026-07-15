"""figure_images — RC uses callee-save EDX for index that PS clobbers EAX with.

PS:  imul eax, eax, 0x58     (clobbers figure_no in eax)
     cmp [eax + figure_list], 0
RC:  imul edx, eax, 0x58     (preserves eax for next iter)
     cmp [edx + figure_list], 0  (requires push edx prologue)

Probe whether Watcom can be coaxed into the eax-clobber form.
"""

from c2.commands.cgex import Experiment

_PRELUDE = """
struct fig_rec { char data[0x58]; };
extern int  figure_no;
extern struct fig_rec figure_list[];
"""

_DEFS = """
struct fig_rec { char data[0x58]; };
int figure_no;
struct fig_rec figure_list[201];
"""

exp = Experiment(
    name="figure_images",
    ps_function="figure_images",
    prelude=_PRELUDE,
    extra_defs=_DEFS,
    externs={
        "get_fig_still_image": "void get_fig_still_image(int n);",
    },
)


# ── trial 1: baseline (current source) ─────────────────────────
exp.add(
    "baseline-global",
    """
void figure_images(void)
{
    for (figure_no = 1; figure_no < 0xc9; figure_no++) {
        if (figure_list[figure_no].data[0] != 0) {
            get_fig_still_image(figure_no);
        }
    }
}
""",
    note="global figure_no as loop counter",
)


# ── trial 2: local counter, assign global before call ──────────
exp.add(
    "local-counter",
    """
void figure_images(void)
{
    int i;
    for (i = 1; i < 0xc9; i++) {
        if (figure_list[i].data[0] != 0) {
            figure_no = i;
            get_fig_still_image(i);
        }
    }
}
""",
    note="local int i — global only set before call",
)


# ── trial 3: arg-passes-figure_no (local i) ────────────────────
exp.add(
    "no-global-update",
    """
void figure_images(void)
{
    int i;
    for (i = 1; i < 0xc9; i++) {
        if (figure_list[i].data[0] != 0) {
            get_fig_still_image(i);
        }
    }
}
""",
    note="local i, no global update inside loop",
)


# ── trial 4: pointer increment ─────────────────────────────────
exp.add(
    "ptr-walk",
    """
void figure_images(void)
{
    struct fig_rec *p;
    figure_no = 1;
    for (p = &figure_list[1]; figure_no < 0xc9; p++, figure_no++) {
        if (p->data[0] != 0) {
            get_fig_still_image(figure_no);
        }
    }
}
""",
    note="pointer walk to avoid index multiply",
)


# ── trial 5: signed index (force int promotion) ────────────────
exp.add(
    "explicit-cast",
    """
void figure_images(void)
{
    for (figure_no = 1; figure_no < 0xc9; figure_no++) {
        if (figure_list[(int)figure_no].data[0] != 0) {
            get_fig_still_image(figure_no);
        }
    }
}
""",
    note="explicit (int) cast on index",
)
