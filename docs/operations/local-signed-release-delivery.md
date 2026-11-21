# Provision local signed release delivery

Use this procedure for an operator-owned local installation. The ordinary
Phoenix API serves one registered v3 release target over IPv4 loopback HTTP.
It verifies signed offers and artifacts with public Ed25519 trust roots. The
development signer holds the private keys outside Phoenix.

## Provision PostgreSQL

1. Use the local installation database with the existing authorization and
   artifact schemas. Apply migrations `20261120000001` and `20261120000002`
   from `hosted/priv/repo/migrations`. Apply `20261120000003` from
   `hosted/priv/local_release_delivery` afterward. Apply `20261120000010` and
   `20261120000011` from the ordinary migration directory before starting the
   API, including when releases are published only from the browser. Run these migrations with
   the common non-login relation owner as `current_user`. This role owns
   `mixer_customer_artifacts`, `mixer_release_heads`, and
   `mixer_release_publications` and has neither superuser nor BYPASSRLS.
   With that owner already selected, run the delivery migration from `hosted/`.

   ```sh
   mix ecto.migrate --migrations-path priv/local_release_delivery --to 20261120000003
   ```

2. Register the target in `public.mixer_release_heads` as the relation owner
   with a null `sequence`. Use the existing restricted browser runtime login
   as `writer_role`. The organization, project, app, environment, platform,
   runtime fingerprint, and channel must match the configuration used below.
   The trigger and release ledger advance the head when a publish commits.

   ```sql
   INSERT INTO public.mixer_release_heads (
     organization_id, project_id, application_id, environment_id,
     platform, runtime_sha256, channel, writer_role
   ) VALUES (
     :'organization', :'project', :'app', :'environment',
     :'platform', :'runtime_sha256', :'channel', :'browser_runtime'
   );
   ```

   Set the psql variables to the installation values before running the SQL.
   For browser head access, the existing browser runtime login needs
   `SELECT` on both release tables and `EXECUTE` on
   `public.mixer_release_read_allowed(text,text,text,text)` and
   `public.mixer_release_bound_artifact(text,text,text,text,text,text,text,text)`.
   Keep the standard browser identity, session, and tenant policies in effect.

3. From `hosted/`, connect to the target database as the local administrator
   with authority to create the reader and grant the database, schema, and
   function privileges. Use a DSN without a password and supply administrator
   authentication through your normal psql setup.

   ```sh
   psql -X -v ON_ERROR_STOP=1 "$MIXER_LOCAL_ADMIN_DSN" \
     -f ../docs/operations/provision-local-release-reader.sql
   psql -X "$MIXER_LOCAL_ADMIN_DSN"
   ```

   Run `\password mixer_release_delivery` in psql and assign a distinct
   password. Use TLS and password authentication for the runtime connection.
   The script requires a fresh login and grants database `CONNECT`, schema
   `USAGE`, and `EXECUTE` on the offer and artifact functions. Keep the login
   free of memberships, object ownership, and table grants. Keep public
   schema creation disabled for runtime logins.

## Upgrade a provisioned CLI writer

Apply any outstanding migrations `20261120000004`, `20261120000010`, and
`20261120000011` from `hosted/priv/repo/migrations` in that order as the release
relation owner. The action migration gives older publication rows the value
`publish`. The halt migration leaves earlier rows and signed bytes intact.

Use the existing target's `writer_role` as the psql variable `release_writer`.
As the relation owner or local database administrator, grant the writer insert
access to the action and health columns before enabling release transitions.

```sql
GRANT INSERT (action) ON public.mixer_release_publications TO :"release_writer";
GRANT INSERT (health_activated, health_pending, health_adverse_signals)
  ON public.mixer_release_publications TO :"release_writer";
```

Keep the existing column-scoped publication grant. Publication history stays
append-only, and the delivery login keeps its function-only access. The
ordinary publisher uses the default `publish` action.

To enable halt audit reads, apply `20261120000012` and grant only the
ordinary API database login access to the bounded read function. Apply the
migration as the same non-login relation owner.

