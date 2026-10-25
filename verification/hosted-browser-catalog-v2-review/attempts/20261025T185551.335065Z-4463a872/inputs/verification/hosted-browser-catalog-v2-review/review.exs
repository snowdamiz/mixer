Code.require_file("hosted/test/mixer_hosted/browser_auth/storage_fixture.exs")

defmodule MixerHosted.BrowserAuth.V2ReviewRepo do
  use Ecto.Repo, otp_app: :v2_review, adapter: Ecto.Adapters.Postgres
end

defmodule MixerHosted.BrowserAuth.V2ReviewTrap do
  def in_transaction? do
    send(self(), :unexpected_repo)
    raise "synthetic secret must be redacted"
  end
end

defmodule MixerHosted.BrowserAuth.V2IndependentReview do
  use ExUnit.Case, async: false
  alias MixerHosted.BrowserAuth.{ActivationPreparationSchema, Catalog, StorageFixture}
  alias MixerHosted.BrowserAuth.V2ReviewRepo, as: Repo
  alias StorageFixture.{Admin, Migration}

  @roles %{
    lifecycle_login: "browser_lifecycle",
    writer: "browser_writer",
    relation_owner: "browser_schema_owner",
    ordinary_runtime_login: "browser_ordinary"
  }
  @helper "public.mixer_browser_prepare_activation(bytea,bytea,bytea,bytea,bigint,public.mixer_browser_access_evidence)"
  @evidence "public.mixer_browser_access_evidence"

  setup_all do
    for app <- [:ecto_sql, :postgrex, :jason], do: Application.ensure_all_started(app)

    common = [
      hostname: "127.0.0.1",
      port: StorageFixture.port(),
      database: "browser_storage",
      log: false
    ]

    start_supervised!({Admin, common ++ [username: "browser_admin", pool_size: 2]})

    start_supervised!(
      {Migration,
       common ++
         [
           username: "browser_admin",
           pool_size: 2,
           after_connect: fn conn ->
             Postgrex.query!(conn, "SET ROLE browser_schema_owner", [])
           end
         ]}
    )

    # The accepted fixture is reused only to install/provision synthetic storage.
    # The attack oracles below do not import either producer test suite.
    StorageFixture.install!()
    StorageFixture.provision!()

    start_supervised!(
      {Repo,
       common ++
         [
           username: "browser_lifecycle",
           pool_size: 1,
           telemetry_prefix: [:v2_review],
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

    q(Repo, "SELECT 1")
    :ok
  end

  test "baseline and combined deployments accept only their exact version and partial marker" do
    assert check(1) == :function_surface_verified

    assert tx(fn -> Catalog.check_function_surface!(Repo, @roles, deadline()) end) ==
             :function_surface_verified

    deny(2)

    combined(fn ->
      assert check(2) == :function_surface_verified
      deny(1)

      assert_raise Catalog.Unavailable, fn ->
        tx(fn -> Catalog.check_function_surface!(Repo, @roles, deadline()) end)
      end

      refute function_exported?(Catalog, :admit!, 0)
    end)
  end

  test "noninteger versions fail before transaction or query admission with one redacted shape" do
    for version <- [
          1.0,
          2.0,
          0,
          -2,
          3,
          nil,
          true,
          false,
          "2",
          <<>>,
          [],
          {2},
          %{version: 2},
          Catalog,
          &check/1,
          9_223_372_036_854_775_807
        ] do
      error =
        assert_raise Catalog.Unavailable, fn ->
          Catalog.check_function_surface!(
            MixerHosted.BrowserAuth.V2ReviewTrap,
            @roles,
            deadline(),
            version
          )
        end

      redacted(error)
      refute_received :unexpected_repo
    end
  end

  test "duplicate accepted names in another namespace and temporary browser types deny both versions" do
    q(Admin, "CREATE SCHEMA review_types")

    try do
      for version <- [1, 2] do
        versioned(version, fn ->
          mutate(
            "CREATE TYPE review_types.mixer_browser_cipher AS (key_id text)",
            "DROP TYPE review_types.mixer_browser_cipher",
            fn -> deny(version) end
          )

          {:ok, conn} =
            Postgrex.start_link(
              hostname: "127.0.0.1",
              port: StorageFixture.port(),
              database: "browser_storage",
              username: "browser_admin"
            )

          try do
            Postgrex.query!(
              conn,
              "CREATE TYPE pg_temp.mixer_browser_temporary AS (value text)",
              []
            )

            deny(version)
          after
            GenServer.stop(conn)
          end

          assert check(version) == :function_surface_verified
        end)
      end
    after
      q(Admin, "DROP SCHEMA review_types")
    end
  end

  test "closed domains and enums in inaccessible namespaces cannot escape either version" do
    q(Admin, "CREATE SCHEMA review_types")

    try do
      for version <- [1, 2] do
        versioned(version, fn ->
          for sql <- [
                "CREATE TYPE review_types.mixer_browser_extra AS ENUM ('a')",
                "CREATE DOMAIN review_types.mixer_browser_extra AS text"
              ] do
            mutate(sql, "DROP TYPE review_types.mixer_browser_extra", fn ->
              q(Admin, "REVOKE ALL ON TYPE review_types.mixer_browser_extra FROM PUBLIC")
              deny(version)
            end)
          end
        end)
      end
    after
      q(Admin, "DROP SCHEMA review_types")
    end
  end

  test "table row types remain outside this partial admission even in a second namespace" do
    combined(fn ->
      q(Admin, "CREATE SCHEMA review_rows")

      try do
        mutate(
          "CREATE TABLE review_rows.mixer_browser_unadmitted(value text)",
          "DROP TABLE review_rows.mixer_browser_unadmitted",
          fn ->
            assert check(2) == :function_surface_verified
          end
        )
      after
        q(Admin, "DROP SCHEMA review_rows")
      end
    end)
  end

  test "moving the exact preparation function into a second namespace cannot qualify" do
    combined(fn ->
      q(Admin, "CREATE SCHEMA review_moved")

      try do
        mutate(
          "ALTER FUNCTION #{@helper} SET SCHEMA review_moved",
          "ALTER FUNCTION review_moved.mixer_browser_prepare_activation(bytea,bytea,bytea,bytea,bigint,public.mixer_browser_access_evidence) SET SCHEMA public",
          fn -> deny(2) end
        )
      after
        q(Admin, "DROP SCHEMA review_moved")
      end
    end)
  end

  test "duplicate valid function ACL entries fail instead of hiding beyond the cap" do
    combined(fn ->
      mutate(
        "UPDATE pg_proc SET proacl=proacl||proacl[1:1] WHERE oid='#{@helper}'::regprocedure",
        "UPDATE pg_proc SET proacl=proacl[1:2] WHERE oid='#{@helper}'::regprocedure",
        fn -> deny(2) end
      )
    end)
  end

  test "duplicate valid type ACL entries fail instead of normalizing to a set" do
    combined(fn ->
      mutate(
        "UPDATE pg_type SET typacl=typacl||typacl[1:1] WHERE oid='#{@evidence}'::regtype",
        "UPDATE pg_type SET typacl=typacl[1:3] WHERE oid='#{@evidence}'::regtype",
        fn -> deny(2) end
      )
    end)
  end

  test "a nonprivileged named grantor with unchanged effective privileges is denied" do
    combined(fn ->
      mutate(
        "UPDATE pg_proc SET proacl=replace(proacl::text,'/browser_writer','/review_mid')::aclitem[] WHERE oid='#{@helper}'::regprocedure",
        "UPDATE pg_proc SET proacl=replace(proacl::text,'/review_mid','/browser_writer')::aclitem[] WHERE oid='#{@helper}'::regprocedure",
        fn ->
          assert q(
                   Admin,
                   "SELECT has_function_privilege('browser_lifecycle','#{@helper}','EXECUTE')"
                 ).rows == [[true]]

          deny(2)
        end
      )

      mutate(
        "UPDATE pg_type SET typacl=replace(typacl::text,'/browser_schema_owner','/review_mid')::aclitem[] WHERE oid='#{@evidence}'::regtype",
        "UPDATE pg_type SET typacl=replace(typacl::text,'/review_mid','/browser_schema_owner')::aclitem[] WHERE oid='#{@evidence}'::regtype",
        fn ->
          assert q(Admin, "SELECT has_type_privilege('browser_lifecycle','#{@evidence}','USAGE')").rows ==
                   [[true]]

          deny(2)
        end
      )
    end)
  end

  test "optional added-helper argument metadata has no permissive defaults" do
    combined(fn ->
      for {column, altered, original} <- [
            {"pronargdefaults", "1", "0"},
            {"provariadic", "25", "0"},
            {"proargmodes", "ARRAY['i','i','i','i','i','i']::char[]", "NULL"},
            {"prokind", "'p'", "'f'"}
          ] do
        mutate(
          "UPDATE pg_proc SET #{column}=#{altered} WHERE oid='#{@helper}'::regprocedure",
          "UPDATE pg_proc SET #{column}=#{original} WHERE oid='#{@helper}'::regprocedure",
          fn -> deny(2) end
        )
      end
    end)
  end

  test "oversized added-helper arrays reject rather than accepting valid prefixes" do
    combined(fn ->
      [[config, names]] =
        q(Admin, "SELECT proconfig,proargnames FROM pg_proc WHERE oid='#{@helper}'::regprocedure").rows

      for {column, oversized, original} <- [
            {"proargnames", names ++ List.duplicate("x", 17), names},
            {"proconfig", ["search_path=" <> String.duplicate("x", 513) | tl(config)], config}
          ] do
        q(Admin, "UPDATE pg_proc SET #{column}=$1::text[] WHERE oid='#{@helper}'::regprocedure", [
          oversized
        ])

        try do
          deny(2)
        after
          q(
            Admin,
            "UPDATE pg_proc SET #{column}=$1::text[] WHERE oid='#{@helper}'::regprocedure",
            [original]
          )
        end

        assert check(2) == :function_surface_verified
      end
    end)
  end

  test "added-helper SQL-standard parsed body metadata is never silently ignored" do
    combined(fn ->
      q(
        Admin,
        "CREATE FUNCTION public.review_sql_body() RETURNS boolean LANGUAGE SQL RETURN true"
      )

      try do
        mutate(
          "UPDATE pg_proc SET prosqlbody=(SELECT prosqlbody FROM pg_proc WHERE oid='public.review_sql_body()'::regprocedure) WHERE oid='#{@helper}'::regprocedure",
          "UPDATE pg_proc SET prosqlbody=NULL WHERE oid='#{@helper}'::regprocedure",
          fn -> deny(2) end
        )
      after
        q(Admin, "DROP FUNCTION public.review_sql_body()")
      end
    end)
  end

  test "added evidence generated default identity and multidimension flags deny" do
    combined(fn ->
      for {column, altered, original, field} <- [
            {"atthasdef", "true", "false", "profile_id"},
            {"attgenerated", "'s'", "''", "profile_id"},
            {"attidentity", "'a'", "''", "profile_id"},
            {"attndims", "2", "1", "scopes"}
          ] do
        mutate(
          "UPDATE pg_attribute SET #{column}=#{altered} WHERE attrelid=(SELECT typrelid FROM pg_type WHERE oid='#{@evidence}'::regtype) AND attname='#{field}'",
          "UPDATE pg_attribute SET #{column}=#{original} WHERE attrelid=(SELECT typrelid FROM pg_type WHERE oid='#{@evidence}'::regtype) AND attname='#{field}'",
          fn -> deny(2) end
        )
      end
    end)
  end

  test "both fixed projections issue their exact count plus one SQL bounds without replay" do
    for {version, caps} <- [{1, [19, 28, 4, 26, 10, 19]}, {2, [20, 30, 5, 35, 13, 20]}] do
      versioned(version, fn ->
        queries = observe(fn -> assert check(version) == :function_surface_verified end)

        interesting =
          Enum.filter(queries, fn sql ->
            String.contains?(sql, "LIMIT") and
              (String.contains?(sql, "mixer_browser_") or String.contains?(sql, "t.typname=ANY")) and
              not String.contains?(sql, "LIMIT 1\n")
          end)

        assert Enum.map(interesting, fn sql ->
                 [_, digits] = Regex.run(~r/LIMIT ([0-9]+)\s*$/, sql)
                 String.to_integer(digits)
               end) == caps

        assert length(queries) == length(Enum.uniq(queries))
      end)
    end
  end

  test "original budget remains consumed after a successful query crosses its deadline" do
    combined(fn ->
      id = {__MODULE__, make_ref()}

      :telemetry.attach(
        id,
        [:v2_review, :query],
        fn _, _, meta, _ ->
          if String.starts_with?(meta.query, "SELECT current_user"), do: Process.sleep(130)
        end,
        nil
      )

      try do
        error =
          assert_raise Catalog.Unavailable, fn ->
            tx(fn ->
              Catalog.check_function_surface!(
                Repo,
                @roles,
                System.monotonic_time(:millisecond) + 100,
                2
              )
            end)
          end

        redacted(error)
      after
        :telemetry.detach(id)
      end

      assert check(2) == :function_surface_verified
    end)
  end

  test "adding role privilege only after upgrade still denies current readmission" do
    combined(fn ->
      for {up, down} <- [
            {"ALTER ROLE browser_schema_owner BYPASSRLS",
             "ALTER ROLE browser_schema_owner NOBYPASSRLS"},
            {"GRANT review_mid TO browser_writer", "REVOKE review_mid FROM browser_writer"},
            {"GRANT browser_schema_owner TO review_mid",
             "REVOKE browser_schema_owner FROM review_mid"}
          ] do
        if String.contains?(up, "TO review_mid"),
          do: q(Admin, "GRANT review_mid TO browser_ordinary")

        try do
          mutate(up, down, fn -> deny(2) end)
        after
          if String.contains?(up, "TO review_mid"),
            do: q(Admin, "REVOKE review_mid FROM browser_ordinary")
        end
      end
    end)
  end

  test "a failure in the last direct-escape query is redacted after all function type checks" do
    combined(fn ->
      mutate(
        "REVOKE SELECT ON pg_catalog.pg_attribute FROM PUBLIC",
        "GRANT SELECT ON pg_catalog.pg_attribute TO PUBLIC",
        fn -> deny(2) end
      )
    end)
  end

  test "relation policies and writer grants require a separate admission even after v2" do
    combined(fn ->
      mutate(
        "CREATE POLICY review_partial ON public.mixer_browser_sessions USING (true)",
        "DROP POLICY review_partial ON public.mixer_browser_sessions",
        fn ->
          assert check(2) == :function_surface_verified
        end
      )

      mutate(
        "GRANT DELETE ON public.mixer_browser_sessions TO browser_writer",
        "REVOKE DELETE ON public.mixer_browser_sessions FROM browser_writer",
        fn ->
          assert check(2) == :function_surface_verified
        end
      )
    end)
  end

  defp q(repo, sql, params \\ []),
    do: Ecto.Adapters.SQL.query!(repo, sql, params, queue: false, timeout: 5_000, log: false)

  defp deadline, do: System.monotonic_time(:millisecond) + 4_500

  defp tx(fun) do
    {:ok, value} = Repo.transaction(fun, queue: false, timeout: 5_000)
    value
  end

  defp check(version),
    do: tx(fn -> Catalog.check_function_surface!(Repo, @roles, deadline(), version) end)

  defp redacted(error),
    do:
      assert(
        Map.from_struct(error) == %{
          __exception__: true,
          message: "browser catalog function surface unavailable"
        }
      )

  defp deny(version), do: redacted(assert_raise Catalog.Unavailable, fn -> check(version) end)

  defp mutate(up, down, fun) do
    q(Admin, up)

    try do
      fun.()
    after
      q(Admin, down)
    end
  end

  defp combined(fun) do
    Enum.each(ActivationPreparationSchema.statements(), &q(Migration, &1))

    try do
      Enum.each(
        ActivationPreparationSchema.provisioning_statements(
          "browser_writer",
          "browser_lifecycle",
          "browser_schema_owner"
        ),
        &q(Admin, &1)
      )

      assert check(2) == :function_surface_verified
      fun.()
    after
      q(Admin, "DROP FUNCTION IF EXISTS #{@helper}")
      q(Admin, "DROP TYPE IF EXISTS #{@evidence}")
    end

    assert check(1) == :function_surface_verified
  end

  defp versioned(1, fun), do: fun.()
  defp versioned(2, fun), do: combined(fun)

  defp observe(fun) do
    id = {__MODULE__, make_ref()}
    parent = self()

    :telemetry.attach(
      id,
      [:v2_review, :query],
      fn _, _, meta, _ -> send(parent, {:review_query, meta.query}) end,
      nil
    )

    try do
      fun.()
    after
      :telemetry.detach(id)
    end

    drain([])
  end

  defp drain(acc) do
    receive do
      {:review_query, query} -> drain(acc ++ [query])
    after
      0 -> acc
    end
  end
end
