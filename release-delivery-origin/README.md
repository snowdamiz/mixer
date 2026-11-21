# Public release delivery origin

This Worker serves the public v3 update and artifact routes for one enrolled
target. `DELIVERY_TARGET` is a JSON binding with the exact organization, project,
app, environment, platform, runtime fingerprint, and channel. `DELIVERY_PUBLIC`
is a dedicated private R2 bucket containing public release material only. The
Worker uses `get` and `head`. Its entry point is `src/index.ts`.

The origin uses the v3 cohort calculation from `contracts/release-v3.json`.
Phoenix retains ownership of target enrollment, publication, compatibility,
signatures, and current trust decisions. The origin takes no credentials for
Phoenix, PostgreSQL, or any signer.

## Snapshot contract

`src/writer.ts` is the storage API for an authorized exporter. It has no
public HTTP route. Keep its write access separate from delivery. The exporter
must obtain a consistent view of committed publication and current trust using
the existing product rules. Before staging bytes, it must verify the original v3
assignment, artifact envelope, canonical manifest digest, scope, compatibility,
and signatures using the product's strict decoders. The storage API checks
snapshot coordinates, sizes, byte digests, and the signed assignment fields it
uses. The exporter remains the authority on publication and trust.

A version-1 snapshot contains these fields.

| Field | Value |
| --- | --- |
| `version` | `1` |
| `target` | The seven exact enrollment coordinates from `DELIVERY_TARGET`. |
| `revision` | A positive uint64 encoded as a decimal string. The exporter advances it per target for each consistent view, including lease renewal, halt, or revocation. |
| `issued_at_ms`, `expires_at_ms` | Unix milliseconds. The validity interval includes issue time and excludes expiry. Its maximum length is five minutes. Never extend expiry past a known trust or key deadline for anything the snapshot serves. |
| `head` | `sequence` as a positive uint64 decimal string, `assignment_sha256` over the exact signed JSON, the v3 `artifact_sha256`, signed `rollout_basis_points`, and the exporter’s Boolean `enabled` decision. |
| `artifacts` | Up to 32 distinct currently authorized public artifacts for this target. Each entry has the v3 `manifest_sha256` and the exact wire `envelope_sha256`. A live offer must reference an entry. |

Stage the exact signed assignment and each public artifact before applying the
snapshot. Include only published public envelopes. Source uploads, logs, native
builds, source maps, and signing material stay outside this bucket. The signed
manifest may contain its existing public digest references.

The snapshot limit is 16 KiB. The signed assignment limit is 64 KiB and the
artifact envelope limit is 6 MiB. Assignment and manifest objects use SHA-256 of
their exact bytes. An artifact object's key uses its existing canonical v3
manifest digest. The stored R2 checksum and snapshot entry both bind that key to
the exact envelope bytes. Write-once storage rejects attempts to replace those
bytes even when the artifact has left the current allowlist.

The writer stores and checks the immutable objects before a conditional update of
the target's single current pointer. A lost compare-and-swap returns `retry`.
Re-read current state before retrying. A byte-identical replay of the current
snapshot returns `unchanged` while its lease is valid. Revision must advance and
sequence and issue time cannot decrease. At the same sequence the assignment
digest cannot change, and a disabled head cannot be re-enabled. A rollback uses
a newer signed assignment. Preserve the pointer across restarts. Restoring or
replacing a bucket requires an independently recovered authoritative revision
and sequence before serving. Old blobs cannot reconstruct current authority.

Use `src/publisher.ts` with a trusted release exporter. It stages immutable
objects only after matching their hashes to the verified projection. The
source must compare the exact enrolled target, head, historical allowlist and
trust deadline again and hold that authority through the pointer update.
A callback permit must remain valid just before the compare-and-swap.
Reconcile a timed-out or disconnected write against storage before retrying.
A refused recheck can leave staged objects in the private bucket, where
public requests cannot see them. Each publication attempt reads the source
again. The publisher caps expiry at the earliest exclusive trust deadline
and the requested lease length. The pointer's current revision determines
the next revision within the authorized update.

## Public HTTP behavior

- `GET /v3/updates` requires the seven coordinates and `installation`. It
  returns the exact signed assignment in the existing JSON offer envelope.
  Unenrolled targets, installations outside the signed cohort, halts, disabled
  heads, and expired or absent snapshots return `204`.
