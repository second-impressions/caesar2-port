"""strcpy/memcpy intrinsic expansion under -oi — what triggers
``movsd; movsd; movsw; movsb`` for ``strcpy(dst, "unused.wav")``.

PS.EXE function ``free_up_sslot`` (42 b @ 0x129B1) emits::

    push edx; push esi; push edi
    mov edx, eax           ; eax = slot, edx = slot copy
    shl eax, 2             ; slot * 4
    add eax, edx           ; slot * 5  (CSE'd index)
    mov  [eax*4 + 0xd2a8], 0x3e8         ; ss_entries[slot*5] = 1000
    lea  edi, [eax*4 + 0xd2ac]           ; &ss_entries[slot*5+1]
    mov  esi, 0x448                       ; "unused.wav" in data seg
    movsd; movsd; movsw; movsb            ; 11-byte unrolled strcpy
    pop edi; pop esi; pop edx; ret

Two PS-specific traits we want to reproduce:

  1.  CSE of ``slot*5`` so both the int-store and the `lea edi`
      reuse a single ``slot_index_in_ints`` value via *4 scaling.

  2.  Unrolled ``strcpy`` to 4+4+2+1 movs for an 11-byte literal.

Run with::

    uv run c2 cgex run strcpy-intrinsic
    uv run c2 cgex run strcpy-intrinsic --trial baseline
"""

from c2.commands.cgex import Experiment

PS_FN = "free_up_sslot"

# A small extra_defs gives the trials access to the ss_entries[] global
# at the same byte address pattern PS uses.  Size 50 ints = 10 entries
# of 5 ints each (count + 4 ints = 16-byte name field).
EXTRA_DEFS = """
int ss_entries[50];
"""

PRELUDE = """
extern int ss_entries[50];
extern void *memcpy(void *, const void *, unsigned);
extern char *strcpy(char *, const char *);
#pragma intrinsic(strcpy, memcpy)
"""

exp = Experiment(
    name="strcpy-intrinsic",
    ps_function=PS_FN,
    chk=False,
    externs={},
    extra_defs=EXTRA_DEFS,
    prelude=PRELUDE,
    cflags="-bt=dos -mf -4r -s -oi",
)


# ── trial 0: baseline = current decomp/src/pcsound.c body ─────────
exp.add(
    "baseline-strcpy",
    """
void free_up_sslot(int slot)
{
    ss_entries[slot * 5]     = 1000;
    strcpy((char *)&ss_entries[slot * 5 + 1], "unused.wav");
}
""",
    note="current source: two indexed expressions, strcpy",
)


# ── trial 1: pointer alias to CSE the index ─────────────────────
exp.add(
    "alias-pointer-strcpy",
    """
void free_up_sslot(int slot)
{
    int *e = &ss_entries[slot * 5];
    *e = 1000;
    strcpy((char *)(e + 1), "unused.wav");
}
""",
    note="local int*e to share index across both ops",
)


# ── trial 2: alias + memcpy with literal length ──────────────────
exp.add(
    "alias-pointer-memcpy11",
    """
void free_up_sslot(int slot)
{
    int *e = &ss_entries[slot * 5];
    *e = 1000;
    memcpy(e + 1, "unused.wav", 11);
}
""",
    note="local int*e + memcpy(.., 11) — should unroll to movsd/movsw/movsb",
)


# ── trial 3: same as baseline but memcpy ─────────────────────────
exp.add(
    "baseline-memcpy11",
    """
void free_up_sslot(int slot)
{
    ss_entries[slot * 5] = 1000;
    memcpy(&ss_entries[slot * 5 + 1], "unused.wav", 11);
}
""",
    note="two indexed exprs + memcpy(.., 11)",
)


# ── trial 4: index-only alias (no pointer) ───────────────────────
exp.add(
    "alias-index-strcpy",
    """
void free_up_sslot(int slot)
{
    int idx = slot * 5;
    ss_entries[idx] = 1000;
    strcpy((char *)&ss_entries[idx + 1], "unused.wav");
}
""",
    note="local int idx as shared index",
)


# ── trial 5: index-only alias + memcpy ───────────────────────────
exp.add(
    "alias-index-memcpy11",
    """
void free_up_sslot(int slot)
{
    int idx = slot * 5;
    ss_entries[idx] = 1000;
    memcpy(&ss_entries[idx + 1], "unused.wav", 11);
}
""",
    note="shared idx + memcpy(.., 11)",
)


# ── trial 6: char-cast pointer alias ─────────────────────────────
exp.add(
    "alias-char-pointer-strcpy",
    """
void free_up_sslot(int slot)
{
    char *e = (char *)&ss_entries[slot * 5];
    *(int *)e = 1000;
    strcpy(e + 4, "unused.wav");
}
""",
    note="char* alias, +4 offset for name field",
)


