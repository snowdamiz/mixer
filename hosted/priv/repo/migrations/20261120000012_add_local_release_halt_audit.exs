defmodule MixerHosted.Repo.Migrations.AddLocalReleaseHaltAudit do
  use Ecto.Migration

  @function "public.mixer_release_audit_halts(text,text,text,text,text,text,text,numeric,integer)"

  def up do
    execute("""
    CREATE FUNCTION public.mixer_release_audit_halts(
      org text, project text, app text, env text, target_platform text,
      runtime text, target_channel text, after_sequence numeric, page_limit integer
    ) RETURNS TABLE(sequence numeric,previous_sequence numeric,artifact_sha256 text,
                    health_activated numeric,health_pending numeric,health_adverse_signals numeric)
    LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = pg_catalog AS $body$
    BEGIN
      IF after_sequence IS NULL OR after_sequence NOT BETWEEN 0 AND 18446744073709551615
        OR after_sequence <> trunc(after_sequence)
        OR page_limit IS NULL OR page_limit NOT BETWEEN 1 AND 100
        OR current_setting('mixer.authz.directory_mode',true) IS DISTINCT FROM ''
        OR coalesce(current_setting('mixer.authz.transaction_marker',true),'') !~ '^[0-9a-f]{64}$'
        OR NOT public.mixer_customer_allowed(org,project,'','','audit.read',false)
      THEN
        RETURN;
      END IF;

      RETURN QUERY
        SELECT p.sequence,p.previous_sequence,p.artifact_sha256,p.health_activated,
               p.health_pending,p.health_adverse_signals
        FROM public.mixer_release_publications p
        WHERE (p.organization_id,p.project_id,p.application_id,p.environment_id,
               p.platform,p.runtime_sha256,p.channel)
            = (org,project,app,env,target_platform,runtime,target_channel)
          AND p.action='halt' AND p.sequence>after_sequence
        ORDER BY p.sequence
        LIMIT page_limit;
    END
    $body$
    """)

    execute("REVOKE ALL ON FUNCTION #{@function} FROM PUBLIC")
  end

  def down, do: execute("DROP FUNCTION #{@function}")
end
