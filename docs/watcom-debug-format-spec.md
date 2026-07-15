# Watcom Debug Info 3.0 Binary Format Specification

This document describes the exact binary layout of the Watcom Debug Info 3.0 format as found in Caesar II's PS.EXE, derived from studying the Open Watcom v2 source code.

## Source References

All format definitions come from the Open Watcom v2 source tree at `~/git/open-watcom/open-watcom-v2/`:

| File | Purpose |
|------|---------|
| `bld/watcom/h/wdbginfo.h` | Core debug info structures |
| `bld/watcom/h/machtype.h` | Machine type definitions (addr48_ptr, etc.) |
| `bld/watcom/h/exe16m.h` | DOS/16M BW executable header |
| `bld/watcom/h/exeflat.h` | LE (Linear Executable) header |
| `bld/exedump/c/dumpwv.c` | How wdump parses debug sections |
| `bld/exedump/c/wdwarf.c` | How wdump finds and reads the master header |
| `bld/exedump/c/d16mexe.c` | How wdump traverses the BW chain |
| `bld/dip/watcom/c/watgbl.c` | Global symbol parsing logic |
| `bld/wl/c/dbginfo.c` | How the linker writes debug info |

## PS.EXE File Layout

PS.EXE is a DOS/4GW Professional bound executable. It contains multiple spliced
executables chained via `next_header_pos` fields, followed by the actual game
code as an LE (Linear Executable), and finally the Watcom debug info.

```
Offset      Size        Content
──────────  ──────────  ─────────────────────────────────────────────────
0x00000000  0x0000F474  MZ DOS Stub (real-mode bootstrap, "requires DOS/4G")
0x0000F474  0x0000EC50  BW #1: VMM.EXP (DOS/4GW Virtual Memory Manager)
0x0001E0C4  0x000171E0  BW #2: 4GWPRO.EXP (DOS/4GW Professional extender)
0x000352A4  0x000CA1EF  LE: Caesar II game code (MZ stub + LE executable)
  0x000352A4  0x00002AA8  ├── MZ stub for LE
  0x00037D4C  0x000002F4  ├── LE header + object/page tables
  0x00038071  0x0003D2B4  ├── Fixup section (relocations)
  0x000754A4  0x0007D000  ├── Data pages (code: 125 pages, data: 13 pages)
  0x000F24A4  ...         └── (last page: 4079 bytes, not full 4096)
0x000FF493  0x0003F40B  Watcom Debug Info 3.0
0x0013E89E  (EOF)       Total: 1,304,734 bytes
```

### Key Insight: The BW Segments Are NOT the Game

The two BW modules (VMM.EXP and 4GWPRO.EXP) are the **DOS/4GW Professional
extender infrastructure**, not the game code. They set up protected mode, manage
virtual memory, and then load the LE executable which contains the actual
Caesar II game. The BW chain is traversed via `next_header_pos` fields:

```
MZ stub
  └─ BW #1 (VMM.EXP):   next_header_pos → 0x1E0C4
                                              │
                         BW #2 (4GWPRO.EXP): next_header_pos → 0x352A4
                                                                  │
                                              LE (Caesar II)  ◄───┘
                                              (signature != BW, chain stops)
```

When `next_header_pos` points to something with signature `LE` instead of `BW`,
the DOS/4GW loader treats it as the application payload to execute.

## Layer 1: MZ DOS Header

Standard DOS MZ executable header at offset 0. Key fields:

| Offset | Size | Field | Value |
|--------|------|-------|-------|
| 0x00 | 2 | Signature | `MZ` (0x5A4D) |
| 0x02 | 2 | Last page bytes | 0x0074 |
| 0x04 | 2 | Pages in file | 0x007B |
| 0x08 | 2 | Header size (paragraphs) | 0x0020 |
| 0x14 | 2 | Initial IP | 0x2382 |
| 0x16 | 2 | Initial CS | 0x01BD |

The MZ stub prints "This program requires DOS/4G" and loads the extender.

## Layer 2: BW DOS/16M Headers (Extender Only)

### BW Header Structure

From `exe16m.h`, the `dos16m_exe_header` structure (128 bytes before GDT):

