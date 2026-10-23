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
- `URLSessionHTTPTransport` is an explicitly installed, bounded native HTTP adapter
  using Foundation URLSession (FoundationNetworking on Android). It is unavailable
  in the WASI guest module; no guest networking bypass is provided.

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

HTTP now includes `URLSessionHTTPTransport(maximumConcurrentRequests: 64)`, with
configured capacity1...256. The host's default transport remains unavailable; the
trusted embedding explicitly installs it after constructing its intersected policy:

```swift
let transport = try URLSessionHTTPTransport(maximumConcurrentRequests: 32)
let host = try CapabilityHost(policy: policy, http: { try await transport.request($0) })
```

The adapter validates even directly constructed typed requests before starting I/O.
The unchanged v1 limits are HTTPS URL4096 bytes,32 unique headers,64-byte names,
4096-byte printable ASCII values, request64KiB, response256KiB, deadline1...30000ms.
Each request has one data task in a private ephemeral session: cache, cookie and
credential stores are disabled, automatic cookie handling is disabled, no delegate
accepts credentials, and TLS uses normal system verification. Darwin server-trust
challenges use default handling; FoundationNetworking verifies in its native backend.
There is no public custom session, protocol class, certificate or trust override.
An explicit `authorization` header is permitted by the frozen schema as request
data; this adapter injects no account secret or ambient credential. Default
`Accept-Encoding` is `identity`, `Accept-Language` is empty and `User-Agent` is the
fixed `MixerCapabilitiesHTTP/1`; explicit allowed values can replace those defaults.
The OS still supplies HTTP framing headers and its normal network/proxy behavior.

All3xx responses and redirect callbacks fail with `redirectDenied` before a follow-up
task is authorized. Future redirect support must reauthorize destination origin
**and method before sending**, with a separate credential-forwarding policy. There
are no adapter retries; OS protocol retransmission/reconnection is not an exactly-once
server-effect guarantee. Credential negotiation (including client certificates,
HTTP authentication and proxy authentication) fails with `ioFailure`. Compressed
responses fail with `invalidResponse`; this avoids exposing a decompressed body with
an original encoding header. No automatic JSON/text decoding occurs.

Response headers are bounded at the delegate boundary and normalized to lowercase,
sorted wire headers. Cookie and HTTP framing/hop headers are removed. Malformed or
oversized metadata fails before retained body buffering. A declared body over256KiB
fails immediately; unknown/deceptive lengths are checked again on each received
chunk, and nonzero length mismatches fail. HEAD/204 return no body; HEAD representation
length metadata does not allocate a body. Zero-byte bodies are valid. The adapter
bounds its own retained body/metadata, not opaque URLSession/native TLS buffers or
the OS HTTP parser's header allocation/coalescing before delegate delivery.

The request captures a process-local monotonic deadline before preflight. Admission,
received headers/chunks and the final successful-result transition check that deadline;
a delayed watchdog cannot authorize a late success. Swift task cancellation and a
monotonic watchdog race through one locked terminal result. This is not hard real-time
network termination. Failures cancel/invalidate the session; success finishes and
invalidates it. A native capacity lease is released only when URLSession acknowledges invalidation.
Late callbacks cannot resume a continuation twice. Cancellation/deadline may occur
after a server accepted a mutation; callers must resolve uncertain remote effects.
Streaming/resumable guest transfers and connectivity remain unavailable schemas.
Custom installed callbacks must independently enforce equivalent bounds: codec/model
validation after their return cannot retroactively bound network allocation.

Android dynamic Swift compilation links the official SDK's FoundationNetworking
backend. With the installed Swift6.3.3 Android SDK, static Swift linking additionally
requires `-Xlinker -lssl -Xlinker -lcrypto -Xlinker -lz`; the separate receipt preserves
the original unresolved-symbol failure and the successful aarch64 link with those
flags. They match the SDK's `libcurl.pc` OpenSSL/zlib dependency declarations; its
stale absolute build paths are not used. Package manifests stay portable. Native
dependency packaging/notices/security review and Android trust-store execution are
pending; cross-compilation does not qualify an APK or establish shipped library versions.

