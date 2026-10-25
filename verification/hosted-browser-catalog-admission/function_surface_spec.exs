Code.require_file("hosted/test/mixer_hosted/browser_auth/storage_fixture.exs")

defmodule MixerHosted.BrowserAuth.FunctionSurfaceFixture.Repo do
  use Ecto.Repo, otp_app: :browser_function_surface, adapter: Ecto.Adapters.Postgres
end

defmodule MixerHosted.BrowserAuth.FunctionSurfaceSpec do
  use ExUnit.Case, async: false
  alias MixerHosted.BrowserAuth.{Catalog, CatalogManifest, StorageSchema}
  alias MixerHosted.BrowserAuth.FunctionSurfaceFixture.Repo
  alias MixerHosted.BrowserAuth.StorageFixture, as: Fixture
  alias MixerHosted.BrowserAuth.StorageFixture.{Admin, Migration}

  @roles %{
    lifecycle_login: "browser_lifecycle",
    writer: "browser_writer",
    relation_owner: "browser_schema_owner",
    ordinary_runtime_login: "browser_ordinary"
  }
  @load "public.mixer_browser_load(bytea,bytea)"
  @cipher "public.mixer_browser_cipher_valid(public.mixer_browser_cipher)"

  setup_all do
    Application.ensure_all_started(:ecto_sql)
    Application.ensure_all_started(:postgrex)
    Application.ensure_all_started(:jason)

    settings = [
      hostname: "127.0.0.1",
      port: Fixture.port(),
      database: "browser_storage",
      pool_size: 1,
      log: false
    ]

    start_supervised!({Admin, settings ++ [username: "browser_admin"]})

    start_supervised!(
      {Migration,
       Keyword.put(settings, :pool_size, 2) ++
         [
           username: "browser_admin",
           after_connect: fn conn ->
             Postgrex.query!(conn, "SET ROLE browser_schema_owner", [])
           end
         ]}
    )

    Fixture.install!()
    Fixture.provision!()

    start_supervised!(
      {Repo,
       settings ++
         [
           username: "browser_lifecycle",
           after_connect: fn conn ->
             for sql <- [
                   "SET search_path=pg_catalog",
                   "SET statement_timeout='5s'",
                   "SET lock_timeout='500ms'",
                   "SET idle_in_transaction_session_timeout='5s'",
                   "SET jit=off",
                   "SET bytea_output=hex"
                 ],
                 do: Postgrex.query!(conn, sql, [])
           end
         ]}
    )

    # Fixture boot may wait for its initial socket. Product queries below and
    # Catalog itself always use queue:false; migration setup is not admission.
    Ecto.Adapters.SQL.query!(Repo, "SELECT 1", [], log: false, timeout: 5_000)

    :ok
  end

  test "accepted capability surface passes repeatedly in separate current transactions" do
    assert check!() == :function_surface_verified
    assert check!() == :function_surface_verified
    assert map_size(CatalogManifest.functions()) == 18
    assert map_size(CatalogManifest.composites()) == 3
    assert not function_exported?(Catalog, :admit!, 0)
  end

  test "outside transaction fails with redacted error" do
    error =
      assert_raise Catalog.Unavailable, fn ->
        Catalog.check_function_surface!(Repo, @roles, deadline())
      end

    assert Exception.message(error) == "browser catalog function surface unavailable"
    assert Map.from_struct(error) == %{__exception__: true, message: Exception.message(error)}
  end

  test "closed expected role shape and names fail before any catalog trust" do
    for roles <- [
          Map.put(@roles, :extra, "browser_admin"),
          Map.delete(@roles, :writer),
          %{@roles | writer: "browser_lifecycle"},
          %{@roles | writer: "public"},
          %{@roles | writer: "pg_read_all_data"},
          %{@roles | writer: "bad; role"},
          %{@roles | writer: nil},
          %{@roles | lifecycle_login: "browser_ordinary"}
        ] do
      rejected!(fn -> Catalog.check_function_surface!(Repo, roles, deadline()) end)
    end
  end

  test "expired, noninteger and newly expanded deadlines fail closed" do
    for value <- [
          System.monotonic_time(:millisecond) - 1,
          System.monotonic_time(:millisecond) + 60_000,
          nil,
          "5000"
        ] do
      rejected!(fn -> Catalog.check_function_surface!(Repo, @roles, value) end)
    end
  end

  test "a transaction cannot change identity using SET ROLE" do
    {:ok, value} =
      Admin.transaction(fn ->
        q!(Admin, "SET LOCAL ROLE browser_lifecycle")

        assert_raise Catalog.Unavailable, fn ->
          Catalog.check_function_surface!(Admin, @roles, deadline())
        end

        :rejected
      end)

    assert value == :rejected
  end

  test "session policy must retain every fixed setting and read committed" do
    for setting <- [
          "SET LOCAL statement_timeout='4s'",
          "SET LOCAL lock_timeout='1s'",
          "SET LOCAL idle_in_transaction_session_timeout='10s'",
          "SET LOCAL jit=on",
          "SET LOCAL search_path=public,pg_catalog",
          "SET LOCAL bytea_output=escape",
          "SET TRANSACTION ISOLATION LEVEL REPEATABLE READ"
        ] do
      rejected!(fn ->
        q!(Repo, setting)
        Catalog.check_function_surface!(Repo, @roles, deadline())
      end)
    end

    assert check!() == :function_surface_verified
  end

  test "observed source drift cannot authorize itself after successful admission" do
    assert check!() == :function_surface_verified
    sql = source_sql("mixer_browser_load")

    mutate!(String.replace(sql, "SELECT * INTO b", "SELECT  * INTO b"), sql, fn ->
      # A byte-only source change is intentionally rejected too; no live catalog
      # body can become the expected answer, before or after an earlier check.
      rejected!()
    end)
  end

  test "oversized stored source fails without being returned over the catalog wire" do
    sql = source_sql("mixer_browser_load")

    oversized =
      String.replace(sql, "BEGIN\n", "BEGIN\n-- " <> String.duplicate("x", 70_000) <> "\n",
        global: false
      )

    mutate!(oversized, sql, &rejected!/0)
  end

  test "catalog row cap fails closed rather than accepting a truncated role graph" do
    q!(Admin, """
    DO $cap$ BEGIN FOR i IN 1..4096 LOOP
      EXECUTE pg_catalog.format('CREATE ROLE surface_cap_%s NOLOGIN NOINHERIT',i);
    END LOOP; END $cap$
    """)

    try do
      rejected!()
    after
      q!(Admin, """
      DO $cap$ BEGIN FOR i IN 1..4096 LOOP
        EXECUTE pg_catalog.format('DROP ROLE surface_cap_%s',i);
      END LOOP; END $cap$
      """)
    end

    assert check!() == :function_surface_verified
  end

  test "blocked catalog query consumes the original deadline without a new five second budget" do
    parent = self()

    holder =
      Task.async(fn ->
        Admin.transaction(fn ->
          q!(Admin, "LOCK TABLE pg_catalog.pg_proc IN ACCESS EXCLUSIVE MODE")
          send(parent, :catalog_locked)

          receive do
            :release_catalog -> :released
          after
            2_000 -> raise "fixture catalog lock release missing"
          end
        end)
      end)

    try do
      assert_receive :catalog_locked, 1_000
      started = System.monotonic_time(:millisecond)

      assert {:error, :rollback} =
               Repo.transaction(
                 fn ->
                   assert_raise Catalog.Unavailable, fn ->
                     Catalog.check_function_surface!(Repo, @roles, started + 120)
                   end

                   :unreachable_commit
                 end,
                 timeout: 5_000,
                 queue: false
               )

      assert System.monotonic_time(:millisecond) - started < 1_000
    after
      send(holder.pid, :release_catalog)
      assert {:ok, :released} = Task.await(holder, 3_000)
    end

    # A driver timeout can replace a socket. Only fixture re-connect readiness
    # may wait; every subsequent product operation remains queue:false.
    Ecto.Adapters.SQL.query!(Repo, "SELECT 1", [], log: false, timeout: 5_000)
    assert check!() == :function_surface_verified
  end

  test "dropped or extra function settings and security flags are rejected" do
    for {up, down} <- [
          {"RESET lock_timeout", "SET lock_timeout='500ms'"},
          {"SET work_mem='16MB'", "RESET work_mem"},
          {"SET search_path=public,pg_catalog", "SET search_path=pg_catalog"},
          {"SECURITY INVOKER", "SECURITY DEFINER"},
          {"STABLE", "VOLATILE"},
          {"STRICT", "CALLED ON NULL INPUT"},
          {"PARALLEL SAFE", "PARALLEL UNSAFE"},
          {"LEAKPROOF", "NOT LEAKPROOF"}
        ] do
      mutate!("ALTER FUNCTION #{@load} #{up}", "ALTER FUNCTION #{@load} #{down}", &rejected!/0)
    end
  end

  test "every one of the eighteen functions is required with no overload" do
    for {name, expected} <- CatalogManifest.functions() do
      signature = "public.#{name}(#{expected.signature})"

      mutate!(
        "ALTER FUNCTION #{signature} RENAME TO surface_renamed",
        "ALTER FUNCTION public.surface_renamed(#{expected.signature}) RENAME TO #{name}",
        &rejected!/0
      )
    end

    mutate!(
      "CREATE FUNCTION public.mixer_browser_load(pg_catalog.text) RETURNS pg_catalog.bool LANGUAGE sql AS 'SELECT true'",
      "DROP FUNCTION public.mixer_browser_load(pg_catalog.text)",
      &rejected!/0
    )
  end

  test "unreviewed executable helper in another schema is rejected" do
    q!(Admin, "CREATE SCHEMA surface_alternate")

    try do
      mutate!(
        "CREATE FUNCTION surface_alternate.mixer_browser_extra() RETURNS pg_catalog.bool LANGUAGE sql AS 'SELECT true'",
        "DROP FUNCTION surface_alternate.mixer_browser_extra()",
        &rejected!/0
      )
    after
      q!(Admin, "DROP SCHEMA surface_alternate")
    end
  end

  test "return type and language drift fail with identical argument types" do
    sql = source_sql("mixer_browser_load")
    # No trigger depends on load, so a transactionally replaced object can prove
    # signature/result/language checks without disrupting dependent fixtures.
    q!(Admin, "DROP FUNCTION #{@load}")

    try do
      q!(
        Admin,
        "CREATE FUNCTION public.mixer_browser_load(bytea,bytea) RETURNS boolean LANGUAGE sql SECURITY DEFINER AS 'SELECT true'"
      )

      q!(Admin, "ALTER FUNCTION #{@load} OWNER TO browser_writer")
      rejected!()
    after
      q!(Admin, "DROP FUNCTION #{@load}")
      q!(Admin, sql)
      q!(Admin, "ALTER FUNCTION #{@load} OWNER TO browser_writer")
      q!(Admin, "REVOKE ALL ON FUNCTION #{@load} FROM PUBLIC")
      q!(Admin, "GRANT EXECUTE ON FUNCTION #{@load} TO browser_lifecycle")
    end

    assert check!() == :function_surface_verified
  end

  test "function owner must be exact trusted restricted writer" do
    mutate!(
      "ALTER FUNCTION #{@load} OWNER TO browser_schema_owner",
      "ALTER FUNCTION #{@load} OWNER TO browser_writer",
      &rejected!/0
    )
  end

  test "function grants include PUBLIC, ordinary, internal helper, missing and grant option drift" do
    for {up, down} <- [
          {"GRANT EXECUTE ON FUNCTION #{@load} TO PUBLIC",
           "REVOKE EXECUTE ON FUNCTION #{@load} FROM PUBLIC"},
          {"GRANT EXECUTE ON FUNCTION #{@load} TO browser_ordinary",
           "REVOKE EXECUTE ON FUNCTION #{@load} FROM browser_ordinary"},
          {"GRANT EXECUTE ON FUNCTION #{@cipher} TO browser_lifecycle",
           "REVOKE EXECUTE ON FUNCTION #{@cipher} FROM browser_lifecycle"},
          {"REVOKE EXECUTE ON FUNCTION #{@load} FROM browser_lifecycle",
           "GRANT EXECUTE ON FUNCTION #{@load} TO browser_lifecycle"},
          {"GRANT EXECUTE ON FUNCTION #{@load} TO browser_lifecycle WITH GRANT OPTION",
           "REVOKE GRANT OPTION FOR EXECUTE ON FUNCTION #{@load} FROM browser_lifecycle"},
          {"GRANT EXECUTE ON FUNCTION #{@load} TO surface_neighbor",
           "REVOKE EXECUTE ON FUNCTION #{@load} FROM surface_neighbor"}
        ],
        do: mutate!(up, down, &rejected!/0)
  end

  test "exact ordered composite fields and types cannot drift" do
    for {up, down} <- [
          {"ALTER ATTRIBUTE key_id TYPE varchar", "ALTER ATTRIBUTE key_id TYPE text"},
          {"RENAME ATTRIBUTE key_id TO renamed_key", "RENAME ATTRIBUTE renamed_key TO key_id"}
        ] do
      mutate!(
        "ALTER TYPE public.mixer_browser_cipher #{up}",
        "ALTER TYPE public.mixer_browser_cipher #{down}",
        &rejected!/0
      )
    end
  end

  test "composite type ACL cannot widen or lose required usage" do
    for {up, down} <- [
          {"GRANT USAGE ON TYPE public.mixer_browser_cipher TO PUBLIC",
           "REVOKE USAGE ON TYPE public.mixer_browser_cipher FROM PUBLIC"},
          {"GRANT USAGE ON TYPE public.mixer_browser_attempt TO browser_ordinary",
           "REVOKE USAGE ON TYPE public.mixer_browser_attempt FROM browser_ordinary"},
          {"GRANT USAGE ON TYPE public.mixer_browser_verified TO browser_lifecycle WITH GRANT OPTION",
           "REVOKE GRANT OPTION FOR USAGE ON TYPE public.mixer_browser_verified FROM browser_lifecycle"},
          {"REVOKE USAGE ON TYPE public.mixer_browser_cipher FROM browser_lifecycle",
           "GRANT USAGE ON TYPE public.mixer_browser_cipher TO browser_lifecycle"}
        ],
        do: mutate!(up, down, &rejected!/0)
  end

  test "restricted role flags and any lifecycle or writer membership edge fail" do
    for {up, down} <- [
          {"ALTER ROLE browser_writer LOGIN", "ALTER ROLE browser_writer NOLOGIN"},
          {"ALTER ROLE browser_lifecycle INHERIT", "ALTER ROLE browser_lifecycle NOINHERIT"},
          {"ALTER ROLE browser_lifecycle BYPASSRLS", "ALTER ROLE browser_lifecycle NOBYPASSRLS"},
          {"ALTER ROLE browser_lifecycle CREATEROLE",
           "ALTER ROLE browser_lifecycle NOCREATEROLE"},
          {"ALTER ROLE browser_schema_owner LOGIN", "ALTER ROLE browser_schema_owner NOLOGIN"},
          {"GRANT browser_writer TO surface_neighbor",
           "REVOKE browser_writer FROM surface_neighbor"},
          {"GRANT surface_neighbor TO browser_lifecycle",
           "REVOKE surface_neighbor FROM browser_lifecycle"},
          {"GRANT browser_schema_owner TO browser_ordinary",
           "REVOKE browser_schema_owner FROM browser_ordinary"}
        ],
        do: mutate!(up, down, &rejected!/0)
  end

  test "ordinary transitive privileged or ownership routes fail despite NOINHERIT" do
    q!(Admin, "GRANT surface_neighbor TO browser_ordinary")

    try do
      mutate!(
        "GRANT pg_read_all_data TO surface_neighbor",
        "REVOKE pg_read_all_data FROM surface_neighbor",
        &rejected!/0
      )

      mutate!(
        "ALTER SCHEMA public OWNER TO surface_neighbor",
        "ALTER SCHEMA public OWNER TO pg_database_owner",
        &rejected!/0
      )
    after
      q!(Admin, "REVOKE surface_neighbor FROM browser_ordinary")
    end
  end

  test "PUBLIC or direct schema CREATE and database CREATE paths fail" do
    for role <- ["PUBLIC", "browser_lifecycle", "browser_writer", "browser_ordinary"] do
      mutate!(
        "GRANT CREATE ON SCHEMA public TO #{role}",
        "REVOKE CREATE ON SCHEMA public FROM #{role}",
        &rejected!/0
      )
    end

    mutate!(
      "GRANT CREATE ON DATABASE browser_storage TO browser_lifecycle",
      "REVOKE CREATE ON DATABASE browser_storage FROM browser_lifecycle",
      &rejected!/0
    )
  end

  test "function surface retains effective public schema usage" do
    q!(Admin, "REVOKE USAGE ON SCHEMA public FROM PUBLIC")

    try do
      mutate!(
        "REVOKE USAGE ON SCHEMA public FROM browser_lifecycle",
        "GRANT USAGE ON SCHEMA public TO browser_lifecycle",
        &rejected!/0
      )
    after
      q!(Admin, "GRANT USAGE ON SCHEMA public TO PUBLIC")
    end
  end

  test "direct lifecycle and ordinary-browser table and column grants fail" do
    for {relation, role, privilege} <- [
          {"mixer_browser_sessions", "browser_lifecycle", "SELECT"},
          {"mixer_authz_profiles", "browser_lifecycle", "SELECT(id)"},
          {"mixer_browser_sessions", "browser_lifecycle", "UPDATE(status)"},
          {"mixer_browser_sessions", "browser_ordinary", "SELECT(id)"},
          {"mixer_authz_profiles", "PUBLIC", "SELECT(id)"}
        ] do
      mutate!(
        "GRANT #{privilege} ON public.#{relation} TO #{role}",
        "REVOKE #{privilege} ON public.#{relation} FROM #{role}",
        &rejected!/0
      )
    end
  end

  test "ordinary SET ROLE capability cannot reach browser table or column grants" do
    q!(Admin, "GRANT surface_neighbor TO browser_ordinary")

    try do
      for privilege <- ["SELECT", "SELECT(id)"] do
        mutate!(
          "GRANT #{privilege} ON public.mixer_browser_sessions TO surface_neighbor",
          "REVOKE #{privilege} ON public.mixer_browser_sessions FROM surface_neighbor",
          &rejected!/0
        )
      end
    after
      q!(Admin, "REVOKE surface_neighbor FROM browser_ordinary")
    end
  end

  test "unreviewed application SECURITY DEFINER execution is denied for lifecycle and writer" do
    q!(
      Admin,
      "CREATE FUNCTION public.surface_escape() RETURNS boolean LANGUAGE sql SECURITY DEFINER AS 'SELECT true'"
    )

    q!(Admin, "REVOKE ALL ON FUNCTION public.surface_escape() FROM PUBLIC")

    try do
      for role <- ["browser_lifecycle", "browser_writer"] do
        mutate!(
          "GRANT EXECUTE ON FUNCTION public.surface_escape() TO #{role}",
          "REVOKE EXECUTE ON FUNCTION public.surface_escape() FROM #{role}",
          &rejected!/0
        )
      end

      # A closed function ACL by itself is not an escape and does not join the
      # reviewed surface. No wildcard allowlist learns it from the catalog.
      assert check!() == :function_surface_verified
    after
      q!(Admin, "DROP FUNCTION public.surface_escape()")
    end
  end

  test "function-surface result explicitly cannot attest relation RLS or check expressions" do
    mutate!(
      "ALTER TABLE public.mixer_browser_sessions NO FORCE ROW LEVEL SECURITY",
      "ALTER TABLE public.mixer_browser_sessions FORCE ROW LEVEL SECURITY",
      fn ->
        assert check!() == :function_surface_verified
      end
    )

    mutate!(
      "ALTER TABLE public.mixer_browser_sessions DROP CONSTRAINT mixer_browser_sessions_id_check",
      "ALTER TABLE public.mixer_browser_sessions ADD CONSTRAINT mixer_browser_sessions_id_check CHECK (octet_length(id)=16)",
      fn ->
        assert check!() == :function_surface_verified
      end
    )
  end

  defp deadline, do: System.monotonic_time(:millisecond) + 4_500

  defp q!(repo, sql),
    do: Ecto.Adapters.SQL.query!(repo, sql, [], log: false, queue: false, timeout: 5_000)

  defp check! do
    {:ok, result} =
      Repo.transaction(
        fn ->
          Catalog.check_function_surface!(Repo, @roles, deadline())
        end,
        timeout: 5_000,
        queue: false
      )

    result
  end

  defp rejected!(fun \\ fn -> Catalog.check_function_surface!(Repo, @roles, deadline()) end) do
    assert {:ok, :rejected} =
             Repo.transaction(
               fn ->
                 assert_raise Catalog.Unavailable, fun
                 :rejected
               end,
               timeout: 5_000,
               queue: false
             )
  end

  defp mutate!(up, down, fun) do
    q!(Admin, up)

    try do
      fun.()
    after
      q!(Admin, down)
    end

    assert check!() == :function_surface_verified
  end

  defp source_sql(name) do
    StorageSchema.statements()
    |> Enum.find(&String.starts_with?(&1, "CREATE FUNCTION public.#{name}("))
    |> String.replace_prefix("CREATE FUNCTION", "CREATE OR REPLACE FUNCTION")
  end
end

