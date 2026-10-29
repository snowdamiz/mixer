# Focused bitmap semantic integration review

**No blocking source-level semantic finding within the unchanged canonical
contract (0..64 active pins).** This review supports the root's integration
decision for the exact selected candidate; it is not runtime acceptance
or authorization to install or release it. Independent Release review remains required.

Selected seal file SHA-256: `0210ab9c252c6f7a5a3eff077e36c2811c79351d916d78b75b2cda88e2bdf85c`
(24 members). Selected 136-source closure:
`e9282e05cea70d4aceaf6a145fb9f971acb023dd41a7d4651216753666305ba1`;
canonical preimage closure:
`af0db424af7b08f013d2c6a8894f4d156f76bc5f493620c6f2c0b85d3bf4c48b`.
Root supplied revision `32ef6faf0ac876bedd86481e14e06fe6136dbdbf` and Git tree
`5949fe3208cb4b2187462fba52d6a7e658e18223`; this lane did not run Git.

## Production semantics

- **Selection and boundaries:** `dense_allowed_pins` is total for zero, 1–63,
  64 and invalid lengths. Acquisition rejects lengths above 64, tail bits and
  bitmap/live-count disagreement before reserving a pin. A nonzero mask selects
  its lowest set bit and verifies that exact record is vacant; zero availability
  checks for orphan vacant records before returning pin exhaustion. No shift by
  64 is reachable from accepted selection or release. These are internal
  consistency defenses, not a claim to detect arbitrary coordinated corruption.
- **Reservation and publication:** the selector does not consume a free bit.
  `acquire_pin` precedes resident lookup/scan/build, and every error from the
  existing acquired path invokes `abandon_pin`. The record write, bitmap clear,
  pin creation and nonce advance are adjacent and infallible. A selection,
  reservation, work, cancellation, decode or publication rejection cannot newly
  consume the free slot or advance its nonce. Existing permissible cache/work
  observations on failures remain subject to the original accounting contract.
- **Release and token custody:** header provenance and `checked_record` retain
  owner, slot, nonce and resident validation. New release validation precedes the
  fallible active-pin ledger removal. Rejection returns the original pin without
  clearing its record or restoring its bit. Success then updates the existing
  usage/resident counts, clears the record and restores exactly its bit. No new
  checkpoint, work debit or stop poll enters release or consuming cleanup.
  Consuming owner cleanup drains records and destroys the entire bitmap owner;
  it does not need to rebuild an availability word that cannot be used again.
- **Admission/accounting:** the bitmap scalar is held in the whole cache/Partial
  types already used by owner/transfer accounting; the extra scratch borrow is
  reflected by existing type-based formulas. Three named `DensePinInventory`
  copies are added to construction, operation and permanent cleanup envelopes.
  Initialization charges one credit before setting the word. Successful
  selection charges five credits before any publication; the full path charges
  the defensive record walk. Lifecycle changes match these operations: initial
  work 5,066; first corpus 5,406; repeated corpus 5,430; bounded no-op init 5,027.
- **Other modes and limits:** default sealed hooks preserve the original literal
  first-free loop and its per-record work; publication/release defaults are
  no-ops. The private Swift implementation supplies the bitmap overrides. The
  control source still matches its baseline hash: all 17 defaults, 64 resident/
  pin/frame ceilings, 86 tickets and 256 MiB combined bytes remain. The
  supported active-pin capacity is 0..64 inclusive; zero admits no pins. Above
  64 records the helper yields zero, acquisition rejects with
  `swift_dense_pin_mask`, and release rejects with `swift_dense_release_mask`.
  This implementation does not support a 128-pin array. The separate historical
  experimental 512-resident / 128-frame-pin profile is outside the supported pin
  range and was not requalified or accepted by the canonical 0..64 tests. Its
  experimental evidence and holds remain separate. The reviewed constructor
  helper output slot is test-only and adds no public ABI.

Production anchors in the candidate: `borrowed.rs:438–468,654–675,703–775,785–917`;
`cache.rs:45–82,299–367,1086–1174,1230–1250,1490–1586,1610–1748,1821–1935,2091–2102,2167–2218`.
Unchanged control anchors: `control.rs:20–60,1215–1265,1614–1629`.

## Preexisting accepted-limit boundary

