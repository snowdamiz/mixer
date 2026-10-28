# Retained storage-stage verifier contract

This is a public contract proposal for an isolated retained verifier v2. It is
source-only work. It contains no verifier implementation, actual certificate,
complete source inventory, semantic approval, trusted root approval, or selected
actual-input invocation. Root accepted the design direction for exact contract
authoring, not the resulting contract or a dependent implementation.

`contract.json` fixes the closed field sets, tagged alternatives, enumerations,
bounds and version changes. `failure-matrix.json` fixes the required behavioral
controls for later implementation and independent review. This document fixes
their semantics. All three are normative; a disagreement is an unresolved
contract error, not permission to choose a weaker interpretation.

This v2 sibling applies only F1, F2 and F3 from the independent review sealed
`df43d958b53785f7928e826d2f7e72c8151ffafb74252f2cdb2a26b03668b5b4` to v1 contract seal
`19532e82c9ea9fac5a5edd5dccc5d081d05f2c5fdec2da1689029de0b0b18837`.
Both predecessor packets remain immutable. `change-scope-receipt.json` and
`source-delta.patch` bind the exact amendment scope. This sibling awaits root
review of the delta before any dependent implementation is selected.

## Scope and versioning

The immutable base is retained verifier v1, producer seal
`8abb6802e73f98982bf863b16175617ca770a72e264364084aa8fa1c84226ee7`, reviewed
counterpart seal
`57f374b75c686fbc62024fd31b2a7ea37e80e33c57016a15b2db99dd3f3b739f`.
The seven source-grammar findings in partial-certificate proposal seal
`278095d3c9e615490c6bcc4046589f20f8beff365845d3e41764ea070126c09a` motivate
this addition. Those facts establish a representational limitation; they do not
establish an exhaustive storage-stage inventory or a certificate.

Only the v2 certificate, semantic-review and external-root-approval envelope
schemas become integer `2`. Their closed field additions are listed in
`contract.json`. The new `storage_inventory` artifact and
`semantic_map.storage_stages` use integer schema `1`. Capture observation,
capture acceptance, source binding, independent seal, input pins and all existing
semantic-map fields retain their exact v1 grammars. There is no v1 fallback or
automatic schema conversion. A verifier-v2 certificate has exactly the old
semantic-map keys plus `storage_stages`.

Keep the actual retained `CURRENT_BINDING` byte-for-byte equivalent, including
source/compiler/target/features/cfg/flags, retained plan/argv and `link_dead_code`.
The four fixed scope fields remain mandatory in every scoped envelope and every
result: `link_dead_code=true`,
`alternate_diagnostic_configuration_only=true`,
`original_capture_qualified=false`, and `runtime_admission_accepted=false`.
`local_geometry_only=true` and `complete_capacity_accepted=false` retain their
current meaning. The original capture is not widened to the alternate build.

## Independent inventory and authority

The new required input is named `storage_inventory`. It is a separately saved,
independently reviewed source inventory, not a client assertion of a count or
hash. Its digest is the SHA-256 of its exact raw bytes. It joins the current
binding digest, accepted capture digest, source-frontier digest and all four
existing target identities and native function anchors. An inventory's target
rows must agree exactly with the corresponding map target and frontier row.
All inventory anchors are checked against the same immutable artifact bytes
using the existing anchor guards and aggregate hash budget. Every new anchor
lies inside a bound whole-function span. A cut's anchors belong to its target;
an operation's before/after cuts have the same target and its anchors belong to
that target. A known native-owned object's evidence includes an anchor in its
owner target; additional use-site anchors may belong to other bound targets.
No text label, path count or source-name string proves source coverage.

An independent reviewer must inspect all four whole functions and their relevant
normal, refusal, cleanup, destruction, termination and outgoing paths to mark
`inventory_complete=true`. The reviewer enumerates physical objects,
representation views, copy/write sites, path/cut identities and alias
obligations. The input map must match the enumerated object, stage and copy IDs
bijectively. Owner, region reference, physical-object reference, operation,
source/destination identity, path/cut identity and required backing keys must
match their inventory requirements exactly. Counts are recomputed, never
accepted as authority. Missing, extra, duplicate, unmapped or substituted rows
are invalid, even if the input recomputes its own digest.

