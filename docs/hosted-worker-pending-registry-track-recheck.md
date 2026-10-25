# Track boundary recheck and exhausted-version fence

This immutable derivative addresses the actual workerd/SQLite track race in
[the sealed correction review](../verification/hosted-worker-pending-registry-engine-correction-review/receipt.json).
It preserves the original engine, prior correction and both review packets.
Its predecessor is correction source digest
`ee330a270f6151dfff96ed561a8b654ca1cc753026d03583cea99aee4276d811`.
The review receipt SHA-256 is
`c1c53d5437854fb9fb0aa24fabd19cc5cb9053f4c40ca29393801da1abe4ce29`.
Root additionally authorized the bounded exhausted-version fence correction
below after an actual SQLite reproduction.

Only isolated `engine.ts` and `ledger.ts` change in production source. Public
wire bytes, private binding interfaces, schema, clock, provider, identity
helpers and registry dependency remain unchanged. Root owns live integration;
this packet adds no entry wiring, schedule, namespace, dependency, provider
capability, publication or restored authority.

## Pre-RPC boundary

The prior correction checked provider kind before asynchronous identity/hash
work, but the final pre-track check omitted that kind. A same-version restore
during `before_track` could replace Android's `cloudflare-linux` provider with
`external-macos`; track then quiesced the registry and cleared the local outbox
without a fence.

The derivative validates the snapshot's immutable binding digest outside SQL.
After every identity/hash/hook await, one synchronous ledger transaction checks
current full retained identity/receipt, immutable binding/resource, provider
kind against the trusted adapter's platform mapping, operation version, exact
outbox/terminal bytes, and independent fence/quarantine. Missing, regressed or
mismatched safety state fails closed and receives a permanent fence where
appropriate. Existing quarantine/fence remains closed. A same-version projection
rewrite is fenced; a legitimate newer local version leaves its latest outbox
for another bounded delivery.

The registry RPC is invoked immediately after the final valid transaction with
no intervening await. No SQL transaction spans a hash, hook, registry RPC or
provider call. There is still one attempt per snapshot and no retry loop.
A valid concurrent ACK may already have cleared the same outbox; it cancels only
the redundant start, without quarantining or lowering delivery metadata.

## ACK and return boundaries

`Ledger.acknowledge` now requires a synchronous validation callback. That callback
runs inside the existing metadata transaction before any acknowledged-version
or outbox-clear write. It rechecks the provider, identity/resource/receipt,
permanent terminal evidence, fence/quarantine and non-regressed history.
Metadata cannot be cleared based on a separately read stale row. Timeout,
unavailable, stale and conflict responses also recheck current local safety;
they confer no acknowledgement. After local sync yields, a final synchronous
check prevents returning success under a newly observed unsafe state.

A newer legitimate operation version or independent ACK-only progress can
advance while an old RPC waits. An exact old ACK may advance its delivery
watermark but never lower a newer watermark or erase a newer outbox. Higher
versions of identical permanent terminal evidence still replay idempotently.
Final effect/claim qualified-clock barriers and report acceptance checks remain
unchanged; delivery is never execution authority.

There is no distributed atomic transaction or cancellation claim. If the remote
terminal track committed before a later local restore/fence, its quiescent
state cannot be rolled back or reopened by this API. Tests explicitly observe
that committed remote state. The local operation instead retains its outbox,
records its permanent fence, declines the ACK-clear and prevents further
provider/claim/report work. A timeout can also leave the remote outcome unknown.
The retained local alarm and constructor recovery remain necessary; this does
not qualify deployed alarm delivery, namespace restore behavior, independent
fleet discovery after a restore, or GA operations.

## Exhausted operation versions

The new actual SQLite MAX control first reproduced a separate pre-existing
failure: at `state_version = "9223372036854775807"`, `Ledger.fence` inserted the
independent fence and then tried to increment the operation version to set its
row quarantine flag. The exhausted save threw and rolled back the entire
transaction, including the permanent fence. That failing selected-case run is
preserved at `runs/20261025T051959774Z` in this packet.

The bounded correction always retains the independent fence. Below MAX, the
normal quarantine transition still increments exactly once and writes its
latest outbox; a repeated fence is idempotent. At MAX, the operation row,
version, row quarantine flag and outbox are immutable. The separate fence alone
remains authoritative to every new-effect, claim, report and known-recovery
check. No limit is increased, reset, wrapped or bypassed, and no unversioned
operation mutation is introduced. Valid terminal ACK metadata and duplicate
track can still complete at MAX without an operation-version increment.
A restored correct provider and a process restart cannot clear the fence.

## Observed evidence

Run:

```sh
node verification/hosted-worker-pending-registry-track-recheck/candidate/check.mjs
```

The final run passed **81/81 actual workerd/SQLite groups**: the prior 54
assertions/inputs reran unchanged, plus 27 focused track/fence controls. The
final run is `runs/20261025T052136773Z` under this packet, with source digest
`f4290d7ab0ece9eb2546d9b6125054d6cbbd4d9ab572d418679fbc41e748b799`.
The earlier 75-group success and the one-case MAX rollback failure remain
immutable evidence. The final runner separates the prior54 and focused counts,
binds exact source and tool versions, and captures complete command output,
exit state and stdout/stderr EOF.

Focused controls include provider/missing-provider, fence/quarantine,
identity/receipt/resource, missing-row and projection mutations before RPC;
provider/fence/quarantine/receipt changes after a committed track;
positive same-version and newer-terminal ACK progress; timeout without a
cancellation claim; and new-launch prevention. MAX controls cover positive and
duplicate terminal ACKs, aborted pre-track and committed post-track fences,
correct-provider restore plus restart persistence, independent fence checks
with row quarantine still zero, and normal-version fence idempotence.

The final run records seven exact-owned SIGKILL controls, 81 disposed owned
storage environments and absence of all observed owned workerd PIDs. Existing
executable/direct-parent ownership checks preserve other projects' processes.
The clock, provider and hostile restore controls remain explicitly excluded
finite fixtures; registry calls use the actual fixed DO binding and SQLite.
The registry remains bound to
`99d8a5dc4e2e9b8875c262ae44d2f1307d3107d3bc48c4300e981f68ec12b428`;
no audit module is imported or modified. Root separately owns the corrected
audit source and live component integration.

The top-level receipt, production delta manifest, scoped patch and input
manifest are review artifacts relative to the frozen correction. The live
71-group controller and 20-process-control suites were not rerun here. Public
and scheduled entry integration, production qualified time/providers,
native/device evidence, deployed operational qualification and GA acceptance
remain outside this packet. This lane changed no live/root/Git files and sent
no customer messages.
