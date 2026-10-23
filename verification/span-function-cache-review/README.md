# Independent decoded-function cache review

The reviewed cache candidate has no open blocking findings within the accepted
Rust-only, nondefault decoded-cache scope. This review does not approve guest
execution or any product/GA gate. Root remains accountable for integration.

The candidate is bound to HEAD `b02b76f40133677f20f87272823aa1a8911a3fbf`
plus the complete dirty VM source manifest in
[`2026-10-23-host-v2/receipt.json`](2026-10-23-host-v2/receipt.json).
The implementation candidate manifest is
`bdbb303375c02abde79556475d930b42bcc889b0d8a3f6b0fa0a556867b9f5c4`.
The accepted design is `docs/span-function-cache-design.md`, SHA-256
`6a95391aac2c76bd194e84b89159d9333c7a2993834b8e76f391d79972ad786a`.
The reviewed production files are:

| File | SHA-256 |
| --- | --- |
| `vm/src/experimental/cache/mod.rs` | `464bc9bf0fc5415fd30632953cf7bb6e300a808f9fd9313832a24e78403d3135` |
| `vm/src/experimental/cache/decode.rs` | `d5ec3a33297c1dc38f8834e70ea13e525244e868aeac997d955a50d418fd3ae1` |

The initial all-source seal check rejected a separately added UI header before
running a compiler or probe. That rejection is preserved in
[`2026-10-23-host/preflight-rejected.log`](2026-10-23-host/preflight-rejected.log).
Root confirmed `vm/include/mixer_vm_guest_ui.h` was an additive, uncompiled
contract outside the cache candidate. The successful runner requires every
original implementation-candidate file hash to match and permits only that
explicit additional path. Its own before/after full manifest binds the header
as well; it does not silently accept other candidate changes.

The reviewer read the accepted design, public API, constructor/pin/release paths,
both decode passes, immutable validated owner, frozen IR construction and existing
cache tests. The review checked these boundaries:

- Complete sealed validation is the only constructor authority; imports cannot
  become entries. Feature exposure adds no default, C ABI, or executor route.
- Owner identities and pin nonces check overflow; opaque pins retain owner/slot/
  nonce rather than storage addresses, and returned views borrow the cache.
- Exact vector reservations are fallible, every production push is capacity
  bounded, flat branch payloads avoid nested allocations, and control storage is
  a fixed array. No infallible heap allocation was found on the reviewed paths.
- Resident, construction and fixed/scratch reservations remain separate; pinned
  bytes are a resident subset. Existing payloads remain charged through planning
  and partial construction remains charged until its payload is dropped.
- Selection is bounded and charged before its destructive phase. Pinned entries
  remain ineligible. A failed replacement may retain the completed eviction
  phase, which is explicitly part of the accepted contract.
- Wrong-owner releases retain the original token; cleanup requires no work,
  allocation, cancellation check or eviction. Forgotten pins consume their
  records and retain their payloads. Cache moves do not replace ownership.
- New operation/control/branch representations match the supported frozen
  semantics by source inspection; original public probes additionally inspect
  absolute positions and multiple flat branch-table slices.

One narrow observation was resolved by the implementation owner before the
sealed matrix: the final post-build cancellation path previously cleared the
construction reservation before dropping its completed temporary entry. Current
`mod.rs:674` explicitly drops the entry first and then clears the reservation.
This exact final cancellation window was inspected in source; it was not forced
by a timing-based race probe. No reviewer edits to implementation or owner tests
were made.

The independently authored [`probes.rs`](probes.rs) uses only the public cache API
and its own small original Wasm assembly helpers. It imports no owner test helper
or external implementation. Debug and optimized release runs both passed:

- Byte-pressure replacement needs two unpinned victims while an 80-byte entry
  stays pinned and a 205-byte mixed payload is constructed. Across all 133
  lifetime work cuts, 102 failures occur before eviction and 31 after the full
  two-victim phase. No half-applied plan, new pin or construction leak is observed.
- Failure of each of the three replacement allocation ordinals retains the
  pinned neighbor, drops partial vectors, releases exactly the two victim
  payloads, permits a successful retry and returns live requested bytes to the
  original baseline after cache drop. Zero reallocations are observed.
- With every allocation request denied, wrong-owner token recovery, view, hit,
  canceled hit and release complete with zero allocation attempts.
- An approved imported checkpoint remains outside the cache; absolute function
  index 1, absolute instruction positions, a two-label `br_table` followed by a
  zero-label `br_table`, and its control target are preserved.
- Eight threads create 256 distinct nonzero owner identities per profile. A
  separately pinned cache and token move to another thread and remain usable.
  This is a finite concurrency sample, not a formal race proof.

Run the review with a fresh output name:

```sh
python3 verification/span-function-cache-review/run.py --name fresh-host-run
```

The runner first validates the accepted-design and implementation-source seals,
then obtains Cargo's exact `experimental-function-cache` rlib artifact using
offline `--no-run` in the existing `vm/target/stream-validation-verification`
graph. Independent rustc executables link that artifact in debug and release;
their rlib, binary, inputs, commands, versions and output digests are recorded.
Build outputs stay under ignored `.build/`. No dependencies or graph are added.
Before root's subsequent combined cache/native feature build could overwrite
shared target artifact paths, both exact candidate rlibs were copied to ignored
`.build/retained-rlibs/`. [`retained-artifacts.json`](retained-artifacts.json)
binds those copies to this receipt and its recorded rlib hashes. This is local
review reproducibility material, not an immutable published consumer package.

To check the preserved receipt against the current tree:

```sh
python3 verification/span-function-cache-review/run.py --name 2026-10-23-host-v2 --verify
```

The check rejects changed source, input or log bindings. Later changes to any
bound VM file make this historical receipt stale as a claim about the current
tree; they do not rewrite what was observed for this candidate.

These are host macOS Rust observations. Work units are accounting units;
allocator counts are requested bytes, not RSS or wall-clock preemption. Owner
exhaustion and stale/nonce mutation defenses were source-reviewed and covered by
the implementation's separate internal tests; the public probes cannot forge
opaque tokens. No physical-device discovery or run was attempted. Execution
bridge, runtime recursive/indirect execution and trap/close integration, full
Swift, WASI, FieldLog release qualification, aggregate session admission,
standards/fuzz/security audit, native ABI/signing/store/customer evidence,
immutable published consumer packages, OTA and GA gates remain pending.
