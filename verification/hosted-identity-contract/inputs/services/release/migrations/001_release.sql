-- Original Mixer W11 durable substrate. Apply with a separate migration owner.
CREATE SCHEMA mixer_release;
REVOKE ALL ON SCHEMA mixer_release FROM PUBLIC;
DO $$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='mixer_release_runtime') THEN
  CREATE ROLE mixer_release_runtime NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS;
 END IF;
END $$;
GRANT USAGE ON SCHEMA mixer_release TO mixer_release_runtime;

CREATE FUNCTION mixer_release.in_scope(org text, project text) RETURNS boolean
LANGUAGE sql STABLE PARALLEL SAFE AS $$
 SELECT org=current_setting('mixer.organization',true)
    AND project=current_setting('mixer.project',true)
    AND current_setting('mixer.role',true) IN ('reader','editor','publisher','delivery')
$$;
CREATE FUNCTION mixer_release.can_edit() RETURNS boolean
LANGUAGE sql STABLE PARALLEL SAFE AS $$
 SELECT current_setting('mixer.role',true) IN ('editor','publisher')
$$;
CREATE FUNCTION mixer_release.can_publish() RETURNS boolean
LANGUAGE sql STABLE PARALLEL SAFE AS $$
 SELECT current_setting('mixer.role',true)='publisher'
$$;
REVOKE ALL ON FUNCTION mixer_release.in_scope(text,text),mixer_release.can_edit(),mixer_release.can_publish() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION mixer_release.in_scope(text,text),mixer_release.can_edit(),mixer_release.can_publish() TO mixer_release_runtime;

CREATE TABLE mixer_release.tenant_heads (
 organization text NOT NULL CHECK (organization ~ '^[A-Za-z0-9_.-]{1,128}$'),
 project text NOT NULL CHECK (project ~ '^[A-Za-z0-9_.-]{1,128}$'),
 last_event numeric(20,0) NOT NULL DEFAULT 0 CHECK(last_event BETWEEN 0 AND 18446744073709551615),
 audit_hash text NOT NULL DEFAULT '' CHECK(audit_hash='' OR audit_hash ~ '^[a-f0-9]{64}$'),
 state_hash text NOT NULL CHECK(state_hash ~ '^[a-f0-9]{64}$'),
 PRIMARY KEY(organization,project)
);
CREATE TABLE mixer_release.artifacts (
 organization text NOT NULL, project text NOT NULL,
 digest text NOT NULL CHECK(digest ~ '^[a-f0-9]{64}$'),
 signed_manifest bytea NOT NULL CHECK(octet_length(signed_manifest) BETWEEN 1 AND 1048576),
 payload bytea NOT NULL CHECK(octet_length(payload) BETWEEN 1 AND 16777216),
 CHECK(convert_from(signed_manifest,'UTF8')::jsonb->'manifest'->'scope'->>'organization' IS NOT DISTINCT FROM organization),
 CHECK(convert_from(signed_manifest,'UTF8')::jsonb->'manifest'->'scope'->>'project' IS NOT DISTINCT FROM project),
 PRIMARY KEY(organization,project,digest),
 FOREIGN KEY(organization,project) REFERENCES mixer_release.tenant_heads
);
CREATE TABLE mixer_release.artifact_state (
 organization text NOT NULL, project text NOT NULL, digest text NOT NULL,
 validated boolean NOT NULL DEFAULT false, published boolean NOT NULL DEFAULT false,
 CHECK (NOT published OR validated),
 PRIMARY KEY(organization,project,digest),
 FOREIGN KEY(organization,project,digest) REFERENCES mixer_release.artifacts
);
CREATE TABLE mixer_release.assignments (
 organization text NOT NULL, project text NOT NULL,
 channel_key text NOT NULL CHECK(octet_length(channel_key) BETWEEN 1 AND 1024),
 sequence numeric(20,0) NOT NULL CHECK(sequence BETWEEN 1 AND 18446744073709551615),
 artifact_digest text NOT NULL,
 signed_assignment bytea NOT NULL CHECK(octet_length(signed_assignment) BETWEEN 1 AND 1048576),
 CHECK(convert_from(signed_assignment,'UTF8')::jsonb->'assignment'->'scope'->>'organization' IS NOT DISTINCT FROM organization),
 CHECK(convert_from(signed_assignment,'UTF8')::jsonb->'assignment'->'scope'->>'project' IS NOT DISTINCT FROM project),
 CHECK((convert_from(signed_assignment,'UTF8')::jsonb->'assignment'->>'sequence')::numeric IS NOT DISTINCT FROM sequence),
 CHECK(convert_from(signed_assignment,'UTF8')::jsonb->'assignment'->>'artifact_sha256' IS NOT DISTINCT FROM artifact_digest),
 PRIMARY KEY(organization,project,channel_key,sequence),
 FOREIGN KEY(organization,project,artifact_digest) REFERENCES mixer_release.artifacts
);
CREATE TABLE mixer_release.channel_heads (
 organization text NOT NULL, project text NOT NULL, channel_key text NOT NULL,
 sequence numeric(20,0) NOT NULL,
 PRIMARY KEY(organization,project,channel_key),
 FOREIGN KEY(organization,project,channel_key,sequence) REFERENCES mixer_release.assignments
);
CREATE TABLE mixer_release.idempotency (
 organization text NOT NULL, project text NOT NULL,
 key text NOT NULL CHECK(key ~ '^[A-Za-z0-9_.-]{1,128}$'),
 request_hash text NOT NULL CHECK(request_hash ~ '^[a-f0-9]{64}$'),
 status integer NOT NULL CHECK(status BETWEEN 200 AND 299),
 response_body bytea NOT NULL CHECK(octet_length(response_body) BETWEEN 1 AND 1048576),
 PRIMARY KEY(organization,project,key),
 FOREIGN KEY(organization,project) REFERENCES mixer_release.tenant_heads
);
CREATE TABLE mixer_release.audit_events (
 organization text NOT NULL, project text NOT NULL,
 id numeric(20,0) NOT NULL CHECK(id BETWEEN 1 AND 18446744073709551615),
 event_body bytea NOT NULL CHECK(octet_length(event_body) BETWEEN 1 AND 16384),
 event_hash text NOT NULL CHECK(event_hash ~ '^[a-f0-9]{64}$'),
 previous_hash text NOT NULL CHECK(previous_hash='' OR previous_hash ~ '^[a-f0-9]{64}$'),
 CHECK(convert_from(event_body,'UTF8')::jsonb->>'organization' IS NOT DISTINCT FROM organization),
 CHECK(convert_from(event_body,'UTF8')::jsonb->>'project' IS NOT DISTINCT FROM project),
 CHECK((convert_from(event_body,'UTF8')::jsonb->>'id')::numeric IS NOT DISTINCT FROM id),
 CHECK(convert_from(event_body,'UTF8')::jsonb->>'hash' IS NOT DISTINCT FROM event_hash),
 PRIMARY KEY(organization,project,id),
 FOREIGN KEY(organization,project) REFERENCES mixer_release.tenant_heads
);
CREATE TABLE mixer_release.outbox (
 organization text NOT NULL, project text NOT NULL,
 id numeric(20,0) NOT NULL,
 event_id numeric(20,0) NOT NULL,
 work_body bytea NOT NULL CHECK(octet_length(work_body) BETWEEN 1 AND 2048),
 CHECK(id=event_id),
 CHECK(convert_from(work_body,'UTF8')::jsonb->>'status' IS NOT DISTINCT FROM 'pending_local_only'),
 PRIMARY KEY(organization,project,id),
 FOREIGN KEY(organization,project,event_id) REFERENCES mixer_release.audit_events
);

