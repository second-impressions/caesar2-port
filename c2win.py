#!/usr/bin/env python3
"""c2win.py -- pyghidra entry point for the Caesar II Windows binary CAESAR2.EXE.

Sibling of ``mac.py`` (Mac PPC) -- same pattern, for the MSVC 4.0 Win95 build
(the matching-decompilation cousin of the DOS Watcom PS.EXE; see
``docs/windows-builds-fingerprint.md``).

The Ghidra project is **disposable**; all naming/typing knowledge lives in
committed files and is re-baked by ``apply_knowledge()``:

  * ``data/windows-builds/func-map.json``   -- 1187 PS function names -> win VA
  * ``data/windows-builds/globals-map.json``-- 1079 global names -> win VA
  * ``decomp/include/c2_data.h``            -- global *types*
  * ``decomp/include/c2_funcs.h``           -- function signatures (params+types)

Workflow::

    import c2win
    c2win.open()                       # ~60s first run (import + analyze + label)
    print(c2win.decompile("city_pop_limit_10_to_1"))

The binary is build A (sha256 caca2babb57d9450...), the closest Windows build
to the -d1 PS.EXE.  See ``data/windows-builds/ghidra-recreate.md``.
"""
from __future__ import annotations
import os
import re
import json
from pathlib import Path
from typing import Optional

REPO = Path(__file__).resolve().parent
EXE_PATH = REPO / 'data' / 'windows-builds' / 'named' / 'caesar2_A_1044480.exe'
PROJECT_LOCATION = REPO / 'C2WinProject'
PROJECT_NAME = 'caesar2_win'
PROGRAM_NAME = 'CAESAR2.EXE'

FUNC_MAP = REPO / 'data' / 'windows-builds' / 'func-map.json'
GLOBALS_MAP = REPO / 'data' / 'windows-builds' / 'globals-map.json'
DATA_HEADER = REPO / 'decomp' / 'include' / 'c2_data.h'
SIG_HEADER = REPO / 'decomp' / 'include' / 'c2_funcs.h'

LANGUAGE_ID = 'x86:LE:32:default'
COMPILER_SPEC_ID = 'windows'

project = None
prog = None
flat = None
_decomp = None


def _detect_ghidra_env():
    import shutil
    install = os.environ.get('GHIDRA_INSTALL_DIR')
    nixhome = os.environ.get('NIX_GHIDRAHOME')
    if install and nixhome:
        return install, nixhome
    wrap = shutil.which('ghidra-cli')
    if wrap:
        text = Path(os.path.realpath(wrap)).read_text(errors='ignore')
        if not install:
            m = re.search(r"GHIDRA_INSTALL_DIR='([^']+)'", text)
            install = m.group(1) if m else install
        if not nixhome:
            m = re.search(r"NIX_GHIDRAHOME='([^']+)'", text)
            nixhome = m.group(1) if m else nixhome
    if not install:
        raise RuntimeError('Set GHIDRA_INSTALL_DIR (+NIX_GHIDRAHOME) before importing c2win.')
    return install, nixhome


def start(quiet: bool = True):
    install, nixhome = _detect_ghidra_env()
    os.environ['GHIDRA_INSTALL_DIR'] = install
    if nixhome:
        os.environ['NIX_GHIDRAHOME'] = nixhome
    import pyghidra
    if not pyghidra.started():
        if quiet:
            buf = os.dup(1)
            try:
                dn = os.open(os.devnull, os.O_WRONLY); os.dup2(dn, 1); os.close(dn)
                pyghidra.start(verbose=False)
            finally:
                os.dup2(buf, 1); os.close(buf)
        else:
            pyghidra.start(verbose=False)
    return pyghidra


def open(analyze_if_missing: bool = True):
    global project, prog, flat
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
    return flat


def _import_and_analyze():
    global project, prog, flat
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
    prog = project.importProgram(JFile(str(EXE_PATH)), lang, cspec)
    project.saveAs(prog, '/', PROGRAM_NAME, True)
    project.close()

    project = GhidraProject.openProject(str(PROJECT_LOCATION), PROJECT_NAME, True)
    prog = project.openProgram('/', PROGRAM_NAME, False)
    flat = FlatProgramAPI(prog)
    tx = prog.startTransaction('autoanalyze')
    try:
        mgr = AutoAnalysisManager.getAnalysisManager(prog)
        mgr.initializeOptions(); mgr.reAnalyzeAll(None)
        mgr.startAnalysis(ConsoleTaskMonitor())
    finally:
        prog.endTransaction(tx, True)
    apply_knowledge()
    save()
    return flat


