Application.ensure_all_started(:ecto_sql)
Application.ensure_all_started(:postgrex)
Logger.configure(level: :error)

defmodule MixerBeginLoginReview.MigrationRepo do
  use Ecto.Repo, otp_app: :mixer_begin_review, adapter: Ecto.Adapters.Postgres
end

port = String.to_integer(System.fetch_env!("PREAUTH_REVIEW_PORT"))

{:ok, repo} =
  MixerBeginLoginReview.MigrationRepo.start_link(
    hostname: "127.0.0.1",
    port: port,
    database: "review_browser",
    username: "review_admin",
    pool_size: 2,
    log: false,
    after_connect: fn conn -> Postgrex.query!(conn, "SET ROLE mixer_review_owner", []) end
  )

try do
  for {number, suffix, module} <- [
        {20_261_024_000_000, "add_oban", MixerHosted.Repo.Migrations.AddOban},
        {20_261_025_000_000, "add_build_journals", MixerHosted.Repo.Migrations.AddBuildJournals},
        {20_261_025_000_001, "add_build_admission",
         MixerHosted.Repo.Migrations.AddBuildAdmission},
        {20_261_025_000_002, "add_build_aggregate_limits",
         MixerHosted.Repo.Migrations.AddBuildAggregateLimits},
        {20_261_025_000_003, "add_customer_authorization",
         MixerHosted.Repo.Migrations.AddCustomerAuthorization},
        {20_261_025_000_004, "add_authorization_state_revisions",
         MixerHosted.Repo.Migrations.AddAuthorizationStateRevisions},
        {20_261_025_000_005, "add_customer_artifact_storage",
         MixerHosted.Repo.Migrations.AddCustomerArtifactStorage},
        {20_261_025_000_006, "add_customer_workspace_discovery",
         MixerHosted.Repo.Migrations.AddCustomerWorkspaceDiscovery},
        {20_261_025_000_007, "add_browser_sessions",
         MixerHosted.Repo.Migrations.AddBrowserSessions},
        {20_261_025_000_008, "add_browser_activation_preparation",
         MixerHosted.Repo.Migrations.AddBrowserActivationPreparation}
      ] do
    Code.require_file("hosted/priv/repo/migrations/#{number}_#{suffix}.exs")
    :ok = Ecto.Migrator.up(MixerBeginLoginReview.MigrationRepo, number, module, log: false)
  end
after
  Supervisor.stop(repo)
end

{:ok, admin} =
  Postgrex.start_link(
    hostname: "127.0.0.1",
    port: port,
    database: "review_browser",
    username: "review_admin",
    backoff_type: :stop
  )

try do
  for sql <-
        MixerHosted.BrowserAuth.StorageSchema.provisioning_statements(
          "mixer_review_writer",
          "mixer_review_lifecycle"
        ) do
    Postgrex.query!(admin, sql, [])
  end

  for sql <-
        MixerHosted.BrowserAuth.ActivationPreparationSchema.provisioning_statements(
          "mixer_review_writer",
          "mixer_review_lifecycle",
          "mixer_review_owner"
        ) do
    Postgrex.query!(admin, sql, [])
  end

  Postgrex.query!(admin, "GRANT USAGE ON SCHEMA public TO mixer_review_runtime", [])

  Postgrex.query!(
    admin,
    "GRANT SELECT ON public.mixer_authz_profiles,public.mixer_authz_principals,public.mixer_authz_bindings,public.mixer_authz_families,public.mixer_authz_credentials TO mixer_review_runtime",
    []
  )
after
  GenServer.stop(admin)
end

