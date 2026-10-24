# Hosted audit codec development acceptance

`MixerHosted.Audit.UploadEvent` is integrated into the hosted service. Its pure
API validates the closed upload-event display, exact retained row bytes and one
immediate predecessor edge. It checks consistency only; identity verification,
membership authorization, database writes and release authority remain separate.

Root reviewed the original codec and independent findings, then accepted the
two-line key-work correction after fresh independent review. Fixed map
cardinality plus lookup of the distinct required keys avoids sorting unbounded
unknown terms. All typed field bounds, exact CBOR, domain hashes and PostgreSQL
display encoding remain unchanged. No dependency or artifact encoder changes.

The accepted source passes 12 focused tests and the complete hosted suite with
105 passed and two explicit Linux-only network-namespace skips. Format,
warnings-as-errors compilation and packaged release checks pass. Independent
correction review freshly runs 12 focused, six retained and two new tests,
including 546 foreign-key substitutions. Complete original/corrected outputs
match 80 producer vectors, 107 independent cases, 185 captured PostgreSQL rows
in six chains and eight independent edges. The finite timing observations are
recorded in the [review](hosted-audit-key-bound-review.md); they are not a universal
latency or total-memory guarantee.

Root copied exactly four additive reviewed files, verified all 60 prior hosted
files unchanged, and matched the complete 66-input tested snapshot. A direct
checkout format check and 12 focused tests pass. The full 105-test/release result
is reused from the byte-identical isolated source, not reported as a second
checkout run. Its owned PostgreSQL fixture and all review scratch were cleaned.
No native instance was started for this component.

The [acceptance receipt](../verification/hosted-audit-root-integration/acceptance.json)
binds source, test inputs, dependency manifests, commands, output and review
results. Its checker optionally verifies the current live files:

```sh
python3 -B verification/hosted-audit-root-integration/verify.py --live
```

This accepts a host development component, not complete production AS05 or any
GA gate. Selected domain schema/catalog migration, actual authoritative writer
and repository composition, authenticated HTTP, Neon/R2/Cloudflare, queue and
operational qualification, native/physical-phone acceptance and published
separate-repository FieldLog consumption remain pending.
