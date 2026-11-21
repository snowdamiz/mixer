defmodule MixerHosted.Repo.Migrations.AddLocalReleaseTargetRegistry do
  use Ecto.Migration

  @role "mixer_release_delivery"
  @heads "public.mixer_release_heads"
  @entries "public.mixer_release_publications"
  @artifacts "public.mixer_customer_artifacts"
  @enrollments "public.mixer_release_delivery_enrollments"
  @identity ~w(organization_id project_id application_id environment_id platform runtime_sha256)
  @target @identity ++ ["channel"]
  @jobs "mixer_release_jobs.oban_jobs"
  @offers "mixer_release_jobs.offer_materializations"
  @queue "queue = 'releases' AND worker = 'MixerHosted.Releases.ReleaseJobs.Materialize'"
  @offer "public.mixer_release_delivery_offer"
  @artifact "public.mixer_release_delivery_artifact"
  @coordinates "org text, proj text, app text, env text, os text, runtime text, lane text"
  @offer_signature @offer <> "(text,text,text,text,text,text,text)"
  @artifact_signature @artifact <> "(text,text,text,text,text,text,text,text)"

  def up do
    execute("""
    DO $body$
    BEGIN
      IF (SELECT count(*) FROM pg_catalog.pg_class c
          JOIN pg_catalog.pg_roles r ON r.oid=c.relowner
          WHERE c.oid IN ('#{@heads}'::regclass,'#{@entries}'::regclass,'#{@artifacts}'::regclass)
            AND c.relrowsecurity AND c.relforcerowsecurity AND r.rolname=current_user
            AND NOT r.rolcanlogin AND NOT r.rolsuper AND NOT r.rolbypassrls) <> 3 THEN
        RAISE EXCEPTION 'target registry requires the restricted release and artifact owner';
      END IF;
      IF (SELECT count(*) FROM pg_catalog.pg_proc p
          WHERE p.oid IN ('#{@offer_signature}'::regprocedure,'#{@artifact_signature}'::regprocedure)
            AND pg_catalog.pg_get_userbyid(p.proowner)=current_user AND p.prosecdef) <> 2 THEN
        RAISE EXCEPTION 'target registry requires the original restricted delivery functions';
      END IF;
    END
    $body$
    """)

    prepare_queue()

    key = Enum.join(@target, ",")

    execute("""
    CREATE TABLE #{@enrollments} (
      reader_role name NOT NULL CHECK (reader_role = '#{@role}'),
      organization_id text NOT NULL, project_id text NOT NULL,
      application_id text NOT NULL, environment_id text NOT NULL,
      platform text NOT NULL, runtime_sha256 text NOT NULL, channel text NOT NULL,
      PRIMARY KEY (reader_role,#{key}),
      FOREIGN KEY (#{key}) REFERENCES #{@heads}(#{key})
    )
    """)

    execute("REVOKE ALL ON #{@enrollments} FROM PUBLIC")
    execute("ALTER TABLE #{@enrollments} ENABLE ROW LEVEL SECURITY")
    execute("ALTER TABLE #{@enrollments} FORCE ROW LEVEL SECURITY")

    execute(
      "CREATE POLICY release_delivery_enrollment_owner ON #{@enrollments} TO CURRENT_USER USING (true)"
    )

    create_reader(
      @offer,
      @coordinates,
      "sequence numeric, rollout integer, digest text, assignment bytea, manifest bytea, payload bytea",
      """
      SELECT p.sequence,p.rollout_basis_points,p.artifact_sha256,p.signed_assignment_bytes,
             a.signed_manifest_bytes,a.payload
      FROM #{@heads} h
      JOIN #{@entries} p ON #{same("p", "h", @target)} AND p.sequence=h.sequence
      JOIN #{@artifacts} a ON #{same("a", "h", @identity)} AND a.manifest_sha256=p.artifact_sha256
      WHERE (#{columns("h", @target)}) = (org,proj,app,env,os,runtime,lane)
      """
    )

    create_reader(
      @artifact,
      @coordinates <> ", digest text",
      "envelope bytea, envelope_digest text, payload_digest text",
      """
      SELECT a.envelope_bytes,a.envelope_sha256,a.payload_sha256
      FROM #{@heads} h
      JOIN #{@artifacts} a ON #{same("a", "h", @identity)} AND a.manifest_sha256=digest
      WHERE (#{columns("h", @target)}) = (org,proj,app,env,os,runtime,lane)
        AND EXISTS (SELECT 1 FROM #{@entries} p
                    WHERE #{same("p", "h", @target)} AND p.artifact_sha256=a.manifest_sha256)
      """
    )

    # The Ecto transaction publishes the enrolled readers and the index removal
    # together. Existing heads receive no implied enrollment.
    execute("DROP INDEX public.mixer_release_one_local_target")
  end

  def down,
    do: raise("target registry rollback requires a forward migration preserving enrollment")

  defp prepare_queue do
    fields = Enum.map_join(@target, ",", &"'#{&1}',p.#{&1}")
    reference_key = Enum.map_join(@target ++ ["sequence"], ",", &"(args ->> '#{&1}')")

    # Block ledger writes first, in publisher order, while allowing an in-flight
    # materializer to finish its ledger read before taking the queue locks.
    execute("LOCK TABLE #{@heads}, #{@entries} IN SHARE ROW EXCLUSIVE MODE")

    execute("""
    DO $body$
    BEGIN
      IF pg_catalog.to_regnamespace('mixer_release_jobs') IS NULL THEN
        -- Reserve the name against installation of the original singleton queue.
        CREATE SCHEMA mixer_release_jobs;
        REVOKE ALL ON SCHEMA mixer_release_jobs FROM PUBLIC;
        RETURN;
      END IF;

      IF (SELECT count(*) FROM pg_catalog.pg_class c
          WHERE c.oid IN (pg_catalog.to_regclass('#{@jobs}'), pg_catalog.to_regclass('#{@offers}'))
            AND c.relkind = 'r' AND c.relrowsecurity AND c.relforcerowsecurity
            AND pg_catalog.pg_get_userbyid(c.relowner) = current_user) <> 2
         OR pg_catalog.obj_description(pg_catalog.to_regclass('#{@jobs}'), 'pg_class')
              IS DISTINCT FROM '14' THEN
        RAISE EXCEPTION 'target registry requires the restricted release queue';
      END IF;

      LOCK TABLE #{@jobs}, #{@offers} IN ACCESS EXCLUSIVE MODE;

      IF EXISTS (
        SELECT 1 FROM #{@jobs} j
        WHERE #{@queue} AND NOT EXISTS (
          SELECT 1 FROM #{@entries} p
          WHERE (#{columns("p", @target)}) = (#{Enum.map_join(@target, ",", &"j.args->>'#{&1}'")})
            AND p.sequence = mixer_release_jobs.publication_sequence_v1(j.args)
            AND p.release_jobs_xact_id IS NOT NULL
            AND j.args = jsonb_build_object('version',1,#{fields},'sequence',trunc(p.sequence)::text)
        )
      ) OR EXISTS (
        SELECT 1 FROM #{@offers} o
        WHERE NOT EXISTS (
          SELECT 1 FROM #{@entries} p
          WHERE #{same("p", "o", @target ++ ["sequence"])}
            AND p.release_jobs_xact_id IS NOT NULL
            AND (p.signed_assignment_bytes,p.artifact_sha256,p.rollout_basis_points,p.action)
              = (o.signed_assignment_bytes,o.artifact_sha256,o.rollout_basis_points,o.action)
        )
      ) THEN
        RAISE EXCEPTION 'retained release queue work does not match the immutable ledger';
      END IF;

      DROP INDEX IF EXISTS mixer_release_jobs.release_job_publication_reference;
      CREATE UNIQUE INDEX release_job_publication_reference
        ON #{@jobs} (#{reference_key}) WHERE #{@queue};
      DROP INDEX IF EXISTS mixer_release_jobs.release_job_publication_sequence;
    END
    $body$
    """)
  end

  defp create_reader(name, arguments, returns, query) do
    # Preserve the grants, caller validation and artifact RLS context from 000003.
    execute("""
    CREATE OR REPLACE FUNCTION #{name}(#{arguments}) RETURNS TABLE(#{returns})
    LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = pg_catalog
    AS $body$
    DECLARE
      prior_action text := coalesce(pg_catalog.current_setting('mixer.authz.action',true),'');
      prior_phase text := coalesce(pg_catalog.current_setting('mixer.authz.phase',true),'');
      prior_org text := coalesce(pg_catalog.current_setting('mixer.authz.organization_id',true),'');
      prior_proj text := coalesce(pg_catalog.current_setting('mixer.authz.project_id',true),'');
    BEGIN
      IF session_user <> '#{@role}' OR current_user = session_user OR
         EXISTS (SELECT 1 FROM pg_catalog.pg_roles r
                 WHERE pg_catalog.pg_has_role(session_user,r.oid,'MEMBER') AND
                   (r.rolname=current_user OR r.rolsuper OR r.rolbypassrls OR r.rolcreaterole OR
                    r.rolcreatedb OR r.rolreplication OR left(r.rolname::text,3)='pg_')) THEN
        RETURN;
      END IF;

      IF NOT EXISTS (SELECT 1 FROM #{@enrollments} e
                     WHERE e.reader_role = session_user
                     AND (#{columns("e", @target)}) = (org,proj,app,env,os,runtime,lane)) THEN
        RETURN;
      END IF;

      PERFORM pg_catalog.set_config('mixer.authz.action','',true),
              pg_catalog.set_config('mixer.authz.phase','effect',true),
              pg_catalog.set_config('mixer.authz.organization_id',org,true),
              pg_catalog.set_config('mixer.authz.project_id',proj,true);
      RETURN QUERY #{query};
      PERFORM pg_catalog.set_config('mixer.authz.project_id',prior_proj,true),
              pg_catalog.set_config('mixer.authz.organization_id',prior_org,true),
              pg_catalog.set_config('mixer.authz.phase',prior_phase,true),
              pg_catalog.set_config('mixer.authz.action',prior_action,true);
    END
    $body$
    """)
  end

  defp same(left, right, fields), do: "(#{columns(left, fields)}) = (#{columns(right, fields)})"
  defp columns(alias_name, fields), do: Enum.map_join(fields, ",", &"#{alias_name}.#{&1}")
end
