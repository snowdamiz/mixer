# Full-Swift list and editor spike

The Swift 6.3.3 reactor completes the list and editor journey in the owned
Mixer VM on arm64 macOS with the existing 256-frame UI geometry. S2a and S2b
still need platform qualification and startup and memory measurements.

## Owned VM replay

Use the pinned tools listed below. From the repository root, run both
diagnostics with fresh output names.

```sh
python3 -B compiler/experiments/swiftui-full-guest/replay.py owned-swift633-64 --owned-ui-only
python3 -B compiler/experiments/swiftui-full-guest/replay.py owned-swift633-256 --owned-ui-only --owned-ui-256
```

Each command builds the base reactor once. It gives the same Wasm file to
`validate_swift_ui` and to the Rust-only `validate_swift_ui_6_3_3` entry.
The legacy validator returned `swift_import_count` in both attempts, as in
the original spike at `21efd610d6aef2cca22b0d22ce91fe5709c28e32`.
The diagnostic checks the exact 32 import names, their order and their
Preview1 signatures. The sequence omits `fd_filestat_set_size` and
`fd_tell` from the legacy 34. Both validators use the same UI exports,
opcode policy and validation limits. The default validation budget allows
64 MiB for source, 16 MiB for metadata, 1 MiB for scratch, 512 million
work credits, and 120 seconds. The owned replay grants monotonic time
and secure random.

### The default UI run stops at frame 65

The new entry validates 53,265 bodies and 4,241,159 instructions. The owner
constructs successfully and `_initialize` returns at a peak depth of 10.
The first frame call then returns `swift_frame_depth` at function 23354,
byte 4008864. It requests 65 frames against a limit of 64 and produces no
snapshot. At refusal the run had used 354,670 fuel and made six host calls.

### The existing 256-frame geometry completes the journey

The second run selects 256 frames, 256 active pins, and 256 cache entries
through `SwiftRunBudget`. All other budgets use their defaults, including
100 million fuel, 64 million cache work credits, 768 memory pages, and a
30-second run deadline. The caller uses `PersistentSwiftUIOwner::construct`
with its cumulative limits.

| Owned VM operation | Elapsed | Fuel used | Host calls | Peak frames |
| --- | ---: | ---: | ---: | ---: |
| Initialize and return the first snapshot | 468 ms | 1,719,469 | 6 | 95 |
| Load the list | 1,744 ms | 7,714,347 | 12 | 53 |
| Open row 527 | 740 ms | 4,469,553 | 2 | 55 |
| Reject a blank save | 41 ms | 193,843 | 2 | 55 |
| Save the Unicode edit | 1,148 ms | 6,519,560 | 2 | 82 |
| Reopen the edited row | 69 ms | 295,329 | 2 | 67 |

The replay checks all six snapshots and the final saved title, UUID and
date. The owner used 20,912,101 fuel, 24,599,357 cache work credits and
26 WASI calls, with zero WASI failures. Guest linear memory grew from 40
to 61 pages, or 2,621,440 to 3,997,696 bytes. Peak combined VM
reservations were 47,479,019 bytes. The process peaked at 62,013,440
resident bytes. The cache reached its 256-entry limit.

On the successful run, validation took 1.226 s and construction took
5.18 ms. These are single observations from a busy macOS 27.0.1 host
with 15 logical CPUs. They show that the workload runs and that startup
and turn time need qualification. The Section 20.2 targets require
relative app measurements on each platform. This run supplies no p95,
app memory baseline, installed profile caps, or signed activation result.

Both attempts used VM tree `d3f0d6c10bf38c46299314a5aff319f18785dc2c`,
Swift 6.3.3 and Rust 1.99.0. The rebuilt reactors differed in digest and
had the same 12,718,666 raw bytes, 3,609,971 gzip bytes and validation
observations. The receipts contain the exact artifact digests, source
revisions, commands, timings and counters. Both owners closed with zero
live reservations and tickets. The runner deleted both work directories
after it observed terminal process groups.

| Attempt | Receipt in the implementation worktree |
| --- | --- |
| Default 64-frame geometry | `verification/local/s2-owned-swift633-01/receipt.json` |
| Existing 256-frame UI geometry | `verification/local/s2-owned-swift633-02/receipt.json` |

The 12 tests in `swift_reactor_validation` and the existing fixed-34
UI export test `r3702_sealed_ui_entries_follow_validated_exports` passed
in release mode. See `verification/local/s2-swift633-legacy-controls/receipt.json`.

## Original compiler and Node replay

The original Swift 6.3.3 WASI SDK build emitted the same ordered 32-import
shape for the command and the reactor. Both completed the journey in
Node WASI on macOS. This replay retains the legacy VM controls.

From the repository root on arm64 macOS, run:

```sh
python3 -B compiler/experiments/swiftui-full-guest/replay.py swiftui-full-guest-replay
```

