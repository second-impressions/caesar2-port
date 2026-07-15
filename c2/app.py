"""Main typer application for the c2 toolkit."""

import os as _os

# Plain-text output: the c2 tools emit NO ANSI colour by default -- cleaner
# for piping, logs, diffing, and agent consumption.  Rich honours NO_COLOR
# (it still parses `[markup]` so tags are consumed, just no colour codes are
# emitted).  Set this BEFORE any command module is imported so every Console
# in the process picks it up.  Opt back in with `C2_COLOR=1`.
if _os.environ.get("C2_COLOR", "").lower() not in ("1", "true", "yes"):
    _os.environ.setdefault("NO_COLOR", "1")

import typer

from c2.commands.compare import compare
from c2.commands.decomp import decomp
from c2.commands.sym import sym
from c2.commands.decomp_verify import decomp_verify
from c2.commands.gen_header import gen_header
from c2.commands.progress import progress
from c2.commands.disasm import disasm
from c2.commands.inferred_sig import inferred_sig
from c2.commands.xrefs import xrefs
from c2.commands.stubs import stubs
from c2.commands.tail_merge_rank import tail_merge
from c2.commands.version_match import version_match
from c2.commands.crossbuild import crossbuild_map
from c2.commands.tree_diff_cmd import tree_diff_cmd
from c2.commands.binir_audit import binir_audit_cmd
from c2.commands.textfile import app as textfile_app
from c2.commands.image import app as image_app
from c2.commands.export import export
from c2.commands.hash import hash_cmd
from c2.commands.install import install
from c2.commands.run import run
from c2.commands.scan import scan
from c2.commands.unpack import unpack
from c2.commands.compiler_id import app as compiler_id_app
from c2.commands.oracle import app as oracle_app
from c2.commands.baseline import app as baseline_app
from c2.commands.row_caches import row_caches
from c2.commands.lint_row_caches import lint_row_caches
from c2.commands.data_init import data_init
from c2.commands.sibling import sibling
from c2.commands.pragma_hints import pragma_hints
from c2.commands.frame_hints import frame_hints
from c2.commands.dispatch_hints import dispatch_hints
from c2.commands.callgraph import callgraph
from c2.commands.sig_drift import sig_drift
from c2.commands.func_order import func_order
from c2.commands.moved_code_hints import moved_code
from c2.commands.regtrace import regtrace, regtrace_sweep
from c2.commands.regtrace_native import regtrace_native
from c2.commands.lastuse import lastuse
from c2.commands.ledger import ledger
from c2.commands.spell import spell
from c2.commands.sweep import sweep
from c2.commands.tempbirths import tempbirths
from c2.commands.savings_view import savings_view
from c2.commands.seats import seats
from c2.commands.cache import cache
from c2.commands.line_shape import line_shape
from c2.commands.local_hints import local_hints
from c2.commands.loop_hints import loops
from c2.commands.const_audit import const_audit
from c2.commands.decl_audit import decl_audit
from c2.commands.line_compare import line_compare
from c2.commands.negative_corpus import negative_corpus
from c2.commands.global_cache_hints import global_cache_hints
from c2.commands.residue_cluster import residue_cluster
from c2.commands.const_drift import const_drift
from c2.commands.trace_census import trace_census
from c2.commands.mac_fn import mac_fn
from c2.commands.mac_decompile import mac_decompile
from c2.commands.win_decompile import win_decompile
from c2.commands.win_verify import win_verify
from c2.commands.win_census import win_census
from c2.commands.dossier import dossier
from c2.commands.line_skeleton import line_skeleton
from c2.commands.shape_recon import shape_recon
from c2.commands.diagnose import diagnose
from c2.commands.functions import functions
from c2.commands.triage import triage
from c2.commands.worklist import worklist
from c2.commands.alloc_replay import alloc_replay
from c2.commands.regalloc_verdict import regalloc_verdict
from c2.commands.shape_census import shape_census
from c2.commands.reg_delta import reg_delta
from c2.commands.delink import delink
from c2.commands.rebuild import rebuild
from c2.commands.reccmp import app as reccmp_app

app = typer.Typer(
    name="c2",
    help="Caesar II reverse engineering toolkit.",
    no_args_is_help=True,
)

