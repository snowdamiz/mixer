# Byte indices: unselected source-only construction

This proposes one private layout amendment and an exact source diff against
correction3 `cache_state.rs`, SHA256
`0ab577c36f9836539181ba5156bdfbc7764ea065266e68d94b431da5fdb47ea8`.
The byte-index merge removes the per-output array copies that obstructed
proposal4. It retains six stable merge passes, 384 byte transfers, at most321
pair comparisons, genuine MAX timestamps, and the original public behavior.

`source/cache_state.rs.txt` is a complete proposed source file, assembled from
the immutable C3 source and the three human-authored fragments. The `.txt`
suffix is intentional. It has never been compiled, imported or executed.
`proposed.diff` shows all changes. Canonical product and old packets are untouched.
The sixteen anonymous128-byte clear statements and exact twelve restores are
byte-identical to C3. G6 accounting is owned by another lane and is not duplicated.

The proposal additionally replaces repeated `rr -> ld -> Range/first_chunk`
reads in G2 and G5 with short-lived immutable eight-byte arena views. This is an
explicit private source change needed to close the affected probe/read costs;
it is not an assumption that an old G2/G5 ledger was accepted. There is no new
arena storage, Candidate owner, dependency, public constructor, entry point or
report representation. The arena views end before later mutable arena work.
G2 separately splits the same Candidate and forms mutable timestamp chunks,
then initializes timestamps by direct array assignments with both8-byte moves
charged. Its Candidate views end at the same block boundary as the arena view.

`primitive-grammar.md` defines the source-work model, with every view/Range/
Option/receiver/argument/result component expanded in `operation-ledger.json`.
No whole fat reference, Range or tuple is a scalar primitive. Scalar blocks
contain at most16 events; each actual fixed payload movement has its own copy
group. The G4 event stream has no payload-copy groups and includes all loop,
side-selection and pass administration within768. The ledger assigns every
owned event uniquely to G2, G3, G4 or G5; no other group's margin is used.

These are disclosed authored-source model bounds for the exact proposed
non-test path, subject to independent review. They are not compiler instructions,
runtime measurements, accepted source qualification, ABI/layout measurements,
an accepted29,344-byte union, OTA/release authority or GA evidence. Test-only
atomics remain in their original semantic positions but are excluded from the
non-test budget and need separate instrumentation qualification if executed.

Run `python3 -B run_source_checks.py` for custody, assembly, arithmetic, range,
order, finite transition and cleanup-identity model checks. The runner preserves
every attempt's raw stdout/stderr and status; no Rust/compiler/native executable
is invoked. `verify_packet.py` verifies the frozen packet without overwriting it.
The model is independently written Python and never imports product code.

Computer use, screen capture, simulator/emulator and physical runs remain paused.
No processes were started for those surfaces. This lane performs no Git mutation,
publication or customer messaging. Root selection and independent review must
precede any implementation or compiler/runtime execution of this proposal.
