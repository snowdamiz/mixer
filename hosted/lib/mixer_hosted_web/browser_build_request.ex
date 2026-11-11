defmodule MixerHostedWeb.BrowserBuildRequest do
  @moduledoc "Private closed query selection; no identity or dependencies are accepted."
  alias MixerHosted.CustomerBuilds.Selection

  @keys ~w(organization_id project_id application_id build_id platform source_sha256 toolchain_lock_sha256 build_definition_sha256)a
  @names Map.new(@keys, &{Atom.to_string(&1), &1})

  def parse(raw) when is_binary(raw) and byte_size(raw) in 1..2048 do
    pairs = :binary.split(raw, "&", [:global])

    with true <- length(pairs) == 8,
         {:ok, fields} <-
           Enum.reduce_while(pairs, {:ok, %{}}, fn pair, {:ok, acc} ->
             case :binary.split(pair, "=") do
               [name, value] ->
                 with key when is_atom(key) and not is_nil(key) <- @names[name],
                      false <- Map.has_key?(acc, key),
                      true <- byte_size(value) in 1..384,
                      false <- Regex.match?(~r/%(?![0-9a-fA-F]{2})/, value) do
                   {:cont, {:ok, Map.put(acc, key, URI.decode_www_form(value))}}
                 else
                   _ -> {:halt, {:error, :invalid_request}}
                 end

               _ ->
                 {:halt, {:error, :invalid_request}}
             end
           end) do
      Selection.new(fields)
    else
      _ -> {:error, :invalid_request}
    end
  rescue
    _ -> {:error, :invalid_request}
  end

  def parse(_), do: {:error, :invalid_request}
end
