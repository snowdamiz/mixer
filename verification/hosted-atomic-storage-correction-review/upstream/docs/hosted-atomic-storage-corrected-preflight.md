# Corrected atomic storage specimen

Producer recommendation for fresh independent review; root acceptance remains
pending. The [AS01–AS07 selection](hosted-atomic-storage-corrections.md) governs
this isolated synthetic PostgreSQL specimen. No product source, migration,
repository route, authorization implementation, provider or GA gate is accepted
by these results. The complete product plan remains binding.

The final candidate passes **73/73** executable cases in an owned PostgreSQL
17.11 cluster through actual Ecto 3.14.2/Ecto SQL 3.14.0/Postgrex 0.22.4/DBConnection 2.10.2,
Elixir 1.20.4 and OTP29. The source and runner digest is
`f346d03f1d279918d0b7a0ea965535bc757fa86874164dc8f14cc233642b21e1`.
The [run6 receipt](../verification/hosted-atomic-storage-corrected-preflight/run-6/receipt.json),
[case observations](../verification/hosted-atomic-storage-corrected-preflight/run-6/tests.json)
and [complete installed catalog](../verification/hosted-atomic-storage-corrected-preflight/run-6/installed-catalog.json)
bind the actual execution. Catalog SHA256 is
`5824cfe3629e65e2da8dcf4d831a10f22589a5b2bd38c02bbf58f90d23971883`.
Tool/package versions and all commands, environment overrides, output and copied
inputs are retained. This is a local host specimen, without a Neon or Linux claim.

The 41 original positive/fault assertions remain, together with the 20 independent
reviewer cases and 12 correction cases. R03/R06–R11/R19 now demand rejection of
the reproduced gaps. The original packets remain unchanged and their read-only
integrity checkers pass. Case39's corruption setup now edits the literal event-ID
CBOR byte: a complete decoder correctly refuses to encode its intentionally
invalid event2/empty-predecessor combination. Its writer rejection assertion is
preserved. Case20 inherits the reviewer's quiet PostgreSQL restart logging; its
COMMIT-loss/restart/retry assertions are unchanged. Exact file diffs and per-case hashes are in the
[probe delta](../verification/hosted-atomic-storage-corrected-preflight/probe-delta.json).
The original valid audit/state/display vectors, 120 independent uint64 vectors,
legacy Go event/hash vectors and signed v3 vectors remain unchanged.

The corrected boundaries are:

| Selection | Implementation and executable evidence |
| --- | --- |
| AS01 | Installed context expiry/completion and artifact size composite fields are unconstrained `numeric`. Entry rejects NULL, NaN, both infinities, fractions, negative and out-of-range values before GUC equality and locks. Application fixture admission independently requires bounded integers. R01–R03/R17/R18 and C01 exercise actual SQL, catalog and typmod evidence. |
| AS02 | A separate fresh policy/clock query follows the final lock and every subsequent retained-row/predecessor/fault read. The final pre-effect query supplies decision/recorded timestamps, and original wall/monotonic budgets remain unextended. Cached returns recheck after validation. A post-DML fresh check aborts all writes if the operation aged or expired while waiting. R04/R05/R19/R20 and C08–C10 confirm actual waits and no committed effects. |
| AS03 | Cached status, 1..4096 response bytes, bounded integral event ID and same-tenant typed event are validated. Actor/action/target/request must match; exact retained UTF-8 response is compared to the event-derived manifest/event encoding. Status201 is this artifact's creation event; a later unchanged-artifact event is200 and must preserve state. Corruption returns no cached material and appends no event. C04/C05 retain valid refreshed-credential and201/200 replay controls. |
| AS04 | Artifact creation event and actor are nonnull server-derived columns; a deferred same-tenant FK supports artifact-before-audit insertion. The writer validates the creation event's exact target/actor and recomputes Change1 and changed state from its previous state. R11/C06 cover constraints and semantic checks, including a test-only owner temporarily disabling the FK to exercise impossible retained corruption. The exact constraint is restored before catalog capture. |
| AS05 | Independent SQL and Elixir typed decoders enforce the exact16 root keys, all JSON types, fixed nested shapes, required values, canonical UUID/hex/decimal text, ValidID, enums, UTF-8 byte bounds, canonical IP/null, membership count/order/uniqueness/roles/revisions and time relationships. SQL validates complete retained rows, exact CBOR, standard SHA256, projections and exact stored PostgreSQL display bytes. The independent Elixir row oracle reconstructs PostgreSQL display formatting and compares exact bytes too. C02 has456 invalid displays and26 valid boundaries with independently authored Python CBOR bytes; C03/C12 cover row budgets, invalid UTF-8 and schema types. |
| AS06 | Terminal, creation and cached selected events each validate their immediate predecessor when needed, including its typed representation/hash. Event1 requires empty previous hash and exact initial state. Rows already validated within the fixed operation share the bounded validation result. R10/C07 cover coherent wrong hash/state edges, malformed predecessor and missing predecessor. No history scan is performed. |
| AS07 | The actual catalog enumerates22 function identities:19 private pure helpers plus two resolver definers and the sole mutation definer. Private helper EXECUTE is individually granted to the writer; runtime cannot invoke those helpers. Function definitions and hashes, owners, ACL entries/effective privileges, composite order/types, all7 tables/constraints, FORCE RLS policies, roles/memberships/default ACLs/schema/database privileges are retained. R12/C11 check the surface. The deliberately granted foreign mutation caller remains a test-only session-gate probe. |

