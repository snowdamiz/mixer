# Retained-evidence review accepts the cost/age candidate rejection

Independent bounded review found no discrepancy in the assigned rejection
evidence. All six finite trace pairs regress in logical CacheWork. The recorded
root decision to reject live integration and decline a full-target attempt is
supported. This is an evidence-integrity and arithmetic review; product-policy
correctness, full-target behavior and release qualification are not accepted.

The read-only [audit executable](../verification/swift-cost-retention-candidate-review/audit.py)
was authored independently for this review. It imports only the Python standard
library and never imports or executes producer scripts, product source or tests.
It reads archives in memory without extraction. Its successful receipt is
[stdout.json](../verification/swift-cost-retention-candidate-review/stdout.json),
with the exact invocation in
[command.json](../verification/swift-cost-retention-candidate-review/command.json)
and exit/output hashes in
[result.json](../verification/swift-cost-retention-candidate-review/result.json).

The assigned packet seal is
`a71d7d9b4405b37e2130c464e0e149d82b2a1ff57f9f75f36cc0e8401bb50702`.
The audit recomputed this seal, all 81 sealed member sizes and SHA-256 hashes,
the complete member set, and the producer document hash
`83178d42bd07c3e23f1c7226494276a06a7758a8f9371c40ea86a11d3a0414ab`.
It recomputed each of the 399 archived source-member hashes and all three
source manifests, checking exact names, counts and source bytes before comparing
the archives with their manifests. No archive member was extracted or executed.

| Source | Files | Manifest SHA-256 | Archive SHA-256 |
| --- | ---: | --- | --- |
| Ordinary live baseline | 132 | `16176e0852fa61cba98acebeb373ee1a6be4c686d0e46ef8bbc144c0527c2cbd` | `98b8792b2907eb36d1e54f2f0b5e04b0738a5a516aa6d1f384e55f9756e94fcb` |
| Baseline with common controls | 133 | `ee10f504353eadf4acfb8d92a2e6dddc4576c1d77768efa6e12fc04bef233174` | `5dd361ac8acab501e306154aeaf7732a86469d948e864fc7d3c14ac065ca9bfd` |
| Candidate | 134 | `b98e72e0c9ba2cc59d001b93f10c864a17befe16d922f4cca540e5afcc6ce108` | `62f14e885d9f2e31d18c487a078a1d3eeeabc684b2a08c1de40a0db9a1229502` |

The current ordinary `vm/` closure was independently enumerated only within
`src/`, `include/`, `tests/`, `Cargo.toml` and `Cargo.lock`. Its exact 132-file set,
every file hash and canonical manifest digest match the ordinary baseline above.
The source paths contain none of the excluded frozen hosted or rejected Worker
V2 lanes, and those lanes were not accessed.

The following numbers were parsed directly from the complete stdout of
`baseline-final-swift` and `candidate-expanded-2`. Ratios and percentages were
derived with exact rational arithmetic before comparison with the producer
summary. All six pairs report zero guest instructions; credits are authored
logical work, not elapsed time or throughput.

| Trace | Baseline decodes / credits | Candidate decodes / credits | Work increase |
| --- | ---: | ---: | ---: |
| Original hot16 / stream128, four rounds | 592 / 1,558,624 | 592 / 1,836,400 | 17.821874% |
| Original cyclic65, three rounds | 195 / 406,583 | 195 / 476,126 | 17.104257% |
| Expensive hot16 / cheap cold streams | 592 / 248,012 | 528 / 363,312 | 46.489686% |
| Cheap hot16 / expensive cold streams | 592 / 1,444,044 | 592 / 1,721,476 | 19.212157% |
| Uniform hot16 / cold streams | 592 / 222,412 | 592 / 500,188 | 124.892542% |
| Expensive old set to cheap cycle64 phase shift | 80 / 17,440 | 784 / 553,152 | 3,071.743119% |

The phase-shift work ratio is exactly `17286/545`, approximately `31.717431`.
The favorable expensive-hot trace saves 64 decodes while using 115,300 more
credits. These retained finite results support rejection without any new test,
full reactor or actual-target run.

Method counts were checked against raw result lines and method-name sets:
39 pristine baseline methods; 42 after adding the same three common controls;
49 candidate methods, including seven candidate-only methods. The sets are
nested, but the counts do not establish equivalent test coverage or independent
correctness. The packet explicitly records a policy-specific change to the
copied `plan_reuse_observation` expectation and a correction to the new all-pinned
test. This audit checks the recorded scope and evidence, not the semantic
sufficiency of those assertions.

Both raw failed runs remain sealed: `candidate-original-swift` exits 101 with
38 passed / 1 failed, preserving the thin-shape 284-versus-288 assertion;
`candidate-expanded-1` exits 101 with 46 passed / 1 failed, preserving
`pin_slots_exhausted` versus `all_entries_pinned`. The initial authoring-script
anchor failure is separately retained as an authored correction record; this
audit does not treat that record as a raw compiler/test transcript.

The Frozen generic controls retain five unit methods and ten integration /
allocation methods (nine plus one). Complete baseline/candidate stdout is
byte-identical for both scopes. Independent normalization changes only the
elapsed-seconds token in Cargo result lines; the normalized SHA-256 hashes are
`c17e6571b4ac9e7bdfc6ddbcb2ecd3d8f1099ad75f75ae022e24da400a67ed27`
and `c76ee9a8856c3614a8ece04ee5d17a361bdd3425fc36706533742bbfb4994730`.
No work, error, allocation, identity, pin or other output is normalized.

The final scratch path is currently absent. Retained cleanup evidence records
two empty holder/process checks, an identity/mutation check, no signals, 438
regular files and 218,566,668 logical bytes removed. Its 68 directories include
the root recorded separately from 67 child directories. Those historical
process and stability checks were not rerun; their receipt integrity and
inventory arithmetic were checked.

The final audit ran on Python 3.14.8, arm64 macOS 27.0.1, exited 0, and produced
stdout SHA-256
`fc4e9cd4cef0bdbda7e79da248c840ad6af4f963bd119f2009c48271428b592f`
with empty stderr. Tool/executable hashes and every packet input-member hash
are in the output. The first audit attempt incorrectly excluded the separate
root from the directory count; its source, command, failure output and receipt
are retained as `attempt-1-*`. The final script corrects only that audit check.

No product/candidate test, source rebuild, scratch restoration, Git command,
full target/reactor, native/UI/capture, physical device, network/provider,
signing, publication, customer operation or FieldLog release was attempted.
The memory inventory and byte-identical implementation-body claims were not
independently audited. Physical-device, operational, published-package and GA
gates remain outside this review. The review's own document and receipt files
are bound by
[seal.json](../verification/swift-cost-retention-candidate-review/seal.json)
and its SHA-256 sidecar.
