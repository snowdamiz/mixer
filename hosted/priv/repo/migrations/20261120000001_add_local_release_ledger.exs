defmodule MixerHosted.Repo.Migrations.AddLocalReleaseLedger do
  use Ecto.Migration

  @scope "organization_id,project_id,application_id,environment_id"
  @target @scope <> ",platform,runtime_sha256"
  @head @target <> ",channel"
  @artifact_key @target <> ",manifest_sha256"
  @sequence_check "BETWEEN 1 AND 18446744073709551615"
  @heads "public.mixer_release_heads"
  @entries "public.mixer_release_publications"

  def up do
    # The existing artifact schema has a project/digest primary key. A unique
    # index lets the ledger reference its full scope without rewriting any rows.
    execute("""
    CREATE UNIQUE INDEX mixer_release_artifact_binding
    ON public.mixer_customer_artifacts (#{@artifact_key})
    """)

    execute("""
    CREATE TABLE #{@heads} (
      organization_id text NOT NULL, project_id text NOT NULL,
      application_id text NOT NULL, environment_id text NOT NULL,
      platform text NOT NULL CHECK (platform IN ('ios','android')),
      runtime_sha256 text NOT NULL CHECK (runtime_sha256 ~ '^[0-9a-f]{64}$'),
      channel text NOT NULL CHECK (channel ~ '^[A-Za-z0-9_.-]{1,128}$'),
      writer_role name NOT NULL,
      sequence numeric CHECK (sequence #{@sequence_check} AND sequence = trunc(sequence)),
      PRIMARY KEY (#{@head}),
      FOREIGN KEY (#{@scope}) REFERENCES
        public.mixer_authz_environments(organization_id,project_id,application_id,id)
    )
    """)

    execute("CREATE UNIQUE INDEX mixer_release_one_local_target ON #{@heads} ((true))")

    execute("""
    CREATE TABLE #{@entries} (
      organization_id text NOT NULL, project_id text NOT NULL,
      application_id text NOT NULL, environment_id text NOT NULL,
      platform text NOT NULL, runtime_sha256 text NOT NULL, channel text NOT NULL,
      sequence numeric NOT NULL CHECK (sequence #{@sequence_check} AND sequence = trunc(sequence)),
      previous_sequence numeric CHECK (previous_sequence < sequence),
      artifact_sha256 text NOT NULL,
      signed_assignment_bytes bytea NOT NULL CHECK (octet_length(signed_assignment_bytes) BETWEEN 1 AND 65536),
      rollout_basis_points integer NOT NULL CHECK (rollout_basis_points BETWEEN 0 AND 10000),
      idempotency_key text NOT NULL CHECK (idempotency_key ~ '^[A-Za-z0-9_.:-]{1,128}$'),
      reason text NOT NULL CHECK (octet_length(reason) BETWEEN 1 AND 512),
      principal_id text NOT NULL REFERENCES public.mixer_authz_principals(id),
      recorded_at timestamp(6) with time zone NOT NULL DEFAULT statement_timestamp(),
      PRIMARY KEY (#{@head},sequence),
      UNIQUE (#{@head},idempotency_key),
      FOREIGN KEY (#{@head}) REFERENCES #{@heads}(#{@head}),
      FOREIGN KEY (#{@head},previous_sequence) REFERENCES #{@entries}(#{@head},sequence),
      CONSTRAINT mixer_release_exact_artifact FOREIGN KEY (#{@target},artifact_sha256)
        REFERENCES public.mixer_customer_artifacts(#{@artifact_key})
    )
    """)

    execute("""
    ALTER TABLE #{@heads} ADD CONSTRAINT mixer_release_current_publication
      FOREIGN KEY (#{@head},sequence) REFERENCES #{@entries}(#{@head},sequence)
    """)

    for table <- [@heads, @entries] do
      execute("REVOKE ALL ON #{table} FROM PUBLIC")
      execute("ALTER TABLE #{table} ENABLE ROW LEVEL SECURITY")
      execute("ALTER TABLE #{table} FORCE ROW LEVEL SECURITY")
    end

    owner? = fn table ->
      "current_user = pg_catalog.pg_get_userbyid((SELECT relowner FROM pg_catalog.pg_class WHERE oid = '#{table}'::regclass))"
    end

    # The migration owner registers the one v3 target with no current assignment.
    execute("""
    CREATE POLICY release_register ON #{@heads} FOR INSERT
      WITH CHECK (#{owner?.(@heads)} AND sequence IS NULL)
    """)

    execute("""
    CREATE POLICY release_owner_read ON #{@entries} FOR SELECT USING (#{owner?.(@entries)})
    """)

    create_access_guard(
      "publish",
      "mixer.release.publish",
      ~w(owner administrator release_manager)
    )

    create_access_guard(
      "read",
      "mixer.workspace.read",
      ~w(owner administrator developer release_manager viewer)
    )

    writer_scope = """
    current_user = session_user AND current_user = writer_role
    AND public.mixer_release_publish_allowed(organization_id,project_id,application_id,environment_id)
    """

    execute("CREATE POLICY release_head_read ON #{@heads} FOR SELECT USING (#{writer_scope})")
    execute("CREATE POLICY release_head_advance ON #{@heads} FOR UPDATE USING (#{writer_scope})")

    visible_head = """
    EXISTS (
      SELECT 1 FROM #{@heads} h
      WHERE (#{qualified("h")}) = (#{qualified("mixer_release_publications")})
    )
    """

    execute("CREATE POLICY release_read ON #{@entries} FOR SELECT USING (#{visible_head})")

    execute("""
    CREATE POLICY release_append ON #{@entries} FOR INSERT WITH CHECK (
      #{visible_head} AND principal_id = current_setting('mixer.authz.principal_id', true)
    )
    """)

    execute("""
    CREATE FUNCTION public.mixer_release_check_advance() RETURNS trigger
    LANGUAGE plpgsql SET search_path = pg_catalog AS $body$
    BEGIN
      IF NEW.sequence IS NULL OR (OLD.sequence IS NOT NULL AND NEW.sequence <= OLD.sequence)
          OR NOT EXISTS (
            SELECT 1 FROM #{@entries} p
            WHERE (#{qualified("p")}) = (#{qualified("NEW")}) AND p.sequence = NEW.sequence
              AND p.previous_sequence IS NOT DISTINCT FROM OLD.sequence
          ) THEN
        RAISE EXCEPTION 'invalid release head transition' USING ERRCODE = '23514';
      END IF;
      RETURN NEW;
    END
    $body$
    """)

    execute("""
    CREATE FUNCTION public.mixer_release_check_committed_head() RETURNS trigger
    LANGUAGE plpgsql SET search_path = pg_catalog AS $body$
    BEGIN
      IF NOT EXISTS (
        SELECT 1 FROM #{@heads} h
        WHERE (#{qualified("h")}) = (#{qualified("NEW")}) AND h.sequence = NEW.sequence
      ) THEN
        RAISE EXCEPTION 'release publication requires a head transition' USING ERRCODE = '23514';
      END IF;
      RETURN NULL;
    END
    $body$
    """)

    execute("REVOKE ALL ON FUNCTION public.mixer_release_check_advance() FROM PUBLIC")
    execute("REVOKE ALL ON FUNCTION public.mixer_release_check_committed_head() FROM PUBLIC")

    execute("""
    CREATE TRIGGER release_check_advance BEFORE UPDATE ON #{@heads}
    FOR EACH ROW EXECUTE FUNCTION public.mixer_release_check_advance()
    """)

    execute("""
    CREATE CONSTRAINT TRIGGER release_check_committed_head AFTER INSERT ON #{@entries}
    DEFERRABLE INITIALLY DEFERRED FOR EACH ROW
    EXECUTE FUNCTION public.mixer_release_check_committed_head()
    """)
  end

  def down do
    execute("LOCK TABLE #{@heads}, #{@entries} IN ACCESS EXCLUSIVE MODE")

    execute("""
    DO $body$ BEGIN
      IF EXISTS (SELECT 1 FROM #{@entries}) THEN
        RAISE EXCEPTION 'release ledger contains committed publications';
      END IF;
    END $body$
    """)

    execute("ALTER TABLE #{@heads} DROP CONSTRAINT mixer_release_current_publication")
    execute("DROP TABLE #{@entries}")
    execute("DROP TABLE #{@heads}")
    execute("DROP FUNCTION public.mixer_release_publish_allowed(text,text,text,text)")
    execute("DROP FUNCTION public.mixer_release_read_allowed(text,text,text,text)")
    execute("DROP FUNCTION public.mixer_release_check_committed_head()")
    execute("DROP FUNCTION public.mixer_release_check_advance()")
    execute("DROP INDEX public.mixer_release_artifact_binding")
  end

  defp create_access_guard(action, required_scope, roles) do
    # Like artifact storage, settings select the request, while the policy
    # rechecks the exact active authorization records under their FORCE RLS.
    function = "public.mixer_release_#{action}_allowed"
    allowed_roles = Enum.map_join(roles, ",", &"'#{&1}'")

    execute("""
    CREATE FUNCTION #{function}(org text, proj text, app text, env text)
    RETURNS boolean LANGUAGE plpgsql STABLE SECURITY INVOKER SET search_path = pg_catalog AS $body$
    DECLARE
      issued bigint;
      expiry bigint;
      checked_at bigint := floor(extract(epoch FROM statement_timestamp()));
    BEGIN
      IF current_setting('mixer.authz.action',true) IS DISTINCT FROM 'release.#{action}'
        OR current_setting('mixer.authz.required_scope',true) IS DISTINCT FROM '#{required_scope}'
        OR current_setting('mixer.authz.phase',true) IS DISTINCT FROM 'effect'
        OR current_setting('mixer.authz.identity_class',true) IS DISTINCT FROM 'human'
        OR current_setting('mixer.authz.directory_mode',true) IS DISTINCT FROM ''
        OR coalesce(current_setting('mixer.authz.transaction_marker',true),'') !~ '^[0-9a-f]{64}$'
        OR org IS DISTINCT FROM current_setting('mixer.authz.organization_id',true)
        OR proj IS DISTINCT FROM current_setting('mixer.authz.project_id',true)
        OR app IS DISTINCT FROM current_setting('mixer.authz.application_id',true)
        OR env IS DISTINCT FROM current_setting('mixer.authz.environment_id',true)
        OR coalesce(current_setting('mixer.authz.token_issued_at',true),'') !~ '^(0|[1-9][0-9]{0,15})$'
        OR coalesce(current_setting('mixer.authz.token_expires_at',true),'') !~ '^(0|[1-9][0-9]{0,15})$'
      THEN
        RETURN false;
      END IF;

      issued := current_setting('mixer.authz.token_issued_at',true)::bigint;
      expiry := current_setting('mixer.authz.token_expires_at',true)::bigint;
      IF issued > checked_at + 30 OR expiry > 9007199254740991
        OR expiry <= checked_at OR issued >= expiry
      THEN
        RETURN false;
      END IF;

      RETURN EXISTS (
        SELECT 1 FROM public.mixer_authz_profiles pf
        JOIN public.mixer_authz_bindings b ON (b.profile_id,b.profile_version) = (pf.id,pf.version)
        JOIN public.mixer_authz_principals pr ON pr.id = b.principal_id
        JOIN public.mixer_authz_credentials c
          ON (c.profile_id,c.profile_version,c.principal_id) = (pf.id,pf.version,pr.id)
        JOIN public.mixer_authz_families f
          ON (f.id,f.profile_id,f.profile_version,f.principal_id) = (c.family_id,pf.id,pf.version,pr.id)
        JOIN public.mixer_authz_organizations o ON o.id = org
        JOIN public.mixer_authz_projects p ON (p.organization_id,p.id) = (org,proj)
        JOIN public.mixer_authz_applications a ON (a.organization_id,a.project_id,a.id) = (org,proj,app)
        JOIN public.mixer_authz_environments e
          ON (e.organization_id,e.project_id,e.application_id,e.id) = (org,proj,app,env)
        JOIN public.mixer_authz_memberships m ON (m.principal_id,m.organization_id) = (pr.id,org)
        WHERE pf.active AND b.active AND pr.active AND c.active AND f.active
          AND o.active AND p.active AND a.active AND e.active
          AND pf.identity_class = 'human' AND b.identity_class = 'human' AND pr.identity_class = 'human'
          AND pf.id = current_setting('mixer.authz.profile_id',true)
          AND pf.version::text = current_setting('mixer.authz.profile_version',true)
          AND pf.issuer = current_setting('mixer.authz.issuer',true)
          AND pf.client_id = current_setting('mixer.authz.client_id',true)
          AND b.subject = current_setting('mixer.authz.subject',true)
          AND pr.id = current_setting('mixer.authz.principal_id',true)
          AND c.reference = current_setting('mixer.authz.credential_ref',true)
          AND f.id = current_setting('mixer.authz.family_id',true)
          AND greatest(pr.not_before,c.not_before,f.not_before) <= least(checked_at,issued)
          AND (c.expires_at IS NULL OR checked_at < c.expires_at)
          AND (f.expires_at IS NULL OR checked_at < f.expires_at)
          AND m.active AND m.not_before <= checked_at
          AND (m.expires_at IS NULL OR checked_at < m.expires_at)
          AND ((m.project_binding = 'all_projects' AND m.project_id IS NULL)
            OR (m.project_binding = 'exact_project' AND m.project_id = proj))
          AND m.role IN (#{allowed_roles})
      );
    END
    $body$
    """)

    execute("REVOKE ALL ON FUNCTION #{function}(text,text,text,text) FROM PUBLIC")
  end

  defp qualified(alias_name) do
    @head |> String.split(",") |> Enum.map_join(",", &"#{alias_name}.#{&1}")
  end
end
