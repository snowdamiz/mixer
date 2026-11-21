# Provision local release delivery for multiple targets

Keep `MIXER_LOCAL_RELEASE_CONFIG` as the v3 configuration for the default
target. The default still supplies the existing release writer configuration.
Keep the existing loopback HTTP listener and the separate
`MIXER_LOCAL_RELEASE_DELIVERY_PASSWORD` for `mixer_release_delivery`.

1. Use a database with the release ledger and the optional
   `20261120000003` delivery migration.
2. Apply `priv/local_release_target_registry/20261120000015_add_local_release_target_registry.exs`
   in an Ecto migration transaction as the restricted, non-login ledger owner.
   The owner needs `CREATE` on the database. For an existing singleton queue,
   the migration validates retained jobs and projections against the immutable
   ledger and installs full publication-reference uniqueness before allowing
   multiple heads. For a registry-first database, the current `20261120000014`
   queue migration uses the registry's empty schema reservation. Apply it
   from `priv/local_release_jobs` explicitly. Ecto warns about the lower
   version when `000015` is already installed. An empty queue rollback from
   that same path restores the reservation. The queue refuses rollback
   while it contains retained work.
3. Provision a release head and its writer role for each target. For every
   target you intend to deliver, including the default, insert a row into
   `public.mixer_release_delivery_enrollments` as the restricted owner. Set
   `reader_role` to `mixer_release_delivery`. Use the exact head key
   `(organization_id, project_id, application_id, environment_id, platform, runtime_sha256, channel)`.
   The reader's existing grants cover the delivery functions. The owner manages
   the enrollment rows.
4. Set `MIXER_LOCAL_RELEASE_TARGET_REGISTRY` to a JSON array of 1–32
   additional entries. Use the v3 fields `host`, `channel`, and `roots` in
   every entry. Supply the host and public roots for that entry's scope.
   Restart Phoenix after changing the config.

The queue remains opt-in. Follow the
[release queue setup](../../docs/operations/local-signed-release-delivery.md#enable-the-release-worker-queue)
after provisioning the heads. Each API writer still uses one explicit release
target and its registered login. Use that target as the API's default when
publishing for it.

Both delivery functions require enrollment as soon as the migration
commits. Existing heads receive no automatic enrollment. Removing an
enrollment revokes the reader's access on its next committed read. To run
the default config alone after opting in, remove the additional entries
by unsetting the registry variable and retain the default enrollment.
Schema reversal requires a forward migration that preserves enrollment.

The offer path is `GET /v3/updates`. Send the exact target as
`organization`, `project`, `app`, `environment`, `platform`, `runtime`,
and `channel`, plus `installation`. Fetch the artifact at the returned
`artifact_url`. The default retains
`/v3/artifacts/<digest>?organization=<org>&project=<project>`. Additional
targets return the seven target fields on the artifact URL. A legacy
artifact URL always resolves against the configured default.

## Replay the local fixture

With the locked test dependencies available and IPv4 loopback ports 5432
and 47301 free, run both orders from `hosted/` as an unprivileged user.

```sh
sh scripts/replay-local-release-target-registry.sh queue-first
sh scripts/replay-local-release-target-registry.sh registry-first
```

Each run starts an isolated PostgreSQL cluster and the ordinary Phoenix API and
release processor on loopback. Two restricted writers publish and replay the
same sequence for two exact targets, and the processor materializes the signed
bytes for each. The replay also publishes a signed rollback and retries a
discarded job by ID. The queue-first run checks that a failed upgrade leaves
the legacy queue and singleton intact, then upgrades with the original job
and projection retained. Each run ends with one passing registry test and
`Removed owned PostgreSQL and fixture scratch.`
