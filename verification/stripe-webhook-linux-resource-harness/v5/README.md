# Private resource harness v5: preserve partial descriptor observations

This source candidate repairs V4-F1 under the root's
`v4-partial-descriptor-repair-selection.json`, SHA-256
`92fb6567eb8904164637274b868efb52dad4bbaf1f99c3e372bf07076df2bed0`.
It has **no Linux compilation or runtime evidence**. Focused independent review,
all 30 runtime matrix rows and GA remain pending. Every prior producer/review
byte is preserved. `checkpoint.py` checks v1's archive and v1/v2/v3/v4 seals plus
completed independent reviews. The new source digest requires a fresh review;
no prior version's runtime-review receipt can authorize this source.

The actual `ProcMetadata.descriptors` adapter previously accumulated all FD link
reads before returning them. A later PermissionError or ENOENT discarded an
already known owned socket/pipe reference. It now yields each sanitized numeric
read to one fixed internal `Inventory.descriptors` consumer before reading the
next entry. The consumer pins the FD-directory identity before enumeration and
records each yielded reference immediately, before another read or clock check.
It still checks the original deadline after that observation and before the next
read. This retains evidence if a read crosses the deadline; it does not qualify
a late scan. There is no external callback or selectable path, FD or command.

The stream remains inside the adapter's `scandir` context and the consumer closes
it in `finally`, including consumer-side rejection. It separately accumulates a
sanitized view for the existing duplicate, per-TID double-read and complete
two-pass checks. Known descriptor kinds with malformed numeric metadata refuse
qualification. Ordinary file targets are discarded immediately; raw targets,
private process contents and exception messages never enter a receipt.

A later read error carries the available numeric partial observation through the
existing immutable `InventoryUnavailable` handoff and actual `Session.cleanup`.
An explicitly proved TID exit may still yield final zero, while the earlier owned
reference remains in the separate historical reference counts. No missing/error
metadata becomes zero without the existing explicit exit proof. Missing
`pid_for_children`, directory identity changes, changing inventories, unshared
FD tables and all existing deadline checks retain the v4 rules.

The actual backend/Session, lifecycle, C launcher, NIF, role and pinned signal
sources are byte-identical to v4. Each cleanup attempt still freezes its own
canonical byte record before retry, with actual/partial/unknown counts, causal
timing and a finite failure reason. First available counts and first failure
remain sticky. A subsequent zero disposal records new physical proof without
replacing the partial positive observation or reopening admission. Receipt views
remain detached. The suite/backend cleanup barrier, four R14 phases, 34 R18
boundaries, FD/control grammar, all resource/output limits and original TERM/
row/suite deadlines are unchanged.

The 16 new host controls reproduce both sealed-v4 evidence losses using its
actual adapter and test the repaired actual adapter through low-level OS mocks.
Actual Session controls cover PermissionError, ENOENT with proved exit, live-TID
ENOENT, malformed link metadata, changing descriptor views, duplicate/malformed
directory entries, partial-positive-to-zero retries, sticky failure/admission,
detached immutable history, ordinary target sanitization and distinct FD
references. The deadline control retains a successful read before a subsequent
clock refusal and proves the modeled iterator/handles close. All 66 inherited
controls remain included. These 82 host controls use no live `/proc`, signals,
compiler, helper/role, daemon/container, provider, native instance, phone, Git or
root tracker operation. Destructive disposal is mocked; no Linux enforcement is
claimed.

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
unavailable in this v5 driver; v1's seven candidate drivers remain preserved in
the checkpoint. The complete resource harness and all trailer/TLS/deployed gates
remain unfinished. No macOS BEAM/C/NIF artifact qualifies as a Linux artifact.

```text
python3 -B verification/stripe-webhook-linux-resource-harness/v5/checkpoint.py
python3 -B verification/stripe-webhook-linux-resource-harness/v5/author.py --attempt <new-number>
python3 -B verification/stripe-webhook-linux-resource-harness/v5/run.py --output <v5>/results/<new-owned-directory>
python3 -B verification/stripe-webhook-linux-resource-harness/v5/verify.py --live
```

The 66 inherited controls additionally cover the old scheduler/leader-only
failures, admission barriers, per-TID metadata models, all finite lifecycle
paths, shared budgets/output allowance, mocked pidfd fences and immutable
bindings. These are host controls, not Linux enforcement. The macOS preflight
exits 78 with all 18 rows unavailable and zero runtime rows. Keep every Linux
compile/ABI/namespace/lifecycle/counter/no-dump/disposal claim unverified until
independent review and root-selected Linux execution.
