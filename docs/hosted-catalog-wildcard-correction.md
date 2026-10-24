# Catalog wildcard and trigger-name raw-domain correction

The isolated candidate corrects **ACSR01 and ACSR02** in `raw_validation.py`.
A zero startup-association OID requires the `*` sentinel. A positive OID still
requires non-null, nonempty, NUL-free UTF8 resolved text and now permits a literal
`*` name. This preserves the existing text domain without adding an identifier
length rule. Every raw trigger `(relation_oid, name)` pair must be unique before
internal names disappear during normalization. Distinct names on one relation
and the same name on different relations remain portable.

The [exact delta](../verification/hosted-catalog-wildcard-correction/implementation.diff)
changes only that validator. All original SQL, schema, roles, functions, types,
capture queries, assertions, normalization and selected comparison bytes remain
unchanged. Selected manifest SHA-256 remains
`78c0c8a56c6d358eda1e8a183176d5fe7b7e67e9427bdeb4aa1bb308dfaa8e6e`.
Candidate source digest is
`3760cbfe5bb28407ce58d678eef22b064a960126d659df031cf11007b789d6d8`.
The predecessor candidate, receipt and final 115-binding independent review are
preserved and verified; the correction does not rewrite their finding oracles.

Fresh model replay passes all **126 original cases** (108 rejections, including
the prior 21 malformed admissions, and 18 portable OID admissions), **1,083 shape
cases**, **8 transport cases**, **3 selected portability controls**, and **136
independent cases**. The only original expected-oracle changes are two legal
positive-OID `*` startup rows and the cloned same-relation trigger-name row in
each shape matrix. Original scripts and explicit adaptation diffs are retained.
The 1,083 matrix now has 1,036 invalid raw rejections and 47 valid unselected raw
controls. Another **24 focused models** cover both startup association fields,
the frozen two ACSR02 observations and portability. The original review's
separate three-case uniqueness probe also freshly replays with **two required
raw/selected rejections and one selected portability admission**.

One fresh socket-only PostgreSQL **17.11** cluster, with **107 padding tables**
and two owned databases, passed **5 targeted cases** containing **11 safe selected
comparisons and 7 selected drift rejections**. Actual quoted role `"*"` has OID
17024 and quoted database `"*"` has OID 17023. Captured startup rows cover zero
database/role sentinels, positive `*` names, and both positive names together.
Raw validation accepts all legal observations; exact comparison still rejects
the additional reachable role/defaults and ordinary trigger/default drift.
PostgreSQL rejects internal/internal, internal/external and external/external
duplicate trigger names with **SQLSTATE 42710**. Both actual name portability
controls remain selected-safe. The fresh baseline has different OIDs and generated
internal trigger names while normalizing to the identical selected manifest.

The original **128 schema cases**, **43 prior controls**, **5 historical finding
observations**, **67 catalog-correction cases**, and **19 ordinary-runtime cases**
(23 safe comparisons / 15 drift rejections) are **reused byte-bound evidence**;
they were not rerun here. The producer's 277-binding and final review's 115-binding
checkers both pass against their unchanged packets. Historical findings remain
observations, not security passes. Neither finding demonstrates an actual malformed
PostgreSQL catalog or ordinary-runtime authorization bypass.

The [frozen receipt](../verification/hosted-catalog-wildcard-correction/receipt.json),
[command and SQL bindings](../verification/hosted-catalog-wildcard-correction/attempt-1/compression.json),
[runtime observations](../verification/hosted-catalog-wildcard-correction/attempt-1/runtime/tests.json)
and [read-only checker](../verification/hosted-catalog-wildcard-correction/check.py)
retain tool versions/executable hashes, source revision/tree digest, original and
adapted input bytes, full compressed output, SQL and cleanup. The observed HEAD is
`e337ddd14236cc94ede4def750a9fde4c461ad3e`, tree
`09a2ecb36e08d49497f9da82c746789be8f47ea5`, on macOS 27.0.1 arm64 with Python
3.14.8 and libpq 170011. The single runtime attempt and all model executions
succeeded. One checker preflight failed because it compared insertion-order
diagnostic strings after sorted JSON serialization; its source, command, output
and diagnosis are preserved under `checker-preflight-attempt-1/`. The checker now
compares the unchanged rejection group sets. No candidate/runtime byte or outcome
changed, and no attempt was discarded. Three expected SQL errors are assertion evidence.
The owned cluster stopped and unique scratch directory was removed. No TCP
listener, other project's process or data, simulator, emulator or phone was touched.

Run the frozen checker without starting a server:

```sh
python3 -B verification/hosted-catalog-wildcard-correction/check.py
```

Independent correction review and root acceptance remain pending. This isolated
point-in-time prerequisite creates no live hosted/SQL mutation or product startup
authority. Concurrent privileged DDL protection, combined domain schema,
HTTP/provider behavior, production operations, signing/publication, native and
physical-phone qualification and GA acceptance remain pending. Phones remain
disconnected. No dependency, tracker, other active lane, commit or push was changed.
