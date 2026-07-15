"""Parse the wcc386 ``~WV1`` register-allocation trace.

The trace is emitted on stdout by the instrumented compiler baked into the
``localhost/watcom-10.0a-wibo-trace`` image (see the watcom10.0a RE repo,
tools/patch_trace.py). It is byte-identical-.obj instrumentation: read-only
hooks that ``printf`` an extensible, versioned line schema.

Schema (v1) -- each line ``~WV1 <tag> <fields...>``:
    cost <arrayAddr:hex> <value:dec>   per Save cost category at startup
                                       (order: load,store,use,def,push,pop)
    lwt  <time:dec>                    SetLoopCost arg; base = (20*time)//256
    fn                                 routine begin (Nth fn == Nth routine
                                       compiled == source-definition order)
    sl   <node:hex> <savings:dec>      PRE-sort ConfList, in list order
    al   <conf:hex> <name:hex> <savings:dec> <regclass:hex> <first:hex> <last:hex> <nameclass:hex> [<defline:dec>]
         defline = source line of the conflict's first non-block instruction
         (ins+0x20); present in trace-image builds from 2026-06 on, else None.
                                       post-sort allocation order (GiveRegister)
    rg   <conf:hex> <regmask:hex>      assigned hw_reg_set (absent => spilled)
    wr   <conf:hex> <withregs:hex> [first last wo0..3 wwi idw io0..3]
                                       conf->with.regs (interference set); FIRST
                                       sighting within the routine's block sticks.
    gi   <conf> <op> <res> <res_reg> <op0> <op0_reg> <op1> <op1_reg>
                                       one per instruction in the conflict's range
                                       (CountRegMoves substrate).

    -- IR-construction records (parsed into ``routine['ir']`` -- see c2.ir) --
    tn   <ptr> <class> <op> <left> <right> <tipe>  TGNode interior
    tb   <ptr> <sub> <tipe> <start> <length>       TGBitLValue leaf
    tl   <ptr> <class> <name|val> <tipe>           TGLeaf leaf
    nb   <ptr> <class> <subclass> <name_id>        AllocName (name birth)
    ni   <ptr> <nops>                              NewIns (instruction birth)

Feeding a routine's ``sl`` list through ``c2.regalloc.sort`` reproduces its
``al``/``rg`` order exactly (H2). ``cost``/``lwt`` give the savings model.
``al`` (name=value handle) + ``wr`` + ``gi`` reproduce the GiveBestReg SELECTION
offline (c2.regalloc.seatchain, full-chain identity certified).

Each routine carries an ``ir`` :class:`c2.ir.IRForest` built from its tn/tb/tl/
nb/ni records: tree forest + per-class name creation order (ConfBefore tie-
break input) + statement roots.  This is the single shared reconstruction --
every consumer (rule predictors, decomp-verify hints, seatchain) imports it.
"""
from __future__ import annotations

from c2.ir import IR_TAGS, build_forest

COST_ORDER = ["load_cost", "store_cost", "use_save", "def_save", "push_cost", "pop_cost"]
NAME_CLASS = {0: "N_CONSTANT", 1: "N_MEMORY", 2: "N_TEMP", 3: "N_REGISTER", 4: "N_INDEXED"}
REG_CLASS = {0x04: "byte", 0x08: "word", 0x0F: "dword", 0x10: "dword",
             0x13: "pair", 0x14: "pair", 0x17: "pair"}

# hw_reg_set masks -> register name (32-bit GP; see c2.regalloc.reglists).
# Byte-pair bit order per OW v1 cgi86reg.h: H = LOW bit (AH=0x1, AL=0x2,
# BH=0x4, BL=0x8, CH=0x10, CL=0x20, DH=0x40, DL=0x80).  Corrected 2026-06-10.
REG_NAME = {0x1000003: "EAX", 0x200000c: "EBX", 0x4000030: "ECX", 0x80000c0: "EDX",
            0x10000100: "ESI", 0x20000200: "EDI", 0x400: "EBP", 0x800: "ESP",
            0x3: "AX", 0xc: "BX", 0x30: "CX", 0xc0: "DX", 0x100: "SI", 0x200: "DI",
            0x2: "AL", 0x1: "AH", 0x4: "BH", 0x8: "BL", 0x10: "CH", 0x20: "CL",
            0x40: "DH", 0x80: "DL"}


def reg_name(mask_hex: str | None):
    if mask_hex is None:
        return None
    return REG_NAME.get(int(mask_hex, 16), "0x" + mask_hex)