`inventory_complete` concerns exhaustive enumeration. `reviewed_complete` in the
map concerns the represented facts, including all required intervals, alignment,
reservation/initialization/value lifetimes, copy extents and aliases. A reviewer
can exhaustively enumerate an object whose geometry or lifetime is unknown;
that permits `inventory_complete=true` with `reviewed_complete=false`. A partial
local factual review, or a containing-frame review, supplies neither exhaustive
enumeration nor complete facts. The currently accepted local facts have not
supplied either new approval.

The independent seal must bind the exact `semantic-review.json` and
`storage-inventory.json` members. Their member names, sizes and raw digests must
join the corresponding input blobs. The existing canonical member-tree digest
check remains. Semantic review binds the complete semantic-map digest, inventory
raw digest, binding, capture acceptance, all four targets and strict completion
flags. Its complete status is permitted only when both old whole-CFG/exits and
outgoing-edge flags, inventory completeness, and storage-fact completeness are
true. Otherwise its partial status is required. Partial semantic-review status
alone grants neither enumeration completeness nor complete semantic approval.
It may bind a separately complete inventory while storage facts remain partial.

External root approval independently joins the exact certificate bytes, map,
review, independent seal, inventory, accepted capture, binding and complete input
pin set. The exact raw root-approval digest must still come from
`Invocation.expected_approval_sha256`, outside all input data. Its added
completeness flags must agree with both review and map. Its partial status is
required when storage or semantic review is partial. A trusted root may approve
an exact partial map for diagnostics; that approval does not close its missing
facts. Absent actual root approval always suppresses actual numeric claims.

Malformed scoped review, inventory or seal envelopes are invalid even before
approval, including synthetic runs. Synthetic mode remains an external strict
boolean and may substitute only `source_tree` in the otherwise exact retained
binding. Synthetic fixtures use their own matching inventory/review/seal bytes.
Synthetic results remain explicitly synthetic, including when a synthetic
control supplies a matching external digest. They cannot establish actual map,
inventory, capture, configuration or runtime approval.

## Physical objects and representation views

`objects` are physical storage identities; `stages` are representation views of
those objects. Every distinct native reservation slot has a separate object ID.
An SSA alias, cast, pointer forwarding, payload/root view or renamed value of
the same physical slot uses the same object ID with an explicitly reviewed view
offset/extent. Equal names or coordinates alone do not prove aliases. Distinct
names alone do not prove distinct storage. Both mappings require exact inventory
review. A representation move does not shorten the object's reservation.

An object records its owner frame, optional existing carrier-region reference,
symbolic interval, reservation lifetime and source evidence. The owner frame is
one of `FCaller`, `FClosure`, `FDispatch`, `FBody`, or explicit `null` for an
unresolved external owner. The referenced existing region is `R`, `C`, `O`, or
`null`; existing frame regions are not carrier aliases. A region reference binds
the same interval and alignment fields as the referenced carrier. It does not
bind the object's reservation lifetime to the carrier's coarser value lifetime.
R is physically owned by the Dispatch frame; C by the Caller frame, regardless
of their existing producer-target roles. Unknown O ownership is not guessed.

Intervals retain an arena ID, signed offset, byte extent and required alignment.
Each unavailable component is explicitly `null` and creates a local missing
fact. Non-null offsets and ends use checked signed arithmetic. Extents are
positive unsigned integers. Alignment is a power of two; its required modulus
is a constraint, never physical-congruence evidence. Existing arena facts and
same-base relations alone supply physical alignment proof. Numerical rebasing,
frame coverage, a layout requirement or a source name supplies none.

A known owned object's interval must be contained in its owner frame interval
on the same reviewed coordinate graph, and its reservation must stay within the
frame's reservation on every applicable path and coarse phase. Unknown owner,
interval, relation, frame restoration or lifetime emits local missing. A known
contradiction is invalid. External objects require an existing reviewed region;
otherwise they are unresolved, not new free-standing counted arenas.

