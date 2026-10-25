alias MixerHosted.CustomerWorkspace.Fixture.{Admin, Runtime}

candidate =
  System.fetch_env!("MIXER_WORKSPACE_PLAN_QUERY") |> File.read!() |> Jason.decode!()

output = System.fetch_env!("MIXER_WORKSPACE_PLAN_DIAGNOSTIC_RESULT")
analyze = System.get_env("MIXER_WORKSPACE_PLAN_ANALYZE") == "true"
force_generic = System.get_env("MIXER_WORKSPACE_PLAN_FORCE_GENERIC") == "true"

:telemetry.attach(
  :workspace_large_customer_pg16_plan_diagnostic,
  [:workspace_probe, :query],
  fn _, measurements, metadata, _ ->
    sql = fn repo, query, params -> Ecto.Adapters.SQL.query!(repo, query, params, log: false) end

    cond do
      metadata.params == ["org-a", 1] and String.contains?(metadata.query, "o.id = $1") and
          is_nil(Process.get(:workspace_large_customer_pg16_plan_diagnostic)) ->
        [[count]] = sql.(Admin, "SELECT count(*) FROM public.mixer_authz_memberships", []).rows

        if count > 100 do
          Process.put(:workspace_large_customer_pg16_plan_diagnostic, :prepared)

          settings =
            sql.(
              Admin,
              "SELECT version(), pg_jit_available(), current_setting('jit'), current_setting('jit_above_cost'), current_setting('jit_inline_above_cost'), current_setting('jit_optimize_above_cost'), current_setting('autovacuum_analyze_threshold'), current_setting('autovacuum_analyze_scale_factor'), current_setting('autovacuum_naptime')",
              []
            ).rows

          binding =
            sql.(
              Runtime,
              "SELECT current_user, session_user, current_setting('mixer.authz.directory_mode'), current_setting('mixer.authz.organization_id'), current_setting('mixer.authz.phase'), current_setting('statement_timeout'), current_setting('lock_timeout')",
              []
            ).rows

          stats_sql = """
          SELECT relname, reltuples, relpages FROM pg_class
          WHERE relname LIKE 'mixer_authz_%' AND relkind = 'r' ORDER BY relname
          """

          stats_before = sql.(Admin, stats_sql, []).rows

          prepared =
            sql.(
              Runtime,
              "SELECT name, generic_plans, custom_plans FROM pg_prepared_statements WHERE statement = $1",
              [candidate["query"]]
            ).rows

          explain = "EXPLAIN (FORMAT JSON) " <> candidate["query"]
          before = sql.(Runtime, explain, candidate["params"]).rows

          sql.(
            Runtime,
            "PREPARE workspace_candidate_probe(text,text,integer) AS " <> candidate["query"],
            []
          )

          sql.(Runtime, "SET LOCAL plan_cache_mode = force_generic_plan", [])

          generic_explain =
            "EXPLAIN (FORMAT JSON) EXECUTE workspace_candidate_probe('org-a',NULL,101)"

          generic_before = sql.(Runtime, generic_explain, []).rows

          if analyze do
            for table <-
                  ~w(profiles principals bindings families credentials organizations projects applications environments organization_heads project_heads memberships) do
              sql.(Admin, "ANALYZE public.mixer_authz_#{table}", [])
            end
          end

          stats_after = sql.(Admin, stats_sql, []).rows
          after_stats = sql.(Runtime, generic_explain, []).rows
          unless force_generic, do: sql.(Runtime, "SET LOCAL plan_cache_mode = auto", [])

          File.write!(
            output,
            Jason.encode!(%{
              query: candidate["query"],
              params: candidate["params"],
              settings: settings,
              runtime_binding: binding,
              memberships: count,
              explicit_analyze: analyze,
              force_generic_production_query: force_generic,
              prepared_statements_before_query: prepared,
              stats_before: stats_before,
              plan_before_analyze: before,
              generic_plan_before_analyze: generic_before,
              stats_after: stats_after,
              plan_after_analyze: after_stats,
              production_candidate_completed: false
            })
          )
        end

      metadata.params == candidate["params"] and metadata.query == candidate["query"] and
          Process.get(:workspace_large_customer_pg16_plan_diagnostic) == :prepared ->
        Process.put(:workspace_large_customer_pg16_plan_diagnostic, :completed)
        result = File.read!(output) |> Jason.decode!()

        result =
          Map.merge(result, %{
            "production_candidate_completed" => true,
            "production_candidate_query_us" =>
              System.convert_time_unit(measurements.query_time, :native, :microsecond),
            "production_candidate_result" =>
              case metadata.result do
                {:ok, %{rows: rows}} -> %{"rows" => length(rows), "status" => "ok"}
                other -> %{"status" => "error", "result" => inspect(other)}
              end
          })

        File.write!(output, Jason.encode!(result))

      true ->
        :ok
    end
  end,
  nil
)
