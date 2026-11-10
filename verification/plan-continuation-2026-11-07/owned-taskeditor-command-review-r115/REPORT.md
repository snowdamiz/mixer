# R115 independent review: PASS

The exact R110 isolated experimental command candidate passes this review. No
concrete blocking counterexample was reproduced. Root retains the adoption
decision; no canonical source or product gate was changed.

The reviewed patch SHA256 is
`2b629bb2ddfbdba8baa856d56db61d0fc46b8b6dd503f8f1ecb6ebbb3c5ff36d`.
Every source entry in R110's after-manifest matched both its retained source copy
and the fresh copy compiled here, before and after execution. Changed afterimages
matched. The source-tree identity supplied by that matching manifest is
`79c68f771f38eec85a68c3c15b917dd9dac0f679e292a339e7f2863d5f271ea6`.
All canonical before-manifest files, including default profiles and runtime
accounting/cache code, still match their original hashes. No root Git read ran.

## Independent execution

The unchanged 60,877,726-byte R106 module, SHA256
`24c0fb1bb38f64ad254ca89543b7ca1328bc8bdf83d198c9e84ba127d9fb7d85`,
was completely validated: 80,514 bodies, 6,546,069 static instructions. The
checked export selected entry 35. Actual owned dispatcher execution reached
`proc_exit(0)`, produced empty guest stderr and all 439 bytes of the frozen native
JSON, SHA256
`3135cb2d45d78106ddda5675c763457df818085394e7c8c63c84ea210d903f22`.
The full JSON preserves one save, one completion transition, 17 observer
deliveries, closed-submit rejection and every Unicode/newline/space byte. R106's
retained Node output was only cross-checked against its native output; Node was
not used for the owned execution.

As an independent anti-hardcoding control, a fresh module copy changes two `F`
bytes to `X`, at offsets 16,200,596 and 16,202,708 inside data section 11. Module
length, sections and code remain unchanged. Its SHA256 is
`2394524d1cd7064e3b047c25bc77e6fd7672b503e62e130e6926b64eda450f21`.
The engine again validates all bodies and executes successfully. Its complete
439-byte JSON changes exactly the test label to
`XieldLogTaskEditorBurstAndSaveDifferential`; every other byte matches the native
oracle. Changed-output SHA256 is
`04edef5a8f8fc18291c1f88920d9c79d95ad6dfea52a351b548f3a3304609a17`.
The harness compares complete output bytes inside the executable test, followed
by independent Python artifact checks. No Swift source was recompiled.

Both runs end with every engine reservation category and live counter zero,
zero tickets and no cleanup invariant. Peaks were 162,857,305 and 162,873,385
requested-capacity bytes respectively, with 60 frames/pins and 36 host calls in
each. Instruction/work counts vary between runs and are retained individually;
no deterministic-count or performance claim is made. These are engine ledger
observations, not RSS measurements.

## Counterexample controls and source review

Six independent test functions and the six R110 regression functions pass in the
first selected payload. The second selected payload runs both full-module cases.
The redundant original R110 ignored full-guest wrapper stays ignored; the review's
explicit full-guest test executes instead. Raw records are in `commands/`.

- A type error after `unreachable` in the last uncalled body, beyond the old
  function ceiling, is rejected at absolute function 80,547, byte 323,706 with
  `operand_type`. The shared `validate::all` loop still visits every defined body.
- Unknown/reordered imports, namespace/signature mismatch, an imported command
  entry, wrong/extra exports, entry parameters, module start sections and
  unsupported shared-memory/table flags refuse. The original fixed reactor ABI
  still validates its original fixture. The real module still refuses at 79,966
  defined functions under the fixed reactor; strict public admission also refuses.
- Different legal data literals produce different actual stdout. Nonzero
  `proc_exit(7)` is retained as failure. A four-byte output cap refuses a five-byte
  write with errno-derived exit 51 and no output. A failing native sink reports
  `output_error` and cannot succeed.
