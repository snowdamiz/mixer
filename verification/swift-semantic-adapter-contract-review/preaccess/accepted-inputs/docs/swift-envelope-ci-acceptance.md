# Standalone fixture-envelope CI acceptance

The accepted fixture-only envelope source now has a portable CI runner with an
exact 86-member source pack. It executes 78 producer and 14 independent tests,
one positive and eight negative API probes, 21,714 fresh candidate comparisons
against retained expected results, and 32 host layout checks. It does not import
or execute the historical model. The underlying step/memory accounting and
source acceptance remain separate from this runner's acceptance.

Independent review rejected the first runner because duplicate compiler fields
could overwrite earlier values and an API error could use an unrelated primary
span. The correction requires one complete coherent compiler identity and pins
all eight probe sources and 23 intended primary targets. Every coded diagnostic
error must match its expected code, identifying terms and source targets;
duplicate JSON keys, invalid offset types and mixed valid/invalid spans reject.
The fixed selected tuples are Rust 1.99.0 and 1.98.1 on Apple arm. Only actual
1.99.0 host qualification has completed at this acceptance boundary.

The corrected producer passes 32 runner controls normally and under Python `-O`.
Independent review passes 346 parser cases in each mode, separately reproduces
both old bugs as rejected subprocess invocations, and exercises one valid
synthetic response baseline plus 39 intended refusals. One clean actual Rust
1.99.0 run passes the complete source closure above. The first 40 synthetic
review invocations had a fixture path error and remain preserved with zero
accepted passes. These response controls establish runner behavior, not product
semantics.

Root reverified all 368 corrected producer members, 10,789 independent members,
the unchanged runtime pack, 795 recorded command results and 1,590 raw streams.
The clean run's 92 retained files, including 79 independent actual-File inputs
and reports, reconcile to their original bytes. Owned command groups returned
and scratch was removed. See the [root acceptance](../verification/swift-envelope-ci-root-review/corrected-runner-acceptance.json)
and [independent review](../verification/swift-envelope-ci-independent-review/correction-review-1/review.md).

The original 52 planned obligations have an explicit disposition map; they are
not 52 passed tests. Whole-budget exhaustion, every individual timeout class,
active-phase interruption and valid local PATH/rustup-symlink launcher variants
were not separately forced. Earlier fault evidence is reused only for unchanged
runner functions and identical pack bytes. The two rejected parser results are
superseded only by the separate correction evidence.

The selected workflow adds the envelope invocation after existing framing checks
and uploads its entire owned output, including partial failure receipts and
hidden ownership files. The existing regression-test discovery includes the new
runner controls. The envelope step has a ten-minute limit around the runner's
480-second active budget and 60-second retention allowance; existing jobs and
framing checks are unchanged. Actual Rust 1.98.1 CI results remain pending until
the delivered commit completes and its artifact is audited.

Large immutable producer/review packets are transported in verified archives
described by [the evidence README](../verification/swift-envelope-ci-delivery/README.md).
The CI runner reads ordinary pack files and never opens those archives.
Historical archive-member paths are provenance, not a claim that every path is
an ordinary file in a fresh checkout. Semantic replay, real authority adapters,
live VM/CLI/target integration, native/device, immutable published FieldLog and
release/GA gates remain pending. No native runtime or capture was started.
