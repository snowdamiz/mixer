# Independent remaining allocator observer review

No actionable defect was found in the four-file test-only repair against
`020f909f2a32553b79ba7068a1798c85d97426b4`. The reviewed source tree is
`fb2d2daabd21c50f813a32cba8d6f3b321201d7853cc2cfb0832b0130c6265de`.
Only the three original allocation tests and the new legacy adapter differ from
the baseline export; `vm/tests/common/allocation_observer.rs` is unchanged.

Independent source comparison preserves all 69 complete assertion invocations,
including their messages: guest 24, native FFI 25, and streaming validator 20.
Independent unmodified original Debug/Release runs establish the 17 measurement
lines. All four repaired Debug/Release runs, with and without
`MIXER_ALLOCATOR_NOISE=1`, reproduce those lines exactly. Guest occupancy remains
`(16, 8388608, 8388608)`; the deliberate 1016-byte Shared Arc allocation failure
still aborts the child. All 12 streaming allocation faults and the four existing
source/metadata/body cancellation gates remain exercised.

`derived.rs` independently exercises 43 assertions in each of four Debug/Release
and normal/noise combinations (172 derived assertion executions). It uses the
exact retained adapter and existing ledger, linked to the independently built VM.
The probes cover alloc/zeroed/realloc sizes and attempted-call ordinals, source
size hits and largest request, denied realloc pointer/byte retention, size-based
refusal, guard-drop fault/gate disarming, preparation outside an interval,
cross-thread owned resize/free, and allocation work on the cancellation helper
while foreground faults and a cancellation gate are armed.

The source review confirms that the adapter counts each synchronous owner request
before refusing it; successful calls and all frees go through the existing pointer
ledger. It never filters a guest request by its size or fixture identity. Source
size is an observation, and failure size is used only in the existing deliberate
OOM child. Lane ownership starts before the original fixtures and outlives their
destruction. The guard borrows its lane and inherits the ledger operation's
non-Send marker. RAII clears both adapter gates and ledger interval state. The
existing ledger preserves failed realloc ownership and follows an owned pointer
when another thread resizes or frees it. Its bounded table aborts on exhaustion.
The stream test's helper cancels at an observed boundary; it neither acquires
allocation ownership nor consumes foreground fault ordinals.

All 40 owner evidence bindings were checked before and after execution. The
independent run records 137 passing evidence/contract checks. Maximum observed
ledger use was 59 FFI, 26 streaming and 227/229 guest slots out of 4096. Slot maxima
include owned test preparation such as child-process command construction and may
vary with the test invocation environment; all 17 measured outputs stay exact.
Standalone derived compilation emits one unused `MAX_SLOTS` re-export warning
because that probe does not consume it. The owner's targeted warnings-denied
Clippy result and its hash were audited; no independent clean-lint claim is made.

Run `PATH=/opt/homebrew/opt/rustup/bin:$PATH python3 verification/remaining-allocator-observers-review/run_review.py`.
It exports the exact baseline, overlays only the four reviewed files, makes both
snapshots read-only, and builds into separate private original/repaired target
directories. Each cargo/rustc command is bounded to 240 seconds and each derived
execution to 45 seconds. Commands, environment, tool versions, complete logs,
source manifests, retained source archives and artifact hashes are recorded in
`receipt.json`, `source-manifest.json`, and `evidence-manifest.json`.

Two initial independent runner attempts are retained separately. A shared Cargo
target directory reused an original binary; the missing new observer output
made review fail closed, and separate target directories corrected it. A later
artifact lookup assumed a hash-suffixed rlib name; accepting the unique actual
`libmixer_vm.rlib` corrected that runner-only issue. Neither attempt is passing
repair evidence or a product failure.

This review accepts host test instrumentation only. It assumes the explicit single
synchronous test owner; future product allocation workers require ownership on
the allocation thread. The exact synthetic four-call/900-byte replay proves the
old process-global observer was susceptible to unrelated threads; it does not
identify the actual hosted allocation stack or thread. Original failed CI remains
failed pending root's hosted integration. Requested bytes are not process RSS or
a portable ABI guarantee. No physical device discovery or run was attempted;
physical iOS/Android, published consumers, compiler/signing/store/customer/
operational/release and GA qualification remain separate and pending as applicable.
This lane changed only its own review evidence and made no commit or push.
