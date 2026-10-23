# Actual FieldLog full Swift reactor diagnostic

The [final receipt](evidence/2026-10-23-qualified/receipt.json) binds the actual
FieldLog model revision `1587d2d4f02ab2dad9914df97f878727dd622296` to a full Swift
6.3.3 static reactor. After exactly one Node WASI `initialize` call, both calls to
`mixer_fieldlog_corpus_v1: () -> i32` returned zero and emitted the complete
unchanged 11-field observation object. Each object equals both the newly built
unchanged native command and the newly built unchanged full Swift Wasm command.
The frozen prior qualification observation also matches. Node remains a trusted
development oracle; this does not execute the owned VM.

Reproduce from the mixer root with a fresh bounded name:

```sh
python3 -B compiler/experiments/fieldlog-reactor/run.py --name FRESH_NAME
```

The official installed Swift toolchain/SDK, Xcode 26.6 SDK, existing Node platform
tool, immutable FieldLog Git commit and existing owned inventory executable must
exist at the paths in `run.py`. There are no downloads or new dependency graphs.
The runner compiles the single immutable `Workspace.swift` directly into separate
native and Wasm `FieldLogModels` objects/modules. It does not reuse an existing
model object. Source archives, exact diagnostic source snapshots, modules,
objects, full artifacts, linker map and extraction trace are retained in ignored
`local/`. Per-command stdout/stderr and receipts, including timeouts or failures,
are retained in `evidence/`. Installed tools remain trusted; their identities and
selected SDK/archive hashes are not complete supply-chain or reproducible-build
attestation. Link paths can affect artifact bytes; a fresh path is not promised
to reproduce the recorded hash.

The test-only wrapper preserves the original 2,675 corpus-body bytes and all
361 Receipt-declaration bytes exactly. The original corpus starts at line 20;
the wrapper body starts at line 26. Every original assertion, Unicode string,
date, report check and JSON print remains in that private throwing function.
Each call creates its own local Workspace. Repeated equality does not establish
persistent feature state, an update transition, or a production feature ABI.

The C-compatible boundary catches Swift errors and returns `1`; success returns
`0`. After a successful corpus call, it explicitly calls official libc
`fflush(nil)` and returns `2` if flushing fails. This direct WASILibc import is
only output-delivery behavior for this test boundary. No additional declared
WASI import appeared: both the first and corrected reactors have the same 34
preview1 function imports. Swift traps/precondition failures are not Swift errors
and do not become a success status. A native executable runs the actual shared
boundary helper with one deliberately throwing closure, then a successful
closure, and calls the full exported wrapper twice.

The [first failed run](evidence/2026-10-23-first/receipt.json) is retained. Both
calls returned zero, but the second original print stayed in libc's buffer
without command-process shutdown. Only one observation object reached stdout,
so qualification failed. The explicit boundary flush fixes this without changing
the corpus body. The intermediate corrected run is also retained separately;
the final run additionally compiles retained immutable wrapper snapshots and
cross-checks the original descriptor reader with Node's declared inventory.

The supported official driver selects `crt1-reactor.o`, `--entry _initialize`
and normal static Swift/Foundation/ICU archives. The final
[descriptor inventory](evidence/2026-10-23-qualified/descriptors.json) resolves
every import/export through its actual Wasm type index and records complete
scalar parameter/result signatures. The only exports are `memory`,
`_initialize: () -> ()` and `mixer_fieldlog_corpus_v1: () -> i32`; there is no
Wasm start section or `_start` export. The initialization observation contains
seven WASI calls, followed by 2,522 and 2,513 calls in the two invocations. The
oracle uses platform secure randomness, fixed arguments, an empty environment
and no filesystem preopens. Those observations do not grant any product
capabilities or excuse uninvoked declared imports.

| Final exact artifact/resource observation | Value |
| --- | ---: |
| Reactor raw bytes | 53,777,114 |
| Reactor SHA-256 | `24d85729a659ff3e5fc6f0517709afbb68b371a41829e90785dabd48e0620994` |
| gzip9, mtime 0 bytes | 18,976,211 |
| gzip SHA-256 | `e22a8226908ef68170ac94267978b4b436c45764bc591451ef16161d6dbd52ac` |
| Types | 493 |
| Imported / defined functions | 34 / 79,832 |
| Globals | 5,273 |
| Inventoried instructions | 6,505,659 |
| Table initial/maximum entries | 46,713 / 46,713 |
| Memory initial pages / declared maximum | 584 / absent |
| Initial linear memory bytes | 38,273,024 |
| After first / second invocation bytes | 40,960,000 / 41,025,536 |

The [binary structure](evidence/2026-10-23-qualified/structure.json),
[link attribution](evidence/2026-10-23-qualified/link-attribution.json), exact
driver commands, SDK inputs, artifact hashes and original source-map hashes
are retained. The complete compressed artifact exceeds 3 MiB. These are one
artifact and before/after linear-memory extents, not p95 sizes, peak allocation,
physical RSS or device measurements. `_initialize` performs runtime work and
the final memory values do not establish leak freedom or persistent state.

The original strict `mixer-integer-v1` validator rejects the final bytes at the
unchanged module-byte ceiling. The existing table-memory-v3 inventory completes
without admitting the module. Its opcode inventory is diagnostic, not complete
type validation. Current general inventory does not expose maximum nesting and
the existing per-body experiment tool pins the older command artifact's byte
length; this slice records nesting as unmeasured instead of widening a limit or
creating another scanner. The optimized stripped module retains only the
`.swift1_autolink_entries` custom section, and source debugging is unqualified.

Three small Python checks reject source/Receipt/assertion drift, incomplete or
duplicate JSON observations, wrong observation values/types, truncated
descriptors and invalid signature references. They passed alongside the actual
compiled native throwing-boundary check and full native/command/reactor parity.
No full W07, owned full Swift execution, persistent feature/UI/effects, device,
30 MiB RSS, immutable published-package dogfood, store, reviewer or GA gate is
marked passed. Phones remain disconnected. No product source, VM, contracts,
SDK or root status/gate documents were changed by this lane; root integrates
the bounded evidence.
