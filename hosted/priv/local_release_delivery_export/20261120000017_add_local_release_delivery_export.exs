defmodule MixerHosted.Repo.Migrations.AddLocalReleaseDeliveryExport do
  use Ecto.Migration

  @reader "mixer_release_delivery"
  @function "public.mixer_release_delivery_export"
  @signature @function <> "(text,text,text,text,text,text,text)"
  @heads "public.mixer_release_heads"
  @publications "public.mixer_release_publications"
  @artifacts "public.mixer_customer_artifacts"
  @enrollments "public.mixer_release_delivery_enrollments"
  @identity ~w(organization_id project_id application_id environment_id platform runtime_sha256)
  @target @identity ++ ["channel"]

  def up do
    execute("""
    DO $body$
    BEGIN
      IF (SELECT count(*) FROM pg_catalog.pg_class c
          JOIN pg_catalog.pg_roles r ON r.oid=c.relowner
          WHERE c.oid IN ('#{@heads}'::regclass,'#{@publications}'::regclass,
                          '#{@artifacts}'::regclass,'#{@enrollments}'::regclass)
            AND c.relrowsecurity AND c.relforcerowsecurity AND r.rolname=current_user
            AND NOT r.rolcanlogin AND NOT r.rolsuper AND NOT r.rolbypassrls) <> 4 THEN
        RAISE EXCEPTION 'delivery export requires the restricted release and enrollment owner';
      END IF;
    END
    $body$
    """)

    # Use the same statement-local artifact RLS context as the enrolled reader.
    execute("""
    CREATE FUNCTION #{@function}(org text, proj text, app text, env text, os text, runtime text, lane text)
    RETURNS TABLE(sequence text, previous_sequence text, action text, rollout integer,
                  manifest_digest text, assignment bytea, canonical_manifest bytea,
                  envelope bytea, envelope_digest text, payload_digest text)
    LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = pg_catalog
    AS $body$
    DECLARE
      prior_action text := coalesce(pg_catalog.current_setting('mixer.authz.action',true),'');
      prior_phase text := coalesce(pg_catalog.current_setting('mixer.authz.phase',true),'');
      prior_org text := coalesce(pg_catalog.current_setting('mixer.authz.organization_id',true),'');
      prior_proj text := coalesce(pg_catalog.current_setting('mixer.authz.project_id',true),'');
    BEGIN
      IF session_user <> '#{@reader}' OR current_user = session_user OR
         EXISTS (SELECT 1 FROM pg_catalog.pg_roles r
                 WHERE pg_catalog.pg_has_role(session_user,r.oid,'MEMBER') AND
                   (r.rolname=current_user OR r.rolsuper OR r.rolbypassrls OR r.rolcreaterole OR
                    r.rolcreatedb OR r.rolreplication OR left(r.rolname::text,3)='pg_')) THEN
        RETURN;
      END IF;

      PERFORM pg_catalog.set_config('mixer.authz.action','',true),
              pg_catalog.set_config('mixer.authz.phase','effect',true),
              pg_catalog.set_config('mixer.authz.organization_id',org,true),
              pg_catalog.set_config('mixer.authz.project_id',proj,true);

      RETURN QUERY
        SELECT trunc(p.sequence)::text,trunc(p.previous_sequence)::text,p.action,
               p.rollout_basis_points,p.artifact_sha256,p.signed_assignment_bytes,
               a.canonical_manifest_cbor,a.envelope_bytes,a.envelope_sha256,a.payload_sha256
        FROM #{@enrollments} e
        JOIN #{@heads} h ON #{same("h", "e", @target)}
        JOIN #{@publications} p ON #{same("p", "h", @target)} AND p.sequence=h.sequence
        JOIN #{@artifacts} a ON #{same("a", "p", @identity)} AND a.manifest_sha256=p.artifact_sha256
        WHERE e.reader_role=session_user AND #{columns("e", @target)}=(org,proj,app,env,os,runtime,lane)
          AND (p.action <> 'halt' OR EXISTS (
            SELECT 1 FROM #{@publications} prior
            WHERE #{same("prior", "p", @target)} AND prior.sequence=p.previous_sequence
              AND prior.artifact_sha256=p.artifact_sha256 AND prior.rollout_basis_points > 0
          ));

      PERFORM pg_catalog.set_config('mixer.authz.project_id',prior_proj,true),
              pg_catalog.set_config('mixer.authz.organization_id',prior_org,true),
              pg_catalog.set_config('mixer.authz.phase',prior_phase,true),
              pg_catalog.set_config('mixer.authz.action',prior_action,true);
    END
    $body$
    """)

    execute("REVOKE ALL ON FUNCTION #{@signature} FROM PUBLIC")
  end

  def down, do: execute("DROP FUNCTION #{@signature}")

  defp same(left, right, fields), do: "#{columns(left, fields)}=#{columns(right, fields)}"
  defp columns(name, fields), do: "(" <> Enum.map_join(fields, ",", &"#{name}.#{&1}") <> ")"
end
