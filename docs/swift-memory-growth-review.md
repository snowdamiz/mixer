# Independent private Swift memory growth review

**Disposition: no reproducible correctness or accounting defect found in the frozen candidate.** This review supports root selection of the private host-only development slice. Root integration and product/GA acceptance remain separate decisions. The binding scope remains `mixer-product-plan.md` section 10; this result does not establish full Swift execution, a public invocation route, native integration, FieldLog release qualification, or any external gate.

The bounded review was assigned to a fresh-context `gpt-6.1-sol` agent with `xhigh` reasoning. The reviewer wrote only this document, `verification/swift-memory-growth-review/`, and unique owned scratch. No live VM, producer evidence, tracker, Git, native, UI, simulator, emulator, or physical-device state was changed. No commit, push, publication, customer message, credential operation, or competitor source/dependency was used.

## Frozen identities and source review

The independently extracted 125-file baseline closure is `96c945a817c81be17fb526067d87cc667a21cdaf5a47be18179e10fe5ed8de0d`, corresponding to the supplied root baseline `a1f78d1e88d6e1e934a08cdb85ce90f87f6ff343`. The 127-file candidate closure is `56e47ffa2c74ea243c9ead371a5ebfdeb59e85c0f05555419d51c84483afabe3`; its archive is `543798d262476aeaa6708f0f9c45606ebaa5465ac15b7d0bf13a2dce19bc33b7`. Producer receipt `569159016118804e09499d028d2a7751c93199bacd5f4f989b0d25fa18ca95d8` and seal `3f3b3a32652c9e7be280843f821c18bc3545cd7ec30f67918d9998cfed56b65b` matched before review. `complete.diff` records all nine changed paths; there are no dependency, public API, controller, cache, or WASI changes.

The source audit followed the actual authority and storage paths:

- `prepare_growth` checks original owners and empty frame state before envelope admission, records that admission in the original cleanup state, and borrows the actual `buffers[3]` ticket beside the original phase. It adds no accepted-owner field.
- The caller's `SwiftGrowthStorage` contains the real `GrowthTransfer`, the uncommitted positive page delta, and sticky debt. The pinned caller publishes its sole outcome to `FrameOperationStorage.entry`. Occupied-entry rejection precedes fetch, counters, PC, operand, and memory effects.
- Preflight protects operand floors/type, exact memory length/capacity/page agreement, and the original S ticket. Declared/host/run maxima, unsigned overflow, zero, full new-plus-old work, and pinned fuel/PC prefixes retain the contract's ordering.
- Positive growth reserves full new storage beside old memory, debits only new pages, allocates exactly, zeros/copies in bounded chunks, and checks after final copy. Rollback destroys the actual new Vec before refund; it removes only its acquired page delta and preserves original memory/S.
- Commit moves actual N into S and actual S into O, converts the delta to committed pages, destroys the old allocation, then refunds O. Later result-push or O-refund failure cannot roll back committed memory/pages.
- N/O layout and the unchanged borrowed owner/count/category/combined predicates are checked before taking the ticket. The same exclusive control borrow then takes the original ticket and calls the unchanged refund through `drop_reserved_with_wasi((), ticket, same_wasi)`. Unit storage has no callback/destructor; no fallible or mutable boundary intervenes.
- Failed ticket prechecks retain their exact Option and charge. Unresolved page debt stays sticky. `GrowthCompletion::Retained` returns the exact phase, actual ticket borrow, transfer storage, fixed caller storage, and preparation wrapper; the admitted envelope remains until explicit cleanup succeeds. Original frame/pin cleanup remains responsible afterward.

## Independently executed evidence

All builds used fresh owned targets keyed by exact source closure, features, profile, production/unit mode, and MIR/runtime/layout/expansion context. No copied producer target or binary was reused. Command receipts retain argv, host/tool versions, source manifests and unchanged-source observation, full compressed outputs, Cargo artifacts, binary paths/hashes, and test lists where applicable. Source archives preserve every compiled overlay.

