# Swift capability checkout source contract

This packet proposes only a sparse-checkout addition in the existing
`swift-capability-native` job. No workflow edit, commit or push was performed.
The 4m03s capability checkout and 11s modified Swift checkout were supplied by
the controlling agent; this offline packet does not independently verify those
remote timings or predict the replacement timing.

The frozen source is commit `ee9f6dc77f88259e2b143fc81dc1085b34a4a943`, tree
`076842155358f5be57a6f97af73577687a32a6d4`. The live workflow base SHA-256 is
`fa8fd8887391ffc00f55bc70b370e725cf99ee330c744387f498bea7a2626a88`; it already
contains the accepted, uncommitted Android owner checkout change. The proposed
future diff preserves those bytes and every command, runtime/tool pin, timeout,
artifact, trigger, environment variable and other job. Its resulting workflow
SHA-256 is `f83defbefd14e710103f4a948f02c15eea8cfd789841d3a5e3593efdb0572eeb`.

## Retained closure

The 60 explicit noncone patterns select exactly 370 committed regular files /
22,995,155 bytes, against 330,732 files / 17,646,706,549 bytes in the frozen tree.
The byte figures describe committed working-tree blobs, excluding `.git`, Git
history and future build/SwiftPM output. They are not measured transfer or disk
usage figures. The source manifest SHA-256 is
`d785c9507dba5f371702757f6d0d6150c7502319b3ffc038de339ffe542b5631`.

| Consumer | Retained current inputs | Reason |
| --- | --- | --- |
| Apple toolchain step | `scripts/ci/verify-apple-toolchain.py` | Standalone standard-library tool; platform executables are runner inputs. |
| Original builder boundary tests and C probes | `experimental-capability-runtime/build-vm.py`, complete `build-tests/` | `test_builder.py` imports this builder, creates original temporary Git fixtures and reads the historical pin below. The two C probes use the emitted VM headers/archive. |
| Frozen VM builder | All 145 current members of `build-vm.py:PATHS` | Cargo manifest/lock, `src/`, headers, profiles, tests, tools, three contracts, capability schema/hashes, and the legacy runtime header. The builder reads them through Git blobs at `$GITHUB_SHA`; retaining their working-tree paths also keeps the current export explicit and avoids intentionally depending on one-object lazy reads. |
| Experimental bridge tests | Package manifest, complete `Sources/` and `Tests/`, `verification/with-loopback.py` | The wrapper creates its certificate and scratch TLS fixture at runtime. No retained certificate or old receipt is read. It is not executed for this audit. |
| Public consumer | `verification/capability-bridge-review/Package.swift` and complete `PublicHarness/` (11 current members together) | SwiftPM copies the complete `PublicHarness/Fixtures` resource directory, including its manifest and all eight Wasm files. Historical review receipts, internal harnesses and candidate copies are not inputs to the invoked SwiftPM target. |
| Installed material/native preimage | Exact `test_native_preimage.py`, exporter, generator, complete capability Java and schema subtrees, SDK capability source, activation test fixtures | The exporter uses `generate.py --check`. Both enumerate complete native source subtrees; excluding an inconvenient source file would change the identity preimage. No Java program is executed by the Python test. |
| Activation and transitive Swift packages | Manifest/resolved files plus complete `Sources/` and `Tests/` for activation, experimental runtime, runtime identity, updates and SDK | Local package edges are activation → experimental runtime/runtime identity/updates/SDK; runtime identity → updates; experimental runtime → SDK. SwiftPM manifest target paths and declared copied fixture directories remain intact. |
| Android binding runner | `scripts/ci/check-android-binding.py`, 13 explicit Android/header/transport/host fixture files | At lines 135–148 the runner copies tracked package manifests/Sources/Tests, all activation Sources and binding include files, three transport files, three Swift host fixture files, and five named host-bridge files. It does not copy scheduler/transport probe siblings. Header and module-map relative paths are retained. |
| Copied SDK test source | Three exact appearance JSON inputs | `AppearanceDescriptorV2Tests.swift` and `AppearanceV1Tests.swift` reference these repository-relative paths. Dependency tests are copied by the binding runner, although the job does not explicitly execute those dependency test suites. Keeping their three canonical inputs is a conservative source-complete allowance (270,289 bytes). |

