defmodule MixerHosted.Repo.Migrations.AddLocalReleaseDelivery do
  use Ecto.Migration

  @role "mixer_release_delivery"
  @heads "public.mixer_release_heads"
  @entries "public.mixer_release_publications"
  @artifacts "public.mixer_customer_artifacts"
  @identity ~w(organization_id project_id application_id environment_id platform runtime_sha256)
  @target @identity ++ ["channel"]
  @offer "public.mixer_release_delivery_offer"
  @artifact "public.mixer_release_delivery_artifact"

  def up do
    execute("""
    DO $body$
    BEGIN
      IF (SELECT count(*) FROM pg_catalog.pg_class c
          JOIN pg_catalog.pg_roles r ON r.oid=c.relowner
          WHERE c.oid IN ('#{@heads}'::regclass,'#{@entries}'::regclass,'#{@artifacts}'::regclass)
            AND c.relrowsecurity AND c.relforcerowsecurity AND r.rolname=current_user
            AND NOT r.rolcanlogin AND NOT r.rolsuper AND NOT r.rolbypassrls) <> 3 THEN
        RAISE EXCEPTION 'local delivery requires the restricted release and artifact owner';
      END IF;
    END
    $body$
    """)

    execute("""
    CREATE POLICY release_delivery_owner ON #{@heads} FOR SELECT USING (
      session_user = '#{@role}' AND NOT pg_catalog.pg_has_role(session_user,writer_role,'MEMBER') AND
      current_user = pg_catalog.pg_get_userbyid(
        (SELECT relowner FROM pg_catalog.pg_class WHERE oid = '#{@heads}'::regclass))
    )
    """)

    create_reader(
      @offer,
      "org text, proj text, app text, env text, os text, runtime text, lane text",
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
      "org text, proj text, app text, env text, os text, runtime text, lane text, digest text",
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
  end

  def down do
    execute("DROP FUNCTION #{@artifact}(text,text,text,text,text,text,text,text)")
    execute("DROP FUNCTION #{@offer}(text,text,text,text,text,text,text)")
    execute("DROP POLICY release_delivery_owner ON #{@heads}")
  end

  defp create_reader(name, arguments, returns, query) do
    # Reuse the artifact store's owner read policy for this statement. Restore
    # the caller settings on success. PostgreSQL rolls back LOCAL changes if
    # the statement fails.
    execute("""
    CREATE FUNCTION #{name}(#{arguments}) RETURNS TABLE(#{returns})
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

    types = arguments |> String.split(", ") |> Enum.map_join(",", fn _ -> "text" end)
    execute("REVOKE ALL ON FUNCTION #{name}(#{types}) FROM PUBLIC")
  end

  defp same(left, right, fields), do: "(#{columns(left, fields)}) = (#{columns(right, fields)})"
  defp columns(alias_name, fields), do: Enum.map_join(fields, ",", &"#{alias_name}.#{&1}")
end