```sql
GRANT EXECUTE ON FUNCTION
  public.mixer_release_audit_halts(text,text,text,text,text,text,text,numeric,integer)
  TO :"api_runtime";
```

Use `GET /v3/orgs/:org/projects/:project/audit?view=rollout_halt` with the
existing project audit role and `mixer.audit.read` scope. Each event contains
`id`, `action`, and the Go V3 `rollout_halt` sample. The cursor is the last
halt assignment sequence, supports the full unsigned 64-bit range, and
stays the same on an empty page. The default audit view continues to return
the schema-2 artifact events and their existing cursor. Use each cursor with
its original view.

## Enable current release details in the console

Apply `20261120000013` from `hosted/priv/repo/migrations` as the common
non-login relation owner. Grant the function to the existing `browser_runtime`
login named in the target's `writer_role`.

```sql
GRANT EXECUTE ON FUNCTION
  public.mixer_release_head_details(text,text,text,text,text,text,text)
  TO :"browser_runtime";
```

Use `view=details` with the existing seven target query parameters on
`GET /console-api/v1/release-head`. The function uses the same live
`release.read` authorization and reads only the publication at that target's
committed head. The console reports the runtime compatibility check at
commit time. The byte count comes from the bound manifest and was checked
against the payload at publication. The read checks the manifest and stored
digests without loading the payload.

## Start the ordinary API

Supply the normal API environment, including `MIXER_HOSTED_ROLE=api`, the
existing DB login and password, and `MIXER_SECRET_KEY_BASE`. Use
`MIXER_HTTP_BIND=127.0.0.1` and omit any HTTPS listener. Supply both additional
settings before starting the process.

- `MIXER_LOCAL_RELEASE_CONFIG` contains a JSON object with exactly
  `host`, `channel`, and `roots`. Use the installed v3 host object for
  `host`, including the exact scope, runtime fingerprint, protocol tuple,
  capability hashes, state version, and limits. Use the registered channel as
  `channel`. The limit is 65,536 bytes.
- `roots` contains one to 128 v3 trust records for the host scope. Each record
  has `key_id`, `public_key`, `scope`, `artifact`, `assignment`, `revoked`,
  `not_before_unix`, and `not_after_unix`. Use canonical padded standard
  Base64 for each raw 32-byte public key. Root IDs must be unique.
- `MIXER_LOCAL_RELEASE_DELIVERY_PASSWORD` contains the password for
  `mixer_release_delivery`. Inject it using the service's secret handling.
  The reader uses the ordinary API's PostgreSQL hostname, database, port 5432,
  and TLS options. It verifies the certificate and hostname and uses one
  connection.

```sh
cd hosted
export MIXER_LOCAL_RELEASE_CONFIG="$(cat "$MIXER_LOCAL_RELEASE_CONFIG_FILE")"
mix phx.server
```

Omit both settings to disable local delivery. One missing or invalid setting
aborts startup. Restart the API after changing the target or trust roots.
The browser and updater both read the registered target. The browser head
continues to require a current browser session and tenant authorization
through its ordinary login.

## Enable signed artifact upload

1. Enroll the release target as described above. Apply the authorization and
   artifact storage migrations and provision the project's artifact audit head.
   Use the same host, runtime fingerprint, and public roots for upload and
   delivery.
2. Run the uploader grants script from `hosted/` as the local database
   administrator.

   ```sh
   psql -X -v ON_ERROR_STOP=1 "$MIXER_LOCAL_ADMIN_DSN" \
     -f ../docs/operations/provision-local-artifact-uploader.sql
   psql -X "$MIXER_LOCAL_ADMIN_DSN"
   ```

   Run `\password mixer_artifact_uploader` in psql. Use a password unique
   to this login and configure password authentication over TLS. Keep the
   login free of role memberships and object ownership. The script grants
   access to the existing authorization checks and artifact transaction.
3. Set `MIXER_LOCAL_ARTIFACT_UPLOAD_ENABLED=true`. Inject the login's
   password as `MIXER_LOCAL_ARTIFACT_UPLOAD_PASSWORD` and restart the API.
   The uploader uses one connection to the API's PostgreSQL host and database
   on port 5432. It inherits the certificate and hostname verification
   settings. Use the ordinary IPv4 loopback HTTP listener.
