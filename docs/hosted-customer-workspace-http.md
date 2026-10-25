# Customer workspace HTTP transport

The ordinary Phoenix router now exposes `GET /v3/orgs` and `GET /v3/projects`
through the existing bearer identity plug. The identity-only pipeline is named
`customer_identity`; existing artifact paths use that same pipeline. The binding
API is `docs/hosted-customer-workspace-contract.md`. This slice implements the
HTTP boundary only, not workspace policy, provisioning or deployment.

## Request and response behavior

`CustomerWorkspaceController` calls the production facade through only
`MixerHosted.CustomerWorkspace.organizations/2` and `projects/3`, using its default
Repo. It receives identity solely from `BearerIdentity`. A trusted test initializer
can choose a facade/clock; no HTTP value can choose dependencies, Repo, actor,
principal, roles, verifier, callbacks, time or SQL.

After the bearer plug's existing bounded credential/query-name policy,
`CustomerWorkspaceRequest` requires a verified human identity and the exact
`mixer.workspace.read` scope before path/query/media/body work. Artifact/audit
scopes and wildcard-looking scope strings do not substitute. It admits only the
two exact raw paths and read methods. Alternate escaped, slash-normalized and
per-organization path aliases do not reach a facade.

`/v3/orgs` accepts only optional `limit` and `cursor`. `/v3/projects` additionally
requires exactly one `organization_id`. Query fields are parsed without fetching
a parameter map. Both names and values receive one strict percent/form decode;
invalid or incomplete percent escapes reject explicitly. This matters because a
literal percent can itself be a valid organization ID. Unknown/duplicate/empty
fields, nested names, empty segments, invalid UTF-8 and an over-8192-byte raw
query reject. Encoded-equivalent duplicates remain duplicates. Organization IDs
use the full existing `Scope.identifier?/1`, including Unicode, colon, slash,
dot segments, plus and literal percent. A query value preserves those IDs without
browser path normalization.

An absent limit defaults to 50. Present limits are canonical decimal 1..100,
without signs, whitespace or leading zeros. An absent cursor means the first
page; an empty cursor rejects. Cursors are canonical unpadded base64url, at most
1400 encoded/1024 decoded bytes, containing exact closed duplicate-free JSON.
They bind version 1, collection, and the exact selected organization for projects.
The compact `Jason.OrderedObject` field order is `v,kind,[organization_id],after`,
matching the storage producer's encoder. Re-encoding must reproduce the original
cursor bytes. The cursor remains an untrusted ordering hint; the backend freshly
authorizes every page.

Both operations require an empty body. The reader checks actual streaming bytes,
including when Content-Length claims zero. It uses a cumulative 15-second
monotonic deadline, at most 128 reads, one-byte total admission length, bounded
per-read size and remaining timeout. Read exceptions, throws, errors, deadline
expiry and endless empty `:more` responses fail with bounded errors. Any declared
Content-Encoding, including `identity`, rejects; no decompressor runs. Content-Type
is absent or exactly one `application/json` value.

Success is emitted only after the facade returns its committed page. The
controller validates closed response keys, row count, sorted unique IDs, full
ID validity, exact project organization, nullable printable bounded names,
canonical sorted unique role arrays, and a next cursor matching the final row.
Organization roles may be empty; project roles must be nonempty. Malformed
facade output fails closed instead of exposing internal fields or foreign-tenant
data. Names are returned exactly as stored; the console owns `display_name ?? id`.

The wire success shapes remain:

```json
{"organizations":[{"id":"org","display_name":null,"organization_roles":[]}],"next_cursor":null}
```

```json
{"projects":[{"organization_id":"org","id":"project","display_name":"Actual Project","roles":["billing_manager"]}],"next_cursor":null}
```

Responses have one `Cache-Control: no-store`, a bounded server correlation
`X-Request-ID`, JSON media metadata and the established generic error envelope.
Stale/duplicate challenge, retry, content and cache metadata are removed before
response construction. Expected domain errors retain 400/401/403/404/503 semantics;
unexpected facade return values, exceptions and throws become generic
`503 authorization_unavailable`. Authentication failures retain the bearer plug's
existing challenges. A 503 contains `Retry-After: 1`; other responses do not inherit
retry advice. HEAD follows the same admission and facade path. The Plug adapter
observed empty success/error response bodies, but actual Bandit wire suppression
requires the separate integration lane's receipt.

## Executed evidence

Run only the explicit selected-source collector:

```sh
python3 verification/hosted-customer-workspace-http/run.py \
  --source-revision 6ed7df4f147b3a3254dab91dd3224b9513f586a8
```

Passing **run-3** executed **54/54 tests**: 22 new workspace transport tests and
32 existing artifact transport regressions. Formatting passed, and cold selected
compilation returned no compile or runtime warnings. The executed input-tree
digest is `97b217a0a2813aea94f2739b94b9b94c96e519d0b9bba5a85a285453e27d28be`.
The root-supplied repair revision is context; copied source bytes/per-file hashes
bind the working additions. The pinned dependency BEAM manifest digest is
`e6d69fc2bab11fd5421dfd51fd05eb9de15b2212403a732a9f1d340e8a67e59b`.
No selected source changed during execution. Scratch was removed.

The tests exercise authentication/scope before body or parameter parsing; full
Scope IDs; strict malformed-escape and duplicate-aware query handling; cursor
canonicalization and tenant binding; finite empty-body admission and failures;
closed output, six roles and null names; generic errors and header cleanup;
trusted-only dependency initialization; actual Phoenix fixture route matching;
and production router rejection of missing bearer before any body/facade call.
Existing artifact transport tests verify the pipeline rename preserves their
routes and boundary behavior.

The collector loads only pinned general dependency BEAMs and explicitly named
ordinary identity/transport sources, without the hosted application ebin, a full
app build or shared harness. Its standalone `transport_defaults.ex` declares
unusable default domain facades solely to make the isolated compilation complete.
Tests use the trusted fixture facade; production missing-auth route cases must
never reach those declarations. They are not product implementations or evidence
of real CustomerWorkspace/default-verifier acceptance.

Failed attempts remain intact. **run-1** compiled production sources without
warnings but the collector asserted an older diagnostics return shape instead
of Elixir 1.20's warnings map. **run-2** passed 53/54 tests; its sole failure tried
to decode the correctly empty HEAD body as JSON. Both corrections were confined
to the collector/tests; no product repair was needed. Every attempt removed its
owned scratch and started no socket server, database, native or capture process.

Real PostgreSQL/current workspace policy and RLS, production default-verifier
acceptance, loopback Endpoint/Bandit wire behavior, browser client integration,
audited lifecycle writers, deployed Neon/Cloudflare operation, customer acceptance,
FieldLog published-package consumption and G22/G24 remain separate evidence.
No frozen lane, shared main harness, production publication/migration, credential
change, customer message, signing or store action occurred. Computer use, capture,
native simulator/emulator and physical-device checks remain paused/pending.
