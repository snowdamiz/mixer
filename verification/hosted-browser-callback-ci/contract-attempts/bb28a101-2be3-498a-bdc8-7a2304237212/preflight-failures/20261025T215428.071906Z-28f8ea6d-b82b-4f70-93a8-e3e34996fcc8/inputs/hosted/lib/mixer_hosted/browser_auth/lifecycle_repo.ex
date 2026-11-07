defmodule MixerHosted.BrowserAuth.LifecycleRepo do
  @moduledoc "Dedicated lifecycle pool. No ordinary authorization, jobs or migrations use it."
  use Ecto.Repo, otp_app: :mixer_hosted, adapter: Ecto.Adapters.Postgres

  @binding Module.concat(__MODULE__, Binding)
  @fields ~w(hostname port database username password pool_size pool_count timeout
    connect_timeout queue show_sensitive_data_on_connection_error ssl)a
  @allowed @fields ++ ~w(otp_app telemetry_prefix log name)a

  @impl true
  def init(:supervisor, config) do
    unless Keyword.keyword?(config) and
             Enum.all?(Keyword.keys(config), &(&1 in @allowed)) and
             Enum.all?(@fields, &Keyword.has_key?(config, &1)) and
             Keyword.get(config, :name, __MODULE__) === __MODULE__ do
      raise ArgumentError, "browser lifecycle pool unavailable"
    end

    # Ecto.config/0 re-reads Application settings, so it cannot attest the
    # options actually used by a running pool. The pool supervisor owns this
    # protected table for exactly its lifetime. No credential is retained here.
    :ets.new(@binding, [:set, :protected, :named_table])
    :ets.insert(@binding, {:binding, fingerprint(config)})
    {:ok, Keyword.put(config, :log, false)}
  end

  def init(:runtime, config), do: {:ok, config}

  @doc false
  def bound?(expected) do
    :ets.info(@binding, :owner) === Process.whereis(__MODULE__) and
      :ets.lookup(@binding, :binding) === [{:binding, fingerprint(expected)}]
  rescue
    _ -> false
  end

  defp fingerprint(config),
    do:
      :crypto.hash(
        :sha256,
        :erlang.term_to_binary(Enum.map(@fields, &{&1, Keyword.fetch!(config, &1)}))
      )
end
