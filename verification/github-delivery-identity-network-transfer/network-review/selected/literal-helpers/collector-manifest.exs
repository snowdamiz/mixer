
defmodule MixerIdentityNetworkCollector.Manifest do
  def files(path) do
    case File.lstat!(path).type do
      :regular -> [path]
      :directory -> File.ls!(path) |> Enum.sort() |> Enum.flat_map(&files(Path.join(path, &1)))
      _ -> raise "non-regular source/dependency/tool input"
    end
  end
  def entry(path) do
    bytes = File.read!(path)
    %{"bytes" => byte_size(bytes), "sha256" => Base.encode16(:crypto.hash(:sha256, bytes), case: :lower)}
  end
  def run do
    frozen = File.read!("/workspace/frozen-manifest.json") |> :json.decode()
    source = Map.new(frozen, fn {path, expected} ->
      actual = entry("/workspace/" <> path)
      ^expected = actual
      {path, actual}
    end)
    deps = Map.new(files("/workspace/hosted/deps"), fn path -> {Path.relative_to(path, "/workspace"), entry(path)} end)
    tools = Map.new(Enum.flat_map(["/workspace/tooling/mix", "/workspace/tooling/rebar3"], &files/1), fn path -> {Path.relative_to(path, "/workspace"), entry(path)} end)
    helpers = Map.new(Path.wildcard("/workspace/collector-*.exs") ++ ["/workspace/frozen-manifest.json"], fn path -> {Path.relative_to(path, "/workspace"), entry(path)} end)
    value = %{"source" => source, "deps" => deps, "tools" => tools, "helpers" => helpers}
    if System.argv() == ["archive-list"] do
      names = Map.keys(source) ++ Map.keys(deps) ++ Map.keys(tools) ++ Map.keys(helpers)
      true = Enum.all?(names, &(not String.contains?(&1, ["\n", "\r", "\0"])))
      File.write!("/workspace/archive-files.txt", Enum.join(Enum.sort(names), "\n") <> "\n", [:exclusive])
    end
    IO.puts("IDENTITY_JSON=" <> IO.iodata_to_binary(:json.encode(value)))
  end
end
MixerIdentityNetworkCollector.Manifest.run()
