"""Guard-vocabulary lint for cross-build conditional compilation.

Version-specific differences between the DOS release and the Windows
build-A witness must be guarded by the target/feature macros from
``include/c2_target.h`` — never by raw compiler macros, which conflate
"which compiler" with "which build of the game".  ``__WATCOMC__``
remains legitimate only for compiler-capability blocks (``#pragma
aux``, ``int386``, far pointers) that other compilers cannot parse.
"""

from __future__ import annotations

import re
from pathlib import Path

SRC = Path("src")
INCLUDE = Path("include")
TARGET_HEADER = INCLUDE / "c2_target.h"

COND_RE = re.compile(r"^\s*#\s*(if|ifdef|ifndef)\b\s*(.*?)\s*$")

# Conditions allowed outside c2_target.h itself.
ALLOWED_TOKENS = re.compile(
    r"C2_TARGET_[A-Z0-9]+|C2_FEAT_[A-Z0-9_]+|C2_PATCHLEVEL"
    r"|__WATCOMC__"          # compiler capability, not game version
    r"|S_IRUSR"              # portable stat-mode fallback
    r"|\w+_H\b"              # include guards
)


def _conditions(path: Path):
    for lineno, line in enumerate(path.read_text().splitlines(), 1):
        m = COND_RE.match(line)
        if m:
            cond = re.sub(r"/\*.*?(\*/|$)|//.*", "", m.group(2)).strip()
            yield lineno, m.group(1), cond


def test_no_raw_compiler_version_guards_in_source():
    """_MSC_VER must not appear in any #if condition outside c2_target.h."""
    offenders = []
    for path in sorted(SRC.glob("*.c")) + sorted(INCLUDE.glob("*.h")):
        if path == TARGET_HEADER:
            continue
        for lineno, _kind, cond in _conditions(path):
            if "_MSC_VER" in cond:
                offenders.append(f"{path}:{lineno}: {cond}")
    assert not offenders, (
        "raw compiler-version guards found (use C2_TARGET_*/C2_FEAT_* "
        "from include/c2_target.h):\n" + "\n".join(offenders)
    )


def test_guard_vocabulary_is_closed():
    """Every conditional uses the approved guard vocabulary."""
    offenders = []
    for path in sorted(SRC.glob("*.c")) + sorted(INCLUDE.glob("*.h")):
        if path == TARGET_HEADER:
            continue
        for lineno, _kind, cond in _conditions(path):
            tokens = re.findall(r"[A-Za-z_][A-Za-z0-9_]*", cond)
            if not tokens:
                continue
            unknown = [
                t for t in tokens
                if t not in ("defined",) and not ALLOWED_TOKENS.fullmatch(t)
            ]
            if unknown:
                offenders.append(f"{path}:{lineno}: {cond} (unknown: {unknown})")
    assert not offenders, (
        "conditional guards outside the approved vocabulary:\n"
        + "\n".join(offenders)
    )


def test_every_feature_macro_is_defined_in_the_target_header():
    """C2_FEAT_* used anywhere must be defined in c2_target.h."""
    defined = set(
        re.findall(r"#\s*define\s+(C2_FEAT_\w+)", TARGET_HEADER.read_text())
    )
    used = set()
    for path in sorted(SRC.glob("*.c")) + sorted(INCLUDE.glob("*.h")):
        if path == TARGET_HEADER:
            continue
        used |= set(re.findall(r"\bC2_FEAT_\w+\b", path.read_text()))
    missing = used - defined
    assert not missing, f"feature macros used but not defined: {sorted(missing)}"
    unused = defined - used
    assert not unused, f"feature macros defined but never used: {sorted(unused)}"


def test_watcomc_guards_only_wrap_compiler_capability_code():
    """__WATCOMC__ blocks must contain Watcom-only constructs, proving
    they are capability guards rather than misfiled version guards."""
    capability = re.compile(
        r"#pragma\s+aux|int386|union\s+REGS|__far|MK_FP|<i86\.h>|"
        r"_dos_(findfirst|findnext|setdrive)|\bsound\s*\(|\bnosound\s*\(|"
        r"\b(inp|outp|outpw)\s*\("   # VGA/CRTC port I/O
    )
    offenders = []
    for path in sorted(SRC.glob("*.c")) + sorted(INCLUDE.glob("*.h")):
        lines = path.read_text().splitlines()
        stack = []
        for i, line in enumerate(lines):
            m = COND_RE.match(line)
            if m and "__WATCOMC__" in m.group(2):
                stack.append(i)
            elif re.match(r"\s*#\s*endif", line) and stack:
                start = stack.pop()
                body = "\n".join(lines[start : i + 1])
                if not capability.search(body):
                    offenders.append(f"{path}:{start + 1}")
    assert not offenders, (
        "__WATCOMC__ guard without Watcom-only constructs (should this "
        "be a C2_TARGET_*/C2_FEAT_* guard?):\n" + "\n".join(offenders)
    )
