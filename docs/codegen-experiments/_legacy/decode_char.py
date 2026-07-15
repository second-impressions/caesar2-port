"""DecodeChar (pump.c) — unsigned-short index widening: `and edx,0xffff`
in-place mask vs `xor eax,eax; mov ax,dx` move-and-zero-extend.

PS.EXE `DecodeChar` (68 b) walks the adaptive-Huffman `son[]` tree.  `c`
is the node index; PS keeps it in EDX throughout (callee-save, `push edx`)
and widens it IN PLACE with `and edx,0xffff` before using it as the index
`son[c]` (`mov dx, word [eax + edx*2]`, son base freshly loaded into EAX).
The return is a plain `mov eax, edx` (edx already clean).

Our build (`unsigned short c`, 12 b diff) instead MOVES c into EAX
(`xor eax,eax; mov ax,dx`) for the index — base in EDX
(`mov dx, word [edx + eax*2]`) — and re-zero-extends at the return
(`xor eax,eax; mov ax,dx`).

PS reference (0x6FE9D)::

    push edx
    mov  edx, [son]
    mov  dx,  word [edx + 0x4e4]     ; c = son[0x272]
    xor  eax, eax ; mov ax, dx ; cmp eax, 0x273 ; jge end
    call GetBit ; add edx, eax        ; c += GetBit()
    and  edx, 0xffff                  ; <-- in-place widen, c stays in edx
    mov  eax, [son] ; mov dx, word [eax + edx*2]   ; c = son[c]
    jmp  top
    sub  edx, 0x273 ; movsx eax, dx ; call update
    mov  eax, edx                     ; <-- return c (already clean)
    pop  edx ; ret

CONCLUSION (2026-06, ~30 trials across two sessions — UNREACHABLE):
The ENTIRE 12 b real-build diff reduces to ONE allocator tie-break — the
truncation FORM of `(unsigned short)(c + GetBit())`:

    PS : and edx, 0xffff           (source==dest reg → in-place mask)
    RC : xor eax,eax ; mov ax, dx  (source!=dest reg → move-form)

That single choice decides the SIB base/index PHYSICAL register pair for
`son[c]` (PS: son=EAX base, c=EDX index;  RC: son=EDX base, c=EAX index,
because RC parks the masked c in EAX which forces son into EDX), and it
CASCADES: with c clean in EDX, PS's `return c` is a bare `mov eax, edx`
(2 b); RC re-zero-extends `xor eax,eax; mov ax,dx` (5 b).  Fix the one
`and edx,0xffff` and the index regs + the return both fall out byte-exact.

BREAKTHROUGH (2026-06, son-register lever FOUND; whole-TU claim REFUTED):
  * REFUTED whole-TU: `RegAlloc()` (regalloc.c:1332) does
    `HW_CAsgn(GivenRegisters, HW_EMPTY)` at entry, and RegAlloc/Generate run
    PER-PROCEDURE (Generate called per function from bldins.c).  No
    cross-function regalloc carryover.  cgex single-TU reproduces son=EDX
    exactly, confirming the effect is LOCAL, not whole-TU.
  * LEVER FOUND: a NAMED local pointer flips son EDX→EAX (Rule-24a/27 named-
    temp class).  `unsigned short *p; ... p = (unsigned short *)son; c = p[c];`
    produces PS's exact index `mov eax,[son]; ... mov dx,[eax+edx*2]` AND the
    in-place `and edx,0xffff` — son now in EAX, c stays in EDX.  (cgex
    trial `son-after-getbit`.)  Inline `son[c]` keeps son in EDX (move-form).
  * RESIDUE after the lever (real build, still 12 b): a 2-instruction
    Rule-27 ORDER swap — PS emits `and edx,0xffff` (the ushort wrap of
    `c += GetBit()`, materialized at the += assignment) BEFORE `mov eax,[son]`;
    our p-local emits the son load (the `p = son` statement) first and the
    mask at the index.  Plus the return form.  The order is the SAME
    ushort-vs-int CONV tension one level down: ushort c won't materialize the
    `+=` wrap as a standalone `and` (it's optimised away / deferred), and int
    c materialises it but breaks the zero-extend compare (`(unsigned short)c`
    adds a cleaning `and`, real build 12→39/41).  No single form lands all of
    {ushort compare, in-place wrap-`and` before the load, son in EAX, clean
    `mov eax,edx` return} simultaneously — but the son-register half is now
    solved, which earlier sessions had wrongly called irreducible.
  * BLOCKER pinned: the order swap is Watcom's U2-truncation materialization
    TIMING.  PS materializes the `c += GetBit()` ushort wrap EAGERLY as a
    standalone `and edx,0xffff` at the += (before the son load); our build
    defers it LAZILY to the index (after the `p=son` load).  ~60 variants
    can't force eager: `c &= 0xffff` / `(c+GetBit())&0xffff` fold into the
    index's lazy clean; `int c` materializes but breaks the compare; `p`
    hoisted before the loop regresses (kept loop-invariant — PS reloads son
    every iteration, so `p = son` must stay INSIDE the loop).  The
    eager-vs-lazy choice is in the cg CONV handling (OP_CONVERT "handles
    itself", i86ldstr.c:512), not a source lever.  The return form is the
    same timing issue at the tail.  Son-register lever = the solved half.
  * REGTRACE CONFIRMATION (c2 regtrace DecodeChar — GiveBestReg tracer):
    DecodeChar has 10 conflicts — c (savings 55, a WORD reg AX/DX/BX/CX) +
    9 temps.  The son-load and index-CONV temps have EQUAL savings (30/30),
    so the son-register is a pure USE-ORDER tie (Rule 28a) — the p-local
    (son used-first) is exactly the right lever, validated.  Critically the
    regtrace shows the residue is NOT a regalloc choice; it is the eager-vs-
    lazy wrap.  ROOT CAUSE (everything chains from this): with the LAZY wrap
    (ushort c) a CONV temp EXISTS and ties son for EAX, winning by use-order;
    with PS's EAGER wrap (`and edx` at the +=) NO CONV temp exists at the
    index, so son grabs EAX uncontested AND the wrap precedes the load.
    All three residues (index regs, instr order, return) collapse to the one
    front-end wrap-timing decision, which is gated on c's type: ushort=lazy,
    int=eager-but-breaks-the-compare.  No source shape forces eager wrap for
    ushort c — this is a front-end CONV-emission policy, not a regalloc or
    source-shape lever.  Tool-confirmed wall.
  * RULE 49 closes the loop: PS's `and edx,0xffff` is the AND-form zext
    (Rule 49 `& MASK` idiom), which Watcom emits ONLY on a genuinely-WIDE
    (dword-class) value.  regtrace proves our c is WORD-class (it is
    `unsigned short`) so the wrap is move-form, never `and`.  Both ways to
    make c dword-class fail: p-local forces it only AT THE INDEX (wrap stays
    lazy → Rule-27 order swap); `int c` forces eager dword wrap but the
    16-bit son[] loads leave dirty high bits needing an EXTRA cleaning `and`
    for the 32-bit compare (PS's compare is the clean move-form `xor;mov
    ax,dx`).  `(c+GetBit())&0xffff` stored to ushort c folds to the implicit
    truncation, not the AND form.  IRREDUCIBLE CORE: c must be SIMULTANEOUSLY
    word-class (clean move-form compare) AND dword-class (eager AND-form
    wrap) — no single C type is both.

DEEPENED (2026-06, +~12 more trials, OW1 i86ldstr.c/makeaddr.c):
The diff is TWO opposite CONV reg-reuse decisions, and PS mixes them:
  * compare `(int)(unsigned short)c < 0x273`: PS does the U2→U4 as a COPY
    `xor eax,eax; mov ax,dx` (result in EAX, c stays clean-enough in EDX).
  * index `son[c]`: PS does the U2→U4 zero-extend IN-PLACE `and edx,0xffff`
    (result reuses EDX) and loads son into EAX, giving `[eax+edx*2]`.
`unsigned short c` makes BOTH conversions the copy-form (compare ✓ but the
body index also copies → move-form ✗).  `int c` + `c & 0xffff` makes BOTH
in-place (body ✓ `and edx` + `[eax+edx*2]`, PROVEN byte-perfect body in the
`synth-int-uscmp-idxand` trial — but the compare then emits an EXTRA
`and edx,0xffff` to clean the int load, +6 b cascade; real build 12→41).
No single type yields PS's mix because it ultimately reduces to which
register `son` (the freshly-loaded global base) takes: PS=EAX (c stays
EDX → in-place `and`), ours=EDX (c evicted to EAX → move-form).  That base
register pick is a regalloc tie-break (likely whole-TU GivenRegisters /
SortList, NOT reproducible in cgex single-TU isolation) with no lever in
DecodeChar's own source.

Verified NOT the lever: types (ushort c / son short*), the per-access son
cast, int-vs-uint return type, GetBit/update prototypes (GetBit CallZap is
{eax}, so c correctly survives EDX across the call in BOTH builds),
operand-order swap `c[son]`, embedding the `+=` in the subscript, caching
son into a local pointer.

Earlier things tried & failed:
  * `int c` / `unsigned int c` + masks: regress (break the narrow compare
    `xor;mov ax,dx;cmp eax,0x273` and the zero-extended initial load).
  * mask at the index cast `son[(unsigned short)c]`: moves the `and edx`
    to the loop TOP (compare) instead of the body — still RC-form index.
  * merged add+index `son[(c+GetBit())&0xffff]`: regresses (59-69 b).
  * cached son pointer (cache-sp/base-first/son-local-ptr): regress.
  * `son[c & 0xffff]`, ptr-math `*(ushort*)((char*)son+2*c)`: no change.
  * `int r = c - 0x273` return temp: IMPROVES in cgex (-1 b) but REGRESSES
    in the real build (12→14) — the real `update()` call's register
    effects differ from the cgex stub, so cgex is NOT faithful for the
    return here.  Keep the baseline `c -= 0x273; return (unsigned int)c`.
This is the same SIB base-vs-index register tie-break flavour as Rule 96,
but the SIB is already formed; the residue is purely the physical reg pick.

Run::  uv run c2 cgex run decode_char
"""

