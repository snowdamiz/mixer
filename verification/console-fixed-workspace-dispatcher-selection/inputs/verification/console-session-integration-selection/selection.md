# W14 production session integration selection

Source-only selection, 2026-10-27. This packet does not authenticate a browser,
accept the pending callback implementation, enable an endpoint or promote G22.
The parent controls implementation ownership and delivery. No product file was
edited by this lane.

`frontend-contract.json` is the closed source proposal for the next fresh lane.
It fixes exact fields/statuses/size/deadline/generation/expiry rules and ownership
against delivered `b231f3d405c06bfb348f193d46a348af0529bd84`. Those new consumer
policy choices await root selection; they are not misrepresented as already
implemented or independently accepted. The server protocol shapes come from the
existing design/storage/runtime documents. The consumer narrows success bodies
to 4 KiB, requires no-store and a duplicate-safe flat JSON subset, invalidates
while hidden/revalidating, uses wall plus monotonic expiry and never grants ready
from any non-200 response. All product edits and execution remain for the parent
to assign after delivery.

## Decision

The production App cannot currently connect to an authenticated browser session
using a callable canonical server contract. The precise missing entry point is
`GET /auth/session`, backed by `MixerHosted.BrowserAuth.Sessions.bootstrap/2`.
Workspace reads also require the two missing fixed cookie routes and
`Sessions.workspace/3`; installing a cookie client alone cannot fill either gap.

At the selected revision, `console/src/main.tsx:7` renders `<App />`.
`App.tsx:69` already accepts `workspaceSession`, and
`state/workspace-context.tsx:9` owns the existing reactive binding. The cookie
client's two targets are `/console-api/v1/orgs` and `/console-api/v1/projects`.
Canonical `hosted/lib/mixer_hosted_web/router.ex` registers neither target and
no `/auth/*` route. Its existing workspace routes are protected `/v3/orgs` and
`/v3/projects` under `BearerIdentity`. The canonical Application graph does not
start a BrowserAuth runtime supervisor/owner or lifecycle pool.

`RuntimeOwner.bootstrap/1`, `load/1`, and `begin_login/4` are private preauth
operations. `finish_result/3` requires `:preauth` and opens `Vault.Preauth`.
Its `%{phase: :storage_ready, generation: ...}` status describes internal storage
admission; it is not the HTTP authenticated-session envelope. The two generations
must never be substituted for each other. Canonical Store has only admission,
bootstrap, load, discover_begin and begin_login operations. There is no canonical
Sessions facade, ClaimOwner, active-session loader/reader, or logout composition.

## Exact missing HTTP and server boundary

The existing design/storage/runtime contracts provide these shapes; the identity
flow document is a design proposal, not an executed login acceptance receipt.
The later runtime contract supersedes earlier injectable dispatcher/provider
arguments: production Sessions must use fixed dependencies.

| HTTP operation | Required fixed server call and successful result |
| --- | --- |
| `GET /auth/session` | `Sessions.bootstrap(raw_cookie_or_nil, %{request_id: server_generated_hex32})`; `200` with exactly `{state:"unauthenticated", csrf_token}` or `{state:"authenticated", generation, expires_at, csrf_token}`. Cookie instruction stays server-side. |
| `GET /console-api/v1/orgs` | `Sessions.workspace(raw_cookie, {:organizations, bounded_page}, metadata)`; exact ordinary `/v3/orgs` representation. |
| `GET /console-api/v1/projects` | `Sessions.workspace(raw_cookie, {:projects, organization_id, bounded_page}, metadata)`; exact ordinary `/v3/projects` representation. |

The session endpoint accepts no body/query, Authorization header, duplicate
session cookie or alternate request-selected identity. Authenticated metadata
requires an active encrypted browser snapshot, exclusive expiry and fresh current
profile/principal/family/credential admission. An unavailable dependency is `503`
with the fixed identity/authorization/session error category; absence of a valid
session can produce the bounded preauth unauthenticated result. No response
contains an API access token, ID token, principal, roles or membership. Public
generation and CSRF are independent canonical 43-character encodings of 32 bytes;
the generation grants no authority. The session's exclusive deadline must remain
capped by the admitted access token/current state/900-second idle rule.

For workspace, Sessions decrypts the exact active token outside authorization
locks and invokes the existing protected pipeline with precisely that server-held
access token. It must use `BearerIdentity` with default `ConfiguredVerifier`,
`CustomerWorkspaceController`/`CustomerWorkspaceRequest`, the ordinary default
`MixerHosted.Repo`, ordinary current membership/RLS/commit checks and existing
response validation. A stored identity, ID token, linkage or cached role cannot
replace this request. Operations and query values are closed; no arbitrary URL,
method, header, provider, facade, Repo or clock can be supplied by browser input.
Preserve existing no-store, bounded JSON/query/body, HEAD and error behavior.

Ingress must route `/auth/*` and `/console-api/*` to Phoenix before SPA fallback,
strip cookies before static assets and ordinary `/v3/*`, and isolate private
responses/Set-Cookie from CDN caches. No CORS workaround or frozen outbound
transport is selected. These are still deployment checks, not facts established
by the local client or source inspection.

## Blocking acceptance is specific

