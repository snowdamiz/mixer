Application.ensure_all_started(:ecto_sql)
Application.ensure_all_started(:postgrex)
Logger.configure(level: :warning)

defmodule MixerTransactionMigrationSmoke.Repo do
  use Ecto.Repo, otp_app: :mixer_authz_migration_smoke, adapter: Ecto.Adapters.Postgres
end

defmodule MixerTransactionMigrationSmoke.Loader do
  def unload do
    # Ecto recompiles a selected .exs migration for each up/down wave. Only
    # completed ordinary migration modules in this owned process are removed.
    for module <- [
          MixerHosted.Repo.Migrations.AddOban,
          MixerHosted.Repo.Migrations.AddBuildJournals,
          MixerHosted.Repo.Migrations.AddBuildAdmission,
          MixerHosted.Repo.Migrations.AddBuildAggregateLimits,
          MixerHosted.Repo.Migrations.AddCustomerAuthorization,
          MixerHosted.Repo.Migrations.AddAuthorizationStateRevisions
        ] do
      :code.purge(module)
      :code.delete(module)
    end
  end
end

repo = MixerTransactionMigrationSmoke.Repo

{:ok, pid} =
  repo.start_link(
    hostname: "127.0.0.1",
    port: String.to_integer(System.fetch_env!("MIXER_TRANSACTION_TEST_PORT")),
    database: "mixer_transaction_migrations_test",
    username: "mixer_fixture",
    ssl: false,
    pool_size: 2,
    log: false
  )

try do
  [path] = System.argv()

  expected = [
    20_261_024_000_000,
    20_261_025_000_000,
    20_261_025_000_001,
    20_261_025_000_002,
    20_261_025_000_003,
    20_261_025_000_004
  ]

  ^expected = Ecto.Migrator.run(repo, path, :up, all: true, log: false)
  [] = Ecto.Migrator.run(repo, path, :up, all: true, log: false)
  MixerTransactionMigrationSmoke.Loader.unload()

  [20_261_025_000_004, 20_261_025_000_003, 20_261_025_000_002] =
    Ecto.Migrator.run(repo, path, :down, step: 3, log: false)

  %{rows: [[nil, nil]]} =
    repo.query!(
      "SELECT to_regclass('public.mixer_authz_profiles')::text, to_regclass('public.mixer_build_fleet_capacity')::text"
    )

  MixerTransactionMigrationSmoke.Loader.unload()

  [20_261_025_000_002, 20_261_025_000_003, 20_261_025_000_004] =
    Ecto.Migrator.run(repo, path, :up, all: true, log: false)

  [] = Ecto.Migrator.run(repo, path, :up, all: true, log: false)

  IO.inspect(%{
    status: :passed,
    applied: expected,
    idempotent_rerun: [],
    reverted: [20_261_025_000_004, 20_261_025_000_003, 20_261_025_000_002],
    reapplied: [20_261_025_000_002, 20_261_025_000_003, 20_261_025_000_004],
    scope:
      "Only ordinary migrations against disposable empty synthetic DB; no broad suite, worker or frozen lane"
  })
after
  Supervisor.stop(pid)
end
