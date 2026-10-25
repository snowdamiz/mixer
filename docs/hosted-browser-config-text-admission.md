# Trusted browser configuration text admission

`BrowserAuth.Config.load/3` now rejects NUL in the three trust-matched UTF-8
metadata fields: `profile_id` (1–128 bytes), `client_id` (1–256 bytes), and
`api_audience` (1–256 bytes). It checks their existing byte bounds and UTF-8
validity explicitly before constructing a configured value or matching the
active human identity. Failure remains `{:error, :invalid_configuration}`.
The matching identity is still required; this check grants no identity authority.

This closes the specific admission gap recorded in
[the independent Vault/digest review](browser-vault-digest-review.md): the
general identity Manifest permits bounded UTF-8 strings containing NUL. It is
unchanged because this slice owns browser configuration admission, not the
general identity contract. The new tests supply matching Manifest entries and
first confirm that the Manifest admits them, so browser denial cannot result
merely from a mismatched trust value.

| Current text boundary | Prior NUL behavior | Browser Config behavior |
| --- | --- | --- |
| `profile_id` | Matched Manifest metadata admitted NUL; used by browser session/attempt SQL text and Vault context. | Explicitly rejects NUL. |
| `client_id` | Matched Manifest metadata admitted NUL; used by attempt SQL text and Vault context. | Explicitly rejects NUL. |
| `api_audience` | Matched Manifest metadata admitted NUL; configuration/trust metadata, not a raw browser-attempt SQL/Vault field. | Explicitly rejects NUL at the same trusted metadata boundary. |
| `issuer`, `redirect_uri` | Attempt SQL/Vault text already constrained by canonical URL/exact redirect validation. | Existing NUL rejection retained. |
| Other URL/reference/fixed text settings | Existing narrow syntax or exact policy values already rejected NUL. | Existing rejection retained. |

No normalization, trimming, ASCII-only metadata policy, or rejection of other
previously valid control bytes is introduced. Composed and decomposed Unicode
remain distinct exact strings. ASCII and multibyte metadata at each byte limit
remain accepted; empty, over-limit and malformed UTF-8 values deny. The closed
17-field JSON schema, fixed policy, 16,384-byte whole-input bound and identity
matching remain in force.

`ConfigurationDigest` source and its versioned 21-field serialization are
unchanged. Its API still requires a trusted constructor-validated Config; it is
not a constructor-provenance validator. The selected test pins the valid
baseline's 910 exact bytes to SHA-256
`3116d5ef6ac718b3d2442df3648c60ab3fa1d640f73d429ed2b30490f1e2d7f3`.
A separate Python standard-library fixed-order JSON/SHA-256 vector verifies
that baseline without importing product code. Existing Unicode and field-boundary
digest controls remain in the selected suite. Vault and StoredSnapshot retain
their own NUL rejection and were not edited by this slice.

Run `python3 verification/hosted-browser-config-text-admission/run.py`. The
runner compiles only Config, unchanged ConfigurationDigest and their four
existing identity helper modules with warnings as errors, then runs the two
selected ExUnit files using the existing pinned Jason BEAMs. Its receipt binds
the selected input/dependency hashes before and after verification, source
revision/tree digest, command arguments, tool/backend versions, complete output
and output hashes, and owned temporary compiler-directory cleanup. It starts
no shared application, database, provider/network request, browser, capture,
native simulator/emulator or phone process. Other projects' processes and data
are preserved. The broad hosted harness and frozen hosted lanes are not used.
The selected suite passes 26 methods with zero failures, exclusions or skips;
the separate Python digest vector and warnings-as-errors compilation pass.

This is a host component correction pending independent review and root
integration acceptance. Trusted runtime configuration provenance, reviewed SQL
lifecycle joining, provider exchange/OIDC validation, key custody, startup and
HTTP/console composition, deployment and customer qualification remain pending.
Native/physical-device checks remain paused and all GA requirements remain
pending. No route, credential, migration, deployment or external publication is
enabled by this slice.
