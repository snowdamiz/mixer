defmodule MixerHosted.Billing.UsageLedger do
  @moduledoc """
  Private ledger for trusted server observations, not a measurement verifier.

  Callers derive scope, source identity and units from authoritative worker,
  assignment or storage state. Arbitrary request data is not proven usage.
  Build units are worker elapsed milliseconds, without minute rounding.
  Active installations are app-scoped installation-months, not physical devices;
  a producer uses one stable initial identity per installation-month, never polls.
  Storage units are exact byte-seconds; pricing and commercial rules are separate.

  Corrections append absolute replacements, each with one causal predecessor.
  Totals sum current chain heads in one snapshot with unbounded integer output.
  A successful append inside an enclosing transaction is still provisional and
  rolls back with that transaction. No provider, entitlement or consumer is wired.
  """
  import Ecto.Query
  alias MixerHosted.Billing.UsageEntry

  defmodule Scope do
    @moduledoc "Explicit tenant/metric/platform and half-open UTC Unix-second period."
    @enforce_keys [:tenant_id, :metric, :platform, :period_start, :period_end]
    defstruct @enforce_keys

    @type t :: %__MODULE__{
            tenant_id: String.t(),
            metric: String.t(),
            platform: String.t(),
            period_start: non_neg_integer(),
            period_end: pos_integer()
          }
  end

  @scope_fields [:tenant_id, :metric, :platform, :period_start, :period_end]
  @observation_fields [:scope, :source, :source_key, :units, :correction_of]
  @max_units 9_223_372_036_854_775_807
  @max_time 253_402_300_799

  @spec scope(term()) :: {:ok, Scope.t()} | {:error, :invalid_scope}
  def scope(%Scope{} = value), do: scope(Map.from_struct(value))

  def scope(%{} = value) when not is_struct(value) do
    with true <- Enum.sort(Map.keys(value)) == Enum.sort(@scope_fields),
         %{
           tenant_id: tenant,
           metric: metric,
           platform: platform,
           period_start: first,
           period_end: last
         } <- value,
         true <- identity?(tenant),
         true <-
           is_integer(first) and is_integer(last) and first >= 0 and
             last > first and last <= @max_time,
         true <- metric_scope?(metric, platform, first, last) do
      {:ok, struct!(Scope, value)}
    else
      _ -> {:error, :invalid_scope}
    end
  end

  def scope(_), do: {:error, :invalid_scope}

  @spec append(module(), map()) ::
          {:ok, :appended | :duplicate, UsageEntry.t()} | {:error, atom()}
  def append(repo, observation) do
    with {:ok, row} <- observation(observation) do
      case repo.transaction(fn -> persist(repo, row) end) do
        {:ok, result} -> result
        {:error, reason} -> {:error, reason}
      end
    end
  end

  @spec total(module(), Scope.t()) :: {:ok, non_neg_integer()} | {:error, :invalid_scope}
  def total(repo, requested_scope) do
    with {:ok, scope} <- scope(requested_scope) do
      # PostgreSQL SUM(bigint) is numeric, then text transports it losslessly.
      # Do not cast the total back to bigint or through float/JSON number.
      %{rows: [[total]]} =
        repo.query!(
          """
          SELECT COALESCE(SUM(e.units), 0)::text
          FROM mixer_billing_usage_entries e
          WHERE e.tenant_id = $1 AND e.metric = $2 AND e.platform = $3
            AND e.period_start = $4 AND e.period_end = $5
            AND NOT EXISTS (SELECT 1 FROM mixer_billing_usage_entries c WHERE c.correction_of = e.id)
          """,
          Enum.map(@scope_fields, &Map.fetch!(scope, &1))
        )

      {:ok, String.to_integer(total)}
    end
  end

  @spec entries(module(), Scope.t()) :: {:ok, [UsageEntry.t()]} | {:error, :invalid_scope}
  def entries(repo, requested_scope) do
    with {:ok, scope} <- scope(requested_scope) do
      {:ok, repo.all(from(e in scoped(scope), order_by: [asc: e.source, asc: e.source_key]))}
    end
  end

  defp persist(repo, row) do
    # Serializes competing identities for this tenant/source/key, including when
    # no row exists yet. Hash collisions serialize unrelated keys without harm.
    repo.query!("SELECT pg_advisory_xact_lock(hashtextextended($1, 0))", [
      Jason.encode!([row.tenant_id, row.source, row.source_key])
    ])

    existing = repo.get_by(UsageEntry, Map.take(row, [:tenant_id, :source, :source_key]))

    cond do
      existing != nil ->
        fields = @scope_fields ++ [:source, :source_key, :units, :correction_of]

        if Map.take(existing, fields) == Map.take(row, fields),
          do: {:ok, :duplicate, existing},
          else: repo.rollback(:identity_conflict)

      row.correction_of == nil ->
        insert(repo, row)

      true ->
        # Scope the parent lookup before locking; tenant probes reveal nothing.
        parent =
          repo.one(
            from(e in scoped(struct!(Scope, Map.take(row, @scope_fields))),
              where: e.id == ^row.correction_of and e.source == ^row.source,
              lock: "FOR UPDATE"
            )
          )

        cond do
          parent == nil ->
            repo.rollback(:predecessor_unavailable)

          repo.exists?(from(e in UsageEntry, where: e.correction_of == ^parent.id)) ->
            repo.rollback(:predecessor_superseded)

          true ->
            insert(repo, row)
        end
    end
  end

  defp insert(repo, row) do
    {:ok, entry} =
      repo.insert(
        struct!(
          UsageEntry,
          Map.merge(row, %{
            id: Ecto.UUID.generate(),
            inserted_at: DateTime.utc_now()
          })
        )
      )

    {:ok, :appended, entry}
  end

  defp scoped(scope) do
    from(e in UsageEntry,
      where:
        e.tenant_id == ^scope.tenant_id and
          e.metric == ^scope.metric and e.platform == ^scope.platform and
          e.period_start == ^scope.period_start and e.period_end == ^scope.period_end
    )
  end

  defp observation(
         %{scope: requested_scope, source: source, source_key: key, units: units} = value
       )
       when not is_struct(value) do
    parent = Map.get(value, :correction_of)

    with true <- Enum.all?(Map.keys(value), &(&1 in @observation_fields)),
         {:ok, scope} <- scope(requested_scope),
         true <- identity?(source) and identity?(key),
         true <- is_integer(units) and units >= 0 and units <= @max_units,
         true <- is_nil(parent) or match?({:ok, ^parent}, Ecto.UUID.cast(parent)),
         true <-
           scope.metric != "active_update_installations" or
             (units in [0, 1] and (parent != nil or units == 1)) do
      {:ok,
       Map.merge(Map.from_struct(scope), %{
         source: source,
         source_key: key,
         units: units,
         correction_of: parent
       })}
    else
      _ -> {:error, :invalid_observation}
    end
  end

  defp observation(_), do: {:error, :invalid_observation}

  defp identity?(value),
    do:
      is_binary(value) and byte_size(value) in 1..128 and
        String.valid?(value) and String.printable?(value) and
        Enum.all?(:binary.bin_to_list(value), &(&1 >= 32 and &1 != 127))

  defp metric_scope?("build_elapsed_milliseconds", platform, _, _),
    do: platform in ["ios", "android"]

  defp metric_scope?("storage_byte_seconds", "all", _, _), do: true

  defp metric_scope?("active_update_installations", "all", first, last) do
    {:ok, start} = DateTime.from_unix(first)
    {:ok, finish} = DateTime.from_unix(last)

    start.day == 1 and start.hour == 0 and start.minute == 0 and start.second == 0 and
      finish.day == 1 and finish.hour == 0 and finish.minute == 0 and finish.second == 0 and
      finish.year * 12 + finish.month == start.year * 12 + start.month + 1
  end

  defp metric_scope?(_, _, _, _), do: false
end