```c
struct dos16m_exe_header {
    uint16_t signature;           // 'BW' = 0x5742
    uint16_t last_page_bytes;     // length of image mod 512
    uint16_t pages_in_file;       // number of 512 byte pages
    uint16_t reserved1;
    uint16_t reserved2;
    uint16_t min_alloc;           // required memory, in KB
    uint16_t max_alloc;           // max KB (private allocation)
    uint16_t stack_seg;           // selector of stack segment
    uint16_t stack_ptr;           // initial SP value
    uint16_t first_reloc_sel;     // huge reloc list selector
    uint16_t init_ip;             // initial IP value
    uint16_t code_seg;            // selector of code segment
    uint16_t runtime_gdt_size;    // runtime GDT size in bytes
    uint16_t MAKEPM_version;      // ver * 100, GLU = (ver+10)*100
    // --- end of DOS-style EXE header ---
    uint32_t next_header_pos;     // file pos of next spliced .EXP
    uint32_t cv_info_offset;      // offset to start of debug info
    uint16_t last_sel_used;       // last selector value used
    uint16_t pmem_alloc;          // private xm amount KB if nonzero
    uint16_t alloc_incr;          // auto ExtReserve amount, in KB
    uint8_t  reserved4[6];
    uint16_t options;             // runtime options
    uint16_t trans_stack_sel;     // sel of transparent stack
    uint16_t exp_flags;           // see ef_ constants
    uint16_t program_size;        // size of program in paras
    uint16_t gdtimage_size;       // size of gdt in file (bytes)
    uint16_t first_selector;      // first user selector (0 => 0x80)
    uint8_t  default_mem_strategy;
    uint8_t  reserved5;
    uint16_t transfer_buffer_size;
    uint8_t  reserved6[48];
    char     EXP_path[64];        // original .EXP file name
    // GDT image follows immediately (gdtimage_size bytes)
    // Then program image follows
};
```

### BW #1: VMM.EXP (offset 0xF474)

The DOS/4GW Virtual Memory Manager. Provides demand-paging and 4GB virtual
address space support. This is Tenberry Software's proprietary code.

