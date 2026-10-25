# Browser lifecycle snapshot decoder

`MixerHosted.BrowserAuth.StoredSnapshot.decode/1` accepts the exact public JSONB
snapshot from the ordinary lifecycle helpers. It validates closed keys, canonical
lowercase PostgreSQL hex bytea, bounded integer/text fields, browser/vault/attempt
linkage and state-specific ciphertext erasure. It derives the exact contexts
consumed by the independently reviewed AES-GCM vault. Unknown fields, versions,
terminal snapshots and null/missing results fail with `:snapshot_unavailable`.

The result contains normalized browser and attempt metadata plus a session
envelope and, only while pending, an attempt envelope. Both result structures
redact Inspect. No dynamic atom creation, network operation, database access,
key lookup, plaintext logging or authentication occurs in this decoder.

The public SQL functions return live `preauth` or `active` browser rows. A load
can return a pending attempt or none. Claim and provider rejection return their
consumed metadata; activation returns completed metadata with the prior begin
epoch/revision/cookie/generation and the newly rotated browser/vault. The decoder
rejects stale attempts, crossed browser/configuration/profile identifiers,
mixed identity linkage, retained consumed ciphertext and malformed claim bounds.
It does not decode the private SQL snapshot helper's terminal/erased rows.

The lifecycle owner must open the pending verifier before claiming, retain it
only in memory, and use it only after a successful atomic claim. Claim erases
durable verifier ciphertext. The consumed snapshot cannot recover that verifier.
An abandoned successful claim fails closed and requires a new login attempt.

This is a data adapter, not authority. A decoded result may be historical or
forged. The owner must first admit the exact reviewed database helper ownership,
body, grants and RLS topology; bind its cookie/configuration/revision to the
request; authenticate ciphertext; apply fresh time checks; use the current
identity verifier; and commit lifecycle changes atomically. Provider trust,
OIDC validation, credentials, runtime topology and the HTTP/console integration
remain separate requirements. No login route or readiness flag is enabled.

The selected host runner is
`python3 verification/hosted-browser-stored-snapshot/run.py`. It compiles only
Vault and StoredSnapshot. Its tests exercise real platform encryption/decryption,
cross-row rejection, closed fields/types, byte bounds, consumed-state handling
and explicit acceptance of structurally valid but unauthenticated ciphertext
followed by cryptographic rejection. Actual SQL output composition, provider,
browser, deployment and GA checks remain pending until separately evidenced.
