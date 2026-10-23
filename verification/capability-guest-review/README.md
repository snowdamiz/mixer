# Independent actual-Wasm capability guest review

No actionable defect was found in the documented Rust composition at frozen
commit `cc0ac37abf45c59df7c85f59ebbb038af7c0a251`. Ten original public-API
adversarial test functions pass in debug and release on macOS arm64. `rustfmt`
and `clippy -D warnings` also pass. This review changes no implementation files.

## Frozen inputs and reproduction

The implementation author's 77-input manifest is
`vm/verification/capability-guest/2026-10-23-host/source-manifest.sha256`, SHA-256
`1697111c4821879673950c143d8474667286e8632c6d769239ff402f999274ba`.
`input-audit.json` independently checks every input and all 42 recorded command
log hashes from Git objects at the frozen commit. It checks 10 unchanged files,
four unchanged public Rust field declarations, empty default Cargo features,
and the 12 exact fixed failure payloads against the pinned transport contract.
The author test, oracle, allocator, and C-smoke logs were verified for identity;
those commands were not independently repeated by this review.

Run from the repository root:

```sh
python3 -B verification/capability-guest-review/verify.py --revision cc0ac37abf45c59df7c85f59ebbb038af7c0a251
python3 -B verification/capability-guest-review/audit_inputs.py
```

`verify.py` exports only the 33 frozen VM source/Cargo inputs into ignored
`.build/capability-guest-review/source`, makes source files read-only, and runs
a separate dependency crate with `experimental-capability-guest` and
`experimental-stream-validation`. It removes stale source-export files and
checks the exact set and hashes again after execution. Its source manifest
SHA-256 is `c17feb07ab9f9c75f6786a6a022171a8b357ecc3d38dc0c80a8bfa99fa8011bf`;
this narrower compilation manifest is distinct from the author's 77 inputs.
One shared ignored target directory is reused, with incremental compilation off.

`frozen-receipt.json` records exact commands, tool versions, source/test/driver
hashes, environment, exits, duration, and raw log hashes. Final execution used
Rust/Cargo 1.99.0, `aarch64-apple-darwin`. `receipt.json` binds this report and
the preserved evidence files. Changed earlier logs are retained as
`*.previous-N.log`.

## Independently exercised behavior

The tests build their own Wasm binaries, LEB encodings, memory sentinels, and
expected results. They import no engine tests or binary fixtures.

- All four enqueue imports return through raw exported imports, direct wrappers,
  and indirect wrappers. Indirect wrappers use the returned value in arithmetic;
  wrong signatures, null entries, and out-of-bounds table indexes trap. Argument
  snapshots survive guest memory writes and growth.
- A 70-case enqueue matrix uses independent unsigned 64-bit range arithmetic
  for 32-bit guest offsets and lengths. All 61 rejected cases preserve every
  memory byte and create no request. Twelve poll cases cover invalid ranges,
  overlapping length words, zero capacity, insufficient capacity, complete
  delivery, and stale retry without partial payload writes or early consumption.
- Exact and one-less fuel thresholds cover six argument lengths and four
  completion lengths across 64-byte charging boundaries. Failed enqueue/poll
  charges leave token/payload memory untouched. A failed poll closes the guest
  while retaining the installed native ticket until actual exit acknowledgement.
- Startup enqueues are unavailable before enablement, never become dispatchable
  after enablement, and deliver the exact fixed failure bytes. The fixed wake
  export actually polls and consumes a result; consumed work does not wake twice.
- Trap and external cancellation close the engine permanently. A concurrent
  native observer cannot drain an enqueue from an active Wasm turn; cancellation
  discards it. Foreign owner tickets fail despite identical raw token bits.
- Thirty-two native completion versus actual guest cancel-import races each
  select one immutable terminal result, deliver once, and retain one native exit
  obligation. Dropping a cancel-control identity does not acknowledge exit.
- A shortened monotonic deadline prevents a later success, delivers exact
  `deadlineExceeded` bytes, and retains the dispatched lease. Repeated explicit
  close reports the same retained cancellation obligation. A preexisting posted
  completion survives a later expiry scan.
- Tickets remain able to acknowledge exit after the guest and every port have
  been dropped. Duplicate acknowledgement is stale. Whole-module validation
  rejects malformed uncalled code, wrong import names/modules, missing memory,
  missing/imported wake, and imported startup. Legacy decode and streaming
  inventory reject the new imports under all three old profiles even with both
  experimental features compiled. A zero host-call limit traps before writes.

## Source review and limits

The public legacy decode/instance path retains private legacy admission; only
`CapabilityGuest` can construct the privileged module/instance. The constructor
does not expose those objects. Runtime import values now flow through all three
call shapes. Shared close/cancellation checks surround turn execution; memory,
request state, and byte-fuel transitions occur through the bounded mailbox helper
under its lock. `DispatchLease` retains the owner and provides an exit-only
acknowledgement independent of guest terminal delivery and owner handles.

The review covers this composition separately from the earlier standalone
mailbox review. It adds no claim about dynamic strict-JSON validation, grants,
native I/O, native bridge copies, process quotas, counted registries, scheduling,
C APIs, executor admission, activation, or release authority. `post_trusted`
accepts opaque bytes by design; the tests intentionally use opaque arguments and
completions. The root-owned `vm/src/capability_ffi/**` follow-on is excluded.

Source review confirms the documented infallible `Arc`/standard mutex allocation
and core interpreter allocation limits; general OOM recovery, no-unwind behavior,
and poison recovery are not qualified here. The author's allocator measurements
remain author evidence. These tests neither instrument allocation-copy delay nor
exhaust all concurrent schedules. The active-turn cancellation test depends on
ordinary host thread scheduling and retains the published turn/fuel ceilings.
Deadline checks use the real monotonic clock and a short normal wait, without
clock replacement. No devices, cross builds, endpoints, publication, or GA gates
were run or passed by this review.

## Preserved initial harness errors

The first preliminary debug run passed six tests and failed two due to review
fixture mistakes: an above-ceiling `u64::MAX` fuel setting was rejected, and a
4096-byte argument range overlapped the original token output. The corrected
tests use the published default fuel ceiling and a disjoint token address.
`initial-harness-adversarial.rs`, `initial-harness-receipt.json`, and
`preliminary-debug.log` preserve the original source, commands, and failures.
An initial unused import warning was removed. These were not implementation
defects or passing qualification. That preliminary working-tree export included
an unwired root-owned `capability_ffi/ranges.rs`; it was never called or reviewed,
and final frozen exports explicitly exclude it. Successful intermediate runs
with fewer tests are preserved separately from the final ten-test evidence.
