# Versioned text assets

Caesar II's `C2.ENG` is not one invariant resource. Official releases pair
several revisions of the `Textfile` data with different revisions of the game
engine. The portable build must accept those resources as shipped; it must not
rewrite them on disk or identify them from a release hash.

The compatibility rule is structural: inspect the loaded offset table and
enable only behavior for which the referenced string group contains the
required strings. This also works with localized and user-supplied resources.

## Known official files

All eight distinct DOS and Windows text resources in the PC release corpus
have the `Textfile` magic, 147 offset-table entries, and a first payload offset
of `0x254`. Their group contents are not identical.

| Resource family | SHA-256 prefix | Bytes | Unique payload offsets | Navigable strings | New Game group `0x2b` | Region quote group `0x45` |
|---|---:|---:|---:|---:|---:|---:|
| early English DOS | `581da6ed` | 31,876 | 142 | 1,293 | 18 | 29 |
| Europe-original English DOS | `d1a7af20` | 31,880 | 142 | 1,293 | 18 | 29 |
| French-original DOS | `9f549492` | 32,954 | 142 | 1,298 | 18 | 30 |
| German-original DOS | `0c0f5a4a` | 36,598 | 142 | 1,292 | 18 | 29 |
| late English DOS | `3c448a3c` | 32,734 | 143 | 1,315 | 19 | 31 |
| English Windows | `bbf703a7` | 32,760 | 143 | 1,315 | 19 | 31 |
| German rerelease DOS | `93d43583` | 38,248 | 143 | 1,314 | 19 | 31 |
| German Windows | `e26ac14f` | 38,232 | 143 | 1,314 | 19 | 31 |

“Navigable strings” applies the boundary rule used by `font_list`, once per
unique payload offset so aliased table entries are not counted repeatedly.

Localization can change the number of NUL-delimited pieces without indicating
an engine revision. The French file, for example, splits one long regional
advice sentence and therefore has 30 entries in group `0x45`, but it does not
contain the two messages added by the late engine. Consequently, the late
regional-query capability requires string index 30, not merely index 29.

Other observed count differences relative to early English are:

- French groups 11, 46, 69, 70, 76, and 77 differ because translated text is
  segmented differently.
- German group 146 has three strings where English has four.
- The late files change the alias layout around groups 116–120. Groups
  116–118 then expose a larger shared payload block; this is not a New Game UI
  feature.

These are why compatibility is capability-based rather than a global
“old/new” flag.

## New Game UI evolution

The old New Game group ends at index 17, “Start this Game” (translated in the
localized files). The late group adds index 18, “Cancel” or “Abbrechen”. The
five difficulty names remain a separate, unchanged five-string group at
`0x2c`.

The engine changed with the resource:

| Engine | Dialog height | Labels at bottom | Skill-detail buttons |
|---|---:|---:|---:|
| DOS 1995-09 / 1995-10 | `0x14` | group `0x2b`, index 17 | 5 |
| DOS 1996-04 | `0x16` | group `0x2b`, indices 17 and 18 | 6 |
| Windows builds A, B, and C | `0x16` | group `0x2b`, indices 17 and 18 | 6 |

The 1995 constants were recovered from both release executables. Their
`show_skill2_box` bodies are 124 bytes and omit the complete 32-byte
`font_list(0x2b, 0x12, ...)` call. Their `skill2_game_loop` bodies pass five
to both `show_buttons` and `control_buttons`. The later DOS body is 156 bytes
and passes six. After masking linked addresses, the Windows function body is
identical in builds A, B, and C.

With an old asset and the late engine, unbounded `font_list` traversal walks
past group `0x2b` into group `0x2c`; index 18 therefore renders “Novice”. The
sixth button remains active and the dialog retains the late height. This is a
cross-version mismatch, not a rendering or encoding problem.

## Regional-query evolution

Late group `0x45` adds two messages:

- index 29: production reduced by a gate between the city and an industry;
- index 30: an empty warehouse.

The 1995 `show_region_query_panel` and `reg_industry_quote` code predates both
messages. An empty warehouse selects the old “very few goods” message at
index 13. An outside industry follows the old workforce/output selection
instead of selecting index 29. The 1996 engine adds the two new choices.

## Port implementation boundary

`src/platform/common/c2_port_text_compat.c` parses the in-memory offset table
read-only. It neither changes the asset file nor rewrites `text_buffer`. It
exposes named structural capabilities for the two verified code/resource
evolution points.

The recovered 1996 engine source remains the default path. The few places
where constants and game/UI selection genuinely changed are guarded by
`PORT_FEAT_TEXT_ASSET_COMPAT`; their `#else` branches retain the shipped 1996
statements. CMake exposes this as `PORT_ENABLE_TEXT_ASSET_COMPAT`, enabled for
the portable build and switchable off for comparison.

The guarded adaptation does the following:

- group `0x2b` has index 18: use the 1996 dialog height, Cancel label, and six
  buttons;
- group `0x2b` lacks index 18: use the recovered 1995 dialog height, omit the
  label, and use five buttons;
- group `0x45` has index 30: use the 1996 empty-warehouse and outside-industry
  messages;
- group `0x45` lacks index 30: use the recovered 1995 selections.

Adding another compatibility case requires both sides of the same evidence:
a structural resource difference and a corresponding engine-code difference.
Do not infer behavior from file size, language, filename, or hash alone.
