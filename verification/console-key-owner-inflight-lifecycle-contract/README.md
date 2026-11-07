# Active-fetch lifecycle: source-only packet

This finite packet specifies KOL08-GRACEFUL and KOL09-KILL. Read contract.md,
prospective-tests.json, execution-proposal.json and reviewed-evidence.json.
It implements no canonical source/test seam and runs no Elixir or TLS process.

The missing test-build-only local destination constructor is explicit. Existing
RawFixture/direct-stop/fixture-supervisor cases cannot silently satisfy the new
real-supervisor/completed-TLS boundary. The original KOL08 ordinary owner-crash
adaptation remains pending beyond this two-case packet.

inputs/ preserves the exact reviewed bytes. source-bindings.json records every
origin, byte count and SHA-256; prepared-3 inputs are checked against their frozen
manifest. freeze.json lists every file below this directory, including copied
upstream freeze.json files. Its sole exclusion is the exact packet-relative path
freeze.json. No basename filter is used.

The read-only offline check is:

    python3 -B verification/console-key-owner-inflight-lifecycle-contract/verify_packet.py

This checks packet membership, bytes, hashes and contract shape. It does not
validate Elixir syntax, execute tests, accept a runtime or authorize a host slot.
