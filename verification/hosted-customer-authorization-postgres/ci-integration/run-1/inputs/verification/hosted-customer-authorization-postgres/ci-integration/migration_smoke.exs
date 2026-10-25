Application.ensure_all_started(:ecto_sql)
Application.ensure_all_started(:postgrex)
Logger.configure(level: :warning)

defmodule MixerAuthzMigrationSmoke.Repo do
  use Ecto.Repo, otp_app: :mixer_authz_migration_smoke, adapter: Ecto.Adapters.Postgres
end

repo = MixerAuthzMigrationSmoke.Repo

{:ok, pid} =
  repo.start_link(
    hostname: "127.0.0.1",
    port: String.to_integer(System.fetch_env!("MIXER_AUTHZ_TEST_PORT")),
    database: "mixer_authz_migrations_test",
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
    20_261_025_000_003
  ]

  ^expected = Ecto.Migrator.run(repo, path, :up, all: true, log: false)
  [] = Ecto.Migrator.run(repo, path, :up, all: true, log: false)

  [20_261_025_000_003, 20_261_025_000_002] =
    Ecto.Migrator.run(repo, path, :down, step: 2, log: false)

  %{rows: [[nil, nil]]} =
    repo.query!(
      "SELECT to_regclass('public.mixer_authz_profiles')::text, to_regclass('public.mixer_build_fleet_capacity')::text"
    )

  [20_261_025_000_002, 20_261_025_000_003] =
    Ecto.Migrator.run(repo, path, :up, all: true, log: false)

  [] = Ecto.Migrator.run(repo, path, :up, all: true, log: false)

  IO.inspect(%{
    status: :passed,
    applied: expected,
    idempotent_rerun: [],
    reverted: [20_261_025_000_003, 20_261_025_000_002],
    reapplied: [20_261_025_000_002, 20_261_025_000_003],
    scope:
      "Only ordinary migrations against disposable empty synthetic DB; no broad suite, worker or frozen lane"
  })
after
  Supervisor.stop(pid)
end