from c2.commands.cgex import Experiment

_PRELUDE = """
extern short *son;
extern int GetBit(void);
extern void update(short n);
"""

_DEFS = """
short *son;
int GetBit(void) { return son[0]; }
void update(short n) { son[0] = n; }
"""

exp = Experiment(
    name="decode_char",
    ps_function="DecodeChar",
    externs={},
    prelude=_PRELUDE,
    extra_defs=_DEFS,
)

exp.add("baseline", """
unsigned int DecodeChar(void)
{
    unsigned short c;
    c = ((unsigned short *)son)[0x272];
    while (c < 0x273) {
        c += (unsigned short)GetBit();
        c = ((unsigned short *)son)[c];
    }
    c -= 0x273;
    update((short)c);
    return (unsigned int)c;
}
""", note="current source (unsigned short c)")

# ── return-type variations ───────────────────────────────────────────────────
exp.add("ret-int", """
unsigned int DecodeChar(void)
{
    unsigned short c;
    c = ((unsigned short *)son)[0x272];
    while (c < 0x273) {
        c += (unsigned short)GetBit();
        c = ((unsigned short *)son)[c];
    }
    c -= 0x273;
    update((short)c);
    return c;
}
""", note="return c (no cast)")

exp.add("ret-type-int", """
int DecodeChar(void)
{
    unsigned short c;
    c = ((unsigned short *)son)[0x272];
    while (c < 0x273) {
        c += (unsigned short)GetBit();
        c = ((unsigned short *)son)[c];
    }
    c -= 0x273;
    update((short)c);
    return c;
}
""", note="int return type")

