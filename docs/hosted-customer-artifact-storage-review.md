# Independent PostgreSQL customer artifact storage review

The final independent selected-source run passed **22 ExUnit methods** on a new,
uniquely owned PostgreSQL 17.11 cluster using `storage_runtime`, a login with no
superuser, BYPASSRLS, role-management, database-creation or replication authority.
Migration 005 independently applied, rolled back and reapplied before the tests.
The final source closure exactly matches the producer's `run-14` receipt across
25 named source, migration, fixture and dependency-description paths. The cluster
stopped successfully and its owned scratch directory was removed.

This is local component/integration evidence. It does not qualify HTTP, deployed
Phoenix/Neon/Cloudflare, provider authentication, publication, R2/CDN, customers,
native devices, published separate-repository FieldLog, operational readiness or
any GA gate. No phone, UI, capture, provider-network or production operation ran.
The public CustomerArtifacts facade and combined seven-migration/CI checks belong
to root's separate integration evidence.

The final packet is
`verification/hosted-customer-artifact-storage-review/run-5/receipt.json`, with
selected input tree SHA-256
`d54c1f7260c66bb275dbe84673da5757fe58cd7f76bda4758618f181084651e5`.
The receipt preserves command arguments, outputs, tool versions, dependency BEAM
hashes, source hashes, producer-closure comparison and cleanup. Dependencies were
unchanged after execution. The run used Elixir 1.20.4, Erlang/OTP 29 and Python
3.14.8 on macOS 27.0.1 arm64. It compiled only the selected ordinary source copies
with pinned dependency BEAMs; it did not load the full Mix application, shared
harness, frozen catalog-inspector, authority-driver or rejected Worker sources.
The collector machinery is adapted from the producer's selected-source collector;
the review fixture, direct SQL assembly, attacks and assertions are independently
authored in `verification/hosted-customer-artifact-storage-review/review_test.exs`.

| Frozen final input | SHA-256 |
| --- | --- |
| CustomerArtifacts.Schema | `5bd58744af4823374cc9a981b0699dc16c7d88f37bc8077a40b509cdf5426a19` |
| CustomerArtifacts.PostgresStorage | `b6e9fcd0c3df4f28b6da90589eb2d3c465780c4f8ec484ace74f893aeb216340` |
| CustomerArtifacts.Topology | `35b4cc8f6a91b9b5049dae2ae50d2c056f4066b5c4e88d2e4115d252c137f4cc` |
| Migration 005 | `35e00750436666e22ee4a483848b9fca4fa33fa39b529dd39d27b940f0d0f681` |
| CustomerArtifactEvent | `6e8450558d71af3d0940e7ca7a5725f7bdbc1ad834f4619f9008d8d196976942` |
| Independent review test | `1a05affc1bac6fdde64e2d2b226d8dd0c162f832d6e3098718041241eadd733f` |

Root confirmed base revision `9662eda186e3beee084f92ac25c4116c92f2cebc` for the
final packet; the selected dirty-tree hashes are authoritative. Runs 1–3 retain
the stale `d385adf...` contract reference as their original revision label. This
is an explicit provenance correction, not a rewrite of those receipts.

The independent review found two reproducible database defects in `run-1`:

- A coherent direct runtime SQL write with display `audit_schema` equal to the
  **string** `"2"` committed successfully. The SQL checked its text projection,
  which did not enforce the closed numeric discriminator. The repaired schema
  requires exact JSONB numeric `2`; the same independent attack now rolls back.
- SQL CBOR accepted retained decimal numeric representations such as `1.0`,
  while the Elixir encoder rejects floats. The repaired SQL numeric grammar
  rejects these values. JSONB normalizes `1e0` to integer `1` before the CBOR
  function receives it; this review does not claim to recover discarded JSON
  lexical spelling. The separate signed-JSON structural checker operates on
  `json` and independently rejects decimal and exponent spellings.

Additional coordinated repairs are independently checked in the final packet:
the producer's creating-event/manifest binding prevents a second artifact from
borrowing an existing creating event; the future principal-start fence denies
metadata and direct visibility even with an otherwise admissible future `iat`;
literal PostgreSQL role/schema prefix handling permits benign `pgordinary`
membership while rejecting predefined-role inheritance and an executable helper
in the ordinary `pgxtempyreview` schema; and explicit policy removal permits
migration 005 rollback without a broad `CASCADE`.

The executable coverage includes:

- FORCE RLS, runtime/session identity equality, immutable-table privileges,
  column grants, nonreachable owner/elevated roles, function execution closure,
  and direct negative privilege operations. Nineteen topology perturbations
  separately exercise owner login/BYPASSRLS, runtime BYPASSRLS, grants, policies,
  triggers, function mode/search path, overloads and writable views. Further
  probes substitute an exact helper body and remove the creating-event FK.
- Twenty-three complete direct SQL attack variants cover partial artifact,
  event, idempotency and head writes; retained byte/hash/canonical changes;
  actor/authorization/membership changes; projection/request/IP/request-ID
  changes; and predecessor/sequence gaps. The string discriminator and extra
  artifact are additional attacks. Each rejection leaves zero domain writes.
  A complete valid direct SQL control commits and remains readable/auditable.
- Metadata returns exactly the eight permitted columns including signed bytes,
  while direct envelope/payload SELECT returns no rows. Fourteen changed GUC
  authority/phase/target/scope/token controls deny both metadata and bytes.
  Current principal-start checks are tested independently of the API facade.
- Same-principal exact-request retries, refreshed credentials, conflicting
  principals/requests/envelopes, format-only new-key uploads, immutable original
  bytes, original actor preservation, concurrent same-key deduplication and
  sequential fresh-key no-op events. Checked-field forgery, foreign-process
  use and post-commit Context use confer no storage authority.
- Callback errors/exceptions and caught storage/topology failures roll back
  prior successful writes. Token and root expiry after measured head-lock waits
  of 343/344 ms deny cached retry success. Admitted uploads and private reads
  hold canonical revocation locks; later requests fail after revocation returns.
- Retained-byte corruption, malformed audit rows and missing predecessors fail
  closed. Audit pagination limits and empty cursor preservation are exercised.
  SQL CBOR matches exact known bytes and Elixir encoding at uint64, Unicode,
  canonical map order, depth, item, container and 65536-byte output bounds.
  Signed JSON rejects duplicate keys and unsupported primitives/structural bounds.

Failures remain evidence: `run-1` records the two reproduced defects (one valid
control and two failing expectations); `run-2` and `run-3` passed 16 and 21
methods at their earlier source closures; `run-4` stopped before database startup
because the review test needed formatting; `run-5` is the final passing packet.
All five receipts record successful cleanup or that PostgreSQL never started.

The trust boundary remains explicit: these checks protect trusted application
composition, not malicious BEAM code or arbitrary identity-GUC SQL executed by a
holder of the application credential. SQL verifies retained consistency and
current linkage; current-root Ed25519 admission remains in the protected API.
Coherent privileged-owner rewrites require separate checkpoint/retention work.

Reproduce using a fresh output directory:

```sh
python3 verification/hosted-customer-artifact-storage-review/run.py \
  --output verification/hosted-customer-artifact-storage-review/run-N \
  --source-revision 9662eda186e3beee084f92ac25c4116c92f2cebc \
  --producer-receipt verification/hosted-customer-artifact-storage/run-14/receipt.json
```
