defmodule MixerHosted.CustomerBuilds.Snapshot do
  @moduledoc "Data-only journal projection; never an authorization capability."
  alias MixerHosted.CustomerBuilds.Selection
  alias MixerHosted.Builds.{Dispatch, Journal, Lifecycle}
  @scope ~w(organization_id project_id application_id build_id platform)a

  def project(record, selection, kind \\ nil) do
    with {:ok, s} <- Selection.new(selection),
         {:ok, build} <- restore(record, s),
         spec = build.spec,
         {:ok, status} <- Lifecycle.customer_status(build) do
      dto =
        %{
          organizationId: s.organization_id,
          projectId: s.project_id,
          applicationId: s.application_id,
          buildId: s.build_id,
          platform: s.platform,
          sourceSha256: spec.source.sha256,
          toolchainLockSha256: spec.toolchain_lock_sha256,
          buildDefinitionSha256: spec.build_definition_sha256,
          revision: record.revision,
          state: Atom.to_string(status.state),
          attempt: status.attempt,
          maxAttempts: status.max_attempts,
          failureCode: if(status.failure, do: Atom.to_string(status.failure.code), else: nil),
          workerCompletionPending: status.worker_completion_pending
        }

      result(dto, record, build, s, kind)
    else
      _ -> {:error, :storage_unavailable}
    end
  rescue
    _ -> {:error, :storage_unavailable}
  end

  @doc false
  def restore(record, %Selection{} = s) do
    with true <- is_map(record),
         true <- Map.take(record, @scope) == Map.take(s, @scope),
         {:ok, build} <- Journal.restore(record.journal),
         spec = build.spec,
         true <-
           Map.take(spec, @scope) |> Map.put(:platform, Atom.to_string(spec.platform)) ==
             Map.take(s, @scope),
         true <- build.request_key == record.request_key,
         true <- record.revision === length(record.journal["events"]),
         true <- spec.source.sha256 == s.source_sha256,
         true <- spec.toolchain_lock_sha256 == s.toolchain_lock_sha256,
         true <- spec.build_definition_sha256 == s.build_definition_sha256 do
      {:ok, build}
    else
      _ -> {:error, :storage_unavailable}
    end
  rescue
    _ -> {:error, :storage_unavailable}
  end

  defp result(dto, _, %{state: :native_succeeded, artifacts: artifacts}, selection, nil) do
    query = selection |> Map.from_struct() |> URI.encode_query()

    descriptors =
      Enum.map(artifacts, fn ref ->
        kind = Atom.to_string(ref.kind)

        %{
          kind: kind,
          sizeBytes: ref.size_bytes,
          sha256: ref.sha256,
          downloadPath: "/console-api/v1/build-artifacts/" <> kind <> "?" <> query
        }
      end)

    {:ok, Map.put(dto, :artifacts, descriptors)}
  end

  defp result(
         dto,
         record,
         %{state: :native_succeeded} = build,
         %Selection{platform: "ios"} = selection,
         :attestation_completion
       ) do
    with {:ok, operation} <- native_operation(record, build),
         {:ok, detail} <- result(dto, record, build, selection, nil) do
      {:ok, Map.put(detail, :workerOperationId, operation)}
    end
  end

  defp result(_, _, _, _, :attestation_completion), do: {:error, :not_found}

  defp result(dto, _, _, _, nil), do: {:ok, dto}

  defp result(dto, record, %{state: state} = build, _, :logs)
       when state in [:native_succeeded, :failed, :cancelled, :timed_out] do
    with {:ok, id} <- Ecto.UUID.cast(record.id),
         %{worker_ref: %Lifecycle.WorkerRef{} = ref} <-
           Enum.find(build.history, &(&1.attempt == build.attempt)) do
      {:ok, {:retained_logs, Dispatch.operation_id(id, ref), dto}}
    else
      _ -> {:error, :not_found}
    end
  end

  defp result(_, record, %{state: :native_succeeded} = build, _, kind) do
    with {:ok, operation} <- native_operation(record, build),
         %Lifecycle.ArtifactRef{} = artifact <-
           Enum.find(build.artifacts, &(Atom.to_string(&1.kind) == kind)) do
      {:ok, {:retained_native, operation, artifact}}
    else
      _ -> {:error, :not_found}
    end
  end

  defp result(_, _, _, _, _), do: {:error, :not_found}

  defp native_operation(record, build) do
    with {:ok, id} <- Ecto.UUID.cast(record.id),
         %{worker_ref: %Lifecycle.WorkerRef{} = ref} <-
           Enum.find(build.history, &(&1.attempt == build.attempt)) do
      {:ok, Dispatch.operation_id(id, ref)}
    else
      _ -> {:error, :not_found}
    end
  end
end
