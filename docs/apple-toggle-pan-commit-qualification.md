# Private final-pan-commit qualification preparation

This packet prepares one public XCTest run against the private candidate described
by `docs/apple-toggle-pan-commit-contract.md`. Preparation does not qualify native
behavior. Root review of the immutable seal and an actual bounded simulator run are
still required. Physical phones remain disconnected and deferred.

The public XCTest target has 43 methods. It retains the original 10 methods and
13 actual input actions unchanged, retains the 16 interruption methods and their
unchanged oracle, adds 16 final-release callback cases, and adds one scoped direct
semantic component method. The single diagnostic app contains all three fixtures;
the unchanged frozen comparator supplies its original native tap pair only.

Each of eight final-release callbacks runs from both initial values. Every case
establishes its initial binding anew and drags through public XCTest coordinates.
The strict oracle requires native touch admission, ordered began/changed/ended
callbacks, one native recognizer identity, real translation and elapsed time,
preview before commit, and the same ended recognizer at the hook. It checks the
hook's before/after states, exact semantic counters, return value, event payload
and order, current binding, direction, traits, cleared preview, and stationary
scroll. Unsupported/malformed observations fail closed.

| Callback mode | Final state | Value event |
| --- | --- | --- |
| Replacement binding | Latest replacement binding | None |
| Stale admission | Prior binding | None |
| Disable | Prior binding, disabled trait | None |
| Explicit cancellation | Prior binding | None |
| Direction change | Prior binding, updated direction | None |
| Nested primary | Proposed binding; nested primary rejected | One proposed value |
| Nested accessibility | Proposed binding; nested return false | One proposed value |
| Binding change after event | Latest replacement binding | One earlier proposed value |

The selection callback reason is `selection`. The after-event case hooks
`panAccepted`, after `valueChanged`. Accepted events precede their informational
completion observer. Rejected commits emit no value event. Binding writes remain
silent. This fixture does not synthesize touches or set recognizer state.

The scoped direct method invokes the original self-test command, retains all 19
original diagnostic checks and their four plain-reference failures, and evaluates
only the selected 36 callback rows through the unchanged semantic oracle. It
retains the unchanged original strict verdict as failed. A scoped component pass
must never be reported as a pass of that original strict suite. Runtime summaries
separate 45 native action results, one direct component result, and the failed
original diagnostic result. The unchanged comparator direct failure suite is not
selected.

The dedicated process adapts only the closed case/action/command union, app
archive selection, runner product paths, and verdict/summary routing. It reuses
the original loopback bridge endpoints, capability handling, public XCTest helpers,
per-instance ownership, independent cleanup, and baseline preservation unchanged.
No new device, filesystem-path, shell or input authority is added to the bridge.
The runner creates at most its one owned simulator at runtime and always attempts
the inherited cleanup, including failures. Preparation performs no native instance
or physical device discovery and no runtime launch.

Run preparation and review from the repository root:

```sh
python3 -B -m unittest discover -s verification/apple-toggle-pan-commit -p test_oracle.py -v
python3 -B verification/apple-toggle-pan-commit/prepare_runner.py
python3 -B verification/apple-toggle-pan-commit/seal_packet.py
python3 -B verification/apple-toggle-pan-commit/run.py verify
```

`host-controls.json` records the exact host command, interpreter, source digests,
output and control counts. `runner-build-attempt-*.json` records the official
build-for-testing invocation and full output; `build-products-manifest.json` and
`test-runner-products.tar.gz` bind the compiled public runner. The candidate app's
separate build receipt, source lock, manifest and archive are owned by root.

After root reviews the actual seal digest, the sole native entry point is:

```sh
python3 -B verification/apple-toggle-pan-commit/run.py run --scope interaction --reviewed-seal ACTUAL_REVIEWED_SHA256
```

Recovery uses the same verified handoff and inherited bounded cleanup:

```sh
python3 -B verification/apple-toggle-pan-commit/run.py cleanup --scope interaction
```

Sealed preparation is immutable. Before correcting a rejected sealed attempt,
archive its named files and exact rejection reason using
`reject_preparation.py 'Concrete rejection reason'`; its receipt and archive are
retained in the next seal. Failed build or host preparation attempts remain
explicit evidence. No runtime or host result implies production Apple adapter,
physical VoiceOver, complete carrier parity, external FieldLog release, store,
customer, operational or GA acceptance.
