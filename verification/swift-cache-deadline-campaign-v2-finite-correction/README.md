# V2 exact finite-expectation correction

Run 40747548560 at `fb7c7f20f8a308424ef4b7092d19d3d4de2c7627`
compiled the primary profile, then stopped at one stale finite assertion:
actual `(100000000, 1000000000, 60000)`, expected
`(100000000, 1000000000, 30000)`. Three finite tests passed, one failed;
zero full attempts executed. All five command groups closed, pending custody was
null and remote scratch was removed. This is not full-workload cleanup evidence.
The actual review seal is
`c15eb4a779600d78adcb2b7e99bbe24c30bfed38d6cf3e087e431134a10457a8`.

This new packet retains the custody-corrected driver and changes only one
generated Rust test expectation. The exact original assertion is replaced with:

```rust
assert_eq!((b.instruction_fuel, b.execution_work, b.deadline_ms), (100_000_000, 1_000_000_000, 60_000));
```

The expected deadline is literal; fuel and work expectations are unchanged.
No frozen v1 control or earlier packet is edited. Relative to the failed compiled
source, only `src/experimental_swift_reactor/cache_tests.rs` changes. Relative to
the reviewed v1 256-resident profile, pure normalization permits exactly the two
runtime deadline fields and this one assertion, restoring every original byte.
Negative controls reject other bounds/test edits, derived or dual-accepted
deadlines, and missing/duplicate assertion anchors.

Nineteen pure source/data and mocked controls pass, including all existing
custody and attempt-selection regressions. The initial negative-control run was
interrupted when unittest tried to format a large intentional dictionary diff;
its stderr is retained. The check now uses the same exact byte equality with a
bounded failure message. That interruption started no compiler, guest or PID
probe. The completed rerun passed in under one second.

The two remaining maximum full attempts, 256 residents, 64M primary/conditional
128M CacheWork, cumulative 60-second runtime/WASI deadline, 120-second validation,
100M fuel, 1B execution work, memory/grant guards, original full artifact and
11-field two-corpus oracle are unchanged. The pending-custody guard, 540-second
driver, 200-second full-target allowance and 15-minute workflow are unchanged.
The correction directly unlocks the four existing compiled finite controls,
original harness control and first selected full attempt; those remain pending.
If the corrected bounded campaign still misses both-corpus-plus-cleanup, the
existing Astra architecture-comparison requirement applies.

Root installs this `workflow.yml` under the same v2 workflow name and dispatches
once at a new commit. Its sparse readset adds this packet and the sealed actual
review's `seal.json`, `receipt.json` and `REVIEW.md`. Command:

```sh
python3 -B verification/swift-cache-deadline-campaign-v2-finite-correction/campaign.py run \
  --output "$RUNNER_TEMP/swift-cache-deadline-campaign-v2"
```

Local checks:

```sh
python3 -B verification/swift-cache-deadline-campaign-v2-finite-correction/test_campaign.py
python3 -B verification/swift-cache-deadline-campaign-v2-finite-correction/campaign.py check \
  --output verification/swift-cache-deadline-campaign-v2-finite-correction/source-check
```

Generated source SHA-256:

- Primary: `c68fb260b6e282f4c6245ad074d01978d17aa79a155d3688654a0585d711e3d7`.
- Conditional: `fe4e9bd1b05938988c858ec228d95f54f93e662f07d5426c440743bcb9a16c87`.

Driver/test/workflow diffs against the failed-run correction are retained beside
the candidate. Input bindings reuse all existing assets and preserve the actual
failed run. No compiler, guest, native/UI/capture, phone, local-custody or global
process probe, commit, push or dispatch was performed here. All earlier holds
and scope/measurement limits remain. No new host feasibility is claimed.
