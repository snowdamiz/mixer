# Independent focused completion-tail review

Verdict: no blocking finding in this bounded actual-source/bytecode review of
candidate seal `8f355ae83ec4d734e8d28451fc64a45200967a718eecb7c1987fa0fcc69d9920`,
product tree `cb5c2b813b9cb375f2907bafcb066ba9c556a2713ffd04c9d74777d9595d01e4`.
This verdict accepts only the reviewed private source/host invariants. It is not
native, canonical integration, public V2, OTA, dogfood, release, or GA acceptance.

## Independent execution and custody

`audit.py` independently checked every one of the producer's 9,791 sealed members
(49,981,814 bytes), the manifest, root custody, root selection, protocol seal,
and selected PC-P01/PC-P02 amendment. The checked 16-file source set and unchanged
86 Android/JNI host leaves were copied into this review before compilation.
`source-map.json` identifies those exact bytes. The candidate's producer runner
and compiled classes were not used to generate this review's bytecode.

`compile` independently compiled the complete 102 Java files with OpenJDK
25.0.4.1, `--release 17 -Xlint:all -Werror -proc:none`, explicit empty classpath
and sourcepath, then `javap -p -c` inspected the resulting classes. `tools.json`
pins javac, java, javap, the JDK modules and JVM library by SHA256; commands,
versions, elapsed times, raw stdout/stderr and class hashes are retained.
Compilation succeeded without diagnostics. This lane ran no producer behavioral
suite or additional JVM behavioral witness: there was no concrete suspected
flaw warranting a duplicate/adversarial test. The separate independent lane owns
the complete behavioral replay and prepared PC-C/PC-S/identity/fatal controls.

The source census independently finds precisely NativeRenderer.java,
NativeAppearanceViewsV2.java, and NativeCoordinatorV2.java changed against the
selected focus-history base. The other 13 product files, all host leaves, the
cross-compilation JNI signature leaf and original 52-test source are identical.
Removing the two exact selected completeFailedV2 try/catch blocks reconstructs
the entire original coordinator file byte for byte. The two hooks retain their
selected positions after existing outcome cleanup and before final throw.

## Success, Begin, and terminal End

NativeRenderer.java:699-725 performs candidate/pending/journal/replay checks,
then validates the entire fixed preservation cohort before its first success
write. Every non-null scope must satisfy captured renderer/candidate/journal/
Record/View/Input/fence/original-token identity, entered and counted ownership,
unreleased/unended PRECOMMIT_READY phase, exact registration and selected Binding,
zero callbacks, empty hook stack, !checking and unchanged scalar loss serial.
`preservationCohortV2` counts represented `counted` members and requires equality
with candidate.heldPreservations and renderer.outstandingFieldPreservations, and
requires shared outstandingEditorNativeCalls >= that cohort. Success preflight
has only the two own scalar identity/cohort helpers and ArrayDeque.isEmpty on its
healthy path; Json.bad and sealScalarV2 occur only in refusing branches.

The independently compiled finishV2 tail begins at bytecode offset 358 and has
121 instructions. All branches stay inside that tail. It contains no invocation,
allocation, explicit throw, monitor, iterator, lambda, boxing, native, Input,
main/Looper, JNI, reporter, event, owner callback, or owner resumption. It first
claims SUCCESS_IN_PROGRESS, unregisters and ends the same fixed scopes, performs
prepared reference/primitive swaps and consumes the candidate, then clears only
those scopes' counted claims and decrements candidate, preservation and shared
counts. The shared count is each release's final write; SUCCESS_DONE follows
the complete release loop. No per-scope throwing guard follows the first effect.
The independent tail hash is the same c25ab54d...a8127c recorded by the producer.

The apparent implicit JVM field/array failure possibilities were checked against
the source invariants, not dismissed solely from opcode names. AttachmentJournal
owns final states and stateCount, constructed together before attach; stateCount
is states.length, elements come from the already-owned journal records, and no
product path replaces array members. NativeState preservation is assigned only
at capture before attachment completes. Both loops use i < stateCount and skip
null preservation entries. Exact preflight establishes each retained non-null
scope and its final record reference. Candidate.gate is final and is selected
from an existing gate or constructed before Candidate creation. No callable work
can invalidate these facts between final preflight and the tail. Arbitrary
reflection/Unsafe corruption or asynchronous VM interruption is not a supported
synchronous refusal and is not claimed recoverable.

NativeRenderer.java:156-169 places main entry and every identity, local-state,
settled-field, current-original, capacity and cohort check before acquisition.
The original Mutation has no continuation leases, so its current() follows only
captured scalar fence/token state; needsFieldPreservation/settledField and roster
retention are also source-audited scalar helpers. The independently compiled
Begin tail begins at 266, has 31 instructions and no invocation/allocation/
explicit throw/monitor. It publishes entered, counted, ATTACHING and the three
counts together, with the shared increment last. No post-return caller-side
entered publication remains. Its independent tail hash matches f7894fe8...07dd2.
Candidate/renderer tally equality and journal bound protect their increments;
the shared value is separately checked nonnegative and below Integer.MAX_VALUE.

