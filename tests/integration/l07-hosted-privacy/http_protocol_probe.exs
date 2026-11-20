[mode] = System.argv()
{:ok, _} = Application.ensure_all_started(:phoenix)
{:ok, _} = Application.ensure_all_started(:bandit)
endpoint = MixerHostedWeb.Endpoint
config =
  MixerHosted.RuntimeConfig.load!(%{
    "MIXER_HOSTED_ROLE" => "api",
    "MIXER_DATABASE_HOST" => "db.fixture.example",
    "MIXER_DATABASE_NAME" => "mixer_fixture",
    "MIXER_DATABASE_USER" => "mixer_fixture",
    "MIXER_DATABASE_PASSWORD" => "synthetic-database-secret",
    "MIXER_SECRET_KEY_BASE" => String.duplicate("fixture-", 8)
  })
settings = put_in(config.endpoint, [:http, :port], 0)
Application.put_env(:mixer_hosted, endpoint,
  Keyword.merge(Application.fetch_env!(:mixer_hosted, endpoint), settings))
{:ok, server} = endpoint.start_link([])
{:ok, {{127, 0, 0, 1}, port}} = endpoint.server_info(:http)
url = "http://127.0.0.1:#{port}/health/live"
try do
  request = fn protocol ->
    System.cmd("/usr/bin/curl", [protocol, "--noproxy", "*", "--silent",
      "--max-time", "4", "--output", "/dev/null", "--write-out",
      "%{http_version} %{http_code}", url], stderr_to_stdout: true)
  end
  {"1.1 200", 0} = transport_v1 = request.("--http1.1")
  IO.inspect(transport_v1, label: "Ordinary HTTP/1.1 health")
  transport_v2 = request.("--http2-prior-knowledge")
  IO.inspect(transport_v2, label: "Ordinary HTTP/2 health")
  case {mode, transport_v2} do
    {"before", {"2 200", 0}} -> :ok
    {"after", {response, code}} when code != 0 ->
      false = String.starts_with?(response, "2 ")
    other -> raise "unexpected protocol outcome #{inspect(other)}"
  end
after
  :ok = Supervisor.stop(server)
  false = Process.alive?(server)
  {:ok, listener} = :gen_tcp.listen(port, ip: {127, 0, 0, 1}, reuseaddr: true)
  :ok = :gen_tcp.close(listener)
  IO.puts("Owned endpoint shut down and port rebound")
end
