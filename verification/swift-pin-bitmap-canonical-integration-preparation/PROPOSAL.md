# Canonical bitmap-pin integration preparation

**Canonical installation is unselected.** Root reports manual run `40824584975`,
attempt 1, failed after about 7m15s in its six-child step. The precise failure and
independent actual artifact acceptance have not been relayed to this lane. This
packet makes no runtime pass claim, dispatches nothing and changes no canonical
source. It prepares the finite integration boundary while actual review proceeds.

The selected 24-member seal is
`0210ab9c252c6f7a5a3eff077e36c2811c79351d916d78b75b2cda88e2bdf85c`.
The complete 136-member canonical closure remains
`af0db424af7b08f013d2c6a8894f4d156f76bc5f493620c6f2c0b85d3bf4c48b`.
The prospective selected closure is
`e9282e05cea70d4aceaf6a145fb9f971acb023dd41a7d4651216753666305ba1`.
Root supplied delivered revision `1eec8e0fc270c0409c8920ee22fd2374f3bd249f`
and Git tree `f20be7de5a047f1983931961cc3d774e56de80a3`; this lane does not
run Git or independently resolve HEAD.

## Exact proposed source set

Each path below maps to the same relative path under
`verification/swift-pin-bitmap-match-binding-correction/candidate/vm/`.
The manifest-directed preflight verifies every old/new byte count and SHA-256,
all 121 unchanged members, and exact reconstruction of both sides of each diff.
`canonical-to-candidate.diff` is the complete 15-file unified source diff.
`receipt.json` holds each exact source preimage and prospective postimage.

| Canonical path below `vm/` | Integration role |
| --- | --- |
| `src/experimental/cache/borrowed.rs` | Private sealed generic pin selection/release hooks; defaults preserve other cache modes' original linear search and work trace. |
| `src/experimental_swift_reactor/cache.rs` | Swift-only free-pin bitmap, initialization/publication/release checks and owner/temporary storage accounting. |
| `src/experimental_swift_reactor/cache_tests.rs` | Seven added bitmap tests, retained regressions, caller-owned constructor output helper and exact lint/format correction. |
| `src/experimental_swift_reactor/lifecycle_tests.rs` | Source-derived constructor/pin work expectations and constant assertion lint correction. |
| `src/experimental_swift_reactor/value_operation_tests.rs` | Required caller of the changed test helper in `execution_tests`; passes its output slot and consumes its full result. |
| `src/experimental_swift_reactor/execution_tests.rs` | Caller-owned test helper output storage and retained assertion/format corrections. |
| `src/experimental_swift_reactor/bulk_memory_operations_tests.rs` | Retained tests with actual formatter/lint bytes. |
| `src/experimental_swift_reactor/control_operations_tests.rs` | Retained tests with actual formatter/lint bytes. |
| `src/experimental_swift_reactor/diagnostic_profile_tests.rs` | Retained tests with actual formatter/lint bytes. |
| `src/experimental_swift_reactor/diagnostic_result_v1_tests.rs` | Retained tests with actual formatter/lint bytes. |
| `src/experimental_swift_reactor/memory_growth_operations_tests.rs` | Retained tests with actual formatter/lint bytes. |
| `src/experimental_swift_reactor/memory_operations_tests.rs` | Retained tests with actual formatter/lint bytes. |
| `src/experimental_wasi/accounted_tests.rs` | Retained tests with actual formatter/lint bytes. |
| `tests/experimental_guest_ui_allocations.rs` | Retained tests with actual formatter/lint bytes. |
| `tests/experimental_guest_ui_validation.rs` | Retained tests with actual formatter/lint bytes. |

## Contracts and consumers

Only the first two files change production implementation. `CacheMode` remains
crate-private and sealed; the Swift cache module is private. No public function
signature, C header, export family, Wasm feature profile, capability schema,
dependency, signed authority or validation grammar is changed. The constructor
output-slot compatibility edit is to a test helper; it is not a public ABI change.
Source inspection is not an emitted binary ABI proof or release authorization.

The bitmap holds one bit per free pin, selects the lowest free slot and checks
layout/live-count agreement before acquisition. Publication clears the bit;
validated release restores it after the original record/ledger release. Release
does not add stop polling, preserving terminal-owner cleanup. Failed preparation
must retain the original record and token obligations. Three copies of the added
named `DensePinInventory` enter construction, operation and cleanup accounting.
Constructor work increases by one credit; successful bitmap selection costs five
credits. The lifecycle expectations change accordingly. These are intended source
contracts awaiting exact executable acceptance, not findings that execution passed.

All 17 `SwiftRunBudget` fields/defaults and the complete control source are byte
identical: 64 residents, 64 pins, 64 frames, 86 tickets, 64,000,000 cache-work credits,
256 MiB combined bytes and all other original ceilings remain. The experimental
512-capacity host profile is separate and is not promoted. Original named tests
are retained; the static roster adds seven cache tests. Runtime test counts must
come from the actual run, including all nine Node oracles.