CREATE FUNCTION mixer_release.immutable() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'immutable release record' USING ERRCODE='42501'; END $$;
CREATE FUNCTION mixer_release.monotonic_artifact() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF (NEW.organization,NEW.project,NEW.digest) IS DISTINCT FROM (OLD.organization,OLD.project,OLD.digest)
    OR (OLD.validated AND NOT NEW.validated) OR (OLD.published AND NOT NEW.published)
    OR (NEW.published IS DISTINCT FROM OLD.published AND NOT mixer_release.can_publish()) THEN
  RAISE EXCEPTION 'invalid artifact state transition' USING ERRCODE='42501';
 END IF;
 RETURN NEW;
END $$;
CREATE FUNCTION mixer_release.monotonic_channel() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF (NEW.organization,NEW.project,NEW.channel_key) IS DISTINCT FROM (OLD.organization,OLD.project,OLD.channel_key)
    OR NEW.sequence<=OLD.sequence THEN
  RAISE EXCEPTION 'assignment sequence must advance' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END $$;
REVOKE ALL ON FUNCTION mixer_release.immutable(),mixer_release.monotonic_artifact(),mixer_release.monotonic_channel() FROM PUBLIC;
CREATE TRIGGER artifact_state_monotonic BEFORE UPDATE ON mixer_release.artifact_state FOR EACH ROW EXECUTE FUNCTION mixer_release.monotonic_artifact();
CREATE TRIGGER channel_head_monotonic BEFORE UPDATE ON mixer_release.channel_heads FOR EACH ROW EXECUTE FUNCTION mixer_release.monotonic_channel();

DO $$ DECLARE name text; BEGIN
 FOREACH name IN ARRAY ARRAY['tenant_heads','artifacts','artifact_state','assignments','channel_heads','idempotency','audit_events','outbox'] LOOP
  EXECUTE format('ALTER TABLE mixer_release.%I ENABLE ROW LEVEL SECURITY',name);
  EXECUTE format('ALTER TABLE mixer_release.%I FORCE ROW LEVEL SECURITY',name);
  EXECUTE format('REVOKE ALL ON mixer_release.%I FROM PUBLIC',name);
  IF name IN ('artifacts','assignments','idempotency','audit_events','outbox') THEN
   EXECUTE format('CREATE TRIGGER append_only BEFORE UPDATE OR DELETE ON mixer_release.%I FOR EACH ROW EXECUTE FUNCTION mixer_release.immutable()',name);
  END IF;
 END LOOP;
