# Independent V2 appearance resolution review

The review owns this directory only. Product code, trackers, commits, pushes,
devices, native resource capture and signed authority are outside its scope.

The binding reviewed source set is the producer's 69 actual source/contract/test
inputs with digest
`b9a12eaa10239fb4d6ce0bdc09478932a2ac46b20119dff8423a843d09cd9138`.
`candidate-4/receipt.json` is the final independent execution receipt. It freezes
those inputs and its own test harness before compilation, uses fresh source and
module/cache/output directories per variant, records commands/tool versions/logs,
and hashes module/library/executable outputs. The original and deliberately
mutated resolver sources are retained separately. The mutation sources are test
controls and are never copied into the product tree.

`oracle.py` independently derives expected data from the frozen contract and
authored descriptor values. It does not import or transform product source.
List expectations use declarative partitions and ancestor queries rather than
the implementation's run-flush/propagated-context algorithm. `Probe.swift` only
serializes actual public results for comparison. Expected full paint matrices
include arbitrary valid unpremultiplied alpha values.

The 133 cases contain 107 accepted and 26 rejected inputs. Ninety-six combined
cases exercise twelve profiles, both schemes, both logical directions, and both
platform selections, each with distinct complete custom platform themes. The
combined trees contain all ten kinds, multiple sibling Lists, empty/headed/direct
groups, nested semantic Sections, inherited disabled state, explicit zero and
half-unit spacing, full state matrices, and exact text properties. Other cases
cover inclusive environment/UTF8 boundaries, unsupported accessibility and nested
contexts, standard-limit revalidation of wider snapshots, and an exact 4,096-node
tree with 4,090 row placements. Each baseline compares 7,858 node records and
31,432 paint-state results, plus full recipe metrics, group references, spacing,
identities, raw environment generations and revision values.

Six separately compiled, deliberately incorrect resolver variants test whether
the oracle detects omitted disabled inheritance, a hardcoded body-caption gap,
final-row separators, admitted nested Lists, collapsed profiles, and lost text
alpha. These expected failures are recorded as mutation detection, never as
product failures. Debug and Release baselines must both compare exactly.

`Adversarial.swift` separately checks public snapshot value semantics, immutable
style calls, preserved routing/reconciler state after failure, full unsigned raw
revision/identity/environment generations, four internally corrupted snapshot
maps, both unselected typed themes, and metadata-only nonexistent resource paths.
The internal corruption probes use testable module access; they do not imply that
an external caller can construct a render snapshot or forge its identity map.

`producer-audit-1/receipt.json` independently checks all 26 retained producer
command logs and 14 compiled outputs and counts actual distinct passed tests:
127 per Debug/Release (119 Swift Testing plus 8 XCTest), including 21 new resolver
functions. It verifies the producer's iOS/official Android/public-consumer evidence
as retained artifacts; those platform compiles are not rerun by this host review.
The producer's original first-target `sdkTestCounts=107` is explicitly superseded
by its bound count audit.

Three harness-development attempts are retained honestly. `candidate-1` rejected
the test harness's supposedly valid locale because it contained U+200D (a control
format scalar); the fixture was corrected to a control-free opaque locale.
`candidate-2` passed both baselines but its first deliberate mutation failed to
compile under warnings-as-errors because the removed inherited state became an
unused local. The mutation was corrected to compile while retaining the semantic
fault. `candidate-3` passed both baselines and detected four semantic mutations,
then its profile mutation failed warnings-as-errors because it switched directly
on a compile-time constant. The final mutation instead substitutes the profile
when constructing the data resolver. None of these attempts is counted as a
product finding or successful full review.

Large exact input/expected/actual JSON artifacts are retained as deterministic
gzip files; the receipt records both compressed and original byte hashes. Build
products remain local and ignored, with their hashes retained in the receipt.

Reproduce with unique labels:

```sh
python3 verification/ui-appearance-resolution-v2-independent-review/verify.py candidate-new
python3 verification/ui-appearance-resolution-v2-independent-review/audit-producer.py producer-audit-new
```

These checks qualify pure data resolution only. They provide no native font
coverage/resources/support, measured extents, native shaping/rendering,
IME/focus/selection/scroll retention, atomic native transaction, stale-generation
enforcement, physical iOS/Android parity, immutable published separate-repository
FieldLog dogfood qualification, signed display/input/health integration, or
signing/store/customer/operational/GA acceptance. Phones remain disconnected and
no device discovery, execution, or reconnection request was performed.
