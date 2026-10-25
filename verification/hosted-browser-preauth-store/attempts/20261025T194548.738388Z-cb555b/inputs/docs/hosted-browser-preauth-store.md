# Browser preauthentication storage composition

This bounded slice implements the first real preauthentication database and
Vault roundtrip from the [runtime contract](hosted-browser-lifecycle-runtime-contract.md).
It is being implemented and is not accepted runtime evidence yet. Root owns
metadata, delivery and shared-contract selection. No Application child, route,
provider, active authentication, production migration or native test is enabled.

The proposed source ownership is the new dedicated `LifecycleRepo`, internal
runtime owner, typed preauthentication drafts and fixed `Store.bootstrap/2` and
`Store.load/1` modules. Existing accepted custody, configuration, Vault, decoder,
function/type catalog and relation catalog sources remain unchanged.

The Store must use fixed `LifecycleRepo` and one original five-second monotonic
deadline through checkout, current admission, SQL, decoding and commit. Both
`Catalog.check_function_surface!/4` with fixed integer version 2 and
`RelationCatalog.check_relation_surface!/3` must succeed in the same owned
READ COMMITTED transaction. A partial catalog result cannot establish readiness.
Checkout and queries use `queue: false`, no retry and the remaining positive
budget. Transaction-local limits, JIT, search path and bytea output are checked.
Existing lifecycle/ordinary transactions or authorization context deny.

Bootstrap prepares server randomness, exact preauthentication AAD and ciphertext
before its transaction. Its decoded result must match every prepared source,
counter, deadline and cipher field except SQL-owned fresh timestamps/audit.
Encrypted load completes its transaction before Vault open. The decrypted CSRF,
current configuration, exact cookie digest, caller and owner generation must
still match immediately before private release. Loaded active data never grants
authentication or workspace access in this slice.

The bounded executable tests will use one disposable synthetic local PostgreSQL
instance and the real restricted lifecycle and ordinary roles. They must exercise
actual fixed Repo/pool behavior, transaction ownership, conjunctive admission and
current drift, rollback/deferred errors/commit-boundary failure, deadline
enforcement, source/AEAD comparisons and redaction. The source closure and pinned
dependency BEAMs will be explicit; frozen catalog-inspector, authority-driver and
rejected Worker V2 sources are excluded. Every run records commands, versions,
revision, tree hashes, output and cleanup, including failed attempts.

Production Neon/TLS and external custody-source qualification, shared startup,
provider/OIDC/current verifier, browser HTTP/console, device, customer, immutable
FieldLog and GA evidence remain pending. Native/UI/capture execution is paused.
