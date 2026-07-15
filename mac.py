#!/usr/bin/env python3
"""mac.py -- pyghidra entry point for the Caesar II Mac PowerPC binary.

Pattern mirrors watcom10.0a/wcc.py:
  1. Environment auto-detected from ghidra-cli (full Ghidra install) +
     NIX_GHIDRAHOME (extension overlay).
  2. JVM started exactly once per process.  Env MUST be set on FIRST call.
  3. Coordinates: Mac PEF loads at 0x10000000 (code) + 0x100A9EB0..0x1014687F (data)
     + 0x10146880 IMPORTS.  r2 TOC base is auto-detected from PEF metadata.
  4. apply_knowledge() bakes our 246 globals, 1291 game function names AND
     ~960 function signatures from decomp/include/c2_funcs.h into the DB so
     the decompiler renders symbolic names with typed params and returns.

Workflow::

    import mac
    mac.open()                    # ~25s first run (import + analyze + label)
    print(mac.decompile("water_trouble"))         # raw Ghidra C
    print(mac.decompile_clean("water_trouble"))   # PEF indirection removed

The ``MacProject/`` directory is gitignored (large, rebuildable).  All naming
state lives in ``.c2-cache/mac/toc_names.fr.json`` (committed) and the
function signatures live in ``decomp/include/c2_funcs.h`` so the DB is fully
reproducible from PEF + those two files.

See ``c2 mac-decompile``, ``c2 mac-fn``, ``docs/mac-ghidra-decompile.md``,
``docs/cross-tu-prototype-audit.md``, and
``docs/signature-cleanups-mac-verified.md`` for the wider workflow.
"""
from __future__ import annotations
import os
import re
import shutil
import json
from pathlib import Path
from typing import Optional

REPO = Path(__file__).resolve().parent
PEF_PATH = REPO / 'MAC' / 'extracted' / 'French retail' / 'Caesar_II_1.0_fr.pef'
PROJECT_LOCATION = REPO / 'MacProject'
PROJECT_NAME = 'caesar2_mac'
PROGRAM_NAME = 'caesar2_mac'
TOC_NAMES_JSON = REPO / '.c2-cache' / 'mac' / 'toc_names.fr.json'
SIG_HEADER = REPO / 'decomp' / 'include' / 'c2_funcs.h'
RAW_CACHE = REPO / '.c2-cache' / 'mac' / 'decompile'

LANGUAGE_ID = 'PowerPC:BE:32:default'
COMPILER_SPEC_ID = 'macosx'

# Auto-detected at open() from the loaded program's r2 context register
TOC_BASE = None

# Memory layout (PEF loader places these)
CODE_BASE = 0x10000000
DATA_LO = 0x100A9EB0
DATA_HI = 0x1014687F
IMPORTS = 0x10146880

# module-level handles populated by open()
project = None
prog = None
flat = None
_decomp = None


def _detect_ghidra_env() -> tuple[str, str]:
    install = os.environ.get('GHIDRA_INSTALL_DIR')
    nixhome = os.environ.get('NIX_GHIDRAHOME')
    if install and nixhome:
        return install, nixhome
    wrap = shutil.which('ghidra-cli')
    if wrap:
        text = Path(os.path.realpath(wrap)).read_text(errors='ignore')
        if not install:
            m = re.search(r"GHIDRA_INSTALL_DIR='([^']+)'", text)
            install = m.group(1) if m else None
        if not nixhome:
            m = re.search(r"NIX_GHIDRAHOME='([^']+)'", text)
            nixhome = m.group(1) if m else None
    if not install:
        raise RuntimeError(
            'Could not determine GHIDRA_INSTALL_DIR.  Set it (full Ghidra install) '
            'and NIX_GHIDRAHOME (extension overlay) before importing mac.')
    return install, nixhome


