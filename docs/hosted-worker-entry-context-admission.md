# Existing-row entry context admission correction

This isolated correction is implemented in
`verification/hosted-worker-entry-context-admission/candidate/`. It has passed
ordinary local functional regression tests; it is not independently accepted or
integrated into the live controller.

The derivative starts from the sealed pending-entry integration candidate:
receipt SHA-256
`b1674bfda880aa2ccabbe0e3820aa68660cc34ae43b65bb59d5affd2bfbd67e6`
and artifact-manifest SHA-256
`b35d311da409fe15c826b8197cfb495222adb60da8dbf8aeb937e36605efdd25`.
All 65 candidate artifacts were checked against that manifest before copying.
The binding entry contract remains
`docs/hosted-worker-pending-entry-integration-contract.md` unchanged.

The existing failed assertion is preserved in
`verification/hosted-worker-pending-entry-integration-review/independent-report.json`:
20 of 21 groups passed, and a rejected immutable identity prevented later correct
enrollment on the same live object. That review was interrupted and remains
incomplete. Its receipt SHA-256 is
`d7659aab4e0ee0c906ca2a038c18a1c7f16c7ed3b3898ab14a127c9d80dec22f`;
its artifact-manifest SHA-256 is
`80d199c694862f7acfab1c4ab2326b53cefef4d759dc35e30780a2ba7b0fa593`.
This correction does not resume that review or treat its completed groups as
independent acceptance of the corrected candidate.

## Correction

Only `candidate/src/operation-state.ts` changes production behavior.
`enrollExisting` validates the complete supplied identity and exact operation
target, reads the existing row, captures its full JSON before any binding-hash
await, and checks `matchesRow` plus SHA-256 of the retained binding. A missing
row returns `missing`; a mismatch returns `conflict` without selecting context or
writing storage.

The private initializer receives the expected full-row JSON. After its final
awaited identity/target validation, it compares the current full row immediately
before the first `selected` and `initialization` assignments. No await separates
that comparison from the assignments. A changed or removed row cannot install
the stale context. Existing same-identity initialization still shares the one
initialization promise; no selected context or slot is reset per request.

Engine, Ledger, the public/private operation RPC surface, registry/audit code,
budgets and scheduled bounds are byte-identical to the producer. Quarantine,
history, MAX, provider, clock and empty-orphan recovery rules remain in their
existing implementations. Production provider, clock and object verifier remain
unavailable. The finite row-change fixture exists only in the excluded test
Worker and cannot be selected by production configuration.

## Observed functional evidence

All commands and first results are retained under this packet's `attempts/`,
including source/compiled/fixture manifests and separate stdout/stderr EOF.

| Suite | Passed | Scope |
| --- | ---: | --- |
| Admission regression | 6/6 | Missing row; wrong immutable digest/platform followed by valid enrollment without restart; binding SHA mismatch; full-row change across an await; retained context |
| Existing entry suite | 45/45 | Entry ordering/budgets, one Engine/in-flight guard, restart, migration, recovery, scheduled delivery fixtures, terminal/history/MAX behavior |
| Existing controller suite | 28/28 | Existing controller and original contract assertions using actual local workerd SQLite and finite fixture effects |

The rejected digest/platform cases create zero new Engines and preserve the full
row and fence. Their later valid enrollment succeeds without a restart. The
finite await case schedules one non-identity history-field change after the row
snapshot; enrollment returns `conflict` before creating an Engine, preserves the
fixture's changed row exactly, and allows a correct retry without restart.
Valid enrollment retains quarantine and all preexisting history fields except
the existing registration/version/outbox/ack updates that enrollment requires.

The compiler succeeded. `production-closure.json` records the 16 reachable
compiled production files and their hashes for build provenance. This static
closure record is not release authorization or an independent audit.
`tool-versions.json`, the final source/compiled/fixture manifests, the exact
source/test and compiled diffs, `cleanup-reconciliation.json`, and `receipt.json`
bind the final candidate and observed environment. The packet is sealed read-only
after final hash and owned-process/store cleanup checks.

## Remaining limits

The current root revision is root-provided
`4ffd5ecf974c3ac8c8a052e9a533fcd7b244f545`; no Git command was run by this lane.
Exact source hashes are authoritative for this derivative. The evidence uses
local workerd SQLite and synthetic provider/clock fixtures. The interrupted
independent review remains incomplete, and the corrected candidate needs its
separate authorized acceptance process before live integration.

No provider calls, deployed schedule, deployment/rollback qualification,
credentials, signing/store/FieldLog publication, operational/GA gate, customer
message, native run or physical-phone run is established here. Physical phones
remain disconnected and deferred. Live code, predecessor packets and root
trackers were not modified. No frozen catalog-inspector/authority-driver or
rejected outbound-worker V2 lane was imported or executed. No new dependency or
Patch/Skip material was used.