cd_app = typer.Typer(
    help="CD management commands (unpack, hash, install, compare).",
    no_args_is_help=True,
)
app.add_typer(cd_app, name="cd")

# PL8 image commands (show, export, import) — self-contained Typer sub-app
app.add_typer(image_app, name="image")

# Top-level commands
app.command("export")(export)
app.command("decomp")(decomp)
app.command("sym")(sym)
app.command("decomp-verify")(decomp_verify)
app.command("shape-census")(shape_census)
app.command("reg-delta")(reg_delta)
app.command("delink")(delink)
app.command("rebuild")(rebuild)
app.add_typer(reccmp_app, name="reccmp")
app.command("gen-header")(gen_header)
app.command("progress")(progress)
app.command("disasm")(disasm)
app.command("inferred-sig")(inferred_sig)
app.command("callgraph")(callgraph)
app.command("sig-drift")(sig_drift)
app.command("func-order")(func_order)
app.command("moved-code")(moved_code)
app.command("trace-census")(trace_census)
app.command("mac-fn")(mac_fn)
app.command("mac-decompile")(mac_decompile)
app.command("win-decompile")(win_decompile)
app.command("win-verify")(win_verify)
app.command("win-census")(win_census)
app.command("dossier")(dossier)
app.command("ledger")(ledger)
app.command("spell")(spell)
app.command("sweep")(sweep)
app.command("tempbirths")(tempbirths)
app.command("savings")(savings_view)
app.command("seats")(seats)
app.command("cache")(cache)
app.command("line-skeleton")(line_skeleton)
app.command("shape-recon")(shape_recon)
app.command("diagnose")(diagnose)
app.command("functions")(functions)
app.command("triage")(triage)
app.command("worklist")(worklist)
app.command("alloc-replay")(alloc_replay)
app.command("regalloc-verdict")(regalloc_verdict)
app.command("regtrace")(regtrace)
app.command("regtrace-native")(regtrace_native)
app.command("regtrace-sweep")(regtrace_sweep)
app.command("lastuse")(lastuse)
app.command("line-shape")(line_shape)
app.command("local-hints")(local_hints)
app.command("loops")(loops)
app.command("line-compare")(line_compare)
app.command("const-audit")(const_audit)
app.command("decl-audit")(decl_audit)
app.command("negative-corpus")(negative_corpus)
app.command("global-cache-hints")(global_cache_hints)
app.command("residue-cluster")(residue_cluster)
app.command("const-drift")(const_drift)
app.command("xrefs")(xrefs)
app.command("stubs")(stubs)
app.command("row-caches")(row_caches)
app.command("lint-row-caches")(lint_row_caches)
app.command("data-init")(data_init)
app.command("sibling")(sibling)
app.command("pragma-hints")(pragma_hints)
app.command("frame-hints")(frame_hints)
app.command("dispatch-hints")(dispatch_hints)
app.command("tail-merge")(tail_merge)
app.command("donors")(tail_merge)
app.command("version-match")(version_match)
app.command("crossbuild-map")(crossbuild_map)
app.command("tree-diff")(tree_diff_cmd)
app.command("binir-audit")(binir_audit_cmd)
app.command("run")(run)
app.add_typer(textfile_app, name="textfile")

# Watcom 10.0a toolchain commands

# CD subgroup commands
cd_app.command("unpack")(unpack)
cd_app.command("hash")(hash_cmd)
cd_app.command("install")(install)
cd_app.command("compare")(compare)
cd_app.command("scan")(scan)

# Compiler version identification
app.add_typer(compiler_id_app, name="compiler-id")

# Codegen oracle
app.add_typer(oracle_app, name="oracle")

# Per-function byte-diff baselines
app.add_typer(baseline_app, name="baseline")

# Brute-force experiment harness (replaces cgex + permute + ast_levers).
from c2.commands.forge import app as forge_app   # noqa: E402

app.add_typer(forge_app, name="forge")

# Pydantic-AI-powered subagent orchestrator (replaces the c2_ext pi tools).
from c2.decompile.cli import decompile_cmd   # noqa: E402

app.command("decompile")(decompile_cmd)
