# Per-operation worker controller implementation

This slice implements the strict internal Worker ingress and the per-operation
SQLite Durable Object ledger selected in the [frozen controller contract](hosted-worker-controller-contract.md).
Root selected this source boundary after reviewing that contract. The production
entry authenticates and validates real wire-v1 requests, then returns a bound
`unavailable` observation because qualified production time and real providers
are deliberately unavailable. It is neither a complete hosted controller nor a
deployed worker fleet. The independent audit registry/scheduler, missed-wake
recovery and exhausted-alarm-retry recovery remain pending by root's scope decision.

## Owned source and behavior

`hosted-worker-controller/src/index.ts` routes only the fixed internal POST after
machine authentication, a bounded UTF-8 body and complete codec validation. It
addresses one DO using the versioned environment/pool/controller/operation hash.
The DO repeats authentication and validation before its engine entry. A valid
configured pool principal gives machine permissions only; Phoenix still owns
tenant policy, admission, immutable source authorization and business state.
Unconfigured/invalid machine credentials reject before routing. No public
runner/result, tenant, release, signing, source-fetch or deployment endpoint is
installed. A four-second edge response timer and four-second bounded-body timer
are local request bounds, not proof of a total platform CPU/memory ceiling.

`wire.ts` independently implements a duplicate-aware finite JSON parser and the
closed v1 schema. It rejects escaped-equivalent members, malformed UTF-8, trailing
messages, floats/exponents, noncanonical decimals, unsupported enum/shape/scope,
and excessive body/depth/token/raw-string size. It preserves all int64 values as
strings/BigInt and preserves SQL expiry microseconds. The old operation hash
uses an exact numeric fence token; the immutable binding uses a string fence and
deadline. The response echoes the current nonce and complete current binding,
with no spec/deadline additions or previous-response cache. Body bytes give
Workers a fixed-length response source; actual managed-edge HTTP/1.1 EOF and
header behavior remain unverified.

The pinned Jason-only compatibility probe found two issues beyond the original
36 producer vectors: Jason's Unicode control escapes use uppercase hex, and
Elixir `String.printable?` accepts DEL U+007F. The first added-vector run failed
on the control-escape hash. The independent controller now walks string
characters to reproduce the required Jason bytes, including literal backslash-u
text, while accepting the exact tested printable repertoire. The failed replay
is retained as `test-attempt-2.*`; the frozen transport/client/contract files were
not modified. The probe loads only Jason 1.4.5 BEAMs and asserts zero loaded
Mixer modules before and after execution. Its source, output, 24 vectors and
exact BEAM/tool hashes are retained separately from the original 36 vectors.

`principal.ts` validates closed restart-scoped machine configuration, canonical
32-byte base64url bearer credentials, and configured environment/controller/pool/
platform scope. Configuration stores SHA-256 of the exact token text; it does
not log or echo a token. Fixed-size digest equality is delegated to standard
Web Crypto HMAC verification with a temporary comparison key. There is no custom
cryptography, credential rotation or tenant authorization. Managed ingress-added
headers are separated from application fields; raw duplicate handling, header
rewriting, TLS and peer closure still require the actual Cloudflare ingress gate.

`schema.sql` and `ledger.ts` use actual synchronous SQLite DO transactions and
durability synchronization. Protocol integers are TEXT, including epochs,
revisions, expiries and the bounded state version. Static parameterized SQL
persists the immutable binding, current watermark/owner, **separate issued effect
request/guard**, stable provider identity, launch-dispatched bit, desired stop,
claim consumption, pending result, terminal evidence and reconciliation state.
There is one operation row and at most 32 audit slots. No TTL, deleteAll,
tombstone recycling, namespace replacement or automatic restore is implemented.

`engine.ts` samples qualified time after its transaction begins and checks
lexicographic BigInt fences/owner/expiry. It rejects stale commands before a
provider query and checks current authority again before effects and claims.
A newer query cannot authorize an older prepared launch. Equal-pair renewal can
only extend expiry. A committed stop revokes unissued claims before the provider
call and survives a missing worker, delayed launch, owner transfer, expiry and
process restart. An expired request cannot create new authority. A previously
committed stop can still be enforced while the clock is unavailable.

Launch intent, wake alarm and dispatch state are durable before the external
call. One provider call is owned per DO; callbacks receive a cancellation signal
and have a two-second timeout. A noncooperative provider retains the occupied
call slot until its local completion is observed. Timeout never proves remote
cancellation. Once a launch was marked dispatched, reconciliation only inspects
the same resource identity; an absent response cannot authorize relaunch or a
replacement. A crash after dispatch marking but before the call can lose work;
the slice chooses conservative uncertainty over duplicate execution.

The internal claim decision commits consumption before returning a grant
decision. Lost responses and process/container restart cannot reset it. Claim
and report objects have finite closed shapes. Result acceptance checks the exact
claim/resource/instance/boot/binding, the finite Lifecycle result shape, current
authorization and an object-verifier interface. It retains a matching report
acknowledgement, conflicts on a different report, and waits for definitive
owned-work drain and settled launch tickets before returning terminal completion.
The production object verifier rejects everything and no production runner
ingress exists. These interfaces therefore do not qualify an authenticated real
supervisor, immutable R2 objects, producer attestation or hostile-code execution.

`clock.ts` supplies an explicitly unavailable production clock. `provider.ts`
supplies an explicitly unavailable production provider and object verifier.
Production has no fixture clock, provider selector, raw observation injection,
arbitrary URL/module, supervisor credential, cloud provisioning credential or OTA
signing key. Real Linux/macOS adapters, their pinned supervisor images and resource
identity/termination guarantees require a later source and qualification slice.

