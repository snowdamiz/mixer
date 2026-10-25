defmodule MixerHosted.Builds.JournalTest do
  use ExUnit.Case, async: true

  alias MixerHosted.Builds.{Journal, Lifecycle}
  alias MixerHosted.Builds.Lifecycle.{ArtifactRef, Policy, Spec}

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

  defp sha(n), do: n |> Integer.to_string(16) |> String.downcase() |> String.pad_leading(64, "0")

  defp spec do
    %{
      organization_id: "org-1",
      project_id: "project-1",
      application_id: "app-1",
      build_id: "build-1",
      platform: :ios,
      source: %{kind: :revision, sha256: sha(100), reference: "refs/heads/main"},
      toolchain_lock_sha256: sha(101),
      build_definition_sha256: sha(102)
    }
  end

  defp policy, do: %{max_attempts: 5, timeout_ms: 100, retry_backoff_ms: 10}

  defp new!(spec \\ spec(), policy \\ policy(), key \\ "request-1", now \\ 0) do
    assert {:ok, document, build} = Journal.new(spec, policy, key, now)
    assert {:ok, ^build} = Journal.restore(document)
    assert {:ok, ^build} = document |> Jason.encode!() |> Jason.decode!() |> Journal.restore()
    {document, build}
  end

  defp append!({document, build}, id, event, now) do
    assert {:ok, expected, :applied} = Lifecycle.transition(build, id, event, now)
    assert {:ok, document, ^expected, :applied} = Journal.append(document, id, event, now)
    assert {:ok, ^expected} = Journal.restore(document)
    assert {:ok, ^expected} = document |> Jason.encode!() |> Jason.decode!() |> Journal.restore()
    assert byte_size(Jason.encode!(document)) <= 131_072
    {document, expected}
  end

  defp start!(pair, now \\ 1) do
    {_document, build} = pair
    assert {:ok, ref} = Lifecycle.worker_ref(build)
    append!(pair, "start-#{build.attempt}", %{type: :start, ref: ref}, now)
  end

  defp artifacts do
    Enum.with_index(@kinds, 1)
    |> Enum.map(fn {kind, n} -> %ArtifactRef{kind: kind, sha256: sha(n), size_bytes: n * 10} end)
  end

  defp success(ref),
    do: %{type: :completed, ref: ref, result: %{outcome: :succeeded, artifacts: artifacts()}}

  defp failure(ref, class \\ :infrastructure, code \\ :worker_lost),
    do: %{
      type: :completed,
      ref: ref,
      result: %{outcome: :failed, class: class, code: code, diagnostic_sha256: sha(200)}
    }

  defp stopped(ref), do: %{type: :stopped, ref: ref, diagnostic_sha256: sha(201)}
  defp cancel(reason \\ "Customer cancelled"), do: %{type: :cancel, reason: reason}

  defp row_event(document, index, fun),
    do:
      Map.update!(
        document,
        "events",
        &List.update_at(&1, index, fn row -> Map.update!(row, "event", fun) end)
      )

  test "creation has an exact string-key schema and accepts only lifecycle creation inputs" do
    {document, build} = new!()
    assert Map.keys(document) |> Enum.sort() == ["creation", "events", "schema"]
    assert document["schema"] === 1
    assert document["events"] === []

    assert document["creation"] == %{
             "spec" => %{
               "organization_id" => "org-1",
               "project_id" => "project-1",
               "application_id" => "app-1",
               "build_id" => "build-1",
               "platform" => "ios",
               "source" => %{
                 "kind" => "revision",
                 "sha256" => sha(100),
                 "reference" => "refs/heads/main"
               },
               "toolchain_lock_sha256" => sha(101),
               "build_definition_sha256" => sha(102)
             },
             "policy" => %{"max_attempts" => 5, "timeout_ms" => 100, "retry_backoff_ms" => 10},
             "request_key" => "request-1",
             "now_ms" => 0
           }

    assert build.state == :queued
    new!(struct!(Spec, spec()), struct!(Policy, policy()))

    {upload, android} =
      new!(%{
        spec()
        | platform: :android,
          source: %{kind: :upload, sha256: sha(1), reference: "upload-1"}
      })

    assert upload["creation"]["spec"]["source"]["kind"] == "upload"
    assert android.spec.platform == :android

    for {input, expected} <- [
          {{Map.put(spec(), :extra, true), policy(), "r", 0}, :invalid_spec},
          {{%{}, policy(), "r", 0}, :invalid_spec},
          {{spec(), Map.put(policy(), :extra, true), "r", 0}, :invalid_policy},
          {{spec(), policy(), "", 0}, :invalid_request},
          {{spec(), policy(), "r", -1}, :invalid_request}
        ] do
      {spec, policy, key, now} = input
      assert {:error, ^expected} = Journal.new(spec, policy, key, now)
    end
  end

  test "success round trips every artifact kind, exact refs and the lifecycle history" do
    {document, build} = new!() |> start!()
    ref = build.active_ref
    {done_document, done} = append!({document, build}, "completed", success(ref), 2)
    assert done.state == :succeeded
    assert done.artifacts == artifacts()
    assert [%{state: :succeeded, worker_ref: ^ref}] = done.history

    assert Enum.at(done_document["events"], 0) == %{
             "id" => "start-1",
             "now_ms" => 1,
             "event" => %{
               "type" => "start",
               "ref" => %{
                 "organization_id" => "org-1",
                 "project_id" => "project-1",
                 "application_id" => "app-1",
                 "build_id" => "build-1",
                 "platform" => "ios",
                 "attempt" => 1,
                 "fence" => 1
               }
             }
           }

    persisted = Enum.at(done_document["events"], 1)["event"]["result"]["artifacts"]
    assert Enum.map(persisted, & &1["kind"]) == Enum.map(@kinds, &Atom.to_string/1)

    assert Enum.all?(
             persisted,
             &(Map.keys(&1) |> Enum.sort() == ["kind", "sha256", "size_bytes"])
           )

    assert {:ok, status} = Lifecycle.customer_status(done)
    assert status.artifacts == artifacts()
    assert status.worker_completion_pending == false
  end

  test "queued cancellation and every matching cancellation reconciliation outcome replay" do
    {_document, cancelled} = append!(new!(), "cancel", cancel(), 0)
    assert cancelled.state == :cancelled
    assert [%{worker_ref: nil}] = cancelled.history

    for expire? <- [false, true], terminal <- [:stopped, :succeeded, :failed] do
      {document, running} = new!() |> start!()
      ref = running.active_ref

      pair =
        if expire?,
          do: append!({document, running}, "expire", %{type: :expire, ref: ref}, 101),
          else: {document, running}

      pair = append!(pair, "cancel", cancel(), 102)
      {pending_document, pending} = pair
      assert pending.state == :cancelling
      assert pending.active_ref == ref
      assert pending.fence == if(expire?, do: 3, else: 2)
      assert {:ok, ^pending} = Journal.restore(pending_document)

      event =
        case terminal do
          :stopped -> stopped(ref)
          :succeeded -> success(ref)
          :failed -> failure(ref)
        end

      {_document, done} = append!(pair, "terminal", event, 103)

      assert {done.state, done.failure, done.artifacts, done.retry_after} ==
               {:cancelled, nil, nil, nil}
    end
  end

  test "timeout uncertainty, definitive completion, retry and late non-infrastructure failure survive replay" do
    {document, running} = new!() |> start!()
    ref = running.active_ref
    pair = append!({document, running}, "expire", %{type: :expire, ref: ref}, 101)
    {pending_document, pending} = pair
    assert pending.state == :reconciling
    assert pending.active_ref == ref

    assert {:error, :invalid_transition} =
             Journal.append(pending_document, "retry", %{type: :retry}, 102)

    for terminal <- [stopped(ref), success(ref), failure(ref)] do
      {done_document, done} = append!(pair, "terminal", terminal, 102)
      assert done.state == :timed_out
      assert done.failure.class == :infrastructure
      assert done.failure.code == :worker_timeout
      {retried_document, retried} = append!({done_document, done}, "retry", %{type: :retry}, 112)
      assert {retried.state, retried.attempt, retried.fence} == {:queued, 2, 4}

      assert {:error, :stale_worker_ref} =
               Journal.append(retried_document, "old-start", %{type: :start, ref: ref}, 113)

      {_next_document, next} = start!({retried_document, retried}, 113)
      assert next.active_ref.fence == 4
    end

    {_document, late} =
      append!({document, running}, "late-compiler", failure(ref, :compiler, :compiler_error), 101)

    assert late.state == :timed_out
    assert late.failure.class == :compiler
    assert late.retry_after == nil
    {_document, late_success} = append!({document, running}, "late-success", success(ref), 101)
    assert late_success.failure.diagnostic_sha256 == nil
    {_document, on_time} = append!({document, running}, "on-time", success(ref), 100)
    assert on_time.state == :succeeded
  end

  test "every declared failure code is converted and lifecycle semantics remain authoritative" do
    pairs = [
      {:infrastructure, :worker_unavailable},
      {:infrastructure, :worker_lost},
      {:infrastructure, :dependency_transport},
      {:infrastructure, :artifact_transport},
      {:infrastructure, :worker_timeout},
      {:compiler, :compiler_error},
      {:test, :test_failure},
      {:policy, :policy_rejection},
      {:policy, :invalid_input},
      {:unknown, :unknown_failure}
    ]

    for {class, code} <- pairs do
      {document, build} = new!() |> start!()

      {_done_document, done} =
        append!({document, build}, "failure", failure(build.active_ref, class, code), 2)

      assert done.state == :failed
      assert done.failure == %{class: class, code: code, diagnostic_sha256: sha(200)}
      assert {:ok, status} = Lifecycle.customer_status(done)
      assert status.retryable == (class == :infrastructure)
    end

    {document, build} = new!() |> start!()

    assert {:error, :invalid_event} =
             Journal.append(
               document,
               "mixed",
               failure(build.active_ref, :compiler, :worker_lost),
               2
             )

    assert {:error, :invalid_observation_time} =
             Journal.append(document, "backwards", stopped(build.active_ref), 0)

    assert {:error, :deadline_not_reached} =
             Journal.append(document, "early", %{type: :expire, ref: build.active_ref}, 100)
  end

  test "all five timeout attempts and backoff fences replay through the longest retry path" do
    pair =
      Enum.reduce(1..5, new!(), fn attempt, pair ->
        now = (attempt - 1) * 120 + 1
        {document, running} = start!(pair, now)

        pair =
          append!(
            {document, running},
            "expire-#{attempt}",
            %{type: :expire, ref: running.active_ref},
            now + 100
          )

        {document, timed_out} =
          append!(pair, "stop-#{attempt}", stopped(running.active_ref), now + 101)

        assert timed_out.attempt == attempt

        if attempt < 5 do
          assert {:error, :backoff_not_reached} =
                   Journal.append(document, "early-retry", %{type: :retry}, now + 110)

          append!({document, timed_out}, "retry-#{attempt}", %{type: :retry}, now + 111)
        else
          assert {:error, :attempt_limit} =
                   Journal.append(document, "retry-5", %{type: :retry}, now + 111)

          {document, timed_out}
        end
      end)

    {document, build} = pair
    assert length(document["events"]) == 19
    assert Enum.map(build.history, & &1.attempt) == [1, 2, 3, 4, 5]
    assert build.state == :timed_out
  end

  test "duplicate delivery preserves the original journal and current build despite delivery time" do
    {document, build} = new!() |> start!()
    event = failure(build.active_ref)
    pair = append!({document, build}, "failure", event, 2)
    pair = append!(pair, "retry", %{type: :retry}, 12) |> start!(13)
    {document, current} = pair
    {document, current} = append!({document, current}, "done", success(current.active_ref), 14)

    for now <- [99_999, -1, nil, @max_time + 1, {:not, :a_time}] do
      assert {:ok, ^document, ^current, :duplicate} =
               Journal.append(document, "failure", event, now)
    end

    assert current.events["failure"].first_observed_at == 2
    assert current.observed_at == 14

    assert {:error, :event_conflict} =
             Journal.append(document, "failure", stopped(build.active_ref), 15)

    assert {:error, :event_conflict} =
             Journal.append(document, "failure", Map.put(event, :extra, true), 15)

    assert {:error, :event_conflict} = Journal.append(document, "failure", {:opaque, event}, 15)
    assert {:error, :invalid_event_id} = Journal.append(document, "", event, 15)
  end

  test "restore rejects snapshots, missing and extra fields, every enum mismatch and malformed creation data" do
    {document, build} = new!()

    for bad <- [
          build,
          nil,
          [],
          {document},
          Map.put(document, "state", "succeeded"),
          Map.put(document, "schema", 2),
          Map.put(document, "schema", 1.0),
          Map.put(document, :schema, 1),
          Map.put(document, "creation", build),
          Map.put(document, "creation", Map.put(document["creation"], "snapshot", build))
        ] do
      assert {:error, :invalid_journal} = Journal.restore(bad)
    end

    for key <- Map.keys(document),
        do: assert({:error, :invalid_journal} = Journal.restore(Map.delete(document, key)))

    creation = document["creation"]

    for key <- Map.keys(creation),
        do:
          assert(
            {:error, :invalid_journal} =
              Journal.restore(put_in(document, ["creation"], Map.delete(creation, key)))
          )

    persisted_spec = creation["spec"]

    for key <- Map.keys(persisted_spec) do
      assert {:error, :invalid_journal} =
               Journal.restore(
                 put_in(document, ["creation", "spec"], Map.delete(persisted_spec, key))
               )
    end

    for {path, value} <- [
          {["spec", "platform"], "linux"},
          {["spec", "platform"], :ios},
          {["spec", "source", "kind"], "branch"},
          {["spec", "source", "kind"], :revision},
          {["spec", "source", "sha256"], String.upcase(sha(255))},
          {["spec", "toolchain_lock_sha256"], String.duplicate("0", 63)},
          {["spec", "source", "reference"], <<255>>},
          {["spec", "build_id"], "a\0b"},
          {["policy", "max_attempts"], 6},
          {["policy", "timeout_ms"], 0},
          {["policy", "retry_backoff_ms"], 3_600_001},
          {["policy", "max_attempts"], 1.0},
          {["request_key"], ""},
          {["now_ms"], -1},
          {["now_ms"], @max_time + 1},
          {["now_ms"], 0.0}
        ] do
      assert {:error, :invalid_journal} =
               Journal.restore(put_in(document, ["creation" | path], value)),
             inspect(path)
    end

    for {path, key} <- [
          {["creation", "spec"], "grant"},
          {["creation", "spec", "source"], "token"},
          {["creation", "policy"], "allow"}
        ] do
      assert {:error, :invalid_journal} =
               Journal.restore(update_in(document, path, &Map.put(&1, key, true)))
    end
  end

  test "persisted event order, identity, observation times and exact worker scopes fail closed" do
    {document, running} = new!() |> start!()
    {done_document, _done} = append!({document, running}, "done", success(running.active_ref), 2)

    for bad <- [
          Map.update!(done_document, "events", &Enum.reverse/1),
          Map.update!(done_document, "events", &(&1 ++ [hd(&1)])),
          Map.update!(
            done_document,
            "events",
            &List.update_at(&1, 1, fn row -> Map.put(row, "id", "start-1") end)
          ),
          Map.update!(
            done_document,
            "events",
            &List.update_at(&1, 1, fn row -> Map.put(row, "now_ms", 0) end)
          ),
          Map.update!(
            done_document,
            "events",
            &List.update_at(&1, 0, fn row -> Map.put(row, "extra", true) end)
          ),
          Map.update!(
            done_document,
            "events",
            &List.update_at(&1, 0, fn row -> Map.put(row, "id", "") end)
          ),
          Map.update!(
            done_document,
            "events",
            &List.update_at(&1, 0, fn row -> Map.delete(row, "now_ms") end)
          ),
          row_event(done_document, 0, &Map.put(&1, "type", "dispatch")),
          row_event(done_document, 0, &Map.put(&1, "extra", true)),
          row_event(done_document, 0, &put_in(&1, ["ref", "extra"], true)),
          row_event(done_document, 0, &Map.put(&1, "ref", running.active_ref)),
          row_event(done_document, 0, &Map.put(&1, "ref", Map.from_struct(running.active_ref)))
        ] do
      assert {:error, :invalid_journal} = Journal.restore(bad)
    end

    for {key, value} <- [
          {"organization_id", "other"},
          {"project_id", "other"},
          {"application_id", "other"},
          {"build_id", "other"},
          {"platform", "android"},
          {"attempt", 2},
          {"fence", 2},
          {"attempt", 0},
          {"fence", @max_time + 1},
          {"platform", "linux"}
        ] do
      assert {:error, :invalid_journal} =
               Journal.restore(row_event(done_document, 0, &put_in(&1, ["ref", key], value)))
    end

    {failed_document, _failed} =
      append!({document, running}, "failed", failure(running.active_ref), 2)

    for {key, value} <- [
          {"outcome", "maybe"},
          {"class", "other"},
          {"code", "other"},
          {"diagnostic_sha256", nil},
          {"class", "compiler"}
        ] do
      assert {:error, :invalid_journal} =
               Journal.restore(row_event(failed_document, 1, &put_in(&1, ["result", key], value)))
    end
  end

  test "artifact encoding rejects extra fields, missing kinds, invalid bytes and semantic content conflicts" do
    {document, running} = new!() |> start!()
    event = success(running.active_ref)
    [first | rest] = artifacts()

    for refs <- [
          [],
          rest,
          artifacts() ++ [first],
          List.duplicate(first, 7),
          [%{first | kind: :other} | rest],
          [%{first | size_bytes: 0} | rest],
          [%{first | size_bytes: @max_time + 1} | rest],
          [%{first | sha256: sha(1) <> "0"} | rest],
          [Map.put(first, :extra, true) | rest],
          [Map.from_struct(first) | rest],
          [%{first | sha256: sha(2), size_bytes: 1} | rest]
        ] do
      assert {:error, :invalid_event} =
               Journal.append(document, "bad", put_in(event, [:result, :artifacts], refs), 2)
    end

    {done_document, _done} = append!({document, running}, "done", event, 2)

    for {key, value} <- [
          {"kind", "native_binary"},
          {"kind", :provenance},
          {"sha256", "bad"},
          {"size_bytes", 0},
          {"size_bytes", 1.0},
          {"extra", true}
        ] do
      corrupted =
        row_event(done_document, 1, fn event ->
          update_in(
            event,
            ["result", "artifacts"],
            &List.update_at(&1, 0, fn artifact -> Map.put(artifact, key, value) end)
          )
        end)

      assert {:error, :invalid_journal} = Journal.restore(corrupted)
    end
  end

  test "shared artifact content and primitive maximum bounds preserve lifecycle acceptance" do
    policy = %{max_attempts: 1, timeout_ms: 86_400_000, retry_backoff_ms: 3_600_000}
    {document, build} = new!(spec(), policy)
    {document, running} = start!({document, build}, @max_time - 86_400_000)
    shared = Enum.map(artifacts(), &%{&1 | sha256: sha(1), size_bytes: @max_time})
    event = put_in(success(running.active_ref), [:result, :artifacts], shared)
    {_document, done} = append!({document, running}, "done", event, @max_time - 1)
    assert done.state == :succeeded
    assert done.artifacts == shared
    new!(spec(), %{max_attempts: 1, timeout_ms: 1, retry_backoff_ms: 0})
  end

  test "native input maps, refs, tuples and unsupported events cannot carry hidden fields or structs" do
    {document, running} = new!() |> start!()
    ref = running.active_ref

    for event <- [
          %{type: :retry, extra: true},
          %{type: "retry"},
          %{type: :unknown},
          %{type: :cancel},
          %{type: :cancel, reason: "ok", extra: true},
          %{type: :start, ref: Map.from_struct(ref)},
          %{type: :start, ref: Map.put(ref, :extra, true)},
          %{type: :start, ref: %{ref | platform: ["ios"]}},
          %{type: :start, ref: %{ref | attempt: 1.0}},
          %{type: :stopped, ref: ref, diagnostic_sha256: nil},
          put_in(success(ref), [:result, :outcome], "succeeded"),
          put_in(failure(ref), [:result, :class], ["infrastructure"]),
          put_in(failure(ref), [:result, :code], %{unknown: true}),
          Map.put(success(ref), :extra, true),
          {ref, :stop},
          running,
          nil,
          []
        ] do
      assert {:error, :invalid_event} = Journal.append(document, "bad", event, 2)
    end

    for key <- [:organization_id, :project_id, :application_id, :build_id] do
      assert {:error, :stale_worker_ref} =
               Journal.append(document, "scope", stopped(Map.put(ref, key, "other")), 2)
    end

    for now <- [-1, nil, 2.0, @max_time + 1] do
      assert {:error, :invalid_observation_time} =
               Journal.append(document, "stop", stopped(ref), now)
    end

    assert {:error, :invalid_journal} = Journal.append(%{}, "stop", stopped(ref), 2)
  end

  test "bounded UTF-8 byte lengths preserve Unicode and JSON escaping without normalization" do
    unicode = String.duplicate("é", 64)
    reference = String.duplicate("🧪", 256)

    spec = %{
      spec()
      | organization_id: unicode,
        build_id: unicode,
        source: %{kind: :upload, sha256: sha(1), reference: reference}
    }

    pair = new!(spec, policy(), unicode, @max_time)
    {document, build} = pair

    assert {:error, :time_overflow} =
             Journal.append(
               document,
               "start",
               %{type: :start, ref: elem(Lifecycle.worker_ref(build), 1)},
               @max_time
             )

    assert {:error, :invalid_spec} =
             Journal.new(%{spec | build_id: unicode <> "a"}, policy(), "r", 0)

    assert {:error, :invalid_spec} =
             Journal.new(put_in(spec, [:source, :reference], reference <> "a"), policy(), "r", 0)

    assert {:error, :invalid_request} = Journal.new(spec, policy(), unicode <> "a", 0)

    {document, build} =
      new!(%{spec | source: %{spec.source | reference: "line\n\t\"\\é🧪"}}, policy(), unicode)

    assert {:ok, ref} = Lifecycle.worker_ref(build)
    {document, running} = append!({document, build}, unicode, %{type: :start, ref: ref}, 1)
    assert {:error, :invalid_event_id} = Journal.append(document, unicode <> "a", cancel(), 2)
    reason = String.duplicate("é", 256)
    {document, pending} = append!({document, running}, "cancel", cancel(reason), 2)
    assert pending.state == :cancelling

    assert {:error, :invalid_event} =
             Journal.append(document, "big-reason", cancel(reason <> "a"), 3)

    assert Enum.at(document["events"], 1)["event"]["reason"] == reason
  end

  test "event list ceilings and deep or oversized inputs are rejected before unbounded traversal" do
    {document, _build} = new!()
    deep = Enum.reduce(1..50_000, "leaf", fn _, nested -> [nested] end)
    huge = String.duplicate("x", 131_073)
    row = %{"id" => "cancel", "event" => %{"type" => "cancel", "reason" => "stop"}, "now_ms" => 0}

    for count <- [31, 32, 33] do
      assert {:error, :invalid_journal} =
               Journal.restore(Map.put(document, "events", List.duplicate(row, count)))
    end

    for bad <- [
          deep,
          Map.put(document, "events", deep),
          Map.put(document, "events", [row | :improper]),
          Map.put(document, "events", List.duplicate(deep, 33)),
          put_in(document, ["creation", "spec", "source"], deep),
          put_in(document, ["creation", "spec", "source", "reference"], huge),
          put_in(document, ["creation", "request_key"], huge),
          put_in(document, ["creation", "spec", "platform"], deep),
          Map.put(document, huge, deep),
          Map.put(document, "events", [%{"id" => huge, "event" => deep, "now_ms" => 0}])
        ] do
      assert {:error, :invalid_journal} = Journal.restore(bad)
    end

    for event <- [
          deep,
          %{type: :cancel, reason: huge},
          %{type: :completed, ref: deep, result: deep},
          %{type: :retry, huge: deep}
        ] do
      assert {:error, :invalid_event} = Journal.append(document, "bad", event, 0)
    end

    assert {:error, :invalid_spec} = Journal.new(%{spec() | source: deep}, policy(), "r", 0)
    assert {:error, :invalid_event_id} = Journal.append(document, huge, cancel(), 0)
  end
end
