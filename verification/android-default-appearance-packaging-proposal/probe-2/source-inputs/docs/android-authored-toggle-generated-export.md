# Android authored-toggle source export

New Android projects now include the accepted `AuthoredToggleInputV2.java`
source required by `NativeAppearanceViewsV2.java`. The generated adapter contains
fourteen Java files, and the new file participates in the existing adapter digest
and `mixer.lock`. Only the generator allowlist and its snapshot/lock tests change.

The [producer receipt](../verification/android-authored-toggle-generated-export/final-receipt.json)
binds the two changed files, 127 source inputs, exact commands, tool identities,
raw output, exported project, class output, DEX and cleanup. Independent review
is pending at this producer freeze.

## Observed verification

- Two focused Swift test functions pass in both Debug and Release. Each run
  includes six parameterized lock cases: edit, remove and rename for both the
  coordinator and authored-toggle sources. CLI verification and the copied
  build driver reject drift before creating `.mixer` output.
- An actual freshly compiled CLI creates `ExportProbe` with `--platform android`.
  All fourteen exported Java files exactly match production source bytes.
- Strict `javac --release 17 -Xlint:all -Werror -implicit:none` compilation against
  the official SDK37 `android.jar`, with an empty source path, produces 160 class
  files. All four authored-toggle class hashes match the retained accepted native
  candidate. Omitting only the authored source reproduces a missing-type compiler
  failure; that expected negative control is retained.
- Official D8 with `--min-api 28` produces a 255,044-byte DEX, SHA-256
  `420aa6339c3f62bada4e5d45174cf424fdb9019017301b2cb05c4baffc717308`.
  `dexdump` confirms the four authored-toggle class descriptors.
- The actual generated consumer separately rejects all three new-source mutations
  through both CLI and direct-driver admission, for six observed rejections.
- A separate read-only audit verifies source and command bindings, exact test
  counts, archive members, compiled classes and recorded scratch cleanup.

The host CLI/tests use Apple Swift 6.4, arm64 macOS. Java is OpenJDK 25.0.4.1;
D8 is 9.2.4-dev from build-tools 37.0.0. The generated Android toolchain lock
records the installed official Swift 6.3.3 Android distribution separately.
No Swift/JNI/APK cross-build is claimed by this Java/D8 check. All owned command
children returned, and the isolated scratch was removed after artifact retention.

## Remaining product boundaries

The Activity, Java implementations, JNI/Swift contracts and native appearance
behavior are unchanged. The ordinary Activity still routes through V1. D8's
minimum API28 setting does not establish private V2 runtime support below API36.
Descriptor/resource packaging, shared-theme defaults, public lifecycle integration,
environment coverage and public renderer qualification remain the dependencies
described in the [routing proposal](android-public-appearance-routing-proposal.md).

Native simulator/emulator runtime, physical phones, capture and UI automation
remain paused. Fresh public interaction/accessibility/parity checks, the final
physical-phone matrix, immutable external FieldLog consumption, release and GA
acceptance remain pending. This source-export repair grants no release authority.
