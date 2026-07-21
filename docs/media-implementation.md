# Audio and movie implementation decision record

Status: proposed architecture, recorded 2026-07-21. The subsystem boundaries
and implementation order are decided. The Smacker decoder and music-synthesizer
choices remain subject to the compatibility and licensing checks below.

## Outcome

Do not place every media format behind one general-purpose playback library.
Caesar II has three materially different media problems:

| Media | Shipped form | Preferred implementation |
| --- | --- | --- |
| Effects and feedback | Simple PCM WAV files | SDL3 audio streams |
| Speech | Headerless PCM `.raw` files | SDL3 streaming |
| Movies | Smacker v2 indexed video, palettes, and audio | `libsmacker`, to be verified against FFmpeg |
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

## Smacker movies: prefer libsmacker, retain an FFmpeg escape hatch

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

FFmpeg remains the reference decoder and fallback, not the initial runtime
dependency. FFmpeg has a Smacker demuxer, `smackvid` and `smackaud` decoders,
and emits `AV_PIX_FMT_PAL8`, so it also fits the indexed renderer without
`libswscale`:

- [FFmpeg Smacker demuxer](https://ffmpeg.org/doxygen/trunk/libavformat_2smacker_8c.html)
- [FFmpeg Smacker codecs](https://ffmpeg.org/doxygen/trunk/libavcodec_2smacker_8c.html)
- [FFmpeg licensing guidance](https://ffmpeg.org/legal.html)

Before selecting libsmacker permanently, build a private corpus check that
decodes every available `.smk` with both implementations and compares:

- open success, dimensions, frame count, and frame duration;
- indexed pixel and palette hashes for every frame;
- audio-track format, decoded byte count, and PCM hashes; and
- completion, malformed-input behavior, and decode time.

If libsmacker fails on an official asset variant or materially disagrees with
FFmpeg, keep the same narrow decoder interface and replace its implementation
with a minimal FFmpeg build. Such a build needs `libavformat`, `libavcodec`, and
`libavutil`, the `smk` demuxer, and the `smackvid`/`smackaud` decoders. It does
not need encoders, networking, programs, filters, `libswscale`, or
`libswresample`; custom AVIO should read through the asset service. Native
dynamic linking is straightforward, but size and LGPL relinking obligations
make this less attractive for the WebAssembly target.

## XMIDI music is a sequencer, not file playback

Music must not be handed to SDL_mixer, FFmpeg, or an ordinary linear MIDI
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
branch state, AIL volume behavior, OPL3 emulation, and Emscripten. Its database
also identifies a Caesar II instrument bank. It is not an automatic dependency
choice, however:

- its public C API exposes trigger callbacks but not the external numbered
  branch jump required to replace `AIL_branch_index`;
- the complete synthesizer contains GPLv3 portions, despite individual
  sequencer, converter, and chip components carrying MIT or LGPL licenses; and
- the port should load the user's shipped `CAESAR.AD`/`CAESAR.OPL` data rather
  than embedding a derived copy of that asset.

There are two acceptable routes:

1. If the port's eventual licensing is compatible with GPLv3, use full
   libADLMIDI and add or upstream a small public branch-jump API.
2. Otherwise, use its sequencer and XMIDI behavior as a reference, combine
   appropriately licensed XMIDI sequencing with an LGPL OPL3 emulator such as
   Nuked OPL3, and implement loading of the shipped Caesar timbre bank.

FluidSynth may later be offered as an optional General MIDI backend. It should
not be the default because it requires a separate SoundFont and would not
reproduce the shipped DOS OPL timbres.

Music generation should run from an engine-thread pump, initially through the
already frequent `continue_db` boundary. Keeping a modest amount of PCM queued
lets SDL3 consume audio asynchronously while trigger callbacks and
`mood_modfication` remain on the engine thread. No audio callback or decoder
worker may mutate recovered game state. If a worker is introduced later, it
must stop at a trigger, publish a notification, and wait for the engine's
branch decision rather than rendering past the decision point.

## Intended dependency direction

```text
Recovered engine
  sound policy, music mood, movie placement and skip behavior
        |
Portable media adapters
  recovered voice model, XMIDI sequencing, Smacker frame scheduling
        |
Codec and synthesis components
  WAV/RAW PCM        XMIDI + OPL3        libsmacker or FFmpeg
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
2. **Movies**
   - Add the decoder interface and libsmacker adapter.
   - Implement full-screen and embedded movie placement, palette changes,
     audio, timing, input skip, and clean stop.
   - Run the libsmacker-versus-FFmpeg private corpus comparison.
   - Add semantic end-to-end tests for intro completion/skip and an embedded
     message movie.
3. **Music**
   - Resolve the port's dependency-license policy.
   - Prove trigger notification and external branch selection on both branching
     XMIDI files before choosing the final synth packaging.
   - Load timbres from the user's assets and render into an SDL3 stream.
   - Add deterministic sequencer tests for every `RBRN` entry and an end-to-end
     test that forces two moods and observes different branch selections.
4. **Cross-target validation**
   - Verify native Linux first, then Windows and macOS.
   - Measure decoder/synth code size and audio scheduling under Emscripten.
   - Keep audio unavailable through the existing capability contract on a
     target until its device and sequencing behavior are actually functional.

This order makes effects and speech available without constraining either
decoder choice, restores the visible movie paths next, and leaves the
branch-sensitive music work until its licensing and API requirements have been
explicitly resolved.
