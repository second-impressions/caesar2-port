"""Run command: launch Caesar II in DOSBox-X, optionally with a GDB stub for Ghidra.

Two executables can be launched:

* ``--recompiled`` (the DEFAULT): the functional rebuild produced by
  ``c2 rebuild`` (recovered source + delinked AV libraries), staged into
  the install dir as ``PSREBLD.EXE``.  The original ``PS.EXE`` in the
  install is never touched.
* ``--original``: the shipped ``PS.EXE`` via the install's ``c2.bat``.
"""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path
from typing import Annotated

import typer

# Sentinel subdirectory that only exists in a --full install.
# If present the install is self-contained and no CD is needed.
_FULL_INSTALL_MARKER = "xmi"

# The rebuilt exe's 8.3 name inside the install dir (the original
# PS.EXE is left untouched; c2.bat keeps launching it for --original).
_REBUILT_NAME = "PSREBLD.EXE"


def _is_full_install(install_dir: Path) -> bool:
    """Return True if the install dir contains the CD asset subdirectories."""
    return (install_dir / _FULL_INSTALL_MARKER).is_dir()


def _write_dosbox_conf(
    install_dir: Path,
    cd_root: Path | None,
    full_install: bool,
    gdb_port: int | None,
    conf_path: Path,
    game_exe: str | None = None,
) -> None:
    """Write a minimal DOSBox-X config that mounts the game and optionally enables the GDB stub.

    For a full install (all CD assets copied locally) the install dir is also
    mounted as D: with -t cdrom.  This tricks the game's CD-presence check
    (test_cd_drive) into succeeding: it switches to D:, tries open("D:\\"),
    which DOSBox-X allows on a cdrom mount, and proceeds without prompting.
    cd_path() then resolves assets from D:\\xmi\\, D:\\smk\\ etc. — the same
    files since D: and C: point to the same directory.

    For a minimal install the real CD root is mounted as D: instead.
    """
    lines: list[str] = ["[dosbox]", "machine=svga_s3", ""]

    if gdb_port is not None:
        lines += [
            "[gdb]",
            "gdbserver=true",
            f"gdbserver_port={gdb_port}",
            "",
        ]

    lines += [
        "[cpu]",
        "core=normal",
        "cputype=pentium",
        # AIL v2 (Miles Sound System) is timing-sensitive: running at max cycles
        # can cause the DIG driver to produce silence or corrupted audio.
        # 10000 cycles is the community-recommended value for Caesar II.
        "cycles=10000",
        "",
        # Sound Blaster 16 — Caesar II uses the Miles Sound System (AIL v2) for
        # all audio:
        #
        #   Digital audio (.RAW samples via Smacker):
        #     AIL calls getenv("BLASTER") to read I/O address, IRQ and DMA.
        #     DOSBox-X sets BLASTER=A220 I7 D1 H5 T6 P330 automatically when
        #     sbtype=sb16 and irq=7.  The T6 type code causes AIL to select
        #     SB16.DIG.  The correct DOSBox-X option to guarantee this is written
        #     into the DOS environment is:  blaster environment variable=true
        #     (default).  Note: "sbset" is NOT a valid DOSBox-X key; the correct
        #     key name is "blaster environment variable".
        #
        #   MIDI music (.XMI files):
        #     AIL drives the OPL3 chip directly via I/O port writes (SBPRO2.MDI /
        #     ADLIB.MDI).  This is completely independent of the MPU-401 interface.
        #     oplmode=opl3 forces the Yamaha YMF262 (OPL3) emulation so the
        #     SBPRO2.MDI driver's 4-operator FM patches work correctly.
        #     mpu401=intelligent is left in place — it does not interfere with
        #     OPL3 playback and is needed if the game ever tries MPU-401 MIDI.
        #
        #   Known AIL v2 / DOSBox-X issues:
        #     dsp require interrupt acknowledge=false — prevents audio from
        #       stopping after a few seconds if the DSP IRQ is not acknowledged
        #       fast enough (common with AIL v2 games).
        #     dsp busy cycle rate=0 — disables SB16 busy-cycle emulation that
        #       some AIL v2 games are not prepared for.
        "[sblaster]",
        "sbtype=sb16",
        "sbbase=220",
        "irq=7",
        "dma=1",
        "hdma=5",
        "blaster environment variable=true",
        "oplmode=opl3",
        "oplemu=default",
        "dsp require interrupt acknowledge=false",
        "dsp busy cycle rate=0",
        "",
        "[midi]",
        "mpu401=intelligent",
        "mididevice=default",
        "",
        "[dos]",
        "hard drive data rate limit=0",
        "",
        "[autoexec]",
        f"mount c {install_dir}",
    ]

    if full_install:
        # Mount the install dir again as D: with cdrom type so the game's
        # CD-presence check (open("D:\")) succeeds.
        lines += [f"mount d {install_dir} -t cdrom"]
    elif cd_root is not None:
        lines += [f"mount d {cd_root} -t cdrom"]

    lines += [
        # Explicitly set the BLASTER environment variable so the Miles Sound
        # System (AIL v2) can find the SB16 hardware settings.  DOSBox-X
        # should set this automatically via "blaster environment variable=true"
        # in [sblaster], but an explicit SET guarantees it regardless of
        # DOSBox-X version or config parsing quirks.
        #
        # Format: A=I/O base  I=IRQ  D=8-bit DMA  H=16-bit DMA  T=card type
        #   T6 = Sound Blaster 16 (causes AIL to select SB16.DIG)
        #   P=MPU-401 I/O base (330h standard)
        "SET BLASTER=A220 I7 D1 H5 T6 P330",
        "c:",
    ]

    if game_exe is None:
        lines += ["c2.bat"]                 # the original: VESA check + ps.exe
    else:
        # Mirror c2.bat's VESA staging, then launch the given exe instead
        # of the shipped ps.exe.
        lines += [
            "havevesa.exe",
            "if errorlevel 1 UNIVESA.EXE",
            game_exe,
        ]
    lines += [""]

    conf_path.write_text("\n".join(lines))


