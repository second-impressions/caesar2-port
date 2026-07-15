#!/usr/bin/env python3
"""start_tune success-path return shape (Rule 85 inverse / far-ptr tail).

Caesar II ``pcsound.c::start_tune`` returns ``char __far *`` (Rule 85:
the two error exits are `MK_FP(1,3)` / `MK_FP(1,4)` -> `mov edx,1; mov
eax,N`).  The RESUME and SUCCESS paths must NOT materialise a far-null
return value -- PS jumps straight to the shared cleanup:

    ... mov esi,[edi+...]; push esi; call _AIL_start_sequence
    add esp, 4            ; cdecl arg cleanup
    jmp <serve_sample+0x42 epilogue>    ; bare near jmp, NO xor/load

i.e. whatever ``edx:eax`` the AIL call deposited is what start_tune
returns.  Recovering that in C is the open lever: the obvious
`return (char __far *)0;`, the uninit-local `return result;`, and the
empty-label `goto done; done: ;` fall-off ALL make Watcom synthesise a
return-value load (``mov edx,[esp+8]; mov eax,[esp+4]``) and reserve a
sub-esp frame for it.  This experiment PROVES the suppressing shape:

  HYPOTHESIS: declare the two AIL calls as returning ``char __far *``
  (matching their real edx:eax deposit) and write them in tail
  position: ``return _AIL_resume_sequence(x);`` /
  ``return _AIL_start_sequence(x);``.  Then Watcom treats the call's
  return registers AS the function's (move-elimination on the return
  value) -> `call; add esp,4; <epilogue>` with NO intervening
  xor/load and ZERO sub-esp frame.  Every other spelling materialises.

Run:  uv run python docs/codegen-experiments/start_tune.py
      (needs podman image localhost/watcom-10.0a-dosemu2)
      (prints ALL PROOFS PASS on success)
"""

from typing import List

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from c2.commands.oracle import compile_snippet

# --- multi-file build to defeat OptSize=50 inlining -----------------------
# `snip.c` declares the AIL calls + defines start_tune; `ail_stubs.c`
# DEFINES the AIL bodies in a SEPARATE object.  Watcom cannot inline
# across objects, so start_tune emits real `call; add esp,4` (cdecl =
# caller cleanup, same call-site shape as ail.h's `parm caller []`).
# Only the AIL RETURN TYPE varies across the void/far* variants -- and
# it MUST match between snip.c's decl and ail_stubs.c's def or Watcom
# errors E1062.
_I86 = '#include <i86.h>\n'
_GLB = 'int S_mdi[2];\n'
_VOID_DECLS = (
    'void __cdecl _AIL_resume_sequence(int seq);\n'
    'void __cdecl _AIL_start_sequence(int seq);\n'
)
_FAR_DECLS = (
    'char __far *__cdecl _AIL_resume_sequence(int seq);\n'
    'char __far *__cdecl _AIL_start_sequence(int seq);\n'
)
_VOID_STUBS = (
    'void __cdecl _AIL_resume_sequence(int seq){}\n'
    'void __cdecl _AIL_start_sequence(int seq){}\n'
)
_FAR_STUBS = (
    'char __far *__cdecl _AIL_resume_sequence(int seq){return 0;}\n'
    'char __far *__cdecl _AIL_start_sequence(int seq){return 0;}\n'
)


def _build(body_src: str, far_ail: bool):
    decls = _FAR_DECLS if far_ail else _VOID_DECLS
    stubs = _FAR_STUBS if far_ail else _VOID_STUBS
    snip = _I86 + _GLB + decls + body_src
    return compile_snippet({'snip.c': snip, 'ail_stubs.c': stubs})


def _tail_after_last_call(fn):
    """Insns from the `add esp,4` (last AIL call's cdecl cleanup) through
    the final `ret` -- the success-path tail we compare."""
    insns = fn.insns
    last_call = max(i for i, ins in enumerate(insns) if ins.mnemonic == "call")
    start = None
    for i in range(last_call + 1, len(insns)):
        if insns[i].mnemonic == "add" and insns[i].op_str.startswith("esp,"):
            start = i
            break
    assert start is not None, "no `add esp,4` after last call"
    return insns[start:]


def _sub_esp_bytes(fn) -> int:
    for ins in fn.insns:
        if ins.mnemonic == "sub" and ins.op_str.startswith("esp,"):
            return int(ins.op_str.split(",")[1].strip(), 16)
    return 0


def _has_materialise(tail) -> bool:
    """True if the success tail synthesises a return-value load/zero."""
    for ins in tail:
        if ins.mnemonic in {"xor"}:
            return True
        if ins.mnemonic == "mov" and (
            ins.op_str.startswith("edx,") or ins.op_str.startswith("eax,")):
            return True
    return False


def _tail_text(tail) -> str:
    return " | ".join(f"{i.mnemonic} {i.op_str}".strip() for i in tail)


# --- candidate variants ---------------------------------------------------

def variant_A_return_zero() -> str:
    """void AIL + `return (char __far *)0;` on success -- current RC residue."""
    return """
char __far *start_tune(unsigned char *seq_arg, int sequence_num, int slot) {
    if (slot == 8) { _AIL_resume_sequence(S_mdi[slot]); return (char __far *)0; }
    if (sequence_num < 0) return (char __far *)MK_FP(1, 3);
    _AIL_start_sequence(S_mdi[slot]);
    return (char __far *)0;
}
"""


