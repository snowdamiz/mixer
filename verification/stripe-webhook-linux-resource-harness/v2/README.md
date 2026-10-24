# Private resource harness v2: R14/R18 candidate

This version adds source implementations for the four selected R14 phases and
34 finite R18 fault boundaries. It has **no Linux compilation or execution
evidence**, no runtime acceptance, and no GA acceptance. All 30 matrix rows stay
pending. It adds no production route, provider, deployment or dependency.

The immutable v1 checkpoint remains byte unchanged. `checkpoint.py` checks its
98 original file bindings and the 99 regular files in `../checkpoints/v1.tar`,
whose extra member is the original seal. Later versioned files are deliberately
outside that checkpoint. The legacy recursive v1 verifier sees later files as
additions; use the explicit checkpoint verifier for the frozen v1 snapshot.

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
unavailable in this v2 driver; v1's seven candidate drivers remain preserved in
the checkpoint. The complete resource harness and all trailer/TLS/deployed gates
remain unfinished. No macOS BEAM/C/NIF artifact qualifies as a Linux artifact.

```text
python3 -B verification/stripe-webhook-linux-resource-harness/v2/checkpoint.py
python3 -B verification/stripe-webhook-linux-resource-harness/v2/test_host.py
python3 -B verification/stripe-webhook-linux-resource-harness/v2/run.py --output <v2>/results/<new-owned-directory>
python3 -B verification/stripe-webhook-linux-resource-harness/v2/verify.py --live
```

Host tests exercise validators, all 34 fault/cleanup paths in an explicitly
labeled in-memory model, shared budgets/output allowance and mocked pidfd
membership fences. They are control tests, not Linux enforcement. The macOS
preflight exits 78 with zero runtime rows. No role/helper/listener/cgroup,
namespace, native instance, daemon, image, provider or cloud operation is started
by host authoring. Keep all Linux source-compile, ABI, namespace, lifecycle,
resource-counter, no-dump and disposal claims unverified until independent replay.
