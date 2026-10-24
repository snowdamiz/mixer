# V9 setup-only iOS simulator diagnostic

The root-selected single V9 diagnostic completed on October 24, 2026. Official
XCTest passed the one selected method, `test000PublicSettingsFullKeyboardAccess`,
with xcodebuild exit 0. The V9 host received and durably retained 278 requests
through cursor 277, including both termination markers and the test-case, suite,
and bundle completion markers. `diagnosticCompleted`, `setupEvidenceComplete`,
and `setupObservationSatisfied` are true. Offline replay exactly matches the live
Settings summary. No bridge failure, persistence warning, retirement pending,
or persistence uncertainty was recorded.

This remains a setup diagnostic. All six application keyboard cases are unrun;
native keyboard qualification, strict native verdicts, carrier acceptance, and
GA remain false. The selected command returned exit 1 at the unchanged inherited
strict-qualification boundary after the setup test passed. The final runtime
verdict explicitly classifies that boundary and retains its traceback. This is
not a native qualification pass.

The selected command was:

```sh
python3 -B verification/apple-toggle-keyboard-focus-v9-preparation/run.py run --scope interaction --reviewed-seal a9f7f3843bd8cfbd2f751f70d2a0b02e503166129ab98637d3602bba2eb4c0f5
```

It began at `2026-10-24T22:24:35.525641+00:00` and ended after 66.500272 seconds,
including lifecycle, installation, XCTest, export, and cleanup. Official XCTest
reports one passed method lasting 22.739809 seconds. The environment was Python
3.14.8 / Clang 21.0.0 on macOS 27.0.1 arm64, Xcode 26.6 (bundle version 24959),
and an iPhone 17 Pro simulator on iOS 26.5 build 23F77. Physical phones remain
disconnected and deferred.

The selection SHA-256 is
`6c846e79181247d00d22dd30e39c80519dd05bc0b35899c2815cfa7838b11f9c`.
Immediately before the run, both the producer seal
`a9f7f3843bd8cfbd2f751f70d2a0b02e503166129ab98637d3602bba2eb4c0f5`
and independent review seal
`eb39d33f3a35dcdd0fb9c462cb49a6e1076688c203483377e9f8bb57565fcd50`
replayed successfully. The extra seven inherited source and three import-data
bindings outside the producer's 1,066 bindings were also rehashed; the independent
review binds 1,168 inputs. Both seals still replayed successfully after cleanup.

The exact V7 binaries were reused without rebuilding: app source closure
`f9ddf3e2615a80930d551351e1496f12ea476cac3e8d1bfd38d8cd101a1d2a46`, app archive
`b9a864d11182ac546d76110d7d4ea342821df98d1e32b3474e57cf07de04b393`, runner source
tree `e0fbb631305e7ec73c52c1d40a950e8b5392da78e53edc046c6459a2e646eaa7`, runner
product tree `004235a284df48a38a7d0a074237a44c603f4eb32bfc0bb063fb94b6e2385835`,
and runner archive `d576682db91277803aa1728c0a8b13e6e66a5a5e278b46ee24e7be8abc60333b`.
The reused V7 revision label is `c628863f7dc3dc3b694d2949be6176a311cce04c`;
the V9 producer/reviewer context label is
`67d6d0455c64ccb454c2e06e11edbdca2836a1cd`. File hashes bind the execution;
these labels do not imply a queried current Git state.

The unchanged public Settings route was Accessibility → Keyboards & Typing →
Full Keyboard Access. AX evidence bound all three route taps and the immediate
child switch at its recorded hit point. The switch changed from string `0` to
`1` after a tap, with accepted enabled observations at sequences 119 and 196
inside the anchored three-second window. Thirteen completed AX/PNG payloads
totaling 770,013 decoded bytes remain in `runtime/captures`. Visual inspection
of the retained before/after PNGs shows the switch off, then green/on with the
focus outline. The 29-second setup, 2-second request, 600-second session, and
all request/event/upload bounds were unchanged.

One supplementary export limitation is retained. The official xcresulttool
attachment export succeeded and left 12 files, including its manifest, UI
snapshots, synthesized-event data, and screen recording. A second inherited
export wrapper then rejected that existing fresh-only output directory, so the
original final `attachment-export.json` reports `passed: false` with
`Fresh fixed attachment output required`. A fresh read-only `__main__/verify`
import confirms two inherited `ExportingCommands` wrappers. The receipt was not
corrected and no native test was retried. Official summary/tests, the exported
attachments, and the durable AX/PNG journal are all retained. The raw xcresult
bundle itself was in the capability workspace removed by the unchanged cleanup
path; only the official exports remain.

The diagnostic used exactly one owned simulator,
`E8CC6986-8D1F-4F76-95CC-64A83D3E7151`. The loopback server shutdown/close,
thread join, capability workspace removal, and owned simulator reconciliation
all passed. Final recorded simctl inventory proves the owned simulator absent
and preserves all four baseline simulator identities and shutdown states.
The capability workspace is absent and pinned Simulator frontend identities
are unchanged. No physical devices or other projects' processes/data were
addressed.

Before the native attempt, the outer evidence recorder stopped after successful
seal replay because it requested the absent `ProductBuildVersion` plist key.
That failure is retained in `execution-preflight-attempt-1.json`; using the
actual `CFBundleVersion` metadata allowed fresh seal replays and the one selected
native attempt. A later offline wrapper-inspection recorder initially failed
because `inspect.getsourcefile` could not resolve an importlib class; its receipt
is retained, and the corrected inspection binds the method code filename. No
prepared source, application, runner, transport, or harness file was changed.

The additive runtime inspection, command receipts, original outputs, cleanup,
and documentation are hash-bound by `execution-seal.json`. Root acceptance is
pending. This lane did not edit Git state or shared trackers.
