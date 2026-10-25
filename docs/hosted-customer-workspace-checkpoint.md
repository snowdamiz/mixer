# Customer workspace checkpoint

Authenticated customer workspace discovery now runs through the real Phoenix
Endpoint, default token verifier, owned read transaction and default PostgreSQL
Repo. The console client consumes those same routes. The reusable organization
and project selector follows the existing website's Flick logo identity,
cream/orange palette, typography and restrained controls. The current App still
requires login/session and selection composition before exposing a connected
customer workspace screen.

`GET /v3/orgs` lists currently visible organizations. `GET /v3/projects` takes the
exact organization ID in the query, preserving slash/dot/Unicode identifiers.
Both support bounded canonical pagination and authenticated HEAD. Human tokens
must contain exactly `mixer.workspace.read`; this does not grant artifact/audit
permissions. Organization roles and effective project roles remain distinct.
Nullable display names are preserved; unnamed whitespace-only identifiers receive
readable visible and accessible markers while selection uses the original ID.

Discovery uses SELECT-only RLS, current identity windows and ordered identity/
selected-head locks inside one owned transaction. Each page is rechecked before
commit; failed commits, revocation and expiry cannot release prepared page data.
Migration 6 adds nullable names and discovery policies while retaining ordinary
artifact isolation. The browser client sends header-only bearer credentials,
rejects redirects, omits cookies, bounds body/deadline work and drops late requests.

| Evidence | Observed local result |
| --- | --- |
| Shared identity session | 20 producer methods and 6 additional independent PostgreSQL controls |
| Directory storage | 24 producer methods and 9 independent controls, including ordinary signed artifact flow under migration 6 |
| HTTP boundary | 22 workspace methods plus 32 existing artifact transport regressions |
| Real signed token scope | 17 verifier methods; old scope-stripping behavior reproduced before repair |
| Production Endpoint join | 11 methods, 65 raw socket responses and the actual Node client against default Repo/JWKS |
| Console | 68 complete host tests and production build; client independent review passes 12 baseline plus 9 new probes |
| Root acceptance | 754 retained/sealed/current file bindings verified; 98 current product inputs |

Counts overlap and are not summed. Seven actual HEAD responses contain no wire
body. Workspace-only tokens are denied artifact/audit access before withheld
bodies. A backend killed after the final workspace read returns 503 without page
data; a fresh retry succeeds. All owned listeners, repositories, key workers,
TLS material, database clusters, temporary compilation files and caches are
cleaned up. No browser/capture/native instance was started.

Three findings are preserved with corrections: an unnamed whitespace identifier
created an unlabeled UI button; strict compilation found an unused argument that
an exit-code-only compiler check had missed; and the original token verifier
stripped the new workspace scope. Corrected UI/compile/token controls and the
full local join pass. Earlier unsuccessful fixtures remain in their original
attempt directories. Exact source, dependency, command and cleanup bindings are
in `verification/hosted-customer-workspace-root-acceptance/attempt-2/acceptance.json`
and the linked producer/review receipts.

Standard Phoenix CI now provisions both workspace test databases and compiles
the actual console client with pinned Node/TypeScript before the required HTTP
join. The workflow and shell syntax are validated locally; the shared full test
runner was not executed locally. Console CI also installs the pinned Elixir/OTP
runtime for its actual identifier-parity test, and changes to that helper/runtime
now trigger console checks. The setup matches Phoenix CI, shell syntax passes,
and the standalone 85-vector test passes; see the supplemental
`verification/hosted-customer-workspace-root-acceptance/console-ci-wiring/receipt.json`.
Exact-push CI is separate pending evidence.

Live identity-provider login, App/session/selection composition, browser CORS,
visual/touch/screen-reader runtime, lifecycle writers, tenant trust, Neon/R2/
Cloudflare operations, customer/FieldLog acceptance and all specified GA reviewer
gates remain pending. Physical phones remain deferred; simulator/emulator and
capture use remain paused under the latest instruction. This local slice does
not narrow the product plan or promote a launch gate.
