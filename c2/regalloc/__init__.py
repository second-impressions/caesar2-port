"""Register-allocation oracle + reference model for Watcom 10.0a.

Two things live here:

1. **A trace oracle** -- compile a C TU/snippet with the instrumented compiler
   (the ``localhost/watcom-10.0a-wibo-trace`` image) and read the *real*
   allocator's decisions per routine: pre-sort conflict list, savings, register
   class, instruction range, and the **assigned register** (which caesar2's
   QEMU ``regtrace`` could not capture -- the "TNT driver segment wall").
   ``.obj`` output is byte-identical to the stock compiler, so this never
   perturbs a verify.

2. **A byte-exact reference model** (RE'd + validated against that oracle):
   ``sort`` (ShellSort + strict ``ConfBefore`` => the H2 equal-savings order),
   ``costs`` (savings cost model, proven across flags), ``reglists`` (the
   candidate-register order = GiveBestReg's final tie-break).

Provenance: derived in the watcom10.0a RE repo (tools/{regalloc_sort,
regalloc_costs,reglists,patch_trace,trace_parse}.py) and proven there
(docs/verification.md: every probe REPRODUCED).
"""
from __future__ import annotations

import functools
import hashlib
import json
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from . import sort, costs, reglists, trace
from .trace import parse as parse_trace, reg_name, REG_NAME

TRACE_IMAGE = "localhost/watcom-10.0a-wibo-trace"
PS_CFLAGS = "-bt=dos -mf -4r -s -d1"   # = decomp_verify.PS_CFLAGS (the real PS.EXE flags)

_KEYWORDS = {"if", "for", "while", "switch", "return", "sizeof", "do", "else"}


def _func_defs_ast(text: str) -> list[str] | None:
    """Top-level function-definition names in source order via the pycparser
    front-end (``c2.commands.c_source``).  Returns None if the parse fails so
    the caller can fall back to the regex scanner.  The AST is the correct
    source of truth -- the regex scanner silently drops functions with
    multi-line signatures (it found 92/158 in lib32.c, missing font_format_split
    and 65 others), which mis-aligns the zip with the `fb` routine order."""
    try:
        from c2.commands import c_source
        ast = c_source.parse_c(text)
        return [f.decl.name for f in c_source.classify(ast).func_defs
                if f.decl and f.decl.name]
    except Exception:
        return None


def _func_defs_regex(text: str) -> list[str]:
    """Fallback: brace-depth-aware regex scan for ``name(...) {`` headers at
    depth 0.  Used only when the AST parse fails (macro-heavy / non-C99 TUs)."""
    s = re.sub(r"//[^\n]*", "", text)
    s = re.sub(r"/\*.*?\*/", " ", s, flags=re.S)
    s = re.sub(r'"(\\.|[^"\\])*"', '""', s)
    s = re.sub(r"'(\\.|[^'\\])*'", "''", s)
    out, i, depth, n = [], 0, 0, len(s)
    while i < n:
        c = s[i]
        if c == "{":
            depth += 1; i += 1; continue
        if c == "}":
            depth -= 1; i += 1; continue
        if depth == 0:
            m = re.match(r"([A-Za-z_]\w*)\s*\(", s[i:])
            if m and m.group(1) not in _KEYWORDS:
                j = i + m.end() - 1; d = 0
                while j < n:
                    if s[j] == "(":
                        d += 1
                    elif s[j] == ")":
                        d -= 1
                        if d == 0:
                            break
                    j += 1
                k = j + 1
                while k < n and s[k] in " \t\n":
                    k += 1
                if k < n and s[k] == "{":
                    out.append(m.group(1)); i = k; continue
        i += 1
    return out


def _func_defs(text: str) -> list[str]:
    """Top-level function-definition names in source order == the order the back
    end processes functions == the `fb` record order, so zip(_func_defs,
    fb_routines) is a 1:1 attribution.  AST-first (accurate), regex fallback."""
    return _func_defs_ast(text) or _func_defs_regex(text)


def attribute(routines: list[dict], files: dict[str, str]) -> dict[str, dict]:
    """Map ``func_name -> routine`` by source-definition order across ``files``
    (build/insertion order), zipping with the per-function `fb` routines 1:1."""
    names: list[tuple[str, str]] = []
    for _fn, text in files.items():
        names.extend((n, _fn) for n in _func_defs(text))
    out: dict[str, dict] = {}
    for i, (name, _fn) in enumerate(names):
        if i < len(routines):
            routines[i]["src_file"] = _fn   # for defline -> source-text lookups
            out[name] = routines[i]
    return out


class RegallocTrace:
    """Parsed register-allocation trace for a build, attributed per function.

    Constructed ONCE from a build's ``~WV1`` stdout (the patched compiler's
    output) + the source files in build order, then shared by all hint
    detectors -- so the parse/attribution is not duplicated. Per-function lookup
    is exact because the `fb` marker fires for every function (incl trivial) in
    source order, zipping 1:1 with the source-definition order.

        .cost_model / .loop_base    savings model for the build's flags
        .routines                   one per function (source order)
        .by_func                    {func_name: routine}
        .routine_for(name)          routine or None (handles trailing `_`)
        .functions                  attributed function names
    """

    def __init__(self, td: dict):
        self.cost_model = td.get("cost_model", {})
        self.loop_time = td.get("loop_time")
        self.loop_base = td.get("loop_base")
        self.routines = td.get("routines", [])
        self.by_func = td.get("by_func", {})

    @classmethod
    def from_build(cls, build_stdout: str, ordered_files: dict[str, str]):
        """`ordered_files`: {filename: source} in COMPILE order (the order the
        build's wcc386 invocations ran), .c files only."""
        td = parse_trace(build_stdout)
        td["by_func"] = attribute(td["routines"], ordered_files)
        return cls(td)

    @property
    def functions(self):
        return list(self.by_func)

    def routine_for(self, name: str):
        return self.by_func.get(name) or self.by_func.get(name.rstrip("_"))

    def reproduces(self, name: str):
        r = self.routine_for(name)
        return reproduce_order(r) if r else None


