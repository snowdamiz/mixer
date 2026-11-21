defmodule MixerHostedWeb.PublicReleaseController do
  @moduledoc false
  @behaviour Plug
  import Plug.Conn

  alias MixerHosted.Authorization.Scope
  alias MixerHosted.Protocol.ArtifactV3Policy
  alias MixerHosted.Releases.{PublicDelivery, Target}

  @offer_fields ~w(organization project app environment platform runtime channel installation)
  @tenant_fields ~w(organization project)

  @impl true
  def init(operation) when operation in [:offer, :artifact], do: operation

  @impl true
  def call(conn, operation) do
    conn = put_resp_header(conn, "cache-control", "no-store")

    result =
      case PublicDelivery.configuration() do
        {:ok, config} -> dispatch(operation, conn, config)
        :disabled -> {:error, :not_found}
      end

    case result do
      {:ok, bytes} -> json(conn, 200, bytes)
      :no_offer -> send_resp(conn, 204, "")
      {:error, :not_found} -> error(conn, 404, "not_found")
      {:error, :invalid_query} -> error(conn, 400, "invalid_query")
      {:error, :storage_unavailable} -> error(conn, 503, "storage_unavailable")
    end
  end

  defp dispatch(:offer, conn, config) do
    with {:ok, fields} <- query(conn.query_string, @offer_fields),
         true <- ArtifactV3Policy.id?(fields["installation"]),
         {:ok, target} <-
           Target.new(%Target{
             scope: %Scope{
               organization_id: fields["organization"],
               project_id: fields["project"],
               application_id: fields["app"],
               environment_id: fields["environment"]
             },
             platform: fields["platform"],
             runtime_sha256: fields["runtime"],
             channel: fields["channel"]
           }) do
      PublicDelivery.offer(config, target, fields["installation"])
    else
      _ -> {:error, :invalid_query}
    end
  end

  defp dispatch(:artifact, conn, config) do
    digest = conn.path_params["digest"]

    with true <- ArtifactV3Policy.digest?(digest),
         {:ok, %{"organization" => org, "project" => project}} <-
           query(conn.query_string, @tenant_fields),
         true <- ArtifactV3Policy.id?(org) and ArtifactV3Policy.id?(project) do
      PublicDelivery.artifact(config, org, project, digest)
    else
      _ -> {:error, :invalid_query}
    end
  end

  defp query(raw, names) when byte_size(raw) in 1..4096 do
    with pairs <- :binary.split(raw, "&", [:global]),
         true <- length(pairs) == length(names) do
      Enum.reduce_while(pairs, {:ok, %{}}, fn pair, {:ok, fields} ->
        case :binary.split(pair, "=") do
          [key, value] ->
            name = URI.decode_www_form(key)

            if name in names and not is_map_key(fields, name),
              do: {:cont, {:ok, Map.put(fields, name, URI.decode_www_form(value))}},
              else: {:halt, {:error, :invalid_query}}

          _ ->
            {:halt, {:error, :invalid_query}}
        end
      end)
    else
      _ -> {:error, :invalid_query}
    end
  end

  defp query(_, _), do: {:error, :invalid_query}

  defp error(conn, status, code), do: json(conn, status, Jason.encode!(%{error: %{code: code}}))

  defp json(conn, status, bytes),
    do: conn |> put_resp_content_type("application/json") |> send_resp(status, bytes)
end
