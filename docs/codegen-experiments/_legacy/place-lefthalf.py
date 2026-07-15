"""Investigate why ``place_lefthalf_diamond`` won't compile to the
PS-matching codegen even though its sister ``place_diamond`` does.

Both functions have nearly identical bodies (24-bit LE int read from
a global byte buffer + bounds check + zoom-dispatched blitter call).

PS form (place_diamond, byte-exact in our build):
  push ebx,ecx,edx,esi
  mov edx, eax                  ; save style
  mov eax, [sprite_image_no]    ; eax = sprite_image_no
  ...
  mov eax, [fixt_data]          ; reuse eax for fixt_data
  mov ebx, [data_ptr]           ; reload data_ptr from memory
  ...
  mov bl, [ebx + eax + 5]       ; INDEXED [base + idx + offset]

PS form (place_lefthalf_diamond, target):
  push ebx,ecx,edx              ; only 3 callee-saves (no esi)
  mov eax, [sprite_image_no]    ; eax = sprite_image_no
  ...
  mov eax, [fixt_data]
  mov edx, [data_ptr]           ; reload
  mov bl, [edx + eax + 5]       ; INDEXED

Recomp form (what we keep getting):
  push ebx,ecx,edx
  mov edx, [sprite_image_no]    ; edx (not eax!) holds sprite_image_no
  ...
  add edx, [fixt_data]          ; FOLD instead of indexed
  mov bl, [edx + 5]             ; SIMPLE base+offset

The PS form keeps two registers separate (eax=fixt_data,
edx=data_ptr) and uses indexed addressing.  The recomp folds them
into a single base.  ~120 b cascade.

Hypothesis: with no parameter, Watcom is free to use edx as primary
work register; with a parameter it spills the param into edx and
forces eax-based work.  But adding ``int style`` param to our source
didn't change the codegen.  Something else gates the choice.

Trials:
  * baseline      — current source: ``void`` signature, full body
  * with_style    — ``int style`` parameter (matches place_diamond)
  * style_used    — style assigned to a local before use
  * dummy_eax     — declare ``int dummy = sprite_image_no;`` first
                    to evict garbage from eax
  * inline_ptr    — pre-cast fixt_data to ``unsigned char *p``
  * three_temps   — split byte loads via three named locals
"""
from c2.commands.cgex import Experiment


EXTERNS = {
    "place_i_large_diamond_lefthalf":
        "extern void place_i_large_diamond_lefthalf(int base, int style);",
    "place_i_medium_diamond_lefthalf":
        "extern void place_i_medium_diamond_lefthalf(int base, int style);",
    "place_i_small_diamond_lefthalf":
        "extern void place_i_small_diamond_lefthalf(int base, int style);",
}


exp = Experiment(
    name="place-lefthalf",
    ps_function="place_lefthalf_diamond",
    chk=False,
    externs=EXTERNS,
    prelude="""
extern int  sprite_image_no;
extern int  data_ptr;
extern int  fixt_data;
extern int  sprite_start;
extern int  sprite_error;
extern char zoom_level;
""",
    extra_defs="""
int  sprite_image_no;
int  data_ptr;
int  fixt_data;
int  sprite_start;
int  sprite_error;
char zoom_level;
""",
)


# ── trial baseline: `void` signature ─────────────────────────────────
exp.add(
    "baseline",
    """
void place_lefthalf_diamond(void)
{
    data_ptr = sprite_image_no * 16 + 8;
    sprite_start = ((unsigned char *)fixt_data)[data_ptr + 4]
                 + (((unsigned char *)fixt_data)[data_ptr + 5] << 8)
                 + (((unsigned char *)fixt_data)[data_ptr + 6] << 16);

    if (sprite_start > 0x4baf0) { sprite_error++; return; }
    if (sprite_start < 0)       { sprite_error++; return; }

    if (zoom_level == 0) { place_i_large_diamond_lefthalf(fixt_data, 0); return; }
    if (zoom_level == 1) { place_i_medium_diamond_lefthalf(fixt_data, 0); return; }
    place_i_small_diamond_lefthalf(fixt_data, 0);
}
""",
    note="void sig (current); recomp folds edx",
)


