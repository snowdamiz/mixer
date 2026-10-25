# Pending-registry engine correction independent review

Review status: **changes required**. One fresh actual workerd/SQLite control
confirms a remaining provider-binding race at the terminal-track boundary.
The two defects from the original review are addressed at report acceptance
and the tested provider action/grant boundaries, but this correction should
not be integrated until its asynchronous tracking boundary is repaired.

The frozen correction receipt SHA-256 is
`3af44bc2353edab386ba20b30e647a71a2b70301c3e37ba2aea50de100a381f1`,
its patch is
`04203b53a6c22b252b781adca727511d977ec5a3e64b83ece2f60dce3f3653d7`,
and its executed source digest is
`ee330a270f6151dfff96ed561a8b654ca1cc753026d03583cea99aee4276d811`.
The original failed review remains unchanged at receipt
`3476e3e26845e4b3b21cf0208aac883908660fa5e3ae8c83392ec3859c824de0`.
This review's production source is byte-identical to the frozen correction.
Only excluded finite test fixtures and an independent runner were added or
changed in the owned review copy.

## Finding

**[P1] Recheck the trusted provider binding after tracking awaits.**
In the frozen correction's `candidate/src/engine.ts`, `flushTrack` checks
`providerMatches(snapshot)` at line 39. It then awaits retained-context
validation, terminal hashing and the `before_track` hook. Its final read at
lines 60–61 compares state version, outbox, receipt and terminal bytes, but
does not recheck the current provider binding. The acknowledgement path at
lines 67–73 also omits this check.

The independent control starts with a correctly admitted stopped terminal,
with its exact terminal outbox still pending after a deliberately lost delivery.
It pauses a subsequent flush at `before_track`, then restores
`provider_kind=external-macos` without changing the ledger version, while the
trusted Android adapter still selects `cloudflare-linux`. After resuming,
`flushTrack` returns `true`, tracks the terminal projection, and clears the
local outbox. The registry becomes quiescent (`pending=0`) at state version
`3`; the conflicting provider is retained with `quarantined=0` and no permanent
fence. No new provider action is required for the counterexample.

This is the same explicit same-version restore/race model used by the
producer's report correction controls. An initial mismatch at `flushTrack`
entry correctly fences, so the failure specifically crosses the await.
It bypasses the correction's stated retained-provider tracking check and can
retire independent pending discovery before the mismatch is fenced.

Before starting `track`, re-read and independently enforce the trusted provider
binding after every hashing/validation await, persist the permanent fence on
disagreement, and decline terminal delivery. Audit the post-RPC acknowledgement
boundary for the same mismatch; an acknowledgement is delivery metadata and
must not substitute for a provider-binding check. Preserve the exact original
resource and terminal bytes rather than repairing identity. Keep existing
ACK-only outbox progress admissible when its identity remains valid.

The counterexample is labelled `productStatus=changes-required` in
`verification/hosted-worker-pending-registry-engine-correction-review/report.json`.
The runner's zero exit means its assertions reproduced the recorded outcomes;
it does not mean product acceptance.

## Focused evidence

The independent runner executed **47 actual workerd/SQLite controls**:
46 passing safety/positive controls and one reproduced product defect.
The existing 54-group producer suite was source-bound and verified rather than
rerun. The review read the complete corrected Engine, Ledger, schema,
registry-context and private interfaces against the selected pending-registry,
stop/terminal and permanent-terminal-replay contracts. Boundary details are in
`verification/hosted-worker-pending-registry-engine-correction-review/boundary-review.json`.

Passing controls cover all three mismatched first commands without row
creation; retained track/claim/report/enrollment entry; constructor recovery;
provider mutation during launch and stop dispatch barriers; provider mutation
after an actual effect observation; consumed-claim and enrollment await races;
all four qualified clock-history fields, all authority and effect snapshot
fields, and retained identity/receipt/claim mutations during verification;
independent permanent fence and same-version quarantine/result/terminal/desired
changes; and valid ACK-only delivery progress during report verification.
All report mutation cases reject without accepting a new result. A conflicting
adapter never receives a provider action in the tested action boundaries,
including the retained stop path.

Exact build and test commands, times, exits, versions, complete stdout/stderr
EOF, source manifest, fixture patch and before/after immutable-input checks are
retained in the review packet. The input checks validated 121 hashes and bound
286 frozen files; all remained unchanged at sealing. The corrected registry
dependency remains
`99d8a5dc4e2e9b8875c262ae44d2f1307d3107d3bc48c4300e981f68ec12b428`.
Only `engine.ts` differs from the original production candidate.

All 47 owned SQLite storage environments were disposed and removed. All 48
observed owned workerd process identities, including one orderly restart,
were absent after cleanup and again at sealing. No SIGKILL was performed.
The fixtures use the actual fixed registry DO binding and SQLite storage;
their provider, clock and fault controls remain excluded synthetic helpers.

No live production file, tracker, Git state, native/device environment,
customer channel, deployment or production configuration was changed.
The frozen catalog-inspector/authority-driver and rejected outbound-transport
lanes were not accessed or executed. This review does not rerun the live
71 controller groups or 20 process controls and does not select Engine live
integration. Public/scheduled entry wiring, production-qualified clocks and
providers, operational/restore qualification, separate-repository immutable
FieldLog dogfood, final physical-phone acceptance and GA gates remain outside
this evidence. Root must select and independently verify a repaired derivative
before integrating the Engine/Ledger packet.
