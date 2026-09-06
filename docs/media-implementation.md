# Audio and movie implementation decision record

Status: accepted architecture, recorded 2026-07-21. SDL3 effects and speech,
libsmacker movies, and branch-aware XMIDI/OPL3 music (the port's own `xmidi`
library) are implemented on the native SDL3 target.

## Outcome

Do not place every media format behind one general-purpose playback library.
Caesar II has three materially different media problems:

| Media | Shipped form | Preferred implementation |
| --- | --- | --- |
| Effects and feedback | Simple PCM WAV files | SDL3 audio streams |
| Speech | Headerless PCM `.raw` files | SDL3 streaming |
| Movies | Smacker v2 indexed video, palettes, and audio | `libsmacker` |
| Music | Miles XMIDI with callbacks and numbered branches | XMIDI sequencer plus OPL3 synthesis |

The examined English installation has 84 WAV effects, 73 RAW speech files,
14 Smacker movies, and five XMIDI scores. These counts are evidence about the
current corpus, not assumptions in the implementation: asset lookup and media
parsing must continue to tolerate other official releases and translations.

The recovered engine remains responsible for media policy. Ambient selection,
music mood calculation, movie placement and skip behavior, volume settings,
loop counts, and voice priorities must not move into the SDL backend. The
portable layer implements the existing engine-facing functions and delegates
only device and decoding work.

## PCM effects and speech: use SDL3 directly

SDL_mixer is not needed for the first complete audio implementation. SDL3 can
load WAV data, convert and resample PCM through `SDL_AudioStream`, apply gain
per stream, and mix all streams bound to one playback device. Adding another
mixer object model would duplicate facilities that the port already depends
on through SDL3.

Relevant SDL documentation:

