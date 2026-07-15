"""Unit tests for the layer-3 last-use reorder analyzer (pure helpers)."""
import sys
sys.path.insert(0, '.')
from c2.commands.lastuse import (
    _reads_writes, _trace, _same_src, _regs_in, _norm, _Insn,
)

def I(idx, mn, ops, ln=None):
    return _Insn(idx, idx, ln, mn, ops)

# ── reads/writes ─────────────────────────────────────────────────────────────
r, w = _reads_writes(I(0, "mov", "edx, eax"))
assert r == {"eax"} and w == {"edx"}, (r, w)
r, w = _reads_writes(I(0, "add", "edx, eax"))           # RMW
assert r == {"edx", "eax"} and w == {"edx"}, (r, w)
r, w = _reads_writes(I(0, "cmp", "ebx, ecx"))           # both read
assert r == {"ebx", "ecx"} and w == set(), (r, w)
r, w = _reads_writes(I(0, "mov", "byte ptr [eax + 0x10], dl"))  # store
assert r == {"eax", "edx"} and w == set(), (r, w)
r, w = _reads_writes(I(0, "call", "0x1234"))            # clobber
assert w == {"eax", "edx", "ebx", "ecx"}, (r, w)
r, w = _reads_writes(I(0, "movsx", "eax, dl"))          # sub-reg src
assert r == {"edx"} and w == {"eax"}, (r, w)
print("✓ _reads_writes: mov/RMW/cmp/store/call/sub-reg")

# ── _trace: def + last use ───────────────────────────────────────────────────
prog = [
    I(0, "mov", "eax, 5"),          # def eax
    I(1, "add", "eax, 1"),          # use+def eax
    I(2, "mov", "edx, eax"),        # last read of eax
    I(3, "mov", "eax, 9"),          # eax redefined (value 1 dead)
    I(4, "mov", "ebx, eax"),        # read of new eax
]
d, lu = _trace(prog, 2, "eax")      # value at idx 2
assert lu == 2, lu                  # last read before the rewrite at 3
print("✓ _trace: last use stops at pure rewrite")

# ── _same_src: single-value home (fixup-masked disps normalised) ─────────────
assert _same_src("mov ebx, dword ptr [0x72d84]",
                 "mov ecx, dword ptr [0x430bc]") is True
assert _same_src("mov edx, eax", "mov ebx, eax") is True
assert _same_src("mov edx, eax", "mov edx, ebx") is False   # same dest
assert _same_src("add edx, eax", "add ebx, eax") is False   # not a move
print("✓ _same_src: detects single-value home, normalises fixup disps")

print("\nAll lastuse tests pass.")
