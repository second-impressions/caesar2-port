# city_test_for_road x<->y seat.  The flip is a CLEAN unstable-ShellSort
# tie (inverse_search: x<->y swap, zero side effects).  No SINGLE
# byte-neutral perturbation flips it -- so throw a broad battery of
# byte-neutral conflict-list perturbations and run PAIRS/TRIPLES: the
# unstable sort may flip [x,y] only under a COMBINATION.
from c2.forge import Forge, TextEdit

forge = Forge("city_test_for_road", file="int_c2.c")
src = forge.text
fn = src.index("int city_test_for_road(int x, int y, int map_ref, int world_dir)\n{")


def at(text, occurrence=0):
    i = -1
    for _ in range(occurrence + 1):
        i = src.index(text, i + 1)
    return i


def cand(name, *pairs):
    edits = []
    for old, new, *rest in pairs:
        occ = rest[0] if rest else 0
        a = at(old, occ)
        edits.append(TextEdit(a, a + len(old), new))
    forge.candidate(name, *edits)


# ── DECL region perturbations (mutually overlapping) ──
cand("np_uint", ("    int n_present;", "    unsigned int n_present;"))
cand("np_long", ("    int n_present;", "    long n_present;"))
cand("ne_uint", ("    int n_empty;", "    unsigned int n_empty;"))
cand("ne_long", ("    int n_empty;", "    long n_empty;"))
cand("i_uint", ("    int i;", "    unsigned int i;"))
# decl-order swaps within int locals
cand("do_ne_np", ("    int n_present;\n    int n_empty;",
                  "    int n_empty;\n    int n_present;"))
cand("do_i_np", ("    int i;\n    int n_present;\n    int n_empty;",
                 "    int n_present;\n    int i;\n    int n_empty;"))
cand("do_i_last", ("    int i;\n    int n_present;\n    int n_empty;",
                   "    int n_present;\n    int n_empty;\n    int i;"))
# char-local decl order
cand("do_chars", ("    signed char forbidden;\n    signed char rand_dir;",
                  "    signed char rand_dir;\n    signed char forbidden;"))

# ── INIT loop region ──
cand("init_rev", ("slots[i][0] = slots[i][1] = slots[i][2] = 0;",
                  "slots[i][2] = slots[i][1] = slots[i][0] = 0;"))

# ── forbidden line region ──
cand("forb_nocast", ("forbidden = ((char)world_dir + 4) & 7;",
                     "forbidden = (world_dir + 4) & 7;"))
cand("forb_signedcast", ("forbidden = ((char)world_dir + 4) & 7;",
                         "forbidden = ((signed char)world_dir + 4) & 7;"))
cand("forb_paren", ("forbidden = ((char)world_dir + 4) & 7;",
                    "forbidden = (((char)world_dir) + 4) & 7;"))

# ── scan loop region (n_present/n_empty computation) ──
SCAN = ("    for (i = 0; i < 8; i += 2) {\n"
        "        if (slots[i][0] == 0) continue;\n"
        "        n_present++; if (slots[i][1] != 0) continue; if (slots[i][2] != 0) continue; n_empty++;\n"
        "    }")
cand("scan_nested", (SCAN,
     "    for (i = 0; i < 8; i += 2) {\n"
     "        if (slots[i][0] != 0) {\n"
     "            n_present++;\n"
     "            if (slots[i][1] == 0 && slots[i][2] == 0) n_empty++;\n"
     "        }\n"
     "    }"))

# ── n_present/n_empty init region ──
cand("np_split", ("    n_present = 0; n_empty = 0;",
                  "    n_present = 0;\n    n_empty = 0;"))
cand("np_swap", ("    n_present = 0; n_empty = 0;",
                 "    n_empty = 0; n_present = 0;"))

# ── return loop region ──
cand("ret_braces", ("for (i = 0; i < 8; i += 2) if (slots[i][0] != 0) return i;",
                    "for (i = 0; i < 8; i += 2) { if (slots[i][0] != 0) return i; }"))

# ── rand_dir expression region ──
cand("rd_paren", ("    rand_dir = (unsigned char)rand8 & 6;",
                  "    rand_dir = ((unsigned char)rand8) & 6;"))
cand("rd_int", ("    rand_dir = (unsigned char)rand8 & 6;",
                "    rand_dir = rand8 & 6;"))

# ── separate loop counter j for the two i<4 fallback loops ──
cand("split_j",
     ("    int n_empty;\n", "    int n_empty;\n    int j;\n"),
     ("            for (i = 0; i < 4; i++) {\n", "            for (j = 0; j < 4; j++) {\n", 0),
     ("        for (i = 0; i < 4; i++) {\n", "        for (j = 0; j < 4; j++) {\n", 0))


def report(summary, tag):
    base = summary.baseline
    print(f"\n[{tag}] BASELINE bytes={base.bytes} seat={base.layers[4]}  "
          f"({len(summary.plans)} plans)")
    wins = [p for p in summary.plans
            if p.score.layers[4] < base.layers[4] or p.score.bytes == 0]
    if not wins:
        # show the byte-neutral seat-unchanged + anything with lowest bytes
        best = sorted(summary.plans, key=lambda p: (p.score.layers[4], p.score.bytes))[:8]
        print("  no seat flip.  closest:")
        for p in best:
            print(f"    {p.plan.name:34s} b={p.score.bytes:<4} seat={p.score.layers[4]} {p.score.layers}")
        return False
    print("  *** FLIP/EXACT ***")
    for p in sorted(wins, key=lambda p: (p.score.bytes, p.score.layers[4])):
        print(f"    {p.plan.name:34s} b={p.score.bytes:<4} seat={p.score.layers[4]} {p.score.layers}")
    return True


with forge.session(jobs=12) as s:
    print("=== SINGLES ===")
    report(s.run("each", stop_at_exact=True), "singles")
    print("\n=== PAIRS ===")
    report(s.run("pairs", stop_at_exact=True, max_variants=6000), "pairs")
    print("\n=== TRIPLES ===")
    report(s.run("triples", stop_at_exact=True, max_variants=25000), "triples")
