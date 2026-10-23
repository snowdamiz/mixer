# Rust-only actual-Wasm capability guest experiment

The nondefault `experimental-capability-guest` feature composes the reviewed
bounded mailbox with actual Wasm execution. Its bytes-based `CapabilityGuest`
constructor is an explicit experimental selection context; ordinary Rust
`Module::decode`/`Instance::new`, CLI, C, session and streaming routes remain
Legacy even when all features are enabled. No profile4, C function, registry,
native I/O, strict dynamic completion codec, scheduler or release route is added.
The [implementation contract](../../../docs/experimental-capability-guest-implementation.md)
describes exact startup/wake/import/ownership behavior.

The [2026-10-23 host receipt](2026-10-23-host/receipt.json) pins the source tree
digest `1697111c4821879673950c143d8474667286e8632c6d769239ff402f999274ba`,
source-file manifest, tool versions, exact commands, logs, library hashes and
unchanged public definitions. The working source was unchanged throughout the
checks. Concurrent root-owned, unwired `vm/src/capability_ffi/**` is explicitly
excluded. This is implementation evidence; independent review is separate.

Reproduce from this source with a fresh receipt name:

```sh
python3 -B vm/verification/capability-guest/verify.py --name host-replay
```

The driver prepends `/opt/homebrew/opt/rustup/bin` to PATH and isolates build
outputs in `vm/target/capability-guest-verification`. The qualified host is arm64
macOS27.0.1, Rust1.99.0, Node22.23.3 and Python3.14.8. The receipt contains exact
version strings. Elapsed values are host development observations, not product
performance measurements. No new dependency is introduced; Node remains a
development oracle only.

| Host check | Debug | Release |
| --- | ---: | ---: |
| Default test functions | 91 passed,8 explicitly ignored | 91 passed,8 explicitly ignored |
| All-feature test functions | 162 passed,9 explicitly ignored | 162 passed,9 explicitly ignored |
| Explicit ignored/oracle test functions | 9 passed | 9 passed |
| New guest functions included above | 34 passed | 34 passed |

The 34 new functions comprise27 actual handcrafted-Wasm integration functions,
6 private failure/layout/lifetime functions and1 isolated allocation function.
They cover six typed imports, direct/indirect/exported i32 returns, null and
wrong-signature indirect traps, startup disabled effects, successful-turn-only
dispatch, exact fixed wake, immutable argument snapshots, unsigned/overlap/empty
memory rules, exact byte-fuel and host-call boundaries, quota/token exhaustion,
owner isolation, terminal payload bytes, permanent cancellation/deadline closure,
normal close/drop with ackable tickets, preserved original unwind and negative
poison acknowledgement. Existing default/integer/numeric/table/session/stream
and mailbox suites run alongside these. Nine old development-oracle functions
are explicitly run; they do not constitute an independent capability authority
or complete Wasm standards suite.

Clippy default/all-features with warnings denied, cargo fmt, and offline fixed
payload regeneration parity passed. Twelve generated static JSON payloads bind
the frozen transport contract SHA
`052ebe9fbdc20a41307332086767e7903680bc83ba273c696edf9187be6b6439`
and exact capability schema hashes. Generation is an explicit development
command, never a Cargo build side effect. Tests separately construct and compare
all12 payload bytes and required lengths. The four legacy C smokes pass against
both default and all-feature static libraries; the same12 C symbols are exposed
by both dynamic libraries. Public contracts/headers, ffi/session/float/stream
sources and Profile/Limits/Module/Instance field definitions match their frozen
reference. The decoder/validator/executor hooks are private and tested through
both admitted and rejected APIs; source equality is not claimed for those hooks.

Direct allocation observations agree in debug/release on this host:

| Observation | Requested bytes / calls |
| --- | ---: |
| Fixed Rust values: guest/shared/port/ticket/mailbox | 640/1000/8/32/984 bytes |
| Shared Arc allocation including counters | 1016 bytes,1 allocation |
|214-byte minimal module constructor with9-page memory | 592878 retained bytes,58 allocation events |
|8 maximum argument and completion pairs | 8388608 retained/peak payload bytes,16 allocations |
| Invalid-memory and full-quota rejection | 0 allocation events |
| Ready poll/ack; close/drop/last-ticket ack | 0 new allocation events |
| Failed1024-byte argument snapshot | no token/request published;36-byte Error String allocated afterward |
| Last normal ticket ack, then owner drop | 1024 argument bytes, then1104 owner/synchronization/cancellation bytes freed |

These are System GlobalAlloc requested Layout observations, not allocator usable
size, physical heap/RSS or stack bounds. Constructor live/peak accounting updates
realloc after it returns and does not measure allocator-internal realloc overlap.
Payload intervals preallocate caller buffers and exclude source bytes, linear
memory, decoded core, fixed shared owner and OS/adapter copies. No auxiliary
queue grows with polling/cancellation, and ready delivery has no staging payload.

Forced1016-byte Shared Arc allocation refusal terminates a bounded child with
SIGABRT; the negative transcript is preserved in both allocation logs. The
existing mailbox's first standard mutex lock also has a known64-byte infallible
allocation and its negative OOM child is retained by the all-feature suite.
Legacy core, error Strings, Cancellation and shared Arcs remain infallible
allocation boundaries. This slice does not claim end-to-end OOM containment.
Poison is tested as terminal and ack failure, without recovery or a successful
reclamation claim. Two initial indirect-test expected-code spelling mistakes
were corrected to the unchanged engine trap codes before the final source pin;
the driver also retains its initial repository-root setup error separately.

Trusted native callers must retain an owner/ticket through actual native cleanup
and acknowledge only then. Dropping every owner early is not proof of I/O exit;
there is no native I/O or counted process registry in this slice. Dynamic posted
completion bytes remain trusted opaque bytes, and argument data is not strict
JSON-decoded at this boundary. Cooperative deadlines/cancellation are checked at
instruction/import/turn-return boundaries, without preempting an in-progress
allocation/copy. A return-boundary error has no active function location.

Independent adversarial review, physical deployment tests, Swift async/strict
native bridge integration, real capability grants/I/O, process-wide session and
native-exit capacity, automatic scheduling, full Swift/FieldLog admission and
execution, immutable published consumer packages, release/store/operations and
GA gates remain open. No phone command was attempted. Existing FieldLog source,
artifact and all profile ceilings remain unchanged; no full FieldLog artifact
was admitted or executed in these tests.
