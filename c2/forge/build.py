"""Single-TU compile-only build pipeline for forge variants.

Critical-path module: every variant compile flows through here.  Hot
loop budget is ~250 ms per variant (warm container + ``wcc386
-fo=out.obj`` + OMF carve + score).

The contract is intentionally minimal::

    builder = ForgeBuilder(work_dir, image=PS_IMAGE, cflags=PS_CFLAGS)
    builder.warm()                       # start the container, once
    code, fixups = builder.compile_one(
        file="controls.c",
        function="show_menus",
        source_text=variant_text,
    )
    builder.shutdown()

No wlink.  No wmake.  No multi-TU walk.  Headers (``decomp/include``)
and unrelated TUs live behind read-only symlinks in ``work_dir/decomp/``
so a header change requires a fresh worker (forge restarts workers when
:meth:`needs_restart` reports true; for the common per-TU sweep we never
hit it).
"""

from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import tempfile
import time
import uuid
from dataclasses import dataclass, replace
from pathlib import Path

from c2.forge.objcarve import (
    FunctionNotInObj, carve, function_line_marks,
)


PS_IMAGE = "localhost/watcom-10.0a-wibo"
PS_CFLAGS = "-bt=dos -mf -4r -s -d1"

# The verifier's persistent build directory.  When ForgeBuilder is in
# ``le`` mode it stages every OTHER .obj from this directory into the
# worker's scratch tree so the wlink step finds them.  Required pre-
# condition for LE mode: the verifier must have built the project at
# least once (run ``c2 decomp-verify`` once before the experiment).
_VERIFIER_BUILD_DIR = Path(".c2-cache/build")


class BuildError(RuntimeError):
    """Variant did not compile.  ``output`` carries wcc386 diagnostics."""

    def __init__(self, msg: str, output: str = ""):
        super().__init__(msg)
        self.output = output


@dataclass
class BuildResult:
    """One variant's compile output (kept tiny -- no per-variant disasm)."""

    code: bytes
    fixups: frozenset[int]
    elapsed_ms: float
    obj_size: int
    line_marks: tuple[tuple[int, int], ...] = ()
    """The variant's -d1 LINNUM marks ``((rel_off, line), ...)`` read back
    from the .obj -- feeds the dual-marks run ledger in the judge."""