| Fresh reviewer evidence | Result |
| --- | --- |
| Exact frozen candidate, all-feature Debug growth selection | 20 tests passed |
| Independently authored adversarial tests, all-feature Debug and Release | 7 tests per profile, 14 passed selections; 11 finite cases and 13 owner fixtures per profile |
| Exact frozen candidate MIR, Swift/all-feature × production/unit | 4 fresh compilations; every schema position matched |
| Independent raw binding/alias enumeration | Exact typed binding and alias multisets, including standalone cleanup and promotions |
| Fresh paired layouts | 4 actual executions: baseline/candidate Swift Debug production and all-feature Release unit |
| Complete producer raw layout audit | All 16 configurations matched every serialized type/owner/new-type/new-owner/class/field/total; every interval, alignment, payload and padding byte checked |
| Fresh baseline/candidate compiler expansion | Complete Frozen impl and all 39 method hashes identical; 14 accepted owner declarations plus `GrowthTransfer`/`ExecutionParts` identical |
| Frozen packet read-only replay | Passed; producer's excluded contaminated/history runs were not promoted |

The new adversarial tests exercise N and O layout rejection with a real allocation destroyed before retained-ticket refund; retry under cancellation; missing/foreign original S rejection before envelope admission or allocator work; preservation of an operand-floor prefix during positive growth; actual nonempty transfer-Vec completion retention; page-admission denial with zero allocator calls; and all four consuming-refund owner/count/category/combined rejection predicates before take. Temporary ledger corruption/restoration exists only in the test overlay to probe predicate safety; it is not a product recovery path or debt repair. The direct allocator-boundary case deliberately isolates page admission, which the ordinary grow path also constrains through its effective maximum.

The fresh exact-source 20-test run additionally reproduces cancellation at zero/copy/final boundaries, actual deadline expiry and cancellation precedence, 767→768 full overlap, allocator/capacity denial, State/Combined denial, work/fuel/PC prefixes, occupied outcome, postcommit push failure, foreign N/O retention and retry, sticky debt, and retained-pin cleanup. Its all-feature test includes five finite Frozen recipes. The producer's sealed 78 four-configuration growth selections, 98 broad Release selections and 20 Frozen differential pairs remain bound supporting evidence; they are not counted as fresh reviewer executions.

## Accounting outcome

All **10,356** fresh positive fields match the actual candidate declaration and fresh MIR projections: 4,724 production positions, 4,824 additional unit positions, and 808 authored positions (202 objects × four roles). All **4,800** accepted memory and **4,324** accepted bulk positions remain exact, with only the documented qualification-spelling normalization for memory. Their accounting tails remain byte-identical.

| aarch64 logical named-object bound | Production bytes | Unit bytes |
| --- | ---: | ---: |
| Growth permanent addition | 316,376 | 559,472 |
| Growth active addition | 973,920 | 1,815,568 |
| Complete header | 2,074,592 | 3,212,368 |
| Complete frame envelope | 4,452,888 | 8,115,000 |

Every production class has zero padding; unit permanent padding is zero and unit active padding is exactly four bytes. Baseline/candidate accepted owner shapes and offsets match. Frozen remains 2,912 bytes; State remains 128 MiB, Combined 256 MiB, and the ticket maximum remains 86. These bounds measure conservative simultaneous logical named objects, not stack, allocator overhead, optimizer temporaries, RSS, or mobile performance.

## Limitations and retained failures

G08's absent-cursor cleanup diagnostic remains open. This review does not complete full dispatch/calls, host imports, Ready/public invocation, the full Swift payload, native joins, simulator/emulator joins, immutable published packages consumed by separate-repository FieldLog, physical phones, signing, store, customer, operational, or GA gates. Physical phones remain deferred; none was requested or attempted.

The review preserves and excludes its initial missing-rustc-PATH diagnostic, two draft adversarial harness failures, one inventory name assertion failure, and one ambiguous source-owner lookup failure. The drafts used an unsupported existing fault hook and incorrectly expected high-water reservation peaks to roll back. Final tests use isolated test-only hooks and assert current-ledger restoration while preserving actual peaks. Collector-only corrections and all failed source closures/outputs remain recorded in `harness-limitations.json`; none required a candidate code change.

Owned scratch is removed only after an open-holder check; `cleanup.json` records the result. The frozen review seal includes every packet file, including every nested command `receipt.json`, excluding only the exact root `seal.json`. `python3 -B verification/swift-memory-growth-review/verify.py` is read-only and performs no compilation, extraction, subprocess execution, native action, or source mutation.
