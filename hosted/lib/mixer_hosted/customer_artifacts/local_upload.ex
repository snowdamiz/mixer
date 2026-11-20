defmodule MixerHosted.CustomerArtifacts.LocalUpload do
  @moduledoc false
  alias MixerHosted.BrowserAuth.Installation
  alias MixerHosted.CustomerArtifacts
  alias MixerHosted.CustomerArtifacts.UploadRepo
  alias MixerHosted.Releases.{DeliveryRepo, Target, WriterRepo}
  alias MixerHosted.RuntimeConfig

  @prefix "MIXER_LOCAL_ARTIFACT_UPLOAD_"
  @enabled @prefix <> "ENABLED"
  @password @prefix <> "PASSWORD"
  @login "mixer_artifact_uploader"

  @derive {Inspect, only: []}
  @enforce_keys [:release, :delivery, :repo]
  defstruct @enforce_keys

  def configure!(env, %RuntimeConfig{} = hosted, release) do
    if Enum.any?(
         Map.keys(env),
         &(String.starts_with?(&1, @prefix) and &1 not in [@enabled, @password])
       ),
       do: invalid!(@enabled)

    case {Map.get(env, @enabled, "false"), Map.fetch(env, @password)} do
      {"false", :error} ->
        hosted

      {"true", {:ok, password}} ->
        configure_upload!(hosted, release, password)

      {"true", :error} ->
        invalid!(@password)

      _ ->
        invalid!(@enabled)
    end
  end

  defp configure_upload!(%RuntimeConfig{role: role} = hosted, release, password) do
    unless role == :api, do: invalid!("MIXER_HOSTED_ROLE")
    unless loopback?(hosted.endpoint), do: invalid!("MIXER_HTTP_BIND")

    case release do
      {%{target: %Target{}} = target, %{repo: reader} = delivery} ->
        unless distinct?([hosted.repo, hosted.create_repo, reader], password),
          do: invalid!(@password)

        repo = Keyword.merge(hosted.repo, username: @login, password: password, pool_size: 1)
        upload = %__MODULE__{release: target, delivery: delivery, repo: repo}

        %{
          hosted
          | artifact_upload: upload,
            database_connection_bound: hosted.database_connection_bound + 1
        }

      _ ->
        invalid!("MIXER_LOCAL_RELEASE_CONFIG")
    end
  end

  def children(%RuntimeConfig{artifact_upload: nil}, _, _), do: []

  def children(
        %RuntimeConfig{role: :api, artifact_upload: %__MODULE__{} = upload} = hosted,
        installation,
        endpoint
      ) do
    unless endpoint_matches?(endpoint) and projections_match?(hosted),
      do: raise(ArgumentError, "conflicting local artifact upload configuration")

    case installation do
      %Installation{runtime: runtime} ->
        unless distinct?([runtime.lifecycle_repo], upload.repo[:password]) and
                 @login not in Map.values(runtime.expected_roles),
               do: invalid!(@password)

      :disabled ->
        :ok
    end

    [{UploadRepo, upload.repo}]
  end

  def configuration do
    case MixerHosted.Application.startup() do
      {:ok, {%RuntimeConfig{artifact_upload: %__MODULE__{} = upload} = hosted, _}} ->
        endpoint = Application.get_env(:mixer_hosted, MixerHostedWeb.Endpoint, [])

        if Process.whereis(UploadRepo) && endpoint_matches?(endpoint) &&
             projections_match?(hosted) do
          {:ok, %{repo: UploadRepo, host: upload.release.host, roots: upload.release.roots}}
        else
          {:error, :storage_unavailable}
        end

      {:ok, {%RuntimeConfig{artifact_upload: nil}, _}} ->
        :disabled

      :error ->
        case Application.get_env(:mixer_hosted, :startup) do
          {%RuntimeConfig{artifact_upload: %__MODULE__{}}, _} -> {:error, :storage_unavailable}
          _ -> if Process.whereis(UploadRepo), do: {:error, :storage_unavailable}, else: :disabled
        end
    end
  end

  defp loopback?(endpoint) do
    Keyword.get_values(endpoint, :server) == [true] and
      match?(
        [[ip: {127, 0, 0, 1}, port: _, http_2_options: _]],
        Keyword.get_values(endpoint, :http)
      ) and
      not Keyword.has_key?(endpoint, :https)
  end

  defp endpoint_matches?(endpoint),
    do: loopback?(endpoint) and Keyword.get_values(endpoint, :adapter) == [Bandit.PhoenixAdapter]

  defp projections_match?(%RuntimeConfig{repo: repo, artifact_upload: upload}) do
    Application.fetch_env(:mixer_hosted, CustomerArtifacts) == :error and
      Application.fetch_env(:mixer_hosted, UploadRepo) == :error and
      Application.fetch_env(:mixer_hosted, DeliveryRepo) == :error and
      Application.fetch_env(:mixer_hosted, :local_release_target) === {:ok, upload.release} and
      Application.fetch_env(:mixer_hosted, :local_release_delivery) === {:ok, upload.delivery} and
      Application.get_env(:mixer_hosted, WriterRepo) in [nil, Keyword.put(repo, :pool_size, 1)]
  end

  defp distinct?(pools, password) do
    is_binary(password) and byte_size(password) in 1..4096 and String.valid?(password) and
      :binary.match(password, <<0>>) == :nomatch and
      Enum.all?(pools, fn
        nil ->
          true

        pool ->
          Keyword.keyword?(pool) and pool[:username] != @login and pool[:password] != password
      end)
  end

  defp invalid!(setting),
    do: raise(ArgumentError, "invalid or missing hosted setting: " <> setting)
end