def trace_compile(files: dict[str, str], *, cflags: str = PS_CFLAGS,
                  main: Optional[str] = None, image: str = TRACE_IMAGE,
                  runner: str = "podman", timeout: int = 180):
    """COMPILE-ONLY trace (no link) of a TU under the trace image -- mirrors
    ``c2 regtrace`` (which compiles the whole real TU with ``-fo=NUL``). Writes
    ``files`` (the .c TU + any .h) into /src, runs ``wcc386 <cflags> -fo=...
    <main>`` and returns ``trace.parse(stdout)`` augmented with ``by_func``.
    ``main`` defaults to the first ``.c`` file."""
    cfiles = [n for n in files if n.lower().endswith(".c")]
    main = main or cfiles[0]
    stem = Path(main).stem
    work = Path(tempfile.mkdtemp(prefix="c2_regtrace_native_"))
    # Name + owner-pid label so decomp_verify.reap_orphan_warm_containers()
    # can reap us if python is SIGKILLed mid-compile.  Unlabeled `podman run
    # --rm` containers from this path used to leak for DAYS (dosemu2 grinds
    # headless, pins a CPU, and every later build crawls).
    import os as _os
    import uuid as _uuid
    cname = f"c2vrf_trace_{_uuid.uuid4().hex[:12]}"
    try:
        for n, t in files.items():
            (work / n).write_text(t)
        try:
            out = subprocess.run(
                [runner, "run", "--rm", "--name", cname,
                 "--label", f"c2_owner_pid={_os.getpid()}",
                 "-v", f"{work}:/src", image,
                 "wcc386", *cflags.split(), f"-fo={stem}.obj", main],
                capture_output=True, text=True, timeout=timeout).stdout
        except subprocess.TimeoutExpired:
            # podman run was killed but the container keeps running headless;
            # stop it NOW instead of leaving a CPU-pinning zombie.
            subprocess.run([runner, "kill", cname], capture_output=True,
                           timeout=10)
            subprocess.run([runner, "rm", "-f", cname], capture_output=True,
                           timeout=10)
            raise
    finally:
        import shutil; shutil.rmtree(work, ignore_errors=True)
    td = parse_trace(out)
    # attribution: `fb` fires per function (incl trivial) in source order, so the
    # routines zip 1:1 with the source-definition order across the .c files.
    td["by_func"] = attribute(td["routines"], {n: files[n] for n in cfiles})
    td["func_order"] = list(td["by_func"])
    td["stdout"] = out
    return td


def compile_with_trace(source, *, cflags: Optional[str] = None,
                       func: Optional[str] = None, **kw):
    """Compile ``source`` (str or {file: text}) under the TRACE image and return
    ``(build, trace_data)`` where ``trace_data`` is :func:`trace.parse` output
    augmented with a ``by_func`` map (source-order attribution). If ``func`` is
    given, ``trace_data['target']`` is that routine (or None).

    Reuses ``c2.commands.oracle.compile_snippet`` -- same wmake/podman path the
    verifier uses, so the build is byte-identical; only stdout gains the trace.
    """
    from c2.commands.oracle import compile_snippet, DEFAULT_CFLAGS
    files = {"snip.c": source} if isinstance(source, str) else dict(source)
    b = compile_snippet(source, image=TRACE_IMAGE,
                        cflags=cflags or DEFAULT_CFLAGS, **kw)
    td = parse_trace(b.output)
    # `fb` routines zip 1:1 with the source functions (in build/source order);
    # the entry-stub routines trail and are ignored by attribute().
    td["by_func"] = attribute(td["routines"],
                              {n: t for n, t in files.items() if n.lower().endswith(".c")})
    if func is not None:
        td["target"] = td["by_func"].get(func) or td["by_func"].get(func.rstrip("_"))
    return b, td


_CORPUS_CACHE = Path(tempfile.gettempdir()) / "c2-regalloc-corpus"

# The "active" corpus trace for the current decomp-verify run -- populated ONCE
# from the wmake build's own ~WV1 output (no duplicate compiles) and shared by
# every hint detector via active().
_ACTIVE: Optional["RegallocTrace"] = None


def set_active(rt: Optional["RegallocTrace"]) -> None:
    global _ACTIVE
    _ACTIVE = rt


def active() -> Optional["RegallocTrace"]:
    return _ACTIVE


def parse_build_trace(build_output: str, sources: dict[str, str]) -> dict:
    """Parse a wmake build log into {cost_model, loop_base, by_func}.

    The build compiles each TU with the -trace image; wmake echoes the
    ``wcc386 ... X.c`` command before each file's ``~WV1`` block, so we segment
    the log by those echo lines and attribute each file's block against THAT
    file's source (read from the staging dir, so it matches the compiled bytes
    exactly). Only files that actually (re)compiled appear -- incremental builds
    yield a partial result that the caller merges into the persisted cache.
    """
    by_func: dict[str, dict] = {}
    oc_census: dict[str, dict] = {}
    cost: dict = {}
    base = None
    cur_name: Optional[str] = None
    cur: list[str] = []

    def _flush():
        nonlocal cost, base
        if cur_name is None or cur_name not in sources or not cur:
            return
        td = parse_trace("\n".join(cur))
        td["by_func"] = attribute(td["routines"], {cur_name: sources[cur_name]})
        by_func.update(td["by_func"])
        if td.get("oc_events"):
            oc_census[cur_name] = oc_summary(td["oc_events"])
        cost = cost or td.get("cost_model", {})
        base = base if base is not None else td.get("loop_base")

    for ln in build_output.splitlines():
        s = ln.strip()
        if s.startswith("wcc386 ") and s.endswith(".c"):
            _flush()
            cur_name = s.rsplit(None, 1)[-1]
            cur = []
        elif ln.startswith("~WV1 "):
            cur.append(ln)
    _flush()
    return {"cost_model": cost, "loop_base": base, "by_func": by_func,
            "oc_census": oc_census}


