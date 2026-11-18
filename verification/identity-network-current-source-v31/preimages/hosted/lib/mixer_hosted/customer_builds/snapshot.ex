defmodule MixerHosted.CustomerBuilds.Snapshot do
  @moduledoc "Data-only journal projection; never an authorization capability."
  alias MixerHosted.CustomerBuilds.Selection
  alias MixerHosted.Builds.{Journal, Lifecycle}
  @scope ~w(organization_id project_id application_id build_id platform)a

  def project(record, selection) do
    with {:ok, s} <- Selection.new(selection),
         true <- is_map(record),
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
         true <- spec.build_definition_sha256 == s.build_definition_sha256,
         {:ok, status} <- Lifecycle.customer_status(build) do
      {:ok,
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
       }}
    else
      _ -> {:error, :storage_unavailable}
    end
  rescue
    _ -> {:error, :storage_unavailable}
  end
end
