# Independent customer artifact HTTP review

The corrected candidate is accepted for the bounded public Plug transport and
router scope: **46 methods pass, including 14 independent control groups**, with
no remaining actionable finding. The original P2 path-normalization defect is
reproduced, preserved and repaired. This is not deployed-service or GA
qualification.

## Finding and coordinated contract addendum

`CustomerArtifactRequest` originally validated only Phoenix's decoded
`path_params`. Actual `MixerHostedWeb.Router.call/2` prepares these five requests
as the same canonical upload target:

- An encoded static version segment, `/%763/orgs/...`.
- Organization `org%2Da` in place of `org-a`.
- Project `project%2Da` in place of `project-a`.
- Digest bytes encoded as repeated `%61` in place of `a`.
- An internal repeated slash before `projects`.

The independent test obtains those parameters from the actual production router
under missing-credential denial, then invokes the public bearer/controller
composition with that same raw path and those actual prepared parameters using
a trusted fixture identity/facade. All five originally return 201 and invoke the
fixture mutation. This is not a claimed credential or cross-tenant bypass. It
demonstrates that the raw request path is not bound to its canonical operation
before effects. The original run is retained with 41 of 42 methods passing.

Root and the producer coordinated an additive canonical-path requirement:
after identity/action-scope admission and decoded route bounds, compare
`conn.request_path` exactly with the reconstructed operation-specific route.
Reject a mismatch with **400 `invalid_path` before query/body work or facade
dispatch**. Apply the rule to upload, read and audit. Encoded static segments,
encoded identifiers/digests and normalized repeated/trailing slashes cannot
select an alternate route spelling. This addendum leaves the previously sealed
contract and original receipts intact.

The error code matches Go's rejection of a nonempty encoded `URL.RawPath`.
Phoenix-routed repeated/trailing slash aliases uniformly become 400
`invalid_path`; Go can instead return a route-miss 404 for additional internal
segments, and it trims outer slashes. That precise normalization/status
difference is intentional and must not be called complete wire equivalence.

## Independent controls and evidence boundaries

The collector copies an explicit allowlist of 25 ordinary product modules,
pinned dependency version records, the original producer test and independently
authored review tests. It starts Phoenix dependencies and compiles only that
selection in an isolated Elixir process; it never loads the application ebin,
the full application, a recursive source collector or the shared harness main.
The runner records the actual source revision, copied source/tree hashes,
dependency BEAM hashes, tool versions, command/output hashes, source/dependency
stability and removal of owned temporary scratch.

Independent control groups exercise:

- Credential and exact action-scope rejection before even a throwing body reader;
  encoded alternative credential names also reject before verifier/body work.
- Escaped duplicate keys, nested duplicate aliases, alternate top-level names,
  unknown envelope fields, encoding declarations and duplicate media headers.
- Encoded query duplicates, double-decode aliases, bracket/unknown query names,
  decimal overflow, and Go-compatible absent-or-empty page defaults.
- A fixed total read deadline that decreases across chunks and rejects bytes
  arriving at the deadline; cumulative maximum/overflow even when an adapter
  returns more than its requested chunk length.
- Nonempty GET bodies despite Content-Length zero; body-reader and clock
  exceptions/throws remain generic failures.
- All three operations preserve unavailable/uncertain facade results and
  exceptions/throws as 503 errors instead of successful HTTP responses. These
  are injected facade failures, not independent real database commit failures.
- Unique no-store/JSON/challenge/retry/request-ID response metadata on success
  and failure, incomplete/unknown trusted initialization dependencies, and
  ignored asserted actor/trust/facade/IP headers.
- Actual production router parameter preparation and method selection, including
  the noncanonical path finding and read/audit regressions for its repair.

The verifier and facade in these controls are trusted, explicitly initialized
fixtures. They do not establish the default ConfiguredVerifier, cold identity
owner, provider login, real signature admission, actual PostgreSQL effects,
socket transport, or real HTTP HEAD body suppression. The separate integration
lane owns those observations. Parsing success cannot authorize publication or
replace domain authorization. Rate/tenant admission controls, service/CI
principals, Neon/R2/CDN, operations, deployment, native/physical verification and
published separate-repository FieldLog remain separate product gates.

## Retained runs

The original [run-1 receipt](../verification/hosted-customer-artifact-http-review/run-1/receipt.json)
and [output](../verification/hosted-customer-artifact-http-review/run-1/output.txt)
retain the exact initial failure. It passes all 29 producer methods plus 12 of
13 independent groups. The five alias observations all report 201. Its source
tree digest is
`d81a54045be58f77fbc4e3812f3bf0932b594096a901e02bd5c5ecc7f8821487`.
[Initial binding audit](../verification/hosted-customer-artifact-http-review/initial-binding-audit.json)
confirms all 25 product inputs exactly match producer run-3, current copied
inputs and recorded outputs match, dependencies/source stayed stable, and owned
scratch was removed. The source revision is
`c4e1f5717c9d912ffa5b18942d088078b0c766f7`; source hashes bind the actual uncommitted
candidate rather than claiming HEAD contains all changes.

The corrected [run-2 receipt](../verification/hosted-customer-artifact-http-review/run-2/receipt.json)
and [output](../verification/hosted-customer-artifact-http-review/run-2/output.txt)
pass **all 46 methods: 32 producer methods plus 14 independent groups**. The five
original upload aliases now each return 400 `invalid_path`, without body-reader
or facade calls. A new independent group also obtains actual production-router
parameters for read/audit encoded or repeated/trailing-slash aliases, verifies
the same early 400 error, and exercises unsupported actual-router methods and
extra path segments. Producer tests also run their trusted fixture router
through upload/read/audit path normalization controls.

The final review uses Elixir 1.20.4, Erlang/OTP 29 and Python 3.14.8, with 15
runtime dependency versions checked against the lock and dependency BEAM hashes
retained. Its source tree digest is
`c3dd073e720ebabfbd0233fc24f6f7d60da2f1343718490b3369de0c70e4bbcf`.
[Final binding audit](../verification/hosted-customer-artifact-http-review/final-binding-audit.json)
confirms all 25 selected product modules plus the original test and lock exactly
match producer run-5, every current/copied input and recorded output matches,
the dependency manifest matches, and source/dependency bytes stayed unchanged
during the run. Owned temporary scratch was removed. The corrected Request
module SHA-256 is
`40b39e38f8c3ecdcb36ba006ee0517303a690246c029d1cc6d42b00a5fbf9a1b`.

Counts from original and corrected attempts overlap and are not additive.
Original review run-1 and producer failures remain retained. The producer's
run-4 fixture-clock compilation failure is not a passing attempt; the final
bindings target its successful run-5.

Run fresh review attempts from the repository root with:

```text
python3 verification/hosted-customer-artifact-http-review/run.py
```

It selects a new `run-N` directory and preserves earlier failures. This review
does not modify product source, prior sealed packets, Git, plan/status trackers,
external providers, native instances or production state. No frozen
catalog/authority/rejected Worker lane, browser, UI or screen capture is used.
