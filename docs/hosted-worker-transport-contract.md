# External worker transport contract, version 1

Root selected the portable HTTPS authentication and first implementation boundary
on October 24, 2026. This packet specifies an actual outbound implementation of
the existing [Dispatch contract](hosted-build-coordinator.md), with no controller,
provider, tenant authority, release publication or fleet-isolation acceptance.
The production default remains unconfigured. Root must inspect this exact packet
before assigning production files. No frozen catalog/authority module was read,
loaded, imported or executed by its probes.

## Existing implementation and next ownership

`hosted/lib/mixer_hosted/builds/dispatch.ex:1` defines the three callbacks and
stable operation identity. `coordinator.ex:292` already monitors callback children,
kills them on timeout/parent death, and retains uncertain capacity. It does not
own sockets or prove all SSL processes die. `lifecycle.ex:63`, `:84`, `:98` and
`:426` define immutable inputs, exact WorkerRef and terminal result shapes.
`runtime_config.ex:15` supplies direct verified database TLS and separate API/
processor roles; it has no worker credentials or adapter configuration.

The pinned inventory is Mint 1.11.0, Jason 1.4.5, OTP 29.1.1/ERTS 17.1,
Elixir 1.20.4, Plug 1.20.3 and Bandit 1.13.1. `mix.exs:25` and `mix.lock` pin the
libraries; `THIRD_PARTY.yml:4` records Mint and `:256` records Jason. OTP SSL,
crypto/public_key and these dependencies are sufficient for the first client.
No HTTP-client, cryptography or controller dependency needs to be added.

`Identity.JWKSTransport`, `Identity.BoundedTCP`, `Identity.DNSResolver` and
`Identity.HTTPWireGuard` provide concrete passive TLS, pinned-address/SNI,
pre-parser byte checking, socket registration and deadline patterns. They are
identity-specific, with a 256 KiB body policy and JWKS media types; do not call
the JWKS fetcher with build data or silently change its accepted contract.
`Billing.WebhookTransport` is a separate inbound component. Its private Linux
resource harness lives in verification, rather than an installed worker role.
Neither component qualifies a new outbound worker transport's OS/native limits.
No worker controller, worker image, Wrangler configuration, Dockerfile or native
fleet provider implementation was found in the non-evidence product tree.

Bounded production ownership after root assignment:

| Owner | New files and responsibility |
| --- | --- |
| Wire/adapter lane | `hosted/lib/mixer_hosted/builds/worker_wire.ex`, `worker_http_adapter.ex`; exact codec, immutable binding, callback mapping; matching `hosted/test/mixer_hosted/builds/worker_*_test.exs` files |
| Outbound transport/config lane | `worker_transport.ex`, `worker_config.ex` in that same directory; finite pre-Mint envelope, socket/watchdog ownership, global admission, pure validated restart-scoped config; matching isolated tests |
| Root integration | RuntimeConfig/Application, existing collector and Dispatch installation; coordinate exact timeout agreement and dependency-purpose inventory |
| Later separate controller lane | Cloudflare Worker/DO ledger, Linux driver and external macOS supervisor, authenticated runner/result channel, durable launch/stop and isolation; select its files and tool dependencies before implementation |

Admission, migrations, coordinator/storage tests belong to another active lane.
This packet changes none of them. It adds no ordinary role or default adapter.

## Closed configuration

Implement `WorkerConfig.load!(env, role, roots)` as a pure constructor, without
environment-to-module/atom conversion or file/network access. Default
`MIXER_BUILD_WORKER_MODE=disabled` returns disabled and rejects stray
`MIXER_BUILD_WORKER_CONFIG` or `MIXER_BUILD_WORKER_TOKEN`. Configured mode is
processor-only and requires both values. Root owns startup integration later.

