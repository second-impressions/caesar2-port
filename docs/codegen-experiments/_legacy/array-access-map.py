"""Rule 88 — Array / struct-array addressing-mode probe matrix.

This experiment maps how Watcom 10.0a lowers indexed data access as a
function of (a) element type width + signedness, (b) whether the index
lands in a free register, (c) struct stride, and (d) whether an address
is taken.  There is no single PS reference function — the value is in
the per-trial disasm, so run with ``--trial <name>`` to dump the asm:

    uv run c2 cgex run array-access-map                 # size table
    uv run c2 cgex run array-access-map --trial rd_signed_char
    uv run c2 cgex run array-access-map --trial stride20

Findings (see Rule 88 in docs/watcom-codegen-patterns.md):

* 88a/88b — scalar `arr[i]` read.  Busy dest (index in EAX): unsigned
  byte/short widen via `mov; and`; free dest (const index): `xor`-first.
  signed → `movsx`.  `& 0xff` always forces `mov; and`.
* 88c — struct `tbl[i].f`: stride = odd × SIB_scale (scale = largest
  pow2 divisor ≤ 8; pure pow2 ≤8 → SIB only, >8 → single shl).  Odd
  cofactor via shift+add/sub.  Field offset folds into disp.
* 88d — address-taken → full byte offset + disp32 base (get_new_sslot).
* 88e — char store: `mov byte ptr [m], rl`, no mask.

Confirmed against byte-exact PS: get_new_sslot, select_a_unit,
plague_an_atom.
"""

from c2.commands.cgex import Experiment

exp = Experiment(
    name="array-access-map",  # no PS reference; observe disasm
    extra_defs="void use(char *p) { (void)p; }\n",
)


# ── 88a/88b: scalar reads, variable index (busy EAX) ─────────────
for _slug, _decl in {
    "plain_char": "char arr[256];",
    "unsigned_char": "unsigned char arr[256];",
    "signed_char": "signed char arr[256];",
    "short": "short arr[256];",
    "ushort": "unsigned short arr[256];",
    "int": "int arr[256];",
}.items():
    exp.add(
        f"rd_{_slug}",
        f"{_decl}\nint g(int i) {{ return arr[i]; }}\n",
        note=f"var-idx read arr[i]->int ({_slug})",
    )
    # const index → destination register is free
    exp.add(
        f"const_{_slug}",
        f"{_decl}\nint g(void) {{ return arr[7]; }}\n",
        note=f"const-idx read arr[7]->int ({_slug})",
    )


# ── 88b: & 0xff vs (unsigned char) cast vs bare, free vs busy ────
exp.add("and_const",
        "char arr[256];\nint g(void){ return arr[7] & 0xff; }\n",
        note="free dest + &0xff -> forces mov;and")
exp.add("cast_const",
        "char arr[256];\nint g(void){ return (unsigned char)arr[7]; }\n",
        note="free dest + cast -> xor-first")
exp.add("and_var",
        "char arr[256];\nint g(int i){ return arr[i] & 0xff; }\n",
        note="busy dest + &0xff -> mov;and")
exp.add("cast_var",
        "char arr[256];\nint g(int i){ return (unsigned char)arr[i]; }\n",
        note="busy dest + cast -> mov;and (indistinguishable)")


# ── 88c: struct-array stride factoring ───────────────────────────
for _slug, _sdef in {
    "stride8": "struct S { int a; int b; };",
    "stride12": "struct S { int a, b, c; };",
    "stride16": "struct S { int a[4]; };",
    "stride20": "struct S { int a; char name[16]; };",
    "stride24": "struct S { int a[6]; };",
    "stride40": "struct S { int a[10]; };",
    "stride6": "struct S { int a; signed char sc; char uc; };",
    "stride10": "struct S { char a[10]; };",
    "stride7": "struct S { char a[7]; };",
}.items():
    exp.add(
        _slug,
        f"{_sdef}\nstruct S tbl[64];\n"
        "int g(int i) { return tbl[i].a; }\n",
        note=f"struct-array read tbl[i].a ({_slug})",
    )


# ── 88c (reuse) + 88e (writes) + signed/unsigned struct fields ───
exp.add(
    "field_mix",
    """
struct S { int a; signed char sc; char uc; };
struct S tbl[64];
int multi(int i) { return tbl[i].a + tbl[i].uc; }   /* reuse i*odd, two SIB loads */
int sfield(int i) { return tbl[i].sc; }             /* signed char field -> movsx */
void wr(int i, int v) { tbl[i].a = v; }             /* int write */
""",
    note="offset reuse / signed field / int write",
)

exp.add(
    "char_store",
    "char carr[256];\nvoid wrc(int i, int v) { carr[i] = v; }\n",
    note="char store -> mov byte ptr [m], rl (no mask)",
)


# ── 88d: address-taken forces full byte offset + disp32 ──────────
exp.add(
    "addr_taken",
    """
struct S { int count; char name[16]; };
struct S tbl[64];
extern void use(char *p);
void g(int i) { use(tbl[i].name); }      /* &field -> full byte offset */
int *h(int i) { return &tbl[i].count; }  /* &element */
""",
    note="address-taken -> shl;add;shl (full byte offset) + disp32 base",
)
