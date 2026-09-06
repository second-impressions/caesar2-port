#!/usr/bin/env python3
"""Caesar II text as gettext: extract shipped C2.ENG/HELP.ENG into .po files,
validate them, and compile them back into the engine's own formats.

The port compiles every language's .po into the binary and rebuilds the
recovered `Textfile` (C2.ENG) and `Helpfile` (HELP.ENG) layouts in memory at
startup (src/platform/common/c2_port_text.c). This tool is the developer side
of that arrangement: it is never part of the build.

Keys (msgctxt):
  0x2f/3          C2.ENG string group 0x2f, string 3 -- the engine's own
                  (group, index) pair, as spelled in the recovered source.
  help/1234/0     HELP.ENG page 1234, string 0 (the title); /1 is the body.

A help page whose text is shared with an earlier page carries the reference
msgid "@<page>" instead of the text; a translation may keep the reference or
replace it with text of its own (the German help uses spare pages for
overflowing chapters).

Help bodies use "\\n" for the engine's `$` line break. `#12text#` is a link
to page 12 and must be kept intact.

Text is UTF-8 in the .po files; the runtime transcodes to the bitmap font's
CP437 code points.
"""
from __future__ import annotations

import argparse
import re
import struct
import sys
from dataclasses import dataclass, field
from pathlib import Path

TEXT_GROUPS = 147
TEXT_BUFFER_CAPACITY = 40000
HELP_PAGES = 2000
HELP_RECORD = 0x3A
HELP_PAGE_TEXT_CAPACITY = 0x7D0
# Late (1996) Textfile alias layout: group -> group whose payload it shares.
TEXT_ALIASES = {117: 116, 118: 116, 120: 119}

ROOT = Path(__file__).resolve().parents[1]


# --------------------------------------------------------------------------
# Textfile (C2.ENG)
# --------------------------------------------------------------------------

def textfile_offsets(data: bytes) -> list[int]:
    if data[:8] != b"Textfile":
        raise ValueError("not a Textfile")
    first = struct.unpack_from("<I", data, 12)[0]
    count = (first - 8) // 4
    return [struct.unpack_from("<I", data, 8 + i * 4)[0] for i in range(count)]


def read_textfile(data: bytes) -> dict[int, list[bytes]]:
    """Group index -> list of NUL-delimited strings (raw CP437 bytes)."""
    offsets = textfile_offsets(data)
    count = len(offsets)
    groups: dict[int, list[bytes]] = {}
    for g in range(1, count):
        start = offsets[g]
        later = [o for o in offsets if o > start]
        end = min(later) if later else len(data)
        payload = data[start:end]
        if not payload.endswith(b"\0"):
            raise ValueError(f"group {g:#x} payload does not end in NUL")
        groups[g] = payload[:-1].split(b"\0")
    return groups


def write_textfile(groups: dict[int, list[bytes]]) -> bytes:
    """Rebuild the late Textfile layout from group -> strings."""
    table_end = 8 + TEXT_GROUPS * 4
    payload = bytearray()
    offsets = [0] * TEXT_GROUPS
    for g in range(1, TEXT_GROUPS):
        if g in TEXT_ALIASES:
            offsets[g] = offsets[TEXT_ALIASES[g]]
            continue
        offsets[g] = table_end + len(payload)
        payload += b"\0".join(groups.get(g, [b""])) + b"\0"
    out = bytearray(b"Textfile")
    for o in offsets:
        out += struct.pack("<I", o)
    out += payload
    return bytes(out)


# --------------------------------------------------------------------------
# Helpfile (HELP.ENG)
# --------------------------------------------------------------------------

@dataclass
class HelpRecord:
    left_sprite: int = 0
    right_sprite: int = 0
    width: int = 0
    left: bytes = b"null.pl8"
    right: bytes = b"null.pl8"
    voc: bytes = b"null.voc"


@dataclass
class HelpFile:
    records: list[HelpRecord]
    # page -> strings, or page -> int (alias of that earlier page)
    pages: dict[int, list[bytes] | int] = field(default_factory=dict)


def _cstr(raw: bytes) -> bytes:
    return raw.split(b"\0", 1)[0]


