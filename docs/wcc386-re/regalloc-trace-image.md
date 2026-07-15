# Native register-allocation trace (the `-trace` compiler image)

> Tooling paths below (`scripts/build-trace-image.sh`, `tools/*.py`,
> `qemu-harness/`) are in the sibling `~/git/ReverseEngineering/watcom10.0a`
> repo — see `README.md` “Where the tooling lives”.

A podman-native counterpart to the QEMU `c2 regtrace`: an **instrumented
wcc386** that prints the *real* allocator's decisions on stdout while producing
**byte-identical `.obj`** output. It captures the **assigned register** — the
piece the QEMU hook could not (`ENABLE_CHOSEN_HOOK=False`, the "TNT driver
segment wall") — and confirms our cost model and the H2 equal-savings order.

Provenance: instrumentation + reference model RE'd and proven in the
`watcom10.0a` repo (`tools/{patch_trace,regalloc_sort,regalloc_costs,reglists,
trace_parse}.py`, `docs/verification.md` — every probe REPRODUCED).

## The image

`localhost/watcom-10.0a-dosemu2-trace` — derived from
`localhost/watcom-10.0a-dosemu2` with `wcc386.exe` swapped for the patched
build (read-only printf trampolines; the stock binary is kept as
`wcc386.orig.exe`). Rebuild from the watcom10.0a repo:

```
bash scripts/build-trace-image.sh     # verifies .obj byte-identity, then builds
```

The hooks reuse the compiler's own `printf`; `.obj` is byte-identical (verified
in the build gate), so this image is a **safe drop-in** for any compile — the
only difference is extra `~WV1 ...` lines on stdout.

## Trace schema (`~WV1 <tag> ...`, extensible)

| tag | fields | meaning |
|---|---|---|
| `lwt` / `cost` | time / addr value | savings model: `base=20*time/256`; costs load,store,use,def,push,pop |
| `fb` | — | function-begin marker (every routine, including trivial) |
| `fn` | — | regalloc phase begin (non-trivial only) |
| `sl` | node savings | PRE-sort ConfList (real ShellSort input) |
| `al` | conf name savings regclass first last nameclass defline | post-sort allocation order |
| `nm` | conf var_name | source variable name for the preceding `al` (al → nm → gi chain) |
| `rg` | conf regmask | **assigned hw_reg_set** (absent ⇒ spilled) |
| `wr` | conf withregs | interference set at FixInstructions (first sighting wins) |
| `gi` | conf op res res_reg op0 op0_reg op1 op1_reg | per-instruction sample over conf's ins_range |
| `fr` | ins type_class except opcode op0 line | RISCify rover (FindRegister) events |
| `st` | name size pre_size base | per-temp slot allocation order (SetTempLocation) |
| `rl` | count | RetList length (OptPush ComTail call site) |
| `cm` | max_save ins_line | per-ret tail-merge decision |
| `tn` | ptr class op left right tipe line | tree interior node (TGNode) |
| `tb` | ptr sub tipe start length line | tree bit-lvalue leaf (TGBitLValue) |
| `tl` | ptr class name_or_val tipe line | tree name/const leaf (TGLeaf) |
| `nb` | ptr class subclass name_id line | name birth (AllocName) |
| `ni` | ptr nops line | instruction birth (NewIns) |
| `fc` | — | per-routine codegen-complete marker (FIRST `fc` after `fb` = routine terminal) |
| `il` | bytes | per-emitted-instruction byte length (AdvanceCode entry = OW EjectInst). Sum gives per-routine offsets of regular user instructions; calls/branches/ret use a separate emit path so are ABSENT — consumers align with the binary disasm to recover real offsets. |
| `ge` | ins opcode gen_class line result op0 op1 | per-cg_ins codegen context (GenObjCode entry).  Fires for EVERY user cg_ins INCLUDING calls/jumps/ret (`opcode=OP_CALL=54` for direct calls, `OP_CALL_INDIRECT=41` for fp calls, `OP_MOV=38` for moves; arith opcodes 1-13 match tn-level positionally; compares 48-53).  `gen_class` is the optab row chosen.  Helper calls via RTCall->DoCall bypass GenObjCode, so the ABSENCE of a `ge` with opcode=OP_CALL at an asm offset is PROOF that any binir-recovered call_with_args there is a compiler helper (stack-check, prolog hook, segment fixup).  Combined with `il`, the parser builds `routine["cgen_events"]` -- per-cg_ins records with `offset`, `il_bytes`, plus the full codegen context. |

Under PS.EXE's flags (`-bt=dos -mf -4r -s -d1`) the trace confirms
**W=10, use=def=push=pop=1, load=store=2** — i.e. the model in
`regalloc-cost.py` is correct for this build.

## Wired into decomp-verify

`decomp-verify`'s default build image is now this `-trace` image (byte-identical
.obj; the `~WV1` lines are filtered out of the build output). For every diffing
function it prints a **regalloc ground-truth** line in the header, e.g.:

