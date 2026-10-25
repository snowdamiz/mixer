alias MixerHosted.CustomerWorkspace.Fixture.Runtime

trace = System.fetch_env!("MIXER_COLD_READ_TRACE")
plans = System.fetch_env!("MIXER_COLD_READ_PLANS")
File.mkdir_p!(plans)
claimed = :atomics.new(1, [])
disable_jit = System.get_env("MIXER_COLD_READ_DISABLE_JIT") == "true"

:telemetry.attach(
  :workspace_cold_organization_read,
  [:workspace_probe, :query],
  fn _, measurements, metadata, _ ->
    unless Process.get(:workspace_cold_explain, false) do
      microseconds = fn key ->
        System.convert_time_unit(Map.get(measurements, key) || 0, :native, :microsecond)
      end

      finished = System.monotonic_time(:microsecond)
      stage = Process.get(:workspace_cold_read)

      stage =
        if is_nil(stage) and String.downcase(metadata.query) == "begin" and
             :atomics.compare_exchange(claimed, 1, 0, 1) == :ok do
          %{sequence: 0, started: finished - microseconds.(:total_time)}
        else
          stage
        end

      if is_map(stage) do
        sequence = stage.sequence + 1

        jit_policy_us =
          if stage.sequence == 0 and disable_jit do
            Process.put(:workspace_cold_explain, true)
            before = System.monotonic_time(:microsecond)

            try do
              Ecto.Adapters.SQL.query!(Runtime, "SET LOCAL jit = off", [],
                timeout: 5_000,
                queue: false,
                log: false
              )

              System.monotonic_time(:microsecond) - before
            after
              Process.delete(:workspace_cold_explain)
            end
          else
            0
          end

        category =
          cond do
            String.contains?(metadata.query, "FROM public.mixer_authz_profiles p CROSS JOIN") ->
              "identity"

            String.contains?(metadata.query, "FROM public.mixer_authz_organizations o WHERE") ->
              "organization"

            String.contains?(metadata.query, "current_user = session_user") or
              String.contains?(metadata.query, "bool_and(c.relrowsecurity") or
                String.contains?(metadata.query, "bool_and(p.prosecdef") ->
              "topology"

            true ->
              "context_or_lock_boundary"
          end

        event = %{
          sequence: sequence,
          query: metadata.query,
          params:
            case metadata.params do
              ["mixer.authz.transaction_marker", _] ->
                ["mixer.authz.transaction_marker", "<redacted synthetic marker>"]

              params ->
                params
            end,
          category: category,
          diagnostic_jit_off: disable_jit,
          diagnostic_jit_policy_us: jit_policy_us,
          finished_unix_millisecond: System.system_time(:millisecond),
          elapsed_at_end_us: finished - stage.started,
          query_us: microseconds.(:query_time),
          decode_us: microseconds.(:decode_time),
          queue_us: microseconds.(:queue_time),
          total_us: microseconds.(:total_time),
          result:
            case metadata.result do
              {:ok, %{num_rows: count}} -> %{status: "ok", rows: count}
              other -> %{status: "error", result: inspect(other)}
            end
        }

        event =
          if category in ["identity", "organization", "topology"] and
               event.result.status == "ok" do
            Process.put(:workspace_cold_explain, true)
            before = System.monotonic_time(:microsecond)

            try do
              plan =
                Ecto.Adapters.SQL.query!(
                  Runtime,
                  "EXPLAIN (FORMAT JSON) " <> metadata.query,
                  metadata.params,
                  timeout: 5_000,
                  queue: false,
                  log: false
                ).rows

              name = Integer.to_string(sequence) <> "-" <> category <> ".json"
              File.write!(Path.join(plans, name), Jason.encode!(%{plan: plan}))

              Map.merge(event, %{
                explain_file: "cold-read-plans/" <> name,
                explain_overhead_us: System.monotonic_time(:microsecond) - before
              })
            after
              Process.delete(:workspace_cold_explain)
            end
          else
            event
          end

        File.write!(trace, Jason.encode!(event) <> "\n", [:append])

        if String.downcase(metadata.query) in ["commit", "rollback"] do
          Process.put(:workspace_cold_read, :finished)
        else
          Process.put(:workspace_cold_read, %{stage | sequence: sequence})
        end
      end
    end
  end,
  nil
)
