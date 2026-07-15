"""Integration tests for rule_hints detectors driven by real Watcom output.

The synthetic tests in ``tests/test_rule_hints.py`` feed hand-crafted
``InsnT`` tuples through each detector.  These integration tests
instead:

  1. Compile a known *wrong-C-form* and *right-C-form* via the oracle.
  2. Run a difflib-style alignment on the masked bytes (the same way
     ``decomp_verify._render_diff`` builds its diff rows).
  3. Feed the resulting (PS-side, recomp-side) row pairs to
     ``detect_hints``.
  4. Assert the detector fires the expected rule on at least one
     diff row, and does NOT fire on any equal row.

Because the inputs are real Watcom 10.0a output, this catches drift
between the *verified* rule mechanism (covered by per-rule oracle
tests) and the *detector heuristics* in ``rule_hints.py``.

For each rule we keep a minimal pair: the C form that produces the
PS-shape and the C form that produces the recomp-shape.  Helpers
mirror the diff-row construction used by the verifier, so the
detectors see exactly what they would see in production.
"""

from __future__ import annotations

import difflib
from typing import Iterable, Optional

import pytest

from c2.commands.oracle import compile_snippet, Function, Insn
from c2.commands.rule_hints import (
    RuleHint,
    detect_hints,
    histogram,
)


# ── Helpers ────────────────────────────────────────────────────────────────────

InsnTuple = tuple[int, int, bytes, str]


def _to_insn_tuple(i: Insn) -> InsnTuple:
    """Mirror the (rel_off, size, raw, "mn op_str") shape used by
    decomp_verify._render_diff."""
    asm = i.mnemonic if not i.op_str else f"{i.mnemonic} {i.op_str}"
    return (i.rel_off, len(i.raw), bytes(i.raw), asm.strip())


def _masked(i: Insn, fixups: set[int], base: int) -> bytes:
    """Mask both fixup bytes and relative call/jmp displacement bytes."""
    raw = bytes(i.raw)
    abs_off = base + i.rel_off

    # Fixup mask
    out = bytearray()
    for k, b in enumerate(raw):
        if (abs_off + k) in fixups:
            out.append(0)
        else:
            out.append(b)

    # Mask the displacement bytes of relative calls/jmps to avoid
    # link-position noise.  Same heuristic as
    # decomp_verify._rel_call_jmp_disp_mask:
    #   E8/E9 + 4-byte rel32 -> mask bytes [1..5)
    #   EB    + 1-byte rel8  -> mask byte  [1..2)
    #   72..7F + 1-byte rel8 -> mask byte  [1..2)
    #   0F 80..8F + 4-byte rel32 -> mask bytes [2..6)
    if raw:
        op = raw[0]
        if op in (0xE8, 0xE9) and len(raw) >= 5:
            for k in range(1, 5):
                out[k] = 0
        elif op == 0xEB and len(raw) >= 2:
            out[1] = 0
        elif 0x70 <= op <= 0x7F and len(raw) >= 2:
            out[1] = 0
        elif op == 0x0F and len(raw) >= 6 and 0x80 <= raw[1] <= 0x8F:
            for k in range(2, 6):
                out[k] = 0
    return bytes(out)


def _build_diff_rows(
    ps: Function,
    recomp: Function,
) -> list[tuple[Optional[InsnTuple], Optional[InsnTuple], bool]]:
    """Mirror decomp_verify._render_diff's row construction.

    Returns a list of (ps, recomp, is_diff) triples.
    """
    ps_keys = [_masked(i, ps.fixups, ps.base) for i in ps.insns]
    rc_keys = [_masked(i, recomp.fixups, recomp.base) for i in recomp.insns]

    matcher = difflib.SequenceMatcher(a=ps_keys, b=rc_keys, autojunk=False)
    rows: list[tuple[Optional[InsnTuple], Optional[InsnTuple], bool]] = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            for k in range(i2 - i1):
                rows.append(
                    (_to_insn_tuple(ps.insns[i1 + k]),
                     _to_insn_tuple(recomp.insns[j1 + k]),
                     False)
                )
        elif tag == "replace":
            n = max(i2 - i1, j2 - j1)
            for k in range(n):
                ps_i = ps.insns[i1 + k] if (i1 + k) < i2 else None
                rc_i = recomp.insns[j1 + k] if (j1 + k) < j2 else None
                rows.append((
                    _to_insn_tuple(ps_i) if ps_i else None,
                    _to_insn_tuple(rc_i) if rc_i else None,
                    True,
                ))
        elif tag == "delete":
            for k in range(i1, i2):
                rows.append(
                    (_to_insn_tuple(ps.insns[k]), None, True)
                )
        elif tag == "insert":
            for k in range(j1, j2):
                rows.append(
                    (None, _to_insn_tuple(recomp.insns[k]), True)
                )
    return rows


