# Load the vetted fixture provisioning helpers. Product modules and routes are stock.
alias MixerHosted.CustomerArtifacts.LocalUpload
alias MixerHosted.Identity.{KeyOwnerSupervisor, StartupFixture, TLSFixture}
alias MixerHosted.Releases.{RuntimeProvisioning, WriterRepo}
alias MixerHosted.Releases.ConfiguredReleaseReplayTest, as: Fixture
alias MixerHosted.{Repo, RuntimeConfig}
alias MixerHostedWeb.Endpoint
ExUnit.start(autorun: false)
{:ok, _} = Application.ensure_all_started(:ecto_sql)
{:ok, _} = Application.ensure_all_started(:postgrex)


source = "test/mixer_hosted/releases/configured_release_replay_test.exs"
fixture =
  File.read!(source)
  |> String.replace(~r/defp (provision!|provision_uploader!|enroll!|stage!|fixture_identity|publish_fixture!)\(/,
       "def \\1(")
  |> String.replace(~s|database: "postgres",|, ~s|database: System.fetch_env!("PGDATABASE"),\n      port: String.to_integer(System.fetch_env!("PGPORT")),|)
  |> String.replace(~s|               "postgres",|, ~s|               System.fetch_env!("PGDATABASE"),|)
Code.compile_string(fixture, source)

env = System.get_env()
config = RuntimeConfig.load!(env)
# Disposable PostgreSQL with SCRAM and IPv4 loopback only, using a private socket for admin.
config = %{config | repo: Keyword.merge(config.repo, port: String.to_integer(env["PGPORT"]), ssl: false)}
{target, delivery} = release = RuntimeProvisioning.load!(env, config)
work = env["D6_RUN"]
case env["D6_COMMAND"] do
  "provision" ->
    Fixture.provision!(target.target)
    Fixture.provision_uploader!(env["MIXER_LOCAL_ARTIFACT_UPLOAD_PASSWORD"])
  "load-prior" ->
    name = env["D6_PHASE"]
    dir = Path.join(env["D6_INPUTS"], name)
    signed = File.read!(Path.join(dir, "assignment.json"))
    assignment = Jason.decode!(signed)["assignment"]
    manifest = File.read!(Path.join(dir, "signed-manifest.json"))
    payload = Base.encode64(File.read!(Path.join(dir, "payload.wasm")))
    envelope = ~s({"signed_manifest":#{manifest},"payload":"#{payload}"})
    identity = Fixture.fixture_identity()
    Fixture.stage!(target, assignment["artifact_sha256"], envelope, identity, "d6-" <> name)
    Fixture.publish_fixture!(target.target,
      %{signed: signed, sequence: assignment["sequence"], digest: assignment["artifact_sha256"]},
      identity, "replay-owner")
  "serve" ->
    config = LocalUpload.configure!(env, config, release)
    writer = RuntimeProvisioning.writer_options!(env, config, release)

    if env["D6_ROOT_AUTH"] == "yes" do
      # Only root runs this branch. Use the existing loopback-only configured
      # verifier destination fixture, with the ordinary auth pipeline.
      {:ok, _} = Application.ensure_all_started(:jose)
      {:ok, tls} = TLSFixture.start_link()
      %{ca: ca, ip: ip, port: port} = GenServer.call(tls, :authority)
      key = JOSE.JWK.generate_key({:rsa, 2048})
      {_, public} = key |> JOSE.JWK.to_public() |> JOSE.JWK.to_map()
      jwk = Map.merge(public, %{"kid" => "d6", "alg" => "RS256", "use" => "sig"})
      TLSFixture.configure(tls, {:body, Jason.encode!(%{"keys" => [jwk]})})
      settings = StartupFixture.configuration(StartupFixture.envelope(), [ca])
      {:ok, _} = KeyOwnerSupervisor.start_fixture(settings.owner_options ++ [fixture: %{ip: ip, port: port}])
      now = System.system_time(:second)
      profile = StartupFixture.entry()["profile"]
      claims = %{"iss" => profile["issuer"], "aud" => profile["audience"],
        "client_id" => profile["client_id"], "sub" => "replay-subject", "jti" => "replay-token",
        "scope" => "mixer.artifact.upload mixer.release.publish mixer.artifact.read",
        "iat" => now - 1, "exp" => now + 480}
      {_, token} = key |> JOSE.JWS.sign(Jason.encode!(claims),
        %{"alg" => "RS256", "typ" => "at+jwt", "kid" => "d6"}) |> JOSE.JWS.compact()
      File.write!(Path.join(work, "operator.token"), token, [:exclusive])
    end

    for {key, value} <- [
      startup: {config, :disabled}, role: config.role, identity_startup: config.identity_startup,
      local_release_target: target, local_release_delivery: delivery
    ] ++ [
      {Repo, config.repo}, {Oban, config.oban}, {WriterRepo, writer},
      {Endpoint, Keyword.merge(Application.fetch_env!(:mixer_hosted, Endpoint), config.endpoint)}
    ], do: Application.put_env(:mixer_hosted, key, value)

    {:ok, _} = Application.ensure_all_started(:mixer_hosted)
    IO.puts("D6_ORIGIN_READY")
    Process.sleep(:infinity)
end
