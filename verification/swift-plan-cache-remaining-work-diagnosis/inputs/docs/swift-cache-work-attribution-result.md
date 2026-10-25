# Full Swift reactor cache attribution

The single selected full-reactor attempt preserves the previous failure exactly: CacheWork attempts 64,000,001 against 64,000,000 at function 1356, byte offset 492821, after 12,971,689 guest instructions. Complete validation, construction and Initialize pass; Corpus 1 fails and Corpus 2 is unrun. Guest/native output parity remains unverified.

The six fixed-size observer snapshots reconcile with the runtime's authoritative counters and report no invalidity. All 318 frozen preparation members and the unchanged 132-file live VM closure verify before and after execution. The test-only observer attributes successful credits, not CPU time:

| Work | Credits | Share |
| --- | ---: | ---: |
| Scan and build | 40,257,233 | 62.90% |
| Resident lookup probes | 12,346,190 | 19.29% |
| Empty-slot, victim and plan-count work | 7,566,848 | 11.82% |
| Free-pin probes | 3,430,616 | 5.36% |
| Lookup headers, policy and construction | 399,113 | 0.62% |

There are 39,432 completed decodes across 485 distinct function identities: 38,947 completions are repeats (98.77%). The cache records 39,368 evictions, 280,175 hits and 39,433 misses. These observations establish repeated decoding; the earlier uninstrumented counters alone did not. The bounded sample identifies the first repeated identities and does not rank the hottest functions or attribute per-function CPU time.

The unchanged budget fails during scan. The next optimization assessment should examine bounded reuse of decode planning and cheaper resident lookup while preserving entry/memory limits, exact reservation accounting, pin/eviction safety and fail-closed validation. These measurements select the problem to investigate; they do not justify increasing work limits or predict full-target completion.

The test exits 101 without a host timeout; both output streams close and the owned process group is absent. Consuming cleanup returns every current primary reservation, live counter and ticket to zero with no cleanup invariant. The original cleanup_empty flag remains false because the earlier runtime failure is retained. The 53,777,114-byte copied guest and temporary scratch are removed after a holder check; no simulator/device runs. [Root result binding](../verification/swift-cache-work-attribution-root-selection/result-binding.json) records the exact selection, preparation, command, events and cleanup. No full runtime, native, public/signed package, FieldLog or GA pass is claimed.
