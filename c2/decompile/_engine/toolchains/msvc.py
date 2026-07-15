"""MSVC 4.0 toolchain implementation.

The Windows analogue of :mod:`c2_ext.toolchains.watcom`.  Delegates to the
existing :mod:`c2.win_bytes` engine for the heavy lifting (CAESAR2.EXE PE
parsing, COFF object parsing, MSVC-in-podman compile invocation, masked
search), and adds the surface the rest of :mod:`c2_ext` expects:

* :meth:`function_info` / :meth:`function_bytes` / :meth:`function_fixups`
  -- via ``data/windows-builds/caesar2_symbols.json`` + CAESAR2.EXE's
  ``.text``.
* :meth:`existing_source` -- via the same brace-matcher the Watcom
  toolchain uses on ``decomp/src/<tu>.c``.
* :meth:`compile_scratch` -- builds a self-contained ``scratch.c`` with
  ``cl.exe`` inside the ``localhost/msvc-4.00-wibo`` container, parses
  the COFF output to extract the named function's bytes + relocations.
* :meth:`disassemble` -- capstone + symbol resolution via the windows
  symbol/globals maps.
* :meth:`byte_exact_functions` -- reads ``.c2-cache/win-verify.json``.

Cross-function elision normalization is a no-op for MSVC: CAESAR2.EXE was
built with ``/Od``, which does not tail-merge / shared-ret / fall-through
neighboring functions the way Watcom does.  The base-class default
pass-through :meth:`normalize_target` is used directly.
"""

from __future__ import annotations

import bisect
import json
import os
import re
import struct
import subprocess
import uuid
from functools import cached_property
from pathlib import Path
from typing import TYPE_CHECKING

import capstone

from c2.decompile._engine.toolchains.base import (
    CompileResult,
    FunctionInfo,
    Insn,
    Toolchain,
    register,
)
from c2.decompile._engine.toolchains.watcom import (
    _extract_function_body,
    _extract_signature,
    _is_reloc_insn,
    _replace_disp_in_op,
    _strip_leading_body_comments,
)

if TYPE_CHECKING:
    pass


# COFF I386 relocation type ids the .obj parser cares about.
_IMAGE_REL_I386_DIR32 = 6
_IMAGE_REL_I386_REL32 = 20


