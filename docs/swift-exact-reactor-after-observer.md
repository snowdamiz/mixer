# Exact full Swift reactor after observer repair

This separate host diagnostic follows root acceptance of the test-only release
observer repair. The previous one-attempt packet at
`verification/swift-exact-reactor-diagnostic/` remains sealed and unchanged. Its
initialization panic at `assertion failed: ordinal < 64` is historical failure
evidence. It does not establish a production VM failure or target success.

The accepted 132-file VM closure is
`f2682c6a2fd6f6e74bd00a2394ff32b704aa1e2ed3d2373ef95cdee29fa7eb2c`.
Only `frame_operations_tests.rs` differs from the prior diagnostic baseline. Root
accepted the zero-mask observer bypass and three owner-backed regression tests;
production VM behavior and budgets remain unchanged. See
`verification/swift-release-observer-root-review/{source-review,receipt,integrated-manifest}.json`.

The new packet at `verification/swift-exact-reactor-after-observer/` copies that
baseline into owned scratch, appends only the private test include, and builds a
fresh Release test executable. The diagnostic harness is byte identical to the
old selected harness: SHA-256
`d72da7bc7aaf4e31b7093fde497f357226d3a4dd954eb577909209102a0bfb00`.
Historical source/compiler/native artifacts are bound by file hashes as data;
no historical driver, native reference binary or Node oracle is executed.

The exact target remains
`compiler/experiments/fieldlog-reactor/local/2026-10-23-qualified/wasm/fieldlog-reactor.wasm`,
53,777,114 bytes, SHA-256
`24d85729a659ff3e5fc6f0517709afbb68b371a41829e90785dabd48e0620994`.
It contains the original full Swift/Foundation/Codable/Unicode/throwing model.
The driver independently checks all eleven native observation fields, types and
values against the qualified historical stdout. It also binds the archive,
model, wrapper/corpus, descriptors, compiler receipts and native object/module/
binary hashes. No substitute corpus or runtime supplies target credit.

The unchanged harness requires complete owned validation, drops its external
input before adoption, constructs one original owner, requests Initialize
(function 35) once, and requests Corpus (62) twice with consuming completion
barriers. Each corpus result must be i32 zero and its actual stdout suffix must
be one complete duplicate-free eleven-field object matching the native output.
The driver independently parses both suffixes. Runtime counters, memory and
stdout remain cumulative between calls; each corpus builds a fresh local
Workspace, so equal output does not prove persistent feature state.

Validation uses the original default 120,000 ms deadline and ceilings. Runtime
and WASI share their original cumulative 30,000 ms deadlines and ceilings. The
outer target limit is 170 seconds, with at most five seconds TERM grace and five
seconds KILL wait for its exact owned process group. No budget, deadline,
counter, hook, cancellation or production source is changed. The first typed
failure and actual raw outputs remain evidence; dependent phases short circuit.
Original retained frame/growth cleanup and consuming owner cleanup remain the
only in-VM cleanup authority.

The derivative Python driver adds an atomic one-attempt marker and saves raw
stream identities and failure/process observations before host cleanup signals.
`killpg(..., 0)` EPERM or another OS error is unknown unless a successful,
completely parsed `ps` observation of the exact PGID proves presence or absence.
Malformed, failed or timed-out `ps` remains unknown; it cannot pass cleanup or
permit scratch deletion. Signals target only the process group created by this
driver. Ten host-only controls cover normal presence/absence and the EPERM,
malformed, nonzero, stderr, timeout, expired cleanup envelope and other-error cases. Command records bind
source, tools, argv files, harness/driver snapshots, outputs, timings and cleanup.

Preparation and small synthetic wiring controls do not execute the real target.
Root must bind the exact fresh executable, harness, driver, inputs and argv in
`root-selection.json` before the sole target attempt. The proposed outer command
is:

```sh
python3 -B verification/swift-exact-reactor-after-observer/diagnostic.py target
```

The fresh Release build, both small wiring controls and ten final host-only
process observation controls pass. The earlier nine-control receipt and original
build remain preserved across the Python-only timing refinement; no executable
rebuild occurred. Root selected the final exact command in
`root-selection.json`, SHA-256
`7a31a9677335ced9527e80b75a119b88b5ba6138cc472a8b8d00a8ba6d61897e`.
The selected driver is SHA-256
`f1e42a9bd4c9e36d6b61c3c33f509ac1ca2e26e83fdb87bee19e02abbb68c231`;
the fresh 4,651,344-byte executable is SHA-256
`1aa8b50867c604e83ac7b91de36704cc137d2ab1818f6c6beb6698e5decf6e43`.

The sole selected target exits 101 after 2.815 seconds, without timeout or host
signals. Complete owned validation passes all 79,832 defined bodies, 34 imports
and 6,505,659 instructions. It consumes 188,428,924 work credits in 468,556
microseconds, with 1,037,096 metadata bytes, 13,312 peak scratch bytes and
54,827,522 internal peak reserved bytes. The simultaneously live external input
has capacity 53,777,114 bytes; their requested-capacity overlap is 108,604,636
bytes, excluding allocator overhead and RSS. The external input is dropped
before adoption.

