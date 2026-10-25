defmodule MixerHosted.Builds.Storage do
  @moduledoc """
  Internal transactional storage for replayable per-platform build decisions.

  This is NOT an authorization boundary. Scope identifies data; it grants no
  permission. No HTTP route or production consumer calls this module yet.
  Future callers must authorize inside the same transaction using authoritative
  membership and storage policy. Runtime role/RLS qualification remains pending.

  Mutations return Ecto.Multi fragments. For an applied decision only, a trusted
  internal factory receives the exact intent and returns an Oban.Job changeset.
  The factory must not perform external effects. Both the domain mutation and
  job insert commit or roll back together with the caller's surrounding Multi.
  No production dispatcher is supplied; the test worker demonstrates atomic
  composition only. Jobs and lifecycle references do not grant worker authority.
  """
  import Ecto.Query
  alias Ecto.{Changeset, Multi}
  alias MixerHosted.Builds.{Journal, Record}
  alias MixerHosted.Repo

  @scope [:organization_id, :project_id, :application_id, :build_id, :platform]

  @doc "Exact-scope internal read. Does not authenticate or authorize the caller."
  def read(scope) do
    with {:ok, scope} <- normalize_scope(scope),
         %Record{} = record <- Repo.one(scoped(scope)),
         {:ok, build} <- replay(record) do
      {:ok, %{record: record, build: build}}
    else
      nil -> {:error, :not_found}
      error -> error
    end
  end

  @doc "Adds creation plus a caller-supplied, exactly bound Oban intent to a Multi."
  def create_multi(%Multi{} = multi, name, spec, policy, key, now, job_factory)
      when is_function(job_factory, 1) do
    multi
    |> Multi.run(name, fn repo, _ -> create(repo, spec, policy, key, now) end)
    |> with_job(name, job_factory)
  end

  @doc "Adds a locked revision-CAS transition and its atomic intent to a Multi."
  def transition_multi(%Multi{} = multi, name, scope, revision, event_id, event, now, job_factory)
      when is_function(job_factory, 1) do
    multi
    |> Multi.run(name, fn repo, _ ->
      transition(repo, scope, revision, event_id, event, now)
    end)
    |> with_job(name, job_factory)
  end

  def cancel_multi(multi, name, scope, revision, event_id, reason, now, job_factory) do
    transition_multi(
      multi,
      name,
      scope,
      revision,
      event_id,
      %{type: :cancel, reason: reason},
      now,
      job_factory
    )
  end

  defp create(repo, spec, policy, key, now) do
    with {:ok, journal, build} <- Journal.new(spec, policy, key, now) do
      scope = wire_scope(build.spec)
      at = DateTime.utc_now()

      attrs =
        Map.merge(scope, %{
          id: Ecto.UUID.generate(),
          request_key: key,
          revision: 0,
          journal: journal,
          inserted_at: at,
          updated_at: at
        })

      case repo.insert_all(Record, [attrs], on_conflict: :nothing, returning: [:id]) do
        {1, [%{id: id}]} ->
          record = repo.one!(from(r in scoped(scope), where: r.id == ^id))
          {:ok, decision(record, build, :applied, "created")}

        {0, []} ->
          existing_creation(repo, scope, key, journal)
      end
    end
  end

  defp existing_creation(repo, scope, key, requested) do
    query =
      from(r in Record,
        where:
          r.organization_id == ^scope.organization_id and r.project_id == ^scope.project_id and
            r.application_id == ^scope.application_id and r.platform == ^scope.platform and
            r.request_key == ^key,
        lock: "FOR UPDATE"
      )

    case repo.one(query) do
      nil ->
        {:error, :build_conflict}

      record ->
        with {:ok, build} <- replay(record) do
          # Receipt time is not request identity; the first creation time wins.
          if Map.drop(record.journal["creation"], ["now_ms"]) ==
               Map.drop(requested["creation"], ["now_ms"]) do
            {:ok, decision(record, build, :duplicate, nil)}
          else
            {:error, :idempotency_conflict}
          end
        end
    end
  end

  defp transition(repo, scope, revision, event_id, event, now) do
    with {:ok, scope} <- normalize_scope(scope),
         true <- is_integer(revision) and revision in 0..32,
         %Record{} = record <- repo.one(from(r in scoped(scope), lock: "FOR UPDATE")),
         {:ok, current} <- replay(record),
         :ok <- revision_matches(record, current, event_id, revision),
         {:ok, journal, build, outcome} <- Journal.append(record.journal, event_id, event, now) do
      cond do
        outcome == :duplicate ->
          {:ok, decision(record, build, :duplicate, nil)}

        true ->
          next = revision + 1
          at = DateTime.utc_now()

          {count, _} =
            repo.update_all(
              from(r in scoped(scope), where: r.id == ^record.id and r.revision == ^revision),
              set: [journal: journal, revision: next, updated_at: at]
            )

          if count == 1 do
            updated = %{record | journal: journal, revision: next, updated_at: at}
            {:ok, decision(updated, build, :applied, Atom.to_string(event.type))}
          else
            {:error, :stale_revision}
          end
      end
    else
      nil -> {:error, :not_found}
      false -> {:error, :invalid_revision}
      error -> error
    end
  end

  defp revision_matches(record, build, event_id, revision) do
    if record.revision == revision or Map.has_key?(build.events, event_id),
      do: :ok,
      else: {:error, :stale_revision}
  end

  defp with_job(multi, name, factory) do
    Multi.merge(multi, fn results ->
      result = Map.fetch!(results, name)

      if result.outcome == :duplicate do
        Multi.new() |> Multi.put({name, :job}, nil)
      else
        Multi.new()
        |> Multi.run({name, :job_changeset}, fn _repo, _ ->
          case factory.(result.intent) do
            %Changeset{data: %Oban.Job{}, valid?: true} = changeset ->
              normalize_job(changeset, result.intent)

            _ ->
              {:error, :invalid_job_changeset}
          end
        end)
        |> Oban.insert({name, :job}, fn changes -> Map.fetch!(changes, {name, :job_changeset}) end)
        |> Multi.run({name, :job_verified}, fn _repo, changes ->
          inserted = Map.fetch!(changes, {name, :job})

          if is_integer(inserted.id) and inserted.id > 0 and not inserted.conflict? and
               inserted.args == result.intent and inserted.queue == "builds" and
               inserted.state in ["available", "scheduled"] and inserted.attempt == 0 do
            {:ok, inserted.id}
          else
            {:error, :invalid_inserted_job}
          end
        end)
      end
    end)
  end

  defp normalize_job(changeset, intent) do
    fields = [:args, :queue, :worker, :max_attempts, :priority, :scheduled_at, :state]
    fields_only = Enum.all?(Map.keys(changeset.changes), &(&1 in fields))
    job = Changeset.apply_changes(changeset)

    if changeset.data == %Oban.Job{} and fields_only and changeset.prepare == [] and
         changeset.repo_opts == [] and changeset.filters == %{} and
         changeset.action in [nil, :insert] and job.args == intent and job.queue == "builds" and
         job.state in ["available", "scheduled"] and
         is_integer(job.max_attempts) and job.max_attempts in 1..20 do
      # Rebuild from a closed allowlist so caller changeset metadata, constraints
      # or callbacks cannot redirect insertion or mutate the verified intent.
      canonical =
        Oban.Job.new(intent,
          queue: "builds",
          worker: job.worker,
          max_attempts: job.max_attempts,
          priority: job.priority,
          scheduled_at: job.scheduled_at,
          state: job.state
        )

      if canonical.valid?, do: {:ok, canonical}, else: {:error, :invalid_job_changeset}
    else
      {:error, :invalid_job_binding}
    end
  end

  defp decision(record, build, outcome, kind) do
    intent =
      if outcome == :applied do
        record
        |> Map.take(@scope)
        |> Map.new(fn {key, value} -> {Atom.to_string(key), value} end)
        |> Map.merge(%{
          "build_record_id" => record.id,
          "revision" => record.revision,
          "attempt" => build.attempt,
          "fence" => build.fence,
          "kind" => kind
        })
      end

    %{record: record, build: build, outcome: outcome, intent: intent}
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

  defp scoped(scope) do
    from(r in Record,
      where:
        r.organization_id == ^scope.organization_id and r.project_id == ^scope.project_id and
          r.application_id == ^scope.application_id and r.build_id == ^scope.build_id and
          r.platform == ^scope.platform
    )
  end

  defp normalize_scope(value) when is_map(value) and map_size(value) == 5 do
    if Enum.all?(@scope, &Map.has_key?(value, &1)) and
         value.platform in [:ios, :android] and
         Enum.all?(@scope -- [:platform], fn key ->
           text = Map.fetch!(value, key)

           is_binary(text) and byte_size(text) in 1..128 and String.valid?(text) and
             String.printable?(text)
         end) do
      {:ok, %{value | platform: Atom.to_string(value.platform)}}
    else
      {:error, :invalid_scope}
    end
  end

  defp normalize_scope(_), do: {:error, :invalid_scope}

  defp wire_scope(spec),
    do: spec |> Map.take(@scope) |> Map.put(:platform, Atom.to_string(spec.platform))
end