def _run_detectors(
    ps: Function,
    recomp: Function,
) -> tuple[list[Optional[RuleHint]], dict[str, int]]:
    rows = _build_diff_rows(ps, recomp)
    hints = detect_hints(
        rows,
        ps.base,
        recomp.base,
        ps.fixups,
        recomp.fixups,
    )
    return hints, histogram(hints)


def _assert_fires(hist: dict[str, int], rule: str, name: str) -> None:
    assert hist.get(rule, 0) >= 1, (
        f"expected {rule} hint to fire on {name}; got histogram={hist}"
    )


def _assert_no_false_positives_on_equal_rows(
    rows: list, hints: list
) -> None:
    """detect_hints should never return a hint for an equal row."""
    for (_, _, is_diff), h in zip(rows, hints):
        if not is_diff:
            assert h is None, f"hint on equal row: {h}"


# ── Rule 4 — operand order in cmp ────────────────────────────────────────────

def test_rule_4_fires_on_real_codegen(watcom_10_0a):
    """`if (a < b)` (PS) vs `if (b > a)` (recomp) must fire Rule 4.

    Use parm-resident operands - global-resident operands collapse
    via load reordering and don’t emit the cmp-operand swap.
    """
    ps_src = """\
extern int dst1, dst2;
void f(int a, int b) { if (a < b) dst1 = 1; else dst2 = 1; }
"""
    rc_src = """\
extern int dst1, dst2;
void f(int a, int b) { if (b > a) dst1 = 1; else dst2 = 1; }
"""
    ps = compile_snippet(ps_src,
                         extern_defs="int dst1, dst2;\n").function("f")
    rc = compile_snippet(rc_src,
                         extern_defs="int dst1, dst2;\n").function("f")
    rows = _build_diff_rows(ps, rc)
    hints = detect_hints(rows, ps.base, rc.base, ps.fixups, rc.fixups)
    hist = histogram(hints)
    _assert_fires(hist, "Rule 4", "a<b vs b>a")
    _assert_no_false_positives_on_equal_rows(rows, hints)


# ── Rule 5 — signed pow2 divide idiom ────────────────────────────────────────

def test_rule_5_fires_when_recomp_uses_ternary_bias(watcom_10_0a):
    """PS uses `x / 8` (sar/shl/sbb), recomp uses ternary bias.

    The detector keys on the unique `sar reg, 31` fingerprint.
    """
    ps_src = """\
extern int x, dst;
void f(void) { dst = x / 8; }
"""
    rc_src = """\
extern int x, dst;
void f(void) { dst = (x < 0 ? x + 7 : x) >> 3; }
"""
    ps = compile_snippet(ps_src, extern_defs="int x, dst;\n").function("f")
    rc = compile_snippet(rc_src, extern_defs="int x, dst;\n").function("f")
    rows = _build_diff_rows(ps, rc)
    hints = detect_hints(rows, ps.base, rc.base, ps.fixups, rc.fixups)
    hist = histogram(hints)
    _assert_fires(hist, "Rule 5", "/8 vs ternary bias")
    _assert_no_false_positives_on_equal_rows(rows, hints)


# ── Rule 8 — char unsigned default vs signed-char movsx ──────────────────────

