# Independent review of the retained stage-contract v2 delta

Verdict: **ACCEPT EXACT F1–F3 DOCUMENT DELTA.** No additional amendment is
required by this review. Root must still select any dependent implementation.

Reviewed producer seal:
`f5abac1ca96ee8741e16a9882411c17e9fe9342ab7b0ac76ebfc2c512d5fde82`.
The immutable predecessor contract seal is
`19532e82c9ea9fac5a5edd5dccc5d081d05f2c5fdec2da1689029de0b0b18837`;
the predecessor independent review seal is
`df43d958b53785f7928e826d2f7e72c8151ffafb74252f2cdb2a26b03668b5b4`.
All three raw seal digests, their complete member rosters, member byte sizes and
digests, and canonical member-tree digests were independently checked. The v2
input-binding roster also joins the exact predecessor and review bytes and the
current user-supplied AGENTS.md.

The exact changed contract leaves are:

- `/cross_field_rules/5`: F1 now requires every listed alternative to be mutually
  exclusive and conditions exhaustiveness on `inventory_complete=true`. A
  supported partial path set creates local missing. It cannot supply numbers.
- `/closed_types/copy_source.literal/types/bytes_hex`: F2 compares literal length
  with the extent only when that extent is known. A null extent remains null and
  missing. The independent 1..32-byte literal bound remains mandatory.
- `/cross_field_rules/12`: F3 requires coverage of the half-open operation
  interval on the exact path. A contradiction in an exhaustive known reservation
  is invalid; unavailable or partial coverage remains missing. An unrelated
  unknown cannot hide a supported contradiction.

The five README edits are the sibling provenance note, the partial semantic-review
clarification, and the three corresponding normative passages. In particular, a
partial semantic review may bind a separately complete inventory while storage
facts remain partial. This now agrees with both the inventory/fact distinction
and the completeness joins.

The six new deferred controls are T10a, T10b, T28a, T29a, T29b and T30b. T30's
mutation was narrowed to undecidable coverage. All 46 predecessor controls remain
in their original order and unchanged apart from that T30 mutation. There are 52
unique control IDs with declared outcomes. These are descriptions of future
executable controls; this review executed none of them.

All closed field sets, schema versions, enumerations, resource bounds, outcome
definitions and other contract leaves are unchanged. The exact retained binding,
external root-approval authority, synthetic boundary, original region-union
algorithm, all-or-null local output and zero-added-stage-byte rule are unchanged.
Unknown O/congruences, Body nonlocal unwind, backing capacity/final destruction,
runtime admission, original capture, FieldLog/OTA and GA remain unresolved.

Source references in the producer sibling are README.md:87-105, 166-174,
225-251; contract.json:179, 189, 196; and failure-matrix.json:22-23, 45-50.
`review.json` records exact changed-line and changed-leaf evidence. The stored
`source-delta.patch` was independently regenerated from both sealed normative
documents and compared byte-for-byte.

This accepts a document delta for root consideration. It supplies no complete
inventory, actual map, semantic or root approval, numeric result, implementation
approval, compiler evidence or runtime qualification. No verifier code was
written, imported or invoked. No raw native outputs, UI/native runtime, network,
Docker, database or process probes were used. The bounded source-only check's
command, observed Python version, input-tree digest, output and duration are in
`receipt.json`. No native or capture instance was started; no cleanup is owed.
