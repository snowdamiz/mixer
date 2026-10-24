# Proposed private Stripe resource and ingress contract

Status: **root selection pending; contract checks only; no resource, TLS, deployed
ingress, trailer-policy, provider or GA acceptance**. This is the next bounded
P11/P12/P14 development proposal under product-plan 13.2–13.5, 17 and 18. It does
not retry the rejected catalog-inspector or authority-driver review lanes.
The ordinary hosted application remains inactive for this transport. Root must
select this contract before dependent implementation.

The baseline is the accepted [transport regression receipt](../verification/stripe-webhook-transport-regressions/acceptance.json):
73 source inputs, digest `1b2f03d474f825a6265e0a10f9baf2adda62dffe6c747542207f32753b4df997`,
149 passing host tests and two skipped namespace fixtures. Those counts are
historical accepted evidence, not tests rerun by this packet. The current module
hash is `56a26cf3a56f3e5a5b2d8f5104fc7c3371b0e44918b007197be5871cf94ef1a5`.
Revision `bbed074d` is caller-supplied context only; the packet uses content
bindings and performs no Git operation.

## Narrow next slice

Implement a **private Linux cgroup-v2 harness and isolated role launcher**, then
obtain a fresh independent implementation replay before root integration. Add no
ordinary application role, public route, customer response, provider connection,
database admission, Oban job, secret owner or deployment. A private successful
capture still returns only the existing synthetic non-2xx 418 marker. The
launcher invokes the unchanged `WebhookTransport.start_link(private_plug)` and
`capture/1`/`dispose/0` interfaces in its own BEAM. Every HTTP read stays in its
original request owner. No parser fork or private adapter manipulation is allowed.

Proposed owned implementation files are a new isolated verification packet
(`run.py`, `role.exs`, `fault_helper.c`, tests and evidence); production changes
are unnecessary for the first resource replay. A later production envelope
module, Linux OCI recipe or Worker candidate requires root contract/ownership
selection. No dependency is added by this packet. Use Python standard library,
the already installed C compiler, pinned hosted BEAM/dependencies and Linux
platform interfaces. Do not install software, start a Docker daemon, pull an
image, start native simulators, or contact providers to satisfy a missing local
capability. A missing delegated Linux environment is explicit unavailable evidence.

## Findings that constrain implementation

The [source map](../verification/stripe-webhook-resource-ingress-contract/source-map.json)
binds actual installed Plug 1.20.3, Bandit 1.13.1, Thousand Island 1.6.0, HPAX 1.1.0
and telemetry 1.4.2 sources, with Elixir 1.20.4 / OTP 29.1.1 pins. Plug documents
body lengths as approximate. Bandit decodes HPACK before checking decoded list
size, sends DATA to stream mailboxes and replenishes receive windows toward
`2^31-1`. H1 parses/discards trailing headers using a fresh default header-options
map; H2 logs inspected trailers before discarding them. Original body/signature
values remain the authenticated inputs. Logger/sink protection remains mandatory.

The selected sixteen connection entries, single stream/request, body cap and
1s/5s/7s deadlines are logical limits. They do not cap native allocations, TLS,
allocator overhead, kernel socket buffers, VM-wide memory or pre-Plug parsing.
`max_heap_size`, BEAM process/port tables and sampled RSS are also different
boundaries. The new harness must retain the selected capture and cancellation
matrix rather than replace it with configuration inspection.

The hosted project requires exactly Elixir 1.20.4, compiles tests with
`--warnings-as-errors`, and builds a production Mix release without test/support
paths. Existing release checks prove the private role stays absent and test
clock/adapter/helpers stay out. A macOS BEAM/ERTS/native dependency is not a Linux
release: rebuild from the same source/lock closure for the actual Linux target,
record architecture, libc, OpenSSL/ERTS dynamic libraries, compiler and image
digest, inspect package exports, and run it there. No base-image digest or Linux
artifact is selected or built here. The future Linux image must be digest pinned,
contain the matching ERTS and runtime libraries, exclude source/build credentials
and test helpers, and keep dependency/license inventory current in THIRD_PARTY.yml.

## Proposed finite development profile

The exact closed object is [profile.json](../verification/stripe-webhook-resource-ingress-contract/profile.json).
All values below are **proposals for synthetic development tests**, not capacity,
latency or production sizing commitments. Root selection does not pass P11.

