"""region_cell struct vs byte access — does modelling region_map cells as
a `struct region_cell` (the "human" 1995 way, mirroring the real
`struct battle_cell` / BCELL) reproduce PS.EXE byte-for-byte?

battle_map is accessed in the byte-exact corpus through a real struct
(`(*(struct battle_cell*)&battle_map[p]).field`), so there is strong
precedent that PS.EXE's source used cell structs.  region_map in our
decomp is accessed through raw byte indexing (`region_map[p + N]`).
This experiment asks whether the struct form is byte-identical for a
clean region-only leaf function.

Test subject: `clear_reg_basic(int rm_offset)` (212 b @ 0x6a0a6) — a
17-line leaf that reads region_map[+1] and writes
region_map[+0/+1/+3/+5/+6/+7].  It is currently byte-exact with byte
access.  PS addressing is `[ebx + region_map+N]` where ebx == rm_offset:
the *byte* offset is added straight onto the global base, so any
struct form must preserve byte-offset addressing to stay exact.

NO accessor MACROS are used in any trial: `struct region_cell` and the
extern `region_map` are declared inline in the prelude / trial bodies,
fields are reached either by raw byte index, by an explicit
`((struct region_cell *)...)->field` cast, or — for the "typed array"
trials — by declaring `region_map` itself as `struct region_cell[]`.
This keeps each trial self-contained and macro-free.

Run with::

    uv run c2 cgex run region_cell_struct
    uv run c2 cgex run region_cell_struct --trial typed-array-cast
"""

from c2.commands.cgex import Experiment

# Shared in every trial body: the cell struct + the stone-random globals.
# region_map itself is declared *per trial* so we can give it either an
# `unsigned char[]` type (cast trials) or a `struct region_cell[]` type
# (typed-array trials).  The backing storage in defs.c is a byte array;
# wlink does not type-check cross-TU symbols, so either declaration links.
PRELUDE = """
struct region_cell {
    unsigned char base_kind;   /* +0x00 */
    unsigned char terrain;     /* +0x01 */
    unsigned char place_state; /* +0x02 */
    unsigned char edge_bits;   /* +0x03 */
    unsigned char gfx;         /* +0x04 */
    unsigned char _unused05;   /* +0x05 */
    unsigned char outside;     /* +0x06 */
    unsigned char occupant;    /* +0x07 */
};
extern signed char stone_random_count;
extern unsigned char stone_random_data[];
"""

DEFS = """
unsigned char region_map[60 * 60 * 8];
signed char stone_random_count;
unsigned char stone_random_data[256];
"""

exp = Experiment(
    name="region_cell_struct",
    ps_function="clear_reg_basic",
    chk=False,
    prelude=PRELUDE,
    extra_defs=DEFS,
)


# ── trial 1: baseline — raw byte access (current source shape) ────
exp.add(
    "byte",
    """
extern unsigned char region_map[];
void clear_reg_basic(int rm_offset)
{
    if (region_map[(rm_offset) + 1] & 0x40) {
        region_map[(rm_offset)] = (char)(((unsigned char)stone_random_data[stone_random_count]) / 4 + 0x18);
    } else if (region_map[(rm_offset) + 1] & 0x80) {
        region_map[(rm_offset)] = (char)(((unsigned char)stone_random_data[stone_random_count]) / 4 + 0x1c);
    } else {
        region_map[(rm_offset)] = (char)(((unsigned char)stone_random_data[stone_random_count]) / 4 + 0x10);
    }
    if (region_map[(rm_offset) + 1] & 1) {
        region_map[(rm_offset) + 7] = 0;
    }
    region_map[(rm_offset) + 1] &= 0xd8;
    region_map[(rm_offset) + 3] &= 2;
    region_map[(rm_offset + 5)] = 0;
    region_map[(rm_offset) + 6] = 0;
    region_map[(rm_offset) + 3] |= 1;
}
""",
    note="raw byte indexing — the current byte-exact source shape",
)


# ── trial 2: char array + struct cast to a local pointer ──────────
exp.add(
    "struct-cast-char",
    """
extern unsigned char region_map[];
void clear_reg_basic(int rm_offset)
{
    struct region_cell *c = (struct region_cell *)&region_map[rm_offset];

    if (c->terrain & 0x40) {
        c->base_kind = (char)(((unsigned char)stone_random_data[stone_random_count]) / 4 + 0x18);
    } else if (c->terrain & 0x80) {
        c->base_kind = (char)(((unsigned char)stone_random_data[stone_random_count]) / 4 + 0x1c);
    } else {
        c->base_kind = (char)(((unsigned char)stone_random_data[stone_random_count]) / 4 + 0x10);
    }
    if (c->terrain & 1) {
        c->occupant = 0;
    }
    c->terrain   &= 0xd8;
    c->edge_bits &= 2;
    c->_unused05  = 0;
    c->outside    = 0;
    c->edge_bits |= 1;
}
""",
    note="unsigned char[] + (struct region_cell *)&region_map[off] local ptr",
)


