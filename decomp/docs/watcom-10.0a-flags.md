# Watcom 10.0a flag reference

Captured straight out of the `watcom-10.0a-dosemu2` container by running
`wcc386` and `wlink ?` with no arguments. Use this as the source of truth
when picking flags for `decomp-verify` builds — every option below is
guaranteed to actually exist in the version that ships with the toolchain
container, which is **not** the same set of flags the modern Open Watcom
v2 docs describe.

To regenerate:

```bash
mkdir -p /tmp/wctest && cd /tmp/wctest
yes "" | timeout 30 podman run --rm -i -v "$PWD:/src" \
    watcom-10.0a-dosemu2 wcc386 > wcc386.txt 2>&1
yes "" | timeout 30 podman run --rm -i -v "$PWD:/src" \
    watcom-10.0a-dosemu2 wlink ? > wlink.txt 2>&1
```

(`yes ""` defeats the `(Press return to continue)` pager that wcc386 /
wlink emit on stdout.)

---

## `wcc386` — WATCOM C32 Optimizing Compiler 10.0a

```
Usage: wcc386 [options] file [options]
             ( /option is also accepted )
```

### Build target / model

| Flag             | Meaning                                                       |
|------------------|---------------------------------------------------------------|
| `-b{m,d,w}`      | build (Multi thread, Dynamic link, Default windowing)         |
| `-bt[=<os>]`     | build target for operating system `<os>`                      |
| `-m{s,m,c,l,f}`  | memory model (Small, Medium, Compact, Large, **Flat**)        |
| `-3r` / `-3s`    | 386 register / stack calling conventions                      |
| `-4r` / `-4s`    | 486 register / stack calling conventions                      |
| `-5r` / `-5s`    | Pentium register / stack calling conventions                  |
| `-7`             | inline 80x87 instructions                                     |
| `-fpc`           | calls to floating-point library                               |
| `-fpi` / `-fpi87`| inline 80x87 (with / without emulation)                       |
| `-fp{2,3,5}`     | optimize floating-point for 287 / 387 / Pentium               |
| `-fpr`           | generate backward-compatible 80x87 code                       |

### Debug / browsing

| Flag         | Meaning                                                            |
|--------------|--------------------------------------------------------------------|
| `-db`        | generate browsing information                                      |
| `-d1{+}`     | line-number debug info                                             |
| `-d2`        | full symbolic debug info                                           |
| `-d3`        | full symbolic + unreferenced type names                            |
| `-d+`        | allow extended `-d` macro definitions                              |
| `-d<n>[=t]`  | precompilation `#define`                                           |
| `-h{w,d,c}`  | debug output format (Watcom, Dwarf, Codeview)                      |

### Optimization — `-o{a,c,d,e,f[+],i,l,m,n,o,p,r,s,t,u,x,z}`

| Letter   | Meaning                                                              |
|----------|----------------------------------------------------------------------|
| `a`      | relax aliasing constraints                                           |
| `c`      | **disable** `<call followed by return>` → `<jump>` optimization       |
| `d`      | disable all optimizations                                            |
| `e[=n]`  | expand user functions inline; `n` controls max size                  |
| `f`      | generate traceable stack frames *as needed*                          |
| `f+`     | always generate traceable stack frames                               |
| `i`      | expand intrinsic functions inline                                    |
| `l`      | enable loop optimizations                                            |
| `l+`     | enable loop unrolling                                                |
| `m`      | generate inline 80x87 code for math functions                        |
| `n`      | allow numerically unstable optimizations                             |
| `o`      | continue compilation if low on memory                                |
| `p`      | generate consistent floating-point results                           |
| `r`      | reorder instructions for best pipeline usage                         |
| `s`      | favor code size over execution time                                  |
| `t`      | favor execution time over code size                                  |
| `u`      | all functions must have unique addresses                             |
| `x`      | equivalent to `-omiler -s`                                           |
| `z`      | do not assume a pointer deref implies pointer not NULL               |

