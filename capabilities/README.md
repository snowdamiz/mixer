# Typed capability v1 slice

This is an independently authored W06 foundation. `schema/v1.json` is the closed
capability contract; `tools/generate.py` emits typed Swift DTOs and operation/result
dispatch, Java DTOs and operation descriptors, schema hashes and an exact native
bridge implementation identity. No source analysis authorizes a release. The schema
is version1, and both capability IDs include `.v1`; every wire message must match the
installed exact schema hash. The schema hash includes the wire rules, descriptor and
closed type vocabulary. Unknown versions, IDs, operations, fields or hash values fail.

`MixerCapabilities` is an additive SDK product. Its public APIs are:

- Generated `HTTPRequestArguments`/`HTTPResponse`, `Header`, `KV*Arguments`/responses,
  `CapabilityOperation`, `CapabilityResult` and `CapabilitySchemas`.
- `CapabilityCodec` encodes calls/cancellation/completions and strictly decodes raw
  inbound bytes or a completion bound to an expected call. Public value models have
  no raw `Codable` path that skips preflight. Byte snapshots, exact fields, duplicate
  keys after escape decoding, UTF-8/surrogates, nesting, values, strings, byte sizes,
  canonical padded base64 and canonical unsigned decimal UInt32 are checked. Integers
  such as `1.0`, `1e0`, booleans in numeric fields and out-of-range numbers are rejected.
- `CapabilityPolicy(installed:manifest:)` validates and intersects grants. Permissions,
  exact HTTPS origins/methods, and storage namespaces can only shrink. The installed
  grants are trusted app policy. Manifest grants must come from an already verified
  compatible release, never raw update JSON. This module does not verify signatures.
  Current release-v1 carries capability hashes only: narrower per-release grants
  still require an explicitly signed release-contract extension and verifier integration.
  An unsigned sidecar cannot supply these grant values for production execution.
- `CapabilityHost` owns one originating guest's random session, issued request slots,
  generation checks, permission checks, background async dispatch, deadlines,
  cancellation and exactly one terminal response to the original delivery closure.
- `GuestCapabilityClient` supplies typed async methods over installed reserve/invoke/
  cancel imports. It carries encoded values; it does not load or execute Wasm.
- `AppPrivateKeyValueStore` is a real native serial actor for the storage protocol.
  `CapabilityNativeIdentity.sha256` is the generated bridge implementation identity.

Swift and Java codecs accept the same strict v1 byte representation. The generator
uses only this owned schema and original generator/runtime source. It never loads
classes, selectors, method names or native pointers from a guest. Java's public
`CapabilityCodec.decodeInbound(byte[])`, `encodeInbound`, `decodeCompletion` and
`encodeCompletion` are the JNI-facing encoded-value surface. They are ordinary Java
APIs, not a completed JNI transport. DTOs use Java8 library/language features and
classfiles; the qualification build also runs official D8 with minimum API28. Actual
JNI integration and the minimum-device matrix remain open.

JSON keys compare decoded Unicode scalar sequences, without normalization. All
identifiers, namespace/key values, URLs and header text in this version are ASCII.
Non-ASCII composed/decomposed forms fail rather than alias. Application text/binary
values cross as canonical padded base64 and are not normalized or interpreted here.
HTTP URLs are lowercase `https://` with bounded lowercase DNS-style labels and an
optional canonical non-default port; no userinfo, fragments, IPv6, backslashes,
spaces or lowercase/malformed percent escapes. Header names are lowercase, unique
and bounded. Cookie and transport-controlled headers fail closed.

One `CapabilityHost` must be privately bound to **one originating guest instance**.
The embedding must not select a host by an untrusted wire session string. Each host
generates its own UUID, and IDs can only be reserved from that host; another host's
session or a stale generation is rejected. Default capacity64, maximum256; slot is
UInt16 and generation nonzero UInt32. A slot retires instead of wrapping. Reserving
an ID consumes quota. Cancellation can abandon an unused reservation. A call's
delivery callback is retained by the host; the cancellation sender cannot replace it.

