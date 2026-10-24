# Stripe resource harness v5 independent review

The focused v5 source and host-method review is approved with no remaining
actionable findings. V4-F1 is corrected: a successfully sanitized descriptor
observation reaches the fixed consumer before a later read, iterator step or
clock check can discard it. This is source/host-method readiness only. It grants
no Linux compilation, resource runtime, production, complete matrix or GA pass.

The review binds v5 seal SHA-256
`22e44e7b2a5d507e0fa2d6cd84aa1b835123d322d8b91baf7004b827490e8c85`,
harness digest
`9459d8fadeaaeda3f5c15971c7c3bce65bc71f87eca1d75dbe1d5c923b532b68`,
fault enum digest
`3fea63bd9a41a3e91b8eb7922f87d52711c7d61b93c524d12c7bfaf6789b23e2`,
and root repair selection SHA-256
`92fb6567eb8904164637274b868efb52dad4bbaf1f99c3e372bf07076df2bed0`.
The read-only live verifier passed all 55 sealed bindings and transitively
verified every preceding producer and review checkpoint unchanged.

[ProcMetadata.descriptors](/Users/andreyyurlov/Documents/dev/mixer/verification/stripe-webhook-linux-resource-harness/v5/proc_inventory.py:90)
yields each decoded numeric descriptor observation inside the live `scandir`
context. The sole fixed
[Inventory consumer](/Users/andreyyurlov/Documents/dev/mixer/verification/stripe-webhook-linux-resource-harness/v5/proc_inventory.py:129)
pins directory identity before starting the stream and calls `observe` at line
143 before the next clock check at line 144. It retains a separate sanitized
view for duplicate and two-pass checks, and closes the stream in `finally`.
Known-kind malformed metadata refuses qualification; raw ordinary file targets
and exception messages do not enter evidence. No external callback, path, FD,
HTTP, signal or command selector was introduced.

Independent actual-adapter/Session controls confirm:

- The sealed v4 adapter reproduces the lost partial socket observation; v5
  retains it before a later `PermissionError` or malformed descriptor value.
- A later iterator-step error and a duplicate rejected by the consumer retain
  the first yield and close modeled iterator/directory handles.
- When the clock expires immediately after a successful read, the reference
  is retained before refusal, and the next descriptor is not read. No late scan
  becomes qualified and the original deadline remains unchanged.
- An explicitly proved TID exit permits valid final physical zero while keeping
  historical socket-reference count one. The v4 adapter's historical count zero
  is reproduced separately.
- Actual cleanup attempts retain partial count one followed by physical zero,
  immutable first bytes, detached receipt views, sticky first failure and closed
  phase/fault admission. An idempotent attempt makes no fresh holder claim.

All 82 producer pure/model/mock controls passed once independently; all eight
additional independent controls passed. The producer suite additionally covers
row serialization, live-TID ENOENT refusal, changed views, malformed directory
entries, distinct FDs for one inode, ordinary-target removal, numeric bounds,
partial/unknown attempts, and the inherited lifecycle/cleanup barriers. The
independent tests use the previously sealed finite syscall fixture and keep
the actual adapter, inventory, generator consumer and Session code installed;
only OS authority and destructive disposal are mocked.

The prior mandatory per-TID `pid_for_children` rule remains restricted to known
owned PID namespace IDs, with missing/unreadable/ambiguous metadata refusing
zero except through proved-exit handling. Directory identity, per-TID double
reads, complete two-pass inventory and immutable cleanup attempt rules remain.
The backend, lifecycle, C launcher, NIF, role and pinned signal-authority bytes
are identical to v4; only the selected private descriptor handoff and binding
plumbing changed. The withdrawn NIF mismatch remains withdrawn.

The four R14 fixture obligations retain their source contracts: idle listener
with no owner/capture; original owner blocked on incomplete H1 body; original
suspended H2 owner with queued DATA and bounded PING traffic; original blocked
response owner with exact synthetic capture, stable progress for at least 200 ms
and positive TCP queue. Observed gate close still precedes one actual owned
PID2 pidfd TERM; the trap checks the original live owners/armed phase and requires
positive bounded callback completion. All 34 fault intents retain their action,
selected boundary and independent cleanup path, mapped in
[enum-review.json](/Users/andreyyurlov/Documents/dev/mixer/verification/stripe-resource-harness-v5-independent-review/enum-review.json).
These are source observations; actual Linux phase and fault reachability is
unverified.

The 2000 ms grace, 2500 ms disposal deadline, shared 120 s row and 900 s suite
deadlines, shared stdout/stderr allowances, resource ceilings, FD3 SEQPACKET
grammar, ancillary rejection/right closure, creator-only SO_PEERCRED handling
and post-exec no-dump contracts are unchanged.

The sealed macOS preflight was inspected: exit 78, 18 unavailable rows and zero
runtime rows; it was not rerun. No C/NIF/BEAM compiler, actual Linux/proc/
namespace/cgroup/signal operation, native/UI/device tool, provider/cloud,
container/daemon, Git mutation or old/root file edit occurred. All 30 runtime
matrix rows, Linux compilation/ABI and actual disposal behavior remain pending.

The [receipt](/Users/andreyyurlov/Documents/dev/mixer/verification/stripe-resource-harness-v5-independent-review/receipt.json)
binds exact commands, tools, source, outputs, repair checks and limitations.
No runtime authorization receipt is issued. Root owns any later selection of
Linux compilation or private execution and its separate evidence requirements.
