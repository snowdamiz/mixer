# Exact source closure and reconciliation

All observations bind the snapshots in the two input manifests. HEAD is context
only; root/other lanes can change the checkout. No source file was imported,
compiled, or executed. Whole-source identity is a precondition for future review,
not proof that semantics, accounting or machine layouts agree.

The accepted completion candidate manifest has 132 named paths. Its source archive
was read as data, with exactly the same 132-member set and each recorded hash
verified. The current canonical snapshot covers those same 132 paths. Their
respective path/byte/hash tree digests are:

- completion: `5bc45d43c0f4ab53f020e9473e426beb2e411891f927cdb489ce12aff0045142`;
- canonical: `97af88de5fdc4cfd0819880aed778c82f967dec7aa6d4968b5a78313e61c1c44`;
- frozen row candidate's 131 copied source members:
  `6f02bc505046ceb60090afcd8e8ba87a4297536990285f4ede4306a77d8c74bc`.

The producer seal itself matches the assigned SHA-256
`472dc4fcffbca9718c9b7c47ced3586170ffd9ab1dbf7185b07e3b4cd2ff87a3`
and lists 481 members. This preparation verifies its 131 source members and two
provisional accounting files individually; it does not access or requalify the
producer's non-source runtime artifacts, nor treat its provisional accounting
claims as accepted complete totals.

## All observed differences

| File | Completion versus canonical/frozen row base | Reconciliation required |
| --- | --- | --- |
| `src/experimental/swift.rs` and all common validator inputs | Exact bytes agree | Preserve actual sealed, non-cloneable owner, supported policy/revision, real descriptors and validation usage. No alternate validator/raw-owner constructor. |
| `src/experimental/cache/borrowed.rs` | Completion adds test-only `CacheMode::ordered_diagnostic`, `ReleaseControl::ordered_release`, `ordered_event`, and hooks at Lookup, MissReady, all eviction boundaries, BuildBegin/End, PinPublished and successful Release | Reauthor/adapt hooks together with their consumer; preserve mutation order, actual owner/descriptor/token and unchanged debit/failure behavior. |
| `src/experimental_swift_reactor/cache.rs` | Completion adds AcquireBegin/failure wrapper, `ordered_release`, hook implementation, and scan/plan observations | Reconcile entire acquire/failure scope and actual work/instruction coordinates; observe without replacing first failure or mutating policy/budget. |
| `src/experimental_swift_reactor/control.rs` | Completion adds test-only `ordered_coordinates` | Preserve coordinate provenance and account complete return/caller places; no Debug parsing as authority. |
| `src/experimental_swift_reactor/cache_tests.rs` | Completion adds ordered wire/observer/finite/completion support and tests after the common source | This fourth changed file is a real source-closure dependency, although omitted from the earlier five-seam comparison. Reconcile wire writer, gate, schema, typed result and all warning/accounting obligations together; inherited serializer/CODE-buffer limitations remain open. |
| `src/experimental_swift_reactor/mod.rs` | Completion equals canonical; frozen row candidate adds only its private `diagnostic_profile` module declaration | Carry only the root-accepted exact adapter module change into the fresh closure. |
| `src/experimental_swift_reactor/diagnostic_profile.rs`, `_tests.rs` | Frozen row candidate adds these two files | Root accepted the isolated host component during preparation; its new acceptance record, not producer provisional totals, defines that scope. |
| `include/mixer_vm.h`, `include/mixer_vm_capability.h`, `include/mixer_vm_guest_ui.h` | Completion and canonical contain them; row crate copy omits them | Distinguish 129 common Rust-crate/distribution inputs plus two row additions from the 132-path distribution. These C headers were not required by the recorded Rust row compilation. Include them in a future selected distribution/diagnostic invocation closure when applicable; do not claim an omission invalidates a Rust test that did not consume them. |

Every other one of the 132 named completion inputs agrees with canonical. Every
one of the 129 available prior-manifest row inputs agrees with canonical except
`mod.rs`. Exact per-file hashes are in `closure-comparison.json`; complete
completion-to-canonical deltas for all four differences are in `source-diffs/`.
No mixed archive/current combination has been built, measured or accepted.

## Recommended single fresh closure

