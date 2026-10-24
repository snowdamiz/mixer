-- SYNTHETIC PREIMPLEMENTATION ONLY. Not a product migration or full authz schema.
BEGIN;
CREATE ROLE mxas_schema NOLOGIN NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE NOREPLICATION;
CREATE ROLE mxas_resolver NOLOGIN NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE NOREPLICATION;
CREATE ROLE mxas_writer NOLOGIN NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE NOREPLICATION;
CREATE ROLE mxas_runtime LOGIN NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE NOREPLICATION;
CREATE ROLE mxas_foreign LOGIN NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE NOREPLICATION;
REVOKE ALL ON DATABASE atomic_preflight FROM PUBLIC;
GRANT CONNECT ON DATABASE atomic_preflight TO mxas_runtime, mxas_foreign;
REVOKE ALL ON SCHEMA public FROM PUBLIC;
CREATE SCHEMA mixer_authz AUTHORIZATION mxas_schema;
CREATE SCHEMA mixer_hosted_release AUTHORIZATION mxas_schema;
REVOKE ALL ON SCHEMA mixer_authz,mixer_hosted_release FROM PUBLIC;
GRANT USAGE ON SCHEMA mixer_authz,mixer_hosted_release TO mxas_resolver,mxas_writer,mxas_runtime,mxas_foreign;
SET ROLE mxas_schema;
ALTER DEFAULT PRIVILEGES REVOKE EXECUTE ON FUNCTIONS FROM PUBLIC;
CREATE TABLE mixer_authz.fixture_policy(actor uuid PRIMARY KEY, role text NOT NULL, active boolean NOT NULL DEFAULT true, revision bigint NOT NULL DEFAULT 1 CHECK(revision>0));
CREATE TABLE mixer_authz.fixture_clock(id int PRIMARY KEY CHECK(id=1), now_s numeric(20,0) NOT NULL);
CREATE TABLE mixer_authz.fixture_fault(id int PRIMARY KEY CHECK(id=1), boundary text NOT NULL);
INSERT INTO mixer_authz.fixture_policy VALUES('00000000-0000-0000-0000-000000000001','developer',true,1),('00000000-0000-0000-0000-000000000002','developer',true,1);
INSERT INTO mixer_authz.fixture_clock VALUES(1,100);
INSERT INTO mixer_authz.fixture_fault VALUES(1,'');
CREATE TYPE mixer_hosted_release.call_context AS (backend int, full_xid text, database_name name, runtime_role name, nonce text, deadline timestamptz, actor uuid, expires_at numeric, authentication_completed_at numeric);
CREATE TYPE mixer_hosted_release.upload_input AS (organization text, project text, app text, environment text, platform text, runtime bytea, manifest bytea, canonical_manifest bytea, signed_document bytea, signature bytea, payload_hash bytea, payload_size numeric, blob_ref text);
CREATE TYPE mixer_hosted_release.upload_request AS (key text, path text, body bytea, request_hash bytea, reason text, request_id uuid, source_ip text, asserted_display jsonb);
CREATE TYPE mixer_hosted_release.upload_result AS (status int, body bytea, event_id numeric, replay boolean);
CREATE TABLE mixer_hosted_release.tenant_heads(organization text,project text,last_event numeric(20,0) NOT NULL DEFAULT 0 CHECK(last_event BETWEEN 0 AND 18446744073709551615),audit_hash bytea NOT NULL DEFAULT ''::bytea,state_hash bytea NOT NULL,PRIMARY KEY(organization,project));
CREATE TABLE mixer_hosted_release.artifacts(organization text,project text,manifest bytea,app text,environment text,platform text,runtime bytea,canonical_manifest bytea,signed_document bytea,signature bytea,payload_hash bytea,payload_size numeric,blob_ref text,created_event numeric NOT NULL,created_actor uuid NOT NULL,PRIMARY KEY(organization,project,manifest));
CREATE TABLE mixer_hosted_release.audit_events(organization text,project text,event_id numeric,event_cbor bytea,event_hash bytea,previous_hash bytea,previous_state bytea,current_state bytea,display_json jsonb,display_bytes bytea,PRIMARY KEY(organization,project,event_id));
CREATE TABLE mixer_hosted_release.idempotency(organization text,project text,key text,actor uuid,action text,target bytea,request_hash bytea,status int,response bytea,event_id numeric,PRIMARY KEY(organization,project,key),FOREIGN KEY(organization,project,event_id) REFERENCES mixer_hosted_release.audit_events);
ALTER TABLE mixer_hosted_release.artifacts ADD CONSTRAINT artifact_creation_event FOREIGN KEY(organization,project,created_event) REFERENCES mixer_hosted_release.audit_events(organization,project,event_id) DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE mixer_hosted_release.artifacts ADD CONSTRAINT artifact_created_event_uint CHECK(created_event>=1 AND created_event<=18446744073709551615 AND trunc(created_event)=created_event);
ALTER TABLE mixer_hosted_release.artifacts ALTER COLUMN organization SET NOT NULL;
ALTER TABLE mixer_hosted_release.artifacts ALTER COLUMN project SET NOT NULL;
ALTER TABLE mixer_hosted_release.artifacts ALTER COLUMN manifest SET NOT NULL;
ALTER TABLE mixer_hosted_release.artifacts ALTER COLUMN app SET NOT NULL;
ALTER TABLE mixer_hosted_release.artifacts ALTER COLUMN environment SET NOT NULL;
ALTER TABLE mixer_hosted_release.artifacts ALTER COLUMN platform SET NOT NULL;
ALTER TABLE mixer_hosted_release.artifacts ALTER COLUMN runtime SET NOT NULL;
ALTER TABLE mixer_hosted_release.artifacts ALTER COLUMN canonical_manifest SET NOT NULL;
ALTER TABLE mixer_hosted_release.artifacts ALTER COLUMN signed_document SET NOT NULL;
ALTER TABLE mixer_hosted_release.artifacts ALTER COLUMN signature SET NOT NULL;
ALTER TABLE mixer_hosted_release.artifacts ALTER COLUMN payload_hash SET NOT NULL;
ALTER TABLE mixer_hosted_release.artifacts ALTER COLUMN payload_size SET NOT NULL;
ALTER TABLE mixer_hosted_release.artifacts ALTER COLUMN blob_ref SET NOT NULL;
ALTER TABLE mixer_hosted_release.audit_events ALTER COLUMN organization SET NOT NULL;
ALTER TABLE mixer_hosted_release.audit_events ALTER COLUMN project SET NOT NULL;
ALTER TABLE mixer_hosted_release.audit_events ALTER COLUMN event_id SET NOT NULL;
ALTER TABLE mixer_hosted_release.audit_events ALTER COLUMN event_cbor SET NOT NULL;
ALTER TABLE mixer_hosted_release.audit_events ALTER COLUMN event_hash SET NOT NULL;
ALTER TABLE mixer_hosted_release.audit_events ALTER COLUMN previous_hash SET NOT NULL;
ALTER TABLE mixer_hosted_release.audit_events ALTER COLUMN previous_state SET NOT NULL;
ALTER TABLE mixer_hosted_release.audit_events ALTER COLUMN current_state SET NOT NULL;
ALTER TABLE mixer_hosted_release.audit_events ALTER COLUMN display_json SET NOT NULL;
ALTER TABLE mixer_hosted_release.audit_events ALTER COLUMN display_bytes SET NOT NULL;
ALTER TABLE mixer_hosted_release.idempotency ALTER COLUMN organization SET NOT NULL;
ALTER TABLE mixer_hosted_release.idempotency ALTER COLUMN project SET NOT NULL;
ALTER TABLE mixer_hosted_release.idempotency ALTER COLUMN key SET NOT NULL;
ALTER TABLE mixer_hosted_release.idempotency ALTER COLUMN actor SET NOT NULL;
ALTER TABLE mixer_hosted_release.idempotency ALTER COLUMN action SET NOT NULL;
ALTER TABLE mixer_hosted_release.idempotency ALTER COLUMN target SET NOT NULL;
ALTER TABLE mixer_hosted_release.idempotency ALTER COLUMN request_hash SET NOT NULL;
ALTER TABLE mixer_hosted_release.idempotency ALTER COLUMN status SET NOT NULL;
ALTER TABLE mixer_hosted_release.idempotency ALTER COLUMN response SET NOT NULL;
ALTER TABLE mixer_hosted_release.idempotency ALTER COLUMN event_id SET NOT NULL;
ALTER TABLE mixer_hosted_release.audit_events ADD CONSTRAINT event_id_uint CHECK(event_id>=1 AND event_id<=18446744073709551615 AND trunc(event_id)=event_id);
CREATE FUNCTION mixer_hosted_release.u(n numeric) RETURNS bytea LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog AS $$
DECLARE width int; h int; x numeric; result bytea; i int;
BEGIN
 IF n IS NULL OR NOT (n>=0 AND n<=18446744073709551615) OR trunc(n)<>n THEN RAISE EXCEPTION 'uint64'; END IF;
 IF n<24 THEN RETURN set_byte(decode('00','hex'),0,n::int); END IF;
 IF n<=255 THEN width:=1;h:=24; ELSIF n<=65535 THEN width:=2;h:=25;ELSIF n<=4294967295 THEN width:=4;h:=26;ELSE width:=8;h:=27;END IF;
 result:=''::bytea;x:=n;
 FOR i IN 1..width LOOP result:=set_byte(decode('00','hex'),0,mod(x,256)::int)||result;x:=div(x,256);END LOOP;
 RETURN set_byte(decode('00','hex'),0,h)||result;