> **Note**: `-oc` *disables* the call→jmp tail-call rewrite. Leaving `c`
> out (the default) keeps the rewrite enabled. There is no separate
> "epilogue merging" knob; what we've been calling "ret-merge" in
> diff output is the call→jmp rewrite cooperating with the linker's
> placement of identical tail blocks. Aggressive `-o` settings (`-ox`,
> `-oxat`, etc.) are needed before the compiler emits epilogues
> uniform enough for that placement to actually collapse.

> **Frame pointers**: `-of` is not the default. Without `-of` the
> compiler is free to omit the frame pointer in any function — which
> is exactly what PS.EXE looks like.

### Codegen / language

| Flag                | Meaning                                                      |
|---------------------|--------------------------------------------------------------|
| `-r`                | save/restore segment registers across calls                  |
| `-ri`               | return chars and shorts as ints                              |
| `-s`                | **remove stack overflow checks** (used by us); see Rule 43 — selectively re-enable per-function via `#pragma on(check_stack)` |
| `-sg`               | generate calls to grow the stack                             |
| `-st`               | touch stack through SS first                                 |
| `-ei`               | force enums to be type `int`                                 |
| `-en`               | emit routine names in the code segment                       |
| `-ep[<n>]`          | call prologue hook routine                                   |
| `-ee`               | call epilogue hook routine                                   |
| `-ez`               | generate Phar Lap EZ-OMF object files                        |
| `-j`                | change `char` default from unsigned to signed                |
| `-zp{1,2,4,8}`      | pack structure members                                       |
| `-zm`               | place each function in a separate segment                    |
| `-zc`               | place literal strings in the code segment                    |
| `-zl`               | remove default library information                           |
| `-zld`              | remove file dependency information                           |
| `-zq`               | operate quietly                                              |
| `-zs`               | syntax check only                                            |
| `-zt<n>`            | set data threshold                                           |
| `-zu`               | `SS != DGROUP`                                               |
| `-zw`               | generate code for Microsoft Windows                          |
| `-zg`               | generate function prototypes using base types                |
| `-z{a,e}`           | disable / enable language extensions                         |
| `-zk{0,1,2}`        | double-byte char support (Kanji / Chinese / Korean)          |
| `-zk0u`             | translate double-byte Kanji to UNICODE                       |
| `-zku=<cp>`         | load UNICODE translate table for code page                   |

### DS / FS / GS pinning

| Flag    | Meaning                                                                 |
|---------|-------------------------------------------------------------------------|
| `-zdf`  | DS floats — not fixed to DGROUP                                         |
| `-zdp`  | DS is pegged to DGROUP                                                  |
| `-zdl`  | load DS directly from DGROUP                                            |
| `-zff`  | FS floats — not fixed to a segment                                      |
| `-zfp`  | FS is pegged to a segment                                               |
| `-zgf`  | GS floats — not fixed to a segment                                      |
| `-zgp`  | GS is pegged to a segment                                               |

### File / output

| Flag                  | Meaning                                                         |
|-----------------------|-----------------------------------------------------------------|
| `-fo=<file>`          | set object or preprocessor output file name                     |
| `-fh=<file>`          | use precompiled headers                                         |
| `-fhq=<file>`         | use precompiled headers quietly                                 |
| `-fi=<file>`          | force `<file>` to be `#include`d                                |
| `-i=<dir>`            | another include directory                                       |
| `-u<name>`            | undefine macro                                                  |
| `-v`                  | output function declarations to `.def`                          |
| `-w<n>`               | warning level                                                   |
| `-we`                 | treat all warnings as errors                                    |
| `-e<n>`               | error limit                                                     |
| `-nc=<name>`          | code class name                                                 |
| `-nd=<name>`          | data segment name                                               |
| `-nm=<name>`          | module name                                                     |
| `-nt=<name>`          | text segment name                                               |
| `-g=<grp>`            | code group name                                                 |
| `-p{l,c,w=<n>}`       | preprocess (line directives / preserve comments / wrap width)   |

