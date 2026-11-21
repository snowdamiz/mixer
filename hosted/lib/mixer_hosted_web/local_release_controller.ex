defmodule MixerHostedWeb.LocalReleaseController do
  @moduledoc false
  @behaviour Plug
  import Plug.Conn
  alias MixerHosted.Identity.VerifiedIdentity
  alias MixerHosted.Protocol.{ArtifactJSON, ArtifactV3Policy}
  alias MixerHosted.Releases
  alias MixerHostedWeb.Endpoint
  alias MixerHostedWeb.Plugs.CustomerArtifactRequest, as: Request

  @maximum_body 128 * 1024
  @promotion_body 160 * 1024
  @signed_limit 64 * 1024
  @promotion_assignments %{
    "ios_signed_assignment" => :ios,
    "android_signed_assignment" => :android
  }
  @assignment_operations [:publish, :promote, :rollback]
  @channel_operations [:halt | @assignment_operations]
  @health_fields ~w(sequence activated pending adverse_signals)

  @impl true
  def init(operation) when operation in [:validate, :stage_promote | @channel_operations],
    do: operation

  @impl true
  def call(conn, operation) do
    identity = conn.assigns[:verified_identity]

    with :ok <- permission(identity),
         {:ok, route} <- route(conn, operation),
         {:ok, key, reason, bytes, conn} <- read_mutation(conn, operation) do
      process(conn, operation, identity, route, key, reason, bytes)
    else
      {:error, error, conn} -> Request.reject(conn, error)
      {:error, error} -> Request.reject(conn, error)
    end
  end

  defp read_mutation(conn, :stage_promote),
    do: Request.read_json_mutation(conn, @promotion_body, :stage_promote)

  defp read_mutation(conn, _), do: Request.read_json_mutation(conn, @maximum_body)

  defp process(conn, operation, identity, route, key, reason, bytes) do
    with {:ok, command} <- decode(operation, bytes),
         {:ok, result} <- execute(operation, conn, identity, route, command, key, reason, bytes) do
      conn
      |> Request.response_headers()
      |> put_resp_content_type("application/json")
      |> send_resp(200, Jason.encode!(response(operation, result)))
    else
      {:error, :permission_denied} -> Request.reject(conn, :role_denied)
      {:error, error} -> Request.reject(conn, error)
    end
  end

  defp execute(:stage_promote, _, identity, route, {source, assignments}, key, reason, _) do
    Releases.promote_staged_environment(identity, route, source, assignments, key, reason)
  end

  defp execute(_, conn, identity, route, command, key, reason, bytes) do
    hash =
      :crypto.hash(:sha256, [conn.method, " ", conn.request_path, <<0>>, reason, <<0>>, bytes])

    Releases.cli(identity, route, command, key, Base.encode16(hash, case: :lower), reason)
  end

  defp permission(%VerifiedIdentity{identity_class: :human, scopes: scopes}) do
    if "mixer.release.publish" in scopes, do: :ok, else: {:error, :role_denied}
  end

  defp permission(%VerifiedIdentity{}), do: {:error, :role_denied}
  defp permission(_), do: {:error, :unauthenticated}

  defp route(%{method: "POST", query_string: "", remote_ip: {127, 0, 0, 1}} = conn, operation) do
    org = conn.path_params["organization_id"]
    project = conn.path_params["project_id"]

    with true <- ArtifactV3Policy.id?(org) and ArtifactV3Policy.id?(project),
         {:ok, suffix, route} <- route_suffix(conn, operation, org, project),
         true <- conn.request_path == "/v3/orgs/" <> org <> "/projects/" <> project <> suffix do
      {:ok, route}
    else
      _ -> {:error, :not_found}
    end
  end

  defp route(_, _), do: {:error, :not_found}

  defp route_suffix(conn, :stage_promote, org, project) do
    app = conn.path_params["application_id"]
    direction = conn.path_params["direction_id"]

    if ArtifactV3Policy.id?(app) and ArtifactV3Policy.id?(direction) and
         conn.scheme == :http and (Endpoint.config(:http) || [])[:ip] == {127, 0, 0, 1} and
         Endpoint.config(:https) in [nil, false] do
      {:ok, "/apps/" <> app <> "/release-promotions/" <> direction,
       {org, project, app, direction}}
    else
      {:error, :not_found}
    end
  end

  defp route_suffix(_, :validate, org, project),
    do: {:ok, "/releases/validate", {org, project, nil}}

  defp route_suffix(conn, operation, org, project) when operation in @channel_operations do
    channel = conn.path_params["channel"]

    if ArtifactV3Policy.id?(channel),
      do:
        {:ok, "/channels/" <> channel <> "/" <> Atom.to_string(operation),
         {org, project, channel}},
      else: {:error, :not_found}
  end

  defp decode(:stage_promote, bytes) do
    with {:ok, body, spans, _} <- ArtifactJSON.decode(bytes, @promotion_body),
         %{
           "source_ios_sequence" => ios,
           "source_android_sequence" => android,
           "ios_signed_assignment" => ios_assignment,
           "android_signed_assignment" => android_assignment
         }
         when map_size(body) == 4 and is_map(ios_assignment) and is_map(android_assignment) <-
           body,
         true <- Enum.all?([ios, android], &(ArtifactV3Policy.uint?(&1) and &1 > 0)),
         assignments = promotion_assignments(bytes, spans),
         true <- map_size(assignments) == 2 do
      {:ok, {%{ios: ios, android: android}, assignments}}
    else
      _ -> {:error, :invalid_json}
    end
  end

  defp decode(operation, bytes) do
    case {operation, ArtifactJSON.decode(bytes, @maximum_body)} do
      {:validate, {:ok, %{"artifact_sha256" => digest} = body, _, _}} when map_size(body) == 1 ->
        if ArtifactV3Policy.digest?(digest),
          do: {:ok, {:validate, digest}},
          else: {:error, :invalid_json}

      {action, {:ok, %{"signed_assignment" => assignment} = body, [{_, _, start, length}], _}}
      when action in @assignment_operations and map_size(body) == 1 and is_map(assignment) and
             length <= 65_536 ->
        {:ok, {action, binary_part(bytes, start, length), nil}}

      {:halt, {:ok, %{"signed_assignment" => assignment, "health" => health} = body, spans, _}}
      when map_size(body) == 2 and is_map(assignment) ->
        decode_halt(bytes, spans, health)

      _ ->
        {:error, :invalid_json}
    end
  end

  defp promotion_assignments(bytes, spans) do
    for {key_start, key_length, start, length} <- spans,
        length <= @signed_limit,
        key = Jason.decode!(binary_part(bytes, key_start, key_length)),
        platform = Map.get(@promotion_assignments, key),
        platform != nil,
        into: %{},
        do: {platform, binary_part(bytes, start, length)}
  end

  defp decode_halt(bytes, spans, health) do
    span =
      Enum.find(spans, fn {start, length, _, _} ->
        Jason.decode!(binary_part(bytes, start, length)) == "signed_assignment"
      end)

    with {_, _, start, length} when length <= 65_536 <- span,
         true <- ArtifactV3Policy.exact?(health, @health_fields),
         true <- Enum.all?(Map.values(health), &ArtifactV3Policy.uint?/1) do
      if health["sequence"] > 0 and health["adverse_signals"] > 0,
        do: {:ok, {:halt, binary_part(bytes, start, length), health}},
        else: {:error, :invalid_health}
    else
      _ -> {:error, :invalid_json}
    end
  end

  defp response(:validate, %{artifact_sha256: digest}) do
    %{
      artifact_sha256: digest,
      protocol_valid: true,
      compiler_eligibility_verified: false,
      policy_approved: false,
      mobile_qualified: false
    }
  end

  defp response(:stage_promote, %{ios: ios, android: android}) do
    %{
      ios: assignment_response(ios),
      android: assignment_response(android),
      delivery: "local_only"
    }
  end

  defp response(operation, result) when operation in @assignment_operations,
    do: Map.put(assignment_response(result), :delivery, "local_only")

  defp response(:halt, %{halt: receipt}), do: receipt

  defp assignment_response(result) do
    Map.take(result, [:artifact_sha256, :rollout_basis_points, :sequence])
  end
end
