# Swift CI refusal at 2c751cbb

Engine run **40942282975**, attempt 1, failed Swift job **123688487731** at
step 10, `Accepted standalone analyzer fixture envelope`.

The first and only recorded fixture error is:

```text
active / RuntimeError / Compiler host/release not selected
```

The runner resolved the supplied rustup launcher to **Rust 1.99.1 on
`aarch64-apple-darwin`**, commit
`58cf8f9c35b355199727627d07ae34a4e2846d67`, dated 2026-10-13, LLVM 23.1.1.
Its compiler SHA-256 is
`1ba7bb8e273bd64125f4048d2ecce530e0a6470e565ab1b3aecf0b82b532f7b1`.
The exact reused ordinary policy permits only Apple ARM64 Rust **1.98.1** and
**1.99.0**. The actual compiler is outside that fixed set.

This is the existing fail-closed compiler qualification boundary. The source
controls explicitly require 1.99.1 rejection, and the prior compiler amendment
requires explicit reselection after later CI compiler drift. The evidence does
not show an engine defect, a compiler failure, an infrastructure fault or flakiness.
It does not identify the prior green run's actual compiler bytes; no causal
comparison with that run is inferred.

## Retained evidence

The exact acquired artifact is 444,759 bytes, SHA-256
`4bf8af7420033af59134305742ccfc6e125a5a09a4e4e4f9ee4720948d94ab0e`.
Bounded ZIP inspection verifies 139 regular/directory members and 8,714,342
uncompressed bytes, including every payload CRC and SHA-256. The review helper
does not extract or import artifact code.

`result.json` records 240 successful source/data assertions. They bind all
86 immutable pack members, all 17 sealed adoption members, the 93 checkout
dependencies, all executed source snapshots, and the actual workflow to the
current source bytes. The workflow SHA-256 remains
`a90bab7dea218e5a098e45eb370e9b666afdf0bda9100cb35ec14dfc779de024`.

The artifact records 22 passing adoption controls. The fixture then starts
exactly five commands: revision, Git tree, Python version, compiler sysroot, and
verbose Rust identity. Every command exits zero and records returned direct
child, absent owned group, separate stdout/stderr EOF and no custody hold.
All eight recorded source/tool postflights pass. Fixture stderr is empty;
fixture stdout records the exact refusal. No fixture scratch is created.
The adapter reports status 1 without an exception or secondary error, and does
not run terminal replay after this failed invocation.

No fixture library, producer, independent-test or API compiler command starts.
All 40-command full-envelope qualification results therefore remain unavailable
for Rust 1.99.1. Following capability, transport, TSan, SDK/CLI, VM-startup and
generated-consumer steps are skipped in this Swift job. Other jobs' outcomes
retain their separate attribution.

## Minimal next scope for root selection

No compiler is newly selected by this investigation. A future correction can
explicitly select Apple ARM64 Rust 1.99.1 for prospective qualification while
retaining strict identity parsing, exact launcher/sysroot/hash capture, the
fixed prior host/version pairs, immutable pack bytes, warnings policy, capture
limits, deadlines, custody safeguards and no-install/no-retry/no-fallback rules.
That would require a coordinated, source-bound policy derivative and its
adoption/dependency bindings; it must preserve this original refused artifact
and the earlier accepted runner identities.

The focused source controls should cover coherent 1.99.1 identity, continued
1.98.1/1.99.0 behavior, malformed or incoherent identities, unselected patch and
nightly releases, other hosts, exact ordinary-policy reuse and failure/source
postflights. Actual qualification must then run the original full workload:
40 commands; 78 producer methods in 18 disjoint groups; 14 independent methods;
32 unchanged layouts; 21,714 comparisons; one positive and eight intended
negative API checks; all retention, source/tool postflight and child/group/pipe
closure checks. Passing source controls alone cannot qualify the compiler.

## Inspection commands and limits

```text
python3 -I -B -S verification/engine-ci-2c751cbb-swift-failure/inspect_artifact.py
python3 -I -B -S verification/engine-ci-2c751cbb-swift-failure/inspect_artifact.py --summarize
python3 -I -B -S verification/engine-ci-2c751cbb-swift-failure/inspect_artifact.py --verify
```

The helper installs active process/session/group/signal/wait/socket/timer API
denials before loading its inert data readers, restricts writes to this review
directory and records the Python executable/version and helper digest. No active
API denial is triggered. Local acquisition, raw logs, raw archive inventories
and raw receipt summaries stay under `local/`; root owns those acquisitions.

This lane performs no Git/gh, network, compiler/product/oracle/native/UI runtime,
process inventory/probe/signal, workflow retry or cleanup operation. No product,
source-policy, workflow, status or gate file is edited. FieldLog run 40802230894,
PGID 2424, inner PID 2621 and all prior holds remain untouched. Native/UI/capture
and physical-phone checks remain pending. There is no release or GA acceptance.