The following live consumers require no source-binding edit for these overlays:

- `runtime/build-vm.py` exports `vm` from the requested commit and records its
  archive/library hashes; its Swift header mirror is unchanged and equal.
- `experimental-capability-runtime/build-vm.py` exports its enumerated source
  paths from the requested commit. Its three exact header pins, export set,
  required paths and source bounds remain valid; no Rust implementation hash is
  hardcoded. Both builders acquire the new VM source when built at the new commit.
- `capabilities/tools/generate.py` and `export-native-preimage.py` hash the
  capability schema plus Swift/Java capability implementation directories, not
  VM Rust. `capabilities/schema/hashes.json` and generated identity files need no
  amendment. A later built/published runtime must retain its actual new library
  identity; this proposal creates no installed runtime fingerprint.
- `scripts/check-policy.py` checks dependency manifests and gate integrity;
  `check-sdk-package.py` compares public/development Swift target graphs.
  Dependency manifests, headers and profiles are unchanged.
- Ordinary envelope and shared-cache fixture adoption bind their own frozen
  source packets. Their dependency manifests have no live `vm/` member, so the
  canonical promotion neither replaces their frozen subjects nor requires their
  seals to change.

No directly affected static public source manifest was identified in the bounded
live consumer paths inspected. Exact consumer input hashes are in the receipt.
The root-owned `PLAN.md`, `STATUS.md`, `work-graph.json` and any new integration
receipt must state the actual selected outcome when a slice is accepted. Historical
baseline/candidate manifests, workflows and packets stay frozen. A historical
manual runner that insists on this old canonical baseline may intentionally reject
a future changed HEAD; rewriting its seal to hide that drift is not integration.

## What ordinary CI will exercise

The inspected `.github/workflows/verify.yml` has SHA-256
`a90bab7dea218e5a098e45eb370e9b666afdf0bda9100cb35ec14dfc779de024`.

- The `rust` job runs default Debug/Release tests, all six experimental features
  in Debug/Release, then those feature sets again with `--ignored`, which explicitly
  invokes the nine unchanged ignored Node reference tests. It also runs Swift
  reactor-only Debug/Release, strict **library-only** reactor Clippy, allocation
  isolation, transport host regressions and public native capability C clients.
- The `swift` job builds the committed default-feature VM static archive and runs
  Swift runtime, activation and public wrapper tests. Default features do not
  enable the changed private Swift reactor. It also retains the SDK/generated
  consumer and unrelated policy/envelope/capability checks.
- The `swift-capability-native` job builds the committed experimental capability
  archive and tests its Swift/C consumers. Its selected feature does not enable
  the private Swift reactor; this job still exercises archive/source provenance
  and public integration compatibility.
- Android owner/JVM, services and the frozen Swift cache-state fixture jobs retain
  their existing independent scopes.

Ordinary CI does **not** include `cargo fmt --check` or strict all-target Clippy.
The selected manual regression was intended to supply those checks and combined
699 Debug/699 Release tests with zero ignored tests and all nine Node oracles.
That failed run cannot satisfy the missing acceptance. No ordinary workflow change
is proposed by this lane; root must decide the next bounded corrective action from
the actual failure. Nothing here establishes a lower Rust MSRV than the observed
manual host compiler, Rust 1.99.0, or changes the frozen Rust 1.98.1 fixture policy.

## Guarded inspection and promotion boundary

Run `node verification/swift-pin-bitmap-canonical-integration-preparation/check.mjs preflight`.
The pure source/data checker imports only Node `fs`, `path`, and `crypto`, caps
input/output sizes and diff work, refuses path traversal/symlinks and foreign writes,
loads no subject code, and has no command/network/process probing path. It checks
selected seal/manifest identities, all 136 canonical inputs and prospective members,
the exact 15-file edit set, diff reconstruction and consumer/canonical postflights.
One initial checker parse error is retained explicitly in `receipt.json`; the
corrected checker passes 689 checks on Node v22.23.3, including independent replay
of the serialized unified patches. This is checker execution,
not a Node Wasm oracle or product runtime run.

After root resolves the failed run, selects an exact accepted candidate, and relays
independent actual acceptance, root may rerun this preflight immediately before its
coordinated canonical copy. Apply all selected paths together and leave the 121
unchanged members byte-identical. `node .../check.mjs installed` is a read-only
post-apply closure inspection that expects the exact selected candidate in canonical
`vm/`; it emits a compact result to stdout and does not overwrite this preparation
receipt or source diff. A changed corrective candidate needs a new explicit binding,
not an exception to the pinned checks. Root then records the actual integration,
commits/pushes the coherent slice and inspects ordinary CI under existing authority.

Native/UI/capture/phone, local compiler/process-custody, published-package FieldLog,
store/customer and GA checks remain pending. No instance, held process, socket,
capture, local compiler or product runtime was started or probed, and no scratch
cleanup or disposal is inferred.
