"""refresh_a_square — register choice for ref_ptr.

PS keeps the computed ref_ptr in `ecx`; recomp keeps it in `eax`.
Cascades into 15 byte-diffs in the unrolled 5×3 stamp.  Probe
which source variation flips the choice.
"""

from c2.commands.cgex import Experiment

_PRELUDE = """
extern int  ref_ptr;
extern char svga_refresh_table[];
"""

_DEFS = """
int  ref_ptr;
char svga_refresh_table[1200];
"""

exp = Experiment(
    name="refresh-a-square",
    ps_function="refresh_a_square",
    prelude=_PRELUDE,
    extra_defs=_DEFS,
)


_TAIL = """
    svga_refresh_table[idx + 0x00] = val;
    svga_refresh_table[idx + 0x01] = val;
    svga_refresh_table[idx + 0x02] = val;
    svga_refresh_table[idx + 0x03] = val;
    svga_refresh_table[idx + 0x04] = val;
    svga_refresh_table[idx + 0x28] = val;
    svga_refresh_table[idx + 0x29] = val;
    svga_refresh_table[idx + 0x2a] = val;
    svga_refresh_table[idx + 0x2b] = val;
    svga_refresh_table[idx + 0x2c] = val;
    svga_refresh_table[idx + 0x50] = val;
    svga_refresh_table[idx + 0x51] = val;
    svga_refresh_table[idx + 0x52] = val;
    svga_refresh_table[idx + 0x53] = val;
    svga_refresh_table[idx + 0x54] = val;
}
"""


# ── trial 1: baseline (current source: x + (y * 40)) ──────────
exp.add(
    "baseline",
    """
void refresh_a_square(int x, int y, char val)
{
    int idx = x;
    idx += y * 0x28;
    ref_ptr = idx;
""" + _TAIL,
    note="x first, += y*40",
)


# ── trial 2: y*40 first, +x via temp ───────────────────────────
exp.add(
    "y40-first",
    """
void refresh_a_square(int x, int y, char val)
{
    int idx = y * 0x28;
    idx += x;
    ref_ptr = idx;
""" + _TAIL,
    note="y*40 first then += x",
)


# ── trial 3: single-expr (x + y*40) ────────────────────────────
exp.add(
    "single-x-first",
    """
void refresh_a_square(int x, int y, char val)
{
    int idx = x + y * 0x28;
    ref_ptr = idx;
""" + _TAIL,
    note="single expression x + y*40",
)


# ── trial 4: single-expr (y*40 + x) ────────────────────────────
exp.add(
    "single-y40-first",
    """
void refresh_a_square(int x, int y, char val)
{
    int idx = y * 0x28 + x;
    ref_ptr = idx;
""" + _TAIL,
    note="single expression y*40 + x (Rule 4 swap)",
)


# ── trial 5: assign to global directly, alias as local ─────────
exp.add(
    "global-direct",
    """
void refresh_a_square(int x, int y, char val)
{
    ref_ptr = x + y * 0x28;
""" + _TAIL.replace("idx", "ref_ptr"),
    note="store to ref_ptr only, no local",
)


# ── trial 6: parm-aliases force regalloc swap ─────────────────
exp.add(
    "swap-params",
    """
void refresh_a_square(int x, int y, char val)
{
    int idx = y * 0x28;
    idx = idx + x;
    ref_ptr = idx;
""" + _TAIL,
    note="explicit two-step add",
)


# ── trial 7: x + y*40 via cast to char ─────────────────────────
exp.add(
    "char-val",
    """
void refresh_a_square(int x, int y, int val)
{
    int idx = x;
    idx += y * 0x28;
    ref_ptr = idx;
""" + _TAIL,
    note="val as int (default param promotion)",
)
