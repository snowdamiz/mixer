# Absent-state envelope correction proposal

This is a new, unselected isolated fixture proposal for the confirmed R2 failure. No corrected Rust candidate has been compiled or run. Independent accounting and root selection of the new guard ownership must precede execution. The historical producer, behavior failure and final accounting packets remain immutable.

The proposal freezes only this document and the new proposal directory under verification/swift-envelope-absent-state-correction. It changes no engine, CLI, CI, parent analyzer, public API, ABI, binary report or root plan/status/gate file. All replay, stored-prefix, semantic-metric and GA acceptance flags remain false.

## Exact scope and source

The baseline envelope is SHA-256 7b8237abbaec492e595508eb7456dab38fbb0d92d8d3cd5a88184f7c1082b9d1; its parent analyzer is 1ef11e06678642231f783fea0e5fe376e8b1912730a6fb696a653ab04cb2043b. The baseline producer seal is 4ddff8237bd49cab9f6191be89e4764966e1af5dfa686bb931ac1372d1e98df1 (306 listed members, 44,895,898 bytes).

The binding root addendum requires absent state to return InternalPoisoned/debit0 before checking the private threshold. The numeric selection 199dfa75b024d04eeef28f2f40165115797a0bbb3d09a2405426172d8339867c changes that threshold from128 to425; it does not change absence priority. Confirmed R2 is 8ccca728cc7523b2f0622db35dea665327d5e8bc7179e21dca01818f6bd56098, with the behavior seal ee8b9ec9ef3b894e6bc40036aa8951528401414933097849f0c2e4a8aa879cff (118 members, 2,032,748 bytes). Final accounting seal 929593356ebb871f4089e04ad1b71d216880d90a3da5151a5421c50553b985e8 (248 members, 43,000,105 bytes) supports the previous bounds while withholding combined acceptance.

Only two source replacements are proposed. The arena length check moves before all private StepBudget accesses and returns poison0 unconditionally on unreadable backing. The spent check and underfunding threshold follow it. The caller debit validator is factored to accept the existing paid425 form and the two explicit zero-debit forms below. The exact source, patch, old/new replacement text, input hashes and source spans are in [source-binding.json](/Users/andreyyurlov/Documents/dev/mixer/verification/swift-envelope-absent-state-correction/proposal-1/source-binding.json). Only the minimal envelope and parent source files are copied; upstream archives and complete packets are directly referenced.

For arena lengths0/32 and credits0/1/424/425/426, the source now proposes ten poison0/spent0 returns with the entire remaining budget, existing arena and candidate unchanged. This is a source proposal, not a new behavior receipt. The original four funded negative controls remain failed historical evidence.

## Funding and dispatch selection requested

The selected amounts are proposed unchanged: leaf425, W24, B471, G112, T42, finish47 and F42, with setup534 and the existing global caps. Existing G112 authority covers the underfunded prior-state/Steps guard. Root must explicitly select its expanded ownership for one terminal unpaid leaf among absent backing at any remaining amount, nonzero entry spent, or present-state underfunding. A numeric fit does not itself select this ownership.

| Terminal leaf path | Named source ownership | Proposed G groups |
| --- | --- | ---: |
| Absent backing | L01 receiving/readability subset9 scalar operations; L14/RH02 complete poison call/helper/return | 1+6=7 |
| Readable backing, invalid entry spent | L01 receiving/readability/spent subset13 scalar operations; same complete poison return | 1+6=7 |
| Readable backing, underfunded | Conservative complete L01/L02/L03/L04/L14: 2+3+96+1+10 | 112 |
| Readable backing, funded | Full leaf425 owns L01..L14, including its precharge checks | 0 |

The unchanged walk reserves G112 before candidate and prior initialization and before every possible leaf. A failed G admission returns before those mutations; paid setup534 and finish47 remain paid, and existing outer F05 owns the input-error finalization. No inactive branch credit, public debit refund or unassigned memory margin is used.

Main B471 already prepays W24 and leaf425 before decode/framing/optional leaf execution. W02 owns dispatch, W03–W05 record/budget construction and arguments, W06 complete reply installation and reply_valid1, W07/W08 validator handling, and W09 any audit-failure poison construction/install. Those caller operations are paid independently of the private reply debit. G or leaf owns the L14 leaf return into received exactly once; W06 owns the distinct received-to-progress transfer.

An actual guard result is status3/reason15 or status2/reason1. Installation occurs only after a complete return. The corrected coherent zero form passes the validator; inconsistent forms become poison under already-paid W09. Either terminal tag makes unchanged leaf_pending false on every later record. A guard after earlier successful observations still runs at most once. Repeated direct private fixture controls are not claimed funded by one G.

Every successful main B keeps public425 even when the private reply debit is0, decoding/framing fails, or a later leaf is skipped. The formula remains 534*S_paid + 47*F_paid + 425*N_B and paid zero-call setup plus finish remains581.

## Debit validation and malformed forms

The accepted debit forms are exactly:

1. spent425, remaining0, reply debit425: the existing paid predicate, whose meaning is unchanged.
2. spent0, reply debit0, status3/reason15: remaining is unrestricted, including funded425/426.
3. spent0, reply debit0, status2/reason1, remaining below425: actual present prior-state Steps refusal.

