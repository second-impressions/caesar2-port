"""copy_ferret_run_to_citizen — 4-bit packed step loop.

PS pattern (inner loop):

    xor eax, eax                ; i = 0
    xor ecx, ecx                ; j = 0
    jmp .test
  .body:
    mov bl, [ferret_run + i]    ; step (BL)
    test al, 1                  ; i & 1?
    jne .else
      mov [citizen_list[citizen_no].wf_steps + j], bl
      jmp .next
    .else:
      shl bl, 4
      add [citizen_list[citizen_no].wf_steps + j], bl
      inc ecx                   ; j++
    .next:
    inc eax
  .test:
    cmp eax, [ferret_run_length]
    jl .body

Key facts:

  * Step is cached in BL (callee-save).
  * j is in ECX (parm slot, normally arg4).
  * imul edx, citizen_no, 0x3A is repeated inside EACH branch.

Recomp pattern:

  * Step in CL, j in EBX — both flipped vs PS (Rule 28a whole-function
    swap).
  * stores via different base register (edx + ebx vs ecx + edx).

Goal: discover the source pattern that forces BL/ECX rather than
CL/EBX.  Hypotheses:

  1. Statement order of `j = 0; i = 0;` vs `i = 0; j = 0;` (Rule 79
    parallel-counter init order).
  2. Mutate-counter spelling (`j++` in else vs separate stmt).
  3. The cached-step temp's declaration scope/type.
  4. Inline `ferret_run[i]` instead of caching.
"""
from c2.commands.cgex import Experiment


_PRELUDE = r"""
struct century { unsigned char type, damaged, _u[2]; };
struct ferret_citizen {
    char _pad[0x11];
    char wf_active;       /* +0x11 */
    char wf_step;         /* +0x12 */
    char wf_length;       /* +0x13 */
    char wf_steps[8];     /* +0x14 */
    char _tail[0x1e];     /* +0x1c..+0x39 — total sizeof = 0x3A */
};
extern struct ferret_citizen citizen_list[];
extern short citizen_no;
extern int ferret_run_length;
extern char ferret_run[];
extern char w_dirc;
"""

_DEFS = r"""
struct ferret_citizen {
    char _pad[0x11];
    char wf_active;
    char wf_step;
    char wf_length;
    char wf_steps[8];
    char _tail[0x1e];
};
struct ferret_citizen citizen_list[64];
short citizen_no;
int ferret_run_length;
char ferret_run[64];
char w_dirc;
"""


exp = Experiment(
    name="copy_ferret_run_to_citizen",
    ps_function="copy_ferret_run_to_citizen",
    chk=True,
    prelude=_PRELUDE,
    extra_defs=_DEFS,
)


# ── baseline: current source after `char step` lever ──
exp.add("baseline", r"""
void copy_ferret_run_to_citizen(void)
{
    int i, j;

    citizen_list[citizen_no].wf_active = 1;
    citizen_list[citizen_no].wf_step = 0;
    citizen_list[citizen_no].wf_length = ferret_run_length;
    w_dirc = ferret_run[0];
    j = 0;
    for (i = 0; i < ferret_run_length; i++) {
        char step = ferret_run[i];
        if ((i & 1) == 0) {
            citizen_list[citizen_no].wf_steps[j] = step;
        } else {
            citizen_list[citizen_no].wf_steps[j] += step << 4;
            j++;
        }
    }
}
""", note="baseline (23 b diff)")


# ── A: swap j/i init order ──
exp.add("A_init_i_first", r"""
void copy_ferret_run_to_citizen(void)
{
    int i, j;

    citizen_list[citizen_no].wf_active = 1;
    citizen_list[citizen_no].wf_step = 0;
    citizen_list[citizen_no].wf_length = ferret_run_length;
    w_dirc = ferret_run[0];
    i = 0;
    j = 0;
    for (; i < ferret_run_length; i++) {
        char step = ferret_run[i];
        if ((i & 1) == 0) {
            citizen_list[citizen_no].wf_steps[j] = step;
        } else {
            citizen_list[citizen_no].wf_steps[j] += step << 4;
            j++;
        }
    }
}
""", note="A: i=0 before j=0 (Rule 79 init order)")


