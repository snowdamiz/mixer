defmodule MixerHosted.CustomerWorkspace.SelfServiceSchema do
  @moduledoc "Explicit workspace lifecycle installation. Runtime receives EXECUTE and no authz DML."
  @writer "mixer_workspace_writer"
  @usage_signature "public.mixer_workspace_build_count_v1(text)"
  @signature "text,text,text,jsonb,bigint,bigint"
  def writer, do: @writer

  def role_statements do
    [
      """
      DO $role$ BEGIN
        IF NOT EXISTS (SELECT 1 FROM pg_catalog.pg_roles WHERE rolname='#{@writer}') THEN
          CREATE ROLE #{@writer} NOLOGIN NOSUPERUSER NOBYPASSRLS NOINHERIT NOCREATEDB NOCREATEROLE NOREPLICATION;
        END IF;
        IF NOT EXISTS (SELECT 1 FROM pg_catalog.pg_roles WHERE rolname='#{@writer}'
          AND NOT rolcanlogin AND NOT rolsuper AND NOT rolbypassrls AND NOT rolinherit
          AND NOT rolcreatedb AND NOT rolcreaterole AND NOT rolreplication)
          OR EXISTS (SELECT 1 FROM pg_catalog.pg_auth_members m JOIN pg_catalog.pg_roles r ON r.oid=m.member OR r.oid=m.roleid WHERE r.rolname='#{@writer}') THEN
          RAISE EXCEPTION 'unsafe workspace writer role';
        END IF;
      END $role$
      """
    ]
  end

  @tenant_tables ~w(organizations projects organization_heads project_heads memberships)
  @identity_tables ~w(profiles principals bindings families credentials)
  @build_create_tables ~w(mixer_build_organization_capacities mixer_build_capacities)
  @build_read_tables ~w(mixer_build_reservations)
  def identity_tables, do: @identity_tables
  def tenant_tables, do: @tenant_tables
  def build_create_tables, do: @build_create_tables
  def build_read_tables, do: @build_read_tables

  defp tenant_write_grants(action) do
    for {table, columns} <- tenant_update_columns() do
      columns = Enum.join(columns, ", ")

      case action do
        :grant -> "GRANT UPDATE (#{columns}) ON public.mixer_authz_#{table} TO #{@writer}"
        :revoke -> "REVOKE UPDATE (#{columns}) ON public.mixer_authz_#{table} FROM #{@writer}"
      end
    end
  end

  def tenant_update_columns do
    [
      {"projects", ~w(active)},
      {"organization_heads", ~w(revision)},
      {"project_heads", ~w(revision)},
      {"memberships", ~w(role active not_before expires_at revision)}
    ]
  end

  def statements do
    [
      """
      CREATE FUNCTION public.mixer_workspace_build_count_v1(target text)
      RETURNS bigint LANGUAGE sql SECURITY DEFINER SET search_path=pg_catalog
      AS $count$#{build_count_body()}$count$
      """,
      "REVOKE ALL ON FUNCTION #{@usage_signature} FROM PUBLIC",
      function(),
      "REVOKE ALL ON FUNCTION public.mixer_workspace_self_service_v1(#{@signature}) FROM PUBLIC"
    ]
  end

  @doc "Run the migration rollback as an operator authorized to drop the provisioned function."
  def rollback_statements do
    [
      "DROP FUNCTION public.mixer_workspace_self_service_v1(#{@signature})",
      "DROP FUNCTION #{@usage_signature}",
      """
      DO $rollback$ BEGIN
        IF EXISTS (SELECT 1 FROM pg_catalog.pg_roles WHERE rolname='#{@writer}') THEN
          REVOKE SELECT, INSERT ON #{relations(@tenant_tables)} FROM #{@writer};
          REVOKE SELECT ON #{relations(@identity_tables)} FROM #{@writer};
          REVOKE UPDATE (revision) ON public.mixer_authz_principals FROM #{@writer};
          REVOKE SELECT, INSERT ON public.mixer_build_organization_capacities,
            public.mixer_build_capacities FROM #{@writer};
          REVOKE SELECT ON public.mixer_build_reservations FROM #{@writer};
          #{Enum.map_join(tenant_write_grants(:revoke), ";\n", & &1)};
          REVOKE USAGE ON SCHEMA public FROM #{@writer};
        END IF;
      END $rollback$
      """
    ] ++
      Enum.map(
        @tenant_tables,
        &"DROP POLICY IF EXISTS workspace_self_service ON public.mixer_authz_#{&1}"
      ) ++
      [
        "DROP POLICY IF EXISTS workspace_member_read ON public.mixer_authz_principals",
        "DROP POLICY IF EXISTS workspace_member_lock ON public.mixer_authz_principals"
      ]
  end

  @doc "Provision the migrated function transactionally as the database operator."
  def provisioning_statements(runtime) do
    unless is_binary(runtime) and Regex.match?(~r/^[a-z][a-z0-9_]{0,62}$/, runtime) and
             not String.starts_with?(runtime, "pg_") and runtime != @writer do
      raise ArgumentError, "invalid runtime role"
    end

    quoted_runtime = ~s("#{runtime}")

    policies =
      for table <- @tenant_tables do
        column = if table == "organizations", do: "id", else: "organization_id"
        predicate = "#{column} = current_setting('mixer.authz.organization_id',true)"

        "CREATE POLICY workspace_self_service ON public.mixer_authz_#{table} TO #{@writer} USING (#{predicate}) WITH CHECK (#{predicate})"
      end

    target = "id = current_setting('mixer.workspace.member_id',true) AND identity_class = 'human'"

    ["BEGIN"] ++
      role_statements() ++
      [
        """
        DO $runtime$ BEGIN
          IF NOT EXISTS (SELECT 1 FROM pg_catalog.pg_roles WHERE rolname='#{runtime}'
            AND rolcanlogin AND NOT rolsuper AND NOT rolbypassrls AND NOT rolcreaterole
            AND NOT rolcreatedb AND NOT rolreplication) THEN
            RAISE EXCEPTION 'unsafe workspace runtime role';
          END IF;
        END $runtime$
        """,
        "GRANT USAGE, CREATE ON SCHEMA public TO #{@writer}",
        "GRANT SELECT, INSERT ON #{relations(@tenant_tables)} TO #{@writer}",
        "GRANT SELECT ON #{relations(@identity_tables)} TO #{@writer}",
        "GRANT UPDATE (revision) ON public.mixer_authz_principals TO #{@writer}",
        "GRANT SELECT, INSERT ON public.mixer_build_organization_capacities, public.mixer_build_capacities TO #{@writer}",
        "GRANT SELECT ON public.mixer_build_reservations TO #{@writer}",
        "CREATE POLICY workspace_member_read ON public.mixer_authz_principals FOR SELECT TO #{@writer} USING (#{target})",
        "CREATE POLICY workspace_member_lock ON public.mixer_authz_principals FOR UPDATE TO #{@writer} USING (#{target}) WITH CHECK (false)"
      ] ++
      tenant_write_grants(:grant) ++
      policies ++
      [
        "GRANT EXECUTE ON FUNCTION #{@usage_signature} TO #{@writer}",
        "ALTER FUNCTION public.mixer_workspace_self_service_v1(#{@signature}) OWNER TO #{@writer}",
        "REVOKE CREATE ON SCHEMA public FROM #{@writer}",
        "GRANT USAGE ON SCHEMA public TO #{quoted_runtime}",
        "GRANT EXECUTE ON FUNCTION public.mixer_workspace_self_service_v1(#{@signature}) TO #{quoted_runtime}",
        "COMMIT"
      ]
  end

  defp relations(tables), do: Enum.map_join(tables, ", ", &"public.mixer_authz_#{&1}")

  # The relation owner already reads build journals under both build installations.
  # The workspace writer can receive only a count scoped to the current tenant.
  def build_count_body do
    """

    SELECT pg_catalog.count(*) FROM public.mixer_builds
    WHERE organization_id = pg_catalog.current_setting('mixer.authz.organization_id', true)
      AND (target IS NULL OR project_id = target)
    """
  end

  defp function do
    """
    CREATE FUNCTION public.mixer_workspace_self_service_v1(op text, org text, target text, body jsonb, issued bigint, expires bigint)
    RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog
      SET statement_timeout='5s' SET lock_timeout='500ms' SET idle_in_transaction_session_timeout='5s'
    AS $workspace$#{body()}$workspace$
    """
  end

  def body do
    """

    DECLARE actor text; oid text; pid text; mid text; n bigint; entered bigint; until_time bigint;
      role_name text; result jsonb; project_count bigint; head bigint; member_exp bigint;
    BEGIN
      entered:=floor(extract(epoch FROM clock_timestamp()))::bigint;
      IF op NOT IN ('create_organization','create_project','set_member','usage','export','delete_project')
        OR body IS NULL OR jsonb_typeof(body)<>'object' THEN RETURN '{"error":"invalid_request"}'; END IF;
      IF op IN ('create_organization','create_project') THEN
        IF (SELECT array_agg(k ORDER BY k) FROM jsonb_object_keys(body) k) IS DISTINCT FROM ARRAY['display_name']::text[]
          OR jsonb_typeof(body->'display_name')<>'string' OR octet_length(body->>'display_name') NOT BETWEEN 1 AND 128
          OR btrim(body->>'display_name')='' OR (body->>'display_name') ~ '[[:cntrl:]]'
          THEN RETURN '{"error":"invalid_request"}'; END IF;
      ELSIF op='set_member' THEN
        IF (SELECT array_agg(k ORDER BY k) FROM jsonb_object_keys(body) k) IS DISTINCT FROM ARRAY['role']::text[]
          OR body->>'role' IS NULL OR body->>'role' NOT IN ('administrator','developer','viewer')
          THEN RETURN '{"error":"invalid_request"}'; END IF;
      ELSIF body<>'{}'::jsonb THEN RETURN '{"error":"invalid_request"}'; END IF;

      actor:=current_setting('mixer.authz.principal_id',true);
      IF actor IS NULL OR actor='' THEN RETURN '{"error":"unauthenticated"}'; END IF;
      oid:=org;
      IF op='create_organization' THEN
        IF org IS NOT NULL OR target IS NOT NULL THEN RETURN '{"error":"invalid_request"}'; END IF;
        oid:='org-'||replace(gen_random_uuid()::text,'-','');
      ELSE
        IF org IS NULL OR octet_length(org) NOT BETWEEN 1 AND 128 OR org='*' THEN RETURN '{"error":"invalid_request"}'; END IF;
      END IF;
      PERFORM set_config('mixer.authz.organization_id',oid,true);
      IF op<>'create_organization' THEN
        SELECT revision INTO head FROM public.mixer_authz_organization_heads WHERE organization_id=oid FOR UPDATE;
        IF NOT FOUND THEN RETURN '{"error":"not_found"}'; END IF;
      END IF;

      n:=floor(extract(epoch FROM clock_timestamp()))::bigint;
      SELECT least(expires,coalesce(c.expires_at,expires),coalesce(f.expires_at,expires))
        INTO until_time
        FROM public.mixer_authz_profiles p
        JOIN public.mixer_authz_bindings b ON b.profile_id=p.id AND b.profile_version=p.version
        JOIN public.mixer_authz_principals a ON a.id=b.principal_id AND a.identity_class=b.identity_class
        JOIN public.mixer_authz_credentials c ON c.profile_id=p.id AND c.profile_version=p.version AND c.principal_id=a.id
        JOIN public.mixer_authz_families f ON f.id=c.family_id AND f.profile_id=p.id AND f.profile_version=p.version AND f.principal_id=a.id
        WHERE p.id=current_setting('mixer.authz.profile_id',true)
          AND p.version::text=current_setting('mixer.authz.profile_version',true)
          AND p.issuer=current_setting('mixer.authz.issuer',true) AND p.client_id=current_setting('mixer.authz.client_id',true)
          AND p.identity_class='human' AND b.identity_class='human'
          AND b.subject=current_setting('mixer.authz.subject',true) AND a.id=actor
          AND c.reference=current_setting('mixer.authz.credential_ref',true)
          AND f.id=current_setting('mixer.authz.family_id',true)
          AND p.active AND b.active AND a.active AND c.active AND f.active
          AND greatest(a.not_before,c.not_before,f.not_before)<=least(n,issued);
      IF NOT FOUND OR until_time IS NULL OR n<entered OR expires<=n OR issued>n+30 OR issued>=expires OR until_time<=n THEN
        RETURN '{"error":"unauthenticated"}';
      END IF;

      IF op='create_organization' THEN
        INSERT INTO public.mixer_authz_organizations(id,active,display_name) VALUES(oid,true,body->>'display_name');
        INSERT INTO public.mixer_authz_organization_heads VALUES(oid,1);
        mid:='member-'||replace(gen_random_uuid()::text,'-','');
        INSERT INTO public.mixer_authz_memberships VALUES(mid,actor,oid,NULL,'all_projects','owner',true,0,NULL,1);
        INSERT INTO public.mixer_build_organization_capacities(organization_id,"limit",revision,configured) VALUES(oid,2,0,true);
        INSERT INTO public.mixer_build_capacities VALUES(oid,'ios',2,0),(oid,'android',2,0);
        result:=jsonb_build_object('id',oid,'display_name',body->>'display_name','organization_roles',jsonb_build_array('owner'),'plan','free');
      ELSE
        IF NOT EXISTS(SELECT 1 FROM public.mixer_authz_organizations WHERE id=oid AND active) THEN RETURN '{"error":"not_found"}'; END IF;
        SELECT m.role,m.expires_at INTO role_name,member_exp FROM public.mixer_authz_memberships m
          WHERE m.organization_id=oid AND m.principal_id=actor AND m.project_id IS NULL
            AND m.project_binding='all_projects' AND m.active AND m.not_before<=n
            AND (m.expires_at IS NULL OR m.expires_at>n)
          ORDER BY CASE m.role WHEN 'owner' THEN 0 WHEN 'administrator' THEN 1 ELSE 2 END,m.id LIMIT 1;
        IF NOT FOUND THEN RETURN '{"error":"not_found"}'; END IF;
        until_time:=least(until_time,coalesce(member_exp,until_time));
        IF op<>'usage' AND role_name<>'owner' THEN RETURN '{"error":"permission_denied"}'; END IF;
        IF op='usage' THEN
          SELECT count(*) INTO project_count FROM public.mixer_authz_projects WHERE organization_id=oid AND active;
          SELECT jsonb_build_object('organization_id',oid,'plan','free','active_projects',project_count,'project_limit',3,
            'build_limit',c."limit",'held_builds',(SELECT count(*) FROM public.mixer_build_reservations r WHERE r.organization_id=oid AND r.held),
            'builds',public.mixer_workspace_build_count_v1(NULL))
            INTO result FROM public.mixer_build_organization_capacities c WHERE c.organization_id=oid AND c.configured;
          IF NOT FOUND THEN RETURN '{"error":"conflict"}'; END IF;
        ELSIF op='create_project' THEN
          IF target IS NOT NULL THEN RETURN '{"error":"invalid_request"}'; END IF;
          IF (SELECT count(*) FROM public.mixer_authz_projects WHERE organization_id=oid AND active)>=3
            OR (SELECT count(*) FROM public.mixer_authz_projects WHERE organization_id=oid)>=100 THEN RETURN '{"error":"quota_exceeded"}'; END IF;
          pid:='project-'||replace(gen_random_uuid()::text,'-','');
          INSERT INTO public.mixer_authz_projects VALUES(oid,pid,true,body->>'display_name');
          INSERT INTO public.mixer_authz_project_heads VALUES(oid,pid,1);
          UPDATE public.mixer_authz_organization_heads SET revision=revision+1 WHERE organization_id=oid;
          result:=jsonb_build_object('organization_id',oid,'id',pid,'display_name',body->>'display_name');
        ELSIF op='set_member' THEN
          IF target IS NULL OR octet_length(target) NOT BETWEEN 1 AND 128 OR target='*' THEN RETURN '{"error":"invalid_request"}'; END IF;
          PERFORM set_config('mixer.workspace.member_id',target,true);
          -- Activation may already hold this principal while waiting for the actor.
          -- Keep the identity lock to commit, but fail immediately on contention.
          PERFORM 1 FROM public.mixer_authz_principals WHERE id=target AND identity_class='human' AND active AND not_before<=n FOR SHARE NOWAIT;
          IF NOT FOUND THEN RETURN '{"error":"not_found"}'; END IF;
          -- Owner mutation is deliberately outside this operation. The founding owner cannot be demoted or removed.
          IF EXISTS(SELECT 1 FROM public.mixer_authz_memberships WHERE organization_id=oid AND principal_id=target AND role='owner' AND active) THEN RETURN '{"error":"conflict"}'; END IF;
          IF (SELECT count(*) FROM public.mixer_authz_memberships
            WHERE organization_id=oid AND principal_id=target AND project_binding='all_projects' AND project_id IS NULL)>1 THEN RETURN '{"error":"conflict"}'; END IF;
          UPDATE public.mixer_authz_memberships SET role=body->>'role',active=true,not_before=n,expires_at=NULL,revision=revision+1
            WHERE organization_id=oid AND principal_id=target AND project_binding='all_projects' AND project_id IS NULL RETURNING id INTO mid;
          IF NOT FOUND THEN
            IF (SELECT count(*) FROM public.mixer_authz_memberships WHERE organization_id=oid)>=100 THEN RETURN '{"error":"quota_exceeded"}'; END IF;
            mid:='member-'||replace(gen_random_uuid()::text,'-','');
            INSERT INTO public.mixer_authz_memberships VALUES(mid,target,oid,NULL,'all_projects',body->>'role',true,n,NULL,1);
          END IF;
          UPDATE public.mixer_authz_organization_heads SET revision=revision+1 WHERE organization_id=oid;
          result:=jsonb_build_object('organization_id',oid,'principal_id',target,'role',body->>'role','id',mid);
        ELSIF op='export' THEN
          result:=jsonb_build_object('organization', (SELECT jsonb_build_object('id',id,'display_name',display_name) FROM public.mixer_authz_organizations WHERE id=oid),
            'projects',coalesce((SELECT jsonb_agg(jsonb_build_object('id',id,'display_name',display_name,'active',active) ORDER BY id) FROM public.mixer_authz_projects WHERE organization_id=oid),'[]'::jsonb),
            'memberships',coalesce((SELECT jsonb_agg(jsonb_build_object('principal_id',principal_id,'role',role,'active',active) ORDER BY id) FROM public.mixer_authz_memberships WHERE organization_id=oid),'[]'::jsonb));
        ELSIF op='delete_project' THEN
          IF target IS NULL THEN RETURN '{"error":"invalid_request"}'; END IF;
          PERFORM 1 FROM public.mixer_authz_project_heads WHERE organization_id=oid AND project_id=target FOR UPDATE;
          IF NOT FOUND THEN RETURN '{"error":"not_found"}'; END IF;
          -- Conservatively retain every project with a build journal. No fence, artifact or worker can be orphaned.
          IF public.mixer_workspace_build_count_v1(target)>0 THEN RETURN '{"error":"conflict"}'; END IF;
          UPDATE public.mixer_authz_projects SET active=false WHERE organization_id=oid AND id=target AND active;
          IF NOT FOUND THEN RETURN '{"error":"not_found"}'; END IF;
          UPDATE public.mixer_authz_project_heads SET revision=revision+1 WHERE organization_id=oid AND project_id=target;
          UPDATE public.mixer_authz_organization_heads SET revision=revision+1 WHERE organization_id=oid;
          result:=jsonb_build_object('organization_id',oid,'id',target,'deleted',true,'retention','tombstone');
        END IF;
      END IF;
      n:=floor(extract(epoch FROM clock_timestamp()))::bigint;
      IF n<entered OR n>=until_time THEN RAISE EXCEPTION 'authority expired before commit'; END IF;
      RETURN result;
    END
    """
  end
end