The conclusion relies on enforced admission, not merely default values. Original
canonical `control.rs` is byte-identical to the selected candidate manifest
(`d31fc8429ce3f72e689c3e40581dbd319aa6d36f456263da141ad905ed108aad`).
`RuntimeControl::adopt` calls `check_budget` at `control.rs:559–591`, before
owner allocation or reservation admission at `605–641`. The check takes
`SwiftRunBudget::default()` as the maximum at `670–671`, compares active pins
at `698–702` (maximum 64 from `47–50`), and returns
`InvalidBudget / swift_run_invalid_budget` when attempted exceeds limit at
`759–769`. Cache entries and frames are separately checked at `693–711`.
The control budget and adopted tickets are private fields (`344–347,371–390`);
`budget()` returns a copy (`775–777`). Replacement helpers at `301–330` are
`cfg(test)` fault injection, not runtime configuration.

The original cache constructor already requires that control and sealed adopted
proof: original `cache.rs:1436–1443,1473–1486,1755–1764` checks their provenance,
then reads `control.budget()` at `1818` and sizes pins at `1841–1852`.
It has no independent raw-budget constructor. The original generic selector
(`borrowed.rs:740–749`) mechanically walks whatever slice an internal source
variant supplies, but a valid canonical adoption could not supply a 128-pin
cache. Both original and selected candidate reject a runtime budget of 65 or 128
active pins during adoption, before cache construction; the candidate's added
mask guard therefore does not remove an accepted canonical configuration.

The historical larger experiment is an explicit source variant. Its pinned
selection is `verification/github-delivery-dense512-completion/selection.json`
(SHA-256 `a556842c1a7579d72260baa518b8a4397249d7db33580696026b488e99265873`),
which selects generated source `066789f44a39300a33e7583ab039086589576e3c8701ecfdd19dc4717ebab567`
and disclaims default/production/GA acceptance. Static source trace:

- `swift-dense512-completion-experiment/candidate.py:45–53` delegates to
  `swift-cachework-128-experiment/candidate.py:49–71`, which changes copied
  control limits, resident/ticket/array capacities, and `cache_entries` to 512.
- That delegates to `swift-frame-pin-admission-candidate/candidate.py:31–65`:
  lines 39–44 change copied defaults from 64 to 128 pins/frames and frame arena
  capacity; lines 50–65 replace the one-word bitmap/storage with two-word
  `[u64; 2]` storage and separate helper/mode method source.
- Completion `campaign.py:173–178,425–438` generates those bytes, records their
  identity, and materializes an isolated scratch crate. Its workflow invokes this
  campaign at lines 37–48. These are source replacements before compilation,
  not a larger runtime parameter accepted by the canonical engine.

The separate experiment's historical Linux result remains its own evidence. It
does not qualify this one-word candidate at 128 pins, and this review neither
invalidates that frozen experiment nor treats its generated implementation as
canonical. No historical packet or workflow was executed or changed.

## Coverage inspected

The seven new tests at `cache_tests.rs:4638–4931` exercise the actual cache owner:
allowed masks and unchanged admission policy; all 65 capacities including zero
and bit 63; lowest-hole reuse with constant 12-credit warm-hit cost and no
allocation; tail/occupied mask rejection and release-token retry; existing
allocation/work/cancellation/provenance sweeps; release after terminal
cancellation; and geometry/admission/consuming cleanup. Reused failure sweeps
derive their bounds from the candidate's successful operations and assert ledger
cleanup, so they include the new constructor/selection boundaries. Geometry
checks consume the changed type formulas and preserve the 86-ticket/combined
ceiling assertions. Their runtime success is not inferred from source inspection.

The existing preparation reports 689 guarded source/data checks; it was read,
not rerun. This lane checked only inspected-input identities, including the four
candidate source files against their sealed member hashes and unchanged control
against its baseline. It did not repeat the consumer inventory or full closure
preflight. Twenty-one inspected inputs and exact hashes are recorded in `receipt.json`.

## Acceptance limits and custody

Independent Release run `40828181211`, attempt 1, was reported queued/running
by root; this lane neither polled it nor consumed an accepted Release result.
The prior actual Debug/formatter/Clippy results are parent-supplied context only.
No subject/compiler/runtime, Git/gh/network, Node oracle, native/UI/capture/phone,
process inventory/held probe, SDK repository/release/tag, credential, customer,
publication or memory-write action was performed. Canonical promotion remains
root-only after independent actual evidence. All existing holds remain. No
processes or test instances were started; no process cleanup was needed.
