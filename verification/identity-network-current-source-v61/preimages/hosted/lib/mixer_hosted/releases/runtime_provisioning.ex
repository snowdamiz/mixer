defmodule MixerHosted.Releases.RuntimeProvisioning do
  @moduledoc "Operator provisioning for one local signed v3 release target."
  alias MixerHosted.Authorization.Scope
  alias MixerHosted.Protocol.{ArtifactJSON, ArtifactV3Policy}
  alias MixerHosted.Releases.Target
  alias MixerHosted.RuntimeConfig, as: HostedConfig

  @config "MIXER_LOCAL_RELEASE_CONFIG"
  @password "MIXER_LOCAL_RELEASE_DELIVERY_PASSWORD"
  @reader "mixer_release_delivery"
  @max_config_bytes 65_536

  def load!(env, %HostedConfig{} = hosted) do
    case {Map.fetch(env, @config), Map.fetch(env, @password)} do
      {:error, :error} ->
        :disabled

      {{:ok, raw}, {:ok, password}} ->
        target = target!(raw)
        repo = reader!(hosted, password)
        {target, Map.put(target, :repo, repo)}

      {:error, _} ->
        invalid!(@config)

      {_, :error} ->
        invalid!(@password)
    end
  end

  defp target!(raw) do
    with {:ok, document, _, _} <- ArtifactJSON.decode(raw, @max_config_bytes),
         true <- ArtifactV3Policy.exact?(document, ~w(host channel roots)),
         host = document["host"],
         true <- ArtifactV3Policy.host?(host),
         {:ok, target} <- target(host, document["channel"]),
         {:ok, roots} <- roots(document["roots"], host["scope"]) do
      %{target: target, host: host, roots: roots}
    else
      _ -> invalid!(@config)
    end
  end

  defp target(%{"scope" => scope, "runtime" => runtime}, channel) do
    Target.new(%Target{
      scope: %Scope{
        organization_id: scope["organization"],
        project_id: scope["project"],
        application_id: scope["app"],
        environment_id: scope["environment"]
      },
      platform: scope["platform"],
      runtime_sha256: runtime,
      channel: channel
    })
  end

  defp roots(encoded, scope) do
    with true <- ArtifactV3Policy.bounded_list?(encoded, 128),
         roots <- Enum.map(encoded, &decode_root/1),
         true <- ArtifactV3Policy.roots?(roots),
         true <- Enum.all?(roots, &(&1["scope"] == scope)) do
      {:ok, roots}
    else
      _ -> :error
    end
  end

  defp decode_root(%{"public_key" => encoded} = root)
       when is_binary(encoded) and byte_size(encoded) == 44 do
    with {:ok, key} <- Base.decode64(encoded),
         ^encoded <- Base.encode64(key) do
      %{root | "public_key" => key}
    else
      _ -> :invalid
    end
  end

  defp decode_root(_), do: :invalid

  defp reader!(%HostedConfig{role: :api, endpoint: endpoint, repo: repo} = hosted, password) do
    if endpoint[:http][:ip] != {127, 0, 0, 1} or endpoint[:https] != nil,
      do: invalid!("MIXER_HTTP_BIND")

    if repo[:username] == @reader,
      do: invalid!("MIXER_DATABASE_USER")

    unless is_binary(password) and byte_size(password) in 1..4096 and
             password != repo[:password] and
             password != (hosted.create_repo || [])[:password],
           do: invalid!(@password)

    Keyword.merge(repo, username: @reader, password: password, pool_size: 1)
  end

  defp reader!(_, _), do: invalid!("MIXER_HOSTED_ROLE")

  defp invalid!(setting),
    do: raise(ArgumentError, "invalid or missing hosted setting: " <> setting)
end