| Boundary | Proposed value, enforcement and reason |
| --- | --- |
| Memory | Own cgroup: `memory.max=1073741824` (1 GiB), `memory.high=805306368` (768 MiB), `memory.swap.max=0`, `memory.oom.group=1`. Prior 151280 KiB sampled RSS leaves investigation headroom; that sample is not a peak. Read back effective files and ancestors before launch; lower ancestor limits fail this exact-profile run. |
| CPU | Own cgroup: `cpu.max="25000 100000"` (0.25 CPU quota), `cpu.weight=100`. This deliberately tests a small fixed quota; inspect `cpu.stat` throttling. Quota is an aggregate scheduler budget, not a per-request deadline or a real-time guarantee. |
| OS tasks | `pids.max=128`, counting Linux tasks/threads, not Erlang processes. Record initial task count and `pids.events`. An inherited task limit must not silently replace this profile. |
| Descriptors / sockets | Inherited hard and soft `RLIMIT_NOFILE=256`; close inherited descriptors except stdin/stdout/stderr. This is a per-process open-descriptor limit, including socket descriptors, **not a sixteen-kernel-socket or container-wide socket-count guarantee**. BEAM `+Q 1024` is a separate port-table guard. Record every owned process's limits and aggregate socket-inode/FD inventory. |
| VM tables / threads | `+S 2:2 +SDcpu 1 +SDio 1 +A 2 +P 32768 +Q 1024`; no distributed node/name or epmd startup. These are supplemental guards; native threads count against `pids.max`. |
| Network | Dedicated network namespace, loopback only, no veth/default route/DNS, no host networking or inherited sockets; clients enter only that owned namespace. Deny new external egress and verify IPv4/IPv6 attempts. Drop capabilities before executing BEAM; no container-management socket or cgroup write mount inside the role. |
| Dumps / files | Hard/soft `RLIMIT_CORE=0`, `RLIMIT_FSIZE=0`; `ERL_CRASH_DUMP=/dev/null`, `ERL_CRASH_DUMP_SECONDS=0`. Read-only role filesystem, bounded 8 MiB private tmpfs, no writable host/secret mount. Inspect dumpability and host core collector configuration; refuse a no-dump qualification when collection/retention is unknown. |
| Controller | Outside the role cgroup; 120s wall limit per case, 900s suite, one role at a time. At stop: close the private admission gate, SIGTERM, allow 2000ms, then cgroup-wide kill; require zero tasks and closed sockets by 2500ms from stop, record actual overshoot. Client/reader, injector and BEAM share the owned kill domain; evidence controller does not. |
| Output | Separate bounded stdout/stderr pipes, 1 MiB each. Collector records only a fixed safe schema; unknown output/overflow is a failed case and triggers whole-cgroup termination. No raw event, exception, stack, request or dump is forwarded into retained evidence. |

Neither `RLIMIT_AS` nor `RLIMIT_NPROC` is used as a substitute for cgroup memory
or task control. Descriptor exhaustion and namespace isolation provide enforceable
socket-related bounds; a universal kernel socket-count cap is not claimed. If
public acceptance requires such a cap, root must select a supported additional
mechanism and review it. Do not invent a cgroup socket-count setting.

The controller must create only its identity-marked child beneath an explicitly
delegated cgroup path, configure/read back limits **before** moving any role task,
and prevent the child from altering/migrating those limits. Refuse launch for
missing controllers, delegation, readback, wrong ownership, ancestor ambiguity,
unknown core collector, insufficient clean namespace/descriptor isolation or
source mismatch. No fallback to a host process or relaxed limit. Tests may report
`unavailable` with exit 78; that is not a runtime pass.

Filesystem setup uses an owned mount namespace with private propagation and a
read-only sealed release/root, not a remount of the host filesystem. PID namespace
and reaper ownership must be recorded; every descendant stays in the owned cgroup.
If namespace/mount privileges are unavailable, refuse the isolation run. Construct
a minimal fixed environment for the role (release PATH, locale and the two dump
settings); do not inherit provider/cloud/database variables, HOME/cookies, tool
credentials or controller environment. Record variable names and fixed nonsensitive
policy values only. Configuration paths and cgroup setup are controller owned.

## Exact harness interfaces and receipts

Proposed command, after root selection:

```text
python3 -B verification/<selected-resource-candidate>/run.py --profile <sealed-profile.json> --delegated-cgroup <owned-parent> --release <sealed-linux-release> --output <new-owned-directory>
```

No request, HTTP header or request-private value can select policy, path, PID,
limit, sink, destination or fault. The controller validates a schema-1 closed
profile against selected constants before subprocess creation. `role.exs` gets
only fixed synthetic mode, an inherited private control pipe and the already
verified release path. Control messages are closed tuples:
`ready(generation, port)`, `stop(generation)`, `stopped(generation, reason)`;
generation is controller minted, matched exactly and never an HTTP capability.
Unknown/replayed/wrong-generation messages fail closed. The stop handler first
closes a private admission gate and kills owned existing connections; graceful
SIGTERM is only a request until termination is observed. The external controller
enforces final cgroup disposal even if the VM is frozen or dead.

Each case emits schema-1 data with exactly: `caseId`, `status` (`passed`, `failed`,
`unavailable`), `reason` (closed enum), `profileDigest`, `sourceDigest`,
`releaseDigest`, `environmentDigest`, `startedMonotonicNs`, `elapsedNs`,
`cgroupBefore`, `cgroupAfter`, `samples`, `termination`, `outputAudit`, `cleanup`.
Samples contain integers/counters only (20ms target period, actual sample times):
memory.current/peak/events, CPU usage/throttle, OS task/current/peak/events,
process RSS, BEAM total memory, heap words, referenced binary bytes, mailbox
length, FD/socket counts. RSS and BEAM sampling remain sampled observations;
retain cgroup memory.peak where available and distinguish kernel accounting from
RSS. Never fetch `messages`, process dictionaries, stack traces, packet captures,
`conn`, body, signature, header/trailer values or core contents. Referenced binary
bytes may double count shared allocations. Missing peak support is reported.