def read_helpfile(data: bytes) -> HelpFile:
    if data[:8] != b"Helpfile":
        raise ValueError("not a Helpfile")
    records = []
    text_offsets = []
    for i in range(HELP_PAGES):
        o = 8 + i * HELP_RECORD
        to, ls, rs, w = struct.unpack_from("<Ihhh", data, o)
        records.append(HelpRecord(ls, rs, w, _cstr(data[o + 10:o + 26]),
                                  _cstr(data[o + 26:o + 42]), _cstr(data[o + 42:o + 58])))
        text_offsets.append(to)
    unique = sorted(set(o for o in text_offsets if o))
    first_page: dict[int, int] = {}
    for page, o in enumerate(text_offsets):
        if o and o not in first_page:
            first_page[o] = page
    pages: dict[int, list[bytes] | int] = {}
    for i, o in enumerate(unique):
        end = unique[i + 1] if i + 1 < len(unique) else len(data)
        segment = data[o:end]
        if not segment.endswith(b"\0"):
            raise ValueError(f"help text at {o} does not end in NUL")
        parts = segment[:-1].split(b"\0")
        # A few entries carry an unreferenced trailing " " string.
        while len(parts) > 1 and parts[-1] in (b" ", b""):
            parts.pop()
        pages[first_page[o]] = parts
    for page, o in enumerate(text_offsets):
        if o and first_page[o] != page:
            pages[page] = first_page[o]
    return HelpFile(records, pages)


def resolve_help_page(hf: HelpFile, page: int) -> list[bytes] | None:
    seen = set()
    while True:
        entry = hf.pages.get(page)
        if entry is None:
            return None
        if isinstance(entry, int):
            if entry in seen:
                raise ValueError(f"help alias cycle at page {page}")
            seen.add(entry)
            page = entry
            continue
        return entry


def write_helpfile(hf: HelpFile) -> bytes:
    """Rebuild a Helpfile the way the C runtime does: every page with its
    own text gets one copy, in page order; references share the target's."""
    text = bytearray()
    table_end = 8 + HELP_PAGES * HELP_RECORD
    offsets: dict[int, int] = {}
    for page in range(1, HELP_PAGES):
        entry = hf.pages.get(page)
        if isinstance(entry, list):
            offsets[page] = table_end + len(text)
            text += b"\0".join(entry) + b"\0"
    out = bytearray(b"Helpfile")
    for page in range(HELP_PAGES):
        rec = hf.records[page] if page < len(hf.records) else HelpRecord()
        target = page
        seen = set()
        while isinstance(hf.pages.get(target), int) and target not in seen:
            seen.add(target)
            target = hf.pages[target]
        offset = offsets.get(target, 0) if page else 0
        out += struct.pack("<Ihhh", offset, rec.left_sprite, rec.right_sprite, rec.width)
        out += rec.left.ljust(16, b"\0")[:16]
        out += rec.right.ljust(16, b"\0")[:16]
        out += rec.voc.ljust(16, b"\0")[:16]
    return bytes(out + text)


# --------------------------------------------------------------------------
# gettext .po (the subset we use), stdlib only
# --------------------------------------------------------------------------

@dataclass
class PoEntry:
    msgctxt: str
    msgid: str
    msgstr: str = ""
    comments: list[str] = field(default_factory=list)     # "#. " extracted
    tcomments: list[str] = field(default_factory=list)    # "# " translator
    references: list[str] = field(default_factory=list)   # "#: "
    flags: list[str] = field(default_factory=list)        # "#, "

    @property
    def fuzzy(self) -> bool:
        return "fuzzy" in self.flags


@dataclass
class PoFile:
    header: dict[str, str] = field(default_factory=dict)
    header_comments: list[str] = field(default_factory=list)
    entries: list[PoEntry] = field(default_factory=list)

    def by_key(self) -> dict[str, PoEntry]:
        return {e.msgctxt: e for e in self.entries}


_ESCAPES = {"\n": "\\n", "\t": "\\t", "\\": "\\\\", '"': '\\"', "\r": "\\r"}
_UNESCAPES = {"n": "\n", "t": "\t", "\\": "\\", '"': '"', "r": "\r"}


def po_quote(s: str) -> str:
    return '"' + "".join(_ESCAPES.get(c, c) for c in s) + '"'