# ── trial with_style: `int style` (matches place_diamond) ─────────────
exp.add(
    "with_style",
    """
void place_lefthalf_diamond(int style)
{
    data_ptr = sprite_image_no * 16 + 8;
    sprite_start = ((unsigned char *)fixt_data)[data_ptr + 4]
                 + (((unsigned char *)fixt_data)[data_ptr + 5] << 8)
                 + (((unsigned char *)fixt_data)[data_ptr + 6] << 16);

    if (sprite_start > 0x4baf0) { sprite_error++; return; }
    if (sprite_start < 0)       { sprite_error++; return; }

    if (zoom_level == 0) { place_i_large_diamond_lefthalf(fixt_data, style); return; }
    if (zoom_level == 1) { place_i_medium_diamond_lefthalf(fixt_data, style); return; }
    place_i_small_diamond_lefthalf(fixt_data, style);
}
""",
    note="int style param (matches place_diamond)",
)


# ── trial dummy_eax: read fixt_data first, into eax ───────────────────
exp.add(
    "dummy_eax",
    """
void place_lefthalf_diamond(void)
{
    int p_base;
    p_base = fixt_data;
    data_ptr = sprite_image_no * 16 + 8;
    sprite_start = ((unsigned char *)p_base)[data_ptr + 4]
                 + (((unsigned char *)p_base)[data_ptr + 5] << 8)
                 + (((unsigned char *)p_base)[data_ptr + 6] << 16);

    if (sprite_start > 0x4baf0) { sprite_error++; return; }
    if (sprite_start < 0)       { sprite_error++; return; }

    if (zoom_level == 0) { place_i_large_diamond_lefthalf(p_base, 0); return; }
    if (zoom_level == 1) { place_i_medium_diamond_lefthalf(p_base, 0); return; }
    place_i_small_diamond_lefthalf(p_base, 0);
}
""",
    note="cache fixt_data in a local first",
)


# ── trial inline_ptr: explicit pointer cast in a local ───────────────
exp.add(
    "inline_ptr",
    """
void place_lefthalf_diamond(void)
{
    unsigned char *p;
    p = (unsigned char *)fixt_data;
    data_ptr = sprite_image_no * 16 + 8;
    sprite_start = p[data_ptr + 4]
                 + (p[data_ptr + 5] << 8)
                 + (p[data_ptr + 6] << 16);

    if (sprite_start > 0x4baf0) { sprite_error++; return; }
    if (sprite_start < 0)       { sprite_error++; return; }

    if (zoom_level == 0) { place_i_large_diamond_lefthalf(fixt_data, 0); return; }
    if (zoom_level == 1) { place_i_medium_diamond_lefthalf(fixt_data, 0); return; }
    place_i_small_diamond_lefthalf(fixt_data, 0);
}
""",
    note="explicit `unsigned char *p` local",
)


# ── trial three_temps: split byte loads into 3 named locals ──────────
exp.add(
    "three_temps",
    """
void place_lefthalf_diamond(void)
{
    int b4, b5, b6;
    data_ptr = sprite_image_no * 16 + 8;
    b4 = ((unsigned char *)fixt_data)[data_ptr + 4];
    b5 = ((unsigned char *)fixt_data)[data_ptr + 5];
    b6 = ((unsigned char *)fixt_data)[data_ptr + 6];
    sprite_start = b4 + (b5 << 8) + (b6 << 16);

    if (sprite_start > 0x4baf0) { sprite_error++; return; }
    if (sprite_start < 0)       { sprite_error++; return; }

    if (zoom_level == 0) { place_i_large_diamond_lefthalf(fixt_data, 0); return; }
    if (zoom_level == 1) { place_i_medium_diamond_lefthalf(fixt_data, 0); return; }
    place_i_small_diamond_lefthalf(fixt_data, 0);
}
""",
    note="three named locals for the bytes",
)
