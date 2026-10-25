# Exact full Swift reactor after cache reset elision: result

Root selected one unchanged full-target attempt with
`verification/swift-exact-reactor-after-cache/root-selection.json`, SHA-256
`f0e55d46a214a5bedc9fdddf70e249ed84b50a6809f37a94068e1eee59dd35c9`.
The accepted 132-file baseline remains
`b28da766c84b6353a4511e2fc3fbcb0d4302d5b8a5a74da1ee3d7fb776ca2c11`.
The exact fresh executable, driver, byte-identical harness, 53,777,114-byte
reactor, input closure and argv matched the selected hashes. The command was:

```sh
python3 -B verification/swift-exact-reactor-after-cache/diagnostic.py target
```

The sole target exits 101 after 3.944 seconds, without timeout or host signals.
Complete owned validation passes all 79,832 defined bodies, 34 imports and
6,505,659 instructions. It consumes 188,428,924 work credits in 423,812
microseconds, with 1,037,096 metadata bytes, 13,312 peak scratch bytes and
54,827,522 internal peak reserved bytes. The simultaneously live external input
has capacity 53,777,114 bytes; requested-capacity overlap is 108,604,636 bytes,
excluding allocator overhead and RSS. The external input is dropped before
adoption. These are observations from this host diagnostic.

Actual adoption, original-owner construction and Initialize pass. The real reply
is `Initialized`; the owner reaches Ready with 584 pages, 37,328 guest
instructions, 169,017 cache work and 76,359,130 execution work after 14,229
microseconds of cumulative runtime.

Corpus 1 fails with the first real typed resource failure:
`Cache / WorkExhausted / swift_run_work / CacheWork`, absolute function 1356,
source offset 492821, attempted work 64,000,001 against the unchanged limit
64,000,000. Its internal failure snapshot records 3,502,374 cumulative runtime
microseconds, 12,971,689 guest instructions, 13,029,465 fuel, 199,187,565
execution work and 228 WASI calls. WASI records 29,635 work, 3,590 transferred
bytes and 3,556 secure random bytes, with zero log bytes or host failures.
Memory reaches 585 pages / 38,338,560 bytes. Combined requested reservations
peak at 176,292,419 bytes; state reservations peak at 89,161,088 bytes. No budget,
deadline, counter, hook, cancellation or production baseline changed.

Corpus 2 is skipped. Actual guest stdout and stderr remain empty, so no
eleven-field guest/native parity is observed. The final libtest assertion panic
reports the preserved diagnostic failure; it does not replace the first typed
resource failure. Both raw process streams and the pre-cleanup failure snapshot
are retained in `commands/target-once/`.

`phase-counters.json` retains exact cache/work snapshots and arithmetic
increments. Corpus 1 below is its terminal snapshot after failure completion and
drain, at 3,502,459 cumulative runtime microseconds. It is not a separate cache
observation at the internal resource checkpoint.

| Counter | Construction | Initialize complete | Corpus 1 terminal |
| --- | ---: | ---: | ---: |
| Entries current | 0 | 64 | 64 |
| Cache category current bytes | 88,536 | 317,413 | 679,113 |
| Cache category peak bytes | 88,536 | 568,299 | 1,936,515 |
| Fixed reserved bytes | 88,536 | 88,536 | 88,536 |
| Resident bytes | 0 | 228,877 | 590,577 |
| Resident peak bytes | 0 | 479,763 | 1,847,979 |
| Pinned bytes | 0 | 0 | 0 |
| Pinned peak bytes | 0 | 184,388 | 1,238,071 |
| Construction bytes | 0 | 0 | 0 |
| Construction peak bytes | 0 | 97,491 | 491,557 |
| Hits | 0 | 324 | 280,175 |
| Misses | 0 | 135 | 39,433 |
| Completed decodes | 0 | 135 | 39,432 |
| Evictions | 0 | 71 | 39,368 |
| Cache work | 640 | 169,017 | 64,000,000 |
| Execution work | 76,242,475 | 76,359,130 | 199,187,565 |
| Fuel | 0 | 37,345 | 13,029,465 |
| Guest instructions | 0 | 37,328 | 12,971,689 |
| Host calls | 0 | 7 | 228 |

These counters locate the unchanged work ceiling and quantify the observed
intervals. They do not select another cache repair, attribute work to a source
hotspot or justify widening a budget. This result establishes no full corpus,
performance or production memory acceptance.

Original consuming owner cleanup completes. The final `final_cleanup_usage`
records all reservation categories, combined reservation, live tickets and live
categories at current zero, with no cleanup invariant. The separate
`cleanup_reservations_and_live_empty` is true. The unchanged success-oriented
`cleanup_empty` also requires no final failure; it remains false, as does the
raw driver `ownedCleanupEmpty`. The preserved failure's attached
`after_cleanup` snapshot precedes final tail retirement and still shows
270,976 bytes / three tickets. The separate final consuming-cleanup snapshot
records their retirement. `target-once-classification.json` preserves this
distinction without changing the original result.

The exact owned OS process group is proven absent, with no signals. Output
handles close and complete hash reads reach EOF. All bound source, historical
packet, target, tool, harness, driver and executable identities remain unchanged
through execution. The separately labelled child high-water RSS is 155,828,224
bytes; it is not a per-phase ledger or performance gate. Empty holder checks and
path/inode rechecks precede owned scratch removal, reclaiming 77,688,816 logical
bytes. The original 4,692,240-byte executable is retained losslessly as
`bin/exact-tests.gz`, 1,772,139 bytes, SHA-256
`3189c995859677f6a18cc040a5b9aef78e2bbbcc7bfe701977b6195caee0d41e`.
Decompression reproduces the selected executable SHA-256
`7b14683ada146c0158ac20a8e71e162bcdadb2d07b9b64f195787528fb3574eb`.
No retry occurred, and no other process, service or native instance changed.

The preparation document and all prepared members retain their bytes. The
prepared executable has the explicitly recorded lossless compressed
representation after cleanup. `result-receipt.json` and `result-seal.json`
separately bind the actual result, all raw evidence, original prepared seal,
selected command and this result document. Verify the final packet read-only,
without compilation or guest execution, with:

```sh
python3 -B verification/swift-exact-reactor-after-cache/verify-result.py
```

The full target, full SL matrix, guest table mutation, production caller stack/
accounting, public/signed/native execution, memory/size/startup/performance, full
app UI/effects/state/async/actor coverage, source debugger, FieldLog immutable
published packages from a separate repository, physical phones, store/customer/
operational and accountable GA gates remain pending. Phones remain disconnected.
This host-only diagnostic changes no provider, service, publication or credential.
