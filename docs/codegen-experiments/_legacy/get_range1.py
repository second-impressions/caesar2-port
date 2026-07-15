"""get_range1 — operand evaluation order of (byte) & mask."""
from c2.commands.cgex import Experiment

_PRELUDE = r"""
#define CITY_W              80
#define CITY_CELL_BYTES     20
#define CITY_ROW            (CITY_W * CITY_CELL_BYTES)
#define CC_RANGE_FLAG(c)    ((c)[0xa])
"""
_DEFS = _PRELUDE

exp = Experiment(
    name="get_range1",
    ps_function="get_range1",
    chk=False,
    prelude=_PRELUDE,
    extra_defs=_DEFS,
)

exp.add("baseline", r"""
int get_range1(unsigned char *start, int range, char mask)
{
    int best, row, col;
    int val;
    unsigned char *c;

    if (range == 1) {
        return (CC_RANGE_FLAG(start)) & mask;
    }
    best = 0;
    for (row = 0; row < range; row++) {
        for (col = 0; col < range; col++) {
            c = start + col * CITY_CELL_BYTES + row * CITY_ROW;
            val = (CC_RANGE_FLAG(c)) & mask;
            if (val > best) best = val;
        }
    }
    return best;
}
""", note="current (46 b diff)")

exp.add("reversed_and", r"""
int get_range1(unsigned char *start, int range, char mask)
{
    int best, row, col;
    int val;
    unsigned char *c;

    if (range == 1) {
        return mask & (CC_RANGE_FLAG(start));
    }
    best = 0;
    for (row = 0; row < range; row++) {
        for (col = 0; col < range; col++) {
            c = start + col * CITY_CELL_BYTES + row * CITY_ROW;
            val = mask & (CC_RANGE_FLAG(c));
            if (val > best) best = val;
        }
    }
    return best;
}
""", note="mask & byte (reversed)")

exp.add("split_load", r"""
int get_range1(unsigned char *start, int range, char mask)
{
    int best, row, col;
    int val;
    int b;
    unsigned char *c;

    if (range == 1) {
        b = CC_RANGE_FLAG(start);
        return b & mask;
    }
    best = 0;
    for (row = 0; row < range; row++) {
        for (col = 0; col < range; col++) {
            c = start + col * CITY_CELL_BYTES + row * CITY_ROW;
            b = CC_RANGE_FLAG(c);
            val = b & mask;
            if (val > best) best = val;
        }
    }
    return best;
}
""", note="int b temp")

exp.add("byte_temp", r"""
int get_range1(unsigned char *start, int range, char mask)
{
    int best, row, col;
    int val;
    unsigned char b;
    unsigned char *c;

    if (range == 1) {
        b = CC_RANGE_FLAG(start);
        return b & mask;
    }
    best = 0;
    for (row = 0; row < range; row++) {
        for (col = 0; col < range; col++) {
            c = start + col * CITY_CELL_BYTES + row * CITY_ROW;
            b = CC_RANGE_FLAG(c);
            val = b & mask;
            if (val > best) best = val;
        }
    }
    return best;
}
""", note="unsigned char b temp")

exp.add("compound_and", r"""
int get_range1(unsigned char *start, int range, char mask)
{
    int best, row, col;
    int val;
    unsigned char *c;

    if (range == 1) {
        val = CC_RANGE_FLAG(start);
        val &= mask;
        return val;
    }
    best = 0;
    for (row = 0; row < range; row++) {
        for (col = 0; col < range; col++) {
            c = start + col * CITY_CELL_BYTES + row * CITY_ROW;
            val = CC_RANGE_FLAG(c);
            val &= mask;
            if (val > best) best = val;
        }
    }
    return best;
}
""", note="compound &=")