Actual adoption, original-owner construction and Initialize pass. The real reply
is `Initialized`; the owner reaches Ready with 584 pages, 37,328 guest
instructions, 307,257 cache work and 76,359,130 execution work after 18,846
microseconds of cumulative runtime. This establishes initialization for this
selected host diagnostic after the observer repair.

Corpus 1 fails with the first real typed runtime resource failure:
`Cache / WorkExhausted / swift_run_work / CacheWork`, absolute function 593,
source offset 344732, attempted work 64,000,001 against unchanged limit
64,000,000. The failure occurs after 2,310,772 cumulative runtime microseconds,
7,360,483 guest instructions, 7,381,922 fuel, 178,656,205 execution work and 140
WASI calls. WASI records 18,019 work, 2,182 transferred bytes and 2,148 secure
random bytes, with zero log bytes or host failures. Memory reaches 585 pages /
38,338,560 bytes. Combined requested reservations peak at 176,292,419 bytes;
state reservations peak at 89,161,088 bytes. These are diagnostic accounting
observations, not production memory or performance acceptance.

The terminal cache snapshot records 24,054 completed decodes, 24,055 misses,
148,116 hits and 23,990 evictions, with 64 entries retained. The counts locate
where the unchanged work ceiling is reached; they do not select a cache repair
or justify widening a budget. Corpus 2 is skipped. Actual captured stdout and
stderr remain empty, so no eleven-field guest/native parity is observed.

The exact cache/work snapshots and arithmetic increments are retained in
`phase-counters.json`. The last column is the terminal Corpus 1 snapshot after
failure completion/drain; it is not a separate cache observation at the internal
resource checkpoint. All values below are direct observations:

| Counter | Construction | Initialize complete | Corpus 1 terminal |
| --- | ---: | ---: | ---: |
| Entries current | 0 | 64 | 64 |
| Cache category current bytes | 88,536 | 317,413 | 622,720 |
| Cache category peak bytes | 88,536 | 568,299 | 1,936,515 |
| Fixed reserved bytes | 88,536 | 88,536 | 88,536 |
| Resident bytes | 0 | 228,877 | 534,184 |
| Resident peak bytes | 0 | 479,763 | 1,847,979 |
| Pinned bytes | 0 | 0 | 0 |
| Pinned peak bytes | 0 | 184,388 | 1,238,071 |
| Construction bytes | 0 | 0 | 0 |
| Construction peak bytes | 0 | 97,491 | 491,557 |
| Hits | 0 | 324 | 148,116 |
| Misses | 0 | 135 | 24,055 |
| Completed decodes | 0 | 135 | 24,054 |
| Evictions | 0 | 71 | 23,990 |
| Cache work | 640 | 307,257 | 64,000,000 |
| Execution work | 76,242,475 | 76,359,130 | 178,656,205 |
| Fuel | 0 | 37,345 | 7,381,922 |
| Guest instructions | 0 | 37,328 | 7,360,483 |
| Host calls | 0 | 7 | 140 |

From Initialize completion to the terminal Corpus 1 snapshot, cache work rises
by 63,692,743; execution work by 102,297,075; guest instructions by 7,323,155;
fuel by 7,344,577; host calls by 133; hits by 147,792; misses by 23,920;
completed decodes by 23,919; and evictions by 23,919. Resident bytes rise by
305,307 while the retained entry count remains 64. These differences quantify
the observed interval and do not attribute work to a source hotspot.

The harness completes the original consuming owner cleanup. The final
`final_cleanup_usage` has every reservation category, combined reservation,
live ticket and live category at current zero, with no cleanup invariant.
`cleanup_reservations_and_live_empty` is true. The original CacheWork failure
remains in `final_failure`; its attached `after_cleanup` snapshot precedes the
last tail retirement and still shows 270,976 bytes / three tickets. The separate
final consuming-cleanup usage records those remaining construction/shared
reservations retired. The unchanged success-oriented `cleanup_empty` predicate
also requires no final failure, so it correctly remains false, as does the raw
driver `ownedCleanupEmpty` field. The original result is unchanged;
`target-once-classification.json` records this distinction explicitly. The final
assertion panic merely reports the preserved typed diagnostic failure.

The owned OS process group is proven absent with no signals. Every bound input,
historical packet member, source, compiler/sysroot, harness, driver and executable
remains unchanged. The separately labelled child high-water RSS observation is
155,729,920 bytes; it is not a per-phase ledger or memory/performance gate.
After empty holder checks and path/inode recheck, owned scratch is removed,
reclaiming 77,624,710 logical bytes. The selected executable is retained as a
1,752,141-byte gzip, with its original executable hash above. No other process,
service, provider or native instance was changed. No retry was attempted.

`receipt.json` summarizes the observation; all raw outputs, snapshots, first
failure, process cleanup and source/tool/command bindings remain in the packet.
`seal.json` binds every retained member and this document. Check it read-only,
without compilation or guest execution, with:

```sh
python3 -B verification/swift-exact-reactor-after-observer/verify.py
```

The full SL matrix and guest table mutation, production caller-stack/accounting,
public/signed/native execution, memory/size/startup/performance, full app UI/
effects/state/async/actor coverage, source debugger, FieldLog immutable published
packages from a separate repository, physical phones, store/customer/operational
and accountable GA gates remain pending. Phones remain disconnected. This
host-only diagnostic does not run native UI or physical/emulated devices and
does not change provider/service state, publishing, credentials or shared gates.