def addr(x: int):
    return prog.getAddressFactory().getDefaultAddressSpace().getAddress(x)


# ── type parsing (shared shape with mac.py) ────────────────────────────────

def _extract_type_info(typ):
    import pycparser.c_ast as ca
    info = {'pointer_levels': 0, 'is_array': False, 'base_type': None}
    cur = typ
    while True:
        if isinstance(cur, ca.PtrDecl):
            info['pointer_levels'] += 1; cur = cur.type
        elif isinstance(cur, ca.ArrayDecl):
            info['is_array'] = True; cur = cur.type
        elif isinstance(cur, ca.TypeDecl):
            cur = cur.type
        elif isinstance(cur, ca.IdentifierType):
            info['base_type'] = ' '.join(cur.names); break
        elif isinstance(cur, (ca.Struct, ca.Union)):
            info['base_type'] = f'{type(cur).__name__.lower()} {cur.name or "anon"}'; break
        else:
            info['base_type'] = type(cur).__name__; break
    return info


def _build_type_map():
    from ghidra.program.model.data import (
        PointerDataType, IntegerDataType, CharDataType, UnsignedCharDataType,
        SignedCharDataType, ShortDataType, UnsignedShortDataType, VoidDataType,
        UnsignedIntegerDataType, LongDataType, FloatDataType,
    )
    dtm = prog.getDataTypeManager()
    g = lambda p, d: dtm.getDataType(p) or d
    int_dt = g('/int', IntegerDataType.dataType)
    uint_dt = g('/uint', UnsignedIntegerDataType.dataType)
    char_dt = g('/char', CharDataType.dataType)
    uchar_dt = g('/uchar', UnsignedCharDataType.dataType)
    short_dt = g('/short', ShortDataType.dataType)
    ushort_dt = g('/ushort', UnsignedShortDataType.dataType)
    long_dt = g('/long', LongDataType.dataType)
    return {
        'int': int_dt, 'signed int': int_dt, 'signed': int_dt,
        'unsigned int': uint_dt, 'unsigned': uint_dt,
        'char': char_dt, 'unsigned char': uchar_dt,
        'signed char': SignedCharDataType.dataType,
        'short': short_dt, 'short int': short_dt, 'signed short': short_dt,
        'unsigned short': ushort_dt, 'unsigned short int': ushort_dt,
        'long': long_dt, 'signed long': long_dt, 'unsigned long': uint_dt,
        'void': VoidDataType.dataType, 'float': FloatDataType.dataType,
    }, int_dt, VoidDataType.dataType


def _dt_for(info, type_map, void_dt):
    from ghidra.program.model.data import PointerDataType
    dt = type_map.get(info.get('base_type'), void_dt)
    for _ in range(info.get('pointer_levels', 0)):
        dt = PointerDataType(dt)
    return dt


def _load_global_types():
    """name -> _extract_type_info dict, parsed from c2_data.h externs."""
    import sys; sys.path.insert(0, str(REPO))
    from c2.commands.c_source import parse_c
    import pycparser.c_ast as ca
    ast = parse_c(DATA_HEADER.read_text(), filename='c2_data.h')
    out = {}
    for node in ast.ext:
        if isinstance(node, ca.Decl) and node.name and not isinstance(node.type, ca.FuncDecl):
            out[node.name] = _extract_type_info(node.type)
    return out


def _load_signatures():
    import sys; sys.path.insert(0, str(REPO))
    from c2.commands.c_source import parse_c
    import pycparser.c_ast as ca
    ast = parse_c(SIG_HEADER.read_text(), filename='c2_funcs.h')
    return {n.name: n for n in ast.ext
            if isinstance(n, ca.Decl) and n.name and isinstance(n.type, ca.FuncDecl)}


