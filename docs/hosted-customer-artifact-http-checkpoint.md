# Customer artifact HTTP checkpoint

The ordinary Phoenix endpoint now accepts protected artifact uploads, exact-byte
private reads and bounded audit pages using the existing v3 resource paths.
HEAD performs the same admission and authorization as GET and returns no body.
The SolidJS console retains the website logo, palette and typography; connecting
these APIs to live customer sessions and workflows remains separate work.

Uploads bind the requested digest to the admitted signed manifest before opening
the authorization transaction. Authentication and exact action scope precede
body reads. The transport rejects duplicate metadata, unknown query fields,
encoded or extra-slash path aliases, unsupported encodings and oversized bodies.
Current membership, tenant visibility, revocation and principal-bound retries
remain enforced inside the existing transaction-owned facade.

Independent review found that Phoenix normalized noncanonical raw paths into
valid route parameters. Both an independent Router probe and a real socket test
reproduced acceptance, including an upload that committed. The repair compares
the raw path with its canonical form after authentication/scope and before body
reads or facade calls. The original failing results remain preserved. Uniform
`400 invalid_path` matches the encoded-path Go rejection; Phoenix-routed extra
slashes may differ from Go's route-miss status. Other documented signed-shape,
authorization and schema-2 audit differences remain explicit migration work.

Accepted local evidence:

| Layer | Result | Scope |
| --- | --- | --- |
| Digest-bound facade | 18 producer and 25 combined independent methods | Actual local PostgreSQL; mismatches cannot reach storage or reuse a cached receipt |
| Transport | 32 producer and 46 combined independent methods | Public Plug/Router controls, with fixture identity/facade where recorded |
| Endpoint integration | 8 methods, 47 real HTTP requests; zero skips | Actual Endpoint, Bandit, default bearer verifier, synthetic TLS/JWKS, and restricted PostgreSQL role |
| Root binding audit | 244 retained files and 56 current product inputs | Exact tested source, command outputs, dependencies, cleanup and shared source consistency |

These counts overlap. The integration includes three empty-wire HEAD responses,
three encoded-path rejections, cold RS256 verification with one TLS JWKS fetch,
and an injected database failure after all four local writes and deferred checks.
That failure returns 503, commits no rows, and permits a later authorized retry.
It does not simulate every ambiguous commit outcome. All owned listeners, key
workers, database clusters and scratch directories were stopped or removed.

The ordinary shared fixture helper supplies the HTTP test database through one
new tuple; only that named helper was extracted and executed locally. The test
uses the ordinary `test_helper.exs`. No shared harness main, frozen authority/
inspector lane, rejected Worker transport, native runtime or capture was used.
All 32 website/console brand bindings and 132 VM bindings remain unchanged.

See [the HTTP contract](hosted-customer-artifact-http-contract.md),
[the independent review](hosted-customer-artifact-http-review.md),
[the real integration](hosted-customer-artifact-http-integration.md), and
[root acceptance](../verification/hosted-customer-artifact-http-root-acceptance/attempt-2/acceptance.json).
Three separately passing Go reference methods are recorded under
`verification/hosted-customer-http-go-reference/`; they are not a paired full
Phoenix/Go equivalence test.

This checkpoint does not qualify a production identity provider, public DNS,
Neon TLS, Cloudflare, R2/CDN, live console workflows, or deployment. One configured
host/trust snapshot remains; tenant trust/lifecycle writers, distributed admission
limits, legacy audit migration and full API/CLI/console parity remain pending.
No native, store, published-package FieldLog or GA gate is promoted. Exact-push
CI is recorded separately from these local receipts.