def test_rule_8_fires_on_signed_vs_unsigned_char_global(watcom_10_0a):
    """Pattern C: PS `signed char g` (movsx); recomp `char g`
    (xor reg, reg + mov reg8, byte ptr).

    This is the standard Watcom 10.0a unsigned-byte-load idiom for
    a global — NOT the `mov reg8, [m]; and reg, 0xff` shape (that
    one applies to indexed/struct-field reads).
    """
    ps_src = """\
extern signed char g;
extern int dst;
void f(void) { dst = g; }
"""
    rc_src = """\
extern char g;
extern int dst;
void f(void) { dst = g; }
"""
    ps = compile_snippet(ps_src,
                         extern_defs="signed char g; int dst;\n").function("f")
    rc = compile_snippet(rc_src,
                         extern_defs="char g; int dst;\n").function("f")
    rows = _build_diff_rows(ps, rc)
    hints = detect_hints(rows, ps.base, rc.base, ps.fixups, rc.fixups)
    hist = histogram(hints)
    _assert_fires(hist, "Rule 8/23", "signed-char read vs xor+mov al")
    _assert_no_false_positives_on_equal_rows(rows, hints)


def test_rule_8_fires_on_struct_field_read(watcom_10_0a):
    """Pattern A: indexed struct-field read - PS uses `movsx reg32,
    byte ptr [...]` and recomp uses `mov reg8, [...]; and reg32,
    0xff`.

    This is the original Pattern A in the detector.
    """
    ps_src = """\
struct s { int a; signed char b; };
extern struct s arr[64];
int f(int i) { return arr[i].b; }
"""
    rc_src = """\
struct s { int a; char b; };
extern struct s arr[64];
int f(int i) { return arr[i].b; }
"""
    ps = compile_snippet(
        ps_src,
        extern_defs="struct s { int a; signed char b; }; struct s arr[64];\n"
    ).function("f")
    rc = compile_snippet(
        rc_src,
        extern_defs="struct s { int a; char b; }; struct s arr[64];\n"
    ).function("f")
    rows = _build_diff_rows(ps, rc)
    hints = detect_hints(rows, ps.base, rc.base, ps.fixups, rc.fixups)
    hist = histogram(hints)
    _assert_fires(hist, "Rule 8/23", "struct-field signed vs unsigned")
    _assert_no_false_positives_on_equal_rows(rows, hints)


# ── Rule 9 — `if (cond == 0)` else-first layout ──────────────────────────────

def test_rule_9_fires_on_test_reg_je_vs_test_reg_jne(watcom_10_0a):
    """Register-resident operand: PS `test eax, eax; je` vs recomp
    `test eax, eax; jne`.
    """
    DEFS = "int x, y; void X(void){} void Y(void){}\n"
    ps_src = """\
extern int x, y;
extern void X(void);
extern void Y(void);
int f(int p) { x = p; if (p != 0) X(); else Y(); return y; }
"""
    rc_src = """\
extern int x, y;
extern void X(void);
extern void Y(void);
int f(int p) { x = p; if (p == 0) Y(); else X(); return y; }
"""
    ps = compile_snippet(ps_src, extern_defs=DEFS).function("f")
    rc = compile_snippet(rc_src, extern_defs=DEFS).function("f")
    rows = _build_diff_rows(ps, rc)
    hints = detect_hints(rows, ps.base, rc.base, ps.fixups, rc.fixups)
    hist = histogram(hints)
    _assert_fires(hist, "Rule 9", "test+je vs test+jne (reg-resident)")
    _assert_no_false_positives_on_equal_rows(rows, hints)


def test_rule_9_fires_on_cmp_mem_je_vs_cmp_mem_jne(watcom_10_0a):
    """Memory-resident operand: PS `cmp [m], 0; je` vs recomp
    `cmp [m], 0; jne`.  The detector must handle this shape too.
    """
    DEFS = "int x; void X(void){} void Y(void){}\n"
    ps_src = """\
extern int x;
extern void X(void);
extern void Y(void);
void f(void) { if (x != 0) X(); else Y(); }
"""
    rc_src = """\
extern int x;
extern void X(void);
extern void Y(void);
void f(void) { if (x == 0) Y(); else X(); }
"""
    ps = compile_snippet(ps_src, extern_defs=DEFS).function("f")
    rc = compile_snippet(rc_src, extern_defs=DEFS).function("f")
    rows = _build_diff_rows(ps, rc)
    hints = detect_hints(rows, ps.base, rc.base, ps.fixups, rc.fixups)
    hist = histogram(hints)
    _assert_fires(hist, "Rule 9", "cmp [m], 0 + je/jne")
    _assert_no_false_positives_on_equal_rows(rows, hints)


