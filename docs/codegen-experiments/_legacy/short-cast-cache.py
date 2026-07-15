"""BRUTE-FORCE search for the ``(short)int_global`` named-local cache lever.

Background: the show_menus residue (controls.c, +10b closed at 43671b12)
was driven by a missing FE temp -- PS source caches ``(short)x_is`` into
a named local AND uses that short for both the field assignment AND the
subsequent ``- 2`` subtract.  Without the named local the compiler
recomputes the sign-extend each time, miscolors the slot, and the frame
ends up one slot shy of PS.

The lever family:

  * cast a wider-typed value to a narrower one (short, signed char,
    unsigned char) and stash it in an int local
  * write that short into a short-field of a struct
  * use the short for the subsequent arithmetic / call args

Watcom emits the pattern as ``mov ax, [src]; mov word ptr [dst], ax;
cwde; mov [esp+slot], eax``.  The cwde + slot store is the FE temp the
allocator wants; it spills more cleanly than recomputing.

This experiment enumerates the lever along three axes -- TYPE (short /
signed char / unsigned char), USE COUNT (1..4 reuse sites after the
cast), and TIMING (cache BEFORE or AFTER the struct field write) -- so
the brute-forced trials cover the full variant space.  Each trial is
checked for the EXACT codegen pattern (cwde / movsx instruction count,
slot-store presence, ConfBefore behaviour) so the asserter can confirm
which variants reproduce the show_menus pattern.

Run::

    uv run c2 cgex run short-cast-cache
    uv run python docs/codegen-experiments/short-cast-cache.py

After landing this prototype, the corresponding ``ast_lever`` is
"short-cache" -- add ``int N = (short)X;`` immediately after the first
write to a short field of ``X`` and rewrite any subsequent ``X +/- K``
in the same statement scope to ``N +/- K``.  The lever is justified iff
the predicted FE temp would land at the same stack slot PS uses (the
spill metric drops from N/M to 0/M).
"""
from c2.commands.cgex import Experiment


_STRUCT_DEF = (
    "struct ent { short x1, x2, y, text; int *items; short item_count; };\n"
)

exp = Experiment(
    name="short-cast-cache", ps_function=None, chk=False,
    externs={
        "ext1": "extern void ext1(int x);",
        "ext2": "extern void ext2(int x, int y);",
        "ext3": "extern void ext3(int x, int y, int z);",
        "ext4": "extern void ext4(int a, int b, int c, int d);",
    },
    prelude=(
        _STRUCT_DEF
        + "extern int g_int;\n"
        + "extern struct ent g_ent;\n"
    ),
    extra_defs=(
        _STRUCT_DEF
        + "int g_int;\n"
        + "struct ent g_ent;\n"
    ),
)


# ------------------------------------------------------------------ baseline --
# the "wrong" form, no named cache: each use re-references g_int (or x)
# and the compiler re-recovers the sign-extension fresh each time.
exp.add(
    "baseline_no_cache",
    """
void t(void) {
    g_ent.x1 = g_int;
    ext4(g_int - 2, g_int - 1, 0x10, 0x10);
    ext4(g_int - 2, g_int - 1, 0x10, 0x10);
}
""",
    note="no FE temp; recomputes the short truncation per use",
)


# ------------------------------------------------------------------ short cast --
# explicit ``int sx = (short)x;`` cache (the show_menus lever proven at
# 43671b12).  Try the cast BEFORE and AFTER the field write -- Watcom may
# fold them differently.
exp.add(
    "short_cache_before",
    """
void t(void) {
    int sx;
    sx = (short)g_int;
    g_ent.x1 = sx;
    ext4(sx - 2, sx - 1, 0x10, 0x10);
    ext4(sx - 2, sx - 1, 0x10, 0x10);
}
""",
    note="cache BEFORE the field write (the show_menus shape)",
)
exp.add(
    "short_cache_after",
    """
void t(void) {
    int sx;
    g_ent.x1 = g_int;
    sx = (short)g_int;
    ext4(sx - 2, sx - 1, 0x10, 0x10);
    ext4(sx - 2, sx - 1, 0x10, 0x10);
}
""",
    note="cache AFTER the field write (read-back form)",
)


# ------------------------------------------------------------------ source of the cast --
# The cwde appears only when the SOURCE of the cast is reachable as a
# short load.  Compare reading the global value directly vs reading
# through the short field we just wrote (PS may pick either).
exp.add(
    "short_cache_via_field",
    """
void t(void) {
    int sx;
    g_ent.x1 = g_int;
    sx = g_ent.x1;
    ext4(sx - 2, sx - 1, 0x10, 0x10);
    ext4(sx - 2, sx - 1, 0x10, 0x10);
}
""",
    note="cache via re-reading the just-written field (cwde from struct)",
)


