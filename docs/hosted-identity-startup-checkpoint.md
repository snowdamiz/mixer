# Configured identity startup checkpoint

Root accepted and integrated the corrected twelve-file startup overlay, with
69-source closure `bfa2dcc1467f524a68fec298bdd098625f450b68ab2bd68b99f2a73d435772c3`.
API startup now validates an explicit disabled/configured identity setting and
starts the configured key owner before the HTTP endpoint. Disabled mode retains
liveness only; processor mode rejects configured identity. A configured owner
starts cold, with no speculative fetch. Configuration inspection is redacted.

The inherited endpoint grammar previously accepted a trailing newline. The two
strict whole-input anchors fix that defect while preserving existing host/path
limits. Original failure evidence remains intact. Independent correction review
passes 31 focused cases, including the original adversarial reproductions,
ASCII controls, Unicode separators and exact length boundaries. The original
ten startup files are unchanged by this correction.

Corrected producer evidence passes 93 macOS tests with two explicit Linux-only
skips and 95 Linux tests with no skips. Actual application startup, cold DNS/TLS
authentication, owner restart, stale lease fencing and connection cleanup are
covered by the retained fixture runs. Root separately runs the integrated host
suite: 93 passes, two Linux-only skips, production release construction, expected
missing-configuration rejection and exclusion of four test-only exports. Its
owned PostgreSQL instance is stopped and scratch removed. Dependencies are
unchanged. The host collector records 62 inputs; the complete source closure
also includes seven unchanged protocol fixture files unused by that collector.

See [root acceptance](../verification/hosted-identity-startup-root-review/acceptance.json),
[correction](hosted-identity-startup-correction.md) and
[independent review](hosted-identity-startup-correction-review.md).
The executable root verifier checks the preserved evidence and source archive;
`--live-source` additionally checks the current checkout against the accepted
closure. The one-time integration script must not be replayed on an integrated tree.

This accepts the configured startup development slice. Authenticated HTTP
admission, authoritative database identity/membership decisions, artifact
transactions, real provider and selected-cloud operation remain pending.
No native or physical test was run for this host slice, and no GA gate is closed.