class ForgeBuilder:
    """Owns one scratch decomp tree + one warm podman container.

    The scratch tree is rebuilt at :meth:`__init__`-time as:

      * ``work/decomp/include`` symlinks to the real ``decomp/include``
      * ``work/decomp/lib``    symlinks to the real ``decomp/lib``
      * ``work/decomp/src``    is a flat directory containing a fresh
        copy of ONLY the target TU (others are absent -- we never
        compile them on the fast path)

    On every :meth:`compile_one` the target file is rewritten with the
    variant text and ``wcc386 <cflags> -fo=out.obj <file>`` runs in the
    warm container.  Total round-trip is ~200 ms once warm.
    """

    def __init__(self, *, image: str = PS_IMAGE, cflags: str = PS_CFLAGS,
                 keep_work: bool = False, source_root: Path | None = None,
                 mode: str = "le"):
        """
        ``mode``:
          * ``"le"`` (default) -- compile + WLINK the target.c with all
            other project .objs staged from ``.c2-cache/build/``.  The
            function's bytes come from the linked LE binary, so they
            match the verifier exactly.  Adds ~150 ms / variant (wlink),
            net ~400 ms / variant single-thread or ~120 ms amortised on
            4 cores.  Requires ``c2 decomp-verify`` to have run at
            least once to populate the build dir.
          * ``"omf"`` -- compile only, carve bytes from the pre-link
            .obj.  Faster (~250 ms / variant) but over-counts byte_diff
            on functions with many cross-module refs (the OMF FIXUPP
            set is wider than the LE fixup table).  Use ONLY for
            tight feedback loops where relative ordering matters more
            than absolute counts.
        """
        if mode not in ("le", "omf"):
            raise ValueError(f"mode must be 'le' or 'omf', got {mode!r}")
        self.image = image
        self.cflags = cflags
        self.mode = mode
        self.keep_work = keep_work
        self._source_root = source_root or Path("decomp")
        self.work: Path = Path(tempfile.mkdtemp(prefix="c2-forge-"))
        self._container: str | None = None
        self._shell: subprocess.Popen | None = None
        self._mounted_files: set[str] = set()
        self._prepare_tree()
        if mode == "le":
            self._stage_le_friends()

    def _prepare_tree(self) -> None:
        """Lay out the scratch tree as a FLAT directory.

        Mirrors the existing wmake build layout (.c2-cache/build/):
        all .c and .h files live at the work root so wcc386 sees them
        with no path -- which is the only way Watcom's DOS-style CLI
        accepts them (forward-slash paths get interpreted as switches
        like ``/bbarian.c`` -> ``Invalid option '/bbarian.c'``).

        Headers from ``decomp/include`` are hard-linked into the work
        dir up front (cheap; <8 files for PS).  The target .c file is
        staged on demand in :meth:`stage`.
        """
        self.work.mkdir(parents=True, exist_ok=True)
        src_root = self._source_root.resolve()
        inc = src_root / "include"
        if inc.is_dir():
            for h in inc.iterdir():
                if h.suffix.lower() in (".h", ".inc"):
                    dst = self.work / h.name
                    try:
                        dst.hardlink_to(h.resolve())
                    except OSError:
                        shutil.copy2(h, dst)

    def stage(self, file: str) -> Path:
        """Make ``file`` (a basename under ``decomp/src/``) available in
        the scratch root as a fresh copy (so per-variant rewrites do
        NOT alter the host source tree).  Idempotent.
        """
        scratch = self.work / file
        if file not in self._mounted_files:
            real = (self._source_root / "src" / file).resolve()
            if not real.exists():
                raise FileNotFoundError(real)
            shutil.copy2(real, scratch)
            self._mounted_files.add(file)
        return scratch

    def _stage_le_friends(self) -> None:
        """Hard-link every .obj from the verifier's build dir into the
        worker's scratch tree, MINUS the target's own .obj (we'll
        compile that fresh per variant).  Also stage clib3r.lib via
        the linker's LIBPATH directive (no copy needed; the image's
        installed Watcom tree handles it).
        """
        if not _VERIFIER_BUILD_DIR.is_dir():
            raise RuntimeError(
                "LE mode requires .c2-cache/build/ to be populated; "
                "run `c2 decomp-verify` once before the experiment, "
                "or pass mode='omf' to ForgeBuilder for a faster but "
                "less accurate path.")
        verifier_objs = sorted(_VERIFIER_BUILD_DIR.glob("*.obj"))
        if not verifier_objs:
            raise RuntimeError(
                f"no .obj files in {_VERIFIER_BUILD_DIR}; run "
                "`c2 decomp-verify` to populate them.")
        for obj in verifier_objs:
            dst = self.work / obj.name
            try:
                dst.hardlink_to(obj.resolve())
            except OSError:
                shutil.copy2(obj, dst)
        self._le_friend_objs = {o.name for o in verifier_objs}
        # Write the linker script once.  It will be re-used every
        # variant; per-variant the script doesn't change because the
        # .obj list is fixed.
        lnk = self.work / "forge.lnk"
        lnk_text = [
            "DEBUG ALL\n",
            "FORMAT os2 le\n",
            "OPTION QUIET\n",
            "OPTION MAP=out.map\n",
            "NAME out.exe\n",
            "LIBPATH Z:\\opt\\watcom\\lib386;"
            "Z:\\opt\\watcom\\lib386\\dos\n",
            "LIBRARY clib3r.lib\n",
        ]
        for obj in verifier_objs:
            lnk_text.append(f"FILE {obj.name}\n")
        lnk.write_text("".join(lnk_text))


    _SHELL_LOG = ".c2-shell.log"

    def warm(self) -> None:
        """Spin up the container with ``work`` mounted at ``/src``.

        The container's MAIN process is an interactive ``/bin/sh``
        reading our pipe (``podman run -i --rm``): every compile/link
        is a pipe write + sentinel read, never a fresh ``podman exec``
        (measured 2026-07-05: the exec path costs 220-1700 ms/call
        under parallel load -- runc/conmon fork + lock contention --
        while the wcc386 compile itself is 46-88 ms).

        Lifetime is tied to the PIPE: if this process dies for ANY
        reason (incl. SIGKILL) the kernel closes the pipe, sh reads
        EOF and exits, and ``--rm`` removes the container.  No
        orphaned containers by construction; the owner-pid label +
        ``reap_orphan_warm_containers`` stay as a second belt for a
        wedged podman.  Stuck compiles are killed IN-container by
        ``timeout`` so the shell survives them.
        """
        if self._shell is not None and self._shell.poll() is None:
            return
        from c2.commands.decomp_verify import reap_orphan_warm_containers
        reap_orphan_warm_containers()
        name = f"c2_forge_warm_{uuid.uuid4().hex[:12]}"
        self._shell = subprocess.Popen(
            ["podman", "run", "-i", "--rm", "--init",
             "--name", name,
             "--label", f"c2_owner_pid={os.getpid()}",
             "-v", f"{self.work.resolve()}:/src",
             "--workdir", "/src",
             "--entrypoint", "/bin/sh",
             self.image],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, text=True, bufsize=1,
        )
        self._container = name
        rc, _out, _ms = self._run("true", timeout=60)   # readiness probe
        if rc != 0:
            raise BuildError("forge container failed its readiness probe",
                             output=_out)

    def _run(self, cmd: str, timeout: float = 60.0) -> tuple[int, str, float]:
        """Run ``cmd`` in the container shell; return ``(rc, output, ms)``.

        The command is wrapped in an in-container ``timeout`` (shell
        survives stuck compilers; rc=124).  All command output goes to
        a log file in the bind mount and is read host-side -- only the
        sentinel travels the pipe, so compiler chatter can't desync
        the protocol.  A wedged SHELL (no sentinel within
        ``timeout``+10s) kills the container (EOF => --rm) and raises.
        """
        import select
        if self._shell is None or self._shell.poll() is not None:
            self._shell = None
            self.warm()
        proc = self._shell
        assert proc is not None and proc.stdin and proc.stdout
        self._seq = getattr(self, "_seq", 0) + 1
        sentinel = f"__C2RC_{self._seq}_"
        log = self.work / self._SHELL_LOG
        try:
            log.unlink(missing_ok=True)
        except OSError:
            pass
        t0 = time.perf_counter()
        try:
            proc.stdin.write(
                f"timeout {max(1, int(timeout))} /bin/sh -c "
                f"{shlex.quote(cmd)} > /src/{self._SHELL_LOG} 2>&1\n"
                f"echo {sentinel}$?\n")
            proc.stdin.flush()
        except BrokenPipeError as exc:
            self._shell = None
            raise RuntimeError(f"forge container shell died: {exc}")
        deadline = t0 + timeout + 10.0      # in-container timeout fires first
        while True:
            remain = deadline - time.perf_counter()
            if remain <= 0:
                self._kill_container()
                raise BuildError(
                    f"container shell wedged (> {timeout:.0f}s + grace)",
                    output=self._read_shell_log())
            r, _, _ = select.select([proc.stdout], [], [], remain)
            if not r:
                continue
            line = proc.stdout.readline()
            if not line:
                self._shell = None
                raise RuntimeError(
                    "forge container shell EOF (container gone?)")
            if line.startswith(sentinel):
                rc = int(line[len(sentinel):].strip() or "1")
                if rc == 124:
                    raise BuildError(
                        f"compile timed out in-container ({timeout:.0f}s)",
                        output=self._read_shell_log())
                return rc, self._read_shell_log(), \
                    (time.perf_counter() - t0) * 1000.0
            # anything else on the pipe is stray noise; ignore

    def _read_shell_log(self) -> str:
        try:
            return (self.work / self._SHELL_LOG).read_text(errors="replace")
        except OSError:
            return ""

    def _kill_container(self) -> None:
        if self._shell is not None:
            try:
                self._shell.kill()          # closes pipe -> sh EOF -> --rm
            except Exception:               # noqa: BLE001
                pass
            self._shell = None
        if self._container is not None:
            subprocess.run(["podman", "rm", "-f", self._container],
                           capture_output=True, timeout=15)

    def shutdown(self) -> None:
        if self._shell is not None:
            try:
                self._shell.stdin.close()   # EOF -> sh exits -> --rm
                self._shell.wait(timeout=5)
            except Exception:               # noqa: BLE001
                try:
                    self._shell.kill()
                except Exception:           # noqa: BLE001
                    pass
            self._shell = None
        if self._container is not None:
            subprocess.run(["podman", "rm", "-f", self._container],
                           capture_output=True, timeout=10)
            self._container = None
        if not self.keep_work:
            shutil.rmtree(self.work, ignore_errors=True)

    def __enter__(self) -> "ForgeBuilder":
        self.warm()
        return self

    def __exit__(self, *_exc) -> None:
        self.shutdown()


    def compile_one(
        self, *, file: str, function: str, source_text: str,
        timeout: int = 60,
    ) -> BuildResult:
        """Write ``source_text`` to ``work/decomp/src/<file>``, run
        ``wcc386 <cflags> -fo=out.obj <file>`` in the warm container,
        carve ``function`` from ``out.obj``, and return its bytes +
        fixups.  Raises :class:`BuildError` on compile failure or
        :class:`FunctionNotInObj` on a missing symbol.
        """
        if self._shell is None:
            self.warm()
        scratch = self.stage(file)
        # The host write is visible to the container immediately (bind
        # mount).  Use os.replace to give an atomic swap so a half-written
        # file can't be seen by a racing compile (defensive; the worker
        # is single-threaded by design).
        tmp = scratch.with_suffix(scratch.suffix + ".tmp")
        tmp.write_text(source_text)
        os.replace(tmp, scratch)

        # wcc386 is a DOS-era compiler: it parses forward-slashes as
        # switch prefixes (``/option``), so paths MUST be bare
        # basenames inside the cwd -- or use backslashes.  We mount
        # the scratch dir as ``/src`` (the wmake build uses the same
        # mount), so passing just the bare file name keeps wcc386 happy
        # and the .obj lands at ``/src/<stem>.obj`` on the host.
        stem = Path(file).stem
        rc, out, compile_ms = self._run(
            f"/usr/local/bin/watcom wcc386 {self.cflags} "
            f"-fo={stem}.obj {file}",
            timeout=timeout,
        )
        if rc != 0 or "Error!" in out or "error:" in out.lower():
            raise BuildError(
                f"wcc386 failed (rc={rc}) on {file}", output=out,
            )
        obj_host = self.work / f"{stem}.obj"
        if not obj_host.exists():
            raise BuildError(f"wcc386 produced no {stem}.obj", output=out)

        if self.mode == "omf":
            # Fast path -- bytes straight from the .obj.
            try:
                code, fixups = carve(obj_host, function)
            except FunctionNotInObj:
                raise
            return BuildResult(
                code=bytes(code),
                fixups=frozenset(fixups),
                elapsed_ms=compile_ms,
                obj_size=obj_host.stat().st_size,
                line_marks=function_line_marks(obj_host, function,
                                               len(code)),
            )

        # LE mode -- wlink the freshly-compiled .obj against all the
        # other project objs (staged by _stage_le_friends), then carve
        # the function from the linked LE binary using the same loader
        # the verifier uses.  Byte counts match the verifier exactly.
        res = self._wlink_and_carve(file=file, function=function,
                                    stem=stem, timeout=timeout,
                                    compile_ms=compile_ms,
                                    build_output=out)
        # The marks come from the .obj (function-relative offsets are
        # identical in the linked image; only fixup fields differ).
        return replace(res, line_marks=function_line_marks(
            obj_host, function, len(res.code)))

    def _wlink_and_carve(self, *, file: str, function: str, stem: str,
                         timeout: int, compile_ms: float,
                         build_output: str) -> BuildResult:
        """Link the freshly-compiled target.obj against the staged
        friends, then return the bytes + fixups for ``function`` carved
        from the resulting LE binary.
        """
        rc, out, link_ms = self._run(
            "/usr/local/bin/watcom wlink @forge.lnk", timeout=timeout)
        if rc != 0 or "Error!" in out:
            raise BuildError(
                f"wlink failed (rc={rc}) on {file}",
                output=build_output + "\n--- wlink ---\n" + out,
            )
        out_exe = self.work / "out.exe"
        if not out_exe.exists():
            raise BuildError("wlink produced no out.exe",
                             output=build_output + "\n" + out)
        # Carve the function from the LE binary.  Use the verifier's
        # own loader so the masking matches exactly.
        from c2.commands.decomp_verify import _load_le_code_and_fixups
        # Avoid the lru_cache: each variant produces a fresh out.exe
        # with the same path; the cache would return STALE bytes.
        # Bypass the cache by calling the underlying function with a
        # bumped mtime tuple.
        code_full, fixups_abs = _load_le_code_and_fixups.__wrapped__(
            str(out_exe), out_exe.stat().st_mtime_ns, out_exe.stat().st_size,
        ) if hasattr(_load_le_code_and_fixups, "__wrapped__") else \
            _load_le_code_and_fixups(out_exe)
        # Find the function in the linked binary via the .map file.
        # Carve a generous slice (up to 64 KB) so the consumer can
        # always trim to the same length the verifier reads: PS.EXE's
        # ``func_size`` (which often INCLUDES inter-function linker
        # padding the next-symbol-offset would miss).  judge.score()
        # truncates to len(PS.bytes_); that gives byte_diff parity
        # with the verifier.
        fn_off, _next_gap = self._fn_offset_in_le(stem, function)
        slice_end = min(fn_off + 0x10000, len(code_full))
        code = bytes(code_full[fn_off:slice_end])
        fixups = frozenset(
            f - fn_off for f in fixups_abs
            if fn_off <= f < slice_end
        )
        return BuildResult(
            code=code, fixups=fixups,
            elapsed_ms=compile_ms + link_ms,
            obj_size=out_exe.stat().st_size,
        )

    def _fn_offset_in_le(self, stem: str, function: str) -> tuple[int, int]:
        """Parse out.map to find ``function``'s offset + size in the
        linked LE binary's code section.  The map's segment-relative
        offset is exactly the offset into the code-section bytes that
        :func:`_load_le_code_and_fixups` returns.
        """
        import re
        map_path = self.work / "out.map"
        if not map_path.exists():
            raise BuildError(f"wlink wrote no map file")
        m_text = map_path.read_text()
        # The Watcom .map format puts the offset FIRST then the symbol:
        #     0001:000xxxxx  fn_name_
        # Where 0001 is the segment number (_TEXT) and xxxxxxx is the
        # offset within the code-section bytes returned by
        # _load_le_code_and_fixups (BEGTEXT + _TEXT, both in object 0).
        # The optional ``+`` after the offset marks library symbols;
        # ``*`` marks a symbol only referenced from debug info (e.g. a
        # function all of whose callers live in OTHER objs -- seen on
        # get_pm_from_actual / control_icons, 2026-07-09 audit).
        candidates = (function + "_", function)
        ordered: list[tuple[str, int]] = []
        for line in m_text.splitlines():
            m = re.match(
                r"\s*0001:([0-9a-fA-F]+)[+*]?\s+([A-Za-z_]\w*)", line)
            if m:
                ordered.append((m.group(2), int(m.group(1), 16)))
        if not ordered:
            raise BuildError("wlink map has no _TEXT symbols")
        ordered.sort(key=lambda x: x[1])
        for i, (name, off) in enumerate(ordered):
            if name in candidates:
                end = (ordered[i + 1][1] if i + 1 < len(ordered)
                       else off + 0x10000)             # last fn: 64 KB cap
                return off, end - off
        raise FunctionNotInObj(
            f"{function!r} not in {map_path}; "
            f"first {min(8, len(ordered))} symbols: "
            f"{[n for n, _ in ordered[:8]]}")


    def needs_restart(self, file: str) -> bool:
        """A worker should be restarted when the user touched a file
        that we have NOT staged (e.g. a header) -- because the warm
        container's mounted headers are now stale relative to the host.
        Currently a no-op (forge sweeps one TU per session); kept as a
        hook for the future CorpusForge driver."""
        return False
