# Catalog wildcard association correction

The raw catalog validator currently requires `(oid == 0) == (name == "*")` for
startup role and database associations. PostgreSQL also permits a quoted role or
database literally named `*`, with a positive OID. The independent review has
reproduced the role case using ordinary local DDL. Its raw rejection is a domain
error; the selected catalog comparator still rejects the additional reachable
role/default. No selected-baseline bypass or availability regression was shown.

Preserve both frozen packets. In a separate candidate, require the `*` sentinel
when the OID is zero. For positive OIDs, retain the existing non-null resolved
text validation and allow a literal `*` name. Do not introduce a new identifier
length rule for these fields. Preserve all other raw validation, stable
normalization, selected expected catalog and SQL bytes.

The final review also identifies ACSR02: different internal trigger rows can
share the same raw `(relation_oid, name)` and disappear into the selected
normalized model. PostgreSQL's retained `pg_trigger.h` declares that pair unique.
Reject duplicate pairs before discarding internal trigger names. Preserve valid
same-name triggers on different relations and different names on one relation;
do not require generated internal names to remain stable across databases.
This is an impossible raw-model admission, with no actual database bypass shown.

Replay original and independent raw-shape models, add role and database cases for
both zero-OID sentinels and positive-OID literal names, and reproduce legal
quoted-name observations in a fresh private PostgreSQL fixture. Confirm selected
comparison still rejects additional reachable roles/defaults and ordinary catalog
drift, with the baseline accepted. Reuse unchanged original schema-suite evidence
explicitly; do not claim a rerun. Bind commands, source, output and cleanup under
`verification/hosted-catalog-wildcard-correction/` and document the result in
`docs/hosted-catalog-wildcard-correction.md`.
Add the frozen ACSR02 reproduction as a required rejection and portable name
controls. Check the ordinary PostgreSQL duplicate-name rejection in that same
owned cluster; no separate broad runtime replay is needed for this constraint.

This isolated correction creates no live database migration or startup authority.
Independent correction review and root acceptance remain pending. No provider,
native, physical-device or GA gate is accepted here.
