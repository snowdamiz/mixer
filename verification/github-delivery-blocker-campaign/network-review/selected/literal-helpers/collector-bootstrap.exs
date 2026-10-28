
defmodule MixerIdentityNetworkCollector.Bootstrap do
  @cap 16_777_216
  def remaining(deadline) do
    left = deadline - System.monotonic_time(:millisecond)
    if left <= 0, do: raise("bootstrap artifact deadline")
    left
  end
  def line(socket, deadline, bytes \\ <<>>) do
    true = byte_size(bytes) < 8192
    {:ok, byte} = :ssl.recv(socket, 1, remaining(deadline))
    next = bytes <> byte
    if String.ends_with?(next, "\r\n"), do: next, else: line(socket, deadline, next)
  end
  def headers(socket, deadline, bytes, rows) do
    true = bytes < 65_536 and length(rows) < 128
    next = line(socket, deadline)
    true = bytes + byte_size(next) <= 65_536
    if next == "\r\n" do
      rows
    else
      [name, value] = String.split(String.trim_trailing(next, "\r\n"), ":", parts: 2)
      true = String.match?(name, ~r/\A[A-Za-z0-9-]+\z/)
      headers(socket, deadline, bytes + byte_size(next), [{String.downcase(name), String.trim(value)} | rows])
    end
  end
  def body(_socket, _io, 0, hash, _deadline), do: :crypto.hash_final(hash)
  def body(socket, io, left, hash, deadline) do
    count = min(left, 65_536)
    {:ok, bytes} = :ssl.recv(socket, count, remaining(deadline))
    ^count = byte_size(bytes)
    :ok = IO.binwrite(io, bytes)
    body(socket, io, left - count, :crypto.hash_update(hash, bytes), deadline)
  end
  def download(url, path, expected) do
    %URI{scheme: "https", host: "builds.hex.pm", port: 443, path: request_path, query: nil, userinfo: nil, fragment: nil} = URI.parse(url)
    true = String.starts_with?(request_path, "/installs/") and not String.contains?(request_path, ["\r", "\n"])
    deadline = System.monotonic_time(:millisecond) + 25_000
    options = [verify: :verify_peer, cacerts: :public_key.cacerts_get(), server_name_indication: ~c"builds.hex.pm", customize_hostname_check: [match_fun: :public_key.pkix_verify_hostname_match_fun(:https)], versions: [:"tlsv1.3", :"tlsv1.2"], active: false, mode: :binary, packet: :raw, send_timeout: 5000, send_timeout_close: true]
    {:ok, socket} = :ssl.connect(~c"builds.hex.pm", 443, options, min(10_000, remaining(deadline)))
    try do
      :ok = :ssl.send(socket, "GET " <> request_path <> " HTTP/1.1\r\nHost: builds.hex.pm\r\nAccept-Encoding: identity\r\nConnection: close\r\n\r\n")
      status = line(socket, deadline)
      true = String.starts_with?(status, ["HTTP/1.1 200 ", "HTTP/1.0 200 "])
      values = headers(socket, deadline, byte_size(status), [])
      [] = for {"transfer-encoding", value} <- values, do: value
      encoding = for {"content-encoding", value} <- values, do: String.downcase(value)
      true = encoding in [[], ["identity"]]
      [length_text] = for {"content-length", value} <- values, do: value
      true = String.match?(length_text, ~r/\A[0-9]{1,8}\z/)
      length = String.to_integer(length_text)
      true = length > 0 and length <= @cap
      {:ok, io} = File.open(path, [:write, :binary, :exclusive])
      actual = try do
        body(socket, io, length, :crypto.hash_init(:sha512), deadline) |> Base.encode16(case: :lower)
      after
        :ok = File.close(io)
      end
      ^expected = actual
      {:error, :closed} = :ssl.recv(socket, 1, remaining(deadline))
      remaining(deadline)
      %{"url" => url, "bytes" => length, "sha512" => actual, "status" => 200, "redirects" => 0, "tls_peer_and_hostname_verified" => true, "content_length_and_eof_exact" => true}
    after
      :ssl.close(socket, min(1000, max(1, deadline - System.monotonic_time(:millisecond))))
    end
  end
  def run do
    {:ok, _} = Application.ensure_all_started(:ssl)
    ca_path = "/etc/ssl/certs/ca-certificates.crt"
    %{type: :regular, size: 224449} = File.stat!(ca_path)
    "714d457d580922dbf1d0be8bd35ba236a842b50b0072ae791582a19adef772a5" = Base.encode16(:crypto.hash(:sha256, File.read!(ca_path)), case: :lower)
    :ok = :public_key.cacerts_load(ca_path)
    true = length(:public_key.cacerts_get()) > 0
    for path <- ["/workspace/home", "/workspace/tooling/mix", "/workspace/tooling/hex", "/workspace/cache", "/workspace/downloads", "/workspace/evidence"], do: File.mkdir_p!(path)
    [] = File.ls!("/workspace/tooling/mix")
    false = File.exists?("/workspace/tooling/rebar3")
    hex = download("https://builds.hex.pm/installs/1.20.0/hex-2.5.1-otp-29.ez", "/workspace/downloads/hex.ez", "6629f4b4bb2e040326151ebb853aad065e342c65ad3a0f2a2674dcf7164eb4328d6c929513d7230309ad75042024e72bef0e0a51ebff373b4173d2746b1772b7")
    rebar = download("https://builds.hex.pm/installs/1.18.4/rebar3-3.28.0-otp-29", "/workspace/downloads/rebar3", "b51946058fbe4aa823185bfe27204be59be439982ac3a3e1dbd9f8260b9af046fcfdfbd9066283c3fbba5a2a45dc3570550c12a9a548daf223b80cac222a6d0f")
    {installed, 0} = System.cmd("/usr/local/bin/mix", ["archive.install", "/workspace/downloads/hex.ez", "--sha512", "6629f4b4bb2e040326151ebb853aad065e342c65ad3a0f2a2674dcf7164eb4328d6c929513d7230309ad75042024e72bef0e0a51ebff373b4173d2746b1772b7", "--force"], stderr_to_stdout: true)
    true = byte_size(installed) < 1_048_576
    "/workspace/tooling/rebar3" = System.fetch_env!("MIX_REBAR3")
    File.rename!("/workspace/downloads/rebar3", "/workspace/tooling/rebar3")
    File.chmod!("/workspace/tooling/rebar3", 0o755)
    {hex_version, 0} = System.cmd("/usr/local/bin/elixir", ["-pa", "/workspace/tooling/mix/archives/hex-2.5.1/hex-2.5.1/ebin", "-e", ":ok = Application.load(:hex); IO.puts(Application.spec(:hex, :vsn))"], stderr_to_stdout: true)
    "2.5.1" = String.trim(hex_version)
    {rebar_version, 0} = System.cmd("/workspace/tooling/rebar3", ["--version"], stderr_to_stdout: true)
    true = byte_size(rebar_version) < 65_536 and String.contains?(rebar_version, "rebar 3.28.0")
    IO.puts("IDENTITY_JSON=" <> IO.iodata_to_binary(:json.encode(%{"hex" => hex, "rebar" => rebar, "hex_version" => String.trim(hex_version), "rebar_version" => rebar_version, "archive_install_output" => installed, "exact_rebar_path" => System.fetch_env!("MIX_REBAR3")})))
  end
end
MixerIdentityNetworkCollector.Bootstrap.run()