def po_unquote(s: str) -> str:
    s = s.strip()
    if len(s) < 2 or s[0] != '"' or s[-1] != '"':
        raise ValueError(f"bad po string: {s!r}")
    out = []
    i = 1
    while i < len(s) - 1:
        c = s[i]
        if c == "\\":
            i += 1
            e = s[i]
            if e not in _UNESCAPES:
                raise ValueError(f"unsupported escape \\{e} in {s!r}")
            out.append(_UNESCAPES[e])
        else:
            out.append(c)
        i += 1
    return "".join(out)


def po_write_string(keyword: str, value: str, width: int = 76) -> str:
    """msgid/msgstr in gettext's multi-line convention."""
    if "\n" not in value and len(po_quote(value)) + len(keyword) + 1 <= width:
        return f"{keyword} {po_quote(value)}\n"
    lines = [f'{keyword} ""\n']
    for piece in value.splitlines(keepends=True):
        # wrap at spaces like msgcat does
        while len(po_quote(piece)) > width:
            cut = piece.rfind(" ", 0, width - 4)
            if cut <= 0:
                break
            lines.append(po_quote(piece[:cut + 1]) + "\n")
            piece = piece[cut + 1:]
        lines.append(po_quote(piece) + "\n")
    return "".join(lines)


def po_dump(po: PoFile) -> str:
    out = []
    for c in po.header_comments:
        out.append(f"# {c}\n" if c else "#\n")
    out.append('msgid ""\nmsgstr ""\n')
    for k, v in po.header.items():
        out.append(po_quote(f"{k}: {v}\n") + "\n")
    for e in po.entries:
        out.append("\n")
        for c in e.tcomments:
            out.append(f"# {c}\n")
        for c in e.comments:
            out.append(f"#. {c}\n")
        if e.references:
            out.append("#: " + " ".join(e.references) + "\n")
        if e.flags:
            out.append("#, " + ", ".join(e.flags) + "\n")
        out.append(f"msgctxt {po_quote(e.msgctxt)}\n")
        out.append(po_write_string("msgid", e.msgid))
        out.append(po_write_string("msgstr", e.msgstr))
    return "".join(out)


def po_parse(text: str) -> PoFile:
    po = PoFile()
    cur: dict[str, list[str]] = {}
    field_name = None
    pending = PoEntry("", "")
    first = True

    def flush():
        nonlocal pending, cur, first, field_name
        if not cur:
            return
        msgid = "".join(cur.get("msgid", []))
        msgstr = "".join(cur.get("msgstr", []))
        ctxt = "".join(cur.get("msgctxt", [])) if "msgctxt" in cur else None
        if first and ctxt is None and msgid == "":
            for line in msgstr.split("\n"):
                if ":" in line:
                    k, v = line.split(":", 1)
                    po.header[k.strip()] = v.strip()
            po.header_comments = pending.tcomments
        else:
            pending.msgctxt = ctxt or ""
            pending.msgid = msgid
            pending.msgstr = msgstr
            po.entries.append(pending)
        first = False
        pending = PoEntry("", "")
        cur = {}
        field_name = None

    for raw in text.splitlines():
        line = raw.rstrip("\n")
        if not line.strip():
            flush()
            continue
        if line.startswith("#"):
            if cur:
                flush()
            if line.startswith("#."):
                pending.comments.append(line[2:].strip())
            elif line.startswith("#:"):
                pending.references.extend(line[2:].split())
            elif line.startswith("#,"):
                pending.flags.extend(f.strip() for f in line[2:].split(","))
            elif line.startswith("#|"):
                pass  # previous msgid, ignore
            else:
                pending.tcomments.append(line[1:].strip())
            continue
        if line.startswith('"'):
            if field_name is None:
                raise ValueError(f"stray string: {line!r}")
            cur[field_name].append(po_unquote(line))
            continue
        m = re.match(r"(msgctxt|msgid|msgstr)\s+(\".*\")$", line)
        if not m:
            raise ValueError(f"unparsed po line: {line!r}")
        field_name = m.group(1)
        cur[field_name] = [po_unquote(m.group(2))]
    flush()
    return po


# --------------------------------------------------------------------------
# Encoding: the bitmap font is CP437-indexed
# --------------------------------------------------------------------------

def decode(raw: bytes) -> str:
    return raw.decode("cp437")


def encode(text: str) -> bytes:
    return text.encode("cp437")


