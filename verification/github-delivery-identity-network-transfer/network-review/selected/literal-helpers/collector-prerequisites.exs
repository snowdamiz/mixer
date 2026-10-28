
emit = fn value -> IO.puts("IDENTITY_JSON=" <> IO.iodata_to_binary(:json.encode(value))) end
hash = fn path -> :crypto.hash(:sha256, File.read!(path)) |> Base.encode16(case: :lower) end
tools = ["/usr/bin/env", "/usr/bin/tar", "/usr/bin/openssl", "/usr/local/bin/elixir", "/usr/local/bin/mix", "/usr/local/bin/erl", "/usr/local/bin/escript"]
rows = Map.new(tools, fn path ->
  %{type: :regular, mode: mode} = File.stat!(path)
  true = Bitwise.band(mode, 0o111) != 0
  {path, %{"sha256" => hash.(path), "bytes" => File.stat!(path).size}}
end)
"/usr/bin/openssl" = System.find_executable("openssl")
"1.20.4" = System.version()
"29" = to_string(:erlang.system_info(:otp_release))
otp_path = Path.join([to_string(:code.root_dir()), "releases", "29", "OTP_VERSION"])
"29.1.1" = File.read!(otp_path) |> String.trim()
{mix, 0} = System.cmd("/usr/local/bin/mix", ["--version"], stderr_to_stdout: true)
true = String.contains?(mix, "Mix 1.20.4")
{openssl, 0} = System.cmd("/usr/bin/openssl", ["version", "-a"], stderr_to_stdout: true)
{tar, 0} = System.cmd("/usr/bin/tar", ["--version"], stderr_to_stdout: true)
true = byte_size(tar) < 65536
versions = %{"/usr/bin/tar" => tar}
emit.(%{"elixir" => System.version(), "otp_patch" => File.read!(otp_path) |> String.trim(), "mix" => mix, "openssl" => openssl, "crypto" => inspect(:crypto.info_lib()), "tools" => rows, "versions" => versions})
