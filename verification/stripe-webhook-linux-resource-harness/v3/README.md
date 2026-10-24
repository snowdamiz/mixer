# Private resource harness v3: two source review repairs

This version repairs the two P1 findings in the sealed independent v2 review:
runtime admission after incomplete cleanup, and missing nonleader namespace/FD
holders. The root selected only this source repair in
`v2-cleanup-review-repair-selection.json`. It retains the four selected R14 phases
and 34 finite R18 fault boundaries. It has **no Linux compilation or execution
evidence**, no runtime acceptance, and no GA acceptance. All 30 matrix rows stay
pending. It adds no production route, provider, deployment or dependency.

Both sealed v1 and v2 remain byte unchanged. `checkpoint.py` checks the v2
104-file seal and completed independent review seal, as well as the v1
98 original file bindings and the 99 regular files in `../checkpoints/v1.tar`,
whose extra member is the original seal. Later versioned files are deliberately
outside that checkpoint. The legacy recursive v1 verifier sees later files as
additions; use the explicit checkpoint verifier for the frozen v1 snapshot.

Suite orchestration permanently blocks every later row after an attempted row
lacks complete validated cleanup. It preserves preceding actual failed receipts
and marks later rows unavailable/unrun with zero launcher starts. The backend
independently revalidates every earlier session's zero-holder/removal proof and
original disposal deadline before any phase or fault session is constructed.
Refusal or a failed cleanup proof preserves the prior active session and latches
admission closed, even if mandatory later cleanup succeeds physically. A row
failure with complete validated disposal can continue; an incomplete disposal
cannot. A later orchestration error never replaces earlier observed receipts.

`proc_inventory.py` enumerates `/proc/PID/task/TID` for every observed task and
reads each TID's namespace and FD metadata, including unshared FD tables. Owned
directory handles, no-follow child opens and named inode/owner checks bind the
enumerated identities. Each task's namespace/descriptor view is read twice;
two complete process/task inventories must agree. New tasks, changed identities,
namespaces or FD metadata, inaccessible directories, and missing metadata for a
still-live task refuse a zero-holder proof. A disappeared task is accepted only
after explicit name absence is verified under the same original deadline. All
inventory handles close even on refusal. Shared references may count more than
once across threads; these are holder checks, not a unique socket capacity claim.
Host churn or restricted metadata can make cleanup unavailable; no inventory retry loop,
deadline reset, process-content read, foreign signal or weaker fallback exists.

The C launcher, NIF, role and pinned signal authority bytes are identical to v2.
The reviewer's initial NIF mismatch premise was withdrawn; no NIF repair is
included. All revised code and its cleanup reachability need independent review.

The root's `r14-r18-private-interface-amendment.json` selects four phase names and
the existing ready tuple semantics; `r14-real-signal-amendment.json` selects the
actual SIGTERM trigger and bounded trap authoring contract. `contract-table.json` maps this version's
exact source-derived fault enum to component, pre/post boundary, observed
condition and cleanup obligation. The enum and its reachability require a fresh
independent source review before runtime. The controller accepts no phase/fault
command, FD, path or callback from HTTP; all test selections are closed enums.

`role.exs` arms these fixtures before sending `ready generation port`:

| Phase | Required observed fixture |
| --- | --- |
| idle | Actual private listener and no request owner/capture |
| h1_body | Admitted original owner with an incomplete fixed-length body pending and no completed capture |
| h2_reader_frozen | Original admitted H2 owner suspended; DATA messages actually queued; bounded PING traffic sent; no completed capture |
| blocked_response | Exact synthetic capture, an original live response owner waiting, unchanged chunk progress for at least 200ms and positive kernel TCP send queue |

The private response uses only 418. The blocked response is bounded to 1024
16-KiB chunks, below the selected 32-MiB wire bound including finite framing and
request overhead. The synthetic client's receive window is small while arming
backpressure, then increases to a fixed 1 MiB only after original owners are
killed, to observe actual FIN/RST within the unchanged stop deadline. No server
configuration, logical admission limit or response deadline is relaxed.

At stop the role closes the private admission gate and emits `phase_gate` while
retaining the original active request owners and phase. The controller must
observe that exact receipt before sending one actual SIGTERM to the unique
owned namespace PID2 via a stable pidfd with namespace, IDs and current cgroup
membership rechecked. The fixed role trap observes that those original owners
and the selected phase are still active at actual signal handling, kills the
owners, stops transport, observes owner DOWN and peer closure, emits numeric
results and sends the existing stopped tuple. Completed request owners cannot
substitute for active owners. H2 suspension/queued messages and blocked-response
progress/kernel backpressure are rechecked at signal handling.

