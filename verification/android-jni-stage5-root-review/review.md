# Root review of the stage 5 JNI proposal

Root accepts the frozen declaration, ownership and verification design, including
the separate closed native backend prerequisite 5N. This is design acceptance;
no Android native receipt, signed execution, physical or GA gate is passed.
The shared appearance prerequisite 5T is being designed separately under updated
product-plan section 8.3. It remains required before visual acceptance.

The review resolved four implementation hazards before freezing:

- Swift's canonical String equality cannot establish raw node-ID byte equality.
  Native ingress must compare the saved identity's UTF-8 bytes before routing.
  Canonically equivalent spellings are tested in separate genuine snapshots;
  the existing reconciler's collision rejection remains intact.
- Public packet encoding must independently narrow custom-limit snapshots and
  bound output while writing. A post-encoding size check alone is insufficient.
- Final weak deletion does not make a JNI slot reusable. The fixed scalar
  release follows the last read, real joins/fences/facade reclaim and zero aliases;
  final resource destruction cannot access the released slot.
- A reserved but never-published slot needs its own acquired-empty rollback after
  known-empty C facade reclaim. Published, staged or uncertain slots cannot use
  that rollback. Repeated successful closes and failed preparations must exceed
  sixteen cycles without losing capacity.

Root also clarified the draw probe's trusted-source scope. A separate real-Window
experiment must establish the marker and returned-stack schedule before enabling
observation. No API name, host fixture, Java flag, reflection-resistance claim or
compositor-pixel claim substitutes for that evidence.

The exact fifteen C declarations compile as C11/C++17 on the host and official
Android API30 aarch64 compiler. The proposed slot record is 64 bytes, alignment8,
with disposition at offset56 on those targets. Javac and javap verify all ten
method descriptors and the constructor against the official Android SDK jar.
Declaration-only Java method bodies always throw and were never executed. Ten
collector regressions pass under both normal and optimized Python. These checks
establish declaration consistency, not a working JNI library or Swift native
backend. All fifty native/visual/external implementation cases remain pending.

Implementation ownership now assigned: root may add only the data-only SDK packet
facility `sdk/Sources/MixerUI/NativePacketV1.swift` and its focused new SDK test file,
then validate and review that bounded slice. It consumes an authoritative snapshot
and creates no native authority. No change to UI-v1 bytes, reconciliation identity,
normal session factories, existing headers or signed core/Prepared is authorized
by this slice. Future 5N shared lifecycle edits, JNI/Java renderer code and 5T
adapter integration require separately coordinated file ownership.