# ── B: while loop instead of for ──
exp.add("B_while", r"""
void copy_ferret_run_to_citizen(void)
{
    int i, j;

    citizen_list[citizen_no].wf_active = 1;
    citizen_list[citizen_no].wf_step = 0;
    citizen_list[citizen_no].wf_length = ferret_run_length;
    w_dirc = ferret_run[0];
    i = 0;
    j = 0;
    while (i < ferret_run_length) {
        char step = ferret_run[i];
        if ((i & 1) == 0) {
            citizen_list[citizen_no].wf_steps[j] = step;
        } else {
            citizen_list[citizen_no].wf_steps[j] += step << 4;
            j++;
        }
        i++;
    }
}
""", note="B: while-loop, i++ at bottom")


# ── C: while with j first ──
exp.add("C_while_j_first", r"""
void copy_ferret_run_to_citizen(void)
{
    int i, j;

    citizen_list[citizen_no].wf_active = 1;
    citizen_list[citizen_no].wf_step = 0;
    citizen_list[citizen_no].wf_length = ferret_run_length;
    w_dirc = ferret_run[0];
    j = 0;
    i = 0;
    while (i < ferret_run_length) {
        char step = ferret_run[i];
        if ((i & 1) == 0) {
            citizen_list[citizen_no].wf_steps[j] = step;
        } else {
            citizen_list[citizen_no].wf_steps[j] += step << 4;
            j++;
        }
        i++;
    }
}
""", note="C: while-loop, j=0 first")


# ── D: hoist step ABOVE the for loop ──
exp.add("D_step_hoisted", r"""
void copy_ferret_run_to_citizen(void)
{
    int i, j;
    char step;

    citizen_list[citizen_no].wf_active = 1;
    citizen_list[citizen_no].wf_step = 0;
    citizen_list[citizen_no].wf_length = ferret_run_length;
    w_dirc = ferret_run[0];
    j = 0;
    for (i = 0; i < ferret_run_length; i++) {
        step = ferret_run[i];
        if ((i & 1) == 0) {
            citizen_list[citizen_no].wf_steps[j] = step;
        } else {
            citizen_list[citizen_no].wf_steps[j] += step << 4;
            j++;
        }
    }
}
""", note="D: hoist `char step` declaration above loop")


# ── E: char j ──
exp.add("E_char_j", r"""
void copy_ferret_run_to_citizen(void)
{
    int i;
    char j;

    citizen_list[citizen_no].wf_active = 1;
    citizen_list[citizen_no].wf_step = 0;
    citizen_list[citizen_no].wf_length = ferret_run_length;
    w_dirc = ferret_run[0];
    j = 0;
    for (i = 0; i < ferret_run_length; i++) {
        char step = ferret_run[i];
        if ((i & 1) == 0) {
            citizen_list[citizen_no].wf_steps[j] = step;
        } else {
            citizen_list[citizen_no].wf_steps[j] += step << 4;
            j++;
        }
    }
}
""", note="E: j is `char` not `int`")


# ── F: pre-increment vs post-increment ──
exp.add("F_pre_inc", r"""
void copy_ferret_run_to_citizen(void)
{
    int i, j;

    citizen_list[citizen_no].wf_active = 1;
    citizen_list[citizen_no].wf_step = 0;
    citizen_list[citizen_no].wf_length = ferret_run_length;
    w_dirc = ferret_run[0];
    j = 0;
    for (i = 0; i < ferret_run_length; ++i) {
        char step = ferret_run[i];
        if ((i & 1) == 0) {
            citizen_list[citizen_no].wf_steps[j] = step;
        } else {
            citizen_list[citizen_no].wf_steps[j] += step << 4;
            ++j;
        }
    }
}
""", note="F: pre-increment everywhere")