Completion and cancellation race on the host actor. Whichever terminal transition
is serialized first wins. Later callbacks/cancellation cannot complete another
request. Close sends cancellation once, cancels work/timers and removes ownership.
Deadline/cancellation keeps a running native adapter's slot leased until that adapter
acknowledges exit; an adapter ignoring cancellation cannot allocate unbounded work by
cycling guest requests. Adapters are trusted installed code and must cooperate with
cancellation. Timers bound response lifetime, not an OS call's physical duration.
Failures are fixed codes without native exception text or credentials. Reserved
requests that were never submitted have no completion to deliver.

HTTP has a real bounded schema and typed installed transport hook, **no bundled
production network adapter**. Default transport is unavailable. Installed transports
must enforce the request64KiB/response256KiB limits before allocating entire responses,
OS TLS, explicit headers only, no ambient credentials/cookie storage, no retries and
no redirect following. The host rejects returned3xx responses. Any future redirect
support must reauthorize destination origin **and method before sending**, and qualify
credential forwarding separately. Streaming, resumable transfers and connectivity
are unavailable in this version; they need explicit schemas and tests. Codec/model
validation after a custom callback cannot retroactively bound its network allocation.

Storage's dedicated host-supplied directory must have an existing private parent.
The adapter creates mode0700, uses an exclusive process lock, descriptor-relative
regular files with no symlink/hard-link following, and validates namespaces/keys as
identifiers (no slash, dot components or traversal). Physical components use canonical
lowercase base32 of the exact ASCII bytes; case-insensitive filesystems cannot merge
distinct grant namespaces or keys. Maximum32 installed namespaces,
64KiB/value, 4MiB total and1024 entries; configured limits may be lower. Empty values
are distinct from missing values. Writes use an owned temporary file, file `fsync`,
atomic rename and directory `fsync`; replacement cannot expose a partial value.
Recognized abandoned transactions are pruned on open/next inventory. Missing values
return `found=false` and empty bytes; deletion is idempotent. An uncertain failed
mutation poisons the store until close/reopen. Cancellation observed at the precommit
check aborts the write; once commit starts an effect may remain even if the response
is cancelled. Close cancels response ownership; it does not synchronously drain native
OS effects. Re-read
the value to resolve that outcome. No cross-key transaction or compare-and-swap is
implied. The directory, ancestors and native policy are trusted app-private state;
malicious host/filesystem rollback and physical power-loss behavior are unqualified.

Adding this native store/capability requires a new store binary. Embed the generated
`CapabilityNativeIdentity.sha256`, exact schema hashes, installed grants/configuration,
toolchain, platform, native dependencies and other SDK bridge identities into the
installed runtime fingerprint. A release's declared capability map cannot register a
new adapter, permission or binary implementation. Regenerate after source edits and
require `generate.py --check` in release builds. This slice exposes the identity; the
compiler/publication pipeline and immutable package registry integration remain open.
Customer extension registration, plugin trust policy, cloud signing and publication
are unavailable; no arbitrary plugin is accepted by the closed dispatch table.

```sh
python3 capabilities/tools/generate.py --check
swift test --package-path capabilities
swift test --package-path sdk
swift build --package-path capabilities --product capability-probe
# The receipt contains the exact installed JDK and SDK commands.
python3 capabilities/tools/codec-differential.py
python3 capabilities/verification/verify.py
```

`verification/receipt.json` records source hashes, commands, tools, outputs and scope.
Host tests are not device receipts. Official WASI target compilation is not an owned
VM acceptance pass: the full Swift ABI/import/scheduler profile and actual guest
transport still need integration. Existing SDK/UI behavior is covered separately.
FieldLog must consume an immutable published package from its separate repository;
this checkout/test adapter is not dogfood qualification. W06/W09/GA remain open,
including all other Section9 families, first FieldLog plugin, physical lifecycle and
permission tests, security review, migration, observability and operational support.