END $$;
CREATE FUNCTION mixer_hosted_release.b(v bytea) RETURNS bytea LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog AS $$
DECLARE h bytea;
BEGIN IF v IS NULL THEN RETURN decode('f6','hex');END IF;h:=mixer_hosted_release.u(octet_length(v));RETURN set_byte(h,0,get_byte(h,0)+64)||v;END $$;
CREATE FUNCTION mixer_hosted_release.t(v text) RETURNS bytea LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog AS $$
DECLARE vbytes bytea;h bytea;
BEGIN IF v IS NULL THEN RETURN decode('f6','hex');END IF;vbytes:=convert_to(v,'UTF8');h:=mixer_hosted_release.u(octet_length(vbytes));RETURN set_byte(h,0,get_byte(h,0)+96)||vbytes;END $$;
CREATE FUNCTION mixer_hosted_release.a(parts bytea[]) RETURNS bytea LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog AS $$
DECLARE h bytea; result bytea;part bytea;
BEGIN h:=mixer_hosted_release.u(cardinality(parts));result:=set_byte(h,0,get_byte(h,0)+128);FOREACH part IN ARRAY parts LOOP IF part IS NULL THEN RAISE EXCEPTION 'implicit null';END IF;result:=result||part;END LOOP;RETURN result;END $$;
CREATE FUNCTION mixer_hosted_release.hash_domain(domain_name text, encoded bytea) RETURNS bytea LANGUAGE sql IMMUTABLE SET search_path=pg_catalog AS $$ SELECT sha256(convert_to(domain_name,'UTF8')||decode('00','hex')||encoded) $$;
CREATE FUNCTION mixer_hosted_release.target(i mixer_hosted_release.upload_input) RETURNS bytea LANGUAGE sql IMMUTABLE SET search_path=pg_catalog AS $$ SELECT mixer_hosted_release.a(ARRAY[mixer_hosted_release.t(i.organization),mixer_hosted_release.t(i.project),mixer_hosted_release.t(i.app),mixer_hosted_release.t(i.environment),mixer_hosted_release.t(i.platform),mixer_hosted_release.b(i.runtime),mixer_hosted_release.b(i.manifest)]) $$;
CREATE FUNCTION mixer_hosted_release.hx(v text) RETURNS bytea LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog AS $$
DECLARE b bytea; BEGIN IF v IS NULL THEN RETURN NULL;END IF;b:=decode(v,'hex');IF encode(b,'hex')<>v THEN RAISE EXCEPTION 'hex';END IF;RETURN b;END $$;
CREATE FUNCTION mixer_hosted_release.event_from_display(d jsonb) RETURNS bytea LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog AS $$
DECLARE actor jsonb:=d->'actor';decision jsonb:=d->'decision';target jsonb:=d->'target';members bytea[]:=ARRAY[]::bytea[];m jsonb; a bytea; de bytea;ta bytea;
BEGIN
 IF (SELECT count(*) FROM jsonb_object_keys(d))<>16 THEN RAISE EXCEPTION 'display keys';END IF;
 FOR m IN SELECT value FROM jsonb_array_elements(decision->6) LOOP
 members:=array_append(members,mixer_hosted_release.a(ARRAY[mixer_hosted_release.b(uuid_send((m->>0)::uuid)),mixer_hosted_release.t(m->>1),mixer_hosted_release.u((m->>2)::numeric)]));END LOOP;
 a:=mixer_hosted_release.a(ARRAY[mixer_hosted_release.b(uuid_send((actor->>0)::uuid)),mixer_hosted_release.t(actor->>1),mixer_hosted_release.b(uuid_send((actor->>2)::uuid)),mixer_hosted_release.t(actor->>3),mixer_hosted_release.u((actor->>4)::numeric),mixer_hosted_release.b(mixer_hosted_release.hx(actor->>5)),mixer_hosted_release.b(mixer_hosted_release.hx(actor->>6)),mixer_hosted_release.b(mixer_hosted_release.hx(actor->>7)),mixer_hosted_release.b(mixer_hosted_release.hx(actor->>8)),mixer_hosted_release.b(uuid_send((actor->>9)::uuid)),mixer_hosted_release.u((actor->>10)::numeric)]);
 de:=mixer_hosted_release.a(ARRAY[mixer_hosted_release.u((decision->>0)::numeric),mixer_hosted_release.u((decision->>1)::numeric),mixer_hosted_release.u((decision->>2)::numeric),mixer_hosted_release.u((decision->>3)::numeric),mixer_hosted_release.u((decision->>4)::numeric),mixer_hosted_release.u((decision->>5)::numeric),mixer_hosted_release.a(members)]);
 ta:=mixer_hosted_release.a(ARRAY[mixer_hosted_release.t(target->>0),mixer_hosted_release.t(target->>1),mixer_hosted_release.t(target->>2),mixer_hosted_release.t(target->>3),mixer_hosted_release.t(target->>4),mixer_hosted_release.b(mixer_hosted_release.hx(target->>5)),mixer_hosted_release.b(mixer_hosted_release.hx(target->>6))]);
 RETURN mixer_hosted_release.a(ARRAY[mixer_hosted_release.u((d->>'audit_schema')::numeric),mixer_hosted_release.u((d->>'id')::numeric),mixer_hosted_release.a(ARRAY[mixer_hosted_release.t(d->'tenant'->>0),mixer_hosted_release.t(d->'tenant'->>1)]),a,de,ta,mixer_hosted_release.t(d->>'action'),mixer_hosted_release.t(d->>'reason'),mixer_hosted_release.b(uuid_send((d->>'request_id')::uuid)),mixer_hosted_release.t(d->>'source_ip'),mixer_hosted_release.u((d->>'recorded_at')::numeric),mixer_hosted_release.b(mixer_hosted_release.hx(d->>'previous_state')),mixer_hosted_release.b(mixer_hosted_release.hx(d->>'current_state')),mixer_hosted_release.b(mixer_hosted_release.hx(d->>'previous_hash')),mixer_hosted_release.b(mixer_hosted_release.hx(d->>'request_hash'))]);
