# Actual cache deadline CI failure review

Run [40747548560](https://github.com/snowdamiz/mixer/actions/runs/40747548560), attempt 1, completed **failure** at commit `fb7c7f20f8a308424ef4b7092d19d3d4de2c7627`, tree `509093e0fcc9f4c83583f8d0ecd61b8b3c9d83d4`. The first actual failure was a stale finite-control deadline assertion. **Zero full attempts executed.** This run provides no new full-workload deadline, fuel, CacheWork, corpus parity, consuming-cleanup, or feasibility result.

## Decisive evidence

The pinned Rust 1.99.0 compiler installed; all 17 pure source/decision tests passed. The primary `256 / 64,000,000 CacheWork / 60,000 ms` profile compiled successfully in 18.601 seconds. Its four selected finite tests returned 3 passed and 1 failed in 1.052 seconds. `campaign_budget_geometry_and_reservations` panicked at generated `src/experimental_swift_reactor/cache_tests.rs:4291:5`:

```text
assertion `left == right` failed
  left: (100000000, 1000000000, 60000)
 right: (100000000, 1000000000, 30000)
```

The failed expected tuple comes from frozen `verification/swift-cache-capacity-campaign-v1/campaign-controls.rs:87`, which the v1 helper appends to the generated cache tests. The corrected v2 parameterizer changes the two runtime deadline defaults and intentionally leaves this test file unchanged. Its pure test at `test_campaign.py:40` enforces exactly those two changed files, so those 17 tests cannot detect the stale Rust expectation. The runtime's observed 60,000 ms is the selected value; the expected 30,000 ms is obsolete for this profile. This is not a sparse-checkout, compiler, workload resource-exhaustion, or process-custody failure.

The artifact's `campaign.json` records `fullAttempts: 0`, `profiles: []`, `status: stopped`, and `error: finite control failed: finite`. The driver increments the attempt counter only after the finite and harness controls. There is no harness-control or full-target directory. The conditional 128M profile was neither evaluated nor run. Its preflight source record is preparation only.

## Custody, identities, and scope

All five actual commands—rustc identity, cargo identity, Python identity, compilation, and finite tests—have positive PIDs, real exit codes, `processGroupEmpty: true`, no timeout, and no cancellation. The first four exited 0; the finite suite exited 101. Custody records `pendingCommand: null`, `provenClosedCommands: 5`, `commandCustodyUnresolved: false`, and `ownedScratchRemoved: true`. These are command and remote scratch observations. They must not be described as full-workload zero-resource cleanup, because that workload never started.

Artifact `12842671384` has 37,681 compressed bytes and SHA-256 `720f96131ae2385a56e2748f996e103f2108bf8eadc69de319daa85e4627f061`; it contains 31 files totaling 87,292 expanded bytes. The review verified the GitHub digest, archive limits, safe paths, regular file types, duplicate exclusions, CRCs, and every extracted file hash. No artifact code ran. The temporary download URL was consumed in memory and never saved. A post-download attempt to read unavailable Node `process.version` raised a ReferenceError after the successful archive write; subsequent independent hashing verified the archive, without another download.

The selected 15-file correction seal remains `d8079bacfbb5fee222ac55354ad5a9aaa2a320327d50acd181426fea0d46a2d3`. The v1 helper remains `5266e70df6e79054ffdc1abfc64b300d9f6252f11e55eb340716ab346bc4c556`. The primary compiled source closure is `2f0973fe11f5db5341d2896d0e9a25b30a11687dedea5914547f5897c8161d28`; the unexecuted 128M source closure is `fd27e6b68e3d57226ad14855166a33f359664cd848fcc1918f3b3e265ffc8a39`. The recorded primary binary is 6,156,376 bytes, SHA-256 `8dedabd2bfbe8147f005c13801fcc8f129cf17fd288310b80c1ae29e9434ac35`; the archive does not include that binary, so this review binds its recorded identity without independently rehashing it. Preflight binds the original 53,777,114-byte full Swift artifact `24d85729a659ff3e5fc6f0517709afbb68b371a41829e90785dabd48e0620994`. It was not executed by this run.

`verify_evidence.py` passed 97 independent offline checks. Its command, output, Python version, source identities, command receipts, and limitations are saved beside this review. This review started no compiler, guest, native/runtime, UI, capture, local custody probe, or remote retry. It read no private FieldLog source/log folder and changed no canonical source, workflow, gate, or delivery metadata. All pre-existing local process holds remain in force.

## Concrete next decision

Preserve this failed dispatch and both earlier frozen v2 packets. In a new versioned correction, change only the generated finite-control expected deadline from the exact tuple `(100_000_000, 1_000_000_000, 30_000)` to `(100_000_000, 1_000_000_000, 60_000)`. Leave the frozen v1 control untouched. Do not weaken the assertion to accept either deadline or derive its expected value from the observed default. Extend the pure exact-delta check to permit this one explicit test expectation change alongside the same two runtime deadline changes, and verify that normalization restores the prior generated test bytes.

That correction directly unlocks the existing four compiled finite controls, the harness control, and the first selected full target. Keep the same original artifact/oracle, source behavior, grants, budgets, 540-second driver bound, 200-second full-target bound, maximum two full attempts, custody guard, and CacheWork-only eligibility for the second attempt. Root must select and deliver a changed sealed source before any new dispatch; this review does not dispatch or authorize an automatic retry. The corrected compilation and controls must pass before any full attempt is counted as executed.

Because this dispatch performed zero full attempts, it cannot discriminate the 60-second deadline hypothesis. A targeted execution-unlock correction is justified by this concrete test defect; repeating the unchanged failed source is not. If the corrected bounded execution still fails to advance both corpus calls and cleanup, apply product-plan 24.4's Astra comparison of algorithm change, resource-policy change, and a different implementation. Native/mobile, public/signed OTA, FieldLog publication, and GA remain pending.
