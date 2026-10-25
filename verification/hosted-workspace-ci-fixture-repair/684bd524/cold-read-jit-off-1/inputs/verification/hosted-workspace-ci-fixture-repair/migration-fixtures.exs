Application.ensure_all_started(:ecto_sql)
Application.ensure_all_started(:postgrex)
Logger.configure(level: :warning)

defmodule MixerHosted.CIFixtureRepair.MigrationRepo do
  use Ecto.Repo, otp_app: :ci_fixture_repair, adapter: Ecto.Adapters.Postgres
end

alias MixerHosted.CIFixtureRepair.MigrationRepo

{:ok, repo} =
  MigrationRepo.start_link(
    hostname: "127.0.0.1",
    port: String.to_integer(System.fetch_env!("MIXER_WORKSPACE_TEST_PORT")),
    database: "mixer_ci_migrations",
    username: "workspace_fixture_admin",
    pool_size: 2,
    ssl: false,
    log: false,
    after_connect: fn c -> Postgrex.query!(c, "SET ROLE workspace_owner", []) end
  )

path = System.fetch_env!("MIXER_CI_MIGRATION_PATH")

expected = [
  20_261_024_000_000,
  20_261_025_000_000,
  20_261_025_000_001,
  20_261_025_000_002,
  20_261_025_000_003,
  20_261_025_000_004,
  20_261_025_000_005,
  20_261_025_000_006
]

^expected = Ecto.Migrator.run(MigrationRepo, path, :up, all: true, log: false)
[] = Ecto.Migrator.run(MigrationRepo, path, :up, all: true, log: false)
aggregate_up = Enum.drop(expected, 3)
aggregate_down = Enum.reverse(aggregate_up)
^aggregate_down = Ecto.Migrator.run(MigrationRepo, path, :down, step: 5, log: false)
^aggregate_up = Ecto.Migrator.run(MigrationRepo, path, :up, all: true, log: false)
all_down = Enum.reverse(expected)
^all_down = Ecto.Migrator.run(MigrationRepo, path, :down, all: true, log: false)
^expected = Ecto.Migrator.run(MigrationRepo, path, :up, all: true, log: false)
[] = Ecto.Migrator.run(MigrationRepo, path, :up, all: true, log: false)

File.write!(
  System.fetch_env!("MIXER_CI_MIGRATION_RESULT"),
  Jason.encode!(%{
    applied: expected,
    aggregate_down: aggregate_down,
    aggregate_reapplied: aggregate_up,
    all_down: all_down,
    all_reapplied: expected,
    repeated_up_empty: true,
    disposable: true,
    held_worker_preservation: "pending automatic CI; this control verifies migration boundaries"
  })
)

Supervisor.stop(repo)
