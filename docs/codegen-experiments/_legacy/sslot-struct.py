"""get_new_sslot — struct-view vs raw int[] indexing.

PS emits this (94 b @ 0x12953)::

    push ebx,ecx,edx,esi,edi
    mov edi, eax              ; fname
    xor ecx, ecx              ; max_c = 0
    xor esi, esi              ; best  = 0
    xor edx, edx              ; i     = 0
  L570:
    mov eax, edx              ; eax = i
    shl eax, 2; add eax, edx  ; eax = i*5
    shl eax, 2                ; eax = i*5*4   (byte offset)
    mov ebx, [eax + 0xd2a8]   ; ebx = ss_entries[i*5]
    inc ebx
    mov [eax + 0xd2a8], ebx
    cmp ecx, ebx
    jg L573
    mov esi, edx              ; best = i
    mov ecx, ebx              ; max_c = ebx
  L573:
    inc edx
    cmp edx, 10
    jl L570
    mov [sslot], esi
    mov eax, esi              ; eax = best
    shl eax, 2; add eax, esi  ; eax = best*5
    shl eax, 2                ; eax = best*5*4
    xor edx, edx
    mov [eax + 0xd2a8], edx   ; ss_entries[best*5] = 0
    add eax, 0xd2a8           ; eax = abs byte addr
    add eax, 4                ; → name field
    mov edx, edi              ; edx = fname
    call strcpy
    jmp 0x13181               ; shared 5-pop+ret epilogue

Key trait: PS keeps ``eax = i*5*4`` (byte offset) and uses
``[eax + 0xd2a8]`` direct displacement, NOT ``[eax*4 + 0xd2a8]``
SIB *4.  Suggests the source treats ss_entries as an array of
20-byte structs.
"""

from c2.commands.cgex import Experiment

PS_FN = "get_new_sslot"

EXTRA_DEFS = """
int ss_entries[50];
int sslot;
char *strcpy(char *dst, const char *src) { (void)dst; (void)src; return dst; }
"""

PRELUDE = """
extern int ss_entries[50];
extern int sslot;
extern char *strcpy(char *, const char *);
"""

exp = Experiment(
    name="sslot-struct",
    ps_function=PS_FN,
    chk=False,
    externs={},
    extra_defs=EXTRA_DEFS,
    prelude=PRELUDE,
    cflags="-bt=dos -mf -4r -s",
)


# ── trial 0: current source, int[] indexing ─────────────────────
exp.add(
    "int-array-shared-hits",
    """
void get_new_sslot(char *fname)
{
    int max_c = 0;
    int best  = 0;
    int i;
    int hits;
    for (i = 0; i < 10; i++) {
        hits = ++ss_entries[i * 5];
        if (max_c < hits) {
            best  = i;
            max_c = hits;
        }
    }
    sslot = best;
    ss_entries[best * 5] = 0;
    strcpy((char *)(ss_entries + best * 5 + 1), fname);
}
""",
    note="current source: int[] indexing with hits temp",
)


# ── trial 1: struct-view via local cast ─────────────────────────
exp.add(
    "struct-local-cast",
    """
void get_new_sslot(char *fname)
{
    struct sslot_entry { int count; char name[16]; };
    struct sslot_entry *e = (struct sslot_entry *)ss_entries;
    int max_c = 0;
    int best  = 0;
    int i;
    for (i = 0; i < 10; i++) {
        e[i].count++;
        if (max_c < e[i].count) {
            best  = i;
            max_c = e[i].count;
        }
    }
    sslot = best;
    e[best].count = 0;
    strcpy(e[best].name, fname);
}
""",
    note="struct view via local pointer cast",
)


# ── trial 2: struct-view + caching count value ──────────────────
exp.add(
    "struct-cached-count",
    """
void get_new_sslot(char *fname)
{
    struct sslot_entry { int count; char name[16]; };
    struct sslot_entry *e = (struct sslot_entry *)ss_entries;
    int max_c = 0;
    int best  = 0;
    int i;
    int c;
    for (i = 0; i < 10; i++) {
        c = ++e[i].count;
        if (max_c < c) {
            best  = i;
            max_c = c;
        }
    }
    sslot = best;
    e[best].count = 0;
    strcpy(e[best].name, fname);
}
""",
    note="struct + cached count",
)


# ── trial 3: struct-view, separate read+write of count ──────────
exp.add(
    "struct-read-then-write",
    """
void get_new_sslot(char *fname)
{
    struct sslot_entry { int count; char name[16]; };
    struct sslot_entry *e = (struct sslot_entry *)ss_entries;
    int max_c = 0;
    int best  = 0;
    int i;
    int c;
    for (i = 0; i < 10; i++) {
        c = e[i].count + 1;
        e[i].count = c;
        if (max_c < c) {
            best  = i;
            max_c = c;
        }
    }
    sslot = best;
    e[best].count = 0;
    strcpy(e[best].name, fname);
}
""",
    note="struct + explicit read-add-write",
)


# ── trial 4: byte-offset arithmetic (no struct) ─────────────────
exp.add(
    "byte-offset-explicit",
    """
void get_new_sslot(char *fname)
{
    int max_c = 0;
    int best  = 0;
    int i;
    int *p;
    int hits;
    char *base = (char *)ss_entries;
    for (i = 0; i < 10; i++) {
        p = (int *)(base + i * 20);
        hits = ++*p;
        if (max_c < hits) {
            best  = i;
            max_c = hits;
        }
    }
    sslot = best;
    p = (int *)(base + best * 20);
    *p = 0;
    strcpy((char *)(p + 1), fname);
}
""",
    note="explicit byte-offset, no struct",
)
