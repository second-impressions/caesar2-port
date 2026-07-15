{
  description = "Caesar II reconstruction — dev shell (python/uv toolchain + DOSBox-X)";

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
              pkgs.python313
              pkgs.uv
              pkgs.dosbox-x # run the rebuilt game (README "Running the game")
            ];

            # libstdc++/zlib must be resolvable so capstone (used by the
            # reccmp fork) can load its native extension inside `uv run`.
            env.LD_LIBRARY_PATH = pkgs.lib.makeLibraryPath [
              pkgs.stdenv.cc.cc.lib
              pkgs.zlib
            ];

            # The Watcom 10.0a toolchain itself is NOT in this shell: c2
            # rebuild/delink shell out to the system podman with the
            # localhost/watcom-10.0a-wibo image.
          };
        }
      );
    };
}
