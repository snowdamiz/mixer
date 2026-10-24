# Stripe resource harness v3 independent re-review

V3 requires changes before private runtime selection. The new suite/backend
admission latch corrects the scheduling behavior identified in v2, and the new
adapter detects nonleader namespace and unshared descriptor-table holders.
Two gaps remain: a Linux PID namespace lifetime reference is omitted, and a
successful cleanup retry erases the first failed holder observation.

This review binds v3 seal SHA-256
`567139b93da497f8cfce6ce5f34aa5029b357e6b9f28a80cc7d70d077461608f`,
harness digest
`c57c99a7743a29da0ffc2422cdacb21a79e672ef2ae9ca9a180b355aa4a4483f`,
fault enum digest
`3fea63bd9a41a3e91b8eb7922f87d52711c7d61b93c524d12c7bfaf6789b23e2`,
and root repair selection SHA-256
`c9559f73209ec01110f58299cdc5d10d72202975c45b036c79435871684a4b62`.
The read-only live verifier passed with 90 sealed bindings. V1's 98 bindings and
99-member archive, v2's 104 bindings, and the prior independent review seal were
also verified unchanged. No prior artifact was edited.

1. **V3-F1, P1: include `pid_for_children` in PID namespace holder proof.**
   [proc_inventory.py:14](/Users/andreyyurlov/Documents/dev/mixer/verification/stripe-webhook-linux-resource-harness/v3/proc_inventory.py:14)
   limits every TID's namespace observations to `pid`, `mnt`, `net`, `ipc` and
   `uts`; the loop at lines 109–117 therefore never examines
   `ns/pid_for_children`. Linux permits this reference to differ from `ns/pid`
   after `setns` or `unshare`, and explicitly identifies it as a reference that
   keeps a PID namespace alive with no member processes. See the lifetime and
   proc-interface descriptions in
   [namespaces(7)](https://man7.org/linux/man-pages/man7/namespaces.7.html) and
   [pid_namespaces(7)](https://man7.org/linux/man-pages/man7/pid_namespaces.7.html).
   The [Linux v6.18 implementation](https://github.com/torvalds/linux/blob/v6.18/kernel/pid_namespace.c#L401)
   retains this separate child-namespace reference in `nsproxy`.
   The actual `ProcMetadata` adapter, with only its OS calls mocked, reports all
   zero holders when nonleader TID 101 holds owned PID namespace 777 solely
   through `pid_for_children`; `validate_cleanup` accepts that proof. Include
   this relevant lifetime reference in the same identity/deadline/race checks,
   retaining the launcher's owned mount/net/pid/ipc/uts scope. An absent,
   unreadable or ambiguous `pid_for_children` must refuse a zero-holder proof;
   only an explicitly proved task exit can use the existing exit-race handling.
   No broader control or foreign-process signaling is needed.

2. **V3-F2, P2: retain the failed cleanup observation across retries.**
   [linux_backend.py:564](/Users/andreyyurlov/Documents/dev/mixer/verification/stripe-webhook-linux-resource-harness/v3/linux_backend.py:564)
   replaces `last_counts` on every attempt. A positive holder count causes
   `validate_cleanup` at line 575 to raise before any failure snapshot enters
   history or sticky failure metadata. If the mandatory retry then observes
   zero, lines 581–585 record only that successful cleanup. The independent
   reproduction observes an initial `namespaceHolders=1`, then zero in both
   final `last_counts` and the only retained history entry; `session.failed`
   remains false and `error_reason` remains `completed`. The backend's admission
   latch correctly stays closed, so this finding concerns lost observed evidence.
   Root's repair selection separately requires preservation of actual failed
   receipts. Preserve each sanitized failed attempt, its numeric observations
   and causal timing before retry; a later physical disposal must retain the
   original failure and the closed admission state.

Independent controls confirm that `schedule_rows` preserves the actual failed
R14 object, suppresses R18, and marks later rows unavailable/unrun with zero
launcher starts. Backend admission also refuses both a later phase and fault
session after a failed cleanup followed by a physically successful retry. The
admission mechanism is repaired; the full selected evidence-preservation
obligation remains open under V3-F2.

The new per-TID traversal, no-follow directory opens, inode/owner stamps, double
namespace/descriptor observations and two complete task inventories were
reviewed against source control flow. Independent tests exercise the actual
`ProcMetadata` adapter through mocked `os.open`, `stat`, `fstat`, `scandir`,
`readlink` and `close`, rather than substituting the producer's higher-level
metadata model. These tests confirm nonleader network-namespace, pipe, socket
and namespace-FD detection, plus refusal for inaccessible or changed views, with
all modeled handles closed. Producer controls also cover identity replacement,
new tasks, explicit exit races and the original deadline. Linux API inspection
found V3-F1 beyond those modeled controls. The
[CPython POSIX implementation](https://github.com/python/cpython/blob/v3.14.0/Modules/posixmodule.c)
also confirms that FD-based `scandir` duplicates the supplied descriptor and
rewinds its stream on close; a presumed repeated-directory-offset defect was
not reported. This is an API source reference, not a Linux runtime receipt.

The role, C launcher, NIF and signal-authority bytes match the already reviewed
v2 bytes exactly. The original four R14 fixtures remain fixed:

| Phase | Source obligation retained |
| --- | --- |
| `idle` | Actual listener and no active request owner or capture. |
| `h1_body` | Original admitted owner waiting on incomplete fixed-length body; no completed capture. |
| `h2_reader_frozen` | Original owner suspended, positive queued messages after bounded DATA/PING writes, no capture; rechecked at TERM. |
| `blocked_response` | Exact synthetic capture, original waiting owner, unchanged chunk progress for at least 200 ms and positive TCP send queue; rechecked at TERM. |

Gate-close observation still precedes exactly one actual owned PID2 pidfd TERM;
original owners and armed phase are checked at the trap, and positive bounded
callback completion is required by the phase validator. The 2000 ms grace and
2500 ms disposal clock retain the first actual TERM origin. All four phases
share 120 s, all 34 fault subcases share 120 s, and the suite retains its 900 s
deadline and shared output limits. All 34 source boundaries retain their
component, selected fault intent, actual action and independent cleanup path;
the updated complete mapping is in
[enum-review.json](/Users/andreyyurlov/Documents/dev/mixer/verification/stripe-resource-harness-v3-independent-review/enum-review.json).
Source reachability is conditional on a valid future Linux artifact and host.

FD3's fixed UNIX `SOCK_SEQPACKET` grammar, 256-byte payload bound, rejection of
all ancillary data with received-rights closure, creator-only interpretation of
`SO_PEERCRED`, post-exec dumpability readback, zero core/file-size limits and
piped-core-collector refusal are unchanged. No phase/fault, path, FD, PID,
callback, HTTP or command authority was added. The withdrawn NIF source-hash
concern remains withdrawn.

All 52 producer pure/model/mock controls passed once independently. Eight
additional independent controls passed; two confirm the remaining source
defects, while the others confirm corrected behavior. The sealed macOS
preflight was inspected: exit 78, 18 unavailable, zero runtime rows. It was not
rerun. No C/NIF/BEAM compilation, Linux/container/daemon/VM start or pull,
installation, live `/proc` inventory, signal, native/device/physical query,
provider/cloud operation, production publication, Git mutation or root tracker
edit occurred. All 30 runtime matrix rows, Linux behavior and GA remain pending.

The sealed
[receipt](/Users/andreyyurlov/Documents/dev/mixer/verification/stripe-resource-harness-v3-independent-review/receipt.json)
records exact bindings, commands, versions, outputs, repair status and limitations.
Preserve v3 and repair in a new immutable revision, then obtain independent
review of the changed source and focused controls. Root owns runtime selection.