def run(
    install_dir: Annotated[
        Path,
        typer.Argument(help="Path to the installed Caesar II directory"),
    ] = Path("install/caesar2"),
    cd_root: Annotated[
        Path | None,
        typer.Option(
            "--cd",
            help=(
                "Path to extracted CD root directory.  Required for a minimal "
                "(non-full) install; mounted as D: inside DOSBox-X so the game "
                "can stream XMI/SMK/RAW assets from it."
            ),
        ),
    ] = None,
    gdb: Annotated[
        bool,
        typer.Option("--gdb/--no-gdb", help="Enable the DOSBox-X GDB stub so Ghidra can attach (default: on)"),
    ] = True,
    gdb_port: Annotated[
        int,
        typer.Option("--gdb-port", help="TCP port for the GDB stub (default: 1234)"),
    ] = 1234,
    recompiled: Annotated[
        bool,
        typer.Option(
            "--recompiled/--original",
            help=(
                "Which executable to launch: --recompiled (default) stages the "
                "functional rebuild (c2 rebuild -> build/PS.EXE) into the install "
                f"dir as {_REBUILT_NAME} and runs it; --original runs the shipped "
                "PS.EXE via the install's c2.bat.  The original PS.EXE is never "
                "overwritten."
            ),
        ),
    ] = True,
) -> None:
    """Launch Caesar II in DOSBox-X.

    By default this runs the RECOMPILED game: the functional rebuild from
    'c2 rebuild' (recovered source + delinked AV libraries), staged into the
    install dir as PSREBLD.EXE.  Use --original for the shipped PS.EXE.

    The command auto-detects whether the install is self-contained (created
    with 'c2 cd install --full') or minimal (CD required at runtime):

    \\b
    Self-contained install (no CD needed):

        c2 run                 # the rebuild (default)
        c2 run --original      # the shipped PS.EXE

    Minimal install (CD must be provided):

        c2 run --cd path/to/cd-root

    With --gdb, DOSBox-X exposes a GDB remote stub on the given port so that
    Ghidra (or gdb) can connect for live debugging.  DOSBox-X will pause at
    startup waiting for the debugger to attach before resuming execution:

        c2 run --gdb --gdb-port 1234
        c2 run --cd path/to/cd-root --gdb
    """
    if not install_dir.exists() or not install_dir.is_dir():
        typer.echo(f"Error: install directory not found: {install_dir}", err=True)
        typer.echo("Run 'c2 cd install <cd-root>' first.", err=True)
        raise typer.Exit(1)

    full = _is_full_install(install_dir)

    if not full and cd_root is None:
        typer.echo(
            "Warning: this is a minimal install (no xmi/ subdir found).  "
            "Music, videos and sound effects will be missing.",
            err=True,
        )
        typer.echo(
            "  Tip: re-run with --cd <cd-root> to mount the CD, or reinstall "
            "with 'c2 cd install --full' for a self-contained install.",
            err=True,
        )

    if cd_root is not None and (not cd_root.exists() or not cd_root.is_dir()):
        typer.echo(f"Error: CD root not found: {cd_root}", err=True)
        raise typer.Exit(1)

    game_exe: str | None = None
    if recompiled:
        # Bring the rebuild up to date (incremental: ~0.5 s when warm) and
        # stage it into the install dir under its own 8.3 name.  The
        # shipped PS.EXE is never touched.
        from c2.commands.rebuild import rebuild as _rebuild

        built = Path("build/PS.EXE")
        try:
            _rebuild()
        except SystemExit as e:          # typer.Exit from a failed build
            if getattr(e, "code", 1):
                typer.echo("Error: 'c2 rebuild' failed — fix the build or "
                           "run with --original.", err=True)
                raise typer.Exit(1)
        if not built.exists():
            typer.echo(f"Error: {built} not found after rebuild.", err=True)
            raise typer.Exit(1)
        staged = install_dir / _REBUILT_NAME
        data = built.read_bytes()
        if not staged.exists() or staged.read_bytes() != data:
            staged.write_bytes(data)
        game_exe = _REBUILT_NAME

    effective_gdb_port = gdb_port if gdb else None

    with tempfile.NamedTemporaryFile(
        suffix=".conf", prefix="caesar2-dosbox-", delete=False, mode="w"
    ) as tmp:
        conf_path = Path(tmp.name)

    _write_dosbox_conf(install_dir, cd_root, full, effective_gdb_port, conf_path,
                       game_exe=game_exe)

    typer.echo(f"Install dir : {install_dir}  ({'full' if full else 'minimal'})")
    typer.echo(f"Executable  : "
               + (f"{_REBUILT_NAME}  (the c2 rebuild; --original for the shipped PS.EXE)"
                  if recompiled else "PS.EXE  (original, via c2.bat)"))
    if cd_root:
        typer.echo(f"CD root     : {cd_root}  (mounted as D:)")
    if gdb:
        typer.echo(f"GDB stub    : enabled on port {gdb_port}")
        typer.echo(f"  → In Ghidra: Debugger → Connect → Remote GDB  host=localhost  port={gdb_port}")
        typer.echo("  DOSBox-X will pause at startup until the debugger attaches.")
    typer.echo(f"DOSBox conf : {conf_path}")
    typer.echo("")

    cmd = ["dosbox-x", "-conf", str(conf_path)]
    typer.echo(f"Launching: {' '.join(cmd)}")

    try:
        subprocess.run(cmd, check=False)
    finally:
        conf_path.unlink(missing_ok=True)
