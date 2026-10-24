# Authority catalog raw-shape correction candidate

The [selected ACR01 correction](hosted-authority-catalog-shape-direction.md) is
implemented in an isolated copied inspector and awaits independent review and
root selection. The entire original **126-case** boundary matrix passes with
an explicit changed oracle: the prior **21 malformed admissions now reject**,
all **18 uint32 OID portability controls still pass**, and the total is 108
rejections and 18 admissions. These are model-input observations, separate from
actual PostgreSQL evidence; ACR01 did not demonstrate an ordinary-runtime
authorization bypass.

The [receipt](../verification/hosted-authority-catalog-shape-correction/receipt.json),
[read-only checker](../verification/hosted-authority-catalog-shape-correction/check.py),
[exact implementation delta](../verification/hosted-authority-catalog-shape-correction/implementation.diff),
and [delta manifest](../verification/hosted-authority-catalog-shape-correction/delta-manifest.json)
bind this candidate. Candidate source digest is
`7e2a24ec2aad45d07d2dd8a5d581fa8df5966e841981d20b27c75acd1de74b40`.
The separately selected expected manifest remains byte for byte unchanged at
SHA-256 `78c0c8a56c6d358eda1e8a183176d5fe7b7e67e9427bdeb4aa1bb308dfaa8e6e`.
There is no reselection path in the new replay driver.

The only inspector changes are a new raw validator and two import/invocation
lines that call it before normalization. Every original schema, function, role,
type, SQL capture query, resolver algorithm, lock order, normalization rule and
original assertion remains unchanged. The predecessor packets, live product
source, dependencies and trackers were not edited by this lane.

Raw validation covers all nine enforcement groups, all nine fresh-session
fields and the unchanged legacy object's nested shapes. It requires exact
keys; bool/int separation; positive or optional uint32 OIDs; nonempty valid
UTF-8 text without NUL; the platform's 63-byte identifier payload bound;
int16 ranges and valid trigger event/timing combinations; nested ACL, config
and parent objects; nullable values; and resolved/wildcard association
consistency. Duplicate JSON keys reject during decoding. List entries and
semantic duplicates are preserved; exact selected comparison continues to
reject extra multiplicity. Internal generated names and deparsed internal DDL
can vary only after their raw domains have passed. No generated-name or OID
field is deleted before validation.

The final added matrix has **1,083 whole-shape cases**: 1,037 malformed raw
inputs reject directly at raw validation, and 46 valid but unselected shapes
pass raw validation while exact selected comparison rejects them. It includes
nonempty synthetic ACL/default/parent values even though those groups or fields
are absent/null in the selected safe state. Eight strict transport cases reject
duplicate keys and non-JSON numbers, and three additional selected portability
controls admit. The checker reruns these model cases in memory and verifies
that validation does not mutate its input.

One fresh Unix-socket-only PostgreSQL **17.11** cluster, with **73 ordinary
padding tables** outside the protected schema, replayed **128/128 original
cases**, **43/43 prior controls plus all five historical observations**,
**67/67 catalog-correction cases**, and **19/19 independent ordinary-runtime
cases**. The five historical observations retain their original finding
oracles and are not security passes. The independent runtime copy preserves
all 19 ordinary cases byte for byte; its two former model observation groups
are separately retained in the original review script, and the new boundary
matrix explicitly applies the changed ACR01 oracle.

The fresh raw relation OIDs and internal FK names differ from the frozen
review capture, while normalized safe state matches the original selection.
Actual renamed/recreated internal FK behavior remains portable, actual extra
FK multiplicity rejects, and the independent observations retain 23 safe
comparisons and 15 deployment/session rejections. Three distinct actual runtime
backend PIDs preserve the exact login/session identity. The original catalog
correction retains its ordinary invalid/unready concurrent-index-build receipt.
`index live=false` remains model coverage only; this packet claims no runtime
concurrent-drop liveness receipt.

All numbered attempts are retained. The first successful exploratory boundary
run had 1,063 added cases; its post-execution snapshot is explicitly labeled.
The final 1,083-case run snapshots source and scripts before execution and
checks that they remain unchanged. One read-only capture-count preflight helper
failed by decoding an explicit `.json.gz` path without decompression; its exact
source, output and hashes are retained, and the checker handles that path.
The first frozen checker execution also exposed a binding-helper error: it
decompressed an explicitly copied `.gz` input before comparing that file's
original compressed-byte hash. That failed checker, manifest and output are
retained; copied inputs now use their exact bytes for binding checks. No runtime
or boundary attempt failed, and no additional SQL matrix was needed.

The actual runtime and final model executions observed HEAD
`e337ddd14236cc94ede4def750a9fde4c461ad3e`, tree
`09a2ecb36e08d49497f9da82c746789be8f47ea5`, Python 3.14.8, PostgreSQL/psql/pg_ctl
17.11 Homebrew, libpq 170011, and macOS 27.0.1 arm64. Source, input, dependency,
tool, command and output hashes are retained. Large JSON outputs are losslessly
compressed with original/compressed hashes. The sole owned cluster was stopped
and its unique data/socket scratch root removed after evidence collection. No
TCP listener, other project's process, simulator, emulator or phone was touched.

Verify the frozen packet without starting anything, from the repository root:

```sh
python3 -B verification/hosted-authority-catalog-shape-correction/check.py
```

To reproduce in a new unused output directory (the driver refuses overwrite):

```sh
python3 -B verification/hosted-authority-catalog-shape-correction/run.py --out /private/tmp/mixer-catalog-shape-independent --oid-padding 79
python3 -B verification/hosted-authority-catalog-shape-correction/run-boundaries.py --out /private/tmp/mixer-catalog-shape-boundaries
```

This is a point-in-time prerequisite inspector. Concurrent privileged DDL
protection, product startup integration, combined authorization/domain schema,
HTTP/provider behavior, hosted operational qualification and GA acceptance
remain pending. Physical phones remain disconnected and deferred to final
acceptance. FieldLog immutable published-package qualification and accountable
independent/root review remain pending. No production publication, customer
message or credential change was performed.