END $$;
-- Private PURE validators. Only the fixed upload definer reads retained rows.
CREATE FUNCTION mixer_hosted_release.finite_uint(v numeric,lo numeric,hi numeric) RETURNS boolean LANGUAGE sql IMMUTABLE SET search_path=pg_catalog AS $$ SELECT coalesce(v>=lo AND v<=hi AND trunc(v)=v,false) $$;
CREATE FUNCTION mixer_hosted_release.jtext(v jsonb,lo int,hi int) RETURNS text LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog AS $$
DECLARE s text; BEGIN IF jsonb_typeof(v) IS DISTINCT FROM 'string' THEN RAISE EXCEPTION 'display text type';END IF;s:=v#>>'{}';IF octet_length(s) NOT BETWEEN lo AND hi THEN RAISE EXCEPTION 'display text bound';END IF;RETURN s;END $$;
CREATE FUNCTION mixer_hosted_release.juint(v jsonb,lo numeric,hi numeric) RETURNS numeric LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog AS $$
DECLARE s text;BEGIN s:=mixer_hosted_release.jtext(v,1,20);IF s!~'^(0|[1-9][0-9]*)$' OR NOT mixer_hosted_release.finite_uint(s::numeric,lo,hi) THEN RAISE EXCEPTION 'display integer';END IF;RETURN s::numeric;END $$;
CREATE FUNCTION mixer_hosted_release.juuid(v jsonb) RETURNS bytea LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog AS $$
DECLARE s text;BEGIN s:=mixer_hosted_release.jtext(v,36,36);IF s!~'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$' OR (s::uuid)::text<>s THEN RAISE EXCEPTION 'display uuid';END IF;RETURN uuid_send(s::uuid);END $$;
CREATE FUNCTION mixer_hosted_release.jhex(v jsonb,lo int,hi int) RETURNS bytea LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog AS $$
DECLARE s text;b bytea;BEGIN s:=mixer_hosted_release.jtext(v,lo*2,hi*2);IF s!~'^[0-9a-f]*$' OR length(s)%2<>0 THEN RAISE EXCEPTION 'display hex';END IF;b:=decode(s,'hex');IF octet_length(b) NOT BETWEEN lo AND hi THEN RAISE EXCEPTION 'display hex bound';END IF;RETURN b;END $$;
CREATE FUNCTION mixer_hosted_release.jid(v jsonb) RETURNS text LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog AS $$
DECLARE s text;BEGIN s:=mixer_hosted_release.jtext(v,1,128);IF s!~'^[A-Za-z0-9_.-]+$' THEN RAISE EXCEPTION 'display id';END IF;RETURN s;END $$;
CREATE FUNCTION mixer_hosted_release.jarray(v jsonb,n int) RETURNS jsonb LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog AS $$
BEGIN IF jsonb_typeof(v) IS DISTINCT FROM 'array' OR jsonb_array_length(v)<>n THEN RAISE EXCEPTION 'display array';END IF;RETURN v;END $$;
CREATE FUNCTION mixer_hosted_release.jip(v jsonb) RETURNS text LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog AS $$
DECLARE s text;BEGIN IF v='null'::jsonb THEN RETURN NULL;END IF;s:=mixer_hosted_release.jtext(v,1,45);IF host(s::inet)<>s THEN RAISE EXCEPTION 'display ip';END IF;RETURN s;END $$;
CREATE OR REPLACE FUNCTION mixer_hosted_release.event_from_display(d jsonb) RETURNS bytea LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog AS $$
DECLARE actor jsonb;decision jsonb;tar jsonb;tenant jsonb;members bytea[]:=ARRAY[]::bytea[];m jsonb;mb bytea;last_mb bytea;role text;upload_role boolean:=false;ac bytea;de bytea;ta bytea;body bytea;eid numeric;auth numeric;at_s numeric;recorded numeric;prev bytea;keys text[]:=ARRAY['audit_schema','id','tenant','actor','decision','target','action','reason','request_id','source_ip','recorded_at','previous_state','current_state','previous_hash','request_hash','hash'];
BEGIN
 IF jsonb_typeof(d) IS DISTINCT FROM 'object' OR octet_length(convert_to(d::text,'UTF8'))>32768 OR NOT d ?& keys OR (SELECT count(*) FROM jsonb_object_keys(d))<>16 THEN RAISE EXCEPTION 'display keys/budget';END IF;
 IF jsonb_typeof(d->'audit_schema') IS DISTINCT FROM 'number' OR d->>'audit_schema' IS DISTINCT FROM '1' OR mixer_hosted_release.jtext(d->'action',15,15)<>'artifact.upload' THEN RAISE EXCEPTION 'display schema/action';END IF;
 actor:=mixer_hosted_release.jarray(d->'actor',11);decision:=mixer_hosted_release.jarray(d->'decision',7);tar:=mixer_hosted_release.jarray(d->'target',7);tenant:=mixer_hosted_release.jarray(d->'tenant',2);
 PERFORM mixer_hosted_release.jid(tenant->0),mixer_hosted_release.jid(tenant->1);
 IF tar->0 IS DISTINCT FROM tenant->0 OR tar->1 IS DISTINCT FROM tenant->1 THEN RAISE EXCEPTION 'display target tenant';END IF;
 eid:=mixer_hosted_release.juint(d->'id',1,18446744073709551615);auth:=mixer_hosted_release.juint(actor->10,0,9007199254740991);at_s:=mixer_hosted_release.juint(decision->0,0,9007199254740991);recorded:=mixer_hosted_release.juint(d->'recorded_at',0,9007199254740991);
 IF auth<at_s-45 OR auth>at_s+30 OR recorded<at_s THEN RAISE EXCEPTION 'display time relationship';END IF;
 IF mixer_hosted_release.jtext(actor->1,5,5)<>'human' THEN RAISE EXCEPTION 'display identity class';END IF;
 IF jsonb_typeof(decision->6) IS DISTINCT FROM 'array' OR jsonb_array_length(decision->6) NOT BETWEEN 1 AND 64 THEN RAISE EXCEPTION 'display members bound';END IF;
 FOR m IN SELECT value FROM jsonb_array_elements(decision->6) LOOP
  m:=mixer_hosted_release.jarray(m,3);mb:=mixer_hosted_release.juuid(m->0);role:=mixer_hosted_release.jtext(m->1,1,20);
  IF (last_mb IS NOT NULL AND mb<=last_mb) OR role NOT IN ('owner','administrator','developer','release_manager','billing_manager','viewer') THEN RAISE EXCEPTION 'display members order/role';END IF;
  upload_role:=upload_role OR role IN ('owner','administrator','developer');last_mb:=mb;
  members:=array_append(members,mixer_hosted_release.a(ARRAY[mixer_hosted_release.b(mb),mixer_hosted_release.t(role),mixer_hosted_release.u(mixer_hosted_release.juint(m->2,1,9223372036854775807))]));
 END LOOP;
 IF NOT upload_role THEN RAISE EXCEPTION 'display upload ceiling';END IF;
 ac:=mixer_hosted_release.a(ARRAY[mixer_hosted_release.b(mixer_hosted_release.juuid(actor->0)),mixer_hosted_release.t('human'),mixer_hosted_release.b(mixer_hosted_release.juuid(actor->2)),mixer_hosted_release.t(mixer_hosted_release.jtext(actor->3,1,128)),mixer_hosted_release.u(mixer_hosted_release.juint(actor->4,1,2147483647)),mixer_hosted_release.b(mixer_hosted_release.jhex(actor->5,32,32)),mixer_hosted_release.b(mixer_hosted_release.jhex(actor->6,32,32)),mixer_hosted_release.b(mixer_hosted_release.jhex(actor->7,32,32)),mixer_hosted_release.b(mixer_hosted_release.jhex(actor->8,32,32)),mixer_hosted_release.b(mixer_hosted_release.juuid(actor->9)),mixer_hosted_release.u(auth)]);
 de:=mixer_hosted_release.a(ARRAY[mixer_hosted_release.u(at_s),mixer_hosted_release.u(mixer_hosted_release.juint(decision->1,1,9223372036854775807)),mixer_hosted_release.u(mixer_hosted_release.juint(decision->2,1,9223372036854775807)),mixer_hosted_release.u(mixer_hosted_release.juint(decision->3,1,9223372036854775807)),mixer_hosted_release.u(mixer_hosted_release.juint(decision->4,1,9223372036854775807)),mixer_hosted_release.u(mixer_hosted_release.juint(decision->5,1,9223372036854775807)),mixer_hosted_release.a(members)]);
 IF mixer_hosted_release.jtext(tar->4,3,7) NOT IN ('ios','android') THEN RAISE EXCEPTION 'display platform';END IF;
 ta:=mixer_hosted_release.a(ARRAY[mixer_hosted_release.t(mixer_hosted_release.jid(tar->0)),mixer_hosted_release.t(mixer_hosted_release.jid(tar->1)),mixer_hosted_release.t(mixer_hosted_release.jid(tar->2)),mixer_hosted_release.t(mixer_hosted_release.jid(tar->3)),mixer_hosted_release.t(tar->>4),mixer_hosted_release.b(mixer_hosted_release.jhex(tar->5,32,32)),mixer_hosted_release.b(mixer_hosted_release.jhex(tar->6,32,32))]);
 prev:=mixer_hosted_release.jhex(d->'previous_hash',0,32);
 IF (eid=1 AND octet_length(prev)<>0) OR (eid>1 AND octet_length(prev)<>32) THEN RAISE EXCEPTION 'display previous hash';END IF;
 PERFORM mixer_hosted_release.jhex(d->'hash',32,32);
 body:=mixer_hosted_release.a(ARRAY[mixer_hosted_release.u(1),mixer_hosted_release.u(eid),mixer_hosted_release.a(ARRAY[mixer_hosted_release.t(tenant->>0),mixer_hosted_release.t(tenant->>1)]),ac,de,ta,mixer_hosted_release.t('artifact.upload'),mixer_hosted_release.t(mixer_hosted_release.jtext(d->'reason',0,512)),mixer_hosted_release.b(mixer_hosted_release.juuid(d->'request_id')),mixer_hosted_release.t(mixer_hosted_release.jip(d->'source_ip')),mixer_hosted_release.u(recorded),mixer_hosted_release.b(mixer_hosted_release.jhex(d->'previous_state',32,32)),mixer_hosted_release.b(mixer_hosted_release.jhex(d->'current_state',32,32)),mixer_hosted_release.b(prev),mixer_hosted_release.b(mixer_hosted_release.jhex(d->'request_hash',32,32))]);
 IF octet_length(body)>16384 THEN RAISE EXCEPTION 'display cbor bound';END IF;
 RETURN body;
