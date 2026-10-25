# Runtime lifecycle contract evidence

This is documentation evidence only. The proposed runtime owner, lifecycle
pool/catalog admission, additive activation preparation and provider/workspace
composition are not implemented or accepted by these checks.

Reproduce from the repository root:

```sh
python3 verification/hosted-browser-lifecycle-runtime-contract/check_contract.py
```

The independently authored checker starts one short-lived Elixir VM, requires
only ordinary `BrowserAuth.StorageSchema`, inventories its eighteen fixed
function bodies/signatures/settings and verifies all nine public typed signatures
against the contract. It uses no application startup, broad hosted harness,
frozen lane, database, provider, credential, native runtime or capture process.
Eight structural controls pass, including independent document mutations for
missing/changed/extra helpers, body hashes and function settings. The runner
preserves each attempt, command argv/output hashes, versions, HEAD, source hashes
and stable-tree digest. Source comparison and text checks do not establish
runtime security or OTA authorization.

`baseline-catalog.json` is the existing version-1 ordinary source inventory,
including exact bodies and their SHA-256 digests. It is not a live catalog
receipt. `receipt.json` copies the latest completed attempt; immutable attempt
receipts and stdout/stderr remain in `attempts/`. Earlier successful checks bind
earlier document revisions and do not replace the final revision's receipt.

`adversity-matrix.json` lists forty pending implementation cases, grouped by
future bounded host fixture. It explicitly records pending status and the need
to freeze exact fixture commands with implementation ownership. None ran in this
contract-only slice. Synthetic loopback identities/keys/roles later used in those
fixtures will not qualify a real provider or Neon/operator topology.

The first selected implementation seam is the exact pure Custody.new/2 and
RuntimeConfig.new/4 contract; all dependent runtime interfaces remain inert until
separately implemented, tested and reviewed. An independent contract review may
be recorded by root in a separately owned evidence directory. Root retains all
integration, status/index/gate updates and authorized delivery.
