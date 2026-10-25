# Isolated external worker HTTPS client candidate

The candidate implements the root-selected
[external worker contract](hosted-worker-transport-contract.md) in four new
modules. It remains under
`verification/hosted-worker-transport/candidate/lib/mixer_hosted/builds/` while
root finishes the parallel fleet-capacity source collection. No live hosted
source, shared collector, startup role, migration or dependency is changed.
Default dispatch remains unconfigured. This is a real TLS client to a separate
controller protocol, rather than an in-memory worker lifecycle substitute.

`WorkerWire` validates exact immutable Dispatch identity and encodes the complete
v1 envelope. It preserves signed-int64 values as decimal strings and SQL lease
microseconds, hashes fixed ordered immutable bytes and uses fresh random request
nonces. A lexical depth/token/string envelope precedes Jason allocation; decoded
duplicate or escaped-equivalent keys, unknown fields, wrong response echoes,
invalid result classes and incomplete artifact sets fail closed. The existing
operation-ID algorithm is unchanged. Shared synthetic Elixir/JavaScript vectors
cover Unicode, combining characters, printable escapes and int64 boundaries.

`WorkerConfig` validates a fixed HTTPS endpoint, pool/environment/controller
binding, explicit CA roots and a separate canonical 256-bit bearer token. It
disables by default and permits configured mode only for processors. Startup
revalidates a supplied config struct. Inspect and configuration errors omit the
token; no URL parameter, environment-to-module conversion or production fixture
selector is added. The ordinary RuntimeConfig/Application do not load it yet.

`WorkerHTTPAdapter` implements the unchanged three Dispatch callbacks.
`WorkerTransport` admits at most sixteen operations with no application wait
queue, one connection per operation and a five-second absolute deadline. It uses
the existing reviewed DNS and bounded TCP components, fixed selected IP/SNI,
verified CA/hostname, passive TLS 1.2/1.3 and HTTP/1.1. There is no redirect,
proxy, cookie, compression, retry or connection reuse path. A finite envelope
checks every incoming status/header byte before Mint. Request JSON is capped at
16 KiB; response JSON at 32 KiB; header/status bytes at 8 KiB; line at 2 KiB;
header count at 32; body receives at 4 KiB. Only one Content-Length-framed
response is supported.

The first actual TLS replay exposed a false-EOF bug: Mint closes its local socket
after a complete `Connection: close` response, so a subsequent SSL recv can report
local closure without proving peer closure. The retained
`verification/hosted-worker-transport/attempt-2.stdout` records false acceptances
of extra bytes and missing peer EOF. The corrected client withholds the final
approved body byte from Mint until genuine peer EOF, rejects any extra byte,
then feeds that byte and requires Mint done. It uses no private Mint state or
parser modifications. A single-byte body and segmented final byte exercise this
boundary directly. The absolute deadline includes EOF, decode and cleanup;
there are final monotonic checks before returning an observation.

Each flight independently monitors caller, role owner and role guard. Raw socket
registration precedes the SSL handshake; SSL process/socket registration precedes
credentials. Deadline or owner/caller loss kills only the owned worker, closes
owned handles and waits for raw-port/SSL-process/worker DOWN before normal slot
release. A separate role guard survives owner death and blocks replacement until
the old flights retire. Unexpected watchdog death quarantines admission instead
of inferring cleanup. There is no automatic restart or public quarantine-reset
API; whole execution-domain disposal is an operational requirement.

The source-bound receipt records isolated executable tests, real synthetic TLS
fixtures, cross-runtime hash vectors, production-mode compilation/export checks,
tool versions, exact source/BEAM inputs and cleanup. Initial failures remain in
the packet. Synthetic TLS private keys are confined to a temporary 0700 fixture
directory, which is deleted immediately after loading; executable assertions
verify removal. No MixerHosted authority/catalog module is loaded. Production
compilation excludes `start_fixture/3` and all test helper modules. This is an
isolated production-BEAM check, not a complete hosted release/package build.

This candidate has no configured real controller or provider. Controller ledger
persistence, immutable binding/fence/tombstone enforcement, source authorization,
authenticated supervisor results, artifact existence/provenance, Cloudflare
Linux and external Apple/macOS worker isolation remain required dependencies.
The client never fetches an opaque source reference or runs customer scripts.
It receives no OTA signing key and authorizes no tenant/release operation.

Protocol, mailbox-admission, process-heap and socket limits are not a hard total
memory/CPU/native-TLS guarantee. Production enablement requires separately
verified resource-domain limits, whole-domain death cleanup, crash/core-dump and
retention policy and all deployment-level sink controls. Library checks establish
no deliberate raw-result/token exposure in exercised sinks and redacted Inspect,
not absolute absence from VM/OS collectors or privileged process inspection.
Root integration and independent implementation review are pending. Full hosted
CI/release, operational/provider qualification, public authorization, signing,
native/dogfood and relevant GA gates remain open.