def variant_B_return_call() -> str:
    """char __far * AIL + `return _AIL_...(...);` in tail position -- HYPOTHESIS."""
    return """
char __far *start_tune(unsigned char *seq_arg, int sequence_num, int slot) {
    if (slot == 8) { return _AIL_resume_sequence(S_mdi[slot]); }
    if (sequence_num < 0) return (char __far *)MK_FP(1, 3);
    return _AIL_start_sequence(S_mdi[slot]);
}
"""


def variant_C_uninit_local() -> str:
    """void AIL + uninit `char __far *result;` + `return result;` (sibling idiom)."""
    return """
char __far *start_tune(unsigned char *seq_arg, int sequence_num, int slot) {
    char __far *result;
    if (slot == 8) { _AIL_resume_sequence(S_mdi[slot]); return result; }
    if (sequence_num < 0) return (char __far *)MK_FP(1, 3);
    _AIL_start_sequence(S_mdi[slot]);
    return result;
}
"""


def variant_D_goto_done_empty() -> str:
    """void AIL + `goto done; ... done: ;` fall-off non-void."""
    return """
char __far *start_tune(unsigned char *seq_arg, int sequence_num, int slot) {
    if (slot == 8) { _AIL_resume_sequence(S_mdi[slot]); goto done; }
    if (sequence_num < 0) return (char __far *)MK_FP(1, 3);
    _AIL_start_sequence(S_mdi[slot]);
done:
    ;
}
"""


def variant_E_cdecl_cast() -> str:
    """void AIL + __cdecl-cast at call site -- avoids re-typing ail.h/stubs."""
    return """
char __far *start_tune(unsigned char *seq_arg, int sequence_num, int slot) {
    if (slot == 8) {
        return ((char __far *(* __cdecl)(int))_AIL_resume_sequence)(S_mdi[slot]);
    }
    if (sequence_num < 0) return (char __far *)MK_FP(1, 3);
    return ((char __far *(* __cdecl)(int))_AIL_start_sequence)(S_mdi[slot]);
}
"""



VARIANTS = [
    ("A  return 0            (void AIL)", variant_A_return_zero, False),
    ("B  return _AIL_call()  (far* AIL)", variant_B_return_call, True),
    ("C  return result       (uninit)   ", variant_C_uninit_local, False),
    ("D  goto done; done:;   (fall-off) ", variant_D_goto_done_empty, False),
    ("E  __cdecl-cast at call (void AIL)", variant_E_cdecl_cast, False),
]


def _success_exit(fn):
    """The success-path exit: insns from the LAST `call`'s `add esp,4` to the
    FIRST following `ret`.  (Variant B's resume+success both `return _AIL_call()`;
    we take the last = success path.)"""
    insns = fn.insns
    call_idxs = [i for i, ins in enumerate(insns) if ins.mnemonic == "call"]
    if not call_idxs:
        return []
    last_call = max(call_idxs)
    start = next((i for i in range(last_call + 1, len(insns))
                  if insns[i].mnemonic == "add" and insns[i].op_str.startswith("esp,")),
                 None)
    if start is None:
        return []
    end = next(i for i in range(start, len(insns)) if insns[i].mnemonic == "ret")
    return insns[start:end + 1]


def main() -> None:
    results = []
    for label, fn_src, far_ail in VARIANTS:
        b = _build(fn_src(), far_ail)
        assert b.ok, f"build failed for {label}:\n{b.output[-400:]}"
        fn = b.function("start_tune")
        exit_ = _success_exit(fn)
        frame = _sub_esp_bytes(fn)
        mat = _has_materialise(exit_) if exit_ else True   # no call -> broken
        results.append((label, frame, mat, _tail_text(exit_)))

    print(f"{'variant':<38} {'frame':>6} {'mat?':>5}   success exit")
    print("-" * 110)
    for label, frame, mat, txt in results:
        print(f"{label:<38} {frame:>6} {str(mat):>5}   {txt}")

    # HYPOTHESIS (proven): ONLY variant B -- declaring the two AIL calls
    # `char __far *`-returning + writing `return _AIL_call(...);` in tail
    # position -- yields PS's success exit: `call; add esp,4; <epilogue>`
    # with NO xor/load materialisation and ZERO sub-esp frame.
    b_frame, b_mat = results[1][1], results[1][2]
    assert b_frame == 0, f"B must have zero sub-esp frame, got {b_frame}"
    assert not b_mat, f"B success exit must not materialise; got: {results[1][3]}"
    for i, (label, frame, mat, _) in enumerate(results):
        if i == 1:
            continue
        assert frame != 0 or mat, \
            f"{label}: expected to materialise/frame (frame={frame}, mat={mat})" \
            f" -- contradicts hypothesis that ONLY B is clean"
    print("\nALL PROOFS PASS")
    print("  - ONLY `return _AIL_call()` with a far*-returning AIL prototype")
    print("    produces PS's success exit: call -> add esp,4 -> bare epilogue")
    print("    (zero sub-esp frame, no xor/load value materialisation).")
    print("  - Variant E (__cdecl cast) is NOT equivalent: Watcom makes it a")
    print("    function-pointer thunk (tail-jmp), not PS's direct `call; add esp,4`.")
    print("  - Applying variant B to start_tune requires the stub generator")
    print("    (c2/commands/c_source.py) to preserve `__far` on pointer-returning")
    print("    stubs; it currently strips it via _WATCOM_KW_RE.  See commit msg.")


if __name__ == "__main__":
    main()
