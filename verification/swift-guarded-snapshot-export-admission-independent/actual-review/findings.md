# Independent review of frozen admission proposal

Reviewed producer seal SHA-256
`b60d1ba0790076b35b6df30dd8df407486f89144e6914f40d2d0d55e4e20e1f5`
after exact root release SHA-256
`d48767359fed33077da8e0bd57dd9bbe72b2f0eae07b00fd4e54f56e263d93fa`.
All 70 producer members / 163,193 bytes verified before review. The independent
35-member pre-release requirements/control packet remains unchanged.

**Conclusion:** useful nonterminal stop/debit and prototype-layout evidence, but
the complete selected-scope/phase ownership contract requires two revisions
before selecting it for an integrated exporter. These are design findings; the
producer explicitly does not implement scope admission/finalization or a writer.
No actual product defect, full Rust behavior pass or operational acceptance is
claimed.

## F1 — P1: specify cleanup before the selected scope can be returned

Producer `design.md:241–258` retains the original admission order, admits a
Snapshot profile foundation in the shared core, then relies on the returned
scope finalizer to restore the captured Original base. It does not specify the
failure exit between successful Construction admission and that scope return.
`prototype/profile_append.rs:17–25` only measures the scope and checks the old
function type; it has no adoption/finalizer implementation to close this gap.

The accepted original `control.rs:684–704` admits Construction, performs a final
`control.check(cursor)`, then on error drops the body/refunds source and metadata
and calls `finish_owned_cleanup`. Cancellation/deadline can become true at that
last check. In the proposed Snapshot profile, that branch has a larger ticket
but no returned scope to consume. Unchanged `finish_owned_cleanup` correctly
retains a Construction charge different from its single known Original base
(`control.rs:1771–1781`); accepting that larger byte count instead would reopen
the rejected counterfeit-floor cleanup route.

Specify the exact pre-return ownership/error result and consuming cleanup for
this branch, including actual early ingress/return/cleanup storage alive there.
Either retire that actual storage to the captured Original base before unchanged
finish, or retain the charge/invariant explicitly without claiming complete
cleanup. Also cover failures before Construction admission and failure while
retiring this early storage. A scope-success-only finalizer does not cover these
branches. Add a bounded control that originates cancellation/deadline at the
original final check after Snapshot Construction admission and proves the real
failure payload plus after-cleanup accounting. This cannot be closed by an
arbitrary bool, caller floor or byte-equality alternate floor.

Fresh independent finite control
`test_post_construction_pre_scope_stop_keeps_unknown_selected_charge` confirms
the required conservative behavior of the unchanged single-floor finish; it is
not an execution of the unimplemented shared core.

## F2 — P2: make the phase-to-guard immutable reborrow concrete

The proposed `begin_snapshot_phase_v1(&'c mut self)` returns a phase retaining
`&'c mut RuntimeControl` until `complete(self, storage)` (`design.md:88–96`,
`prototype/initial_append.rs:3`). The sequence then creates the original direct
guard and uses it for export/header/rows before completing the phase
(`design.md:132–158`). The accepted literal is
`InitialProfileBorrowV1 { cache, control, wasi, scalars }`
(`cache/initial_profile_v1.rs:163`). Directly borrowing that original control
while the phase's exclusive borrow remains needed by complete does not compile.

The producer probes independently compile the phase layout and a guard stop
method (`prototype/initial_append.rs:24–25`); they do not compose phase entry,
the sole guard and consuming retirement. Fresh minimal native compiler controls
using those exact lifetime relations reject the direct sequence with **only
E0502** in Debug and optimized modes. Sources and full JSON diagnostics are
retained under this directory. These controls use opaque stand-in component
types; they establish the borrow relation, not actual Mixer integration.

Specify a private shared reborrow from the actual live phase (or another exact
ownership contract), including both phase-admitted and phase-refused paths,
before creating the one guard. The signature must keep every guard-derived
borrow within that shared reborrow and let the real phase be consumed only
after all guard/views end. The additional reborrow/Option/Result/argument/return
places belong in the final accounting. A separate feasibility control with an
added `shared_control(&self)` compiles in both modes; that demonstrates one
possible direction, not acceptance or modification of the producer design.

## Evidence that holds, with its scope

- Freshly carried all 25 frozen independent Python/File controls; five additional
  independent formula/pre-scope controls pass. Real duplicate, independently
  opened, hardlink and symlink File handles are rejected by actual kernel
  `(dev, ino)` identity before writing in the independent host controls.
- Independently decoded all six recorded LLVM constant contexts and reconstructed
  every byte of both 144-member compiled-source preimages from accepted source
  plus exact prototype additions. Shell=29,256 and common-core delta=8,536 match
  the retained constants. Scope=5,984 unit /5,936 production also matches. This
  validates attribution of those prototype measurements, not complete/minimal
  runtime floors or live admission behavior. Unit is Debug only; production has
  Debug and optimized constants. No full Mixer compilation was replayed.
- Independently recalculated the proposed maximum: extent 69,765,152; records
  109,184; words 331,716; blocks 17,033; calls 545,056; P+R=2,611,235,080. The
  default 1,000,000,000 ExecutionWork budget refuses that envelope. This is a
  preserved diagnostic refusal, not a reason to increase a grant. P remains
  consumed if R refuses. Source-level operation-count coverage remains a
  required implementation audit, as the producer itself states.
- The actual prototype immutable stop method reads the original cancellation,
  actual carried deadline/origin and exact copied existing first failure without
  mutation or cloning; its debit updates original ExecutionWork only after a
  successful checked addition. Full expected cache/WASI pairing and conditional
  storage admission remain explicitly unimplemented, so the weaker prototype
  ticket helper is not accepted as that algorithm.
- Output alias, before/after syscall checks, call-32 behavior, original I/O plus
  post-stop retention, actual consuming cleanup and unchanged original eight
  payloads are sound requirements in the document. Its Python models are not
  actual wrapper/File/cleanup executions. Full conditional source-place layout
  closure and the selected entry/result/finalizer places remain pending. The
  410,672/410,040 partial sums are not complete floors or grants.
- Only the released root pure-encoder selection contract was read. Its bounded
  block-production interface still needs later work/stop composition; none of
  the active encoder implementation was read. The proposal's per-word/per-record
  stop promises must be reconciled with that actual interface during integration.

No producer/frozen/canonical files changed. Tiny compiler outputs were created
only in an owned TemporaryDirectory and removed; all subprocesses completed.
Python bytecode emission was disabled and host alias fixtures were removed.
Native/device/simulator/emulator/UI/capture/process inventories stayed paused.
No new grant, original-wrapper execution, publication, commit/push or GA claim.
