# Independent review of the proposed private initial profile/header contract

**Verdict: retain as a source/design proposal; require the five root amendments
below before selecting dependent implementation.** The byte map, all-17-budget
comparison, conservative header/reservation formula, source-closure reconciliation
and explicit lack of authority are suitable foundations. The conceptual
signatures do not yet establish every stronger identity/history/exclusivity claim.
This is a contract finding, not a failed Rust implementation: no header or guard
implementation exists or was compiled in this review.

The assigned producer seal is
`aee8ffbe028f9fe3084a62a81fe0946dc6a21cc132e16d83915917cf6657515f`.
All 200 members/23,038,631 bytes verify unchanged. The independent audit also
verifies the root custody and row acceptance hashes supplied with the task,
all 178 nested input snapshots, all 132 archived/current distribution members
and the 131 row-source identities. Archive contents were read only as data.
`commands/run001/custody.stdout` contains exact full member custody; its receipt
binds commands, Python executable/version/hash, source revision context and output.
The producer used path-component tuple ordering for its tree, reproducing
`c96a25ccad0593e316484e39550954e85dd78abb69b12cc7ecc719aeaa4cb754`.
Plain full-relative-string lexical ordering produces
`a2f44f50412386bd1a2bb5d4a83e0690bce670fd800e9fc29a130000fb949e45`.
This ordering distinction is recorded; no member mismatch or producer edit is
inferred. An initial exploratory lexical-order assertion failed on this
distinction before the exact producer order was identified; this was not a
product test failure.

## 1. R1: separate locally derived layout from external build attestation

The proposed `borrow_initial_profile_v1(cache, control, wasi, selected_budget)`
receives an actual cache, control, optional WASI and only a complete budget record.
The proposed guard retains shared borrows of those owners. None of those values
contains selected compiler, target/configuration, source-manifest, executable or
layout-receipt identity. `UnverifiedProfileDigestBytesV1` is intentionally opaque
and caller supplied. Therefore error 6 cannot presently mean refusal of an
unavailable/different **external layout/build identity**. Equal local shapes are
possible in two different builds. Feeding a matching receipt digest, a supplied
boolean, or matching scalar layout numbers into this helper does not verify the
build. Size and alignment measured by the running exact-source build are useful
structural facts, with a separate provenance question.

Root should explicitly select one of these bounded meanings:

- Recommended for the pure helper: error 6 checks only a named complete local
  structural-layout/schema profile, using actual `size_of`/`align_of` and
  root-selected private structural data available through an explicitly amended
  signature or exact immutable source constants. List the producer and complete
  contents of that private data. External source/tool/target/build/receipt
  attestation stays unavailable here and is enforced only by the separately
  selected host verifier/custodian. If no selected local comparison exists yet,
  leave this error unimplemented rather than invent a successful check.
- If error 6 must enforce external identity, add a specifically defined private
  verified-selection input whose sole constructor belongs to an independently
  accepted verifier and whose lifetimes/artifact binding are part of the new
  contract. That verifier does not currently exist. It cannot be replaced by an
  externally constructible record, trait implementation or `verified: bool`.

Neither option embeds an executable's own final hash into that executable.
A build may embed selected structural constants; the external receipt may bind
the final executable. Embedding the exact receipt digest back into the binary
when that receipt hashes the binary creates a dependency cycle. The pure header
may contain opaque externally supplied executable/receipt digest bytes without
creating that cycle or verifying those bytes.

## 2. R2: existing WASI checks establish common control ownership

Frozen cache source `pairing` calls the supplied owner's `checked_usage`;
that method checks the WASI header ticket against the control. Cache
`check_header` checks its own header against the same control. This refuses a
foreign runtime owner and a supplied owner without its real header. The cache
stores no WASI reference or historical instance identity. `None` bypasses the
optional check. A second safely constructed WASI owner from another prepared
phase under the same RuntimeControl can satisfy these checks; nothing in those
checks compares it with the optional instance supplied to cache construction.
`WasiConstructionPhase.constructed` prevents repetition within that phase, not
all future `AccountedWasi::prepare` calls on that control.

No header scalar depends on a WASI instance; the optional borrow supplies actual
diagnostic observations. The bounded recommended amendment is to promise
**common RuntimeControl ownership of the supplied optional WASI**, with no claim
that it is historically the identical optional instance. Preserve `None` as
supported when no observation is supplied. The later typed original-result and
WASI/lifecycle context must bind its actual run owners independently.

If the historical-instance claim is necessary, root must select construction-time
capture of the very optional borrow through a closed private continuation and
retain it through header/row generation. There must be no second independently
supplied optional WASI argument capable of substituting another same-control
owner or replacing Some with None. Do not add an owner integer or external
identity boolean to the cache and call that historical provenance.

