"""Search honest equivalent RMW hosts for the final anonymous lookup seat.

2026-07-14 result: from the 8-byte/seat1 post-guard baseline, Forge found
``dirty-and-self-1`` as the unique improving single: the middle update path's
``dirty = dirty & 0xf0`` form produced byte-exact code with shape 0.  The
28-candidate grid stopped at the first exact plan.  Landed in ``9be405fb``.
"""

import re

from c2.forge import Forge, TextEdit


forge = Forge("mid3_line_with_sides_base", file="pm_map3.c")
src = forge.text
start = forge.fs.body.start_byte
end = forge.fs.body.end_byte
body = src[start:end]


def candidates(pattern, replacement, stem):
    for number, match in enumerate(re.finditer(pattern, body)):
        old = match.group(0)
        new = replacement(match)
        if old != new:
            pos = start + match.start()
            forge.candidate(
                f"{stem}-{number}", TextEdit(pos, pos + len(old), new)
            )


# Watcom distinguishes compound and explicit self-read trees even though both
# are faithful to the field/global update witnessed by the other builds.
candidates(
    r"(?P<lhs>\(\*\(struct battle_cell \*\).*?\)\.dirty) &= (?P<rhs>0xf0);",
    lambda m: f"{m.group('lhs')} = {m.group('lhs')} & {m.group('rhs')};",
    "dirty-and-self",
)
candidates(
    r"(?P<lhs>\(\*\(struct battle_cell \*\).*?\)\.dirty) \|= (?P<rhs>1);",
    lambda m: f"{m.group('lhs')} = {m.group('lhs')} | {m.group('rhs')};",
    "dirty-or-self",
)
candidates(
    r"(?P<lhs>tile) &= (?P<rhs>0xc);",
    lambda m: f"{m.group('lhs')} = {m.group('lhs')} & {m.group('rhs')};",
    "tile-and-self",
)
candidates(
    r"(?P<lhs>sprite_image_no) \+= (?P<rhs>0x10);",
    lambda m: f"{m.group('lhs')} = {m.group('lhs')} + {m.group('rhs')};",
    "image-add-self",
)
candidates(
    r"(?P<lhs>sprite_x) \+= (?P<rhs>pm_diamond_(?:half_)?width);",
    lambda m: f"{m.group('lhs')} = {m.group('lhs')} + {m.group('rhs')};",
    "sprite-x-add-self",
)
candidates(
    r"(?P<lhs>sprite_y|pm_y_clip)  ?\+= (?P<rhs>pm_diamond_half_height);",
    lambda m: f"{m.group('lhs')} = {m.group('lhs')} + {m.group('rhs')};",
    "tail-add-self",
)

# Prefix/postfix are value-equivalent where the increment result is discarded.
candidates(
    r"(?P<lhs>pm_shown_y|i)\+\+;",
    lambda m: f"++{m.group('lhs')};",
    "prefix-inc",
)

# Equivalent row/index tree spellings for the three map loads.
candidates(
    r"pseudo_map\[pm_shown_y\]\[pm_shown_x\+\+\]",
    lambda m: "*(pseudo_map[pm_shown_y] + pm_shown_x++)",
    "pointer-index",
)
candidates(
    r"pseudo_map\[pm_shown_y\]\[pm_shown_x\+\+\]",
    lambda m: "*(*(pseudo_map + pm_shown_y) + pm_shown_x++)",
    "double-pointer-index",
)

# run: c2 forge exp pm-map3-with-sides-rmw-grid --depth 2 --jobs 14