Begin with the retained exact canonical 132-path set (including C distribution
headers), not a filesystem discovery or arbitrary whole-repository copy. Using the new root acceptance for the isolated row component, add precisely its two source files
and module declaration, bound to that acceptance. Reconcile the four diagnostic
instrumentation/test-support files as one explicitly reviewed patch against this
base. Name every newly authored header/layout/observer/harness/support file and
compiler input before compilation; any generated harness expansion must itself
be an exact input with an authenticated build-to-binary receipt.

The old analyzer selection verifier proposed exactly 132 baseline +132 candidate
members. A candidate with two row files and any header additions exceeds132. Its
future manifest-count schema must be explicitly selected/reviewed with the new
exact count and fixed aggregate bounds before it could qualify this closure.
Neither silently omit the new modules nor call the old132-name verifier valid.
This is a schema/dependency reconciliation, not a selected cap increase or
permission to implement the verifier. The canonical snapshot can be a base now;
the final diagnostic source tree does not yet exist and has no accepted hash.

Retain the instrumented archived closure as historical finite emission evidence.
Preserve its first failures, invalid/failure15 sidecars, CODE/writer/partial-buffer
limits and original timeouts byte-for-byte. A clean byte diff is not a proof that
its former complete logical phase inventory covers new row/header/bridge source.
New source requires fresh work, memory, transfer, Result/caller, lifecycle and
simultaneous-lifetime accounting under unchanged reservations and deadlines.

## Exact construction source and historical budget candidate

Canonical `cache.rs` derives `entries=min(budget.cache_entries,
proof.defined_function_count())`, allocates that many slots and exactly
`budget.active_pins` pins, fixed512 patches,192 resident-index bytes and512
`Option<ScanPlan>` cells; successful construction initializes `next_nonce=1`.
`cache_header_bytes()` uses measured complete types and checked composition:

```
H = sizeof(SwiftFunctionCache) - sizeof(ValidatedSwiftReactor)
    + compute_cache_cleanup_temporary_bytes()
    + 192 + 512*sizeof(Option<ScanPlan>)
B = H + slots*sizeof(SwiftSlot) + pins*sizeof(PinRecord)
      + 512*sizeof(decode::Patch)
```

Index/plan payload is already inH. Do not add it twice or use the cache struct
size alone asH. Slot/pin/patch actual vector capacities must equal requested
counts through the existing exact-capacity contract. Existing `SwiftMeter::base`
is current Cache reservation minus resident bytes; a future observer must also
prove that this equalsB at the selected initial point with no other Cache-category
owner. It cannot learn initialB from the first MissReady or a final usage record.

`docs/swift-ordered-retention-diagnostic-design.md` points to the accepted
attribution runtime audit. Its inspected read-only source points to historical
`verification/swift-current-attribution-runtime/root-selection.json` (SHA256
`ff4a4032f201f26b184fbdcd60c60147ebc8c1acbe1ba85a654b2c574e7a9f94`) and
`selected-command.json` (SHA256
`edf7e7ab5bbd8d34376bde3fa10e4c6177c7713289838b779f051d7b834dd56a`).
The retained stdout contains exactly one 17-field `run_budget` event, equal to the
canonical default maxima in `contract.json`. The historical command separately
retains120,000ms validation,30,000ms run/WASI,170s outer and5s grace/kill waits.
Those are historical observations only. No legacy selection is replayable
permission for this closure or a new target attempt. No source/target/binary was
restored or run and that old result seal was not reaudited in this lane.

Finite accepted emission examples use several narrower invocation budgets. Root
must select one exact complete17-field invocation record, paired with the actual
immutable RuntimeControl. Defaults, historical budgets and independently narrowed
fixtures are different candidates, not implicit interchangeable selections.

## Row acceptance received during this preparation

`acceptance-input.json` binds root
`profile-adapter-acceptance.json`, SHA256
`ee3ef423db5e404b58ab86c1e1123a81113e542c6af8b691e37f5932b3e42381`.
Root accepts only the isolated actual-owner row-body host prerequisite under
Rust1.99.0 macOS arm64. Its independent fixed logical union is11,912 bytes, or
13,904 including constructor/owner places. The450,652,288 source-action plus
cumulative-requested-I/O-byte bound is neither VM credits nor CPU/RSS/stack.
Producer provisional7,504/97,301,024 complete totals are superseded. The copied
provisional accounting remains historical input, not this proposal's accepted
number. Existing row behavior/source acceptance does not join new header,
construction observer, composer, custody, analyzer or caller reservations.
No canonical integration, new CI/compiler target, real binding, runtime or GA
acceptance follows. This lane read only the newly released root record and did
not inspect the independent review directory.
