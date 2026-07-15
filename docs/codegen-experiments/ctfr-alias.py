# city_test_for_road: the x<->y param EDI/EBP seat tie (sav 4/4).
# NEW angles vs the prior battery:
#  (A) named-local ALIASES for x/y -- if 10.0a coalesces `int lx = x;`
#      (the "PropRegsOne #if 0" no-merge claim is from the 2002 vendored
#      source, only a HINT), lx/ly become NAMED locals => a Rule 115
#      decl-order lever on the tie that params don't have.
#  (B) first-use direction: reference x EARLY (before the N guard) so
#      x's FIRST use precedes y's (the §(3) first-use proxy) -- the
#      prior ctfr-lastuse.py only probed the LAST-use direction.
#  (C) param-order: swap which name is declared first while keeping the
#      register semantics (can we get x's FE temp-id above y's?).
from c2.forge import Forge, TextEdit

forge = Forge("city_test_for_road", file="int_c2.c")
src = forge.text
fn = src.index("int city_test_for_road(int x, int y, int map_ref, int world_dir)\n{")

DECLS = (
    "    unsigned char slots[8][3];\n"
    "    signed char forbidden;\n"
    "    signed char rand_dir;\n"
    "    int i;\n"
    "    int n_present;\n"
    "    int n_empty;\n"
)
decl_a = src.index(DECLS, fn)
decl_b = decl_a + len(DECLS)

FORB = "    forbidden = ((char)world_dir + 4) & 7;\n"
forb_a = src.index(FORB, fn)
forb_b = forb_a + len(FORB)

EG = "if (x < 0x4f) {"
WG = "if (x > 0) {"
eg = src.index(EG, fn)
wg = src.index(WG, fn)


def cand(name, *edits):
    forge.candidate(name, *edits)


# ── (A) named-local aliases: does the param->local copy coalesce? ──
# A1: lx aliases BOTH x-guards; declared FIRST among the int locals.
cand("A1_lx_both_first",
     TextEdit(decl_a, decl_b, DECLS.replace("    int i;\n",
              "    int lx;\n    int i;\n")),
     TextEdit(forb_a, forb_a, "    lx = x;\n"),
     TextEdit(eg, eg + len(EG), "if (lx < 0x4f) {"),
     TextEdit(wg, wg + len(WG), "if (lx > 0) {"))
# A2: same but declared LAST (Rule 115 direction non-monotonic).
cand("A2_lx_both_last",
     TextEdit(decl_a, decl_b, DECLS.replace("    int n_empty;\n",
              "    int n_empty;\n    int lx;\n")),
     TextEdit(forb_a, forb_a, "    lx = x;\n"),
     TextEdit(eg, eg + len(EG), "if (lx < 0x4f) {"),
     TextEdit(wg, wg + len(WG), "if (lx > 0) {"))
# A3: BOTH lx and ly aliases, lx declared before ly.
cand("A3_lxly_xfirst",
     TextEdit(decl_a, decl_b, DECLS.replace("    int i;\n",
              "    int lx;\n    int ly;\n    int i;\n")),
     TextEdit(forb_a, forb_a, "    lx = x;\n    ly = y;\n"),
     TextEdit(eg, eg + len(EG), "if (lx < 0x4f) {"),
     TextEdit(wg, wg + len(WG), "if (lx > 0) {"),
     TextEdit(src.index("if (y > 0) {", fn), src.index("if (y > 0) {", fn) + len("if (y > 0) {"), "if (ly > 0) {"),
     TextEdit(src.index("if (y < 0x4f) {", fn), src.index("if (y < 0x4f) {", fn) + len("if (y < 0x4f) {"), "if (ly < 0x4f) {"))
# A4: ly and lx, ly declared before lx (reverse).
cand("A4_lxly_yfirst",
     TextEdit(decl_a, decl_b, DECLS.replace("    int i;\n",
              "    int ly;\n    int lx;\n    int i;\n")),
     TextEdit(forb_a, forb_a, "    lx = x;\n    ly = y;\n"),
     TextEdit(eg, eg + len(EG), "if (lx < 0x4f) {"),
     TextEdit(wg, wg + len(WG), "if (lx > 0) {"),
     TextEdit(src.index("if (y > 0) {", fn), src.index("if (y > 0) {", fn) + len("if (y > 0) {"), "if (ly > 0) {"),
     TextEdit(src.index("if (y < 0x4f) {", fn), src.index("if (y < 0x4f) {", fn) + len("if (y < 0x4f) {"), "if (ly < 0x4f) {"))

# ── (B) first-use direction: give x an early first use ──
# B1: bare x; before N guard (folds? -> baseline; if it flips, first-use is the key)
cand("B1_x_stmt_early", TextEdit(forb_b, forb_b, "    x;\n"))
# B2: (void)x early
cand("B2_voidx_early", TextEdit(forb_b, forb_b, "    (void)x;\n"))
# B3: fold x into forbidden line: mask by x|7 keeps &7 (may or may not fold)
cand("B3_forb_or_x7",
     TextEdit(forb_a, forb_b, "    forbidden = (((char)world_dir + 4) & 7) & (x | 7);\n"))
# B4: fold x-x into world_dir expr
cand("B4_forb_wd_plus_xmx",
     TextEdit(forb_a, forb_b, "    forbidden = ((char)world_dir + 4 + (x - x)) & 7;\n"))

# ── (C) param-order: reverse the signature decl order, remap regs ──
# In __watcall param position fixes the register; to keep semantics we
# must ALSO swap uses.  This tests whether swapping the SIGNATURE decl
# order (FE temp-id) flips the tie when the emitted regs are forced back
# by remapping.  (Likely changes bytes; a seat=0 here still names the
# mechanism.)
SIG = "int city_test_for_road(int x, int y, int map_ref, int world_dir)"
sig_a = src.index(SIG, fn)
# C1: declare y before x in the signature but the FIRST reg param is
# still the column value -> rename so eax-param keeps column semantics.
# (y, x) means eax=y-name; to keep eax=column we must call the eax param
# 'x' still -> i.e. this is just a rename, inert.  Instead probe adding a
# 5th dummy param that shifts nothing but the id walk:  SKIP (inert).

with forge.session(jobs=12) as s:
    summary = s.run("each", stop_at_exact=True)

base = summary.baseline
print(f"\nBASELINE  bytes={base.bytes}  layers(ir,isl,w,sp,seat)={base.layers}")
print(f"{'candidate':28s} {'bytes':>6} {'seat':>5}  layers")
print("-" * 70)
for p in sorted(summary.plans, key=lambda p: (p.score.layers[4], p.score.bytes)):
    lay = p.score.layers
    flag = "  <== SEAT FLIP" if lay[4] < base.layers[4] else ("  <== EXACT" if p.score.bytes == 0 else "")
    print(f"{p.plan.name:28s} {p.score.bytes:>6} {lay[4]:>5}  {lay}{flag}")