# ── trial 3: char array + struct cast re-formed inline each use ───
exp.add(
    "struct-inline-char",
    """
extern unsigned char region_map[];
void clear_reg_basic(int rm_offset)
{
    if (((struct region_cell *)&region_map[rm_offset])->terrain & 0x40) {
        ((struct region_cell *)&region_map[rm_offset])->base_kind = (char)(((unsigned char)stone_random_data[stone_random_count]) / 4 + 0x18);
    } else if (((struct region_cell *)&region_map[rm_offset])->terrain & 0x80) {
        ((struct region_cell *)&region_map[rm_offset])->base_kind = (char)(((unsigned char)stone_random_data[stone_random_count]) / 4 + 0x1c);
    } else {
        ((struct region_cell *)&region_map[rm_offset])->base_kind = (char)(((unsigned char)stone_random_data[stone_random_count]) / 4 + 0x10);
    }
    if (((struct region_cell *)&region_map[rm_offset])->terrain & 1) {
        ((struct region_cell *)&region_map[rm_offset])->occupant = 0;
    }
    ((struct region_cell *)&region_map[rm_offset])->terrain   &= 0xd8;
    ((struct region_cell *)&region_map[rm_offset])->edge_bits &= 2;
    ((struct region_cell *)&region_map[rm_offset])->_unused05  = 0;
    ((struct region_cell *)&region_map[rm_offset])->outside    = 0;
    ((struct region_cell *)&region_map[rm_offset])->edge_bits |= 1;
}
""",
    note="unsigned char[] + inline (struct region_cell *) cast per field",
)


# ── trial 4: region_map IS a struct region_cell[] (correctly typed),
#            still addressed by byte offset via a char* re-cast ─────
exp.add(
    "typed-array-cast",
    """
extern struct region_cell region_map[];
void clear_reg_basic(int rm_offset)
{
    struct region_cell *c = (struct region_cell *)((char *)region_map + rm_offset);

    if (c->terrain & 0x40) {
        c->base_kind = (char)(((unsigned char)stone_random_data[stone_random_count]) / 4 + 0x18);
    } else if (c->terrain & 0x80) {
        c->base_kind = (char)(((unsigned char)stone_random_data[stone_random_count]) / 4 + 0x1c);
    } else {
        c->base_kind = (char)(((unsigned char)stone_random_data[stone_random_count]) / 4 + 0x10);
    }
    if (c->terrain & 1) {
        c->occupant = 0;
    }
    c->terrain   &= 0xd8;
    c->edge_bits &= 2;
    c->_unused05  = 0;
    c->outside    = 0;
    c->edge_bits |= 1;
}
""",
    note="struct region_cell region_map[]; byte-offset via (char*)region_map+off",
)


# ── trial 5: region_map IS a struct region_cell[]; the param is a
#            human CELL INDEX (rm_offset/8 -> region_map[idx].field).
#            Tests whether the fully-human indexed form can match
#            (it cannot — PS bakes the byte offset into the caller). ─
exp.add(
    "typed-array-index",
    """
extern struct region_cell region_map[];
void clear_reg_basic(int rm_offset)
{
    int idx = rm_offset / 8;

    if (region_map[idx].terrain & 0x40) {
        region_map[idx].base_kind = (char)(((unsigned char)stone_random_data[stone_random_count]) / 4 + 0x18);
    } else if (region_map[idx].terrain & 0x80) {
        region_map[idx].base_kind = (char)(((unsigned char)stone_random_data[stone_random_count]) / 4 + 0x1c);
    } else {
        region_map[idx].base_kind = (char)(((unsigned char)stone_random_data[stone_random_count]) / 4 + 0x10);
    }
    if (region_map[idx].terrain & 1) {
        region_map[idx].occupant = 0;
    }
    region_map[idx].terrain   &= 0xd8;
    region_map[idx].edge_bits &= 2;
    region_map[idx]._unused05  = 0;
    region_map[idx].outside    = 0;
    region_map[idx].edge_bits |= 1;
}
""",
    note="struct region_cell region_map[]; human cell-index region_map[off/8]",
)


# ── trial 6: region_map IS a struct region_cell[]; param is a DIRECT
#            cell index (no divide confound).  Purpose is NOT to match
#            PS (the ABI meaning differs) but to expose the codegen:
#            does `region_map[idx].field` emit ×8 index scaling
#            (shl/lea) that PS's byte-offset addressing never has?
exp.add(
    "typed-array-index-direct",
    """
extern struct region_cell region_map[];
void clear_reg_basic(int idx)
{
    if (region_map[idx].terrain & 0x40) {
        region_map[idx].base_kind = (char)(((unsigned char)stone_random_data[stone_random_count]) / 4 + 0x18);
    } else if (region_map[idx].terrain & 0x80) {
        region_map[idx].base_kind = (char)(((unsigned char)stone_random_data[stone_random_count]) / 4 + 0x1c);
    } else {
        region_map[idx].base_kind = (char)(((unsigned char)stone_random_data[stone_random_count]) / 4 + 0x10);
    }
    if (region_map[idx].terrain & 1) {
        region_map[idx].occupant = 0;
    }
    region_map[idx].terrain   &= 0xd8;
    region_map[idx].edge_bits &= 2;
    region_map[idx]._unused05  = 0;
    region_map[idx].outside    = 0;
    region_map[idx].edge_bits |= 1;
}
""",
    note="struct region_cell region_map[]; DIRECT cell index region_map[idx] (expose x8 scaling)",
)
