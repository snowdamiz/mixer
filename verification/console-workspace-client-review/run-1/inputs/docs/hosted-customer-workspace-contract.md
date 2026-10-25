# Customer workspace discovery contract

This is the coordinated design for the next ordinary customer API slice under
`mixer-product-plan.md` §17. It is source-reviewed design, not an implemented or
runtime-qualified API. Root approved the API, role semantics, nullable names,
query-based organization selection, and directory-mode boundary on 2026-10-25.
The existing artifact/audit authorization contract remains unchanged.

## Source-derived prerequisites

At source revision `c0334a9958df1f1d973310bbbdfc1ac8ec8912f9`:

- `VerifiedIdentity` is bounded verified token evidence, not membership authority.
- `Authorization.Policy` implements human `artifact.read`, `artifact.upload`,
  and `audit.read` only. Billing managers cannot borrow those actions for console
  discovery. All six canonical roles already exist in schema and policy.
- `Session.prepare!` locks profile → principal → family → credential →
  organization head → project head. `Evidence` and `Transaction.Snapshot` require
  a real project; they cannot represent a principal's organization directory.
- `Scope.new/1` requires an organization. Its identifier predicate accepts
  printable valid UTF-8, 1..128 bytes, excludes the exact string `*`, and excludes
  C0/C1/DEL controls. Colon, slash, Unicode, `.` and `..` can be valid IDs.
- `mixer_authz_organizations` has `id, active`; `mixer_authz_projects` has
  `organization_id, id, active`. Neither currently stores a name. Existing
  migrations add identity revisions and artifact storage, not tenant names.
- Current resource RLS and membership coverage are project-specific and exclude
  `organization_only` from project authority. No existing directory route exists.

The receipt in `verification/hosted-customer-workspace-contract/` binds the
explicitly reviewed ordinary sources and these claims. Historical notes informed
scope selection; the current source, rather than their old implementation
status, is the evidence for this design.

## Public API

| Method | Exact path | Query fields | Success |
| --- | --- | --- | --- |
| GET/HEAD | `/v3/orgs` | optional `limit`, optional `cursor` | bounded organization page |
| GET/HEAD | `/v3/projects` | required `organization_id`, optional `limit`, optional `cursor` | bounded project page |

These are new directory collections, not changes to the Go-compatible artifact
paths. Organization selection is a query value because browsers normalize dot
path segments even when the caller percent-encodes them. A client uses
`encodeURIComponent(organization_id)` in the query. There are no path parameters,
organization headers, default organization, wildcard tenant or read-all API.

The success envelopes are closed:

```json
{"organizations":[{"id":"org:one","display_name":"One Team","organization_roles":["owner"]}],"next_cursor":null}
```

```json
{"projects":[{"organization_id":"org:one","id":"project/one","display_name":null,"roles":["developer","viewer"]}],"next_cursor":null}
```

Every row's IDs satisfy the existing `Scope.identifier?/1`, without narrowing
the alphabet to the artifact HTTP path alphabet. Project `organization_id` must
exactly equal the decoded requested organization ID. The database returns rows
in order; the console must preserve that order. There are no totals, credentials,
principal IDs, raw memberships, internal heads, billing identifiers or artifact
metadata in these representations.

`display_name` is the actual stored nullable name. A non-null name is valid UTF-8,
1..256 bytes, printable, and excludes C0/C1/DEL controls. It may contain `*`.
Return its exact bytes without normalization or trimming. A malformed non-null
value fails closed as unavailable; it must not silently become null. The console
uses `display_name ?? id`, displaying the actual ID for historical unnamed rows.

Role strings are exactly `owner`, `administrator`, `developer`,
`release_manager`, `billing_manager`, `viewer`. Every role array is unique and
lexicographically sorted. `organization_roles` includes live organization-scoped
`organization_only` and `all_projects` grants only; exact-project roles never
become organization roles. Its array may be empty. Project `roles` is the union
of live explicit `all_projects` and matching `exact_project` roles and is always
nonempty. These are descriptive current roles, not action grants or a replacement
for authorizing a subsequent request.

## Authorization semantics

The new action is **`workspace.read`**, requiring the exact verified token scope
**`mixer.workspace.read`**. Only human identities are supported. A token's artifact
or audit scope does not imply workspace scope, and workspace scope does not imply
artifact/audit/build/release/billing/member-management authority. No role is
excluded from workspace discovery: all six roles, including billing manager,
can use a live membership for this action.

An organization is visible when it is active and the currently resolved human
principal has any live membership in it, using any of the three explicit binding
modes. A live `exact_project` membership still identifies its active organization
when that project is inactive. This reveals only organization metadata and does
not make the inactive project visible. A principal with no live membership gets
`200` with an empty organization page.

