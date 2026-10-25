# Exact Swift reactor after private resident index: single selected result

The sole selected full-target attempt fails closed during Corpus 1 with the first
real typed resource failure: `Invocation / ResourceExhausted /
swift_run_ticket_inventory / TicketInventory`, function 79,548, source offset
15,881,589, attempted 87 tickets against the unchanged limit 86. It is not a
full-reactor completion or native-parity pass. Root selected the exact packet with
SHA-256 `677beb7e3bb2751f0fc819f4e695dc22f576ffa027eb7b6bc6c7139b834599fb` at
commit `be472ce6424a691de5673e3438d2768264827d23`. Source-freeze HEAD context remains
`ee390cbf56ba388a21c7d28c884dbed5fd7282fe`; the selected 132-file source closure is
`02fd25a32b05cf8c4b10e0f68df029d8851e14610ccecbec772be09af5073f8d`. No build receipt is relabeled as the later commit.

The selected command was:

```sh
python3 -B verification/swift-exact-reactor-after-resident-index/diagnostic.py target
```

The exact selected child exits 101 after 2.161608 seconds,
without timeout or host cleanup signals. The outer driver reports failure. The
53,777,114-byte reactor, approved byte-identical original after-cache harness,
fresh executable, source closure, tools, input/native-oracle closure, argv and
limits remain unchanged through execution. No retry occurred. No attribution
instrumentation was added. The original after-cache CacheWork failure remains
immutable historical evidence.

Complete owned validation passes all 79,832 defined bodies, 34 imports and
6,505,659 instructions. It consumes 188,428,924 validation work credits in
467,705 microseconds; metadata is 1,037,096 bytes, peak scratch 13,312 bytes and
internal peak reserved capacity 54,827,522 bytes. The external input has capacity
53,777,114 bytes, for requested-capacity overlap 108,604,636 bytes, excluding
allocator overhead and RSS. The external input is dropped before adoption.

Adoption, original-owner construction and Initialize succeed. The actual reply
is `Initialized`; the owner reaches Ready with 584 memory pages, 37,328 guest
instructions, 158,536 cache work and 76,359,130 execution work, at 18,329 cumulative
runtime microseconds. Construction observes the selected fixed cache reservation
89,376 bytes and constructor cache work 832. These are full-target observations.

Corpus 1 reaches the typed TicketInventory failure at 1,655,443 cumulative runtime
microseconds, 6,555,490 guest instructions, 6,574,090 fuel, 31,475,443 cache work,
175,789,054 execution work and 132 host calls. At the checkpoint, inventory is
86 live tickets, with 64 cache residents, 12 active pins, 12 frames, 55 controls
and 114 values. Combined requested reservations are 137,957,627 bytes, peak
139,479,555 bytes. Construction reservations are 31,548,424 bytes, peak
31,636,718 bytes. Memory remains 584 pages / 38,273,024 bytes. WASI records
16,963 work, 2,054 transferred bytes, 2,020 secure-random bytes, and zero log
bytes or host failures.

The unchanged observer identifies the active Invocation cursor and aggregate
inventory. It does not emit a per-ticket owner list, the requesting reservation
owner/category, or the attempted reservation bytes. Initialize's completed
snapshot already records 86 tickets with 64 residents. These observations do not
identify the requesting ticket owner or establish the cause of its pressure.
A separate diagnosis must bind any further owner attribution; no instrumentation
or causal repair was added to this run.

Corpus 2 is skipped. Actual guest stdout and stderr remain empty at every emitted
snapshot. No eleven-field native-parity observation is available. The final libtest
assertion panic preserves the diagnostic failure and does not replace its typed
resource cause. `commands/target-once/` retains raw streams and the pre-cleanup
failure snapshot.

`phase-counters.json` retains direct snapshots and exact arithmetic intervals.
Corpus 1 below is its terminal snapshot after failure completion and drain at
1,655,521 cumulative runtime microseconds; it is not a separate cache observation
at the internal failure checkpoint.

| Counter | Construction | Initialize complete | Corpus 1 terminal |
| --- | ---: | ---: | ---: |
| Entries current | 0 | 64 | 64 |
| Cache category current bytes | 89,376 | 318,253 | 503,721 |
| Cache category peak bytes | 89,376 | 569,139 | 1,937,355 |
| Fixed reserved bytes | 89,376 | 89,376 | 89,376 |
| Resident bytes | 0 | 228,877 | 414,345 |
| Resident peak bytes | 0 | 479,763 | 1,847,979 |
| Pinned peak bytes | 0 | 184,388 | 1,238,071 |
| Construction peak bytes | 0 | 97,491 | 491,557 |
| Hits | 0 | 324 | 131,944 |
| Misses | 0 | 135 | 22,467 |
| Completed decodes | 0 | 135 | 22,467 |
| Evictions | 0 | 71 | 22,403 |
| Live tickets | 22 | 86 | 86 |
| Cache work | 832 | 158,536 | 31,475,443 |
| Execution work | 76,242,475 | 76,359,130 | 175,789,054 |
| Fuel | 0 | 37,345 | 6,574,090 |
| Guest instructions | 0 | 37,328 | 6,555,490 |
| Host calls | 0 | 7 | 132 |

Original consuming owner cleanup completes. `final_cleanup_usage` records all
reservation categories, combined reservation, live tickets and live categories
at current zero, without a cleanup invariant. The independent
`cleanup_reservations_and_live_empty` event is true. The unchanged success-oriented
`cleanup_empty` and raw driver `ownedCleanupEmpty` remain false because the first
failure is retained. The failure's attached `after_cleanup` snapshot predates final
tail retirement and records 271,360 bytes / three tickets; the separate final
consuming snapshot records their retirement. The classifier preserves both facts.

Owned process group 50585 is proven absent, with no signals. Output
handles close and complete hash reads reach EOF. All prepared members retain
their bytes, apart from the selected executable's explicitly recorded lossless
compressed representation after cleanup. Empty holder checks and path/inode
rechecks precede removal of only owned scratch, reclaiming
77,750,391 logical bytes. The 4,729,840-byte
selected executable remains in `bin/exact-tests.gz`,
1,784,813 bytes, compressed SHA-256
`3e901e5f9db1b6b6f821008bb0b4549ef5f06dd30198732c66308ed4bb42e237`. Decompression reproduces
selected executable SHA-256
`06581b463d8f278776c91684e66ac643e17d6d338d34846d78aabebc2f7aca93`. The separate child high-water RSS observation is
117,506,048 bytes; it is not a per-phase ledger, production
memory, or performance acceptance result.

The original preparation document, receipt, seal, harness and driver stay frozen.
`result-receipt.json` and `result-seal.json` separately bind the actual result,
classifier, direct counters, raw evidence, preparation seal, exact root selection,
cleanup and this report. Verify the final packet read-only without compilation,
full-target execution or native execution:

```sh
python3 -B verification/swift-exact-reactor-after-resident-index/verify-result.py
```

Full-target completion, full SL matrix, guest table mutation, production caller
stack/accounting, public/signed/native execution, memory/size/startup/performance,
full app UI/effects/state/async/actor coverage, source debugger, immutable published
FieldLog packages consumed from a separate repository, physical phones, store,
customer/operational and accountable GA gates remain pending. Phones remain
disconnected. No native/simulator/emulator run, other project's process, provider,
deployment, credential, publication or frozen hosted lane was changed.
