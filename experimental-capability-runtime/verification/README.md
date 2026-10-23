# Bridge implementation evidence

The production/API/SDK inputs stayed frozen from candidate 1 through candidate 3;
only `verify.py` changed to validate singular Swift Testing test/suite counts and
record the actual public consumer binaries. Candidate5 is the strict final
implementer qualification after the independently reproduced close-race fix; independent review is recorded separately by its owner.

| Evidence | Result and scope |
| --- | --- |
| `2026-10-23-candidate-5/receipt.json` |16 original tests each debug/release/Swift TSan, separate filtered measurement: 1, host/iOS/simulator/Android public consumer links and actual binary identities; host public empty-module rejection run. 55 immutable source inputs. |
| `2026-10-23-active-payload-4/receipt.json` |Separate public observer against the same candidate 5 production/SDK: 2 debug+2 release runs, 8 overlapping large concrete storage gets per run, exact guest payloads and 8 acknowledgements/drain.60 source inputs including observer. |
| `development-history.json` |Preserved intermediate commands/log hashes and initial failed experiments; these are not frozen final qualification. |

Candidate5 receipt SHA256:
`6194e77ab6119f2d91d18f0a374a04fc99bd018019ae9c1e1a81e6e3e02fd07e`.
Its source manifest SHA256:
`070f626acd4cfc99ec2bdeb9b1e1dc45da228548d3f6458fb8fbe1b7bbca4b4d`.
Active observer receipt SHA256:
`b94b555e81a2806dba39e22d3ff7212776aa036b54851f9d0a7849e316f8208c`.
Its source manifest SHA256:
`2e40b854bf896deae88079dd0c9a7865729e08f76a471efa410d4027b23c42cd`.

Each active run verified 8 values of 49,152 binary/65,536 base64 bytes and 525,976
combined guest-wrapper bytes. Debug sampled maximum malloc in-use was 5,487,680–
5,850,720 bytes; maximum batch duration 9.261–9.801ms exceeded the cooperative 8ms
cutoff by 1.261–1.801ms. Release samples were 4,093,328–4,159,808 bytes with maximum
batch 3.882–4.122ms and no observed overrun. Maximum callback durations were 10.25–
11.21us debug and 7.04–7.46us release. These are process-wide 1ms sample observations
including native/runtime/observer work, not exact per-codec/transient-copy peaks
or hard RSS bounds. Logical payload/workers are pump-boundary counters. Swift
TSan's malloc-zone counters returning 0 do not mean no allocation; sanitizer
instrumentation is a separate environment. Exact allocation tracing remains open.

The preserved candidate 3 separate 16-idle-owner process observed 0 timer ticks over 266ms and
152us process CPU during that interval. This single measurement is not a CPU SLA.
The normal-trust TLS fixture saw a real local TCP connection and TLS failure
without HTTP application bytes; no trust or credential store was modified.

Reproduce with fresh names using `verify.py --name <name>` and
`observe-active.py --name <name>` from the repository root. Both export immutable
source into ignored scratch and consume the separately qualified staged native
archive. The observer defaults to candidate 5 and accepts an explicit immutable base receipt.
Candidate3/active3 remain immutable historical receipts. Only Ownership.swift
changed from candidate 3 to candidate 5: explained checked closed-handle 3 is
suppressed on drain/wake/deadline query paths; retained ack 3 and metadata/status 4
faults remain fatal. The independent review owns the exact failed regression.
No source/SDK/native input changed during either completed final run. Cross
builds compile/link only; system frameworks/Rust archive are not Swift TSan
instrumented. Phones remain disconnected. No activation, release, identity,
publication, device or GA gate is qualified by these receipts.
