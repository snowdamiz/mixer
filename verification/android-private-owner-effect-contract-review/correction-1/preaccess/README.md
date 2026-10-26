# Correction-1 preaccess review plan

Candidate access is not authorized in this phase and no correction candidate
was inspected. `review-plan.md` is the immutable snapshot of the initial
correction-review document. `plan.json` carries its finite obligation IDs and
review phases. `receipt.json` records the original bindings, verified original
member identities, local tool identities and exact context commands.

`seal.py capture` writes the one preaccess snapshot; it does not read or execute
candidate files. `seal.py check` re-verifies this preaccess seal and original
member hashes. Do not rerun capture after the candidate arrives. Later authorized
review evidence belongs in the sibling `review/` directory, preserving this seal
and all original review members.

Adding this root-authorized correction directory means the original review's
closed-directory membership check is no longer the appropriate directory oracle.
Its 77 explicitly sealed members and original manifest stay immutable and are
independently hash-verified instead; this is not an original packet refresh.
