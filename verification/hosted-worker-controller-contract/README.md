# Worker controller contract packet

This packet selects a future implementation and supplies independent executable
acceptance tests. It contains no controller implementation or provider adapter.

The contract is `docs/hosted-worker-controller-contract.md`. Root approved the
contract-only proposal before edits. Only that document and this directory are
owned by the lane. Sources are explicitly allowlisted in `run.py`; the frozen
catalog/authority lane is neither discovered nor loaded.

Commands run from the repository root:

```sh
python3 verification/hosted-worker-controller-contract/run.py
python3 verification/hosted-worker-controller-contract/verify_packet.py
node verification/hosted-worker-controller-contract/acceptance.mjs --vectors
node verification/hosted-worker-controller-contract/acceptance.mjs
```

The last command **must exit 77** while no candidate is assigned. This is pending
controller acceptance, not a failure hidden as a pass. `--vectors` verifies five
Python/Node UTF-8 byte/hash fixtures only. Jason interoperability is pending.
`verify_packet.py` checks hashes, explicit source bindings and test inventory;
its passing result is packet consistency only. It imports no product modules.

`receipt.json` captures runtime versions, the explicit allowed-input tree digest,
input/artifact hashes, command outputs and limitations. `sources.json` seals nine
official Cloudflare documentation retrievals with timestamps and raw response
hashes; no complete third-party page is copied into the repository. Browser/web
documentation review preceded those bounded GETs. Repeat source retrievals can
change hashes even when product documentation is unchanged. `run.py` deliberately
refreshes the packet; do not use it to imply old results apply to a newer source.

A later independently assigned controller candidate can be tested with:

```sh
node verification/hosted-worker-controller-contract/acceptance.mjs --candidate /absolute/path/to/test/acceptance-driver.mjs
```

The exact test-only driver interface is documented in the runner header. Root
must inspect candidate source and prove actual SQLite-backed DO runtime execution.
The runner cannot establish that platform fact merely from adapter claims.
Additional acceptance cases and all operational gates in the contract remain
mandatory; this finite first runner is not the whole product qualification suite.