LETTER_TABLE = [0, 63, 64, 0, 0, 65, 0, 74, 67, 68, 66, 70, 78, 69, 79, 77, 62, 53, 54, 55, 56,
                57, 58, 59, 60, 61, 72, 73, 0, 71, 0, 75, 0, 27, 28, 29, 30, 31, 32, 33, 34, 35,
                36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 0, 99, 0, 0,
                0, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21,
                22, 23, 24, 25, 26, 0, 0, 0, 0, 0, 103, 99, 88, 86, 83, 85, 1, 103, 90, 87, 89,
                91, 94, 93, 27, 27, 31, 105, 105, 98, 95, 97, 102, 101, 25, 41, 47, 0, 0, 0, 0,
                0, 84, 92, 96, 100, 104, 104, 1, 15] + [0] * 57 + [106] + [0] * 30


def glyph_missing(text: str) -> set[str]:
    """Characters the game font cannot draw (rendered as a blank)."""
    bad = set()
    for ch in text:
        if ch in " \n":
            continue
        try:
            code = ord(ch.encode("cp437"))
        except UnicodeEncodeError:
            bad.add(ch)
            continue
        if code < 32 or LETTER_TABLE[code - 32] == 0:
            bad.add(ch)
    return bad


# --------------------------------------------------------------------------
# Model <-> po
# --------------------------------------------------------------------------

HELP_BREAK = "$"


def help_to_po_text(raw: bytes) -> str:
    return decode(raw).replace(HELP_BREAK, "\n")


def help_from_po_text(text: str) -> bytes:
    return encode(text.replace("\n", HELP_BREAK))


def text_key(group: int, index: int) -> str:
    return f"{group:#x}/{index}"


def help_key(page: int, slot: int) -> str:
    return f"help/{page}/{slot}"


KEY_TEXT = re.compile(r"^0x([0-9a-f]+)/(\d+)$")
KEY_HELP = re.compile(r"^help/(\d+)/(\d+)$")


def source_references(src_root: Path) -> dict[tuple[int, int], list[str]]:
    """(group, index) -> 'file:line' for literal font_list-style calls."""
    refs: dict[tuple[int, int], list[str]] = {}
    call = re.compile(r"\b(font_list|font_format_split|get_text_pointer|font_centre|"
                      r"get_list_string)\(\s*(0x[0-9a-fA-F]+|\d+)\s*,\s*(0x[0-9a-fA-F]+|\d+)\s*[,)]")
    msg = re.compile(r"\bput_message\(\s*(0x[0-9a-fA-F]+|\d+)\s*,")
    for path in sorted(src_root.glob("*.c")):
        for lineno, line in enumerate(path.read_text(errors="replace").splitlines(), 1):
            for m in call.finditer(line):
                key = (int(m.group(2), 0), int(m.group(3), 0))
                refs.setdefault(key, []).append(f"src/{path.name}:{lineno}")
            for m in msg.finditer(line):
                g = int(m.group(1), 0)
                for i in (0, 1):
                    refs.setdefault((g, i), []).append(f"src/{path.name}:{lineno}")
    return refs


def build_entries(groups: dict[int, list[bytes]], hf: HelpFile,
                  english: PoFile | None, refs: dict, is_pot: bool) -> list[PoEntry]:
    """Entries for one language. With `english`, msgid comes from the pot and
    the language text goes to msgstr; the pot itself has msgstr empty."""
    en = english.by_key() if english else {}
    entries: list[PoEntry] = []
    for g in range(1, TEXT_GROUPS):
        if g in TEXT_ALIASES:
            continue
        strings = groups.get(g, [])
        for i, raw in enumerate(strings):
            key = text_key(g, i)
            text = decode(raw)
            if is_pot:
                e = PoEntry(key, text)
                e.references = refs.get((g, i), [])
            else:
                src = en.get(key)
                if src is None:
                    continue  # not in the canonical layout; reported by extract
                e = PoEntry(key, src.msgid, text)
            entries.append(e)
    for page in range(1, HELP_PAGES):
        entry = hf.pages.get(page)
        if entry is None:
            continue
        if isinstance(entry, int):
            target = entry
            count = len(resolve_help_page(hf, page) or [])
            for slot in range(count):
                key = help_key(page, slot)
                if is_pot:
                    entries.append(PoEntry(key, f"@{target}"))
                elif key in en:
                    entries.append(PoEntry(key, en[key].msgid, f"@{target}"))
            continue
        for slot, raw in enumerate(entry):
            key = help_key(page, slot)
            text = help_to_po_text(raw)
            if is_pot:
                e = PoEntry(key, text)
                if slot == 0:
                    e.comments = [f"help page {page}: title" ]
                entries.append(e)
            elif key in en:
                entries.append(PoEntry(key, en[key].msgid, text))
    return entries


