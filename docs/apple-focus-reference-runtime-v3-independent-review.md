# Apple reference-first runtime v3 independent review

**Rejected for native dispatch.** The frozen V3 importer still rounds some
original decimal timestamps before deciding whether they have whole-nanosecond
precision. Three independent hostile controls return a strict diagnostic pass
where the documented contract requires invalid/incomplete evidence and an
unknown input count. The production importer precision path needs a separately
versioned repair and independent review before root selects a native run.

The composed auxiliary inventory repair passes every exercised valid and hostile
control. This finding does not require changing the retained compiled products,
the strict oracle, Session, TransactionStore, or the original V2 review failure.
No native execution or release acceptance is granted by this review.

The reviewed producer handoff SHA256 is
`f50006ea6fbe274eac4a78c214a33da4b77c4249b0ef2e8a19f1e0c4200e18f1`;
the packet SHA256 is
`89e4b9b819bacc7ba69aee1fa2344245bf2eb26a3b8ed72a33a169f574f3fd60`.
The reviewer model/effort is `gpt-6.1-sol`, `xhigh`. Root owns integration and any
fresh native selection. The binding product scope and repository instructions
were read; no hosted catalog-inspector/authority-driver source was accessed.

| Control set | Observed outcome |
| --- | --- |
| Retained producer suite | 111/111 pass, no skips/errors |
| Retained focused repair suite | 25/25 pass, no skips/errors |
| Exact original reviewer replay | 32/33 pass; required invalid direct-commit fixture failure retained |
| Newly authored independent suite | 34/37 pass; three decimal precision failures, no errors/skips |
| Additional exact-input reproduction through actual adapter with fake tool returns | 5/8 pass; the same three precision failures reproduced |
| Newly authored composed auxiliary inventory controls, included in the independent suite | 25/25 pass |

## R1: ambient Decimal precision silently changes an authoritative endpoint

`decimal_timestamp_ns` in the frozen producer's `importer.py`, lines 69–74,
multiplies the original Decimal by `Decimal(1_000_000_000)` using the ambient
Decimal context. At the observed default precision of 28 significant digits,
that multiplication rounds sufficiently long fractions. The subsequent
`scaled == scaled.to_integral_value()` comparison inspects the rounded value,
so it cannot detect fractional information already discarded.

These are the exact original JSON tokens and observed conversions:

| Original raw timestamp token | Selected role | Observed integer ns | Expected outcome | Actual outcome |
| --- | --- | ---: | --- | --- |
| `1792893615.123456789000000000000000001` | Official premise | 1792893615123456789 | Reject unrepresentable sub-ns endpoint | Strict diagnostic pass; count 1 |
| `1792893615.999999999999999999999999999` | Official premise | 1792893616000000000 | Reject; selected baseline is later than the original endpoint | Strict diagnostic pass; count 1 |
| `1792893620.123456789000000000000000001` | Official returned witness | 1792893620123456789 | Reject unrepresentable sub-ns endpoint | Strict diagnostic pass; count 1 |

The second control supplies baseline and unchanged-after signatures with mtime
`1792893616000000000`. An independent integer coefficient/exponent comparison
confirms that this is **later than the original premise token**. V3 rounds the
premise upward to that same integer and accepts the baseline. This contradicts
the zero-tolerance original-endpoint ordering contract. The first and third
controls demonstrate that nonzero fractional information can also disappear
without an upward carry.

Every counterexample is explicitly synthetic host evidence. The internal
`provenanceAccepted=true` result is the consistency result inside an intentionally
created host capsule; it does not attest an authentic Apple result or demonstrate
native keyboard delivery. All broad `runPassed`, complete-case, cursor, keyboard,
carrier and GA flags remain false even in these erroneous diagnostic passes.

The additional reproduction exercises the actual frozen adapter's
`capture_official` path, including its auxiliary inventory and first export
binding. It uses fake summary/tests command returns and synthetic result
directories. Original raw manifest bytes, official traversal strings, attachment
bytes, application captures, observer data, root selection, cleanup input,
converter output and returned result are preserved separately for each case in
[precision-reproduction-1](../verification/apple-focus-reference-runtime-v3-independent-review/precision-reproduction-1/receipt.json).
The same defect therefore reaches final import through the adapter; it is not
limited to a direct converter unit call or decoded-float fixture.

The repair should establish exact representability from the original decimal
coefficient/exponent, or use another bounded operation that cannot round before
checking integrality. Increasing a fixed context precision merely moves the
failure boundary. Preserve rejection of genuine fractional nanoseconds, the
original raw lexemes, zero clock tolerance, and the unchanged-after case.

Positive controls accept raw nine-digit premise/witness endpoints exactly and
reject the same signature at endpoint +1 ns. The ordinary ten-digit token
`1792893615.1234567891` rejects correctly. Those successes do not cover the longer
fractions above. No producer implementation or validator was edited to obtain
these outcomes.

## Actual composition and provenance boundary

