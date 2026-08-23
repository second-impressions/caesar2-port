from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]


def test_version_scheme_starts_at_one_and_has_build_metadata():
    cmake = (ROOT / "CMakeLists.txt").read_text()
    template = (ROOT / "include" / "c2_version.h.in").read_text()
    assert "project(caesar2-port VERSION 1.0.0" in cmake
    assert '"${PROJECT_VERSION}-${C2_BUILD_NUMBER}-${C2_GIT_HASH}"' in cmake
    assert "git rev-list --count HEAD" in cmake
    assert "git rev-parse --short=8 HEAD" in cmake
    assert '#define C2_VERSION_STRING "@C2_VERSION_STRING@"' in template


def test_pages_builds_every_main_push_and_deploys_wasm():
    workflow = (ROOT / ".github" / "workflows" / "pages.yml").read_text()
    assert re.search(r"push:\s*\n\s*branches: \[main\]", workflow)
    assert "paths-ignore" not in workflow
    assert "submodules: recursive" in workflow
    assert "-DC2_BUILD_NUMBER=${BUILD_NUMBER}" in workflow
    assert "-DC2_GIT_HASH=${SHORT_SHA}" in workflow
    assert "actions/upload-pages-artifact@v3" in workflow
    assert "actions/deploy-pages@v4" in workflow
    assert "coi-serviceworker.js" in workflow
    assert "caesar2-en.wasm" in workflow


def test_import_tests_split_synthetic_and_opt_in_corpora():
    cmake = (ROOT / "CMakeLists.txt").read_text()
    assert "add_test(NAME import-readers" in cmake
    assert 'set(C2_TEST_GAME_DATA_SOURCES "" CACHE STRING' in cmake
    assert "game-data-corpus-${corpus_index}" in cmake
    assert 'LABELS "game-data-corpus;requires-original-assets"' in cmake
    assert "C2_TEST_GAME_DATA_SOURCES" not in (ROOT / ".github" / "workflows" / "ci.yml").read_text()


def test_pages_shell_exposes_version_and_cross_origin_isolation():
    shell = (ROOT / "web" / "caesar2.html").read_text()
    worker = (ROOT / "web" / "coi-serviceworker.js").read_text()
    assert shell.count("@C2_VERSION_STRING@") >= 2
    assert 'src="coi-serviceworker.js"' in shell
    assert '"Cross-Origin-Opener-Policy", "same-origin"' in worker
    assert '"Cross-Origin-Embedder-Policy", "require-corp"' in worker
    assert "serviceWorker.register" in worker
