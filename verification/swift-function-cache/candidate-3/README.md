# Private Swift cache candidate 3

This adds the two remaining mandatory assertions while preserving sealed C1/C2:
actual cache-owner allocator exhaustion through the real constructor path, and
no-effect propagation after every current terminal kind. No target, guest,
executor, device, release or GA execution is claimed.

The owner test routes the same checked atomic increment to a thread-local private
counter under a cfg(test)-only RAII scope. It issues MAX-1 once, rejects MAX three
times through the real three-allocation constructor/partial-drain branch, checks
matching allocation/free bytes and zero final ledgers, and proves both normal
and panic restoration followed by successful production-counter construction.
The production NEXT_OWNER is never seeded or stored by this seam.

The sticky matrix explicitly latches each of all21 SwiftRunFailureKind values in
the actual RuntimeControl after a real cache entry/pin and AccountedWasi dispatch.
It repeats5 prepared phase.pin calls,5 full pin calls and5 prepare calls per kind,
covering existing-hit/new-miss/invalid-function requests. Exact first cause,
complete cache stats/decodes, authoritative usage except advancing native time,
WASI service counters, allocator effects and Planning/Scan/Build/Publication
steps remain unchanged. Honest terminal drain releases the live entry/pin once,
preserves distinct at_failure/after_cleanup snapshots, and finishes at zero.
These are terminal-latch propagation cases; natural origin tests remain separate
named evidence. Guest/WASI/executor-origin behavior is not inferred from latches.

`accounting-delta.md` and the complete measured map record construction +96 to
57224, with unchanged foundation16504 and other component/whole-slot allowances.
C2 exact-source phase acceptance is historical, not silently extended to C3.

Final collection reruns the complete feature/profile matrix,18 exact named tests
per profile with zero-selection rejection,9 explicit ignored references per
profile, product-library Clippy/fmt, exact original-engine legacy traces, and
native exports/headers. The first development collection was stopped by source
stability checking when the final Planning assertion was added; its artifacts
remain in qualification-attempt-1. It is not final qualification.

An additional exploratory all-tests/all-features Clippy command failed on
pre-existing test-only large-error/range/drop/style lints in cache, WASI and
unrelated guest-UI tests. Its complete output is preserved in
development-clippy-all-tests.log. It is not reported as passing. No unowned lane
was edited to clear those warnings. The final qualification records the required
product-library Clippy scopes separately.
