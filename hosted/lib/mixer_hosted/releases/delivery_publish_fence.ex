defmodule MixerHosted.Releases.DeliveryPublishFence do
  @moduledoc """
  Internal authority for a single pointer compare-and-swap (CAS).

  Pass the exact projection from `DeliveryExport.current/1`. With an explicit
  grant on the opt-in locking function, this operation locks the enrollment
  and head and verifies the projection again inside the same transaction.
  A sibling publisher can share those locks. The pointer CAS still decides
  which publisher applied its update.

  The callback runs in a linked task with a monotonic deadline and the
  export's exclusive Unix-second validity bound. It must perform one
  synchronous, deadline-aware CAS without background writes and return
  `:applied`, `:conflict`, or `:indeterminate`. Any conflict is a refusal,
  including when the competing pointer has identical content. An issued
  external write may have taken effect on timeout, disconnect or failed
  commit. Reconcile against the pointer store and reacquire authority before
  any subsequent write.

  The locking transaction requires PostgreSQL 17 or later for its
  server-side transaction timeout. The positive result describes the CAS
  under the locked authority. Another publication can advance the head after
  the transaction commits.

  Trust configuration comes from the local release delivery startup
  snapshot. Drain publishers before replacing that configuration or its
  roots. The fence rereads the snapshot around the callback and refuses
  acknowledgement on an observed change. Application environment writes
  have no PostgreSQL lock and a change reverted between reads is unobservable.
  """

  alias Ecto.Adapters.SQL
  alias MixerHosted.Releases.{DeliveryExport, DeliveryRepo, PublicDelivery, Target}

  @query "SELECT * FROM public.mixer_release_delivery_lock_current($1,$2,$3,$4,$5,$6,$7)"
  @limits """
  SELECT set_config('transaction_timeout', '5000ms', true),
         set_config('statement_timeout', '2500ms', true),
         set_config('lock_timeout', '250ms', true)
  """
  @db_options [timeout: 5_000, queue: false, log: false]
  @callback_ms 1_000

  @type deadline :: %{deadline_monotonic_ms: integer(), valid_until_unix: integer() | nil}
  @type cas_result :: :applied | :conflict | :indeterminate

  @spec with_current(Target.t(), map(), (deadline() -> cas_result())) ::
          {:ok, :applied} | {:error, atom()}
  def with_current(%Target{} = target, expected, cas)
      when is_map(expected) and is_function(cas, 1) do
    cas_state = make_ref()

    try do
      with {:ok, config} <- PublicDelivery.configuration(),
           {:ok, _} <- PublicDelivery.select(config, target),
           false <- DeliveryRepo.checked_out?() do
        transact(target, expected, config, cas, cas_state)
      else
        :error -> {:error, :not_found}
        _ -> {:error, :unavailable}
      end
    rescue
      DBConnection.ConnectionError ->
        transaction_failure(cas_state)

      error in RuntimeError ->
        if Process.whereis(DeliveryRepo),
          do: reraise(error, __STACKTRACE__),
          else: transaction_failure(cas_state)
    after
      Process.delete(cas_state)
    end
  end

  def with_current(_, _, _), do: {:error, :rejected}

  defp transact(target, expected, config, cas, cas_state) do
    deadline = System.monotonic_time(:millisecond) + @db_options[:timeout]

    result =
      DeliveryRepo.transaction(
        fn ->
          case locked_cas(target, expected, config, deadline, cas, cas_state) do
            {:ok, applied} -> applied
            {:error, reason} -> DeliveryRepo.rollback(reason)
          end
        end,
        @db_options
      )

    case result do
      {:ok, {window, verified_at}} ->
        if current?(config, window, verified_at),
          do: {:ok, :applied},
          else: {:error, :indeterminate}

      {:error, :rollback} ->
        transaction_failure(cas_state)

      {:error, _} = error ->
        error
    end
  end

  defp transaction_failure(cas_state), do: {:error, Process.get(cas_state, :unavailable)}

  defp locked_cas(target, expected, config, deadline, cas, cas_state) do
    with {:ok, _} <- SQL.query(DeliveryRepo, @limits, [], @db_options),
         :ok <- lock_current(target),
         now = System.system_time(:millisecond),
         {:ok, ^expected} <- DeliveryExport.current_in_transaction(target),
         {:ok, ^config} <- PublicDelivery.configuration(),
         {:ok, window} <- callback_window(expected.valid_until_unix, now, deadline),
         :applied <- run_cas(cas, window, cas_state) do
      with true <- current?(config, window, now),
           {:ok, _} <- SQL.query(DeliveryRepo, "SELECT 1", [], @db_options) do
        {:ok, {window, now}}
      else
        _ -> {:error, :indeterminate}
      end
    else
      :conflict -> {:error, :conflict}
      :indeterminate -> {:error, :indeterminate}
      {:error, %Postgrex.Error{postgres: %{code: :lock_not_available}}} -> {:error, :busy}
      {:error, %Postgrex.Error{}} -> {:error, :unavailable}
      {:error, %DBConnection.ConnectionError{}} -> {:error, :unavailable}
      {:error, reason} when is_atom(reason) -> {:error, reason}
      _ -> {:error, :rejected}
    end
  end

  defp lock_current(%Target{scope: scope} = target) do
    args = [
      scope.organization_id,
      scope.project_id,
      scope.application_id,
      scope.environment_id,
      target.platform,
      target.runtime_sha256,
      target.channel
    ]

    case SQL.query(DeliveryRepo, @query, args, @db_options) do
      {:ok, %{rows: [[true]]}} -> :ok
      {:ok, %{rows: [[false]]}} -> {:error, :not_found}
      {:error, _} = error -> error
      _ -> {:error, :unavailable}
    end
  end

  defp callback_window(expiry, verified_at, transaction_deadline) do
    now = System.system_time(:millisecond)
    monotonic = System.monotonic_time(:millisecond)
    deadline = min(transaction_deadline, monotonic + @callback_ms)
    deadline = if expiry, do: min(deadline, monotonic + expiry * 1000 - now), else: deadline

    if now >= verified_at and monotonic < deadline do
      {:ok, %{deadline_monotonic_ms: deadline, valid_until_unix: expiry}}
    else
      {:error, :rejected}
    end
  end

  defp current?(config, window, verified_at) do
    now = System.system_time(:millisecond)

    System.monotonic_time(:millisecond) < window.deadline_monotonic_ms and now >= verified_at and
      (is_nil(window.valid_until_unix) or now < window.valid_until_unix * 1000) and
      PublicDelivery.configuration() == {:ok, config}
  end

  defp run_cas(cas, window, cas_state) do
    # The transaction can fail after its body returns and the pointer CAS may already have run.
    Process.put(cas_state, :indeterminate)

    task =
      Task.async(fn ->
        try do
          cas.(window)
        catch
          _, _ -> :indeterminate
        end
      end)

    remaining = max(0, window.deadline_monotonic_ms - System.monotonic_time(:millisecond))

    case Task.yield(task, remaining) || Task.shutdown(task, :brutal_kill) do
      {:ok, :conflict} ->
        Process.put(cas_state, :conflict)
        :conflict

      {:ok, :applied} ->
        :applied

      _ ->
        :indeterminate
    end
  end
end
