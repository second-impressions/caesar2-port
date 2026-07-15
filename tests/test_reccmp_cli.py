"""CLI wiring for the stock reccmp report commands."""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from c2.app import app
from c2.commands import reccmp as reccmp_command


runner = CliRunner()


@pytest.mark.parametrize(
    ("command", "module", "extra"),
    [
        ("code", "reccmp.tools.asmcmp", ["--json", "report.json", "--silent"]),
        ("data", "reccmp.tools.datacmp", ["--all", "--no-color"]),
    ],
)
def test_report_commands_forward_stock_reccmp_options(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    command: str,
    module: str,
    extra: list[str],
):
    monkeypatch.chdir(tmp_path)
    for name in ("reccmp-project.yml", "reccmp-user.yml", "reccmp-build.yml"):
        (tmp_path / name).write_text("", encoding="utf-8")

    calls = []
    monkeypatch.setattr(
        reccmp_command,
        "_run_module",
        lambda actual_module, args: calls.append((actual_module, args)),
    )

    result = runner.invoke(app, ["reccmp", command, *extra])

    assert result.exit_code == 0, result.output
    assert calls == [(module, extra)]


def test_report_command_explains_missing_generated_configuration(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["reccmp", "code"])

    assert result.exit_code != 0
    assert "c2 reccmp prepare" in result.output
    assert "c2 rebuild" in result.output


def test_rebuild_help_exposes_reccmp_publication_switch():
    result = runner.invoke(app, ["rebuild", "--help"])

    assert result.exit_code == 0
    assert "--reccmp" in result.output
    assert "--no-reccmp" in result.output
    assert "--reccmp-config" in result.output
