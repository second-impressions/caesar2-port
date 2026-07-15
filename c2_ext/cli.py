"""``c2-ext`` CLI: subagent harness command set.

**Compose** always sets up for the **watcom 10.0a** compile target (PS.EXE
is the project's primary byte oracle); the agent picks which byte oracle
to validate against per-call:

* ``verify <run_dir> [--target watcom|msvc]``  -- compile scratch.c with the
  named toolchain and byte-compare against its binary.  watcom = PS.EXE,
  msvc = CAESAR2.EXE.
* ``disasm <fn> [--binary watcom|msvc|mac]`` -- disassemble a function
  from one of the three reference binaries.
* ``decompile <fn> --binary {msvc,mac}`` -- Ghidra-decompiled C source
  for a function from CAESAR2.EXE (MSVC /Od) or the Mac PPC binary.

Watcom-only tools (the byte-exact corpus they consult is per-toolchain):

* ``compose <fn> [--blank] [--out PATH]`` -- prepare a run dir.
* ``harvest <run_dir>`` -- read back scratch.c + final verify result.
* ``index [--force]`` -- build / refresh the embedding index.
* ``nearest [--fn NAME | --snippet TEXT] [--top N]``
* ``info <fn>`` / ``fetch <fn>`` / ``lookup <query>`` / ``apply <run_dir>``

All commands accept ``--json`` for structured output the TS layer can
consume directly.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from c2_ext.project import ProjectConfig


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="c2-ext")
    sub = parser.add_subparsers(dest="command", required=True)

    sp = sub.add_parser("targets", help="List configured targets / binaries")
    sp.add_argument("--json", action="store_true")

    # compose -- always watcom (PS.EXE is the canonical byte oracle).
    sp = sub.add_parser("compose", help="Prepare a run directory (always watcom)")
    sp.add_argument("function")
    sp.add_argument("--blank", action="store_true",
                    help="Start scratch.c from an empty stub")
    sp.add_argument("--out", type=Path, default=None,
                    help="Explicit run dir (default: runs_root/<slug>-<ts>)")
    sp.add_argument("--json", action="store_true")

    sp = sub.add_parser("harvest", help="Read back a run dir's outputs")
    sp.add_argument("run_dir", type=Path)
    sp.add_argument("--json", action="store_true")

    sp = sub.add_parser("index", help="Build / refresh embedding index (watcom)")
    sp.add_argument("--force", action="store_true")
    sp.add_argument("--json", action="store_true")

    sp = sub.add_parser("verify", help="Compile + byte-diff vs target binary")
    sp.add_argument("run_dir", type=Path)
    sp.add_argument("--target", default="watcom",
                    choices=("watcom", "msvc"),
                    help="Compile toolchain + byte oracle (default: watcom).")
    sp.add_argument("--diff", action="store_true",
                    help="Show full per-row diff (default: context window)")
    sp.add_argument("--json", action="store_true")
    sp.add_argument("--no-checkpoint", action="store_true",
                    help="Disable auto-checkpoint of the best scratch.c "
                         "(by default the run dir keeps scratch.best.c "
                         "+ scratch.best.json with the lowest-shape watcom verify so far).")

    sp = sub.add_parser("revert-to-best",
                        help="Restore scratch.best.c into scratch.c")
    sp.add_argument("run_dir", type=Path)
    sp.add_argument("--json", action="store_true")

    sp = sub.add_parser("disasm",
                        help="Disassembly with L+N + symbols, from any binary")
    sp.add_argument("function", nargs="?", default=None)
    sp.add_argument("--binary", default="watcom",
                    choices=("watcom", "msvc", "mac"),
                    help="Which reference binary to disassemble (default: watcom).")
    sp.add_argument("--run-dir", type=Path, default=None,
                    help="If set, default function = the run's function")
    sp.add_argument("--range", type=str, default=None,
                    help="START:END byte offsets to show (watcom/msvc only)")
    sp.add_argument("--bytes", action="store_true", help="Show raw bytes column")
    sp.add_argument("--limit", type=int, default=300,
                    help="Max rows to show (default: 300; use --no-limit to disable)")
    sp.add_argument("--no-limit", action="store_true",
                    help="Show every row even for huge functions")
    sp.add_argument("--json", action="store_true")

    sp = sub.add_parser("decompile",
                        help="Ghidra-decompiled C source from CAESAR2.EXE or Mac PPC")
    sp.add_argument("function")
    sp.add_argument("--binary", required=True,
                    choices=("msvc", "mac"),
                    help="msvc = CAESAR2.EXE (/Od); mac = Mac PPC (CodeWarrior)")
    sp.add_argument("--json", action="store_true")

    sp = sub.add_parser("nearest", help="Embedding-similar functions (watcom corpus)")
    g = sp.add_mutually_exclusive_group()
    g.add_argument("--fn", type=str, default=None,
                   help="Reference function name")
    g.add_argument("--snippet", type=str, default=None,
                   help="Ad-hoc asm snippet")
    sp.add_argument("--run-dir", type=Path, default=None,
                    help="Default --fn = the run's function")
    sp.add_argument("--top", type=int, default=10)
    sp.add_argument("--json", action="store_true")

    sp = sub.add_parser("fetch", help="Fetch decompiled C for a watcom byte-exact function")
    sp.add_argument("function")
    sp.add_argument("--json", action="store_true")

    sp = sub.add_parser(
        "apply",
        help="Lift scratch.c's function back into the real project TU",
    )
    sp.add_argument("run_dir", type=Path)
    sp.add_argument("--dry-run", action="store_true",
                    help="Compute the splice but don't write")
    sp.add_argument("--json", action="store_true")

    sp = sub.add_parser("lookup", help="Look up a symbol by name, address, or glob")
    sp.add_argument("query", help="Name, hex/decimal address, or glob (e.g. barb_*)")
    sp.add_argument("--limit", type=int, default=25,
                    help="Max matches for glob/fuzzy queries (default: 25)")
    sp.add_argument("--binary", default="watcom",
                    choices=("watcom", "msvc"),
                    help="Symbol DB to query (default: watcom = PS.EXE).")
    sp.add_argument("--json", action="store_true")

    sp = sub.add_parser("info", help="Structural info + siblings + types for a function")
    sp.add_argument("function", nargs="?", default=None,
                    help="Function name (default: the run's function)")
    sp.add_argument("--run-dir", type=Path, default=None)
    sp.add_argument("--siblings", type=int, default=8)
    sp.add_argument("--json", action="store_true")

    sp = sub.add_parser("stop", help="Stop a run's warm container")
    sp.add_argument("run_dir", type=Path)

    args = parser.parse_args(argv)
    # Every subcommand binds to the WATCOM project view by default.
    # `verify --target msvc` and `disasm --binary msvc` switch to the
    # MSVC view on demand via project.for_target("msvc").
    project = ProjectConfig.load(target="watcom")
    return _dispatch(args, project)


def _dispatch(args, project: ProjectConfig) -> int:
    cmd = args.command
    if cmd == "targets":
        return _cmd_targets(args, project)
    if cmd == "compose":
        return _cmd_compose(args, project)
    if cmd == "harvest":
        return _cmd_harvest(args, project)
    if cmd == "index":
        return _cmd_index(args, project)
    if cmd == "verify":
        return _cmd_verify(args, project)
    if cmd == "revert-to-best":
        return _cmd_revert_to_best(args)
    if cmd == "disasm":
        return _cmd_disasm(args, project)
    if cmd == "decompile":
        return _cmd_decompile(args, project)
    if cmd == "nearest":
        return _cmd_nearest(args, project)
    if cmd == "fetch":
        return _cmd_fetch(args, project)
    if cmd == "info":
        return _cmd_info(args, project)
    if cmd == "lookup":
        return _cmd_lookup(args, project)
    if cmd == "apply":
        return _cmd_apply(args, project)
    if cmd == "stop":
        return _cmd_stop(args, project)
    raise SystemExit(f"unknown command {cmd}")


#  implementations


def _cmd_targets(args, project) -> int:
    info = {
        "default": project.default_target,
        "active": project.active_target,
        "targets": list(project.available_targets),
    }
    if args.json:
        print(json.dumps(info))
        return 0
    print(f"default: {info['default']}")
    print(f"active:  {info['active']}")
    print("targets:")
    for name in info["targets"]:
        marker = " *" if name == info["active"] else "  "
        try:
            sub_proj = project.for_target(name)
            tcname = sub_proj.toolchain_spec.name
            tgt = sub_proj.target_binary.name
            print(f"  {marker} {name:10s}  {tcname:14s}  vs {tgt}")
        except Exception as e:
            print(f"  {marker} {name:10s}  (config error: {e})")
    return 0


def _cmd_compose(args, project) -> int:
    from c2_ext.runs import compose, ComposeError
    try:
        path = compose(project, args.function, blank=args.blank, out_dir=args.out)
    except ComposeError as e:
        if args.json:
            print(json.dumps({"ok": False, "error": str(e)}))
        else:
            sys.stderr.write(f"compose failed: {e}\n")
        return 1
    if args.json:
        print(json.dumps({"ok": True, "run_dir": str(path),
                          "function": args.function}))
    else:
        print(path)
    return 0


def _cmd_harvest(args, project) -> int:
    from c2_ext.runs import harvest
    h = harvest(args.run_dir)
    if args.json:
        print(json.dumps(h))
    else:
        print(f"run dir: {h.get('run_dir')}")
        print(f"exists:  {h.get('exists')}")
        if h.get("exists"):
            print(f"fn:      {h['function']}")
            print(f"scratch: {len(h['scratch'])} chars")
    return 0


def _cmd_index(args, project) -> int:
    from c2_ext.embed.index import index_corpus
    res = index_corpus(project, force=args.force)
    if args.json:
        print(json.dumps(res))
    else:
        print(f"index: {res}")
    return 0


def _cmd_verify(args, project) -> int:
    from c2_ext.verify import (
        verify, maybe_checkpoint_best, read_best_manifest,
    )
    res = verify(project, args.run_dir, diff=args.diff, target=args.target)

    # Auto-checkpoint best-so-far (watcom only; msvc + build-fails are
    # ignored inside maybe_checkpoint_best).
    checkpointed = False
    if not getattr(args, "no_checkpoint", False):
        checkpointed = maybe_checkpoint_best(args.run_dir, res)

    if args.json:
        print(json.dumps({
            "build_ok": res.build_ok,
            "exact": res.exact,
            "byte_diff": res.byte_diff,
            "real_diff_rows": res.real_diff_rows,
            "target": res.target,
            "target_bytes": res.target_bytes_size,
            "your_bytes": res.your_bytes_size,
            "rendered": res.rendered,
            "fallthrough_callee": res.fallthrough_callee,
            "donor_name": res.donor_name,
            "shape_distance": res.shape_distance,
            "checkpoint_updated": checkpointed,
            "best": read_best_manifest(args.run_dir),
        }))
    else:
        for line in res.rendered:
            print(line)
        # Footer: tell the agent about the best-so-far and the
        # snapshot-revert tool.  Only when the current state is NOT
        # the best (i.e. the agent has somewhere to revert to).
        if res.target == "watcom" and not res.exact:
            manifest = read_best_manifest(args.run_dir)
            if manifest is not None:
                if not res.build_ok:
                    cur_metric = "BUILD FAIL"
                else:
                    cur_metric = (f"{res.byte_diff}/{res.target_bytes_size}"
                                  + ("" if res.shape_distance is None
                                     else f"  shape ir {res.shape_distance.get('ir',0)} "
                                          f"width {res.shape_distance.get('width',0)} "
                                          f"spill {res.shape_distance.get('spill',0)} "
                                          f"seat {res.shape_distance.get('seat',0)}"))
                if checkpointed:
                    print(f"\n* new best snapshot: {manifest.get('metric','?')}"
                          f"  (saved to scratch.best.c)")
                else:
                    print(f"\n* best so far: {manifest.get('metric','?')}"
                          f"  -- `c2-ext revert-to-best` restores it"
                          f"\n  this verify:  {cur_metric}")
    return 0 if res.exact else (1 if not res.build_ok else 2)


def _cmd_revert_to_best(args) -> int:
    from c2_ext.verify import revert_to_best
    try:
        info = revert_to_best(args.run_dir)
    except FileNotFoundError as e:
        msg = str(e)
        if args.json:
            print(json.dumps({"reverted": False, "error": msg}))
        else:
            sys.stderr.write(msg + "\n")
        return 2
    if args.json:
        print(json.dumps(info))
    else:
        sd = info.get("shape_distance") or {}
        sd_str = ("" if not sd else
                  f"  shape ir {sd.get('ir',0)} width {sd.get('width',0)} "
                  f"spill {sd.get('spill',0)} seat {sd.get('seat',0)}")
        print(f"reverted scratch.c <- scratch.best.c  "
              f"(byte_diff={info.get('byte_diff','?')}{sd_str})")
    return 0


def _cmd_disasm(args, project) -> int:
    if args.binary == "mac":
        return _cmd_disasm_mac(args)
    # watcom / msvc: in-process via the toolchain
    target_proj = project if args.binary == "watcom" else project.for_target("msvc")
    return _cmd_disasm_toolchain(args, target_proj)


def _cmd_disasm_toolchain(args, project) -> int:
    from c2_ext.format.asm import apply_line_numbers, render_rows
    tc = project.toolchain()
    fn_name = args.function
    if fn_name is None:
        if args.run_dir is None:
            sys.stderr.write("error: function name or --run-dir required\n")
            return 2
        from c2_ext.runs import load_meta
        fn_name = load_meta(args.run_dir).function
    pool = tc.byte_exact_functions()
    own = None
    if args.run_dir is not None:
        from c2_ext.runs import load_meta
        own = load_meta(args.run_dir).function
    # Pool-restrict: only allow names in the byte-exact pool OR the run's own fn.
    if fn_name not in pool and fn_name != own:
        msg = (f"function {fn_name!r} is not in the {args.binary} byte-exact pool; "
               f"only the run's own function and byte-exact functions can be disassembled")
        if args.json:
            print(json.dumps({"ok": False, "error": msg}))
        else:
            sys.stderr.write(msg + "\n")
        return 2
    try:
        info = tc.function_info(fn_name)
    except KeyError as e:
        sys.stderr.write(f"{e}\n")
        return 1
    fb = tc.function_bytes(fn_name)
    fix = tc.function_fixups(fn_name)
    insns = tc.disassemble(fb, info.address, fix)
    lns = tc.line_numbers(fn_name)
    rows = apply_line_numbers(insns, lns)
    if args.range:
        try:
            start_s, end_s = args.range.split(":", 1)
            start = int(start_s, 0) if start_s else 0
            end = int(end_s, 0) if end_s else 1 << 30
        except ValueError:
            sys.stderr.write("--range must be START:END (hex or dec)\n")
            return 2
        rows = [r for r in rows if start <= r.offset < end]
    total_rows = len(rows)
    elided = 0
    if not args.no_limit and args.range is None and total_rows > args.limit:
        head = args.limit // 2
        tail = args.limit - head
        elided = total_rows - args.limit
        rows = rows[:head] + rows[-tail:]
    lines = render_rows(rows, show_offset=True, show_bytes=args.bytes)
    if elided:
        mid = args.limit // 2
        marker = (
            f"... {elided} rows elided "
            f"(showing {args.limit}/{total_rows}; "
            f"pass --range or --no-limit to expand) ..."
        )
        lines = lines[:mid] + [marker] + lines[mid:]
    if args.json:
        print(json.dumps({
            "function": fn_name,
            "binary": args.binary,
            "address_hex": f"0x{info.address:x}",
            "size": info.size,
            "lines": lines,
            "total_rows": total_rows,
            "shown_rows": len(rows),
            "elided_rows": elided,
        }))
    else:
        for line in lines:
            print(line)
    return 0


def _cmd_disasm_mac(args) -> int:
    """Mac PPC disasm: shell out to ``c2 mac-fn`` (Ghidra-backed)."""
    if not args.function:
        if args.run_dir is None:
            sys.stderr.write("error: function name or --run-dir required\n")
            return 2
        from c2_ext.runs import load_meta
        args.function = load_meta(args.run_dir).function
    cmd = ["uv", "run", "c2", "mac-fn", args.function]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if args.json:
        print(json.dumps({
            "ok": proc.returncode == 0,
            "binary": "mac",
            "function": args.function,
            "output": proc.stdout,
            "stderr": proc.stderr,
        }))
    else:
        sys.stdout.write(proc.stdout)
        if proc.stderr:
            sys.stderr.write(proc.stderr)
    return proc.returncode


def _cmd_decompile(args, project) -> int:
    """Ghidra C decompile of a function from CAESAR2.EXE or Mac PPC."""
    cmd_name = "win-decompile" if args.binary == "msvc" else "mac-decompile"
    cmd = ["uv", "run", "c2", cmd_name, args.function]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if args.json:
        print(json.dumps({
            "ok": proc.returncode == 0,
            "binary": args.binary,
            "function": args.function,
            "source": proc.stdout,
            "stderr": proc.stderr,
        }))
    else:
        sys.stdout.write(proc.stdout)
        if proc.stderr:
            sys.stderr.write(proc.stderr)
    return proc.returncode


def _cmd_nearest(args, project) -> int:
    from c2_ext.embed.index import query_by_function, query_by_snippet
    tc = project.toolchain()
    pool = tc.byte_exact_functions()
    fn = args.fn
    if fn is None and args.snippet is None:
        if args.run_dir is None:
            sys.stderr.write("error: --fn, --snippet, or --run-dir required\n")
            return 2
        from c2_ext.runs import load_meta
        fn = load_meta(args.run_dir).function

    try:
        if args.snippet is not None:
            hits = query_by_snippet(project, args.snippet, top=args.top)
        else:
            hits = query_by_function(project, fn, top=args.top)
    except RuntimeError as e:
        sys.stderr.write(f"{e}\n")
        return 1
    hits = [h for h in hits if h["name"] in pool]
    if args.json:
        print(json.dumps({"hits": hits[:args.top]}))
    else:
        for h in hits[:args.top]:
            print(f"  {h['name']:40s}  {h['score']:.4f}")
    return 0


def _cmd_fetch(args, project) -> int:
    tc = project.toolchain()
    pool = tc.byte_exact_functions()
    if args.function not in pool:
        msg = (f"function {args.function!r} is not in the byte-exact pool; "
               f"`fetch` only returns sources for proven-correct templates")
        if args.json:
            print(json.dumps({"ok": False, "error": msg}))
        else:
            sys.stderr.write(msg + "\n")
        return 2
    src = tc.existing_source(args.function)
    if src is None:
        msg = f"function {args.function!r} has no decomp source in the project"
        if args.json:
            print(json.dumps({"ok": False, "error": msg}))
        else:
            sys.stderr.write(msg + "\n")
        return 1
    file_name, body = src
    if args.json:
        print(json.dumps({"ok": True, "function": args.function,
                          "source_file": file_name, "body": body}))
    else:
        print(body)
    return 0


def _cmd_apply(args, project) -> int:
    from c2_ext.apply import apply, ApplyError
    try:
        result = apply(project, args.run_dir, dry_run=args.dry_run)
    except ApplyError as e:
        if args.json:
            print(json.dumps({"ok": False, "error": str(e)}))
        else:
            sys.stderr.write(f"apply failed: {e}\n")
        return 1
    if args.json:
        print(json.dumps({
            "ok": True,
            "function": result.function,
            "source_file": result.source_file,
            "tu_path": result.tu_path,
            "bytes_before": result.bytes_before,
            "bytes_after": result.bytes_after,
            "bytes_changed": result.bytes_changed,
            "wrote": result.wrote,
        }))
    else:
        verb = "would lift" if args.dry_run else "lifted"
        print(
            f"{verb} {result.function} into {result.tu_path}\n"
            f"  bytes: {result.bytes_before} -> {result.bytes_after} "
            f"(delta {result.bytes_changed:+d})"
        )
    return 0


def _cmd_lookup(args, project) -> int:
    from c2_ext.symbols import lookup
    if args.binary == "msvc":
        project = project.for_target("msvc")
    hits = lookup(project.symbols_json, args.query, limit=args.limit)
    if args.json:
        print(json.dumps({"hits": [h.to_dict() for h in hits]}))
        return 0 if hits else 1
    if not hits:
        sys.stderr.write(f"no symbol matches {args.query!r}\n")
        return 1
    for h in hits:
        kind_tag = h.kind if h.kind != "function" else "fn"
        delta_tag = ""
        if h.delta > 0:
            delta_tag = f"+0x{h.delta:x}"
        elif h.delta < 0:
            delta_tag = f"-0x{-h.delta:x}"
        size_tag = f"size={h.size}" if h.size else ""
        source_tag = (
            f"{h.source_file}:{h.source_lines[0]}-{h.source_lines[1]}"
            if h.source_lines else ""
        )
        parts = [
            f"{h.name}{delta_tag}",
            h.address_hex,
            f"({kind_tag})",
            size_tag,
            source_tag,
        ]
        print("  " + "  ".join(p for p in parts if p))
    return 0


def _cmd_info(args, project) -> int:
    from c2_ext.info import info, render_info_md
    fn_name = args.function
    if fn_name is None:
        if args.run_dir is None:
            sys.stderr.write("error: function name or --run-dir required\n")
            return 2
        from c2_ext.runs import load_meta
        fn_name = load_meta(args.run_dir).function
    try:
        fi = info(project, fn_name, siblings_top=args.siblings)
    except KeyError as e:
        sys.stderr.write(f"{e}\n")
        return 1
    if args.json:
        print(json.dumps(fi.to_dict(), default=str))
    else:
        print(render_info_md(fi))
    return 0


def _cmd_stop(args, project) -> int:
    tc = project.toolchain()
    stop = getattr(tc, "stop_warm_container", None)
    if callable(stop):
        stop(args.run_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
