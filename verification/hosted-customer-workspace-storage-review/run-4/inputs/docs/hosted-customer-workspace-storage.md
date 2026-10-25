# Customer workspace discovery storage

`MixerHosted.CustomerWorkspace.organizations/2` and `projects/3` own fresh,
bounded read-only PostgreSQL transactions. Optional final Repo arguments are
trusted server/test seams. No caller callback, request-selected dependency,
artifact Decision or authorization Context is accepted.

The coordinated public contract is
[`hosted-customer-workspace-contract.md`](hosted-customer-workspace-contract.md).
The additive migration stores nullable real names, gates existing scoped SELECT
policies to the empty ordinary mode, and adds explicit SELECT-only directory
policies requiring the human identity chain, current token/credential/family
windows and exact directory action/scope/phase/settings. Existing mutation and
artifact action ceilings are unchanged. Names receive printable UTF-8 validation
on reads; historical nulls are returned as null.

Each page selects at most limit+1 resources. At most one deterministic live
membership per role supplies role summaries. Organization visibility falls back
to one exact-project witness when there is no organization-scoped witness.
Selected organization heads and then project/witness heads are shared locked in
byte order. Temporary exact target lock settings always restore the intended
directory context. Frozen selected witnesses and resources are re-read after the
last lock wait; changed/missing/expired witnesses fail closed without replacement
or retries. Fresh identity and time checks and complete backend/transaction/GUC
equality precede the actual owning commit. Only commit success returns a page.

The writer serialization protocol in the contract remains a dependency, not an
implemented lifecycle/provisioning writer. Pages are weakly consistent across
requests and cursors are ordering hints. LIMIT bounds materialized candidates
and lock counts, not all internal PostgreSQL scan work. Finite SQL/lock/transaction
deadlines bound the fixed local reads.

The selected ordinary-source collector is
`verification/hosted-customer-workspace-storage/run.py`. It compiles only its
explicit sources against already pinned general-purpose dependency BEAMs and
runs the focused suite on a disposable loopback PostgreSQL database with separate
nonlogin owner and unprivileged runtime. It never imports the shared collector,
loads frozen lanes, starts the application, or starts native/capture processes.
Every attempt preserves input hashes, output, tool versions and cleanup.

Observed evidence is in `verification/hosted-customer-workspace-storage/run-10/`:
24 host PostgreSQL tests passed, including all 18 role/binding combinations,
identity revoke fences, foreign/inactive scope behavior, strict canonical pages,
full Scope IDs, real/null/malformed names, directory RLS, forbidden runtime grants,
selected project/organization revocation across lock waits, frozen witness loss,
membership expiry during a lock wait, token expiry during finalization, and
final-context corruption. A 121-membership customer exercises the 100-row page
and authorized lookahead without a global membership cap. A revoker waits behind
an already selected reader until commit. The actual COMMIT failure test inserts
duplicate values into a test-only deferred-constraint probe after the production
read function returns; PostgreSQL rejects COMMIT and the facade exposes no page.
The expected Postgrex unique-constraint error is preserved in the test log.
Migration apply/rollback/reapply and owned database/scratch cleanup were observed.
Earlier failed attempts remain preserved. The ordinary empty-mode regression
checks organization/project/application/environment ancestry under the new
migration, including organization-only owner denial. Name tests cover the exact
256-byte multibyte boundary. The collector asserts exactly 24 tests and zero
failures, skips or exclusions. Tools were Elixir 1.20.4 / Erlang OTP 29 and
PostgreSQL 17.11 on this macOS host. Already-pinned dependency BEAMs and the
copied mix.lock are hashed in each receipt; no new dependency was introduced.

These synthetic fixture tests do not establish deployed database security or an
audited controlled-writer implementation. Production issuer/SSO, lifecycle
writers, deployed Neon/Cloudflare topology and operational
review, customer acceptance and immutable published FieldLog dogfooding remain
pending. Computer use/capture/native simulator/emulator and physical-phone runs
remain paused/pending. This work authorizes no production migration, publication,
customer message or credential change.
