# Independent Swift capability checkout review

Accepted for the bounded offline source-coverage claim. No actionable missing
input or unexpected workflow mutation was found in the reviewed proposal. This
acceptance is restricted to the frozen ten-member proposal manifest
`99b65cf71f7a07bb2fb8f129b673b82759cbb8c6796dd69a4dce6250a3d73ddc`.
It does not claim a successful hosted checkout, complete CI job, runtime test,
OTA release, or GA gate.

The independently observed source was HEAD
`d04fd5cc71bc72061f18203e414b90869129b4ca`, tree
`c37fc4777830a8e2d1613c70c9867f8033150e5d`. Every selected tree entry was
unchanged from proposal base `ee9f6dc77f88259e2b143fc81dc1085b34a4a943`
and every selected working-tree file equalled its canonical Git blob. Changes
to these scripts, manifests, copied inputs, resources, or rules require renewed
coverage review.

## Observed checks

`python3 -B verification/ci-swift-capability-sparse-checkout-independent/review-v4.py`
passed in 0.941496 seconds. `receipt.json` records Git/Python versions, source
revision/tree, exact Git argv, input/output byte counts and SHA-256, return codes,
and timing. Every child has a 50-second timeout; the audit has a 54-second alarm.
The audit never imports or executes a subject script.

- All ten producer packet members matched the supplied manifest.
- The 60 explicit positive noncone rules retain exactly 370 regular committed
  files / 22,995,155 blob bytes. The independently reconstructed source manifest
  is `d785c9507dba5f371702757f6d0d6150c7502319b3ffc038de339ffe542b5631`.
- Independent finite Git tree reads established the command-input union and
  base/current equality. A 23,336,960-byte canonical Git tar archive contained
  exactly the same 370 regular-file members and bytes; it was read in memory
  and never extracted. No whole-repository tree export was performed.
- Git 2.56.0's native `sparse-checkout check-rules --no-cone` matcher passed
  393 controls: all 370 existing inputs, seven future optional/resource inputs,
  and 16 exclusions/adjacent-name lookalikes. `controls.json` records each case.
- The 145 current VM export members, 13 explicit Android inputs, 11 public
  consumer members, full package Sources/Tests and declared resource directories
  remain present. The native preimage was independently reconstructed from 17
  records and equalled the canonical checked-in fixture and metadata digest.
- The fixed historical pin is a local ancestor of the reviewed HEAD. Its nine
  exact input blobs / 62,506 bytes matched the producer historical metadata.
  The current source cannot replace these historical objects.
- The proposal retains `fetch-depth: 0`. Reconstructing the insertion only within
  `swift-capability-native` reproduced every proposed byte and removing it
  reconstructed the complete base workflow. `git apply --check` passed without
  applying anything. Live workflow SHA-256 stayed
  `fa8fd8887391ffc00f55bc70b370e725cf99ee330c744387f498bea7a2626a88`;
  proposed result SHA-256 is
  `f83defbefd14e710103f4a948f02c15eea8cfd789841d3a5e3593efdb0572eeb`.

The producer's full-tree 17.6 GB total is contextual producer evidence. This
independent audit intentionally reads only the finite selected and historical
closures and does not independently recalculate the full repository byte total.
Blob totals exclude `.git`, retained history, remote transfers, future build
outputs, and external SwiftPM dependencies. No timing improvement is predicted.

## Manual transitive-read review

The invoked job bodies and source were read to establish why the finite inputs
are required. String and syntax searches were navigation aids; no source-pattern
analysis authorizes product behavior or a release.