@register("msvc-4.0")
class MSVCToolchain(Toolchain):
    """MSVC 4.0 ``/Od``, targeting the Windows PE32 ``CAESAR2.EXE``."""

    DEFAULT_IMAGE = "localhost/msvc-4.00-wibo"
    # Cflags applied to every scratch compile.  The include-split compose
    # inlines only the TU's ORIGINAL header block; sibling prototypes are
    # provided by force-including the sandbox's own ``c2_funcs.h`` (same
    # as the project-level win build in ``c2.win_bytes``).  Without it,
    # call-before-definition sites implicitly declare ``int f()`` and
    # MSVC hard-errors (C2371) at every later ``void`` definition —
    # wcc386 tolerates that, so only the MSVC target needs the /FI.
    # The Watcom-specific calling-convention keywords are stripped via
    # ``-D`` so they parse as nothing.
    DEFAULT_CFLAGS: tuple[str, ...] = (
        "/nologo", "/c", "/Od", "/Zp1",
        "/FIc2_funcs.h",
        "/D__watcall=", "/D__pascal=", "/D__far=",
        "/D__near=", "/D__interrupt=", "/D__loadds=",
    )

    #  Caches (built once per instance)

    @cached_property
    def _sym_records(self) -> list[dict]:
        """Raw entries from caesar2_symbols.json (every function in CAESAR2.EXE)."""
        return json.loads(self.project.symbols_json.read_text())

    @cached_property
    def _name_to_record(self) -> dict[str, dict]:
        """ps_name \u2192 symbol record (only entries that have a ps_name)."""
        out: dict[str, dict] = {}
        for s in self._sym_records:
            ps = s.get("ps_name")
            if ps:
                out[ps] = s
        return out

    @cached_property
    def _sorted_records(self) -> list[tuple[int, dict]]:
        """(address, record) sorted by address \u2014 for nearest-symbol lookup."""
        rows = [(self._addr(s), s) for s in self._sym_records]
        rows.sort()
        return rows

    @cached_property
    def _func_addrs(self) -> list[int]:
        return [a for a, _ in self._sorted_records]

    @cached_property
    def _globals_records(self) -> list[dict]:
        path = self.project.globals_map
        if path is None or not path.is_file():
            return []
        return json.loads(path.read_text())

    @cached_property
    def _globals_index(self) -> tuple[list[int], list[str]]:
        rows = sorted(
            (int(g["win_va"], 16), g["name"]) for g in self._globals_records
        )
        if not rows:
            return [], []
        addrs, names = zip(*rows)
        return list(addrs), list(names)

    @cached_property
    def _win_image(self):
        """CAESAR2.EXE PE32 image (cached for the lifetime of the toolchain)."""
        from c2 import win_bytes as wb
        return wb.load_win_image(self.project.target_binary)

    @cached_property
    def _sources_by_basename(self) -> dict[str, Path]:
        return {p.name: p for p in self.project.sources_dir.glob("*.c")}

    @cached_property
    def _byte_exact_pool(self) -> frozenset[str]:
        cache = self.project.root / ".c2-cache" / "win-verify.json"
        if not cache.is_file():
            return frozenset()
        try:
            data = json.loads(cache.read_text())
        except (json.JSONDecodeError, OSError):
            return frozenset()
        return frozenset(
            f["name"] for f in data.get("functions", [])
            if f.get("status") == "exact"
        )

    #  Identity

    @property
    def _msvc_image(self) -> str:
        if self.project.toolchain_spec.compiler_image:
            return self.project.toolchain_spec.compiler_image
        return os.environ.get("C2_MSVC_IMAGE", self.DEFAULT_IMAGE)

    #  Helpers

    @staticmethod
    def _addr(s: dict) -> int:
        a = s["address"]
        return int(a, 16) if isinstance(a, str) else int(a)

    def _record_for(self, name: str) -> dict:
        rec = self._name_to_record.get(name)
        if rec is None:
            raise KeyError(f"function {name!r} not in {self.project.symbols_json}")
        return rec

    #  Toolchain interface: function metadata

    def function_info(self, name: str) -> FunctionInfo:
        rec = self._record_for(name)
        addr = self._addr(rec)
        size = int(rec.get("size", 0))
        source_file = rec.get("source")
        sig = None
        existing = self.existing_source(name)
        if existing:
            _, body_text = existing
            sig = _extract_signature(body_text)
        return FunctionInfo(
            name=name, address=addr, size=size,
            source_file=source_file, signature=sig,
        )

    def function_bytes(self, name: str) -> bytes:
        info = self.function_info(name)
        return self._win_image.func_bytes(info.address, info.size)

    def function_fixups(self, name: str) -> frozenset[int]:
        """No per-function relocation map in the PE shipping image.

        The CAESAR2.EXE we compare against is fully linked, so there are
        no symbolic fixups to strip on the TARGET side.  The verify
        layer still asks the *compiled scratch* for its own COFF fixups
        and uses that mask for diff classification, so call/data-disp
        bytes still don't count as real diffs.
        """
        return frozenset()

    def line_numbers(self, name: str) -> tuple[tuple[int, int], ...]:
        """CAESAR2.EXE was built without line-info we can recover; return ()."""
        return ()

    def resolve_data_ref(self, addr: int) -> tuple[str, int] | None:
        idx, names = self._globals_index
        if not idx:
            return None
        pos = bisect.bisect_right(idx, addr) - 1
        if pos < 0:
            return None
        d = addr - idx[pos]
        if 0 <= d <= 0x4000:
            return names[pos], d
        return None

    def resolve_code_ref(self, addr: int) -> tuple[str, int] | None:
        addrs = self._func_addrs
        if not addrs:
            return None
        pos = bisect.bisect_right(addrs, addr) - 1
        if pos < 0:
            return None
        rec = self._sorted_records[pos][1]
        base = self._addr(rec)
        name = rec.get("ps_name") or rec.get("ghidra_name")
        if name is None:
            return None
        return name, addr - base

    def existing_source(self, name: str) -> tuple[str, str] | None:
        """Lift ``name``'s function definition from its source TU.

        Uses ``c2.win_bytes.tu_of`` to discover which TU defines the
        function (works for ANY function in decomp/src, not just those
        with a CAESAR2.EXE mapping), then brace-matches the body.
        """
        # First trust the symbol record's `source` field; fall back to
        # tu_of() (a build-free column-0 scan over decomp/src).
        rec = self._name_to_record.get(name)
        tu_name = None
        if rec and rec.get("source"):
            tu_name = rec["source"]
            if not tu_name.endswith(".c"):
                tu_name = tu_name + ".c"
        if tu_name is None:
            from c2.win_bytes import tu_of
            tu = tu_of(name)
            if tu:
                tu_name = f"{tu}.c"
        if tu_name is None:
            return None
        src_path = self._sources_by_basename.get(tu_name)
        if src_path is None:
            return None
        text = src_path.read_text()
        body = _extract_function_body(text, name)
        if body is None:
            return None
        return tu_name, _strip_leading_body_comments(body)

    # MSVC 4.0 doesn't ship the Watcom DOS-specific headers (i86.h,
    # bios.h, dos.h, conio.h, ...), so we filter them out of any
    # bundled scratch.  The agent can re-add a header manually if the
    # compile errors on a missing prototype.
    _MSVC_HEADER_BLOCKLIST = frozenset({
        "i86.h", "bios.h", "dos.h", "conio.h", "io.h", "sys/types.h",
        "graph.h", "malloc.h",
    })

    def source_includes(self, source_file_name: str) -> list[str]:
        """Return the TU's stdlib ``#include`` lines that MSVC actually has."""
        src_path = self._sources_by_basename.get(source_file_name)
        if src_path is None:
            return []
        out: list[str] = []
        for line in src_path.read_text().splitlines():
            s = line.strip()
            if s.startswith("#include"):
                # Drop Watcom-specific headers MSVC doesn't ship.
                m = re.match(r'^#include\s*[<"]([^>"]+)[>"]', s)
                if m and m.group(1).lower() in self._MSVC_HEADER_BLOCKLIST:
                    continue
                out.append(s)
            elif s and not s.startswith("//") and not s.startswith("/*") \
                    and not s.startswith("*") and not s.startswith("#"):
                break
        return out

    #  Compilation via the msvc-4.00-wibo container

    def compile_scratch(self, run_dir: Path, function_name: str) -> CompileResult:
        scratch = run_dir / "scratch.c"
        if not scratch.is_file():
            return CompileResult(
                ok=False, stderr=f"scratch.c not found at {scratch}",
                function_bytes=None, fixup_offsets=frozenset(),
            )

        obj_name = f"scratch_{uuid.uuid4().hex[:8]}.obj"
        cflags = list(self.cflags) if self.cflags else list(self.DEFAULT_CFLAGS)
        cflags = list(cflags) + list(self.project.toolchain_spec.extra_defines)
        # The msvc-4.00-wibo container's entrypoint sits in /src by
        # convention (see data/windows-builds/ghidra-recreate.md +
        # c2.win_bytes._run_msvc); mounting the run dir there keeps
        # paths relative and avoids fighting the wibo entrypoint over
        # workdir handling.
        cmd = [
            "podman", "run", "--rm", "-v", f"{run_dir}:/src",
            self._msvc_image, "cl.exe",
            *cflags, f"/Fo{obj_name}", "scratch.c",
        ]
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        except subprocess.TimeoutExpired:
            return CompileResult(
                ok=False, stderr="msvc compiler timeout (120s)",
                function_bytes=None, fixup_offsets=frozenset(),
            )
        except FileNotFoundError as e:
            return CompileResult(
                ok=False, stderr=f"podman not found: {e}",
                function_bytes=None, fixup_offsets=frozenset(),
            )

        obj_path = run_dir / obj_name
        stderr = (r.stdout or "") + (r.stderr or "")
        if not obj_path.is_file():
            return CompileResult(
                ok=False, stderr=stderr.strip() or "compile produced no .obj",
                function_bytes=None, fixup_offsets=frozenset(),
            )
        obj_bytes = obj_path.read_bytes()
        try:
            obj_path.unlink()
        except OSError:
            pass

        text, funcs, reloc = _parse_coff(obj_bytes)
        match = next(
            ((i, n, s, e) for i, (n, s, e) in enumerate(funcs)
             if n == function_name or n == "_" + function_name),
            None,
        )
        if match is None:
            names = ", ".join(n for n, _s, _e in funcs[:20])
            return CompileResult(
                ok=False,
                stderr=f"function {function_name!r} not found in obj.\n"
                       f"Have: {names}\n{stderr}",
                function_bytes=None, fixup_offsets=frozenset(),
            )
        _i, _name, start, end = match
        code = text[start:end]
        mask = frozenset(o - start for o in reloc if start <= o < end)
        return CompileResult(
            ok=True, stderr=stderr.strip(),
            function_bytes=bytes(code), fixup_offsets=mask,
            line_marks=(),
        )

    #  Disassembly + symbol resolution

    @cached_property
    def _cs(self) -> capstone.Cs:
        cs = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
        cs.detail = True
        return cs

    def disassemble(
        self, code: bytes, base_addr: int,
        fixup_offsets: frozenset[int] | None = None,
    ) -> list[Insn]:
        out: list[Insn] = []
        fn_start = base_addr
        fn_end = base_addr + len(code)
        for ins in self._cs.disasm(code, base_addr):
            offset = ins.address - fn_start
            op_str = ins.op_str
            resolved = self._resolve_operands(ins, fn_start, fn_end)
            if resolved is not None:
                op_str = resolved

            is_reloc = _is_reloc_insn(ins)
            if not is_reloc and fixup_offsets:
                for k in range(ins.size):
                    if (offset + k) in fixup_offsets:
                        is_reloc = True
                        break

            out.append(Insn(
                offset=offset, size=ins.size, line=None, is_donor=False,
                mnemonic=ins.mnemonic, op_str=op_str,
                raw=bytes(ins.bytes), is_relocation=is_reloc,
            ))
        return out

    def _resolve_operands(
        self, ins: capstone.CsInsn, fn_start: int, fn_end: int,
    ) -> str | None:
        try:
            ops = list(ins.operands)
        except (AttributeError, capstone.CsError):
            return None

        # Calls / jumps with an immediate target.
        if ins.mnemonic in ("call", "jmp") or ins.mnemonic.startswith("j"):
            for op in ops:
                if op.type == capstone.x86.X86_OP_IMM:
                    target = op.value.imm
                    if fn_start <= target < fn_end:
                        return f".L_{target - fn_start:x}"
                    code_ref = self.resolve_code_ref(target)
                    if code_ref:
                        name, delta = code_ref
                        return name if delta == 0 else f"{name}+0x{delta:x}"
                    return None

        # Memory operands with an absolute DIR32 displacement.
        for op in ops:
            if op.type != capstone.x86.X86_OP_MEM:
                continue
            disp = op.value.mem.disp
            if disp == 0:
                continue
            # Only resolve when the displacement looks like an absolute VA
            # (inside CAESAR2.EXE's image base range).
            if not (0x00400000 <= (disp & 0xFFFFFFFF) <= 0x00700000):
                continue
            ref = self.resolve_data_ref(disp & 0xFFFFFFFF)
            if ref is None:
                continue
            name, delta = ref
            symbolic = name if delta == 0 else f"{name}+0x{delta:x}"
            return _replace_disp_in_op(ins.op_str, disp & 0xFFFFFFFF, symbolic)
        return None

    #  Embedding noise stripper

    def normalize_asm_for_embedding(self, asm_text: str) -> str:
        out_lines: list[str] = []
        for line in asm_text.splitlines():
            s = line
            s = re.sub(r"^\s*[+D]?\+?\d+\s+", "", s)
            s = re.sub(r"^\s*[0-9a-fA-F]+\s+", "", s)
            s = re.sub(r"^\s*([0-9a-fA-F]{2}\s)+\s+", "", s)
            s = re.sub(r"\.L_[0-9a-f]+", ".Lx", s)
            s = re.sub(r"\[[a-zA-Z_][a-zA-Z0-9_]*(\+0x[0-9a-fA-F]+)?\]", "[DATA]", s)
            s = re.sub(r"\[0x[0-9a-fA-F]+\]", "[DATA]", s)
            s = re.sub(r"\b0x[0-9a-fA-F]{3,}\b", "IMM", s)
            out_lines.append(s)
        return "\n".join(out_lines)

    #  Pool

    def byte_exact_functions(self) -> frozenset[str]:
        return self._byte_exact_pool


