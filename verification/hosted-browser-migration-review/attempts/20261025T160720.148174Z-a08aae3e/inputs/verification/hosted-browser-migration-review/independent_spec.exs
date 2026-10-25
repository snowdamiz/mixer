{:ok, _} = Application.ensure_all_started(:ecto_sql)
{:ok, _} = Application.ensure_all_started(:postgrex)
Logger.configure(level: :warning)

defmodule MixerBrowserMigrationReview.Owner do
  use Ecto.Repo, otp_app: :migration_review, adapter: Ecto.Adapters.Postgres
end

defmodule MixerBrowserMigrationReview.Runtime do
  use Ecto.Repo, otp_app: :migration_review, adapter: Ecto.Adapters.Postgres
end

defmodule MixerBrowserMigrationReview.Test do
  use ExUnit.Case, async: false
  alias MixerBrowserMigrationReview.{Owner, Runtime}

  @versions [
    20_261_024_000_000,
    20_261_025_000_000,
    20_261_025_000_001,
    20_261_025_000_002,
    20_261_025_000_003,
    20_261_025_000_004,
    20_261_025_000_005,
    20_261_025_000_006,
    20_261_025_000_007
  ]
  @tables ~w(sessions session_vault oidc_attempts session_events)

  setup_all do
    for {repo, user} <- [{Owner, "migration_owner"}, {Runtime, "migration_runtime"}] do
      start_supervised!(
        {repo,
         hostname: "127.0.0.1",
         port: String.to_integer(System.fetch_env!("MIXER_BROWSER_MIGRATION_PORT")),
         database: "browser_migrations",
         username: user,
         ssl: false,
         pool_size: 2,
         log: false}
      )
    end

    :ok
  end

  test "real migration topology and restricted calls survive full and six-step cycles" do
    path = Path.join(System.fetch_env!("MIXER_REVIEW_ROOT"), "hosted/priv/repo/migrations")
    before_roles = Owner.query!("SELECT oid,rolname FROM pg_roles ORDER BY oid").rows

    assert [[false, false, false, false]] =
             Owner.query!(
               "SELECT rolsuper,rolbypassrls,rolcreaterole,rolcreatedb FROM pg_roles WHERE rolname=current_user"
             ).rows

    assert @versions == Ecto.Migrator.run(Owner, path, :up, all: true, log: false)
    assert [] == Ecto.Migrator.run(Owner, path, :up, all: true, log: false)

    assert Enum.map(@versions, &[&1]) ==
             Owner.query!("SELECT version FROM schema_migrations ORDER BY version").rows

    assert_inert_runtime()

    # These mutations are confined to this disposable database. They demonstrate
    # that permissions and RLS flags are independently observable regressions.
    Owner.query!("GRANT EXECUTE ON FUNCTION public.mixer_browser_load(bytea,bytea) TO PUBLIC")

    assert [[true]] ==
             Owner.query!(
               "SELECT has_function_privilege('migration_runtime','public.mixer_browser_load(bytea,bytea)','EXECUTE')"
             ).rows

    assert [[nil]] ==
             Runtime.query!("SELECT public.mixer_browser_load(NULL::bytea,NULL::bytea)").rows

    Owner.query!("REVOKE EXECUTE ON FUNCTION public.mixer_browser_load(bytea,bytea) FROM PUBLIC")
    Owner.query!("ALTER TABLE mixer_browser_sessions DISABLE ROW LEVEL SECURITY")

    assert [[false, true]] ==
             Owner.query!(
               "SELECT relrowsecurity,relforcerowsecurity FROM pg_class WHERE oid='public.mixer_browser_sessions'::regclass"
             ).rows

    Owner.query!("ALTER TABLE mixer_browser_sessions ENABLE ROW LEVEL SECURITY")
    assert_inert_runtime()

    Owner.query!("""
    INSERT INTO mixer_builds (id,organization_id,project_id,application_id,build_id,platform,request_key,revision,journal,inserted_at,updated_at)
    VALUES ('00000000-0000-4000-8000-000000000002','review-org','review-project','review-app','review-build','android','review-request',0,'{}',now(),now())
    """)

    build = Owner.query!("SELECT * FROM mixer_builds").rows
    unload()
    latest = Enum.drop(@versions, 3)
    assert Enum.reverse(latest) == Ecto.Migrator.run(Owner, path, :down, step: 6, log: false)

    assert Enum.map(Enum.take(@versions, 3), &[&1]) ==
             Owner.query!("SELECT version FROM schema_migrations ORDER BY version").rows

    assert_browser_absent()

    assert [[nil]] ==
             Owner.query!("SELECT to_regclass('public.mixer_build_fleet_capacity')::text").rows

    assert build == Owner.query!("SELECT * FROM mixer_builds").rows
    unload()
    assert latest == Ecto.Migrator.run(Owner, path, :up, all: true, log: false)
    assert build == Owner.query!("SELECT * FROM mixer_builds").rows
    assert_inert_runtime()
    unload()
    assert Enum.reverse(@versions) == Ecto.Migrator.run(Owner, path, :down, all: true, log: false)
    assert [] == Owner.query!("SELECT version FROM schema_migrations").rows
    assert_browser_absent()
    unload()
    assert @versions == Ecto.Migrator.run(Owner, path, :up, all: true, log: false)
    assert_inert_runtime()
    assert before_roles == Owner.query!("SELECT oid,rolname FROM pg_roles ORDER BY oid").rows
  end

  defp assert_inert_runtime do
    for suffix <- @tables do
      table = "mixer_browser_" <> suffix

      assert [[true, true]] ==
               Owner.query!(
                 "SELECT relrowsecurity,relforcerowsecurity FROM pg_class WHERE oid=$1::text::regclass",
                 ["public." <> table]
               ).rows

      assert [[0]] ==
               Owner.query!(
                 "SELECT count(*) FROM pg_policies WHERE schemaname='public' AND tablename=$1",
                 [table]
               ).rows

      [[column]] =
        Owner.query!(
          "SELECT attname FROM pg_attribute WHERE attrelid=$1::text::regclass AND attnum>0 AND NOT attisdropped ORDER BY attnum LIMIT 1",
          ["public." <> table]
        ).rows

      for sql <- [
            "SELECT 1 FROM #{table} LIMIT 0",
            "INSERT INTO #{table} DEFAULT VALUES",
            "UPDATE #{table} SET #{column}=#{column} WHERE false",
            "DELETE FROM #{table} WHERE false",
            "TRUNCATE #{table}"
          ] do
        assert {:error, %Postgrex.Error{postgres: %{code: :insufficient_privilege}}} =
                 Runtime.query(sql)
      end
    end

    for {name, signature} <- MixerHosted.BrowserAuth.StorageSchema.public_signatures() do
      args = signature |> String.split(",") |> Enum.map_join(",", &("NULL::" <> &1))

      assert {:error, %Postgrex.Error{postgres: %{code: :insufficient_privilege}}} =
               Runtime.query("SELECT public.#{name}(#{args})")
    end
  end

  defp assert_browser_absent do
    assert [[0]] ==
             Owner.query!(
               "SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' AND c.relname LIKE 'mixer_browser_%'"
             ).rows

    assert [[0]] ==
             Owner.query!(
               "SELECT count(*) FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname='public' AND p.proname LIKE 'mixer_browser_%'"
             ).rows

    assert [[0]] ==
             Owner.query!(
               "SELECT count(*) FROM pg_type t JOIN pg_namespace n ON n.oid=t.typnamespace WHERE n.nspname='public' AND (t.typname LIKE 'mixer_browser_%' OR t.typname LIKE '_mixer_browser_%')"
             ).rows
  end

  defp unload do
    for file <-
          Path.wildcard(
            Path.join(System.fetch_env!("MIXER_REVIEW_ROOT"), "hosted/priv/repo/migrations/*.exs")
          ) do
      ast = file |> File.read!() |> Code.string_to_quoted!()
      {:defmodule, _, [name, _]} = ast
      module = Module.concat(elem(name, 2))
      :code.purge(module)
      :code.delete(module)
    end
  end
end