def oc_summary(events: list[dict]) -> dict:
    """Per-TU summary of the OC-queue merge stream (the corpus-grounding
    view persisted in the build cache; full streams stay in the per-file
    ``file_trace`` caches).  Invariants this lets `c2 trace-census` check
    corpus-wide: nj == ct (every splice births exactly one back-jump);
    op >= em - born (deletions are visible as op-without-em); the first fq
    postdates the last op (whole-TU-accumulate drain model)."""
    tags: dict[str, int] = {}
    op_cls: dict[str, int] = {}
    em_cls: dict[str, int] = {}
    fw_save: dict[str, int] = {}
    ct_save: dict[str, int] = {}
    jm_save: dict[str, int] = {}
    em_bytes = 0
    last_op_seq = first_fq_seq = None
    for e in events:
        t = e["tag"]
        tags[t] = tags.get(t, 0) + 1
        if t == "op":
            op_cls[str(e["cls"])] = op_cls.get(str(e["cls"]), 0) + 1
            last_op_seq = e.get("seq")
        elif t == "em":
            em_cls[str(e["cls"])] = em_cls.get(str(e["cls"]), 0) + 1
            em_bytes += e["objlen"]
        elif t == "fw":
            k = str(min(e["save"], 64))   # cap the tail
            fw_save[k] = fw_save.get(k, 0) + 1
        elif t == "ct":
            ct_save[str(e["save"])] = ct_save.get(str(e["save"]), 0) + 1
        elif t == "jm":
            jm_save[str(e["save"])] = jm_save.get(str(e["save"]), 0) + 1
        elif t == "fq" and first_fq_seq is None:
            first_fq_seq = e.get("seq")
    return {"tags": tags, "op_cls": op_cls, "em_cls": em_cls,
            "fw_save": fw_save, "ct_save": ct_save, "jm_save": jm_save,
            "em_bytes": em_bytes,
            "drain_after_push": (None if last_op_seq is None
                                 or first_fq_seq is None
                                 else first_fq_seq > last_op_seq)}


@functools.lru_cache(maxsize=4)
def trace_image_id(image: str = None) -> str:
    """The CURRENT trace image's identity (12-hex podman image ID), mixed
    into every trace-cache key/stamp so a REBUILT image (new probes)
    auto-invalidates all cached traces.

    This closes the long-standing stale-cache class where a probe added to
    patch_trace.py required someone to REMEMBER to bump _CACHE_VERSION --
    forgetting it served old traces silently missing the new records
    (bit the lw/dn/lcx rollout, 2026-07-09).  _CACHE_VERSION now covers
    only PARSER-side schema changes (new fields extracted from existing
    records); image-side changes are automatic.

    Returns "noimage" when podman/the image is unavailable so offline
    cache READS still work (they were written with a real id, so a
    missing image simply misses -- the correct behaviour, since a compile
    would fail anyway)."""
    img = image or TRACE_IMAGE
    try:
        out = subprocess.run(
            ["podman", "image", "inspect", "-f", "{{.Id}}", img],
            capture_output=True, text=True, timeout=15)
        if out.returncode == 0 and out.stdout.strip():
            return out.stdout.strip()[:12]
    except Exception:
        pass
    return "noimage"


def load_cache(cache_path):
    """Load the persisted per-function build trace (or None).

    Entries written by an older trace-record schema OR a different trace
    IMAGE are DISCARDED wholesale (version + image stamp check): a
    stamp-less merge would silently degrade the hints that depend on newer
    records (e.g. fr `blk` tags -> the Rule 122 reorder test returns None
    instead of a verdict; the lw census silently absent)."""
    cache_path = Path(cache_path)
    if not cache_path.exists():
        return None
    try:
        data = json.loads(cache_path.read_text())
    except Exception:
        return None
    if data.get("v") != _CACHE_VERSION:
        return None
    if data.get("img") != trace_image_id():
        return None
    return _rebuild_ir(data)


def update_cache(cache_path, parsed: dict) -> dict:
    """Merge a (possibly partial, incremental) parsed build trace into the
    persisted sidecar so non-recompiled files keep their entries. Returns the
    merged {cost_model, loop_base, by_func}."""
    cache_path = Path(cache_path)
    data: dict = {"by_func": {}}
    if cache_path.exists():
        try:
            data = json.loads(cache_path.read_text())
        except Exception:
            data = {"by_func": {}}
        if (data.get("v") != _CACHE_VERSION
                or data.get("img") != trace_image_id()):
            data = {"by_func": {}}      # schema/image changed: drop stale entries
    data["v"] = _CACHE_VERSION
    data["img"] = trace_image_id()
    data.setdefault("by_func", {}).update(parsed.get("by_func", {}))
    data.setdefault("oc_census", {}).update(parsed.get("oc_census", {}))
    if parsed.get("cost_model"):
        data["cost_model"] = parsed["cost_model"]
    if parsed.get("loop_base") is not None:
        data["loop_base"] = parsed["loop_base"]
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    # JSON-safe view: strip the per-routine IRForest objects (cyclic, not
    # serializable -- the silent killer that kept this cache stale for two
    # days: json.dumps raised, the caller's except swallowed it, and every
    # consumer fell back to per-file container compiles).  `_ir_records`
    # stays in the file; readers rebuild via _rebuild_ir.
    _strip_ir_for_cache(data)
    cache_path.write_text(json.dumps(data))
    return _rebuild_ir(data)


