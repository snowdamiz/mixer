ACCEPT — exact ordinary Android host CI artifact for pair9 R2 at `96f03ab65966a6374e958e780fa09a3eed814c0b`. No blocking finding within this scope. This closes the ordinary-host-CI condition for these bytes only. It does not accept the overall workflow, generated consumers, native behavior, release, or GA.

Run `42430741909`, supplied attempt `1`, job `128578860306` (`android-owner-host`), artifact `13597407658`. The supplied artifact API snapshot, job snapshot, checkout log, upload log, archive, frozen source maps and immutable owning Git blobs agree. Attempt 1 is recorded by acquisition metadata; the retained job/artifact API snapshots do not independently expose an attempt field. No network lookup or current GitHub state assertion occurred.

The retained `/tmp/mixer-ci96-android-host.zip` is exactly 1,716,883 bytes with SHA-256 `ea77e0529d5639b68fa8e8d3d9e30281b50e663d61ca66af6a6064bdc406a795`. All ZIP member CRCs, unique safe member names, all 957 file hashes and all 11,213,090 uncompressed bytes independently verify. Every existing extracted file equals its corresponding ZIP member, with no extra or missing file. The ZIP remains retained; no second extraction was made. `archive-files.json` lists every full file hash.

Observed retained outputs:

- A: 231 cases / 1,250 assertions; 92 frozen inputs, 88 explicit Java sources and 273 retained class files.
- B: 14,692 checks; 108 frozen inputs, 104 explicit Java sources and 346 retained class files. Its 1,323 hit rows are exactly 189 obligations × seven cases, with no missing obligations. Every selected frame resolves to an instruction boundary containing an invocation, its real method descriptor, constant-pool target and classfile source line. All seven cases agree on one exact caller per site, and the 189 callers are distinct. All source invocation anchors match the pinned source. Nine direct editor calls resolve to the actual InputConnection targets.
- All 15 helper/constructor boundary traces equal their clean matrix rows and retain their final event, receiver and original caller. Both secondary anchors verify against compiled code: line 521 for the toggle measurement and line 719 for layout. The stale line-826 selector is absent at that final measurement event.
- Observer: 190 cases. Platform: 134 cases / 699 assertions. Their closure has 40 frozen inputs and 35 explicit Java sources. It retains complete command/output reports, a 178-entry class identity manifest and javap reports; its class bytes were removed by the producer. Independent rehashing of those 178 class files is unavailable. A/B retain all 619 class files and independently rehash successfully.

All 39 retained command receipts report exit 0, reaped direct children, no timeout and no output overflow. Every stdout/stderr hash matches its retained bytes. Compilation has empty diagnostics, explicit frozen source rosters, `--release 17 -Xlint:all -Werror -proc:none` and identical empty classpath/sourcepath. Test argv bind assertions, bounded heaps, exact compiled classpaths and actual test entry classes. Full B was requested without `--skip-matrix`. Its retained host elapsed time is 117.56 seconds, inside the runner's 300-second bound; this is a run record, not a performance comparison.

The three closure receipts bind the same Temurin Java/Javac/Javap executable identities and retained outputs identify JDK 17.0.21+9 / javac 17.0.21. These Linux executable hashes are producer claims bound to the command records; the binaries are unavailable for independent rehashing on this Mac. Their complete identities are in `audit-result.json`.

All three host steps and artifact preservation are successful in the supplied job snapshot. The only skipped step is `Show retained Android host failure diagnostics`. The exact owning workflow at `.github/workflows/verify.yml:43` puts it behind `if: failure()`, while artifact preservation uses `if: always()` at line 61. This intentional diagnostic skip is not a skipped test. The job log records the exact checkout head, closure commands and uploaded archive digest/size/artifact ID.

The owning Git tree is `6dacea5d2f5cd55d6934142cce556a4bd0fcd1c0`. Every closure input equals both its retained input and the exact Git96f blob. All 101 canonical inputs equal the frozen R2 selection, with zero differing paths; the inventory is also independently closed against Git's package/source inventory. Their recomputed digest is `a10a62cc79145bc80bfd780257589f437cc82e2f1ebaad6ccde39c134d56e0ca`. The frozen profile is `mixer.android-source-pair.9`; all SDK22 and adapter24 file bytes and both aggregate digests independently verify:

- SDK22: `bc03288599ece5612cc4dce8b80fc404942584e0477ec9333bd39c0fa7d352d0`.
- Adapter24: `ee9414d3b68f9d66ba275c93339018e5eaebb161a7dc25d7056538c652305d89`.

