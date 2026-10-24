# V5 Settings diagnostic: independent source and host review

**Disposition: one actionable host/replay finding; V5 native execution remains
unselected.** The reviewed packet is
`verification/apple-toggle-keyboard-focus-v5-preparation/packet-seal.json`,
SHA-256 `8626e01f8622b0a27176cb37331edd7076d50b566f61b5c52bc5d4b1703770aa`.
All 84 bound files match before and after review. The root source selection is
`d9849baa4dadc9285e5b95f1ec35ff560d9926aec6d66e2d9f9e01e98b1cd8ca`.
The machine-readable disposition is in the review lane's `review.json`; the
immutable evidence inventory is `review-seal.json`.

The independent emitter uses the sealed real `Bridge.request`, Settings
`Session`, durable saves and offline replay. It does not import the producer's
fixtures or adapted test classes. Its AX text, PNGs, UI snapshots, tap markers and
clock are explicitly synthetic host data. No XCTest, simulator/emulator, physical
device, UI/capture, Git operation, download or public tracker edit occurred.
Historical revision context `9a9c0e000234b07a92c4484979d3587f7f24df48` is copied from
the sealed binary receipt; no current Git revision is asserted.

**Finding V5-IR-01 (P2): a destination observed before the route tap is credited
as post-navigation evidence.** In `settings_telemetry.py:216–218`, captures are
ordered against the preceding capture, but a route tap does not advance that
capture boundary. Lines 236–239 credit the next destination without checking its
capture against the recorded tap's `finishedUptime`. Lines 283–287 validate the
tap's own timing but omit its completion time from `route_bindings`.

The raw witness under
`verification/apple-toggle-keyboard-focus-v5-independent-review/witnesses/pre-tap-destination/`
contains 32 durable records and all 12 referenced AX/PNG files. It alters only the
capture and nested snapshot timestamps of the three route-opened observations.
Destination metadata is a separate correct NavigationBar; each raw old selector
remains present, offscreen and unhittable. For the first route:

| Record | Sequence | Reported runner uptime |
| --- | ---: | ---: |
| Search capture finished | 2 | 10.022 |
| Destination observed | 5 | 10.0222 |
| Route-opened capture finished | 5 | 10.0223 |
| Tap started | 4 | 10.042 |
| Tap finished | 4 | 10.043 |

The route-opened **record** is delivered after the tap marker, with monotonic
record and host receipt times. Its nested evidence nevertheless predates the
tap. All three `destinationMatched` fields become true while every
`oldSelectorAbsent` remains false. `selectedRouteEvidenceExpected` and
`setupObservationSatisfied` both become true. The actual offline replay accepts
the same journal and returns the exact same summary. This is credited stale
evidence, not merely retention of raw stale data.

The Swift source at `ToggleUITests.swift:168–171` samples the target, performs the
tap, sends its marker, then captures the destination. The finding is therefore a
host validation/replay hole demonstrated by adversarial synthetic timestamps;
it is not evidence that the native producer sampled an old page during a run.
Retain the selected route tap's completion time and require
`tap.finishedUptime <= routeOpened.captureStartedUptime <= destination.observedUptime`
before crediting the destination. Keep the existing capture ordering, same-route
binding, bounds, app bytes, switch anchor and qualification boundary. The ordinary
assertion `test_CONTRACT_destination_captured_before_tap_return_cannot_complete`
is retained as a failing targeted control; a correction should reject this
journal or leave setup unsatisfied while preserving the valid ordered flow.

`attempt-1.json` retains command arguments, Python/Swift versions, source hashes,
raw outputs and the failure. The 26 independent host methods ran: 25 passed and
one failed exactly as above. Positive controls exercise the real Bridge and
replay. Negative controls cover anonymous-container-only evidence, wrong or
outside child metadata, self/descendant mismatch, tap frame/type/identity and
sequence/time mismatch, zero-frame raw searches versus actions/switches, old
selectors versus destinations, nested capture times, the unchanged three-second
anchor, wrong/late switch samples, host receipt regression/duration, replay file
and identity mutations, symlinks, pending uploads, HTTP geometry rejection and
transactional persistence. The real HTTP geometry rejection retains status 400
and its reason without advancing the accepted cursor.

The exact runner's shared `DiagnosticTransport.swift` compiled with the pinned
macOS SDK as a Foundation host executable. All 35 independent checks passed,
including absolute/request budgets, HTTP versus network causes, first-error
retention through secondary failures and UTF-8 reason bounds. This is host
Foundation evidence, not an iOS runtime receipt. The sealed V5 preflight passed;
it binds the producer's earlier control/crossbuild receipts. Those producer test
suites were not rerun in their immutable directories. The frozen failed V4
runtime replay and analysis check also pass unchanged; that confirms replay
agreement with a failed diagnostic rather than setup success.

Only this review lane and this document were written. The owned host scratch was
removed, along with 52 compiler-cache files totaling 31,188,887 bytes inside the
review lane. No native instance was created, queried or cleaned up. The sealed
source and historical evidence remain unchanged. No keyboard/carrier/GA
qualification is accepted; all six application cases remain unrun and physical
phones remain disconnected and deferred. Root should select any repair as a new
packet before selecting native execution.
