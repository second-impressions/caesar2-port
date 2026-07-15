"""``c2.forge`` -- targeted, low-boilerplate codegen-experiment harness.

The cgex successor.  Authoring an investigative experiment is one or
two dozen lines of targeted DSL; massive composition + warm-container
workers do the heavy lifting.

**Read the skill first**: ``.pi/skills/forge/SKILL.md`` is the canonical
cheatsheet + user guide.  In a REPL, ``from c2.forge import skill_path;
print(open(skill_path()).read())`` dumps it inline.

Quick start::

    from c2.forge import Forge

    with Forge("show_menus", file="controls.c") as f:
        f.preset("tie_group")               # bulk candidates
        f.swap_decls("sx", "sy")            # targeted candidate
        f.commute_at(line=147)              # another
        summary = f.run("pairs", jobs=6)    # cartesian, 1200+ plans
        summary.show()
        f.apply(summary.best().plan)        # text-preserving splice

Imports are lazy: the heavy modules (pool, build, worker, ps_ref) are
only loaded when ``Forge.run()`` or ``ps_ref.load()`` actually need
them, so ``import c2.forge`` is essentially free.
"""

from __future__ import annotations

from pathlib import Path


#
# We avoid importing the worker / pool / builder at module load time so
# REPL startup and toolapi import paths stay snappy.  The Forge class
# itself is light: it touches tree-sitter (via c2.forge.cspan) lazily
# on first span query.


def __getattr__(name):
    # PEP 562 lazy attribute load -- only first access triggers the heavy
    # imports the symbol requires.
    if name == "Forge":
        from c2.forge.experiment import Forge
        return Forge
    if name == "Summary":
        from c2.forge.experiment import Summary
        return Summary
    if name == "PlanResult":
        from c2.forge.experiment import PlanResult
        return PlanResult
    if name == "Score":
        from c2.forge.judge import Score
        return Score
    if name == "score":
        from c2.forge.judge import score
        return score
    if name == "TextEdit":
        from c2.forge.edits import TextEdit
        return TextEdit
    if name == "Candidate":
        from c2.forge.edits import Candidate
        return Candidate
    if name == "EditPlan":
        from c2.forge.edits import EditPlan
        return EditPlan
    if name == "load_ps_ref":
        from c2.forge.ps_ref import load
        return load
    if name == "PSRef":
        from c2.forge.ps_ref import PSRef
        return PSRef
    if name == "FnSpan":
        from c2.forge.cspan import FnSpan
        return FnSpan
    if name == "DecisionMatrix":
        from c2.forge.matrix import DecisionMatrix
        return DecisionMatrix
    if name == "RunStore":
        from c2.forge.runstore import RunStore
        return RunStore
    if name == "PRESETS":
        from c2.forge.presets import PRESETS
        return PRESETS
    raise AttributeError(f"module 'c2.forge' has no attribute {name!r}")


__all__ = [
    "Forge", "Summary", "PlanResult",
    "Score", "score",
    "TextEdit", "Candidate", "EditPlan",
    "PSRef", "load_ps_ref",
    "FnSpan", "DecisionMatrix", "RunStore", "PRESETS",
    "skill_path",
]


def skill_path() -> Path:
    """Return the absolute path to ``forge``'s pi skill.

    Useful from a REPL when you've forgotten the DSL surface::

        from c2.forge import skill_path
        print(open(skill_path()).read())

    or from a custom shell::

        less "$(uv run python -c 'from c2.forge import skill_path;
            print(skill_path())')"

    The skill is the single canonical cheatsheet -- this module never
    embeds API documentation inline (it would drift).
    """
    # Try project-local first (the source-of-truth location while you're
    # in a clone of the caesar2 repo).
    here = Path.cwd() / ".pi" / "skills" / "forge" / "SKILL.md"
    if here.exists():
        return here
    # Fall back to walking up from this module.
    p = Path(__file__).resolve()
    for parent in p.parents:
        cand = parent / ".pi" / "skills" / "forge" / "SKILL.md"
        if cand.exists():
            return cand
    raise FileNotFoundError(
        "forge skill not found -- expected .pi/skills/forge/SKILL.md")
