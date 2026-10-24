# Private lifecycle contract packet

This is a proposal for root review. `selected=false` and `runtime=false` remain
binding for this packet. The contract is
[`docs/swift-reactor-lifecycle-contract.md`](../../docs/swift-reactor-lifecycle-contract.md).
`matrix.json` contains 24 planned lifecycle/target acceptance groups; none passed
by this packet. The target runner is neither implemented nor authorized here.

The saved attempt has four positive production Rust typecheck configurations and
two expected borrow rejections, plus three tool-version commands. The only
isolated source changes are an uncalled probe and a private module declaration.
The witness is deliberately narrower than the product proposal: its boolean and
copied vacancy check are borrow experiments, not an implementation to promote.

Run the saved-proof verifier from the Mixer repository:

```sh
python3 -B verification/swift-reactor-lifecycle-contract/verify.py --live
```

Omit `--live` for archive-only replay. Both modes are read-only and execute no
compiler, test or VM. They check the packet's exact file closure, saved inputs,
original/normalized V7 identities, archived baseline/witness bytes, commands and
expected diagnostics, scope flags and cleanup receipts. The live option also
checks the current 130 VM source hashes, bound input files and absent scratch.
It does not rediscover process holders or devices.

`collect.py` can create a fresh uncalled composition attempt with installed pinned
Rust/Cargo in new owned temporary targets. It uses `cargo check --lib --locked
--offline`; no test/VM binary runs. Its exact executable hashes, versions,
arguments, source closures, complete outputs, process groups and cleanup are
retained. Running it in this sealed directory changes the packet file closure;
preserve this packet and arrange a separate new reproduction directory before
collecting another attempt. Do not rewrite historical attempt evidence.

The baseline archive is a new copy of root's final normalized 130-file V7 source
closure `3dee84f70c852c2a26572c1d6e3463e45e56760a6bba403fabfb9c355ccb1cd3`.
Root's predecessor runtime results remain scoped to original V7. No retained
53 MB reactor was read or run. No product source, tracker, Git, network, provider,
native app, simulator/emulator or phone was changed or used.

Selection must be a separate root review artifact. New lifecycle/common-barrier
accounting, actual behavior, the complete entry route and later target execution
remain unaccepted. Native/FieldLog/OTA/GA qualification remains pending.
