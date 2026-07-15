"""get_selection_goods_list (controls.c) — i*2 CSE vs per-store SIB *2 fold.

PS.EXE folds the `*2` of each `short`-array store into the addressing-mode
SIB byte, recomputing it per store:

    mov word ptr [eax*2 + highlight_goods_list], dx
    mov word ptr [eax*2 + selection_goods_list], ax

Our build CSEs `i*2` into EBX once per iteration and reuses it:

    lea ebx, [eax + eax]
    mov word ptr [ebx + highlight_goods_list], dx
    mov word ptr [ebx + selection_goods_list], ax

The CSE shifts every subsequent byte (151 b diff).  This experiment
bisects source forms of the `mode == 0` loop that stop Watcom hoisting
`i*2` (Rule 96 / strength-reduction-control family).

CONCLUSION (2026-06): UNRESOLVED 151 b in the faithful order; no source
lever.  The mode==0 loop stores to two `short` arrays at the same index i:

    highlight_goods_list[i] = (industry[i].status == 1);   /* unconditional */
    if (industry[i].status != 0) selection_goods_list[i] = i;

PS folds `*2` into each store's SIB byte (`[eax*2 + base]`), recomputing
it per store.  Our build CSEs `i*2` into EBX (`lea ebx,[eax+eax]`) above
the branch and reuses it for both stores — shifting every later byte
(151 b cascade).

Bisection (12 trials):
* **highlight-first (PS's actual store order) ALWAYS CSEs** — 153 b.
  status-temp, separate index var (`k=i`), value temp (`hv`), `(short)`
  casts: all 153 b.  The CSE is robust under every highlight-first form.
* **selection-first breaks the CSE** (33 b) — but PS stores highlight
  FIRST (`mov word [eax*2+0x321c0],dx` precedes the selection store at
  0x321e8), so selection-first is the WRONG order and the 33 b is the
  store-order mismatch, not progress toward PS.
* split-loops / pointer-walk-highlight: 173 / 188 b (worse).

So PS emits highlight-first WITHOUT the `i*2` CSE that our build always
performs for the same source — a Watcom CSE/code-motion aggressiveness
difference (same family as the ComTail donor race), with no faithful
C-source spelling that suppresses it.  Source left as-is (faithful
highlight-first); the 151 b is a recomp-only CSE artefact.

Run::  uv run c2 cgex run get_selection_goods_list
"""

from c2.commands.cgex import Experiment

_TYPES = """
struct industry_rec {
    int status, supply, delivered, unit_size, count, has_supply, city_supply;
    int supply_pipeline[5];
};
struct region_source_rec { unsigned char primary; unsigned char choices[9]; };
extern short highlight_goods_list[];
extern short selection_goods_list[];
extern struct industry_rec industry[];
extern struct region_source_rec region_sources[];
extern int province_is;
extern void __STOSB(void *dst, int val, unsigned n);
#pragma aux __STOSB "*" parm caller [eax] [edx] [ecx] modify [];
"""

_DEFS = """
struct industry_rec {
    int status, supply, delivered, unit_size, count, has_supply, city_supply;
    int supply_pipeline[5];
};
struct region_source_rec { unsigned char primary; unsigned char choices[9]; };
short highlight_goods_list[64];
short selection_goods_list[64];
struct industry_rec industry[32];
struct region_source_rec region_sources[64];
int province_is;
#pragma aux __STOSB "*" parm caller [eax] [edx] [ecx] modify [];
void __STOSB(void *dst, int val, unsigned n) { (void)dst; (void)val; (void)n; }
"""

exp = Experiment(
    name="get_selection_goods_list",
    ps_function="get_selection_goods_list",
    externs={},
    prelude=_TYPES,
    extra_defs=_DEFS,
    chk=False,
)

_TAIL = """
    if (mode == 1) {
        for (i = 0; i < 3; i++)
            selection_goods_list[i] = region_sources[province_is].choices[i];
        return;
    }
    if (mode == 2) {
        for (i = 0; i < 3; i++)
            selection_goods_list[i] = region_sources[province_is].choices[3 + i];
        return;
    }
    if (mode == 3) {
        for (i = 0; i < 3; i++)
            selection_goods_list[i] = region_sources[province_is].choices[6 + i];
    }
}
"""