```
regalloc (actual 10.0a): 198 values, 5 spilled  [W=10 load=2 store=2 use=1]
  s27->EAX  s19->EAX  s19->EBX  s11->EAX  …
```

The data is produced by `c2.commands.regalloc_hints` consuming `c2.regalloc` --
parsed **once per .c file** and disk-cached (`file_trace`, content-hashed, only
changed files recompile, exactly like wmake), so no work is duplicated across
hints. Attribution is exact: the per-function `fb` marker (emitted at the
`RegAlloc` entry for **every** function incl. trivial ones) makes the Nth
routine == the Nth source function, so a brace-aware source scan zips 1:1.

## Using it from code — `c2.regalloc`

```python
from c2 import regalloc

# compile + link a snippet under the trace image, attribute by symbol order:
build, td = regalloc.compile_with_trace(src, func="do_promotion")
r = td["target"]
for a in r["alloc"]:
    print(a["savings"], a["regclass_name"], a["reg_name"])   # chosen register
assert regalloc.reproduce_order(r)                            # H2 self-check

# compile-only a whole TU (byte-faithful, no link):
td = regalloc.trace_compile({"T.C": tu_src, "FOO.H": hdr}, cflags=regalloc.PS_CFLAGS)
```

`c2.regalloc` also re-exports the **byte-exact reference model** (validated
against this oracle): `sort` (ShellSort + strict `ConfBefore` ⇒ H2), `costs`
(savings cost model, `from_flags(cpu, ot, os_)`), `reglists` (candidate-register
order = GiveBestReg's final tie-break: dword = EAX,EBX,ECX,EDX,ESI,EDI).

## Using it from the CLI — `c2 regtrace-native` (= `c2 regtrace --native`)

```
uv run c2 regtrace-native move_army           # target-only snippet (clean attribution)
uv run c2 regtrace move_army --native          # same engine, folded into regtrace
uv run c2 regtrace-native move_army --tu --all # whole TU, every routine (raw)
uv run c2 regtrace-native move_army --json     # machine-readable
```

Shows the cost model and, per conflict, savings / register class / kind /
**assigned register** / instruction range, plus an **H2 offline-reproduce**
check (our `c2.regalloc.sort` over the `sl` list must equal the `al` order).

By default it compiles a **target-only snippet** (file preamble + just that
function); callees get prototypes from the headers so codegen matches the full
TU (Rule 37). For a function that calls an un-prototyped file-local static, use
`--tu` (byte-faithful, but routines aren't name-attributed) and cross-check
byte-equality with `c2 decomp-verify`.

## How this resolves open items

* **Chosen register** (`regalloc-predictor-plan.md`: "blocked — TNT driver
  segment wall") — now captured directly (`rg`).
* **H2 vs a secondary `ConfBefore` key** (`regalloc-model.md` §3) — settled:
  `ConfBefore` is strict savings, equal-savings order is the *unstable*
  ShellSort over the ConfList; `c2.regalloc.sort` reproduces every observed
  order (incl. 14-element equal-savings groups).
* **Cost model** — confirmed for PS.EXE's exact flags (and parameterised across
  `-3/-4/-5` × `-ot/-os` in `c2.regalloc.costs`).

## Relation to QEMU `c2 regtrace` — complementary, not redundant

They capture **different data** and overlap only on `savings`:

| | QEMU `c2 regtrace` (default) | `--native` (this image) |
|---|---|---|
| engine | QEMU + hardware breakpoint | one podman compile |
| chosen register | **modeled** (`_model_chosen`, "validated 3/3") | **actual**, captured (`rg`) |
| candidates / `with.regs` / CG `ins_walk` | **captured** | not captured |
| variable name / source line (`var`/`def_line`) | **captured** (from the IL) | not captured (temps only) |
| savings | yes | yes |
| `--explain` / `--solve` / `--vs` / `--il` | yes (need the inputs above) | no |
| H2 offline-reproduce check | no | yes |
| cost-model dump | no | yes |

**Why native is folded in as `--native` but not the default:** `--explain` /
`--solve` / `--il` need the QEMU input capture (candidates, `with.regs`, the CG
instruction list) and the variable names / source lines, which the native trace
does not have. So native is a *complement*, not a superset: use it for "what
did it actually pick (ground truth) and does our offline model reproduce it",
and the QEMU default for "why" at the IR-input level and for the closed-loop
levers.

**The highest-value future merge:** feed native's *actual* chosen register into
regtrace's pipeline to replace the *modeled* `chosen` (the analyses all key off
it; today it is a 3-case-validated prediction). Matching is by allocation order
+ savings (both engines process conflicts in the same ShellSort order). The
larger end-state is to add candidate / `with.regs` capture (the hook points are
known) and FE name resolution to the trace image, making the native engine a
strict superset so QEMU can be retired.