# ── trial 7: char-cast pointer + memcpy ──────────────────────────
exp.add(
    "alias-char-pointer-memcpy11",
    """
void free_up_sslot(int slot)
{
    char *e = (char *)&ss_entries[slot * 5];
    *(int *)e = 1000;
    memcpy(e + 4, "unused.wav", 11);
}
""",
    note="char* alias + memcpy(.., 11)",
)


# ── trial 8: no -oi ──────────────────────────────────────────────
exp.add(
    "baseline-strcpy-no-oi",
    """
void free_up_sslot(int slot)
{
    ss_entries[slot * 5]     = 1000;
    strcpy((char *)&ss_entries[slot * 5 + 1], "unused.wav");
}
""",
    cflags="-bt=dos -mf -4r -s",
    note="without -oi — sanity check: should call _strcpy",
)


# ── trial 9: index var but no shift via &x[idx] ─────────────────
# PS uses `[eax*4 + base]` SIB encoding; my "alias-index-strcpy"
# does `shl esi,2; [esi+base]`.  Try various tweaks to keep the
# compiler from pre-scaling the index.

exp.add(
    "ptr-into-int-array-strcpy",
    """
void free_up_sslot(int slot)
{
    int *base = ss_entries;
    base[slot * 5]     = 1000;
    strcpy((char *)&base[slot * 5 + 1], "unused.wav");
}
""",
    note="local pointer alias to ss_entries[0]",
)


# ── trial 10: only one shared index, used twice as array indices ─
exp.add(
    "shared-element-index",
    """
void free_up_sslot(int slot)
{
    int e = slot * 5;
    ss_entries[e]     = 1000;
    strcpy((char *)&ss_entries[e + 1], "unused.wav");
}
""",
    note="explicit element index (variant of alias-index-strcpy)",
)


# ── trial 11: index expressed as (slot<<2)+slot ────────────────
exp.add(
    "shift-add-explicit",
    """
void free_up_sslot(int slot)
{
    int e = (slot << 2) + slot;
    ss_entries[e]     = 1000;
    strcpy((char *)&ss_entries[e + 1], "unused.wav");
}
""",
    note="manual shift+add to mirror what PS computes for slot*5",
)


# ── trial 12: split count vs name with int+1 ───────────────────
exp.add(
    "split-count-name",
    """
void free_up_sslot(int slot)
{
    int *count_ptr = &ss_entries[slot * 5];
    int *name_ptr  = count_ptr + 1;
    *count_ptr = 1000;
    strcpy((char *)name_ptr, "unused.wav");
}
""",
    note="separate count/name pointers - explicit +1 offset",
)


# ── trial 13: char-cast both, name as +4 byte offset ───────────
exp.add(
    "char-base-byte-offset",
    """
void free_up_sslot(int slot)
{
    char *base = (char *)ss_entries + slot * 20;
    *(int *)base = 1000;
    strcpy(base + 4, "unused.wav");
}
""",
    note="explicit byte arithmetic to encourage [base + disp]",
)


# ── trial 14: baseline w/ ss_entries+slot*5+1 syntax ────────────
exp.add(
    "ptr-add-1",
    """
void free_up_sslot(int slot)
{
    ss_entries[slot * 5] = 1000;
    strcpy((char *)(ss_entries + slot * 5 + 1), "unused.wav");
}
""",
    note="strcpy gets ss_entries+slot*5+1 (pointer arithmetic) "
         "instead of &ss_entries[slot*5+1] (address-of-index)",
)


# ── trial 15: dst as separately-cast ss_entries pointer ─────────
exp.add(
    "char-ptr-via-add",
    """
void free_up_sslot(int slot)
{
    int e = slot * 5;
    ss_entries[e] = 1000;
    strcpy((char *)(ss_entries + e + 1), "unused.wav");
}
""",
    note="alias index, then ptr-arithmetic for strcpy dst",
)


# ── trial 16: assignment as &arr[i*5+1] vs &arr[i*5][1] ─────────
exp.add(
    "addr-of-elt-plus-1",
    """
void free_up_sslot(int slot)
{
    ss_entries[slot * 5] = 1000;
    strcpy((char *)&(ss_entries[slot * 5] + 1)[0], "unused.wav");
}
""",
    note="alternative syntax to express &ss_entries[slot*5 + 1]",
)


# ── trial 17: store-then-strcpy via separate stmts ──────────────
# Try forcing the compiler to recognise that &ss_entries[slot*5]
# from the first stmt can be reused for the strcpy dst by writing
# it via an explicit pointer alias and then doing strcpy(p+4).
exp.add(
    "char-ptr-after-store",
    """
void free_up_sslot(int slot)
{
    int *e = &ss_entries[slot * 5];
    *e = 1000;
    strcpy(((char *)e) + 4, "unused.wav");
}
""",
    note="char-ptr derived from int-ptr, +4 byte offset for strcpy",
)