---

## `wlink` — WATCOM Linker 10.0

```
usage: wlink {directive}
```

### Top-level directives (all formats)

| Directive                                            | Meaning                                                                          |
|------------------------------------------------------|----------------------------------------------------------------------------------|
| `File obj{,obj}`                                     | input object/library files                                                       |
| `Name exe`                                           | output executable filename                                                       |
| `OPtion opt{,opt}`                                   | linker options (see below)                                                       |
| `Library lib{,lib}`                                  | additional libraries to search                                                   |
| `Path p{;p}`                                         | search path for object files                                                     |
| `LIBPath p{;p}`                                      | search path for libraries                                                        |
| `LIBFile obj{,obj}`                                  | objects pulled in only if referenced                                             |
| `Debug Watcom dblist \| Codeview \| Dwarf \| All`    | emit debug info                                                                  |
| `MODTrace mod{,mod}`                                 | print module load trace                                                          |
| `SYMTrace sym{,sym}`                                 | print symbol resolve trace                                                       |
| `SYStem name` / `SYStem Begin name … End`            | use a `wlsystem.lnk` system definition (`dos4g`, `dos`, `os2v2`, …)              |
| `FORMat form`                                        | output format (see per-format sections)                                          |
| `Alias a=sym{,a=sym}`                                | symbol aliases                                                                   |
| `REFerence sym{,sym}`                                | force a symbol to be linked                                                      |
| `@ file`                                             | include directives from another file                                             |
| `# comment`                                          | comment                                                                          |
| `DISAble msg{,msg}`                                  | suppress numbered diagnostics                                                    |
| `SOrt [GLobal] [ALPhabetical]`                       | map sort order                                                                   |
| `LANGuage JApanese \| CHinese \| KOrean`             | message language                                                                 |

`dblist` element: one of `LInes`, `Types`, `LOcals`, `All`, `STatic`.

### `OPtion` values (all formats)

| Option                          | Meaning                                                          |
|---------------------------------|------------------------------------------------------------------|
| `Map[=file]`                    | write map file                                                   |
| `NODefaultlibs`                 | do **not** pull in object-file default-library records           |
| `STack=n`                       | set stack size                                                   |
| `Dosseg`                        | DOS segment ordering                                             |
| `Verbose`                       | verbose                                                          |
| `OSName=str`                    | set OS name string                                               |
| `Caseexact` / `NOCASEexact`     | case sensitivity for symbol matching                             |
| `NAMELen=n`                     | symbol name length limit                                         |
| `Quiet`                         | suppress banner / progress                                       |
| `SYMFile[=file]`                | emit symbol file                                                 |
| `Undefsok`                      | tolerate undefined externals                                     |
| `STRip`                         | strip debug info                                                 |
| `MAXErrors=n`                   | error limit                                                      |
| `CAChe` / `NOCAChe`             | object file caching                                              |
| `MANGlednames`                  | preserve mangled C++ names in map                                |
| `STATics`                       | include statics in map                                           |
| `ARTificial`                    | include artificial symbols in map                                |
| `REDefsok` / `NOREDefsok`       | allow / forbid duplicate symbol definitions                      |

### `FORMat OS2 LE` (the format we use)

```
form ::= "OS2" ["FLat"|"LE"|"LX"]
              ["PHYSdevice" | "VIRTdevice"
               | ["DLl"["INITGlobal"|"INITInstance"
                          ["TERMInstance"|"TERMGlobal"]]]
               | "PM" | "PMCompatible" | "FULLscreen"]
```

Per-format directives:

| Directive                          | Meaning                                          |
|------------------------------------|--------------------------------------------------|
| `NEWsegment`                       | start a new segment                              |
| `SEGment seg{,seg}`                | per-segment options                              |
| `IMPort imp{,imp}`                 | DLL imports                                      |
| `EXPort exp{,exp}`                 | DLL exports                                      |
| `EXPort = wlib_directive_file`     | export list from file                            |

