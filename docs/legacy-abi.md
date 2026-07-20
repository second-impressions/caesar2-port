# Legacy ABI and data-layout contract

## Scope

Removing DOS APIs is not sufficient to make the recovered engine portable.
The source also reflects Watcom's data model, packing, character semantics,
pointer width, and optimizer assumptions. Wasm32 happens to preserve a
32-bit pointer width and can therefore conceal defects that appear immediately
on x86-64 or ARM64 macOS.

This document defines the initial portable compilation contract and the
source changes required to leave that contract safely.

## Scalar model

The recovered engine assumes:

- 8-bit bytes;
- 16-bit `short`;
- 32-bit `int` and `long` in serialized and mapped records;
- 32-bit historical pointers;
- little-endian file and memory data; and
- unsigned plain `char` in code reconstructed from the DOS build.

Portable build configuration must assert the scalar widths it relies on.
Serialized formats should progressively move to `stdint.h` types and explicit
encoding, but that conversion must not silently change existing save or asset
layouts.

## Structure packing

Watcom 10.0a used one-byte structure packing for these sources. Every gap
represented in `entities.h` is an actual recovered byte, not implicit compiler
padding. Modern targets must express this explicitly and maintain static
assertions for all engine records that are:

- serialized;
- loaded directly from assets;
- indexed with a historical byte stride; or
- shared with translated assembly routines.

Prefer a scoped project packing macro or `#pragma pack(push, 1)` around legacy
record definitions rather than a global compiler option that can affect
system headers. Portable-only host structures use the native ABI.

Packing alone does not make pointer-bearing records historical-layout
compatible on a 64-bit host. Those records require the treatment below.

## Pointer-bearing records

Several UI and descriptor records contain native pointers or callbacks:

- `selection_rec`;
- `slider_rec`;
- `icon_rec`;
- `menu_item_rec` and `menu_rec`;
- `button_rec`;
- `save_entry`; and
- function-pointer tables such as the action and intelligence tables.

Typed access to these records may use native pointer widths in the portable
target. Code that treats the records as historical byte blobs may not.

Known source sites requiring correction include:

- callback dispatch through byte offsets into `rome2_buttons`;
- callback dispatch through a byte offset into `city_actions`; and
- truncating `landfill` to `int` before calling `place_2x2_block`.

These must become typed pointer-safe expressions. Building native Linux with
`-m32` is not a solution because it excludes modern macOS and merely hides the
defect. Wasm32 must not be used as evidence that a pointer conversion is safe.

`save_entry` itself is a runtime descriptor and may contain native pointers;
the buffers and sizes it names define the serialized data. Tests must confirm
that the descriptor object is never written to disk as a raw record.

## Character signedness

The DOS corpus was compiled with unsigned plain `char`. Modern Clang, GCC, and
MSVC targets do not all share that default. Until every behaviorally relevant
plain-char use has an explicit type, portable targets must select unsigned
plain `char` (`-funsigned-char` on Clang/GCC, the corresponding MSVC option)
and assert representative conversions in tests.

This is separate from fields explicitly reconstructed as `signed char`, which
must remain signed.

## Aliasing, alignment, and arithmetic

The engine deliberately overlays map cells and scratch buffers with typed
views. The initial portable optimization contract should include
`-fno-strict-aliasing` for Clang/GCC while these accesses are audited.

Packed and scratch-buffer accesses may be unaligned. Portable C replacements
for assembly must not create undefined unaligned typed dereferences on targets
that require alignment; use byte operations or `memcpy` where necessary.

The historical compiler emitted wrapping two's-complement arithmetic for
signed overflow. Use `-fwrapv` initially, then replace important overflow
dependencies with explicit unsigned or fixed-width operations as they are
identified. Do not enable aggressive overflow assumptions merely because a
test scene still renders.

## Function and calling-convention syntax

`__far`, `__pascal`, Watcom `#pragma aux`, and imported Windows decoration are
historical ABI mechanics. Platform selection must use `PLATFORM_DOS`,
`PLATFORM_WINDOWS`, or `PLATFORM_PORTABLE`, never compiler identity.

Compiler-specific pragmas may remain in a DOS-only declaration or header when
they describe the authentic ABI. The portable API should use ordinary C
calling conventions and should not expose far-pointer status values. Where a
legacy caller observes only success/failure, the compatibility implementation
translates a normal portable result to the legacy representation.

## Save and asset compatibility

Raw state-block save/load currently relies on exact record sizes. Before a
portable build writes user saves, it must have:

- compile-time size/offset assertions for every registered block;
- fixture tests reading original saves;
- round-trip tests that compare all serialized bytes intentionally preserved;
- explicit treatment of any pointer or process-local handle; and
- versioning for later portable-only extensions.

Asset readers must similarly distinguish byte offsets from native structure
indices. The numerous city, region, and battle map cursors are historical byte
offsets by design and are not host pointers.

## Recommended build checks

Every portable CI configuration should fail early unless:

- scalar widths match the supported model;
- required legacy structure offsets match assertions;
- plain `char` is unsigned;
- no pointer-to-`int` conversion is accepted without an explicit reviewed
  compatibility helper; and
- translated raster routines pass framebuffer tests on both a 64-bit native
  target and Wasm32.

Native sanitizer builds should include AddressSanitizer, UndefinedBehavior
Sanitizer, and ThreadSanitizer in separate configurations. A clean Wasm build
does not replace those checks.
