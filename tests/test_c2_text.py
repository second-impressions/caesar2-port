"""The gettext text bundle: every translation validates against the
template, and the C runtime rebuilds exactly what the Python reference
compiler produces."""
import os
from pathlib import Path
import re
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


# ---------------------------------------------------------------------------
# Every string of every original .ENG reaches the engine unchanged.
#
# C2_TEXT_CORPUS names a directory that is searched for C2.ENG/HELP.ENG pairs
# (imported discs, installations). Each pair's language is detected the way
# the port detects it, and every string the engine would have read from the
# original is compared with what it reads from the bundle at the same
# address. A difference is acceptable only when the po entry carries a
# translator comment saying why, or when the tool's documented fixups touch
# that address (the shipped French file's own segmentation faults). Older
# revisions of a language differ from the 1996 text the bundle carries; the
# revision closest to the bundle is the one held to this standard.
# ---------------------------------------------------------------------------

def load_tool():
    import importlib.util
    spec = importlib.util.spec_from_file_location("c2text", TOOL)
    module = importlib.util.module_from_spec(spec)
    sys.modules["c2text"] = module
    spec.loader.exec_module(module)
    return module


def find_original_pairs(corpus: Path):
    pairs = {}
    for c2 in corpus.rglob("*"):
        if c2.name.upper() != "C2.ENG":
            continue
        for sibling in c2.parent.iterdir():
            if sibling.name.upper() == "HELP.ENG":
                pairs[(c2.read_bytes(), sibling.read_bytes())] = c2
    return pairs


def engine_view(tool, c2eng: bytes, helpeng: bytes):
    """Address -> bytes as the engine reads them: (group, index) for C2.ENG,
    ('help', page, slot) for HELP.ENG, aliases resolved."""
    view = {}
    for group, strings in tool.read_textfile(c2eng).items():
        for index, raw in enumerate(strings):
            view[tool.text_key(group, index)] = raw
    hf = tool.read_helpfile(helpeng)
    for page in range(1, tool.HELP_PAGES):
        strings = tool.resolve_help_page(hf, page)
        if strings is None:
            continue
        for slot, raw in enumerate(strings):
            view[tool.help_key(page, slot)] = raw
    return view


def fixup_touched_keys(tool, c2eng: bytes, helpeng: bytes, pot) -> set:
    """Addresses whose content the tool's fixups change for this file."""
    raw = engine_view(tool, c2eng, helpeng)
    groups = tool.read_textfile(c2eng)
    hf = tool.read_helpfile(helpeng)
    pot_groups, pot_pages, _ = tool.po_to_model(pot)
    touched = set()
    for name in list(tool.FIXUPS) + [None]:
        log = []
        try:
            fixed_groups = {g: list(v) for g, v in groups.items()}
            tool.apply_fixups(fixed_groups, c2eng, name, log)
        except (KeyError, IndexError, ValueError):
            continue
        for g, strings in groups.items():
            fixed = fixed_groups.get(g)
            # A group the fixups drop, or that aliases one they drop in the
            # 1996 layout, is a layout difference, not a string difference.
            dropped = fixed is None or tool.TEXT_ALIASES.get(g) in groups and \
                tool.TEXT_ALIASES.get(g) not in fixed_groups
            for i in range(max(len(strings), len(fixed or []))):
                key = tool.text_key(g, i)
                if dropped or (fixed[i] if i < len(fixed) else None) != raw.get(key):
                    touched.add(key)
    fixed_help = tool.HelpFile(hf.records, dict(hf.pages))
    tool.align_help_pages(fixed_help, pot_pages, [])
    for page in range(1, tool.HELP_PAGES):
        before = tool.resolve_help_page(hf, page)
        after = tool.resolve_help_page(fixed_help, page)
        if before != after:
            for slot in range(max(len(before or []), len(after or []))):
                touched.add(tool.help_key(page, slot))
    return touched


def test_every_original_string_reaches_the_engine(tmp_path):
    corpus = os.environ.get("C2_TEXT_CORPUS")
    binary = find_text_test_binary()
    if not corpus or binary is None:
        pytest.skip("C2_TEXT_CORPUS not set or c2-port-text-test not built")
    tool = load_tool()
    pairs = find_original_pairs(Path(corpus))
    assert pairs, f"no C2.ENG/HELP.ENG pairs under {corpus}"

    dump = tmp_path / "dump"
    dump.mkdir()
    result = subprocess.run([str(binary)], capture_output=True, text=True,
                            env={**os.environ, "C2_TEXT_DUMP_DIR": str(dump)})
    assert result.returncode == 0, result.stdout + result.stderr

    pot = tool.po_parse(POT.read_text(encoding="utf-8"))
    languages = {}
    for tag, path in LANGUAGES.items():
        po = tool.po_parse(path.read_text(encoding="utf-8"))
        languages[tag] = {
            "po": po,
            "detect": tool.encode(po.header.get("X-C2-Detect", "")),
            "bundle": engine_view(tool, (dump / f"{tag}.c2.eng").read_bytes(),
                                  (dump / f"{tag}.help.eng").read_bytes()),
        }

    # Group the originals by detected language, as the port would.
    by_language = {tag: [] for tag in languages}
    for (c2eng, helpeng), path in pairs.items():
        first = tool.read_textfile(c2eng)[1][0]
        for tag, lang in languages.items():
            if lang["detect"] and first == lang["detect"]:
                by_language[tag].append((path, c2eng, helpeng))
    report = []
    for tag, originals in by_language.items():
        if not originals:
            report.append(f"{tag}: no original in the corpus")
            continue
        lang = languages[tag]
        explained = {e.msgctxt for e in lang["po"].entries if e.tcomments}

        def is_explained(key):
            # Alias groups carry their target's text and its explanation.
            m = re.match(r"0x([0-9a-f]+)/(\d+)$", key)
            if m and int(m.group(1), 16) in tool.TEXT_ALIASES:
                key = tool.text_key(tool.TEXT_ALIASES[int(m.group(1), 16)], int(m.group(2)))
            return key in explained
        best = None
        for path, c2eng, helpeng in originals:
            original = engine_view(tool, c2eng, helpeng)
            touched = fixup_touched_keys(tool, c2eng, helpeng, pot)
            diffs = {k for k in set(original) | set(lang["bundle"])
                     if original.get(k) != lang["bundle"].get(k)}
            unexplained = sorted(k for k in diffs - touched if not is_explained(k))
            candidate = (len(unexplained), len(diffs), path, unexplained, touched & diffs)
            if best is None or candidate[:2] < best[:2]:
                best = candidate
        count, total, path, unexplained, fixed = best
        report.append(f"{tag}: {path}: {total} differences, {len(fixed)} from fixups, "
                      f"{count} unexplained")
        original = engine_view(tool, *[b for b in pairs if pairs[b] == path][0])
        for key in unexplained[:20]:
            report.append(f"    {key}: original {original.get(key)!r}"
                          f" -> bundle {lang['bundle'].get(key)!r}")
        assert count == 0, "\n".join(report)
    print("\n".join(report))
