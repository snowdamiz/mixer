# Next slice: exact-toolchain dispatch return-region evidence

Select a **capture-only compiler inspection of the unchanged frozen source**, then
a small offline verifier for an independently reviewed region certificate. This
packet is a source-only proposal. It runs neither compiler, model, layout query,
certificate checker nor product code, and authorizes no such run.

Root accepted the previous 24-test slice only as an isolated synthetic host model.
That acceptance is a prerequisite here, not physical evidence. This plan binds
the exact acceptance receipt, independent terminal review, model v2 source, source
146 manifest, retained MIR frontier and accepted layout receipt.

## Why this approach

Keep the real return path intact long enough to resolve its physical question.
The 13,624-byte AdmittedReturn exists before the 13,640-byte complete child. The
Body activation is separate. Rust ownership moves, equal type widths and MIR
StorageDead do not establish their addresses, overlap or physical lifetime.

Adding a return/child slot helper now would change the path being qualified and
still leave that helper's by-value arguments, temporaries and native frames to
be bounded. A caller-supplied byte buffer labelled Body would not bound the actual
callee stack. The smaller next implementation is an artifact-bound verifier;
the compiler supplies the current native representation before a storage rewrite
is selected. This is a decision for this finite boundary, not a general compiler
analyzer project.

## The four-function frontier

Follow only the actual run_one_admitted_fixture_v1 caller, its exact closure at
initial_profile_v1.rs:861:36, the ReservationV1::dispatch_v1 monomorphization for
that closure and AdmittedFixtureOutcomeV1, and run_prepaid_admitted_fixture_v1.
target-frontier.json binds each complete frozen source expression and retained
MIR range. Closure source identity must not resolve to a proxy closure.

The return producer has setup refusal, conservative invariant fallback, raw
loader/correlation refusal, pre-scope failure and both finished leaf results.
Every normal return must write the complete admitted carrier. The fallback stays
counterfactual; generated code for it does not prove normal File reachability.

Also trace the caller's Result<PrepaidOwned<...>,Refusal> return destination when
it is a distinct slot. Its equal 13,640-byte layout is not an identity proof.
Do not extend analysis into engine/VM execution or pretend to bound all callees.

## Capture proposal, not a released command

capture-plan.json specifies one rustc invocation on the original, unchanged
146-file tree, using the pinned Rust 1.99.0 compiler and aarch64-apple-darwin
target. The accepted four feature cfgs, fixture cfg, opt-level=0, overflow checks,
unwind mode and MIR optimization setting are explicit. One codegen unit and full
debug information are inspection settings. Emit only LLVM IR and assembly into
a fresh owned directory; do not link or execute an artifact.

This configuration has not been compiled. Its future facts will be limited to
that exact inspection configuration. They will not automatically qualify an
earlier Debug build, opt2, another target, a subsequently selected policy path or
a new implementation. Preserve all pending production selectors.

The capture has a single 55-second budget: work through 44 seconds, owned cleanup
through 49, final hashes through 53.5. Output is bounded at 256 MiB total, 64 files,
1 MiB stdout and 2 MiB stderr. A separately reviewed root controller must enforce
these limits while collecting output. No retry, version query, formatter, test,
model execution or layout diagnostic is included. If functions are omitted,
ambiguous, optimized away or output exceeds a limit, preserve a failed/incomplete
capture. Do not add force-reachability code, dead-code flags, optimization changes
or a second compilation automatically.

The three baseline warnings remain warnings. Future source-bound diagnostic
handling must freeze full expected records, including the known source-path
rebinding and exact successful warning-summary form, before release. An unknown
warning/error/summary is not ignored or called zero-warning. Raw capture alone
does not accept any physical interpretation.

Root must separately freeze and review the adapted controller and exact capture
plan before releasing one invocation. Reuse of the reviewed controller design
does not qualify unobserved failure/timeout/EPERM branches or diagnose the old
failed attempt. Require exact owned child/group custody and closure, all input
and artifact hashes, observation-before-receipt publication and the reviewed
one-way signal cutoff. No global process inventory is permitted.

## What the next two source files implement

After this plan is reviewed, create only the proposed offline files named in
next-slice.json: region_certificate.py and tests_region_certificate.py. They use
Python's standard library and run in a separate Python -B operation of at most
55 seconds, with no subprocess, environment discovery or compiler invocation.
Root owns the capture controller in its own lane; no new producer runtime runner
is proposed here.