# ── G: explicit step << 4 in else, with else-first ordering ──
exp.add("G_else_first", r"""
void copy_ferret_run_to_citizen(void)
{
    int i, j;

    citizen_list[citizen_no].wf_active = 1;
    citizen_list[citizen_no].wf_step = 0;
    citizen_list[citizen_no].wf_length = ferret_run_length;
    w_dirc = ferret_run[0];
    j = 0;
    for (i = 0; i < ferret_run_length; i++) {
        char step = ferret_run[i];
        if ((i & 1) != 0) {
            citizen_list[citizen_no].wf_steps[j] += step << 4;
            j++;
        } else {
            citizen_list[citizen_no].wf_steps[j] = step;
        }
    }
}
""", note="G: flip if/else direction (odd branch first)")


# ── H: split j++ from else body ──
exp.add("H_j_step_split", r"""
void copy_ferret_run_to_citizen(void)
{
    int i, j;

    citizen_list[citizen_no].wf_active = 1;
    citizen_list[citizen_no].wf_step = 0;
    citizen_list[citizen_no].wf_length = ferret_run_length;
    w_dirc = ferret_run[0];
    j = 0;
    for (i = 0; i < ferret_run_length; i++) {
        char step = ferret_run[i];
        if ((i & 1) == 0) {
            citizen_list[citizen_no].wf_steps[j] = step;
        } else {
            citizen_list[citizen_no].wf_steps[j] = citizen_list[citizen_no].wf_steps[j] + (step << 4);
            j++;
        }
    }
}
""", note="H: explicit + instead of += in else")


# ── I: int step (wider type) ──
exp.add("I_int_step", r"""
void copy_ferret_run_to_citizen(void)
{
    int i, j;

    citizen_list[citizen_no].wf_active = 1;
    citizen_list[citizen_no].wf_step = 0;
    citizen_list[citizen_no].wf_length = ferret_run_length;
    w_dirc = ferret_run[0];
    j = 0;
    for (i = 0; i < ferret_run_length; i++) {
        int step = ferret_run[i];
        if ((i & 1) == 0) {
            citizen_list[citizen_no].wf_steps[j] = step;
        } else {
            citizen_list[citizen_no].wf_steps[j] += step << 4;
            j++;
        }
    }
}
""", note="I: int step instead of char")


# ── J: inline ferret_run[i] (no temp) ──
exp.add("J_no_temp", r"""
void copy_ferret_run_to_citizen(void)
{
    int i, j;

    citizen_list[citizen_no].wf_active = 1;
    citizen_list[citizen_no].wf_step = 0;
    citizen_list[citizen_no].wf_length = ferret_run_length;
    w_dirc = ferret_run[0];
    j = 0;
    for (i = 0; i < ferret_run_length; i++) {
        if ((i & 1) == 0) {
            citizen_list[citizen_no].wf_steps[j] = ferret_run[i];
        } else {
            citizen_list[citizen_no].wf_steps[j] += ferret_run[i] << 4;
            j++;
        }
    }
}
""", note="J: no temp, inline ferret_run[i] both branches (original)")


# ── K: cached citizen pointer ──
exp.add("K_cached_ptr", r"""
void copy_ferret_run_to_citizen(void)
{
    int i, j;
    struct ferret_citizen *cz = &citizen_list[citizen_no];

    cz->wf_active = 1;
    cz->wf_step = 0;
    cz->wf_length = ferret_run_length;
    w_dirc = ferret_run[0];
    j = 0;
    for (i = 0; i < ferret_run_length; i++) {
        char step = ferret_run[i];
        if ((i & 1) == 0) {
            cz->wf_steps[j] = step;
        } else {
            cz->wf_steps[j] += step << 4;
            j++;
        }
    }
}
""", note="K: cache &citizen_list[citizen_no] in local pointer")


# ── L: j incremented every iter with /2 indexing ──
exp.add("L_no_separate_j", r"""
void copy_ferret_run_to_citizen(void)
{
    int i;
    char step;

    citizen_list[citizen_no].wf_active = 1;
    citizen_list[citizen_no].wf_step = 0;
    citizen_list[citizen_no].wf_length = ferret_run_length;
    w_dirc = ferret_run[0];
    for (i = 0; i < ferret_run_length; i++) {
        step = ferret_run[i];
        if ((i & 1) == 0) {
            citizen_list[citizen_no].wf_steps[i >> 1] = step;
        } else {
            citizen_list[citizen_no].wf_steps[i >> 1] += step << 4;
        }
    }
}
""", note="L: derive j from i (no separate counter)")


