defmodule MixerHosted.Repo.Migrations.AddCustomerWorkspaceDiscovery do
  use Ecto.Migration

  def up do
    ordinary_policies(true)

    for table <- ~w(organizations projects) do
      execute("""
      ALTER TABLE public.mixer_authz_#{table} ADD COLUMN display_name text
        CHECK (display_name IS NULL OR octet_length(display_name) BETWEEN 1 AND 256)
      """)
    end

    # This is an invoker expression over the existing identity RLS. It adds no
    # privileged resolver, grant, mutation policy, or artifact authority.
    guard = """
    CASE WHEN current_setting('mixer.authz.directory_mode', true) IN ('organizations','projects')
      AND current_setting('mixer.authz.action', true) = 'workspace.read'
      AND current_setting('mixer.authz.required_scope', true) = 'mixer.workspace.read'
      AND current_setting('mixer.authz.phase', true) = 'directory'
      AND current_setting('mixer.authz.identity_class', true) = 'human'
      AND current_setting('mixer.authz.project_id', true) = ''
      AND current_setting('mixer.authz.application_id', true) = ''
      AND current_setting('mixer.authz.environment_id', true) = ''
      AND ((current_setting('mixer.authz.directory_mode', true) = 'organizations'
          AND current_setting('mixer.authz.organization_id', true) = '')
        OR (current_setting('mixer.authz.directory_mode', true) = 'projects'
          AND current_setting('mixer.authz.organization_id', true) <> ''))
    THEN EXISTS (
      SELECT 1 FROM public.mixer_authz_profiles p
      JOIN public.mixer_authz_bindings b ON b.profile_id = p.id AND b.profile_version = p.version
      JOIN public.mixer_authz_principals a ON a.id = b.principal_id
      JOIN public.mixer_authz_credentials c ON c.principal_id = a.id
        AND c.profile_id = p.id AND c.profile_version = p.version
      JOIN public.mixer_authz_families f ON f.id = c.family_id AND f.principal_id = a.id
        AND f.profile_id = p.id AND f.profile_version = p.version
      WHERE p.active AND b.active AND a.active AND c.active AND f.active
        AND p.identity_class = 'human' AND b.identity_class = 'human' AND a.identity_class = 'human'
        AND a.id = current_setting('mixer.authz.principal_id', true)
        AND f.id = current_setting('mixer.authz.family_id', true)
        AND c.reference = current_setting('mixer.authz.credential_ref', true)
        AND NULLIF(current_setting('mixer.authz.token_issued_at', true),'')::bigint
          >= GREATEST(a.not_before, c.not_before, f.not_before)
        AND NULLIF(current_setting('mixer.authz.token_issued_at', true),'')::bigint
          <= extract(epoch FROM clock_timestamp()) + 30
        AND NULLIF(current_setting('mixer.authz.token_expires_at', true),'')::bigint
          > extract(epoch FROM clock_timestamp())
        AND NULLIF(current_setting('mixer.authz.token_issued_at', true),'')::bigint
          < NULLIF(current_setting('mixer.authz.token_expires_at', true),'')::bigint
        AND a.not_before <= extract(epoch FROM clock_timestamp())
        AND c.not_before <= extract(epoch FROM clock_timestamp())
        AND f.not_before <= extract(epoch FROM clock_timestamp())
        AND (c.expires_at IS NULL OR c.expires_at > extract(epoch FROM clock_timestamp()))
        AND (f.expires_at IS NULL OR f.expires_at > extract(epoch FROM clock_timestamp()))
    ) ELSE false END
    """

    execute("""
    CREATE POLICY directory_read ON public.mixer_authz_memberships FOR SELECT USING (
      (#{guard}) AND principal_id = current_setting('mixer.authz.principal_id', true)
      AND active AND not_before <= extract(epoch FROM clock_timestamp())
      AND (expires_at IS NULL OR expires_at > extract(epoch FROM clock_timestamp()))
      AND (current_setting('mixer.authz.directory_mode', true) = 'organizations'
        OR organization_id = current_setting('mixer.authz.organization_id', true)))
    """)

    execute("""
    CREATE POLICY directory_read ON public.mixer_authz_organizations FOR SELECT USING (
      (#{guard}) AND active
      AND (current_setting('mixer.authz.directory_mode', true) = 'organizations'
        OR id = current_setting('mixer.authz.organization_id', true))
      AND EXISTS (SELECT 1 FROM public.mixer_authz_memberships m
        WHERE m.organization_id = mixer_authz_organizations.id
          AND m.principal_id = current_setting('mixer.authz.principal_id', true)
          AND m.active AND m.not_before <= extract(epoch FROM clock_timestamp())
          AND (m.expires_at IS NULL OR m.expires_at > extract(epoch FROM clock_timestamp()))))
    """)

    execute("""
    CREATE POLICY directory_read ON public.mixer_authz_projects FOR SELECT USING (
      (#{guard}) AND current_setting('mixer.authz.directory_mode', true) = 'projects'
      AND organization_id = current_setting('mixer.authz.organization_id', true) AND active
      AND EXISTS (SELECT 1 FROM public.mixer_authz_organizations o
        WHERE o.id = mixer_authz_projects.organization_id AND o.active)
      AND EXISTS (SELECT 1 FROM public.mixer_authz_memberships m
        WHERE m.organization_id = mixer_authz_projects.organization_id
          AND m.principal_id = current_setting('mixer.authz.principal_id', true)
          AND ((m.project_binding = 'all_projects' AND m.project_id IS NULL)
            OR (m.project_binding = 'exact_project' AND m.project_id = mixer_authz_projects.id))
          AND m.active AND m.not_before <= extract(epoch FROM clock_timestamp())
          AND (m.expires_at IS NULL OR m.expires_at > extract(epoch FROM clock_timestamp()))))
    """)
  end

  def down do
    for table <- ~w(projects organizations memberships),
        do: execute("DROP POLICY directory_read ON public.mixer_authz_#{table}")

    for table <- ~w(projects organizations),
        do: execute("ALTER TABLE public.mixer_authz_#{table} DROP COLUMN display_name")

    ordinary_policies(false)
  end

  defp ordinary_policies(directory_guard?) do
    linked = """
    EXISTS (SELECT 1 FROM public.mixer_authz_bindings b
      WHERE b.principal_id = current_setting('mixer.authz.principal_id', true))
    """

    actor = "principal_id = current_setting('mixer.authz.principal_id', true) AND (#{linked})"
    organization = "organization_id = current_setting('mixer.authz.organization_id', true)"
    project = "project_id = current_setting('mixer.authz.project_id', true)"

    visible = """
    EXISTS (SELECT 1 FROM public.mixer_authz_memberships m
      WHERE m.principal_id = current_setting('mixer.authz.principal_id', true)
        AND m.organization_id = current_setting('mixer.authz.organization_id', true)
        AND ((m.project_binding = 'all_projects' AND m.project_id IS NULL)
          OR (m.project_binding = 'exact_project' AND m.project_id = current_setting('mixer.authz.project_id', true)))
        AND m.active AND m.not_before <= extract(epoch FROM statement_timestamp())
        AND (m.expires_at IS NULL OR m.expires_at > extract(epoch FROM statement_timestamp())))
    """

    guard =
      if directory_guard?,
        do: "COALESCE(current_setting('mixer.authz.directory_mode', true),'') = '' AND ",
        else: ""

    for {table, predicate} <- [
          {"memberships", "#{actor} AND #{organization} AND (project_id IS NULL OR #{project})"},
          {"organizations",
           "id = current_setting('mixer.authz.organization_id', true) AND (#{visible})"},
          {"projects",
           "#{organization} AND id = current_setting('mixer.authz.project_id', true) AND (#{visible})"}
        ] do
      execute(
        "ALTER POLICY scoped_read ON public.mixer_authz_#{table} USING (#{guard}(#{predicate}))"
      )
    end
  end
end
