# Hosted key owner implementation

Status: **implemented component, awaiting independent root source/evidence review**.
The [receipt](../verification/hosted-key-owner-implementation/receipt.json) freezes
commands, source hashes, platform scope and limitations. Application startup is
not wired to this component; the existing HTTP API still exposes health only.
No provider, authenticated route, membership policy, database authority,
publication, dogfood release or GA acceptance is supplied.

## Explicit configuration and verification

`KeyOwnerSupervisor.start_link/1` accepts a complete reviewed manifest, generation,
one explicit adapter binding, nonempty deployment CA roots and trusted recursive
resolvers. It starts the worker supervisor before the owner. Module loading does
not fetch keys, discover an issuer or read mutable application-environment trust.
At most eight enabled/disabled profiles are installed. The exact pure profile
contains no URL/cache fields; the outer entry binds its reviewed HTTPS host,
port443 and exact path. Unsupported production ports reject in this first slice.
Manifest installation validates the entire candidate and expected generation.
Issuer/client/class are immutable; versioned changes/re-enable cannot reuse a
retired version. Emergency disable can keep the version. Bounded30-second
remove/re-add tombstones preserve attempt cooldown; live profiles plus tombstones
are at most16. A separate lifetime history retains at most16 distinct IDs and
last validated entries/retired state, with no keys or snapshots. Immutable
identity and highest version remain enforced after cooldown expiry. Removed IDs
and disabled-to-enabled bindings require a strictly higher version. A seventeenth
ever-seen ID rejects rather than evicting history; the whole candidate updates
history/manifest/tombstones atomically. Clock faults and reaping preserve history.
This stricter configuration-churn availability limit is the [root supplement](../verification/hosted-key-owner-root-review/profile-history-selection.json).
Unshared configured strings in16 maximal records total at most81872 bytes, plus
bounded map/scalar overhead; the receipt separately measures serialized example
metadata. This history is process-local. Durable provisioning/DB enforcement
across owner/component restarts remains pending and is not proved by this cache.
Unrelated configuration never partially publishes.

All six accepted pure verifier modules and their tests remain unchanged.
`ConfiguredVerifier.authenticate/2` implements the frozen behavior using the
explicit owner binding. Its private-use `authenticate(owner, profile_id, token,
now)` entry selects only an already installed binding; it cannot supply network
configuration, roots or a snapshot. A token never selects a profile or URL.

Admission reserves one of16 per-profile and128 total ETS slots before sending
an owner message. A reservation includes its caller, unique nonce and monotonic
admission sample. The owner monitors admitted callers and reaps abandoned
pre-mailbox reservations. `checkout(owner, permit, now)` obtains current trust or
joins one required flight; JOSE verification runs in that admitted caller.
`finish(owner, lease)` then serializes the enabled profile/version/snapshot/epoch
and freshness fence. One retry can use current trust; a second race fails
unavailable. A retired lease cannot return an identity after disable or key
removal. The public result remains only verified identity, unauthenticated or
identity unavailable.

The owner retains at most eight snapshots, four transport/validation flights and
128 FIFO negative entries per profile. Fresh unknown keys deny immediately and
may start one eligible background refresh; known-key signature failures never
fetch. Attempt admission, including failures, starts a non-extending30-second
cooldown. Hits do not renew negative expiry or FIFO order. Successful replacement
atomically clears old negatives and removes omitted keys. Invalid candidates do
not partially publish or change old deadlines. There is no stale fallback.

HTTP freshness uses Date/Age and valid max-age or Expires, with any shorter
s-maxage/Expires limit, paired clocks, response delay, conservative whole-second
floor and the300-second ceiling. Validation/publication consumes the original
monotonic expiry. Both exclusive wall and monotonic freshness bounds must hold.
Clock reversal/discontinuity retires trust and in-flight epochs. A clock fault
never changes the reviewed manifest generation, so an expected-generation
emergency disable can still commit.

## Transport and resource ownership

Production uses the pinned Mint1.11.0 HTTP/1 parser and OTP TLS. The explicit
resolver applies A/AAAA queries under the same two-second deadline, bounds CNAME
hops/answers and rejects unsafe/mixed addresses before HTTP. One deterministic
accepted tuple is connected without a second lookup; actual peer, CA chain,
certificate time, hostname and SNI remain mandatory. Only the reviewed GET path
and fixed Accept/identity/close headers are sent. No redirect, retry, alternate
address/family, proxy, authorization, cookie, HTTP/2 or pooled connection exists.

The independent bounded wire guard only rejects; Mint must also complete the
same framing. The guard rejects every nonempty trailer, including metadata Mint
normally strips. Informational sections are at most four; aggregate headers are
at most10KiB/64 fields. Status200, supported media type, identity encoding and
unambiguous framing are mandatory. No event crossing262144 actual body bytes is
appended. The unchanged snapshot constructor validates all1-16 public RSA keys.