def _headers(include_dir) -> dict[str, str]:
    return {h.name.upper(): h.read_text(errors="replace")
            for h in Path(include_dir).glob("*.h")}


_CACHE_VERSION = 58   # v58: frx GROUND-TRUTH pairing is POSITIONAL (each frx attaches to the fr that immediately precedes it in the stream) instead of the per-class index zip -- the zip mis-aligned every truth after a NULL-return fr (except mask covers the whole ring, no frx fires; common.c move_clock_ferret row 1 = except 0x7fffffff), poisoning ~148/12k rover-pick certifications.  A NULL-return fr now carries NO truth.  Also parses the >= 2026-07-13 image's br records (post-MakeFlowGraph chain snapshot -> routine['chain_post_mfg']) and the fr except-mask components zap/live/resreg (the c2.regalloc.rover counterfactual substrate).  v57: ct records re-parsed with the REAL 5-field commit schema (ins, winner, old, new, save) -- v56 mislabeled the 0x67a7b AddNewJump-commit payload as a 2-field entry record ({list,ins} were actually {ins,winner}); legacy 2-field images still parse.  Discovered while root-causing action's Rule 135 epilogue (2026-07-12): the ct/fw/cc/op/em OC-queue streams sufficed to derive the whole ComTail/TransformJumps mechanism -- no new probes needed.  v56: ct/ctc/ctj/ctw (ComTail canonical-decision probes, image 2026-07-11b) parsed -- entry list+ins, per-candidate FindCommon save, JustMoveLabel outcome, the AddNewJump commit (ins->winner+save).  The canonical choice restructures the block chain (= the LdStAlloc walk order), rooting action's mid-epilogue + byte-rover rotation.  v55: bump on schema change; old caches are bypassed.  v55: frx (FindRegister ground-truth return, hook 0x62aaf) parsed into routine['frx'] ({rover, cls, mask, blk}; pairs 1:1 with same-class fr records) -- the rover pick becomes DIRECTLY visible, no simulation needed (caesar2 action byte-rotation session 2026-07-11).  v54 (image 2026-07-10j): nf (FreeName@0x3a24e name-DEATH) records parsed into routine['nf'] ({name, caller, seq}) -- the nb complement: joins by ptr + seq interleaving resolve name LIFETIMES through frl recycling, and the caller RA names the CULLING pass (measured: the bool-collapse cleanup 0x43cxx family, the pre-RegAlloc sweep ~0x586xx, the FreeNames teardown).  nb records now carry seq too (the global ~WV1 stream ordinal) for the chronological join.  Motivation: Rule 107 insert-window construct screening -- byte-neutral candidate temps (coalesced `t = x;` user temps, dead stores) birth then die INVISIBLY before AssignTemps; nf makes the death + killer observable so tempbirths/spell can screen for SURVIVAL instead of inferring from count deltas (build_road_from_elastic / set_route_elastic_range residues, caesar2 2026-07-10).  v53: al rows carry birth_walk_idx = the conf ptr MOST-RECENT cn-birth walk vintage AT PRESENTATION TIME (stream-order dict; free-list-reuse safe -- a global last-birth-wins map misjoined 871 round-0 rows).  cn recs still carry walk_idx (pre-fb = 0, in-routine = len(il_walks) at birth).  savings.py joins birth_walk_idx (savings computed at CREATION and carried: get_range1 start born r0/presented r1, sav = walk-0 computation); toogreedy joins the presentation walk_idx.  v51: alloc rows carry walk_idx -- the il_walks index CURRENT at presentation time (stream-order join for the per-round snapshots; round ordinals desync from walk ordinals when a trip presents zero conflicts: get_range1 has 3 walks / 2 rounds and its round-1 rows consume walk 2).  savings.py/toogreedy.py join by walk_idx.  v50 (image 2026-07-10i): PER-ROUND bs/be/iv snapshots -- RegAlloc's three round loop-back edges (AssignConflicts!=1 @0x584ea, MoreConflicts full-rebuild @0x58512, LiveInfoUpdate @0x58519) re-run the full walk, each prefixed by an `rr <edge>` header parsed into il_walks[n]['edge'] (round index = walk ordinal; il_walks[0] stays the certified round-0 vintage every existing consumer pins).  Rounds >= 1 carry the previous round's FixInstructions rewrites (temp->N_REGISTER result/operand swaps observed live) + refreshed live sets: closes the round>0/pos-miss CalcSavings gap classes (P1) and records the between-round IL a FixInstructions port (P5) certifies against.  v49 (image 2026-07-10f): iv reg fields resolve THROUGH one N_INDEXED level (class-4 name -> index name @+0xc -> hw_reg_set if the index is N_REGISTER) -- FlowConflicts NowAlives the INDEX of indexed operands/results, which for struct-copy MOVs (lea esi/edi setup) IS a register name.  v48 (image 2026-07-10e): iv rows carry DIRECT hw_reg_set fields res_reg/op0_reg/op1_reg (no regmap join needed; register-PAIR names -- struct-copy MOVs -- resolve too) + xtra_regs = OR-fold of operands[2..N-1] (the CALL parm registers FlowConflicts walks; op0/op1 alone lose them).  v47 (image 2026-07-10d): bs/be/iv snapshot MOVED from MakeConflicts entry (0x5930f -- STALE: pre-NOP-prefix/Renumber/FlowConflicts-rebuild, mixed UpdateLive vintages, 33% single-step transition exactness) to RegAlloc 0x584b9, AFTER MakeConflicts->MakeLiveInfo->AxeDeadCode and immediately before the allocation rounds: the ONE-VINTAGE state the first GiveBestReg round consumes; streams post-fb (walks attach to the open routine; lazy wrap-detected walk splits).  v46 (image 2026-07-10c): bs/be/iv full-IL + liveness snapshot at MakeConflicts (per-block boundary live sets + successor EDGES = the flow graph + every ins with live sets/metas -- the PRE-ALLOCATION baseline for the IL->liveness model, item 3 substrate), parsed into routine['il_walks'] (bb-delimited, buffered before fb like block_by_block); wr trailing <usage> field (conf->name->v.usage: 0x88 = NEEDS_MEMORY|USE_ADDRESS = the NeighboursUse live-across gate polarity, USE_IN_ANOTHER_BLOCK = NowAlive/NowDead channel) surfaced as alloc row 'usage' -- closes neighbours.py's usage_mem guess.  v45: gi trailing extension (image 2026-07-10b): ins ptr + NeighboursUse inputs (live.regs, live.out[0..3], live.within, zap->reg) per walked ins, gi walk now performs the REAL block hop (the per-block ins list is CIRCULAR -- the 0x4b sentinel's next is the SAME block's first ins, so the old +4 walk silently looped inside one block), and each gi burst is also attached to its OWN alloc row as own_walk (per-presentation segmentation; the legacy per-conf-ptr _gi join concatenates presentations and free-list re-owners).  v44: ce/cm (CountRegMoves entry + per-contribution credit events, 2026-07-10 image) parsed into alloc rows as crm_tree {temp, alt, size} + crm_events [{cand, ins, total}] (commit-window scoped like cand_scores) -- the credit ground truth: value set = {tree->temp, tree->alt} (alias ring), credit unit = tree->size, walk = the compiler's own block-hopping range traversal.  v43: nb (AllocName per-class name-birth) records parsed into routine['nb'] -- creation order + FE line attribution for every name (Names[N_TEMP] = reversed(nb class==2 survivors)), closing the source->nb1 link of the slot chain; the nb1->nb2 (AllocBefore) and nt_pre->nt_post (SortCmp_flag2_2b) ShellSorts were both validated 100% on the byte-exact corpus 2026-07-09 (1137/1137 and 1224/1224, an-order 138/138; the earlier 30 'failures' were multi-round nb1/nb2 concatenation in this parser, fixed by per-event segmentation in the validator).  v42: lw (LdStAlloc complete per-ins walk), dn (GiveRegister denials), lcx0..lcx5 (LdStCompress rejection reasons) -- the 2026-07-09 probe set consumed by c2.regalloc.lwalk / c2 spell / the Rover hint lw census.  v41: nb1/nb2 records carry loc24([+0x24]) + off10([+0x10]) -- the AllocBefore comparator's both-no-conflict/savings tiebreak fields (needed to reproduce BuildNameConflicts' non-stable ShellSort, the nb1->nb2 step).  v40: nt/na records carry the two SortCmp_flag2_2b tiebreak dwords (+0x10 v.offset descending, +0x24 t.location) as off10/loc24 -- 10.0a's AssignTemps sort is NOT stable on same-size temps, it orders them by +0x10 descending.  v39 added per-`round` tags to presort/postsort/alloc entries (Mechanism A, RegAlloc outer-loop AssignConflicts retry), wired through reproduce_order and rounds_summary.  Layer 2 of reproduce_order also gained the alloc canonicalisation (drop sav=0 InMemory, dedupe FixInstructions echoes, sub-sequence not prefix to allow CONFLICT_ON_HOLD skips) -- 100 % on byte-exact corpus, no cache schema change required for that part.
                      # v30 adds Score (sb/sbi/sbs) + MergeIndex (mic/mip/mi)
                      # events from the 2026-06-22 patch_trace probe sweep --
                      # `score_events` / `mergeindex_events` on every routine.
                      # (22: wibo pivot -- DOS-trace caches retired)
                      # v17: routine retlists/comtail (rl/cm ComTail records)
                      #      + top-level opt (option-resolver snapshot)
                      # v18: comtail field 2 renamed line->raw20 (census-
                      #      grounded: an oc_entry header word, NOT a line)
                      # v19: top-level oc_events (op/fw/ct/jm/lb/cc/sc/fq) --
                      #      the unit-global OC-queue tail-merge stream
                      # v20: 2026-06-12b image -- op grows hdr/b2/w10/w14;
                      #      new em (emit ledger) / nl (label birth) / nj
                      #      (splice back-jump); rl/cm retired from the
                      #      image (fw supersedes); seq on oc_events + ge
                      #      cgen events (cross-stream interleave join).
                      #      MUST bump here on image rebuilds that add
                      #      records: the compile cache key hashes source
                      #      text + flags, NOT the image.
                     # v3: added per-routine `emit_lengths` / `emit_offsets` /
                     #     `code_size` (from `il` AdvanceCode-entry trace record).
                     # v4: added per-routine `ge_events` (from `ge`
                     #     GenObjCode-entry trace record).
                     # v5: `ge` and `il` interleaved into `cgen_events`
                     #     (per-cg_ins record with offset + il_bytes derived
                     #     from chronological walk).  `ge_events` removed --
                     #     replaced by `cgen_events`.
                     # v6: added per-routine `confs` (from `cn`
                     #     AddConflictNode-exit trace record): the
                     #     conflict CREATION order, measured at the
                     #     creation site -- the equal-savings tie-break
                     #     substrate (pre-ShellSort input).
                     # v7: alloc rows carry `tree_cands` (from `bt`
                     #     GiveBestReg-entry record): the REAL candidate
                     #     list (tree->regs after BuildRegTree/MarkPossible
                     #     narrowing) -- the al-squat exclusion detector
                     #     (watcom10.0a docs/al-squat-family.md).
                     # v8: routine `ldst_blocks` (from `bk` LdStAlloc
                     #     block-walk record) + fr rows carry `blk` (the
                     #     bk index they followed): exact block grouping
                     #     of rover advances -- the Rule 121/122 arm-swap
                     #     reorder-test substrate.


