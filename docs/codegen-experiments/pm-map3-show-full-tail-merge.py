"""Recover the backward PS jump as ComTail output, not a source goto.

The Windows /Od build shows that each terrain-virtual arm duplicates the
``sprite_x`` increment and continues the loop.  That makes its complete tail
identical to the earlier update-virtual arm, giving Watcom a natural backward
tail-merge target without any backward control flow in the C source.
"""

from c2.forge import Forge, TextEdit


forge = Forge("show_battlemap_base", file="pm_map3.c")
src = forge.text
start = forge.fs.body.start_byte
end = forge.fs.body.end_byte


def add_full_tail(name, style, number):
    old = f"""        if (((pm_shown_ptr) >= 0x0FFF0000)) {{
            sprite_image_no = ((pm_shown_ptr) - 0x0FFF0000);
            place_diamond({number});
        }} else {{"""
    new = f"""        if (((pm_shown_ptr) >= 0x0FFF0000)) {{
            sprite_image_no = ((pm_shown_ptr) - 0x0FFF0000);
            place_diamond({number});
            sprite_x += pm_diamond_width;
            continue;
        }} else {{"""
    pos = src.index(old, start, end)
    forge.candidate(name, TextEdit(pos, pos + len(old), new))


add_full_tail("top-full-tail", "top", 2)
add_full_tail("bottom-full-tail", "bottom", 1)

