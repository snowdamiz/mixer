# Shared-input cache-fixture diagnostic candidate

This is a concrete, reviewable candidate for one later root-selected manual CI
diagnostic. It has not been compiled, run as a Rust fixture, dispatched, committed
or pushed by this lane. No canonical/global file or historical pack was edited.

The accepted Rust source is byte-exact at SHA-256
`f7d62c01e251642677e22f7595af9683f9c451f1db43683be5d2ef86fedba141`.
Its independent source-review tree is
`407647c81271e3dd4d49308a224a7d0cc1165e31a793dfadb1a51924aa605d84`.
Source acceptance is sufficient to prepare this integration; actual compiler and
complete-fixture evidence remain pending.

## Ready integration

The only proposed workflow installation is an exact copy of
`workflow/cache-fixture-shared-input-diagnostic.yml` to
`.github/workflows/cache-fixture-shared-input-diagnostic.yml`. The workflow uses
`workflow_dispatch` only. It refers to this sibling under its current name; no
directory rename or change to the canonical Verify job is needed. Root selects
delivery and dispatch. Nothing here dispatches automatically, retries a failed
fixture, or raises any numeric bound. A workflow rerun with attempt greater than
one is refused; selecting another diagnostic requires a new deliberate dispatch.

`pack-overlay/` contains only the accepted regression source, amended source
roster, amended bindings, and effective manifest. The previous roster predecessor
and `fixture_setup_amendment` are preserved. All other 83 effective pack members,
including product/library source, API/layout/File controls, methods and existing
partitions, are borrowed from the immutable frozen base by exact SHA. No large
pack or raw artifact is duplicated in this candidate's committed inputs.

`materialize_pack.py` verifies the complete frozen base, closed overlay, exact
source preimage, accepted source and independent review before copying ordinary
files into fresh owned `materialized/pack`. It rejects extra, missing, mutated,
duplicate, traversal and symlink inputs; it does not create hardlinks. It verifies
the entire effective 86-member pack and ownership again after copying and during
runner postflight. Interrupted materialization leaves its ownership marker,
partial inputs and failure receipt recoverable under this sibling.

`check_cache_state.py` is a minimal derivative of base runner SHA-256
`162b34dcf64fee840c53ead9ff0ee9ab7241741ac9708fbed8ccb697caff2bf3`.
`runner-amendment.diff` contains the complete amendment. It retains the complete
Debug and optimized fixture closure: 103 child commands including all existing
producer Debug groups, host/producer/independent/control methods, 23 layouts,
31 captured File cases, and all 25 API probes per mode. It retains the 60-second
per-child, 600-second active, 60-second cleanup and 8 MiB per-stream caps, environment
scrubbing, exact derivative-source checks, failure retention, ownership and
process-group custody safeguards. No case was split and no assertion or accepted
Rust test semantics changed.

The selected compiler is exactly `aarch64-apple-darwin`, Rust `1.98.1` on `macos-15`.
The manual workflow sets `RUSTUP_TOOLCHAIN=1.98.1-aarch64-apple-darwin` and
`RUSTUP_AUTO_INSTALL=0`. The existing launcher/sysroot/verbose/hash checks verify
the actual compiler and fail if it is unavailable or different. There is no
installation or fallback to another compiler.

Each command retains raw before/after `RUSAGE_CHILDREN` user/system CPU and
minor/major-fault snapshots. Deltas are labeled as reaped-child aggregate counters
in this sequential trusted runner. A child-reap failure, absent spawn or custody
hold withholds the delta. This is not isolated-process CPU accounting. Existing
supervision and terminal-fact requirements remain authoritative.

Context phase progress is retained in raw stderr and structured command rows,
including an explicit unattributed elapsed remainder. `prepare_ms` excludes
caller context cloning and shared setup/validation; `elapsed_ms` includes them.
Individual phase values use integer milliseconds rounded down. `completed=1003`
precedes final shared validation/removal and cannot establish completion. Accept
completion only from full command success, exact fixture verification and a
successful postflight/cleanup receipt.

## Executed offline evidence

Command:
`python3 -B verification/cache-fixture-shared-input-candidate/offline_verify.py`.
`offline-controls.json` records Python/host, exact input hashes, output scope,
command budget and cleanup. `offline-controls.stdout` retains full test output.

The audited in-process run passed 28 runner source/file/mock controls and nine
materializer groups, with zero denied-operation attempts. The pinned current base
`test_runner.py` has 32 test methods, all retained, and the candidate adds four
bounded mock accounting controls, for 36 total. Eight existing controls that
launch children or use signals remain unrun here; the manual workflow runs all
36 controls before starting the one complete fixture invocation. The existing
compiler-selection assertion is narrowed to the declared compiler. The existing
deadline-injection controls isolate only the newly added overlay hook, preserving
their original timer/cleanup assertions.

Materializer controls exercise the full actual 86-member closure, including
ordinary-file identity, mutated/missing/extra base and overlay members/manifests,
duplicate/traversal/symlink replacements, wrong original source even under
deliberately repinned test manifests, candidate mutations, ownership refusal and
retention after injected copy failure. All synthetic owned scratch is removed.
This does not execute Rust, a compiler or a product runtime.

No current Git revision was probed because this lane is source/file-only. The
read-set digest records exact source/evidence bytes before and after the run;
they are unchanged. The shipping seal binds this candidate's files. The later CI
workflow records the checkout revision/tree and verifies the installed workflow
against this candidate, then retains the executed runner, complete materialized
pack, stdout/stderr, phase progress, CPU accounting, original review/bindings,
failure inputs, postflight and cleanup/custody receipts. Runtime materialization
is retained for that artifact; runner scratch is removed only under the unchanged
verified-retention and custody rules. Cleanup failures preserve recoverable
scratch. Other projects and held groups are never discovered or touched.

## Acceptance limits

The historical 60-second timeout remains failed. Root supplied later unchanged
passes, including 52.410318 seconds and green results on 5ef/295; this lane did not
refresh them. Those observations do not prove a product regression. A later exact
fixture pass supports only this declared-compiler harness diagnostic.

The candidate removes 2,568,193,536 profile clone bytes and 2,565,633,024 profile
file-write bytes while keeping all 1,003 analyzer invocations and fresh 8 MiB
arena initialization with 1,048,576 paid extensions per case. Shared profile
content is also read twice for validation. Eliminated traffic is not a speedup
estimate; the actual remaining cost and behavior require the diagnostic.

No runtime, local compiler, Git command, process inventory, held-group probe,
UI, simulator/emulator, native device, screen capture, old FieldLog fetch,
publication or dispatch was performed. Physical/native/capture checks remain
paused or pending. Allocation, replay, capability and release/GA holds remain
active. This candidate grants no release, customer, native or GA authority.