# ── Rule 12 — data-pointer literal vs integer ────────────────────────────────

def test_rule_12_fires_on_pointer_vs_integer_literal_via_call_arg(watcom_10_0a):
    """`mov reg, imm32` form: pass the literal as a call arg so
    Watcom emits B8+rd (mov r32, imm32) rather than folding into a
    `mov [m], imm32` instruction."""
    ps_src = """\
extern char buf[64];
extern void use(int);
void f(void) { use((int)buf); }
"""
    rc_src = """\
extern void use(int);
void f(void) { use(0x90100); }
"""
    ps = compile_snippet(
        ps_src,
        extern_defs="char buf[64]; void use(int x){(void)x;}\n"
    ).function("f")
    rc = compile_snippet(
        rc_src,
        extern_defs="void use(int x){(void)x;}\n"
    ).function("f")
    rows = _build_diff_rows(ps, rc)
    hints = detect_hints(rows, ps.base, rc.base, ps.fixups, rc.fixups)
    hist = histogram(hints)
    _assert_fires(hist, "Rule 12", "pointer fixup vs integer literal (call arg)")
    _assert_no_false_positives_on_equal_rows(rows, hints)


def test_rule_12_fires_on_mem_store_form(watcom_10_0a):
    """`mov dword ptr [m], imm32` form: storing a constant directly
    into a global.  Same fixup-vs-literal contrast in the imm bytes."""
    ps_src = """\
extern char buf[64];
extern int dst;
void f(void) { dst = (int)buf; }
"""
    rc_src = """\
extern int dst;
void f(void) { dst = 0x90100; }
"""
    ps = compile_snippet(
        ps_src,
        extern_defs="char buf[64]; int dst;\n"
    ).function("f")
    rc = compile_snippet(
        rc_src,
        extern_defs="int dst;\n"
    ).function("f")
    rows = _build_diff_rows(ps, rc)
    hints = detect_hints(rows, ps.base, rc.base, ps.fixups, rc.fixups)
    hist = histogram(hints)
    _assert_fires(hist, "Rule 12", "pointer fixup vs integer literal (mem store)")
    _assert_no_false_positives_on_equal_rows(rows, hints)


# ── Rule 14 — void return vs explicit return N ───────────────────────────────

def test_rule_14_fires_on_int_return_when_ps_is_void(watcom_10_0a):
    """PS is `void f(void) { ... }` (bare `ret`); recomp is
    `int f(void) { ...; return 0; }` (sets EAX before ret)."""
    ps_src = """\
extern int dst;
void f(void) { dst = 1; }
"""
    rc_src = """\
extern int dst;
int f(void) { dst = 1; return 0; }
"""
    ps = compile_snippet(ps_src, extern_defs="int dst;\n").function("f")
    rc = compile_snippet(rc_src, extern_defs="int dst;\n").function("f")
    rows = _build_diff_rows(ps, rc)
    hints = detect_hints(rows, ps.base, rc.base, ps.fixups, rc.fixups)
    hist = histogram(hints)
    _assert_fires(hist, "Rule 14", "int-return vs void")
    _assert_no_false_positives_on_equal_rows(rows, hints)


# ── Rule 16 — short vs near jmp ──────────────────────────────────────────────

