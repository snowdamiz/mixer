defmodule MixerHosted.Builds.WorkerWire do
  @moduledoc "Exact bounded v1 external-worker messages; no authorization is inferred."
  alias MixerHosted.Builds.{Dispatch, Lifecycle}
  alias MixerHosted.Identity.BoundedJSON
  @max 9_223_372_036_854_775_807
  @scope ~w(organization_id project_id application_id build_id platform)a
  @ref @scope ++ [:attempt, :fence]
  @spec_keys @scope ++ [:source, :toolchain_lock_sha256, :build_definition_sha256]
  @kinds ~w(unsigned_native_binary guest_artifact resource_inventory debug_symbols compatibility_report sbom provenance)a
  @failures %{
    "infrastructure" =>
      {:infrastructure,
       %{
         "worker_unavailable" => :worker_unavailable,
         "worker_lost" => :worker_lost,
         "dependency_transport" => :dependency_transport,
         "artifact_transport" => :artifact_transport,
         "worker_timeout" => :worker_timeout
       }},
    "compiler" => {:compiler, %{"compiler_error" => :compiler_error}},
    "test" => {:test, %{"test_failure" => :test_failure}},
    "policy" =>
      {:policy, %{"policy_rejection" => :policy_rejection, "invalid_input" => :invalid_input}},
    "unknown" => {:unknown, %{"unknown_failure" => :unknown_failure}}
  }
  @kind_map Map.new(@kinds, &{Atom.to_string(&1), &1})

  def encode(command, %Dispatch.Request{} = request, config)
      when command in [:query, :ensure_started, :stop] do
    with {:ok, ref} <- ref(request.ref),
         {:ok, spec} <- spec(request.spec),
         true <- Map.take(ref, @scope) == Map.take(spec, @scope),
         true <- integer?(request.deadline_ms, 1, @max),
         true <- exact?(request.guard, [:record_id, :revision, :owner_id, :epoch, :expires_at]),
         g = request.guard,
         true <- uuid?(g.record_id),
         true <- text?(g.owner_id, 128),
         true <- integer?(g.revision, 0, 32) and integer?(g.epoch, 1, @max),
         %DateTime{} <- g.expires_at,
         expiry = DateTime.to_unix(g.expires_at, :microsecond),
         true <- integer?(expiry, 1, @max),
         true <- request.operation_id == operation_id(g.record_id, ref),
         true <- ref.platform in config.platforms do
      wire_ref = stringify_ref(ref)
      wire_spec = stringify_spec(spec)
      deadline = Integer.to_string(request.deadline_ms)

      immutable = [
        "mixer-worker-binding-v1",
        request.operation_id,
        g.record_id,
        [
          ref.organization_id,
          ref.project_id,
          ref.application_id,
          ref.build_id,
          Atom.to_string(ref.platform),
          ref.attempt,
          Integer.to_string(ref.fence)
        ],
        [
          spec.organization_id,
          spec.project_id,
          spec.application_id,
          spec.build_id,
          Atom.to_string(spec.platform),
          Atom.to_string(spec.source.kind),
          spec.source.sha256,
          spec.source.reference,
          spec.toolchain_lock_sha256,
          spec.build_definition_sha256
        ],
        deadline
      ]

      envelope = %{
        "version" => 1,
        "environment_id" => config.environment_id,
        "pool_id" => config.pool_id,
        "controller_id" => config.controller_id,
        "request_id" => Base.encode16(:crypto.strong_rand_bytes(16), case: :lower),
        "command" => Atom.to_string(command),
        "operation_id" => request.operation_id,
        "immutable_sha256" => sha(Jason.encode!(immutable)),
        "ref" => wire_ref,
        "spec" => wire_spec,
        "deadline_ms" => deadline,
        "guard" => %{
          "record_id" => g.record_id,
          "revision" => Integer.to_string(g.revision),
          "owner_id" => g.owner_id,
          "epoch" => Integer.to_string(g.epoch),
          "expires_at_us" => Integer.to_string(expiry)
        }
      }

      body = Jason.encode!(envelope)

      if byte_size(body) <= 16_384,
        do: {:ok, body, Map.drop(envelope, ["spec", "deadline_ms"])},
        else: {:error, :invalid_request}
    else
      _ -> {:error, :invalid_request}
    end
  rescue
    _ -> {:error, :invalid_request}
  catch
    _, _ -> {:error, :invalid_request}
  end

  def encode(_, _, _), do: {:error, :invalid_request}

  def decode(raw, expected) when is_map(expected) do
    with {:ok, value} <- object(raw, 32_768),
         true <- exact?(value, Map.keys(expected) ++ ["observation"]),
         true <- Map.delete(value, "observation") === expected,
         {:ok, status} <- observation(value["observation"]),
         {:ok, worker_ref} <- decode_ref(value["ref"]) do
      {:ok,
       %Dispatch.Observation{operation_id: value["operation_id"], ref: worker_ref, status: status}}
    else
      {:dispatch_error, reason} -> {:error, reason}
      _ -> {:error, :uncertain}
    end
  rescue
    _ -> {:error, :uncertain}
  catch
    _, _ -> {:error, :uncertain}
  end

  def decode(_, _), do: {:error, :uncertain}

  def object(raw, limit) when is_binary(raw) and byte_size(raw) <= limit do
    with true <- String.valid?(raw),
         :ok <- lexical(raw, 0, 0, false, false, 0),
         {:ok, object} <- BoundedJSON.object(raw, limit),
         do: {:ok, object},
         else: (_ -> :error)
  end

  def object(_, _), do: :error

  # Lexical size/depth/token guards precede Jason; full syntax stays Jason's job.
  defp lexical(_, depth, tokens, _, _, size) when depth > 8 or tokens > 512 or size > 8_192,
    do: :error

  defp lexical(<<>>, 0, _, false, false, _), do: :ok
  defp lexical(<<>>, _, _, _, _, _), do: :error

  defp lexical(<<_, rest::binary>>, d, t, true, true, n),
    do: lexical(rest, d, t, true, false, n + 1)

  defp lexical(<<?\\, rest::binary>>, d, t, true, false, n),
    do: lexical(rest, d, t, true, true, n + 1)

  defp lexical(<<?", rest::binary>>, d, t, true, false, _),
    do: lexical(rest, d, t, false, false, 0)

  defp lexical(<<_, rest::binary>>, d, t, true, false, n),
    do: lexical(rest, d, t, true, false, n + 1)

  defp lexical(<<?", rest::binary>>, d, t, false, false, _),
    do: lexical(rest, d, t + 1, true, false, 0)

  defp lexical(<<c, rest::binary>>, d, t, false, false, _) when c in [?{, ?[],
    do: lexical(rest, d + 1, t + 1, false, false, 0)

  defp lexical(<<c, rest::binary>>, d, t, false, false, _) when c in [?}, ?]] and d > 0,
    do: lexical(rest, d - 1, t, false, false, 0)

  defp lexical(<<c, rest::binary>>, d, t, false, false, _) when c in [32, 9, 10, 13, ?:, ?,],
    do: lexical(rest, d, t, false, false, 0)

  defp lexical(<<_, rest::binary>>, d, t, false, false, _), do: scalar(rest, d, t + 1)

  defp scalar(<<c, _::binary>> = raw, d, t) when c in [32, 9, 10, 13, ?:, ?,, ?}, ?]],
    do: lexical(raw, d, t, false, false, 0)

  defp scalar(<<_, rest::binary>>, d, t), do: scalar(rest, d, t)
  defp scalar(<<>>, d, t), do: lexical(<<>>, d, t, false, false, 0)

  defp ref(%Lifecycle.WorkerRef{} = value) do
    value = Map.from_struct(value)

    if exact?(value, @ref) and scope?(value) and integer?(value.attempt, 1, 5) and
         integer?(value.fence, 1, @max), do: {:ok, value}, else: :error
  end

  defp ref(_), do: :error

  defp spec(%Lifecycle.Spec{} = value) do
    value = Map.from_struct(value)

    if exact?(value, @spec_keys) and scope?(value) and
         exact?(value.source, [:kind, :sha256, :reference]) and
         value.source.kind in [:revision, :upload] and hex?(value.source.sha256) and
         text?(value.source.reference, 1024) and
         hex?(value.toolchain_lock_sha256) and hex?(value.build_definition_sha256),
       do: {:ok, value},
       else: :error
  end

  defp spec(_), do: :error

  defp scope?(value),
    do:
      value.platform in [:ios, :android] and
        Enum.all?(@scope -- [:platform], &text?(value[&1], 128))

  defp stringify_ref(value),
    do:
      value
      |> Map.new(fn {k, v} -> {Atom.to_string(k), v} end)
      |> Map.put("platform", Atom.to_string(value.platform))
      |> Map.put("fence", Integer.to_string(value.fence))

  defp stringify_spec(value) do
    value
    |> Map.new(fn {k, v} -> {Atom.to_string(k), v} end)
    |> Map.put("platform", Atom.to_string(value.platform))
    |> Map.put("source", %{
      "kind" => Atom.to_string(value.source.kind),
      "sha256" => value.source.sha256,
      "reference" => value.source.reference
    })
  end

  defp operation_id(record_id, value),
    do:
      sha(
        Jason.encode!([
          "mixer-build-operation-v1",
          record_id,
          value.organization_id,
          value.project_id,
          value.application_id,
          value.build_id,
          Atom.to_string(value.platform),
          value.attempt,
          value.fence
        ])
      )

  defp decode_ref(value) do
    with true <- exact?(value, Enum.map(@ref, &Atom.to_string/1)),
         {:ok, fence} <- decimal(value["fence"], 1, @max),
         platform when platform in ["ios", "android"] <- value["platform"] do
      {:ok,
       struct!(Lifecycle.WorkerRef,
         organization_id: value["organization_id"],
         project_id: value["project_id"],
         application_id: value["application_id"],
         build_id: value["build_id"],
         platform: if(platform == "ios", do: :ios, else: :android),
         attempt: value["attempt"],
         fence: fence
       )}
    else
      _ -> :error
    end
  end

  defp observation(%{"status" => "absent"} = v),
    do: if(exact?(v, ["status"]), do: {:ok, :absent}, else: :error)

  defp observation(%{"status" => "running"} = v),
    do: if(exact?(v, ["status"]), do: {:ok, :running}, else: :error)

  defp observation(%{"status" => "stopped", "diagnostic_sha256" => hash} = v),
    do:
      if(exact?(v, ["status", "diagnostic_sha256"]) and hex?(hash),
        do: {:ok, {:stopped, hash}},
        else: :error
      )

  defp observation(%{"status" => "completed", "result" => result} = v) do
    with true <- exact?(v, ["status", "result"]),
         {:ok, result} <- result(result),
         do: {:ok, {:completed, result}},
         else: (_ -> :error)
  end

  defp observation(%{"status" => "error", "code" => code} = v) do
    if exact?(v, ["status", "code"]) do
      case code do
        "stale" -> {:dispatch_error, :stale}
        "unavailable" -> {:dispatch_error, :unavailable}
        "uncertain" -> {:dispatch_error, :uncertain}
        _ -> :error
      end
    else
      :error
    end
  end

  defp observation(_), do: :error

  defp result(%{"outcome" => "succeeded", "artifacts" => artifacts} = value)
       when is_list(artifacts) and length(artifacts) == 7 do
    with true <- exact?(value, ["outcome", "artifacts"]),
         converted = Enum.map(artifacts, &artifact/1),
         true <- Enum.all?(converted, &match?({:ok, _}, &1)),
         converted = Enum.map(converted, &elem(&1, 1)),
         true <- Enum.sort(Enum.map(converted, & &1.kind)) == Enum.sort(@kinds),
         true <-
           Enum.all?(Enum.group_by(converted, & &1.sha256), fn {_, refs} ->
             length(Enum.uniq(Enum.map(refs, & &1.size_bytes))) == 1
           end),
         do: {:ok, %{outcome: :succeeded, artifacts: converted}},
         else: (_ -> :error)
  end

  defp result(%{"outcome" => "failed"} = v) do
    with true <- exact?(v, ~w(outcome class code diagnostic_sha256)),
         {class, codes} <- Map.get(@failures, v["class"]),
         {:ok, code} <- Map.fetch(codes, v["code"]),
         true <- hex?(v["diagnostic_sha256"]),
         do:
           {:ok,
            %{
              outcome: :failed,
              class: class,
              code: code,
              diagnostic_sha256: v["diagnostic_sha256"]
            }},
         else: (_ -> :error)
  end

  defp result(_), do: :error

  defp artifact(v) do
    with true <- exact?(v, ~w(kind sha256 size_bytes)),
         {:ok, kind} <- Map.fetch(@kind_map, v["kind"]),
         true <- hex?(v["sha256"]),
         {:ok, size} <- decimal(v["size_bytes"], 1, @max),
         do: {:ok, %Lifecycle.ArtifactRef{kind: kind, sha256: v["sha256"], size_bytes: size}},
         else: (_ -> :error)
  end

  def decimal(v, min, max) when is_binary(v) and byte_size(v) in 1..19 do
    if Regex.match?(~r/\A(?:0|[1-9][0-9]*)\z/, v) do
      n = String.to_integer(v)
      if n >= min and n <= max, do: {:ok, n}, else: :error
    else
      :error
    end
  end

  def decimal(_, _, _), do: :error

  defp exact?(v, keys),
    do: is_map(v) and map_size(v) == length(keys) and Enum.all?(keys, &Map.has_key?(v, &1))

  defp integer?(n, min, max), do: is_integer(n) and n >= min and n <= max

  defp text?(v, max),
    do: is_binary(v) and byte_size(v) in 1..max and String.valid?(v) and String.printable?(v)

  defp hex?(v), do: is_binary(v) and byte_size(v) == 64 and Regex.match?(~r/\A[0-9a-f]{64}\z/, v)

  defp uuid?(v),
    do:
      is_binary(v) and
        Regex.match?(~r/\A[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\z/, v)

  defp sha(v), do: :crypto.hash(:sha256, v) |> Base.encode16(case: :lower)
end
