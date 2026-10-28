# Independent shared-input integration acceptance

Accepted for root selection of one manual harness diagnostic. No concrete source
integration blocker was found in the sealed candidate. This is source/file/mock
acceptance; compiler availability, compilation and the complete fixture are pending.

The reviewed candidate is `verification/cache-fixture-shared-input-candidate/`:

- Shipping seal SHA-256: `db6ba0fcb4c66f5a38dd0f93ce9dc381a869b12fbf8eda7ecb8f5b3f57bfeca7`.
- Shipping tree: `96a51f27039c6c091eae9fd0e447bc9ca2d71f453eebc6c8ca6e58474640c698`, 21 members, 231,418 bytes.
- Runner SHA-256: `40357071ea8da19e051c8e470a7faa78dfa42bfbc3c756d3d30a790671be7d6d`.
- Workflow SHA-256: `50f55de2d34606f93a0687413d8a542e47d843c8481a2bc958f13e2407c26bbf`.
- Accepted Rust source SHA-256: `f7d62c01e251642677e22f7595af9683f9c451f1db43683be5d2ef86fedba141`.
- Existing independent source-review tree: `407647c81271e3dd4d49308a224a7d0cc1165e31a793dfadb1a51924aa605d84`.

The existing Rust acceptance was used as an immutable prerequisite. This review
did not reopen the 1,003 vectors, fresh arenas or assertions. It verified that the
thin overlay binds that exact accepted source and original preimage, borrowing 83
unchanged frozen members into the closed 86-member effective pack. The manifest
is the fourth overlay file outside that member list. Both recorded amendment
diffs exactly reconstruct the candidate from their pinned base Python files.
The predecessor `fixture_setup_amendment` and all other base binding fields remain
unchanged. Product/library source, API/File/layout controls, method inventories and
partitions remain bound by the immutable base and effective manifest.

`python3 -B verification/cache-fixture-overlay-independent/review.py` passed 28
runner source/file/mock controls, nine materializer groups and six additional
integration controls. The latter verify source mutation after materialization,
failure on missing compiler with zero child commands, spawn-failure accounting,
counter regression/missing-snapshot rejection, informational progress handling,
and exact toolchain environment selection. The missing-compiler test executes
the real Python `execute` path with inert signal mocks; it observes failed status,
exact overlay/pack postflight, retained input and owned scratch cleanup. It does
not test an actual compiler, timer or subprocess.

The audited run attempted zero forbidden operations. The independently bound
117-file read-set is unchanged, including the candidate's original 114-file
read-set. Python version, host, command, exact hashes and results are in
`review.json`; full unittest output is in `controls.stdout`. All synthetic files
were created under this sibling and removed. Candidate materialization remains
absent. The retained `first-run-*` files show an incorrect dictionary-shaped
expectation in this review harness for a list-shaped compiler target; correcting
that review assertion yielded the passing run. It was not a candidate failure.

The workflow is manual-only, refuses attempts after the first, runs all 36 focused
runner controls before its single complete fixture invocation, and preserves
failure evidence with unconditional artifact upload. Its exact toolchain
`1.98.1-aarch64-apple-darwin` is permitted by the frozen base. It sets
`RUSTUP_AUTO_INSTALL=0`; no installation or fallback is present. An unavailable
compiler or wrong identity fails without claiming a fixture pass. Whether the
remote runner has this compiler is unverified.

The full 103-child Debug/optimized closure, 60-second child limit, 600-second active
limit, 60-second cleanup allowance, 8 MiB stream caps, source postflight, owned
process-group custody and retention-before-delete rules remain intact. All 32
base control methods remain; four accounting mocks make 36. Eight real-child or
signal controls remain pending here and are required by the workflow.

CPU snapshots and deltas are explicitly sequential reaped-child aggregates, with
no process isolation claim. A missing spawn, failed reap or custody hold withholds
the delta. Progress parsing is informational extraction and does not establish
monotonicity or completeness. It records the elapsed remainder and excluded work;
`completed=1003` precedes final shared validation/removal. Only complete successful
commands, exact fixture coverage and successful postflight/cleanup can qualify
this diagnostic.

No compiler, Rust/product runtime, Git command, process inventory, child,
socket, real signal/timer/wait operation, held-group probe, native runtime, UI,
capture, push or dispatch occurred. No canonical/global/frozen file was edited.
No old FieldLog artifact was fetched. Historical timeout failure and all native,
allocation, replay, capability, custody, release/customer/GA holds remain active.
Current green CI is not evidence of a regression or speedup; neither is claimed.
