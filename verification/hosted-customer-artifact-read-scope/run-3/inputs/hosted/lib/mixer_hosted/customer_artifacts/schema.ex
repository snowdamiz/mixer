defmodule MixerHosted.CustomerArtifacts.Schema do
  @moduledoc false
  @tables ~w(artifact_heads artifacts audit_events idempotency)
  def tables, do: Enum.map(@tables, &("mixer_customer_" <> &1))
  def functions, do: Map.keys(functions_sql()) |> Enum.sort()
  def statements, do: table_statements() ++ function_statements() ++ policies() ++ triggers()

  defp table_statements do
    [
      """
      CREATE TABLE public.mixer_customer_artifact_heads (
        organization_id text NOT NULL, project_id text NOT NULL,
        sequence bigint NOT NULL CHECK (sequence BETWEEN 0 AND 9007199254740991),
        event_sha256 text NOT NULL CHECK (event_sha256 ~ '^[0-9a-f]{64}$' OR (sequence=0 AND event_sha256='')),
        state_sha256 text NOT NULL CHECK (state_sha256 ~ '^[0-9a-f]{64}$'),
        PRIMARY KEY (organization_id,project_id),
        FOREIGN KEY (organization_id,project_id) REFERENCES public.mixer_authz_projects(organization_id,id)
      )
      """,
      """
      CREATE TABLE public.mixer_customer_artifacts (
        organization_id text NOT NULL, project_id text NOT NULL,
        application_id text NOT NULL, environment_id text NOT NULL,
        platform text NOT NULL CHECK (platform IN ('ios','android')),
        runtime_sha256 text NOT NULL CHECK (runtime_sha256 ~ '^[0-9a-f]{64}$'),
        manifest_sha256 text NOT NULL CHECK (manifest_sha256 ~ '^[0-9a-f]{64}$'),
        payload_sha256 text NOT NULL CHECK (payload_sha256 ~ '^[0-9a-f]{64}$'),
        envelope_sha256 text NOT NULL CHECK (envelope_sha256 ~ '^[0-9a-f]{64}$'),
        envelope_bytes bytea NOT NULL CHECK (octet_length(envelope_bytes) BETWEEN 1 AND 6291456),
        signed_manifest_bytes bytea NOT NULL CHECK (octet_length(signed_manifest_bytes) BETWEEN 1 AND 65536),
        canonical_manifest_cbor bytea NOT NULL CHECK (octet_length(canonical_manifest_cbor) BETWEEN 1 AND 65536),
        signature bytea NOT NULL CHECK (octet_length(signature)=64),
        payload bytea NOT NULL CHECK (octet_length(payload) BETWEEN 1 AND 4194304),
        creating_sequence bigint NOT NULL CHECK (creating_sequence BETWEEN 1 AND 9007199254740991),
        PRIMARY KEY (organization_id,project_id,manifest_sha256),
        FOREIGN KEY (organization_id,project_id,application_id,environment_id)
          REFERENCES public.mixer_authz_environments(organization_id,project_id,application_id,id),
        FOREIGN KEY (organization_id,project_id) REFERENCES public.mixer_customer_artifact_heads(organization_id,project_id)
      )
      """,
      """
      CREATE TABLE public.mixer_customer_audit_events (
        organization_id text NOT NULL, project_id text NOT NULL,
        sequence bigint NOT NULL CHECK (sequence BETWEEN 1 AND 9007199254740991),
        manifest_sha256 text NOT NULL CHECK (manifest_sha256 ~ '^[0-9a-f]{64}$'),
        audit_schema smallint NOT NULL CHECK (audit_schema=2),
        event_cbor bytea NOT NULL CHECK (octet_length(event_cbor) BETWEEN 1 AND 65536),
        event_sha256 text NOT NULL CHECK (event_sha256 ~ '^[0-9a-f]{64}$'),
        previous_event_sha256 text NOT NULL CHECK (previous_event_sha256 ~ '^[0-9a-f]{64}$' OR (sequence=1 AND previous_event_sha256='')),
        previous_state_sha256 text NOT NULL CHECK (previous_state_sha256 ~ '^[0-9a-f]{64}$'),
        current_state_sha256 text NOT NULL CHECK (current_state_sha256 ~ '^[0-9a-f]{64}$'),
        display jsonb NOT NULL CHECK (jsonb_typeof(display)='object' AND octet_length(display::text)<=131072),
        PRIMARY KEY (organization_id,project_id,sequence),
        FOREIGN KEY (organization_id,project_id,manifest_sha256)
          REFERENCES public.mixer_customer_artifacts(organization_id,project_id,manifest_sha256) DEFERRABLE INITIALLY DEFERRED
      )
      """,
      """
      ALTER TABLE public.mixer_customer_artifacts ADD CONSTRAINT mixer_customer_artifacts_creating_event
        FOREIGN KEY (organization_id,project_id,creating_sequence)
        REFERENCES public.mixer_customer_audit_events(organization_id,project_id,sequence) DEFERRABLE INITIALLY DEFERRED
      """,
      """
      CREATE TABLE public.mixer_customer_idempotency (
        organization_id text NOT NULL, project_id text NOT NULL,
        key text NOT NULL CHECK (octet_length(key) BETWEEN 1 AND 128 AND key ~ '^[A-Za-z0-9_.:-]+$'),
        principal_id text NOT NULL REFERENCES public.mixer_authz_principals(id),
        action text NOT NULL CHECK (action='artifact.upload'),
        application_id text NOT NULL, environment_id text NOT NULL,
        manifest_sha256 text NOT NULL CHECK (manifest_sha256 ~ '^[0-9a-f]{64}$'),
        request_sha256 text NOT NULL CHECK (request_sha256 ~ '^[0-9a-f]{64}$'),
        event_sequence bigint NOT NULL CHECK (event_sequence BETWEEN 1 AND 9007199254740991),
        status integer NOT NULL CHECK (status IN (200,201)),
        payload_sha256 text NOT NULL CHECK (payload_sha256 ~ '^[0-9a-f]{64}$'),
        PRIMARY KEY (organization_id,project_id,key),
        UNIQUE (organization_id,project_id,event_sequence),
        FOREIGN KEY (organization_id,project_id,event_sequence)
          REFERENCES public.mixer_customer_audit_events(organization_id,project_id,sequence) DEFERRABLE INITIALLY DEFERRED,
        FOREIGN KEY (organization_id,project_id,manifest_sha256)
          REFERENCES public.mixer_customer_artifacts(organization_id,project_id,manifest_sha256) DEFERRABLE INITIALLY DEFERRED,
        FOREIGN KEY (organization_id,project_id,application_id,environment_id)
          REFERENCES public.mixer_authz_environments(organization_id,project_id,application_id,id)
      )
      """
    ]
  end

  def functions_sql do
    %{
      "mixer_customer_cbor_head" =>
        {"major integer, n numeric", "bytea", "IMMUTABLE", false,
         """
         DECLARE r bytea; b integer; width integer; x numeric := n;
         BEGIN
           IF n < 0 OR n > 18446744073709551615 OR n <> trunc(n) OR major NOT IN (0,3,4,5) THEN RAISE EXCEPTION 'invalid cbor'; END IF;
           IF n < 24 THEN RETURN set_byte(decode('00','hex'),0,major*32+n::integer); END IF;
           IF n<=255 THEN width:=1; b:=24; ELSIF n<=65535 THEN width:=2; b:=25; ELSIF n<=4294967295 THEN width:=4; b:=26; ELSE width:=8; b:=27; END IF;
           r:=set_byte(decode(repeat('00',width+1),'hex'),0,major*32+b);
           FOR i IN REVERSE width..1 LOOP r:=set_byte(r,i,mod(x,256)::integer); x:=div(x,256); END LOOP;
           RETURN r;
         END
         """},
      "mixer_customer_cbor_part" =>
        {"v jsonb, depth integer, remaining integer", "TABLE(encoded bytea, items integer)",
         "IMMUTABLE", false,
         """
         DECLARE kind text := jsonb_typeof(v); result bytea; count integer:=1; n integer; part record; pair record; val jsonb;
         BEGIN
           IF depth>16 OR remaining<1 THEN RAISE EXCEPTION 'cbor limit'; END IF;
           IF kind='string' THEN result:=convert_to(v#>>'{}','UTF8'); result:=public.mixer_customer_cbor_head(3,octet_length(result))||result;
           ELSIF kind='number' THEN result:=public.mixer_customer_cbor_head(0,(v#>>'{}')::numeric);
           ELSIF kind='boolean' THEN result:=CASE WHEN v='true'::jsonb THEN decode('f5','hex') ELSE decode('f4','hex') END;
           ELSIF kind='array' THEN
             n:=jsonb_array_length(v); IF n>256 THEN RAISE EXCEPTION 'cbor container'; END IF;
             result:=public.mixer_customer_cbor_head(4,n);
             FOR val IN SELECT value FROM jsonb_array_elements(v) LOOP
               SELECT * INTO STRICT part FROM public.mixer_customer_cbor_part(val,depth+1,remaining-count);
               count:=count+part.items; result:=result||part.encoded;
               IF octet_length(result)>65536 THEN RAISE EXCEPTION 'cbor output'; END IF;
             END LOOP;
           ELSIF kind='object' THEN
             SELECT count(*) INTO n FROM jsonb_each(v); IF n>256 THEN RAISE EXCEPTION 'cbor container'; END IF;
             result:=public.mixer_customer_cbor_head(5,n);
             FOR pair IN SELECT key,value, public.mixer_customer_cbor_head(3,octet_length(convert_to(key,'UTF8')))||convert_to(key,'UTF8') AS k FROM jsonb_each(v) ORDER BY k LOOP
               IF depth+1>16 OR count+1>=remaining THEN RAISE EXCEPTION 'cbor items'; END IF;
               count:=count+1; result:=result||pair.k;
               SELECT * INTO STRICT part FROM public.mixer_customer_cbor_part(pair.value,depth+1,remaining-count);
               count:=count+part.items; result:=result||part.encoded;
               IF octet_length(result)>65536 THEN RAISE EXCEPTION 'cbor output'; END IF;
             END LOOP;
           ELSE RAISE EXCEPTION 'invalid cbor value'; END IF;
           IF count>remaining OR octet_length(result)>65536 THEN RAISE EXCEPTION 'cbor limit'; END IF;
           RETURN QUERY SELECT result,count;
         END
         """},
      "mixer_customer_cbor" =>
        {"v jsonb", "bytea", "IMMUTABLE", false,
         """
         DECLARE b bytea;
         BEGIN SELECT encoded INTO STRICT b FROM public.mixer_customer_cbor_part(v,0,4096); RETURN b; END
         """},
      "mixer_customer_hash" =>
        {"domain text, v jsonb", "text", "IMMUTABLE", false,
         """
         BEGIN RETURN encode(sha256(convert_to(domain,'UTF8')||decode('00','hex')||public.mixer_customer_cbor(v)),'hex'); END
         """},
      "mixer_customer_allowed" =>
        {"org text, proj text, app text, env text, requested text, metadata boolean", "boolean",
         "STABLE", false, allowed_body()},
      "mixer_customer_artifact_metadata" =>
        {"digest text",
         "TABLE(organization_id text,project_id text,application_id text,environment_id text,platform text,runtime_sha256 text,manifest_sha256 text,signed_manifest_bytes bytea)",
         "STABLE", true,
         """
         BEGIN
           IF digest IS NULL OR digest !~ '^[0-9a-f]{64}$' OR current_setting('mixer.authz.phase',true) IS DISTINCT FROM 'metadata'
             OR coalesce(current_setting('mixer.authz.application_id',true),'')<>'' OR coalesce(current_setting('mixer.authz.environment_id',true),'')<>'' THEN RETURN; END IF;
           RETURN QUERY SELECT a.organization_id,a.project_id,a.application_id,a.environment_id,a.platform,a.runtime_sha256,a.manifest_sha256,a.signed_manifest_bytes
             FROM public.mixer_customer_artifacts a WHERE a.manifest_sha256=digest
             AND public.mixer_customer_allowed(a.organization_id,a.project_id,'','', 'artifact.read',true);
         END
         """},
      "mixer_customer_key_exists" =>
        {"candidate text", "boolean", "STABLE", true,
         """
         BEGIN
           IF candidate IS NULL OR octet_length(candidate) NOT BETWEEN 1 AND 128 OR candidate !~ '^[A-Za-z0-9_.:-]+$'
             OR NOT public.mixer_customer_allowed(current_setting('mixer.authz.organization_id',true),current_setting('mixer.authz.project_id',true),current_setting('mixer.authz.application_id',true),current_setting('mixer.authz.environment_id',true),'artifact.upload',false)
             THEN RETURN false; END IF;
           RETURN EXISTS (SELECT 1 FROM public.mixer_customer_idempotency d WHERE d.organization_id=current_setting('mixer.authz.organization_id',true) AND d.project_id=current_setting('mixer.authz.project_id',true) AND d.key=candidate);
         END
         """},
      "mixer_customer_immutable" =>
        {"", "trigger", "VOLATILE", false,
         "BEGIN RAISE EXCEPTION 'immutable customer ledger'; END"},
      "mixer_customer_integrity" => {"", "trigger", "VOLATILE", true, integrity_body()}
    }
  end

  def signatures do
    %{
      "mixer_customer_cbor_head" => "integer,numeric",
      "mixer_customer_cbor_part" => "jsonb,integer,integer",
      "mixer_customer_cbor" => "jsonb",
      "mixer_customer_hash" => "text,jsonb",
      "mixer_customer_allowed" => "text,text,text,text,text,boolean",
      "mixer_customer_artifact_metadata" => "text",
      "mixer_customer_key_exists" => "text",
      "mixer_customer_immutable" => "",
      "mixer_customer_integrity" => ""
    }
  end

  defp function_statements do
    Enum.flat_map(functions_sql(), fn {name, {args, returns, volatility, definer, body}} ->
      [
        "CREATE FUNCTION public.#{name}(#{args}) RETURNS #{returns} LANGUAGE plpgsql #{volatility} #{if definer, do: "SECURITY DEFINER", else: "SECURITY INVOKER"} SET search_path=pg_catalog AS $mixer$\n#{body}$mixer$",
        "REVOKE ALL ON FUNCTION public.#{name}(#{signatures()[name]}) FROM PUBLIC"
      ]
    end)
  end

  defp allowed_body do
    """
    DECLARE issued numeric; expiry numeric; now numeric:=extract(epoch FROM statement_timestamp());
    BEGIN
      IF current_setting('mixer.authz.identity_class',true) IS DISTINCT FROM 'human'
        OR org IS DISTINCT FROM current_setting('mixer.authz.organization_id',true)
        OR proj IS DISTINCT FROM current_setting('mixer.authz.project_id',true)
        OR requested IS DISTINCT FROM current_setting('mixer.authz.action',true)
        OR requested NOT IN ('artifact.upload','artifact.read','audit.read')
        OR current_setting('mixer.authz.required_scope',true) IS DISTINCT FROM
           (CASE requested WHEN 'artifact.upload' THEN 'mixer.artifact.upload' WHEN 'artifact.read' THEN 'mixer.artifact.read' ELSE 'mixer.audit.read' END)
        OR current_setting('mixer.authz.phase',true) IS DISTINCT FROM (CASE WHEN metadata THEN 'metadata' ELSE 'effect' END)
        OR coalesce(current_setting('mixer.authz.token_issued_at',true),'') !~ '^(0|[1-9][0-9]{0,15})$'
        OR coalesce(current_setting('mixer.authz.token_expires_at',true),'') !~ '^(0|[1-9][0-9]{0,15})$'
        THEN RETURN false; END IF;
      issued:=current_setting('mixer.authz.token_issued_at',true)::numeric;
      expiry:=current_setting('mixer.authz.token_expires_at',true)::numeric;
      IF issued>9007199254740991 OR expiry>9007199254740991 OR issued>now+30 OR expiry<=now OR issued>=expiry THEN RETURN false; END IF;
      IF NOT metadata AND requested<>'audit.read' AND
        (app IS DISTINCT FROM current_setting('mixer.authz.application_id',true) OR env IS DISTINCT FROM current_setting('mixer.authz.environment_id',true)) THEN RETURN false; END IF;
      IF requested='audit.read' AND
        (coalesce(current_setting('mixer.authz.application_id',true),'')<>'' OR coalesce(current_setting('mixer.authz.environment_id',true),'')<>'') THEN RETURN false; END IF;
      RETURN EXISTS (
        SELECT 1 FROM public.mixer_authz_profiles pf
        JOIN public.mixer_authz_bindings b ON b.profile_id=pf.id AND b.profile_version=pf.version AND b.subject=current_setting('mixer.authz.subject',true)
        JOIN public.mixer_authz_principals pr ON pr.id=b.principal_id AND pr.identity_class='human'
        JOIN public.mixer_authz_credentials c ON c.profile_id=pf.id AND c.profile_version=pf.version AND c.reference=current_setting('mixer.authz.credential_ref',true) AND c.principal_id=pr.id
        JOIN public.mixer_authz_families f ON f.id=c.family_id AND f.principal_id=pr.id AND f.profile_id=pf.id AND f.profile_version=pf.version
        JOIN public.mixer_authz_organizations o ON o.id=org
        JOIN public.mixer_authz_projects p ON p.organization_id=org AND p.id=proj
        JOIN public.mixer_authz_memberships m ON m.principal_id=pr.id AND m.organization_id=org
        WHERE pf.active AND b.active AND pr.active AND c.active AND f.active AND o.active AND p.active
          AND pf.identity_class='human' AND b.identity_class='human'
          AND pf.id=current_setting('mixer.authz.profile_id',true) AND pf.version::text=current_setting('mixer.authz.profile_version',true)
          AND pf.issuer=current_setting('mixer.authz.issuer',true) AND pf.client_id=current_setting('mixer.authz.client_id',true)
          AND pr.id=current_setting('mixer.authz.principal_id',true) AND f.id=current_setting('mixer.authz.family_id',true)
          AND pr.not_before<=issued AND c.not_before<=issued AND f.not_before<=issued
          AND c.not_before<=now AND f.not_before<=now AND (c.expires_at IS NULL OR now<c.expires_at) AND (f.expires_at IS NULL OR now<f.expires_at)
          AND m.active AND m.not_before<=now AND (m.expires_at IS NULL OR now<m.expires_at)
          AND ((m.project_binding='all_projects' AND m.project_id IS NULL) OR (m.project_binding='exact_project' AND m.project_id=proj))
          AND m.role=ANY(CASE WHEN requested='artifact.upload' THEN ARRAY['owner','administrator','developer'] ELSE ARRAY['owner','administrator','developer','release_manager','viewer'] END)
          AND (metadata OR requested='audit.read' OR EXISTS (SELECT 1 FROM public.mixer_authz_applications a JOIN public.mixer_authz_environments e
            ON e.organization_id=a.organization_id AND e.project_id=a.project_id AND e.application_id=a.id
            WHERE a.organization_id=org AND a.project_id=proj AND a.id=app AND a.active AND e.id=env AND e.active))
      );
    END
    """
  end

  defp policies do
    tables = [
      "mixer_customer_artifact_heads",
      "mixer_customer_artifacts",
      "mixer_customer_audit_events",
      "mixer_customer_idempotency"
    ]

    base =
      Enum.flat_map(tables, fn table ->
        [
          "ALTER TABLE public.#{table} ENABLE ROW LEVEL SECURITY",
          "ALTER TABLE public.#{table} FORCE ROW LEVEL SECURITY",
          "REVOKE ALL ON public.#{table} FROM PUBLIC"
        ]
      end)

    owner =
      "current_user::text = (SELECT r.rolname FROM pg_catalog.pg_class c JOIN pg_catalog.pg_roles r ON r.oid=c.relowner WHERE c.oid='public.mixer_customer_artifacts'::regclass)"

    allowed =
      "public.mixer_customer_allowed(organization_id,project_id,application_id,environment_id,current_setting('mixer.authz.action',true),false)"

    base ++
      [
        "CREATE POLICY customer_integrity_owner ON public.mixer_customer_artifact_heads FOR SELECT USING (#{owner})",
        "CREATE POLICY customer_read ON public.mixer_customer_artifacts FOR SELECT USING (current_setting('mixer.authz.action',true) IN ('artifact.upload','artifact.read') AND #{allowed})",
        "CREATE POLICY customer_insert ON public.mixer_customer_artifacts FOR INSERT WITH CHECK (current_setting('mixer.authz.action',true)='artifact.upload' AND #{allowed})",
        "CREATE POLICY customer_metadata_owner ON public.mixer_customer_artifacts FOR SELECT USING (#{owner} AND current_setting('mixer.authz.phase',true)='metadata' AND public.mixer_customer_allowed(organization_id,project_id,'','','artifact.read',true))",
        "CREATE POLICY customer_integrity_owner ON public.mixer_customer_artifacts FOR SELECT USING (#{owner} AND current_setting('mixer.authz.phase',true)='effect' AND organization_id=current_setting('mixer.authz.organization_id',true) AND project_id=current_setting('mixer.authz.project_id',true))",
        "CREATE POLICY customer_read ON public.mixer_customer_artifact_heads FOR SELECT USING (public.mixer_customer_allowed(organization_id,project_id,current_setting('mixer.authz.application_id',true),current_setting('mixer.authz.environment_id',true),current_setting('mixer.authz.action',true),false))",
        "CREATE POLICY customer_transition ON public.mixer_customer_artifact_heads FOR UPDATE USING (public.mixer_customer_allowed(organization_id,project_id,current_setting('mixer.authz.application_id',true),current_setting('mixer.authz.environment_id',true),'artifact.upload',false)) WITH CHECK (public.mixer_customer_allowed(organization_id,project_id,current_setting('mixer.authz.application_id',true),current_setting('mixer.authz.environment_id',true),'artifact.upload',false))",
        "CREATE POLICY customer_read ON public.mixer_customer_audit_events FOR SELECT USING (public.mixer_customer_allowed(organization_id,project_id,'','','audit.read',false))",
        "CREATE POLICY customer_insert ON public.mixer_customer_audit_events FOR INSERT WITH CHECK (public.mixer_customer_allowed(organization_id,project_id,current_setting('mixer.authz.application_id',true),current_setting('mixer.authz.environment_id',true),'artifact.upload',false))",
        "CREATE POLICY customer_integrity_owner ON public.mixer_customer_audit_events FOR SELECT USING (#{owner} AND current_setting('mixer.authz.phase',true)='effect' AND organization_id=current_setting('mixer.authz.organization_id',true) AND project_id=current_setting('mixer.authz.project_id',true))",
        "CREATE POLICY customer_read ON public.mixer_customer_idempotency FOR SELECT USING (principal_id=current_setting('mixer.authz.principal_id',true) AND public.mixer_customer_allowed(organization_id,project_id,application_id,environment_id,'artifact.upload',false))",
        "CREATE POLICY customer_insert ON public.mixer_customer_idempotency FOR INSERT WITH CHECK (principal_id=current_setting('mixer.authz.principal_id',true) AND public.mixer_customer_allowed(organization_id,project_id,application_id,environment_id,'artifact.upload',false))",
        "CREATE POLICY customer_integrity_owner ON public.mixer_customer_idempotency FOR SELECT USING (#{owner} AND current_setting('mixer.authz.phase',true)='effect' AND organization_id=current_setting('mixer.authz.organization_id',true) AND project_id=current_setting('mixer.authz.project_id',true))"
      ]
  end

  defp triggers do
    Enum.flat_map(~w(artifacts audit_events idempotency), fn table ->
      [
        "CREATE TRIGGER customer_immutable BEFORE UPDATE OR DELETE ON public.mixer_customer_#{table} FOR EACH ROW EXECUTE FUNCTION public.mixer_customer_immutable()"
      ]
    end) ++
      Enum.map(["artifact_heads", "artifacts", "audit_events", "idempotency"], fn table ->
        "CREATE CONSTRAINT TRIGGER customer_integrity AFTER INSERT OR UPDATE ON public.mixer_customer_#{table} DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION public.mixer_customer_integrity()"
      end)
  end

  defp integrity_body do
    """
    DECLARE h record; a record; e record; d record; prev record; document jsonb; envelope json; value jsonb; expected text; expected_state text; n bigint; org text:=NEW.organization_id; proj text:=NEW.project_id;
    BEGIN
      SELECT * INTO STRICT h FROM public.mixer_customer_artifact_heads x WHERE x.organization_id=org AND x.project_id=proj;
      IF TG_TABLE_NAME='mixer_customer_artifact_heads' AND TG_OP='INSERT' AND h.sequence=0 THEN
        IF h.event_sha256<>'' OR h.state_sha256<>public.mixer_customer_hash('mixer.hosted.customer.state.v2',jsonb_build_array(2,org,proj)) THEN RAISE EXCEPTION 'invalid genesis'; END IF;
        RETURN NULL;
      END IF;
      IF TG_TABLE_NAME='mixer_customer_artifact_heads' THEN
        IF TG_OP<>'UPDATE' OR NEW.sequence<>OLD.sequence+1 THEN RAISE EXCEPTION 'invalid head transition'; END IF;
        n:=NEW.sequence;
      ELSIF TG_TABLE_NAME='mixer_customer_artifacts' THEN n:=NEW.creating_sequence;
      ELSIF TG_TABLE_NAME='mixer_customer_audit_events' THEN n:=NEW.sequence;
      ELSE n:=NEW.event_sequence; END IF;
      SELECT * INTO STRICT e FROM public.mixer_customer_audit_events x WHERE x.organization_id=org AND x.project_id=proj AND x.sequence=n;
      SELECT * INTO STRICT a FROM public.mixer_customer_artifacts x WHERE x.organization_id=org AND x.project_id=proj AND x.manifest_sha256=e.manifest_sha256;
      SELECT * INTO STRICT d FROM public.mixer_customer_idempotency x WHERE x.organization_id=org AND x.project_id=proj AND x.event_sequence=n;
      IF h.sequence<n OR e.display->>'audit_schema'<>'2' OR (SELECT count(*) FROM jsonb_object_keys(e.display))<>18
        OR NOT e.display ?& ARRAY['audit_schema','sequence','tenant','actor','authorization','target','action','outcome','reason','request_id','source_ip','recorded_at','previous_state_sha256','current_state_sha256','previous_event_sha256','request_sha256','envelope_sha256','event_sha256']
        THEN RAISE EXCEPTION 'invalid event projection'; END IF;
      value:=jsonb_build_array(e.display->'audit_schema',e.display->'sequence',e.display->'tenant',e.display->'actor',e.display->'authorization',e.display->'target',e.display->'action',e.display->'outcome',e.display->'reason',e.display->'request_id',e.display->'source_ip',e.display->'recorded_at',e.display->'previous_state_sha256',e.display->'current_state_sha256',e.display->'previous_event_sha256',e.display->'request_sha256',e.display->'envelope_sha256');
      IF e.event_cbor<>public.mixer_customer_cbor(value)
        OR e.event_sha256<>encode(sha256(convert_to('mixer.hosted.customer.audit.v2','UTF8')||decode('00','hex')||e.event_cbor),'hex')
        OR e.display->>'event_sha256'<>e.event_sha256 OR e.display->'sequence'<>to_jsonb(n) OR e.display->'tenant'<>jsonb_build_array(org,proj)
        OR e.display->>'previous_event_sha256'<>e.previous_event_sha256 OR e.display->>'previous_state_sha256'<>e.previous_state_sha256 OR e.display->>'current_state_sha256'<>e.current_state_sha256
        OR e.display->>'action'<>'artifact.upload' OR e.display->>'outcome' NOT IN ('created','unchanged')
        OR e.display->>'request_id' !~ '^[0-9a-f]{32}$' OR octet_length(e.display->>'reason')>512
        OR jsonb_array_length(e.display->'actor')<>12 OR jsonb_array_length(e.display->'authorization')<>11 OR jsonb_array_length(e.display->'target')<>8
        OR e.display->'target'<>jsonb_build_array(org,proj,a.application_id,a.environment_id,a.platform,a.runtime_sha256,a.manifest_sha256,a.payload_sha256)
        OR e.display->'actor'->>0<>d.principal_id OR e.display->'actor'->>1<>'human'
        OR d.action<>'artifact.upload' OR d.application_id<>a.application_id OR d.environment_id<>a.environment_id OR d.manifest_sha256<>a.manifest_sha256 OR d.payload_sha256<>a.payload_sha256
        OR d.request_sha256<>e.display->>'request_sha256'
        OR d.request_sha256<>public.mixer_customer_hash('mixer.hosted.customer.upload.request.v2',jsonb_build_array(2,'artifact.upload',e.display->'target',e.display->'envelope_sha256',e.display->'reason'))
        THEN RAISE EXCEPTION 'inconsistent customer event'; END IF;
      IF n=1 THEN expected_state:=public.mixer_customer_hash('mixer.hosted.customer.state.v2',jsonb_build_array(2,org,proj)); expected:='';
      ELSE SELECT * INTO STRICT prev FROM public.mixer_customer_audit_events x WHERE x.organization_id=org AND x.project_id=proj AND x.sequence=n-1; expected_state:=prev.current_state_sha256; expected:=prev.event_sha256; END IF;
      IF e.previous_state_sha256<>expected_state OR e.previous_event_sha256<>expected THEN RAISE EXCEPTION 'broken chain'; END IF;
      IF e.display->>'outcome'='created' THEN
        expected_state:=public.mixer_customer_hash('mixer.hosted.customer.state.v2',jsonb_build_array(2,org,proj,expected_state,n,a.manifest_sha256,e.display->>'envelope_sha256',a.payload_sha256));
        IF a.creating_sequence<>n OR d.status<>201 OR e.display->>'envelope_sha256'<>a.envelope_sha256 THEN RAISE EXCEPTION 'invalid created'; END IF;
      ELSE IF a.creating_sequence>=n OR d.status<>200 THEN RAISE EXCEPTION 'invalid unchanged'; END IF; END IF;
      IF expected_state<>e.current_state_sha256 THEN RAISE EXCEPTION 'invalid state'; END IF;
      IF h.sequence=n AND (h.event_sha256<>e.event_sha256 OR h.state_sha256<>e.current_state_sha256) THEN RAISE EXCEPTION 'invalid head edge'; END IF;
      IF EXISTS (SELECT 1 FROM public.mixer_customer_audit_events x WHERE x.organization_id=org AND x.project_id=proj AND x.sequence>h.sequence) THEN RAISE EXCEPTION 'event beyond head'; END IF;
      IF TG_TABLE_NAME='mixer_customer_artifact_heads' AND (NEW.event_sha256<>e.event_sha256 OR NEW.state_sha256<>e.current_state_sha256 OR OLD.event_sha256<>e.previous_event_sha256 OR OLD.state_sha256<>e.previous_state_sha256) THEN RAISE EXCEPTION 'head transition mismatch'; END IF;
      envelope:=convert_from(a.envelope_bytes,'UTF8')::json; document:=convert_from(a.signed_manifest_bytes,'UTF8')::jsonb;
      IF (SELECT count(*) FROM json_object_keys(envelope))<>2 OR NOT envelope::jsonb ?& ARRAY['signed_manifest','payload']
        OR convert_to((envelope->'signed_manifest')::text,'UTF8')<>a.signed_manifest_bytes
        OR (SELECT count(*) FROM jsonb_object_keys(document))<>2 OR NOT document ?& ARRAY['manifest','signature']
        OR decode(document->>'signature','base64')<>a.signature OR replace(encode(a.signature,'base64'),chr(10),'')<>document->>'signature'
        OR decode(envelope->>'payload','base64')<>a.payload OR replace(encode(a.payload,'base64'),chr(10),'')<>envelope->>'payload'
        OR public.mixer_customer_cbor(document->'manifest')<>a.canonical_manifest_cbor
        OR encode(sha256(a.canonical_manifest_cbor),'hex')<>a.manifest_sha256 OR encode(sha256(a.payload),'hex')<>a.payload_sha256 OR encode(sha256(a.envelope_bytes),'hex')<>a.envelope_sha256
        OR document->'manifest'->'scope'<>jsonb_build_object('organization',org,'project',proj,'app',a.application_id,'environment',a.environment_id,'platform',a.platform)
        OR document->'manifest'->>'runtime'<>a.runtime_sha256 OR document->'manifest'->>'payload_sha256'<>a.payload_sha256
        OR document->'manifest'->'compressed_bytes'<>to_jsonb(octet_length(a.payload))
        THEN RAISE EXCEPTION 'inconsistent retained artifact'; END IF;
      RETURN NULL;
    END
    """
  end
end
