# R396: current generated Java failure

The current artifact proves an Android toolchain-inspection deadline during **Debug `mixer create`**, before any Java/D8 consumer build. It does not prove a sparse source-closure omission. The deeper reason the inspection exceeded its limit is not recorded.

- Repository/revision: `snowdamiz/mixer`, `12a57c991cc5e51d5f2ad898a522355deed481a9`.
- Run/job: `42898333528` / `130117303167`.
- Artifact: `13802900928`, `generated-java-12a57c991cc5e51d5f2ad898a522355deed481a9-42898333528-1`, 229,453,255 bytes.
- ZIP SHA-256: `7cce50a9f4c11b11da08cef5cc15597c26e91e36de86e43242b8c757f7397ed5`.
- Git tree recorded by the run: `4384865b2fc3cf3b1d7caadd232f0a474b1003f2`.

## First failing command

`integration/commands/011-debug-create.stdout` contains:

```json
{"code":"process.runtime-deadline","message":"Command stopped with terminal custody: runtime-deadline","status":"error"}
```

Its stderr is empty. The CLI invocation was the Debug producer's `mixer create GeneratedJavaApp --platform android --directory …/debug/original --application dev.mixer.generatedjava --sdk-path …/sdk --android-adapter-path …/native/android`. The outer CLI exited 1 after 183.131 seconds with no outer timeout or output stop.

The copied top-level integration receipt embeds the nested inspection receipt: `python3 …/MixerCLI_MixerBuild.bundle/Resources/android-build.py inspect`, PID/PGID/session 12351, policy `local-full-android-toolchain-inspection` with runtime 180 seconds and cleanup 60 seconds. It records `stopReason=runtime-deadline`, `groupKillSent=true`, `exitCode=9`, and zero stdout/stderr bytes. Runtime start to cleanup was 180.547272 seconds; runtime start to terminal was 181.058761 seconds. Signal 9 is the recorded deadline cleanup outcome, not an independent Python exit diagnostic.

The preceding version probe exited 0, and the Debug producer build exited 0. Bootstrap and integration standalone official inspections exited 0 in 45.903 and 41.857 seconds. These elapsed observations identify the execution-path difference; they do not establish a performance regression or which operation stalled. `consumers` is empty: none of the six expected consumer builds reached a recorded result; Release producer work was not reached.

## Custody and preservation

Top-level bootstrap/integration receipts were copied and checked before opening failure streams or the bundled inspection helper. All 25 recorded outer commands and both recorded nested commands have direct-child reap, both EOFs, descriptor closure and positive group-absence evidence. Both nested states are TERMINAL/released. No UNKNOWN or cleanup error is recorded in those summaries, and no archive entry named HOLD.json was present.

Bootstrap removed its owned toolchain scratch. Integration deliberately retained terminal failed-run scratch at `/Users/runner/work/_temp/generated-java-ci/integration/generated-java-owned-2r9f972f`; `owned_scratch_removed=false` is preserved as that fact. R396 did not clean, probe, signal, wait on or retry hosted resources. All historical holds remain intact. No new hold was created by this offline inspection.

## Source attribution and limitation

The exact bundled inspection helper is 40,156 bytes, SHA-256 `04675e4b320a68ed89d4f06f7a232fdde87ff0316e9f569a0725c9a02c1fea28`, matching its entry in the run's admitted source inputs. It probes Swift/Java, hashes tools/metadata and five full installed distributions, and emits its structured result only when inspection completes (`bundled-android-build.py:451–492`). There is no per-phase progress record. Its source-profile decode is build-only; this invocation is `inspect`.

Canonical static reads of OwnedCommand.swift, POSIXCommandControl.swift, ProcessRunner.swift, AndroidProject.swift and check-android-generated-java.py match the pinned run's hashes (see source-read-provenance.json). AndroidProject.swift:78 selects `.fullAndroidToolchainInspection`; OwnedCommand.swift:14 sets 180 seconds, and OwnedCommand.swift:171 selects the runtime-deadline stop. The integration runner checks the create exit before validate_consumer. No source/profile admission failure is shown. A current bootstrap source read was not present in the integration source map and is excluded from historical implementation conclusions.

The retained archive contains only the nested launch/intent receipts, the two terminal command receipts and empty Swift temporary markers for this command. It does not identify whether a version probe, hashing phase, I/O delay or another operation consumed the deadline. A specific omitted source, slow distribution, Java problem, or larger required numeric limit would be speculation.

## Minimal next test / fix proposal for parent and R388

Keep R388's ownership of canonical CLI, binding and proposed afterimages. No competing patch or Pair-number edit was made. No demonstrated product fault supports a numeric-limit or profile fix yet.

The smallest discriminating follow-up is a **fresh isolated diagnostic comparison**, owned by that lane: record begin/end checkpoints only around the existing inspection probes and tool/distribution hashes, using a bounded sidecar in the fresh owned output directory. Compare direct inspection with the packaged CLI's create inspection using identical explicit tool paths/environment and the existing 180-second policy. Keep stdout as one JSON result; stderr progress is unsafe here because ProcessRunner combines streams before JSON decoding. Preserve all full-inventory, changed-file, symlink, authority and custody checks. This requires no generalized controller, artifact seal or extra review campaign. R396 did not execute or authorize a hosted rerun.

Minimal regression when implementing checkpoints: inert operation doubles must produce the same inspection result and phase order with tracing enabled/disabled, preserve the original error for a failing phase, and never authorize a pass or alter deadline/cleanup facts. The real regression target remains the packaged create invocation under owned custody. A helper-selector closure control is conditional on an actual omission finding; none was demonstrated here.

## Offline verification

`python3 -B verification/plan-continuation-2026-11-07/generated-consumer-current-failure-r396/verify_observation.py` passed on Python 3.14.8/macOS 27.0.1. It rechecks only copied top-level metadata and the exact copied failure/helper bytes. `observation-result.json` preserves its output; `result.json` is the compact parent handoff. This is evidence verification, not a new compiler, Android runtime, device, immutable-package or GA pass.

No root Git commands, canonical writes, workflow reruns, remote mutations, subchildren, device operations or historical held-namespace accesses were performed. The named current artifact was the only artifact downloaded. Full ZIP extraction was not performed.