Per-format options:

| Option                                                              | Meaning                          |
|---------------------------------------------------------------------|----------------------------------|
| `Alignment=n`                                                       | section alignment                |
| `OLDlibrary=dll`                                                    | old DLL name                     |
| `VERSion=major.[minor]`                                             | DLL version                      |
| `DEscription desc`                                                  | module description               |
| `MODName=name`                                                      | module name                      |
| `Heapsize=n`                                                        | heap size                        |
| `ONEautodata` / `MANYautodata` / `NOAutodata`                       | autodata segment policy          |
| `PACKCode=n` / `PACKData=n`                                         | code/data packing                |
| `OFFset=n`                                                          | base offset                      |
| `NEWFiles`                                                          | new file format flag             |
| `PROTmode`                                                          | protected mode                   |
| `STUB=name`                                                         | DOS stub name                    |

`segdesc` model words: `PReload`/`LOadoncall`, `SHared`/`NONShared`,
`EXECUTEOnly`/`EXECUTERead`/`READOnly`/`READWrite`, `Iopl`/`NOIopl`,
`CONforming`/`NONConforming`, `PERManent`/`NONPERManent`, `INValid`,
`RESident`, `CONTiguous`, `DYNamic`.

### Other available formats (for reference)

`wlink` 10.0 also supports `Dos`, `WIndows`, `WIndows NT`, `PHARlap`,
`NOVell`, `QNX`, and `ELF` output formats. We don't use them — see
`/tmp/wlink_raw.txt` for the full per-format directive lists if you
ever need them.

---

## Decision: default flags are `-bt=dos -mf -3r -s -os`

After extensive flag sweeps + an exact match of `slave_estimate` under `-os`,
we've committed to `-os` (favor size) as the default. Reasoning:

- **`-os` produced the only near-byte-exact match** on a non-trivial
  function we were confident we had transcribed correctly: `slave_estimate`
  matches with only 2 bytes of call-target relocation cascade.
- **DOS game context**: mid-90s DOS floppy distribution meant EXE size
  mattered. `-os` was a very common choice.
- **Small simple functions all improve**: `check_for_promotion` (150→143),
  `city_pop_limit_10_to_1` (54→51), `adjust_peace_criteria` (48→42),
  `get_morale_and_readiness` (127→125).
- **Aggregate-total metric is NOT reliable**: 60% of the total diff comes
  from 3 large functions (`set_current_cohort_totals`, `fill_cohort_centuries`,
  `slave_welfare`) whose C source is still speculative. Their diffs reflect
  the gap between our guessed source and the real source, not flag quality.

### Caveats / contradictions

Some instruction-level fingerprints in PS.EXE suggest the original may have
used time-favouring codegen rather than strict `-os`:

- PS.EXE uses `mov edx, eax; sar edx, 0x1f` (5 bytes) where `-os` emits
  `cdq` (1 byte) for sign-extending EAX before signed division.
- PS.EXE uses `mov [addr], 0` immediate stores (10 bytes) where `-os`
  emits `xor reg, reg; mov [addr], reg` (8 bytes) for zero-stores.

These suggest the real build may have been `-ot` or a mixed setting we
can't reproduce. We accept this and stick with `-os` because it gives the
best *match* on ground-truth functions even if the aggregate is worse.

### Interaction with `#pragma aux modify exact [eax]`

Adding narrow clobber-set pragmas to extern functions can force the
callee's codegen to push/pop every register it uses (matching PS.EXE's
"save everything" style) and can also free the caller's allocator to
leave locals in scratch registers across calls. **But the pragma
interacts poorly with `-os`**: under `-os`, the size-favouring body
layout no longer fills the forced callee-saved slots, and the pragma
actively makes things worse (observed on `slave_welfare`: 256 bytes
without pragma → 284 bytes with pragma). Under `-ore` it was the
opposite (297 → 76). We've dropped the pragma from `slave_welfare`
since the default is now `-os`.

