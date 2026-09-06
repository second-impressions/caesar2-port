"""The gettext text bundle: every translation validates against the
template, and the C runtime rebuilds exactly what the Python reference
compiler produces."""
import os
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "c2-text.py"
PO = ROOT / "po"
POT = PO / "c2.pot"
LANGUAGES = {"en": POT, **{p.stem: p for p in sorted(PO.glob("*.po"))}}


def run(*args, check=True):
    result = subprocess.run([sys.executable, str(TOOL), *map(str, args)],
                            capture_output=True, text=True)
    if check:
        assert result.returncode == 0, result.stdout + result.stderr
    return result


def test_bundle_has_the_three_shipped_languages():
    assert {"en", "de", "fr"} <= set(LANGUAGES)


def test_template_is_english():
    header = POT.read_text(encoding="utf-8")[:2000]
    assert '"Language: en\\n"' in header
    assert '"X-C2-Name: English\\n"' in header
    assert '"X-C2-Detect: File\\n"' in header


@pytest.mark.parametrize("tag", sorted(LANGUAGES))
def test_translation_validates_against_the_template(tag):
    result = run("check", "--pot", POT, LANGUAGES[tag])
    assert "error:" not in result.stdout, result.stdout


@pytest.mark.parametrize("tag", sorted(t for t in LANGUAGES if t != "en"))
def test_translation_covers_the_template(tag):
    """Shipped translations may leave the 1996 additions untranslated, but
    nothing else."""
    result = run("check", "--pot", POT, LANGUAGES[tag])
    summary = result.stdout.strip().splitlines()[-1]
    untranslated = int(summary.split(" entries, ")[1].split(" untranslated")[0])
    assert untranslated <= 25, summary


def test_po_files_are_utf8_without_bom():
    for path in LANGUAGES.values():
        raw = path.read_bytes()
        assert not raw.startswith(b"\xef\xbb\xbf")
        raw.decode("utf-8")


def find_text_test_binary():
    env = os.environ.get("C2_TEXT_TEST_BINARY")
    candidates = [Path(env)] if env else []
    candidates += [ROOT / "build" / "ci" / "c2-port-text-test",
                   ROOT / "build" / "port" / "linux-debug" / "c2-port-text-test",
                   ROOT / "build" / "port" / "linux-release" / "c2-port-text-test"]
    for c in candidates:
        if c.is_file() and os.access(c, os.X_OK):
            return c
    return None


def test_c_runtime_matches_the_reference_compiler(tmp_path):
    binary = find_text_test_binary()
    if binary is None:
        pytest.skip("c2-port-text-test not built")
    dump = tmp_path / "dump"
    dump.mkdir()
    result = subprocess.run([str(binary)], capture_output=True, text=True,
                            env={**os.environ, "C2_TEXT_DUMP_DIR": str(dump)})
    assert result.returncode == 0, result.stdout + result.stderr
    for tag, po in LANGUAGES.items():
        c2eng = tmp_path / f"{tag}.eng"
        helpeng = tmp_path / f"{tag}.hlp"
        run("compile", po, "--c2", c2eng, "--help-out", helpeng)
        assert (dump / f"{tag}.c2.eng").read_bytes() == c2eng.read_bytes(), tag
        assert (dump / f"{tag}.help.eng").read_bytes() == helpeng.read_bytes(), tag
        assert c2eng.stat().st_size <= 40000
