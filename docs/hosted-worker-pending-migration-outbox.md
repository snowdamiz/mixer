# Exact null outbox requirement for migration enrollment

The isolated derivative adds exactly `r.track_outbox_json===null` to Engine's
shared `unenrolledMigrationShape` helper. Every other production byte is retained
from the frozen migration-history candidate. This closes root's selected P2:
quarantined stopped/completed rows with null identity and registration but a
reintroduced valid non-null terminal outbox now return `conflict` from explicit
enrollment, preserve the entire operation row and issue no provider effect.

The frozen producer receipt remains
`5bce543f307a07666aa5bc70b4f9e5da6f59ac82edc5956c26d859a8f64d288e`, with source
digest `361c391b035a7a4cdbfaa9d6013cb4944431eb97ad14c65731caac292f947483`.
The frozen independent review receipt remains
`43992550d3fff245b10e0d019c484f904f24f6de1b4de6bb2645635e0cc3aa06`.
All 349 artifact bindings in those two receipts, both receipts and seals, root's
exact selected decision, and five external fixture/tool bindings are verified
before execution, after execution and at seal: 359 files in total. Historical
failed attempts and their assertions remain intact in their original packets.
The derivative records those historical attempts explicitly.

The producer and independent review run in separate owned copies. All frozen
drivers and both original runtime fixtures are byte-identical; no assertion or
loader path changes were needed. Across each closure's 13 production files, only
the single shared-helper conjunction differs. Ledger, schema, wire, clock,
provider, registry and public contracts retain their original bytes. The
[exact patch](../verification/hosted-worker-pending-migration-outbox/migration-outbox.patch)
and production/driver identity manifests bind those comparisons.

Actual workerd/SQLite verification passes **769/769 controls**:

* All **688/688** producer controls pass: prior 81, review 40, terminal 279,
  independent 78, and migration/history 210. Their existing valid committed
  nonterminal stop cleanup, ACK full-row fencing and MAX no-reset controls remain
  unchanged.
* All **69/69** independent review controls pass with its driver byte-identical.
  The four formerly failing stopped/completed direct/restart extra-outbox cases
  now pass. The previous four actual schema-1/2 terminal enrollment regressions
  and two retained-ACK regressions also pass. Valid already-registered enrollment,
  actual legacy migration enrollment, and lower-ACK pending delivery remain valid.
* A separate **12/12** regression closure covers genuine schema-2 stopped/completed
  migration with missing/null, empty-string and malformed outbox bytes, directly
  and after owned hard restart. Null retains the explicit maintenance path;
  empty/malformed bytes reject, preserve the complete restored row, retain a
  durable independent inconsistency fence and leave registry/provider history
  unchanged. Every case restarts again after enrollment admission/rejection and
  verifies durable row/fence bytes, quarantine, and denied claim/report authority.
  The only extra fixture action writes those three finite outbox values; the
  original frozen fixtures and drivers remain unchanged.

The reproducible complete run is:

```sh
python3 verification/hosted-worker-pending-migration-outbox/run.py
```

The [sealed receipt](../verification/hosted-worker-pending-migration-outbox/receipt.json)
binds the source snapshots and digests, all three compiled closures, exact patch,
commands, installed tool/executable versions and hashes, exit codes/signals,
stdout/stderr EOF, complete test reports and cleanup. Hard restarts recheck the
exact executable and direct-parent ownership before signaling only the owned
workerd. Every recorded owned workerd PID is absent and each owned SQLite
storage environment is removed at seal. Other projects' processes and data are
preserved. Root-provided HEAD `be472ce6424a691de5673e3438d2768264827d23` is
context only; Git is neither consulted nor changed.

This packet awaits root's fresh independent narrow acceptance review and any
separately selected live integration. It is finite local workerd/SQLite evidence
with an excluded synthetic clock/provider. Recognizing a migration-consistent
shape is not proof of historical origin and grants no execution authority.
Live/root production source, Git, native/phone/provider/deployment/credential and
customer/publication state are unchanged. The frozen catalog inspector, authority
driver and rejected outbound transport V2 lane are not read, imported or executed.
Public/scheduled wiring, live controller 71/process 20 suites, deployed
alarms/restores/fleet/capacity, production clock/provider qualification,
immutable-package FieldLog, signing/store, final physical phones and accountable
GA acceptance remain pending. Physical phones remain disconnected. No remote
rollback, cancellation or distributed atomicity is claimed.
