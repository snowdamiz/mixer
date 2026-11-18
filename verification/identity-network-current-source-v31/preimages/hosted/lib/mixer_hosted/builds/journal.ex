defmodule MixerHosted.Builds.Journal do
  @moduledoc """
  Closed, bounded JSON-compatible lifecycle journals for internal persistence.

  Only creation inputs and ordered events are persisted. Restore replays the
  accepted lifecycle API; no caller-provided Build snapshot is hydrated. This
  codec provides neither authorization nor source, worker or artifact proof.
  """

  alias MixerHosted.Builds.Lifecycle
  alias MixerHosted.Builds.Lifecycle.{ArtifactRef, WorkerRef}

  @max_time 9_223_372_036_854_775_807
  @max_events 32
  @max_bytes 128 * 1024
  @scope ~w(organization_id project_id application_id build_id platform)
  @spec_fields @scope ++ ~w(source toolchain_lock_sha256 build_definition_sha256)
  @policy ~w(max_attempts timeout_ms retry_backoff_ms)
  @ref @scope ++ ~w(attempt fence)
  @ref_keys [
    :organization_id,
    :project_id,
    :application_id,
    :build_id,
    :platform,
    :attempt,
    :fence
  ]
  @kinds [
    unsigned_native_binary: "unsigned_native_binary",
    guest_artifact: "guest_artifact",
    resource_inventory: "resource_inventory",
    debug_symbols: "debug_symbols",
    compatibility_report: "compatibility_report",
    sbom: "sbom",
    provenance: "provenance"
  ]
  @classes [
    infrastructure: "infrastructure",
    compiler: "compiler",
    test: "test",
    policy: "policy",
    unknown: "unknown"
  ]
  @codes [
    worker_unavailable: "worker_unavailable",
    worker_lost: "worker_lost",
    dependency_transport: "dependency_transport",
    artifact_transport: "artifact_transport",
    worker_timeout: "worker_timeout",
    compiler_error: "compiler_error",
    test_failure: "test_failure",
    policy_rejection: "policy_rejection",
    invalid_input: "invalid_input",
    unknown_failure: "unknown_failure"
  ]

  @doc "Creates a canonical schema-1 journal and its validated queued build."
  def new(spec, policy, request_key, now_ms) do
    with {:ok, build} <- Lifecycle.new(spec, policy, request_key, now_ms) do
      document = %{
        "schema" => 1,
        "creation" => %{
          "spec" => encode_spec(build.spec),
          "policy" => %{
            "max_attempts" => build.policy.max_attempts,
            "timeout_ms" => build.policy.timeout_ms,
            "retry_backoff_ms" => build.policy.retry_backoff_ms
          },
          "request_key" => build.request_key,
          "now_ms" => build.queued_at
        },
        "events" => []
      }

      if bounded_json?(document), do: {:ok, document, build}, else: {:error, :journal_limit}
    end
  end

  @doc "Replays an exact schema-1 document; every stored row must newly apply."
  def restore(document) do
    with true <- exact?(document, ~w(schema creation events)),
         1 <- document["schema"],
         {:ok, spec, policy, request_key, now_ms} <- decode_creation(document["creation"]),
         {:ok, rows} <- decode_rows(document["events"]),
         true <- bounded_json?(document),
         {:ok, build} <- Lifecycle.new(spec, policy, request_key, now_ms),
         {:ok, build} <- replay(rows, build) do
      {:ok, build}
    else
      _ -> {:error, :invalid_journal}
    end
  end

  @doc """
  Appends a lifecycle event. Exact duplicate delivery retains the original
  document and current replayed build, ignoring the duplicate delivery time.
  """
  def append(document, event_id, event, now_ms) do
    with {:ok, build} <- restore(document),
         true <- text?(event_id, 128) do
      case encode_event(event) do
        {:ok, encoded} ->
          append_event(document, build, event_id, event, encoded, now_ms)

        :error ->
          reason =
            if Map.has_key?(build.events, event_id), do: :event_conflict, else: :invalid_event

          {:error, reason}
      end
    else
      false -> {:error, :invalid_event_id}
      error -> error
    end
  end

  defp append_event(document, build, event_id, event, encoded, now_ms) do
    with {:ok, updated, outcome} <- Lifecycle.transition(build, event_id, event, now_ms) do
      if outcome == :duplicate do
        {:ok, document, updated, :duplicate}
      else
        row = %{"id" => event_id, "event" => encoded, "now_ms" => now_ms}
        appended = Map.update!(document, "events", &(&1 ++ [row]))

        if bounded_json?(appended),
          do: {:ok, appended, updated, :applied},
          else: {:error, :journal_limit}
      end
    end
  end

  defp replay(rows, build) do
    Enum.reduce_while(rows, {:ok, build}, fn {id, event, now_ms}, {:ok, current} ->
      case Lifecycle.transition(current, id, event, now_ms) do
        {:ok, updated, :applied} -> {:cont, {:ok, updated}}
        _ -> {:halt, :error}
      end
    end)
  end

  defp encode_spec(spec) do
    %{
      "organization_id" => spec.organization_id,
      "project_id" => spec.project_id,
      "application_id" => spec.application_id,
      "build_id" => spec.build_id,
      "platform" => encode_enum!(spec.platform, ios: "ios", android: "android"),
      "source" => %{
        "kind" => encode_enum!(spec.source.kind, revision: "revision", upload: "upload"),
        "sha256" => spec.source.sha256,
        "reference" => spec.source.reference
      },
      "toolchain_lock_sha256" => spec.toolchain_lock_sha256,
      "build_definition_sha256" => spec.build_definition_sha256
    }
  end

  defp decode_creation(value) do
    with true <- exact?(value, ~w(spec policy request_key now_ms)),
         {:ok, spec} <- decode_spec(value["spec"]),
         {:ok, policy} <- decode_policy(value["policy"]),
         true <- text?(value["request_key"], 128),
         true <- time?(value["now_ms"]) do
      {:ok, spec, policy, value["request_key"], value["now_ms"]}
    else
      _ -> :error
    end
  end

  defp decode_spec(value) do
    with true <- exact?(value, @spec_fields),
         {:ok, scope} <- decode_scope(value),
         source = value["source"],
         true <- exact?(source, ~w(kind sha256 reference)),
         {:ok, kind} <- decode_enum(source["kind"], revision: "revision", upload: "upload"),
         true <- sha?(source["sha256"]) and text?(source["reference"], 1024),
         true <- sha?(value["toolchain_lock_sha256"]) and sha?(value["build_definition_sha256"]) do
      {:ok,
       Map.merge(scope, %{
         source: %{kind: kind, sha256: source["sha256"], reference: source["reference"]},
         toolchain_lock_sha256: value["toolchain_lock_sha256"],
         build_definition_sha256: value["build_definition_sha256"]
       })}
    else
      _ -> :error
    end
  end

  defp decode_scope(value) do
    with true <- Enum.all?(@scope -- ["platform"], &text?(value[&1], 128)),
         {:ok, platform} <- decode_enum(value["platform"], ios: "ios", android: "android") do
      {:ok,
       %{
         organization_id: value["organization_id"],
         project_id: value["project_id"],
         application_id: value["application_id"],
         build_id: value["build_id"],
         platform: platform
       }}
    else
      _ -> :error
    end
  end

  defp decode_policy(value) do
    if exact?(value, @policy) and integer?(value["max_attempts"], 1, 5) and
         integer?(value["timeout_ms"], 1, 86_400_000) and
         integer?(value["retry_backoff_ms"], 0, 3_600_000) do
      {:ok,
       %{
         max_attempts: value["max_attempts"],
         timeout_ms: value["timeout_ms"],
         retry_backoff_ms: value["retry_backoff_ms"]
       }}
    else
      :error
    end
  end

  defp decode_rows(rows) do
    if bounded_list?(rows, 0, @max_events) do
      Enum.reduce_while(rows, {:ok, []}, fn row, {:ok, acc} ->
        with true <- exact?(row, ~w(id event now_ms)),
             true <- text?(row["id"], 128) and time?(row["now_ms"]),
             {:ok, event} <- decode_event(row["event"]) do
          {:cont, {:ok, [{row["id"], event, row["now_ms"]} | acc]}}
        else
          _ -> {:halt, :error}
        end
      end)
      |> case do
        {:ok, decoded} -> {:ok, Enum.reverse(decoded)}
        :error -> :error
      end
    else
      :error
    end
  end

  defp encode_event(%{type: type, ref: ref} = value) when type in [:start, :expire] do
    with true <- exact?(value, [:type, :ref]),
         {:ok, ref} <- encode_ref(ref) do
      {:ok, %{"type" => encode_enum!(type, start: "start", expire: "expire"), "ref" => ref}}
    else
      _ -> :error
    end
  end

  defp encode_event(%{type: :cancel, reason: reason} = value) do
    if exact?(value, [:type, :reason]) and text?(reason, 512),
      do: {:ok, %{"type" => "cancel", "reason" => reason}},
      else: :error
  end

  defp encode_event(%{type: :retry} = value) do
    if exact?(value, [:type]), do: {:ok, %{"type" => "retry"}}, else: :error
  end

  defp encode_event(%{type: :stopped, ref: ref, diagnostic_sha256: digest} = value) do
    with true <- exact?(value, [:type, :ref, :diagnostic_sha256]) and sha?(digest),
         {:ok, ref} <- encode_ref(ref) do
      {:ok, %{"type" => "stopped", "ref" => ref, "diagnostic_sha256" => digest}}
    else
      _ -> :error
    end
  end

  defp encode_event(%{type: :completed, ref: ref, result: result} = value) do
    with true <- exact?(value, [:type, :ref, :result]),
         {:ok, ref} <- encode_ref(ref),
         {:ok, result} <- encode_result(result) do
      {:ok, %{"type" => "completed", "ref" => ref, "result" => result}}
    else
      _ -> :error
    end
  end

  defp encode_event(_), do: :error

  defp decode_event(%{"type" => type, "ref" => ref} = value) when type in ["start", "expire"] do
    with true <- exact?(value, ~w(type ref)),
         {:ok, ref} <- decode_ref(ref),
         {:ok, type} <- decode_enum(type, start: "start", expire: "expire") do
      {:ok, %{type: type, ref: ref}}
    else
      _ -> :error
    end
  end

  defp decode_event(%{"type" => "cancel", "reason" => reason} = value) do
    if exact?(value, ~w(type reason)) and text?(reason, 512),
      do: {:ok, %{type: :cancel, reason: reason}},
      else: :error
  end

  defp decode_event(%{"type" => "retry"} = value) do
    if exact?(value, ["type"]), do: {:ok, %{type: :retry}}, else: :error
  end

  defp decode_event(%{"type" => "stopped", "ref" => ref, "diagnostic_sha256" => digest} = value) do
    with true <- exact?(value, ~w(type ref diagnostic_sha256)) and sha?(digest),
         {:ok, ref} <- decode_ref(ref) do
      {:ok, %{type: :stopped, ref: ref, diagnostic_sha256: digest}}
    else
      _ -> :error
    end
  end

  defp decode_event(%{"type" => "completed", "ref" => ref, "result" => result} = value) do
    with true <- exact?(value, ~w(type ref result)),
         {:ok, ref} <- decode_ref(ref),
         {:ok, result} <- decode_result(result) do
      {:ok, %{type: :completed, ref: ref, result: result}}
    else
      _ -> :error
    end
  end

  defp decode_event(_), do: :error

  defp encode_ref(%WorkerRef{} = value) do
    if exact_struct?(value, WorkerRef, @ref_keys) do
      encoded = %{
        "organization_id" => value.organization_id,
        "project_id" => value.project_id,
        "application_id" => value.application_id,
        "build_id" => value.build_id,
        "platform" => encode_enum(value.platform, ios: "ios", android: "android"),
        "attempt" => value.attempt,
        "fence" => value.fence
      }

      case decode_ref(encoded) do
        {:ok, _} -> {:ok, encoded}
        _ -> :error
      end
    else
      :error
    end
  end

  defp encode_ref(_), do: :error

  defp decode_ref(value) do
    with true <- exact?(value, @ref),
         {:ok, scope} <- decode_scope(value),
         true <- integer?(value["attempt"], 1, 5) and integer?(value["fence"], 1, @max_time) do
      {:ok,
       struct!(WorkerRef, Map.merge(scope, %{attempt: value["attempt"], fence: value["fence"]}))}
    else
      _ -> :error
    end
  end

  defp encode_result(%{outcome: :succeeded, artifacts: artifacts} = value) do
    with true <- exact?(value, [:outcome, :artifacts]) and bounded_list?(artifacts, 7, 7),
         {:ok, encoded} <- map_valid(artifacts, &encode_artifact/1) do
      {:ok, %{"outcome" => "succeeded", "artifacts" => encoded}}
    else
      _ -> :error
    end
  end

  defp encode_result(%{outcome: :failed} = value) do
    if exact?(value, [:outcome, :class, :code, :diagnostic_sha256]) and
         sha?(value.diagnostic_sha256) do
      encoded = %{
        "outcome" => "failed",
        "class" => encode_enum(value.class, @classes),
        "code" => encode_enum(value.code, @codes),
        "diagnostic_sha256" => value.diagnostic_sha256
      }

      case decode_result(encoded) do
        {:ok, _} -> {:ok, encoded}
        _ -> :error
      end
    else
      :error
    end
  end

  defp encode_result(_), do: :error

  defp decode_result(%{"outcome" => "succeeded", "artifacts" => artifacts} = value) do
    with true <- exact?(value, ~w(outcome artifacts)) and bounded_list?(artifacts, 7, 7),
         {:ok, decoded} <- map_valid(artifacts, &decode_artifact/1) do
      {:ok, %{outcome: :succeeded, artifacts: decoded}}
    else
      _ -> :error
    end
  end

  defp decode_result(%{"outcome" => "failed"} = value) do
    with true <- exact?(value, ~w(outcome class code diagnostic_sha256)),
         true <- sha?(value["diagnostic_sha256"]),
         {:ok, class} <- decode_enum(value["class"], @classes),
         {:ok, code} <- decode_enum(value["code"], @codes) do
      {:ok,
       %{
         outcome: :failed,
         class: class,
         code: code,
         diagnostic_sha256: value["diagnostic_sha256"]
       }}
    else
      _ -> :error
    end
  end

  defp decode_result(_), do: :error

  defp encode_artifact(%ArtifactRef{} = value) do
    if exact_struct?(value, ArtifactRef, [:kind, :sha256, :size_bytes]) do
      encoded = %{
        "kind" => encode_enum(value.kind, @kinds),
        "sha256" => value.sha256,
        "size_bytes" => value.size_bytes
      }

      case decode_artifact(encoded) do
        {:ok, _} -> {:ok, encoded}
        _ -> :error
      end
    else
      :error
    end
  end

  defp encode_artifact(_), do: :error

  defp decode_artifact(value) do
    with true <- exact?(value, ~w(kind sha256 size_bytes)),
         {:ok, kind} <- decode_enum(value["kind"], @kinds),
         true <- sha?(value["sha256"]) and integer?(value["size_bytes"], 1, @max_time) do
      {:ok, %ArtifactRef{kind: kind, sha256: value["sha256"], size_bytes: value["size_bytes"]}}
    else
      _ -> :error
    end
  end

  defp map_valid(values, fun) do
    Enum.reduce_while(values, {:ok, []}, fn value, {:ok, acc} ->
      case fun.(value) do
        {:ok, converted} -> {:cont, {:ok, [converted | acc]}}
        _ -> {:halt, :error}
      end
    end)
    |> case do
      {:ok, reversed} -> {:ok, Enum.reverse(reversed)}
      :error -> :error
    end
  end

  # Both sides are finite compile-time enum tables. No caller string becomes an atom.
  defp encode_enum(value, pairs) do
    case Enum.find(pairs, fn {atom, _string} -> atom === value end) do
      {_atom, string} -> string
      nil -> nil
    end
  end

  defp encode_enum!(value, pairs), do: Keyword.fetch!(pairs, value)

  defp decode_enum(value, pairs) do
    case Enum.find(pairs, fn {_atom, string} -> string === value end) do
      {atom, _string} -> {:ok, atom}
      nil -> :error
    end
  end

  defp exact?(value, keys),
    do:
      is_map(value) and not is_struct(value) and map_size(value) == length(keys) and
        Enum.all?(keys, &Map.has_key?(value, &1))

  defp exact_struct?(value, module, keys),
    do:
      is_struct(value, module) and map_size(value) == length(keys) + 1 and
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

  defp bounded_list?([], min, _max), do: min <= 0
  defp bounded_list?([_ | rest], min, max) when max > 0, do: bounded_list?(rest, min - 1, max - 1)
  defp bounded_list?(_, _, _), do: false

  # Run only after closed-schema field/list bounds. Count default JSON bytes
  # without allocating an encoded copy or traversing caller-controlled depth.
  defp bounded_json?(value), do: match?({:ok, _}, json_budget(value, @max_bytes, 0))
  defp json_budget(_, budget, _) when budget < 0, do: :error
  defp json_budget(_, _, depth) when depth > 8, do: :error

  defp json_budget(value, budget, _depth) when is_binary(value) do
    remaining = budget - 2 - escaped_size(value, 0)
    if remaining >= 0, do: {:ok, remaining}, else: :error
  end

  defp json_budget(value, budget, _depth) when is_integer(value) do
    remaining = budget - byte_size(Integer.to_string(value))
    if remaining >= 0, do: {:ok, remaining}, else: :error
  end

  defp json_budget(value, budget, depth) when is_map(value) do
    json_members(Map.to_list(value), budget - 2, depth, fn {key, member}, left ->
      with {:ok, left} <- json_budget(key, left, depth + 1),
           {:ok, left} <- json_budget(member, left - 1, depth + 1) do
        {:ok, left}
      end
    end)
  end

  defp json_budget(value, budget, depth) when is_list(value),
    do: json_members(value, budget - 2, depth, &json_budget(&1, &2, depth + 1))

  defp json_members([], budget, _depth, _fun) when budget >= 0, do: {:ok, budget}
  defp json_members([], _, _, _), do: :error

  defp json_members([value | rest], budget, depth, fun) do
    with {:ok, left} <- fun.(value, budget) do
      json_members(rest, left - if(rest == [], do: 0, else: 1), depth, fun)
    end
  end

  defp escaped_size(<<>>, size), do: size

  defp escaped_size(<<byte, rest::binary>>, size) do
    extra =
      cond do
        byte in [8, 9, 10, 12, 13, ?", ?\\] -> 2
        byte < 32 -> 6
        true -> 1
      end

    escaped_size(rest, size + extra)
  end
end
