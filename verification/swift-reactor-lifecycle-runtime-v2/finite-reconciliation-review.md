# Pre-runtime finite representation reconciliation

Candidate `0fa7ae254ac2b3aa3390e6fbc935e920422fc9024db220256074ec6ef4e3cd56`
changes only the selected SL09 and SL13 test bodies. All other 131 files and all
imports/helpers/hooks/21 other test bodies are byte-identical. Production
lifecycle/growth/accounting source, formulas and every Frozen source are exact.
The new tests compile in all four unit contexts. No test in this packet has run.

The same retained official metadata driver (`80c8c841…`) and original qualified
compiler/sysroot bin/lib bytes produced all four raw queries. No download or
shared install occurred. All five compiler targets and metadata scratch are
cleaned; complete outputs and binary/MIR artifacts remain archived.

The four queries retain 160 accounted runtime bodies and 256 precisely partitioned
CTFE annotation bodies. Accounted body identity sets and all instructions match
after the **finite, per-context allocation bijections** in
`unchanged-runtime-proof.json`. Thirty-four raw full MIR strings differ only in
those allocation identifiers: 7 Debug and 10 Release bodies per feature set.

`runtime-body-reconciliation.json.gz` preserves every old/new full body, raw SHA,
all allocation declarations, every occurrence, complete bytes/text/alignment,
offset and relocation/reference text. Each allocation is paired with its actual
counterpart; the global per-context map and reverse map are injective. Replacing
only these exact bound identifiers makes each complete body and allocation block
byte-identical. The same mapping covers all 74 changed constant-operand records.
No arbitrary identifier is removed, and equality is not inferred from counts.

There are also 134 raw local sourceInfo changes, covering 632 four-role rows.
All are derive/macro hygiene numeric context indices. Full file/line/column
coordinates, scope, actual body definition hash, local/operand identity and full
actual type/layout remain matched. `finite-metadata-differences.json.gz` retains
190 exact changed span/sourceInfo fields, including type graph definitions.
Unchanged occurrences are included in the per-context hygiene bijection, so
distinctness is checked against both changed and unchanged recorded contexts.
The driver did **not** query full macro expansion chains. That limitation is
explicit; root must review/accept this finite representation evidence or select
further metadata before runtime. No generic hygiene-index exemption is adopted.

The exact raw proof also matches 2,636 local/operand/FnDef records, 11,760 sealed
unit four-role positions, 176 whole retained source-carrier field witnesses,
116 full owner/carrier declarations and 2,330 type graph/layout records. Complete
owner fields/variants/offsets/alignments and all accounting declarations match.
No numeric accounting credit is added. Production formula values remain those
of the previously accepted unchanged source and exact unit class layouts.

There is **no unexplained instruction, position, actual type, full layout,
source-coordinate or scope difference** in the retained comparison. All 39
Frozen methods are byte-identical in a fresh official expansion against the
retained full old expanded methods. Actual full raw bodies and every finite
representation delta remain available for independent inspection.

Root's separate finite representation selection is pending. Runtime cannot start
until it arrives. The full original matrix and complete authored/remaining ledger
are byte-preserved. SL09 strengthened assertions are still unrun. SL12 guest table
mutation remains unsupported/unimplemented/unrun. No live, full reactor, native,
Git or shared-tracker work occurred.

`pre-runtime-freeze.json` binds every file present at this review boundary. Later
runtime evidence may be added only after selection; frozen files must not change.
Read-only verification:

```sh
python3 -B verification/swift-reactor-lifecycle-runtime-v2/verify_pre_runtime.py
```
