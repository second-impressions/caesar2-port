"""Install command: install Caesar II from a CD directory to a target location."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Annotated

import typer


# Files to copy from the CD root (case-insensitive glob)
_CD_ROOT_GLOBS = [
    "SIERRA.EXE", "BOOTDISK.EXE", "SIERRA.ERR", "INTERP.ERR",
    "WHAT.EXE", "*.PIF", "UNIVESA.*", "COPYRIGHT", "CHECK.EXE",
    "INSTALL.*", "RESOURCE.CFG", "README.TXT",
]

# CD-only asset subdirectories the game streams at runtime.
#
# Discovered via static analysis of PS.EXE (cd_path / readfile):
#   .PL8 → pl8/   .RAW → raw/   .XMI → xmi/   .SMK → smk/
#
# The game's readfile() tries the current directory first; if the file is
# present locally it never touches the CD.  Copying these into the install
# dir gives a fully self-contained hard-drive install.
_CD_ASSET_DIRS = ["pl8", "raw", "xmi", "smk"]


def install(
    cd_root: Annotated[Path, typer.Argument(help="Path to extracted CD root directory")],
    install_dir: Annotated[
        Path,
        typer.Argument(help="Installation destination directory"),
    ] = Path("install/caesar2"),
    full: Annotated[
        bool,
        typer.Option(
            "--full",
            help=(
                "Copy CD-only asset directories (pl8/, raw/, xmi/, smk/) into the "
                "install dir so the game runs without a CD.  Without this flag the "
                "install is minimal (HD/ tree only) and the CD must be mounted at "
                "runtime via 'c2 run --cd <cd-root>'."
            ),
        ),
    ] = False,
) -> None:
    """Install Caesar II from an extracted CD directory.

    By default only the HD/ tree is copied (minimal install).  Pass --full to
    also copy the CD-only media assets so the game runs without a CD.
    """
    if not cd_root.exists() or not cd_root.is_dir():
        typer.echo(f"Error: CD root not found: {cd_root}", err=True)
        raise typer.Exit(1)

    hd_dir = cd_root / "HD"
    if not hd_dir.exists():
        typer.echo(f"Error: CD does not contain 'HD' directory: {hd_dir}", err=True)
        raise typer.Exit(1)

    install_dir.mkdir(parents=True, exist_ok=True)

    typer.echo(f"CD root:     {cd_root}")
    typer.echo(f"Install dir: {install_dir}")
    typer.echo(f"Mode:        {'full (no CD required)' if full else 'minimal (CD required at runtime)'}")

    # Copy files from CD root
    typer.echo("\nCopying files from CD root...")
    for f in cd_root.iterdir():
        if f.is_file():
            name_upper = f.name.upper()
            for pattern in _CD_ROOT_GLOBS:
                pat_upper = pattern.upper()
                if pat_upper.endswith(".*"):
                    stem = pat_upper[:-2]
                    if name_upper.startswith(stem):
                        shutil.copy2(f, install_dir / f.name)
                        typer.echo(f"  Copied: {f.name}")
                        break
                elif "*" in pat_upper:
                    # Simple wildcard: *.PIF → any .PIF file
                    ext = pat_upper.lstrip("*")
                    if name_upper.endswith(ext):
                        shutil.copy2(f, install_dir / f.name)
                        typer.echo(f"  Copied: {f.name}")
                        break
                elif name_upper == pat_upper:
                    shutil.copy2(f, install_dir / f.name)
                    typer.echo(f"  Copied: {f.name}")
                    break

    # Copy HD/ directory contents
    typer.echo("\nCopying game files from HD/...")
    shutil.copytree(str(hd_dir), str(install_dir), dirs_exist_ok=True)

    if full:
        # Copy CD-only asset subdirectories so the game never needs the CD.
        typer.echo("\nCopying CD asset directories (pl8, raw, xmi, smk)...")
        for dirname in _CD_ASSET_DIRS:
            # Try both lower-case and upper-case variants (CD images vary)
            src = next(
                (cd_root / d for d in (dirname, dirname.upper()) if (cd_root / d).is_dir()),
                None,
            )
            if src is None:
                typer.echo(f"  Warning: {dirname}/ not found on CD, skipping")
                continue
            dest = install_dir / dirname
            shutil.copytree(str(src), str(dest), dirs_exist_ok=True)
            typer.echo(f"  Copied: {src.name}/ → {dest}/")

    # Create c2.bat launcher
    bat_path = install_dir / "c2.bat"
    bat_path.write_text(
        "@echo off\ncls\nhavevesa.exe\nif errorlevel 1 UNIVESA.EXE\nps.exe\n"
    )
    typer.echo(f"\nCreated launcher: {bat_path}")

    # Create cd.dat — the CD presence sentinel file.
    #
    # Static analysis of test_cd_drive() in PS.EXE shows the check is:
    #   chdir("D:\")          ← switches to CD drive root
    #   open("cd.dat", O_RDONLY)  ← tries to open this specific file
    # If open() succeeds the game proceeds; otherwise "No CD check info found".
    # For a full install this file lives in the install dir (mounted as D: cdrom).
    cd_dat = install_dir / "cd.dat"
    if not cd_dat.exists():
        cd_dat.touch()
        typer.echo(f"Created CD sentinel: {cd_dat}")

    # Write RESOURCE.CFG.
    #
    # Static analysis of PS.EXE (read_config) shows the game scans the file for
    # the key "resaud" and returns the character at offset +7, i.e. the drive
    # letter in "resaud=D".  DOSBox-X allows open() on the root of a cdrom-type
    # mount; a plain hard-drive mount fails — so resaud must point at D: which
    # 'c2 run' always mounts as -t cdrom:
    #   --full   : D: = install dir itself (same files, fake cdrom)
    #   minimal  : D: = real CD root supplied via --cd
    #
    # We always overwrite RESOURCE.CFG (the HD/ copy from the CD may contain
    # stale drive letters from the original Sierra install, and appending would
    # accumulate duplicate keys across repeated installs).
    resource_cfg = install_dir / "RESOURCE.CFG"
    resource_cfg.write_text(
        "resaud=D\n"
        "resmap=D\n"
        "ressfx=D\n"
        "rescdisc=D\n"
        "audiosize=63\n"
    )
    typer.echo(f"Wrote RESOURCE.CFG: {resource_cfg}")

    # Write DIG.INI — Miles Sound System digital-audio driver configuration.
    #
    # PS.EXE (LOWSOUNDDRIVERLOAD) calls _AIL_install_DIG_driver_file() which
    # reads DIG.INI from the current directory to determine which .DIG driver
    # to load and what I/O settings to use.  Without this file the AIL library
    # cannot initialise the sound driver, samples_running stays 0, and the
    # game falls back to a PC-speaker beep.
    #
    # Format confirmed by running SETSOUND.EXE inside DOSBox-X and inspecting
    # the output (Miles Design AIL v3.02, 18-Jan-95):
    #   - Comment header block (lines starting with ;)
    #   - DEVICE : human-readable card name
    #   - DRIVER : driver filename (relative, no path)
    #   - IO_ADDR: I/O base in hex with 'h' suffix (matches DOSBox-X sbbase=220)
    #   - IRQ    : IRQ number (matches DOSBox-X irq=7)
    #   - DMA_8_BIT  : 8-bit DMA channel (matches DOSBox-X dma=1)
    #   - DMA_16_BIT : 16-bit DMA channel (-1 = not used / auto)
    #
    # SETSOUND.EXE selects SBLASTER.DIG (generic SB-compatible) when
    # autodetecting under DOSBox-X, not SB16.DIG.  DMA_16_BIT is -1 because
    # the generic SBLASTER driver uses 8-bit DMA only.
    dig_ini = install_dir / "DIG.INI"
    dig_ini.write_text(
        ";\n"
        ";Miles Design Audio Interface Library V3.02 of 18-Jan-95\n"
        ";\n"
        "\n"
        "DEVICE      Creative Labs Sound Blaster or 100% compatible\n"
        "DRIVER      SBLASTER.DIG\n"
        "IO_ADDR     220h\n"
        "IRQ         7\n"
        "DMA_8_BIT   1\n"
        "DMA_16_BIT  -1\n"
    )
    typer.echo(f"Wrote DIG.INI: {dig_ini}")

    # Write MDI.INI — Miles Sound System MIDI driver configuration.
    #
    # PS.EXE reads MDI.INI to select the MIDI/FM-music driver.  SBPRO2.MDI
    # drives the OPL3 chip (Yamaha YMF262) directly via I/O port writes and
    # is the correct choice for DOSBox-X with oplmode=opl3.  This driver is
    # completely independent of the MPU-401 interface.
    #
    # Format confirmed by running SETSOUND.EXE inside DOSBox-X:
    #   IO_ADDR 220h, all other fields -1 (OPL base port 388h is hard-coded
    #   in the driver itself).
    mdi_ini = install_dir / "MDI.INI"
    mdi_ini.write_text(
        ";\n"
        ";Miles Design Audio Interface Library V3.02 of 18-Jan-95\n"
        ";\n"
        "\n"
        "DEVICE      Creative Labs Sound Blaster(TM) 16\n"
        "DRIVER      SBPRO2.MDI\n"
        "IO_ADDR     220h\n"
        "IRQ         -1\n"
        "DMA_8_BIT   -1\n"
        "DMA_16_BIT  -1\n"
    )
    typer.echo(f"Wrote MDI.INI: {mdi_ini}")

    typer.echo("\nInstall complete.")
    if full:
        typer.echo("Run 'c2 run' to launch — no CD required (install dir mounted as fake D: cdrom).")
    else:
        typer.echo("Run 'c2 run --cd <cd-root>' to launch with the CD mounted as D:.")