# ── M: process pairs (i = j*2, j outer) ──
exp.add("M_pair_outer", r"""
void copy_ferret_run_to_citizen(void)
{
    int j;

    citizen_list[citizen_no].wf_active = 1;
    citizen_list[citizen_no].wf_step = 0;
    citizen_list[citizen_no].wf_length = ferret_run_length;
    w_dirc = ferret_run[0];
    for (j = 0; j*2 < ferret_run_length; j++) {
        citizen_list[citizen_no].wf_steps[j] = ferret_run[j*2];
        if (j*2+1 < ferret_run_length)
            citizen_list[citizen_no].wf_steps[j] += ferret_run[j*2+1] << 4;
    }
}
""", note="M: pair-wise outer j loop")


# ── N: int step (Watcom may treat int storage differently) ──
exp.add("N_int_step", r"""
void copy_ferret_run_to_citizen(void)
{
    int i, j;
    int step;

    citizen_list[citizen_no].wf_active = 1;
    citizen_list[citizen_no].wf_step = 0;
    citizen_list[citizen_no].wf_length = ferret_run_length;
    w_dirc = ferret_run[0];
    i = 0;
    j = 0;
    for (; i < ferret_run_length; i++) {
        step = ferret_run[i];
        if ((i & 1) == 0) {
            citizen_list[citizen_no].wf_steps[j] = step;
        } else {
            citizen_list[citizen_no].wf_steps[j] += step << 4;
            j++;
        }
    }
}
""", note="N: int step (was 'char step')")


# ── O: unsigned char step ──
exp.add("O_uchar_step", r"""
void copy_ferret_run_to_citizen(void)
{
    int i, j;
    unsigned char step;

    citizen_list[citizen_no].wf_active = 1;
    citizen_list[citizen_no].wf_step = 0;
    citizen_list[citizen_no].wf_length = ferret_run_length;
    w_dirc = ferret_run[0];
    i = 0;
    j = 0;
    for (; i < ferret_run_length; i++) {
        step = ferret_run[i];
        if ((i & 1) == 0) {
            citizen_list[citizen_no].wf_steps[j] = step;
        } else {
            citizen_list[citizen_no].wf_steps[j] += step << 4;
            j++;
        }
    }
}
""", note="O: unsigned char step")


# ── P: dummy reference to step in even branch ──
exp.add("P_dummy_use", r"""
void copy_ferret_run_to_citizen(void)
{
    int i, j;
    char step;

    citizen_list[citizen_no].wf_active = 1;
    citizen_list[citizen_no].wf_step = 0;
    citizen_list[citizen_no].wf_length = ferret_run_length;
    w_dirc = ferret_run[0];
    i = 0;
    j = 0;
    for (; i < ferret_run_length; i++) {
        step = ferret_run[i];
        if ((i & 1) == 0) {
            citizen_list[citizen_no].wf_steps[j] = step;
            step = step;  /* keep alive across branch */
        } else {
            citizen_list[citizen_no].wf_steps[j] += step << 4;
            j++;
        }
    }
}
""", note="P: redundant step = step at end of even branch")


# ── Q: do-while loop ──
exp.add("Q_do_while", r"""
void copy_ferret_run_to_citizen(void)
{
    int i, j;
    char step;

    citizen_list[citizen_no].wf_active = 1;
    citizen_list[citizen_no].wf_step = 0;
    citizen_list[citizen_no].wf_length = ferret_run_length;
    w_dirc = ferret_run[0];
    if (ferret_run_length <= 0) return;
    i = 0;
    j = 0;
    do {
        step = ferret_run[i];
        if ((i & 1) == 0) {
            citizen_list[citizen_no].wf_steps[j] = step;
        } else {
            citizen_list[citizen_no].wf_steps[j] += step << 4;
            j++;
        }
        i++;
    } while (i < ferret_run_length);
}
""", note="Q: do-while loop")


