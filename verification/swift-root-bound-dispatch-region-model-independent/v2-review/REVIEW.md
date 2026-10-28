# V2 source review: R01 corrected; release one bounded host attempt

The frozen v2 correction addresses R01. Recommend root release exactly the one
compile and conditional one host-test command in host plan
`5a2950e97e714e3628546d9b73aa2918c72f23f1221c64806823f978dc2c32e8`.
No blocking source issue remains in this review. Rust compilation and all 24
declared test methods remain unexecuted; no test result is inferred from their
assertions.

The released producer seal
`53ab4e6ef041346dadadbbba69b7e5f5a7c35df004d9f1da753845be15779861`
contains 11 verified members, tree
`348f163d40ddc9931b8c78abaedb3b5a535327cd54560b9951899e0de72db952`.
The source/plan/contract/toolchain/linker/SDK review checked 130 unique input
members before and after with identical hashes. The original producer packet
and six-member independent review remain unchanged. No producer preparation
script, Rust model, compiler, test, version command or prior checker was replayed.

## Corrected semantic coverage

All three transition forms into `BodyReturned` call the same private
`return_admitted(payload)` helper: setup refusal, the expressly counterfactual
invariant fallback, and the common `BoundReturn` for raw-refusal and leaf-return
payloads. The helper moves all backing owners from `Body` to `AdmittedReturn`,
then independently retains `Body` as the unknown callee activation/frame.
`AdmittedReturn` maps to `CurrentShape::AdmittedOutcome`, with the accepted
13,624-byte minimum and alignment checks. `ChildWrap` transfers the complete
carrier and its backing owners to `Child`, destroys the now backing-free Body
frame, and enters the returned-child phase.

This closes the original gap in the model behavior, beyond adding assertions.
Every recorded return segment contains the distinct typed carrier. The unchanged
assessment requires a top-level region for every semantic owner in every live
segment; its shape must match `for_owner`, have complete evidenced capacity, and
meet the known size/alignment. An 8-byte unknown Body extent cannot stand in for
the carrier, and a later child extent cannot satisfy an earlier owner. A nested
declaration alone cannot bypass the mandatory top-level owner coverage.

The retained Body obligation also cannot be replaced by the carrier. Its width
remains unknown. The test fixture's 8-byte frame bound is arbitrary synthetic
input, not a measured frame width. Semantic transfers establish neither physical
aliasing nor disjointness. Same-arena declarations need their explicit identity
evidence and compatible funding; live intervals enter the existing checked
union. Distinct simultaneous arenas require disjointness evidence. Complete
backing obligations remain counted once per key while any owner is live, through
carrier transfer and explicit destruction.

The independently reconstructed exact model delta equals the frozen model.
Apart from adding the owner, helper, three helper calls, child transfer and shape
mapping, the state/assessment implementation is unchanged. Candidate-copy
atomic refusal, explicit payload/wrapper drop and unwind cleanup phases,
forgotten/unwound refusal, ten quote partitions, separate Work/Bytes units,
checked sums/unions and retained child sums remain intact. The ScopePairReady
phase still explicitly represents the 56-byte scope pair. Every assessment
retains its private `ModelOnly` marker, including fitting reviewed-looking
hypotheses; no output grants production authority.

## Prepared tests and limits

The original twenty methods are preserved byte-for-byte. Four appended methods
cover the four frozen R01 specifications. Their helpers declare eleven return
trace representatives: five setup failures, one conservative invariant fallback,
two raw refusals, pre-scope leaf failure and two finished-leaf payloads. This is
not a claim of exhaustive state enumeration or normal File reachability.

The new declaration builder narrows each extent to its semantic owner interval.
The child starts at ChildWrap, after the typed carrier segment. C01 and C02
remove return coverage; C03 supplies undersized reviewed-looking capacity, wrong
shape, an expired interval and missing evidence. C04 preserves complete separate
coverage or explicitly declares overlapping return/child storage, while removing
identity, frame disjointness, frame lifetime or compatible funding in adverse
subcases. Fitting hypotheses still pass through the model-only assessment helper.
These are source-reviewed assertions prepared for the root-owned host attempt,
not observed passing tests.

## Exact host plan

The plan binds exactly two isolated Rust files and only standard collections,
the pinned rustc 1.99.0 toolchain/clang/link editor/SDK, explicit full environment,
cwd and two argv arrays. Root may run one Debug `rustc --test` compilation for
`aarch64-apple-darwin` with overflow checks and unwind panics, then only on compile
exit zero run that binary with `--test-threads=1 --nocapture`. Expected execution
is exactly 24 tests, none ignored. There is no retry, optimized second build,
formatter, version query, product layout query or native/device action.

Both commands share one cumulative 55-second budget: compile deadline 30,
test deadline 45, exact owned cleanup 49 and posthash 53.5 seconds. Output caps,
generated-file bounds, absent-before-launch command directory, binary pre/post
hashing, source/tool custody and exact child/group closure remain required. Root
owns the runtime lane, release receipt and terminal evidence. Any failure or
unrun stage remains a failure/pending stage; ambiguous artifacts are preserved.

This reviewer created no compiler/test process or build artifact. No cleanup is
owed. The first independent source/hash script completed source and plan checks
but refused its own reported Homebrew Python symlink while writing the receipt;
its exact script/stdout/stderr are retained in `review-attempt-1/`. Recording the
resolved executable fixed that reviewer metadata issue; the corrected source/hash
review passed. This was not a producer/model/compiler retry.

No canonical product source, metadata, commit or push changed. Actual physical
capacity, work prices, production grants, root funding, complete ownership,
FieldLog, OTA and GA remain pending regardless of a future host-model result.
