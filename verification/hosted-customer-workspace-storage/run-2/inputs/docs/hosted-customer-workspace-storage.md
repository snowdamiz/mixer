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

Runtime evidence is pending the first successful collector receipt. Production
issuer/SSO, lifecycle writers, deployed Neon/Cloudflare topology and operational
review, customer acceptance and immutable published FieldLog dogfooding remain
pending. Computer use/capture/native simulator/emulator and physical-phone runs
remain paused/pending. This work authorizes no production migration, publication,
customer message or credential change.