**Rule of thumb**: only add `#pragma aux ... modify exact [eax]` if you
empirically verify it improves the specific function's diff count under
the current default flags. Don't sprinkle it preemptively.

## Empirical flag sweep — best combos for PS.EXE matching

Ran on `decomp/src/formulae.c` (19 non-stub functions, 2156 byte diffs at
baseline) across all available `watcom-*-dosemu2` images and the whole
relevant `wcc386` flag space. Lower total = closer to PS.EXE.

| Compiler   | Baseline | Best `-o…`        | Best total |
|------------|----------|--------------------|------------|
| 9.5        | 2206     | `-or`              | 2180       |
| 9.5c       | 2220     | `-ore`             | 2201       |
| **10.0a**  | **2156** | **`-ore`**         | **2131**   |
| 10.0b      | 2156     | `-ore`             | 2131       |
| 10.5       | —        | (broken image, do not use) | —  |
| 10.6a      | 2220     | `-ore`             | 2201       |

**10.0a + `-ore` is the winner** and is the new default in
`c2/commands/decomp_verify.py`. Note however:

- **No exact matches exist.** The best we can do is ≈98.8% match rate.
  The residual diffs are register allocation, immediate zero-store
  idioms, and the WLINK ret-merge tail-jumps — none of which flags can
  reach.
- **`-or`** (instruction reordering for pipeline) is the single
  highest-impact flag, saving ~22 bytes overall and consistently
  helping 10+ functions.
- **`-oe`** (inline user functions) saves another 3 bytes for
  `want_promotion` via the `make_emperor` one-liner.
- **`-oa`** (relax aliasing) is a trap — it saves ~20 bytes on
  `get_morale_and_readiness` but costs ~80 bytes on
  `set_current_cohort_totals` by defeating CSE on the global `temp_army`.
- **`-ot` / `-os` / `-ox`**: marginal wins on small functions, losses
  on the four big ones.
- **`-of+`** (always frame pointer): *hurts everything*. PS.EXE was
  built without frame pointers.
- **`-ol` / `-ol+`** (loop opts / unroll): neutral to slightly
  negative. Original was not built with aggressive loop opts.
