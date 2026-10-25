defmodule MixerHosted.Authorization.Transaction.Snapshot do
  @moduledoc """
  Closed, bounded audit data from the locked authorization rows.

  This data is not authority. `issued_at` and `expires_at` describe the verified
  access token, never an authentication event. Subject linkage is represented by
  SHA-256 of the exact subject within its profile/version namespace. The request
  ID is generated here and has no relationship to a caller's HTTP request ID.
  """

  alias MixerHosted.Authorization.{Policy, Scope}
  alias MixerHosted.Authorization.Postgres.Session
  alias MixerHosted.Identity.Encoding

  @maximum 9_007_199_254_740_991
  @roles ~w(owner administrator developer release_manager billing_manager viewer)
  @fields [
    :request_id,
    :profile,
    :binding,
    :principal,
    :credential,
    :family,
    :memberships,
    :organization_head,
    :project_head,
    :identity,
    :action,
    :target,
    :checked_at
  ]

  @doc false
  def load!(repo, identity, evidence, linkage, decision, now) do
    [id, version, issuer, client, identity_class, active, state_revision] =
      Session.one!(
        repo,
        "SELECT id, version, issuer, client_id, identity_class, active, state_revision FROM public.mixer_authz_profiles",
        [],
        :unauthenticated
      )

    [
      profile,
      profile_version,
      subject,
      binding_class,
      principal,
      binding_active,
      binding_revision
    ] =
      Session.one!(
        repo,
        "SELECT profile_id, profile_version, subject, identity_class, principal_id, active, revision FROM public.mixer_authz_bindings",
        [],
        :unauthenticated
      )

    [cp, cv, reference, credential_principal, family_id, ca, cs, ce, cr] =
      Session.one!(
        repo,
        "SELECT profile_id, profile_version, reference, principal_id, family_id, active, not_before, expires_at, revision FROM public.mixer_authz_credentials",
        [],
        :unauthenticated
      )

    [fid, fp, fv, family_principal, fa, fs, fe, fr] =
      Session.one!(
        repo,
        "SELECT id, profile_id, profile_version, principal_id, active, not_before, expires_at, revision FROM public.mixer_authz_families",
        [],
        :unauthenticated
      )

    snapshot = %{
      request_id: Base.encode16(:crypto.strong_rand_bytes(16), case: :lower),
      profile: %{
        id: id,
        version: version,
        issuer: issuer,
        client_id: client,
        identity_class: identity_class,
        active: active,
        state_revision: state_revision
      },
      binding: %{
        profile_id: profile,
        profile_version: profile_version,
        subject_digest: digest(subject),
        identity_class: binding_class,
        principal_id: principal,
        active: binding_active,
        revision: binding_revision
      },
      principal: evidence.principal,
      credential: %{
        profile_id: cp,
        profile_version: cv,
        reference: reference,
        principal_id: credential_principal,
        family_id: family_id,
        active: ca,
        not_before: cs,
        expires_at: ce,
        revision: cr
      },
      family: %{
        id: fid,
        profile_id: fp,
        profile_version: fv,
        principal_id: family_principal,
        active: fa,
        not_before: fs,
        expires_at: fe,
        revision: fr
      },
      memberships:
        evidence.memberships
        |> Enum.filter(&(&1.id in decision.membership_ids))
        |> Enum.sort_by(& &1.id),
      organization_head: %{
        organization_id: decision.target.organization_id,
        revision: evidence.organization_revision
      },
      project_head: %{
        organization_id: decision.target.organization_id,
        project_id: decision.target.project_id,
        revision: evidence.project_revision
      },
      identity: identity_snapshot(identity),
      action: decision.action,
      target: decision.target,
      checked_at: now
    }

    # Verify all raw-state projections against the accepted, locked policy
    # evidence before retaining a snapshot. The policy contract stays unchanged.
    if linkage.principal_id != principal or linkage.family_id != fid or
         subject != identity.subject or evidence.profile_active != active or
         evidence.binding_active != binding_active or
         evidence.binding.principal_id != principal or
         evidence.credential.active != (ca and fa) or
         evidence.credential.not_before != max(cs, fs) or
         evidence.credential.expires_at != earliest(ce, fe) or
         not valid?(snapshot, identity, decision) do
      repo.rollback(:authorization_unavailable)
    end

    snapshot
  end

  @doc false
  def valid?(snapshot, identity, decision) do
    with true <- strict?(snapshot, @fields),
         true <- hex?(snapshot.request_id, 32),
         true <- Encoding.numeric_date?(snapshot.checked_at),
         true <-
           Policy.valid_decision?(
             decision,
             identity,
             snapshot.action,
             snapshot.target,
             snapshot.checked_at
           ),
         true <- profile?(snapshot.profile),
         true <- binding?(snapshot.binding),
         true <- principal?(snapshot.principal),
         true <- credential?(snapshot.credential),
         true <- family?(snapshot.family),
         true <- strict?(snapshot.organization_head, [:organization_id, :revision]),
         true <- strict?(snapshot.project_head, [:organization_id, :project_id, :revision]),
         true <-
           strict?(snapshot.identity, [
             :profile_id,
             :profile_version,
             :issuer,
             :subject_digest,
             :client_id,
             :credential_ref,
             :identity_class,
             :issued_at,
             :expires_at,
             :scopes
           ]),
         true <- snapshot.identity === identity_snapshot(identity),
         true <- bounded_list?(snapshot.memberships, 64),
         true <- Enum.all?(snapshot.memberships, &membership?/1),
         true <- Enum.map(snapshot.memberships, & &1.id) === decision.membership_ids,
         true <-
           Enum.all?(
             snapshot.memberships,
             &(&1.principal_id == snapshot.principal.id and
                 Scope.membership_covers?(&1, snapshot.target))
           ),
         true <-
           Enum.sort(Enum.uniq(Enum.map(snapshot.memberships, & &1.role))) === decision.roles,
         true <- projections?(snapshot, identity, decision) do
      true
    else
      _ -> false
    end
  rescue
    _ -> false
  catch
    _, _ -> false
  end

  defp projections?(s, i, d) do
    p = s.profile
    b = s.binding
    c = s.credential
    f = s.family

    p.id == i.profile_id and p.version == i.profile_version and p.issuer == i.issuer and
      p.client_id == i.client_id and p.identity_class == "human" and p.active and
      b.profile_id == p.id and b.profile_version == p.version and
      b.subject_digest == digest(i.subject) and
      b.identity_class == p.identity_class and b.principal_id == s.principal.id and b.active and
      s.principal.id == d.principal_id and s.principal.identity_class == :human and
      s.principal.active and
      s.principal.revision == d.principal_revision and s.principal.not_before <= i.issued_at and
      c.profile_id == p.id and c.profile_version == p.version and c.reference == i.credential_ref and
      c.principal_id == s.principal.id and c.family_id == f.id and c.active and
      c.revision == d.credential_revision and f.profile_id == p.id and
      f.profile_version == p.version and
      f.principal_id == s.principal.id and f.active and live?(c, i, s.checked_at) and
      live?(f, i, s.checked_at) and
      Enum.all?(s.memberships, &(&1.active and live?(&1, nil, s.checked_at))) and
      s.organization_head.organization_id == s.target.organization_id and
      s.organization_head.revision == d.organization_revision and
      revision?(s.organization_head.revision) and
      s.project_head.organization_id == s.target.organization_id and
      s.project_head.project_id == s.target.project_id and
      s.project_head.revision == d.project_revision and revision?(s.project_head.revision)
  end

  defp profile?(p) do
    strict?(p, [:id, :version, :issuer, :client_id, :identity_class, :active, :state_revision]) and
      Encoding.bounded_string?(p.id, 128) and version?(p.version) and
      Encoding.bounded_string?(p.issuer, 2048) and Encoding.bounded_string?(p.client_id, 256) and
      p.identity_class in ["human", "service"] and is_boolean(p.active) and
      revision?(p.state_revision)
  end

  defp binding?(b) do
    strict?(b, [
      :profile_id,
      :profile_version,
      :subject_digest,
      :identity_class,
      :principal_id,
      :active,
      :revision
    ]) and
      Encoding.bounded_string?(b.profile_id, 128) and version?(b.profile_version) and
      hex?(b.subject_digest, 64) and b.identity_class in ["human", "service"] and
      Scope.identifier?(b.principal_id) and is_boolean(b.active) and revision?(b.revision)
  end

  defp principal?(p) do
    strict?(p, [:id, :identity_class, :active, :not_before, :revision]) and
      Scope.identifier?(p.id) and
      p.identity_class in [:human, :service] and is_boolean(p.active) and
      Encoding.numeric_date?(p.not_before) and revision?(p.revision)
  end

  defp credential?(c) do
    strict?(c, [
      :profile_id,
      :profile_version,
      :reference,
      :principal_id,
      :family_id,
      :active,
      :not_before,
      :expires_at,
      :revision
    ]) and
      Encoding.bounded_string?(c.profile_id, 128) and version?(c.profile_version) and
      Encoding.bounded_string?(c.reference, 256) and Scope.identifier?(c.principal_id) and
      Scope.identifier?(c.family_id) and state?(c)
  end

  defp family?(f) do
    strict?(f, [
      :id,
      :profile_id,
      :profile_version,
      :principal_id,
      :active,
      :not_before,
      :expires_at,
      :revision
    ]) and
      Scope.identifier?(f.id) and Encoding.bounded_string?(f.profile_id, 128) and
      version?(f.profile_version) and Scope.identifier?(f.principal_id) and state?(f)
  end

  defp membership?(m) do
    with true <-
           strict?(m, [
             :id,
             :principal_id,
             :role,
             :scope,
             :project_binding,
             :active,
             :not_before,
             :expires_at,
             :revision
           ]),
         true <- Scope.identifier?(m.id) and Scope.identifier?(m.principal_id),
         true <- m.role in @roles and state?(m),
         {:ok, scope} <- Scope.new(m.scope) do
      (is_nil(scope.project_id) and m.project_binding == :all_projects) or
        (Scope.project_only?(scope) and m.project_binding == :exact_project)
    else
      _ -> false
    end
  end

  defp identity_snapshot(i) do
    i |> Map.from_struct() |> Map.delete(:subject) |> Map.put(:subject_digest, digest(i.subject))
  end

  defp state?(v),
    do: is_boolean(v.active) and window?(v.not_before, v.expires_at) and revision?(v.revision)

  defp window?(s, nil), do: Encoding.numeric_date?(s)
  defp window?(s, e), do: Encoding.numeric_date?(s) and Encoding.numeric_date?(e) and s < e

  defp live?(v, i, now),
    do:
      v.not_before <= now and (is_nil(v.expires_at) or now < v.expires_at) and
        (is_nil(i) or v.not_before <= i.issued_at)

  defp revision?(v), do: is_integer(v) and v in 1..@maximum
  defp version?(v), do: is_integer(v) and v in 1..2_147_483_647

  defp strict?(v, fields) when is_map(v) and not is_struct(v),
    do: map_size(v) == length(fields) and Enum.all?(fields, &Map.has_key?(v, &1))

  defp strict?(_, _), do: false
  defp bounded_list?([], _), do: true

  defp bounded_list?([_ | rest], remaining) when remaining > 0,
    do: bounded_list?(rest, remaining - 1)

  defp bounded_list?(_, _), do: false

  defp hex?(v, n) when is_binary(v) and byte_size(v) == n,
    do: Enum.all?(:binary.bin_to_list(v), &(&1 in ?0..?9 or &1 in ?a..?f))

  defp hex?(_, _), do: false
  defp digest(subject), do: :crypto.hash(:sha256, subject) |> Base.encode16(case: :lower)
  defp earliest(nil, b), do: b
  defp earliest(a, nil), do: a
  defp earliest(a, b), do: min(a, b)
end
