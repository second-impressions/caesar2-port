"""Guard-vocabulary lint for cross-build conditional compilation.

Version-specific differences between the DOS release and the Windows
build-A witness must be guarded by the target/feature macros from
``include/c2_target.h`` — never by raw compiler macros, which conflate
"which compiler" with "which build of the game". Platform-specific
compiler capabilities are selected by the platform macros too. Optional
fixes for confirmed shipped bugs are catalogued in
``include/c2_bugfixes.h``.

Two prefixes are approved, and the split is deliberate:

``PLATFORM_DOS`` / ``PLATFORM_WINDOWS`` / ``C2_FEAT_*`` / ``C2_FIX_*`` /
``C2_PATCHLEVEL`` are shared verbatim with caesar2-reconstruction, so
recovered code carrying them cherry-picks in both directions unchanged.

``PORT_*`` names everything this repository adds for itself — host
platforms, port features, port fixes, the observation stream. Seeing the
prefix at a use site inside a recovered translation unit is what tells a
reader the guard is port-added rather than recovered.
"""

from __future__ import annotations

import re
from pathlib import Path

SRC = Path("src")
INCLUDE = Path("include")
TARGET_HEADER = INCLUDE / "c2_target.h"
BUGFIX_HEADER = INCLUDE / "c2_bugfixes.h"

COND_RE = re.compile(r"^\s*#\s*(if|ifdef|ifndef|elif)\b\s*(.*?)\s*$")

# Conditions allowed outside c2_target.h itself.
ALLOWED_TOKENS = re.compile(
    # shared with caesar2-reconstruction — never rename these
    r"PLATFORM_(DOS|WINDOWS)|C2_FEAT_[A-Z0-9_]+"
    r"|C2_FIX_[A-Z0-9_]+|C2_PATCHLEVEL"
    # added by the port
    r"|PORT_PLATFORM(_(LINUX|WIN32|WASM))?"
    r"|PORT_(FEAT|FIX|ENABLE|DEBUG)_[A-Z0-9_]+"
    r"|S_IRUSR"              # portable stat-mode fallback
    r"|\w+_H\b"              # include guards
)


def _conditions(path: Path):
    for lineno, line in enumerate(path.read_text().splitlines(), 1):
        m = COND_RE.match(line)
        if m:
            cond = re.sub(r"/\*.*?(\*/|$)|//.*", "", m.group(2)).strip()
            yield lineno, m.group(1), cond


def test_no_raw_compiler_guards_in_source():
    """Compiler identity must not select source variants."""
    offenders = []
    for path in sorted(SRC.rglob("*.c")) + sorted(INCLUDE.rglob("*.h")):
        for lineno, _kind, cond in _conditions(path):
            if "_MSC_VER" in cond or "__WATCOMC__" in cond:
                offenders.append(f"{path}:{lineno}: {cond}")
    assert not offenders, (
        "raw compiler guards found (use PLATFORM_*/C2_FEAT_* "
        "from include/c2_target.h):\n" + "\n".join(offenders)
    )


def test_guard_vocabulary_is_closed():
    """Every conditional uses the approved guard vocabulary."""
    offenders = []
    for path in sorted(SRC.rglob("*.c")) + sorted(INCLUDE.rglob("*.h")):
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
    for path in sorted(SRC.rglob("*.c")) + sorted(INCLUDE.rglob("*.h")):
        if path == TARGET_HEADER:
            continue
        used |= set(re.findall(r"\bC2_FEAT_\w+\b", path.read_text()))
    missing = used - defined
    assert not missing, f"feature macros used but not defined: {sorted(missing)}"
    unused = defined - used
    assert not unused, f"feature macros defined but never used: {sorted(unused)}"


def test_every_bugfix_macro_is_defined_in_the_bugfix_header():
    """C2_FIX_* used by shipped code must belong to the bug-fix catalogue."""
    defined = set(
        re.findall(r"#\s*define\s+(C2_FIX_\w+)", BUGFIX_HEADER.read_text())
    )
    used = set()
    for path in sorted(SRC.rglob("*.c")) + sorted(INCLUDE.rglob("*.h")):
        if path == BUGFIX_HEADER:
            continue
        used |= set(re.findall(r"\bC2_FIX_\w+\b", path.read_text()))
    missing = used - defined
    assert not missing, f"bug-fix macros used but not defined: {sorted(missing)}"
    unused = defined - used
    assert not unused, f"bug-fix macros defined but never used: {sorted(unused)}"


def test_bugfixes_default_to_the_portable_target_only():
    """A retained shipped-target build must not acquire port bug fixes."""
    text = BUGFIX_HEADER.read_text()
    defined = set(re.findall(r"#\s*define\s+(C2_FIX_\w+)", text))
    for name in defined:
        assert re.search(
            rf"#\s*define\s+{name}\s+PORT_PLATFORM\b", text
        ), f"{name} does not default to PORT_PLATFORM"


def test_portable_target_keeps_the_recovered_software_menus():
    """The port has no Windows-native replacement for the recovered menu bar."""
    text = (SRC / "controls.c").read_text()
    assert re.search(
        r"#\s*if\s+PLATFORM_WINDOWS\s*\n\s*return\s*;",
        text,
    )
    assert "C2_FEAT_SOFTWARE_MENUS" not in text


def test_wasm_is_a_platform_target_not_a_feature():
    """Browser scheduling follows the Wasm leaf target."""
    text = TARGET_HEADER.read_text()
    assert "PORT_PLATFORM_WASM" in text
    assert "C2_FEAT_BROWSER_RUNTIME" not in text
