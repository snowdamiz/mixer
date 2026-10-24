# Independent review of private Swift bulk memory

The sealed candidate is suitable for root integration as a bounded private host
slice. No blocking candidate defect was found. Root integration and acceptance
remain separate. This review makes no growth, full Swift, Ready/public, native,
phone, G08, release or GA claim.

The reviewed bytes are the 125-file closure
`e5050427a9653019e429bd6cb050133e89617d9a40c9896e0d684f12aa7c8626`,
against accepted 123-file input
`17f9ea5b93fbc0b5bd51df8484e30e0cbe420eac646730da7d330c4b4ecde9ff`.
The host checkout was `615a05dc14655dace87c2ff561a610bef4526621`. The binding
product plan, AGENTS, private contract and implementation evidence were read.
All compilation and execution occurred in separately extracted review scratch;
no live VM, tracker, other lane, native tool, dependency, commit or push changed.

## Code and ownership findings

Exactly nine source paths differ, including two new files. The original Frozen
bulk/copy/fill bodies and MemorySize push expression are shared by literal macro
expansion. Fresh compiler expansion reproduces all 39 Frozen method hashes;
all 14 containing owner declarations remain exact. The old memory algorithm
bodies differ only in the coordinated visibility tokens, and their complete
4,800-position accounting suffix is byte-identical. The other changes are the
new private module, its tests and checked additive envelope formulas/assertions.

Copy pops length, source, destination through the accepted typed and live-accounted
helper after active/frame/floor/type/page checks. It validates source and destination
ranges before charging or indexing. u32 conversion zero-extends all three I32
operands. Fill uses the low byte. Checked ranges admit zero length at the exact
memory end and reject an address beyond it. The original bulk boundary charges
ceil(length/64) fuel and length work; the three pops retain their own work. A later
work denial keeps fuel and the completed pop prefix. Zero length still traverses
fuel/work checks, with no chunk check.

Backward chunks when destination exceeds source and forward chunks otherwise
preserve memmove semantics, including equal addresses. The control check precedes
every at-most-4,096-byte effect. Cancellation keeps the completed suffix or prefix
and the full prior bulk debit. There is no final extra check after the last chunk.
Independent byte-oracle tests cover unaligned overlap, equal ranges, chunk edges
and end-aligned cancellation effects.

The actual pinned caller uses the retained frame pin and cache view, copies only
instruction/function scalars and ends the view before effects. It selects only
Copy/Fill/Size, sets the actual cursor, debits one instruction/fuel credit and one
work credit, then checked-advances the actual PC once. The helper adds neither
instruction count nor PC movement. Original live agreement, capacities and the
memory page count are checked through the original owners; MemorySize uses the
accepted push helper and actual live predebit. Warm helper and caller probes show
zero synchronous allocation attempts, unchanged memory pointer/capacity, pins
and reservation observations.

Both entry paths reject an occupied actual `FrameOperationStorage.entry` before
fetch/debit/PC/operand/memory effects, preserve its value and request drain. Outer
Ok means a vacant slot received the actual inner outcome; consumers must inspect
that outcome. An inner error requests terminal drain, success is taken before
reuse, and failure remains for fixed completion. Actual post-pop removal failure
uses the accepted debt wrapper; the review does not assume successful live deltas
on error. Original deepest-first retirement, retained failed-release pins,
explicit cleanup retry, sticky first failure and WASI attribution remain intact.
No alternate owner, slot, ticket or cleanup authority was introduced.

The source patch has exactly two added whitespace-only lines, patch lines 164
and 165. Root may normalize those separately during integration and bind the
revised integrated closure; this review continues to identify the exact sealed
candidate.

## Fresh and retained evidence

Fresh sealed-source executions run BM01–BM16 exactly once in each Swift-only/all
Debug/Release configuration: 64 successful selections. Three independent review
fixtures run in those same four configurations: 12 successful selections. They
use the real original owners and memory, with 18/3/8 fixture owners respectively,
one counted attempt per fixture, 584 actual pages, at most three frames and the
original 64-attempt bound. Filters, test identities, allocation results, outputs,
executable hashes, tool versions and source manifests are retained.

Fresh compiler MIR is reproduced in Swift-only/all-feature production/unit
configurations. All 4,324 new fields and every canonical part of the 4,800 old
fields match. A separate raw fn/promoted-const enumeration confirms the standalone
`bulk_memory_pinned_step::promoted[0]` and the actual preflight closure promotion;
actual test functions/promotions supply no production credit. Exactly 1,672 old
unit rows change only `mirFunction` by adding the full containing-module prefix.
Every field, type, alias, literal, position, binding and count remains identical.
The review accepts only that exact prefix delta, not general name normalization.

Fresh all-feature Release baseline/candidate production/unit layout probes match
the corresponding four sealed probes. Independent raw replay also reconstructs
all 16 sealed layout outputs. Each field has its actual aligned interval within
its containing struct; no interval reuses an earlier field's bytes. Actual typed
unit `()` places remain separately named at measured zero size and supply no
credit for another object. Fresh containing padding is included, including four
production active bytes. Original owners, offsets, accepted memory components,
construction bounds and fixed 128/256 MiB State/Combined limits remain exact.
The unchanged control source retains the authoritative 86-ticket maximum.

| Complete aarch64 host logical bound | Production | Unit |
| --- | ---: | ---: |
| Fresh bulk active addition | 642,456 | 1,206,544 |
| Fresh bulk permanent addition | 121,856 | 121,856 |
| Complete execution header | 1,758,216 | 2,652,896 |
| Complete frame-operation envelope | 3,478,968 | 6,299,432 |
| Preserved construction envelope | 1,069,144 | 1,071,904 |

These are conservative simultaneous named-object accounting bounds. They do not
measure compiler stack, allocator overhead, RSS or optimizer temporaries.

The producer's exact sealed packet was replayed with `--live-baseline`. The
remaining 248 prior execution selections, 64 Frozen baseline/candidate runtime
observation pairs, 64 Frozen integration selections, eight library checks and CI
Clippy are reused from that source-bound packet, not claimed as fresh review
executions. The Frozen runtime fixture source and raw paired observations were
inspected; fresh identical expanded methods independently corroborate parity.
Broad prior suites were not repeated without a specific concern.

Seven review harness failures are retained: an invalid failure-kind spelling in
a new review test, three MIR enumeration/path assumptions, an overstrict
zero-sized-type assertion, a Python token-spacing error and an overstrict
field-sum-equals-container assertion that omitted fresh padding. Their source,
commands/outputs or exact failure records remain in the packet. They are excluded
from successful evidence. None required a candidate change.

Rust/Cargo are 1.99.0 on aarch64 Apple Darwin. Review scratch was checked for open
files and removed after evidence collection; other projects and native instances
were untouched. The read-only checker is:

```text
python3 -B verification/swift-bulk-memory-review/verify.py
```

Growth, host imports, full dispatch/calls, Ready/public invocation, the full Swift
target, native joins, separate-repository immutable published FieldLog, final
physical phones, signing/store/customer/operational gates and GA remain pending.
The preserved absent-cursor Cleanup diagnostic keeps G08 open. Host tests supply
no iOS/Android, simulator/emulator, physical-phone, UI or release qualification.