def apply_knowledge(save_after: bool = True) -> dict:
    """Bake function names, global names+types, and signatures into the DB."""
    import pycparser.c_ast as ca
    from java.util import ArrayList
    from ghidra.program.model.symbol import SourceType
    from ghidra.program.model.listing import ParameterImpl, ReturnParameterImpl, Function
    from pycparser import c_generator
    gen = c_generator.CGenerator()

    fm = prog.getFunctionManager()
    listing = prog.getListing()
    type_map, int_dt, void_dt = _build_type_map()
    FUT = Function.FunctionUpdateType
    stats = dict(funcs=0, globals=0, globals_typed=0, sigs=0, sig_fail=0)

    func_map = json.loads(FUNC_MAP.read_text())
    globals_map = json.loads(GLOBALS_MAP.read_text())
    gtypes = _load_global_types()
    sigs = _load_signatures()

    tx = prog.startTransaction('apply c2win knowledge')
    try:
        # 1. function names
        for r in func_map:
            a = addr(int(r['win_va'], 16))
            f = fm.getFunctionAt(a)
            if f is None:
                continue
            try:
                f.setName(r['ps_name'], SourceType.USER_DEFINED); stats['funcs'] += 1
            except Exception:
                pass
        # 2. globals: label + type
        for g in globals_map:
            a = addr(int(g['win_va'], 16)); nm = g['name']
            try:
                flat.createLabel(a, nm, True, SourceType.USER_DEFINED); stats['globals'] += 1
            except Exception:
                pass
            info = gtypes.get(nm)
            if info and not info.get('is_array'):     # scalars/pointers only (arrays need element count)
                dt = _dt_for(info, type_map, void_dt)
                try:
                    listing.clearCodeUnits(a, a.add(dt.getLength() - 1), False)
                    listing.createData(a, dt); stats['globals_typed'] += 1
                except Exception:
                    pass
        # 3. function signatures (params + types)
        for f in fm.getFunctions(True):
            decl = sigs.get(f.getName())
            if decl is None:
                continue
            try:
                fdecl = decl.type
                ret_dt = _dt_for(_extract_type_info(fdecl.type), type_map, void_dt)
                params = ArrayList()
                if fdecl.args:
                    for p in fdecl.args.params:
                        if isinstance(p, ca.Typename):
                            if gen.visit(p).strip() == 'void':
                                continue
                            params.add(ParameterImpl(None, _dt_for(_extract_type_info(p.type), type_map, void_dt), prog))
                        elif isinstance(p, ca.Decl):
                            params.add(ParameterImpl(p.name or 'arg', _dt_for(_extract_type_info(p.type), type_map, void_dt), prog))
                f.updateFunction(None, ReturnParameterImpl(ret_dt, prog), params,
                                 FUT.DYNAMIC_STORAGE_FORMAL_PARAMS, True, SourceType.USER_DEFINED)
                stats['sigs'] += 1
            except Exception:
                stats['sig_fail'] += 1
    finally:
        prog.endTransaction(tx, True)
    if save_after:
        save()
    return stats


def save():
    df = prog.getDomainFile()
    if df is not None and df.getParent() is not None:
        project.save(prog)
    else:
        project.saveAs(prog, '/', PROGRAM_NAME, True)


def func(name_or_addr):
    fm = prog.getFunctionManager()
    if isinstance(name_or_addr, int):
        a = addr(name_or_addr); return fm.getFunctionContaining(a) or fm.getFunctionAt(a)
    for f in fm.getFunctions(True):
        if f.getName() == name_or_addr:
            return f
    return None


def decompile(x, timeout: int = 60) -> str:
    global _decomp
    from ghidra.app.decompiler import DecompInterface
    from ghidra.util.task import ConsoleTaskMonitor
    f = x if hasattr(x, 'getEntryPoint') else func(x)
    if f is None:
        raise ValueError(f'no function: {x!r}')
    if _decomp is None:
        _decomp = DecompInterface(); _decomp.openProgram(prog)
    res = _decomp.decompileFunction(f, timeout, ConsoleTaskMonitor())
    return res.getDecompiledFunction().getC()


RAW_CACHE = REPO / '.c2-cache' / 'win' / 'decompile'


def decompile_cached(name: str, timeout: int = 60) -> Optional[str]:
    """Disk-cached Windows decompile -- the shared cache-or-fetch primitive
    (mirrors ``mac.decompile_cached``).  Returns None when the function is
    absent from the Windows build (recorded as an empty cache file).  Opens the
    JVM/project only on a cache miss."""
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


def close():
    global project, prog, flat
    if project is not None:
        project.close()
    project = prog = flat = None
