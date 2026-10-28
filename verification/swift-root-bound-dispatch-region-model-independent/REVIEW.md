# Source review: add complete pre-wrap return coverage

Do not release the current host plan yet. One concrete model-capacity gap needs
a separately frozen source correction. No compiler or model/test execution was
performed, and no future test outcome is claimed.

The exact producer seal
`e0d38e4ddc3e2ab130d516750208981112d62135ab58b9598c751ac16e847c5d`
and all 10 members were independently verified. Host plan
`ab5584b2783ef8186908a5ba05fefbf55fcd429a37431d55d93043400c6de522`
binds one compile and one serial test invocation, a single 55-second budget,
owned output containment and no retry. Contract, selection, input, toolchain,
linker and SDK hashes were checked. There are exactly two Rust source files and
20 declared test methods; none has been run.

R01: both the setup-refusal transition and `BoundReturn` enter
`BodyReturned(payload)` while retaining only `ValueId::Body`. `Body` maps to
`UnobservedFrame(Body)`, so it has no observed size minimum. The test declaration
builder explicitly defaults unobserved owners to 8 bytes. `Snapshot` retains no
phase/payload, so later capacity assessment cannot recover that this phase owns
the complete **13,624-byte AdmittedFixtureOutcome** before child wrapping.

Consequently, declarations can begin the child extent only at `ChildWrap` and
cover the earlier returned value with the accepted 8-byte Body frame. All
owner-region checks still find a declaration, while the complete return carrier
has no matching known-width extent or explicit containing-slot association.
Existing positive fixtures keep every extent live for the whole horizon, which
masks this missing semantic-to-physical coverage requirement. This is a source
deduction from the validation paths, not a claim that the unexecuted binary
returned a particular result.

Add a distinct admitted return-carrier owner at every `BodyReturned` transition,
bound to `CurrentShape::AdmittedOutcome`, or an equivalent phase-aware explicit
coverage/containment mapping. Keep the callee activation/frame requirement
separate. Physical return-slot aliasing with the later child must remain an
evidenced hypothesis. Add narrow-lifetime tests for both setup-refusal and loaded
return paths: absent, undersized or expired return coverage refuses; complete
typed coverage can permit a synthetic model-only fit. Four concrete case
specifications are retained beside the review.

The rest of the reviewed structure is promising. `ScopePairReady` plus
`SplitScopePair` explicitly retain the 56-byte pre-child pair under P0. This
addresses a real omitted value phase without inventing shared physical slots.
Candidate-copy transitions make invalid refusals atomic. Payload take/drop,
reservation take, wrapper drop, token creation and unwind cleanup are separate.
All ten acquisition/P0/C0-C5 partitions, Work/Bytes separation, checked union
arithmetic, once-per-backing sets and model-only outcomes remain explicit.
Reviewed-looking or synthetic evidence cannot mint product authority.

The invariant fallback is expressly a conservative synthetic observation, not
normal File reachability. Preserve that distinction when extending it; its
after-two-open test is not an actual source execution receipt.

Keep every original source/test/plan/seal immutable and review the corrected
packet before root releases one bounded host run. Compilation and tests remain
pending. No canonical product source/metadata, commit or push was changed. No
compiler/runtime/parser/version, native/UI/capture/device or process inventory
was used. All actual physical capacity, prices, grants, funding, ownership,
FieldLog, OTA and GA remain pending. No process or build artifact was created;
no cleanup is owed.
