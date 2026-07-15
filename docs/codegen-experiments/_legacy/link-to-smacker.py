"""link_to_smacker -- SOLVED byte-exact (the checked-global-reused-as-arg reload).

    int link_to_smacker(void) {
        if (smacker_open) return 1;
        SetSmackAILDigDriver(dig, smacker_open);   /* __cdecl(int unused, int dig) */
        smacker_open = 1;
        return 1;
    }

ROOT (proven; watcom10.0a docs/parm-reload-rover.md, binary-confirmed):
`smacker_open` is loaded for the `if` test and RELOADED for the 2nd call arg --
`Enregister` (wcc386 va 0x62939) returns a PARM_DEF's N_MEMORY operand
unconditionally.  That 2nd RISCify is an extra push-scratch rover advance
(`FindRegister`), so the build runs FOUR rover advances (test, smacker_open
reload, dig, const-1) where PS runs THREE -- bumping dig EBX->ECX and the const 1
into a fresh callee-save ESI (+push esi/pop esi).  `Score` coalesces the reload
back to `push edx`, but only AFTER the rover already cascaded.

LEVER (SOLVED, byte-exact -- `temp_after_guard`): copy the global into a temp
AFTER the guard and pass the temp.  The test stays a DIRECT read (rover -> EDX,
PS's register); `o = smacker_open` is a plain MOV (not RISCified, no rover
advance); the arg `push o` references a TEMP (not N_MEMORY) so it is not
RISCified either -> advances become test/dig/const = EDX/EBX/ECX = PS; Score then
coalesces the temp's load into the guard's live EDX, emitting `push edx`.

WHY PLACEMENT MATTERS: caching BEFORE the guard (`int o = smacker_open; if (o)`)
puts the *test* on the named temp, which GiveBestReg allocates from
DoubleRegs[0]=EAX (not the rover's EDX), shifting everything (`cache_before`:
diff 35).  Copy AFTER the guard so only the arg becomes a temp.

    uv run c2 cgex run link-to-smacker            # table (temp_after_guard -> 1 = harness stub byte)
    uv run c2 cgex run link-to-smacker -t temp_after_guard -v
"""
from c2.commands.cgex import Experiment

exp = Experiment(
    name="link-to-smacker",
    ps_function="link_to_smacker",
    chk=False,
    prelude=("extern int smacker_open; extern int dig;\n"
             "extern void __cdecl SetSmackAILDigDriver(int unused, int dig);"),
    extra_defs=("int smacker_open; int dig;\n"
                "void __cdecl SetSmackAILDigDriver(int unused, int dig)"
                " { (void)unused; (void)dig; }"),
)

exp.add("baseline", """
int link_to_smacker(void) {
    if (smacker_open) return 1;
    SetSmackAILDigDriver(dig, smacker_open);
    smacker_open = 1;
    return 1;
}
""", note="current decomp -> 44 (reload cascade + esi); fr = 4 advances")

exp.add("temp_after_guard", """
int link_to_smacker(void) {
    int o;
    if (smacker_open) return 1;
    o = smacker_open;
    SetSmackAILDigDriver(dig, o);
    smacker_open = 1;
    return 1;
}
""", note="SOLVED: arg via a temp AFTER the guard -> byte-exact (1 = harness stub)")

exp.add("cache_before", """
int link_to_smacker(void) {
    int o = smacker_open;
    if (o) return 1;
    SetSmackAILDigDriver(dig, o);
    smacker_open = 1;
    return 1;
}
""", note="WRONG placement: test on the named temp -> EAX -> shifts all (35)")
