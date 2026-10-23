# Host layout, heap and process RSS observations

The unchanged eager interpreter representation is expensive enough to require a layout decision before a full Swift profile. Fourteen isolated host probes passed against immutable VM revision `64123c509e861ddd522631b293eadebdaca11341`, without raising any production ceiling. The actual FieldLog module was neither admitted, decoded nor executed by the owned VM in this experiment. [The proposal](PROPOSAL.md) is a review artifact, not a new profile or permission to expand existing profiles.

## Reproduction and provenance

```sh
python3 -B compiler/experiments/profile-budget/layout/run.py --name UNIQUE_LABEL
```

The runner requires a fresh output label, Python 3.12 or later, installed Rust and Darwin `/usr/bin/time -l`. It exports the frozen VM and contracts from Git, adds two `cfg(test)` observers and the independently authored measurement module, and builds a release unit-test executable in ignored local output. It verifies every other frozen VM file and every measurement source hash. No working `vm/` file is edited. Fixture generation runs in a separate process, so builder allocations do not enter measured phases.

The final [receipt](evidence/2026-10-22-observed/receipt.json) records exact command arguments, exit codes, full stdout/stderr identities, tool identities, fixture identities, the immutable export and the measurement source manifest. Recorded host: macOS 27.0.1 arm64, Rust/cargo 1.99.0. Model selection: `gpt-6.1-sol`, `xhigh`.

| Identity | SHA-256 |
| --- | --- |
| Frozen VM/contracts archive | `6547c3562bd8918650f7c3bea38817601724c53ab031261b0e48a879d7329280` |
| Measurement source manifest digest | `f90d22f55a71a15aea841c31f59e70adf18ea6bfb623f2c6f8b3e155deb7e314` |
| Rust probe source | `a7134555c4f313053974fe5ab7902b0eba2736bc635fb181ea3d0a5b7fc21e0e` |
| Observed release test executable | `706220071c421dc5690734c3d6cd1f0b82f4a7bb3de6c524277f59f702fa1cd6` |

Earlier output-marker/parser and instrumentation iterations are preserved only under ignored `local/layout-*/superseded-evidence/`. The committed `2026-10-22-observed` receipt is the final run.

## What is measured

The test-only global allocator wraps Rust's `System` allocator. It directly records current and maximum requested live bytes and allocation counts after the phase baseline. It includes successful `alloc`, `alloc_zeroed`, `realloc` and `dealloc`; it does not measure allocator metadata, native library allocations, or transient internal copies within a system realloc. Phase snapshots occur before JSON formatting. Maximum live byte and allocation counters are observed directly, rather than inferred from end-of-phase totals. They need not peak at the same instant.

Process peak RSS is independently observed by Darwin `time -l`. It includes the Rust harness and native libraries, is not baseline-subtracted, and is neither steady-state application RSS nor an OTA/native difference. Requested capacity may include untouched pages; RSS can therefore be smaller than requested bytes. Freed Rust allocations need not immediately leave RSS. Per-case processes avoid attributing earlier case allocations to later cases. No timing, physical device, app memory-pressure, energy or full Swift performance claim follows.

All byte values below are exact bytes. One MiB is 1,048,576 bytes. Peak allocation counts include the measured process baseline of 46 live Rust allocations.

| Probe | Peak requested bytes above baseline | Maximum live allocation count | Process peak RSS bytes |
| --- | ---: | ---: | ---: |
| Minimal one-function module | 1,378 | 60 | 2,670,592 |
| Read combined source only | 3,445,782 | 47 | 6,062,080 |
| Decode combined source only | 17,078,583 | 62 | 18,710,528 |
| Dense instructions | 10,786,979 | 60 | 12,402,688 |
| 2,048 small functions | 476,082 | 2,107 | 3,293,184 |
| Branch-table payloads | 10,327,642 | 560 | 13,320,192 |
| 64 active guest frames | 4,479,134 | 311 | 7,208,960 |
| 1,024 mutable globals | 42,166 | 61 | 2,785,280 |
| 65,536 table entries | 787,766 | 62 | 3,571,712 |
| Active data, source dropped | 7,341,366 | 62 | 13,254,656 |
| Active data, source retained | 10,487,147 | 62 | 13,221,888 |
| Dense code plus active data | 17,827,030 | 62 | 22,921,216 |
| One retained public C ABI session | 21,273,452 | 63 | 22,921,216 |
| Sixteen retained public C ABI sessions | 288,687,542 | 258 | 256,851,968 |

The minimal fixture has a void `run` function containing `end`; its name `empty` does not mean an eight-byte module. The table probe selects existing table-memory-v3; other probes use existing integer-v1. No imports are present. Every executing instance returns void successfully. Source-only, decode-only and session-retention cases intentionally perform no guest invocation. These are representation and retention probes, not standards or differential execution qualification.

## Layout and retained payloads

Measured native sizes are specific to this Rust/compiler/target combination; Rust's default representation is not a stable C layout.

| Native type | Size bytes | Alignment bytes |
| --- | ---: | ---: |
| `Op` | 32 | 8 |
| `Instruction` | 40 | 8 |
| `Function` | 64 | 8 |
| `Module` | 424 | 8 |
| `Signature` | 32 | 8 |
| `Value` | 16 | 8 |
| `Type` | 1 | 1 |
| Execution `Frame` | 88 | 8 |
| Execution `Label` | 32 | 8 |

