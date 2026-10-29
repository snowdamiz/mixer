# Envelope producer timeout experiment

The automatic Engine run 40801222690 stopped at the producer's fixed 120-second limit. It started 77 of 78 methods and recorded 76 terminal successes. The last header method has no retained assertion or panic. Its partial input does not locate the exact instruction at timeout. The original artifact and frozen 86-member envelope packet remain unchanged.

The strongest explanation is aggregate suite cost. The source repeatedly builds an 80,000-row profile and writes full inputs; the context method alone repeats 1,003 vectors. These are source observations, not a measured allocation or I/O profile. No per-method timings survived the original combined command, so a method-specific slow path remains possible.

This candidate changes the runner only. It uses 17 exact root filters and one 61-method embedded filter, arranged in the original lexical order. All 78 names must appear exactly once, with exact filtered summaries and terminal success. Every test body, assertion, input, oracle and product budget remains frozen. Each partition gets separate owned scratch because process-local fixture counters restart. The 14-method independent run and all library/API checks retain their original execution shape.

The producer commands keep 120 seconds each; the complete invocation keeps 480 active seconds and 60 seconds for retention and cleanup. The aggregate deadline is not 18 times the per-command deadline. Commands now use bounded pipe capture: 8 MiB per stream and 64 MiB across all commands. Those are new experimental safeguards; the original runner had no output-cap field. The candidate records actual EOF only when read, retains the first exception if cleanup also fails, holds a child whose terminal custody is unresolved, and prevents scratch removal or another command while held.

Review candidate_runner.py against runner.diff. overlay.json applies exact literal changes to the pinned canonical runner; producer-partition.json contains the full 78-method mapping. decision.json binds the observed artifact, frozen sources, competing hypotheses, and next check. verify_packet.py checks the seal and current dependency bytes. The packet does not modify canonical CI or include an automatic workflow.

Run the guarded source checks:

    python3 -B verification/envelope-producer-timeout-experiment/test_candidate.py
    python3 -B verification/envelope-producer-timeout-experiment/verify_packet.py

All 28 controls passed locally with 0 skips. They execute actual Python orchestration with fake children, streams and clock. This is source evidence, not a process-control or product-runtime pass. The earlier import/helper/generator preparation failures are retained under logs/. The established offline guard is copied unchanged from the compiler-admission-v3 packet and installed before importing candidate code.

The next executable check is one complete remote macOS ARM64 envelope-partition host fixture invocation on an explicitly selected compiler, after independent source review and root selection. Prefer the same Rust 1.98.1 identity as the retained baseline. The candidate keeps the original allowlist of 1.98.1 and 1.99.0; it installs nothing. A success must include all 40 commands, 78 producer and 14 independent methods, 32 layouts, 21,714 finite comparisons, all API compile checks, original postflight checks, exact artifact binding, and cleanup evidence. If a partition fails, preserve it and stop. No automatic retry, larger deadline, fallback or test reduction is authorized by this packet.

The separate shared-input cache fixture already has complete v4 host evidence. It can later be adopted into the ordinary cache CI job through a distinct reviewed wiring change that materializes the exact overlay and retains compiler admission, focused controls, 60/600/60 limits, captures and artifact replay. That would not alter this frozen envelope packet or establish its timeout is fixed.

No local Rust, Swift, Elixir, product, native, UI, capture, process inventory or held-group probe was run. All listed holds, including FieldLog 40802230894 remote PGID 2424 / inner 2621, remain untouched. This packet grants no Engine fix, performance, default, customer, OTA or GA acceptance.
