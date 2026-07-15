{
  description = "Dev shell for reverse-engineering the Watcom 10.0a wcc386 compiler binary";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

  outputs = { self, nixpkgs }:
    let
      systems = [ "x86_64-linux" "aarch64-linux" "x86_64-darwin" ];
      forAll = f: nixpkgs.lib.genAttrs systems (s: f nixpkgs.legacyPackages.${s});
    in {
      devShells = forAll (pkgs: {
        default = pkgs.mkShell {
          name = "wcc386-re";
          packages = [
            # Disassembly / RE
            pkgs.rizin                       # `rizin`, `rz-asm` -- quick raw disasm
            pkgs.radare2                     # `r2` if you prefer it
            (pkgs.python3.withPackages (ps: [
              ps.capstone                    # used by wcc_image.py / disasm scripts
            ]))
            # Ghidra (headless analyzer + GUI). The project already ships
            # ghidra-cli, but this makes the shell self-contained.
            pkgs.ghidra
            # The original toolchain lives in a podman image
            # (localhost/watcom-10.0a-dosemu2); podman itself is provided by
            # the host. `qemu`/`dosbox` are handy alternatives.
            pkgs.podman
          ];
          shellHook = ''
            echo "wcc386-10.0a RE shell"
            echo "  python wcc_image.py <wcc386-10.0a.exe>            # crack format + dump reg tables"
            echo "  python wcc_image.py <exe> --ghidra-base           # import flags for analyzeHeadless"
            echo ""
            echo "Quick raw disasm of the flat image at the correct base (va = file + 0x6758):"
            echo "  rizin -n -e asm.bits=32 -e asm.arch=x86 -m 0x6758 <exe>"
            echo ""
            echo "Headless Ghidra import (decompiler):"
            echo "  analyzeHeadless <projdir> wcc386_10_0a -import <exe> \\"
            echo "     -loader BinaryLoader -loader-baseAddr 0x6758 -processor x86:LE:32:default"
          '';
        };
      });
    };
}