4. Send the signed artifact to
   `PUT /v3/orgs/:organization_id/projects/:project_id/artifacts/:manifest_sha256`.
   Use a current bearer with `mixer.artifact.upload` and authorization for
   the enrolled target. Supply `Idempotency-Key` and `X-Mixer-Reason`.
   The stock `mixer update publish` command sends this request before
   release validation and publication.

The uploader is off by default. To disable it, remove the uploader password,
omit the flag or set it to `false`, and restart the API.

## Enable CLI validation and publication

1. Provision delivery and artifact upload for the same target. Apply
   the outstanding migrations described above under the same non-login relation owner.
2. Confirm that the registered head's `writer_role` is the restricted login
   in `MIXER_DATABASE_USER`. The browser publisher and CLI writer use this
   login. Keep its existing authorization reads and lock-function grants.
   As the administrator, set the psql variable `browser_runtime` to that login
   and apply the release grants in the target database.

   ```sql
   BEGIN;
   GRANT SELECT, UPDATE (sequence) ON public.mixer_release_heads TO :"browser_runtime";
   GRANT SELECT, INSERT (
     organization_id, project_id, application_id, environment_id, platform,
     runtime_sha256, channel, sequence, previous_sequence, artifact_sha256,
     signed_assignment_bytes, rollout_basis_points, idempotency_key, reason, principal_id,
     action, health_activated, health_pending, health_adverse_signals
   ) ON public.mixer_release_publications TO :"browser_runtime";
   GRANT SELECT, INSERT ON public.mixer_release_cli_requests TO :"browser_runtime";
   GRANT EXECUTE ON FUNCTION
     public.mixer_release_publish_allowed(text,text,text,text),
     public.mixer_release_read_allowed(text,text,text,text),
     public.mixer_release_bound_artifact(text,text,text,text,text,text,text)
   TO :"browser_runtime";
   COMMIT;
   ```

   Keep the writer free of relation ownership, owner-role memberships, public
   schema creation privileges, and direct customer artifact table access.
3. Set `MIXER_LOCAL_RELEASE_WRITER_ENABLED=true` and restart the API. The writer
   uses one extra connection with the same login, credentials, and verified
   TLS options as the ordinary API. The API must listen on IPv4 loopback HTTP.
   Set the flag to `false` or omit it for reader-only provisioning.
4. Use a current human bearer authorized for release publication and artifact
   upload in the target tenant. Validate the staged artifact with
   `POST /v3/orgs/:organization_id/projects/:project_id/releases/validate`.
   Send a JSON object containing `artifact_sha256`.
   Publish the signed assignment with
   `POST /v3/orgs/:organization_id/projects/:project_id/channels/:channel/publish`.
   Send a JSON object containing `signed_assignment`. Set `Idempotency-Key`
   and `X-Mixer-Reason` on each request. Use distinct keys for validation and
   publication. After publication, check the same sequence and artifact digest
   in the authenticated browser head and the updater offer for an eligible
   installation.

## Promote a signed release between environments

1. Register both iOS and Android heads in each environment and enroll all
   four targets for delivery. Put one target in `MIXER_LOCAL_RELEASE_CONFIG`
   and the others in `MIXER_LOCAL_RELEASE_TARGET_REGISTRY`. Use the installed
   host and scoped public roots for each target. Follow the
   [target registry setup](../../hosted/scripts/replay-local-release-target-registry.md).
2. Apply `20261120000016` from `hosted/priv/local_stage_promotion` as the
   restricted ledger owner. As that owner, insert an active row into
   `public.mixer_stage_promotion_directions` with the direction ID, tenant,
   source and destination environment IDs, and all four runtime fingerprints
   and channels. Set `writer_role` to the restricted API login in
   `MIXER_DATABASE_USER`. Use that login as the writer of both destination heads.
