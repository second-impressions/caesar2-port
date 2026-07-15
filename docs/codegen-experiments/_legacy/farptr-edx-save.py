"""farptr-edx-save — does the RETURN TYPE control whether a void function
preserves (pushes) EDX when it uses EDX internally?

The OW v1 `MustSaveRegs` (i86reg.c) does, in the non-MODIFY_EXACT path:
    save &= ~FullReg(parm.used | return_reg)
For a far pointer return the return_reg is RL_DX_EAX = {DX, EAX} (16-bit DX
seg).  FullReg(DX) promotes to EDX, so EDX is removed from `save` -> never
pushed.  For a near pointer / int the return_reg is {EAX}, so EDX survives
and is pushed if used.

This experiment tells us whether the verifier's 10.0a actually applies that
FullReg to the return_reg (the open question behind start_sequences's edx
push).

  A-far   char __far * return, uses edx in a global-counter loop
  B-near  char *       return, same body
  C-void  void         return, same body
  D-int   int          return, same body

RESULT (verifier 10.0a, 2026-06-20, via print_trial prologue):
  A-far   prologue `push ebx` ONLY -- EDX NOT preserved; seg materialised at
          the epilogue (`mov edx, ds`) or the return site (`mov edx,1` for
          MK_FP).  i.e. the far-ptr return reg RL_DX_EAX = {DX,EAX} FullRegs
          to EDX and is stripped from must_save.
  B-near  prologue `push ebx; push edx` -- EDX PRESERVED (RL_EAX return reg
          leaves EDX in must_save).
  C-void  EDX PRESERVED (return_reg EMPTY).
  D-int   EDX PRESERVED (RL_EAX).
  long-long (U8/I8 = RL_EDX_EAX) and struct-in-regs FullReg to EDX too -> no
  push, same as far-ptr.

IMPLICATION for pcsound.c start_sequences / start_samples: PS.EXE PUSHES EDX
for these far-ptr-returning functions (constant-seg MK_FP error codes), but
the verifier's 10.0a never does (the FullReg above strips EDX).  A non-far
return type would push EDX but cannot emit the 2-register seg (`mov edx,1`);
a `modify exact` pragma forces the push but is DISPROVEN as PS source -- it
would have regressed start_sound (a body-exact far-ptr fn that tail-merges
with start_sequences and stays exact WITHOUT any pragma).  So the edx push is
not reachable from faithful far-ptr C under the verifier image: a far-ptr
return must_save divergence between the verifier's 10.0a and the 10.0a that
built PS.EXE (the one place the "byte-identical" claim has an exception).

Run::  uv run c2 cgex run farptr-edx-save
"""

from c2.commands.cgex import Experiment

exp = Experiment(
    name="farptr-edx-save",
    chk=False,
    externs={
        "ext_call": "extern int ext_call(int v);",
    },
    extra_defs="int g_ctr;\nint g_arr[4];\n",
    prelude="extern int g_ctr;\nextern int g_arr[4];\n",
)

_BODY = """
    for (g_ctr = 0; g_ctr < 2; g_ctr++) {{
        g_arr[g_ctr] = ext_call(g_ctr);
    }}
    if (g_arr[0] == 0) return {ret1};
    return {ret0};
"""

exp.add("A-far",
        "char __far *f(void)\n{" + _BODY.format(ret1="(char __far *)1", ret0="(char __far *)0") + "}\n",
        note="far-ptr return (RL_DX_EAX)")
exp.add("B-near",
        "char *f(void)\n{" + _BODY.format(ret1="(char *)1", ret0="(char *)0") + "}\n",
        note="near-ptr return (RL_EAX)")
exp.add("C-void",
        "void f(void)\n{" + _BODY.replace("return {ret1};", "return;").replace("return {ret0};", "return;") + "}\n",
        note="void return")
exp.add("D-int",
        "int f(void)\n{" + _BODY.format(ret1="1", ret0="0") + "}\n",
        note="int return (RL_EAX)")
