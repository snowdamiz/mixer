# R39 distinct Activity fixture

Built one unsigned APK from R36 with exactly one test-source change: add `Intent.FLAG_ACTIVITY_MULTIPLE_TASK` beside `FLAG_ACTIVITY_NEW_TASK`. The manifest package/target is `dev.mixer.fieldlog.distinctactivities`. The R36 log tag and phase probes remain exact.

Compilation and D8 completed in 4.211 seconds under the 60-second budget; packaging and alignment completed in 3.479 seconds under the 15-second budget. One javac and one D8 invocation; no Swift or JNI rebuild. All owned build command groups were observed absent. Raw command arguments, process identities, exits, versions and outputs are in `compile-1/`. Input tree hashes are in `compile-1/inputs.json`.

Exactly 226 non-instrumentation classes and all 18 native libraries match both R36 and R24. Source restoration verifies all original R24/R20 assertions, cleanup and PASS text. The actual DEX contains every R36 probe message and the complete original PASS text. APK entries other than manifest/DEX are preserved. The unsigned APK is frozen read-only, SHA-256 `78578248427dd6048f6904ce169e61e8afb74d4f42f32ee4b851d94828de21ff`.

Root must sign and run the component in `handoff.json` for its one bounded 90-second runtime attempt. No runtime PASS is claimed. No devices, ADB, Git, signing, delegated children, canonical metadata/source edits, held reads or publication were used. All writes are confined to this fixture namespace and its fresh userdata build directory.
