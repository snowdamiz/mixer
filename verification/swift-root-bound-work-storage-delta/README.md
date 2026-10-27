# Root-bound work and storage delta preparation

This lane prepares the finite pricing prerequisite for the accessible-result
original-root lifetime repair. It is **source/MIR inventory only**. No layout,
work price, payload-backing bound, whole-host funding, full ownership, forgotten
root funding, runtime, native, FieldLog, OTA or GA acceptance follows.

The candidate is exactly source146
`91bab68a8aef4a7cbe300af0fca8145462e08dcaaef2631f42a0d2d55748bd8f`,
under the released implementation seal SHA-256
`7efe39286257be85d0e91f4bdd80b6098d24d7d2f446dcdc2e8dd7adb0159fa4`.
The baseline is the frozen IR01 retirement correction, source146
`c3a33b76eef6bf9ad86ef1cb0320e94bcefa5a0609ec1a30872a9d83371bd0db`.
Only `retained_profile_loader_v1.rs` and `cache/initial_profile_v1.rs` differ.
The two source manifests are compared; the two changed sources plus unchanged
generic child source are read and checked against their frozen packet members.
This is not a new all146-source custody replay.

## Concrete delta and accounting boundary

`delta-inventory.json` contains exact hashed source spans for 16 type declarations
(including the explicitly unchanged-field `OriginalCorrelationRefusalV1`
relocation), 24 handwritten/dependency function bodies and 24 separate
compiler-emitted constructor/shim occurrences. The function inventory includes
the producer's 38 new-type items and ten additions: original-root accessor, two
scope functions, six existing child-account/destruction/token bodies, and the
old leaf helper as a relocation donor. Duplicate emitted constructor/shim
occurrences are retained individually and do not imply duplicate runtime calls.

Every selected argument, return/local declaration and non-comment MIR statement
has an exact archive item/line hash and an explicit positive obligation mapping.
The candidate mapping includes 65 arguments, 580 local/return places and 2,873
rows. There are 2,084 comparable baseline rows. The selected candidate rows
include three actual closure capture fields, 30 drop-tagged rows, 48 cleanup
blocks and 97 unwind-tagged rows; categories overlap. These are finite coverage
counts. They are neither dynamic instruction counts nor byte floors or peaks.
Exact selected baseline function spans are independently checked against the
baseline full item roster and gzip. No source or MIR regeneration ran.

The 24 obligations are defined in `contract.py` and copied into the inventory:

| Work obligations | Storage obligations |
| --- | --- |
| W01 scope/root accessor | S01 association/root field representations |
| W02 root-aware correlation/branch wrapping | S02 generic bound representations |
| W03 complete File facade/selected moves | S03 selected/correlation representations |
| W04 existing fixed leaf sequence, rebound | S04 fixed frame/fixture/result places |
| W05 complete fixture envelope assembly | S05 admitted payload/child representations |
| W06 short shared observation/scalar copy | S06 actual anonymous dispatch closure |
| W07 admitted wrappers/dispatch captures | S07 shared views/scalars/parent places |
| W08 existing setup/loader work, rebound | S08 original selected/error/File backing |
| W09 destruction and unwind instantiations | S09 setup/fixture/leaf/shared backing |
| W10 existing child token protocol, rebound | S10 IR01 acquisition backing/sticky charge |
| W11 existing outer ordering, rebound | S11 drop/unwind simultaneous storage |
| W12 private pair partition, test calls only | S12 independent child token/parent storage |

Each obligation remains `UNRESOLVED` for price and layout/backing bound. Existing
means an explicit dependency to rebind to the new actual source/context. It does
not carry a numerical quote or layout forward. The IR01 source contract already
requires new owner/call/capture/return accounting; this inventory adds the
root-bound-family delta without reinventing the upstream callee accounting.
All nine new-place classes in the independent frozen `source-review.json`, and
all 13 finite producer private-transition sites, map to this inventory.

The concrete distinctions matter:

* Both association inputs gain an original-root reference. All core success and
  refusal returns use the consumed attempt's root. The foreign expected input
  supplies a comparison, never output-root custody.
* `RootBound`, selected wrappers, raw variants, File reconstruction locals and
  fixture/admitted wrappers need new representations and transfer/drop work.
  `AdmittedFixtureOutcome::Loaded` also contains the nested bound root; an enum
  layout must be observed rather than inferred from the number of references.
