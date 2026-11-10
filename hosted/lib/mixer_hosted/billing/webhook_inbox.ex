defmodule MixerHosted.Billing.WebhookInbox do
  @moduledoc """
  Verified, endpoint-scoped durable Stripe admission after exact-byte capture.

  Configuration is trusted server state, never request parameters. The worker
  must reconcile current Stripe state using the persisted inbox identity; event
  snapshots confer no organization permission and never apply billing state.
  This component does not mount a route or start the private transport role.
  """
  alias MixerHosted.Billing.{WebhookEvent, WebhookSignature}
  alias MixerHosted.Repo

  @types %{
    "customer.subscription.created" => "subscription",
    "customer.subscription.updated" => "subscription",
    "customer.subscription.deleted" => "subscription",
    "invoice.paid" => "invoice",
    "invoice.payment_failed" => "invoice",
    "invoice.finalized" => "invoice",
    "invoice.voided" => "invoice",
    "invoice.marked_uncollectible" => "invoice",
    "invoice.payment_succeeded" => "invoice",
    "checkout.session.completed" => "checkout.session",
    "checkout.session.async_payment_succeeded" => "checkout.session",
    "checkout.session.expired" => "checkout.session"
  }

  def admit(%{raw_body: body, signature_header_values: headers}, config) do
    with :ok <- configured(config),
         :ok <-
           WebhookSignature.verify(body, headers, config.secrets, System.system_time(:second)),
         {:ok, event} <- decode(body),
         {:ok, fields} <- scoped_event(event, config) do
      persist(
        Map.merge(fields, %{
          id: Ecto.UUID.generate(),
          endpoint_id: config.endpoint_id,
          account: config.account,
          livemode: config.livemode,
          body_sha256: :crypto.hash(:sha256, body),
          inserted_at: DateTime.utc_now()
        }),
        config.worker
      )
    end
  rescue
    _error in [DBConnection.ConnectionError, Postgrex.Error] -> {:error, :storage_unavailable}
  end

  def admit(_, _), do: {:error, :invalid_event}

  defp configured(%{
         endpoint_id: endpoint,
         account: account,
         livemode: mode,
         secrets: _,
         worker: worker
       })
       when is_binary(endpoint) and byte_size(endpoint) in 1..255 and
              (is_nil(account) or is_binary(account)) and is_boolean(mode) and is_atom(worker) do
    if Code.ensure_loaded?(worker) and function_exported?(worker, :new, 1) and
         function_exported?(worker, :perform, 1) and Oban.config().repo == Repo and
         Oban.Config.get_engine(Oban.config()) == Oban.Engines.Basic do
      :ok
    else
      {:error, :verification_unavailable}
    end
  rescue
    _error in [ArgumentError, RuntimeError] -> {:error, :verification_unavailable}
  end

  defp configured(_), do: {:error, :verification_unavailable}

  defp decode(body) do
    case Jason.decode(body, objects: :ordered_objects) do
      {:ok, value} -> unique_objects(value, 0)
      _ -> {:error, :invalid_event}
    end
  end

  # Reject ambiguous signed JSON, including nested duplicate keys.
  defp unique_objects(_, depth) when depth > 64, do: {:error, :invalid_event}

  defp unique_objects(%Jason.OrderedObject{values: pairs}, depth) do
    Enum.reduce_while(pairs, {:ok, %{}}, fn {key, value}, {:ok, acc} ->
      with false <- Map.has_key?(acc, key),
           {:ok, parsed} <- unique_objects(value, depth + 1) do
        {:cont, {:ok, Map.put(acc, key, parsed)}}
      else
        _ -> {:halt, {:error, :invalid_event}}
      end
    end)
  end

  defp unique_objects(values, depth) when is_list(values) do
    Enum.reduce_while(values, {:ok, []}, fn value, {:ok, acc} ->
      case unique_objects(value, depth + 1) do
        {:ok, parsed} -> {:cont, {:ok, [parsed | acc]}}
        error -> {:halt, error}
      end
    end)
    |> case do
      {:ok, parsed} -> {:ok, Enum.reverse(parsed)}
      error -> error
    end
  end

  defp unique_objects(value, _), do: {:ok, value}

  defp scoped_event(
         %{
           "object" => "event",
           "id" => id,
           "type" => type,
           "created" => created,
           "livemode" => mode,
           "data" => %{"object" => %{"id" => object_id, "object" => object_type}}
         } = event,
         config
       )
       when is_integer(created) and created >= 0 and created <= 253_402_300_799 do
    cond do
      mode !== config.livemode or Map.get(event, "account") !== config.account ->
        {:error, :wrong_scope}

      not identifier?(id, "evt_") or not identifier?(object_id, "") ->
        {:error, :invalid_event}

      not is_map_key(@types, type) or Map.get(@types, type) != object_type ->
        {:error, :unsupported_event}

      true ->
        {:ok, %{event_id: id, event_type: type, event_created: created, object_id: object_id}}
    end
  end

  defp scoped_event(_, _), do: {:error, :invalid_event}

  defp identifier?(value, prefix) when is_binary(value) and byte_size(value) in 1..255,
    do:
      String.starts_with?(value, prefix) and String.valid?(value) and
        Enum.all?(
          :binary.bin_to_list(value),
          &(&1 in ?a..?z or &1 in ?A..?Z or &1 in ?0..?9 or &1 == ?_)
        )

  defp identifier?(_, _), do: false

  defp persist(row, worker) do
    Ecto.Multi.new()
    |> Ecto.Multi.run(:event, fn repo, _ ->
      case repo.insert_all(WebhookEvent, [row],
             on_conflict: :nothing,
             conflict_target: [:endpoint_id, :event_id],
             returning: [:id]
           ) do
        {1, [%{id: id}]} ->
          {:ok, {:accepted, id}}

        {0, []} ->
          existing =
            repo.get_by!(WebhookEvent, endpoint_id: row.endpoint_id, event_id: row.event_id)

          if existing.body_sha256 == row.body_sha256 and existing.account == row.account and
               existing.livemode == row.livemode,
             do: {:ok, {:duplicate, existing.id}},
             else: {:error, :event_conflict}
      end
    end)
    |> Ecto.Multi.run(:job, fn _repo, %{event: event} ->
      case event do
        {:accepted, id} ->
          case Oban.insert(worker.new(%{"inbox_id" => id})) do
            {:ok, %Oban.Job{conflict?: true}} -> {:error, :enqueue_conflict}
            result -> result
          end

        {:duplicate, _} ->
          {:ok, nil}
      end
    end)
    |> Repo.transaction()
    |> case do
      {:ok, %{event: {status, id}}} -> {:ok, status, id}
      {:error, :event, reason, _} -> {:error, reason}
      {:error, :job, _, _} -> {:error, :enqueue_failed}
    end
  end
end
