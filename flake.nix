{
  description = "Caesar II portable continuation — development shell";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  };

  outputs =
    { self, nixpkgs }:
    let
      forAllSystems = nixpkgs.lib.genAttrs [ "x86_64-linux" "aarch64-linux" ];
    in
    {
      devShells = forAllSystems (
        system:
        let
          pkgs = nixpkgs.legacyPackages.${system};
          # The save format's schema compiler. Pinned to the latest release
          # independently of the nixpkgs lock: the runtime bundled under
          # third_party/flatcc must be the same version, and the generated
          # accessors under src/platform/common/c2_save_gen/ must come from
          # it (tests/test_save_schema.py). Bump all three together.
          flatcc = pkgs.flatcc.overrideAttrs (old: rec {
            version = "0.6.3";
            # nixpkgs' clang-15 patch and hexdigits fix are upstream since 0.6.2
            patches = [ ];
            postPatch = "";
            src = pkgs.fetchFromGitHub {
              owner = "dvidelabs";
              repo = "flatcc";
              tag = "v${version}";
              hash = "sha256-kDZ05r/k15peBLGG2jzyeKwrdTn3+1PWrrDUmC3SV50=";
            };
          });
        in
        {
          default = pkgs.mkShell {
            packages = [
              pkgs.chromium
              pkgs.ccache
              pkgs.cmake
              pkgs.emscripten
              pkgs.firefox
              pkgs.ninja
              pkgs.nodejs
              pkgs.playwright-test
              pkgs.playwright-driver.browsers
              pkgs.pkg-config
              pkgs.sdl3
              pkgs.clang
              pkgs.llvmPackages.llvm   # llvm-symbolizer for sanitizer reports
              pkgs.gdb
              pkgs.imagemagick
              pkgs.libbacktrace
              pkgs.python313
              pkgs.uv
              pkgs.unity-test
              flatcc                  # save-format schema compiler (tools/regen-save-schema.sh)
            ];

            # libstdc++/zlib must be resolvable so capstone (used by the
            # reccmp fork) can load its native extension inside `uv run`.
            env.LD_LIBRARY_PATH = pkgs.lib.makeLibraryPath [
              pkgs.stdenv.cc.cc.lib
              pkgs.zlib
            ];
            env.PLAYWRIGHT_BROWSERS_PATH = "${pkgs.playwright-driver.browsers}";
            env.NODE_PATH = "${pkgs.playwright-test}/lib/node_modules";

            # The Watcom 10.0a toolchain itself is NOT in this shell: c2
            # rebuild/delink shell out to the system podman with the
            # ghcr.io/second-impressions/watcom-10.0a-wibo image (public;
            # override with C2_WATCOM_IMAGE).
          };
        }
      );
    };
}
