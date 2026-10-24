# Numeric primitive extraction independent review

Recommendation: accept this narrow frozen primitive-dispatch slice. No blocking
source, public-behavior, accounting-map, test-validity or provenance finding was
identified. This recommendation applies only to producer seal
`3aa593f55798bc9e381119a865b1a2388dcebc7272395e1a035a0b3ed04a8e58`
and product VM tree
`541597e176144c8fdedc4469f0d9a42095b2ca5cd19f50af94785c064e872248`.

The independently inspected product diff changes only
`vm/src/experimental/execution/{mod,borrowed}.rs` and adds
`vm/tests/span_numeric_extraction.rs`. The private helper contains the original
three primitive-selection branches. Its only concrete mode is FrozenMode; the
short values borrow returns the original arena. The helper preserves the raw
`Result<(), &'static str>` type. Numeric shape, frame/type validation, the
`count + 1` work debit, observation of the actual post-helper arena and guest-trap
mapping remain in the same owner order. No owner field, public API, mode object,
Swift adapter, failure wrapper or reservation formula changes.

The eight derived typed inventories include the new helper and values-adapter
source/argument/reference positions and raw result transfer positions. Named
positions occupy disjoint bytes; the audit checked 1,476 emitted positions over
the four span/all-feature profile comparisons. Pop and divide/truncate child
calls are sequential, and the separate phase inventory retains caller roles.
The maximum selected window is 464 of the unchanged 512 scalar bytes. The
unchanged total fixed reservation is 2,912 bytes; Frame/Control/SpanInstance and
their offsets match baseline and candidate. These are executable typed source
inventories, **not** measured compiler stack frames. The rejected larger
fallible/unit adapter inventories remain failed historical evidence and are not
the applied source.

The producer's public trace fixture tests all scalar/saturating route shapes
and records full public results, diagnostics, usage/cache counters and allocation
intervals for comparison against the baseline. The fixture's ordinary success
results are trace comparisons, rather than stand-alone semantic expectations;
the existing scalar parity/float suites and explicit Node oracle runs supply
the complementary semantic checks. The independent fixture adds ten direct
expected value/trap outcomes using argument-bearing functions, plus four exact
numeric work-debit boundaries per profile. It asserts trap cursors, instruction
and fuel counts, complete cleanup, sticky failures, no cold reallocation and
zero warm allocation while the observer rejects its first request. Both fresh
Debug and Release targets passed with source manifests checked before and after.

The independent read-only audit verifies all 229 final producer seal bindings,
the source archive contents and hashes, the product tree digest, all 44 main and
27 explicit-oracle command logs, runtime/list test identities, selected counts
22/48/137/186, 454 equal public traces per span/all profile, and the identical
26 broad Clippy diagnostic identities. The baseline source archive matches Git
revision `b6a797241087403eb8b5a729940728694b940d84` byte for byte. The independently
built product source exactly matches the producer snapshot. Scoped all-feature
library/new-test Clippy passes; broader all-target Clippy remains a failure.
The minimal-span independent builds also emit three existing cache-borrowed
warnings, retained in the raw logs.

Evidence is in `20261024T004648645488Z/receipt.json` (fresh test commands, versions,
snapshots and outputs), `producer-audit.json` (independent artifact audit), and
`acceptance.json` (this lane's final bindings). `run.py` reproduces the focused
host regression into fresh targets. `audit.py` audits the exact producer seal
without writing in the producer's lane.

This is selected host evidence. It does not re-run the full product integration
suite or execute the full Swift target. Complete numeric owner sharing, Swift
execution/initialization, devices, immutable published FieldLog consumption and
GA acceptance remain pending. Phones were not accessed. This reviewer changed
only `verification/numeric-primitive-independent-review/`, with no commit, push,
tracker mutation or product edit.
