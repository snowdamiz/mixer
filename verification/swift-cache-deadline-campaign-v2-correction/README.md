# V2 command-custody preservation correction

This sibling corrects one exception-path defect identified by root before any
dispatch. The frozen v2 packet remains unchanged. Its imported v1 command helper
can raise after spawning but before returning a terminal receipt. V2 formerly
decided whether to remove scratch from an exception-message substring; an
arbitrary `OSError` could therefore remove files while child custody was unknown.

`campaign.py` is the frozen v2 driver with one explicit custody guard at every
command site. It records a pending command before calling the inherited helper.
It clears pending only after a returned dictionary contains a positive integer
owned PID, a valid integer process exit status (never `-999`), and
`processGroupEmpty` exactly `true`. A missing proof or any intervening exception
leaves custody pending, blocks subsequent commands/attempts, retains scratch and
records `stopped-unresolved-command-custody`. This is conservative preservation;
it neither adds process probes nor attempts recovery after the helper fails.
Root disposition is required before reusing those affected remote resources.

The inherited runner and telemetry are unchanged. The correction adds no VM
change: both generated source manifests are byte-identical to frozen v2, with
256 residents, cumulative runtime/WASI 60 seconds across initialization and both
corpus calls, 100M fuel and all retained validation/memory/capability/oracle
safeguards. Validation is still 120 seconds. Maximum two full attempts, the
CacheWork-only second-attempt condition, 540-second driver and 15-minute workflow
remain. V1's four actual results remain valid; no old primary run is selected.

The complete driver difference is `driver-delta-from-frozen-v2.patch`. The input
bindings retain v1 assets, the actual-review seal and the frozen v2 driver,
tests, README, workflow and seal. No large input is copied. `finding.json` binds
the concrete reviewed defect to those frozen sources.

Root installs this packet's `workflow.yml` under the same v2 workflow name. Its
readset adds this sibling and its command becomes:

```sh
python3 -B verification/swift-cache-deadline-campaign-v2-correction/campaign.py run \
  --output "$RUNNER_TEMP/swift-cache-deadline-campaign-v2"
```

Local checks:

```sh
python3 -B verification/swift-cache-deadline-campaign-v2-correction/test_campaign.py
python3 -B verification/swift-cache-deadline-campaign-v2-correction/campaign.py check \
  --output verification/swift-cache-deadline-campaign-v2-correction/source-check
```

Seventeen source/data and fully mocked controls pass. They include the inherited
helper's arbitrary error after mock spawn and post-spawn receipt-write error,
sentinel `-999`, absent/false/non-boolean group proof, malformed PID/status,
subsequent-command refusal, normal proven closure and scratch cleanup only after
closure. The mocked tests never launch a child or probe a PID. Compiler, guest,
native, UI/capture, physical-device and local-custody holds remain unchanged.
Actual remote compilation, full-corpus results and cleanup remain pending. All
scope, measurement and architecture-escalation limits in the frozen v2 README
continue to apply.
