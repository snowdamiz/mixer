defmodule MixerHosted.Repo.Migrations.AddCustomerAuthorization do
  use Ecto.Migration

  @tables ~w(profiles principals bindings families credentials organizations projects applications environments organization_heads project_heads memberships)

  def up do
    statements("""
    CREATE TABLE public.mixer_authz_profiles (
      id text NOT NULL CHECK (octet_length(id) BETWEEN 1 AND 128),
      version integer NOT NULL CHECK (version > 0),
      issuer text NOT NULL CHECK (octet_length(issuer) BETWEEN 1 AND 2048),
      client_id text NOT NULL CHECK (octet_length(client_id) BETWEEN 1 AND 256),
      identity_class text NOT NULL CHECK (identity_class IN ('human','service')),
      active boolean NOT NULL,
      PRIMARY KEY (id, version), UNIQUE (id, version, identity_class)
    );
    CREATE TABLE public.mixer_authz_principals (
      id text PRIMARY KEY CHECK (octet_length(id) BETWEEN 1 AND 128),
      identity_class text NOT NULL CHECK (identity_class IN ('human','service')),
      active boolean NOT NULL,
      not_before bigint NOT NULL CHECK (not_before BETWEEN 0 AND 9007199254740991),
      revision bigint NOT NULL CHECK (revision BETWEEN 1 AND 9007199254740991),
      UNIQUE (id, identity_class)
    );
    CREATE TABLE public.mixer_authz_bindings (
      profile_id text NOT NULL, profile_version integer NOT NULL,
      subject text NOT NULL CHECK (octet_length(subject) BETWEEN 1 AND 256),
      identity_class text NOT NULL, principal_id text NOT NULL,
      active boolean NOT NULL,
      PRIMARY KEY (profile_id, profile_version, subject),
      FOREIGN KEY (profile_id, profile_version, identity_class)
        REFERENCES public.mixer_authz_profiles(id, version, identity_class),
      FOREIGN KEY (principal_id, identity_class)
        REFERENCES public.mixer_authz_principals(id, identity_class)
    );
    CREATE TABLE public.mixer_authz_families (
      id text PRIMARY KEY CHECK (octet_length(id) BETWEEN 1 AND 128),
      profile_id text NOT NULL, profile_version integer NOT NULL,
      principal_id text NOT NULL REFERENCES public.mixer_authz_principals(id),
      active boolean NOT NULL,
      not_before bigint NOT NULL CHECK (not_before BETWEEN 0 AND 9007199254740991),
      expires_at bigint CHECK (expires_at BETWEEN 0 AND 9007199254740991 AND expires_at > not_before),
      revision bigint NOT NULL CHECK (revision BETWEEN 1 AND 9007199254740991),
      FOREIGN KEY (profile_id, profile_version) REFERENCES public.mixer_authz_profiles(id, version),
      UNIQUE (id, profile_id, profile_version, principal_id)
    );
    CREATE TABLE public.mixer_authz_credentials (
      profile_id text NOT NULL, profile_version integer NOT NULL,
      reference text NOT NULL CHECK (octet_length(reference) BETWEEN 1 AND 256),
      principal_id text NOT NULL, family_id text NOT NULL,
      active boolean NOT NULL,
      not_before bigint NOT NULL CHECK (not_before BETWEEN 0 AND 9007199254740991),
      expires_at bigint CHECK (expires_at BETWEEN 0 AND 9007199254740991 AND expires_at > not_before),
      revision bigint NOT NULL CHECK (revision BETWEEN 1 AND 9007199254740991),
      PRIMARY KEY (profile_id, profile_version, reference),
      FOREIGN KEY (family_id, profile_id, profile_version, principal_id)
        REFERENCES public.mixer_authz_families(id, profile_id, profile_version, principal_id)
    );
    CREATE TABLE public.mixer_authz_organizations (
      id text PRIMARY KEY CHECK (octet_length(id) BETWEEN 1 AND 128 AND id <> '*'),
      active boolean NOT NULL
    );
    CREATE TABLE public.mixer_authz_projects (
      organization_id text NOT NULL REFERENCES public.mixer_authz_organizations(id),
      id text NOT NULL CHECK (octet_length(id) BETWEEN 1 AND 128 AND id <> '*'),
      active boolean NOT NULL, PRIMARY KEY (organization_id, id)
    );
    CREATE TABLE public.mixer_authz_applications (
      organization_id text NOT NULL, project_id text NOT NULL,
      id text NOT NULL CHECK (octet_length(id) BETWEEN 1 AND 128 AND id <> '*'),
      active boolean NOT NULL, PRIMARY KEY (organization_id, project_id, id),
      FOREIGN KEY (organization_id, project_id) REFERENCES public.mixer_authz_projects(organization_id, id)
    );
    CREATE TABLE public.mixer_authz_environments (
      organization_id text NOT NULL, project_id text NOT NULL, application_id text NOT NULL,
      id text NOT NULL CHECK (octet_length(id) BETWEEN 1 AND 128 AND id <> '*'),
      active boolean NOT NULL, PRIMARY KEY (organization_id, project_id, application_id, id),
      FOREIGN KEY (organization_id, project_id, application_id)
        REFERENCES public.mixer_authz_applications(organization_id, project_id, id)
    );
    CREATE TABLE public.mixer_authz_organization_heads (
      organization_id text PRIMARY KEY REFERENCES public.mixer_authz_organizations(id),
      revision bigint NOT NULL CHECK (revision BETWEEN 1 AND 9007199254740991)
    );
    CREATE TABLE public.mixer_authz_project_heads (
      organization_id text NOT NULL, project_id text NOT NULL,
      revision bigint NOT NULL CHECK (revision BETWEEN 1 AND 9007199254740991),
      PRIMARY KEY (organization_id, project_id),
      FOREIGN KEY (organization_id, project_id) REFERENCES public.mixer_authz_projects(organization_id, id)
    );
    CREATE TABLE public.mixer_authz_memberships (
      id text PRIMARY KEY CHECK (octet_length(id) BETWEEN 1 AND 128 AND id <> '*'),
      principal_id text NOT NULL REFERENCES public.mixer_authz_principals(id),
      organization_id text NOT NULL REFERENCES public.mixer_authz_organizations(id),
      project_id text,
      project_binding text NOT NULL,
      role text NOT NULL CHECK (role IN ('owner','administrator','developer','release_manager','billing_manager','viewer')),
      active boolean NOT NULL,
      not_before bigint NOT NULL CHECK (not_before BETWEEN 0 AND 9007199254740991),
      expires_at bigint CHECK (expires_at BETWEEN 0 AND 9007199254740991 AND expires_at > not_before),
      revision bigint NOT NULL CHECK (revision BETWEEN 1 AND 9007199254740991),
      FOREIGN KEY (organization_id, project_id) REFERENCES public.mixer_authz_projects(organization_id, id),
      CHECK ((project_binding IN ('organization_only','all_projects') AND project_id IS NULL)
        OR (project_binding = 'exact_project' AND project_id IS NOT NULL))
    );
    CREATE INDEX mixer_authz_memberships_lookup
      ON public.mixer_authz_memberships(principal_id, organization_id, project_id, project_binding, id);
    """)

    for table <- @tables do
      execute("ALTER TABLE public.mixer_authz_#{table} ENABLE ROW LEVEL SECURITY")
      execute("ALTER TABLE public.mixer_authz_#{table} FORCE ROW LEVEL SECURITY")
      execute("REVOKE ALL ON public.mixer_authz_#{table} FROM PUBLIC")
    end

    profile = """
    id = current_setting('mixer.authz.profile_id', true)
    AND version::text = current_setting('mixer.authz.profile_version', true)
    AND issuer = current_setting('mixer.authz.issuer', true)
    AND client_id = current_setting('mixer.authz.client_id', true)
    AND identity_class = current_setting('mixer.authz.identity_class', true)
    """

    binding = """
    profile_id = current_setting('mixer.authz.profile_id', true)
    AND profile_version::text = current_setting('mixer.authz.profile_version', true)
    AND subject = current_setting('mixer.authz.subject', true)
    AND identity_class = current_setting('mixer.authz.identity_class', true)
    AND EXISTS (SELECT 1 FROM public.mixer_authz_profiles p
      WHERE p.id = profile_id AND p.version = profile_version)
    """

    linked = """
    EXISTS (SELECT 1 FROM public.mixer_authz_bindings b
      WHERE b.principal_id = current_setting('mixer.authz.principal_id', true))
    """

    actor = "principal_id = current_setting('mixer.authz.principal_id', true) AND (#{linked})"
    organization = "organization_id = current_setting('mixer.authz.organization_id', true)"
    project = "project_id = current_setting('mixer.authz.project_id', true)"

    policy("profiles", profile)
    policy("bindings", binding)
    policy("principals", "id = current_setting('mixer.authz.principal_id', true) AND (#{linked})")

    policy(
      "families",
      "#{actor} AND profile_id = current_setting('mixer.authz.profile_id', true) AND profile_version::text = current_setting('mixer.authz.profile_version', true) AND id = current_setting('mixer.authz.family_id', true)"
    )

    policy(
      "credentials",
      "#{actor} AND profile_id = current_setting('mixer.authz.profile_id', true) AND profile_version::text = current_setting('mixer.authz.profile_version', true) AND reference = current_setting('mixer.authz.credential_ref', true)"
    )

    policy("memberships", "#{actor} AND #{organization} AND (project_id IS NULL OR #{project})")
    policy("organization_heads", "#{organization} AND (#{linked})")
    policy("project_heads", "#{organization} AND #{project} AND (#{linked})")

    visible = """
    EXISTS (SELECT 1 FROM public.mixer_authz_memberships m
      WHERE m.principal_id = current_setting('mixer.authz.principal_id', true)
        AND m.organization_id = current_setting('mixer.authz.organization_id', true)
        AND ((m.project_binding = 'all_projects' AND m.project_id IS NULL)
          OR (m.project_binding = 'exact_project' AND m.project_id = current_setting('mixer.authz.project_id', true)))
        AND m.active AND m.not_before <= extract(epoch FROM statement_timestamp())
        AND (m.expires_at IS NULL OR m.expires_at > extract(epoch FROM statement_timestamp())))
    """

    policy(
      "organizations",
      "id = current_setting('mixer.authz.organization_id', true) AND (#{visible})"
    )

    policy(
      "projects",
      "#{organization} AND id = current_setting('mixer.authz.project_id', true) AND (#{visible})"
    )

    policy(
      "applications",
      "#{organization} AND #{project} AND id = current_setting('mixer.authz.application_id', true) AND (#{visible})"
    )

    policy(
      "environments",
      "#{organization} AND #{project} AND application_id = current_setting('mixer.authz.application_id', true) AND id = current_setting('mixer.authz.environment_id', true) AND (#{visible})"
    )

    # FOR SHARE needs UPDATE privilege. Only these fixed SQL helpers have it;
    # the runtime receives EXECUTE, never UPDATE on an authorization table.
    for {table, predicate} <- [
          {"profiles",
           "id = current_setting('mixer.authz.profile_id', true) AND version::text = current_setting('mixer.authz.profile_version', true)"},
          {"principals", "id = current_setting('mixer.authz.principal_id', true)"},
          {"families", "id = current_setting('mixer.authz.family_id', true)"},
          {"credentials",
           "profile_id = current_setting('mixer.authz.profile_id', true) AND profile_version::text = current_setting('mixer.authz.profile_version', true) AND reference = current_setting('mixer.authz.credential_ref', true)"},
          {"organization_heads", organization},
          {"project_heads", "#{organization} AND #{project}"}
        ] do
      execute("""
      CREATE FUNCTION public.mixer_authz_lock_#{table}() RETURNS boolean
      LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog AS $lock$
      BEGIN
        PERFORM 1 FROM public.mixer_authz_#{table} WHERE #{predicate} FOR SHARE;
        RETURN FOUND;
      END
      $lock$;
      """)

      execute("REVOKE ALL ON FUNCTION public.mixer_authz_lock_#{table}() FROM PUBLIC")
    end
  end

  def down do
    for table <- ~w(profiles principals families credentials organization_heads project_heads) do
      execute("DROP FUNCTION public.mixer_authz_lock_#{table}()")
    end

    for table <- Enum.reverse(@tables) do
      execute("DROP TABLE public.mixer_authz_#{table}")
    end
  end

  defp policy(table, predicate) do
    execute(
      "CREATE POLICY scoped_read ON public.mixer_authz_#{table} FOR SELECT USING (#{predicate})"
    )

    # PostgreSQL row-locking SELECT also applies UPDATE USING policies. Permit
    # only the same scoped row to be locked; WITH CHECK false forbids updates.
    execute(
      "CREATE POLICY scoped_lock ON public.mixer_authz_#{table} FOR UPDATE USING (#{predicate}) WITH CHECK (false)"
    )
  end

  defp statements(sql) do
    sql |> String.split(";", trim: true) |> Enum.each(&execute/1)
  end
end
