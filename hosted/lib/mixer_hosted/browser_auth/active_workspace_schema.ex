defmodule MixerHosted.BrowserAuth.ActiveWorkspaceSchema do
  @moduledoc false
  alias MixerHosted.BrowserAuth.ActiveReadSchema

  @name "mixer_browser_workspace_admit"
  @signature "bytea,bytea,bigint,text,text,text,text,integer,text,text,text,text,bigint,bigint,text[]"
  @settings Map.fetch!(ActiveReadSchema.manifest(), "mixer_browser_current_active_load").settings

  def manifest do
    [_, source, _] = String.split(function(), "$workspace_admit$")

    %{
      @name => %{
        signature: @signature,
        source: source,
        returns: "bigint",
        settings: @settings,
        runtime_execute: false,
        argument_names:
          ~w(p_cookie p_config p_revision p_generation p_actor p_family
          p_profile p_version p_issuer p_subject p_client p_credential p_issued p_expires p_scopes)
      }
    }
  end

  def provisioning_statements(ordinary_login) do
    true = Regex.match?(~r/\A[a-z_][a-z0-9_]{0,62}\z/, ordinary_login)
    true = ordinary_login != "public" and not String.starts_with?(ordinary_login, "pg_")

    [
      "BEGIN",
      "SET LOCAL lock_timeout='500ms'",
      function(),
      "REVOKE ALL ON FUNCTION public.#{@name}(#{@signature}) FROM PUBLIC",
      "GRANT CREATE ON SCHEMA public TO browser_writer",
      "ALTER FUNCTION public.#{@name}(#{@signature}) OWNER TO browser_writer",
      "REVOKE CREATE ON SCHEMA public FROM browser_writer",
      "SET LOCAL ROLE browser_writer",
      ~s|GRANT EXECUTE ON FUNCTION public.#{@name}(#{@signature}) TO "#{ordinary_login}"|,
      "COMMIT"
    ]
  end

  def rollback_statement, do: "DROP FUNCTION IF EXISTS public.#{@name}(#{@signature})"

  def function do
    """
    CREATE FUNCTION public.#{@name}(p_cookie bytea,p_config bytea,p_revision bigint,
      p_generation text,p_actor text,p_family text,p_profile text,p_version integer,
      p_issuer text,p_subject text,p_client text,p_credential text,p_issued bigint,
      p_expires bigint,p_scopes text[])
    RETURNS bigint LANGUAGE plpgsql SECURITY DEFINER
    SET search_path=pg_catalog SET statement_timeout='5s' SET lock_timeout='500ms'
    SET idle_in_transaction_session_timeout='5s' SET bytea_output='hex'
    AS $workspace_admit$
    DECLARE admission jsonb; browser jsonb;
    BEGIN
      IF p_generation IS NULL OR p_actor IS NULL OR p_family IS NULL
        OR ('mixer.workspace.manage'=ANY(p_scopes)) IS NOT TRUE
      THEN RAISE EXCEPTION 'browser workspace unavailable' USING ERRCODE='P0001'; END IF;

      -- Reuse the current-authority check and retain its locks through the caller's commit.
      admission:=public.mixer_browser_current_active_load(p_cookie,p_config,p_revision,
        ROW(p_profile,p_version,p_issuer,p_subject,p_client,p_credential,p_issued,p_expires,p_scopes)
          ::public.mixer_browser_access_evidence);
      browser:=admission->'snapshot'->'browser';
      IF browser->>'generation' IS DISTINCT FROM p_generation
        OR browser->>'principal_id' IS DISTINCT FROM p_actor
        OR browser->>'family_id' IS DISTINCT FROM p_family
      THEN RAISE EXCEPTION 'browser workspace unavailable' USING ERRCODE='P0001'; END IF;
      RETURN (admission->>'expires_at')::bigint;
    END;
    $workspace_admit$
    """
  end
end