def start(quiet: bool = True):
    """Start the JVM with the correct environment.  Idempotent within a process,
    but env MUST be right on the FIRST call.

    When ``quiet=True`` (default), suppress the Module manifest warnings that
    the Nix overlay's extension scanner spams to stdout.
    """
    install, nixhome = _detect_ghidra_env()
    os.environ['GHIDRA_INSTALL_DIR'] = install
    if nixhome:
        os.environ['NIX_GHIDRAHOME'] = nixhome
    import pyghidra
    if not pyghidra.started():
        if quiet:
            # Ghidra writes "Module manifest file error ..." to stdout during
            # the initial JVM bootstrap when the Nix extension overlay's
            # ghidra-mcp-plugin/Module.manifest carries shell-export-style
            # variables that the parser rejects.  Harmless but noisy.
            buf = os.dup(1)
            try:
                devnull = os.open(os.devnull, os.O_WRONLY)
                os.dup2(devnull, 1)
                os.close(devnull)
                pyghidra.start(verbose=False)
            finally:
                os.dup2(buf, 1)
                os.close(buf)
        else:
            pyghidra.start(verbose=False)
    return pyghidra


def open(analyze_if_missing: bool = True):
    """Open the Mac project, returning a FlatProgramAPI.
    Populates module globals ``project``, ``prog``, ``flat``, ``TOC_BASE``."""
    global project, prog, flat, TOC_BASE
    start()
    from ghidra.base.project import GhidraProject
    from ghidra.program.flatapi import FlatProgramAPI
    from ghidra.framework.model import ProjectLocator

    loc = ProjectLocator(str(PROJECT_LOCATION), PROJECT_NAME)
    if not loc.exists():
        if not analyze_if_missing:
            raise FileNotFoundError(f'project not found: {loc}')
        return _import_and_analyze()
    project = GhidraProject.openProject(str(PROJECT_LOCATION), PROJECT_NAME, True)
    prog = project.openProgram('/', PROGRAM_NAME, False)
    flat = FlatProgramAPI(prog)
    TOC_BASE = _read_toc_base()
    return flat


def _read_toc_base() -> Optional[int]:
    """Read r2 base from any function's context register (set by PEF loader)."""
    lang = prog.getLanguage()
    r2 = lang.getRegister('r2')
    pc = prog.getProgramContext()
    fm = prog.getFunctionManager()
    for f in fm.getFunctions(True):
        val = pc.getValue(r2, f.getEntryPoint(), False)
        if val is not None:
            return int(val.longValue() if hasattr(val, 'longValue') else val)
    return None


def _import_and_analyze():
    global project, prog, flat, TOC_BASE
    from ghidra.base.project import GhidraProject
    from ghidra.program.util import DefaultLanguageService
    from ghidra.program.model.lang import LanguageID, CompilerSpecID
    from ghidra.program.flatapi import FlatProgramAPI
    from ghidra.app.plugin.core.analysis import AutoAnalysisManager
    from ghidra.util.task import ConsoleTaskMonitor
    from java.io import File as JFile

    PROJECT_LOCATION.mkdir(parents=True, exist_ok=True)
    project = GhidraProject.createProject(str(PROJECT_LOCATION), PROJECT_NAME, False)

    svc = DefaultLanguageService.getLanguageService()
    lang = svc.getLanguage(LanguageID(LANGUAGE_ID))
    cspec = lang.getCompilerSpecByID(CompilerSpecID(COMPILER_SPEC_ID))

    prog = project.importProgram(JFile(str(PEF_PATH)), lang, cspec)
    project.saveAs(prog, '/', PROGRAM_NAME, True)
    project.close()

    # Reopen for analysis
    project = GhidraProject.openProject(str(PROJECT_LOCATION), PROJECT_NAME, True)
    prog = project.openProgram('/', PROGRAM_NAME, False)
    flat = FlatProgramAPI(prog)

    tx = prog.startTransaction('autoanalyze')
    try:
        mgr = AutoAnalysisManager.getAnalysisManager(prog)
        mgr.initializeOptions()
        mgr.reAnalyzeAll(None)
        mgr.startAnalysis(ConsoleTaskMonitor())
    finally:
        prog.endTransaction(tx, True)

    TOC_BASE = _read_toc_base()
    apply_knowledge()
    save()
    return flat


