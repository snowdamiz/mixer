# Independent review of the private Swift resident index

No actionable defect was found in the frozen six-file candidate. The independent review recommends root integration as a development slice under the selected contract. This is not production acceptance, a full-reactor completion result, native parity, or permission to expand any limit.

The reviewed producer seal is `fc45e20ca74edc4d435b1d9d82ed8b01bb68a55b42801501901356ab530b39d7`; receipt `916b8fdfdc2d78f538bb2fc556a37cce97304850bc4868c8e1685304d2b76267`; patch `bbf581ceb101f4befbd5d9f837b7fe7648155c36d009b1eb1c46cbc5c3f0401e`. All 570 sealed members and the candidate's 132-file closure `02fd25a32b05cf8c4b10e0f68df029d8851e14610ccecbec772be09af5073f8d` were verified independently. The live baseline closure remains `b28da766c84b6353a4511e2fc3fbcb0d4302d5b8a5a74da1ee3d7fb776ca2c11`; root HEAD at review preparation was `ee390cbf56ba388a21c7d28c884dbed5fd7282fe`. Only review-owned scratch and artifacts were changed. Producer preparation/verification scripts were read, never executed or appended to.

The review read the contract, producer report, six-file patch and relevant shared/private lifecycle source. Default CacheMode lookup preserves the literal former linear loop and mutation hooks do nothing; FrozenMode does not override those defaults. A fresh baseline with its original cache test file restored and a fresh candidate use separate target directories. Their complete 53,783-byte FrozenMode observation trace is identical, including recorded work/failure/allocation observations.

The index uses exactly 128 heads and 64 next links. Lookup validates the entire encountered chain before returning a match; slot bounds precede bit shifts and dereferences, requested identities come from decoded residents, bucket checks reject foreign chains, and repeated slots or a nonempty link after 64 nodes fail closed. Removal validates the victim's whole chain, then precharges both writes before unlinking. Insertion validates its chain and empty destination, then precharges both writes before index and infallible slot publication. Removal refusal retains the affected resident; insertion refusal drops the newly built entry and ticket while retaining the first terminal cause. Partial progress through several completed evictions remains coherent. No public execution contract, decoder, 64-entry ceiling, production budget, dependency or native bridge changed.

| Fresh host verification | Observed result |
| --- | --- |
| Unmodified private cache, Debug | 29 passed |
| Unmodified execution/construction, Debug | 21 passed |
| Unmodified lifecycle, Debug | 49 passed |
| Unmodified shared cache, all features, Debug | 5 passed |
| Literal FrozenMode comparison | Identical fresh baseline/candidate traces |
| Independent candidate controls, Debug | 6 passed |
| Independent candidate controls, all features, Release | 6 passed |
| Independent baseline controls, Debug | 2 passed |

Independent controls append tests only to a fresh scratch copy. The shared baseline/candidate control source uses its own timestamp, slot and pin model for 2,048 operations at each of capacities 1, 3, 16 and 64. All 8,192 operations match the model and the baseline trace. The respective runs make 1,013, 1,003, 889 and 472 evictions; checks include every slot identity, pin multiplicity, strict rank, pin nonce, resident and pin live counts, resident ticket counts, cache reservation sum, and every index membership after each operation. Hits and releases allocate nothing. Candidate and baseline model output is identical in Debug; the candidate Release output is also identical.

Independent fault controls cover all 832 shorter constructor credit budgets and all 852 observed constructor cancellation checkpoints. Every refusal drops partial storage, retained proof and tickets to zero. Another independent fixture needs four resident evictions before an exactly fitting large entry can publish. All 193 shorter replacement budgets and 141 cancellation checkpoints preserve index/slot/ticket/live-count coherence; the work-prefix matrix observes zero, one, two, three and four completed evictions, retains the original failure on retry and consumes cleanup to zero. Four additional cases find the requested head before an invalid, empty, wrong-bucket or cyclic tail; every case rejects the request without a hit, allocation or publication.

The independently rerun original cache suite also covers collision head/middle/tail removal, reuse/reinsertion, all-pinned refusal, each mutation work/cancellation boundary, an inclusive 64-node chain, malformed links, four constructor allocation/capacity refusals, decode/allocation/deadline failures, owner/nonce safeguards, dirty scratch, independently expected IR and consuming cleanup. This review combines those representative regressions with independently authored controls; it does not treat producer test success alone as review.

Measured allocation and reservation checks find four exact constructor allocations totaling 26,304 buffer payload bytes, including 192 index bytes, with five added tickets for those buffers and the cache header. Default fixed reservation is 89,376 bytes; cleanup/header/construction/operation/foundation envelopes are 62,696/63,072/57,896/88,294/269,616 bytes. The ticket capacity remains 86. Source inspection confirms the new vector, ticket/owner moves, scratch borrows and helper/return inventories are included in measured reservation calculations. These are conservative named-object envelopes, not stack high-water or process RSS measurements. The existing cache suite verifies the conservative FrozenMode helper inventory still fits its unchanged reservation.

| Independent finite actual-cache fixture | Baseline | Candidate |
| --- | ---: | ---: |
| Construction credits | 640 | 832 |
| 64 cold decodes | 13,127 | 9,671 |
| Four 64-entry resident hit sweeps | 8,832 | 2,048 |
| Retained decoded payload bytes | 2,600 | 2,600 |
| Hit allocation requests | 0 | 0 |
| Fixed reservation bytes | 88,536 | 89,376 |

The finite hit-credit reduction is 76.81%; it is not CPU timing or a reactor completion prediction. The unfavorable first-slot single-resident hit costs eight credits instead of three. The original, independently rerun 64-collision control costs 260 credits and validates the whole chain. Repeated-decoding cost remains outside this change.

One initial lifecycle filter selected zero tests. Its exit-zero receipt is retained and excluded from coverage; the corrected filter ran all 49 lifecycle tests. An initial unqualified shell tool-version probe could not find `rustc`; absolute toolchain paths resolved it. Initial independent controls were strengthened to ensure small-capacity evictions and add actual allocation/ticket measurements; their earlier receipts and exact overlay sources are retained. No Rust test failed or timed out during this review. Two pre-existing test-only `dropping_copy_types` warnings remain; an initial review-only `unused_mut` warning was removed in the final overlay. The producer's failed/timeout attempts and invalidated stale-target trace remain unchanged and explicitly unqualified.

Receipts record complete command arguments, sanitized environment, Rust/Cargo 1.99.0 tool identity, Python version, source manifests, executed binary hashes, raw output hashes, EOF and process-group termination. Owned source/build scratch is removed only after confirming all recorded groups are absent and a recursive holder check finds no open files. The independent seal binds these artifacts and this report to the exact producer packet. No simulator, emulator, physical phone, full reactor target, excluded hosted lane, signing, store release or publication was executed. Physical phones, native parity, immutable published FieldLog consumption and specified final acceptance gates remain pending.

[Independent receipt](../verification/swift-cache-resident-index-review/receipt.json), [seal](../verification/swift-cache-resident-index-review/seal.json), [packet audit](../verification/swift-cache-resident-index-review/packet-audit.json), [comparison](../verification/swift-cache-resident-index-review/independent-comparison.json), [literal trace comparison](../verification/swift-cache-resident-index-review/frozen-comparison.json), [independent common controls](../verification/swift-cache-resident-index-review/common-controls.rs), [candidate controls](../verification/swift-cache-resident-index-review/candidate-controls.rs).