def po_to_model(po: PoFile, english: PoFile | None = None
                ) -> tuple[dict[int, list[bytes]], dict[int, list[bytes] | int], list[str]]:
    """Resolve a po (msgstr, else msgid) into engine strings. Returns the
    text groups, the help pages and a list of problems."""
    problems: list[str] = []
    groups: dict[int, list[tuple[int, bytes]]] = {}
    help_pages: dict[int, dict[int, str]] = {}
    for e in po.entries:
        value = e.msgstr if (e.msgstr and not e.fuzzy) else e.msgid
        m = KEY_TEXT.match(e.msgctxt)
        if m:
            g, i = int(m.group(1), 16), int(m.group(2))
            try:
                groups.setdefault(g, []).append((i, encode(value)))
            except UnicodeEncodeError as err:
                problems.append(f"{e.msgctxt}: not encodable: {err}")
            continue
        m = KEY_HELP.match(e.msgctxt)
        if m:
            help_pages.setdefault(int(m.group(1)), {})[int(m.group(2))] = value
            continue
        problems.append(f"unknown key {e.msgctxt!r}")
    text_groups: dict[int, list[bytes]] = {}
    for g, items in groups.items():
        items.sort()
        if [i for i, _ in items] != list(range(len(items))):
            problems.append(f"group {g:#x}: string indices are not contiguous")
        text_groups[g] = [s for _, s in items]
    pages: dict[int, list[bytes] | int] = {}
    for page, slots in help_pages.items():
        keys = sorted(slots)
        if keys != list(range(len(keys))):
            problems.append(f"help page {page}: slots are not contiguous")
        values = [slots[k] for k in keys]
        if all(v.startswith("@") for v in values) and len({*values}) == 1:
            try:
                pages[page] = int(values[0][1:])
            except ValueError:
                problems.append(f"help page {page}: bad reference {values[0]!r}")
            continue
        strings = []
        for v in values:
            if v.startswith("@"):
                problems.append(f"help page {page}: mixed reference and text")
                v = ""
            try:
                strings.append(help_from_po_text(v))
            except UnicodeEncodeError as err:
                problems.append(f"help page {page}: not encodable: {err}")
                strings.append(b"")
        pages[page] = strings
    return text_groups, pages, problems


def check_po(po: PoFile, pot: PoFile, records: list[HelpRecord] | None = None
             ) -> tuple[list[str], list[str]]:
    """(errors, warnings). Errors break the build; warnings are things the
    shipped files themselves do (undrawable characters, relinked pages)."""
    problems: list[str] = []
    warnings: list[str] = []
    pot_keys = pot.by_key()
    seen = set()
    for e in po.entries:
        if e.msgctxt in seen:
            problems.append(f"duplicate key {e.msgctxt}")
        seen.add(e.msgctxt)
        if e.msgctxt not in pot_keys:
            problems.append(f"{e.msgctxt}: not in the template")
        elif pot_keys[e.msgctxt].msgid != e.msgid:
            problems.append(f"{e.msgctxt}: msgid differs from the template")
        value = e.msgstr or e.msgid
        if value.startswith("@"):
            value = ""
        # link tags are markup, not drawn; the "@@" placeholders draw blank
        missing = glyph_missing(re.sub(r"#\d*", "", value).replace("@@", ""))
        if missing:
            warnings.append(f"{e.msgctxt}: no glyph for {''.join(sorted(missing))!r}")
        if KEY_HELP.match(e.msgctxt):
            for tag in re.findall(r"#(\d+)", e.msgid):
                if e.msgstr and f"#{tag}" not in e.msgstr:
                    warnings.append(f"{e.msgctxt}: link #{tag} missing from translation")
    groups, pages, more = po_to_model(po)
    problems += more
    if len(write_textfile(groups)) > TEXT_BUFFER_CAPACITY:
        problems.append(f"C2.ENG text exceeds {TEXT_BUFFER_CAPACITY} bytes")
    hf = HelpFile(records or [HelpRecord() for _ in range(HELP_PAGES)], pages)
    for page in range(1, HELP_PAGES):
        try:
            strings = resolve_help_page(hf, page)
        except ValueError as err:
            problems.append(str(err))
            continue
        if strings is None:
            continue
        size = sum(len(s) + 1 for s in strings)
        if size > HELP_PAGE_TEXT_CAPACITY:
            problems.append(f"help page {page}: {size} bytes exceeds {HELP_PAGE_TEXT_CAPACITY}")
    return problems, warnings


