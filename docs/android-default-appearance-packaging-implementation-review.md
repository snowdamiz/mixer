# Independent Android appearance packaging implementation review

Status: preaccess assertions frozen; awaiting the root's exact frozen
implementation handoff. This document and packet use accepted Git revision
`99d6384306ea17643b70c472f93b57418c674f86`, the prior frozen public-contract review,
and root's [selected contract](../verification/android-default-appearance-packaging-implementation-review/implementation-selection.json).
No mutable implementation product file or producer packet has been read.
No product or compiler has run in this review.

The selected root contract SHA-256 is
`30171f00f98ed7e27c8f9654f0c997a7c9672e282697a7a4c8fa7bfca1d98582`.
The [accepted source manifest](../verification/android-default-appearance-packaging-implementation-review/accepted-source-manifest.json)
and [baseline receipt](../verification/android-default-appearance-packaging-implementation-review/baseline-receipt.json)
bind this review's input selection. Accepted sources are read with `git show`
against that explicit revision, never from the changing product working tree.
The original 15-file proposal-review packet and preaccess baseline stay untouched.

## Independent invariant matrix

The machine-readable [vectors](../verification/android-default-appearance-packaging-implementation-review/vectors.json)
define inputs and expected behavior before implementation access. They describe
black-box contracts, rather than mirroring a future helper's internal functions
or assuming its error strings. Implementation-specific test entry points will
be selected only after the frozen source arrives. The assertions remain fixed;
any justified change requires an explicit review amendment.

| Area | Independent assertion |
| --- | --- |
| Producer provenance | The CLI's linked existing `mixerDefaultV2()` and `canonicalData(_:)` produce the descriptor once. The exact result enters the adapter before its digest. No copied theme table, Java default, fixture input, SDK source scraping, copied-SDK emitter, new supervisor or new watchdog. The copied SDK stays separately source-locked. |
| Model semantics at generation | The real closed codec, with the existing default, establishes shared mode, empty resources and system sans. The descriptor id/format/recipe are those of the API output. Retained 9,587-byte/hash evidence is a comparison reference, never the product input or a replacement for fresh API derivation. |
| Complete source inventory | The only asset file is `app/assets/MixerAppearanceV2/descriptor.json`; the only asset directories are the required path. Reject hidden names, names skipped by source hashing, extra empty directories, dangling/ordinary symlinks and special files. Inspect owned path components before following a redirect. |
| Admission order | Closed asset layout, directory/file type and 1–65,536-byte size checks occur before general hashing opens the asset, before output creation/cleanup and before tool execution. FIFO/oversized/redirect cases must terminate with refusal and preserve sentinels. |
| Source locks | A valid asset preserves existing SDK/adapter drift rejection. Edit/remove/rename must not become allowed by packaging. Keep authored Java mutation regressions as well as the new asset regressions. |
| Recomputed lock limitation | A locally recomputed lock is unauthenticated. Python path/type/size checks cannot claim canonical/default/font/resource semantics. Layout-valid noncanonical bytes are not a semantic success; a layout/size rejection with a recomputed lock proves only that narrow rejection. |
| Final ZIP | Inspect the aligned final APK, reject duplicate ZIP names, and require its complete asset inventory to be exactly one fixed descriptor entry whose length and bytes match the admitted locked input. Missing/additional/renamed/wrong-byte entries fail. Do not hide duplicate names by first building a dictionary. |
| Resource and staging regression | Keep both app resource refusals. The existing staging test's minimum valid-asset fixture may change; every containment assertion and outside-file sentinel must remain. Output symlink/hardlink/FIFO protections stay in force. |
| Product scope | Public V1 Activity, Java/JNI/Swift runtime implementation, ProjectGenerator, ProcessRunner, schemas, theme/branding and dependencies except explicit first-party MixerUI stay within the selected scope. No copied-SDK compatibility or public V2/native/release authority claim follows. |

