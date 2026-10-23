# Experimental native capability sessions

The optional Rust feature `experimental-capability-native` exposes the bounded
capability guest through fifteen C functions in
[`mixer_vm_capability.h`](../vm/include/mixer_vm_capability.h). It depends on the
experimental guest and mailbox features. Default and guest-only builds do not
export these functions. The public legacy header, profile IDs, structures and
import admission remain unchanged. This is a development interface, with no
activation or release authority.

The implementation follows the separately reviewed
[native ownership design](capability-native-abi-proposal.md). Root matched the
frozen implementation, combined qualification and independent review in the
[integration receipt](../verification/capability-native-integration-2026-10-23.json).

## One bounded registry

Legacy and capability C sessions share the existing sixteen-slot registry.
Reservations, live sessions, closing sessions with outstanding native work, and
destructors in progress all count against the same ceiling. Handles include a
slot generation. Every operation checks the session family before mutating it;
one family cannot cancel or close the other.

A successful `take` of a Call retains an owner-bound dispatch lease in a fixed
eight-entry ledger and increments an outstanding native-work count. None,
too-small and Cancel results create no new obligation. Only the first successful
exit acknowledgement decrements that count. Delivery, cancellation, close and
dropping a ticket cannot substitute for exit. Acknowledged ledger entries do not
authorize stale operations: the underlying mailbox checks each token again.

Close invalidates ordinary access immediately and stops admission. Exit
acknowledgements may still use the retained closing generation. A caller that
never acknowledges actual cleanup retains capacity. A quarantined session also
remains counted, even if its outstanding count is zero.

Transient operation references are released under the registry mutex while the
registry retains its own reference. This synchronizes count and quarantine
changes with the last-reference check. Final instance destruction happens outside
the registry mutex while the slot remains `Reclaiming`; only completed destruction
permits generation advance and reuse. Registry critical sections never acquire
the guest, ledger or mailbox mutexes.

## Pointer and operation boundary

All new functions preflight every input and output range, including the report,
before writing anything. Required null pointers, address or length overflow,
oversized buffers and any writable overlap return status 3 with every output
unchanged. Read-only overlap and empty buffers are supported. Fixed structures
may be unaligned. After valid preflight, output structures are initialized without
reading their prior contents. Callers still own pointer validity and lifetime.

The supported layouts are LP64 arm64 and x86_64. The new limits, message and result
structures have sizes 32, 40 and 24 bytes, respectively, with alignment 8. Rust
compile-time assertions and the original C client check every field offset.
Unsupported layouts fail admission.

Validation uses the same full decoder and startup/wake checks as construction,
without creating instance memory or a mailbox owner. Construction reserves a
shared registry slot before validation and instantiation. Guest startup runs once
with effects disabled; enable follows successful startup. Guest turns, memory
copies and completion wakes use the owned interpreter and its existing limits.

Result kinds are meaningful only when the C status is zero. An existing terminal
result wins over a later post or deadline narrowing, including after exit while
the identity remains retained. Once consumed and released, that identity is
stale. An early exit without a terminal causes later post/narrowing to reject.
Remaining duration zero is expiry, never a fresh timeout.

Recoverable payload allocation refusal preserves request state for retry or
expiry. Contained unwind, poison and invariant failure latch quarantine. Closing
an unpoisoned mailbox can still succeed after quarantine; successful close means
the owner transition completed, not that exit occurred or capacity was released.
Standard-library allocations can still abort on out-of-memory, as documented by
the underlying guest/mailbox evidence.

## Integration boundary

The C layer copies bounded argument and result bytes. It performs no JSON decoding,
grant enforcement, HTTP or storage dispatch, Swift continuation scheduling or
automatic wake loop. Those operations belong to the planned strict Swift bridge.
A trusted bridge must preserve each handle/token/operation mapping, honor the
original enqueue deadline, and acknowledge actual native cleanup separately from
terminal delivery. Close must latch bridge admission before cancelling registered
work so a late returned Call cannot escape into new I/O.

Only one VM archive may be linked into a process. An experimental archive already
contains the legacy functions and the shared registry; co-linking a second default
archive is not a supported integration strategy.

## Scoped verification

The frozen implementation passes 91 default tests and 185 combined-feature tests
in each host build mode, plus nine explicitly invoked reference-test functions
per mode. Fourteen actual C smoke runs cover legacy and new entry points.
Independent public C tests add 48 take/close and 48 ack/close races per mode,
mixed sixteen-slot capacity checks, stale-token and alias/no-write cases.
The exact source, logs and tests are preserved in the
[implementation evidence](../vm/verification/capability-native/README.md) and
[independent review](../verification/capability-native-review/README.md).

iOS and Android arm64 Rust archives, C layout objects and linked C clients build;
they were not executed on devices. A repeated host debug build produced a different
archive hash. The source-bound build logs and exact independently tested archive
hashes are retained; bit-for-bit reproducibility is not claimed. Expanded Linux
native C CI is a separate subsequent check.

Physical phones remain disconnected. Host tests, C clients, cross-target
compilation and symbol/layout checks cannot qualify device behavior, complete
Swift guest execution, activation migration, FieldLog adoption or any GA gate.
