defmodule MixerHosted.Billing.UsageLedgerTest do
  use ExUnit.Case, async: false
  alias MixerHosted.Billing.{UsageEntry, UsageLedger}
  alias MixerHosted.Repo
  @max 9_223_372_036_854_775_807

  setup_all do
    config = [
      hostname: "127.0.0.1",
      port: String.to_integer(System.fetch_env!("MIXER_USAGE_DATABASE_PORT")),
      database: "mixer_usage_r398",
      username: "mixer_fixture",
      pool_size: 8
    ]

    start_supervised!({Repo, config})

    Code.require_file(
      "../../../priv/repo/migrations/20261110000001_add_billing_usage_ledger.exs",
      __DIR__
    )

    assert :ok ==
             Ecto.Migrator.up(
               Repo,
               20_261_110_000_001,
               MixerHosted.Repo.Migrations.AddBillingUsageLedger,
               log: false
             )

    stop_supervised!(Repo)
    {:ok, config: config}
  end

  setup %{config: config} do
    start_supervised!({Repo, config})
    {:ok, tenant: Ecto.UUID.generate()}
  end

  defp scope(tenant, overrides \\ %{}) do
    {:ok, scope} =
      UsageLedger.scope(
        Map.merge(
          %{
            tenant_id: tenant,
            metric: "build_elapsed_milliseconds",
            platform: "ios",
            period_start: 1_793_491_200,
            period_end: 1_796_083_200
          },
          overrides
        )
      )

    scope
  end

  defp observation(scope, overrides) do
    Map.merge(
      %{scope: scope, source: "trusted-worker-v1", source_key: "build-1", units: 120_001},
      overrides
    )
  end

  defp append(scope, overrides \\ %{}),
    do: UsageLedger.append(Repo, observation(scope, overrides))

  defp concurrently(fun) do
    1..12
    |> Task.async_stream(fun, max_concurrency: 8, timeout: 15_000, ordered: false)
    |> Enum.map(fn {:ok, result} -> result end)
  end

  test "exact elapsed units persist and retries return the same immutable entry", %{
    tenant: tenant
  } do
    scope = scope(tenant)
    assert {:ok, :appended, original} = append(scope)
    assert original.units == 120_001
    assert {:ok, :duplicate, ^original} = append(scope)
    assert {:error, :identity_conflict} = append(scope, %{units: 120_002})
    assert {:ok, 120_001} == UsageLedger.total(Repo, scope)
    assert {:ok, [^original]} = UsageLedger.entries(Repo, scope)
  end

  test "same source identity conflicts across metric, platform and period", %{tenant: tenant} do
    base = scope(tenant)
    assert {:ok, :appended, _} = append(base)

    for different <- [
          scope(tenant, %{platform: "android"}),
          scope(tenant, %{metric: "storage_byte_seconds", platform: "all"}),
          scope(tenant, %{period_start: base.period_start + 1})
        ] do
      assert {:error, :identity_conflict} = append(different)
      assert {:ok, 0} == UsageLedger.total(Repo, different)
    end
  end

  test "concurrent identical inserts deduplicate atomically", %{tenant: tenant} do
    scope = scope(tenant)
    results = concurrently(fn _ -> append(scope) end)
    assert Enum.count(results, &match?({:ok, :appended, _}, &1)) == 1
    assert Enum.count(results, &match?({:ok, :duplicate, _}, &1)) == 11
    assert results |> Enum.map(fn {:ok, _, e} -> e.id end) |> Enum.uniq() |> length() == 1
    assert {:ok, 120_001} == UsageLedger.total(Repo, scope)
  end

  test "concurrent conflicting observations cannot both win", %{tenant: tenant} do
    scope = scope(tenant)
    results = concurrently(fn n -> append(scope, %{units: n}) end)
    assert [{:ok, :appended, winner}] = Enum.filter(results, &match?({:ok, :appended, _}, &1))
    assert Enum.count(results, &(&1 == {:error, :identity_conflict})) == 11
    assert {:ok, winner.units} == UsageLedger.total(Repo, scope)
  end

  test "tenant/source identities and explicit queries isolate observations", %{tenant: tenant} do
    a = scope(tenant)
    b = scope(Ecto.UUID.generate())
    assert {:ok, :appended, original} = append(a)
    assert {:ok, :appended, _} = append(b, %{units: 7})

    assert {:error, :predecessor_unavailable} =
             append(
               b,
               %{source_key: "foreign-parent", correction_of: original.id, units: 0}
             )

    assert {:ok, 120_001} == UsageLedger.total(Repo, a)
    assert {:ok, 7} == UsageLedger.total(Repo, b)
    assert {:ok, [entry]} = UsageLedger.entries(Repo, b)
    assert entry.tenant_id == b.tenant_id
    assert {:error, :invalid_scope} == UsageLedger.total(Repo, %{})
    assert {:error, :invalid_scope} == UsageLedger.entries(Repo, %{tenant_id: tenant})
    assert {:ok, :appended, _} = append(a, %{source: "another-trusted-worker", units: 2})
    assert {:ok, 120_003} == UsageLedger.total(Repo, a)
  end

  test "corrections replace chain heads without rewriting history", %{tenant: tenant} do
    scope = scope(tenant)
    assert {:ok, :appended, base} = append(scope, %{units: 10})
    correction = %{source_key: "correct-1", correction_of: base.id, units: 4}
    assert {:ok, :appended, corrected} = append(scope, correction)
    assert {:ok, :duplicate, ^corrected} = append(scope, correction)
    assert {:error, :identity_conflict} = append(scope, Map.put(correction, :units, 5))

    assert {:error, :predecessor_superseded} =
             append(
               scope,
               %{source_key: "stale-correction", correction_of: base.id, units: 3}
             )

    assert {:ok, :appended, _} =
             append(
               scope,
               %{source_key: "correct-2", correction_of: corrected.id, units: 6}
             )

    assert {:ok, 6} == UsageLedger.total(Repo, scope)
    assert {:ok, history} = UsageLedger.entries(Repo, scope)
    assert length(history) == 3
    assert Repo.get!(UsageEntry, base.id).units == 10
  end

  test "missing and out-of-order predecessors refuse then exact retry succeeds", %{tenant: tenant} do
    scope = scope(tenant)
    missing = Ecto.UUID.generate()

    assert {:error, :predecessor_unavailable} =
             append(
               scope,
               %{source_key: "too-early", correction_of: missing, units: 1}
             )

    # Model a previously known authoritative predecessor id arriving later.
    row = %UsageEntry{
      id: missing,
      tenant_id: tenant,
      metric: scope.metric,
      platform: scope.platform,
      period_start: scope.period_start,
      period_end: scope.period_end,
      source: "trusted-worker-v1",
      source_key: "late-original",
      units: 9,
      inserted_at: DateTime.utc_now()
    }

    Repo.insert!(row)

    assert {:ok, :appended, correction} =
             append(
               scope,
               %{source_key: "too-early", correction_of: missing, units: 1}
             )

    assert {:ok, :duplicate, ^correction} =
             append(
               scope,
               %{source_key: "too-early", correction_of: missing, units: 1}
             )

    assert {:ok, 1} == UsageLedger.total(Repo, scope)
  end

  test "competing correction successors serialize to exactly one head", %{tenant: tenant} do
    scope = scope(tenant)
    assert {:ok, :appended, base} = append(scope)

    results =
      concurrently(fn n ->
        append(
          scope,
          %{source_key: "correction-#{n}", correction_of: base.id, units: n}
        )
      end)

    assert [{:ok, :appended, winner}] = Enum.filter(results, &match?({:ok, :appended, _}, &1))
    assert Enum.count(results, &(&1 == {:error, :predecessor_superseded})) == 11
    assert {:ok, winner.units} == UsageLedger.total(Repo, scope)
    assert {:ok, rows} = UsageLedger.entries(Repo, scope)
    assert length(rows) == 2
  end

  test "rollback covers original and correction and frees idempotency identity", %{tenant: tenant} do
    scope = scope(tenant)

    assert {:error, :abort} =
             Repo.transaction(fn ->
               assert {:ok, :appended, original} = append(scope)

               assert {:ok, :appended, _} =
                        append(
                          scope,
                          %{source_key: "correction", correction_of: original.id, units: 3}
                        )

               assert {:ok, 3} == UsageLedger.total(Repo, scope)
               Repo.rollback(:abort)
             end)

    assert {:ok, []} == UsageLedger.entries(Repo, scope)
    assert {:ok, 0} == UsageLedger.total(Repo, scope)
    assert {:ok, :appended, _} = append(scope)
  end

  test "large exact totals exceed bigint without wrapping or float", %{tenant: tenant} do
    scope = scope(tenant)

    for n <- 1..3,
        do:
          assert(
            {:ok, :appended, _} =
              append(
                scope,
                %{source_key: "large-#{n}", units: @max}
              )
          )

    assert {:ok, @max * 3} == UsageLedger.total(Repo, scope)
    assert {:error, :invalid_observation} = append(scope, %{units: @max + 1})
  end

  test "invalid exact units, scopes and unknown fields fail closed", %{tenant: tenant} do
    scope = scope(tenant)

    for units <- [-1, 1.0, "1", true, nil] do
      assert {:error, :invalid_observation} = append(scope, %{units: units})
    end

    assert {:error, :invalid_observation} = append(scope, %{customer_proven: true})
    assert {:error, :invalid_observation} = append(scope, %{correction_of: "not-uuid"})

    for bad <- [
          %{scope | metric: "build_compute_milliseconds"},
          %{scope | platform: "all"},
          %{scope | period_start: scope.period_end},
          %{scope | tenant_id: ""},
          %{scope | period_start: 1.0}
        ] do
      assert {:error, :invalid_scope} = UsageLedger.scope(bad)
      assert {:error, :invalid_observation} = append(bad)
    end

    assert {:ok, 0} == UsageLedger.total(Repo, scope)
  end

  test "installation-month base 1 can be voided and reopened with new causal keys", %{
    tenant: tenant
  } do
    start = DateTime.to_unix(~U[2026-12-01 00:00:00Z])
    finish = DateTime.to_unix(~U[2027-01-01 00:00:00Z])

    scope =
      scope(tenant, %{
        metric: "active_update_installations",
        platform: "all",
        period_start: start,
        period_end: finish
      })

    obs = %{
      source: "trusted-assignment-v1",
      source_key: "app-pseudonym/install-pseudonym/2026-12",
      units: 1
    }

    assert {:ok, :appended, base} = append(scope, obs)
    assert {:ok, :duplicate, ^base} = append(scope, obs)
    assert {:error, :invalid_observation} = append(scope, %{units: 0})
    assert {:error, :invalid_observation} = append(scope, %{units: 2})

    assert {:ok, :appended, void} =
             append(scope, %{
               source: obs.source,
               source_key: "void",
               correction_of: base.id,
               units: 0
             })

    assert {:ok, 0} == UsageLedger.total(Repo, scope)

    assert {:ok, :appended, _} =
             append(scope, %{
               source: obs.source,
               source_key: "reopen",
               correction_of: void.id,
               units: 1
             })

    assert {:ok, 1} == UsageLedger.total(Repo, scope)
    assert {:error, :invalid_scope} = UsageLedger.scope(%{scope | period_end: finish - 1})
    assert {:error, :invalid_scope} = UsageLedger.scope(%{scope | period_start: start + 1})
  end

  test "corrections cannot cross metric, platform, period or source", %{tenant: tenant} do
    scope = scope(tenant)
    assert {:ok, :appended, base} = append(scope)

    for other <- [
          %{scope | platform: "android"},
          %{scope | period_end: scope.period_end + 1},
          %{scope | metric: "storage_byte_seconds", platform: "all"}
        ] do
      assert {:error, :predecessor_unavailable} =
               append(
                 other,
                 %{source_key: "wrong-scope", correction_of: base.id, units: 0}
               )
    end

    assert {:error, :predecessor_unavailable} =
             append(
               scope,
               %{
                 source: "other-producer",
                 source_key: "wrong-source",
                 correction_of: base.id,
                 units: 0
               }
             )
  end

  test "database rejects mutation and direct cross-scope correction", %{tenant: tenant} do
    scope = scope(tenant)
    assert {:ok, :appended, base} = append(scope)

    for statement <- [
          "UPDATE mixer_billing_usage_entries SET units = 0",
          "DELETE FROM mixer_billing_usage_entries",
          "TRUNCATE mixer_billing_usage_entries"
        ] do
      assert {:error, %Postgrex.Error{postgres: %{code: :check_violation}}} =
               Repo.query(statement)
    end

    assert {:error, %Postgrex.Error{postgres: %{code: :foreign_key_violation}}} =
             Repo.query(
               """
               INSERT INTO mixer_billing_usage_entries
               (id,tenant_id,metric,platform,period_start,period_end,source,source_key,units,correction_of,inserted_at)
               SELECT $1::uuid, 'foreign-tenant', metric,platform,period_start,period_end,source,'cross-scope',0,id,inserted_at
               FROM mixer_billing_usage_entries WHERE id = $2::uuid
               """,
               [Ecto.UUID.dump!(Ecto.UUID.generate()), Ecto.UUID.dump!(base.id)]
             )

    assert {:ok, 120_001} == UsageLedger.total(Repo, scope)
  end

  test "committed ledger survives repo close and reopen", %{tenant: tenant, config: config} do
    scope = scope(tenant, %{metric: "storage_byte_seconds", platform: "all"})
    assert {:ok, :appended, base} = append(scope, %{units: 123_456_789})
    stop_supervised!(Repo)
    start_supervised!({Repo, config})
    assert {:ok, 123_456_789} == UsageLedger.total(Repo, scope)
    assert {:ok, :duplicate, ^base} = append(scope, %{units: 123_456_789})
  end

  test "concurrent readers see the old head until replacement commits", %{tenant: tenant} do
    scope = scope(tenant)
    assert {:ok, :appended, base} = append(scope, %{units: 10})
    caller = self()

    task =
      Task.async(fn ->
        Repo.transaction(fn ->
          assert {:ok, :appended, _} =
                   append(
                     scope,
                     %{source_key: "replacement", correction_of: base.id, units: 4}
                   )

          send(caller, :replacement_uncommitted)

          receive do
            :commit -> :committed
          after
            5_000 -> Repo.rollback(:reader_barrier_expired)
          end
        end)
      end)

    assert_receive :replacement_uncommitted, 5_000
    assert {:ok, 10} == UsageLedger.total(Repo, scope)
    send(task.pid, :commit)
    assert {:ok, :committed} == Task.await(task, 5_000)
    assert {:ok, 4} == UsageLedger.total(Repo, scope)
  end

  test "database refuses same-statement causal cycles", %{tenant: tenant} do
    scope = scope(tenant)
    a = Ecto.UUID.dump!(Ecto.UUID.generate())
    b = Ecto.UUID.dump!(Ecto.UUID.generate())

    assert {:error, %Postgrex.Error{postgres: %{code: :foreign_key_violation}}} =
             Repo.query(
               """
               INSERT INTO mixer_billing_usage_entries
               (id,tenant_id,metric,platform,period_start,period_end,source,source_key,units,correction_of,inserted_at)
               VALUES ($1::uuid,$3,'build_elapsed_milliseconds','ios',$4,$5,'worker','cycle-a',1,$2::uuid,now()),
                      ($2::uuid,$3,'build_elapsed_milliseconds','ios',$4,$5,'worker','cycle-b',1,$1::uuid,now())
               """,
               [a, b, tenant, scope.period_start, scope.period_end]
             )

    assert {:ok, []} == UsageLedger.entries(Repo, scope)
  end
end