def _rebuild_ir(td: dict) -> dict:
    """Reconstruct per-routine ``IRForest`` objects from the cached raw IR
    records list (``_ir_records``).  IRForest itself is not JSON-friendly
    (cyclic references via Node.left/right), so we cache the chronological
    raw records and rebuild on read.

    Iterates BOTH ``routines`` (the canonical per-source-order list) AND
    ``by_func`` (the name->routine index).  When the cached blob is
    JSON-roundtripped, ``by_func`` and ``routines`` no longer share
    object identity, so we have to rebuild on each independently --
    otherwise consumers accessing routines via ``by_func`` (the common
    path) would see ``_ir_records`` but no ``ir`` forest.
    """
    from c2.ir import build_forest

    def _ensure(ro: dict) -> None:
        if "ir" in ro:
            return
        recs = ro.pop("_ir_records", None)
        if recs is None:
            return
        ro["ir"] = build_forest([(t, list(f)) for t, f in recs])

    for ro in td.get("routines", []):
        _ensure(ro)
    for ro in td.get("by_func", {}).values():
        _ensure(ro)
    return td


def _strip_ir_for_cache(td: dict) -> dict:
    """Replace each routine's ``IRForest`` object with the raw ``_ir_records``
    list (populated by the parser) -- the build_forest() input is small,
    deterministic, and JSON-friendly.  Routines keep all other fields.

    Strip on BOTH ``routines`` and ``by_func`` for the same reason
    ``_rebuild_ir`` rebuilds on both: JSON-roundtripping breaks the
    object-identity that the in-memory build relies on."""
    for ro in td.get("routines", []):
        ro.pop("ir", None)
    for ro in td.get("by_func", {}).values():
        ro.pop("ir", None)
    return td