The environment receipt's `context_revision` is `fb4c8f074f1a3e5eb2b1b1a45b44f0fa61a7cc62` and explicitly marked inherited, not live Git. It is not used as this review's owning revision. Exact Git96f input equality plus the checked-out CI job establish that closure's binding. The two A/B revision commands explicitly return Git96f.

Frozen source identities, read through the owning Git object rather than the mutable parent checkout:

- `native/android/app/src/dev/mixer/android/NativeEnvironmentPlatformV2.java`: 17999 bytes, SHA-256 `ae20d376d09e27bd751c07f140001446853f1cf00e1a9a37ec1e67f02c8fc5cb`.
- `native/android/app/src/dev/mixer/android/NativeEnvironmentV2.java`: 15229 bytes, SHA-256 `7a072fbf56ed128ffe2f580195a6856afc8cf34c31585e1a61443c0f7d84e119`.
- `native/android/tests/NativeEnvironmentV2ObserverHostTests.java`: 29972 bytes, SHA-256 `724773ae47848d243a18295be62e068f729d36c5072f31624db25b743c395f95`.
- `native/android/tests/NativeOwnerV2ConcreteHostTests.java`: 89268 bytes, SHA-256 `e20c1bbaf00419e9e871669eb4abf1e28a2ce0620d4e6bd78a79f11fe32f7776`.
- `native/android/tests/private-owner-barrier-map.json`: 222745 bytes, SHA-256 `e2f7c621fe0a15cdc17e3820532bd1bb83d0b051b46a00e66048fc7cfcb06e81`.
- `native/android/tests/run-private-owner-host.py`: 5923 bytes, SHA-256 `03b86998cb2ef3fdaffac360340bf93a36ec7514c7fd639d62264b2f38c8c6be`.
- `native/android/tests/run-environment-platform-host.py`: 9734 bytes, SHA-256 `632aa35dd146371b9614c3c063c7cfbf90d7e7a521b0bfcf68a929fd26aa10a9`.
- `.github/workflows/verify.yml`: 36084 bytes, SHA-256 `99993998b7babd9b85c2c7f8e662720b87b5be82eb8ea787d1effd6191fb5b73`.
- `cli/Sources/MixerBuild/AndroidSDKCompatibility.swift`: 25690 bytes, SHA-256 `65d176da09ca858ef1b045cc172b4197243dbb895ef54de69935f3c1078c694f`.

`source-bindings.json` retains full hashes for all owning blobs read. `resolved-bytecode-anchors.json` retains all 189 clean invocation bindings. `canonical-comparison.json` retains the full 101-input comparison.

Custody and scope limits: producer source code waits for its direct children and removes its owned scratch; the corresponding receipts claim that succeeded. This audit neither observes current process state nor establishes process-group absence, escaped-descendant containment or provider cleanup. Acquisition metadata claims closure of its own urllib and ZIP readers and labels provider-internal disposal unobserved. This reviewer directly observed closure only of its own ZIP reader. No inherited closure claim is expanded to provider disposal.

The prior `android-host-review-r3` review establishes historical fixture context and explicitly required fresh ordinary CI; its older 14,655-check run is not relabeled. `android-motion-thread-review-r2` establishes the isolated R2 history and integration conditions. This review accepts independently checked current CI outputs and exact source bindings; it does not import pair8 results, six-consumer acceptance or native claims from either historical review. Both directories were read without modification. The broader generated-consumer lane was still in progress in the supplied jobs snapshot and is outside this verdict.

Reproduce from the parent root with `python3 -B verification/plan-continuation-2026-11-07/pair9-host-ci-review/audit.py`. The final audit exits 0 with 35,633 checks; exact Python/Git versions, tree, script hash and scope are in `audit-result.json`; Git command/status/output digests are in `git-commands.json`; full input hashes and before/after stability checks are in `inputs.json`. `audit.stdout` is retained and `audit.stderr` is empty. Two initial review-helper failures (profile Sources/ path mapping, then the overbroad assumption that the environment retained class bytes) and corrections remain in `audit-attempts.json`. They did not execute product code or change source inputs.

No compiler, JVM, D8, Swift, native runtime, device/UI/capture action, network request, process probe/signal, delegated child, commit, push or tracker edit was performed. Initial workspace/file listing and subsequent data-only Python/read-only Git were the only inspection methods. Writes are confined to this new review directory. Historical Binder failure and controller-admission preparation failure remain failures; all held groups and retained scratch, physical phones, held v5 startup and frozen hosted lanes remain untouched. No physical-device, API28/32/33/37 runtime, callback restoration/removal silence, immutable external FieldLog package, signing/store, operational, OTA or GA qualification follows.
