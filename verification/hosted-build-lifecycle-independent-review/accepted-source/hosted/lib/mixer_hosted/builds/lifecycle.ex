defmodule MixerHosted.Builds.Lifecycle do
  @moduledoc """
  Pure, bounded decisions for one platform build and its worker attempts.

  Inputs are trusted application data, not proof of authorization, worker
  authenticity, durable CAS, external termination, artifact content or release
  eligibility. Persist each decision atomically before performing its effect.
  No process, clock, storage, provider, signing or billing operation runs here.
  Cancellation/expiry retain execution uncertainty until a matching definitive
  terminal observation; they never authorize replacement dispatch by themselves.
  """

  @max_time 9_223_372_036_854_775_807
  @event_limit 32
  @artifact_kinds [
    :unsigned_native_binary,
    :guest_artifact,
    :resource_inventory,
    :debug_symbols,
    :compatibility_report,
    :sbom,
    :provenance
  ]
  @states [
    :queued,
    :running,
    :cancelling,
    :reconciling,
    :succeeded,
    :failed,
    :cancelled,
    :timed_out
  ]
  @terminal [:succeeded, :failed, :cancelled, :timed_out]
  @active [:running, :cancelling, :reconciling]
  @infra [
    :worker_unavailable,
    :worker_lost,
    :dependency_transport,
    :artifact_transport,
    :worker_timeout
  ]
  @failure_codes %{
    infrastructure: @infra,
    compiler: [:compiler_error],
    test: [:test_failure],
    policy: [:policy_rejection, :invalid_input],
    unknown: [:unknown_failure]
  }
  @spec_keys [
    :organization_id,
    :project_id,
    :application_id,
    :build_id,
    :source,
    :toolchain_lock_sha256,
    :build_definition_sha256,
    :platform
  ]
  @policy_keys [:max_attempts, :timeout_ms, :retry_backoff_ms]
  @scope_keys [:organization_id, :project_id, :application_id, :build_id, :platform]

  defmodule Spec do
    @moduledoc "Immutable build identity data; no authorization or resolution proof."
    @enforce_keys [
      :organization_id,
      :project_id,
      :application_id,
      :build_id,
      :source,
      :toolchain_lock_sha256,
      :build_definition_sha256,
      :platform
    ]
    defstruct @enforce_keys
  end

  defmodule Policy do
    @moduledoc "Finite explicitly configured attempt, deadline and backoff bounds."
    @enforce_keys [:max_attempts, :timeout_ms, :retry_backoff_ms]
    defstruct @enforce_keys
  end

  defmodule WorkerRef do
    @moduledoc "Exact scoped attempt/fence identity; never authentication or authority."
    @enforce_keys [
      :organization_id,
      :project_id,
      :application_id,
      :build_id,
      :platform,
      :attempt,
      :fence
    ]
    defstruct @enforce_keys
  end

  defmodule ArtifactRef do
    @moduledoc "Content reference data; no existence, provenance or eligibility proof."
    @enforce_keys [:kind, :sha256, :size_bytes]
    defstruct @enforce_keys
  end

  defmodule Build do
    @moduledoc "Trusted in-memory state; not an untrusted-data hydration or durable record API."
    @enforce_keys [:spec, :policy, :request_key, :queued_at, :observed_at]
    defstruct @enforce_keys ++
                [
                  state: :queued,
                  attempt: 1,
                  fence: 1,
                  active_ref: nil,
                  desired_terminal: nil,
                  started_at: nil,
                  deadline: nil,
                  finished_at: nil,
                  retry_after: nil,
                  failure: nil,
                  artifacts: nil,
                  history: [],
                  events: %{}
                ]
  end

  @doc "Creates queued attempt 1. Caller storage owns request-key uniqueness and authorization."
  def new(spec, policy, request_key, now_ms) do
    with {:ok, spec} <- normalize_spec(spec),
         {:ok, policy} <- normalize_policy(policy),
         true <- text?(request_key, 128),
         true <- time?(now_ms) do
      {:ok,
       %Build{
         spec: spec,
         policy: policy,
         request_key: request_key,
         queued_at: now_ms,
         observed_at: now_ms
       }}
    else
      false -> {:error, :invalid_request}
      error -> error
    end
  end

  @doc "Returns reference data for queued/possibly active work, without authorizing dispatch."
  def worker_ref(%Build{} = build) do
    cond do
      not valid_build?(build) -> {:error, :invalid_build}
      build.state == :queued -> {:ok, reference(build)}
      build.state in @active -> {:ok, build.active_ref}
      true -> {:error, :no_active_attempt}
    end
  end

  def worker_ref(_), do: {:error, :invalid_build}

  @doc """
  Applies an exact event once. Duplicate identity compares event payload only;
  later delivery time is ignored and the first observation time is retained.
  New events require monotonic bounded coordinator time. Event history has a
  hard 32-entry ceiling, including when receiving an otherwise valid event.
  """
  def transition(%Build{} = build, event_id, event, now_ms) do
    cond do
      not valid_build?(build) ->
        {:error, :invalid_build}

      not text?(event_id, 128) ->
        {:error, :invalid_event_id}

      Map.has_key?(build.events, event_id) ->
        case build.events[event_id] do
          %{payload: ^event} -> {:ok, build, :duplicate}
          _ -> {:error, :event_conflict}
        end

      map_size(build.events) >= @event_limit ->
        {:error, :event_limit}

      not time?(now_ms) or now_ms < build.observed_at ->
        {:error, :invalid_observation_time}

      not event?(event) ->
        {:error, :invalid_event}

      true ->
        with {:ok, updated} <- apply_event(build, event, now_ms) do
          accepted = %{payload: event, first_observed_at: now_ms}

          {:ok,
           %{updated | observed_at: now_ms, events: Map.put(build.events, event_id, accepted)},
           :applied}
        end
    end
  end

  def transition(_, _, _, _), do: {:error, :invalid_build}

  @doc "Exact per-platform status. It makes no queue estimate or release/distribution/billing claim."
  def customer_status(%Build{} = build) do
    if valid_build?(build) do
      {retryable, retry_blocked} = retry_status(build)

      {:ok,
       %{
         build_id: build.spec.build_id,
         platform: build.spec.platform,
         state: build.state,
         attempt: build.attempt,
         max_attempts: build.policy.max_attempts,
         worker_completion_pending: build.state in @active,
         retryable: retryable,
         retry_after: build.retry_after,
         retry_blocked: retry_blocked,
         failure: build.failure,
         artifacts: build.artifacts
       }}
    else
      {:error, :invalid_build}
    end
  end

  def customer_status(_), do: {:error, :invalid_build}

  defp apply_event(build, %{type: :start, ref: ref}, now) do
    with :ok <- expect_state(build, [:queued]),
         :ok <- expect_ref(ref, reference(build)),
         {:ok, deadline} <- add_time(now, build.policy.timeout_ms) do
      {:ok, %{build | state: :running, active_ref: ref, started_at: now, deadline: deadline}}
    end
  end

  defp apply_event(build, %{type: :cancel}, now) do
    with :ok <- expect_state(build, [:queued, :running, :reconciling]) do
      if build.state == :queued do
        finish(build, :cancelled, nil, nil, now)
      else
        with {:ok, fence} <- add_time(build.fence, 1) do
          {:ok, %{build | state: :cancelling, desired_terminal: :cancelled, fence: fence}}
        end
      end
    end
  end

  defp apply_event(build, %{type: :expire, ref: ref}, now) do
    with :ok <- expect_state(build, [:running]),
         :ok <- expect_ref(ref, build.active_ref),
         true <- now >= build.deadline,
         {:ok, fence} <- add_time(build.fence, 1) do
      {:ok, %{build | state: :reconciling, desired_terminal: :timed_out, fence: fence}}
    else
      false -> {:error, :deadline_not_reached}
      error -> error
    end
  end

  defp apply_event(build, %{type: :completed, ref: ref, result: result}, now) do
    with :ok <- expect_state(build, @active),
         :ok <- expect_ref(ref, build.active_ref) do
      observe_terminal(build, result, now)
    end
  end

  defp apply_event(build, %{type: :stopped, ref: ref, diagnostic_sha256: diagnostic}, now) do
    with :ok <- expect_state(build, @active),
         :ok <- expect_ref(ref, build.active_ref) do
      observe_terminal(
        build,
        %{
          outcome: :failed,
          class: :infrastructure,
          code: :worker_lost,
          diagnostic_sha256: diagnostic
        },
        now
      )
    end
  end

  defp apply_event(build, %{type: :retry}, now) do
    with :ok <- expect_state(build, [:failed, :timed_out]),
         {true, nil} <- retry_status(build),
         true <- now >= build.retry_after,
         {:ok, fence} <- add_time(build.fence, 1) do
      {:ok,
       %{
         build
         | state: :queued,
           attempt: build.attempt + 1,
           fence: fence,
           queued_at: now,
           desired_terminal: nil,
           started_at: nil,
           deadline: nil,
           finished_at: nil,
           retry_after: nil,
           failure: nil
       }}
    else
      {false, reason} -> {:error, reason}
      false -> {:error, :backoff_not_reached}
      error -> error
    end
  end

  defp observe_terminal(%Build{state: :cancelling} = build, _result, now),
    do: finish(build, :cancelled, nil, nil, now)

  defp observe_terminal(%Build{state: :reconciling} = build, result, now),
    do: finish(build, :timed_out, timeout_failure(result), nil, now)

  defp observe_terminal(build, result, now) do
    cond do
      now >= build.deadline ->
        finish(build, :timed_out, timeout_failure(result), nil, now)

      result.outcome == :succeeded ->
        finish(build, :succeeded, nil, result.artifacts, now)

      true ->
        finish(build, :failed, Map.delete(result, :outcome), nil, now)
    end
  end

  defp finish(build, state, failure, artifacts, now) do
    with {:ok, fence} <- add_time(build.fence, 1) do
      retry_after =
        if retry_failure?(failure) and build.attempt < build.policy.max_attempts do
          case add_time(now, build.policy.retry_backoff_ms) do
            {:ok, at} -> at
            {:error, :time_overflow} -> nil
          end
        end

      record = %{
        attempt: build.attempt,
        worker_ref: build.active_ref,
        state: state,
        queued_at: build.queued_at,
        started_at: build.started_at,
        deadline: build.deadline,
        finished_at: now,
        failure: failure,
        artifacts: artifacts
      }

      {:ok,
       %{
         build
         | state: state,
           fence: fence,
           active_ref: nil,
           desired_terminal: nil,
           finished_at: now,
           retry_after: retry_after,
           failure: failure,
           artifacts: artifacts,
           history: build.history ++ [record]
       }}
    end
  end

  # A deadline must never turn a known compiler/test/policy failure into a
  # retryable infrastructure failure merely because its report arrived late.
  defp timeout_failure(%{outcome: :failed, class: class} = result)
       when class != :infrastructure,
       do: Map.delete(result, :outcome)

  defp timeout_failure(result),
    do: %{
      class: :infrastructure,
      code: :worker_timeout,
      diagnostic_sha256: Map.get(result, :diagnostic_sha256)
    }

  defp retry_status(build) do
    cond do
      build.state not in [:failed, :timed_out] -> {false, :not_retryable_state}
      not retry_failure?(build.failure) -> {false, :non_retryable_failure}
      build.attempt >= build.policy.max_attempts -> {false, :attempt_limit}
      is_nil(build.retry_after) -> {false, :time_overflow}
      true -> {true, nil}
    end
  end

  defp retry_failure?(%{class: :infrastructure, code: code}), do: code in @infra
  defp retry_failure?(_), do: false

  defp expect_state(%{state: state}, allowed) do
    if state in allowed, do: :ok, else: {:error, :invalid_transition}
  end

  defp expect_ref(ref, expected) do
    if ref == expected, do: :ok, else: {:error, :stale_worker_ref}
  end

  defp reference(build) do
    build.spec
    |> Map.from_struct()
    |> Map.take(@scope_keys)
    |> Map.merge(%{attempt: build.attempt, fence: build.fence})
    |> then(&struct!(WorkerRef, &1))
  end

  defp event?(%{type: :start} = event),
    do: exact?(event, [:type, :ref]) and ref?(event.ref)

  defp event?(%{type: :cancel} = event),
    do: exact?(event, [:type, :reason]) and text?(event.reason, 512)

  defp event?(%{type: :expire} = event),
    do: exact?(event, [:type, :ref]) and ref?(event.ref)

  defp event?(%{type: :completed} = event),
    do: exact?(event, [:type, :ref, :result]) and ref?(event.ref) and result?(event.result)

  defp event?(%{type: :stopped} = event),
    do:
      exact?(event, [:type, :ref, :diagnostic_sha256]) and ref?(event.ref) and
        sha?(event.diagnostic_sha256)

  defp event?(%{type: :retry} = event), do: exact?(event, [:type])
  defp event?(_), do: false

  defp result?(%{outcome: :succeeded} = result),
    do: exact?(result, [:outcome, :artifacts]) and artifacts?(result.artifacts)

  defp result?(%{outcome: :failed} = result) do
    exact?(result, [:outcome, :class, :code, :diagnostic_sha256]) and
      result.code in Map.get(@failure_codes, result.class, []) and sha?(result.diagnostic_sha256)
  end

  defp result?(_), do: false

  defp artifacts?(refs) do
    bounded_list?(refs, 7, 7) and Enum.all?(refs, &artifact?/1) and
      Enum.sort(Enum.map(refs, & &1.kind)) == Enum.sort(@artifact_kinds) and
      refs
      |> Enum.group_by(& &1.sha256)
      |> Enum.all?(fn {_digest, same_content} ->
        length(Enum.uniq(Enum.map(same_content, & &1.size_bytes))) == 1
      end)
  end

  defp artifact?(%ArtifactRef{} = ref),
    do:
      exact?(Map.from_struct(ref), [:kind, :sha256, :size_bytes]) and
        ref.kind in @artifact_kinds and sha?(ref.sha256) and
        integer?(ref.size_bytes, 1, @max_time)

  defp artifact?(_), do: false

  defp ref?(%WorkerRef{} = ref) do
    exact?(Map.from_struct(ref), @scope_keys ++ [:attempt, :fence]) and
      Enum.all?(@scope_keys -- [:platform], &text?(Map.fetch!(ref, &1), 128)) and
      ref.platform in [:ios, :android] and integer?(ref.attempt, 1, 5) and
      integer?(ref.fence, 1, @max_time)
  end

  defp ref?(_), do: false

  defp normalize_spec(value) do
    value = if is_struct(value, Spec), do: Map.from_struct(value), else: value

    if spec?(value), do: {:ok, struct!(Spec, value)}, else: {:error, :invalid_spec}
  end

  defp spec?(spec) do
    exact?(spec, @spec_keys) and
      Enum.all?(@scope_keys -- [:platform], &text?(Map.fetch!(spec, &1), 128)) and
      spec.platform in [:ios, :android] and
      exact?(spec.source, [:kind, :sha256, :reference]) and
      spec.source.kind in [:revision, :upload] and sha?(spec.source.sha256) and
      text?(spec.source.reference, 1024) and sha?(spec.toolchain_lock_sha256) and
      sha?(spec.build_definition_sha256)
  end

  defp normalize_policy(value) do
    value = if is_struct(value, Policy), do: Map.from_struct(value), else: value

    if policy?(value), do: {:ok, struct!(Policy, value)}, else: {:error, :invalid_policy}
  end

  defp policy?(policy) do
    exact?(policy, @policy_keys) and integer?(policy.max_attempts, 1, 5) and
      integer?(policy.timeout_ms, 1, 86_400_000) and
      integer?(policy.retry_backoff_ms, 0, 3_600_000)
  end

  defp valid_build?(build) do
    is_struct(build.spec, Spec) and spec?(Map.from_struct(build.spec)) and
      is_struct(build.policy, Policy) and policy?(Map.from_struct(build.policy)) and
      text?(build.request_key, 128) and build.state in @states and
      integer?(build.attempt, 1, build.policy.max_attempts) and
      integer?(build.fence, 1, @max_time) and
      time?(build.queued_at) and time?(build.observed_at) and build.queued_at <= build.observed_at and
      is_map(build.events) and map_size(build.events) <= @event_limit and
      bounded_list?(build.history, 0, build.policy.max_attempts) and
      length(build.history) == build.attempt - if(build.state in @terminal, do: 0, else: 1) and
      execution_shape?(build)
  end

  defp execution_shape?(%{state: :queued} = build),
    do:
      is_nil(build.active_ref) and is_nil(build.started_at) and is_nil(build.deadline) and
        is_nil(build.finished_at) and is_nil(build.desired_terminal) and is_nil(build.artifacts) and
        is_nil(build.failure) and is_nil(build.retry_after)

  defp execution_shape?(%{state: state} = build) when state in @active do
    ref?(build.active_ref) and
      Map.take(Map.from_struct(build.active_ref), @scope_keys) ==
        Map.take(Map.from_struct(build.spec), @scope_keys) and
      build.active_ref.attempt == build.attempt and build.active_ref.fence <= build.fence and
      time?(build.started_at) and time?(build.deadline) and build.started_at >= build.queued_at and
      build.deadline > build.started_at and is_nil(build.finished_at) and is_nil(build.artifacts) and
      is_nil(build.failure) and is_nil(build.retry_after) and
      case state do
        :running ->
          build.active_ref.fence == build.fence and is_nil(build.desired_terminal)

        :cancelling ->
          build.active_ref.fence < build.fence and build.desired_terminal == :cancelled

        :reconciling ->
          build.active_ref.fence < build.fence and build.desired_terminal == :timed_out
      end
  end

  defp execution_shape?(build) do
    is_nil(build.active_ref) and is_nil(build.desired_terminal) and time?(build.finished_at) and
      build.finished_at >= build.queued_at and
      case build.state do
        :succeeded ->
          artifacts?(build.artifacts) and is_nil(build.failure) and is_nil(build.retry_after)

        :cancelled ->
          is_nil(build.artifacts) and is_nil(build.failure) and is_nil(build.retry_after)

        state when state in [:failed, :timed_out] ->
          is_nil(build.artifacts) and failure?(build.failure) and
            (is_nil(build.retry_after) or
               (time?(build.retry_after) and build.retry_after >= build.finished_at))
      end
  end

  defp failure?(failure) do
    exact?(failure, [:class, :code, :diagnostic_sha256]) and
      failure.code in Map.get(@failure_codes, failure.class, []) and
      (sha?(failure.diagnostic_sha256) or
         (failure.class == :infrastructure and failure.code == :worker_timeout and
            is_nil(failure.diagnostic_sha256)))
  end

  defp exact?(value, keys),
    do:
      is_map(value) and map_size(value) == length(keys) and
        Enum.all?(keys, &Map.has_key?(value, &1))

  defp integer?(value, min, max), do: is_integer(value) and value >= min and value <= max
  defp time?(value), do: integer?(value, 0, @max_time)

  defp text?(value, max),
    do:
      is_binary(value) and byte_size(value) in 1..max and String.valid?(value) and
        String.printable?(value)

  defp sha?(value) when is_binary(value) and byte_size(value) == 64,
    do: value |> :binary.bin_to_list() |> Enum.all?(&(&1 in ?0..?9 or &1 in ?a..?f))

  defp sha?(_), do: false
  defp add_time(left, right) when left <= @max_time - right, do: {:ok, left + right}
  defp add_time(_, _), do: {:error, :time_overflow}

  defp bounded_list?([], min, _max), do: min <= 0
  defp bounded_list?([_ | rest], min, max) when max > 0, do: bounded_list?(rest, min - 1, max - 1)
  defp bounded_list?(_, _, _), do: false
end

