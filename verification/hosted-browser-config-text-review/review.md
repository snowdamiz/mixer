# Independent Config metadata text review

Verdict: no actionable findings in the bounded change. The exact producer source
and test hashes match its accepted snapshot. Review covers `BrowserAuth.Config`,
its two selected test files, and the unchanged digest/identity dependencies.
It does not accept provider trust, authentication, durable sessions or deployment.

The new constructor checks the three trust-matched metadata fields before
construction: profile ID (128 bytes), client ID and API audience (256 bytes each).
It preserves `Encoding.bounded_string?` UTF-8 and byte bounds, and additionally
rejects decoded NUL. The subsequent manifest binding remains exact. Other binary
configuration values already reject NUL through their literal/URL/reference
contracts; no normalization, digest field, version or order changed.

[Run 1](run-1/receipt.json) passes 32 selected methods: 26 existing producer methods
and six independent review groups, zero failures, skips or exclusions. Counts
include overlap with producer acceptance and must not be added to it. The six
independent groups cover exact byte-boundary NUL at beginning/middle/end with an
otherwise valid matching manifest, NUL in every binary field, escaped metadata
keys and duplicate aliases, simultaneous maximum UTF-8 values, exact composed
and decomposed Unicode plus existing controls, and type/empty/overlong rejection.
The baseline remains 910 bytes with SHA-256
`3116d5ef6ac718b3d2442df3648c60ab3fa1d640f73d429ed2b30490f1e2d7f3`.

Six separately computed Python fixed-order JSON and SHA-256 comparisons match
the baseline and five exact Unicode/control-byte vectors emitted by the live
constructor/digest. The independent source/test tree digest is
`5771f7c1c4bf6b16982a41fce0321939ea3c2bdd2f5b77347be6bd3be8e3bd30`.
All selected inputs and dependency BEAM hashes, commands, versions, stdout and
stderr are retained. Owned compiler scratch was removed. No PostgreSQL, native,
capture, browser, provider or application process was started by this review.

The unchanged digest API explicitly requires constructor-validated Config. Its
ability to hash a manually forged Config remains a caller precondition, not
proof that arbitrary structs are SQL/vault-admitted. No scope expansion into
unselected browser storage, provider or endpoint code occurred.