#  COFF parser (lifted from c2.win_bytes; kept self-contained so this
#  module doesn't reach across into the runtime there at import time).

def _parse_coff(obj: bytes) -> tuple[bytes, list[tuple[str, int, int]], set[int]]:
    nsec = struct.unpack_from("<H", obj, 2)[0]
    symptr, nsym = struct.unpack_from("<II", obj, 8)
    optsz = struct.unpack_from("<H", obj, 16)[0]
    so = 20 + optsz
    text = b""
    text_idx = None
    relptr = nrel = 0
    for i in range(nsec):
        b = so + i * 40
        nm = obj[b : b + 8].rstrip(b"\0")
        _vs, _va, rawsz, rawptr, rp = struct.unpack_from("<IIIII", obj, b + 8)
        nr = struct.unpack_from("<H", obj, b + 32)[0]
        if nm == b".text":
            text = obj[rawptr : rawptr + rawsz]
            text_idx, relptr, nrel = i + 1, rp, nr
            break
    if text_idx is None:
        return b"", [], set()

    reloc: set[int] = set()
    for r in range(nrel):
        va, _si, ty = struct.unpack_from("<IIH", obj, relptr + r * 10)
        if ty in (_IMAGE_REL_I386_DIR32, _IMAGE_REL_I386_REL32):
            reloc.update(range(va, va + 4))

    strtab = symptr + nsym * 18

    def symname(raw: bytes) -> str:
        if raw[:4] == b"\0\0\0\0":
            off = struct.unpack_from("<I", raw, 4)[0]
            end = obj.find(b"\0", strtab + off)
            return obj[strtab + off : end].decode("latin1")
        return raw.rstrip(b"\0").decode("latin1")

    fsyms: list[tuple[int, str]] = []
    i = 0
    while i < nsym:
        b = symptr + i * 18
        value, secnum, typ, sclass, naux = struct.unpack_from("<IhHBB", obj, b + 8)
        if secnum == text_idx and sclass == 2 and (typ & 0x20):
            fsyms.append((value, symname(obj[b : b + 8]).lstrip("_")))
        i += 1 + naux

    fsyms.sort()
    funcs: list[tuple[str, int, int]] = []
    for k, (val, name) in enumerate(fsyms):
        end = fsyms[k + 1][0] if k + 1 < len(fsyms) else len(text)
        funcs.append((name, val, end))
    return text, funcs, reloc