`MIXER_BUILD_WORKER_CONFIG` is at most 4,096 UTF-8 bytes and has exactly:
`version=1`, `endpoint`, `environment_id`, `pool_id`, `controller_id`, `platforms`,
`resolvers`. Endpoint has exactly `host`, `port=443`,
`path="/internal/mixer-build-worker/v1"`. Host is canonical lower-case DNS,
2–253 bytes, with at least two valid DNS labels; no URL, IP literal, userinfo,
query, fragment, trailing dot or encoded route. IDs are printable ASCII
1–128 bytes. Platforms are a unique nonempty subset of `ios`, `android`.
Resolvers are 1–3 unique canonical global-unicast IPv4/IPv6 literals, port 53.
Roots are an explicit nonempty bounded list of valid DER CA certificates from
trusted bootstrap, never HTTP or a root path in the config JSON. Cap roots at
256 certificates/1 MiB total and each DER at 64 KiB before certificate parsing.

The token is exactly 43 base64url characters without padding, canonically
encoding 32 random bytes. It is supplied separately by trusted secret injection.
It is never deliberately emitted as a URL parameter, source field, command-line
argument, log, error, telemetry value or inspection output. Config structs must
implement redacted Inspect; errors contain only closed reason atoms. Pure BEAM
code cannot establish absence from an OS core or erl_crash.dump. Production
enablement separately requires enforced launcher crash/core-dump and retention
policy plus hard-resource isolation; library tests cannot pass that gate. Tests use distinct
synthetic credentials. No production setting exposes fixture IP, port, CA,
clock, raw HTTP injection, transport module or arbitrary callback selection.
Constructor-supplied synthetic roots can test TLS without weakening validation.

The selected finite development profile is: 16 simultaneous socket owners,
zero queued calls, 5,000 ms total transport lifetime, 6,000 ms coordinator
callback timeout, 30,000 ms coordinator lease TTL and 1,000 ms polling. Constants
are not caller-selected. Root must validate their agreement before installing
the adapter. Resource exhaustion rejects before DNS/socket creation.

## HTTPS and authentication

The adapter POSTs exactly one command to the fixed endpoint. Use HTTPS only,
TLS 1.2/1.3, certificate-chain and hostname verification, fixed SNI/Host and
ALPN HTTP/1.1. Resolve once through bounded configured DNS, reject non-global
answers, connect to the selected IP, and verify the actual peer matches it.
No environment proxy, redirect, cookie, automatic retry, connection pool,
compression, HTTP/2, upgrade or alternate destination is supported in v1.

Headers are exactly Host, Content-Type `application/json`, Accept
`application/json`, Accept-Encoding `identity`, Connection `close`,
Content-Length and Authorization `Bearer <token>`; the client may supply the
Host/length through Mint's documented generation rather than duplicate them.
The controller maps the credential to the configured environment/controller/
pool/platform set before accepting work. These machine permissions grant no
tenant membership, source access, release eligibility or signing authority.
Never forward the pool token into the build sandbox.

