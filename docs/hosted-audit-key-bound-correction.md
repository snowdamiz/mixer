# Bounded audit key validation

This isolated candidate replaces both sorts of unvalidated supplied map keys
with exact cardinality and lookup of the fixed required keys. The complete
implementation delta is two lines. Every field bound, CBOR byte, domain hash,
PostgreSQL display encoding, retained-row and adjacent-edge rule is unchanged.

The corrected source passes **12 focused tests**, including the original eleven,
and **105 full hosted tests with two explicit Linux-only namespace skips**.
Formatting, warnings-as-errors compilation, packaged release construction,
missing-config rejection and test-export exclusion pass. Replayed independent
tests cover all **107 coherent-hash cases and eight chain edges**, with six tests
passing. These are retained review cases run by root against the correction;
independent correction acceptance is still pending.

The added regression rejects sixteen or ten oversized unknown keys and every
single required-key replacement by seven foreign key forms at exact cardinality.
The original captured 185 PostgreSQL rows, six chains and 80 producer vectors
remain unchanged. No artifact CBOR support or general-purpose dependency changes.

The original finite timing probe, with inputs allocated before measurement,
records the following median microseconds per twenty rejection calls:

| Input | 1 KiB key | 1 MiB key | 4 MiB key |
| --- | ---: | ---: | ---: |
| Unknown display keys, corrected | 6 | 35 | 36 |
| Unknown row keys, corrected | 2 | 1 | 2 |
| Unknown display keys, original review | 26 | 6,221 | 26,565 |
| Unknown row keys, original review | 11 | 4,137 | 18,235 |

Known-key oversized-value controls also remain bounded in these observations.
These measurements illustrate the correction on this host; no timing threshold,
universal latency or total BEAM memory guarantee is inferred. Source validation
now visits only fixed short keys after a cardinality check.

The [receipt](../verification/hosted-audit-key-bound-correction/receipt.json) binds
the corrected source, exact dependencies, original review inputs, commands,
outputs, tool versions and source archives. The owned PostgreSQL fixture and
scratch were removed. The [checker](../verification/hosted-audit-key-bound-correction/check.py)
replays integrity checks without starting services.

No live source or database migration has been changed. Independent correction
review and root integration acceptance remain pending. Current-authority/domain
writer composition, authenticated HTTP, cloud providers, native/physical checks,
published FieldLog consumption and all GA gates remain open.
