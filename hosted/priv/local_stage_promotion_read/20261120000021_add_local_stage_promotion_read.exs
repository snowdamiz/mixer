defmodule MixerHosted.Repo.Migrations.AddLocalStagePromotionRead do
  use Ecto.Migration

  @bindings "public.mixer_stage_promotion_bindings"
  @heads "public.mixer_release_heads"
  @publications "public.mixer_release_publications"
  @reader "public.mixer_stage_promotion_receipts"
  @signature "#{@reader}(text,text,text,text,text,text,text,numeric,text)"

  def up do
    execute("""
    DO $body$
    BEGIN
      IF (SELECT count(*) FROM pg_catalog.pg_class c
          JOIN pg_catalog.pg_roles r ON r.oid=c.relowner
          WHERE c.oid IN ('#{@bindings}'::regclass,'#{@heads}'::regclass,'#{@publications}'::regclass)
            AND c.relrowsecurity AND c.relforcerowsecurity AND r.rolname=current_user
            AND NOT r.rolcanlogin AND NOT r.rolsuper AND NOT r.rolbypassrls) <> 3 THEN
        RAISE EXCEPTION 'promotion receipts require the restricted release ledger owner';
      END IF;
    END
    $body$
    """)

    # The ordinary login may also publish. Keep its direct binding SELECT under
    # the publisher policy and expose only the destination projection below.
    execute("""
    CREATE POLICY stage_binding_receipt_owner ON #{@bindings}
    FOR SELECT TO CURRENT_USER USING (
      current_user <> session_user AND writer_role = session_user
      AND public.mixer_release_read_allowed(
        organization_id,project_id,application_id,destination_environment_id)
    )
    """)

    execute("""
    CREATE FUNCTION #{@reader}(
      org text, project text, app text, env text, target_platform text,
      runtime text, target_channel text, publication_sequence numeric, digest text
    ) RETURNS TABLE(
      platform text, runtime_sha256 text, channel text, sequence numeric,
      artifact_sha256 text, head_sequence numeric
    ) LANGUAGE sql STABLE SECURITY DEFINER SET search_path = pg_catalog AS $body$
      WITH receipts AS (
        SELECT p.platform,p.runtime_sha256,p.channel,p.sequence,p.artifact_sha256,
               h.sequence AS head_sequence
        FROM #{@bindings} b
        CROSS JOIN LATERAL (VALUES #{reference("ios")}, #{reference("android")})
          AS v(platform,runtime_sha256,channel,sequence,artifact_sha256)
        JOIN #{@heads} h
          ON (h.organization_id,h.project_id,h.application_id,h.environment_id,
              h.platform,h.runtime_sha256,h.channel)
           = (b.organization_id,b.project_id,b.application_id,b.destination_environment_id,
              v.platform,v.runtime_sha256,v.channel)
          AND h.writer_role=session_user
        JOIN #{@publications} p
          ON (p.organization_id,p.project_id,p.application_id,p.environment_id,
              p.platform,p.runtime_sha256,p.channel,p.sequence,p.artifact_sha256)
           = (b.organization_id,b.project_id,b.application_id,b.destination_environment_id,
              v.platform,v.runtime_sha256,v.channel,v.sequence,v.artifact_sha256)
          AND p.action='stage_promote' AND h.sequence >= p.sequence
        WHERE (b.organization_id,b.project_id,b.application_id,b.destination_environment_id)
            = (org,project,app,env)
          AND b.writer_role=session_user
          AND public.mixer_release_read_allowed(org,project,app,env)
          AND ((#{anchor("ios")}) OR (#{anchor("android")}))
      )
      SELECT * FROM receipts WHERE (SELECT count(*) FROM receipts)=2
    $body$
    """)

    execute("REVOKE ALL ON FUNCTION #{@signature} FROM PUBLIC")
  end

  def down do
    execute("DROP FUNCTION #{@signature}")
    execute("DROP POLICY stage_binding_receipt_owner ON #{@bindings}")
  end

  defp reference(platform) do
    fields = ~w(platform runtime_sha256 channel sequence artifact_sha256)
    "(" <> Enum.map_join(fields, ",", &"b.destination_#{platform}_#{&1}") <> ")"
  end

  defp anchor(platform) do
    "target_platform='#{platform}' AND #{reference(platform)} = " <>
      "(target_platform,runtime,target_channel,publication_sequence,digest)"
  end
end