* A root reference has representation cost. It does not own/fund the original
  proof/source backing, selected/error or io-error storage, File owners or OS
  resource state, rows/snapshot, shared Cancellation backing, claims or leaf
  results. Those remain separate carried-backing obligations until final
  destruction, including partial setup refusal and unwind.
* The actual closure fields are fixture by value, attempt by value and expected
  by shared reference. The captured attempt contains the original root field.
  A captured-field sum is not an observed anonymous closure layout.
* The existing scope/adopt/construct/outer/finish work moves from the old cache
  match/helper to the fixed synchronous loader frame. W04 rebinds that call and
  its new argument/return/frame contexts. It does not charge a second leaf
  invocation or invent another allocation from each move.
* Short `primary`/child views borrow complete live payloads. Child destruction
  consumes the complete payload before returning a child-only reservation
  token. It does not confer acquisition-refund authority. Ordinary Drop and
  panic return no release token.
* After any scope issue, IR01 retains the full acquisition charge. The accessible
  root relationship does not prove durable funding after `mem::forget`, useful
  joint retirement or shutdown. Those remain separate pending obligations.

The type declarations have implicit field/variant drops. Retained selected MIR
contains drop terminators and cleanup edges, but does not provide every
monomorphized standard-library/drop-glue body or its cost. W09/S11 explicitly
retain this limitation. MIR `StorageDead` does not certify backing destruction.
No sum of all 580 slots is asserted to be a simultaneously live peak.

## Offline executable evidence

The final inventory is reconstructed with:

```text
python3 -B verification/swift-root-bound-work-storage-delta/check.py
```

`check.py` verifies frozen membership/hash pins, the exact two-file source delta,
selected source/MIR spans, all actual closure capture fields, complete finite
mapping and explicit claim limits. It streams each authoritative gzip once,
hashes every uncompressed byte and retains only selected bodies in memory.
The candidate archive is 4,140,573 bytes / 84,594,785 uncompressed bytes; the
baseline archive is 3,849,862 / 85,605,256. No complete source146/MIR copy is
created. The 210,000,000-byte input ceiling includes these streams; the checker
has a 25-second CPU bound and the single Python child a 35-second wall bound.
`commands/` receipts record the actual tool/source/output hashes and cleanup.
`run_offline.py` created the producer receipts before sealing; a reviewer should
run the read-only checker above and retain fresh output in its own lane.

Fifteen in-memory adverse controls require rejection of a lost root field,
type, function, local, unwind row or review class; wrong source/MIR/baseline
binding; false closure ownership; zero/invented price, layout or funding claim;
changed input hash; and duplicate-leaf implication. These are inventory integrity
controls, not independent Rust lifetime/compiler or funding tests.

Two exploratory checker failures preceded the recorded successful builds: an
ambiguous `usage_v1` selector also matched the unchanged account usage method,
and a closure-line source anchor used the enclosing function name rather than
the actual closure expression. Both checks were narrowed to exact pinned
contexts. Build/build-2 receipts preserve successful intermediate inventory
revisions; build-3 and check are the final checker revision. No frozen source or
prior lane changed, and no compiler retry or product test occurred.

## Smallest next layout frontier, not executed

`layout-probe-proposal.json` specifies one bounded compiler-only invocation with
the retained rustc 1.99.0 aarch64-apple-darwin identity/environment. The two
proposed named fragments cover 28 unique new boundary/aggregate shapes, once per
type; unchanged scalar/callee rosters and test-only generic pair
monomorphizations are excluded. This is the minimal next frontier relative to
that explicit roster, not a claim of global minimality or complete storage
qualification. It deliberately avoids replaying a broad prior layout harness.

The third fragment preserves the actual dispatch closure expression, binds it
locally and proposes two concrete source-size diagnostics for its own
`MaybeUninit` shape and a `repr(C)` leading-byte wrapper. This actual-closure
diagnostic strategy is **unexecuted and unqualified**; the proposal requires
exact concrete diagnostics and refuses absent/ambiguous observations. It never
accepts a proxy capture sum. All named/closure query fragments are diagnostic
scratch proposals, with intentional compiler errors; they are not product
engine source and have not been inserted, compiled or run.

Root must separately release any compiler lane and review the runner/source
delta before a later query. This packet starts no compiler or layout query,
native/runtime test, simulator/emulator, UI/capture, network request, hosted
work, stopped Androidv5/callbackUnitA work or process inventory. Only bounded
offline Python ran. No product metadata, old prices, gates or other lane files
were edited. Independent review and all price/backing/peak/funding acceptance
remain pending.
