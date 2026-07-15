"""IR forest reconstruction from wcc386 ``~WV1`` trace records.

This is the SINGLE shared implementation of the wcc386 IR (tree forest + name
table + instruction birth events).  Every consumer -- rule predictors,
decomp-verify hints, seatchain, future trace tooling -- imports from here.

Source records (emitted by the instrumented compiler, see watcom10.0a's
``tools/patch_trace.py``).  Every IR record's TRAILING field is ``line`` --
the front-end's current ``SrcLine`` global at hook-fire time:
  * ``tn <ptr> <class> <op> <left> <right> <tipe> <line>``  -- TGNode
  * ``tb <ptr> <sub> <tipe> <start> <length> <line>``       -- TGBitLValue
  * ``tl <ptr> <class> <name|val> <tipe> <line>``           -- TGLeaf
  * ``nb <ptr> <class> <subclass> <name_id> <line>``        -- AllocName
  * ``ni <ptr> <nops> <line>``                              -- NewIns

``line`` is the source-line number of the statement the C front end is
currently emitting CG-API calls for.  ``line == 0`` marks compiler-emitted
synthetic IR (no source statement -- e.g. function prolog setup, runtime
support inits).  Older trace images may omit the field; the builder treats
a missing trailing field as ``line=None``.

Ordering invariant: a ``tn`` node always arrives AFTER its left + right
children (TGNode is called bottom-up by CG{Binary,Compare,Assign,...} after the
operand subtrees have been emitted).  Likewise a ``tl`` referencing a name
always arrives AFTER that name's ``nb``.  A single forward pass therefore
resolves every reference; no two-pass fixup needed.

Class enums (10.0a-verified empirically via /tmp/wcpatch_test/enumprob.c
which exercises one cg_op per function; DO NOT consult OW v1 for values
unless cross-checked).  The full tn_class enum (positional from OW v1
``bld/cg/h/tree.h`` ``tn_class``) was confirmed unchanged in 10.0a:

  TN classes (tn.cls / tl.cls / tb.cls):
      LEAF=0 UNARY=1 BINARY=2 COMPARE=3 ASSIGN=4 LV_ASSIGN=5
      FLOW=6 PRE_GETS=7 LV_PRE_GETS=8 POST_GETS=9
      PARM=0xa CALL=0xb COMMA=0xc
      FLOW_OUT=0xd QUESTION=0xe COLON=0xf
      BIT_LVALUE=0x10 BIT_RVALUE=0x11 CONS=0x12 WARP=0x13
      CALLBACK=0x14 HANDLE=0x15 PATCH=0x16
      (TN_NUMBER_OF_CLASSES=0x17 -- not a real class) SIDE_EFFECT=0x18

  Name classes (nb.cls):
      CONSTANT=0 MEMORY=1 TEMP=2 REGISTER=3 INDEXED=4

  cg_op values seen in TN_BINARY (cls=2) -- match OW v1 positional enum:
      1=O_PLUS  3=O_MINUS  5=O_TIMES  7=O_DIV  8=O_MOD
      9=O_AND   10=O_OR    11=O_XOR
      12=O_RSHIFT  13=O_LSHIFT

  cg_op values seen in TN_PRE_GETS (cls=7) -- same set as TN_BINARY:
      `X op= Y` produces TN_PRE_GETS with op = the cg_op of `op`.
      (Note: 10.0a's optimiser rewrites `g -= K` to `g += -K`, so PRE_GETS
       op=O_MINUS rarely appears in real corpus.)

  cg_op values seen in TN_POST_GETS (cls=9):
      1=O_PLUS (i++)  3=O_MINUS (i--)
      (++i / --i rewrite to TN_PRE_GETS or TN_BINARY+ASSIGN.)

  cg_op values seen in TN_UNARY (cls=1):
      17=O_NEGATE (-a)  18=O_COMPLEMENT (~a)
      80=O_CONVERT (signed convert -- `(long)a`, `(short)a`, `(char)a`)
      36=O_CONVERT_U (unsigned-related convert; appears for `(unsigned)a`
                      and as the implicit zext leg of bit-field read/write)
      (!a never produces TN_UNARY -- the front end rewrites to
       `a == 0`, i.e. TN_COMPARE op=O_CMP_EQUAL.)

  cg_op values seen in TN_COMPARE (cls=3) -- OW v1 OP_CMP_* enum offset 48:
      48=O_CMP_EQUAL    49=O_CMP_NOT_EQUAL
      50=O_CMP_GREATER  51=O_CMP_LESS_EQUAL
      52=O_CMP_LESS     53=O_CMP_GREATER_EQUAL

  cg_op values seen in TN_FLOW (cls=6) -- short-circuit `&&`/`||` boolean ops:
      76=O_FLOW_AND  77=O_FLOW_OR  (tentative -- empirically observed
      pairs only, not exercised in the enumprob.c probe).

Statement boundaries: each ``TN_ASSIGN``/``TN_LV_ASSIGN`` root corresponds to
one DoTGAssign call == one source-level assignment statement.  10.0a almost
always emits TN_ASSIGN even for lvalue-array stores (`g_arr[i] = v`); the
distinct TN_LV_ASSIGN is reserved for special lvalue contexts.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterator, Optional


# ---- enums ---------------------------------------------------------------

TN_LEAF        = 0x00
TN_UNARY       = 0x01
TN_BINARY      = 0x02
TN_COMPARE     = 0x03
TN_ASSIGN      = 0x04
TN_LV_ASSIGN   = 0x05
TN_FLOW        = 0x06      # short-circuit &&/|| internal flow node
TN_PRE_GETS    = 0x07      # the Rule 17b class: `X op= Y` (compound assign)
TN_LV_PRE_GETS = 0x08
TN_POST_GETS   = 0x09      # i++ / i--
TN_PARM        = 0x0a
TN_CALL        = 0x0b
TN_COMMA       = 0x0c
TN_FLOW_OUT    = 0x0d      # the boolean-result terminal of TN_COMPARE chains
TN_QUESTION    = 0x0e      # `?:` test
TN_COLON       = 0x0f      # `?:` arms
TN_BIT_LVALUE  = 0x10
TN_BIT_RVALUE  = 0x11
TN_CONS        = 0x12
TN_WARP        = 0x13
TN_CALLBACK    = 0x14
TN_HANDLE      = 0x15
TN_PATCH       = 0x16
TN_SIDE_EFFECT = 0x18

TN_CLASS_NAME = {
    TN_LEAF:        "LEAF",
    TN_UNARY:       "UNARY",
    TN_BINARY:      "BINARY",
    TN_COMPARE:     "COMPARE",
    TN_ASSIGN:      "ASSIGN",
    TN_LV_ASSIGN:   "LV_ASSIGN",
    TN_FLOW:        "FLOW",
    TN_PRE_GETS:    "PRE_GETS",
    TN_LV_PRE_GETS: "LV_PRE_GETS",
    TN_POST_GETS:   "POST_GETS",
    TN_PARM:        "PARM",
    TN_CALL:        "CALL",
    TN_COMMA:       "COMMA",
    TN_FLOW_OUT:    "FLOW_OUT",
    TN_QUESTION:    "QUESTION",
    TN_COLON:       "COLON",
    TN_BIT_LVALUE:  "BIT_LVALUE",
    TN_BIT_RVALUE:  "BIT_RVALUE",
    TN_CONS:        "CONS",
    TN_WARP:        "WARP",
    TN_CALLBACK:    "CALLBACK",
    TN_HANDLE:      "HANDLE",
    TN_PATCH:       "PATCH",
    TN_SIDE_EFFECT: "SIDE_EFFECT",
}

# cg_op enum (10.0a, empirically recovered via enumprob.c probe; see module
# docstring for the probe -> op mapping).  Where 10.0a matches OW v1 the OW
# name is used; where it diverges or where the OW name is unknown a
# 10.0a-specific name is used and noted.
O_PLUS     = 1        # binary +
O_MINUS    = 3        # binary -
O_TIMES    = 5        # binary *
O_DIV      = 7        # /
O_MOD      = 8        # %
O_AND      = 9        # &
O_OR       = 10       # |
O_XOR      = 11       # ^
O_RSHIFT   = 12       # >>
O_LSHIFT   = 13       # <<
O_NEGATE   = 17       # unary -
O_COMPLEMENT = 18     # unary ~
O_CONVERT_U = 36      # unsigned-related convert; bit-field zext leg
O_FLOW_AND = 76       # `&&` short-circuit (tentative; corpus-observed only)
O_FLOW_OR  = 77       # `||` short-circuit (tentative; corpus-observed only)
O_CONVERT  = 80       # signed convert (`(long)a`, `(short)a`, `(char)a`)
O_CMP_EQUAL          = 48
O_CMP_NOT_EQUAL      = 49
O_CMP_GREATER        = 50
O_CMP_LESS_EQUAL     = 51
O_CMP_LESS           = 52
O_CMP_GREATER_EQUAL  = 53

CG_OP_NAMES = {
    O_PLUS: "O_PLUS", O_MINUS: "O_MINUS",
    O_TIMES: "O_TIMES", O_DIV: "O_DIV", O_MOD: "O_MOD",
    O_AND: "O_AND", O_OR: "O_OR", O_XOR: "O_XOR",
    O_RSHIFT: "O_RSHIFT", O_LSHIFT: "O_LSHIFT",
    O_NEGATE: "O_NEGATE", O_COMPLEMENT: "O_COMPLEMENT",
    O_CONVERT_U: "O_CONVERT_U", O_CONVERT: "O_CONVERT",
    O_FLOW_AND: "O_FLOW_AND", O_FLOW_OR: "O_FLOW_OR",
    O_CMP_EQUAL: "O_CMP_EQUAL", O_CMP_NOT_EQUAL: "O_CMP_NOT_EQUAL",
    O_CMP_GREATER: "O_CMP_GREATER", O_CMP_LESS_EQUAL: "O_CMP_LESS_EQUAL",
    O_CMP_LESS: "O_CMP_LESS", O_CMP_GREATER_EQUAL: "O_CMP_GREATER_EQUAL",
}


# ── cg_ins.opcode (the BYTE at +0x22 in the instruction struct) ──────────
#
# This is the OPCODE used at the cg_ins level (post-lowering from the IR
# tree).  POSITIONALLY MATCHES the tree-level CG_OP for arithmetic /
# comparison ops -- 10.0a uses a SINGLE cg_op enum across both levels.
# Additional values exist for move/call/control-flow that have no tree
# counterpart.
#
# Empirically recovered via the `ge` trace records (GenObjCode entry)
# using the enumcgi.c probe + enum_probe.c.  Source of truth (with
# detailed notes per opcode): watcom10.0a/knowledge/wcc386_regalloc.py
# ``CG_INS_OPCODE_VALUES`` dict.
#
# Consumers (c2.commands.binir_audit, c2.tree_diff) match these against
# routine["cgen_events"][i]["opcode"] to discriminate user instructions
# from compiler-emitted helpers (helpers like RTCall do NOT go through
# GenObjCode so they emit no `ge` record -- absence is PROVEN, not
# heuristic).

CG_INS_OPCODE = {
    # arith (match tn-level)
    "OP_ADD":            1,
    "OP_SUB":            3,
    "OP_MUL":            5,
    "OP_DIV":            7,
    "OP_MOD":            8,
    "OP_AND":            9,
    "OP_OR":             10,
    "OP_XOR":            11,
    "OP_RSHIFT":         12,
    "OP_LSHIFT":         13,
    "OP_NEGATE":         17,
    "OP_COMPLEMENT":     18,
    # cg_ins-level only
    "OP_MOV":            38,    # 0x26 -- regular mov (also confirms INS_NOTE)
    "OP_CALL_INDIRECT":  41,    # 0x29 -- `call dword ptr [m|reg]`
    "OP_CALL":           54,    # 0x36 -- `call rel32` (user call signature;
                                # helper calls bypass GenObjCode entirely)
    # comparison (match tn-level)
    "OP_CMP_EQUAL":         48,
    "OP_CMP_NOT_EQUAL":     49,
    "OP_CMP_GREATER":       50,
    "OP_CMP_LESS_EQUAL":    51,
    "OP_CMP_LESS":          52,
    "OP_CMP_GREATER_EQUAL": 53,
    # block boundary / nop (gen_class=0 -> GenObjCode bails)
    "OP_BLOCK_OR_NOP":      0,
}

# Reverse lookup -- numeric -> name (for trace-event pretty-printing).
CG_INS_OPCODE_NAMES = {v: k for k, v in CG_INS_OPCODE.items()}

# Convenience constants for the most-checked opcodes (binir-audit).
INS_OP_CALL          = CG_INS_OPCODE["OP_CALL"]
INS_OP_CALL_INDIRECT = CG_INS_OPCODE["OP_CALL_INDIRECT"]
INS_OP_MOV           = CG_INS_OPCODE["OP_MOV"]

N_CONSTANT = 0
N_MEMORY   = 1
N_TEMP     = 2
N_REGISTER = 3
N_INDEXED  = 4

NAME_CLASS_NAME = {N_CONSTANT: "CONSTANT", N_MEMORY: "MEMORY",
                   N_TEMP: "TEMP", N_REGISTER: "REGISTER",
                   N_INDEXED: "INDEXED"}

# 10.0a almost always emits TN_ASSIGN even for lvalue-array stores; the rare
# TN_LV_ASSIGN appears only in special lvalue contexts.  Keep BOTH in the
# statement set so the parser doesn't drop any.
STATEMENT_CLASSES = (TN_ASSIGN, TN_LV_ASSIGN)


# ---- model ---------------------------------------------------------------

@dataclass
class Name:
    """A name node (NameLists entry), born from one ``nb`` event.

    ``seq`` is the per-class **birth order** -- the order ``AllocName`` was
    called for this class.  This is the SOURCE-SIDE LEVER (Rule 28 / Rule 115):
    the source author controls birth order via declaration order.

    NOTE: birth order is NOT the same as conflict creation order.  The back
    end's ``RoughSortTemps`` calls ``SortList(Names[N_TEMP], AllocBefore)``
    before ``AssignGlobalBits`` walks it and issues ``AddConflictNode``, so
    conflicts come out savings-sorted, not birth-sorted.  See
    :func:`c2.regalloc.name_birth_order` vs :func:`c2.regalloc.name_list` for
    both views.

    ``ord_all`` is the global cross-class creation index, useful for debugging.
    ``line`` is the source line of the statement that triggered AllocName
    (``None`` if the trace image predates source-line instrumentation; ``0``
    for compiler-internal synthetics like hardware-register names that are
    born before any source statement is seen).
    """
    ptr: int
    cls: int
    subcls: int
    name_id: int
    seq: int                  # per-class BIRTH index (0,1,2,...)
    ord_all: int              # global creation index across all classes
    line: int | None = None   # source line at hook-fire (SrcLine global)

    @property
    def cls_name(self) -> str:
        return NAME_CLASS_NAME.get(self.cls, f"cls{self.cls:#x}")


@dataclass
class Node:
    """A tree node, built from one ``tn`` / ``tl`` / ``tb`` event.

    Interior nodes (``kind=='tn'``) carry ``op`` and resolved ``left`` /
    ``right`` children.  Leaves (``kind=='tl'``) wrap a name or constant in
    ``payload`` (and ``name`` is set when ``payload`` matched an ``nb`` ptr).
    Bit-lvalues (``kind=='tb'``) carry ``bit_start`` / ``bit_len`` and
    reference a ``sub`` expression (often unresolved -- it's a side-band
    pointer the back end uses for the storage location).
    """
    ptr: int
    kind: str                 # 'tn' | 'tl' | 'tb'
    cls: int
    tipe: int
    op: int = 0                       # tn only
    left_ptr: int = 0                 # tn only
    right_ptr: int = 0                # tn only
    left: Optional["Node"] = None     # tn only (resolved)
    right: Optional["Node"] = None    # tn only (resolved)
    payload: int = 0                  # tl: name_or_val
    name: Optional[Name] = None       # tl: resolved when payload is an nb ptr
    sub_ptr: int = 0                  # tb only
    bit_start: int = 0                # tb only
    bit_len: int = 0                  # tb only
    line: int | None = None           # source line at hook-fire (None if pre-
                                      # instrumentation image; 0 for synthetics)

    @property
    def cls_name(self) -> str:
        return TN_CLASS_NAME.get(self.cls, f"cls{self.cls:#x}")

    def is_statement(self) -> bool:
        return self.cls in STATEMENT_CLASSES

    def walk(self) -> Iterator["Node"]:
        """Pre-order traversal (self, left subtree, right subtree)."""
        yield self
        if self.left is not None:
            yield from self.left.walk()
        if self.right is not None:
            yield from self.right.walk()


@dataclass
class Ins:
    """Instruction birth event (``ni`` record).  Opcode / operands are filled
    in by the MakeXxx caller AFTER NewIns returns, so they are NOT in this
    record -- correlate with ``gi`` (regalloc-time samples) by ``ptr``."""
    ptr: int
    nops: int
    line: int | None = None           # source line at NewIns time (SrcLine)


@dataclass
class IRForest:
    """Per-routine IR view.  Built by :func:`build_forest` from a routine's
    chronological ``tn`` / ``tl`` / ``tb`` / ``nb`` / ``ni`` records.

    Attributes
    ----------
    nodes : dict[int, Node]
        LAST seen tree node per in-compiler pointer.  ptrs are heavily reused
        across statements (the free-list returns the same memory once the
        front end is done with one statement and starts the next), so this
        dict only holds the most-recent occupant.  Use ``all_nodes`` (a
        chronological list) for retrospective analysis -- references inside
        already-constructed Nodes' ``left``/``right`` slots are stable Python
        object handles and never get overwritten.
    names : list[Name]
        Names in global birth order (``nb`` emit order).
    names_by_ptr : dict[int, Name]
        Lookup by the in-compiler name-pointer.
    names_by_class : dict[int, list[Name]]
        Names bucketed by ``cls``, each list in BIRTH order (AllocName call
        order).  Source-side lever for Rule 28 / Rule 115 (the user controls
        birth order via declaration order).  This is NOT the ConfBefore tie-
        break input -- see ``Name.seq`` docstring for the distinction.
    roots : list[Node]
        Statement roots (TN_ASSIGN / TN_LV_ASSIGN), in DoTGAssign emit order.
    insns : list[Ins]
        Instruction birth events in NewIns emit order.
    """
    nodes: dict[int, Node]         = field(default_factory=dict)
    all_nodes: list[Node]          = field(default_factory=list)
    names: list[Name]              = field(default_factory=list)
    names_by_ptr: dict[int, Name]  = field(default_factory=dict)
    names_by_class: dict[int, list[Name]] = field(default_factory=dict)
    roots: list[Node]              = field(default_factory=list)
    insns: list[Ins]               = field(default_factory=list)

    # ---- convenience accessors ------------------------------------------

    def statements(self) -> list[Node]:
        """Alias for ``roots`` -- statement boundaries (TN_ASSIGN roots)."""
        return list(self.roots)

    def name_order(self, cls: int) -> list[Name]:
        """Per-class birth order (AllocName call order).  See ``Name.seq``
        for why this is NOT the ConfBefore tie-break input."""
        return list(self.names_by_class.get(cls, []))

    def nodes_of(self, *classes: int) -> list[Node]:
        """All nodes whose ``cls`` is in ``classes`` (in pointer order is not
        meaningful; iterate the dict for a deterministic order keyed by ptr)."""
        return [n for n in self.nodes.values() if n.cls in classes]


# ---- builder -------------------------------------------------------------

# Each handler: (field-list f, forest, ordinal counters) -> None.  Counters are
# in-place dicts so that successive calls keep counting.

def _opt_line(f: list[str], idx: int) -> int | None:
    """Trailing-field accessor: returns None when the field is missing (older
    trace images without source-line instrumentation)."""
    return int(f[idx]) if len(f) > idx else None


def _consume_nb(f: list[str], forest: IRForest,
                per_class: dict[int, int], ord_counter: list[int]) -> None:
    ptr     = int(f[0], 16)
    cls     = int(f[1])
    subcls  = int(f[2])
    name_id = int(f[3], 16)
    line    = _opt_line(f, 4)
    seq = per_class.get(cls, 0)
    per_class[cls] = seq + 1
    name = Name(ptr=ptr, cls=cls, subcls=subcls, name_id=name_id,
                seq=seq, ord_all=ord_counter[0], line=line)
    ord_counter[0] += 1
    forest.names.append(name)
    forest.names_by_ptr[ptr] = name
    forest.names_by_class.setdefault(cls, []).append(name)


def _consume_tl(f: list[str], forest: IRForest) -> None:
    ptr     = int(f[0], 16)
    cls     = int(f[1])
    payload = int(f[2], 16)
    tipe    = int(f[3], 16)
    line    = _opt_line(f, 4)
    node = Node(ptr=ptr, kind="tl", cls=cls, tipe=tipe, payload=payload,
                name=forest.names_by_ptr.get(payload), line=line)
    forest.nodes[ptr] = node
    forest.all_nodes.append(node)


def _consume_tb(f: list[str], forest: IRForest) -> None:
    ptr    = int(f[0], 16)
    sub    = int(f[1], 16)
    tipe   = int(f[2], 16)
    start  = int(f[3])
    length = int(f[4])
    line   = _opt_line(f, 5)
    node = Node(ptr=ptr, kind="tb", cls=TN_BIT_LVALUE, tipe=tipe,
                sub_ptr=sub, bit_start=start, bit_len=length, line=line)
    forest.nodes[ptr] = node
    forest.all_nodes.append(node)


def _consume_tn(f: list[str], forest: IRForest) -> None:
    ptr   = int(f[0], 16)
    cls   = int(f[1])
    op    = int(f[2])
    left  = int(f[3], 16)
    right = int(f[4], 16)
    tipe  = int(f[5], 16)
    line  = _opt_line(f, 6)
    node = Node(ptr=ptr, kind="tn", cls=cls, tipe=tipe, op=op,
                left_ptr=left, right_ptr=right,
                left=forest.nodes.get(left) if left else None,
                right=forest.nodes.get(right) if right else None,
                line=line)
    forest.nodes[ptr] = node
    forest.all_nodes.append(node)
    if cls in STATEMENT_CLASSES:
        forest.roots.append(node)


def _consume_ni(f: list[str], forest: IRForest) -> None:
    forest.insns.append(Ins(ptr=int(f[0], 16), nops=int(f[1]),
                            line=_opt_line(f, 2)))


_HANDLERS = {
    "nb": _consume_nb,
    "tl": _consume_tl,
    "tb": _consume_tb,
    "tn": _consume_tn,
    "ni": _consume_ni,
}

IR_TAGS = frozenset(_HANDLERS)


def build_forest(records: list[tuple[str, list[str]]]) -> IRForest:
    """Construct an :class:`IRForest` from a routine's chronological IR
    records.

    Parameters
    ----------
    records : list[(tag, fields)]
        ``tag`` is one of ``IR_TAGS``; ``fields`` is the trailing args of the
        ``~WV1 <tag> ...`` line (everything after the tag).  Records MUST be in
        emit order; the builder relies on the bottom-up invariant.
    """
    forest = IRForest()
    per_class: dict[int, int] = {}
    ord_counter = [0]
    for tag, fields in records:
        h = _HANDLERS.get(tag)
        if h is _consume_nb:
            h(fields, forest, per_class, ord_counter)
        elif h is not None:
            h(fields, forest)
    return forest
