#!/usr/bin/env python3
"""start_samples L142 check-loop island (2026-07-03): OPEN — load+test spelling unfound.

The one remaining island in pcsound.c::start_samples (A-form source, 36 b,
binir 1/8 = L142 only):

  PS  (0x11860):                          RC (A-form):
    mov  eax,[ds]                           mov  eax,[ds]
    mov  edx,[eax*4+S_dig]   ; dword load   cmp  dword [eax*4+S_dig],0
    test edx,edx                            je   ...
    jne  skip                               xor  edx,edx      ; segment 0
    mov  eax,2               ; edx==0 IS    mov  eax,2
    jmp  epi                 ; the segment
  skip: lea ebx,[eax+1]                   skip: lea ebx,[eax+1]   ; SAME (idx CSE holds)

PS loads S_dig[ds] into EDX, tests the register, and the return-2 site has NO
`xor edx,edx` — the loaded (known-zero) EDX is reused as the far-pointer
segment half.  RC's A-form compares memory directly and materialises the 0.

Everything is grounded in OW v1 source + the 10.0a binary RE:

* `cse.c` ProcessExpr: CSE requires equal type_class — MK_FP's
  `(unsigned short)` cast word-folds the segment read (mov dx,[mem]), so it
  never CSEs with the dword compare.  Confirmed by compile (variant B).
* `scins.c` TryRegOp: Score replaces a constant operand with a register
  known-equal ("don't change cmp x,0" guards only condition opcodes) — this
  is how PS elides the segment move once the value sits in EDX, and why our
  h-variants emit `mov edx,eax` (known-zero EAX reused).
* `regalloc.c` CountRegMoves: seat credit needs the move partner to be a
  PHYSICAL register in the IL at GiveBestReg time.  The far-return pair is
  built through a shared U2/U4 pair temp (sav=7, allocated AFTER h sav=21),
  so h never sees EDX credit.  Witness the working direction:
  raider_in_region's `map_ref` seats EDX via the put_message arg move
  (args ARE physical at IL-build; return halves are NOT).
* Corpus scan (1442 byte-exact fns): `mov r,[r*4+..]; test r,r` occurs
  NOWHERE — the pattern is unique to start_samples.  55 plain
  `mov r,[mem]; test r,r; jcc` witnesses all have a visible second use
  (`if (x) free(x)` family) or a named local consumed later.

~30 spellings probed (this file's PROBES reproduce the key ones):
  - named local h (assign-in-cond / stmt / block-scoped / `register`):
    load+test YES, but h seats EAX (greedy; EDX credit invisible, see above)
    and the h-def SPLITS the [ds] increment CSE (lea -> mov/inc reload).
  - `switch (S_dig[ds]) case 0:`: load+test, but splits idx CSE + funnels.
  - `(S_dig[ds] & S_dig[ds]) == 0`: the ONLY spelling with load+test AND
    intact idx CSE (x&x survives the folder, AND-with-dead-result = TEST) —
    but it perturbs the whole return-pair seating (10 reg swaps; idx/value
    seats flip EAX<->EDX; GB shows "skipped EAX(masked)" round-2 starving,
    creation-order sensitive).
  - MK_FP(S_dig[ds],2) / raw `:>` / (unsigned)/(unsigned long) casts:
    word-fold, no CSE.
  - `(char __far *)(S_dig[ds]+2)`: dword CSE fires (load+test in EDX!) but
    the return is lea eax,[edx+2] + mov edx,ds (int->far cast = DS segment).
  - rc-staging (`rc = ...MK_FP(h,2); return rc;`): copy-prop flattens to the
    h-variant.
  - identity forms (|0, ^0, +0, *1, -0, >>0, casts): all fold to cmp mem,0.
  - volatile (cast or decl): cmp mem,0 is a single read; no load.

Isolation caveat: a minimal far-ptr TU with the pragma funnels ALL returns
(mov edx,eax/mov eax,ebx epilogue join) — the real TU does not; probe
results transfer only for the loop SHAPE, not the return realization.

Round 2 (same day, user-pushed) -- the oracle-witness pass:

* WIN oracle recovered BY ADDRESS (c2win.decompile(0x00401085); the name
  lookup fails -- tier-2 map entry).  MSVC /Od asm of the check loop:
  `mov eax,[0x55c074]; cmp dword [eax*4+0x55c310],0; jne` -- NO stack
  slot, NO explicit AND, single array ref.  At /Od any named temp or
  x&x would be explicit ==> the WIN-era source condition is the plain
  anonymous `if (S_dig[ds] == 0)`.  (Caveat: Win is the LATER port --
  it replaced the far-ptr error returns with `sound_error(off, seg)`
  calls, so the DOS return spelling is not directly witnessed.)
* sound_error fingerprint: samples' fail arm calls error(2, 0);
  sequences' calls error(2, 1) -- mirroring DOS MK_FP(1,2).  ==> the
  DOS samples return VALUE is (seg=0, off=2), i.e. `(char __far *)2`
  or `MK_FP(0, 2)` (both compile IDENTICALLY -- tried).
* Cross-build: bytes identical in all three PS builds across 6 months
  of development ==> the load+test shape is a ROBUST property of the
  spelling, not a heap/creation-order accident.
* Corpus scan (all 1521 fns): the 5-insn shape `mov r,[idx*4+base];
  test r,r; jne; mov eax,imm; jmp` with EDX untouched is UNIQUE to
  start_samples.
* MECHANISM of the named-h increment split identified: cse.c
  UnOpsLiveFrom's conservative ReDefinedBy blocks the backward
  LinkMemMoves propagation (the [ds] re-read unification) across a
  NAMED-local assignment; anonymous-result ops pass through -- which
  is why `(S_dig[ds] & S_dig[ds])` keeps the unification while every
  h spelling splits it.
* Best structural variant: `if ((S_dig[ds] & S_dig[ds]) == 0) return
  (char __far *)MK_FP(0, 2);` -- IL matches PS except the index temp's
  savings (50 vs PS's ~30, from the doubled address ref) defers it to
  allocation ROUND-2 where EAX is masked (a sav=0 call-return temp owns
  it) ==> idx seats EDX, value EAX -- ONE systematic seat swap from
  byte-exact.  PS's IL must materialize the value into an ANONYMOUS
  temp with a SINGLE address ref; no C spelling found that does this
  (identity ops fold; casts fold; unsigned relationals stay cmp-mem;
  volatile stays cmp-mem; comma DCEs; switch/goto restructure).

Round 3 (parser fix + the :> / MK_FP-seg family):

* c2's pycparser preprocess() now rewrites Watcom's `:>` base operator
  to binary `+` (parse-only), so raw-:> spellings are testable in the
  real TU.  The container's REAL 10.0a i86.h confirms
  `MK_FP(s,o) = ((unsigned short)(s)):>((void __near *)(o))`.
* New hypothesis tested: PS source = `MK_FP(S_dig[ds], 2)` -- the far
  seg IS the loaded value (semantically (0:2) on the taken path, and
  it would explain PS's missing seg-half conflict: our MK_FP(0,2)
  needs a separate sav=0 seg temp that takes EAX round-1 and masks the
  idx).  DEAD: the int->segment conversion narrows the load to `mov
  dx,[..]` REGARDLESS of the (unsigned short) cast (raw `:>` with int
  or (__segment) operand narrows identically), and the U2 load cannot
  CSE with the condition's U4 read.  Wrapping the seg expr in AND-self
  pushes the narrow THROUGH the AND (word load + `and edx,edx`).
  x&x-condition + MK_FP(S_dig[ds],2) is worse (ir 4/11, shl+word).
* 28a commutes of the x&x condition (`!(..)`, `0 == (..)`) are inert.
* The one-seat residue of x&x+MK_FP(0,2) (ir 1/11, seat 1/7) is
  classified by the cascade engine as an H2 creation-order tie
  (replay-unreachable; the clean-build lever would be moving the idx's
  last use, which `ds++` pins).

STATUS: A-form kept (best PLAUSIBLE-source layer vector: ir2, 36 b;
concordance 1.00; win-witnessed condition + fingerprinted return
value).  The x&x variant is shape-closer (ir1) but is not credible
1995 source -- kept out per the over-fitting rule.  The materializing
construct remains the single open question.

Run: `python docs/codegen-experiments/start_samples_check_loop.py`
(needs podman image localhost/watcom-10.0a-dosemu2).
"""

