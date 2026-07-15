"""get_best_elastic_value — byte-field temp width + dir/v register tie.

PS `get_best_elastic_value` (182 b @ 0x666A4) scans 4 directions; per
direction it reads the byte field `road_aqueduct` (unsigned char @ +2)
into a temp `v` and tests `v != 0 && v < best_elastic_value`.

PS `-d1` line walk (the source-shape witness):
    L391  best_elastic_value = 100;      (mov [val],0x64  -- immediate)
    L392  best_elastic_dirc  = 0;        (xor ebp,ebp; mov [dirc],ebp)
    L394  i = 0;                          (xor ecx,ecx)
    L396  while ((i++) < 4)               (mov eax,ecx; inc ecx; cmp eax,4)
    L398  if (dir == 0)                   (test edx,edx; jne)   <- dir in EDX
    L400  if (y > 0)                      (test esi,esi; jle)   <- y in ESI
    L402  v = CM_N(ptr).road_aqueduct;    (mov al,[ebx+..])     <- v in AL
    L403  if (v != 0 && v < best...)      (test al,al; je; and eax,0xff; cmp eax,[val])

So PS: x=EDI, y=ESI, ptr=EBX, dir=EDX, i=ECX, v=AL(EAX), EBP holds 0.
The widening is LAZY (mov al; test al,al; ...; and eax,0xff) -> `v` is
`unsigned char`.

Residue history:
  * `int v`          -> widening EAGER (xor eax,eax; mov al; test eax,eax)
                        != PS; prologue/regalloc otherwise matches (107 b,
                        cascade from the size diff).
  * `unsigned char v`-> widening matches PS, BUT v lands in DL not AL,
                        which evicts `dir` from EDX to EAX (141 b).

Goal: `unsigned char v` (lazy widen) AND v=AL / dir=EDX (PS layout).

--- FINDING (2026-06-18) ---------------------------------------------
The residue is a type<->EBP-materialization COUPLING, not a plain tie:

  * PS allocates a 3rd callee-save (EBP) to hold the constant 0 for the
    `best_elastic_dirc = 0;` store.  It is forced to materialise 0 in a
    register because the source order is
        L391 best_elastic_value = 100;
        L392 best_elastic_dirc  = 0;   <- store here, NO zero reg exists yet
        L394 i = 0;                    <- ECX only zeroed here, AFTER
    so at L392 there is no zeroed register to reuse -> xor ebp,ebp; mov.
    With EBP live, dir stays in EDX and v gets AL (EAX free).

  * `int v`  : eager widen `xor eax,eax; mov al` PER load (!= PS's shared
    `mov al ... and eax,0xff`), BUT keeps PS's register layout (EBP=0,
    dir=EDX).  107 b -- the size-changing per-load xor cascades.
  * `unsigned char v` : widen STRUCTURE matches PS (byte test + shared
    `and`), but the lower register pressure lets the scheduler HOIST the
    `i = 0` (xor ecx) ahead of the dirc store and reuse ECX=0 -> EBP is
    never materialised -> dir spills to EAX, v to DL.  139 b.

Levers tried in cgex, all inert/worse: decl order (i/dir/v all perms),
for-loop init, `dir = dirc` as a late statement, inline-no-temp (217 b).
The EBP materialisation cannot be forced from C source once `v` is a
byte: the i=0 / dirc=0 zero-merge is a scheduler decision driven by the
pressure that v's type sets.  NOT closed -- the open lever is whether
any source shape blocks the zero-merge while keeping `unsigned char v`.
Identical-body twin: `get_best_rm_elastic_value` (same residue).

--- RE-CONFIRMED (2026-06-19) ----------------------------------------
Independently re-derived the whole finding.  Two hypotheses re-tested
and DISPROVED as closers:
  * "PS read the field uncached" (no `v` temp): PS emits ONE `mov al`
    per direction (single read), so the field WAS cached.  A nested
    uncached body (`if (y>0) { if (field!=0 && field<best) ... }`)
    makes Watcom read the byte TWICE (`cmp byte [m],0` + `mov cl,[m]`)
    -- 124 b, worse, and reorders the else-if chain (Rule 152 misses).
    The fully-&&-combined inline is 180 b (cgex `inline-no-temp`).
  * raw `unsigned char *cm` pointer instead of the struct macro:
    Watcom caches the pointer and spills `best_elastic_dirc` to memory
    -> 140 b, worse.  Macro field access is correct (matches the asm
    offsets exactly); do NOT drop it.
`c2 permute --depth 2` on the uchar body: 0 improvements (all 15
variants >= 141; confirms cascade "savings-major, not decl/use-order").
The dir(sav=121)/v(sav=120) gap is exactly the `int dir = dirc` copy's
1@d0 ref; no byte-preserving source edit removes it or raises v.
Verdict: genuine scheduler-oracle residue.  Committed equilibrium
stays `int v` (107 b) -- fewer bytes than the more-faithful but
regalloc-disturbed `unsigned char v` (139 b).

--- LAYOUT CRACKED, widen-coupling found (2026-06-19, session 2) ------
The register layout IS reachable.  Root cause of the `unsigned char v`
miss is a 1-unit SAVINGS gap, not a scheduler black box: the direction
value (`int dir = dirc` -> sav 121, or the param `dirc` -> sav 122)
out-ranks `v` (byte, sav 120) by 1-2, so it claims EAX first and evicts
`v` from AL.  PROOF: `best_elastic_value = v & 0xff` adds exactly one
depth-1 `v` ref (+10 sav -> v=130), which flips the whole allocation to
PS's layout -- push ebp, `mov edx,ecx`, dir=EDX, i=ECX, v=AL all match
(139 b -> 98 b, BELOW the 107 int-v floor).  `both-mask` (+2 refs,
v=140) OVERSHOOTS back to 139 (non-monotonic, as the regalloc docs
warn) -- the window is exactly +1.

BUT the +1 is UNCLOSABLE faithfully: the savings boost must come from an
emitted `v` op, and every such op IS the divergence --
  * `v & 0xff` (store or cmp) -> the explicit mask is a SECOND widen;
    PS shares ONE in-place `and eax,0xff` across cmp+store, recomp
    splits it into `movzx ebp,al` (cmp, preserves al) + `and eax,0xff`
    (store).  Residue 98 b = the 2 widen rows + tail reorder.
  * a duplicate byte test (`v!=0 && v!=0`) emits a 2nd `test` (110 b).
  * a named int temp `vi=v` COALESCES back to one value (139 b).
  * folded refs (`v-v`, `v&0`, `v*0`) drop before CalcSavings (inert).
PS's binary (built by the SAME 10.0a that builds our recomp, which
puts v in DL for every faithful form) has `v` winning with NO extra
op -- so PS's source must give `dir` a lower ref count or `v` a higher
one through a shape not yet found (or an explicit cast we can't see).
Same class as font_format_split (lib32.c): `and reg,0xff` vs `movzx`
byte-squat tie -> "pure pressure tie-break, no faithful source handle."

Also re-confirmed dead: uncached field (PS reads ONCE = cached; nested
uncached double-reads, 124 b), raw `unsigned char *` pointer (spills
best_elastic_dirc, 140 b), init reorder (merges the EBP zero, 151-4 b),
combined-&& branches, count-down / do-while loops -- all worse.
NEXT: needs the 10.0a allocator/savings oracle on `dir` vs `v` to see
why PS's direction value ranks below the byte temp.
----------------------------------------------------------------------

Run::  uv run c2 cgex run get_best_elastic_value
"""