3. Keep the existing CLI publication grants. As the administrator, set the
   psql variable `release_writer` to the API login and grant access to the
   promotion functions and binding ledger.

   ```sql
   GRANT EXECUTE ON FUNCTION public.mixer_stage_promotion_admit(text),
     public.mixer_stage_promotion_source(text,numeric,numeric) TO :"release_writer";
   GRANT SELECT, INSERT (
     direction_id, writer_role, organization_id, project_id, application_id,
     source_environment_id, destination_environment_id,
     source_ios_runtime_sha256, source_ios_channel,
     source_android_runtime_sha256, source_android_channel,
     destination_ios_runtime_sha256, destination_ios_channel,
     destination_android_runtime_sha256, destination_android_channel,
     idempotency_key, request_sha256, principal_id, reason,
     source_ios_sequence, source_ios_artifact_sha256,
     source_android_sequence, source_android_artifact_sha256,
     destination_ios_sequence, destination_ios_artifact_sha256,
     destination_android_sequence, destination_android_artifact_sha256
   ) ON public.mixer_stage_promotion_bindings TO :"release_writer";
   ```

4. On the IPv4 loopback HTTP API, set `MIXER_LOCAL_RELEASE_WRITER_ENABLED=true`
   and set `MIXER_LOCAL_STAGE_PROMOTION_DIRECTIONS` to a JSON array of 1–32
   direction objects, up to 65,536 bytes total. Restart the API. Unset the
   direction variable and restart to disable the routes.

   Each object has exactly `direction_id`, `source`, and `destination`.
   Use the unique SQL direction ID, 1–128 characters from `A–Z`, `a–z`,
   `0–9`, underscore, period, or hyphen. Both sides have exactly `ios` and
   `android`. Each platform entry has the seven target fields below. Replace
   the example fingerprint with the target's 64-digit lowercase hex digest.

   ```json
   {
     "organizationId": "org-a",
     "projectId": "project-a",
     "applicationId": "fieldlog",
     "environmentId": "development",
     "platform": "ios",
     "runtimeFingerprint": "IOS_DEVELOPMENT_RUNTIME_SHA256",
     "channel": "beta"
   }
   ```

   Use one organization, project, and application across the route, and one
   distinct environment per side. The API resolves host policy and roots from
   the exact configured targets. At request time PostgreSQL checks the active
   SQL direction, writer, and four delivery enrollments.
