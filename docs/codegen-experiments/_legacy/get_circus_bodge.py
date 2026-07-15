"""get_circus_bodge (landfill.c) — last (unsigned char) cast: zext vs mask.

PS.EXE `get_circus_bodge` (200 b @ ...) tests `(unsigned char)kind` against
8 consecutive values.  Every test re-zero-extends the kind byte with the
cast idiom `xor edx,edx; mov dl,al; cmp edx,N` (keeping `kind` in EAX).
The LAST test (0xf0) is where `kind` dies, and our build masks the dead
EAX in place (`and eax,0xff; cmp eax,0xf0`) instead of the zext idiom —
a 6 b last-use regalloc artefact.

This experiment bisects whether any source form makes the final cast use
the same zext idiom as the preceding seven.

CONCLUSION (2026-06): UNRESOLVED 6 b, no zero-cost lever.  The final
`(unsigned char)kind == 0xf0` test is `kind`'s last use, so Watcom masks the
dead EAX in place (`and eax,0xff`) instead of the `xor edx; mov dl,al` zext
idiom the preceding seven tests use.  `kind-live` (a trailing
`cm_sptr = (unsigned char)kind`) DOES restore the zext form — proving the
lever is keeping `kind` live — but the extra use costs its own 6 bytes
(net 12 b).  Caching the byte once (`unsigned char k = kind`) collapses all
eight zexts into one and diverges wildly (163 b).  A genuine last-use
regalloc artefact with no zero-cost source form; left as-is (matches the
in-source comment in landfill.c).

Run::  uv run c2 cgex run get_circus_bodge
"""

from c2.commands.cgex import Experiment

_PRELUDE = """
extern unsigned char city_map[];
extern int cm_sptr;
extern int sprite_image_no;
"""

_DEFS = """
unsigned char city_map[128000];
int cm_sptr;
int sprite_image_no;
"""

exp = Experiment(
    name="get_circus_bodge",
    ps_function="get_circus_bodge",
    externs={},
    prelude=_PRELUDE,
    extra_defs=_DEFS,
)

exp.add("baseline", """
void get_circus_bodge(int kind)
{
    unsigned char m = city_map[cm_sptr + 6] & 0x20;
    if (m != 0) return;
    if ((unsigned char)kind == 0xe9) sprite_image_no = 0x6d;
    if ((unsigned char)kind == 0xea) sprite_image_no = 0x6e;
    if ((unsigned char)kind == 0xeb) sprite_image_no = 0x6f;
    if ((unsigned char)kind == 0xec) sprite_image_no = 0x70;
    if ((unsigned char)kind == 0xed) sprite_image_no = 0x72;
    if ((unsigned char)kind == 0xee) sprite_image_no = 0x73;
    if ((unsigned char)kind == 0xef) sprite_image_no = 0x74;
    if ((unsigned char)kind == 0xf0) sprite_image_no = 0x75;
}
""", note="current source")


# Make the final compare not the last use: a trailing redundant test on kind.
exp.add("trailing-test", """
void get_circus_bodge(int kind)
{
    unsigned char m = city_map[cm_sptr + 6] & 0x20;
    if (m != 0) return;
    if ((unsigned char)kind == 0xe9) sprite_image_no = 0x6d;
    if ((unsigned char)kind == 0xea) sprite_image_no = 0x6e;
    if ((unsigned char)kind == 0xeb) sprite_image_no = 0x6f;
    if ((unsigned char)kind == 0xec) sprite_image_no = 0x70;
    if ((unsigned char)kind == 0xed) sprite_image_no = 0x72;
    if ((unsigned char)kind == 0xee) sprite_image_no = 0x73;
    if ((unsigned char)kind == 0xef) sprite_image_no = 0x74;
    if ((unsigned char)kind == 0xf0) sprite_image_no = 0x75;
    if ((unsigned char)kind == 0xf1) sprite_image_no = 0x76;
}
""", note="extra 9th test (keeps 0xf0 from being last)")


# Cache the byte once (one zext for all eight).
exp.add("cache-byte", """
void get_circus_bodge(int kind)
{
    unsigned char m = city_map[cm_sptr + 6] & 0x20;
    unsigned char k;
    if (m != 0) return;
    k = (unsigned char)kind;
    if (k == 0xe9) sprite_image_no = 0x6d;
    if (k == 0xea) sprite_image_no = 0x6e;
    if (k == 0xeb) sprite_image_no = 0x6f;
    if (k == 0xec) sprite_image_no = 0x70;
    if (k == 0xed) sprite_image_no = 0x72;
    if (k == 0xee) sprite_image_no = 0x73;
    if (k == 0xef) sprite_image_no = 0x74;
    if (k == 0xf0) sprite_image_no = 0x75;
}
""", note="unsigned char k = kind; (single zext)")


exp.add("final-local-int", """
void get_circus_bodge(int kind)
{
    unsigned char m = city_map[cm_sptr + 6] & 0x20;
    int k;
    if (m != 0) return;
    if ((unsigned char)kind == 0xe9) sprite_image_no = 0x6d;
    if ((unsigned char)kind == 0xea) sprite_image_no = 0x6e;
    if ((unsigned char)kind == 0xeb) sprite_image_no = 0x6f;
    if ((unsigned char)kind == 0xec) sprite_image_no = 0x70;
    if ((unsigned char)kind == 0xed) sprite_image_no = 0x72;
    if ((unsigned char)kind == 0xee) sprite_image_no = 0x73;
    if ((unsigned char)kind == 0xef) sprite_image_no = 0x74;
    k = (unsigned char)kind;
    if (k == 0xf0) sprite_image_no = 0x75;
}
""", note="final line through int local")

exp.add("final-local-uchar", """
void get_circus_bodge(int kind)
{
    unsigned char m = city_map[cm_sptr + 6] & 0x20;
    unsigned char k;
    if (m != 0) return;
    if ((unsigned char)kind == 0xe9) sprite_image_no = 0x6d;
    if ((unsigned char)kind == 0xea) sprite_image_no = 0x6e;
    if ((unsigned char)kind == 0xeb) sprite_image_no = 0x6f;
    if ((unsigned char)kind == 0xec) sprite_image_no = 0x70;
    if ((unsigned char)kind == 0xed) sprite_image_no = 0x72;
    if ((unsigned char)kind == 0xee) sprite_image_no = 0x73;
    if ((unsigned char)kind == 0xef) sprite_image_no = 0x74;
    k = kind;
    if (k == 0xf0) sprite_image_no = 0x75;
}
""", note="final line through uchar local")

# Same chain but kind reused at the end (forces it live).
exp.add("kind-live", """
void get_circus_bodge(int kind)
{
    unsigned char m = city_map[cm_sptr + 6] & 0x20;
    if (m != 0) return;
    if ((unsigned char)kind == 0xe9) sprite_image_no = 0x6d;
    if ((unsigned char)kind == 0xea) sprite_image_no = 0x6e;
    if ((unsigned char)kind == 0xeb) sprite_image_no = 0x6f;
    if ((unsigned char)kind == 0xec) sprite_image_no = 0x70;
    if ((unsigned char)kind == 0xed) sprite_image_no = 0x72;
    if ((unsigned char)kind == 0xee) sprite_image_no = 0x73;
    if ((unsigned char)kind == 0xef) sprite_image_no = 0x74;
    if ((unsigned char)kind == 0xf0) sprite_image_no = 0x75;
    cm_sptr = (unsigned char)kind;
}
""", note="trailing use of (unsigned char)kind keeps it live")
