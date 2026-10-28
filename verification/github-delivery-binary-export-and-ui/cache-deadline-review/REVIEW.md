# Corrected second cache campaign: actual runtime review

The corrected second campaign is closed with the milestone unmet. Both permitted full attempts failed during the first corpus call; neither produced a complete native-oracle result, and neither began the second corpus. The GitHub workflow succeeded because the finite diagnostic campaign completed and preserved its observations. Its green status is not host feasibility or product acceptance.

## Identity and selection

- Run: `40755988137`, attempt 1, manual dispatch, job `123054909834`.
- Selected head: `56ff14c925168284761c5aca4f0bd4129cf3c995`.
- Selected tree: `75989099938ed5256c4144cbc9e62979ee323183`.
- Artifact: `12845123804`, 85,455 bytes; SHA256 `4ee27b6c875eaaa9f0d43bcb667ee0a5e82463d7e00059dbea4e843ac2a23fae`.
- Safe bounded extraction: 61 files, 345,946 expanded bytes. No artifact code was imported or executed in this review.
- Correction seal: `d6bf688b0b1333bb10a5c946c14febedbbdac463a884d446da9f5460b66ebdde`; all 18 sealed files rehashed.
- Selected driver SHA256: `77ab5079e7e818d551b3c77f7b56b15babdb1dea521151a80643e9fad259763c`.
- The prior finite-failure review remains unchanged, including seal SHA256 `c15eb4a779600d78adcb2b7e99bbe24c30bfed38d6cf3e087e431134a10457a8` and its 45 named files.

Git objects at the selected commit join the reviewed driver and workflow. Actual profile manifests and deltas equal both sealed correction source checks and actual preflight manifests. The original 53,777,114-byte Wasm input was independently decompressed and rehashed to `24d85729a659ff3e5fc6f0517709afbb68b371a41829e90785dabd48e0620994`. The original oracle retains all 11 typed fields.

The remote tool receipts identify Rust 1.99.0 (`b940084d7`, LLVM 23.1.1), Cargo 1.99.0 (`5f94df478`) and Python 3.12.3 on Linux x86_64. Both optimized builds retained overflow checks, used locked offline compilation, and joined one compiler executable to the finite, harness and full commands. The job log records 19 passing pure source/decision controls.

## Actual execution

| Observation | Primary | Conditional |
| --- | --- | --- |
| Profile | 256 residents / 64,000,000 CacheWork / 60 seconds | 256 residents / 128,000,000 CacheWork / 60 seconds |
| Generated source SHA256 | `c68fb260b6e282f4c6245ad074d01978d17aa79a155d3688654a0585d711e3d7` | `fe4e9bd1b05938988c858ec228d95f54f93e662f07d5426c440743bcb9a16c87` |
| Finite controls | 4 passed, 0 failed | 4 passed, 0 failed |
| Harness control | 1 passed, 0 failed | 1 passed, 0 failed |
| Full exact target | 0 passed, 1 failed; exit 101 | 0 passed, 1 failed; exit 101 |
| First failure | `WorkExhausted`, `swift_run_work`, `CacheWork` | `FuelExhausted`, `swift_run_fuel`, `InstructionFuel` |
| Attempted / limit | 64,000,001 / 64,000,000 | 100,000,001 / 100,000,000 |
| Runtime at failure | 41.736968 seconds | 44.335205 seconds |
| Full command wall time | 42.820089 seconds | 45.415002 seconds |
| Guest instructions | 89,506,650 | 99,059,182 |
| Metered instruction fuel | 90,341,527 | 100,000,000 |
| CacheWork consumed | 64,000,000 | 70,883,119 |
| Execution work consumed | 647,084,442 | 684,238,606 |
| Corpus result | Corpus 1 failed; corpus 2 not begun | Corpus 1 failed; corpus 2 not begun |
| Complete native-oracle outputs | 0 | 0 |

Both profiles validated the full input, constructed an owner, initialized it once to `Ready`, then became `Terminal` during `corpus_1`. Both use the original cumulative runtime/WASI clock origin. The 100-million instruction-fuel limit, one-billion execution-work limit, 64-frame and active-pin limits, validation limits, memory limits, and host grants remain unchanged. The full command timeout was 200 seconds; neither timeout nor cancellation occurred. The driver bound was 540 seconds and workflow job bound 15 minutes.

The primary meets every selected condition for the second attempt: exact CacheWork exhaustion, actual counter at 64,000,000, valid original-linked attribution, original cause preserved, unchanged source/input observation, consuming zero-resource cleanup, normal child exit 101 and proven absent child process group. The conditional attempt is therefore within selection. It reached the original instruction-fuel limit, so another deadline or CacheWork increase alone cannot make this exact execution finish under the current fuel policy.

At corpus failure both profiles had 1,006 completed decodes, 485 distinct decoded functions and 521 repeated decodes; the cache reported 750 evictions. This does not by itself establish that a cache algorithm change will solve the guest-instruction limit. Raw attribution is retained for the required architecture comparison.

## Cleanup and custody

Both final consuming cleanup observations have zero current retained-source, retained-metadata, cache, state, WASI, shared, construction and combined reservations; zero live tickets; and zero cache entries, active pins, frames, values, controls and memory pages. `cleanup_invariant` is null. The raw `cleanup_reservations_and_live_empty` event is true.

`cleanup_empty=false` is correct here: the harness includes absence of a retained original failure in that boolean. Both exact original runtime failures are preserved in `final_failure`. Its intermediate `after_cleanup` snapshot is followed by the consuming `final_cleanup_usage` observation that releases shared and construction ownership. The preserved failure is not evidence of leaked resources. Nested historical validation/WASI accounting remains diagnostic history; the authoritative final reservation and live ledgers are zero.

All 11 started/terminal receipt pairs join by argv, cwd, environment, actual PID and timestamp. Every child has a non-placeholder exit status, `processGroupEmpty=true`, no signals, no timeout and no cancellation. Only the two full targets exited 101. Output digests match the raw files. The final custody record has 11 proven-closed commands and no pending command; owned scratch removal is recorded true. No additional attempt, local runtime, native runtime, compiler, process-custody probe, UI, capture or dispatch was performed by this review.

## Decision and limits

The independent offline verifier passed 335 checks. Accept this as an accurately preserved failed campaign with verified cleanup and bounded custody. Do not promote a profile, mark full host feasibility, accept a second-corpus result, or mark a GA gate verified.

The next required action is a fresh Astra architecture comparison of algorithm change, resource-policy change and a different implementation, with a named executable discriminating test and finite bounds. Preserve this baseline and all active holds. The two permitted full attempts are consumed; this review authorizes no replay, extra numeric profile, fuel increase, compiler/runtime run, or new preparation-only chain.

Generated sources and executable bytes were removed with remote scratch. The retained evidence joins generated source manifests to sealed selected manifests and remote unchanged-source checks, and joins recorded binary SHA256/size to compiler paths and all invoked test commands. It does not permit independent local binary-byte rehashing. Raw wait4 RSS is retained, but the common launcher high-water floor prevents a VM-attributable per-profile RSS comparison. Physical-device, simulator/emulator, signed OTA, immutable published FieldLog-package, customer, operational and GA evidence remains pending as applicable.
