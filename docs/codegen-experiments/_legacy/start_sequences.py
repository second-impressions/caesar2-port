"""start_sequences — the W107 far-pointer retval funnel (open question).

PS @ 0x118A2 (217 b) returns `char __far *` with THREE value sites:
  install-fail  -> (char __far *)1         [xor edx,edx; mov eax,1]
  handle-null   -> (char __far *)MK_FP(1,2) [mov edx,1; mov eax,2]  (inside a loop)
  guard/success -> fall to a VALUE-FREE bare epilogue (eax undefined; W107)

PS writes edx:eax PER SITE and jmps to a bare `pop ebp; jmp <shared>`
(the return-1 copy is the kept ComTail instance; the others back-jump).

Our recomp FUNNELS: it holds the retval in callee-saves esi:edi and
homes `mov edx,edi; mov eax,esi` at one exit (the W107 join read keeps
the value live across the allocate-loop calls -> callee-save).  113 b.

This sweep probes which source shape suppresses the funnel (makes
Watcom write edx:eax per site).  cgex builds in isolation, so the
epilogue won't tail-merge (absolute diff floor is nonzero); the SIGNAL
is the per-trial disasm: look for `xor edx,edx; mov eax,1` (GOOD,
per-site) vs `mov esi,1 ... mov eax,esi` (BAD, funnel).

Run:
    uv run c2 cgex run start_sequences
    uv run c2 cgex run start_sequences --trial baseline   # dump asm
"""

from c2.commands.cgex import Experiment

_GLOBALS = """
struct c2inf_rec { char pad0[13]; char tunes_on; char pad1[46]; };
extern struct c2inf_rec c2inf;
extern int sequences_running;
extern int mdi;
extern int ms;
extern int S_mdi[];
extern int tune1;
extern int tune2;
extern int tune_mood;
extern int tune_branch_count;
extern int last_battle_mood;
extern int last_city_mood;

#pragma aux _AIL_set_GTL_filename_prefix "*" parm caller [] modify [eax ebx ecx edx]
#pragma aux _AIL_install_MDI_INI         "*" parm caller [] modify [eax ebx ecx edx]
#pragma aux _AIL_allocate_sequence_handle "*" parm caller [] modify [eax ebx ecx edx]
void _AIL_set_GTL_filename_prefix(char *s);
int  _AIL_install_MDI_INI(void *p);
int  _AIL_allocate_sequence_handle(int h);
"""

_DEFS = """
struct c2inf_rec { char pad0[13]; char tunes_on; char pad1[46]; };
struct c2inf_rec c2inf;
int sequences_running;
int mdi;
int ms;
int S_mdi[2];
int tune1;
int tune2;
int tune_mood;
int tune_branch_count;
int last_battle_mood;
int last_city_mood;
#pragma aux _AIL_set_GTL_filename_prefix "*" parm caller [] modify [eax ebx ecx edx]
#pragma aux _AIL_install_MDI_INI         "*" parm caller [] modify [eax ebx ecx edx]
#pragma aux _AIL_allocate_sequence_handle "*" parm caller [] modify [eax ebx ecx edx]
void _AIL_set_GTL_filename_prefix(char *s) { (void)s; }
int  _AIL_install_MDI_INI(void *p) { (void)p; return 0; }
int  _AIL_allocate_sequence_handle(int h) { return h; }
#include <i86.h>
"""

exp = Experiment(
    name="start_sequences",
    ps_function="start_sequences",
    chk=True,
    prelude=_GLOBALS,
    extra_defs=_DEFS,
)

_HEAD = '#include <i86.h>\nchar __far *start_sequences(void)\n'

# ── baseline: current source (wrapping if + trailing return 0) ──
exp.add(
    "baseline",
    _HEAD + """{
    if (!sequences_running && c2inf.tunes_on) {
        _AIL_set_GTL_filename_prefix("CAESAR");
        if (_AIL_install_MDI_INI(&mdi) != 0) return (char __far *)1;
        for (ms = 0; ms < 2; ms++) {
            S_mdi[ms] = _AIL_allocate_sequence_handle(mdi);
        }
        for (ms = 0; ms < 2; ms++) {
            if (S_mdi[ms] == 0) return (char __far *)MK_FP(1, 2);
        }
        tune1 = 0;
        tune2 = 1;
        tune_mood = 0;
        tune_branch_count = 0;
        last_battle_mood = 0;
        last_city_mood = 0;
        sequences_running = 1;
    }
    return (char __far *)0;
}""",
    note="current: wrapping if + trailing return 0 (113b funnel)",
)

# ── no trailing return (W107 fall-off) ──
exp.add(
    "no-trailing-return",
    _HEAD + """{
    if (!sequences_running && c2inf.tunes_on) {
        _AIL_set_GTL_filename_prefix("CAESAR");
        if (_AIL_install_MDI_INI(&mdi) != 0) return (char __far *)1;
        for (ms = 0; ms < 2; ms++) {
            S_mdi[ms] = _AIL_allocate_sequence_handle(mdi);
        }
        for (ms = 0; ms < 2; ms++) {
            if (S_mdi[ms] == 0) return (char __far *)MK_FP(1, 2);
        }
        tune1 = 0;
        tune2 = 1;
        tune_mood = 0;
        tune_branch_count = 0;
        last_battle_mood = 0;
        last_city_mood = 0;
        sequences_running = 1;
    }
}""",
    note="W107 fall-off end (no trailing return)",
)

# ── early-return guards, no trailing return (W107) ──
exp.add(
    "early-guards-w107",
    _HEAD + """{
    if (sequences_running) return (char __far *)0;
    if (c2inf.tunes_on == 0) return (char __far *)0;
    _AIL_set_GTL_filename_prefix("CAESAR");
    if (_AIL_install_MDI_INI(&mdi) != 0) return (char __far *)1;
    for (ms = 0; ms < 2; ms++) {
        S_mdi[ms] = _AIL_allocate_sequence_handle(mdi);
    }
    for (ms = 0; ms < 2; ms++) {
        if (S_mdi[ms] == 0) return (char __far *)MK_FP(1, 2);
    }
    tune1 = 0;
    tune2 = 1;
    tune_mood = 0;
    tune_branch_count = 0;
    last_battle_mood = 0;
    last_city_mood = 0;
    sequences_running = 1;
    return (char __far *)0;
}""",
    note="early-return guards + trailing return 0",
)

# ── handle-null check OUTSIDE the loop (separate flag) ──
exp.add(
    "check-after-loop",
    _HEAD + """{
    if (!sequences_running && c2inf.tunes_on) {
        _AIL_set_GTL_filename_prefix("CAESAR");
        if (_AIL_install_MDI_INI(&mdi) != 0) return (char __far *)1;
        for (ms = 0; ms < 2; ms++) {
            S_mdi[ms] = _AIL_allocate_sequence_handle(mdi);
        }
        ms = 0;
        while (ms < 2) {
            if (S_mdi[ms] == 0) return (char __far *)MK_FP(1, 2);
            ms++;
        }
        tune1 = 0;
        tune2 = 1;
        tune_mood = 0;
        tune_branch_count = 0;
        last_battle_mood = 0;
        last_city_mood = 0;
        sequences_running = 1;
    }
    return (char __far *)0;
}""",
    note="handle-null loop as while",
)
