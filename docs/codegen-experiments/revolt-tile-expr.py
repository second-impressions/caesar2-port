"""get_region_revolt_points -- tile-expression temp structure.

PS (L362-L365):
    movzx edi, [x]; mov edx, edi          ; x -> EDI home + EDX addr-copy
    movzx esi, [y]; mov ecx, esi          ; y -> ESI home + ECX copy (dies in xor)
    mov eax, esi; shl 4; sub; shl 5       ; eax = 480y
    mov dl, [eax + edx*8 + region_map]    ; tile
    xor ecx, esi; mov cl, dl              ; widen tile via ecx==esi zero

RC form A (x first): x -> ESI + ECX addr-copy, y -> EDI, NO y copy.
RC form B (y first): seats all match PS ("register layout matches PS")
but the x load happens after the mul (PS loads x first).

Search: alternate spellings of the tile expression (byte-offset form,
RM_CELL, bytemasks, parenthesizations) plus statement splits that give
the y-conversion its own temp.
"""

from c2.forge import Forge

TILE_LN = 497

VARIANTS = [
    # form B: y*W first, x second (seats match, order wrong) -- anchor
    "    tile = (((struct region_cell *)region_map + (hut_list[n].y) * REGION_W) + (hut_list[n].x))->base_kind;",
    # byte-offset y, cell-scaled x
    "    tile = (*((struct region_cell *)((unsigned char *)region_map + hut_list[n].y * (REGION_W * 8)) + hut_list[n].x)).base_kind;",
    "    tile = (*((struct region_cell *)((unsigned char *)region_map + hut_list[n].y * REGION_W * 8) + hut_list[n].x)).base_kind;",
    # x cell-add on the cast base, then byte-offset y
    "    tile = (*(struct region_cell *)((unsigned char *)((struct region_cell *)region_map + hut_list[n].x) + hut_list[n].y * REGION_W * 8)).base_kind;",
    # RM_CELL byte-offset whole-index forms
    "    tile = RM_CELL((hut_list[n].x + hut_list[n].y * REGION_W) * 8).base_kind;",
    "    tile = RM_CELL(hut_list[n].x * 8 + hut_list[n].y * REGION_W * 8).base_kind;",
    # array-index forms
    "    tile = region_map[hut_list[n].x + hut_list[n].y * REGION_W].base_kind;",
    "    tile = (&region_map[hut_list[n].x] + hut_list[n].y * REGION_W)->base_kind;",
    "    tile = (&region_map[hut_list[n].y * REGION_W] + hut_list[n].x)->base_kind;",
    # bytemask / cast variants on form A
    "    tile = (((struct region_cell *)region_map + (hut_list[n].x & 0xff)) + (hut_list[n].y) * REGION_W)->base_kind;",
    "    tile = (((struct region_cell *)region_map + (hut_list[n].x)) + (hut_list[n].y & 0xff) * REGION_W)->base_kind;",
    # int-cast variants (extra convert temp?)
    "    tile = (((struct region_cell *)region_map + (hut_list[n].x)) + (int)(hut_list[n].y) * REGION_W)->base_kind;",
    "    tile = (((struct region_cell *)region_map + (int)(hut_list[n].x)) + (hut_list[n].y) * REGION_W)->base_kind;",
]


forge = Forge("get_region_revolt_points", file="bbarian.c")

for _i, _v in enumerate(VARIANTS):
    forge.replace_line(TILE_LN, _v)

# sub-expression extraction into locals (auto decl placement)
forge.split_expr(at_line=TILE_LN, expr_text="(hut_list[n].y) * REGION_W",
                 into_var="row", type_="int")
forge.split_expr(at_line=TILE_LN, expr_text="hut_list[n].y",
                 into_var="y", type_="int")
forge.split_expr(at_line=TILE_LN, expr_text="hut_list[n].x",
                 into_var="x", type_="int")
