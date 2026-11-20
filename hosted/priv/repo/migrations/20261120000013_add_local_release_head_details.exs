defmodule MixerHosted.Repo.Migrations.AddLocalReleaseHeadDetails do
  use Ecto.Migration

  @function "public.mixer_release_head_details(text,text,text,text,text,text,text)"

  def up do
    execute("""
    CREATE FUNCTION public.mixer_release_head_details(
      org text, project text, app text, env text, target_platform text,
      runtime text, target_channel text
    ) RETURNS TABLE(
      sequence numeric, signed_assignment_bytes bytea, rollout_basis_points integer,
      artifact_sha256 text, payload_sha256 text, action text,
      signed_manifest_bytes bytea, canonical_manifest_cbor bytea
    ) LANGUAGE sql STABLE SECURITY DEFINER SET search_path = pg_catalog
    AS $body$
      SELECT h.sequence, p.signed_assignment_bytes, p.rollout_basis_points,
             p.artifact_sha256, a.payload_sha256, p.action,
             a.signed_manifest_bytes, a.canonical_manifest_cbor
      FROM public.mixer_release_heads h
      LEFT JOIN public.mixer_release_publications p
        USING (organization_id,project_id,application_id,environment_id,platform,runtime_sha256,channel,sequence)
      LEFT JOIN public.mixer_customer_artifacts a
        ON (a.organization_id,a.project_id,a.application_id,a.environment_id,a.platform,a.runtime_sha256,a.manifest_sha256)
         = (h.organization_id,h.project_id,h.application_id,h.environment_id,h.platform,h.runtime_sha256,p.artifact_sha256)
      WHERE (h.organization_id,h.project_id,h.application_id,h.environment_id,h.platform,h.runtime_sha256,h.channel)
          = (org,project,app,env,target_platform,runtime,target_channel)
        AND h.writer_role = session_user
        AND public.mixer_release_read_allowed(org,project,app,env)
    $body$
    """)

    execute("REVOKE ALL ON FUNCTION #{@function} FROM PUBLIC")
  end

  def down, do: execute("DROP FUNCTION #{@function}")
end
