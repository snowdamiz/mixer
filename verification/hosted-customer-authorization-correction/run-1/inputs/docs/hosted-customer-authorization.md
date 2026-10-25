# Ordinary customer authorization prerequisite

`MixerHosted.Authorization.Policy` implements the existing
[hosted identity contract](hosted-identity-contract.md)'s first decision slice:
human `artifact.read`, `artifact.upload`, and project `audit.read`, each narrowed
by its exact verified `mixer.*` token scope. The full binding scope remains
`mixer-product-plan.md` §§13, 17 and 18. This prerequisite does not complete
ordinary customer console authorization or a GA gate.

Root coordinated this contract before implementation. All other actions and
service/CI identities fail closed. No route, verifier, existing repository,
migration, provider configuration, dependency, or root execution index changes
are included. Only ordinary identity source was used; no frozen authority or
catalog implementation or rejected outbound Worker implementation was used.

## Frozen product ceilings

This preserves the six-role baseline from the identity contract. These are
capability ceilings requiring current authoritative membership and restrictions,
not permissions implied by a role name. Only the last three columns are
implemented by this pure slice.

| Role | Future product ceiling, still requiring dedicated authorization | Artifact read | Artifact upload | Audit read |
| --- | --- | --- | --- | --- |
| owner | Project/member/service/billing administration; protected ownership transfer; eligible for explicit environment release grants | yes | yes | yes |
| administrator | Project/member/service administration excluding owner grants/removal/transfer; billing summary; explicit release grants | yes | yes | yes |
| developer | Assigned-project metadata/artifacts/build request/validation; explicit development/staging release grants; production requires another eligible role | yes | yes | yes |
| release_manager | Assigned-project metadata/artifact read/validation; explicit release grants; upload/build request requires another eligible role | yes | no | yes |
| billing_manager | Organization billing/usage/invoices/spending caps; no private artifact/source/log access | no | no | no |
| viewer | Assigned-project metadata/artifact read/audit | yes | no | yes |

The exact narrowing scopes are `mixer.artifact.read`, `mixer.artifact.upload`, and
`mixer.audit.read`. A scope cannot create membership, and a role cannot replace a
missing scope. Multiple current eligible memberships union capabilities; only
the memberships contributing the evaluated action appear in the decision.
Unknown roles, fields, actions, wildcard IDs, or policy representations deny.
Private source, logs, symbols, source maps, signing credentials, billing, builds,
releases, approvals, and member administration remain unsupported.

Future services need an explicit organization-owned service principal,
project/action/environment ceiling, active credential or reviewed CI workload
binding, and token-scope intersection. A service must never become a human
owner, member administrator, billing manager, or independent human approver.
This slice rejects all service identities; synthetic owner data cannot bypass
that restriction. Environment release grants and optional two-person production
approval remain pending, including proposal/action/cohort/policy binding and
current distinct human approvers. Existing customer authorization policy must
eventually control automation without an extra manual approval when none is
configured.

## Inputs and evidence

`Scope.new/1` accepts only a bounded organization → project → application →
environment path with no gaps. Each non-null identifier is 1–128 UTF-8 printable
bytes and cannot be `*`. Artifact policy requires the complete environment path;
project audit requires only organization/project. This scope does not include
platform/runtime/content binding and cannot replace artifact validation.

`Policy.evaluate(identity, action, target, evidence, now)` accepts the ordinary
`VerifiedIdentity` structure and closed server evidence maps. Inputs are bounded
before enumeration: at most 32 distinct token scopes of 1–256 bytes, 64 membership
lifecycle entries, exact record keys, bounded identifiers, and integer time and
revision ranges. Improper lists and duplicate membership lifecycle IDs reject.
Distinct lifecycle IDs can contribute the same role; they confer no greater
capability than that role's ceiling. No atom is created from external text.

The repository evidence has these exact fields:

| Field | Required server-owned content |
| --- | --- |
| `binding` | Exact profile ID/version, issuer, subject, client, identity class, internal principal ID |
| `binding_active`, `profile_active` | Current binding and trust-profile enablement |
| `principal` | Internal ID/class, active state, valid-after (`not_before`), revision |
| `credential` | Exact verified credential reference and principal ID, active state, valid-after, optional expiry, revision |
| `target` | Actual stored or validated immutable-resource scope and aggregate active ancestry |
| `memberships` | Lifecycle ID, principal ID, canonical role, organization/project scope, explicit project binding, active state, validity window, revision |
| `organization_revision`, `project_revision` | Current authorization-head versions for audit attribution |

