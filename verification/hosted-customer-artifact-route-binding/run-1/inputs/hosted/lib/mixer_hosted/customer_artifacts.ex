defmodule MixerHosted.CustomerArtifacts do
  @moduledoc """
  Customer artifact operations composed inside owned authorization transactions.

  The caller supplies a previously verified identity, a closed organization/project
  route, and bounded request data. Request data never chooses a Repo, trust root,
  host policy, callback, clock, actor, or audit request ID. The transaction creates
  its own request ID and success is returned only after its commit succeeds.

  Trusted application configuration under this module is exactly
  `%{repo: repo_module, host: host_policy, roots: public_roots}`. This initial
  composition serves one configured host policy; a tenant trust registry and its
  mutation protocol remain separate work. Missing configuration fails closed.
  This module does not activate an HTTP route or publish an artifact.
  """

  alias MixerHosted.Authorization
  alias MixerHosted.Authorization.{Policy, Scope}
  alias MixerHosted.CustomerArtifacts.PostgresStorage
  alias MixerHosted.Protocol.{ArtifactAdmission, ArtifactV3Policy}

  @maximum 9_007_199_254_740_991

  def upload(identity, route_tenant, key, envelope, request_metadata) do
    upload_expected(identity, route_tenant, key, envelope, request_metadata, :any)
  end

  @doc "Uploads only when the signed manifest digest matches the route before any storage effect."
  def upload_at(identity, route_tenant, expected_digest, key, envelope, request_metadata) do
    upload_expected(
      identity,
      route_tenant,
      key,
      envelope,
      request_metadata,
      {:at, expected_digest}
    )
  end

  defp upload_expected(identity, route_tenant, key, envelope, request_metadata, expected) do
    with {:ok, project} <- project(route_tenant),
         :ok <- expected_digest(expected),
         {:ok, config} <- configuration(),
         target = host_target(config.host),
         {:ok, ^target} <- Policy.request(identity, "artifact.upload", target, now()),
         :ok <- required_scope(identity, "mixer.artifact.upload"),
         :ok <- same_project(project, target),
         :ok <- metadata(request_metadata),
         :ok <- idempotency_key(key),
         {:ok, checked} <- admit(envelope, config, expected),
         :ok <- matching_digest(expected, checked.manifest_sha256) do
      command = Map.put(request_metadata, :key, key)

      Authorization.with_authorized_transaction(
        identity,
        "artifact.upload",
        target,
        fn context -> PostgresStorage.upload(context, checked, command, config) end,
        config.repo
      )
    end
  end

  def read(identity, route_tenant, manifest_sha256, request_metadata) do
    with {:ok, project} <- project(route_tenant),
         {:ok, ^project} <- Policy.metadata_request(identity, project, now()),
         :ok <- metadata(request_metadata),
         :ok <- manifest_digest(manifest_sha256),
         {:ok, config} <- configuration(),
         :ok <- same_project(project, host_target(config.host)) do
      Authorization.with_artifact_read_transaction(
        identity,
        project,
        manifest_sha256,
        fn context, resolved ->
          if resolved.target == host_target(config.host) and
               resolved.platform == config.host["scope"]["platform"] and
               resolved.runtime_sha256 == config.host["runtime"] and
               resolved.manifest_sha256 == manifest_sha256 do
            PostgresStorage.read(context, manifest_sha256, config)
          else
            {:error, :storage_unavailable}
          end
        end,
        config.repo
      )
    end
  end

  def audit(identity, route_tenant, after_sequence, limit, request_metadata) do
    with {:ok, project} <- project(route_tenant),
         {:ok, ^project} <- Policy.request(identity, "audit.read", project, now()),
         :ok <- required_scope(identity, "mixer.audit.read"),
         :ok <- metadata(request_metadata),
         :ok <- page(after_sequence, limit),
         {:ok, config} <- configuration(),
         :ok <- same_project(project, host_target(config.host)) do
      Authorization.with_authorized_transaction(
        identity,
        "audit.read",
        project,
        fn context -> PostgresStorage.audit(context, after_sequence, limit, config) end,
        config.repo
      )
    end
  end

  defp configuration do
    with {:ok, config} <- Application.fetch_env(:mixer_hosted, __MODULE__),
         true <- exact?(config, [:repo, :host, :roots]),
         true <- is_atom(config.repo) and config.repo not in [nil, true, false],
         true <- Code.ensure_loaded?(config.repo),
         true <-
           Enum.all?([transaction: 2, rollback: 1, in_transaction?: 0], fn {f, a} ->
             function_exported?(config.repo, f, a)
           end),
         true <- ArtifactV3Policy.host?(config.host),
         true <- ArtifactV3Policy.roots?(config.roots) do
      {:ok, config}
    else
      _ -> {:error, :storage_unavailable}
    end
  end

  defp project(route) do
    if exact?(route, [:organization_id, :project_id]) do
      case Scope.new(route) do
        {:ok, %Scope{project_id: project} = scope} when is_binary(project) -> {:ok, scope}
        _ -> {:error, :invalid_request}
      end
    else
      {:error, :invalid_request}
    end
  end

  defp host_target(host) do
    scope = host["scope"]

    %Scope{
      organization_id: scope["organization"],
      project_id: scope["project"],
      application_id: scope["app"],
      environment_id: scope["environment"]
    }
  end

  defp same_project(project, target) do
    if project.organization_id == target.organization_id and
         project.project_id == target.project_id,
       do: :ok,
       else: {:error, :not_found}
  end

  defp metadata(value) do
    if exact?(value, [:reason, :source_ip]) and is_binary(value.reason) and
         byte_size(value.reason) <= 512 and String.valid?(value.reason) and
         canonical_ip?(value.source_ip),
       do: :ok,
       else: {:error, :invalid_request}
  end

  defp canonical_ip?(nil), do: true

  defp canonical_ip?(value) when is_binary(value) and byte_size(value) in 1..45 do
    if String.valid?(value) do
      case :inet.parse_address(String.to_charlist(value)) do
        {:ok, address} -> to_string(:inet.ntoa(address)) == value
        _ -> false
      end
    else
      false
    end
  end

  defp canonical_ip?(_), do: false

  defp idempotency_key(key) when is_binary(key) and byte_size(key) in 1..128 do
    if Enum.all?(:binary.bin_to_list(key), fn c ->
         c in ?A..?Z or c in ?a..?z or c in ?0..?9 or c in [?_, ?., ?:, ?-]
       end),
       do: :ok,
       else: {:error, :invalid_request}
  end

  defp idempotency_key(_), do: {:error, :invalid_request}

  defp manifest_digest(value),
    do: if(ArtifactV3Policy.digest?(value), do: :ok, else: {:error, :invalid_request})

  defp expected_digest(:any), do: :ok
  defp expected_digest({:at, value}), do: manifest_digest(value)
  defp matching_digest(:any, _actual), do: :ok
  defp matching_digest({:at, expected}, expected), do: :ok
  defp matching_digest({:at, _expected}, _actual), do: {:error, :digest_mismatch}

  defp page(after_sequence, limit)
       when is_integer(after_sequence) and after_sequence in 0..@maximum and
              is_integer(limit) and limit in 1..100,
       do: :ok

  defp page(_, _), do: {:error, :invalid_request}

  defp required_scope(identity, scope),
    do: if(scope in identity.scopes, do: :ok, else: {:error, :permission_denied})

  defp admit(envelope, config, expected) do
    case ArtifactAdmission.admit(envelope, config.host, config.roots, now()) do
      {:ok, checked} -> {:ok, checked}
      _ when expected == :any -> {:error, :invalid_request}
      _ -> {:error, :artifact_invalid}
    end
  end

  defp exact?(map, keys),
    do:
      is_map(map) and not is_struct(map) and map_size(map) == length(keys) and
        Enum.all?(keys, &Map.has_key?(map, &1))

  defp now, do: System.system_time(:second)
end