5. Select one committed source publication per platform from the same release.
   For each destination, sign a manifest for its own scope and runtime with
   the corresponding source payload and release content. Stage the signed
   artifact through [artifact upload](#enable-signed-artifact-upload) with
   that destination target as the uploader's default. Sign each destination
   assignment against the staged manifest digest at a sequence above its head.
6. Point the CLI at the local promotion API and use a current human bearer
   with `mixer.release.publish` and destination publication access. Run the
   command with the two source sequences and signed destination assignment files.

   ```sh
   mixer update promote-environment DIRECTION \
     --organization ORG --project PROJECT --application APP \
     --source-ios-sequence N --source-android-sequence N \
     --ios-assignment FILE --android-assignment FILE --reason REASON
   ```

   A successful response reports both destination publications. The service
   advances both heads and records one binding in the same transaction.

## Halt a rollout after an adverse signal

Run the stock `mixer update halt` command with the current artifact digest, a
health file, and a signed zero-percent assignment for that artifact and target
at a higher sequence. The health file contains the observed current `sequence`
and unsigned `activated`, `pending`, and `adverse_signals` counts. At least one
adverse signal is required. The assignment signer must have current authority.

The publication journal records one `halt` row. For authorized database
readback, `previous_sequence` identifies the observed rollout and
`health_activated`, `health_pending`, and `health_adverse_signals` hold the
reported counts. An exact authorized CLI retry returns the same sample even
after the head advances.

Update checks return HTTP 204 while the halt is current. Previously published
artifacts remain available under the existing delivery verification rules.
Publish or promote at a higher signed sequence to resume new offers.

## Enable the release worker queue

1. After you register the release target, apply optional migration
   `20261120000014` from `hosted/priv/local_release_jobs` as the non-login
   release ledger owner. The owner needs `CREATE` on the ledger database. If
   the optional target registry is already installed, use the current queue
   migration with its empty schema reservation. To add the registry to an
   existing queue, run the current `20261120000015` as the ledger owner. It
   validates the retained jobs and projections and installs full-reference
   uniqueness in the transaction that allows additional heads.
2. Run [provision-local-release-jobs.sql](provision-local-release-jobs.sql)
   as the local database administrator against the ledger database. The script
   provisions the restricted login on every registered head. Rerun it after
   registering a new writer. Set a separate password for the restricted
   `mixer_release_processor` login.
3. Start a separate hosted process with `MIXER_HOSTED_ROLE=processor`,
   `MIXER_PROCESSOR_PROFILE=releases_v1`, and
   `MIXER_DATABASE_USER=mixer_release_processor`. Use the same ledger database
   and the processor password with the standard verified TLS settings.
4. Set `MIXER_LOCAL_RELEASE_JOBS_ENABLED=true` on the API and restart it.
   A new publication commits its release job with its ledger row and head
   advance. The job key includes all seven target coordinates and the
   publication sequence. Exact replay returns the original result without
   adding a job.

Check `mixer_release_jobs.oban_jobs` for a completed `releases` job and
`mixer_release_jobs.offer_materializations` for its corresponding projection.
The browser and updater serve the committed ledger while jobs are pending.
Omit the API flag or set it to `false` to stop enqueueing new jobs.

If a release job exhausts its attempts, resolve the storage failure before
retrying. Run [retry-local-release-job.sql](retry-local-release-job.sql) as the
local ledger administrator with `psql -v release_job_id=<job-id>`. One returned
row means the job is available for one more attempt. An empty result means
the job was ineligible for this operation. Check the job state and the
projection after the processor runs.

## Enable the private delivery export

Start from the [exact target registry setup](../../hosted/scripts/replay-local-release-target-registry.md).
Apply `20261120000017` from `hosted/priv/local_release_delivery_export` as
the restricted relation owner. As the same owner, apply `20261120000018`
from `hosted/priv/local_release_delivery_snapshot`. Grant the delivery login
execute permission on the snapshot function.

```sql
GRANT EXECUTE ON FUNCTION
  public.mixer_release_delivery_snapshot(text,text,text,text,text,text,text)
  TO mixer_release_delivery;
```

`MixerHosted.Releases.DeliveryExport.current/1` takes the exact configured
`Target` from inside Phoenix. A single PostgreSQL statement reads the enrolled
head and its publication history. The result contains the stored signed
assignment, the Worker target and head fields, and `artifact` for a positive
head. A signed halt returns zero rollout and `artifact: nil`.

Use `artifacts` for the snapshot allowlist. The export considers at most the
32 most recent committed positive-rollout publications for all seven target
coordinates, ordered by descending sequence at or below the observed head.
A positive head takes one position in that window. Zero-rollout rows, including
halts, take none. Within the window the export keeps the newest occurrence of
each canonical manifest digest. The export skips entries that fail current
v3 artifact trust, compatibility, or stored hash checks. Duplicates and
rejected entries leave unused positions. Once a publication falls outside
the window, its digest is eligible only if it also occurs inside the window.

Each admitted artifact contains the canonical manifest digest, exact envelope
digest, and exact envelope bytes. The list starts with the positive head when
present, then follows descending publication sequence. Artifacts from the
prior positive rollout can remain eligible after a halt.

`valid_until_unix` is the earliest exclusive expiry among the roots used to
verify the head and all admitted artifacts. `nil` means those roots have no
configured expiry. The lease writer must apply the short lease cap and fence
the read against head, enrollment, and trust changes before updating the
pointer. Serving an issued snapshot during a database outage requires the
separate delivery runtime.

Run the live Phoenix and PostgreSQL replay with the locked dependencies
available and loopback ports 5432 and 47301 free.

```sh
cd hosted
sh scripts/replay-local-release-target-registry.sh export
```

## Replay with a disposable signed fixture

Run the configuration and effective-listener checks from `hosted/`.

```sh
MIX_ENV=test mix test --warnings-as-errors \
  test/mixer_hosted/releases/runtime_provisioning_test.exs
MIX_ENV=test mix test --warnings-as-errors \
  test/mixer_hosted/releases/browser_publication_test.exs:28 \
  test/mixer_hosted/releases/browser_publication_test.exs:79
```

For a live replay, use a disposable PostgreSQL instance on IPv4 loopback
port 5432. Keep its administrator socket in private scratch. Configure TLS
with a disposable CA, a server certificate for `127.0.0.1`, and a `hostssl`
SCRAM rule for loopback. In the API process only, set
`ERL_AFLAGS="-public_key cacerts_path '\"$MIXER_FIXTURE_CA\"'"` to trust the
fixture CA through OTP. The normal API and delivery Repo options both keep
peer and hostname verification enabled.

As the fixture cluster administrator, create these roles and database.

```sql
CREATE ROLE ledger_fixture_admin LOGIN SUPERUSER;
CREATE ROLE ledger_owner NOLOGIN NOINHERIT;
CREATE ROLE ledger_runtime LOGIN NOINHERIT;
CREATE ROLE mixer_customer_build_catalog_definer_v1 NOLOGIN NOINHERIT;
CREATE DATABASE mixer_local_release_ledger OWNER ledger_fixture_admin;
\connect mixer_local_release_ledger
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
ALTER SCHEMA public OWNER TO ledger_owner;
GRANT USAGE ON SCHEMA public TO ledger_runtime;
\password ledger_runtime
```

Set `MIXER_FIXTURE_SOCKET` to the owned PostgreSQL socket directory. Run the
existing ledger test to install the schema and commit the synthetic signed
release through the restricted writer. Then install the reader grants and set
its password as above.

```sh
MIX_ENV=test MIXER_RELEASE_LEDGER_TEST_PORT=5432 \
  MIXER_RELEASE_LEDGER_TEST_SOCKET="$MIXER_FIXTURE_SOCKET" \
  mix test --warnings-as-errors test/mixer_hosted/releases/postgres_test.exs:192

vector=../services/protocol/testdata/signed-release-v3.json
release_config="$(jq -c \
  '{host, roots, channel: .signed_assignment.assignment.channel}' "$vector")"
```

Start `mix phx.server` with `MIXER_DATABASE_HOST=127.0.0.1`,
`MIXER_DATABASE_NAME=mixer_local_release_ledger`, and
`MIXER_DATABASE_USER=ledger_runtime`. Use the two fixture passwords and keep
the browser profile disabled for this replay. First start with both release
settings unset and expect 404. Stop the API, export `MIXER_LOCAL_RELEASE_CONFIG`
from `$release_config`, inject the reader password, and restart the API before
requesting the offer.

```sh
origin="http://127.0.0.1:${MIXER_HTTP_PORT:-4000}"
offer="$(curl -fsS --get "$origin/v3/updates" \
  --data-urlencode organization=org-a --data-urlencode project=project-a \
  --data-urlencode app=fieldlog --data-urlencode environment=development \
  --data-urlencode platform=ios --data-urlencode channel=beta \
  --data-urlencode "runtime=$(jq -r .host.runtime "$vector")" \
  --data-urlencode "installation=$(jq -r .installation "$vector")")"
printf '%s\n' "$offer"
curl -fsS "$origin$(printf '%s' "$offer" | jq -r .artifact_url)"
```

Expect HTTP 200 for the offer and artifact, sequence
`18446744073709551615` in the signed assignment, and the fixture's signed
manifest and payload in the artifact. An otherwise valid offer query with a
different channel returns 204. The artifact URL with a different tenant returns
404. In `pg_stat_ssl`, confirm that the ordinary login and delivery login
both use TLS. Stop the owned API and PostgreSQL, confirm both ports are reusable,
and remove the fixture scratch.

For the independent authenticated browser regression, run the full
`test/mixer_hosted/releases/browser_publication_test.exs` with the existing
browser catalog fixture. That fixture supplies the synthetic sign-in and
checks the exact tenant head in a separately seeded database using the same
ledger migrations. It also checks authenticated CLI validation and publication
against the same head.
