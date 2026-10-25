# Recorded count-plan Rust rejection independently audited

The sealed finite result is accepted as an accurately recorded **rejection**.
The candidate remains rejected for live integration and a full-target retry.
Three of six complete CacheWork measurements regress, phase turnover regresses,
and the operation requires 20,472 additional reservation bytes under unchanged
limits. The favorable rows do not establish an actual-target call-order shape.
This review does not accept candidate correctness or select policy retuning.

The [independent audit packet](../verification/swift-count-plan-retention-candidate-review/)
contains an executed, read-only Python audit: **23 methods pass, zero failures or
errors** in the final invocation. It checks retained source and execution evidence;
it does not rerun Rust, the target workload, or any native runtime. One initial
audit invocation passed 22 methods and failed one overly literal diagnostic-string
check because rustc abbreviated a source line. That invocation, source and report
remain retained. The corrected check binds the complete existing diagnostic;
no producer artifact was changed.

## Bound source and evidence

The producer seal is exactly
`29601717bcdc4c8a6c1de9c80ab2d26fdcc04c265b799dfa7e07868d541eb8a1`.
Every one of its **114 members** matches its recorded length and SHA-256. The
producer document remains included in that immutable seal. All three archives
contain exactly 132 unique regular files, with safe relative names, and every
member matches its respective manifest. The pristine manifest SHA-256 and the
freshly rehashed live `vm/` closure are both
`16176e0852fa61cba98acebeb373ee1a6be4c686d0e46ef8bbc144c0527c2cbd`.
This is the exact named closure; it does not claim to inventory unlisted files.

| Archive | Manifest SHA-256 |
| --- | --- |
| Pristine baseline | `16176e0852fa61cba98acebeb373ee1a6be4c686d0e46ef8bbc144c0527c2cbd` |
| Instrumented tested baseline | `50fff8c385641cb77c0449d16a3f87064ee87cca2f8dc544af265e0833ab6946` |
| Candidate | `a14988b504a29ff94025b594f7e0e0bb65da7a05b653140a299318808741468b` |

Independent unified diffs reconstructed from the archives match **both retained
patches byte for byte**. The candidate-versus-tested-baseline patch changes only
`src/experimental/cache/borrowed.rs`, `src/experimental/cache/tests.rs`,
`src/experimental_swift_reactor/cache.rs` and
`src/experimental_swift_reactor/cache_tests.rs`. Both Cargo files and the fixed
runtime control/limit source remain byte-identical to pristine. The six-trace
test input bytes remain unchanged in both instrumented archives. All original
Swift tests are byte-preserved except the added passive checkpoint hook.

All **14 Rust command receipts** bind their recorded source-manifest hash, tool
versions/executable hashes, argv, offline environment, stdout/stderr lengths and
hashes, exit status, and unchanged live closure. Eleven commands exit zero. Three
exit 101: two initial compiler failures and the retained original candidate
Swift suite failure. These outcomes are distinct from final audit passes.
The producer used arm64 macOS, Cargo 1.99.0 and rustc 1.99.0; the independent
audit receipt records its own actual Python executable, hash and version.
Command-time source manifests also retain intermediate probe/adapter states;
the three complete archives are the final pristine/tested-baseline/candidate
states, not a claim of intermediate source archives for every invocation.

## Results independently derived from raw streams

Fresh baseline trace records exactly match the earlier historical baseline trace
records. The historical stream hash is checked separately; its libtest timing
and unrelated output need not equal the fresh stream. Work intervals exclude
warm-up work. Decode intervals subtract sixteen warm-up decodes except cyclic65,
which has no warm-up decodes.

| Interval | Baseline decodes | Candidate decodes | Baseline work | Candidate work | Work delta |
| --- | ---: | ---: | ---: | ---: | ---: |
| Hot16 / stream128, four rounds | 576 | 512 | 1,558,624 | 1,461,008 | -97,616 |
| Cyclic65, three rounds | 195 | 132 | 406,583 | 303,416 | -103,167 |
| Expensive hot / cheap cold | 576 | 512 | 248,012 | 150,228 | -97,784 |
| Cheap hot / expensive cold | 576 | 512 | 1,444,044 | 1,460,948 | +16,904 |
| Uniform hot / cold | 576 | 512 | 222,412 | 232,148 | +9,736 |
| Expensive old16 to twelve cheap64 cycles | 64 | 81 | 17,440 | 25,918 | +8,478 |

Every trace reports zero executed guest instructions and peak 73 tickets. The
57 additional source-policy work credits are independently bound to the selected
41+16 schedule: cold work is 129→186, reused work 119→176, and three-victim work
204→261. The unchanged model estimate of eight credits is not the measured Rust
cost. These policy groups do not measure CPU instructions, memcpy, stack or RSS.

The outcome is 32 bytes; both complete outcome and preparation Results are
1,096 bytes. The 25 measured, nonoverlapping inventory fields occupy 6,820 bytes
plus four padding bytes. Independently summing complete field sizes and alignment
gives **6,824 × 3 = 20,472 bytes**. Existing measured inventory/layout values stay
unchanged: DeltaExisting is zero. Operation reservation grows **92,350→112,822**.
The constructor retains five allocation requests, 54,976 allocated bytes and
4,928 work credits in the selected fixture. No persistent policy payload or new
ticket is present in the source change or implemented layout report.

