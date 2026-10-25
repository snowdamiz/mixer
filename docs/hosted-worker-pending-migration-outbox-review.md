# Independent null-outbox migration acceptance review

The selected cumulative Engine candidate is accepted for root-selected development
integration. Fresh actual workerd/SQLite tests pass **37/37 controls**, with no
actionable finding. This closes the four explicit-enrollment failures in the
immediately preceding migration-history review. Entry integration and GA acceptance
remain separate, pending work.

The reviewed producer receipt is
`verification/hosted-worker-pending-migration-outbox/receipt.json`, SHA-256
`a27b0ce3438705f0bd30ae4dd088f19d4ece3367cb91f78ad42eab8b1413bca1`,
with aggregate source digest
`36dd888e47b999cb4a60c2d5f76789f878068a9f04340d86e23d70c917d50f15`
and compiled digest
`281c5fffbb5c78bf58a2d513e29ae1d93e66664615b1caa5987e793856844f14`.
The exact production patch has SHA-256
`94f76c441b8a86f224dafb43403aa2b83446c089bf0ad823cc3a1c486faff7b3`.
All 244 producer artifact bindings and all 359 inherited frozen input bindings
match. The previous failed review receipt, SHA-256
`43992550d3fff245b10e0d019c484f904f24f6de1b4de6bb2645635e0cc3aa06`,
and its original failing controls remain unchanged.

## Reviewed change and both call sites

Exactly one production condition is added to
[Engine line 42](../verification/hosted-worker-pending-migration-outbox-review/candidate/src/engine.ts):
`r.track_outbox_json===null` in `unenrolledMigrationShape`. The rest of Engine
and all twelve other production files are byte-identical to the preceding
migration-history candidate. All thirteen production files in this independent
review are exact producer copies; the compiled production files are also exact
matches. The full accepted source and compiled closure is bound by
[source-closure.json](../verification/hosted-worker-pending-migration-outbox-review/source-closure.json).

The helper has two call sites. `terminalProjection`, at line 57, invokes it
inside the existing exact-null outbox branch; the new condition is already true
there. This retains observation of genuine quarantined migration terminals.
`enrollExisting`, at line 543, invokes it only for the fully unenrolled identity
and registration pair. That path now rejects a non-null outbox before
`nextVersion` and before registry registration. The already-registered path does
not invoke this helper. Canonical bounded history validation runs before shape
acceptance; both zero and MAX behavior retain their existing semantics.

The final synchronous enrollment transaction, after registry and identity/hash
awaits, rechecks terminal consistency, provider identity, permanent fence and
equality of the entire current operation row against the originally validated
row. The null-outbox precondition cannot be bypassed by restoring another row
while enrollment awaits. This condition neither clears quarantine nor grants
claim/report/command authority, and it does not assert historical provenance.

## Fresh runtime evidence

The review authors its own assertions and controls. It copies the authorized
finite original-controller fixture and adds only excluded registry-call counters.
These counters detect a duplicate registration RPC even when registry record
bytes do not change. No producer test assertion or production source is edited.
The 37 controls cover:

* The four original stopped/completed, direct/hard-restart cases with a valid
  reintroduced outbox and null registration. All return `conflict`, retain every
  operation column, preserve quarantine one and terminal bytes, keep provider
  calls unchanged, and issue **zero registration or tracking RPCs**. Constructor
  recovery preserves these valid projections without a corruption fence.
* Genuine stopped/completed terminals through actual schema-1 and schema-2 SQLite
  migration, constructor recovery, explicit recovery and hard restart. With an
  exact-null outbox they enroll successfully, advance exactly once, retain all
  other operation columns and quarantine one, and create the matching versioned
  terminal outbox. No automatic registration/tracking or provider effect occurs.
  Claim, valid-shaped report and plain command remain denied before and after
  enrollment.
* Empty and malformed outbox bytes, direct and after hard restart for both
  terminal phases. Each is preserved exactly and rejected with the independent
  `track_terminal_inconsistent` fence. These cases are distinct from a valid
  non-null outbox, which is consistent evidence but still outside the selected
  unenrolled migration shape.
* Already-registered stopped/completed rows with a valid pending outbox. Explicit
  enrollment remains accepted, advances once, sends the exact new projection,
  clears its ACKed outbox and retains registration and permanent terminal bytes
  without another provider effect. Partial identity/receipt, empty and malformed
  registration pairs with null outboxes continue to reject.
* Ten asynchronous final-row controls: while enrollment is held before its
  explicit registry RPC, restore a valid/empty/malformed outbox, failure count or
  provider identity for each terminal phase. All reject local enrollment and
  preserve the entire restored row across hard restart. Exactly the requested
  duplicate registration round trip occurs after release; there is no new remote
  record, tracking call or provider effect. Remote rollback is not claimed.
* Both terminal phases at MAX with a null migration outbox. Neither registers,
  acquires partial local registration, wraps/resets a version or changes a row.
  Both real retained-ACK/lowered-state controls preserve the complete row and
  remote history under the independent `track_history_regressed` fence.
* A committed nonterminal stop continues its owned provider cleanup under an
  independent fence plus registry and clock outages, while terminal, claim and
  report authority remain withheld.

The producer's 769 groups were not rerun for count. Their sealed reports and
original drivers were hash-verified; the fresh 37 controls target this exact
condition and its dependencies. Acceptance of the cumulative Engine relies on
those retained prior reviews and this correction review, with the selected
migration/history contract preserved.

## Evidence and limits

[The sealed receipt](../verification/hosted-worker-pending-migration-outbox-review/receipt.json)
binds all inputs, source and compiled manifests, exact commands, installed tool
versions, outputs, exits/signals, stdout/stderr EOF and cleanup. Reproduce with:

```sh
python3 verification/hosted-worker-pending-migration-outbox-review/run.py
python3 verification/hosted-worker-pending-migration-outbox-review/seal.py
```

All 37 owned SQLite environments were disposed and removed. Seventy-eight hard
restarts targeted only the exact executable and direct-parent-owned workerd PID
after identity recheck. Every recorded owned PID is absent at seal. Other
projects' data and processes are preserved.

Root-provided HEAD `be472ce6424a691de5673e3438d2768264827d23` is context only;
Git is neither consulted nor changed. This review owns only its packet and this
document. It does not integrate live Engine or entry code or change unrelated VM
work. The frozen catalog inspector, authority driver and rejected outbound-worker
transport V2 lanes are unread, unimported and unexecuted.

This is finite local actual-workerd/SQLite evidence with a synthetic clock and
provider. Live controller 71/process 20 suites, public/scheduled entry wiring,
production provider/clock behavior, deployed alarms/restores/fleet/capacity,
immutable-package FieldLog, signing/store, final physical phones and accountable
GA acceptance remain pending. Phones remain disconnected; no native/UI/phone,
provider/deployment/credential, customer messaging or publication changes occur.
