# Typed callback storage prerequisite

This Unit A candidate adds private `CallbackDraft.Discovery`, `Claim`, `Reject`
and fixed `Store.discover_callback/1`, `claim/2`, `provider_reject/2` operations.
Producer execution and independent acceptance are pending. No callback facade,
Claim owner, provider, HTTP route or authenticated browser is enabled.

Discovery commits an encrypted, live non-null PREAUTH pending source before any
Vault opening. Claim authenticates canonical recovered CSRF against the saved
digest and opens the exact verifier outside its mutation transaction. Rejection
authenticates the session without opening the verifier. Both recheck current
function/relation catalogs and fixed-load the whole source under the browser
SHARE lock before unchanged mutation SQL. Every output field is compared before
COMMIT. Browser audit alone increments; all other browser/session fields remain
identical. Only the specified terminal attempt fields change and its cipher is
erased. Claim expiry is fixed from original entry plus 60 and saved deadlines.

Each new Store operation owns one synchronous closed `{:failed, lease, error}`
report to the retained RuntimeOwner as its actual original caller, within the
original deadline. This releases that exact slot on acknowledgment and clears
readiness for unknown outcomes or entered admission failures. Future Unit B must
not assume the lease survives an error or give reporting another timeout.
Foreign/altered leases cannot release another slot. No acknowledgment implies no
readiness assertion; original expiry/monitor cleanup remains the bound. Successful
discovery retains the original slot for mutation. Success returns only a private
StoredSnapshot and grants no Claim authority or automatic replay.

Reproduce the selected projectless closure with
`python3 -B verification/hosted-browser-callback-storage/run.py`. Its explicit
synthetic localhost PostgreSQL 17 roles and manually assembled RuntimeConfig
are component fixtures, not Neon/TLS, Application or custody qualification. The
accepted default KeyOwner starts without provider work. No broad hosted harness,
frozen catalog-inspector/authority-driver/rejected Worker V2, injected verifier,
native runtime, UI, capture or unrelated process discovery is used. Selected
source/dependency hashes, commands/versions, failures, outputs and exact owned
resource cleanup are preserved per attempt. Native/phone and external published
FieldLog/customer/GA evidence remains pending.
