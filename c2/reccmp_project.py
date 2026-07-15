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


def expected_original_hash(project_file: Path = PROJECT_FILE) -> str:
    """Read the authoritative original hash from the tracked project file."""
    try:
        return str(
            _project_data(project_file)["targets"][TARGET_ID]["hash"]["sha256"]
        ).lower()
    except (KeyError, TypeError) as exc:
        raise ValueError(
            f"{project_file} has no {TARGET_ID} SHA-256 declaration"
        ) from exc


def _portable_path(path: Path, relative_to: Path) -> str:
    """Return a YAML-friendly path relative to the config directory."""
    return Path(os.path.relpath(path.resolve(), relative_to.resolve())).as_posix()


def write_user_config(
    original: Path = Path("data/PS.EXE"),
    config_path: Path = USER_FILE,
    project_file: Path = PROJECT_FILE,
) -> Path:
    """Validate *original* and publish the machine-local reccmp user file."""
    if not original.is_file():
        raise FileNotFoundError(f"original executable not found: {original}")
    expected = expected_original_hash(project_file)
    actual = _sha256(original)
    if actual != expected:
        raise ValueError(
            f"unexpected PS.EXE SHA-256: got {actual}, expected {expected}"
        )

    payload = {
        "targets": {
            TARGET_ID: {
                "path": _portable_path(original, config_path.parent),
            }
        }
    }
    config_path.write_text(
        yaml.safe_dump(payload, sort_keys=False), encoding="utf-8"
    )
    return config_path


def publish_build_artifacts(
    executable: Path,
    linker_map: Path,
    config_path: Path = BUILD_FILE,
    project_file: Path = PROJECT_FILE,
) -> tuple[Path, Path]:
    """Publish the map beside *executable* and write reccmp-build.yml.

    The bound and unbound images have the same LE virtual addresses, so the
    wlink map produced for ``c2_x.exe`` is also authoritative for the final
    ``PS.EXE`` container.
    """
    if not executable.is_file():
        raise FileNotFoundError(f"rebuilt executable not found: {executable}")
    if not linker_map.is_file():
        raise FileNotFoundError(f"wlink map not found: {linker_map}")
    if not project_file.is_file():
        raise FileNotFoundError(f"reccmp project file not found: {project_file}")

    published_map = executable.with_suffix(".map")
    published_map.parent.mkdir(parents=True, exist_ok=True)
    if published_map.resolve() != linker_map.resolve():
        shutil.copyfile(linker_map, published_map)

    payload = {
        "project": _portable_path(project_file.parent, config_path.parent),
        "targets": {
            TARGET_ID: {
                "path": _portable_path(executable, config_path.parent),
                "map_file": _portable_path(published_map, config_path.parent),
            }
        },
    }
    config_path.write_text(
        yaml.safe_dump(payload, sort_keys=False), encoding="utf-8"
    )
    return published_map, config_path
