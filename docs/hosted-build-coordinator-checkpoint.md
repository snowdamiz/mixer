# Hosted build coordinator checkpoint

The internal Oban coordinator now consumes durable build intents, commits a
start before dispatch, and reconciles a stable external operation across lease
transfers. Uncertain cancellation, timeout or callback failure retains capacity.
Definitive terminal evidence releases only the matching attempt. Guarded retries
use locked database time and the existing classification, backoff and attempt limits.

Root and independent review accept the current source closure
`c21aff5bfbfcbe113e39c7ac99747336f69b91f5b40bb7363ff2df54700c2026`:

- 261 host tests pass, including 19 producer coordinator tests, 14 independent
  controls and one actual asynchronous Oban processor check. These counts are
  included in the total. Two identity tests requiring isolated Linux networking
  remain skipped on this Mac.
- The processor check uses `testing: :disabled`, the PostgreSQL notifier and a
  real supervised queue. It consumes the creation job, commits its successor,
  invokes the modeled adapter and persists a snooze while retaining capacity.
- All 92 current and archived inputs and 21 command logs match. Formatting,
  compilation with warnings as errors and the production release pass. The
  coordinator is present in the release; modeled provider/review helpers are absent.
- Owned Oban, database rows, PostgreSQL and scratch cleanup are confirmed.

The first collection preserved two test assertion failures: an unnormalized Oban
worker name and a tombstone request carrying an expired lease. The next collection
passed the direct coordinator controls but the new asynchronous check stalled.
A focused diagnostic exposed mismatched Repo/notifier connection configuration
and a diagnostic logger error. The corrected fixture supplies one connection
configuration, waits for a bounded notifier round trip and guarantees cleanup
even when diagnostic reporting fails. The focused processor check and final
combined collection pass. Production coordinator behavior did not change during
these fixture corrections.

Evidence is retained under
`verification/hosted-build-coordinator/attempt-1` through `attempt-5-final`,
`verification/hosted-build-coordinator/root-review/acceptance.json` and
`verification/hosted-build-coordinator-independent-review/receipt.json`.
The producer source inventory is a historical pre-collection handoff.

The external provider remains modeled; no adapter is configured by default.
Public authorization/RLS, authenticated worker results, isolated customer-code
execution, aggregate/fleet quotas, artifact publication/signing, billing,
cloud operations and GA remain pending. See the
[coordinator contract](hosted-build-coordinator.md) for provider obligations.
