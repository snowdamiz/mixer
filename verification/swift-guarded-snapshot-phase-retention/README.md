# Isolated conservative snapshot phase retention amendment

This packet changes only `control.rs` and `cache/initial_profile_v1.rs` from the
accepted frozen funding225/source144 tree
`7e3e861ca65d8c6359623443d6a7810b878c1029494a0ae557307d35ed43484b`.
The new source144 tree is
`9c654ec4967f184bcc262c36ac4d65067a3f9d48107f7f9e72789f4cd88960fd`.
The funding acceptance, independent seal and both lifetime reports are hash-bound
in `preparation.json` and `input-lifetime-reports.json`. All frozen inputs remain
unchanged. Canonical product files and root metadata are untouched.

`RuntimeControl::snapshot_commit_storage_v1` still computes the checked previous
plus additional construction total, preflights before committing, and updates
the same actual ticket and construction/combined current and peak counters. It
now returns that already-computed **committed** total. The sole product caller
carries it through its existing tuple/local/field as `retained` (the same byte
length as `previous`). `SnapshotAccessV1::complete` passes that unchanged target
and the existing WASI observation to the existing
`end_construction_phase_with_wasi` normalizer. On a sound unchanged ledger, its
difference is zero, so it destroys the paired phase storage and retains A while
producer diagnostics may still survive. This does not infer that any producer
return/move place or owned diagnostic backing has ended, transferred, or reused
a receiving slot.

All previous source-role charges remain, including distinct A producer and S
receiving roles and the old selected-floor 200-byte charge. The exact accepted
recipe remains **C78,240 / S941,467 / A430,175 / H81,327**. There are no optional
credits, removed-role credits, new arithmetic, runtime locals, calls, type/field
layouts or work actions. Fresh unoptimized MIR from both the exact baseline and
candidate in production and cfg(test) establishes identical roles and bodies for
seven focused functions in each context after only the declared operand and
identifier normalization. `source-delta-accounting.json` records that evidence.
No fresh global inventory or broad runtime suite was performed.

Verification is scoped to pinned **rustc 1.99.0 / aarch64-apple-darwin**:

- Four exact metadata/MIR compiles passed: baseline and candidate, each in
  production and cfg(test). These compile source144 without any test overlay.
- Three standalone executions each passed 174 pure integer/constant controls.
  The reviewed scalar harness is unchanged and uses a clearly synthetic F0;
  its 32/64-bit mathematical cases do not qualify any other native target.
  A fourth compilation returned the expected checked-overflow E0080.
- Sixty-eight exact source, preservation and focused compiler-MIR controls passed.
  An initial control-driver assertion incorrectly expected direct `Ok(copy local)`;
  actual unchanged MIR copies into an existing operand temporary before
  `Ok(move temp)`. The first failed command, exact attempted driver/source and
  outputs remain under `commands/source-ordering-accounting-controls-attempt-1`.
  Only that assertion driver changed before the successful run.
- Ten finite actual Rust control tests passed with 468 unrelated tests filtered
  out. Three separately hashed fragments were appended only to an owned scratch
  copy. They directly set up and verify private finite ledger/ticket/header/
  cancellation fixtures, then execute the actual commit, real private admitted
  or refused completion, and original normalizer. They never call begin,
  adoption, the profile/source loader, the VM, or the writer. This is private
  control-helper execution with a synthetic checked setup, not a source144
  admission or writer execution.

The private controls verify that the actual unit target remains 1,898,105 bytes
(selected with H plus A), the same ticket storage address/owner/category and
three ticket counts survive commit, construction/combined current and peak
bookkeeping is correct, higher historical peaks survive, completion retains A,
and the final conservative ConstructionBound retirement keeps the enlarged
construction charge. Unit execution also asserts existing control/access/storage
sizes 1,720/1,104/5,328 with alignment 8. Missing ticket, owner/category, lower and
upper phase bounds, storage/cancel/layout refusals, and WASI-bearing fault results
are exercised. Paired storage destruction before success or fault is separately
observed with a finite Drop sentinel. The refused real completion leaves its
ledger/fault state unchanged. Since normal same-target completion subtracts zero,
the existing checked-sub underflow branches are exercised by deliberately asking
the unchanged normalizer to shrink against one malformed counter at a time;
this does not claim new corruption detection for a zero-difference completion.

The complete normalizer, error branches, Original path, refused path, writer,
final cleanup, policy constants, fixture grants and fail-closed work stop remain
unchanged by exact source differential checks. **WorkAuditPending** still refuses
before selected A commit/transfer/writer admission. No emission helper or its
hypothetical grant is added. Fixed policies remain 256 MiB and 1 billion work;
300,000/400,000 fixture grants are unchanged and undispatched. No early A refund
or completion suppression is introduced. Original ConstructionBound final
retirement remains deliberately conservative; healthy cleanup is not qualified.

Every compiler, scalar, control-test and source-control command has bounded
owned process-group custody, source and tool bindings, captured output and a
cleanup receipt. Only recorded owned groups are rechecked. Scratch copies,
binaries, metadata and full MIR are removed; only focused evidence remains.
`inspection-failures.json` also records corrected read-only source-path mistakes.
No native/device/simulator/emulator/UI/capture process is started or inventoried,
and no other project's process/data is touched. Native checks remain paused.

Fresh independent phase-retention review remains pending when this producer
packet is sealed. Pre-ingress H/external-harness ownership, full writer storage
and work qualification, genuine caller admission, writer runtime, Linux/32-bit
or other targets, physical-stack/RSS, operational funding, healthy cleanup, OTA,
FieldLog and GA acceptance remain unqualified. This fixes one conservative phase
lifetime boundary; it grants no release authority. Rebuild drivers write evidence
and may only be rerun in a new unfrozen copy after sealing.
