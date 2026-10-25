# Browser runtime constructor independent review

The exact `Custody.new/2` and `BrowserAuth.RuntimeConfig.new/4` source passes
independent development review. The final isolated run passes **25 independent
methods, zero failures, skips or exclusions**. No product correction was needed.
This accepts constructor shape, derivation and rejection behavior only.

The reviewed tree is based on `4492bbc74c47c77514951ae49b0fe418c7873db8`, with
the new uncommitted source identified by these frozen SHA-256 values:

| Source | SHA-256 |
| --- | --- |
| `hosted/lib/mixer_hosted/browser_auth/custody.ex` | `675429fa3daf5c84cf8ee8223aeeea6842889af859a6468c763ffc0ea6033803` |
| `hosted/lib/mixer_hosted/browser_auth/runtime_config.ex` | `0ce7e28450b7f5652313fc22cb909ea6e65cc8b4a8edcc960669d5a950da0962` |

The [final receipt](../verification/hosted-browser-runtime-constructor-review/attempts/final-2/receipt.json)
records commands, source and dependency hashes, output hashes, tool versions and
cleanup. Its complete input-tree digest is
`2ea94047f844426fff327816c7581ddefc980cee9b06304ba50f28113eaed1af`.
Elixir 1.20.4 / OTP 29 / public_key 1.21.7 / OpenSSL 4.0.3 ran with two scheduler
threads. The review compiled only the selected actual ordinary loader,
StartupConfig, Config, Manifest, Encoding, BoundedJSON, ConfigurationDigest,
Vault and constructor sources with warnings as errors. Existing Jason BEAMs
were the only project dependency path. Producer tests were not imported.

| Independently exercised boundary | Observed result |
| --- | --- |
| Actual ordinary `RuntimeConfig.load!/1` role, identity startup and Repo | Configured API values are preserved; processor and invalid roles deny. No positional substitute can recast the role. |
| Ordinary Config / Manifest / digest validation | Exact enabled human profile, version, issuer, client, audience and binding are required. Duplicate identity options, malformed manifests and browser JSON duplicates deny. |
| Closed maps, structs and keyword lists | Browser env, hosted outer struct, lifecycle map, Custody/key and ordinary Repo/TLS options reject missing, unknown or duplicate members as applicable. No lifecycle host, URL, pool, callback or raw-key override is admitted. Existing trusted StartupConfig validation remains delegated to Config/Manifest. |
| Custody and references | Exact three-member material, configured `vault://` equality, canonical ASCII paths and 256-byte bound are required. Existing Vault key ID/bytes validation is used again at runtime construction. |
| Text and opaque byte bounds | Host, roles, references and browser metadata reject invalid UTF-8/NUL where their existing text grammars require it. Database/password inputs retain the ordinary loader's opaque 1–4,096-byte binary contract; no UTF-8 claim is added. Raw vault key material remains exactly 32 arbitrary bytes. |
| Explicit role expectations | Ordinary login, lifecycle login, writer and relation owner are pairwise distinct restricted names. All pairwise collisions, reserved names, invalid bytes and oversized names deny. |
| Connection derivation | Exact ordinary host/port/database/TLS is retained. Lifecycle credentials are distinct supplied values; pool size is 2, pool count 1, queue false, connect/query limits 5,000 ms and sensitive connection errors false. Ordinary pool sizes 2/8/20 preserve the expected aggregate increment of 2. |
| Direct DNS and TLS | Pooler labels, IPs, URI aliases, malformed hosts, weakened verification, SNI mismatch, malformed roots, mismatched decoded roots, extra/duplicate TLS options and replacement matchers deny. The exact loader-owned OTP match fun is retained. A malicious matcher is never invoked. |
| Disabled mode | Only empty/default or explicit disabled browser maps with nil lifecycle and custody material succeed; all five remaining result fields are nil. |
| Disclosure | Inspect exposes only documented mode/connection counts. Constructor errors remain exactly `{:error, :session_unavailable}` with no input echo. Credentials and raw key bytes do not enter configuration digest bytes. |
| Effects | No new environment, application configuration, file/network, randomness, process, port or global-store mutation is observed in the scoped constructor trace. See the existing URI infrastructure read qualification below. |

The first three diagnostic attempts are preserved. They exposed an overly broad
review assumption that existing validation performs zero transitive global
reads; they did not expose a new constructor effect. On this Elixir version,
ordinary Config/Manifest URL validation follows `URI.uri_from_map/1` through
`elixir_config.get({:uri, "https"}, nil)` to
`ets.lookup(:elixir_config, {:uri, "https"})`. The accepted trace exception
matches that exact table, key, argument shape and caller, with exactly 12 reads
across two configured calls. All other traced effects still fail the test.
The final independent control changes only the disposable BEAM node's HTTPS
default port from 443 to 444: both the original configuration and explicit-port
aliases deny, restoration to 443 is asserted, and the baseline then succeeds.
There is no transitive zero-global-read claim. `run-4` passed the 24-method
predecessor; `final-1` adds the registry-drift control. `final-2` repeats that
25-method suite after removing one review-source blank line at EOF, and is the
acceptance run. The whitespace diagnostic is preserved separately.

All temporary owned compiled BEAM directories were removed, including failed
diagnostic runs. No application, database, network resolver/provider, browser,
capture, simulator, emulator or physical-device process was started or
discovered. Local OTP CA roots are read by the ordinary loader during fixture
setup, outside the constructor effect trace. The isolated-node registry control
restores its value before node exit.

This review does not establish that an arbitrary struct is the live supervised
configuration, that secret material came from a secure source, or that a caller
cannot forge trusted BEAM data. Same-value startup composition, live custody and
owner isolation, LifecycleRepo checkout/deadlines, per-transaction catalog/SQL
admission, cryptographic roundtrips, current verifier/provider joins, HTTP,
operator/Neon, native, FieldLog and GA acceptance remain separate pending work.
No Application, supervisor, Repo, Catalog, Store, route or provider wiring was
changed. Frozen catalog-inspector, authority-driver and rejected Worker V2
sources were not read, imported or executed. No GA gate is promoted.
