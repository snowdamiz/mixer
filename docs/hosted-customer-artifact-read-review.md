# Independent staged customer artifact read review

The frozen staged-read authorization slice has no actionable defect observed in
this bounded review. Run 1 passed **80 tests**: 17 new independent adversarial
methods, the producer's 15 staged-read methods, and all 30 unchanged Policy plus
18 unchanged transaction methods. The producer packet is
`verification/hosted-customer-artifact-read-scope/run-4/receipt.json`, selected
source tree `794103f2ccfa6e897d79b8373a5d714608e0c5319711f92a566b9b7429634f23`.
This acceptance applies to the frozen authorization slice and its exact frozen
storage dependency, not subsequent changes or a GA gate.

## Preserved execution

```sh
python3 verification/hosted-customer-artifact-read-review/run.py \
  --output verification/hosted-customer-artifact-read-review/run-1 \
  --source-revision 9662eda186e3beee084f92ac25c4116c92f2cebc
```

The collector copied the producer's named ordinary source inputs and tests into
its own immutable run directory before compiling. Its only new executable input
is the independent review test; its fixture setup derives from the producer's
migration/seed fixture, with separate module, database, telemetry, probe and role
names. All general-purpose dependency BEAMs were copied and compared with the
producer run-4 dependency manifest before compilation. No shared Mix compile,
application startup, harness main, catalog-inspector, authority-driver, rejected
Worker V2 lane, or Git command was executed.

The run used Elixir 1.20.4, Erlang/OTP 29 and Homebrew PostgreSQL 17.11 on local
macOS. `elixirc --warnings-as-errors`, formatting validation, actual SQL tests,
command outputs, dependency hashes and input hashes are preserved. The review
selected tree is `445a63d08003d04cf8ef38b8ee9f4b037135e583f519e9058ccc6480501f9e06`;
the shared dependency manifest is
`c544378354d431a88740973b97517211c514bcad9a51616cb6188cf6ee502645`.

The owned loopback cluster created `mixer_artifact_read_review` with
`read_review_fixture_admin`, nonlogin `read_review_owner` and restricted login
`read_review_runtime`. Runtime is nonsuperuser, non-BYPASSRLS, cannot create roles
or databases, cannot replicate, cannot change authorization tables, and does not
inherit their owner. The producer read and unchanged transaction regressions
used separate newly created databases/roles in that same disposable cluster.
The cluster was stopped and its scratch directory removed. Expected connection
timeout diagnostics from deliberate five-second deadline tests remain in the
log; those cases passed rollback assertions. No failed review attempt exists.

## Security observations

- A verified human with only `mixer.artifact.read` can resolve a strict project
  target. `mixer.audit.read` remains independently required for audit access.
  Organization-only, full environment, incomplete application, string-key,
  extra-field and malformed identity inputs fail before a repository lookup.
  Missing read scope remains `permission_denied` even for a hidden project.
- Nine committed authority changes made while a real reader was observed waiting
  on the profile lock were current on admission: inactive profile, binding,
  principal, credential, family, membership, organization and project, plus a
  role change to billing manager. All rejected before the metadata SQL helper.
  Organization-only membership cannot see a project; all-projects viewer
  membership can. Inactive derived applications/environments cannot bind a
  full transaction Context.
- The real migration 005 helper exposes exactly the metadata projection with
  empty application/environment GUCs. Runtime direct base-table SELECT returns
  zero private artifact, idempotency and audit rows in metadata phase. The
  resolver issues exactly one metadata helper SELECT and no runtime artifact
  payload/envelope query before it. Wrong action, required scope, phase,
  identity linkage, token spelling/window or nonempty derived settings makes
  direct helper reads empty.
- Signed JSON has closed shape and duplicate-key rejection. Malformed Unicode,
  trailing values, unknown keys and noncanonical/incorrect-length signature
  spellings fail. Every normalized target/platform/runtime column must match the
  parsed manifest; canonical CBOR must hash to the exact requested digest.
  Reordered/whitespace-varied valid JSON retains the same canonical CBOR/digest
  and exact original signed JSON bytes. Metadata has only the seven documented
  fields and grants no reusable authority.
- All 19 connection fingerprint GUC fields were individually changed inside an
  actual transaction. Every attempted checkpoint failed, latched failure and
  rolled back earlier SQL despite a caught failure. Altered Context data, target
  and action also fail; cross-process and post-completion/stale Context reuse
  cannot grant authority. Nested transaction rejection leaves a valid owning
  caller usable.
- Credential, family and membership windows expiring immediately after actual
  metadata resolution prevent callback entry. Five-second transaction/deadline expiry
  after metadata resolution prevents callback entry, and final deadline expiry
  rolls back local SQL and rejects cached success. Escaped effect exceptions,
  throws, exits, unknown errors and malformed effect callbacks cannot be caught
  into a successful commit. Existing token-time, domain-wait, wall-clock and
  snapshot regression assertions remain unchanged and passed.

## Acceptance limits

The tests apply real product migrations 003/004/005, RLS and the topology checker,
but synthetic superuser seeds deliberately bypass mutation/deferred integrity
triggers. The modified test manifest retains only signature shape; these rows
are not signature-valid uploaded artifacts. Deliberate five-second overrun tests
also activated DBConnection transaction timeouts: executable evidence proves
the combined timeout/deadline rollback boundary, while the independent monotonic
checks are established by source inspection rather than isolated clock injection. This receipt therefore proves
metadata resolution, bounded authorization and lifecycle behavior, not successful
upload integrity, cryptographic trust or private-storage re-admission. Root must
integrate the customer facade with actually uploaded stored artifacts after the
storage lane freezes and reverify against that final storage source.

Root separately identified a standard Mix test-discovery supplement: the producer
read test needs explicit migration-module loading when those modules have not
already been compiled by this standalone collector. Root owns that test-only
integration change and combined current-storage migration smoke; this frozen
review does not qualify either change.

This review made no edits to production, shared/producer or Git files and ran no
provider, network, UI, capture, native or physical-device testing. It does not
qualify HTTP/console composition, production Neon/Cloudflare/TLS behavior, provider
identity, immutable published FieldLog consumption, customer operation,
independent security acceptance or GA. Physical-phone checks remain pending.