# ── apply_knowledge: stripping, labelling, typing, signing ─────────────────


def _ghidra_dt_for(info, prog, type_map):
    """Map an (extract_type_info-shaped) dict to a Ghidra DataType."""
    from ghidra.program.model.data import PointerDataType, VoidDataType
    base = type_map.get(info.get('base_type'))
    if base is None:
        base = VoidDataType.dataType
    dt = base
    for _ in range(info.get('pointer_levels', 0)):
        dt = PointerDataType(dt)
    return dt


def _extract_type_info(typ):
    """Walk a pycparser type chain into a structured dict."""
    import pycparser.c_ast as ca
    info = {'pointer_levels': 0, 'is_array': False, 'array_size': None,
            'base_type': None}
    cur = typ
    while True:
        if isinstance(cur, ca.PtrDecl):
            info['pointer_levels'] += 1
            cur = cur.type
        elif isinstance(cur, ca.ArrayDecl):
            info['is_array'] = True
            cur = cur.type
        elif isinstance(cur, ca.TypeDecl):
            cur = cur.type
        elif isinstance(cur, ca.IdentifierType):
            info['base_type'] = ' '.join(cur.names)
            break
        elif isinstance(cur, (ca.Struct, ca.Union)):
            info['base_type'] = f'{type(cur).__name__.lower()} {cur.name or "<anon>"}'
            break
        else:
            info['base_type'] = type(cur).__name__
            break
    return info


def _load_signatures():
    """Parse decomp/include/c2_funcs.h into a name -> pycparser.Decl map."""
    import sys
    sys.path.insert(0, str(REPO))
    from c2.commands.c_source import parse_c
    import pycparser.c_ast as ca
    ast = parse_c(SIG_HEADER.read_text(), filename='c2_funcs.h')
    sigs = {}
    for node in ast.ext:
        if isinstance(node, ca.Decl) and node.name and isinstance(node.type, ca.FuncDecl):
            sigs[node.name] = node
    return sigs


