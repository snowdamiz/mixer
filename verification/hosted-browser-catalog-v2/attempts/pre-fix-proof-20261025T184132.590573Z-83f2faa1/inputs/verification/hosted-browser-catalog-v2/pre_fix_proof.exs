Code.require_file("hosted/test/mixer_hosted/browser_auth/storage_fixture.exs")

defmodule MixerHosted.BrowserAuth.CatalogV2PreFixRepo do
  use Ecto.Repo, otp_app: :catalog_v2_proof, adapter: Ecto.Adapters.Postgres
end

defmodule MixerHosted.BrowserAuth.CatalogV2PreFixProof do
  use ExUnit.Case, async: false
  alias MixerHosted.BrowserAuth.{Catalog, StorageFixture}
  alias MixerHosted.BrowserAuth.StorageFixture.{Admin, Migration}
  alias MixerHosted.BrowserAuth.CatalogV2PreFixRepo, as: Repo

  @roles %{
    lifecycle_login: "browser_lifecycle",
    writer: "browser_writer",
    relation_owner: "browser_schema_owner",
    ordinary_runtime_login: "browser_ordinary"
  }

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

  test "pre-fix v1 incorrectly admits an extra closed browser standalone composite" do
    q(Admin, "CREATE TYPE public.mixer_browser_extra AS (value text)")

    try do
      q(Admin, "REVOKE ALL ON TYPE public.mixer_browser_extra FROM PUBLIC")
      assert check() == :function_surface_verified
    after
      q(Admin, "DROP TYPE public.mixer_browser_extra")
    end
  end

  test "pre-fix v1 incorrectly admits preparation type only without helper" do
    q(Admin, "CREATE TYPE public.mixer_browser_access_evidence AS (profile_id text)")

    try do
      q(Admin, "REVOKE ALL ON TYPE public.mixer_browser_access_evidence FROM PUBLIC")
      assert check() == :function_surface_verified
    after
      q(Admin, "DROP TYPE public.mixer_browser_access_evidence")
    end
  end

  test "pre-fix v1 incorrectly admits function and type ACL grantor drift" do
    [[function_acl]] =
      q(
        Admin,
        "SELECT proacl::text FROM pg_proc WHERE oid='public.mixer_browser_load(bytea,bytea)'::regprocedure"
      ).rows

    [[type_acl]] =
      q(
        Admin,
        "SELECT typacl::text FROM pg_type WHERE oid='public.mixer_browser_cipher'::regtype"
      ).rows

    try do
      q(
        Admin,
        "UPDATE pg_proc SET proacl=ARRAY['browser_writer=X/browser_admin','browser_lifecycle=X/browser_admin']::aclitem[] WHERE oid='public.mixer_browser_load(bytea,bytea)'::regprocedure"
      )

      q(
        Admin,
        "UPDATE pg_type SET typacl=ARRAY['browser_schema_owner=U/browser_admin','browser_writer=U/browser_admin','browser_lifecycle=U/browser_admin']::aclitem[] WHERE oid='public.mixer_browser_cipher'::regtype"
      )

      assert check() == :function_surface_verified
    after
      Ecto.Adapters.SQL.query!(
        Admin,
        "UPDATE pg_proc SET proacl=$1::text::aclitem[] WHERE oid='public.mixer_browser_load(bytea,bytea)'::regprocedure",
        [function_acl],
        log: false
      )

      Ecto.Adapters.SQL.query!(
        Admin,
        "UPDATE pg_type SET typacl=$1::text::aclitem[] WHERE oid='public.mixer_browser_cipher'::regtype",
        [type_acl],
        log: false
      )
    end

    assert check() == :function_surface_verified
  end

  defp q(repo, sql), do: Ecto.Adapters.SQL.query!(repo, sql, [], log: false)

  defp check do
    {:ok, result} =
      Repo.transaction(
        fn ->
          Catalog.check_function_surface!(
            Repo,
            @roles,
            System.monotonic_time(:millisecond) + 4_500
          )
        end,
        queue: false,
        timeout: 5_000
      )

    result
  end
end
