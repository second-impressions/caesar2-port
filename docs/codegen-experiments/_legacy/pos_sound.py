"""pos_sound — AIL sample dispatcher (positive_buffer variant).

PS @ 0x11E92, 174 bytes.  Sibling of `neg_sound` (byte-exact); the
two differ only in the buffer arg (`positive_buffer` vs
`negative_buffer`).  PS tail-merges neg_sound's back half INTO
pos_sound's L314 — pos_sound is the donor.

Current source diff is 13 b, all at L314:

  PS:               jne $+7           ; if (X != 0) skip 7b
                    xor edx, edx      ; (dead — EDX not read later)
                    mov eax, 3        ; (dead — EAX overwritten by next insn)
                    mov eax, [ds]     ; ← fall through, continue to start_sample
                    ...
  RC:               je <epilogue>     ; if (X == 0) return
                    mov eax, [ds]
                    ...

So PS source does NOT have `if (X == 0) return;`.  Instead it
unconditionally falls through to `_AIL_start_sample(...)`, and the
zero-branch sets EAX=3 / EDX=0 as DEAD writes.

`xor edx, edx; mov eax, 3` together is the canonical 32-bit
constant load for an `int` value of 3, OR the 64-bit constant
load (long long) 3.  Watcom 10.0a doesn't normally emit dead
stores — so the source must reference these writes somehow.

Hypotheses tested:
  * `if (...) some_local = 3;` where some_local is a register-only
    local that's never read.
  * `if (...) return 3;` if pos_sound was originally `int`.
  * `if (...) { dig_status = 3; }` (writes to global — but no
    `mov [dig_status], eax` in PS).
  * `(X == 0) ? expr : 0;` short-circuit assigning some local.
"""

from c2.commands.cgex import Experiment


_PRELUDE = """
struct c2inf_t { char pad[0xc]; char samples_on; char pad2[256]; };
extern struct c2inf_t c2inf;
extern int samples_running;
extern int ds;
extern int dig_status;
extern void *S_dig[];
extern char positive_buffer[];
extern int _AIL_sample_status(void *);
extern void _AIL_end_sample(void *);
extern void _AIL_init_sample(void *);
extern int _AIL_set_sample_file(void *, void *, int);
extern void _AIL_start_sample(void *);
"""

_DEFS = """
struct c2inf_t { char pad[0xc]; char samples_on; char pad2[256]; };
struct c2inf_t c2inf;
int samples_running, ds, dig_status;
void *S_dig[8];
char positive_buffer[16];
int _AIL_sample_status(void *p) { (void)p; return 0; }
void _AIL_end_sample(void *p) { (void)p; }
void _AIL_init_sample(void *p) { (void)p; }
int _AIL_set_sample_file(void *p, void *q, int n) { (void)p; (void)q; (void)n; return 0; }
void _AIL_start_sample(void *p) { (void)p; }
"""

exp = Experiment(
    name="pos_sound",
    ps_function="pos_sound",
    chk=True,
    prelude=_PRELUDE,
    extra_defs=_DEFS,
)


# Baseline (current source): if (X == 0) return; — RC emits je <epilogue>.
exp.add("baseline", """
void pos_sound(void)
{
    if (c2inf.samples_on == 0)  return;
    if (samples_running == 0)   return;

    ds = 4;
    dig_status = _AIL_sample_status(S_dig[4]);
    if (dig_status == 4) _AIL_end_sample(S_dig[ds]);
    _AIL_init_sample(S_dig[ds]);
    if (_AIL_set_sample_file(S_dig[ds], positive_buffer, -1) == 0) return;
    _AIL_start_sample(S_dig[ds]);
}
""", note="baseline: if (X==0) return")


