defmodule MixerHosted.Releases.RuntimeProvisioning do
  @moduledoc "Operator provisioning for local signed v3 release delivery."
  alias MixerHosted.Authorization.Scope
  alias MixerHosted.Protocol.{ArtifactJSON, ArtifactV3Policy}
  alias MixerHosted.Releases.EnvironmentPromotion.Direction
  alias MixerHosted.Releases.EnvironmentPromotion.Direction.Enrollment
  alias MixerHosted.Releases.Target
  alias MixerHosted.RuntimeConfig, as: HostedConfig

  @config "MIXER_LOCAL_RELEASE_CONFIG"
  @registry "MIXER_LOCAL_RELEASE_TARGET_REGISTRY"
  @directions "MIXER_LOCAL_STAGE_PROMOTION_DIRECTIONS"
  @password "MIXER_LOCAL_RELEASE_DELIVERY_PASSWORD"
  @writer_enabled "MIXER_LOCAL_RELEASE_WRITER_ENABLED"
  @reader "mixer_release_delivery"
  @max_config_bytes 65_536
  @max_additional_targets 32
  @max_directions 32

  def load!(env, %HostedConfig{} = hosted) do
    registry = Map.fetch(env, @registry)

    case {Map.fetch(env, @config), Map.fetch(env, @password)} do
      {:error, :error} when not hosted.local_release_jobs and registry == :error ->
        :disabled

      {{:ok, raw}, {:ok, password}} ->
        target = target!(raw)
        repo = reader!(hosted, password)
        delivery = target |> Map.put(:repo, repo) |> add_registry!(registry)
        {target, delivery}

      {:error, _} ->
        invalid!(@config)

      {_, :error} ->
        invalid!(@password)
    end
  end

  @doc false
  def writer_options!(env, %HostedConfig{role: role, repo: repo}, provisioning) do
    case {Map.get(env, @writer_enabled, "false"), role, provisioning} do
      {"false", _, _} ->
        nil

      {"true", :api, {%{target: %Target{}}, %{repo: _reader}}} ->
        Keyword.put(repo, :pool_size, 1)

      _ ->
        invalid!(@writer_enabled)
    end
  end

  @doc false
  def stage_promotion_directions!(env, provisioning, writer) do
    case {Map.fetch(env, @directions), provisioning, writer} do
      {:error, _, _} ->
        %{}

      {{:ok, raw}, {default, delivery}, [_ | _]} ->
        decode_directions!(raw, default, Map.get(delivery, :registry, %{}))

      _ ->
        invalid!(@directions)
    end
  end

  defp decode_directions!(raw, default, registry) do
    with {:ok, documents, _, _} <- ArtifactJSON.decode(raw, @max_config_bytes),
         true <- ArtifactV3Policy.bounded_list?(documents, @max_directions),
         [_ | _] <- documents do
      targets =
        Map.new([default | Map.values(registry)], fn entry ->
          wire =
            Map.new(Target.wire(entry.target), fn {key, value} -> {Atom.to_string(key), value} end)

          {wire, struct!(Enrollment, entry)}
        end)

      Enum.reduce(documents, %{}, fn document, directions ->
        with true <- ArtifactV3Policy.exact?(document, ~w(direction_id source destination)),
             id = document["direction_id"],
             true <- Direction.id?(id) and not is_map_key(directions, id),
             {:ok, source, source_scope} <- direction_side(document["source"], targets),
             {:ok, destination, destination_scope} <-
               direction_side(document["destination"], targets),
             true <- source_scope.environment_id != destination_scope.environment_id,
             true <-
               %{source_scope | environment_id: destination_scope.environment_id} ===
                 destination_scope do
          Map.put(directions, id, %Direction{source: source, destination: destination})
        else
          _ -> invalid!(@directions)
        end
      end)
    else
      _ -> invalid!(@directions)
    end
  end

  defp direction_side(%{"ios" => ios, "android" => android} = side, targets)
       when map_size(side) == 2 do
    with %{^ios => %Enrollment{target: %Target{platform: "ios", scope: scope}} = ios_entry} <-
           targets,
         %{
           ^android =>
             %Enrollment{target: %Target{platform: "android", scope: ^scope}} = android_entry
         } <-
           targets do
      {:ok, %{ios: ios_entry, android: android_entry}, scope}
    end
  end

  defp direction_side(_, _), do: :error

  defp target!(raw) do
    with {:ok, document, _, _} <- ArtifactJSON.decode(raw, @max_config_bytes),
         {:ok, target} <- decode_target(document) do
      target
    else
      _ -> invalid!(@config)
    end
  end

  defp add_registry!(delivery, :error), do: delivery

  defp add_registry!(%{target: default} = delivery, {:ok, raw}) do
    with {:ok, documents, _, _} <- ArtifactJSON.decode(raw, @max_config_bytes),
         true <- ArtifactV3Policy.bounded_list?(documents, @max_additional_targets),
         [_ | _] <- documents do
      registry =
        Enum.reduce(documents, %{}, fn document, entries ->
          case decode_target(document) do
            {:ok, %{target: target} = entry}
            when target != default and not is_map_key(entries, target) ->
              Map.put(entries, target, entry)

            _ ->
              invalid!(@registry)
          end
        end)

      Map.put(delivery, :registry, registry)
    else
      _ -> invalid!(@registry)
    end
  end

  defp decode_target(document) do
    with true <- ArtifactV3Policy.exact?(document, ~w(host channel roots)),
         host = document["host"],
         true <- ArtifactV3Policy.host?(host),
         {:ok, target} <- target(host, document["channel"]),
         {:ok, roots} <- roots(document["roots"], host["scope"]) do
      {:ok, %{target: target, host: host, roots: roots}}
    else
      _ -> :error
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
