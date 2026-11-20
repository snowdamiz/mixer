# Provision local release delivery for multiple targets

Keep `MIXER_LOCAL_RELEASE_CONFIG` as the v3 configuration for the default
target. The default still supplies the existing release writer configuration.
Keep the existing loopback HTTP listener and the separate
`MIXER_LOCAL_RELEASE_DELIVERY_PASSWORD` for `mixer_release_delivery`.

1. Use a database with the release ledger and the optional
   `20261120000003` delivery migration. Leave
   `MIXER_LOCAL_RELEASE_JOBS_ENABLED` off.
2. Apply `priv/local_release_target_registry/20261120000015_add_local_release_target_registry.exs`
   in an Ecto migration transaction as the same restricted, non-login owner.
   The owner needs `CREATE` on the database. The migration refuses an existing
   `mixer_release_jobs` schema and reserves that schema name to block
   later installation of `20261120000014`. Keep the reservation until the
   queue deduplicates by the full publication reference, including sequence.
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
and 47301 free, run `hosted/scripts/replay-local-release-target-registry.sh`
as an unprivileged user. The runner uses PostgreSQL, OpenSSL, and Mix. It
starts an isolated PostgreSQL cluster and the ordinary Phoenix API on
loopback. The test uses fixture identities and synthetic signed artifacts.
Look for one passing registry test and
`Removed owned PostgreSQL and fixture scratch.`