from c2.commands.cgex import Experiment

_PRELUDE = """
struct city_cell {
    char         pad0[2];
    unsigned char road_aqueduct;   /* +0x02 */
    char         pad3[20 - 3];
};
#define CITY_ROW         1600
#define CITY_CELL_BYTES  20
#define CM_CELL(off)  (*(struct city_cell *)((unsigned char *)city_map + (off)))
#define CM_N(off)   CM_CELL((off) - CITY_ROW)
#define CM_S(off)   CM_CELL((off) + CITY_ROW)
#define CM_E(off)   CM_CELL((off) + CITY_CELL_BYTES)
#define CM_W(off)   CM_CELL((off) - CITY_CELL_BYTES)
extern unsigned char city_map[];
extern int best_elastic_value;
extern int best_elastic_dirc;
"""

_DEFS = _PRELUDE + """
unsigned char city_map[128000];
int best_elastic_value;
int best_elastic_dirc;
"""

exp = Experiment(
    name="get_best_elastic_value",
    ps_function="get_best_elastic_value",
    prelude=_PRELUDE,
    extra_defs=_DEFS,
)

_BODY_UCHAR = """
void get_best_elastic_value(int x, int y, int ptr, int dirc)
{
    int i;
    int dir = dirc;
    unsigned char v;

    best_elastic_value = 100;
    best_elastic_dirc = 0;
    i = 0;
    while (i++ < 4) {
        if (dir == 0) {
            if (y > 0) {
                v = CM_N(ptr).road_aqueduct;
                if (v != 0 && v < best_elastic_value) {
                    best_elastic_value = v;
                    best_elastic_dirc = dir;
                }
            }
        } else if (dir == 1) {
            if (x < 79) {
                v = CM_E(ptr).road_aqueduct;
                if (v != 0 && v < best_elastic_value) {
                    best_elastic_value = v;
                    best_elastic_dirc = dir;
                }
            }
        } else if (dir == 2) {
            if (y < 79) {
                v = CM_S(ptr).road_aqueduct;
                if (v != 0 && v < best_elastic_value) {
                    best_elastic_value = v;
                    best_elastic_dirc = dir;
                }
            }
        } else if (dir == 3) {
            if (x > 0) {
                v = CM_W(ptr).road_aqueduct;
                if (v != 0 && v < best_elastic_value) {
                    best_elastic_value = v;
                    best_elastic_dirc = dir;
                }
            }
        }
        dir++;
        if (dir > 3) dir = 0;
    }
}
"""

