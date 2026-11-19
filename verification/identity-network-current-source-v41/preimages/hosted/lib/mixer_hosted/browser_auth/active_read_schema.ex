defmodule MixerHosted.BrowserAuth.ActiveReadSchema do
  @moduledoc "Private unselected DDL. Not a production migration."
  @name "mixer_browser_current_active_load"
  @signature "bytea,bytea,bigint,public.mixer_browser_access_evidence"
  @settings [
    "search_path=pg_catalog",
    "statement_timeout=5s",
    "lock_timeout=500ms",
    "idle_in_transaction_session_timeout=5s",
    "bytea_output=hex"
  ]
  def manifest do
    [_, source, _] = String.split(function(), "$active_read$")

    %{
      @name => %{
        signature: @signature,
        source: source,
        returns: "jsonb",
        argument_names: ~w(p_cookie p_config p_revision i),
        settings: @settings,
        security_definer: true,
        runtime_execute: true
      }
    }
  end

  def statements,
    do: [function(), "REVOKE ALL ON FUNCTION public.#{@name}(#{@signature}) FROM PUBLIC"]

  def provisioning_statements do
    [
      "BEGIN",
      "SET LOCAL lock_timeout='500ms'",
      "GRANT CREATE ON SCHEMA public TO browser_writer",
      "ALTER FUNCTION public.#{@name}(#{@signature}) OWNER TO browser_writer",
      "REVOKE CREATE ON SCHEMA public FROM browser_writer",
      "SET LOCAL ROLE browser_writer",
      "GRANT EXECUTE ON FUNCTION public.#{@name}(#{@signature}) TO browser_lifecycle",
      "COMMIT"
    ]
  end

  def function do
    """
    CREATE FUNCTION public.mixer_browser_current_active_load(p_cookie bytea,p_config bytea,p_revision bigint,i public.mixer_browser_access_evidence)
    RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER
    SET search_path=pg_catalog SET statement_timeout='5s' SET lock_timeout='500ms'
    SET idle_in_transaction_session_timeout='5s' SET bytea_output='hex'
    AS $active_read$
    DECLARE d public.mixer_browser_sessions; b public.mixer_browser_sessions;
      p public.mixer_authz_profiles; binding public.mixer_authz_bindings;
      principal public.mixer_authz_principals; f public.mixer_authz_families;
      c public.mixer_authz_credentials; v public.mixer_browser_session_vault;
      entered bigint; n bigint; expires bigint; cnt integer;
    BEGIN
      entered:=pg_catalog.floor(extract(epoch FROM pg_catalog.clock_timestamp()))::bigint;
      IF p_cookie IS NULL OR octet_length(p_cookie)<>32 OR p_config IS NULL OR octet_length(p_config)<>32
        OR p_revision IS NULL OR p_revision NOT BETWEEN 1 AND 9007199254740991
        OR i.profile_id IS NULL OR i.profile_version IS NULL OR i.subject IS NULL
        OR i.issuer IS NULL OR i.client_id IS NULL OR i.credential_ref IS NULL
        OR i.issued_at IS NULL OR i.issued_at<0 OR i.issued_at>entered+30
        OR i.expires_at IS NULL OR i.expires_at<=GREATEST(entered,i.issued_at)
        OR i.scopes IS NULL OR ('mixer.workspace.read'=ANY(i.scopes)) IS NOT TRUE
      THEN RAISE EXCEPTION 'browser session unavailable' USING ERRCODE='P0001'; END IF;
      SELECT * INTO STRICT d FROM public.mixer_browser_sessions WHERE cookie_digest=p_cookie;
      -- Same shared authority lock order as activation and ordinary authz.
      SELECT * INTO STRICT p FROM public.mixer_authz_profiles WHERE id=d.profile_id AND version=d.profile_version FOR UPDATE;
      SELECT * INTO STRICT binding FROM public.mixer_authz_bindings WHERE profile_id=p.id AND profile_version=p.version AND subject=i.subject;
      SELECT * INTO STRICT principal FROM public.mixer_authz_principals WHERE id=d.principal_id FOR UPDATE;
      SELECT * INTO STRICT f FROM public.mixer_authz_families WHERE id=d.family_id FOR UPDATE;
      PERFORM 1 FROM public.mixer_authz_credentials WHERE family_id=d.family_id ORDER BY profile_id COLLATE "C",profile_version,reference COLLATE "C" LIMIT 2 FOR UPDATE;
      SELECT count(*) INTO cnt FROM (SELECT 1 FROM public.mixer_authz_credentials WHERE family_id=d.family_id LIMIT 2) bounded;
      SELECT * INTO STRICT c FROM public.mixer_authz_credentials WHERE profile_id=d.profile_id AND profile_version=d.profile_version AND reference=d.credential_ref;
      SELECT * INTO STRICT b FROM public.mixer_browser_sessions WHERE id=d.id FOR SHARE;
      SELECT * INTO STRICT v FROM public.mixer_browser_session_vault WHERE browser_id=b.id FOR SHARE;
      n:=pg_catalog.floor(extract(epoch FROM pg_catalog.clock_timestamp()))::bigint;
      IF n<entered OR b IS DISTINCT FROM d OR b.status IS DISTINCT FROM 'active'
        OR b.revision IS DISTINCT FROM p_revision OR b.config_digest IS DISTINCT FROM p_config OR b.initial_config_digest IS DISTINCT FROM p_config
        OR b.expected_profile_id IS DISTINCT FROM p.id OR b.expected_profile_version IS DISTINCT FROM p.version
        OR p.id IS DISTINCT FROM i.profile_id OR p.version IS DISTINCT FROM i.profile_version
        OR p.issuer IS DISTINCT FROM i.issuer OR p.client_id IS DISTINCT FROM i.client_id
        OR p.active IS DISTINCT FROM true OR p.identity_class IS DISTINCT FROM 'human'
        OR binding.active IS DISTINCT FROM true OR binding.identity_class IS DISTINCT FROM 'human'
        OR binding.principal_id IS DISTINCT FROM b.principal_id OR binding.revision<1 OR p.state_revision<1
        OR principal.active IS DISTINCT FROM true OR principal.identity_class IS DISTINCT FROM 'human'
        OR i.issued_at<principal.not_before OR principal.not_before>n
        OR f.active IS DISTINCT FROM true OR f.profile_id IS DISTINCT FROM p.id OR f.profile_version IS DISTINCT FROM p.version
        OR f.principal_id IS DISTINCT FROM principal.id OR i.issued_at<f.not_before OR f.not_before>n
        OR cnt<>1 OR c.active IS DISTINCT FROM true OR c.principal_id IS DISTINCT FROM principal.id
        OR c.family_id IS DISTINCT FROM f.id OR c.reference IS DISTINCT FROM i.credential_ref
        OR c.revision IS DISTINCT FROM b.credential_revision OR i.issued_at<c.not_before OR c.not_before>n
        OR v.envelope_kind IS DISTINCT FROM 'active' OR v.epoch IS DISTINCT FROM b.epoch OR v.session_revision IS DISTINCT FROM b.revision
        OR NOT public.mixer_browser_cipher_valid(ROW(v.key_id,v.iv,v.tag,v.ciphertext)::public.mixer_browser_cipher)
      THEN RAISE EXCEPTION 'browser session unavailable' USING ERRCODE='P0001'; END IF;
      expires:=LEAST(b.absolute_expires_at,b.idle_expires_at,i.expires_at,f.expires_at,c.expires_at);
      n:=pg_catalog.floor(extract(epoch FROM pg_catalog.clock_timestamp()))::bigint;
      IF n<entered OR n>=expires THEN RAISE EXCEPTION 'browser session unavailable' USING ERRCODE='P0001'; END IF;
      RETURN pg_catalog.jsonb_build_object('version',1,'expires_at',expires,'snapshot',public.mixer_browser_snapshot(b.id,NULL));
    EXCEPTION WHEN no_data_found OR too_many_rows THEN
      RAISE EXCEPTION 'browser session unavailable' USING ERRCODE='P0001';
    END;
    $active_read$
    """
  end
end
