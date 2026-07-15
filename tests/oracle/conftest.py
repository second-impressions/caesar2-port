"""Shared helpers for oracle-based rule verification tests."""
from __future__ import annotations

import shutil
import subprocess

import pytest


def _have_podman_image(image: str) -> bool:
    if not shutil.which("podman"):
        return False
    proc = subprocess.run(
        ["podman", "image", "exists", image],
        capture_output=True,
    )
    return proc.returncode == 0


@pytest.fixture(scope="session")
def watcom_10_0a():
    """Skip oracle tests when the 10.0a container image isn't available."""
    from c2.commands.oracle import IMAGE_10_0A
    if not _have_podman_image(IMAGE_10_0A):
        pytest.skip(f"podman image {IMAGE_10_0A} not present")
    return IMAGE_10_0A


# Standard "two snippet" pattern: same function, same externs, two formulations.
def two_snippets(
    *, externs: str, defs: str, body_right: str, body_wrong: str,
    proto: str, fn_name: str,
) -> tuple[str, str, str]:
    """Build a (right_src, wrong_src, defs_src) triple for an oracle test.

    The two source variants share identical extern declarations and only
    differ in the body of ``fn_name``.  ``defs`` is compiled separately
    so the externs in ``body_*`` resolve at link time but tentative
    definitions don't change codegen in the primary TU.
    """
    template = f"{externs}\n\n{proto}\n{{\n{{body}}\n}}\n"
    return (
        template.replace("{body}", body_right),
        template.replace("{body}", body_wrong),
        defs,
    )
