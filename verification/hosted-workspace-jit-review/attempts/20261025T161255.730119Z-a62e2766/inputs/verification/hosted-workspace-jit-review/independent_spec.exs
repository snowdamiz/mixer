defmodule JitReview.Admin do
  use Ecto.Repo, otp_app: :jit_review, adapter: Ecto.Adapters.Postgres
end

defmodule JitReview.Migration do
  use Ecto.Repo, otp_app: :jit_review, adapter: Ecto.Adapters.Postgres
end

defmodule JitReview.Runtime do
  use Ecto.Repo, otp_app: :jit_review, adapter: Ecto.Adapters.Postgres
end

defmodule JitReview.IndependentSpec do
  use ExUnit.Case, async: false
  alias MixerHosted.Authorization.Postgres.Session
  alias JitReview.{Admin, Migration, Runtime}

  setup_all do
    base = [
      hostname: "127.0.0.1",
      port: String.to_integer(System.fetch_env!("JIT_REVIEW_PORT")),
      database: "mixer_jit_review",
      ssl: false,
      log: false
    ]

    start_supervised!({Admin, base ++ [username: "jit_review_admin", pool_size: 1]})

    start_supervised!(
      {Migration,
       base ++
         [
           username: "jit_review_admin",
           pool_size: 2,
           after_connect: fn conn -> Postgrex.query!(conn, "SET ROLE jit_review_owner", []) end
         ]}
    )

    start_supervised!(
      {Runtime,
       base ++ [username: "jit_review_runtime", pool_size: 1, telemetry_prefix: [:jit_review]]}
    )

    for {version, module} <- [
          {20_261_025_000_003, MixerHosted.Repo.Migrations.AddCustomerAuthorization},
          {20_261_025_000_004, MixerHosted.Repo.Migrations.AddAuthorizationStateRevisions}
        ],
        do: assert(:ok = Ecto.Migrator.up(Migration, version, module, log: false))

    for table <-
          ~w(profiles principals bindings families credentials organizations projects applications environments organization_heads project_heads memberships),
        do: q(Admin, "GRANT SELECT ON public.mixer_authz_#{table} TO jit_review_runtime")

    for table <- ~w(profiles principals families credentials organization_heads project_heads),
        do:
          q(
            Admin,
            "GRANT EXECUTE ON FUNCTION public.mixer_authz_lock_#{table}() TO jit_review_runtime"
          )

    q(
      Admin,
      "INSERT INTO public.mixer_authz_profiles(id,version,issuer,client_id,identity_class,active) VALUES('review',1,'https://review.invalid','review','human',true)"
    )

    q(Admin, "INSERT INTO public.mixer_authz_principals VALUES('review-person','human',true,0,1)")

    q(
      Admin,
      "INSERT INTO public.mixer_authz_bindings(profile_id,profile_version,subject,identity_class,principal_id,active) VALUES('review',1,'review-subject','human','review-person',true)"
    )

    q(
      Admin,
      "INSERT INTO public.mixer_authz_families VALUES('review-family','review',1,'review-person',true,0,NULL,1)"
    )

    q(
      Admin,
      "INSERT INTO public.mixer_authz_credentials VALUES('review',1,'review-token','review-person','review-family',true,0,NULL,1)"
    )

    :ok
  end

  test "same backend restores nondefault session JIT and all bounds after successful preparation" do
    for prior <- ~w(on off) do
      checked_out(prior, fn before ->
        assert {:ok, %{principal_id: "review-person", family_id: "review-family"}} =
                 Runtime.transaction(
                   fn ->
                     result = Session.prepare_identity!(Runtime, identity())
                     assert_local(before)
                     result
                   end, timeout: 5_000, queue: false)

        assert settings() == before
        record("success-#{prior}", before)
      end)
    end
  end

  test "same backend restores nondefault settings on explicit owner rollback" do
    for prior <- ~w(on off) do
      checked_out(prior, fn before ->
        assert {:error, :review_rollback} =
                 Runtime.transaction(
                   fn ->
                     Session.prepare_identity!(Runtime, identity())
                     assert_local(before)
                     Runtime.rollback(:review_rollback)
                   end, timeout: 5_000, queue: false)

        assert settings() == before
        record("explicit-rollback-#{prior}", before)
      end)
    end
  end

  test "identity-denial rollback restores the same backend and permits its next transaction" do
    checked_out("on", fn before ->
      assert {:error, :unauthenticated} =
               Runtime.transaction(
                 fn ->
                   Session.prepare_identity!(Runtime, %{identity() | credential_ref: "missing"})
                 end, timeout: 5_000, queue: false)

      assert settings() == before

      assert {:ok, :reused} =
               Runtime.transaction(
                 fn ->
                   Session.prepare_identity!(Runtime, identity())
                   assert_local(before)
                   :reused
                 end, timeout: 5_000, queue: false)

      assert settings() == before
      record("identity-denied-and-reused", before)
    end)
  end

  test "PostgreSQL error abort restores the same backend and all nondefault settings" do
    checked_out("on", fn before ->
      assert_raise Postgrex.Error, fn ->
        Runtime.transaction(
          fn ->
            Session.prepare_identity!(Runtime, identity())
            assert_local(before)
            q(Runtime, "SELECT 1/0")
          end, timeout: 5_000, queue: false)
      end

      assert settings() == before
      record("sql-error", before)
    end)
  end

  test "an actual effective-setting fault denies before topology and restores the same connection" do
    owner = self()
    handler = {__MODULE__, make_ref()}

    :ok =
      :telemetry.attach(
        handler,
        [:jit_review, :query],
        fn _, _, metadata, _ ->
          if self() == owner do
            send(owner, {:query, metadata.query})
            if metadata.query == "SET LOCAL jit = off", do: q(Runtime, "SET LOCAL jit = on")
          end
        end,
        nil
      )

    try do
      checked_out("on", fn before ->
        assert {:error, :authorization_unavailable} =
                 Runtime.transaction(
                   fn ->
                     Session.prepare_identity!(Runtime, identity())
                     flunk("faulted preparation returned authority")
                   end, timeout: 5_000, queue: false)

        assert settings() == before
        queries = queries([])
        assert "SET LOCAL jit = off" in queries
        assert "SET LOCAL jit = on" in queries
        assert "SELECT pg_catalog.current_setting('jit')" in queries
        refute Enum.any?(queries, &String.contains?(&1, "current_user = session_user"))
        record("effective-mismatch", before)
      end)
    after
      :telemetry.detach(handler)
    end
  end

  test "outside-transaction call fails without modifying any session setting" do
    checked_out("on", fn before ->
      assert_raise RuntimeError, "cannot call rollback outside of transaction", fn ->
        Session.prepare_identity!(Runtime, identity())
      end

      assert settings() == before
      record("outside-owner-transaction", before)
    end)
  end

  defp identity,
    do: %{
      profile_id: "review",
      profile_version: 1,
      issuer: "https://review.invalid",
      client_id: "review",
      subject: "review-subject",
      credential_ref: "review-token"
    }

  defp q(repo, sql), do: Ecto.Adapters.SQL.query!(repo, sql, [], log: false)

  defp checked_out(prior, fun) do
    Runtime.checkout(
      fn ->
        try do
          for sql <- [
                "SET SESSION jit = #{prior}",
                "SET SESSION statement_timeout = '4321ms'",
                "SET SESSION lock_timeout = '321ms'",
                "SET SESSION idle_in_transaction_session_timeout = '4321ms'"
              ],
              do: q(Runtime, sql)

          assert [["jit_review_runtime", "jit_review_runtime", false, false, false]] =
                   q(
                     Runtime,
                     "SELECT current_user,session_user,rolsuper,rolbypassrls,pg_catalog.pg_has_role(current_user,'jit_review_owner','MEMBER') FROM pg_catalog.pg_roles WHERE rolname=current_user"
                   ).rows

          fun.(settings())
        after
          for setting <-
                ~w(jit statement_timeout lock_timeout idle_in_transaction_session_timeout),
              do: q(Runtime, "RESET #{setting}")
        end
      end, timeout: 5_000, queue: false)
  end

  defp settings do
    [row] =
      q(
        Runtime,
        "SELECT pg_backend_pid(),current_setting('jit'),current_setting('statement_timeout'),current_setting('lock_timeout'),current_setting('idle_in_transaction_session_timeout'),current_setting('transaction_isolation')"
      ).rows

    row
  end

  defp assert_local([pid | _]),
    do: assert(settings() == [pid, "off", "5s", "500ms", "5s", "read committed"])

  defp queries(acc) do
    receive do
      {:query, query} -> queries([query | acc])
    after
      0 -> Enum.reverse(acc)
    end
  end

  defp record(name, before),
    do:
      File.write!(
        System.fetch_env!("JIT_REVIEW_SETTINGS"),
        Jason.encode!(%{case: name, before: before, after: settings()}) <> "\n",
        [:append]
      )
end

