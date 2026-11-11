defmodule MixerHosted.BrowserAuth.ProviderOwner do
  @moduledoc "Raw provider boundary. Production transport is deliberately unconfigured and fails closed."
  use GenServer
  alias MixerHosted.BrowserAuth.ConfigurationDigest
  alias MixerHosted.Identity.TrustSnapshot

  def exchange(config, code, verifier, deadline) do
    GenServer.call(__MODULE__, {:exchange, config, code, verifier, deadline}, remaining(deadline))
  catch
    :exit, _ -> {:error, :provider_unavailable}
  end

  def finish(ticket, config, deadline) do
    GenServer.call(__MODULE__, {:finish, ticket, config}, remaining(deadline))
  catch
    :exit, _ -> {:error, :provider_unavailable}
  end

  def start_link(:unconfigured),
    do: GenServer.start_link(__MODULE__, :unconfigured, name: __MODULE__)

  if Mix.env() == :test do
    @doc false
    def start_fixture(config, snapshot, transport),
      do:
        GenServer.start_link(__MODULE__, {:fixture, config, snapshot, transport},
          name: __MODULE__
        )
  end

  def init(:unconfigured), do: {:ok, :unconfigured}

  if Mix.env() == :test do
    def init({:fixture, config, snapshot, transport}) when is_pid(transport) do
      {:ok, digest} = ConfigurationDigest.digest(config)

      {:ok,
       %{
         config: config,
         digest: digest,
         snapshot: snapshot,
         transport: transport,
         generation: make_ref()
       }}
    end
  end

  def handle_call({:exchange, config, code, verifier, deadline}, _from, %{config: config} = s) do
    if fresh?(s) and System.monotonic_time(:millisecond) < deadline do
      request = %{
        issuer: config.issuer,
        client_id: config.client_id,
        redirect_uri: config.redirect_uri,
        token_endpoint: config.token_endpoint,
        client_auth_method: config.client_auth_method,
        client_credential_ref: config.client_credential_ref,
        code: code,
        code_verifier: verifier,
        grant_type: "authorization_code"
      }

      result = GenServer.call(s.transport, {:exchange, request}, remaining(deadline))

      case result do
        {:ok, raw} when is_binary(raw) and byte_size(raw) <= 16384 ->
          if fresh?(s) and System.monotonic_time(:millisecond) < deadline,
            do: {:reply, {:ok, raw, s.snapshot, {self(), s.generation, s.digest}}, s},
            else: {:reply, {:error, :provider_unavailable}, s}

        _ ->
          {:reply, {:error, :provider_unavailable}, s}
      end
    else
      {:reply, {:error, :provider_unavailable}, s}
    end
  end

  def handle_call({:finish, {pid, generation, digest}, config}, _from, %{config: config} = s) do
    valid = pid === self() and generation === s.generation and digest === s.digest and fresh?(s)
    {:reply, if(valid, do: :ok, else: {:error, :provider_unavailable}), s}
  end

  def handle_call(_, _, s), do: {:reply, {:error, :provider_unconfigured}, s}

  def format_status(status),
    do:
      Map.new(status, fn {k, v} ->
        if k in [:state, :message, :reason, :log], do: {k, :redacted}, else: {k, v}
      end)

  defp fresh?(s), do: TrustSnapshot.status(s.snapshot, System.system_time(:second)) === :fresh
  defp remaining(d), do: max(1, min(5000, d - System.monotonic_time(:millisecond)))
end
