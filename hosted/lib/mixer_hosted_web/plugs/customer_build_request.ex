defmodule MixerHostedWeb.Plugs.CustomerBuildRequest do
  @moduledoc "Closed immutable selection parser; identity is assigned by trusted authentication."
  import Plug.Conn
  alias MixerHosted.CustomerBuilds.Selection
  @keys ~w(source_sha256 toolchain_lock_sha256 build_definition_sha256)
  @route ~w(organization_id project_id application_id build_id platform)
  def parse(conn) do
    with true <- conn.method == "GET",
         true <- is_map(conn.path_params),
         true <- Enum.sort(Map.keys(conn.path_params)) == Enum.sort(@route),
         true <- headers?(conn.req_headers),
         {:ok, filters} <- query(conn.query_string),
         raw = Map.merge(conn.path_params, filters),
         atom_keys = Map.new(raw, fn {k, v} -> {key(k), v} end),
         {:ok, selection} <- Selection.new(atom_keys),
         true <- conn.request_path == path(selection),
         {:ok, "", next} <- read_body(conn, length: 1, read_length: 1, read_timeout: 1000) do
      {:ok, selection, next}
    else
      _ -> {:error, :invalid_request}
    end
  rescue
    _ -> {:error, :invalid_request}
  end

  def path(s),
    do:
      "/v3/orgs/#{s.organization_id}/projects/#{s.project_id}/apps/#{s.application_id}/builds/#{s.build_id}/#{s.platform}"

  defp key("organization_id"), do: :organization_id
  defp key("project_id"), do: :project_id
  defp key("application_id"), do: :application_id
  defp key("build_id"), do: :build_id
  defp key("platform"), do: :platform
  defp key("source_sha256"), do: :source_sha256
  defp key("toolchain_lock_sha256"), do: :toolchain_lock_sha256
  defp key("build_definition_sha256"), do: :build_definition_sha256

  defp headers?(headers) do
    names = Enum.map(headers, &elem(&1, 0))

    length(names) == length(Enum.uniq(names)) and
      not Enum.any?(
        names,
        &(&1 in ~w(content-encoding transfer-encoding idempotency-key x-mixer-reason))
      ) and
      Enum.all?(headers, fn
        {"content-length", "0"} -> true
        {"content-length", _} -> false
        {"content-type", "application/json"} -> true
        {"content-type", _} -> false
        _ -> true
      end)
  end

  defp query(q) when is_binary(q) and byte_size(q) <= 512 do
    parts = :binary.split(q, "&", [:global])

    if length(parts) == 3 do
      Enum.reduce_while(parts, {:ok, %{}}, fn part, {:ok, acc} ->
        case :binary.split(part, "=") do
          [key, value] ->
            if key in @keys and not Map.has_key?(acc, key) and Selection.digest?(value),
              do: {:cont, {:ok, Map.put(acc, key, value)}},
              else: {:halt, :error}

          _ ->
            {:halt, :error}
        end
      end)
    else
      :error
    end
  end

  defp query(_), do: :error
end