## Runtime verification and dependency boundary

The development inputs are pinned to Node 22.23.3, npm 10.9.9, TypeScript 5.9.3,
Miniflare 4.20260730.0, workers-types 5.20260730.1 and transitive workerd
1.20260730.1, with compatibility date 2026-07-30. The lockfile contains 58 exact
package entries with licenses, integrity and purpose in the owned
`hosted-worker-controller/THIRD_PARTY.yml`. They are development dependencies;
the production module closure has nine owned compiled/data files and only the
built-in `cloudflare:workers` external module. The TypeScript-AST closure audit
excludes every test entry and rejects dynamic/unselected module imports.

Installation and clean reinstall both used `--ignore-scripts`. The workerd
package's postinstall declaration was inspected and remained disabled; its installed loader
resolves the pinned optional Darwin binary directly. No dependency script was
enabled. No Wrangler/container wrapper, new production dependency or global
tool installation was added. The receipt binds all installed dependency file
hashes plus the native runtime, compiler, Node and relevant OS/tool versions.

Commands from `hosted-worker-controller/`:

```sh
npm ci --ignore-scripts --no-audit --no-fund
npm run build
npm test
node audit-build.mjs
```

For an independent replay, set the test-only `MIXER_CONTROLLER_TEST_REPORT` to a
new absolute report path so replay output does not overwrite this frozen packet.
That setting belongs only to the Node test runner and is absent from production.

The final suite passes 28 reported groups. It replays the unchanged frozen 20
scenarios plus five fixtures, all 36 original Elixir producer vectors and the
24 extra Jason/control/Unicode vectors. Additional actual workerd/SQLite tests
cover closed-shape/parser bounds, managed metadata versus ambiguous auth,
rehashed immutable conflicts, 32 simultaneous ensures, 16 simultaneous claims,
stop while a launch call is actually awaiting, abortable timeout, issued-guard
transfer, final time rechecks, clock rollback, exact SQL TEXT types, transaction
rollback, bounded audit history, report validation/teardown and durable restore
quarantine. One test leaves the runtime with no customer/control HTTP for 1.35
seconds and observes a real persisted alarm callback, rather than manually
calling the handler and labeling that automatic delivery.

Four tests identify the exact owned workerd child PID and executable, send
SIGKILL, then restart a new runtime against the same SQLite persistence. They
cover durable launch intent before provider call, provider effect before ledger
acknowledgement, consumed claim before grant, and permanent stopped state before
a later ensure. The finite fake provider's call journal is also SQLite-backed.
Those are actual runtime/storage/process tests with modeled external effects;
they do not become Cloudflare provider, Linux sandbox, macOS host or descendant
termination receipts. The final report has 114 owned cleanup records, including
four killed child identities; all owned Miniflare instances and temporary storage
are disposed/removed. The collector independently checks those paths and that
no process runs this project's exact workerd binary. Other projects are untouched.

Initial type errors, a Miniflare ESM-rule startup error and the added-vector
control-escape failure remain in numbered attempt logs. The final clean build,
runtime tests and production closure checks pass with empty stderr. Historical
attempt source trees were not individually archived at the moment of failure;
the final frozen tree, artifacts, dependency bytes and commands are sealed in
`verification/hosted-worker-controller-implementation/receipt.json`. This is a
truthful limitation on replaying those historical attempts, not a hidden pass.

## Pending independent audit integration contract

Root explicitly deferred registry/scheduler source to a subsequent bounded slice.
The next public interface should be a trusted private
`PendingOperationRegistry.track(identity, state_version, next_due_us)` and
`scan_due(cursor, limit)`/`wake(identity)` integration. Identity must include the
exact environment/controller/pool/operation, namespace generation and immutable
binding digest. Persist version/decimal time as exact TEXT; reject older updates,
bind equal-version retries identically, cap scans to 32 entries and paginate
durably. Registry entries are wake authority only: they cannot create a build,
renew a lease, grant a claim, release admission capacity or replace an operation.

The per-operation row must persist a registry outbox intent atomically with its
effect intent; cross-DO registration is not a transaction. Idempotently register
before executing a new effect and retain/retry that outbox across crashes.
Registry failure cannot authorize a launch. A separately scheduled Worker can
wake only registered existing identities using a private binding. Missing,
restored or wrong-generation identities must quarantine, never reconstruct
authority from a registry payload. Remove a pending wake entry only against
matching permanent terminal evidence; retain operation tombstones in their
authoritative namespace. An independently retained nonrollbackable authority
record remains necessary before safely accepting a restored ledger/namespace.

That next slice must test real cross-DO persistence, crash between local commit
and registry registration, registration replay/conflict, bounded scan fairness,
alarm rearm failure, exhausted automatic retries, namespace outage, no incoming
HTTP, missed-wake recovery and measured wake latency. A local per-operation alarm
test cannot accept those requirements. Waking the separate Phoenix/Oban processor
roles is also a distinct integration/operational requirement.

## Acceptance boundary

This packet is ready for independent source review of the per-operation slice.
It does not accept the outbound transport candidate or enable Dispatch. No live
hosted module, shared status/inventory, Git, database/service outside owned local
test storage, cloud account, provider API, credential, customer message, native
runtime or physical phone was changed. No customer scripts/source or signing
credentials were used. No deployment or publication occurred.

Keep actual edge TLS/header/framing/EOF, qualified bounded production time,
Linux/macOS provisioning and image pins, one-shot trusted supervisor and
descendant disposal, scoped source/private-R2/result authentication, hard whole
domain resource limits, independent audit recovery, restore/namespace permanence,
Neon/Oban zero-traffic liveness, public authorization, signing, stores, customer
acceptance and all relevant GA gates explicitly pending.