Use Swift 6.3.3 with the matching non-Embedded `wasm32-unknown-wasip1` SDK,
Xcode 26.6 for the macOS SDK, Rust 1.99.0, Node 26, and Zstandard 1.5.7.
Pass a new output name each time. The script records the exact tools,
commands, source digests, module hashes, and observations in
`verification/local/<name>/receipt.json`. It keeps command logs and removes
disposable outputs when process groups and any acquired reactor owner settle.

## Workload and artifact cost

The spike owns a small offscreen SwiftUI-shaped subset. It generates 1,000
FieldLog-style records. List appearance starts a Swift `Task`, which yields
before loading the records. A row action opens record 527, the editor binds
its title, Save rejects blank input, and Save commits a Unicode edit. The
workspace observes the change through Observation and reopens the saved
FoundationEssentials JSON with the original UUID and date. The macOS
reference imports Apple's Foundation and exercises the same source logic.
The update renames Save and changes validation to reject whitespace-only
titles and cap titles at 100 UTF-8 bytes.

The command runs the whole journey through async `@main`. The reactor
exposes the current experimental UI transport exports and returns six
value snapshots across separate host calls. Its adapter invokes the pinned
single-threaded Swift runtime's cooperative executor for each turn. The
frames are spike JSON, and the host sends fixed fixture events. Product
`MixerSwiftUI`, `UIDocument`, durable storage, and signed activation remain
outside this harness. [Swift 6.3.3 cooperative executor](https://github.com/swiftlang/swift/blob/swift-6.3.3-RELEASE/stdlib/public/Concurrency/CooperativeGlobalExecutor.cpp)

| Build | Base raw bytes | Base gzip bytes | Update raw bytes | Update gzip bytes | Compressed diff bytes |
| --- | ---: | ---: | ---: | ---: | ---: |
| Full Swift WASI command | 12,716,326 | 3,608,772 | 12,716,578 | 3,608,839 | 292,449 |
| Full Swift WASI reactor | 12,718,666 | 3,609,972 | 12,718,918 | 3,609,878 | 659,137 |
| Command with locale-sensitive Foundation control | 53,740,081 | 18,967,546 | | | |

Zstandard reconstructs each complete update byte for byte from its
corresponding base. Both unsigned payloads fit below 3 MiB. The experiment
has zero assets and one source change. The signed envelope, installed app
size, and p95 over the dogfood corpus remain pending. Independent rebuilds
had small differences in compressed size and produced different hashes.
Use the base and patch from the same build pair.

The linker maps show FoundationEssentials, Swift Concurrency, and
Observation in both lean builds. The locale-formatting control separately
links FoundationInternationalization and the Foundation ICU data object.
No ICU archive contributes to either lean module.

## Measurements and platform handoff

Both approaches ran five fresh Node processes per variant, alternating
base and update within each approach. The receipt reports the median and
range for Node read and compile, instantiation, and the timed guest work.
It checks the command result and the reactor's six snapshots on each sample.
The command begins with 2.50 MiB of Wasm linear memory and ends with
2.81 MiB. The reactor begins with 2.50 MiB and ends with 3.81 MiB. These are
linear-memory sizes, with the separate Node process peak RSS in the
receipt. The host was busy. These observations describe the host replay.
The original Mixer replay stopped at import admission. The owned VM
diagnostics above measure host instruction fuel, call depth and turn time.

In the updated reactor, Node read and compilation took a median 17.26 ms
(15.81–21.08 ms). The first frame turn took 11.49 ms (9.54–13.93 ms),
the asynchronous list load took 2.09 ms (1.94–3.57 ms), and the Save turn
took 6.29 ms (4.86–8.29 ms). Each reactor journey made 26 WASI calls:
22 clock calls, three random calls, and one environment size call.
The Node turn timings include the Wasm call and exclude the subsequent
host decode and any platform rendering.

S2a and S2b still need an independently reviewed versioned VM profile
and the platform checks below.

| Spike | Current observation | Root-owned platform check |
| --- | --- | --- |
| S2a iOS | The owned reactor completed on macOS. iOS VM execution and budgets are pending. | Build the iOS 17.0 Simulator VM and app with the new profile fingerprint and the verified reactor base. On the oldest supported 17.x runtime, replay the fixture through the iOS engine and compare cold bundled and signed-activation launches. |
| S2b Android | The owned reactor completed on macOS. Android VM execution and budgets are pending. | Build the API 28 NDK VM and Android host with the new profile fingerprint and the verified reactor base. On an API 28 emulator, replay the fixture through the Android engine and compare cold bundled and signed-activation launches. |

For each platform, capture signed transfer and bundled app bytes, the
time to first accepted frame, steady and peak app RSS, turn duration,
instruction fuel, host calls, and maximum call depth. Verify that the
fixture completes and the owner closes. Keep the Section 20.2 startup
and added-memory budgets pending until the corresponding measurements
exist. Section 24.6 reserves any Embedded fallback for the owner's decision.