A project is visible only when both organization and project are active and a
live membership explicitly covers it through `all_projects` or matching
`exact_project`. `organization_only` never supplies project authority, including
when its role is owner or administrator. A visible organization with only
organization-only membership returns `200` with an empty project page. Missing,
inactive or invisible requested organizations all return generic `404 not_found`.

Live means `active`, `not_before <= fresh server time`, and `expires_at` absent
or strictly greater than that time. The exact profile/version/issuer/client/class
and subject binding, internal principal, registered credential reference and
family must be current, linked, active, in window and consistent with token
issued-at fences. Unknown bindings/credentials never bootstrap membership.

## Pagination and transport

Query parsing is bounded and duplicate-aware before making a parameter map.
After one strict percent/form decode, names must be exactly those listed above;
unknown/duplicate/empty names, empty segments, malformed escapes and nested or
bracket forms fail with `400 invalid_request`. Project `organization_id` appears
exactly once and is a valid full Scope ID. It is forbidden on `/v3/orgs`. Literal
`+` in an ID must be percent-encoded as `%2B`. The existing bearer plug's earlier
8,192-byte raw-query bound and alternative-token-name rejection remain in force.

`limit` defaults to **50** only when absent. When present, it is 1..100, expressed
as 1..3 decimal digits without signs, whitespace or leading zeros. Empty values
reject. `cursor` is absent for the first page; an empty value rejects. The console
treats returned cursors as opaque and sends them back unchanged.

The cursor is canonical unpadded base64url (`[A-Za-z0-9_-]`), 1..1400 encoded
bytes, containing at most 1024 decoded bytes. Its decoded JSON is a closed object,
with no duplicate or escaped-equivalent keys and no extra fields:

```json
{"v":1,"kind":"organizations","after":"last organization ID"}
```

```json
{"v":1,"kind":"projects","organization_id":"exact requested organization ID","after":"last project ID"}
```

The encoder emits the shown field order, compact UTF-8 JSON, no insignificant
whitespace, ordinary non-control UTF-8 strings with only required JSON escapes,
then unpadded base64url. Decode, validate the exact schema and types, re-encode,
and require byte equality. Version, collection or organization mismatch rejects.
The existing ordinary `Identity.BoundedJSON` can reject duplicate object keys;
no new JSON dependency is required. A cursor is an untrusted ordering hint, not
authority, a snapshot, or proof that its `after` ID is currently visible. It need
not be signed, and every page freshly authenticates and authorizes.

Use PostgreSQL `COLLATE "C"` consistently for ordering and strict `id > after`
comparison. Fetch at most `limit + 1` candidate rows, return at most `limit`, and
emit a cursor for the last returned ID only when the authorized lookahead row
exists. Otherwise `next_cursor` is null. Empty pages have null `next_cursor`.
No offset, count, automatic retry, cross-request snapshot or cached allow exists.
Concurrent grants/deletions can change later pages; a refresh starts over.

Use `BearerIdentity` before query/body parameter fetching. Require the new human
scope before body work, then perform the real current database lookup. GET/HEAD
have no body; reject nonempty streaming bodies, not merely nonzero declared
length. Reuse the artifact HTTP contract's bounded body-read deadline, media and
no-decompression behavior: absent Content-Encoding, absent or exactly one exact
`application/json` Content-Type, and bounded raw reads. No parser or automatic
decompressor runs before identity. No request value can choose Repo, clock,
callback, actor, principal, role, membership, identity verifier or SQL.

All responses retain one `Cache-Control: no-store`, bounded server correlation
`X-Request-ID`, and the existing generic JSON error envelope:
`{"error":{"code":"...","message":"..."},"request_id":"..."}`.
The bearer plug preserves its existing 400/401/503 challenge behavior. New
transport errors are `400 invalid_request`, `415 unsupported_content_encoding`,
and bounded body-read failure; scope/class denial is `403 permission_denied`,
revoked identity is `401 unauthenticated`, and query/lock/topology/commit failure
is `503 authorization_unavailable` with `Retry-After: 1`. Identity-verifier
unavailability remains `503 identity_unavailable`. HEAD performs the same checks
and returns no wire body. Never send page rows before the owning commit succeeds.

## Small internal identity prerequisite

Root owns the extraction of **`Session.prepare_identity!(repo, identity_key)`**
from ordinary `Session.prepare!`. It establishes the same fresh READ COMMITTED
transaction bounds and topology checks, parameterized transaction-local identity
settings, and profile → principal → family → credential shared locks, returning
only resolved linkage. It resets tenant/directory context first. The existing
`prepare!` composes that helper, binds its target, then takes organization and
project heads in the same order. It must preserve existing behavior and tests.

