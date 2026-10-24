# Independent promoted memory accounting review

**Accept the bounded MR01 correction.** The 123-file frozen candidate
`a01da340253ad086e69c060a041d8d15b3f9bb7a63f8c11465af704ce01ef65b`
resolves the prior review's accounting omission. This is an independent review
of a private host slice; root integration and acceptance remain separate.

The producer receipt is
`e261cb8e2f30a013db7803baaf057c10d66bef02155c77b79b9ea37985d5ee16`.
Its checker passes all 563 bindings and the accepted live-baseline check. This
review copies and binds the frozen packet, independently extracts its archives,
and never edits the producer, prior review, live VM or trackers.

The complete source comparison against behavior closure
`6046a5fa8ba3800ec168b7ae6a80cb82bad5ba39b8701cb23a5db720d998bb62`
permits exactly eight new `#[cfg(test)]` fields in `ActivePositions`. Removing
those exact declarations reconstructs every behavior-source byte. All other
122 files, executable source, dependencies, owner declarations, limits, tickets
and diagnostics are unchanged. Every original schema row is retained exactly:
4,792 existing rows plus eight new rows produce 4,800 distinct fields.

Independent raw-MIR inspection covers the four frozen production/unit,
Swift-only/all-feature configurations and a fresh exact-candidate Swift-only
unit compilation. It reproduces all 2,104 production and 2,164 additional unit
canonical positions, aliases, typed literals, five capture payloads, the shared
width body and all selected promotions. Both typed bindings in the actual
`memory_pinned_step::promoted[0]` body receive separate source, argument,
returned and caller fields. The collector uses the same `selected(name)` rule
for functions and promotions. Its three regression tests pass; actual
test-module promotions remain excluded. No old row or alias supplies credit for
the eight new positions.

Fresh paired Swift-only Debug unit probes compile typed references to each new
actual field. The compiler measures eight distinct, aligned 8-byte intervals
with offsets 1,127,424 through 1,127,480. Unit active bytes increase from
1,142,696 to 1,142,760 and the complete frame envelope increases from 5,092,824
to 5,092,888. Permanent bytes remain 121,856. The probes use separately archived
instrumented source copies; runtime regressions use the exact unmodified frozen
candidate. These are host logical named-object bounds, with no compiler-stack,
allocator-overhead or RSS claim.

All twelve fresh focused selections pass: AF05 aggregate boundaries, AF22 phase
admission and distinct reservations, and MM16 accounting restoration, each once
in Swift-only/all-feature Debug/Release. AF22 rejects the one-byte-insufficient
combined limit and prints the corrected 5,092,888-byte frame bound. All fresh
executions bind commands, tool versions, source manifests, executable hashes and
raw outputs.

The broader corrected 64 memory and 184 prior frame/control/value selections,
four compiler MIR configurations, sixteen paired layouts and eight library
checks are reused explicitly. Their commands, exact corrected source closure
and outputs are frozen in this packet. Independent interval checks cover every
positive measured field; production totals are unchanged, unit active/frame
totals alone grow by 64 bytes, and existing fields retain size/alignment. All
fourteen containing owner declarations and layouts remain identical.

Independent reconstruction of the actual compiler-expanded output reproduces
all 39 Frozen method hashes. Exact executable-source equivalence supports the
explicit reuse of 56 immutable baseline/candidate Frozen observation pairs and
four 16-test integration runs, with their original separately instrumented
source archives, commands and outputs. These executions were not repeated by
this review. Frozen reservation remains 2,912 bytes, ticket authority remains
86, and State/Combined limits remain 128/256 MiB.

One independent audit-parser draft included `pub` in six hashes while the
producer hash convention begins at `fn`; its exact script and failed output are
retained. The corrected parser reproduces all 39 hashes. An optional live-checker
draft scanned historical documentation/evidence outside the defined source
closure; all 121 source files matched, and the corrected checker uses the
canonical Cargo/src/tests/include scope. Its failed script, receipt, seal and
output are preserved. No compiler or runtime qualification failed. An
inspection-only lookup used a nonexistent filename;
the actual `frozen-runtime-reuse.json` was then inspected and bound.

There is one nonblocking integration note: candidate
`src/experimental/execution/mod.rs:1139–1140` contains two whitespace-only lines,
inherited byte-for-byte from the behavior source. Root owns their separately
bound normalization and integrated validation; this frozen correction is
unchanged. No other scoped finding blocks MR01 acceptance.

The read-only standalone checker is
`python3 -B verification/swift-memory-promoted-review/verify.py`.
Only this review's disposable scratch was removed after source revalidation and
an empty `lsof` result. No processes were terminated and no native, UI,
simulator/emulator or physical-device execution ran. Other project data and
instances were preserved.

G08's absent-cursor Cleanup diagnostic remains open. Full Swift dispatch,
Ready/public invocation, bulk memory/growth, native joins, separate-repository
published immutable FieldLog consumption, physical phones, signing, store,
customer, operational and GA gates remain pending. This review makes no full
Swift, public API, release or GA qualification claim.
