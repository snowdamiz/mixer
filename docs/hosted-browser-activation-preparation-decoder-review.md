# Independent activation-preparation decoder review

The selected ordinary `ActivationPreparation.decode/1` passes independent host
shape review: 29 executable methods, zero failures and zero skips. No product
defect was found in the frozen decoder. This acceptance is limited to the pure
decoder and its existing ordinary `StoredSnapshot`/`Vault` validation path.

The reviewed decoder SHA-256 is
`e208e159719dd29ff75186667404cb6018391a2ecc3b8a3534db131d1bc281f5`.
The existing snapshot SHA-256 is
`ce92f99c3990bf9ddd0fbf5d8c7d329ea63bb5dc31ec3df4922907b19986cd3e`;
the existing Vault SHA-256 is
`e376cdd7305a520c61e716e3f4fcd3f5493e280ff5424ba822516f9a6f4281b2`.
These actual ordinary modules are compiled together with standalone
`elixirc --warnings-as-errors`; no product stubs or producer test oracle are
imported. Review fixtures are independently authored synthetic values in the
documented format. Exact source copies, the current Git revision/tracked tree,
selected file hashes/tree digest, compiled BEAM hashes, command arguments, tool
versions and output live in each timestamped attempt.

The review confirms these parallel contract properties:

- Exactly six string keys produce exactly the six typed fields. Each missing,
  extra, atom-alias, mixed-key, nonmap, struct and malformed nested row denies with
  only `{:error, :session_unavailable}`.
- Version is exact integer 1. All three revisions independently require integer
  1 through 9007199254740991. Principal text accepts 1 through 128 UTF-8 bytes,
  counts bytes for multibyte text, rejects NUL/invalid encoding and retains the
  supplied text without trimming or normalization.
- The full decoded snapshot equals the actual `StoredSnapshot.decode/1` result.
  Its existing exact keys, bytea encoding, byte/cipher bounds, key-ID/AAD shape,
  browser/vault/attempt linkage, claim bounds and completion invariants remain
  enforced. Every existing nested key and atom alias has a negative control.
- Valid absent, pending, provider-rejected and completed snapshots are first
  accepted by the actual ordinary decoder and then denied by preparation. Only
  a claimed attempt with all four attempt-cipher fields erased and
  `attempt_envelope: nil` succeeds. Both preauth and active browsers succeed.
- The incoming provisional principal can differ from an old active browser
  principal. The result preserves the old browser/session-envelope identity and
  the separate incoming principal. All provisional revisions can change
  independently without acquiring owner or authorization binding.
- Typed result/snapshot/envelope/sealed `Inspect` output omits private values.
  Invalid input yields the exact generic result and no captured standard output.
  No plaintext is synthesized or decrypted: synthetic unauthenticated session
  ciphertext passes shape decoding and fails actual Vault authentication.
- Stale but internally ordered synthetic dates pass shape decoding. The decoder
  has no current-time gate, caller identity/configuration/claim input, startup,
  readiness, authenticated-session or permission entrypoint.
- Process dictionary, environment and working directory remain unchanged across
  repeated successes/errors. Call tracing is bounded to decoder entry/return in
  an isolated host VM and observes actual snapshot decode and Vault associated
  data validation. Selected valid/invalid paths make no clock, random, file,
  network, process mutation, application, database, logging or authority calls.
  The worker's coordination messages are outside the decoder trace window.
  Actual source and compiled imports supplement this finite dynamic evidence;
  it is not universal runtime qualification.

The root-approved runtime-contract clarification was independently reviewed:
`decode/1` validates shape and delegates snapshot decoding; a future trusted
owner must compare the complete decoded fields with its retained claim, current
access identity and current configuration before use. A one-argument decoder
cannot establish those comparisons. This resolves an attribution ambiguity
without weakening that pending owner responsibility. The reviewed
[runtime contract](hosted-browser-lifecycle-runtime-contract.md) SHA-256 is
`faad9be11adf9bb9501bd7007811dc893562c878026ea7734c3104ceabbc0d82`.

Run the review with:

```sh
python3 verification/hosted-browser-activation-preparation-decoder-review/run.py
```

The [latest receipt](../verification/hosted-browser-activation-preparation-decoder-review/receipt.json)
identifies the selected final attempt. The run records Elixir 1.20.4 on Erlang/OTP
29 and Python 3.14.8, compiles only the three selected product modules, checks
explicit review formatting/Python syntax/whitespace, audits compiled imports,
executes the independent methods and verifies selected source stability. All
owned scratch/compiled products are removed, including failed attempts. Earlier
failed attempts are retained: one unsupported compiler-output option, one
unsupported Elixir runtime option and one review tracer initially including its
own coordination send/deprecated compiler-option setup. These were review
harness mistakes; no product bytes changed. The final run has no test/compiler
warnings and passes all methods.

No broad hosted application, Mix discovery or database is started. This lane
does not read, import or execute the frozen catalog-inspector/authority-driver or
rejected Worker V2 work. No other lane's files, plan/status/gates, dependencies,
commits or pushes are changed by this review. No native/capture/UI/physical-phone
processes or process discovery are started. Native checks remain paused/unrun.

Additive SQL projection/type/helper/migration/catalog admission, immutable source
binding by the runtime owner, fresh current verifier/OIDC/provider evidence,
owner-retained claim/configuration/identity comparisons, transaction/time fences,
real key custody, HTTP/console composition, deployment and FieldLog qualification
remain pending. No GA gate or complete runtime lifecycle is accepted here.
