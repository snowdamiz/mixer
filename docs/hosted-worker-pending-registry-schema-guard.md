# Audit schema guard and terminal replay derivative

This narrow derivative addresses the independent review's
[`audit_missing_schema_meta` finding](hosted-worker-pending-registry-components-review.md).
The original producer receipt remains
`d25bc98f405bb25ea1c93ee583c92fe370f58dd777c8d28376830d8d2c648a18`;
the changes-required review receipt remains
`0d100e3d3c9310d34131efc8d64a0749f71d9cbb05daaac226e0f8ccf56f1bb9`.
Both original packets are preserved unchanged. The corrected candidate lives only
in [`verification/hosted-worker-pending-registry-schema-guard/candidate/`](../verification/hosted-worker-pending-registry-schema-guard/candidate/).
Root owns review, source selection and integration.

Before the audit constructor executes schema creation or inserts a fresh metadata
row, it now rejects an absent `pending_audit_meta` table when either
`pending_audit_summary` or `pending_audit_completion` exists. The query checks
bounded table existence, so empty surviving safety tables also fail closed.
An existing metadata table with no row is already rejected by its exact-one-row
check and has a focused regression control here. When all three audit tables are
absent, normal installation still creates the initial configuration, run sequence
`"0"`, sixteen cursors and sixteen empty completion slots.

The initial schema slice changes only `src/pending-audit.ts`: one bounded static
SQLite existence check before initialization. Its eight-case passing receipt is
preserved unchanged. Root then selected the terminal replay correction described
below, which also changes `src/pending-registry.ts`. All remaining production
source/type/SQL files, the sealed public interface, dependency pins, runtime bounds
and completion-retention behavior are byte-identical. No Engine/Ledger, live
source, tracker, deployment, credential, device, UI or Git edit is included.

The excluded focused fixture removes only specifically named tables/rows in its
owned local SQLite store, then performs identity-checked SIGKILL/restart. These
are explicit partial-schema fault injections; no claim is made that ordinary
SQLite crash recovery produces a missing table. Each rejected-state control
compares exact schema and surviving row bytes before/after two real restarts and
an unavailable audit call. A retained late `unavailable` ticket must remain
unchanged and unapplied; no replacement metadata/run token, new recovery call,
backoff mutation or synthetic authority is allowed.

The focused controls cover:

- Fresh installation, independent scheduled runs, stable registration and recovery
  after an actual restart.
- Missing metadata with both a retained completion and bounded summary history.
- Missing metadata with populated summary alone or retained completion alone.
- Missing metadata with only an empty summary table, only an empty completion
  table, or both existing tables empty.
- An existing metadata table with zero rows.

Reproduce from the repository root:

```sh
node verification/hosted-worker-pending-registry-schema-guard/run-check.mjs --terminal-only
```

The runner binds exact source/compiled hashes, the one-file source delta, tools,
commands, output streams, process-group EOF/absence and owned storage/PID cleanup.
It verifies the sealed original producer/review artifact bindings before and
after the focused run. The historical seventeen component groups and twenty
process-identity controls remain historical source-bound evidence; this narrow
change does not claim a new full-suite run. Real engine/schema-3/barrier/entry
integration, complete thirty-case acceptance and all deployed/native/GA gates
remain pending.


## Selected terminal replay correction

Root selected the additive
[terminal replay clarification](hosted-worker-pending-registry-terminal-replay-contract.md)
in receipt SHA-256
`141f32609d338647687d8f49c63d4add83d395c4cb833173204dcb80d37ffd38`.
A permanent terminal operation can accept newer guard/clock metadata while
retaining the same terminal result, so its newest atomic outbox must remain
trackable. The old component rejected every greater version after quiescence.

For `pending=0`, the corrected registry accepts a greater version only when the
incoming closed terminal projection is byte-identical to the stored canonical
terminal projection. This requires the same phase/evidence digest and null
next-due. It updates only the TEXT state-version watermark, retaining terminal
bytes, allocation/identity, quiescence and every delivery-history field. Equal
versions still require exact projection equality; older versions remain stale.
A pending projection, differing terminal phase/digest, non-null next-due,
malformed/extra field or overflowing version conflicts without mutation.

Four focused actual workerd/SQLite controls cover both terminal phases, versions
above 2^53 and at int64 maximum, retained failure-eight/attention/skip-seven/
attempt-eight history, stale tickets, exact replay after lost ACK and SIGKILL,
concurrent watermarks, and zero scheduled recovery starts for the quiescent row.
These are registry controls; the separate Engine lane owns real cross-DO terminal
command/outbox replay. No Engine workaround suppresses legitimate terminal
outbox production.

The default runner executes the schema and terminal controls. `--terminal-only`
executes the newly selected four controls while preserving the existing eight
schema controls as separate evidence. The audit guard source hash is checked
against that earlier passing receipt; it has not changed. The sealed original
producer/review packets remain unchanged. `corrections.diff` contains only the
two selected source deltas; neither is integrated into live sources.

The preserved schema run is `runs/20261025T044125775Z`, source digest
`aec32e0a366cf2b95a4a9585fe84dccb07225e53779e7faf1999fa06d55a576c`. The final terminal run is
`runs/20261025T044746060Z`, source digest
`ae105631d742e19999dc64dbfc0fc466cf6c9d5146ee4411dcc3988aaaab0b54`. The audit guard file is
`8120ebd4786005b263264c1162fa5a6ed0a7a0347d235aa5b6c4e984b076e38d`;
the corrected registry file is
`99d8a5dc4e2e9b8875c262ae44d2f1307d3107d3bc48c4300e981f68ec12b428`.
The two selected runs disposed twelve owned stores and observed eighteen exact
SIGKILL boundaries, all PID/storage and command EOF/group checks clean. Root
review and source selection remain pending; the original seventeen-group and
twenty-identity-control baseline was not rerun for these focused corrections.
