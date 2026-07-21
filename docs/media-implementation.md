# Audio and movie implementation decision record

Status: accepted architecture, recorded 2026-07-21. SDL3 effects and speech,
libsmacker movies, and branch-aware libADLMIDI music are implemented on the
native SDL3 target.

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

FFmpeg is deliberately outside the project architecture: it is neither a
runtime dependency, a fallback, nor a comparison oracle. Compatibility work
must be driven from the official Caesar II movie corpus and libsmacker itself.
If libsmacker does not handle an official asset variant, fix the decoder or
the narrow adapter and add that asset shape to the libsmacker-facing tests.

The port consumes the Second Impressions libsmacker fork as an SSH git
submodule. The fork currently carries three narrow portability fixes: an
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

[libADLMIDI](https://github.com/Wohlstand/libADLMIDI) is the strongest
implementation reference. It supports AIL XMIDI, trigger callbacks, internal
branch machinery, AIL volume behavior, OPL3 emulation, and Emscripten. Its
database also identifies a Caesar II instrument bank. It is not an automatic
dependency choice, however:

- its public C API exposes trigger callbacks but not the external numbered
  branch jump required to replace `AIL_branch_index`;
- the complete synthesizer contains GPLv3 portions, despite individual
  sequencer, converter, and chip components carrying MIT or LGPL licenses; and
- the port should load the user's shipped `CAESAR.AD`/`CAESAR.OPL` data rather
  than embedding a derived copy of that asset.

The selected route is the public
[Second Impressions libADLMIDI fork](https://github.com/second-impressions/libADLMIDI),
whose git remote is `git@github.com:second-impressions/libADLMIDI.git`. The
fork commit `7ca7092` closes both gaps in the upstream implementation: the SMF
marker parser turns the converter's `:XBRN:hh` markers into song-wide branch
locations, and `adl_jumpToBranch` exposes the existing sequencer jump with a
bounded branch ID and an explicit success result. A synthetic XMIDI regression
proves branch discovery, missing and out-of-range failures, and the resulting
playback-position jump. Direct validation against the examined Caesar II
assets finds all 54 branches in `BATEST2.XMI` and all 42 branches in
`CITYPROV.XMI`; the three linear `FORUM` scores correctly expose no branches.

The port pins that fork as an SSH git submodule. It initializes the Caesar II
embedded bank only to retain libADLMIDI's generated note-lifetime metadata,
then overlays every instrument from the user's shipped `CAESAR.OPL` or
`CAESAR.AD` Miles bank. The asset's OPL register values, note offsets, bank
selection, and percussion mapping therefore remain authoritative. The fork
and port must retain their respective license notices; the port's eventual
distribution terms must be compatible with libADLMIDI's GPLv3-covered complete
synthesizer.

Miles GTL voice records store the modulator's five OPL registers first, then
the feedback/connection byte, then the carrier's five registers. libADLMIDI's
public `ADL_Instrument` representation exposes the carrier first. The adapter
performs that ordering conversion explicitly and its asset test checks known
2-op and 4-op instruments against the embedded Caesar reference metadata.
Copying the two blocks in file order reverses the synthesis roles, producing
quiet, metallic-sounding instruments despite otherwise valid playback.

The recovered digital-sample master volume and sequence volume are independent
Miles controls. The common adapter applies the former only to effects, speech,
PC-speaker feedback, and movie audio voices; it applies sequence fades and the
tune slider only to the two music voices. Neither setting is multiplied into
the other.

FluidSynth may later be offered as an optional General MIDI backend. It should
not be the default because it requires a separate SoundFont and would not
reproduce the shipped DOS OPL timbres.

Music generation runs from an engine-thread pump through the already frequent
`continue_db` boundary. Each of the two recovered sequence handles owns a
libADLMIDI player and a private SDL voice. The pump keeps approximately 100 ms
of stereo 44.1-kHz PCM queued; SDL consumes it asynchronously while trigger
callbacks, `mood_modfication`, volume fades, and numbered branch jumps remain
on the engine thread. No audio callback or decoder worker mutates recovered
game state. If a worker is introduced later, it must stop at a trigger,
publish a notification, and wait for the engine's branch decision rather than
rendering past the decision point.

One official `CITYPROV.XMI` is 28,678 bytes, larger than the recovered DOS
27,500-byte tune buffer. Portable builds enable the guarded
`C2_FIX_LARGE_XMI_ASSETS` compatibility fix and use a 64-KiB buffer; disabling
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
