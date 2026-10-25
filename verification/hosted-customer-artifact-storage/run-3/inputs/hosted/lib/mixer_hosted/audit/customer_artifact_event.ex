defmodule MixerHosted.Audit.CustomerArtifactEvent do
  @moduledoc """
  Pure, bounded schema-2 customer artifact audit codec.

  Snapshots and records are forgeable data, never storage authority. Building a
  record does not admit an artifact, verify a signature, acquire a lock or prove
  database freshness. Decode verifies only invariants retained by the wire data.
  All digests are lowercase hexadecimal text; external references are hashed in
  separate namespaces. No raw subject, issuer, client or credential is retained.
  """

  alias MixerHosted.Authorization.{Policy, Scope}
  alias MixerHosted.Authorization.Transaction.Snapshot
  alias MixerHosted.Identity.Encoding
  alias MixerHosted.Protocol.ArtifactCBOR

  @max 9_007_199_254_740_991
  @action "artifact.upload"
  @scope "mixer.artifact.upload"
  @roles ~w(owner administrator developer)
  @fields ~w(audit_schema sequence tenant actor authorization target action outcome reason request_id source_ip recorded_at previous_state_sha256 current_state_sha256 previous_event_sha256 request_sha256 envelope_sha256)
  @display_fields @fields ++ ["event_sha256"]
  @artifact_fields ~w(organization_id project_id application_id environment_id platform runtime_sha256 manifest_sha256 payload_sha256 envelope_sha256)a
  @command_fields ~w(sequence previous_state_sha256 previous_event_sha256 outcome reason source_ip)a
  @snapshot_fields ~w(request_id profile binding principal credential family memberships organization_head project_head identity action target checked_at)a
  @member_fields ~w(id principal_id role scope project_binding active not_before expires_at revision)a
  @immutable_fields @snapshot_fields -- [:memberships, :checked_at]
  @row_fields [:event_cbor, :event_sha256, :display]

  defmodule Record do
    @moduledoc "A forgeable pure value; validation grants no storage or actor authority."
    @enforce_keys [:event_cbor, :event_sha256, :display]
    defstruct @enforce_keys
    @type t :: %__MODULE__{event_cbor: binary(), event_sha256: binary(), display: map()}
  end

  @type error :: {:error, :invalid_audit_event}

  @spec build(term(), term(), term(), term(), term()) :: {:ok, Record.t()} | error()
  def build(identity, locked, fresh, artifact, command) do
    with true <- snapshot?(locked, identity),
         true <- snapshot?(fresh, identity),
         true <- Enum.all?(@immutable_fields, &(Map.fetch!(locked, &1) === Map.fetch!(fresh, &1))),
         true <-
           fresh.checked_at >= locked.checked_at and fresh.checked_at <= locked.checked_at + 5,
         true <- strict?(artifact, @artifact_fields),
         true <- strict?(command, @command_fields),
         {:ok, target} <- artifact_target(artifact),
         true <- target_scope(target) === fresh.target,
         true <- command?(command),
         {:ok, binding_bytes} <-
           ArtifactCBOR.encode([identity.profile_id, identity.profile_version, identity.subject]),
         {:ok, request} <- request_hash(target, artifact.envelope_sha256, command.reason),
         {:ok, current} <- current_state(target, artifact.envelope_sha256, command) do
      actor = [
        fresh.principal.id,
        "human",
        identity.profile_id,
        identity.profile_version,
        hash("binding_key", binding_bytes),
        hash("issuer", identity.issuer),
        hash("subject", identity.subject),
        hash("client", identity.client_id),
        hash("credential_ref", identity.credential_ref),
        fresh.family.id,
        identity.issued_at,
        identity.expires_at
      ]

      authorization = [
        locked.checked_at,
        fresh.checked_at,
        [fresh.profile.state_revision, true],
        [fresh.binding.revision, true],
        [fresh.principal.revision, true, fresh.principal.not_before],
        [
          fresh.credential.revision,
          true,
          fresh.credential.not_before,
          optional(fresh.credential.expires_at)
        ],
        [fresh.family.revision, true, fresh.family.not_before, optional(fresh.family.expires_at)],
        fresh.organization_head.revision,
        fresh.project_head.revision,
        @scope,
        Enum.map(fresh.memberships, &member_array/1)
      ]

      display =
        Enum.zip(@fields, [
          2,
          command.sequence,
          Enum.take(target, 2),
          actor,
          authorization,
          target,
          @action,
          command.outcome,
          command.reason,
          fresh.request_id,
          optional(command.source_ip),
          fresh.checked_at,
          command.previous_state_sha256,
          current,
          command.previous_event_sha256,
          request,
          artifact.envelope_sha256
        ])
        |> Map.new()

      with {:ok, bytes} <- ArtifactCBOR.encode(Enum.map(@fields, &Map.fetch!(display, &1))) do
        decode(Map.put(display, "event_sha256", hash("audit", bytes)))
      else
        _ -> invalid()
      end
    else
      _ -> invalid()
    end
  rescue
    _ -> invalid()
  catch
    _, _ -> invalid()
  end

  @spec decode(term()) :: {:ok, Record.t()} | error()
  def decode(display) do
    with true <- strict?(display, @display_fields),
         true <- display["audit_schema"] === 2 and positive?(display["sequence"]),
         [org, project] <- display["tenant"],
         true <- Scope.identifier?(org) and Scope.identifier?(project),
         {:ok, actor} <- actor(display["actor"]),
         true <-
           authorization?(display["authorization"], actor, display["recorded_at"], org, project),
         true <- target?(display["target"]),
         [^org, ^project | _] <- display["target"],
         true <- display["action"] === @action,
         true <- reason?(display["reason"]),
         true <- hex?(display["request_id"], 32),
         true <- optional_ip?(display["source_ip"]),
         true <- digest?(display["event_sha256"]) and digest?(display["envelope_sha256"]),
         command = %{
           sequence: display["sequence"],
           previous_state_sha256: display["previous_state_sha256"],
           previous_event_sha256: display["previous_event_sha256"],
           outcome: display["outcome"],
           reason: display["reason"],
           source_ip: nil
         },
         true <- command?(command),
         true <- initial_state?(command, org, project),
         {:ok, current} <- current_state(display["target"], display["envelope_sha256"], command),
         true <- current === display["current_state_sha256"],
         {:ok, request} <-
           request_hash(display["target"], display["envelope_sha256"], display["reason"]),
         true <- request === display["request_sha256"],
         {:ok, bytes} <- ArtifactCBOR.encode(Enum.map(@fields, &Map.fetch!(display, &1))),
         digest = hash("audit", bytes),
         true <- digest === display["event_sha256"] do
      {:ok, %Record{event_cbor: bytes, event_sha256: digest, display: display}}
    else
      _ -> invalid()
    end
  rescue
    _ -> invalid()
  catch
    _, _ -> invalid()
  end

  @spec validate_row(term()) :: :ok | error()
  def validate_row(row) do
    with {:ok, row} <- row_map(row),
         true <- is_binary(row.event_cbor) and byte_size(row.event_cbor) in 1..65_536,
         true <- digest?(row.event_sha256),
         {:ok, decoded} <- decode(row.display),
         true <-
           decoded.event_cbor === row.event_cbor and decoded.event_sha256 === row.event_sha256 do
      :ok
    else
      _ -> invalid()
    end
  end

  @spec validate_edge(term(), term()) :: :ok | error()
  def validate_edge(current, previous) do
    with :ok <- validate_row(current),
         {:ok, current} <- row_map(current) do
      c = current.display

      if c["sequence"] == 1 do
        if is_nil(previous), do: :ok, else: invalid()
      else
        with :ok <- validate_row(previous),
             {:ok, previous} <- row_map(previous),
             p = previous.display,
             true <- c["tenant"] === p["tenant"] and c["sequence"] == p["sequence"] + 1,
             true <- c["previous_event_sha256"] === previous.event_sha256,
             true <- c["previous_state_sha256"] === p["current_state_sha256"] do
          :ok
        else
          _ -> invalid()
        end
      end
    else
      _ -> invalid()
    end
  end

  @spec genesis(term(), term()) :: {:ok, binary()} | error()
  def genesis(organization, project) do
    if Scope.identifier?(organization) and Scope.identifier?(project) do
      {:ok, bytes} = ArtifactCBOR.encode([2, organization, project])
      {:ok, hash("state", bytes)}
    else
      invalid()
    end
  end

  @spec request_hash(term(), term(), term()) :: {:ok, binary()} | error()
  def request_hash(target, envelope_sha256, reason) do
    with true <- target?(target) and digest?(envelope_sha256) and reason?(reason),
         {:ok, bytes} <- ArtifactCBOR.encode([2, @action, target, envelope_sha256, reason]) do
      {:ok, hash("upload.request", bytes)}
    else
      _ -> invalid()
    end
  end

  defp snapshot?(s, identity) do
    with true <- strict?(s, @snapshot_fields),
         true <- bounded_list?(s.memberships, 64) and s.memberships != [],
         true <-
           Enum.all?(s.memberships, fn m ->
             strict?(m, @member_fields) and Scope.identifier?(m.id) and m.role in @roles
           end),
         true <-
           is_map(s.principal) and is_map(s.credential) and
             is_map(s.organization_head) and is_map(s.project_head),
         decision = %Policy.Decision{
           action: s.action,
           target: s.target,
           principal_id: s.principal.id,
           credential_ref: identity.credential_ref,
           profile_id: identity.profile_id,
           profile_version: identity.profile_version,
           membership_ids: Enum.map(s.memberships, & &1.id),
           roles: s.memberships |> Enum.map(& &1.role) |> Enum.uniq() |> Enum.sort(),
           principal_revision: s.principal.revision,
           credential_revision: s.credential.revision,
           organization_revision: s.organization_head.revision,
           project_revision: s.project_head.revision,
           evaluated_at: s.checked_at
         },
         true <- Snapshot.valid?(s, identity, decision),
         true <- s.action === @action and s.principal.not_before <= s.checked_at do
      true
    else
      _ -> false
    end
  end

  defp artifact_target(a) do
    target = [
      a.organization_id,
      a.project_id,
      a.application_id,
      a.environment_id,
      a.platform,
      a.runtime_sha256,
      a.manifest_sha256,
      a.payload_sha256
    ]

    if target?(target) and digest?(a.envelope_sha256), do: {:ok, target}, else: invalid()
  end

  defp target?([org, project, app, env, platform, runtime, manifest, payload]),
    do:
      Enum.all?([org, project, app, env], &Scope.identifier?/1) and
        platform in ["ios", "android"] and Enum.all?([runtime, manifest, payload], &digest?/1)

  defp target?(_), do: false

  defp target_scope([org, project, app, env | _]),
    do: %Scope{
      organization_id: org,
      project_id: project,
      application_id: app,
      environment_id: env
    }

  defp actor([
         principal,
         "human",
         profile,
         version,
         binding,
         issuer,
         subject,
         client,
         credential,
         family,
         issued,
         expires
       ]) do
    if Scope.identifier?(principal) and Encoding.bounded_string?(profile, 128) and
         is_integer(version) and version in 1..2_147_483_647 and Scope.identifier?(family) and
         Enum.all?([binding, issuer, subject, client, credential], &digest?/1) and
         date?(issued) and date?(expires) and issued < expires do
      {:ok, %{issued: issued, expires: expires}}
    else
      invalid()
    end
  end

  defp actor(_), do: invalid()

  defp authorization?(
         [
           locked,
           fresh,
           [pr, true],
           [br, true],
           [principal_r, true, principal_start],
           [cr, true, credential_start, credential_end],
           [fr, true, family_start, family_end],
           org_r,
           project_r,
           @scope,
           members
         ],
         actor,
         recorded,
         org,
         project
       ) do
    date?(locked) and date?(fresh) and fresh >= locked and fresh <= locked + 5 and
      recorded === fresh and actor.issued <= locked + 30 and fresh < actor.expires and
      Enum.all?([pr, br, principal_r, cr, fr, org_r, project_r], &positive?/1) and
      date?(principal_start) and principal_start <= locked and principal_start <= actor.issued and
      state_window?(credential_start, credential_end, locked, fresh, actor.issued) and
      state_window?(family_start, family_end, locked, fresh, actor.issued) and
      members?(members, fresh, org, project)
  end

  defp authorization?(_, _, _, _, _), do: false

  defp state_window?(start, finish, locked, fresh, issued),
    do: date?(start) and start <= locked and start <= issued and end?(finish, start, fresh)

  defp end?([], _start, _now), do: true
  defp end?([finish], start, now), do: date?(finish) and start < finish and now < finish
  defp end?(_, _, _), do: false

  defp members?(members, now, org, project) do
    bounded_list?(members, 64) and members != [] and
      Enum.all?(members, &member?(&1, now, org, project)) and
      sorted_ids?(members, nil)
  end

  defp member?(
         [id, role, revision, org, optional_project, binding, true, start, finish],
         now,
         org,
         project
       ),
       do:
         Scope.identifier?(id) and role in @roles and positive?(revision) and
           ((optional_project === [] and binding === "all_projects") or
              (optional_project === [project] and binding === "exact_project")) and
           date?(start) and start <= now and end?(finish, start, now)

  defp member?(_, _, _, _), do: false

  defp sorted_ids?([], _previous), do: true
  defp sorted_ids?([[id | _] | rest], nil), do: sorted_ids?(rest, id)
  defp sorted_ids?([[id | _] | rest], previous), do: id > previous and sorted_ids?(rest, id)

  defp member_array(m),
    do: [
      m.id,
      m.role,
      m.revision,
      m.scope.organization_id,
      optional(m.scope.project_id),
      Atom.to_string(m.project_binding),
      true,
      m.not_before,
      optional(m.expires_at)
    ]

  defp command?(c),
    do:
      positive?(c.sequence) and digest?(c.previous_state_sha256) and
        ((c.sequence == 1 and c.previous_event_sha256 === "") or
           (c.sequence > 1 and digest?(c.previous_event_sha256))) and
        c.outcome in ["created", "unchanged"] and reason?(c.reason) and
        (is_nil(c.source_ip) or canonical_ip?(c.source_ip))

  defp initial_state?(%{sequence: 1, previous_state_sha256: previous}, org, project),
    do: genesis(org, project) === {:ok, previous}

  defp initial_state?(_, _, _), do: true

  defp current_state(_target, _envelope, %{outcome: "unchanged", previous_state_sha256: previous}),
       do: {:ok, previous}

  defp current_state(
         [org, project, _app, _env, _platform, _runtime, manifest, payload],
         envelope,
         c
       ) do
    with {:ok, bytes} <-
           ArtifactCBOR.encode([
             2,
             org,
             project,
             c.previous_state_sha256,
             c.sequence,
             manifest,
             envelope,
             payload
           ]) do
      {:ok, hash("state", bytes)}
    end
  end

  defp optional_ip?([]), do: true
  defp optional_ip?([ip]), do: canonical_ip?(ip)
  defp optional_ip?(_), do: false

  defp canonical_ip?(ip) when is_binary(ip) and byte_size(ip) in 2..45 do
    with true <- String.valid?(ip),
         {:ok, address} <- :inet.parse_address(String.to_charlist(ip)),
         rendered = address |> :inet.ntoa() |> List.to_string() do
      rendered === ip
    else
      _ -> false
    end
  end

  defp canonical_ip?(_), do: false

  defp row_map(%Record{} = row) when map_size(row) == 4 do
    value = Map.from_struct(row)
    if strict?(value, @row_fields), do: {:ok, value}, else: invalid()
  end

  defp row_map(row) do
    if strict?(row, @row_fields), do: {:ok, row}, else: invalid()
  end

  defp strict?(value, fields) when is_map(value) and not is_struct(value),
    do: map_size(value) == length(fields) and Enum.all?(fields, &Map.has_key?(value, &1))

  defp strict?(_, _), do: false
  defp bounded_list?([], _), do: true

  defp bounded_list?([_ | tail], remaining) when remaining > 0,
    do: bounded_list?(tail, remaining - 1)

  defp bounded_list?(_, _), do: false
  defp optional(nil), do: []
  defp optional(value), do: [value]
  defp reason?(v), do: is_binary(v) and byte_size(v) <= 512 and String.valid?(v)
  defp date?(v), do: Encoding.numeric_date?(v)
  defp positive?(v), do: is_integer(v) and v in 1..@max
  defp digest?(v), do: hex?(v, 64)

  defp hex?(v, n) when is_binary(v) and byte_size(v) == n,
    do: Enum.all?(:binary.bin_to_list(v), &(&1 in ?0..?9 or &1 in ?a..?f))

  defp hex?(_, _), do: false

  defp hash(field, bytes),
    do:
      :crypto.hash(:sha256, "mixer.hosted.customer." <> field <> ".v2\0" <> bytes)
      |> Base.encode16(case: :lower)

  defp invalid, do: {:error, :invalid_audit_event}
end