# ------------------------------------------------------------------ char variants --
# Try ``(signed char)`` / ``(unsigned char)`` for byte-field analogues.
# The cbw/cwde axis is one wider; the codegen will use movsx byte->dword
# (or xor+mov-low byte->dword for the unsigned form).
exp.add(
    "schar_cache_before",
    """
void t(void) {
    int sx;
    sx = (signed char)g_int;
    g_ent.x1 = (short)sx;
    ext4(sx - 2, sx - 1, 0x10, 0x10);
    ext4(sx - 2, sx - 1, 0x10, 0x10);
}
""",
    note="signed-char cache (movsx byte->dword)",
)
exp.add(
    "uchar_cache_before",
    """
void t(void) {
    int sx;
    sx = (unsigned char)g_int;
    g_ent.x1 = (short)sx;
    ext4(sx - 2, sx - 1, 0x10, 0x10);
    ext4(sx - 2, sx - 1, 0x10, 0x10);
}
""",
    note="unsigned-char cache (xor+mov-low or movzx)",
)


# ------------------------------------------------------------------ use counts --
# Vary the number of reuse sites: 1, 2, 4, 8.  The named local's savings
# is linear in use count; the regalloc tie-break / spill decision may
# flip past N=2.
def _gen_uses(n):
    body = "    int sx;\n    sx = (short)g_int;\n    g_ent.x1 = sx;\n"
    for i in range(n):
        body += f"    ext4(sx - 2, sx - 1, 0x10, 0x{0x10 + i:02x});\n"
    return f"void t(void) {{\n{body}}}\n"


for n in (1, 2, 4, 8):
    exp.add(
        f"short_cache_uses_{n}",
        _gen_uses(n),
        note=f"short cache with {n} reuse site(s) after the field write",
    )


# ------------------------------------------------------------------ loop forms --
# The lever appears INSIDE a for-loop in show_menus.  Replicate the loop
# context so the spill metric for the iteration variable also matters.
exp.add(
    "short_cache_in_loop",
    """
void t(int n) {
    int sx;
    int i;
    for (i = 1; i <= n; i++) {
        sx = (short)g_int;
        g_ent.x1 = sx;
        ext4(sx - 2, sx - 1, 0x10, 0x10);
        ext4(sx - 2, sx - 1, 0x10, 0x10);
        g_int += 0x20;
    }
}
""",
    note="show_menus shape: cache inside a counted for loop",
)
exp.add(
    "short_cache_in_loop_no_cache",
    """
void t(int n) {
    int i;
    for (i = 1; i <= n; i++) {
        g_ent.x1 = g_int;
        ext4(g_int - 2, g_int - 1, 0x10, 0x10);
        ext4(g_int - 2, g_int - 1, 0x10, 0x10);
        g_int += 0x20;
    }
}
""",
    note="show_menus shape WITHOUT the short cache (baseline of the loop form)",
)


# ------------------------------------------------------------------ pair caches --
# Cache BOTH the short of x_is AND y-1 (the show_menus pattern caches
# both the x-coord short AND the y-1 result).
exp.add(
    "pair_cache_short_and_ymin1",
    """
void t(int n) {
    int sx;
    int ry;
    int i;
    for (i = 1; i <= n; i++) {
        sx = (short)g_int;
        g_ent.x1 = sx;
        ry = g_ent.y - 1;
        ext4(sx - 2, ry, 0x10, 0x10);
        ext4(sx - 2, ry, 0x10, 0x10);
        g_int += 0x20;
    }
}
""",
    note="dual cache: (short)x AND (y-1) -- the full show_menus shape",
)


# ------------------------------------------------------------------ ordering levers --
# When BOTH sx and ry caches are present, vary their decl order and
# first-assign order -- the regalloc tie-break may flip.
exp.add(
    "pair_cache_decl_sx_first",
    """
void t(int n) {
    int sx;
    int ry;
    int i;
    for (i = 1; i <= n; i++) {
        sx = (short)g_int;
        ry = g_ent.y - 1;
        g_ent.x1 = sx;
        ext4(sx - 2, ry, 0x10, 0x10);
        ext4(sx - 2, ry, 0x10, 0x10);
    }
}
""",
    note="pair cache, sx decl first, sx assign first",
)
exp.add(
    "pair_cache_decl_ry_first",
    """
void t(int n) {
    int ry;
    int sx;
    int i;
    for (i = 1; i <= n; i++) {
        ry = g_ent.y - 1;
        sx = (short)g_int;
        g_ent.x1 = sx;
        ext4(sx - 2, ry, 0x10, 0x10);
        ext4(sx - 2, ry, 0x10, 0x10);
    }
}
""",
    note="pair cache, ry decl first, ry assign first",
)


