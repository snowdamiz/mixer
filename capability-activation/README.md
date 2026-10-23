# Installed capability material

`MixerCapabilityActivation` currently validates and retains immutable installed
material only. It exposes `CapabilityMaterialFile` and
`InstalledCapabilityExecution(identityJSON:materials:trustRootsJSON:privateContainer:)`.
The result exposes its runtime fingerprint. It does not expose execution,
selection, adapters, policy DTOs, a verifier, sessions or effects enablement.

The embedding supplies trusted installed identity and raw root bytes, the exact
canonical material files, and an application-private container obtained through
its platform API. The initializer bounds inputs before taking owned snapshots,
checks their exact SHA-256 bindings, enforces the frozen closed schemas and
canonical material encoding, and retains one private `ReleaseVerifierV3` context.
The container is retained as a trusted native input; this initializer does not
inspect, create or prove the privacy of that path. It creates no adapter, session,
task, directory or file and performs no network operation.

Materials require sorted ASCII keys, compact JSON, ASCII escaping, shortest
unsigned decimal integers and exactly one final LF. Roots instead use the existing
closed `[TrustRoot]` shape and are bound by their exact raw bytes. Empty installed
grant sets stay empty. The package never invents storage namespaces.

The linked SDK native and schema identities must equal the frozen execution
contract references. To capture the actual native digest preimage, run
`python3 capabilities/tools/export-native-preimage.py --check --output <output>`
from the repository. That preimage is sorted compact ASCII JSON with **no** final
LF. It is distinct from both the hexadecimal digest text and material encoding.
The helper does not import or modify the generator.

These checks bind the known concrete SDK adapter implementation family. They do
not attest arbitrary engine, compiler, SDK or dependency hashes declared by a
descriptor, prove complete build graph capture or consumption, or inspect a final
signed application binary. Test descriptors label their remaining test metadata.
No downloaded release is authorized by this material value alone.

The package depends on the experimental bridge and must link its single native
archive containing both C families and the shared registry. Do not also link the
default runtime archive. Later durable v3 selection, bounded validation, concrete
adapter construction, startup, effects, health and recovery need separate slices.
The old verifier, identity and activation APIs are unchanged.

Host tests use the qualified experimental archive, for example:

```sh
swift test --package-path capability-activation \
  -Xcc -I/path/to/experimental/host/include \
  -Xlinker -L/path/to/experimental/host/lib
```

Qualification receipts are in `verification/capability-installed-material/`.
Host checks do not qualify physical iOS/Android operation, published packages,
application signing, installed graph attestation or an OTA activation route.