# ── c as int with explicit masks (match `and edx,0xffff`) ────────────────────
exp.add("int-c-mask-add", """
int DecodeChar(void)
{
    int c;
    c = ((unsigned short *)son)[0x272];
    while (c < 0x273) {
        c = (c + GetBit()) & 0xffff;
        c = ((unsigned short *)son)[c];
    }
    c -= 0x273;
    update((short)c);
    return c;
}
""", note="int c, mask (c+GetBit)&0xffff")

exp.add("uint-c-mask-add", """
unsigned int DecodeChar(void)
{
    unsigned int c;
    c = ((unsigned short *)son)[0x272];
    while (c < 0x273) {
        c = (c + GetBit()) & 0xffff;
        c = ((unsigned short *)son)[c];
    }
    c -= 0x273;
    update((short)c);
    return c;
}
""", note="unsigned int c, mask")

exp.add("int-c-mask-step", """
int DecodeChar(void)
{
    int c;
    c = ((unsigned short *)son)[0x272];
    while (c < 0x273) {
        c += GetBit();
        c &= 0xffff;
        c = ((unsigned short *)son)[c];
    }
    c -= 0x273;
    update((short)c);
    return c;
}
""", note="int c, separate c &= 0xffff")

# ── index expression variations (keep c in edx) ──────────────────────────────
exp.add("idx-deref", """
unsigned int DecodeChar(void)
{
    unsigned short c;
    c = ((unsigned short *)son)[0x272];
    while (c < 0x273) {
        c += (unsigned short)GetBit();
        c = *((unsigned short *)son + c);
    }
    c -= 0x273;
    update((short)c);
    return (unsigned int)c;
}
""", note="*((ushort*)son + c)")

