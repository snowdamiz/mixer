defmodule MixerHosted.Releases.PublicDelivery do
  @moduledoc """
  Anonymous v3 reads for explicitly provisioned local installation targets.

  Enable the API child with `:local_release_delivery` containing a target, its
  installed host, current public roots and restricted `:repo` connection
  options. Its SQL login receives EXECUTE on only the two delivery functions
  installed by the optional local release delivery migration.
  """
  alias MixerHosted.Protocol.{ArtifactAdmission, ArtifactCBOR, ArtifactV3Policy, AssignmentV3}
  alias MixerHosted.Releases.{DeliveryAdmission, DeliveryRepo, Target}

  @key :local_release_delivery
  @role "mixer_release_delivery"
  @enrollment_guard " WHERE pg_catalog.to_regclass('public.mixer_release_delivery_enrollments') IS NOT NULL"

  def children(endpoint) do
    case provision() do
      :disabled ->
        []

      {:ok, %{repo: options}} ->
        if endpoint[:http][:ip] != {127, 0, 0, 1} or endpoint[:https] != nil,
          do: raise(ArgumentError, "local release delivery requires a loopback HTTP listener")

        [{DeliveryRepo, options}, {DeliveryAdmission, @role}]

      {:error, :invalid_provisioning} ->
        raise ArgumentError, "invalid local release delivery provisioning"
    end
  end

  def configuration do
    case provision() do
      {:ok, config} -> if Process.whereis(DeliveryRepo), do: {:ok, config}, else: :disabled
      _ -> :disabled
    end
  end

  def offer(config, %Target{} = target, installation) do
    with {:ok, entry} <- select(config, target) do
      case rows(
             config,
             "SELECT * FROM public.mixer_release_delivery_offer($1,$2,$3,$4,$5,$6,$7)",
             coordinates(target)
           ) do
        {:ok, [[sequence, rollout, digest, bytes, manifest, payload]]} ->
          offer_signed(
            config,
            entry,
            installation,
            sequence,
            rollout,
            digest,
            bytes,
            manifest,
            payload
          )

        {:ok, []} ->
          :no_offer

        _ ->
          {:error, :storage_unavailable}
      end
    else
      :error -> :no_offer
    end
  end

  def artifact(%{target: target} = config, org, project, digest) do
    if target.scope.organization_id == org and target.scope.project_id == project do
      artifact(config, target, digest)
    else
      {:error, :not_found}
    end
  end

  def artifact(config, %Target{} = target, digest) do
    with {:ok, entry} <- select(config, target) do
      case rows(
             config,
             "SELECT * FROM public.mixer_release_delivery_artifact($1,$2,$3,$4,$5,$6,$7,$8)",
             coordinates(target) ++ [digest]
           ) do
        {:ok, [[envelope, envelope_digest, payload_digest]]} ->
          verify_artifact(config, entry, digest, envelope, envelope_digest, payload_digest)

        {:ok, []} ->
          {:error, :not_found}

        _ ->
          {:error, :storage_unavailable}
      end
    else
      :error -> {:error, :not_found}
    end
  end

  @doc false
  def select(%{target: target} = config, target), do: {:ok, config}
  def select(%{registry: registry}, target), do: Map.fetch(registry, target)
  def select(_, _), do: :error

  defp offer_signed(
         config,
         entry,
         installation,
         sequence,
         rollout,
         digest,
         bytes,
         manifest,
         payload
       ) do
    artifact = %{signed_manifest_bytes: manifest, payload: payload}
    target = entry.target
    context = %{channel: target.channel, last_sequence: 0, now: System.system_time(:second)}
    sequence = Decimal.to_integer(sequence)

    with {:ok, %{assignment: assignment}} <-
           AssignmentV3.verify(bytes, artifact, entry.roots, entry.host, context),
         %{
           "sequence" => ^sequence,
           "rollout_basis_points" => ^rollout,
           "artifact_sha256" => ^digest
         } <-
           assignment,
         true <- eligible?(assignment, installation),
         {:ok, ^config} <- configuration() do
      url = "/v3/artifacts/" <> digest <> "?" <> artifact_query(config, target)
      {:ok, ["{\"signed_assignment\":", bytes, ",\"artifact_url\":", Jason.encode!(url), "}"]}
    else
      _ -> :no_offer
    end
  end

  defp artifact_query(%{target: target}, target) do
    URI.encode_query(organization: target.scope.organization_id, project: target.scope.project_id)
  end

  defp artifact_query(_config, target) do
    target
    |> Target.signed_scope()
    |> Map.merge(%{"runtime" => target.runtime_sha256, "channel" => target.channel})
    |> URI.encode_query()
  end

  defp verify_artifact(config, entry, digest, envelope, envelope_digest, payload_digest) do
    with {:ok, %{manifest_sha256: ^digest, payload_sha256: ^payload_digest}} <-
           ArtifactAdmission.admit(
             envelope,
             entry.host,
             entry.roots,
             System.system_time(:second)
           ),
         ^envelope_digest <- Base.encode16(:crypto.hash(:sha256, envelope), case: :lower),
         {:ok, ^config} <- configuration() do
      {:ok, envelope}
    else
      _ -> {:error, :not_found}
    end
  end

  defp eligible?(assignment, installation) do
    cohort =
      assignment["scope"]
      |> Map.take(~w(organization project app environment))
      |> Map.merge(%{"channel" => assignment["channel"], "installation" => installation})

    {:ok, bytes} = ArtifactCBOR.encode(cohort)
    bucket = rem(:binary.decode_unsigned(:crypto.hash(:sha256, bytes)), 10_000)
    bucket < assignment["rollout_basis_points"]
  end

  defp rows(config, sql, args) do
    # An opted-in API must not serve rows from the pre-enrollment SQL functions.
    sql = if Map.has_key?(config, :registry), do: sql <> @enrollment_guard, else: sql

    case Ecto.Adapters.SQL.query(DeliveryRepo, sql, args,
           timeout: 5_000,
           queue: false,
           log: false
         ) do
      {:ok, %{rows: rows}} -> {:ok, rows}
      {:error, _} -> {:error, :storage_unavailable}
    end
  end

  defp coordinates(%Target{scope: scope} = target) do
    [
      scope.organization_id,
      scope.project_id,
      scope.application_id,
      scope.environment_id,
      target.platform,
      target.runtime_sha256,
      target.channel
    ]
  end

  defp provision do
    case Application.get_env(:mixer_hosted, @key, :disabled) do
      :disabled ->
        :disabled

      %{target: %Target{}, repo: repo} = config ->
        with true <- target_config?(Map.drop(config, [:repo, :registry])),
             true <- registry_config?(config),
             true <- Keyword.keyword?(repo) and repo[:username] == @role do
          {:ok, config}
        else
          _ -> {:error, :invalid_provisioning}
        end

      _ ->
        {:error, :invalid_provisioning}
    end
  end

  defp registry_config?(%{target: default, registry: registry})
       when is_map(registry) and map_size(registry) in 1..32 do
    Enum.all?(registry, fn
      {target, %{target: target, host: host, roots: roots} = entry} when target != default ->
        target_config?(entry) and Enum.all?(roots, &(&1["scope"] == host["scope"]))

      _ ->
        false
    end)
  end

  defp registry_config?(config), do: not Map.has_key?(config, :registry)

  defp target_config?(%{target: target, host: host, roots: roots} = entry)
       when map_size(entry) == 3 do
    Target.new(target) == {:ok, target} and ArtifactV3Policy.host?(host) and
      host["scope"] == Target.signed_scope(target) and host["runtime"] == target.runtime_sha256 and
      ArtifactV3Policy.roots?(roots)
  end

  defp target_config?(_), do: false
end
