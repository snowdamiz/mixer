# Cache-control diagnostic correction

The failed attempt is independently sealed at
`../github-delivery-identity-network-transfer/cache-controls-review/`.
Its current result remains one error in 29 controls, with the compiler fixture
skipped. The primary cleanup exception was not retained. This correction does
not claim to fix that unknown underlying cause.

`check_cache_state.py` now initializes group disappearance conservatively,
retains the primary exception plus separate cleanup exceptions, and completes
output hashing and both receipt writes when `stop` raises. If the last cleanup
attempt cannot establish group disappearance, `owned_group_gone` stays false
and `Commands.active` preserves custody. A command or cleanup exception is
raised after evidence finalization. Existing signal, timeout, polling, output
cap, process identity and success predicates are unchanged; no process retry
was added.

`test_runner.py` retains the descendant control's original exception, receipt,
and raw command files under current `logs/descendant-control/` before its
assertions and teardown. Assertion diagnostics include that evidence. Teardown
retains unresolved owned scratch and a custody-hold receipt instead of deleting
it. The three added controls use synthetic process, pipe and selector objects.
They validate simultaneous primary/stop exceptions, cleanup-only reporting and
retention, and the unchanged requirement for a positive group-disappearance
observation before success.

Executed exactly:

```text
python3 -B verification/swift-cache-controls-diagnostic-correction/run_mocked_controls.py
```

All three controls passed. An audit hook was installed before the runner was
imported and denied subprocess, socket, exec, spawn, fork, kill and killpg audit
events. No denied event was attempted. Every process/PID/group interaction in
these selected cases was mocked, and source hashes were unchanged during the
run. `mocked-controls.json` records the exact source hashes, Python version,
selected methods, result and scope; `mocked-controls.stderr` preserves unittest
output. The scoped source diff passed `git diff --check`.

The complete suite now has 32 methods but was not executed. No compiler, actual
descendant, alternate custody replay, held PID/group probe, process inventory,
native runtime, simulator/emulator, UI, Docker, PostgreSQL, or hosted operation
ran. Root review and any separately authorized remote CI remain pending. No
commit, push, workflow, README, canonical status/gate metadata, or memory update
was performed by this lane.