def test_rule_16_fires_on_short_vs_near_jmp_encoding(watcom_10_0a):
    """Construct two functions with the same jmp target but different
    distances so the encoding flips from EB (short) to E9 (near).

    Use external function calls in the loop body to prevent Watcom
    from collapsing the body via constant folding / strength reduction.
    """
    DEFS = "int arr[256]; void use(int x){(void)x;}\n"

    def body(n):
        return "".join(f"use(arr[{i}]);\n" for i in range(n))

    short_src = f"""\
extern int arr[256];
extern void use(int);
void f(int n) {{
    while (n--) {{
        {body(8)}
    }}
}}
"""
    long_src = f"""\
extern int arr[256];
extern void use(int);
void f(int n) {{
    while (n--) {{
        {body(60)}
    }}
}}
"""
    ps = compile_snippet(short_src, extern_defs=DEFS).function("f")
    rc = compile_snippet(long_src, extern_defs=DEFS).function("f")
    from c2.commands.rule_hints import detect_rule_16
    ps_jmps = [i for i in ps.insns if i.mnemonic == "jmp"]
    rc_jmps = [i for i in rc.insns if i.mnemonic == "jmp"]
    assert ps_jmps, ps.disasm_text()
    assert rc_jmps, rc.disasm_text()
    assert ps_jmps[0].raw[0] == 0xEB, ps.disasm_text()
    assert rc_jmps[0].raw[0] == 0xE9, rc.disasm_text()
    h = detect_rule_16(_to_insn_tuple(ps_jmps[0]), _to_insn_tuple(rc_jmps[0]))
    assert h is not None and h.rule == "Rule 16"


# ── Rule 17 — flag-mask split-RMW ────────────────────────────────────────────

def test_rule_17_fires_on_split_rmw_flag_field(watcom_10_0a):
    """PS splits `x = (x & MASK) | BIT;` into `x &= MASK; x |= BIT;`
    (forces the extra reg-copy temp); recomp keeps the combined form.
    """
    ps_src = """\
extern unsigned char flags;
void f(void) {
    flags &= 0xfe;
    flags |= 0x01;
}
"""
    rc_src = """\
extern unsigned char flags;
void f(void) {
    flags = (flags & 0xfe) | 0x01;
}
"""
    ps = compile_snippet(ps_src,
                         extern_defs="unsigned char flags;\n").function("f")
    rc = compile_snippet(rc_src,
                         extern_defs="unsigned char flags;\n").function("f")
    rows = _build_diff_rows(ps, rc)
    hints = detect_hints(rows, ps.base, rc.base, ps.fixups, rc.fixups)
    hist = histogram(hints)
    _assert_fires(hist, "Rule 17", "split-RMW vs combined")
    _assert_no_false_positives_on_equal_rows(rows, hints)


# ── Rule 19 — dword vs byte spill ────────────────────────────────────────────

def test_rule_19_fires_on_dword_vs_byte_param_spill(watcom_10_0a):
    """A function with `(int p, int q)` parms uses dword spills; same
    function with `(int p, char q)` uses a byte spill at the same site
    when the second arg is stored into a stack slot.

    NOTE: Under our verifier flag set (`-bt=dos -mf -4r -s`) Watcom 10.0a
    almost always finds room for parameters in callee-save registers
    (EBX/ESI/EDI/EBP) and avoids the `mov [esp+N], reg` write site that
    Rule 19's detector keys on.  A real PS.EXE function like
    `create_unit` does emit the relevant `push eax`/`mov bl, [esp]`
    pattern, but reproducing that shape from a synthetic snippet is
    fragile.  This test stays conservative: if neither build spills,
    we skip rather than asserting on absent behavior.

    See `tests/oracle/test_rule_08_char_unsigned_default.py::
    test_char_int_two_param_spill_distinguishes_widths` for direct
    coverage of the spill-width discrimination via the oracle.
    """
    ps_src = """\
extern int a, b;
void f(int p, int q) {
    a = p + q;
    b = p - q;
}
"""
    rc_src = """\
extern int a, b;
void f(int p, char q) {
    a = p + q;
    b = p - q;
}
"""
    ps = compile_snippet(ps_src, extern_defs="int a, b;\n").function("f")
    rc = compile_snippet(rc_src, extern_defs="int a, b;\n").function("f")
    # Look specifically for parameter-write spills (`mov [esp+N], reg`),
    # not loads — the detector keys on opcodes 0x88/0x89.
    def _has_param_spill_write(fn):
        for i in fn.insns:
            if i.mnemonic == "mov" and (
                i.op_str.startswith("dword ptr [esp")
                or i.op_str.startswith("byte ptr [esp")
            ):
                return True
        return False
    if not (_has_param_spill_write(ps) and _has_param_spill_write(rc)):
        pytest.skip(
            "Watcom kept parameters in callee-save regs; no `mov [esp+N], "
            "reg` site to compare.  Rule 19 detector targets the write "
            "form; this synthetic snippet doesn't trigger it.  See "
            "tests/oracle/test_rule_08_char_unsigned_default.py for "
            "direct coverage of the byte-vs-dword spill discrimination."
        )
    rows = _build_diff_rows(ps, rc)
    hints = detect_hints(rows, ps.base, rc.base, ps.fixups, rc.fixups)
    hist = histogram(hints)
    _assert_fires(hist, "Rule 19", "dword vs byte spill")


