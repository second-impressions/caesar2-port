import json
from pathlib import Path
import subprocess
import sys
import zipfile


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "c2-assets.py"


def run(*args):
    return subprocess.run([sys.executable, str(TOOL), *map(str, args)],
                          capture_output=True, text=True)


def make_source(root: Path, language: bytes, speech: bytes):
    root.mkdir(parents=True)
    (root / "C2.ENG").write_bytes(language)
    (root / "HELP.ENG").write_bytes(language + b" help")
    (root / "RAW").mkdir()
    (root / "RAW" / "C01.RAW").write_bytes(speech)
    (root / "SMK").mkdir()
    (root / "SMK" / "INTRO.SMK").write_bytes(b"video")
    for index in range(101):
        (root / f"CORE{index:03}.PL8").write_bytes(b"shared" + bytes([index]))


def test_multilanguage_pack_deduplicates_and_verifies(tmp_path):
    english = tmp_path / "english"
    german = tmp_path / "german"
    make_source(english, b"english", b"hello")
    make_source(german, b"german", b"hallo")
    output = tmp_path / "all.c2assets"
    result = run("build", "--core", english,
                 "--text", f"en={english}", "--speech", f"en={english}",
                 "--text", f"de={german}", "--speech", f"de={german}",
                 "--video", f"dos={english}", "--output", output)
    assert result.returncode == 0, result.stderr
    checked = run("verify", output)
    assert checked.returncode == 0, checked.stderr
    with zipfile.ZipFile(output) as archive:
        manifest = json.loads(archive.read("C2PACK.JSN"))
    assert set(manifest["profiles"]) == {"de", "en"}
    assert manifest["components"]["text/de"]["C2.ENG"] != \
           manifest["components"]["text/en"]["C2.ENG"]
    # 101 core + two text pairs + two speech + one shared video, with shared
    # core content stored once rather than once per language.
    assert len(manifest["objects"]) < 110


def test_mac_intro_is_exposed_under_canonical_name(tmp_path):
    core = tmp_path / "core"
    make_source(core, b"english", b"hello")
    mac = tmp_path / "mac" / "SMK"
    mac.mkdir(parents=True)
    (mac / "INTRONEW.SMK").write_bytes(b"large mac intro")
    output = tmp_path / "mac.c2assets"
    result = run("build", "--core", core, "--text", f"en={core}",
                 "--video", f"mac={mac}", "--output", output)
    assert result.returncode == 0, result.stderr
    with zipfile.ZipFile(output) as archive:
        manifest = json.loads(archive.read("C2PACK.JSN"))
    assert "SMK/INTRO.SMK" in manifest["components"]["video/mac"]
    assert all("INTRONEW" not in key for key in manifest["components"]["video/mac"])


def test_iso_pack_builds_and_verifies(tmp_path):
    source = tmp_path / "source"
    make_source(source, b"english", b"hello")
    output = tmp_path / "assets.iso"
    result = run("build", "--core", source, "--text", f"en={source}",
                 "--format", "iso", "--output", output)
    assert result.returncode == 0, result.stderr
    checked = run("verify", output)
    assert checked.returncode == 0, checked.stderr


def test_verify_rejects_changed_object(tmp_path):
    source = tmp_path / "source"
    make_source(source, b"english", b"hello")
    good = tmp_path / "good.c2assets"
    assert run("build", "--core", source, "--text", f"en={source}",
               "--output", good).returncode == 0
    bad = tmp_path / "bad.c2assets"
    with zipfile.ZipFile(good) as src, zipfile.ZipFile(bad, "w") as dst:
        for info in src.infolist():
            data = src.read(info)
            if info.filename.startswith("OBJECTS/"):
                data += b"corrupt"
            dst.writestr(info.filename, data)
    result = run("verify", bad)
    assert result.returncode != 0
    assert "verification failed" in result.stderr
