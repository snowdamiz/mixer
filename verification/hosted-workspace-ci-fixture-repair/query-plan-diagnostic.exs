alias MixerHosted.CustomerWorkspace.Fixture.{Admin, Runtime}

:telemetry.attach(
  :workspace_large_customer_plan_diagnostic,
  [:workspace_probe, :query],
  fn _, measurements, metadata, _ ->
    if metadata.params == ["org-a", nil, 101] and
         String.contains?(metadata.query, "FROM public.mixer_authz_projects p") and
         not Process.get(:workspace_large_customer_plan_diagnostic, false) do
      Process.put(:workspace_large_customer_plan_diagnostic, true)

      sql = fn repo, query, params ->
        Ecto.Adapters.SQL.query!(repo, query, params, log: false)
      end

      [[version, jit_available, jit, jit_cost, jit_inline_cost, jit_optimize_cost]] =
        sql.(
          Admin,
          "SELECT version(), pg_jit_available(), current_setting('jit'), current_setting('jit_above_cost'), current_setting('jit_inline_above_cost'), current_setting('jit_optimize_above_cost')",
          []
        ).rows

      stats_sql = """
      SELECT relname, reltuples, relpages FROM pg_class
      WHERE relname LIKE 'mixer_authz_%' AND relkind = 'r' ORDER BY relname
      """

      stats_before = sql.(Admin, stats_sql, []).rows

      explain = "EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) " <> metadata.query
      before = sql.(Runtime, explain, metadata.params).rows

      for table <-
            ~w(profiles principals bindings families credentials organizations projects applications environments organization_heads project_heads memberships) do
        sql.(Admin, "ANALYZE public.mixer_authz_#{table}", [])
      end

      stats_after = sql.(Admin, stats_sql, []).rows
      after_stats = sql.(Runtime, explain, metadata.params).rows

      File.write!(
        System.fetch_env!("MIXER_WORKSPACE_PLAN_DIAGNOSTIC_RESULT"),
        Jason.encode!(%{
          query: metadata.query,
          params: metadata.params,
          version: version,
          jit_available: jit_available,
          jit: jit,
          jit_above_cost: jit_cost,
          jit_inline_above_cost: jit_inline_cost,
          jit_optimize_above_cost: jit_optimize_cost,
          original_query_us:
            System.convert_time_unit(measurements.query_time, :native, :microsecond),
          stats_before: stats_before,
          plan_before_analyze: before,
          stats_after: stats_after,
          plan_after_analyze: after_stats
        })
      )
    end
  end,
  nil
)
