defmodule MixerHosted.BrowserAuth.StorageSchema do
  @moduledoc """
  Fixed PostgreSQL lifecycle capability; SQL only, without a running Repo.

  Migration installation is inert. A reviewed operator must separately provision
  existing dedicated roles with `provisioning_statements/2`. This API returns an
  explicit plan and never creates a role, login, password, provider or key.
  Encrypted discovery snapshots are not authentication or verifier evidence.
  """
  @browser_tables ~w(sessions session_vault oidc_attempts session_events)
  @authz_tables ~w(profiles principals bindings families credentials)
  @public_helpers ~w(bootstrap load begin claim provider_reject fail_claim activate logout expire)
  @max 9_007_199_254_740_991

  def maximum_integer, do: @max

  def signatures do
    %{
      "mixer_browser_bootstrap" =>
        "bytea,bytea,text,bytea,bytea,text,integer,bigint,public.mixer_browser_cipher,text",
      "mixer_browser_load" => "bytea,bytea",
      "mixer_browser_begin" =>
        "bytea,bytea,bytea,bigint,public.mixer_browser_attempt,public.mixer_browser_cipher,text",
      "mixer_browser_claim" => "bytea,bytea,bytea,bigint,bytea,bigint,text",
      "mixer_browser_provider_reject" => "bytea,bytea,bytea,bigint,text",
      "mixer_browser_fail_claim" => "bytea,bytea,bytea,bytea,text,text",
      "mixer_browser_activate" =>
        "bytea,bytea,bytea,bytea,bigint,public.mixer_browser_verified,bytea,bytea,text,text,bigint,public.mixer_browser_cipher,text",
      "mixer_browser_logout" => "bytea,bytea,bytea,bigint,text",
      "mixer_browser_expire" => "bytea,bigint,text",
      "mixer_browser_snapshot" => "bytea,bytea",
      "mixer_browser_cipher_valid" => "public.mixer_browser_cipher",
      "mixer_browser_audit" =>
        "public.mixer_browser_sessions,public.mixer_browser_sessions,text,text,bytea,text,public.mixer_browser_verified",
      "mixer_browser_integrity" => "",
      "mixer_browser_attempt_integrity" => "",
      "mixer_browser_event_immutable" => "",
      "mixer_browser_event_integrity" => "",
      "mixer_browser_lock_existing" => "public.mixer_browser_sessions",
      "mixer_browser_revoke_existing" => "public.mixer_browser_sessions,bigint"
    }
  end

  def public_signatures do
    Map.take(signatures(), Enum.map(@public_helpers, &("mixer_browser_" <> &1)))
  end

  @doc "Exact source/configuration manifest for independent catalog admission."
  def catalog_manifest do
    defs =
      Map.new(functions(), fn sql ->
        [head, body, _] = String.split(sql, "$browser$")

        name =
          head
          |> String.split("(", parts: 2)
          |> hd()
          |> String.replace_prefix("CREATE FUNCTION public.", "")

        {name,
         %{
           signature: Map.fetch!(signatures(), name),
           source: body,
           security_definer: true,
           settings: [
             "search_path=pg_catalog",
             "statement_timeout=5s",
             "lock_timeout=500ms",
             "idle_in_transaction_session_timeout=5s",
             "bytea_output=hex"
           ],
           runtime_execute: Map.has_key?(public_signatures(), name)
         }}
      end)

    %{
      version: 1,
      functions: defs,
      relations: Enum.map(@browser_tables, &("mixer_browser_" <> &1)),
      authz_relations: Enum.map(@authz_tables, &("mixer_authz_" <> &1)),
      browser_mutable_columns:
        Map.new(
          ~w(sessions session_vault oidc_attempts),
          &{&1, String.split(mutable_columns(&1), ",")}
        ),
      policies: %{read: "true", insert: "true", update: "true", lock_check: "false"},
      transaction: %{isolation: "read committed", statement_ms: 5000, lock_ms: 500, idle_ms: 5000}
    }
  end

  def statements do
    types() ++
      tables() ++
      functions() ++
      triggers() ++
      Enum.flat_map(@browser_tables, fn name ->
        table = "public.mixer_browser_" <> name

        [
          "ALTER TABLE #{table} ENABLE ROW LEVEL SECURITY",
          "ALTER TABLE #{table} FORCE ROW LEVEL SECURITY",
          "REVOKE ALL ON #{table} FROM PUBLIC"
        ]
      end) ++
      Enum.map(signatures(), fn {name, args} ->
        "REVOKE ALL ON FUNCTION public.#{name}(#{args}) FROM PUBLIC"
      end) ++
      Enum.map(
        ~w(cipher attempt verified),
        &"REVOKE ALL ON TYPE public.mixer_browser_#{&1} FROM PUBLIC"
      )
  end

  # Operator-only generation of a fixed plan. No database or runtime input is
  # consulted here. Do not expose this function through an HTTP/application API.
  def provisioning_statements(writer_role, lifecycle_login) do
    writer = role!(writer_role)
    login = role!(lifecycle_login)
    if writer == login, do: raise(ArgumentError, "distinct lifecycle roles required")

    [
      "BEGIN",
      provisioning_preflight(writer, login),
      "GRANT USAGE, CREATE ON SCHEMA public TO #{writer}"
    ] ++
      Enum.map(signatures(), fn {name, args} ->
        "ALTER FUNCTION public.#{name}(#{args}) OWNER TO #{writer}"
      end) ++
      [
        "REVOKE CREATE ON SCHEMA public FROM #{writer}",
        "GRANT USAGE ON SCHEMA public TO #{login}"
      ] ++
      Enum.flat_map(~w(cipher attempt verified), fn type ->
        ["GRANT USAGE ON TYPE public.mixer_browser_#{type} TO #{writer}, #{login}"]
      end) ++
      role_policies(writer) ++
      Enum.map(public_signatures(), fn {name, args} ->
        "GRANT EXECUTE ON FUNCTION public.#{name}(#{args}) TO #{login}"
      end) ++ ["COMMIT"]
  end

  def rollback_statements do
    # Owner is recorded in the exact capability, not accepted from a session GUC.
    # Inert migration functions share the migration/table owner and need no revoke.
    # Functions returning/accepting session row types precede the session table.
    [
      """
      DO $rollback$
      DECLARE w name; t name;
      BEGIN
        SELECT r.rolname INTO w FROM pg_catalog.pg_proc p
        JOIN pg_catalog.pg_namespace n ON n.oid=p.pronamespace
        JOIN pg_catalog.pg_roles r ON r.oid=p.proowner
        WHERE n.nspname='public' AND p.proname='mixer_browser_load'
          AND pg_catalog.pg_get_function_identity_arguments(p.oid)='p_cookie bytea, p_config bytea';
        SELECT r.rolname INTO t FROM pg_catalog.pg_class c
        JOIN pg_catalog.pg_roles r ON r.oid=c.relowner
        WHERE c.oid='public.mixer_browser_sessions'::pg_catalog.regclass;
        IF w IS NOT NULL AND w <> t THEN
          EXECUTE pg_catalog.format('REVOKE SELECT ON public.mixer_authz_profiles,public.mixer_authz_principals,public.mixer_authz_bindings,public.mixer_authz_families,public.mixer_authz_credentials FROM %I', w);
          EXECUTE pg_catalog.format('REVOKE UPDATE(state_revision) ON public.mixer_authz_profiles FROM %I', w);
          EXECUTE pg_catalog.format('REVOKE UPDATE(revision) ON public.mixer_authz_principals FROM %I', w);
          EXECUTE pg_catalog.format('REVOKE INSERT,UPDATE(active,revision) ON public.mixer_authz_families FROM %I', w);
          EXECUTE pg_catalog.format('REVOKE INSERT,UPDATE(active,revision) ON public.mixer_authz_credentials FROM %I', w);
        END IF;
      END $rollback$;
      """
    ] ++
      Enum.flat_map(@authz_tables, fn table ->
        Enum.map(
          ~w(read lock insert update),
          &"DROP POLICY IF EXISTS mixer_browser_#{&1} ON public.mixer_authz_#{table}"
        )
      end) ++
      Enum.flat_map(@browser_tables, fn table ->
        [
          "DROP TRIGGER IF EXISTS mixer_browser_integrity ON public.mixer_browser_#{table}",
          "DROP TRIGGER IF EXISTS mixer_browser_immutable ON public.mixer_browser_#{table}"
        ]
      end) ++
      Enum.map(
        ~w(session_events oidc_attempts session_vault),
        &"DROP TABLE public.mixer_browser_#{&1}"
      ) ++
      Enum.map(signatures(), fn {name, args} -> "DROP FUNCTION public.#{name}(#{args})" end) ++
      ["DROP TABLE public.mixer_browser_sessions"] ++
      Enum.map(~w(verified attempt cipher), &"DROP TYPE public.mixer_browser_#{&1}")
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

  defp provisioning_preflight(writer, login) do
    """
    DO $admit$
    DECLARE w pg_catalog.pg_roles; l pg_catalog.pg_roles;
    BEGIN
      SELECT * INTO STRICT w FROM pg_catalog.pg_roles WHERE rolname='#{writer}';
      SELECT * INTO STRICT l FROM pg_catalog.pg_roles WHERE rolname='#{login}';
      IF w.rolcanlogin OR w.rolsuper OR w.rolbypassrls OR w.rolcreaterole OR w.rolcreatedb OR w.rolreplication OR w.rolinherit
        OR NOT l.rolcanlogin OR l.rolsuper OR l.rolbypassrls OR l.rolcreaterole OR l.rolcreatedb OR l.rolreplication OR l.rolinherit
        OR EXISTS (SELECT 1 FROM pg_catalog.pg_auth_members WHERE member IN(w.oid,l.oid) OR roleid IN(w.oid,l.oid))
        OR EXISTS (SELECT 1 FROM pg_catalog.pg_class WHERE relowner IN(w.oid,l.oid))
        OR EXISTS (SELECT 1 FROM pg_catalog.pg_namespace WHERE nspowner IN(w.oid,l.oid)
          OR pg_catalog.has_schema_privilege(w.oid,oid,'CREATE') OR pg_catalog.has_schema_privilege(l.oid,oid,'CREATE'))
        OR EXISTS (SELECT 1 FROM pg_catalog.pg_class c JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace
          WHERE n.nspname='public' AND c.relkind IN('r','p','v','m','f') AND
           (pg_catalog.has_table_privilege(w.oid,c.oid,'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER')
            OR pg_catalog.has_table_privilege(l.oid,c.oid,'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER')
            OR pg_catalog.has_any_column_privilege(w.oid,c.oid,'SELECT,INSERT,UPDATE,REFERENCES')
            OR pg_catalog.has_any_column_privilege(l.oid,c.oid,'SELECT,INSERT,UPDATE,REFERENCES')))
      THEN RAISE EXCEPTION 'browser lifecycle provisioning denied' USING ERRCODE='42501'; END IF;
    END $admit$;
    """
  end

  defp role_policies(writer) do
    Enum.flat_map(@browser_tables, fn table ->
      rel = "public.mixer_browser_" <> table

      if table == "session_events" do
        [
          "CREATE POLICY mixer_browser_read ON #{rel} FOR SELECT TO #{writer} USING (true)",
          "CREATE POLICY mixer_browser_insert ON #{rel} FOR INSERT TO #{writer} WITH CHECK (true)",
          "GRANT SELECT,INSERT ON #{rel} TO #{writer}"
        ]
      else
        [
          "CREATE POLICY mixer_browser_read ON #{rel} FOR SELECT TO #{writer} USING (true)",
          "CREATE POLICY mixer_browser_insert ON #{rel} FOR INSERT TO #{writer} WITH CHECK (true)",
          "CREATE POLICY mixer_browser_update ON #{rel} FOR UPDATE TO #{writer} USING (true) WITH CHECK (true)",
          "GRANT SELECT,INSERT ON #{rel} TO #{writer}",
          "GRANT UPDATE(#{mutable_columns(table)}) ON #{rel} TO #{writer}"
        ]
      end
    end) ++
      Enum.flat_map(@authz_tables, fn table ->
        rel = "public.mixer_authz_" <> table

        read = [
          "CREATE POLICY mixer_browser_read ON #{rel} FOR SELECT TO #{writer} USING (true)",
          "GRANT SELECT ON #{rel} TO #{writer}"
        ]

        case table do
          "bindings" ->
            read

          lock when lock in ["profiles", "principals"] ->
            column = if table == "profiles", do: "state_revision", else: "revision"

            read ++
              [
                "CREATE POLICY mixer_browser_lock ON #{rel} FOR UPDATE TO #{writer} USING (true) WITH CHECK (false)",
                "GRANT UPDATE(#{column}) ON #{rel} TO #{writer}"
              ]

          _ ->
            read ++
              [
                "CREATE POLICY mixer_browser_insert ON #{rel} FOR INSERT TO #{writer} WITH CHECK (true)",
                "CREATE POLICY mixer_browser_update ON #{rel} FOR UPDATE TO #{writer} USING (true) WITH CHECK (true)",
                "GRANT INSERT,UPDATE(active,revision) ON #{rel} TO #{writer}"
              ]
        end
      end)
  end

  defp mutable_columns("sessions"),
    do:
      "cookie_digest,status,epoch,revision,generation,csrf_digest,last_seen_at,absolute_expires_at,idle_expires_at,profile_id,profile_version,principal_id,family_id,credential_ref,credential_revision,audit_sequence"

  defp mutable_columns("session_vault"),
    do:
      "epoch,session_revision,vault_generation,ciphertext_version,envelope_kind,key_id,iv,tag,ciphertext"

  defp mutable_columns("oidc_attempts"),
    do:
      "status,claim_digest,claimed_at,claim_expires_at,completion_reason,key_id,iv,tag,ciphertext"

  defp types do
    [
      "CREATE TYPE public.mixer_browser_cipher AS (key_id text,iv bytea,tag bytea,ciphertext bytea)",
      "CREATE TYPE public.mixer_browser_attempt AS (state_digest bytea,nonce_digest bytea,profile_id text,profile_version integer,issuer text,client_id text,redirect_uri text,expires_at bigint,cipher public.mixer_browser_cipher)",
      "CREATE TYPE public.mixer_browser_verified AS (profile_id text,profile_version integer,issuer text,subject text,client_id text,credential_ref text,issued_at bigint,expires_at bigint,scopes text[],profile_revision bigint,binding_revision bigint,principal_revision bigint)"
    ]
  end

  defp tables do
    [
      """
      CREATE TABLE public.mixer_browser_sessions (
        id bytea PRIMARY KEY CHECK (octet_length(id)=16),
        cookie_digest bytea NOT NULL UNIQUE CHECK (octet_length(cookie_digest)=32),
        status text NOT NULL CHECK (status IN('preauth','active','revoked','expired')),
        epoch bigint NOT NULL CHECK (epoch BETWEEN 1 AND 9007199254740991),
        revision bigint NOT NULL CHECK (revision BETWEEN 1 AND 9007199254740991),
        generation text NOT NULL CHECK (generation ~ '^[A-Za-z0-9_-]{42}[AEIMQUYcgkosw048]$'),
        csrf_digest bytea NOT NULL CHECK (octet_length(csrf_digest)=32),
        created_at bigint NOT NULL CHECK (created_at BETWEEN 0 AND 9007199254740991),
        last_seen_at bigint NOT NULL CHECK (last_seen_at >= created_at),
        absolute_expires_at bigint NOT NULL CHECK (absolute_expires_at > created_at AND absolute_expires_at <=9007199254740991),
        idle_expires_at bigint NOT NULL CHECK (idle_expires_at > created_at AND idle_expires_at <=absolute_expires_at),
        expected_profile_id text NOT NULL CHECK (octet_length(expected_profile_id) BETWEEN 1 AND 128),
        expected_profile_version integer NOT NULL CHECK (expected_profile_version > 0),
        initial_config_digest bytea NOT NULL CHECK (octet_length(initial_config_digest)=32),
        config_digest bytea NOT NULL CHECK (octet_length(config_digest)=32),
        profile_id text,profile_version integer,principal_id text,family_id text,credential_ref text,credential_revision bigint,
        audit_sequence bigint NOT NULL CHECK (audit_sequence BETWEEN 1 AND 9007199254740991),
        CHECK ((profile_id IS NULL AND profile_version IS NULL AND principal_id IS NULL AND family_id IS NULL AND credential_ref IS NULL AND credential_revision IS NULL AND status<>'active') OR
          (profile_id IS NOT NULL AND profile_version IS NOT NULL AND principal_id IS NOT NULL AND family_id IS NOT NULL AND credential_ref IS NOT NULL AND credential_revision IS NOT NULL AND credential_revision BETWEEN 1 AND 9007199254740991 AND status<>'preauth')),
        FOREIGN KEY(profile_id,profile_version,credential_ref) REFERENCES public.mixer_authz_credentials(profile_id,profile_version,reference),
        FOREIGN KEY(family_id,profile_id,profile_version,principal_id) REFERENCES public.mixer_authz_families(id,profile_id,profile_version,principal_id)
      )
      """,
      """
      CREATE TABLE public.mixer_browser_session_vault (
        browser_id bytea PRIMARY KEY REFERENCES public.mixer_browser_sessions(id),
        epoch bigint NOT NULL CHECK (epoch BETWEEN 1 AND 9007199254740991),
        session_revision bigint NOT NULL CHECK (session_revision BETWEEN 1 AND 9007199254740991),
        vault_generation bigint NOT NULL CHECK (vault_generation BETWEEN 1 AND 9007199254740991),
        ciphertext_version integer NOT NULL CHECK (ciphertext_version=1),
        envelope_kind text NOT NULL CHECK (envelope_kind IN('preauth','active','erased')),
        key_id text,iv bytea,tag bytea,ciphertext bytea,
        CHECK ((envelope_kind='erased' AND key_id IS NULL AND iv IS NULL AND tag IS NULL AND ciphertext IS NULL) OR
          (envelope_kind IN('preauth','active') AND key_id IS NOT NULL AND key_id ~ '^[A-Za-z0-9._-]{1,128}$' AND iv IS NOT NULL AND octet_length(iv)=12 AND tag IS NOT NULL AND octet_length(tag)=16 AND ciphertext IS NOT NULL AND octet_length(ciphertext) BETWEEN 1 AND 8192))
      )
      """,
      """
      CREATE TABLE public.mixer_browser_oidc_attempts (
        state_digest bytea PRIMARY KEY CHECK(octet_length(state_digest)=32),
        browser_id bytea NOT NULL REFERENCES public.mixer_browser_sessions(id),
        browser_epoch bigint NOT NULL CHECK(browser_epoch BETWEEN 1 AND 9007199254740991),
        browser_revision bigint NOT NULL CHECK(browser_revision BETWEEN 1 AND 9007199254740991),
        cookie_digest bytea NOT NULL CHECK(octet_length(cookie_digest)=32),
        generation text NOT NULL CHECK(generation ~ '^[A-Za-z0-9_-]{42}[AEIMQUYcgkosw048]$'),
        config_digest bytea NOT NULL CHECK(octet_length(config_digest)=32),
        profile_id text NOT NULL CHECK(octet_length(profile_id) BETWEEN 1 AND 128),
        profile_version integer NOT NULL CHECK(profile_version > 0),
        issuer text NOT NULL CHECK(octet_length(issuer) BETWEEN 1 AND 2048),
        client_id text NOT NULL CHECK(octet_length(client_id) BETWEEN 1 AND 256),
        redirect_uri text NOT NULL CHECK(octet_length(redirect_uri) BETWEEN 1 AND 2048),
        return_route text NOT NULL CHECK(return_route='workspace'),
        nonce_digest bytea NOT NULL CHECK(octet_length(nonce_digest)=32),
        created_at bigint NOT NULL CHECK(created_at BETWEEN 0 AND 9007199254740991),
        expires_at bigint NOT NULL CHECK(expires_at > created_at AND expires_at<=created_at+300 AND expires_at<=9007199254740991),
        status text NOT NULL CHECK(status IN('pending','claimed','provider_rejected','completed','failed','superseded')),
        claim_digest bytea CHECK(octet_length(claim_digest)=32),
        claimed_at bigint, claim_expires_at bigint,
        completion_reason text CHECK(completion_reason IN('provider_rejected','exchange_failed','oidc_failed','identity_failed','session_failed','completed','superseded','expired','logout')),
        ciphertext_version integer NOT NULL DEFAULT 1 CHECK(ciphertext_version=1),
        key_id text,iv bytea,tag bytea,ciphertext bytea,
        CHECK ((status='pending' AND claim_digest IS NULL AND claimed_at IS NULL AND claim_expires_at IS NULL AND completion_reason IS NULL AND key_id IS NOT NULL AND key_id ~ '^[A-Za-z0-9._-]{1,128}$' AND iv IS NOT NULL AND octet_length(iv)=12 AND tag IS NOT NULL AND octet_length(tag)=16 AND ciphertext IS NOT NULL AND octet_length(ciphertext) BETWEEN 1 AND 8192) OR
          (status<>'pending' AND key_id IS NULL AND iv IS NULL AND tag IS NULL AND ciphertext IS NULL AND
           ((status='claimed' AND completion_reason IS NULL AND claim_digest IS NOT NULL AND claimed_at IS NOT NULL AND claim_expires_at IS NOT NULL AND claimed_at>=created_at AND claim_expires_at>claimed_at AND claim_expires_at<=expires_at) OR
            (completion_reason IS NOT NULL AND ((status='provider_rejected' AND completion_reason='provider_rejected') OR (status='completed' AND completion_reason='completed' AND claim_digest IS NOT NULL) OR (status='failed' AND completion_reason IN('exchange_failed','oidc_failed','identity_failed','session_failed') AND claim_digest IS NOT NULL) OR (status='superseded' AND completion_reason IN('superseded','expired','logout')))))))
      )
      """,
      "CREATE UNIQUE INDEX mixer_browser_one_attempt ON public.mixer_browser_oidc_attempts(browser_id,browser_epoch) WHERE status IN('pending','claimed')",
      """
      CREATE TABLE public.mixer_browser_session_events (
        browser_id bytea NOT NULL REFERENCES public.mixer_browser_sessions(id),
        sequence bigint NOT NULL CHECK(sequence BETWEEN 1 AND 9007199254740991),
        audit_schema integer NOT NULL CHECK(audit_schema=1),
        operation text NOT NULL CHECK(operation IN('bootstrap','begin','claim','provider_reject','fail_claim','activate','replace','logout','expire')),
        outcome text NOT NULL CHECK(outcome IN('created','pending','claimed','provider_rejected','failed','active','revoked','expired')),
        request_id text NOT NULL CHECK(request_id ~ '^[0-9a-f]{32}$'),
        recorded_at bigint NOT NULL CHECK(recorded_at BETWEEN 0 AND 9007199254740991),
        old_revision bigint, new_revision bigint NOT NULL CHECK(new_revision BETWEEN 1 AND 9007199254740991), old_epoch bigint,new_epoch bigint NOT NULL CHECK(new_epoch BETWEEN 1 AND 9007199254740991),
        old_status text,new_status text NOT NULL CHECK(new_status IN('preauth','active','revoked','expired')),
        config_digest bytea NOT NULL CHECK(octet_length(config_digest)=32), attempt_state_digest bytea CHECK(octet_length(attempt_state_digest)=32),
        profile_id text,profile_version integer,principal_id text,family_id text,
        issuer_hash bytea CHECK(octet_length(issuer_hash)=32),subject_hash bytea CHECK(octet_length(subject_hash)=32),
        client_hash bytea CHECK(octet_length(client_hash)=32),credential_hash bytea CHECK(octet_length(credential_hash)=32),
        profile_revision bigint,binding_revision bigint,principal_revision bigint,family_revision bigint,credential_revision bigint,
        token_issued_at bigint,token_expires_at bigint,
        PRIMARY KEY(browser_id,sequence),
        CHECK((sequence=1 AND operation='bootstrap' AND old_revision IS NULL AND old_epoch IS NULL AND old_status IS NULL AND new_revision=1 AND new_epoch=1 AND new_status='preauth' AND outcome='created') OR
          (sequence>1 AND old_revision IS NOT NULL AND old_revision BETWEEN 1 AND 9007199254740991 AND old_epoch IS NOT NULL AND old_epoch BETWEEN 1 AND 9007199254740991 AND old_status IS NOT NULL AND old_status IN('preauth','active') AND
           ((operation='begin' AND outcome='pending' AND new_status=old_status AND new_revision=old_revision+1 AND new_epoch=old_epoch+1) OR
            (operation='claim' AND outcome='claimed' AND new_status=old_status AND new_revision=old_revision AND new_epoch=old_epoch) OR
            (operation='provider_reject' AND outcome='provider_rejected' AND new_status=old_status AND new_revision=old_revision AND new_epoch=old_epoch) OR
            (operation='fail_claim' AND outcome='failed' AND new_status=old_status AND new_revision=old_revision AND new_epoch=old_epoch) OR
            (operation='activate' AND outcome='active' AND old_status='preauth' AND new_status='active' AND new_revision=old_revision+1 AND new_epoch=old_epoch+1) OR
            (operation='replace' AND outcome='active' AND old_status='active' AND new_status='active' AND new_revision=old_revision+1 AND new_epoch=old_epoch+1) OR
            (operation='logout' AND outcome='revoked' AND new_status='revoked' AND new_revision=old_revision+1 AND new_epoch=old_epoch+1) OR
            (operation='expire' AND outcome='expired' AND new_status='expired' AND new_revision=old_revision+1 AND new_epoch=old_epoch+1)))),
        CHECK((operation IN('activate','replace') AND token_issued_at IS NOT NULL AND token_expires_at>token_issued_at AND issuer_hash IS NOT NULL AND subject_hash IS NOT NULL AND client_hash IS NOT NULL AND credential_hash IS NOT NULL) OR
          (operation NOT IN('activate','replace') AND token_issued_at IS NULL AND token_expires_at IS NULL AND issuer_hash IS NULL AND subject_hash IS NULL AND client_hash IS NULL AND credential_hash IS NULL))
      )
      """
    ]
  end

  defp function(name, args, result, body) do
    """
    CREATE FUNCTION public.#{name}(#{args}) RETURNS #{result}
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path=pg_catalog SET statement_timeout='5s'
    SET lock_timeout='500ms' SET idle_in_transaction_session_timeout='5s' SET bytea_output='hex'
    AS $browser$
    #{body}
    $browser$
    """
  end

  defp functions do
    primitive_functions() ++ lifecycle_functions()
  end

  defp primitive_functions do
    [
      function("mixer_browser_cipher_valid", "c public.mixer_browser_cipher", "boolean", """
      BEGIN
        RETURN c.key_id IS NOT NULL AND c.key_id ~ '^[A-Za-z0-9._-]{1,128}$'
          AND c.iv IS NOT NULL AND octet_length(c.iv)=12 AND c.tag IS NOT NULL AND octet_length(c.tag)=16
          AND c.ciphertext IS NOT NULL AND octet_length(c.ciphertext) BETWEEN 1 AND 8192;
      END;
      """),
      function("mixer_browser_snapshot", "p_browser bytea,p_state bytea", "jsonb", """
      DECLARE b public.mixer_browser_sessions; v public.mixer_browser_session_vault; a public.mixer_browser_oidc_attempts;
      BEGIN
        SELECT * INTO STRICT b FROM public.mixer_browser_sessions WHERE id=p_browser;
        SELECT * INTO v FROM public.mixer_browser_session_vault WHERE browser_id=b.id;
        IF p_state IS NOT NULL THEN SELECT * INTO a FROM public.mixer_browser_oidc_attempts WHERE state_digest=p_state AND browser_id=b.id; END IF;
        RETURN pg_catalog.jsonb_build_object('browser',pg_catalog.to_jsonb(b),'vault',CASE WHEN v.browser_id IS NULL THEN NULL ELSE pg_catalog.to_jsonb(v) END,
          'attempt',CASE WHEN a.state_digest IS NULL THEN NULL ELSE pg_catalog.to_jsonb(a) END);
      END;
      """),
      function(
        "mixer_browser_audit",
        "o public.mixer_browser_sessions,n public.mixer_browser_sessions,p_operation text,p_outcome text,p_state bytea,p_request text,i public.mixer_browser_verified",
        "void",
        """
        BEGIN
          INSERT INTO public.mixer_browser_session_events(browser_id,sequence,audit_schema,operation,outcome,request_id,recorded_at,
            old_revision,new_revision,old_epoch,new_epoch,old_status,new_status,config_digest,attempt_state_digest,profile_id,profile_version,principal_id,family_id,
            issuer_hash,subject_hash,client_hash,credential_hash,profile_revision,binding_revision,principal_revision,family_revision,credential_revision,token_issued_at,token_expires_at)
          VALUES(n.id,n.audit_sequence,1,p_operation,p_outcome,p_request,pg_catalog.floor(extract(epoch FROM pg_catalog.clock_timestamp()))::bigint,
            o.revision,n.revision,o.epoch,n.epoch,o.status,n.status,n.config_digest,p_state,n.profile_id,n.profile_version,n.principal_id,n.family_id,
            CASE WHEN i.issuer IS NULL THEN NULL ELSE pg_catalog.sha256(pg_catalog.convert_to('mixer.browser.audit.issuer.v1','UTF8')||pg_catalog.decode('00','hex')||pg_catalog.int4send(octet_length(i.issuer))||pg_catalog.convert_to(i.issuer,'UTF8')) END,
            CASE WHEN i.subject IS NULL THEN NULL ELSE pg_catalog.sha256(pg_catalog.convert_to('mixer.browser.audit.subject.v1','UTF8')||pg_catalog.decode('00','hex')||pg_catalog.int4send(octet_length(i.subject))||pg_catalog.convert_to(i.subject,'UTF8')) END,
            CASE WHEN i.client_id IS NULL THEN NULL ELSE pg_catalog.sha256(pg_catalog.convert_to('mixer.browser.audit.client.v1','UTF8')||pg_catalog.decode('00','hex')||pg_catalog.int4send(octet_length(i.client_id))||pg_catalog.convert_to(i.client_id,'UTF8')) END,
            CASE WHEN i.credential_ref IS NULL THEN NULL ELSE pg_catalog.sha256(pg_catalog.convert_to('mixer.browser.audit.jti.v1','UTF8')||pg_catalog.decode('00','hex')||pg_catalog.int4send(octet_length(i.credential_ref))||pg_catalog.convert_to(i.credential_ref,'UTF8')) END,
            i.profile_revision,i.binding_revision,i.principal_revision,CASE WHEN i.profile_id IS NULL THEN NULL ELSE 1 END,n.credential_revision,i.issued_at,i.expires_at);
        END;
        """
      ),
      function("mixer_browser_lock_existing", "d public.mixer_browser_sessions", "void", """
      DECLARE f public.mixer_authz_families; c public.mixer_authz_credentials; count_credentials integer;
      BEGIN
        IF d.family_id IS NULL THEN RETURN; END IF;
        PERFORM 1 FROM public.mixer_authz_profiles WHERE id=d.profile_id AND version=d.profile_version FOR UPDATE;
        PERFORM 1 FROM public.mixer_authz_principals WHERE id=d.principal_id FOR UPDATE;
        SELECT * INTO STRICT f FROM public.mixer_authz_families WHERE id=d.family_id FOR UPDATE;
        PERFORM 1 FROM public.mixer_authz_credentials WHERE family_id=d.family_id ORDER BY profile_id COLLATE "C",profile_version,reference COLLATE "C" LIMIT 2 FOR UPDATE;
        SELECT count(*) INTO count_credentials FROM (SELECT 1 FROM public.mixer_authz_credentials WHERE family_id=d.family_id LIMIT 2) bounded;
        IF count_credentials<>1 OR f.profile_id<>d.profile_id OR f.profile_version<>d.profile_version OR f.principal_id<>d.principal_id THEN
          RAISE EXCEPTION 'browser session unavailable' USING ERRCODE='P0001';
        END IF;
        SELECT * INTO STRICT c FROM public.mixer_authz_credentials WHERE profile_id=d.profile_id AND profile_version=d.profile_version AND reference=d.credential_ref;
        IF c.principal_id<>d.principal_id OR c.family_id<>d.family_id THEN RAISE EXCEPTION 'browser session unavailable' USING ERRCODE='P0001'; END IF;
      END;
      """),
      function(
        "mixer_browser_revoke_existing",
        "d public.mixer_browser_sessions,p_now bigint",
        "void",
        """
        BEGIN
          IF d.family_id IS NULL THEN RETURN; END IF;
          UPDATE public.mixer_authz_families SET active=false,revision=revision+1 WHERE id=d.family_id AND active;
          UPDATE public.mixer_authz_credentials SET active=false,revision=revision+1 WHERE family_id=d.family_id AND active;
        END;
        """
      ),
      function("mixer_browser_integrity", "", "trigger", """
      DECLARE e public.mixer_browser_session_events; v public.mixer_browser_session_vault; c public.mixer_authz_credentials; b public.mixer_browser_sessions;
      BEGIN
        IF TG_TABLE_NAME='mixer_browser_session_vault' THEN
          SELECT * INTO STRICT b FROM public.mixer_browser_sessions WHERE id=NEW.browser_id;
        ELSE b:=NEW;
        END IF;
        SELECT * INTO e FROM public.mixer_browser_session_events WHERE browser_id=b.id AND sequence=b.audit_sequence;
        IF NOT FOUND OR e.new_revision<>b.revision OR e.new_epoch<>b.epoch OR e.new_status<>b.status OR e.config_digest<>b.config_digest THEN
          RAISE EXCEPTION 'browser audit transition missing' USING ERRCODE='23514'; END IF;
        IF TG_TABLE_NAME='mixer_browser_session_vault' THEN
          IF TG_OP='INSERT' THEN
            IF e.operation<>'bootstrap' OR NEW.vault_generation<>1 OR NEW.epoch<>1 OR NEW.session_revision<>1 THEN RAISE EXCEPTION 'browser vault initial transition invalid' USING ERRCODE='23514'; END IF;
          ELSE
            IF e.operation NOT IN('begin','activate','replace','logout','expire') OR NEW.browser_id<>OLD.browser_id OR NEW.vault_generation<>OLD.vault_generation+1
              OR NEW.epoch<>OLD.epoch+1 OR NEW.session_revision<>OLD.session_revision+1
            THEN RAISE EXCEPTION 'browser vault transition invalid' USING ERRCODE='23514'; END IF;
          END IF;
        END IF;
        IF TG_TABLE_NAME='mixer_browser_sessions' THEN
          IF TG_OP='INSERT' THEN
            IF b.audit_sequence<>1 OR e.operation<>'bootstrap' OR e.old_revision IS NOT NULL THEN RAISE EXCEPTION 'browser initial transition invalid' USING ERRCODE='23514'; END IF;
          ELSE
            IF b.audit_sequence<>OLD.audit_sequence+1 OR e.old_revision<>OLD.revision OR e.old_epoch<>OLD.epoch OR e.old_status<>OLD.status OR b.id<>OLD.id
              OR b.created_at<>OLD.created_at OR b.initial_config_digest<>OLD.initial_config_digest OR b.config_digest<>OLD.config_digest OR OLD.status IN('revoked','expired')
              OR (b.revision=OLD.revision AND (pg_catalog.to_jsonb(b)-'audit_sequence') IS DISTINCT FROM (pg_catalog.to_jsonb(OLD)-'audit_sequence'))
              OR b.revision NOT IN(OLD.revision,OLD.revision+1) OR b.epoch NOT IN(OLD.epoch,OLD.epoch+1)
            THEN RAISE EXCEPTION 'browser transition invalid' USING ERRCODE='23514'; END IF;
          END IF;
        END IF;
        SELECT * INTO v FROM public.mixer_browser_session_vault WHERE browser_id=b.id;
        IF b.status IN('preauth','active') THEN
          IF NOT FOUND OR v.epoch<>b.epoch OR v.session_revision<>b.revision OR v.envelope_kind<>b.status THEN RAISE EXCEPTION 'browser vault linkage invalid' USING ERRCODE='23514'; END IF;
        ELSIF FOUND AND (v.ciphertext IS NOT NULL) THEN RAISE EXCEPTION 'terminal browser vault retained' USING ERRCODE='23514'; END IF;
        IF b.status='active' THEN
          SELECT * INTO STRICT c FROM public.mixer_authz_credentials WHERE profile_id=b.profile_id AND profile_version=b.profile_version AND reference=b.credential_ref;
          IF c.principal_id<>b.principal_id OR c.family_id<>b.family_id OR c.revision<>b.credential_revision THEN RAISE EXCEPTION 'browser credential linkage invalid' USING ERRCODE='23514'; END IF;
        END IF;
        RETURN NULL;
      END;
      """),
      function("mixer_browser_attempt_integrity", "", "trigger", """
      DECLARE b public.mixer_browser_sessions; e public.mixer_browser_session_events;
      BEGIN
        SELECT * INTO STRICT b FROM public.mixer_browser_sessions WHERE id=NEW.browser_id;
        SELECT * INTO STRICT e FROM public.mixer_browser_session_events WHERE browser_id=b.id AND sequence=b.audit_sequence;
        IF TG_OP='UPDATE' AND (OLD.status NOT IN('pending','claimed') OR NEW.state_digest<>OLD.state_digest OR NEW.browser_id<>OLD.browser_id OR NEW.browser_epoch<>OLD.browser_epoch
          OR NEW.browser_revision<>OLD.browser_revision OR NEW.config_digest<>OLD.config_digest OR NEW.profile_id<>OLD.profile_id OR NEW.profile_version<>OLD.profile_version
          OR NEW.issuer<>OLD.issuer OR NEW.client_id<>OLD.client_id OR NEW.redirect_uri<>OLD.redirect_uri OR NEW.nonce_digest<>OLD.nonce_digest OR NEW.expires_at<>OLD.expires_at
          OR NEW.cookie_digest<>OLD.cookie_digest OR NEW.generation<>OLD.generation OR NEW.created_at<>OLD.created_at
          OR (OLD.status='claimed' AND (NEW.status NOT IN('completed','failed','superseded') OR NEW.claim_digest IS DISTINCT FROM OLD.claim_digest OR NEW.claimed_at IS DISTINCT FROM OLD.claimed_at OR NEW.claim_expires_at IS DISTINCT FROM OLD.claim_expires_at))
          OR (OLD.status='pending' AND NEW.status NOT IN('claimed','provider_rejected','superseded')))
        THEN RAISE EXCEPTION 'browser attempt transition invalid' USING ERRCODE='23514'; END IF;
        IF TG_OP='INSERT' THEN
          IF e.operation<>'begin' OR e.attempt_state_digest IS DISTINCT FROM NEW.state_digest OR NEW.status<>'pending'
            OR NEW.browser_epoch<>b.epoch OR NEW.browser_revision<>b.revision OR NEW.cookie_digest<>b.cookie_digest OR NEW.generation<>b.generation OR NEW.config_digest<>b.config_digest
          THEN RAISE EXCEPTION 'browser attempt event missing' USING ERRCODE='23514'; END IF;
        ELSE
          IF (NEW.status='claimed' AND (e.operation<>'claim' OR e.attempt_state_digest IS DISTINCT FROM NEW.state_digest))
            OR (NEW.status='provider_rejected' AND (e.operation<>'provider_reject' OR e.attempt_state_digest IS DISTINCT FROM NEW.state_digest))
            OR (NEW.status='completed' AND (e.operation NOT IN('activate','replace') OR e.attempt_state_digest IS DISTINCT FROM NEW.state_digest))
            OR (NEW.status='failed' AND (e.operation<>'fail_claim' OR e.attempt_state_digest IS DISTINCT FROM NEW.state_digest))
            OR (NEW.status='superseded' AND (e.operation NOT IN('begin','logout','expire') OR (e.operation='begin' AND e.attempt_state_digest IS NOT DISTINCT FROM NEW.state_digest)))
          THEN RAISE EXCEPTION 'browser attempt event missing' USING ERRCODE='23514'; END IF;
        END IF;
        RETURN NULL;
      END;
      """),
      function("mixer_browser_event_immutable", "", "trigger", """
      BEGIN RAISE EXCEPTION 'browser audit is immutable' USING ERRCODE='42501'; END;
      """),
      function("mixer_browser_event_integrity", "", "trigger", """
      DECLARE b public.mixer_browser_sessions; p public.mixer_browser_session_events;
      BEGIN
        SELECT * INTO STRICT b FROM public.mixer_browser_sessions WHERE id=NEW.browser_id;
        IF NEW.sequence>b.audit_sequence OR (NEW.sequence=b.audit_sequence AND (NEW.new_revision<>b.revision OR NEW.new_epoch<>b.epoch OR NEW.new_status<>b.status OR NEW.config_digest<>b.config_digest)) THEN
          RAISE EXCEPTION 'orphan browser event' USING ERRCODE='23514'; END IF;
        IF NEW.sequence>1 THEN
          SELECT * INTO STRICT p FROM public.mixer_browser_session_events WHERE browser_id=NEW.browser_id AND sequence=NEW.sequence-1;
          IF NEW.old_revision<>p.new_revision OR NEW.old_epoch<>p.new_epoch OR NEW.old_status<>p.new_status THEN RAISE EXCEPTION 'browser audit chain invalid' USING ERRCODE='23514'; END IF;
        END IF;
        RETURN NULL;
      END;
      """)
    ]
  end

  defp triggers do
    [
      "CREATE CONSTRAINT TRIGGER mixer_browser_integrity AFTER INSERT OR UPDATE ON public.mixer_browser_sessions DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION public.mixer_browser_integrity()",
      "CREATE CONSTRAINT TRIGGER mixer_browser_integrity AFTER INSERT OR UPDATE ON public.mixer_browser_session_vault DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION public.mixer_browser_integrity()",
      "CREATE CONSTRAINT TRIGGER mixer_browser_integrity AFTER INSERT OR UPDATE ON public.mixer_browser_oidc_attempts DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION public.mixer_browser_attempt_integrity()",
      "CREATE CONSTRAINT TRIGGER mixer_browser_integrity AFTER INSERT ON public.mixer_browser_session_events DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION public.mixer_browser_event_integrity()",
      "CREATE TRIGGER mixer_browser_immutable BEFORE UPDATE OR DELETE ON public.mixer_browser_session_events FOR EACH ROW EXECUTE FUNCTION public.mixer_browser_event_immutable()"
    ]
  end

  defp lifecycle_functions do
    bootstrap_and_load() ++ attempts() ++ activation() ++ termination()
  end

  defp bootstrap_and_load do
    [
      function(
        "mixer_browser_bootstrap",
        "p_id bytea,p_cookie bytea,p_generation text,p_csrf bytea,p_config bytea,p_profile text,p_version integer,p_deadline bigint,p_cipher public.mixer_browser_cipher,p_request text",
        "jsonb",
        """
        DECLARE b public.mixer_browser_sessions; n bigint;
        BEGIN
          n:=pg_catalog.floor(extract(epoch FROM pg_catalog.clock_timestamp()))::bigint;
          IF p_deadline IS NULL OR p_deadline<=n OR p_deadline>n+300 OR NOT public.mixer_browser_cipher_valid(p_cipher) THEN
            RAISE EXCEPTION 'browser session unavailable' USING ERRCODE='P0001'; END IF;
          INSERT INTO public.mixer_browser_sessions(id,cookie_digest,status,epoch,revision,generation,csrf_digest,created_at,last_seen_at,absolute_expires_at,idle_expires_at,
            expected_profile_id,expected_profile_version,initial_config_digest,config_digest,audit_sequence)
          VALUES(p_id,p_cookie,'preauth',1,1,p_generation,p_csrf,n,n,p_deadline,p_deadline,p_profile,p_version,p_config,p_config,1) RETURNING * INTO b;
          INSERT INTO public.mixer_browser_session_vault(browser_id,epoch,session_revision,vault_generation,ciphertext_version,envelope_kind,key_id,iv,tag,ciphertext)
          VALUES(b.id,b.epoch,b.revision,1,1,'preauth',p_cipher.key_id,p_cipher.iv,p_cipher.tag,p_cipher.ciphertext);
          PERFORM public.mixer_browser_audit(NULL::public.mixer_browser_sessions,b,'bootstrap','created',NULL,p_request,NULL::public.mixer_browser_verified);
          RETURN public.mixer_browser_snapshot(b.id,NULL);
        END;
        """
      ),
      function("mixer_browser_load", "p_cookie bytea,p_config bytea", "jsonb", """
      DECLARE b public.mixer_browser_sessions; s bytea; n bigint;
      BEGIN
        SELECT * INTO b FROM public.mixer_browser_sessions WHERE cookie_digest=p_cookie FOR SHARE;
        n:=pg_catalog.floor(extract(epoch FROM pg_catalog.clock_timestamp()))::bigint;
        IF NOT FOUND OR b.status NOT IN('preauth','active') OR b.config_digest IS DISTINCT FROM p_config OR n>=b.absolute_expires_at OR n>=b.idle_expires_at THEN
          RETURN NULL; END IF;
        SELECT state_digest INTO s FROM public.mixer_browser_oidc_attempts WHERE browser_id=b.id AND browser_epoch=b.epoch AND status='pending' LIMIT 1;
        RETURN public.mixer_browser_snapshot(b.id,s);
      END;
      """)
    ]
  end

  defp attempts do
    [
      function(
        "mixer_browser_begin",
        "p_cookie bytea,p_csrf bytea,p_config bytea,p_revision bigint,a public.mixer_browser_attempt,p_cipher public.mixer_browser_cipher,p_request text",
        "jsonb",
        """
        DECLARE o public.mixer_browser_sessions; b public.mixer_browser_sessions; v public.mixer_browser_session_vault; n bigint;
        BEGIN
          SELECT * INTO o FROM public.mixer_browser_sessions WHERE cookie_digest=p_cookie FOR UPDATE;
          IF NOT FOUND THEN RAISE EXCEPTION 'browser session unavailable' USING ERRCODE='P0001'; END IF;
          PERFORM 1 FROM public.mixer_browser_oidc_attempts WHERE browser_id=o.id AND status IN('pending','claimed') ORDER BY state_digest FOR UPDATE;
          SELECT * INTO STRICT v FROM public.mixer_browser_session_vault WHERE browser_id=o.id FOR UPDATE;
          n:=pg_catalog.floor(extract(epoch FROM pg_catalog.clock_timestamp()))::bigint;
          IF o.status NOT IN('preauth','active') OR o.csrf_digest IS DISTINCT FROM p_csrf OR o.config_digest IS DISTINCT FROM p_config OR o.revision IS DISTINCT FROM p_revision
            OR n>=o.absolute_expires_at OR n>=o.idle_expires_at OR a.profile_id IS DISTINCT FROM o.expected_profile_id OR a.profile_version IS DISTINCT FROM o.expected_profile_version
            OR a.expires_at IS NULL OR a.expires_at<=n OR a.expires_at>LEAST(n+300,o.absolute_expires_at,o.idle_expires_at)
            OR NOT public.mixer_browser_cipher_valid(a.cipher) OR NOT public.mixer_browser_cipher_valid(p_cipher)
          THEN RAISE EXCEPTION 'browser session unavailable' USING ERRCODE='P0001'; END IF;
          UPDATE public.mixer_browser_oidc_attempts SET status='superseded',completion_reason='superseded',key_id=NULL,iv=NULL,tag=NULL,ciphertext=NULL
            WHERE browser_id=o.id AND status IN('pending','claimed');
          UPDATE public.mixer_browser_sessions SET epoch=epoch+1,revision=revision+1,audit_sequence=audit_sequence+1 WHERE id=o.id RETURNING * INTO b;
          UPDATE public.mixer_browser_session_vault SET epoch=b.epoch,session_revision=b.revision,vault_generation=vault_generation+1,
            key_id=p_cipher.key_id,iv=p_cipher.iv,tag=p_cipher.tag,ciphertext=p_cipher.ciphertext WHERE browser_id=b.id;
          INSERT INTO public.mixer_browser_oidc_attempts(state_digest,browser_id,browser_epoch,browser_revision,cookie_digest,generation,config_digest,profile_id,profile_version,
            issuer,client_id,redirect_uri,return_route,nonce_digest,created_at,expires_at,status,key_id,iv,tag,ciphertext)
          VALUES(a.state_digest,b.id,b.epoch,b.revision,b.cookie_digest,b.generation,b.config_digest,a.profile_id,a.profile_version,a.issuer,a.client_id,a.redirect_uri,'workspace',a.nonce_digest,n,a.expires_at,'pending',(a.cipher).key_id,(a.cipher).iv,(a.cipher).tag,(a.cipher).ciphertext);
          PERFORM public.mixer_browser_audit(o,b,'begin','pending',a.state_digest,p_request,NULL::public.mixer_browser_verified);
          RETURN public.mixer_browser_snapshot(b.id,a.state_digest);
        END;
        """
      ),
      function(
        "mixer_browser_claim",
        "p_cookie bytea,p_state bytea,p_config bytea,p_revision bigint,p_claim bytea,p_deadline bigint,p_request text",
        "jsonb",
        """
        DECLARE o public.mixer_browser_sessions; b public.mixer_browser_sessions; a public.mixer_browser_oidc_attempts; n bigint; changed integer;
        BEGIN
          SELECT * INTO o FROM public.mixer_browser_sessions WHERE cookie_digest=p_cookie FOR UPDATE;
          IF NOT FOUND THEN RAISE EXCEPTION 'browser session unavailable' USING ERRCODE='P0001'; END IF;
          SELECT * INTO a FROM public.mixer_browser_oidc_attempts WHERE browser_id=o.id AND state_digest=p_state FOR UPDATE;
          n:=pg_catalog.floor(extract(epoch FROM pg_catalog.clock_timestamp()))::bigint;
          IF NOT FOUND OR o.status NOT IN('preauth','active') OR o.config_digest IS DISTINCT FROM p_config OR o.revision IS DISTINCT FROM p_revision
            OR a.status<>'pending' OR a.browser_epoch<>o.epoch OR a.browser_revision<>o.revision OR a.config_digest<>o.config_digest
            OR a.cookie_digest<>o.cookie_digest OR a.generation<>o.generation OR n>=a.expires_at OR n>=o.absolute_expires_at OR n>=o.idle_expires_at
            OR p_claim IS NULL OR octet_length(p_claim)<>32 OR p_deadline IS NULL OR p_deadline<=n OR p_deadline>LEAST(a.expires_at,n+60)
          THEN RAISE EXCEPTION 'browser session unavailable' USING ERRCODE='P0001'; END IF;
          UPDATE public.mixer_browser_oidc_attempts SET status='claimed',claim_digest=p_claim,claimed_at=n,claim_expires_at=p_deadline,key_id=NULL,iv=NULL,tag=NULL,ciphertext=NULL
            WHERE state_digest=p_state AND status='pending' AND browser_epoch=o.epoch;
          GET DIAGNOSTICS changed=ROW_COUNT;
          IF changed<>1 THEN RAISE EXCEPTION 'browser session unavailable' USING ERRCODE='P0001'; END IF;
          UPDATE public.mixer_browser_sessions SET audit_sequence=audit_sequence+1 WHERE id=o.id RETURNING * INTO b;
          PERFORM public.mixer_browser_audit(o,b,'claim','claimed',p_state,p_request,NULL::public.mixer_browser_verified);
          RETURN public.mixer_browser_snapshot(b.id,p_state);
        END;
        """
      ),
      function(
        "mixer_browser_provider_reject",
        "p_cookie bytea,p_state bytea,p_config bytea,p_revision bigint,p_request text",
        "jsonb",
        """
        DECLARE o public.mixer_browser_sessions; b public.mixer_browser_sessions; a public.mixer_browser_oidc_attempts; n bigint; changed integer;
        BEGIN
          SELECT * INTO o FROM public.mixer_browser_sessions WHERE cookie_digest=p_cookie FOR UPDATE;
          IF NOT FOUND THEN RAISE EXCEPTION 'browser session unavailable' USING ERRCODE='P0001'; END IF;
          SELECT * INTO a FROM public.mixer_browser_oidc_attempts WHERE browser_id=o.id AND state_digest=p_state FOR UPDATE;
          n:=pg_catalog.floor(extract(epoch FROM pg_catalog.clock_timestamp()))::bigint;
          IF NOT FOUND OR o.status NOT IN('preauth','active') OR o.config_digest IS DISTINCT FROM p_config OR o.revision IS DISTINCT FROM p_revision
            OR a.status<>'pending' OR a.browser_epoch<>o.epoch OR a.browser_revision<>o.revision OR a.config_digest<>o.config_digest
            OR a.cookie_digest<>o.cookie_digest OR a.generation<>o.generation OR n>=a.expires_at OR n>=o.absolute_expires_at OR n>=o.idle_expires_at
          THEN RAISE EXCEPTION 'browser session unavailable' USING ERRCODE='P0001'; END IF;
          UPDATE public.mixer_browser_oidc_attempts SET status='provider_rejected',completion_reason='provider_rejected',key_id=NULL,iv=NULL,tag=NULL,ciphertext=NULL
            WHERE state_digest=p_state AND status='pending' AND browser_epoch=o.epoch;
          GET DIAGNOSTICS changed=ROW_COUNT;
          IF changed<>1 THEN RAISE EXCEPTION 'browser session unavailable' USING ERRCODE='P0001'; END IF;
          UPDATE public.mixer_browser_sessions SET audit_sequence=audit_sequence+1 WHERE id=o.id RETURNING * INTO b;
          PERFORM public.mixer_browser_audit(o,b,'provider_reject','provider_rejected',p_state,p_request,NULL::public.mixer_browser_verified);
          RETURN public.mixer_browser_snapshot(b.id,p_state);
        END;
        """
      ),
      function(
        "mixer_browser_fail_claim",
        "p_cookie bytea,p_state bytea,p_config bytea,p_claim bytea,p_reason text,p_request text",
        "boolean",
        """
        DECLARE o public.mixer_browser_sessions; b public.mixer_browser_sessions; a public.mixer_browser_oidc_attempts; n bigint;
        BEGIN
          SELECT * INTO o FROM public.mixer_browser_sessions WHERE cookie_digest=p_cookie FOR UPDATE;
          IF NOT FOUND THEN RAISE EXCEPTION 'browser session unavailable' USING ERRCODE='P0001'; END IF;
          SELECT * INTO a FROM public.mixer_browser_oidc_attempts WHERE browser_id=o.id AND state_digest=p_state FOR UPDATE;
          n:=pg_catalog.floor(extract(epoch FROM pg_catalog.clock_timestamp()))::bigint;
          IF NOT FOUND OR o.status NOT IN('preauth','active') OR o.config_digest IS DISTINCT FROM p_config OR a.config_digest<>o.config_digest
            OR a.status<>'claimed' OR a.browser_epoch<>o.epoch OR a.browser_revision<>o.revision OR a.claim_digest IS DISTINCT FROM p_claim
            OR p_reason IS NULL OR p_reason NOT IN('exchange_failed','oidc_failed','identity_failed','session_failed') OR n>=a.expires_at OR n>=a.claim_expires_at OR n>=o.absolute_expires_at OR n>=o.idle_expires_at
          THEN RAISE EXCEPTION 'browser session unavailable' USING ERRCODE='P0001'; END IF;
          UPDATE public.mixer_browser_oidc_attempts SET status='failed',completion_reason=p_reason,key_id=NULL,iv=NULL,tag=NULL,ciphertext=NULL WHERE state_digest=p_state;
          UPDATE public.mixer_browser_sessions SET audit_sequence=audit_sequence+1 WHERE id=o.id RETURNING * INTO b;
          PERFORM public.mixer_browser_audit(o,b,'fail_claim','failed',p_state,p_request,NULL::public.mixer_browser_verified);
          RETURN true;
        END;
        """
      )
    ]
  end

  defp activation do
    [
      function(
        "mixer_browser_activate",
        "p_cookie bytea,p_state bytea,p_config bytea,p_claim bytea,p_revision bigint,i public.mixer_browser_verified,p_new_cookie bytea,p_new_csrf bytea,p_generation text,p_family text,p_deadline bigint,p_cipher public.mixer_browser_cipher,p_request text",
        "jsonb",
        """
        DECLARE d public.mixer_browser_sessions; o public.mixer_browser_sessions; b public.mixer_browser_sessions;
          a public.mixer_browser_oidc_attempts; v public.mixer_browser_session_vault; p public.mixer_authz_profiles;
          binding public.mixer_authz_bindings; principal public.mixer_authz_principals; old_family public.mixer_authz_families; n bigint; cnt integer;
        BEGIN
          SELECT * INTO d FROM public.mixer_browser_sessions WHERE cookie_digest=p_cookie;
          IF NOT FOUND OR i.profile_id IS NULL OR i.profile_version IS NULL OR i.subject IS NULL THEN
            RAISE EXCEPTION 'browser session unavailable' USING ERRCODE='P0001'; END IF;
          PERFORM 1 FROM public.mixer_authz_profiles WHERE (id,version) IN((i.profile_id,i.profile_version),(d.profile_id,d.profile_version))
            ORDER BY id COLLATE "C",version FOR UPDATE;
          SELECT * INTO p FROM public.mixer_authz_profiles WHERE id=i.profile_id AND version=i.profile_version;
          IF NOT FOUND THEN RAISE EXCEPTION 'browser identity unavailable' USING ERRCODE='P0001'; END IF;
          SELECT * INTO binding FROM public.mixer_authz_bindings WHERE profile_id=i.profile_id AND profile_version=i.profile_version AND subject=i.subject;
          IF NOT FOUND THEN RAISE EXCEPTION 'browser onboarding required' USING ERRCODE='P0001'; END IF;
          PERFORM 1 FROM public.mixer_authz_principals WHERE id IN(binding.principal_id,d.principal_id) ORDER BY id COLLATE "C" FOR UPDATE;
          SELECT * INTO STRICT principal FROM public.mixer_authz_principals WHERE id=binding.principal_id;
          IF d.family_id IS NOT NULL THEN
            SELECT * INTO STRICT old_family FROM public.mixer_authz_families WHERE id=d.family_id FOR UPDATE;
            PERFORM 1 FROM public.mixer_authz_credentials WHERE family_id=d.family_id ORDER BY profile_id COLLATE "C",profile_version,reference COLLATE "C" LIMIT 2 FOR UPDATE;
            SELECT count(*) INTO cnt FROM (SELECT 1 FROM public.mixer_authz_credentials WHERE family_id=d.family_id LIMIT 2) bounded;
            IF cnt<>1 OR old_family.profile_id<>d.profile_id OR old_family.profile_version<>d.profile_version OR old_family.principal_id<>d.principal_id
              OR NOT EXISTS(SELECT 1 FROM public.mixer_authz_credentials WHERE profile_id=d.profile_id AND profile_version=d.profile_version AND reference=d.credential_ref AND principal_id=d.principal_id AND family_id=d.family_id AND revision=d.credential_revision)
            THEN RAISE EXCEPTION 'browser session unavailable' USING ERRCODE='P0001'; END IF;
          END IF;
          SELECT * INTO STRICT o FROM public.mixer_browser_sessions WHERE id=d.id FOR UPDATE;
          SELECT * INTO a FROM public.mixer_browser_oidc_attempts WHERE browser_id=o.id AND state_digest=p_state FOR UPDATE;
          IF NOT FOUND THEN RAISE EXCEPTION 'browser session unavailable' USING ERRCODE='P0001'; END IF;
          SELECT * INTO STRICT v FROM public.mixer_browser_session_vault WHERE browser_id=o.id FOR UPDATE;
          n:=pg_catalog.floor(extract(epoch FROM pg_catalog.clock_timestamp()))::bigint;
          IF o IS DISTINCT FROM d OR o.status NOT IN('preauth','active') OR o.revision IS DISTINCT FROM p_revision OR o.config_digest IS DISTINCT FROM p_config
            OR a.status<>'claimed' OR a.browser_epoch<>o.epoch OR a.browser_revision<>o.revision OR a.config_digest<>o.config_digest OR a.cookie_digest<>o.cookie_digest OR a.generation<>o.generation
            OR a.claim_digest IS DISTINCT FROM p_claim OR n>=a.expires_at OR n>=a.claim_expires_at OR n>=o.absolute_expires_at OR n>=o.idle_expires_at
            OR i.profile_id IS DISTINCT FROM a.profile_id OR i.profile_version IS DISTINCT FROM a.profile_version OR i.issuer IS DISTINCT FROM a.issuer OR i.client_id IS DISTINCT FROM a.client_id
            OR p.id IS DISTINCT FROM o.expected_profile_id OR p.version IS DISTINCT FROM o.expected_profile_version
            OR NOT p.active OR p.identity_class<>'human' OR p.issuer IS DISTINCT FROM i.issuer OR p.client_id IS DISTINCT FROM i.client_id OR p.state_revision IS DISTINCT FROM i.profile_revision
            OR NOT binding.active OR binding.identity_class<>'human' OR binding.revision IS DISTINCT FROM i.binding_revision
            OR NOT principal.active OR principal.identity_class<>'human' OR principal.revision IS DISTINCT FROM i.principal_revision OR principal.not_before>n
            OR i.issued_at IS NULL OR i.issued_at<principal.not_before OR i.issued_at>n+30 OR i.issued_at<0 OR i.expires_at IS NULL OR i.expires_at<=GREATEST(n,i.issued_at) OR i.expires_at>9007199254740991
            OR i.scopes IS NULL OR NOT ('mixer.workspace.read'=ANY(i.scopes)) OR cardinality(i.scopes)>64
            OR i.credential_ref IS NULL OR octet_length(i.credential_ref) NOT BETWEEN 1 AND 256
            OR p_deadline IS NULL OR p_deadline<=n OR p_deadline>LEAST(i.expires_at,n+900)
            OR p_family IS NULL OR p_family !~ '^browser_[A-Za-z0-9_-]{42}[AEIMQUYcgkosw048]$'
            OR p_new_cookie IS NULL OR octet_length(p_new_cookie)<>32 OR p_new_cookie=o.cookie_digest
            OR p_new_csrf IS NULL OR octet_length(p_new_csrf)<>32 OR p_new_csrf=o.csrf_digest
            OR p_generation IS NULL OR p_generation=o.generation OR NOT public.mixer_browser_cipher_valid(p_cipher)
            OR (d.family_id IS NOT NULL AND (NOT old_family.active OR old_family.not_before>n OR (old_family.expires_at IS NOT NULL AND old_family.expires_at<=n)))
          THEN RAISE EXCEPTION 'browser session unavailable' USING ERRCODE='P0001'; END IF;
          -- Unique INSERTs preserve every credential and family tombstone forever.
          INSERT INTO public.mixer_authz_families(id,profile_id,profile_version,principal_id,active,not_before,expires_at,revision)
            VALUES(p_family,i.profile_id,i.profile_version,principal.id,true,LEAST(i.issued_at,n),i.expires_at,1);
          INSERT INTO public.mixer_authz_credentials(profile_id,profile_version,reference,principal_id,family_id,active,not_before,expires_at,revision)
            VALUES(i.profile_id,i.profile_version,i.credential_ref,principal.id,p_family,true,LEAST(i.issued_at,n),i.expires_at,1);
          -- A uniqueness insertion can wait; repeat all temporal decisions afterwards.
          n:=pg_catalog.floor(extract(epoch FROM pg_catalog.clock_timestamp()))::bigint;
          IF n>=a.expires_at OR n>=a.claim_expires_at OR n>=o.absolute_expires_at OR n>=o.idle_expires_at OR n>=i.expires_at OR n>=p_deadline THEN
            RAISE EXCEPTION 'browser session unavailable' USING ERRCODE='P0001'; END IF;
          PERFORM public.mixer_browser_revoke_existing(o,n);
          UPDATE public.mixer_browser_sessions SET cookie_digest=p_new_cookie,csrf_digest=p_new_csrf,generation=p_generation,status='active',epoch=epoch+1,revision=revision+1,
            last_seen_at=n,absolute_expires_at=p_deadline,idle_expires_at=p_deadline,profile_id=i.profile_id,profile_version=i.profile_version,principal_id=principal.id,
            family_id=p_family,credential_ref=i.credential_ref,credential_revision=1,audit_sequence=audit_sequence+1 WHERE id=o.id RETURNING * INTO b;
          UPDATE public.mixer_browser_session_vault SET epoch=b.epoch,session_revision=b.revision,vault_generation=vault_generation+1,envelope_kind='active',
            key_id=p_cipher.key_id,iv=p_cipher.iv,tag=p_cipher.tag,ciphertext=p_cipher.ciphertext WHERE browser_id=b.id;
          UPDATE public.mixer_browser_oidc_attempts SET status='completed',completion_reason='completed',key_id=NULL,iv=NULL,tag=NULL,ciphertext=NULL WHERE state_digest=p_state;
          PERFORM public.mixer_browser_audit(o,b,CASE WHEN o.family_id IS NULL THEN 'activate' ELSE 'replace' END,'active',p_state,p_request,i);
          RETURN public.mixer_browser_snapshot(b.id,p_state);
        END;
        """
      )
    ]
  end

  defp termination do
    [
      function(
        "mixer_browser_logout",
        "p_cookie bytea,p_csrf bytea,p_config bytea,p_revision bigint,p_request text",
        "boolean",
        """
        DECLARE d public.mixer_browser_sessions; o public.mixer_browser_sessions; b public.mixer_browser_sessions; n bigint;
        BEGIN
          SELECT * INTO d FROM public.mixer_browser_sessions WHERE cookie_digest=p_cookie;
          IF NOT FOUND THEN RAISE EXCEPTION 'browser session unavailable' USING ERRCODE='P0001'; END IF;
          IF d.status='revoked' AND d.csrf_digest IS NOT DISTINCT FROM p_csrf AND d.config_digest IS NOT DISTINCT FROM p_config THEN RETURN true; END IF;
          PERFORM public.mixer_browser_lock_existing(d);
          SELECT * INTO STRICT o FROM public.mixer_browser_sessions WHERE id=d.id FOR UPDATE;
          PERFORM 1 FROM public.mixer_browser_oidc_attempts WHERE browser_id=o.id AND status IN('pending','claimed') ORDER BY state_digest FOR UPDATE;
          PERFORM 1 FROM public.mixer_browser_session_vault WHERE browser_id=o.id FOR UPDATE;
          n:=pg_catalog.floor(extract(epoch FROM pg_catalog.clock_timestamp()))::bigint;
          IF o IS DISTINCT FROM d OR o.status NOT IN('preauth','active') OR o.revision IS DISTINCT FROM p_revision OR o.csrf_digest IS DISTINCT FROM p_csrf OR o.config_digest IS DISTINCT FROM p_config THEN
            RAISE EXCEPTION 'browser session unavailable' USING ERRCODE='P0001'; END IF;
          PERFORM public.mixer_browser_revoke_existing(o,n);
          UPDATE public.mixer_browser_sessions SET status='revoked',epoch=epoch+1,revision=revision+1,audit_sequence=audit_sequence+1 WHERE id=o.id RETURNING * INTO b;
          UPDATE public.mixer_browser_oidc_attempts SET status='superseded',completion_reason='logout',key_id=NULL,iv=NULL,tag=NULL,ciphertext=NULL WHERE browser_id=o.id AND status IN('pending','claimed');
          UPDATE public.mixer_browser_session_vault SET epoch=b.epoch,session_revision=b.revision,vault_generation=vault_generation+1,envelope_kind='erased',key_id=NULL,iv=NULL,tag=NULL,ciphertext=NULL WHERE browser_id=o.id;
          PERFORM public.mixer_browser_audit(o,b,'logout','revoked',NULL,p_request,NULL::public.mixer_browser_verified);
          RETURN true;
        END;
        """
      ),
      function(
        "mixer_browser_expire",
        "p_browser bytea,p_revision bigint,p_request text",
        "boolean",
        """
        DECLARE d public.mixer_browser_sessions; o public.mixer_browser_sessions; b public.mixer_browser_sessions; n bigint;
        BEGIN
          SELECT * INTO d FROM public.mixer_browser_sessions WHERE id=p_browser;
          IF NOT FOUND THEN RETURN false; END IF;
          IF d.status IN('revoked','expired') THEN RETURN false; END IF;
          PERFORM public.mixer_browser_lock_existing(d);
          SELECT * INTO STRICT o FROM public.mixer_browser_sessions WHERE id=d.id FOR UPDATE;
          PERFORM 1 FROM public.mixer_browser_oidc_attempts WHERE browser_id=o.id AND status IN('pending','claimed') ORDER BY state_digest FOR UPDATE;
          PERFORM 1 FROM public.mixer_browser_session_vault WHERE browser_id=o.id FOR UPDATE;
          n:=pg_catalog.floor(extract(epoch FROM pg_catalog.clock_timestamp()))::bigint;
          IF o IS DISTINCT FROM d OR o.revision IS DISTINCT FROM p_revision OR o.status NOT IN('preauth','active') THEN RAISE EXCEPTION 'browser session unavailable' USING ERRCODE='P0001'; END IF;
          IF n<o.absolute_expires_at AND n<o.idle_expires_at THEN RETURN false; END IF;
          PERFORM public.mixer_browser_revoke_existing(o,n);
          UPDATE public.mixer_browser_sessions SET status='expired',epoch=epoch+1,revision=revision+1,audit_sequence=audit_sequence+1 WHERE id=o.id RETURNING * INTO b;
          UPDATE public.mixer_browser_oidc_attempts SET status='superseded',completion_reason='expired',key_id=NULL,iv=NULL,tag=NULL,ciphertext=NULL WHERE browser_id=o.id AND status IN('pending','claimed');
          UPDATE public.mixer_browser_session_vault SET epoch=b.epoch,session_revision=b.revision,vault_generation=vault_generation+1,envelope_kind='erased',key_id=NULL,iv=NULL,tag=NULL,ciphertext=NULL WHERE browser_id=o.id;
          PERFORM public.mixer_browser_audit(o,b,'expire','expired',NULL,p_request,NULL::public.mixer_browser_verified);
          RETURN true;
        END;
        """
      )
    ]
  end
end
