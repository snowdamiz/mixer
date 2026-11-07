Independent generated-Java runner review, 2026-11-07

Verdict: changes required before real toolchain execution. Root reports that no
real toolchains have run. This review executed Python controls only and did not
approve a compiler, native/UI, simulator/emulator, or physical-device attempt.
The reviewed source identities and commands are in `receipt.json`.

1. P1 — unknown command cleanup still permits scratch deletion.
   `scripts/ci/check-android-generated-java.py:211-228,459-469` sends SIGKILL to
   the runner-created group and waits only for its direct child. A successful
   kill syscall does not establish group absence. Normal loop completion implies
   pipe EOF, but the receipt does not retain either stream's EOF observation;
   timeout/output-limit cleanup closes streams without establishing EOF.
   Neither PID/PGID nor an actual group-absence observation is retained. If
   killpg or child.wait raises, execution skips stream/selector closure and the
   commands.json write. The outer catch records a failure, then unconditionally
   removes scratch, although descendants may still own it.

   Pure Python reproduction injected a killpg PermissionError for a newly
   created Python child: run raised before reaping/closing/persisting its
   terminal receipt. The review harness then killed and reaped that same owned
   child and verified its group absent. A separate execute-boundary control
   injected the unknown-cleanup outcome at the producer boundary and observed
   its custody sentinel deleted and `owned_scratch_removed: true`. It remained
   status failed; this control does not claim the status itself became passed.

   Required correction: retain PID/owned PGID, direct-child reap, separate EOF
   observations, signal result and bounded group-absence result, including
   cleanup errors. Persist diagnostics through nested cleanup failures. Gate
   success and scratch removal on observed terminal custody; retain scratch and
   a failed/unknown cleanup receipt otherwise. A plain compiler failure whose
   owned group is absent and pipes reached EOF may still clean up normally.
   No enumeration or signalling of unrelated/held processes is needed. This
   asks for facts about the created group, not containment of arbitrary escaped
   descendants or a general process supervisor.

2. P2 — SwiftPM producer concurrency has no selected bound.
   `scripts/ci/check-android-generated-java.py:407-410` supplies neither -j nor
   --jobs. The pure execute-boundary control captured that exact argv without
   executing Swift. Sequential Debug/Release producers do not bound the jobs
   inside each build. Root reports other native lanes are bounded to two jobs
   on the shared 15-core/48-GB host. Add an explicit two-job bound (or another
   root-selected finite bound) before execution and record it in receipts and
   the proposed workflow/README. A jobs bound is a resource selection, not a
   performance conclusion; no OOM or slowdown was measured here.

3. P2 — requested member-reference observation is not implemented.
   `scripts/ci/check-android-generated-java.py:257-265` invokes dexdump and checks
   only emitted class descriptors. It retains classes/DEX and the tool's ordinary
   output, but performs no explicit member-reference extraction or disassembly
   step and has no member-reference observation in its receipt. Capture actual
   class/DEX member references with an official tool, retain the command and
   output identity, and state the observation's scope. This is an evidence
   completeness correction, independent of the execution-safety blockers above;
   it does not require or establish full API28 compatibility qualification.

Source findings that support the proposed integration shape:

- Both producer modes use the actual SwiftPM-built CLI in distinct fresh scratch
  builds. Each invokes actual `create --platform android` with explicit SDK and
  adapter inputs, actual export, and physical rename for relocation after the
  original compilation. No runtime inventory/create replacement was found.
- Canonical driver inspect is actually invoked, and actual create's owning Swift
  implementation also invokes its bundled driver's real inspection. Full
  toolchain identity is compared with the consumer lock and again postflight.
  The tool inputs select official Swift6.3.3, Android28 Swift SDK/NDKr27d,
  JDK25, SDK37.0 and build-tools37.0.0; this review did not execute those tools.
- Source-pair .7 pins SDK22/adapter24 and all 18 emitted product Java sources.
  Generated Java is read directly from actual consumers and never rewritten by
  the runner. The original, moved and exported inventories must match across
  both producer modes. Each locks canonical descriptor bytes, source digests,
  source topology and the exact rendered driver/template. These checks compare
  emitted copies; they do not count transformed canonical source as generation.
- All six compile invocations select the complete 18-file roster against the
  SDK37 jar, Java17 bytecode, strict lint/Werror, no annotation processing and
  empty sourcepath; D8 selects min-api28. Producer Debug/Release is correctly
  distinguished from APK configuration.
- Six negatives per producer use its actual exported consumer and actual CLI
  and copied driver. First-four generic digests are recomputed; named refusals
  and absence of .mixer staging are required. This is an actual-execution plan,
  not evidence that those integration refusals have already happened.
- The original tests clearly label fake data/children as Python controls. The
  README/pure-controls receipt preserve the real integration's unrun status.
  The workflow is only a proposal with explicit worker/path prerequisites;
  no installed job, hosted inventory or CI result is inferred.

Verification performed:

- Supplied suite: 26/26 passed normally, 26/26 with Python -O.
- Independent review controls: four reproductions passed normally and with -O.
  Their pass means the reviewed gaps reproduced, not that fixes passed.
- Python-only logs, command identities, interpreter identity, Git revision/tree,
  source hashes, and cleanup are retained in this directory. The injected-cleanup
  reproduction used an owned Python sleeper; it was killed/reaped, its pipes
  closed and its owned process group observed absent by the review harness. All test
  temporary directories were removed. No existing process was inspected or
  signalled.

Acceptance remains conditional on the custody and job-bound corrections, their
meaningful Python controls, a fresh review of the changed source, and parent-owned
real integration. Actual Debug/Release generation, all six javac/D8 closures,
actual tamper denials, member-reference observation and toolchain postflight are
unrun. APK, runtime, API28 floor/linkage, signing, immutable published packages,
separate-repository FieldLog consumption and GA gates remain unqualified.

Ownership was restricted to this directory. No product/runner/test/workflow
source, status/graph/gate, commit, push, merge, child task or CI dispatch was
changed by this reviewer.