This helper does not establish current authority by itself. The new closed
`MixerHosted.CustomerWorkspace.organizations(identity, page)` and
`MixerHosted.CustomerWorkspace.projects(identity, organization_id, page)` facades own their
transaction, load and validate fresh identity rows after the final lock wait,
execute only their fixed local read queries, and finalize before returning.
Their optional final Repo argument supplies trusted server/test configuration
only: `organizations/2,3` and `projects/3,4`. The page is the closed
`%{limit: integer, cursor: nil | binary}` map with the bounds above. They return
`{:ok, page}` using the exact envelopes above, or `{:error, bounded_reason}`.
The production defaults use `MixerHosted.Repo`. No external or
caller-supplied callback is accepted. No general privileged IdentityContext,
targetless artifact context or new mutation capability is introduced.

Reject an existing Repo transaction, active artifact Context, nested directory
invocation and foreign connection/task/Repo reuse. Bind any internal invocation
state to the owner process, exact Repo/dynamic Repo, live backend/transaction IDs,
current/session user, random transaction-local marker, complete identity/GUC
settings, operation, selected organization and monotonic deadline. Clear it on
every exit. This is trusted application discipline, not a malicious-BEAM or
hostile-SQL sandbox. It is never a response or reusable ticket.

Use `mixer.authz.directory_mode` with exactly:

| Mode | Meaning and tenant settings during a directory read |
| --- | --- |
| empty string | every ordinary identity/artifact session; no directory privilege |
| `organizations` | all four organization/project/application/environment settings empty |
| `projects` | exact organization setting; project/application/environment settings empty |

Workspace modes are set only after identity preparation, with
`action=workspace.read`, `required_scope=mixer.workspace.read`, and
`phase=directory`. Root adds `directory_mode` to the artifact Context's complete
connection-setting comparison. Changing it therefore invalidates an existing
artifact Context. Directory reads never construct or accept that Context, and
ordinary sessions reset the mode even on reused connections.

## Additive schema and RLS changes

The producer owns a new migration after `20261025000005`, not edits to historical
migrations. Add nullable `display_name text` to organizations and projects,
constrained to null or 1..256 octets. Historical rows remain null. Validate the
stronger printable UTF-8 response contract when reading; an invalid stored value
is unavailable. Future controlled writers must apply that same validation and
serialize name/active-state changes through the matching head. No name-edit or
provisioning endpoint is part of this slice. No existing IDs are rewritten or
narrowed, and no production backfill or data correction is implied.

Add explicit **SELECT-only**, directory-mode-gated RLS policies on memberships,
organizations and projects. Keep existing policies for ordinary modes and all
existing artifact role/scope ceilings unchanged. Do not add a permissive policy
that is active merely because organization/project GUCs are empty.

- Membership directory visibility requires the exact bound human identity and
  principal, workspace mode/action/required scope/phase, current identity windows,
  and a live own membership. Project mode additionally restricts organization.
  Organization mode may enumerate only the resolved actor's memberships.
- Organization visibility requires the active row and a live visible own
  membership for its ID; project mode additionally requires the exact requested
  organization. `organization_only`, `all_projects`, and `exact_project` all
  identify the organization.
- Project visibility requires its active row, the active visible organization,
  and a live matching explicit `all_projects` or `exact_project` membership.
  Organization-only rows do not match. Project metadata is needed only in project
  mode; organization mode need not expose project rows.

This dependency is nonrecursive: organization → membership; project →
organization + membership; membership → existing identity records, never back
to tenant resource tables. A small `SECURITY INVOKER` SQL predicate may factor
the exact identity/window/mode guard. It must not become a privileged projection
or accept caller-supplied principal/role authority. No new SECURITY DEFINER
directory resolver, owner bypass, read-all view, authz DML grant, or global tenant
scan is needed. Existing scoped fixed head-lock helpers can be reused.

Preserve ENABLE/FORCE RLS, nonlogin/non-bypass owners, no PUBLIC privileges,
runtime SELECT-only authorization tables and existing helper EXECUTE topology.
Extend topology checks for any new helper using its exact expected signature,
security mode, owner, search path and grants. Directory mode must not expose
artifacts, idempotency, audit events or a write path. A trusted application can
set GUCs; this remains the existing API/SQL trust boundary and still requires
deployed database review. It is not database authentication against a compromised
API login.

## Selected-row serialization and finalization

Use the existing five-second total/statement/idle transaction bounds, 500 ms
lock bound, actual server wall time and monotonic deadline. Query/read failures
roll back with bounded errors. No positive authority is cached.

1. Admit the new action/scope and pagination; own a new transaction; prepare and
   lock the exact identity chain. Capture a deadline before database work.
