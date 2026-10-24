defmodule MixerHosted.MixProject do
  use Mix.Project

  def project do
    [
      app: :mixer_hosted,
      version: "0.1.0",
      elixir: "== 1.20.4",
      elixirc_paths: elixirc_paths(Mix.env()),
      start_permanent: Mix.env() == :prod,
      deps: deps(),
      aliases: [test: "test --no-start"]
    ]
  end

  def application do
    [mod: {MixerHosted.Application, []}, extra_applications: [:logger, :ssl, :inets]]
  end

  defp elixirc_paths(:test), do: ["lib", "test/support"]
  defp elixirc_paths(_), do: ["lib"]

  defp deps do
    [
      {:phoenix, "== 1.8.16"},
      {:plug, "== 1.20.3"},
      {:bandit, "== 1.13.1"},
      {:ecto_sql, "== 3.14.0"},
      {:postgrex, "== 0.22.4"},
      {:oban, "== 2.24.2"},
      {:jason, "== 1.4.5"}
    ]
  end
end
