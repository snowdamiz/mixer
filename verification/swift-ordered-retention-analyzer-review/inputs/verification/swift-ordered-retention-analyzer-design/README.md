# Offline analyzer design packet

Scope: concrete contract, fixed type/interface layouts, authored step schedule
and independent finite support controls. This is not a complete Rust analyzer,
host custody wrapper, strict original-result/profile adapter, target driver or
workload pass. No stream's old sidecar is modified or promoted.

The final command receipt is `result.json`. Run the finite design checks with:

```
/opt/homebrew/bin/python3 -B verification/swift-ordered-retention-analyzer-design/run_checks.py
```

That producer creates a new retained run and requires a new seal. For read-only
verification of the final frozen packet, upstream member identities, finite
Python tests and retained standalone layout binary:

```
/opt/homebrew/bin/python3 -B verification/swift-ordered-retention-analyzer-design/verify.py
```

Rust/Cargo/product/target code is not imported by the Python oracle. Only the
single independently authored `layout.rs` file is compiled; it has no dependency
or product import. `inputs/` snapshots source/documents actually consulted.
The large original source archive is hashed member-by-member in64KiB blocks;
only three specifically permitted cache/control files are snapshotted.

Run1 preserves a failed seal-digest transcription (member count222 accidentally
concatenated to a64-character digest). Run2 preserves a failed support-runner
archive preflight (three original source members exceed a snapshot-only2MB
limit); the correction hashes every manifest member in bounded blocks and keeps
the limit on the three selected snapshots. Neither failure started a compiler,
product, analyzer or native runtime. Successful runs retain tool/version/hash,
revision/tree digest, argv/environment, outputs and cleanup. No owned scratch
source/build/native instance exists; the finite layout executable is a retained
evidence member. No process discovery, source restoration, commit or push occurs.

All186 original prototype,222 completion and158 independent completion-review
sealed members verify before and after the finite tests. The selected finite
completion has root acceptance with independent peak16,186; that does not accept
this new analyzer design. Native/capture/UI execution stays paused. Full analyzer,
real target binding, stdout/stderr target transport, full workload, policy,
published-package FieldLog and signing/store/customer/operational/GA remain pending.
