# Independent Settings first-failure instrumentation review

No actionable findings were found in the frozen diagnostic-only derivative.
Recommend accepting this source review for root's next selection decision.
This review grants no native preparation, retry, Settings success, or GA credit.

Reviewed producer handoff SHA-256:
`d637e80716b9407028f059dd44673e09cd74f536d7bec2909fa02a0da5b40190`.
The accepted offline diagnosis remains
`162ffcc666e601263a70a6226289eab833e6335d84fa9a36b89c91426e248209`.
The original V5 failure's timed-out request identity remains unknown; the
observed deadline pressure is not a transport fix or a recovered identity.

## Frozen input and actual diff

Independent hashing checked all 26 sealed members and the bound acceptance.
The independent verifier read only the two named Swift members from the original
V5 archive's named nested archive and compared their exact bytes to the retained
original copies. It reconstructed the complete three-file unified patch.
The derivative source tree remains
`78fba50b813b34dd83c153df2b84be145d9a2f96aa05f6fa873ff89787bc1643`.

The transport helper is byte-identical. The only existing-file changes are a
private latch property and instrumentation inside `SettingsTelemetry.post()`.
The pre-`post()` prefix differs only by that property; every byte beginning at
`func start()` is unchanged. Consequently the 29-second deadline initialization
and shortening, serial upload order, setup predicates, and downstream native/UI
test predicates retain their original source. The request limit of 2,500,
8,192-byte request/response caps, two-second ceiling, relative semaphore wait,
existing guards, and original error values/latching remain intact. No new
bridge request, retry, dependency, package, or importer change was introduced.

## Diagnostic behavior reviewed

The record's exact allowlisted identity is retained; start is explicitly
distinguished, sequence zero is start-only, UUID/slot/integer forms are bounded,
and absent/unsupported identity fields become null. Chunk stage stays null.
Request ordinal and URLSession task identifier remain distinct. The recorded
allowance is the value returned by the original `begin()` call, using the same
captured begin uptime; clipping is reported against the existing two-second
ceiling. Semaphore expiration supplies no guessed status/Foundation error code.

The output dictionary contains only its 19 explicit keys. Finite times, bounded
identity strings/integers, fixed branches, numeric status/error codes, and nulls
are serialized beneath a 2,048-byte JSON ceiling. New diagnostic output never
copies URL, headers, capability, response/error descriptions, payload hashes,
detail/snapshot dictionaries, PNG/AX bytes, or encoded chunks. The producer's
sentinel redaction controls and the independent boundary controls agree.

The original timeout is latched before ancillary output. Callback fields are
read only after successful semaphore completion; the expiration path neither
reads those fields nor adds a second callback access. Public callers retain
their original recursive lock. The diagnostic selects its first record under
its own lock, releases that lock before calling the sink, and never consults a
bridge. A throwing sink is swallowed and cannot permit a second record; a
reentrant sink returns without deadlock or a second emission. Existing
configuration/body/admission failures retain their original nonsticky behavior.

## Focused independent execution

[Host receipt](../verification/apple-settings-failure-instrumentation-review/host-receipt.json)
records five focused groups, seven host process executions, and no failures:

- Completed callback and clipped semaphore timeout were each run against both
  exact original and derivative `SettingsTelemetry` prefixes. Outcomes, request
  counts, and first-error preservation matched. The derivative timeout recorded
  ordinal 10, request sequence 9, task identifier 1, exact chunk identity, and
  actual allowance `0.019985833438113332` seconds, with clipping true and
  status/error code null. These are synthetic host values.
- Sixteen metadata cases checked the exact output-key set, valid slot endpoints,
  chunk bounds, integer-type rejection, malformed slot/UUID/stage/kind redaction,
  the byte ceiling, and forbidden-field sentinels.
- A sink throwing before producing output was called exactly once across two
  failure attempts. A reentrant sink also ran exactly once.

Compilation used pinned Apple Swift 6.3.3, an explicit
`arm64-apple-macosx26.0` target, and the recorded macOS SDK. Both exact prefixes
through `post()` were compiled with the independent harness; the derivative
also compiled the new helper and unchanged transport. The full UIKit/XCTest
file was not compiled. Custom URLProtocol schemes were used without sockets
or listeners. This extends the reviewed producer evidence of 19 passing host
controls; the full producer matrix was not rerun or modified.

The producer retained all four attempts: the initial harness compiler failure,
Date and NaN Objective-C invalid-serializer exception/crash probes, and the
passing final suite. Those crash probes were not rerun. The new Swift catch
does not claim to catch Objective-C exceptions or process failures; the
original serializer limitation remains explicit and is not introduced by this
diagnostic-only derivative.

## Receipt and acceptance boundary

[Independent source verification](../verification/apple-settings-failure-instrumentation-review/source-verification.json)
and [input manifest](../verification/apple-settings-failure-instrumentation-review/inputs.json)
record exact input/output hashes, command, tool version, and source scope.
[Cleanup](../verification/apple-settings-failure-instrumentation-review/cleanup.json)
confirms owned executables/module cache were removed, scratch is absent, and
the producer packet is unchanged. The review can be verified without executing
host/native code using its `verify_inputs.py` script; rerunning host controls
changes review receipts and requires resealing this review.

No native runtime, device, simulator/emulator, UI, screenshot, or listener was
queried or started. No package was prepared. Excluded hosted catalog-inspector,
authority-driver, and rejected outbound-transport V2 lanes were not read,
imported, or executed. Only this report and the assigned review directory were
written; no producer/live/frozen packet, tracker, or Git state was edited.
Other projects' processes/data were untouched.

Native instrumentation behavior and full UIKit compilation remain unverified.
Settings remains failed, `test010ReferenceFirstTab` remains skipped, and the
incomplete run still fails its importer. Physical phones remain disconnected
and deferred. Keyboard/carrier/full-matrix, immutable external FieldLog dogfood,
signing, store, operational, accountable-reviewer, and GA gates remain pending.
