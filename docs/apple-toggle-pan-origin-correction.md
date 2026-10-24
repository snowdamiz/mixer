# Private Apple toggle pan origin correction

This packet prepares a private admission correction and a fresh XCTest replay.
It changes only the copied diagnostic fixture under
`verification/apple-toggle-pan-origin-correction/app/source/` and its owned
verification harness. It has not dispatched native input, booted or installed an
app, used CUA, queried a phone, run Git, changed live SDK/product code, or changed
an earlier receipt. Native acceptance remains pending independent root review.

The preparation baseline context is `ef7510043e8ea9fc55dd7555dc91e9265b0215e3` as supplied
by root. The shared tree includes unrelated unfinished work; this is not a clean
committed-tree claim. Content hashes below define the exact private candidate.

## Evidence requiring the correction

The retained root review of the previous SDK26.5 XCTest run has 14 action
evaluations: 9 passed, four authored LTR/RTL pans failed, and comparator direct
API failed. Diagnostic direct API was incomplete after 11 observed checks. All
12 XCTest methods reported completion (6 passed, 6 failed) before xcodebuild
stalled until its 600-second timeout. These are separate outcomes. Root retained
owned simulator/server/thread/capability cleanup evidence. Per-request bridge
errors and the final summary were unavailable after interruption, so the precise
`invalidResponse` cause is unproven. An atomic-file replacement race is a
hypothesis, not a finding. The original historical19/12 strict failures remain
failures, and both direct suites remain pending for this new candidate.

Actual native movement was delivered in all four authored pans: initial touch
positions were x14 or x49, with at least9pt displacement before admission, while
`translation(in:)` at shouldBegin reported only +2 or -2. Enabled and allowed were
true. Standalone pan, blank-list scroll, carrier-origin vertical scroll and six
native tap actions passed their strict evidence predicates. The immutable
`TogglePanPolicy` still requires6pt and strictly more than1.2 horizontal dominance.

## Admission and lifecycle contract

