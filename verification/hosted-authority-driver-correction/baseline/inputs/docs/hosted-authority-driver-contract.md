# Current-authority driver and transaction integration direction

Root selects a bounded next implementation: connect the existing current-authority
SQL interfaces to the actual pinned Ecto/Postgrex driver in an isolated specimen.
This follows the [transaction selection](../verification/hosted-transaction-context-root-review/selection.json)
and [schema contract](hosted-authority-schema-contract.md). The schema catalog
correction remains under review; this direction does not select a final product
migration or authorize live integration. Preserve the exact schema/functions
while exercising the real driver and coordinator mechanics.

The source baseline is the current accepted `hosted/` application and dependencies.
Use its fixed `MixerHosted.Repo`, identity and command values in an isolated copy;
no alternate production Repo, dynamic customer connection, SQL Sandbox-only test,
mock policy resolver or fabricated authorization decision qualifies. A separately
named owner fixture connection is permitted only for setup and adversarial writes.
No runtime pool uses migration-owner credentials. Keep the API shape internal;
there is no HTTP route or reusable public authorization ticket in this slice.

Authentication finishes before the transaction. Preserve `VerifiedIdentity`'s
existing shape and take its exact issuer/profile/client/subject/class/times/scopes
from the accepted verifier. A trusted invocation envelope captures authentication
completion time immediately after a successful verification; it must not refresh
that timestamp at transaction entry or after body/signature work. Bind that same
time in every SQL identity parameter. The envelope is trusted-code discipline,
not an unforgeable capability within a compromised BEAM process. Original identity
fixtures may construct this envelope in tests, explicitly without claiming a real
provider or HTTP verification flow.

Hash the bounded credential reference's exact UTF-8 bytes with SHA-256 before
SQL transport; retain profile/issuer/client namespace through the complete binding.
Keep raw credentials out of SQL, logs and retained exception data. Unknown scopes
must keep the accepted verifier's known-scope intersection behavior. No identity
fields grant membership. Reject malformed or unsupported transport values before
querying; numeric and timestamp bounds remain enforced in SQL too.

The coordinator must use the selected `queue: false` admission and original
absolute monotonic deadline, capped at five seconds. Reject nested entry, foreign
process/Repo/dynamic Repo, missing invocation or wrong action/target. Set READ
COMMITTED first after BEGIN and install a fresh transaction-local nonce. Capture
and repeatedly compare actual backend PID, full xid text, database, role and nonce
on the same checked-out connection. Keep one fixed database wall deadline alongside
the original monotonic deadline; neither may be extended by later context copies
or queries. Explain and test how both clocks constrain the operation. Remaining
statement time decreases, lock timeout is at most 250ms, and callback completion
must pass the final guard. Delete the invocation marker in `after` on every path.

Transport the exact six SQL composite types without string interpolation or an
ad-hoc PostgreSQL record-text serializer. Use bound scalar parameters with explicit
fixed ROW/type expressions, or the pinned driver's actual qualified composite
support after demonstrating it. Bound every result shape/count/field. Preserve
full xid text, all UUID/digest bytes, integer/numeric exactness, timestamp precision
and membership order. Never expand a VOLATILE composite-returning expression in a
way that executes it once per returned column; use a single function call in FROM
or another demonstrated single-evaluation query shape.

Call the actual `lookup_admission`, `lock_admission_rows`, then `decide_current` in
separate statements. The latter reacquires the five canonical shared locks and
uses its fresh internal snapshot; preserve that implementation. Policy/denial
results cannot invoke the protected callback. Freeze the actual returned immutable
principal/binding/family, five revisions, complete ordered witness, action/target
and transaction identity into the active invocation. Changed copies, stale
contexts, another process or a later transaction must fail closed. An exact
immutable copy in the same trusted invocation is not claimed distinguishable by
object identity.

The internal test callback is fixed and bounded. It may inspect decision/context
or invoke a narrowly authored synthetic effect to prove transaction behavior.
Expose no arbitrary SQL helper to product callers. Tests may deliberately issue
raw COMMIT/BEGIN, forged GUCs or timeouts through the fixture machinery; those
prove stale-context rejection and uncertainty boundaries, not hostile-code
containment. Do not reacquire an authorization lock after a tenant head. The
writer-only `recheck_current` remains lock-free and inaccessible directly to
runtime; no domain or artifact mutation is implemented in this slice.

Execute a finite real PostgreSQL matrix covering successful complete parameter
round trips and each supported action, absent/disabled/current-version identity,
credential denial, valid-after, scope/role intersection, ancestry, membership
64/65/duplicate/window boundaries, all five observed lock stages and both revoke
orderings. Include original-context reuse after commit/rollback/exception,
changed copied deadlines/target/identity, foreign process/dynamic Repo, raw
COMMIT/BEGIN with restored nonce, busy checkout without callback entry, statement
and lock timeout, callback overrun, and fresh time after a confirmed wait. Verify
no synthetic effect on rejected paths and exact cleanup of all local settings.
Retain valid UTF-8/backslash/NUL rejection and full-width numeric transport cases.
Do not repeat every schema-only case merely to inflate a count; preserve the exact
frozen schema suite and add tests for this new driver boundary.

Freeze a source overlay, exact dependency/input/command/tool/output evidence,
all failed attempts, executable replay/checker and owned-resource cleanup. A new
independent review and root acceptance are required before live integration.
Complete schema/startup selection, combined domain RLS/writer composition,
authenticated HTTP, artifact metadata lookup, management/credential lifecycle,
Neon/Cloudflare/R2/Oban, native, published FieldLog and all GA gates remain pending.
