"""build_wall_from_elastic — residual 32 b after the committed 256->32 fix.

COMMITTED FIX (2289ff3, 256 -> 32):
  * inline best_elastic_dirc in the 4-way switch (not `int dirc`): flips the
    global load off EAX's 5-byte A1 moffs32 onto PS's 6-byte 8b 0d/8b 1d,
    killing a 2-byte-per-load Rule-16 jmp cascade.  256 -> 49.
  * declare loop vars `y` before `x` (Rule 79): y->EDI, x->EBP per PS.  -> 32.
  First walk + prolog (push ebx..ebp; sub esp,0xc) now byte-exact.

RESIDUAL 32 b — ROOT CAUSE (loop-carried allocator state, NOT a source idiom):
  The whole residual cascades from ONE allocator decision in walk2's counter
  setup.  PS reloads the GLOBAL pm_over_cm_ptr into EAX for the counter byte
  read (`mov eax,[pm_over_cm_ptr]; xor ecx,ecx; mov cl,[eax+city_map+2]`),
  which forces counter->ECX.  We free EAX, so counter->EAX.  Everything else
  follows mechanically:
      counter->ECX (PS) => dirc->EBX (ECX taken)  vs  counter->EAX => dirc->ECX
      => tail reuses the warm ECX/EBX for elastic_start_dirc/const-1
         vs we reuse EDI/ESI (the dead y/ptr callee-saves)
  walk2 swaps are same-length (no cascade); the tail differs by 1 byte
  (eager store) which shifts our epilogue off the tail-merge point +0x261.

EAGER-STORE MECHANISM (learned here): PS stores elastic_start_dirc eagerly
  (`mov [g],ecx` before the cmp).  A `g = 0` wrap lets Watcom store-once
  (defer) -> 615 b.  A g-READING wrap (`g -= 4`, `g &= 3`) forces g+1 to be
  committed -> eager store -> size 616 (trial tail_subwrap: 32 -> 20!), but
  the final op is `lea [edi-4]` not PS's `xor edi`, and the regs are still
  edi/esi not ecx/ebx.  So the eager store is a CONSEQUENCE of the ecx/ebx
  tail allocation, which is a consequence of counter->ECX in walk2.  PS's
  authentic source is `g = 0` (the disasm shows xor edi,edi) WITH the eager
  store, i.e. PS got the eager store for free from its register allocation.

EXHAUSTED (do not re-try blindly):
  * cgex source idioms: family loop form is `while(count>0){count--;}` (the
    `while(x-->0)` form is formulae.c's other author — off-style, regresses);
    tail post-inc/pre-inc/+1/==4 all = 32 or worse; walk2 setup reorders
    (ptr-first, counter-last) regress to ~250 (they CSE pm_over_cm_ptr the
    wrong way); separate counter var regresses 253.
  * permute depth 1 AND depth 2 + climb: 0 improvements (all 43/120 variants
    byte-equal at 32, regressions, or build-fail).  cache_global regresses
    +400 (confirms inline); swap_assigns confirms x/y init order.

CONCLUSION: the residual is a deterministic-but-source-opaque register pick
  (which reg pm_over_cm_ptr reloads into entering walk2).  No source lever
  found that forces it to EAX without CSE-ing it the wrong way.  Committed
  at 32 b as a faithful non-exact donor; prolog is exact so build_wall is
  correctly anchored.  Future: needs an oracle trace of GiveBestReg at the
  walk2 counter conflict to see why EAX is/ isn't chosen.

    uv run c2 cgex run build_wall
    uv run c2 cgex run build_wall --trial baseline
"""

from c2.commands.cgex import Experiment

GLOBALS = """
unsigned char city_map[128000];
int pm_over_cm_ptr, over_x, over_y;
int best_elastic_value, best_elastic_dirc, elastic_start_dirc;
int illegal_build, particles_built, particles_cleared;
"""

PRELUDE = """
extern unsigned char city_map[];
extern int pm_over_cm_ptr, over_x, over_y;
extern int best_elastic_value, best_elastic_dirc, elastic_start_dirc;
extern int illegal_build, particles_built, particles_cleared;
"""