NativeRenderer.java:170-177 refuses foreign/replayed End before any endpoint
effect. Exact terminal End requires captured identity and own entered/count-held,
unreleased, ended/unregistered, zero callback/hook/!checking terminal-phase state,
plus coherent cohort and shared funding. It deliberately does not require a
current operation or native success authority. Its independently compiled tail
starts at 87 and has 31 direct scalar instructions. The predicate's original
identity comparison never substitutes an equivalent Mutation/token or owner.

## Failure accounting and disposal

NativeRenderer.java:651-697 first refuses foreign candidate/journal, success-done,
replay, foreign scope provenance and foreign Record registration before claiming
the failed endpoint. No-scope/no-original candidates require no fabricated
Mutation or count. Exact unentered CAPTURED registrations are removed and marked
released without decrement or native-prefix report. Counted-but-not-entered and
entered-but-not-counted inconsistencies are retained rather than repaired.

The reporting loop observes the supplied primary/fatal and per-field failures
while releasable holds remain held. A local callback/hook/checking imbalance ends
and unregisters that exact owned scope but retains its count; another balanced,
funded exact scope can still release. A separate final whole-cohort funding/
identity/end-readiness pass follows all reporters and precedes any decrement.
The release loop has no reporter, throwing per-scope guard, native query, owner
resumption or call to the public Input endpoint. It clears only releaseReady
own counted holds; already released scopes are skipped. The last call in its
independently compiled method is final preflight's preservationEndReadyV2 at 683;
the release loop follows, candidate/shared writes are at 772/792, and retained
firstFatal is selected only afterward (athrow 824). Existing outer coordinator
leave/disposal flow is unchanged. Chronological fatal behavior is tested by the
separate independent behavioral lane, not newly claimed from this static audit.

The three custody tallies have only the reviewed acquisition/release writes;
no reset, borrowed-count repair or automatic retry exists. If shared funding is
below candidate-held preservation custody, preservationFailureFundedV2 fails and
no represented preservation decrement is authorized. Thus the underfunded
A/C-held2+B-shared1 state remains preservation2 after B's legitimate shared
unwind reaches shared0. NativeRenderer.java:94 keeps owner disposal busy on
either shared != 0 or preservation != 0; NativeCoordinatorV2.busyForOwnerDisposal
and disposeOnce use that guard. It does not infer disposal safety from shared0.
This proves the specified below-cohort underfunding invariant; it is not full
recovery or independent accounting for arbitrary corruption of every active
EditorLease/shared counter. Normal exact shared accounting remains a premise.

## Captured lifecycle suffix during getter reentry

NativeAppearanceViewsV2.java:875-884 uses captured identity and actually entered,
count-held, unended/unreleased registration plus the existing bounded hook stack
to admit only its already-entered lifecycle suffix. It intentionally does not
reject merely because checking=true or the current operation has been lost.
It registers the exact hook, records actual denial/loss and invokes the matching
native superclass callback before calling the ordinary exact() postcheck.
The independent bytecode orders actualLoss at 119, nativeCall.run at 134, and
exact at 140, with finally leave on both return and throw.

NativeField.actualLoss records every actual observed loss, including repeated
already-latched loss, then executes the scalar denial and revoke steps. It catches
observation/report failures so the captured native suffix is still reached.
capturedLossSuffixV2 uses exact captured ownership and the currently registered
loss hook; it grants no target access, fresh Mutation, cleanup conversion,
success token, bind/layout permission or callback scope revival. exact() still
rejects checking reentry and tuple() still demands current original, compatible
binding, settled field and unchanged loss marker. Thus native suffix custody does
not become success authority. Ended/released/foreign scopes refuse before hook,
loss marker or superclass effects. Runtime Android behavior remains unqualified.

## Limits and cleanup

This is a focused independent actual-source review plus host compilation and
bytecode inspection. It does not duplicate the main independent behavioral
matrix and cannot substitute for it. SDK37/D8, native ART/IME, physical devices,
simulators, emulators, selection getter callback entries, signing/store,
separate-repository FieldLog packages and operational/GA gates remain outside
this evidence. The copied host leaves have the producer's documented limits;
no native framework behavior is inferred from them.

Each compiler/version/disassembler child had a 60-second bound and was reaped.
Owned compilation scratch/TMP was removed. Exact inputs, compiled classes and
raw outputs are retained deliberately as evidence. No native/UI/capture or
process inventory was started or queried; other project processes/data were not
accessed. One early read-only JSON-shape inspection failed and is retained in
exploration-failure.txt; it supplied no validation result. No product/canonical
source, Git state, dependency, native runtime or acceptance gate was changed.