# --------------------------------------------------------------------------
# Per-source fixups: shipped files whose segmentation disagrees with the
# engine's indices. Applied before alignment against the template.
# --------------------------------------------------------------------------

def _join(strings: list[bytes], index: int, sep: bytes = b" ") -> None:
    """Join strings[index] onto strings[index-1]."""
    left = strings[index - 1]
    right = strings[index]
    if left.endswith(b" ") or right.startswith(b" "):
        sep = b""
    strings[index - 1] = left + sep + right
    del strings[index]


def _split(strings: list[bytes], index: int, at: bytes) -> None:
    left, right = strings[index].split(at, 1)
    strings[index:index + 1] = [left, at + right]


FIXUPS = {
    # The French translator split several long strings with a NUL instead of
    # a space and merged two short ones; every later index in those groups
    # was shifted in the shipped game. Restore the engine's segmentation.
    "fr": [
        ("join", 0x2e, 2), ("join", 0x45, 11), ("join", 0x46, 8), ("join", 0x46, 5),
        ("join", 0x4c, 2), ("join", 0x4d, 25),
        ("split", 0xb, 2, b"action n'a pas d'effet"),
    ],
}


def apply_fixups(groups: dict[int, list[bytes]], data: bytes, name: str | None,
                 log: list[str]) -> None:
    offsets = textfile_offsets(data)
    if offsets[0x74] == offsets[0x77]:
        # 1995 layout: 0x74..0x78 all alias the Senate letter that the 1996
        # layout keeps at 0x77; the battle icon tips at 0x74 do not exist.
        del groups[0x74]
        log.append("1995 layout: no battle icon tips (group 0x74)")
    for op in FIXUPS.get(name or "", []):
        if op[0] == "join":
            _join(groups[op[1]], op[2])
            log.append(f"fixup join {op[1]:#x}/{op[2]} -> {op[1]:#x}/{op[2]-1}")
        elif op[0] == "split":
            _split(groups[op[1]], op[2], op[3])
            log.append(f"fixup split {op[1]:#x}/{op[2]}")


def align_help_pages(hf: HelpFile, template: dict[int, list[bytes] | int], log: list[str]) -> None:
    """Repair pages whose title/body segmentation disagrees with the template:
    a lone string holding both (split at the first blank line) or a body
    broken into several strings (joined back)."""
    for page, entry in hf.pages.items():
        want = template.get(page)
        if not isinstance(entry, list) or not isinstance(want, list):
            continue
        if len(entry) == 1 and len(want) == 2 and b"$$" in entry[0]:
            title, body = entry[0].split(b"$$", 1)
            hf.pages[page] = [title, body]
            log.append(f"help page {page}: split title from body")
        elif len(entry) > len(want) >= 1:
            head = entry[:len(want)]
            for extra in entry[len(want):]:
                sep = b"" if extra.startswith(HELP_BREAK.encode()) or head[-1].endswith(b" ") else b" "
                head[-1] = head[-1] + sep + extra
            hf.pages[page] = head
            log.append(f"help page {page}: joined {len(entry) - len(want)} extra string(s) onto the body")


# --------------------------------------------------------------------------
# Commands
# --------------------------------------------------------------------------

def load_sources(args) -> tuple[dict[int, list[bytes]], HelpFile]:
    groups = read_textfile(Path(args.c2).read_bytes())
    hf = read_helpfile(Path(args.help).read_bytes())
    return groups, hf


