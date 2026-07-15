"""get_free_memory — lib32 RAM probing loop.

PS @ 0x28659, 104 bytes.  Current source is at 58 b diff against PS.

The remaining diff is the FIRST iteration setup:

  PS: mov edx, 0x400; mov [allocable_memory], edx; mov eax, edx; call malloc
  RC: mov eax, 0x400; mov [allocable_memory], eax; call malloc

PS uses EDX as a staging register for n; RC uses EAX directly via the
short `mov [m], eax` form (a3 ?? ?? ?? ?? = 5 bytes vs 89 15 ?? ?? ?? ??
= 6 bytes).  PS's path is 3 bytes longer due to the explicit edx→eax
move, but that's the pattern we need.

Run::

    uv run c2 cgex run get_free_memory
"""

from c2.commands.cgex import Experiment


_PRELUDE = """
#define NULL ((void *)0)
extern int allocable_memory;
extern void *malloc(unsigned);
extern void  free(void *);
"""

_DEFS = """
int allocable_memory;
void *malloc(unsigned n) { (void)n; return (void *)0; }
void free(void *p) { (void)p; }
"""

exp = Experiment(
    name="get_free_memory",
    ps_function="get_free_memory",
    chk=True,
    prelude=_PRELUDE,
    extra_defs=_DEFS,
)


exp.add("baseline", """
void get_free_memory(void)
{
    void *p;
    int n;
    n = 0x400;
    allocable_memory = n;
    while ((p = malloc(n)) != NULL) {
        free(p);
        allocable_memory += 0x400;
        n = allocable_memory;
    }
    allocable_memory -= 0x400;
    allocable_memory = allocable_memory / 0x400;
}
""", note="baseline (58 b)")


exp.add("A_use_n_at_end", """
void get_free_memory(void)
{
    void *p;
    int n;
    n = 0x400;
    allocable_memory = n;
    while ((p = malloc(n)) != NULL) {
        free(p);
        n += 0x400;
        allocable_memory = n;
    }
    n -= 0x400;
    allocable_memory = n / 0x400;
}
""", note="A: use n at end")


exp.add("B_double_assign", """
void get_free_memory(void)
{
    void *p;
    int n;
    n = 0x400;
    allocable_memory = n;
    n = allocable_memory;
    while ((p = malloc(n)) != NULL) {
        free(p);
        allocable_memory += 0x400;
        n = allocable_memory;
    }
    allocable_memory -= 0x400;
    allocable_memory = allocable_memory / 0x400;
}
""", note="B: re-read n before loop")


exp.add("C_do_while", """
void get_free_memory(void)
{
    void *p;
    int n;
    n = 0x400;
    allocable_memory = n;
    p = malloc(n);
    while (p != NULL) {
        free(p);
        allocable_memory += 0x400;
        n = allocable_memory;
        p = malloc(n);
    }
    allocable_memory -= 0x400;
    allocable_memory = allocable_memory / 0x400;
}
""", note="C: unrolled malloc")


exp.add("D_init_via_global", """
void get_free_memory(void)
{
    void *p;
    int n;
    allocable_memory = 0x400;
    n = allocable_memory;
    while ((p = malloc(n)) != NULL) {
        free(p);
        allocable_memory += 0x400;
        n = allocable_memory;
    }
    allocable_memory -= 0x400;
    allocable_memory = allocable_memory / 0x400;
}
""", note="D: init via global write then re-read")


exp.add("E_for_loop", """
void get_free_memory(void)
{
    void *p;
    int n;
    for (n = 0x400; ; n = allocable_memory) {
        allocable_memory = n;
        p = malloc(n);
        if (p == NULL) break;
        free(p);
        allocable_memory += 0x400;
    }
    allocable_memory -= 0x400;
    allocable_memory = allocable_memory / 0x400;
}
""", note="E: for loop init")


exp.add("F_set_first_outside", """
void get_free_memory(void)
{
    void *p;
    int n;
    n = 0x400;
    allocable_memory = n;
    goto first;
    while (1) {
        free(p);
        allocable_memory += 0x400;
        n = allocable_memory;
first:
        p = malloc(n);
        if (p == NULL) break;
    }
    allocable_memory -= 0x400;
    allocable_memory = allocable_memory / 0x400;
}
""", note="F: goto first label")