exp = Experiment(
    name="build_wall",
    ps_function="build_wall_from_elastic",
    chk=False,
    externs={
        "get_best_elastic_value":
            "extern void get_best_elastic_value(int x, int y, int ptr, int d);",
        "wall_ramifications":
            "extern int wall_ramifications(int x, int y);",
        "restore_city_from_undo_buffer":
            "extern void restore_city_from_undo_buffer(void);",
    },
    extra_defs=GLOBALS,
    prelude=PRELUDE,
)


def _body(walk1_step, walk2_step, tail):
    """Assemble the function from interchangeable pieces."""
    return f"""
void build_wall_from_elastic(void)
{{
    int counter, y, x, ptr;
    char outer_state;
    unsigned char saved_byte2;

    counter = (unsigned char)city_map[pm_over_cm_ptr + 2];
    if (city_map[pm_over_cm_ptr + 1] & 4)
        counter++;
    if (counter == 0) {{ illegal_build = 1; return; }}
    if (counter == 0xff) {{ illegal_build = 1; return; }}

    outer_state = 0;
    x = over_x;
    y = over_y;
    ptr = pm_over_cm_ptr;
    while (counter > 0) {{
        counter--;
        if ((city_map[ptr + 1] & 6) == 0) particles_built++;
        if ((unsigned char)city_map[ptr] < 0x1a) particles_cleared++;
        city_map[ptr + 3] |= 1;
        if (!(city_map[ptr + 1] & 4)) {{
            if (city_map[ptr + 1] & 0x20) city_map[ptr + 1] |= 4;
            else city_map[ptr + 1] |= 2;
        }}
        saved_byte2 = city_map[ptr + 2];
        get_best_elastic_value(x, y, ptr, elastic_start_dirc);
        if (saved_byte2 >= best_elastic_value) {{
{walk1_step}
        }} else if (saved_byte2 > 1) {{
            outer_state = 1;
            goto check_outer_state;
        }} else {{
            break;
        }}
    }}

    counter = (unsigned char)city_map[pm_over_cm_ptr + 2];
    if (city_map[pm_over_cm_ptr + 1] & 4)
        counter++;
    x = over_x;
    y = over_y;
    ptr = pm_over_cm_ptr;
    while (counter > 0) {{
        counter--;
        if (!wall_ramifications(x, y)) {{
            outer_state = 2;
            goto check_outer_state;
        }}
        city_map[ptr + 0x12] = 0;
        saved_byte2 = city_map[ptr + 2];
        get_best_elastic_value(x, y, ptr, elastic_start_dirc);
        if (saved_byte2 >= best_elastic_value) {{
{walk2_step}
        }} else {{
            if (saved_byte2 > 1) outer_state = 3;
            goto check_outer_state;
        }}
    }}

check_outer_state:
    if (outer_state != 0) {{
        illegal_build = 1;
        restore_city_from_undo_buffer();
{tail}
    }}
}}
"""


STEP_INLINE = """            if (best_elastic_dirc == 0) { ptr -= 0x640; y--; }
            else if (best_elastic_dirc == 1) { ptr += 0x14;  x += best_elastic_dirc; }
            else if (best_elastic_dirc == 2) { ptr += 0x640; y++; }
            else if (best_elastic_dirc == 3) { ptr -= 0x14;  x--; }"""

TAIL_POSTINC = """        elastic_start_dirc++;
        if (elastic_start_dirc > 3)
            elastic_start_dirc = 0;"""

exp.add("baseline", _body(STEP_INLINE, STEP_INLINE, TAIL_POSTINC),
        note="committed source: inline dirc + post-inc tail (32 b in-tree)")

# ── tail variants: chase PS's eager store (mov [g],ecx before cmp) ──
exp.add("tail_preinc", _body(STEP_INLINE, STEP_INLINE,
    """        if (++elastic_start_dirc > 3)
            elastic_start_dirc = 0;"""),
    note="pre-inc in condition")

exp.add("tail_plus1", _body(STEP_INLINE, STEP_INLINE,
    """        elastic_start_dirc = elastic_start_dirc + 1;
        if (elastic_start_dirc > 3)
            elastic_start_dirc = 0;"""),
    note="explicit +1 then test")