END $$;
CREATE FUNCTION mixer_hosted_release.row_valid(e mixer_hosted_release.audit_events) RETURNS boolean LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog AS $$
DECLARE encoded bytea;initial bytea;BEGIN
 encoded:=mixer_hosted_release.event_from_display(e.display_json);
 IF NOT mixer_hosted_release.finite_uint(e.event_id,1,18446744073709551615) OR e.organization IS NULL OR e.project IS NULL OR e.display_json->'tenant' IS DISTINCT FROM jsonb_build_array(e.organization,e.project) OR e.display_json->>'id' IS DISTINCT FROM e.event_id::text OR e.event_cbor IS DISTINCT FROM encoded OR e.event_hash IS DISTINCT FROM mixer_hosted_release.hash_domain('mixer.hosted.audit.v1',encoded) OR e.display_json->>'hash' IS DISTINCT FROM encode(e.event_hash,'hex') OR e.previous_hash IS DISTINCT FROM mixer_hosted_release.jhex(e.display_json->'previous_hash',0,32) OR e.previous_state IS DISTINCT FROM mixer_hosted_release.jhex(e.display_json->'previous_state',32,32) OR e.current_state IS DISTINCT FROM mixer_hosted_release.jhex(e.display_json->'current_state',32,32) OR e.display_bytes IS DISTINCT FROM convert_to(e.display_json::text,'UTF8') OR octet_length(e.display_bytes)>32768 THEN RAISE EXCEPTION 'event row corrupt';END IF;
 IF e.event_id=1 THEN
  initial:=mixer_hosted_release.hash_domain('mixer.hosted.state.v1',mixer_hosted_release.a(ARRAY[mixer_hosted_release.u(1),mixer_hosted_release.t(e.organization),mixer_hosted_release.t(e.project)]));
  IF e.previous_hash<>''::bytea OR e.previous_state<>initial THEN RAISE EXCEPTION 'first event edge';END IF;
 END IF;RETURN true;END $$;
CREATE FUNCTION mixer_hosted_release.changed_state(previous bytea,i mixer_hosted_release.upload_input) RETURNS bytea LANGUAGE sql IMMUTABLE SET search_path=pg_catalog AS $$ SELECT mixer_hosted_release.hash_domain('mixer.hosted.state.v1',mixer_hosted_release.a(ARRAY[mixer_hosted_release.u(1),mixer_hosted_release.b(previous),mixer_hosted_release.a(ARRAY[mixer_hosted_release.a(ARRAY[mixer_hosted_release.u(1),mixer_hosted_release.b(i.manifest),mixer_hosted_release.b(i.payload_hash),mixer_hosted_release.u(i.payload_size),mixer_hosted_release.t(i.blob_ref),mixer_hosted_release.target(i),mixer_hosted_release.b(sha256(i.signed_document)),mixer_hosted_release.b(i.signature)])])])) $$;
CREATE FUNCTION mixer_hosted_release.time_valid(c mixer_hosted_release.call_context,now_s numeric,wall_now timestamptz) RETURNS boolean LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog AS $$
BEGIN IF NOT mixer_hosted_release.finite_uint(now_s,0,9007199254740991) OR c.authentication_completed_at>=c.expires_at OR now_s>=c.expires_at OR c.authentication_completed_at<now_s-45 OR c.authentication_completed_at>now_s+30 OR c.deadline IS NULL OR c.deadline<=wall_now THEN RAISE EXCEPTION 'expired' USING ERRCODE='42501';END IF;RETURN true;END $$;

-- Dedicated nonrecursive resolver reads only synthetic fixture policy. No domain query.
CREATE FUNCTION mixer_authz.allowed(o text,p text) RETURNS boolean LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog SET row_security=on AS $$
DECLARE ok boolean;
BEGIN
 IF current_user<>'mxas_resolver' OR session_user<>'mxas_runtime' OR current_setting('role')<>'none' OR o IS DISTINCT FROM 'o' OR p IS DISTINCT FROM 'p' OR nullif(current_setting('mixer_atomic.invocation_nonce',true),'') IS NULL OR current_setting('mixer_atomic.action',true) NOT IN ('artifact.upload','artifact.read','audit.read') THEN RETURN false;END IF;
 SELECT f.active AND f.role IN ('owner','administrator','developer','release_manager','viewer') AND (current_setting('mixer_atomic.action',true)<>'artifact.upload' OR f.role IN ('owner','administrator','developer')) INTO ok FROM mixer_authz.fixture_policy f WHERE f.actor::text=current_setting('mixer_atomic.actor',true);
 RETURN coalesce(ok,false);
