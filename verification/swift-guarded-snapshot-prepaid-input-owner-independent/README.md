# Independent prepaid input-owner review

The frozen candidate's host-model evidence is **returned for correction**. The
source-owned bootstrap and minimum existing-open correlation direction is
implementable under the existing trusted, quiescent local launcher model. This
review selects no authority, numeric policy, native adapter, production route or
GA gate. Four desired-property regressions fail against the candidate model;
16 independently authored controls pass. The original candidate stays immutable.

The reviewed candidate seal is
`9c73d3405370a71ad447136ab7a4e56c2d45dbf4fd4627c319a8626f8a53033e`,
36 members and 448460 bytes, with tree
`961bf1001f674e40f4be6895c0c786e06a90f8aa7ad09b9d904c2c339496f0b8`.
The root release is independently checked against SHA256
`3f7c771eb0ef9a0e44633dac0dab6c4120cc16ed925909441e503a9e9584434e`.
Every command rehashes all 299 declared frozen inputs, 40253112 bytes, all 36
candidate members and the three specified root release/acceptance receipts
before and after. No producer freeze, runner, test suite or one-shot entry was
replayed. Only this directory was written. No compiler, product executable,
native/runtime/UI/capture process or broad process inventory was used.

## Findings and the correction boundary

1. **Partial and complete handles do not participate in model retirement.**
   In candidate `model.py:166`, `adopt_slots` sets `handle.adopted` at line 181,
   but does not place the handle into a reservation-owned or returned outcome.
   `TestReservation.owned` receives only byte bodies at line 106. Its destructor
   model at lines 112–120 clears byte bodies/diagnostics, and release at
   lines 127–132 sets storage to zero. A refusal at slot 2 leaves two adopted
   handles outside the owning retirement roster. Full adoption followed by
   destroy/release clears the charge while all 13 model descriptors remain valid
   and adopted. Those are two retained failing regressions, not native close
   observations. The candidate's tests only inspect adoption flags on the
   externally retained input list; they do not establish owner transfer or
   funded complete retirement. The concrete correction must own every partial
   File and govern the remaining raw-slot obligations without double ownership.
   Acquiring all input work must leave separately funded cleanup available.

2. **Admission/provenance is a detached marker in the model.** Candidate
   `model.py:293` stores object IDs and a Boolean, without a live owner or
   reservation/generation binding. `correlate_before_leaf` at line 317 checks
   the marker's class and equality between two caller-supplied dictionaries.
   It dispatches with equal empty dictionaries. It also dispatches with a
   different reservation after the original owner has been destroyed and its
   storage released. These are two additional retained failures. A closed
   expected-provenance value must derive from the admitted owner and include
   every promised field, and the model must enforce the exact live owner's
   reservation identity/generation and single consumption. This is a host-model
   evidence defect; the proposed Rust lexical owner/view design can enforce
   those requirements when implemented and independently reviewed.

3. **One interface sequence needs clarification.** The sketch's comments at
   `interface.inc.rs:133–140` unconditionally say `SAME-handle loader/leaf`.
   The README and contract instead recommend existing opens plus correlation
   as the minimum route. Correct that sequence to identify the minimum route
   and retain same-handle loading as the optional larger delta. No equal-FD
   requirement is needed under the existing trust model.

`correction-contract.json` gives the minimal concrete requirements and hostile
controls. R1 and R2 are mandatory before accepting the four model claims; R3
clarifies the interface. No missing native implementation or explicitly null
policy value is treated as a contradiction or invented failure.

## Accepted reasoning within the stated model

The bootstrap direction has a finite trust root: independently provisioned
launcher and child startup P0 exist before the private zero-argument
`from_preexisting_fixture_startup_v1` call. Its first frames and the source
policy are already externally funded. The full maximum acquisition reservation
precedes descriptor validation, unsafe adoption, metadata, allocation, reads,
hashing and parsing. Input limits, review labels, FDs, digests and later child
refunds cannot mint this root. A source-root policy and trusted-launcher
provision are unimplemented obligations; a numeric counter cannot prove them.

The thirteen fixed-slot regular-file protocol is feasible within that assumption
if the native bridge establishes valid exclusive ownership before each unsafe
conversion, one-time bitmap/table, no preexisting Rust owner, single-thread/no
close or reassignment handler, all 13 distinct dev/inode objects and retained
launcher immutability. The launcher resets shared open-file-description offsets
to zero before launch and then never reads/seeks/writes them. Validity checks,
metadata and eventual retirement must all be prepaid. Slot validity alone is
insufficient. The model does not qualify an actual bridge or process startup.

Ten identity caps total 67454875 bytes. Compiler/review caps, FD_BASE, all five
fixture path caps and packet cap remain unselected. The executable/cwd 4096
observation cap does not apply to fixture paths. Five native path bodies and
five retained path bodies are separately allocated/charged, in addition to 12
full identity preimages and the separately live path packet. Raw non-UTF8 paths
and longer-than-4096 fixture paths are allowed only under a separately selected
finite path policy; NUL/empty paths refuse. Equality or aliasing earns no credit.

The finite-read formula bounds calls, including Interrupted and the EOF request:

`32 * (ceil(actual_extent / 4096) + 1)`.

