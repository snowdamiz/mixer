# Guard-bound complete snapshot export preparation

Status: proposed private contract, frozen for separate root and independent
review. This packet selects no canonical/product integration and contains no
working exporter. The Rust prototype compiles a signature and field access and
always refuses `PreparationOnly`; it is never executed. Python controls parse
unverified synthetic data and model bounded writes. Neither control grants
validation, provenance, semantic replay or release authority.

## Accepted inputs and decisions requiring selection

The current source is the root-accepted corrected 144-member source tree
`9fbdabbc5122f71809483b3b0a0e95a71b9813def61572f366bcebc8ac6d08fb`.
Root acceptance SHA is
`635696d0f95e7adf231095ca05a223d47f0353c563b63f60ab242e9cf7bc2697`;
next-boundary instruction SHA is
`bf6a9c6600bba2a87e4c16dbbdac8fccb1ad5da562b92943267f6ab6c999f4fd`.
The producer and independent correction seals are preserved by reference in
`inputs/input-custody.json`. The copied 144 members are checked against the
accepted manifest. The 11 host-support members and earlier command/layout
evidence retain their original attribution; this preparation does not replay
their executions or claim the entire original 201-layout matrix was remeasured.

Select the new wire IDs and fields below, the narrowly enlarged privacy bridge,
the independent outer observation, and the complete source-place admission roster
before an executable exporter slice. The two retained-profile real-binding
documents in input custody are historical proposals. In particular their
`MIXBLD01`/`MIXSES01`, 17-limit launcher proposal is not the actual loader.

The current foundation remains 366,896 unit /366,312 production bytes; the
original 300,000 grant refuses. Existing 400,000 host evidence remains separately
labelled refusal-path evidence. No product budget increase is selected. After
measuring the exporter places, root may separately select a named host-only
positive fixture grant equal to the actual full requirement, with exact-floor
and floor-minus-one controls. Such a fixture exercises implementation and does
not accept an operational storage budget or change original selections.

## Actual loader and separate runtime observation

The actual loader parses `MIXLBD01` and `MIXLSE01`, both version 1 with 512-byte
headers. Build cap is 131,072; session cap is 65,536; source cap is 67,108,864.
Build sections cap complete manifest/command/environment/compiler-version bytes
at 65,536/16,384/16,384/16,384. It checks 144 source and 11 support members.
Session sections are exactly one 64-byte executable identity plus bounded
argument/environment/cwd encodings (64/16,384/16,384/4,096 caps). Loader process
matching and full source equality are trusted-local correlation; actual File
owners return, and no File-close proof follows.

The actual private `LoaderProvenanceV1` retains exactly five validation limits,
source extent, six 32-byte values (`source`, `manifest`, `build`, `session`,
`executable`, `nonce`) and four File identities in Source/Build/Session/Executable
order. Each identity has dev/inode/bytes/mode/mtime/mtime_ns/ctime/ctime_ns. Signed
timestamps use their exact two's-complement 64-bit representation. Nonce is
copied as retained bytes, never reclassified as a digest or signature.

Proposed `MIXLPR01` is a new 576-byte observation record, not an alternate loader
input: magic 0..8, version 1 at 8, length 576 at 16, source extent at 24, five
validation limits at 32..72, six retained values at 72..264, four identities at
264..520, zeros at 520..576. It introduces no new provenance field. In particular
it does not invent build/session artifact lengths that the adopted sidecar does
not retain. Future custody joins retain the actual original File metadata and
artifacts rather than filling absent data from caller claims.

Proposed `MIXRTB01` is a distinct 512-byte version 1 runtime observation, sourced
from the actual same guard/control/WASI owner. Its fields are magic; version at
8; length 512 at 16; WASI presence at 24; actual nonzero cache/control owner at 32;
all 17 run limits at 40..176; optional seven WASI limits at 176..232; optional
five grant booleans at 232..272; the eight existing initial guard scalars at
272..336; zero at 336..512. The order is exactly the public source declaration
order listed in `format_model.py`. None requires all 96 WASI bytes zero; Some
with zero budgets and grants remains distinct. `one_transfer_bytes`, `iovecs`,
`log_bytes`, and memory_pages are checked u32 values widened losslessly to u64.
All budgets retain existing narrowing-only ceilings; zero remains exhausted.
The actual WASI budget/grants are private in the context: a narrow immutable
source-backed read through `AccountedWasi` is a planned new private contract,
not a current accessor or a caller-supplied copy. Runtime record production and
same-owner joins are not implemented by the preparation signature.

