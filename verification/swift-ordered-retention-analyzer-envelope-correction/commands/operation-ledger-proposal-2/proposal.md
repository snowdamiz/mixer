# Fixture-envelope correction proposal

This packet corrects the private poison scheduler and proposes a complete source-operation accounting amendment. It does not qualify the current historical128/192 constants. The original796-member producer,64-member accounting review,646-member public review, proposal1 and69-member correction-accounting review remain immutable. Main engine/CLI, custody, binary report fields, semantic metrics and release authority are unchanged.

The corrected private `leaf_pending` refuses both retained status3 and retained reason15 before any later leaf call. A complete status1/reason15 reply therefore has the same poison priority as finalization. The leaf uses safe fixed-range reads/staging/commit; its one arena-length check and sized2048 candidate prove all twelve exact8-byte destinations before mutation. No raw pointers, dynamic per-record owner, allocator, I/O or callback were introduced. Two authored regressions are retained but have not yet been executed against a selected numeric contract.

## Proposal2 and current limits

`verification/swift-ordered-retention-analyzer-envelope-correction/commands/operation-ledger-proposal-2/` is the separately frozen review handoff. Source SHA256 remains `e86ef43a99f99245c78308666f91f5147981859ca03fa3f97e62d46993667535`; the531-line accepted framing prefix is unchanged. The operation ledger retains at most16 named bounded scalar operations **or** one actual fixed transfer/copy of at most128 bytes per group. Each whole16-byte handle transfer has its own copy group. A single source-to-destination edge is charged once for work; both complete places are counted for storage while they coexist.

| Proposed subdivision | Groups |
| --- | ---: |
| Private leaf upper | 425 |
| Added ordinary-record wrapper W | 24 |
| Accepted framing subdivision | 22 |
| Combined atomic B | 471 |
| Separately prepaid underfunded guard G | 112 |
| Outer setup wrapper T | 42 |
| Complete finalizer/typed projection finish | 47 |
| Outer final wrapper F | 42 = base29 + early-error13 |
| Retained main setup charge | 534, actual source upper329 |

The425 bound is a conservative actual-source upper, not a mathematical minimum or proof that no tighter implementation could fit128. No numeric amendment has been selected. Source constants still contain historical leaf128/W42/B192/G36/T20/finish8/F44. Those constants do not pay for the revised source and must not be replayed as qualified accounting.

Mandatory8192 preflight remains; proposed B471 leaves7721 credits of preflight margin, which is unused rather than assigned to hidden work. New fixed setup576 fits the unchanged65,536 setup cap. Complete finish47+guard112+outer F42 reserve201 report credits; unchanged fixed report work can charge up to6245, for6446 within the existing3,000,000 report reserve. IO263,584, total268,435,456 steps, arena8,388,608, transient65,536 and transient reservation41,984 remain unchanged. Budget construction still withholds all IO/report reserves before replay admission. No full4,194,304-record observation or native/CPU performance claim follows.

## C1: every finalizer execution has an explicit prepaid owner

Proposal1 assigned every finalizer/project operation to finish47, but input observation may fail before that charge. Correction-accounting finding C1 identified the exact early source upper: E01 classification/entry2 + E09/project10 + E10 return1 =13 groups. Proposal2 adds exactly those named13 groups as F05 in outer `F_wrapper`, raising29 to42. The outer report reservation succeeds before output safety, arena allocation, Progress initialization or any input observation. It therefore dominates every actual call to `finalize`.

On **every returned input Err**, F05 owns E01+E09/EH03+E10. This includes initial/context/profile/header/setup errors and later record/drain/footer/EOF/metadata failures. Complete finish47, if already paid, stays unused with no refund. On **input Ok**, finish47 owns E01–E10, and F05 stays unused. Successful `observe_inputs` requires successful walk completion; the walk's setup and finish reservations precede candidate initialization and every record. Thus input Ok implies both reservations succeeded. These assignments use existing input-result control flow; no new Rust flag, field, argument or hidden owner tracks them. Credits from either inactive branch are never used by another block.

The proposed public cumulative counter is:

`envelope_debit = 534*S_paid + 47*F_paid + 425*N_B`

`S_paid` and `F_paid` are mathematical indicators for successful main setup and complete-finish reservations; `N_B` counts successful atomic B471 charges. `F_paid` is distinct from outer `F_wrapper42`, which never enters the public envelope counter. Each successful B contributes425 even if decoding/framing later fails, the leaf is skipped after refusal/poison, or the final observation is suppressed. A private underfunded leaf reply retains private debit0; any already paid main425 remains in the cumulative counter. G112 is reserved before candidate mutation and can execute at most once because Steps latches Refused.

A main setup failure leaves counter0; successful setup followed by failed finish leaves534; successful setup+finish followed by failed guard leaves581. Such returned input errors yield Unavailable and the fixed framing-derived reason, with every state/coordinate/extent field zero and truthful cumulative debit retained. Successful zero-call complete or limited framing remains absent: Unavailable/EnvelopeUnavailable, all extent fields0, debit581. Successful limited drain with a reply retains only a partial fixture extent and never calls normal non-CAP finish. Incomplete/failed drain does not establish a complete or partial observation. Output-safety/allocation/write/postwrite outer errors return no aggregate. The exhaustive call-order/funding table is frozen with proposal2.

## C2: complete type and storage evidence

All six affected complete unit/walk Result edges in BR01/BS01/BP01/S01/S03/F03 now name actual40-byte `Result<(),AnalyzerError>`, while the contained `AnalyzerError` remains32. Each complete transfer still fits one copy group. The exact independent32-declaration probe and raw output are carried into proposal2: unit/bool/u64/Arena Results40, Budget Result64, Stamp/Fixture Results80, aggregate/Result232, Progress144, Reply/Observation128, Framing80, Reader48, Metadata144 and metadata IO Result152.

The complete edge inventory records source and destination widths; larger aggregate transfers retain their entire232-byte owner while their work copies are split128+104. The memory inventory keeps all accepted framing/Reader/metadata/Stamp/report roles and the conservative composed24,656-byte role upper within41,984 reserved bytes. New word8, complete StepBudget source/local, all range/slice/Option/Pair values and caller/return places are explicitly mapped to existing helper leases. Final source lifetime qualification remains pending independent review; this is no physical stack/RSS/compiler-elision claim.

Proposal2 carries the accountant's exact seven-operation inherited framing22 crosswalk, accepted source hash, accepted ledger document and seal. Loop, mandatory preflight, single atomic Budget call, decoded128 backing/Reader call, offset arithmetic, field/profile join and Framing coordinate retain their accepted boundary. All typed-leaf access, progress/latch/reply handling, new setup/report calls and aggregate/error edges are separately mapped. The changed Budget operand requires explicit numeric selection.

No cost-dependent full replay has run. Historical producer64 passes and16,170 oracle cases are evidence for the original source, not this corrected packet. The independent original64 timeout remains unqualified. After independent accounting review and root numeric selection, a fresh bounded direct-Rust producer replay, actual-value layouts, first-failure retention, upstream preservation checks and owned-child cleanup are required. Native/capture/UI/device/runtime/hosted lanes remain paused or out of scope.
