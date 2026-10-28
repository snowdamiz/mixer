# Independent review of released lifecycle candidate 1

Recommendation: correct the narrow terminal artifact validators before releasing
the exact host run. The product patch and seven test cases match the selected
ordinary lifecycle contract. The remaining finding is evidence-validator
robustness, not an observed product security defect or runtime failure. No
additional product code, product tests, TLS, DB, application, or network work is
requested by this review.

Released producer freeze: 2169ba480aed74fcdac967908e578275fd7ebf3ca12d5f54448a3d61604b91a9.
Released plan: 3e9f39f19848f0ab36a524907d73c17fd7b68eaf96546e0185aad281c0496d01.
Independent preaccess seal: 1a1ec451725c4aa10bbe5b7282fd7e16bb5435e9ee310846889a83fd613df843.
The seven sealed preaccess members remain unchanged. This review is additive in
review-1/; it does not rewrite the original preaccess packet.

## R01: required terminal evidence fields and types are not enforced

Priority P2; requested before execution. In prepared-1/runner.py:270-283 the
terminal predicates check the values that happen to be present, rather than the
required schemas written by the source-bound bootstraps and test helpers.

Concrete source-derived counterexamples (not executed against the runner):

- original-regression.json or original-cleanup.json containing only
  {"unrelated": true} satisfies its respective nonempty all-true predicate.
- corrected/postconditions.json containing only {"cleanup_receipts": 7} passes
  while omitting every process, registration, admission, and application check.
- Any corrected *-cleanup.json containing {} passes its predicate. A sole key
  ending in _result is also ignored, regardless of value or type.
- ExUnit zero counts supplied as false or 0.0 compare equal to integer zero in
  Python. total: 7.0 similarly compares equal to 7. The result keys need integer
  types with booleans excluded, in addition to expected values.
- runtime.json is required and strict JSON is parsed, but its fields are never
  validated. Missing or wrong-type version/environment observations survive the
  terminal artifact layer, although compile-common.exs separately asserts the
  expected language versions and the bootstraps assert no product app.

The trusted current producers write full maps, so this is not evidence that a
current test passed with missing checks. It matters because the requested
terminal evidence must fail closed when an artifact is incomplete, malformed,
or its producer and validator drift. Strict JSON duplicate/nonfinite rejection
is already present and should remain.

Use exact key sets and source-derived types/values in
required-artifact-schemas.json. Preserve full artifacts/output on validation
failure, and fail the receipt. Integer checks must use type(value) is int (or an
equivalent rejection of booleans/floats). Boolean checks must use identity with
true/false. The five ordinary component cleanup maps have five required true
booleans and two result strings; accepted successful result strings are :ok or
:already_stopped, exactly as inspect(atom) writes them. The separate KOL04 and
KOL06 maps have their own exact schemas. Reject unknown keys rather than silently
excluding every suffix _result. This is a runner-only correction; preserve
prepared-1 and issue a separately sealed corrected runner/plan packet.

## Product and test review

Both beforeimages equal the accepted original snapshot bytes. KeyOwner differs
only by Process.flag(:trap_exit, true) at the start of the shared initializer and
the stored-table close call. Admission differs only by replacing close/1 with
the documented creator/current-table guarded close/2 plus ArgumentError denial.
The creator check precedes pointer comparison, which is harmless under the
selected serial lifecycle. The code deletes no ETS table, scans no global
registry, and makes no concurrent CAS claim. Existing parent handling,
supervisor order/strategy, infinity shutdown, waiter-before-drain ordering, and
transport code remain unchanged.

All 18 staged identity sources were read directly or, for the previously read
accepted modules, checked equal except for the exact selected diff. No staged
code injects a success verifier or starts a provider at compile time. The
dedicated suite matches the canonical staged bytes.

KOL01 uses actual parent Supervisor.stop, asserts trap_exit/creator/current
pointer, obtains a real permit, proves live disabled-profile unauthenticated,
then proves absent pointer and both public denials. KOL02 owner-only termination
preserves workers, proves new table/epoch/empty state, and shows stale release
does not consume a fresh permit. KOL03 observes killed-owner DOWN, dead table and
retained pointer while the exact component is suspended, proves public denial,
resumes in after, and verifies replacement of both children. KOL04 independently
uses same-creator mismatch, a monitored foreign caller, a deleted old table,
current creator close, and second close with absent pointer; it also asserts
close/1 absent and does not globally erase terms. KOL05 preserves the first
owner/table/epoch on ordinary duplicate start. KOL06 tests invalid manifest,
binding, and roots through ordinary supervisor startup and observes no owner,
worker registration, or pointer. KOL07 kills the exact no-flight worker
supervisor and requires old owner DOWN reason shutdown, replacement empty
children/table/epoch, stale rejection, and final pointer absence. Synthetic
Lease values are explicitly rejection-only. These are meaningful first-boundary
tests; their runtime behavior remains unverified.

Test helpers register component cleanup before suspension/assertions, retain
exact component PIDs, resume before stop, retain cleanup observations, and assert
pointer absence without direct erasure. KOL04's finally close is guarded and
cannot change the prior test result. Failed child-start helpers are monitored
and reaped by exact PID. No extra product test is required to address R01.

## Runner and custody review

The independent read-only audit passed 224 exact freeze members, 223 prepared
plan members, 212 canonical pins, 969 tool pins, the 18-source roster with 19
source module declarations, and 186 dependency files in five recorded apps.
All tool versions remain byte-bound expectations; no version process ran.
Dependency versions match the copied mix.lock entries and the runtime closure
loads their app versions and rejects MixerHosted modules in dependency BEAMs.
Fresh original/corrected VMs compile separate output; no cached product BEAM or
product application is loaded. macOS system shared libraries are accurately
outside the hermetic pin claim.

The original control meaningfully witnesses the contradictory KOL01 outcome:
ordinary parent stop leaves exactly the old dead pointer while both public
paths deny. It exits successfully only when that defect witness is true. This
is an expected-defect control, not a claim that an original ExUnit suite emitted
a failing terminal count. The frozen preaccess demand for a relevant failing
behavior is met by this explicit inverted predicate; unrelated startup/compiler
failure cannot pass the control. Preserve that wording in execution reporting.

The earlier runner concerns are corrected in the released source. Output is
fixed under the implementation lane and exist_ok=False prevents the same
execution directory being reused. Signals append instead of asynchronously
raising across Popen/child retention. Every retained child enters exact PID/group
cleanup; any child/group uncertainty preserves scratch and fails. A failed reap
does not authorize rmtree. Work stops at 40 seconds, cleanup has a 46-second
cutoff, post-run hashes/artifact parsing/durable observation writing use 52, and
the receipt check uses 55. Pins and artifacts are rechecked before the finite
signal cutoff. Signals received or pending by that cutoff fail; signals later
than the stated cutoff are explicitly outside the receipt. No new process
inventory is required. The cooperative checks do not promise recovery from a
hard-killed Python runner or a blocked host filesystem call.

After R01 is corrected and re-reviewed, the source is suitable for root to
release one exact bounded original/corrected host execution. This review grants
no runtime release and no product behavior acceptance. Actual compilation,
warning counts, original defect witness, corrected seven-case counts, complete
stdout and exact cleanup still need fresh evidence. KOL08/KOL09, real transport
drain, application/provider/HTTP/browser/session, operations, physical devices,
native/UI/capture, and GA remain pending.
