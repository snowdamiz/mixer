# Proposed bounded contract

## Root decision requested

Select one isolated actual-source profile-row adapter candidate. Do not select a
new cache policy, public File admission, a real semantic report, canonical VM
integration, CLI descriptor adoption, a full-target attempt or higher limits.
The immediately useful result is evidence that every emitted function row came
from a real sealed validated owner, rather than from an event or synthetic row
constructor.

No public Rust API changes in this slice. Preserve all three existing fixture
entry points, public types/getters, enum discriminants, layouts, literal-false
authority getters, report bytes and canonical CI pack bytes. In particular, do
not add a constructor for `ValidatedSwiftReactor`, `Fixture`, a decoded record,
`Loan`, initial cache state, a prepaid receipt or a binding boolean.

## Proposed private interfaces

Add an owned module under the isolated copy's `experimental_swift_reactor` module:

```rust
#[repr(C)]
struct ProfileRowV1 {
    defined: u32,
    type_index: u32,
    body_offset: u64,
    body_len: u64,
    reserved: u64,
}

#[repr(C)]
pub(crate) struct ProfileRowsObservationV1 {
    rows: u64,
    defined_functions: u64,
    imported_functions: u64,
    source_extent: u64,
    type_count: u64,
    output_bytes: u64,
    output_attempts: u64,
    reserved: u64,
}

#[repr(C)]
pub(crate) struct ProfileAdapterErrorV1 {
    code: u32,
    stage: u32,
    offset: u64,
    output_bytes: u64,
    output_attempts: u64,
}

fn profile_row_v1(
    snapshot: &ValidatedSwiftReactor, absolute: u32,
) -> Result<ProfileRowV1, ProfileAdapterErrorV1>;

pub(crate) fn write_profile_row_body_v1(
    snapshot: &ValidatedSwiftReactor, output: &mut File,
) -> Result<ProfileRowsObservationV1, ProfileAdapterErrorV1>;
```

The row has 32 wire bytes encoded field by field in little endian; a Rust memory
image, cast or transmute is never its serializer. The row/observation/error fields are
private. Result/error values contain fixed scalars only, no String/Vec, snapshot
owner, body borrow or File owner. Choose and independently review the exact fixed
error enum and complete Result/caller layout before implementation acceptance;
this preparation does not claim that an uncompiled layout fits an inherited
reservation.

`profile_row_v1` accepts only `absolute < 80_000`. It calls the real
`snapshot.execution_function(absolute)` within the VM crate. For each import and
each unused absolute row it emits exactly `defined=0, type_index=MAX32,
body_offset=MAX64, body_len=0, reserved=0`. It must distinguish a legitimate
undefined row from inconsistent observations: validate checked
`imports + defined_functions <= 80_000`, the fixed supported validator revision
and policy, `validated_bodies == defined_functions`, and `types <= MAX32` before
emission. Inside the defined absolute range, missing metadata is an error, not an
undefined row. No imported body is invented. `absolute_index` must equal the
requested absolute row, `type_index < actual type_count`, and checked offset+len
must fit the retained source. Length and offset conversions are checked. Body
bytes are borrowed from the sealed owner only while the row is derived; no body
copy is retained. There is no raw metadata/deserializer input, alternative
validator, relaxed policy or externally implemented trait replacing the owner.

The writer emits exactly `80_000 * 32 = 2_560_000` bytes in absolute-index order,
with one fixed buffer no larger than 65,536 bytes and no whole row vector/profile
copy. It accepts one safe existing File borrow. Check regular output, initial
offset zero and length zero before writing. A failed write retains the partial
output and returns a fixed error including truthful successful byte/attempt
coordinates; it never reopens/retries another path, truncates a preexisting File,
or emits success after an incomplete write. Each assembled output block gets at
most 32 combined short-write/Interrupted/error attempts; zero/overreport/error/
exhaustion refuses. Only private test seams may inject a bounded writer.

This output is a **row body**, not an admitted `MIXPRF01` profile. It has no
synthetic or real header, digest, context, cache construction value or acceptance
bit. A fixed observation reports row count, defined/imported counts, source
extent, type count, completed output bytes and attempts. Its meaning is local
row derivation, never artifact origin, digest verification, successful execution,
full replay, immutable path custody or package/release eligibility. A later
custodian must hash actual retained descriptors with a standard implementation;
this module implements no cryptography and consumes no supplied digest as truth.

