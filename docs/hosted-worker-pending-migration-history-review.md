# Independent migration-history review

The frozen candidate is **not accepted for live integration**. Fresh actual
workerd/SQLite tests pass **65 of 69 controls**. Four failures expose one remaining
selected-contract gap: explicit enrollment accepts a quarantined, unenrolled row
with a non-null outbox. Genuine schema-1/2 migration enrollment and the previous
six finding regressions pass the independently authored controls.

The reviewed producer receipt is
`verification/hosted-worker-pending-migration-history/receipt.json`, SHA-256
`5bce543f307a07666aa5bc70b4f9e5da6f59ac82edc5956c26d859a8f64d288e`;
source digest
`361c391b035a7a4cdbfaa9d6013cb4944431eb97ad14c65731caac292f947483`;
Engine patch SHA-256
`d290f0d410224fcdcb8128b431c4c3252353f0849d03e2ae0a9561d7ed7fa520`.
All 213 producer artifact bindings, 335 frozen prior bindings, and 23 candidate
source entries match before execution and at seal. All 13 production source
files in the review are exact copies. The review independently authors its
control driver and finite extra restore/migration fixture actions. No producer
file or production module is edited.

## P2: require null outbox for unenrolled explicit migration enrollment

At [candidate Engine line 42](../verification/hosted-worker-pending-migration-history/candidate/src/engine.ts),
`unenrolledMigrationShape` checks quarantine, identity/registration, ACK, both
barriers and positive state, but omits `track_outbox_json === null`. The missing
outbox branch in `terminalProjection` supplies that condition for its own use.
The explicit maintenance path calls the same helper at Engine line 543 without
that surrounding branch. A valid non-null outbox passes terminal consistency,
so this second use accepts a row outside the selected exact unenrolled migration
shape.

Four fresh controls create genuine stopped/completed terminals, run the actual
schema-2 SQLite migration and restore one valid terminal outbox at the retained
state version. Every remaining field has the exact migration-consistent shape:
quarantine one, canonical positive version, ACK zero, null identity/registration,
null effect/claim barriers, closed valid terminal, matching row phase and null
next-due. Two controls invoke enrollment directly. Two hard restart first and
confirm constructor recovery preserves the restored row byte-for-byte before
invoking enrollment. All four return `enrolled` instead of `conflict`, save
identity and registration and advance stopped version `3` to `4` or completed
version `9` to `10`. The final report retains the complete before/after rows.

Quarantine remains one, the terminal bytes are unchanged and provider call
history is unchanged. No execution authority, remote rollback or customer effect
is demonstrated. This is nevertheless a real explicit-maintenance contract
violation: recognizing a migration-consistent shape is intentionally narrower
than accepting arbitrary quarantined unenrolled state. Reject the non-null
outbox shape before registry enrollment and local mutation, while preserving
valid existing-registration enrollment. Do not classify this as a proven new
regression against the prior candidate; this review does not run a predecessor
baseline for this case.

See final report controls
`{stopped,completed}-unenrolled-extra-outbox-{direct,restart}-must-reject` and
observations `{stopped,completed}-extra-outbox-{direct,restart}`.

## Passing evidence

The 65 passing fresh controls include:

* Genuine stopped/completed rows and actual schema-1/schema-2 SQLite migration,
  constructor recovery, explicit recovery, owned hard restarts and successful
  explicit enrollment. Every legacy operation column is retained, quarantine
  stays set, the outbox receives the next version and authority remains denied.
* The four prior schema-1/2 enrollment regressions and both prior retained-ACK
  regressions. The latter first commit a real terminal/ACK, lower only local
  state, retain the higher remote terminal, reject flush, preserve the entire
  local row and persist the independent history fence across hard restart.
* Partial registration, empty/malformed registration objects, barriers, positive
  ACK in an unenrolled row, signed/fractional state and whitespace ACK values.
  Explicit enrollment rejects and retains the observed row. SQLite independently
  rejects quarantine two under its CHECK constraint before Engine admission.
* Enrollment pauses inside its registry await while failures, clock floor,
  permanent terminal bytes, provider, independent fence or row existence change.
  Final enrollment rejects without overwriting the restored row. Restarts retain
  those rows and any permanent fences. These are finite adversarial controls,
  rather than an exhaustive all-column Cartesian product.
* Central ACK-ahead rejection at flush, constructor/recovery, plain command,
  valid-shaped claim/report and explicit enrollment boundaries. Full-row equality,
  unchanged provider history and durable independent fences are asserted. Ordinary
  and MAX-adjacent histories cover terminal and nonterminal rows; exact ACK equality
  at ordinary/MAX versions remains valid with a null outbox.
* Valid already-registered idle/stopped/completed explicit enrollment succeeds,
  increments exactly once and clears its exact versioned outbox without changing
  registration or issuing another provider call. Migrated MAX rows cannot acquire
  partial registration, wrap/reset the version or mutate the row. Valid lower-ACK
  pending terminal delivery still succeeds.
* History restores while the final pre-track hook waits and while an already
  committed remote terminal ACK waits. Both reject, preserve every restored row
  column and leave the observed remote record unchanged. Already committed remote
  history is not claimed to be rolled back.
* Positive nonterminal committed-stop cleanup continues under an independent
  fence plus registry/clock outages; an owned stop call occurs while terminal,
  claim and report authority remain withheld.

The producer's 688 controls were not rerun for count. Inspection of
`assertion-amendments.patch` (SHA-256
`6f73ea6600d005c3649cf641c26e46bf98ff7cc51c0472074d5245d25fae1133`)
confirms exactly three prior regression controls changed from quarantine/outbox
mutation expectations to stronger full-row equality plus the independent
`track_history_regressed` fence. Their existing no-new-provider-effect,
claim/report denial and remote-commit assertions remain. The other prior drivers
and byte-identical independent 78 driver match their declared bindings. Original
producer failures and drivers remain frozen.

The initial two-case probe, initial 62-control run and final 69-control run are
preserved. The initial 62-control run had the two direct real failures plus one
fixture expectation error: the attempted quarantine-two restore was rejected by
SQLite's CHECK constraint before the enrollment test. The final driver explicitly
asserts that SQL rejection and row preservation. It retains all four real failing
expectations without weakening them.

## Evidence and limits

[The sealed review receipt](../verification/hosted-worker-pending-migration-history-review/receipt.json)
binds source/compiled manifests, frozen inputs, every attempt, exact commands,
tool/runtime versions, exits/signals, stdout/stderr EOF, the control report and
owned process/storage cleanup. Reproduce the review with:

```sh
python3 verification/hosted-worker-pending-migration-history-review/run.py
```

Root-provided HEAD `be472ce6424a691de5673e3438d2768264827d23` is context only;
Git is not consulted or changed. The review owns only its packet and this document.
All owned SQLite environments are disposed and removed; exact recorded owned
workerd PIDs are absent at seal. Hard restarts signal only the executable and
direct-parent-owned process after identity recheck. Other projects' processes and
data are preserved.

This is a finite local workerd/SQLite Engine review using the separately authorized
original controller fixture and synthetic provider/clock. It does not qualify
live integration, public/scheduled entry wiring, deployed alarms/restores/fleet
or capacity, production provider/clock behavior, live controller 71/process 20
suites, immutable-package FieldLog, signing/store, final phones or GA. Physical
phones remain disconnected. No native, provider, deployment, credential, live/root,
customer communication or publication changes occur. The frozen catalog inspector,
authority driver and rejected outbound-worker transport V2 lanes are not read,
imported or executed.
