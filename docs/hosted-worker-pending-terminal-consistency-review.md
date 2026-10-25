# Independent terminal-consistency review

The frozen candidate is **not accepted for live integration**. The final independent
actual workerd/SQLite matrix passed 72 of 78 controls. Four failures demonstrate an
introduced legacy-terminal enrollment regression; two demonstrate a pre-existing
ACK-ahead restore gap that remains in this candidate. The original stopped/completed
projection finding is fixed in the tested boundaries. This review changes no
production source and does not qualify deployment or GA.

The producer receipt is
`verification/hosted-worker-pending-terminal-consistency/receipt.json`, SHA-256
`e4afac5866c26ffd96c460bbdd54e3cf0098bc1d378601ba7e542d6f819e677b`;
patch SHA-256
`ca15d306c91dbdbccc3ae858fb09c0236258f5e51c2fa9dbc38b914ae73284d5`;
source digest
`b46bac2e4377663e2df078743c655c062f42cc92893a3d53b702476b05b6966f`.
All 158 producer artifacts, 212 frozen prior bindings and 21 candidate source
entries matched before execution and after it. The review copied the exact 13
production source files; only excluded fixtures and the independently authored
driver differ. The producer's 400 tests were not rerun by this review.

## P2: preserve explicit enrollment for valid migrated terminal rows

The new missing-outbox guard at candidate `src/engine.ts:51` treats every positive
terminal version with `registry_ack_version = "0"` and no outbox as corruption.
`enrollExisting` invokes that guard at line 524 before registration or its intended
outbox-producing save. This includes the valid state deliberately produced by
the unchanged schema-1/2 migration in `src/ledger.ts`: terminal bytes and version
are retained, new delivery fields begin at ACK zero and null outbox, and existing
row quarantine remains set.

The selected [registry contract](hosted-worker-pending-registry-contract.md)
lines 264–273 permits explicit enrollment of a known matching existing row,
persisting its outbox while retaining quarantine. Four independent controls
create genuine stopped/completed terminals, exercise the actual schema-1 and
schema-2 SQLite migrations, and invoke that maintenance entry. All return
`{"status":"conflict"}` and write the separate permanent fence with reason
`track_terminal_inconsistent`. The stopped version remains `"3"`; completed
remains `"9"`; original terminal JSON and migration quarantine remain unchanged.
There is no malformed terminal body or identity/provider disagreement.

The same four controls pass against the exact frozen predecessor production
modules: enrollment returns `enrolled`, saves the outbox and retains row
quarantine. The introduced guard therefore prevents the documented migration
enrollment path. The correction must distinguish proven legacy migration state
from a damaged registered terminal projection without clearing quarantine,
accepting malformed evidence, or weakening ordinary registered-row checks.
Constructor recovery also uses the same guard before any later enrollment.

The complete candidate observations are in
`independent-report.json` under `probe-schema{1,2}-{stopped,completed}-terminal-explicit-enrollment`;
`baseline-report.json` records the four positive predecessor controls.

## P2: fence a retained ACK watermark ahead of a terminal row

At `src/engine.ts:51`, the null-outbox branch rejects ACK below local version but
accepts ACK above it. `flushTrack` then returns true at line 107 before the
existing `trackSnapshotValid` regression check at lines 81–82 can run. This is
locally detectable history disagreement, rather than an absent remote watermark.

Two independent controls first perform a genuine exact terminal track/ACK, then
restore only `state_version` one lower while preserving the entire remaining
row, including its exact terminal, null outbox and retained ACK. Stopped is
restored from version/ACK `"3"` to version `"2"` with ACK `"3"`; completed is
restored from `"9"` to `"8"` with ACK `"9"`. Both `flushTrack` calls return
`{"flushed":true}` with no fence and no row changes. The remote terminal remains
committed at the higher version.

