# Isolated clear128 correction3

Correction3 applies only the selected cleanup clear block: sixteen anonymous
128-byte borrowed stores replace the old256 zero-word iterations. Its exact
`cache_state.rs` SHA256 is
`0ab577c36f9836539181ba5156bdfbc7764ea065266e68d94b431da5fdb47ea8`.
The other two library files, all test vectors/oracles and all test expectations
are byte-identical to correction2. The pre-clear prefix, twelve restores and
private fault suffix are unchanged. This isolated closure changes no canonical
runtime, public API, observation/report bytes, semantic budget or sorting code.

Fresh Rust1.99.0 host qualification passes in debug and `-O`. Per mode, the
three binaries pass84 host,108 producer-regression and98 independent-regression
methods, representing122 distinct methods:30 new cache-state methods,78 inherited
producer methods (54 embedded +17 fixture +7 transport), and14 inherited
independent methods. All16 new and9 inherited API dispositions pass per mode,
including the expected compile failures. The actual test executable hashes,
source hashes, PID/PGID, individual60-second deadlines, stdout/stderr and observed
exits are retained. Fourteen owned binaries/rlibs were hashed before deletion;
their children had returned, scratch and bytecode are absent.

Each mode freshly executes29 public actual four-File cases and2 private injected
commit/cleanup poison File cases. The public cases yield27 complete32
observations and2 outer errors with no aggregate; the private cases yield2
complete32 poison observations. Five private stage/guard methods, full32 terminal
precedence and semantic/budget-neighbor controls also execute in the fresh
binary. Private injected states give zero public reachability credit. Source IDs
and raw-output hashes are mapped in `proofs/fresh-qualification.json`.

The existing private byte control checks every Candidate byte for three fills
(6,144 byte comparisons), all twelve restore payloads, and an unchanged8MiB
arena. It covers both ends and every128-byte clear boundary, so another mirrored
test was unnecessary. The private poison test proves suppressed extent and no
dispatch of either later leaf after controlled partial commit/cleanup failure.
All captured input/report bytes and result values match frozen correction2;
that comparison is additional evidence, not inherited credit for this run.
All actual bytes are retained once under `evidence/content`, with fresh-case
timestamps and command provenance in each case manifest.

Twenty-three complete helper/Option/Result layouts are freshly observed in both
modes, including Progress144, Paid24, Loan16, Fixture72, Option<Fixture>80,
observation256, aggregate488 and public Result488. These measurements establish
complete type sizes; they do not establish simultaneous lifetimes or the full
29,344-byte role union. The new anonymous array128 plus live Paid24 is only a
152-byte wire-role subtotal. Other coexisting owners remain explicit and open
in `proofs/phase-lifetime-inventory.json`.

The selected clear-block source model is189 groups:2,768 scalar component
operations in173 blocks plus16 actual128-byte copies. Repeat construction
includes128 element-initialization edges per store. No additional fictional
initializer-array copy, named zero128 local, array promotion, optimizer elision
or alternative32-group convention supplies this bound. The selection and
sealed independent clear review are bound in `proofs/work-boundaries.json`.
The complete G6 helper/staging/commit/cleanup/caller ledger is separately owned
and still pending at this freeze. No637 subtotal or unexplained spare allowance
is inherited.

G128 retains zero-debit guard reply/source/received and caller terminal
installation; G7 retains ordinary paid reply/audit installation. Actual
post-loan cleanup remains G6. The G3/G4 source-model obstacles and complete
phase/lifetime union remain open. Source-work acceptance, lifetime acceptance,
independent implementation acceptance and GA qualification are false. This host
checkpoint does not qualify Rust1.98, Swift/native/physical targets or a release.
Native runtime, capture and UI remain paused; none were started or inventoried.

Three read-only audit attempts failed on a generic-function locator and frozen
evidence-path assumptions; their exact tool source and raw errors are retained
under `evidence/audit-attempt-*`. The corrected audit passes. A preparatory
inspection assumed JSON case files and failed; the actual result/manifests were
then inspected. None was a Rust test failure or required a product/test change.

This closure is frozen separately from all original/correction1/correction2 and
proposal seals. Root may bind the later G6 packet in a new review receipt; this
seal must not be rewritten. Run `python3 -B verify_checkpoint.py` for read-only
custody verification. Runner/audit scripts that write evidence must be reproduced
only in a separate copy of the frozen closure.
