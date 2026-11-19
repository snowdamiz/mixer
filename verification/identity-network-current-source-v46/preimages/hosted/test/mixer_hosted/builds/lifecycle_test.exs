defmodule MixerHosted.Builds.LifecycleTest do
  use ExUnit.Case, async: true
  alias MixerHosted.Builds.Lifecycle
  alias MixerHosted.Builds.Lifecycle.{ArtifactRef, Build, WorkerRef}

  @max_time 9_223_372_036_854_775_807
  @kinds [
    :unsigned_native_binary,
    :guest_artifact,
    :resource_inventory,
    :debug_symbols,
    :compatibility_report,
    :sbom,
    :provenance
  ]

  defp sha(number),
    do: number |> Integer.to_string(16) |> String.downcase() |> String.pad_leading(64, "0")

  defp spec do
    %{
      organization_id: "org-1",
      project_id: "project-1",
      application_id: "app-1",
      build_id: "build-1",
      platform: :ios,
      source: %{kind: :revision, sha256: sha(100), reference: "main@0123456789abcdef"},
      toolchain_lock_sha256: sha(101),
      build_definition_sha256: sha(102)
    }
  end

  defp policy, do: %{max_attempts: 3, timeout_ms: 100, retry_backoff_ms: 10}

  defp queued(spec \\ spec(), policy \\ policy(), now \\ 0) do
    assert {:ok, build} = Lifecycle.new(spec, policy, "request-1", now)
    build
  end

  defp apply!(build, id, event, now) do
    assert {:ok, updated, :applied} = Lifecycle.transition(build, id, event, now)
    updated
  end

  defp running(build \\ queued(), now \\ 1) do
    assert {:ok, ref} = Lifecycle.worker_ref(build)
    apply!(build, "start-#{build.attempt}", %{type: :start, ref: ref}, now)
  end

  defp artifacts do
    @kinds
    |> Enum.with_index(1)
    |> Enum.map(fn {kind, i} -> %ArtifactRef{kind: kind, sha256: sha(i), size_bytes: i * 10} end)
  end

  defp success(ref),
    do: %{type: :completed, ref: ref, result: %{outcome: :succeeded, artifacts: artifacts()}}

  defp failure(ref, class \\ :infrastructure, code \\ :worker_lost),
    do: %{
      type: :completed,
      ref: ref,
      result: %{outcome: :failed, class: class, code: code, diagnostic_sha256: sha(200)}
    }

  defp stop(ref), do: %{type: :stopped, ref: ref, diagnostic_sha256: sha(201)}
  defp cancel, do: %{type: :cancel, reason: "Customer cancelled the build"}

  test "immutable identity, exact scoped worker reference and successful output status" do
    initial = queued()
    assert initial.state == :queued
    assert {initial.attempt, initial.fence, initial.active_ref} == {1, 1, nil}
    assert {:ok, ref} = Lifecycle.worker_ref(initial)

    assert ref == %WorkerRef{
             organization_id: "org-1",
             project_id: "project-1",
             application_id: "app-1",
             build_id: "build-1",
             platform: :ios,
             attempt: 1,
             fence: 1
           }

    build = running(initial)
    assert build.deadline == 101
    assert {:ok, ^ref} = Lifecycle.worker_ref(build)
    done = apply!(build, "success", success(ref), 100)
    assert done.state == :succeeded
    assert done.fence == 2
    assert done.spec == initial.spec
    assert done.artifacts == artifacts()
    assert is_nil(done.active_ref)
    assert [%{state: :succeeded, worker_ref: ^ref, artifacts: refs}] = done.history
    assert refs == artifacts()
    assert {:ok, status} = Lifecycle.customer_status(done)

    assert status == %{
             build_id: "build-1",
             platform: :ios,
             state: :succeeded,
             attempt: 1,
             max_attempts: 3,
             worker_completion_pending: false,
             retryable: false,
             retry_after: nil,
             retry_blocked: :not_retryable_state,
             failure: nil,
             artifacts: artifacts()
           }

    assert {:error, :no_active_attempt} = Lifecycle.worker_ref(done)

    assert {:error, :invalid_transition} =
             Lifecycle.transition(done, "replace", success(ref), 100)

    assert {:error, :invalid_transition} =
             Lifecycle.transition(done, "cancel-late", cancel(), 100)

    assert {:error, :invalid_transition} =
             Lifecycle.transition(done, "retry-late", %{type: :retry}, 100)

    assert done.artifacts == refs
  end

  test "new input is closed, typed and bounded with no source or identity inference" do
    for key <- Map.keys(spec()) do
      assert {:error, :invalid_spec} = Lifecycle.new(Map.delete(spec(), key), policy(), "r", 0),
             inspect(key)

      assert {:error, :invalid_spec} = Lifecycle.new(Map.put(spec(), key, nil), policy(), "r", 0),
             inspect(key)
    end

    bad_specs = [
      Map.put(spec(), :unknown, true),
      Map.put(spec(), :platform, :linux),
      Map.put(spec(), :build_id, String.duplicate("x", 129)),
      Map.put(spec(), :build_id, ""),
      Map.put(spec(), :build_id, <<255>>),
      Map.put(spec(), :build_id, "a\0b"),
      Map.put(spec(), :toolchain_lock_sha256, String.upcase(sha(255))),
      Map.put(spec(), :build_definition_sha256, String.duplicate("0", 63)),
      put_in(spec(), [:source, :kind], :branch),
      put_in(spec(), [:source, :sha256], "main"),
      put_in(spec(), [:source, :reference], String.duplicate("x", 1025)),
      Map.update!(spec(), :source, &Map.put(&1, :token, "not accepted")),
      %{},
      nil,
      []
    ]

    for value <- bad_specs do
      assert {:error, :invalid_spec} = Lifecycle.new(value, policy(), "r", 0), inspect(value)
    end

    for key <- Map.keys(policy()) do
      assert {:error, :invalid_policy} = Lifecycle.new(spec(), Map.delete(policy(), key), "r", 0)

      assert {:error, :invalid_policy} =
               Lifecycle.new(spec(), Map.put(policy(), key, 1.0), "r", 0)
    end

    for value <- [
          Map.put(policy(), :max_attempts, 0),
          Map.put(policy(), :max_attempts, 6),
          Map.put(policy(), :timeout_ms, 0),
          Map.put(policy(), :timeout_ms, 86_400_001),
          Map.put(policy(), :retry_backoff_ms, -1),
          Map.put(policy(), :retry_backoff_ms, 3_600_001),
          Map.put(policy(), :unknown, 1),
          nil,
          %{}
        ] do
      assert {:error, :invalid_policy} = Lifecycle.new(spec(), value, "r", 0)
    end

    for request <- [nil, "", String.duplicate("x", 129), "a\0b"] do
      assert {:error, :invalid_request} = Lifecycle.new(spec(), policy(), request, 0)
    end

    for now <- [-1, @max_time + 1, 0.0, nil] do
      assert {:error, :invalid_request} = Lifecycle.new(spec(), policy(), "r", now)
    end

    upload = put_in(spec(), [:source, :kind], :upload)
    assert {:ok, %{spec: %{source: %{kind: :upload}}}} = Lifecycle.new(upload, policy(), "r", 0)

    assert {:ok, _} =
             Lifecycle.new(spec(), %{max_attempts: 1, timeout_ms: 1, retry_backoff_ms: 0}, "r", 0)
  end

  test "cancellation before dispatch is terminal without claiming any worker stopped" do
    build = apply!(queued(), "cancel", cancel(), 0)
    assert build.state == :cancelled
    assert build.fence == 2
    assert [%{worker_ref: nil, started_at: nil, state: :cancelled}] = build.history

    assert {:ok, %{state: :cancelled, worker_completion_pending: false}} =
             Lifecycle.customer_status(build)

    assert {:error, :invalid_transition} =
             Lifecycle.transition(build, "retry", %{type: :retry}, 10)
  end

  test "cancellation fences result authority while retaining uncertainty and exact stop identity" do
    build = running()
    ref = build.active_ref
    pending = apply!(build, "cancel", cancel(), 2)
    assert {pending.state, pending.fence, pending.active_ref} == {:cancelling, 2, ref}
    assert pending.history == []

    assert {:ok,
            %{
              state: :cancelling,
              worker_completion_pending: true,
              artifacts: nil,
              retryable: false
            }} = Lifecycle.customer_status(pending)

    assert {:error, :invalid_transition} =
             Lifecycle.transition(pending, "retry", %{type: :retry}, 3)

    assert {:error, :invalid_transition} =
             Lifecycle.transition(pending, "new-start", %{type: :start, ref: ref}, 3)

    assert {:error, :stale_worker_ref} =
             Lifecycle.transition(pending, "wrong-stop", stop(%{ref | fence: 2}), 3)

    done = apply!(pending, "late-success", success(ref), 3)
    assert done.state == :cancelled
    assert done.fence == 3
    assert done.active_ref == nil
    assert done.artifacts == nil
    assert {:ok, ^done, :duplicate} = Lifecycle.transition(done, "cancel", cancel(), 999)
    assert done.events["cancel"].first_observed_at == 2
  end

  test "expiry does not permit replacement until definitive matching worker completion" do
    build = running()
    ref = build.active_ref

    assert {:error, :deadline_not_reached} =
             Lifecycle.transition(build, "early", %{type: :expire, ref: ref}, 100)

    pending = apply!(build, "expire", %{type: :expire, ref: ref}, 101)

    assert {pending.state, pending.desired_terminal, pending.fence} ==
             {:reconciling, :timed_out, 2}

    assert pending.active_ref == ref

    assert {:ok, %{state: :reconciling, worker_completion_pending: true, retryable: false}} =
             Lifecycle.customer_status(pending)

    assert {:error, :invalid_transition} =
             Lifecycle.transition(pending, "retry", %{type: :retry}, 1_000)

    assert {:error, :invalid_transition} =
             Lifecycle.transition(pending, "start", %{type: :start, ref: ref}, 1_000)

    done = apply!(pending, "observed-stop", stop(ref), 102)
    assert done.state == :timed_out

    assert done.failure == %{
             class: :infrastructure,
             code: :worker_timeout,
             diagnostic_sha256: sha(201)
           }

    assert done.active_ref == nil
    assert done.retry_after == 112
    next = apply!(done, "retry", %{type: :retry}, 112)
    assert {next.state, next.attempt, next.fence} == {:queued, 2, 4}
    assert next.spec == build.spec
    assert next.policy == build.policy
    assert next.history == done.history

    assert {:error, :stale_worker_ref} =
             Lifecycle.transition(next, "old-start", %{type: :start, ref: ref}, 112)

    next = running(next, 113)

    assert {:error, :stale_worker_ref} =
             Lifecycle.transition(next, "old-result", success(ref), 114)

    assert {:error, :stale_worker_ref} =
             Lifecycle.transition(
               next,
               "future-result",
               success(%{next.active_ref | attempt: 3}),
               114
             )

    assert next.artifacts == nil
  end

  test "late definitive terminal report alone can establish timeout completion, discarding artifacts" do
    for now <- [101, 102] do
      build = running()
      done = apply!(build, "late", success(build.active_ref), now)
      assert {done.state, done.active_ref, done.artifacts} == {:timed_out, nil, nil}

      assert done.failure == %{
               class: :infrastructure,
               code: :worker_timeout,
               diagnostic_sha256: nil
             }

      assert {:ok, %{retryable: true, retry_after: after_time}} = Lifecycle.customer_status(done)
      assert after_time == now + 10
    end
  end

  test "cancel during timeout reconciliation preserves cancellation priority until definite stop" do
    build = running()
    pending = apply!(build, "expire", %{type: :expire, ref: build.active_ref}, 101)
    pending = apply!(pending, "cancel", cancel(), 102)

    assert {pending.state, pending.fence, pending.active_ref} ==
             {:cancelling, 3, build.active_ref}

    for event <- [stop(build.active_ref), failure(build.active_ref), success(build.active_ref)] do
      done = apply!(pending, "terminal", event, 103)

      assert {done.state, done.fence, done.failure, done.artifacts, done.retry_after} ==
               {:cancelled, 4, nil, nil, nil}
    end
  end

  test "exact worker scope rejects numerically equal references from all other scopes" do
    build = running()

    for {key, value} <- [
          organization_id: "org-2",
          project_id: "project-2",
          application_id: "app-2",
          build_id: "build-2",
          platform: :android,
          attempt: 2,
          fence: 2
        ] do
      ref = Map.put(build.active_ref, key, value)

      assert {:error, :stale_worker_ref} =
               Lifecycle.transition(build, "wrong-#{key}", success(ref), 2),
             inspect(key)

      assert {:error, :stale_worker_ref} =
               Lifecycle.transition(build, "stop-#{key}", stop(ref), 2),
             inspect(key)
    end
  end

  test "duplicates ignore delivery time, preserve first observation, and never revert newer attempts" do
    build = running()
    event = failure(build.active_ref)
    failed = apply!(build, "outcome", event, 2)
    next = apply!(failed, "retry", %{type: :retry}, 12)
    next = running(next, 13)
    done = apply!(next, "success", success(next.active_ref), 14)
    assert {:ok, ^done, :duplicate} = Lifecycle.transition(done, "outcome", event, 99_999)
    assert {:ok, ^done, :duplicate} = Lifecycle.transition(done, "outcome", event, -1)
    assert done.events["outcome"].first_observed_at == 2
    assert done.observed_at == 14

    assert {:error, :event_conflict} =
             Lifecycle.transition(done, "outcome", success(build.active_ref), 15)

    assert {:error, :event_conflict} =
             Lifecycle.transition(
               done,
               "success",
               Map.put(success(next.active_ref), :extra, true),
               15
             )

    assert {:error, :invalid_transition} = Lifecycle.transition(done, "new-outcome", event, 15)
  end

  test "infrastructure allowlist retries with backoff and stops at finite attempt cap" do
    for code <- [
          :worker_unavailable,
          :worker_lost,
          :dependency_transport,
          :artifact_transport,
          :worker_timeout
        ] do
      final =
        Enum.reduce(1..3, queued(), fn attempt, queued_build ->
          now = (attempt - 1) * 20 + 1
          running_build = running(queued_build, now)

          failed =
            apply!(
              running_build,
              "failed-#{attempt}",
              failure(running_build.active_ref, :infrastructure, code),
              now + 1
            )

          assert failed.state == :failed

          if attempt < 3 do
            assert {:error, :backoff_not_reached} =
                     Lifecycle.transition(failed, "too-soon", %{type: :retry}, now + 10)

            apply!(failed, "retry-#{attempt}", %{type: :retry}, now + 11)
          else
            assert {:error, :attempt_limit} =
                     Lifecycle.transition(failed, "retry-final", %{type: :retry}, now + 11)

            assert {:ok, %{retryable: false, retry_blocked: :attempt_limit}} =
                     Lifecycle.customer_status(failed)

            failed
          end
        end)

      assert Enum.map(final.history, & &1.attempt) == [1, 2, 3]
      assert length(final.history) == 3
      assert final.spec == queued().spec
    end
  end

  test "compiler, test, policy and unknown failures never blindly retry" do
    for {class, code} <- [
          compiler: :compiler_error,
          test: :test_failure,
          policy: :policy_rejection,
          policy: :invalid_input,
          unknown: :unknown_failure
        ] do
      build = running()
      done = apply!(build, "failed", failure(build.active_ref, class, code), 2)
      assert done.state == :failed
      assert done.failure.diagnostic_sha256 == sha(200)
      assert done.retry_after == nil

      assert {:error, :non_retryable_failure} =
               Lifecycle.transition(done, "retry", %{type: :retry}, 20)

      assert {:ok, %{retryable: false, retry_blocked: :non_retryable_failure}} =
               Lifecycle.customer_status(done)
    end
  end

  test "a deadline cannot turn known nonretryable failure reports into infrastructure retries" do
    for {class, code} <- [
          compiler: :compiler_error,
          test: :test_failure,
          policy: :policy_rejection,
          unknown: :unknown_failure
        ] do
      running_build = running()
      ref = running_build.active_ref
      reconciling = apply!(running_build, "expire", %{type: :expire, ref: ref}, 101)

      for build <- [running_build, reconciling] do
        done = apply!(build, "late-failure", failure(ref, class, code), 102)
        assert done.state == :timed_out
        assert done.failure == %{class: class, code: code, diagnostic_sha256: sha(200)}
        assert done.retry_after == nil

        assert {:error, :non_retryable_failure} =
                 Lifecycle.transition(done, "retry", %{type: :retry}, 112)
      end
    end
  end

  test "closed event, failure and artifact input rejects unsupported or mutable result contracts" do
    build = running()
    ref = build.active_ref
    success_event = success(ref)
    refs = artifacts()

    bad_refs = [
      tl(refs),
      refs ++ [hd(refs)],
      [nil | tl(refs)],
      [%{hd(refs) | kind: :signed_release} | tl(refs)],
      [%{hd(refs) | size_bytes: 0} | tl(refs)],
      [%{hd(refs) | size_bytes: @max_time + 1} | tl(refs)],
      [%{hd(refs) | sha256: sha(2)} | tl(refs)],
      [Map.put(hd(refs), :url, "https://mutable.invalid/latest") | tl(refs)],
      Enum.map(refs, &Map.from_struct/1),
      [hd(refs) | :bad_tail]
    ]

    for bad <- bad_refs do
      event = put_in(success_event, [:result, :artifacts], bad)
      assert {:error, :invalid_event} = Lifecycle.transition(build, "bad", event, 2), inspect(bad)
    end

    invalid = [
      nil,
      [],
      %{},
      %{type: :unknown},
      %{type: :retry, extra: true},
      Map.put(success_event, :unknown, true),
      Map.delete(success_event, :ref),
      %{type: :cancel, reason: ""},
      %{type: :cancel, reason: String.duplicate("x", 513)},
      %{type: :start, ref: Map.from_struct(ref)},
      %{type: :start, ref: Map.put(ref, :extra, true)},
      %{type: :start, ref: Map.delete(ref, :fence)},
      %{type: :stopped, ref: ref, diagnostic_sha256: "url"},
      put_in(failure(ref), [:result, :class], :new_class),
      put_in(failure(ref), [:result, :code], :compiler_error),
      put_in(failure(ref), [:result, :diagnostic_sha256], nil),
      put_in(success_event, [:result, :outcome], :uploaded)
    ]

    for event <- invalid do
      assert {:error, :invalid_event} = Lifecycle.transition(build, "bad", event, 2),
             inspect(event)
    end

    for id <- [nil, "", String.duplicate("x", 129)] do
      assert {:error, :invalid_event_id} = Lifecycle.transition(build, id, success_event, 2)
    end
  end

  test "distinct output roles may content-address identical bytes with the same recorded size" do
    build = running()
    [first, second | rest] = artifacts()
    shared = %{first | sha256: second.sha256, size_bytes: second.size_bytes}
    event = put_in(success(build.active_ref), [:result, :artifacts], [shared, second | rest])
    done = apply!(build, "success", event, 2)
    assert done.state == :succeeded
    assert done.artifacts == [shared, second | rest]
  end

  test "new events require bounded monotonic time and safe deadline, backoff and fence arithmetic" do
    build = running()

    for now <- [0, -1, @max_time + 1, 1.0, nil] do
      assert {:error, :invalid_observation_time} =
               Lifecycle.transition(build, "event", success(build.active_ref), now)
    end

    queued_build = queued(spec(), policy(), @max_time - 1)
    {:ok, ref} = Lifecycle.worker_ref(queued_build)

    assert {:error, :time_overflow} =
             Lifecycle.transition(queued_build, "start", %{type: :start, ref: ref}, @max_time - 1)

    edge_policy = %{max_attempts: 2, timeout_ms: 1, retry_backoff_ms: 10}
    edge = queued(spec(), edge_policy, @max_time - 2) |> running(@max_time - 2)
    done = apply!(edge, "observed", failure(edge.active_ref), @max_time - 2)
    assert done.state == :failed
    assert done.retry_after == nil

    assert {:ok, %{retryable: false, retry_blocked: :time_overflow}} =
             Lifecycle.customer_status(done)

    assert {:error, :time_overflow} =
             Lifecycle.transition(done, "retry", %{type: :retry}, @max_time)

    max_fence = %{build | fence: @max_time, active_ref: %{build.active_ref | fence: @max_time}}
    assert {:error, :time_overflow} = Lifecycle.transition(max_fence, "cancel", cancel(), 2)

    assert {:error, :time_overflow} =
             Lifecycle.transition(max_fence, "success", success(max_fence.active_ref), 2)
  end

  test "explicit event ceiling rejects without mutation while recorded exact duplicates remain readable" do
    build = running()
    payload = %{type: :cancel, reason: "Recorded synthetic boundary event"}

    events =
      for i <- 1..32, into: %{}, do: {"event-#{i}", %{payload: payload, first_observed_at: 1}}

    full = %{build | events: events}
    assert {:error, :event_limit} = Lifecycle.transition(full, "new", success(full.active_ref), 2)
    assert {:ok, ^full, :duplicate} = Lifecycle.transition(full, "event-1", payload, 999)
    assert {:error, :event_conflict} = Lifecycle.transition(full, "event-1", cancel(), 999)
    assert map_size(full.events) == 32
  end

  test "per-platform customer projection preserves a failure and never invents measured queue data" do
    ios = running() |> then(&apply!(&1, "ok", success(&1.active_ref), 2))
    android_spec = Map.merge(spec(), %{platform: :android, build_id: "build-android"})

    android =
      queued(android_spec)
      |> running()
      |> then(&apply!(&1, "fail", failure(&1.active_ref, :compiler, :compiler_error), 2))

    assert {:ok, %{platform: :ios, state: :succeeded}} = Lifecycle.customer_status(ios)

    assert {:ok, %{platform: :android, state: :failed, artifacts: nil} = status} =
             Lifecycle.customer_status(android)

    for key <- [
          :queue_position,
          :estimated_wait,
          :release_status,
          :signed,
          :charge,
          :aggregate_success
        ] do
      refute Map.has_key?(status, key)
    end
  end

  test "every state accepts only its explicit event set" do
    queued_build = queued()
    running_build = running(queued_build)
    ref = running_build.active_ref
    cancelling = apply!(running_build, "cancel", cancel(), 2)
    reconciling = apply!(running_build, "expire", %{type: :expire, ref: ref}, 101)
    succeeded = apply!(running_build, "done", success(ref), 2)
    failed = apply!(running_build, "failed", failure(ref), 2)
    cancelled = apply!(cancelling, "stopped", stop(ref), 3)
    timed_out = apply!(reconciling, "stopped", stop(ref), 102)

    allowed = %{
      queued: [:start, :cancel],
      running: [:cancel, :expire, :success, :failure, :stopped],
      cancelling: [:success, :failure, :stopped],
      reconciling: [:cancel, :success, :failure, :stopped],
      succeeded: [],
      failed: [:retry],
      cancelled: [],
      timed_out: [:retry]
    }

    events = %{
      start: %{type: :start, ref: ref},
      cancel: cancel(),
      expire: %{type: :expire, ref: ref},
      success: success(ref),
      failure: failure(ref),
      stopped: stop(ref),
      retry: %{type: :retry}
    }

    for build <- [
          queued_build,
          running_build,
          cancelling,
          reconciling,
          succeeded,
          failed,
          cancelled,
          timed_out
        ],
        {name, event} <- events do
      result = Lifecycle.transition(build, "matrix-#{name}", event, 112)

      if name in allowed[build.state] do
        assert match?({:ok, _, :applied}, result), inspect({build.state, name, result})
      else
        assert result == {:error, :invalid_transition}, inspect({build.state, name, result})
      end
    end
  end

  test "five attempts require at most twenty accepted transitions, below the hard ledger ceiling" do
    initial = queued(spec(), %{policy() | max_attempts: 5})

    last =
      Enum.reduce(1..4, initial, fn attempt, build ->
        now = (attempt - 1) * 200 + 1
        build = running(build, now)
        ref = build.active_ref
        build = apply!(build, "expire-#{attempt}", %{type: :expire, ref: ref}, now + 100)
        build = apply!(build, "stopped-#{attempt}", stop(ref), now + 101)
        apply!(build, "retry-#{attempt}", %{type: :retry}, now + 111)
      end)

    last = running(last, 801)
    ref = last.active_ref
    last = apply!(last, "expire-5", %{type: :expire, ref: ref}, 901)
    last = apply!(last, "cancel-5", cancel(), 902)
    last = apply!(last, "stopped-5", stop(ref), 903)

    assert {last.attempt, last.state, length(last.history), map_size(last.events)} ==
             {5, :cancelled, 5, 20}

    assert Enum.map(last.history, & &1.attempt) == [1, 2, 3, 4, 5]
  end

  test "invalid outer state returns errors rather than starting or reconstructing application services" do
    for build <- [
          nil,
          %{},
          %Build{spec: nil, policy: nil, request_key: "r", queued_at: 0, observed_at: 0},
          %{queued() | history: [:bad]},
          %{queued() | events: nil},
          %{queued() | state: :unknown}
        ] do
      assert {:error, :invalid_build} = Lifecycle.transition(build, "event", %{type: :retry}, 0)
      assert {:error, :invalid_build} = Lifecycle.worker_ref(build)
      assert {:error, :invalid_build} = Lifecycle.customer_status(build)
    end
  end

  test "bounded generated event sequences maintain state, fencing, output and no-overlap invariants" do
    # Fixed enumeration, no random seed or external property-test dependency.
    for seed <- 0..63 do
      final =
        Enum.reduce(1..40, queued(spec(), %{policy() | max_attempts: 5}), fn step, build ->
          now = step * 25
          event = generated_event(build, rem(seed * 11 + step * 7, 10))

          case Lifecycle.transition(build, "generated-#{step}", event, now) do
            {:ok, updated, :applied} ->
              assert updated.spec == build.spec
              assert updated.policy == build.policy
              assert updated.attempt >= build.attempt
              assert updated.attempt <= 5
              assert updated.fence >= build.fence
              assert map_size(updated.events) <= 32
              assert length(updated.history) <= 5

              if updated.attempt > build.attempt do
                assert build.state in [:failed, :timed_out]
                assert build.active_ref == nil
                assert updated.attempt == build.attempt + 1
                assert updated.fence > build.fence
              end

              if build.state in [:cancelling, :reconciling] and
                   updated.state in [:cancelling, :reconciling] do
                assert updated.active_ref == build.active_ref
              end

              if build.artifacts != nil, do: assert(updated.artifacts == build.artifacts)
              assert {:ok, status} = Lifecycle.customer_status(updated)

              assert status.worker_completion_pending ==
                       updated.state in [:running, :cancelling, :reconciling]

              assert {:ok, ^updated, :duplicate} =
                       Lifecycle.transition(updated, "generated-#{step}", event, now + 1_000)

              updated

            {:error, _reason} ->
              assert {:ok, _} = Lifecycle.customer_status(build)
              build
          end
        end)

      assert final.attempt <= 5
    end
  end

  defp generated_event(build, choice) do
    {:ok, ref} =
      Lifecycle.worker_ref(
        (build.state in [:queued, :running, :cancelling, :reconciling] && build) || queued()
      )

    case choice do
      0 -> %{type: :start, ref: ref}
      1 -> %{type: :expire, ref: ref}
      2 -> cancel()
      3 -> stop(ref)
      4 -> success(ref)
      5 -> failure(ref)
      6 -> failure(ref, :compiler, :compiler_error)
      7 -> %{type: :retry}
      8 -> success(%{ref | build_id: "other-build"})
      9 -> %{type: :unknown}
    end
  end
end