The new pure `TogglePanAdmission` records public `UITouch.location(in:)` in the
actual carrier window from `shouldReceive touch`. Apple documents this callback
before recognizer `touchesBegan`, and public gesture location supplies the native
current point. See the retained [shouldReceive contract](https://developer.apple.com/documentation/uikit/uigesturerecognizerdelegate/gesturerecognizer(_:shouldreceive:)-16fuh)
and [gesture location contract](https://developer.apple.com/documentation/uikit/uigesturerecognizer/location(in:)).
The candidate does not call recognizer subclass touch APIs or set recognizer state.

At shouldBegin, current native window location minus that captured origin feeds
the existing6pt/1.2 policy. A touch attempt is fenced by touch/native carrier/window
identity, binding generation, frame, bounds, transform, window bounds and three
converted basis points. Missing/terminal/multiple/duplicate touches, nonfinite
coordinates/time, stale time, input gates, detachment and geometry changes fail
closed. Invalidated attempts cannot revive after geometry is restored. Binding,
direction, scroll-parent, native cancellation and terminal touch changes clear the
origin. Native view cancellation caused by a recognized pan retains the active
attempt until the actual recognizer terminates.

UIKit's UIView and delegate shouldBegin routing is not assumed to have a one-call
contract. An attempt keeps its initial policy result, while every repeated query
rechecks all identity/geometry/gate fences. A repeated query never becomes a new
touch capture. Trace records expose capture/reset/decision attempts, exact
origin/current/displacement, touch phase/time, native translation, identities,
and captured/current geometry for native review.

The same native `UIPanGestureRecognizer`, one-touch maximum, cancellation
configuration, and dynamic vertical-scroll failure arbitration remain. Preview,
release selection and value dispatch retain the original native pan translation
calculations exactly. Policy and SDK files are byte-identical to the frozen
diagnostic baseline. Only `AuthoredToggleCarrier.swift` and new
`TogglePanAdmission.swift` differ; `source-from-baseline.diff` is retained.

## Replay and durable evidence

The default closed replay selects exactly10 native interaction methods and13
required evaluations: standalone pan, blank scroll, four directional authored
pans, carrier vertical scroll, and authored/plain/comparator tap pairs. It retains
all existing strict predicates, including timed ordered native callbacks,
translation progression, intermediate preview without commit, one value event,
zero pan primary action, stationary list and actual native selected transitions.
`oracle.py` is byte-identical to the previous sealed oracle. The comparator
archive/source remain unchanged.

The two original direct XCTest methods remain in the compiled target and are
available only through the separate closed `--scope direct` selection. They use
`runtime-direct/`; default interactions use `runtime/`. Each scope permits one
fresh dispatch to an absent output directory. No direct suite is silently passed
because the first replay omits it. Exact original19/12 check names, order, counts,
results and explicit diagnostic completion remain required.

The bounded loopback bridge retains each error immediately with operation,
generation/case, error type/reason and the last valid observation or explicit
unavailability. File guards report type/link-count/size/inode metadata. They
retain the existing fail-closed policy without assuming a replacement race.
Bridge summaries are atomically replaced and fsynced after every request.
Capability/header/request-body logging is disabled; errors redact the capability.
The XCTest error now includes the returned bounded bridge rejection reason.

The runner writes an atomic final runtime verdict from `finally`, including
interruption and independently attempted cleanup outcomes. Missing bridge,
XCTest normal terminal result, observations, official summaries or cleanup are
explicitly unavailable and cannot yield success. Official redacted XCTest exports
are attempted on timeout too. Ordered action completion, XCTest method outcomes,
xcodebuild terminal status, direct-suite scope and cleanup remain separate.
The existing bounded single-instance ownership/recovery rules are retained.

## Compiler and host evidence

The exact app and runner compile with Xcode26.6(17F113), Swift6.3.3,
arm64 iPhoneSimulator26.5 SDK and minimum iOS26.0. This is compile evidence only.
All92 Python host controls and58 executable Swift policy/lifecycle/path checks
pass. Controls cover repeated admission queries, changed fences, both policy
boundaries/directions, multi-touch/stale/missing/cancelled inputs, fresh attempts,
interrupted summaries, strict failure retention, durable bridge errors,
capability redaction, closed replay scopes and original cleanup/archive guards.
Earlier failed host/compile/document-retrieval attempts are retained. They include
an ambiguous Swift test literal and a host fixture expecting the wrong rejection
exception; both were corrected without relaxing production guards.

- Corrected app source closure: `718434bf3efa26e51868eed26478693b6966e2ebd89f2b2e5847b2cbe8d8e1e5`.
- Corrected app archive: `7853b8a0b1adc39786ff13c1baa3961eb067882658ca7d595e80b9292ee6c601`.
- Prepared harness source tree: `caa5520ccb1961ffd0c438ff1464f3f699922caeec72959392702b4bb803e862`.
- Runner product tree: `f4cf09e8b5cc9289f56ea1dcfdb7cd5b7562edc6ca681e3696a62d760b076185`.
- Runner archive: `9bd2c3809c17690d1272b4d6f3dfee7edbd7deb00db3d504c5d57ff8098e7ada`.
- Comparator archive: `1c55dab124608b019ab4a1b6e0a9a2355e5f72287602b890a0a3f78aa6b30fa9`.

Build commands, full output, source hashes, tool/SDK hashes and versions are in
`app/build-attempt-4.json`, `app/source-lock.json`, `app/receipt.json`,
`preparation-commands.json`, `build-products-manifest.json`,
`policy-commands.json`, `policy-receipt.json`, and `host-checks.json`.
`evidence-bindings.json` pins129 historical input files. Six fresh official Apple
contracts, URLs, hashes and retrieval details are under `official/`.
Only standard Python, CoreGraphics and installed Apple tools are used.

Root first independently reviews this document, exact source diff, host controls,
receipts and `packet-seal.json`, then executes the read-only check:

```sh
python3 -B verification/apple-toggle-pan-origin-correction/harness.py verify
python3 -B -m unittest discover -s verification/apple-toggle-pan-origin-correction -p 'test_*.py' -v
```

If prepared Products are absent, `harness.py restore-products` validates and
restores only the sealed runner into that absent canonical destination. Root's
first native dispatch, after exact seal selection, is:

```sh
python3 -B verification/apple-toggle-pan-origin-correction/harness.py run --reviewed-seal REVIEWED_SEAL_SHA256 --scope interaction
```

The optional separate direct replay adds `--scope direct`. Recovery uses
`harness.py cleanup` with the matching scope. This preparation has run none of
these native commands. Do not rebuild/edit a sealed producer; a changed candidate
requires separate review and identity.

Native replay/full cancellation-disable-stale/no-change/focus-keyboard matrix,
compositor parity, physical phones/VoiceOver final acceptance, product adapter
integration, immutable external FieldLog consumption, store/operational/reviewer
and GA gates remain pending. No physical-phone reconnection is requested.
