# Independent pending-registry track review

The frozen candidate is **not accepted for live integration**. Forty independent
focused actual workerd/SQLite controls passed, but an additional restored-state
control reproduced a terminal projection consistency defect twice. The final
synchronous track barrier, validated atomic ACK clear, and independent fence at
MAX behaved as claimed in the focused controls. This review changes no production
source and supplies no deployment or GA acceptance.

The reviewed packet is
`verification/hosted-worker-pending-registry-track-recheck/receipt.json`, SHA-256
`d9bd48d069746b24ed3386e9842a1693e5aba44c33ffd4e095646acaef7cff5c`,
with patch SHA-256
`a7876fc0786f53ea3e201a1969a3f90a07a0c48c71e2602151f5a4ee7ac64372`
and source digest
`f4290d7ab0ece9eb2546d9b6125054d6cbbd4d9ab572d418679fbc41e748b799`.
All 91 frozen binding/artifact checks passed before and after execution. The
prior correction review receipt remains
`c1c53d5437854fb9fb0aa24fabd19cc5cb9053f4c40ca29393801da1abe4ce29`.
The earlier 75-group pass, actual MAX rollback failure, and final 81-group packet
are preserved and hash checked. Its 81 groups are prior 54 plus 27 focused groups;
this independent review did not rerun that entire suite.

## Finding: bind terminal projection phase to permanent row evidence

**P2; reproducible in actual workerd/SQLite.** In the frozen engine's
`flushTrack` terminal branch, lines 79–82 check exact terminal JSON bytes and
allow either `completed` or `stopped`, but never require the projection phase to
match the row's phase or the status encoded by those permanent JSON bytes.
The final barrier compares the row against the already-corrupted snapshot, so
it cannot discover an inconsistency that existed before that snapshot.

The finite fixture first creates a legitimate stopped row with a retained
terminal outbox and a still-pending registry. It then changes only the restored
outbox's terminal phase to `completed`. The row phase remains `stopped`, the
exact terminal evidence remains `{"status":"stopped",...}`, and identity,
receipt, binding, resource, version and provider remain unchanged. Calling
`flushTrack` returns `{ "flushed": true }`. The registry becomes permanently
quiescent with terminal phase `completed` and SHA-256
`7c7523d853a210cb51c8005872b8932a7969b042672b38b38943d52135d3777e`,
which hashes the local **stopped** evidence. Local ACK metadata advances, the
outbox is cleared, and no fence is written.

The initial and repeated reproductions are retained in the review packet. The
repeat exits 1 on the assertion requiring fail-closed behavior; complete before,
restored and after rows, remote projection, command output and cleanup appear in
`snapshot-consistency-report.json` and `commands.json`. The mismatch check is
also absent in the frozen predecessor, so this defect is not introduced by the
two-module correction delta. It remains a failure of the selected candidate's
terminal/outbox/row consistency contract.

Before invoking track, require the phase/status derived from the exact permanent
terminal bytes, the operation row's terminal phase, and the terminal outbox
phase to agree. The outbox's terminal presence must likewise agree with the
permanent row. A disagreement must fail closed, retain local recovery evidence,
and preserve the independent fence even at MAX. This review makes no proposed
production edit and does not claim that an already committed remote terminal
can be cancelled, rewritten or reopened.

## Passing focused evidence

The 40-control suite uses an owned copy of all frozen production source bytes,
the same corrected registry binding, and finite test-only fixture additions.
Production source is byte-identical to the frozen candidate. The full source
and compiled manifests, concrete commands, tool versions, stdout/stderr, exit
codes, and frozen-input checks are in the review packet.

The controls include 15 mutations during `before_track` and 14 mutations while
an already committed remote terminal ACK is held. They cover provider mapping,
missing provider, retained identity and receipt, immutable binding and digest,
resource key, operation ID, missing row, exact outbox and permanent terminal
bytes, row phase, regressed version, independent fence and quarantine. The
pre-RPC guard prevented remote mutation; delayed ACK guards retained local
outbox/ACK state and prevented claims/reports after unsafe changes. The remote
terminal remained committed in post-track cases; the tests make no rollback or
cancellation claim. Retained local alarms and outboxes remain recovery hints,
not proof of deployed alarm delivery or external fleet discovery.

Independent ACK progress before RPC cancels only redundant delivery. Independent
ACK progress and legitimate newer identical terminal versions while an older
ACK waits preserve the newer watermark and exact latest state. A provider change
during ACK sync is rejected by the final return guard. Direct actual-SQLite
ACK callback controls verified rejection without metadata writes, a committed
fence with retained outbox, rollback of callback writes on throw, and an allowed
exact ACK clear without operation-version increment.

At MAX, a **nonterminal desired-run row with an already consumed claim** was
provider-fenced, restored to the correct provider and hard restarted. The entire
operation row stayed byte-for-byte equal to the original row, including version,
outbox and `quarantined = 0`. Its separate permanent fence survived restart.
A new command, claim, report and known recovery were rejected; two reconciliation
calls produced no new provider calls. This proves rejection from the independent
fence instead of relying on terminal state or the row quarantine flag. Additional
MAX controls verified exact positive/duplicate terminal ACKs and delayed committed
terminal ACK rejection, corrected-provider restore and restart with retained
local outbox and alarm. Existing owned stop cleanup exceptions remain governed
by the stop-terminal contract; this is not a claim that all cleanup effects are
forbidden by every fence at ordinary versions.

## Scope and cleanup

All 40 focused harness environments and both finding reproductions were disposed;
all their temporary SQLite storage directories were removed. Three focused
hard-restart controls killed only the exact executable/direct-parent-owned
workerd process. A final process/storage check covers every recorded owned PID
and directory. Other projects' processes were not signalled. No simulator,
emulator or physical device was used.

Excluded: live/root source edits, Git changes, public or scheduled entry wiring,
schedule installation, external provider publication, customer communication,
qualified production clocks/providers, live 71/20 suite reruns, native/device
qualification, remote cancellation, distributed atomicity, deployed alarms and
restore qualification, and GA acceptance. The catalog inspector, authority
driver, rejected outbound-worker transport and audit source were not imported
or evaluated. Root-provided HEAD `ee390cbf56ba388a21c7d28c884dbed5fd7282fe`
is recorded as context only; Git was not consulted or modified by this review.
