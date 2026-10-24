defmodule MixerCatalogInspector.MixProject do
  use Mix.Project

  def project do
    [
      app: :mixer_catalog_inspector,
      version: "0.1.0",
      elixir: "== 1.20.4",
      deps:
        Enum.map(
          ~w(ecto_sql ecto postgrex db_connection decimal telemetry jason)a,
          fn name -> {name, path: "deps/#{name}", override: true} end
        )
    ]
  end

  def application, do: [extra_applications: [:logger, :crypto]]
end
