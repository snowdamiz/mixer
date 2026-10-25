defmodule MixerHosted.Authorization.ArtifactRead do
  @moduledoc false

  alias MixerHosted.Authorization.{Policy, Scope}
  alias MixerHosted.Authorization.Postgres.{Evidence, Session}
  alias MixerHosted.Authorization.Transaction.{Context, Snapshot}
  alias MixerHosted.CustomerArtifacts.PostgresStorage
  alias MixerHosted.Protocol.{ArtifactCBOR, ArtifactJSON, ArtifactV3Policy}

  @columns ~w(organization_id project_id application_id environment_id platform runtime_sha256 manifest_sha256 signed_manifest_bytes)
  @errors [
    :invalid_request,
    :unauthenticated,
    :not_found,
    :permission_denied,
    :authorization_unavailable,
    :conflict,
    :immutable_conflict,
    :idempotency_conflict,
    :storage_unavailable
  ]

  def run(identity, project_target, digest, callback, repo) do
    admitted_at = System.system_time(:second)
    deadline = System.monotonic_time(:millisecond) + 5_000

    with {:ok, project} <- Policy.metadata_request(identity, project_target, admitted_at),
         :ok <- valid_digest(digest),
         true <- is_function(callback, 2),
         false <- Context.active?(),
         false <- repo.in_transaction?() do
      lookup = %{
        identity: Policy.identity_key(identity),
        action: "artifact.read",
        target: project
      }

      result =
        repo.transaction(
          fn ->
            try do
              linkage = Session.prepare!(repo, lookup)

              Session.context!(repo,
                action: "artifact.read",
                token_issued_at: Integer.to_string(identity.issued_at),
                token_expires_at: Integer.to_string(identity.expires_at),
                required_scope: "mixer.artifact.read",
                phase: "metadata"
              )

              evidence = Evidence.load!(repo, lookup, linkage)
              now = current!(repo, admitted_at, deadline)
              evaluate_metadata!(repo, identity, project, evidence, now)
              PostgresStorage.check_topology!(repo)
              metadata = resolve!(repo, project, digest)

              # The project stage never binds a Context. Only the immutable
              # signed manifest may supply the actual app/environment target.
              target = metadata.target

              Session.context!(repo,
                application_id: target.application_id,
                environment_id: target.environment_id,
                phase: "effect"
              )

              lookup = %{lookup | target: target}
              evidence = Evidence.load!(repo, lookup, linkage)
              now = current!(repo, admitted_at, deadline, now)
              decision = evaluate!(repo, identity, target, evidence, now)
              snapshot = Snapshot.load!(repo, identity, evidence, linkage, decision, now)

              context =
                Context.bind!(
                  repo,
                  identity,
                  "artifact.read",
                  target,
                  evidence,
                  snapshot,
                  admitted_at,
                  deadline
                )

              Context.checkpoint!(context, repo, "artifact.read", target)

              case callback.(context, metadata) do
                {:ok, value} ->
                  Context.checkpoint!(context, repo, "artifact.read", target)
                  {:ok, value}

                {:error, reason} when reason in @errors ->
                  repo.rollback(reason)

                _ ->
                  repo.rollback(:authorization_unavailable)
              end
            after
              Context.clear!()
            end
          end,
          timeout: 5_000,
          queue: false
        )

      case result do
        {:ok, {:ok, value}} -> {:ok, value}
        {:error, reason} when reason in @errors -> {:error, reason}
        _ -> {:error, :authorization_unavailable}
      end
    else
      {:error, reason} when reason in @errors -> {:error, reason}
      _ -> {:error, :authorization_unavailable}
    end
  rescue
    _ -> {:error, :authorization_unavailable}
  catch
    _, _ -> {:error, :authorization_unavailable}
  end

  defp resolve!(repo, project, digest) do
    case Session.query!(repo, "SELECT * FROM public.mixer_customer_artifact_metadata($1)", [
           digest
         ]) do
      %{columns: @columns, rows: []} ->
        repo.rollback(:not_found)

      %{columns: @columns, rows: [row]} ->
        case decode_metadata(row, project, digest) do
          {:ok, metadata} -> metadata
          _ -> repo.rollback(:storage_unavailable)
        end

      _ ->
        repo.rollback(:storage_unavailable)
    end
  end

  @doc false
  def decode_metadata(
        [organization, project, application, environment, platform, runtime, digest, bytes],
        %Scope{organization_id: organization, project_id: project} = project_scope,
        digest
      )
      when is_binary(bytes) and byte_size(bytes) in 1..65_536 do
    with {:ok, ^project_scope} <- Scope.new(project_scope),
         true <- Scope.project_only?(project_scope),
         true <-
           Enum.all?([organization, project, application, environment], &ArtifactV3Policy.id?/1),
         true <- platform in ["ios", "android"],
         true <- ArtifactV3Policy.digest?(runtime) and ArtifactV3Policy.digest?(digest),
         {:ok, signed, _, _} <- ArtifactJSON.decode(bytes, 65_536),
         true <- ArtifactV3Policy.exact?(signed, ~w(manifest signature)),
         manifest = signed["manifest"],
         true <- ArtifactV3Policy.manifest?(manifest),
         true <- signature_shape?(signed["signature"]),
         true <-
           manifest["scope"] == %{
             "organization" => organization,
             "project" => project,
             "app" => application,
             "environment" => environment,
             "platform" => platform
           } and manifest["runtime"] == runtime,
         {:ok, cbor} <- ArtifactCBOR.encode(manifest),
         true <- hash(cbor) == digest do
      {:ok,
       %{
         target: %Scope{
           organization_id: organization,
           project_id: project,
           application_id: application,
           environment_id: environment
         },
         platform: platform,
         runtime_sha256: runtime,
         manifest_sha256: digest,
         signed_manifest_bytes: bytes,
         canonical_manifest_cbor: cbor,
         manifest: manifest
       }}
    else
      _ -> {:error, :storage_unavailable}
    end
  end

  def decode_metadata(_, _, _), do: {:error, :storage_unavailable}

  defp signature_shape?(text) when is_binary(text) and byte_size(text) == 88 do
    case Base.decode64(text, padding: true) do
      {:ok, decoded} when byte_size(decoded) == 64 -> Base.encode64(decoded) == text
      _ -> false
    end
  end

  defp signature_shape?(_), do: false

  defp valid_digest(digest),
    do: if(ArtifactV3Policy.digest?(digest), do: :ok, else: {:error, :invalid_request})

  defp hash(bytes), do: Base.encode16(:crypto.hash(:sha256, bytes), case: :lower)

  defp current!(repo, admitted_at, deadline, previous \\ 0) do
    now = System.system_time(:second)

    if now < admitted_at or now < previous or System.monotonic_time(:millisecond) >= deadline,
      do: repo.rollback(:authorization_unavailable)

    now
  end

  defp evaluate_metadata!(repo, identity, target, evidence, now) do
    case Policy.metadata_evaluate(identity, target, evidence, now) do
      {:ok, decision} -> decision
      {:error, reason} -> repo.rollback(reason)
    end
  end

  defp evaluate!(repo, identity, target, evidence, now) do
    case Policy.evaluate(identity, "artifact.read", target, evidence, now) do
      {:ok, decision} -> decision
      {:error, reason} -> repo.rollback(reason)
    end
  end
end
