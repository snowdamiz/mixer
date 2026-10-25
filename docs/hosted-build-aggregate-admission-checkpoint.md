# Hosted build capacity checkpoint

Fresh build admission now requires explicit capacity at four levels: the whole
fleet, its iOS or Android pool, the organization across both platforms, and the
existing organization/platform pair. Every held reservation counts, including
workers whose state is uncertain. Shrinking or disabling a limit stops new work
while allowing existing workers to reconcile and release after definitive
termination.

The additive migration creates closed aggregate defaults and preserves existing
journals, reservations and leases. A fixed PostgreSQL transaction advisory mutex
serializes all admission and configuration fragments, including absent policy
rows and compositions spanning multiple organizations. Admission rejects isolation
modes other than READ COMMITTED because an older snapshot could miss reservations
committed while waiting for the mutex. Database time is sampled after locks.

Root verification observes:

- 255 repository tests pass, including all 71 build tests and 20 new aggregate
  controls. Two identity tests requiring isolated Linux networking remain skipped.
- A separate run passes all 11 independently authored PostgreSQL controls, with
  no skips. These observe advisory wait state and lock ordering, stale earlier
  snapshots, competing claims, transaction rollback, first configuration,
  cross-scope composition, held-worker reconciliation and migration preservation.
- All 91 live/archive inputs and 19 command outputs match the repository run.
  The independent run adds its one test file: 92 inputs and 23 command outputs.
  Production source is identical between the two runs. Formatting, compilation
  with warnings treated as errors, the release build and test-helper exclusion
  pass. Both owned PostgreSQL instances and scratch directories are removed.

The repository collection is
`verification/hosted-build-aggregate-admission-root-review/attempt-2/receipt.json`,
with source digest
`256d02916db75025b0d087c45ebff979a5108f588d1a3b5b8b7334cce2464bdc`.
The separate independent collection is `independent-attempt-1/receipt.json` in
the same directory, with source digest
`d670c9376af2d5f384b294e736fbd9a1f760daec89396deba433a87b020e8f52`.
Root binding reviews retain their exact source/archive/output checks.
The [independent review](hosted-build-aggregate-admission-independent-review.md)
found no blocking defect; `acceptance.json` in the root review directory records
development-slice acceptance. Its direct persistence tests retain an Oban notifier
configuration diagnostic and do not qualify notification delivery.

The initial full run passed 251 tests but invalidated four foundation integration
tests because their setup still expected the previous three migrations. Updating
that exact expected list to include the fourth migration fixed the setup; no
production behavior changed. That failed receipt and cleanup remain preserved.
Earlier producer diagnostics retain a fixture metadata assertion failure and an
unused-default compilation warning, both corrected before the final source freeze.

No production database migration has been applied. All admission writers must be
upgraded or stopped before aggregate limits can be relied upon: old binaries do
not enforce the new limits. The global mutex is a correctness tradeoff; throughput,
fairness and multiple-database fleet behavior remain unqualified. Provider execution,
public authorization, customer-code isolation, usage attribution, artifact signing,
cloud operation, FieldLog qualification and GA remain pending.

See the [aggregate admission contract](hosted-build-aggregate-admission.md) for
configuration, upgrade and composition requirements.
