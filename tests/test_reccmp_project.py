"""Tests for the Caesar II/reccmp project boundary."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
import yaml

from c2.reccmp_project import (
    TARGET_ID,
    publish_build_artifacts,
    write_user_config,
)
from reccmp.project.config import Compiler, ProjectFile


def _write_project(path: Path, original: bytes) -> None:
    digest = hashlib.sha256(original).hexdigest()
    path.write_text(
        yaml.safe_dump(
            {
                "targets": {
                    TARGET_ID: {
                        "filename": "PS.EXE",
                        "compiler": "watcom",
                        "source-root": ["decomp/src"],
                        "hash": {"sha256": digest},
                    }
                }
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )


def test_tracked_project_selects_watcom_pipeline():
    project = ProjectFile.from_file(Path("reccmp-project.yml"))
    target = project.targets[TARGET_ID]

    assert target.compiler == Compiler.WATCOM
    assert target.filename == "PS.EXE"
    assert target.source_root == (Path("decomp/src"),)


def test_write_user_config_validates_and_relativizes_original(tmp_path: Path):
    original_data = b"synthetic original"
    project_file = tmp_path / "reccmp-project.yml"
    original = tmp_path / "inputs" / "PS.EXE"
    config = tmp_path / "reccmp-user.yml"
    original.parent.mkdir()
    original.write_bytes(original_data)
    _write_project(project_file, original_data)

    assert write_user_config(original, config, project_file) == config
    assert yaml.safe_load(config.read_text(encoding="utf-8")) == {
        "targets": {TARGET_ID: {"path": "inputs/PS.EXE"}}
    }


def test_write_user_config_rejects_wrong_original(tmp_path: Path):
    project_file = tmp_path / "reccmp-project.yml"
    original = tmp_path / "PS.EXE"
    original.write_bytes(b"wrong")
    _write_project(project_file, b"expected")

    with pytest.raises(ValueError, match="unexpected PS.EXE SHA-256"):
        write_user_config(original, tmp_path / "reccmp-user.yml", project_file)


def test_publish_build_artifacts_copies_map_and_writes_discovery(tmp_path: Path):
    project_file = tmp_path / "reccmp-project.yml"
    config = tmp_path / "reccmp-build.yml"
    executable = tmp_path / "build" / "PS.EXE"
    linker_map = tmp_path / "cache" / "ps.map"
    executable.parent.mkdir()
    linker_map.parent.mkdir()
    executable.write_bytes(b"LE image")
    linker_map.write_text("wlink map", encoding="latin1")
    _write_project(project_file, b"unused")

    published_map, written_config = publish_build_artifacts(
        executable, linker_map, config, project_file
    )

    assert published_map == executable.with_suffix(".map")
    assert published_map.read_text(encoding="latin1") == "wlink map"
    assert written_config == config
    assert yaml.safe_load(config.read_text(encoding="utf-8")) == {
        "project": ".",
        "targets": {
            TARGET_ID: {
                "path": "build/PS.EXE",
                "map_file": "build/PS.map",
            }
        },
    }
