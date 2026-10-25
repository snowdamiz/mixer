defmodule MixerHosted.Identity.StartupFixture do
  @moduledoc false
  alias MixerHosted.Identity.StartupConfig

  def standard_roots do
    Enum.map(:public_key.cacerts_get(), fn
      {:cert, der, _} -> der
      der -> der
    end)
  end

  def envelope do
    %{
      "version" => 1,
      "generation" => 1,
      "binding" => "startup-fixture",
      "profiles" => [entry()],
      "resolvers" => ["127.0.0.1"]
    }
  end

  def entry do
    %{
      "profile" => %{
        "profile_id" => "startup-fixture",
        "profile_version" => 1,
        "issuer" => "https://issuer.fixture.invalid/oauth",
        "audience" => "mixer-api",
        "client_id" => "reviewed-client",
        "identity_class" => "human",
        "enabled" => true
      },
      "jwks_endpoint" => %{"host" => "jwks.fixture.invalid", "port" => 443, "path" => "/keys"},
      "transport" => "hosted_https"
    }
  end

  def configuration(object, roots),
    do:
      StartupConfig.load!(
        %{
          "MIXER_IDENTITY_MODE" => "configured",
          "MIXER_IDENTITY_CONFIG" => Jason.encode!(object)
        },
        :api,
        roots
      )

  def foundation_env do
    %{
      "MIXER_HOSTED_ROLE" => "api",
      "MIXER_DATABASE_HOST" => "db.example.test",
      "MIXER_DATABASE_NAME" => "mixer_foundation_test",
      "MIXER_DATABASE_USER" => "mixer_fixture",
      "MIXER_DATABASE_PASSWORD" => "synthetic",
      "MIXER_SECRET_KEY_BASE" => String.duplicate("synthetic-", 8)
    }
  end

  def app_settings(identity) do
    settings = MixerHosted.RuntimeConfig.load!(foundation_env())
    Application.put_env(:mixer_hosted, :role, settings.role)
    Application.put_env(:mixer_hosted, :identity_startup, identity)
    Application.put_env(:mixer_hosted, :build_worker_startup, settings.build_worker_startup)
    Application.put_env(:mixer_hosted, :build_dispatch, settings.build_dispatch)

    Application.put_env(:mixer_hosted, MixerHosted.Repo,
      hostname: "127.0.0.1",
      port: String.to_integer(System.fetch_env!("MIXER_TEST_DATABASE_PORT")),
      database: "mixer_startup_test",
      username: "mixer_fixture",
      pool_size: 2,
      ssl: false
    )

    Application.put_env(:mixer_hosted, Oban, settings.oban)

    endpoint =
      Application.get_env(:mixer_hosted, MixerHostedWeb.Endpoint)
      |> Keyword.merge(settings.endpoint)
      |> Keyword.put(:http, ip: {127, 0, 0, 1}, port: 0)

    Application.put_env(:mixer_hosted, MixerHostedWeb.Endpoint, endpoint)
    :ok
  end

  def prepare_database do
    app_settings(StartupConfig.load!(%{}, :api, []))

    {:ok, repo} =
      MixerHosted.Repo.start_link(Application.fetch_env!(:mixer_hosted, MixerHosted.Repo))

    path = Application.app_dir(:mixer_hosted, "priv/repo/migrations")
    Ecto.Migrator.run(MixerHosted.Repo, path, :up, all: true)
    Supervisor.stop(repo)
  end

  def token(key) do
    now = System.system_time(:second)

    claims = %{
      "iss" => entry()["profile"]["issuer"],
      "aud" => "mixer-api",
      "sub" => "synthetic-startup-subject",
      "client_id" => "reviewed-client",
      "iat" => now - 1,
      "exp" => now + 120,
      "jti" => "synthetic-startup-token"
    }

    JOSE.JWS.sign(key, Jason.encode!(claims), %{
      "alg" => "RS256",
      "typ" => "at+jwt",
      "kid" => "startup-key"
    })
    |> JOSE.JWS.compact()
    |> elem(1)
  end

  def evidence(name, value) do
    case System.get_env("MIXER_TEST_IDENTITY_EVIDENCE") do
      nil -> :ok
      dir -> File.write!(Path.join(dir, name), Jason.encode!(value, pretty: true))
    end
  end
end

defmodule MixerHosted.Identity.StartupDNSFixture do
  @moduledoc false
  use GenServer
  def start_link(_), do: GenServer.start_link(__MODULE__, [])

  def init(_) do
    {:ok, socket} = :gen_udp.open(53, [:binary, ip: {127, 0, 0, 1}, active: true])
    {:ok, %{socket: socket, queries: []}}
  end

  def handle_call(:queries, _, s), do: {:reply, s.queries, s}

  def handle_info({:udp, socket, ip, port, raw}, s) do
    {:ok, message} = :inet_dns.decode(raw)
    [query] = :inet_dns.msg(message, :qdlist)
    name = :inet_dns.dns_query(query, :domain)
    type = :inet_dns.dns_query(query, :type)
    header = :inet_dns.msg(message, :header)
    header = :inet_dns.make_header(header, qr: true, aa: false, ra: true)

    answers =
      if type == :a,
        do: [:inet_dns.make_rr(domain: name, type: :a, class: :in, ttl: 120, data: {8, 8, 8, 8})],
        else: []

    reply = :inet_dns.make_msg(message, header: header, anlist: answers) |> :inet_dns.encode()
    :ok = :gen_udp.send(socket, ip, port, reply)
    {:noreply, %{s | queries: [{name, type} | s.queries]}}
  end

  def terminate(_, s), do: :gen_udp.close(s.socket)
end