exp.add("idx-int-tmp", """
unsigned int DecodeChar(void)
{
    unsigned short c;
    int ci;
    c = ((unsigned short *)son)[0x272];
    while (c < 0x273) {
        c += (unsigned short)GetBit();
        ci = c;
        c = ((unsigned short *)son)[ci];
    }
    c -= 0x273;
    update((short)c);
    return (unsigned int)c;
}
""", note="int ci = c; son[ci]")

# ── GetBit add variations ────────────────────────────────────────────────────
exp.add("add-nocast", """
unsigned int DecodeChar(void)
{
    unsigned short c;
    c = ((unsigned short *)son)[0x272];
    while (c < 0x273) {
        c += GetBit();
        c = ((unsigned short *)son)[c];
    }
    c -= 0x273;
    update((short)c);
    return (unsigned int)c;
}
""", note="c += GetBit() (no cast)")

exp.add("add-explicit-mask", """
unsigned int DecodeChar(void)
{
    unsigned short c;
    c = ((unsigned short *)son)[0x272];
    while (c < 0x273) {
        c = (unsigned short)(c + GetBit());
        c = ((unsigned short *)son)[c];
    }
    c -= 0x273;
    update((short)c);
    return (unsigned int)c;
}
""", note="c = (ushort)(c + GetBit())")

# ── son base via a local pointer (force son into a single reg) ───────────────
exp.add("son-local-ptr", """
unsigned int DecodeChar(void)
{
    unsigned short c;
    unsigned short *s = (unsigned short *)son;
    c = s[0x272];
    while (c < 0x273) {
        c += (unsigned short)GetBit();
        c = s[c];
    }
    c -= 0x273;
    update((short)c);
    return (unsigned int)c;
}
""", note="cached unsigned short *s = son")

# ── KEY NEW ANGLE: int c, mask at the INDEX cast.  Goal: `c += GetBit()`
# stays plain 32-bit in EDX, `(unsigned short)c` emits `and edx,0xffff`
# right before the index, c stays in EDX (EAX free for son), and the
# `return c` is a clean `mov eax,edx`. ───────────────────────────────────────
exp.add("int-c-idxcast", """
unsigned int DecodeChar(void)
{
    int c;
    c = ((unsigned short *)son)[0x272];
    while (c < 0x273) {
        c += GetBit();
        c = ((unsigned short *)son)[(unsigned short)c];
    }
    c -= 0x273;
    update((short)c);
    return c;
}
""", note="int c, mask at index (unsigned short)c")

exp.add("int-c-idxcast-castbit", """
unsigned int DecodeChar(void)
{
    int c;
    c = ((unsigned short *)son)[0x272];
    while (c < 0x273) {
        c += (unsigned short)GetBit();
        c = ((unsigned short *)son)[(unsigned short)c];
    }
    c -= 0x273;
    update((short)c);
    return c;
}
""", note="int c, (ushort)GetBit + mask at index")

exp.add("int-c-idxand", """
unsigned int DecodeChar(void)
{
    int c;
    c = ((unsigned short *)son)[0x272];
    while (c < 0x273) {
        c += GetBit();
        c = ((unsigned short *)son)[c & 0xffff];
    }
    c -= 0x273;
    update((short)c);
    return c;
}
""", note="int c, son[c & 0xffff]")

exp.add("int-c-rettype", """
int DecodeChar(void)
{
    int c;
    c = ((unsigned short *)son)[0x272];
    while (c < 0x273) {
        c += GetBit();
        c = ((unsigned short *)son)[(unsigned short)c];
    }
    c -= 0x273;
    update((short)c);
    return c;
}
""", note="int return + int c + mask at index")

# ── explicit 32-bit mask on unsigned short c (force `and edx`) ────────────────
exp.add("us-mask-sep", """
unsigned int DecodeChar(void)
{
    unsigned short c;
    c = ((unsigned short *)son)[0x272];
    while (c < 0x273) {
        c += (unsigned short)GetBit();
        c &= 0xffff;
        c = ((unsigned short *)son)[c];
    }
    c -= 0x273;
    update((short)c);
    return (unsigned int)c;
}
""", note="unsigned short c, separate c &= 0xffff")

