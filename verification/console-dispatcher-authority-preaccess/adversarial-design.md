# Fresh adversarial test design

These cases are independent preaccess oracles. They must run only after root
releases a frozen exact execution plan. No case here has run. Tests call only
the unchanged public dispatch/3 for dispatcher outcomes. A separate local
administrator may seed and commit fixture state using the documented lock
protocol; it never serves as the runtime Repo login. Each case starts from a
known fixture or restores committed fixture state explicitly.

## A1: exact tenant bytes and real page projection

Use an own organization `own/é+%2F` and a distinct foreign organization
`own/é+%2f` (NFC versus NFD and literal percent-case distinctions). Both have
active projects with distinct sentinel names; only the own organization has a
membership for the token's resolved principal. Give the own organization at
least two projects with IDs ordered under COLLATE C. Use the same freshly signed
RS256 fixture token, not a constructed VerifiedIdentity.

Dispatch organizations and projects with limit 1. Require 200, exact top-level
and row keys, exact nullable/display-name bytes, sorted unique roles and the
actual first authorized row. Decode and independently reconstruct the cursor
from its documented ordered JSON fields, then dispatch the next page. It must
contain only authorized IDs strictly greater than the prior last ID, without
repetition; the terminal cursor is null. A project cursor for the own
organization cannot be reused for the foreign organization: typed admission
returns `{:error, :invalid_request}`. A cursor does not provide authority.

Every captured response has only status/headers/body; the three unique headers
are no-store, JSON UTF-8 and that call's exact 32-lowercase-hex request ID. A
fixture's deterministic ID proves byte propagation only, not randomness. No
authorization header, token, subject, credential reference, principal/family,
raw membership, witness, profile configuration or connection state may appear
in JSON or headers. Check closed schemas, plus distinctive private sentinels;
do not use a blacklist alone. Body is a binary at most 262144 bytes.

## A2: owner visibility cannot supply project authority after revocation

Start with two live memberships in the own organization: organization_only
owner and all_projects developer. Baseline organizations is 200 with
organization_roles [developer, owner], and projects is 200 with roles
[developer]. Commit revocation of only the all_projects row, under the
organization head lock. Dispatch again with the exact same still-valid token
and a new metadata ID. The organization remains visible with [owner], and the
project page is exactly {projects: [], next_cursor: null} with status 200.

Then revoke the organization_only row and commit. A new organizations dispatch
contains no own organization; in an otherwise empty principal fixture it is
exactly {organizations: [], next_cursor: null}. A new projects dispatch for the
same own organization is generic 404 not_found, rather than 200 or 503. This
tests authority freshness between dispatches; it does not test a racing writer
or expiry during an individual read.

## A3: foreign and absent organizations are indistinguishable

While the signed token is valid and the own organization is accessible, dispatch
projects for the active foreign lookalike and a valid nonexistent organization.
Both are 404 with the same fixed error code/message. Only request_id differs.
Require no foreign name, ID, membership or identity sentinel in either result.
A foreign project cannot enter the own project's page, including lookahead.
If a canonical forged cursor after an invisible ID is used, it remains only an
ordering hint and cannot make an invisible row visible.

## A4: cryptographically valid token loses registered credential authority

Keep membership live, record a baseline 200, then commit credential active=false
under its documented identity lock. Reuse the exact signed token. Require
401 with error.code unauthenticated, fixed Authentication required. message,
that dispatch's request_id and the unique Bearer error="invalid_token"
challenge. Do not accept 503 as a substitute. In a separate isolated case,
family revocation or token expiry may extend evidence; neither can be claimed
from credential revocation alone. Restoring the fixture may permit a subsequent
200, demonstrating a fresh lookup rather than a sticky local deny.

## A5: ordinary transaction refusal and pooled connection cleanup

Use the actual default Repo with pool_size=1 and its restricted login. Before
and after every success/denial, assert get_dynamic_repo() is Repo,
in_transaction? is false, Context.active? is false and the Storage active marker
is absent; preserve unrelated caller mailbox/process-dictionary sentinels.
Observe the same backend for pre/post probes. All 20 source-listed authz GUCs
must equal their original empty/nil baseline after each call, including failure;
transaction-local jit and timeout settings must restore if that is claimed.
Outside a directory transaction the runtime must see no tenant directory rows.

Within an explicitly caller-owned Repo transaction, dispatch must return the
captured 503 authorization_unavailable response and no page. It must neither
commit nor roll back that caller transaction; after caller rollback and normal
cleanup the next clean authorized dispatch can succeed. Do not fake Context or
mutate product-private state to test this case. Runtime context corruption and
late commit failure are separate tests if not exercised by this candidate.

The successful ordinary path plus pinned Session/Storage code binds the role,
20 GUC values, transaction identity and finalization checks. Extra claims about
observed in-transaction values require an explicit passive observation with
no callback authority injection and a bounded/redacted receipt; post-call empty
GUCs alone cannot prove all in-transaction values.

## A6: identity failure precedence remains distinct from authority failure

With the real default owner running, a syntactically accepted token with an
invalid signature produces canonical 401 invalid_token. A malformed token input
or metadata/page shape fails at its existing admission stage. Stopping only
the owned registered default KeyOwner/Admission chain, if included in the
released plan, makes a valid dispatch fail 503 identity_unavailable; it must
never reuse a previous 200. Do not replace ConfiguredVerifier, install trust
snapshots, fake canonical module names or edit KeyOwner private state.

## Evidence and cleanup

The frozen candidate must pin ordinary source/dependency/tool bytes, compile
mode (test-only fixture functions), exact commands, case count and outcomes,
restriction/role/RLS topology, retained output, actual environment, deadlines,
and a redacted fixture identity. Preserve every failure as failure. Prove owned
TLS listener/connections, identity owner/workers/Admission state, Repo pool,
disposable DB/runtime role/cluster, process group and scratch are stopped or
removed according to the exact released ownership plan. Starting no native or
UI resources does not authorize touching any other project's processes.
