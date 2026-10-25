# Independently authored, offline documentation inventory only. No Repo, app,
# frozen lane, database, provider, network, native process or credential is used.
defmodule ContractJSON do
  def encode(nil), do: "null"
  def encode(true), do: "true"
  def encode(false), do: "false"
  def encode(value) when is_integer(value), do: Integer.to_string(value)
  def encode(value) when is_atom(value), do: encode(Atom.to_string(value))
  def encode(value) when is_binary(value) do
    escaped = for <<byte <- value>>, into: "" do
      case byte do
        ?" -> "\\\""
        ?\\ -> "\\\\"
        b when b < 32 -> "\\u" <> String.pad_leading(Integer.to_string(b, 16), 4, "0")
        b -> <<b>>
      end
    end
    "\"" <> escaped <> "\""
  end
  def encode(values) when is_list(values), do: "[" <> Enum.map_join(values, ",", &encode/1) <> "]"
  def encode(values) when is_map(values) do
    fields = values |> Enum.sort_by(fn {key, _} -> to_string(key) end)
    "{" <> Enum.map_join(fields, ",", fn {key, value} -> encode(to_string(key)) <> ":" <> encode(value) end) <> "}"
  end
end

[path] = System.argv()
Code.require_file(path)
schema = MixerHosted.BrowserAuth.StorageSchema
returns = schema.statements()
  |> Enum.filter(&String.starts_with?(&1, "CREATE FUNCTION public."))
  |> Map.new(fn sql ->
    [name, rest] = sql |> String.replace_prefix("CREATE FUNCTION public.", "") |> String.split("(", parts: 2)
    result = rest |> String.split(" RETURNS ", parts: 2) |> List.last() |> String.split("\n", parts: 2) |> hd()
    {name, result}
  end)
manifest = schema.catalog_manifest()
functions = Map.new(manifest.functions, fn {name, spec} ->
  {name, Map.merge(spec, %{result: Map.fetch!(returns, name), source_sha256: Base.encode16(:crypto.hash(:sha256, spec.source), case: :lower)})}
end)
IO.puts(ContractJSON.encode(%{manifest | functions: functions}))
