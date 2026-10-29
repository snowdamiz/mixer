# Lifecycle accounting correction candidate

The two failures in actual hosted run **40806119805** come from the unchanged
lifecycle fixture's old pin-scan prices. This packet proposes one test-only
overlay. It does not change the bitmap implementation, a production default,
the runtime profile, or any lifecycle resource envelope. Corrected Rust
execution, independent review, formatting and lint remain pending.

## Preserved actual failure

The original candidate closure is
`4f9968797133b17520e5387e8ea9870bad779159968357cd31c50abbeb8c8bbd`.
The saved actual source manifest agrees with all 136 of its members. Actual
Rust 1.99.0 (`b940084d7eb6a299eb4bfeb8e34901bc051e7ac4`, Linux x86_64) passed
the seven focused methods, 46 cache methods, 43 frame methods and five Frozen
methods according to the parent result review. The fifth Cargo command failed:
465 passed, two failed, zero ignored, in 331.42 seconds. The sixth Cargo command
did not run. This packet binds the actual fifth-command output and compiler
identity directly; it does not rerun or replace the independent actual-result
review or treat the earlier subsets as a complete pass.

SL13 failed its first cache-work assertion at lifecycle_tests.rs:954 with
actual 4,894 and expected 4,893. SL14's cache-boundary subcase failed the common
success helper at line 291 with “actual operation did not complete.” The raw
output does not reveal SL14's structured failure object. The diagnosis below is
the deterministic source explanation for the stale budget; a corrected actual
Rust run must still confirm the complete behavior.

Raw artifact 12868935321, SHA-256
`1452097cd405aa96a1facdd53bbd3fcf8a83affb5bb1b5735f35277e21ad1d26`,
stays in the sibling actual-result lane's local directory. Its hashes and the
original stdout/stderr are bound in `baseline-bindings.json`; raw CI is not
copied into this packet.

## Source mechanism and exact arithmetic

The frozen Swift cache constructor charges one credit immediately before
publishing `partial.free_pins`. It still charges each entry, pin record, patch,
resident-index cell and scan-plan cell as before. The lifecycle module has 29
defined functions, so its constructor costs:

`29 + 64 + 1 + 512 + 192 + 512*8 = 4894`.

The formerly reviewed generic 64-entry constructor's 4,928→4,929 change is the
same mechanism with 64 entry slots instead of 29; it is not the lifecycle
fixture's absolute value.

`SwiftMode::available_pin` charges three credits for inventory validation and
two for selected-record validation/eventual mask publication. Successful
selection is therefore five credits at both slot zero and slot one. The old
Frozen/default hook still charges one per scanned pin record. The private
Swift hook is reached before the existing cold-or-hit branch. Neither that
branch nor release adds a further bitmap work charge. Consequently each cold
call's old `108 + P + 2*B + 3*I + 13` expression retains all non-pin terms and
replaces only `P` with five. The existing resident-index and scan-plan work is
unchanged.

| SL13 point | Old increment | New increment | New cumulative total |
| --- | ---: | ---: | ---: |
| Construct | 4,893 | 4,894 | 4,894 |
| Initialize35, B14/I6, slot0 | 168 | 172 | 5,066 |
| First corpus62, B7/I3, slot0 | 145 | 149 | — |
| Nested callee36, B19/I9, slot1 | 188 | 191 | 5,406 |
| Second corpus, two warm hits | 8 + 9 | 12 + 12 | 5,430 |

The expected cumulative deltas are +1, +5, +12 and +19. These are algebraic
consequences of the bound charge sites; they were not copied from successful
runtime outputs. The existing 8→12 first-slot hit and 260→264 full-chain hit
expectations in the frozen cache tests are consistent with the same +4 price
change. Their files remain byte-identical in this packet.

SL14 uses the unchanged no-op initializer B2/I1. Its new cold cost is
`108 + 5 + 2*2 + 3*1 + 13 = 133`, and its exact cumulative initialization
boundary is `4894 + 133 = 5027`. The old 5,022 cap is five credits below this
required amount, so it cannot complete initialization under the unchanged
checked cumulative meter. This explains why the existing `success` helper
panics before the intended later-call failure assertions.