All other budget/debit combinations fail the audit and install paid poison425 without changing the truthful public main debit. In particular zero Observed, funded Steps0, mixed zero poison tags, nonzero spent contradictions and wrong debit values fail closed. A raw private funded426 normal call may leave1; the unchanged orchestration always supplies exactly425, so its paid caller audit still requires remaining0. Invalid entry spent returns private poison0 but remains inconsistent with the caller budget and is replaced by paid poison.

This function audits debit coherence. State shape, closure and phase remain checked by the existing finalizer. Poison markers still stop scheduling and suppress all extent before state dereference. Actual reply helpers set reserved words14/15 to0; the debit validator does not inspect those words or state fields. Fabricated paid malformed forms retain the exact existing stage-specific behavior: mixed poison markers latch and suppress extent; other invalid tags/state fail finalization. A fabricated paid status1 with a nonzero nonpoison reason is outside actual helper provenance and may remain schedulable under unchanged leaf_pending; this proposal does not claim that debit_valid alone certifies that fabricated form. Canonical poison0 with fabricated nonzero extent/reserved words still latches and projects zero extent and false authority flags. The [truth table](/Users/andreyyurlov/Documents/dev/mixer/verification/swift-envelope-absent-state-correction/proposal-1/validator-truth-table.json) states these limits explicitly.

## Source accounting and complete lifetimes

The baseline final ledger has116 rows (6b7206d61440775f568d983b0aa2473d96eed1d0838c91a4035cc59fb9a9845a), and108 fixed transfer edges (8be91fc764715a227deba3459a7c53ec8804195f4e98cb7f8097fb636f1e0e46). The new [precise delta](/Users/andreyyurlov/Documents/dev/mixer/verification/swift-envelope-absent-state-correction/proposal-1/ledger-delta.json) authenticates each unchanged row, replaces L01/W08, removes the two prior validator rows and supplies seven scalar-only validator rows. Reconstruction yields121 rows and the same108 transfer edges. Historical source line annotations are baseline coordinates; the exact replacement text resolves new coordinates.

L01 keeps25 operations/two groups in a new order. The validator uses a maximum over actual mutually exclusive terminal paths, with explicit per-block rounding:

| Validator path | Rows | Groups |
| --- | --- | ---: |
| Paid return | DV00 + DV01 | 2 |
| Inconsistent unpaid return | DV00 + DV02 + DV02R | 3 |
| Poison reason return | DV00 + DV02 + DV03 + DV04 | 4 |
| Steps expression or rejection | DV00 + DV02 + DV03 + DV05 | 5 |

DV00 has7, DV01 has15, DV02 has15, DV02R has2, DV03/DV04 each10, and DV05 has25 scalar operations split as10+15. Each scalar group contains at most16 named bounded scalar operations. Each call follows exactly one terminal path; W08 reserves its5-group maximum, and explanatory child rows are not charged again. No compiler elision or assumed scalarization supplies this bound. Existing actual fixed transfers remain at most128 bytes per group; complete source and destination memory places remain counted.

No type declaration, named local owner, aggregate, borrow transfer, allocation or callback is added. The underfunded boolean starts later. The same private128 reply,144 Progress,232 aggregate/Result and complete40-byte unit Results remain fixed. Existing debit-validator128 helper storage covers its two native references, boolean source/return/caller and scalar/index/control temporaries. The existing936 leaf subroles remain within1152, and240 walk subroles remain within256.

One retained Candidate2048 and payload888..983 stay fixed. All twelve prior/stage/commit ranges remain byte-identical; the same exclusive arena slice and length survive through commit. The guard returns before prior/word initialization, arena reads or candidate writes. Logical named groups remain Candidate2048, Control6656, IO1472, Metadata2400, Report4296, Setup5168 and Wire2616: total24,656 within41,984 reserved and65,536 ceiling. The23,552 margin remains unassigned and unused. These are source bounds, not fresh compiler layouts, physical stack/RSS or CPU qualification.

The source/control-flow derivation and arithmetic checks establish a reviewable proposal. They do not substitute for independent actual-source accounting, execution, cryptographic release admission or a GA gate.

## Pending evidence and custody

The [test plan](/Users/andreyyurlov/Documents/dev/mixer/verification/swift-envelope-absent-state-correction/proposal-1/test-plan.json) requires the ten absent controls, exact length boundary, present underfunding priority, a finite validator matrix with malformed/reserved/extent cases, actual installation/latch/finalizer controls, paid B/public counter failures and skips, full present-state regression/oracle checks, complete layouts and API controls. These are planned only. Root must first select the exact source/funding contract after independent review.

Proposal preparation uses standard-library Python hashing, JSON, byte comparison and arithmetic plus git version/revision metadata. Owned subprocess commands have45-second deadlines, separate sessions, exact argv/version/source/output receipts, and kill/reap only their own child on timeout. No Rust compilation, candidate runtime, old producer harness import/execution, hosted inspector, native/UI/capture, physical run or process discovery occurs. No executable/native scratch is created; no unowned process is touched. Native and device checks remain pending under the pause, and phones remain disconnected.
