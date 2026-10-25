# Pending-entry independent review: interrupted

The review stopped on root instruction after a concrete enrollment defect was
reproduced. This is an incomplete review and provides no acceptance. No producer
source, live source, root tracker, Git state, native/UI/phone, provider, credential
or deployment was changed.

The review verified the supplied 528 producer artifacts and the exact contract,
receipt and artifact-manifest hashes before copying the candidate into this
review lane. Two fresh TypeScript builds passed. The copied baseline entry suite
passed 45 of 45 actual workerd/SQLite groups. The independent suite executed 21
groups: 20 passed and one failed. Total executed runtime groups: 66; passed: 65.
No tests, new runtime probes or retries ran after the stop instruction.

The failing independent case is
`private-enrollment-row-identity-before-context-selection`, preserved at
`verification/hosted-worker-pending-entry-integration-review/candidate/test/review.mjs`
and in `independent-report.json`. On an unenrolled migrated row after restart,
call private `enrollExisting` with the correct operation key and object target
but a different, well-formed immutable SHA-256. It returns `conflict`, preserving
the durable row. A subsequent call with the exact correct identity also returns
`conflict`. The failing assertion expects the correct enrollment to succeed.

The cause is the order in `OperationState.enrollExisting` (candidate source line
62): it calls `initialize` before Engine enrollment checks that identity against
the existing row. Initialization permanently selects the wrong identity and
constructs its Engine. The later valid enrollment encounters the selected
context conflict. This is a P2 availability/correctness defect in the private
enrollment path. No authority grant or provider effect from the wrong identity
was observed. A dedicated minimal reproducer and recovery-after-restart control
were not completed before the review stopped.

The additional passing independent controls exercised delayed valid and invalid
restore with concurrent requests; mixed recovery/enrollment/fetch during restore;
32 near-timeout first admissions; aborted and expired-budget late ACK settlement;
a held effect with one Engine/launch; full-row preservation for public bursts on
unenrolled migration; malformed unenrolled shape rejection; hidden production RPC
methods; and production unavailable behavior. Restore delay and synthetic effects
exist only in excluded review fixtures. The production-source and compiled closure
audits remain unfinished; no complete surface or schedule-limit review is claimed.

All recorded review-owned resources were already cleaned by the harness and then
reconciled read-only: 66 temporary SQLite stores absent, 81 recorded PIDs absent,
and 15 exact-owned hard restarts recorded. No additional signals were needed.
Commands, manifest hashes, logs and EOF observations are retained in `attempts/`.
The first independent failure and its assertion remain unchanged.

See `verification/hosted-worker-pending-entry-integration-review/receipt.json`,
`cleanup-reconciliation.json`, `baseline45-report.json`, `independent-report.json`
and `input-bindings.json`. The receipt records unfinished work and tool-version
capture limitations. These are local workerd receipts with fixture effects;
deployment, schedule delivery, production dependencies, devices, signing, stores,
FieldLog and GA qualification remain outside this interrupted review.