- **`-oc`** (disable call→jmp): no effect — the rewrite is default-on,
  so passing `-oc` would only *disable* it (and that made no
  measurable difference either, suggesting PS.EXE doesn't heavily
  rely on the rewrite in the functions we've looked at).
- **Struct packing (`-zp1/2/4/8`)**: `-zp1` no-op (default already
  packs our `army_rec`), others fail the `sizeof == 0xAF` assert.
- **`-3r` vs `-5r`**: not tested but PS.EXE was built for 386.
- **Linker tweaks**: irrelevant to per-function bytes.
  `SYSTEM dos4g`, `OPTION osname`, `OPTION PACKCode=...`,
  `OPTION Alignment=...`, `OPTION NODEFAULTLIBS` — all produce the
  same 2131-byte total. WLINK 10.0 has no identical-code-folding /
  tail-merge option in its directive list, so the linker cannot fix
  codegen differences.

### Takeaway

Accept that `c2 decomp-verify --cflags '-bt=dos -mf -3r -s -ore'` is
our floor. Residual register-allocation and zero-store cascade diffs
must be documented as NOTE comments per-function rather than
chased via flag combinations — more flags will not help.

## Default libs, headers, predefines — empirical dead ends

Hypothesis we tested: maybe third-party libraries, standard headers, or
built-in predefines are nudging the compiler toward different output
than PS.EXE. Empirical answer: **no**.

### Default libs make zero difference

`OPTION NODEFAULTLIBS` vs. no option: both produce 2131 byte diffs on
`formulae.c -ore`. This is because `wcc386` emits fully-formed object
code **before** the link step, and WLINK 10.0 has no whole-program
optimisation / identical-code-folding / tail-merge pass. The linker
can rearrange functions in memory but cannot rewrite their bytes.
Watcom CRT, Miles Sound System, and Smacker are orthogonal to
per-function codegen in our .c files.

### Default struct packing is already 1

Verified by emitting `sizeof(struct { char a; int b; })` into a .obj
and disassembling with `wdisasm`:

| Flag         | `sizeof` |
|--------------|---------:|
| (none)       |        5 |
| `-zp1`       |        5 |
| `-zp8`       |        8 |

So Watcom 10.0a on `-bt=dos -mf -3r` packs to 1-byte alignment by
default. The `army_rec` struct in `formulae.c` therefore happens to
land at exactly `0xAF` bytes without needing any `#pragma pack`.

> ⚠️ **`-zp8` does NOT fail the `army_rec_size_check` typedef** —
> Watcom 10.0a silently accepts `typedef int x[-1];` and `typedef int
> x[1/0];`. Static-assert array tricks are unreliable in this
> compiler. Validate struct layouts by emitting `sizeof` into
> `_DATA` and running `wdisasm`.

### Headers can influence packing but `formulae.c` has no `#include`s

Several Watcom 10.0a headers open with `#pragma pack(1);` and never
restore it (`stdio.h`, `stdlib.h`, …). If the original game source
included one of these and then declared structs, those structs would
be force-packed to 1 regardless of any `-zp` flag. Since **our**
`formulae.c` rewrites don't include any headers, this quirk doesn't
affect us — and it wouldn't help even if it did, because Watcom's
default packing already matches.

### Built-in predefines (all with `-bt=dos -mf -3r`)

```
__WATCOMC__ = 1000
__386__     = 1
__DOS__     = 1          (only with -bt=dos; -bt=dos4g drops it)
__FLAT__    = 1
M_I386      = 1
__STDC__    = 1
__SW_3R     = 1
```

None of these feed back into codegen the way a macro like
`__CHAR_SIGNED__` would, and none of them are referenced in
`formulae.c`.

### What's left

The residual 2131 bytes of diff across 19 functions is compiler
codegen that we cannot flag our way out of:

1. **Register allocation.** The original picks `ebx/ecx/edx/esi/edi`
   in an order that Watcom 10.0a's allocator doesn't reproduce from
   our C source.
2. **Immediate zero-store idiom.** PS.EXE uses `xor reg,reg` + a run
   of `mov [addr], reg` stores. Watcom 10.0a emits `mov [addr], 0`
   immediate stores. No flag changes this; all versions in the
   container produce the same 5-byte-per-store output.
3. **WLINK ret-merge / shared epilogues.** PS.EXE has several
   functions whose entire return path is a `jmp` to a different
   function's `pop ... ret`. Neither `wcc386` nor `wlink` in any
   container produces this.

See per-function `NOTE:` comments in `decomp/src/formulae.c` for
callouts.

## What's missing (and why it matters)

A few things you might *expect* to find but won't:

- **No explicit "tail-merge" / "identical code folding" linker option.**
  Whatever the original PS.EXE build was doing to share `pop … ret`
  epilogues happens at the *compiler* level (`-o…` settings + the
  call→jmp rewrite from leaving `-oc` off). The linker just lays the
  resulting blocks out next to each other.
- **No `-of` by default.** Frame pointers are omitted, which matches
  PS.EXE.
- **`-ox` does not include `-oa` or `-oc`.** It expands to `-omiler -s`.
  If you want `-oa` (relax aliasing) or want to *disable* call→jmp,
  pass them explicitly.
- **`-zp` packing default is 8 (modern Watcom)** but for `-bt=dos -3r`
  Watcom 10 happens to leave the `army_rec` struct unpadded —
  empirically verified by the `sizeof == 0xAF` `typedef` assert in
  `formulae.c`. Don't trust this without a `static_assert`-style
  guard.
