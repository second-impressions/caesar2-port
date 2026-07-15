"""Project configuration loader.

Reads ``.c2-extension.yml`` from the repo root (or any ancestor) and
produces a frozen :class:`ProjectConfig` object plus the active
:class:`Toolchain` instance.

Two equivalent config shapes are supported:

* **Single-target** (legacy) — top-level ``toolchain:`` + ``project:``
  blocks.  One implicit target named ``default``.
* **Multi-target** — a ``targets:`` map of named targets, each with its
  own ``toolchain:`` + ``project:`` block, plus a top-level
  ``default_target:`` selecting which one is active by default.

Either shape can be combined with the top-level ``run:`` / ``embed:``
blocks (those are toolchain-agnostic and shared across targets).

To select a non-default target, callers pass ``target=<name>`` to
:meth:`ProjectConfig.load`, or the ``c2-ext`` CLI accepts ``--target``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

import yaml

if TYPE_CHECKING:
    from c2.decompile._engine.toolchains.base import Toolchain


CONFIG_FILENAME = ".c2-extension.yml"
DEFAULT_TARGET_NAME = "default"


@dataclass(frozen=True)
class ToolchainSpec:
    """Toolchain-specific knobs from the config file."""

    name: str = "watcom-10.0a"
    cc: str = "wcc386"
    cflags: tuple[str, ...] = ("-bt=dos", "-mf", "-4r", "-s", "-d1")
    calling_convention: str = "watcall"
    arch: str = "x86-32"
    # Optional: podman image used to run the compiler.  When set, the
    # toolchain spawns the compiler inside this container; otherwise it
    # uses a host-installed ``cc``.  Watcom defaults to the project's
    # ``localhost/watcom-10.0a-wibo`` image; MSVC defaults to
    # ``localhost/msvc-4.00-wibo``.
    compiler_image: str | None = None
    # Optional: extra defines / force-includes that need to be passed on
    # every compile (e.g. ``-D__pascal=`` for MSVC, which doesn't know
    # the Watcom calling-convention keyword).
    extra_defines: tuple[str, ...] = ()


@dataclass(frozen=True)
class ProjectConfig:
    """Resolved per-project configuration, scoped to ONE active target.

    Paths are absolute; toolchain spec is normalized; the embedding
    section defaults to a working jina-v2 pipeline.

    ``targets`` holds the unresolved raw data for every other configured
    target so callers can introspect what's available without reloading
    the YAML; ``active_target`` names which one this :class:`ProjectConfig`
    is bound to.
    """

    root: Path
    """Repo root — the directory containing the config file."""

    active_target: str
    """Name of the currently-bound target (e.g. ``watcom`` or ``msvc``)."""

    toolchain_spec: ToolchainSpec

    target_binary: Path
    """Path to the binary we're decompiling (e.g. data/PS.EXE)."""

    symbols_json: Path
    """Symbol DB extracted from the binary."""

    headers_dir: Path
    """Directory holding project headers, copied into each run dir."""

    sources_dir: Path
    """Directory holding the existing decomp .c sources (used to lift function bodies)."""

    cache_dir: Path
    """Per-project cache (embeddings, build cache)."""

    runs_root: Path
    """Where new run directories are created."""

    # Optional per-target supplementary maps.  These default to ``None``
    # when the target doesn't need them.
    func_map: Path | None = None
    """ps_name → target_va map (used by the MSVC target; the Watcom target
    encodes the mapping in ``symbols_json`` directly)."""

    globals_map: Path | None = None
    """name → data-symbol VA map (used by the MSVC target to resolve
    memory-operand displacements)."""

    default_body: str = "existing"  # "existing" | "blank"

    embed_model: str = "jinaai/jina-embeddings-v2-base-code"
    embed_dim: int = 768
    embed_pool: str = "byte_exact_only"

    # Names of every target declared in the YAML — useful for the CLI
    # `--target=...` validator and orchestrator UX.
    available_targets: tuple[str, ...] = ()
    """All target names declared in the config (sorted)."""

    default_target: str = DEFAULT_TARGET_NAME
    """The target picked when no ``--target`` flag is supplied."""

    @classmethod
    def load(cls, start: Path | None = None,
             *, target: str | None = None) -> "ProjectConfig":
        """Find ``.c2-extension.yml`` walking up from ``start`` (or cwd).

        If ``start`` (or cwd) contains a run-dir ``meta.json`` with a
        ``project_root`` key, that path is used directly — letting the
        agent tools work from a run dir nested anywhere on disk.  When
        the meta.json also carries a ``target`` field, it is used as the
        default if no explicit ``target`` argument is given.
        """
        s = start or Path.cwd()
        meta = s / "meta.json"
        meta_target: str | None = None
        if meta.is_file():
            try:
                data = json.loads(meta.read_text())
                root = data.get("project_root")
                meta_target = data.get("target")
                if root:
                    candidate = Path(root) / CONFIG_FILENAME
                    if candidate.is_file():
                        return cls.from_file(
                            candidate, target=target or meta_target,
                        )
            except (OSError, json.JSONDecodeError):
                pass
        path = find_config(s)
        return cls.from_file(path, target=target or meta_target)

    @classmethod
    def from_file(cls, config_path: Path,
                  *, target: str | None = None) -> "ProjectConfig":
        root = config_path.parent.resolve()
        data = yaml.safe_load(config_path.read_text()) or {}

        # Discover the targets table.  Either:
        #   - new shape: data["targets"] = {name: {toolchain, project}}
        #     with optional data["default_target"]
        #   - legacy shape: top-level "toolchain" + "project" become a
        #     single implicit "default" target
        targets_raw: dict[str, dict] = data.get("targets") or {}
        if not targets_raw:
            legacy = {
                "toolchain": data.get("toolchain") or {},
                "project": data.get("project") or {},
            }
            targets_raw = {DEFAULT_TARGET_NAME: legacy}
            default_target = DEFAULT_TARGET_NAME
        else:
            default_target = data.get("default_target")
            if default_target is None:
                # No explicit default → fall back to the first one declared.
                default_target = next(iter(targets_raw))
            if default_target not in targets_raw:
                raise ValueError(
                    f"default_target {default_target!r} is not one of "
                    f"the declared targets: {sorted(targets_raw)}"
                )

        active = target or default_target
        if active not in targets_raw:
            raise ValueError(
                f"target {active!r} not declared in {config_path}; "
                f"available: {sorted(targets_raw)}"
            )

        tgt_raw = targets_raw[active]
        tc = tgt_raw.get("toolchain") or {}
        tc_spec = ToolchainSpec(
            name=tc.get("name", "watcom-10.0a"),
            cc=tc.get("cc", "wcc386"),
            cflags=tuple(tc.get("cflags", ["-bt=dos", "-mf", "-4r", "-s", "-d1"])),
            calling_convention=tc.get("calling_convention", "watcall"),
            arch=tc.get("arch", "x86-32"),
            compiler_image=tc.get("compiler_image"),
            extra_defines=tuple(tc.get("extra_defines", ())),
        )

        proj = tgt_raw.get("project") or {}
        target_binary = _resolve_path(proj.get("target_binary", "data/PS.EXE"), root)
        symbols_json = _resolve_path(proj.get("symbols", "data/out/symbols.json"), root)
        headers_dir = _resolve_path(proj.get("headers_dir", "decomp/include"), root)
        sources_dir = _resolve_path(proj.get("sources_dir", "decomp/src"), root)
        func_map_raw = proj.get("func_map")
        globals_map_raw = proj.get("globals_map")
        func_map = _resolve_path(func_map_raw, root) if func_map_raw else None
        globals_map = _resolve_path(globals_map_raw, root) if globals_map_raw else None
        cache_dir = _resolve_path(
            proj.get("cache_dir", "~/.cache/c2-ext/caesar2"), root
        )

        # `run:` / `embed:` are toolchain-agnostic — read once from the
        # top level (legacy + new shape both).
        run = data.get("run") or {}
        runs_root = _resolve_path(run.get("root", "~/.cache/c2-ext/runs"), root)
        default_body = run.get("default_body", "existing")
        if default_body not in ("existing", "blank"):
            raise ValueError(
                f"run.default_body must be 'existing' or 'blank', got {default_body!r}"
            )

        embed = data.get("embed") or {}

        return cls(
            root=root,
            active_target=active,
            toolchain_spec=tc_spec,
            target_binary=target_binary,
            symbols_json=symbols_json,
            headers_dir=headers_dir,
            sources_dir=sources_dir,
            func_map=func_map,
            globals_map=globals_map,
            cache_dir=cache_dir,
            runs_root=runs_root,
            default_body=default_body,
            embed_model=embed.get("model", "jinaai/jina-embeddings-v2-base-code"),
            embed_dim=int(embed.get("dim", 768)),
            embed_pool=embed.get("pool", "byte_exact_only"),
            available_targets=tuple(sorted(targets_raw)),
            default_target=default_target,
        )

    def toolchain(self) -> "Toolchain":
        """Construct the active Toolchain instance for this project."""
        from c2.decompile._engine.toolchains.base import get_toolchain
        return get_toolchain(self.toolchain_spec.name)(self)

    def for_target(self, target: str) -> "ProjectConfig":
        """Return a fresh :class:`ProjectConfig` bound to ``target``.

        Convenience for tools that need to switch targets without
        re-parsing the YAML (e.g. orchestrator listing both Watcom and
        MSVC verdicts for a function).
        """
        if target == self.active_target:
            return self
        return ProjectConfig.from_file(self.root / CONFIG_FILENAME, target=target)


def find_config(start: Path) -> Path:
    """Walk up from ``start`` looking for :data:`CONFIG_FILENAME`."""
    here = start.resolve()
    while True:
        candidate = here / CONFIG_FILENAME
        if candidate.is_file():
            return candidate
        if here == here.parent:
            raise FileNotFoundError(
                f"{CONFIG_FILENAME} not found in {start} or any ancestor"
            )
        here = here.parent


def _resolve_path(value: str, root: Path) -> Path:
    """Resolve a path from the config — expand ``~``, make absolute relative to ``root``."""
    p = Path(value).expanduser()
    return p if p.is_absolute() else (root / p).resolve()