def apply_knowledge(save_after: bool = True) -> dict:
    """Bake the curated naming + signature knowledge into the Ghidra DB:

      * Strip CodeWarrior `.` prefix from function names
      * Label TOC slots as `_NAME` and the pointed-to globals as `NAME`
      * Type TOC slots as `int *` and globals as `int`
      * Apply function signatures from decomp/include/c2_funcs.h

    Idempotent.  Returns a stats dict.
    """
    import pycparser.c_ast as ca
    from java.util import ArrayList
    from ghidra.program.model.symbol import SourceType
    from ghidra.program.model.data import (
        PointerDataType, IntegerDataType, CharDataType, UnsignedCharDataType,
        SignedCharDataType, ShortDataType, UnsignedShortDataType, VoidDataType,
        UnsignedIntegerDataType, LongDataType, FloatDataType,
    )
    from ghidra.program.model.listing import (
        ParameterImpl, ReturnParameterImpl, Function,
    )
    from pycparser import c_generator
    gen = c_generator.CGenerator()

    if TOC_BASE is None:
        raise RuntimeError('TOC_BASE unknown -- call open() first')
    if not TOC_NAMES_JSON.exists():
        raise FileNotFoundError(f'{TOC_NAMES_JSON}')
    toc_map = json.loads(TOC_NAMES_JSON.read_text())

    fm = prog.getFunctionManager()
    st = prog.getSymbolTable()
    listing = prog.getListing()
    mem = prog.getMemory()
    dtm = prog.getDataTypeManager()

    int_dt = dtm.getDataType('/int') or IntegerDataType.dataType
    uint_dt = dtm.getDataType('/uint') or UnsignedIntegerDataType.dataType
    char_dt = dtm.getDataType('/char') or CharDataType.dataType
    uchar_dt = dtm.getDataType('/uchar') or UnsignedCharDataType.dataType
    schar_dt = SignedCharDataType.dataType
    short_dt = dtm.getDataType('/short') or ShortDataType.dataType
    ushort_dt = dtm.getDataType('/ushort') or UnsignedShortDataType.dataType
    long_dt = dtm.getDataType('/long') or LongDataType.dataType
    void_dt = VoidDataType.dataType
    float_dt = FloatDataType.dataType
    int_ptr_dt = PointerDataType(int_dt)
    type_map = {
        'int': int_dt, 'signed int': int_dt, 'signed': int_dt,
        'unsigned int': uint_dt, 'unsigned': uint_dt,
        'char': char_dt,
        'unsigned char': uchar_dt,
        'signed char': schar_dt,
        'short': short_dt, 'signed short': short_dt, 'short int': short_dt,
        'unsigned short': ushort_dt, 'unsigned short int': ushort_dt,
        'long': long_dt, 'signed long': long_dt,
        'unsigned long': uint_dt,    # 32-bit ABI
        'void': void_dt,
        'float': float_dt,
    }
    FunctionUpdateType = Function.FunctionUpdateType

    stats = {'stripped_dots': 0, 'labeled_slots': 0, 'labeled_globals': 0,
             'typed_slots': 0, 'typed_globals': 0,
             'sig_applied': 0, 'sig_failed': 0}

    sigs = _load_signatures()

    tx = prog.startTransaction('apply mac knowledge')
    try:
        # 1. Strip '.' prefix from CodeWarrior function names
        for f in fm.getFunctions(True):
            n = f.getName()
            if n.startswith('.') and len(n) > 1 and not n.startswith('._'):
                try:
                    f.setName(n[1:], SourceType.USER_DEFINED)
                    stats['stripped_dots'] += 1
                except Exception:
                    pass

        # 2. Label TOC slots + globals; type them
        for toc_off_str, pc_name in toc_map.items():
            toc_off = int(toc_off_str)
            slot_addr_int = TOC_BASE + toc_off
            try:
                slot_addr = flat.toAddr(slot_addr_int)
            except Exception:
                continue
            try:
                b = [mem.getByte(flat.toAddr(slot_addr_int + i)) & 0xff for i in range(4)]
            except Exception:
                continue
            global_addr_int = b[0] << 24 | b[1] << 16 | b[2] << 8 | b[3]
            if not (CODE_BASE <= global_addr_int < IMPORTS + 0x10000):
                continue
            try:
                global_addr = flat.toAddr(global_addr_int)
            except Exception:
                continue
            try:
                flat.createLabel(slot_addr, f'_{pc_name}', True, SourceType.USER_DEFINED)
                stats['labeled_slots'] += 1
            except Exception:
                pass
            try:
                flat.createLabel(global_addr, pc_name, True, SourceType.USER_DEFINED)
                stats['labeled_globals'] += 1
            except Exception:
                pass
            try:
                listing.clearCodeUnits(slot_addr, slot_addr.add(3), False)
                listing.createData(slot_addr, int_ptr_dt)
                stats['typed_slots'] += 1
            except Exception:
                pass
            try:
                listing.clearCodeUnits(global_addr, global_addr.add(3), False)
                listing.createData(global_addr, int_dt)
                stats['typed_globals'] += 1
            except Exception:
                pass

        # 3. Apply function signatures
        for f in fm.getFunctions(True):
            name = f.getName()
            if name not in sigs:
                continue
            decl = sigs[name]
            try:
                fdecl = decl.type
                ret_info = _extract_type_info(fdecl.type)
                ret_dt = _ghidra_dt_for(ret_info, prog, type_map)
                params_list = ArrayList()
                if fdecl.args:
                    for p in fdecl.args.params:
                        if isinstance(p, ca.Typename):
                            s = gen.visit(p).strip()
                            if s == 'void':
                                continue
                            p_info = _extract_type_info(p.type)
                            params_list.add(
                                ParameterImpl(None, _ghidra_dt_for(p_info, prog, type_map), prog)
                            )
                        elif isinstance(p, ca.Decl):
                            p_info = _extract_type_info(p.type)
                            params_list.add(
                                ParameterImpl(
                                    p.name or 'arg',
                                    _ghidra_dt_for(p_info, prog, type_map),
                                    prog,
                                )
                            )
                ret_param = ReturnParameterImpl(ret_dt, prog)
                f.updateFunction(
                    None,                                            # cconv unchanged
                    ret_param, params_list,
                    FunctionUpdateType.DYNAMIC_STORAGE_FORMAL_PARAMS,
                    True,                                            # force
                    SourceType.USER_DEFINED,
                )
                stats['sig_applied'] += 1
            except Exception:
                stats['sig_failed'] += 1
    finally:
        prog.endTransaction(tx, True)

    if save_after:
        save()
    return stats


