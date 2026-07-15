# Caesar II `Textfile` Format (`.ENG` / `.GER` / `.FRE` / `.SPA`)

> ImHex pattern: [`tools/imhex/caesar2_textfile.hexpat`](../tools/imhex/caesar2_textfile.hexpat).
> Re-verified against the current decomp (`lib32.c` `get_buffer_ofset` reads
> `text_buffer[8 + i*4]` as a 3-byte LE offset; `c2.c`
> `readfile("c2.eng", text_buffer, 0x9c40, 0)` = 40000-byte buffer) -- the
> layout below is accurate.

## Overview

Caesar II uses a custom binary text format for all localised UI strings. The format is
identified by the magic `"Textfile"` and is used for the main game text files:

| Filename   | Language |
|------------|----------|
| `C2.ENG`   | English  |
| `C2.GER`   | German   |
| `C2.FRE`   | French   |
| `C2.SPA`   | Spanish  |

Despite the `.eng` extension on all variants, the format is the same for every language.
The active file is selected at startup by `set_language` (`PS.EXE` @ `0x70CD1`), which
copies the appropriate filename into the global `lang_file` variable (`0xC493C`).

> **Note:** `HELP.ENG` / `HELP.GER` / etc. use a **different** format with magic `"Helpfile"`
> (a fixed 58-byte page-record database read by `load_media_entry`). See
> [`helpfile-format.md`](helpfile-format.md). They are **not** covered by this document.

---

## Loading

The entire file is loaded raw into the `text_buffer` global (`0xB84CC`) by
`load_start_graphics` via a single call:

```c
readfile(lang_file, &text_buffer, 40000, 0);
```

`readfile` (`PS.EXE`) opens the file, seeks to offset 0, and reads up to `param_3` bytes.
No parsing is done at load time — the buffer is accessed in-place using the offset table.

### Buffer Size Limit

The `text_buffer` is **40,000 bytes** (hard-coded in the `readfile` call). If the file
exceeds this size, data is silently truncated. All known retail files are well within this
limit:

| File (largest known) | Size    | Headroom |
|----------------------|---------|----------|
| German C2.ENG        | 38,248 B | 1,752 B  |
| English C2.ENG       | 31,876 B | 8,124 B  |
| French C2.ENG        | 32,954 B | 7,046 B  |

**Do not create files larger than 40,000 bytes.**

---

## Binary Format

### Magic (8 bytes, offset `0x00`)

```
54 65 78 74 66 69 6c 65   "Textfile"
```

Eight ASCII bytes with **no null terminator**. This is the only fixed-size header field.

### Offset Table (offset `0x08`, variable length)

Immediately after the magic, a table of **4-byte little-endian absolute file offsets** begins.
Each entry is the absolute byte offset within the file of the corresponding string group.

```
Offset  Size  Description
------  ----  -----------
0x08    4     entry[0]  — always 0x00000000 (null/sentinel)
0x0C    4     entry[1]  — absolute file offset of string group 1
0x10    4     entry[2]  — absolute file offset of string group 2
...
```

#### Entry Count

The number of entries is **not stored explicitly**. It is derived from `entry[1]`, which
is the offset of the first real string (and therefore the byte immediately after the table):

```
num_entries = (entry[1] - 8) / 4
```

For `C2.ENG` (Europe Rerelease 1996-04-25):
- `entry[1]` = `0x000254` → first string at file offset 596
- `num_entries` = `(0x254 - 8) / 4` = **147 entries** (indices 0–146)

#### Offset Table Limits

- Each offset is a 4-byte LE value. In practice only 3 bytes are used (the 4th is always
  `0x00`), giving a maximum addressable offset of `0xFFFFFF` = 16,777,215 bytes — far
  beyond the 40,000-byte buffer limit.
- The maximum number of entries is bounded by the buffer limit:
  `floor((40000 - 8) / 4)` = **9,998 entries** (theoretical maximum).
- All known retail files have exactly **147 entries**.

#### Aliased Entries

Multiple offset-table entries **may point to the same file offset** (aliasing). This is
used to expose the same string group under several logical indices without duplicating the
string data. For example, in `C2.ENG` (Europe Rerelease 1996-04-25), entries 116–120 all
point to offset `0x739d`:

```
entry[116] = 0x00739d  ─┐
entry[117] = 0x00739d   │  all point to the same string group
entry[118] = 0x00739d   │
entry[119] = 0x00739d   │
entry[120] = 0x00739d  ─┘
```

The parser preserves aliasing by sharing the same `list` object for all entries that map
to the same file offset. The serialiser detects shared objects (by identity) and emits the
string data only once, producing binary-identical output.

#### Example (C2.ENG first 10 entries)

