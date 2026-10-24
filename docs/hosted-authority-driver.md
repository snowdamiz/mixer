# Isolated current-authority driver candidate

This is a frozen executable candidate for independent review, following the
[root driver direction](hosted-authority-driver-contract.md). It does not install
or accept live hosted authorization. The binding product plan remains unchanged.
The schema/catalog correction is a separate prerequisite; this packet deliberately
retains the original schema and resolver bytes and does not implement startup
schema selection.

The [receipt](../verification/hosted-authority-driver/receipt.json) identifies the
final run, all attempts, exact copied hosted source, dependency sources, command
arguments, environment, tools, outputs and cleanup. The [checker](../verification/hosted-authority-driver/check.py)
validates those frozen bindings. Replay uses the retained inputs and dependency
archive, not the current hosted checkout:

```sh
python3 -B verification/hosted-authority-driver/check.py
python3 -B verification/hosted-authority-driver/run.py --frozen-run run-7
```

The specimen copies the actual accepted `hosted/` source into disposable scratch,
adds only the [source overlay](../verification/hosted-authority-driver/probe/lib/),
and compiles with the unchanged `mix.exs` and `mix.lock`. The runtime uses the
actual `MixerHosted.Repo`, Ecto 3.14.2, Ecto SQL 3.14.0, Postgrex 0.22.4 and
DBConnection 2.10.2. Its one-connection runtime pool logs in as
`mixer_hosted_runtime`, never the fixture owner. Separately named raw fixture
connections provision synthetic data and hold adversarial locks. No SQL Sandbox,
mock resolver, HTTP server or provider is involved.

`Envelope.authenticate/2` calls the accepted configured verifier and captures
`System.system_time(:second)` immediately after its successful return. It preserves
the accepted `VerifiedIdentity` shape. The tests explicitly construct synthetic
verified identity envelopes; they do not qualify a provider or an authenticated
HTTP path. Transaction entry retains the captured completion time. Exact bounded
UTF-8 credential-reference bytes are SHA-256 hashed with OTP crypto before any
SQL transport. No raw token or credential reference appears in query parameters,
query evidence, or retained driver exceptions. Query evidence records fixed SQL,
parameter counts and durations; it intentionally omits parameter values. Unknown
OAuth scopes keep the accepted verifier's known-scope intersection behavior;
unknown names supplied directly to this internal transport are malformed.

The transport constructs the exact six named SQL records using parameterized
scalar fields and fixed qualified `ROW(...)::mixer_authz.type` expressions. It uses
neither record-text construction nor JSON record conversion. Every actual
resolver call is a single function relation in `FROM`, with explicit scalar
projection. The driver validates one-row cardinality, exact field counts,
identity/target/transaction equality, 16-byte UUIDs, exact integer numerics,
positive signed-bigint revisions, UTC timestamp values and ordered, unique,
maximum-64 membership witnesses. Decision and witness composite construction is
also exercised against the real driver's composite/array decoder. The protected
path uses flattened fields so no custom Postgrex type registration is needed.

Lookup, lock and decision are three separate statements. The unchanged SQL still
reacquires all five shared locks during decision and reads its fresh internal
snapshot. PostgreSQL's actual function-counter deltas demonstrate one
`decide_current`, two `lock_admission_rows`, six `lookup_admission` and one
`recheck_current` execution for one successful complete invocation. The internal
calls account for the extra counts; column projection does not repeat the
VOLATILE outer function.

The coordinator rejects a foreign dynamic Repo before querying its transaction
state. It rejects nested entry and uses `queue: false` with the original absolute
monotonic deadline, capped at 5,000ms. READ COMMITTED is the first statement after
BEGIN. It installs one random local nonce and one fixed database wall deadline;
subsequent queries never refresh either. Every guarded operation compares the
owning process, fixed Repo, dynamic Repo, complete immutable active context,
action/target, actual backend PID, full xid text, database, session/effective role,
`role=none`, nonce, isolation and original SQL deadline. The active value retains
the complete identity, target, principal/binding/family, five revisions and ordered
witness. Changed copies fail closed; an exact immutable copy within the same
trusted invocation is intentionally equivalent.

Each fixed repository call receives the remaining original monotonic budget;
transaction-local statement timeouts decrease, with a 250ms lock timeout. The
application clock limits admission, all calls and callback completion. The fixed
SQL wall deadline additionally limits database work, and the final guard checks
fresh database time against credential expiry and the original completion window.
Neither clock is extended by copying a context or changing a local setting. No
system-clock jump was induced. DBConnection can close an over-budget connection;
it does not terminate arbitrary BEAM code. The invocation marker is removed in
`after`, including rollback, exception and timeout paths. Transaction-local nonce,
deadline, statement and lock settings return to their exact startup defaults.

The callback is a fixed, internal fixture module with a closed set of bounded
modes. It inspects context or invokes one narrowly authored synthetic INSERT into
an isolated fixture table. Deliberate raw COMMIT/BEGIN, nonce changes, waits and
exceptions are fixture modes for adversarial tests. No caller-supplied SQL or
function is accepted, no domain object is mutated, and no tenant head is acquired.
Writer-only `recheck_current` remains directly inaccessible to runtime. A later
combined writer must use its lock-free recheck after every relevant wait and
before effects; this specimen does not implement that writer or claim membership
windows cannot advance after the recorded decision clock.

The original schema suite ran unchanged once: 128/128. The final actual-driver
matrix passes 56/56. Its separate cases cover all 18 supported role/action pairs,
current/absent/disabled/versioned identity, credential denial and valid-after,
original completion and expiry bounds, UTF-8/backslash and NUL/invalid-byte
rejection, scope/ancestry, 64/65/duplicate/window/organization-only membership,
changed immutable copies, foreign process/Repo/dynamic Repo, nested entry, closed
contexts, raw transaction replacement with restored nonce, busy checkout, slow
SQL, callback deadlines, exact local cleanup and no effects on rejected paths.
A separate BEAM callback-entry counter confirms policy/identity denials and busy
admission never enter the protected callback; zero SQL effects alone would not
prove that distinction.

Observed values include a full xid above 2^32, exact 9007199254740991 identity
numeric, 9223372036854775806 revisions, six-digit timestamp precision, all five
canonical lock waits, both revoker orderings, and fresh expiry after a confirmed
wait. The full xid fixture changes only the epoch of a newly initialized, offline,
disposable cluster before its first start. Lock evidence uses actual
`pg_blocking_pids`, not an inferred uncontended-lock catalog. Positive policy is
read again on the next invocation. Synthetic effects roll back on deadline and
exception paths. A failure racing an already-sent COMMIT remains uncertain;
this packet does not requalify lost-response/idempotent retry behavior from the
separate atomic-writer work.

Every failed attempt remains retained. Early compile failures, a fixture lifecycle
UUID collision, the dynamic-Repo guard order and delayed PostgreSQL statistics
flush were corrected; no failed attempt is represented as a pass. All owned
clusters and scratch were removed, no TCP listener opened, and no other project's
processes, simulators or phones were touched.

Independent review and root acceptance are required before live integration.
Final schema/catalog startup selection, combined domain RLS/writer composition,
authenticated HTTP/cancellation, artifact metadata resolution, credential and
management lifecycle, Neon/TLS/pooling/failover, Cloudflare/R2/Oban, published
FieldLog, physical-phone final acceptance and every GA gate remain pending.
