# Corrected atomic storage independent review

Recommendation: **correction required before complete AS05 or repository acceptance**.
The frozen candidate repairs the seven original successful gap reproductions, and
its unchanged 73-case suite passes independently. A new exact-display failure
remains: PostgreSQL and the independent Elixir retained-row checker disagree on
valid control-character escapes. This review does not repair the producer.

The [review receipt](../verification/hosted-atomic-storage-correction-review/receipt.json),
[finding CR01](../verification/hosted-atomic-storage-correction-review/findings.json)
and [source review](../verification/hosted-atomic-storage-correction-review/source-review.json)
bind the recommendation. Root remains accountable for correction selection and
acceptance. The [AS01–AS07 contract](hosted-atomic-storage-corrections.md), original
preflight, original independent review and root correction selection were read
and preserved. The producer checker freshly verifies 269 bindings; all supplied
document, receipt and seal hashes match. Original packet checkers also pass.

CR01 affects `lib/codec.ex:134,141–146` in the immutable producer run6 input.
For U+000B, PostgreSQL stores the JSON spelling `\u000b`, while
`Codec.postgres_display` delegates strings to Jason, which emits `\u000B`.
The same difference affects U+000E, U+000F and U+001A through U+001F. Across 45
independent text boundaries, both typed decoders produce identical CBOR, but nine
exact display comparisons disagree. An actual upload with reason U+000B succeeds,
SQL `row_valid` returns true, and the original bytes replay successfully; the
Elixir retained-row oracle rejects that valid stored row. U+000E and U+001F
repeat the actual-row failure. This is a false rejection of valid rows, without
an observed SQL corruption or unauthorized-success bypass.

The [counterexamples](../verification/hosted-atomic-storage-correction-review/display-counterexamples.json)
retain both complete display byte strings. The
[actual retained rows](../verification/hosted-atomic-storage-correction-review/retained-row-counterexamples.json)
retain all columns for eight uploaded/replayed rows, with explicit hex for binary
columns. A separately authored Python standard-library oracle reconstructs their
CBOR, standard hashes, projections, exact PostgreSQL display bytes and adjacent
edges without consulting the candidate encoder. All eight validate; three are
falsely rejected by Elixir. The failed equality and row-acceptance assertions
remain failures. Correct exact JSON string formatting while preserving literal
backslash-u text and its case; ten literal-escape controls already pass.

| Selection | Independent observed disposition |
| --- | --- |
| AS01 | Actual composites are unconstrained numeric. Nonfinite, fractional, negative and overrange inputs reject before locks. Eight additional tiny fractions retain their evidence and reject; mathematically integral scaled numeric values remain valid. |
| AS02 | Source checks follow all retained-row/predecessor/fault reads, precede replay disclosure and follow DML. The final pre-effect clock follows the last blocking read; only bounded pure encoding and the immediate wall-deadline guard remain before first DML. Actual read/DML waits preserve exact expiry and 45/30-second bounds. A reviewer-only nontransactional sequence proves expired/stale late-read rejection occurs before any attempted artifact/audit INSERT; rollback cannot conceal sequence advancement. The unexpired 139 control executes both INSERT triggers and stores decision/recorded 139. Original monotonic/SQL deadlines remain unextended. |
| AS03 | Bad status/body/size/event and actor/action/target/request associations reject; exact 201 creation and later 200 unchanged replay remain valid, including refreshed credentials for the same immutable principal. |
| AS04 | Nonnull server-derived creation event/actor, deferred same-tenant FK and semantic target/actor/Change1 linkage reject corruption. A later creation event independently validates its nonterminal predecessor. |
| AS05 | Closed typed shapes, canonical numeric/UUID/hex/ID/IP, bounds and time checks reject the prior gaps. CR01 blocks the complete exact-display claim. Actual 312 newline/control/Unicode suffix mutations reject in both decoders; no trailing-newline regex bypass was observed. |
| AS06 | Head, selected cached and creation events validate the required bounded immediate edges. Additional old cached-event and later creation-event predecessor corruptions reject while the head's own adjacent edge is unrelated. |
| AS07 | Fresh catalog bytes exactly match the producer: 22 actual function definitions/ACLs, 19 private pure helpers, two resolver definers and one mutation definer; seven FORCE-RLS tables and four composites. All 19 private helpers also deny actual runtime and foreign direct execution. |

