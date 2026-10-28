# Independent retained storage-stage contract review

Verdict: **AMENDMENT REQUIRED; dependent implementation remains unselected.**

This is an independent, source-only review of frozen contract seal
`19532e82c9ea9fac5a5edd5dccc5d081d05f2c5fdec2da1689029de0b0b18837`.
It does not review or approve an actual inventory, map, certificate, root approval,
capture execution, numeric geometry, compiler result or runtime behavior.

The reviewed design preserves the immutable verifier-v1 region union and
all-or-null output interface. It adds physical reservation objects and distinct
representation views without adding their bytes to the union. The exact retained
binding, R/Dispatch and C/Caller ownership, raw inventory/review/seal/root digest
joins, external approval authority, synthetic boundary, and explicit unknown
O/congruence/Body unwind/backing obligations are stated. No requirement to resolve
those unknowns follows from this review.

The following are document-level findings, not executed verifier counterexamples.
All three normative sources must agree before implementation.

## F1: Partial inventory versus unconditional path exhaustiveness

`contract.json:103-104` permits `inventory_complete=false`;
`contract.json:186` and `failure-matrix.json:21` permit a correctly labelled
partial inventory. `README.md:71-78` distinguishes complete enumeration from a
partial local review. But `contract.json:189` requires all independently reviewed
paths to be exhaustive without conditioning that requirement on inventory
completeness. A sound partial inventory containing only a reviewed subset of
alternatives therefore has both an explicit accepted partial representation and
an unconditional violated rule. The language could alternatively be read as
letting a partial set self-assert exhaustiveness. Neither reading is an exact
closed contract for incomplete input.

Exact amendment: replace the first two sentences of the rule at line 189 with:

> Every listed path is a source-reviewed symbolic alternative. Listed alternatives
> must be mutually exclusive. `inventory_complete=true` additionally requires the
> independently reviewed alternatives to be exhaustive across the required local
> frontier. With `inventory_complete=false`, a supported subset of alternatives
> may be retained; omitted or unreviewed alternatives create local missing and
> never become evidence of exhaustiveness. No fictitious placeholder path is
> required for an unenumerated alternative.

Keep the remaining shared-prefix, source-anchor, identity and cross-path rules.
Clarify `README.md:87-88` as: "Partial semantic-review status alone grants neither
enumeration completeness nor complete semantic approval. It may bind a separately
complete inventory while storage facts remain partial." This preserves the
explicit complete-inventory/partial-facts case at lines 71-75.

Add controls: a correctly bound partial inventory containing a supported subset
of paths, with all completion joins false as applicable, is retained as local
missing; the same subset with `inventory_complete=true` is invalid when the exact
review establishes an omitted required alternative. Missing alternatives never
produce numbers.

## F2: Literal store with unknown extent has incompatible rules

`contract.json:176` allows `storage_copy.bytes=null`. The literal alternative at
line 179 unconditionally requires its hex length to equal twice that field.
However, `contract.json:195` expressly says that the length comparison is made
only when the extent is known and that a null extent remains missing, never
inferred. `failure-matrix.json:41` also expects unknown copy extent to be missing.
Consequently a literal store whose exact bytes are known but whose reviewed
written extent is unavailable has incompatible validity rules.

Exact replacement for `copy_source.literal.types.bytes_hex`:

> nonempty lowercase hexadecimal encoding of 1..32 exact bytes; when
> storage_copy.bytes is non-null its length equals twice storage_copy.bytes;
> when storage_copy.bytes is null, retain that null and emit local missing without
> inferring extent from the literal

Keep the independent 32-byte bound even when extent is null. Add separate controls
for null extent (missing), known extent/length disagreement (invalid), and known
matching extent (otherwise unchanged). No store initialization or value lifetime
is inferred from this amendment.

## F3: Operation reservation failure needs the known/unknown distinction

`README.md:223-229` and `contract.json:196` require both physical reservations to
cover the entire operation interval. `README.md:244-246` and
`contract.json:193,198` distinguish known contradiction from unavailable facts.
But `failure-matrix.json:43` places "source/destination reservation does not close
over operation" in one unconditional `local_missing` case. This encompasses a
complete known reservation that demonstrably ends before the operation, as well
as a partial/unknown reservation whose coverage cannot be proved. These require
different outcomes under the declared contract.

Exact amendment to the operation rule:

> For each stage endpoint, prove reservation coverage of the entire half-open
> operation interval `[before,after)` on the exact path. If the exhaustive known
> reservation intervals demonstrably fail to cover it, the claim is invalid.
> If an interval, phase, path projection or reservation state is unavailable or
> partial so that coverage cannot be decided, emit local missing. A supported
> known contradiction remains invalid even when some unrelated fact is unknown.

Split T30: unknown reservation coverage remains `local_missing`; a known exhaustive
source or destination reservation that excludes any portion of the required operation interval is
`invalid`. Known cross-path references remain invalid under the existing rule.

## Boundaries retained

The contract's inventory/map bijection, scoped raw-byte custody joins, strict
type/closed-field budgets, physical-slot/view distinction, per-path byte lifetime
coverage, overlap rules, source-kind restrictions, alias identities, stage
containment and zero-added-byte rule are otherwise suitable for the next exact
review. Existing accepted local geometry and the seven v1 grammar gaps establish
neither complete stage enumeration nor factual completeness. An inventory reviewer
still owns the semantic enumeration; a source-only checker cannot replace it.

This review does not require every representation byte or padding byte to be
initialized. No copy automatically establishes initialization, valid values,
backing capacity, final destruction or durability. Unknown facts must remain
unknown and suppress the appropriate output. Actual approval, original capture,
runtime admission, physical devices, FieldLog/OTA and GA remain unapproved.

`review_source.py` verifies selected document/source pins and the frozen packet,
checks the seven saved grammar-source spans, records exact finding spans and
performs bounded document assertions. It never imports or invokes the verifier.
The command and observed tool version are in `receipt.json`. Future implementation
controls, including the original numeric tests, remain deferred; this review
executed none of them.
