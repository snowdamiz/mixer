# Final Swift cleanup foundation allowance

The private executor layout prerequisite now has an explicit foundation allowance
for final cleanup. It covers named output references and authored operation and
return values after the execution header is refunded. This does not implement an
executor constructor, interpreter algorithm, initialization or invocation.

The independent inventory in
`verification/swift-executor-final-accounting-review/decision.json` identified
missing roles in the previous foundation. Its original control source and all
cache candidate3 receipts remain immutable historical evidence. The correction
is qualified separately in `verification/swift-final-boundary-accounting/`.

The original seven foundation classes remain unchanged: three proof, three
control and three adopted wrappers; four failure and four usage objects; six
ticket objects and six optional WASI observations. New private inventory types
describe complete refund, record and finish groups. They are never instantiated
and contain no runtime owner fields. The containing structs account all tags and
alignment. Whole array, IntoIter and Flatten objects are separate from the plain
ticket slots; their fields are not counted a second time as spare tickets.

| Whole final group | Measured arm64 bytes |
| --- | ---: |
| Refund, including nested fault and clock chain | 688 |
| Record cleanup and clock chain | 272 |
| Consume control, ticket iterators and clock chain | 864 |

The new allowance is the target-compiled maximum of those three whole groups.
The refund call and its result end before record cleanup. Record and the outcome
assignment end before control consumption. Both output references persist and
are present in every group. There is no switch inside a surviving parent helper,
reuse of owner padding, relabeling of diagnostics as references, or reliance on
last-use optimization. The whole-group maximum is a conservative sufficient
allowance for these authored roles, not a mathematical minimum or physical stack
measurement. Opaque standard-library internals and compiler-generated spill
storage remain outside this existing requested-memory accounting model.

The size formula is now an explicit `const` initializer. Runtime calls return its
precomputed checked Option; they create no formula array, iterator or fold. The
new row therefore does not require a recursively growing runtime formula model.
On the measured host, foundation admission increases from 16,504 to 17,368 bytes.
Existing owner layouts and reservation ownership semantics are unchanged. Cache
additional construction/operation/header envelopes retain their existing values;
their sum with the foundation increases by 864. Old conservative cache rows for
the prior formula are retained, without claiming to reuse them for new roles.

Actual adoption tests exercise the previous floor, one byte short of the new
floor and exact new admission. Cleanup tests exercise real AccountedWasi output,
successful and missing-header completion, refund underflow, a previous terminal
failure followed by invalid ownership, and finish-time construction, owner and
underflow faults. Rejected refunds retain their combined charge and ticket;
cleanup never invents room. First-failure details remain unchanged. Finish-time
invariants remain independent cleanup observations. Allocation checks require
zero new allocations and reallocations during these boundaries.

This appendix does not accept the runtime or its full target. Exact production
and unit layouts, feature/profile regressions, legacy tests and independent review
must bind the corrected source before root acceptance. Physical devices, signing,
store, immutable published FieldLog, performance and all GA gates remain open.
