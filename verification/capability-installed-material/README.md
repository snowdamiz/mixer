# Installed material qualification

Final candidate2 is the material-only `MixerCapabilityActivation` package and the
read-only native-preimage helper. The owner source freeze is
`2026-10-23-candidate-2/source-manifest.sha256`:
`cd9f855902ee2221516c8aafcdd88ddbab138f57cddc2c6489361e9f2869abd9`.
Its 135 inputs include exact frozen v3 verifier, identity2 and bridge dependency
sources, original fixtures/tests, known schema contracts and generated native
source inputs. Source and export hashes were checked before and after each owner
command. Build caches are excluded from source/evidence manifests.

All 16 original tests passed in debug, release and Swift TSan (48 test-case
executions). They cover real linked native/schema identity bindings, zero/one/two
capabilities, exact roles and every material digest, mandatory/unknown fields,
canonical and malformed JSON, configuration limits, directory traversal forms,
empty grant denials, family/order/count/origin rules, roots raw binding and strict
decoding, byte/depth/value limits, externally mutable Data ownership, no directory
creation, and 32 concurrent immutable initializations/value copies. TSan covers
Swift/C shim code, not system frameworks or the reused Rust archive.

The native-preimage helper's three original tests pass, including read-only
generator `--check`, repeat equality/no production writes, copied-input source
mutation, normalized schema preimage, excluded identity/probe files, text newline
semantics and protected output paths. The exact 17-source preimage is 2394 bytes,
has no final LF, and hashes to the linked/frozen native identity
`4fcc770e62d39b415e657ce03aa11fa7fb83ee8bfe1a99567716e9b4372d1c59`.
Material fixtures instead have one final LF. They were authored independently;
no identity-parser synthetic native fixture was imported. Other test metadata and
non-attested build fields are labelled in fixture provenance.

An external non-`@testable` release-linked client constructed the public value and
checked its fingerprint. A positive external typecheck passed; five negative
compiles proved that private state, session creation, effects enablement, an
independent verifier and caller adapters are unavailable through this API. The
client links the qualified single experimental archive
`a015ff65980422dd0b9c5cad2e28741d1e5ba478e0f657dcaedf75477d553b72`.
Its pinned native dependency receipts establish archive provenance; these material
tests do not execute the native session registry.

The compile-only sidecar passed official iOS arm64 and Android arm64 target
module/object compilation with warnings as errors. It records exact commands,
SDK/compiler versions and artifact hashes. It is not a mobile application link,
device execution, lifecycle, signing or publication receipt.

Candidate1 is preserved unchanged. It was green but root's independent source
review found that arbitrary role Strings were hashed before a length bound.
Candidate2 checks at most 129 UTF8 bytes and rejects lengths above 128 or invalid
ASCII before hashing/concatenation; its tests include a 1 MiB malformed suffix.
No other production behavior changed between these candidates.

`run.py --label <new-label>` freezes and runs the owner matrix. `cross-compile.py`
binds the final host receipt and compiles that exact export. `finalize.py` audits
the receipts/logs/artifacts/contracts and preserved legacy source bytes, then
seals source and evidence manifests. Root owns independent integration review and
commits. No files from other active lanes are staged by this lane.

This value creates no adapter, task, native/session handle, directory or file.
The trusted private container path is an embedding assumption, not a proven path.
Known SDK identity equality does not prove arbitrary declared engine/toolchain/
dependency hashes, complete graph capture/consumption or a final signed binary.
Durable v3 selection, same-config validation, concrete adapters, startup, effects,
health/recovery, published packages, physical phones and GA gates remain outside
this slice. No device was queried or run.