# ── pointer-math index: explicit *2 scaling (changes SIB base/index) ──────────
exp.add("idx-ptr-math", """
unsigned int DecodeChar(void)
{
    unsigned short c;
    c = ((unsigned short *)son)[0x272];
    while (c < 0x273) {
        c += (unsigned short)GetBit();
        c = *(unsigned short *)((char *)son + 2 * (int)c);
    }
    c -= 0x273;
    update((short)c);
    return (unsigned int)c;
}
""", note="*(ushort*)((char*)son + 2*c)")

# ── int c, son load hoisted into the index expression with explicit cast ─────
exp.add("int-c-uintcast", """
unsigned int DecodeChar(void)
{
    int c;
    c = ((unsigned short *)son)[0x272];
    while (c < 0x273) {
        c += GetBit();
        c = ((unsigned short *)son)[(unsigned int)c & 0xffff];
    }
    c -= 0x273;
    update((short)c);
    return c;
}
""", note="int c, son[(uint)c & 0xffff]")

# ── MERGED add+index: keep the 32-bit add-result and mask it straight
# into the index (avoid round-tripping c through 16-bit dx). ─────────────────
exp.add("merged-mask", """
unsigned int DecodeChar(void)
{
    unsigned short c;
    c = ((unsigned short *)son)[0x272];
    while (c < 0x273) {
        c = ((unsigned short *)son)[(c + GetBit()) & 0xffff];
    }
    c -= 0x273;
    update((short)c);
    return (unsigned int)c;
}
""", note="c = son[(c + GetBit()) & 0xffff]  (ushort c)")

exp.add("merged-temp", """
unsigned int DecodeChar(void)
{
    unsigned short c;
    c = ((unsigned short *)son)[0x272];
    while (c < 0x273) {
        int t = (c + GetBit()) & 0xffff;
        c = ((unsigned short *)son)[t];
    }
    c -= 0x273;
    update((short)c);
    return (unsigned int)c;
}
""", note="int t = (c + GetBit()) & 0xffff; c = son[t]")

exp.add("merged-temp-and-at-idx", """
unsigned int DecodeChar(void)
{
    unsigned short c;
    c = ((unsigned short *)son)[0x272];
    while (c < 0x273) {
        int t = c + GetBit();
        c = ((unsigned short *)son)[t & 0xffff];
    }
    c -= 0x273;
    update((short)c);
    return (unsigned int)c;
}
""", note="int t = c + GetBit(); c = son[t & 0xffff]")

exp.add("merged-nomask", """
unsigned int DecodeChar(void)
{
    unsigned short c;
    c = ((unsigned short *)son)[0x272];
    while (c < 0x273) {
        c = ((unsigned short *)son)[c + GetBit()];
    }
    c -= 0x273;
    update((short)c);
    return (unsigned int)c;
}
""", note="c = son[c + GetBit()]  (no explicit mask)")

# ── return-only fix: int temp for the c-0x273 subtract (baseline body) ───────
exp.add("ret-int-tmp", """
unsigned int DecodeChar(void)
{
    unsigned short c;
    int r;
    c = ((unsigned short *)son)[0x272];
    while (c < 0x273) {
        c += (unsigned short)GetBit();
        c = ((unsigned short *)son)[c];
    }
    r = c - 0x273;
    update((short)r);
    return r;
}
""", note="int r = c - 0x273; update(r); return r")

exp.add("ret-sub-in-c-int", """
unsigned int DecodeChar(void)
{
    unsigned short c;
    c = ((unsigned short *)son)[0x272];
    while (c < 0x273) {
        c += (unsigned short)GetBit();
        c = ((unsigned short *)son)[c];
    }
    {
        int r = (int)c - 0x273;
        update((short)r);
        return (unsigned int)r;
    }
}
""", note="(int)c - 0x273 temp, return (uint)r")

# ── operand-order flips: son[c] ≡ c[son] (Rule 4 — source operand order
# may change which address operand is allocated a register first). ───────────
exp.add("idx-swap-cson", """
unsigned int DecodeChar(void)
{
    unsigned short c;
    c = ((unsigned short *)son)[0x272];
    while (c < 0x273) {
        c += (unsigned short)GetBit();
        c = c[(unsigned short *)son];
    }
    c -= 0x273;
    update((short)c);
    return (unsigned int)c;
}
""", note="c = c[(unsigned short*)son]  (operand swap)")

exp.add("idx-swap-init-too", """
unsigned int DecodeChar(void)
{
    unsigned short c;
    c = 0x272[(unsigned short *)son];
    while (c < 0x273) {
        c += (unsigned short)GetBit();
        c = c[(unsigned short *)son];
    }
    c -= 0x273;
    update((short)c);
    return (unsigned int)c;
}
""", note="both indexes swapped")

