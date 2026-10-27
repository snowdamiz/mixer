# Independent retained-profile composition review

Disposition: **required corrections before product implementation selection**.
This review accepts no new product contract, source, real binding, native check,
release authority or GA gate. Root explicitly classified both findings below as
required corrections. The original producer 26-pass result is preserved and is
insufficient to establish the claimed retained-owner lifecycle.

Reviewed input: preparation seal SHA-256
`c7a8ead8257b8e13543c4fb3bb3ed385513f83080c960a58333b617d05c44860`,
41 exact declared members, plus only seal.json and the exact root-selected
self-seal sidecar. Source-tree SHA-256
`fd3c6972e040cb038a5e59d0836eba0c8315c3c4c2eb230f1c82925e5aeed13b`.
No candidate member was read/imported/executed before successful custody.

## R01: Closed retained wrapper can authorize a reused descriptor

Required correction. `prototype.py:103-108` closes descriptors and clears fds,
but keeps fd, links and initial metadata. `idle` at110-112 only checks child-live;
`check` at114-125 and `hash_range` at185-202 do not check an owned/open lifecycle
state. The retained-entry composer at322-343 checks only concrete type, sizes,
offsets and cached identities.

The unchanged-source control closes one Retained, then opens the unchanged same
path with a fresh Retained. The same ordered walk reuses the same descriptor
numbers. `hash_range(stale, ...)` succeeds even though stale.fds is empty and
the new wrapper owns all12 descriptors. The accepted digest is
`427408c65f1bfe046e5a9911ae7f08db654e2fe271f7c903032f79a62138ee6a`.
No path rewrite, inode/metadata restoration, malicious child, external process
or descriptor-number forcing is used. The test asserts refusal and fails.

Preserve this exact control. Select an explicit lifecycle/ownership contract:
once close begins or succeeds, a wrapper must not read, seek, check, lease,
compose, or adopt through its saved numeric descriptors. Invalidating saved
handles and requiring the currently owned open state must prevent a fresh
wrapper from reviving an old wrapper. An integer descriptor plus matching
metadata is insufficient evidence of continuing wrapper ownership. Qualify
actual close-to-reopen and stale-wrapper use through the real retained entry.

## R02: One close exception aborts every remaining ancestor close

Required correction. `_close` at54-58 always removes the descriptor from the
registry, including on close error. `Retained.close` at103-108 stops at the first
exception before attempting the remaining descriptors or clearing its list.

One unchanged-source control actually closes the leaf, then injects an OSError
report from that call. The remaining11 known owned ancestor descriptors remain
actually open, as verified by fstat on this control's captured descriptor set.
The test asserts no stranded remaining handles and fails. This is an injected
reporting-fault schedule, not a claim that a real kernel close fault occurred.
Reviewer cleanup subsequently closes only those known owned ancestors; final
owned registry and scratch counts are zero. That cleanup does not make the
candidate control pass.

A second root-requested bounded control injects the error before actual leaf
close. fstat confirms that known-owned leaf remains open, but `_close` has removed
it from OPEN_FDS. The test asserts continued ownership accounting and fails.
Reviewer cleanup retires the exact captured12-descriptor set before opening any
new descriptor. It does not blindly retry an uncertain real OS close: this test
alone knows its injected exception precedes the syscall. A real uncertain-close
branch needs a separately selected platform policy.

Preserve this exact control. Define terminal cleanup failure semantics before
implementation: continue bounded cleanup of independent remaining owned
handles, retain the original failure together with cleanup failures, and record
every uncertain descriptor state explicitly. Do not infer closure because a
registry entry was removed. A failed close may leave descriptor state unknown;
blindly retrying a saved numeric descriptor can target a later reused handle.
Quarantine uncertainty and prevent healthy-zero/reuse claims until the selected
platform contract establishes safe retirement. No proposed correction may
silently replace the original composition failure with a later cleanup error.

## Bounded positive observations

The exact four copied Python members replay all26 producer methods, including
307 leaf-preimage mutations. These remain synthetic fixtures. Six of nine
independent methods pass; three controls for R01/R02 remain raw failures, with no test expectation
changed to classify their acceptance as success.

- The exact source tree and41-member packet verify. Initial exact-closure refusal
  for the previously unlisted seal.sha256 is retained. Root then selected only
  its exact76-byte self-seal content as metadata, and corrected custody passed.
- Source inspection maps all six ValidatedSwiftReactor fields, eight complete
  metadata buffers with capacity/charged/category/items, ten usage fields and18
  observation fields to the proposed snapshot record. Signature/import/function/
  global/export/segment spans and fields, declarations, both optional limits,
  policy/revisions, ordered34 imports and provenance are represented. Additional
  independent missing-key and accounting-preimage controls pass. This is a
  source-field mapping; no actual Rust exporter is compiled or executed.
