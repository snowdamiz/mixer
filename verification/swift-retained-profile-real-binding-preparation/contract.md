# Proposed real retained-profile binding contract

Status: **root selection required; preparation/data controls only**.

## 1. Established scope and the next decision

The binding product scope remains `mixer-product-plan.md`, especially owned
implementation, original diagnostics, immutable artifacts, exact runtime/build
compatibility, resource controls, FieldLog and evidence-based gates. PLAN/STATUS
do not narrow that scope. This packet owns only this new verification directory.

The accepted private initial construction/header/row source tree is
`71a00fde8a43aef5a7e6104932d3f0ca10a5989fb686c99828937b05aa363c7c`
in the 3,830-member producer packet, with completed 1,045-member independent
review and root component acceptance
`77287c9659d8033450571f0a1aef4ccb02eacc513999cd6fdaa34f7746431a71`.
That acceptance includes exact selected host configurations, original result
ownership, and source-object/lifetime accounting. It does not include real input
binding or integration. The older accounting receipt's production foundation
number is corrected by the root addendum; use 269,080 production /269,616 unit,
71,200/71,688 submitted headroom, 197,880/197,928 submitted source union and
330,960/331,496 source-derived prepared bounds. The separate unit-only
331,496-byte, one-ticket quarantine is never healthy zero.

Root accepted the exact C01/R03 finite host correction in
`retained-composition-stdio-host-acceptance.json`, SHA
`d5326f39cf49f796149fea2ebb7f0e602f6dd7df202c9540a82891bec20d823e`.
Its producer/independent seals are
`c79bd64dc0019c17f03b17df0a6bd5dc8879334d64fbf74f92507d75a5e81f54`
and `a10b46f06b54e3bd3e940c7cf403cac7f80faed4814347f2c38616ab447006e1`.
The prototype source is exactly
`af8d04f4940bca83c341d72970ef088852e27919305cda7aa7d53396ea2d2ccf`.
Its 32-attempt/512-byte read boundary and once-only raw-owner cleanup are
preserved: a completed 32nd read succeeds; a short nonempty 32nd read without
complete request or EOF refuses; there is no 33rd read. Child exit, process
reaping, directory removal, descriptor-number reuse and retries cannot retire
uncertain close/name obligations. The original 659/340 packets and required old
failures remain immutable. This does not accept complete real composition.

Three concrete choices need root selection before source implementation:

1. **Provenance carrier and privacy:** recommend a private selected-validation
   wrapper which captures the actual validation budget and loader/build/session
   provenance, transfers that sealed sidecar into the private `AdoptedProof`, and
   keeps the public `ValidatedSwiftReactor` layout/API unchanged. Its diagnostic
   adoption path must share the original admission/cleanup implementation. A
   new field in the public proof is an alternative with a wider layout/schema
   migration. Neither shape is currently selected or implemented.
2. **Real byte schemas and result overflow:** recommend the fixed layouts below,
   a separate retained complete typed constructor/extra-cleanup receipt, and
   strict refusal on unsupported codes/fields/receipt overflow. Root must select
   exact schema/discriminant/code-applicability tables and real source/build
   count closure. No Debug parser or silent truncation is acceptable.
3. **Implementation scope:** recommend isolated source promotion of only the
   accepted 140+11 baseline plus the exact roster, with independently prepared
   privacy/lifetime/typed-result controls. Keep actual analyzer authority and
   historical full-target execution in a later separately reviewed slice.

## 2. Exact current producer and consumer interfaces