# ── Rule 24a — spill swap ────────────────────────────────────────────────────

def test_rule_24a_fires_on_named_local_spill_swap(watcom_10_0a):
    """Same function with and without the named-local Rule 24a fix.
    The two should differ in which arg is spilled to a stack slot."""
    DEFS = (
        "struct REGS_w { short ax, bx, cx, dx, si, di, cflag, _pad; };\n"
        "union REGS { struct REGS_w w; };\n"
        "int int386(int n, union REGS *i, union REGS *o) "
        "{ (void)n; (void)i; (void)o; return 0; }\n"
    )
    ps_src = """\
struct REGS_w { short ax, bx, cx, dx, si, di, cflag, _pad; };
union REGS { struct REGS_w w; };
extern int int386(int n, union REGS *i, union REGS *o);
extern void *memset(void *s, int c, unsigned int n);
void mouserange(int xmin, int ymin, int xmax, int ymax) {
    union REGS r;
    int hi_x = xmax;            /* Rule 24a fix */
    memset(&r, 0, 0x1c);
    r.w.ax = 7;
    r.w.cx = (short)xmin;
    r.w.dx = (short)hi_x;
    int386(0x33, &r, &r);
    r.w.ax = 8;
    r.w.cx = (short)ymin;
    r.w.dx = (short)ymax;
    int386(0x33, &r, &r);
}
"""
    rc_src = """\
struct REGS_w { short ax, bx, cx, dx, si, di, cflag, _pad; };
union REGS { struct REGS_w w; };
extern int int386(int n, union REGS *i, union REGS *o);
extern void *memset(void *s, int c, unsigned int n);
void mouserange(int xmin, int ymin, int xmax, int ymax) {
    union REGS r;
    memset(&r, 0, 0x1c);
    r.w.ax = 7;
    r.w.cx = (short)xmin;
    r.w.dx = (short)xmax;
    int386(0x33, &r, &r);
    r.w.ax = 8;
    r.w.cx = (short)ymin;
    r.w.dx = (short)ymax;
    int386(0x33, &r, &r);
}
"""
    ps = compile_snippet(ps_src, extern_defs=DEFS,
                         need_clib3r=True).function("mouserange")
    rc = compile_snippet(rc_src, extern_defs=DEFS,
                         need_clib3r=True).function("mouserange")
    rows = _build_diff_rows(ps, rc)
    hints = detect_hints(rows, ps.base, rc.base, ps.fixups, rc.fixups)
    hist = histogram(hints)
    _assert_fires(hist, "Rule 24a", "named-local spill swap")


# ── Rule 24b — shift-in-place vs shift-copy ──────────────────────────────────

def test_rule_24b_fires_on_shift_in_place_vs_shift_copy(watcom_10_0a):
    DEFS = (
        "struct REGS_w { short ax, bx, cx, dx, si, di, cflag, _pad; };\n"
        "union REGS { struct REGS_w w; };\n"
        "int int386(int n, union REGS *i, union REGS *o) "
        "{ (void)n; (void)i; (void)o; return 0; }\n"
    )
    ps_src = """\
struct REGS_w { short ax, bx, cx, dx, si, di, cflag, _pad; };
union REGS { struct REGS_w w; };
extern int int386(int n, union REGS *i, union REGS *o);
int lock_region(unsigned int addr, unsigned int size) {
    union REGS r;
    unsigned int hi;        /* Rule 24b fix */
    r.w.ax = 0x600;
    hi = addr >> 16;
    r.w.bx = (short)hi;
    r.w.cx = (short)addr;
    hi = size >> 16;
    r.w.si = (short)hi;
    r.w.di = (short)size;
    int386(0x31, &r, &r);
    return r.w.cflag == 0;
}
"""
    rc_src = """\
struct REGS_w { short ax, bx, cx, dx, si, di, cflag, _pad; };
union REGS { struct REGS_w w; };
extern int int386(int n, union REGS *i, union REGS *o);
int lock_region(unsigned int addr, unsigned int size) {
    union REGS r;
    r.w.ax = 0x600;
    r.w.bx = (short)(addr >> 16);
    r.w.cx = (short)addr;
    r.w.si = (short)(size >> 16);
    r.w.di = (short)size;
    int386(0x31, &r, &r);
    return r.w.cflag == 0;
}
"""
    ps = compile_snippet(ps_src, extern_defs=DEFS,
                         need_clib3r=True).function("lock_region")
    rc = compile_snippet(rc_src, extern_defs=DEFS,
                         need_clib3r=True).function("lock_region")
    rows = _build_diff_rows(ps, rc)
    hints = detect_hints(rows, ps.base, rc.base, ps.fixups, rc.fixups)
    hist = histogram(hints)
    _assert_fires(hist, "Rule 24b", "shift-in-place vs shift-copy")


