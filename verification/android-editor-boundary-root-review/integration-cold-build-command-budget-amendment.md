# Bounded cold compiler and packaging commands

Root selects a maximum180-second external qualification-command budget for one
fresh Android integration cold Swift compiler/build/test-bundle preparation or
full unsigned generated-driver packaging command per selected source/flag/config
context, followed by bounded cleanup/reap. Tool invocations yield progress to the
controller; no UI/native runtime or process inventory is authorized.

This changes only the coordinator-imposed60-second build-command harness bound.
The frozen integration contract requires Debug/Release and complete generated
consumer evidence, but does not require all cold compiler work to finish within
60 seconds. Several unchanged complete builds passed near52 seconds while other
cold build attempts reached56/60-second harness bounds. Repeated partial cold
builds are not evidence of a product deadline failure and need not be replayed
indefinitely. Preserve every original timeout and distinguish compiler/build
wall-clock evidence from actual product behavior and runtime limits.

Keep product source, assertions, all VM/capability/request deadlines, reservations,
thread/owner invariants, JVM behavior-test limits and source/BCI qualifications
unchanged. Existing source-fixed Swift initial-profile/row component command
budgets are not amended. The larger budget applies only to currently selected
Android CLI/host integration build-support commands, recorded by exact argv,
source, compiler/configuration and output. It grants no product timeout waiver,
performance claim, native execution or complete integration acceptance.

Prefer the already selected compiler/build-system flags. A different build
system is a separately named context and cannot silently replace a failed one.
Do not combine overlapping heavy Swift compile retries: coordinate CLI and host
build phases, continue independent source/review/JVM work, and retain the exact
final selected context and bounded child cleanup.