def cmd_pot(args) -> int:
    groups, hf = load_sources(args)
    refs = source_references(ROOT / "src") if not args.no_references else {}
    po = PoFile()
    po.header_comments = [
        "Caesar II text -- gettext template.",
        "Keys: 0x2f/3 = C2.ENG string group/index; help/12/0 = HELP.ENG page 12 title, /1 body.",
        "\"@12\" means: same text as help page 12. \\n is a line break; #12text# links to page 12.",
        "The game font is CP437: see tools/c2-text.py check for what it can draw.",
    ]
    po.header = {
        "Project-Id-Version": "caesar2-port",
        "MIME-Version": "1.0",
        "Content-Type": "text/plain; charset=UTF-8",
        "Content-Transfer-Encoding": "8bit",
        "Language": "en",
        "X-C2-Name": "English",
        "X-C2-Detect": decode(groups[1][0]),
    }
    po.entries = build_entries(groups, hf, None, refs, True)
    Path(args.output).write_text(po_dump(po), encoding="utf-8")
    print(f"{args.output}: {len(po.entries)} entries")
    return 0


def cmd_extract(args) -> int:
    groups, hf = load_sources(args)
    pot = po_parse(Path(args.pot).read_text(encoding="utf-8"))
    log: list[str] = []
    apply_fixups(groups, Path(args.c2).read_bytes(), args.fixups, log)
    pot_groups, pot_pages, _ = po_to_model(pot)
    align_help_pages(hf, pot_pages, log)
    # Report structural differences against the template.
    for g in range(1, TEXT_GROUPS):
        if g in TEXT_ALIASES:
            continue
        want = len(pot_groups.get(g, []))
        have = len(groups.get(g, []))
        if want != have:
            log.append(f"group {g:#x}: template has {want} strings, source has {have}")
    for page in range(1, HELP_PAGES):
        want = pot_pages.get(page)
        have = hf.pages.get(page)
        w = len(want) if isinstance(want, list) else ("@" if want is not None else None)
        h = len(have) if isinstance(have, list) else ("@" if have is not None else None)
        if isinstance(want, list) and isinstance(have, list) and len(want) != len(have):
            log.append(f"help page {page}: template has {len(want)} strings, source has {len(have)}")
    po = PoFile()
    po.header_comments = [f"Caesar II text -- {args.name} translation."]
    po.header = dict(pot.header)
    po.header.update({
        "Language": args.lang,
        "X-C2-Name": args.name,
        "X-C2-Detect": decode(groups[1][0]),
        "Plural-Forms": "nplurals=2; plural=(n != 1);",
    })
    po.entries = build_entries(groups, hf, pot, {}, False)
    have = {e.msgctxt for e in po.entries}
    for e in pot.entries:
        if e.msgctxt not in have:
            po.entries.append(PoEntry(e.msgctxt, e.msgid, ""))
            log.append(f"{e.msgctxt}: not in source, left untranslated")
    order = {e.msgctxt: i for i, e in enumerate(pot.entries)}
    po.entries.sort(key=lambda e: order.get(e.msgctxt, 1 << 30))
    Path(args.output).write_text(po_dump(po), encoding="utf-8")
    for line in log:
        print(line)
    print(f"{args.output}: {len(po.entries)} entries")
    return 0


def cmd_check(args) -> int:
    pot = po_parse(Path(args.pot).read_text(encoding="utf-8"))
    status = 0
    for path in args.po:
        po = po_parse(Path(path).read_text(encoding="utf-8"))
        problems, warnings = check_po(po, pot)
        for p in problems:
            print(f"{path}: error: {p}")
        if args.verbose:
            for w in warnings:
                print(f"{path}: warning: {w}")
        elif warnings:
            print(f"{path}: {len(warnings)} warnings (-v to list)")
        status |= 1 if problems else 0
        untranslated = sum(1 for e in po.entries if not e.msgstr)
        fuzzy = sum(1 for e in po.entries if e.fuzzy)
        print(f"{path}: {len(po.entries)} entries, {untranslated} untranslated, {fuzzy} fuzzy")
    return status


RECORDS_INC = ROOT / "src" / "platform" / "common" / "c2_port_help_records.inc"


def read_records_inc(path: Path = RECORDS_INC) -> list[HelpRecord]:
    """The page records the runtime compiles in (see cmd_records)."""
    records = []
    for line in path.read_text().splitlines():
        m = re.match(r'\{ (-?\d+), (-?\d+), (-?\d+), "([^"]*)", "([^"]*)", "([^"]*)" \},', line)
        if m:
            records.append(HelpRecord(int(m.group(1)), int(m.group(2)), int(m.group(3)),
                                      m.group(4).encode(), m.group(5).encode(), m.group(6).encode()))
    if len(records) != HELP_PAGES:
        raise ValueError(f"{path}: {len(records)} records, expected {HELP_PAGES}")
    return records


