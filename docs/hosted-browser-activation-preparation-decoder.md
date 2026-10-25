# Activation-preparation projection decoder

`MixerHosted.BrowserAuth.ActivationPreparation.decode/1` is the pure shape
prerequisite for the proposed additive activation-preparation projection in the
[lifecycle runtime contract](hosted-browser-lifecycle-runtime-contract.md). It
accepts a map with exactly these six string keys:

```text
version = integer 1
snapshot = existing StoredSnapshot JSONB shape
principal_id = valid UTF-8 text, 1..128 bytes, no NUL
profile_revision = integer 1..9007199254740991
binding_revision = integer 1..9007199254740991
principal_revision = integer 1..9007199254740991
```

The decoder delegates the entire nested snapshot to the existing ordinary
`StoredSnapshot.decode/1`, requires an actual attempt with status `claimed` and
its erased attempt ciphertext (`attempt_envelope: nil`), and retains the complete
decoded snapshot. It accepts either existing live browser kind supported by that
decoder. The returned `%ActivationPreparation{}` contains exactly the six typed
fields above and has redacted `Inspect`. Missing, extra, atom-alias, structural,
type, bound, nested-linkage or claim-state errors return only
`{:error, :session_unavailable}`. The input is a decoded map; duplicate JSON key
handling belongs to a later transport/JSON boundary.

Text semantics match the ordinary snapshot decoder: the bound counts UTF-8 bytes,
NUL and invalid UTF-8 deny, and no normalization or trimming is applied. Every
revision is checked independently as a positive safe53 integer; a float or numeric
string is unavailable. No profile version is substituted for a database revision.

Success proves shape only. It grants no authentication, authorization, database
provenance, freshness, current configuration, verified access identity or retained
claim binding. An incoming provisional principal can differ from the old active
browser principal. Changing a shape-valid provisional principal or revision does
not establish any permission. The contract's later owner-binding prose describes
a separate pending trusted owner responsibility; this one-argument decoder has no
owner-retained identity, claim or configuration against which to compare.

The future trusted ClaimOwner and separately reviewed database/helper/catalog
work must establish and compare those bindings, current verifier evidence and
transaction/time fences. No additive SQL type/helper, migration, catalog change,
database caller, application startup, HTTP route or readiness switch is included.
`StorageSchema` is unchanged. This decoder calls the existing snapshot/Vault
context validator and introduces no cipher, AAD, custody or decryption path.

Run the focused host checks with:

```sh
python3 verification/hosted-browser-activation-preparation-decoder/run.py
```

The runner compiles only actual ordinary `Vault`, `StoredSnapshot` and
`ActivationPreparation` source with standalone `elixirc --warnings-as-errors`.
It executes the new preparation suite plus the existing snapshot regression suite
with synthetic fixtures and the existing OTP AES-GCM implementation. It requires
no third-party dependency BEAMs and does not build or start the hosted application.
It records exact commands, tool versions, source revision, file and tree hashes,
output, result counts and owned scratch cleanup in timestamped attempt receipts.
It never imports or executes the frozen catalog/authority lanes or rejected
Worker V2.

The cases exercise exact map envelopes; version, byte and safe53 bounds;
UTF-8/NUL; nested disagreements; valid absent/pending/rejected/completed attempts;
claim erasure; malformed session ciphertext; redacted inspection and errors; and
the explicit absence of authentication, freshness and owner binding. Passing
checks are selected host shape evidence. Actual SQL composition, additive schema
and catalog admission, trusted owner/configuration/access binding, runtime
transactions, provider/OIDC/custody qualification, HTTP/console integration and
deployment remain pending. Native simulator/emulator, capture, UI automation and
physical-phone checks remain paused and unrun. No GA gate is promoted.
