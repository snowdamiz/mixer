# Experimental owned-adapter lifecycle evidence

This slice adds a private Swift SPI to the isolated experimental bridge. The
trusted caller reserves its own whole-attempt slot before opening concrete
adapters, transfers exclusive use through `OwnedCapabilityAdapterGroup`, and
supplies fixed nonblocking terminal and retirement sinks without strong paths
back to the group, construction or session. The SPI cannot prove uniqueness,
authorize execution, or implement the future outer coordinator.

`OwnedLifecycleTests.swift` uses real native creation and concrete app-private
storage. It checks partial setup, untouched ownership after prepare failure,
duplicate consume, construction cancellation and abandonment, public session
deinit, real storage effects and reopen after retirement, observer release, and
actual native registry exhaustion. Existing development API tests remain in the
same suite. The ordinary and SPI cross consumers are separate executable
products linked against the same single experimental archive.

`probes.py` exports immutable qualification inputs and applies the recorded
test-only patch to a private copy. Its five isolated tests gate a successful
constructor tail after continuation publication, a cancelled constructor after
real C creation, concrete KV close return, and the real installed storage
`afterInvocation` join; the final test mutates the ABI report after actual C
creation to observe conservative quarantine. These are derived scheduling and
fault controls, not unmodified public reproductions. The original concrete
adapter is never replaced. Each quarantine probe runs in a separate process.

Run the final implementer matrix with a fresh name:

```sh
python3 -B experimental-capability-runtime/verification/verify.py --name NAME
python3 -B verification/capability-bridge-lifecycle/probes.py --freeze NAME --name PROBE-NAME
python3 -B experimental-capability-runtime/verification/replay-public.py --freeze NAME --name PUBLIC-NAME
```

Receipts pin each exported source, command, output, linked binary and staged
native artifact. Historical development failures and runs remain separate:
`initial-test-compile` preserves the initial Swift capture diagnostics;
`development-probes-1` records the first debug derived-source run. The final
probe timeout is deliberately wider than that development run for scheduler
qualification; no production deadline behavior changed.

The retirement boundary is logical constructor tail plus checked native drain
plus actual concrete adapter close. It does not establish runtime Task/allocator
destruction, general OOM behavior, a shutdown latency guarantee, platform device
execution, activation, publication, release or GA qualification. Local Swift
6.3.3 cannot substitute for hosted pinned Xcode 26.3 qualification. Rust archives
and platform frameworks are not instrumented by Swift TSan. Independent review
is recorded by the separately owned lifecycle-review lane.