- [SDL3 audio overview](https://wiki.libsdl.org/SDL3/CategoryAudio)
- [SDL_LoadWAV](https://wiki.libsdl.org/SDL3/SDL_LoadWAV)
- [SDL_BindAudioStreams](https://wiki.libsdl.org/SDL3/SDL_BindAudioStreams)
- [SDL_SetAudioStreamGain](https://wiki.libsdl.org/SDL3/SDL_SetAudioStreamGain)

The portable implementation should preserve the recovered voice model instead
of exposing SDL streams to engine code:

- a bounded pool for ordinary effects;
- the dedicated positive/negative feedback voice;
- the dedicated streaming speech voice;
- recovered loop counts, status checks, stop/pause behavior, and configured
  sample volume; and
- `continue_db` as the regular engine-thread service point, even though SDL3
  does not require Miles-style double-buffer maintenance.

WAV files should enter through the asset service, not through backend-relative
filesystem paths. Speech should be queued with the format used by the recovered
path: unsigned 8-bit, mono PCM at 22,050 Hz. SDL3 owns conversion to the actual
device format.

## Smacker movies: use libsmacker

The first runtime implementation should use
[libsmacker](https://github.com/greg-kennedy/libsmacker). Its API matches this
game unusually well:

- it can open a movie from a memory buffer, preserving the asset boundary;
- it exposes each decoded 8-bit indexed frame and its palette directly;
- it exposes decoded audio chunks and their source format;
- it reports frame duration and advances one frame at a time; and
- it is a small cross-platform C library under LGPL 2.1.

Decoded indices should be copied into the existing `internal_screen` region and
the decoded palette should pass through the existing palette publication path.
All portable modes should use that indexed framebuffer; the historical
direct-VGA mode does not justify a second renderer. Smacker audio should feed a
normal SDL3 audio stream and share the device with the rest of the audio
backend. Preserve the recovered decision to stop ordinary samples when a movie
starts.

Retain `start_smacking`, `continue_smacking`, `stop_smacking`, and
`are_smacking` as the engine-facing surface. `continue_smacking` should decode
at most the next due frame and use the common shutdown-aware timing service; it
must not recreate the original `SmackWait` busy loop.

Preserve the recovered refresh ownership as well. Buffered modes 0 and 1 copy
the decoded frame into `internal_screen` and mark its dirty region, but
`continue_smacking` does not publish it. The surrounding recovered loop draws
the software cursor and calls `refresh_svga_screen` once for the completed
frame. Publishing once before and once after the cursor creates a visible
cursor-less intermediate frame. Mode 2 historically wrote directly to the VGA
screen, so its portable equivalent publishes immediately because it has no
surrounding buffered refresh.

FFmpeg is deliberately outside the project architecture: it is neither a
runtime dependency, a fallback, nor a comparison oracle. Compatibility work
must be driven from the official Caesar II movie corpus and libsmacker itself.
If libsmacker does not handle an official asset variant, fix the decoder or
the narrow adapter and add that asset shape to the libsmacker-facing tests.

libsmacker is bundled in `third_party/libsmacker/` (see
`third_party/README.md` for provenance); its `patches/` carry three narrow
fixes over upstream: an
absent Huffman tree no longer consumes a nonexistent terminator bit, failed
opens can release partially initialized decoder state, and public/internal
error results are explicitly signed for unsigned-`char` consumers. The first
fix is required by the shipped 640x480 `INTRO.SMK`; the other thirteen examined
movies happened not to exercise it. Commit `24531a7` fully decodes all 14
examined official movies under AddressSanitizer and UndefinedBehaviorSanitizer,
and malformed input now returns an error rather than asserting during cleanup.

## XMIDI music is a sequencer, not file playback

Music must not be handed to SDL_mixer or an ordinary linear MIDI
player. The recovered Miles interaction is game-visible:

1. playback reaches an XMIDI trigger;
2. Miles invokes `mood_modfication`;
3. the engine recalculates `tune_branch`; and
4. `AIL_branch_index` jumps playback to that numbered `RBRN` location.

At least `CITYPROV.XMI` and `BATEST2.XMI` in the examined assets contain
explicit `RBRN` tables. Flattening these files to ordinary MIDI would lose the
dynamic city and battle score even if the notes themselves played correctly.

The port therefore carries its own music library, `src/xmidi/` with the
public headers in `include/xmidi/`, reimplemented in C from the two binaries
that defined the original behaviour:

- **`xmidi.c` — the AIL 3.x XMIDI sequencer.** PS.EXE links Miles Sound
  System 3.x statically with full symbols, so `XMI_serve`,
  `XMI_send_channel_voice_message`, `XMI_read_log`/`XMI_write_log`,
  `XMI_refresh_channel`, `AIL_API_branch_index` and the sequence API were
  decompiled and transliterated. The library keeps the 120 Hz service tick
  (`MDI_SERVICE_RATE`), the 32-entry note-duration queue, the four-deep
  for-loop stack shared by all channels, numbered `RBRN` branches that set the
  event pointer and abandon open loops (`MDI_ALLOW_LOOP_BRANCHING` off),
  callback triggers, the controller log that a resumed sequence replays, the
  per-channel controller preset the driver constructor sends, and the volume
  model where sequence volume × controller 7 × master volume / 16129 reaches
  the driver, refreshed on every eighth service interval during fades. The
  default loop count is one, as in AIL: `FORUM3.XMI`, which has no loop
  controllers, plays once and then reports `SEQ_DONE`, exactly as under DOS.
- **`miles_opl.c` — the Miles OPL3 driver.** `HD/OPL3.MDI` is a 16 KiB
  real-mode driver compiled from C; it was disassembled with Ghidra and
  reimplemented function by function: 20 virtual voices over 18 physical
  channels, round-robin allocation, priority-based stealing with the voice
  protect controller, 4-op pairs through register 0x104, the velocity table,
  the 12×16 F-number table with its block/row tables, the channel-volume ×
  expression × velocity product applied to carrier levels, pan thresholds at
  28 and 99, bend range from controller 6 and the register image written at
  reset. `miles_opl_tables.c` holds those tables verbatim and
  `tests/c2_xmidi_test.c` compares every one of them byte-for-byte against the
  shipped driver image, and checks that the other Miles FM drivers on the disc
  (`ADLIB.MDI`, `SBPRO2.MDI`, `PAS.MDI`, ...) carry the same tables. Known
  driver quirks, such as the partner lookup in the stealing routine indexing
  by virtual voice, are reproduced and commented.
- **Nuked OPL3** (`third_party/nuked-opl3`, LGPL-2.1-or-later, one C file) is
  the chip emulator. It is the only third-party code in the music path.

Timbres come from the user's shipped `CAESAR.OPL` (or `CAESAR.AD`) Miles
Global Timbre Library, loaded whole; the DOS driver's 4 KiB timbre cache and
its LRU eviction are the only part not reproduced. Miles GTL voice records
store the modulator's five OPL registers first, then the feedback/connection
byte, then the carrier's five registers, and for 4-op timbres a second voice
after that; bit 7 of the first connection byte is the second pair's
connection. The asset test checks the known 2-op and 4-op instruments.

The sequencer reproduces one AIL bug on purpose, behind
`XMI_QUIRK_BRANCH_SKIPS_EVENT` (on by default): after a controller that moves
the playback position, `XMI_serve` advances past whatever event sits at the
new position. Branch targets in the shipped scores follow their own marker,
so nine of the 42 city branches lose their first note when reached from the
trigger callback, just as they did under DOS. Clearing the quirk plays them.

`c2-xmi-render` (built on demand) renders a score through the driver to a WAV
file for listening tests. Against the previous libADLMIDI-based path the
timing is identical (100 ms envelope correlation 0.89–0.92 at zero lag) and
the level is about 1.7× higher, because libADLMIDI's "AIL" volume model only
approximated the driver's total-level arithmetic.

The recovered digital-sample master volume and sequence volume are independent
Miles controls. The common adapter applies the former only to effects, speech,
PC-speaker feedback, and movie audio voices; it applies sequence fades and the
tune slider only to the two music voices. Neither setting is multiplied into
the other.

FluidSynth may later be offered as an optional General MIDI backend behind the
sequencer's MIDI callback. It should not be the default because it requires a
separate SoundFont and would not reproduce the shipped DOS OPL timbres.

Music generation runs from an engine-thread pump through the already frequent
`continue_db` boundary. Each of the two recovered sequence handles owns a
libADLMIDI player and a private SDL voice. The pump keeps at least 100 ms of
stereo 44.1-kHz PCM queued according to `SDL_GetAudioStreamQueued`; SDL
consumes it asynchronously while trigger
callbacks, `mood_modfication`, volume fades, and numbered branch jumps remain
on the engine thread. No audio callback or decoder worker mutates recovered
game state. If a worker is introduced later, it must stop at a trigger,
publish a notification, and wait for the engine's branch decision rather than
rendering past the decision point.

Debug builds expose read-only per-voice queue telemetry. The native and Wasm
music-buffer smokes enter a city, sample both music voices over time, require
at least 40 ms of scheduling margin, and verify continued synthesis. Native
SDL additionally records every device request that could not be satisfied and
fails on any missing bytes. The older wall-clock deadline estimate is retained
only for one-shot voice lifetime: rounding each generated chunk up to whole
milliseconds made that estimate drift from real consumption and previously
caused periodic music underruns.

One official `CITYPROV.XMI` is 28,678 bytes, larger than the recovered DOS
27,500-byte tune buffer. Portable builds enable the guarded
`PORT_FIX_LARGE_XMI_ASSETS` compatibility fix and use a 64-KiB buffer; disabling
the feature retains the legacy limit. This avoids truncating a valid official
asset without changing the reconstruction or mutating the asset.

## Intended dependency direction

```text
Recovered engine
  sound policy, music mood, movie placement and skip behavior
        |
Portable media adapters
  recovered voice model, XMIDI sequencing, Smacker frame scheduling
        |
Codec and synthesis components
  WAV/RAW PCM        XMIDI + OPL3        libsmacker
        |
Platform backend
  SDL3 audio device and existing indexed-frame publication
```

Decoder and synth implementations may have private handles, but those handles
must not escape into recovered headers or engine globals. The SDL backend owns
the physical device. Portable common code owns formats and legacy semantics.

## Implementation order and acceptance checks

1. **PCM foundation**
   - Open one SDL3 playback device and bind the recovered voice set.
   - Implement WAV effects, feedback sounds, RAW speech, volume, looping,
     status, pause, stop, and shutdown.
   - Add memory-output/unit tests for voice reuse and PCM duration.
   - **Implemented:** recovered sound policy is compiled from `pcsound.c`;
     WAV effects, feedback sounds, RAW speech, gain, looping, status,
     per-speech pause, stop, shutdown, and PC-speaker tones use the SDL3
     backend. Focused SDL tests cover decoding, lifetime, stop, and
     per-voice pause, and the recovered-flow test suite remains green.
2. **Movies**
   - Add the decoder interface and libsmacker adapter.
   - Implement full-screen and embedded movie placement, palette changes,
     audio, timing, input skip, and clean stop.
   - Exercise every available official movie through libsmacker and record
     open, dimensions, frame count, frame timing, palette, audio, completion,
     and malformed-input behavior.
   - Add semantic end-to-end tests for intro completion/skip and an embedded
     message movie.
   - **Implemented:** the common adapter loads movies through the asset
     service, schedules frames from libsmacker's microsecond duration, copies
     indexed pixels and palettes into the recovered framebuffer, and appends
     frame audio to a dedicated SDL3 voice. The recovered intro, VGA cinematic,
     message placement, and mouse-skip loops remain in control. VGA-era
     320x200 playback is mapped to the port's 640x480 4:3 framebuffer with
     nearest-neighbour integer coverage rather than introducing a second
     renderer. The decoder test walks every frame of all available known
     official movies and includes a malformed-input case; recovered-flow smoke
     tests exercise intro skipping and animated message cleanup.
3. **Music**
   - Create the project-owned libADLMIDI fork and add the external numbered
     branch API before integrating music into the port.
   - Prove trigger notification and external branch selection on both branching
     XMIDI files before choosing the final synth packaging.
   - Load timbres from the user's assets and render into an SDL3 stream.
   - Add deterministic sequencer tests for every `RBRN` entry and an end-to-end
     test that observes the recovered callback and branch selection.
   - **Implemented:** fork commit `7ca7092` provides the public jump and restores
     converted XMIDI branch locations. The port's Unity test verifies every
     numbered location in both official branching scores and rejects all
     absent IDs. The recovered city-flow smoke waits for a real trigger,
     `mood_modfication`, and branch selection before it passes. The Miles
     adapter loads the user's timbre bank, uses the AIL volume model and Nuked
     OPL emulator, and queues synthesis through the SDL3 audio boundary.
4. **Cross-target validation**
   - Verify native Linux first, then Windows and macOS.
   - Measure decoder/synth code size and audio scheduling under Emscripten.
   - Keep audio unavailable through the existing capability contract on a
     target until its device and sequencing behavior are actually functional.

The three native-Linux media slices now follow this dependency order. Remaining
media work is cross-target validation, especially browser scheduling and size,
plus broader audible/behavioral coverage of battle mood changes.
