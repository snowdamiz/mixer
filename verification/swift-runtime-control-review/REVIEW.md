# Independent Swift runtime-control foundation review

Verdict: accept this private foundation slice. No unresolved actionable defect
was found in the final source below. This is independent review evidence, not
root acceptance, component integration, target-execution permission or release
qualification.

The owner identified and fixed one cleanup gap before the final source freeze:
`finish_owned_cleanup` refunded an enlarged construction ticket even when phase
storage could remain outside the consumed control. The final implementation
retains that whole charge and ticket and records `ConstructionBound` unless the
phase has explicitly dropped its storage and returned to the foundation floor.
Two independent probes exercise this through an externally live Vec and a
destructor unwind. Both pass in Debug and Release.

The final review binds revision `d6505acac44ca8de456abb7748a149bf8990b72a`
plus the exact dirty/new source captured in the receipt. The scoped source was
unchanged across qualification. The source manifest digest (SHA-256 of compact
sorted JSON of relative path to SHA-256) is
`f845e1e371ae57967ae7f702efcbf41a9b42902ee619f30680293c7aac810d96`.

| Input | SHA-256 |
| --- | --- |
| `vm/src/experimental_swift_reactor/control.rs` | `5211d729092d57badaeb7e95f1ddabaf9aba4574c8d966b8ebc525bee8249f10` |
| `vm/src/experimental_swift_reactor/control_tests.rs` | `82265afa3dedb361aaf27f3384c50153dcde57d8aa9fca2c250dcfd611c547a1` |
| `vm/src/execute.rs` | `7c161ef66965aa2b82a44ac1f2bc47b677fdd38647639c4708ab753bbd7a66c9` |
| `vm/src/experimental_swift_reactor/mod.rs` | `e64945889cd03285bbecfda5a8176807bce2f91e6a474139c7cdd115fe960099` |
| `vm/src/experimental_swift_reactor/allocation_tests.rs` | `e24115b413f336e568c4aa947e1d78cca235ef309dea09b39d20beb832feb16b` |
| accepted design | `59708209438de44811f0ba7efa941ca9c9778067159e94728031f5a44a9af07b` |
| root contract acceptance | `3122b4e859fc67c2645b06dcf977e1812b15e0188661c0e89c42cdc550dfff16` |
| owner final qualification receipt | `6440053c041cf4e2cfe024fbabbe10b7a632641936667945d67cee335e3095e2` |

Only this review directory was written. No product file was edited and no commit,
push, device, publication or service operation was performed. The retained
compressed disposable snapshot contains exact source copies plus one appended
`cfg(test)` module declaration and independently authored `probes.rs`. The
snapshot manifest identifies the instrumentation explicitly; the uninstrumented
input manifest binds the reviewed product.

Seven original adversarial probes pass in each of Debug and Release:

- A deterministic 4,000-operation independent reference model compares every
  category and combined current/peak, inline ticket counts and interleaved zero
  reservations/refunds; the entire operation interval allocates nothing.
- A panicking storage destructor interrupts both aggregate release and phase-end
  cleanup; no refund occurs before the destructor completes.
- Passing another owner's genuine adopted proof actually drops its payload but
  refunds neither wrong ledger. The original ledger retains orphan charges.
- Every effect seam returns the same first failure after terminalization,
  including zero-credit calls, exact-capacity checks, admission, construction
  growth and invalid WASI budget attempts. Cleanup still drains owned resources.
- Arbitrary maximal copied WASI observations do not affect admission, duplicate
  WASI counters, or become persistent accounting state.
- Earlier WASI deadline selection cannot reopen under later carried budgets;
  real expiry remains sticky and records the selected origin and overshoot.
- A live external 181-byte phase Vec prevents enlarged construction teardown from
  claiming zero reservations.

Each mode additionally passes the interpreter (35), frozen span execution (16),
function cache (9), and standalone WASI (9) integration tests with all features.
The default interpreter separately passes 35 tests in each mode. An external
crate's attempted access to `RuntimeControl` fails with the expected `E0603`
private-module diagnostic. Complete commands, outputs, tool versions, compiler
binary hashes, platform, source manifests and snapshot hashes are retained in
`2026-10-23-foundation/receipt.json` and its logs. This run used rustc/cargo 1.99.0
on `aarch64-apple-darwin`.

The first review attempt was preserved under
`2026-10-23-foundation-attempt-1/`: its probe fixture did not compile because the
review encoder expected `&str` while an import name is `&[u8]`. That review-only
type error was corrected. Product source and legacy regression results were
unchanged; the final receipt contains the successful source-bound rerun.

Code inspection and the owner's separately bound evidence cover all seventeen
budget dimensions, proof-consuming adoption, exact pre-allocation admission,
no new control allocations after proof/token acquisition, non-Clone owner-bound
tickets, seven disjoint reservation categories, checked cumulative counters,
sticky typed failure snapshots and cleanup accounting. The root helper adds a
feature-gated private cancellation layout measurement without changing stored
legacy owner fields. The current control has no public entry point and selects
no alternative route for a legacy constructor.

The construction allowance models named foundation wrappers and scratch. It is
not a compiler-stack, allocator-overhead, RSS or hard-realtime claim. Later
composition must enlarge the same reservation before creating its additional
objects and prove that cleanup receives all actual storage covered by each
aggregate ticket. Neither a caller passing unrelated storage to the generic
private release seam nor correct future caller ownership is proved by these
foundation tests.

No Swift cache, executor, accounted WASI constructor, initialization or corpus
invocation is composed here. No immutable 53,777,114-byte reactor was instantiated
or executed. WASI snapshots remain observations only; attaching exact active
context observations to future admission failures remains integration work.
No native ABI widening, physical iOS/Android receipt, immutable published FieldLog
consumer, signing/store/customer/operational/GA gate is claimed.