import subprocess
import tempfile
from pathlib import Path

PROBE = r"""
extern int gd;
extern int A[6];
int f1(void) {  /* A-form: cmp mem,0 + unified idx (lea) */
    for (gd = 0; gd < 6; gd++) if (A[gd] == 0) return 1;
    return 0;
}
int f2(void) {  /* named local: load+test but idx CSE splits (mov/inc) */
    int h;
    for (gd = 0; gd < 6; gd++) if ((h = A[gd]) == 0) return 1;
    return 0;
}
int f3(void) {  /* x&x: load+test AND unified idx -- the only such form */
    for (gd = 0; gd < 6; gd++) if ((A[gd] & A[gd]) == 0) return 1;
    return 0;
}
"""


def main() -> None:
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from c2.parsers import omf
    import capstone

    cs = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    with tempfile.TemporaryDirectory() as td:
        src = Path(td) / "probe.c"
        src.write_text(PROBE)
        subprocess.run(
            ["podman", "run", "--rm", "-v", f"{td}:/src",
             "localhost/watcom-10.0a-dosemu2",
             "wcc386 -bt=dos -mf -4r -s -d1 probe.c"],
            check=True, capture_output=True)
        for fname, body, _fix in omf.parse_obj_functions(str(Path(td) / "probe.obj")):
            text = "\n".join(f"{i.mnemonic} {i.op_str}".strip()
                             for i in cs.disasm(body, 0))
            print(f"=== {fname}\n{text}\n")
        # f1: memory compare, unified increment
        # f2: register load+test, SPLIT increment (reload)
        # f3: register load+test, unified increment (but seats flip in the
        #     real far-return TU -- see module docstring)


if __name__ == "__main__":
    main()
