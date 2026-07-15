#!/usr/bin/env python3
"""Convert an OS/2 IPF INF/HLP help file to Markdown.

Faithful decoder for the IBM Information Presentation Facility compiled
help format (magic "HS"), based on Marcus Groeber / Carl Hauser's
reverse-engineered spec (inf02b.doc) and the reference C decoder
(unipfc.c). Used to read the Watcom 10.0a docs shipped in the
toolchain container (cguide.inf, clib.inf, ...).

Usage:  python3 tools/inf2md.py <file.inf> [out.md]
"""
import struct, sys
from pathlib import Path


class INF:
    def __init__(self, data: bytes):
        self.d = data
        h = {}
        u = lambda fmt, off: struct.unpack_from("<" + fmt, data, off)[0]
        # header layout (inf02b.doc); only the text-bearing fields are used
        h["ntoc"]            = u("H", 0x08)
        h["tocstrtablestart"]= u("I", 0x0a)
        h["tocstrlen"]       = u("I", 0x0e)
        h["nslots"]          = u("H", 0x3e)
        h["slotsstart"]      = u("I", 0x40)
        h["dictlen"]         = u("I", 0x44)
        h["ndict"]           = u("H", 0x48)
        h["dictstart"]       = u("I", 0x4a)
        h["title"]           = data[0x6b:0x6b+48].split(b"\0")[0].decode("cp437", "replace")
        self.h = h
        self._dict()
        self._slots()
        self._toc()

    def _dict(self):
        # length-prefixed strings; length byte counts itself (incl). word =
        # the (len-1) bytes after it.
        self.dict = []
        p = self.h["dictstart"]; end = p + self.h["dictlen"]
        for _ in range(self.h["ndict"]):
            if p >= end:
                break
            ln = self.d[p]
            self.dict.append(self.d[p+1:p+ln])
            p += ln if ln else 1

    def _slots(self):
        s = self.h["slotsstart"]
        self.slots = list(struct.unpack_from("<%dI" % self.h["nslots"], self.d, s))

    def _toc(self):
        # toc entries are sequential at tocstrtablestart, each prefixed by a
        # total-length byte (unipfc.c get_toc)
        self.toc = []
        p = self.h["tocstrtablestart"]; end = p + self.h["tocstrlen"]
        for _ in range(self.h["ntoc"]):
            if p >= end:
                break
            ln = self.d[p]
            self.toc.append(self.d[p:p+ln])
            p += ln if ln else 1

    # ── article (slot) text decode ──────────────────────────────────────
    def _slot_tokens(self, pos):
        """Yield decode tokens for one slot's article."""
        stuff, localdictpos, nlocal, ntext = struct.unpack_from("<BIBH", self.d, pos)
        text = self.d[pos+8:pos+8+ntext]
        local = struct.unpack_from("<%dH" % nlocal, self.d, localdictpos) if nlocal else ()
        i = 0
        while i < len(text):
            b = text[i]
            if b < nlocal:
                gi = local[b]
                yield ("W", self.dict[gi] if gi < len(self.dict) else b"")
                i += 1
            elif b == 0xFA:
                yield ("PARA", None); i += 1
            elif b == 0xFB:
                i += 1
            elif b == 0xFC:
                yield ("SPACE_TOGGLE", None); i += 1
            elif b == 0xFD:
                yield ("BR", None); i += 1
            elif b == 0xFE:
                yield ("SP", None); i += 1
            elif b == 0xFF:
                esclen = text[i+1] if i+1 < len(text) else 1
                code = text[i+2] if i+2 < len(text) else 0
                arg = text[i+3] if i+3 < len(text) else 0
                yield ("ESC", (code, arg, text[i+3:i+1+esclen]))
                i += 1 + esclen
            else:
                i += 1

    def article(self, toc_entry):
        """Return (level, hidden, title, list-of-slot-token-iterators)."""
        p = 0
        ln = toc_entry[p]; p += 1
        flags = toc_entry[p]; p += 1
        ntocslots = toc_entry[p]; p += 1
        level = flags & 0x0F
        hidden = bool(flags & 0x40)
        if flags & 0x20:                       # extended window descriptor
            w1, w2 = toc_entry[p], toc_entry[p+1]; p += 2
            if w1 & 0x8: p += 2
            if w1 & 0x1: p += 5
            if w1 & 0x2: p += 5
            if w2 & 0x4: p += 2
        slot_ids = struct.unpack_from("<%dH" % ntocslots, toc_entry, p)
        tptr = p + ntocslots*2
        title = toc_entry[tptr:ln].decode("cp437", "replace").rstrip()
        return level, hidden, title, slot_ids


