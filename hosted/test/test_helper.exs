ExUnit.start(assert_receive_timeout: 1_000)
Logger.configure(level: :warning)
Application.ensure_all_started(:phoenix)
Application.ensure_all_started(:ecto_sql)
Application.ensure_all_started(:postgrex)
Application.ensure_all_started(:oban)
Application.ensure_all_started(:inets)

defmodule MixerHosted.Test.Migrations do
  @moduledoc false
  @files Jason.decode!(File.read!(Path.join(__DIR__, "support/reviewed_migrations.json")))

  def versions, do: Enum.map(@files, &(&1 |> String.split("_") |> hd() |> String.to_integer()))

  def check_files!(path) do
    observed =
      Path.wildcard(Path.join(path, "*.exs")) |> Enum.map(&Path.basename/1) |> Enum.sort()

    if observed != @files, do: raise("migration files differ from reviewed foundation list")
    :ok
  end

  def up!(repo, path) do
    check_files!(path)
    expected = versions()
    ^expected = Ecto.Migrator.run(repo, path, :up, all: true)
    expected
  end
end