| Consumer and source location | Coverage disposition |
| --- | --- |
| `.github/workflows/verify.yml`, `swift-capability-native` job | Every original command/tool pin/environment/timeout/artifact remains byte-identical; only checkout configuration is added. The existing accepted Android checkout change in the base workflow is preserved. |
| `build-tests/test_builder.py:20-40` | Imports `build-vm.py`, reads nine fixed production header/contract/schema blobs with `git show PIN:path`, and creates its own temporary Git fixtures. No external retained verification packet is read. |
| `build-vm.py:53-58,165-204,315-322` | Enumerates PATHS from canonical Git objects, checks regular blobs, then writes its own canonical source tar from those bytes. All 145 present export members are selected. Absent `vm/build.rs` remains a rule because its introduction must be visible to the builder's fail-closed check. |
| `scripts/ci/check-android-binding.py:135-160` | Copies tracked package manifest/resolution/Sources/Tests members, full activation Sources and binding includes, three transport inputs, three named Swift fixture inputs, and five host-bridge inputs. All 13 explicit Android/header/host members are selected. It emits a new harness manifest; adjacent scheduler and transport probe siblings are not consumed. |
| Android include/module maps | Binding header reaches `../../transport/include/mixer_ui_transport.h`; host bridge reaches its own headers, transport internal header and binding header. Those exact relative paths and module maps are retained. System headers are runner inputs. |
| `test_native_preimage.py:21-49`, `export-native-preimage.py:32-55`, `generate.py` | The Python test reads complete SDK capability, Java capability and schema subtrees and a checked-in activation fixture. Export `--check` invokes generator `--check`; its generated Swift/Java/schema output comparison requires all retained output files as well as all native preimage members. No Java executable is invoked by this test. Nothing was executed for this review. |
| Six consumed `Package.swift` files | All declarations were read. Activation uses experimental runtime, identity, updates and SDK; identity uses updates; experimental runtime and public consumer use SDK. All local target paths, public headers and copied Fixtures directories are covered. Updates' external Swift Crypto and resolved Swift ASN.1 remain external CI inputs. |
| Public bridge target | Its Package manifest selects `PublicHarness`, including the complete Fixtures directory with its manifest and eight Wasm blobs. Uninvoked historical/internal harnesses and prior packet seals are omitted appropriately. |
| SDK copied tests | The three repository-relative appearance JSON files are retained. The Android runner copies dependency test source, but the invoked job does not execute those dependency test suites. The allowance is conservative coverage, without a dependency-test pass claim. |
| `verification/with-loopback.py:21-30` and Apple toolchain verifier | The TLS wrapper creates its own ephemeral certificate/key; there is no retained certificate input. The Apple verifier is standalone and consumes official runner tools. Neither was executed here. |

The bounded tracked root/package override checks also matched the proposal:
no tracked root Rust toolchain/Cargo/SwiftPM/attribute/submodule/LFS overrides,
or `.swiftpm` under the six consumed Swift package roots, were present at either
reviewed revision. This is a finite checked absence, not a future guarantee.

## Auditor iterations and cleanup

Three failed independent-auditor iterations are preserved without overwriting
their source or evidence. The first extra canonical archive call included four
intentionally absent optional paths, which Git archive refuses. The next two
exposed whole-workflow anchor searches in the independent reviewer; the producer
correctly scoped its search to the target job. `review-v4.py` corrects both
auditor issues, passed, and is the final audit. The correction JSON files bind
the earlier script hashes, actual failed commands, output and limitations.
These were reviewer defects, with no proposal defect inferred from them.

An initial orientation `git status --short --untracked-files=normal` enumerated
existing unrelated dirty-path names and was not used as review evidence. The
formal audit avoided full-tree enumeration. A mistaken read of nonexistent
`.github/workflows/ci.yml` was corrected to `verify.yml`; it wrote nothing.

Only this new independent review directory was written. No workflow or product
file, producer packet, source index, alternate index, checkout, tar extraction,
compiler, JVM, product test harness, network listener/request, native runtime,
simulator/emulator, UI automation, capture, global process inventory, credential
operation, or publication was started. There are no owned persistent processes
or disposable environments to clean up. Other projects' processes and data were
preserved.

The packet is released read-only. Root owns any later application and delivery.
Remote Actions filter/checkout behavior, historical object availability, checkout
duration, external SwiftPM resolution and complete job outcomes remain pending.
Paused simulator/emulator/UI/capture checks and physical device, operational,
release and GA gates remain pending.
