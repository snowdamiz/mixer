# Preserved development failures

The first fixed-host terminal-capacity execution aborted in the actual resource
owner destructor (`CapabilityGuestUIAndroidResources.swift`, then line 178).
Quarantining the pool count alone did not retain the ARC reservation/resource
chain after the last shell dropped. The accepted fixed final-obligation cells
repair that ownership boundary; the original OS diagnostic is retained here.

The caller TaskExecutor probe did not inherit into the unstructured presentation
Task: it recorded one parent job and zero held presentation jobs, then reached its
test-observation deadline. That technique is not counted as a Task-return hold.
A subsequent debugging print incorrectly called synchronizeFile on stdout and
raised NSFileHandleOperationException; it is unrelated to product behavior.
The exact production-byte scheduler probe uses a separate recorded C hook-wrapper
build and cannot be counted as an ordinary uninstrumented execution.

## Final verification refinements

- `runs/regression-tsan-final-1`: launching TSan XCTest through `xcrun` loaded
  interceptors too late. Direct execution of the exact platform XCTest tool with
  the recorded `DYLD_INSERT_LIBRARIES` resolved it; later all-mode regressions
  pass. The failed launcher output remains unchanged.
- `runs/android-final-{1,2,3,4}` retain actual cross-verifier failures: missing
  experimental-header include path, missing C shim include path, an incomplete
  retained Crypto module-only dependency lacking real `bcm.cc.o`/CXKCP link
  inputs, and a final ELF tool-path error after a successful strict link.
  `runs/android-final-5` and the repaired-source replay use actual required
  objects and succeed. No missing symbol was replaced by a stub.
- `runs/tsan-repaired-1/late-progress-fault.log`: a test-only progress register
  saw a legitimate sequence mismatch because the old verification pause did not
  wait for an already-active callback. The fixed verification pause observes
  actual callback/command return before the sequence is sampled; it advances no
  C fence and supplies no result. Repaired-2 passes all ordinary modes.
- `runs/{debug,release,tsan}-probe-repaired-2/fault-after-join.log`: the new
  opposite-order test waited for fault fanout while intentionally parking the
  real reclaim caller that still owned registry admission. This deadlocked the
  verification schedule. Repaired-3 first releases that actual BUSY return,
  then waits for real fault fanout; all modes pass. Production locks were not
  altered to accommodate this test.
- Failed LLDB attempts remain in `runs/lldb-*`: inherited TaskExecutor preference
  did not hold the unstructured presentation Task; a C-expression barrier and
  initial event-loop handling failed; optimized inline frames initially hid the
  actual caller PC and local continuation array; initial cancellation holder
  frames/AST locations could not expose the exact owned Task handle. Later
  receipts identify the precise successful source/binary/driver/frame binding.
  Historical pre-store scheduler holds are not relabeled as post-store proof.
- Independent review found S4R-03 in candidate2: a fault latched after successful
  nonfinal RETIRE but before common finish still allowed C consumer_joined.
  The required narrow beginJoin guard now rejects a fault under its existing
  lock. Candidate2 remains retained. Actual late-progress regression requires
  retirement_done=1, consumer_joined=0 and pinned real resources/capacity.
- `runs/lldb-release-lifetime-final-{5,6}` retain the final optimized Release
  private Swift lifetime-counter attempts. The actual initialized static storage
  symbol and live class reference were located after a completed real owner
  cycle. Release's counter debug type has byte size zero and no fields, so there
  was no type-bound scalar field location. No guessed heap offset or counter
  write was performed. Debug/TSan actual exhaustion proofs pass; Release's
  lifetime-counter dynamic injection remains explicitly unexecuted.
