Generated Java runner correction, round 2, November 7, 2026.

The runner and its Python controls address all three findings in
`../generated-java-review/REVIEW.md`. Fresh independent review remains pending.
This task executed no Swift or Java tool, native build, runtime, UI, or capture.
Native work is resumed under the latest user instruction. Native qualification
remains pending, phones remain disconnected, and historical holds remain active.

Only these existing files changed in this task:

- `scripts/ci/check-android-generated-java.py`
- `scripts/ci/tests/test_android_generated_java_runner.py`

All new evidence is in this directory. `baseline.json` records the original
identities of both files and all 14 files in the two sealed evidence directories.
`test-commands.json` confirms that both sealed directories retain the same
file inventories and byte hashes. No tracker, gate, workflow, product source,
commit, push, merge, or delegated task changed in this task.

The command runner records the PID and its owned PGID, the direct-child reap,
separate stdout and stderr EOF observations, the SIGKILL result, and bounded
group-absence observations. Each cleanup operation retains its own error.
Stream and selector closure and diagnostic persistence continue after signal,
reap, drain, or close failures. The top-level receipt also contains every
in-memory command record, so a denied command-receipt write retains those facts
in `receipt.json` when that separate path remains writable. No implementation
can guarantee persistence if all receipt destinations deny writes.

Command success requires a reaped child, observed EOF on both streams,
observed absence of its created group, and no cleanup error. A positive compiler
exit still fails the command, while observed terminal custody permits scratch
removal. Denied signals, denied observations, groups present at the finite
deadline, missing EOF, or cleanup errors retain scratch and fail execution.
An unresolved command also prevents another command from starting. A failed
scratch deletion retains its path and error in the final receipt.

Cleanup probes and signals only the group created by each `Popen` call with
`start_new_session=True`. It performs no process enumeration. The tests inject
denials only for newly owned Python children. Their finalizers clean up those
children after the injection ends. The implementation does not claim to contain
descendants that deliberately escape the created group. No historical held
process was probed or signalled, including the seven listed groups or FieldLog
run 40802230894, PGID 2424, PID 2621. The held v5 startup was not retried.

Both SwiftPM producer modes now select `-j 2`. The receipt records
`producer_jobs`, each successful producer's `jobs` and build argv, and every
actual command argv, including a failed producer command. This supplements the
sealed workflow proposal and README without changing them. The proposed job
invokes the corrected runner and inherits its explicit bound. No workflow is
installed by this correction.

Each of the six consumers now selects official JDK `javap -v -p -c -s` for every
emitted classfile. The selected tool's version and binary hash are checked
before integration and again afterward. Its raw stdout is retained as
`member-references.javap.txt`, with an output hash and exact command argv.
`member-references.json` inventories the constant-pool `Fieldref`, `Methodref`,
and `InterfaceMethodref` entries by owning class. It also binds the complete
classfile input inventory. Missing, duplicate, or unexpected class scopes and
unresolved member entries fail closed. The per-consumer receipt links the inventory hash, raw
output hash, command label, reference count, and scope.

This observation covers pre-D8 classfile references, including unused entries.
The retained verbose disassembly contains the remaining constant pool and
instructions. The extracted inventory does not resolve dynamic invocation or
reflection and does not describe reference changes made by D8. D8 conversion
with `--min-api 28` remains separate evidence and grants no API28 floor or
linkage approval. The official command contract is documented in the
[JDK 25 javap manual](https://docs.oracle.com/en/java/javase/25/docs/specs/man/javap.html).

The six actual consumers remain Debug and Release producers, each with an
original, physically relocated, and CLI-exported consumer. Their complete
18-source Java roster, actual create and export operations, source locks,
full canonical toolchain inspections, source stability checks, six tamper cases
per producer, and dependency checks remain in the executable runner. No Java
source is rewritten or substituted in that integration path.

The expanded suite passes 40 controls normally and 40 with Python `-O` on
Python 3.14.8. The logs and command hashes are in `test-commands.json`.
The controls exercise live-child signal denial, unknown or denied group
observations, separate EOF outcomes, nested reap and close failures,
command-receipt write denial, scratch retention, successful cleanup after a
compiler-shaped Python failure, job selection, and member inventory controls.
They also retain the prior source, lock, tamper, timeout, and output controls.
All test temporary directories were removed. These fake children and dummy
class data establish Python runner behavior only.

The runner retains the existing 160-command, 600-second-per-command,
2,400-second execution, 4-MiB-per-stream, and 64-MiB-total output ceilings.
Cleanup has a separate five-second finite deadline per command. No resource
limit was calibrated against a real compiler in this task. A verbose member
dump that exceeds the retained output ceiling fails closed for parent review.

The next gate is fresh independent review of the two source identities in
`receipt.json`, followed by parent-owned real integration. Actual CLI generation,
all six strict javac and D8 consumers, actual member observations and tamper
refusals, and toolchain postflight remain unrun in this task. APK, API28 floor,
native runtime, physical-device, signing, immutable published-package,
separate-repository FieldLog, and GA acceptance remain pending.

The executable Python gate is:

```sh
python3 -B verification/plan-continuation-2026-11-07/generated-java-fix-r2/run_controls.py
```

The executable real-toolchain gate below is unrun. The parent selects the full
installed toolchain paths and a new output directory after independent review.
The canonical inspection still requires the complete official macOS toolchain,
including Swift 6.3.3, the Android 28 Swift SDK and NDK r27d bundle, JDK 25,
SDK 37.0, and build-tools 37.0.0. `javap` and `dexdump` are explicit prerequisites.
The output path must not exist.

```sh
python3 -B scripts/ci/check-android-generated-java.py \
	--swift "$MIXER_SWIFT" \
	--swift-sdks "$MIXER_SWIFT_SDKS_PATH" \
	--android-artifact "$MIXER_ANDROID_ARTIFACT_PATH" \
	--jdk "$MIXER_JDK" \
	--android-sdk "$ANDROID_HOME" \
	--output "$MIXER_GENERATED_JAVA_OUTPUT" \
	--execute-toolchains
```