def file_trace(cfile, include_dir, *, cflags: str = PS_CFLAGS,
               image: str = TRACE_IMAGE, runner: str = "podman",
               headers: Optional[dict] = None) -> dict:
    """Trace ONE .c file (compile-only, byte-faithful to decomp-verify's per-TU
    build), disk-cached by content hash. Returns the trace dict with ``by_func``
    AND a freshly-built ``IRForest`` per routine (rebuilt from the cached raw
    IR records list on every read -- IRForest's cyclic graph isn't JSON-safe).

    Only changed files re-compile (like wmake), so this is the per-file unit
    the hint layer uses lazily for just the function(s) it inspects."""
    cfile = Path(cfile)
    text = cfile.read_text(errors="replace")
    headers = _headers(include_dir) if headers is None else headers
    hdr_key = hashlib.sha1("".join(sorted(headers.values())).encode()).hexdigest()[:8]
    key = hashlib.sha1(
        f"v{_CACHE_VERSION}\0{trace_image_id(image)}\0"
        f"{cfile.name}\0{text}\0{cflags}\0{hdr_key}".encode()
    ).hexdigest()[:16]
    cache = _CORPUS_CACHE / key / "trace.json"
    if cache.exists():
        return _rebuild_ir(json.loads(cache.read_text()))
    td = trace_compile({cfile.name: text, **headers}, cflags=cflags,
                       main=cfile.name, image=image, runner=runner)
    td.pop("stdout", None)
    # Write a JSON-safe view (strip IRForest objects), then rebuild for the
    # in-memory return value.
    _strip_ir_for_cache(td)
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(td))
    # stamp the entry so `c2 cache gc` can prune orphaned key-spaces
    # PRECISELY (keys are opaque hashes; without the stamp, age is the
    # only GC signal)
    (cache.parent / "meta.json").write_text(json.dumps(
        {"v": _CACHE_VERSION, "img": trace_image_id(image),
         "src": cfile.name}))
    return _rebuild_ir(td)


def corpus_trace(src_dir, include_dir, *, cflags: str = PS_CFLAGS,
                 image: str = TRACE_IMAGE, runner: str = "podman") -> "RegallocTrace":
    """Full-corpus register-allocation trace, attributed per function, cached
    per .c file by content hash.

    Compiles each ``src_dir/*.c`` compile-only with the trace image and the
    headers from ``include_dir`` -- this is exactly how decomp-verify's wmake
    builds each TU (separately, then links), so the codegen (and thus the
    allocation) is byte-faithful. Parsing happens ONCE per file and is cached
    (only changed files re-compile, like wmake), so hints share a single parsed
    result without duplicating work.
    """
    src_dir, include_dir = Path(src_dir), Path(include_dir)
    headers = _headers(include_dir)
    by_func: dict[str, dict] = {}
    routines_all: list[dict] = []
    cost: dict = {}
    base = None
    for c in sorted(src_dir.glob("*.c")):
        td = file_trace(c, include_dir, cflags=cflags, image=image,
                        runner=runner, headers=headers)
        cost = cost or td.get("cost_model", {})
        base = base if base is not None else td.get("loop_base")
        by_func.update(td.get("by_func", {}))
        routines_all.extend(td.get("routines", []))
    return RegallocTrace({"cost_model": cost, "loop_base": base,
                          "routines": routines_all, "by_func": by_func})