This split is intentional: loader correlation records what the loader actually
validated; runtime observation records the later actual control configuration.
Neither is substituted for the earlier wider session proposal.

## Complete immutable logical snapshot grammar

Proposed `MIXSNB02`, version 2, deliberately distinguishes this contract from
unimplemented historical `MIXSNB01`. It is an exact little-endian, pointer-free
logical encoding. No Rust `repr`, padding, addresses, allocator internals, unused
Vec capacity bytes, raw enum discriminants or process-local pointers are copied.
Every integer is an explicit u64 word; original u32/usize conversions are checked
and lossless. The initial selected target is the current 64-bit little-endian
aarch64 Apple host. A different native layout must be explicitly selected with a
new compatible layout contract, never truncated into this one.

The 2,560-byte fixed header provides the complete fixed fields and a nine-entry
directory while fitting within one existing 4,096-byte transfer block:

| Byte range | Exact contents |
| --- | --- |
| 0..8 | `MIXSNB02` |
| 8..64 | version 2, header 2560, complete byte extent, sections 9, policy ID 1, validator revision 1, resolved import count 34 |
| 64..96 | actual source extent; metadata instruction count; native word bytes 8; native proof bytes 664 |
| 96..136 | actual five validation limits, equal to retained provenance |
| 136..144 | zero |
| 144..224 | all 10 `SwiftValidationUsage` fields in source order |
| 224..384 | all 18 observations, with each of the two Option maxima expanded to presence/value, 20 words total |
| 384..488 | metadata memory present/minimum/host max; table present/minimum/host max; declaration memory-maximum present/value; table-maximum present/value; memory declaration offset; table declaration offset; instruction count |
| 488..512 | zero |
| 512..1088 | exact new 576-byte `MIXLPR01` |
| 1088..1600 | exact new 512-byte `MIXRTB01` |
| 1600..2176 | nine exact 64-byte directory entries |
| 2176..2448 | actual 34 resolved `WasiFunction` IDs, each one u64 |
| 2448..2560 | zero |

This covers every private proof field: source section, full metadata, sealed
policy, all 34 resolved imports, complete validation usage, complete observations.
The resolved-import array is separate from metadata import descriptors. Its
stable wire IDs 1..34 follow the exact `WasiFunction::ALL` order in the accepted
descriptor source. Implementation must use an exhaustive match on each actual
enum value; casting a Rust discriminant or serializing `ALL` instead of the
actual proof array is forbidden. Type IDs are I32=1, I64=2, F32=3, F64=4.
Signature result uses 0=None or those IDs. Policy ID 1 means only the sealed
`SwiftReactorExperimentV1`; frozen/unknown policies refuse.

Every directory has words: id, logical count, native allocated capacity,
native element bytes, charged bytes, category, absolute payload offset, payload
byte extent. Category 1 is source and 2 is metadata. Payload sections follow
the directory order contiguously with no gaps, overlaps or trailer. Source
capacity equals boxed source length and has element size 1; charged source bytes
equal the actual validation source reservation. Each metadata entry records the
actual private Buffer values length, Vec capacity, `size_of::<T>()`, `charged`
and category. Check count <= capacity, multiplication without overflow,
charged == capacity * element bytes, and actual Metadata category. Do not infer
capacity from length or distribute aggregate usage heuristically.

| id / Buffer | Logical record, each field one u64 | Logical cap | Native element bytes |
| --- | --- | ---: | ---: |
| 0 source | exact source bytes | 67,108,864 bytes | 1 |
| 1 signatures | first parameter, count, optional result ID | 512 | 12 |
| 2 parameters | Type ID | 8,192 | 1 |
| 3 imports | module offset/bytes, name offset/bytes, type index | 34 | 20 |
| 4 functions | body offset/bytes, type index | 79,966 | 12 |
| 5 globals | Type ID, mutable 0/1, initializer offset/bytes | 8,192 | 12 |
| 6 exports | name offset/bytes, kind, index | 4,096 | 16 |
| 7 data | payload offset/bytes, destination, count | 4,096 | 16 |
| 8 elements | payload offset/bytes, destination, count | 4,096 | 16 |

Logical caps derive from the current fixed policy; function cap is 80,000 minus
the required 34 imports. Capacity may exceed logical count because actual Buffer
growth doubles; it is bounded by charged capacity and the unchanged metadata
budget, not incorrectly by the logical count cap. `metadata_reserved` must equal
native proof bytes plus all eight charged capacities. The source validator
reserves `size_of::<ValidatedSwiftReactor>()` into Metadata before source copy.
Current proof size 664 is inherited from accepted identity 49 and additionally
checked, along with the eight element sizes, by ordinary-production compiler
constants in this prototype. That is not measurement of the new exporter places
or a rerun of all 201 identities.

