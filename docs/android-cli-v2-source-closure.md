# Android generated renderer source closure

The internal V2 renderer adds seven Java compile dependencies. The CLI's explicit
adapter snapshot now exports those dependencies alongside its five existing Java
sources. Each exported source is copied byte for byte and included in the adapter
digest in `mixer.lock`. Checklist features and instrumentation remain excluded.

A fresh CLI build creates a real Android consumer with these twelve sources.
The snapshot regression, exact byte/digest checks, production Java 17 compilation
with warnings as errors, and D8 minimum API28 conversion all pass. The complete
generated consumer, class archive, DEX, source snapshot and command receipts are
retained under `verification/android-cli-v2-source-closure/candidate-2/`.
This is the earlier Java-only checkpoint. The current generated app source and
native link are captured by `verification/android-generated-v2-bridge/candidate-3/`.
Candidate1's commands passed, but its final source guard rejected concurrent
renderer corrections. It remains a failed historical attempt.

This preserves generated V1 builds as internal renderer dependencies evolve.
It does not enable V2 in generated apps or package a V2 appearance descriptor.
Private staged engine exports and JNI ownership now have separate host and
cross-build evidence in `docs/android-generated-v2-bridge.md`; Activity
coordination and actual generated V2 native execution remain pending. Compilation
at minimum API28 does not qualify the V2 consumer's API36+ runtime requirement.
