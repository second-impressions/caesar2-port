# Web shell components

The shell intentionally uses native HTML, Pico's accessible controls, and a
small project-owned component layer rather than a JavaScript framework. The
component layer lives in `c2_shell.css`; behavior remains in `c2_shell.js.in`.

## Spacing

`--c2-space-1` through `--c2-space-6` are the shared spacing scale. New
components should use these tokens rather than introducing one-off margins or
gaps.

Vertical rhythm belongs to the parent:

- `.c2-stack` creates a vertical flex stack;
- `--c2-stack-gap` changes the gap for one component;
- stack children have no block margins; and
- hidden children leave no phantom spacing.

This is important for the splash, where the optional status and language rows
can disappear while the title-to-action gap remains stable.

## Primitives

- `.c2-surface`: shared border, background, padding, radius, shadow, and blur.
- `.c2-stack`: reusable vertical flow.
- `.c2-action-grid`: primary splash actions.
- `.c2-choice-grid` / `.c2-source-choice`: asset-source choices.
- `.c2-modal-header`: dialog title and close action.
- `.c2-settings-layout`: tab rail plus fixed content pane.
- `.c2-settings-row`: label/control alignment.
- `.c2-segmented`: accessible radio-backed segmented control.
- `.c2-compact-action` / `.c2-inline-actions`: small settings actions.
- `.c2-hint`: secondary explanatory or status text.

Component classes describe layout and appearance. IDs are reserved for
behavior hooks and ARIA relationships. Avoid styling a component through its ID
unless the rule represents a unique state such as the disabled Play button.

## Adding UI

1. Start with semantic native HTML.
2. Compose existing primitives before adding a component.
3. Put spacing on the parent via `gap`, not on individual children.
4. Use the spacing scale for geometry.
5. Keep keyboard behavior and state in `c2_shell.js.in`.
6. Add a static contract test in `tests/test_port_layering.py`; geometry changes
   should also be checked in Chromium and Firefox.
