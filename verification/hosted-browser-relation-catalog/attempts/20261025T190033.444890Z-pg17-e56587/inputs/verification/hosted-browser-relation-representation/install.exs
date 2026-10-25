# Exact ordinary migration installation only; no Mixer app or admission module.
defmodule MixerRelationRepresentation.MigrationRepo do
  use Ecto.Repo, otp_app: :relation_representation, adapter: Ecto.Adapters.Postgres
end

Application.ensure_all_started(:ecto_sql)
Application.ensure_all_started(:postgrex)

Code.require_file("hosted/lib/mixer_hosted/browser_auth/storage_schema.ex")
Code.require_file("hosted/lib/mixer_hosted/customer_artifacts/schema.ex")

migrations = [
  {"20261024000000_add_oban.exs", MixerHosted.Repo.Migrations.AddOban},
  {"20261025000000_add_build_journals.exs", MixerHosted.Repo.Migrations.AddBuildJournals},
  {"20261025000001_add_build_admission.exs", MixerHosted.Repo.Migrations.AddBuildAdmission},
  {"20261025000002_add_build_aggregate_limits.exs",
   MixerHosted.Repo.Migrations.AddBuildAggregateLimits},
  {"20261025000003_add_customer_authorization.exs",
   MixerHosted.Repo.Migrations.AddCustomerAuthorization},
  {"20261025000004_add_authorization_state_revisions.exs",
   MixerHosted.Repo.Migrations.AddAuthorizationStateRevisions},
  {"20261025000005_add_customer_artifact_storage.exs",
   MixerHosted.Repo.Migrations.AddCustomerArtifactStorage},
  {"20261025000006_add_customer_workspace_discovery.exs",
   MixerHosted.Repo.Migrations.AddCustomerWorkspaceDiscovery},
  {"20261025000007_add_browser_sessions.exs", MixerHosted.Repo.Migrations.AddBrowserSessions}
]

{:ok, repo} =
  MixerRelationRepresentation.MigrationRepo.start_link(
    hostname: "127.0.0.1",
    port: String.to_integer(System.fetch_env!("REPRESENTATION_PORT")),
    database: "browser_storage",
    username: "browser_admin",
    pool_size: 2,
    log: false,
    after_connect: fn conn -> Postgrex.query!(conn, "SET ROLE browser_schema_owner", []) end
  )

try do
  for {file, module} <- migrations do
    Code.require_file("hosted/priv/repo/migrations/" <> file)
    version = String.slice(file, 0, 14) |> String.to_integer()
    :ok = Ecto.Migrator.up(MixerRelationRepresentation.MigrationRepo, version, module, log: false)
    IO.puts("installed #{version} #{module}")
  end
after
  GenServer.stop(repo)
end

{:ok, conn} =
  Postgrex.start_link(
    hostname: "127.0.0.1",
    port: String.to_integer(System.fetch_env!("REPRESENTATION_PORT")),
    database: "browser_storage",
    username: "browser_admin",
    backoff_type: :stop
  )

try do
  for sql <-
        MixerHosted.BrowserAuth.StorageSchema.provisioning_statements(
          "browser_writer",
          "browser_lifecycle"
        ),
      do: Postgrex.query!(conn, sql, [])

  Postgrex.query!(conn, "GRANT USAGE ON SCHEMA public TO browser_ordinary", [])

  Postgrex.query!(
    conn,
    "GRANT SELECT ON public.mixer_authz_profiles,public.mixer_authz_principals,public.mixer_authz_bindings,public.mixer_authz_families,public.mixer_authz_credentials TO browser_ordinary",
    []
  )
after
  GenServer.stop(conn)
end
