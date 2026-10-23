# Independent persistent-session review

One confirmed allocation-ceiling race in `ac9c855a360b3f7f0317d0a0dfb57c67dba51ed2` is resolved by `64123c509e861ddd522631b293eadebdaca11341`. No additional confirmed blocking finding was identified in the reviewed session lifecycle, shared FFI argument decoding, host memory transfer, panic containment or public pointer contract. This is scoped independent host evidence, not a general security audit, race-detector run, device receipt or full Swift qualification.

The original registry reused a Closing slot when `Weak::strong_count()` reached zero. Arc reaches zero before running the payload's destructors. The independent test starts sixteen one-page sessions, blocks the actual guest-memory deallocation of one closing session, verifies close has not returned, and attempts another creation while fifteen sessions remain live. The original code admits that seventeenth still-allocated instance (status0) instead of rejecting capacity (status3). The test releases its allocator gate and cleans every handle before asserting, so a stuck test or leaked handle is not the cause.

The identical independently authored test, SHA-256 `b400bd03338122e4ee0df1850c8923bfc2115c03f7c85e90dd5c68828ad6f94d`, fails as expected on the original commit in **debug and release**, then passes on the fixed commit in **debug and release**. Only the new integration-test file is added to each isolated Git archive; no production source is altered. The source archives, test identity, exact commands, tool versions, expected exit codes101/0 and captured output are recorded in the [original receipt](evidence/ac9c855a360b3f7f0317d0a0dfb57c67dba51ed2/receipt.json) and [fixed receipt](evidence/64123c509e861ddd522631b293eadebdaca11341/receipt.json).

The root implementation fix retains a registry-owned Arc in Closing, represents admitted operations as generation-bearing leases, moves a sole registry Arc into Reclaiming under the registry lock, drops the complete payload outside that lock, and only then increments/retires the generation and releases the slot. Reclaiming continues consuming capacity. A final lease drop or close drives reclamation; an old delayed reclaim rechecks generation and cannot affect a replacement. The test directly exercises the important interval between strong-count zero and completed deallocation.

Read-only review also checked:

- Handles remain process-local opaque identities, with checked slot selection, nonzero generation and permanent retirement before wrap. They are not authorization secrets.
- Invoke/read/write serialize through try_lock; cancellation and close do not wait for an active instance lock. Defined admitted-operation races are documented and do not promise rollback.
- Memory transfers check the full unsigned range, including empty operations, before copying; the 1MiB API transfer ceiling remains unchanged. No guest-memory pointer escapes.
- Caller buffers remain borrowed for the call; decoding owns the retained module. Existing unaligned C struct transfers, null/length checks and valid-buffer/non-overlap preconditions remain explicit.
- The extracted argument helper preserves legacy numeric encodings and bounds. Interpreter errors terminate retained state; malformed API encodings and transfer/busy errors leave it usable as documented.
- Mutex poison prevents session reuse after an internal panic. FFI catch_unwind still contains Rust panics; this does not make invalid foreign pointers safe.

Reproduce into unused, owned local outputs:

```sh
python3 -B compiler/experiments/profile-budget/session-review/reproduce.py --revision ac9c855a360b3f7f0317d0a0dfb57c67dba51ed2 --expect quota-race
python3 -B compiler/experiments/profile-budget/session-review/reproduce.py --revision 64123c509e861ddd522631b293eadebdaca11341 --expect pass
```

Execution was macOS arm64 with Rust1.99.0. Review agent selection was gpt-6.1-sol/xhigh, independent of the root agent's session implementation. The reviewer changed only experiment/test/evidence files in this directory; root owns the production fix and its own regression copy. No physical-device operation was attempted. The user's unplugged-device constraint leaves fixed-source device requalification deferred; earlier receipts remain tied to their original commits.
