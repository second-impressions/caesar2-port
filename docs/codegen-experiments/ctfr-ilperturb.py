# city_test_for_road x<->y seat.  CONFIRMED reachable: perturbing i's
# conflict (long/unsigned i) flips x->EDI.  Those change emitted code;
# hunt a BYTE-NEUTRAL IL perturbation that flips the ShellSort the same
# way.  Targets: §1 inline-index vs cached-pointer (slots[i]/slots[rd]),
# scan-loop restructure, statement order, chain-assign order.
from c2.forge import Forge, TextEdit

forge = Forge("city_test_for_road", file="int_c2.c")
src = forge.text
fn = src.index("int city_test_for_road(int x, int y, int map_ref, int world_dir)\n{")


def repl(name, old, new, *more):
    a = src.index(old, fn)
    edits = [TextEdit(a, a + len(old), new)]
    forge.candidate(name, *edits)


def repl2(name, pairs):
    edits = []
    for old, new in pairs:
        a = src.index(old, fn)
        edits.append(TextEdit(a, a + len(old), new))
    forge.candidate(name, *edits)


# ── scan loop: cache slots[i] as a pointer (§1) ──
SCAN = ("    for (i = 0; i < 8; i += 2) {\n"
        "        if (slots[i][0] == 0) continue;\n"
        "        n_present++; if (slots[i][1] != 0) continue; if (slots[i][2] != 0) continue; n_empty++;\n"
        "    }")
repl("scan_ptr", SCAN,
     "    for (i = 0; i < 8; i += 2) {\n"
     "        unsigned char *s = slots[i];\n"
     "        if (s[0] == 0) continue;\n"
     "        n_present++; if (s[1] != 0) continue; if (s[2] != 0) continue; n_empty++;\n"
     "    }")
# scan loop: nested-if instead of continue chain
repl("scan_nested", SCAN,
     "    for (i = 0; i < 8; i += 2) {\n"
     "        if (slots[i][0] != 0) {\n"
     "            n_present++;\n"
     "            if (slots[i][1] == 0 && slots[i][2] == 0) n_empty++;\n"
     "        }\n"
     "    }")

# ── the single-road return loop: cache / form ──
repl("ret_ge", "for (i = 0; i < 8; i += 2) if (slots[i][0] != 0) return i;",
     "for (i = 0; i < 8; i += 2) { if (slots[i][0] != 0) return i; }")

# ── empty-scan fallback loops: cache slots[rand_dir] pointer ──
EMPTY = ("            for (i = 0; i < 4; i++) {\n"
         "                if (slots[rand_dir][0] != 0) {\n"
         "                    if (slots[rand_dir][1] == 0 && slots[rand_dir][2] == 0) {\n"
         "                        if (rand_dir != forbidden) return rand_dir;\n"
         "                    }\n"
         "                }\n"
         "                rand_dir += 2;\n"
         "                if (rand_dir > 6) rand_dir = 0;\n"
         "            }")
repl("empty_ptr", EMPTY,
     "            for (i = 0; i < 4; i++) {\n"
     "                unsigned char *s = slots[rand_dir];\n"
     "                if (s[0] != 0) {\n"
     "                    if (s[1] == 0 && s[2] == 0) {\n"
     "                        if (rand_dir != forbidden) return rand_dir;\n"
     "                    }\n"
     "                }\n"
     "                rand_dir += 2;\n"
     "                if (rand_dir > 6) rand_dir = 0;\n"
     "            }")

# ── init loop chain-assign order / form ──
INIT = "    for (i = 0; i < 8; i += 2) slots[i][0] = slots[i][1] = slots[i][2] = 0;"
repl("init_ptr", INIT,
     "    for (i = 0; i < 8; i += 2) { unsigned char *s = slots[i]; s[0] = s[1] = s[2] = 0; }")
repl("init_rev", INIT,
     "    for (i = 0; i < 8; i += 2) slots[i][2] = slots[i][1] = slots[i][0] = 0;")

# ── statement order: n_present/n_empty init vs rand_dir ──
repl2("npinit_split", [("    n_present = 0; n_empty = 0;",
                        "    n_present = 0;\n    n_empty = 0;")])
repl2("npinit_swap", [("    n_present = 0; n_empty = 0;",
                       "    n_empty = 0; n_present = 0;")])
# move rand_dir assignment BEFORE the scan loop
repl2("rand_before_scan",
      [("    n_present = 0; n_empty = 0;\n",
        "    rand_dir = (unsigned char)rand8 & 6;\n    n_present = 0; n_empty = 0;\n"),
       ("\n    rand_dir = (unsigned char)rand8 & 6;\n    if (n_present != 0) {",
        "\n    if (n_present != 0) {")])

# ── forbidden line before/after the init loop (stmt order) ──
repl2("forb_before_init",
      [("    for (i = 0; i < 8; i += 2) slots[i][0] = slots[i][1] = slots[i][2] = 0;\n    forbidden = ((char)world_dir + 4) & 7;\n",
        "    forbidden = ((char)world_dir + 4) & 7;\n    for (i = 0; i < 8; i += 2) slots[i][0] = slots[i][1] = slots[i][2] = 0;\n")])

with forge.session(jobs=12) as s:
    summary = s.run("each", stop_at_exact=True, max_variants=200)

base = summary.baseline
print(f"\nBASELINE  bytes={base.bytes}  layers(ir,isl,w,sp,seat)={base.layers}")
print(f"{'candidate':22s} {'bytes':>6} {'seat':>5}  layers")
print("-" * 66)
for p in sorted(summary.plans, key=lambda p: (p.score.layers[4], p.score.bytes)):
    lay = p.score.layers
    flag = ""
    if lay[4] < base.layers[4]:
        flag = "  <== SEAT FLIP"
    if p.score.bytes == 0:
        flag = "  <== *** BYTE EXACT ***"
    print(f"{p.plan.name:22s} {p.score.bytes:>6} {lay[4]:>5}  {lay}{flag}")
