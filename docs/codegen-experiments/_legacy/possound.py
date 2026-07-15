"""pos_sound — the dead `xor edx,edx; mov eax,3` on the set_sample_file==0 path.

PS.EXE `pos_sound` (void) emits, for the failed-set_sample_file path:

    +008b  test eax, eax
           jne  0x94             ; if result != 0, skip
           xor  edx, edx         ; result == 0 path ...
           mov  eax, 3           ; ... dead (eax overwritten next insn)
    +0094  mov  eax, [ds]        ; <- BOTH paths fall through here
           ... _AIL_start_sample(S_dig[ds]) ...
           jmp  epilogue

i.e. the `== 0` branch computes a discarded value (`xor edx,edx; mov
eax,3`) and FALLS THROUGH to _AIL_start_sample — it does NOT return.
Our current source `if (... == 0) return;` instead emits a single
`je epilogue` (the early return), giving a 13-byte diff.

Goal: find the C statement in the `== 0` branch that produces
`xor edx,edx; mov eax,3` with fall-through (no control transfer).

Run with::

    uv run c2 cgex run possound
    uv run c2 cgex run possound --trial baseline
"""

from c2.commands.cgex import Experiment

_PRELUDE = """
struct c2inf_rec { char pad0[12]; char samples_on; char pad1[47]; int max_samples; };
extern struct c2inf_rec c2inf;
extern int S_dig[];
extern int ds;
extern int dig_status;
extern int samples_running;
extern char positive_buffer[];

#pragma aux _AIL_sample_status   "*" parm caller [] modify [eax ebx ecx edx]
#pragma aux _AIL_end_sample      "*" parm caller [] modify [eax ebx ecx edx]
#pragma aux _AIL_init_sample     "*" parm caller [] modify [eax ebx ecx edx]
#pragma aux _AIL_set_sample_file "*" parm caller [] modify [eax ebx ecx edx]
#pragma aux _AIL_start_sample    "*" parm caller [] modify [eax ebx ecx edx]
int  _AIL_sample_status(int handle);
void _AIL_end_sample(int handle);
void _AIL_init_sample(int sample);
int  _AIL_set_sample_file(int sample, void *buf, int block);
void _AIL_start_sample(int sample);
"""

# Definitions for linking (defs TU).  Same pragmas as the prelude so the
# decorated symbol names agree across TUs.
_DEFS = """
struct c2inf_rec { char pad0[12]; char samples_on; char pad1[47]; int max_samples; };
struct c2inf_rec c2inf;
int S_dig[8];
int ds;
int dig_status;
int samples_running;
char positive_buffer[16];
#pragma aux _AIL_sample_status   "*" parm caller [] modify [eax ebx ecx edx]
#pragma aux _AIL_end_sample      "*" parm caller [] modify [eax ebx ecx edx]
#pragma aux _AIL_init_sample     "*" parm caller [] modify [eax ebx ecx edx]
#pragma aux _AIL_set_sample_file "*" parm caller [] modify [eax ebx ecx edx]
#pragma aux _AIL_start_sample    "*" parm caller [] modify [eax ebx ecx edx]
int  _AIL_sample_status(int h) { return h; }
void _AIL_end_sample(int s) { (void)s; }
void _AIL_init_sample(int s) { (void)s; }
int  _AIL_set_sample_file(int s, void *b, int blk) { (void)b; (void)blk; return s; }
void _AIL_start_sample(int s) { (void)s; }
"""

exp = Experiment(
    name="possound",
    ps_function="pos_sound",
    chk=True,
    prelude=_PRELUDE,
    extra_defs=_DEFS,
)


def _wrap(body: str, ret: str = "void", proto_extra: str = "") -> str:
    return f"""
{ret} pos_sound(void)
{{
{body}
}}
"""


# ── baseline: current source (early return) ───────────────────────
exp.add(
    "baseline",
    _wrap("""    if (c2inf.samples_on == 0)  return;
    if (samples_running == 0)   return;

    ds = 4;
    dig_status = _AIL_sample_status(S_dig[4]);
    if (dig_status == 4) _AIL_end_sample(S_dig[ds]);
    _AIL_init_sample(S_dig[ds]);
    if (_AIL_set_sample_file(S_dig[ds], positive_buffer, -1) == 0) return;
    _AIL_start_sample(S_dig[ds]);"""),
    note="current: if(==0) return; -> je epilogue (13b diff)",
)


