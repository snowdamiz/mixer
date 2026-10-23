# HTTP cleanup fixture CI repair

This is macOS unit-test evidence for a test-only repair. No product transport
source, public contract, generated identity, signing configuration, device, or
publication behavior changed.

## Observed failure and deterministic reproduction

Hosted run `39988758316`, job `120534733648`, revision `f19cf9f` failed the combined
cleanup predicate in `cancellationDeadlineAndQuotaReleaseTheirNativeTasks` under
Swift 6.2.4 / Xcode 26.3 TSan. The original log is retained byte for byte as
`hosted-f19cf9f-swift.log`, with its SHA256 in `investigation.json`. The assertion
did not identify which wait or predicate component failed. Its precise hosted
timing branch remains unattributed.

The original source passes the targeted local Debug test and the complete hosted
TSan filter under local Swift 6.4. An isolated test-clock probe then expires the
deadline on the fourth monotonic admission read: URLSession and its suspended
data task exist, but `task.resume()` has not run. The request reports
`deadlineExceeded`, the session invalidates, and the lease count becomes zero.
The protocol never starts, so its stop count is zero. The original assertion
still requires exactly one stop and fails deterministically:

```text
pre-resume-expiry: active=0, starts=0, stops=0
Expectation failed: predicate()
native transport did not acknowledge bounded cleanup
```

`pre-resume-expiry-probe.diff` and
`pre-resume-expiry-original-assertion.log` retain the exact probe and expected
failed test. This demonstrates a legal ordering rejected by the old test; it
does not establish that ordering as the exact cause of the hosted incident.

## Repair and preserved checks

The started-request test uses an injected, lock-protected monotonic clock. It
observes the deadline fixture start, verifies one active lease, and then advances
the clock by the request's ordinary 1000 ms budget. The watchdog observes expiry
without waiting for wall-clock time. URLSession retains its normal independent
native timeout. Cancellation, quota rejection, deadline failure, exactly one
protocol stop per started cancelled/expired request, zero native leases after
invalidation, and subsequent successful capacity reuse remain asserted.

The cleanup poll remains **400 iterations × 5 ms**. Failure messages now include
the phase, active leases, fixture starts, and fixture stops.

`deadlineBeforeNativeResumeReleasesLeaseWithoutProtocolStop` uses the same
pre-resume clock ordering as the failing probe and expects `deadlineExceeded`,
exactly one observed native session-invalidation callback, zero active leases,
zero protocol starts, and zero protocol stops. Observing invalidation ensures
that this regression cannot silently become an earlier preflight-only expiry.

## Reproduction and receipts

The runner copies only `sdk/` and `capabilities/`, excluding build outputs,
SwiftPM state, and prior verification artifacts, into a temporary frozen source
snapshot. It records the repository revision/tree, complete source manifests,
SHA256 digests, tool versions, exact commands, environments, timestamps, output
paths, and output hashes in `investigation.json`. Initialization restores the
original HTTP test from `f19cf9f` inside the snapshot so the original assertion
remains reproducible after the workspace repair has been committed.

The investigation stages, in order, are:

```sh
python3 verification/http-cleanup-ci-repair/investigate.py init
python3 verification/http-cleanup-ci-repair/investigate.py baseline
python3 verification/http-cleanup-ci-repair/investigate.py probe
python3 verification/http-cleanup-ci-repair/investigate.py repaired
python3 verification/http-cleanup-ci-repair/investigate.py final
python3 verification/http-cleanup-ci-repair/investigate.py seal
```

The runner refuses to replace an existing investigation. The initial repaired
source and its logs are retained separately from the final source, which adds
the explicit native-invalidation observation. Final logs are prefixed `final-`.
Only the test source is copied from the live tree for the repair stages; unrelated
working-tree edits never enter the frozen verification snapshot.

`receipt.json` summarizes the final source digest, verified source scope,
unchanged product transport, final command outcomes, observed test summaries,
and limitations. The full investigation retains both before/after source
manifests and the historical expected failure.

Final verification covers the separate pre-resume regression, complete
capability Debug and Release suites, the exact hosted four-suite TSan filter,
twenty repeated TSan runs of the two cleanup regressions, and the hosted TSan
filter using the locally available Xcode 26.6 / Swift 6.3.3 toolchain.

## Limits

Swift 6.2.4 / Xcode 26.3 is not installed locally; exact hosted compiler
revalidation remains pending CI. URLProtocol fixtures bypass real network I/O
and TLS. TSan instruments owned compiled code, while system framework internals
are opaque. No physical iOS/Android, production network, signing, immutable
package consumption, publication, or GA qualification is claimed.
