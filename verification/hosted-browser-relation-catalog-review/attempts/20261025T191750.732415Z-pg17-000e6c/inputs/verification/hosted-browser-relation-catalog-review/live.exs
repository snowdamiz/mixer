# Independent review controls; ordinary installer is reused, not producer tests.
Application.ensure_all_started(:ecto_sql)
Application.ensure_all_started(:postgrex)
Code.require_file("hosted/lib/mixer_hosted/browser_auth/relation_manifest.ex")
Code.require_file("hosted/lib/mixer_hosted/browser_auth/relation_catalog.ex")

defmodule RelationReview.Admin do
  use Ecto.Repo, otp_app: :relation_review, adapter: Ecto.Adapters.Postgres
end

defmodule RelationReview.Login do
  use Ecto.Repo, otp_app: :relation_review, adapter: Ecto.Adapters.Postgres
end

defmodule RelationReview.Wire do
  def in_transaction?, do: true
end

defmodule RelationReview.Adapter do
  def query(_, sql, params, opts) do
    true = Keyword.keys(opts) |> Enum.sort() == [:log, :queue, :timeout]
    false = Keyword.fetch!(opts, :queue)
    false = Keyword.fetch!(opts, :log)
    timeout = Keyword.fetch!(opts, :timeout)
    true = is_integer(timeout) and timeout > 0 and timeout <= 5000
    index = Process.get(:review_index, 0)
    Process.put(:review_index, index + 1)
    Process.put(:review_options, [opts | Process.get(:review_options, [])])

    if Process.get(:review_replay) do
      {^sql, ^params, result} = Enum.fetch!(Process.get(:review_capture), index)
      Process.get(:review_fault).(index, result)
    else
      result = Ecto.Adapters.SQL.query!(RelationReview.Login, sql, params, opts)
      Process.put(:review_rows, [{sql, params, result} | Process.get(:review_rows, [])])
      {:ok, result}
    end
  end
end