END $$;
-- No SELECT grants on tenant_heads for delivery except the explicit policy.
CREATE POLICY tenant_read ON mixer_release.tenant_heads FOR SELECT TO mixer_release_runtime USING(mixer_release.in_scope(organization,project) AND current_setting('mixer.role',true)<>'delivery');
CREATE POLICY tenant_insert ON mixer_release.tenant_heads FOR INSERT TO mixer_release_runtime WITH CHECK(mixer_release.in_scope(organization,project) AND mixer_release.can_edit());
CREATE POLICY tenant_update ON mixer_release.tenant_heads FOR UPDATE TO mixer_release_runtime USING(mixer_release.in_scope(organization,project) AND mixer_release.can_edit()) WITH CHECK(mixer_release.in_scope(organization,project) AND mixer_release.can_edit());
CREATE POLICY state_read ON mixer_release.artifact_state FOR SELECT TO mixer_release_runtime USING(mixer_release.in_scope(organization,project) AND (current_setting('mixer.role',true)<>'delivery' OR published));
CREATE POLICY state_insert ON mixer_release.artifact_state FOR INSERT TO mixer_release_runtime WITH CHECK(mixer_release.in_scope(organization,project) AND mixer_release.can_edit() AND (NOT published OR mixer_release.can_publish()));
CREATE POLICY state_update ON mixer_release.artifact_state FOR UPDATE TO mixer_release_runtime USING(mixer_release.in_scope(organization,project) AND mixer_release.can_edit()) WITH CHECK(mixer_release.in_scope(organization,project) AND mixer_release.can_edit());
CREATE POLICY artifact_read ON mixer_release.artifacts FOR SELECT TO mixer_release_runtime USING(mixer_release.in_scope(organization,project) AND (current_setting('mixer.role',true)<>'delivery' OR EXISTS(SELECT 1 FROM mixer_release.artifact_state s WHERE s.organization=artifacts.organization AND s.project=artifacts.project AND s.digest=artifacts.digest AND s.published)));
CREATE POLICY artifact_insert ON mixer_release.artifacts FOR INSERT TO mixer_release_runtime WITH CHECK(mixer_release.in_scope(organization,project) AND mixer_release.can_edit());
CREATE POLICY channel_read ON mixer_release.channel_heads FOR SELECT TO mixer_release_runtime USING(mixer_release.in_scope(organization,project));
CREATE POLICY channel_insert ON mixer_release.channel_heads FOR INSERT TO mixer_release_runtime WITH CHECK(mixer_release.in_scope(organization,project) AND mixer_release.can_publish());
CREATE POLICY channel_update ON mixer_release.channel_heads FOR UPDATE TO mixer_release_runtime USING(mixer_release.in_scope(organization,project) AND mixer_release.can_publish()) WITH CHECK(mixer_release.in_scope(organization,project) AND mixer_release.can_publish());
CREATE POLICY assignment_read ON mixer_release.assignments FOR SELECT TO mixer_release_runtime USING(mixer_release.in_scope(organization,project) AND (current_setting('mixer.role',true)<>'delivery' OR EXISTS(SELECT 1 FROM mixer_release.channel_heads h WHERE h.organization=assignments.organization AND h.project=assignments.project AND h.channel_key=assignments.channel_key AND h.sequence=assignments.sequence)));
CREATE POLICY assignment_insert ON mixer_release.assignments FOR INSERT TO mixer_release_runtime WITH CHECK(mixer_release.in_scope(organization,project) AND mixer_release.can_publish());
DO $$ DECLARE name text; BEGIN
 FOREACH name IN ARRAY ARRAY['idempotency','audit_events','outbox'] LOOP
  EXECUTE format('CREATE POLICY tenant_read ON mixer_release.%I FOR SELECT TO mixer_release_runtime USING(mixer_release.in_scope(organization,project) AND current_setting(''mixer.role'',true)<>''delivery'')',name);
  EXECUTE format('CREATE POLICY tenant_insert ON mixer_release.%I FOR INSERT TO mixer_release_runtime WITH CHECK(mixer_release.in_scope(organization,project) AND mixer_release.can_edit())',name);
 END LOOP;
END $$;
GRANT SELECT,INSERT,UPDATE ON mixer_release.tenant_heads,mixer_release.artifact_state,mixer_release.channel_heads TO mixer_release_runtime;
GRANT SELECT,INSERT ON mixer_release.artifacts,mixer_release.assignments,mixer_release.idempotency,mixer_release.audit_events,mixer_release.outbox TO mixer_release_runtime;
