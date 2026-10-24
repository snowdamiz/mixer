# Swift memory promoted accounting correction

The bounded private correction adds the standalone unit caller promotion omitted
by MR01. Its 123-file source closure is `a01da340253ad086e69c060a041d8d15b3f9bb7a63f8c11465af704ce01ef65b`. The reviewed behavior source
remains `6046a5fa8ba3800ec168b7ae6a80cb82bad5ba39b8701cb23a5db720d998bb62` and the accepted live control baseline
remains `241f7a6037100d29a4d277e1ec176fec55c0380b4283c17120bb8ace045318d5`. Live VM code was not edited.

The promoted-body collector applies the same `selected(name)` rule as function
bodies. Actual compiler MIR contains `memory_pinned_step::promoted[0]` with a
`&LocalKey<Cell<bool>>` return and `LocalKey<Cell<bool>>` backing place. Each now
has distinct source, argument, returned and caller positions. All 4,792 original
schema rows and source fields remain; eight additional unit fields bring the
inventory to 4,800 (2,104 production canonical, 2,164 additional unit canonical,
480 authored active and 52 authored permanent). Historical schema metadata is
retained exactly; the fresh canonical audit records current compiler locations.

Only eight `#[cfg(test)]` accounting fields differ from the behavior source.
Every executable source byte, dependency manifest, owner declaration, limit,
ticket and diagnostic is unchanged. A collector regression includes the actual
standalone promotion, excludes actual test-module promotions and preserves all
original rows. Four fresh Swift-only/all-feature production/unit compiler MIR
configurations reproduce every positive role, including captures, aliases,
literals, width and all selected promotions.

Sixteen paired actual compiler layout runs measure every positive field and its
containing struct, with disjoint offsets. The eight new fields each measure eight
bytes and increase unit active/frame bounds by 64 bytes. Original owner sizes,
alignments and offsets remain unchanged across features/profiles.

| aarch64 host named-object bound | Production | Unit |
| --- | ---: | ---: |
| Memory active addition | 624,544 | 1,142,760 |
| Memory permanent addition | 121,856 | 121,856 |
| Execution header | 1,636,360 | 2,531,040 |
| Complete frame operation envelope | 2,836,512 | 5,092,888 |
| Construction envelope | 1,069,144 | 1,071,904 |

All sixteen frozen MM01–MM16 names execute once in each Swift-only/all-feature
Debug/Release configuration: 64 successful memory selections. The prior 34
frame/control and 12 value tests pass in all four configurations. Eight
default/span/Swift/all Debug/Release library checks pass. Runtime commands use
the exact corrected source; layout programs use separately archived instrumented
copies. No runtime algorithm, control flow, limit, ticket or test expectation
changes are part of this correction.

All 39 compiler-expanded Frozen methods and fourteen owner declarations match
both the reviewed behavior source and original accepted baseline. Frozen retains
its 2,912-byte reservation, the authority remains 86 tickets and State/Combined
limits remain 128/256 MiB. Exact source equivalence supports explicit reuse of
the immutable 56 actual Frozen baseline/candidate observation pairs and four
16-test integration runs. Their commands, outputs, source archives/manifests and
the source-equivalence proof are copied and bound; those executions were not
repeated by this correction. Swift-only MM14 still records Frozen feature absence.

The packet retains exact archives, commands/tools/outputs/executable hashes,
current MIR, measured layouts, the first failed metadata-retention check and its
exact script/input reconstruction, and cleanup. The standalone read-only checker
is `python3 -B verification/swift-memory-promoted-correction/verify.py` (optional
`--live-baseline`). Only this lane's disposable scratch was removed; no native,
simulator/emulator, physical-phone or UI execution ran.

Fresh independent correction review and root acceptance remain required. G08
still has the preserved absent-cursor Cleanup diagnostic. Logical named-object
accounting is not compiler stack, allocator overhead or RSS. Swift bulk memory
and growth, full dispatcher/Ready/public invocation, native joins, immutable
published separate-repository FieldLog, physical phones, signing, store,
customer, operational and GA gates remain open. This is a bounded host slice.