defmodule RelationReview do
  alias MixerHosted.BrowserAuth.RelationCatalog, as: Product

  @roles %{
    lifecycle_login: "browser_lifecycle",
    writer: "browser_writer",
    relation_owner: "browser_schema_owner",
    ordinary_runtime_login: "browser_ordinary"
  }
  @targets ~w(mixer_browser_sessions mixer_browser_session_vault mixer_browser_oidc_attempts mixer_browser_session_events mixer_authz_profiles mixer_authz_principals mixer_authz_bindings mixer_authz_families mixer_authz_credentials)
  def assert(true), do: :ok
  def assert(_), do: raise("independent review assertion failed")
  def query(repo, sql), do: Ecto.Adapters.SQL.query!(repo, sql, [], log: false, query_type: :text)

  def record(name, fun) do
    IO.puts("review: " <> name)
    value = fun.()
    Process.put(:review_checks, [%{name: name, passed: true} | Process.get(:review_checks, [])])
    value
  end

  def policy(repo) do
    for sql <- [
          "SET LOCAL search_path=pg_catalog",
          "SET LOCAL jit=off",
          "SET LOCAL statement_timeout='5s'",
          "SET LOCAL lock_timeout='500ms'",
          "SET LOCAL idle_in_transaction_session_timeout='5s'",
          "SET LOCAL bytea_output=hex"
        ],
        do: query(repo, sql)
  end

  def check(repo, deadline \\ nil),
    do:
      Product.check_relation_surface!(
        repo,
        @roles,
        deadline || System.monotonic_time(:millisecond) + 5000
      )

  def unavailable(fun) do
    try do
      fun.()
      raise "checker accepted independent negative control"
    rescue
      exception in Product.Unavailable ->
        assert(Exception.message(exception) === "browser storage unavailable")

        assert(
          Map.from_struct(exception) === %{
            __exception__: true,
            message: "browser storage unavailable"
          }
        )
    end
  end

  def baseline do
    assert(
      RelationReview.Login.transaction(
        fn ->
          policy(RelationReview.Login)
          check(RelationReview.Login)
        end, log: false) === {:ok, :relation_surface_verified}
    )
  end

  def fact(name, sql) do
    result = Ecto.Adapters.SQL.query!(RelationReview.Admin, sql, [], log: false)
    assert(result.rows === [[true]])

    Process.put(:review_facts, [
      %{name: name, sql: sql, result: true} | Process.get(:review_facts, [])
    ])
  end

  def mutation(name, sql, effect, accept \\ false) do
    record(name, fn ->
      assert(
        RelationReview.Admin.transaction(
          fn ->
            query(RelationReview.Admin, sql)
            fact(name, effect)
            query(RelationReview.Admin, "SET LOCAL SESSION AUTHORIZATION browser_lifecycle")
            policy(RelationReview.Admin)

            if accept do
              assert(check(RelationReview.Admin) === :relation_surface_verified)
            else
              unavailable(fn -> check(RelationReview.Admin) end)
            end

            RelationReview.Admin.rollback(:independent_restoration)
          end,
          log: false
        ) === {:error, :independent_restoration}
      )

      baseline()
    end)
  end

  def replay(fault, deadline \\ nil) do
    Process.put(:review_replay, true)
    Process.put(:review_index, 0)
    Process.put(:review_options, [])
    Process.put(:review_fault, fault)

    try do
      check(RelationReview.Wire, deadline)
    after
      Process.put(:review_replay, false)
    end
  end

  def run do
    record("genuine lifecycle-login baseline", &baseline/0)

    record("unchanged admin checkout/session authorization baseline", fn ->
      assert(
        RelationReview.Admin.transaction(
          fn ->
            query(RelationReview.Admin, "SET LOCAL SESSION AUTHORIZATION browser_lifecycle")
            policy(RelationReview.Admin)
            assert(check(RelationReview.Admin) === :relation_surface_verified)
            RelationReview.Admin.rollback(:independent_restoration)
          end,
          log: false
        ) === {:error, :independent_restoration}
      )
    end)

    targets = Enum.map_join(@targets, ",", &("'public." <> &1 <> "'::regclass"))
    cte = "WITH targets AS (SELECT unnest(ARRAY[" <> targets <> "]) AS oid) "

    summary =
      cte <>
        "SELECT json_build_object('relations',(SELECT count(*) FROM targets),'columns',(SELECT count(*) FROM pg_attribute WHERE attrelid IN(SELECT oid FROM targets) AND attnum>0),'constraints',(SELECT count(*) FROM pg_constraint WHERE conrelid IN(SELECT oid FROM targets) OR confrelid IN(SELECT oid FROM targets)),'checks',(SELECT count(*) FROM pg_constraint WHERE conrelid IN(SELECT oid FROM targets) AND contype='c'),'primary',(SELECT count(*) FROM pg_constraint WHERE conrelid IN(SELECT oid FROM targets) AND contype='p'),'unique',(SELECT count(*) FROM pg_constraint WHERE conrelid IN(SELECT oid FROM targets) AND contype='u'),'foreign',(SELECT count(*) FROM pg_constraint WHERE (conrelid IN(SELECT oid FROM targets) OR confrelid IN(SELECT oid FROM targets)) AND contype='f'),'indexes',(SELECT count(*) FROM pg_index WHERE indrelid IN(SELECT oid FROM targets)),'policies',(SELECT count(*) FROM pg_policy WHERE polrelid IN(SELECT oid FROM targets)))"

    record("independent full-boundary census", fn ->
      %{rows: [[actual]]} =
        Ecto.Adapters.SQL.query!(RelationReview.Admin, summary, [], log: false)

      assert(
        actual === %{
          "relations" => 9,
          "columns" => 124,
          "constraints" => 109,
          "checks" => 80,
          "primary" => 9,
          "unique" => 4,
          "foreign" => 12,
          "indexes" => 14,
          "policies" => 32
        }
      )

      Process.put(:review_census, actual)
    end)

    record("independent complete numeric RI and index backlinks", fn ->
      fact(
        "all twelve FK groups: four numeric function/index/endpoint links",
        cte <>
          "SELECT count(*)=12 AND bool_and((SELECT count(*)=4 AND bool_and(t.tgconstrindid=k.conindid AND NOT t.tgdeferrable AND NOT t.tginitdeferred AND t.tgenabled='O' AND t.tgisinternal AND ((t.tgfoid='pg_catalog.\"RI_FKey_check_ins\"()'::regprocedure AND t.tgtype=5 AND t.tgrelid=k.conrelid AND t.tgconstrrelid=k.confrelid) OR (t.tgfoid='pg_catalog.\"RI_FKey_check_upd\"()'::regprocedure AND t.tgtype=17 AND t.tgrelid=k.conrelid AND t.tgconstrrelid=k.confrelid) OR (t.tgfoid='pg_catalog.\"RI_FKey_noaction_del\"()'::regprocedure AND t.tgtype=9 AND t.tgrelid=k.confrelid AND t.tgconstrrelid=k.conrelid) OR (t.tgfoid='pg_catalog.\"RI_FKey_noaction_upd\"()'::regprocedure AND t.tgtype=17 AND t.tgrelid=k.confrelid AND t.tgconstrrelid=k.conrelid))) FROM pg_trigger t WHERE t.tgconstraint=k.oid)) FROM pg_constraint k WHERE k.contype='f' AND(k.conrelid IN(SELECT oid FROM targets) OR k.confrelid IN(SELECT oid FROM targets))"
      )
    end)

    record("independent both incoming FK source identities", fn ->
      fact(
        "exact external referencing set",
        cte <>
          "SELECT array_agg(conrelid::regclass::text ORDER BY conrelid::regclass::text)=ARRAY['mixer_authz_memberships','mixer_customer_idempotency'] FROM pg_constraint WHERE contype='f' AND confrelid IN(SELECT oid FROM targets) AND conrelid NOT IN(SELECT oid FROM targets)"
      )
    end)

    mutation(
      "incoming RI wrong constraint group",
      "UPDATE pg_trigger t SET tgconstraint=(SELECT oid FROM pg_constraint WHERE conrelid='public.mixer_authz_memberships'::regclass AND confrelid='public.mixer_authz_principals'::regclass) WHERE t.tgrelid='public.mixer_customer_idempotency'::regclass AND t.tgisinternal AND t.tgtype=5 AND t.tgconstraint=(SELECT oid FROM pg_constraint WHERE conrelid='public.mixer_customer_idempotency'::regclass AND confrelid='public.mixer_authz_principals'::regclass)",
      "SELECT count(*)=2 FROM pg_trigger t JOIN pg_constraint k ON k.oid=t.tgconstraint WHERE k.conrelid='public.mixer_authz_memberships'::regclass AND k.confrelid='public.mixer_authz_principals'::regclass AND t.tgtype=5"
    )

    mutation(
      "foreign-key child equality vector empty",
      "UPDATE pg_constraint SET conffeqop=ARRAY[]::oid[] WHERE conrelid='public.mixer_browser_sessions'::regclass AND contype='f'",
      "SELECT count(*)=2 AND bool_and(cardinality(conffeqop)=0) FROM pg_constraint WHERE conrelid='public.mixer_browser_sessions'::regclass AND contype='f'"
    )

    mutation(
      "index collation numeric link disagrees",
      "UPDATE pg_index SET indcollation=((SELECT oid::text FROM pg_collation WHERE collname='C' AND collnamespace='pg_catalog'::regnamespace)||' 0')::oidvector WHERE indexrelid='public.mixer_authz_profiles_pkey'::regclass",
      "SELECT i.indcollation[0]<>a.attcollation AND i.indcollation[1]=0 FROM pg_index i JOIN pg_attribute a ON a.attrelid=i.indrelid AND a.attname='id' WHERE i.indexrelid='public.mixer_authz_profiles_pkey'::regclass"
    )

    mutation(
      "explicit empty immutable column ACL remains distinct from NULL",
      "UPDATE pg_attribute SET attacl=ARRAY[]::aclitem[] WHERE attrelid='public.mixer_browser_sessions'::regclass AND attname='id'",
      "SELECT attacl IS NOT NULL AND cardinality(attacl)=0 FROM pg_attribute WHERE attrelid='public.mixer_browser_sessions'::regclass AND attname='id'"
    )

    mutation(
      "inconsistent fast default hasmissing with NULL value",
      "UPDATE pg_attribute SET attmissingval=NULL WHERE attrelid='public.mixer_authz_profiles'::regclass AND attname='state_revision'",
      "SELECT atthasmissing AND attmissingval IS NULL FROM pg_attribute WHERE attrelid='public.mixer_authz_profiles'::regclass AND attname='state_revision'"
    )

    mutation(
      "identity metadata has no default equivalence",
      "UPDATE pg_attribute SET attidentity='a' WHERE attrelid='public.mixer_browser_sessions'::regclass AND attname='epoch'",
      "SELECT attidentity='a' FROM pg_attribute WHERE attrelid='public.mixer_browser_sessions'::regclass AND attname='epoch'"
    )

    mutation(
      "owner raw ACL grant option denied despite implicit rights",
      "GRANT SELECT ON public.mixer_browser_sessions TO browser_schema_owner WITH GRANT OPTION",
      "SELECT bool_or(is_grantable) FROM pg_class c CROSS JOIN LATERAL aclexplode(c.relacl) a WHERE c.oid='public.mixer_browser_sessions'::regclass AND a.grantee='browser_schema_owner'::regrole"
    )

    mutation(
      "PUBLIC readonly application view escape",
      "CREATE VIEW public.review_members AS SELECT principal_id FROM public.mixer_authz_memberships; GRANT SELECT ON public.review_members TO PUBLIC",
      "SELECT has_table_privilege('browser_lifecycle','public.review_members','SELECT') AND has_table_privilege('browser_writer','public.review_members','SELECT')"
    )

    mutation(
      "lifecycle sequence UPDATE escape",
      "CREATE SEQUENCE public.review_sequence; GRANT UPDATE ON SEQUENCE public.review_sequence TO browser_lifecycle",
      "SELECT has_sequence_privilege('browser_lifecycle','public.review_sequence','UPDATE')"
    )

    mutation(
      "tenant column-only SELECT escape",
      "GRANT SELECT(id) ON public.mixer_authz_organizations TO browser_writer",
      "SELECT NOT has_table_privilege('browser_writer','public.mixer_authz_organizations','SELECT') AND has_column_privilege('browser_writer','public.mixer_authz_organizations','id','SELECT')"
    )

    mutation(
      "constraint trigger immediate metadata",
      "UPDATE pg_trigger SET tginitdeferred=false WHERE tgrelid='public.mixer_browser_session_events'::regclass AND tgname='mixer_browser_integrity'",
      "SELECT tgdeferrable AND NOT tginitdeferred FROM pg_trigger WHERE tgrelid='public.mixer_browser_session_events'::regclass AND tgname='mixer_browser_integrity'"
    )

    mutation(
      "user trigger function alias cannot substitute equal body",
      "DO $x$ DECLARE body text; BEGIN SELECT prosrc INTO body FROM pg_proc WHERE oid='public.mixer_browser_integrity()'::regprocedure; EXECUTE format('CREATE FUNCTION public.review_integrity() RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER AS %L',body); END $x$; ALTER FUNCTION public.review_integrity() OWNER TO browser_writer; UPDATE pg_trigger SET tgfoid='public.review_integrity()'::regprocedure WHERE tgrelid='public.mixer_browser_sessions'::regclass AND tgname='mixer_browser_integrity'",
      "SELECT t.tgfoid<>'public.mixer_browser_integrity()'::regprocedure AND p.prosrc=q.prosrc FROM pg_trigger t JOIN pg_proc p ON p.oid=t.tgfoid CROSS JOIN pg_proc q WHERE t.tgrelid='public.mixer_browser_sessions'::regclass AND t.tgname='mixer_browser_integrity' AND q.oid='public.mixer_browser_integrity()'::regprocedure"
    )

    mutation(
      "automatic CHECK rename remains equivalent",
      "ALTER TABLE public.mixer_browser_sessions RENAME CONSTRAINT mixer_browser_sessions_id_check TO review_generated_check",
      "SELECT count(*)=1 FROM pg_constraint WHERE conrelid='public.mixer_browser_sessions'::regclass AND conname='review_generated_check'",
      true
    )

    mutation(
      "automatic RI names remain equivalent",
      "UPDATE pg_trigger SET tgname='review_ri_'||oid::text WHERE tgrelid='public.mixer_browser_sessions'::regclass AND tgisinternal",
      "SELECT count(*)>0 AND bool_and(tgname LIKE 'review_ri_%') FROM pg_trigger WHERE tgrelid='public.mixer_browser_sessions'::regclass AND tgisinternal",
      true
    )

    {:ok, wire} = Agent.start_link(fn -> nil end, name: RelationReview.Wire)

    :ok =
      Ecto.Repo.Registry.associate(wire, RelationReview.Wire, %{
        pid: wire,
        telemetry: {RelationReview.Wire, false, []},
        sql: RelationReview.Adapter,
        opts: [],
        log_stacktrace_mfa: nil
      })

    try do
      Process.put(:review_index, 0)
      Process.put(:review_rows, [])

      record("independent actual wire capture", fn ->
        assert(
          RelationReview.Login.transaction(
            fn ->
              policy(RelationReview.Login)
              check(RelationReview.Wire)
            end, log: false) === {:ok, :relation_surface_verified}
        )
      end)

      calls = Enum.reverse(Process.get(:review_rows))
      assert(length(calls) === 12)
      Process.put(:review_capture, calls)

      record("unaltered captured wire passes", fn ->
        assert(replay(fn _, r -> {:ok, r} end) === :relation_surface_verified)
      end)

      for family <- 0..11 do
        for {name, change} <- [
              {"missing positive backend PID", fn r -> %{r | connection_id: nil} end},
              {"noninteger row count", fn r -> %{r | num_rows: 1.0} end},
              {"extra scalar in row",
               fn r -> %{r | rows: [(hd(r.rows) || []) ++ [false] | tl(r.rows)]} end}
            ] do
          # The empty forbidden family is tested using an explicit malformed row.
          record("independent wire #{family}: " <> name, fn ->
            unavailable(fn ->
              replay(fn i, r ->
                if i == family do
                  value =
                    if name == "extra scalar in row" and r.rows == [],
                      do: %{r | rows: [[1, false]], num_rows: 1},
                      else: change.(r)

                  {:ok, value}
                else
                  {:ok, r}
                end
              end)
            end)
          end)
        end

        record("independent wire #{family}: thrown diagnostic redacted without retry", fn ->
          unavailable(fn ->
            replay(fn i, r ->
              if i == family, do: throw({:private, "REVIEW-SECRET"}), else: {:ok, r}
            end)
          end)

          assert(Process.get(:review_index) === family + 1)
        end)
      end

      for {field, value} <- [
            {"collate", "C.UTF-8"},
            {"provider", "i"},
            {"actual_version", "review-version"},
            {"replication", "replica"},
            {"version", 150_000}
          ] do
        record("independent unqualified environment: " <> field, fn ->
          unavailable(fn ->
            replay(fn i, r ->
              if i == 0 do
                at = Enum.find_index(r.columns, &(&1 == field))
                [row] = r.rows
                {:ok, %{r | rows: [List.replace_at(row, at, value)]}}
              else
                {:ok, r}
              end
            end)
          end)

          assert(Process.get(:review_index) === 1)
        end)
      end

      for {family, field, value} <- [
            {1, "oid", 4_294_967_296},
            {2, "name", <<255>>},
            {4, "keys", [nil]},
            {7, "roles", [0, 0]},
            {10, "rights", [true, false, true, nil]}
          ] do
        record("independent scalar #{family}: " <> field, fn ->
          unavailable(fn ->
            replay(fn i, r ->
              if i == family do
                at = Enum.find_index(r.columns, &(&1 == field))
                [row | tail] = r.rows
                {:ok, %{r | rows: [List.replace_at(row, at, value) | tail]}}
              else
                {:ok, r}
              end
            end)
          end)
        end)
      end

      record("original deadline expires before post-query decoding", fn ->
        deadline = System.monotonic_time(:millisecond) + 30

        unavailable(fn ->
          replay(
            fn i, r ->
              if i == 3, do: Process.sleep(45)
              {:ok, r}
            end,
            deadline
          )
        end)

        assert(Process.get(:review_index) === 4)
      end)
    after
      Agent.stop(wire)
    end

    baseline()

    result = %{
      checks: Enum.reverse(Process.get(:review_checks, [])),
      facts: Enum.reverse(Process.get(:review_facts, [])),
      census: Process.get(:review_census)
    }

    File.write!(
      Path.join(System.fetch_env!("RELATION_OUTPUT"), "checks.json"),
      Jason.encode!(result, pretty: true) <> "\n"
    )

    IO.puts("passed independent methods: #{length(result.checks)}")
  end
end

port = System.fetch_env!("RELATION_PORT") |> String.to_integer()

children =
  for {repo, user} <- [
        {RelationReview.Admin, "browser_admin"},
        {RelationReview.Login, "browser_lifecycle"}
      ] do
    {:ok, pid} =
      repo.start_link(
        hostname: "127.0.0.1",
        port: port,
        database: "browser_storage",
        username: user,
        pool_size: 1,
        log: false,
        backoff_type: :stop
      )

    pid
  end

try do
  RelationReview.run()
after
  Enum.each(children, &GenServer.stop/1)
end
