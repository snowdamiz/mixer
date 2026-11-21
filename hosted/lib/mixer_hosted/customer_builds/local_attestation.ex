defmodule MixerHosted.CustomerBuilds.LocalAttestation do
  @moduledoc false
  alias MixerHosted.BrowserAuth.Installation
  alias MixerHosted.Builds.NativeDevelopmentAttestation
  alias MixerHosted.CustomerBuilds.AttestationRepo
  alias MixerHosted.RuntimeConfig
  alias MixerHostedWeb.Endpoint

  @password "MIXER_LOCAL_NATIVE_ATTESTATION_PASSWORD"
  @public_key "MIXER_LOCAL_NATIVE_ATTESTATION_PUBLIC_SPKI_BASE64"
  @login "mixer_native_attestation_writer"

  @derive {Inspect, only: [:origin]}
  @enforce_keys [:repo, :origin, :port, :public_spki_der]
  defstruct @enforce_keys

  def configure!(env, %RuntimeConfig{} = hosted, release) do
    case {Map.fetch(env, @password), Map.fetch(env, @public_key)} do
      {:error, :error} ->
        hosted

      {{:ok, password}, {:ok, encoded}} ->
        configure_writer!(hosted, release, password, decode_spki!(encoded))

      {:error, _} ->
        invalid!(@password)

      {_, :error} ->
        invalid!(@public_key)
    end
  end

  def children(%RuntimeConfig{native_attestation: nil}, _, _), do: []

  def children(
        %RuntimeConfig{role: :api, native_attestation: %__MODULE__{} = provision},
        installation,
        endpoint
      ) do
    unless endpoint_matches?(endpoint, provision.port) and no_conflicting_settings?() do
      raise ArgumentError, "conflicting local native attestation configuration"
    end

    case installation do
      %Installation{runtime: runtime} ->
        unless distinct?(runtime.lifecycle_repo, provision.repo[:password]) and
                 @login not in Map.values(runtime.expected_roles),
               do: invalid!(@password)

      :disabled ->
        :ok
    end

    [{AttestationRepo, provision.repo}]
  end

  def configuration do
    case MixerHosted.Application.startup() do
      {:ok, {%RuntimeConfig{role: :api, native_attestation: %__MODULE__{} = provision}, _}} ->
        port = provision.port
        endpoint = Application.get_env(:mixer_hosted, Endpoint, [])

        if Process.whereis(AttestationRepo) &&
             endpoint_matches?(endpoint, port) &&
             no_conflicting_settings?() &&
             match?({:ok, {{127, 0, 0, 1}, ^port}}, Endpoint.server_info(:http)) do
          {:ok, Map.take(provision, [:origin, :public_spki_der])}
        else
          {:error, :authorization_unavailable}
        end

      {:ok, _} ->
        :disabled

      :error ->
        {:error, :authorization_unavailable}
    end
  end

  defp configure_writer!(hosted, release, password, spki) do
    unless hosted.role == :api, do: invalid!("MIXER_HOSTED_ROLE")
    unless match?(%{retained_root: _}, hosted.native), do: invalid!("MIXER_NATIVE_RETAINED_ROOT")
    port = local_port(hosted.endpoint) || invalid!("MIXER_HTTP_BIND")

    delivery_repo =
      case release do
        {_, %{repo: repo}} -> repo
        :disabled -> nil
      end

    upload_repo = if hosted.artifact_upload, do: hosted.artifact_upload.repo
    pools = [hosted.repo, hosted.create_repo, delivery_repo, upload_repo]

    unless is_binary(password) and byte_size(password) in 1..4096 and String.valid?(password) and
             :binary.match(password, <<0>>) == :nomatch and
             Enum.all?(pools, &distinct?(&1, password)),
           do: invalid!(@password)

    provision = %__MODULE__{
      repo: Keyword.merge(hosted.repo, username: @login, password: password, pool_size: 1),
      origin: "http://127.0.0.1:#{port}",
      port: port,
      public_spki_der: spki
    }

    %{
      hosted
      | native_attestation: provision,
        database_connection_bound: hosted.database_connection_bound + 1
    }
  end

  defp decode_spki!(<<_::binary-size(60)>> = encoded) do
    with {:ok, der} <- Base.decode64(encoded),
         ^encoded <- Base.encode64(der),
         true <- NativeDevelopmentAttestation.valid_public_spki?(der) do
      der
    else
      _ -> invalid!(@public_key)
    end
  end

  defp decode_spki!(_), do: invalid!(@public_key)

  defp no_conflicting_settings? do
    Application.fetch_env(:mixer_hosted, AttestationRepo) == :error and
      Application.fetch_env(:mixer_hosted, :native_development_attestation) == :error
  end

  defp endpoint_matches?(endpoint, port),
    do:
      local_port(endpoint) == port and
        Keyword.get_values(endpoint, :adapter) == [Bandit.PhoenixAdapter]

  defp local_port(endpoint) do
    case {Keyword.get_values(endpoint, :server), Keyword.get_values(endpoint, :http),
          Keyword.has_key?(endpoint, :https)} do
      {[true], [[ip: {127, 0, 0, 1}, port: port, http_2_options: [enabled: false]]], false}
      when port in 1..65_535 ->
        port

      _ ->
        nil
    end
  end

  defp distinct?(nil, _), do: true

  defp distinct?(pool, password),
    do: Keyword.keyword?(pool) and pool[:username] != @login and pool[:password] != password

  defp invalid!(setting),
    do: raise(ArgumentError, "invalid or missing hosted setting: " <> setting)
end