The same two cases fail against the predecessor, so this gap is **not introduced
by the terminal-consistency delta**. It remains incompatible with the selected
contract's restore/history fence and the existing explicit `ACK > state` guard.
Validate that relationship before the no-outbox success path, retain the observed
row, and record the independent fence. No remote rollback, cancellation or
reopening is requested or claimed. See
`probe-{stopped,completed}-missing-outbox-ack-ahead-history-regression` in both
candidate and baseline reports.

## Passing evidence and test limitations

The independent driver supplies 72 passing controls covering:

* The original wrong outbox terminal phase for both stopped and completed rows,
  at ordinary and int64 MAX versions, before snapshot, during the final pre-RPC
  await, and while an already committed remote ACK is held. Invalid rows remain
  exactly equal across every SQLite operation column, including outbox and ACK.
* Combined malformed terminal JSON and a mismatched provider through registered
  and plain command, constructor recovery, quarantine, explicit enrollment,
  identity-only recovery, valid-shaped claim/report, and reconciliation paths.
  Delayed effect validation, provider acceptance, final claim grant and report
  acceptance reject malformed outbox/terminal/provider combinations without
  overwriting evidence or causing another provider call.
* Strict duplicate-key detection, including escaped duplicate status keys and
  nested result duplicates, extra fields and oversized terminal bytes. Valid
  reordered fields and escaped status spelling retain their exact permanent
  bytes and hash those bytes rather than parsed/reserialized JSON.
* Independent same-version ACKs, legitimate newer identical terminal replay,
  and a terminal phase mutation after ACK durability. The later mutation is
  fenced while already committed ACK metadata and remote terminal remain
  committed; the review does not claim their rollback.
* Actual SQLite rollback of a throwing ACK callback and a preserved-fence
  transaction, first-fence identity/version/reason retention, exact ACK clearing
  without version increment, and fence durability over owned hard restarts.
  Ordinary and MAX terminal command admission reject an independent fence
  without changing the row or admitting claim/report authority.
* A nonterminal desired-run MAX row with consumed claim: provider fencing leaves
  the entire row unchanged with row quarantine zero; restoring the correct
  provider and hard restarting preserves the independent fence. Commands,
  claim, report, known recovery and repeated reconciliation cannot create effects.
* Real owned stop calls from a valid nonterminal committed stop during registry
  and clock outages with an independent fence. Cleanup remains possible; no
  terminal observation or drain/capacity authority is admitted.

The initial standalone six-case probes, initial 68-case run and final 78-case
run remain preserved. The initial run passed 60 cases and had six real contract
failures plus two overly strict report-test expectations: stopped rows had no
claim/instance, so their generated reports were invalid before entering any
authority path. The final fixture supplies valid-shaped report fields and both
controls pass. The initial baseline compilation rejected an unused fixture's
four-argument fence call because that optional argument did not exist in the
predecessor; that output is retained, and the unused action was omitted from the
baseline fixture. No production module was adapted to obtain baseline results.

Commands, installed runtime/tool versions, source and compiled manifests,
stdout/stderr EOF, every result and final process/storage checks appear in
[the sealed review packet](../verification/hosted-worker-pending-terminal-consistency-review/receipt.json).
The review owns only its packet and this document. All 158 owned SQLite storage
environments were disposed and removed; all recorded owned workerd PIDs were
absent at seal. Fourteen hard restarts signalled only exact
executable/direct-parent-owned workerd processes. Other projects' processes and
data were preserved.

Root-provided HEAD `ee390cbf56ba388a21c7d28c884dbed5fd7282fe` is context only;
Git was not consulted or changed. No live VM, root/live implementation, public
or scheduled entry, audit source, namespace, provider, deployment, credentials,
dependency or customer communication was changed. The frozen catalog inspector,
authority driver and rejected outbound-worker transport lanes were not read,
imported or executed. Fixtures use synthetic clocks/providers and real local
workerd SQLite. No native runtime or physical device was used. The live 71/20
suites, production clocks/providers, deployed schedule/alarm/restore/capacity
qualification, FieldLog immutable-package dogfood, final phones and accountable
GA acceptance remain pending.