def parse(stdout_text: str) -> dict:
    """Parse a trace transcript into {cost_model, loop_time, loop_base, routines}.

    One routine per FUNCTION (delimited by `fb`, emitted for EVERY function incl
    trivial ones), in source/compile order:
        {index, has_regalloc, presort:[{node,savings}],
         postsort:[{node,savings}],          # `sa` records (>= 2026-06-11)
         alloc:[{conf,name, savings,regclass,regclass_name, first,last,
                 nameclass,nameclass_name, reg,reg_name,
                 given_regs}],               # >= 2026-06-11 image
         savecalc:{conf: [{blk,save,cost,depth}]},   # `cv` (>= 2026-06-11)
         retlists:[int], comtail:[{save,raw20}],      # `rl`/`cm` ComTail
         confs:[{conf,name,class}]}

    Top level additionally carries ``opt`` (the `opt` option-resolver
    snapshot: {opt_for_size, flags1, flags2, target}) -- the compile's
    option state; assert it when chasing flag-sensitive codegen deltas.

    Top level also carries ``oc_events`` -- the UNIT-GLOBAL OC-queue tail-
    merge stream in TRACE ORDER (op/fw/ct/jm/lb/cc/sc/fq/em/nl/nj).  These
    are not per-routine (the peephole queue accumulates the whole TU; cross-
    function merges span routines; the drain runs once at the end).  Every
    event carries ``seq`` (the global ~WV1 record index; ge cgen events
    carry it too -- the cross-stream interleave join).  Tags:
      op {entry,hdr,objlen,cls,attr,b2,w10,w14,rtn}
                                       queue-push identity ledger.  w10 =
                                       label/target ptr for transfer
                                       classes (gate on cls!), the offline
                                       crossing-rule predictor.
      fw {cand,ins,old,new,save}       FindCommon result (walk-depth);
                                       save=0 = first-pair mismatch (and
                                       old/new garbage -- gate on save>0).
                                       The comparator needs +0x10 label-ptr
                                       IDENTITY for transfer classes, so a
                                       walk stops at the first distinct-
                                       label jmp-pair (goto-form sibling
                                       functions merge only the common
                                       epilogue suffix).  Bursts share
                                       `ins`; max(save) over a burst == the
                                       retired `cm`, burst size+1 == `rl`.
      ct {ins,best,old,new,save}       ComTail splice commit (keep-first)
      jm {label,old,new,save,ins}      JustMoveLabel commit (keep-first)
      lb {ins,label}                   ChgLblRef (boundary-label merge)
      cc {jmp,label}                   ComCode push-side backward-common
      sc {jmp,label}                   StraightenCode (front-side OptPull)
      fq {}                            drain group; FIRST fq = push->front
                                       boundary
      em {entry,hdr,objlen,cls,attr,b2}
                                       EMIT ledger: final layout order +
                                       final objlen (post-shortening);
                                       cumulative objlen = byte offsets =
                                       the backward join.  op-without-em =
                                       deleted; em-without-op = splice-born.
      nl {label,ins}                   AddNewLabel return: merge-label birth
                                       or REUSE (same ptr repeats)
      nj {add,label}                   AddNewJump: splice back-jump birth,
                                       1:1 with ct
    Old traces' rl/cm records still parse into routine retlists/comtail;
    the >= 2026-06-12b image no longer emits them (fw supersedes both).

    ``postsort`` is the `sa` stream: ConfList head order RIGHT AFTER
    SortList returns -- the EXACT order GiveRegister iterates.  Equals
    the offline-sort of ``presort`` on a clean run; H2 self-check
    compares them.  ``given_regs`` on each alloc is the GivenRegisters
    snapshot at THAT conflict's GiveBestReg entry -- the running set
    of all hw_reg_sets committed by previous allocations; the
    layer-3 tie-break key (``HW_Subset(GivenRegisters, reg)``).
    Byte-class theorem: byte conflicts allocate AFTER the dword ones,
    so given_regs typically already contains every byte reg (committed
    via the dword EAX/EBX/ECX/EDX picks) -> HW_Subset is true for ALL
    byte candidates -> the layer-3 tie-break never discriminates and
    pure candidate-LIST order decides byte seats (Rule 133).

    ``confs`` is the `cn` (AddConflictNode birth) stream: the conflict
    CREATION order for the routine, measured at the creation site -- the
    substrate of every equal-savings tie-break (SortConflicts' ShellSort
    permutes exactly this list, via the PREPENDed ConfList =
    reversed(confs)).  reversed(presort) gives the same order for conflicts
    alive at the pre-sort snapshot; ``confs`` additionally carries the name
    ptr/class and post-snapshot creations.  Join keys: confs[i].conf ==
    alloc[j].conf, confs[i].name == an `nb` ptr (-> source line).
    Trivial functions appear as empty routines (has_regalloc=False).
    """
    cost, lwt, routines = {}, None, []
    opt_state = None     # `opt` record: option-resolver snapshot (once per compile)
    cur = None
    pending = None
    # IR-records attribution per routine.  The compiler's per-routine event
    # sequence is:
    #
    #     [tn/tl/nb/ni for routine K's front-end statements]
    #     fb[K]   (RegAlloc enters for K)
    #     [late inserts: tn/tl/nb/ni from RISCification etc.]
    #     fc[K]   (Generate returns -- routine K is fully done)
    #     [tn/tl/nb/ni for routine K+1]
    #     fb[K+1] ...
    #     fc[K+1]
    #     ...
    #
    # Generate is also called BETWEEN statements (per cg_name batch) -- those
    # interim `fc` events fire during front-end IR building and do NOT end a
    # routine.  The TERMINAL `fc` is the first `fc` AFTER `fb` -- only that
    # one closes the routine.
    ir_buf: list[tuple[str, list[str]]] = []
    cn_buf: list[dict] = []          # cn records fire in MakeConflicts, BEFORE fb
    bo_buf: list[dict] = []          # bo/bor fire in the FE tree burn, BEFORE fb
    br_buf: list[dict] = []          # br (post-MakeFlowGraph chain snapshot)
                                     # fires in Generate's pre-conflicts pass
                                     # window, BEFORE fb -- buffered like bo.
    ni_buf: list[dict] = []          # ni (NewIns IL-instruction birth) fires in
                                     # the FE burn too -- buffered like cn/bo
    ob_buf: list[dict] = []          # ob/oh fire in AssignGlobalBits, also pre-fb
    oh_buf: list[dict] = []
    nb1_buf: list[dict] = []         # nb1/nb2 fire at BuildNameConflicts SortList (pre-fb)
    nb2_buf: list[dict] = []
    _nb_pass_pending = None          # nbc/nbo (SAllocTemp/STempOffset entry) awaiting its nb
    _nb_outer_pending = None         # nbb (BGNewTemp entry) awaiting its nb
    nf_buf: list[dict] = []          # nf (FreeName death) -- buffered like nb
    nb_buf: list[dict] = []          # nb (AllocName birth) fires in the FE burn +
                                     # optimizer passes, mostly pre-fb -- buffered like cn/bo.
                                     # EMIT ORDER == per-class creation order; Names[class]
                                     # is PREPEND-built (AllocName: new->next = head), so
                                     # Names[N_TEMP] head order == reversed(nb class==2).
    bb_pending = None                # BlockByBlock value at MakeConflicts entry, BEFORE fb
    il_walk_buf = []                 # bs/be/iv full-IL snapshot walks (MakeConflicts, BEFORE fb)
    _ixp_buf: dict = {}              # ixp records pending their iv row (per ins ptr)
    # oc_events: the UNIT-GLOBAL OC-queue merge stream (op/fw/ct/jm/lb/cc/
    # sc/fq), in TRACE ORDER.  These are NOT per-routine: the peephole queue
    # accumulates the whole TU and cross-function tail-merges span routines;
    # the front-side drain (fq/sc) runs once at the very end (after the last
    # fc).  Order is load-bearing -- entry pointers (op) are reused from a
    # free list, so a ptr identity is only valid from its `op` record until a
    # ct/jm deletes it; consumers must replay in order.  See
    # tools/patch_trace.py (OC-queue machinery) + knowledge FindCommon.
    oc_events: list[dict] = []
    expect_terminal_fc = False
    seq = -1   # monotonic ~WV1 record index: the cross-stream join between
               # oc_events and cgen_events (ge records carry it too) -- the
               # trace-order interleave is the ONLY link from a cg_ins to
               # the queue entries its emission pushed (op records between
               # consecutive ge records belong to the earlier ge).
    for ln in stdout_text.splitlines():
        f = ln.split()
        if len(f) < 2 or f[0] != "~WV1":
            continue
        tag = f[1]
        seq += 1
        if cur is not None:
            cur["_seq"] = seq
        if tag == "lwt":
            lwt = int(f[2])
            cost = {}            # cost block repeats per compiler invocation; keep the latest
        elif tag == "cost":
            i = len(cost)
            if i < len(COST_ORDER):
                cost[COST_ORDER[i]] = int(f[3])
        elif tag == "opt" and len(f) >= 6:
            # Option-resolver snapshot at FUN_0002ebcc (once per compiler
            # invocation; keep the latest).  opt_for_size == OptForSize
            # (EBX low byte); > 0x32 disables jump-table label alignment in
            # CodeLabel (the cluster #32 trailing-pad delta).  flags1/flags2/
            # target are the raw EAX/EDX/ECX bitfields (see patch_trace.py
            # header for bit meanings, e.g. -od => flags1 bit31).
            opt_state = {"opt_for_size": int(f[2]), "flags1": f[3],
                         "flags2": f[4], "target": f[5]}
        elif tag == "fb":         # RegAlloc enters for routine K
            # routine K just entered regalloc.  If a previous routine is still
            # open (no terminal fc seen between its fb and now -- shouldn't
            # happen in a clean trace, but guard anyway), finalize it.
            if cur is not None:
                _finalize_routine(cur)
            cur = {"index": len(routines), "has_regalloc": False, "presort": [],
                   "postsort": [],
                   "alloc": [], "fr": [], "frx": [], "slots": [],
                   "nt_pre": [], "nt_post": [], "an": [],
                   "nb1": nb1_buf, "nb2": nb2_buf,
                   "nb": nb_buf,
                   "nf": nf_buf,
                   "blocks_born": bo_buf,
                   "chain_post_mfg": br_buf,
                   "il_born": ni_buf,
                   "block_by_block": bb_pending,
                   "il_walks": il_walk_buf,
                   "_wr": {}, "_rng": {}, "_gi": {},
                   "_graph": {},
                   "_seq": 0, "_wr_all": {}, "_bt_all": {},
                   "_gb_all": {}, "_tg_all": {}, "_wp_all": [],
                   "_ce_all": {}, "_cm_all": {},
                   "_ir": ir_buf, "_cg": [], "confs": cn_buf,
                   "ob": ob_buf, "oh": oh_buf,
                   "savecalc": {},
                   "retlists": [], "comtail": [],
                   "ldst_blocks": [],
                   "_round_idx": 0, "_round_open_sa": False,
                   "_conf_birth_walk": {c["conf"]: 0 for c in cn_buf},
                   "score_events": [], "mergeindex_events": []}
                   # `score_events`: PostOptimize Score (redundant-load
                   # coalesce) trace.  One dict per event in stream order:
                   #   {tag:'sb',  seq, ins, opcode, into}  successful coalesce
                   #       (`into` = the counterpart ins folded into;
                   #        >= 2026-07-09 image, else None)
                   #   {tag:'sbi', seq, ins}           call invalidate
                   #   {tag:'sbs', seq, ins, opcode}  aliasing-store invalidate
                   # The consumer pairs PS-vs-RC streams: a sb that fires
                   # on one side and not the other (with the matching ins's
                   # opcode + a sbi/sbs explaining the rejection) names the
                   # specific call/store in the loop body whose presence
                   # caused the divergence.  (caesar2's 'loop-hoist' class.)
                   #
                   # `mergeindex_events`: PostOptimize MergeIndex (index-
                   # fusion) trace.  One dict per event in stream order:
                   #   {tag:'mic', seq, ins, opcode}  candidate_test attempt
                   #   {tag:'mip', seq, ins, opcode}  predicate attempt
                   #   {tag:'mi',  seq, ins, opcode}  fusion commit
                   # Logic: an ins with `mic` but no `mip` => candidate
                   # rejected.  With `mip` but no `mi` => predicate
                   # rejected -- the inner-loop clause (if any) is named
                   # by mir1..6; absence of any mir for the ins means
                   # the rejection was the opcode-ineligible top-of-
                   # function bail (not instrumented; trivial filter).
                   # Schema: mip - mi - sum(mir1..6) = opcode-bail count.
                   # Spec: ~/git/ReverseEngineering/watcom10.0a/docs/
                   # score-redundant-load-and-mergeindex.md.
                   # `savecalc` is the `cv` stream (>= 2026-06-11 image):
                   # conf -> [{blk, save, cost, depth}] -- CalcSavings'
                   # per-block raw unit sums captured at the _UpdateCost
                   # join (savcode.h), BEFORE the Weight multiply.
                   # Invariant (verified): final savings ==
                   #   sum(save*W^min(depth,4)) - sum(cost*W^min(depth,4)),
                   # W = 10 (Save.loop_weight), clamped to 0 / MAX_SAVE-1.
                   # The Rule 126 lever: WHICH block and WHICH unit class
                   # (use/def/index save vs load/store cost) produced a
                   # savings delta between PS and the recompile.
                   # `postsort` is the `sa` stream: ConfList HEAD ORDER
                   # right after SortList returns -- the EXACT order
                   # GiveRegister will iterate.  Cross-check vs offline
                   # sort.shell_sort(presort): they should match
                   # (modulo the ON_HOLD reseat retry rounds).  When
                   # the sequences diverge, the equal-savings tie-break
                   # is the only suspect.
                   # `ldst_blocks` is the bk stream: LdStAlloc's block-walk
                   # order (block-LIST = creation order; Rules 121/122
                   # substrate).  Each fr record carries "blk" = the index
                   # of the bk record it followed, so rover advances group
                   # by block exactly (the arm-swap reorder test input).
                   # `_cg` holds interleaved codegen events (`ge` + `il`) in
                   # trace order; we need the interleaving to compute
                   # per-cg_ins asm offsets (see _finalize_routine).
                   # `confs` drains the cn (conflict-birth) buffer: routine
                   # K's MakeConflicts runs BEFORE fb[K] (Generate calls
                   # MakeConflicts, then RegAlloc); cn after fb (RegAlloc
                   # retry rebuilds) appends directly.
            ir_buf = []
            cn_buf = []
            bo_buf = []
            br_buf = []
            ni_buf = []
            ob_buf = []
            oh_buf = []
            nb1_buf = []
            nb2_buf = []
            nb_buf = []
            nf_buf = []
            il_walk_buf = []
            _ixp_buf.clear()
            bb_pending = None
            routines.append(cur); pending = None
            expect_terminal_fc = True
        elif tag == "fc":
            # Generate just returned.  This is routine K's terminal `fc` only
            # when fb[K] has fired (expect_terminal_fc was armed).  Interim
            # `fc` events (between statements, or before the first routine
            # for compiler init) are recorded but do NOT close the routine.
            if expect_terminal_fc and cur is not None:
                _finalize_routine(cur)
                cur = None
                expect_terminal_fc = False
                pending = None
        elif tag == "fn" and cur is not None:   # regalloc phase (only non-trivial)
            cur["has_regalloc"] = True
        elif tag == "sl" and cur is not None:
            # Multi-round AssignConflicts (OW v1 regalloc.c:1314).  Each
            # RegAlloc outer-loop iteration calls AssignConflicts which calls
            # SortConflicts -> SortList (one `sl` stream + one `sa` head
            # dump).  We split rounds at the boundary `sa` -> next `sl`:
            # the FIRST `sl` after any `sa` opens a new round.  Round index
            # is recorded on every sl/sa/al entry so reproduce_order_per_round
            # can validate the ShellSort model per-round.  See
            # docs/mechanism-survey-2026-06-25.md (Mechanism A).
            if cur.get("_round_open_sa"):
                cur["_round_idx"] = cur.get("_round_idx", 0) + 1
                cur["_round_open_sa"] = False
            cur["presort"].append({"node": f[2], "savings": int(f[3]),
                                   "round": cur.get("_round_idx", 0)})
        elif tag == "sa" and cur is not None:
            cur["_round_open_sa"] = True
            cur["postsort"].append({"node": f[2], "savings": int(f[3]),
                                    "round": cur.get("_round_idx", 0)})
        elif tag == "nt" and cur is not None and len(f) >= 6:
            # Names[N_TEMP] PRE-sort head at AssignTemps' SortList call.
            # fields: ptr, conflict_ptr (often 0 at AssignTemps time), size,
            # usage byte (NEEDS_MEMORY=0x80, USE_MEMORY=0x10, USE_IN_OTHER=0x2),
            # flag dword (low byte = +0x28..+0x2b flags, bit 2/byte3=0x2 USED_AS_FD,
            # byte3 bit 0x1=CONST_TEMP).  See AllocBefore @0x5905b and
            # TempAllocBefore @0x55503.  This is THE input to the size sort --
            # the rover/regalloc residue order.
            cur.setdefault("nt_pre", []).append({
                "name": f[2], "conf": f[3], "size": int(f[4], 16),
                "usage": int(f[5], 16),
                "flags": int(f[6], 16) if len(f) > 6 else 0,
                "off10": int(f[7], 16) if len(f) > 7 else 0,
                "loc24": int(f[8], 16) if len(f) > 8 else 0,
            })
        elif tag == "na" and cur is not None and len(f) >= 6:
            # Names[N_TEMP] POST-sort head -- the order AllocNewLocal /
            # SetTempLocation iterates.  The NEEDS_MEMORY (usage&0x80)
            # subsequence of THIS is the SLOT ORDER (slot[i] == ith
            # NEEDS_MEMORY temp here).  Direct ground truth for Rule 107.
            cur.setdefault("nt_post", []).append({
                "name": f[2], "conf": f[3], "size": int(f[4], 16),
                "usage": int(f[5], 16),
                "flags": int(f[6], 16) if len(f) > 6 else 0,
                "off10": int(f[7], 16) if len(f) > 7 else 0,
                "loc24": int(f[8], 16) if len(f) > 8 else 0,
            })
        elif tag == "bb" and len(f) >= 3:
            # BlockByBlock value at MakeConflicts entry.  1 = the
            # BuildNameConflicts savings sort is SKIPPED -- expect nb1/nb2
            # to be empty for this routine; the Names[N_TEMP] order at
            # AssignTemps time depends on per-block name list mutations
            # rather than a global savings sort.  0 = full pipeline, nb1
            # has the pre-sort order.  MakeConflicts fires BEFORE the
            # routine's `fb` marker (RegAlloc entry), so we buffer here
            # and attach on the next `fb`.
            bb_pending = int(f[2])
        elif tag == "rr" and len(f) >= 3:
            # allocation-ROUND snapshot header (image >= 2026-07-10i): a
            # bs/be/iv walk follows.  edge = the RegAlloc edge that fired
            # (0 = round-0 entry 0x584b9 -- the vintage every certified
            # consumer uses via il_walks[0]; 1 = AssignConflicts!=1
            # loop-back; 2 = MoreConflicts full-rebuild loop-back, i.e.
            # post MakeLiveInfo+AxeDeadCode; 3 = LiveInfoUpdate
            # loop-back).  Round index == walk ordinal.  Rounds >= 1
            # carry the previous round's FixInstructions rewrites +
            # refreshed live sets: the round>0/pos-miss savings-gap
            # substrate (P1) and the between-round IL ground truth a
            # FixInstructions port certifies against (P5).
            _walks = cur["il_walks"] if cur is not None else il_walk_buf
            _walks.append({"edge": int(f[2], 16), "blocks": []})
        elif tag == "bs" and len(f) >= 10:
            # full-IL snapshot BLOCK row (image >= 2026-07-10d: RegAlloc
            # 0x584b9, post-MakeLiveInfo/AxeDeadCode -- streams AFTER fb
            # into the open routine; since image 2026-07-10i one walk per
            # ROUND, each opened by an rr header).  The block
            # struct doubles as the 0x4b pseudo-ins, so the live fields
            # are the BLOCK-BOUNDARY live sets.  A new walk opens lazily
            # when the incoming blk already appears in the current walk
            # (wrap detection -- the pre-rr-image fallback; rr-opened
            # walks never trip it: a fresh walk starts empty).
            _walks = cur["il_walks"] if cur is not None else il_walk_buf
            _w = _walks[-1] if _walks else None
            if _w is None or any(b["blk"] == f[2] for b in _w["blocks"]):
                _w = {"blocks": []}
                _walks.append(_w)
            _w["blocks"].append({
                "blk": f[2], "targets": int(f[3], 16),
                "live_regs": int(f[4], 16),
                "live_out": [int(x, 16) for x in f[5:9]],
                "live_within": int(f[9], 16),
                "edges": [], "ins": []})
        elif tag == "be" and len(f) >= 4:
            # successor edge of the current snapshot block (the FLOW GRAPH).
            _walks = cur["il_walks"] if cur is not None else il_walk_buf
            if _walks and _walks[-1]["blocks"]:
                _walks[-1]["blocks"][-1]["edges"].append(f[3])
        elif tag == "xtp" and len(f) >= 6:
            # NON-REGISTER TAIL operand (operands[2..N-1] = call parms):
            # raw name ptr + class|flags<<8 + N_INDEXED index ptr (0
            # unless class 4).  A temp parm f(show_map_fn) is a use_save
            # ref, an indexed parm f(table[t]) an index_save ref -- both
            # invisible in op0/op1/xtra_regs.  Emitted BEFORE its ins's
            # iv row (image >= 2026-07-10g; supersedes the short-lived
            # ixp record).  Buffered per ins ptr, attached as xtra_ops.
            _ixp_buf.setdefault(f[2], []).append(
                {"name": int(f[3], 16), "meta": int(f[4], 16),
                 "idx": int(f[5], 16)})
        elif tag == "iv" and len(f) >= 17:
            # full-IL snapshot INS row: pre-allocation liveness baseline.
            _walks = cur["il_walks"] if cur is not None else il_walk_buf
            if _walks and _walks[-1]["blocks"]:
                _walks[-1]["blocks"][-1]["ins"].append({
                    "ins": f[2], "opcode": int(f[3], 16),
                    "result": int(f[4], 16), "op0": int(f[5], 16),
                    "op1": int(f[6], 16),
                    "res_meta": int(f[7], 16), "op0_meta": int(f[8], 16),
                    "op1_meta": int(f[9], 16),
                    "live_regs": int(f[10], 16),
                    "live_out": [int(x, 16) for x in f[11:15]],
                    "live_within": int(f[15], 16),
                    "zap_reg": int(f[16], 16),
                    # image >= 2026-07-10e: DIRECT hw_reg_set capture (no
                    # regmap join; register-PAIR names included) + the
                    # OR-fold of operands[2..N-1] (CALL parm registers).
                    "res_reg": int(f[17], 16) if len(f) >= 21 else None,
                    "op0_reg": int(f[18], 16) if len(f) >= 21 else None,
                    "op1_reg": int(f[19], 16) if len(f) >= 21 else None,
                    "xtra_regs": int(f[20], 16) if len(f) >= 21 else None,
                    # image >= 2026-07-10f: N_INDEXED index ptrs (the
                    # name's +0xc, 0 for non-indexed names) -- the
                    # CalcSavings _ReplaceIdx* substrate (savings.py).
                    "res_idx": int(f[21], 16) if len(f) >= 24 else None,
                    "op0_idx": int(f[22], 16) if len(f) >= 24 else None,
                    "op1_idx": int(f[23], 16) if len(f) >= 24 else None,
                    # image >= 2026-07-10h: TooGreedy per-ins context,
                    # packed (num_operands<<16)|(t.index_needs<<8)|
                    # (gen_table->reg_set; 0 = NULL gen_table = RL_).
                    "tg_ctx": int(f[24], 16) if len(f) >= 25 else None,
                    "xtra_ops": _ixp_buf.pop(f[2], None)})
        elif tag == "nbb" and len(f) >= 3:
            # BGNewTemp ENTRY: the OUTER creator RA (FlowOut / BGGlobalTemp /
            # a specific burn helper) for the following nbc+nb pair.
            _nb_outer_pending = f[2]
        elif tag in ("nbc", "nbo") and len(f) >= 4:
            # SAllocTemp (nbc) / STempOffset (nbo) ENTRY: the PASS attribution
            # for the next `nb` class==2 record (stream-order join).  f[2] =
            # direct caller RA (runtime), f[3] = [esp+8] = grandcaller through
            # the thin AllocTemp/TempOffset wrappers.  Stashed and consumed by
            # the next nb record below.  f[4] (image >= 2026-07-10g) = entry
            # EAX: for nbo the BASE name ptr (the alias-ring edge -- OW
            # namelist.c STempOffset inserts the new alias into base's ring;
            # transitive base edges reach the DeAlias master); for nbc the
            # class dword (ignored).
            _nb_pass_pending = {"kind": tag, "caller": f[2], "caller2": f[3],
                                "base": (f[4] if tag == "nbo"
                                         and len(f) >= 5 else None)}
        elif tag == "nb" and len(f) >= 6:
            # AllocName exit -- per-class name birth (see patch_trace.py
            # 'AllocName' hook).  class: 0=N_CONSTANT, 1=N_MEMORY, 2=N_TEMP,
            # 3=N_REGISTER, 4=N_INDEXED, ...  `line` is the FE SrcLine at
            # the birth -- the statement attribution for the name.  Emission
            # order is the CREATION order; Names[class] is built by PREPEND,
            # so the list order later seen by BuildNameConflicts (nb1) is
            # reversed(creation) filtered to survivors (AllocFrl recycles
            # freed name structs -- ptr identity is only valid between
            # consecutive births of the same ptr).
            rec_nb = {"name": f[2], "class": int(f[3]), "subclass": int(f[4]),
                      "name_id": f[5], "seq": seq,
                      "line": int(f[6]) if len(f) > 6 else 0,
                      # trailing %x (>= 2026-07-09 push_caller image): the
                      # CALLER return address inside wcc386 -- the PASS that
                      # created this name (FE burn / CSE / bldins / loopopts /
                      # makeaddr / bldcall ...).  The L0 anon births that
                      # populate the Rule 107 flip windows are attributable
                      # ONLY through this field.
                      "caller": f[7] if len(f) > 7 else None}
            if rec_nb["class"] == 2 and _nb_pass_pending is not None:
                rec_nb["pass_kind"] = _nb_pass_pending["kind"]      # nbc=SAllocTemp, nbo=STempOffset(alias)
                rec_nb["pass_caller"] = _nb_pass_pending["caller"]   # RA into the creating pass
                rec_nb["pass_caller2"] = _nb_pass_pending["caller2"] # grandcaller (thin-wrapper hop)
                if _nb_pass_pending.get("base"):
                    rec_nb["alias_base"] = _nb_pass_pending["base"]  # nbo: ring-edge base name
                _nb_pass_pending = None
                if _nb_outer_pending is not None:
                    rec_nb["pass_outer"] = _nb_outer_pending  # BGNewTemp's caller (nbb)
                    _nb_outer_pending = None
            (nb_buf if cur is None else cur.setdefault("nb", [])).append(rec_nb)
        elif tag == "nf" and len(f) >= 4:
            # FreeName ENTRY (0x3a24e) -- name DEATH, the nb complement
            # (image >= 2026-07-10j).  f[2]=name ptr (recyclable; join the
            # ptr's most recent nb record chronologically for class +
            # attribution), f[3]=caller RA = the CULLING pass.  Motivation:
            # Rule 107 insert-window construct screening (a coalesced user
            # temp births then dies invisibly; nf names the killer so
            # tempbirths/spell can screen constructs for SURVIVAL).
            rec_nf = {"name": f[2], "caller": f[3], "seq": seq}
            (nf_buf if cur is None else cur.setdefault("nf", [])).append(rec_nf)
        elif tag == "nb1" and len(f) >= 6:
            # Names[N_TEMP] PRE-sort at BuildNameConflicts end (the SECOND
            # SortList call in the pipeline -- chronologically EARLIER than
            # AssignTemps' nt/na hooks).  The comparator at va 0x5905b
            # ("AllocBefore equivalent") sorts by CONST_TEMP flag bit, then
            # has-conflict before no-conflict, then savings DESC.
            # BuildNameConflicts fires BEFORE the routine's `fb` marker, so
            # we buffer and attach at the next `fb`.
            # `sort_sav` = savings AT sort time via deref through name.conflict
            # (= `name->v.conflict->savings`); 0 when name has no conflict.
            # This is what AllocBefore actually saw -- typically lower than
            # the al-record savings (which include later CalcSavings refinement
            # in AssignConflicts).
            rec_nb1 = {"name": f[2], "conf": f[3], "size": int(f[4], 16),
                       "usage": int(f[5], 16),
                       "flags": int(f[6], 16) if len(f) > 6 else 0,
                       "loc24": int(f[7], 16) if len(f) > 7 else 0,
                       "off10": int(f[8], 16) if len(f) > 8 else 0,
                       "sort_sav": int(f[9]) if len(f) > 9 and f[9] not in ("None","") else None}
            (nb1_buf if cur is None else cur.setdefault("nb1", [])).append(rec_nb1)
        elif tag == "nb2" and len(f) >= 6:
            # Names[N_TEMP] POST-sort at BuildNameConflicts end.
            rec_nb2 = {"name": f[2], "conf": f[3], "size": int(f[4], 16),
                       "usage": int(f[5], 16),
                       "flags": int(f[6], 16) if len(f) > 6 else 0,
                       "loc24": int(f[7], 16) if len(f) > 7 else 0,
                       "off10": int(f[8], 16) if len(f) > 8 else 0,
                       "sort_sav": int(f[9]) if len(f) > 9 and f[9] not in ("None","") else None}
            (nb2_buf if cur is None else cur.setdefault("nb2", [])).append(rec_nb2)
        elif tag == "an" and cur is not None and len(f) >= 5:
            # AllocNewLocal entry: per-iteration in AssignTemps' body loop
            # that passed the AllocNewLocal gate.  Each `an` precedes either
            # an `st` (fresh slot) or no `st` (ReUsableStack-coalesced into
            # an existing slot).  Pairing `an` with `st` gives the exact
            # subset of nt_post that becomes a SLOT -- the missing piece
            # for strict prediction of slot order.
            cur.setdefault("an", []).append({
                "name": f[2], "size": int(f[3]),
                "usage": int(f[4], 16),
                "flags": int(f[5], 16) if len(f) > 5 else 0,
            })
        elif tag == "rl" and cur is not None:
            # RetList length at each OptPush ComTail call -- how many ret
            # sites were candidates for the per-ret tail merge.
            cur["retlists"].append(int(f[2]))
        elif tag == "cm" and cur is not None:
            # ComTail's finalized decision: save = best common return-tail
            # byte count among the RetList candidates (0 = no merge; the
            # gate is save > 5).  Fires once per ComTail invocation from ANY
            # call site; `rl` fires only at the OptPush call site (retcount
            # wrap), so the rl positionally closes the cm run that preceded
            # it.  The Rule 15/42 observable: WHICH ret tails the compiler
            # considered merging and what each merge saved.
            #
            # raw20 = the word at max-candidate+0x20.  CORPUS-GROUNDED
            # (c2 trace-census, 11k records): NOT a source line -- the value
            # distribution is a handful of constants (0x100, 0x201, 0x205,
            # 0x600, 0xA06...), i.e. an oc_entry header word (class/objlen
            # pair).  The hook was designed as `ins_line` from one probe;
            # keep the raw word until the field is RE-grounded in the
            # 10.0a binary.  Do NOT join it against source lines.
            cur["comtail"].append({"save": int(f[2]), "raw20": int(f[3])})
        elif tag == "cv" and cur is not None:
            cur["savecalc"].setdefault(f[2], []).append(
                {"blk": f[3], "save": int(f[4]), "cost": int(f[5]),
                 "depth": int(f[6])})
        elif tag == "al" and cur is not None:
            rc = int(f[5], 16)
            nc = int(f[8], 16) if len(f) > 8 else None
            a = {"conf": f[2], "name": f[3], "savings": int(f[4]),
                 "regclass": rc, "regclass_name": REG_CLASS.get(rc, hex(rc)),
                 "first": f[6], "last": f[7],
                 "nameclass": nc, "nameclass_name": NAME_CLASS.get(nc) if nc is not None else None,
                 "defline": int(f[9]) if len(f) > 9 else None,
                 # image >= 2026-07-10h: conf flags byte (+0x55) --
                 # 0x9 = INDEX_SPLIT|SEGMENT_SPLIT, 0x80 = NEVER_TOO_GREEDY
                 "conf_flags": int(f[10], 16) if len(f) > 10 else None,
                 "reg": None, "reg_name": None, "var": None,
                 "tree_cands": None, "_birth_seq": cur["_seq"],
                 "round": cur.get("_round_idx", 0),
                 # v50: the il_walks index CURRENT at presentation time --
                 # the walk vintage this row's TooGreedy actually
                 # consumed.  STREAM-ORDER join, robust where the round
                 # ordinal desyncs from the walk ordinal (a trip that
                 # presents zero conflicts emits no sl burst, so
                 # _round_idx does not bump but a walk still fired --
                 # observed: get_range1's 3 walks / 2 rounds).
                 "walk_idx": max(0, len(cur["il_walks"]) - 1),
                 # v52: the conf's most-recent cn BIRTH walk vintage AT
                 # THIS POINT IN THE STREAM (order-respecting join --
                 # conf ptrs are free-list REUSED, so a global
                 # last-birth-wins map misjoins round-0 rows).  Savings
                 # are computed at creation and CARRIED to presentation;
                 # savings.py joins this field.
                 "birth_walk_idx": cur.get("_conf_birth_walk", {}).get(f[2], 0)}
            cur["alloc"].append(a); pending = a
        elif tag == "nm" and cur is not None and len(f) >= 4:
            # source variable name for the just-emitted al (al -> nm chain);
            # resolved in-compiler via SymGetPtr (patch_trace nm hook).
            tgt = (pending if pending is not None and pending["conf"] == f[2]
                   else next((a for a in reversed(cur["alloc"])
                              if a["conf"] == f[2]), None))
            if tgt is not None:
                tgt["var"] = f[3]
        elif tag == "bt" and cur is not None and len(f) >= 13:
            # GiveBestReg entry: the conflict's REAL candidate list
            # (tree->regs after BuildRegTree/MarkPossible narrowing; first 8
            # entries of the 0-terminated array).  The first bt after a
            # conflict's `al` is its top-level tree -- attach to that row.
            # Subsequent bt records for the same conf (hi/lo recursion,
            # RegAlloc retries) are ignored once tree_cands is set.
            masks = []
            for tok in f[5:13]:
                v = int(tok, 16)
                if v == 0:
                    break
                masks.append(v)
            _btrec = {"seq": cur["_seq"],
                      "tree_cands": [REG_NAME.get(m, hex(m)) for m in masks]}
            if len(f) >= 16:
                _btrec["conf_state"] = int(f[13], 16)
                _btrec["id_within"] = int(f[14], 16)
                _btrec["id_out"] = int(f[15], 16)
            if len(f) >= 17:
                _btrec["given_regs"] = int(f[16], 16)
            cur["_bt_all"].setdefault(f[2], []).append(_btrec)
            tgt = (pending if pending is not None and pending["conf"] == f[2]
                   else next((a for a in reversed(cur["alloc"])
                              if a["conf"] == f[2]), None))
            if tgt is not None and tgt.get("tree_cands") is None:
                tgt["tree_cands"] = [REG_NAME.get(m, hex(m)) for m in masks]
                # state/id-bit extension (image >= 2026-06-10): bit2 of
                # state = CONFLICT_ON_HOLD; id_out|id_within both EMPTY =
                # NeighboursUse treats the conflict as live over its WHOLE
                # LINEAR range (al-squat suspect).  First sighting sticks.
                if len(f) >= 16:
                    tgt["conf_state"] = int(f[13], 16)
                    tgt["on_hold"] = bool(int(f[13], 16) & 4)
                    # FIELD ORDER (corrected 2026-06-10, OW v1 conflict.h:
                    # within FIRST): f[14] = conf+0x40 = id.WITHIN_BLOCK
                    # (local_bit_set, 32 bits/block), f[15] = OR-fold of
                    # conf+0x44..0x50 = id.OUT_OF_BLOCK (global_bit_set,
                    # 128-bit pool).  id_bits = (within, out).
                    tgt["id_bits"] = (int(f[14], 16), int(f[15], 16))
                    tgt["id_within"] = int(f[14], 16)
                    tgt["id_out"] = int(f[15], 16)
                    tgt["no_id_bits"] = (int(f[14], 16) | int(f[15], 16)) == 0
                # given: GivenRegisters @ 0x7f884 read at GiveBestReg ENTRY
                # (the running set of all hw_reg_sets already committed via
                # FixInstructions inside this routine).  The ConfBefore
                # tie-break key (HW_Subset(GivenRegisters, reg)).  Packed
                # word 0 | word 1 << 16 (same encoding as the candidate
                # masks).  Available from image >= 2026-06-11.
                if len(f) >= 17:
                    tgt["given_regs"] = int(f[16], 16)
        elif tag == "gb" and cur is not None and len(f) >= 5:
            # GiveBestReg per-candidate score: one record per candidate that
            # survived with.regs/except/TooGreedy, with its CountRegMoves
            # saves.  Pick = argmax saves; tie -> first candidate already
            # subset of GivenRegisters; else list order.  Attach the FIRST
            # gb sweep after a conflict's al to that row (like bt); also
            # keep the raw stream for multi-pass analysis.
            v = int(f[3], 16)
            sv = int(f[4], 16)
            if sv > 0x7fffffff:
                sv -= 0x100000000          # CountRegMoves is signed
            entry = {"cand": REG_NAME.get(v, hex(v)), "saves": sv}
            cur.setdefault("gb", []).append({"conf": f[2], **entry})
            cur["_gb_all"].setdefault(f[2], []).append(
                {"seq": cur["_seq"], **entry})
            tgt = (pending if pending is not None and pending["conf"] == f[2]
                   else next((a for a in reversed(cur["alloc"])
                              if a["conf"] == f[2]), None))
            if tgt is not None:
                sc = tgt.setdefault("cand_scores", [])
                if not any(e["cand"] == entry["cand"] for e in sc):
                    sc.append(entry)
        elif tag == "ce" and cur is not None and len(f) >= 8:
            # CountRegMoves ENTRY (image >= 2026-07-10): conf, candidate
            # hw_reg_set, conf->tree, tree->temp, tree->alt, tree->size.
            # {temp, alt} is the VALUE SET the credit loop matches operands
            # against (the alias-ring ground truth crm10a lacked); size is
            # the credit unit (full=size, half=size>>1).  tree==0 (early
            # return 0) records zero fields.  One record per (conf, cand)
            # scoring call; keep the per-conf stream for window scoping.
            cur["_ce_all"].setdefault(f[2], []).append({
                "seq": cur["_seq"], "cand_mask": int(f[3], 16),
                "tree": f[4], "temp": f[5], "alt": f[6],
                "size": int(f[7], 16)})
        elif tag == "cq" and cur is not None and len(f) >= 6:
            # CountRegMoves credit EVENT (loop-tail hook, edi-delta dedup):
            # conf, candidate regs, the ins that just credited, the running
            # total AFTER the add.  The walk is the compiler's own range
            # traversal (opcode-0x4b block hops included -- unlike gi's
            # naive +4 walk).  The ce entry hook ZEROES the dedup slot per
            # call (image >= 2026-07-10b), so the stream is PURE credit
            # events; a total DROP between consecutive events of one conf
            # marks a new scoring call (edi restarts at 0).
            v = int(f[3], 16)
            cur["_cm_all"].setdefault(f[2], []).append({
                "seq": cur["_seq"], "cand": REG_NAME.get(v, hex(v)),
                "cand_mask": v, "ins": f[4], "total": int(f[5], 16)})
        elif tag == "tg" and cur is not None and len(f) >= 5:
            # TooGreedy verdict per candidate (verdict!=0 = veto).  With gb:
            # bt-minus-gb candidates split into tg-vetoed vs mask-skipped
            # (with.regs/except -- no tg record at all).
            if int(f[4], 16) != 0:
                v = int(f[3], 16)
                nm = REG_NAME.get(v, hex(v))
                cur["_tg_all"].setdefault(f[2], []).append(
                    {"seq": cur["_seq"], "reg": nm})
                tgt = (pending if pending is not None and pending["conf"] == f[2]
                       else next((a for a in reversed(cur["alloc"])
                                  if a["conf"] == f[2]), None))
                if tgt is not None:
                    vetoes = tgt.setdefault("tg_veto", [])
                    if nm not in vetoes:
                        vetoes.append(nm)
        elif tag == "wp" and cur is not None and len(f) >= 4:
            # WorthProlog verdict (patch_trace wp @0x401e9; no conf field):
            # budget (savings term, ECX) vs prologue cost (ESI) for the
            # candidate that won the gb argmax of the OPEN presentation.
            # budget < cost => the winner is DECLINED and the conflict is
            # homed to MEMORY with no rg commit (W107 retval-funnel class,
            # Rule 136).  Scoped to the row by birth window in
            # _finalize_routine (same per-owner semantics as bt/gb/tg).
            _budget = int(f[2], 16)
            _cost = int(f[3], 16)
            cur["_wp_all"].append({"seq": cur["_seq"], "budget": _budget,
                                   "cost": _cost,
                                   "ok": _budget >= _cost})
        elif tag == "wr" and cur is not None:
            # Per-presentation sighting log (2026-06-13): the conflict is
            # re-presented across RegAlloc passes (spill rounds); the
            # presentation that matters is the one the COMMIT (rg) closes.
            # _finalize_routine re-attaches the last sighting before each
            # row's commit seq.  The legacy first-sighting fields below are
            # kept as the fallback for never-committed rows.
            _sight = {"seq": cur["_seq"], "mask": int(f[3], 16),
                      "rng": (f[4], f[5]) if len(f) >= 6 else None,
                      "graph": None}
            # trailing usage extension (image >= 2026-07-10c):
            # conf->name->v.usage; bit 0x88 = NEEDS_MEMORY|USE_ADDRESS
            # (the NeighboursUse live-across gate), USE_IN_ANOTHER_BLOCK
            # feeds NowAlive/NowDead channel selection.
            if len(f) >= 17:
                _sight["usage"] = int(f[16], 16)
            if len(f) >= 16:
                _sight["graph"] = {
                    "with_out": [int(x, 16) for x in f[6:10]],
                    "with_within": int(f[10], 16),
                    "id_within": int(f[11], 16),
                    "id_out": [int(x, 16) for x in f[12:16]],
                }
            cur["_wr_all"].setdefault(f[2], []).append(_sight)
            if f[2] not in cur["_wr"]:
                cur["_wr"][f[2]] = int(f[3], 16)
            # ins_range.first/last (trace image >= the rng extension); the
            # FIRST sighting is decision-time, same as the mask.
            if len(f) >= 6 and f[2] not in cur["_rng"]:
                cur["_rng"][f[2]] = (f[4], f[5])
            # conflict-graph extension (trace image >= 2026-06-12):
            # wo0..3 wwi (with.out/within = NeighboursUse-fresh neighbor id
            # bitsets, INCLUDING self bits) + idw io0..3 (own id bits in
            # full).  FIRST sighting, like the mask.
            if len(f) >= 16 and f[2] not in cur["_graph"]:
                cur["_graph"][f[2]] = {
                    "with_out": [int(x, 16) for x in f[6:10]],
                    "with_within": int(f[10], 16),
                    "id_within": int(f[11], 16),
                    "id_out": [int(x, 16) for x in f[12:16]],
                }
        elif tag == "gi" and cur is not None:
            _g = {
                "opcode": int(f[3], 16), "result": int(f[4], 16), "result_reg": int(f[5], 16),
                "op0": int(f[6], 16), "op0_reg": int(f[7], 16),
                "op1": int(f[8], 16), "op1_reg": int(f[9], 16)}
            # trailing extension (image >= 2026-07-10b): the ins PTR (joins
            # cq credit events + the ir forest) and the NeighboursUse
            # inputs stored on the ins -- live.regs, live.out_of_block[4],
            # live.within_block, zap->reg (NeighboursUse@0x580c0 substrate
            # for the offline no_conflict / with.regs port).
            if len(f) >= 18:
                _g["ins"] = f[10]
                _g["live_regs"] = int(f[11], 16)
                _g["live_out"] = [int(x, 16) for x in f[12:16]]
                _g["live_within"] = int(f[16], 16)
                _g["zap_reg"] = int(f[17], 16)
            if len(f) >= 20:
                # class(+4) | temp_flags(+0x2a)<<8 for result / op0 -- the
                # 0x57670 MOV-credit predicate inputs (N_TEMP && flags&8).
                _g["res_meta"] = int(f[18], 16)
                _g["op0_meta"] = int(f[19], 16)
            if len(f) >= 21:
                # image >= 2026-07-10h: TooGreedy per-ins context at
                # ALLOCATION vintage -- (num_operands<<16)|
                # (t.index_needs<<8)|gen_table->reg_set.  FixGenEntry
                # re-selects gen rows during allocation, so the
                # RegAlloc-entry iv snapshot's reg_set can be stale.
                _g["tg_ctx"] = int(f[20], 16)
            cur["_gi"].setdefault(f[2], []).append(_g)
            # per-presentation walk (2026-07-10b): the gi burst follows ITS
            # al record (the al/nm/gi chain fires at allocation time), so
            # attaching to the OPEN pending row segments the concatenated
            # per-conf-ptr stream exactly -- free-list reuse and
            # re-presentation both poison the legacy _gi join.
            if pending is not None and pending["conf"] == f[2]:
                pending.setdefault("own_walk", []).append(_g)
        elif tag == "st" and cur is not None and len(f) >= 4:
            # SetTempLocation: per-temp slot allocation, in walk order.  The
            # emission ORDER = the AssignTemps post-sort walk = the SLOT INDEX.
            # `pre_size` is CurrProc->locals.size BEFORE this call's increment;
            # `base` is CurrProc->locals.base.  The temp's actual stack location
            # is -(pre_size + size + base) -- the ground-truth slot offset.
            cur["slots"].append({
                "name": f[2], "size": int(f[3]),
                "pre_size": int(f[4]) if len(f) > 4 else None,
                "base": int(f[5]) if len(f) > 5 else None,
            })
        elif tag == "bk" and cur is not None:
            # LdStAlloc entered a block (walk order = block-list order).
            cur["ldst_blocks"].append(f[2])
        elif tag == "ni" and len(f) >= 5:
            # NewIns exit: IL-instruction BIRTH (ptr, nops, SrcLine at birth;
            # opcode is filled by the MakeXxx caller AFTER NewIns, so it is
            # NOT here -- join to lw/ge by ptr for the opcode).  Emission
            # order == the tree-burn IL EMISSION order: the finest-grained
            # witness of the burn (the layer below bo's block births).
            # Consumed by lwalk.il_birth_compare -- the kind-flip-free /
            # IL-birth residue class's screener (take_census, top_it).
            rec = {"ins": f[2], "nops": int(f[3]), "line": int(f[4])}
            if cur is None:
                ni_buf.append(rec)
            else:
                cur["il_born"].append(rec)
        elif tag == "bo" and len(f) >= 6:
            # Block BIRTH (GenBlock link; 2026-07-09): the front end just
            # completed CurrBlock and appended it to the HeadBlock chain.
            # Emission order == chain order at birth == tree-burn generation
            # order -- the PROVENANCE of the bk walk (bo\bk divergence =
            # optimizer restructure; bk pointers with NO bo = opt-born
            # blocks, e.g. blktrim merge products).  line is blk+0x20 (the
            # -d1 mark EnLink stamped at block OPEN; usually 0 -- line
            # marks are consumed by AddIns, so attribute lines via the
            # lw/fr streams grouped by bk instead).  Fires in the FE burn,
            # BEFORE the routine's fb: buffered like cn.
            rec = {"blk": f[2], "line": int(f[3]),
                   "class": int(f[4], 16), "targets": int(f[5])}
            if cur is None:
                bo_buf.append(rec)
            else:
                cur["blocks_born"].append(rec)
        elif tag == "br" and len(f) >= 5:
            # Post-MakeFlowGraph block-chain snapshot (>= 2026-07-13 image):
            # one row per block IN CHAIN ORDER right after MakeFlowGraph
            # (DFS/RPO relink + ReorderBlocks + ReturnsToBottom).  class
            # bit0 = RETURN (the ReturnsToBottom haul predicate).  The
            # middle chain vintage: bo (FE birth) -> br (post-MFG) -> bk
            # (LdStAlloc walk).  A block whose position diverges bo->br
            # was moved by the pre-conflicts optimizer / MFG; one
            # diverging br->bk by a later pass.  Fires pre-fb (Generate's
            # pass window runs before RegAlloc): buffered like bo.
            rec = {"blk": f[2], "line": int(f[3]), "class": int(f[4], 16),
                   "edges": []}
            if cur is None:
                br_buf.append(rec)
            else:
                cur["chain_post_mfg"].append(rec)
        elif tag == "bre" and len(f) >= 4:
            # Edge row of the immediately-preceding br block (>= 2026-07-13b
            # image): dest ptrs in EDGE-ARRAY ORDER -- the exact order
            # MarkVisited's DFS consumed them.  br + bre = chain AND flow
            # graph at one vintage: the offline chain model's input
            # (c2.regalloc.rover.predict_chain) and certification target.
            tgt_list = br_buf if cur is None else cur["chain_post_mfg"]
            if tgt_list and tgt_list[-1]["blk"] == f[2]:
                tgt_list[-1]["edges"].append(f[3])
        elif tag == "bor" and len(f) >= 4:
            # Block REBIND (ReGenBlock; 2026-07-09): `old` was reallocated
            # (extra edge slot) and continues as pointer `new` at the SAME
            # chain position.  Consumers matching bo->bk by pointer must
            # apply these.
            rec = {"old": f[2], "new": f[3]}
            tgt = bo_buf if cur is None else cur["blocks_born"]
            for b in tgt:
                if b["blk"] == rec["old"]:
                    b["blk"] = rec["new"]
                    b.setdefault("rebound_from", []).append(rec["old"])
        elif tag in ("lcx0", "lcx1", "lcx2", "lcx3", "lcx4", "lcx5") and cur is not None:
            # LdStCompress REJECTION (2026-07-09): the failure-side
            # complement of `lc`.  lcx1 = result-mov reg in next ins's zap;
            # lcx2 = load reg interferes with a sibling N_REGISTER operand;
            # lcx3 = load reg zapped by next ins; lcx4 = ChangeIns encoding
            # refusal.  Pair with fr/lw by ins ptr: every RISCified ins now
            # resolves to fused (lc) or a NAMED reject.  All lcx (and lc)
            # events belong to the single PostOptimize-END compress driver
            # (see the `cd` marker) -- fired over the fully-post-processed
            # IL, AFTER Score/61303/63404/54990 could perturb adjacency.
            cur.setdefault("lcx", []).append({"why": tag, "ins": f[2]})
        elif tag == "r2" and cur is not None:
            # FUN_00061303 entry (bb-gated per-loop-depth PostOptimize
            # pass; NOT the compress -- kept as a BlockByBlock witness).
            cur["loopdepth_ran"] = True
        elif tag == "r2i" and cur is not None:
            cur["loopdepth_sweeps"] = cur.get("loopdepth_sweeps", 0) + 1
        elif tag == "cw" and cur is not None and len(f) >= 8:
            # CompressIns pair-scan CONTEXT (2026-07-09): one record per
            # real compress attempt (past the was-RISCified gate).
            # prev/next = the adjacent ins in CHAIN order; prevkind/
            # nextkind = the pair-recognition kind (0..4 = a MOV half's
            # name kind, 3 = N_REGISTER = recognized; 0x1NN = not a
            # recognized MOV, NN = that ins's opcode -- 0x14b = BLOCK
            # HEADER: the halves are CHAIN-separated even if the final
            # LAYOUT is byte-adjacent, the cap_land_value kept-triple
            # hypothesis).  Join to fr/lc/lcx by ins ptr.
            cur.setdefault("cw", []).append({
                "ins": f[2], "opcode": int(f[3], 16),
                "prev": f[4], "prevkind": int(f[5], 16),
                "next": f[6], "nextkind": int(f[7], 16)})
        elif tag == "cd" and cur is not None:
            # The LdStCompress DRIVER call site (PostOptimize END,
            # 0x439e2 -> 0x62ff0; sole path to the compress worker, so
            # ALL lc/lcx in this routine are its events).  Driver gates:
            # OptForSize <= 0x32 (default 50 = boundary; -os disables
            # compression) AND cpu level >= 4.  There is NO round-1/
            # round-2 compress split -- the pair's fate is decided ONCE,
            # last, over the fully-post-processed IL (which is why lcx0
            # 'pair separated' dominates the rejects).
            cur["compress_driver"] = True
        elif tag == "dn" and cur is not None and len(f) >= 6:
            # GiveRegister DENIAL (2026-07-09): GiveBestReg returned 0 for
            # this conflict -- no register in its tree survived
            # with.regs/except/TooGreedy; the value goes to memory.  Pair
            # with al/nm (savings, name) and bt (tree candidates) to see
            # exactly which registers were contested.
            cur.setdefault("dn", []).append({
                "conf": f[2], "withregs": int(f[3], 16),
                "f54": int(f[4], 16), "f55": int(f[5], 16)})
        elif tag == "lw" and cur is not None and len(f) >= 10:
            # LdStAlloc COMPLETE per-instruction walk (call-site hook before
            # LoadStoreIns; 2026-07-09).  The candidate universe of which
            # `fr` is the RISCified subset: pair by `ins` ptr -- an lw with
            # no matching fr = the op was SKIPPED (DoesSomething gate or
            # Enregister NULL; op-kind fields show why -- all-N_REGISTER
            # operands mean the allocator bound the value).  Kinds:
            # 1=N_INDEXED 2=N_MEMORY 3=N_REGISTER 4=N_TEMP, 0xf=absent.
            # THE map for the rover influence-window fit: a skipped op in
            # an inject window is a named +1 candidate, a RISCified one a
            # -1 candidate.
            cur.setdefault("lw", []).append({
                "ins": f[2], "opcode": int(f[3], 16), "line": int(f[4]),
                "type_class": int(f[5], 16), "nops": int(f[6], 16),
                "reskind": int(f[7], 16), "op0kind": int(f[8], 16),
                "op1kind": int(f[9], 16),
                "blk": len(cur["ldst_blocks"]) - 1})
        elif tag == "fr" and cur is not None and len(f) >= 7:
            # RISCify rover (FindRegister) entry: ins, type_class, except,
            # opcode, operand0, and (newer trace images) the source line of the
            # RISCified instruction (ins->line_num) -- lets the rover trajectory
            # be mapped back to C.  The push-scratch picker -- see rover_hints.
            # "blk" indexes the bk record this fr followed (block grouping).
            _fr = {"ins": f[2], "type_class": int(f[3]),
                   "except": int(f[4], 16), "opcode": int(f[5], 16),
                   "op0": f[6],
                   "line": int(f[7]) if len(f) > 7 else None,
                   "blk": len(cur["ldst_blocks"]) - 1}
            if len(f) > 14:
                # 2026-07-11 image: result + op0 NAME IDENTITY (class byte,
                # v.symbol handle, v.offset).  (sym, off) is the site key of
                # a RISCified const store / split load -- joins every fr
                # advance (even Score-coalesced ones) to its global.
                _fr.update({"res": f[8], "rescls": int(f[9], 16),
                            "ressym": int(f[10], 16), "resoff": int(f[11], 16),
                            "op0cls": int(f[12], 16),
                            "op0sym": int(f[13], 16),
                            "op0off": int(f[14], 16)})
            if len(f) > 17:
                # 2026-07-13 image: the except-mask COMPONENTS.
                # except == zap | live | resreg (certified corpus-wide by
                # c2.regalloc.rover.certify_except).  zap is IL-static;
                # live (the live REGISTER set at the ins) and resreg (the
                # result's register when N_REGISTER) are SEATING-dependent
                # -- the substrate for counterfactual rover walks ("what
                # does the cursor pick if conflict X sits in reg R"):
                # except' = zap | live' | resreg', with live'/resreg'
                # recomputed from the certified seat chain.  See
                # c2/regalloc/rover.py.
                _fr.update({"zap": int(f[15], 16), "live": int(f[16], 16),
                            "resreg": int(f[17], 16)})
            cur["fr"].append(_fr)
        elif tag == "ct" and cur is not None and len(f) >= 7:
            # ComTail splice COMMIT (patch_trace.py hook 0x67a7b, 5 fields:
            # ins, best, old, new, save): the NEW ins's common tail [new..ins]
            # is deleted and a jmp to <old> (in the winner's copy) replaces
            # it.  KEEP-FIRST direction.  (v56 mislabeled this 5-field record
            # with a 2-field 'entry' schema -- {list,ins} were really
            # {ins,winner}; fixed v57.)
            cur.setdefault("ct", []).append({"ins": f[2], "winner": f[3],
                                             "old": f[4], "new": f[5],
                                             "save": int(f[6], 16)})
        elif tag == "ct" and cur is not None and len(f) >= 4:
            # legacy 2-field ComTail entry record (older images): candidate
            # list head + incoming ins.
            cur.setdefault("ct", []).append({"list": f[2], "ins": f[3]})
        elif tag == "ctc" and cur is not None and len(f) >= 4:
            cur.setdefault("ctc", []).append({"cand": f[2],
                                              "save": int(f[3], 16)})
        elif tag == "ctm" and cur is not None and len(f) >= 5:
            # the MAX decision (pre-JustMoveLabel; fires on every nonzero
            # max): winner = the candidate that stays canonical.
            cur.setdefault("ctm", []).append({"ins": f[2], "winner": f[3],
                                              "save": int(f[4], 16)})
        elif tag == "ctw" and cur is not None and len(f) >= 5:
            # the COMMIT: `ins` becomes a jmp into `winner` (winner stays
            # canonical/inline); save = the shared-suffix byte count.
            cur.setdefault("ctw", []).append({"ins": f[2], "winner": f[3],
                                              "save": int(f[4], 16)})
        elif tag == "frx" and cur is not None and len(f) >= 4:
            # FindRegister GROUND-TRUTH return (hook 0x62aaf, the *rover=regs
            # epilogue): rover cursor VAR (0x80714 byte / 0x80718 word /
            # 0x80710 dword) + the ACTUAL chosen register mask.  Pairs 1:1
            # with the i-th same-class fr record (rover_validate.py proved
            # sim==frx 7028/7028) -- but parsing it makes the pick DIRECTLY
            # visible, so consumers need no simulation at all.
            # rover var addr is heap-relocated under wibo; the static VAs
            # (byte 0x80714 / word 0x80718 / dword 0x80710) keep their low
            # nibble, which identifies the class.
            _rv = int(f[2], 16) & 0xF
            cur["frx"].append({
                "rover": f[2],
                "cls": {4: "byte", 8: "word", 0: "dword"}.get(_rv),
                "mask": int(f[3], 16),
                "blk": len(cur["ldst_blocks"]) - 1})
            # POSITIONAL truth pairing (2026-07-13): an frx fires at
            # FindRegister's FOUND-return, i.e. IMMEDIATELY after its own
            # fr entry record (FindRegister is not recursive; nothing
            # interleaves).  Attach the truth to the LAST fr row.  This
            # replaces the old per-class INDEX zip in _finalize_routine,
            # which silently mis-aligned every truth after a NULL-return
            # fr (except mask = all regs, e.g. 0x7fffffff -- no frx fires;
            # seen in common.c move_clock_ferret).  A NULL-return fr now
            # correctly carries NO truth.
            if cur["fr"] and "truth" not in cur["fr"][-1]:
                from c2.regalloc.reglists import REG_NAME as _RN
                _nm = _RN.get(int(f[3], 16))
                if _nm:
                    cur["fr"][-1]["truth"] = _nm.lower()
        elif tag == "rg" and cur is not None:
            # given_before = GivenRegisters at THIS pick's commit (union of
            # all prior rg picks in the routine) -- the input to the
            # GiveBestReg tie-break (Rule 124 knob 3).  Derived, no hook.
            tgt_rg = None
            if pending is not None and pending["conf"] == f[2] and pending["reg"] is None:
                tgt_rg = pending
            else:
                for a in reversed(cur["alloc"]):
                    if a["conf"] == f[2] and a["reg"] is None:
                        tgt_rg = a; break
            if tgt_rg is not None:
                tgt_rg["reg"] = f[3]; tgt_rg["reg_name"] = reg_name(f[3])
                tgt_rg["given_before"] = cur.get("_given", 0)
                tgt_rg["_commit_seq"] = cur["_seq"]
                try:
                    cur["_given"] = cur.get("_given", 0) | int(f[3], 16)
                except ValueError:
                    pass
        elif tag == "lc" and cur is not None and len(f) >= 5:
            # CompressIns merge-back COMMIT (LdStCompress): a RISCified ins
            # was CISCified back to memory form.  presult!=0 = the adjacent
            # result-store mov was absorbed; popnd!=0 = the operand-load mov.
            # fr (split attempt) + lc (merge-back) = the complete LdStAlloc
            # RISCify story: an fr'd ins with NO lc keeps the split form
            # (last-addend / acc-swap declines -- Rule 130).
            cur.setdefault("lc", []).append({
                "ins": f[2],
                "presult": f[3] != "0",
                "popnd": f[4] != "0",
            })
        elif tag == "rq" and cur is not None:
            # GiveReqdRegister commit (required-register path; parm-reg
            # table).  Same semantics as rg but NOT a GiveBestReg pick:
            # no tie-break ran.  Recorded as an alloc row with
            # source="rq" so walks show TOTAL commit coverage (rg+rq =
            # the only two FixInstructions callers in 10.0a).
            cur["alloc"].append({
                "conf": f[2], "reg": f[3], "reg_name": reg_name(f[3]),
                "source": "rq", "savings": None, "regclass": None,
                "regclass_name": None, "name": None,
            })
        elif tag == "ob" and len(f) >= 9:
            # AssignGlobalBits out-of-block id-bit assignment, in POOL
            # CONSUMPTION ORDER (RoughSortTemps rough savings sort).
            # class: 2=N_TEMP (after DeAlias), 1=N_MEMORY.  bits = the
            # 128-bit global_bit_set as 4 dwords (exactly one bit set).
            rec_ob = {"conf": f[2], "name": f[3], "class": int(f[4], 16),
                      "bits": tuple(int(x, 16) for x in f[5:9])}
            (ob_buf if cur is None else cur.setdefault("ob", [])).append(rec_ob)
        elif tag == "oh" and len(f) >= 4:
            # Out-of-block bit pool EXHAUSTED -> CONFLICT_ON_HOLD (savings
            # zeroed this round; MoreConflicts re-bits next round).  Any
            # conflict here is allocation-ROUND-2+ material (gb hint's
            # [ROUND-2:] tag, Rule 124 knob 4).
            rec_oh = {"conf": f[2], "name": f[3]}
            (oh_buf if cur is None else cur.setdefault("oh", [])).append(rec_oh)
        elif tag == "il" and cur is not None:
            # `il <bytes>` -- AdvanceCode entry (= OW EjectInst).  Fires
            # once per AdvanceCode-path emit (most arith/mov/shift/cmp
            # instructions; absent for calls/branches/ret).  Appended to
            # `_cg` in trace order so the parser can interleave with `ge`.
            try:
                cur["_cg"].append(("il", int(f[2])))
            except (IndexError, ValueError):
                pass
        elif tag == "ge" and cur is not None:
            # `ge <ins> <opcode> <gen_class> <line> <result> <op0> <op1>` --
            # GenObjCode entry.  Fires once per CG INSTRUCTION, in code-
            # emission order, for EVERY user cg_ins INCLUDING calls /
            # jumps / ret (which `il` misses).  Schema:
            #   ins:      hex cg_ins ptr (matches a prior `ni`)
            #   opcode:   instruction-level cg_op (OP_MOV=0x26, OP_BLOCK=0x4b,
            #             OP_CALL/OP_JMP/etc. -- DIFFERENT enum from tn.op)
            #   gen_class: optab dispatch row (G_RC=split RMW, G_MC=in-place
            #              RMW, G_LEA, G_CALL, G_RET, etc.)
            #   line:     source line (ins->line_num set by AddIns@0x3975f)
            #   result:   result name ptr (matches an `nb`'s ptr when named)
            #   op0/op1:  operand-0 / operand-1 name ptrs
            if len(f) >= 9:
                try:
                    cur["_cg"].append(("ge", {
                        "seq":       seq,
                        "ins":       int(f[2], 16),
                        "opcode":    int(f[3]),
                        "gen_class": int(f[4]),
                        "line":      int(f[5]),
                        "result":    int(f[6], 16),
                        "op0":       int(f[7], 16),
                        "op1":       int(f[8], 16),
                    }))
                except (IndexError, ValueError):
                    pass
        elif tag == "cn" and len(f) >= 4:
            # AddConflictNode birth: conflict creation order, measured at
            # the creation site.  Fires during MakeConflicts -- i.e. BEFORE
            # the routine's fb (buffer like IR tags) -- and again during
            # RegAlloc retry rebuilds (append directly to the open routine).
            rec = {"conf": f[2], "name": f[3],
                   "class": int(f[4]) if len(f) > 4 else None}
            if cur is None:
                # MakeConflicts-era birth (pre-fb): round-0 vintage.
                rec["walk_idx"] = 0
                cn_buf.append(rec)
            else:
                # In-routine birth (MoreConflicts retry): its savings are
                # computed against the post-rewrite IL, whose snapshot is
                # the NEXT walk (the rr walk fires after MoreConflicts ->
                # MakeLiveInfo/LiveInfoUpdate, before the next trip) --
                # so walk_idx = len(il_walks) AT BIRTH, uncapped
                # (snap_index clamps on pre-rr traces).  v52.  The
                # _conf_birth_walk dict tracks the ptr's LATEST birth in
                # stream order (free-list reuse safe); al rows copy it.
                rec["walk_idx"] = len(cur["il_walks"])
                cur.setdefault("_conf_birth_walk", {})[f[2]] = rec["walk_idx"]
                cur["confs"].append(rec)
        elif tag == "op" and len(f) >= 4:
            # OptPush queue-push identity ledger.  hdr8 = dword at entry+8:
            # byte0 objlen, byte1 class|attrs (low nibble class, OW
            # ocentry.h, corpus-grounded vs the 145k-push class histogram:
            # 1=INFO, 2=CODE, 5=BDATA, 6=LABEL, 7=LREF, 8=CALL, 9=CALLI,
            # 0xa=JCOND(jcc!), 0xc=JMP, 0xd=JMPI(switch), 0xe=RET; attrs
            # 0x10=FAR, 0x20=SHORT, 0x40=POP, 0x80=FLOAT),
            # byte2 (b2) = operand length for the comparator's raw-byte
            # compare (OptCmpIns@0x678ca: full +9 AND +0xA must match, then
            # cls 6..8/0xc -> +0x10 ptr identity, JCOND/RET -> +0x14 byte
            # (the cond_no / pop word) then +0x10 ptr, else memcmp(p+8,
            # len=b2)).  w10/w14 (>= 2026-06-12b
            # image) = raw dwords at entry+0x10/+0x14: w10 is the LABEL/
            # TARGET ptr for transfer classes (the offline crossing-rule
            # predictor; joins nl/lb/cc/sc label identities) -- raw operand
            # bytes for other classes, so GATE ON cls before joining.
            h = int(f[3], 16)
            oc_events.append({"tag": "op", "seq": seq, "entry": f[2],
                              "hdr": f[3],
                              "objlen": h & 0xff,
                              "cls": (h >> 8) & 0xf,
                              "attr": (h >> 8) & 0xf0,
                              "b2": (h >> 16) & 0xff,
                              "w10": f[4] if len(f) >= 6 else None,
                              "w14": f[5] if len(f) >= 6 else None,
                              "rtn": cur["index"] if cur else None})
        elif tag == "fw" and len(f) >= 7:
            # FindCommon result per candidate: cand,ins,old,new,save.
            # save=0 = first-pair mismatch AND old/new are GARBAGE
            # (FindCommon never wrote the tmp slots) -- gate on save>0
            # before using old/new.  The comparator requires +0x10
            # label-ptr IDENTITY for transfer classes -> the walk-depth
            # bound.  fw bursts share the same `ins` (burst = one ComTail
            # invocation); max(save) over a burst = the old `cm` record,
            # burst size + 1 = the old `rl` record (both removed from the
            # image 2026-06-12b).
            oc_events.append({"tag": "fw", "seq": seq,
                              "cand": f[2], "ins": f[3],
                              "old": f[4], "new": f[5], "save": int(f[6])})
        elif tag == "ct" and len(f) >= 7:
            # ComTail SPLICE commit (keep-first; save>OptInsSize(JMP)=5).
            # Followed by nl (the merge label birth/reuse) + nj (the
            # back-jump birth) for the same splice.
            oc_events.append({"tag": "ct", "seq": seq,
                              "ins": f[2], "best": f[3],
                              "old": f[4], "new": f[5], "save": int(f[6])})
        elif tag == "jm" and len(f) >= 7:
            # JustMoveLabel commit (label relocation, no fall-in; keep-first).
            oc_events.append({"tag": "jm", "seq": seq, "label": f[2],
                              "old": f[3],
                              "new": f[4], "save": int(f[5]), "ins": f[6]})
        elif tag == "lb" and len(f) >= 4:
            oc_events.append({"tag": "lb", "seq": seq,
                              "ins": f[2], "label": f[3]})
        elif tag == "cc" and len(f) >= 4:
            oc_events.append({"tag": "cc", "seq": seq,
                              "jmp": f[2], "label": f[3]})
        elif tag == "sc" and len(f) >= 4:
            oc_events.append({"tag": "sc", "seq": seq,
                              "jmp": f[2], "label": f[3]})
        elif tag == "fq":
            # FlushAhead/OptPull drain group.  The FIRST fq is the push->
            # front-side boundary (everything after is OptPull effects).
            oc_events.append({"tag": "fq", "seq": seq})
        elif tag == "em" and len(f) >= 4:
            # EMIT ledger (>= 2026-06-12b image): one per emitted queue
            # entry, in FINAL LAYOUT ORDER, hdr8 AT EMIT TIME (objlen is
            # final, post branch-shortening -- the op-time objlen may be
            # stale).  Cumulative objlen over the em stream = object-code
            # byte offsets: THE backward join from bytes to queue entries.
            # Balance rule: op-without-em = invisibly deleted (ct/jm tails,
            # RetAftrLbl/RetAftrCal, FindShort); em-without-op = born
            # outside OptPush (nj splice jmps, nl label defines).
            h = int(f[3], 16)
            oc_events.append({"tag": "em", "seq": seq, "entry": f[2],
                              "hdr": f[3],
                              "objlen": h & 0xff,
                              "cls": (h >> 8) & 0xf,
                              "attr": (h >> 8) & 0xf0,
                              "b2": (h >> 16) & 0xff})
        elif tag == "nl" and len(f) >= 4:
            # AddNewLabel RETURN: a merge label is born OR REUSED (repeat
            # nl with the same label ptr = later splices into the same old
            # tail reuse the existing label).  ins = the class-6 label-
            # define queue entry (label+0x18).
            oc_events.append({"tag": "nl", "seq": seq,
                              "label": f[2], "ins": f[3]})
        # ---- PostOptimize Score (redundant-load coalesce) probes ----
        elif tag == "sb" and cur is not None and len(f) >= 4:
            # >= 2026-07-09 image: f[4] = the COUNTERPART ins the coalesce
            # folds into (the earlier holder of the value) -- ReplaceLoad's
            # EAX arg.  Read its reg off the lw/fr records: this names the
            # OTHER END of a Score separation (the lcx0 'pair separated'
            # cause) directly.
            cur["score_events"].append({"tag": "sb", "seq": seq,
                                         "ins": f[2],
                                         "opcode": int(f[3], 16),
                                         "into": f[4] if len(f) >= 5 else None})
        elif tag == "sbi" and cur is not None and len(f) >= 3:
            cur["score_events"].append({"tag": "sbi", "seq": seq,
                                         "ins": f[2]})
        elif tag == "sbs" and cur is not None and len(f) >= 4:
            cur["score_events"].append({"tag": "sbs", "seq": seq,
                                         "ins": f[2],
                                         "opcode": int(f[3], 16)})
        # ---- PostOptimize MergeIndex (index-fusion) probes ----
        elif tag == "mic" and cur is not None and len(f) >= 4:
            cur["mergeindex_events"].append({"tag": "mic", "seq": seq,
                                              "ins": f[2],
                                              "opcode": int(f[3], 16)})
        elif tag == "mip" and cur is not None and len(f) >= 4:
            cur["mergeindex_events"].append({"tag": "mip", "seq": seq,
                                              "ins": f[2],
                                              "opcode": int(f[3], 16)})
        elif tag == "mi" and cur is not None and len(f) >= 4:
            cur["mergeindex_events"].append({"tag": "mi", "seq": seq,
                                              "ins": f[2],
                                              "opcode": int(f[3], 16)})
        # ---- Per-clause MergeIndex rejection (always-on; cave cost absorbed
        # by the dead-code SACRIFICE in patch_trace.py) ----
        elif (tag.startswith("mir") and len(tag) == 4 and tag[3].isdigit()
              and cur is not None and len(f) >= 3):
            cur["mergeindex_events"].append({"tag": tag, "seq": seq,
                                              "ins": f[2],
                                              "clause": int(tag[3])})
        elif tag == "nj" and len(f) >= 4:
            # AddNewJump: the ComTail splice back-jump is born -- a new
            # class-0xc entry inserted after <add> targeting <label> (the
            # nl just before).  1:1 with ct.  This jmp never gets an op
            # record; it surfaces in em as the entry following <add>.
            oc_events.append({"tag": "nj", "seq": seq,
                              "add": f[2], "label": f[3]})
        elif tag in IR_TAGS:
            # IR-construction records: tn/tb/tl/nb/ni for function K are
            # emitted between fb[K-1] and fb[K] (front-end work happens BEFORE
            # back-end regalloc).  Buffer here; the buffer drains into the new
            # routine at the next fb.  Records emitted DURING regalloc (after
            # fb[K] but before fb[K+1]) belong to routine K's late inserts and
            # are appended directly to it.
            if cur is None:
                ir_buf.append((tag, f[2:]))
            else:
                cur["_ir"].append((tag, f[2:]))
    if cur is not None:
        _finalize_routine(cur)
    base = (((20 * lwt) // 256) or 1) if lwt is not None else None
    return {"cost_model": cost, "loop_time": lwt, "loop_base": base,
            "opt": opt_state, "routines": routines,
            "oc_events": oc_events}


def _finalize_routine(cur: dict) -> None:
    """Attach per-conflict with.regs + ins_walk (the GiveBestReg SELECTION
    inputs) to each alloc entry; build the IR forest from this routine's
    tn/tb/tl/nb/ni records; then drop the scratch buffers.

    The raw IR records list is moved to ``_ir_records`` so the disk cache
    can persist it -- ``IRForest`` itself has cyclic Node.left/right
    references and isn't JSON-safe; the cache rebuilds the forest on read
    via :func:`c2.regalloc._rebuild_ir`."""
    # frx GROUND-TRUTH pairing happens POSITIONALLY at parse time (see the
    # frx branch): each frx attaches to the fr record that immediately
    # preceded it in the stream.  (The historical per-class INDEX zip that
    # lived here mis-aligned every truth after a NULL-return fr -- an fr
    # whose except mask covers the whole ring gets no frx -- which poisoned
    # rover-pick certification on ~148/12k rows corpus-wide.)
    wr = cur.pop("_wr", {}); gi = cur.pop("_gi", {})
    rng = cur.pop("_rng", {})
    graph = cur.pop("_graph", {})
    wr_all = cur.pop("_wr_all", {})
    wp_all = cur.pop("_wp_all", [])
    bt_all = cur.pop("_bt_all", {})
    gb_all = cur.pop("_gb_all", {})
    tg_all = cur.pop("_tg_all", {})
    ce_all = cur.pop("_ce_all", {})
    cm_all = cur.pop("_cm_all", {})
    cur.pop("_seq", None)
    # birth order per conf ptr (free-list reuse): owner K's sighting window
    # is [birth_K, birth_{K+1}).
    births = {}
    for a in cur["alloc"]:
        if "_birth_seq" in a:
            births.setdefault(a["conf"], []).append(a["_birth_seq"])
    for v in births.values():
        v.sort()
    all_births = sorted(b for v in births.values() for b in v)
    # wp records carry no conf: attach each to the presentation whose
    # birth window [birth, next_birth_of_ANY_conflict) contains it (the
    # stream is al ... bt -> tg/gb -> wp -> [rg]; the next al closes the
    # presentation whether or not a commit happened).  A failing wp on a
    # row with NO commit = the conflict was homed to MEMORY (Rule 136).
    import bisect
    for a in cur["alloc"]:
        bseq = a.get("_birth_seq")
        if bseq is None:
            continue
        i = bisect.bisect_right(all_births, bseq)
        nxt = all_births[i] if i < len(all_births) else None

        def _inwin(evs):
            return [w for w in evs
                    if w["seq"] >= bseq and (nxt is None or w["seq"] < nxt)]

        evs = _inwin(wp_all)
        if evs:
            a["wp"] = [{"budget": w["budget"], "cost": w["cost"],
                        "ok": w["ok"]} for w in evs]
        if "_commit_seq" in a:
            continue
        # Never-committed presentation: classify the MEMORY exile.
        #   worthprolog -- gb winner declined (wp budget < cost);
        #   masked      -- bt fired but every candidate was with.regs/
        #                  except-masked (no tg/gb at all): the classic
        #                  live-range-crosses-everything class (Rule 136
        #                  retval funnel: load_map_graphics `ret`).
        if evs and any(not w["ok"] for w in evs):
            a["memory_exiled"] = "worthprolog"
        elif (_inwin(bt_all.get(a["conf"], []))
                and not _inwin(gb_all.get(a["conf"], []))
                and not _inwin(tg_all.get(a["conf"], []))):
            a["memory_exiled"] = "masked"
    for a in cur["alloc"]:
        # legacy first-sighting attach (fallback / never-committed rows)
        a["withregs"] = wr.get(a["conf"], 0)
        a["ins_walk"] = gi.get(a["conf"], [])
        a["ins_range"] = rng.get(a["conf"])    # (first, last) ins ptrs or None
        a["graph"] = graph.get(a["conf"])      # with/id bitsets or None
        # per-presentation re-attach (2026-06-13): a conflict re-presented
        # across RegAlloc spill rounds carries one wr/bt/gb sweep per
        # presentation; the row's truth is the presentation its COMMIT (rg)
        # closed.  Use the last sighting at/before the commit seq.  Conf
        # ptrs are free-list-reused, but a reused ptr's sightings are
        # strictly later than the prior owner's commit, so the window
        # selection stays per-owner.
        cseq = a.pop("_commit_seq", None)
        bseq = a.pop("_birth_seq", None)
        if cseq is None or bseq is None:
            continue
        # store the commit-window view SEPARATELY (commit_*); legacy
        # first-sighting fields stay primary until the windowed view is
        # corpus-certified (replay A/Bs them).
        # Stream order per presentation (raw-trace-grounded 2026-06-13):
        #   al (birth) ... bt -> tg/gb sweep -> rg (commit) -> wr (POST-
        #   commit NeighboursUse snapshot).
        # The wr that BELONGS to a row is the one in [birth_K, birth_K+1)
        # -- its own post-commit sweep (the semantic the certified replay
        # was built on).  The legacy first-sighting rule hands owner 1's
        # wr to every later free-list re-owner of the same conf ptr; that
        # staleness was the show_latest_route-class identity leak.
        bl = births.get(a["conf"], [])
        nxt = next((b for b in bl if b > bseq), None)
        sights = [s2 for s2 in wr_all.get(a["conf"], [])
                  if s2["seq"] >= bseq and (nxt is None or s2["seq"] < nxt)]
        if sights:
            w = sights[0]
            a["commit_withregs"] = w["mask"]
            if w["rng"] is not None:
                a["commit_ins_range"] = w["rng"]
            if w["graph"] is not None:
                a["commit_graph"] = w["graph"]
            if w.get("usage") is not None:
                a["usage"] = w["usage"]
        bts = [b for b in bt_all.get(a["conf"], [])
               if bseq <= b["seq"] <= cseq]
        if bts:
            top = bts[0]
            a["commit_tree_cands"] = top["tree_cands"]
            if "given_regs" in top:
                a["commit_given_regs"] = top["given_regs"]
            lo = top["seq"]
            sweep = [g for g in gb_all.get(a["conf"], [])
                     if lo <= g["seq"] <= cseq]
            if sweep:
                sc: list[dict] = []
                for g in sweep:           # dedup keep-first = top-level sweep
                    if not any(e["cand"] == g["cand"] for e in sc):
                        sc.append({"cand": g["cand"], "saves": g["saves"]})
                a["commit_cand_scores"] = sc
            vets = [t["reg"] for t in tg_all.get(a["conf"], [])
                    if lo <= t["seq"] <= cseq]
            a["commit_tg_veto"] = list(dict.fromkeys(vets))
            # ce/cm (CountRegMoves ground truth, image >= 2026-07-10),
            # scoped to the same commit-window sweep as cand_scores.
            ces = [c for c in ce_all.get(a["conf"], [])
                   if lo <= c["seq"] <= cseq]
            if ces:
                a["crm_tree"] = {k: ces[0][k]
                                 for k in ("temp", "alt", "size")}
            cms = [c for c in cm_all.get(a["conf"], [])
                   if lo <= c["seq"] <= cseq]
            if cms:
                a["crm_events"] = [
                    {"cand": c["cand"], "ins": c["ins"],
                     "total": c["total"]} for c in cms]
    records = cur.pop("_ir", [])
    cur["_ir_records"] = records      # persisted in the on-disk cache
    cur["ir"] = build_forest(records)

    # Interleaved `ge`/`il` codegen events -> per-cg_ins asm offset map.
    #
    # Walk `_cg` in trace order:
    #   - At each `ge`: bind THIS cg_ins to the current cumulative byte
    #     offset.  Subsequent `il` records accumulate into THIS ins's
    #     byte count, until the next `ge`.
    #   - For ge's whose ins consumes NO il (calls/branches/ret -- they
    #     bypass AdvanceCode), the byte count is initially 0; consumers
    #     reconstruct the actual size by disassembling the binary at the
    #     offset (calls are 5 bytes for `call rel32`, jumps similarly).
    #
    # Output:
    #   `cgen_events` -- list of per-cg_ins records, each:
    #       {"ins": ptr, "opcode": ..., "gen_class": ..., "line": ...,
    #        "result": ..., "op0": ..., "op1": ...,
    #        "offset": cumulative-byte-offset-at-emit-start,
    #        "il_bytes": sum of il records attributed to this ge}
    #   `emit_lengths` / `emit_offsets` / `code_size` -- legacy
    #       AdvanceCode-only view (preserved for back-compat).
    cg_log = cur.pop("_cg", [])
    cgen_events: list[dict] = []
    emit_lengths: list[int] = []
    emit_offsets: list[int] = []
    pos = 0
    current_ge: dict | None = None
    for kind, payload in cg_log:
        if kind == "ge":
            ev = dict(payload)
            ev["offset"] = pos
            ev["il_bytes"] = 0
            cgen_events.append(ev)
            current_ge = ev
        else:  # "il"
            n = int(payload)
            emit_lengths.append(n)
            emit_offsets.append(pos)
            if current_ge is not None:
                current_ge["il_bytes"] += n
            pos += n
    cur["cgen_events"] = cgen_events
    cur["emit_lengths"] = emit_lengths
    cur["emit_offsets"] = emit_offsets
    cur["code_size"] = pos


def has_trace(stdout_text: str) -> bool:
    return "~WV1 " in stdout_text


import re as _re
_LST_FUNC = _re.compile(r"\s+[0-9a-f]+\s+[0-9a-f ]+?\s+([A-Za-z_$][\w$]*)_\s")


def lst_func_names(lst_text: str) -> list[str]:
    """Public function labels from a ``wdisasm -l`` listing, in code order
    (== the order the back end processes routines == trace `fn` order)."""
    return [m.group(1) for ln in lst_text.splitlines()
            if (m := _LST_FUNC.match(ln))]


def savecalc_savings(entries: list[dict], base: int | None) -> int:
    """Reconstruct a conflict's CalcSavings result from its `cv` per-block
    breakdown (``routine["savecalc"][conf]``): ``sum((save - cost) *
    W^min(depth, 4))`` clamped at 0 / MAX_SAVE-1, with ``W = loop_base``
    (Save.loop_weight, 10 for the PS flags).  Mirrors OW c/regsave.c
    CalcSavings + h/savcode.h _UpdateCost; verified exact against the
    `sl` savings on probe TUs.  The per-entry view is the Rule 126 lever:
    a PS-vs-recompile savings delta pins to a BLOCK (and its loop depth),
    i.e. to the exact statement whose use/def/index unit count differs."""
    w = base or 10
    save = cost = 0
    for e in entries:
        m = w ** min(e["depth"], 4)
        save += e["save"] * m
        cost += e["cost"] * m
    if save <= cost:
        return 0
    return min(save - cost, 0xfffffffe)   # MAX_SAVE-1 (conflict.h 0xFFFFFFFF)
