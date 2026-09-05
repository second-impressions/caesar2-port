# xmidi — Miles XMIDI sequencer and OPL3 driver

A small C11 library that plays Caesar II's music the way the DOS game did:
the AIL 3.x XMIDI player and the `OPL3.MDI` Miles driver, reimplemented from
the binaries, on top of the Nuked OPL3 chip emulator. No C++, no external
dependencies beyond `third_party/nuked-opl3`.

| File | Reproduces | Source of truth |
| --- | --- | --- |
| `xmidi.c` | XMIDI file layout, `XMI_serve`, controller log, loops, branches, triggers, volume/tempo ramps, the driver's channel preset | AIL 3.x linked into `PS.EXE` (symbols intact) |
| `miles_opl.c` | MIDI → OPL3 register driver: voice allocation, stealing, 4-op pairs, volume, pitch, pan | `HD/OPL3.MDI` (Ghidra, 16-bit real mode) |
| `miles_opl_tables.c` | Frequency, block, velocity, operator/channel maps, 4-op tables, reset register image | Bytes copied from `OPL3.MDI`; verified by `tests/c2_xmidi_test.c` |

## Usage

```c
struct xmi_player *player = xmi_player_create(44100);
xmi_player_load_bank(player, gtl_bytes, gtl_size);        /* CAESAR.OPL / .AD */

struct xmi_sequence *seq = xmi_sequence_create(xmi_player_driver(player));
xmi_sequence_init(seq, xmi_bytes, xmi_size, 0);
xmi_sequence_set_trigger_callback(seq, on_trigger, user);  /* controller 119 */
xmi_sequence_start(seq);

xmi_player_render(player, stereo_int16, frames);         /* serves at 120 Hz */
xmi_sequence_branch(seq, 40);                              /* AIL_branch_index */
```

The sequencer and the synthesizer are independent: `xmi_driver_create` takes
any MIDI message sink, and `miles_opl_message` accepts plain channel-voice
messages, so either half can be tested or replaced on its own.

## Fidelity

Everything that the game can observe follows the originals, including their
oddities: the loop stack is shared by all channels, a branch abandons open
loops, fades are forwarded on every eighth 120 Hz tick and stop being
forwarded once the target is reached, the driver's stealing routine indexes
its partner table by virtual voice, and a sequence plays once unless told
otherwise. One AIL bug is switchable (`XMI_QUIRK_BRANCH_SKIPS_EVENT`, default
on): the event found at a branch target is skipped, which loses the first note
of nine city-score sections.

What is deliberately not reproduced: the DOS driver's 4 KiB timbre cache
(all timbres stay resident), channel locking between sequences, sysex and the
beat/bar callbacks.

## Verification

`tests/c2_xmidi_test.c` runs synthetic scores without assets and, with
`C2_TEST_DATA_DIR` set, checks every driver table against the shipped
`OPL3.MDI`, the same tables inside the sibling FM drivers, the `CAESAR.OPL`
records, branch tables and timbre lists of the five scores, tick-exact trigger
timing, loop and end-of-track behaviour, register-level results of note-on,
volume, pan, bend, sustain, stealing and 4-op pairing, and the player's
service-rate clock. `c2-xmi-render` writes a score to WAV for listening.
