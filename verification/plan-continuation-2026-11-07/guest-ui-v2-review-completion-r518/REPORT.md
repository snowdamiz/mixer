PASS for the exact, explicitly UNSELECTED R486 host codec/exchange/header slice.
No concrete defect was established by this independent executable review. Root
owns adoption; this verdict grants no selection, native, release or GA acceptance.

The freshly built retained R486 producer harness passed all 132 checks. The new
independently authored R518 harness passed 77 checks. Identical new V1 control
source passed 19 checks against both the candidate module and the unchanged R472
baseline module; their entire stdout, including original deterministic event
bytes, is byte-identical. This is 19 differential scenarios executed twice,
not 38 independent scenarios. Raw results are logs/producer.stdout,
logs/independent.stdout, logs/v1-candidate.stdout and logs/v1-baseline.stdout.
All four payloads exited zero and emitted no stderr. Comparisons are recorded in
comparisons.json.

Pinned inputs were verified before copying. R486 source tree:
61a3e7760d53788894e04dea2deaaa7db038abe8cb2d6fc6fcce61950e871120.
Patch: 344adf265429189050076837a44670381c4a6d0dd9b4f2ca5d54e175379891f0.
Every entry in R486 SHA256SUMS verified, including source, retained harness,
candidate contract/header and artifacts. The exact R472 inputs listed by R486
also verified. A separate reconstruction of all six patch entries from the
unchanged R472 source and R486 source/candidate bytes reproduced the supplied
patch byte for byte. Copied product and producer source files remain unchanged;
all copied producer artifacts remained byte-identical after the retained run.
This verifies proposed V1 patch preservation and a real R472 V1 source comparison;
no canonical source/header/contract or root Git observation was made.

The independent harness covers UTF8 byte counts using emoji, combining sequences
and escaping controls at 100000 bytes and one byte beyond; all other string fields
at the 4096-byte boundary; horizontal versus vertical policy; explicit policy;
malformed UTF8, JSON, surrogate pairs and decoded duplicate keys; numeric event
lexemes/coercion/overflow; original envelope schemaVersion 1; canonical-equivalent
node identity and duplicate identity; and rejection of an unguarded Codable
entry point. Its exchange attacks exercise foreign owner presentation tickets,
replayed presentation completion, generation validation, single-slot admission
and result retention, accepted event priority over ready, actual-ready conflict
classification, non-invoked ready without turn credit, close outcomes and sticky
before/after-intent protocol failure classification. These are direct host data
operations, not actual guest turns, native UI events or exhaustive concurrency
interleavings.

Independent header checks include an unaligned offset of 1, exact adjacency of
all ranges, a full event capacity ending at the last wasm32 memory byte, a
one-byte document at the final memory byte, one-byte overlap and wrap attacks,
reserved high bytes, a memory size beyond wasm32 and fixed prior header/event
locations. The retained producer additionally covers actual encoded 1MiB caps,
multiple-field escape expansion beyond the cap, node/depth/child ceilings,
strict axis/action/property refusal, original R472 whole Unicode/100000-byte
event equality, stale claims/revisions, running close and other boundary cases.

The V1 differential executes its real 65536-byte document and 4096-byte event
boundaries and their first rejected bytes, actual editor refusals, button startup,
presentation, exact activate/null wire bytes, accepted sequence, busy and result
retention, ready arbitration and no-invocation credit, generation refusal, queued
close and post-close refusal against both modules. Candidate public V1
construction uses the original validator/codecs and caps. No V1 contract/header
change appears in the exactly reconstructed patch. V2 reserves separate exports,
dependencies and MUI2 magic; event schemaVersion 1 is intentional. This review
does not treat reserved identifiers as an installed admission implementation.

One isolated release SwiftPM build used the current Xcode toolchain and three
jobs. It completed with direct child exit0 after 70.56 observed seconds; its
internal reported build time was 59.91 seconds. The observed duration governs.
The four executable runs each completed in under one observed second. Exact
argv, cwd, PID/PGID recorded before waits, timeout budgets, exit codes, observed
duration and executable hashes are in commands.json and logs/*.json. Swift
6.4.2, target arm64-apple-macosx27.0.0, is recorded in logs/version.stdout. No
harness correction or second build was needed. Exact review package hashes are
in source-manifest.json. No Git revision was queried; pinned source tree/file
hashes identify the consumed source.

Every launched payload's direct child was reaped, with no timeout or UNKNOWN
custody event observed. Descendant process-group absence was not independently
measured and is not inferred from direct completion. Fresh R518 build, source,
artifacts and logs are intentionally retained; cleanup.json makes no blanket
descendant absence claim. No simulator/frontend/device or historical held
chain was touched. No root Git, remote, credential, signing or delegated-child
operation occurred. R506 remains a separate INCOMPLETE attempt: its held source,
scratch, raw candidate outputs, compiler PGID76976 and outer exec38931 were not
read, resumed, probed or reused. This fresh harness was independently authored
and does not come from R506.

The V2 C validation symbol remains an UNIMPLEMENTED/UNLINKED declaration. Native
memory bridge, installed recognizer, actual EntryEditor guest reactor and
VM/effects/model/durable differential are not implemented or validated by this
slice. The R472 80544-versus-79966 resource-profile blocker remains unchanged.
R508 work was not an input. Separate published-package consumption,
physical-device/final acceptance and release/GA gates remain pending. Local host
checks do not substitute for them. Root can use this one independent host-slice
review for its adoption decision while retaining all these limitations and the
historical holds.

To rerun in a new output namespace, copy the retained source/, candidate/ and
artifacts/ layout, then build all products from source/ with the exact toolchain
command in commands.json and a new --scratch-path. Execute R486, R518,
V1Candidate and V1Baseline from source/ so ../artifacts resolves to that new
namespace. Compare both V1 stdout files byte for byte. The single-use run.py
labels deliberately refuse overwriting this review's evidence.