Reasons are the fixed enum in profile.json. `outputAudit` contains allowed-schema
counts, rejected-output count and sentinel-match booleans, never rejected bytes.
Synthetic sentinels test the allowlist; searching sentinels alone does not prove
redaction or make an arbitrary report safe. Record exit/signal and
`memory.events:oom_kill` delta together: exit 137 alone is not OOM attribution.
OOM injection uses a privately compiled, bounded helper in the same cgroup with
at most 1280 MiB touched, no other fork/allocation loop and a 30s injector bound.
CPU, task and descriptor helpers have finite attempt counts in profile.json.
Do not run OOM/resource stress on the host or place the evidence controller in
the stressed cgroup. Any counter/readback/output failure makes the case failed.

The [matrix](../verification/stripe-webhook-resource-ingress-contract/matrix.json)
specifies required private Linux, local synthetic TLS and separately staged cases.
Keep failures and cleanup receipts. Local unavailable cases do not block authoring
or independent source review, but they remain pending runtime qualification.

## Ingress and public trailer decision remain separate

Current official [Cloudflare instance documentation](https://developers.cloudflare.com/containers/platform/limits/)
lists `basic` as 1 GiB/0.25 vCPU. This motivates a comparison profile; it does not
prove equivalent enforcement. The [direct Container API](https://developers.cloudflare.com/containers/api/durable-object-container/)
distinguishes start, readiness, monitoring and stop. Its documented controls do
not establish delegated cgroup, task, descriptor, core-dump or output-retention
controls. Do not promote local Linux controls to Cloudflare guarantees.

[Worker Request documentation](https://developers.cloudflare.com/workers/runtime-apis/request/)
describes a body stream and runtime-selected Content-Length/framing. Therefore
proxying a Fetch Request is not proof of original wire framing/header occurrences.
The inspected Request interface does not document a trailer-observation API;
that is absence of a documented guarantee, not proof that a deployed edge rejects
or discards all trailers. P12 stays **unselected**. Root may later choose either
explicit discard with exact body/original signature authentication and all-path
privacy, or reject via a separately proven ingress capability. Do not implement
an unobservable trailer rejection or silently narrow supported H1 chunked/H2
framing to make it pass.

P14 staging must pin Worker source/build, Wrangler/type versions, compatibility
date/flags, image digest, routing/DO policy, instance type, TLS/WAF/cache/body/log
configuration and region. Test real external TLS 1.2/1.3 and ALPN H1/H2 separately
from the Worker→DO→container protocol. Compare client→Worker and container capture
outcomes for exact body bytes, duplicate/case/whitespace-sensitive signature
occurrences, CL/TE normalization, declared/undeclared trailers, compressed bodies,
slow streaming, backpressure, disconnect, timeout, cancellation and large chunks.
Record which ambiguity is rejected at which hop; accepted duplicates must not
become a merged signature accepted by accident. No cache, request-body log,
console/error/tail export or automatic retry/redirect may expose/replay a body.
An edge cancellation is not proof of backend disposal: observe original backend
owners/socket closure independently. Do not copy raw bodies into DO storage.

[Cloudflare outbound documentation](https://developers.cloudflare.com/containers/configuration/outbound-traffic/)
limits HTTP interception differently from arbitrary TCP egress. This private
resource role requires no Neon/Stripe connection and can deny all outbound
Internet. Later Neon native TLS PostgreSQL/Oban notifications need a separately
qualified direct path; an HTTP allowlist is not that evidence. Stripe test mode
delivery/header/order/retry compatibility, endpoint/account/mode/generation/secret
authority, durable inbox + atomic Oban enqueue before acknowledgment and billing
reconciliation remain separate P15/P16/G23 gates. No synchronous Stripe call is
added to update delivery or recovery.

## Selection and acceptance boundaries

Root selects the proposed constants, launcher interfaces, fixed matrix and owned
implementation files before work starts. A fresh independent transport/resource
reviewer must replay private Linux enforcement, shutdown/OOM/privacy and local
TLS cases, including negative controls. Root separately assigns accountable
operational, ingress/privacy and billing/security reviewers for deployed
Cloudflare, selected public trailer behavior, Neon and Stripe staging gates.
No reviewer is assigned or acceptance inferred by this proposal.

The packet's executable `verify.py --live` checks its closed profile/schema,
matrix completeness, negative contract mutations, exact source/dependency/tool
bindings and seals. Its count is **contract/evidence checks, not runtime behavior**.
This authoring run starts no listener, BEAM role, stress helper, database, Linux
container, daemon or native instance. Cleanup reports that limited scope. Later
runtime cleanup must prove owned cgroup task count zero, process/namespace/socket
and pipe closure, no listener, no raw dump files, and identity-checked scratch
removal; preserve unrelated projects and retained redacted receipts.