The directory inventory assertion applies to the internal asset closure; it is
not a claim that a path check isolates this build from concurrent same-user
writers. Source and artifact rechecks remain local before/after observations.
Special-file vectors will create only owned FIFO/socket fixtures, never system
devices or sockets that accept network traffic. No hardlink rejection policy is
invented for source inputs where the selected contract requires ordinary regular
files; existing output hardlink refusal remains a separate preserved contract.

## Planned independent execution after frozen handoff

First verify the root's source manifest and seal, snapshot only the required CLI,
SDK and updates build closure into owned review scratch, and compare its paths
and bytes with accepted Git plus the selected six-file implementation scope.
Do not run or import a producer collector. Check unchanged V1/native/runtime,
ProjectGenerator and ProcessRunner identities from the frozen source selection.
No broad hosted collector, frozen inspector, authority driver or WorkerV2 path
is an input to this review.

Use two complementary layers with bounded scope:

1. **Independent adversarial host checks.** Replay the new focused Python asset
   tests and existing staging containment tests against the exact frozen driver,
   then exercise independent omitted vectors from the matrix. Use a fixture
   driver subprocess with a short deadline, private owned process group and a
   fake tool sentinel; invalid input must fail before a tool sentinel or output
   changes. Pure preflight/ZIP functions may be called in a fresh host child
   after source review when that is the narrowest meaningful assertion. Record
   which vectors actually ran; do not turn a reviewed assertion into a pass.
2. **Fresh generated consumer.** Build the exact frozen CLI in a fresh owned
   scratch path with two jobs, create a uniquely named Android project from its
   selected SDK/adapter and run its actual generated complete unsigned build.
   Independently inspect its locked adapter and aligned ZIP and compare bytes
   with fresh API-derived canonical data and both production pure codecs. Retain
   Swift/JNI/Java/D8/AAPT2/zipalign command/artifact bindings. A synthetic APK,
   precompiled repository adapter or copied producer APK is not this check.

Root selected independent Debug/Release CLI and Python tests plus the actual
complete unsigned consumer build. Coordinate the exact-source replay with root
to avoid repeating completed equivalent broad suites: a source-identical
Debug/Release receipt can be reviewed, while independently executing the
adversarial cases and fresh consumer above. If root selects exact-source host
replay instead of another cross-build after seeing the producer's frozen
evidence, record that narrower executed scope explicitly and leave the
unexecuted fresh-cross-build assertion pending. Never relabel it independent
completion. Do not start compiler children before the frozen handoff.

For canonical provenance, derive through a small review-owned host probe linked
to the exact frozen SDK's real MixerUI API. It is verification-only; it does not
become a CLI emitter or imply equivalence of arbitrary `--sdk-path` SDKs. A
separate create-only case can use a copied source distribution with the required
default API deliberately absent to establish that the selected CLI-owned data
path does not secretly add a copied-SDK compilation gate. That fixture is never
used for the qualified complete consumer cross-build.

Every executed command needs argv, cwd, tool version/path/hash, selected source
digest, full stdout/stderr, exit status and bounded deadline. Keep owned command
groups and scratch separate from other projects. On timeout/failure retire only
owned children and retain diagnostics before scratch cleanup; record successful
cleanup. No global process discovery or cleanup is permitted. Any process-group
checks are limited to a child this collector itself just created; they are not
system inventory.

## Pending qualification

All execution remains pending until the frozen handoff. Computer use, native
runtime, simulator/emulator, capture and UI automation remain paused; phones
remain disconnected. Do not run `doctor`, `adb`, simulator tools or process
inventory. No UI, native installed capture/lifecycle, API28–35 runtime coverage,
TalkBack, resource/font/custom-theme support, physical matrix, external immutable
FieldLog consumption, SDK/default/ABI compatibility, signed authority, release or
GA gate is promoted by a passing host or unsigned packaging check.
