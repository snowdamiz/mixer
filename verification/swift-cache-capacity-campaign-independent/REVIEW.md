# Independent cache-capacity campaign review

Decision: accept the pinned preparation for root to integrate and execute the
four primary comparisons once on the selected GitHub-hosted Linux runner.
This is permission to collect bounded diagnostic evidence, not a completed
runtime result, production profile change, OTA release, native receipt or GA pass.
The reviewer was assigned fresh `gpt-6-astra`, `xhigh` under product-plan
20.3/24.4 and ADR 0002. Ownership was this directory only.

The trigger is the preserved CacheWork failure at 64,000,001 / 64,000,000 after
23,358,291 guest instructions, together with repeated preparation-only cycles.
The concrete command unlocked by this review is:

```sh
python3 -B verification/swift-cache-capacity-campaign-v1/campaign.py run \
  --output "$RUNNER_TEMP/swift-cache-capacity-campaign-v1"
```

The accepted sequence is 64/64M, 64/128M, 128/64M and 256/64M, serially. A fifth
combined attempt is reserved by ADR 0002 but is neither selected nor implemented
by this driver. Root must use the four results to justify that continuation,
bind it to this campaign and retain the total five-attempt ceiling; rerunning
all four in a new invocation is not an approved continuation.

## Evidence and source boundary

`receipt.json` binds all candidate input and driver hashes, the four generated
source-manifest digests, Python/platform identity and the exact review command.
`pure-controls.stdout` records 15 passing checks: the author's nine and six
independent checks. Execution took under one second. No compiler, guest, child
process, native/UI/capture, global inventory, PID/custody or device test ran.
Temporary oracle files were removed. No canonical source, Git/index or product
status metadata was changed by this reviewer.

The archive is the accepted 132-file observer closure; each generated variant has
only the audited cache/control/test changes and one original harness include.
The complete validator, execution/lifecycle implementation, borrowed cache
algorithm and decoder remain byte-identical. The baseline and work-only source
closures differ only in the cache-work number in `control.rs`. Every generated
manifest independently matched the retained author source-check manifest.

The original 18,976,211-byte compressed full artifact remains SHA-256
`e22a8226908ef68170ac94267978b4b436c45764bc591451ef16161d6dbd52ac`.
Its decompressed bytes, original harness, native observation, telemetry parser
and historical stdout were verified against their bound hashes. The historical
failure replay remains a failure with valid supplementary telemetry and consuming
cleanup. It was not reclassified as completion or used as a paired Linux timing.

## Storage, work and lifetime challenge

| Changed item | Finding |
| --- | --- |
| Resident index | All actual owners, transfers, borrows, return inventory and inspection types use u16 consistently. The fixed 128 buckets plus N links charge `(128+N)*2` bytes while initialization still visits and charges every logical cell. Slot 256 is representable, zero remains empty, and slot bounds precede bitmap indexing. |
| Cycle detection | The N/64-word bitmap covers exactly 64/128/256 residents. The existing three complete `ResidentIndexInventory` reservations grow through `size_of`; no new heap payload is introduced. Zeroing one/two/four words is bounded scratch work. Probe/node debit semantics remain unchanged, so credits are not CPU instructions. |
| Eviction planning | The generic N-element bool plan and private operation reservation grow together. The actual N-cell recount and real slot walks retain their original debits. Larger capacity can therefore increase planning work; savings are not assumed. |
| Residents and pins | Resident allocation uses checked N times actual `SwiftSlot` size and exact-capacity reservation. Active pin storage, nonce/owner validation, free-pin search and the 64-pin ceiling remain unchanged. |
| Tickets and lifetime | N+22 is the ledger's live-ticket ceiling, not an unaccounted fixed ticket array. Resident tickets remain inside charged actual owners; transfer/result types remain covered by actual `size_of` inventories. Index/plan payloads still drop before the header refund. |
| Failure and counters | Checked additions, overflow failures, sticky first failures, fail-before-publication order and consuming cleanup are unchanged. The accepted observer remains supplemental and retains one reset before one owner; neither cumulative cache work nor guest counters reset between corpus calls. |

The candidate retains the 16 MiB cache, 8 MiB entry, 48 MiB guest memory,
256 MiB combined logical reservation, 64 frames, 100M instruction fuel, 1B
execution work, 120-second validation deadline and cumulative 30-second runtime
deadline. Source review does not substitute for the pending compiled envelope
control or actual host observations.

The four remote finite controls exercise the discriminating risks: retain all N
residents and hit them without decoding; force eviction; reject pin 65; validate
an N-node collision chain and slot 256; reject cycles/out-of-range links; reuse
original exhaustive replacement work/cancellation and constructor failure
boundaries; and consume an actual N-resident owner under the original combined
ceiling. These tests must pass for each profile before its full attempt.

## Runner and oracle corrections resolved

The initial driver could consume up to 2,280 seconds under a 1,500-second job
ceiling. It now has a 1,080-second monotonic campaign limit and declines each
command unless its original bound plus a 20-second cleanup/receipt reserve fits.
Checkout, compiler installation and pure checks have one/three/one-minute caps;
upload has two minutes, within the 25-minute job bound. Compile remains 180
seconds, finite and original-harness controls 90 each, and a full attempt 170,
with TERM/KILL bounded to five seconds each. SIGTERM/SIGINT request cancellation
through the same owned-group polling and cleanup path. An unresolved owned group
stops resource reuse and retains scratch. Exceptional runner/OS failure or forced
kill can still leave incomplete evidence; it never establishes feasibility.

The classifier now handles the Rust test-runner prefix before the first event
and independently parses each corpus's stdout suffix after the preceding phase,
including nonempty initialization output. Independent adversarial cases reject
duplicate keys/phases, an extra or missing field, wrong numeric/boolean types,
concatenated observations and rewritten cumulative stdout. Native-equality labels
alone cannot establish feasibility. The original Rust oracle and consuming
cleanup remain mandatory, as do both corpus phases, valid telemetry, zero exit,
no timeout and an empty owned process group.

The driver preserves commands, tool versions, source/binary/input identities,
raw outputs, phase counters, cache churn, reservations and per-command wait4
observations. Logical reservations remain distinct from process RSS; neither is
an observed device-memory result. I/O/toolchain/finite failures remain stopped
campaigns, not completed comparisons. The maximum schedule may stop before all
four variants if commands consume the available aggregate budget.

## Required interpretation and next decision

The small-cache hypothesis predicts lower repeated decode/build cost and churn
from retention. The competing larger-table hypothesis predicts increased chain,
victim-selection and plan-recount cost that can dominate those savings. The
work-only control asks whether the same implementation can complete with a larger
finite allowance. All four use the widened index, so the fresh baseline is
required and the historical byte-index result stays separate.

Compare complete named phases and their instruction progress, category deltas,
decodes/hits/evictions and reservation peaks. Lower credits at an earlier failure
are not an optimization. A longer prefix is diagnostic progress. Correct output
from both corpus calls on one initialized owner, without an invariant failure and
with consuming cleanup, is host feasibility. A work-only success is profile
feasibility. A single timing is an observation, not a speedup claim.

After the bounded remote run, root should select the smallest demonstrated
adequate experimental configuration with headroom, justify the unused combined
attempt, or move to a different algorithmic hypothesis. Do not expand this review
into another prerequisite-only cycle. Native/UI/capture pause, disconnected
phones, UnitA/local-custody/global-inventory holds and retired Android v5 stay in
force. Public-SDK integration, immutable separate-repository FieldLog consumption,
signed OTA, physical devices and GA retain their own pending acceptance.