def name_list(routine: dict) -> list:
    """The routine's conflict-CREATION order with each name's identity,
    from the ``cn`` (AddConflictNode-exit) trace stream
    (``routine["confs"]``) -- a direct per-creation measurement that also
    carries the name pointer + name class, and includes conflicts created
    after the pre-sort snapshot (RegAlloc retry rebuilds).

    NOTE: conflict-creation order is NOT identical to ``nb`` name-birth order
    (see :func:`name_birth_order`).  ``AssignGlobalBits`` walks ``Names[N_TEMP]``
    AFTER ``RoughSortTemps`` resorts it by savings (dataflo.c:131,
    ``AllocBefore``), so conflicts come out in savings-sorted order, not in
    AllocName order.  For example, in probe.c routine 0 the 1st-born name
    (savings=3) maps to the 2nd-created conflict because a 2nd-born name with
    savings=4 sorted ahead of it.

    Use this function for "in what order did the back end PROCESS conflicts?"
    -- the ConfList pre-sort layout that ``SortList`` operates on.  Use
    :func:`name_birth_order` for "in what order did the front end DECLARE
    names?" -- the source-side lever (declaration order).

    Returns, in conflict-creation order:
        [{conf, name, savings, defline, nameclass, reg_name, regclass_name}]
    ``defline`` (source line of the def) is the steering handle; ``name``
    is the in-compiler name pointer (hex) -- joins with ``nb`` records.
    """
    by_conf = {a["conf"]: a for a in routine.get("alloc", [])}
    savings_by_conf = {e["node"]: e["savings"]
                       for e in routine.get("presort", [])}
    out = []
    for e in routine.get("confs", []):
        a = by_conf.get(e["conf"], {})
        out.append({
            "conf": e["conf"], "name": e["name"],
            "savings": savings_by_conf.get(e["conf"], a.get("savings")),
            "defline": a.get("defline"),
            "nameclass": a.get("nameclass_name"),
            "reg_name": a.get("reg_name"),
            "regclass_name": a.get("regclass_name"),
            "var": a.get("var"),
        })
    return out


def name_birth_order(routine: dict, cls: int = 2) -> list:
    """Per-class name birth order from the instrumented ``nb`` (AllocName)
    stream -- the FRONT-END declaration order, i.e. the source-side lever
    (Rule 28 / Rule 115).

    Ground truth straight from the trace's IR forest, NOT inferred from
    ``presort``.  Returns ``[]`` when the trace lacks IR data.

    ``cls`` defaults to ``N_TEMP=2``; pass ``N_REGISTER=3``, ``N_MEMORY=1``,
    etc. for other classes.

    Each entry is JOINED with the matching ``al`` record on
    ``a["name"] == name.ptr``.  Names without an ``al`` record were filtered
    by ``BuildNameConflicts`` (typical reasons: dead temp, USE_MEMORY forced
    to stack, alias chain collapsed to a representative) -- those entries
    appear with ``conf=None`` so callers can SEE the gap.

    Returns, in birth order:
        [{name, conf, savings, defline, nameclass, reg_name, regclass_name}]
    where ``name`` is the in-compiler name pointer (hex) and ``conf`` is the
    conflict pointer (hex) or ``None`` if no conflict was created.

    Compare with :func:`name_list` (conflict creation order).  The two are
    DIFFERENT views -- birth order is what the source code controls;
    creation order is what the back end actually saw.  See ``name_list``'s
    docstring for the semantic difference.
    """
    ir = routine.get("ir")
    if ir is None:
        return []
    names = ir.names_by_class.get(cls, [])
    if not names:
        return []
    by_name = {int(a["name"], 16): a for a in routine.get("alloc", [])}
    savings_by_conf = {e["node"]: e["savings"]
                       for e in routine.get("presort", [])}
    out = []
    for nm in names:
        a = by_name.get(nm.ptr)
        if a is None:
            out.append({"name": f"{nm.ptr:x}", "conf": None,
                        "savings": None, "defline": None,
                        "nameclass": nm.cls_name, "reg_name": None,
                        "regclass_name": None})
            continue
        out.append({
            "name": f"{nm.ptr:x}",
            "conf": a["conf"],
            "savings": savings_by_conf.get(a["conf"], a["savings"]),
            "defline": a.get("defline"),
            "nameclass": a.get("nameclass_name"),
            "reg_name": a.get("reg_name"),
            "regclass_name": a.get("regclass_name"),
            "var": a.get("var"),
        })
    return out


def _is_subsequence(sub, full):
    """True iff ``sub`` is an order-preserving subsequence of ``full``."""
    i = 0
    for x in full:
        if i < len(sub) and sub[i] == x:
            i += 1
    return i == len(sub)


def _alloc_canon(alloc_round: list[dict], post_set: set) -> list[str]:
    """Canonicalise a round's ``alloc`` stream into the set of conflicts
    that went through ``SortConflicts`` and were allocated this round.

    Three filters peel away the noise that's NOT a SortConflicts output:

    1. **Drop ``savings == 0`` entries** — ``AssignConflicts`` routes those
       through ``InMemory`` (OW v1 ``regalloc.c:1107``), bypassing
       ``GiveRegister`` and the sort entirely.
    2. **Drop entries whose conf isn't in this round's postsort** —
       sub-conflicts split off later (NEEDS_INDEX_SPLIT etc.) and other
       sort-bypassing allocations.
    3. **Dedupe to first occurrence** — ``FixInstructions`` re-emits an
       ``al`` per use-site of the allocated conflict; we keep only the
       first (which is the SortConflicts-driven allocation event).

    The result is the order in which ``GiveRegister`` allocated
    SortConflicts-driven conflicts in this round.  It's a sub-sequence
    (not a prefix) of postsort: ``CONFLICT_ON_HOLD`` conflicts are sorted
    into postsort but skipped this round (released to the next).
    """
    seen = set()
    out = []
    for a in alloc_round:
        if (a.get("savings") or 0) <= 0:
            continue
        c = a["conf"]
        if c not in post_set or c in seen:
            continue
        seen.add(c)
        out.append(c)
    return out


