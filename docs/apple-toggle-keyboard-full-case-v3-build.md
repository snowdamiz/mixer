# Apple keyboard full-case V3 generic runner build

**Compiler succeeded; initial recorder failed on generated empty directories;
source restoration and product archival supplement verified.** This is one
generic iOS Simulator UI-test runner compilation. No application was rebuilt,
and no native test case or device/frontend query was run. All six application
keyboard cases remain unrun. Native, carrier and GA acceptance remain pending
or false; physical phones remain disconnected and deferred.

Root selected the exact source/host acceptance and generic compile proposal in
`verification/apple-toggle-keyboard-full-case-root-review/v3-source/`. The build
independently revalidated producer seal
`2d600f0289324591cfab82b3ff3d0d987dcdfce9e081a0ff2571d47d6c844039`, review seal
`5a3e441332174e477527943b0d23f3eb66db952c8a0b8d9d0bc688904ed20c9c`, their 80 and
117 files, all 2,537 input bindings, the exact five runner source files, and
tool hashes. The fresh canonical V3 build destination was absent. The revision
label `ccd8e4c3d96f96876a1339a51dc4297f4175d4fc` comes from root acceptance;
no Git command was executed.

`build_runner.py` recorded the exact compiler argv, cwd, complete intentionally
minimal environment, timeout, Python binary/version, tool/SDK/bundle hashes,
source trees and raw compiler stdout/stderr. One Xcode 26.6 (bundle build 24959)
`build-for-testing` command used the generic iOS Simulator destination, SDK 26.5,
arm64 and `CODE_SIGNING_ALLOWED=NO`. It returned exit 0 in 6.731551959 seconds
and printed `TEST BUILD SUCCEEDED`. No separate native tool version command was
run; installed metadata and build-dispatched probes are preserved. The source
project contains only the external-app UI-test runner target and no application
build dependency.

The original recorder then failed its full source-tree invariant because Xcode
created four empty mode-0777 directories beneath
`harness/MixerToggleUITests.xcodeproj/project.xcworkspace`: that directory and
its `xcshareddata`, `swiftpm`, and `configuration` descendants. Existing runner
entries, every producer/review/input file byte and mode, and all tools remained
unchanged. `recorder.stderr` preserves the failure and `command.json` preserves
the successful compiler result. The exclusive `attempt-started.json` marker
permanently spends the selected attempt. There was no compiler retry.

After root independently compared the observations, root explicitly selected a
separate narrow restoration/archive supplement. Its
`supplement/selection-and-identities.json` records the exact four directories,
device/inode/mode identities, original evidence hashes and cleanup authority.
`supplement/finalize.py` checked no-follow identities and emptiness, then removed
only those directories deepest-first with `rmdir` through each parent directory
descriptor. It used no recursion or unlink. Positive absence checks passed and
the complete source tree again matched the original precompile observation.
Original recorder evidence remained byte-for-byte unchanged.

The supplement binds 70 product entries, including 42 files totaling 20,762,081
bytes. The complete product tree digest is
`80ae16baf64547a477e981dc73f31cf8baec1c1d5e0aa8cbde3346ef2dcddde5`.
Its 6,231,713-byte archive digest is
`1064c8082add39b2dbaa5e0757c95673f8c54064a3e43adea49f3416fe3b2b1b`.
Every archived member, file payload/length/hash/mode, directory mode and link
target was verified without extraction. Source, tools and products were checked
again for stability. The original command and failed-recorder output hashes are
bound by `supplement/build-products-manifest.json`.

Twelve synthetic host controls passed before compilation. They cover exact
seal/input/tool revalidation with process creation forbidden, existing and
symlink destination refusal, spent-attempt refusal, changed-input refusal,
complete tree membership/modes, escaping symlinks, valid binary archives, and
archive byte/mode/duplicate/member mutation rejection. Their raw output and
source/tool/command receipt remain in this packet. These are host controls,
not native test evidence. Their disposable synthetic directories are absent.

The exact generated build directory and owned compiler temporary directory are
retained for review; their paths are in `supplement/cleanup.json`. No simulator
instance was created, so no instance cleanup was required. Other projects'
processes and data were not addressed. A generic compiler may read installed
platform services internally; this packet authorizes no instance/frontend
query and makes no claim to have audited Xcode's internal service traffic.

The product receipt awaits independent and root acceptance. No post-build
adapter was prepared or run. Root must separately select a reviewed post-build
preflight/adapter and native run. Read-only verification of this packet is:

```sh
python3 -B verification/apple-toggle-keyboard-full-case-v3-build/verify.py
```

No OTA, customer, store, dogfood, physical-phone, carrier, operational or GA gate
is accepted by this build.
