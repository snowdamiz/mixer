# Complete Swift reactor validation stage

The canonical implementation-lane receipt is
[`2026-10-23-final-v2/receipt.json`](2026-10-23-final-v2/receipt.json).
It records complete validation under the fixed experimental policy and exact
structural ABI. It records **no instantiation or target execution**, package
admission, signature verification, publication, device qualification or GA credit.
The source revision is `8296296cd4489dc49914cf794002a3b9b9d866c3` plus the
individually hashed source capture. Its source-tree digest is
`75ab612da891fba4cc267f4e00d0531bb13c9081f6bddd57b4cc20584f312e42`.

| Observation | Final measured value |
| --- | ---: |
| Immutable target length / runner Vec capacity | 53,777,114 / 53,777,114 bytes |
| Target SHA-256 | `24d85729a659ff3e5fc6f0517709afbb68b371a41829e90785dabd48e0620994` |
| Fully type-validated bodies / defined bodies | 79,832 / 79,832 |
| Imports / total functions | 34 / 79,866 |
| Instructions | 6,505,659 |
| Types / aggregate signature parameters | 493 / 4,105 |
| Globals / data segments / element segments | 5,273 / 20 / 1 |
| Maximum parameters plus locals / operands / controls | 181 / 67 / 379 |
| Retained source reservation | 53,777,114 bytes |
| Retained / peak metadata reservation | 1,037,096 / 1,037,096 bytes |
| Peak scratch reservation | 13,312 bytes |
| Peak simultaneous internal reservation | 54,827,522 bytes |
| Input-capacity plus internal-reservation peak overlap | 108,604,636 bytes |
| Lifetime validation work / fixed maximum | 188,428,924 / 512,000,000 credits |
| Release validation elapsed / cooperative deadline | 454,222 microseconds / 120,000 milliseconds |

All six formerly rejected absolute functions—24,208, 24,280, 33,106, 33,107,
53,196 and 68,133—are included in the complete all-body validation pass. Raw
instruction or scalar-arity diagnostics do not substitute for this proof.

Internal reservation accounting includes the specialized fixed state, exact
requested capacities and old/new growth overlap. The caller's immutable input
Vec remains alive through validation and retained-byte equality, so its measured
capacity is separately added to the observed simultaneous internal peak. This
reports those two categories only, excluding allocator overhead, other harness
and subprocess allocations, and the caller's shared cancellation allocation.
It is not process heap or RSS measurement. The 81MiB independent internal category
maxima remain source 64MiB + metadata 16MiB + scratch 1MiB; no future runtime ledger
is implemented or qualified here.

The opaque `ValidatedSwiftReactor` has no Clone, mutation, deserializer, arbitrary
policy/resolver input or conversion to legacy/executable ownership. The proof
certifies policy and ABI validity for its owned bytes; it does not attest their
digest or implementation identity. Original small fixtures use the same complete
fixed structural ABI and validator. Only the explicit runner qualifies the pinned
artifact, hashing the actual immutable allocation with the platform SHA-256 tool
before passing it to the validator.

The final capture passes 48 all-feature unit tests, 12 original Swift-policy
integration tests and one exhaustive allocation-observer test in Debug and
Release; 11 compile-fail authority doctests; and focused all-feature Clippy with
warnings denied. The allocation test observed all 56 allocation ordinals, refused
each one independently, cancelled each one independently, and delayed each
ordinal past a real cooperative deadline. It verified source, metadata and body
deadline stages, zero reallocations, allocation-free error cleanup and no retained
leaks. Its requested peak 18,377 bytes is below the internal reserved peak 20,025
bytes. Original fixtures exercise every fixed dimension, independent narrowing
budgets including zero/overflow/widening, exact import/export/declaration forms,
uncalled and unreachable type errors, checked unsigned active segment bounds,
and the exact 64MiB source and 8,000,000-instruction limits.

Frozen validation retains its original meter 88-byte, metadata 352-byte,
body 144-byte and proof 520-byte layouts on 64-bit targets, including all-feature
builds. Private zero-sized legacy control/declaration specializations add no
stored state. The borrowed 8-byte policy view fits the existing 128-byte fixed
miscellaneous allowance. Swift alone retains and charges its extended control,
declarations, policy, resolved imports and observations. Root integration owns
the full default/stream/cache/execution feature regression matrix; independent
review separately compares calibrated legacy budget admission and usage.

Run the explicit local qualification with a fresh evidence directory:

```sh
python3 -B verification/swift-reactor-validation/qualify.py \
  --artifact compiler/experiments/fieldlog-reactor/local/2026-10-23-qualified/wasm/fieldlog-reactor.wasm \
  --output verification/swift-reactor-validation/<fresh-receipt-directory> \
  --checks
```

The runner never overwrites a receipt. It captures all source and embedded
assets, compiler/Cargo executables and versions, source hashes, commands, outputs,
driver hash and target hash. Its ignored `local/` contains reproducible snapshots
and build outputs; receipts and logs remain reviewable. CI runs the original
same-policy fixtures without the unpublished retained target. No ignored Cargo
test depends on that local artifact.

Historical receipts remain intact: `2026-10-23-first-attempt` is the first complete
Swift validation before exact legacy layout preservation; `2026-10-23-final`
passed complete validation after that repair, then its focused snapshot build
failed because the harness omitted existing embedded JSON assets. The canonical
`final-v2` capture includes those assets and passes all its recorded checks.
Phones remain disconnected and their checks pending.
