# Independent conservative phase-retention review

The frozen two-file amendment passes this bounded independent review. It
returns the already checked and committed construction total, forwards that
same existing `usize` through `retained`, and supplies it to the original
completion normalizer. With the checked unchanged ledger, completion destroys
the phase storage, subtracts zero, and retains the A charge. This closes the
early-refund boundary while producer diagnostics may still be live. Root
integration and any writer release remain separate decisions.

Inputs are bound in `audit.json`: the root release hash is
`12627178051e0747ce835af0f22f44eab5d69e563f86dcf0a210b1cdf9f11f23`,
the producer seal is
`623b5ec0b8ef7c2f68b344c191f9a6d2f5fd93b3085c7f0b4ae02c960c895001`
(254 members / 21,540,355 bytes), and source144 is
`9c654ec4967f184bcc262c36ac4d65067a3f9d48107f7f9e72789f4cd88960fd`.
The accepted constants-only baseline is source144
`7e3e861ca65d8c6359623443d6a7810b878c1029494a0ae557307d35ed43484b`.
All frozen inputs were verified before execution and again before sealing.

Thirty-four immutable-input, exact-differential, call-site and evidence-custody
checks pass. Independent reconstruction requires exactly seven replacements
across `control.rs` and `cache/initial_profile_v1.rs`; the other 142 source
members are byte-identical. A search across all 144 source members finds the
single commit method and its sole caller. The complete normalizer, Original
branch, refused branch, writer, outer retirement, final conservative cleanup,
policies, fixture grants and constants remain byte-identical. The accepted
recipe stays C78,240 / S941,467 / A430,175 / H81,327. No old role, producer
return/move place, S receiving place, or conservative 200-byte floor charge is
credited or removed.

Four fresh exact metadata/MIR builds pass on pinned rustc 1.99.0
(`b940084d7eb6a299eb4bfeb8e34901bc051e7ac4`) for aarch64-apple-darwin:
baseline/candidate in production and cfg(test), without overlays. The seven
focused functions per context contain 290 declared MIR roles in total, with
identical names/types before the binding rename and no added roles. Their full
MIR bodies match after the same-length rename and the one existing return
operand read are normalized. Calls, arithmetic, branches, validation, traversal
and debit actions do not change. This is focused compiler evidence, not a new
global inventory or physical stack/RSS measurement.

Eight independently authored host tests pass with 468 unrelated tests filtered.
They run the actual private commit and real admitted/refused complete, using
three separately hashed fragments in a disposable copy. The finite fixture
constructs and validates the actual private ticket/header/backing/ledger pair;
it does not call begin, adoption, a source/profile loader, the VM, or the writer.
The admitted test retains the same ticket storage address, owner/category,
current/peak counters and ticket counts, then denies one extra byte at an exact
combined ceiling. Higher historical peaks and zero additions survive. Atomic
commit refusals, missing/owner/category/bound completion faults and WASI
observations survive. Real-shrink controls execute both checked-sub underflow
branches, and a Drop sentinel observes phase destruction on success/fault.
Refused completion keeps its malformed ledger and existing fault. Final
retirement still records ConstructionBound and retains the enlarged charge.
The unchanged unit layouts are control 1,720, access 1,104 and phase storage
5,328 bytes, each aligned to 8.

The private completion shim additionally creates the actual SnapshotAttemptV1
failed-export type containing an io::Error with owned diagnostic backing. That
backing has the same address and has not been dropped after real complete; it
is dropped exactly once afterwards. This is a synthetic liveness witness, not
a genuine writer result or selected ingress. Exact source review separately
confirms export exists before complete, moves into SnapshotOuterV1 afterwards,
and remains in SnapshotRunV1 / SnapshotPrimaryRetirementV1 and returned finish
diagnostics. Retaining the full ticket avoids assuming those producer places
or their owned backing have ended or reused the S receiving slots.

The original baseline is also compiled with the same independent overlay
(only the old field spelling differs). One exact regression test fails with
the expected exit 101 after real completion: the same ticket address/owner/
category holds 1,467,930 bytes instead of 1,898,105. The candidate passes that
test. Original failure output is preserved. Two pre-execution review corrections
to the independent filter/expected error are recorded with exact earlier files;
they caused no failed command. Producer's earlier failed MIR assertion and
expected E0080 overflow evidence remain frozen and were reviewed.

The first independent freeze check used string path ordering to compare a
manifest collected in Path ordering; it rejected identical per-path byte/hash
data. The exact driver and observed failure are retained. The corrected check
keeps the original manifest order and validates every source/overlay byte/hash.
No product or executable-test failure resulted from this packet-driver error.

The unchanged normalizer retains owner, bound and checked-sub code. A
same-target zero-difference completion cannot itself expose counter underflow;
the underflow tests deliberately request real shrink on malformed counters.
The product path holds exclusive control access while exposing only a shared
borrow during export/header/rows. This review adds no new corruption detector.
WorkAuditPending still refuses before A commit, transfer and writer admission.

Compiler/runtime children have bounded owned process-group custody, captured
output, exact command/environment/tool/source bindings and reaping receipts.
Only those recorded groups are rechecked. Disposable scratch, binaries,
metadata and full MIR are removed; compact focused evidence remains. Canonical
code, Git and root metadata were not edited. No native, simulator, emulator,
device, UI or capture runtime was started or inventoried.

H pre-ingress/external-harness ownership, complete writer storage/work funding,
genuine admission, writer execution, healthy cleanup, operational qualification,
other compilers/targets, native checks, OTA, FieldLog and GA remain pending.
This packet grants no production or release authority. Reproduction drivers
refuse after sealing; use a new owned unsealed copy to rerun them.