## 3. R3: virgin cache shape is not before-first-attempt chronology

The strict stated shape checks are valuable and must inspect actual fields:
slot resident=None, pin count=0, last_used=0; every PinRecord exactly
`nonce=0, entry=0`; every plan None; all 192 index bytes zero; nonce 1; all cache
usage fields except fixed_reserved (including peaks and own active_pins) and
control live cache entries/pins zero. Counting free pins only by nonce
does not by itself prove the exact constructor state. Check actual bounded
lengths/capacities for slots, pins, 512 patches, 192 index bytes and 512 plans.
Safe construction and authentic ticket/layout checks remain prerequisites;
private fault witnesses are defensive cases, not alternate owner constructors.

There is nevertheless a concrete source-path counterexample to chronology.
After successful construction, prepare an operation and call `pin` on imported
absolute index 0. Generic `pin` performs `meter.work(1)` and then fails
`snapshot.function(0)` with `not_defined_function`, before touching nonce,
hits/misses, pins, residents, index or plans. The runtime latches its first
failure. Cache shape and B equality remain exactly initial. Existing
`check_owner` is deliberately cleanup independent and does not consult the
runtime's first failure. A guard implemented only from the stated cache checks
and existing owner preflight could therefore be minted after a real acquisition
attempt. These are source observations and an offline projection counterexample;
the actual Rust path was not executed here.

Root should choose a closed, source-reviewed construction continuation that
mints the guard only after successful constructor/phase completion and before
the cache/control can reach any acquisition call. Its sole call path, allowed
preconstruction owner setup, no-reentry rule and retained borrows must be named
inputs. No returned guard may borrow a moved local owner; the actual owner stays
in its caller's live storage throughout the continuation. A fixed selected helper
can be used without an arbitrary callback or externally forgeable phase marker.
An alternative is a separately selected source-bound history predicate, including
terminal-failure handling; the current proposal defines none. Do not silently
relax “before any acquisition” to “before any successful acquisition.”

Do not require all control work or runtime live state to be zero. Constructor
loops themselves consume `slots + pins + 4800` cache-work credits in the frozen
source. Other state/WASI owners are explicitly permitted. Do not erase,
reinterpret or replace the original typed first failure while reporting a
separate fixed profile refusal. External cancellation/deadline state must not be
used as a guessed substitute for chronology or add an unselected eligibility rule.

## 4. R4: B equality does not prove absence of zero-byte Cache tickets

The exact cache/header/buffer tickets and the aggregate Cache current B can
establish the arithmetic base needed by the profile. They cannot establish the
unqualified phrase “no unrelated Cache-category owner.” Frozen
`RuntimeControl.admit(Cache, 0)` is permitted when existing checks/ticket capacity
pass: it increments the global live-ticket count while leaving Cache current and
combined bytes unchanged. Per-category usage exposes current/peak bytes, not a
per-category ticket inventory. Other runtime/state/WASI owners are allowed, so
the global ticket count does not identify the extra category by itself.

Recommended for this header: state the exact provable invariant, all real
cache-owned header/slot/pin/patch ticket checks plus Cache current==B and
resident=0, which excludes unrelated **positive bytes**. This does not assert
absence of a zero-byte unrelated ticket. If categorical owner exclusivity is
required, include the complete closed adoption/pre-cache/construction call path
and its allowed admission inventory in R3's source selection; immediate
postconstruction timing alone does not exclude a preexisting zero-byte ticket.
Do not invent a per-category ledger, new cap, receipt constructor or global
all-owners-zero precondition in this slice. Final ticket/lifecycle joining is
still a separate real-context requirement.

## 5. R5: bind row derivation to the retained guard's actual cache proof

The accepted writer is `write_profile_row_body_v1(snapshot, output)`. Its actual
owner and File behavior are accepted only in the root record's isolated host
scope. Its signature permits a second valid snapshot. Matching header counts,
body bytes, source hash or any caller-supplied digest does not prove that this
snapshot is the identical owner retained by the initial cache guard.

Root must name a restricted private bridge which takes the initial guard and an
empty output File, obtains the proof from the retained cache internally and calls
the unchanged row writer. It must not take a second snapshot, raw descriptor,
revalidated owner or owner identity scalar. Retain the same cache/control/optional
WASI borrows through all header/row emission. Give the sibling helper only the
minimum restricted access required to derive that proof; do not publish a
general authority getter or allow an independent constructor. The composer must
consume the exact retained File emitted by this call path plus its build-bound
receipt. Python cannot recover a Rust proof from a File or infer owner identity
from a digest; its hash join proves byte equality only. The stable immutable
snapshot-binding record/schema/provenance remains explicitly unavailable until
separately selected, as the producer already acknowledges.

## 6. Positive contract facts and exact future closure