def reproduce_order(routine: dict) -> bool:
    """True if our ShellSort over the routine's pre-sort list reproduces its
    actual allocation order (H2 self-check).

    Per-ROUND validation (Mechanism A, ``docs/mechanism-survey-2026-06-25.md``):
    OW v1 ``RegAlloc()`` runs an outer ``for(;;)`` loop that calls
    ``AssignConflicts`` (= ``CalcSavings`` + ``SortConflicts``) multiple
    times; each iteration emits its own ``sl``/``sa`` stream.  The trace
    parser tags every ``sl``/``sa``/``al`` entry with a ``round`` index
    (see ``trace.py``).  This check partitions presort/postsort/alloc by
    that round and runs the ShellSort + alloc check PER ROUND.

    Two layers, applied per round:
      1. Offline ShellSort on the round's ``presort`` reproduces the
         round's ``postsort`` head dump (the ``sa`` records).  Direct
         compare on the SortConflicts output.
      2. The round's ``alloc`` events, **canonicalised** by
         :func:`_alloc_canon` (drop ``savings==0`` InMemory bypass, drop
         sort-bypassing sub-conflicts, dedupe FixInstructions echoes), is
         an order-preserving **sub-sequence** of postsort.  Not a prefix:
         ``CONFLICT_ON_HOLD`` conflicts are sorted but skipped this round.

    Validated against the full byte-exact corpus (N=1102): 100 % pass.
    Legacy traces without ``round`` tags fall back to the old single-
    pass check.
    """
    presort = routine.get("presort") or []
    postsort = routine.get("postsort") or []
    alloc = routine.get("alloc") or []
    if not presort:
        return True
    has_rounds = any("round" in e for e in presort)
    if not has_rounds:
        # Legacy single-pass fallback.
        pre = [{"id": e["node"], "savings": e["savings"]} for e in presort]
        sort.shell_sort(pre,
                        lambda a, b: sort.conf_before(a["savings"], b["savings"]))
        got = [e["id"] for e in pre]
        if postsort and got != [e["node"] for e in postsort]:
            return False
        return got == [a["conf"] for a in alloc[:len(pre)]]
    # Per-round.  Partition all three streams by `round`.
    rounds = sorted({e.get("round", 0) for e in presort}
                    | {e.get("round", 0) for e in postsort}
                    | {a.get("round", 0) for a in alloc})
    for ri in rounds:
        pre_r = [{"id": e["node"], "savings": e["savings"]}
                 for e in presort if e.get("round", 0) == ri]
        post_r = [e for e in postsort if e.get("round", 0) == ri]
        if not pre_r:
            continue
        sort.shell_sort(pre_r,
                        lambda a, b: sort.conf_before(a["savings"], b["savings"]))
        got = [e["id"] for e in pre_r]
        # Layer 1: direct sa head compare for this round.
        if post_r and got != [e["node"] for e in post_r]:
            return False
        # Layer 2: canonicalised alloc is a sub-sequence of postsort.
        post_ids = [e["node"] for e in post_r]
        post_set = set(post_ids)
        alloc_r = [a for a in alloc if a.get("round", 0) == ri]
        canon = _alloc_canon(alloc_r, post_set)
        if canon and not _is_subsequence(canon, post_ids):
            return False
    return True


def rounds_summary(routine: dict) -> list[dict]:
    """Per-round summary: ``[{round, n_presort, n_postsort, n_alloc,
    layer1_ok, layer2_ok}]``.

    Diagnostic companion to ``reproduce_order``: when ``reproduce_order``
    returns False, this tells you WHICH round failed and which layer.
    Empty list if the trace doesn't carry round tags (legacy).
    """
    presort = routine.get("presort") or []
    if not any("round" in e for e in presort):
        return []
    postsort = routine.get("postsort") or []
    alloc = routine.get("alloc") or []
    rounds = sorted({e.get("round", 0) for e in presort}
                    | {e.get("round", 0) for e in postsort}
                    | {a.get("round", 0) for a in alloc})
    out = []
    alloc_idx = 0
    for ri in rounds:
        pre_r = [{"id": e["node"], "savings": e["savings"]}
                 for e in presort if e.get("round", 0) == ri]
        post_r = [e for e in postsort if e.get("round", 0) == ri]
        alloc_r = []
        while alloc_idx < len(alloc) and alloc[alloc_idx].get("round", 0) == ri:
            alloc_r.append(alloc[alloc_idx])
            alloc_idx += 1
        if not pre_r:
            out.append({"round": ri, "n_presort": 0,
                        "n_postsort": len(post_r), "n_alloc": len(alloc_r),
                        "layer1_ok": None, "layer2_ok": None})
            continue
        sort.shell_sort(pre_r,
                        lambda a, b: sort.conf_before(a["savings"], b["savings"]))
        got = [e["id"] for e in pre_r]
        post_ids = [e["node"] for e in post_r]
        post_set = set(post_ids)
        layer1 = (got == post_ids) if post_r else None
        canon = _alloc_canon(alloc_r, post_set)
        layer2 = (_is_subsequence(canon, post_ids)
                  if canon else (None if not alloc_r else True))
        out.append({"round": ri, "n_presort": len(pre_r),
                    "n_postsort": len(post_r), "n_alloc": len(alloc_r),
                    "n_alloc_canon": len(canon),
                    "layer1_ok": layer1, "layer2_ok": layer2})
    return out
