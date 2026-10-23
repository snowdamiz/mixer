# Allocation observer CI repair

The two allocation observers counted unrelated process allocations and armed allocation failure/cancellation globally. A deterministic independent worker reproduces both errors using the preserved original cache test: a held 900-byte allocation makes the existing constructor cleanup assertion fail (8095 versus 7195), and an allocation made after arming failure ordinal 1 consumes that fault on the worker, allowing the constructor to succeed. These are observer failures. The saved GitHub log does not identify the actual allocation or thread behind its 900-byte delta, so this evidence does not attribute that exact allocation stack.

`revision-comparison.json` confirms that `caaa005` and the green `5a5b395` have identical `vm/src` trees and identical cache allocation test source. The original cache observer source is also byte-identical in the validation baseline `e299f1a60eb06dc9405021fc49ced215eaa42336`.

The repair changes only `vm/tests/span_function_cache_allocations.rs`, `vm/tests/span_execution_allocations.rs`, and `vm/tests/common/allocation_observer.rs`. The original 30 cache and 23 execution assertions remain. Ownership begins at test entry, retaining proof/preparation allocations in cleanup baselines. Fault/cancellation intervals use separate thread-local state. A static 4096-slot pointer ledger retains exact requested sizes and follows owned allocations when another thread frees or reallocates them. Removal precedes `System.dealloc`; the ledger lock covers `System.realloc` and its bookkeeping to prevent address reuse from confusing allocation lifetimes. No allocation sizes, alignments, or product code are changed. Overflow aborts instead of silently dropping observations.

The helper checks failed-reallocation retention, owned cross-thread reallocation/deallocation, deterministic reused-address bookkeeping, RAII disarming, and background allocation/zeroed allocation/reallocation isolation from foreground faults, cancellation, calls and peaks. The probe uses an opaque `GlobalAlloc` trait call so optimized builds execute it; direct `std::alloc` probes had been elided in an intermediate release check. This change affects probes only.

`receipt.json` binds tool versions, commands, the immutable baseline revision, the exact three-file overlay digests, the complete tested VM snapshot, before/after source digests, and every command log. All checks pass:

- Debug baseline and `MIXER_ALLOCATOR_NOISE=1` targeted tests.
- Release baseline and `MIXER_ALLOCATOR_NOISE=1` targeted tests.
- Targeted Clippy with warnings denied.

Noise alternates a real independent 900-byte allocation/free after each operation baseline, while the foreground failure/cancellation gate is armed, and retains its changed lifetime through the existing cleanup assertions. Counts and requested peaks are identical across all four configurations: cache constructor/decode 2/3 allocations and 1248/4277 bytes; execution constructor/invoke 6/4 allocations and 462872/131357 bytes. Maximum ledger use is 17 cache slots and 37 execution slots.

Run `python3 verification/allocator-observer-ci-repair/run_checks.py` to rebuild the immutable baseline with the current three test files overlaid. Run `python3 verification/allocator-observer-ci-repair/reproduce_original.py live` or `fault` for the expected failing original tests; these scripts operate in private exports and do not rewrite the working tree. Each writes a source manifest and full logs. `original/` preserves the complete original test sources, instrumented reproductions, baseline VM archive, and original GitHub failure log/receipt.

`intermediate-policy-wip/` preserves an attempted current-tree matrix blocked by another lane's temporarily mismatched `Policy`/`Limits` signatures; it is a source-coordination failure, not observer or product evidence. `intermediate-release-probe/` preserves the discarded optimized probe attempt and its full snapshot. Neither is presented as a passing check.

This slice qualifies synchronous host allocation observations only. It makes no physical-device, cross-target compiler, signing, immutable published-package, release, or GA claim. Future product worker allocations would need explicit ownership attribution. Root must validate integration with concurrent product changes before publishing repository CI results. No commits, pushes, dependencies, devices, or production edits were performed by this lane.
