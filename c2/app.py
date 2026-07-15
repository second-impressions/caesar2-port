"""Main typer application for the c2 toolkit."""

import os as _os

# Plain-text output: the c2 tools emit NO ANSI colour by default -- cleaner
# for piping, logs, diffing, and agent consumption.  Rich honours NO_COLOR
# (it still parses `[markup]` so tags are consumed, just no colour codes are
# emitted).  Set this BEFORE any command module is imported so every Console
# in the process picks it up.  Opt back in with `C2_COLOR=1`.
if _os.environ.get("C2_COLOR", "").lower() not in ("1", "true", "yes"):
    _os.environ.setdefault("NO_COLOR", "1")

import typer

from c2.commands.compare import compare
from c2.commands.decomp import decomp
from c2.commands.sym import sym
from c2.commands.gen_header import gen_header
from c2.commands.disasm import disasm
from c2.commands.xrefs import xrefs
from c2.commands.textfile import app as textfile_app
from c2.commands.image import app as image_app
from c2.commands.export import export
from c2.commands.hash import hash_cmd
from c2.commands.install import install
from c2.commands.run import run
from c2.commands.scan import scan
from c2.commands.unpack import unpack
from c2.commands.delink import delink
from c2.commands.rebuild import rebuild
from c2.commands.reccmp import app as reccmp_app

app = typer.Typer(
    name="c2",
    help="Caesar II reconstruction toolkit.",
    no_args_is_help=True,
)

cd_app = typer.Typer(
    help="CD management commands (unpack, hash, install, compare).",
    no_args_is_help=True,
)
app.add_typer(cd_app, name="cd")

# Game asset tooling
app.add_typer(image_app, name="image")
app.add_typer(textfile_app, name="textfile")

# Build & link toolchain
app.command("export")(export)
app.command("decomp")(decomp)
app.command("delink")(delink)
app.command("rebuild")(rebuild)
app.add_typer(reccmp_app, name="reccmp")
app.command("gen-header")(gen_header)

# Inspection utilities
app.command("sym")(sym)
app.command("disasm")(disasm)
app.command("xrefs")(xrefs)

# Runtime
app.command("run")(run)

# CD subgroup commands
cd_app.command("unpack")(unpack)
cd_app.command("hash")(hash_cmd)
cd_app.command("install")(install)
cd_app.command("compare")(compare)
cd_app.command("scan")(scan)
