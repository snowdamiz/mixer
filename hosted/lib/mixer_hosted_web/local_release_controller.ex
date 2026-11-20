defmodule MixerHostedWeb.LocalReleaseController do
  @moduledoc false
  @behaviour Plug
  import Plug.Conn
  alias MixerHosted.Identity.VerifiedIdentity
  alias MixerHosted.Protocol.{ArtifactJSON, ArtifactV3Policy}
  alias MixerHosted.Releases
  alias MixerHostedWeb.Plugs.CustomerArtifactRequest, as: Request

  @maximum_body 128 * 1024
  @assignment_operations [:publish, :promote, :rollback]

  @impl true
  def init(operation) when operation in [:validate | @assignment_operations], do: operation

  @impl true
  def call(conn, operation) do
    identity = conn.assigns[:verified_identity]

    with :ok <- permission(identity),
         {:ok, route} <- route(conn, operation),
         {:ok, key, reason, bytes, conn} <- Request.read_json_mutation(conn, @maximum_body) do
      process(conn, operation, identity, route, key, reason, bytes)
    else
      {:error, error, conn} -> Request.reject(conn, error)
      {:error, error} -> Request.reject(conn, error)
    end
  end

  defp process(conn, operation, identity, route, key, reason, bytes) do
    with {:ok, command} <- decode(operation, bytes),
         hash =
           :crypto.hash(:sha256, [
             conn.method,
             " ",
             conn.request_path,
             <<0>>,
             reason,
             <<0>>,
             bytes
           ]),
         {:ok, result} <-
           Releases.cli(identity, route, command, key, Base.encode16(hash, case: :lower), reason) do
      conn
      |> Request.response_headers()
      |> put_resp_content_type("application/json")
      |> send_resp(200, Jason.encode!(response(operation, result)))
    else
      {:error, :permission_denied} -> Request.reject(conn, :role_denied)
      {:error, error} -> Request.reject(conn, error)
    end
  end

  defp permission(%VerifiedIdentity{identity_class: :human, scopes: scopes}) do
    if "mixer.release.publish" in scopes, do: :ok, else: {:error, :role_denied}
  end

  defp permission(%VerifiedIdentity{}), do: {:error, :role_denied}
  defp permission(_), do: {:error, :unauthenticated}

  defp route(%{method: "POST", query_string: "", remote_ip: {127, 0, 0, 1}} = conn, operation) do
    org = conn.path_params["organization_id"]
    project = conn.path_params["project_id"]
    channel = conn.path_params["channel"]

    with true <- ArtifactV3Policy.id?(org) and ArtifactV3Policy.id?(project),
         {:ok, suffix} <- suffix(operation, channel),
         true <- conn.request_path == "/v3/orgs/" <> org <> "/projects/" <> project <> suffix do
      {:ok, {org, project, channel}}
    else
      _ -> {:error, :not_found}
    end
  end

  defp route(_, _), do: {:error, :not_found}

  defp suffix(:validate, nil), do: {:ok, "/releases/validate"}

  defp suffix(operation, channel) when operation in @assignment_operations do
    if ArtifactV3Policy.id?(channel),
      do: {:ok, "/channels/" <> channel <> "/" <> Atom.to_string(operation)},
      else: {:error, :not_found}
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
        {:ok, {action, binary_part(bytes, start, length)}}

      _ ->
        {:error, :invalid_json}
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

  defp response(operation, result) when operation in @assignment_operations do
    result
    |> Map.take([:artifact_sha256, :rollout_basis_points, :sequence])
    |> Map.put(:delivery, "local_only")
  end
end