The custom trap waits at most 1000ms for the role's disposal acknowledgement and
emits a required positive `term_callback` completion record before returning to
default handling. Default handling, early trap return or timeout cannot qualify
without all required observations. The exact official
[Elixir 1.20.4 trap implementation](https://github.com/elixir-lang/elixir/blob/v1.20.4/lib/elixir/lib/system.ex)
and [OTP 29.1.1 default handler](https://github.com/erlang/otp/blob/OTP-29.1.1/lib/kernel/src/erl_signal_handler.erl)
are read-only source references, pinned by content hashes in `signal-authority.json`.
Their code is not copied into the harness.

The controller independently owns the 2000ms grace and 2500ms final disposal
deadline, both starting at its first successful actual TERM send. Gate preparation
is bounded inside the same row/suite deadline. Role timestamps establish local
causal order only. No zero-TERM stop, late capture, absent peer closure, stale
phase, intended setup or generic smoke result substitutes for these observations.

`linux_backend.py` implements serial, identity-marked cgroup/namespace launches
with exact limits, sealed Linux release and tool bindings inherited from v1.
Fresh compiler outputs must be Linux ELF for the actual architecture and match
the sealed release's helper/NIF bytes exactly. Build provenance and runtime
symbol resolution remain independent review and Linux replay obligations.
It uses pidfds plus current cgroup membership for signals, including a separately
owned launcher pidfd covering the trusted setup process before its first join.
Its finite C/role hooks emit only explicit numeric reached/injected counters.
The controller hooks occur at actual resource/control boundaries. Stage 28/29
fixtures deliberately stop the owned tasks so signal/kill boundaries cannot be
claimed after the role has already exited normally; that freeze occurs after
the observed gate close and before the actual TERM.

Faults do not enter the independent cleanup selector. Cleanup preserves the
original TERM clock after an injected failure, performs bounded termination,
keeps failures failed, closes control/pipes/pidfds, checks namespace/descriptor
holders using process metadata only, and removes only identity-matched empty
owned cgroups and marked scratch. Unknown holder access, extra files, surviving
tasks or unproved identity refuse qualification; unrelated processes are never
signaled. The all-resource observation time must also fit the same 2500ms bound.
No process environment, messages, dictionaries, stack, conn, request/trailer/body
value, packet capture or dump contents is fetched. Compiler diagnostics retain
only byte counts/exit, while source/compiler/header/artifact identities are bound.

Each complete R14 row shares one 120s deadline across all four phases. Each R18
row shares one 120s deadline across all 34 faults; the 900s suite clock also
remains shared. Output allowance is shared across subcases as well: at most
1 MiB stdout and 1 MiB stderr for the row. Cleanup still runs after a deadline
failure and records the failure rather than abandoning resources or resetting
the clock. No root/limit/namespace/channel/counter/source fallback exists.

`run.py` defaults to read-only preflight. Actual runtime additionally requires
the matching Linux artifact/delegation and a closed fresh review receipt with:

```text
schema status harnessDigest profileDigest sourceDigest reviewer
faultEnumDigest checkpointSealDigest
```

Status must be
`independent-source-and-lifecycle-enum-review-approved-for-private-runtime`.
No such receipt or Linux artifact is authored here. Other R rows are forced
unavailable in this v3 driver; v1's seven candidate drivers remain preserved in
the checkpoint. The complete resource harness and all trailer/TLS/deployed gates
remain unfinished. No macOS BEAM/C/NIF artifact qualifies as a Linux artifact.

```text
python3 -B verification/stripe-webhook-linux-resource-harness/v3/checkpoint.py
python3 -B verification/stripe-webhook-linux-resource-harness/v3/author.py --attempt <new-number>
python3 -B verification/stripe-webhook-linux-resource-harness/v3/run.py --output <v3>/results/<new-owned-directory>
python3 -B verification/stripe-webhook-linux-resource-harness/v3/verify.py --live
```

The 21 repair host controls reproduce the old scheduler and holder failures using
the actual sealed v2 Python functions with mocked execution/metadata, then check
the corrected v3 expectations independently. They cover suite and backend
admission, preserved failures/unrun rows, nonleader-only namespace, pipe, socket
and namespace-FD holdings, inaccessible/changing inventories, identity replacement
and explicit exit races. No live `/proc` inventory or signal is performed.

The 31 inherited host tests exercise validators, all 34 fault/cleanup paths in an explicitly
labeled in-memory model, shared budgets/output allowance and mocked pidfd
membership fences. They are control tests, not Linux enforcement. The macOS
preflight exits 78 with zero runtime rows. No role/helper/listener/cgroup,
namespace, native instance, daemon, image, provider or cloud operation is started
by host authoring. Keep all Linux source-compile, ABI, namespace, lifecycle,
resource-counter, no-dump and disposal claims unverified until independent replay.
