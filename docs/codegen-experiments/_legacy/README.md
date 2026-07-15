# Legacy cgex experiments (archived)

These 119 files were written against `c2.commands.cgex` (the
isolated/decomp-bound oracle harness deleted when `c2 forge` landed).
They no longer run.

They are kept here because **the docstring of each file is a worked-out
note** on a Watcom 10.0a codegen quirk -- the inferred mechanism, the
verified lever, sometimes a worked example with offsets.  That body of
evidence is what eventually crystallised into the regalloc-model
documentation (`docs/wcc386-re/regalloc-model.md`) and into forge's
built-in lever set (`c2 forge ls-levers`).

If you find yourself reaching for one of these files for its conclusion,
that conclusion is also captured somewhere durable:

* **regalloc levers** -- ported into `c2/forge/levers/` (firstassign,
  decl_order, stmt_swap, width, commute, relorder, split/fuse, …).  See
  `c2 forge ls-levers`.
* **Codegen-form flips** -- ported into `c2/forge/levers/codegen_forms.py`
  (shift1, bytemask, derefform).
* **Cross-version / cost-model findings** -- captured in
  `docs/watcom-codegen-patterns.md` and
  `docs/wcc386-re/regalloc-model.md`.
* **Source-style rules** -- captured in `docs/observed-source-style.md`.

If you need to RE-RUN one of these as a forge experiment, lift the
prelude/body into the new DSL.  Examples in this directory (one level
up) show the pattern.  Most cgex experiments map cleanly onto a forge
experiment with a few `forge.use(...)` lines plus a custom `@forge.lever`
if the test was probing a pattern outside the built-in palette.
