defmodule MixerHosted.BrowserAuth.StorageFixture.Admin do
  use Ecto.Repo, otp_app: :browser_storage_fixture, adapter: Ecto.Adapters.Postgres
end

defmodule MixerHosted.BrowserAuth.StorageFixture.Migration do
  use Ecto.Repo, otp_app: :browser_storage_fixture, adapter: Ecto.Adapters.Postgres
end

defmodule MixerHosted.BrowserAuth.StorageFixture.OperatorMigration do
  use Ecto.Repo, otp_app: :browser_storage_fixture, adapter: Ecto.Adapters.Postgres
end

defmodule MixerHosted.BrowserAuth.StorageFixture do
  alias MixerHosted.BrowserAuth.StorageSchema
  alias MixerHosted.BrowserAuth.StorageFixture.Migration

  def install!(repo \\ Migration) do
    for {module, file} <- [
          {MixerHosted.Repo.Migrations.AddCustomerAuthorization,
           "20261025000003_add_customer_authorization.exs"},
          {MixerHosted.Repo.Migrations.AddAuthorizationStateRevisions,
           "20261025000004_add_authorization_state_revisions.exs"},
          {MixerHosted.Repo.Migrations.AddCustomerWorkspaceDiscovery,
           "20261025000006_add_customer_workspace_discovery.exs"},
          {MixerHosted.Repo.Migrations.AddBrowserSessions,
           "20261025000007_add_browser_sessions.exs"}
        ] do
      unless Code.ensure_loaded?(module),
        do: Code.require_file(Path.expand("../../../priv/repo/migrations/" <> file, __DIR__))

      version = String.slice(file, 0, 14) |> String.to_integer()
      :ok = Ecto.Migrator.up(repo, version, module, log: false)
    end
  end

  def provision! do
    conn = connection!("browser_admin")

    try do
      Enum.each(
        StorageSchema.provisioning_statements("browser_writer", "browser_lifecycle"),
        &Postgrex.query!(conn, &1, [])
      )
    after
      GenServer.stop(conn)
    end
  end

  def q!(repo, sql, params \\ []), do: Ecto.Adapters.SQL.query!(repo, sql, params, log: false)
  def now, do: System.system_time(:second)
  def random(n \\ 32), do: :crypto.strong_rand_bytes(n)
  def token, do: Base.url_encode64(random(), padding: false)
  def request, do: Base.encode16(random(16), case: :lower)
  def cipher, do: {"fixture-v1", random(12), random(16), random(48)}

  def connection!(role \\ "browser_lifecycle") do
    {:ok, conn} =
      Postgrex.start_link(
        hostname: "127.0.0.1",
        port: port(),
        username: role,
        database: "browser_storage",
        ssl: false,
        backoff_type: :stop
      )

    Process.unlink(conn)
    Postgrex.query!(conn, "SET statement_timeout='5s'", [])
    Postgrex.query!(conn, "SET lock_timeout='500ms'", [])
    Postgrex.query!(conn, "SET idle_in_transaction_session_timeout='5s'", [])
    conn
  end

  def port, do: String.to_integer(System.fetch_env!("MIXER_BROWSER_STORAGE_PORT"))

  def call(conn, name, args) do
    {sql, values} = query(name, args)

    case Postgrex.query(conn, sql, values, timeout: 5_000, queue: false) do
      {:ok, %{rows: [[value]]}} -> {:ok, value}
      {:error, error} -> {:error, error.postgres.code}
    end
  end

  # Composite values use explicit ROW casts with bound primitive parameters.
  # The database driver never parses provider/browser text into SQL.
  def query(name, args) do
    {expressions, values, _} =
      Enum.reduce(args, {[], [], 1}, fn arg, {expr, values, n} ->
        {cast, primitive} =
          case arg do
            {:cipher, {key, iv, tag, ciphertext}} ->
              {"ROW($#{n},$#{n + 1},$#{n + 2},$#{n + 3})::public.mixer_browser_cipher",
               [key, iv, tag, ciphertext]}

            {:attempt, a} ->
              {key, iv, tag, ciphertext} = a.cipher

              {"ROW($#{n},$#{n + 1},$#{n + 2},$#{n + 3},$#{n + 4},$#{n + 5},$#{n + 6},$#{n + 7},ROW($#{n + 8},$#{n + 9},$#{n + 10},$#{n + 11})::public.mixer_browser_cipher)::public.mixer_browser_attempt",
               [
                 a.state,
                 a.nonce,
                 a.profile,
                 1,
                 a.issuer,
                 a.client,
                 a.redirect,
                 a.expires,
                 key,
                 iv,
                 tag,
                 ciphertext
               ]}

            {:verified, i} ->
              {"ROW($#{n},$#{n + 1},$#{n + 2},$#{n + 3},$#{n + 4},$#{n + 5},$#{n + 6},$#{n + 7},$#{n + 8},$#{n + 9},$#{n + 10},$#{n + 11})::public.mixer_browser_verified",
               [
                 i.profile,
                 1,
                 i.issuer,
                 i.subject,
                 i.client,
                 i.jti,
                 i.iat,
                 i.exp,
                 i.scopes,
                 i.profile_revision,
                 i.binding_revision,
                 i.principal_revision
               ]}

            primitive ->
              {"$#{n}", [primitive]}
          end

        {expr ++ [cast], values ++ primitive, n + length(primitive)}
      end)

    {"SELECT public.mixer_browser_#{name}(#{Enum.join(expressions, ",")})", values}
  end

  def bootstrap(conn, deadline \\ now() + 250) do
    cookie = random()
    config = random()
    csrf = random()
    id = random(16)

    args = [
      id,
      cookie,
      token(),
      csrf,
      config,
      "humans",
      1,
      deadline,
      {:cipher, cipher()},
      request()
    ]

    {:ok, snapshot} = call(conn, :bootstrap, args)
    %{id: id, cookie: cookie, config: config, csrf: csrf, revision: 1, snapshot: snapshot}
  end

  def begin_login(conn, b, expires \\ now() + 150) do
    a = %{
      state: random(),
      nonce: random(),
      profile: "humans",
      issuer: "https://issuer.fixture",
      client: "console",
      redirect: "https://console.fixture/auth/callback",
      expires: expires,
      cipher: cipher()
    }

    {:ok, snap} =
      call(conn, :begin, [
        b.cookie,
        b.csrf,
        b.config,
        b.revision,
        {:attempt, a},
        {:cipher, cipher()},
        request()
      ])

    {%{b | revision: b.revision + 1, snapshot: snap}, a}
  end

  def claim(conn, b, a, deadline \\ now() + 55) do
    claim = random()

    {:ok, snapshot} =
      call(conn, :claim, [b.cookie, a.state, b.config, b.revision, claim, deadline, request()])

    {claim, snapshot}
  end

  def identity(jti \\ token()) do
    %{
      profile: "humans",
      issuer: "https://issuer.fixture",
      subject: "subject-1",
      client: "console",
      jti: jti,
      iat: now() - 5,
      exp: now() + 600,
      scopes: ["mixer.workspace.read"],
      profile_revision: 1,
      binding_revision: 1,
      principal_revision: 1
    }
  end

  def activate(conn, b, a, claim, i \\ identity()) do
    new_cookie = random()
    new_csrf = random()
    generation = token()
    family = "browser_" <> token()

    args = [
      b.cookie,
      a.state,
      b.config,
      claim,
      b.revision,
      {:verified, i},
      new_cookie,
      new_csrf,
      generation,
      family,
      now() + 500,
      {:cipher, cipher()},
      request()
    ]

    {call(conn, :activate, args),
     %{b | cookie: new_cookie, csrf: new_csrf, revision: b.revision + 1}, family, i, args}
  end
end