def cmd_compile(args) -> int:
    po = po_parse(Path(args.po).read_text(encoding="utf-8"))
    groups, pages, problems = po_to_model(po)
    for p in problems:
        print(p, file=sys.stderr)
    if problems:
        return 1
    if args.c2:
        Path(args.c2).write_bytes(write_textfile(groups))
    if args.help_out:
        if args.records:
            records = read_helpfile(Path(args.records).read_bytes()).records
        else:
            records = read_records_inc()
        Path(args.help_out).write_bytes(write_helpfile(HelpFile(records, pages)))
    return 0


def cmd_compare(args) -> int:
    """Compare two C2.ENG or HELP.ENG files by what the engine sees."""
    a = Path(args.a).read_bytes()
    b = Path(args.b).read_bytes()
    diffs = []
    if a[:8] == b"Textfile":
        ga, gb = read_textfile(a), read_textfile(b)
        for g in range(1, TEXT_GROUPS):
            if ga.get(g) != gb.get(g):
                diffs.append(f"group {g:#x}")
    else:
        ha, hb = read_helpfile(a), read_helpfile(b)
        for page in range(HELP_PAGES):
            if resolve_help_page(ha, page) != resolve_help_page(hb, page):
                diffs.append(f"help page {page} text")
            if ha.records[page] != hb.records[page]:
                diffs.append(f"help page {page} record")
    for d in diffs:
        print(d)
    print(f"{len(diffs)} differences")
    return 1 if diffs else 0


def cmd_records(args) -> int:
    """Emit the language-neutral help page records as a C table."""
    hf = read_helpfile(Path(args.help).read_bytes())
    lines = ["/* Generated by tools/c2-text.py records from the 1996 HELP.ENG. */",
             "/* page: left sprite, right sprite, width, left image, right image, voice */"]
    for page, r in enumerate(hf.records):
        def name(b: bytes) -> str:
            return '"' + b.decode("ascii") + '"'
        lines.append(f"{{ {r.left_sprite}, {r.right_sprite}, {r.width}, "
                     f"{name(r.left)}, {name(r.right)}, {name(r.voc)} }},")
    Path(args.output).write_text("\n".join(lines) + "\n")
    print(f"{args.output}: {len(hf.records)} records")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("pot", help="write the English template from the 1996 files")
    p.add_argument("--c2", required=True)
    p.add_argument("--help-file", dest="help", required=True)
    p.add_argument("--no-references", action="store_true")
    p.add_argument("-o", "--output", required=True)
    p.set_defaults(func=cmd_pot)

    p = sub.add_parser("extract", help="write a language .po from shipped files")
    p.add_argument("--c2", required=True)
    p.add_argument("--help-file", dest="help", required=True)
    p.add_argument("--pot", required=True)
    p.add_argument("--lang", required=True, help="language tag, e.g. de")
    p.add_argument("--name", required=True, help="native language name")
    p.add_argument("--fixups", help="named fixup set (see FIXUPS)")
    p.add_argument("-o", "--output", required=True)
    p.set_defaults(func=cmd_extract)

    p = sub.add_parser("check", help="validate .po files against the template")
    p.add_argument("--pot", required=True)
    p.add_argument("-v", "--verbose", action="store_true")
    p.add_argument("po", nargs="+")
    p.set_defaults(func=cmd_check)

    p = sub.add_parser("compile", help="reference compiler: .po -> C2.ENG / HELP.ENG")
    p.add_argument("po")
    p.add_argument("--c2")
    p.add_argument("--help-out")
    p.add_argument("--records", help="HELP.ENG whose page records to use "
                   "(default: the compiled-in table)")
    p.set_defaults(func=cmd_compile)

    p = sub.add_parser("compare", help="compare two C2.ENG or HELP.ENG files semantically")
    p.add_argument("a")
    p.add_argument("b")
    p.set_defaults(func=cmd_compare)

    p = sub.add_parser("records", help="emit the help page record table as C")
    p.add_argument("--help-file", dest="help", required=True)
    p.add_argument("-o", "--output", required=True)
    p.set_defaults(func=cmd_records)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