def save():
    """Persist the program back into the project."""
    df = prog.getDomainFile()
    if df is not None and df.getParent() is not None:
        project.save(prog)
    else:
        project.saveAs(prog, '/', PROGRAM_NAME, True)


def addr(x: int):
    return prog.getAddressFactory().getDefaultAddressSpace().getAddress(x)


def func(name_or_addr):
    """Resolve a function by name or virtual address."""
    fm = prog.getFunctionManager()
    if isinstance(name_or_addr, int):
        a = addr(name_or_addr)
        return fm.getFunctionContaining(a) or fm.getFunctionAt(a)
    for f in fm.getFunctions(True):
        if f.getName() == name_or_addr:
            return f
    return None


def decompile(x, timeout: int = 60) -> str:
    """Decompile a function by name or address.  Returns raw Ghidra C source."""
    global _decomp
    from ghidra.app.decompiler import DecompInterface
    from ghidra.util.task import ConsoleTaskMonitor
    f = x if hasattr(x, 'getEntryPoint') else func(x)
    if f is None:
        raise ValueError(f'no function: {x!r}')
    if _decomp is None:
        _decomp = DecompInterface()
        _decomp.openProgram(prog)
    res = _decomp.decompileFunction(f, timeout, ConsoleTaskMonitor())
    return res.getDecompiledFunction().getC()


def decompile_cached(name: str, timeout: int = 60) -> Optional[str]:
    """Disk-cached Mac decompile (mirrors ``c2win.decompile_cached``).

    Cache hit returns instantly (no JVM).  Cache miss opens the project,
    decompiles, and persists the RAW Ghidra C for next time.  An empty cache
    file records a known-miss (function absent from the Mac build) -> None,
    so a subsequent ``decompile_clean`` can report absence without re-querying.
    """
    cache = RAW_CACHE / f'{name}.c'
    if cache.exists():
        txt = cache.read_text()
        return txt or None
    try:
        if prog is None:
            open()
        text = '' if func(name) is None else decompile(name, timeout)
    except Exception:
        return None
    try:
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(text)
    except OSError:
        pass
    return text or None


def decompile_clean(x, timeout: int = 60) -> str:
    """Decompile then run the AST-based PEF-indirection cleaner.

    When ``x`` is a name the raw decompile is fetched via ``decompile_cached``
    (cache-or-fetch: instant on a cache hit, opens the JVM only on a miss).
    Returns the cleaned source, or falls back to the raw text if AST parsing
    fails (with a leading comment explaining why).  Raises ``ValueError`` if
    ``x`` names a function absent from the Mac build (callers may pre-check
    with ``func``).
    """
    from c2.mac.clean import clean_decompile, known_globals
    if isinstance(x, str):
        raw = decompile_cached(x, timeout)
        if raw is None:
            raise ValueError(f'no Mac function: {x!r}')
    else:
        raw = decompile(x, timeout)
    cleaned, err = clean_decompile(raw, known_globals())
    if cleaned is None:
        return f"/* clean_decompile failed: {err} -- raw output follows */\n{raw}"
    return cleaned


def close():
    """Close the project handle (single-writer DB)."""
    global project, prog, flat
    if project is not None:
        project.close()
    project = prog = flat = None