The regex finding uses actual PostgreSQL execution, consistent with its documented
default non-newline-sensitive behavior and absence of Perl's trailing-newline
special treatment. [PostgreSQL 17 pattern matching](https://www.postgresql.org/docs/17/functions-matching.html#POSIX-MATCHING-RULES)
describes those semantics. Root's selected `event_from_display(jsonb)` seam
validates retained JSONB, so normalized raw `1e0` becoming integer1 remains an
accepted representation. No lexical raw JSON parser is claimed. PostgreSQL
[documents numeric normalization and preserved fractional zeros](https://www.postgresql.org/docs/17/datatype-json.html#JSON-INPUT-OUTPUT).

All four fresh executions use owned disposable PostgreSQL 17.11, actual
Ecto 3.14.2/Ecto SQL 3.14.0/Postgrex 0.22.4/DBConnection 2.10.2, Elixir 1.20.4/OTP 29
and the seven accepted archive-verified dependencies. No dependency changed.
All runs observed revision `4250e05a132c04370d5ccb971c9faaf1b82a9395`.
Exact argv, environment overrides, versions, source/dependency/contract copies,
stdout/stderr and proxy observations remain in each numbered run.

| Fresh run | Result | Source and runner digest |
| --- | --- | --- |
| run1 | Original corrected suite 73/73; no implementation/test changes | `a2547bf7e3f0427379eccca27457c122952c00795b38df88067ac9eb1f4ef6f8` |
| run2 | 79/81; I02/I03 expose CR01 | `047516144650ec06677f7741d918e65dc6b000d666c2e5ed0f0d9a8fe441fb8e` |
| run3 | 81/83; same two failures, plus before-DML observation and literal-escape controls | `a6d67a12f388f3d7bea9ff27dbdd7f0d2fc66361d904a25c74699fb5cb6e331b` |
| run4 | 81/83; same assertions fail; exact actual rows additionally retained | `c2b75a2c46787c636e3bfe142c81d4cdc5dc14c43e4b35cde8f4b3b58c51e8c9` |

The unchanged schema/codec/context/blob/bounds/proxy source is copied from frozen
run6. Review cases are appended without changing the 73 existing bodies.
Runner adaptations select owned paths and retain the actual catalog even on an
assertion failure. Run2 predates that diagnostic adaptation and has no catalog;
runs1/3/4 each independently emit the exact catalog SHA256
`5824cfe3629e65e2da8dcf4d831a10f22589a5b2bd38c02bbf58f90d23971883`.
The [adaptations](../verification/hosted-atomic-storage-correction-review/harness-adaptations.json)
and exact diff retain this distinction. Every run repeats the real lost-COMMIT
acknowledgement, actual PostgreSQL restart and fresh exact retry successfully.
No failed attempt was deleted, relabeled or weakened into a pass.

All four owned proxies/clusters/sockets/build/cache/blob/scratch trees were stopped
and removed. The review-only triggers/schema were dropped; no candidate function
was changed. Other projects' processes, native instances and physical phones were
untouched. Physical phones remain disconnected and deferred. No commit or push,
live hosted code/migration, dependency, tracker or prior packet was changed.

Run `python3 -B verification/hosted-atomic-storage-correction-review/check.py`
for read-only frozen-evidence verification; it intentionally verifies retained
failures and does not report the candidate as accepted. A fresh execution should
copy the immutable run4 inputs to another owned packet before running its runner.

This is a synthetic fixed policy/clock/tenant/target storage specimen. Complete
authoritative credential/profile/membership locking, final product DDL/helper
manifest/startup inspector, repository and HTTP composition, actual signed
admission, Neon/R2/Cloudflare/Linux service execution, Oban/domain jobs,
multi-process blob durability, operational/customer/FieldLog and accountable GA
qualification remain pending. Adjacent-edge checks do not prove whole-history
integrity against a privileged coherent offline rewrite; cached-row checks do not
prove original-key provenance against the corresponding coherent privileged
rewrite. Those stronger claims require an independent retained commitment.
COMMIT may finish just after expiry once sent, and disconnect never proves rollback.
