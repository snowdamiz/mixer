# Terminal consistency and evidence-preserving quarantine

This isolated derivative corrects the terminal projection consistency finding in
[the independent track review](hosted-worker-pending-registry-track-review.md).
The frozen track-recheck candidate, all historical attempts and the review packet
remain unchanged. This packet is bounded to Engine/Ledger copies and excluded
actual-workerd/SQLite fixtures; root selects any later live integration.

Before remote tracking, the exact permanent terminal JSON is parsed with the
existing bounded strict parser and its closed stopped/completed observation shape
is validated. Its parsed status, operation phase, terminal presence, exact outbox
bytes and outbox phase must agree. Terminal next-due must be null. A terminal row
without an outbox is valid only after its current version has already been
acknowledged. A nonterminal projection must contain explicit null terminal state.
The evidence digest hashes the exact permanent bytes, including valid whitespace;
parsing does not normalize, repair or replace them.

The same synchronous check runs against the initial row, the final pre-RPC row,
the row inside the atomic ACK callback and the row after ACK sync yields. The
existing exact snapshot/version/identity/provider checks still apply. No await
separates the final pre-RPC transaction from RPC invocation, and no transaction
spans hashing, hooks, storage sync or a remote/provider call. An independent exact
ACK may suppress a redundant start or advance metadata without a fence; legitimate
newer identical terminal evidence retains its existing replay behavior.

An inconsistency records the existing independent permanent fence using a narrow
Ledger option that preserves the entire operation row. This path never parses or
saves malformed terminal bytes, repairs a phase, replaces a recovery outbox,
changes ACK metadata, increments a version or changes row quarantine. It preserves
the exact observed row at ordinary versions and at int64 MAX. Default fencing
still has its existing below-MAX quarantine transition and MAX behavior; the
first independent fence's identity/version/reason remains retained.

Consistency precedes early provider fencing and row saves in registered/plain
command admission, effect preparation, final effect validation, provider-result
acceptance, constructor recovery, claim consumption/final grant, report validation
and acceptance, identity-only recovery, explicit enrollment and explicit local
quarantine. Generic asynchronous fence calls also validate the current projection
before their normal save. This prevents a combined malformed terminal and wrong
provider from reaching an earlier save that could throw or overwrite recovery
evidence. Reconciliation's exception cleanup likewise preserves invalid state.
The selected owned-cleanup exception remains for valid nonterminal committed
stops. An independently fenced terminal row rejects commands without mutation,
including at MAX; terminal state cannot turn that cleanup exception into a reply
or metadata admission path.

The first preserved runtime attempt passed the prior 81 groups, all 40 independent
review controls and 141 of 165 initial new controls. Its 24 failures exposed the
previous command stop exception on restored fenced terminal rows: ordinary
versions returned terminal and mutated metadata, while MAX attempted an exhausted
save. The coordinated command/recovery guards above correct that behavior. This
attempt is retained in `runs/20261025T053643803896Z` with its exact source, output,
EOF, failure report and owned cleanup evidence.

The final run `runs/20261025T054037055986Z` passed **400/400 actual
workerd/SQLite groups**: 81 unchanged prior groups, 40 unchanged independent
review controls and 279 new controls. Its source digest is
`b46bac2e4377663e2df078743c655c062f42cc92893a3d53b702476b05b6966f`.
Across both preserved attempts, 686 owned storage environments were removed and
80 hard-restart controls killed only executable/direct-parent-owned workerd
processes. Every recorded owned PID and storage directory was absent at seal.

The final source-bound results and hashes are recorded in
[the sealed receipt](../verification/hosted-worker-pending-terminal-consistency/receipt.json).
Run the complete bounded packet with:

```sh
python3 verification/hosted-worker-pending-terminal-consistency/run.py
```

The final matrix reruns the unchanged 81-group driver and unchanged 40-control
review driver, then tests genuine completed/stopped positive flows, null versus
present terminal state, all row/outbox/status disagreements before snapshot,
during pre-track awaits and while committed remote ACKs are held, malformed JSON
and closed bodies, duplicate status fields, exact digests, full-row preservation,
normal/MAX permanent fences, corrected-state restores and hard restarts,
independent ACK progress, and the early authority-path ordering above. Source,
commands, installed tools, exit states, stdout/stderr EOF, process identity and
owned SQLite cleanup are bound in the packet.

A remote terminal committed before a later local mutation remains committed; no
rollback, cancellation, reopening or distributed atomicity is claimed. If local
ACK metadata already committed before a subsequent sync-time mutation, it is not
rolled back: the newly observed row and permanent terminal bytes are retained and
independently fenced. A retained alarm/outbox is a recovery hint, not deployed
alarm delivery or independent fleet-discovery qualification.

No live/root/Git files, public or scheduled entry, audit module, namespace,
provider, schedule, credential, dependency or deployment was changed. The frozen
catalog inspector, authority driver and rejected outbound transport lanes were
not read, imported or executed. Synthetic clock/provider and hostile restore
fixtures remain excluded from production imports. The live 71/20 suites,
production clock/provider behavior, deployed restore/alarm/capacity operations,
FieldLog immutable-package release qualification, final physical phones and GA
acceptance remain pending. No native runtime or customer communication occurred.