END $$;
CREATE FUNCTION mixer_authz.evidence(actor_id uuid) RETURNS TABLE(role text,revision bigint,now_s numeric) LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog SET row_security=on AS $$
BEGIN
 IF current_user<>'mxas_resolver' OR actor_id::text IS DISTINCT FROM current_setting('mixer_atomic.actor',true) OR NOT mixer_authz.allowed('o','p') THEN RAISE EXCEPTION 'policy denied' USING ERRCODE='42501';END IF;
 RETURN QUERY SELECT f.role,f.revision,c.now_s FROM mixer_authz.fixture_policy f CROSS JOIN mixer_authz.fixture_clock c WHERE f.actor=actor_id AND c.id=1;
 IF NOT FOUND THEN RAISE EXCEPTION 'missing policy';END IF;
END $$;
RESET ROLE;
ALTER FUNCTION mixer_authz.allowed(text,text) OWNER TO mxas_resolver;
ALTER FUNCTION mixer_authz.evidence(uuid) OWNER TO mxas_resolver;
GRANT SELECT ON mixer_authz.fixture_policy,mixer_authz.fixture_clock TO mxas_resolver;
GRANT EXECUTE ON FUNCTION mixer_authz.allowed(text,text) TO mxas_runtime,mxas_writer,mxas_resolver;
GRANT EXECUTE ON FUNCTION mixer_authz.evidence(uuid) TO mxas_writer;
SET ROLE mxas_schema;
CREATE FUNCTION mixer_hosted_release.upload_v1(c mixer_hosted_release.call_context,i mixer_hosted_release.upload_input,r mixer_hosted_release.upload_request) RETURNS mixer_hosted_release.upload_result LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog SET row_security=on AS $$
DECLARE h mixer_hosted_release.tenant_heads%ROWTYPE;d mixer_hosted_release.idempotency%ROWTYPE;old mixer_hosted_release.artifacts%ROWTYPE;prior mixer_hosted_release.audit_events%ROWTYPE;edge mixer_hosted_release.audit_events%ROWTYPE;cached mixer_hosted_release.audit_events%ROWTYPE;creation mixer_hosted_release.audit_events%ROWTYPE;checked_ids numeric[]:=ARRAY[]::numeric[];ev record;target_bytes bytea;event_bytes bytea;state_bytes bytea;state_next bytea;event_hash bytea;event_id numeric;result_body bytea;status int;display jsonb;actual_change boolean;fault text;actor_bytes bytea;decision_bytes bytea;target_display jsonb;zero bytea:=decode(repeat('00',32),'hex');
BEGIN
 IF NOT mixer_hosted_release.finite_uint(c.expires_at,0,9007199254740991) OR NOT mixer_hosted_release.finite_uint(c.authentication_completed_at,0,9007199254740991) OR c.expires_at::text IS DISTINCT FROM current_setting('mixer_atomic.expires',true) OR c.authentication_completed_at::text IS DISTINCT FROM current_setting('mixer_atomic.authentication_completed_at',true) THEN RAISE EXCEPTION 'identity integer/binding' USING ERRCODE='42501';END IF;
 -- current_user intentionally changed by SECURITY DEFINER; never compare it with captured runtime.
 IF current_user<>'mxas_writer' OR session_user<>'mxas_runtime' OR current_setting('role')<>'none' OR c.runtime_role IS DISTINCT FROM 'mxas_runtime'::name OR c.backend IS DISTINCT FROM pg_backend_pid() OR c.full_xid IS DISTINCT FROM pg_current_xact_id()::text OR c.database_name IS DISTINCT FROM current_database() OR c.nonce IS NULL OR c.nonce!~'^[0-9a-f]{64}$' OR c.nonce IS DISTINCT FROM current_setting('mixer_atomic.invocation_nonce',true) OR c.deadline IS NULL OR c.deadline<=clock_timestamp() OR c.deadline>clock_timestamp()+interval '5 seconds' OR c.actor::text IS DISTINCT FROM current_setting('mixer_atomic.actor',true) OR current_setting('mixer_atomic.action',true) IS DISTINCT FROM 'artifact.upload' THEN RAISE EXCEPTION 'context rejected' USING ERRCODE='42501';END IF;
 IF i.organization IS DISTINCT FROM 'o' OR i.project IS DISTINCT FROM 'p' OR i.app IS DISTINCT FROM 'a' OR i.environment IS DISTINCT FROM 'e' OR i.platform IS DISTINCT FROM 'ios' OR i.app IS DISTINCT FROM current_setting('mixer_atomic.app',true) OR i.environment IS DISTINCT FROM current_setting('mixer_atomic.environment',true) OR i.platform IS DISTINCT FROM current_setting('mixer_atomic.platform',true) OR encode(i.runtime,'hex') IS DISTINCT FROM current_setting('mixer_atomic.runtime',true) OR encode(i.manifest,'hex') IS DISTINCT FROM current_setting('mixer_atomic.manifest',true) THEN RAISE EXCEPTION 'target rejected' USING ERRCODE='42501';END IF;
 IF octet_length(i.runtime) IS DISTINCT FROM 32 OR octet_length(i.manifest) IS DISTINCT FROM 32 OR i.canonical_manifest IS NULL OR octet_length(i.canonical_manifest) NOT BETWEEN 1 AND 65536 OR sha256(i.canonical_manifest) IS DISTINCT FROM i.manifest OR i.signed_document IS NULL OR octet_length(i.signed_document) NOT BETWEEN 1 AND 65536 OR octet_length(i.signature) IS DISTINCT FROM 64 OR octet_length(i.payload_hash) IS DISTINCT FROM 32 OR NOT mixer_hosted_release.finite_uint(i.payload_size,1,4194304) OR i.blob_ref IS DISTINCT FROM 'sha256:'||encode(i.payload_hash,'hex') THEN RAISE EXCEPTION 'artifact rejected';END IF;
 IF r.key IS NULL OR octet_length(r.key) NOT BETWEEN 1 AND 128 OR r.key!~'^[A-Za-z0-9_.-]+$' OR r.path IS DISTINCT FROM '/v3/private/artifacts' OR r.body IS NULL OR octet_length(r.body) NOT BETWEEN 1 AND 6291456 OR octet_length(r.request_hash) IS DISTINCT FROM 32 OR r.request_hash IS DISTINCT FROM sha256(convert_to('POST '||r.path,'UTF8')||decode('00','hex')||r.body) OR r.reason IS NULL OR octet_length(r.reason)>512 OR r.request_id IS NULL OR (r.source_ip IS NOT NULL AND (octet_length(r.source_ip)>45 OR host(r.source_ip::inet) IS DISTINCT FROM r.source_ip)) THEN RAISE EXCEPTION 'request rejected';END IF;
 target_bytes:=mixer_hosted_release.target(i);
 -- Synthetic canonical auth lock; full five-class lock chain belongs to next product lane.
 PERFORM 1 FROM mixer_authz.fixture_policy f WHERE f.actor=c.actor FOR SHARE;
 IF NOT FOUND THEN RAISE EXCEPTION 'missing policy lock';END IF;
 SELECT * INTO h FROM mixer_hosted_release.tenant_heads x WHERE x.organization=i.organization AND x.project=i.project FOR UPDATE;
 IF NOT FOUND THEN RAISE EXCEPTION 'missing tenant head';END IF;
 -- Separate volatile SQL statement after all locks, before ANY idempotency lookup.
 SELECT * INTO ev FROM mixer_authz.evidence(c.actor);
 PERFORM mixer_hosted_release.time_valid(c,ev.now_s,clock_timestamp());
 IF h.last_event=0 THEN
  IF h.audit_hash<>''::bytea OR h.state_hash<>mixer_hosted_release.hash_domain('mixer.hosted.state.v1',mixer_hosted_release.a(ARRAY[mixer_hosted_release.u(1),mixer_hosted_release.t(i.organization),mixer_hosted_release.t(i.project)])) THEN RAISE EXCEPTION 'initial head corrupt';END IF;
 ELSE
  SELECT * INTO prior FROM mixer_hosted_release.audit_events x WHERE x.organization=i.organization AND x.project=i.project AND x.event_id=h.last_event;
  IF NOT FOUND THEN RAISE EXCEPTION 'missing terminal';END IF;
 SELECT * INTO ev FROM mixer_authz.evidence(c.actor);
 PERFORM mixer_hosted_release.time_valid(c,ev.now_s,clock_timestamp());

 IF NOT (prior.event_id=ANY(checked_ids)) THEN
  PERFORM mixer_hosted_release.row_valid(prior);
  IF prior.event_id>1 THEN
   SELECT * INTO edge FROM mixer_hosted_release.audit_events x WHERE x.organization=prior.organization AND x.project=prior.project AND x.event_id=prior.event_id-1;
   IF NOT FOUND THEN RAISE EXCEPTION 'missing predecessor';END IF;
 SELECT * INTO ev FROM mixer_authz.evidence(c.actor);
 PERFORM mixer_hosted_release.time_valid(c,ev.now_s,clock_timestamp());
   PERFORM mixer_hosted_release.row_valid(edge);
   IF prior.previous_hash IS DISTINCT FROM edge.event_hash OR prior.previous_state IS DISTINCT FROM edge.current_state THEN RAISE EXCEPTION 'predecessor edge corrupt';END IF;
  END IF;
  checked_ids:=array_append(checked_ids,prior.event_id);
 END IF;

  IF prior.event_hash IS DISTINCT FROM h.audit_hash OR prior.current_state IS DISTINCT FROM h.state_hash THEN RAISE EXCEPTION 'head corrupt';END IF;
 END IF;

 SELECT * INTO d FROM mixer_hosted_release.idempotency x WHERE x.organization=i.organization AND x.project=i.project AND x.key=r.key;
 -- Retain FOUND independently of later fresh evidence queries.
 status:=CASE WHEN FOUND THEN 1 ELSE 0 END;
 SELECT * INTO ev FROM mixer_authz.evidence(c.actor);
 PERFORM mixer_hosted_release.time_valid(c,ev.now_s,clock_timestamp());
 IF status=1 AND (d.actor IS DISTINCT FROM c.actor OR d.action IS DISTINCT FROM 'artifact.upload' OR d.target IS DISTINCT FROM target_bytes OR d.request_hash IS DISTINCT FROM r.request_hash) THEN RAISE EXCEPTION 'idempotency conflict' USING ERRCODE='23505';END IF;
 SELECT * INTO old FROM mixer_hosted_release.artifacts x WHERE x.organization=i.organization AND x.project=i.project AND x.manifest=i.manifest;
 actual_change:=NOT FOUND;
 SELECT * INTO ev FROM mixer_authz.evidence(c.actor);
 PERFORM mixer_hosted_release.time_valid(c,ev.now_s,clock_timestamp());
 IF NOT actual_change THEN
  IF (old.app,old.environment,old.platform,old.runtime,old.canonical_manifest,old.signed_document,old.signature,old.payload_hash,old.payload_size,old.blob_ref) IS DISTINCT FROM (i.app,i.environment,i.platform,i.runtime,i.canonical_manifest,i.signed_document,i.signature,i.payload_hash,i.payload_size,i.blob_ref) THEN RAISE EXCEPTION 'immutable artifact conflict' USING ERRCODE='23505';END IF;
  IF NOT mixer_hosted_release.finite_uint(old.created_event,1,18446744073709551615) OR old.created_actor IS NULL OR old.created_event>h.last_event THEN RAISE EXCEPTION 'creation link missing';END IF;
  SELECT * INTO creation FROM mixer_hosted_release.audit_events x WHERE x.organization=old.organization AND x.project=old.project AND x.event_id=old.created_event;
  IF NOT FOUND THEN RAISE EXCEPTION 'creation event missing';END IF;
 SELECT * INTO ev FROM mixer_authz.evidence(c.actor);
 PERFORM mixer_hosted_release.time_valid(c,ev.now_s,clock_timestamp());

 IF NOT (creation.event_id=ANY(checked_ids)) THEN
  PERFORM mixer_hosted_release.row_valid(creation);
  IF creation.event_id>1 THEN
   SELECT * INTO edge FROM mixer_hosted_release.audit_events x WHERE x.organization=creation.organization AND x.project=creation.project AND x.event_id=creation.event_id-1;
   IF NOT FOUND THEN RAISE EXCEPTION 'missing predecessor';END IF;
 SELECT * INTO ev FROM mixer_authz.evidence(c.actor);
 PERFORM mixer_hosted_release.time_valid(c,ev.now_s,clock_timestamp());
   PERFORM mixer_hosted_release.row_valid(edge);
   IF creation.previous_hash IS DISTINCT FROM edge.event_hash OR creation.previous_state IS DISTINCT FROM edge.current_state THEN RAISE EXCEPTION 'predecessor edge corrupt';END IF;
  END IF;
  checked_ids:=array_append(checked_ids,creation.event_id);
 END IF;

  IF creation.display_json->'target' IS DISTINCT FROM jsonb_build_array(i.organization,i.project,i.app,i.environment,i.platform,encode(i.runtime,'hex'),encode(i.manifest,'hex')) OR creation.display_json->'actor'->>0 IS DISTINCT FROM old.created_actor::text OR creation.current_state IS DISTINCT FROM mixer_hosted_release.changed_state(creation.previous_state,i) THEN RAISE EXCEPTION 'creation transition corrupt';END IF;
 END IF;
 IF status=1 THEN
  IF actual_change OR d.status IS NULL OR d.status NOT IN (200,201) OR d.response IS NULL OR octet_length(d.response) NOT BETWEEN 1 AND 4096 OR NOT mixer_hosted_release.finite_uint(d.event_id,1,18446744073709551615) OR d.event_id>h.last_event THEN RAISE EXCEPTION 'cached result corrupt';END IF;
  SELECT * INTO cached FROM mixer_hosted_release.audit_events x WHERE x.organization=d.organization AND x.project=d.project AND x.event_id=d.event_id;
  IF NOT FOUND THEN RAISE EXCEPTION 'cached event missing';END IF;
 SELECT * INTO ev FROM mixer_authz.evidence(c.actor);
 PERFORM mixer_hosted_release.time_valid(c,ev.now_s,clock_timestamp());

 IF NOT (cached.event_id=ANY(checked_ids)) THEN
  PERFORM mixer_hosted_release.row_valid(cached);
  IF cached.event_id>1 THEN
   SELECT * INTO edge FROM mixer_hosted_release.audit_events x WHERE x.organization=cached.organization AND x.project=cached.project AND x.event_id=cached.event_id-1;
   IF NOT FOUND THEN RAISE EXCEPTION 'missing predecessor';END IF;
 SELECT * INTO ev FROM mixer_authz.evidence(c.actor);
 PERFORM mixer_hosted_release.time_valid(c,ev.now_s,clock_timestamp());
   PERFORM mixer_hosted_release.row_valid(edge);
   IF cached.previous_hash IS DISTINCT FROM edge.event_hash OR cached.previous_state IS DISTINCT FROM edge.current_state THEN RAISE EXCEPTION 'predecessor edge corrupt';END IF;
  END IF;
  checked_ids:=array_append(checked_ids,cached.event_id);
 END IF;

  IF cached.display_json->'actor'->>0 IS DISTINCT FROM d.actor::text OR cached.display_json->>'action' IS DISTINCT FROM d.action OR cached.display_json->'target' IS DISTINCT FROM creation.display_json->'target' OR cached.display_json->>'request_hash' IS DISTINCT FROM encode(d.request_hash,'hex') OR d.status IS DISTINCT FROM (CASE WHEN cached.event_id=old.created_event THEN 201 ELSE 200 END) OR d.response IS DISTINCT FROM convert_to('{"manifest_sha256":"'||encode(i.manifest,'hex')||'","event_id":"'||d.event_id::text||'"}','UTF8') THEN RAISE EXCEPTION 'cached linkage/body corrupt';END IF;
  IF cached.event_id<>old.created_event AND cached.current_state IS DISTINCT FROM cached.previous_state THEN RAISE EXCEPTION 'cached unchanged transition corrupt';END IF;
  -- Repeat fresh authorization/time immediately before disclosing retained material.
 SELECT * INTO ev FROM mixer_authz.evidence(c.actor);
 PERFORM mixer_hosted_release.time_valid(c,ev.now_s,clock_timestamp());
  RETURN (d.status,d.response,d.event_id,true)::mixer_hosted_release.upload_result;
 END IF;
 IF h.last_event=18446744073709551615 THEN RAISE EXCEPTION 'event exhausted';END IF;
 event_id:=h.last_event+1;
 -- Test-only late read remains present to reproduce the original wait gap.
 SELECT boundary INTO fault FROM mixer_authz.fixture_fault WHERE id=1;
 SELECT * INTO ev FROM mixer_authz.evidence(c.actor);
 PERFORM mixer_hosted_release.time_valid(c,ev.now_s,clock_timestamp());

 state_next:=h.state_hash;
 IF actual_change THEN
  state_bytes:=mixer_hosted_release.a(ARRAY[mixer_hosted_release.u(1),mixer_hosted_release.b(h.state_hash), mixer_hosted_release.a(ARRAY[mixer_hosted_release.a(ARRAY[mixer_hosted_release.u(1),mixer_hosted_release.b(i.manifest),mixer_hosted_release.b(i.payload_hash),mixer_hosted_release.u(i.payload_size),mixer_hosted_release.t(i.blob_ref),target_bytes,mixer_hosted_release.b(sha256(i.signed_document)),mixer_hosted_release.b(i.signature)])])]);
  state_next:=mixer_hosted_release.hash_domain('mixer.hosted.state.v1',state_bytes);
 END IF;
 -- Fixed synthetic evidence stands in for the full schema1 fields, retaining exact shape.
 actor_bytes:=mixer_hosted_release.a(ARRAY[mixer_hosted_release.b(uuid_send(c.actor)),mixer_hosted_release.t('human'),mixer_hosted_release.b(uuid_send('00000000-0000-0000-0000-000000000010'::uuid)),mixer_hosted_release.t('fixture'),mixer_hosted_release.u(1),mixer_hosted_release.b(zero),mixer_hosted_release.b(zero),mixer_hosted_release.b(zero),mixer_hosted_release.b(zero),mixer_hosted_release.b(uuid_send('00000000-0000-0000-0000-000000000020'::uuid)),mixer_hosted_release.u(c.authentication_completed_at)]);
 decision_bytes:=mixer_hosted_release.a(ARRAY[mixer_hosted_release.u(ev.now_s),mixer_hosted_release.u(1),mixer_hosted_release.u(1),mixer_hosted_release.u(1),mixer_hosted_release.u(1),mixer_hosted_release.u(1),mixer_hosted_release.a(ARRAY[mixer_hosted_release.a(ARRAY[mixer_hosted_release.b(uuid_send(c.actor)),mixer_hosted_release.t(ev.role),mixer_hosted_release.u(ev.revision)])])]);
 event_bytes:=mixer_hosted_release.a(ARRAY[mixer_hosted_release.u(1),mixer_hosted_release.u(event_id),mixer_hosted_release.a(ARRAY[mixer_hosted_release.t(i.organization),mixer_hosted_release.t(i.project)]),actor_bytes,decision_bytes,target_bytes,mixer_hosted_release.t('artifact.upload'),mixer_hosted_release.t(r.reason),mixer_hosted_release.b(uuid_send(r.request_id)),mixer_hosted_release.t(r.source_ip),mixer_hosted_release.u(ev.now_s),mixer_hosted_release.b(h.state_hash),mixer_hosted_release.b(state_next),mixer_hosted_release.b(h.audit_hash),mixer_hosted_release.b(r.request_hash)]);
 IF octet_length(event_bytes)>16384 THEN RAISE EXCEPTION 'event budget';END IF;
 event_hash:=mixer_hosted_release.hash_domain('mixer.hosted.audit.v1',event_bytes);
 target_display:=jsonb_build_array(i.organization,i.project,i.app,i.environment,i.platform,encode(i.runtime,'hex'),encode(i.manifest,'hex'));
 display:=jsonb_build_object('audit_schema',1,'id',event_id::text,'tenant',jsonb_build_array(i.organization,i.project),'actor',jsonb_build_array(c.actor::text,'human','00000000-0000-0000-0000-000000000010','fixture','1',encode(zero,'hex'),encode(zero,'hex'),encode(zero,'hex'),encode(zero,'hex'),'00000000-0000-0000-0000-000000000020',c.authentication_completed_at::text),'decision',jsonb_build_array(ev.now_s::text,'1','1','1','1','1',jsonb_build_array(jsonb_build_array(c.actor::text,ev.role,ev.revision::text))),'target',target_display,'action','artifact.upload','reason',r.reason,'request_id',r.request_id::text,'source_ip',r.source_ip,'recorded_at',ev.now_s::text,'previous_state',encode(h.state_hash,'hex'),'current_state',encode(state_next,'hex'),'previous_hash',encode(h.audit_hash,'hex'),'request_hash',encode(r.request_hash,'hex'),'hash',encode(event_hash,'hex'));
 IF mixer_hosted_release.event_from_display(display) IS DISTINCT FROM event_bytes THEN RAISE EXCEPTION 'generated display mismatch';END IF;
 IF r.asserted_display IS NOT NULL AND r.asserted_display IS DISTINCT FROM display THEN RAISE EXCEPTION 'display mismatch';END IF;
 IF octet_length(convert_to(display::text,'UTF8'))>32768 THEN RAISE EXCEPTION 'display budget';END IF;
 IF c.deadline<=clock_timestamp() THEN RAISE EXCEPTION 'deadline';END IF;
 IF actual_change THEN INSERT INTO mixer_hosted_release.artifacts VALUES(i.organization,i.project,i.manifest,i.app,i.environment,i.platform,i.runtime,i.canonical_manifest,i.signed_document,i.signature,i.payload_hash,i.payload_size,i.blob_ref,event_id,c.actor);END IF;
 IF fault='artifact' THEN RAISE EXCEPTION 'fault artifact';END IF;
 INSERT INTO mixer_hosted_release.audit_events VALUES(i.organization,i.project,event_id,event_bytes,event_hash,h.audit_hash,h.state_hash,state_next,display,convert_to(display::text,'UTF8'));
 IF fault='audit' THEN RAISE EXCEPTION 'fault audit';END IF;
 status:=CASE WHEN actual_change THEN 201 ELSE 200 END;
 result_body:=convert_to('{"manifest_sha256":"'||encode(i.manifest,'hex')||'","event_id":"'||event_id::text||'"}','UTF8');
 IF octet_length(result_body)>4096 THEN RAISE EXCEPTION 'response budget';END IF;
 INSERT INTO mixer_hosted_release.idempotency VALUES(i.organization,i.project,r.key,c.actor,'artifact.upload',target_bytes,r.request_hash,status,result_body,event_id);
 IF fault='idempotency' THEN RAISE EXCEPTION 'fault idempotency';END IF;
 UPDATE mixer_hosted_release.tenant_heads x SET last_event=event_id,audit_hash=event_hash,state_hash=state_next WHERE x.organization=i.organization AND x.project=i.project;
 IF NOT FOUND THEN RAISE EXCEPTION 'missing head update';END IF;
 IF fault='head' THEN RAISE EXCEPTION 'fault head';END IF;

 SELECT * INTO ev FROM mixer_authz.evidence(c.actor);
 PERFORM mixer_hosted_release.time_valid(c,ev.now_s,clock_timestamp());
 RETURN (status,result_body,event_id,false)::mixer_hosted_release.upload_result;