Server identity and response authenticity come from the same verified TLS
connection. Each response echoes a fresh nonce and the complete request binding;
do not invent a detached signature scheme. Standard network authentication is
separate from OTA signing: no OTA/release private signing key enters this client,
controller or untrusted worker. A separately authorized signing stage remains
required. For bearer-secret protection, see [RFC 6750 section 5](https://www.rfc-editor.org/rfc/rfc6750#section-5).
Cloudflare Access service tokens may add ingress protection, but do not replace
the controller's pool authorization. [Access service authentication](https://developers.cloudflare.com/cloudflare-one/access-controls/service-credentials/service-tokens/)
supports machine credentials; [Workers mTLS](https://developers.cloudflare.com/workers/runtime-apis/bindings/mtls/)
is an outbound binding and documents a restriction for Cloudflare-proxied
destinations. Direct-origin mTLS requires a separate qualified profile.

## Exact wire shapes and immutable bytes

Every object rejects unknown, missing, duplicate and escaped-equivalent member
names at every depth. Decode with string keys and copy strings; never create
atoms from input. Reject invalid UTF-8, floats, exponent integers, signed/leading
zero decimal strings and out-of-range values. Before Jason decodes, a bounded
JSON lexical envelope rejects nesting over 8, over 512 tokens or a string token
over 8,192 raw bytes. After decoding, enforce the tighter field bounds below.
Map enum strings only through explicit clauses. Do not hydrate arbitrary structs.

Request has exactly:

```text
version: 1
environment_id, pool_id, controller_id: configured IDs
request_id: 32 lower-case hex characters from 16 fresh cryptographic random bytes
command: "query" | "ensure_started" | "stop"
operation_id: 64 lower-case hex SHA-256, unchanged Dispatch identity
immutable_sha256: 64 lower-case hex SHA-256 defined below
ref: {organization_id, project_id, application_id, build_id, platform, attempt, fence}
spec: {organization_id, project_id, application_id, build_id, platform,
       source: {kind, sha256, reference}, toolchain_lock_sha256, build_definition_sha256}
deadline_ms: decimal string
guard: {record_id, revision, owner_id, epoch, expires_at_us}
```

Ref/spec scope must agree exactly; `record_id` is canonical lower-case UUID.
Lifecycle identifier bounds remain 128 printable UTF-8 bytes and source reference
1,024 bytes, source kind is `revision`/`upload`, platform is `ios`/`android`,
hashes are lower-case hex64 and attempt is JSON integer 1–5. Owner ID uses the
existing printable UTF-8 128-byte bound. All other integer fields, including
revision, fence, epoch, deadlines, expiries and artifact sizes, are canonical
decimal **strings**, parsed into arbitrary-precision integers before comparing.
Maximum is `9223372036854775807`; revision is 0–32, fence/epoch are positive,
deadline/expiry are positive. Preserve SQL DateTime microseconds exactly in
`expires_at_us`; never truncate to milliseconds. Do not call `Number()` on these
fields in a TypeScript controller.

`immutable_sha256` hashes UTF-8 JSON emitted by Jason, without whitespace, for
this fixed-order array, using the already validated string values:

```text
["mixer-worker-binding-v1", operation_id, guard.record_id,
 [ref.organization_id, ref.project_id, ref.application_id, ref.build_id,
  ref.platform, ref.attempt, ref.fence],
 [spec.organization_id, spec.project_id, spec.application_id, spec.build_id,
  spec.platform, spec.source.kind, spec.source.sha256, spec.source.reference,
  spec.toolchain_lock_sha256, spec.build_definition_sha256], deadline_ms]
```

Thus fence/deadline are strings in this new digest. The existing operation ID
algorithm remains unchanged: its fence is a JSON integer. A TypeScript controller
that recomputes that old ID must serialize the validated decimal digits as an
integer token, rather than round through a JS number. Shared cross-runtime byte
vectors are required before a controller is accepted, including Unicode,
printable control/escape boundaries and int64 values.

An HTTP 200 response has exactly these closed keys: `version environment_id pool_id controller_id
request_id command operation_id immutable_sha256 ref guard observation`.
Every echoed value must match this request exactly, including owner and expiry.
Observation has exactly one of these shapes:

```text
{status: "absent"}
{status: "running"}
{status: "stopped", diagnostic_sha256: hex64}
{status: "completed", result: {outcome: "succeeded", artifacts: [seven artifact objects]}}
{status: "completed", result: {outcome: "failed", class, code, diagnostic_sha256: hex64}}
{status: "error", code: "stale" | "unavailable" | "uncertain"}
```

Artifact objects have exactly `kind sha256 size_bytes`; require exactly the seven
existing Lifecycle kinds once each, and identical sizes for equal hashes.
Failure class/code pairs must match Lifecycle's finite allowlist exactly.
Convert validated artifacts into ArtifactRef structs and the result's existing
finite atom enums only after the complete response validates. Absence/running
never free capacity. A validated error maps only to its Dispatch error atom.
All non-200, malformed, wrong-binding, timeout, parent loss and transport failures
map conservatively to `:uncertain` (pre-dispatch disabled/capacity rejection may
return `:unavailable`); no response becomes a terminal observation by inference.

## Bounds before parsing and cleanup

The outbound encoded JSON is at most 16,384 bytes before connecting; total
request header bytes are at most 8,192. The new transport's finite HTTP envelope
runs **before every Mint stream call**, rather than inspecting already allocated
Mint events. It accepts a single HTTP/1.1 200 response with exact Content-Length
1–32,768, one Content-Type `application/json`, and no Transfer-Encoding,
Content-Encoding except identity, Trailer, upgrade, informational response,
folded header, control character, duplicate case-insensitive header or extra
message. Cap status/header line at 2,048 bytes, all status+header bytes at 8,192,
and fields at 32. Content-Length is canonical decimal, not a list or repetition.
Connection-close framing and chunked responses are unsupported in this controlled
v1 protocol; the controller must emit Content-Length.

Read status/headers one byte at a time with a bounded accumulator, and body in
at most 4,096-byte chunks capped by remaining declared bytes. Feed only approved
bytes to Mint, require its done event and envelope completion to agree, then
require peer closure under the same absolute deadline. Read at most one further
byte; any extra byte, socket error or missing EOF before that deadline rejects
the entire response. Only clean peer closure permits JSON decoding and returning
an observation. The controlled server must actually close after its one response;
the Connection header alone is not evidence of closure. Close the entire client
connection on rejection. No parser-body concatenation over 32,768 bytes, decode
before completion, unbounded mailbox, or drain-to-reuse path is permitted.
Mint's `max_header_list_size=8192` is supplemental, not the first allocation
boundary. Use passive SSL, raw socket/SSL-driver buffers of 16,384, bounded TCP
activation, `max_handshake_size=65536`, send timeouts with close, and one absolute
monotonic deadline spanning admission, DNS, TCP, TLS, send, read and decode.
The 5,000 ms deadline never resets on progress or per phase.

Register the raw socket with an independent watchdog **before** SSL handshake;
register SSL connection processes and the SSL socket before sending credentials.
The watchdog monitors original caller, transport owner and bounded role owner.
Caller death, timeout, capacity-owner death, malformed input or registration
failure revokes the permit and closes only owned sockets/connections; ensure no
blocked TLS/receiver child survives. Retain a capacity permit until termination
and cleanup are observed. Close the per-request connection on every outcome.
Use bounded safe diagnostics; no raw response, request, token, exception,
stacktrace, socket term or config may deliberately enter a library-controlled
sink. Absolute secret absence from process memory, VM/OS crash collectors and
deployment-level sinks requires separate operational enforcement and review.

These are executable protocol, process and socket limits. They do not establish
a total memory/CPU/native TLS ceiling. A later enabled deployment needs a separate
resource-controlled transport execution domain, with enforced memory/task/FD/
output limits and parent-death whole-domain disposal, independently verified on
its actual Linux target. BEAM `max_heap_size`, sampled RSS, buffer options and a
post-parser byte count are not substitutes. The existing verification-only
Stripe cgroup launcher is a reference pattern, not a reusable accepted production
launcher or worker qualification. Keep hard-resource and deployed TLS gates
explicitly pending when accepting the first client library slice.

## Controller and provider obligations before real enablement

The separately deployed controller must authenticate the request, validate
binding, acquire its durable operation lock, sample time after the lock and
compare `{epoch, revision}` lexicographically before recording any effect.
Same epoch requires the same owner; equal pairs may renew expiry forward only
for that owner. An older pair cannot query/ensure/stop or change a watermark.
An expired request cannot act; measured clock uncertainty must be bounded and
applied conservatively, with rechecks before effect acceptance. A wall-clock
claim or comparison to a stale pre-lock timestamp is insufficient.

Persist original record/ref/spec/deadline, immutable digest, high-water pair,
owner/expiry, desired state, stable provider execution identity, effect intent
and terminal evidence. Query of an absent execution may still persist binding/
high-water; absent is never proof that an earlier accepted start cannot arrive.
Commit desired stop/tombstone before contacting a provider, including when no
worker exists. Never expire/delete/reopen terminal identity: retain at least
operation+binding digest+terminal tombstone forever. No TTL or transparent
namespace reset is permitted. Restore/deploy reconciliation must not roll back
fences, erase tombstones or create a second dispatcher.

Controller ledger writes and external launch are not one transaction. Persist
launch intent first, use one stable provider resource identity, keep boot inert,
and grant a one-shot immutable job claim outside customer scripts. On timeout,
query that identity; never blindly create a replacement or rerun scripts because
an API returned absent. A newer stop invalidates pending start claims; already
running work must be stopped and reconciled. Persist a terminal stop immediately
as desired state, but return `stopped` only when all owned work and descendants
are definitively gone and delayed accepted launch requests cannot resurrect it.
Provider stop acknowledgment/SIGTERM alone is not terminal proof.

Cloudflare's [direct Durable Object Container API](https://developers.cloudflare.com/containers/api/)
can connect a stable DO identity to Linux compute; it does not prove one-shot
job execution or hostile-code isolation. Put binding/fences/tombstones and
effect intents in durable transactional storage, never ephemeral container disk.
[DO SQLite storage](https://developers.cloudflare.com/durable-objects/api/sqlite-storage-api/)
supplies transactional storage; separate its network effects from transactions.
[Container lifecycle](https://developers.cloudflare.com/containers/concepts/architecture/)
requires readiness and termination observation; ordinary disk is disposable.
Use GA service scheduling and pinned images per product-plan 13.4. Android build
code runs only in a separate qualified Linux job sandbox; otherwise use the
explicit external Linux exception. macOS workers remain on licensed Apple hosts
outside Cloudflare; a separate trusted supervisor controls ephemeral macOS jobs
and reports through authenticated pool/operation-scoped runner credentials.

The controller holds provisioner credentials; trusted runner supervisors have
only operation-scoped source/artifact grants and result credentials unavailable
to build scripts. `source.reference` is opaque data, never an authorized fetch
URL. Separately resolve authorized immutable source, toolchain and build
definition objects; verify checksums before execution. Bounded logs/private R2
uploads use scoped grants; result acceptance authenticates supervisor identity,
exact operation/binding/attempt, one-time claim and artifact hashes/sizes against
immutable objects. An authenticated hash declaration alone proves neither object
existence nor build success, provenance, app identity or release eligibility.
Build workers and the controller never receive OTA signing keys.

## Verification and current limits

The packet's `run.py` runs only two dependency/interoperability probes and seals
the read source/tool/command outputs. The Elixir probe loads only pinned Jason,
Mint and HPAX dependency BEAMs, proves duplicate-member preservation and exact
int64 decoding, performs a real bounded plaintext loopback Mint POST/read/close,
and reports zero loaded MixerHosted modules. The Node probe demonstrates JS
number precision loss and exact decimal-string/BigInt handling. This is API
evidence, not a prototype controller, worker authentication or HTTPS receipt.

Implementation must add exact-codec/adversarial tests and actual synthetic TLS
wire tests for authentication header handling, hostname/CA rejection, peer
pinning, all pre-Mint boundaries, long header/body fragments, DNS/TLS stalls,
timeout and parent death at every stage, admission exhaustion, failure cleanup,
secret sink/Inspect checks and production fixture-export exclusion. Independent
review must replay the source-bound negative controls before root integration.
No physical/native tests, cloud deploy, source publication, provider calls,
credentials changes or hosted application startup occur in this packet. Hard
Linux resource ceilings, controller persistence/failover, provider execution,
hostile-code isolation, Neon/R2/Cloudflare operational qualification, public
authorization, signing and all relevant GA gates remain pending.
