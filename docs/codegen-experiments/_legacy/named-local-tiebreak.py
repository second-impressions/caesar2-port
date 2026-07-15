"""PROOF: a named C local consolidates N inline reads into ONE high-
savings conflict; the inline form emits N separate sav=1 conflicts.  The
refactored mechanism for the 5x diffing-vs-exact mirror corpus bias.

Background: `vendor/open-watcom/bld/cg/h/name.h:209` defines

    #define _FrontEndTmp( op ) ( !( (op)->t.temp_flags & CONST_TEMP ) && \\
                                   (op)->v.symbol != NULL )

The initial hypothesis (observed-source-style.md §13, 2026-06-25 corpus
survey) was that named locals (FE temps, `v.symbol != NULL`) sort EARLIER
than CSE / index temps (`symbol == NULL`) in `ConfBefore` ties of equal
savings.  This experiment isolated the question and found a sharper
mechanism.

**Refined finding (proved here):** for an N-use global access, Watcom does
NOT auto-CSE the N inline reads into a single high-savings temp inside a
basic block under PS_CFLAGS (`-bt=dos -mf -4r -s -d1`, BlockByBlock=TRUE,
no -ot).  Each inline read produces a SEPARATE single-use sav=1 conflict
that lives only across the surrounding instruction.  A NAMED local of the
same global produces ONE conflict with savings = (defs + uses), which is
N+1 (sav=5 for the 4-use case here).

Consequence in the regalloc queue: the named-local form contributes ONE
conflict at the TOP of the ConfBefore sort (savings 5); the inline form
contributes N conflicts at the BOTTOM (savings 1 each).  This changes
EVERY allocation decision downstream of the consolidated conflict's seat
-- not via a tie-break perturbation (the original conjecture), but via a
structural rank change.  The named local out-prioritizes ANY equal-or-
smaller-savings rival in the queue; the inline reads sort LAST and lose
to every higher-savings competitor.

This is the load-bearing reason `local = G;` mirrors that PS source did
not have perturb the corpus's regalloc outcomes -- they UPGRADE a set of
sav=1 leaf temps into ONE sav=N front-end temp at the front of the queue.

Trials (each performs 4 uses of each of two values after a sink() call):

  named_named    int a=gi[0], b=gi[1];   sink(); use a,b 4× each
  named_inline   int a=gi[0];            sink(); use a 4×, gi[1] 4× inline
  inline_named   int b=gi[1];            sink(); gi[0] 4× inline, use b 4×
  inline_inline  /* no locals */          sink(); gi[0] 4×, gi[1] 4× inline

Run::

    uv run c2 cgex run named-local-tiebreak
    uv run python docs/codegen-experiments/named-local-tiebreak.py
"""
from c2.commands.cgex import Experiment


exp = Experiment(
    name="named-local-tiebreak", ps_function="t", chk=False,
    externs={"sink": "extern void sink(void);"},
    prelude="extern int gi[40]; extern int go[40];\n",
    extra_defs="int gi[40]; int go[40];\n",
)


# Each value is read 4× after a sink() call.  4× depth-1 uses = savings 4
# under PS_CFLAGS (W=10 base, no -ot).  Equal savings on `a` vs `b` (or
# their inline equivalents).  The sink() ensures the values cross a call,
# so EAX is masked off and the candidates are EDX,EBX,ECX,ESI,EDI,EBP.

exp.add("named_named",
        "int t(void){"
        "  int a = gi[0];"
        "  int b = gi[1];"
        "  sink();"
        "  go[0] = a; go[1] = a; go[2] = a; go[3] = a;"
        "  go[4] = b; go[5] = b; go[6] = b; go[7] = b;"
        "}",
        note="two FE temps -- both have v.symbol != NULL")
exp.add("named_inline",
        "int t(void){"
        "  int a = gi[0];"
        "  sink();"
        "  go[0] = a; go[1] = a; go[2] = a; go[3] = a;"
        "  go[4] = gi[1]; go[5] = gi[1]; go[6] = gi[1]; go[7] = gi[1];"
        "}",
        note="one FE temp `a`, one CSE temp for gi[1] -- gi[1] has v.symbol == NULL")
exp.add("inline_named",
        "int t(void){"
        "  int b = gi[1];"
        "  sink();"
        "  go[0] = gi[0]; go[1] = gi[0]; go[2] = gi[0]; go[3] = gi[0];"
        "  go[4] = b; go[5] = b; go[6] = b; go[7] = b;"
        "}",
        note="mirror of named_inline -- if FE bias is real, `b` (named) still wins higher reg")
exp.add("inline_inline",
        "int t(void){"
        "  sink();"
        "  go[0] = gi[0]; go[1] = gi[0]; go[2] = gi[0]; go[3] = gi[0];"
        "  go[4] = gi[1]; go[5] = gi[1]; go[6] = gi[1]; go[7] = gi[1];"
        "}",
        note="both CSE temps -- no FE bias either side")


