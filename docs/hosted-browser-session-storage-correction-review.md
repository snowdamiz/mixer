# Independent review of browser storage security corrections

This review targets the corrected SQL frozen at StorageSchema SHA-256
`676bb977bbe4c322caf63c1a5f40d86e7861847636029948b55cb01f6dedb6dd`, with producer
spec SHA-256 `dfffb543660d713a833b241f09d172e3576b0613051cd45e2657ceaa2bf706cc`.
It is separate from the [review that authored the repairs](hosted-browser-session-storage-review.md).
The producer removed one extra trailing blank line after the initial successful
review run; executable bytes and StorageSchema were unchanged. The final runner
rebinds the formatted spec and repeats the selected correction controls.
It makes no product edits. Root owns integration and final acceptance.

The scope correction changes activation's required-workspace-scope denial to
`('mixer.workspace.read'=ANY(i.scopes)) IS NOT TRUE`. SQL NULL array elements
can no longer turn that denial into an unknown condition. The existing 64-element
cap remains enforced. Bootstrap and begin re-read the database clock after their
unique INSERTs. Activation rechecks after credential/family insertion and again
after its unique cookie UPDATE, including the old-family expiry. All corrected
denials raise inside the same transaction, so earlier row, vault, family,
credential, attempt and audit mutations roll back together.

The six independently authored selected methods cover:

- Nil/empty arrays, NULL-only/NULL-containing arrays without the required scope,
  changed-case/trailing-space scope aliases, and 65 elements all deny. Complete
  JSONB snapshots of all nine browser/authz tables remain identical on denial.
- Required scope with NULL neighbors and at the exact 64-element boundary still
  activates an eligible human and creates the expected family/credential.
- Bootstrap's unique-cookie collision with a different internal ID waits for a
  concurrent transaction to abort, then rejects after exclusive expiry without
  leaving durable rows.
- Begin's colliding state INSERT rejects after expiry and restores a previously
  claimed attempt, the session revision, vault bytes and audit history exactly.
- Replacement activation's cookie UPDATE rejects after claim expiry and restores
  the previously active family/credential, with no new family or credential.
- The same cookie collision succeeds when released before expiry, providing a
  positive control for the late rejection.

Wait controls observe the exact worker backend in `Lock/transactionid` and
confirm `pg_blocking_pids` contains the owned locker before releasing it. They
cross the exclusive deadline within the unchanged 500 ms function lock budget;
the success control releases before its deadline. These are real PostgreSQL
unique-index waits and rollbacks, not simulated function return values.

Run `python3 verification/hosted-browser-session-storage-correction-review/run.py`.
The assertions do not import the producer spec. They reuse the existing selected
fixture's installation, synthetic constructors and bound-parameter composite
encoding helpers. The cluster/process harness is a disclosed adaptation of the
producer harness; no claim of an independent cryptographic or protocol oracle is
made. The runner freezes both product/spec hashes, records source and dependency
manifests before/after execution, command/version/output hashes and cleanup, and
requires all six methods to pass with zero failures, exclusions or skips.

The top-level `verification/hosted-browser-session-storage-correction-review/review.json`
binds the final result and report to its immutable attempt receipt. Actual local
execution is PostgreSQL 17, Elixir 1.20.4 and OTP 29. PostgreSQL 16 CI remains a
separate pending integration gate. This review does not replace the full original
SQL review, migration review or current verifier/provider/key-custody/runtime
topology/HTTP join. No broad hosted harness, production application, provider
request, browser/capture, native simulator/emulator or phone is started.
Every owned disposable PostgreSQL instance and scratch directory is removed,
including failed attempts. Other projects' processes and data are preserved.
Neon/deployment, customer/browser/native and GA acceptance remain pending.