- The actual WASI adapter overwrites environment sizes with zero. No-preopen and
  path-open calls return BADF (8); polling returns NOTSUP (58). The exact closed
  import resolver, fixed argv, capability grants and unchanged no-filesystem
  dispatch remain in use.
- Cancellation before adoption, exhausted deadline, adoption/construction
  resources, frame/pin/cache capacity, cache/execution work, host-call exhaustion
  and attempted widening past 64 frames/pins fail with consuming cleanup. Native
  cancellation raised by the output sink after guest exit leaves the completed
  guest result and complete cleanup; the documented native sink remains outside
  the engine's time/storage contract.

The meaningful code changes were reviewed in `experimental/policy.rs`,
`experimental/swift.rs`, command execution, its frame-operation integration and
WASI instrumentation, against original policy/metadata/body validation,
construction, dispatcher and cleanup paths. Command authority remains sealed and
consumed once. No source-hash special case, metadata-only admission, interpreter
substitution or guest-success receipt fabrication was found. The 131,072-function
and 16-million-instruction ceilings belong only to the distinct native-selected
command diagnostic policy. The fixed reactor/export ABI and public limits remain
unchanged. These ceilings are diagnostic headroom, not a production recommendation.

The existing 512-slot keyed scan plans, 64 resident/pin/frame ceilings, coupled
reservation tickets and metered vectors are retained. Added WASI counter storage
is included by the original `size_of`-based owner/construction accounting. The new
runner consumes original growth/frame cleanup and instance cleanup. If consuming
frame cleanup cannot complete, the report remains incomplete without a fabricated
zero-usage snapshot. Unsafe injection into that branch was not attempted.

## Bounds and limitations

Exactly two offline, locked Cargo compile commands used jobs=2, and exactly two
runtime executable payloads used test-threads=1. Both builds succeeded; the second
corrected this review's zero-host-call-budget fixture to actually execute a host
call, before any runtime payload. Candidate implementation files were unchanged.
All six new command groups were individually observed absent after direct-child
reap. Exact argv, PID/PGID, output, versions and elapsed command time are in
`COMMANDS.txt`, `commands.json` and `receipt.json`. Recorded command wall time is
8.668 seconds under the 600 active + 60 cleanup allowance.

Toolchain: rustc 1.99.0 `b940084d7`, Cargo 1.99.0 `5f94df478`, macOS 27.0.1 arm64.
Test executable SHA256:
`491fd2d2d9c5bb1270019185ab261bce6505c86ab90690afbfd39dce011d476f`.
The fresh retained source/build/module namespace is
`/Users/andreyyurlov/.t3/userdata/mixer-taskeditor-r115-lpifwroq`.
Logs and comparison outputs are also retained in this R115 directory.

CPU2 was implemented through Cargo job and test-dispatch limits, without an OS
CPU quota/affinity or RSS cap. Per-command wall/CPU/file/log limits and unchanged
engine limits were retained. Engine ledgers exclude caller buffers, allocator
overhead and native stack. No new native oracle execution occurred; the R106
native receipt and unmodified TaskEditor, Workspace, fixture and FeatureStore
source hashes were checked. Source inspection confirms MainActor dispatch,
`Task.yield()` and the real async save closure, preserving untrimmed save values.
Storage durability is outside that fixture's contract.

R110's separate failed pre-exec version launch retains its producer-reported
identity/absence uncertainty. This review did not inspect or operate on that
process chain or any historical hold. No candidate/canonical mutation, Git
operation, push, CI trigger, device, native app, signing, subagent, production
profile or GA change occurred. Immutable-package, widget/device, full W07/W08,
store and final acceptance remain separate.

Minimal next fix: none identified. Root may select integration and run
`FieldLogTaskEditorBurstAndSaveDifferentialOwnedVM` on the selected integrated
source with this same frozen module and complete native oracle.
