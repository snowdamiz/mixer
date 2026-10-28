
emit = fn value -> IO.puts("IDENTITY_JSON=" <> IO.iodata_to_binary(:json.encode(value))) end
hash = fn path -> :crypto.hash(:sha256, File.read!(path)) |> Base.encode16(case: :lower) end
tools = ["/usr/bin/env", "/usr/bin/tar", "/usr/bin/openssl", "/usr/local/bin/elixir", "/usr/local/bin/mix", "/usr/local/bin/erl", "/usr/local/bin/escript"]
rows = Map.new(tools, fn path ->
  %{type: :regular, mode: mode, size: size} = File.stat!(path)
  true = Bitwise.band(mode, 0o111) != 0
  {path, %{"sha256" => hash.(path), "bytes" => size}}
end)
"/usr/bin/openssl" = System.find_executable("openssl")
"1.20.4" = System.version()
"29" = to_string(:erlang.system_info(:otp_release))
otp_path = Path.join([to_string(:code.root_dir()), "releases", "29", "OTP_VERSION"])
"29.1.1" = File.read!(otp_path) |> String.trim()
{mix, 0} = System.cmd("/usr/local/bin/mix", ["--version"], stderr_to_stdout: true)
true = String.contains?(mix, "Mix 1.20.4")
{openssl, 0} = System.cmd("/usr/bin/openssl", ["version", "-a"], stderr_to_stdout: true)
true = String.starts_with?(openssl, "OpenSSL 3.0.22 ")
{tar, 0} = System.cmd("/usr/bin/tar", ["--version"], stderr_to_stdout: true)
true = byte_size(tar) < 65536 and String.starts_with?(tar, "tar (GNU tar) 1.34")
{:ok, _} = Application.ensure_all_started(:ssl)
ca_path = "/etc/ssl/certs/ca-certificates.crt"
%{type: :regular, size: 224449} = File.stat!(ca_path)
"714d457d580922dbf1d0be8bd35ba236a842b50b0072ae791582a19adef772a5" = hash.(ca_path)
:ok = :public_key.cacerts_load(ca_path)
roots = :public_key.cacerts_get()
true = is_list(roots) and length(roots) > 0
root_hashes = Enum.map(roots, fn {:cert, der, _decoded} -> :crypto.hash(:sha256, der) |> Base.encode16(case: :lower) end) |> Enum.sort()
bundle_hashes = Enum.map(:public_key.pem_decode(File.read!(ca_path)), fn {:Certificate, der, :not_encrypted} -> :crypto.hash(:sha256, der) |> Base.encode16(case: :lower) end) |> Enum.sort()
true = root_hashes == bundle_hashes
libraries = Enum.map(:crypto.info_lib(), fn {name, number, version} -> %{"name" => to_string(name), "number" => number, "version" => to_string(version)} end)
[%{"name" => "OpenSSL", "number" => number, "version" => crypto_version}] = libraries
true = is_integer(number) and number > 0 and String.starts_with?(crypto_version, "OpenSSL 3.0.22 ")
ca = %{"path" => ca_path, "bytes" => 224449, "sha256" => hash.(ca_path), "load" => "explicit-selected-bundle", "loaded_count" => length(roots), "loaded_der_sha256" => root_hashes}
versions = %{"/usr/bin/tar" => tar}
emit.(%{"elixir" => System.version(), "otp_patch" => File.read!(otp_path) |> String.trim(), "mix" => mix, "openssl" => openssl, "crypto" => inspect(:crypto.info_lib()), "crypto_libraries" => libraries, "tools" => rows, "versions" => versions, "ca" => ca})