# ── markdown rendering ──────────────────────────────────────────────────
_STYLE = {1: "*", 2: "**", 3: "***", 4: "*", 5: "_", 6: "*_", 0: ""}


def render(inf: INF) -> str:
    out = ["# " + (inf.h["title"] or "(untitled)"), ""]
    for entry in inf.toc:
        level, hidden, title, slot_ids = inf.article(entry)
        depth = min(level + 1, 6)
        htext = title.strip()
        out.append("")
        out.append("#" * depth + " " + (htext or "(section)") + (" *(hidden)*" if hidden else ""))
        out.append("")
        out.append(_render_body(inf, slot_ids))
    md = "\n".join(out)
    # collapse >2 blank lines
    while "\n\n\n\n" in md:
        md = md.replace("\n\n\n\n", "\n\n\n")
    return md


def _render_body(inf: INF, slot_ids) -> str:
    paras = []          # finished blocks
    cur = []            # current line's words
    lines = []          # current paragraph's lines
    spacing = True
    in_ex = False
    ex_lines = []

    def flush_line():
        nonlocal cur
        if cur:
            lines.append("".join(cur)); cur = []

    def flush_para():
        nonlocal lines
        flush_line()
        if lines:
            paras.append("\n".join(lines)); lines = []

    def flush_ex():
        nonlocal ex_lines
        flush_line_ex()
        if ex_lines:
            body = "\n".join(ex_lines).rstrip("\n")
            paras.append("```\n" + body + "\n```")
            ex_lines = []

    ex_cur = []
    def flush_line_ex():
        nonlocal ex_cur
        ex_lines.append("".join(ex_cur)); ex_cur = []

    for sid in slot_ids:
        if sid >= len(inf.slots):
            continue
        for tok, val in inf._slot_tokens(inf.slots[sid]):
            if tok == "W":
                w = val.decode("cp437", "replace")
                if in_ex:
                    ex_cur.append(w);
                    if spacing: ex_cur.append(" ")
                else:
                    cur.append(w)
                    if spacing: cur.append(" ")
            elif tok == "SP":
                (ex_cur if in_ex else cur).append(" ")
            elif tok == "SPACE_TOGGLE":
                spacing = not spacing
            elif tok == "BR":
                if in_ex: flush_line_ex()
                else: flush_line()
            elif tok == "PARA":
                if in_ex: flush_line_ex()
                else: flush_para()
                spacing = True
            elif tok == "ESC":
                code, arg, _rest = val
                if code == 0x0B:            # begin monospace example
                    flush_para(); in_ex = True; spacing = False
                elif code == 0x0C:          # end example
                    flush_ex(); in_ex = False; spacing = True
                elif code == 0x1A:          # begin :lines.
                    flush_para(); spacing = False
                elif code == 0x1B:          # end :lines.
                    flush_para(); spacing = True
                # style/colour/margin escapes (0x02-0x04,0x0d,0x11-0x14,...)
                # carry no plain-text payload -> ignored for md fidelity
    if in_ex:
        flush_ex()
    else:
        flush_para()
    return "\n\n".join(paras).strip() + "\n"


def main():
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(1)
    src = Path(sys.argv[1])
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else src.with_suffix(".md")
    inf = INF(src.read_bytes())
    md = render(inf)
    out.write_text(md)
    print(f"{src.name}: {len(inf.toc)} sections, {inf.h['ndict']} dict words "
          f"-> {out} ({len(md)} bytes)")


if __name__ == "__main__":
    main()