exp.add("tail_eq4", _body(STEP_INLINE, STEP_INLINE,
    """        elastic_start_dirc++;
        if (elastic_start_dirc == 4)
            elastic_start_dirc = 0;"""),
    note="post-inc, == 4 wrap")

exp.add("tail_ge", _body(STEP_INLINE, STEP_INLINE,
    """        elastic_start_dirc++;
        if (elastic_start_dirc >= 4)
            elastic_start_dirc = 0;"""),
    note="post-inc, >= 4")

# ── walk2 variants: PS counter->ECX, dirc->EBX ──
STEP_LOCAL = """            int dir2 = best_elastic_dirc;
            if (dir2 == 0) { ptr -= 0x640; y--; }
            else if (dir2 == 1) { ptr += 0x14;  x += dir2; }
            else if (dir2 == 2) { ptr += 0x640; y++; }
            else if (dir2 == 3) { ptr -= 0x14;  x--; }"""

exp.add("walk2_localdir", _body(STEP_INLINE, STEP_LOCAL, TAIL_POSTINC),
    note="walk2 uses local dirc cache (walk1 inline)")

# ── walk2 counter root: PS counter->ECX forces dirc->EBX ──
# Try forcing counter off EAX in walk2 by separate variable / decl order.
def _body2(decls, w2_pre, tail=TAIL_POSTINC):
    """Variant allowing custom decls + walk2 counter handling."""
    b = _body(STEP_INLINE, STEP_INLINE, tail)
    b = b.replace("    int counter, y, x, ptr;", decls)
    return b

# separate counter for walk2 (1995 often reused/separate names)
exp.add("w2_sep_counter",
    _body2("    int counter, y, x, ptr;\n    int n;", "")
      .replace("""    counter = (unsigned char)city_map[pm_over_cm_ptr + 2];
    if (city_map[pm_over_cm_ptr + 1] & 4)
        counter++;
    x = over_x;
    y = over_y;
    ptr = pm_over_cm_ptr;
    while (counter > 0) {
        counter--;
        if (!wall_ramifications(x, y)) {""",
    """    n = (unsigned char)city_map[pm_over_cm_ptr + 2];
    if (city_map[pm_over_cm_ptr + 1] & 4)
        n++;
    x = over_x;
    y = over_y;
    ptr = pm_over_cm_ptr;
    while (n > 0) {
        n--;
        if (!wall_ramifications(x, y)) {"""),
    note="walk2 uses separate counter var 'n'")

# ── tail: more eager-store attempts ──
exp.add("tail_subwrap", _body(STEP_INLINE, STEP_INLINE,
    """        elastic_start_dirc++;
        if (elastic_start_dirc > 3)
            elastic_start_dirc -= 4;"""),
    note="wrap via -= 4 (g only reaches 4)")

exp.add("tail_dowhile", _body(STEP_INLINE, STEP_INLINE,
    """        elastic_start_dirc++;
        do {
            if (elastic_start_dirc > 3) elastic_start_dirc = 0;
        } while (0);"""),
    note="wrap in do-while(0) block")

exp.add("tail_gt3_brace", _body(STEP_INLINE, STEP_INLINE,
    """        ++elastic_start_dirc;
        if (elastic_start_dirc > 3) {
            elastic_start_dirc = 0;
        }"""),
    note="pre-inc statement + braced if")

# ── walk2 counter decrement forms ──
def w2_counter(decr):
    b = _body(STEP_INLINE, STEP_INLINE, TAIL_POSTINC)
    # only the SECOND 'counter--;' (walk2). split on the wall_ramifications marker.
    head, _, rest = b.partition("    while (counter > 0) {\n        counter--;\n        if (!wall_ramifications")
    rest = decr + "        if (!wall_ramifications" + rest
    return head + "    while (counter > 0) {\n" + rest

exp.add("w2_predec", w2_counter("        --counter;\n"),
    note="walk2 prefix --counter")
exp.add("w2_explicit", w2_counter("        counter = counter - 1;\n"),
    note="walk2 explicit counter = counter - 1")