```
Index  File Offset  First string at that offset
-----  -----------  ---------------------------
    0  0x000000     (null sentinel — always 0)
    1  0x000254     "File"
    2  0x000271     "Edit"
    3  0x0002a4     ...
    4  0x0002c8     ...
    5  0x0002fa     ...
    6  0x000370     ...
    7  0x0005be     ...
    8  0x00076d     ...
    9  0x0007ce     ...
```

### String Area (offset = `entry[1]`, variable length)

Each entry in the offset table points to a **string group** — one or more null-terminated
strings packed consecutively. The game accesses individual strings within a group by counting
`\0`-terminated segments.

#### Character Encoding

All strings use **CP437** (IBM PC / DOS codepage 437). Non-ASCII characters appear in
German, French, and Spanish files:

| CP437 byte | Character | Example |
|------------|-----------|---------|
| `0x81`     | `ü`       | `B\x81rger` → `Bürger` |
| `0x84`     | `ä`       | `B\x84der` → `Bäder` |
| `0x94`     | `ö`       | `k\x94nnen` → `können` |
| `0x99`     | `Ö`       | `\x99rtlicher` → `Örtlicher` |
| `0x9a`     | `Ü`       | `\x9aberaus` → `Überaus` |
| `0x82`     | `é`       | `R\x82servoir` → `Réservoir` |

#### String Termination

- Each string is terminated by a `\0` (NUL byte).
- Multiple strings within a group are packed back-to-back, each terminated by `\0`.
- Leading control characters (bytes `< 0x20`) before the first printable character are
  skipped by `get_text_pointer`.

#### String Navigation Algorithm

`get_text_pointer` (`PS.EXE` @ `0x264BD`) navigates to string `n` within group `i`:

```c
// Watcom __watcall: group index in EAX, string index in EDX
void get_text_pointer(int group_idx, int string_idx) {
    text_pointer = &text_buffer + get_buffer_ofset(group_idx);
    // Count string_idx boundaries
    // A boundary = '\0' followed by a printable char (or another '\0')
    while (string_idx > 0) {
        if (*text_pointer == '\0') {
            if (text_pointer[-1] > 0x1f || text_pointer[-1] == '\0')
                string_idx--;
        }
        text_pointer++;
    }
    // Skip leading control characters
    while (*text_pointer < 0x20)
        text_pointer++;
}
```

A "string boundary" is counted when:
- The current byte is `\0` **AND**
- The previous byte is either `\0` or a printable character (`> 0x1f`)

This means consecutive `\0` bytes do **not** count as multiple boundaries — only the
transition from printable content to `\0` (or `\0` to `\0` at the very start) counts.

---

## Rendering Special Characters

The font renderer `put_a_font_string` (`PS.EXE` @ `0x26C2E`) interprets two special
byte values at render time. These are **not** stored as escape sequences in the Textfile
— they are rendering-engine conventions:

| Byte | Char | Behaviour |
|------|------|-----------|
| `0x23` | `#`  | **Insert placeholder**: if `insert_place == 1`, replaced character-by-character from the `insert_text` global buffer. If `insert_place == 0`, rendered as a space. |
| `0x5f` | `_`  | **Padding space**: always rendered as a space. Used for trailing-space padding in fixed-width layouts. |

No `#` or `_` characters appear in the known retail C2.ENG/C2.GER/C2.FRE files — the
placeholder mechanism exists in the rendering engine but is not used in the Textfile strings.

### In-Game Letter Format (groups 116–146)

Groups 116–146 in C2.ENG contain in-game letters from the Senate/Emperor. Each group has
the structure:

```
string[0]  = "To"          ← addressee label
string[1]  = "..."         ← letter body text
string[2+] = ""            ← optional empty strings (padding/unused slots)
```

The game renders these letters in `show_emperor_message` (`PS.EXE` @ `0x597DC`):

```c
// Render "To" label from string[0]
font_list(group_idx, 0, 0x70, 0xfc, &font2, 0x10);
// Append player name directly from c2inf+0x1a (DAT_0009d00a) on the same line
put_a_font_string(&c2inf.player_name, x_is + 0x74, 0xfc, &font2, 0x10);
// Render letter body from string[1], word-wrapped
font_format_split(group_idx, 1, 0x68, 0x11c, 0x138, 100, 0x68, 0x138, &font1, 0x10);
```

The player name is stored at `_c2inf + 0x1a` (the `c2inf` save-game struct, 26 bytes in).
It is appended after `"To"` by a direct `put_a_font_string` call — **not** via a `#`
placeholder in the string data.

Groups 116–120 are **aliased** (all point to the same file offset) — they share the
same welcome letter text, used for different game contexts.

The message system (`put_message` / `show_messages` / `message`) queues group indices
into `message_list`. When the group index is > 0x77 (119), `message()` calls
`show_emperor_message`; otherwise it calls `show_basic_message`.

---

## Key Functions (PS.EXE)

All addresses are Ghidra virtual addresses (code segment base `0x10000`).

