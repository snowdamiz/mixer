defmodule MixerHostedWeb.BrowserBuildCatalogRequest do
  @moduledoc false
  alias MixerHosted.CustomerBuildCatalog.Input

  @names %{
    "organization_id" => :organization_id,
    "project_id" => :project_id,
    "application_id" => :application_id,
    "cursor" => :cursor
  }
  def parse(path, raw)
      when path in ["/console-api/v1/applications", "/console-api/v1/build-catalog"] and
             is_binary(raw) and byte_size(raw) in 1..8192 do
    kind = if path == "/console-api/v1/applications", do: :applications, else: :builds

    allowed =
      if kind == :applications,
        do: ~w(organization_id project_id cursor),
        else: ~w(organization_id project_id application_id cursor)

    pairs = :binary.split(raw, "&", [:global])

    with true <- length(pairs) in (length(allowed) - 1)..length(allowed),
         {:ok, values} <-
           Enum.reduce_while(pairs, {:ok, %{}}, fn pair, {:ok, acc} ->
             case :binary.split(pair, "=") do
               [k, v] ->
                 if k in allowed and not Map.has_key?(acc, @names[k]) and byte_size(v) in 1..4200 and
                      not Regex.match?(~r/%(?![0-9a-fA-F]{2})/, v),
                    do: {:cont, {:ok, Map.put(acc, @names[k], URI.decode_www_form(v))}},
                    else: {:halt, :error}

               _ ->
                 {:halt, :error}
             end
           end),
         scope = Map.delete(values, :cursor),
         page = %{cursor: Map.get(values, :cursor)},
         {:ok, _} <- Input.new(kind, scope, page) do
      {:ok, {kind, scope, page}}
    else
      _ -> {:error, :invalid_request}
    end
  rescue
    _ -> {:error, :invalid_request}
  end

  def parse(_, _), do: {:error, :invalid_request}
end