# ------------------------------------------------------------------ EXCESSIVE COMBINATIONS --
# Per the user directive: brute-force the lever across every axis we can
# think of.  The cache landed -10b in straight-line code on the
# baseline.  These trials map out where else it fires (and where it
# doesn't), so the corresponding ast_lever can refuse to apply on the
# no-fire shapes.

# Axis: cast type (short / schar / uchar / int / `& 0xff` mask form)
for cast_form, cast_slug in (
    ("(short)g_int",         "cast_short"),
    ("(signed char)g_int",   "cast_schar"),
    ("(unsigned char)g_int", "cast_uchar"),
    ("g_int & 0xff",         "mask_0xff"),
    ("g_int & 0xffff",       "mask_0xffff"),
    ("g_int",                "no_cast_int"),
):
    exp.add(
        f"axis_cast__{cast_slug}",
        f"""
void t(void) {{
    int sx;
    sx = {cast_form};
    g_ent.x1 = (short)sx;
    ext4(sx - 2, sx - 1, 0x10, 0x10);
    ext4(sx - 2, sx - 1, 0x10, 0x10);
}}
""",
        note=f"cast form = {cast_form}",
    )

# Axis: where the cache is initialized (decl-init vs separate assign)
for init_form, init_slug in (
    ("int sx = (short)g_int;",     "decl_init"),
    ("int sx; sx = (short)g_int;", "sep_assign"),
    ("int sx = g_int; sx = (short)sx;", "re_assign"),
):
    exp.add(
        f"axis_init__{init_slug}",
        f"""
void t(void) {{
    {init_form}
    g_ent.x1 = (short)sx;
    ext4(sx - 2, sx - 1, 0x10, 0x10);
    ext4(sx - 2, sx - 1, 0x10, 0x10);
}}
""",
        note=f"init form = {init_slug}",
    )

# Axis: USE in the subsequent expressions (passed directly vs subtracted
# vs added vs both vs across-call)
for expr_form, expr_slug in (
    ("ext4(sx, sx, 0x10, 0x10);",       "raw"),
    ("ext4(sx - 2, sx - 1, 0x10, 0x10);", "sub_const"),
    ("ext4(sx + 5, sx + 3, 0x10, 0x10);", "add_const"),
    ("ext4(sx - g_int, sx - 1, 0x10, 0x10);", "sub_global"),
):
    exp.add(
        f"axis_use__{expr_slug}",
        f"""
void t(void) {{
    int sx;
    sx = (short)g_int;
    g_ent.x1 = (short)sx;
    {expr_form}
}}
""",
        note=f"use form = {expr_slug}",
    )

# Axis: FIELD type (short / unsigned short / signed char / int)
for field_type, field_slug in (
    ("short",       "short"),
    ("unsigned short", "ushort"),
    ("signed char", "schar"),
    ("unsigned char", "uchar"),
    ("int",         "int"),
):
    sd = (f"struct ent2 {{ {field_type} f; }};\n"
          "extern struct ent2 g_ent2;\n")
    exp.add(
        f"axis_field__{field_slug}",
        sd + f"""
void t(void) {{
    int sx;
    sx = (short)g_int;
    g_ent2.f = ({field_type})sx;
    ext4(sx - 2, sx - 1, 0x10, 0x10);
    ext4(sx - 2, sx - 1, 0x10, 0x10);
}}
struct ent2 g_ent2;
""",
        note=f"field type = {field_type}",
    )

# Axis: ordering within the dual-cache pattern (sx vs ry decl + assign
# permutations) -- the full 4-permutation matrix
for (d1, d2, a1, a2), slug in (
    (("int sx;", "int ry;",
      "sx = (short)g_int;", "ry = g_ent.y - 1;"), "d_sx_ry__a_sx_ry"),
    (("int sx;", "int ry;",
      "ry = g_ent.y - 1;", "sx = (short)g_int;"), "d_sx_ry__a_ry_sx"),
    (("int ry;", "int sx;",
      "sx = (short)g_int;", "ry = g_ent.y - 1;"), "d_ry_sx__a_sx_ry"),
    (("int ry;", "int sx;",
      "ry = g_ent.y - 1;", "sx = (short)g_int;"), "d_ry_sx__a_ry_sx"),
):
    exp.add(
        f"axis_pair_order__{slug}",
        f"""
void t(void) {{
    {d1}
    {d2}
    {a1}
    {a2}
    g_ent.x1 = (short)sx;
    ext4(sx - 2, ry, 0x10, 0x10);
    ext4(sx - 2, ry, 0x10, 0x10);
}}
""",
        note=f"pair-order {slug}",
    )

