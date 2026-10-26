# Independent Android owner CI integration review

The repaired `android-owner-host` job passes this bounded CI integration review,
conditional on root delivering the complete required source closure and observing
the remote Linux/JDK 17 result. No product host suite was rerun. This review
accepts neither native-owner semantics nor the entire verification workflow.

The current workflow is 16,072 bytes, SHA-256
`d38e911270bc2660de414d7d62dd53bad54948ce2577af899dfb9b4ad9d96d41`.
The dependency metadata is 20,682 bytes, SHA-256
`4a0217a472d34db72ac4e6e0f25d3b352a8793b1cf5148f2f6110b1ab7ddf76f`.
The exact comparison against HEAD proves the only workflow addition is this job
and the only dependency metadata addition is the external OpenJDK toolchain
entry. Existing jobs were not behaviorally reviewed. The new metadata paths do
not belong to the frozen native309 or CLI356 input maps. Both invoked runners
still match their exact identities in both maps.

The job selects `ubuntu-24.04` and requires `JAVA_HOME_17_X64`. It invokes the
unchanged private-owner JVM runner for closures A and B, with no `--skip-matrix`,
then the unchanged observer JVM runner. Its job cap is 15 minutes and the three
step caps are 5, 7 and 2 minutes. Nonzero runner exits fail the step/job; subsequent
ordinary test steps skip. The `always()` upload step covers all three
`runner.temp/android-owner-*/` evidence directories, uses a commit-specific name
and keeps artifacts for 14 days. It warns when evidence is absent, so an error
before evidence creation remains visible in Actions logs. Whole-job timeout,
cancellation or upload-service failure can prevent artifact retention.

The independent syntax probe found a concrete problem in the original job:
`The runner's official JDK 17 is required` inside the quoted `${VAR:?word}`
expression was rejected by this Mac's Bash parser as an unmatched apostrophe.
All three original extracted scripts returned syntax exit 2. Root replaced the
three error words with `Official JDK 17 is required`; all three repaired scripts
now pass `/bin/bash -n`. Ruby's YAML parser also accepts the repaired workflow and
dependency file. The original failed workflow, extracted scripts, raw parser
errors and reviewer receipt remain under `attempts/initial-shell-failure/`.
This does not claim an observed original failure on Ubuntu's Bash version.

The earlier local recipe receipt remains immutable. It binds the original
16,111-byte workflow hash
`ff6d502622115a722476a98e858e45a4ad9c94b7c679c0f92da810c66047bf65`.
The separate `workflow-message-fix-disposition.json` proves the repaired workflow
differs only by those three error messages, removing 39 bytes; all three product
runner commands remain byte-identical. No product behavior rerun is necessary
to verify this shell-only repair, and the historical receipt is not represented
as having used newer workflow bytes.

The retained local evidence used actual Homebrew OpenJDK 27 with `javac
--release 17`, strict warnings, disabled annotation processing, and explicit
empty class/source paths. Its raw summaries report closure A's 216 cases and
1,101 assertions, closure B's 14,477 checks, and the observer's 162 cases. These
are three different units and are not combined into a test-method count. All 17
nested command results and stream hashes verify, as do current source bytes and
retained input snapshots: 89 entries for A, 92 for B and 31 for observer.
Owner class-map hashes and retained Java 17 classfile headers verify. Observer
class hashes remain recorded in its receipt, but its removed scratch class
bytes cannot be reopened independently. The tools' launcher hashes match the
receipts; they do not bind every runtime library. Source revision fields are
context only; exact source hashes are authoritative.

The owner runner bounds each stream to 4,000,000 bytes, ordinary commands to
60 seconds, the host matrix to 300 seconds and JVM heap to 256 MiB. The observer
runner uses ordinary command deadlines of 45 seconds, a 30-second host deadline
and 128 MiB heap. Its existing `communicate()` streams have no byte-output cap;
the new CI step/job time caps still apply. This limitation is unchanged and is
not counted as a new product acceptance result. Both runners reap owned children
and remove owned scratch; the retained local receipts report completed cleanup.

Delivery requires all paths in `delivery-dependencies.json`. The reviewed union
contains 199 required paths; 155 are currently untracked, comprising 154 native
paths in the pending canonical delivery and this additional mandatory input:

`verification/android-private-owner-integration-implementation/barrier-map.json`

The map is source-bound at 217,766 bytes, SHA-256
`065099211419b03e3f6988db175f7445f43efce2c37f2fb0140f41889ea335a8`.
The required roster and canonical descriptor are already tracked. Workflow and
metadata delivery alone is insufficient: root must include the pending canonical
native/CLI files plus the barrier map. Later source changes require fresh exact
bindings before reusing these local receipts.

The review itself executes 13 parser/version/read-only Git commands. It starts
no JVM product suite, native runtime, simulator, emulator, phone, UI automation,
capture or process inventory. It makes no source/workflow/dependency edits,
staging, commit or push. Remote Ubuntu 24.04 with JDK 17, the separate native-owner
review/witness, paused native/phone checks, immutable published FieldLog use,
signing, stores, operations and GA remain pending.
