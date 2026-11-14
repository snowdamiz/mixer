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

  def processor_config do
    foundation_env()
    |> Map.merge(%{
      "MIXER_HOSTED_ROLE" => "processor",
      "MIXER_PROCESSOR_PROFILE" => "builds_v1",
      "MIXER_DATABASE_USER" => "mixer_build_processor",
      "MIXER_DATABASE_POOL_SIZE" => "2"
    })
    |> MixerHosted.RuntimeConfig.load!()
  end

  # Owned loopback database and direct restricted login; no production TLS claim.
  def processor_runtime! do
    alias MixerHosted.Test.OrdinaryBrowserStartupFixture, as: Fixture
    alias MixerHosted.Test.OrdinaryBrowserStartupFixture.Database, as: F
    alias MixerHosted.BrowserAuth.StorageFixture.{Admin, Migration}
    import ExUnit.Assertions
    import ExUnit.Callbacks

    Fixture.refuse_names!([MixerHosted.Supervisor, MixerHosted.Repo, Oban, Admin, Migration])
    parent = System.fetch_env!("MIXER_BROWSER_CATALOG_FIXTURE_ROOT")
    suffix = Base.encode16(:crypto.strong_rand_bytes(6), case: :lower)
    database = "identity_processor_" <> suffix
    namespace = Path.join(parent, database)
    File.mkdir!(namespace)
    System.put_env("MIXER_BROWSER_CATALOG_FIXTURE_ROOT", namespace)

    # Registered first so restoration follows database teardown (reverse callback order).
    on_exit(fn ->
      System.put_env("MIXER_BROWSER_CATALOG_FIXTURE_ROOT", parent)
      assert System.fetch_env!("MIXER_BROWSER_CATALOG_FIXTURE_ROOT") == parent
      File.write!(Path.join(namespace, "parent-restored.json"), Jason.encode!(%{restored: true}))
    end)

    admin = F.connection!("browser_admin", "postgres")

    try do
      ensure_processor_fixture_role!(admin, "browser_admin", [
        true,
        true,
        false,
        true,
        false,
        false,
        false
      ])

      ensure_processor_fixture_role!(admin, "browser_schema_owner", [
        false,
        false,
        false,
        false,
        false,
        false,
        false
      ])

      ensure_processor_fixture_role!(admin, "mixer_customer_build_catalog_definer_v1", [
        false,
        false,
        false,
        false,
        false,
        false,
        false
      ])

      ensure_processor_fixture_role!(admin, "mixer_build_create", [
        true,
        false,
        false,
        false,
        false,
        false,
        false
      ])

      Postgrex.query!(admin, "CREATE DATABASE " <> database <> " OWNER browser_schema_owner", [])
    after
      GenServer.stop(admin)
    end

    on_exit(fn ->
      for name <- [MixerHosted.Supervisor, MixerHosted.Repo, Oban, Admin, Migration],
          do: assert(Process.whereis(name) == nil)

      conn = F.connection!("browser_admin", "postgres")

      try do
        assert [[0]] ==
                 Postgrex.query!(conn, "SELECT count(*) FROM pg_stat_activity WHERE datname=$1", [
                   database
                 ]).rows

        Postgrex.query!(conn, "DROP DATABASE " <> database, [])

        File.write!(
          Path.join(namespace, "database-dropped.json"),
          Jason.encode!(%{database: database, dropped: true})
        )
      after
        GenServer.stop(conn)
      end
    end)

    opts = [
      hostname: "127.0.0.1",
      port: F.port(),
      database: database,
      pool_size: 2,
      ssl: false,
      log: false
    ]

    start_supervised!({Admin, opts ++ [username: "browser_admin"]})

    start_supervised!(
      {Migration,
       opts ++
         [
           username: "browser_admin",
           after_connect: fn c -> Postgrex.query!(c, "SET ROLE browser_schema_owner", []) end
         ]}
    )

    MixerHosted.BrowserAuth.StorageFixture.install!(Migration)

    for {file, module, version} <- [
          {"20261025000000_add_build_journals.exs", MixerHosted.Repo.Migrations.AddBuildJournals,
           20_261_025_000_000},
          {"20261025000001_add_build_admission.exs",
           MixerHosted.Repo.Migrations.AddBuildAdmission, 20_261_025_000_001},
          {"20261025000002_add_build_aggregate_limits.exs",
           MixerHosted.Repo.Migrations.AddBuildAggregateLimits, 20_261_025_000_002}
        ] do
      unless Code.ensure_loaded?(module), do: Code.require_file("priv/repo/migrations/" <> file)
      assert :ok == Ecto.Migrator.up(Migration, version, module, log: false)
    end

    assert :ok == Ecto.Migrator.up(Migration, 1, R1026.ObanMigration, log: false)
    for sql <- MixerHosted.CustomerBuilds.CreateSchema.statements(), do: F.q!(Migration, sql)

    roles = [
      MixerHosted.Builds.ProcessorProfile.role(),
      MixerHosted.Builds.ProcessorProfile.locker()
    ]

    for role <- roles do
      ensure_processor_fixture_role!(Admin, role, [
        role == "mixer_build_processor",
        false,
        false,
        false,
        false,
        false,
        false
      ])
    end

    for sql <- MixerHosted.Builds.ProcessorProfile.statements(:builds_v1) do
      unless Enum.any?(roles, &String.starts_with?(sql, "CREATE ROLE " <> &1 <> " ")) do
        F.q!(Admin, String.replace(sql, ~s(:"processor_database"), ~s("#{database}")))
      end
    end

    settings = processor_config()

    repo =
      Keyword.merge(settings.repo,
        hostname: "127.0.0.1",
        port: F.port(),
        database: database,
        ssl: false,
        log: false
      )

    settings = %{settings | repo: repo}
    Application.put_env(:mixer_hosted, :role, settings.role)
    Application.put_env(:mixer_hosted, :identity_startup, settings.identity_startup)
    Application.put_env(:mixer_hosted, MixerHosted.Repo, repo)
    Application.put_env(:mixer_hosted, Oban, settings.oban)
    Application.put_env(:mixer_hosted, MixerHostedWeb.Endpoint, settings.endpoint)
    Application.put_env(:mixer_hosted, :startup, {settings, :disabled})

    on_exit(fn ->
      case Process.whereis(MixerHosted.Supervisor) do
        nil ->
          :ok

        root ->
          assert Application.stop(:mixer_hosted) == :ok
          refute Process.alive?(root)
      end
    end)

    settings
  end

  defp ensure_processor_fixture_role!(conn, role, expected) do
    sql =
      "SELECT rolcanlogin,rolsuper,rolbypassrls,rolinherit,rolcreatedb,rolcreaterole,rolreplication FROM pg_roles WHERE rolname=$1"

    query = fn statement, params ->
      if is_pid(conn),
        do: Postgrex.query!(conn, statement, params),
        else: Ecto.Adapters.SQL.query!(conn, statement, params, log: false)
    end

    case query.(sql, [role]).rows do
      [] ->
        [login | _] = expected
        mode = if login, do: "LOGIN", else: "NOLOGIN"

        query.(
          "CREATE ROLE " <>
            role <>
            " " <>
            mode <> " NOSUPERUSER NOBYPASSRLS NOINHERIT NOCREATEDB NOCREATEROLE NOREPLICATION",
          []
        )

        ^expected = query.(sql, [role]).rows |> hd()

      [^expected] ->
        :ok
    end
  end

  def app_settings(identity) do
    settings = MixerHosted.RuntimeConfig.load!(foundation_env())
    Application.put_env(:mixer_hosted, :role, settings.role)
    Application.put_env(:mixer_hosted, :identity_startup, identity)

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

    hosted = %{
      settings
      | identity_startup: identity,
        endpoint: endpoint,
        repo: Application.fetch_env!(:mixer_hosted, MixerHosted.Repo)
    }

    Application.put_env(:mixer_hosted, :startup, {hosted, :disabled})
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
