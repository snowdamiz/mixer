# Independent C facade, UI-entry and progress transport review

Decision: **no blocking finding identified for this private C stage**. This is an
independent host state-machine and Android object/link review, not Android signed
UI support, runtime/display qualification, or final integration acceptance.

The review binds the actual C/header/test inputs and the implementation owner's
receipt to `receipt.json`, `source-before.sha256`, and `source-after.sha256`.
The accepted contract hash is checked against
`verification/android-binding-contract-acceptance.json`. Every entry in the
owner's source manifest was independently verified before execution. Source
revision was `76a3254f1e974fbce144e6887b6d73c243f68243`; the selected review input
tree digest was
`cfd1fe925bb1855f8943f3a7371df6198a830f7126e25f6b99050016674d2275`.
The selected inputs stayed unchanged throughout all checks.

Reproduce from the repository root:

```sh
python3 verification/android-facade-transport-review/verify.py
```

## Executed evidence

| Suite | Debug | Release | ASan + UBSan | TSan |
| --- | ---: | ---: | ---: | ---: |
| New independent probes | 11 | 11 | 11 | 11 |
| Original unchanged transport tests | 26 | 26 | 26 | 26 |
| Prior unchanged independent probes | 9 | 9 | 9 | 9 |
| Implementation owner's facade probes | 27 | 27 | 27 | 27 |

All 292 host case executions passed with strict compiler warnings as errors.
No failing run preceded these results. The original 26 and prior 9 test source
hashes match the frozen implementation receipt and were not edited. Every case
runs in a new process with a bounded timeout; the actual command, exit, version,
output path and tool input hashes are recorded. The review authored only this
new verification directory, without production edits, fixes, or commits.

The actual `transport.c` and `platform_android.c` also compiled with the installed
official NDK r27d API30 arm64 compiler. A no-undefined link rejected all missing
fixed hooks, a second rejected missing `mxuit_progress` alone, and the inert
link-only hook probe linked successfully against `libandroid`. Product object
symbols contained no test controls; ELF headers, program headers, dependencies
and artifact hashes are recorded. No dependency or platform capability was added.

## Independently derived adversarial schedules

| Probe | What was exercised |
| --- | --- |
| `exact_active_drain_matrix` | Actual PRESENT and RETIRE drains reject wrong facade, owner, waiter and kind before the valid exact lease; a lease on one facade blocks CLEANUP on another. Nested error callbacks preserve both fences, byte, hook counts and fault state. Completion cannot reuse the consumed drain identity. |
| `nested_reject_before_read` | Cross-facade INGRESS/CLEANUP rejection and mismatched leave/validate cannot release the global lease. An injected read failure survives two nested callbacks, proving rejection precedes read/fault handling. Leaving creates demand without advancing a fence. |
| `completion_cleanup_needs_new_fence` | RETIRE completion itself acquires and leaves a later CLEANUP lease. Its serial updates both facade and endpoint and prevents reclaim until the subsequent callback fences the later entry. |
| `terminal_capacity_retry` | Failed terminal allocation at full owner capacity does not consume terminal-once. After a real owner retirement/reclaim, exactly one successful terminal allocation and retirement is possible; later terminal allocation rejects and the old facade remains stale after reuse. |
| `full_reuse_during_progress` | A worker resumed during a held process-only healthy progress hook reclaims all 16 old endpoints/facades, reuses all 16 records and requests replacements before the callback resumes its scan. Only fresh exact identities execute; no stale slot pointer or tail frees replacement records. Idle creates no new byte. |
| `concurrent_fault_fanout` | Sixteen worker requests race a single injected pipe failure. The first sticky fault publishes exactly once outside the C lock and wakes all 16 fixed native observer cells without any Looper dispatch. All endpoints/facades remain closing and counted. |
| `fault_races_healthy_progress` | A worker creates the first pipe fault while a healthy process-only progress hook is held outside C locks. Both scalar updates are delivered, the first fault survives the healthy hook's later return, and no owner helper executes after the fault. |
| `all_native_tails` | A separate installed UI thread holds an active entry, then a completion, then a platform-return tail. Trusted consumer join can latch, but every reclaim remains BUSY through each tail. A worker cannot impersonate the UI thread to validate, leave, or fence. Only a later callback releases scalar capacity. |
| `all_bits_entry_fence` | An actual CLEANUP lease with serial `UINT64_MAX` pins a successfully retired endpoint until the full unsigned serial is fenced; no signed comparison truncates it. |
| `active_entry_fault_unwinds` | Worker fault during an active ingress lease does not allow nested callback progress or reclaim. Validation reports the fault, exact leave still clears the active lease, and the unfenced records remain quarantined/counted. |
| `lost_wake_registration_orders` | Native observer sequence checks cover healthy progress before registration, after registration, and before the post-registration reclaim retry. This exercises the C notification/reclaim interaction; it does not prove the future Swift continuation implementation. |

## Source audit

The C record/lock transitions were read independently against contract sections
4, 5, and 7, rather than accepting test count alone:

- `transport.c:210` and `transport.c:226`: facade and endpoint allocation are
  atomic under the C lock, issue independent monotonically increasing IDs, keep
  terminal issuance sticky only after successful allocation, inherit the current
  facade entry serial, and create no progress hook, new fault or pipe demand.
- `transport.c:270`: direct entries validate argument shape and the installing
  pthread, enforce one global active entry, and require exact live linked
  owner/waiter/active drain kind for PRESENT/RETIRE. `transport.c:318` clears only
  the exact lease and schedules demand; it never advances a fence.
- `transport.c:329` and `transport.c:363`: scalar reclaim checks are under the
  same C lock. Endpoint reclaim requires retirement, explicit actual-join
  assertion, no waiter/helper/completion, callback fence and facade-entry fence;
  facade reclaim additionally requires closing, no endpoint and no active or
  unfenced facade entry. Acquire/reclaim paths have no hidden progress hook.
- `transport.c:380`: readiness/fd/thread and nested callback/global active-entry
  checks precede reading the byte, event failure, epoch changes, progress and
  owner scans. Successful callback entry publishes fences outside the C lock
  before looking at slots. Active/completing state pins each scanned slot across
  its fixed hook; a later nonreentrant callback proves prior callback return.
- `transport.c:50` and `transport.c:60`: fault creation latches the first code,
  closes all live records, consumes the one publication bit under the mutex, then
  calls process-only progress after unlocking. The publication return tail uses
  only copied scalar values and performs no owner read. Healthy and fault hooks
  may overlap, so a later binding must merge max fences and sticky first fault
  exactly as the accepted contract requires.

## Pending integration evidence

The host ALooper symbols are a small driver for the real platform wrapper; no
Android Looper, Java main-Looper comparison, JNI entry, widget, draw observation
or display health executed. The hook observer cells use pthread synchronization
and do not implement or qualify Swift continuations, Tasks or the authoritative
join permit. `consumer_joined` remains a trusted caller assertion; actual
`Task.value` and resource alias/destructor proofs belong to the later binding.
C facade reclaim assumes its separate exact final Swift cleanup receipt and
releases only scalar accounting. The after-leave Swift/JNI/Java return tail must
still be audited and run in Android integration. No C result authorizes release.

ASan leak detection was disabled; no memory-use, leak, energy or performance
claim is made. No emulator or physical device executed. Phones remain
disconnected; there was no device discovery, run, or reconnect request. Signing,
publication, customers, operational acceptance, FieldLog immutable-package
qualification, and GA gates remain outside this receipt. Android signed UI stays
unsupported.