The verifier consumes bounded saved artifact bytes and a finite certificate. It
checks strict JSON, byte lengths/hashes of the actual in-memory inputs, exact
source/function/symbol bindings, referenced artifact byte ranges, geometry,
lifetime coverage, checked arithmetic and union certificates. It does not infer
native aliasing from names, regex matches, source moves or user evidence labels.
It is not a full LLVM IR, assembly or type normalizer.

After capture, a source reviewer must produce the concrete mapping from emitted
return-destination SSA values, address computations, stores/copies, native
prologues/epilogues and call edges to the finite region rows. An independent
reviewer must check the entire relevant function/control-flow slices and every
normal/cleanup exit, then seal that exact mapping. Only a root receipt naming
that mapping hash and review seal may permit the verifier to label its resolved
rows reviewed local geometry. Matching snippets alone never proves a mapping.
No arbitrary ReviewedBound-looking field can substitute for this approval.

Freeze the verifier and synthetic controls before parsing actual saved artifacts.
Then review/release that exact saved-input invocation separately. This sequencing
prevents adapting a successful interpretation silently to actual output.

## Facts that must be resolved, and facts that remain missing

R: bind the complete AdmittedFixtureOutcome to an actual return destination with
13,624-byte minimum, alignment at least 8, capacity, symbolic arena/base+offset,
and coverage on every return path until wrapping. Establish hidden return-pointer
identity across the actual body, closure and dispatcher; unresolved PHI/call
mapping remains unknown.

C: bind the whole 13,640-byte PrepaidOwned child and any distinct outer Result
destination. Bind the contained Option<T>/T extent without charging it twice.
For return-slot reuse, separately prove actual base identity, offsets and live
overlap; no reuse is assumed. If separate, prove that relation. Compute a checked
interval union for every relevant phase rather than blindly adding or taking max.

F: bind the Body function's complete native frame, including padding, spills,
outgoing argument/return storage and all normal/cleanup SP changes. Map the
coexisting caller/dispatcher/closure frames independently. A frame extent already
containing an R/C slot includes that slot once. An LLVM alloca is not by itself a
final native frame. Source type minima do not bound F, and F must never default
to eight bytes. Unknown dynamic adjustment, stack probing/helper behavior, call
peak, indirect target or cleanup edge leaves the corresponding bound unresolved.

This first frontier may prove local frame reservations and return-slot relations;
it does not bound deeper setup/loader/leaf/stdlib/drop/unwind call peaks. Record
every outgoing edge as an unresolved obligation unless separately pinned evidence
covers it. In particular no normal-return frame result qualifies destruction or
unwind peak. A missing transitive frame or cleanup bound keeps complete Body/whole
dispatch capacity incomplete even if local rows are reviewed.

B: retain the same backing identities through the R -> C transfer. Original root
inputs/paths and P0 binding storage stay separate; child setup Files retain their
exact successful prefix, then optional executable, original proof/error graphs,
shared Cancellation and claims/output state. Inline pointers, file descriptors,
equal paths/inodes, requested Arc layout or successful compiler emission do not
bound these backing capacities or prove healthy final destruction. No actual
backing upper bound, allocator/OS overhead, durable forgotten-root custody or
File/error/drop receipt is produced by this slice.

Retain original acquisition operation/cleanup/storage, P0 work/storage and all six
child work/storage components. Geometry is bytes, work remains a distinct unit.
Do not mint a price, shrink the six-component retained quote, charge the relocated
leaf twice, skip the parent/token, or treat a reference as pointee funding.

## Acceptance and concrete next action

Implement and source-review the two-file offline certificate verifier with the
16 finite control families in prospective-controls.json. Separately prepare the
root capture-controller delta and full expected diagnostics for one bounded
compiler capture. Those are the next reviewable code artifacts; this packet
creates neither. No new storage wrapper or canonical product edit is selected.

Possible capture result: artifact custody only. Possible later verifier result:
reviewed local region facts plus explicit missing facts. All outputs remain
local_geometry_only, and complete_capacity_accepted=false. Unknown alias/frame/
backing facts refuse the applicable capacity calculation. Even a complete narrow
local union supplies no quote, grant, refund, root durability or integration.

Prices, actual backing bounds, transitive/destruction peaks, root funding/custody,
canonical product integration, native/device qualification, FieldLog, OTA and GA
remain pending. No current runtime cleanup is owed: this source-only packet
creates no child process or build output.
