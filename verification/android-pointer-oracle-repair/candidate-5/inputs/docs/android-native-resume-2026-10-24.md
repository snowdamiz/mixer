# Android appearance runtime revalidation

The current private Android appearance consumer passes its resumed API37 emulator
run. Candidate 16 executes the exact twelve native product/harness files previously
compiled in `headless-section-4`, including the Section width and baseline repairs.
The run passes 570 main assertions, 120 first-baseline assertions, 120 last-baseline
assertions, 14 inset assertions and five separately installed rejection fixtures.
These counts describe separate suites, not independent implementations.

Section cases cover centered ZStack, intrinsic HStack, header-only and wider-child
sections, wrapped headers, nested list-row sections, and selected first/last native
baselines in both directions. Unsupported control baselines still reject. The main
suite retains actual Activity/AssetManager/native View, input, selection/composition,
identity, stale-state, attachment failure, rollback and retirement coverage.

The collector records 180 successful commands, exact installed APK hashes, compiler
and tool versions, a source snapshot and nine current hardware/compositor capture
scenes. Root verified the sealed inputs, unchanged native source, all command logs,
335 archived build artifacts and cleanup, and visually reviewed Section LTR/RTL,
first-baseline RTL, last-baseline LTR and the shared fixture captures. Frame-committed
hardware/compositor correspondence is a same-platform freshness check; it does not
establish cross-platform design parity.

The owned read-only/no-snapshot instance reused the existing AVD on port 5586 and
was stopped after collection. Both owned ports and its process were absent after
cleanup. The unrelated running emulator was preserved. No physical phone was used.

The [root receipt](../verification/android-native-appearance-v2/candidate-16-root-review/acceptance.json)
and executable `verify.py` bind this development acceptance. Earlier failed runs,
headless receipts and pre-repair native captures remain historical evidence. This
receipt supersedes their current-source native-pending statements only for the
private Android consumer subset exercised here.

The ordinary engine/JNI/native coordinator join, public V2 bootstrap, complete
font/resource and OS support, iOS/Android design comparison, accessibility workflows,
published FieldLog qualification and final physical/store/operational/GA gates
remain pending. API37 emulator execution does not establish API28 runtime support.
