defmodule MixerHosted.Releases.PublicDelivery do
  @moduledoc """
  Anonymous v3 reads for an explicitly provisioned local installation target.

  Enable the API child with `:local_release_delivery` containing a target, its
  installed host, current public roots and restricted `:repo` connection
  options. Its SQL login receives EXECUTE on only the two delivery functions
  installed by the optional local release delivery migration.
  """
  alias MixerHosted.Protocol.{ArtifactAdmission, ArtifactCBOR, ArtifactV3Policy, AssignmentV3}
  alias MixerHosted.Releases.{DeliveryRepo, Target}

  @key :local_release_delivery
  @role "mixer_release_delivery"

  def children(endpoint) do
    case provision() do
      :disabled ->
        []

      {:ok, %{repo: options}} ->
        if endpoint[:http][:ip] != {127, 0, 0, 1} or endpoint[:https] != nil,
          do: raise(ArgumentError, "local release delivery requires a loopback HTTP listener")

        [{DeliveryRepo, options}]

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

  def offer(%{target: target} = config, %Target{} = requested, installation) do
    if requested == target do
      case rows(
             "SELECT * FROM public.mixer_release_delivery_offer($1,$2,$3,$4,$5,$6,$7)",
             coordinates(target)
           ) do
        {:ok, [[sequence, rollout, digest, bytes, manifest, payload]]} ->
          offer_signed(config, installation, sequence, rollout, digest, bytes, manifest, payload)

        {:ok, []} ->
          :no_offer

        _ ->
          {:error, :storage_unavailable}
      end
    else
      :no_offer
    end
  end

  def artifact(%{target: target} = config, org, project, digest) do
    if target.scope.organization_id == org and target.scope.project_id == project do
      case rows(
             "SELECT * FROM public.mixer_release_delivery_artifact($1,$2,$3,$4,$5,$6,$7,$8)",
             coordinates(target) ++ [digest]
           ) do
        {:ok, [[envelope, envelope_digest, payload_digest]]} ->
          verify_artifact(config, digest, envelope, envelope_digest, payload_digest)

        {:ok, []} ->
          {:error, :not_found}

        _ ->
          {:error, :storage_unavailable}
      end
    else
      {:error, :not_found}
    end
  end

  defp offer_signed(config, installation, sequence, rollout, digest, bytes, manifest, payload) do
    artifact = %{signed_manifest_bytes: manifest, payload: payload}
    target = config.target
    context = %{channel: target.channel, last_sequence: 0, now: System.system_time(:second)}
    sequence = Decimal.to_integer(sequence)

    with {:ok, %{assignment: assignment}} <-
           AssignmentV3.verify(bytes, artifact, config.roots, config.host, context),
         %{
           "sequence" => ^sequence,
           "rollout_basis_points" => ^rollout,
           "artifact_sha256" => ^digest
         } <-
           assignment,
         true <- eligible?(assignment, installation),
         {:ok, ^config} <- configuration() do
      tenant =
        URI.encode_query(
          organization: target.scope.organization_id,
          project: target.scope.project_id
        )

      url = "/v3/artifacts/" <> digest <> "?" <> tenant
      {:ok, ["{\"signed_assignment\":", bytes, ",\"artifact_url\":", Jason.encode!(url), "}"]}
    else
      _ -> :no_offer
    end
  end

  defp verify_artifact(config, digest, envelope, envelope_digest, payload_digest) do
    with {:ok, %{manifest_sha256: ^digest, payload_sha256: ^payload_digest}} <-
           ArtifactAdmission.admit(
             envelope,
             config.host,
             config.roots,
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

  defp rows(sql, args) do
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

      %{target: %Target{} = target, host: host, roots: roots, repo: repo} = config
      when map_size(config) == 4 ->
        with {:ok, ^target} <- Target.new(target),
             true <- ArtifactV3Policy.host?(host) and host["scope"] == Target.signed_scope(target),
             true <- host["runtime"] == target.runtime_sha256 and ArtifactV3Policy.roots?(roots),
             true <- Keyword.keyword?(repo) and repo[:username] == @role do
          {:ok, config}
        else
          _ -> {:error, :invalid_provisioning}
        end

      _ ->
        {:error, :invalid_provisioning}
    end
  end
end
