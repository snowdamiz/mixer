# Fixed begin-login independent review

Independent review passes 34 selected PostgreSQL 16 component controls on the
frozen fixed preauthentication begin-login implementation. No blocking product
finding remains in this scope. Root acceptance is pending. The producer separately
passes 30 begin controls and the unchanged 30 accepted bootstrap/load regressions;
these overlapping counts do not establish a larger complete matrix. Application
startup, active identity/login, provider exchange, HTTP routes and authentication
readiness remain pending.

The immutable producer handoff is
[handoff.json](../verification/hosted-browser-begin-login/handoff.json), SHA-256
`35df021b5207e7717242ab3d18181a61a7eb6be16e0ab058e6b68998cd65a2c1`.
The selected clean independent receipt is
[20261025T204044.344416Z-pg16-ae7369](../verification/hosted-browser-begin-login-review/attempts/20261025T204044.344416Z-pg16-ae7369/receipt.json),
SHA-256 `8fb5830f4bb7251e5bc255d2dc42563b99ffce91da3953c3e9286155cdc4efcf`.
It binds 59 selected source inputs, 14 review inputs, 528 dependency files and 51
outputs, with no source/dependency drift. Selected compilation treats warnings
as errors. Runtime output contains only the 34 named pass reports and final count;
stderr is empty. The reviewer made no product edits; frozen product sources
remained unchanged throughout selected execution.

## Contract and source review

The review read the [fixed contract](hosted-browser-begin-login.md), the accepted
owner/Store/private drafts, Protocol/Vault/StoredSnapshot, and only relevant fixed
load/begin/snapshot lifecycle SQL. The archived
[provisional source audit](../verification/hosted-browser-begin-login-review/provisional-source-audit/receipt.json)
exactly matches all three final frozen product hashes. No frozen inspector,
authority-driver or rejected Worker V2 source was read or executed.

The public owner binds the canonical supplied cookie to the duplicate-preserving
raw Cookie header before reservation. Confirmed discovery precedes source session
AEAD opening and exact Origin/recovered synchronizer CSRF verification. One caller
permit and the original five-second deadline span both separately committed,
catalog-checked Store transactions and all cryptography. No request-selected Repo,
provider, clock, callback or SQL operation is accepted.

Direct Store admission independently checks exact session/attempt progression,
canonical distinct state/nonce/verifier, the fixed bounded URL reconstruction,
source/new CSRF and verifier AEAD and any projected old verifier. The old verifier
is authenticated solely for source integrity and never reused. Before mutating
COMMIT, decode compares the entire browser increment map, both contexts/ciphers
and complete new pending attempt, including all null claim/completion fields,
created-time bounds, expiry and state/nonce digests. The source revision CAS is
retained. The direct internal Store API does not prove external-header provenance
against trusted BEAM code; the public owner is the closed request boundary.

Ordinary load keeps rejecting every projected attempt/envelope. Dedicated begin
discovery admits exact current pending state for replacement, including an expired
authenticated attempt while its browser remains live. Fixed load hides claimed
and terminal rows; the component does not claim to observe them. Unchanged SQL
supersedes pending/claimed rows under its existing locks. A claim may increment
audit_sequence without revision between discovery and begin: the independent
actual claim race proves whole-browser comparison rejects and rolls back that
revision-stable race without changing the committed claimed state.

## Executed selected behavior

The clean independent run verifies exact public URL/state/nonce/PKCE/cipher
agreement and full browser increments, identity absence, pending replacement with
fresh values and old cipher clearing, private Inspect, ordinary-load rejection,
seven raw-header/cookie/Origin/CSRF denials without durable mutation, closed
metadata/route/cookie admission, and unavailable absent-browser handling.

Eight selected draft/source mutations cover source session AEAD, old projected
verifier AEAD, new session/verifier AEAD, attempt context, fixed URL, overlong URL
and source audit_sequence. Each returns unavailable without durable change. Other
controls exercise one-winner stale-draft revision CAS, the actual revision-stable
claim race, hidden claimed replacement, real expired pending replacement,
foreign-caller lease denial and completed permit cleanup. This is selected
coverage, not every field or complete owner/lifecycle failure schedule.

The shared publication correction also passes bootstrap/committed-load/nil-load
regressions. Authoritative finish validates and releases the caller permit and
returns only a private wall-time receipt; the previous internal :ok reply shape
has changed. Redacted Publication contains the private value without exposing it.
A retained-PID status request uses the original deadline and generation; subsequent
caller-local monotonic/wall/exclusive-expiry/registered-owner samples fence release.
No successful fallback cleanup call follows that final local sample.

Two independent post-finish controls use official BEAM trace barriers, temporarily
one online scheduler inside the owned VM, and only owned suspended request/tracer
processes. Both prove the final status call had not returned before fault action,
so local publication samples remained ahead. Crossing the original deadline and
replacing the registered owner with a new generation-1 owner both withhold the URL
as commit/committed. Each observes one actual committed begin and unchanged state
after withholding, with no retry. These controls do not claim the owner-side status
sample had not occurred or make external response delivery atomic. The unavoidable
final check-to-return interval remains a qualification limit. The producer's
stronger queued-status identity-loss control is separate evidence.

Unknown COMMIT cannot prove nonmutation and must release no URL or automatic
retry. This independent selection does not rerun all unknown-COMMIT schedules;
the existing Store classification is source-reviewed and separately exercised by
producer regressions. A known committed value can be withheld without implying
rollback.

## Fixture correction, environment and pending gates

The [initial diagnostic attempt](../verification/hosted-browser-begin-login-review/attempts/20261025T203930.917462Z-pg16-ed2630/receipt.json)
completed its 34 invariants and cleanup but is not accepted review evidence. The
review fixture passed log:false to raw Postgrex, which the pinned DBConnection
interpreted as an invalid logger function and printed synthetic encrypted snapshot
metadata. The corrected wrapper omits that option, using its default nil. Product
Store logging was unchanged. The strict clean-output rule rejects such diagnostics;
the complete frozen-product selection was rerun successfully. Original sources,
raw output and receipt remain immutable, with explicit
[attempt dispositions](../verification/hosted-browser-begin-login-review/attempt-dispositions.json).

The actual environment is PostgreSQL 16.15 Linux aarch64/C locale in one owned
random-port loopback Docker container, Elixir 1.20.4/OTP 29, pinned existing BEAM
dependencies, and the actual default KeyOwner. Synthetic restricted roles and a
manually constructed ssl:false RuntimeConfig qualify this component fixture only.
They do not qualify production constructor/TLS/5432/Neon/custody/startup binding.
No fake provider/verifier, injected clock, product rewrite, broad hosted harness,
native runtime, UI, capture, device or unrelated-process discovery was used.

Both attempts record exact container identity before removal and scratch inode
identity before deletion; all owned container/scratch absence checks pass. Final
runtime cleanup records admin, ordinary/lifecycle repos, original/replacement
owners, default KeyOwner, worker supervisor and all transient request/tracer
processes absent. Other projects' resources were preserved.

The full 40-case owner, 18-case lifecycle and 48-case relation runtime matrices
remain pending, as do complete all-field mutation and failure schedules, current
verifier/provider/HTTP joins, active begin, shared Application startup, operational
custody/Neon, immutable external FieldLog/customer, complete native/phone evidence
and accountable GA acceptance. Phones remain disconnected and native/UI/capture
runtime checks remain paused. Internal storage_ready grants no browser/customer
authentication authority.