The actual extra pure helper identities are `finite_uint(numeric,numeric,numeric)`,
`jtext(jsonb,integer,integer)`, `juint(jsonb,numeric,numeric)`, `juuid(jsonb)`,
`jhex(jsonb,integer,integer)`, `jid(jsonb)`, `jarray(jsonb,integer)`, `jip(jsonb)`,
`row_valid(mixer_hosted_release.audit_events)`,
`changed_state(bytea,mixer_hosted_release.upload_input)` and
`time_valid(mixer_hosted_release.call_context,numeric,timestamp with time zone)`.
They supplement the eight original actual helper identities; the installed
catalog contains every exact definition and effective grant. No conceptual alias
is an installed-object check. Product names remain the original selected
`upload_artifact_v1(writer_context_v1,artifact_input_v1,request_input_v1)` signature;
product expiry/completion/payload input types are now unconstrained numeric under
AS01. Root must select the product DDL/helper identities/ACL manifest before a
product startup inspector is implemented.

Wait observations distinguish late `AccessShareLock` reads on idempotency and
artifacts from `RowExclusiveLock` DML waits on artifacts, audit and idempotency.
They also show that both initial synthetic policy and tenant-head locks are
already held. Exact expiry140 and stale age46 deny, inclusive age45 and unexpired
controls succeed, and a later fault read changes the actual new decision/recorded
clock to110. The original SQL deadline rejects after a confirmed read wait.
Authentication completion may be30 seconds after decision time; no
completion<=decision/recorded restriction was added. Recorded time must be at
least decision time. The existing real COMMIT-acknowledgement-loss proxy, actual
server restart, fresh authorized exact retry, boundary fault rollbacks and blob
uncertainty rules all still pass. A lost response does not prove rollback;
COMMIT may complete just after expiry once already sent.

`event_from_display(jsonb)` validates the retained typed JSONB representation.
PostgreSQL normalizes raw JSON token `1e0` to JSONB integer representation1 before
entry, while `1.0`/`1.00` remain noninteger representations and are rejected. The
helper cannot recover discarded raw token spelling and is not a public arbitrary
JSON parser. Root explicitly selected this interpretation; C12 retains an
accepted normalized control, rejected retained representations and Elixir's
separate typed-integer1 rule. The initial lexical rejection assertion failed in
run5 and is preserved unchanged there. No raw JSON API was added.

All six attempts are retained: run1 failed DDL parsing; run2 passed60/61 before the
case39 fixture adaptation; run3 failed test compilation on an unsupported test
regex escape; run4 passed72/72; run5 passed72/73 and exposed the JSONB normalization
boundary; run6 passed73/73 after root's clarification. Every owned PostgreSQL
cluster, proxy that was started, socket and scratch/build/cache/blob tree was
stopped/removed. Run1 failed before any proxy was started. No other project
process or native instance was touched. The inherited dependency xref warning
remains; no dependency/lock changed.

Run `python3 -B verification/hosted-atomic-storage-corrected-preflight/check.py`
for read-only retained-evidence checks. A fresh execution uses
`python3 -B verification/hosted-atomic-storage-corrected-preflight/run.py` and
creates a new numbered owned run. Frozen passing source is also preserved under
`run-6/inputs/probe/` with the exact runner and independent corpus generator.

This specimen uses synthetic principals, policy/clock/fault rows, opaque artifact
bytes and fixed tenant/target RLS. It supplies no real credential/profile/binding
or canonical five-lock authorization implementation, product migration/inspector,
HTTP admission, signed upload composition, publication, Neon/R2/Cloudflare,
Oban/domain-job atomicity, operational/customer/FieldLog or GA qualification.
Adjacent-edge and cached-row checks detect inconsistent retained material under
append-only runtime privileges; they do not prove history or original-key
provenance against a privileged offline owner coherently rewriting an entire
chain or cached association. That requires an independent retained commitment.
The local blob fixture retains its trusted single-process/directory and uncertain
outcome limitations. Physical phones remain disconnected and deferred; no native
or physical test was attempted by this lane. Fresh independent review and root
acceptance remain required before repository implementation.
