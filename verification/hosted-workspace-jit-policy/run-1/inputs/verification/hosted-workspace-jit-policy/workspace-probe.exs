alias MixerHosted.CustomerWorkspace.Fixture.Runtime
output = System.fetch_env!("MIXER_JIT_POLICY_PROBE_DIR")
claimed = :atomics.new(1, [])

:telemetry.attach(
  :workspace_jit_policy_probe,
  [:workspace_probe, :query],
  fn _, measurements, metadata, _ ->
    unless Process.get(:jit_policy_observing, false) do
      stage = Process.get(:jit_policy_trace)

      stage =
        if is_nil(stage) and String.downcase(metadata.query) == "begin" and
             :atomics.compare_exchange(claimed, 1, 0, 1) == :ok,
           do: %{sequence: 0, started: System.monotonic_time(:microsecond)},
           else: stage

      if is_map(stage) do
        sequence = stage.sequence + 1

        event = %{
          sequence: sequence,
          query: metadata.query,
          elapsed_us: System.monotonic_time(:microsecond) - stage.started,
          query_us:
            System.convert_time_unit(
              Map.get(measurements, :query_time) || 0,
              :native,
              :microsecond
            )
        }

        if String.contains?(metadata.query, "FROM public.mixer_authz_organizations o WHERE") do
          Process.put(:jit_policy_observing, true)

          try do
            [[jit]] = Ecto.Adapters.SQL.query!(Runtime, "SHOW jit", [], log: false).rows

            [[plan]] =
              Ecto.Adapters.SQL.query!(
                Runtime,
                "EXPLAIN (FORMAT JSON) " <> metadata.query,
                metadata.params, timeout: 5_000, queue: false, log: false).rows

            File.write!(
              Path.join(output, "workspace-organization-plan.json"),
              Jason.encode!(%{effective_jit: jit, plan: plan, query_us: event.query_us})
            )
          after
            Process.delete(:jit_policy_observing)
          end
        end

        File.write!(
          Path.join(output, "workspace-first-transaction.jsonl"),
          Jason.encode!(event) <> "\n",
          [:append]
        )

        Process.put(
          :jit_policy_trace,
          if(String.downcase(metadata.query) in ["commit", "rollback"],
            do: :finished,
            else: %{stage | sequence: sequence}
          )
        )
      end
    end
  end,
  nil
)
