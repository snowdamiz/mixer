Code.require_file("hosted/test/mixer_hosted/browser_auth/storage_fixture.exs")

defmodule MixerHosted.BrowserAuth.CatalogV2Repo do
  use Ecto.Repo, otp_app: :catalog_v2, adapter: Ecto.Adapters.Postgres
end

defmodule MixerHosted.BrowserAuth.CatalogV2TrapRepo do
  def in_transaction? do
    send(self(), :unexpected_repo_call)
    raise "unexpected Repo call"
  end
end

defmodule MixerHosted.BrowserAuth.CatalogV2Test do
  use ExUnit.Case, async: false

  alias MixerHosted.BrowserAuth.{
    ActivationPreparationSchema,
    Catalog,
    CatalogManifest,
    CatalogManifestV2,
    StorageFixture
  }

  alias MixerHosted.BrowserAuth.StorageFixture.{Admin, Migration}
  alias MixerHosted.BrowserAuth.CatalogV2Repo, as: Repo

  @roles %{
    lifecycle_login: "browser_lifecycle",
    writer: "browser_writer",
    relation_owner: "browser_schema_owner",
    ordinary_runtime_login: "browser_ordinary"
  }
  @helper "public.mixer_browser_prepare_activation(bytea,bytea,bytea,bytea,bigint,public.mixer_browser_access_evidence)"
  @type_name "public.mixer_browser_access_evidence"
  @name "mixer_browser_prepare_activation"
  @fields ~w(profile_id profile_version issuer subject client_id credential_ref issued_at expires_at scopes)

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

    StorageFixture.install!()
    StorageFixture.provision!()

    start_supervised!(
      {Repo,
       common ++
         [
           username: "browser_lifecycle",
           pool_size: 1,
           telemetry_prefix: [:catalog_v2],
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

  test "static v2 is exactly unchanged v1 plus accepted helper type and decoder pin" do
    assert Map.drop(CatalogManifestV2.functions(), [@name]) == CatalogManifest.functions()

    assert Map.drop(CatalogManifestV2.composites(), ["mixer_browser_access_evidence"]) ==
             CatalogManifest.composites()

    assert map_size(CatalogManifestV2.functions()) == 19
    assert map_size(CatalogManifestV2.composites()) == 4
    assert Enum.count(CatalogManifestV2.functions(), fn {_, f} -> f.runtime_execute end) == 10
    assert Enum.sum(Enum.map(CatalogManifestV2.composites(), fn {_, f} -> length(f) end)) == 34

    assert CatalogManifestV2.argument_names()[@name] ==
             ~w(p_cookie p_state p_config p_claim p_revision i)

    assert CatalogManifestV2.returns()[@name] == "jsonb"

    assert CatalogManifestV2.decoder() == %{
             module: "MixerHosted.BrowserAuth.ActivationPreparation",
             source_sha256: "e208e159719dd29ff75186667404cb6018391a2ecc3b8a3534db131d1bc281f5"
           }

    assert CatalogManifestV2.source_pins()["activation_preparation_schema.ex"] ==
             "d58bc6009d6118ba9469f087af99e893df6a99038cdccec11ba5048d48bf4ae8"

    assert not function_exported?(Catalog, :admit!, 0)
  end

  test "three argument API remains v1 and explicit v2 rejects baseline" do
    assert check(1) == :function_surface_verified
    assert check(:default) == :function_surface_verified
    denied(2)
  end

  test "only exact integer versions are accepted before any Repo call" do
    for version <- [
          nil,
          false,
          true,
          0,
          3,
          -1,
          1.0,
          2.0,
          "1",
          "2",
          :v2,
          %{},
          %{version: 2},
          CatalogManifestV2,
          fn -> 2 end
        ] do
      error =
        assert_raise Catalog.Unavailable, fn ->
          Catalog.check_function_surface!(
            MixerHosted.BrowserAuth.CatalogV2TrapRepo,
            @roles,
            deadline(),
            version
          )
        end

      assert_redacted(error)
      refute_received :unexpected_repo_call
    end
  end

  test "addition type alone rejects both versions including an exact field list" do
    [type_sql | _] = ActivationPreparationSchema.statements()
    q(Migration, type_sql)

    try do
      q(Migration, "REVOKE ALL ON TYPE #{@type_name} FROM PUBLIC")
      denied(1)
      denied(2)
    after
      q(Admin, "DROP TYPE #{@type_name}")
    end

    assert check(1) == :function_surface_verified
  end

  test "inert complete addition rejects v1 and v2 before upgrade provisioning" do
    install()

    try do
      denied(1)
      denied(2)
    after
      remove()
    end
  end

  test "upgraded combined surface accepts v2 repeatedly and rejects v1" do
    versioned(2, fn ->
      assert check(2) == :function_surface_verified
      assert check(2) == :function_surface_verified
      denied(1)
      assert_raise Catalog.Unavailable, fn -> check(:default) end
    end)

    assert check(1) == :function_surface_verified
    denied(2)
  end

  test "actual combined function source signatures parameter names settings and results match static input" do
    versioned(2, fn ->
      {:ok, rows} =
        Admin.transaction(fn ->
          q(Admin, "SET LOCAL search_path=pg_catalog")

          q(
            Admin,
            "SELECT p.proname::text,oidvectortypes(p.proargtypes),pg_get_function_result(p.oid),p.prosrc,p.proconfig,p.proargnames FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname='public' AND left(p.proname,14)='mixer_browser_' ORDER BY p.proname"
          ).rows
        end)

      assert length(rows) == 19

      for [name, args, result, source, settings, names] <- rows do
        expected = CatalogManifestV2.functions()[name]
        assert args == String.replace(expected.signature, ",", ", ")
        assert result == CatalogManifestV2.returns()[name]
        assert source == expected.source
        assert settings == expected.settings
        assert names == CatalogManifestV2.argument_names()[name]
      end

      assert check(2) == :function_surface_verified
    end)
  end

  test "actual ACLs include exact owner grantor no grant option and 29 function plus 12 type grants" do
    versioned(2, fn ->
      functions =
        q(
          Admin,
          "SELECT p.proname::text,g.rolname::text,s.rolname::text,a.privilege_type,a.is_grantable FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace CROSS JOIN LATERAL aclexplode(p.proacl) a JOIN pg_roles g ON g.oid=a.grantee JOIN pg_roles s ON s.oid=a.grantor WHERE n.nspname='public' AND left(p.proname,14)='mixer_browser_'"
        ).rows

      expected =
        Enum.flat_map(CatalogManifestV2.functions(), fn {n, f} ->
          [[n, "browser_writer", "browser_writer", "EXECUTE", false]] ++
            if(f.runtime_execute,
              do: [[n, "browser_lifecycle", "browser_writer", "EXECUTE", false]],
              else: []
            )
        end)

      assert length(functions) == 29
      assert Enum.sort(functions) == Enum.sort(expected)

      types =
        q(
          Admin,
          "SELECT t.typname::text,g.rolname::text,s.rolname::text,a.privilege_type,a.is_grantable FROM pg_type t CROSS JOIN LATERAL aclexplode(t.typacl) a JOIN pg_roles g ON g.oid=a.grantee JOIN pg_roles s ON s.oid=a.grantor WHERE t.typname=ANY($1::text[])",
          [Map.keys(CatalogManifestV2.composites())]
        ).rows

      assert length(types) == 12

      assert Enum.sort(types) ==
               Enum.sort(
                 for n <- Map.keys(CatalogManifestV2.composites()),
                     r <- ~w(browser_schema_owner browser_writer browser_lifecycle),
                     do: [n, r, "browser_schema_owner", "USAGE", false]
               )
    end)
  end

  test "actual added composite has exact nine ordered names and types" do
    versioned(2, fn ->
      rows =
        q(
          Admin,
          "SELECT attname::text,format_type(atttypid,atttypmod),attnum::int FROM pg_attribute WHERE attrelid=(SELECT typrelid FROM pg_type WHERE oid='#{@type_name}'::regtype) AND attnum>0 ORDER BY attnum"
        ).rows

      assert rows ==
               Enum.zip([
                 @fields,
                 ~w(text integer text text text text bigint bigint text[]),
                 Enum.to_list(1..9)
               ])
               |> Enum.map(&Tuple.to_list/1)
    end)
  end

  test "each of all nineteen v2 bodies rejects independent byte drift then restores" do
    versioned(2, fn ->
      for {name, f} <- CatalogManifestV2.functions() do
        mutate(
          "UPDATE pg_proc SET prosrc=prosrc||E'\\n-- drift' WHERE oid=$1::text::regprocedure",
          ["public.#{name}(#{f.signature})"],
          "UPDATE pg_proc SET prosrc=$1 WHERE oid=$2::text::regprocedure",
          [f.source, "public.#{name}(#{f.signature})"],
          fn -> denied(2) end
        )
      end

      assert check(2) == :function_surface_verified
    end)
  end

  test "added helper argument names and oversized source cannot authorize themselves" do
    versioned(2, fn ->
      mutate(
        "UPDATE pg_proc SET proargnames=ARRAY['renamed','p_state','p_config','p_claim','p_revision','i']::text[] WHERE oid='#{@helper}'::regprocedure",
        [],
        "UPDATE pg_proc SET proargnames=$1::text[] WHERE oid='#{@helper}'::regprocedure",
        [CatalogManifestV2.argument_names()[@name]],
        fn -> denied(2) end
      )

      mutate(
        "UPDATE pg_proc SET prosrc=$1 WHERE oid='#{@helper}'::regprocedure",
        [String.duplicate("x", 65_537)],
        "UPDATE pg_proc SET prosrc=$1 WHERE oid='#{@helper}'::regprocedure",
        [CatalogManifestV2.functions()[@name].source],
        fn -> denied(2) end
      )
    end)
  end

  test "added helper exact settings security definer and optional attributes fail closed" do
    versioned(2, fn ->
      for {up, down} <- [
            {"RESET lock_timeout", "SET lock_timeout='500ms'"},
            {"SET work_mem='16MB'", "RESET work_mem"},
            {"SECURITY INVOKER", "SECURITY DEFINER"},
            {"STABLE", "VOLATILE"},
            {"STRICT", "CALLED ON NULL INPUT"},
            {"PARALLEL SAFE", "PARALLEL UNSAFE"},
            {"LEAKPROOF", "NOT LEAKPROOF"}
          ] do
        mutate("ALTER FUNCTION #{@helper} #{up}", "ALTER FUNCTION #{@helper} #{down}", fn ->
          denied(2)
        end)
      end

      for {column, value, restore} <- [
            {"prosupport", "'abs(integer)'::regprocedure", "0"},
            {"probin", "'extra'", "NULL"},
            {"proretset", "true", "false"}
          ] do
        mutate(
          "UPDATE pg_proc SET #{column}=#{value} WHERE oid='#{@helper}'::regprocedure",
          "UPDATE pg_proc SET #{column}=#{restore} WHERE oid='#{@helper}'::regprocedure",
          fn -> denied(2) end
        )
      end
    end)
  end

  test "missing helper and a renamed helper reject v2" do
    versioned(2, fn ->
      mutate(
        "ALTER FUNCTION #{@helper} RENAME TO other_prepare",
        "ALTER FUNCTION public.other_prepare(bytea,bytea,bytea,bytea,bigint,public.mixer_browser_access_evidence) RENAME TO #{@name}",
        fn -> denied(2) end
      )

      q(Admin, "DROP FUNCTION #{@helper}")
      denied(2)
    end)
  end

  test "an added helper overload trips the v2 function cap plus one sentinel" do
    versioned(2, fn ->
      mutate(
        "CREATE FUNCTION public.mixer_browser_prepare_activation(text) RETURNS boolean LANGUAGE sql AS 'SELECT true'",
        "DROP FUNCTION public.mixer_browser_prepare_activation(text)",
        fn -> denied(2) end
      )
    end)
  end

  test "added helper result language and fixed signature are mandatory" do
    versioned(2, fn ->
      q(Admin, "DROP FUNCTION #{@helper}")

      q(
        Admin,
        "CREATE FUNCTION #{@helper} RETURNS boolean LANGUAGE sql SECURITY DEFINER AS 'SELECT true'"
      )

      q(Admin, "ALTER FUNCTION #{@helper} OWNER TO browser_writer")
      q(Admin, "REVOKE ALL ON FUNCTION #{@helper} FROM PUBLIC")
      q(Admin, "GRANT EXECUTE ON FUNCTION #{@helper} TO browser_lifecycle")
      denied(2)
    end)
  end

  test "added helper owner must be exact writer" do
    versioned(2, fn ->
      mutate(
        "ALTER FUNCTION #{@helper} OWNER TO browser_schema_owner",
        "ALTER FUNCTION #{@helper} OWNER TO browser_writer",
        fn -> denied(2) end
      )
    end)
  end

  test "added helper grants reject extra missing PUBLIC ordinary and grant option ACLs" do
    versioned(2, fn ->
      for {up, down} <- [
            {"GRANT EXECUTE ON FUNCTION #{@helper} TO PUBLIC",
             "REVOKE EXECUTE ON FUNCTION #{@helper} FROM PUBLIC"},
            {"GRANT EXECUTE ON FUNCTION #{@helper} TO browser_ordinary",
             "REVOKE EXECUTE ON FUNCTION #{@helper} FROM browser_ordinary"},
            {"GRANT EXECUTE ON FUNCTION #{@helper} TO surface_neighbor",
             "REVOKE EXECUTE ON FUNCTION #{@helper} FROM surface_neighbor"},
            {"REVOKE EXECUTE ON FUNCTION #{@helper} FROM browser_lifecycle",
             "GRANT EXECUTE ON FUNCTION #{@helper} TO browser_lifecycle"},
            {"GRANT EXECUTE ON FUNCTION #{@helper} TO browser_lifecycle WITH GRANT OPTION",
             "REVOKE GRANT OPTION FOR EXECUTE ON FUNCTION #{@helper} FROM browser_lifecycle"}
          ] do
        mutate(up, down, fn -> denied(2) end)
      end
    end)
  end

  test "grantor-only function ACL drift rejects both versions including new helper" do
    for version <- [1, 2] do
      versioned(version, fn ->
        names = if version == 1, do: ["mixer_browser_load"], else: ["mixer_browser_load", @name]

        for name <- names do
          mutate(
            "UPDATE pg_proc SET proacl=replace(proacl::text,'/browser_writer','/browser_admin')::aclitem[] WHERE proname=$1",
            [name],
            "UPDATE pg_proc SET proacl=replace(proacl::text,'/browser_admin','/browser_writer')::aclitem[] WHERE proname=$1",
            [name],
            fn -> denied(version) end
          )
        end
      end)
    end
  end

  test "grantor-only type ACL drift rejects both versions and all four v2 composites" do
    for version <- [1, 2] do
      versioned(version, fn ->
        manifest = if version == 1, do: CatalogManifest, else: CatalogManifestV2

        for name <- Map.keys(manifest.composites()) do
          mutate(
            "UPDATE pg_type SET typacl=replace(typacl::text,'/browser_schema_owner','/browser_admin')::aclitem[] WHERE typname=$1",
            [name],
            "UPDATE pg_type SET typacl=replace(typacl::text,'/browser_admin','/browser_schema_owner')::aclitem[] WHERE typname=$1",
            [name],
            fn -> denied(version) end
          )
        end
      end)
    end
  end

  test "closed extra standalone browser composite in public or another schema rejects both versions" do
    q(Admin, "CREATE SCHEMA catalog_extra")

    try do
      for version <- [1, 2] do
        versioned(version, fn ->
          for schema <- ["public", "catalog_extra"] do
            mutate(
              "CREATE TYPE #{schema}.mixer_browser_extra AS (value text)",
              "DROP TYPE #{schema}.mixer_browser_extra",
              fn ->
                q(Admin, "REVOKE ALL ON TYPE #{schema}.mixer_browser_extra FROM PUBLIC")
                denied(version)
              end
            )
          end
        end)
      end
    after
      q(Admin, "DROP SCHEMA catalog_extra")
    end
  end

  test "an extra browser enum or domain cannot hide outside standalone composite discovery" do
    for version <- [1, 2] do
      versioned(version, fn ->
        for definition <- ["AS ENUM('one')", "AS (value text)"] do
          mutate(
            "CREATE TYPE public.mixer_browser_extra #{definition}",
            "DROP TYPE public.mixer_browser_extra",
            fn -> denied(version) end
          )
        end

        mutate(
          "CREATE DOMAIN public.mixer_browser_extra AS text",
          "DROP DOMAIN public.mixer_browser_extra",
          fn -> denied(version) end
        )
      end)
    end
  end

  test "added type owner ACL usage and grant option must remain exact" do
    versioned(2, fn ->
      for {up, down} <- [
            {"ALTER TYPE #{@type_name} OWNER TO browser_admin",
             "ALTER TYPE #{@type_name} OWNER TO browser_schema_owner"},
            {"GRANT USAGE ON TYPE #{@type_name} TO PUBLIC",
             "REVOKE USAGE ON TYPE #{@type_name} FROM PUBLIC"},
            {"GRANT USAGE ON TYPE #{@type_name} TO surface_neighbor",
             "REVOKE USAGE ON TYPE #{@type_name} FROM surface_neighbor"},
            {"REVOKE USAGE ON TYPE #{@type_name} FROM browser_lifecycle",
             "GRANT USAGE ON TYPE #{@type_name} TO browser_lifecycle"},
            {"GRANT USAGE ON TYPE #{@type_name} TO browser_writer WITH GRANT OPTION",
             "REVOKE GRANT OPTION FOR USAGE ON TYPE #{@type_name} FROM browser_writer"}
          ] do
        mutate(up, down, fn -> denied(2) end)
      end
    end)
  end

  test "every new type field name order type collation and dimensions is checked" do
    versioned(2, fn ->
      for field <- @fields do
        mutate(
          "UPDATE pg_attribute SET attname='changed' WHERE attrelid=(SELECT typrelid FROM pg_type WHERE oid='#{@type_name}'::regtype) AND attname=$1",
          [field],
          "UPDATE pg_attribute SET attname=$1 WHERE attrelid=(SELECT typrelid FROM pg_type WHERE oid='#{@type_name}'::regtype) AND attname='changed'",
          [field],
          fn -> denied(2) end
        )
      end

      for {column, value, restore} <- [
            {"attcollation", "0", "'default'::regcollation"},
            {"attnotnull", "true", "false"},
            {"attndims", "1", "0"},
            {"attnum", "10", "1"},
            {"atttypid", "'varchar'::regtype", "'text'::regtype"}
          ] do
        mutate(
          "UPDATE pg_attribute SET #{column}=#{value} WHERE attrelid=(SELECT typrelid FROM pg_type WHERE oid='#{@type_name}'::regtype) AND attname='profile_id'",
          "UPDATE pg_attribute SET #{column}=#{restore} WHERE attrelid=(SELECT typrelid FROM pg_type WHERE oid='#{@type_name}'::regtype) AND attname='profile_id'",
          fn -> denied(2) end
        )
      end
    end)
  end

  test "v2 field cap plus one and retained dropped field are both denied" do
    versioned(2, fn ->
      q(Admin, "ALTER TYPE #{@type_name} ADD ATTRIBUTE extra text")
      denied(2)
      q(Admin, "ALTER TYPE #{@type_name} DROP ATTRIBUTE extra")
      denied(2)
    end)
  end

  test "both version escape scans reject callable definer outside reviewed surface" do
    for version <- [1, 2] do
      versioned(version, fn ->
        mutate(
          "CREATE FUNCTION public.catalog_escape() RETURNS boolean LANGUAGE sql SECURITY DEFINER AS 'SELECT true'",
          "DROP FUNCTION public.catalog_escape()",
          fn -> denied(version) end
        )
      end)
    end
  end

  test "v2 keeps exact roles transaction original deadline and session policy" do
    versioned(2, fn ->
      assert_raise Catalog.Unavailable, fn ->
        Catalog.check_function_surface!(Repo, @roles, deadline(), 2)
      end

      for roles <- [
            Map.put(@roles, :extra, "value"),
            %{@roles | writer: "browser_lifecycle"},
            %{@roles | writer: "pg_read_all_data"}
          ] do
        assert_raise Catalog.Unavailable, fn ->
          tx(fn -> Catalog.check_function_surface!(Repo, roles, deadline(), 2) end)
        end
      end

      for limit <- [
            nil,
            "5000",
            System.monotonic_time(:millisecond) - 1,
            System.monotonic_time(:millisecond) + 60_000
          ] do
        assert_raise Catalog.Unavailable, fn ->
          tx(fn -> Catalog.check_function_surface!(Repo, @roles, limit, 2) end)
        end
      end

      for setting <- [
            "SET LOCAL jit=on",
            "SET LOCAL search_path=public",
            "SET LOCAL statement_timeout='4s'"
          ] do
        assert_raise Catalog.Unavailable, fn ->
          tx(fn ->
            q(Repo, setting)
            Catalog.check_function_surface!(Repo, @roles, deadline(), 2)
          end)
        end
      end

      assert check(2) == :function_surface_verified
    end)
  end

  test "v2 consumes one original deadline across successful queries without reset or retries" do
    versioned(2, fn ->
      id = {__MODULE__, make_ref()}
      parent = self()

      :telemetry.attach(
        id,
        [:catalog_v2, :query],
        fn _, _, metadata, _ ->
          if String.starts_with?(metadata.query, "SELECT") do
            send(parent, {:catalog_query, metadata.query})
            Process.sleep(12)
          end
        end,
        nil
      )

      try do
        started = System.monotonic_time(:millisecond)

        error =
          assert_raise Catalog.Unavailable, fn ->
            tx(fn -> Catalog.check_function_surface!(Repo, @roles, started + 125, 2) end)
          end

        assert_redacted(error)
        assert System.monotonic_time(:millisecond) - started < 500
      after
        :telemetry.detach(id)
      end

      queries = drain([])
      assert length(queries) >= 3
      assert length(queries) == length(Enum.uniq(queries))
      assert check(2) == :function_surface_verified
    end)
  end

  test "actual catalog permission error stays redacted in both versions" do
    for version <- [1, 2] do
      versioned(version, fn ->
        mutate(
          "REVOKE SELECT ON pg_catalog.pg_proc FROM PUBLIC",
          "GRANT SELECT ON pg_catalog.pg_proc TO PUBLIC",
          fn -> denied(version) end
        )
      end)
    end
  end

  test "v2 retains deny checks for direct table and column escape" do
    versioned(2, fn ->
      for {role, privilege} <- [
            {"browser_lifecycle", "SELECT"},
            {"browser_ordinary", "SELECT(id)"}
          ] do
        mutate(
          "GRANT #{privilege} ON public.mixer_browser_sessions TO #{role}",
          "REVOKE #{privilege} ON public.mixer_browser_sessions FROM #{role}",
          fn -> denied(2) end
        )
      end
    end)
  end

  test "v2 partial marker still cannot attest relation RLS policy or writer grant admission" do
    versioned(2, fn ->
      mutate(
        "ALTER TABLE public.mixer_browser_sessions NO FORCE ROW LEVEL SECURITY",
        "ALTER TABLE public.mixer_browser_sessions FORCE ROW LEVEL SECURITY",
        fn -> assert check(2) == :function_surface_verified end
      )

      mutate(
        "GRANT DELETE ON public.mixer_browser_sessions TO browser_writer",
        "REVOKE DELETE ON public.mixer_browser_sessions FROM browser_writer",
        fn -> assert check(2) == :function_surface_verified end
      )
    end)
  end

  defp q(repo, sql, params \\ []),
    do: Ecto.Adapters.SQL.query!(repo, sql, params, log: false, timeout: 5_000)

  defp tx(fun) do
    {:ok, result} = Repo.transaction(fun, queue: false, timeout: 5_000)
    result
  end

  defp check(version) do
    tx(fn ->
      if version == :default,
        do: Catalog.check_function_surface!(Repo, @roles, deadline()),
        else: Catalog.check_function_surface!(Repo, @roles, deadline(), version)
    end)
  end

  defp denied(version) do
    error = assert_raise Catalog.Unavailable, fn -> check(version) end
    assert_redacted(error)
  end

  defp assert_redacted(error),
    do:
      assert(
        Map.from_struct(error) == %{
          __exception__: true,
          message: "browser catalog function surface unavailable"
        }
      )

  defp deadline, do: System.monotonic_time(:millisecond) + 4_500
  defp mutate(up, down, fun), do: mutate(up, [], down, [], fun)

  defp mutate(up, up_params, down, down_params, fun) do
    q(Admin, up, up_params)

    try do
      fun.()
    after
      q(Admin, down, down_params)
    end
  end

  defp install, do: Enum.each(ActivationPreparationSchema.statements(), &q(Migration, &1))

  defp upgrade do
    conn = StorageFixture.connection!("browser_admin")

    try do
      Enum.each(
        ActivationPreparationSchema.provisioning_statements(
          "browser_writer",
          "browser_lifecycle",
          "browser_schema_owner"
        ),
        &Postgrex.query!(conn, &1, [])
      )
    after
      GenServer.stop(conn)
    end
  end

  defp remove do
    q(Admin, "DROP FUNCTION IF EXISTS #{@helper}")
    q(Admin, "DROP TYPE IF EXISTS #{@type_name}")
  end

  defp versioned(1, fun), do: fun.()

  defp versioned(2, fun) do
    install()

    try do
      upgrade()
      fun.()
    after
      remove()
    end
  end

  defp drain(acc) do
    receive do
      {:catalog_query, query} -> drain([query | acc])
    after
      0 -> Enum.reverse(acc)
    end
  end
end