# A: invert condition — call start_sample only on success.
exp.add("A_invert", """
void pos_sound(void)
{
    if (c2inf.samples_on == 0)  return;
    if (samples_running == 0)   return;

    ds = 4;
    dig_status = _AIL_sample_status(S_dig[4]);
    if (dig_status == 4) _AIL_end_sample(S_dig[ds]);
    _AIL_init_sample(S_dig[ds]);
    if (_AIL_set_sample_file(S_dig[ds], positive_buffer, -1) != 0)
        _AIL_start_sample(S_dig[ds]);
}
""", note="A: invert — if(X!=0) start_sample")


# B: dead store of 3 to local int (never read).
exp.add("B_dead_local_3", """
void pos_sound(void)
{
    int err;
    if (c2inf.samples_on == 0)  return;
    if (samples_running == 0)   return;

    ds = 4;
    dig_status = _AIL_sample_status(S_dig[4]);
    if (dig_status == 4) _AIL_end_sample(S_dig[ds]);
    _AIL_init_sample(S_dig[ds]);
    err = 0;
    if (_AIL_set_sample_file(S_dig[ds], positive_buffer, -1) == 0)
        err = 3;
    (void)err;
    _AIL_start_sample(S_dig[ds]);
}
""", note="B: dead local err=3 on zero")


# C: dig_status = 3 on zero — global write (test for memory write).
exp.add("C_global_dig_status", """
void pos_sound(void)
{
    if (c2inf.samples_on == 0)  return;
    if (samples_running == 0)   return;

    ds = 4;
    dig_status = _AIL_sample_status(S_dig[4]);
    if (dig_status == 4) _AIL_end_sample(S_dig[ds]);
    _AIL_init_sample(S_dig[ds]);
    if (_AIL_set_sample_file(S_dig[ds], positive_buffer, -1) == 0)
        dig_status = 3;
    _AIL_start_sample(S_dig[ds]);
}
""", note="C: dig_status = 3 on zero")


# D: ternary expression — local int with conditional value.
exp.add("D_ternary_local", """
void pos_sound(void)
{
    int err;
    if (c2inf.samples_on == 0)  return;
    if (samples_running == 0)   return;

    ds = 4;
    dig_status = _AIL_sample_status(S_dig[4]);
    if (dig_status == 4) _AIL_end_sample(S_dig[ds]);
    _AIL_init_sample(S_dig[ds]);
    err = (_AIL_set_sample_file(S_dig[ds], positive_buffer, -1) == 0) ? 3 : 0;
    (void)err;
    _AIL_start_sample(S_dig[ds]);
}
""", note="D: ternary into local err")


# E: empty if-then with no body — does Watcom emit any code?
exp.add("E_empty_branch", """
void pos_sound(void)
{
    if (c2inf.samples_on == 0)  return;
    if (samples_running == 0)   return;

    ds = 4;
    dig_status = _AIL_sample_status(S_dig[4]);
    if (dig_status == 4) _AIL_end_sample(S_dig[ds]);
    _AIL_init_sample(S_dig[ds]);
    if (_AIL_set_sample_file(S_dig[ds], positive_buffer, -1) == 0) {
        /* intentional fall-through */
    }
    _AIL_start_sample(S_dig[ds]);
}
""", note="E: empty if body")


# F: long long dead-store — would emit xor edx, edx; mov eax, 3 if 64-bit.
exp.add("F_longlong_local", """
void pos_sound(void)
{
    long long err;
    if (c2inf.samples_on == 0)  return;
    if (samples_running == 0)   return;

    ds = 4;
    dig_status = _AIL_sample_status(S_dig[4]);
    if (dig_status == 4) _AIL_end_sample(S_dig[ds]);
    _AIL_init_sample(S_dig[ds]);
    err = 0;
    if (_AIL_set_sample_file(S_dig[ds], positive_buffer, -1) == 0)
        err = 3;
    (void)err;
    _AIL_start_sample(S_dig[ds]);
}
""", note="F: long long err=3 (forces edx:eax)")


# G: return 3 — if pos_sound was originally int.
exp.add("G_return_3_int", """
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
""", note="G: int return type, return 3 on failure")