exp.add("w2_minuseq", w2_counter("        counter -= 1;\n"),
    note="walk2 counter -= 1")

# g-reading wrap variants (force eager store like tail_subwrap)
exp.add("tail_and3", _body(STEP_INLINE, STEP_INLINE,
    """        elastic_start_dirc++;
        if (elastic_start_dirc > 3)
            elastic_start_dirc &= 3;"""),
    note="wrap via &= 3")
exp.add("tail_mod4", _body(STEP_INLINE, STEP_INLINE,
    """        elastic_start_dirc++;
        elastic_start_dirc %= 4;"""),
    note="wrap via %= 4 unconditional")
exp.add("tail_minusconst", _body(STEP_INLINE, STEP_INLINE,
    """        elastic_start_dirc++;
        if (elastic_start_dirc > 3)
            elastic_start_dirc = elastic_start_dirc - 4;"""),
    note="wrap via g = g - 4")

# ── 1995 idiom: post-dec in the while condition ──
def w2_postdec(b):
    """Replace walk2 'while (counter>0){counter--;' with 'while(counter-->0){'."""
    head, sep, rest = b.partition("    while (counter > 0) {\n        counter--;\n        if (!wall_ramifications")
    return head + "    while (counter-- > 0) {\n        if (!wall_ramifications" + rest

exp.add("w2_while_postdec",
    w2_postdec(_body(STEP_INLINE, STEP_INLINE, TAIL_POSTINC)),
    note="walk2: while (counter-- > 0) 1995 idiom")

# both walks post-dec
def both_postdec(b):
    b = b.replace("    while (counter > 0) {\n        counter--;\n        if ((city_map[ptr + 1] & 6) == 0)",
                  "    while (counter-- > 0) {\n        if ((city_map[ptr + 1] & 6) == 0)")
    return w2_postdec(b)
exp.add("both_while_postdec",
    both_postdec(_body(STEP_INLINE, STEP_INLINE, TAIL_POSTINC)),
    note="both walks: while (counter-- > 0)")

# ── walk2 counter index register: PS keeps pm_over_cm_ptr in EAX (counter->ECX) ──
# v1: assign ptr first, read counter via the LOCAL ptr (city_map[ptr+2])
def w2_ptr_first(b):
    old = """    counter = (unsigned char)city_map[pm_over_cm_ptr + 2];
    if (city_map[pm_over_cm_ptr + 1] & 4)
        counter++;
    x = over_x;
    y = over_y;
    ptr = pm_over_cm_ptr;
    while (counter > 0) {
        counter--;
        if (!wall_ramifications"""
    new = """    ptr = pm_over_cm_ptr;
    counter = (unsigned char)city_map[ptr + 2];
    if (city_map[ptr + 1] & 4)
        counter++;
    x = over_x;
    y = over_y;
    while (counter > 0) {
        counter--;
        if (!wall_ramifications"""
    return b.replace(old, new)

exp.add("w2_ptr_first", w2_ptr_first(_body(STEP_INLINE, STEP_INLINE, TAIL_POSTINC)),
    note="walk2: ptr=pm_over_cm_ptr first, counter via city_map[ptr+2]")

# v2: read counter through the global but keep x/y/ptr order, counter via local after ptr
def w2_counter_after(b):
    old = """    counter = (unsigned char)city_map[pm_over_cm_ptr + 2];
    if (city_map[pm_over_cm_ptr + 1] & 4)
        counter++;
    x = over_x;
    y = over_y;
    ptr = pm_over_cm_ptr;
    while (counter > 0) {
        counter--;
        if (!wall_ramifications"""
    new = """    x = over_x;
    y = over_y;
    ptr = pm_over_cm_ptr;
    counter = (unsigned char)city_map[pm_over_cm_ptr + 2];
    if (city_map[pm_over_cm_ptr + 1] & 4)
        counter++;
    while (counter > 0) {
        counter--;
        if (!wall_ramifications"""
    return b.replace(old, new)

exp.add("w2_counter_last", w2_counter_after(_body(STEP_INLINE, STEP_INLINE, TAIL_POSTINC)),
    note="walk2: x/y/ptr first, then counter setup")
