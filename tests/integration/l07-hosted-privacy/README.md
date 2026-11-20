# Replay hosted privacy checks for L07

Run both profiles against the pinned Phoenix source and disposable loopback
PostgreSQL. The source pin is `e326ce2041d8b2176b2086b2f59cd6cde6d97e56`, the
HTTP/1.1 correction directly on v57
`36e1d8bbe1bdbf4522e49cf83d740780d1c54900`.

## Run the replay

Use Python 3.12 or later, Elixir 1.20.4 with OTP 29, PostgreSQL 17, and local Hex
archives and packages for the pinned `hosted/mix.lock`. The target Git commit and
its hosted blobs must be available locally. Run from the repository root.

```sh
python3 -OB tests/integration/l07-hosted-privacy/run.py
```

Use `--pg-bin`, `--hex-cache`, or `--mix-cache` for non-default installation
paths. Use `--receipt /path/to/new.json` to save the sanitized result. The normal
command exits 0 when both profiles complete their HTTP, stock sink, and cleanup
checks. Use `--require-clean-telemetry` to also require private markers to be
absent from the privileged event subscriber. This option exits 2 for the known
metadata finding after both profiles and cleanup complete. A replay error exits 1.

The runner archives the pinned source and installs the locked dependencies with
`HEX_OFFLINE=1`. The test overlay exposes the pinned registration fixture's SQL
setup helper and excludes that fixture's own test. The privacy test uses the
stock provider's second-tenant and reduced-scope modes. It keeps the normal
`RuntimeConfig` HTTP options and uses an ephemeral loopback address. The root
protocol probe separately verifies the HTTP/1.1 listener behavior.

The runner uses private scratch under `verification/local/` and starts one
cluster and one BEAM instance at a time. It caps source and cache inputs and
individual output files, and samples the scratch tree against a 1 GiB stop
threshold with 256 MiB reserved within the 1.25 GiB budget. The receipt reports
the sampled peak. The runner verifies database removal, process group absence,
and reuse of the Phoenix, authorization, JWKS, and PostgreSQL ports. It removes
scratch on completion and prints the path if process custody is unresolved.

## Read the results

- Both synthetic tenant owners sign in, list their own organizations, submit
  support requests, read builds, and export workspace data over real HTTP.
  Cross-tenant build, log, artifact, and export requests return 404. A valid
  session with reduced build scope receives 403. The fixture checks exact
  response codes and bodies on enrolled refusal paths.
- The ordinary profile has retained reads disabled. The retained profile serves
  both owners' sanitized build log projections and three synthetic artifacts
  belonging to one owner. It refuses a projection with an injected raw field.
  Both profiles keep Oban queues off and seed terminal journals and files
  directly. Worker log generation and native compilation are outside this test.
- The runner scans the full combined BEAM stdout/stderr and PostgreSQL stderr
  after both owned groups exit. A separate log message proves each configured
  sink is live. The scan uses raw synthetic marker strings, including generated
  fixture session material, and emits only labels. PostgreSQL uses the recorded
  stock logging settings. This covers the tested settings and marker encodings.
- The fixture checks the registered callbacks with `:telemetry.list_handlers([])`
  and the stock Logger sinks with OTP `:logger` APIs. It allows only the pinned
  Phoenix logging handlers and Mixer in-process transaction receipt callbacks.
  Before and after the observer, the inventories contain no default exporter.
  The fixture uses loopback services and has no external receiver. The result
  provides no packet-level egress measurement.
- The deliberately attached BEAM subscriber sees request cookies, CSRF tokens,
  form markers, query secrets, and the rejected bearer marker in selected
  HTTP event metadata. It also sees tenant labels in Repo results. This is
  privileged in-process evidence, and it remains an open privacy finding on the
  HTTP/1.1 pin. The receipt stores event counts, field names, and marker labels.
  [Original adverse receipt](../../../verification/receipts/l07-hosted-privacy-original-adverse-20261120.json)

The route probes for metrics, telemetry, source maps, and crash attachments
return 404 on this router with and without a session. They establish route
absence for these requests. App telemetry upload, per-app identifiers,
telemetry disable controls, positive bearer or audit export, offboarding,
deletion, backups, retention policy, and cache isolation across a shared proxy
or CDN remain outside the replay. The tested `no-store` headers cover the
client-facing endpoints. Crash attachment and source map intake, access, and
retention require their own evidence, including release artifact serving.

[Corrected-source replay receipt](../../../verification/receipts/l07-hosted-privacy-replay-20261120.json)
[Separate HTTP protocol receipt](../../../verification/receipts/l07-hosted-http1-privacy-20261120.json)
