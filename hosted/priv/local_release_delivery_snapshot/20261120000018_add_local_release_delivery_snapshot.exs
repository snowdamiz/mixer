defmodule MixerHosted.Repo.Migrations.AddLocalReleaseDeliverySnapshot do
  use Ecto.Migration

  @function "public.mixer_release_delivery_snapshot"
  @signature @function <> "(text,text,text,text,text,text,text)"
  @head_reader "public.mixer_release_delivery_export(text,text,text,text,text,text,text)"
  @publications "public.mixer_release_publications"
  @artifacts "public.mixer_customer_artifacts"
  @index "mixer_release_positive_publication_history"
  @identity ~w(organization_id project_id application_id environment_id platform runtime_sha256)
  @target @identity ++ ["channel"]

  def up do
    execute("""
    DO $body$
    BEGIN
      IF NOT EXISTS (
        SELECT 1 FROM pg_catalog.pg_proc p
        JOIN pg_catalog.pg_roles r ON r.oid=p.proowner
        WHERE p.oid='#{@head_reader}'::regprocedure AND r.rolname=current_user
          AND NOT r.rolcanlogin AND NOT r.rolsuper AND NOT r.rolbypassrls
      ) THEN
        RAISE EXCEPTION 'delivery snapshot requires the restricted head reader owner';
      END IF;
    END
    $body$
    """)

    execute("""
    CREATE INDEX #{@index}
      ON #{@publications} (#{Enum.join(@target, ",")},sequence DESC)
      INCLUDE (artifact_sha256) WHERE rollout_basis_points > 0
    """)

    execute("""
    CREATE FUNCTION #{@function}(org text, proj text, app text, env text, os text, runtime text, lane text)
    RETURNS TABLE(sequence text, previous_sequence text, action text, rollout integer,
                  manifest_digest text, assignment bytea, canonical_manifest bytea,
                  envelope bytea, envelope_digest text, payload_digest text, history_sequence numeric)
    LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = pg_catalog
    AS $body$
    DECLARE
      prior_action text := coalesce(pg_catalog.current_setting('mixer.authz.action',true),'');
      prior_phase text := coalesce(pg_catalog.current_setting('mixer.authz.phase',true),'');
      prior_org text := coalesce(pg_catalog.current_setting('mixer.authz.organization_id',true),'');
      prior_proj text := coalesce(pg_catalog.current_setting('mixer.authz.project_id',true),'');
    BEGIN
      PERFORM pg_catalog.set_config('mixer.authz.action','',true),
              pg_catalog.set_config('mixer.authz.phase','effect',true),
              pg_catalog.set_config('mixer.authz.organization_id',org,true),
              pg_catalog.set_config('mixer.authz.project_id',proj,true);

      -- The existing reader checks the login and exact enrollment before history is visible.
      -- Both STABLE readers use the calling statement's snapshot.
      RETURN QUERY
        WITH head AS MATERIALIZED (
          SELECT * FROM public.mixer_release_delivery_export(org,proj,app,env,os,runtime,lane)
        ), recent AS MATERIALIZED (
          SELECT p.sequence,p.artifact_sha256
          FROM head h
          CROSS JOIN LATERAL (
            SELECT p.sequence,p.artifact_sha256
            FROM #{@publications} p
            WHERE #{columns("p", @target)}=(org,proj,app,env,os,runtime,lane)
              AND p.sequence <= h.sequence::numeric AND p.rollout_basis_points > 0
            ORDER BY p.sequence DESC
            LIMIT 32
          ) p
          WHERE h.rollout = 0 OR p.artifact_sha256 <> h.manifest_digest
        ), retained AS (
          SELECT max(r.sequence) AS sequence,r.artifact_sha256
          FROM recent r GROUP BY r.artifact_sha256
        )
        SELECT h.*,NULL::numeric FROM head h
        UNION ALL
        SELECT NULL,NULL,NULL,NULL,r.artifact_sha256,NULL,a.canonical_manifest_cbor,
               a.envelope_bytes,a.envelope_sha256,a.payload_sha256,r.sequence
        FROM retained r
        CROSS JOIN LATERAL (
          SELECT a.canonical_manifest_cbor,a.envelope_bytes,a.envelope_sha256,a.payload_sha256
          FROM #{@artifacts} a
          WHERE #{columns("a", @identity)}=(org,proj,app,env,os,runtime)
            AND a.manifest_sha256=r.artifact_sha256
          LIMIT 1
        ) a;

      PERFORM pg_catalog.set_config('mixer.authz.project_id',prior_proj,true),
              pg_catalog.set_config('mixer.authz.organization_id',prior_org,true),
              pg_catalog.set_config('mixer.authz.phase',prior_phase,true),
              pg_catalog.set_config('mixer.authz.action',prior_action,true);
    END
    $body$
    """)

    execute("REVOKE ALL ON FUNCTION #{@signature} FROM PUBLIC")
  end

  def down do
    execute("DROP FUNCTION #{@signature}")
    execute("DROP INDEX public.#{@index}")
  end

  defp columns(name, fields), do: "(" <> Enum.map_join(fields, ",", &"#{name}.#{&1}") <> ")"
end
