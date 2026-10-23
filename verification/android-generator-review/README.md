# Independent Android generator review

Scoped local generation/build review passed after the staging containment repair in
`b588481e21c521e264826a5c442901b8157fc112`. This is not physical-device, signing,
store, FieldLog D2, OTA release, or GA qualification.

The initial implementation was frozen from committed source
`b4f13ec9a78b882380a6cfba0a9607990ca9babe`; the repaired source was separately
frozen from `b588481`. Both copies still match every captured source hash after
execution. The reviewer wrote only this directory. `.local/` contains ignored
source copies, compiled test artifacts, isolated sentinels, and exact APK copies.

The review found and reproduced one P1 issue with four forms: a symlinked
`.mixer` or `android-build` directory deleted outside APK/receipt sentinels, while
a symlinked or hard-linked `build-input.json.tmp` overwrote an outside sentinel.
Each original direct-driver attempt eventually rejected its deliberately wrong
toolchain lock, after the outside mutation had happened. All sentinels were
review-owned. The committed repair rejects all four cases before mutation.
Additional deep directory links, FIFOs and non-directory staging paths reject
safely; normal internal SwiftPM cache links remain accepted. No scoped finding
remains unresolved.

| Evidence | Result |
| --- | --- |
| Frozen CLI tests | 19 passed on both initial and repaired source |
| Frozen engine package | 3 reusable-runtime and 5 existing-checklist tests passed |
| Independent runtime probes | 6 passed: value-state rollback, native buffer rollback, routing/generations, stale events, encoded/native output limits, handle budget and malformed input |
| Independent generated app | Fresh creation, byte-exact Java/JNI/schema export, 4 shared host tests and 1 original C ABI test passed; the C ABI test covers disabled Add, small-buffer add rollback, Unicode, 100 entries and entry-limit rejection |
| Independent fail-closed probes | SDK/adapter drift, capabilities, resources, direct malformed configuration/path names and escaping tool-directory links reject |
| Staging repair | Four original cases plus four other rejection shapes and one internal-link positive passed; 9 permanent regression functions passed under normal Python and `-O` |
| Actual repaired APK audit | 85 committed source manifest entries, 9 qualification-command log hashes, both cross-build receipt hashes, built-app/SDK/adapter locks and the exact repaired driver match |
| Independent official-tool APK inspection | 22 pinned-tool commands passed: 16KiB ZIP alignment, identity/ABI, 18 AArch64 ELF64 libraries, complete non-system `DT_NEEDED` closure, 3 owned DEX classes, app-owned feature/model and C ABI symbols |

The final unsigned APK is 27,257,525 bytes with SHA-256
`a170142c2d91f6475d20e6545f3ab509011b950bb41b16e5945cbd2fe92f8fe3`.
Its normalized 21-entry ZIP-content digest is
`179f7855b676c64d2e14c1e333199ef1f5640bbcd16f3f76fb36fe2b01ed90ac`.
The original APK and user-edited feature/manifest/entry build evidence were also
audited. The independent reviewer inspected actual APKs and the complete real
cross-build/cache-rebuild evidence; a duplicate full cross-build was not run.

`receipt.json` indexes commands, tool versions, source digests and findings.
`final-artifact-audit.json`, `staging-fix-replay.json`, and
`consumer-probe-results.json` provide the detailed scopes. Every retained evidence
file is hashed in `review-evidence.sha256`.

The first independent runtime harness attempt incorrectly decoded the guarded
`UIDocument` through an ordinary nested `JSONDecoder`. Its three failures are
retained in `runtime-probe-attempt-1.log` and the exact first harness source in
`attempts/RuntimeProbe.attempt1.swift`. Using the public `UIDocument.decode` guard
fixed the harness; all six probes passed in attempt 2. This was a harness error.

This review assumes trusted, synchronous, non-reentrant app callbacks with value
state and no external effects. `Sendable` alone does not provide transactional
isolation for reference graphs or effects. Before/after local source observation
is not a concurrent-write sandbox or build attestation. Native resource/capability
packaging, persistence/process restoration, navigation, device UI/IME/accessibility,
performance, production signing/installability, independent clean CI APK builds,
published immutable packages, external FieldLog D2, store acceptance and GA remain
pending. No device discovery, signing, installation, store action, production
publication, customer message, new dependency, or credential change was performed.
