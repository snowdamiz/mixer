rows =
  for {name, tuple} <- Mix.Dep.Lock.read() do
    {:ok, metadata} = :file.consult(String.to_charlist("deps/#{name}/hex_metadata.config"))
    metadata = Map.new(metadata)

    %{
      name: name,
      version: elem(tuple, 2),
      checksum: elem(tuple, 3),
      outer_checksum: elem(tuple, 7),
      licenses: Map.fetch!(metadata, "licenses"),
      origin: "https://hex.pm/packages/#{name}"
    }
  end

IO.puts(Jason.encode!(%{dependencies: Enum.sort_by(rows, & &1.name)}, pretty: true))
