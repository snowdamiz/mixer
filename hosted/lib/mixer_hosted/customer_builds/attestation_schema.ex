defmodule MixerHosted.CustomerBuilds.AttestationSchema do
  @moduledoc false
  alias MixerHosted.Authorization.Postgres.Session
  alias MixerHosted.CustomerBuilds.CreateSchema

  @writer "mixer_native_attestation_writer"
  @table "public.mixer_native_development_attestations"
  @name "mixer_native_development_attestation_v1"
  @entry "public.#{@name}(text,text,text,text,jsonb,text,text,text,text,bytea)"
  @authz_tables ~w(profiles principals bindings families credentials organizations projects
                  applications environments organization_heads project_heads memberships)
  @authz_locks ~w(profiles principals families credentials organization_heads project_heads)

  def writer, do: @writer

  def writer_grant_objects do
    {Enum.map(@authz_tables, &"public.mixer_authz_#{&1}"),
     Enum.map(@authz_locks, &"public.mixer_authz_lock_#{&1}()"), @entry}
  end

  defp body do
    """
    DECLARE
      completion jsonb;
      stored #{@table}%ROWTYPE;
    BEGIN
      IF session_user <> '#{@writer}' OR (#{CreateSchema.guard(:attest)}) IS DISTINCT FROM true
      THEN RETURN NULL; END IF;

      -- Keep the coordinator's global mutex before its build and admission locks.
      PERFORM pg_catalog.pg_advisory_xact_lock(1296648258, 1);
      SELECT jsonb_build_object('record',to_jsonb(b),'attempt',r.attempt,
        'worker_fence',r.worker_fence,'terminal_event_id',r.terminal_event_id,'lease_epoch',l.epoch)
      INTO completion
      FROM public.mixer_builds b
      JOIN public.mixer_build_reservations r ON r.build_record_id=b.id
      JOIN public.mixer_build_coordinator_leases l ON l.build_record_id=b.id
      WHERE b.organization_id=current_setting('mixer.authz.organization_id',true)
        AND b.project_id=current_setting('mixer.authz.project_id',true)
        AND b.application_id=current_setting('mixer.authz.application_id',true)
        AND b.build_id=$1 AND b.platform='ios'
        AND b.journal#>>'{creation,spec,source,sha256}'=$2
        AND b.journal#>>'{creation,spec,toolchain_lock_sha256}'=$3
        AND b.journal#>>'{creation,spec,build_definition_sha256}'=$4
        AND b.journal#>>'{events,-1,event,type}'='completed'
        AND b.journal#>>'{events,-1,event,result,outcome}'='native_succeeded'
        AND NOT r.held AND r.organization_id=b.organization_id AND r.platform=b.platform
        AND r.terminal_event_id=b.journal#>>'{events,-1,id}'
        AND r.attempt::text=b.journal#>>'{events,-1,event,ref,attempt}'
        AND r.worker_fence::text=b.journal#>>'{events,-1,event,ref,fence}'
        AND l.owner_id IS NULL AND l.expires_at IS NULL
      FOR SHARE OF b,r,l;

      IF completion IS NULL OR (#{CreateSchema.guard(:attest)}) IS DISTINCT FROM true
      THEN RETURN NULL; END IF;

      IF $5 IS NULL THEN
        IF $6 IS NULL AND $7 IS NULL AND $8 IS NULL AND $9 IS NULL AND $10 IS NULL THEN
          RETURN completion;
        END IF;
        RETURN NULL;
      END IF;

      IF completion IS DISTINCT FROM $5 THEN RETURN '"conflict"'::jsonb; END IF;

      INSERT INTO #{@table} (build_record_id,journal_revision,attempt,worker_operation_id,
        native_binding_sha256,signer_key_sha256,signing_origin,envelope)
      VALUES ((completion#>>'{record,id}')::uuid,(completion#>>'{record,revision}')::bigint,
        (completion->>'attempt')::integer,$6,$7,$8,$9,$10)
      ON CONFLICT (build_record_id) DO NOTHING;
      IF FOUND THEN RETURN '"attached"'::jsonb; END IF;

      SELECT * INTO STRICT stored FROM #{@table}
      WHERE build_record_id=(completion#>>'{record,id}')::uuid;
      IF ROW(stored.journal_revision,stored.attempt,stored.worker_operation_id,
        stored.native_binding_sha256,stored.signer_key_sha256,stored.signing_origin,stored.envelope)
        IS NOT DISTINCT FROM ROW((completion#>>'{record,revision}')::bigint,
          (completion->>'attempt')::integer,$6,$7,$8,$9,$10)
      THEN RETURN '"duplicate"'::jsonb; END IF;
      RETURN '"immutable_conflict"'::jsonb;
    END
    """
  end

  def statements do
    [
      """
      CREATE TABLE #{@table} (
        build_record_id uuid PRIMARY KEY REFERENCES public.mixer_builds(id) ON DELETE RESTRICT,
        journal_revision bigint NOT NULL CHECK (journal_revision BETWEEN 2 AND 32),
        attempt integer NOT NULL CHECK (attempt BETWEEN 1 AND 5),
        worker_operation_id text NOT NULL CHECK (worker_operation_id ~ '^[0-9a-f]{64}$'),
        native_binding_sha256 text NOT NULL CHECK (native_binding_sha256 ~ '^[0-9a-f]{64}$'),
        signer_key_sha256 text NOT NULL CHECK (signer_key_sha256 ~ '^[0-9a-f]{64}$'),
        signing_origin text NOT NULL CHECK (signing_origin ~ '^http://127[.]0[.]0[.]1:[0-9]+$'
          AND octet_length(signing_origin) <= 16401),
        envelope bytea NOT NULL CHECK (octet_length(envelope) BETWEEN 1 AND 16384)
      )
      """,
      "REVOKE ALL ON #{@table} FROM PUBLIC",
      "ALTER TABLE #{@table} ENABLE ROW LEVEL SECURITY",
      "ALTER TABLE #{@table} FORCE ROW LEVEL SECURITY",
      "CREATE POLICY attestation_owner_read ON #{@table} FOR SELECT TO CURRENT_USER USING (true)",
      "CREATE POLICY attestation_owner_insert ON #{@table} FOR INSERT TO CURRENT_USER WITH CHECK (true)",
      "CREATE FUNCTION #{@entry} RETURNS jsonb LANGUAGE plpgsql VOLATILE SECURITY DEFINER " <>
        "SET search_path=pg_catalog AS $attestation$" <> body() <> "$attestation$",
      "REVOKE ALL ON FUNCTION #{@entry} FROM PUBLIC"
    ]
  end

  def fixture_grant_statement, do: "GRANT EXECUTE ON FUNCTION #{@entry} TO #{@writer}"

  def owner_access_sql(relation) do
    """
    pg_catalog.has_table_privilege(#{relation}.relowner,#{relation}.oid,'SELECT')
    AND pg_catalog.has_table_privilege(#{relation}.relowner,#{relation}.oid,'INSERT')
    AND (SELECT count(*)=2 AND count(*) FILTER (WHERE q.polpermissive
        AND q.polroles=ARRAY[#{relation}.relowner]
        AND ((q.polname='attestation_owner_read' AND q.polcmd='r'
              AND pg_catalog.pg_get_expr(q.polqual,q.polrelid)='true' AND q.polwithcheck IS NULL)
          OR (q.polname='attestation_owner_insert' AND q.polcmd='a'
              AND q.polqual IS NULL AND pg_catalog.pg_get_expr(q.polwithcheck,q.polrelid)='true')))=2
      FROM pg_catalog.pg_policy q WHERE q.polrelid=#{relation}.oid)
    """
  end

  def admit!(repo) do
    [safe] =
      Session.one!(
        repo,
        """
        SELECT count(*)=1 AND COALESCE(bool_and(
          current_user=session_user AND w.rolname=current_user
          AND w.rolcanlogin AND NOT (w.rolsuper OR w.rolbypassrls OR w.rolinherit
            OR w.rolcreaterole OR w.rolcreatedb OR w.rolreplication)
          AND NOT EXISTS (SELECT 1 FROM pg_auth_members WHERE member=w.oid OR roleid=w.oid)
          AND NOT has_schema_privilege(w.oid,n.oid,'CREATE')
          AND p.oid=to_regprocedure($2) AND p.prosrc=$3 AND p.prosecdef AND p.provolatile='v'
          AND p.prorettype='jsonb'::regtype AND p.proconfig=ARRAY['search_path=pg_catalog']::text[]
          AND p.prokind='f' AND NOT p.proretset AND NOT p.proisstrict AND NOT p.proleakproof
          AND p.pronargdefaults=0 AND p.prosupport=0 AND p.provariadic=0
          AND p.prolang=(SELECT oid FROM pg_language WHERE lanname='plpgsql')
          AND NOT (o.rolcanlogin OR o.rolsuper OR o.rolbypassrls)
          AND has_function_privilege(w.oid,p.oid,'EXECUTE')
          AND EXISTS (
            SELECT 1 FROM aclexplode(p.proacl) a
            WHERE a.grantee=w.oid AND a.grantor=p.proowner
              AND a.privilege_type='EXECUTE' AND NOT a.is_grantable
          )
          AND NOT EXISTS (
            SELECT 1 FROM aclexplode(COALESCE(p.proacl, acldefault('f',p.proowner))) a
            WHERE a.grantor<>p.proowner OR a.grantee NOT IN (p.proowner,w.oid)
              OR a.privilege_type<>'EXECUTE' OR a.is_grantable
          )
          AND t.relowner=p.proowner AND t.relkind='r' AND t.relrowsecurity AND t.relforcerowsecurity
          AND #{owner_access_sql("t")}
          AND NOT EXISTS (
            SELECT 1 FROM aclexplode(t.relacl) a WHERE a.grantee<>t.relowner
          )
          AND NOT EXISTS (
            SELECT 1 FROM pg_attribute col, LATERAL aclexplode(col.attacl) a
            WHERE col.attrelid=t.oid AND a.grantee<>t.relowner
          )
          AND NOT EXISTS (
            SELECT 1 FROM pg_class c
            WHERE c.oid IN (t.oid,'public.mixer_builds'::regclass,
              'public.mixer_build_reservations'::regclass,'public.mixer_build_coordinator_leases'::regclass)
              AND (has_table_privilege(w.oid,c.oid,'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER')
                OR has_any_column_privilege(w.oid,c.oid,'SELECT,INSERT,UPDATE,REFERENCES'))
          )
        ),false)
        FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
        JOIN pg_roles o ON o.oid=p.proowner JOIN pg_roles w ON w.rolname=$4
        JOIN pg_class t ON t.relnamespace=n.oid AND t.relname='mixer_native_development_attestations'
        WHERE n.nspname='public' AND p.proname=$1
        """,
        [@name, @entry, body(), @writer],
        :authorization_unavailable
      )

    if safe != true, do: {:error, :authorization_unavailable}, else: :ok
  end

  def apply!(repo, selection, payload) do
    args = [
      selection.build_id,
      selection.source_sha256,
      selection.toolchain_lock_sha256,
      selection.build_definition_sha256
      | payload
    ]

    sql = "SELECT public.#{@name}($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)"

    response =
      Ecto.Adapters.SQL.query!(repo, sql, args,
        timeout: 5_000,
        queue: false,
        log: false,
        telemetry_event: nil
      )

    case response.rows do
      [[nil]] when hd(payload) == nil -> {:error, :not_found}
      [[nil]] -> {:error, :conflict}
      [["conflict"]] -> {:error, :conflict}
      [["immutable_conflict"]] -> {:error, :immutable_conflict}
      [["attached"]] -> {:ok, :attached}
      [["duplicate"]] -> {:ok, :duplicate}
      [[%{} = snapshot]] -> {:ok, snapshot}
      _ -> {:error, :storage_unavailable}
    end
  end
end