- The eight preimages are separated by explicit record magic/role or exact raw
  bytes. Baseline/candidate roles are domain separated. The proposed digest DAG
  does not include a final selection/profile digest inside its own preimage.
  Actual manifest completeness, build-to-binary, selected event/layout/session
  schemas and owner provenance remain pending, as dependencies P01-P04 state.
- The zero-claim512-byte original transport is a separate immutable byte value.
  The independent control checks all eight original claim ranges are zero,
  rejects an individual nonzero byte in every slot, and verifies exactly256
  nonclaim bytes preserved while only[128,384) changes in the separate final
  header. Actual accepted helper output/original typed-result custody is absent.
- The producer positive control writes exactly2,560,512 bytes, verifies retained
  body/whole-profile/subrange identities before and after a terminal child, and
  retains the same synthetic writer's body fd. The copied child adopts exactly
  two inherited descriptors. The successful and injected-timeout children are
  actually terminally reaped. The child is fixed and trusted; its writable output
  fd, script-path execution and Python interpreter are not an admitted product
  executable or hostile-consumer custody protocol.
- Independent arithmetic confirms the stated source-level explicit read/write
  call and requested-byte maxima, including21 parent EOF passes and585 visible
  retained descriptors. These exclude Rust exporter, original transport/result
  receipts, Python allocator/library/kernel/CPU/time work and real-context phases.
- A separate no-process Nonterminal model executes three bounded wait attempts,
  two kills, and confirms two owners stay leased with24 retained descriptors
  quarantined. This is a modeled source branch; no actual stuck OS child exists.
  Reviewer-only model retirement occurs after recording the lease. It proves
  neither real OS quarantine persistence nor healthy cleanup of a stuck child.

## Original state and pending authority

The proposed outer result preserves the original eight outcome variants and
describes NotAttempted for tags1-5/7 and pre-guard6, Attempted for post-guard6
and8, with exporter failure separate from original header/row outcome. It adds
no ninth original variant. Source inspection finds the intended same-guard seam
consistent with the predecessor's sole guard literal, subject to actual-source
implementation and lifetime review. `protocol-types.rs` remains deliberately
uncompiled; repr(C)/repr(u32) creates no measured layout, privacy test, work
reservation, or compiler receipt.

The record does not retain actual original validation budget/build/session facts
in the current owner. Those need a genuine producer and same-input-load/source
equality, rather than caller digests or reconstruction from usage. Actual metadata
capacity growth and supported serialization caps need reconciliation. The17-word
invocation budget, original typed terminal/raw bytes, optional pre-meter cursor,
applicable errors/work/instructions, all15 final consumption joins, refund versus
quarantine and8192-byte selection/result/custody context are not implemented.
The producer correctly lists them as P01-P08 dependencies. No matching synthetic
header/record can discharge those dependencies.

Production foundation269,080 and unit269,616, headroom71,200/71,688 and prepared
bound330,960/331,496 remain distinct predecessor facts. The accepted451,173,376
scalar remains abstract callsite-action plus requested-I/O only; it is no bound
on actual retry/callback/CPU work and no allowance for this composition.

Canonical integration, actual semantic replay/private CLI/full historical target,
new compiler/CI/native/mobile/UI/device, separate-repo immutable FieldLog package,
OTA/store/customer/operational/GA acceptance remain pending. Native/runtime/UI/
capture and process inventories were paused throughout this review. No process
inventory, UI automation, native run, prohibited hosted import/read/execution,
canonical edit, commit, push or publication was performed.

## Evidence and reproduction

`input-custody.json` verifies the exact frozen package. `source-custody.json`
binds copied executable members to the producer source tree. Raw producer replay
is producer-replay.stdout/stderr plus replay/test-results.json. Raw independent
assertions are independent.stdout/stderr and independent-results.json.
`initial-custody-failure.stderr` preserves the initial metadata closure refusal.
`receipt.json` records actual commands, tool/source identities and cleanup.
`seal.json` closes this finite review packet; seal.sha256 names its exact bytes.

From the repository root, host-only reproduction is:

```text
python3 -B verification/swift-retained-profile-composition-independent/verify_custody.py
python3 -B verification/swift-retained-profile-composition-independent/prepare_replay.py
cd verification/swift-retained-profile-composition-independent/replay
python3 -B test_preparation.py
cd ..
python3 -B test_independent.py
```

The last command is expected to exit1 with three unchanged control failures for
the two required lifecycle findings. The first8-method6-pass/2-failure result is
retained separately in history/first-eight-controls.
Do not run the producer run_evidence.py: it rebuilds producer custody and evidence
from live inputs, outside this review's ownership.
