# Frozen review and bounded reproduction

Do not run prepare.py or run_checks.py in the frozen producer directory. The default seal verifier and input verifier are read-only:

```sh
python3 -B verification/swift-real-profile-loader-binding/seal_packet.py
python3 -B verification/swift-real-profile-loader-binding/verify_inputs.py
```

For full actual-loader replay copy this entire packet into reviewer-owned scratch, preserve source144 and host11, and update only the copied run_checks.py ROOT constant to `/Users/andreyyurlov/Documents/dev/mixer` if the copy's nesting changes HERE.parents[1]. Run the copied script with python3 -B. It writes only its own HERE and scratch, fixes compiler/runtime environments, bounds each child to60 seconds/256KiB output, terminally waits all children and removes owned scratch in finally. It launches no native/mobile/UI/capture runtime and reads no active producer lane. A changed copied runner is deliberately hashed before its own new compilation, so replay gets new valid build/session context; never relabel its bytes as this frozen run.

Pure reusable functions in run_checks.py (import does not run main): packed(values), env_packed(mapping), identity_bytes(source_path), build_record(parts4,compiler_digest,output_bytes), session_record(source_path,source_digest,build_bytes,binary_bytes,nonce,budget5,argv,env_without_two_identity_keys,cwd,scenario), manifest(folder), ident(path). Record builders return bytes; identity helpers observe actual files. They do not mint Rust carrier authority. Actual launcher logic in main, with closed compiler variables and OS nonce, remains part of the trusted scope.

The unit filter is `experimental_swift_reactor::retained_profile_loader_v1::tests::`; actual selected-loader child is `actual_selected_loader_child`, run with `--exact`, `--nocapture`, `--test-threads=1`. Without a launch context that method returns before loading and is not a genuine loader pass. Main emits a genuine original-validator fixture, runs13 helpers, then launches each real scenario with its actual retained source/build/session/preimage/env context. See sessions/, source-preimages/, session-observations.json and build-preimage-{debug,optimized}.bin for exact consumed bytes. Native invalid-UTF8 pathname creation fails with EILSEQ92 and is not counted as loader execution.

Independent private tests may append a test-only child include inside a copied `retained_profile_loader_v1.rs`. This grants tests access to private helpers/fields without changing the original module. Keep variant manifest, exact append bytes, fixture identity, flags, compiler/runtime identities and outputs. Compile-time identities bind the exact copied tree/build, so a genuine launch against a modified tree must use a newly emitted build/session, never the frozen binary's old claims.

The producer's positive/negative compiler cases live in compile_cases/. All23 new type sizes are measured in actual Debug/optimized unit binaries; separate ordinary-production metadata variants append only const size/alignment assertions and establish equality in both configurations. Source/type measurement is separate from physical stack/RSS and operational reservation acceptance.

Historical attempts01..06 preserve first orchestration/compiler failures and narrower passing attempts. Their paths in command receipts describe original execution locations; archived logs/preimages are under the corresponding attempt directory. Attempt05 passed101 commands but did not retain session preimages/bind the runner/compare production layouts. Attempt06 passed103 with those gaps closed, before the per-run validation-error peak correction and its large malformed-input regression case. Final receipt and source manifest identify the reviewed implementation; do not count historical source as final.