exp.add("baseline", """
void get_selection_goods_list(int mode)
{
    int i;
    __STOSB(selection_goods_list, 0x100010, 0x22);
    if (mode == 0) {
        for (i = 0; i < 0x10; i++) {
            highlight_goods_list[i] = (industry[i].status == 1);
            if (industry[i].status != 0) {
                selection_goods_list[i] = i;
            }
        }
    }
""" + _TAIL, note="current source")


# nest the second store under the same condition only (no change) — control
exp.add("status-temp", """
void get_selection_goods_list(int mode)
{
    int i;
    __STOSB(selection_goods_list, 0x100010, 0x22);
    if (mode == 0) {
        for (i = 0; i < 0x10; i++) {
            int st = industry[i].status;
            highlight_goods_list[i] = (st == 1);
            if (st != 0) {
                selection_goods_list[i] = i;
            }
        }
    }
""" + _TAIL, note="cache industry[i].status in a temp")


# store i via a short to keep value narrow; index stays subscript
exp.add("short-i", """
void get_selection_goods_list(int mode)
{
    short i;
    __STOSB(selection_goods_list, 0x100010, 0x22);
    if (mode == 0) {
        for (i = 0; i < 0x10; i++) {
            highlight_goods_list[i] = (industry[i].status == 1);
            if (industry[i].status != 0) {
                selection_goods_list[i] = i;
            }
        }
    }
""" + _TAIL, note="short i loop counter")


def _mode0(loop):
    return """
void get_selection_goods_list(int mode)
{
    int i;
    __STOSB(selection_goods_list, 0x100010, 0x22);
    if (mode == 0) {
""" + loop + """
    }
""" + _TAIL

# selection store first, highlight after
exp.add("sel-first", _mode0("""
        for (i = 0; i < 0x10; i++) {
            if (industry[i].status != 0) selection_goods_list[i] = i;
            highlight_goods_list[i] = (industry[i].status == 1);
        }
"""), note="selection store before highlight")

# two separate loops
exp.add("split-loops", _mode0("""
        for (i = 0; i < 0x10; i++)
            highlight_goods_list[i] = (industry[i].status == 1);
        for (i = 0; i < 0x10; i++)
            if (industry[i].status != 0) selection_goods_list[i] = i;
"""), note="two separate loops")

# pointer-walk highlight
exp.add("ptr-highlight", _mode0("""
        short *hp = highlight_goods_list;
        for (i = 0; i < 0x10; i++) {
            *hp++ = (industry[i].status == 1);
            if (industry[i].status != 0) selection_goods_list[i] = i;
        }
"""), note="pointer-walk highlight array")

# store (short)i to discourage shared i*2
exp.add("cast-store", _mode0("""
        for (i = 0; i < 0x10; i++) {
            highlight_goods_list[i] = (short)(industry[i].status == 1);
            if (industry[i].status != 0) selection_goods_list[i] = (short)i;
        }
"""), note="(short) casts on stored values")


# highlight first, selection via a separate index var (defeat i*2 CSE)
exp.add("sel-sep-idx", _mode0("""
        for (i = 0; i < 0x10; i++) {
            highlight_goods_list[i] = (industry[i].status == 1);
            if (industry[i].status != 0) {
                int k = i;
                selection_goods_list[k] = k;
            }
        }
"""), note="highlight first; selection via separate k=i")

# compute highlight value into temp first (PS sete-first), store highlight, then if
exp.add("hv-temp", _mode0("""
        for (i = 0; i < 0x10; i++) {
            short hv = (industry[i].status == 1);
            highlight_goods_list[i] = hv;
            if (industry[i].status != 0)
                selection_goods_list[i] = i;
        }
"""), note="highlight value temp, store, then if")

# selection-first but highlight value computed first (sete early), highlight stored last
exp.add("sel-first-hv", _mode0("""
        for (i = 0; i < 0x10; i++) {
            short hv = (industry[i].status == 1);
            if (industry[i].status != 0)
                selection_goods_list[i] = i;
            highlight_goods_list[i] = hv;
        }
"""), note="hv first, selection in if, highlight last")
