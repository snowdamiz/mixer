defmodule MixerHosted.Builds.LifecycleIndependentControlsTest do
  use ExUnit.Case, async: true
  alias MixerHosted.Builds.Lifecycle, as: L
  alias MixerHosted.Builds.Lifecycle.ArtifactRef

  @max 9_223_372_036_854_775_807
  @roles [
    :unsigned_native_binary,
    :guest_artifact,
    :resource_inventory,
    :debug_symbols,
    :compatibility_report,
    :sbom,
    :provenance
  ]
  @infra [
    :worker_unavailable,
    :worker_lost,
    :dependency_transport,
    :artifact_transport,
    :worker_timeout
  ]
  @noninfra [
    compiler: :compiler_error,
    test: :test_failure,
    policy: :policy_rejection,
    policy: :invalid_input,
    unknown: :unknown_failure
  ]

  defp digest(n), do: n |> Integer.to_string(16) |> String.downcase() |> String.pad_leading(64, "0")

  defp queued(options \\ []) do
    spec = %{
      organization_id: "review-org",
      project_id: "review-project",
      application_id: "review-app",
      build_id: "review-build",
      platform: Keyword.get(options, :platform, :ios),
      source: %{kind: :upload, sha256: digest(81), reference: "independent upload"},
      toolchain_lock_sha256: digest(82),
      build_definition_sha256: digest(83)
    }

    policy = %{
      max_attempts: Keyword.get(options, :max_attempts, 5),
      timeout_ms: Keyword.get(options, :timeout_ms, 100),
      retry_backoff_ms: Keyword.get(options, :retry_backoff_ms, 10)
    }

    assert {:ok, build} = L.new(spec, policy, "review-request", Keyword.get(options, :now, 0))
    build
  end

  defp step(build, id, event, now) do
    assert {:ok, updated, :applied} = L.transition(build, id, event, now)
    assert updated.spec == build.spec
    assert updated.policy == build.policy
    assert updated.request_key == build.request_key
    assert updated.fence >= build.fence
    assert updated.attempt in build.attempt..min(build.attempt + 1, build.policy.max_attempts)
    assert updated.observed_at >= build.observed_at
    updated
  end

  defp ref(build) do
    assert {:ok, reference} = L.worker_ref(build)
    reference
  end

  defp start(build, now \\ 1),
    do: step(build, "start-#{build.attempt}", %{type: :start, ref: ref(build)}, now)

  defp outputs do
    Enum.with_index(@roles, 1)
    |> Enum.map(fn {role, i} -> %ArtifactRef{kind: role, sha256: digest(i), size_bytes: i * 17} end)
  end

  defp succeeded(reference, artifacts \\ outputs()),
    do: %{type: :completed, ref: reference, result: %{outcome: :succeeded, artifacts: artifacts}}

  defp failed(reference, class \\ :infrastructure, code \\ :worker_lost),
    do: %{
      type: :completed,
      ref: reference,
      result: %{outcome: :failed, class: class, code: code, diagnostic_sha256: digest(99)}
    }

  defp stopped(reference),
    do: %{type: :stopped, ref: reference, diagnostic_sha256: digest(98)}

  defp cancel, do: %{type: :cancel, reason: "Independent cancellation control"}

  test "all seven worker-reference fields fence start, completion, stop and expiry" do
    queued_build = queued()
    running = start(queued_build)
    reference = ref(running)
    cancelling = step(running, "cancel", cancel(), 2)
    reconciling = step(running, "expire", %{type: :expire, ref: reference}, 101)

    for {key, other} <- [
          organization_id: "other-org",
          project_id: "other-project",
          application_id: "other-app",
          build_id: "other-build",
          platform: :android,
          attempt: 2,
          fence: 2
        ] do
      wrong = Map.put(reference, key, other)

      assert {:error, :stale_worker_ref} =
               L.transition(queued_build, "wrong-start", %{type: :start, ref: wrong}, 1)

      assert {:error, :stale_worker_ref} =
               L.transition(running, "wrong-expiry", %{type: :expire, ref: wrong}, 101)

      for build <- [running, cancelling, reconciling],
          event <- [succeeded(wrong), failed(wrong), stopped(wrong)] do
        assert {:error, :stale_worker_ref} = L.transition(build, "wrong-terminal", event, 102)
        assert {:ok, ^reference} = L.worker_ref(build)
        assert build.attempt == 1
        assert build.artifacts == nil
      end
    end
  end

  test "old exact events remain duplicates of the latest successful retry independent of delivery time" do
    initial = queued()
    running = start(initial)
    old_failure = failed(ref(running))
    done = step(running, "failure-1", old_failure, 2)
    next = step(done, "retry-1", %{type: :retry}, 12) |> start(13)
    final = step(next, "success-2", succeeded(ref(next)), 14)

    for {id, record} <- final.events, now <- [-1, nil, @max + 1, 1_000_000] do
      assert {:ok, ^final, :duplicate} = L.transition(final, id, record.payload, now)
    end

    assert final.events["failure-1"].first_observed_at == 2
    assert final.events["start-1"].first_observed_at == 1
    assert final.observed_at == 14
    assert final.attempt == 2
    assert final.artifacts == outputs()

    assert {:error, :event_conflict} =
             L.transition(final, "failure-1", failed(ref(running), :compiler, :compiler_error), 14)

    assert {:error, :event_conflict} =
             L.transition(final, "success-2", succeeded(ref(next), Enum.reverse(outputs())), 14)

    assert {:error, :invalid_transition} = L.transition(final, "new-old-result", old_failure, 14)
  end

  test "synthetic full trusted ledger rejects fresh work while exact and conflicting duplicates are readable" do
    running = queued() |> start()

    # The ordinary finite attempt machine cannot reach 32 entries (maximum 20).
    # This deliberately fabricated trusted Build exercises only the hard boundary;
    # it is not evidence that this API validates arbitrary hydrated state.
    extras =
      for i <- 1..31, into: %{} do
        {"synthetic-#{i}", %{payload: cancel(), first_observed_at: 1}}
      end

    full = %{running | events: Map.merge(running.events, extras)}
    assert map_size(full.events) == 32

    assert {:error, :event_limit} =
             L.transition(full, "fresh-success", succeeded(ref(full)), 2)

    original = full.events["start-1"].payload
    assert {:ok, ^full, :duplicate} = L.transition(full, "start-1", original, nil)
    assert {:ok, ^full, :duplicate} = L.transition(full, "synthetic-1", cancel(), @max + 1)

    assert {:error, :event_conflict} =
             L.transition(full, "start-1", %{type: :start, ref: %{ref(full) | fence: 2}}, 2)

    assert full.observed_at == 1
    assert full.state == :running
    assert full.artifacts == nil

    oversized = %{full | events: Map.put(full.events, "overflow", %{payload: cancel()})}
    assert {:error, :invalid_build} = L.customer_status(oversized)
  end

  test "elapsed cancellation and expiry never permit replacement without exact terminal evidence" do
    running = queued() |> start()
    reference = ref(running)
    expired = step(running, "expire", %{type: :expire, ref: reference}, 101)

    pending_states = [
      step(running, "cancel", cancel(), 2),
      expired,
      step(expired, "cancel", cancel(), 102)
    ]

    for pending <- pending_states do
      assert {:ok, ^reference} = L.worker_ref(pending)
      assert pending.active_ref == reference
      assert pending.fence > reference.fence
      assert pending.history == []

      assert {:ok, %{worker_completion_pending: true, retryable: false}} =
               L.customer_status(pending)

      for event <- [%{type: :retry}, %{type: :start, ref: reference}] do
        assert {:error, :invalid_transition} =
                 L.transition(pending, "replacement", event, 1_000_000)
      end

      invented = %{reference | fence: pending.fence}

      for event <- [stopped(invented), succeeded(invented)] do
        assert {:error, :stale_worker_ref} =
                 L.transition(pending, "invented-reconciliation", event, 1_000_000)
      end

      for event <- [stopped(reference), succeeded(reference), failed(reference)] do
        final = step(pending, "exact-terminal", event, 1_000_000)
        expected = if pending.state == :cancelling, do: :cancelled, else: :timed_out
        assert final.state == expected
        assert final.active_ref == nil
        assert final.artifacts == nil
        assert length(final.history) == 1

        assert {:ok, %{worker_completion_pending: false}} = L.customer_status(final)

        if expected == :timed_out do
          assert {:error, :backoff_not_reached} =
                   L.transition(final, "early-retry", %{type: :retry}, 1_000_009)

          successor = step(final, "retry", %{type: :retry}, 1_000_010)
          assert successor.state == :queued
          assert successor.attempt == 2
          assert successor.active_ref == nil
          refute ref(successor) == reference
        else
          assert {:error, :invalid_transition} =
                   L.transition(final, "retry", %{type: :retry}, 1_000_010)
        end
      end
    end
  end

  test "every known noninfrastructure failure stays nonretryable before, at and after deadline and reconciliation" do
    running = queued() |> start()
    reference = ref(running)
    expired = step(running, "expire", %{type: :expire, ref: reference}, 101)

    for {class, code} <- @noninfra,
        {build, now, state} <- [
          {running, 100, :failed},
          {running, 101, :timed_out},
          {running, 1_000_000, :timed_out},
          {expired, 102, :timed_out}
        ] do
      final = step(build, "known-failure", failed(reference, class, code), now)
      assert final.state == state
      assert final.failure == %{class: class, code: code, diagnostic_sha256: digest(99)}
      assert final.retry_after == nil

      assert {:ok, %{retryable: false, retry_blocked: :non_retryable_failure}} =
               L.customer_status(final)

      assert {:error, :non_retryable_failure} =
               L.transition(final, "retry", %{type: :retry}, 1_000_010)
    end
  end

  test "all infrastructure codes obey explicit backoff and finite exhaustion while mismatched classifications reject" do
    for code <- @infra do
      first = queued(max_attempts: 2) |> start()
      failed_first = step(first, "failure-1", failed(ref(first), :infrastructure, code), 2)

      assert {:error, :backoff_not_reached} =
               L.transition(failed_first, "retry", %{type: :retry}, 11)

      second = step(failed_first, "retry", %{type: :retry}, 12) |> start(13)
      final = step(second, "failure-2", failed(ref(second), :infrastructure, code), 14)
      assert Enum.map(final.history, & &1.attempt) == [1, 2]

      assert {:error, :attempt_limit} = L.transition(final, "retry-2", %{type: :retry}, 24)
      assert {:ok, %{retryable: false, retry_blocked: :attempt_limit}} = L.customer_status(final)
    end

    build = queued() |> start()

    for {class, code} <- [
          infrastructure: :compiler_error,
          compiler: :worker_lost,
          unknown: :worker_timeout,
          infrastructure: :out_of_memory
        ] do
      assert {:error, :invalid_event} =
               L.transition(build, "unlisted", failed(ref(build), class, code), 2)
    end
  end

  test "five uncertainty cycles bound history and every old accepted event remains harmless after exhaustion" do
    for cancel_final <- [false, true] do
      initial = queued()

      final =
        Enum.reduce(1..5, initial, fn attempt, build ->
          now = (attempt - 1) * 200 + 1
          build = start(build, now)
          reference = ref(build)
          build = step(build, "expire-#{attempt}", %{type: :expire, ref: reference}, now + 100)

          build =
            if attempt == 5 and cancel_final,
              do: step(build, "cancel-final", cancel(), now + 101),
              else: build

          build = step(build, "stop-#{attempt}", stopped(reference), now + 102)

          if attempt < 5,
            do: step(build, "retry-#{attempt}", %{type: :retry}, now + 112),
            else: build
        end)

      assert final.attempt == 5
      assert final.spec == initial.spec
      assert final.policy == initial.policy
      assert Enum.map(final.history, & &1.attempt) == [1, 2, 3, 4, 5]
      assert map_size(final.events) == if(cancel_final, do: 20, else: 19)
      assert final.state == if(cancel_final, do: :cancelled, else: :timed_out)
      assert final.active_ref == nil
      assert final.artifacts == nil

      expected_error = if cancel_final, do: :invalid_transition, else: :attempt_limit
      assert {:error, ^expected_error} = L.transition(final, "sixth-attempt", %{type: :retry}, 1_000)

      for {id, recorded} <- final.events do
        assert {:ok, ^final, :duplicate} = L.transition(final, id, recorded.payload, nil)
      end
    end
  end

  test "signed64 limits preserve definitive results while blocking deadline, backoff and synthetic fence overflow" do
    initial = queued(now: @max - 100, timeout_ms: 100, retry_backoff_ms: 1)
    running = start(initial, @max - 100)
    assert running.deadline == @max
    assert step(running, "before-deadline", succeeded(ref(running)), @max - 1).state == :succeeded

    timed_out = step(running, "at-deadline", succeeded(ref(running)), @max)
    assert timed_out.state == :timed_out
    assert timed_out.finished_at == @max
    assert timed_out.retry_after == nil
    assert timed_out.artifacts == nil

    assert {:ok, %{retryable: false, retry_blocked: :time_overflow}} = L.customer_status(timed_out)
    assert {:error, :time_overflow} = L.transition(timed_out, "retry", %{type: :retry}, @max)

    assert {:error, :time_overflow} =
             L.transition(initial, "late-start", %{type: :start, ref: ref(initial)}, @max - 99)

    for invalid <- [-1, @max + 1, 1.0, nil] do
      assert {:error, :invalid_observation_time} =
               L.transition(running, "bad-time", succeeded(ref(running)), invalid)
    end

    ordinary = queued() |> start()
    synthetic_ref = %{ref(ordinary) | fence: @max}
    synthetic = %{ordinary | fence: @max, active_ref: synthetic_ref}

    # A 64-bit fence cannot be reached by the bounded normal machine. These
    # trusted synthetic values exercise overflow rejection, not state hydration.
    for event <- [cancel(), stopped(synthetic_ref), succeeded(synthetic_ref)] do
      assert {:error, :time_overflow} = L.transition(synthetic, "overflow", event, 2)
    end

    assert {:error, :time_overflow} =
             L.transition(synthetic, "overflow-expiry", %{type: :expire, ref: synthetic_ref}, 101)

    assert synthetic.state == :running
    assert synthetic.history == []
  end

  test "seven typed immutable roles allow consistent shared bytes and reject shape or size conflicts" do
    build = queued() |> start()
    reference = ref(build)
    shared = Enum.map(outputs(), &%{&1 | sha256: digest(7), size_bytes: 37})
    final = step(build, "shared-content", succeeded(reference, shared), 2)
    assert final.state == :succeeded
    assert final.artifacts == shared
    assert {:ok, ^final, :duplicate} = L.transition(final, "shared-content", succeeded(reference, shared), 3)

    assert {:error, :invalid_transition} =
             L.transition(final, "replace-output", succeeded(reference, outputs()), 3)

    malformed = [
      [%{hd(shared) | size_bytes: 38} | tl(shared)],
      [%{hd(shared) | kind: :sbom} | tl(shared)],
      [Map.put(hd(shared), :url, "mutable-latest") | tl(shared)],
      Enum.map(shared, &Map.from_struct/1),
      Enum.take(shared, 6),
      shared ++ [hd(shared)],
      [%{hd(shared) | size_bytes: 0} | tl(shared)],
      [%{hd(shared) | size_bytes: @max + 1} | tl(shared)],
      [hd(shared) | :improper_tail]
    ]

    for outputs <- malformed do
      assert {:error, :invalid_event} =
               L.transition(build, "malformed-output", succeeded(reference, outputs), 2)
    end
  end

  test "per-platform projection preserves Android failure beside successful iOS with no invented release or billing authority" do
    ios = queued() |> start()
    ios = step(ios, "ios-result", succeeded(ref(ios)), 2)
    android = queued(platform: :android) |> start()
    android = step(android, "android-result", failed(ref(android), :compiler, :compiler_error), 2)

    assert {:ok, %{state: :succeeded, platform: :ios}} = L.customer_status(ios)
    assert {:ok, %{state: :failed, platform: :android, artifacts: nil} = status} = L.customer_status(android)

    for absent <- [:aggregate_success, :signed, :release_status, :charge, :queue_position, :estimated_wait] do
      refute Map.has_key?(status, absent)
    end
  end
end