2. Under the exact directory mode, select at most `limit + 1` ordered candidates
   plus bounded membership witnesses. An organization can use one live
   organization-scoped witness; if it has none, use one deterministic live
   exact-project witness. A requested organization's visibility may similarly
   require one witness outside its returned project page. Role summaries can use
   at most one deterministic witness per canonical role, not unbounded history.
3. Lock all selected organization heads in C-order, then all necessary project
   heads in C-order by `(organization_id, project_id)`, deduplicated. For an org
   page, this is at most 101 org heads and 101 witness project heads. For a project
   page, this is one org head and at most 102 project heads: 101 candidates plus
   one optional organization-visibility witness. The lookahead participates too.
   Missing expected heads fail closed. Do not create them in a read.
4. Existing head helpers operate on exact tenant settings. For each bounded lock,
   temporarily use empty directory mode and `phase=directory_lock` with only its
   exact target, call the fixed scoped helper, then restore the complete intended
   directory context. No directory read runs under that temporary context. The
   fixed local code owns the lock list; HTTP cannot supply it.
5. After the final lock wait, re-read identity, selected resource rows, chosen
   witnesses, current names and effective roles in fresh READ COMMITTED statements
   and revalidate linkage/time/mode/connection. A selected witness that disappeared,
   changed outside its locked scope or expired fails closed; this slice may return
   503 rather than recursively retrying or replacing it through an unlocked
   witness. Every returned row and lookahead must still be currently authorized.
6. Immediately before commit, recheck the exact identity, selected witnesses and
   relevant time windows against fresh actual time, reject wall-clock regression
   or monotonic deadline expiry, and verify the live connection/context. Recompute
   role summaries if temporal expiration removes a grant; return no expired role.
   No caller code runs after this check. Commit success precedes HTTP success.

The controlled-writer protocol is a dependency of the serialization claim, not
an implemented lifecycle API: binding/linkage changes serialize on profile;
principal, family and credential changes on their existing lock classes;
organization-wide membership/name/active changes on organization head; and
exact-project membership/name/active changes on project head, with earlier
classes shared-locked in the same global order. A writer that has committed
revocation before a new read's final lock acquisition must be seen by its fresh
re-read. A writer racing a selected read waits for the read to commit; revocation
does not retroactively cancel a read admitted before it returned.

Directory pages are weakly consistent across requests. New grants or unrelated
changes can alter page membership around the scan and do not require a global
directory lock. They cannot authorize a disclosed selected row: only its locked,
re-read witnesses can. LIMIT bounds returned materialization and head counts,
not all PostgreSQL internal scan work; indexed actor lookups and finite query
deadlines bound operational exposure. Do not add a global membership cap that
rejects an otherwise valid customer solely for having many projects.

## Minimal dependency and evidence order

1. Freeze this public JSON/query/scope/role/mode contract so the SolidJS lane can
   implement exact types, empty/error states and pagination concurrently.
2. Root extracts `prepare_identity!`, resets `directory_mode`, adds it to existing
   Context binding checks, and runs focused existing identity/artifact regressions.
3. The bounded producer adds the names/RLS migration and fixed read-only
   CustomerWorkspace modules plus focused host/PostgreSQL tests. It uses the
   new identity helper, not an artifact transaction or a generalized authority
   framework. No membership/provisioning writer is introduced.
4. Root integrates ordinary HTTP routes/request validation after the backend
   contract passes; run real loopback HTTP + owned PostgreSQL evidence with a
   synthetic trusted verifier, separate nonlogin owner/runtime roles and explicit
   cleanup. Console can then use these actual APIs in host tests.
5. An independent read-only review checks the exact source/evidence and denied
   cases. Root coordinates coherent commit/push and observes CI.

Required executable producer cases include six roles × three binding modes;
organization-only empty project pages; inactive organization/project distinction;
exact ancestry and cross-organization duplicates; names/null/invalid stored
names; full Scope IDs including `.`, `..`, slash, colon, Unicode, plus/percent and
quotes; strict cursor/query/body parsing; deterministic multi-page/empty/terminal
pages; current identity windows and all identity revoke fences; both selected
head revocation orderings; expiry during a lock wait and before commit; witness
fallback failure; absence of cross-actor/ordinary-artifact mode visibility;
forbidden RLS/owner/grant topology; commit/read errors; and connection cleanup.
Integration must verify actual HEAD wire behavior, not a Plug response body.

Source inspection and contract checks do not prove these runtime properties.
Production issuer/SSO, audited lifecycle writers, Neon/Cloudflare topology,
operations, customer acceptance, FieldLog immutable published-package consumption
and G22/G24 acceptance remain pending. Computer use, capture, native
simulator/emulator and physical-phone runs remain paused/pending; this contract
starts none. No production migration/publication, customer messages, credential
changes, signing or store work is implied.