# ── Rule 26 — sete-fold of boolean call argument ─────────────────────────────

def test_rule_26_fires_on_ternary_vs_explicit_branch(watcom_10_0a):
    """PS uses if/else with two calls; recomp uses ternary inside one
    call, materialising the boolean via `sete`."""
    DEFS = (
        "int g;\n"
        "void X(int i, int hi) { (void)i; (void)hi; }\n"
    )
    ps_src = """\
extern int g;
extern void X(int i, int hi);
void f(void) {
    int i;
    for (i = 0; i < 12; i++) {
        if (i == g) X(i, 1);
        else        X(i, 0);
    }
}
"""
    rc_src = """\
extern int g;
extern void X(int i, int hi);
void f(void) {
    int i;
    for (i = 0; i < 12; i++) {
        X(i, i == g ? 1 : 0);
    }
}
"""
    ps = compile_snippet(ps_src, extern_defs=DEFS).function("f")
    rc = compile_snippet(rc_src, extern_defs=DEFS).function("f")
    rows = _build_diff_rows(ps, rc)
    hints = detect_hints(rows, ps.base, rc.base, ps.fixups, rc.fixups)
    hist = histogram(hints)
    _assert_fires(hist, "Rule 26", "ternary vs explicit branch")
    _assert_no_false_positives_on_equal_rows(rows, hints)


# ── Rule 28 — whole-function callee-save register swap ──────────────────────
#
# No oracle-based integration test for Rule 28: there is no known
# C-level lever that flips Watcom's choice of ESI vs EDI for a
# long-lived 32-bit local under the verifier flag set.  The default
# allocator picks ESI per `Reg64Order[]` (`bld/cg/intel/386/c/386rgtbl.c`)
# and the GivenRegisters tie-breaker keeps every subsequent local on
# ESI.  PS.EXE's EDI choice comes from a higher CountRegMoves savings
# count for EDI in PS's source, which we cannot reproduce in two
# variants of the same function.
#
# The detector is exhaustively covered by
# ``tests/oracle/test_rule_28_callee_save_swap.py`` (24 unit tests
# with hand-built InsnT tuples) and is exercised end-to-end against
# PS.EXE itself (`new_name_game_loop`, `battle_game_loop`,
# `check_for_promotion`, etc.) — those are real-world acceptance
# tests rather than CI-runnable.


# ── Negative test — matched code emits no hints ──────────────────────────────

def test_no_hints_on_byte_identical_code(watcom_10_0a):
    """Compiling the same source twice yields zero diff rows and zero
    hints."""
    src = """\
extern int x, y, dst;
void f(void) { dst = x + y; }
"""
    ps = compile_snippet(src, extern_defs="int x, y, dst;\n").function("f")
    rc = compile_snippet(src, extern_defs="int x, y, dst;\n").function("f")
    rows = _build_diff_rows(ps, rc)
    n_diff = sum(1 for _, _, d in rows if d)
    assert n_diff == 0, "expected zero diff rows for identical sources"
    hints = detect_hints(rows, ps.base, rc.base, ps.fixups, rc.fixups)
    hist = histogram(hints)
    assert hist == {}, f"expected no hints; got {hist}"
