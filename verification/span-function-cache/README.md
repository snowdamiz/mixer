# W08 bounded decoded-function cache host evidence

The root-approved contract is `docs/span-function-cache-design.md`; its accepted
SHA-256 is frozen in `accepted-design.json`. Production is Rust-only and gated
by the nondefault `experimental-function-cache` feature, which depends on the
complete streaming validator. The cache consumes a sealed `ValidatedSpans`
without copying its source. It provides no guest invocation/executable conversion.

Reproduce from the repository root with a fresh receipt name:

```sh
python3 -B verification/span-function-cache/run.py --name FRESH_NAME
```

The runner uses installed Rust/Cargo 1.99.0 and Node as a platform development
oracle, Cargo offline, and the existing
`vm/target/stream-validation-verification` target. It creates no package graph or
external source/fixture/dependency download. Initial development failures and
the narrow static-error Clippy allowance are recorded in
`development-diagnostics.md`.

The sealed `2026-10-23-host/receipt.json` records exact source/tool/command/output
identities at HEAD `b02b76f40133677f20f87272823aa1a8911a3fbf`, with dirty VM
source manifest SHA-256
`bdbb303375c02abde79556475d930b42bcc889b0d8a3f6b0fa0a556867b9f5c4`.
All 87 VM input files remain identical before and after the receipt. The exact
76-file isolation comparison against `ac2d2b6` strips only the approved new feature line
from Cargo.toml and the gated cache declaration from experimental/mod.rs.

| Host check | Result |
| --- | --- |
| Default debug | 91 passed; 8 development oracles not selected by that command |
| Default release | 91 passed; same 8 unselected |
| Cache feature debug | 122 passed; 9 development oracles not selected by that command |
| Cache feature release | 122 passed; same 9 unselected |
| Explicit feature development oracles | All 9 passed; no oracle left skipped in this receipt |
| Format | Passed |
| Default and feature Clippy, all targets | Passed with `-D warnings` |
| Existing source/test/header/profile/Cargo.lock isolation | 76 exact baseline files matched after only two approved snippet removals |

The 14 new checks include three internal tests, nine public integration tests,
one separate-process allocator test and one compile-fail lifetime doctest.
They compare every supported opcode shape, absolute offset, local/constant and
structured target against frozen private IR; exercise recursive/indirect frame
pin retention without executing guests; cover LRU/byte-pressure/pin exhaustion,
oversize retention, imported/invalid function indices, source ownership/moving,
wrong-owner recovery, stale tokens, identity/nonce/statistic exhaustion, exact
and every smaller work-credit boundary, canceled hits/misses, zero-count locals,
and invalid uncalled code before authority is constructed.

The allocator probe reports two constructor allocation calls and three mixed
entry construction calls, with no reallocations. Failure and cancellation at
every constructor/entry allocation ordinal return no partial entry/pin and free
partial allocations. Hits and releases allocate nothing, including when an
allocator failure is armed. Exhausted work still permits explicit release.
The mixed entry requested 4,277 payload bytes, plus 1,248 requested constructor
heap bytes; its conservative cache peak reservation was 15,605 bytes.

| Independently authored boundary fixture | Requested cache heap peak | Resident entry payload | Cache reservation peak | Total reservation peak, including retained proof |
| --- | ---: | ---: | ---: | ---: |
| 4,096 locals | 5,272 | 4,136 | 15,352 | 24,140 |
| 200,000 instructions | 8,001,136 | 8,000,000 | 8,011,216 | 8,211,812 |
| 200,000 branch targets | 801,336 | 800,200 | 811,416 | 1,012,023 |
| 128 controls | 11,336 | 10,200 | 21,416 | 22,392 |

Requested heap observations are actual allocator request sizes on macOS arm64;
reservations also cover fixed/cache/pin/slot state, both bounded decoder pass
states/control arrays, two readers, the fixed 64-slot eviction plan, meter,
static failures and bounded scalar temporaries. These are explicit reservation
models, not compiler stack-layout measurements, allocator usable sizes, RSS,
physical device results or maxima over every admitted combination. The largest
observed heap peak in this fixture set does not establish an application memory
budget pass. Resident bytes already include the pinned subset. The cache counts
one complete construction payload concurrently with all retained resident
entries; no leaked/forgotten pin releases its reservation accidentally.

Cancellation probes deterministically cancel at native allocation boundaries,
and each traversal/emission/cache operation checks cooperative cancellation
before charged work. Work-boundary tests traverse the full miss path including
second-pass construction. This is no wall-clock preemption guarantee; an
asynchronously canceled instruction-level timing bound was not independently
measured.

Independent review owns `verification/span-function-cache-review/`. Source review
already tightened the final unpublished-entry cancellation path to explicitly
drop its payload before releasing its reservation. The final receipt includes
that fix. Independent review completion is separate evidence.

No C/native archive or binary symbol rebuild was run for this lane. Existing
Rust FFI/session tests and exact header/source isolation passed; they do not
substitute for a native consumer or binary C ABI receipt. Execution bridge,
actual recursive/indirect guest execution, trap/close integration, WASI, full
Swift/resource admission, FieldLog semantics, aggregate session memory admission,
physical iOS/Android, complete standards/fuzz/security suites, immutable
published-package consumption, OTA and GA remain pending. Phones stayed
disconnected; no device tool was invoked. This lane made no commit or push.