Organization-only membership does not grant project visibility. An organization
membership must explicitly state `project_binding: :all_projects` to cover
projects. A project membership uses `:exact_project`; application/environment
memberships and implicit wildcard expansion reject. Every membership must bind
the resolved principal. The authoritative target ancestry must equal every
requested organization/project/application/environment field, and all ancestry
must be active. These data relationships must eventually be established by
durable foreign keys and queries, not a client's asserted parent IDs.

Identity binding must match profile version, issuer, subject, client, class and
credential reference exactly. Disabled profile/binding/principal/credential,
wrong principal/class/reference, credential expiry, or a token issued before a
current principal/credential valid-after fence rejects. The existing verified
token expiry and maximum 30-second future issued-at allowance are preserved.
This slice introduces no separate token-lifetime or evidence-cache allowance.

Success is `{:ok, %Policy.Decision{...}}`, an audit projection containing exact
action/target, principal/credential/profile references, contributing membership
IDs/roles, revisions and evaluation time. It contains no raw bearer. A Decision
is ordinary trusted-process data, not a transferable authorization ticket, and
no domain store accepts it. Opaque types or private constructors would not
protect against malicious code inside the trusted BEAM process.

Errors are bounded atoms: invalid request, unauthenticated identity/current
credential, nonvisible/inactive target, insufficient supported permission, or
authorization unavailable. Public mapping remains the existing identity
contract's 400/401/404/403/503 policy; no HTTP endpoint is implemented here.

## Durable and public integration still required

`Repository.evaluate/5` defaults to the unavailable implementation and accepts a
repository module only as trusted server configuration. It validates identity,
supported action and target before requesting policy data. The module implements
`with_evidence(lookup, callback)`, invokes the pure callback under its protected
transaction, and returns its result. Exceptions, malformed results and missing
dependencies become `authorization_unavailable` without logging credentials.
The lookup contains only the exact identity binding/credential reference,
action and target; token scopes or request role names are not database authority.

No durable implementation is supplied. To connect it safely, the ordinary server
repository must resolve current principal, credential, trust/binding state,
membership and actual target lineage on the same connection and real protected
transaction. Use the identity contract's canonical shared lock order and
conflicting revocation-writer locks at READ COMMITTED, bounded transaction and
statement timeouts, current queries after lock waits, and no positive evidence
cache. Recheck before persisting an effect. Failed/unknown lookup denies. Never
perform provider calls or customer code while holding those locks.

Revisions supplied alongside old evidence cannot prove freshness. The retained
negative-boundary test deliberately shows that an old enabled snapshot still
evaluates after a different snapshot is revoked. Only a qualified durable
lookup/locking protocol can close that race. No cached evidence grace is defined.

The separate `Authorization.with_authorized_transaction` facade from the identity
contract remains required: create a connection/request/action-bound internal
context accepted only by the domain repository; perform tenant/RLS enforcement,
current authorization before idempotency-result retrieval, domain mutation,
immutable audit and Oban intent atomically. The pure Decision here is not that
context. Builds.Storage remains internal and unauthorizing. A future protected
Phoenix pipeline must place verified identity, durable authorization and bounded
command parsing before customer operations. The SolidJS console still has no
connected customer data from this slice.

## Verification boundary

Run `python3 verification/hosted-customer-authorization/run.py`. It creates a
unique owned temporary directory, copies and hashes only ordinary identity and
new policy source/tests, compiles with warnings as errors, and runs standalone
ExUnit without Mix application startup, test helpers, dependencies, database,
provider, network, UI, native runtime or device execution. It records exact
commands/environment, tool versions, the root-supplied source revision (explicitly
not independently queried), input tree digest, stdout/stderr, exit status and
cleanup. Each attempt preserves its own inputs and driver.

The tests cover all six roles across all three supported actions, exact token
scope narrowing, mismatched tenant ancestry and identity binding, principal and
credential disablement/expiry/valid-after, membership revocation/window/limits,
explicit organization-wide project access, unsupported service/build/release/
billing actions, malformed/duplicate/oversized evidence, repository failures and
the stale-snapshot boundary. They are host policy evidence only. Durable
membership/RLS/race tests, real identity/SSO, service/CI issuance and revocation,
customer HTTP workflows, build/release/billing operations, external qualification
and accountable GA review remain pending. No native instances or other projects'
processes are created or changed.

Observed final producer result: `run-3` compiled with warnings as errors and
passed **26/26** standalone ExUnit tests on Darwin arm64, Elixir 1.20.4 and
Erlang/OTP 29.1.1 (ERTS 17.1), with `ERL_FLAGS='+S 2:2'`. `run-1` is retained
with 24/26 passing: it exposed an audit-target function clause and newline
identifier admission, both fixed before the passing `run-2`. Final `run-3` adds
the existing verifier's profile-version ceiling and explicit control-character
checks. All three owned temporary roots were removed. The retained test inputs
are the exact executed sources; this trailing result note was added afterward.