exp.add("idx-ptr-add-swap", """
unsigned int DecodeChar(void)
{
    unsigned short c;
    c = ((unsigned short *)son)[0x272];
    while (c < 0x273) {
        c += (unsigned short)GetBit();
        c = *(c + (unsigned short *)son);
    }
    c -= 0x273;
    update((short)c);
    return (unsigned int)c;
}
""", note="*(c + (ushort*)son)  (index first in add)")

# ── SYNTHESIS: int c (clean edx home + clean return), zero-extend forced
# at the compare via (unsigned short)c, in-place `and` forced at the index
# via c & 0xffff.  Aims to combine all three PS forms at once. ───────────────
exp.add("synth-int-uscmp-idxand", """
unsigned int DecodeChar(void)
{
    int c;
    c = ((unsigned short *)son)[0x272];
    while ((unsigned short)c < 0x273) {
        c += GetBit();
        c = ((unsigned short *)son)[c & 0xffff];
    }
    c -= 0x273;
    update((short)c);
    return c;
}
""", note="int c, (ushort)c compare + c&0xffff index")

exp.add("synth-int-uscmp-idxand-rt", """
int DecodeChar(void)
{
    int c;
    c = ((unsigned short *)son)[0x272];
    while ((unsigned short)c < 0x273) {
        c += GetBit();
        c = ((unsigned short *)son)[c & 0xffff];
    }
    c -= 0x273;
    update((short)c);
    return c;
}
""", note="int return + int c + (ushort)c cmp + c&0xffff idx")

exp.add("synth-uscmp-noidxand", """
unsigned int DecodeChar(void)
{
    int c;
    c = ((unsigned short *)son)[0x272];
    while ((unsigned short)c < 0x273) {
        c += GetBit();
        c = ((unsigned short *)son)[(unsigned short)c];
    }
    c -= 0x273;
    update((short)c);
    return c;
}
""", note="int c, (ushort)c compare + (ushort)c index")

# ── round N: force son's load to precede / outrank the index CONV ────────────
def _mk(body_loop, note, c_decl="unsigned short c", ret="return (unsigned int)c;",
        init="c = ((unsigned short *)son)[0x272];"):
    return exp.add(note.split(":")[0], """
unsigned int DecodeChar(void)
{
    %s;
    %s
    while (c < 0x273) {
%s
    }
    c -= 0x273;
    update((short)c);
    %s
}
""" % (c_decl, init, body_loop, ret), note=note)

_mk("        { int b = GetBit(); c += b; c = ((unsigned short *)son)[c]; }",
    "bit-temp: int b=GetBit(); c+=b")
_mk("        c += (unsigned short)GetBit();\n        c = ((unsigned short *)son)[(int)c];",
    "idx-intcast: son[(int)c]")
_mk("        c += (unsigned short)GetBit();\n        c = ((unsigned short *)son)[(unsigned)c];",
    "idx-uintcast: son[(unsigned)c]")
_mk("        unsigned short *p;\n        c += (unsigned short)GetBit();\n        p = (unsigned short *)son + c;\n        c = *p;",
    "ptr-var: p = son + c; c = *p")
_mk("        c += (unsigned short)GetBit();\n        c = *(unsigned short *)(son + c);",
    "ptr-son-add: *(ushort*)(son + c)")

_mk("        unsigned short *p;\n        c += (unsigned short)GetBit();\n        p = (unsigned short *)son;\n        c = p[c];",
    "son-after-getbit: p=son after add, c=p[c]")

_mk("        int idx;\n        c += (unsigned short)GetBit();\n        idx = c;\n        c = ((unsigned short *)son)[idx];",
    "idx-then-son: idx=c (mask early); son[idx]")
_mk("        unsigned short *p;\n        int idx;\n        c += (unsigned short)GetBit();\n        idx = c;\n        p = (unsigned short *)son;\n        c = p[idx];",
    "idxmask-then-p: idx=c; p=son; p[idx]")

_mk("        int idx;\n        c += (unsigned short)GetBit();\n        idx = c & 0xffff;\n        c = ((unsigned short *)son)[idx];",
    "intidx-mask: int idx = c&0xffff; son[idx]")
_mk("        unsigned short *p;\n        c += (unsigned short)GetBit();\n        c &= 0xffff;\n        p = (unsigned short *)son;\n        c = p[c];",
    "us-maskstmt-p: c&=0xffff; p=son; p[c]")
