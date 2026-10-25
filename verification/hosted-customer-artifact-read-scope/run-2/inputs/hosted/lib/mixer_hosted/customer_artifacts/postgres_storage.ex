defmodule MixerHosted.CustomerArtifacts.PostgresStorage do
  @moduledoc """
  Protected local customer artifact SQL within Authorization's owned transaction.

  Configuration is a closed trusted server map containing `repo`, `host`, `roots`.
  This module never begins a transaction and never performs external effects.
  A Context is checked before any query, after the project-head wait and before
  bytes or cached results return. A Checked artifact is re-admitted at effect time.
  """
  alias MixerHosted.Authorization.Scope
  alias MixerHosted.Authorization.Postgres.Session
  alias MixerHosted.Authorization.Transaction.Context
  alias MixerHosted.Audit.CustomerArtifactEvent, as: Event
  alias MixerHosted.CustomerArtifacts.Topology
  alias MixerHosted.Protocol.{ArtifactAdmission, ArtifactV3Policy}
  @maximum 9_007_199_254_740_991
  @artifact_columns ~w(organization_id project_id application_id environment_id platform runtime_sha256 manifest_sha256 payload_sha256 envelope_sha256 envelope_bytes signed_manifest_bytes canonical_manifest_cbor signature payload creating_sequence)
  @event_columns ~w(event_cbor event_sha256 display)

  @doc false
  def check_topology!(repo), do: Topology.check!(repo)

  def upload(context, checked, command, config) do
    protect(context, "artifact.upload", config, fn repo, target, _ ->
      with true <- valid_command?(command),
           %ArtifactAdmission.Checked{} <- checked,
           true <- target === scope(checked) do
        check_topology!(repo)

        [sequence, previous_event, previous_state] =
          Session.one!(
            repo,
            "SELECT sequence,event_sha256,state_sha256 FROM public.mixer_customer_artifact_heads WHERE organization_id=$1 AND project_id=$2 FOR UPDATE",
            tenant(target),
            :storage_unavailable
          )

        fresh = Context.checkpoint!(context, repo, "artifact.upload", target)

        with {:ok, ^checked} <-
               ArtifactAdmission.recheck(checked, config.host, config.roots, fresh.checked_at),
             true <- sequence < @maximum do
          artifact = artifact(checked)

          with {:ok, request_hash} <-
                 Event.request_hash(
                   Enum.map(
                     ~w(organization_id project_id application_id environment_id platform runtime_sha256 manifest_sha256 payload_sha256)a,
                     &Map.fetch!(artifact, &1)
                   ),
                   artifact.envelope_sha256,
                   command.reason
                 ) do
            own =
              query(
                repo,
                "SELECT principal_id,action,application_id,environment_id,manifest_sha256,request_sha256,event_sequence,status,payload_sha256 FROM public.mixer_customer_idempotency WHERE organization_id=$1 AND project_id=$2 AND key=$3",
                tenant(target) ++ [command.key]
              ).rows

            case own do
              [
                [
                  principal,
                  "artifact.upload",
                  app,
                  env,
                  digest,
                  ^request_hash,
                  seq,
                  status,
                  payload
                ]
              ]
              when principal == fresh.principal.id and app == target.application_id and
                     env == target.environment_id and digest == checked.manifest_sha256 ->
                Context.effect!(context, repo, "artifact.upload", target, fn effect ->
                  with {:ok, ^checked} <-
                         ArtifactAdmission.recheck(
                           checked,
                           config.host,
                           config.roots,
                           effect.checked_at
                         ) do
                    {:ok, result(status, digest, payload, seq)}
                  else
                    _ -> {:error, :storage_unavailable}
                  end
                end)

              [] ->
                case query(repo, "SELECT public.mixer_customer_key_exists($1)", [command.key]).rows do
                  [[false]] ->
                    write_new(
                      context,
                      checked,
                      command,
                      config,
                      artifact,
                      sequence,
                      previous_event,
                      previous_state
                    )

                  _ ->
                    {:error, :idempotency_conflict}
                end

              _ ->
                {:error, :idempotency_conflict}
            end
          else
            _ -> {:error, :storage_unavailable}
          end
        else
          _ -> {:error, :storage_unavailable}
        end
      else
        _ -> {:error, :invalid_request}
      end
    end)
  end

  def read(context, digest, config) do
    protect(context, "artifact.read", config, fn repo, target, _ ->
      if ArtifactV3Policy.digest?(digest) do
        check_topology!(repo)

        case query(
               repo,
               "SELECT #{Enum.join(@artifact_columns, ",")} FROM public.mixer_customer_artifacts WHERE organization_id=$1 AND project_id=$2 AND manifest_sha256=$3",
               tenant(target) ++ [digest]
             ).rows do
          [row] ->
            retained = Map.new(Enum.zip(@artifact_columns, row))

            Context.effect!(context, repo, "artifact.read", target, fn fresh ->
              with true <-
                     retained["application_id"] == target.application_id and
                       retained["environment_id"] == target.environment_id,
                   {:ok, checked} <-
                     ArtifactAdmission.admit(
                       retained["envelope_bytes"],
                       config.host,
                       config.roots,
                       fresh.checked_at
                     ),
                   true <- matches?(retained, checked),
                   [^row] <-
                     query(
                       repo,
                       "SELECT #{Enum.join(@artifact_columns, ",")} FROM public.mixer_customer_artifacts WHERE organization_id=$1 AND project_id=$2 AND manifest_sha256=$3",
                       tenant(target) ++ [digest]
                     ).rows do
                {:ok,
                 %{
                   envelope_bytes: checked.envelope_bytes,
                   manifest_sha256: checked.manifest_sha256,
                   payload_sha256: checked.payload_sha256
                 }}
              else
                _ -> {:error, :storage_unavailable}
              end
            end)

          [] ->
            {:error, :not_found}

          _ ->
            {:error, :storage_unavailable}
        end
      else
        {:error, :invalid_request}
      end
    end)
  end

  def audit(context, after_sequence, limit, config) do
    protect(context, "audit.read", config, fn repo, target, _ ->
      if Scope.project_only?(target) and is_integer(after_sequence) and
           after_sequence in 0..@maximum and is_integer(limit) and limit in 1..100 do
        check_topology!(repo)

        records =
          query(
            repo,
            "SELECT #{Enum.join(@event_columns, ",")} FROM public.mixer_customer_audit_events WHERE organization_id=$1 AND project_id=$2 AND sequence>$3 ORDER BY sequence LIMIT $4",
            tenant(target) ++ [after_sequence, limit]
          ).rows

        predecessor =
          if records == [] or after_sequence == 0,
            do: nil,
            else: predecessor(repo, target, after_sequence)

        Context.effect!(context, repo, "audit.read", target, fn _ ->
          with {:ok, result} <- validate_page(records, predecessor, after_sequence) do
            {:ok, result}
          end
        end)
      else
        {:error, :invalid_request}
      end
    end)
  end

  defp write_new(
         context,
         checked,
         command,
         config,
         artifact,
         sequence,
         previous_event,
         previous_state
       ) do
    repo = config.repo
    target = context.target

    existing =
      query(
        repo,
        "SELECT #{Enum.join(@artifact_columns, ",")} FROM public.mixer_customer_artifacts WHERE organization_id=$1 AND project_id=$2 AND manifest_sha256=$3",
        tenant(target) ++ [checked.manifest_sha256]
      ).rows

    outcome =
      case existing do
        [] ->
          "created"

        [row] ->
          retained = Map.new(Enum.zip(@artifact_columns, row))

          if retained["canonical_manifest_cbor"] === checked.canonical_manifest_cbor and
               retained["signature"] === checked.signature and
               retained["payload"] === checked.payload and
               matches_current?(retained, config, context), do: "unchanged", else: :conflict

        _ ->
          :invalid
      end

    case outcome do
      :conflict ->
        {:error, :immutable_conflict}

      :invalid ->
        {:error, :storage_unavailable}

      _ ->
        Context.effect!(context, repo, "artifact.upload", target, fn fresh ->
          with {:ok, ^checked} <-
                 ArtifactAdmission.recheck(checked, config.host, config.roots, fresh.checked_at),
               {:ok, event} <-
                 Event.build(context.identity, context.snapshot, fresh, artifact, %{
                   sequence: sequence + 1,
                   previous_state_sha256: previous_state,
                   previous_event_sha256: previous_event,
                   outcome: outcome,
                   reason: command.reason,
                   source_ip: command.source_ip
                 }) do
            if outcome == "created" do
              values = [
                artifact.organization_id,
                artifact.project_id,
                artifact.application_id,
                artifact.environment_id,
                artifact.platform,
                artifact.runtime_sha256,
                artifact.manifest_sha256,
                artifact.payload_sha256,
                artifact.envelope_sha256,
                checked.envelope_bytes,
                checked.signed_manifest_bytes,
                checked.canonical_manifest_cbor,
                checked.signature,
                checked.payload,
                sequence + 1
              ]

              insert(repo, "mixer_customer_artifacts", @artifact_columns, values)
            end

            display = event.display

            insert(
              repo,
              "mixer_customer_audit_events",
              ~w(organization_id project_id sequence manifest_sha256 audit_schema event_cbor event_sha256 previous_event_sha256 previous_state_sha256 current_state_sha256 display),
              tenant(target) ++
                [
                  sequence + 1,
                  checked.manifest_sha256,
                  2,
                  event.event_cbor,
                  event.event_sha256,
                  previous_event,
                  previous_state,
                  display["current_state_sha256"],
                  display
                ]
            )

            status = if outcome == "created", do: 201, else: 200

            insert(
              repo,
              "mixer_customer_idempotency",
              ~w(organization_id project_id key principal_id action application_id environment_id manifest_sha256 request_sha256 event_sequence status payload_sha256),
              tenant(target) ++
                [
                  command.key,
                  fresh.principal.id,
                  "artifact.upload",
                  target.application_id,
                  target.environment_id,
                  checked.manifest_sha256,
                  display["request_sha256"],
                  sequence + 1,
                  status,
                  checked.payload_sha256
                ]
            )

            case query(
                   repo,
                   "UPDATE public.mixer_customer_artifact_heads SET sequence=$3,event_sha256=$4,state_sha256=$5 WHERE organization_id=$1 AND project_id=$2 AND sequence=$6",
                   tenant(target) ++
                     [sequence + 1, event.event_sha256, display["current_state_sha256"], sequence]
                 ).num_rows do
              1 ->
                # Force all deferred checks inside the protected effect, so a
                # constraint failure is a latched storage error before commit.
                query(repo, "SET CONSTRAINTS ALL IMMEDIATE")
                query(repo, "SET CONSTRAINTS ALL DEFERRED")

                {:ok,
                 result(status, checked.manifest_sha256, checked.payload_sha256, sequence + 1)}

              _ ->
                {:error, :storage_unavailable}
            end
          else
            _ -> {:error, :storage_unavailable}
          end
        end)
    end
  end

  defp protect(context, action, config, callback) do
    # Even malformed contexts pass through Context's owner-process latch. Never
    # authorize by matching the public struct alone or by accepting a Decision.
    repo = if is_map(config), do: Map.get(config, :repo), else: nil
    target = if is_map(context), do: Map.get(context, :target), else: nil

    Context.effect!(context, repo, action, target, fn snapshot ->
      try do
        if valid_config?(config),
          do: callback.(repo, target, snapshot),
          else: {:error, :invalid_request}
      rescue
        _ -> {:error, :storage_unavailable}
      end
    end)
  end

  defp valid_config?(c),
    do:
      strict?(c, [:repo, :host, :roots]) and is_atom(c.repo) and ArtifactV3Policy.host?(c.host) and
        ArtifactV3Policy.roots?(c.roots)

  defp valid_command?(c),
    do:
      strict?(c, [:key, :reason, :source_ip]) and is_binary(c.key) and byte_size(c.key) in 1..128 and
        Enum.all?(
          :binary.bin_to_list(c.key),
          &(&1 in ?A..?Z or &1 in ?a..?z or &1 in ?0..?9 or &1 in [?_, ?., ?:, ?-])
        ) and is_binary(c.reason) and byte_size(c.reason) <= 512 and String.valid?(c.reason) and
        (is_nil(c.source_ip) or is_binary(c.source_ip))

  defp strict?(c, keys),
    do:
      is_map(c) and not is_struct(c) and map_size(c) == length(keys) and
        Enum.all?(keys, &Map.has_key?(c, &1))

  defp scope(c),
    do: %Scope{
      organization_id: c.target["organization"],
      project_id: c.target["project"],
      application_id: c.target["app"],
      environment_id: c.target["environment"]
    }

  defp artifact(c),
    do: %{
      organization_id: c.target["organization"],
      project_id: c.target["project"],
      application_id: c.target["app"],
      environment_id: c.target["environment"],
      platform: c.target["platform"],
      runtime_sha256: c.target["runtime"],
      manifest_sha256: c.manifest_sha256,
      payload_sha256: c.payload_sha256,
      envelope_sha256: hash(c.envelope_bytes)
    }

  defp tenant(t), do: [t.organization_id, t.project_id]
  defp hash(b), do: Base.encode16(:crypto.hash(:sha256, b), case: :lower)

  defp result(status, m, p, s),
    do: %{status: status, manifest_sha256: m, payload_sha256: p, event_sequence: s}

  defp query(repo, sql, args \\ []), do: Session.query!(repo, sql, args)

  defp insert(repo, table, columns, values),
    do:
      query(
        repo,
        "INSERT INTO public.#{table} (#{Enum.join(columns, ",")}) VALUES (#{Enum.map_join(1..length(columns), ",", &"$#{&1}")})",
        values
      )

  defp matches?(r, c),
    do:
      r["envelope_bytes"] === c.envelope_bytes and
        r["signed_manifest_bytes"] === c.signed_manifest_bytes and
        r["canonical_manifest_cbor"] === c.canonical_manifest_cbor and
        r["signature"] === c.signature and r["payload"] === c.payload and
        Enum.all?(artifact(c), fn {k, v} -> r[Atom.to_string(k)] === v end)

  defp matches_current?(r, config, context) do
    fresh = Context.checkpoint!(context, config.repo, "artifact.upload", context.target)

    case ArtifactAdmission.admit(r["envelope_bytes"], config.host, config.roots, fresh.checked_at) do
      {:ok, c} -> matches?(r, c)
      _ -> false
    end
  end

  defp predecessor(repo, target, n) do
    case query(
           repo,
           "SELECT #{Enum.join(@event_columns, ",")} FROM public.mixer_customer_audit_events WHERE organization_id=$1 AND project_id=$2 AND sequence=$3",
           tenant(target) ++ [n]
         ).rows do
      [r] -> record(r)
      _ -> :missing
    end
  end

  defp record([cbor, hash, display]),
    do: %{event_cbor: cbor, event_sha256: hash, display: display}

  defp validate_page(rows, predecessor, after_sequence) do
    Enum.reduce_while(rows, {:ok, [], predecessor, after_sequence}, fn row, {:ok, acc, prev, n} ->
      e = record(row)

      if e.display["sequence"] == n + 1 and Event.validate_row(e) == :ok and
           Event.validate_edge(e, prev) == :ok,
         do: {:cont, {:ok, [e.display | acc], e, n + 1}},
         else: {:halt, {:error, :storage_unavailable}}
    end)
    |> case do
      {:ok, values, _, _} -> {:ok, Enum.reverse(values)}
      _ -> {:error, :storage_unavailable}
    end
  end
end
