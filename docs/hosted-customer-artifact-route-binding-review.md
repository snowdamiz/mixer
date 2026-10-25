# Independent digest-addressed upload review

The additive `CustomerArtifacts.upload_at/6` change is accepted for its bounded
application-facade scope. No actionable defect was found. This is not HTTP,
identity-provider, deployed-service, native or GA acceptance.

The review inspected the actual ordinary facade and its three new producer
tests. The facade always wraps caller input as `{:at, expected_digest}`; the
private `:any` path is selected only by the existing `upload/5` entry point.
Invalid expected values cannot select that unrestricted path. Expected-digest
syntax validation occurs before configuration/body admission. With a valid
expected digest, the existing identity/time/class check and exact
`mixer.artifact.upload` scope check precede signed-byte admission. The route
project, metadata and idempotency key are also checked before admission.

The admitted manifest digest is compared at the last `with` clause before
`Authorization.with_authorized_transaction/5` is invoked. Therefore a mismatch
cannot reach a Repo transaction, domain write, commit or same-key receipt
lookup. A valid expected digest and valid signed bytes must both exist before
that transaction boundary. Authoritative current database membership and policy
still run inside the existing protected transaction after signed admission;
the earlier pure identity/scope checks do not substitute for them.

`upload_at/6` returns `:digest_mismatch` for valid signed bytes at a different
route digest, and `:artifact_invalid` for rejected signed admission. These are
the typed values that the separate HTTP adapter will map to 422; this review
does not exercise that HTTP mapping. A bad signature takes the admission-error
path even if the route digest also differs. The original `upload/5` retains
`:invalid_request` for rejected admission and its existing receipt semantics.

## Independent executable evidence

The review collector selects the same ordinary source/migration dependencies as
the producer, copies them into a fresh owned evidence tree and compiles the
selected product modules with `elixirc --warnings-as-errors`. It preserves the
original test source, then creates a separately hashed combined test file from
that source plus seven independently authored test groups and an instrumented
Repo. It never edits product source or the producer packet.

The instrumented Repo reports calls to `in_transaction?/0`, `transaction/2` and
`rollback/1`. A matching signed digest reaches the first two, establishing the
positive control. A mismatched digest, structured/malformed expected input,
rejected identity/scope or foreign route does not call any of them. Tests use
actual signed fixture bytes rather than treating a forgeable Checked struct as
admission authority.

Seven independent groups exercise:

1. A route mismatch stops before every instrumented Repo boundary, while a
   matching digest reaches the positive control.
2. `:any`, nested `{:at, digest}`, maps, tuples, charlists, numeric/boolean values,
   non-UTF-8 bytes and malformed textual digests cannot select an unrestricted
   upload or open a transaction.
3. Missing/expired/future-issued identities, a service identity class, read-only
   scope, scope suffixes and wrong-case scopes reject before invalid-body
   classification and Repo calls.
4. Foreign organization/project routes reject before body classification and
   Repo calls.
5. A real corrupted 64-byte signature yields `:artifact_invalid` with either a
   matching or mismatched route digest; `upload/5` retains `:invalid_request`.
6. A committed same-key success cannot rescue invalid signature bytes, a
   structured expected value or a mismatched route digest. Actual PostgreSQL
   artifact/event/idempotency counts and the project sequence remain unchanged.
7. An authorized `upload/5` receipt can be retried through matching `upload_at/6`
   without an extra event, and a later new-key `upload/5` retains unchanged-content
   status 200 and the next event sequence.

The fresh run passes **25 methods: 18 producer/original methods plus seven new
independent groups**. It uses PostgreSQL 17.11 on loopback, Elixir 1.20.4 and
Erlang/OTP 29 on macOS. Synthetic owner/runtime roles and their isolated database
are provisioned only within the collector's disposable cluster. The cluster is
stopped and its scratch directory removed after evidence collection.

Run from the repository root:

```text
python3 verification/hosted-customer-artifact-route-binding-review/run.py --output verification/hosted-customer-artifact-route-binding-review/run-1 --source-revision c4e1f5717c9d912ffa5b18942d088078b0c766f7
```

The retained run exists already; subsequent executions require a new output
directory. The source revision is provenance only: immutable copied source
hashes bind the actual uncommitted candidate. The review source-tree digest is
`3200f292fec3ead3d94e724b19cda0d5cc6c53f4bfed65f4b33a78f406205465`.

[Run receipt](../verification/hosted-customer-artifact-route-binding-review/run-1/receipt.json)
records exact argv, versions, input/dependency/output hashes and cleanup.
[Independent binding audit](../verification/hosted-customer-artifact-route-binding-review/binding-audit.json)
confirms all 24 selected product/migration/original-test files match the producer
packet, all copied inputs still match current sources, all recorded output hashes
match, and the generated combined test hash matches its receipt. There were no
live source changes during the run. Original receipt/logs are preserved.

This result adds application-level route binding and retry/admission evidence.
It does not independently repeat HTTP/HEAD/body parsing, default identity-owner,
socket delivery, upstream provider, arbitrary commit-failure, deployment, R2/CDN,
multi-tenant trust lifecycle, operational, physical-device or separate-repository
FieldLog qualification. No frozen catalog/authority/rejected Worker lane, shared
harness main, UI, screenshot or native runtime is used. No production action or
Git/plan/tracker modification is part of this review.
