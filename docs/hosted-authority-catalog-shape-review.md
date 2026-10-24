# Independent authority catalog raw-shape review

The frozen ACR01 candidate closes the original malformed-admission finding in
its selected-state model. All **126 original boundary cases** replayed with
108 rejections and 18 OID portability admissions; all 21 prior malformed
admissions now reject. The added **1,083 shape cases**, **8 transport cases** and
**3 selected portability controls** also replayed successfully. Another **136
independently authored model cases** pass. A final retained-header cross-check
found **two additional malformed raw-model admissions**, documented as ACSR02.

One raw-domain false rejection remains: **ACSR01**. In
`raw_validation.py:190`, zero OIDs and the displayed name `*` are treated as a
two-way equivalence. PostgreSQL also permits an actual quoted role named
`"*"`. In the fresh owned cluster, this ordinary DDL succeeds:

```sql
CREATE ROLE "*" NOLOGIN;
GRANT "*" TO mixer_hosted_runtime;
ALTER ROLE "*" IN DATABASE authority_contract SET application_name=review;
```

The unchanged capture query returns a real role OID **17807**, role `*`, database
OID **16384**, database `authority_contract`, and config
`["application_name=review"]`. Raw validation rejects it with
`malformed raw value: startup_defaults[0] wildcard association role`. The role
without its default passes raw validation. The same source condition also
covers database names. This is a valid **unselected** raw shape: the additional
reachable role and default already fail the separate exact selected comparison.
It demonstrates neither a selected-safe regression nor an authorization bypass.
The correction should require `oid == 0` to imply the wildcard marker, while
allowing a positive OID to resolve any valid actual name, including `*`.
Root selection remains pending that narrow domain correction.

**ACSR02** concerns the declared unique `(tgrelid, tgname)` key in the retained
`pg_trigger.h:85`. Two distinct internal triggers on
`mixer_authz.applications` (row OIDs 16757 and 16758, relation OID 16730) can be
given the identical raw name `RI_ConstraintTrigger_a_16758`; both raw and selected
validation admit. An internal trigger can similarly take the existing external
trigger name `lifecycle_guard` on the same relation and still admit. The raw
names are individually well-typed but cannot coexist under that unique catalog
key. They disappear before selected comparison. This is a malformed model-input
admission, with no actual SQL or ordinary-runtime bypass demonstrated. Check
`(relation_oid, name)` uniqueness across **all** trigger rows before discarding
internal names. The separate control that reuses a name on another relation
remains portable. The [dedicated observations](../verification/hosted-authority-catalog-shape-review/name-uniqueness-observations.json)
preserve both finding oracles and the portability control.

The [receipt](../verification/hosted-authority-catalog-shape-review/receipt.json),
[domain audit](../verification/hosted-authority-catalog-shape-review/domain-review.json),
[actual counterexample](../verification/hosted-authority-catalog-shape-review/attempt-1/extra-runtime/summary.json)
and [read-only checker](../verification/hosted-authority-catalog-shape-review/check.py)
freeze this review. Candidate source digest is
`7e2a24ec2aad45d07d2dd8a5d581fa8df5966e841981d20b27c75acd1de74b40`;
candidate receipt SHA-256 is
`49ecbed394b965f68f50e242da0103005d3e86fee23a42955fc5530b982f2e22`.
The producer checker independently passed **277 bindings**. Source copies and
all selected bytes were bound before execution and remained unchanged. The
selected manifest retains SHA-256
`78c0c8a56c6d358eda1e8a183176d5fe7b7e67e9427bdeb4aa1bb308dfaa8e6e`.

The complete source delta remains a new raw validator plus its import and call
before normalization. SQL, schema/functions/roles/types, capture queries,
normalization, retained comparison and original assertions match the frozen
predecessor. The manual field audit covers all nine enforcement groups, nine
session fields and the legacy nested objects. Raw validation checks exact keys,
primitive domains, UTF8/NUL and identifier-byte bounds, uint32 OIDs, required and
optional association presence, nested ACL/config/parent values and booleans
before discarded fields disappear. Duplicate JSON keys reject at decoding.
Semantic duplicates and list multiplicity remain visible to exact comparison;
ACSR02 is the missing uniqueness check for names that are discarded.
Cross-row numeric OID equality is intentionally outside the portable model
contract; resolved semantic identities remain selected comparison inputs.

One new socket-only PostgreSQL **17.11** cluster with **89 padding tables**
replayed all **19 ordinary-runtime cases**: **23 safe comparisons** and **15
DDL/session rejections**, including renamed/recreated internal FKs and extra-FK
multiplicity. The fresh raw relation OIDs and generated internal-trigger names
differ from the earlier capture, while normalized safe state equals the selected
manifest. Three fresh runtime connections retain distinct backend PIDs and exact
login/session identity. The independent quoted-name probe and its safe
restoration also passed their explicit finding-reproduction oracles.

The original **128 cases**, **43 prior controls**, **5 historical observations**
and **67 catalog-correction cases** were **reused from byte-bound producer
execution**, checked against unchanged executed source and captures. They were
not rerun in this review. The five historical observations remain finding
observations, not security passes. The model matrix was freshly executed here;
model inputs are separate from actual SQL evidence. `index live=false` remains
model evidence only, and no concurrent-drop runtime liveness receipt is added.

The sole runtime/model review attempt succeeded. The final uniqueness probe
adds two finding observations and one valid portability control; those two
admissions are findings, not security passes. The preliminary 106-binding
review receipt, manifest, checker, document and successful checker command are
retained unchanged under `preliminary-106-binding-review/`, so the root's earlier
check remains historical evidence. No failed attempt was discarded. Exact
commands, tool versions and executable hashes, source/input hashes, output
hashes, SQL commands and compressed original-byte bindings are retained. The
observed HEAD was `e337ddd14236cc94ede4def750a9fde4c461ad3e`, tree
`09a2ecb36e08d49497f9da82c746789be8f47ea5`, on macOS 27.0.1 arm64 with Python
3.14.8 and libpq 170011. The owned cluster stopped and its unique scratch root
was removed. No TCP listener, other project's process, simulator, emulator or
physical phone was touched.

Run the frozen review without starting a server:

```sh
python3 -B verification/hosted-authority-catalog-shape-review/check.py
```

This remains a point-in-time prerequisite review. Concurrent privileged DDL
protection, full product startup, combined domain schema, provider/HTTP behavior,
production operations and GA acceptance remain pending. Physical-phone checks
remain deferred to final acceptance. No publication, customer message,
credential change, producer/live-source edit, dependency change or push occurred.
