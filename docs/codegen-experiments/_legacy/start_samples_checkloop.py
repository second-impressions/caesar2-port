#!/usr/bin/env python3
"""start_samples check-loop: find the C shape that emits load-then-test.

PS start_samples' second loop (the `S_dig[ds] == 0` check) emits:

    mov eax, [ds]                 ; reload index
    mov edx, [eax*4 + S_dig]      ; LOAD the value into a register
    test edx, edx                 ; test the REGISTER (not memory)
    jne skip
    mov eax, 2; jmp epilogue      ; return 2 materialized in eax
skip:
    lea ebx, [eax + 1]            ; counter via lea (eax free)
    mov [ds], ebx
    cmp ebx, 6; jl loop

The recovered source `for(...) if (S_dig[ds] == 0) return 2;` makes Watcom
fold the test into a memory compare (`cmp [eax*4+S_dig], 0; jne`) -- a
different, smaller encoding.  PS loads first.  This cgex scans candidate
C shapes for the one whose emitted check-loop matches PS's
load-then-test-in-edx + counter-in-ebx-via-lea shape.

Run:  uv run python docs/codegen-experiments/start_samples_checkloop.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from c2.commands.oracle import compile_snippet

# Mirror start_samples: a global int array S_dig[6], global index ds,
# a cdecl AIL_allocate call (cross-object so it doesn't inline), and
# the two-loop structure (assign loop, then check loop).
_GLB = "int S_dig[6];\nint ds;\n"
_AIL_DECL = "int __cdecl _AIL_allocate_sample_handle(int dig);\n"
_AIL_STUB = "int __cdecl _AIL_allocate_sample_handle(int dig){return 0;}\n"
_FAR_DECL = "char __far *__cdecl init_ss(void);\n"  # not used; just for link
_PRELUDE = _GLB + _AIL_DECL + _FAR_DECL

def _build(body: str):
    snip = _PRELUDE + body
    return compile_snippet({'snip.c': snip, 'ail_stubs.c': _AIL_STUB})


def _check_loop_region(fn):
    """Find the check loop's body: from the SECOND `mov eax,[ds]` (reload
    of the loop index after the assign loop reset) to the `mov [ds],ebx`
    counter store.  Return those insns."""
    insns = fn.insns
    # find all `mov eax, [...]` (ds reloads) -- the 2nd starts the check loop
    reloads = [i for i, ins in enumerate(insns)
              if ins.mnemonic == "mov" and ins.op_str.startswith("eax, dword ptr [")
              and "0x" in ins.op_str]  # global ds
    if len(reloads) < 2:
        return []
    start = reloads[1]
    # up to and including the counter store `mov [..], ebx` or `mov [..], eax`
    end = len(insns)
    for i in range(start, len(insns)):
        if insns[i].mnemonic in {"ret", "call"} and i > start + 2:
            end = i
            break
    return insns[start:end]


def _text(region):
    return " | ".join(f"{i.mnemonic} {i.op_str}".strip() for i in region)


# --- candidate shapes -----------------------------------------------------

def shape_A_inline_test() -> str:
    """Current RC: inline `if (S_dig[ds] == 0)` -- folds to cmp [mem],0."""
    return """
char __far *start_samples(void) {
    char __far *rc;
    for (ds = 0; ds < 6; ds++) S_dig[ds] = _AIL_allocate_sample_handle(0);
    for (ds = 0; ds < 6; ds++) if (S_dig[ds] == 0) return (char __far *)2;
    return rc;
}
"""


def shape_B_named_local() -> str:
    """Named local h = S_dig[ds]; if (h == 0) return 2;  (loads into a reg)."""
    return """
char __far *start_samples(void) {
    char __far *rc;
    for (ds = 0; ds < 6; ds++) S_dig[ds] = _AIL_allocate_sample_handle(0);
    for (ds = 0; ds < 6; ds++) {
        int h;
        h = S_dig[ds];
        if (h == 0) return (char __far *)2;
    }
    return rc;
}
"""


def shape_C_single_loop() -> str:
    """Merge: assign + check in ONE loop (like start_sequences, which is exact)."""
    return """
char __far *start_samples(void) {
    char __far *rc;
    for (ds = 0; ds < 6; ds++) {
        S_dig[ds] = _AIL_allocate_sample_handle(0);
        if (S_dig[ds] == 0) return (char __far *)2;
    }
    return rc;
}
"""


SHAPES = [
    ("A inline test        (current RC)", shape_A_inline_test),
    ("B named local h      (load+test)  ", shape_B_named_local),
    ("C single loop        (sibling)    ", shape_C_single_loop),
]


def main() -> None:
    for label, src in SHAPES:
        b = _build(src())
        assert b.ok, f"build failed for {label}:\n{b.output[-400:]}"
        fn = b.function("start_samples")
        print(f"\n===== {label} =====")
        for i in fn.insns:
            print(f"  {i.mnemonic} {i.op_str}")


if __name__ == "__main__":
    main()
