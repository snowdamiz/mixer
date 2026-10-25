# Frozen next-retention experiment, unselected

This packet contains an independently authored finite Python model for
count-plan-aware cold insertion. No product implementation or target retry is
selected. See `docs/swift-retention-next-design.md` for policy, accounting limits,
phase regressions and the selection decision.

- `contract.json` was frozen before the first execution; no policy retuning.
- `model.py` defines the primary policy and three fixed controls.
- `model-attempt-1/` retains its exact command, inputs, result, streams and cleanup.
- `test_model.py` has 24 passing finite host methods, including independent
  reference cases and selected historical byte-hash checks.
- `tests-attempt-1/` retains the corresponding test evidence.
- `synthetic-traces.json` contains explicit reconstructed finite access bytes;
  these are synthetic and are not the actual target call stream.
- `analyze.py` derives `comparison.json` without executing prior producer code.
- `seal-preflight-attempt-1/` preserves the initial metadata-mismatch rejection;
  `metadata-context-change.json` records the later root-owned PLAN update without
  changing historical receipts or retuning/rerunning the model.
- `seal.json` and `seal.sha256` bind the final owned packet and design document.

Reproduce into a **new** attempt name, never overwrite an existing attempt:

```
python3 -B verification/swift-retention-next-design/run.py model model-new-attempt
python3 -B verification/swift-retention-next-design/run.py tests tests-new-attempt
```

The runner validates the ordinary 132-file live source closure, binds every
consulted input and owned executable, captures the actual Python/platform/revision,
uses a freshly named owned temporary directory and removes it after synchronous
completion. It starts no VM/compiler/native/UI/capture/background process and
does no process discovery. Existing evidence is read only; producer scripts are
never imported or executed.

The model's eight-credit miss estimate is not measured CacheWork. Global model
assertions are test instrumentation. No Rust type layout, exact future reservation
delta, body decoding/work, CPU time, zero-ledger cleanup, target benefit, physical
phone, FieldLog published package or GA acceptance is established.
