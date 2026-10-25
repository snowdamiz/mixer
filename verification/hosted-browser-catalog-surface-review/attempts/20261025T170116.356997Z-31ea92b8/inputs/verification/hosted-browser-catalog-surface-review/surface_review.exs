Code.require_file("hosted/test/mixer_hosted/browser_auth/storage_fixture.exs")

defmodule MixerHosted.BrowserAuth.SurfaceReviewRepo do
  use Ecto.Repo, otp_app: :surface_review, adapter: Ecto.Adapters.Postgres
end

defmodule MixerHosted.BrowserAuth.SurfaceReview do
  use ExUnit.Case, async: false
  alias MixerHosted.BrowserAuth.{Catalog, CatalogManifest, StorageSchema, StorageFixture}
  alias MixerHosted.BrowserAuth.SurfaceReviewRepo, as: Repo
  alias StorageFixture.{Admin, Migration}
  @roles %{lifecycle_login: "browser_lifecycle", writer: "browser_writer",
    relation_owner: "browser_schema_owner", ordinary_runtime_login: "browser_ordinary"}
  @load "public.mixer_browser_load(bytea,bytea)"

  setup_all do
    for app <- [:ecto_sql, :postgrex, :jason], do: Application.ensure_all_started(app)
    common = [hostname: "127.0.0.1", port: StorageFixture.port(), database: "browser_storage", log: false]
    start_supervised!({Admin, common ++ [username: "browser_admin", pool_size: 2]})
    start_supervised!({Migration, common ++ [username: "browser_admin", pool_size: 2,
      after_connect: fn conn -> Postgrex.query!(conn, "SET ROLE browser_schema_owner", []) end]})
    # Reused accepted fixture installation/provisioning only. Test oracle and
    # adversarial controls below are independently authored for this review.
    StorageFixture.install!()
    StorageFixture.provision!()
    start_supervised!({Repo, common ++ [username: "browser_lifecycle", pool_size: 1,
      telemetry_prefix: [:surface_review], after_connect: fn conn ->
        for sql <- ["SET search_path=pg_catalog", "SET statement_timeout='5s'",
          "SET lock_timeout='500ms'", "SET idle_in_transaction_session_timeout='5s'",
          "SET jit=off", "SET bytea_output=hex"], do: Postgrex.query!(conn, sql, [])
      end]})
    Ecto.Adapters.SQL.query!(Repo, "SELECT 1", [], log: false, timeout: 5_000)
    :ok
  end

  test "baseline returns the named partial result and fixed source agrees with authored SQL" do
    assert check() == :function_surface_verified
    assert not function_exported?(Catalog, :admit!, 0)
    assert map_size(CatalogManifest.functions()) == 18
    for sql <- StorageSchema.statements(), String.starts_with?(sql, "CREATE FUNCTION public.") do
      [header, body, _] = String.split(sql, "$browser$")
      name = header |> String.split("(") |> hd() |> String.replace_prefix("CREATE FUNCTION public.", "")
      assert CatalogManifest.functions()[name].source == body
    end
  end

  test "independent raw eighteen-function projection matches authored source types settings owner ACL and attributes" do
    assert {:ok, :checked} = Admin.transaction(fn ->
      q(Admin, "SET LOCAL search_path=pg_catalog")
      installed = q(Admin, """
      SELECT p.proname::text,oidvectortypes(p.proargtypes),pg_get_function_result(p.oid),
        p.prosrc,p.proconfig,l.lanname::text,o.rolname::text,
        p.prosecdef,p.prokind::text,p.provolatile::text,p.proisstrict,p.proleakproof,
        p.proparallel::text,p.proretset,p.provariadic::oid::bigint,p.pronargdefaults,
        p.proargmodes IS NULL,p.prosupport::oid::bigint,p.probin IS NULL,p.prosqlbody IS NULL,
        p.proargnames
      FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
      JOIN pg_language l ON l.oid=p.prolang JOIN pg_roles o ON o.oid=p.proowner
      WHERE n.nspname='public' AND left(p.proname,14)='mixer_browser_'
      ORDER BY p.proname
      """).rows
      expected = for sql <- StorageSchema.statements(), String.starts_with?(sql, "CREATE FUNCTION public.") do
        [header, source, _] = String.split(sql, "$browser$")
        [declaration | _] = String.split(header, "\n", trim: true)
        [left, result] = String.split(declaration, ") RETURNS ")
        [name, arguments] = String.split(left, "(", parts: 2)
        name = String.replace_prefix(name, "CREATE FUNCTION public.", "")
        names = if arguments == "", do: nil, else: Enum.map(String.split(arguments, ","), fn argument -> hd(String.split(argument)) end)
        [name,String.replace(StorageSchema.signatures()[name], ",", ", "),result,source,
          ["search_path=pg_catalog","statement_timeout=5s","lock_timeout=500ms",
           "idle_in_transaction_session_timeout=5s","bytea_output=hex"],
          "plpgsql","browser_writer",true,"f","v",false,false,"u",false,0,0,true,0,true,true,names]
      end
      assert length(installed) == 18
      assert Enum.sort(installed) == Enum.sort(expected)
      grants = q(Admin, """
      SELECT p.proname::text,CASE WHEN x.grantee=0 THEN 'PUBLIC' ELSE r.rolname::text END,
        x.privilege_type,x.is_grantable
      FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
      CROSS JOIN LATERAL aclexplode(coalesce(p.proacl,acldefault('f',p.proowner))) x
      LEFT JOIN pg_roles r ON r.oid=x.grantee
      WHERE n.nspname='public' AND left(p.proname,14)='mixer_browser_'
      """).rows
      expected_grants = for [name | _] <- expected, do: [name,"browser_writer","EXECUTE",false]
      expected_grants = expected_grants ++ for suffix <- ~w(bootstrap load begin claim provider_reject fail_claim activate logout expire), do: ["mixer_browser_" <> suffix,"browser_lifecycle","EXECUTE",false]
      assert Enum.sort(grants) == Enum.sort(expected_grants)
      :checked
    end, queue: false)
  end

  test "independent raw composite projection matches authored field order types owners and expanded usage" do
    expected = for sql <- StorageSchema.statements(), String.starts_with?(sql, "CREATE TYPE public.mixer_browser_") do
      [prefix, fields] = String.split(sql, " AS (")
      name = String.replace_prefix(prefix, "CREATE TYPE public.", "")
      fields = fields |> String.trim_trailing(")") |> String.split(",") |> Enum.with_index(1)
      {name, for {field,index} <- fields do
        [field_name, type] = String.split(field, " ", parts: 2)
        [name,field_name,type,index]
      end}
    end
    assert length(expected) == 3
    assert {:ok, :checked} = Admin.transaction(fn ->
      q(Admin, "SET LOCAL search_path=pg_catalog")
      actual = q(Admin, """
      SELECT t.typname::text,a.attname::text,format_type(a.atttypid,a.atttypmod),a.attnum::int
      FROM pg_type t JOIN pg_namespace n ON n.oid=t.typnamespace
      JOIN pg_attribute a ON a.attrelid=t.typrelid AND a.attnum>0
      WHERE n.nspname='public' AND t.typname=ANY($1::text[]) ORDER BY t.typname,a.attnum
      """, [Enum.map(expected,&elem(&1,0))]).rows
      assert actual == (expected |> Enum.flat_map(&elem(&1,1)) |> Enum.sort())
      owners = q(Admin, """
      SELECT t.typname::text,r.rolname::text,t.typtype::text,c.relkind::text
      FROM pg_type t JOIN pg_namespace n ON n.oid=t.typnamespace
      JOIN pg_roles r ON r.oid=t.typowner JOIN pg_class c ON c.oid=t.typrelid
      WHERE n.nspname='public' AND t.typname=ANY($1::text[])
      """, [Enum.map(expected,&elem(&1,0))]).rows
      assert Enum.sort(owners) == Enum.sort(for {name,_} <- expected, do: [name,"browser_schema_owner","c","c"])
      actual_grants = q(Admin, """
      SELECT t.typname::text,CASE WHEN x.grantee=0 THEN 'PUBLIC' ELSE r.rolname::text END,
        x.privilege_type,x.is_grantable
      FROM pg_type t JOIN pg_namespace n ON n.oid=t.typnamespace
      CROSS JOIN LATERAL aclexplode(coalesce(t.typacl,acldefault('T',t.typowner))) x
      LEFT JOIN pg_roles r ON r.oid=x.grantee
      WHERE n.nspname='public' AND t.typname=ANY($1::text[])
      """, [Enum.map(expected,&elem(&1,0))]).rows
      expected_grants = for {name,_} <- expected, role <- ~w(browser_schema_owner browser_writer browser_lifecycle), do: [name,role,"USAGE",false]
      assert Enum.sort(actual_grants) == Enum.sort(expected_grants)
      :checked
    end, queue: false)
  end

  test "all eighteen raw source byte changes are detected independently" do
    for {name, expected} <- CatalogManifest.functions() do
      signature = "public.#{name}(#{expected.signature})"
      original = q(Admin, "SELECT prosrc FROM pg_catalog.pg_proc WHERE oid=$1::pg_catalog.text::pg_catalog.regprocedure", [signature]).rows |> hd() |> hd()
      try do
        q(Admin, "UPDATE pg_catalog.pg_proc SET prosrc=prosrc || E'\\n-- review byte drift' WHERE oid=$1::pg_catalog.text::pg_catalog.regprocedure", [signature])
        deny()
      after
        q(Admin, "UPDATE pg_catalog.pg_proc SET prosrc=$2 WHERE oid=$1::pg_catalog.text::pg_catalog.regprocedure", [signature, original])
      end
    end
    assert check() == :function_surface_verified
  end

  test "same body with changed PLpgSQL parameter names is denied" do
    with_catalog_column("proargnames", "ARRAY['renamed_cookie','p_config']::text[]", &deny/0)
  end

  test "optional defaults argument modes support and binary semantics deny" do
    for {column, value} <- [{"pronargdefaults", "1"}, {"provariadic", "17"},
      {"proargmodes", "ARRAY['i','i']::\"char\"[]"}, {"prosupport", "1"},
      {"probin", "'review-marker'"}] do
      with_catalog_column(column, value, &deny/0)
    end
  end

  test "oversized configuration and parameter arrays are invalid markers not accepted prefixes" do
    with_catalog_column("proconfig", "ARRAY['search_path=pg_catalog','statement_timeout=5s','lock_timeout=500ms','idle_in_transaction_session_timeout=5s','review.pad=' || repeat('x',70000)]::text[]", &deny/0)
    with_catalog_column("proargnames", "ARRAY['p_cookie','p_config',repeat('x',70000)]::text[]", &deny/0)
  end

  test "source bounds reject every oversize source even when original is its prefix" do
    with_catalog_column("prosrc", "prosrc || repeat(' ',65537)", &deny/0)
  end

  test "a nineteenth private browser function fails even without executable grants" do
    mutate("CREATE FUNCTION public.mixer_browser_review_extra() RETURNS boolean LANGUAGE sql AS 'SELECT true'; REVOKE ALL ON FUNCTION public.mixer_browser_review_extra() FROM PUBLIC",
      "DROP FUNCTION public.mixer_browser_review_extra()", &deny/0)
  end

  test "all three composite owners and unrelated grantee usage are exact" do
    for type <- Map.keys(CatalogManifest.composites()) do
      mutate("ALTER TYPE public.#{type} OWNER TO review_leaf", "ALTER TYPE public.#{type} OWNER TO browser_schema_owner", &deny/0)
      mutate("GRANT USAGE ON TYPE public.#{type} TO review_leaf", "REVOKE USAGE ON TYPE public.#{type} FROM review_leaf", &deny/0)
    end
  end

  test "same-typed field reordering, explicit collation and added dropped attributes deny" do
    mutate("ALTER TYPE public.mixer_browser_cipher RENAME ATTRIBUTE iv TO review_hold; ALTER TYPE public.mixer_browser_cipher RENAME ATTRIBUTE tag TO iv; ALTER TYPE public.mixer_browser_cipher RENAME ATTRIBUTE review_hold TO tag",
      "ALTER TYPE public.mixer_browser_cipher RENAME ATTRIBUTE tag TO review_hold; ALTER TYPE public.mixer_browser_cipher RENAME ATTRIBUTE iv TO tag; ALTER TYPE public.mixer_browser_cipher RENAME ATTRIBUTE review_hold TO iv", &deny/0)
    mutate("ALTER TYPE public.mixer_browser_cipher ALTER ATTRIBUTE key_id TYPE text COLLATE \"C\"",
      "ALTER TYPE public.mixer_browser_cipher ALTER ATTRIBUTE key_id TYPE text COLLATE \"default\"", &deny/0)
    q(Admin, "ALTER TYPE public.mixer_browser_cipher ADD ATTRIBUTE review_tail text")
    try do
      deny()
      q(Admin, "ALTER TYPE public.mixer_browser_cipher DROP ATTRIBUTE review_tail")
      deny()
    after
      # Direct catalog deletion is a synthetic corruption repair for this one
      # disposable fixture; PostgreSQL retains a dropped composite attribute.
      q(Admin, "DELETE FROM pg_catalog.pg_attribute WHERE attrelid='public.mixer_browser_cipher'::pg_catalog.regclass AND attnum=5")
      q(Admin, "UPDATE pg_catalog.pg_class SET relnatts=4 WHERE oid='public.mixer_browser_cipher'::pg_catalog.regclass")
    end
    assert check() == :function_surface_verified
  end

  test "named owner cannot reach predefined or privileged roles through a chain" do
    mutate("GRANT review_mid TO browser_schema_owner; GRANT review_leaf TO review_mid; GRANT pg_read_all_data TO review_leaf",
      "REVOKE pg_read_all_data FROM review_leaf; REVOKE review_leaf FROM review_mid; REVOKE review_mid FROM browser_schema_owner", &deny/0)
    mutate("GRANT review_mid TO browser_schema_owner; ALTER ROLE review_mid REPLICATION",
      "ALTER ROLE review_mid NOREPLICATION; REVOKE review_mid FROM browser_schema_owner", &deny/0)
  end

  test "ordinary recursive function ownership and database ownership deny despite NOINHERIT" do
    q(Admin, "GRANT review_mid TO browser_ordinary; GRANT review_leaf TO review_mid")
    try do
      mutate("CREATE FUNCTION public.review_owned() RETURNS boolean LANGUAGE sql AS 'SELECT true'; ALTER FUNCTION public.review_owned() OWNER TO review_leaf; REVOKE ALL ON FUNCTION public.review_owned() FROM PUBLIC",
        "DROP FUNCTION public.review_owned()", &deny/0)
      mutate("CREATE DATABASE review_owned_database OWNER review_leaf", "DROP DATABASE review_owned_database", &deny/0)
    after
      q(Admin, "REVOKE review_leaf FROM review_mid; REVOKE review_mid FROM browser_ordinary")
    end
  end

  test "PUBLIC security definer in a second schema denies but closed ACL is harmless" do
    q(Admin, "CREATE SCHEMA review_second; CREATE FUNCTION review_second.escape() RETURNS boolean LANGUAGE sql SECURITY DEFINER AS 'SELECT true'")
    try do
      deny()
      q(Admin, "REVOKE ALL ON FUNCTION review_second.escape() FROM PUBLIC")
      assert check() == :function_surface_verified
      q(Admin, "GRANT EXECUTE ON FUNCTION review_second.escape() TO browser_writer")
      deny()
    after
      q(Admin, "DROP SCHEMA review_second CASCADE")
    end
  end

  test "direct lifecycle view foreign table and column privilege escapes deny" do
    mutate("CREATE VIEW public.review_view AS SELECT id FROM public.mixer_browser_sessions; GRANT SELECT ON public.review_view TO browser_lifecycle",
      "DROP VIEW public.review_view", &deny/0)
    mutate("CREATE FOREIGN DATA WRAPPER review_fdw; CREATE SERVER review_server FOREIGN DATA WRAPPER review_fdw; CREATE FOREIGN TABLE public.review_foreign(id bytea) SERVER review_server; GRANT INSERT ON public.review_foreign TO browser_lifecycle",
      "DROP FOREIGN TABLE public.review_foreign; DROP SERVER review_server; DROP FOREIGN DATA WRAPPER review_fdw", &deny/0)
    mutate("GRANT REFERENCES(id) ON public.mixer_authz_principals TO browser_lifecycle",
      "REVOKE REFERENCES(id) ON public.mixer_authz_principals FROM browser_lifecycle", &deny/0)
  end

  test "membership ceiling rejects a graph even when roles are below the role ceiling" do
    q(Admin, "DO $r$ BEGIN FOR i IN 1..100 LOOP EXECUTE format('CREATE ROLE review_graph_%s NOLOGIN NOINHERIT',i); END LOOP; FOR i IN 1..100 LOOP FOR j IN i+1..100 LOOP EXECUTE format('GRANT review_graph_%s TO review_graph_%s',i,j); END LOOP; END LOOP; END $r$")
    try do
      assert [[count]] = q(Admin, "SELECT count(*) FROM pg_catalog.pg_auth_members").rows
      assert count > 4096
      deny()
    after
      q(Admin, "DO $r$ BEGIN FOR i IN 1..100 LOOP EXECUTE format('DROP ROLE review_graph_%s',i); END LOOP; END $r$")
    end
    assert check() == :function_surface_verified
  end

  test "one original deadline covers successive successful queries with no query replay" do
    id = {:surface_review_delay, make_ref()}
    :ok = :telemetry.attach(id, [:surface_review, :query], &__MODULE__.slow_query/4, self())
    started = System.monotonic_time(:millisecond)
    try do
      deny(fn -> Catalog.check_function_surface!(Repo, @roles, started + 125) end)
      elapsed = System.monotonic_time(:millisecond) - started
      assert elapsed >= 125 and elapsed < 800
      queries = collect_queries([]) |> Enum.filter(&String.starts_with?(&1, "SELECT"))
      assert length(queries) >= 2 and length(queries) <= 4
      assert Enum.uniq(queries) == queries
    after
      :telemetry.detach(id)
    end
    assert check() == :function_surface_verified
  end

  test "wrong transaction identity and local settings deny; settings restore after rollback" do
    assert_raise Catalog.Unavailable, fn -> Catalog.check_function_surface!(Repo, @roles, deadline()) end
    assert {:ok, :denied} = Admin.transaction(fn ->
      q(Admin, "SET LOCAL ROLE browser_lifecycle")
      assert_raise Catalog.Unavailable, fn -> Catalog.check_function_surface!(Admin, @roles, deadline()) end
      :denied
    end, queue: false)
    for sql <- ["SET LOCAL jit=on", "SET LOCAL bytea_output=escape", "SET LOCAL search_path=public", "SET LOCAL lock_timeout='0'"] do
      assert {:error, :review_rollback} = Repo.transaction(fn ->
        q(Repo, sql)
        assert_raise Catalog.Unavailable, fn -> Catalog.check_function_surface!(Repo, @roles, deadline()) end
        Repo.rollback(:review_rollback)
      end, queue: false)
      assert check() == :function_surface_verified
    end
  end

  test "catalog errors retain only the fixed redacted exception" do
    q(Admin, "REVOKE SELECT ON pg_catalog.pg_proc FROM PUBLIC")
    try do
      assert {:error, :review_denied} = Repo.transaction(fn ->
        error = assert_raise Catalog.Unavailable, fn -> Catalog.check_function_surface!(Repo, @roles, deadline()) end
        assert Map.from_struct(error) == %{__exception__: true, message: "browser catalog function surface unavailable"}
        Repo.rollback(:review_denied)
      end, queue: false)
    after
      q(Admin, "GRANT SELECT ON pg_catalog.pg_proc TO PUBLIC")
    end
    assert check() == :function_surface_verified
  end

  test "partial success deliberately does not attest full writer grants or RLS policy" do
    mutate("GRANT DELETE ON public.mixer_browser_sessions TO browser_writer",
      "REVOKE DELETE ON public.mixer_browser_sessions FROM browser_writer", fn -> assert check() == :function_surface_verified end)
    mutate("CREATE POLICY review_permissive ON public.mixer_browser_sessions FOR SELECT TO browser_writer USING(true)",
      "DROP POLICY review_permissive ON public.mixer_browser_sessions", fn -> assert check() == :function_surface_verified end)
  end

  def slow_query(_event, _measurements, metadata, pid) do
    send(pid, {:review_query, metadata.query})
    if String.starts_with?(metadata.query, "SELECT"), do: Process.sleep(55)
  end
  defp collect_queries(acc) do
    receive do
      {:review_query, query} -> collect_queries(acc ++ [query])
    after
      0 -> acc
    end
  end
  defp q(repo, sql, params \\ []) do
    statements = if params == [] and not String.starts_with?(sql, "DO "), do: String.split(sql, ";", trim: true), else: [sql]
    Enum.reduce(statements, nil, fn statement, _ -> Ecto.Adapters.SQL.query!(repo, statement, params, queue: false, timeout: 5_000, log: false) end)
  end
  defp deadline, do: System.monotonic_time(:millisecond) + 4_500
  defp check do
    assert {:ok, value} = Repo.transaction(fn -> Catalog.check_function_surface!(Repo, @roles, deadline()) end, queue: false, timeout: 5_000)
    value
  end
  defp deny(fun \\ fn -> Catalog.check_function_surface!(Repo, @roles, deadline()) end) do
    assert {:ok, :denied} = Repo.transaction(fn ->
      assert_raise Catalog.Unavailable, fun
      :denied
    end, queue: false, timeout: 5_000)
  end
  defp mutate(up, down, fun) do
    q(Admin, up)
    try do
      fun.()
    after
      q(Admin, down)
    end
    assert check() == :function_surface_verified
  end
  defp with_catalog_column(column, expression, fun) do
    [[original]] = q(Admin, "SELECT #{column} FROM pg_catalog.pg_proc WHERE oid='#{@load}'::pg_catalog.regprocedure").rows
    try do
      q(Admin, "UPDATE pg_catalog.pg_proc SET #{column}=#{expression} WHERE oid='#{@load}'::pg_catalog.regprocedure")
      fun.()
    after
      q(Admin, "UPDATE pg_catalog.pg_proc SET #{column}=$1 WHERE oid='#{@load}'::pg_catalog.regprocedure", [original])
    end
    assert check() == :function_surface_verified
  end
end