Inline type size excludes heap-owned vector payloads. The dense fixture has 199,999 instructions in 300,034 source bytes, but its instruction vector has 262,144 slots, reserving 10,485,760 bytes. Multiplying instruction length by 40 would give only 7,999,960 bytes. The 2,048-function fixture allocates four instruction slots per one-instruction function: 327,680 bytes of code capacity, plus function and other metadata. The branch fixture has only 2,001 decoded instructions but also 8,192,000 bytes of branch-label vector capacity; an instruction-count limit alone is not a decoded-heap budget.

The 604-byte frame fixture contains 64 functions, each with 4,096 i64 locals, calling the next until all 64 guest frames are active. Decoded local-type capacity is 262,144 bytes. Instantiated live requested bytes above baseline are 277,150; invocation briefly raises the maximum to 4,479,134 and returns to 277,150. The additional observed peak is 4,201,984 bytes, dominated by the 262,144 live `Value` local slots (4,194,304 bytes), plus frame/control storage. This is a measured maximum for this fixture, not the maximum of all legal combinations of frames, operands and controls.

The data fixture carries 3,145,728 active data bytes and declares exactly 64 memory pages (4,194,304 bytes). After decoding, retaining source and the module uses 6,292,699 bytes above baseline. Dropping the caller source frees exactly 3,145,781 bytes, leaving 3,146,918. Instantiation adds 4,194,328, reaching 7,341,246 live requested bytes. The module retains its active-data vector while the instance copies those bytes into writable linear memory. Retaining the caller source through instantiation reaches 10,487,027 live bytes. Therefore source, retained segment payload and mutable memory are separate allocations in the current model. No physical-page sharing is inferred.

The combined fixture is 3,445,782 source bytes, 199,999 instructions, 3,145,728 retained active data bytes and 4,194,304 linear-memory bytes. Its decoded live allocation is 17,078,300 bytes above baseline with source, or 13,632,518 after source is dropped. Instantiation then reaches 17,826,846. Maximum counters additionally see short-lived validation/execution allocations. All non-session cases return to their measured allocation baseline after their owned values are dropped.

## Retained sessions and aggregate memory

The session cases use the actual frozen public `mixer_vm_session_create_v1` and close APIs, sequentially creating one or sixteen independent combined-fixture instances. Each create succeeds within the unchanged 4 MiB source, 200,000 instruction, 64-page memory and 16-session ceilings. They measure retained instances, not concurrent execution or in-flight close races; the separate [session review](../session-review/README.md) tests the latter.

With the caller source dropped, one session retains 17,827,670 requested bytes above baseline; sixteen retain 285,241,760. Creation maximums, while caller source is still alive, are 21,273,452 and 288,687,542 respectively. The sixteen-session process RSS maximum is directly observed as 256,851,968 bytes, not a sixteenfold RSS extrapolation. Closing every session leaves one allocation of 64 bytes above baseline in both cases. This experiment does not attribute that residual allocation or claim exact return to baseline. It does establish that the large per-session payload allocations are no longer live according to the allocator counter.

A session-count ceiling does not by itself impose an acceptable aggregate memory ceiling for a much larger future profile. Creation, active execution, old/new activation overlap and destruction in progress all need explicit aggregate accounting before such a profile can be approved.

## Actual FieldLog arithmetic, not full-module execution

The compiler experiment's smallest candidate is identified in [its immutable receipt](../evidence/2026-10-22-qualified/receipt.json): 52,008,982 raw bytes, 18,852,048 gzip9 bytes, 79,837 defined functions, 6,505,962 body instructions, 37,712,864 active data bytes, and 584 initial pages (38,273,024 bytes). These quantities are metadata/Node model observations from the prior experiment. They do not authorize owned execution.

Applying the measured eager layout to those counts gives these estimates:

| Term | Arithmetic bytes |
| --- | ---: |
| Instruction length × 40 | 260,238,480 |
| Function length × 64 | 5,109,568 |
| Retained active-data copy under the current model | 37,712,864 |
| Initial mutable linear memory | 38,273,024 |
| Minimum sum of those terms | **341,333,936** |

The instruction term is about 248.18 MiB; the sum is about 325.52 MiB. These are arithmetic lower bounds under the current eager layout/copy model, not a measurement of a full Swift Rust module's heap or RSS. They omit source retention, excess vector capacity, branch payloads, locals, signatures, globals, tables, indices, allocations and execution frames. A naive sixteen-independent-instance extrapolation of that sum is 5,461,342,976 bytes; it is an estimate, not a measured allocation or RSS. Sharing immutable module representation could change that multiplication, but is not implemented or qualified here.

The largest actual function body is 61,994 wire bytes. Wire byte length is not decoded instruction count, vector capacity or complete cache-entry size. No cache can be admitted from that value alone.

The complete model executable remains 15,706,320 gzip bytes over 3 MiB (5.9929 times that amount). This is not the plan's representative-change p95 patch metric. The prior Node oracle observes 625 pages after the corpus (40,960,000 bytes); neither that observation nor the initial 584 pages is an app RSS or OTA/native memory difference. Full Swift/ICU semantics, all required runtime bytes, debugger/source-map support, 34 unsupported WASI imports, actual owned execution and the physical performance/operational gates remain open. Phones were unavailable by user instruction; no device attempt occurred.