The review imports copied sources from the complete 31-file selected closure and
constructs the actual composed Bridge. Valid Settings start and AX/PNG uploads
pass through the actual Session and TransactionStore, retaining their normal
summary, canonical journal sequence, UUID attempts, hard links and payload names.
The producer's complete 276-request Settings replay plus real Bridge
begin/ready/resume/reset/baseline flow also passes its retained control, producing
the expected before/begin roles with synthetic application acknowledgments.

The new independent composition controls reject same-byte journal and payload
replacement, an additional external hard link, orphan payloads, retained ancillary
failure files, an earlier attempt's ancillary failure or unresolved retirement,
boolean receipt times, foreign session generation, duplicate JSON fields,
symlinked attempts/outcomes, duplicate outcome ownership, swapped staged journals,
a guard retained after later successful commits, unrecognized summary members,
summary-only verdict/observation claims, boolean summary generation, a foreign
application command, missing first/middle journals and a payload renamed as a
different witness. Complete inventories and rejection reasons are preserved in
[control-results.json](../verification/apple-focus-reference-runtime-v3-independent-review/attempt-1/control-results.json).

Accepted auxiliary inventory returns no application roles before actual app
captures exist and explicitly reports
`authoritativeApplicationEvidenceCreated=false`. Settings metadata and bridge
summaries cannot fill missing native return evidence. The importer keeps a
passing premise with missing return evidence unknown, rejects unbound public
caller dictionaries, validates exact integer command generation and all four
signature fields on both samples, and allows genuinely unchanged observations.

The original 33-control replay remains unchanged. Bridge construction and valid
Session start now accept, while the old probe's direct TransactionStore write of
`{'record':'host-only-independent-synthetic-payload-publication'}` rejects with
`Closed Session journal/identity required`. Its original assertion that all three
stages accept remains the sole historical failure. The separate actual
Session.observe/chunk publication controls pass. No whitelist or validator
weakening was introduced to claim 33/33.

Source review confirms that dispatch checks the reviewed packet and the separate
out-of-band root selection hash before loading composition. The root selection
binds one fresh owned simulator, baselines, source/product identities and the
pinned developer directory. Actual command completion, observer V2, unique
official executions, first attachment export, result/session identity, immutable
in-process capture and all five cleanup operations remain required. The final
adapter revalidates auxiliary files and rejects changed app capture bytes. Python
private tokens are trusted-code conventions rather than process isolation.

## Frozen evidence, reproduction and cleanup

Independent file/archive verification ran before producer imports. All 307
bound files, including historical handoffs and failures, were rechecked after
testing with identical rows and binding-tree SHA256
`202a3e44b5a319f44b1bbc10c2af0f2ea80003118fa3bad482fdb7f041384b7a`.
The official SDK version alias was resolved only to its pinned canonical SDK
target and rehashed. Tool binaries were read as files rather than invoked.

The selected runtime tree SHA256 is
`649ac759761d2cf59ee01cc5d367d6b7fded42407e7150a25dd8b2468361841d`.
The accepted 39-source tree remains
`696bfdd8a31be7b4d9ba49f57783625c7edbb75c126bb4696e31acc5aa0f238a`;
the 55-product archive remains
`0941185e39cc0171b0bf5d2aeb72738588e88b9c7b3d676f893b70c3bf644fa8`.
The compilation revision label `ba9ad4372f94463ba4d363cdfd76dd565c96413f`
is inherited; exact frozen hashes define this review, with no Git query.

The executed commands are:

```sh
/opt/homebrew/opt/python@3.14/bin/python3.14 -B verification/apple-focus-reference-runtime-v3-independent-review/bindings.py
/opt/homebrew/opt/python@3.14/bin/python3.14 -B verification/apple-focus-reference-runtime-v3-independent-review/run_review.py --attempt 1
/opt/homebrew/opt/python@3.14/bin/python3.14 -B verification/apple-focus-reference-runtime-v3-independent-review/reproduce_precision.py
```

Python is 3.14.8 on Darwin 27.0.0 arm64. The full suite receipt SHA256 is
`fffd0b044e7f076927bf3d12e7d4df675563be9841f1b0c48bd6c8e460c0206d`;
the exact-input adapter reproduction receipt SHA256 is
`1c19aa91be155356acbcb15a87c2d3c0f2646e3d97115d666131f859f94ad6dc`.
They record commands, versions, source/input/output hashes, full failed
assertions, guarded host probe programs and actual cleanup.

All owned temporary product/source/probe directories were removed. Inspection
source copies, executable reviewer programs, every attempt, counterexample and
log remain under the owned review directory. No producer/live/shared state,
strict oracle, product archive or Git state was modified. No compiler, native
command, simulator, emulator, phone, UI/capture or service was run; no other
project was touched.

This review qualifies host consistency only and currently rejects the V3
production importer precision path. It cannot select or approve a native run,
attest keyboard delivery, prove platform parity or immutable published FieldLog
use, or satisfy signing, store, customer, operational, accountable-reviewer,
physical-phone or GA gates. Physical phones remain disconnected and deferred.
Root will separately decide on a fresh run only after a repaired version receives
independent acceptance.