Known overlapping byte intervals and simultaneous reservations on the same path
cannot be represented as distinct physical objects: they require one object ID
and explicitly reviewed views. Unknown physical overlap or temporal reuse is
local missing. Proven temporal reuse requires reviewed disjoint reservation
intervals on every applicable path. It never follows from source moves or phase
labels. The bounded grammar deliberately has no affirmative
distinct-but-simultaneously-overlapping physical-storage relation.

Each stage records a physical object ID and a byte view. Known view bounds must
fit the object, and all byte-lifetime segments must fit the view. A stage has
separate initialized-byte and valid-value lifetime tables. Neither a complete
physical reservation nor a full-representation copy implies that all bytes,
padding or inactive enum fields are initialized or contain live values.

## Paths, cuts and lifetimes

Path/cut identities and their order live only in the independently reviewed
inventory. Every listed path is a source-reviewed symbolic alternative through
the local frontier, not a runtime-reachability claim. Listed alternatives must
be mutually exclusive. `inventory_complete=true` additionally requires the
independently reviewed alternatives to be exhaustive across the required local
frontier. With `inventory_complete=false`, a supported subset of alternatives
may be retained; omitted or unreviewed alternatives create local missing and
never become evidence of exhaustiveness. No fictitious placeholder path is
required for an unenumerated alternative. Shared
prefix/suffix operations are repeated as cut rows on each applicable alternative.
Their path-specific copy IDs may share source anchors; object/stage identities
stay shared where storage is shared. A cut belongs to a target and a coarse phase
boundary, or explicitly has unknown phase `null`. Its source anchors establish
the reviewed location. The position in the sealed path's cut array establishes
order only because the independent review and external root approval bind it.
Input array order, lexical IDs, instruction-coordinate arithmetic and prose
cannot establish execution order. Distinct paths have no temporal relation in
this bounded grammar. A required fact that cannot be projected onto the same
reviewed alternative remains unknown; no cross-path containment is inferred.

Every cut ID is unique within its path. Cut phases, when known, lie in `0..5`
and are nondecreasing along that path; `5` is the terminal boundary, not a sixth
numeric phase. A copy/write has distinct before/after cuts on one path with
before preceding after. A source-reviewed path with unresolved ordering, phase
mapping or external continuation has `closed=false` and creates local missing.
In this v2 contract, `nonlocal_unwind`, `terminate`, and `unknown` termination
cannot have `closed=true`. In particular no Body restoration at
`__Unwind_Resume` or `panic_in_cleanup` may be fabricated.

Reservation lifetime intervals are half-open cut intervals. Initialized/value
lifetime segments add explicit byte offset/extent within their stage view.
`known` means the listed set is exhaustive for every inventory-required path;
`partial` preserves established intervals but is incomplete; `unknown` preserves
no intervals. `partial` or `unknown` always creates local missing. A known
reservation must be nonempty. A known initialized/value set may be empty only
when the exact sealed map review explicitly establishes absence on every
applicable path, and it cannot satisfy an inventory-required live field or copy
precondition. Empty arrays are not defaults for unknown information.

Every reservation and byte segment must refer to its inventory-applicable path
and ordered cuts. Stage segments are temporally contained in the same object's
reservation on that exact path. Where a phase is known, the entire segment must
stay inside its enclosing owner-frame coarse lifetime: the begin phase is at
least the frame begin and strictly less than its end; the end phase is at most
the frame end. A positive cut interval can remain inside one coarse phase.
Missing path alternatives,
unknown cut phases, unclosed path ends or unproved cross-target containment remain
local missing. Cross-path references are invalid. Existing native-frame all-exit
checks still apply independently.

## Copies, writes and backing aliases

Each required operation has its own copy ID and separate source/destination
stage identity, view-relative offsets, byte extent, path, before/after cuts,
operation, alias set and anchors. A representation `memcpy` or `memmove` is not
collapsed into abstract Body/Closure/Dispatch return links. Payload and root
writes are distinct rows; source values and stores into a carrier are not
invented as new storage objects.