- `GET /v3/artifacts/{manifest_sha256}` requires `organization` and `project`.
  The configured enrollment supplies the other coordinates, and only the
  current snapshot's allowlist authorizes the digest. A tenant mismatch, a digest
  outside that allowlist, or an expired or absent snapshot returns `404`.
- A signed zero-rollout head suppresses offers. Its artifact may remain
  authorized. To apply an assignment revocation, disable the affected head in a
  newer snapshot. To apply an artifact revocation, remove the affected digest
  and disable any head that would offer it. A request that already read the
  preceding pointer can finish under that snapshot's lease. Fresh reads use the
  new pointer. Without an exporter refresh, both routes close at lease expiry.
- Invalid queries return `400`, unsupported methods return `405`, and
  unavailable or inconsistent storage returns `503`. All responses use
  `Cache-Control: no-store` so a cached HTTP response cannot outlast the
  authorization lease. CDN cache configuration and a production lease duration
  require separate qualification.

## Replay committed Phoenix releases in Workerd

Run the opt-in fixture from a full checkout as an unprivileged user. Put
PostgreSQL 17.11, OpenSSL, Go 1.26, Elixir 1.20.4 with OTP 29, Node 22.23.3,
and npm 10.9.9 on `PATH`. Free IPv4 loopback ports 5432 and 47301 for this run.
The fixture allocates its own Workerd port and creates a short private scratch
directory for PostgreSQL, its test CA, the Unix socket, and local R2 data.

```sh
(cd hosted && MIX_ENV=test mix deps.get --only test)
(cd hosted-worker-controller && npm ci --ignore-scripts --no-audit --no-fund)
sh hosted/scripts/replay-local-release-target-registry.sh cross-runtime
```

To use a separate Node dependency directory, set `MIXER_DELIVERY_TOOLCHAIN`
to the absolute path containing the controller's two package files and its
locked install. Keep the Mix sources visible at `hosted/deps` for the compile-time
database manifest. The replay builds the Go PostgreSQL probe with the locked
module dependencies and verifies the server CA, server version, and reader role.

Phoenix commits the signed assignments in PostgreSQL. The Workerd publisher
reads the current export and stages only its hash-checked allowlist through the
local R2 binding. A private Unix socket carries the export and a one-use grant
while PostgreSQL holds the enrollment and head locks. Workerd charges the
grant's round trip against its remaining time and checks the permit directly
before the conditional pointer write. The fixture invokes the writer by
in-process Miniflare RPC. Both Worker HTTP entry points refuse writes.

The `MIXER_DELIVERY_REPLAY` line records the byte hashes and pointer states.
Expect the exact current offer and both current and historical artifacts
before and during the outage, followed by 204 and 404 at expiry. The replay
also checks that the outage cannot renew the lease, a late permit cannot
write, and a lost acknowledgement is reconciled against the exact R2
pointer. It restarts the owned database, commits a signed halt, and refuses
both stale authority and a stale pointer ETag. A cleanup failure reports the
retained path and known process identities. This is loopback evidence for
Workerd's local R2 implementation. Cloud R2 and CDN behavior require later
qualification.

## Replay the standalone Worker controls

Run from the repository root with Go and the PostgreSQL tools available. Set
`MIXER_DELIVERY_PG_BIN` if the tools are outside `PATH`. Use the Node and npm
versions in `hosted-worker-controller/package.json`.

```sh
npm ci --ignore-scripts --no-audit --no-fund --prefix hosted-worker-controller
node hosted-worker-controller/node_modules/typescript/bin/tsc -p release-delivery-origin
node release-delivery-origin/test/run.mjs
```

The replay builds the existing Go public-update fixture signer, loads its
synthetic signed publications into a disposable PostgreSQL fixture table, and
copies the public bytes into the Worker's R2 binding through the snapshot API.
It reads both routes over loopback HTTP, stops PostgreSQL, confirms its socket
refuses a fresh query, and repeats the byte comparisons before expiry. The
fixture writer also drives halt, revocation, cohort, ordering, and conflict
checks. The publisher controls use a separate bucket and a fixture authority
source to cover authority changes during staging, exclusive expiry and
stale replay. The replay uses the hosted worker controller's locked toolchain and
workerd identity check. It exercises a separate delivery process and actual
local Worker storage. The PostgreSQL table and Miniflare writer are fixture
inputs. The cross-runtime replay above covers the Phoenix export and permit.
Provider R2, CDN behavior, and full L05 acceptance remain pending.
