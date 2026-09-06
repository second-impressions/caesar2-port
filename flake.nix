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
              pkgs.gdb
              pkgs.imagemagick
              pkgs.libbacktrace
              pkgs.python313
              pkgs.uv
              pkgs.unity-test
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

          # Windows cross target.  This is the cheap LLP64/Win32 canary that
          # CI also runs on its Linux runner; the authoritative Windows build
          # is MSVC on a Windows runner.  The cross stdenv is needed rather
          # than a bare compiler package so the mcfgthreads runtime and the
          # target sysroot land in the wrapper's search paths.
          #
          #   nix develop .#mingw
          #   cmake --preset windows-mingw-debug
          #   cmake --build --preset windows-mingw-debug
          mingw = pkgs.pkgsCross.mingwW64.mkShell {
            depsBuildBuild = [ pkgs.pkgsCross.mingwW64.buildPackages.pkg-config ];
            nativeBuildInputs = [
              pkgs.ccache
              pkgs.cmake
              pkgs.ninja
            ];
            buildInputs = [
              pkgs.pkgsCross.mingwW64.windows.mcfgthreads
            ];
          };
        }
      );
    };
}
