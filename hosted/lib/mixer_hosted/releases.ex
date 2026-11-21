defmodule MixerHosted.Releases do
  @moduledoc """
  Local v3 publication ledger and opt-in environment promotion.

  Publication entry points verify the retained signed bytes inside a
  fresh authorization transaction with the provisioned head locked.
  """

  import Ecto.Query, only: [from: 2]
  alias Ecto.Changeset
  alias MixerHosted.Authorization
  alias MixerHosted.Authorization.Postgres.Session
  alias MixerHosted.Authorization.Transaction.Context
  alias MixerHosted.Identity.{Encoding, VerifiedIdentity}
  alias MixerHosted.Protocol.{ArtifactAdmission, ArtifactV3Policy, AssignmentV3}

  alias MixerHosted.Releases.{
    CLIRequest,
    Head,
    Publication,
    ReleaseJobs,
    Target,
    WriterCatalog,
    WriterRepo
  }

  alias MixerHosted.Releases.EnvironmentPromotion.{Command, Direction, Storage, Verifier}
  alias MixerHosted.Releases.EnvironmentPromotion.Command.Evidence
  alias MixerHosted.Releases.EnvironmentPromotion.Direction.Enrollment

  @action "release.publish"
  @stage_platforms [:android, :ios]
  @value_fields [:artifact_sha256, :signed_assignment_bytes, :rollout_basis_points]

  @type result :: %{
          sequence: pos_integer(),
          previous_sequence: pos_integer() | nil,
          artifact_sha256: String.t(),
          signed_assignment_bytes: binary(),
          rollout_basis_points: 0..10_000
        }

  @type signed_command :: {:signed, Target.t(), binary(), (module() -> :ok)}

  @spec publish(
          VerifiedIdentity.t(),
          signed_command(),
          String.t(),
          String.t(),
          module()
        ) ::
          {:ok, result()} | {:error, atom()}
  def publish(identity, command, key, reason, repo \\ MixerHosted.Repo)

  # The internal browser caller supplies the retained session check. The actual
  # host, channel and roots come from explicit trusted server provisioning.
  def publish(identity, {:signed, %Target{} = target, bytes, current!}, key, reason, repo)
      when is_binary(bytes) and is_function(current!, 1) do
    with {:ok, ^target} <- Target.new(target),
         true <- valid_metadata?(key, reason),
         {:ok, signed} <- AssignmentV3.decode_signed(bytes),
         {:ok, config} <- configured_target(target) do
      Authorization.with_authorized_transaction(
        identity,
        @action,
        target.scope,
        fn context ->
          publish_signed!(context, repo, target, signed, config, current!, key, reason)
        end,
        repo
      )
    else
      {:error, reason} = error when reason in [:not_found, :authorization_unavailable] -> error
      _ -> {:error, :invalid_request}
    end
  end

  def publish(_, _, _, _, _), do: {:error, :invalid_request}

  @doc """
  Promotes two committed source publications through an operator-provisioned direction.

  The selector contains one source sequence per platform. Destination evidence
  must match the exact bytes of each already staged destination artifact. The
  direction (including hosts and roots) comes from
  `:local_stage_promotion_directions` and must match the enabled SQL route.
  """
  def promote_environment(
        identity,
        direction_id,
        source_sequences,
        destination,
        key,
        reason,
        repo \\ WriterRepo
      ) do
    with true <- ArtifactV3Policy.id?(direction_id) and valid_metadata?(key, reason),
         true <- stage_sequences?(source_sequences) and stage_evidence?(destination),
         {:ok, direction} <- stage_direction(direction_id) do
      scope = direction.destination.ios.target.scope

      request = %{
        id: direction_id,
        source: source_sequences,
        destination: destination,
        key: key,
        reason: reason
      }

      Authorization.with_authorized_transaction(
        identity,
        @action,
        scope,
        &stage_locked(&1, repo, direction, request),
        repo
      )
    else
      false -> {:error, :invalid_request}
      {:error, _} = error -> error
    end
  end

  defp stage_sequences?(%{ios: ios, android: android} = sequences) when map_size(sequences) == 2,
    do: Enum.all?([ios, android], &(ArtifactV3Policy.uint?(&1) and &1 > 0))

  defp stage_sequences?(_), do: false

  defp stage_evidence?(%{ios: %Evidence{}, android: %Evidence{}} = evidence)
       when map_size(evidence) == 2,
       do: true

  defp stage_evidence?(_), do: false

  defp stage_direction(id) do
    configured = Application.get_env(:mixer_hosted, :local_stage_promotion_directions, %{})

    with %{^id => %Direction{source: source, destination: destination} = direction} <- configured,
         {:ok, source_scope} <- stage_target_pair(source),
         {:ok, dest_scope} <- stage_target_pair(destination),
         true <- source_scope.environment_id != dest_scope.environment_id,
         true <- %{source_scope | environment_id: dest_scope.environment_id} === dest_scope do
      {:ok, direction}
    else
      _ -> {:error, :invalid_promotion}
    end
  end

  defp stage_target_pair(
         %{
           ios: %Enrollment{target: %Target{platform: "ios", scope: scope} = ios},
           android: %Enrollment{target: %Target{platform: "android", scope: scope} = android}
         } = pair
       )
       when map_size(pair) == 2 do
    with {:ok, ^ios} <- Target.new(ios), {:ok, ^android} <- Target.new(android), do: {:ok, scope}
  end

  defp stage_target_pair(_), do: :error

  defp stage_locked(context, repo, direction, request) do
    check_writer!(repo)
    Storage.check!(repo)

    # Both targets share the bound Scope. Their primary keys differ first by
    # platform, so Android then iOS is a consistent lock order for every route.
    destinations =
      Map.new(@stage_platforms, fn platform ->
        target = direction.destination[platform].target
        filter = Target.filter(target)
        head = repo.one(from(h in Head, where: ^filter, lock: "FOR UPDATE"))
        {platform, %{target: target, filter: filter, head: head}}
      end)

    scope = direction.destination.ios.target.scope
    fresh = Context.checkpoint!(context, repo, @action, scope)
    principal = fresh.principal.id
    WriterCatalog.check_artifact!(repo)

    with true <- Enum.all?(destinations, fn {_, destination} -> destination.head != nil end),
         {:ok, ^direction} <- stage_direction(request.id),
         {:ok, route} <- Storage.admit(repo, request.id, direction),
         {:ok, source} <- Storage.source(repo, request.id, request.source),
         command = %Command{source: source, destination: request.destination},
         binding = Storage.binding(repo, request.id, request.key),
         sequences = stage_previous_sequences(destinations, binding),
         {:ok, verified} <- stage_verify(command, direction, sequences, fresh.checked_at),
         :ok <- stage_destination_artifacts(repo, verified),
         fingerprint = stage_fingerprint(route, command, principal, request),
         metadata = %{
           key: request.key,
           reason: request.reason,
           principal: principal,
           fingerprint: fingerprint
         },
         {:ok, rows} <-
           stage_write(repo, destinations, route, verified, fresh, binding, metadata),
         {:ok, ^direction} <- stage_direction(request.id),
         {:ok, ^route} <- Storage.admit(repo, request.id, direction),
         now = Context.checkpoint!(context, repo, @action, scope).checked_at,
         :ok <- stage_reverify(command, direction, sequences, fresh.checked_at, now) do
      {:ok, %{ios: result(rows.ios), android: result(rows.android)}}
    else
      false -> {:error, :release_not_found}
      {:ok, _} -> {:error, :authorization_unavailable}
      {:error, _} = error -> error
    end
  end

  defp stage_previous_sequences(destinations, nil) do
    Map.new(destinations, fn {platform, %{head: head}} ->
      {platform, if(head.sequence, do: Decimal.to_integer(head.sequence), else: 0)}
    end)
  end

  # A receipt identifies completed appends. The current head is irrelevant to
  # the signed sequences on replay, but current trust and authority still apply.
  defp stage_previous_sequences(_, _binding), do: %{ios: 0, android: 0}

  defp stage_verify(command, direction, sequences, now) do
    case Verifier.verify(command, direction, %{now: now, destination_last_sequences: sequences}) do
      {:ok, _} = verified -> verified
      {:error, {_, :destination, :assignment_replay}} -> {:error, :conflict}
      {:error, _} -> {:error, :assignment_rejected}
    end
  end

  defp stage_reverify(_, _, _, now, now), do: :ok

  defp stage_reverify(command, direction, sequences, _, now) do
    with {:ok, _} <- stage_verify(command, direction, sequences, now), do: :ok
  end

  defp stage_destination_artifacts(repo, verified) do
    Enum.reduce_while(@stage_platforms, :ok, fn platform, :ok ->
      %{target: target, evidence: evidence, assignment: signed} = verified[platform].destination

      case stored_artifact(repo, target, signed.assignment["artifact_sha256"]) do
        {:ok, %{signed_manifest_bytes: manifest, payload: payload}}
        when manifest === evidence.signed_manifest_bytes and payload === evidence.payload ->
          {:cont, :ok}

        {:ok, _} ->
          {:halt, {:error, :artifact_invalid}}

        {:error, _} = error ->
          {:halt, error}
      end
    end)
  end

  defp stage_fingerprint(route, command, principal, request) do
    evidence =
      Enum.flat_map(@stage_platforms, fn platform ->
        source = command.source[platform]

        [Integer.to_string(source.sequence), source.artifact_sha256] ++
          stage_evidence_bytes(source.evidence) ++
          stage_evidence_bytes(command.destination[platform])
      end)

    # Length framing retains the original JSON spelling and raw payload without
    # tying persisted retries to a runtime-specific serialization format.
    fields =
      ["mixer.stage-promotion.v1" | route] ++ [principal, request.key, request.reason] ++ evidence

    fields |> Enum.map(fn bytes -> [<<byte_size(bytes)::64>>, bytes] end) |> Storage.sha256()
  end

  defp stage_evidence_bytes(evidence),
    do: [evidence.signed_manifest_bytes, evidence.signed_assignment_bytes, evidence.payload]

  defp stage_write(
         repo,
         destinations,
         _route,
         _verified,
         _fresh,
         %{fingerprint: fingerprint, principal: principal, sequences: sequences},
         %{fingerprint: fingerprint, principal: principal}
       ) do
    rows =
      Map.new(destinations, fn {platform, %{filter: filter}} ->
        {platform, Storage.publication(repo, filter, sequences[platform])}
      end)

    {:ok, rows}
  end

  defp stage_write(repo, destinations, route, verified, fresh, nil, metadata) do
    with :ok <- stage_keys_available(repo, destinations, metadata.key),
         {:ok, android} <-
           stage_append(repo, destinations.android, verified.android, fresh, metadata),
         {:ok, ios} <- stage_append(repo, destinations.ios, verified.ios, fresh, metadata),
         :ok <- Storage.insert!(repo, route, verified, metadata) do
      {:ok, %{ios: ios, android: android}}
    end
  end

  defp stage_write(_, _, _, _, _, _, _), do: {:error, :idempotency_conflict}

  defp stage_keys_available(repo, destinations, key) do
    Enum.reduce_while(@stage_platforms, :ok, fn platform, :ok ->
      filter = destinations[platform].filter
      by_key = [{:idempotency_key, key} | filter]

      with :ok <- browser_key_available(repo, filter, key),
           false <- repo.exists?(from(p in Publication, where: ^by_key)) do
        {:cont, :ok}
      else
        _ -> {:halt, {:error, :idempotency_conflict}}
      end
    end)
  end

  defp stage_append(repo, %{head: head, filter: filter}, verified, fresh, metadata) do
    values =
      publication_values(
        verified.destination.assignment,
        fresh,
        metadata.key,
        metadata.reason,
        :stage_promote,
        nil
      )

    append(repo, head, Map.new(filter), values)
  end

  @doc false
  def cli(identity, {org, project, channel}, command, key, request_hash, reason) do
    with true <- Process.whereis(WriterRepo) != nil,
         {:ok, %{target: %Target{} = target}} <-
           Application.fetch_env(:mixer_hosted, :local_release_target),
         {:ok, ^target} <- Target.new(target),
         :ok <- cli_route(target, org, project, channel),
         true <- valid_metadata?(key, reason) and ArtifactV3Policy.digest?(request_hash),
         {:ok, config} <- configured_target(target) do
      Authorization.with_authorized_transaction(
        identity,
        @action,
        target.scope,
        fn context ->
          cli_locked(context, target, config, command, key, request_hash, reason)
        end,
        WriterRepo
      )
      |> case do
        {:error, :not_found} -> {:error, :scope_denied}
        result -> result
      end
    else
      :error -> {:error, :release_not_found}
      false -> {:error, :release_not_found}
      {:error, _} = error -> error
      _ -> {:error, :authorization_unavailable}
    end
  end

  defp cli_route(target, org, project, channel) do
    cond do
      {org, project} != {target.scope.organization_id, target.scope.project_id} ->
        {:error, :scope_denied}

      channel != nil and channel != target.channel ->
        {:error, :release_not_found}

      true ->
        :ok
    end
  end

  defp cli_locked(context, target, config, command, key, hash, reason) do
    repo = WriterRepo
    check_writer!(repo)
    filter = Target.filter(target)
    head = repo.one(from(h in Head, where: ^filter, lock: "FOR UPDATE"))
    fresh = Context.checkpoint!(context, repo, @action, target.scope)
    {:ok, ^config} = configured_target(target)
    WriterCatalog.check_receipts!(repo)
    WriterCatalog.check_artifact!(repo)
    by_key = [{:idempotency_key, key} | filter]
    principal = fresh.principal.id

    result =
      cond do
        head == nil ->
          {:error, :release_not_found}

        receipt = repo.get_by(CLIRequest, by_key) ->
          cli_replay(receipt, hash, principal, command, {target, config, filter}, context)

        repo.exists?(from(p in Publication, where: ^by_key)) ->
          {:error, :idempotency_conflict}

        true ->
          with {:ok, result, verify_at} <-
                 cli_new(command, head, filter, target, config, fresh, key, reason) do
            fields = %{
              idempotency_key: key,
              request_sha256: hash,
              principal_id: principal,
              artifact_sha256: result.artifact_sha256,
              publication_sequence: result[:sequence] && Decimal.new(result.sequence)
            }

            repo.insert!(struct!(CLIRequest, Map.merge(Map.new(filter), fields)))

            with :ok <- cli_verify_at_checkpoint(context, target, fresh.checked_at, verify_at),
                 do: {:ok, result}
          end
      end

    {:ok, ^config} = configured_target(target)
    result
  end

  defp cli_replay(
         %CLIRequest{request_sha256: hash, principal_id: principal} = receipt,
         hash,
         principal,
         command,
         {target, config, filter},
         context
       ) do
    case {command, receipt.publication_sequence} do
      {{:validate, digest}, nil} when digest == receipt.artifact_sha256 ->
        {:ok, %{artifact_sha256: digest}}

      {{action, bytes, health}, %Decimal{} = sequence} ->
        row =
          WriterRepo.one!(
            replay_publication(
              action,
              [
                sequence: sequence,
                artifact_sha256: receipt.artifact_sha256,
                idempotency_key: receipt.idempotency_key,
                principal_id: principal
              ] ++ filter
            )
          )

        with true <- row.action == Atom.to_string(action) and row.signed_assignment_bytes == bytes,
             true <- action != :halt or health == Publication.health(row),
             {:ok, artifact} <- cli_artifact(target, row.artifact_sha256, :not_validated),
             :ok <- check_replay_signature(action, row, artifact, config, target, context) do
          {:ok, cli_result(row, target)}
        else
          false -> {:error, :idempotency_conflict}
          {:error, _} = error -> error
        end

      _ ->
        {:error, :idempotency_conflict}
    end
  end

  defp cli_replay(_, _, _, _, _, _), do: {:error, :idempotency_conflict}

  defp replay_publication(:halt, filter) do
    from(p in Publication,
      where: ^filter,
      select_merge: %{
        health_activated: p.health_activated,
        health_pending: p.health_pending,
        health_adverse_signals: p.health_adverse_signals
      }
    )
  end

  defp replay_publication(_, filter), do: from(p in Publication, where: ^filter)

  defp check_replay_signature(action, row, artifact, config, target, context) do
    # The receipt identifies a committed assignment. Its retry does not advance the head.
    last = if action == :halt, do: Decimal.to_integer(row.previous_sequence), else: 0

    verify_at = fn now ->
      verify_cli_assignment(
        action,
        row.signed_assignment_bytes,
        artifact,
        config,
        target.channel,
        last,
        now
      )
    end

    %{checked_at: now} = Context.checkpoint!(context, WriterRepo, @action, target.scope)
    {:ok, ^config} = configured_target(target)

    with :ok <- verify_at.(now), do: cli_verify_at_checkpoint(context, target, now, verify_at)
  end

  defp cli_verify_at_checkpoint(context, target, checked_at, verify_at) do
    now = Context.checkpoint!(context, WriterRepo, @action, target.scope).checked_at
    if now == checked_at, do: :ok, else: verify_at.(now)
  end

  defp cli_new({:validate, digest}, _head, _filter, target, config, fresh, _key, _reason) do
    with {:ok, artifact} <- cli_artifact(target, digest, :release_not_found) do
      verify_at = fn now -> validate_artifact(artifact, config, digest, now) end

      with :ok <- verify_at.(fresh.checked_at) do
        {:ok, %{artifact_sha256: digest}, verify_at}
      end
    end
  end

  defp cli_new({action, bytes, health}, head, filter, target, config, fresh, key, reason)
       when action in [:publish, :promote, :rollback, :halt] do
    with {:ok, signed} <- cli_decode_assignment(bytes),
         :ok <- cli_assignment(target, signed.assignment),
         {:ok, artifact} <- cli_candidate(action, target, head, filter, signed.assignment, health),
         last = if(head.sequence, do: Decimal.to_integer(head.sequence), else: 0),
         verify_at = fn now ->
           verify_cli_assignment(action, bytes, artifact, config, target.channel, last, now)
         end,
         :ok <- verify_at.(fresh.checked_at),
         :ok <- cli_transition(action, head, filter, signed.assignment),
         {:ok, stored} <-
           append(
             WriterRepo,
             head,
             Map.new(filter),
             publication_values(signed, fresh, key, reason, action, health)
           ) do
      {:ok, cli_result(stored, target), verify_at}
    end
  end

  defp cli_candidate(:halt, target, head, filter, assignment, health) do
    digest = assignment["artifact_sha256"]

    cond do
      assignment["channel"] != target.channel or assignment["rollout_basis_points"] != 0 ->
        {:error, :invalid_halt}

      is_nil(head.sequence) or not Decimal.equal?(head.sequence, health["sequence"]) ->
        {:error, :stale_rollout}

      WriterRepo.exists?(
        from(p in Publication,
          where: ^filter,
          where: p.sequence == ^head.sequence and p.artifact_sha256 == ^digest,
          where: p.rollout_basis_points > 0
        )
      ) ->
        cli_artifact(target, digest, :stale_rollout)

      true ->
        {:error, :stale_rollout}
    end
  end

  defp cli_candidate(_, target, _head, filter, %{"artifact_sha256" => digest}, nil) do
    if WriterRepo.exists?(
         from(r in CLIRequest,
           where: ^filter,
           where: r.artifact_sha256 == ^digest and is_nil(r.publication_sequence)
         )
       ),
       do: cli_artifact(target, digest, :not_validated),
       else: {:error, :not_validated}
  end

  defp cli_transition(action, _head, _filter, _assignment) when action in [:publish, :halt],
    do: :ok

  defp cli_transition(:promote, head, filter, assignment) do
    digest = assignment["artifact_sha256"]
    rollout = assignment["rollout_basis_points"]

    if head.sequence &&
         WriterRepo.exists?(
           from(p in Publication,
             where: ^filter,
             where: p.sequence == ^head.sequence and p.artifact_sha256 == ^digest,
             where: p.rollout_basis_points < ^rollout
           )
         ),
       do: :ok,
       else: {:error, :invalid_promotion}
  end

  defp cli_transition(:rollback, head, filter, assignment) do
    digest = assignment["artifact_sha256"]

    if head.sequence &&
         WriterRepo.exists?(
           from(p in Publication,
             where: ^filter,
             where: p.sequence <= ^head.sequence and p.artifact_sha256 == ^digest
           )
         ),
       do: :ok,
       else: {:error, :invalid_rollback}
  end

  defp cli_decode_assignment(bytes) do
    case AssignmentV3.decode_signed(bytes) do
      {:ok, _} = signed -> signed
      {:error, _} -> {:error, :assignment_rejected}
    end
  end

  defp validate_artifact(artifact, config, digest, now) do
    case ArtifactAdmission.admit_signed(
           artifact.signed_manifest_bytes,
           artifact.payload,
           config.host,
           config.roots,
           now
         ) do
      {:ok, %{manifest_sha256: ^digest}} -> :ok
      _ -> {:error, :artifact_invalid}
    end
  end

  defp verify_cli_assignment(action, bytes, artifact, config, channel, last, now) do
    verify = if action == :halt, do: &AssignmentV3.verify_halt/5, else: &AssignmentV3.verify/5

    case verify.(bytes, artifact, config.roots, config.host, %{
           channel: channel,
           last_sequence: last,
           now: now
         }) do
      {:ok, _signed} ->
        :ok

      {:error, reason} when reason in [:artifact_rejected, :document_or_payload_limit] ->
        {:error, :artifact_invalid}

      {:error, _} ->
        {:error, :assignment_rejected}
    end
  end

  defp cli_assignment(target, assignment) do
    cond do
      assignment["scope"] != Target.signed_scope(target) -> {:error, :scope_denied}
      assignment["runtime"] != target.runtime_sha256 -> {:error, :unknown_runtime}
      true -> :ok
    end
  end

  defp cli_artifact(target, digest, missing) do
    case stored_artifact(WriterRepo, target, digest) do
      {:error, :not_found} -> {:error, missing}
      result -> result
    end
  end

  defp publication_values(signed, fresh, key, reason, action, health) do
    values = %{
      sequence: Decimal.new(signed.assignment["sequence"]),
      idempotency_key: key,
      reason: reason,
      principal_id: fresh.principal.id,
      artifact_sha256: signed.assignment["artifact_sha256"],
      signed_assignment_bytes: signed.signed_assignment_bytes,
      rollout_basis_points: signed.assignment["rollout_basis_points"]
    }

    case action do
      :publish ->
        values

      :halt ->
        Enum.reduce(
          Publication.health_fields(),
          Map.put(values, :action, "halt"),
          fn {field, key}, acc -> Map.put(acc, field, Decimal.new(Map.fetch!(health, key))) end
        )

      _ ->
        Map.put(values, :action, Atom.to_string(action))
    end
  end

  defp publish_signed!(context, repo, target, signed, config, current!, key, reason) do
    check_writer!(repo)
    filter = Target.filter(target)

    with %Head{} = head <- repo.one(from(h in Head, where: ^filter, lock: "FOR UPDATE")),
         {:ok, artifact} <- stored_artifact(repo, target, signed.assignment["artifact_sha256"]) do
      stored = repo.get_by(Publication, [{:idempotency_key, key} | filter])
      last = if is_nil(stored) and head.sequence, do: Decimal.to_integer(head.sequence), else: 0
      :ok = current!.(repo)
      fresh = Context.checkpoint!(context, repo, @action, target.scope)
      {:ok, ^config} = configured_target(target)

      with :ok <- browser_key_available(repo, filter, key),
           {:ok, signed} <- verify(signed, artifact, config, target, last, fresh.checked_at) do
        values = publication_values(signed, fresh, key, reason, :publish, nil)

        result =
          if stored,
            do: replay(stored, values),
            else: append(repo, head, Map.new(filter), values)

        with {:ok, stored} <- result do
          {:ok, ^config} = configured_target(target)
          now = Context.checkpoint!(context, repo, @action, target.scope).checked_at

          if now != fresh.checked_at,
            do: {:ok, ^signed} = verify(signed, artifact, config, target, last, now)

          :ok = current!.(repo)
          {:ok, result(stored)}
        end
      end
    else
      nil -> {:error, :not_found}
      error -> error
    end
  end

  defp browser_key_available(repo, filter, key) do
    if WriterCatalog.receipts_installed?(repo) do
      WriterCatalog.check_receipts!(repo)
      by_key = [{:idempotency_key, key} | filter]

      if repo.exists?(from(r in CLIRequest, where: ^by_key)),
        do: {:error, :idempotency_conflict},
        else: :ok
    else
      :ok
    end
  end

  defp configured_target(target) do
    case Application.fetch_env(:mixer_hosted, :local_release_target) do
      {:ok, %{target: ^target, host: host, roots: roots} = config} when map_size(config) == 3 ->
        if ArtifactV3Policy.host?(host) and host["scope"] == Target.signed_scope(target) and
             host["runtime"] == target.runtime_sha256 and ArtifactV3Policy.roots?(roots),
           do: {:ok, config},
           else: {:error, :authorization_unavailable}

      _ ->
        {:error, :not_found}
    end
  end

  defp stored_artifact(repo, target, digest) do
    %Target{scope: scope, platform: platform, runtime_sha256: runtime} = target

    case Session.query!(
           repo,
           """
           SELECT signed_manifest_bytes,payload,payload_sha256
           FROM public.mixer_release_bound_artifact($1,$2,$3,$4,$5,$6,$7,$8)
           """,
           [
             scope.organization_id,
             scope.project_id,
             scope.application_id,
             scope.environment_id,
             platform,
             runtime,
             target.channel,
             digest
           ]
         ).rows do
      [[manifest, payload, payload_digest]] ->
        if Base.encode16(:crypto.hash(:sha256, payload), case: :lower) == payload_digest do
          {:ok, %{signed_manifest_bytes: manifest, payload: payload}}
        else
          {:error, :storage_unavailable}
        end

      [] ->
        {:error, :not_found}
    end
  end

  defp verify(signed, artifact, config, target, last, now) do
    context = %{channel: target.channel, last_sequence: last, now: now}

    case AssignmentV3.verify(
           signed.signed_assignment_bytes,
           artifact,
           config.roots,
           config.host,
           context
         ) do
      {:ok, ^signed} = verified -> verified
      {:error, :assignment_replay} -> {:error, :conflict}
      {:error, :root_policy} -> {:error, :permission_denied}
      {:error, _} -> {:error, :invalid_request}
    end
  end

  defp append(repo, head, target, values) do
    if is_nil(head.sequence) or Decimal.gt?(values.sequence, head.sequence) do
      row =
        struct!(
          Publication,
          Map.merge(target, Map.put(values, :previous_sequence, head.sequence))
        )

      changeset =
        row
        |> Changeset.change()
        |> Changeset.foreign_key_constraint(:artifact_sha256,
          name: :mixer_release_exact_artifact
        )

      case repo.insert(changeset) do
        {:ok, stored} ->
          repo.update!(Changeset.change(head, sequence: stored.sequence))
          with :ok <- ReleaseJobs.enqueue(repo, stored), do: {:ok, stored}

        {:error, %Changeset{errors: [artifact_sha256: _]}} ->
          {:error, :not_found}

        {:error, _} ->
          {:error, :storage_unavailable}
      end
    else
      {:error, :conflict}
    end
  end

  defp replay(stored, values) do
    # Numeric may round-trip with a different scale. Compare its value exactly.
    if stored.action == "publish" and Decimal.equal?(stored.sequence, values.sequence) and
         Map.take(stored, Map.keys(values) -- [:sequence]) === Map.delete(values, :sequence) do
      {:ok, stored}
    else
      {:error, :idempotency_conflict}
    end
  end

  defp result(stored) do
    stored
    |> Map.take(@value_fields)
    |> Map.put(:sequence, Decimal.to_integer(stored.sequence))
    |> Map.put(
      :previous_sequence,
      stored.previous_sequence && Decimal.to_integer(stored.previous_sequence)
    )
  end

  defp cli_result(%Publication{action: "halt"} = stored, target),
    do: Map.put(result(stored), :halt, Publication.halt_sample(stored, target))

  defp cli_result(stored, _target), do: result(stored)

  defp valid_metadata?(key, reason) do
    is_binary(key) and byte_size(key) in 1..128 and
      Regex.match?(~r/\A[A-Za-z0-9_.:-]+\z/, key) and
      Encoding.bounded_string?(reason, 512) and :binary.match(reason, <<0>>) == :nomatch
  end

  defp check_writer!(repo) do
    [[count, safe?]] =
      Session.query!(repo, """
      SELECT count(*),bool_and(c.relkind='r' AND c.relrowsecurity AND c.relforcerowsecurity
        AND NOT r.rolcanlogin AND NOT r.rolsuper AND NOT r.rolbypassrls
        AND NOT pg_catalog.pg_has_role(current_user,c.relowner,'MEMBER')
        AND NOT pg_catalog.has_schema_privilege(current_user,'public','CREATE')
        AND NOT pg_catalog.has_table_privilege(current_user,c.oid,'DELETE,TRUNCATE,REFERENCES,TRIGGER')
        AND NOT pg_catalog.has_any_column_privilege(current_user,c.oid,'REFERENCES')
        AND CASE WHEN c.relname='mixer_release_heads' THEN
          NOT pg_catalog.has_any_column_privilege(current_user,c.oid,'INSERT')
          AND NOT EXISTS (
            SELECT 1 FROM pg_catalog.pg_attribute a WHERE a.attrelid=c.oid AND a.attnum>0
              AND NOT a.attisdropped AND a.attname<>'sequence'
              AND pg_catalog.has_column_privilege(current_user,c.oid,a.attnum,'UPDATE'))
        ELSE NOT pg_catalog.has_any_column_privilege(current_user,c.oid,'UPDATE')
          AND NOT pg_catalog.has_column_privilege(current_user,c.oid,'recorded_at','INSERT') END)
      FROM pg_catalog.pg_class c JOIN pg_catalog.pg_roles r ON r.oid=c.relowner
      WHERE c.oid IN ('public.mixer_release_heads'::regclass,'public.mixer_release_publications'::regclass)
      """).rows

    if count != 2 or not safe?, do: repo.rollback(:authorization_unavailable)
  end
end
