# Authority catalog raw-shape correction

Root selects **ACR01** from the frozen
[independent review](hosted-authority-catalog-review.md) for correction before
catalog prerequisite acceptance. The review reproduces 21 malformed admissions
in 126 boundary cases, separately from successful ordinary PostgreSQL drift
rejections. It does not demonstrate an ordinary-runtime authorization bypass.

The next isolated candidate must validate complete raw shapes and primitive
domains before deleting OIDs or generated internal-trigger text. Use the
review's `raw-field-domains.json` and retained PostgreSQL 17 headers as the
concrete starting contract: integer OIDs are unsigned 32-bit values, booleans
are not integers, required associations are positive, and optional zero OIDs
agree with absent resolved identities. Required trigger names/definitions are
nonempty valid text; names obey the platform identifier byte bound. Validate
all nine enforcement groups, nested ACL/default/parent values, and all nine
fresh-session fields without accepting unknown keys or dropping duplicate
semantic entries. Retained comparison must still reject every selected drift.

Preserve the separately selected expected manifest byte for byte, including
its original SHA-256
`78c0c8a56c6d358eda1e8a183176d5fe7b7e67e9427bdeb4aa1bb308dfaa8e6e`.
Do not regenerate selection from an observed deployment. Preserve every original
schema, function, role, type and SQL capture query. No resolver algorithm,
grant, lock order, migration, driver or live product source changes belong here.
The only product-candidate changes are raw validation and necessary wiring to
invoke it before lossy normalization; keep an exact implementation delta.

Replay the review's entire 126-case boundary matrix with the 21 defect cases
now requiring rejection and the 18 OID portability cases still passing. Add
direct boundaries for newly validated raw fields, including malformed nested
arrays/objects, nullability, text and identifier bounds, bool/integer confusion,
unknown/duplicate keys and association consistency. Do not convert historical
finding reproductions into security passes without an explicit changed oracle
in this new copy. Keep original evidence unchanged.

Run one fresh disposable PostgreSQL replay with different OIDs: original 128
cases, prior 43 controls plus five explicitly historical observations, all 67
catalog corrections, and the independent review's ordinary-DDL/session cases.
Preserve renamed/recreated internal FK portability and multiplicity. No extra
runtime matrix is necessary unless a correction or new failure warrants it.
Keep failed attempts, exact source/dependency/tool/command/output bindings and
owned-resource cleanup. Separate model-input evidence from actual SQL evidence.

Ownership is a new `verification/hosted-authority-catalog-shape-correction/`
packet and `docs/hosted-authority-catalog-shape-correction.md` only. Other packets,
live source, trackers, dependencies and commits remain root-owned or frozen.
Fresh independent review is required before root selection. This inspector is
a point-in-time prerequisite; concurrent privileged DDL protection, production
startup, combined domain schema, HTTP, provider and GA acceptance remain pending.
