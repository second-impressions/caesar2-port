# Start from a SEAT=0 basin (source already mutated with a seat-flipping
# base, e.g. `long i`) and drive the COLLATERAL to zero while seat stays
# 0.  The full lever battery + custom byte-neutral perturbations, pairs
# and triples.  Read min-bytes among seat==0 plans.
import sys
from c2.forge import Forge, TextEdit

forge = Forge("city_test_for_road", file="int_c2.c")
src = forge.text
fn = src.index("int city_test_for_road(int x, int y, int map_ref, int world_dir)\n{")

forge.preset("all")   # full battery discovered on the (mutated) source


def at(text, occ=0):
    i = -1
    for _ in range(occ + 1):
        i = src.index(text, i + 1)
    return i


def cand(name, *pairs):
    edits = []
    for old, new, *rest in pairs:
        a = at(old, rest[0] if rest else 0)
        edits.append(TextEdit(a, a + len(old), new))
    forge.candidate(name, *edits)


# extra byte-neutral conflict-list perturbations to compose with the battery
cand("np_uint", ("    int n_present;", "    unsigned int n_present;"))
cand("ne_uint", ("    int n_empty;", "    unsigned int n_empty;"))
cand("np_long", ("    int n_present;", "    long n_present;"))
cand("ne_long", ("    int n_empty;", "    long n_empty;"))
cand("scan_nested",
     ("    for (i = 0; i < 8; i += 2) {\n"
      "        if (slots[i][0] == 0) continue;\n"
      "        n_present++; if (slots[i][1] != 0) continue; if (slots[i][2] != 0) continue; n_empty++;\n"
      "    }",
      "    for (i = 0; i < 8; i += 2) {\n"
      "        if (slots[i][0] != 0) {\n"
      "            n_present++;\n"
      "            if (slots[i][1] == 0 && slots[i][2] == 0) n_empty++;\n"
      "        }\n"
      "    }"))

base = None
with forge.session(jobs=12) as s:
    for mode in ("each", "pairs"):
        summary = s.run(mode, stop_at_exact=True, max_variants=8000)
        base = summary.baseline
        seat0 = [p for p in summary.plans if p.score.layers[4] == 0]
        exact = [p for p in summary.plans if p.score.bytes == 0]
        seat0.sort(key=lambda p: (p.score.bytes, p.score.layers))
        print(f"\n=== {mode} ===  baseline bytes={base.bytes} "
              f"layers={base.layers}  plans={len(summary.plans)} "
              f"seat0={len(seat0)} exact={len(exact)}")
        if exact:
            print("  *** BYTE EXACT ***")
            for p in exact[:5]:
                print(f"    {p.plan.name}")
        for p in seat0[:12]:
            print(f"    b={p.score.bytes:<4} {p.score.layers}  {p.plan.name[:70]}")