# ── discarded long local = 3 (32-bit long is just eax in Watcom) ──
exp.add(
    "long-local-3",
    _wrap("""    long _d;
    if (c2inf.samples_on == 0)  return;
    if (samples_running == 0)   return;

    ds = 4;
    dig_status = _AIL_sample_status(S_dig[4]);
    if (dig_status == 4) _AIL_end_sample(S_dig[ds]);
    _AIL_init_sample(S_dig[ds]);
    if (_AIL_set_sample_file(S_dig[ds], positive_buffer, -1) == 0) _d = 3;
    _AIL_start_sample(S_dig[ds]);"""),
    note="if(==0) _d = 3; (dead long local)",
)


# ── int pos_sound, return 3 (expect jmp epilogue, not fallthrough) ─
exp.add(
    "int-return-3",
    """
int pos_sound(void)
{
    if (c2inf.samples_on == 0)  return 0;
    if (samples_running == 0)   return 0;

    ds = 4;
    dig_status = _AIL_sample_status(S_dig[4]);
    if (dig_status == 4) _AIL_end_sample(S_dig[ds]);
    _AIL_init_sample(S_dig[ds]);
    if (_AIL_set_sample_file(S_dig[ds], positive_buffer, -1) == 0) return 3;
    _AIL_start_sample(S_dig[ds]);
    return 0;
}
""",
    note="int return, return 3 — control-flow check",
)


# ── discarded expression statement: (long)3; ──────────────────────
exp.add(
    "expr-long-3",
    _wrap("""    if (c2inf.samples_on == 0)  return;
    if (samples_running == 0)   return;

    ds = 4;
    dig_status = _AIL_sample_status(S_dig[4]);
    if (dig_status == 4) _AIL_end_sample(S_dig[ds]);
    _AIL_init_sample(S_dig[ds]);
    if (_AIL_set_sample_file(S_dig[ds], positive_buffer, -1) == 0) (void)(long)3;
    _AIL_start_sample(S_dig[ds]);"""),
    note="if(==0) (void)(long)3; (discarded long expr)",
)


# ── discarded __int64 value 3 -> edx:eax = 0:3, register-only ─────
exp.add(
    "i64-expr-3",
    _wrap("""    if (c2inf.samples_on == 0)  return;
    if (samples_running == 0)   return;

    ds = 4;
    dig_status = _AIL_sample_status(S_dig[4]);
    if (dig_status == 4) _AIL_end_sample(S_dig[ds]);
    _AIL_init_sample(S_dig[ds]);
    if (_AIL_set_sample_file(S_dig[ds], positive_buffer, -1) == 0) (void)(__int64)3;
    _AIL_start_sample(S_dig[ds]);"""),
    note="if(==0) (void)(__int64)3; (discarded 64-bit -> xor edx; mov eax,3?)",
)


# ── __int64-returning function, return 3 ─────────────────────────
exp.add(
    "i64-return-3",
    """
__int64 pos_sound(void)
{
    if (c2inf.samples_on == 0)  return 0;
    if (samples_running == 0)   return 0;

    ds = 4;
    dig_status = _AIL_sample_status(S_dig[4]);
    if (dig_status == 4) _AIL_end_sample(S_dig[ds]);
    _AIL_init_sample(S_dig[ds]);
    if (_AIL_set_sample_file(S_dig[ds], positive_buffer, -1) == 0) return 3;
    _AIL_start_sample(S_dig[ds]);
    return 0;
}
""",
    note="__int64 return, return 3",
)


# ── dig_status assigned but as a value 3 via long cast ────────────
exp.add(
    "int-local-3",
    _wrap("""    int _d;
    if (c2inf.samples_on == 0)  return;
    if (samples_running == 0)   return;

    ds = 4;
    dig_status = _AIL_sample_status(S_dig[4]);
    if (dig_status == 4) _AIL_end_sample(S_dig[ds]);
    _AIL_init_sample(S_dig[ds]);
    if (_AIL_set_sample_file(S_dig[ds], positive_buffer, -1) == 0) _d = 3;
    _AIL_start_sample(S_dig[ds]);"""),
    note="if(==0) _d = 3; (dead int local)",
)