# ── R: step declared as parm-like alias to force regalloc ──
exp.add("R_step_indirect", r"""
void copy_ferret_run_to_citizen(void)
{
    int i, j;
    char step, step_alias;

    citizen_list[citizen_no].wf_active = 1;
    citizen_list[citizen_no].wf_step = 0;
    citizen_list[citizen_no].wf_length = ferret_run_length;
    w_dirc = ferret_run[0];
    i = 0;
    j = 0;
    for (; i < ferret_run_length; i++) {
        step_alias = ferret_run[i];
        step = step_alias;
        if ((i & 1) == 0) {
            citizen_list[citizen_no].wf_steps[j] = step;
        } else {
            citizen_list[citizen_no].wf_steps[j] += step << 4;
            j++;
        }
    }
}
""", note="R: Rule 24c-style alias")


# ── S: separate sequential branches (no nested if) ──
exp.add("S_split_loops", r"""
void copy_ferret_run_to_citizen(void)
{
    int i, j;
    char step;

    citizen_list[citizen_no].wf_active = 1;
    citizen_list[citizen_no].wf_step = 0;
    citizen_list[citizen_no].wf_length = ferret_run_length;
    w_dirc = ferret_run[0];
    j = 0;
    for (i = 0; i < ferret_run_length; i += 2) {
        step = ferret_run[i];
        citizen_list[citizen_no].wf_steps[j] = step;
        if (i + 1 < ferret_run_length) {
            step = ferret_run[i + 1];
            citizen_list[citizen_no].wf_steps[j] += step << 4;
        }
        j++;
    }
}
""", note="S: step over pairs, single body")


# ── T: explicit signed char (matches ferret_run elt type) ──
exp.add("T_signed_char", r"""
void copy_ferret_run_to_citizen(void)
{
    int i, j;
    signed char step;

    citizen_list[citizen_no].wf_active = 1;
    citizen_list[citizen_no].wf_step = 0;
    citizen_list[citizen_no].wf_length = ferret_run_length;
    w_dirc = ferret_run[0];
    i = 0;
    j = 0;
    for (; i < ferret_run_length; i++) {
        step = ferret_run[i];
        if ((i & 1) == 0) {
            citizen_list[citizen_no].wf_steps[j] = step;
        } else {
            citizen_list[citizen_no].wf_steps[j] += step << 4;
            j++;
        }
    }
}
""", note="T: signed char")


# ── U: rearrange step << 4 as 16 * step ──
exp.add("U_mul16", r"""
void copy_ferret_run_to_citizen(void)
{
    int i, j;
    char step;

    citizen_list[citizen_no].wf_active = 1;
    citizen_list[citizen_no].wf_step = 0;
    citizen_list[citizen_no].wf_length = ferret_run_length;
    w_dirc = ferret_run[0];
    i = 0;
    j = 0;
    for (; i < ferret_run_length; i++) {
        step = ferret_run[i];
        if ((i & 1) == 0) {
            citizen_list[citizen_no].wf_steps[j] = step;
        } else {
            citizen_list[citizen_no].wf_steps[j] += 16 * step;
            j++;
        }
    }
}
""", note="U: 16*step instead of step<<4")


# ── W: hoist imul invariant outside loop ──
exp.add("W_hoist_imul", r"""
void copy_ferret_run_to_citizen(void)
{
    int i, j, off;
    char step;

    citizen_list[citizen_no].wf_active = 1;
    citizen_list[citizen_no].wf_step = 0;
    citizen_list[citizen_no].wf_length = ferret_run_length;
    w_dirc = ferret_run[0];
    off = citizen_no * 0x3a;
    i = 0;
    j = 0;
    for (; i < ferret_run_length; i++) {
        step = ferret_run[i];
        if ((i & 1) == 0) {
            ((char *)citizen_list)[off + 0x14 + j] = step;
        } else {
            ((char *)citizen_list)[off + 0x14 + j] += step << 4;
            j++;
        }
    }
}
""", note="W: hoist citizen_no*0x3a, address via byte ptr")


