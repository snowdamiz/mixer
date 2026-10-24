# Independent catalog raw-domain correction review

The frozen correction passes this narrow independent review. **ACSR01 and
ACSR02 are closed in the copied raw-input contract**, with no additional finding.
Root selection and acceptance remain pending. The candidate source digest is
`3760cbfe5bb28407ce58d678eef22b064a960126d659df031cf11007b789d6d8`;
its producer receipt SHA-256 is
`cc82538ba0709c831cf2b0579109a93cd419a972318fb84576e8ec03071d295f`.

Direct source comparison confirms the complete delta changes only
`raw_validation.py`: zero startup-association OIDs require `*`; positive OIDs
retain the existing non-null, nonempty, NUL-free UTF8 text domain, including
literal `*`. No identifier-length rule was added to resolved startup names.
Every raw `(relation_oid, name)` trigger pair is checked for uniqueness after
field-domain checks and before internal names disappear during normalization.
The check includes internal and external triggers. Same names on different
relations and different internal names on one relation remain portable. SQL,
schema, functions, roles, types, capture queries, assertions, normalization and
the selected comparator remain byte-identical to the predecessor. The selected
manifest retains SHA-256
`78c0c8a56c6d358eda1e8a183176d5fe7b7e67e9427bdeb4aa1bb308dfaa8e6e`.

The 96-binding correction checker and the preserved 277-binding producer and
115-binding independent-review checkers pass. A separate frozen-copy replay
recomputes all **126 original boundary cases** (108 rejections, all 21 historical
malformed cases rejected, 18 portable OID admissions), **1,083 shape cases**,
**8 transport cases**, **3 selected portability controls**, **136 independent
cases**, **24 focused cases**, and the **3-case uniqueness replay**. Original
scripts, negative-control findings and each exact oracle adaptation remain
preserved. The only shape-oracle changes admit two positive-OID literal-star
startup rows as valid unselected raw shapes and reject the cloned same-relation
trigger-name row in each shape matrix. The uniqueness replay requires both
historical impossible pairs to reject while retaining its portability admission.

Another **133 independently authored model cases** pass. They cover both
association fields, all zero/positive sentinel combinations, OID type/range
failures, empty/null/NUL/invalid-UTF8 values, trigger collision order and all
internal/external combinations, portable names, and malformed trigger names
before pair construction. Long valid resolved text remains admitted by the raw
model, explicitly preserving its existing text contract; those synthetic values
are not claims about actual PostgreSQL identifier lengths. Four predecessor
negative controls still reproduce both literal-star false rejections and both
impossible-pair admissions, while the corrected source reverses exactly those
raw outcomes. Model inputs are separate from actual SQL evidence.

One new socket-only PostgreSQL **17.11** cluster with **131 padding tables** and
two owned databases replays the byte-bound targeted DDL harness, with none of
the broad schema/runtime suites invoked. All **5 targeted cases** pass, producing
**11 selected-safe comparisons**, **7 selected drift rejections**, **3 actual
duplicate-trigger SQLSTATE `42710` rejections** and **2 actual trigger-name
portability controls**. Quoted role `"*"` has positive OID **17096** and quoted
database `"*"` has positive OID **17095**. Actual captured rows cover positive
role with zero database sentinel, positive role scoped to the ordinary database,
positive database with zero role sentinel, and both positive literal-star names.
All raw observations validate; added reachable roles/defaults and ordinary
disabled-trigger/default drift still reject selected comparison. The fresh
baseline has different relation OIDs and generated internal names from the
producer's fixture while normalizing to the same selected manifest. PostgreSQL
rejects internal/internal, internal/external and external/external duplicate
trigger names; distinct names on one relation and the same name on different
relations remain selected-safe.

The original **128 schema cases**, **43 prior controls**, **5 historical finding
observations**, **67 catalog-correction cases**, and **19 ordinary-runtime cases**
(23 safe comparisons / 15 drift rejections) are **reused byte-bound evidence**,
not freshly executed suites. Historical finding observations remain observations,
not security passes. Neither finding demonstrates a malformed actual PostgreSQL
catalog or an ordinary-runtime authorization bypass.

The [review receipt](../verification/hosted-catalog-wildcard-review/receipt.json),
[input archive](../verification/hosted-catalog-wildcard-review/input-manifest.json),
[model observations](../verification/hosted-catalog-wildcard-review/attempt-1/model-review.json),
[runtime observations](../verification/hosted-catalog-wildcard-review/attempt-1/runtime/tests.json)
and [read-only checker](../verification/hosted-catalog-wildcard-review/check.py)
bind reviewed source, original archives and outputs, exact commands and SQL,
tool versions/executable hashes, compression hashes and cleanup. The observed
HEAD is `9f314ebb07096136d8c90438ce7e8c8a2387502b`, tree
`3162c37758b4869e860ef3b785e7dd29628d120f`, on macOS 27.0.1 arm64 with
Python 3.14.8 and libpq 170011. The sole independent review execution succeeded;
no review failure or attempt was discarded. The producer's historical checker
preflight failure, original checker and diagnosis are retained unchanged. The
three expected SQL errors are assertion evidence. The owned cluster stopped
and its unique scratch directory was removed. No TCP listener, other project's
process/data, simulator, emulator or physical phone was touched.

Run the frozen review without starting PostgreSQL:

```sh
python3 -B verification/hosted-catalog-wildcard-review/check.py
```

This review accepts only the isolated point-in-time raw-domain correction. It
creates no live hosted/SQL mutation, product startup inspector, current-authority
or domain-writer integration. Concurrent privileged DDL protection, combined
domain schema, HTTP/provider behavior, production operations, signing/publication,
native qualification and GA acceptance remain pending. Physical phones remain
disconnected and deferred to final acceptance. No dependency, root tracker,
other active lane, commit or push was changed by this review.
