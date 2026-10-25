# Customer artifact event independent review

This review covers only the ordinary pure schema-2
`MixerHosted.Audit.CustomerArtifactEvent` codec and its retained v1/ArtifactCBOR
regressions. It does not narrow the binding `mixer-product-plan.md` scope or
qualify transaction authority, persistence, deployed/customer operations, native
devices, separate-repository published FieldLog packages, or any GA gate.

**Result: accepted as a pure bounded codec development slice after one repaired
P2 finding.** Independent `run-3` passes 49 tests against producer `run-4`.
The original failing reproduction remains preserved in review `run-2`.

## Frozen inputs and method

The initial reviewed codec SHA-256 is
`0b3ac571d7e008acf12f12fb148ba55cb80b712634180346a6547930b1768913`;
producer test SHA-256 is
`6cbe0d238c1b54747c0bda05fbfd42f639c30233e944c3c3ef1ad422ebcf8de4`;
codec document SHA-256 is
`0318a66c362fa1b010c80cbba8412310d6cc889c418b3289dac3a29af1214d31`.
The producer packet is `verification/hosted-customer-artifact-event/run-3`.
Its root-supplied base revision is
`9662eda186e3beee084f92ac25c4116c92f2cebc`; the exact selected source digest in
each review receipt is the authoritative tree identity. No Git was executed.

The independent collector in
`verification/hosted-customer-artifact-event-review/run.py` snapshots named
ordinary dependencies from the producer's immutable inputs, verifies their
recorded digests, copies and verifies pinned general-purpose dependency BEAMs,
compiles with warnings as errors, and starts a fresh standalone BEAM process
registered as `:mixer_customer_artifact_event_review_collector`. Distribution is
disabled. It never starts the full Mix application, a shared hosted harness,
PostgreSQL, native instances, or network/provider operations. Frozen/rejected
catalog-inspector, authority-driver and Worker V2 sources are excluded.

The reviewer Python standard-library oracle does not import the producer oracle
or use Elixir's encoder. Eighteen primitive vectors check unsigned integer
widths, booleans, UTF-8 strings and fixed arrays before encoding a second
1,195-byte Unicode fixture. It independently derives all five external-identity
hashes, tenant genesis, created state, retry request identity and event digest.
The fixture includes a raw subject and profile containing a zero byte, exact
UTF-8 external references, positive maximum profile version, organization and
project memberships, optional ends, and a newly eligible fresh member. The test
also rejects the known wrong subject/binding prehashes and printable-backslash
zero domain spelling.

Reviewer ExUnit cases check closed top-level and nested shapes; exact target,
identity and locked/fresh linkage; selected role, scope, binding and window
semantics; inclusive start/exclusive end and five-second boundaries; created
and unchanged state/chain behavior; credential/metadata-independent retry
hashes; field-sensitive target/envelope/reason identity; predecessor tampering;
maximum scalar/member bounds; exact retained-row reconstruction; malformed
terms including improper lists, functions, processes, references, bitstrings,
100,000-element invalid tails and depth-100 invalid values. Semantic mutation
tests recompute event hashes before decode, so rejection cannot rely only on a
stale hash. The original 38 producer/v1/CBOR cases run unchanged alongside the
reviewer cases.

## Initial finding and preserved attempts

`run-1` passed 47 tests, but hostile atom identity exposed an Elixir runtime
warning. The focused callback sentinel added for `run-2` produces **47/48
passed, one failed**. Both attempts and all exact source, tool, command and
output evidence remain under the review directory. Every owned temporary
source/dependency/BEAM scratch directory was removed after its run.

**P2 — reject the identity type before field access.** In the initial codec,
`snapshot?/2` constructs `Policy.Decision` by evaluating
`identity.credential_ref`, `identity.profile_id` and `identity.profile_version`
before `Snapshot.valid?/3` validates the identity. An atom naming a loaded
module can invoke its corresponding zero-argument functions. The outer rescue
eventually returns `{:error, :invalid_audit_event}`, but it cannot undo an
already executed callback. The reviewer sentinel sends a same-process message;
the negative assertion fails in `run-2/tests.log`. This is a malformed-data
purity defect, not demonstrated authorization escalation. Reject a non
`VerifiedIdentity` value before any such access, retaining the existing full
closed identity validation downstream.

The initial source was not accepted. Root repaired the codec by making
`is_struct(identity, VerifiedIdentity)` the first build condition, before
snapshot/identity field access, and added a producer sentinel regression.

## Repaired source and final evidence

The final reviewed producer packet is
`verification/hosted-customer-artifact-event/run-4`; its 39 tests pass. Reviewed
codec SHA-256 is
`6e8450558d71af3d0940e7ca7a5725f7bdbc1ad834f4619f9008d8d196976942`,
test SHA-256 is
`1e5729064e747fc57c64dd7b28030ef89b0d9e72bbaaef733bdab93dca2aee93`,
and codec document SHA-256 is
`a3bc8cf3f07637bf4a6c9973329f18bf96b76712a19a8efce14ccc80c3bcf8ca`.

Independent review `run-3/receipt.json` reports **49 passed**: the producer's 39
cases and ten reviewer cases, including both callback sentinels. Source compile
and reviewer formatting checks pass; no runtime warning remains. The reviewer
oracle still independently reproduces the exact canonical event and all hashes;
its event digest is
`3c644af4d521fada6d08d8f99328cfc47a9e1c82ce260c9f3659ddd1ca413eb2`.
The selected source/tooling tree digest is
`865c6f4f2e9b6f154682d838ef3af0a88fc2647228665e01633fba606ee34f0f`.
The general-purpose dependency BEAM manifest digest is
`d750c4f0f2110c2d991d98110daafbcce855d4231df152cb49acfb6a2d9cb11d`.
The immutable receipt records exact commands, tool versions, copied input
digests, output and scratch cleanup. Existing v1 and ArtifactCBOR live source and
test digests match their frozen producer copies.

Reproduce the final independent run with a new output directory:

```sh
python3 verification/hosted-customer-artifact-event-review/run.py \
  --output verification/hosted-customer-artifact-event-review/run-N \
  --producer-run verification/hosted-customer-artifact-event/run-4 \
  --source-sha256 6e8450558d71af3d0940e7ca7a5725f7bdbc1ad834f4619f9008d8d196976942 \
  --test-sha256 1e5729064e747fc57c64dd7b28030ef89b0d9e72bbaaef733bdab93dca2aee93 \
  --doc-sha256 a3bc8cf3f07637bf4a6c9973329f18bf96b76712a19a8efce14ccc80c3bcf8ca
```

The finding is resolved for this exact frozen source. No unresolved codec
finding was observed within the specified review scope.

## Explicit limitations

The review intentionally demonstrates that a fully coherent altered principal
projection and correctly resealed event can pass decode/row/edge checks. These
APIs validate consistency of forgeable data; they cannot authenticate raw
identity references, snapshots, locks, current authorization, admitted artifact
bytes, the earlier selected membership set, or a privileged coherent history
rewrite. The storage transaction must own those separate invariants.

This is host execution on macOS/Elixir/OTP only. It uses frozen ordinary
Policy/Snapshot dependencies rather than another active lane's changing files;
later integration must test the final combined source. Boundary checks bound
codec traversal and encoded output, not caller input allocation or total BEAM
memory. No physical device, simulator/emulator, DB, signing, provider, immutable
published package, customer or operational acceptance is supplied here.