Retained failures establish why the receive strategy changed: passive recv0 and
TLS active-once both batched beyond16KiB. Exact positive reads now request one
byte for bounded metadata, at most4096 remaining declared/chunk payload bytes,
and two bytes for chunk terminators, then feed passive Mint. This bounds each
input delivered to the guard/parser without assuming a TLS-record-sized batch.
Large close-delimited bodies use one-byte reads and can exhaust the fixed
deadline; that availability/compatibility limit is explicit. No deadline is
extended for them.

OTP's documented `cb_info` seam uses Mixer `BoundedTCP` to cap positive internal
TCP activation counts to1. Non-activation options are applied with reads paused,
then driver buffer16384 is set and verified, then bounded activation is restored.
A buffer-only update preserves prior activation: an earlier failed integration
showed that silently dropping it stalls Mint responses. Driver buffer is distinct
from OS recbuf; the latter was observed to grow above500KiB. No global SSL or
other application's options are changed.

The callback synchronously registers the newly created raw TCP port before TLS
handshake, verifies ownership, and records its controller through the supported
`controlling_process/2` callback. Each flight watchdog force-closes raw and
completed TLS sockets on timeout/cancellation and waits for raw-port DOWN,
controller DOWN and worker DOWN before retiring the flight. The two-second
absolute deadline includes admission/queue, DNS, connect/TLS, response,
validation and publication. A late candidate cannot install.

Graceful owner/supervisor shutdown and restart remain pending while an owned
monitored TLS controller is deliberately held. Infinite child shutdown waits
preserve fail-closed accounting instead of a default5-second force-kill releasing
old capacity. Tests deliberately hold four real controllers, close their ports,
kill their workers, deny a fifth flight, and show restart only after the old
controllers and workers are down. Container/SIGKILL termination is outside that
graceful process-cleanup guarantee; no hard real-time scheduler guarantee is
claimed.

## Evidence and qualification boundary

The final host run executes45 tests (29 owner/transport plus16 unchanged pure
verifier tests). The disposable Linux collector additionally executes the actual
production DNS/rebinding fixture. Its network-none namespace assigns8.8.8.8 to
its own lo:1 and listens on443; the DNS stub switches subsequent answers to
loopback before connection. Production resolution/classification and TLS fetch
succeed with the pinned public peer after exactly A/AAAA queries; the separate
127.0.0.1:443 sink receives zero connections. A subsequent private answer rejects
before TCP. This uses no product resolver or loopback bypass. NET_ADMIN is scoped
to that disposable container; no host or other container route is changed.

The matrix exercises whole-manifest/key limits and atomic replacement; real CA,
hostname, expired/future/bad-signature certificate, plaintext/downgrade and IPv6
checks; actual DNS unsafe/mixed/CNAME/overflow/truncation/delay/rebinding; redirect
sink and error statuses; exact full256KiB Content-Length and chunked documents
with four workers; oversize/framing/header/trailer/compression/informational
rejection; freshness arithmetic; real status/header/body/drip/handshake deadlines;
caller death and delayed cleanup;100-request single-flight admission; eight-profile
four-flight limits; bounded FIFO negatives and cooldown across remove/re-add;
real signed-token overlapping rotation/removal/invalid replacement; lease,
disable, removal, clock, shutdown and restart fences.

Resource receipts separately sample worker/parser/mailbox and exact client-side
OTP29 TLS handler/sender processes under fast8MiB500 bodies, slow/partial input
and four suspended consumers. Assertions use a4MiB referenced-binary/8MiB heap
measurement budget per sampled TLS process. These are observed samples, not a
universal RSS, kernel-buffer or hard process-memory maximum. The hard application
bounds are payload/parser/metadata/admission/flight limits and owned socket
lifecycle. Test-only opaque-socket instrumentation is pinned to OTP29; product
code uses public port ownership and callbacks.

The Linux collector pins the official Hexpm image digest, records OTP29.1.1,
ssl11.7.7, Elixir1.20.4 and OS details, builds a production release without
starting it, and verifies fixture constructors are absent from packaged BEAM
exports. Production constructors reject fixture options. Test exceptions only
select fixture IP/port; CA/hostname verification remains enabled. Ephemeral
CA/leaf keys are removed before listening; listeners/processes, temporary builds
and the disposable container are cleaned on success/failure.

All receipts are component evidence. Selected-provider issuance/rotation/cache
semantics, deployment egress/fleet quotas/clock behavior, root application wiring,
HTTP request admission, membership/DB authorization, Cloudflare/Neon operation,
external FieldLog packages, independent security acceptance and GA remain open.
Physical phones stay disconnected/deferred; this lane uses no native simulator,
emulator, screen capture or physical-device run.
