# Quarantined migration enrollment and retained ACK history

This isolated derivative corrects both findings from the frozen
[terminal-consistency review](hosted-worker-pending-terminal-consistency-review.md).
The original terminal-consistency producer receipt remains
`e4afac5866c26ffd96c460bbdd54e3cf0098bc1d378601ba7e542d6f819e677b`, its
source digest remains
`b46bac2e4377663e2df078743c655c062f42cc92893a3d53b702476b05b6966f`, and the
review receipt remains
`2a5646144c8696d6ff2c02d935a6942a18d61dd0c5f8ddf7e99314f5aa0dab13`.
All 335 files in those two packets are bound before and after execution and at
seal. Their original source, drivers, failed attempts and evidence remain frozen.

The only production-module change is in the excluded Engine copy. Ledger, schema, wire, clock, provider,
registry and public contracts remain byte-identical to the frozen candidate.
The terminal parser still validates the exact bounded permanent bytes, their
closed stopped/completed body, matching row/outbox phases, terminal presence and
null terminal next-due. Terminal version zero is rejected. Exact valid whitespace
and escaped bytes remain permanent evidence rather than repair input.

A missing terminal outbox is tolerated only for the bounded shape consistent
with the source schema-1/2 migration: quarantine is exactly one, state version is
positive canonical bounded decimal, ACK is exactly `"0"`, and both retained
identity/registration and both barrier fields are exactly null. The null outbox
branch itself supplies the remaining null field. This shape is not proof of
historical origin. Recognizing it only preserves quarantine and the documented
explicit maintenance path; it does not enumerate operations, enroll automatically,
clear a fence, synthesize a row, grant command/claim/report authority or dispatch a
provider effect. Constructor recovery and hard restart can observe valid migrated
terminal evidence without permanently fencing it before maintenance can run.

Explicit enrollment requires the caller's fixed full identity, existing matching
row, immutable binding digest and trusted provider. A previously unenrolled row
must retain the complete migration-consistent quarantine/barrier/ACK shape;
partial, empty or malformed registration state is rejected. Retained registration
must validate against the full fixed context. Following all asynchronous work,
the synchronous final transaction validates consistency/provider again, refuses
an independent fence and requires equality across every operation column with
the initially validated row. Only then does it save matching registration and a
new versioned outbox, retaining quarantine and every other operation field.
Exhausted MAX rows cannot wrap, reset, acquire a partial local registration or
manufacture an unversioned outbox.

Both state and ACK versions are validated as canonical bounded decimal before
projection acceptance. A retained ACK greater than state records the independent
`track_history_regressed` fence while preserving the entire observed row,
including ACK, outbox, quarantine and terminal bytes. This guard runs before any
no-outbox success and through the existing synchronous guards on authority,
recovery and ACK boundaries. It covers terminal and nonterminal rows. Valid ACK
equality and a valid pending outbox whose ACK is lower remain accepted. Invalid
or overflowing history values fail closed with the same full-row preservation.
No remote history rollback, cancellation, terminal reopening or distributed
atomicity is claimed.

The final full actual workerd/SQLite matrix passes **688/688 groups**: the prior
81, 40 and 279 groups; the independent 78 controls with its driver byte-identical;
and 210 new migration/history groups. All six independent finding cases now
pass. The new matrix uses genuine stopped/completed state and actual schema-1/2
SQLite migration, before and after constructor/recovery/restarts and explicit
enrollment, plus full-row preservation checks, hostile registration/barrier/
quarantine/version deviations, malformed terminal bodies, enrollment races,
retained fences, ordinary/MAX history boundaries, exact ACK equality and lower-ACK
pending delivery. Existing valid nonterminal committed-stop cleanup remains
covered by the prior and independent controls.

Three prior control assertions required a narrow derivative amendment: they
expected quarantine mutation or replacement outbox creation on restored ACK-ahead
state. The selected preservation contract requires exact restored-row equality
instead. The derivative strengthens those three controls to assert that equality
and the independent permanent history fence while retaining provider/claim/report
and remote-commit assertions. The other 397 prior controls retain their original assertions; all 78 independent
controls retain their original bodies. The original drivers remain frozen;
`assertion-amendments.patch` binds the exact assertion-only diff. The initial full
run is accurately retained as failed, with these three conflicting expectations;
its independent 78 and new 204 controls passed. The earlier standalone 189-group
pass is also retained, separately from final qualification.

The [sealed receipt](../verification/hosted-worker-pending-migration-history/receipt.json)
binds the source digest, exact Engine patch, original inputs, all attempts,
commands, installed tool versions, exits/signals, stdout/stderr EOF and ownership
based process/storage cleanup. The reproducible complete candidate run is:

```sh
python3 verification/hosted-worker-pending-migration-history/run.py
```

This packet awaits a fresh independent review and root-selected live integration.
No live/root/Git/native/provider/deployment or unrelated VM source was changed.
No frozen catalog inspector, authority driver or rejected outbound transport lane
was read, imported or executed. The fixture's clock/provider and hostile restores
are synthetic and excluded from production imports. Public or scheduled entry
wiring, live controller 71/process 20 suites, production clock/provider behavior,
deployed alarms/restores/fleet discovery/capacity, immutable-package FieldLog,
signing/store/final physical phones and GA acceptance remain pending. Physical
phones stayed disconnected; no customer communication or publication occurred.
