# Independent guest UI contract review

Reviewed by the guest UI design lane, 2026-10-23. Result: consistent with the
root-accepted design after the corrections below. The accepted design bytes
and their acceptance seal were not changed.

Final reviewed bytes:

- `contracts/guest-ui-event-v1.json`:
  `34180d46e20e403c9cd3f3aa1584a7b6d0e67e94900267c7aa51c87116566024`
- `vm/include/mixer_vm_guest_ui.h`:
  `d8d8217b900662e77787a8729f5c1cfe096b0df25ffe39e289f89d69fc156ab5`
- Accepted design:
  `7b7b3a8a70757349330b1f7d898be4db297b888b9cf606464e210494905a44f4`

The original checker is `check_contract.py`; final output is
`final-candidate-3b/receipt.json`. It records 55 passing static checks, exact
commands, Python/Git/Clang versions, source revision/tree, captured file
digests, and the reviewed contract/header copies. The two original C/C++
translation units check only the declared function type, include guards,
optional ABI version, and inherited host LP64 structure sizes. Both passed
Apple clang 21.0.0 syntax-only checks under C11/C++17 with warnings as errors.

## Corrections made by root before this result

The initial candidate omitted fresh private host creation on rebinding and
exact exchange/issuer scoping of old native action closures. Root added the
`rebinding` requirement so an old callback cannot be rebuilt against a new
host whose revision/node generation happens to match.

Root added the accepted single native attachment/probe requirement, including
rejection before a second engine host, probe, or presentation consumer is
allocated. Multiple native windows remain outside this slice.

The ownership prohibition was clarified to prohibit `DispatchSource` and
external execution sources while allowing the two required data-only typed
wake queues. That is the intended meaning of the accepted design's shorter
word `source`; the design seal remains unchanged.

Root added `wake_finish`: one reader issuance and one simultaneous waiter,
resumption outside locks, pending retirement hint before finished return,
delivery signal before finish, and control-channel finish owned only by the
existing signals handoff. Joining a presentation task now cannot be interpreted
as sufficient while skipping final MainActor retirement.

## Checked source and contract relationships

The three fixed exports, 32-byte unaligned little-endian control header,
`MIU1` magic, bounded UI subset, strict event shape/numeric/UTF-8 constraints,
exact installed dependency/startup reservation, and signed runtime matching
agree with the accepted design. No existing contract or legacy C header hash
changed. The contract's self hash remains a symbolic requirement, avoiding a
literal self-hashing document; the installed dependency receives the actual
hash of the reviewed bytes.

The existing native export helper emits machine code `capability_export`
with no function and offset zero. In the UI validate-only context the checked
Swift classification is `.validation`, status 1,
`.validation(.requiredDefinedExport)`. The proposed helper explicitly reuses
that code for every fixed UI export defect after full module validation. It
does not identify which export or whether it was missing/imported/wrong-kind/
wrong-signature, and the contract does not claim it does. All other module
errors stay in their existing checked domain; report/message substrings play
no part in classification.

Actual existing memory read/write bounds rejection is status 3,
`invalid_arguments`; it is not a distinct out-of-bounds code. The definition
correctly preserves that checked bridge classification and makes any such
failure terminal for a fixed UI composite. Numeric range/overlap checks can
separately produce the new UI `memoryRange` code before C work.

The one shared guard, event-before-wake ordering, capacity through result
consumption, latest-document replacement, fixed counted presentation consumer,
actual task-return join, private issuer identity, private native receipt, and
before/after-intent recovery paths agree with the accepted design. Native
quarantine, actual exit acknowledgment, observation interval, and trusted
milestone rules are preserved as requirements.

## Scope

This is static consistency review of definitions and existing source, plus
host compiler checks of declarations. The new C symbol, guest event decoder,
exchange/wake implementation, UI transport, renderer/probe, signed integrated
flow, and race tests have not been implemented or executed by this review.
No guest module was run and no archive was linked. Static checks do not
authorize an OTA release, establish native preflight correctness, establish
thread/lifetime behavior, or pass a compiler, device, FieldLog, store, customer,
performance/RSS, publication, or GA gate. Phones remain disconnected.