Paths prefixed **accepted/** below mean the released
`verification/swift-initial-profile-construction-implementation/source/vm/`
tree, not canonical promotion. Exact input hashes/excerpts are in
`source-evidence.json`; source line references describe those frozen bytes.

| Role | Actual file / interface | Current limitation |
| --- | --- | --- |
| Complete validation | canonical and accepted `src/experimental/swift.rs:367`: `pub fn validate_swift_reactor(input: &[u8], budget: SwiftValidationBudget, cancellation: &Cancellation) -> Result<ValidatedSwiftReactor, SwiftValidationFailure>` | Consumes a caller slice. There is no retained-File loader, session/build handle or original validation-budget field in the returned owner. |
| Validator implementation | same file `fn validate(input: &[u8], budget: SwiftValidationBudget, cancellation: &Cancellation, started: Instant) -> Result<ValidatedSwiftReactor, Failure>` | Original exact source allocation/copy occurs here; successful owner has six fields source/metadata/policy/imports/usage/observations. It does not attest artifact origin. |
| Runtime adoption | accepted `src/experimental_swift_reactor/control.rs:559`: `pub(crate) fn adopt(proof: ValidatedSwiftReactor, budget: SwiftRunBudget, started: Instant, cancellation: Cancellation) -> Result<(Self, AdoptedProof), SwiftRunFailure>` | Moves the authentic proof and captures validation usage, but cannot reconstruct the five original validation limits from that usage. |
| Adopted owner | same file: `pub(crate) struct AdoptedProof { proof: ValidatedSwiftReactor, source: ReservationTicket, metadata: ReservationTicket }`; `proof(&self) -> &ValidatedSwiftReactor` | No build/session provenance. Original tickets/control remain authority. |
| Cache preparation | accepted `src/experimental_swift_reactor/cache.rs:1473`: `pub(crate) fn prepare<'a>(control: &'a mut RuntimeControl, wasi: Option<&'a AccountedWasi>, adopted: &AdoptedProof, cursor: Cursor) -> Result<CacheConstructionPhase<'a>, SwiftRunFailure>` | Authentic owner and construction accounting, not a selected artifact loader. |
| Construction/completion | same file: `CacheConstructionPhase::construct(&mut self, adopted: AdoptedProof) -> Result<SwiftFunctionCache, CacheConstructionFailure>` and `complete<T>(self, returned_phase_storage: T) -> Result<(), SwiftRunFailure>` | Returned storage and rejected adopted proof must follow actual cleanup; observational drop cannot refund tickets. |
| Initial profile wrapper | accepted `src/experimental_swift_reactor/cache/initial_profile_v1.rs:113`: `fn construct_with_initial_profile_v1(cache_out: &mut Option<SwiftFunctionCache>, control: &mut RuntimeControl, wasi: Option<&AccountedWasi>, adopted: AdoptedProof, selected: &SelectedInitialProfileV1, claims: &UnverifiedProfileDigestBytesV1, row_output: &mut File) -> InitialProfileConstructionOutcomeV1` | All eight claims are copied unverified. There is no exporter or provenance parameter. |
| Guard/header | same module sole `InitialProfileBorrowV1<'a> { cache: &'a SwiftFunctionCache, control: &'a RuntimeControl, wasi: Option<&'a AccountedWasi>, scalars: InitialProfileScalarsV1 }`; header submodule `encode_profile_header_v1(initial: &InitialProfileBorrowV1<'_>, claims: &UnverifiedProfileDigestBytesV1) -> Result<UnverifiedProfileHeaderV1, ProfileHeaderErrorV1>` | Shared borrows preserve actual owner and initial state; opaque digest bytes grant no trust. |
| Row producer | accepted `src/experimental_swift_reactor/diagnostic_profile.rs`: `pub(crate) fn write_profile_row_body_v1(snapshot: &ValidatedSwiftReactor, output: &mut File) -> Result<ProfileRowsObservationV1, ProfileAdapterErrorV1>`; guard wrapper derives `initial.cache.proof()` internally | Empty regular File at offset0, 80,000 rows x32 bytes, 4,096-byte buffer, 625 blocks, <=32 explicit writes/block. Partial physical output/progress is retained. |
| Final consumption | accepted control `record_cleanup(&mut self, wasi: Option<WasiUsage>) -> Option<SwiftRunFailure>`; `finish_owned_cleanup(self, wasi: Option<WasiUsage>) -> SwiftRunUsage` | After-cleanup failure observation and actual final consuming observation are distinct. Missing external authority/storage remains conservatively charged. |
| Host composition | accepted corrected Python prototype `compose_fixture(paths, sizes, header, output, scratch, scope=SCOPE)` and `compose_from_retained_fixture(inputs, header, output, scratch, scope=SCOPE)` | Eight fixture artifacts, no authentic Rust exporter. Fixed child hashes only profile/subrange/body; it is not the Rust analyzer. |
| Fixed child | `child_consume(profile, body, scratch)` invokes `[resolved_python, '-I','-S','-B', exact_consumer_py, profile_fd, body_fd]`, passes exactly two leased fds, waits five seconds then kill/wait five | Preserves terminal child-step result; it does not establish whole-profile post-consumer or runtime result acceptance. |
| Framing consumer | frozen header-prep `inputs/verification/swift-cache-state-ci/pack/source/library/analyzer.rs:492`: `pub fn analyze_fixture(stream: &mut File, profile_file: &mut File, context: &mut File, output: &mut File) -> Result<ReplayOutcome, AnalyzerError>` | `MIXFIX01` only, Unavailable/Binding; `stored_prefix_validated` and `full_replay_accepted` stay literal false. |
| Cache-state consumer | same frozen library `cache_state.rs:15668`: `pub fn analyze_fixture_cache_state_v1(stream: &mut File, profile_file: &mut File, context: &mut File, output: &mut File) -> Result<FixtureCacheStateOutcomeV1, AnalyzerError>` | Synthetic fixture FSM only; real binding, semantic metrics, stored-prefix validity and full-replay getters stay literal false. |
| Canonical CLI | `vm/src/main.rs` integer/numeric/table-memory validate/inventory/invoke routes | No retained Swift real-profile route. Canonical Swift module lacks the accepted private `diagnostic_profile` and initial-profile additions. No current CLI can honestly claim this integration. |

The frozen completion instrumentation is separate from this canonical source.
Its `cache_tests.rs` writer `finish(&mut self, footer: [u64;64]) -> [u64;64]`
and observer `footer(usage: &SwiftRunUsage, failure: Option<&SwiftRunFailure>)`
encode only a subset of the original failure. Existing `original.txt`/semantic
receipts use Debug formatting; `usage_keys` asserts WASI=None and omits elapsed
fields from semantic comparison. Preserve those historical bytes and semantics;
they cannot become the new typed result by parsing or relabeling them.

## 3. Source-private provenance and trust roles proposed for selection

The previous preparation's exporter is still an uncompiled signature proposal:

```rust
fn export_initial_snapshot_binding_v1(
    initial: &InitialProfileBorrowV1<'_>,
    provenance: &SelectedSnapshotExportProvenanceV1,
    output: &mut std::fs::File,
) -> Result<SnapshotExportObservationV1, SnapshotExportErrorV1>;
```

Keep it as the sole guard-bound entry. A metadata serializer must live inside
`experimental::swift`'s privacy boundary because snapshot metadata/import buffers
are private there. Proposed minimal privacy bridge: make the guard's *type*
crate-visible with fields/sole constructor private, expose only the read borrow
needed by that serializer, and require the actual unforgeable guard as its
parameter. No raw-proof alternative or arbitrary callback can invoke export.
Re-run positive and negative compiler cases in both modes: sibling guard literal,
guard escape, proof escape, cache/control mutation, supplied foreign snapshot,
external selection literal, move and callback/reentry must remain impossible.
This changes a private source contract and therefore needs root selection.

Recommended trust flow:

1. A trusted host source/build verifier opens and hashes the **complete selected**
   baseline/candidate member sets, compiler/linker/tool executables and exact
   build outputs. It verifies command/flags/environment/target/configuration,
   dependency lock identities and build-to-binary closure. It cannot accept a
   caller bool, executable basename, git revision alone, a partial manifest or
   a source-only record as the compiled adapter identity. Public signed
   toolchain/package admission remains outside this local development contract.
2. The same trusted launcher creates one session with fresh nonce, exact
   executable/argv/environment/cwd and inherited-descriptor roster, complete
   actual 17-field invocation budget, original 5-field validation budget,
   optional 7-field WASI budget and five grants. It derives accepted source,
   schema/layout, build and code-applicability receipt handles. The session hash
   is a correlation commitment, never a stand-alone authority token.
3. A new private loader adopts its exact inherited original-input File once,
   with selected length/type/identity checks. It reads all exact bytes with
   bounded calls, rejects short/extra input, calls the original complete
   validator with those actual five limits, then checks the immutable returned
   `proof.source()` against the entire loaded slice while both are live. This
   is byte equality, not source length or digest-text equality. Rust std has no
   SHA-256; host SHA-256 input pre/post checks remain standard cryptography.
   No hand-supplied `source.sha256` is trusted without this producer relation.
4. Only that loader can mint `SelectedValidatedProfileV1` (proposed private type)
   containing the real proof plus sealed actual budget/session/input/build
   provenance. Selected adoption consumes this wrapper, shares original
   `RuntimeControl::adopt`, and puts the sidecar inside the authentic
   `AdoptedProof` which subsequently moves into the cache. The ordinary public
   validator/adoption path has no selected sidecar and cannot export a real
   binding. Sidecar mismatch or absent provenance refuses, preserving all
   original owner/cleanup payloads. No proof clone/deserializer or copied usage
   snapshot can mint the wrapper.
5. Authentic prepare/construct/complete and every initial-owner check create
   the original sole guard. It checks the selected sidecar belongs to that
   adopted owner/session. Export exact logical `MIXSNB01` through that guard
   once, before header/rows and before first acquisition. No callback, await,
   reentry, guest/native operation, owner/control mutation or second validation
   can occur until export/header/rows have finished and the guard drops.
6. Keep the original result and zero-claim transport header unchanged. Host
   reads actual retained snapshot/body/transport/results and builds a **distinct**
   final header only after row hash and all selected joins exist. Original
   transport slots [128,384) are zeros; preserve [0,128) and [384,512) byte for
   byte. Hash both originals and final artifacts. The zero transport does not
   become an authenticated historical header after composition.
7. Host custody then binds the same actual run/session/build/source to all
   immutable artifacts, leases exactly its declared child descriptors once,
   terminally reaps that child, performs complete post-consumer hashes/metadata
   checks through the same retained descriptors, and preserves every primary,
   result and cleanup error. Admit only the explicitly trusted quiescent local
   scope. Unsupported concurrent/hostile rewrite models refuse.

Proposed extra record schemas for root selection are closed canonical records,
using the preceding preparation's eight-byte magic + LF + sorted ASCII JSON + LF
grammar (no floats/bools/unknown keys/duplicate keys or noncanonical bytes):

| Record | Required closed content and noncircular commitment |
| --- | --- |
| `MIXBLD01` (new proposal, <=128KiB) | schema, candidate_manifest_sha256, compiler/linker/tool executable identities and version-output digests, target, configuration, ordered commands/argv, selected environment, dependency_lock digests, outputs with path/bytes/sha256, exporter_source_sha256, producer_schema_sha256. It cannot hash itself or a session/profile that contains its own digest. Member and output closure must be root-selected; manifest counts are not silently inherited from 140+11. |
| `MIXBUD01` (prior proposal, <=4KiB) | schema plus all 17 exact invocation fields. Validation/WASI/grants remain separately included in session; no default inference. |
| `MIXSES01` (amended proposal, <=64KiB) | schema, nonce_hex, argv, exact environment/cwd policy, executable_sha256, candidate_manifest_sha256, build_receipt_sha256, invocation_budget_sha256, validation_budget five fields, optional wasi_budget seven fields, five grants, ordered fd-role/length/identity roster, owner_scope=`one-private-guard`. This adds required source-backed facts to the prior proposal and is not a selected compatible revision. |
| `MIXCON01` (new proposal, <=64KiB) | schema, session_sha256, owner_ordinal, original constructor tag, exact branch payload observations, every nested original/completion error as a full typed failure record, raw returned transport bytes/digest, row outcome and progress, export state/result/progress, returned-owner dispositions. It serializes observations; owner authority remains in the actual result/control. |
| `MIXCUP01` (new proposal, <=64KiB) | schema, session/build/candidate identities, full original primary/result reference, ordered list of **every** known independent cleanup error and owner generation/state, unresolved fd/name/process leases, all before/after hashes and actual final consumption references. Unknown primary/exception forms or a record exceeding its cap make real context unavailable. Never truncate nested errors, erase original exception objects, or suppress independent cleanup attempts. |

Original raw Debug sidecars remain preserved files with their real byte digest,
length and producer identity. The new typed record is separately emitted from
actual typed objects. It is not asserted byte-equivalent to Debug formatting.
Root must finalize these record versions/counts and the code/applicability table
before implementation; this packet does not grant admission from schemas alone.

## 4. Original owned outcomes and error preservation

The unchanged source enum is `#[repr(u32)]` but no Rust object image is serialized.
Its original numeric tags are explicitly retained:

| Tag / branch | Original payloads that must survive unchanged | Export relation |
| --- | --- | --- |
| 1 SlotOccupied | returned `AdoptedProof` | NotAttempted |
| 2 SelectionRefused | `ProfileHeaderErrorV1` and returned adopted owner | NotAttempted |
| 3 PreparationFailed | exact `SwiftRunFailure` and returned adopted owner | NotAttempted |
| 4 ConstructionFailed | `CacheConstructionFailure { failure, rejected_adopted: Option<AdoptedProof> }` **and separate** `Result<(),SwiftRunFailure>` completion | NotAttempted; retain both failures if both occur |
| 5 PhaseCompletionFailed | exact completion `SwiftRunFailure`; constructed cache remains in caller slot | NotAttempted |
| 6 HeaderRefused | exact `ProfileHeaderErrorV1`; cache remains | NotAttempted for pre-guard refusal; Attempted with exact result for later header encoding refusal |
| 7 HeaderOwnerCheckFailed | exact `SwiftRunFailure`; cache remains | NotAttempted |
| 8 HeaderEncoded | original exact `UnverifiedProfileHeaderV1 { bytes:[u8;512] }` plus `Result<ProfileRowsObservationV1,ProfileAdapterErrorV1>` | Attempted exactly once; failure cannot hide row outcome or original header |

The separate outer product remains a proposal:
`InitialProfileBundleOutcomeV1 { original: InitialProfileConstructionOutcomeV1,
snapshot: SnapshotEmissionStateV1 }`. It adds no ninth original branch. Export
failure makes real binding unusable but never substitutes for the original
terminal failure, mutates tickets, retries construction or changes the original
header/row order. Every returned original proof/cache/control must follow its
existing consuming cleanup. `MIXCON01` retains all branch observations and
nested failures; the 2,048-byte context is not a container for Rust owners or
an excuse to drop a second completion/cleanup error.

`SwiftRunFailure` fields are preserved exactly: stage, kind, original code
bytes, optional function u32, optional offset usize, optional resource and its
reservation payload, attempted/limit u64, optional observed_capacity usize,
deadline origin, optional WASI failure and its Budget resource, optional guest
exit u32, full at_failure usage, and independently optional after_cleanup usage.
Pre-meter `function=None/offset=None` differs from Some(0); no MAX sentinel
replaces an optional u32/usize. `after_cleanup` is not the final consuming usage.
Cleanup errors remain separate observations and cannot overwrite the primary.

All enum mappings below are **proposed wire IDs**, not Rust discriminants:

- Stage1..6: Adoption, Cache, Initialization, Invocation, Wasi, Cleanup.
- Kind1..21: InvalidBudget, Cancelled, Deadline, Allocation, Adoption,
  CategoryExhausted, CombinedExhausted, ResourceExhausted, FuelExhausted,
  WorkExhausted, HostCallLimit, PinLimit, FrameLimit, ValueLimit, ControlLimit,
  DecoderMismatch, UnsupportedEnvironment, GuestTrap, GuestExit, Wasi, Invariant.
- Resource1..17: Reservation(category), Combined, CacheEntryBytes, CacheEntries,
  ActivePins, Frames, Values, Controls, MemoryPages, CacheWork, ExecutionWork,
  InstructionFuel, HostCalls, Deadline, TicketInventory, OwnerIdentity,
  ExactCapacity. Category1..7: RetainedSource, RetainedMetadata, Cache, State,
  Wasi, Shared, Construction. Non-Reservation payload is zero.
- Deadline origin1 Run/2 Wasi. Cleanup0 None,1..5 ReservationOwner,
  ReservationUnderflow, MissingConstruction, ConstructionBound, LiveUnderflow.
- WASI failure1..8: InvalidBudget, Allocation, InvalidArguments, InvalidMemory,
  Budget(resource), Cancelled, Deadline, Invariant. WASI Budget resource1..5:
  Calls, Transfer, TransferSize, Work, Iovecs. Other WASI payload is zero.

These mappings compile exhaustively against the exact released type declarations
in this packet. Unknown numeric IDs, inactive payloads and width overflow refuse.
No code-applicability decision follows. The prior wire's 24 known code IDs are
insufficient as a general typed-source contract. A selected complete exact
code/kind/stage/resource/cursor/applicability registry is still required.

## 5. Exact typed-result partition proposal: 2,048 bytes

The proposed partition is metadata256 + failure scalar256 + at_failure512 +
after_cleanup512 + **separate final consuming usage512**. It is a new artifact,
not a Rust ABI measurement and not the original Debug receipt bytes.

Metadata consists of 32 little-endian u64 words. Word0 is `MIXRES01`; words1..3
are version1,length2048,terminal-form1 (`Option<SwiftRunFailure>`). Word4 has
failure-present bit0,after-cleanup-present bit1,final-consumption-present bit2;
unknown bits refuse and bit1 requires bit0. Word5 is constructor tag0 when that
entry did not participate, or original tag1..8. Words6/7 are raw original-result
and complete constructor-receipt lengths. Words8..11 hash exact original raw
result bytes;12..15 complete typed constructor receipt;16..19 session record;
20..23 typed result schema;24..27 exact writer receipt;28..31 are zero. A missing
constructor has length0 and zero digest. Metadata joins refer to actual retained
artifacts and their session/producer, not arbitrary supplied digests.

Failure scalar record [256,512) consists of 16 LE u64 words followed by 128
exact printable ASCII code bytes with zero padding. Words0/1 stage/kind;word2
presence mask bits0 function,1 offset,2 resource,3 observed_capacity,4 WASI
failure,5 guest_exit;word3 code length1..128;word4 function;5 offset;6 resource
tag;7 category payload;8 attempted;9 limit;10 observed_capacity;11 deadline
origin;12 WASI tag;13 WASI resource;14 guest_exit;15 reserved0. Absent fields
have literal zero payloads. Unknown code schemas or code>128 bytes/unsupported
ASCII refuse real context rather than truncating. Full original objects/raw
receipts remain retained when observation cannot be encoded. Function/guest_exit
u32 and source usize conversions are checked; 0 and MAX values remain distinct
from absence. This packet qualifies only host usize<=64 representation.

Every usage record is exactly64 LE u64 words, with no padding:

| Words | Exact actual source fields |
| --- | --- |
| 0..15 | current,peak pairs for reservations retained_source,retained_metadata,cache,state,wasi,shared,construction,combined |
| 16,17 | reservations live_tickets,peak_tickets |
| 18..29 | current,peak pairs for live cache_entries,active_pins,frames,values,controls,memory_pages |
| 30..34 | cache_work,execution_work,instruction_fuel,instructions,host_calls |
| 35 | cleanup invariant0..5 |
| 36..39 | elapsed_micros,deadline_ms,deadline_origin1..2,deadline_overshoot_micros |
| 40..49 | validation input_visible_bytes,source_bytes,metadata_reserved,scratch_reserved,metadata_peak_reserved,scratch_peak_reserved,total_peak_reserved,work_used,elapsed_micros,deadline_ms |
| 50 | WASI usage present0/1 |
| 51..63 | WASI calls,work,transfer_bytes,random_bytes,log_bytes,failures, then reservations fixed_state_bytes,staging_bytes,rollback_bytes,stdout_bytes,stderr_bytes,current_bytes,peak_bytes |

Missing snapshots are all zero bytes and their metadata presence bits are zero.
WASI=None requires words51..63 zero; Some(default-zero) has word50=1. The three
snapshots have independent bytes; no cleanup flag can manufacture one from
another. All peaks, elapsed/deadline, validation, WASI and counter fields survive.
Unknown/future data fields require new reviewed schema; this fixed record cannot
silently omit them. Additional original completion/cleanup failures reside in
the complete retained constructor/cleanup receipts with session/source/build
joins, and block context if unsupported or over-cap. They never disappear.

## 6. All fifteen final ledger joins

For the original completed diagnostic footer, compare each word to the **actual
final consuming `SwiftRunUsage`** from the same original control, not at_failure,
after_cleanup, expected zeros or a new control's defaults:

| Footer word | Final consuming source field | Usage record word |
| --- | --- | --- |
| 16 | reservations.retained_source.current | 0 |
| 17 | reservations.retained_metadata.current | 2 |
| 18 | reservations.cache.current | 4 |
| 19 | reservations.state.current | 6 |
| 20 | reservations.wasi.current | 8 |
| 21 | reservations.shared.current | 10 |
| 22 | reservations.construction.current | 12 |
| 23 | reservations.combined.current | 14 |
| 24 | reservations.live_tickets | 16 |
| 25 | live.cache_entries.current | 18 |
| 26 | live.active_pins.current | 20 |
| 27 | live.frames.current | 22 |
| 28 | live.values.current | 24 |
| 29 | live.controls.current | 26 |
| 30 | live.memory_pages.current | 28 |

Join footer10 cache_work and11 instructions to final usage30 and33, footer12/13/14
to exact original kind/code/stage (with the complete selected registry), footer31
to final cleanup invariant, footer32 to original failure presence, and all
failure-event optional cursor/work/instruction coordinates to actual original
typed observations. These joins are necessary and do not alone prove the FSM,
typed applicability, or missing event tail. Pre-meter cursor absence is preserved.

Healthy zero requires actual consuming cleanup and fifteen exact zero values
plus required owner/name/child obligations closed. The cfg(test) unit quarantine
must retain construction331,496,combined>=331,496,one live ticket and its actual
cleanup invariant; it cannot be patched to zero for context. Private host fd/name
uncertainty is a separate ledger from Rust reservations. Either unresolved kind
blocks a healthy-binding result. The data tests mutate all fifteen fields
independently, and keep at_failure/after_cleanup/final consumption distinct.

## 7. Entire 8,192-byte context proposal

The required partition remains [0,4096) selection + [4096,6144) original result +
[6144,8192) custody, with all unassigned bytes zero. Proposed component magics
are `MIXSEL01`, `MIXRES01`, `MIXCST01`; none are selected or supported by current
product consumers. The first magic is a proposed real-context discriminator,
not a reuse of `MIXFIX01`. Existing fixture parsers/getters stay unchanged.

Selection word0 is `MIXSEL01`;words1..12 are version1,selection4096,total8192,
result offset4096,length2048,custody offset6144,length2048,event-schema version1,
typed-result version1,custody version1,run-budget count17,validation count5;
word13 WASI-budget presence0/1,14 target-string length1..128,15 reserved0. Bytes128..640 hold
sixteen SHA-256 commitments in this order: baseline_manifest,candidate_manifest,
event_schema,adapter_binary,layout_receipt,snapshot,original_input,row_body,
original_transport,final_profile,stream,session,build_receipt,typed_result_schema,
custody_schema,code_applicability. These bind exact retained preimages; a shared
fabricated set is still unauthenticated.

Bytes640..776 contain all17 run-budget u64 words in the actual source order;
776..816 all5 original validation limits;816..872 all7 optional WASI budget
values in calls,transfer_bytes,work,one_transfer_bytes,iovecs,log_bytes,deadline_ms
order;872..912 five 0/1 grant words secure_random,realtime,monotonic,stdout,stderr.
Word13 distinguishes absent WASI from Some(all-zero); absent requires bytes
816..912 all zero. This is a new explicit proposal requiring root selection,
not an inferred default or a compatible amendment of MIXFIX01. The data controls
verify both representations and reject hidden payloads under absence.

Target bytes912..1040 are exact counted printable ASCII plus zero padding.
Bytes1040..1120 contain source_extent,type_count,slots,pins,initial_nonce,cache
base,cache capacity,entry limit,record cap,phase mask as ten checked u64s. The
remainder1120..4096 is zero. Target/configuration/tool identity additionally
joins the accepted build receipt and measured layout, not just target text.

Custody words0..7 are proposed magic,version1,length2048,scope1 (trusted
quiescent local),retained-artifact count1..32,complete-custody-receipt byte
length1..65536,actual child adoptions0..32,reserved0. Bytes64..320 contain eight
SHA-256 commitments: complete custody receipt, exact ordered artifact roster,
session,build receipt,final profile,event stream,complete typed result receipt,
complete typed constructor/cleanup bundle. Bytes320..2048 are zero. Original
generation/dev/inode/path/metadata/close/error facts live in the complete
retained custody transcript; this fixed view does not replace them or create
ownership. The selected custody schema must fix this exact order and actual
terminal/no-missing-error admission; caller counts cannot authorize it.

`context_contract.py` tests exact offsets/versions/reserved bytes/widths and
digest joins only. It deliberately returns real_binding_verified,
stored_prefix_validated,semantic_metrics_valid,full_replay_accepted all false.
It does not parse positive-present typed-failure records or validate real
selection/build/custody. Those require a genuine source implementation and
independent decoder/admission review. No new real API is exported by this packet.

## 8. Finite budgets and lifetime consequences

Preserve all actual validation/run maxima and deadlines. Existing row output
stays 2,560,000 bytes/625 blocks/20,000 explicit write attempts; header512 and
composed profile2,560,512 stay exact. Parent raw stdio stays <=32 reads/request
and <=512 bytes/request. Do not put a larger typed result/context on stdout.
Write retained files and use a closed <=512-byte child receipt only for exact
artifact references/status; parent independently reads/hashes those files.

Previous logical host ceilings apply only to nine retained owners, at most65
descriptors each (<=585), and two raw stdio owners, under the accepted fixture
roster. The real proposal adds session/build/budget/transport/raw-result/typed-
result/constructor/cleanup/context/writer artifacts and sequential source/tool
verification. It cannot reuse nine/585, the old read-count budget, or the old
source-object allowance without an explicit new simultaneous roster.

Root must select N<=32 simultaneous retained owners and A<=64 ancestors/owner,
or a smaller concrete roster. At most N*(A+1)+2 source-owned descriptors may be
live before separately counted inherited child views, plus the explicitly
bounded sequential verifier handle if concurrent. No blanket increase is
selected here. Lease every actual shared OFD once, lock all parent operations
during the child lease, and retain unresolved owners/names without admission.

For exact files of length L and 4,096-byte reusable transfer buffer, one full
hash/EOF pass requests at most `32*(L+1)` bytes and has at most
`32*(ceil(L/4096)+1)` explicit calls. These are conservative requested-I/O units,
not bytes actually read, library retries, CPU or VM work. Add each full pre/post
pass and subrange pass, partial writes, source equality scans, canonical record
serialization, code/enum validation and custody source verification separately.
A full 8,192-byte context read needs at most64 block calls plus32 EOF calls;
typed result uses a retained File, not a forbidden oversized stdio request.

Loader-visible source allocation, immutable proof copy and equality traversal
overlap must be charged before allocation. Sidecar, session/record handles,
SnapshotEmissionState/Result, complete outer result, arguments/return/move/caller
storage, failure/result serialization state, output File, buffers, cleanup tails
and any retained original payloads require fresh exact layouts in Debug and
optimized production/unit configurations and simultaneous-lifetime review.
The 165-entry predecessor inventory cannot be silently reused after types change.
The exporter must account charged Buffer capacities/category as well as logical
items; no unused allocation/padding/pointer image is serialized.

The accepted 451,173,376 scalar remains abstract callsite-action plus requested-I/O
only. It excludes authored atomic retry/callback reevaluations, all actual source
evaluations, CPU, allocator/kernel/library internals, elapsed time and VM debit.
This proposal borrows no part of that scalar or an unrelated host budget. If
the complete proposed simultaneous union does not fit unchanged limits, change
the ownership/order/representation through review; do not enlarge the caps.

## 9. Implementation/migration and verification sequence

`migration-roster.json` is a proposed exact minimum file roster, with explicit
reselection dependencies. No canonical promotion or source implementation is
authorized by this preparation. Root first selects the provenance carrier,
privacy amendment, complete record/code schemas (including the proposed WASI
presence field), source-count closure, finite owner roster and per-configuration accounting.

Then one isolated product lane copies the exact accepted 140+11 baseline and
implements loader/adoption/export/result/context preparation in that ownership.
An independently prepared lane tests real loader/source equality, budget drift,
build/session/source/binary substitution, owner mismatch, all eight original
outcomes including double failures, full typed snapshots/WASI/optional cursors,
every15 ledger mismatch and quarantine, writer partial outputs and EOF/attempt
boundaries, original transport preservation, same-fd pre/post hashes and every
cleanup/primary/result join. Failed compilation must still preserve positive
fixtures; actual bytes, permissions and untouched limits are required.

Only subsequent root-selected consumer work may add a distinct real-context API,
with actual accepted selection/result/custody handles, code applicability,
body/FSM/work/lifecycle/ledger joins and report semantics. It must preserve all
fixture false getters. CAP may establish only a validated captured prefix; it
cannot establish uncaptured tail/guest success/full replay. Missing required
tail information refuses complete replay. Full target replay follows only after
real contracts and complete budgets are selected and independently accepted.

This packet's fourteen Debug and fourteen optimized Rust methods execute exact
released **data declarations**, not authentic producer/loader/control behavior.
Exhaustive enum matches, all fields, WASI absence/zero, u32 overflow, code caps,
reserved/presence bytes, fifteen independent ledger mutations and separate
quarantine/final observations pass. Twelve Python methods pass proposed framing
and cryptographic-byte controls; the deliberately colluding fixture still grants
no provenance. This evidence supports design review only. It does not qualify
any genuine selected producer, source-admission or semantic replay gate.

Canonical/full-target/new compiler or CI qualification, native iOS/Android,
paused simulator/emulator/device/UI/capture execution, physical matrix, immutable
published packages consumed by separate-repository FieldLog, dogfood/OTA/store/
customer/operations and every GA gate remain pending. No process inventory,
hosted forbidden harness/inspector/authority/rejected-worker access, unrelated
Android startup experiment, canonical/index edit, commit/push or publication
was performed.