exp.add("uchar-v", _BODY_UCHAR, note="unsigned char v (Mac type) — widen matches, v=DL?")

exp.add("int-v", _BODY_UCHAR.replace("unsigned char v;", "int v;"),
        note="int v — eager widen, dir=EDX (original 107b)")


# ── declaration-order / dir-handling variants (all unsigned char v) ──
def _mk(decls, dir_init="    int dir = dirc;", body_dir="dir"):
    loop = _BODY_UCHAR
    # strip the original decls block
    head = "void get_best_elastic_value(int x, int y, int ptr, int dirc)\n{\n"
    tail = loop.split("    while (i++ < 4) {", 1)[1]
    return head + decls + "\n    best_elastic_value = 100;\n    best_elastic_dirc = 0;\n    i = 0;\n    while (i++ < 4) {" + tail

exp.add("decl-dir-i-v", _mk("    int dir = dirc;\n    int i;\n    unsigned char v;"),
        note="decl: dir, i, v")
exp.add("decl-i-v-dir", _mk("    int i;\n    unsigned char v;\n    int dir = dirc;"),
        note="decl: i, v, dir")
exp.add("decl-v-i-dir", _mk("    unsigned char v;\n    int i;\n    int dir = dirc;"),
        note="decl: v, i, dir")
exp.add("decl-v-dir-i", _mk("    unsigned char v;\n    int dir = dirc;\n    int i;"),
        note="decl: v, dir, i")
exp.add("dir-split", _mk("    int i;\n    int dir;\n    unsigned char v;").replace(
        "    i = 0;\n", "    dir = dirc;\n    i = 0;\n"),
        note="dir = dirc as separate stmt after value/dirc init")


# ── inline (no v temp): the field is uchar, so `field != 0` is a byte
#    test and `field < best` promotes -> PS's mov al / and eax,0xff shape
#    with no eager widen and no byte-reg reshuffle. ──
_INLINE = """
void get_best_elastic_value(int x, int y, int ptr, int dirc)
{
    int i;
    int dir = dirc;

    best_elastic_value = 100;
    best_elastic_dirc = 0;
    i = 0;
    while (i++ < 4) {
        if (dir == 0) {
            if (y > 0 && CM_N(ptr).road_aqueduct != 0
                && CM_N(ptr).road_aqueduct < best_elastic_value) {
                best_elastic_value = CM_N(ptr).road_aqueduct;
                best_elastic_dirc = dir;
            }
        } else if (dir == 1) {
            if (x < 79 && CM_E(ptr).road_aqueduct != 0
                && CM_E(ptr).road_aqueduct < best_elastic_value) {
                best_elastic_value = CM_E(ptr).road_aqueduct;
                best_elastic_dirc = dir;
            }
        } else if (dir == 2) {
            if (y < 79 && CM_S(ptr).road_aqueduct != 0
                && CM_S(ptr).road_aqueduct < best_elastic_value) {
                best_elastic_value = CM_S(ptr).road_aqueduct;
                best_elastic_dirc = dir;
            }
        } else if (dir == 3) {
            if (x > 0 && CM_W(ptr).road_aqueduct != 0
                && CM_W(ptr).road_aqueduct < best_elastic_value) {
                best_elastic_value = CM_W(ptr).road_aqueduct;
                best_elastic_dirc = dir;
            }
        }
        dir++;
        if (dir > 3) dir = 0;
    }
}
"""
exp.add("inline-no-temp", _INLINE, note="no v temp; field accessed inline (uchar)")

# uchar v but force the loop counter to NOT be a hoistable plain xor:
exp.add("uchar-for", _BODY_UCHAR.replace(
    "    i = 0;\n    while (i++ < 4) {", "    for (i = 0; i++ < 4; ) {"),
    note="uchar v, for-loop init")

# uchar v + dir as a separate late assignment (raise pressure before loop):
exp.add("uchar-dir-late", _BODY_UCHAR.replace(
    "    int dir = dirc;\n", "    int dir;\n").replace(
    "    i = 0;\n", "    dir = dirc;\n    i = 0;\n"),
    note="uchar v, dir=dirc as stmt before i=0")

# --- session 2: the +1-savings layout flip (UNFAITHFUL but proves the
#     mechanism).  `v & 0xff` on the store adds one depth-1 v ref, which
#     flips the WHOLE register layout to PS (push ebp, mov edx,ecx,
#     dir=EDX, i=ECX, v=AL) -> 98 b (below the 107 int-v floor).  The 98 b
#     residue is the double-widen: PS shares one in-place `and eax,0xff`,
#     the explicit `& 0xff` forces a separate `movzx ebp,al` (cmp) +
#     `and` (store).  Keep as the witness that the layout is reachable;
#     do NOT commit (no-op mask, not faithful, not exact).
exp.add("store-mask-FLIP", _BODY_UCHAR.replace(
    "best_elastic_value = v;", "best_elastic_value = v & 0xff;"),
    note="v&0xff store (all branches) -> 98b, PS layout, unfaithful")