| Field | Value |
|-------|-------|
| Original name | VMM.EXP |
| Entry point | 0080:88B3 |
| Next header pos | 0x1E0C4 (→ BW #2) |

### BW #2: 4GWPRO.EXP (offset 0x1E0C4)

The DOS/4GW Professional extender kernel. Sets up protected mode, loads the LE
executable, and transfers control to it. This is Tenberry Software's proprietary
code, NOT the game.

| Field | Value |
|-------|-------|
| Original name | 4GWPRO.EXP |
| Entry point | 0080:2CD3 |
| Next header pos | 0x352A4 (→ LE executable) |

## Layer 3: LE (Linear Executable) — THE GAME

The LE at offset 0x352A4 contains the actual Caesar II game code. It is a
**32-bit flat model** executable compiled with Watcom C/C++ 32.

### LE Header (at file offset 0x37D4C)

The LE has its own MZ stub (0x2AA8 bytes) before the actual LE header.

| Field | Value |
|-------|-------|
| Signature | `LE` (0x454C) |
| CPU type | 2 (80386) |
| OS type | 1 (OS/2) |
| Module flags | 0x00000200 |
| Number of pages | 138 |
| Page size | 4096 bytes |
| Last page size | 4079 bytes |
| EIP object | 1 (code), EIP = 0x62D14 |
| ESP object | 2 (data), ESP = 0x89420 |
| Number of objects | 2 |
| Data pages offset | 0x40200 (from MZ start) |

### LE Object Table

| Object | Virtual Size | Base Addr | Flags | Pages | Description |
|--------|-------------|-----------|-------|-------|-------------|
| 1 | 0x7C1D0 (508,368 bytes) | 0x10000 | R-X 32-bit | 125 | **Code** |
| 2 | 0x89420 (562,208 bytes) | 0x90000 | RW- 32-bit | 13 (file) | **Data + BSS** |

### Data Pages in File

| Content | File Offset | Size |
|---------|-------------|------|
| Code pages (1-125) | 0x754A4 | 512,000 bytes (125 × 4096) |
| Data pages (126-138) | 0xF24A4 | 53,248 bytes (13 × 4096) |

Note: The last code page is only 4079 bytes of actual data (page 125 is not
full). Virtual size 0x7C1D0 = 124 × 4096 + 4048 = 512,000 - 48 ≈ matches.

### Entry Point

The EIP is 0x62D14 in Object 1. At this offset in the code, the bytes read
`"WATCOM C/C++32"` — this is the Watcom C runtime startup code (`cstart_`).

## Layer 4: Watcom Debug Info 3.0

### How to Find the Debug Info

The master debug header is at the **very end of the file**. To find it:

1. Seek to `file_size - sizeof(master_dbg_header)` = `file_size - 14`
2. Read 14 bytes as `master_dbg_header`
3. Verify `signature == 0x8386`
4. The debug info starts at `file_size - debug_size` (the `debug_size` field in the header)

### Master Debug Header

14 bytes, packed, at the very end of the file:

```c
struct master_dbg_header {      // 14 bytes total
    uint16_t signature;         // 0x8386 (WAT_DBG_SIGNATURE)
    uint8_t  exe_major_ver;     // 3 (EXE_MAJOR_VERSION)
    uint8_t  exe_minor_ver;     // 0
    uint8_t  obj_major_ver;     // 1
    uint8_t  obj_minor_ver;     // 0
    uint16_t lang_size;         // size of language table in bytes
    uint16_t segment_size;      // size of segment table in bytes
    uint32_t debug_size;        // total size of ALL debug info (including this header)
};
```

For PS.EXE:
- `signature` = 0x8386
- `exe_major_ver` = 3, `exe_minor_ver` = 0
- `obj_major_ver` = 1, `obj_minor_ver` = 0
- `lang_size` = 0x0002 (just "C\0")
- `segment_size` = 0x0004 (two uint16 entries: 0x0001, 0x0002)
- `debug_size` = 0x0003F40B (259,083 bytes)

### Debug Info Layout (from start of debug data)

```
Offset from debug start    Content
────────────────────────    ───────────────────────────
0x00000000                  Source Language Table (lang_size bytes)
lang_size                   Segment Address Table (segment_size bytes)
lang_size + segment_size    Section 0 Header + Data
...                         (more sections if overlays exist)
debug_size - 14             Master Debug Header (14 bytes)
```

### Source Language Table

A sequence of null-terminated strings. For PS.EXE: just `"C\0"` (2 bytes).

### Segment Address Table

An array of `uint16_t` values listing the segment numbers used. For PS.EXE: `[0x0001, 0x0002]` (4 bytes).

These segment numbers correspond to the LE objects:
- **Segment 1 = LE Object 1** (Code, 0x7C1D0 bytes, 32-bit flat)
- **Segment 2 = LE Object 2** (Data + BSS, 0x89420 bytes, 32-bit flat)

### Section Debug Header

Each section starts with a `section_dbg_header` (14 bytes):

```c
struct section_dbg_header {     // 14 bytes total
    uint32_t mod_offset;        // offset to module info from section start
    uint32_t gbl_offset;        // offset to global symbols from section start
    uint32_t addr_offset;       // offset to address info from section start
    uint32_t section_size;      // total size of this section
    uint16_t section_id;        // section ID number
};
```

For PS.EXE Section 0:
- `mod_offset` = 0x00025262
- `gbl_offset` = 0x00026885
- `addr_offset` = 0x0003ECBB
- `section_size` = 0x0003F3F7

### Module Info Records

Each module is a variable-length `mod_dbg_info` record:

```c
struct mod_dbg_info {
    uint16_t language;          // offset into language table
    // demand_info for locals:
    uint32_t locals_info_off;   // offset from section start to local data
    uint16_t locals_entries;    // number of entries in locals link table
    // demand_info for types:
    uint32_t types_info_off;    // offset from section start to type data
    uint16_t types_entries;     // number of entries in types link table
    // demand_info for lines:
    uint32_t lines_info_off;    // offset from section start to line data
    uint16_t lines_entries;     // number of entries in lines link table
    // name:
    uint8_t  name_len;          // length of name string
    char     name[name_len];    // module name (NOT null-terminated)
};
```

Total size per record: `2 + 3*(4+2) + 1 + name_len` = `21 + name_len` bytes.

For PS.EXE, there are 178 modules (indices 0-177), including:
- `D:\C2\CODE\c2.c` (module 0)
- `D:\C2\CODE\pcsound.c` (module 2)
- `D:\C2\CODE\action.c` (module 23)
- `R:\NET\LIBS\AIL\DEV3\FLAT\aildebug.c` (module 59)

### Global Symbol Info

Global symbols are packed sequentially from `section_start + gbl_offset` to `section_start + addr_offset`.

Each symbol is a `v3_gbl_info` record (variable length):

```
Bytes 0-3:   offset (uint32_t LE) — flat offset into LE object
Bytes 4-5:   segment (uint16_t LE) — 1=code (LE Object 1), 2=data (LE Object 2)
Bytes 6-7:   module index (uint16_t LE)
Byte  8:     kind flags (uint8_t)
Byte  9:     name length N (uint8_t)
Bytes 10..10+N-1: name characters
```

Total record size: `10 + name_length`

**Kind flags** (can be OR'd together):
- `0x01` = `GBL_KIND_STATIC` - static/local symbol
- `0x02` = `GBL_KIND_DATA` - data symbol
- `0x04` = `GBL_KIND_CODE` - code/function symbol

### Address Info

Address info maps code/data ranges to modules. Packed sequentially from `section_start + addr_offset` to `section_start + section_size`.

Each entry is a `seg_dbg_info`:

```c
struct seg_dbg_info {
    // addr48_ptr base:
    uint32_t base_offset;       // base offset in segment (always 0 for PS.EXE)
    uint16_t base_segment;      // segment number (1=code, 2=data)
    uint16_t count;             // number of address entries (mask with 0x7FFF)
    // followed by count addr_dbg_info entries:
    struct {
        uint32_t size;          // size of this address range
        uint16_t mod;           // module index
    } entries[count];
};
```

For PS.EXE, segment 1 (code) has 164 module entries with cumulative sizes
totaling 0x7C1CF bytes — which is exactly `LE Object 1 vsize (0x7C1D0) - 1`.
This confirms the debug offsets are direct flat offsets into the LE code object.

## Symbol-to-Address Mapping

### The Correct Mapping (32-bit Flat)

Debug symbol offsets are **direct flat offsets into the LE objects**:

- **Code symbol** at `segment=1, offset=X` → byte offset `X` from start of LE Object 1
- **Data symbol** at `segment=2, offset=X` → byte offset `X` from start of LE Object 2

For Ghidra import with a 32-bit flat address space:
- LE Object 1 (code) is loaded at base address 0x10000 (the LE relocation base)
- LE Object 2 (data) is loaded at base address 0x90000 (the LE relocation base)
- Symbol at `0001:0x00000010` → Ghidra address `0x10010` (code base + offset)
- Symbol at `0002:0x00001234` → Ghidra address `0x91234` (data base + offset)

### Why the Old Mapping Was Wrong

The previous approach tried to map debug offsets to BW#2 GDT selectors
(0x80-0xB0), treating the 76KB of 16-bit BW code as the game. This resulted in:
- Only 223 of 3,857 symbols resolving (5.8%)
- 3,634 symbols marked as "dead" (beyond physical code)
- The game appearing to be only 76KB when PS.EXE is 1.3MB

The reality is that the BW#2 segments are the DOS/4GW loader, and the game is
the 508KB LE executable that follows it.

## Line Number Info

For each module with `lines_entries > 0`, the line data is at `section_start + lines_info_off`.

The line data starts with an offset table: `(lines_entries + 1)` uint32 values.

Each line data block is a `v3_line_segment`:

```c
struct v3_line_segment {
    uint32_t segment;           // offset into address info section
    uint16_t count;             // number of line entries
    struct {
        uint16_t line;          // source line number
        uint32_t code_offset;   // flat offset from LE object base
    } entries[count];           // repeated count times
};
```

## Validation

We can validate our parser against the existing `PS.EXE.wdump` output:

1. **Module count**: 178 modules (indices 0-177)
2. **First module**: `D:\C2\CODE\c2.c`
3. **Symbol count**: 3,857 symbols
4. **First symbol**: `main_` at `0001:00000010` (code)
5. **Symbol kinds**: 2,178 code + 1,535 data + 83 static code + 61 static data
6. **Debug size**: 0x3F40B bytes
7. **addr_info segment 1 total**: 0x7C1CF bytes = LE Object 1 vsize - 1