END $$;
RESET ROLE;
ALTER FUNCTION mixer_hosted_release.upload_v1(mixer_hosted_release.call_context,mixer_hosted_release.upload_input,mixer_hosted_release.upload_request) OWNER TO mxas_writer;
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA mixer_authz,mixer_hosted_release FROM PUBLIC;
GRANT EXECUTE ON FUNCTION mixer_authz.allowed(text,text) TO mxas_resolver,mxas_writer,mxas_runtime;
GRANT EXECUTE ON FUNCTION mixer_authz.evidence(uuid) TO mxas_writer;
GRANT EXECUTE ON FUNCTION mixer_hosted_release.u(numeric) TO mxas_writer;
GRANT EXECUTE ON FUNCTION mixer_hosted_release.b(bytea) TO mxas_writer;
GRANT EXECUTE ON FUNCTION mixer_hosted_release.t(text) TO mxas_writer;
GRANT EXECUTE ON FUNCTION mixer_hosted_release.a(bytea[]) TO mxas_writer;
GRANT EXECUTE ON FUNCTION mixer_hosted_release.hash_domain(text,bytea) TO mxas_writer;
GRANT EXECUTE ON FUNCTION mixer_hosted_release.target(mixer_hosted_release.upload_input) TO mxas_writer;
GRANT EXECUTE ON FUNCTION mixer_hosted_release.hx(text) TO mxas_writer;
GRANT EXECUTE ON FUNCTION mixer_hosted_release.event_from_display(jsonb) TO mxas_writer;
GRANT EXECUTE ON FUNCTION mixer_hosted_release.finite_uint(numeric,numeric,numeric) TO mxas_writer;
GRANT EXECUTE ON FUNCTION mixer_hosted_release.jtext(jsonb,integer,integer) TO mxas_writer;
GRANT EXECUTE ON FUNCTION mixer_hosted_release.juint(jsonb,numeric,numeric) TO mxas_writer;
GRANT EXECUTE ON FUNCTION mixer_hosted_release.juuid(jsonb) TO mxas_writer;
GRANT EXECUTE ON FUNCTION mixer_hosted_release.jhex(jsonb,integer,integer) TO mxas_writer;
GRANT EXECUTE ON FUNCTION mixer_hosted_release.jid(jsonb) TO mxas_writer;
GRANT EXECUTE ON FUNCTION mixer_hosted_release.jarray(jsonb,integer) TO mxas_writer;
GRANT EXECUTE ON FUNCTION mixer_hosted_release.jip(jsonb) TO mxas_writer;
GRANT EXECUTE ON FUNCTION mixer_hosted_release.row_valid(mixer_hosted_release.audit_events) TO mxas_writer;
GRANT EXECUTE ON FUNCTION mixer_hosted_release.changed_state(bytea,mixer_hosted_release.upload_input) TO mxas_writer;
GRANT EXECUTE ON FUNCTION mixer_hosted_release.time_valid(mixer_hosted_release.call_context,numeric,timestamp with time zone) TO mxas_writer;
GRANT EXECUTE ON FUNCTION mixer_hosted_release.upload_v1(mixer_hosted_release.call_context,mixer_hosted_release.upload_input,mixer_hosted_release.upload_request) TO mxas_runtime,mxas_foreign;
-- Foreign EXECUTE is a deliberate adversarial privilege used only to prove session gate.
GRANT SELECT,INSERT ON mixer_hosted_release.artifacts,mixer_hosted_release.audit_events,mixer_hosted_release.idempotency TO mxas_writer;
GRANT SELECT,UPDATE(last_event,audit_hash,state_hash) ON mixer_hosted_release.tenant_heads TO mxas_writer;
GRANT SELECT ON mixer_authz.fixture_policy,mixer_authz.fixture_fault TO mxas_writer;
GRANT UPDATE(revision) ON mixer_authz.fixture_policy TO mxas_writer;
GRANT SELECT ON mixer_hosted_release.artifacts,mixer_hosted_release.audit_events TO mxas_runtime;
SET ROLE mxas_schema;
DO $$ DECLARE n text;BEGIN FOREACH n IN ARRAY ARRAY['fixture_policy','fixture_clock','fixture_fault'] LOOP EXECUTE format('ALTER TABLE mixer_authz.%I ENABLE ROW LEVEL SECURITY',n);EXECUTE format('ALTER TABLE mixer_authz.%I FORCE ROW LEVEL SECURITY',n);EXECUTE format('CREATE POLICY fixture_owner ON mixer_authz.%I TO mxas_schema USING(true) WITH CHECK(true)',n);EXECUTE format('CREATE POLICY resolver_read ON mixer_authz.%I FOR SELECT TO mxas_resolver USING(true)',n);END LOOP;END $$;
CREATE POLICY writer_read ON mixer_authz.fixture_policy FOR SELECT TO mxas_writer USING(true);
CREATE POLICY writer_lock ON mixer_authz.fixture_policy FOR UPDATE TO mxas_writer USING(true) WITH CHECK(true);
CREATE POLICY writer_fault ON mixer_authz.fixture_fault FOR SELECT TO mxas_writer USING(true);
DO $$ DECLARE n text;BEGIN FOREACH n IN ARRAY ARRAY['tenant_heads','artifacts','audit_events','idempotency'] LOOP EXECUTE format('ALTER TABLE mixer_hosted_release.%I ENABLE ROW LEVEL SECURITY',n);EXECUTE format('ALTER TABLE mixer_hosted_release.%I FORCE ROW LEVEL SECURITY',n);EXECUTE format('CREATE POLICY fixture_owner ON mixer_hosted_release.%I TO mxas_schema USING(true) WITH CHECK(true)',n);EXECUTE format('CREATE POLICY writer_scope ON mixer_hosted_release.%I TO mxas_writer USING(mixer_authz.allowed(organization,project)) WITH CHECK(mixer_authz.allowed(organization,project))',n);END LOOP;END $$;
CREATE POLICY runtime_artifact ON mixer_hosted_release.artifacts FOR SELECT TO mxas_runtime USING(current_setting('mixer_atomic.action',true)='artifact.read' AND mixer_authz.allowed(organization,project));
CREATE POLICY runtime_audit ON mixer_hosted_release.audit_events FOR SELECT TO mxas_runtime USING(current_setting('mixer_atomic.action',true)='audit.read' AND mixer_authz.allowed(organization,project));
INSERT INTO mixer_hosted_release.tenant_heads(organization,project,state_hash) VALUES('o','p',mixer_hosted_release.hash_domain('mixer.hosted.state.v1',mixer_hosted_release.a(ARRAY[mixer_hosted_release.u(1),mixer_hosted_release.t('o'),mixer_hosted_release.t('p')])));
COMMIT;
