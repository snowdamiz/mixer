defmodule MixerHosted.Authorization.Policy do
  @moduledoc """
  Pure first-slice role and token-scope intersection.

  Inputs are current server repository evidence, never HTTP roles or claims.
  Validation cannot prove database freshness, lineage, locks or revocation.
  A result is an evaluation, not a transaction context or storage capability.
  Only human artifact read/upload and project audit read are implemented.
  """

  alias MixerHosted.Authorization.Scope
  alias MixerHosted.Identity.{Encoding, VerifiedIdentity}

  @max_integer 9_007_199_254_740_991
  @roles ~w(owner administrator developer release_manager billing_manager viewer)
  @read_roles ~w(owner administrator developer release_manager viewer)
  @write_roles ~w(owner administrator developer)
  @actions %{
    "artifact.read" => {"mixer.artifact.read", @read_roles},
    "artifact.upload" => {"mixer.artifact.upload", @write_roles},
    "audit.read" => {"mixer.audit.read", @read_roles}
  }
  @identity_fields [
    :profile_id,
    :profile_version,
    :issuer,
    :subject,
    :client_id,
    :credential_ref,
    :issued_at,
    :expires_at,
    :identity_class,
    :scopes
  ]
  @binding_fields [
    :profile_id,
    :profile_version,
    :issuer,
    :subject,
    :client_id,
    :identity_class,
    :principal_id
  ]
  @principal_fields [:id, :identity_class, :active, :not_before, :revision]
  @credential_fields [:reference, :principal_id, :active, :not_before, :expires_at, :revision]
  @membership_fields [
    :id,
    :principal_id,
    :role,
    :scope,
    :project_binding,
    :active,
    :not_before,
    :expires_at,
    :revision
  ]
  @evidence_fields [
    :binding,
    :binding_active,
    :profile_active,
    :principal,
    :credential,
    :target,
    :memberships,
    :organization_revision,
    :project_revision
  ]

  defmodule Decision do
    @moduledoc "An audit-oriented pure evaluation; domain stores must not accept it as authority."
    @enforce_keys [
      :action,
      :target,
      :principal_id,
      :credential_ref,
      :profile_id,
      :profile_version,
      :membership_ids,
      :roles,
      :principal_revision,
      :credential_revision,
      :organization_revision,
      :project_revision,
      :evaluated_at
    ]
    defstruct @enforce_keys
    @type t :: %__MODULE__{}
  end

  @type error ::
          :invalid_request
          | :unauthenticated
          | :not_found
          | :permission_denied
          | :authorization_unavailable
  @type result :: {:ok, Decision.t()} | {:error, error()}
  @type evidence :: map()
  @decision_fields Decision.__struct__() |> Map.from_struct() |> Map.keys()

  @doc false
  def valid_decision?(%Decision{} = decision, identity, action, target, now) do
    with {:ok, ^target} <- request(identity, action, target, now),
         {:ok, {required_scope, allowed_roles}} <- Map.fetch(@actions, action) do
      map_size(decision) == length(@decision_fields) + 1 and
        strict?(Map.from_struct(decision), @decision_fields) and
        decision.action == action and decision.target == target and
        decision.credential_ref == identity.credential_ref and
        decision.profile_id == identity.profile_id and
        decision.profile_version == identity.profile_version and decision.evaluated_at == now and
        Scope.identifier?(decision.principal_id) and
        bounded_list?(decision.membership_ids, 64) and decision.membership_ids != [] and
        Enum.all?(decision.membership_ids, &Scope.identifier?/1) and
        Enum.sort(Enum.uniq(decision.membership_ids)) == decision.membership_ids and
        bounded_list?(decision.roles, length(@roles)) and decision.roles != [] and
        Enum.all?(decision.roles, &(&1 in allowed_roles)) and
        Enum.sort(Enum.uniq(decision.roles)) == decision.roles and
        length(decision.roles) <= length(decision.membership_ids) and
        required_scope in identity.scopes and
        revision?(decision.principal_revision) and revision?(decision.credential_revision) and
        revision?(decision.organization_revision) and revision?(decision.project_revision)
    else
      _ -> false
    end
  end

  def valid_decision?(_, _, _, _, _), do: false

  @spec evaluate(term(), term(), term(), term(), term()) :: result()
  def evaluate(identity, action, target, evidence, now) do
    with {:ok, target} <- request(identity, action, target, now) do
      evaluate_request(identity, action, target, evidence, now)
    end
  end

  @doc false
  def metadata_evaluate(identity, target, evidence, now) do
    with {:ok, target} <- metadata_request(identity, target, now) do
      evaluate_request(identity, "artifact.read", target, evidence, now)
    end
  end

  defp evaluate_request(identity, action, target, evidence, now) do
    with {:ok, evidence} <- evidence(evidence),
         :ok <- current_identity(identity, evidence, now),
         :ok <- live_target(target, evidence.target),
         memberships = eligible_memberships(evidence.memberships, target, now),
         :ok <- visible(memberships),
         {:ok, roles, membership_ids} <- permission(identity, action, memberships) do
      {:ok,
       %Decision{
         action: action,
         target: target,
         principal_id: evidence.principal.id,
         credential_ref: identity.credential_ref,
         profile_id: identity.profile_id,
         profile_version: identity.profile_version,
         membership_ids: membership_ids,
         roles: roles,
         principal_revision: evidence.principal.revision,
         credential_revision: evidence.credential.revision,
         organization_revision: evidence.organization_revision,
         project_revision: evidence.project_revision,
         evaluated_at: now
       }}
    end
  end

  @doc false
  @spec request(term(), term(), term(), term()) :: {:ok, Scope.t()} | {:error, error()}
  def request(identity, action, target, now) do
    cond do
      not Encoding.numeric_date?(now) ->
        {:error, :invalid_request}

      not valid_identity?(identity) ->
        {:error, :unauthenticated}

      identity.expires_at <= now or identity.issued_at > now + 30 ->
        {:error, :unauthenticated}

      identity.identity_class != :human ->
        {:error, :permission_denied}

      not (is_binary(action) and byte_size(action) in 1..32 and is_map_key(@actions, action)) ->
        {:error, :permission_denied}

      true ->
        with {:ok, scope} <- Scope.new(target),
             true <- valid_action_target?(action, scope) do
          {:ok, scope}
        else
          _ -> {:error, :invalid_request}
        end
    end
  end

  @doc false
  def metadata_request(identity, target, now) do
    # This is project metadata admission only. It cannot construct an artifact
    # Decision or Context and does not weaken request/4's environment contract.
    with {:ok, scope} <- request(identity, "audit.read", target, now) do
      if "mixer.artifact.read" in identity.scopes,
        do: {:ok, scope},
        else: {:error, :permission_denied}
    end
  end

  @doc false
  def identity_key(%VerifiedIdentity{} = identity),
    do:
      Map.take(identity, @binding_fields -- [:principal_id])
      |> Map.put(:credential_ref, identity.credential_ref)

  defp valid_identity?(%VerifiedIdentity{} = identity) do
    map_size(identity) == length(@identity_fields) + 1 and
      strict?(Map.from_struct(identity), @identity_fields) and
      Encoding.bounded_string?(identity.profile_id, 128) and
      profile_version?(identity.profile_version) and
      Encoding.bounded_string?(identity.issuer, 2_048) and
      Encoding.bounded_string?(identity.subject, 256) and
      Encoding.bounded_string?(identity.client_id, 256) and
      Encoding.bounded_string?(identity.credential_ref, 256) and
      identity.identity_class in [:human, :service] and
      Encoding.numeric_date?(identity.issued_at) and Encoding.numeric_date?(identity.expires_at) and
      identity.issued_at < identity.expires_at and bounded_list?(identity.scopes, 32) and
      Enum.all?(identity.scopes, &Encoding.bounded_string?(&1, 256)) and
      Enum.uniq(identity.scopes) == identity.scopes
  end

  defp valid_identity?(_), do: false

  defp valid_action_target?("audit.read", scope), do: Scope.project_only?(scope)
  defp valid_action_target?(_action, scope), do: Scope.environment?(scope)

  defp evidence(value) do
    with true <- strict?(value, @evidence_fields),
         true <- strict?(value.binding, @binding_fields),
         true <- strict?(value.principal, @principal_fields),
         true <- strict?(value.credential, @credential_fields),
         true <- strict?(value.target, [:scope, :active]),
         {:ok, target} <- Scope.new(value.target.scope),
         true <- is_boolean(value.target.active),
         true <- is_boolean(value.binding_active) and is_boolean(value.profile_active),
         true <- valid_binding?(value.binding),
         true <- valid_principal?(value.principal),
         true <- valid_credential?(value.credential),
         true <- revision?(value.organization_revision) and revision?(value.project_revision),
         true <- bounded_list?(value.memberships, 64),
         {:ok, memberships} <- memberships(value.memberships),
         true <- Enum.all?(memberships, &(&1.principal_id == value.principal.id)) do
      {:ok, %{value | memberships: memberships, target: %{value.target | scope: target}}}
    else
      _ -> {:error, :authorization_unavailable}
    end
  end

  defp valid_binding?(binding) do
    Scope.identifier?(binding.principal_id) and
      Encoding.bounded_string?(binding.profile_id, 128) and
      profile_version?(binding.profile_version) and
      Encoding.bounded_string?(binding.issuer, 2_048) and
      Encoding.bounded_string?(binding.subject, 256) and
      Encoding.bounded_string?(binding.client_id, 256) and
      binding.identity_class in [:human, :service]
  end

  defp valid_principal?(principal),
    do:
      Scope.identifier?(principal.id) and principal.identity_class in [:human, :service] and
        is_boolean(principal.active) and Encoding.numeric_date?(principal.not_before) and
        revision?(principal.revision)

  defp valid_credential?(credential),
    do:
      Encoding.bounded_string?(credential.reference, 256) and
        Scope.identifier?(credential.principal_id) and is_boolean(credential.active) and
        window?(credential.not_before, credential.expires_at) and revision?(credential.revision)

  defp memberships(values) do
    Enum.reduce_while(values, {:ok, [], MapSet.new()}, fn value, {:ok, result, ids} ->
      with true <- strict?(value, @membership_fields),
           true <-
             Scope.identifier?(value.id) and Scope.identifier?(value.principal_id) and
               value.role in @roles,
           false <- MapSet.member?(ids, value.id),
           {:ok, scope} <- Scope.new(value.scope),
           true <- membership_scope?(scope, value.project_binding),
           true <- is_boolean(value.active) and window?(value.not_before, value.expires_at),
           true <- revision?(value.revision) do
        {:cont, {:ok, [%{value | scope: scope} | result], MapSet.put(ids, value.id)}}
      else
        _ -> {:halt, :invalid}
      end
    end)
    |> case do
      {:ok, result, _ids} -> {:ok, Enum.reverse(result)}
      _ -> :invalid
    end
  end

  defp membership_scope?(%Scope{project_id: nil}, binding),
    do: binding in [:organization_only, :all_projects]

  defp membership_scope?(%Scope{application_id: nil}, :exact_project), do: true
  defp membership_scope?(_, _), do: false

  defp current_identity(identity, evidence, now) do
    binding = evidence.binding
    principal = evidence.principal
    credential = evidence.credential

    if Enum.all?(@binding_fields -- [:principal_id], fn field ->
         Map.fetch!(identity, field) == Map.fetch!(binding, field)
       end) and binding.principal_id == principal.id and
         credential.principal_id == principal.id and principal.identity_class == :human and
         credential.reference == identity.credential_ref and evidence.profile_active and
         evidence.binding_active and principal.active and credential.active and
         principal.not_before <= now and identity.issued_at >= principal.not_before and
         identity.issued_at >= credential.not_before and
         in_window?(credential.not_before, credential.expires_at, now) do
      :ok
    else
      {:error, :unauthenticated}
    end
  end

  defp live_target(target, %{scope: target, active: true}), do: :ok
  defp live_target(_target, _evidence), do: {:error, :not_found}

  defp eligible_memberships(memberships, target, now),
    do:
      Enum.filter(memberships, fn member ->
        member.active and in_window?(member.not_before, member.expires_at, now) and
          Scope.membership_covers?(member, target)
      end)

  defp visible([]), do: {:error, :not_found}
  defp visible(_), do: :ok

  defp permission(identity, action, memberships) do
    {scope, roles} = Map.fetch!(@actions, action)
    permitted = Enum.filter(memberships, &(&1.role in roles))

    if scope in identity.scopes and permitted != [] do
      {:ok, permitted |> Enum.map(& &1.role) |> Enum.uniq() |> Enum.sort(),
       permitted |> Enum.map(& &1.id) |> Enum.sort()}
    else
      {:error, :permission_denied}
    end
  end

  defp strict?(value, fields) when is_map(value) and not is_struct(value),
    do: map_size(value) == length(fields) and Enum.all?(fields, &Map.has_key?(value, &1))

  defp strict?(_, _), do: false
  defp profile_version?(value), do: is_integer(value) and value in 1..2_147_483_647
  defp revision?(value), do: is_integer(value) and value in 1..@max_integer
  defp window?(start, nil), do: Encoding.numeric_date?(start)

  defp window?(start, finish),
    do: Encoding.numeric_date?(start) and Encoding.numeric_date?(finish) and start < finish

  defp in_window?(start, finish, now), do: start <= now and (is_nil(finish) or now < finish)

  # Reject improper and over-limit lists before Enum traversal or duplicate checks.
  defp bounded_list?([], _remaining), do: true

  defp bounded_list?([_ | rest], remaining) when remaining > 0,
    do: bounded_list?(rest, remaining - 1)

  defp bounded_list?(_, _), do: false
end
