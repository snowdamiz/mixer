defmodule MixerHosted.BrowserAuth.ActivationPreparationSchema do
  @moduledoc """
  Opt-in additive SQL prerequisite for provisional activation preparation.

  This does not alter StorageSchema, install a migration, enable a route, or
  provide combined version-2 catalog admission. A reviewed operator installs
  `statements/0`, then separately selects the upgrade-only provisioning plan.
  Preparation metadata is never authentication or a durable authority ticket.
  """
  @name "mixer_browser_prepare_activation"
  @signature "bytea,bytea,bytea,bytea,bigint,public.mixer_browser_access_evidence"
  @type_name "mixer_browser_access_evidence"
  @fields [
    {"profile_id", "text"},
    {"profile_version", "integer"},
    {"issuer", "text"},
    {"subject", "text"},
    {"client_id", "text"},
    {"credential_ref", "text"},
    {"issued_at", "bigint"},
    {"expires_at", "bigint"},
    {"scopes", "text[]"}
  ]
  @decoder_source Path.expand("activation_preparation.ex", __DIR__)
  @external_resource @decoder_source
  @decoder_sha256 :crypto.hash(:sha256, File.read!(@decoder_source))
                  |> Base.encode16(case: :lower)
  @settings [
    "search_path=pg_catalog",
    "statement_timeout=5s",
    "lock_timeout=500ms",
    "idle_in_transaction_session_timeout=5s",
    "bytea_output=hex"
  ]

  def signatures, do: %{@name => @signature}
  def public_signatures, do: signatures()

  @doc "Partial version-2 addition only; no complete admission consumer is supplied."
  def catalog_manifest do
    [_, body, _] = String.split(function(), "$preparation$")

    %{
      version: 2,
      baseline_version: 1,
      additive_only: true,
      functions: %{
        @name => %{
          signature: @signature,
          source: body,
          returns: "jsonb",
          argument_names: ~w(p_cookie p_state p_config p_claim p_revision i),
          settings: @settings,
          security_definer: true,
          runtime_execute: true
        }
      },
      composites: %{@type_name => @fields},
      decoder: %{
        module: "MixerHosted.BrowserAuth.ActivationPreparation",
        source_sha256: @decoder_sha256
      }
    }
  end

  @doc "Inert installation only; PUBLIC gets neither execution nor type usage."
  def statements do
    [
      "CREATE TYPE public.#{@type_name} AS (" <>
        Enum.map_join(@fields, ",", fn {name, type} -> name <> " " <> type end) <> ")",
      function(),
      "REVOKE ALL ON FUNCTION public.#{@name}(#{@signature}) FROM PUBLIC",
      "REVOKE ALL ON TYPE public.#{@type_name} FROM PUBLIC"
    ]
  end

  @doc "Upgrade existing roles only. Execute the returned transaction without omission/reordering."
  def provisioning_statements(writer_role, lifecycle_login, relation_owner) do
    writer = role!(writer_role)
    login = role!(lifecycle_login)
    owner = role!(relation_owner)

    if length(Enum.uniq([writer, login, owner])) != 3,
      do: raise(ArgumentError, "distinct lifecycle roles required")

    [
      "BEGIN",
      "SET LOCAL statement_timeout='5s'",
      "SET LOCAL lock_timeout='500ms'",
      "SET LOCAL idle_in_transaction_session_timeout='5s'",
      provisioning_preflight(writer, login, owner),
      "GRANT CREATE ON SCHEMA public TO #{writer}",
      "ALTER FUNCTION public.#{@name}(#{@signature}) OWNER TO #{writer}",
      "REVOKE CREATE ON SCHEMA public FROM #{writer}",
      "ALTER TYPE public.#{@type_name} OWNER TO #{owner}",
      "GRANT USAGE ON TYPE public.#{@type_name} TO #{writer}, #{login}",
      "GRANT EXECUTE ON FUNCTION public.#{@name}(#{@signature}) TO #{login}",
      """
      DO $finish$
      DECLARE w oid:='#{writer}'::pg_catalog.regrole;
        l oid:='#{login}'::pg_catalog.regrole; o oid:='#{owner}'::pg_catalog.regrole;
      BEGIN
        IF pg_catalog.has_schema_privilege(w,'public','CREATE')
          OR (SELECT proowner FROM pg_catalog.pg_proc WHERE oid='public.#{@name}(#{@signature})'::pg_catalog.regprocedure) IS DISTINCT FROM w
          OR (SELECT typowner FROM pg_catalog.pg_type WHERE oid='public.#{@type_name}'::pg_catalog.regtype) IS DISTINCT FROM o
          OR (SELECT count(*)<>2 OR count(DISTINCT grantee)<>2 OR
                bool_or(grantor<>w OR grantee NOT IN(w,l) OR privilege_type<>'EXECUTE' OR is_grantable)
              FROM pg_catalog.aclexplode(COALESCE(
                (SELECT proacl FROM pg_catalog.pg_proc WHERE oid='public.#{@name}(#{@signature})'::pg_catalog.regprocedure),
                pg_catalog.acldefault('f',w))))
          OR (SELECT count(*)<>3 OR count(DISTINCT grantee)<>3 OR
                bool_or(grantor<>o OR grantee NOT IN(o,w,l) OR privilege_type<>'USAGE' OR is_grantable)
              FROM pg_catalog.aclexplode(COALESCE(
                (SELECT typacl FROM pg_catalog.pg_type WHERE oid='public.#{@type_name}'::pg_catalog.regtype),
                pg_catalog.acldefault('T',o)))) THEN
          RAISE EXCEPTION 'browser preparation provisioning denied' USING ERRCODE='42501';
        END IF;
      END $finish$;
      """,
      "COMMIT"
    ]
  end

  @doc "Remove this addition only; never replay baseline rollback/provisioning."
  def rollback_statements do
    [
      "DROP FUNCTION public.#{@name}(#{@signature})",
      "DROP TYPE public.#{@type_name}"
    ]
  end

  defp role!(name) when is_binary(name) and byte_size(name) in 1..63 do
    valid =
      name != "public" and not String.starts_with?(name, "pg_") and
        name
        |> :binary.bin_to_list()
        |> Enum.with_index()
        |> Enum.all?(fn {c, i} -> c in ?a..?z or c == ?_ or (i > 0 and c in ?0..?9) end)

    if valid, do: name, else: raise(ArgumentError, "restricted role identifier required")
  end

  defp role!(_), do: raise(ArgumentError, "restricted role identifier required")

  defp provisioning_preflight(writer, login, owner) do
    """
    DO $upgrade$
    DECLARE w pg_catalog.pg_roles; l pg_catalog.pg_roles; o pg_catalog.pg_roles;
    BEGIN
      SELECT * INTO STRICT w FROM pg_catalog.pg_roles WHERE rolname='#{writer}';
      SELECT * INTO STRICT l FROM pg_catalog.pg_roles WHERE rolname='#{login}';
      SELECT * INTO STRICT o FROM pg_catalog.pg_roles WHERE rolname='#{owner}';
      IF w.rolcanlogin OR NOT l.rolcanlogin OR o.rolcanlogin
        OR w.rolsuper OR w.rolbypassrls OR w.rolcreaterole OR w.rolcreatedb OR w.rolreplication OR w.rolinherit
        OR l.rolsuper OR l.rolbypassrls OR l.rolcreaterole OR l.rolcreatedb OR l.rolreplication OR l.rolinherit
        OR o.rolsuper OR o.rolbypassrls OR o.rolcreaterole OR o.rolcreatedb OR o.rolreplication OR o.rolinherit
        OR EXISTS(SELECT 1 FROM pg_catalog.pg_auth_members WHERE member IN(w.oid,l.oid,o.oid) OR roleid IN(w.oid,l.oid,o.oid))
        OR EXISTS(SELECT 1 FROM pg_catalog.pg_namespace WHERE
          pg_catalog.has_schema_privilege(w.oid,oid,'CREATE') OR pg_catalog.has_schema_privilege(l.oid,oid,'CREATE'))
        OR NOT pg_catalog.has_schema_privilege(w.oid,'public','USAGE')
        OR NOT pg_catalog.has_schema_privilege(l.oid,'public','USAGE')
        OR EXISTS(SELECT 1 FROM pg_catalog.pg_class WHERE relowner IN(w.oid,l.oid))
        OR EXISTS(SELECT 1 FROM pg_catalog.pg_namespace WHERE nspowner IN(w.oid,l.oid))
        OR EXISTS(SELECT 1 FROM pg_catalog.pg_database WHERE datdba IN(w.oid,l.oid))
        OR EXISTS(SELECT 1 FROM pg_catalog.pg_database WHERE datname=pg_catalog.current_database()
          AND (pg_catalog.has_database_privilege(w.oid,oid,'CREATE') OR pg_catalog.has_database_privilege(l.oid,oid,'CREATE')))
        OR EXISTS(SELECT 1 FROM pg_catalog.pg_class c JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace
          WHERE n.nspname='public' AND c.relkind IN('r','p','v','m','f') AND
            (pg_catalog.has_table_privilege(l.oid,c.oid,'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER')
             OR pg_catalog.has_any_column_privilege(l.oid,c.oid,'SELECT,INSERT,UPDATE,REFERENCES')))
        OR (SELECT count(*) FROM pg_catalog.pg_class c JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace
          WHERE n.nspname='public' AND c.relname IN('mixer_browser_sessions','mixer_browser_session_vault','mixer_browser_oidc_attempts','mixer_browser_session_events')
            AND c.relowner=o.oid AND c.relrowsecurity AND c.relforcerowsecurity)<>4
        OR (SELECT count(*) FROM pg_catalog.pg_type t JOIN pg_catalog.pg_namespace n ON n.oid=t.typnamespace
          WHERE n.nspname='public' AND t.typname IN('mixer_browser_cipher','mixer_browser_attempt','mixer_browser_verified') AND t.typowner=o.oid
            AND pg_catalog.has_type_privilege(w.oid,t.oid,'USAGE') AND pg_catalog.has_type_privilege(l.oid,t.oid,'USAGE'))<>3
        OR (SELECT count(*) FROM pg_catalog.pg_proc p JOIN pg_catalog.pg_namespace n ON n.oid=p.pronamespace
          WHERE n.nspname='public' AND pg_catalog.left(p.proname::text,14)='mixer_browser_' AND p.proname<>'#{@name}' AND p.proowner=w.oid)<>18
        OR (SELECT count(*) FROM pg_catalog.pg_proc p JOIN pg_catalog.pg_namespace n ON n.oid=p.pronamespace
          WHERE n.nspname='public' AND pg_catalog.left(p.proname::text,14)='mixer_browser_' AND p.proname<>'#{@name}'
            AND pg_catalog.has_function_privilege(l.oid,p.oid,'EXECUTE'))<>9
        OR (SELECT typowner FROM pg_catalog.pg_type WHERE oid='public.#{@type_name}'::pg_catalog.regtype)<>o.oid
        OR (SELECT proowner FROM pg_catalog.pg_proc WHERE oid='public.#{@name}(#{@signature})'::pg_catalog.regprocedure)<>o.oid
        OR (SELECT count(*)<>1 OR bool_or(grantor<>o.oid OR grantee<>o.oid OR privilege_type<>'EXECUTE' OR is_grantable)
            FROM pg_catalog.aclexplode(COALESCE(
              (SELECT proacl FROM pg_catalog.pg_proc WHERE oid='public.#{@name}(#{@signature})'::pg_catalog.regprocedure),
              pg_catalog.acldefault('f',o.oid))))
        OR (SELECT count(*)<>1 OR bool_or(grantor<>o.oid OR grantee<>o.oid OR privilege_type<>'USAGE' OR is_grantable)
            FROM pg_catalog.aclexplode(COALESCE(
              (SELECT typacl FROM pg_catalog.pg_type WHERE oid='public.#{@type_name}'::pg_catalog.regtype),
              pg_catalog.acldefault('T',o.oid))))
      THEN RAISE EXCEPTION 'browser preparation provisioning denied' USING ERRCODE='42501'; END IF;
    END $upgrade$;
    """
  end

  defp function do
    """
    CREATE FUNCTION public.#{@name}(p_cookie bytea,p_state bytea,p_config bytea,p_claim bytea,p_revision bigint,i public.mixer_browser_access_evidence) RETURNS jsonb
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path=pg_catalog SET statement_timeout='5s'
    SET lock_timeout='500ms' SET idle_in_transaction_session_timeout='5s' SET bytea_output='hex'
    AS $preparation$
    DECLARE r record; b public.mixer_browser_sessions; v public.mixer_browser_session_vault;
      a public.mixer_browser_oidc_attempts; p public.mixer_authz_profiles;
      binding public.mixer_authz_bindings; principal public.mixer_authz_principals;
      entered bigint; finished bigint; scope text; seen text[]:=ARRAY[]::text[]; scope_bytes integer:=0;
    BEGIN
      entered:=pg_catalog.floor(extract(epoch FROM pg_catalog.clock_timestamp()))::bigint;
      IF p_cookie IS NULL OR octet_length(p_cookie)<>32 OR p_state IS NULL OR octet_length(p_state)<>32
        OR p_config IS NULL OR octet_length(p_config)<>32 OR p_claim IS NULL OR octet_length(p_claim)<>32
        OR p_revision IS NULL OR p_revision NOT BETWEEN 1 AND 9007199254740991
        OR i.profile_id IS NULL OR octet_length(i.profile_id) NOT BETWEEN 1 AND 128
        OR i.profile_version IS NULL OR i.profile_version<=0
        OR i.issuer IS NULL OR octet_length(i.issuer) NOT BETWEEN 1 AND 2048
        OR i.subject IS NULL OR octet_length(i.subject) NOT BETWEEN 1 AND 256
        OR i.client_id IS NULL OR octet_length(i.client_id) NOT BETWEEN 1 AND 256
        OR i.credential_ref IS NULL OR octet_length(i.credential_ref) NOT BETWEEN 1 AND 256
        OR i.issued_at IS NULL OR i.issued_at NOT BETWEEN 0 AND 9007199254740991 OR i.issued_at>entered+30
        OR i.expires_at IS NULL OR i.expires_at NOT BETWEEN 0 AND 9007199254740991
        OR i.expires_at<=GREATEST(entered,i.issued_at) OR i.expires_at-i.issued_at>900
        OR i.scopes IS NULL OR pg_catalog.array_ndims(i.scopes) IS DISTINCT FROM 1
        OR pg_catalog.array_lower(i.scopes,1) IS DISTINCT FROM 1 OR pg_catalog.cardinality(i.scopes) NOT BETWEEN 1 AND 64
        OR ('mixer.workspace.read'=ANY(i.scopes)) IS NOT TRUE
      THEN RAISE EXCEPTION 'browser session unavailable' USING ERRCODE='P0001'; END IF;
      -- PostgreSQL UTF8 text cannot contain NUL. These bounded parameter-only
      -- checks do not read relations or create an additional MVCC snapshot.
      FOREACH scope IN ARRAY i.scopes LOOP
        IF scope IS NULL OR octet_length(scope) NOT BETWEEN 1 AND 1024
          OR scope ~ '[^!#-~]' OR pg_catalog.strpos(scope,pg_catalog.chr(92))>0 OR scope=ANY(seen)
        THEN RAISE EXCEPTION 'browser session unavailable' USING ERRCODE='P0001'; END IF;
        scope_bytes:=scope_bytes+octet_length(scope)+1;
        IF scope_bytes>1025 THEN RAISE EXCEPTION 'browser session unavailable' USING ERRCODE='P0001'; END IF;
        seen:=pg_catalog.array_append(seen,scope);
      END LOOP;
      -- Every relation and the exact JSON projection share this one statement
      -- snapshot. Unique indexes bound each join; LIMIT 2 + STRICT denies extras.
      SELECT s AS browser,sv AS vault,oa AS attempt,ap AS profile,ab AS binding,pr AS principal,
        pg_catalog.jsonb_build_object('browser',pg_catalog.to_jsonb(s),'vault',pg_catalog.to_jsonb(sv),'attempt',pg_catalog.to_jsonb(oa)) AS snapshot
      INTO STRICT r
      FROM public.mixer_browser_sessions s
      JOIN public.mixer_browser_session_vault sv ON sv.browser_id=s.id
      JOIN public.mixer_browser_oidc_attempts oa ON oa.state_digest=p_state AND oa.browser_id=s.id
      LEFT JOIN public.mixer_authz_profiles ap ON ap.id=i.profile_id AND ap.version=i.profile_version
      LEFT JOIN public.mixer_authz_bindings ab ON ab.profile_id=i.profile_id AND ab.profile_version=i.profile_version AND ab.subject=i.subject
      LEFT JOIN public.mixer_authz_principals pr ON pr.id=ab.principal_id
      WHERE s.cookie_digest=p_cookie
      LIMIT 2;
      b:=r.browser; v:=r.vault; a:=r.attempt; p:=r.profile; binding:=r.binding; principal:=r.principal;
      finished:=pg_catalog.floor(extract(epoch FROM pg_catalog.clock_timestamp()))::bigint;
      -- Claim validity is checked before binding state can be disclosed.
      IF finished<entered OR (b.status IS DISTINCT FROM 'preauth' AND b.status IS DISTINCT FROM 'active') OR b.revision IS DISTINCT FROM p_revision
        OR b.config_digest IS DISTINCT FROM p_config OR b.epoch IS NULL OR b.epoch NOT BETWEEN 1 AND 9007199254740991
        OR b.generation IS NULL OR b.expected_profile_id IS DISTINCT FROM i.profile_id OR b.expected_profile_version IS DISTINCT FROM i.profile_version
        OR b.created_at IS NULL OR b.created_at NOT BETWEEN 0 AND 9007199254740991
        OR b.last_seen_at IS NULL OR b.last_seen_at<b.created_at
        OR b.absolute_expires_at IS NULL OR b.absolute_expires_at NOT BETWEEN 0 AND 9007199254740991
        OR b.idle_expires_at IS NULL OR b.idle_expires_at<=b.last_seen_at OR b.idle_expires_at>b.absolute_expires_at
        OR entered>=b.absolute_expires_at OR entered>=b.idle_expires_at OR finished>=b.absolute_expires_at OR finished>=b.idle_expires_at
        OR v.browser_id IS DISTINCT FROM b.id OR v.epoch IS DISTINCT FROM b.epoch OR v.session_revision IS DISTINCT FROM b.revision
        OR v.vault_generation IS NULL OR v.vault_generation NOT BETWEEN 1 AND 9007199254740991 OR v.envelope_kind IS DISTINCT FROM b.status
        OR v.ciphertext_version IS DISTINCT FROM 1
        OR NOT public.mixer_browser_cipher_valid(ROW(v.key_id,v.iv,v.tag,v.ciphertext)::public.mixer_browser_cipher)
        OR a.status IS DISTINCT FROM 'claimed' OR a.browser_id IS DISTINCT FROM b.id
        OR a.browser_epoch IS DISTINCT FROM b.epoch OR a.browser_revision IS DISTINCT FROM b.revision
        OR a.cookie_digest IS DISTINCT FROM b.cookie_digest OR a.generation IS DISTINCT FROM b.generation OR a.config_digest IS DISTINCT FROM b.config_digest
        OR a.created_at IS NULL OR a.created_at<b.created_at OR a.expires_at IS NULL
        OR a.expires_at NOT BETWEEN 0 AND 9007199254740991 OR a.expires_at<=a.created_at OR a.expires_at>a.created_at+300
        OR a.claim_digest IS DISTINCT FROM p_claim OR a.claimed_at IS NULL OR a.claimed_at< a.created_at
        OR a.claimed_at>entered OR a.claim_expires_at IS NULL OR a.claim_expires_at<=a.claimed_at OR a.claim_expires_at>a.expires_at OR a.claim_expires_at>a.claimed_at+60
        OR entered>=a.expires_at OR entered>=a.claim_expires_at OR finished>=a.expires_at OR finished>=a.claim_expires_at
        OR a.profile_id IS DISTINCT FROM i.profile_id OR a.profile_version IS DISTINCT FROM i.profile_version
        OR a.issuer IS DISTINCT FROM i.issuer OR a.client_id IS DISTINCT FROM i.client_id
        OR a.redirect_uri IS NULL OR octet_length(a.redirect_uri) NOT BETWEEN 1 AND 2048 OR a.return_route IS DISTINCT FROM 'workspace'
        OR a.ciphertext_version IS DISTINCT FROM 1 OR a.key_id IS NOT NULL OR a.iv IS NOT NULL OR a.tag IS NOT NULL OR a.ciphertext IS NOT NULL
        OR a.completion_reason IS NOT NULL OR finished>=i.expires_at
      THEN RAISE EXCEPTION 'browser session unavailable' USING ERRCODE='P0001'; END IF;
      IF p.id IS NULL OR p.id IS DISTINCT FROM b.expected_profile_id OR p.version IS DISTINCT FROM b.expected_profile_version
        OR p.active IS DISTINCT FROM true OR p.identity_class IS DISTINCT FROM 'human'
        OR p.issuer IS DISTINCT FROM i.issuer OR p.client_id IS DISTINCT FROM i.client_id
        OR p.state_revision IS NULL OR p.state_revision NOT BETWEEN 1 AND 9007199254740991
      THEN RAISE EXCEPTION 'browser identity unavailable' USING ERRCODE='P0001'; END IF;
      IF binding.profile_id IS NULL THEN
        RAISE EXCEPTION 'browser onboarding required' USING ERRCODE='P0001';
      END IF;
      IF binding.profile_id IS DISTINCT FROM i.profile_id OR binding.profile_version IS DISTINCT FROM i.profile_version OR binding.subject IS DISTINCT FROM i.subject
        OR binding.active IS DISTINCT FROM true OR binding.identity_class IS DISTINCT FROM 'human'
        OR binding.revision IS NULL OR binding.revision NOT BETWEEN 1 AND 9007199254740991
        OR principal.id IS NULL OR principal.id IS DISTINCT FROM binding.principal_id OR octet_length(principal.id) NOT BETWEEN 1 AND 128
        OR principal.active IS DISTINCT FROM true OR principal.identity_class IS DISTINCT FROM 'human'
        OR principal.revision IS NULL OR principal.revision NOT BETWEEN 1 AND 9007199254740991
        OR principal.not_before IS NULL OR principal.not_before>entered OR i.issued_at<principal.not_before
      THEN RAISE EXCEPTION 'browser identity unavailable' USING ERRCODE='P0001'; END IF;
      finished:=pg_catalog.floor(extract(epoch FROM pg_catalog.clock_timestamp()))::bigint;
      IF finished<entered OR finished>=b.absolute_expires_at OR finished>=b.idle_expires_at
        OR finished>=a.expires_at OR finished>=a.claim_expires_at OR finished>=i.expires_at THEN
        RAISE EXCEPTION 'browser session unavailable' USING ERRCODE='P0001';
      END IF;
      RETURN pg_catalog.jsonb_build_object('version',1,'snapshot',r.snapshot,'principal_id',principal.id,
        'profile_revision',p.state_revision,'binding_revision',binding.revision,'principal_revision',principal.revision);
    EXCEPTION WHEN no_data_found OR too_many_rows THEN
      RAISE EXCEPTION 'browser session unavailable' USING ERRCODE='P0001';
    END;
    $preparation$
    """
  end
end