For known sources, `memcpy`/`memmove` require stage sources and `store` permits
stage or literal sources. Unknown sources remain missing rather than being
silently coerced into a supported source. Stage sources carry a stage ID and
view-relative source offset. Literal sources
carry exact lowercase hex bytes, at most 32 bytes, and are permitted only for
`store`. When `storage_copy.bytes` is non-null, the hex length equals twice
that byte extent. When it is null, retain the null and emit local missing
without inferring extent from the literal; the independent 32-byte literal
bound still applies. External-sret sources carry the corresponding existing outgoing edge
ID and are permitted only for `external_sret`. Unknown sources are explicit and
create local missing. An external write or callee sret does not prove write
completeness, initialized bytes, valid values or final destruction; those
separate lifetime facts must be independently reviewed. External local effects
remain subject to the original unresolved-edge checks.

Known positive copy extent must fit source and destination views using checked
arithmetic. `memcpy` requires independently reviewed nonoverlap on the physical
coordinate graph at the site; known overlap is invalid and unknown overlap is
local missing. `memmove` permits overlap but supplies no new alias or value fact.
For each stage endpoint, prove reservation coverage of the entire half-open
operation interval `[before,after)` on the exact path. If the exhaustive known
reservation intervals demonstrably fail to cover it, the claim is invalid.
If an interval, phase, path projection or reservation state is unavailable or
partial so that coverage cannot be decided, emit local missing. A supported
known contradiction remains invalid even when some unrelated fact is unknown.
Initialized/value segments describe exactly what is known before and after;
the verifier must not propagate full-byte initialization automatically.

Stage and copy alias tables carry a strict knowledge state and exact
`{key,backing_id}` references into the existing thirteen backing obligations.
Their keys must match the inventory requirement; identities must match the
existing backing row. A stage-source copy's aliases must be supported by both
source and destination views for the copied semantic fields, as approved by the
inventory. Literal stores carry no backing aliases. External sources may only
preserve reviewed existing obligations. Unknown alias knowledge is local missing.
No stage, copy or move mints an allocation identity, a zero capacity, final
destruction or root durability. Existing R-to-C transfers and all thirteen
conditional capacity/destruction obligations remain mandatory.

## Completeness and numeric output

Known malformed/contradictory claims are invalid. Explicit partial/unknown facts
are retained as missing. `reviewed_complete=true` alongside any stage-inventory
or stage-fact gap is false completeness and is invalid; it cannot mask a gap.
`reviewed_complete=false` always adds local missing, even if all currently listed
facts look known. An incomplete inventory always adds local missing.

The numeric union algorithm, five phases and seven existing region roles remain
unchanged. The addition validates representation obligations against existing
physical reservation coverage; it adds **zero** stage/object bytes to the sum.
Intermediate stages contained in a frame, and multiple views of R/C, therefore
cannot double count the frame. An object not covered by an existing reviewed
reservation is missing or invalid; this contract does not silently expand the
counted frontier. It also does not let the counted parent frame complete an
unrepresented intermediate stage.

Keep the current all-or-null local numeric interface. Any new local missing
fact suppresses the entire `closed_local_phase_bytes` vector and
`local_peak_bytes`; no partial-phase numbers or new subpeaks are introduced.
Absent actual approval also suppresses them. Existing transitive/backing gaps
continue to suppress the corresponding whole-capacity/backing/unwind claims;
where such a gap prevents a required stage lifetime or local effect from closing,
it additionally creates local missing. Complete capacity remains false in every
result. Unknown physical congruences, O's arena/relation, external Body unwind,
backing capacity/final destruction, `WholeQuotePending`, prices, durable funding,
original-build qualification, runtime admission, FieldLog/OTA and GA remain
unresolved. Contract acceptance or later synthetic controls change none of them.

## Deferred acceptance

Root must review this exact sealed contract before dependent verifier code is
authored. A later isolated implementation needs synthetic tests from the failure
matrix, bounded source-only host controls, independent source review and a fresh
root source decision. A source-approved complete inventory, exact partial map,
semantic review, seal and trusted approval must be separately prepared and
reviewed before root selects any actual-input invocation. None is supplied here.
Compiler/native/UI/network/Docker/database/process probes are outside this slice.
Native runtime and capture remain paused; no owned instance was started.