# ── X: hoist wf_steps row pointer ──
exp.add("X_row_ptr", r"""
void copy_ferret_run_to_citizen(void)
{
    int i, j;
    char step;
    char *row;

    citizen_list[citizen_no].wf_active = 1;
    citizen_list[citizen_no].wf_step = 0;
    citizen_list[citizen_no].wf_length = ferret_run_length;
    w_dirc = ferret_run[0];
    row = citizen_list[citizen_no].wf_steps;
    i = 0;
    j = 0;
    for (; i < ferret_run_length; i++) {
        step = ferret_run[i];
        if ((i & 1) == 0) {
            row[j] = step;
        } else {
            row[j] += step << 4;
            j++;
        }
    }
}
""", note="X: hoist wf_steps row pointer")


# ── Y: process i AND i+1 together inside even branch ──
exp.add("Y_dual_branch", r"""
void copy_ferret_run_to_citizen(void)
{
    int i, j;
    char step;

    citizen_list[citizen_no].wf_active = 1;
    citizen_list[citizen_no].wf_step = 0;
    citizen_list[citizen_no].wf_length = ferret_run_length;
    w_dirc = ferret_run[0];
    i = 0;
    j = 0;
    for (; i < ferret_run_length; i++) {
        step = ferret_run[i];
        if ((i & 1) == 0)
            citizen_list[citizen_no].wf_steps[j] = step;
        else {
            citizen_list[citizen_no].wf_steps[j] = (char)(citizen_list[citizen_no].wf_steps[j] | (step << 4));
            j++;
        }
    }
}
""", note="Y: use | instead of +=")


# ── Z: post-increment j after write (with j pre-init -1) ──
exp.add("Z_j_after_even", r"""
void copy_ferret_run_to_citizen(void)
{
    int i, j;
    char step;

    citizen_list[citizen_no].wf_active = 1;
    citizen_list[citizen_no].wf_step = 0;
    citizen_list[citizen_no].wf_length = ferret_run_length;
    w_dirc = ferret_run[0];
    i = 0;
    j = 0;
    for (; i < ferret_run_length; i++) {
        step = ferret_run[i];
        if ((i & 1) != 0) {
            citizen_list[citizen_no].wf_steps[j] += step << 4;
            j++;
            continue;
        }
        citizen_list[citizen_no].wf_steps[j] = step;
    }
}
""", note="Z: continue in odd branch, fall-through even")


# ── AA: explicit register hint via auto─alias for step ──
exp.add("AA_step_first_assign", r"""
void copy_ferret_run_to_citizen(void)
{
    int i, j;
    char step = 0;

    citizen_list[citizen_no].wf_active = 1;
    citizen_list[citizen_no].wf_step = step;       /* use step as 0 source */
    citizen_list[citizen_no].wf_length = ferret_run_length;
    w_dirc = ferret_run[0];
    i = 0;
    j = 0;
    for (; i < ferret_run_length; i++) {
        step = ferret_run[i];
        if ((i & 1) == 0) {
            citizen_list[citizen_no].wf_steps[j] = step;
        } else {
            citizen_list[citizen_no].wf_steps[j] += step << 4;
            j++;
        }
    }
}
""", note="AA: prime step=0 used for wf_step write (lifts BL across prelude)")


# ── V: j++ before write in else ──
exp.add("V_j_pre", r"""
void copy_ferret_run_to_citizen(void)
{
    int i, j;
    char step;

    citizen_list[citizen_no].wf_active = 1;
    citizen_list[citizen_no].wf_step = 0;
    citizen_list[citizen_no].wf_length = ferret_run_length;
    w_dirc = ferret_run[0];
    i = 0;
    j = -1;
    for (; i < ferret_run_length; i++) {
        step = ferret_run[i];
        if ((i & 1) == 0) {
            j++;
            citizen_list[citizen_no].wf_steps[j] = step;
        } else {
            citizen_list[citizen_no].wf_steps[j] += step << 4;
        }
    }
}
""", note="V: j++ in even branch (before write)")
