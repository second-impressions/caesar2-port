# Open Watcom wcc386 Inline Assembly Buffer Overflow

## Summary

Open Watcom's 32-bit C compiler (`wcc386`) crashes with a buffer overflow
when compiling C files containing many inline `_asm { db ...; dd offset ...; }`
blocks. The compiler reports "0 warnings, 0 errors" but then terminates with
`*** buffer overflow detected ***: terminated` during object file emission.

## Affected Files

Currently two C2 game modules trigger this bug:

| File | Functions | `_asm` blocks | `dd offset` fixups | Raw bytes |
|---|---|---|---|---|
| `evolver.c` | 39 | 39 | 849 | ~9KB |
| `int_c2.c` | 94 | 146 | 1689 | ~20KB |

Other files with more fixups (e.g. `action.c` with 2054, `map.c` with 2901)
compile successfully. The crash is not strictly correlated with fixup count,
block count, or total code size.

## Root Cause Analysis

### The 4096-byte `_asm` block limit

Each `_asm { }` block has a hard limit of `MAXIMUM_BYTESEQ = 4096` bytes
in Watcom's internal buffer (`bld/cc/h/pragdefn.h:82`). This buffer stores
not just the raw assembled bytes, but also fixup metadata:

- Each `db 0xNN` → 1 byte in the buffer
- Each `dd offset sym` → **14 bytes** in the buffer:
  - 4 bytes of data (the 32-bit offset placeholder)
  - 1 `FLOATING_FIXUP_BYTE` marker
  - ~9 bytes of fixup metadata (symbol reference, fixup type, offset)

The check is at `bld/cc/c/asmstmt.c:120`:
```c
if( AsmCodeAddress > MAXIMUM_BYTESEQ ) {
    CErr1( ERR_TOO_MANY_BYTES_IN_PRAGMA );
}
```

We work around this by splitting `_asm` blocks before hitting 3800 bytes
of internal cost (tracking `raw_bytes + fixup_count * 10`). Multiple
consecutive `_asm {}` blocks in one function produce contiguous code
with no extra bytes inserted between them.

### The crash (separate from the 4096 limit)

Even with correctly-sized `_asm` blocks, certain files crash the compiler.
The crash occurs **after** successful compilation ("0 errors") during
object file writing, suggesting an internal data structure overflow.

### Root cause: WASM parses db bytes as instructions

WASM (the assembler embedded in wcc386) parses `db` byte sequences
as x86 instructions to track the instruction stream. When a `db` line
ends with an **incomplete x86 instruction** (e.g. a multi-byte opcode
whose operands are on the next line), and the next line is a
`dd offset symbol` (fixup reference), WASM's parser state is corrupted.

Example that crashes:
```
_asm {
    db 0x80, 0xBB     /* starts 'add [ebx+...], imm8' — incomplete */
    dd offset symbol  /* WASM tries to parse this as operand bytes → CRASH */
}
```

The `0x80 0xBB` begins an x86 instruction that expects a 32-bit
displacement + 8-bit immediate (6 more bytes). When those bytes don't
arrive before the `dd offset`, WASM's internal buffer overflows.

This does NOT happen when each line is its own `_asm {}` block because
`AsmSysInit()` resets the parser state for each block.

## Workaround

Emit each `db`/`dd offset` line as its own single-line `_asm {}` block:

```c
void some_func(void) {
    _asm { db 0x53, 0x51, 0x55 }
    _asm { db 0xC7, 0x05 }
    _asm { dd offset some_global }
    _asm { db 0x01, 0x00, 0x00, 0x00 }
    _asm { db 0x59, 0x5B, 0xC3 }
}
```

Consecutive single-line `_asm {}` blocks produce contiguous code with
no extra bytes inserted between them (verified by disassembly). This
avoids the internal buffer overflow entirely while maintaining
byte-identical output.

## Environment

- Open Watcom v2 (64-bit Linux host, targeting DOS/4GW 32-bit)
- Compiler: `wcc386 -bt=dos -mf -3r -s`
- glibc fortify detected the overflow (`*** buffer overflow detected ***`)

## References

- `bld/cc/h/pragdefn.h:82` — `#define MAXIMUM_BYTESEQ 4096`
- `bld/cc/c/asmstmt.c:97-160` — `AsmStmt()`, the `_asm {}` handler
- `bld/cc/c/cpragx86.c:1014-1020` — `AsmSysInit()`, buffer/counter reset
- `bld/cc/c/cpragx86.c:595-603` — `AsmSysLine()`, WASM invocation per line
- `bld/fe_misc/h/callinfo.c:401` — `WatcallInfo.objname = NULL` (register convention)
- `bld/comp_cfg/h/langenv.h:74-75` — `TS_DATA_MANGLE="_*"`, `TS_CODE_MANGLE="*_"`