The author must inventory source instructions, loop/work bounds, block attempts,
all complete owner/argument/Result/caller/error places and simultaneous lifetimes
for this exact new source. The snapshot's validation/retained-source/metadata
costs stay separately accounted under their current limits. Neither the fixture
component's 29,344-byte logical union nor its selected G1..G7 totals automatically
cover this new module. Do not increase analyzer/VM reservations or debit caps.

## Explicit fixture bridge

A host test may wrap these derived rows with an independently encoded synthetic
`MIXPRF01` header and `MIXFIX01` context, then call the unchanged accepted
`analyze_fixture_cache_state_v1` with four actual distinct Files. Label that bridge
as **real small-module row provenance, synthetic configuration/binding**. It tests
the actual parser/body-identity join and successful finite transitions; it cannot
make `real_binding_verified`, `stored_prefix_validated`, `full_replay_accepted` or
semantic metric validity true. All remain literally false. A fixture wrapper is
test support, never a real adapter or accepted profile header generator.

## Bounded proposed ownership

After root selection, producer owns only
`verification/swift-cache-state-profile-adapter/**`. Copy one explicitly frozen,
hashed current VM source closure into `source/vm/`; preserve all original files
except the isolated copy's `src/experimental_swift_reactor/mod.rs` module
declaration. Independently author only these candidate files:

- `source/vm/src/experimental_swift_reactor/diagnostic_profile.rs`;
- `source/vm/src/experimental_swift_reactor/diagnostic_profile_tests.rs`;
- isolated `mod.rs` declaration and test-module declaration;
- owned host test driver, independently encoded fixtures, commands, raw outputs,
  inventories, immutable copied closedpack inputs and packet seal.

Do not edit the live `vm/`, canonical CI pack/runner, old evidence, root metadata,
other lanes, or source-cache algorithms. Build the real copied VM crate, not a
rewritten struct or a textual model of the extractor. New test fixtures are
independently authored Wasm with the fixed actual validator ABI. Root owns later
canonical integration, documentation/status/gate updates, commits and delivery.
Independent review receives a different bounded directory and no write access to
the frozen producer packet. No new third-party dependency is necessary.

## Dependency order after this slice

1. Select an exact diagnostic VM closure and reconcile its source/schema/layout
   with the accepted emission seams; instrumented archived cache/control bytes
   and current canonical bytes have different identities. Build a real profile
   header from the same actual validated snapshot plus that exact selected cache
   construction/layout and unchanged narrowed run budget. Require measured
   compiler layouts, `slots=min(cache_entries, defined_functions)`, actual pins,
   nonce1, and the complete fixed-cache reservation formula from the exact source.
   An input requiring zero slots/pins is unsupported under the present fixture
   parser; do not silently broaden it. Bind all eight profile digests and hash the
   complete profile plus row body through retained descriptors.
2. Implement the closed selection/source/tool binding, original typed result
   adapter, all 15 final ledger comparisons and exact failure/code/stage/resource
   applicability. Do not parse Debug text with regex or learn a failure code from
   an old sidecar. Preserve pre-meter original optional failure cursors.
3. Add the separately named real context/replay path, real semantic metrics and
   versioned report join only after those contracts are accepted. Keep existing
   fixture behavior separate. Every new source needs fresh accounting/lifetime
   review under unchanged limits; a hash match of the scalar cursor is not that
   proof.
4. Independently review the standard-library host custodian and private CLI worker:
   safe path/no-follow handling, actual SHA-256, exact same-descriptor pre/post
   hashing and stability checks, no parent seeks while inherited descriptors are
   live, closed argv/pass_fds, exactly-once private adoption, bounded child/reap/
   cleanup and exclusive report/acceptance output. The current runner explicitly
   qualifies trusted quiescent fixture checkout evidence, not adversarial custody.
5. Close inherited serializer/CODE-buffer and writer accounting/repair obligations,
   then separately select one bounded full-target diagnosis with an exact source
   closure. Preserve every old invalid/failure15 sidecar and the failed original
   whole-suite timeout. No full-target retry is selected here.

Steps 1–4 have dependencies and may be designed independently under root control;
they do not follow automatically from acceptance of this row adapter. The row
adapter cannot prove cache construction, real source invocation custody, failures,
refund/quarantine, final consuming ledger, uncaptured CAP tail, target benefit,
guest completion, CPU/RSS, native behavior, signing/store, separate-repository
published-package FieldLog, customer/operational readiness or GA.
