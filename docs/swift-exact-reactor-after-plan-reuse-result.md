# Exact full Swift reactor after decode-plan reuse: result

The one selected full host attempt fails Corpus 1 at the original CacheWork
ceiling: `Cache / WorkExhausted / swift_run_work / CacheWork`, attempted
64,000,001 / 64,000,000, function 23610, offset 4154038. Validation and Initialize
pass; Corpus 2 is unrun. The causal failure records 23,358,291 instructions and
4,840,104 elapsed microseconds in the cumulative 30-second runtime window.
These are raw counters at this failure cursor, not performance qualification.
Guest stdout/stderr remain empty, native parity is false and full completion
has not passed. The guest child exits 101; the original driver exits 1. There
is no timeout, signal or retry.

Root selected commit `6403eea98031207f6e40a72b55dfd3bd4e7e6ec2`, exact 132-file
source closure `16176e0852fa61cba98acebeb373ee1a6be4c686d0e46ef8bbc144c0527c2cbd`, with selection SHA-256
`b81b166b9fe32c73daa128483150fd5fcd428e2f4b1328fd8042de4289f6f272`. The 53,777,114-byte module remains
`24d85729a659ff3e5fc6f0517709afbb68b371a41829e90785dabd48e0620994`.
The original harness, oracle, workloads, counters and limits are unchanged:
86 tickets, 64 residents/pins, 16-MiB cache, 8-MiB entry, 64-million cache work,
256-MiB combined memory, validation 120 seconds, runtime/WASI cumulative
30 seconds each, and outer 170 seconds plus five-second TERM/KILL waits.
Source, tools/sysroot, module, commands and streams are rechecked; product
sources and both preparation document/seal remain byte-identical.

| Named checkpoint | Instructions | Cache work | Live/peak tickets | Cache hits/misses/decodes/evictions |
| --- | ---: | ---: | ---: | --- |
| Constructed | 0 | 4,928 | 21 / 21 | 0 / 0 / 0 / 0 |
| Initialize | 37,328 | 160,343 | 85 / 85 | 324 / 135 / 135 / 71 |
| Corpus 1 terminal after drain | 23,358,291 | 64,000,000 | 84 / 86 | 537,576 / 61,628 / 61,627 / 61,564 |

The causal failure precedes that terminal snapshot: it holds 85 tickets,
64 entries, 17 active pins and 16 frames. The fixed IR-cache reservation is
118,240 bytes; Corpus 1 terminal resident payload is 498,274 bytes, with
1,847,979 peak resident and 1,238,071 peak pinned bytes. Plan-hit counters are
not exposed by this observer. All complete raw phase usage and cache records
are retained in `phase-counters.json`. The prior run stops at a different
cursor after 15,753,076 instructions. Only constructed and successful Initialize
are compared as equivalent checkpoints: guest counters/live shapes match
apart from cache work; fixed cache reservation rises 29,008 bytes and combined
current reservation rises 30,472 bytes. These counts do not predict completion.

The original causal failure is retained unchanged in `final_failure`, apart
from its appended cleanup observation. Its copied `after_cleanup` snapshot is
before foundation consumption: three tickets, construction 269,616 plus shared
1,744 = combined 271,360 bytes. `finish_owned_cleanup` then consumes that actual
foundation closure. The final consuming runtime ledger has **every current
reservation category, every live count and live tickets zero**, with no cleanup
invariant. The nested WASI submeter remains a copied historical component
observation; runtime ledger WASI current reservation is zero.
`cleanup_empty=false` and `ownedCleanupEmpty=false` are success-oriented flags
that retain the original failure. They are distinct from current-ledger emptiness.
`consuming-cleanup-audit.json` binds this boundary to the unchanged source/harness.

Before host removal, 28 exact result-input snapshots were archived. Target
PID/PGID 95928 and all preparation groups are absent; complete raw streams
reached EOF. Raw child stdout is 18,074 bytes, SHA-256
`49e4a54e37fcbf6998d9beed000a79781b10eda8606e2389edb8c7cce5284f42`;
stderr is 429 bytes, SHA-256
`ffe32c4e3c489b20709247b1b33bdf266068d52c205f7743de2d9e6227897110`.
Root wrapper stdout/stderr and execution metadata are archived separately.

The existing `diagnostic.py cleanup` ran exactly once under a bounded wrapper.
Empty recursive holders and exact path/device/inode checks passed. Cleanup
PID/PGID 96645 is absent, exit 0, without signals.
Only owned runtime scratch (73,032,845 logical bytes)
and the raw executable were removed. The compiler target was already removed
in preparation. The original 4,878,784-byte executable is retained losslessly as
`bin/exact-tests.gz` (1,832,318 bytes,
SHA-256 `e985a47f2b01eaddee97779ccf8c504bb8fa383eb1cc9904005408b7882db3f4`). Its decompressed SHA-256 is
`7f06c49a9943f63dc47079b107c22e3a446aa8d243ae68c4b94be6e56a9e34d9`. Recompression preserves the prepared gzip bytes exactly;
the pre-cleanup gzip is also archived. `prepared-transformations.json` explicitly
accounts for the removed raw executable and historical preparation bindings.
Other projects' processes and data are untouched.

The result receipt, raw evidence, input archive, cleanup audit and result seal
are retained in [the result packet](../verification/swift-exact-reactor-after-plan-reuse/result-receipt.json). Verify read-only, without compiler or guest runs:

```sh
python3 -B verification/swift-exact-reactor-after-plan-reuse/verify-result.py
```

No further target, compile, synthetic surrogate, native/UI/device/phone, provider,
network, hosted frozen-lane, Git or release operation was used for finalization.
The prepared-only verifier remains historical and must not be treated as a
post-cleanup verifier. Root review precedes any separately bounded offline
cache diagnosis; no retry is selected. Guest parity, full completion, standards
matrix, production accounting/caller stack, signed/public/native execution,
performance/size/memory/startup, immutable published FieldLog packages consumed
from a separate repository, phones, store, customer/operational and accountable
GA acceptance remain pending. Phones remain disconnected and deferred. The
whole product goal remains active.
