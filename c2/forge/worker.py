"""``python -m c2.forge.worker`` -- forge worker subprocess entry point.

Reads JSON-lines requests on stdin, writes JSON-lines replies on
stdout.  Everything else (warnings, exceptions, builder chatter) goes
to stderr; the parent reads stderr only on death.

The worker is **stateful** -- one container and one ForgeBuilder per
process lifetime.  Re-initialisation (different file / function) is
not supported; the parent should just spawn a fresh worker.

Protocol: see :mod:`c2.forge.pool`.
"""

from __future__ import annotations

import json
import os
import sys
import traceback
from dataclasses import asdict
from pathlib import Path


def _send(obj: dict) -> None:
    sys.stdout.write(json.dumps(obj) + "\n")
    sys.stdout.flush()


def _err(*msg) -> None:
    print(*msg, file=sys.stderr)


def main() -> int:
    os.environ["C2_FORGE_WORKER"] = "1"

    # Defer all heavy imports until after init -- gives the parent
    # snappy startup feedback even when imports are slow.
    builder = None
    ps = None
    target_file: str | None = None

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            _err(f"forge worker: bad json: {line!r}")
            continue

        op = req.get("op")
        if op == "init":
            try:
                from c2.forge import ps_ref
                from c2.forge.build import (
                    ForgeBuilder, PS_CFLAGS, PS_IMAGE,
                )
                cflags = req.get("cflags") or PS_CFLAGS
                image = req.get("image") or PS_IMAGE
                source_root = Path(req.get("source_root", "decomp"))
                builder = ForgeBuilder(
                    image=image, cflags=cflags, source_root=source_root,
                )
                builder.warm()
                # Stage the target TU once (subsequent compile_one calls
                # are stage-cached -- no per-variant copy).
                builder.stage(req["file"])
                target_file = req["file"]
                ps = ps_ref.load(req["function"])
                _send({"event": "warmed",
                       "container": builder._container or ""})
            except Exception as exc:                       # noqa: BLE001
                _err(traceback.format_exc())
                _send({"event": "error", "msg": str(exc)})
                return 1
            continue

        if op == "exit":
            break

        if op == "compile":
            vid = req["id"]
            file_text = req["file_text"]
            try:
                _do_compile(vid, file_text, builder, ps,
                            file=req.get("file") or target_file,
                            want_ledger=bool(req.get("want_ledger")))
            except Exception as exc:                       # noqa: BLE001
                _err(traceback.format_exc())
                _send({"id": vid, "ok": False, "error": str(exc),
                       "bytes": -1, "size": 0, "size_delta": 0,
                       "shape": {}})
            continue

        _err(f"forge worker: unknown op {op!r}")

    if builder is not None:
        builder.shutdown()
    return 0


def _do_compile(vid: str, file_text: str, builder, ps,
                file: str | None, want_ledger: bool = False) -> None:
    """Compile one variant + score it; send the result back."""
    from c2.forge.build import BuildError
    from c2.forge.judge import score
    from c2.forge.objcarve import FunctionNotInObj

    if not file:
        raise RuntimeError("worker: no target file staged")

    try:
        build = builder.compile_one(
            file=file, function=ps.name, source_text=file_text,
        )
    except BuildError as exc:
        _send({
            "id": vid, "ok": False,
            "error": f"build: {exc}",
            "build_output": exc.output[-800:],
            "bytes": -1, "size": 0, "size_delta": 0, "shape": {},
        })
        return
    except FunctionNotInObj as exc:
        _send({
            "id": vid, "ok": False,
            "error": f"missing: {exc}",
            "bytes": -1, "size": 0, "size_delta": 0, "shape": {},
        })
        return

    sc = score(ps, build.code, build.fixups,
               rc_line_marks=build.line_marks, want_ledger=want_ledger)
    reply = {
        "id": vid,
        "ok": sc.ok,
        "bytes": sc.bytes,
        "size": sc.size,
        "size_delta": sc.size_delta,
        "shape": sc.shape,
        "elapsed_ms": round(build.elapsed_ms, 1),
        "error": sc.error,
    }
    if want_ledger and sc.ledger is not None:
        reply["ledger"] = sc.ledger
    _send(reply)


if __name__ == "__main__":
    raise SystemExit(main())