Maximum encoded size is exactly 69,765,152 bytes: fixed header plus the independent
source and logical section caps. This is an envelope cap, not an allocated Vec,
RSS claim, guaranteed reachable source combination, or raised runtime budget.
All optional absent payloads and reserved bytes are zero; presence/boolean/enum
values are exact. Every span uses checked offset+length <= source extent; each
type index is in range; signature parameter spans are in range. Actual exporters
derive all sections and duplicated counts from one immutable view and reject
internal disagreement. Full import ABI, export-index and segment semantic
revalidation remain properties of the actual original validator, not authority
supplied by the data decoder. A syntax-valid mutated fixture remains untrusted.

The finite Python decoder additionally checks contiguous coverage, per-section
and complete caps, native charged inventories, source/provenance/runtime extent
equality, source and metadata usage equality, observation logical lengths,
import/body totals, options, field widths and exact zero ranges. It does not
revalidate Wasm, issue proof owners or prove File custody. Synthetic positive
records are explicitly not authentic validation results.

## Sole guard, privacy and provenance path

Retain the existing sole `InitialProfileBorrowV1` literal after original phase
completion and successful `inspect_initial_v1`. Its type may become crate-visible
through a private-module re-export; every field and constructor stays private.
The cache/control/WASI remain the actual same immutable owners. No exporter
API takes raw `ValidatedSwiftReactor`, a foreign snapshot, arbitrary provenance,
digest text, bool, callback or a replacement guard.

Proposed bridge lives under `experimental::swift`, the real validator privacy
boundary. Its sole entry takes `&'guard InitialProfileBorrowV1<'owner>`, and every
returned source/metadata/provenance view is bounded by `'guard`, never just
`'owner`. The guard internally derives proof from its actual cache and selected
provenance from the same cache's actual `AdoptedProof`. A selected-missing ordinary
adoption remains valid ordinary adoption but refuses binding export distinctly;
it cannot be promoted by matching a digest. The provenance type remains opaque
and non-Clone; the preparation visibility adjustment does not expose fields or
an owned/parts constructor. Snapshot references use only the authentic six
retained values and identities. A host hash of output is an artifact observation
after writing, never a proof/provenance minting route.

The compile prototype adds only immutable bridge methods, re-exports and a new
guard-bound logical view. Its Buffer accessor reads values.len/capacity,
size_of/charged/category inside account.rs. The original proof layout, owner
fields, sole guard literal, eight-outcome enum and constructor body are unchanged.
The source delta is kept separate from the accepted copy. Ordinary-production
Debug and optimized compile cases cover positive exact signature, raw proof,
foreign source argument, digest/bool, callback, second guard literal, guard
clone, guard-borrow escape, guard move, view literal and source mutation. No
compile failure is accepted if it includes an unrelated diagnostic code. This
is privacy/signature feasibility, not behavioral correctness of a future writer.

## Original outcomes and ordering

Keep `InitialProfileConstructionOutcomeV1` unchanged, including inline owners,
original failure values, both ticket refunds/quarantine, row result and header.
Add a separate outer result with `primary: InitialProfileConstructionOutcomeV1`
and `snapshot: SnapshotExportAttemptV1`. Before any guard there is `NotReached`,
with no fabricated primary failure. Original variants 1..7 retain SlotOccupied
adopted; SelectionRefused error/adopted; PreparationFailed failure/adopted;
ConstructionFailed failure/completion; PhaseCompletionFailed failure;
HeaderRefused error; HeaderOwnerCheckFailed failure. Variant 8 retains its exact
HeaderEncoded header/rows. Do not translate, collapse, parse Debug or replace
any of these payloads with an export error.

On the original success path, admit planned export places/work before creating
the sole guard. Under that same guard, attempt export once; preserve its separate
observation; then call the original header encoder and original row writer in
their existing header-before-row order, even if export failed. Missing selected
provenance, bad output, partial output and exhausted writer attempts are outer
export errors only. A later header refusal preserves the earlier export
observation; header failure still prevents the row writer exactly as before.
No export failure retries construction, resets a cursor, implicitly refunds a
ticket, changes completion, or reenters preparation/acquisition. The earlier
phase-completion failure stays earlier than guard/export. Once the guard is
live there is no mutable RuntimeControl access or new ledger operation.

## Storage, work, writer and cleanup admission

