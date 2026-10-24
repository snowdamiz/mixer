# Stripe resource harness v4 independent review

V4 directly repairs both findings from v3. One P2 gap remains in preservation
of partial descriptor observations, so this review requests changes and grants
no private runtime approval.

The reviewed v4 seal SHA-256 is
`309bbd3b0b4fb56ec9d3545204a5be24f1664fe5274ca873c610d18e77dc7f9e`,
the harness digest is
`64768849091ac048d91c2679303506a40b18633a5982cc8f25683ff7f2b117ec`,
and the root repair selection SHA-256 is
`35758c19f017c1bb6db5b5ccf60fee1b14fb3d9c30f68f6e86b0029d304e7158`.
The read-only live verifier passed all 50 sealed bindings and transitively
verified v1/v2/v3 and previous review packets unchanged. The fault enum retains
digest `3fea63bd9a41a3e91b8eb7922f87d52711c7d61b93c524d12c7bfaf6789b23e2`.

**V4-F1, P2: retain successfully read descriptor references when a later entry
fails or the task exits.**
[proc_inventory.py:79](/Users/andreyyurlov/Documents/dev/mixer/verification/stripe-webhook-linux-resource-harness/v4/proc_inventory.py:79)
buffers decoded `readlink` results in a local list. `Inventory.task` forwards
those references to its observer only after the entire descriptor scan returns
at lines 171–172. If a later entry raises, earlier successful owned-reference
reads disappear from partial evidence.

The independent actual-adapter/session chain reads synthetic FD 7 successfully
as owned `socket:[999]`, then receives `PermissionError` at FD 8. The inventory
refuses qualification, but the immutable cleanup attempt records both partial
`observedCounts.socketHolders=0` and `observedReferenceCounts.socketHolders=0`.
A later successful disposal preserves those incorrect historical zero counts.
In the second reproduction, FD 8 raises `FileNotFoundError` and TID 101's exit is
explicitly proved. Final zero holders is valid after that exit, but the returned
historical `observed_counts` still loses the earlier known socket reference.

The selected requirement covers available partial observations and references
surviving errors or exits. Preserve each sanitized successful descriptor read
at read time through a fixed internal observation hook, or carry bounded
immutable partial observations when a subsequent read fails. Keep the existing
final-zero qualification and explicit-exit rules. This remedy needs no arbitrary
callback, FD, path, HTTP, signal, or command authority.

The direct v3 corrections are confirmed separately:

- `pid_for_children` is mandatory for each observed TID and matched only against
  known owned PID namespace IDs. Missing, unreadable, invalid, changing or
  ambiguous metadata refuses zero except through the existing proved-exit path.
  The actual old adapter reproduces its missing-reference defect; the v4 adapter
  detects the same owned reference and rejects its numeric cleanup proof. This
  preserves the launcher's mount/net/pid/ipc/uts scope and the lifetime semantics
  documented in [namespaces(7)](https://man7.org/linux/man-pages/man7/namespaces.7.html)
  and [pid_namespaces(7)](https://man7.org/linux/man-pages/man7/pid_namespaces.7.html).
- Cleanup calls now append canonical immutable byte records before returning
  or raising. Actual positive-to-zero retries retain both attempts, sticky first
  counts and failure, original TERM origin, closed admission and detached receipt
  views. Idempotent calls record no fresh holder observation. The old actual
  session reproduces its overwritten evidence; the v4 actual session preserves
  it and refuses both later phase and fault-session admission after physical
  cleanup. Producer controls also verify complete row serialization.

The remaining finding concerns observations inside a descriptor scan that does
not return. Complete descriptor-table observations, immediate namespace
observations, unknown failures and the canonical records themselves are retained
by the reviewed paths. Missing child metadata and live permission errors remain
fail-closed; no false runtime pass was produced by these controls.

All four R14 source contracts remain intact: idle listener with no owner/capture,
an original owner blocked on incomplete H1 body, an original suspended H2 owner
with actual queued messages and bounded DATA/PING traffic, and an original
backpressured response owner with exact synthetic capture, stable progress for
at least 200 ms and positive TCP queue. Gate close still precedes one actual
owned PID2 pidfd TERM; the trap checks original live owners and armed phase and
requires positive bounded callback completion. C launcher, NIF, role and pinned
signal-authority bytes are unchanged.

All 34 boundary intents retain their actual action, selected fault point and
independent cleanup path; the complete current mapping is in
[enum-review.json](/Users/andreyyurlov/Documents/dev/mixer/verification/stripe-resource-harness-v4-independent-review/enum-review.json).
The 2000 ms grace, 2500 ms disposal deadline, shared 120 s row and 900 s suite
deadlines, shared output allowances, resource ceilings, FD3 SEQPACKET grammar,
ancillary rejection/right closure, creator-only SO_PEERCRED interpretation and
post-exec no-dump contract are unchanged. Source reachability remains conditional
on a valid future Linux artifact and environment.

All 66 producer pure/model/mock controls passed once independently. Four
additional independent controls passed: two confirm direct repairs and two
reproduce V4-F1 through the actual adapter, inventory and session paths with
low-level OS authority mocked. The prior independent finite syscall fixture is
reused by immutable binding. The sealed macOS preflight was inspected: exit 78,
18 unavailable, zero runtime rows; it was not rerun.

No C/NIF/BEAM compiler, Linux runtime, live `/proc` inventory, signal, provider,
cloud, container, daemon, native/device/physical tool, Git mutation or root
tracker edit was used. All original producer and review bytes were preserved.
All 30 runtime matrix rows and GA remain pending. Root owns future selection;
preserve v4 and repair the narrow observation handoff in a new immutable version.

The [receipt](/Users/andreyyurlov/Documents/dev/mixer/verification/stripe-resource-harness-v4-independent-review/receipt.json)
binds exact source, commands, tools, outputs, direct repair status, remaining
finding and limitations.
