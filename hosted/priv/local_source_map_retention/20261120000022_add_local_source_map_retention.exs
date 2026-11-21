defmodule MixerHosted.Repo.Migrations.AddLocalSourceMapRetention do
  use Ecto.Migration

  @table "public.mixer_release_source_maps"
  @scope "organization_id, project_id, application_id, environment_id"
  @target @scope <> ", platform, runtime_sha256, channel"
  @key @target <> ", sequence"
  @guard "public.mixer_release_source_map_allowed"
  @signature "text,text,text,text,text,text,text,numeric,text"
  @unexpired "retain_until > floor(extract(epoch FROM statement_timestamp()))"

  def up do
    execute("""
    CREATE TABLE #{@table} (
      organization_id text NOT NULL, project_id text NOT NULL,
      application_id text NOT NULL, environment_id text NOT NULL,
      platform text NOT NULL, runtime_sha256 text NOT NULL, channel text NOT NULL,
      sequence numeric NOT NULL, artifact_sha256 text NOT NULL,
      retained_by text NOT NULL REFERENCES public.mixer_authz_principals(id),
      retain_until bigint NOT NULL,
      map_bytes bytea,
      PRIMARY KEY (#{@key}),
      FOREIGN KEY (#{@key}) REFERENCES public.mixer_release_publications(#{@key})
    )
    """)

    execute("""
    CREATE INDEX mixer_release_source_map_expiry
    ON #{@table} (retain_until) WHERE map_bytes IS NOT NULL
    """)

    execute("REVOKE ALL ON #{@table} FROM PUBLIC")
    execute("ALTER TABLE #{@table} ENABLE ROW LEVEL SECURITY")
    execute("ALTER TABLE #{@table} FORCE ROW LEVEL SECURITY")

    execute("""
    CREATE FUNCTION #{@guard}(
      org text, project text, app text, env text, target_platform text, runtime text,
      target_channel text, published_sequence numeric, digest text
    ) RETURNS boolean LANGUAGE sql STABLE SECURITY INVOKER SET search_path = pg_catalog
    AS $body$
      SELECT current_user = session_user
        AND public.mixer_release_publish_allowed(org,project,app,env)
        AND EXISTS (
          SELECT 1 FROM public.mixer_authz_memberships m
          WHERE m.organization_id = org AND m.principal_id = current_setting('mixer.authz.principal_id',true)
            AND m.role = 'owner' AND m.active
            AND m.not_before <= floor(extract(epoch FROM statement_timestamp()))
            AND (m.expires_at IS NULL OR m.expires_at > floor(extract(epoch FROM statement_timestamp())))
            AND ((m.project_binding = 'all_projects' AND m.project_id IS NULL)
              OR (m.project_binding = 'exact_project' AND m.project_id = project))
        )
        AND EXISTS (
          SELECT 1 FROM public.mixer_release_publications p
          WHERE (p.organization_id,p.project_id,p.application_id,p.environment_id,p.platform,
                 p.runtime_sha256,p.channel,p.sequence,p.artifact_sha256)
              = (org,project,app,env,target_platform,runtime,target_channel,published_sequence,digest)
            AND p.action = 'publish'
        )
    $body$
    """)

    execute("REVOKE ALL ON FUNCTION #{@guard}(#{@signature}) FROM PUBLIC")

    visible = "#{@unexpired} AND #{@guard}(#{@key}, artifact_sha256)"

    execute(
      "CREATE POLICY source_map_read ON #{@table} FOR SELECT USING (#{visible} AND map_bytes IS NOT NULL)"
    )

    execute("""
    CREATE POLICY source_map_retain ON #{@table} FOR INSERT WITH CHECK (
      #{visible}
      AND retained_by = current_setting('mixer.authz.principal_id',true)
      AND octet_length(map_bytes) BETWEEN 1 AND 4194304
      AND encode(sha256(map_bytes),'hex') = (
        SELECT convert_from(a.signed_manifest_bytes,'UTF8')::jsonb->'manifest'->>'source_map_sha256'
        FROM public.mixer_release_bound_artifact(#{@target}, artifact_sha256) a
      )
    )
    """)
  end

  def down do
    execute("LOCK TABLE #{@table} IN ACCESS EXCLUSIVE MODE")
    execute("ALTER TABLE #{@table} NO FORCE ROW LEVEL SECURITY")

    execute("""
    DO $body$ BEGIN
      IF EXISTS (SELECT 1 FROM #{@table}) THEN
        RAISE EXCEPTION 'source map retention records exist';
      END IF;
    END $body$
    """)

    execute("DROP TABLE #{@table}")
    execute("DROP FUNCTION #{@guard}(#{@signature})")
  end
end