G22 records the callback Unit A candidate as
`producer-passed-independent-review-and-ci-integration-pending`, with independent
review `incomplete-interrupted-no-acceptance` and zero PG16 methods run. Both
selected reviewer compilations failed before database creation, then an automated
safety check interrupted the review. The cleanup receipt records no callback
runtime/reviewer controls executed and all owned resources absent. This lane did
not rerun or delegate that stopped review/harness.

Branch `5595f7b6` and packaging correction `9f15b11f` recorded 95 selected PG16
methods and 664 ordinary methods with two existing skips. They are isolated CI
evidence; neither gives main integration or independent Unit A acceptance.
Protected dirty Store/callback sources were not imported or executed. The packet
uses canonical HEAD Store for callable-source claims and reads the candidate
documents/receipts only for recorded status.

Actual login additionally needs accepted Unit A storage; Unit B supervised
ClaimOwner/shared permit and retained-wall handoff; bounded qualified provider
exchange and separate OIDC verification; exact OIDC/API subject/client binding;
current default API verification; controlled prepare/activation/failure/logout
lifecycle composition; and trusted startup/custody/pool admission. Existing SQL
and Vault primitives do not supply these end-to-end guarantees. Unknown exact
identity remains onboarding-required and cannot create a first owner.
The initial interactive login also needs `/auth/login`, `/auth/callback`,
`/auth/logout`, the fixed `/login` console route and user actions; `/auth/refresh`
is explicitly outside the initial slice.

## Smallest separable product source slice to select now

Implement the consumer of the specified session boundary without enabling a
fake session. Suggested new owned files are:

1. `console/src/api/browser-session-client.ts`: fixed relative `GET /auth/session`,
   `credentials: "same-origin"`, `redirect: "error"`, `cache: "no-store"`,
   `referrerPolicy: "no-referrer"` and JSON accept only. No token, Cookie, origin,
   destination or arbitrary header option. Use bounded strict UTF-8/JSON and
   closed discriminated response keys, canonical43 fields and safe-integer
   exclusive expiry. Honor the contract's 4-KiB session JSON and 8-KiB response
   ceilings; do not inherit the workspace reader's larger 256-KiB limit. Timeout,
   cancellation, non-JSON, missing route/SPA fallback, malformed fields and all
   dependency/network failures fail unavailable and expose no provider text.
2. `console/src/state/browser-session-controller.ts` (with a small Solid owner if
   needed): one in-memory session check owner, initially unavailable. Only a
   live successful authenticated envelope can produce a new immutable
   `{kind:"ready", client:createCookieWorkspaceClient()}` value. Unauthenticated
   metadata produces the existing unauthenticated capability; every failed,
   expired, superseded or invalidated check clears private workspace capability.
   Fence late results by operation epoch plus captured server generation. New
   generation rotates the immutable session object even for the same account.
   Expiry uses both the exclusive server deadline and a monotonic bound against
   local clock rollback. No persistent browser storage or token handling.
3. `console/src/main.tsx`: mount that owner within a Solid lifetime and pass its
   reactive session accessor into the already present App seam. Wire startup,
   foreground revalidation and explicit retry/invalidation; cross-tab messages
   carry only invalidation and cause fresh server reads. Dispose owned requests,
   timers/listeners/channel. Do not alter the released pagination code.

This is concrete source integration, not a successful login claim: against the
current canonical backend it must remain unavailable because `/auth/session`
is absent. A static asset server's `200` HTML fallback must also stay unavailable.
Tests may synthesize metadata as fixtures but fixtures cannot become production
authority or preinstall a ready client. The production client is constructed only
after the accepted same-origin endpoint has supplied current authenticated state.

An independent backend source slice can separately implement a private fixed
workspace dispatcher against the ordinary bearer pipeline, with no public cookie
route and no Sessions/provider injection. Root must first select its exact local
interface and ownership. This is useful pipeline composition, but it does not
remove the active-session/Unit A/Unit B/provider dependencies above.

## Minimum verification for that subsequent implementation

Run meaningful host tests for closed successful/unauthenticated responses;
canonical43/safe-integer/unknown/duplicate-field failures; 404 and HTML fallback;
no-store/redirect/cookie/header policy; bounded UTF-8/body read/deadline handling;
startup and same/different generation behavior; expiry and local-clock rollback;
replacement, request cancellation, late-response races and synchronous Solid
read/action fences; foreground and cross-tab invalidation; disposal and zero
persisted credentials. Include the actual cookie workspace client and App binding
with deterministic synthetic server metadata, labelled as host fixtures.
Before claiming connected production workspace, independently qualify the real
Endpoint/default verifier/default Repo session-to-workspace join, logout and
revocation races, actual cookie policy, provider/startup/custody and ingress.

This selection lane ran only source/receipt reads and its bounded Python source
audit. No product build, compiler/test binary, BEAM/PostgreSQL/container/provider,
browser/UI/capture, native simulator/emulator or physical phone ran. No global
process inventory, credential/customer change, Git mutation or publication was
performed. Source-check success is not runtime/security/GA acceptance.

See `receipt.json`, `inputs.json`, `source-checks.json` and `audit.stdout.txt` for
exact revision/tree, selected source digests, commands/tool versions, check output,
PID/resource scope and observed limitations.

The first source collector failed its own uniqueness assertion because the
callback status is repeated under three separate GA gates. The corrected audit
selects G22 by exact id. `audit-before-g22-scope-fix.py` and
`audit-attempt-1-failure.json` preserve that source/output failure; it did not run
product tests or the stopped callback harness and is not reported as a pass.
