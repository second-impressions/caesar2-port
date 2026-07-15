{
  pkgs,
  lib,
  config,
  inputs,
  ...
}:

let
  # codex from nixpkgs PR #540177 (0.144.1)
  pkgs-codex = import inputs.nixpkgs-codex {
    inherit (pkgs.stdenv.hostPlatform) system;
    config.allowUnfree = true;
  };

  wcc10a = pkgs.stdenv.mkDerivation {
    name = "wcc10a";
    src = pkgs.fetchgit {
      url = "https://github.com/thirdpartystuff/win32-watcom10";
      rev = "4ff06555657448d62441f4bb359f96c79e08a568";
      hash = "sha256-/3YLfgbLmsWXmPmPio+zcA3PGBnBdW55i5kVCDfGGI4=";
    };
    nativeBuildInputs = [ pkgs.makeWrapper ];
    installPhase = ''
      mkdir -p $out/bin $out/share/wcc10a
      cp -r . $out/share/wcc10a/

      # wcc386: the NT stub delegates to binb/wcc386.exe via its own DOS extender
      makeWrapper ${pkgs.wine}/bin/wine $out/bin/wcc386 \
        --add-flags "$out/share/wcc10a/binnt/wcc386.exe" \
        --set WATCOM "$out/share/wcc10a" \
        --set WINEDEBUG "-all"

      for tool in wlink wlib; do
        makeWrapper ${pkgs.wine}/bin/wine $out/bin/$tool \
          --add-flags "$out/share/wcc10a/binnt/$tool.exe" \
          --set WATCOM "$out/share/wcc10a" \
          --set WINEDEBUG "-all"
      done

      # wasm is not in this repo — fall back to open-watcom-v2 for assembling
    '';
  };
in

{
  # https://devenv.sh/basics/
  env.GREET = "devenv";

  # https://devenv.sh/packages/
  packages = [
    pkgs.bchunk
    pkgs.p7zip
    pkgs.xxd
    pkgs.binwalk
    pkgs.nasm
    pkgs.detect-it-easy
    #pkgs.open-watcom-bin
    #pkgs.open-watcom-v2  # replaced by wcc10.5 for byte-identical output
    wcc10a
    pkgs.open-watcom-v2  # for wasm (not in wcc10a repo)
    pkgs.wine
    pkgs.imhex
    pkgs.dosbox-x
    pkgs-codex.codex
  ];

  # https://devenv.sh/languages/
  # libstdc++ must be on LD_LIBRARY_PATH so that capstone (used by reccmp)
  # can load its native extension inside `uv run`.
  env.NIX_LD_LIBRARY_PATH = lib.makeLibraryPath [
    pkgs.stdenv.cc.cc
    pkgs.stdenv.cc.cc.lib
    pkgs.zlib
  ];
  env.NIX_LD = lib.fileContents "${pkgs.stdenv.cc}/nix-support/dynamic-linker";
  env.LD_LIBRARY_PATH = "${pkgs.stdenv.cc.cc.lib}/lib";

  languages.python = {
    enable = true;
    uv.enable = true;
  };

  languages.javascript = {
    bun.enable = true;
  };

  languages.java.enable = true;
}