`source-closure.json` records every selected file's mode, Git blob, byte count,
SHA-256 and consumer groups. It includes the 11 current Swift/Cargo policy and
resolution manifests and every resource member. No invoked step in this job runs
`scripts/check-policy.py` or scans all repository manifests, so the unrelated
historical verification manifests needed by the separate `swift` job are not
required here. No whole historical evidence packet or its checksum seal is read
by these commands. Complete declared fixture subtrees are retained; old packet
logs and seals are excluded.

Four absent paths are intentional future-safe rules: experimental runtime,
SDK and public bridge `Package.resolved`, plus `vm/build.rs`. The latter is in
the builder's export list specifically so its presence fails closed. An absent
file is not supplied or invented by the proposal.

The full committed metadata also confirms there is no tracked root
`rust-toolchain`, `rust-toolchain.toml`, `.cargo`, `.swiftpm`, `.gitattributes`,
`.gitmodules` or `.lfsconfig`, nor a `.swiftpm` subtree in the six consumed
SwiftPM package roots. Thus this frozen checkout does not omit a tracked local
toolchain, package-configuration, attribute or submodule override. This is a
checked absence at the stated revision, not a promise about later changes.

## History and canonical data

Keep `fetch-depth: 0` exactly. `test_builder.py:23,31` reads pinned commit
`1adb25c48a8723f56ed2649712fe5e357920c53e` using `git show PIN:path` for nine
production header/contract/schema blobs. The audit verifies that commit is an
ancestor of the selected source and binds all nine members / 62,506 bytes in
`historical-inputs.json`. Retaining current files cannot substitute for the
historical Git objects. Shallow fetch depth 1 would not satisfy this read.
Remote availability and filtered historical object retrieval remain pending.

The three current public VM header hashes and fixed transport contract match
the builder's constants. The SDK legacy header equals the VM legacy header.
The checked-in native preimage is exactly SHA-256
`4fcc770e62d39b415e657ce03aa11fa7fb83ee8bfe1a99567716e9b4372d1c59`, matching
the capability metadata field; this audit does not execute its generator or
reconstruct native semantics. The three appearance JSON hashes are retained in
`source-closure.json:canonical_data`. Complete activation, update, identity and
public-bridge fixture resources are selected, including their canonical hashes.

The existing activation/runtime-identity/updates `Package.resolved` files remain
unchanged. The updates package uses external Swift Crypto 5.0.3; its resolved
set also contains Swift ASN.1 1.7.3. Those external checkouts and official runner
tools are CI inputs beyond this repository's source closure. They were not
downloaded, inspected or executed here.

## Executed verification and boundaries

Run `python3 -B verification/ci-swift-capability-sparse-checkout-contract/audit.py`
from the repository root to repeat the finite source audit at this exact base.
It records Git/Python versions, exact argv, source/tree identity, command
timeouts, exits, elapsed time and bounded output digests in `receipt.json`.
The retained output is the selected canonical source metadata, historical
metadata, source manifest, rule controls, base workflow and proposed patch.
Full-tree work reads metadata once and reads only selected blobs afterward;
there is no 17.6 GB extraction or worktree materialization.

The local Git 2.56.0 native noncone `sparse-checkout check-rules` matcher covers
every current required member and 12 explicit inclusion/exclusion controls.
The selected set equals the declared union; all 370 live selected inputs match
the frozen Git blobs. `git apply --check` verifies the data patch can apply to
the supplied workflow without writing it. Removing the addition reconstructs
every original job byte. The workflow is rehashed unchanged at completion.
The audit's direct and transitive Git commands have a 50-second timeout, and
the whole Python audit has a 54-second alarm. This packet is source-only
coverage evidence and cannot authorize OTA, release or GA acceptance.

No compiler, product/native/JVM test harness, loopback fixture, native runtime,
simulator/emulator, device, UI automation, screenshot, global process inventory,
network request, publication or credential operation was started. The audit
creates no scratch repository, alternate index, materialized checkout or
persistent child; its owned cleanup is complete with no disposal required.
Other projects' processes and data were not inspected or changed.

The proposal is released read-only for independent review. Application,
publication, remote CI checkout duration and actual complete job outcomes are
pending. Actions' hosted Git/filter behavior, remote historical object
availability, SwiftPM resolution and runtime behavior remain unverified. Native
simulator/emulator/UI/capture checks remain paused under the supplied override;
physical-device, operational, release and GA gates remain pending.
