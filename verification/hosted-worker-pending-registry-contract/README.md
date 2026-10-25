# Registry contract packet

This packet accompanies `docs/hosted-worker-pending-registry-contract.md`.
It defines public private-binding types, root-selected finite limits, canonical
identity/hash/shard vectors and 30 required implementation acceptance cases.
No registry, audit coordinator, schedule, migration or live route is implemented.

`verify_packet.py` checks packet consistency, independent Python-generated exact
UTF-8 hash bytes, all 16 shard buckets and the inspected source hashes. The
type-only interface is checked by the existing pinned TypeScript compiler.
These are static contract checks. Runtime cases are explicitly pending and need
the actual candidate's cross-DO workerd/SQLite implementation, not a model or a
driver that returns prewritten observations. There is no pass claim for a
candidate, production deployment, scheduler, clock, provider, restore authority,
physical device or GA gate.

Recheck the source-bound packet from the repository root:

```sh
python3 verification/hosted-worker-pending-registry-contract/verify_packet.py
```

The source manifest describes the inspected tree and baseline Git revision; some
root-owned checkpoint documentation may have been uncommitted when inspected.
After implementation changes those sources, a manifest mismatch is expected;
preserve this proposal receipt and create a new source-bound implementation
packet rather than rewriting its historical evidence. `receipt.json` binds
the exact commands, versions, stdout/stderr and scope of this contract check.
