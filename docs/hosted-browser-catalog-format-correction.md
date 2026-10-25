# Browser catalog formatting correction

Phoenix CI `40219535335` for `9d5c40ee` passed the selected browser storage and
migration step, then stopped at `mix format --check-formatted` before the broader
host suite. The retained format log identifies only the final extra newline in
`catalog.ex` and `catalog_manifest.ex`. Earlier source-format equality and the
root whitespace exception did not satisfy the actual Mix formatter.

Root ran the actual Mix formatter on three explicit copies in a projectless
temporary directory. Its before-check reproduced the failure; the after-check
passed. Each product file and the producer's selected test file lost exactly one
terminal LF byte. Every preceding byte is unchanged. No application, broad
hosted harness or frozen source was loaded by the formatter.

The corrected bytes pass the existing 26-method PostgreSQL 17.11 producer suite
and 20-method independent PostgreSQL 16.15 suite, replayed by root. Source,
dependency and output bindings were checked again, and both owned databases and
scratch were removed. Historical reviewed hashes and failures remain unchanged;
the [correction receipt](../verification/hosted-browser-catalog-format-correction/receipt.json)
binds the current bytes and both new attempts.

This retains the same partial function/type prerequisite scope. Full relation,
policy and writer-grant admission, trusted Store ownership, readiness, provider,
customer and GA requirements remain pending. Fresh exact-push CI is required.
