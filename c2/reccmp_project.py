"""Caesar II's small adapter around reccmp's three project files.

The canonical target configuration is tracked in ``reccmp-project.yml``.
The original executable and rebuilt artifacts are machine-local, so this
module writes the ignored user/build files after validating their inputs.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import shutil

import yaml


TARGET_ID = "C2"
WINDOWS_TARGET_ID = "C2WIN"
PROJECT_FILE = Path("reccmp-project.yml")
USER_FILE = Path("reccmp-user.yml")
BUILD_FILE = Path("reccmp-build.yml")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _project_data(project_file: Path = PROJECT_FILE) -> dict:
    data = yaml.safe_load(project_file.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"invalid reccmp project file: {project_file}")
    return data


def expected_original_hash(
    project_file: Path = PROJECT_FILE,
    target_id: str = TARGET_ID,
) -> str:
    """Read a target's authoritative original hash from the project file."""
    try:
        return str(
            _project_data(project_file)["targets"][target_id]["hash"]["sha256"]
        ).lower()
    except (KeyError, TypeError) as exc:
        raise ValueError(
            f"{project_file} has no {target_id} SHA-256 declaration"
        ) from exc


def _portable_path(path: Path, relative_to: Path) -> str:
    """Return a YAML-friendly path relative to the config directory."""
    return Path(os.path.relpath(path.resolve(), relative_to.resolve())).as_posix()


def write_user_config(
    original: Path = Path("original/PS.EXE"),
    config_path: Path = USER_FILE,
    project_file: Path = PROJECT_FILE,
    windows_original: Path | None = None,
) -> Path:
    """Validate the supplied originals and publish reccmp's user file."""

    def validate(path: Path, target_id: str) -> None:
        if not path.is_file():
            raise FileNotFoundError(f"original executable not found: {path}")
        expected = expected_original_hash(project_file, target_id)
        actual = _sha256(path)
        if actual != expected:
            raise ValueError(
                f"unexpected {path.name} SHA-256: got {actual}, expected {expected}"
            )

    validate(original, TARGET_ID)

    payload = {
        "targets": {
            TARGET_ID: {
                "path": _portable_path(original, config_path.parent),
            }
        }
    }
    if windows_original is not None:
        validate(windows_original, WINDOWS_TARGET_ID)
        payload["targets"][WINDOWS_TARGET_ID] = {
            "path": _portable_path(windows_original, config_path.parent),
        }
    config_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return config_path


def publish_build_artifacts(
    executable: Path,
    linker_map: Path,
    published_executable: Path | None = None,
    config_path: Path = BUILD_FILE,
    project_file: Path = PROJECT_FILE,
) -> tuple[Path, Path, Path]:
    """Publish the analysis executable and map, then write build discovery.

    reccmp must inspect the linker's pre-bind ``c2_x.exe`` rather than the
    runnable ``PS.EXE``. Once the non-debug image is exact, the latter grafts
    PS's original debug trailer and therefore no longer describes the symbols
    emitted by the reconstruction build.
    """
    if not executable.is_file():
        raise FileNotFoundError(f"rebuilt executable not found: {executable}")
    if not linker_map.is_file():
        raise FileNotFoundError(f"wlink map not found: {linker_map}")
    if not project_file.is_file():
        raise FileNotFoundError(f"reccmp project file not found: {project_file}")

    if published_executable is None:
        published_executable = executable
    published_executable.parent.mkdir(parents=True, exist_ok=True)
    if published_executable.resolve() != executable.resolve():
        shutil.copyfile(executable, published_executable)

    published_map = published_executable.with_suffix(".map")
    published_map.parent.mkdir(parents=True, exist_ok=True)
    if published_map.resolve() != linker_map.resolve():
        shutil.copyfile(linker_map, published_map)

    payload = {
        "project": _portable_path(project_file.parent, config_path.parent),
        "targets": {
            TARGET_ID: {
                "path": _portable_path(published_executable, config_path.parent),
                "map_file": _portable_path(published_map, config_path.parent),
            }
        },
    }
    config_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return published_executable, published_map, config_path
