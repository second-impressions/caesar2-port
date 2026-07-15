"""Static rule-hint detection for decomp-verify diff output.

Each detector inspects a pair of (PS.EXE, recomp) instructions plus a
small surrounding window and returns a `RuleHint` if the diff matches
a documented Watcom 10.0a codegen rule from
``docs/watcom-codegen-patterns.md``.

The point is to short-circuit LLM reasoning for byte diffs that have a
known, mechanical explanation: when the verifier prints
``→ Rule 16 (short-vs-near jmp encoding cascade)`` next to a diff line,
the agent can look up the rule and apply the documented fix instead of
re-deriving it.

Only **high-confidence** rules live here - patterns that are unambiguous
from byte / instruction shape alone, with low false-positive risk.
Medium-confidence rules (Rule 5, 9, 15, 17, 20, 22) are deferred to a
v2 once the v1 hints have been validated in practice.

Each detector returns ``None`` if the rule does not apply.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

# Capstone instruction tuple shape used by decomp_verify._render_diff:
#   (rel_addr, size, raw_bytes, "mnemonic op_str")
InsnT = tuple[int, int, bytes, str]


@dataclass(frozen=True)
class RuleHint:
    """A single rule hit on a diff row."""
    rule: str            # Short label, e.g. "Rule 16"
    summary: str         # One-line description of what's mismatching
    fix: str             # One-line suggested source-level remedy

    def render(self) -> str:
        return f"→ {self.rule} ({self.summary})"


# ── Helpers ────────────────────────────────────────────────────────────────────

def _mnemonic(insn: InsnT | None) -> str:
    """Return the bare mnemonic of an instruction, or empty string."""
    if insn is None:
        return ""
    asm = insn[3]
    return asm.split(None, 1)[0] if asm else ""


def _operands(insn: InsnT | None) -> str:
    """Return the operand string of an instruction, or empty string."""
    if insn is None:
        return ""
    asm = insn[3]
    parts = asm.split(None, 1)
    return parts[1] if len(parts) > 1 else ""


_BYTE_REGS = {"al", "bl", "cl", "dl", "ah", "bh", "ch", "dh"}
_WORD_REGS = {"ax", "bx", "cx", "dx", "si", "di", "bp", "sp"}


def _cmp_operand_width(insn: InsnT | None) -> Optional[str]:
    """Width of a ``cmp``'s first operand: 'byte' | 'word' | 'dword' | None.

    Empirically (docs/codegen-experiments enum probes) the *width* of the
    compare is what separates a byte-packed ``enum`` from an ``unsigned``
    int when the conditional jump is unsigned:

      * ``cmp al, K`` / ``cmp byte ptr [m], K``   → byte  (enum / unsigned char
        kept byte-wide)
      * ``cmp eax, K`` / ``cmp dword ptr [m], K`` → dword (unsigned int)

    Returns ``None`` when the instruction is not a ``cmp`` or the width is
    not determinable from the disassembly text.
    """
    if _mnemonic(insn) != "cmp":
        return None
    ops = _operands(insn)
    if not ops:
        return None
    first = ops.split(",", 1)[0].strip()
    if "byte ptr" in first:
        return "byte"
    if "word ptr" in first:
        return "word"
    if "dword ptr" in first:
        return "dword"
    reg = first.lstrip("[").split("+")[0].split("-")[0].strip().rstrip("]")
    if reg in _BYTE_REGS:
        return "byte"
    if reg in _WORD_REGS:
        return "word"
    if reg.startswith("e") and reg[1:] in _WORD_REGS:
        return "dword"
    return None


def _all_bytes_in_fixup(insn: InsnT, abs_base: int, fix: set[int],
                       offset: int = 0, length: int | None = None) -> bool:
    """Are bytes [offset, offset+length) of `insn` all in the fixup set?

    Defaults to checking all of insn's bytes.
    """
    rel_off, _size, raw, _asm = insn
    if length is None:
        length = len(raw) - offset
    return all(
        (abs_base + rel_off + i) in fix
        for i in range(offset, offset + length)
    )


def _none_in_fixup(insn: InsnT, abs_base: int, fix: set[int],
                   offset: int = 0, length: int | None = None) -> bool:
    """Are bytes [offset, offset+length) of `insn` NONE in the fixup set?"""
    rel_off, _size, raw, _asm = insn
    if length is None:
        length = len(raw) - offset
    return not any(
        (abs_base + rel_off + i) in fix
        for i in range(offset, offset + length)
    )


# ── Rule 4 - operand order in cmp ────────────────────────────────────────────

# Pairs of complementary Jcc mnemonics: PS uses left, recomp uses right
# (or vice versa) because the source author wrote `a > b` instead of
# `b < a` (or the other way round).
_JCC_FLIP: dict[str, str] = {
    "jl":  "jg",   "jg":  "jl",
    "jle": "jge",  "jge": "jle",
    "jb":  "ja",   "ja":  "jb",
    "jbe": "jae",  "jae": "jbe",
}

# Pairs of complementary equality jumps used by Rule 9 (operator-flip
# with operands UNCHANGED).  This is the same `_JCC_FLIP` set above
# plus the equality forms - any Jcc inversion where the cmp operands
# stay the same is Rule 9 territory; an operand-swap with this same
# Jcc inversion is Rule 4 (handled separately by detect_rule_4).
_JCC_EQ_FLIP: dict[str, str] = {
    "je": "jne", "jne": "je",
    "jz": "jnz", "jnz": "jz",
    "jl": "jge", "jge": "jl",
    "jle": "jg",  "jg":  "jle",
    "jb": "jae", "jae": "jb",
    "jbe": "ja",  "ja":  "jbe",
}


# ── Rule 90 - jcc signedness mismatch (enum / unsigned vs signed) ─────────────

# Same-direction ordered jumps that differ ONLY in signedness.  PS and
# recomp branch the same way (both "greater", both "less"), but one uses
# the signed form (jg/jl/jge/jle) and the other the unsigned form
# (ja/jb/jae/jbe).  That means the compared value's *promotion* differs:
# char/int promote signed (jg/jl); a byte-packed enum with all-non-neg
# enumerators (or an `unsigned` value) promotes unsigned (ja/jb).
_JCC_SIGNEDNESS: dict[str, str] = {
    "jg":  "ja",  "ja":  "jg",
    "jge": "jae", "jae": "jge",
    "jl":  "jb",  "jb":  "jl",
    "jle": "jbe", "jbe": "jle",
}
_SIGNED_JCC = {"jg", "jge", "jl", "jle"}


def detect_rule_90(
    ps: InsnT | None,
    recomp: InsnT | None,
    ps_prev: InsnT | None,
    recomp_prev: InsnT | None,
) -> Optional[RuleHint]:
    """Signedness mismatch on an ordered conditional jump (Rule 90).

    Fires when PS and recomp emit the SAME-direction ordered jump but
    one is signed (jg/jl/jge/jle) and the other unsigned (ja/jb/jae/jbe).
    The compared value's declared type drives the promotion signedness:

      * PS unsigned (ja/jb), recomp signed (jg/jl)  → the value should be
        UNSIGNED (declare `unsigned`, or a byte-packed `enum` if it is a
        small non-negative tag).  See Rule 90.
      * PS signed (jg/jl), recomp unsigned (ja/jb)  → the value should be
        SIGNED (`signed char` / `int`); a current `enum`/`unsigned` decl
        is wrong.

    This is distinct from Rule 4 (operand-order swap → *complementary*
    jcc jl↔jg) and Rule 9 (operator flip).  Here the branch DIRECTION is
    unchanged; only the signed/unsigned encoding differs.  To avoid
    overlapping with Rule 4, require the preceding cmp/test operands to
    match on both sides (no operand swap).
    """
    if ps is None or recomp is None:
        return None
    pm, rm = _mnemonic(ps), _mnemonic(recomp)
    if _JCC_SIGNEDNESS.get(pm) != rm:
        return None
    # Guard against Rule 4 overlap: if the preceding compares have *swapped*
    # operands (cmp A,B vs cmp B,A), that's operand-order (Rule 4), not a
    # signedness bug.  A mere width difference (cmp al,K vs cmp eax,K - the
    # enum-vs-int case) is NOT a swap and must NOT be deferred.
    if (_mnemonic(ps_prev) in ("cmp", "test")
            and _mnemonic(recomp_prev) in ("cmp", "test")):
        ps_ops = [o.strip() for o in _operands(ps_prev).split(",")]
        rc_ops = [o.strip() for o in _operands(recomp_prev).split(",")]
        if (len(ps_ops) == 2 and len(rc_ops) == 2
                and ps_ops[0] == rc_ops[1] and ps_ops[1] == rc_ops[0]
                and ps_ops[0] != ps_ops[1]):
            # genuine operand swap → Rule 4 territory; defer.
            return None
    ps_signed = pm in _SIGNED_JCC
    ps_width = _cmp_operand_width(ps_prev)
    if ps_signed:
        fix = ("PS promotes SIGNED (char/int); recomp emitted an unsigned "
               "branch - a current `enum`/`unsigned` decl is wrong. Declare "
               "the compared value `signed char` / `int`.")
        summary = f"PS signed {pm}, recomp unsigned {rm} (value is char/int)"
    else:
        # PS is unsigned.  The PS compare WIDTH disambiguates the unsigned
        # source type (enum probes, docs/codegen-experiments):
        #   byte  cmp + unsigned jcc  → byte-packed `enum` (all-non-neg) or
        #                               an `unsigned char` kept byte-wide.
        #   dword cmp + unsigned jcc  → `unsigned int` / `unsigned`.
        if ps_width == "byte":
            fix = ("PS does a BYTE compare + unsigned branch - the value is a "
                   "byte-packed `enum` (all-non-neg enumerators) or an "
                   "`unsigned char` kept byte-wide.  Recomp widened it to a "
                   "signed int compare: retype the value to a byte `enum` "
                   "(or keep it `unsigned char` used only byte-wide). Rule 90.")
            summary = (f"PS unsigned BYTE {pm}, recomp signed {rm} "
                       f"(value is a byte enum / unsigned char)")
        elif ps_width == "dword":
            fix = ("PS does a DWORD compare + unsigned branch - the value is "
                   "`unsigned int` / `unsigned`.  Declare it unsigned. Rule 90.")
            summary = (f"PS unsigned DWORD {pm}, recomp signed {rm} "
                       f"(value is unsigned int)")
        else:
            fix = ("PS promotes UNSIGNED; recomp emitted a signed branch. Make "
                   "the compared value `unsigned` - or, if it is a small "
                   "non-negative tag, a byte-packed `enum` (Rule 90).")
            summary = f"PS unsigned {pm}, recomp signed {rm} (value is unsigned/enum)"
    return RuleHint(rule="Rule 90", summary=summary, fix=fix)


def detect_rule_4(
    ps: InsnT | None,
    recomp: InsnT | None,
    ps_prev: InsnT | None,
    recomp_prev: InsnT | None,
) -> Optional[RuleHint]:
    """Operand-order swap in cmp + complementary Jcc.

    Triggers when the diff row is a Jcc whose previous instruction was
    a cmp on both sides, the cmp operands are swapped, and the Jcc
    mnemonics are complementary (jle↔jge, jl↔jg, ...).
    """
    if ps is None or recomp is None:
        return None
    ps_mn, rc_mn = _mnemonic(ps), _mnemonic(recomp)
    if ps_mn not in _JCC_FLIP or _JCC_FLIP[ps_mn] != rc_mn:
        return None
    # Need a preceding cmp on both sides
    if _mnemonic(ps_prev) != "cmp" or _mnemonic(recomp_prev) != "cmp":
        return None
    ps_ops = _operands(ps_prev).split(",")
    rc_ops = _operands(recomp_prev).split(",")
    if len(ps_ops) != 2 or len(rc_ops) != 2:
        return None
    a, b = ps_ops[0].strip(), ps_ops[1].strip()
    c, d = rc_ops[0].strip(), rc_ops[1].strip()
    if a == d and b == c:
        return RuleHint(
            rule="Rule 4",
            summary=f"cmp operands swapped ({ps_mn}↔{rc_mn})",
            fix="reverse the comparison in the source: write `a < b`, "
                "not `b > a` (Watcom preserves source operand order).",
        )
    return None


# ── Rule 4b - comparison boundary inclusive/exclusive form ────────────────────

# Inclusive <-> exclusive Jcc complements (SAME direction, boundary shifts by
# one).  `x > N`  -> `cmp N;  jle`(skip) ;  `x >= N+1` -> `cmp N+1; jl`(skip).
# `x < N`  -> `cmp N;  jge`(skip) ;  `x <= N-1` -> `cmp N-1; jg`(skip).
_JCC_BOUNDARY: dict[str, str] = {
    "jle": "jl",  "jl": "jle",
    "jge": "jg",  "jg": "jge",
    "jbe": "jb",  "jb": "jbe",
    "jae": "ja",  "ja": "jae",
}


def _parse_imm(tok: str) -> Optional[int]:
    """Parse a trailing immediate operand ('0x82' / '5' / '-1') to int."""
    tok = tok.strip()
    try:
        return int(tok, 16) if tok.lower().startswith(("0x", "-0x")) else int(tok)
    except ValueError:
        return None


def detect_rule_4b(
    ps: InsnT | None,
    recomp: InsnT | None,
    next_ps: InsnT | None,
    next_recomp: InsnT | None,
) -> Optional[RuleHint]:
    """Comparison boundary written in the equivalent-but-wrong form.

    Fires when an *aligned* diff row is a ``cmp R, imm`` on both sides with
    the SAME first operand but immediates differing by exactly one, AND the
    following Jcc is the inclusive/exclusive complement (``jle``\u2194``jl``,
    ``jge``\u2194``jg``, unsigned forms too).  That is the signature of source
    written ``x > N`` where PS used ``x >= N+1`` (or ``< N`` vs ``<= N-1``):
    semantically identical, different bytes (immediate + Jcc opcode).

    Requiring the Jcc complement on the NEXT row rejects the desync
    artefact where the aligner pairs two unrelated ``cmp``s.
    """
    if ps is None or recomp is None:
        return None
    if _mnemonic(ps) != "cmp" or _mnemonic(recomp) != "cmp":
        return None
    ps_ops = _operands(ps).split(",")
    rc_ops = _operands(recomp).split(",")
    if len(ps_ops) != 2 or len(rc_ops) != 2:
        return None
    # Same first operand (register or memory expression).
    if ps_ops[0].strip() != rc_ops[0].strip():
        return None
    ps_imm = _parse_imm(ps_ops[1])
    rc_imm = _parse_imm(rc_ops[1])
    if ps_imm is None or rc_imm is None:
        return None
    if abs(ps_imm - rc_imm) != 1:
        return None
    # Confirm the inclusive/exclusive Jcc complement on the next row.
    nps, nrc = _mnemonic(next_ps), _mnemonic(next_recomp)
    if nps not in _JCC_BOUNDARY or _JCC_BOUNDARY[nps] != nrc:
        return None
    op = ps_ops[0].strip()
    return RuleHint(
        rule="Rule 4b",
        summary=f"cmp {op}, {hex(ps_imm)} (PS) vs {hex(rc_imm)} (RC); "
                f"{nps}\u2194{nrc}",
        fix=f"rewrite the comparison boundary to PS's form: use the "
            f"constant {hex(ps_imm)} (e.g. `>= {hex(ps_imm)}` instead of "
            f"`> {hex(rc_imm)}`, or `<= {hex(ps_imm)}` instead of "
            f"`< {hex(rc_imm)}`).  Semantically identical; Watcom keeps the "
            f"source form, so the immediate + Jcc must match PS literally.",
    )


# ── Rule 8 / 23 - signed-char movsx vs mov+and 0xff ──────────────────────

def _is_zext_to_dword(insn: InsnT | None) -> bool:
    """Is this an `and reg32, 0xff` zero-extension to dword?"""
    if insn is None:
        return False
    if _mnemonic(insn) != "and":
        return False
    asm = insn[3].upper()
    if "0XFF" not in asm and "0FFH" not in asm:
        return False
    # Operand1 must be a 32-bit reg (eax/ebx/ecx/edx/esi/edi/ebp)
    ops = _operands(insn).split(",")
    if not ops:
        return False
    return ops[0].strip().lower() in {
        "eax", "ebx", "ecx", "edx", "esi", "edi", "ebp",
    }


def _is_self_xor(insn: InsnT | None) -> bool:
    """Is this an `xor reg32, reg32` self-zero of a 32-bit register?"""
    if insn is None or _mnemonic(insn) != "xor":
        return False
    ops = [o.strip().lower() for o in _operands(insn).split(",")]
    if len(ops) != 2 or ops[0] != ops[1]:
        return False
    return ops[0] in {
        "eax", "ebx", "ecx", "edx", "esi", "edi", "ebp",
    }


def detect_rule_8(
    ps: InsnT | None,
    recomp: InsnT | None,
    ps_next: InsnT | None,
    recomp_next: InsnT | None,
    ps_prev: InsnT | None = None,
    recomp_prev: InsnT | None = None,
) -> Optional[RuleHint]:
    """signed char read (movsx) vs unsigned-byte-then-zero-extend.

    Three patterns trigger - all share the property that PS reads
    a byte with sign-extension (`movsx`) while recomp does an
    unsigned-byte load followed by zero-extension.

    A. Struct-field / indexed-array read (zero-extend AFTER the load):
         PS:     movsx reg32, byte ptr [m]
         Recomp: mov   reg8,  byte ptr [m]
                 and   reg32, 0xff             (next row)

    B. After-the-fact zero-extension (the byte was already in reg8):
         PS:     movsx reg32, reg8
         Recomp: and   reg32, 0xff

    C. Plain global / local-with-stack-slot read (zero-extend BEFORE
       the load - Watcom's standard unsigned-byte load idiom):
         PS:     movsx reg32, byte ptr [m]
         Recomp: xor   reg32, reg32             (current row OR prev)
                 mov   reg8,  byte ptr [m]
    """
    if ps is None or recomp is None:
        return None
    if _mnemonic(ps) != "movsx":
        return None

    ps_ops = _operands(ps).split(",")
    if len(ps_ops) != 2:
        return None
    ps_src = ps_ops[1].strip().lower()

    # Constrain to BYTE-source movsx (signed char → int). `movsx reg, word
    # ptr` (short → int) is unrelated to Rule 8/23.
    is_byte_mem = "byte ptr" in ps_src
    is_byte_reg = ps_src in {
        "al", "bl", "cl", "dl", "ah", "bh", "ch", "dh",
    }
    if not (is_byte_mem or is_byte_reg):
        return None

    # Pattern A: PS movsx reg32, byte ptr [mem]
    #            Recomp mov reg8, byte ptr [mem]  +  and reg32, 0xff
    if (
        is_byte_mem
        and _mnemonic(recomp) == "mov"
        and "byte ptr" in _operands(recomp)
        and _is_zext_to_dword(recomp_next)
    ):
        return RuleHint(
            rule="Rule 8/23",
            summary="PS movsx (signed), recomp mov+and 0xff (unsigned)",
            fix="declare the struct field / variable as `signed char` "
                "(and drop any `(char)` cast at the read site).",
        )

    # Pattern C: PS movsx reg32, byte ptr [mem]
    #            Recomp xor reg32, reg32  (current row, or prev row)
    #                   mov reg8, byte ptr [mem]   (next row, or current)
    if is_byte_mem:
        # C1: recomp's CURRENT row is the xor; next is the mov
        if (
            _is_self_xor(recomp)
            and recomp_next is not None
            and _mnemonic(recomp_next) == "mov"
            and "byte ptr" in _operands(recomp_next)
        ):
            return RuleHint(
                rule="Rule 8/23",
                summary="PS movsx (signed), recomp xor+mov al (unsigned)",
                fix="declare the variable / global as `signed char` "
                    "(and drop any `(char)` cast at the read site).",
            )
        # C2: recomp's CURRENT row is the byte mov; PREV was the xor
        if (
            _mnemonic(recomp) == "mov"
            and "byte ptr" in _operands(recomp)
            and _is_self_xor(recomp_prev)
        ):
            return RuleHint(
                rule="Rule 8/23",
                summary="PS movsx (signed), recomp xor+mov al (unsigned)",
                fix="declare the variable / global as `signed char` "
                    "(and drop any `(char)` cast at the read site).",
            )

    # Pattern B: PS movsx reg32, reg8
    #            Recomp and reg32, 0xff (the reg8 was loaded earlier)
    if is_byte_reg and _is_zext_to_dword(recomp):
        return RuleHint(
            rule="Rule 8/23",
            summary="PS movsx (signed), recomp and reg, 0xff (unsigned)",
            fix="declare the struct field / variable as `signed char` "
                "(and drop any `(char)` cast at the read site).",
        )

    return None


# ── Rule 12 - data-pointer literal vs integer constant ────────────────────────

def detect_rule_12(
    ps: InsnT | None,
    recomp: InsnT | None,
    ps_abs_base: int,
    recomp_abs_base: int,
    ps_fix: set[int],
    recomp_fix: set[int],
) -> Optional[RuleHint]:
    """PS encodes a data-pointer fixup, recomp emits a literal IMM.

    Two shapes covered:

    A. ``mov r32, imm32`` (opcode B8+rd, 5 bytes):
         PS:     b8 ?? ?? ?? ??           (4-byte fixup in imm)
         Recomp: b8 NN NN NN NN           (literal imm)

    B. ``mov dword ptr [m], imm32`` (opcode C7 05 ... imm32, 10 bytes):
         PS:     c7 05 ?? ?? ?? ?? ?? ?? ?? ??   (fixup in BOTH the
                                                  mem operand and the
                                                  imm32)
         Recomp: c7 05 ?? ?? ?? ?? NN NN NN NN   (fixup only on the
                                                  mem operand)

    The discriminator is: PS's imm32 bytes are fully relocated, recomp's
    are literal.  Different destination registers / addresses don't
    match.
    """
    if ps is None or recomp is None:
        return None
    if ps[1] != recomp[1]:           # different sizes - not the same shape
        return None

    # Pattern A: `mov reg, imm32` (B8..BF + 4-byte imm)
    if (
        ps[1] == 5
        and 0xB8 <= ps[2][0] <= 0xBF
        and ps[2][0] == recomp[2][0]
    ):
        if (
            _all_bytes_in_fixup(ps, ps_abs_base, ps_fix, offset=1, length=4)
            and _none_in_fixup(recomp, recomp_abs_base, recomp_fix,
                               offset=1, length=4)
        ):
            return RuleHint(
                rule="Rule 12",
                summary="PS has data-pointer fixup, recomp emits integer literal",
                fix="pass `(int)&data_NNNN` (address-of) instead of an "
                    "integer constant - see the data symbol the literal "
                    "value matches.",
            )
        return None

    # Pattern B: `mov dword ptr [m], imm32` (C7 05 ... + 4-byte imm at offset 6)
    if (
        ps[1] == 10
        and ps[2][0:2] == b"\xc7\x05"
        and recomp[2][0:2] == b"\xc7\x05"
    ):
        if (
            _all_bytes_in_fixup(ps, ps_abs_base, ps_fix, offset=6, length=4)
            and _none_in_fixup(recomp, recomp_abs_base, recomp_fix,
                               offset=6, length=4)
        ):
            return RuleHint(
                rule="Rule 12",
                summary="PS has data-pointer fixup, recomp emits integer literal",
                fix="pass `(int)&data_NNNN` (address-of) instead of an "
                    "integer constant - see the data symbol the literal "
                    "value matches.",
            )
        return None

    return None


# ── Rule 14 - `void` return vs explicit `return N` ────────────────────────────

def detect_rule_14(
    ps: InsnT | None,
    recomp: InsnT | None,
    ps_next: InsnT | None,
    recomp_next: InsnT | None,
) -> Optional[RuleHint]:
    """Recomp emits `mov eax, IMM` immediately before a `ret` that PS lacks.

    This shows up as a row where PS is None / different instruction and
    recomp has `mov eax, IMM` followed by `ret`, indicating the source
    was declared as `int X(...) { ...; return N; }` but PS treats it as
    `void X(...) { ...; }` (no EAX set before ret).
    """
    if recomp is None:
        return None
    rc_mn = _mnemonic(recomp)
    if rc_mn not in ("mov", "xor"):
        return None
    rc_ops = _operands(recomp)
    # Must target eax with an immediate or self-zero
    if rc_mn == "mov" and not (rc_ops.startswith("eax,") and recomp[1] >= 5):
        return None
    if rc_mn == "xor" and rc_ops.replace(" ", "") != "eax,eax":
        return None
    # The immediately following recomp insn should be a `ret`
    if _mnemonic(recomp_next) != "ret":
        return None
    # PS at this position is either missing this instruction (None) or is
    # already the `ret` itself (different mnemonic from recomp).
    if ps is not None and _mnemonic(ps) == rc_mn:
        return None
    return RuleHint(
        rule="Rule 14",
        summary="recomp sets EAX before ret, PS does not",
        fix="declare the function `void` (drop the `return N` - call sites "
            "may still appear to consume it but PS doesn't set EAX).",
    )


# ── Rule 16 - short-vs-near jmp encoding ──────────────────────────────────────

def detect_rule_16(
    ps: InsnT | None,
    recomp: InsnT | None,
) -> Optional[RuleHint]:
    """Same branch mnemonic, different encoding length.

    Two shapes covered:

    A. Unconditional jmp:    EB rel8 (2 bytes) vs E9 rel32 (5 bytes).
    B. Conditional Jcc:      7x rel8 (2 bytes) vs 0F 8x rel32 (6 bytes).

    The most common cause is intermediate stubs inflating/deflating
    the byte distance to a target.  Works even when the longer
    encoding overflows the PS function bounds (capstone shows
    ``<raw Nb>`` in that case).
    """
    if ps is None or recomp is None:
        return None
    if not ps[2] or not recomp[2]:
        return None
    ps_op = ps[2][0]
    rc_op = recomp[2][0]

    # Pattern A: jmp short EB <-> jmp near E9
    if {ps_op, rc_op} == {0xEB, 0xE9}:
        if _mnemonic(ps) != "jmp" and _mnemonic(recomp) != "jmp":
            return None
        longer = "PS" if ps_op == 0xE9 else "recomp"
        return RuleHint(
            rule="Rule 16",
            summary=f"jmp encoding mismatch ({longer} uses 5-byte E9, "
                    "other uses 2-byte EB)",
            fix="decompile intermediate stubs between this jmp and its "
                "merge target to push the distance over 127 bytes (or "
                "under, depending on direction).",
        )

    # Pattern B: Jcc short 70..7F <-> Jcc near 0F 80..8F
    def _is_short_jcc(op: int) -> bool:
        return 0x70 <= op <= 0x7F

    def _is_near_jcc(insn: InsnT) -> bool:
        return (
            len(insn[2]) >= 2
            and insn[2][0] == 0x0F
            and 0x80 <= insn[2][1] <= 0x8F
        )

    ps_short  = _is_short_jcc(ps_op)
    ps_near   = _is_near_jcc(ps)
    rc_short  = _is_short_jcc(rc_op)
    rc_near   = _is_near_jcc(recomp)
    if (ps_short and rc_near) or (ps_near and rc_short):
        # Same Jcc condition?  The low nibble must match (74/0F84 = je,
        # 75/0F85 = jne, etc.).  Where the long form's second byte is
        # 0x80 + (short_op - 0x70).
        ps_cond = (ps_op & 0x0F) if ps_short else (ps[2][1] & 0x0F)
        rc_cond = (rc_op & 0x0F) if rc_short else (recomp[2][1] & 0x0F)
        if ps_cond != rc_cond:
            return None
        longer = "PS" if ps_near else "recomp"
        return RuleHint(
            rule="Rule 16",
            summary=f"Jcc encoding mismatch ({longer} uses 6-byte 0F 8x, "
                    "other uses 2-byte 7x)",
            fix="decompile intermediate stubs between this Jcc and its "
                "target to push the distance over 127 bytes (or under, "
                "depending on direction).",
        )
    return None


# ── Rule 19 - char vs int parameter spill ─────────────────────────────────────

def detect_rule_19(
    ps: InsnT | None,
    recomp: InsnT | None,
) -> Optional[RuleHint]:
    """Function-entry stack spill width mismatch.

    Triggers on `mov [esp{+N}], reg` where PS uses 4-byte spill
    (opcode 0x89) and recomp uses 1-byte spill (0x88), or vice versa.
    """
    if ps is None or recomp is None:
        return None
    if _mnemonic(ps) != "mov" or _mnemonic(recomp) != "mov":
        return None
    if "[esp" not in _operands(ps):
        return None
    if "[esp" not in _operands(recomp):
        return None
    ps_op, rc_op = ps[2][0], recomp[2][0]
    # 0x88 = mov r/m8, r8;  0x89 = mov r/m32, r32 (for our spills)
    if {ps_op, rc_op} != {0x88, 0x89}:
        return None
    smaller = "PS" if ps_op == 0x88 else "recomp"
    return RuleHint(
        rule="Rule 19",
        summary=f"stack spill width mismatch ({smaller} uses byte spill, "
                "other uses dword spill)",
        fix="change the parameter type between `int` (dword spill) and "
            "`char`/`unsigned char` (byte spill) to match PS's width.",
    )


# ── Rule 9 - `if (cond == 0)` else-first layout ──────────────────────────────

def _is_compare_against_zero(insn: InsnT | None) -> tuple[str, str] | None:
    """If `insn` is a zero-compare, return (kind, operand) describing it.

    Recognised forms:
      * ``test reg, reg``        - kind="test",  operand=reg
      * ``cmp reg, 0``           - kind="cmp",   operand=reg
      * ``cmp dword ptr [m], 0`` - kind="cmpm",  operand=mem-text
      * ``cmp byte/word ptr [m], 0`` - kind="cmpm", operand=mem-text
    Returns None otherwise.
    """
    if insn is None:
        return None
    mn = _mnemonic(insn)
    if mn not in ("test", "cmp"):
        return None
    ops = [o.strip() for o in _operands(insn).split(",")]
    if len(ops) != 2:
        return None
    op1, op2 = ops
    if mn == "test" and op1 == op2:
        return ("test", op1.lower())
    if mn == "cmp":
        # cmp X, 0 - operand 2 must be literal 0
        if op2 in ("0", "0x0"):
            if "[" in op1:
                return ("cmpm", op1.lower())
            return ("cmp", op1.lower())
    return None


def detect_rule_9(
    ps: InsnT | None,
    recomp: InsnT | None,
    ps_prev: InsnT | None,
    recomp_prev: InsnT | None,
) -> Optional[RuleHint]:
    """if/else block reorder with operator-flipped Jcc.

    Triggers when both sides are conditional jumps with complementary
    mnemonics (je↔jne, jz↔jnz, jl↔jge, jle↔jg, jb↔jae, jbe↔ja) AND
    the immediately preceding instruction on both sides is the SAME
    compare:

      * ``test reg, reg`` (zero-compare, register-resident)
      * ``cmp reg, 0`` / ``cmp <ptr> [m], 0`` (zero-compare, mem-resident)
      * ``cmp X, Y`` for any pair X, Y - so long as both sides match

    A `cmp X, Y` vs `cmp Y, X` (operands swapped) with complementary
    Jcc is Rule 4 territory and is handled by detect_rule_4 (which
    runs after Rule 9 in the chain - so the operand-equality check
    here distinguishes the two).

    The fix is to invert the source `if (cond)` to `if (!cond)` and
    swap the if/else bodies, so the if-body becomes the natural
    fall-through.  Per the verified Rule 9 mechanism: the if-body
    ALWAYS falls through; the Jcc opcode is the inverted C test.
    """
    if ps is None or recomp is None:
        return None
    ps_mn, rc_mn = _mnemonic(ps), _mnemonic(recomp)
    if ps_mn not in _JCC_EQ_FLIP or _JCC_EQ_FLIP[ps_mn] != rc_mn:
        return None

    # Equality forms (je/jne/jz/jnz) require a zero-compare; inequality
    # forms (jl/jge/jle/jg/etc.) require any cmp with identical operands.
    if ps_mn in ("je", "jne", "jz", "jnz"):
        ps_z = _is_compare_against_zero(ps_prev)
        rc_z = _is_compare_against_zero(recomp_prev)
        if ps_z is None or rc_z is None:
            return None
        if ps_z != rc_z:
            return None
    else:
        # Inequality: prev must be `cmp X, Y` (or `test reg, reg`) on both
        # sides with the SAME operands.  Same-operand check rules out
        # Rule 4 (operand-swap).
        if (
            _mnemonic(ps_prev) not in ("cmp", "test")
            or _mnemonic(ps_prev) != _mnemonic(recomp_prev)
        ):
            return None
        ps_ops = [o.strip() for o in _operands(ps_prev).split(",")]
        rc_ops = [o.strip() for o in _operands(recomp_prev).split(",")]
        if len(ps_ops) != 2 or ps_ops != rc_ops:
            return None
    return RuleHint(
        rule="Rule 9",
        summary=f"if/else block reorder with operator-flipped Jcc "
                f"({ps_mn}↔{rc_mn})",
        fix="flip the source condition (e.g. `a < b` <-> `a >= b`) "
            "and swap the if/else bodies so the if-body becomes the "
            "natural fall-through.",
    )


# ── Rule 17 - flag-mask split-RMW extra temp ────────────────────────────

_REG8 = {
    "al", "bl", "cl", "dl", "ah", "bh", "ch", "dh",
}


def _is_immediate_token(tok: str) -> bool:
    """Recognise a numeric immediate (capstone formats: ``0x1f``, ``31``,
    ``-1``, ``0xffffff9d``).  Used by Rules 17, 5, 24b which need to
    distinguish ``and reg8, IMM`` from ``and reg8, reg8`` etc."""
    t = tok.strip().lower()
    if not t:
        return False
    if t.startswith("-"):
        t = t[1:]
    if t.startswith("0x"):
        return all(c in "0123456789abcdef" for c in t[2:])
    return t.isdigit()


def _is_and_reg8_imm(insn: InsnT | None) -> str | None:
    """If `insn` is `and reg8, IMM`, return the reg name."""
    if insn is None or _mnemonic(insn) != "and":
        return None
    ops = [o.strip() for o in _operands(insn).split(",")]
    if len(ops) != 2 or ops[0] not in _REG8:
        return None
    if not _is_immediate_token(ops[1]):
        return None
    return ops[0]


def _is_or_reg8_imm(insn: InsnT | None) -> str | None:
    """If `insn` is `or reg8, IMM`, return the reg name."""
    if insn is None or _mnemonic(insn) != "or":
        return None
    ops = [o.strip() for o in _operands(insn).split(",")]
    if len(ops) != 2 or ops[0] not in _REG8:
        return None
    if not _is_immediate_token(ops[1]):
        return None
    return ops[0]


def detect_rule_17(
    ps: InsnT | None,
    recomp: InsnT | None,
    ps_next: InsnT | None,
    recomp_next: InsnT | None,
    ps_prev: InsnT | None = None,
    recomp_prev: InsnT | None = None,
) -> Optional[RuleHint]:
    """Flag-mask split-RMW emits an extra register-copy temp.

    PS pattern (split form, larger)::

        mov  reg8a, [flags]
        and  reg8a, MASK
        mov  [flags], reg8a       ← intermediate store (Rule 3)
        mov  reg8b, reg8a         ← extra reg-copy
        or   reg8b, BIT
        mov  [flags], reg8b

    Recomp pattern (combined form, smaller)::

        mov  reg8c, [flags]
        and  reg8c, MASK
        or   reg8c, BIT
        mov  [flags], reg8c

    Watcom's regalloc picks different physical registers for the
    split vs combined form, so we do NOT require any register-name
    match between the sides.  Two complementary triggers cover the
    main difflib alignment shapes:

    Trigger A (`mov reg8a, reg8b` row):

      * PS row : `mov reg8a, reg8b` (different 8-bit regs - the
        reg-copy that combined form omits).
      * Recomp anywhere in the [-1, 0, +1] window: `or reg8c, IMM`.

    Trigger B (`and` row paired with `or` row):

      * PS row : `and reg8a, IMM` (the AND in the split form).
      * Recomp row at same diff index: `or reg8b, IMM`.
        difflib often pairs these because they're both "middle"
        ALU ops on a byte register.

    The combination is specific enough to be a high-confidence Rule
    17 hit.
    """
    if ps is None or recomp is None:
        return None

    # Trigger A: PS reg8-copy paired with recomp `or reg8, IMM`
    if _mnemonic(ps) == "mov":
        ps_ops = [o.strip() for o in _operands(ps).split(",")]
        if (
            len(ps_ops) == 2
            and ps_ops[0] in _REG8
            and ps_ops[1] in _REG8
            and ps_ops[0] != ps_ops[1]
        ):
            target = (
                _is_or_reg8_imm(recomp)
                or _is_or_reg8_imm(recomp_next)
                or _is_or_reg8_imm(recomp_prev)
            )
            if target is not None:
                return RuleHint(
                    rule="Rule 17",
                    summary=(
                        f"flag-mask split-RMW extra temp "
                        f"(PS mov {ps_ops[0]},{ps_ops[1]}; recomp "
                        f"folded `or {target}, IMM`)"
                    ),
                    fix="split `x = (x & MASK) | BIT;` into TWO statements: "
                        "`x &= MASK;` then `x |= BIT;` to force the extra "
                        "reg-copy temp.",
                )

    # Trigger B: PS `and reg8, IMM` paired with recomp `or reg8, IMM`
    ps_and = _is_and_reg8_imm(ps)
    rc_or  = _is_or_reg8_imm(recomp)
    if ps_and is not None and rc_or is not None:
        return RuleHint(
            rule="Rule 17",
            summary=(
                f"flag-mask split-RMW alignment "
                f"(PS `and {ps_and}, IMM`; recomp `or {rc_or}, IMM`)"
            ),
            fix="split `x = (x & MASK) | BIT;` into TWO statements: "
                "`x &= MASK;` then `x |= BIT;` to force the extra "
                "reg-copy temp.",
        )
    return None


# ── Rule 24 - spill swap and shift-in-place choices ────────────

_CALLEE_SAVE_REGS = {"esi", "edi", "ebx", "ebp"}
_LOW32_REGS       = {"eax", "ebx", "ecx", "edx"}


def _classify_mov(insn: InsnT | None) -> tuple[str, str, str] | None:
    """Return (dst_kind, dst_text, src_text) for a `mov` insn or None.

    `dst_kind` is ``"reg"`` for a callee-save destination register or
    ``"stack"`` for an ``[esp...]`` memory destination. Anything else
    (segment regs, BYTE PTR moves, etc.) returns None.
    """
    if insn is None or _mnemonic(insn) != "mov":
        return None
    ops = [o.strip() for o in _operands(insn).split(",")]
    if len(ops) != 2:
        return None
    dst, src = ops
    dst_lower = dst.lower()
    if dst_lower in _CALLEE_SAVE_REGS:
        return ("reg", dst_lower, src.lower())
    if dst_lower.startswith("dword ptr [esp") or (
        "[esp" in dst_lower and "byte ptr" not in dst_lower
        and "word ptr" not in dst_lower
    ):
        return ("stack", dst_lower, src.lower())
    return None


_RULE_100_REGS = {"eax", "ebx", "ecx", "edx", "esi", "edi", "ebp"}


_RULE_100_ARITH = {
    "sub", "add", "sbb", "adc", "and", "or", "xor", "imul",
    "cmp", "test", "sar", "sal", "shl", "shr", "lea",
}


def detect_rule_100(
    ps: InsnT | None,
    recomp: InsnT | None,
    ps_next: InsnT | None,
    recomp_next: InsnT | None,
    ps_abs_base: int,
    recomp_abs_base: int,
    ps_fix: set[int],
    recomp_fix: set[int],
) -> Optional[RuleHint]:
    """Rule 100 - live-range-shortening lever (inverse of Rule 97).

    Fires when, at one diff row, PS re-materializes a PLAIN literal into
    a register as a COMPLETE value where recomp reuses a still-live
    register into the SAME destination:

        PS:     mov eax, 0xe0          (b8 e0 00 00 00, imm NOT relocated)
        Recomp: mov eax, esi          (89 f0  - reuses a cached local)

    Same destination register, both `mov`, PS source = non-fixup
    immediate, recomp source = a GP register.  This is the tell that
    our source keeps a local alive (`setup_refresh_area(y, ...)`) past
    the point PS re-emits the equal constant - spelling the use as the
    literal shortens the local's range and can flip a layer-3 Rule 28a
    callee-save swap (worked: new_name_game_loop -60b -> 0).

    Excluded: rows where PS immediately COMBINES the literal into an
    arithmetic op on the same register (`mov eax, 0x50; sub eax, esi`
    == `0x50 - esi`).  Those are operand-evaluation-order / capacity
    regalloc cases (layer 3/6), NOT a source-level literal substitution
    - the literal is one operand of a binary expression, not a complete
    value, so "pass the literal" does not apply.

    High precision: it cannot collide with Rule 12 (which needs BOTH
    sides to be `mov reg, imm`); the recomp side here is a register
    move, never an immediate.  The PS immediate must be a plain
    constant (no fixup bytes), so a relocated pointer-literal
    (`mov reg, &global`) does not trigger it.
    """
    if ps is None or recomp is None:
        return None
    if _mnemonic(ps) != "mov" or _mnemonic(recomp) != "mov":
        return None
    ps_ops = [o.strip().lower() for o in _operands(ps).split(",")]
    rc_ops = [o.strip().lower() for o in _operands(recomp).split(",")]
    if len(ps_ops) != 2 or len(rc_ops) != 2:
        return None
    ps_dst, ps_src = ps_ops
    rc_dst, rc_src = rc_ops
    # Same destination GP register on both sides.
    if ps_dst != rc_dst or ps_dst not in _RULE_100_REGS:
        return None
    # PS source is a plain numeric immediate that is NOT relocated.
    if not _is_immediate_token(ps_src):
        return None
    if not _none_in_fixup(ps, ps_abs_base, ps_fix):
        return None
    # Recomp source is a GP register (the reused live value), not an
    # immediate and not a memory operand.
    if rc_src not in _RULE_100_REGS:
        return None
    # Exclude the `K - v` operand-order case: if PS's NEXT instruction is
    # an arithmetic op whose destination is this same register, the
    # literal is a binary-expression operand, not a complete value.
    if ps_next is not None and _mnemonic(ps_next) in _RULE_100_ARITH:
        nxt_ops = [o.strip().lower() for o in _operands(ps_next).split(",")]
        if nxt_ops and nxt_ops[0] == ps_dst:
            return None
    return RuleHint(
        rule="Rule 100",
        summary=f"PS re-materializes literal {ps_src} into {ps_dst}; "
                f"recomp reuses live register {rc_src}",
        fix="pass the literal at this use site (instead of the cached "
            "local/variable) to shorten its live range - can flip a "
            "layer-3 Rule 28a swap.  Read `c2 disasm` to confirm "
            "direction vs Rule 97 (keep the local if PS reuses a live reg).",
    )


def detect_rule_24a(
    ps: InsnT | None,
    recomp: InsnT | None,
    ps_next: InsnT | None,
    recomp_next: InsnT | None,
    ps_prev: InsnT | None,
    recomp_prev: InsnT | None,
) -> Optional[RuleHint]:
    """Argument-spill swap: PS keeps arg in callee-save reg, recomp
    spills to stack (or vice versa).

    Triggers on a row where:

    * Both sides are `mov` whose source is the SAME register but
      destinations differ in kind - one is a callee-save register
      (esi/edi/ebx/ebp), the other is an `[esp+IMM]` slot.
    * An adjacent diff row (prev or next) has the OPPOSITE swap:
      same kinds flipped between PS and recomp, with a DIFFERENT
      source register.

    The two-row "swap" together is structurally distinct from any
    other documented rule, so the false-positive risk is low.
    """
    cur_ps = _classify_mov(ps)
    cur_rc = _classify_mov(recomp)
    if cur_ps is None or cur_rc is None:
        return None
    if cur_ps[0] == cur_rc[0]:
        return None
    if cur_ps[2] != cur_rc[2]:           # source registers must match
        return None

    # Look in next row first (typical layout), then prev row.
    for other_ps, other_rc in (
        (ps_next, recomp_next),
        (ps_prev, recomp_prev),
    ):
        ot_ps = _classify_mov(other_ps)
        ot_rc = _classify_mov(other_rc)
        if ot_ps is None or ot_rc is None:
            continue
        if ot_ps[0] == ot_rc[0]:                    # not a swap
            continue
        if ot_ps[0] == cur_ps[0]:                   # same direction
            continue
        if ot_ps[2] != ot_rc[2]:                    # source mismatch
            continue
        if ot_ps[2] == cur_ps[2]:                   # same source as current
            continue

        if cur_ps[0] == "stack":
            spilled = cur_ps[2]
            kept_in = cur_rc[1]
            return RuleHint(
                rule="Rule 24a",
                summary=(
                    f"spill swap: PS spills {spilled} to stack, "
                    f"recomp keeps it in {kept_in}"
                ),
                fix=(
                    "introduce a named local that aliases the argument "
                    "PS spills (`int x_local = arg;` before any other "
                    "use) so Watcom assigns it its own stack slot."
                ),
            )
        else:
            spilled = cur_rc[2]
            kept_in = cur_ps[1]
            return RuleHint(
                rule="Rule 24a",
                summary=(
                    f"spill swap: recomp spills {spilled} to stack, "
                    f"PS keeps it in {kept_in}"
                ),
                fix=(
                    "introduce a named local that aliases the argument "
                    "PS keeps in a register so Watcom matches the "
                    "spill choice from the other side of the swap."
                ),
            )
    return None


def _shr_reg_imm(insn: InsnT | None) -> tuple[str, str] | None:
    """If `insn` is `shr <reg32>, IMM`, return (reg, imm); else None."""
    if insn is None or _mnemonic(insn) != "shr":
        return None
    ops = [o.strip() for o in _operands(insn).split(",")]
    if len(ops) != 2:
        return None
    reg, imm = ops[0].lower(), ops[1].lower()
    if reg not in _LOW32_REGS:
        return None
    return (reg, imm)


def detect_rule_24b(
    ps: InsnT | None,
    recomp: InsnT | None,
    ps_next: InsnT | None,
    recomp_next: InsnT | None,
    ps_prev: InsnT | None,
    recomp_prev: InsnT | None,
) -> Optional[RuleHint]:
    """Shift-in-place vs shift-copy choice for splitting a 32-bit arg.

    PS does ``mov ebx, eax; ... shr eax, 0x10; ... mov [m], ax; mov
    [m], bx`` - shifts the ORIGINAL register and reads the low half
    from the saved copy. Recomp does ``mov ebx, eax; shr ebx, 0x10;
    mov [m], bx; mov [m], ax`` - shifts the COPY and reads the low
    half from the original.

    Triggers on a row where exactly ONE side has ``shr <reg>, IMM``
    and any of the [-1, 0, +1] rows on the OTHER side has ``shr
    <different_reg>, IMM`` with the same shift count.
    """
    ps_shr = _shr_reg_imm(ps)
    rc_shr = _shr_reg_imm(recomp)

    # Need a shr on exactly one side of THIS row (otherwise either
    # neither has the pattern, or both shifted the same reg - no diff).
    if (ps_shr is None) == (rc_shr is None):
        return None

    if ps_shr is not None:
        ps_reg, imm = ps_shr
        # Find a recomp shr in any of [-1, 0, +1] rows with same imm.
        for cand in (recomp_prev, recomp, recomp_next):
            cand_shr = _shr_reg_imm(cand)
            if cand_shr is None:
                continue
            rc_reg, rc_imm = cand_shr
            if rc_imm != imm or rc_reg == ps_reg:
                continue
            return RuleHint(
                rule="Rule 24b",
                summary=(
                    f"shift-in-place vs shift-copy "
                    f"(PS shr {ps_reg}, recomp shr {rc_reg})"
                ),
                fix=(
                    "introduce an explicit `unsigned int hi = arg >> N;` "
                    "local before the field assignment so Watcom shifts "
                    "the original register (PS pattern) instead of a "
                    "saved copy."
                ),
            )
        return None
    else:
        rc_reg, imm = rc_shr  # type: ignore[misc]
        for cand in (ps_prev, ps, ps_next):
            cand_shr = _shr_reg_imm(cand)
            if cand_shr is None:
                continue
            ps_reg, ps_imm = cand_shr
            if ps_imm != imm or ps_reg == rc_reg:
                continue
            return RuleHint(
                rule="Rule 24b",
                summary=(
                    f"shift-in-place vs shift-copy "
                    f"(PS shr {ps_reg}, recomp shr {rc_reg})"
                ),
                fix=(
                    "introduce an explicit `unsigned int hi = arg >> N;` "
                    "local before the field assignment so Watcom shifts "
                    "the original register (PS pattern) instead of a "
                    "saved copy."
                ),
            )
        return None


# ── Rule 26 - sete-fold of a boolean call argument ────────────────────

# Conditional set instructions Watcom emits when folding `a == b` (etc.)
# into a 0/1 register value. PS.EXE uses these only 11 times across 37k
# instructions, so a SETcc on the recomp side is a near-certain signal
# of an over-folded boolean.
_SETCC_MNEMONICS = frozenset({
    "sete", "setne", "setl", "setle", "setg", "setge",
    "setb", "setbe", "seta", "setae",
    "sets", "setns", "setz", "setnz", "seto", "setno",
    "setp", "setnp", "setpe", "setpo", "setc", "setnc",
})


def detect_rule_26(
    ps: InsnT | None,
    recomp: InsnT | None,
) -> Optional[RuleHint]:
    """Recomp folded a boolean to ``setcc`` where PS used a branch.

    Triggers when the recomp insn is any ``setcc reg8`` and PS at the
    same diff row is *not* a ``setcc`` (typically ``None`` or a
    branch/mov from the explicit-branch sequence).

    The fix is to express the call in C as two distinct call
    statements inside an ``if/else`` instead of a single call with a
    ``?:`` flag arg - see Rule 26 in
    ``docs/watcom-codegen-patterns.md``.

    PS.EXE contains only 11 ``setcc`` instructions across 37k+ insns,
    so any recomp ``setcc`` paired with a non-``setcc`` PS row is a
    high-confidence Rule 26 hit.
    """
    if recomp is None:
        return None
    rc_mn = _mnemonic(recomp)
    if rc_mn not in _SETCC_MNEMONICS:
        return None
    # PS must NOT be the same setcc - otherwise both sides matched and
    # this isn't a Rule 26 case.
    if ps is not None and _mnemonic(ps) == rc_mn:
        return None
    return RuleHint(
        rule="Rule 26",
        summary=f"recomp folded boolean to `{rc_mn}`, PS used explicit branch",
        fix="split a `func(..., cond ? A : B)` ternary into two call "
            "statements inside `if (cond) func(..., A); else func(..., B);` "
            "so Watcom emits the explicit branch (PS pattern) instead of "
            "folding the boolean to a setcc.",
    )


# ── Rule 5 - signed division by power of 2 (sar/shl/sbb idiom) ────────────

def _is_sar_31(insn: InsnT | None) -> bool:
    """Is this `sar reg, 31` (the sign-extension that starts the idiom)?"""
    if insn is None or _mnemonic(insn) != "sar":
        return False
    ops = [o.strip() for o in _operands(insn).split(",")]
    if len(ops) != 2:
        return False
    # 31 may render as "0x1f" or "31"
    return ops[1].lower() in {"0x1f", "31"}


def _next_is_idiv(insn: InsnT | None) -> bool:
    """Is this an `idiv`/`div` (i.e. the sar 31 before it is just the
    cdq-equivalent sign-extension for a hardware divide, NOT the
    sar/shl/sbb shift-div idiom)?"""
    if insn is None:
        return False
    return _mnemonic(insn) in {"idiv", "div"}


def detect_rule_5(
    ps: InsnT | None,
    recomp: InsnT | None,
    next_ps: InsnT | None = None,
    next_recomp: InsnT | None = None,
) -> Optional[RuleHint]:
    """Signed-division-by-power-of-2 idiom mismatch.

    The 4-insn idiom `sar reg, 31; shl reg, N; sbb dst, reg; sar dst, N`
    starts with `sar reg, 31`.  BUT `sar reg, 31` is ALSO the
    cdq-equivalent sign-extension that precedes a hardware `idiv`
    (`mov edx,src; sar edx,31; idiv divisor`).  So `sar reg,31` alone is
    NOT a unique fingerprint of the shift idiom -- we must check that the
    NEXT instruction on that side is not an `idiv`/`div`.  Without that
    guard, any function that uses `idiv` (e.g. `x % 2` -- MOD has no
    power-of-2 reduction, see i86table.c, so it is always a real idiv)
    produces spurious Rule 5/5b hints once a size shift misaligns the
    two instruction streams.
    """
    ps_is = _is_sar_31(ps) and not _next_is_idiv(next_ps)
    rc_is = _is_sar_31(recomp) and not _next_is_idiv(next_recomp)
    if ps_is == rc_is:
        return None
    if ps_is:
        return RuleHint(
            rule="Rule 5",
            summary="PS uses sar/shl/sbb signed-div idiom, recomp doesn't",
            fix="write the divide as plain `x / N` (where N is a power "
                "of 2) so Watcom emits the sar/shl/sbb sequence; do "
                "NOT use the ternary-bias form.",
        )
    return RuleHint(
        rule="Rule 5b",
        summary="recomp uses sar/shl/sbb signed-div idiom; PS uses a bare "
                "shift OR a shared-divisor idiv",
        fix="recomp strength-reduced `x / 2^N` to the sar/shl/sbb shift form "
            "(table rule V_OP2TWO->G_DIV2 / V_OP2POW2->G_POW2DIV).  PS did "
            "NOT.  Two PS-matching sources: (a) if the value is non-negative "
            "by construction, write `x >> N` (a bare arithmetic shift); or "
            "(b) if an adjacent `x % 2^N` shares the divisor, PS keeps the "
            "divisor 2^N in a TEMP register so V_OP2TWO/V_OP2POW2 (which "
            "require op2 == literal constant) FAIL and BOTH the `/` and `%` "
            "emit `idiv` -- match PS's `idiv` form, do not force a shift.  "
            "CAVEAT: regresses when the divided value shares its load with a "
            "sibling `& (2^N-1)` parity test - skip those.",
    )


# ── Rule 27 - instruction-pair reorder at function entry ─────────────────

def _find_rule_27_pairs(
    rows: list[tuple[InsnT | None, InsnT | None, bool]],
) -> dict[int, tuple[int, str, str]]:
    """Find all instruction-pair-reorder swaps in `rows`.

    Returns ``{row_index: (peer_index, ps_text, rc_text)}`` - every
    row that is part of a swap pair maps to the index of its peer
    plus the two instruction texts involved.

    Two shapes are recognised:

    A. **delete + insert** - difflib aligned the swap as one missing
       row on PS and one missing row on recomp:

          row i:  PS=`mov X, A`,  RC=None       (delete)
          row j:  PS=None,        RC=`mov X, A` (insert)

       within ±3 rows of each other.

    B. **replace + replace** - difflib paired up both rows:

          row i:  PS=`mov X, A`,  RC=`mov Y, B`
          row j:  PS=`mov Y, B`,  RC=`mov X, A`

    Limit to `mov` instructions: random `cmp` / `add` reorders are
    far rarer in practice and would muddy the hint.
    """
    out: dict[int, tuple[int, str, str]] = {}
    used: set[int] = set()

    def _is_simple_mov(insn: InsnT | None) -> bool:
        if insn is None:
            return False
        return _mnemonic(insn) == "mov"

    n = len(rows)
    for i in range(n):
        if i in used:
            continue
        ps_i, rc_i, d_i = rows[i]
        if not d_i:
            continue

        # Shape A: delete row (PS has insn, RC is None)
        if _is_simple_mov(ps_i) and rc_i is None:
            ps_text = ps_i[3]
            for offset in (1, -1, 2, -2, 3, -3):
                j = i + offset
                if not (0 <= j < n) or j in used:
                    continue
                ps_j, rc_j, d_j = rows[j]
                if not d_j:
                    continue
                if ps_j is None and _is_simple_mov(rc_j) and rc_j[3] == ps_text:
                    out[i] = (j, ps_text, rc_j[3])
                    out[j] = (i, ps_text, rc_j[3])
                    used.add(i)
                    used.add(j)
                    break
            continue

        # Shape A (insert row first): RC has insn, PS is None
        if _is_simple_mov(rc_i) and ps_i is None:
            rc_text = rc_i[3]
            for offset in (1, -1, 2, -2, 3, -3):
                j = i + offset
                if not (0 <= j < n) or j in used:
                    continue
                ps_j, rc_j, d_j = rows[j]
                if not d_j:
                    continue
                if rc_j is None and _is_simple_mov(ps_j) and ps_j[3] == rc_text:
                    out[i] = (j, ps_j[3], rc_text)
                    out[j] = (i, ps_j[3], rc_text)
                    used.add(i)
                    used.add(j)
                    break
            continue

        # Shape B: replace row, look for mirrored replace within ±3
        if (
            _is_simple_mov(ps_i)
            and _is_simple_mov(rc_i)
            and ps_i[3] != rc_i[3]
        ):
            ps_text, rc_text = ps_i[3], rc_i[3]
            for offset in (1, -1, 2, -2, 3, -3):
                j = i + offset
                if not (0 <= j < n) or j in used:
                    continue
                ps_j, rc_j, d_j = rows[j]
                if not d_j:
                    continue
                if (
                    _is_simple_mov(ps_j)
                    and _is_simple_mov(rc_j)
                    and ps_j[3] == rc_text
                    and rc_j[3] == ps_text
                ):
                    out[i] = (j, ps_text, rc_text)
                    out[j] = (i, ps_text, rc_text)
                    used.add(i)
                    used.add(j)
                    break
    return out


# ── Rule 28 - whole-function callee-save register swap ────────────────────────
#
# When a void(void)-shaped function has long-lived locals, Watcom's greedy
# allocator picks callee-save registers from `Reg64Order` / `DoubleRegs` (in
# `bld/cg/intel/386/c/386rgtbl.c`) using `CountRegMoves` savings (in
# `bld/cg/c/regalloc.c:GiveBestReg`).  ESI is BEFORE EDI in both priority
# lists, so by default the first long-lived 32-bit local lands in ESI; the
# tie-breaker then prefers registers already in `GivenRegisters` (i.e.
# already pushed in the prologue) so subsequent locals stick to ESI.
#
# Bit-identical between OW v1.0.0 (`bld/cg/intel/386/c/386rgtbl.c:50-58`,
# `bld/cg/c/regalloc.c:836-840`) and OW v2 master (same files, same lines).
#
# Some PS.EXE functions (e.g. `new_name_game_loop`, `battle_game_loop`)
# allocate the long-lived value to EDI instead, because PS's source had a
# slightly different shape that nudged the savings calculation toward EDI.
# Without that source-level lever, the recomp picks ESI everywhere, leading
# to a function-wide diff that looks like a single-pair register swap.
#
# This detector is a function-level pre-scan: it inspects the prologue
# pushes to identify a single-pair swap, then per-row checks that each diff
# is fully explained by that rename (asm-string comparison after register
# substitution, with numeric tokens in fixup positions allowed to differ).

_CALLEE_SAVE_PUSH_REGS = frozenset({
    "ebx", "ecx", "edx", "esi", "edi", "ebp",
})

_PUSH_RE = re.compile(r"^push\s+([a-z0-9]+)$")

_REG_FORMS_R28 = {
    "eax": ("eax", "ax", "al", "ah"),
    "ebx": ("ebx", "bx", "bl", "bh"),
    "ecx": ("ecx", "cx", "cl", "ch"),
    "edx": ("edx", "dx", "dl", "dh"),
    "esi": ("esi", "si"),
    "edi": ("edi", "di"),
    "ebp": ("ebp", "bp"),
}

_TOKEN_RE_R28 = re.compile(r"[\w]+|[^\w\s]")


def _scan_prologue_pushes(
    insns: list[InsnT | None],
) -> tuple[list[str], int, int]:
    """Return register names from leading consecutive `push reg` insns.

    Skips an optional stack-check preamble of the form
    ``push <imm32>; call <abs>`` (Watcom\u2019s `__CHK` invocation, present
    on functions with stack frames \u2265 0x100 bytes).

    Returns ``(pushes, push_start, push_end)`` where ``push_start`` and
    ``push_end`` are insn indices delimiting the contiguous register-
    push prologue.  Stops at the first non-push or push-of-non-
    callee-save instruction.
    """
    n = len(insns)
    i = 0
    # Optional stack-check preamble: push <imm>; call <abs>
    if (
        i + 1 < n
        and insns[i] is not None
        and insns[i + 1] is not None
        and re.fullmatch(r"push\s+(?:0x[0-9a-fA-F]+|[0-9]+)", insns[i][3])
        and _mnemonic(insns[i + 1]) == "call"
    ):
        i += 2

    pushes: list[str] = []
    start = i
    while i < n:
        ins = insns[i]
        if ins is None:
            break
        m = _PUSH_RE.match(ins[3])
        if not m:
            break
        reg = m.group(1).lower()
        if reg not in _CALLEE_SAVE_PUSH_REGS:
            break
        pushes.append(reg)
        i += 1
    return pushes, start, i


def _find_rule_28_swap(
    rows: list[tuple[InsnT | None, InsnT | None, bool]],
) -> tuple[str, str] | None:
    """Detect a single-pair callee-save register swap in the prologue.

    Returns ``(ps_reg, rc_reg)`` if exactly one register differs between
    the PS and recomp prologue push sequences, else ``None``.

    Requires the prologues to have the same length.  Asymmetric push
    counts (Rule 28b \u2014 regalloc-priority cascade) are handled by
    `_find_rule_28b_extras` instead.
    """
    ps_insns = [r[0] for r in rows]
    rc_insns = [r[1] for r in rows]
    ps_pushes, _, _ = _scan_prologue_pushes(ps_insns)
    rc_pushes, _, _ = _scan_prologue_pushes(rc_insns)
    if len(ps_pushes) != len(rc_pushes) or not ps_pushes:
        return None
    ps_only = set(ps_pushes) - set(rc_pushes)
    rc_only = set(rc_pushes) - set(ps_pushes)
    if len(ps_only) != 1 or len(rc_only) != 1:
        return None
    return next(iter(ps_only)), next(iter(rc_only))


def _find_rule_28b_extras(
    rows: list[tuple[InsnT | None, InsnT | None, bool]],
) -> tuple[set[str], set[str]] | None:
    """Detect asymmetric callee-save push counts (Rule 28b).

    Returns ``(ps_only, rc_only)`` \u2014 sets of register names pushed
    on one side but not the other \u2014 if the difference is
    non-empty AND each side has at most ONE extra register beyond
    the common set.  Otherwise returns ``None``.

    The single-extra-per-side restriction keeps the detector
    focused: the common case is PS has +1 extra callee-save (e.g.
    PS uses ECX as IDIV divisor while recomp uses EBX).  More
    elaborate divergences \u2014 multiple regs added/removed on
    each side \u2014 are too noisy to flag as a single rule.
    """
    ps_insns = [r[0] for r in rows]
    rc_insns = [r[1] for r in rows]
    ps_pushes, _, _ = _scan_prologue_pushes(ps_insns)
    rc_pushes, _, _ = _scan_prologue_pushes(rc_insns)
    ps_only = set(ps_pushes) - set(rc_pushes)
    rc_only = set(rc_pushes) - set(ps_pushes)
    if not ps_only and not rc_only:
        return None
    # Only flag when the asymmetry is small enough to be useful.
    if len(ps_only) > 1 or len(rc_only) > 1:
        return None
    # Must be ASYMMETRIC \u2014 the symmetric 1-vs-1 case is Rule 28a.
    if len(ps_only) == 1 and len(rc_only) == 1:
        return None
    return ps_only, rc_only


def _norm_reg_token_r28(tok: str, swap: dict[str, str]) -> str:
    """Map a register token via the swap, preserving the size suffix."""
    low = tok.lower()
    for full, forms in _REG_FORMS_R28.items():
        if low in forms:
            other = swap.get(full)
            if other is None:
                return low
            i = forms.index(low)
            return _REG_FORMS_R28[other][i]
    return low


def _is_numeric_token(tok: str) -> bool:
    return bool(re.fullmatch(r"-?(0x[0-9a-fA-F]+|[0-9]+)", tok))


def _swap_reg_token_count(tokens: list[str], swap_regs: set[str]) -> int:
    """Count tokens that name any sub-form of a swap-pair register."""
    n = 0
    for t in tokens:
        for full, forms in _REG_FORMS_R28.items():
            if full in swap_regs and t in forms:
                n += 1
                break
    return n


def _row_is_pure_swap(
    ps: InsnT,
    rc: InsnT,
    ps_reg: str,
    rc_reg: str,
    ps_in_fixup: bool,
    rc_in_fixup: bool,
) -> bool:
    """Is the row identical under (ps_reg <-> rc_reg) substitution?

    Requires:
      * Same token count after splitting on word/punct boundaries.
      * Token-by-token equivalence under the register swap.
      * At least one token on each side names a swap-pair register
        (otherwise the rename is a no-op and the byte diff has
        another cause - typically a Rule 16 branch-distance cascade).
      * Numeric-token mismatches are tolerated **only** when both
        bytes are fixup-affected (relocated addresses that legitimately
        differ between the two builds).
    """
    swap = {ps_reg: rc_reg, rc_reg: ps_reg}
    pt = _TOKEN_RE_R28.findall(ps[3].lower())
    rt = _TOKEN_RE_R28.findall(rc[3].lower())
    if len(pt) != len(rt):
        return False
    swap_regs = {ps_reg, rc_reg}
    if (
        _swap_reg_token_count(pt, swap_regs) == 0
        and _swap_reg_token_count(rt, swap_regs) == 0
    ):
        return False
    fixup_ok = ps_in_fixup and rc_in_fixup
    for a, b in zip(pt, rt):
        if a == b:
            continue
        if _is_numeric_token(a) and _is_numeric_token(b):
            if fixup_ok:
                continue
            return False
        if _norm_reg_token_r28(a, swap) == b:
            continue
        return False
    return True


def detect_rule_28(
    ps: InsnT | None,
    recomp: InsnT | None,
    swap: tuple[str, str] | None,
    ps_abs_base: int,
    recomp_abs_base: int,
    ps_fix: set[int],
    recomp_fix: set[int],
) -> Optional[RuleHint]:
    """Per-row Rule 28 check (called only when `swap` was detected).

    Fires when this row is fully explained by the function-level
    callee-save swap.  Does NOT fire on rows that need additional
    rules (Rule 16 cascades, layout shifts, etc.).
    """
    if swap is None or ps is None or recomp is None:
        return None
    ps_reg, rc_reg = swap
    ps_in_fixup = any(
        (ps_abs_base + ps[0] + i) in ps_fix for i in range(len(ps[2]))
    )
    rc_in_fixup = any(
        (recomp_abs_base + recomp[0] + i) in recomp_fix
        for i in range(len(recomp[2]))
    )
    if not _row_is_pure_swap(ps, recomp, ps_reg, rc_reg, ps_in_fixup, rc_in_fixup):
        return None
    return RuleHint(
        rule="Rule 28",
        summary=f"whole-function callee-save swap ({ps_reg}↔{rc_reg})",
        fix=f"PS allocates {ps_reg} where recomp picks {rc_reg}; the "
            "Watcom regalloc savings calculation in `GiveBestReg` ranked "
            f"{ps_reg} higher in PS.  Source-level lever: introduce or "
            "remove a named-local that biases the savings (Rule 24-style).",
    )


def _push_or_pop_reg(insn: InsnT | None) -> tuple[str, str] | None:
    """If `insn` is `push <reg>` or `pop <reg>`, return (mnemonic, reg)."""
    if insn is None:
        return None
    mn = _mnemonic(insn)
    if mn not in ("push", "pop"):
        return None
    op = _operands(insn).strip().lower()
    if op in _CALLEE_SAVE_PUSH_REGS:
        return mn, op
    return None


def detect_rule_28b(
    ps: InsnT | None,
    recomp: InsnT | None,
    extras: tuple[set[str], set[str]] | None,
) -> Optional[RuleHint]:
    """Per-row Rule 28b check (asymmetric callee-save push count).

    Fires on push/pop rows that name a register present on only one
    side of the prologue\u2019s push set.  Body rows are NOT tagged \u2014
    the body shape diverges too much for a single-rule explanation.
    """
    if extras is None:
        return None
    ps_only, rc_only = extras
    ps_pop = _push_or_pop_reg(ps)
    rc_pop = _push_or_pop_reg(recomp)

    # PS-only row (recomp is None or holds an unrelated insn) where PS
    # names a register that is in ps_only.
    if ps_pop is not None and ps_pop[1] in ps_only:
        return RuleHint(
            rule="Rule 28b",
            summary=(
                f"asymmetric callee-save push set "
                f"(PS pushes extra {ps_pop[1]})"
            ),
            fix=(
                "PS\u2019s regalloc reserved an additional callee-save "
                "register that recomp didn\u2019t need.  Often a Watcom "
                "10.0a quirk for tiny non-leaf math helpers (e.g. "
                "`totalXpercent`, `valueDIVtotal`).  No general "
                "source-level lever \u2014 document as a known artefact."
            ),
        )
    # Recomp-only row (PS is None or holds an unrelated insn) where
    # recomp names a register that is in rc_only.
    if rc_pop is not None and rc_pop[1] in rc_only:
        return RuleHint(
            rule="Rule 28b",
            summary=(
                f"asymmetric callee-save push set "
                f"(recomp pushes extra {rc_pop[1]})"
            ),
            fix=(
                "Recomp\u2019s regalloc reserved a callee-save register "
                "that PS didn\u2019t need.  Try removing a named local or "
                "splitting an expression to reduce live-range pressure."
            ),
        )
    return None


def _make_rule_27_hint(ps_text: str, rc_text: str) -> RuleHint:
    return RuleHint(
        rule="Rule 27",
        summary=(
            f"instruction-pair reorder "
            f"(`{ps_text}` and `{rc_text}` emitted in opposite order)"
        ),
        fix="function-entry parm-spill order is determined by the "
            "order Watcom's register allocator processes virtual "
            "names. Adding or REMOVING a named local that aliases a "
            "parm (e.g. `int cap = value;` -> use `value` directly, "
            "or vice versa) flips the order. Try inverting whichever "
            "choice the source currently makes.",
    )


# ── Register-width helpers (used by Rules 37/40/51/62) ───────────────────────

# Map 8-bit register names to their parent 32-bit register name.
_LOW_TO_FULL: dict[str, str] = {
    "al": "eax", "ah": "eax",
    "bl": "ebx", "bh": "ebx",
    "cl": "ecx", "ch": "ecx",
    "dl": "edx", "dh": "edx",
}

# 32-bit registers (full).
_FULL_REGS: set[str] = {
    "eax", "ebx", "ecx", "edx", "esi", "edi", "ebp", "esp",
}


def _reg_family(name: str) -> str | None:
    """Return the 32-bit parent of a register name (or itself if 32-bit).

    Returns None for unknown tokens.
    """
    n = name.strip().lower()
    if n in _FULL_REGS:
        return n
    return _LOW_TO_FULL.get(n)


# ── Rule 29 - DEC vs LEA for in-place global decrement ───────────────────────

def detect_rule_29(
    ps: InsnT | None,
    recomp: InsnT | None,
    next_ps: InsnT | None,
    next_recomp: InsnT | None,
) -> Optional[RuleHint]:
    """PS uses `dec reg; mov [m], reg`; recomp uses `lea reg2, [reg1 - 1];
    mov [m], reg2`.

    The diff row pairs PS's 1-byte `dec` opcode (0x48..0x4F) with
    recomp's 3-byte `lea reg2, [reg1 - 1]` (opcode 0x8D, disp8=0xFF),
    or vice versa.  The instruction immediately after on each side
    should be a `mov [mem], reg` store.
    """
    if ps is None or recomp is None:
        return None
    ps_mn, rc_mn = _mnemonic(ps), _mnemonic(recomp)
    if {ps_mn, rc_mn} != {"dec", "lea"}:
        return None
    # The LEA must be `reg, [reg' - 1]` (or `reg, [reg' + 0xFF]` etc.).
    lea_insn = ps if ps_mn == "lea" else recomp
    lea_ops = _operands(lea_insn).replace(" ", "")
    # Match e.g. `eax,[ebx-1]` (any 32-bit GPR).
    _gpr32 = r"(?:eax|ebx|ecx|edx|esi|edi|ebp|esp)"
    if not re.match(rf"{_gpr32},\[{_gpr32}-(0x)?0*1\]$", lea_ops):
        return None
    # Confirm at least one side has a following `mov [mem], reg` store
    # (the rule is about the in-place RMW shape, so SOMETHING must
    # commit the value back; on the dec side the store may be the
    # `dec [m]` form itself if the source uses memory operand).
    if _mnemonic(next_ps) != "mov" and _mnemonic(next_recomp) != "mov":
        return None
    longer = "recomp" if rc_mn == "lea" else "PS"
    return RuleHint(
        rule="Rule 29",
        summary=f"in-place decrement form mismatch ({longer} uses 3-byte "
                "`lea reg, [src - 1]`, other uses 1-byte `dec reg`)",
        fix="if PS uses `dec`: write `int v = global; v--; global = v;`. "
            "If PS uses `lea`: write `global--;` directly.",
    )


# ── Rule 37 - implicit-int return after a call ───────────────────────────────

def detect_rule_37(
    ps: InsnT | None,
    recomp: InsnT | None,
    prev_ps: InsnT | None,
    prev_recomp: InsnT | None,
) -> Optional[RuleHint]:
    """PS does `test al, al` after a call, recomp does `test eax, eax`
    (or vice versa).

    Pattern: same mnemonic (`test`), self-test on a register pair, but
    one side uses the 8-bit half and the other side uses the full
    32-bit register.  Distinctive in 1 byte (0x84 vs 0x85).  The
    preceding instruction on at least one side is a `call`.
    """
    if ps is None or recomp is None:
        return None
    if _mnemonic(ps) != "test" or _mnemonic(recomp) != "test":
        return None
    ps_ops = [o.strip().lower() for o in _operands(ps).split(",")]
    rc_ops = [o.strip().lower() for o in _operands(recomp).split(",")]
    if len(ps_ops) != 2 or len(rc_ops) != 2:
        return None
    # Both must be self-tests.
    if ps_ops[0] != ps_ops[1] or rc_ops[0] != rc_ops[1]:
        return None
    ps_fam = _reg_family(ps_ops[0])
    rc_fam = _reg_family(rc_ops[0])
    if ps_fam is None or rc_fam is None or ps_fam != rc_fam:
        return None
    ps_is_8  = ps_ops[0] in _LOW_TO_FULL
    rc_is_8  = rc_ops[0] in _LOW_TO_FULL
    if ps_is_8 == rc_is_8:
        return None
    # Confirm at least one side has a preceding `call`.
    if _mnemonic(prev_ps) != "call" and _mnemonic(prev_recomp) != "call":
        return None
    narrow = "PS" if ps_is_8 else "recomp"
    return RuleHint(
        rule="Rule 37",
        summary=f"post-call self-test width mismatch ({narrow} uses 8-bit "
                "reg, other uses 32-bit - callee was declared without a "
                "prototype, so C89 implicit-int kicked in)",
        fix="forward-declare the callee with its real return type (e.g. "
            "`extern char fn(void);`) *before* the first call site.",
    )


# ── Rule 40 - signed-char sentinel test on caller side ───────────────────────

def detect_rule_40(
    ps: InsnT | None,
    recomp: InsnT | None,
    prev_ps: InsnT | None,
    prev_recomp: InsnT | None,
) -> Optional[RuleHint]:
    """PS has `cmp al, 0xff`; recomp has `cmp eax, -1` / `cmp eax,
    0xffffffff` (or vice versa).

    Caller-side companion to Rule 40: when the callee was declared
    `signed char` returning `-1` sentinel, PS compares 1-byte; if the
    caller saw `int` return, it compares 4-byte.
    """
    if ps is None or recomp is None:
        return None
    if _mnemonic(ps) != "cmp" or _mnemonic(recomp) != "cmp":
        return None
    ps_ops = [o.strip().lower() for o in _operands(ps).split(",")]
    rc_ops = [o.strip().lower() for o in _operands(recomp).split(",")]
    if len(ps_ops) != 2 or len(rc_ops) != 2:
        return None
    # First operand must be a register pair (8-bit vs 32-bit).
    ps_fam = _reg_family(ps_ops[0])
    rc_fam = _reg_family(rc_ops[0])
    if ps_fam is None or rc_fam is None or ps_fam != rc_fam:
        return None
    ps_is_8 = ps_ops[0] in _LOW_TO_FULL
    rc_is_8 = rc_ops[0] in _LOW_TO_FULL
    if ps_is_8 == rc_is_8:
        return None
    # Second operand must be a -1 / 0xff sentinel form on both sides.
    def _is_neg1(tok: str) -> bool:
        t = tok.replace(" ", "").lower()
        return t in ("-1", "0xff", "0xffffffff", "255")
    if not (_is_neg1(ps_ops[1]) and _is_neg1(rc_ops[1])):
        return None
    # Preceding instruction should be a `call` on at least one side
    # (the cmp is testing the call result).
    if _mnemonic(prev_ps) != "call" and _mnemonic(prev_recomp) != "call":
        return None
    narrow = "PS" if ps_is_8 else "recomp"
    return RuleHint(
        rule="Rule 40",
        summary=f"post-call sentinel-test width mismatch ({narrow} uses "
                "8-bit `cmp al, 0xff`, other uses 32-bit `cmp eax, -1`)",
        fix="declare the callee `signed char` (not `char` or `int`) so "
            "its `return -1;` matches the caller's 8-bit compare.",
    )


# ── Rule 43 - `__CHK` prologue presence/absence ──────────────────────────────

def detect_rule_43(
    ps: InsnT | None,
    recomp: InsnT | None,
    next_ps: InsnT | None,
    next_recomp: InsnT | None,
    prev_ps: InsnT | None,
    prev_recomp: InsnT | None,
) -> Optional[RuleHint]:
    """One side has `push imm32; call __CHK` prologue, other doesn't.

    Distinctive signature: at the very start of the function (no
    preceding instruction on the side that has the CHK push), one
    side has `push <small_imm>` (5-byte opcode 0x68) followed by
    `call rel32` (5-byte opcode 0xE8), and the other side has a
    plain register-save push.
    """
    if ps is None or recomp is None:
        return None
    if _mnemonic(ps) != "push" or _mnemonic(recomp) != "push":
        return None
    ps_op, rc_op = ps[2][0], recomp[2][0]
    # One side must be a 5-byte `push imm32` (0x68) and the other
    # side must be a 1-byte `push reg` (0x50..0x57).
    chk_is_ps = (ps_op == 0x68 and 0x50 <= rc_op <= 0x57)
    chk_is_rc = (rc_op == 0x68 and 0x50 <= ps_op <= 0x57)
    if not (chk_is_ps or chk_is_rc):
        return None
    chk_side = ps if chk_is_ps else recomp
    next_chk_side = next_ps if chk_is_ps else next_recomp
    # The push's next insn on the CHK side must be a `call`.
    if _mnemonic(next_chk_side) != "call":
        return None
    # The pushed immediate should be a small positive number (typical
    # frame size: 4..0x200).  Reject obvious data-pointer literals.
    if len(chk_side[2]) < 5:
        return None
    imm = int.from_bytes(chk_side[2][1:5], "little")
    if imm == 0 or imm > 0x10000:
        return None
    # The other side must not have a `push imm32 ; call` early either.
    # (Crude proxy: must be a register push.)
    side = "PS" if chk_is_ps else "recomp"
    return RuleHint(
        rule="Rule 43",
        summary=f"`__CHK` prologue mismatch ({side} has `push {imm}; "
                "call __CHK`, other has plain reg-save prologue)",
        fix="wrap the function with `#pragma on(check_stack)` / "
            "`#pragma off(check_stack)` (or remove the wrap) to match "
            "PS's stack-check setting.",
    )


# ── Rule 44 - spurious `and eax, 0xff` after byte AND ────────────────────────

def _is_and_reg_ff(insn: InsnT | None) -> str | None:
    """If `insn` is `and reg32, 0xff`, return the register name."""
    if insn is None or _mnemonic(insn) != "and":
        return None
    ops = [o.strip().lower() for o in _operands(insn).split(",")]
    if len(ops) != 2:
        return None
    if ops[0] not in _FULL_REGS:
        return None
    if ops[1] not in ("0xff", "0xffu", "255"):
        return None
    return ops[0]


def _find_rule_44_excess(
    rows: list[tuple[InsnT | None, InsnT | None, bool]],
) -> dict[int, str]:
    """Identify rows where Rule 44 (spurious `and reg, 0xff`) fires.

    Strategy: count `and reg, 0xff` per side at the function level.
    A *true* Rule 44 case is asymmetric (PS_count != RC_count); the
    asymmetric side has more zexts than the other.  Matched counts
    indicate a layout-shift artefact and are suppressed.

    Returns a dict mapping row-index -> side ("PS" / "recomp") for
    rows that represent the true excess.
    """
    ps_rows: list[tuple[int, str]] = []   # [(row_idx, reg)]
    rc_rows: list[tuple[int, str]] = []
    for i, (ps, rc, is_diff) in enumerate(rows):
        if not is_diff:
            continue
        p = _is_and_reg_ff(ps)
        r = _is_and_reg_ff(rc)
        if p:
            ps_rows.append((i, p))
        if r:
            rc_rows.append((i, r))
    out: dict[int, str] = {}
    # Per-register breakdown so a function with extra `and eax, 0xff`
    # on one side and extra `and edx, 0xff` on the other still flags
    # each excess correctly.
    from collections import defaultdict
    ps_by_reg: dict[str, list[int]] = defaultdict(list)
    rc_by_reg: dict[str, list[int]] = defaultdict(list)
    for idx, reg in ps_rows:
        ps_by_reg[reg].append(idx)
    for idx, reg in rc_rows:
        rc_by_reg[reg].append(idx)
    for reg in set(ps_by_reg) | set(rc_by_reg):
        p_list = ps_by_reg.get(reg, [])
        r_list = rc_by_reg.get(reg, [])
        excess = len(p_list) - len(r_list)
        if excess > 0:
            # PS has more - last `excess` PS rows are the genuine excess.
            for idx in p_list[-excess:]:
                out[idx] = "PS"
        elif excess < 0:
            for idx in r_list[excess:]:  # last |excess| RC rows
                out[idx] = "recomp"
    return out


def detect_rule_44(
    row_idx: int,
    ps: InsnT | None,
    recomp: InsnT | None,
    rule_44_excess: dict[int, str],
    prev_ps: InsnT | None,
    prev_recomp: InsnT | None,
    next_ps: InsnT | None,
    next_recomp: InsnT | None,
) -> Optional[RuleHint]:
    """One side has `and reg32, 0xff` between a byte AND and a Jcc,
    the other side does not.

    Uses the function-level excess map from `_find_rule_44_excess` to
    suppress layout-shift artefacts (rows where both sides have an
    equal count of `and reg, 0xff` instructions).
    """
    side = rule_44_excess.get(row_idx)
    if side is None:
        return None
    insn = ps if side == "PS" else recomp
    reg = _is_and_reg_ff(insn)
    if reg is None:
        return None  # safety
    # Confirm the surrounding context resembles `byte AND → zext → Jcc`.
    fam_prev_same = prev_ps if side == "PS" else prev_recomp
    fam_next_same = next_ps if side == "PS" else next_recomp
    full_to_low = {"eax": "al", "ebx": "bl", "ecx": "cl", "edx": "dl"}
    low = full_to_low.get(reg)
    if low is None:
        return None
    prev_ops_same = _operands(fam_prev_same).lower()
    if low not in prev_ops_same:
        return None
    next_mn = _mnemonic(fam_next_same)
    if next_mn not in ("je", "jne", "jz", "jnz"):
        return None
    return RuleHint(
        rule="Rule 44",
        summary=f"{side} has spurious `and {reg}, 0xff` between a byte "
                "AND and a Jcc (5 bytes of cascade trigger)",
        fix="split the masked byte into an `unsigned char` temp: "
            "`unsigned char x = byte & MASK; if (x == 0) ...`.",
    )


# Rule 106 - callee `unsigned short` param truncates the caller's argument

def _is_and_reg_ffff(insn: InsnT | None) -> str | None:
    """If `insn` is `and reg32, 0xffff`, return the register name.

    `and reg32, 0xffff` is the 16-bit-unsigned truncation Watcom emits when
    an `int`-valued argument is passed to a callee whose declared parameter
    is `unsigned short` (Rule 106).  It is rare in compiled code, so a
    PS-only occurrence right before a `call` is a strong, specific signal.
    """
    if insn is None or _mnemonic(insn) != "and":
        return None
    ops = [o.strip().lower() for o in _operands(insn).split(",")]
    if len(ops) != 2:
        return None
    if ops[0] not in _FULL_REGS:
        return None
    if ops[1] not in ("0xffff", "0xffffu", "65535"):
        return None
    return ops[0]


def _call_within(rows: list[tuple[InsnT | None, InsnT | None, bool]],
                 start: int, side_idx: int, window: int = 3) -> bool:
    """True if a `call` appears on the given side within `window` rows
    after `start` (the arg-truncation precedes the call)."""
    for j in range(start + 1, min(start + 1 + window, len(rows))):
        if _mnemonic(rows[j][side_idx]) == "call":
            return True
    return False


def _find_rule_106_excess(
    rows: list[tuple[InsnT | None, InsnT | None, bool]],
) -> dict[int, str]:
    """Rows where one side has an excess `and reg, 0xffff` that precedes a
    `call` -- the callee-parameter-width truncation of Rule 106.

    Same asymmetry strategy as `_find_rule_44_excess`: count call-adjacent
    `and reg, 0xffff` per side; flag only the genuine excess so a balanced
    pair (a real `& 0xffff` that merely shifted) is suppressed.
    """
    from collections import defaultdict
    ps_by_reg: dict[str, list[int]] = defaultdict(list)
    rc_by_reg: dict[str, list[int]] = defaultdict(list)
    for i, (ps, rc, is_diff) in enumerate(rows):
        if not is_diff:
            continue
        p = _is_and_reg_ffff(ps)
        r = _is_and_reg_ffff(rc)
        if p and _call_within(rows, i, 0):
            ps_by_reg[p].append(i)
        if r and _call_within(rows, i, 1):
            rc_by_reg[r].append(i)
    out: dict[int, str] = {}
    for reg in set(ps_by_reg) | set(rc_by_reg):
        p_list = ps_by_reg.get(reg, [])
        r_list = rc_by_reg.get(reg, [])
        excess = len(p_list) - len(r_list)
        if excess > 0:
            for idx in p_list[-excess:]:
                out[idx] = "PS"
        elif excess < 0:
            for idx in r_list[excess:]:
                out[idx] = "recomp"
    return out


def detect_rule_106(
    row_idx: int,
    ps: InsnT | None,
    recomp: InsnT | None,
    rule_106_excess: dict[int, str],
) -> Optional[RuleHint]:
    """One side truncates a call argument with `and reg, 0xffff` (16-bit
    unsigned param) and the other does not -- Rule 106.

    PS-excess => PS's callee declares the parameter `unsigned short` and
    recomp's prototype is too wide (`int`/signed `short`): the fix is to
    narrow the parameter.  recomp-excess => the mirror (recomp's prototype
    is too narrow): widen it.
    """
    side = rule_106_excess.get(row_idx)
    if side is None:
        return None
    insn = ps if side == "PS" else recomp
    reg = _is_and_reg_ffff(insn)
    if reg is None:
        return None  # safety
    if side == "PS":
        return RuleHint(
            rule="Rule 106",
            summary=f"PS masks a call arg with `and {reg}, 0xffff`; recomp "
                    "omits it (callee param should be `unsigned short`)",
            fix="declare the callee's parameter `unsigned short` (not `int`/"
                "signed `short`) so the int-valued arg is truncated to 16-bit.",
        )
    return RuleHint(
        rule="Rule 106",
        summary=f"recomp masks a call arg with `and {reg}, 0xffff` that PS "
                "does not (callee param is too narrow)",
        fix="widen the callee's parameter to `int` (or signed `short`) so the "
            "arg is not truncated to 16-bit unsigned.",
    )


# ── Rule 49 - `& 0xff` vs `(unsigned char)` zext idiom ───────────────────────

def _is_self_xor_to_full(insn: InsnT | None) -> str | None:
    """If `insn` is `xor reg32, reg32` (self-XOR), return the register."""
    if insn is None or _mnemonic(insn) != "xor":
        return None
    ops = [o.strip().lower() for o in _operands(insn).split(",")]
    if len(ops) != 2 or ops[0] != ops[1]:
        return None
    if ops[0] not in _FULL_REGS:
        return None
    return ops[0]


def _is_byte_load(insn: InsnT | None) -> str | None:
    """If `insn` is `mov reg8, byte ptr [m]`, return the 8-bit reg."""
    if insn is None or _mnemonic(insn) != "mov":
        return None
    ops = [o.strip().lower() for o in _operands(insn).split(",", 1)]
    if len(ops) != 2:
        return None
    if ops[0] not in _LOW_TO_FULL:
        return None
    if "[" not in ops[1]:
        return None
    return ops[0]


def detect_rule_49(
    ps: InsnT | None,
    recomp: InsnT | None,
    next_ps: InsnT | None,
    next_recomp: InsnT | None,
    prev_ps: InsnT | None,
    prev_recomp: InsnT | None,
) -> Optional[RuleHint]:
    """Two zext idioms across a 2-row window:

      PS:  mov reg.lo, [m]; and reg, 0xff   (load-then-mask, longer)
      RC:  xor reg, reg; mov reg.lo, [m]    (xor-then-load, shorter)

    Detection: a diff row where one side is `xor reg, reg` (self-zero)
    and the other side is `mov reg.lo, [m]` to the same register
    family; with confirmation that the other zext form appears in an
    adjacent row.
    """
    if ps is None or recomp is None:
        return None
    # Case A: PS=xor, RC=mov reg.lo, [m]
    ps_xor = _is_self_xor_to_full(ps)
    rc_load = _is_byte_load(recomp)
    if ps_xor and rc_load and _LOW_TO_FULL.get(rc_load) == ps_xor:
        # Confirm RC has `and reg, 0xff` in adjacent row.
        if (_is_and_reg_ff(next_recomp) == ps_xor
            or _is_and_reg_ff(prev_recomp) == ps_xor):
            return RuleHint(
                rule="Rule 49",
                summary="zext idiom mismatch (PS uses `xor reg, reg; mov "
                        "reg.lo, [m]`; recomp uses `mov reg.lo, [m]; and "
                        "reg, 0xff`)",
                fix="flip the source: use `(unsigned char)x[i]` or "
                    "`((unsigned char *)x)[i]` (PS-style xor form) vs "
                    "`x[i] & 0xff` (mask form) to match PS.",
            )
    # Case B: PS=mov reg.lo, [m], RC=xor (the mirror).
    rc_xor = _is_self_xor_to_full(recomp)
    ps_load = _is_byte_load(ps)
    if rc_xor and ps_load and _LOW_TO_FULL.get(ps_load) == rc_xor:
        if (_is_and_reg_ff(next_ps) == rc_xor
            or _is_and_reg_ff(prev_ps) == rc_xor):
            return RuleHint(
                rule="Rule 49",
                summary="zext idiom mismatch (recomp uses `xor reg, reg; "
                        "mov reg.lo, [m]`; PS uses `mov reg.lo, [m]; "
                        "and reg, 0xff`)",
                fix="flip the source: use `x[i] & 0xff` (PS's mask form) "
                    "instead of `(unsigned char)x[i]`.",
            )
    return None


# ── Rule 51 - EAX-shortcut absolute load vs generic byte load ────────────────

def detect_rule_51(
    ps: InsnT | None,
    recomp: InsnT | None,
) -> Optional[RuleHint]:
    """PS uses the 5-byte EAX-only `a1 ?? ?? ?? ??` (mov eax, [m])
    absolute load; recomp uses the 6-byte generic byte-load form
    `8a ?? ?? ?? ?? ??` (mov reg8, byte ptr [m]).

    Pattern: same memory operand on both sides, but one side loads
    into `eax` (5 bytes, opcode 0xa1) and the other side loads into
    a byte register (6 bytes, opcode 0x8a with modrm).
    """
    if ps is None or recomp is None:
        return None
    ps_op, rc_op = ps[2][0], recomp[2][0]
    # Detect 0xA1 (mov eax, moffs32) vs 0x8A (mov r8, r/m8).
    if {ps_op, rc_op} != {0xA1, 0x8A}:
        return None
    # Both must be "mov" mnemonic.
    if _mnemonic(ps) != "mov" or _mnemonic(recomp) != "mov":
        return None
    # The 0x8A side must target a byte half-register.
    short_side = ps if ps_op == 0xA1 else recomp
    byte_side = recomp if ps_op == 0xA1 else ps
    byte_ops = [o.strip().lower() for o in _operands(byte_side).split(",", 1)]
    if len(byte_ops) != 2 or byte_ops[0] not in _LOW_TO_FULL:
        return None
    short_name = "PS" if ps_op == 0xA1 else "recomp"
    return RuleHint(
        rule="Rule 51",
        summary=f"absolute-load encoding mismatch ({short_name} uses "
                "5-byte `mov eax, [m]` (opcode A1), other uses 6-byte "
                "`mov reg.lo, byte ptr [m]` (opcode 8A))",
        fix="hoist the masked load into an `int` temp first: "
            "`int v = global & MASK; ((char *)dst)[i] = (char)(v + N);` "
            "forces the EAX-shortcut form.",
    )


# ── Rule 53 - `setne; movzx` boolean materialisation ─────────────────────────

def detect_rule_53(
    ps: InsnT | None,
    recomp: InsnT | None,
) -> Optional[RuleHint]:
    """One side has `setne`/`sete reg8`, the other doesn't.

    PS uses the `setne; ...; and reg, 0xff` materialisation when the
    source wrote `(expr) != 0` explicitly; recomp omits the setne
    when the source wrote bare `expr`.  Surfaces as a diff row where
    one side has `setne reg8` (0F 95) or `sete reg8` (0F 94) and
    the other side has an unrelated instruction.
    """
    SET_MNS = ("setne", "sete", "setz", "setnz")
    ps_mn, rc_mn = _mnemonic(ps), _mnemonic(recomp)
    ps_is_set = ps_mn in SET_MNS
    rc_is_set = rc_mn in SET_MNS
    if ps_is_set == rc_is_set:
        return None
    side = "PS" if ps_is_set else "recomp"
    return RuleHint(
        rule="Rule 53",
        summary=f"boolean materialisation mismatch ({side} uses "
                "`setne; movzx`/`and reg, 0xff` for an explicit "
                "`!= 0` test; other side has bare-expression form)",
        fix="if PS has setne: write `(expr) != 0` (or `!!(expr)` / "
            "`(expr) ? 1 : 0`). If PS doesn't: write bare `expr` "
            "(drop the `!= 0`).",
    )


# NOTE: Rules 92 (goto-fail epilogue funnel), 93 (do/while vs while test
# placement), 94 (||-split vs combined), and 95 (switch dispatch) are
# STRUCTURAL / whole-loop / whole-function patterns.  They were trialled as
# per-row classifiers and rejected: the diff aligner emits `cmp`/`jcc`/`jmp`
# inserts and deletes so pervasively (a do/while signal alone matched 1390 rows
# across the corpus) that any per-row trigger is hopelessly low-precision.
# They are surfaced instead by the source-level Style check
# (c2/commands/style_check.py) and the documented rules in
# docs/watcom-codegen-patterns.md; the byte diff itself is left to the existing
# Rule 9 (jcc flip) / regalloc classifiers.  Do NOT re-add them here without a
# loop/CFG-aware pre-scan that is proven 0-false-positive on the full corpus.


# ── Rule 91 - compound `op=` in-place memory RMW vs expanded load-op-store ──
#
# Front-end proof (OpenWatcom V1, bld/cc/c/cgen2.c + bld/cg/c/cg.c):
#   compound `op=` routes through `CGPreGets` -> builds an O_PRE_GETS node
#   (Unary(O_PRE_GETS, Binary(op,l,r))) - a dedicated read-modify-write IR
#   whose lvalue is evaluated ONCE.  `x = x op y` builds a plain Binary plus
#   a separate assignment, materialising the lvalue twice, so the back-end
#   cannot fold it into a single in-place memory op.  Hence:
#     compound : `op byte/dword [base+idx+disp], imm`   (one insn)
#     expanded : `mov reg,[mem]; op reg,imm; mov [mem],reg` (load-op-store)

# inc/dec are Rule 72's domain (the `++field` counter idiom); Rule 91 covers
# the binary compound operators only.
_RMW_MEM_OPS = frozenset({"add", "sub", "and", "or", "xor"})


# An *indexed* memory operand for Rule 91: `[<base> + <disp>]` (optionally with
# `<size> ptr`), where the base register is NOT a stack pointer.  Rule 91 is
# about indexed array / struct-array lvalues (`figure_list[i].field`), which
# compile to `[index_reg + global_disp32]`.  Plain stack locals (`[esp+4]`,
# `[ebp-8]`) and direct globals (`[disp32]`, a fixed-global field - exempt from
# Rule 91 because both source forms are byte-identical there) are excluded.
_INDEXED_MEM_RE = re.compile(
    r"(?:(byte|word|dword)\s+ptr\s+)?\[\s*(e[abcd]x|esi|edi)\b[^\]]*\]"
)


def _indexed_mem_shape(operand: str) -> tuple[str, str] | None:
    """Return (size, base_reg) if `operand` is an indexed (non-stack) memory
    reference, else None."""
    m = _INDEXED_MEM_RE.search(operand)
    if not m:
        return None
    return (m.group(1) or "", m.group(2))


def _is_mem_dest_rmw(insn: InsnT | None) -> tuple[str, str] | None:
    """If insn is an in-place indexed RMW `<op> [base+disp], <src>`, return
    its (size, base_reg) shape; else None."""
    if insn is None or _mnemonic(insn) not in _RMW_MEM_OPS:
        return None
    dest = _operands(insn).split(",", 1)[0].strip()
    return _indexed_mem_shape(dest)


def _is_mem_load(insn: InsnT | None) -> tuple[str, str] | None:
    """If insn is `mov reg, [base+disp]` (indexed load), return the source's
    (size, base_reg) shape; else None."""
    if insn is None or _mnemonic(insn) != "mov":
        return None
    parts = _operands(insn).split(",", 1)
    if len(parts) != 2:
        return None
    dest, src = parts[0].strip(), parts[1].strip()
    if "[" in dest:
        return None
    return _indexed_mem_shape(src)


def _dest_reg(insn: InsnT | None) -> str:
    return _operands(insn).split(",", 1)[0].strip() if insn else ""


def _mem_operand(operand: str) -> str:
    """Return the `[...]` substring of an operand, or ''."""
    a = operand.find("[")
    b = operand.find("]", a)
    return operand[a:b + 1] if a >= 0 and b > a else ""


def _completes_load_op_store(
    load: InsnT | None, nxt: InsnT | None, nxt2: InsnT | None,
    shape: tuple[str, str],
) -> bool:
    """True if `load` (`mov R, [mem]`) is followed by `<rmwop> R, imm` and a
    `mov [mem], R` store - SAME register R AND the SAME memory address for the
    load and the store.  Requiring load-addr == store-addr is what makes this
    a genuine `x = x op c` self-modify rather than a coincidental load + an
    unrelated store to a different global (the load/store disps are within one
    build, so they are directly comparable - no fixup masking between them)."""
    reg = _dest_reg(load)
    if not reg:
        return False
    load_mem = _mem_operand(_operands(load))
    if not load_mem:
        return False
    # next: <op> reg, imm   (the modify)
    if _mnemonic(nxt) not in _RMW_MEM_OPS:
        return False
    op_parts = _operands(nxt).split(",", 1)
    if len(op_parts) != 2 or op_parts[0].strip() != reg:
        return False
    # next2: mov [mem], reg   (store: same reg, same indexed shape, SAME addr)
    if _mnemonic(nxt2) != "mov":
        return False
    st = _operands(nxt2).split(",", 1)
    if len(st) != 2 or st[1].strip() != reg:
        return False
    store_mem = st[0].strip()
    return (_indexed_mem_shape(store_mem) == shape
            and _mem_operand(store_mem) == load_mem)


def detect_rule_91(
    ps: InsnT | None,
    recomp: InsnT | None,
    next_ps: InsnT | None,
    next2_ps: InsnT | None,
    next_recomp: InsnT | None,
    next2_recomp: InsnT | None,
) -> Optional[RuleHint]:
    """In-place indexed memory RMW on one side vs a complete load-op-store
    sequence on the other - the compound `arr[i].f op= x` vs expanded
    `arr[i].f = arr[i].f op x` divergence (Rule 91).

    The load side must thread a register through `mov R,[m]; op R,imm;
    mov [m],R` (same R, same indexed shape) - this is what distinguishes a
    genuine expanded compound from a coincidental load-vs-RMW alignment in a
    large unrelated diff (shape-matching alone is NOT enough, because masked
    fixup displacements make two different globals look identical).

    PS uses BOTH forms across the codebase, so the hint points whichever way
    matches PS.
    """
    if ps is None or recomp is None:
        return None
    ps_rmw, rc_load = _is_mem_dest_rmw(ps), _is_mem_load(recomp)
    if ps_rmw and rc_load == ps_rmw and _completes_load_op_store(
            recomp, next_recomp, next2_recomp, ps_rmw):
        return RuleHint(
            rule="Rule 91",
            summary="PS in-place memory RMW (`op [mem], imm`); recomp emits "
                    "load-op-store (expanded `x = x op y`)",
            fix="write the compound `arr[i].field op= rhs;` (in-place RMW), "
                "not the expanded `arr[i].field = arr[i].field op rhs;`.",
        )
    rc_rmw, ps_load = _is_mem_dest_rmw(recomp), _is_mem_load(ps)
    if rc_rmw and ps_load == rc_rmw and _completes_load_op_store(
            ps, next_ps, next2_ps, rc_rmw):
        return RuleHint(
            rule="Rule 91",
            summary="recomp in-place memory RMW; PS emits load-op-store "
                    "(PS used the expanded `x = x op y` here)",
            fix="write the expanded `arr[i].field = arr[i].field op rhs;` "
                "(load-op-store) to match PS, not the compound `op=`.",
        )
    return None


# ── Rule 96 - SIB scale fold vs pre-scale (`idx*4` vs `shl`+plain index) ──────
#
# A two-subscript indexed read `arr[X].field[D]` (power-of-two outer stride)
# folds `X*scale` into the addressing-mode SIB byte when X stays unscaled in a
# register: PS emits `mov dst, [base + X*4 + disp]`.  Under register pressure
# the recomp pre-scales X with a `shl` and drops the SIB scale, emitting
# `mov dst, [base + X + disp]` (no `*N`).  Detect the row where PS carries a
# `reg*2/4/8` scale and the recomp's corresponding memory operand has the same
# shape but NO scale (and a `shl` was emitted on the recomp side just before).
# See Rule 96 in docs/watcom-codegen-patterns.md (mid2_line_no_sides_base).

_SIB_SCALE_RE = re.compile(r"\b(e[a-d]x|esi|edi|ebp)\s*\*\s*([248])\b")


def _has_sib_scale(insn: InsnT | None) -> bool:
    return insn is not None and bool(_SIB_SCALE_RE.search(_operands(insn)))


def detect_rule_96(
    ps: InsnT | None,
    recomp: InsnT | None,
    prev_recomp: InsnT | None,
    prev2_recomp: InsnT | None,
) -> Optional[RuleHint]:
    """PS folds `X*scale` into the SIB byte (`[base + X*4 + disp]`); recomp
    pre-scaled X with a nearby `shl` and emits a plain `[base + index + disp]`
    with no scale.  Requires: same mnemonic, both indexed memory, PS has a
    `reg*2/4/8` scale, recomp does NOT, and a `shl reg, 1/2/3` appears on the
    recomp side within the previous two rows (the pre-scale).
    """
    if ps is None or recomp is None:
        return None
    if _mnemonic(ps) != _mnemonic(recomp):
        return None
    ps_ops, rc_ops = _operands(ps), _operands(recomp)
    if "[" not in ps_ops or "[" not in rc_ops:
        return None
    if not _has_sib_scale(ps) or _has_sib_scale(recomp):
        return None
    # The recomp must have pre-scaled via a shl in the preceding 1-2 rows.
    prevs = (prev_recomp, prev2_recomp)
    if not any(_mnemonic(p) == "shl" for p in prevs if p is not None):
        return None
    return RuleHint(
        rule="Rule 96",
        summary="PS folds the array index into the SIB scale (`idx*N`); "
                "recomp pre-scaled it (`shl`+plain `[base+index]`)",
        fix="give the array-index value its own temp and the inner subscript "
            "its own local (`int t = arr_idx; ...; m[t].f[d]`) so Watcom keeps "
            "the index unscaled in a register and folds `*N` into the SIB byte "
            "(Rule 96).",
    )


# ── Rule 99 - narrow (16-bit) vs 32-bit zero-extend of a byte/short value ────
#
# A local holding a byte/short value (e.g. an LHARC bit-buffer shift register)
# zero-extends to 16-bit in PS via a high-byte self-xor (`xor ah, ah`,
# `xor ch, ch`, `xor dh, dh`, `xor bh, bh`) when the surrounding arithmetic is
# 16-bit; an `int` local makes Watcom widen everything to 32-bit and zero-extend
# the byte with `and e<reg>x, 0xff` instead.  Detect PS's high-byte self-xor
# opposite a recomp `and e<reg>, 0xff` on the same row.  See Rule 99 in
# docs/watcom-codegen-patterns.md (GetBit/GetByte, pump.c).

# high-byte reg -> its enclosing 32-bit register (for the full-xor variant)
_HI_BYTE_TO_E = {"ah": "eax", "bh": "ebx", "ch": "ecx", "dh": "edx"}
_HI_BYTE_REGS = frozenset(_HI_BYTE_TO_E)
_AND_0xFF_RE = re.compile(r"^(e[a-d]x|esi|edi)\s*,\s*0xff$")


def _hibyte_self_xor_reg(insn: InsnT | None) -> str | None:
    """Return the high-byte register if insn is `xor <hi8>, <hi8>`, else None."""
    if insn is None or _mnemonic(insn) != "xor":
        return None
    parts = [p.strip() for p in _operands(insn).split(",", 1)]
    if len(parts) == 2 and parts[0] == parts[1] and parts[0] in _HI_BYTE_REGS:
        return parts[0]
    return None


def _is_hibyte_self_xor(insn: InsnT | None) -> bool:
    return _hibyte_self_xor_reg(insn) is not None


def _is_and_byte_mask(insn: InsnT | None) -> bool:
    return insn is not None and _mnemonic(insn) == "and" \
        and bool(_AND_0xFF_RE.match(_operands(insn).strip()))


def _is_full_self_xor(insn: InsnT | None, ereg: str | None = None) -> bool:
    """`xor eREG, eREG` (full 32-bit clear); if ereg given, must match it."""
    if insn is None or _mnemonic(insn) != "xor":
        return False
    parts = [p.strip() for p in _operands(insn).split(",", 1)]
    if len(parts) != 2 or parts[0] != parts[1]:
        return False
    if parts[0] not in _HI_BYTE_TO_E.values():
        return False
    return ereg is None or parts[0] == ereg


def detect_rule_99(
    ps: InsnT | None,
    recomp: InsnT | None,
) -> Optional[RuleHint]:
    """PS zero-extends a byte/short value to 16-bit via a high-byte self-xor
    (`xor ah, ah`); recomp widens to 32-bit with `and e<reg>, 0xff`.  Points
    whichever way matches PS - if PS is the narrow form, the value's `int`
    local should be `short`.
    """
    if ps is None or recomp is None:
        return None
    ps_hi = _hibyte_self_xor_reg(ps)
    if ps_hi is not None and (_is_and_byte_mask(recomp)
                              or _is_full_self_xor(recomp, _HI_BYTE_TO_E[ps_hi])):
        return RuleHint(
            rule="Rule 99",
            summary="PS zero-extends in 16-bit (`xor <hi8>, <hi8>`); recomp "
                    "widens to 32-bit (`and e<reg>, 0xff` / `xor e<reg>, e<reg>`)",
            fix="declare the byte/short value's local as `short` (not `int`) "
                "so Watcom keeps the arithmetic 16-bit and uses the narrow "
                "zero-extend (Rule 99).",
        )
    if _is_hibyte_self_xor(recomp) and _is_and_byte_mask(ps):
        return RuleHint(
            rule="Rule 99",
            summary="recomp zero-extends in 16-bit; PS widens to 32-bit "
                    "(`and e<reg>, 0xff`) - PS used an `int`-width value here",
            fix="widen the local to `int` to match PS's 32-bit zero-extend "
                "(Rule 99, reverse direction).",
        )
    return None


# ── Rule 62 - `x + x` lowers to LEA; `x << 1` lowers to mov+add ──────────────

def _is_lea_self_double(insn: InsnT | None) -> tuple[str, str] | None:
    """If `insn` is `lea reg, [src + src]`, return (dst, src)."""
    if insn is None or _mnemonic(insn) != "lea":
        return None
    ops = _operands(insn).replace(" ", "").lower()
    m = re.match(r"(e[abcd]x|esi|edi|ebp),\[(e[abcd]x|esi|edi|ebp)\+\2\]$",
                  ops)
    if not m:
        return None
    return (m.group(1), m.group(2))


def _is_self_add(insn: InsnT | None) -> str | None:
    """If `insn` is `add reg, reg` (self-add), return the register."""
    if insn is None or _mnemonic(insn) != "add":
        return None
    ops = [o.strip().lower() for o in _operands(insn).split(",")]
    if len(ops) != 2 or ops[0] != ops[1]:
        return None
    if ops[0] not in _FULL_REGS:
        return None
    return ops[0]


def detect_rule_62(
    ps: InsnT | None,
    recomp: InsnT | None,
    next_ps: InsnT | None,
    next_recomp: InsnT | None,
    prev_ps: InsnT | None,
    prev_recomp: InsnT | None,
) -> Optional[RuleHint]:
    """One side has `lea reg, [src+src]` (3 b); other has
    `mov reg, src; add reg, reg` (4-5 b) for the same doubling.

    Detection: a diff row where one side is the `lea reg, [src+src]`
    and the other side is either the `mov reg, src` or the
    `add reg, reg` of the 2-instruction sequence (with the
    complementary instruction appearing in the adjacent row).
    """
    if ps is None or recomp is None:
        return None
    # Case A: one side is the LEA, the other side is `add reg, reg`
    # (the mov was elided / absorbed, leaving only the self-add at
    # the diff row).
    ps_lea = _is_lea_self_double(ps)
    rc_lea = _is_lea_self_double(recomp)
    ps_add = _is_self_add(ps)
    rc_add = _is_self_add(recomp)

    if ps_lea and rc_add and _reg_family(ps_lea[0]) == rc_add:
        return RuleHint(
            rule="Rule 62",
            summary="doubling-encoding mismatch (PS uses 3-byte `lea reg, "
                    "[src+src]`; recomp uses `mov reg, src; add reg, reg` "
                    "- 1-byte cascade trigger)",
            fix="PS uses the LEA form: write the doubling as `x + x` "
                "(the literal addition). NOTE: `x * 2` / `2 * x` do NOT "
                "produce LEA - they lower to `mov; add` like `x << 1`.",
        )
    if rc_lea and ps_add and _reg_family(rc_lea[0]) == ps_add:
        return RuleHint(
            rule="Rule 62",
            summary="doubling-encoding mismatch (recomp uses 3-byte `lea "
                    "reg, [src+src]`; PS uses `mov reg, src; add reg, reg` "
                    "- 1-byte cascade trigger)",
            fix="PS uses the mov+add form: write the doubling as `x << 1`, "
                "`x * 2`, or `2 * x` (any multiply/shift doubling). "
                "Only the literal `x + x` lowers to LEA.",
        )
    return None


# ── Rule 20 - scaled-index post-loop vs absolute terminal disp ──────────────

_SIB_SCALED_RE = re.compile(r"\[e[a-z]+\*[1248]\b")
_ABS_DISP_RE   = re.compile(r"\[0x[0-9a-f]+\]")


def detect_rule_20(
    ps: InsnT | None,
    recomp: InsnT | None,
) -> Optional[RuleHint]:
    """One side uses `[reg*K + disp]` (scaled post-loop index), other
    uses an absolute `[disp]` (terminal value baked in).

    Trigger: same mnemonic on both sides, both sides have a memory
    operand, but one side's operand contains a SIB-scaled register
    (`[reg*1/2/4/8]`) and the other's is a plain absolute
    displacement (`[0xABCD]`).
    """
    if ps is None or recomp is None:
        return None
    if _mnemonic(ps) != _mnemonic(recomp):
        return None
    ps_ops = _operands(ps).lower()
    rc_ops = _operands(recomp).lower()
    ps_scaled = bool(_SIB_SCALED_RE.search(ps_ops))
    rc_scaled = bool(_SIB_SCALED_RE.search(rc_ops))
    if ps_scaled == rc_scaled:
        return None
    ps_abs = bool(_ABS_DISP_RE.search(ps_ops))
    rc_abs = bool(_ABS_DISP_RE.search(rc_ops))
    # Scaled side must NOT be the absolute side; absolute side must
    # NOT be scaled.  Confirm the other side actually uses an absolute
    # displacement (rather than e.g. `[reg + disp]`).
    if ps_scaled and not rc_abs:
        return None
    if rc_scaled and not ps_abs:
        return None
    scaled_side = "PS" if ps_scaled else "recomp"
    return RuleHint(
        rule="Rule 20",
        summary=f"scaled-vs-absolute index ({scaled_side} uses `[reg*K + "
                "disp]`; other uses bare `[disp]` - loop counter terminal "
                "value was hoisted vs baked into the address)",
        fix="if PS is scaled: use the loop counter post-loop as the index "
            "(e.g. `arr[i]` after `for(i=0;i<N;i++)` falls through with "
            "`i==N`).  If PS is absolute: write the terminal index as a "
            "named constant or assign-then-use.",
    )


# ── Rule 35 - byte-by-byte LE word load order ──────────────────────────────

def _find_rule_35_pairs(
    rows: list[tuple[InsnT | None, InsnT | None, bool]],
) -> dict[int, str]:
    """Find adjacent same-side insertion pairs of
    `mov reg1, reg2` + `xor reg2, reg2` - the Rule 35 "copy-then-clear"
    sequence Watcom emits when the high-first source order was used.

    PS uses low-first source (`buf[k] + (buf[k+1] << 8)`), so its
    high byte stays in `edx` until the combine; recomp source spelled
    `(buf[k+1] << 8) + buf[k]` (high-first), forcing Watcom to copy
    `edx → edi` and clear `edx` for the next byte load - 4 extra
    bytes per packed-int slot.
    """
    out: dict[int, str] = {}
    for i in range(len(rows) - 1):
        ps1, rc1, diff1 = rows[i]
        ps2, rc2, diff2 = rows[i + 1]
        if not (diff1 and diff2):
            continue
        # RC-only insertion pair
        if ps1 is None and ps2 is None and rc1 is not None and rc2 is not None:
            if _is_rule_35_mov_xor_pair(rc1, rc2):
                out[i] = "recomp"
                continue
        # PS-only deletion pair (rare)
        if rc1 is None and rc2 is None and ps1 is not None and ps2 is not None:
            if _is_rule_35_mov_xor_pair(ps1, ps2):
                out[i] = "PS"
    return out


def _is_rule_35_mov_xor_pair(a: InsnT, b: InsnT) -> bool:
    """Returns True iff `a` is `mov reg1, reg2` and `b` is `xor reg2, reg2`."""
    if _mnemonic(a) != "mov" or _mnemonic(b) != "xor":
        return False
    a_ops = [o.strip().lower() for o in _operands(a).split(",")]
    b_ops = [o.strip().lower() for o in _operands(b).split(",")]
    if len(a_ops) != 2 or len(b_ops) != 2:
        return False
    if a_ops[0] not in _FULL_REGS or a_ops[1] not in _FULL_REGS:
        return False
    if b_ops[0] != b_ops[1] or b_ops[0] not in _FULL_REGS:
        return False
    return a_ops[1] == b_ops[0] and a_ops[0] != a_ops[1]


def detect_rule_35(
    row_idx: int,
    ps: InsnT | None,
    recomp: InsnT | None,
    rule_35_pairs: dict[int, str],
) -> Optional[RuleHint]:
    """One side has `mov reg1, reg2; xor reg2, reg2` insertion pair -
    the high-first source-order byte-load codegen.
    """
    side = rule_35_pairs.get(row_idx)
    if side is None:
        return None
    insn = recomp if side == "recomp" else ps
    a_ops = [o.strip().lower() for o in _operands(insn).split(",")]
    return RuleHint(
        rule="Rule 35",
        summary=f"{side} has `mov {a_ops[0]}, {a_ops[1]}; xor {a_ops[1]}, "
                f"{a_ops[1]}` byte-load reorder pair - high-first source "
                "order forces an extra copy+clear (4 b per packed-int slot)",
        fix="flip the C source: write `buf[k] + (buf[k+1] << 8)` "
            "(low-first) instead of `(buf[k+1] << 8) + buf[k]` for "
            "packed little-endian byte loads.",
    )


# ── Rule 49b - xor+mov.lo zext idiom asymmetric pair insertion ────────────────

def _find_rule_49b_pairs(
    rows: list[tuple[InsnT | None, InsnT | None, bool]],
) -> dict[int, str]:
    """Find adjacent insert (or delete) pairs of
    `xor reg, reg` + `mov reg.lo, byte ptr [...]` on a single side.

    When PS uses the *load-then-mask* zext idiom (`mov reg.lo, [m];
    and reg, 0xff`) and the recomp source picked the cast form
    (`(unsigned char)x`), the recomp emits the *xor-then-load* idiom
    instead.  In a diffing function these two RC-only rows appear as
    a pair of insertions (and the PS counterpart appears as a pair
    of deletions elsewhere because the SequenceMatcher can't align
    them).  Detect those insertion pairs and flag them.

    Returns dict mapping the row-index of the *xor* row → side
    ("PS" for delete pair, "recomp" for insert pair).
    """
    out: dict[int, str] = {}
    for i in range(len(rows) - 1):
        ps1, rc1, diff1 = rows[i]
        ps2, rc2, diff2 = rows[i + 1]
        if not (diff1 and diff2):
            continue
        # RC-only insertion pair?
        if ps1 is None and ps2 is None and rc1 is not None and rc2 is not None:
            xor_reg = _is_self_xor_to_full(rc1)
            load_reg = _is_byte_load(rc2)
            if xor_reg and load_reg and _LOW_TO_FULL.get(load_reg) == xor_reg:
                out[i] = "recomp"
                continue
        # PS-only deletion pair?
        if rc1 is None and rc2 is None and ps1 is not None and ps2 is not None:
            xor_reg = _is_self_xor_to_full(ps1)
            load_reg = _is_byte_load(ps2)
            if xor_reg and load_reg and _LOW_TO_FULL.get(load_reg) == xor_reg:
                out[i] = "PS"
    return out


def detect_rule_49b(
    row_idx: int,
    ps: InsnT | None,
    recomp: InsnT | None,
    rule_49b_pairs: dict[int, str],
) -> Optional[RuleHint]:
    """One side has an asymmetric `xor reg, reg; mov reg.lo, [...]`
    pair insertion - the cast-form zext idiom of Rule 49.
    """
    side = rule_49b_pairs.get(row_idx)
    if side is None:
        return None
    insn = recomp if side == "recomp" else ps
    reg = _is_self_xor_to_full(insn)
    if reg is None:
        return None
    return RuleHint(
        rule="Rule 49b",
        summary=f"{side} has asymmetric `xor {reg}, {reg}; mov "
                f"{reg[1:]+'l' if reg.endswith('x') else reg}.lo, [...]` "
                "zext idiom pair - cast-form `(unsigned char)x` codegen",
        fix="flip the C source zext spelling: if recomp has the pair, "
            "switch from `(unsigned char)x` to `x & 0xff` to force the "
            "load-then-mask form PS uses.  If PS has the pair, do the "
            "reverse.",
    )


# ── Rule 84 - byte-temp reuse: `mov dl,[m]; and edx,0xff` vs `xor edx,edx; mov dl,[m]` ─

def _find_rule_84_rows(
    rows: list[tuple[InsnT | None, InsnT | None, bool]],
) -> dict[int, str]:
    """Locate diff rows that belong to a Rule 84 byte-temp-reuse cascade.

    Pattern (PS uses the `mov+and` in-place Z1to4 form, RC uses the
    `xor+mov` clear-first form):

        diff row i:    PS=None / RC=`xor reg, reg`             (insert)
        equal row j:   both = `mov reg.lo, byte ptr [m]`       (aligned)
        diff row k:    PS=`and reg, 0xff` / RC=None            (delete)

    SequenceMatcher aligns the `mov reg.lo, [m]` as equal because both
    sides emit byte-identical loads; only the surrounding widening
    differs.  That leaves the xor on RC-only insertion rows and the
    `and reg, 0xff` on PS-only deletion rows, *one row apart from any
    `xor + mov.lo` pair that Rule 49b would catch*.

    Distinguishes Rule 84 (multi-read byte-temp cascade, fixed by a
    named `unsigned char x;` reused across reads) from a single Rule
    49 alignment flip (fixed by `(unsigned char)` cast vs `& 0xff`):
    the cascade must fire ≥ 2 times in the same register family.

    Returns dict mapping each contributing diff-row index → side
    ("PS" for the deleted `and`, "recomp" for the inserted `xor`).
    """
    from collections import defaultdict

    # Helpers: "equal byte load" = both sides have `mov reg.lo, [m]`
    # for the same low register.  Tracked by family.
    def _equal_byte_load_fam(
        row: tuple[InsnT | None, InsnT | None, bool]
    ) -> str | None:
        ps, rc, is_diff = row
        if is_diff or ps is None or rc is None:
            return None
        p_low = _is_byte_load(ps)
        r_low = _is_byte_load(rc)
        if p_low and p_low == r_low:
            return _LOW_TO_FULL.get(p_low)
        return None

    # For each candidate lone-xor insert / lone-and delete, the
    # corresponding equal `mov reg.lo, [m]` must be ADJACENT in the
    # diff alignment - within +/-1 row, with no diffing test/jcc
    # between.  This filters out branch-separated reads (e.g. an
    # if-else-if chain where each branch widens its own byte load)
    # which look like the pattern by raw count but where the
    # source-level byte-temp-reuse lever does NOT apply.
    def _xor_has_adjacent_mov(
        idx: int, reg: str, side: str
    ) -> bool:
        # xor on `side` is followed by equal mov reg.lo, [m] of
        # `reg` within the next 1 row.
        for j in (idx + 1,):
            if 0 <= j < len(rows):
                fam = _equal_byte_load_fam(rows[j])
                if fam == reg:
                    return True
        return False

    def _and_has_adjacent_mov(
        idx: int, reg: str, side: str
    ) -> bool:
        # `and reg, 0xff` on `side` is preceded by equal mov reg.lo,
        # [m] of `reg` within the previous 1 row (no intervening
        # test/jcc - those break the "in-place widening" pattern).
        for j in (idx - 1,):
            if 0 <= j < len(rows):
                fam = _equal_byte_load_fam(rows[j])
                if fam == reg:
                    return True
        return False

    # Per-register family, collect candidate xor inserts and and deletes
    # that satisfy the adjacency criterion.
    rc_xor_by_reg: dict[str, list[int]] = defaultdict(list)
    ps_and_by_reg: dict[str, list[int]] = defaultdict(list)
    ps_xor_by_reg: dict[str, list[int]] = defaultdict(list)
    rc_and_by_reg: dict[str, list[int]] = defaultdict(list)

    for i, (ps, rc, is_diff) in enumerate(rows):
        if not is_diff:
            continue
        # Lone xor insert (RC-only)?
        if ps is None and rc is not None:
            reg = _is_self_xor_to_full(rc)
            if reg and _xor_has_adjacent_mov(i, reg, "recomp"):
                rc_xor_by_reg[reg].append(i)
            elif _is_and_reg_ff(rc):
                a = _is_and_reg_ff(rc)
                if a and _and_has_adjacent_mov(i, a, "recomp"):
                    rc_and_by_reg[a].append(i)
        # Lone and-0xff delete (PS-only)?
        elif rc is None and ps is not None:
            reg = _is_and_reg_ff(ps)
            if reg and _and_has_adjacent_mov(i, reg, "PS"):
                ps_and_by_reg[reg].append(i)
            else:
                x = _is_self_xor_to_full(ps)
                if x and _xor_has_adjacent_mov(i, x, "PS"):
                    ps_xor_by_reg[x].append(i)

    out: dict[int, str] = {}
    # Forward (PS=and-form, RC=xor-form): want to flip RC to PS-style.
    # Fire when there is at least one matching xor-insert AND
    # at least one matching and-delete for the same register family.
    # The adjacency check on the candidates already filtered out the
    # branch-separated false positives; the count match here ensures
    # the two halves of the cascade actually come from the same
    # source-level mismatch (insert + delete on different sides).
    for reg, xor_rows in rc_xor_by_reg.items():
        and_rows = ps_and_by_reg.get(reg, [])
        if xor_rows and and_rows:
            for idx in xor_rows:
                out[idx] = "recomp"
            for idx in and_rows:
                out[idx] = "PS"
    # Mirror (PS=xor-form, RC=and-form): rare; suppress unless ≥ 2 of
    # each so we don't flag noise.
    for reg, xor_rows in ps_xor_by_reg.items():
        and_rows = rc_and_by_reg.get(reg, [])
        if len(xor_rows) >= 2 and len(and_rows) >= 2:
            for idx in xor_rows:
                out[idx] = "PS"
            for idx in and_rows:
                out[idx] = "recomp"
    return out


def detect_rule_84(
    row_idx: int,
    ps: InsnT | None,
    recomp: InsnT | None,
    rule_84_rows: dict[int, str],
) -> Optional[RuleHint]:
    """Multi-read byte-temp cascade: PS reuses a single named byte
    local across ≥ 2 sequential reads, RC emits per-read clear-and-load.

    Fires only when the cascade has ≥ 2 lone `xor reg, reg` inserts
    on one side AND ≥ 2 lone `and reg, 0xff` deletes on the other
    side AND ≥ 2 equal `mov reg.lo, [m]` aligned rows (all same
    register family).  Single-instance flips are handled by Rule 49 /
    49b instead.

    See ``docs/watcom-codegen-patterns.md`` Rule 84 for the source
    lever (declare `unsigned char x;` once, reuse it across all byte
    reads).
    """
    if row_idx not in rule_84_rows:
        return None
    side = rule_84_rows[row_idx]
    insn = recomp if side == "recomp" else ps
    reg_xor = _is_self_xor_to_full(insn)
    reg_and = _is_and_reg_ff(insn)
    reg = reg_xor or reg_and
    if reg is None:
        return None
    return RuleHint(
        rule="Rule 84",
        summary=(
            f"byte-temp cascade ({reg}): PS reuses one named `unsigned "
            "char` local across multiple sequential byte reads, recomp "
            "emits a fresh `xor reg, reg; mov reg.lo, [m]` pair per read"
        ),
        fix=(
            "declare a single `unsigned char x;` at the top of the body "
            "and reuse it across each byte read: `x = FIELD_A(p); if (x "
            "< K) { x = FIELD_B(p); if ((x & M) != 0) { x = FIELD_C(p); "
            "... } }`.  The reused local pins the value to a stable "
            "register; Watcom's rCLRHI_R then emits the and-form Z1to4 "
            "that PS uses.  See Rule 84 in docs/watcom-codegen-patterns.md."
        ),
    )


# ── Rule 10 - staged global RMW vs single fused store ───────────────────────

_MEM_RMW_MNEMONICS = ("add", "sub", "or", "and", "xor")


def _mem_target(insn: InsnT | None) -> str | None:
    """If `insn` is a RMW to a non-trivial memory operand, return the
    memory text.

    Recognises `add [m], reg`, `or [m], reg`, ... - 32-bit RMW only.
    Returns the bracketed memory expression (lower-cased, whitespace-
    stripped) or None.

    Excludes plain `[reg]` (2-byte instructions) and `byte ptr [...]`
    forms.  Those decode out of fixup-masked null-byte data and would
    cause massive false-positive cascades.  A genuine global RMW
    always uses a disp32 absolute address or `[reg + disp32]` form,
    which requires the instruction to be ≥ 6 bytes long.
    """
    if insn is None:
        return None
    mn = _mnemonic(insn)
    if mn not in _MEM_RMW_MNEMONICS:
        return None
    # Instruction size filter: real disp32 RMW is ≥ 6 bytes; reject
    # plain `[reg]` forms (2-byte) which are almost always data noise.
    if len(insn[2]) < 4:
        return None
    ops = _operands(insn).strip().lower()
    # Exclude byte-pointer RMW (`add byte ptr [...]`) - these are also
    # mostly data-decoded-as-code artefacts.
    if ops.startswith("byte ptr "):
        return None
    # Allow `word ptr ` / `dword ptr ` prefixes for explicit 32-bit
    # disp32 forms.
    m = re.match(r"(?:dword ptr |word ptr )?\[([^\]]+)\]", ops)
    if not m:
        return None
    mem = m.group(1).replace(" ", "")
    # The memory expression must contain a hex literal (absolute
    # address or non-zero displacement) - plain `[reg]` is excluded
    # by the size filter above, but `[reg+reg]` (no disp) could
    # still slip through and is also suspicious.  Real RMW to a
    # global indexes via `[reg*4 + disp32]` or `[disp32]`.
    if "0x" not in mem:
        return None
    return mem


def _find_rule_10_excess(
    rows: list[tuple[InsnT | None, InsnT | None, bool]],
) -> dict[int, str]:
    """Identify rows where Rule 10 (staged global RMW) fires.

    Count `<op> [m], reg` instructions per side, grouped by memory
    target.  When PS has 2+ writes to the same global that RC
    collapsed into one (or vice versa), the excess rows are
    genuine Rule 10 hits.  Like Rule 44, suppresses layout-shift
    artefacts where both sides have matching counts.
    """
    from collections import defaultdict
    ps_by_mem: dict[str, list[int]] = defaultdict(list)
    rc_by_mem: dict[str, list[int]] = defaultdict(list)
    for i, (ps, rc, is_diff) in enumerate(rows):
        if not is_diff:
            continue
        pm = _mem_target(ps)
        rm = _mem_target(rc)
        if pm:
            ps_by_mem[pm].append(i)
        if rm:
            rc_by_mem[rm].append(i)
    out: dict[int, str] = {}
    for mem in set(ps_by_mem) | set(rc_by_mem):
        p_list = ps_by_mem.get(mem, [])
        r_list = rc_by_mem.get(mem, [])
        # Only fire when one side has 2+ writes and the other has 0
        # - the rule is about "PS staged multiple updates that RC
        # fused", so we want a clear asymmetry, not a layout shift.
        if len(p_list) >= 2 and len(r_list) == 0:
            for idx in p_list:
                out[idx] = "PS"
        elif len(r_list) >= 2 and len(p_list) == 0:
            for idx in r_list:
                out[idx] = "recomp"
    return out


def detect_rule_10(
    row_idx: int,
    ps: InsnT | None,
    recomp: InsnT | None,
    rule_10_excess: dict[int, str],
) -> Optional[RuleHint]:
    """One side has 2+ `<op> [global], reg` writes; the other has
    none (the writes were fused into a single accumulator + store).
    """
    side = rule_10_excess.get(row_idx)
    if side is None:
        return None
    insn = ps if side == "PS" else recomp
    mn = _mnemonic(insn)
    mem = _mem_target(insn)
    if mem is None:
        return None
    return RuleHint(
        rule="Rule 10",
        summary=f"{side} has staged `{mn} [{mem}], reg` RMW vs single "
                "fused accumulator-then-store on the other side",
        fix="if PS has staged form: write each update as a separate "
            "`g = ...; g += ...; g += ...;` statement.  If PS has the "
            "fused form: combine into one `g = a + b + c;` expression.",
    )


# ── Rule 35a - `+` not `|` for packed-byte combine ─────────────────────────

def detect_rule_35a(
    ps: InsnT | None,
    recomp: InsnT | None,
) -> Optional[RuleHint]:
    """PS has `add reg, reg`; recomp has `or reg, reg` with same
    operands (or vice versa).

    Distinctive in a single opcode byte (0x01 add r/m32, r32 vs
    0x09 or r/m32, r32) and arises when the C source picked `|`
    instead of `+` (or vice-versa) for combining a low byte with a
    shifted high byte.
    """
    if ps is None or recomp is None:
        return None
    ps_mn, rc_mn = _mnemonic(ps), _mnemonic(recomp)
    if {ps_mn, rc_mn} != {"add", "or"}:
        return None
    # Operands must match exactly (same register pair).
    if _operands(ps).strip().lower() != _operands(recomp).strip().lower():
        return None
    ps_is_add = ps_mn == "add"
    return RuleHint(
        rule="Rule 35a",
        summary=f"combine-op mismatch (PS uses `{ps_mn}`, recomp uses "
                f"`{rc_mn}` for the same operand pair - 1-byte opcode "
                "diff that cascades through subsequent regalloc)",
        fix="use `+` (PS form) instead of `|` for packed-byte "
            "combines: `lo + (hi << 8)`, not `lo | (hi << 8)`."
            if ps_is_add else
            "use `|` (PS form) instead of `+` for this combine.",
    )


# ── Byte-register identity swap (regalloc noise) ─────────────────
#
# Same mnemonic, same memory operand (modulo fixup), but one side uses
# a different byte register (e.g. bh vs dh, cl vs al).  Do NOT assume a
# reorder lever here: a byte swap has FOUR distinct causes (the `Byte-seat:`
# verdict in decomp-verify -v classifies which) -- collateral to a dword
# tie (reorderable), Rule 126 AL-squat masking (int-widen), Rule 127
# rover-seated CSE (de-name), or Rule 133 inert byte tie (IRREDUCIBLE: the
# byte tie-break is dead, so reordering provably cannot move it).  See
# byte_seat_hints.py and watcom10.0a repo docs/wcc386-re/regalloc-model.md byte seating.

_BYTE_REGS = frozenset({"al", "ah", "bl", "bh", "cl", "ch", "dl", "dh"})


def _insn_overlaps_fixup(insn: InsnT, abs_base: int, fix: set[int]) -> bool:
    rel_off, _size, raw, _asm = insn
    return any((abs_base + rel_off + i) in fix for i in range(len(raw)))


def detect_byte_reg_swap(
    ps: InsnT | None,
    recomp: InsnT | None,
    ps_abs_base: int = 0,
    recomp_abs_base: int = 0,
    ps_fix: set[int] | None = None,
    recomp_fix: set[int] | None = None,
) -> Optional[RuleHint]:
    """Both sides emit the same mnemonic and the same operand structure,
    differing only in which byte register is used (e.g. `mov [m], bh`
    vs `mov [m], dh`, or `xor bh, bh` vs `xor dh, dh`).

    Numeric operand mismatches are accepted when both instructions overlap
    fixup bytes; this covers `mov [array+field], cl` vs `mov [array+field], bh`
    rows where PS and RC have different relocated absolute addresses.

    Register assignment follows first-use order (Rule 28a); reorder the
    competing values' first uses where the source allows.
    """
    if ps is None or recomp is None:
        return None
    ps_mn = _mnemonic(ps)
    rc_mn = _mnemonic(recomp)
    if ps_mn != rc_mn:
        return None
    pt = _TOKEN_RE_R28.findall(ps[3].lower())
    rt = _TOKEN_RE_R28.findall(recomp[3].lower())
    if len(pt) != len(rt):
        return None
    fixup_ok = (
        ps_fix is not None and recomp_fix is not None
        and _insn_overlaps_fixup(ps, ps_abs_base, ps_fix)
        and _insn_overlaps_fixup(recomp, recomp_abs_base, recomp_fix)
    )
    swap_count = 0
    ps_breg = rc_breg = ""
    for a, b in zip(pt, rt):
        if a == b:
            continue
        if a in _BYTE_REGS and b in _BYTE_REGS:
            swap_count += 1
            ps_breg, rc_breg = a, b
            continue
        if _is_numeric_token(a) and _is_numeric_token(b) and fixup_ok:
            continue
        return None  # non-byte-register, non-fixup difference
    if swap_count == 0:
        return None
    # Allow up to 2 swaps (e.g. `xor bh, bh` vs `xor dh, dh` has 2).
    if swap_count > 2:
        return None
    return RuleHint(
        rule="Byte-reg swap",
        summary=(
            f"byte-register identity swap (PS uses `{ps_breg}`, "
            f"recomp uses `{rc_breg}`)"
        ),
        fix=(
            "byte-register identity swap -- see the `Byte-seat:` verdict "
            "(decomp-verify -v) for the per-function cause + lever: CASE A "
            "collateral to a dword/word tie (Rule 28a/115/123, reorderable); "
            "B AL-squat masking (Rule 126 int-widen); C rover-seated CSE "
            "(Rule 127 de-name); or D inert byte tie (Rule 133 -- the byte "
            "tie-break is DEAD, regalloc.c:855-858, so it is IRREDUCIBLE: do "
            "NOT reorder/decl-swap/permute).  watcom10.0a repo docs/wcc386-re/regalloc-model.md "
            "byte-register seating."
        ),
    )


# ── General register identity swap (regalloc noise) ───────────────
#
# Same as Byte-reg swap but for full/sub-word general registers.  This is
# intentionally lower priority than all numbered/actionable rules and lower
# priority than Byte-reg swap: it classifies residual rows that are pure
# allocator identity choices (eax↔ebx, edx↔ebx, etc.) with no opcode or
# layout difference.

_ALL_GPR_FORMS: dict[str, tuple[str, ...]] = {
    "eax": ("eax", "ax", "al", "ah"),
    "ebx": ("ebx", "bx", "bl", "bh"),
    "ecx": ("ecx", "cx", "cl", "ch"),
    "edx": ("edx", "dx", "dl", "dh"),
    "esi": ("esi", "si"),
    "edi": ("edi", "di"),
    "ebp": ("ebp", "bp"),
    "esp": ("esp", "sp"),
}
_FORM_TO_FULL = {form: full for full, forms in _ALL_GPR_FORMS.items() for form in forms}


def _same_reg_width(a: str, b: str) -> bool:
    fa = _FORM_TO_FULL.get(a)
    fb = _FORM_TO_FULL.get(b)
    if fa is None or fb is None:
        return False
    return _ALL_GPR_FORMS[fa].index(a) == _ALL_GPR_FORMS[fb].index(b)


def detect_reg_identity_swap(
    ps: InsnT | None,
    recomp: InsnT | None,
    ps_abs_base: int = 0,
    recomp_abs_base: int = 0,
    ps_fix: set[int] | None = None,
    recomp_fix: set[int] | None = None,
) -> Optional[RuleHint]:
    """Same mnemonic and operand structure, differing only in register
    identity (e.g. `mov eax, edx` vs `mov ebx, edx`, or an indexed mem-op
    using `edx + ebx*4` vs `ebx + edx*4`).  Numeric operand mismatches are
    allowed only when both rows overlap fixups.
    """
    if ps is None or recomp is None:
        return None
    if _mnemonic(ps) != _mnemonic(recomp):
        return None
    pt = _TOKEN_RE_R28.findall(ps[3].lower())
    rt = _TOKEN_RE_R28.findall(recomp[3].lower())
    if len(pt) != len(rt):
        return None
    fixup_ok = (
        ps_fix is not None and recomp_fix is not None
        and _insn_overlaps_fixup(ps, ps_abs_base, ps_fix)
        and _insn_overlaps_fixup(recomp, recomp_abs_base, recomp_fix)
    )
    swaps: set[tuple[str, str]] = set()
    for a, b in zip(pt, rt):
        if a == b:
            continue
        if _same_reg_width(a, b):
            swaps.add((_FORM_TO_FULL[a], _FORM_TO_FULL[b]))
            continue
        if _is_numeric_token(a) and _is_numeric_token(b) and fixup_ok:
            continue
        return None
    if not swaps or len(swaps) > 2:
        return None
    # Avoid re-classifying byte-only cases; Byte-reg swap is more specific.
    if all(a in _BYTE_REGS and b in _BYTE_REGS for a, b in zip(pt, rt) if a != b):
        return None
    pairs = ", ".join(f"{a}↔{b}" for a, b in sorted(swaps))

    # Discriminate layer-4 (op-DIRECTION / accumulator choice) from layer-3
    # (assignment swap).  When the mnemonic is a COMMUTATIVE binary op and
    # the two sides use the SAME multiset of register operands (just
    # reordered as dst/src), both sides ASSIGNED the same registers - only
    # which operand became the result differs.  That is instruction
    # selection / CountRegMoves (layer 4), NOT the last-use tie-break, and
    # is NOT fixable by reordering uses (see restore_picture_part; proof in
    # docs/codegen-experiments/regalloc-temps.py).
    _COMMUTATIVE = {"add", "adc", "or", "xor", "and", "imul", "lea"}
    ps_regs = sorted(t for t in pt[1:] if t in _FORM_TO_FULL)
    rc_regs = sorted(t for t in rt[1:] if t in _FORM_TO_FULL)
    if _mnemonic(ps) in _COMMUTATIVE and ps_regs == rc_regs and ps_regs:
        return RuleHint(
            rule="Reg swap",
            summary=f"op-direction / accumulator choice ({pairs})",
            fix=(
                "LAYER 4 (NOT last-use): both sides assign the same registers; "
                "only which commutative operand becomes the result differs "
                "(CountRegMoves / instruction selection).  This is the "
                "restore_picture_part residue class - reordering source uses "
                "does NOT move it.  See regalloc-temps.py."
            ),
        )

    return RuleHint(
        rule="Reg swap",
        summary=f"register identity swap ({pairs})",
        fix=(
            "equal-savings layer-3 tie-break.  Two source levers: "
            "(a) Rule 28a -- commute / move the deciding use so the right "
            "value is referenced first (worked: change_citizen_targs; in "
            "`A op B` the LATER operand takes the higher reg); (b) Rule 115 "
            "-- swap the two tied locals' DECLARATION order (when the use "
            "is pinned by semantics; worked: show_help_page).  See "
            "watcom10.0a repo docs/wcc386-re/regalloc-model.md §3.  Screen offline first: "
            "`c2 savings <fn> --flip VAR=REG --depth 2` (grounded savings/"
            "credit edits through the full sort+pick replay).  NB confirm "
            "this is a named-local swap, not a whole-function single-value "
            "choice or an arg-placement-constrained temp -- those need "
            "other levers."
        ),
    )


# ── Rule 109: scaled-index load fused into the result register ─────────
#
# A single-use indexed/scaled load (`arr[i].field`) whose result is consumed
# into a FIXED register (a call/return arg register, or any spot the value
# must land in) gets its scaled index FUSED into that same register, because
# the index is single-use and CountRegMoves coalesces it into the result
# (`movsx Rd; imul Rd; mov Rd,[Rd+disp]`).  PS keeps the index in a separate
# SCRATCH register and loads the result elsewhere (`movsx Re; imul Re;
# mov Rd,[Re+disp]`), because PS's source gave the index a SECOND use (often
# a now-dead store through the same index that Watcom DCEs).  The diagnostic
# tell is the load row itself: same destination Rd on both sides, but PS's
# base register != Rd (split) while recomp's base register == Rd (merged).

_RULE109_LOAD_RE = re.compile(
    r"^(mov|movsx|movzx)\s+(eax|ebx|ecx|edx|esi|edi|ebp)\s*,\s*"
    r"(?:[a-z]+ ptr )?\[\s*(eax|ebx|ecx|edx|esi|edi|ebp)\b"
)


def detect_rule_109(
    ps: InsnT | None,
    recomp: InsnT | None,
) -> Optional[RuleHint]:
    """Rule 109 - a scaled-index load whose index PS keeps in a separate
    scratch register but recomp FUSES into the load's destination register.

    Tell (the load row): both sides are `<mov*> Rd, [Rbase + disp]` with the
    SAME destination Rd, but PS has ``Rbase != Rd`` (index split into a
    scratch) while recomp has ``Rbase == Rd`` (index merged into the result).
    Fires only on that exact shape so it never collides with an ordinary
    register-identity swap.
    """
    if ps is None or recomp is None:
        return None
    mp = _RULE109_LOAD_RE.match(ps[3].lower())
    mr = _RULE109_LOAD_RE.match(recomp[3].lower())
    if mp is None or mr is None:
        return None
    if mp.group(1) != mr.group(1):          # same load mnemonic
        return None
    ps_dst, ps_base = mp.group(2), mp.group(3)
    rc_dst, rc_base = mr.group(2), mr.group(3)
    if ps_dst != rc_dst:                     # same result register both sides
        return None
    if ps_base == ps_dst:                    # PS must be SPLIT (scratch index)
        return None
    if rc_base != rc_dst:                    # recomp must be MERGED (fused)
        return None
    return RuleHint(
        rule="Rule 109",
        summary=(
            f"scaled-index load fused into result reg: PS `[{ps_base}]`→{ps_dst} "
            f"(index in scratch), recomp `[{rc_base}]`→{rc_dst} (index merged)"
        ),
        fix=(
            "the single-use index of `arr[i].field` coalesces into the "
            "result register; give the index a SECOND use so it gets its own "
            "scratch register (PS shape).  The minimal trigger is an "
            "otherwise-dead store through the same index that Watcom DCEs, "
            "e.g. `arr[i].field = arr[i].field;` immediately before the use "
            "(reconstructs a dead store PS's source had).  A plain extra READ "
            "does NOT work (it is DCE'd whole); it must be a STORE (its "
            "address computation materialises the index).  See Rule 109."
        ),
    )


# ── Rule 110: const-store FORM mismatch (immediate <-> register) ──

_IMM_OPND_RE = re.compile(r"^(?:0x[0-9a-fA-F]+|-?\d+)$")
# byte sub-register -> its 32-bit parent (for matching `xor bl,bl` to `mov [m],bl`)
_BYTE_PARENT = {"al": "eax", "ah": "eax", "bl": "ebx", "bh": "ebx",
                "cl": "ecx", "ch": "ecx", "dl": "edx", "dh": "edx"}
_GPR_OR_BYTE = (set(_BYTE_PARENT) |
                {"eax", "ebx", "ecx", "edx", "esi", "edi", "ebp"})


def _mem_store_src(insn: InsnT | None) -> Optional[tuple[str, str]]:
    """If ``insn`` is ``mov <mem>, <src>`` return ``(width, src)`` where width
    is 'byte'|'word'|'dword'|'' (implicit) and src is the source operand;
    else None."""
    if _mnemonic(insn) != "mov":
        return None
    ops = _operands(insn)
    if "," not in ops:
        return None
    dst, src = (s.strip() for s in ops.split(",", 1))
    if "[" not in dst:                       # destination must be memory
        return None
    width = ""
    for w in ("byte", "word", "dword"):
        if dst.startswith(w + " ptr"):
            width = w
            break
    return (width, src.strip())


def _reg_is_const_materialised(prev: InsnT | None, reg: str) -> bool:
    """True if ``prev`` materialised ``reg`` (or its byte parent) as a constant:
    ``xor reg,reg`` or ``mov reg, <imm>`` - i.e. ``reg`` holds a const-temp."""
    if prev is None:
        return False
    fam = {reg}
    if reg in _BYTE_PARENT:
        fam |= {reg, _BYTE_PARENT[reg]}
    parts = (prev[3] or "").replace(",", " ").split()
    if len(parts) >= 3 and parts[0] == "xor" and parts[1] in fam and parts[1] == parts[2]:
        return True
    if len(parts) >= 3 and parts[0] == "mov" and parts[1] in fam \
            and _IMM_OPND_RE.match(parts[2]):
        return True
    return False


def detect_rule_110(
    ps: InsnT | None,
    recomp: InsnT | None,
    prev_ps: InsnT | None,
    prev_recomp: InsnT | None,
) -> Optional[RuleHint]:
    """Rule 110 - a const-store **FORM** mismatch: one side stores a constant
    as an immediate (`mov <mem>, <imm>`) and the other materialises it in a
    register first (`xor r,r` / `mov r,imm` then `mov <mem>, r`).

    Per Rule 110 the const-store form is deterministic (0 always register; a
    nonzero constant register-cached iff referenced >= 2 times), so a form
    mismatch is a **ref-count** difference for that literal, NOT a regalloc
    one.  (A register-vs-register store of a const - same form, different reg
    - is regalloc and is flagged by the Byte-reg/Reg swap classifiers, not
    here.)  Fires only when exactly one side is an immediate store, the other
    is a same-width register store, and the register side's value is a
    confirmed const-temp (materialised by the preceding insn).
    """
    sp = _mem_store_src(ps)
    sr = _mem_store_src(recomp)
    if sp is None or sr is None:
        return None
    wp, srcp = sp
    wr, srcr = sr
    if wp != wr:                              # same store width on both sides
        return None
    p_imm = bool(_IMM_OPND_RE.match(srcp))
    r_imm = bool(_IMM_OPND_RE.match(srcr))
    if p_imm == r_imm:                        # need exactly one immediate side
        return None
    if p_imm:
        # PS immediate, recomp register: recomp over-shares the literal
        reg = srcr
        if reg not in _GPR_OR_BYTE or not _reg_is_const_materialised(prev_recomp, reg):
            return None
        ps_form, rc_form = f"mov [m], {srcp}", f"mov [m], {reg}"
        fix = ("recomp references this literal >= 2 times so cachecon caches it "
               "in a register; PS uses it once (immediate).  Make the constant "
               "single-use on recomp's side - use a distinct literal, or move one "
               "use into a call argument (call args never count).")
    else:
        # PS register, recomp immediate: PS shares the literal >= 2 times
        reg = srcp
        if reg not in _GPR_OR_BYTE or not _reg_is_const_materialised(prev_ps, reg):
            return None
        ps_form, rc_form = f"mov [m], {reg}", f"mov [m], {srcr}"
        fix = ("PS references this literal >= 2 times (register-cached); recomp "
               "uses it once (immediate).  Make the source share the literal "
               ">= 2 times (a second store / a register-operand compare of the "
               "same value).  If the literal is 0 it is ALWAYS register-form - "
               "then it is a which-register regalloc diff, not a form one.")
    return RuleHint(
        rule="Rule 110",
        summary=f"const-store form mismatch: PS `{ps_form}`, recomp `{rc_form}`",
        fix="Rule 110: const-store form is set by the literal's ref-count. " + fix,
    )


# ── Add-in-place vs LEA copy before use (regalloc/source-shape noise) ──

_GPR32_RE = r"(?:eax|ebx|ecx|edx|esi|edi|ebp|esp)"
_GPR32_SET = {"eax", "ebx", "ecx", "edx", "esi", "edi", "ebp"}

# __watcall integer argument registers (where a register-arg value is placed).
_WATCALL_ARG_REGS = {"eax", "edx", "ebx", "ecx"}


def detect_rule_98(
    ps: InsnT | None,
    recomp: InsnT | None,
) -> Optional[RuleHint]:
    """Rule 98 - a computed register-argument value is born in the arg
    register on PS (`add ecx, 0x20`) but computed in a scratch and moved
    on recomp (`lea ecx, [eax + 0x20]`), i.e. the SAME result register but
    the running value lived in a different register.

    Distinguished from `detect_add_vs_lea_copy` (in-place pointer adjust,
    `lea_src == add_reg`): here ``lea_src != add_reg`` and
    ``lea_dst == add_reg`` - the whole arithmetic chain ran in EAX (the
    accumulator short-load winner) and got `lea`'d into the arg register,
    instead of running directly in the arg register like PS.

    Fix: a Rule 24c neutral term that folds to 0 forces the value into its
    own temp so the parm-move counts in GiveBestReg/CountRegMoves and the
    value is born in the arg register.  The neutral operand MUST be local
    to this call's args (e.g. an array element being passed), not a global
    an earlier call shares.  See Rule 98 in
    docs/watcom-codegen-patterns.md.
    """
    if ps is None or recomp is None:
        return None
    ps_mn, rc_mn = _mnemonic(ps), _mnemonic(recomp)
    if {ps_mn, rc_mn} != {"add", "lea"}:
        return None
    add = ps if ps_mn == "add" else recomp
    lea = ps if ps_mn == "lea" else recomp
    m_add = re.fullmatch(
        rf"\s*({_GPR32_RE})\s*,\s*(0x[0-9a-fA-F]+|\d+)\s*",
        _operands(add).lower())
    if not m_add:
        return None
    add_reg, imm = m_add.group(1), m_add.group(2)
    m_lea = re.fullmatch(
        rf"\s*({_GPR32_RE})\s*,\s*\[\s*({_GPR32_RE})\s*\+\s*(0x[0-9a-fA-F]+|\d+)\s*\]\s*",
        _operands(lea).lower())
    if not m_lea:
        return None
    lea_dst, lea_src, lea_imm = m_lea.groups()
    # Rule 98 signature: same result register, same displacement, but the
    # running value lived in a DIFFERENT register (lea_src != result reg).
    if lea_dst != add_reg or lea_src == add_reg:
        return None
    if int(lea_imm, 0) != int(imm, 0):
        return None
    # The result register must be a __watcall arg register (the value is
    # being placed into an argument slot).
    if add_reg not in _WATCALL_ARG_REGS:
        return None
    ps_in_arg_reg = ps_mn == "add"
    return RuleHint(
        rule="Rule 98",
        summary=(
            f"register-arg value born in `{add_reg}` (PS `add`) vs computed "
            f"in `{lea_src}` then `lea`'d into `{add_reg}` (recomp)"
            if ps_in_arg_reg else
            f"register-arg value computed in `{lea_src}` then `lea`'d into "
            f"`{add_reg}` (PS) vs born in `{add_reg}` (recomp `add`)"
        ),
        fix=(
            "add a Rule 24c neutral term that folds to 0 (e.g. "
            "`+ (arr[0] - arr[0])` using a value LOCAL to this call's args) "
            "to force the value into its own temp so it lands in the arg "
            "register; verify earlier calls keep their PS register."
        ),
    )


def detect_add_vs_lea_copy(
    ps: InsnT | None,
    recomp: InsnT | None,
    next_ps: InsnT | None,
    next_recomp: InsnT | None,
) -> Optional[RuleHint]:
    """One side mutates a pointer/index in-place (`add esi, 0x70`) while
    the other computes a copy (`lea eax, [esi + 0x70]`) and immediately
    uses the copy (commonly `push eax` vs `push esi`).

    This appeared during the sibling+swap sweep in start_smacking's
    palette-buffer argument setup.  It is regalloc/source-shape noise,
    not a semantic mismatch; source levers are live-range shaping or
    using a named adjusted-pointer temp, but neither is reliably better.
    """
    if ps is None or recomp is None:
        return None
    ps_mn, rc_mn = _mnemonic(ps), _mnemonic(recomp)
    if {ps_mn, rc_mn} != {"add", "lea"}:
        return None
    add = ps if ps_mn == "add" else recomp
    lea = ps if ps_mn == "lea" else recomp
    m_add = re.fullmatch(rf"\s*({_GPR32_RE})\s*,\s*(0x[0-9a-fA-F]+|\d+)\s*", _operands(add).lower())
    if not m_add:
        return None
    add_reg, imm = m_add.group(1), m_add.group(2)
    m_lea = re.fullmatch(rf"\s*({_GPR32_RE})\s*,\s*\[\s*({_GPR32_RE})\s*\+\s*(0x[0-9a-fA-F]+|\d+)\s*\]\s*", _operands(lea).lower())
    if not m_lea:
        return None
    lea_dst, lea_src, lea_imm = m_lea.groups()
    if lea_src != add_reg or int(lea_imm, 0) != int(imm, 0):
        return None
    # Optional confirmation: next rows use the adjusted value under the
    # corresponding register identity, e.g. push esi vs push eax.
    nxt_add = next_ps if ps_mn == "add" else next_recomp
    nxt_lea = next_ps if ps_mn == "lea" else next_recomp
    if nxt_add is not None and nxt_lea is not None:
        if _mnemonic(nxt_add) != _mnemonic(nxt_lea):
            return None
        ao = _operands(nxt_add).strip().lower()
        lo = _operands(nxt_lea).strip().lower()
        if ao != add_reg or lo != lea_dst:
            return None
    ps_in_place = ps_mn == "add"
    return RuleHint(
        rule="Add/LEA copy",
        summary=(
            f"adjusted-pointer form mismatch (PS mutates `{add_reg}` with "
            f"`add`, recomp computes copy `{lea_dst}` with `lea`)"
            if ps_in_place else
            f"adjusted-pointer form mismatch (PS computes copy `{lea_dst}` "
            f"with `lea`, recomp mutates `{add_reg}` with `add`)"
        ),
        fix=(
            "usually regalloc/live-range noise.  If actionable, try a named "
            "adjusted-pointer temp (`p2 = p + imm`) vs mutating the original "
            "pointer in-place; keep whichever matches neighbouring uses."
        ),
    )


# ── Rule 72 - prefix-inc/dec field vs cached-temp RMW ──────────────

def detect_rule_72(
    ps: InsnT | None,
    recomp: InsnT | None,
    next_ps: InsnT | None,
    next_recomp: InsnT | None,
) -> Optional[RuleHint]:
    """PS does one-instruction `inc/dec [field]`; recomp does the
    three-instruction `mov reg, [field]; inc/dec reg; mov [field], reg`
    cache sequence (or vice versa).  See Rule 72 in
    docs/watcom-codegen-patterns.md.

    Trigger: the C source caches the field's value in an `int` local
    before incrementing it back, instead of using prefix `++field` /
    `--field` directly.
    """
    if ps is None or recomp is None:
        return None
    ps_mn, rc_mn = _mnemonic(ps), _mnemonic(recomp)
    if {ps_mn, rc_mn} not in ({"inc", "mov"}, {"dec", "mov"}):
        return None
    # The inc/dec side must operate on a memory operand.
    inc_side = ps if ps_mn in ("inc", "dec") else recomp
    if "[" not in _operands(inc_side):
        return None
    # The mov side must be a register-from-memory LOAD (i.e. start of
    # the cache sequence), not a store.  Accept optional `byte ptr` /
    # `dword ptr` qualifier between the dst register and the `[`.
    mov_side = ps if ps_mn == "mov" else recomp
    mov_ops = _operands(mov_side).replace(" ", "")
    if not re.match(r"^[a-z]+,(?:byteptr|wordptr|dwordptr)?\[", mov_ops):
        return None
    # Optional confirmation: the next row on the cached side should be
    # an inc/dec of a register (the modify step).
    nxt = next_ps if ps_mn == "mov" else next_recomp
    if nxt is not None and _mnemonic(nxt) not in ("inc", "dec", "mov", "cmp"):
        return None
    ps_is_inline = ps_mn in ("inc", "dec")
    op = ps_mn if ps_is_inline else rc_mn
    return RuleHint(
        rule="Rule 72",
        summary=(
            f"prefix-{op} RMW mismatch (PS: in-place `{op} [field]`; "
            "recomp: cached `mov reg, [field]; "
            f"{op} reg; mov [field], reg`)"
            if ps_is_inline else
            f"prefix-{op} RMW mismatch (recomp: in-place; PS: cached)"
        ),
        fix=(
            f"replace `int tmp = field {('+' if op == 'inc' else '-')} 1; "
            f"field = tmp; if (tmp ...)` with prefix "
            f"`{'++' if op == 'inc' else '--'}field; if (field ...)` so "
            "Watcom emits the in-place RMW."
            if ps_is_inline else
            "if recomp is in-place but PS cached: introduce an "
            "`int tmp = field; field = tmp "
            f"{('+' if op == 'inc' else '-')} 1` cache."
        ),
    )


# ── Rule 73 - cached row pointer vs folded disp32 ──────────────────

_HUGE_DISP_THRESHOLD = 0x1000  # 4 KiB; bigger ⇒ likely folded array+field
_SMALL_DISP_THRESHOLD = 0x100  # 256 B; smaller ⇒ likely cached-ptr offset

_DISP_RE = re.compile(
    r"\[[a-z]+(?:\*\d+)?(?:\s*\+\s*[a-z]+(?:\*\d+)?)?\s*\+\s*"
    r"(0x[0-9a-fA-F]+|\d+)\]"
)


def _mem_displacement(insn: InsnT | None) -> Optional[int]:
    """Extract the disp32/disp8 from a `[reg + disp]` operand, if any."""
    if insn is None:
        return None
    m = _DISP_RE.search(_operands(insn))
    if not m:
        return None
    raw = m.group(1)
    try:
        return int(raw, 16 if raw.startswith("0x") else 10)
    except ValueError:
        return None


def _has_disp32_fixup(insn: InsnT, abs_base: int, fix: set[int]) -> bool:
    """Are the last 4 bytes of `insn`'s encoding in the fixup set (i.e.
    the trailing disp32 has been relocated)?"""
    rel_off, _size, raw, _asm = insn
    if len(raw) < 4:
        return False
    base = len(raw) - 4
    return any(
        (abs_base + rel_off + base + i) in fix
        for i in range(4)
    )


def detect_rule_73(
    ps: InsnT | None,
    recomp: InsnT | None,
    ps_abs_base: int,
    recomp_abs_base: int,
    ps_fix: set[int],
    recomp_fix: set[int],
) -> Optional[RuleHint]:
    """One side folds `array_base + field_offset` into a disp32
    (fixup-masked); the other side uses a cached row pointer with a
    small literal field offset.

    See Rule 73 in docs/watcom-codegen-patterns.md.
    """
    if ps is None or recomp is None:
        return None
    if _mnemonic(ps) != _mnemonic(recomp):
        return None
    if _mnemonic(ps) not in (
        "mov", "cmp", "add", "sub", "or", "and", "xor", "lea", "test",
    ):
        return None
    # Must have a memory operand on both sides.
    if "[" not in _operands(ps) or "[" not in _operands(recomp):
        return None
    ps_folded = _has_disp32_fixup(ps, ps_abs_base, ps_fix)
    rc_folded = _has_disp32_fixup(recomp, recomp_abs_base, recomp_fix)
    if ps_folded == rc_folded:
        return None  # both fold or both cached - no mismatch
    cached_side = recomp if ps_folded else ps
    disp = _mem_displacement(cached_side)
    if disp is None or disp >= _SMALL_DISP_THRESHOLD:
        return None
    return RuleHint(
        rule="Rule 73",
        summary=(
            "cached-pointer mismatch (PS folds `array+field` into disp32, "
            f"recomp uses `[cached_ptr + 0x{disp:x}]`)"
            if ps_folded else
            "cached-pointer mismatch (recomp folds, PS uses cached pointer + "
            f"`0x{disp:x}` offset)"
        ),
        fix=(
            "remove the `T *cache = &array[idx]` local and inline "
            "`array[idx].field` at every use site (works for ≤ 3 uses)."
            if ps_folded else
            "introduce a `T *cache = &array[idx]` local with multiple "
            "`cache->field` uses (works when use count is high)."
        ),
    )


# ── Rule 81 - named byte-temp pins regalloc in byte-copy loops ──────

_LOW_BYTE = {"eax": "al", "ebx": "bl", "ecx": "cl", "edx": "dl"}


def _parse_byte_load_with_disp(
    insn: InsnT | None,
) -> tuple[str, str, str] | None:
    """If `insn` is `mov <reg8>, byte ptr [<base32> + disp32]`,
    return ``(reg8, base32, disp_text)``.  Returns None otherwise.

    Used by Rule 81's byte-copy nucleus detector.
    """
    if insn is None or _mnemonic(insn) != "mov":
        return None
    ops = [o.strip().lower() for o in _operands(insn).split(",")]
    if len(ops) != 2:
        return None
    dst, src = ops
    if dst not in _LOW_BYTE.values():
        return None
    # Source must be `byte ptr [base + disp32]` or `[base + disp32]`.
    m = re.fullmatch(
        r"(?:byte\s+ptr\s+)?\[\s*([a-z0-9]+)\s*(?:\+\s*(\S+?))?\s*\]",
        src,
    )
    if not m:
        return None
    base = m.group(1)
    disp = m.group(2) or ""
    if base not in _LOW32_REGS and base not in {"esi", "edi", "ebp"}:
        return None
    # Require a 32-bit displacement form (Rule 81's signature uses a
    # global/array base; the load is `[reg + 0x27cfc]`-style).
    if not disp:
        return None
    return (dst, base, disp)


def _parse_byte_store_indirect(
    insn: InsnT | None,
    reg8: str,
) -> str | None:
    """If `insn` is `mov [<base32>], <reg8>` (no displacement), return
    the base register; else None.
    """
    if insn is None or _mnemonic(insn) != "mov":
        return None
    ops = [o.strip().lower() for o in _operands(insn).split(",")]
    if len(ops) != 2:
        return None
    dst, src = ops
    if src != reg8:
        return None
    m = re.fullmatch(
        r"(?:byte\s+ptr\s+)?\[\s*([a-z0-9]+)\s*\]",
        dst,
    )
    if not m:
        return None
    base = m.group(1)
    if base not in _LOW32_REGS and base not in {"esi", "edi", "ebp"}:
        return None
    return base


def _find_rule_81_swap(
    rows: list[tuple[InsnT | None, InsnT | None, bool]],
) -> set[int]:
    """Pre-scan for the Rule 81 byte-copy regalloc swap signature.

    The pattern (in PS and recomp, with the BASE/STORE registers
    SWAPPED between the two sides):

        mov <reg8>, byte ptr [<load_base> + <disp>]
        test <reg8>, <reg8>
        je   <end>
        mov  [<store_base>], <reg8>

    Where between PS and RC: PS's load_base == RC's store_base AND
    PS's store_base == RC's load_base.  This is the function-wide
    register swap caused by a named ``char c`` local in the source
    Form A (Rule 81 § Form A).

    Since difflib may misalign the load rows between PS and recomp
    (alignment shifts due to earlier prologue diffs), we scan each
    column independently for the load+store pattern, then match by
    register-swap symmetry.

    Returns the set of row indices that contain a diff row near the
    detected pattern (so the hint surfaces on at least one diff row).
    """
    n = len(rows)

    def _find_load_store_pair(
        col: int,
    ) -> tuple[int, int, str, str, str] | None:
        """Find the first `mov reg8, [base+disp]` followed within 6
        rows by `mov [other_base], reg8`.  Returns
        ``(load_row, store_row, reg8, load_base, store_base)``."""
        for i in range(n):
            insn = rows[i][col]
            load = _parse_byte_load_with_disp(insn)
            if load is None:
                continue
            reg8, load_base, _disp = load
            for j in range(i + 1, min(i + 7, n)):
                store_insn = rows[j][col]
                store_base = _parse_byte_store_indirect(store_insn, reg8)
                if store_base is None:
                    continue
                if store_base == load_base:
                    # Same base used for both load + store - not a swap
                    # candidate (this is e.g. an in-place RMW).
                    break
                return (i, j, reg8, load_base, store_base)
        return None

    ps_pair = _find_load_store_pair(0)
    rc_pair = _find_load_store_pair(1)
    if ps_pair is None or rc_pair is None:
        return set()
    _, _, ps_reg8, ps_load_base, ps_store_base = ps_pair
    _, _, rc_reg8, rc_load_base, rc_store_base = rc_pair
    # Same byte target reg (BL/AL/CL/DL).
    if ps_reg8 != rc_reg8:
        return set()
    # Swap symmetry: PS loads from REG_A and stores via REG_B; RC
    # loads from REG_B and stores via REG_A.
    if ps_load_base != rc_store_base or ps_store_base != rc_load_base:
        return set()
    # Flag the load rows from both PS and RC sides (whichever is a
    # diff row, or the alignment-row between them).  We return the
    # ps_pair's load row index - the renderer will surface the hint
    # there.
    out: set[int] = set()
    ps_load_i, ps_store_i, _, _, _ = ps_pair
    rc_load_i, rc_store_i, _, _, _ = rc_pair
    # Add whichever of the four rows are diff rows.
    for idx in (ps_load_i, rc_load_i, ps_store_i, rc_store_i):
        if 0 <= idx < n and rows[idx][2]:
            out.add(idx)
    # Also include the row immediately after a delete-only load row
    # (difflib alignment puts the swap signal there).
    for idx in (ps_load_i, rc_load_i):
        if 0 <= idx < n - 1 and rows[idx + 1][2]:
            out.add(idx + 1)
    return out


_WORD_REGS = {"ax", "bx", "cx", "dx", "si", "di", "bp"}


_ARG_REGS = ("eax", "edx", "ebx", "ecx")


def detect_rule_139(
    ps: InsnT | None,
    recomp: InsnT | None,
    next_ps: InsnT | None,
    next_recomp: InsnT | None,
    prev_ps: InsnT | None = None,
    prev_recomp: InsnT | None = None,
) -> Optional[RuleHint]:
    """Dead-argument staging (Rule 139).

    A PS-only `mov <argreg>, imm` immediately before a call both sides
    share: PS stages an argument the callee never reads, i.e. the
    ORIGINAL callee prototype takes an int the body ignores (often
    symmetric with an init_ sibling that uses it).  Worked example:
    `free_sample_buffer(10)` in main (c2.c, exact); the callee's own
    bytes do not change when the dead param is added."""
    if ps is None or recomp is not None:
        return None
    # The imm-mov must be the ONLY PS-only staging insn: if the previous
    # row is also a PS-only delete, the whole argument block differs
    # (different call signature/values) -- not a dead argument.
    if prev_ps is not None and prev_recomp is None:
        return None
    asm = ps[3]
    if not asm.startswith("mov "):
        return None
    parts = asm[4:].split(",", 1)
    if len(parts) != 2:
        return None
    reg, val = parts[0].strip(), parts[1].strip()
    if reg not in _ARG_REGS or not val.startswith("0x") and not val.isdigit():
        return None
    if next_ps is None or not next_ps[3].startswith("call "):
        return None
    if next_recomp is None or not next_recomp[3].startswith("call "):
        return None
    return RuleHint(
        rule="Rule 139",
        summary=f"PS stages a DEAD argument ({reg} = {val}) before the "
                f"shared call",
        fix=f"the original callee prototype takes an int it ignores: add "
            f"the parameter to decl+def (callee bytes unchanged) and pass "
            f"{val} at this call site (cf. free_sample_buffer(10), main).",
    )


def _find_rule_140_rows(
    rows: list[tuple[InsnT | None, InsnT | None, bool]],
) -> dict[int, RuleHint]:
    """Loop-prologue hoist (Rule 140).

    Both sides jump BACKWARD with the same mnemonic but PS's target sits
    GAP bytes after RC's, and the PS instructions in the gap window
    [ps_target-gap, ps_target) are plain stores (mov/xor): PS's back
    edge re-enters AFTER those stores, i.e. the statements were written
    BEFORE the loop, not at the top of its body.  Worked example:
    `turbo_mode = 0;` hoisted above `while(1)` in main (c2.c, exact)."""
    out: dict[int, RuleHint] = {}
    ps_by_off = {p[0]: p for p, _, _ in rows if p is not None}
    for i, (ps, rc, is_diff) in enumerate(rows):
        if not is_diff or ps is None or rc is None:
            continue
        m_ps, m_rc = ps[3].split()[0], rc[3].split()[0]
        if m_ps != m_rc or not (m_ps == "jmp" or m_ps.startswith("j")):
            continue
        try:
            t_ps = int(ps[3].split()[-1], 16)
            t_rc = int(rc[3].split()[-1], 16)
        except ValueError:
            continue
        if t_ps >= ps[0] or t_rc >= rc[0]:
            continue                               # backward only
        gap = (rc[0] - t_rc) - (ps[0] - t_ps)
        if not (0 < gap <= 32):
            continue
        # PS insns inside [t_ps - gap, t_ps) must be plain stores.
        win, off = [], t_ps - gap
        while off < t_ps:
            ins = ps_by_off.get(off)
            if ins is None:
                break
            win.append(ins)
            off += ins[1]
        if off != t_ps or not win:
            continue
        if not all(ins[3].split()[0] in {"mov", "xor"} for ins in win):
            continue
        out[i] = RuleHint(
            rule="Rule 140",
            summary=f"PS back-edge re-enters at +{t_ps:#x}, AFTER "
                    f"{len(win)} store insn(s) RC keeps inside the loop",
            fix="hoist the statement(s) (e.g. `flag = 0;`) ABOVE the "
                "loop: PS re-runs the body without them, so they were "
                "written before `while(...)`, not at the body top "
                "(cf. turbo_mode=0 in main, c2.c).",
        )
    return out


def detect_rule_133(
    ps: InsnT | None,
    recomp: InsnT | None,
) -> Optional[RuleHint]:
    """cwde vs movsx r32,r16: WORD-class seat flip marker (Rule 133).

    Sign-extending a 16-bit value to 32 bits is ``cwde`` (1 byte) iff the
    value sits in AX, else ``movsx eax, rX`` (3 bytes).  When the two
    sides disagree, the underlying `short` value was SEATED differently
    by the word-class allocator (candidate order AX,DX,BX,CX,SI,DI --
    cgi86reg pair order, validated in fade_to_palette) -- and the 1b-vs-3b
    size delta cascades into offsets/jcc widths downstream.  This is a
    WORD-register allocation lever (savings/conflict order of the short
    locals), not instruction selection: fix the short variable's seat
    (decl/savings levers, or split counters as in fade_to_palette i/j)
    and the extension instruction follows.
    """
    if ps is None or recomp is None:
        return None
    pm, rm = _mnemonic(ps), _mnemonic(recomp)
    pair = {pm, rm}
    if pair != {"cwde", "movsx"}:
        return None
    mv = ps if pm == "movsx" else recomp
    ops = [o.strip().lower() for o in _operands(mv).split(",")]
    if len(ops) != 2 or ops[1] not in _WORD_REGS:
        return None
    who_ax = "PS" if pm == "cwde" else "recomp"
    other = ops[1].upper()
    return RuleHint(
        rule="Rule 133",
        summary=(f"cwde vs movsx eax,{other}: word-class seat flip "
                 f"({who_ax} has the short in AX)"),
        fix=(f"The 16-bit value sits in AX on the {who_ax} side but in "
             f"{other} on the other -- a WORD-register seat difference "
             f"(candidates AX,DX,BX,CX,SI,DI).  Fix the short local's "
             f"allocation (savings rank / conflict order / split "
             f"counters, cf. fade_to_palette), NOT this instruction; "
             f"the cwde/movsx choice and the 1b-vs-3b cascade follow. "
             f"Rule 133."),
    )


_R132_ALU = ("add", "sub", "and", "or", "xor", "shl", "sar", "shr", "imul")


def _find_rule_132_rows(
    rows: list[tuple[InsnT | None, InsnT | None, bool]],
) -> dict[int, RuleHint]:
    """Pre-scan for copy-then-op vs op-in-place divergence (Rule 132).

    One side shows ``mov rT, rS`` + ``<alu> rT, X`` (value-preserving
    copy: rS's value is LIVE past the statement) while the other side
    does the same ALU in-place on its left register.  Grounded: OW v1
    split.c rMOVOP1RES/rUSEREGISTER always reduce via a result temp;
    the copy survives allocation iff the left operand has a later use
    (oracle docs/codegen-experiments/copy_then_op_liveness.py).

    Returns {row_index: hint} for the row holding the copy-side ``mov``.
    """
    out: dict[int, RuleHint] = {}
    n = len(rows)

    def _col(side: int) -> list[tuple[int, InsnT]]:
        return [(i, r[side]) for i, r in enumerate(rows) if r[side] is not None]

    def _copy_op_at(col: list, k: int):
        """mov rT,rS + alu rT,X starting at column position k."""
        if k + 1 >= len(col):
            return None
        i0, ins0 = col[k]
        if _mnemonic(ins0) != "mov":
            return None
        m = re.fullmatch(
            rf"\s*({_GPR32_RE})\s*,\s*({_GPR32_RE})\s*",
            _operands(ins0).lower(),
        )
        if not m or m.group(1) == m.group(2):
            return None
        rt, rs = m.group(1), m.group(2)
        i1, ins1 = col[k + 1]
        mn = _mnemonic(ins1)
        if mn not in _R132_ALU:
            return None
        ops = [o.strip() for o in _operands(ins1).lower().split(",")]
        if len(ops) != 2 or ops[0] != rt or ops[1] == rt:
            return None
        return (i0, rt, rs, mn, ops[1])

    for side, other in ((0, 1), (1, 0)):
        col = _col(side)
        ocol = _col(other)
        for k in range(len(col)):
            hit = _copy_op_at(col, k)
            if hit is None:
                continue
            i0, rt, rs, mn, x = hit
            if not rows[i0][2]:           # only annotate diff rows
                continue
            # other side: same ALU done IN-PLACE (no copy) nearby?
            near = [oi for oi, oins in ocol if abs(oi - i0) <= 3
                    and _mnemonic(oins) == mn]
            inplace = False
            for oi in near:
                oins = rows[oi][other]
                oops = [o.strip() for o in _operands(oins).lower().split(",")]
                if len(oops) == 2 and oops[0] in _GPR32_SET:
                    # in-place iff the other side has NO reg,reg mov
                    # feeding this ALU dst immediately before it.
                    op_idx = next(j for j, (ii, _) in enumerate(ocol)
                                  if ii == oi)
                    prev = ocol[op_idx - 1][1] if op_idx > 0 else None
                    if prev is not None and _mnemonic(prev) == "mov":
                        pm = re.fullmatch(
                            rf"\s*{re.escape(oops[0])}\s*,\s*({_GPR32_RE})\s*",
                            _operands(prev).lower(),
                        )
                        if pm:
                            continue      # both sides copy -> not Rule 132
                    inplace = True
                    break
            if not inplace:
                continue
            who = "PS" if side == 0 else "recomp"
            kept = (f"{who} preserves {rs.upper()}"
                    if side == 0 else
                    f"recomp preserves {rs.upper()}")
            if side == 0:
                fix = (
                    f"PS copies before the `{mn}` (mov {rt},{rs}) -- the "
                    f"value in {rs.upper()} is READ AGAIN later in PS's "
                    f"source (second use / `return v` / cached variable), "
                    f"while OUR source consumed it (in-place `{mn}`). "
                    f"Do NOT restructure this statement: add the later "
                    f"use (or stop reusing the variable for the result). "
                    f"Oracle: copy_then_op_liveness.py; OW v1 split.c "
                    f"rMOVOP1RES. Rule 132.")
            else:
                fix = (
                    f"OUR build copies before the `{mn}` (mov {rt},{rs}) "
                    f"-- our source keeps the value in {rs.upper()} alive "
                    f"past this statement (extra later read) where PS "
                    f"consumed it in place.  Remove/inline the later use "
                    f"so the value dies at this op. Rule 132.")
            out[i0] = RuleHint(
                rule="Rule 132",
                summary=(f"copy-then-{mn} vs in-place {mn}: {kept} "
                         f"(left value live past stmt)"),
                fix=fix,
            )
    return out


def detect_rule_132(
    i: int,
    rule_132_rows: dict[int, RuleHint],
) -> Optional[RuleHint]:
    """Copy-then-op vs op-in-place: left-operand liveness (Rule 132)."""
    return rule_132_rows.get(i)


def detect_rule_81(
    row_idx: int,
    ps: InsnT | None,
    recomp: InsnT | None,
    rule_81_rows: set[int],
) -> Optional[RuleHint]:
    """Byte-copy loop regalloc swap (Rule 81).

    Fires on the indexed-load row of a byte-copy loop where PS and
    recomp picked SWAPPED registers for the source-index pointer
    and the destination pointer.  The fix is the source-level
    rewrite: drop the named ``char c`` temp and double-load the
    source expression in both the loop test and the body.
    """
    if row_idx not in rule_81_rows:
        return None
    return RuleHint(
        rule="Rule 81",
        summary=(
            "byte-copy loop regalloc swap "
            "(named `char c` temp pins int counter onto wrong reg)"
        ),
        fix=(
            "drop the named `char c` byte-temp.  Rewrite "
            "`while ((c = src[i]) != 0) { *out++ = c; i++; } *out = c;` "
            "as `while (src[i] != 0) { *out = src[i]; i++; out++; } "
            "*out = 0;` - Watcom CSEs the two `src[i]` reads into one "
            "BL emit, frees BL from being pinned, and flips the int "
            "counter into the parm reg (Form B in the loop catalog)."
        ),
    )


# ── Rule 78 - pointer-save-before-deref 5-insn copy pattern ─────────


def _find_rule_78_copies(
    rows: list[tuple[InsnT | None, InsnT | None, bool]],
) -> set[int]:
    """Pre-scan for PS's 5-insn ptr-save / inc / lea-dst / load / store
    byte-copy idiom.  Returns the set of PS-side row indices that are
    part of such a pattern AND are also diff rows.

    Pattern (PS side, 5 consecutive non-None rows):

      (1) mov  regA, regB          ; save source pointer (regA != regB)
      (2) inc  regB                ; advance original
      (3) lea  regC, [r1 + r2]     ; compute destination address
      (4) mov  regA_low8, [regA]   ; load byte via saved pointer
      (5) mov  [regC], regA_low8   ; store byte via dest pointer

    Only EAX/EBX/ECX/EDX qualify for `regA` (need a sub-byte register).
    The recomp counterpart is the compact 2-3 insn direct-indexed
    form; if the same pattern is present on the recomp side, we
    skip (both sides match → nothing to suggest).
    """
    out: set[int] = set()
    n = len(rows)
    if n < 5:
        return out

    def _matches_pattern(idx: int, side: int) -> bool:
        """Check the 5-insn pattern on `side` (0=PS, 1=recomp)
        starting at row `idx`.  Returns True iff a complete match."""
        insns = [rows[idx + k][side] for k in range(5)]
        if any(x is None for x in insns):
            return False
        # (1) mov regA, regB
        if _mnemonic(insns[0]) != "mov":
            return False
        m1 = re.fullmatch(
            rf"\s*({_GPR32_RE})\s*,\s*({_GPR32_RE})\s*",
            _operands(insns[0]).lower(),
        )
        if not m1:
            return False
        regA, regB = m1.group(1), m1.group(2)
        if regA == regB or regA not in _LOW_BYTE:
            return False
        regA_byte = _LOW_BYTE[regA]
        # (2) inc regB
        if _mnemonic(insns[1]) != "inc":
            return False
        if _operands(insns[1]).strip().lower() != regB:
            return False
        # (3) lea regC, [...]
        if _mnemonic(insns[2]) != "lea":
            return False
        m3 = re.fullmatch(
            rf"\s*({_GPR32_RE})\s*,\s*\[\s*({_GPR32_RE})"
            rf"\s*\+\s*({_GPR32_RE})\s*\]\s*",
            _operands(insns[2]).lower(),
        )
        if not m3:
            return False
        regC = m3.group(1)
        # (4) mov regA_byte, byte ptr [regA]
        if _mnemonic(insns[3]) != "mov":
            return False
        m4 = re.fullmatch(
            rf"\s*{regA_byte}\s*,\s*(?:byte\s+ptr\s+)?\[\s*{regA}\s*\]\s*",
            _operands(insns[3]).lower(),
        )
        if not m4:
            return False
        # (5) mov byte ptr [regC], regA_byte
        if _mnemonic(insns[4]) != "mov":
            return False
        m5 = re.fullmatch(
            rf"\s*(?:byte\s+ptr\s+)?\[\s*{regC}\s*\]\s*,\s*{regA_byte}\s*",
            _operands(insns[4]).lower(),
        )
        if not m5:
            return False
        return True

    for i in range(n - 4):
        if not _matches_pattern(i, 0):       # PS-side match
            continue
        # If recomp has the same 5-insn shape too, both are equal -
        # no source-level lever to recommend.
        if _matches_pattern(i, 1):
            continue
        # Need at least one diff row in the window for the hint to
        # appear in the diff output at all.
        diff_idxs = [i + k for k in range(5) if rows[i + k][2]]
        if not diff_idxs:
            continue
        for k in diff_idxs:
            out.add(k)
    return out


def detect_rule_78(
    row_idx: int,
    ps: InsnT | None,
    recomp: InsnT | None,
    rule_78_rows: set[int],
) -> Optional[RuleHint]:
    """PS uses the named pointer-save-before-deref 5-insn copy
    idiom; recomp collapsed to the compact 2-3 insn direct-indexed
    form (or vice versa).
    """
    if row_idx not in rule_78_rows:
        return None
    return RuleHint(
        rule="Rule 78",
        summary=(
            "PS uses the 5-insn `mov save, src; inc src; lea dst; "
            "mov byte, [save]; mov [dst], byte` byte-copy idiom"
        ),
        fix=(
            "name BOTH the pre-increment source ptr AND the dest "
            "address as explicit locals: "
            "`char *p = src++; char *q = &buf[i]; *q = *p;` - "
            "either name elision collapses Watcom to the compact form."
        ),
    )


# ── Rule 82 - if-zero-replace pins scratch to result register ──────


def _parse_movsx_word_reg(insn: InsnT | None) -> str | None:
    """`movsx <reg32>, word ptr [...]` → ``<reg32>`` or None."""
    if insn is None:
        return None
    if _mnemonic(insn) != "movsx":
        return None
    ops = _operands(insn)
    m = re.match(r"\s*(e[a-z]{2})\s*,\s*word\b", ops, re.I)
    if not m:
        return None
    return m.group(1).lower()


def _parse_imul_reg_reg_imm(insn: InsnT | None) -> tuple[str, str] | None:
    """`imul <r1>, <r2>, <imm>` → ``(r1, r2)`` (3-operand form)."""
    if insn is None:
        return None
    if _mnemonic(insn) != "imul":
        return None
    ops = _operands(insn)
    m = re.match(r"\s*(e[a-z]{2})\s*,\s*(e[a-z]{2})\s*,\s*[^,]+\s*$",
                 ops, re.I)
    if not m:
        return None
    return (m.group(1).lower(), m.group(2).lower())


def _parse_mov_reg_indirect_disp32(
    insn: InsnT | None,
) -> tuple[str, str] | None:
    """`mov <r_dst>, [<r_base> + disp32]` → ``(r_dst, r_base)`` or
    None.  Accepts ``dword ptr`` annotations and bare forms; rejects
    plain ``[reg]`` without a displacement (we want the indexed-field
    form specifically)."""
    if insn is None:
        return None
    if _mnemonic(insn) != "mov":
        return None
    ops = _operands(insn)
    # Match "mov reg, [base + disp]" but require disp to be present.
    m = re.match(
        r"\s*(e[a-z]{2})\s*,\s*(?:dword\s+ptr\s+)?"
        r"\[\s*(e[a-z]{2})\s*\+\s*0x[0-9a-f]+\s*\]\s*$",
        ops,
        re.I,
    )
    if not m:
        return None
    return (m.group(1).lower(), m.group(2).lower())


def _parse_test_reg_self(insn: InsnT | None) -> str | None:
    """`test <reg>, <reg>` with same reg both sides → reg name."""
    if insn is None:
        return None
    if _mnemonic(insn) != "test":
        return None
    ops = _operands(insn)
    m = re.match(r"\s*(e[a-z]{2})\s*,\s*(e[a-z]{2})\s*$", ops, re.I)
    if not m or m.group(1).lower() != m.group(2).lower():
        return None
    return m.group(1).lower()


def _parse_mov_reg_imm(insn: InsnT | None) -> tuple[str, str] | None:
    """`mov <reg>, <imm>` → ``(reg, imm_text)`` or None."""
    if insn is None:
        return None
    if _mnemonic(insn) != "mov":
        return None
    ops = _operands(insn)
    m = re.match(r"\s*(e[a-z]{2})\s*,\s*((?:0x[0-9a-f]+)|\d+)\s*$",
                 ops, re.I)
    if not m:
        return None
    return (m.group(1).lower(), m.group(2))


def _find_rule_82_pattern(
    rows: list[tuple[InsnT | None, InsnT | None, bool]],
) -> set[int]:
    """Pre-scan for the Rule 82 if-zero-replace regalloc-pin signature.

    Looks for an indexed-load via `movsx + imul + mov reg, [scratch+disp]`
    immediately followed by an `if (result == 0) result = N;` test
    (i.e. `test reg, reg; jne short; mov reg, imm`) on BOTH PS and
    RC sides - where:

      * PS uses ``scratch != result`` (separate live ranges,
        scratch in EAX, result in EDX).
      * RC uses ``scratch == result`` (merged live range, both
        in EDX - the in-place RMW form that CountRegMoves scores
        higher).

    Returns the set of row indices that should surface the hint.
    """
    n = len(rows)
    if n < 6:
        return set()

    def _scan(col: int) -> tuple[int, str, str] | None:
        """Find ``(movsx_row, scratch_reg, result_reg)`` triple if
        the pattern is present on this side; None otherwise."""
        for i in range(n):
            insn = rows[i][col]
            scratch = _parse_movsx_word_reg(insn)
            if scratch is None:
                continue
            # Must be followed by `imul scratch, scratch, imm` within 1.
            imul_pair = _parse_imul_reg_reg_imm(
                rows[i + 1][col] if i + 1 < n else None)
            if imul_pair is None:
                continue
            if imul_pair[0] != scratch or imul_pair[1] != scratch:
                continue
            # Followed by `mov result_reg, [scratch + disp32]`.
            ld = _parse_mov_reg_indirect_disp32(
                rows[i + 2][col] if i + 2 < n else None)
            if ld is None:
                continue
            result_reg, base_reg = ld
            if base_reg != scratch:
                continue
            # Now look for the test/jne/mov-imm if-zero-replace
            # pattern within 4 rows of the load.
            for j in range(i + 3, min(i + 7, n)):
                t_reg = _parse_test_reg_self(rows[j][col])
                if t_reg is None:
                    continue
                if t_reg != result_reg:
                    break
                # The next row must be a near jne short forward.
                jne_insn = rows[j + 1][col] if j + 1 < n else None
                if jne_insn is None or _mnemonic(jne_insn) != "jne":
                    break
                # And the row after must be `mov result, imm`.
                mov_imm = _parse_mov_reg_imm(
                    rows[j + 2][col] if j + 2 < n else None)
                if mov_imm is None or mov_imm[0] != result_reg:
                    break
                return (i, scratch, result_reg)
            # If we get here, no if-zero-replace seen - pattern incomplete.
        return None

    ps_hit = _scan(0)
    rc_hit = _scan(1)
    if ps_hit is None or rc_hit is None:
        return set()
    ps_movsx_row, ps_scratch, ps_result = ps_hit
    rc_movsx_row, rc_scratch, rc_result = rc_hit
    # PS: scratch != result; RC: scratch == result.
    if ps_scratch == ps_result:
        return set()
    if rc_scratch != rc_result:
        return set()
    # And the result register should match between sides (it's the
    # call-arg target - typically EDX for arg2).
    if ps_result != rc_result:
        return set()

    # Surface the hint on whichever of the movsx rows is a diff row,
    # plus the imul and load rows.
    out: set[int] = set()
    for base_row in (ps_movsx_row, rc_movsx_row):
        for off in range(3):
            idx = base_row + off
            if 0 <= idx < n and rows[idx][2]:
                out.add(idx)
    return out


def detect_rule_82(
    row_idx: int,
    ps: InsnT | None,
    recomp: InsnT | None,
    rule_82_rows: set[int],
) -> Optional[RuleHint]:
    """If-zero-replace pins scratch to result register (Rule 82).

    Fires on the 3-instruction indexed load (movsx + imul + mov)
    immediately before an ``if (x == 0) x = N;`` test, where PS
    keeps the scratch in a separate register (EAX) while recomp
    merged it into the result register (EDX) via in-place RMW.

    The fix is the source-level rewrite from
    ``if (x == 0) x = N;`` to the equivalent ternary
    re-assignment ``x = x == 0 ? N : x;`` - this splits the live
    range of ``x`` so the indexed-load scratch can't co-exist
    with the post-test value in the same register.
    """
    if row_idx not in rule_82_rows:
        return None
    return RuleHint(
        rule="Rule 82",
        summary=(
            "if-zero-replace `if (x == 0) x = N;` pins indexed-load "
            "scratch to result register"
        ),
        fix=(
            "rewrite `if (x == 0) x = N;` as the ternary "
            "re-assignment `x = x == 0 ? N : x;`.  The ternary "
            "splits x's live range so the indexed-load scratch "
            "can't be merged into x's register; Watcom then picks "
            "EAX (DoubleRegs preference) for the scratch and emits "
            "the PS-matching three-instruction sequence."
        ),
    )


# ── Rules 141-147 (bbarian.c burn-down, 2026-06-12) ───────────────────────
#
# These detectors parse the instruction's STRUCTURED operands (capstone
# detail re-decoded from the raw bytes via c2.commands.insn_ast), not the
# rendered text: register identity, operand width, SIB scale and immediates
# come from the decoder itself.

from c2.commands import insn_ast as _ia


def _find_rule_141_rows(
    rows: list[tuple[InsnT | None, InsnT | None, bool]],
) -> dict[int, RuleHint]:
    """Live argument vs literal zero (Rule 141).

    A ONE-SIDED ``xor <argreg>, <argreg>`` whose following rows are all
    EQUAL register-staging up to an EQUAL ``call``: the side WITHOUT the
    xor passes a LIVE value already sitting in the register (a variable
    — typically the value computed just above), the side WITH the xor
    passes literal 0.  Worked examples: war/raider/horde_trouble pass
    ``months_since_last_X`` (still live in EDX from the ``++``) as
    chance_of_attack's 2nd arg — RC's literal 0 emitted the extra
    ``xor edx, edx``; citizen_maraude_to_target's 3rd
    try_a_citymap_square arg (both PS callsites xor ebx).
    """
    out: dict[int, RuleHint] = {}
    n = len(rows)
    for i, (ps, rc, is_diff) in enumerate(rows):
        if not is_diff:
            continue
        if ps is None and rc is not None:
            ins, zero_side = _ia.decode(rc), "RC"
        elif rc is None and ps is not None:
            ins, zero_side = _ia.decode(ps), "PS"
        else:
            continue
        reg = _ia.is_reg_self_xor(ins)
        if reg is None or reg not in _ia.WATCALL_ARG_REGS_2_4:
            continue
        # Forward: only EQUAL arg-staging rows (mov/xor/lea/push), then an
        # EQUAL call, within 6 rows.
        reached_call = False
        for j in range(i + 1, min(i + 7, n)):
            pj, rj, dj = rows[j]
            if dj or pj is None or rj is None:
                break
            dec = _ia.decode(pj)
            if dec is None:
                break
            if dec.mnemonic == "call":
                reached_call = True
                break
            if dec.mnemonic not in ("mov", "xor", "lea", "push"):
                break
        if not reached_call:
            continue
        if zero_side == "RC":
            out[i] = RuleHint(
                rule="Rule 141",
                summary=f"RC zeroes call arg {reg}; PS leaves a LIVE value "
                        f"in it",
                fix=f"the argument is a VARIABLE, not literal 0: trace what "
                    f"PS's {reg} holds at this callsite (c2 disasm — often "
                    f"the value computed/incremented just above, e.g. "
                    f"months_since_last_war in war_trouble) and pass that "
                    f"expression.",
            )
        else:
            out[i] = RuleHint(
                rule="Rule 141",
                summary=f"PS zeroes call arg {reg}; RC leaves a live value "
                        f"in it",
                fix=f"our source passes a variable that happens to sit in "
                    f"{reg}; PS passes literal 0 — replace the argument "
                    f"expression with 0.",
            )
    return out


def detect_rule_142(
    ps: InsnT | None,
    recomp: InsnT | None,
    next_ps: InsnT | None,
    next_recomp: InsnT | None,
) -> Optional[RuleHint]:
    """Return-constant staged via EDX + merged return suffix (Rule 142).

    PS ``mov edx, K`` vs RC ``mov eax, K`` (same constant) where PS's
    NEXT instruction is ``mov eax, edx`` (RC has no counterpart or is
    already in the epilogue): PS stages every return constant in EDX and
    copies to EAX at one shared point, so the ``mov eax, edx`` + epilogue
    suffix ComTail-merges across the return paths (the return-0 block
    becomes ``xor edx, edx; jmp <mov eax,edx>``).  Source shape: funnel
    the returns — ``if (g1 && g2) { body; return 1; } return 0;``.
    Worked: revolt_trouble (&&-guard, byte-exact); corpus witness:
    known_world (empire.c, byte-exact).
    """
    p, r = _ia.decode(ps), _ia.decode(recomp)
    if p is None or r is None:
        return None
    pm, rm = _ia.is_mov_reg_imm(p), _ia.is_mov_reg_imm(r)
    if pm is None or rm is None:
        return None
    if pm[0] != "edx" or rm[0] != "eax" or pm[1] != rm[1]:
        return None
    np = _ia.decode(next_ps)
    if _ia.is_mov_reg_reg(np, width=4) != ("eax", "edx"):
        return None
    nr = _ia.decode(next_recomp)
    if nr is not None and nr.mnemonic not in ("pop", "ret", "jmp"):
        return None
    return RuleHint(
        rule="Rule 142",
        summary=f"PS stages return constant {pm[1]:#x} via EDX "
                f"(mov edx, K; mov eax, edx) — merged return suffix",
        fix="funnel the return paths so they share the staged suffix: "
            "`if (guard1 && guard2) { body; return 1; } return 0;` "
            "(the &&-guard shape; worked: revolt_trouble, cf. "
            "known_world).  Plain per-site `return K;` emits the "
            "constant directly into EAX.",
    )


def _find_rule_143_rows(
    rows: list[tuple[InsnT | None, InsnT | None, bool]],
) -> dict[int, RuleHint]:
    """Consecutive compound RMWs on ONE memory lvalue (Rule 143).

    PS shows a byte-register COPY CHAIN — ``mov b2, b1`` between byte
    ALU steps, ONE load, ONE final byte store — while RC fuses the same
    ALU steps in place on a single byte register.  Cause: the source is
    consecutive compound RMWs on the SAME memory location
    (``m &= A; m |= b; m &= C;``): Watcom store-forwards each
    statement's load from the previous statement's pending value and
    dead-store-eliminates the intermediate stores, leaving one fresh
    byte register per statement (the copies).  Worked: do_land_trade
    (171b -> 0).  NOT the Rule 17 register-lvalue split — on a memory
    lvalue the split spelling with a temp regresses.
    """
    out: dict[int, RuleHint] = {}
    n = len(rows)
    for i, (ps, rc, is_diff) in enumerate(rows):
        if not is_diff or ps is None:
            continue
        p = _ia.decode(ps)
        cp = _ia.is_mov_reg_reg(p, width=1)
        if cp is None or cp[0] == cp[1]:
            continue
        if cp[0] not in _ia.BYTE_REGS or cp[1] not in _ia.BYTE_REGS:
            continue
        def _is_fused_rc(d: "_ia.Insn | None") -> bool:
            """In-place byte ALU or byte store: RC's fused form."""
            if d is None:
                return False
            if d.mnemonic in ("or", "and", "xor") and d.ops and \
                    d.ops[0].is_reg and d.ops[0].size == 1:
                return True
            st = _ia.is_mov_mem_reg(d)
            return st is not None and st[0].size == 1

        # RC side at this row (when present) must look like the FUSED form.
        r = _ia.decode(rc)
        saw_rc_fused = _is_fused_rc(r)
        if r is not None and not saw_rc_fused:
            continue
        # Forward on the PS side: >=1 byte ALU step, then a byte store,
        # within 8 PS rows (further copies allowed in between).  Collect
        # fused-RC evidence over the same window.
        saw_alu = saw_store = False
        for j in range(i + 1, min(i + 9, n)):
            saw_rc_fused = saw_rc_fused or _is_fused_rc(
                _ia.decode(rows[j][1]))
            pj = _ia.decode(rows[j][0])
            if pj is None:
                continue
            if pj.mnemonic in ("or", "and", "xor") and pj.ops and \
                    pj.ops[0].is_reg and pj.ops[0].size == 1:
                saw_alu = True
                continue
            st = _ia.is_mov_mem_reg(pj)
            if st is not None and st[0].size == 1:
                saw_store = True
                break
            if _ia.is_mov_reg_reg(pj, width=1) is not None:
                continue                       # another copy in the chain
            break
        if saw_alu and saw_store and saw_rc_fused:
            out[i] = RuleHint(
                rule="Rule 143",
                summary=f"byte RMW copy chain (PS copies {cp[1]}->{cp[0]} "
                        f"between ALU steps, single load + single store)",
                fix="write CONSECUTIVE compound RMWs on the memory lvalue "
                    "itself (`m &= A; m |= b; m &= C;`): Watcom "
                    "store-forwards and dead-store-eliminates, emitting "
                    "one load, a fresh byte reg per statement, one final "
                    "store (worked: do_land_trade).  Do NOT use the "
                    "Rule 17 register split — on memory it emits two RMWs "
                    "and regresses.",
            )
    return out


def _find_rule_144_rows(
    rows: list[tuple[InsnT | None, InsnT | None, bool]],
) -> dict[int, RuleHint]:
    """``while (i++ < N)`` loop head (Rule 144).

    PS's loop head is ``mov rA, rB`` / ``inc rB`` / ``cmp rA, IMM`` with
    a BACKWARD jump targeting the ``mov``: the comparison tests the OLD
    value (the copy) while the counter has already advanced — only the
    top-tested post-increment ``while (i++ < N)`` produces this; a
    for-loop puts the inc at the bottom.  Worked:
    get_region_invasion_points (93b -> 0).
    """
    out: dict[int, RuleHint] = {}
    ps_rows = [(i, _ia.decode(r[0])) for i, r in enumerate(rows)
               if r[0] is not None]
    back_targets = set()
    for _i, dec in ps_rows:
        t = _ia.jump_target(dec)
        if t is not None and dec is not None and t < dec.addr:
            back_targets.add(t)
    if not back_targets:
        return out
    for k in range(len(ps_rows) - 2):
        ia_, a = ps_rows[k]
        ib_, b = ps_rows[k + 1]
        ic_, c = ps_rows[k + 2]
        if a is None or b is None or c is None:
            continue
        if a.addr not in back_targets:
            continue
        cp = _ia.is_mov_reg_reg(a, width=4)
        if cp is None or cp[0] == cp[1]:
            continue
        r_old, r_ctr = cp
        if b.mnemonic != "inc" or len(b.ops) != 1 or \
                not b.ops[0].is_reg or b.ops[0].reg != r_ctr:
            continue
        cmp = _ia.is_cmp_reg_imm(c)
        if cmp is None or cmp[0] != r_old:
            continue
        if not any(rows[t][2] for t in (ia_, ib_, ic_)):
            continue                          # all three rows equal: no diff
        out[ia_] = RuleHint(
            rule="Rule 144",
            summary=f"PS loop head copies OLD {r_ctr} into {r_old}, "
                    f"increments, then compares the OLD value "
                    f"(post-increment tested at top)",
            fix=f"write `i = 0; while (i++ < {cmp[1]:#x}) {{ ... }}` — the "
                f"copy holds the pre-increment value for the compare; a "
                f"for-loop bottom inc cannot produce this shape (worked: "
                f"get_region_invasion_points).",
        )
    return out


def _find_rule_145_rows(
    rows: list[tuple[InsnT | None, InsnT | None, bool]],
) -> dict[int, RuleHint]:
    """Signed ``% (1<<k)`` vs unsigned ``& (2^k - 1)`` (Rule 145).

    One side computes a SIGNED remainder (``mov rD, 2^k`` … ``idiv rD``)
    where the other masks (``and r, 2^k-1``): the source spells ``% N``
    (signed semantics, different for negatives) — not ``& (N-1)``.
    Worked: barbarian_invades_city's ``(world_dir + 4) % 8`` (264b -> 0
    with the other levers).
    """
    out: dict[int, RuleHint] = {}
    n = len(rows)
    for i, (ps, rc, is_diff) in enumerate(rows):
        for side in (0, 1):
            ins = _ia.decode(rows[i][side])
            if ins is None or ins.mnemonic != "idiv":
                continue
            if len(ins.ops) != 1 or not ins.ops[0].is_reg:
                continue
            div_reg = ins.ops[0].reg
            # A diff row must exist nearby (the idiv row itself may align
            # against an unrelated equal row).
            if not any(rows[j][2] for j in
                       range(max(0, i - 2), min(n, i + 3))):
                continue
            # Same side, backward: the divisor materialisation.
            divisor = None
            seen = 0
            for j in range(i - 1, -1, -1):
                cand = _ia.decode(rows[j][side])
                if cand is None:
                    continue
                seen += 1
                if seen > 4:
                    break
                mv = _ia.is_mov_reg_imm(cand)
                if mv is not None and mv[0] == div_reg:
                    v = mv[1]
                    if v > 1 and (v & (v - 1)) == 0:
                        divisor = v
                    break
            if divisor is None:
                continue
            # Other side, +-4 rows: and r, divisor-1.
            other = 1 - side
            for j in range(max(0, i - 4), min(n, i + 5)):
                cand = _ia.decode(rows[j][other])
                if cand is None or cand.mnemonic != "and":
                    continue
                if len(cand.ops) == 2 and cand.ops[1].is_imm and \
                        cand.ops[1].imm == divisor - 1:
                    rem_side = "PS" if side == 0 else "RC"
                    mask_side = "RC" if side == 0 else "PS"
                    fix = (
                        f"write `x % {divisor}` — {rem_side} computes the "
                        f"SIGNED remainder (idiv); `x & {divisor - 1}` only "
                        f"matches for unsigned/known-positive values "
                        f"(worked: barbarian_invades_city world_dir)."
                        if side == 0 else
                        f"write `x & {divisor - 1}` — PS masks; our "
                        f"`x % {divisor}` emits the signed idiv sequence."
                    )
                    out[i] = RuleHint(
                        rule="Rule 145",
                        summary=f"{rem_side} signed remainder (idiv by "
                                f"{divisor}) vs {mask_side} mask "
                                f"(and {divisor - 1:#x})",
                        fix=fix,
                    )
                    break
    return out


def _find_rule_146_rows(
    rows: list[tuple[InsnT | None, InsnT | None, bool]],
) -> dict[int, RuleHint]:
    """De-invent the local: field-read CSE takes the callee-save (Rule 146).

    A compare CHAIN (>=2 ``cmp reg, IMM`` replace rows, same immediates
    both sides) where RC's register is EAX and PS's is one callee-save:
    RC fused a NAMED local into EAX (1-byte-shorter ``3D`` encodings,
    cascading through every later jump); PS's value is the CSE temp of
    REPEATED global/field reads, homed in a callee-save.  Delete the
    local and spell the memory read in each compare.  Worked:
    continue_battle (battle_state -> EBP), barbarian_invades_city
    (total_troops -> EBX, 264b -> 0), get_morale_and_readiness.
    """
    pairs: list[tuple[int, str]] = []
    for i, (ps, rc, is_diff) in enumerate(rows):
        if not is_diff or ps is None or rc is None:
            continue
        pc = _ia.is_cmp_reg_imm(_ia.decode(ps))
        rcmp = _ia.is_cmp_reg_imm(_ia.decode(rc))
        if pc is None or rcmp is None:
            continue
        if pc[1] != rcmp[1]:
            continue
        if pc[0] in _ia.CALLEE_SAVE32 and rcmp[0] == "eax":
            pairs.append((i, pc[0]))
    if len(pairs) < 2 or len({r for _, r in pairs}) != 1:
        return {}
    reg = pairs[0][1]
    hint = RuleHint(
        rule="Rule 146",
        summary=f"compare chain: RC fused a named local into EAX "
                f"(short cmp encodings); PS holds the value in "
                f"{reg} — the CSE temp of repeated memory reads",
        fix="de-invent the local: spell the global/field read in EACH "
            "compare (`if (army_list[i].total_troops >= K) ...`); "
            "Watcom's CSE homes the repeated reads in the callee-save "
            "exactly as PS (worked: continue_battle battle_state->EBP, "
            "barbarian_invades_city total_troops->EBX).",
    )
    # Anchor on the defining load when present: a replace row
    # `mov <reg>, [mem]` vs `mov eax, [mem]` shortly before the first cmp.
    first = pairs[0][0]
    for i in range(first - 1, max(-1, first - 6), -1):
        ps, rc, is_diff = rows[i]
        if not is_diff or ps is None or rc is None:
            continue
        pl = _ia.is_mov_reg_mem(_ia.decode(ps))
        rl = _ia.is_mov_reg_mem(_ia.decode(rc))
        if pl is not None and rl is not None and \
                pl[0] == reg and rl[0] == "eax":
            return {i: hint}
    return {first: hint}


def _find_rule_147_rows(
    rows: list[tuple[InsnT | None, InsnT | None, bool]],
) -> dict[int, RuleHint]:
    """Array element width/stride mismatch (Rule 147).

    One side reads a 4-byte field through a SCALED index
    (``mov r32, [rI*4 + disp32]``) while the other side, within a few
    rows, reads a 1-byte field UNSCALED through the SAME index value
    (``mov r8, byte [rI + disp32]``, base register == the scaled side's
    index register): the array's element/field type is declared with the
    wrong width — stride and operand width diverge TOGETHER, so it is
    the declaration, not regalloc.  One header edit moves every user.
    Worked: struct troop_numbers_rec fields are int, not unsigned char
    (entities.h; flipped all four *_trouble functions).

    Function-level scan because the diff aligner rarely pairs the two
    loads on one row — the different instruction counts around them
    produce insert/delete runs.
    """
    def scaled_wide(d: "_ia.Insn | None"):
        got = _ia.is_mov_reg_mem(d)
        if got is None:
            return None
        _reg, mem = got
        if mem.size == 4 and mem.scale in (2, 4) and mem.index:
            return mem
        return None

    def byte_unscaled(d: "_ia.Insn | None"):
        got = _ia.is_mov_reg_mem(d)
        if got is None:
            return None
        reg, mem = got
        if mem.size == 1 and mem.scale == 1 and mem.base and mem.disp:
            return mem
        return None

    out: dict[int, RuleHint] = {}
    n = len(rows)
    for i, (ps, rc, is_diff) in enumerate(rows):
        if not is_diff:
            continue
        for side, wide_name, narrow_name in ((0, "PS", "RC"),
                                             (1, "RC", "PS")):
            mem_w = scaled_wide(_ia.decode(rows[i][side]))
            if mem_w is None:
                continue
            other = 1 - side
            for j in range(max(0, i - 5), min(n, i + 6)):
                if not rows[j][2]:
                    continue
                mem_n = byte_unscaled(_ia.decode(rows[j][other]))
                if mem_n is None or mem_n.base != mem_w.index:
                    continue
                out[i] = RuleHint(
                    rule="Rule 147",
                    summary=f"{wide_name} reads a 4-byte field through a "
                            f"scaled index ({mem_w.index}*{mem_w.scale}); "
                            f"{narrow_name} a 1-byte field unscaled through "
                            f"the same index — element width/stride "
                            f"mismatch",
                    fix="fix the array's element/field type in entities.h "
                        "(or _TYPE_OVERRIDES): width and stride diverge "
                        "TOGETHER, so this is the declaration, not "
                        "regalloc (worked: troop_numbers_rec char->int "
                        "flipped all four *_trouble functions).",
                )
                break
            if i in out:
                break
    return out


def _find_rule_150_rows(
    rows: list[tuple[InsnT | None, InsnT | None, bool]],
) -> dict[int, RuleHint]:
    """`goto label;` (target = mid-function) vs `return;` (target = epilogue).

    Both sides emit a jcc/jmp with the same mnemonic at the same offset,
    but PS's target lands in the function EPILOGUE (the pop+ret
    sequence) while RC's target is a label EARLIER in the function whose
    body is `if (...) return;` plus cleanup code.  PS's source uses
    `return;` at these sites; RC's uses `goto <label>;` to a label that
    has additional cleanup the early-exit paths should SKIP.

    Replace the `goto <label>;` sites with plain `return;` -- Watcom
    will jmp directly to the function epilogue exactly as PS, and the
    cleanup code stays reachable only via the natural fall-through.
    Semantically equivalent when the early-exit paths represent
    terminal-state cases (no cleanup needed).

    Worked: main_game_loop (454 b -> 0); three `if (game_state == X)
    goto restart_check;` sites all rewritten to `return;` because the
    restart_check label's cleanup (decay counters, message refresh,
    ambient FX) is irrelevant on game-end states 1/2/3.

    INVERSE of Rule 148 (which converts return -> goto-end for the
    epilogue-funnel-when-epilogue-is-big case).  Rule 150 fires when
    PS already funnels to epilogue and RC funnels to a mid-function
    label instead.
    """
    # Build PS instruction map keyed by offset for epilogue lookup.
    ps_by_off: dict[int, _ia.Insn] = {}
    for r in rows:
        if r[0] is not None:
            d = _ia.decode(r[0])
            if d is not None:
                ps_by_off[d.addr] = d
    if not ps_by_off:
        return {}

    def is_epilogue_start(addr: int) -> bool:
        """True if PS instruction at addr begins a pop…pop;ret sequence."""
        cur = addr
        pops = 0
        while cur in ps_by_off:
            ins = ps_by_off[cur]
            if ins.mnemonic == "pop":
                pops += 1
                cur += ins.size
            elif ins.mnemonic == "ret":
                return pops >= 2
            else:
                return False
        return False

    # Pre-collect candidate jumps so we can require >= 2 hitting the same
    # PS target (the goto-label pattern has multiple sites converging).
    candidates: list[tuple[int, int, int, _ia.Insn]] = []
    for i, (ps, rc, is_diff) in enumerate(rows):
        if not is_diff or ps is None or rc is None:
            continue
        p, r = _ia.decode(ps), _ia.decode(rc)
        if p is None or r is None or p.mnemonic != r.mnemonic:
            continue
        if not (p.mnemonic == "jmp" or p.mnemonic.startswith("j")):
            continue
        ps_t = _ia.jump_target(p)
        rc_t = _ia.jump_target(r)
        if ps_t is None or rc_t is None:
            continue
        # Forward jumps only, and PS strictly further than RC by >= 20 b.
        if ps_t <= p.addr or rc_t <= r.addr or ps_t <= rc_t + 20:
            continue
        # PS must target the epilogue; RC must NOT (else it is a different shape).
        if not is_epilogue_start(ps_t) or is_epilogue_start(rc_t):
            continue
        candidates.append((i, ps_t, rc_t, p))

    # Require >= 2 candidates sharing the same PS epilogue target (the
    # multi-site early-exit pattern; a lone match is likely a different rule).
    by_target: dict[int, list[tuple[int, int, _ia.Insn]]] = {}
    for row_i, ps_t, rc_t, p in candidates:
        by_target.setdefault(ps_t, []).append((row_i, rc_t, p))

    out: dict[int, RuleHint] = {}
    for ps_t, sites in by_target.items():
        if len(sites) < 2:
            continue
        rc_targets = sorted({rc_t for _i, rc_t, _p in sites})
        rc_t_str = ", ".join(f"+{t:#x}" for t in rc_targets[:3])
        for row_i, _rc_t, p in sites:
            out[row_i] = RuleHint(
                rule="Rule 150",
                summary=f"PS {p.mnemonic} skips to epilogue at +{ps_t:#x}; "
                        f"RC's target {rc_t_str} is mid-function ("
                        f"{len(sites)} sites converge here)",
                fix="PS source uses `return;` here; ours uses `goto <label>;` "
                    "to a mid-function label whose body is `if (...) return;` "
                    "plus cleanup code that the early-exit paths should "
                    "SKIP.  Replace each `goto X;` with `return;` -- the "
                    "label's cleanup remains reachable via natural "
                    "fall-through.  Worked: main_game_loop (454 b -> 0); "
                    "INVERSE of Rule 148 (which converts return->goto-end "
                    "for big epilogues).",
            )
    return out


# ── Driver ─────────────────────────────────────────────────────────

# ── Rule 151 — int vs short local: movsx/cwde sign-extension mismatch ──────

def detect_rule_151(ps, recomp, next_ps, next_recomp, prev_ps, prev_recomp):
    """Rule 151: a `short` local that PS declares as `int`.

    Pattern A (reg-to-reg widen before compare):
      PS:  cmp <reg32>, imm                   (no prior widening)
      RC:  movsx eax, <reg16>; cmp eax, imm   (widens first)

    Pattern B (field-load width: movsx vs mov-word + cwde):
      PS:  movsx eax, word ptr [mem]  (0F BF)
      RC:  mov   ax,  word ptr [mem]  (66 8B)   [+ cwde on next row]
    """
    if ps is None or recomp is None:
        return None
    pa, ra = ps[3], recomp[3]
    # Pattern A: RC has `movsx eax, <reg16/32>` and next is `cmp eax, imm`,
    # while PS has `cmp <reg>, imm` directly (no movsx).
    if (ra.startswith("movsx eax, ") and next_recomp and next_ps
            and _mnemonic(next_ps) == "cmp" and _mnemonic(next_recomp) == "cmp"
            and _mnemonic(ps) == "cmp"):
        return RuleHint(
            rule="Rule 151",
            summary="RC sign-extends (movsx) before compare; PS compares directly "
                    "→ the local is `int`, not `short`",
            fix="change `short` → `int` for the variable being compared",
        )
    # Pattern B: PS movsx eax, word ptr [mem]  vs  RC mov ax, word ptr [mem]
    if (pa.startswith("movsx eax, word ptr ") and ra.startswith("mov ax, word ptr ")):
        return RuleHint(
            rule="Rule 151",
            summary="PS loads field via `movsx` (int local); RC loads via "
                    "`mov ax` (short local)",
            fix="change `short` → `int` for the variable receiving the field load",
        )
    # Pattern B reverse: RC movsx eax, word ptr [mem]  vs  PS mov ax, word ptr [mem]
    # -> our local is `int` but PS had `short`.
    if (ra.startswith("movsx eax, word ptr ") and pa.startswith("mov ax, word ptr ")):
        return RuleHint(
            rule="Rule 151",
            summary="RC loads field via `movsx` (int local); PS loads via "
                    "`mov ax` (short local)",
            fix="change `int` → `short` for the variable receiving the field load",
        )
    # Pattern C: RC `cwde` (98) that PS lacks — the widening after a word-width
    # load. (When BOTH sides have cwde/movsx, that's Rule 133 word-seat, not 151.)
    if ra == "cwde" and pa != "cwde" and _mnemonic(ps) != "movsx":
        return RuleHint(
            rule="Rule 151",
            summary="RC widens with `cwde` (short→int); PS has no widening "
                    "→ the local is `int`, not `short`",
            fix="change `short` → `int` for the variable being widened",
        )
    # Pattern C reverse: PS `cwde` that RC lacks.
    if pa == "cwde" and ra != "cwde" and _mnemonic(recomp) != "movsx":
        return RuleHint(
            rule="Rule 151",
            summary="PS widens with `cwde` (short→int); RC has no widening "
                    "→ the local should be `short`, not `int`",
            fix="change `int` → `short` for the variable being widened",
        )
    return None


# ── Rule 152 — explicit `else if (var == K)` vs bare `else` ────────────────

def _find_rule_152_rows(rows):
    """Find PS-only `cmp reg, literal; jne/je` pairs (delete rows) that
    indicate an explicit `else if` check PS has but RC lacks."""
    hits = {}
    n = len(rows)
    for i in range(n - 1):
        ps0, _, d0 = rows[i]
        ps1, _, d1 = rows[i + 1]
        if not d0 or not d1:
            continue
        rc0 = rows[i][1]
        rc1 = rows[i + 1][1]
        if rc0 is not None or rc1 is not None:
            continue  # not a pure delete pair
        if ps0 is None or ps1 is None:
            continue
        a0, a1 = ps0[3], ps1[3]
        if (_mnemonic_of(a0) == "cmp" and _mnemonic_of(a1) in ("jne", "je", "jg", "jl", "jge", "jle")
                and re.search(r", (0x[0-9a-f]+|\d+)$", a0)):
            lit = re.search(r", (0x[0-9a-f]+|\d+)$", a0).group(1)
            hits[i] = RuleHint(
                rule="Rule 152",
                summary=f"PS has explicit `cmp {{reg}}, {lit}; {_mnemonic_of(a1)}` "
                        f"(else-if check) that RC lacks",
                fix=f"change bare `else` to `else if (var == {lit})`",
            )
            hits[i + 1] = hits[i]  # claim both rows
    return hits


def _mnemonic_of(asm):
    return asm.split()[0] if asm else ""


def detect_hints(
    rows: list[tuple[InsnT | None, InsnT | None, bool]],
    ps_abs_base: int,
    recomp_abs_base: int,
    ps_fix: set[int],
    recomp_fix: set[int],
) -> list[Optional[RuleHint]]:
    """Run all detectors over a sequence of (ps, recomp, is_diff) rows.

    Returns a list parallel to `rows`, with a `RuleHint` (or None) per
    row. Only diff rows are inspected - equal rows always return None.
    """
    rule_27_pairs   = _find_rule_27_pairs(rows)
    rule_28_swap    = _find_rule_28_swap(rows)
    rule_28b_extras = _find_rule_28b_extras(rows)
    rule_44_excess  = _find_rule_44_excess(rows)
    rule_106_excess = _find_rule_106_excess(rows)
    rule_10_excess  = _find_rule_10_excess(rows)
    rule_49b_pairs  = _find_rule_49b_pairs(rows)
    rule_84_rows    = _find_rule_84_rows(rows)
    rule_35_pairs   = _find_rule_35_pairs(rows)
    rule_78_rows    = _find_rule_78_copies(rows)
    rule_81_rows    = _find_rule_81_swap(rows)
    rule_82_rows    = _find_rule_82_pattern(rows)
    rule_132_rows   = _find_rule_132_rows(rows)
    rule_140_rows   = _find_rule_140_rows(rows)
    rule_141_rows   = _find_rule_141_rows(rows)
    rule_143_rows   = _find_rule_143_rows(rows)
    rule_144_rows   = _find_rule_144_rows(rows)
    rule_145_rows   = _find_rule_145_rows(rows)
    rule_146_rows   = _find_rule_146_rows(rows)
    rule_147_rows   = _find_rule_147_rows(rows)
    rule_150_rows   = _find_rule_150_rows(rows)
    rule_152_rows   = _find_rule_152_rows(rows)

    hints: list[Optional[RuleHint]] = []
    for i, (ps, recomp, is_diff) in enumerate(rows):
        if not is_diff:
            hints.append(None)
            continue

        prev_ps     = rows[i - 1][0] if i > 0 else None
        prev_recomp = rows[i - 1][1] if i > 0 else None
        next_ps     = rows[i + 1][0] if i + 1 < len(rows) else None
        next_recomp = rows[i + 1][1] if i + 1 < len(rows) else None
        next2_ps     = rows[i + 2][0] if i + 2 < len(rows) else None
        next2_recomp = rows[i + 2][1] if i + 2 < len(rows) else None
        prev2_recomp = rows[i - 2][1] if i >= 2 else None

        # Try each detector in priority order; first match wins.
        # Order: more-specific patterns first, generic fallbacks last.
        h = (
            rule_140_rows.get(i)
            or rule_141_rows.get(i)
            or rule_144_rows.get(i)
            or rule_145_rows.get(i)
            or rule_146_rows.get(i)
            or rule_150_rows.get(i)
            or detect_rule_142(ps, recomp, next_ps, next_recomp)
            # Rule 143 must claim its rows BEFORE Rule 17: the same byte-reg
            # copy also matches the register-lvalue split shape, whose fix
            # REGRESSES on a memory lvalue.
            or rule_143_rows.get(i)
            or rule_147_rows.get(i)
            or detect_rule_139(ps, recomp, next_ps, next_recomp,
                               prev_ps, prev_recomp)
            or detect_rule_16(ps, recomp)
            or detect_rule_8(ps, recomp, next_ps, next_recomp,
                              prev_ps, prev_recomp)
            or detect_rule_5(ps, recomp, next_ps, next_recomp)
            or detect_rule_17(ps, recomp, next_ps, next_recomp,
                              prev_ps, prev_recomp)
            or detect_rule_9(ps, recomp, prev_ps, prev_recomp)
            or detect_rule_4b(ps, recomp, next_ps, next_recomp)
            or detect_rule_4(ps, recomp, prev_ps, prev_recomp)
            or detect_rule_90(ps, recomp, prev_ps, prev_recomp)
            or detect_rule_19(ps, recomp)
            or detect_rule_24a(ps, recomp, next_ps, next_recomp,
                               prev_ps, prev_recomp)
            or detect_rule_24b(ps, recomp, next_ps, next_recomp,
                               prev_ps, prev_recomp)
            or detect_rule_26(ps, recomp)
            or detect_rule_12(ps, recomp, ps_abs_base, recomp_abs_base,
                              ps_fix, recomp_fix)
            or detect_rule_14(ps, recomp, next_ps, next_recomp)
            or detect_rule_100(ps, recomp, next_ps, next_recomp,
                               ps_abs_base, recomp_abs_base,
                               ps_fix, recomp_fix)
            # A-band peephole detectors (Rules 29/37/40/43/44/49/51/53/62).
            or detect_rule_29(ps, recomp, next_ps, next_recomp)
            or detect_rule_37(ps, recomp, prev_ps, prev_recomp)
            or detect_rule_40(ps, recomp, prev_ps, prev_recomp)
            or detect_rule_43(ps, recomp, next_ps, next_recomp,
                              prev_ps, prev_recomp)
            or detect_rule_44(i, ps, recomp, rule_44_excess,
                              prev_ps, prev_recomp,
                              next_ps, next_recomp)
            or detect_rule_106(i, ps, recomp, rule_106_excess)
            # B-band: function-level pre-scan detectors.
            or detect_rule_10(i, ps, recomp, rule_10_excess)
            or detect_rule_35a(ps, recomp)
            or detect_rule_84(i, ps, recomp, rule_84_rows)
            or detect_rule_49b(i, ps, recomp, rule_49b_pairs)
            or detect_rule_35(i, ps, recomp, rule_35_pairs)
            or detect_rule_20(ps, recomp)
            or detect_rule_49(ps, recomp, next_ps, next_recomp,
                              prev_ps, prev_recomp)
            or detect_rule_51(ps, recomp)
            or detect_rule_53(ps, recomp)
            or detect_rule_62(ps, recomp, next_ps, next_recomp,
                              prev_ps, prev_recomp)
            or detect_rule_91(ps, recomp, next_ps, next2_ps,
                               next_recomp, next2_recomp)
            or detect_rule_96(ps, recomp, prev_recomp, prev2_recomp)
            or detect_rule_99(ps, recomp)
            or detect_rule_72(ps, recomp, next_ps, next_recomp)
            or detect_rule_133(ps, recomp)
            or detect_rule_132(i, rule_132_rows)
            or detect_rule_81(i, ps, recomp, rule_81_rows)
            or detect_rule_82(i, ps, recomp, rule_82_rows)
            or detect_rule_78(i, ps, recomp, rule_78_rows)
            or detect_rule_98(ps, recomp)
            or detect_rule_109(ps, recomp)
            or detect_rule_151(ps, recomp, next_ps, next_recomp,
                              prev_ps, prev_recomp)
            or rule_152_rows.get(i)
            or detect_add_vs_lea_copy(ps, recomp, next_ps, next_recomp)
            or detect_rule_73(ps, recomp,
                              ps_abs_base, recomp_abs_base,
                              ps_fix, recomp_fix)
            # Rule 110 fires LAST among the mov-store detectors: an
            # addressing-mode mismatch (Rule 73 cached-pointer) also flips the
            # const-store form, and there the fix is Rule 73 - let it claim
            # those rows first.  Rule 110 then catches only the pure form
            # (ref-count) mismatches with matching addressing.
            or detect_rule_110(ps, recomp, prev_ps, prev_recomp)
        )
        # Rule 27 / Rule 28 fire last (lowest priority): only annotate
        # rows that none of the other detectors already explained.
        if h is None and i in rule_27_pairs:
            _peer, ps_text, rc_text = rule_27_pairs[i]
            h = _make_rule_27_hint(ps_text, rc_text)
        if h is None:
            h = detect_rule_28(
                ps, recomp, rule_28_swap,
                ps_abs_base, recomp_abs_base, ps_fix, recomp_fix,
            )
        if h is None:
            h = detect_rule_28b(ps, recomp, rule_28b_extras)
        if h is None:
            h = detect_byte_reg_swap(ps, recomp,
                                     ps_abs_base, recomp_abs_base,
                                     ps_fix, recomp_fix)
        if h is None:
            h = detect_reg_identity_swap(ps, recomp,
                                         ps_abs_base, recomp_abs_base,
                                         ps_fix, recomp_fix)
        hints.append(h)
    return hints


def histogram(hints: list[Optional[RuleHint]]) -> dict[str, int]:
    """Count rule occurrences across a hint list."""
    h: dict[str, int] = {}
    for hint in hints:
        if hint is None:
            continue
        h[hint.rule] = h.get(hint.rule, 0) + 1
    return h
