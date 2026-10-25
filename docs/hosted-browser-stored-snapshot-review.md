# Independent stored-snapshot decoder review

This bounded review checks the frozen `StoredSnapshot` data decoder against the
ordinary SQL public row shape and independently constructed encrypted records.
The current [receipt](../verification/hosted-browser-stored-snapshot-review/receipt.json)
records exact source hashes, revision/tree digest, commands, tool/backend versions,
stdout/stderr hashes, failures and owned temporary-build cleanup. The runner pins
the coordinated Vault, decoder and producer-test source hashes. This report is
bound by `review_report_sha256` in the receipt.

Run `python3 verification/hosted-browser-stored-snapshot-review/run.py`. Only Vault
and StoredSnapshot are compiled. SQL is read as text: a balanced-clause parser
extracts actual table columns and compares them to a separately declared review
contract (22 browser, 10 vault, 26 attempt fields). The SQL snapshot helper uses
`to_jsonb` of those row types under exactly `browser`, `vault` and `attempt` keys.
This shape check is not SQL execution, catalog admission or a review of the SQL
lifecycle/security implementation. That separate SQL lane remains unreviewed.

The selected independent probes cover all nine documented live result variants:
preauth/active with no attempt, pending, claimed or provider-rejected metadata,
and active with completed metadata. Each context is constructed before calling
the decoder, compared in full to the decoded context, and used to open real Vault
encryption. Completed metadata retains the old begin context and requires the
new browser epoch/revision/cookie/generation. Pending verifier custody opens under
its saved context; consumed verifier ciphertext must be explicitly nil.

Adversarial probes cover missing/extra/null/wrong-key-type objects in every state,
all returned bytea widths and canonical lowercase hex, ciphertext bounds, crossed
browser/profile/config/epoch/revision linkage, mixed active/preauth fields,
unsupported versions/states, claim bounds, consumed-state erasure, metadata
types/text bounds/time ordering, every trailing Base64URL character, fixed public
errors and redacted Inspect. Structurally valid corrupted ciphertext decodes and
then fails Vault authentication, demonstrating the data-only boundary. Historical
timestamps, bounded operator text and a distinct initial-configuration digest are
not authentication or provenance evidence.

The decoder accepts only canonical lowercase PostgreSQL hex bytea. The SQL source
now pins `SET bytea_output='hex'` and records that setting in its catalog manifest.
Actual SQL result composition and runtime setting qualification were not performed
by this independent review. The separate SQL producer's reported hostile-setting
roundtrip remains outside this review's evidence. No live database or network
process was started here.

Documentation-only postrun correction: the preceding paragraph was updated after
the selected host run to acknowledge the SQL source pin. The bound report hash
was refreshed with an amendment record; tests were not rerun, producer files were
not edited, and the original command results/source bindings remain unchanged.

The earlier Vault/configuration-digest evidence is unchanged. No producer source
was edited. The reviewer started no shared application, provider/network/database,
browser, screen capture, native UI, simulator/emulator or phone process. Its
owned compiler/BEAM temporary directory is removed after success or failure;
other projects' processes and data are preserved. The frozen catalog-inspector,
authority-driver and rejected Worker transportV2 lanes were not read, imported,
compiled or executed.

Successful decode does not establish database provenance, freshness, key trust,
request/cookie/config admission, one-use claim, current identity/OIDC verification
or authorization. Trusted lifecycle ownership, transaction joining/fencing,
external key custody, provider exchange, application/HTTP/console integration,
browser/deployment/security qualification, paused native/physical-device checks,
customer and GA acceptance remain pending. This review is a pausing point for a
pure data-adapter development slice only.