Storage's dedicated host-supplied directory must have an existing private parent.
The adapter creates mode0700, uses an exclusive process lock, descriptor-relative
regular files with no symlink/hard-link following, and validates namespaces/keys as
identifiers (no slash, dot components or traversal). Physical components use canonical
lowercase base32 of the exact ASCII bytes; case-insensitive filesystems cannot merge
distinct grant namespaces or keys. Maximum32 installed namespaces,
64KiB/value, 4MiB total and1024 entries; configured limits may be lower. Reopening
checks all retained bytes and entries against those configured limits and fails
with `quotaExceeded` if either is exceeded, preserving values. To narrow a policy,
the trusted host must first prune under its previous limits. Empty values
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
# Separate transport receipt; prior receipt intentionally pins its earlier source.
python3 capabilities/verification/http-transport/verify.py
```

`verification/receipt.json` records source hashes, commands, tools, outputs and scope.
Host tests are not device receipts. Official WASI target compilation is not an owned
VM acceptance pass: the full Swift ABI/import/scheduler profile and actual guest
transport still need integration. Existing SDK/UI behavior is covered separately.
FieldLog must consume an immutable published package from its separate repository;
this checkout/test adapter is not dogfood qualification. W06/W09/GA remain open,
including all other Section9 families, first FieldLog plugin, physical lifecycle and
permission tests, security review, migration, observability and operational support.
The separate HTTP transport receipt covers injected URLProtocol lifecycle/boundary
tests and a real local untrusted-certificate rejection without changing trust stores.
It does not qualify successful production TLS, Android runtime trust configuration,
real redirect/auth/cache behavior on all platforms, device radio/background lifecycle,
guest imports, signed network-grant activation or FieldLog network integration.

## Strict guest transport value codec

`GuestCapabilityTransportCodecV1` now implements the four methods declared by the
[frozen development transport contract](../contracts/guest-capability-transport-v1.json):
`decodeArguments(_:operation:)`, `encodeArguments(_:)`,
`decodeCompletion(_:expectedOperation:)` and `encodeCompletion(_:operation:)`.
`GuestCapabilityOperationV1` has exactly `httpRequest`, `storageGet`, `storagePut`
and `storageDelete` (tags1...4). Completion values are typed success, unchanged
capability failure, or the separate `rejected(.invalidArguments)` transport outcome.

The generator derives fixed metadata from the existing schema and approved mapping.
The codec reuses strict object preflight/type dispatch, validates directly constructed
DTOs during encoding, rejects wrong-operation results, normalizes new decode failures
to sanitized `CapabilityWireError` and retains the existing value
semantics: HTTP302 and `found=false` with nonempty canonical bytes are type-valid.
Native redirect/store policy is enforced separately. No identity/token appears in
these payloads; the bridge must validate its actual native `CapabilityCall` before
conversion and retain originating request ownership outside this value codec.

The separate public `guest-transport-probe` executes all90 original frozen fixtures
in debug and release. The [codec receipt](verification/guest-transport-codec/README.md)
also records direct-DTO/boundary/routing tests, first-generation native-hash coverage,
old Swift/Java codec regression, and iOS/Android/WASI compilation. The historical
contract/projection receipt remains unchanged. Schema/old envelope/model/adapter
bytes and semantic hashes remain frozen; this slice changes the generated native
implementation identity from `9e66695878568cbb0859d13cc6505ffd45b1471365af4d236fb9601efc0f6ed2`
to `9a89c437d78df58eb809765c945ba05239f491c85b4e72f1ffba22c640e7759e`.
This is an installed-code change requiring the correct new native fingerprint.

This codec does not register Wasm imports, supply a native bridge or Swift async
executor, enable capability activation, implement identity/release version changes,
or qualify OTA/device/FieldLog/store/GA behavior. Phones remain disconnected.
