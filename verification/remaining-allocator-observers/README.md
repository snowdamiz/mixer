# Remaining allocator observers

The release VM job `120548022868` on `d6505ac` failed the guest payload occupancy assertion: expected `(16, 8388608, 8388608)`, observed `(20, 8389508, 8389508)`. `original/ci-vm.log` preserves the complete hosted log. The actual hosted allocation stack and thread remain unattributed.

The guest, native FFI and streaming validation probes still used process-global activity/fault gates and process-global live-byte accounting. An isolated single Rust test does not isolate it from the process's harness threads. `reproduce_original.py` demonstrates two independent observer defects using an immutable `020f909f2a32553b79ba7068a1798c85d97426b4` export and the exact preserved guest test assertions:

- A synchronized worker makes three transient 1-byte requests and one retained 900-byte request after the guest occupancy baseline. The existing assertion fails with exactly `(20, 8389508, 8389508)` in debug and release. This deliberately synthetic stack reproduces the observed delta; it does not identify the hosted stack.
- A synchronized worker requests 900 bytes after fault ordinal 1 is armed. That background request is refused, consuming the global fault. The intended guest allocation succeeds, and its existing `unwrap_err()` fails in debug and release.

Original uninstrumented debug/release baselines pass all three tests. The reproduction overlays add only the worker and its synchronization at the selected observation boundary; product code, fixtures, original allocation arguments and original assertions remain intact. Sources, complete snapshots, file manifests, tools, commands and log identities are retained in `original/` and `original-replay-receipt.json`.

The repair changes three test files and adds `vm/tests/common/legacy_allocation_observer.rs`. The already-reviewed `common/allocation_observer.rs` remains byte-identical. Its bounded pointer ledger accounts for exact requested bytes throughout each test's ownership lifetime, including preparation outside a measurement interval and destruction on another thread. Failed reallocations retain ownership; successful cross-thread reallocations transfer it by pointer. Ledger capacity exhaustion aborts. No allocator sizes, alignments, product behavior or source fixtures change.

The adapter supplies thread-local activity, failure ordinal, failure size, source size and allocation cancellation gates. It counts each attempted lane request once, including refusals, while delegating successful allocator operations and all pointer bookkeeping to the existing observer. Measurement guards borrow the lane and retain the existing non-Send operation guard; scope exit disarms faults and gates. The adapter's retained cancellation token and background worker are constructed before lane ownership, and interval token clones allocate no memory. Ownership starts before the original fixtures and lasts through their later destruction. This remains a single synchronous test owner per executable; future product allocation workers require explicit ownership on the actual allocation thread.

The stream test still allocates and validates on its test thread. Its intentional helper thread waits for that allocation boundary and cancels; the helper never acquires allocation ownership or consumes a fault ordinal. Source/metadata/body cancellation ordinals `[1, 2, 5, calls]` remain unchanged. The guest's platform-specific 1016-byte Shared Arc child still aborts with allocation failure.

The adapter checks background allocation/zeroed allocation/reallocation isolation from foreground calls, live bytes, peak, largest request, source hits and fault ordinal 1. It also checks RAII fault disarming. The existing observer's own checks continue covering cross-thread owned cleanup/reallocation, failed-reallocation retention, deterministic address reuse and cancellation disarming. Probe calls use an opaque `GlobalAlloc` trait reference so optimized builds execute them.

`receipt.json` binds the immutable foundation plus exactly four named test overlays, complete snapshot, before/after source digest, tools, command logs and hashes. All checks pass:

- Debug and release with normal harness scheduling.
- Debug and release with `MIXER_ALLOCATOR_NOISE=1`; an unrelated worker alternates a real held 900-byte allocation/free after each baseline while the lane's fault gate is armed, retaining the changed background lifetime through the original cleanup assertions.
- Targeted Clippy with warnings denied.

`audit.py` confirms all 69 original assertions (guest 24, FFI 25, stream 20) remain unchanged and all 17 printed measurement lines exactly match the uninstrumented original baselines in all four repaired runs. Guest occupancy remains `(16, 8388608, 8388608)`, refusal remains `(2, 36, 36)`, native refusal remains `(1, 0, 0, 1024)`, all 12 stream fault ordinals fail closed, and all four cancellation gates return no proof. Maximum observed pointer ledger use is 59 FFI, 26 stream, and 216/218 guest slots of 4096. `audit-receipt.json` contains the complete observations and audit results.

`intermediate-adapter-lifetime-probe/` preserves a discarded selfcheck refinement. Its additional live/peak assertions initially raced the new worker's startup bookkeeping before a ready handshake; assertion formatting then encountered the armed first-allocation fault and aborted. The final adapter waits for worker readiness before establishing that baseline, and holds the worker lifetime through the assertions. This intermediate attempt is instrumentation debugging, not passing product evidence.

Reproduce with `python3 verification/remaining-allocator-observers/reproduce_original.py`, `python3 verification/remaining-allocator-observers/run_checks.py`, then `python3 verification/remaining-allocator-observers/audit.py`. The scripts use private exports and do not rewrite live VM source.

This evidence qualifies host test instrumentation only. It does not provide physical iOS/Android, cross-target compiler, signing, immutable published-package, customer, operational, release or GA evidence. Phones were not used. No commits, pushes, new dependencies or product edits were performed by this lane. Root coordinates integration and repository CI.