| Symbol | Address | Description |
|--------|---------|-------------|
| `set_language` | `0x70CD1` | Sets `lang_file` and `media_file` based on language code (1=ENG, 2=GER, 3=FRE, 4=SPA) |
| `get_buffer_ofset` | `0x26485` | Returns absolute file offset for entry `i`: reads 4-byte LE dword from `text_buffer + 8 + i*4` |
| `get_text_pointer` | `0x264BD` | Sets global `text_pointer` to string `n` within group `i` |
| `load_to_text_buffer` | `0x263AF` | Copies text from a buffer position into a destination buffer (same navigation as `get_text_pointer`) |
| `load_from_text_buffer` | `0x2641A` | Copies text from a source buffer into a buffer position |
| `load_format_buffer_from_disk` | `0x26B1A` | Reads a 2-byte BE offset at `idx*4+0x1e` then a string at `offset+0x1c`. This does **not** match `HELP.ENG` (read by `load_media_entry`) and has no decompiled callers — earlier "HELP.ENG reader" claims were inaccurate. |
| `put_a_font_string` | `0x26C2E` | Renders a string character-by-character; handles `#` insert placeholder and `_` padding space |
| `get_insert_letter` | `0x26EFE` | Returns next character from `insert_text` buffer (used for `#` substitution) |

### Key Globals (PS.EXE)

| Symbol | Address | Description |
|--------|---------|-------------|
| `text_buffer` | `0xB84CC` | 40,000-byte buffer holding the loaded Textfile |
| `text_pointer` | `0xC348A8` | Pointer into `text_buffer` set by `get_text_pointer` |
| `lang_file` | `0xC493C` | Filename of the active language file (e.g. `"c2.eng"`) |
| `media_file` | — | Filename of the active help file (e.g. `"help.eng"`) |

---

## `get_buffer_ofset` Decompilation

```c
// PS.EXE @ 0x26485  (Watcom __watcall: param_1 in EAX)
int get_buffer_ofset(int param_1) {
    param_1 = param_1 * 4;
    // Reads bytes at text_buffer+8+param_1 as 3-byte little-endian
    // (4th byte is always 0x00, so equivalent to a 4-byte LE dword read)
    return (uint8_t)(text_buffer[8 + param_1])
         | (uint8_t)(text_buffer[9 + param_1]) << 8
         | (uint8_t)(text_buffer[10 + param_1]) << 16;
}
```

Ghidra shows `DAT_000b84d4` = `text_buffer + 8` (= `0xB84CC + 8 = 0xB84D4`).

---

## File Layout Summary

```
Offset        Size        Description
------        ----        -----------
0x0000        8           Magic: "Textfile" (no null terminator)
0x0008        N×4         Offset table: N entries of 4-byte LE absolute file offsets
                            entry[0] = 0x00000000  (always null sentinel)
                            entry[1] = offset of string group 1  ← also = table end
                            entry[2] = offset of string group 2
                            ...
entry[1]      variable    String area: null-terminated strings packed consecutively
                            Each entry[i] points to the start of a string group
                            Multiple strings within a group are separated by \0
```

### C2.ENG Statistics (Europe Rerelease 1996-04-25)

| Field | Value |
|-------|-------|
| File size | 31,876 bytes (0x7C84) |
| Magic | `"Textfile"` |
| Offset table | 147 entries (indices 0–146), bytes 0x08–0x253 |
| String area | bytes 0x254–0x7C83 |
| String groups | 146 usable (entry[0] is null sentinel) |
| Encoding | CP437 |

---

## Intermediate Representation (for round-trip tooling)

The Python parser in [`c2/parsers/textfile.py`](../c2/parsers/textfile.py) produces a
`TextFile` dataclass that can be serialised back to binary-identical output:

```python
@dataclass
class TextFile:
    groups: list[list[bytes]]  # groups[i] = list of raw CP437 byte strings
```

- `groups[0]` is always `[]` (the null sentinel entry).
- Each `groups[i]` is a list of raw `bytes` objects (CP437-encoded, no null terminators).
- Round-tripping: `parse(path)` → modify → `serialise(textfile)` → binary-identical output.
- For human editing, use `decode_group(group)` / `encode_group(strings)` to convert
  between `bytes` and `str` (CP437 ↔ Unicode).

### Serialisation Rules

To reconstruct the binary file from a `TextFile`:

1. Write magic `b"Textfile"` (8 bytes).
2. Compute string area: for each group, join strings with `b"\x00"` and append `b"\x00"`.
   Group 0 (sentinel) contributes nothing to the string area.
3. Compute absolute offsets: `entry[0] = 0`, `entry[i] = cumulative byte position`.
4. Write offset table: one 4-byte LE dword per entry.
5. Write string area.

The offset table size is `num_groups * 4` bytes, so the string area starts at
`8 + num_groups * 4`.
