# Browser configuration digest

`BrowserAuth.ConfigurationDigest` derives the raw 32-byte configuration fence
used by durable browser sessions, OIDC attempts and encrypted custody. It accepts
only the current configured `Config` shape and fixed policy. Disabled mode,
missing/unknown fields, malformed bounded scalars and unsupported future policy
choices return one fixed error. It does not validate a provider or establish
trust: the caller must first use `Config.load` with the current configured
identity owner.

The version-one input is the ASCII domain `mixer.browser.configuration.v1`
followed by NUL and UTF-8 JSON `[1, pairs]`. `pairs` is the explicitly ordered
array of all 21 configuration field names and scalar values declared in the
module. Mode and client-auth atoms become their fixed strings. Integer and
boolean types remain distinct. No map iteration order, normalization or delimiter
concatenation determines identity. SHA-256 uses OTP `:crypto`.

Every endpoint, origin, exact profile/version/issuer/client/audience, secret/key
reference and fixed cookie/session flow policy participates. Actual credential
and encryption-key values cannot be fields in the accepted Config shape. A
secret-reference version change changes this digest; rotation under an unchanged
reference needs an independently qualified key-version policy. This digest alone
does not revoke sessions or fence an in-flight operation: SQL admission must
compare it atomically, and AEAD must bind it to the record context.

Run `python3 verification/hosted-browser-configuration-digest/run.py` for selected
Config and configuration-digest host checks. This compiles six explicitly named
ordinary modules with the pinned Jason dependency, not the shared hosted app.
Receipts record exact inputs, commands, tools, outputs and temporary-build cleanup.
Provider I/O, session owner/storage integration and deployment remain pending.
No browser, native runtime, capture, physical device or production key is used.