The complete17 field order and maxima match the frozen SwiftRunBudget source.
All 17 must compare to the actual immutable control budget; the header subset
omits thirteen fields, and `min(entries, defined)` can also conceal a difference
in raw cache_entries. Values equal to a historical default record do not establish
root selection or origin. `SelectedInvocationBudgetV1` must have one named private
source producer rooted in the selected complete record. This review selects no
budget. Zero in unrelated limits means exhausted, not universally invalid;
only slots/pins outside 1..64 are unsupported by this existing profile grammar.
Entry_limit=0 and entry_limit>capacity remain meaningful construction/header
cases, provided the canonical ceilings and actual B<=capacity hold.

The frozen current distribution is exactly132 named paths. Four archived
emission inputs differ: generic borrowed cache, Swift cache, control and
cache_tests. Add the root-accepted two row files and its sole module declaration;
the common three C distribution headers remain part of the distribution closure
even though the row Rust compilation did not consume them. The result has at
least134 named paths before new header, construction observer, selected-data,
layout, bridge, test, harness/support and generated compiler inputs. Exact final
names/count/digests and an explicit review of the old analyzer's exact132-count
schema must precede any claim that the new closure qualifies there. No merged
archive/current tree currently has accepted build or semantic equivalence.

Independently recomputed arithmetic agrees with the proposed formulas:

```
H = sizeof(SwiftFunctionCache) - sizeof(ValidatedSwiftReactor)
    + complete_cleanup_inventory + 192 + 512*sizeof(Option<ScanPlan>)
B = H + actual_slots*sizeof(SwiftSlot) + actual_pins*sizeof(PinRecord)
      + 512*sizeof(decode::Patch)
```

Index/plan payload is already in H. Check every subtraction/product/addition and
integer narrowing; derive actual slots=min(selected entries, this proof's defined)
and actual pins=selected active_pins. Verify actual length/capacity and authentic
header/buffer ticket category/bytes/owner before trusting equality. This review
selects no ABI layout values. Fresh Debug/optimized source/tool/target/config-bound
sizes **and alignments**, complete Results, error/argument/caller/return/move
places, private selected-data and borrow owners, File/Metadata/write/composer
transfers, cleanup, loops and simultaneous lifetimes need a complete new proof
under unchanged reservations. The old row11,912/13,904-byte union and450,652,288
source-action-plus-requested-I/O bound cannot be added as allowance or inherited
as VM credits. Retained source/metadata and validation scratch/work remain
separately charged. The analyzer29,344-byte/7,048-group proof also does not cover
new callers or phases.

Pure header encoding is correctly limited to512 field-by-field LE bytes, eight
opaque32-byte claims, 24 reserved scalar bytes and trailing128 zero bytes.
There is no Rust object-image serialization, File, hashing, signing, allocation,
acceptance getter or selection digest in that contract. The row output must stay
empty/offset0 and retains its625 blocks/20,000 calls. A separate output composer
produces2,560,512 bytes; its work/logical places/calls/I/O fault progress and
custody cannot inherit the row writer's bounds. Canonical preimage schemas for
all eight artifacts, a complete build receipt, exact body File/profile subrange
hash joins, retained-descriptor pre/post checks, supported path/custody model and
strict typed original result/15-word final ledger remain separate dependencies.
Matching hashes establish bytes, not immutable custody or source ownership.

The final-selection digest may depend on the complete profile; the profile must
not depend back on that selection. No existing MIXFIX01 echo or literal-false
authority getter changes, even with real-looking hashes. Real context schema,
replay, semantic metrics, CLI, full-target, new CI/compiler/OS, native/physical,
FieldLog/store/operational/GA acceptance remain pending.

## 7. Controls and honest scope

The 48 independent Python methods pass. They exercise design arithmetic and
encoding, all4,096 slot/pin pairs, one-field drift for every budget field,
supported/unsupported count/policy/type boundaries, every plan/index cell,
nonce/counter/length/capacity mutations, digest extents/slot swaps, unchanged
row admission, composition byte algebra, dependency noncycles and the concrete
information-limit counterexamples above. The synthetic values deliberately lack
Rust ownership or authority. Source text witnesses pin the reviewed reasoning to
actual frozen code; syntax checks alone prove neither semantics nor OTA safety.

No product Rust was imported, compiled or executed. No new File writer,
descriptor custodian, actual header authority or owner-lifetime compiler proof
was exercised. No native/simulator/emulator/device/UI/capture/process inventory,
full target, archived fullsuite/103-pack, hosted code, active Android correction
or integration-protocol access occurred. No Git mutation, canonical/other-lane
write, cap/deadline/crypto/dependency change occurred. Python children completed
and were reaped by subprocess.run; no scratch or native instance was created.
All packet files are retained review evidence. Root owns amendment selection,
canonical tracking updates, delivery and any later implementation task.