The next implementation must measure all new types in actual unit and ordinary
production Debug/optimized builds and extend the source-derived simultaneous
accounting before allocation or output I/O. A size literal or this wire grammar
cannot authorize storage. `source-roster.json` lists each source and closure.
`storage-plan.json` lists every proposed ingress, return, move, caller, writer,
failure, lifetime and cleanup place. Counts are conservative named source places,
not guesses at compiler stack reuse or allocator overhead. New places cannot
be treated as covered by an old 201-entry table or hidden in a temporary.

Admission order must be concrete. The outer caller's arguments/retained output
and cleanup/return places belong in foundation before it creates them or acquires
an export File. Exact bounds for header/view/writer/output error temporaries and
all simultaneous moves belong in the original shared construction reservation
before guard creation. Any separately owned file/open/metadata/error/name storage
must have an admitted caller/operational owner before the corresponding action.
No independent untracked ledger or refundable observational Drop is allowed.
If a caller borrows an already-open quiescent File, the selected evidence must
explicitly name that preexisting owner and the still-pending acquisition/custody
scope; a borrowed File alone does not close that gate.

Reserve/check work from checked actual source extent and actual logical counts
before guard creation, using the existing immutable proof observations only to
calculate an allowance. The exporter rederives/verifies the immutable counts
under the guard; no preflight count becomes authority. Include all encoded source
bytes, scalar/enum/span checks, Buffer element visits, block filling and bounded
attempts in an explicit source-backed work formula and refuse insufficient
original work limits. Do not silently use the 69,765,152-byte maximum as a new
work grant. Work cannot be charged by mutating control during the live guard.
Deadline/cancellation handling under a live immutable guard needs an explicit
read-only check contract with its own error observation; it must not reenter
or mutate the original terminal runtime result. This remains a selection and
implementation question, not coverage claimed by the compile prototype.

Use one reusable 4,096-byte stack transfer buffer and stream into it, preserving
the original bounded-I/O discipline. At most 32 explicit writes per block,
including Interrupted. Completing the 32nd call succeeds; an incomplete 32nd
call refuses with acknowledged progress and no 33rd call. Zero, overreported
counts and other I/O failures refuse separately with original bytes/attempt
counts retained. Continuous blocking across section boundaries ensures at most
ceil(total/4096) blocks; do not reset attempt allowances for each field.
Output must be an actual borrowed empty regular File at position zero, checked
after admission. No generic writer/callback is an exposed authority entry.
Any generic fault-injection seam remains private to the implementation writer.
Do not allocate an entire source/metadata/snapshot output Vec. Success records
acknowledged bytes and calls only; no fsync, closed descriptor, immutable name,
digest custody or publication follows. Never delete partial output as an
implicit way to erase its failure/progress identity.

After the guard and its views are actually destroyed, only the original control
may retire admitted exporter temporaries and later consume the original cache,
adopted source/metadata tickets and WASI state. An output/file cleanup failure is
additional independent evidence; it never replaces primary/completion/cleanup
failure. Uncertain external descriptor/name obligations stay pending/charged.
Original quarantine is preserved. Measure and retain caller/result/cleanup moves
through actual consuming cleanup, not just the exporter call. No exporter return
implies all ledgers are zero or all file owners closed.

## Minimum executable slice and later boundaries

After independent contract review/root selection, minimum executable work is:
actual-source private bridge, exact complete snapshot encoder, counted File
writer, independent outer observation, original eight-outcome/ordering controls,
source-place/work admission and cleanup measurements; host-only all-eight
behavior controls, exact-floor refusals, partial output/32-call boundaries,
capacity and private-field coverage, borrow/privacy compilation and ordinary
production symbol/API review. Retain all original selection refusals, and label
any newly selected host positive grant explicitly. No new device/native runtime
tests are requested while paused.

Later slices separately close: loader operational allocation/IO admission;
actual File close/name/hash custody and retained output identities; typed complete
constructor/raw-result export borrowing real typed failures and actual consuming
final usage; all 15 final ledger observations and additional cleanup failures;
semantic context, original result/constructor/session/source joins and FSM/replay;
full workload; canonical integration; immutable published packages consumed from
separate-repo FieldLog; native physical matrix, signing/store/customer/operational
and GA gates. Raw Debug result bytes remain their own retained artifact throughout.
A snapshot digest or valid MIXRES01/MIXSNB02 grammar authorizes none of them.

No native/device/simulator/emulator/UI/capture/process inventories, Git changes,
production publication, hosted inspector or rejected worker/Android materials
were used. Only this new preparation directory is owned by this lane.
