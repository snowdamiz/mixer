defmodule MixerHosted.Repo.Migrations.AddLocalReleaseHeadRead do
  use Ecto.Migration

  @scope ~w(organization_id project_id application_id environment_id)
  @artifact_identity @scope ++ ~w(platform runtime_sha256)
  @head_identity @artifact_identity ++ ["channel"]
  @heads "public.mixer_release_heads"
  @entries "public.mixer_release_publications"
  @artifact_function "public.mixer_release_bound_artifact(text,text,text,text,text,text,text,text)"

  def up do
    scope_condition =
      Enum.map_join(@scope, " AND ", fn field ->
        "#{field} = current_setting('mixer.authz.#{field}', true)"
      end)

    execute("""
    CREATE POLICY release_browser_head ON #{@heads} FOR SELECT USING (
      current_user = session_user AND current_user = writer_role
      AND public.mixer_release_read_allowed(#{Enum.join(@scope, ",")})
    )
    """)

    # Publishers need the retained rows for retries. Browser readers see only
    # the publication referenced by the head.
    set_publication_visibility("""
    AND (current_setting('mixer.authz.action', true) = 'release.publish'
         OR h.sequence = mixer_release_publications.sequence)
    """)

    execute("""
    CREATE POLICY release_publish_only ON #{@entries} AS RESTRICTIVE FOR INSERT
      WITH CHECK (current_setting('mixer.authz.action', true) = 'release.publish')
    """)

    # The artifact store keeps its existing RLS and writer grants. This helper
    # reads under the non-login relation owner and can see only the caller's
    # provisioned head and its exact immutable artifact rows.
    execute("""
    CREATE POLICY release_bound_artifact_owner ON #{@heads} FOR SELECT USING (
      current_user <> session_user AND writer_role = session_user
      AND current_user = pg_catalog.pg_get_userbyid(
        (SELECT relowner FROM pg_catalog.pg_class WHERE oid = '#{@heads}'::regclass))
      AND current_setting('mixer.authz.action', true) IN ('release.publish', 'release.read')
      AND current_setting('mixer.authz.phase', true) = 'effect'
      AND #{scope_condition}
    )
    """)

    bind_artifact = Enum.map_join(@artifact_identity, " AND ", &"a.#{&1} = h.#{&1}")

    bind_publication = Enum.map_join(@head_identity, " AND ", &"p.#{&1} = h.#{&1}")

    execute("""
    CREATE FUNCTION public.mixer_release_bound_artifact(
      org text, project text, app text, env text, target_platform text,
      runtime text, target_channel text, digest text
    ) RETURNS TABLE(signed_manifest_bytes bytea,payload bytea,payload_sha256 text)
    LANGUAGE sql STABLE SECURITY DEFINER SET search_path = pg_catalog
    AS $body$
      SELECT CASE WHEN current_setting('mixer.authz.action', true) = 'release.publish'
                  THEN a.signed_manifest_bytes END,
             CASE WHEN current_setting('mixer.authz.action', true) = 'release.publish'
                  THEN a.payload END,
             a.payload_sha256
      FROM #{@heads} h
      JOIN public.mixer_customer_artifacts a ON #{bind_artifact}
      WHERE (h.organization_id,h.project_id,h.application_id,h.environment_id,h.platform,h.runtime_sha256,h.channel)
          = (org,project,app,env,target_platform,runtime,target_channel)
        AND h.writer_role = session_user
        AND a.manifest_sha256=digest
        AND (public.mixer_release_publish_allowed(org,project,app,env)
             OR (public.mixer_release_read_allowed(org,project,app,env)
                 AND EXISTS (SELECT 1 FROM #{@entries} p
                             WHERE #{bind_publication} AND p.sequence=h.sequence
                               AND p.artifact_sha256=a.manifest_sha256)))
    $body$
    """)

    execute("REVOKE ALL ON FUNCTION #{@artifact_function} FROM PUBLIC")
  end

  def down do
    execute("DROP FUNCTION #{@artifact_function}")
    execute("DROP POLICY release_bound_artifact_owner ON #{@heads}")
    execute("DROP POLICY release_publish_only ON #{@entries}")
    execute("DROP POLICY release_browser_head ON #{@heads}")
    set_publication_visibility("")
  end

  defp set_publication_visibility(sequence_condition) do
    bound = Enum.map_join(@head_identity, " AND ", &"h.#{&1} = mixer_release_publications.#{&1}")

    execute("""
    ALTER POLICY release_read ON #{@entries} USING (
      EXISTS (SELECT 1 FROM #{@heads} h WHERE #{bound} #{sequence_condition})
    )
    """)
  end
end