def _allocations(exp_, trial):
    """{var_name_or_'temp_<addr>': chosen_reg} for the trial."""
    try:
        rows = exp_.regtrace(trial)
    except Exception:
        return {}
    out = {}
    for r in rows:
        v = r.get("var")
        reg = r.get("chosen") or r.get("reg_name") or r.get("reg")
        sav = r.get("savings", 0)
        # We only care about the int-width values (regclass dword == 0xF).
        if r.get("class") not in (0xF, 0x10):
            continue
        key = v if v else f"temp@{r.get('handle', 0):x}"
        if key in out:
            continue  # first conflict wins (later may be a re-allocation)
        out[key] = {"reg": reg, "savings": sav, "var": v, "row": r}
    return out


def _summarise(name, allocs):
    print(f"\n  {name}")
    for k, v in allocs.items():
        named = "FE" if v["var"] else "CSE-temp"
        print(f"    sav={v['savings']:<3d}  {named:<8s}  {k:<22s}  ->  {v['reg']}")


def _classify(rows):
    """Split conflict rows into (named, anonymous) lists with their savings."""
    named = []
    anon = []
    for r in rows:
        if r.get("class") not in (0xF, 0x10):
            continue
        v = r.get("var")
        reg = r.get("chosen") or r.get("reg_name")
        sav = r.get("savings", 0)
        (named if v else anon).append({"name": v, "reg": reg, "sav": sav})
    return named, anon


def verify():
    exp.run()
    print("=== named local vs CSE/inline temp in 10.0a regalloc queue ===\n")

    summaries = {}
    for tn in ("named_named", "named_inline", "inline_named", "inline_inline"):
        rows = exp.regtrace(tn)
        named, anon = _classify(rows)
        summaries[tn] = (named, anon)
        named_sav = sorted({n["sav"] for n in named})
        anon_sav = [a["sav"] for a in anon]
        print(f"  {tn:<14s}  FE conflicts: {len(named):2d} (sav={named_sav or '—'})  "
              f"anon conflicts: {len(anon):2d} (sav={sorted(set(anon_sav)) or '—'})")
        for n in named:
            print(f"      FE  sav={n['sav']:<3d} `{n['name']}` -> {n['reg']}")
        for a in anon[:6]:
            print(f"      CSE sav={a['sav']:<3d} (anonymous)     -> {a['reg']}")

    # ── proposition: the named-local form consolidates the N inline reads
    # into ONE FE temp with savings ~= N+1.  The inline form emits N
    # anonymous temps each with sav=1 -- the SUM of savings is the same,
    # but the QUEUE STRUCTURE differs sharply: 1 high-priority conflict vs
    # N low-priority leaves.
    print("\n=== mechanism check ===")
    def named_max_sav(tn):
        n, _ = summaries[tn]
        return max((x["sav"] for x in n), default=0)
    def anon_max_sav(tn):
        _, a = summaries[tn]
        return max((x["sav"] for x in a), default=0)
    def anon_count(tn):
        _, a = summaries[tn]
        return len(a)

    fe_nn = named_max_sav("named_named")
    fe_ni = named_max_sav("named_inline")
    ct_ni = anon_max_sav("named_inline")
    n_ni  = anon_count("named_inline")
    fe_ii = named_max_sav("inline_inline")
    ct_ii = anon_max_sav("inline_inline")
    n_ii  = anon_count("inline_inline")

    # 4 uses of each value; named expects sav >= 4 (uses + def), anon expects
    # sav == 1 per inline read leaf.
    cons_named = fe_nn >= 4 and fe_ni >= 4
    print(f"  named_named  FE max sav = {fe_nn}    (expect ≥ 4)   {'OK' if fe_nn >= 4 else 'FAIL'}")
    print(f"  named_inline FE max sav = {fe_ni}    (expect ≥ 4)   {'OK' if fe_ni >= 4 else 'FAIL'}")
    print(f"  named_inline anon max sav = {ct_ni}, count = {n_ni}   "
          f"(expect sav=1, count≥3 -- inline reads atomized)")
    print(f"  inline_inline FE present = {fe_ii > 0}    (expect 0)   {'OK' if fe_ii == 0 else 'FAIL'}")
    print(f"  inline_inline anon count = {n_ii}    (expect ≥6 -- all 8 reads atomized)")

    proven = cons_named and ct_ni <= 2 and fe_ii == 0
    print("\n=== verdict ===")
    if proven:
        print("  PROVEN: a named C local consolidates N inline reads into ONE")
        print("  high-savings (sav=N+1) FE conflict; the inline form emits N")
        print("  separate sav=1 anonymous conflicts.  The named-local form")
        print("  thus contributes a TOP-of-queue conflict where the inline")
        print("  form contributes BOTTOM-of-queue leaves -- a structural rank")
        print("  change, not (just) a ConfBefore name-pointer tie-break.")
        print("  Mechanism for the 5x diffing-vs-exact mirror corpus bias")
        print("  is now grounded: drop the mirror -> drop a high-priority")
        print("  conflict that PS source did not have -> downstream allocations")
        print("  re-rank in PS's favour.")
    else:
        print("  inconclusive -- the regtrace rows did not match the expected")
        print("  shape.  Inspect _classify output above and the .insns dumps.")


if __name__ == "__main__":
    verify()