The correction changes this test-only cap and its two matching ledger
assertions to 5,027. It retains successful initialization exactly at the cap,
then expects the later corpus request to fail with CacheWork while instructions
remain one and cache work remains 5,027. The checked meter rejects a positive
charge exceeding its limit without committing the increment. No slack is
added: 5,026 cannot complete initialization and 5,028 admits the next one-credit
charge, so both fail the intended exact-boundary arithmetic control. There is
no per-call reset, replenishment, retry, workaround, ignore, or relaxed assertion.

## Scope and candidate composition

`candidate/vm/src/experimental_swift_reactor/lifecycle_tests.rs` is the sole
new overlay. `baseline/vm/` retains its exact original file;
`lifecycle-tests.diff` records all edits. Thirteen exact substitutions affect
only comments and cache-accounting expressions/literals in SL13 and the cache
subcase of SL14. Guest module construction, guest bytes, calls, assertions,
cleanup, execution-work subcase and absolute-deadline subcase are preserved.
All original lifecycle test names and their order are preserved.

The fresh 136-member combined closure is
`674242606ec1f81e8bf53d6d10c0ae390c94c75e78d0a5c0e695bfb36b5eec20`.
Materialize each exact path in `manifest.json.materializationPaths` only after
checking its `candidateFiles` size/hash. Three upstream bitmap overlays are
referenced byte-for-byte; this packet supplies the fourth lifecycle-test
overlay. The 132 remaining canonical files and all 17 `SwiftRunBudget` defaults
are unchanged. Runtime lifecycle/frame code and its full accounting envelopes
are unchanged. No public/signed profile is added or modified.

The three upstream seals are bound and every listed member was rehashed:
producer `290909956b188ed46c73c2c73541c8ed60a80788f0d51f9adbca0940579a54f2`,
independent `84b2cc15c97f951d850904a733ec747fbbb0b17ee23fe8f0b19a8da285c5dfaa`,
corrected harness `f44236c30b0a789b86171d864cf997537d7055a4a32543243854871081b2ab3f`.

## Guarded controls and remaining work

All 12 focused pure control groups pass on Python 3.14.8, with zero failed,
errored or skipped groups. They check frozen bindings, complete baseline and
candidate closures, actual failed-source identity, unchanged workload and test
coverage, source charge sites, independently computed deltas, exact-boundary
negative controls, cumulative no-refill semantics, all default fields, unchanged
host cases/caps and denial of live APIs. `offline_guard.py` installs before
implementation/test imports and denies nested processes, session/group/signal/
wait/socket operations. These supporting controls are not Rust semantics,
native behavior, a performance measurement or release authority.

The first pure run passed 11 groups and failed one because its independently
computed intermediate cold values were 149/191 while a report/control literal
had been mistyped as 148/192. Both pairs sum to 340. The Rust overlay's formulas,
all cumulative totals and its source closure were already correct and did not
change. The first output, result and exact test script are preserved, and the
subsequent literal-only correction is recorded in `preparation-history.json`.

Root must review and explicitly rebind the host admission to the fresh closure
before any new run. This packet selects no dispatch or retry and changes no
runner/workflow. Preserve the existing six Cargo commands, order, filters and
300/300/180/180/600/600-second limits, seven-child maximum including compiler
identity, 2,500-second active/60-second cleanup bounds, 8MiB per stream and zero
whole-reactor attempts. All-feature Debug and Release must execute without
excluding the two repaired tests. The original failed result remains a failure.

No Git/gh, compiler, Rust/Swift/Elixir/product runtime, native/UI/capture,
process inventory or held-process probe was performed by this lane. No child
test instances or scratch processes were created. Protected hosted.yml,
store.ex and .wrangler were not edited. All specified local custody holds,
old fetch, Unit A, broad hosted and remote FieldLog 40802230894/PGID2424/PID2621
remain untouched. No canonical integration, OTA, published-package FieldLog,
native acceptance or GA gate is claimed.
