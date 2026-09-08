from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]


def test_version_scheme_names_releases_and_everything_else_by_origin():
    cmake = (ROOT / "CMakeLists.txt").read_text()
    template = (ROOT / "include" / "c2_version.h.in").read_text()
    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text()
    assert re.search(r"project\(caesar2-port VERSION [1-9]\d*\.\d+\.\d+ ", cmake)
    # A release is its version, and nothing else is: main-<sha>, prN-<sha>,
    # dev-<sha>, or the configure time of an edited worktree.
    assert 'set(C2_VERSION_STRING "${PROJECT_VERSION}${C2_VERSION_SUFFIX}")' in cmake
    assert 'set(C2_VERSION_STRING "${C2_BUILD_LABEL}-${C2_GIT_HASH}")' in cmake
    assert 'set(C2_VERSION_STRING "local-${C2_LOCAL_BUILD_STAMP}")' in cmake
    assert 'git status --porcelain --untracked-files=no' in cmake
    assert 'string(TIMESTAMP C2_LOCAL_BUILD_STAMP "%Y%m%d-%H%M%S" UTC)' in cmake
    assert "git rev-parse --short=8 HEAD" in cmake
    assert '#define C2_VERSION_STRING "@C2_VERSION_STRING@"' in template
    # CI labels builds by origin, and a pull request by its own head commit.
    assert "format('pr{0}', github.event.pull_request.number) || 'main'" in ci
    assert "github.event.pull_request.head.sha || github.sha" in ci


def test_release_workflow_tags_builds_and_drafts():
    workflow = (ROOT / ".github" / "workflows" / "release.yml").read_text()
    assert "tags: ['v*']" in workflow
    assert "workflow_dispatch:" in workflow
    # The tag goes on the verified commit, the builds check out the same one,
    # and nothing is published without a person pressing the button.
    assert workflow.count("ref: ${{ needs.verify.outputs.commit }}") == 5
    assert 'git tag -a "$tag" -F /tmp/tag-notes.md "$commit"' in workflow
    assert "--draft" in workflow
    assert "actions/attest-build-provenance" in workflow
    for artifact in ("windows-x64", "AppImage", ".flatpak", "-web", ".dmg"):
        assert artifact in workflow
    assert "packaging/appimage/build.sh" in workflow
    assert "flatpak/flatpak-github-actions/flatpak-builder" in workflow
    script = (ROOT / "tools" / "release.py").read_text()
    assert '"prepare"' in script and '"publish"' in script
    assert (ROOT / "CHANGELOG.md").read_text().startswith("# Changelog")


def test_pages_deploys_the_single_main_wasm_build():
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text()
    assert re.search(r"push:\s*\n\s*branches: \[main\]", workflow)
    assert "submodules: recursive" not in workflow  # nothing left to fetch
    assert workflow.count("emcmake cmake --preset wasm-release") == 1
    assert workflow.count("cmake --build build/ci-wasm") == 1
    assert "--clean-first" not in workflow
    assert "needs: wasm" in workflow
    # One site on the gh-pages branch: the latest published release at /,
    # main at /main/, each pull request from this repository at /pr/N/,
    # removed when it closes. One script writes every directory.
    assert 'group: gh-pages' in workflow
    assert 'target="pr/$PR_NUMBER"; else target="main"' in workflow
    assert ".github/scripts/publish-pages.sh" in workflow
    pages_release = (ROOT / ".github" / "workflows" / "pages-release.yml").read_text()
    assert "types: [published]" in pages_release
    assert "github.event.release.prerelease == false" in pages_release
    assert 'publish-pages.sh . _site' in pages_release
    script = (ROOT / ".github" / "scripts" / "publish-pages.sh").read_text()
    assert "! -name pr ! -name main" in script
    assert "github.event.pull_request.head.repo.full_name == github.repository" in workflow
    assert "preview-cleanup:" in workflow
    # Deployments, not comments, point at the previews.
    assert "deployments: write" in workflow
    assert "environment: `preview/pr-${pr}`" in workflow
    assert "environment: 'main'" in workflow
    assert "pull-requests: write" not in workflow
    assert (ROOT / ".github" / "scripts" / "deployment.js").exists()
    assert "coi-serviceworker.js" in workflow
    assert "c2-shell.js" in workflow
    assert "c2-shell.css" in workflow
    assert "index.wasm" in workflow


def test_about_box_reports_the_running_build():
    cmake = (ROOT / "CMakeLists.txt").read_text()
    header = (ROOT / "include" / "c2_version.h.in").read_text()
    target = (ROOT / "include" / "c2_target.h").read_text()
    screens = (ROOT / "src" / "screens.c").read_text()
    assert "#define PORT_FEAT_BUILD_STAMP PORT_PLATFORM" in target
    # Shipped targets keep the recovered c2.eng version lines.
    assert "#if PORT_FEAT_BUILD_STAMP" in screens
    assert "put_a_font_string(c2_port_version_line()" in screens
    assert "font_list(0xb, 0, 0xa0, 0x58, font1, 0x10);" in screens
    # The startup notice carries the same stamp; other warnings are untouched.
    controls = (ROOT / "src" / "controls.c").read_text()
    assert "#if PORT_FEAT_BUILD_STAMP" in controls
    assert "if (message_idx == 0) {" in controls
    assert "put_a_font_string(c2_port_version_line()" in controls
    compat = (ROOT / "src" / "platform" / "common" / "c2_port_compat.c").read_text()
    assert '"Version: " C2_VERSION_STRING' in compat
    assert "font_list(0xb, message_idx,     x + 0x10, y + 0x10, font1, 0x10);" in controls
    assert not (ROOT / ".github" / "workflows" / "pages.yml").exists()


def test_nix_and_wasm_configuration_are_cached():
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text()
    setup = (ROOT / ".github" / "actions" / "setup-nix" / "action.yml").read_text()
    flake = (ROOT / "flake.nix").read_text()
    assert "nix-community/cache-nix-action@v7" in setup
    assert "~/.cache/ccache" in setup
    assert "pkgs.ccache" in flake
    assert "build/ci-wasm" in workflow
    assert ".cache/emscripten" in workflow
    assert "embuilder build sdl3-mt zlib" in workflow
    assert "CMAKE_C_COMPILER_LAUNCHER=ccache" in workflow


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