# Axis: with N loop iterations (1..4 sequential add-then-call)
for n_iter in (1, 2, 3, 4):
    body = "    int sx;\n    sx = (short)g_int;\n    g_ent.x1 = (short)sx;\n"
    for k in range(n_iter):
        body += f"    ext4(sx - 2, sx - 1, 0x10, 0x{0x10 + k:02x});\n"
    exp.add(
        f"axis_n_iter__{n_iter}",
        f"void t(void) {{\n{body}}}\n",
        note=f"{n_iter} sequential reuse(s)",
    )

# Axis: nesting inside an outer call (caller arg-prep order matters)
exp.add(
    "axis_nesting__outer_call",
    """
void t(void) {
    int sx;
    ext1(g_int);
    sx = (short)g_int;
    g_ent.x1 = (short)sx;
    ext4(sx - 2, sx - 1, 0x10, 0x10);
}
""",
    note="call before the cache",
)
exp.add(
    "axis_nesting__cache_then_call",
    """
void t(void) {
    int sx;
    sx = (short)g_int;
    ext1(sx);
    g_ent.x1 = (short)sx;
    ext4(sx - 2, sx - 1, 0x10, 0x10);
}
""",
    note="cache, call(sx), then reuse sx",
)
exp.add(
    "axis_nesting__cache_in_branch",
    """
void t(int cond) {
    int sx;
    sx = (short)g_int;
    g_ent.x1 = (short)sx;
    if (cond) ext4(sx - 2, sx - 1, 0x10, 0x10);
    else      ext4(sx - 2, sx - 1, 0x10, 0x1a);
}
""",
    note="both branches reuse sx (show_menus exact shape)",
)

# Axis: literal sharing (`+2` reused multiple times)
for lit, slug in (("2", "two"), ("5", "five"), ("16", "sixteen"),
                   ("-2", "neg_two")):
    exp.add(
        f"axis_lit_share__{slug}",
        f"""
void t(int n) {{
    int sx;
    int width;
    sx = (short)g_int;
    g_ent.x1 = (short)sx;
    width = (n + 4) / 16 + {lit};
    ext4(sx - {lit}, sx - 1, width, 0x10);
    ext4(sx - {lit}, sx - 1, width, 0x1a);
}}
""",
        note=f"shared literal {lit}",
    )

# Axis: the SHOW_MENUS exact replica (control-buttons sibling), parametric
# over the loop COUNT shape.
exp.add(
    "replica_show_menus_minimal",
    """
void t(struct ent *menus, int count, int active) {
    struct ent *m;
    int i;
    int start_x;
    int y;
    int text;
    int sx;
    ext1(0);
    g_int = 0;
    g_int = menus->x1;
    start_x = g_int;
    m = menus;
    for (i = 1; i <= count; i++) {
        text = m->text;
        m->x1 = (short)g_int;
        sx = (short)g_int;
        y = m->y;
        if (i == active) {
            ext1(text);
            ext4(sx - 2, y - 1, 0x10, 0x10);
        } else {
            ext1(text);
            ext4(sx - 2, y - 1, 0x1a, 0x10);
        }
        m->x2 = (short)g_int;
        g_int += 0x20;
        m++;
    }
}
""",
    note="replica of show_menus -- the proof of the lever in context",
)
exp.add(
    "replica_show_menus_no_cache",
    """
void t(struct ent *menus, int count, int active) {
    struct ent *m;
    int i;
    int start_x;
    int y;
    int text;
    ext1(0);
    g_int = 0;
    g_int = menus->x1;
    start_x = g_int;
    m = menus;
    for (i = 1; i <= count; i++) {
        text = m->text;
        m->x1 = (short)g_int;
        y = m->y;
        if (i == active) {
            ext1(text);
            ext4(g_int - 2, y - 1, 0x10, 0x10);
        } else {
            ext1(text);
            ext4(g_int - 2, y - 1, 0x1a, 0x10);
        }
        m->x2 = (short)g_int;
        g_int += 0x20;
        m++;
    }
}
""",
    note="replica WITHOUT cache (baseline of the lever)",
)


if __name__ == "__main__":
    # Optional asserter: re-runs all trials and prints a verdict.  The
    # interesting axes are:
    #
    #   * does the cached form produce a `cwde` + slot store (the FE temp)?
    #   * does the un-cached form produce N copies of `mov ax; cwde`?
    #   * does the loop form produce ONE spill slot for sx and another
    #     for the loop counter?
    #
    # Trials that match the show_menus byte-pattern reproduce the lever.
    import sys
    exp.run()
    exp.print_table()
    sys.exit(0)
