"""Probe: memset(p, 0, N) inlining to bare __STOSB call.

PS init_help_history (0x58907) emits:

    push ecx; push edx
    mov eax, [first_help_page]
    mov [this_help_page], eax
    xor edx, edx
    mov [this_help_action], edx
    mov ecx, 0x190
    mov eax, help_history
    call __STOSB                  ← count in ecx, no broadcast preamble
    pop edx; pop ecx; ret

Our default build (with `memset()` as source) emits the same shape but
saves/uses `ebx` instead of `ecx` for the count register — Watcom's
__watcall passes the 3rd int arg of memset() in ebx and resolves the
call to `memset` (the lib symbol), not `__STOSB`.

Goal: find a flag/pragma combination where Watcom inlines memset to
the bare __STOSB call (count in ecx) when val=0 and the surrounding
code has already zeroed edx.

Run with::

    uv run c2 cgex run memset_init_help
"""

from c2.commands.cgex import Experiment

exp = Experiment(
    name="memset_init_help",
    ps_function="init_help_history",
    chk=False,
    need_clib3r=True,
    extra_defs="""
int first_help_page;
int this_help_page;
int this_help_action;
char help_history[0x190];
""",
)

BODY = """
#include <string.h>
extern int first_help_page;
extern int this_help_page;
extern int this_help_action;
extern char help_history[0x190];

void init_help_history(void)
{
    this_help_page = first_help_page;
    this_help_action = 0;
    memset(help_history, 0, 0x190);
}
"""

# ── trial 1: baseline (default cflags, no pragma) ──────────────
exp.add("baseline", BODY)

# ── trial 2: -oi added ──────────────
exp.add("oi", BODY, cflags="-bt=dos -mf -4r -s -oi")

# ── trial 3: pragma intrinsic(memset) ──────────────
exp.add("pragma_intrinsic", "#pragma intrinsic(memset)\n" + BODY)

# ── trial 4: pragma intrinsic + -oi ──────────────
exp.add(
    "pragma_intrinsic_oi",
    "#pragma intrinsic(memset)\n" + BODY,
    cflags="-bt=dos -mf -4r -s -oi",
)

# ── trial 5: -oi + -ol (loop opts) ──────────────
exp.add("oi_ol", BODY, cflags="-bt=dos -mf -4r -s -oi -ol")

# ── trial 6: -oi + -oh (super-optimal regalloc) ──────────────
exp.add("oi_oh", BODY, cflags="-bt=dos -mf -4r -s -oi -oh")

# ── trial 7: -oi + -ot (optimise time) ──────────────
exp.add("oi_ot", BODY, cflags="-bt=dos -mf -4r -s -oi -ot")

# ── trial 8: -oi + -os (optimise size) ──────────────
exp.add("oi_os", BODY, cflags="-bt=dos -mf -4r -s -oi -os")

# ── trial 9: __INLINE_FUNCTIONS__ defined manually ──────────────
exp.add(
    "inline_macro",
    "#define __INLINE_FUNCTIONS__ 1\n" + BODY,
)

# ── trial 10: include xstring.h via -fi ──────────────
exp.add("inline_macro_oi", "#define __INLINE_FUNCTIONS__ 1\n" + BODY,
        cflags="-bt=dos -mf -4r -s -oi")
