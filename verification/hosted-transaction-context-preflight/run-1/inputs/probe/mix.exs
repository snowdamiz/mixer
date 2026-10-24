defmodule MixerTransactionContextPreflight.MixProject do
  use Mix.Project

  def project do
    [app: :mixer_transaction_context_preflight, version: "0.0.0", elixir: "== 1.20.4", deps: deps()]
  end

  def application, do: [extra_applications: [:logger, :crypto]]

  # Isolated, archive-verified copies only. Never loads live hosted source or its build.
  defp deps do
    root = System.fetch_env!("MXTC_DEPS")

    for name <- [:telemetry, :decimal, :jason, :db_connection, :ecto, :postgrex, :ecto_sql] do
      {name, path: Path.join(root, Atom.to_string(name)), override: true}
    end
  end
end