Both copies record **256 resident hits, 2,048 work, zero allocation requests and
zero allocated bytes**. The eleven actual checkpoints preserve work, order,
cache bytes, tickets, pins and entries. The first pre-admission checkpoint is
identical. At every admitted checkpoint the candidate construction and combined
reservations are 20,472 bytes higher: construction 361,966→382,438; combined
487,257→507,729. Hit work/allocation parity is supported; hit-byte parity fails.
Baseline operation admission succeeds at headroom 92,350 and 112,821; candidate
fails both before allocation and succeeds at 112,822. These are memory
regressions under the unchanged combined-byte limit.

The 109 complete generic records are independently extracted and compared:
one layout, six IR access, six resident/pin/statistics states, 94 work-failure
prefixes and two cancellation records. Both normalized streams have SHA-256
`a20b0adffab19d110bedd958fe0a9950e5f4ed4ab86e428f29258fafd92cb9a5`.
This supports the recorded selected generic differential, not all generic uses.

## Failure and ownership evidence

The actual finite Rust oracle exercises capacities zero through 64. Capacity zero
tests rejection; the other 64 capacities each execute 384 transitions, yielding
**24,576 transitions per mode**. Its source independently models direct-mapped
plan collisions, cold/reused timestamps, empty-slot choice and lowest-slot ties,
then compares actual slot identity, pin count, zero priority, inserted slot and
relative victim order after every operation. This does not compare absolute
work-counter timestamps against model ordinals. A separate independent Python
enumeration confirms the deterministic finite input/model states and records
state-stream hashes; it is explicitly not a fresh VM oracle replay.

Retained raw output plus assertion-source inspection support all shorter cold
and reused work allowances (baseline 129/119; candidate 186/176), every selected
cancellation checkpoint (baseline 74/67; candidate 76/69), and three individual
allocation-failure ordinals on each path. Candidate completed-scan/later-failure
counts are 111 cold and 176 reused. Real three-victim pressure observes completed
eviction prefixes **0, 1, 2 and 3**, with the opaque held pin and its instruction
allocation preserved. Reused-path eviction totals 1/2 include its seeded eviction.
The selected controls include four immutable identity/count corruptions, original
count-plan collisions, a malformed real scan with no published plan, and actual
all-pinned rejection. Their consuming cleanup assertions check zero combined
bytes, tickets, resident entries and active pins.

Source review confirms that the resident-hit branch contains a literal copy of
the original publication tail; the new helper/outcome/debit runs on the miss
path. The 41-credit charge precedes cold plan publication. Successful complete
scan publication can survive later capacity, planning or build failure. The
16-credit preparation and its error cleanup precede resident-index insertion;
an attempted built owner is dropped on preparation/insertion failure. Earlier
evictions are retained as completed prefixes. There is no whole-miss rollback,
and sticky failure prevents retrying a terminal runtime using a retained plan.
The operation phase enlarges existing construction reservation before creating
its phase and uses the existing consuming completion boundary. This source
reasoning supplements the retained finite execution evidence; it is not a
general proof of candidate memory or behavioral correctness.

| Recorded Rust suite | Baseline | Candidate |
| --- | --- | --- |
| Original generic private | 5 pass | 5 pass |
| Public generic cache | 9 pass | 9 pass |
| Public generic allocation | 1 pass | 1 pass |
| Original Swift cache | 39 pass | **37 pass, 2 fail** |
| New finite selection | 8 pass | 9 pass |
| Unchanged common trace methods | 3 pass | 3 pass |

Two separate prospective layout commands each pass one method. The new finite
counts include their generic differential and the candidate's implemented
inventory test; do not add these again as new Rust methods. The original
candidate failures are `plan_reuse_observation` (expected 288 decodes, observed
225) and `reset_elision_observation_fixture` (expected timestamp 5,027, observed
zero). Their assertions remain intact. Both panics occur before consuming cleanup;
neither is a zero-ledger cleanup receipt. The initial unavailable scan-result
helper method and nonexistent `AllPinned` variant compile failures are also
retained; their adapter fixes do not remove an original behavioral assertion.

Old16 phase decodes stay 81 after either twelve or 64 cheap64 cycles versus 64
baseline. Old64 turnover, including deliberate plan-collision turnover, remains
128 versus 64. These adverse controls remain part of the rejection.

## Cleanup, limitations and disposition

The historical cleanup preflight and removal receipts bind the same scratch
path, device and inode and record synchronous-child completion. The owned scratch
path is independently absent now. No process discovery was performed, so this
review makes no fresh process-list claim. It starts no Rust child, compiler,
native instance, capture or background process and creates no extracted source
tree. It does not read/import/execute the frozen hosted catalog inspector,
authority driver, or rejected Worker V2. Root-owned concurrent metadata and other
lanes are outside this review's write scope. The producer and both frozen model
packets remain immutable and rehash correctly.

There is no evidence-integrity finding requiring producer correction. Preserve
the measured rejection and its limits. Actual-target call order, full-target
benefit, live integration, native/device/UI/capture execution, compiler/signing/
store/provider/customer/operational acceptance, immutable published FieldLog
consumption and all specified final/GA acceptance remain pending. Neither the
finite Rust passes nor this offline audit promote a GA gate or authorize OTA.
