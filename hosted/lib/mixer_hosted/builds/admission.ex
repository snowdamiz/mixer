defmodule MixerHosted.Builds.Admission do
  @moduledoc """
  Internal, PostgreSQL-serialized fleet and organization build occupancy and
  coordinator ownership. These APIs provide no tenant or worker authorization.

  Claiming reserves capacity only; external dispatch requires a committed
  lifecycle start first. The reservation survives lease expiry and uncertainty.
  Lease epochs and worker lifecycle fences are independent. All mutations are
  Multi fragments. Every fragment first takes the same transaction advisory
  mutex, then fleet -> platform -> organization -> organization/platform ->
  build -> reservation -> lease locks. Do not acquire raw locks on these tables
  before the first Admission fragment in a composed transaction.
  """
  import Ecto.Query
  alias Ecto.Multi
  alias MixerHosted.Builds.{Journal, Record, Storage}

  alias __MODULE__.{
    Capacity,
    FleetCapacity,
    FleetPlatformCapacity,
    OrganizationCapacity,
    Lease,
    Reservation,
    Token
  }

  @scope [:organization_id, :project_id, :application_id, :build_id, :platform]
  @max_int 9_223_372_036_854_775_807
  @terminal [:succeeded, :failed, :cancelled, :timed_out]

  defmodule FleetCapacity do
    @moduledoc false
    use Ecto.Schema
    @primary_key {:id, :string, autogenerate: false}
    schema "mixer_build_fleet_capacity" do
      field(:limit, :integer, default: 0)
      field(:revision, :integer, default: 0)
      field(:configured, :boolean, default: false)
    end
  end

  defmodule FleetPlatformCapacity do
    @moduledoc false
    use Ecto.Schema
    @primary_key {:platform, :string, autogenerate: false}
    schema "mixer_build_fleet_platform_capacities" do
      field(:limit, :integer, default: 0)
      field(:revision, :integer, default: 0)
      field(:configured, :boolean, default: false)
    end
  end

  defmodule OrganizationCapacity do
    @moduledoc false
    use Ecto.Schema
    @primary_key {:organization_id, :string, autogenerate: false}
    schema "mixer_build_organization_capacities" do
      field(:limit, :integer, default: 0)
      field(:revision, :integer, default: 0)
      field(:configured, :boolean, default: false)
    end
  end

  defmodule Capacity do
    @moduledoc false
    use Ecto.Schema
    @primary_key false
    schema "mixer_build_capacities" do
      field(:organization_id, :string, primary_key: true)
      field(:platform, :string, primary_key: true)
      field(:limit, :integer)
      field(:revision, :integer)
    end
  end

  defmodule Reservation do
    @moduledoc false
    use Ecto.Schema
    @primary_key {:build_record_id, :binary_id, autogenerate: false}
    schema "mixer_build_reservations" do
      field(:organization_id, :string)
      field(:platform, :string)
      field(:attempt, :integer)
      field(:worker_fence, :integer)
      field(:held, :boolean)
      field(:terminal_event_id, :string)
    end
  end

  defmodule Lease do
    @moduledoc false
    use Ecto.Schema
    @primary_key {:build_record_id, :binary_id, autogenerate: false}
    schema "mixer_build_coordinator_leases" do
      field(:owner_id, :string)
      field(:epoch, :integer)
      field(:expires_at, :utc_datetime_usec)
    end
  end

  defmodule Token do
    @moduledoc "Internal coordinator reference data, never authentication or worker authority."
    @enforce_keys [:scope, :record_id, :attempt, :owner_id, :epoch]
    defstruct @enforce_keys
  end

  @doc "Explicit internal configuration; :new creates revision 0, integer revisions use CAS."
  def configure_multi(%Multi{} = multi, name, scope, revision, limit) do
    Multi.run(multi, name, fn repo, _ -> configure(repo, scope, revision, limit) end)
  end

  @doc "Explicit fleet-total configuration; new closed placeholders require :new activation."
  def configure_fleet_multi(%Multi{} = multi, name, revision, limit) do
    Multi.run(multi, name, fn repo, _ ->
      configure_aggregate(repo, :fleet, %{}, revision, limit)
    end)
  end

  @doc "Explicit fleet platform-pool configuration, independently bounded for iOS and Android."
  def configure_fleet_platform_multi(%Multi{} = multi, name, scope, revision, limit) do
    Multi.run(multi, name, fn repo, _ ->
      configure_aggregate(repo, :platform, scope, revision, limit)
    end)
  end

  @doc "Explicit organization-total configuration, shared by both platform pools."
  def configure_organization_multi(%Multi{} = multi, name, scope, revision, limit) do
    Multi.run(multi, name, fn repo, _ ->
      configure_aggregate(repo, :organization, scope, revision, limit)
    end)
  end

  @doc "Claims a queued attempt, or reclaims the same held attempt for reconciliation."
  def claim_multi(%Multi{} = multi, name, scope, owner_id, ttl_ms) do
    Multi.run(multi, name, fn repo, _ -> claim(repo, scope, owner_id, ttl_ms) end)
  end

  @doc "Renews a live, exactly fenced coordinator lease using database time after locks."
  def renew_multi(%Multi{} = multi, name, token, ttl_ms) do
    Multi.run(multi, name, fn repo, _ ->
      with true <- ttl?(ttl_ms),
           {:ok, context} <- guard(repo, token) do
        lease = %{context.lease | expires_at: DateTime.add(context.now, ttl_ms, :millisecond)}
        persist_lease(repo, lease)
        {:ok, result(%{context | lease: lease}, :renewed)}
      else
        false -> {:error, :invalid_lease_policy}
        error -> error
      end
    end)
  end

  @doc "Guards a lifecycle mutation, composing its CAS and Oban insert in the same Multi."
  def transition_multi(%Multi{} = multi, name, token, revision, event_id, event, factory)
      when is_function(factory, 1) do
    multi
    |> Multi.run({name, :admission}, fn repo, _ ->
      if is_map(event) and
           Map.get(event, :type) in [:start, :cancel, :expire, :completed, :stopped],
         do: guard(repo, token),
         else: {:error, :invalid_guarded_event}
    end)
    |> Multi.merge(fn changes ->
      context = Map.fetch!(changes, {name, :admission})

      Storage.transition_multi(
        Multi.new(),
        name,
        token.scope,
        revision,
        event_id,
        event,
        context.now_ms,
        factory
      )
    end)
  end

  @doc "Releases matching definitive termination, or a conclusively never-started queued cancellation."
  def release_multi(%Multi{} = multi, name, token, terminal_event_id) do
    Multi.run(multi, name, fn repo, _ ->
      with true <- text?(terminal_event_id, 128),
           {:ok, context} <- guard(repo, token),
           :ok <- terminal_evidence(context, terminal_event_id) do
        reservation = %{context.reservation | held: false, terminal_event_id: terminal_event_id}
        lease = %{context.lease | owner_id: nil, expires_at: nil}
        persist_reservation(repo, reservation)
        persist_lease(repo, lease)
        {:ok, result(%{context | reservation: reservation, lease: lease}, :released)}
      else
        false -> {:error, :invalid_terminal_event_id}
        error -> error
      end
    end)
  end

  @doc "Yields coordination immediately without releasing capacity or changing the worker fence."
  def yield_multi(%Multi{} = multi, name, token) do
    Multi.run(multi, name, fn repo, _ ->
      with {:ok, context} <- guard(repo, token) do
        lease = %{context.lease | expires_at: context.now}
        persist_lease(repo, lease)
        {:ok, result(%{context | lease: lease}, :yielded)}
      end
    end)
  end

  @doc "Retries only the current definitively released attempt, using locked database time."
  def retry_multi(%Multi{} = multi, name, scope, revision, event_id, factory)
      when is_function(factory, 1) do
    multi
    |> Multi.run({name, :admission}, fn repo, _ ->
      with true <- is_integer(revision) and revision in 0..32,
           {:ok, context} <- locked(repo, scope),
           :ok <- valid_reservation(context),
           true <- context.record.revision == revision,
           %Reservation{held: false} = reservation <- context.reservation,
           true <- reservation.attempt == context.build.attempt,
           true <- context.build.state in @terminal,
           true <- is_nil(context.lease.owner_id) and is_nil(context.lease.expires_at),
           true <- released_evidence?(context, reservation.terminal_event_id) do
        {:ok, context}
      else
        false -> {:error, :released_current_attempt_required}
        nil -> {:error, :released_current_attempt_required}
        %Reservation{} -> {:error, :released_current_attempt_required}
        error -> error
      end
    end)
    |> Multi.merge(fn changes ->
      context = Map.fetch!(changes, {name, :admission})

      Storage.transition_multi(
        Multi.new(),
        name,
        scope,
        revision,
        event_id,
        %{type: :retry},
        context.now_ms,
        factory
      )
    end)
  end

  defp configure(repo, scope, revision, limit) do
    with {:ok, scope} <- capacity_scope(scope),
         true <- capacity_policy?(revision, limit),
         {:ok, _} <- lock_capacities(repo, scope) do
      if revision == :new do
        attrs = Map.merge(scope, %{limit: limit, revision: 0})

        case repo.insert_all(Capacity, [attrs], on_conflict: :nothing) do
          {1, _} -> {:ok, struct!(Capacity, attrs)}
          {0, _} -> {:error, :capacity_exists}
        end
      else
        case repo.one(from(c in capacity_query(scope), lock: "FOR UPDATE")) do
          nil ->
            {:error, :capacity_unconfigured}

          %Capacity{revision: ^revision} = capacity ->
            repo.update_all(capacity_query(scope), set: [limit: limit, revision: revision + 1])
            {:ok, %{capacity | limit: limit, revision: revision + 1}}

          _ ->
            {:error, :stale_capacity_revision}
        end
      end
    else
      false -> {:error, :invalid_capacity_policy}
      error -> error
    end
  end

  defp configure_aggregate(repo, kind, scope, revision, limit) do
    with {:ok, scope} <- aggregate_scope(kind, scope),
         true <- capacity_policy?(revision, limit),
         {:ok, capacities} <- lock_capacities(repo, scope) do
      capacity = Map.fetch!(capacities, kind)
      {schema, identity} = aggregate_identity(kind, scope)
      query = aggregate_query(schema, identity)

      cond do
        revision == :new and (capacity == nil or not capacity.configured) ->
          attrs = Map.merge(identity, %{limit: limit, revision: 0, configured: true})

          if capacity == nil,
            do: repo.insert!(struct!(schema, attrs)),
            else: repo.update_all(query, set: [limit: limit, revision: 0, configured: true])

          {:ok, struct!(schema, attrs)}

        revision == :new ->
          {:error, :capacity_exists}

        capacity == nil or not capacity.configured ->
          {:error, :capacity_unconfigured}

        capacity.revision != revision ->
          {:error, :stale_capacity_revision}

        true ->
          repo.update_all(query, set: [limit: limit, revision: revision + 1])
          {:ok, %{capacity | limit: limit, revision: revision + 1}}
      end
    else
      false -> {:error, :invalid_capacity_policy}
      error -> error
    end
  end

  defp capacity_policy?(revision, limit),
    do:
      is_integer(limit) and limit in 0..10_000 and
        (revision == :new or (is_integer(revision) and revision in 0..(@max_int - 1)))

  defp claim(repo, scope, owner_id, ttl_ms) do
    with true <- text?(owner_id, 128) and ttl?(ttl_ms),
         {:ok, context} <- locked(repo, scope),
         :ok <- valid_reservation(context),
         {:ok, context} <- reserve(repo, context),
         {:ok, context, outcome} <- take_lease(repo, context, owner_id, ttl_ms) do
      {:ok, result(context, outcome)}
    else
      false -> {:error, :invalid_lease_policy}
      error -> error
    end
  end

  defp reserve(_repo, %{reservation: %Reservation{held: true}} = context), do: {:ok, context}

  defp reserve(repo, context) do
    cond do
      context.build.state != :queued ->
        {:error, :not_queued}

      context.reservation != nil and context.reservation.attempt >= context.build.attempt ->
        {:error, :attempt_already_released}

      true ->
        with :ok <- available_capacity(repo, context) do
          reservation = %Reservation{
            build_record_id: context.record.id,
            organization_id: context.scope.organization_id,
            platform: context.scope.platform,
            attempt: context.build.attempt,
            worker_fence: context.build.fence,
            held: true,
            terminal_event_id: nil
          }

          if context.reservation == nil,
            do: repo.insert!(reservation),
            else: persist_reservation(repo, reservation)

          {:ok, %{context | reservation: reservation}}
        end
    end
  end

  defp available_capacity(repo, context) do
    held = from(r in Reservation, where: r.held)
    platform = from(r in held, where: r.platform == ^context.scope.platform)
    organization = from(r in held, where: r.organization_id == ^context.scope.organization_id)

    pair =
      from(r in organization,
        where: r.platform == ^context.scope.platform
      )

    policies = [
      {context.capacities.fleet, held, :fleet_capacity_unconfigured, :fleet_capacity_exhausted},
      {context.capacities.platform, platform, :fleet_platform_capacity_unconfigured,
       :fleet_platform_capacity_exhausted},
      {context.capacities.organization, organization, :organization_capacity_unconfigured,
       :organization_capacity_exhausted},
      {context.capacity, pair, :scope_not_found_or_unconfigured, :capacity_exhausted}
    ]

    Enum.reduce_while(policies, :ok, fn {capacity, query, missing, full}, _ ->
      cond do
        capacity == nil or Map.get(capacity, :configured, true) != true ->
          {:halt, {:error, missing}}

        repo.aggregate(query, :count) >= capacity.limit ->
          {:halt, {:error, full}}

        true ->
          {:cont, :ok}
      end
    end)
  end

  defp take_lease(repo, context, owner_id, ttl_ms) do
    lease = context.lease

    cond do
      lease != nil and live?(lease, context.now) and lease.owner_id == owner_id ->
        {:ok, context, :duplicate}

      lease != nil and live?(lease, context.now) ->
        {:error, :lease_held}

      lease != nil and lease.epoch == @max_int ->
        {:error, :lease_epoch_exhausted}

      true ->
        updated = %Lease{
          build_record_id: context.record.id,
          owner_id: owner_id,
          epoch: if(lease == nil, do: 1, else: lease.epoch + 1),
          expires_at: DateTime.add(context.now, ttl_ms, :millisecond)
        }

        if lease == nil, do: repo.insert!(updated), else: persist_lease(repo, updated)
        {:ok, %{context | lease: updated}, if(lease == nil, do: :acquired, else: :reclaimed)}
    end
  end

  defp guard(repo, token) do
    with :ok <- valid_token(token),
         {:ok, context} <- locked(repo, token.scope),
         :ok <- valid_reservation(context),
         true <-
           context.record.id == token.record_id and context.reservation != nil and
             context.reservation.held and context.reservation.attempt == token.attempt and
             context.lease != nil and context.lease.owner_id == token.owner_id and
             context.lease.epoch == token.epoch,
         true <- live?(context.lease, context.now) do
      {:ok, context}
    else
      false -> {:error, :stale_lease}
      error -> error
    end
  end

  defp locked(repo, scope) do
    with {:ok, scope} <- normalize_scope(scope),
         {:ok, capacities} <- lock_capacities(repo, scope),
         %Capacity{} = capacity <- capacities.capacity,
         %Record{} = record <- repo.one(from(b in build_query(scope), lock: "FOR UPDATE")),
         {:ok, build} <- replay(record) do
      reservation =
        repo.one(
          from(r in Reservation, where: r.build_record_id == ^record.id, lock: "FOR UPDATE")
        )

      lease =
        repo.one(from(l in Lease, where: l.build_record_id == ^record.id, lock: "FOR UPDATE"))

      # clock_timestamp, unlike transaction_timestamp/now(), advances during lock waits.
      %{rows: [[micros]]} =
        repo.query!("SELECT floor(extract(epoch FROM clock_timestamp()) * 1000000)::bigint")

      now = DateTime.from_unix!(micros, :microsecond)

      {:ok,
       %{
         scope: scope,
         capacity: capacity,
         capacities: capacities,
         record: record,
         build: build,
         reservation: reservation,
         lease: lease,
         now: now,
         now_ms: div(micros, 1000)
       }}
    else
      nil -> {:error, :scope_not_found_or_unconfigured}
      error -> error
    end
  end

  # The database mutex exists independently of all configuration rows, so missing
  # parents and first configuration serialize with claims too. It is retained
  # across every Multi fragment and rollback, and is reentrant in a transaction.
  # No transaction may take a raw admission/build row lock before this mutex.
  defp lock_capacities(repo, scope) do
    # Repeatable-read snapshots can predate a mutex wait and miss a reservation
    # committed by its former holder. Fail closed rather than weaken the caller's
    # isolation or silently count against an old snapshot.
    case repo.query!("SELECT current_setting('transaction_isolation')") do
      %{rows: [["read committed"]]} ->
        repo.query!("SELECT pg_advisory_xact_lock(1296648258, 1)")
        {:ok, lock_capacity_rows(repo, scope)}

      _ ->
        {:error, :unsupported_admission_isolation}
    end
  end

  defp lock_capacity_rows(repo, scope) do
    fleet = locked_capacity(repo, FleetCapacity, %{id: "fleet"})

    platform =
      if Map.has_key?(scope, :platform),
        do: locked_capacity(repo, FleetPlatformCapacity, Map.take(scope, [:platform]))

    organization =
      if Map.has_key?(scope, :organization_id),
        do: locked_capacity(repo, OrganizationCapacity, Map.take(scope, [:organization_id]))

    capacity =
      if Map.has_key?(scope, :organization_id) and Map.has_key?(scope, :platform),
        do: repo.one(from(c in capacity_query(scope), lock: "FOR UPDATE"))

    %{fleet: fleet, platform: platform, organization: organization, capacity: capacity}
  end

  defp locked_capacity(repo, schema, identity),
    do: repo.one(from(c in aggregate_query(schema, identity), lock: "FOR UPDATE"))

  defp aggregate_query(schema, identity), do: from(c in schema, where: ^Map.to_list(identity))

  defp aggregate_identity(:fleet, _), do: {FleetCapacity, %{id: "fleet"}}
  defp aggregate_identity(:platform, scope), do: {FleetPlatformCapacity, scope}
  defp aggregate_identity(:organization, scope), do: {OrganizationCapacity, scope}

  defp aggregate_scope(:fleet, %{} = scope) when map_size(scope) == 0, do: {:ok, scope}

  defp aggregate_scope(:platform, %{platform: platform} = scope)
       when map_size(scope) == 1 and platform in [:ios, :android],
       do: {:ok, %{platform: Atom.to_string(platform)}}

  defp aggregate_scope(:organization, %{organization_id: id} = scope) when map_size(scope) == 1,
    do: if(text?(id, 128), do: {:ok, scope}, else: {:error, :invalid_scope})

  defp aggregate_scope(_, _), do: {:error, :invalid_scope}

  defp valid_reservation(%{reservation: nil, lease: nil}), do: :ok
  defp valid_reservation(%{reservation: nil}), do: {:error, :invalid_admission}

  defp valid_reservation(context) do
    r = context.reservation
    l = context.lease
    history = Enum.find(context.build.history, &(&1.attempt == r.attempt))
    current = r.attempt == context.build.attempt

    expected_fence =
      cond do
        current and context.build.state == :queued ->
          context.build.fence

        current and context.build.active_ref != nil ->
          context.build.active_ref.fence

        history != nil and history.worker_ref != nil ->
          history.worker_ref.fence

        history != nil and history.started_at == nil ->
          # Queued cancellation never started a worker and advances the fence once.
          event =
            Enum.find(context.build.events, fn {_id, e} ->
              e.first_observed_at == history.finished_at and e.payload.type == :cancel
            end)

          if current and event != nil, do: context.build.fence - 1, else: nil

        true ->
          nil
      end

    if r.organization_id == context.scope.organization_id and r.platform == context.scope.platform and
         is_integer(r.attempt) and r.attempt in 1..context.build.attempt and
         r.worker_fence == expected_fence and is_boolean(r.held) and
         (not r.held or current) and l != nil and l.build_record_id == r.build_record_id and
         is_integer(l.epoch) and l.epoch in 1..@max_int and
         ((r.held and text?(l.owner_id, 128) and match?(%DateTime{}, l.expires_at) and
             is_nil(r.terminal_event_id)) or
            (not r.held and is_nil(l.owner_id) and is_nil(l.expires_at) and
               text?(r.terminal_event_id, 128) and
               released_evidence?(context, r.terminal_event_id))) do
      :ok
    else
      {:error, :invalid_admission}
    end
  end

  defp terminal_evidence(context, event_id) do
    r = context.reservation

    if context.build.state in @terminal and context.build.attempt == r.attempt and
         released_evidence?(context, event_id) do
      :ok
    else
      {:error, :definitive_terminal_evidence_required}
    end
  end

  defp released_evidence?(context, event_id) do
    event = Map.get(context.build.events, event_id)
    r = context.reservation
    terminal = Enum.find(context.build.history, &(&1.attempt == r.attempt))

    if terminal != nil and event != nil and event.first_observed_at == terminal.finished_at do
      cond do
        event.payload.type in [:completed, :stopped] ->
          terminal.worker_ref != nil and event.payload.ref == terminal.worker_ref and
            terminal.worker_ref.attempt == r.attempt and
            terminal.worker_ref.fence == r.worker_fence

        event.payload.type == :cancel ->
          # The replayed history proves no start was persisted. A capacity claim
          # itself cannot dispatch work; only a committed start permits dispatch.
          terminal.state == :cancelled and terminal.worker_ref == nil and
            terminal.started_at == nil and terminal.deadline == nil and
            context.build.attempt == r.attempt and context.build.fence == r.worker_fence + 1

        true ->
          false
      end
    else
      false
    end
  end

  defp replay(record) do
    with {:ok, build} <- Journal.restore(record.journal),
         true <- wire_scope(build.spec) == Map.take(record, @scope),
         true <- build.request_key == record.request_key,
         true <- record.revision == length(record.journal["events"]) do
      {:ok, build}
    else
      _ -> {:error, :invalid_journal}
    end
  end

  defp valid_token(%Token{} = token) do
    with true <-
           Map.keys(Map.from_struct(token)) |> Enum.sort() ==
             Enum.sort([:scope, :record_id, :attempt, :owner_id, :epoch]),
         {:ok, _} <- normalize_scope(token.scope),
         {:ok, _} <- Ecto.UUID.cast(token.record_id),
         true <-
           text?(token.owner_id, 128) and is_integer(token.attempt) and token.attempt in 1..5 and
             is_integer(token.epoch) and token.epoch in 1..@max_int do
      :ok
    else
      _ -> {:error, :invalid_lease_token}
    end
  end

  defp valid_token(_), do: {:error, :invalid_lease_token}
  defp ttl?(ttl), do: is_integer(ttl) and ttl in 1..300_000

  defp live?(lease, now),
    do:
      lease.owner_id != nil and lease.expires_at != nil and
        DateTime.compare(now, lease.expires_at) == :lt

  defp result(context, outcome) do
    token =
      if outcome not in [:released, :yielded] do
        %Token{
          scope: Map.put(context.scope, :platform, context.build.spec.platform),
          record_id: context.record.id,
          attempt: context.reservation.attempt,
          owner_id: context.lease.owner_id,
          epoch: context.lease.epoch
        }
      end

    Map.merge(Map.take(context, [:record, :build, :reservation, :lease, :now_ms]), %{
      token: token,
      outcome: outcome
    })
  end

  defp persist_reservation(repo, reservation) do
    attrs =
      Map.take(reservation, [
        :organization_id,
        :platform,
        :attempt,
        :worker_fence,
        :held,
        :terminal_event_id
      ])
      |> Map.to_list()

    {1, _} =
      repo.update_all(
        from(r in Reservation, where: r.build_record_id == ^reservation.build_record_id),
        set: attrs
      )

    :ok
  end

  defp persist_lease(repo, lease) do
    {1, _} =
      repo.update_all(from(l in Lease, where: l.build_record_id == ^lease.build_record_id),
        set: [owner_id: lease.owner_id, epoch: lease.epoch, expires_at: lease.expires_at]
      )

    :ok
  end

  defp capacity_query(scope),
    do:
      from(c in Capacity,
        where: c.organization_id == ^scope.organization_id and c.platform == ^scope.platform
      )

  defp build_query(scope),
    do:
      from(b in Record,
        where:
          b.organization_id == ^scope.organization_id and b.project_id == ^scope.project_id and
            b.application_id == ^scope.application_id and b.build_id == ^scope.build_id and
            b.platform == ^scope.platform
      )

  defp wire_scope(spec),
    do: spec |> Map.take(@scope) |> Map.put(:platform, Atom.to_string(spec.platform))

  defp capacity_scope(value) do
    if is_map(value) and map_size(value) == 2 and text?(Map.get(value, :organization_id), 128) and
         Map.get(value, :platform) in [:ios, :android],
       do:
         {:ok,
          %{organization_id: value.organization_id, platform: Atom.to_string(value.platform)}},
       else: {:error, :invalid_scope}
  end

  defp normalize_scope(value) do
    if is_map(value) and map_size(value) == 5 and Enum.all?(@scope, &Map.has_key?(value, &1)) and
         Map.get(value, :platform) in [:ios, :android] and
         Enum.all?(@scope -- [:platform], &text?(Map.get(value, &1), 128)),
       do: {:ok, %{value | platform: Atom.to_string(value.platform)}},
       else: {:error, :invalid_scope}
  end

  defp text?(value, max),
    do:
      is_binary(value) and byte_size(value) in 1..max and String.valid?(value) and
        String.printable?(value)
end
