
[role] = System.argv()
paths = case role do
  "prepare" -> ["/workspace", "/workspace/tooling", "/tmp"]
  "test" -> ["/workspace", "/workspace/tooling", "/tmp", "/run"]
end
source = "/proc/self/mountinfo"
{:ok, io} = File.open(source, [:read, :binary])
bytes = try do
  data = IO.binread(io, 65_537)
  true = is_binary(data) and byte_size(data) > 0 and byte_size(data) <= 65_536
  data
after
  :ok = File.close(io)
end
lines = String.split(bytes, "\n", trim: true)
true = length(lines) <= 1024
selected = Enum.filter(lines, fn line ->
  [_id, _parent, _device, _root, path, _flags | _] = String.split(line)
  Enum.any?(paths, fn selected_path -> path == selected_path or String.starts_with?(path, selected_path <> "/") end)
end)
true = length(selected) <= 32 and Enum.all?(selected, &(byte_size(&1) <= 4096))
modes = Map.new(paths, fn path ->
  %{type: :directory, mode: mode} = File.stat!(path)
  {path, Bitwise.band(mode, 0o7777)}
end)
result = %{"role" => role, "source" => source, "read_bytes" => byte_size(bytes), "read_sha256" => Base.encode16(:crypto.hash(:sha256, bytes), case: :lower), "selected_lines" => selected, "path_modes" => modes}
IO.puts("IDENTITY_JSON=" <> IO.iodata_to_binary(:json.encode(result)))
