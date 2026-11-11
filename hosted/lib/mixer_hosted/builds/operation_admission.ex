defmodule MixerHosted.Builds.OperationAdmission do
  @moduledoc """
  UNSELECTED private PostgreSQL admission primitives for trusted internal callers.

  This module deliberately does not implement Dispatch and never produces its
  Observation. Admission is not a launch, a stop intent is not a stopped worker,
  and an unadmitted query does not prove absence. Every result retains external
  execution uncertainty and capacity obligations. There is no executor here.

  The supplied repo is trusted transactional storage, not an HTTP authorization
  boundary. Direct SQL writers can fabricate their own rows; these bytes and
  constraints do not establish external provenance or authenticate any worker.
  No adapter is installed, no default configuration is changed, no row is pruned.
  """
  alias MixerHosted.Builds.Dispatch.Request
  alias MixerHosted.Builds.Lifecycle.{Spec, WorkerRef}

  defmodule Admission do
    @moduledoc "Storage decision only; never a Dispatch worker observation."
    @enforce_keys [:operation_id, :decision, :state, :version]
    defstruct @enforce_keys
    @type state :: :unadmitted | :admitted | :stop_intent
    @type decision ::
            :read
            | :admission_recorded
            | :admission_replay
            | :stop_recorded
            | :stop_replay
            | :fenced
    @type t :: %__MODULE__{
            operation_id: String.t(),
            decision: decision(),
            state: state(),
            version: {pos_integer(), non_neg_integer()}
          }
  end

  @type refusal ::
          :invalid_request | :identity_conflict | :stale | :deadline_expired | :unavailable
  @type result :: {:ok, Admission.t()} | {:error, refusal()}
  @max 9_223_372_036_854_775_807
  @scope [:organization_id, :project_id, :application_id, :build_id, :platform]
  @decisions %{
    "read" => :read,
    "admission_recorded" => :admission_recorded,
    "admission_replay" => :admission_replay,
    "stop_recorded" => :stop_recorded,
    "stop_replay" => :stop_replay,
    "fenced" => :fenced
  }
  @states %{"unadmitted" => :unadmitted, "admitted" => :admitted, "stop_intent" => :stop_intent}
  @refusals %{
    "invalid_request" => :invalid_request,
    "identity_conflict" => :identity_conflict,
    "stale" => :stale,
    "deadline_expired" => :deadline_expired
  }
  @sql "SELECT outcome, admission_state, lease_epoch, journal_revision FROM mixer_build_operation_admit($1, $2, $3, $4, $5, $6::text::uuid, $7, $8, $9, $10)"

  @spec query(module(), Request.t()) :: result()
  def query(repo, request), do: apply_request(repo, "query", request)
  @spec ensure_admitted(module(), Request.t()) :: result()
  def ensure_admitted(repo, request), do: apply_request(repo, "ensure", request)
  @spec stop_intent(module(), Request.t()) :: result()
  def stop_intent(repo, request), do: apply_request(repo, "stop", request)

  # Parameters are lossless deterministic Erlang terms, not JSON normalization
  # or only a digest: the database compares the complete original bytes.
  defp apply_request(repo, action, request) do
    with :ok <- request_shape(request),
         params = [
           action,
           request.operation_id,
           :erlang.term_to_binary(request.ref, [:deterministic]),
           :erlang.term_to_binary(request.spec, [:deterministic]),
           request.deadline_ms,
           request.guard.record_id,
           request.guard.epoch,
           request.guard.revision,
           request.guard.owner_id,
           request.guard.expires_at
         ],
         {:ok, %{rows: [row]}} <- repo.query(@sql, params) do
      decode(request.operation_id, row)
    else
      {:error, :invalid_request} = error -> error
      _ -> {:error, :unavailable}
    end
  end

  defp decode(id, [decision, state, epoch, revision])
       when is_integer(epoch) and is_integer(revision) do
    with {:ok, decision} <- Map.fetch(@decisions, decision),
         {:ok, state} <- Map.fetch(@states, state) do
      {:ok,
       %Admission{operation_id: id, decision: decision, state: state, version: {epoch, revision}}}
    else
      _ -> {:error, :unavailable}
    end
  end

  defp decode(_, [refusal, nil, nil, nil]),
    do: {:error, Map.get(@refusals, refusal, :unavailable)}

  defp decode(_, _), do: {:error, :unavailable}

  defp request_shape(%Request{ref: %WorkerRef{} = ref, spec: %Spec{} = spec, guard: guard} = r)
       when is_map(guard) and map_size(guard) == 5 do
    # Reject open or unbounded references before copying fields or serializing.
    # The existing Lifecycle contract bounds each scope ID to 128 UTF-8 bytes.
    with true <- closed_ref?(ref),
         {:ok, build} <-
           MixerHosted.Builds.Lifecycle.new(
             spec,
             %{max_attempts: 5, timeout_ms: 1, retry_backoff_ms: 0},
             "admission-shape",
             0
           ),
         {:ok, expected} <- MixerHosted.Builds.Lifecycle.worker_ref(build),
         true <- Map.take(ref, @scope) == Map.take(expected, @scope),
         true <- ref.attempt in 1..5 and is_integer(ref.attempt),
         true <- ref.fence in 1..@max,
         true <- is_binary(r.operation_id) and byte_size(r.operation_id) == 64,
         {:ok, _} <- Base.decode16(r.operation_id, case: :lower),
         true <- is_integer(r.deadline_ms) and r.deadline_ms in 0..@max,
         %{
           record_id: record,
           revision: revision,
           epoch: epoch,
           owner_id: owner,
           expires_at: %DateTime{}
         } <- guard,
         true <- is_binary(record) and valid_uuid?(record),
         true <- is_integer(revision) and revision in 0..32,
         true <- is_integer(epoch) and epoch in 1..@max,
         true <- is_binary(owner) and byte_size(owner) in 1..128,
         true <- String.valid?(owner) and String.printable?(owner) do
      :ok
    else
      _ -> {:error, :invalid_request}
    end
  end

  defp request_shape(_), do: {:error, :invalid_request}

  defp closed_ref?(
         %WorkerRef{
           organization_id: organization,
           project_id: project,
           application_id: application,
           build_id: build,
           platform: platform,
           attempt: attempt,
           fence: fence
         } = ref
       )
       when map_size(ref) == 8 and platform in [:ios, :android] and
              is_integer(attempt) and attempt in 1..5 and
              is_integer(fence) and fence in 1..@max do
    Enum.all?([organization, project, application, build], fn id ->
      is_binary(id) and byte_size(id) in 1..128 and
        String.valid?(id) and String.printable?(id)
    end)
  end

  defp closed_ref?(_), do: false

  defp valid_uuid?(id) do
    case String.split(id, "-") do
      [a, b, c, d, e]
      when byte_size(a) == 8 and byte_size(b) == 4 and byte_size(c) == 4 and byte_size(d) == 4 and
             byte_size(e) == 12 ->
        match?({:ok, _}, Base.decode16(a <> b <> c <> d <> e, case: :mixed))

      _ ->
        false
    end
  end
end
