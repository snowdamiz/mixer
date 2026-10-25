# Ordinary customer authorization prerequisite review

Review status: one reproducible correctness finding awaits coordinated producer
correction. This review evaluates only the selected pure authorization
prerequisite. It does not accept customer HTTP authorization, a protected
transaction, the console, release automation or any GA gate.

Root selected the existing first-slice contract in
[`selection.json`](../verification/customer-authorization-policy-root-selection/selection.json).
The reviewed producer seal is
[`seal.json`](../verification/hosted-customer-authorization/seal.json), SHA-256
`9f8c9019b00fb0e3190362b3ed142ebe0bcc64bed59593b76c61860da803b97b`.
Its 70 entries matched live bytes when checked. Source revision
`b375e55ded9e3e10c327891ab681beff2a471e26` is root-supplied context; the
review did not execute Git. Actual executed source is retained and hashed under
[`verification/hosted-customer-authorization-review/`](../verification/hosted-customer-authorization-review/).

## Finding

**P2 — Reject malformed successful repository decisions.**
`Repository.evaluate/5` at `hosted/lib/mixer_hosted/authorization/repository.ex:42`
only matches a returned Decision's action and target. A configured repository
that returns `{:ok, struct(Policy.Decision, action: action, target: scope)}`
without calling the supplied callback is accepted, although every principal,
credential, membership, role, revision and evaluation-time field is `nil`.
`@enforce_keys` does not validate maps built by `struct/2` at runtime. The
independent regression expects `authorization_unavailable` and reproduces the
failure in [run-3 output](../verification/hosted-customer-authorization-review/run-3/independent-probes.stdout).

This is an accidental-adapter-failure and return-contract problem inside trusted
server code. It is not a requirement to sandbox a malicious repository or other
BEAM module. The facade and documentation claim malformed results fail closed,
so a success should be a complete, identity/action/target-bound callback result;
at minimum a partial or mismatched projection must reject. The configured
adapter still remains responsible for actually invoking the callback inside the
real protected transaction.

## Verified finite behavior

The actual three new modules compiled with warnings as errors on Darwin arm64,
Elixir 1.20.4, Erlang/OTP 29.1.1, ERTS 17.1, `ERL_FLAGS='+S 2:2'`. Independent
`run-3` passed 15 of 16 tests; the sole failure is the finding above. The
producer's existing 26 tests were independently rerun and passed. The receipt
records exact commands, versions, source byte hashes, output and cleanup.
`run-1` is retained as a review-harness syntax failure; the actual modules
compiled and producer tests passed in that attempt, but its independent probes
did not execute. No result from that attempt is counted as probe evidence.
`run-2` first reproduced the finding; `run-3` also confirms the revised review
runner returns exit code 1 for a failed probe. All retained inputs matched the
live bytes at the end of their respective runs.

The passing independent probes establish:

- All six canonical role ceilings match the selected contract. Exact supported
  OAuth scopes narrow those eligible memberships, and empty/inactive memberships,
  billing-only roles, role aliases and arbitrary token scopes confer no grant.
- Profile ID/version, issuer, subject, client, identity class, principal and
  credential references bind exactly. Disabled profile/binding/principal or
  credential rejects. Service/CI and unsupported release/build/billing/member/
  approval actions deny.
- Principal/credential valid-after equal to token issuance is accepted; issuance
  before either fence rejects. Token and credential expiry reject at equality.
  The existing verifier's 30-second future issued-at boundary is preserved,
  with no additional evidence-cache, revocation or membership grace.
- Every requested tenant ancestor must match actual server target evidence.
  Missing ancestors reject; project-only audit is distinct from environment
  artifact access. Organization-only membership grants no project visibility;
  explicit `all_projects` remains confined to its exact organization, and
  `exact_project` cannot cross projects.
- Closed fields, malformed nested data, wrong principals, duplicates and
  unsupported membership forms reject. Proper lists cap at 32 token scopes and
  64 memberships; improper and oversized lists reject before eligibility
  traversal. Bounds use UTF-8 bytes. Headers/role-shaped extra keys do not grant.
- The unavailable repository default, unknown modules, malformed result tuples,
  raised exceptions, throws and synchronous exits return bounded errors. Invalid
  requests never invoke the repository callback, and lookup excludes raw bearer,
  roles and token scopes.

The ordinary artifact `ArtifactV3Policy.id?/1`, Go `protocol.ValidID`, and upload
audit identifier rules use the same ASCII `A-Z a-z 0-9 _ . -` alphabet and 1–128
byte range. Every permitted byte, punctuation-only representative and 128-byte
identifier remains accepted by `Scope.identifier?/1`; no existing identifier or
canonical role is narrowed. Scope additionally admits printable Unicode and
other literal punctuation. That broader parser does not validate an artifact or
expand a literal `project-*` membership into another project; ordinary immutable
artifact/audit validation remains necessary before future composition.

## Acceptance boundary

The pure evaluator deliberately reaccepts an old enabled snapshot after a
separate revoked snapshot was evaluated. Timestamp and revision integers supplied
with evidence cannot establish freshness, lineage or revocation ordering. A
future authoritative current-state lookup, canonical shared/conflicting lock
protocol, same-transaction callback, membership-aware RLS, context-bound domain
repository and fresh authorization before idempotency retrieval remain required.
No positive cache or pure Decision may substitute for them.

The Decision is an audit-oriented projection, not the complete immutable upload
audit record: individual membership revisions, binding/family identities and
platform/runtime/content bindings still need authoritative construction in the
future integration. Any additional customer deny or restriction policy must be
evaluated there; the six-role ceiling alone cannot override it. No domain store
or public route consumes the Decision in this slice.

No database, migration, server, provider, network, UI, native/device or frozen-lane
execution occurred. Each owned scratch directory was removed; no native instance
was created and no other project's process was changed. Durable authorization,
provider/SSO/service/CI qualification, customer workflows, console behavior,
operational review and accountable GA acceptance remain pending.