The independent request-state automaton exhaustively checks 100842 small
adversarial schedules over interruptions, zeros, short reads, errors and
overreports, and checks real 4096/32 maxima at ten extents. A 33-byte payload read
one byte at a time refuses on call 32, with 32 bytes consumed. Worst-case legal
success uses 31 interruptions then a complete response for every block and EOF,
attaining the formula. Overreported, zero or extra EOF data refuse finitely.
Checked quotient/remainder avoids round-up addition overflow; the formula at
u64::MAX is 144115188075855904 calls. Pricing multiplication and all storage
sums still require checked arithmetic. This establishes a call-count bound,
not a native syscall latency/cost or healthy cleanup contract.

Concrete allocation must bound requested capacity, slack, failure backing and
original diagnostics before invocation. No post-allocation `capacity` test or
`try_reserve_exact` promise resolves that obligation. Independent controls
confirm the model refuses an unaffordable allocation before its effect and
retains an injected original error object. Those tests do not measure allocator
or error backing. R1 prevents operation exhaustion from consuming cleanup.

The precompile/postcompile identity order is acyclic: freeze source/host/tool/
orchestration closure and compile manifest/argv/environment-minus-exact5,
compile the five identities, retain actual output, then externally create build,
fresh session/process-environment-minus-exact2 and finally external review
excluding its own digest. External review binds the actual source/build/session/
executable and source policy; manifest correspondence is also bound transitively
through compiled five identities and the actual build. The child must explicitly
decode and verify the exact reviewed full closure, rather than infer it from 146
and 11 counts or an opaque manifest digest. Actual image-to-handle custody still
needs the reviewed native bridge. `_NSGetExecutablePath` plus reopening alone
does not establish the new image relationship. No adversarial-launcher support
or new signing/acceptance authority is introduced by this review.

## Source comparison and minimum route

The existing loader source was inspected before proposing changes. It already
rehashes actual source/build/session/executable bodies, checks five compiled
identities and section digests, expected session hash, nonce, source FileIdentity64,
source extent, original validator limits, process argv/environment/cwd, four-file
dev/inode anti-aliasing, source/proof equality and final metadata of all four
actual handles. These are retained checks, not missing features. Distinct handle
numbers alone do not fail under immutable trusted quiescent custody.

`LoaderProvenanceV1` at frozen loader line 187 already retains the nine groups
needed for correlation: validation budget, source extent, source/manifest/build/
session/executable digests, nonce and all four FileIdentity64 records. The entry
at frozen `cache/initial_profile_v1.rs:812` currently dispatches `Ok(selected)`
directly to the leaf, and provenance fields are private. The minimal future
source change is a private loader correlation helper plus an entry branch before
the leaf. Its complete expected state must derive from the admitted owner,
not from arbitrary dictionaries. Keep selected result, files, original failures
and correlation diagnostic charged together. Source-root path-to-object custody
holds across both opens; native path bytes are still checked. Both complete
sets of backing and owners coexist and must be priced without sharing credit.
The optional same-handle route changes more source/ownership/cost and is not
selected by this review.

The separate exact source comparison rehashes all 146 provider origins: 145 are
unchanged; the initial-profile source adds 6881 bytes between an unchanged 61294
byte prefix and 4 byte suffix. All old bytes remain in order. The actual 17
SwiftRunBudget fields and eight original unverified claim fields/copy assignments
remain present. The original selected module's historical literals are preserved;
the proposed new execution policy still selects only the 1B work and 256MiB
constraints, with 15 other policy selections pending. Three production selectors
remain Pending, and all six provider upstream requirements remain unqualified.
No future changed source is identified by the current source tree automatically.

## Evidence and completion limits

- `commands/candidate-desired-properties`: exit 1, four failed desired-property
  regressions retained verbatim. This is a failing candidate-model result.
- `commands/independent-controls`: exit 0, sixteen controls and 100842 exhaustive
  read schedules. These are independent specification/model controls only.
- `commands/source-comparison`: exit 1, reviewer initially assumed append after
  the entire old file; the provider actually inserts before its closing braces.
  The failed assertion and exact script/inputs remain preserved.
- `commands/source-comparison-v2`: exit 0, complete byte comparison establishes
  the one insertion and unchanged original prefix/suffix, fields and selectors.
  This corrects the reviewer's comparison assumption; it is no product defect.

Each command retains exact argv, Python 3.14.8 executable hash/version, independent
script snapshots, source tree/release identity, before/after input custody,
stdout/stderr hashes, terminal status and cleanup. Each sole owned Python child
was started in its own process group under 55 seconds, reaped, and its group was
confirmed absent through its exact owned PGID. No global process query occurred.

All new Rust source, compiler/lifetimes/layouts, root quantities, complete
provider/acquisition/bridge/correlation/backing/retirement costs, actual executable
closure, allocator/error contracts and native image correspondence remain
unimplemented or unqualified. The three selectors stay Pending. Physical phones,
simulators/emulators, runtime/UI/capture, FieldLog published-package consumption,
operational/OTA and GA evidence remain pending. This packet changes no product
source or root policy and creates no grant. The root decides any bounded contract
acceptance after the model return and corrections are reconciled.
