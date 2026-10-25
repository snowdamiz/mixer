defmodule MixerHosted.Authorization.Postgres.Evidence do
  @moduledoc false

  alias MixerHosted.Authorization.{Scope, Postgres.Session}

  def load!(repo, lookup, linkage) do
    # Every state query is a separate READ COMMITTED statement after the final
    # lock wait. Never use a pre-lock snapshot as current authorization evidence.
    i = lookup.identity

    [profile_active, issuer, client, identity_class] =
      Session.one!(
        repo,
        "SELECT active, issuer, client_id, identity_class FROM public.mixer_authz_profiles",
        [],
        :unauthenticated
      )

    [principal_id, binding_active] =
      Session.one!(
        repo,
        "SELECT principal_id, active FROM public.mixer_authz_bindings",
        [],
        :unauthenticated
      )

    [id, principal_class, active, not_before, revision] =
      Session.one!(
        repo,
        "SELECT id, identity_class, active, not_before, revision FROM public.mixer_authz_principals",
        [],
        :unauthenticated
      )

    [
      reference,
      credential_principal,
      family_id,
      credential_active,
      credential_start,
      credential_end,
      credential_revision
    ] =
      Session.one!(
        repo,
        "SELECT reference, principal_id, family_id, active, not_before, expires_at, revision FROM public.mixer_authz_credentials",
        [],
        :unauthenticated
      )

    [family_principal, family_active, family_start, family_end] =
      Session.one!(
        repo,
        "SELECT principal_id, active, not_before, expires_at FROM public.mixer_authz_families",
        [],
        :unauthenticated
      )

    if principal_id != linkage.principal_id or id != principal_id or
         credential_principal != principal_id or family_principal != principal_id or
         family_id != linkage.family_id or reference != i.credential_ref or
         issuer != i.issuer or client != i.client_id or identity_class != "human" or
         principal_class != "human" do
      repo.rollback(:unauthenticated)
    end

    [organization_revision] =
      Session.one!(
        repo,
        "SELECT revision FROM public.mixer_authz_organization_heads",
        [],
        :not_found
      )

    [project_revision] =
      Session.one!(repo, "SELECT revision FROM public.mixer_authz_project_heads", [], :not_found)

    memberships = memberships!(repo, lookup.target, principal_id)

    %{
      binding: %{
        profile_id: i.profile_id,
        profile_version: i.profile_version,
        issuer: issuer,
        subject: i.subject,
        client_id: client,
        identity_class: :human,
        principal_id: principal_id
      },
      binding_active: binding_active,
      profile_active: profile_active,
      principal: %{
        id: id,
        identity_class: :human,
        active: active,
        not_before: not_before,
        revision: revision
      },
      credential: %{
        reference: reference,
        principal_id: principal_id,
        active: credential_active and family_active,
        not_before: max(credential_start, family_start),
        expires_at: earliest(credential_end, family_end),
        revision: credential_revision
      },
      target: target!(repo, lookup.target),
      memberships: memberships,
      organization_revision: organization_revision,
      project_revision: project_revision
    }
  end

  defp memberships!(repo, target, principal) do
    rows =
      Session.query!(
        repo,
        """
        SELECT id, principal_id, role, organization_id, project_id, project_binding,
          active, not_before, expires_at, revision
        FROM public.mixer_authz_memberships
        WHERE principal_id = $1 AND organization_id = $2
          AND ((project_id IS NULL AND project_binding = 'all_projects')
            OR (project_id = $3 AND project_binding = 'exact_project'))
        ORDER BY id LIMIT 65
        """,
        [principal, target.organization_id, target.project_id]
      ).rows

    if length(rows) > 64, do: repo.rollback(:authorization_unavailable)

    Enum.map(rows, fn [
                        id,
                        principal_id,
                        role,
                        organization,
                        project,
                        binding,
                        active,
                        start,
                        finish,
                        revision
                      ] ->
      %{
        id: id,
        principal_id: principal_id,
        role: role,
        scope: %Scope{organization_id: organization, project_id: project},
        project_binding: project_binding(binding),
        active: active,
        not_before: start,
        expires_at: finish,
        revision: revision
      }
    end)
  end

  defp target!(repo, %Scope{application_id: nil} = target) do
    [organization, project, organization_active, project_active] =
      Session.one!(
        repo,
        """
        SELECT o.id, p.id, o.active, p.active
        FROM public.mixer_authz_projects p
        JOIN public.mixer_authz_organizations o ON o.id = p.organization_id
        WHERE p.organization_id = $1 AND p.id = $2
        """,
        [target.organization_id, target.project_id],
        :not_found
      )

    %{
      scope: %Scope{organization_id: organization, project_id: project},
      active: organization_active and project_active
    }
  end

  defp target!(repo, target) do
    [organization, project, application, environment, oa, pa, aa, ea] =
      Session.one!(
        repo,
        """
        SELECT o.id, p.id, a.id, e.id, o.active, p.active, a.active, e.active
        FROM public.mixer_authz_environments e
        JOIN public.mixer_authz_applications a ON (a.organization_id, a.project_id, a.id) =
          (e.organization_id, e.project_id, e.application_id)
        JOIN public.mixer_authz_projects p ON (p.organization_id, p.id) = (a.organization_id, a.project_id)
        JOIN public.mixer_authz_organizations o ON o.id = p.organization_id
        WHERE e.organization_id = $1 AND e.project_id = $2 AND e.application_id = $3 AND e.id = $4
        """,
        [target.organization_id, target.project_id, target.application_id, target.environment_id],
        :not_found
      )

    %{
      scope: %Scope{
        organization_id: organization,
        project_id: project,
        application_id: application,
        environment_id: environment
      },
      active: oa and pa and aa and ea
    }
  end

  defp earliest(nil, finish), do: finish
  defp earliest(start, nil), do: start
  defp earliest(a, b), do: min(a, b)
  defp project_binding("all_projects"), do: :all_projects
  defp project_binding("exact_project"), do: :exact_project
end
