# try_this_regionmap_square: the goto-ret0 vs plain-return-0 mix at each
# exit site is byte-identical AFTER the online ComTail merges, but the
# IL trees differ per site -> the anon CSE mask temps' creation order
# differs -> the ShellSort slot assignment differs (islands 1-3,5,7-9).
# Enumerate the mix to find PS's slot layout.  (The framed mid-epilogue
# at 0x217 is a CLASSIFIED unreachable residue -- see
# ~/git/ReverseEngineering/watcom10.0a/probes/framed-epilogue/ -- so
# byte-exact is NOT the target; judge by the shape layers.)
from c2.forge import Forge, TextEdit

forge = Forge("try_this_regionmap_square", file="int_c2.c")
src = forge.index.text
fn_start = src.index("int try_this_regionmap_square(int target, int kind, int third)")
fn_end = src.index("int try_a_seamap_square(")


def sites(needle):
    out = []
    i = fn_start
    while True:
        i = src.find(needle, i, fn_end)
        if i < 0:
            break
        out.append(i)
        i += len(needle)
    return out


# plain `return 0;` -> `goto ret0;` toggles (each site)
n = 0
for off in sites("return 0;"):
    # skip the ret0 label's own return
    prev = src.rfind("\n", 0, off)
    line = src[prev + 1 : off]
    if "ret0:" in src[max(fn_start, off - 40) : off]:
        continue
    forge.candidate(
        f"g{n}_ret0_at_{off}",
        TextEdit(start=off, end=off + len("return 0;"), replacement="goto ret0;"),
    )
    n += 1

# goto ret0 -> plain return (the 0x10-arm's two)
for off in sites("goto ret0;"):
    forge.candidate(
        f"p{n}_plain_at_{off}",
        TextEdit(start=off, end=off + len("goto ret0;"), replacement="return 0;"),
    )
    n += 1

# branch-B tail: goto ret999 (already applied) <-> return 0x3e7
tail = sites("    goto ret999;\n}")
if tail:
    off = tail[0] + 4
    forge.candidate(
        "b_tail_plain999",
        TextEdit(start=off, end=off + len("goto ret999;"), replacement="return 0x3e7;"),
    )

# 0x10-arm: goto ret999 -> return 0x3e7
off = sites("goto ret999;")[0]
forge.candidate(
    "a_arm_plain999",
    TextEdit(start=off, end=off + len("goto ret999;"), replacement="return 0x3e7;"),
)
